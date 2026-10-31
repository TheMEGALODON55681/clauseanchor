"""The parse queue: one worker, one child process per parse, real children throughout."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import replace

import pytest

from app.config import Settings
from app.parsing import parse_document
from app.services import parse_jobs
from app.services.parse_jobs import ParseQueue
from app.services.store import DocumentRecord, Session, Store
from tests.fixtures.build import build_docx
from tests.synthetic import FakeClock, process_alive, wait_until

TTL = 3600
SLOW = [
    sys.executable,
    "-c",
    "import time, runpy; time.sleep(0.8);"
    " runpy.run_module('app.parse_worker', run_name='__main__')",
]
Rig = Callable[..., tuple[Store, ParseQueue]]


@pytest.fixture
def rig(clock: FakeClock, spawned: list[subprocess.Popen[bytes]]) -> Iterator[Rig]:
    """Queues on a fresh store. It needs `spawned` first, so the leak check runs after the stop."""
    made: list[tuple[Store, ParseQueue]] = []

    def build(**overrides: int) -> tuple[Store, ParseQueue]:
        store = Store(ttl_seconds=TTL, clock=clock)
        queue = ParseQueue(store, replace(Settings(), **overrides))
        queue.start()
        made.append((store, queue))
        return store, queue

    yield build
    for store, queue in made:
        queue.stop()
        store.close()


def upload(store: Store, queue: ParseQueue, data: bytes) -> tuple[Session, DocumentRecord, str]:
    _, session = store.create_session()
    doc = store.add_document(
        session.id, filename="a.pdf", media_type="application/pdf", byte_count=len(data)
    )
    job_id = store.add_job(doc.id, "parse")
    assert queue.submit(doc.id, job_id, data) is True
    return session, doc, job_id


def job(store: Store, session: Session, job_id: str):
    return store.get_job(session.id, job_id)


def finished(store: Store, session: Session, job_id: str):
    return wait_until(
        lambda: (j := job(store, session, job_id)) and j.status in ("succeeded", "failed") and j
    )


def test_a_parse_runs_in_a_child_and_the_document_is_stored(
    rig: Rig, fixture_bytes: dict[str, bytes], spawned: list[subprocess.Popen[bytes]]
) -> None:
    store, queue = rig()
    raw = fixture_bytes["simple.pdf"]
    session, doc, job_id = upload(store, queue, raw)
    done = finished(store, session, job_id)
    assert (done.status, done.error) == ("succeeded", None)
    held = store.get_document(session.id, doc.id)
    assert held.status == "parsed"
    assert held.parsed == parse_document(raw)
    assert len(spawned) == 1
    assert spawned[0].poll() is not None


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("malformed.pdf", "MALFORMED_FILE"),
        ("scanned.pdf", "SCANNED_PDF"),
        ("tracked_insert.docx", "TRACKED_CHANGES_PRESENT"),
        ("corrupt_zip.docx", "MALFORMED_FILE"),
    ],
)
def test_a_parser_error_becomes_the_job_error(
    rig: Rig, fixture_bytes: dict[str, bytes], name: str, code: str
) -> None:
    store, queue = rig()
    session, doc, job_id = upload(store, queue, fixture_bytes[name])
    done = finished(store, session, job_id)
    assert (done.status, done.error) == ("failed", code)
    held = store.get_document(session.id, doc.id)
    assert (held.status, held.parsed) == ("failed", None)


def test_one_child_runs_at_a_time_and_a_job_moves_from_queued_to_running_to_succeeded(
    rig: Rig,
    fixture_bytes: dict[str, bytes],
    spawned: list[subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(parse_jobs, "WORKER_ARGS", SLOW)
    store, queue = rig()
    raw = fixture_bytes["simple.pdf"]
    first = upload(store, queue, raw)
    second = upload(store, queue, raw)
    seen: set[tuple[str, str]] = set()
    most_alive = 0
    end = time.monotonic() + 60
    while time.monotonic() < end:
        states = (job(store, *first[::2]).status, job(store, *second[::2]).status)
        seen.add(states)
        most_alive = max(most_alive, sum(child.poll() is None for child in spawned))
        if states == ("succeeded", "succeeded"):
            break
        time.sleep(0.02)
    assert ("running", "queued") in seen
    assert ("succeeded", "queued") in seen or ("succeeded", "running") in seen
    assert seen <= {
        ("queued", "queued"),
        ("running", "queued"),
        ("succeeded", "queued"),
        ("succeeded", "running"),
        ("succeeded", "succeeded"),
    }
    assert most_alive == 1
    assert len(spawned) == 2


def test_a_child_that_hangs_is_killed_at_the_wall_clock_limit(
    rig: Rig, spawned: list[subprocess.Popen[bytes]], hanging: Callable[[], int]
) -> None:
    store, queue = rig(parse_kill_seconds=1)
    # More than a pipe holds, so the write to the child's stdin blocks as well: the kill must
    # not wait for a child that never reads.
    session, doc, job_id = upload(store, queue, b"x" * 2_000_000)
    start = time.monotonic()
    done = finished(store, session, job_id)
    assert (done.status, done.error) == ("failed", "PARSE_TIMEOUT")
    assert time.monotonic() - start < 15
    assert not process_alive(hanging())
    assert spawned[0].poll() is not None
    assert store.get_document(session.id, doc.id).status == "failed"


def test_a_parse_that_reaches_the_memory_cap_fails_with_the_memory_code(
    rig: Rig, spawned: list[subprocess.Popen[bytes]]
) -> None:
    store, queue = rig(parse_memory_mib=64)
    bomb = build_docx("<w:p/>" * 700_000)  # about 4 MB of empty paragraphs, 130 MiB in lxml
    session, _, job_id = upload(store, queue, bomb)
    done = finished(store, session, job_id)
    # lxml reports the refused allocation as a read error, so the child says MALFORMED_FILE
    assert (done.status, done.error) == ("failed", "PARSE_MEMORY_LIMIT")
    assert spawned[0].poll() is not None


def test_each_child_starts_under_the_configured_cap(
    rig: Rig, monkeypatch: pytest.MonkeyPatch, fixture_bytes: dict[str, bytes]
) -> None:
    # The peak rule gives the memory code with or without an OS cap, so the memory tests alone
    # cannot show that the cap reaches the child. test_memcap shows the cap works.
    caps: list[int] = []
    real = parse_jobs.CappedProcess

    def spy(args, memory_bytes):
        caps.append(memory_bytes)
        return real(args, memory_bytes)

    monkeypatch.setattr(parse_jobs, "CappedProcess", spy)
    store, queue = rig(parse_memory_mib=64)
    session, _, job_id = upload(store, queue, fixture_bytes["simple.docx"])
    assert finished(store, session, job_id).status == "succeeded"
    assert caps == [64 * 1024 * 1024]


def test_a_small_file_fits_the_same_small_cap(rig: Rig, fixture_bytes: dict[str, bytes]) -> None:
    store, queue = rig(parse_memory_mib=64)
    session, _, job_id = upload(store, queue, fixture_bytes["simple.docx"])
    assert finished(store, session, job_id).status == "succeeded"


@pytest.mark.parametrize(
    "script",
    [
        "import sys; sys.exit(3)",
        "import sys; sys.stdout.write('garbage')",
        "pass",
        'import sys; sys.stdout.write(\'{"error": "NO_SUCH_CODE"}\')',
        "import sys; sys.stdout.write('[1]')",
        "import sys; sys.stdout.write('{\"document\": {}}')",
        'import sys; sys.stdout.write(\'{"error": "NO_TEXT_FOUND"}\'); sys.exit(1)',
    ],
    ids=[
        "exit status",
        "not json",
        "no output",
        "unknown code",
        "wrong shape",
        "empty document",
        "valid answer but a failing exit",
    ],
)
def test_any_other_child_failure_is_parse_failed(
    rig: Rig, monkeypatch: pytest.MonkeyPatch, script: str
) -> None:
    monkeypatch.setattr(parse_jobs, "WORKER_ARGS", [sys.executable, "-c", script])
    store, queue = rig()
    session, _, job_id = upload(store, queue, b"anything")
    done = finished(store, session, job_id)
    assert (done.status, done.error) == ("failed", "PARSE_FAILED")


def test_a_failure_in_the_worker_fails_that_job_and_the_next_one_runs(
    rig: Rig,
    fixture_bytes: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    real = parse_jobs.CappedProcess
    calls: list[int] = []

    def flaky(args: object, memory_bytes: int) -> object:
        calls.append(1)
        if len(calls) == 1:
            raise OSError("secret-library-text")
        return real(args, memory_bytes)

    monkeypatch.setattr(parse_jobs, "CappedProcess", flaky)
    store, queue = rig()
    first = upload(store, queue, fixture_bytes["simple.pdf"])
    second = upload(store, queue, fixture_bytes["simple.pdf"])
    assert finished(store, first[0], first[2]).error == "PARSE_FAILED"
    assert finished(store, second[0], second[2]).status == "succeeded"
    assert "secret-library-text" not in caplog.text
    assert "OSError" in caplog.text


def test_a_full_queue_refuses_the_next_job(
    rig: Rig, spawned: list[subprocess.Popen[bytes]], hanging: Callable[[], int]
) -> None:
    store, queue = rig(parse_queue_length=1)
    first = upload(store, queue, b"a")
    wait_until(lambda: job(store, *first[::2]).status == "running")  # it left the queue
    upload(store, queue, b"b")  # waits: this is the one place in the queue
    _, session = store.create_session()
    doc = store.add_document(
        session.id, filename="c.pdf", media_type="application/pdf", byte_count=1
    )
    third = store.add_job(doc.id, "parse")
    assert queue.submit(doc.id, third, b"c") is False
    assert len(spawned) == 1


def test_deleting_a_document_mid_parse_kills_its_child_before_the_call_returns(
    rig: Rig, spawned: list[subprocess.Popen[bytes]], hanging: Callable[[], int]
) -> None:
    store, queue = rig()
    session, doc, job_id = upload(store, queue, b"a")
    pid = hanging()
    assert spawned[0].poll() is None
    assert process_alive(pid)
    assert store.delete_document(session.id, doc.id) is True
    assert spawned[0].poll() is not None
    assert not process_alive(
        pid
    )  # the interpreter, which the launcher on Windows stands in front of
    assert job(store, session, job_id) is None


def test_deleting_a_session_kills_its_child(
    rig: Rig, spawned: list[subprocess.Popen[bytes]], hanging: Callable[[], int]
) -> None:
    store, queue = rig()
    session, _, _ = upload(store, queue, b"a")
    pid = hanging()
    store.delete_session(session.id)
    assert spawned[0].poll() is not None
    assert not process_alive(pid)


def test_an_expired_session_loses_its_child_to_the_sweep(
    rig: Rig,
    spawned: list[subprocess.Popen[bytes]],
    hanging: Callable[[], int],
    clock: FakeClock,
) -> None:
    store, queue = rig()
    upload(store, queue, b"a")
    pid = hanging()
    clock.advance(TTL)
    assert store.sweep() == 1
    assert spawned[0].poll() is not None
    assert not process_alive(pid)


def test_a_document_deleted_while_it_waits_is_never_parsed_and_its_bytes_are_dropped(
    rig: Rig, spawned: list[subprocess.Popen[bytes]], hanging: Callable[[], int]
) -> None:
    store, queue = rig()
    first = upload(store, queue, b"a")
    hanging()
    session, doc, _ = upload(store, queue, b"waiting")
    waiting = queue._items[doc.id]
    store.delete_document(session.id, doc.id)
    assert waiting.data is None
    store.delete_document(first[0].id, first[1].id)  # frees the worker
    wait_until(lambda: queue._items == {})
    assert len(spawned) == 1


def test_a_child_is_killed_when_the_hook_runs_while_the_worker_is_still_starting_it(
    rig: Rig, fixture_bytes: dict[str, bytes], spawned: list[subprocess.Popen[bytes]]
) -> None:
    store, queue = rig()
    session, doc, _ = upload(store, queue, fixture_bytes["simple.pdf"])
    store.delete_document(session.id, doc.id)  # races the worker, and either order must end clean
    wait_until(lambda: queue._items == {})
    assert all(child.poll() is not None for child in spawned)


def test_stopping_the_queue_kills_the_running_child_and_ends_the_thread(
    rig: Rig, spawned: list[subprocess.Popen[bytes]], hanging: Callable[[], int]
) -> None:
    store, queue = rig(parse_queue_length=2)
    upload(store, queue, b"a")
    upload(store, queue, b"b")
    pid = hanging()
    queue.stop()
    assert spawned[0].poll() is not None
    assert not process_alive(pid)
    assert not queue._thread.is_alive()
    assert len(spawned) == 1  # the waiting job was never started


def test_what_a_child_writes_to_stderr_reaches_no_log_and_no_record(
    rig: Rig,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    script = "import sys; sys.stderr.write('CANARY-CONTRACT-TEXT'); sys.exit(1)"
    monkeypatch.setattr(parse_jobs, "WORKER_ARGS", [sys.executable, "-c", script])
    caplog.set_level(logging.DEBUG)
    store, queue = rig()
    session, doc, job_id = upload(store, queue, b"anything")
    done = finished(store, session, job_id)
    queue.stop()
    seen = capfd.readouterr()
    for text in (
        caplog.text,
        seen.out,
        seen.err,
        repr(done),
        repr(store.get_document(session.id, doc.id)),
    ):
        assert "CANARY-CONTRACT-TEXT" not in text
