"""Made-up test data: a catalogue and a clock that only moves when a test moves it, plus a poll.

Every catalogue id, name and status here is invented and none is real. The real 46 ids are
Tanishq's, and the ids below must never be copied from anywhere.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path


def wait_until[T](check: Callable[[], T], timeout: float = 30.0) -> T:
    """Polls until `check()` is truthy and returns its value. A real child process finishes on
    its own clock, so a test waits for the state it needs and never sleeps for a fixed time."""
    end = time.monotonic() + timeout
    while not (value := check()):
        if time.monotonic() > end:
            raise AssertionError("the awaited state did not arrive")
        time.sleep(0.02)
    return value


def process_alive(pid: int) -> bool:
    """Whether a process with this id is running. A test uses it for the interpreter behind
    a child, which the Popen object does not show."""
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    kernel32.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32))
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    handle = kernel32.OpenProcess(0x1000, 0, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    code = ctypes.c_uint32()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    kernel32.CloseHandle(handle)
    return code.value == 259  # STILL_ACTIVE


def snapshot(root: Path) -> set[tuple[str, int, int]]:
    """Path, size and modification time of every file under root, tool folders left out."""
    skip = {".venv", ".git", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", "dist"}
    found = set()
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            stat = os.stat(os.path.join(folder, name))
            found.add((os.path.join(folder, name), stat.st_size, stat.st_mtime_ns))
    return found


class FakeClock:
    """The injected clock (one callable). Tests move time with `advance`, so nothing sleeps."""

    def __init__(self, now: float = 1_800_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def synthetic_catalogue() -> dict:
    return {
        "catalogue_version": "synthetic-test-0",
        "categories": [
            {
                "id": "synthetic.alpha",
                "display_name": "Synthetic Alpha",
                "source": "cuad",
                "support_status": "synthetic_status_a",
            },
            {
                "id": "synthetic.beta",
                "display_name": "Synthetic Beta",
                "source": "india_extension",
                "support_status": "synthetic_status_b",
            },
            {
                "id": "synthetic.gamma",
                "display_name": "Synthetic Gamma",
                "source": "cuad",
                "support_status": "synthetic_status_a",
            },
        ],
    }
