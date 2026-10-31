"""The document and job half of the Store that 2-C fills: delete, job state, results, drop hook."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import closing

import pytest

from app.config import MAX_DOCUMENTS_PER_SESSION
from app.parsing import ParsedDocument, parse_document
from app.services.store import DocumentLimitError, Store
from tests.synthetic import FakeClock

TTL = 3600


@pytest.fixture
def store(clock: FakeClock) -> Iterator[Store]:
    with closing(Store(ttl_seconds=TTL, clock=clock)) as s:
        yield s


@pytest.fixture
def parsed(fixture_bytes: dict[str, bytes]) -> ParsedDocument:
    return parse_document(fixture_bytes["simple.pdf"])


def new_doc(store: Store):
    _, session = store.create_session()
    doc = store.add_document(
        session.id, filename="a.pdf", media_type="application/pdf", byte_count=10
    )
    assert doc is not None
    job_id = store.add_job(doc.id, "parse")
    assert job_id is not None
    return session, doc, job_id


def rows(store: Store, table: str) -> int:
    with store._lock:
        return store._db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_a_new_document_is_parsing_and_keeps_its_metadata(store: Store) -> None:
    session, doc, _ = new_doc(store)
    held = store.get_document(session.id, doc.id)
    assert (held.status, held.media_type, held.byte_count, held.parsed) == (
        "parsing",
        "application/pdf",
        10,
        None,
    )


def test_a_job_runs_then_succeeds_with_its_result(store: Store, parsed: ParsedDocument) -> None:
    session, doc, job_id = new_doc(store)
    assert store.get_job(session.id, job_id).status == "queued"
    assert store.start_job(job_id) is True
    assert store.get_job(session.id, job_id).status == "running"
    store.finish_job(job_id, parsed=parsed)
    job = store.get_job(session.id, job_id)
    assert (job.status, job.error, job.kind, job.document_id) == (
        "succeeded",
        None,
        "parse",
        doc.id,
    )
    held = store.get_document(session.id, doc.id)
    assert held.status == "parsed"
    assert held.parsed is parsed


def test_a_job_can_fail_with_a_code(store: Store) -> None:
    session, doc, job_id = new_doc(store)
    store.start_job(job_id)
    store.finish_job(job_id, error="MALFORMED_FILE")
    job = store.get_job(session.id, job_id)
    assert (job.status, job.error) == ("failed", "MALFORMED_FILE")
    held = store.get_document(session.id, doc.id)
    assert (held.status, held.parsed) == ("failed", None)


def test_a_job_finishes_with_a_result_or_a_code_and_never_both(
    store: Store, parsed: ParsedDocument
) -> None:
    session, _, job_id = new_doc(store)
    store.start_job(job_id)
    with pytest.raises(ValueError):
        store.finish_job(job_id)
    with pytest.raises(ValueError):
        store.finish_job(job_id, parsed=parsed, error="MALFORMED_FILE")
    assert store.get_job(session.id, job_id).status == "running"


def test_only_a_queued_job_starts(store: Store) -> None:
    _, _, job_id = new_doc(store)
    assert store.start_job(job_id) is True
    assert store.start_job(job_id) is False
    assert store.start_job("no-such-job") is False


def test_a_result_for_a_deleted_document_is_dropped(store: Store, parsed: ParsedDocument) -> None:
    session, doc, job_id = new_doc(store)
    store.start_job(job_id)
    assert store.delete_document(session.id, doc.id) is True
    store.finish_job(job_id, parsed=parsed)
    assert store.get_document(session.id, doc.id) is None
    assert store.get_job(session.id, job_id) is None
    assert (rows(store, "documents"), rows(store, "jobs")) == (0, 0)


def test_delete_document_removes_the_ram_record_and_both_rows(store: Store) -> None:
    session, doc, _ = new_doc(store)
    assert store.delete_document(session.id, doc.id) is True
    with store._lock:
        assert doc.id not in store._documents
    assert (rows(store, "documents"), rows(store, "jobs")) == (0, 0)
    assert store.delete_document(session.id, doc.id) is False


def test_delete_document_frees_a_slot_and_keeps_the_session(store: Store) -> None:
    session, first, _ = new_doc(store)
    for _ in range(MAX_DOCUMENTS_PER_SESSION - 1):
        store.add_document(session.id, filename="b.pdf", media_type="application/pdf", byte_count=1)
    with pytest.raises(DocumentLimitError):
        store.add_document(session.id, filename="c.pdf", media_type="application/pdf", byte_count=1)
    store.delete_document(session.id, first.id)
    assert rows(store, "sessions") == 1
    assert store.add_document(
        session.id, filename="c.pdf", media_type="application/pdf", byte_count=1
    )


def test_another_sessions_document_and_job_look_missing(store: Store) -> None:
    _, doc, job_id = new_doc(store)
    _, other = store.create_session()
    assert store.get_job(other.id, job_id) is None
    assert store.get_document(other.id, doc.id) is None
    assert store.delete_document(other.id, doc.id) is False
    assert rows(store, "documents") == 1


def test_a_job_of_an_expired_session_is_gone(store: Store, clock: FakeClock) -> None:
    session, _, job_id = new_doc(store)
    clock.advance(TTL)
    assert store.get_job(session.id, job_id) is None
    assert (rows(store, "sessions"), rows(store, "documents"), rows(store, "jobs")) == (0, 0, 0)


def test_the_drop_hook_hears_every_way_a_document_can_go(store: Store, clock: FakeClock) -> None:
    heard: list[list[str]] = []
    store.on_drop = lambda ids: heard.append(sorted(ids))

    session, doc, _ = new_doc(store)
    store.delete_document(session.id, doc.id)
    assert heard == [[doc.id]]

    session, doc2, _ = new_doc(store)
    store.delete_session(session.id)
    assert heard[-1] == [doc2.id]

    session, doc3, _ = new_doc(store)
    clock.advance(TTL)
    store.sweep()
    assert heard[-1] == [doc3.id]

    session, doc4, job_id = new_doc(store)
    clock.advance(TTL)
    assert store.get_job(session.id, job_id) is None  # the lazy path
    assert heard[-1] == [doc4.id]


def test_the_drop_hook_is_not_called_for_a_session_without_documents(store: Store) -> None:
    heard: list[list[str]] = []
    store.on_drop = lambda ids: heard.append(list(ids))
    _, session = store.create_session()
    store.delete_session(session.id)
    assert heard == []
