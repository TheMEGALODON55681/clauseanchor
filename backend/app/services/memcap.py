"""A memory cap for one child process. This is the only platform-specific code in the API (D2).

Windows: a job object with a per-process memory limit, made through ctypes. The child is created
suspended, joins the job, and only then runs, so nothing it starts can be outside the cap: a
virtualenv's python.exe is a launcher that starts the real interpreter at once, and a child that
joined after that would miss it. The caller writes to the child's stdin after that, and the child
does nothing until its input arrives. Closing the job's handle kills whatever is still in it.
POSIX: RLIMIT_AS, set in the child between fork and exec.
"""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x100
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    _EXTENDED_LIMIT_INFORMATION = 9
    _BASIC_ACCOUNTING_INFORMATION = 1
    _CREATE_SUSPENDED = 0x4

    class _BasicLimits(ctypes.Structure):
        _fields_ = (
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        )

    class _IoCounters(ctypes.Structure):
        _fields_ = tuple((name, ctypes.c_ulonglong) for name in "ABCDEF")

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = (
            ("BasicLimitInformation", _BasicLimits),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        )

    class _Accounting(ctypes.Structure):
        _fields_ = (
            ("TotalUserTime", wintypes.LARGE_INTEGER),
            ("TotalKernelTime", wintypes.LARGE_INTEGER),
            ("ThisPeriodTotalUserTime", wintypes.LARGE_INTEGER),
            ("ThisPeriodTotalKernelTime", wintypes.LARGE_INTEGER),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        )

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    _kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    _kernel32.QueryInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
    )
    _kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    _kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    # Popen drops the suspended process's thread handle, so the whole process is resumed instead
    _ntdll = ctypes.WinDLL("ntdll")
    _ntdll.NtResumeProcess.argtypes = (wintypes.HANDLE,)
    _ntdll.NtResumeProcess.restype = ctypes.c_long

BACKEND_DIR = Path(__file__).resolve().parents[2]  # where `python -m app...` finds the package


class CappedProcess:
    """A child process that starts inside a memory cap. `popen` is an ordinary Popen with stdin
    and stdout pipes and stderr discarded. Call `close` once the child has exited."""

    def __init__(self, args: Sequence[str], memory_bytes: int) -> None:
        self._job = None
        if sys.platform == "win32":
            self._job = self._make_job(memory_bytes)
            try:
                self.popen = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    cwd=BACKEND_DIR,
                    creationflags=subprocess.CREATE_NO_WINDOW | _CREATE_SUSPENDED,
                )
            except BaseException:
                _kernel32.CloseHandle(self._job)
                raise
            handle = int(self.popen._handle)
            joined = _kernel32.AssignProcessToJobObject(self._job, handle)
            error = ctypes.get_last_error()
            # A child that cannot join its cap does not run: fail closed
            if not joined or _ntdll.NtResumeProcess(handle) != 0:
                self.popen.kill()
                self.popen.wait()
                self.close()
                raise OSError(error, "the child could not start inside its memory cap")
        else:
            import resource

            def apply_cap() -> None:
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

            self.popen = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=BACKEND_DIR,
                preexec_fn=apply_cap,
            )

    @staticmethod
    def _make_job(memory_bytes: int):
        job = _kernel32.CreateJobObjectW(None, None)
        if not job:
            raise OSError(ctypes.get_last_error(), "no job object")
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = (
            _JOB_OBJECT_LIMIT_PROCESS_MEMORY | _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        limits.ProcessMemoryLimit = memory_bytes
        if not _kernel32.SetInformationJobObject(
            job, _EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            error = ctypes.get_last_error()
            _kernel32.CloseHandle(job)
            raise OSError(error, "the memory cap could not be set")
        return job

    def peak_bytes(self) -> int | None:
        """The most memory the child committed, or None where the platform cannot say (POSIX)."""
        if self._job is None:
            return None
        limits = _ExtendedLimits()
        if not _kernel32.QueryInformationJobObject(
            self._job,
            _EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
            None,
        ):
            return None
        return limits.PeakProcessMemoryUsed

    def kill(self) -> None:
        """Ends the child and everything it started. On Windows the job is ended, because the
        process `popen` holds is the launcher of a virtualenv and the interpreter is its child."""
        if self._job is not None:
            _kernel32.TerminateJobObject(self._job, 1)
        self.popen.kill()

    def wait(self, timeout: float) -> bool:
        """True once the child has exited and, on Windows, nothing is left in its job. The console
        host Windows gives a child without a console goes a moment after the child does."""
        end = time.monotonic() + timeout
        try:
            self.popen.wait(timeout)
        except subprocess.TimeoutExpired:
            return False
        while self._job is not None and self._active() > 0:
            if time.monotonic() > end:
                return False
            time.sleep(0.005)
        return True

    def _active(self) -> int:
        accounting = _Accounting()
        _kernel32.QueryInformationJobObject(
            self._job,
            _BASIC_ACCOUNTING_INFORMATION,
            ctypes.byref(accounting),
            ctypes.sizeof(accounting),
            None,
        )
        return accounting.ActiveProcesses

    def close(self) -> None:
        if self._job is not None:
            _kernel32.CloseHandle(self._job)
            self._job = None
