"""The analysis half of the Store: job rows with progress, the result in RAM, one at a time."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import closing

import pytest

from app.services.store import AnalysisActiveError, Store
from tests.synthetic import FakeClock

IDS = ("a.one", "a.two")
RESULT = object()  # the store keeps a result as it is and reads nothing in it


@pytest.fixture
def store(clock: FakeClock) -> Iterator[Store]:
    with closing(Store(ttl_seconds=3600, clock=clock)) as s:
        yield s


def new_session(store: Store):
    return store.create_session()[1]


def new_doc(store: Store, session=None):
    session = session or new_session(store)
    doc = store.add_document(
        session.id, filename="a.pdf", media_type="application/pdf", byte_count=10
    )
    assert doc is not None
    return session, doc


def start(store: Store, session, doc, scope: str = "unspecified"):
    started = store.add_analysis_job(session.id, doc.id, IDS, scope)
    assert started is not None
    return started


def test_an_analysis_job_starts_queued_with_its_own_ids_and_a_record_in_ram(store: Store) -> None:
    session, doc = new_doc(store)
    job_id, analysis_id = start(store, session, doc, "india_review")
    assert job_id != analysis_id
    job = store.get_job(session.id, job_id)
    assert (job.kind, job.status, job.error, job.analysis_id) == (
        "analysis",
        "queued",
        None,
        analysis_id,
    )
    assert (job.stage, job.completed_units, job.total_units, job.finished_at) == (
        None,
        0,
        None,
        None,
    )
    record = store.get_document(session.id, doc.id).analysis
    assert (record.analysis_id, record.job_id, record.category_ids) == (analysis_id, job_id, IDS)
    assert (record.jurisdiction_scope, record.result) == ("india_review", None)


def test_a_parse_job_has_no_analysis_id(store: Store) -> None:
    session, doc = new_doc(store)
    job_id = store.add_job(doc.id, "parse")
    assert store.get_job(session.id, job_id).analysis_id is None


def test_nothing_starts_for_a_stranger_or_an_unknown_document(store: Store) -> None:
    session, doc = new_doc(store)
    other = new_session(store)
    assert store.add_analysis_job(other.id, doc.id, IDS, "unspecified") is None
    assert store.add_analysis_job(session.id, "no-such-id", IDS, "unspecified") is None


def test_a_session_runs_one_analysis_at_a_time_across_its_documents(store: Store) -> None:
    session, first = new_doc(store)
    _, second = new_doc(store, session)
    job_id, _ = start(store, session, first)
    with pytest.raises(AnalysisActiveError):
        store.add_analysis_job(session.id, second.id, IDS, "unspecified")
    store.start_job(job_id)
    with pytest.raises(AnalysisActiveError):  # running counts too
        store.add_analysis_job(session.id, first.id, IDS, "unspecified")
    store.finish_analysis(job_id, status="cancelled")
    assert store.add_analysis_job(session.id, second.id, IDS, "unspecified") is not None


def test_another_session_is_not_held_up(store: Store) -> None:
    session, doc = new_doc(store)
    start(store, session, doc)
    other, other_doc = new_doc(store)
    assert store.add_analysis_job(other.id, other_doc.id, IDS, "unspecified") is not None


def test_a_new_analysis_replaces_the_previous_one_of_the_document(store: Store) -> None:
    session, doc = new_doc(store)
    job_id, first = start(store, session, doc)
    store.start_job(job_id)
    store.finish_analysis(job_id, status="succeeded", result=RESULT)
    assert store.get_analysis(session.id, first)[1].analysis.result is RESULT
    _, second = start(store, session, doc)
    assert store.get_analysis(session.id, first) is None
    assert store.get_analysis(session.id, second)[1].analysis.result is None


def test_progress_is_recorded_only_while_the_job_runs(store: Store) -> None:
    session, doc = new_doc(store)
    job_id, _ = start(store, session, doc)
    store.set_progress(job_id, "inference", 1, 4)
    assert store.get_job(session.id, job_id).stage is None  # still queued
    store.start_job(job_id)
    store.set_progress(job_id, "inference", 3, 4)
    job = store.get_job(session.id, job_id)
    assert (job.stage, job.completed_units, job.total_units) == ("inference", 3, 4)
    store.finish_analysis(job_id, status="partial", result=RESULT)
    store.set_progress(job_id, "inference", 4, 4)
    assert store.get_job(session.id, job_id).completed_units == 3


@pytest.mark.parametrize("status", ["succeeded", "partial"])
def test_a_finished_analysis_keeps_its_result_and_its_finish_time(
    store: Store, clock: FakeClock, status: str
) -> None:
    session, doc = new_doc(store)
    job_id, analysis_id = start(store, session, doc)
    store.start_job(job_id)
    clock.advance(42)
    assert store.finish_analysis(job_id, status=status, result=RESULT) is True
    job, held = store.get_analysis(session.id, analysis_id)
    assert (job.status, job.error, job.finished_at) == (status, None, clock())
    assert job.created_at == clock() - 42
    assert held.analysis.result is RESULT


@pytest.mark.parametrize(
    ("status", "error"),
    [("failed", "ANALYSIS_FAILED"), ("cancelled", None), ("timed_out", None)],
)
def test_a_stopped_or_failed_analysis_keeps_no_result(
    store: Store, status: str, error: str | None
) -> None:
    session, doc = new_doc(store)
    job_id, analysis_id = start(store, session, doc)
    store.start_job(job_id)
    assert store.finish_analysis(job_id, status=status, error=error) is True
    job, held = store.get_analysis(session.id, analysis_id)
    assert (job.status, job.error) == (status, error)
    assert held.analysis.result is None


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "succeeded"},  # a finished job needs its result
        {"status": "succeeded", "result": RESULT, "error": "ANALYSIS_FAILED"},
        {"status": "failed", "result": RESULT, "error": "ANALYSIS_FAILED"},
        {"status": "failed"},  # a failure needs its code
        {"status": "cancelled", "error": "ANALYSIS_FAILED"},
        {"status": "running"},  # not an end state
    ],
)
def test_a_finish_that_contradicts_itself_is_refused(store: Store, bad: dict) -> None:
    session, doc = new_doc(store)
    job_id, _ = start(store, session, doc)
    with pytest.raises(ValueError):
        store.finish_analysis(job_id, **bad)


def test_a_job_that_has_ended_cannot_be_ended_again(store: Store) -> None:
    session, doc = new_doc(store)
    job_id, _ = start(store, session, doc)
    store.start_job(job_id)
    assert store.finish_analysis(job_id, status="cancelled") is True
    assert store.finish_analysis(job_id, status="succeeded", result=RESULT) is False
    assert store.get_job(session.id, job_id).status == "cancelled"
    assert store.get_document(session.id, doc.id).analysis.result is None


def test_a_waiting_job_can_be_cancelled_before_it_runs(store: Store) -> None:
    session, doc = new_doc(store)
    job_id, _ = start(store, session, doc)
    assert store.finish_analysis(job_id, status="cancelled") is True
    assert store.start_job(job_id) is False  # the worker then skips it


def test_a_finish_after_the_document_is_deleted_leaves_no_trace(store: Store) -> None:
    session, doc = new_doc(store)
    job_id, analysis_id = start(store, session, doc)
    store.start_job(job_id)
    store.delete_document(session.id, doc.id)
    assert store.finish_analysis(job_id, status="succeeded", result=RESULT) is False
    assert store.get_analysis(session.id, analysis_id) is None
    assert store.get_job(session.id, job_id) is None


def test_an_analysis_is_visible_to_its_own_session_only(store: Store) -> None:
    session, doc = new_doc(store)
    _, analysis_id = start(store, session, doc)
    assert store.get_analysis(session.id, analysis_id) is not None
    assert store.get_analysis(new_session(store).id, analysis_id) is None
    assert store.get_analysis(session.id, "no-such-id") is None


def test_an_expired_session_takes_its_analysis_with_it(store: Store, clock: FakeClock) -> None:
    session, doc = new_doc(store)
    _, analysis_id = start(store, session, doc)
    clock.advance(3601)
    assert store.get_analysis(session.id, analysis_id) is None


def test_deleting_a_job_row_clears_the_record_for_a_rolled_back_start(store: Store) -> None:
    session, doc = new_doc(store)
    job_id, analysis_id = start(store, session, doc)
    store.delete_job(job_id)
    assert store.get_job(session.id, job_id) is None
    assert store.get_analysis(session.id, analysis_id) is None
    assert store.get_document(session.id, doc.id).analysis is None
    assert store.add_analysis_job(session.id, doc.id, IDS, "unspecified") is not None


def test_the_drop_hook_hears_a_document_with_an_analysis(store: Store) -> None:
    session, doc = new_doc(store)
    start(store, session, doc)
    heard: list[list[str]] = []
    store.on_drop = lambda ids: heard.append(list(ids))
    store.delete_session(session.id)
    assert heard == [[doc.id]]
