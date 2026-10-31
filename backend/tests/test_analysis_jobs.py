"""The analysis queue with a fake core: load states, every way a job can end, FIFO and the limit."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from clauseanchor_core import AnalysisResult, ProgressEvent, text_digest

from app.config import Settings
from app.parsing.errors import WarningCode
from app.parsing.model import ParsedDocument, ParseWarning, StructureNode
from app.services.analysis_jobs import AnalysisQueue
from app.services.store import JobRecord, Session, Store
from tests.fake_core import DIGEST, MADE_UP_TEXT, FakeCore, add_parsed, parsed_document, real_result
from tests.synthetic import FakeClock, wait_until

IDS = ("cat.one", "cat.two", "cat.three")
SECRET = "SECRET-CONTRACT-WORDS-91"


@dataclass
class Started:
    session: Session
    document_id: str
    job_id: str
    analysis_id: str
    parsed: ParsedDocument


class Rig:
    def __init__(self, store: Store, queue: AnalysisQueue, core: FakeCore) -> None:
        self.store, self.queue, self.core = store, queue, core

    def start(
        self, parsed: ParsedDocument | None = None, *, ids=IDS, scope="unspecified", session=None
    ) -> Started:
        parsed = parsed or parsed_document()
        session = session or self.store.create_session()[1]
        doc = add_parsed(self.store, session, parsed)
        job_id, analysis_id = self.store.add_analysis_job(session.id, doc.id, ids, scope)
        assert self.queue.submit(job_id, doc.id, parsed, ids, scope)
        return Started(session, doc.id, job_id, analysis_id, parsed)

    def job(self, started: Started) -> JobRecord:
        return self.store.get_job(started.session.id, started.job_id)

    def wait(self, started: Started, *statuses: str) -> JobRecord:
        return wait_until(lambda: (j := self.job(started)).status in statuses and j)

    def held(self, started: Started):
        return self.store.get_document(started.session.id, started.document_id).analysis


@pytest.fixture
def make_rig(clock: FakeClock, fake_core: FakeCore, tmp_path: Path) -> Iterator[Callable[..., Rig]]:
    with ExitStack() as stack:

        def make(*, loaded: bool = True, **overrides: object) -> Rig:
            settings = replace(
                Settings(analyzer="real", artifacts_dir=tmp_path, artifacts_sha256=DIGEST),
                **overrides,
            )
            store = Store(ttl_seconds=3600, clock=clock)
            queue = AnalysisQueue(store, settings)
            stack.callback(store.close)
            stack.callback(queue.stop)  # runs first: LIFO
            queue.start()
            if loaded:
                wait_until(lambda: queue.state != "loading")
            return Rig(store, queue, fake_core)

        yield make


@pytest.fixture
def rig(make_rig: Callable[..., Rig]) -> Rig:
    return make_rig()


# --- loading ---------------------------------------------------------------------------------


def test_the_analyzer_loads_off_the_calling_thread_and_reports_loading_then_ok(
    make_rig: Callable[..., Rig], fake_core: FakeCore
) -> None:
    fake_core.load_gate = threading.Event()
    rig = make_rig(loaded=False)
    wait_until(lambda: fake_core.loads)
    assert rig.queue.state == "loading"
    fake_core.load_gate.set()
    wait_until(lambda: rig.queue.state == "ok")
    assert rig.queue.analyzer is fake_core


def test_a_failed_load_is_reported_and_logs_the_class_name_only(
    make_rig: Callable[..., Rig], fake_core: FakeCore, caplog: pytest.LogCaptureFixture
) -> None:
    fake_core.load_error = RuntimeError(SECRET)
    with caplog.at_level(logging.DEBUG):
        rig = make_rig()
    assert rig.queue.state == "failed"
    assert rig.queue.analyzer is None
    assert "RuntimeError" in caplog.text
    assert SECRET not in caplog.text


# --- the ways a job ends ---------------------------------------------------------------------


def test_a_complete_run_succeeds_with_its_validated_result_and_its_progress(rig: Rig) -> None:
    started = rig.start()
    job = rig.wait(started, "succeeded")
    assert (job.error, job.stage, job.completed_units, job.total_units) == (None, "inference", 3, 3)
    assert job.finished_at is not None
    result = rig.held(started).result
    assert [c.category_id for c in result.categories] == list(IDS)
    assert result.doc_id == started.document_id  # the core's doc_id is the document's id


def test_the_core_gets_the_stored_text_untouched_and_the_context_from_the_bridge(
    rig: Rig,
) -> None:
    node = StructureNode("n1", None, "heading", "1", 1, 0, 6, "Madeup")
    parsed = parsed_document(
        nodes=(node,),
        decorations=((26, 27),),
        warnings=(ParseWarning(WarningCode.BLANK_PAGE, 1),),
        partial=True,
    )
    started = rig.start(parsed, scope="india_review")
    rig.wait(started, "partial")
    (call,) = rig.core.calls
    assert call["text"] is parsed.source_text  # not copied, cleaned or rebuilt (D6)
    assert (call["doc_id"], call["text_sha256"]) == (started.document_id, parsed.text_sha256)
    assert call["category_ids"] == IDS
    context = call["context"]
    assert (context.jurisdiction_scope, context.parser_complete) == ("india_review", False)
    assert context.warnings == ["BLANK_PAGE"]
    assert [(n.id, n.kind, n.start, n.end) for n in context.structure_nodes] == [
        ("n1", "heading", 0, 6),
        ("clauseanchor.decoration.0", "decoration", 26, 27),
    ]


def test_progress_comes_from_the_core_events_while_the_job_runs(rig: Rig) -> None:
    def reports_then_waits(text, **kwargs):
        kwargs["progress"](ProgressEvent("inference", 2, 7))
        return rig.core.gated(text, **kwargs)

    rig.core.behave = reports_then_waits
    started = rig.start()
    job = wait_until(lambda: (j := rig.job(started)).completed_units == 2 and j)
    assert (job.status, job.stage, job.completed_units, job.total_units) == (
        "running",
        "inference",
        2,
        7,
    )
    rig.core.release.set()
    rig.wait(started, "succeeded")


def test_a_search_that_is_not_complete_ends_partial_and_not_succeeded(rig: Rig) -> None:
    rig.core.unavailable = frozenset({"cat.two"})
    started = rig.start()
    assert rig.wait(started, "succeeded", "partial").status == "partial"
    assert rig.held(started).result is not None  # a partial run keeps what it found


def test_a_partial_parse_ends_partial_even_when_every_search_finished(rig: Rig) -> None:
    started = rig.start(parsed_document(partial=True))
    assert rig.wait(started, "succeeded", "partial").status == "partial"


def test_cancelling_a_running_analysis_ends_it_with_no_result(rig: Rig) -> None:
    rig.core.behave = rig.core.hold
    started = rig.start()
    wait_until(rig.core.running.is_set)
    assert rig.queue.cancel(started.job_id) is True
    job = rig.wait(started, "cancelled")
    assert (job.error, rig.held(started).result) == (None, None)
    assert rig.core.saw_stop.is_set()


def test_cancelling_a_waiting_analysis_ends_it_at_once_and_it_never_runs(rig: Rig) -> None:
    rig.core.behave = rig.core.gated
    first = rig.start()
    wait_until(rig.core.running.is_set)
    second = rig.start()
    assert rig.job(second).status == "queued"
    assert rig.queue.cancel(second.job_id) is True
    assert rig.job(second).status == "cancelled"  # no waiting for the worker to reach it
    rig.core.release.set()
    rig.wait(first, "succeeded")
    assert [call["doc_id"] for call in rig.core.calls] == [first.document_id]


def test_cancelling_a_job_the_queue_does_not_hold_is_a_no_op(rig: Rig) -> None:
    started = rig.start()
    rig.wait(started, "succeeded")
    assert rig.queue.cancel(started.job_id) is False
    assert rig.queue.cancel("no-such-job") is False
    assert rig.job(started).status == "succeeded"


def test_an_analysis_that_outlives_the_time_limit_is_stopped_and_marked_timed_out(
    make_rig: Callable[..., Rig],
) -> None:
    rig = make_rig(analysis_timeout_seconds=0.3)
    rig.core.behave = rig.core.hold
    started = rig.start()
    job = rig.wait(started, "timed_out")
    assert (job.error, rig.held(started).result) == (None, None)
    assert rig.core.saw_stop.is_set()


def test_the_time_limit_counts_from_the_start_of_the_run_not_from_the_wait(
    make_rig: Callable[..., Rig],
) -> None:
    rig = make_rig(analysis_timeout_seconds=1.0)

    def takes_seven_tenths_of_a_second(text, **kwargs):
        end = time.monotonic() + 0.7
        while time.monotonic() < end:
            rig.core._check(kwargs["cancelled"])
            time.sleep(0.01)
        return rig.core.default(text, **kwargs)

    rig.core.behave = takes_seven_tenths_of_a_second
    first, second = rig.start(), rig.start()
    # The second one is 1.4 s old when it ends, which is over the limit of 1 s, and it still
    # succeeds because its clock started when it did.
    assert rig.wait(first, "succeeded", "timed_out").status == "succeeded"
    assert rig.wait(second, "succeeded", "timed_out").status == "succeeded"


def test_an_analyzer_that_finishes_after_it_was_told_to_stop_leaves_no_result(rig: Rig) -> None:
    def ignores_the_flag(text, *, doc_id, category_ids, cancelled, **_):
        rig.core.running.set()
        wait_until(cancelled)
        return real_result(text, doc_id, category_ids)

    rig.core.behave = ignores_the_flag
    started = rig.start()
    wait_until(rig.core.running.is_set)
    rig.queue.cancel(started.job_id)
    rig.wait(started, "cancelled")
    assert rig.held(started).result is None


def corrupt(change: Callable[[AnalysisResult, str], AnalysisResult]):
    def behave(text, *, doc_id, category_ids, **_):
        return change(real_result(text, doc_id, category_ids), doc_id)

    return behave


@pytest.mark.parametrize(
    "change",
    [
        lambda r, d: replace(r, text_sha256=text_digest("other text")),
        lambda r, d: replace(r, doc_id="another-document"),
        lambda r, d: replace(r, mode="stub"),  # fixture output must never pass as real
        lambda r, d: replace(r, artifact_manifest_sha256="not-a-digest"),
        lambda r, d: replace(r, contract_version="1.0"),
        lambda r, d: replace(r, categories=r.categories[:-1]),  # a requested category is missing
        lambda r, d: replace(
            r, categories=[*r.categories, replace(r.categories[0], category_id="x")]
        ),
        lambda r, d: replace(
            r,
            categories=[
                replace(
                    r.categories[0],
                    clauses=[
                        replace(
                            r.categories[0].clauses[0],
                            span=replace(r.categories[0].clauses[0].span, text="wrong"),
                        )
                    ],
                ),
                *r.categories[1:],
            ],
        ),
        lambda r, d: replace(
            r, categories=[replace(r.categories[0], status="found"), *r.categories[1:]]
        ),
    ],
    ids=["hash", "doc", "mode", "digest", "version", "missing", "extra", "span", "status"],
)
def test_a_result_that_fails_validation_fails_the_job_and_is_not_stored(
    rig: Rig, change: Callable[[AnalysisResult, str], AnalysisResult]
) -> None:
    rig.core.behave = corrupt(change)
    started = rig.start()
    job = rig.wait(started, "failed")
    assert job.error == "ANALYSIS_INVALID_RESULT"
    assert rig.held(started).result is None


def test_an_absent_category_on_a_partial_parse_is_refused_and_not_passed_on(rig: Rig) -> None:
    def says_absent(text, *, doc_id, category_ids, **_):
        result = real_result(text, doc_id, category_ids)
        absent = replace(
            result.categories[0],
            status="absent",
            decision_confidence=0.9,
            reason_code=None,
            unresolved_count=0,
            clauses=[],
        )
        return replace(result, categories=[absent, *result.categories[1:]])

    rig.core.behave = says_absent
    started = rig.start(parsed_document(partial=True))
    assert rig.wait(started, "failed").error == "ANALYSIS_INVALID_RESULT"
    assert rig.held(started).result is None


def test_an_analyzer_error_fails_the_job_and_its_text_reaches_no_log(
    rig: Rig, caplog: pytest.LogCaptureFixture
) -> None:
    def breaks(text, **_):
        raise RuntimeError(f"{SECRET} {text[:20]}")

    rig.core.behave = breaks
    with caplog.at_level(logging.DEBUG):
        started = rig.start()
        job = rig.wait(started, "failed")
    assert job.error == "ANALYSIS_FAILED"
    assert "RuntimeError" in caplog.text
    assert SECRET not in caplog.text
    assert MADE_UP_TEXT[:20] not in caplog.text


def test_the_worker_goes_on_to_the_next_job_after_a_failure(rig: Rig) -> None:
    def breaks(text, **_):
        raise ValueError("boom")

    rig.core.behave = breaks
    bad = rig.start()
    rig.wait(bad, "failed")
    rig.core.behave = rig.core.default
    assert rig.wait(rig.start(), "succeeded")


# --- queue -----------------------------------------------------------------------------------


def test_jobs_run_one_at_a_time_in_the_order_they_came(rig: Rig) -> None:
    rig.core.behave = rig.core.gated
    first, second, third = rig.start(), rig.start(), rig.start()
    wait_until(rig.core.running.is_set)
    assert [rig.job(s).status for s in (first, second, third)] == ["running", "queued", "queued"]
    rig.core.release.set()
    for started in (first, second, third):
        rig.wait(started, "succeeded")
    assert [call["doc_id"] for call in rig.core.calls] == [
        s.document_id for s in (first, second, third)
    ]


def test_a_full_queue_refuses_the_next_job_and_a_cancel_frees_a_place(
    make_rig: Callable[..., Rig],
) -> None:
    rig = make_rig(analysis_queue_length=1)
    rig.core.behave = rig.core.gated
    running = rig.start()
    wait_until(rig.core.running.is_set)
    waiting = rig.start()
    session = rig.store.create_session()[1]
    parsed = parsed_document()
    doc = add_parsed(rig.store, session, parsed)
    job_id, _ = rig.store.add_analysis_job(session.id, doc.id, IDS, "unspecified")
    assert rig.queue.submit(job_id, doc.id, parsed, IDS, "unspecified") is False
    rig.queue.cancel(waiting.job_id)
    assert rig.queue.submit(job_id, doc.id, parsed, IDS, "unspecified") is True
    rig.core.release.set()
    rig.wait(running, "succeeded")


def test_a_document_deleted_while_its_job_waits_is_skipped(rig: Rig) -> None:
    rig.core.behave = rig.core.gated
    first = rig.start()
    wait_until(rig.core.running.is_set)
    second = rig.start()
    rig.store.delete_document(second.session.id, second.document_id)
    rig.core.release.set()
    rig.wait(first, "succeeded")
    wait_until(lambda: rig.queue._items == {})
    assert [call["doc_id"] for call in rig.core.calls] == [first.document_id]


@pytest.mark.parametrize("how", ["document", "session"])
def test_deleting_the_document_or_the_session_mid_analysis_cancels_it(rig: Rig, how: str) -> None:
    rig.core.behave = rig.core.hold
    started = rig.start()
    wait_until(rig.core.running.is_set)
    if how == "document":
        assert rig.store.delete_document(started.session.id, started.document_id)
    else:
        rig.store.delete_session(started.session.id)
    wait_until(rig.core.saw_stop.is_set)
    wait_until(lambda: rig.queue._items == {})
    assert rig.store.get_job(started.session.id, started.job_id) is None


def test_the_next_job_runs_after_a_deleted_one_was_cancelled(rig: Rig) -> None:
    rig.core.behave = rig.core.hold
    gone = rig.start()
    wait_until(rig.core.running.is_set)
    nxt = rig.start()
    rig.core.behave = rig.core.default
    rig.store.delete_document(gone.session.id, gone.document_id)
    assert rig.wait(nxt, "succeeded")


def test_stopping_the_queue_stops_a_running_analysis(make_rig: Callable[..., Rig]) -> None:
    rig = make_rig()
    rig.core.behave = rig.core.hold
    rig.start()
    wait_until(rig.core.running.is_set)
    rig.queue.stop()
    assert rig.core.saw_stop.is_set()
    assert not rig.queue._thread.is_alive()
