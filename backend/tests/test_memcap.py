"""The memory cap, on real child processes."""

from __future__ import annotations

import subprocess
import sys

import pytest

from app.services.memcap import CappedProcess

MIB = 1024 * 1024
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="job objects exist on Windows")


def run(code: str, cap_mib: int) -> tuple[subprocess.Popen[bytes], bytes, int | None]:
    capped = CappedProcess([sys.executable, "-c", code], cap_mib * MIB)
    try:
        out, _ = capped.popen.communicate(b"", timeout=60)
        return capped.popen, out, capped.peak_bytes()
    finally:
        if capped.popen.poll() is None:
            capped.popen.kill()
            capped.popen.wait()
        capped.close()


def test_a_child_inside_its_cap_runs_normally() -> None:
    popen, out, peak = run("print('fits')", 256)
    assert (popen.returncode, out.strip()) == (0, b"fits")
    assert peak is None or 0 < peak < 256 * MIB


def test_a_child_over_its_cap_cannot_get_the_memory() -> None:
    popen, out, _ = run("x = bytearray(400 * 1024 * 1024); print('got it')", 128)
    assert popen.returncode != 0
    assert b"got it" not in out


@windows_only
def test_the_peak_shows_that_the_cap_was_reached() -> None:
    _, _, peak = run("x = []\nwhile True: x.append(bytearray(1024 * 1024))", 96)
    assert peak is not None
    assert peak >= 0.95 * 96 * MIB


@windows_only
def test_closing_the_job_kills_a_child_that_is_still_running() -> None:
    capped = CappedProcess([sys.executable, "-c", "import time; time.sleep(600)"], 256 * MIB)
    assert capped.popen.poll() is None
    capped.close()
    capped.popen.wait(timeout=10)
    assert capped.popen.returncode is not None


def test_stderr_is_discarded_and_stdin_is_a_pipe() -> None:
    capped = CappedProcess(
        [
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('x' * 100000); print(sys.stdin.read())",
        ],
        256 * MIB,
    )
    out, err = capped.popen.communicate(b"echo", timeout=60)
    capped.close()
    assert (out.strip(), err) == (b"echo", None)


@windows_only
@pytest.mark.parametrize("failing", ["AssignProcessToJobObject", "NtResumeProcess"])
def test_a_child_that_cannot_start_inside_its_cap_is_killed_and_never_runs(
    monkeypatch: pytest.MonkeyPatch, failing: str
) -> None:
    from app.services import memcap

    target = memcap._ntdll if failing == "NtResumeProcess" else memcap._kernel32
    monkeypatch.setattr(
        target, failing, lambda *args: 0 if failing == "AssignProcessToJobObject" else 1
    )
    made: list[subprocess.Popen[bytes]] = []

    class Recorded(subprocess.Popen):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            made.append(self)

    monkeypatch.setattr(memcap.subprocess, "Popen", Recorded)
    with pytest.raises(OSError, match="inside its memory cap"):
        CappedProcess([sys.executable, "-c", "import time; time.sleep(600)"], 256 * MIB)
    assert len(made) == 1
    assert made[0].poll() is not None
