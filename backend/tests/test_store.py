from __future__ import annotations

import base64
import hashlib
import sqlite3
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest

from app.config import MAX_DOCUMENTS_PER_SESSION, MAX_SESSIONS
from app.services.store import DocumentLimitError, SessionLimitError, Store
from tests.synthetic import FakeClock

TTL = 3600
TABLES = ("sessions", "documents", "jobs")


@pytest.fixture
def store(clock: FakeClock) -> Iterator[Store]:
    with closing(Store(ttl_seconds=TTL, clock=clock)) as s:
        yield s


def column(store: Store, table: str, name: str) -> list:
    """White-box read of one SQLite column, under the store's own lock."""
    with store._lock:
        return [r[0] for r in store._db.execute(f"SELECT {name} FROM {table}")]


def ram_ids(store: Store) -> set[str]:
    with store._lock:
        return set(store._documents)


def dump(store: Store) -> str:
    with store._lock:
        return "\n".join(store._db.iterdump())


def add_doc(store: Store, session_id: str, name: str = "a.pdf"):
    doc = store.add_document(session_id, filename=name, media_type="application/pdf", byte_count=10)
    assert doc is not None
    return doc


def test_the_token_is_32_random_bytes_in_url_safe_text(store: Store) -> None:
    token, _ = store.create_session()
    assert len(base64.urlsafe_b64decode(token + "=")) == 32


def test_each_session_gets_a_new_token_and_id(store: Store) -> None:
    (t1, s1), (t2, s2) = store.create_session(), store.create_session()
    assert t1 != t2
    assert s1.id != s2.id


def test_sqlite_holds_the_sha256_of_the_token_and_never_the_token(store: Store) -> None:
    token, session = store.create_session()
    assert column(store, "sessions", "id") == [session.id]
    assert column(store, "sessions", "token_hash") == [hashlib.sha256(token.encode()).hexdigest()]
    assert token not in dump(store)


def test_the_session_object_does_not_carry_the_token(store: Store) -> None:
    token, session = store.create_session()
    found = store.get_session(token)
    assert found == session
    assert token not in repr(found)


def test_an_unknown_token_finds_no_session(store: Store) -> None:
    store.create_session()
    assert store.get_session("A" * 43) is None


def test_expiry_is_fixed_at_creation_and_a_lookup_does_not_extend_it(
    store: Store, clock: FakeClock
) -> None:
    created = clock()
    token, session = store.create_session()
    assert session.expires_at == created + TTL
    clock.advance(TTL - 1)
    found = store.get_session(token)
    assert found is not None
    assert found.expires_at == created + TTL
    assert column(store, "sessions", "expires_at") == [created + TTL]


def test_a_session_works_one_tick_before_expiry_and_is_gone_at_expiry(
    store: Store, clock: FakeClock
) -> None:
    token, session = store.create_session()
    clock.now = session.expires_at - 0.001
    assert store.get_session(token) is not None
    assert len(column(store, "sessions", "id")) == 1
    clock.now = session.expires_at
    assert store.get_session(token) is None
    assert column(store, "sessions", "id") == []


def test_the_documents_expires_at_is_the_sessions(store: Store, clock: FakeClock) -> None:
    _, session = store.create_session()
    clock.advance(600)  # a document made later still ends with its session, not an hour on
    doc = add_doc(store, session.id)
    assert doc.expires_at == session.expires_at
    assert column(store, "documents", "expires_at") == [session.expires_at]


def test_a_document_is_found_by_its_owner_and_not_by_another_session(store: Store) -> None:
    _, mine = store.create_session()
    _, other = store.create_session()
    doc = add_doc(store, mine.id)
    assert store.get_document(mine.id, doc.id) is doc
    assert store.get_document(other.id, doc.id) is None
    assert ram_ids(store) == {doc.id}


def test_lazy_expiry_deletes_a_document_and_its_session_on_access(
    store: Store, clock: FakeClock
) -> None:
    _, session = store.create_session()
    doc = add_doc(store, session.id)
    assert store.add_job(doc.id, "parse") is not None
    clock.now = session.expires_at - 0.001
    assert store.get_document(session.id, doc.id) is doc
    clock.now = session.expires_at
    assert store.get_document(session.id, doc.id) is None
    assert [column(store, t, "id") for t in TABLES] == [[], [], []]
    assert ram_ids(store) == set()


def test_adding_to_a_gone_session_returns_none(store: Store, clock: FakeClock) -> None:
    _, session = store.create_session()
    clock.now = session.expires_at
    assert store.add_document(session.id, filename="a", media_type="m", byte_count=1) is None
    assert store.add_document("unknown", filename="a", media_type="m", byte_count=1) is None
    assert column(store, "sessions", "id") == []


def test_adding_a_job_to_a_gone_document_returns_none(store: Store, clock: FakeClock) -> None:
    _, session = store.create_session()
    doc = add_doc(store, session.id)
    clock.now = session.expires_at
    assert store.add_job(doc.id, "parse") is None
    assert store.add_job("unknown", "parse") is None
    assert column(store, "jobs", "id") == []


def test_the_file_name_stays_in_ram_and_not_in_sqlite(store: Store) -> None:
    _, session = store.create_session()
    doc = add_doc(store, session.id, name="payroll-acme-final.docx")
    assert store.get_document(session.id, doc.id).filename == "payroll-acme-final.docx"
    assert "payroll-acme-final" not in dump(store)


def test_delete_removes_the_session_its_documents_and_its_jobs_from_ram_and_sqlite(
    store: Store,
) -> None:
    token, session = store.create_session()
    _, other = store.create_session()
    mine = add_doc(store, session.id)
    theirs = add_doc(store, other.id)
    store.add_job(mine.id, "parse")
    kept_job = store.add_job(theirs.id, "parse")

    store.delete_session(session.id)

    assert store.get_session(token) is None
    assert column(store, "sessions", "id") == [other.id]
    assert column(store, "documents", "id") == [theirs.id]
    assert column(store, "jobs", "id") == [kept_job]
    assert ram_ids(store) == {theirs.id}


def test_the_sweep_removes_expired_sessions_and_all_they_own_with_no_request(
    store: Store, clock: FakeClock
) -> None:
    _, old = store.create_session()
    old_doc = add_doc(store, old.id)
    store.add_job(old_doc.id, "parse")
    clock.advance(1800)
    _, young = store.create_session()
    young_doc = add_doc(store, young.id)
    young_job = store.add_job(young_doc.id, "parse")

    clock.now = old.expires_at
    assert store.sweep() == 1

    assert column(store, "sessions", "id") == [young.id]
    assert column(store, "documents", "id") == [young_doc.id]
    assert column(store, "jobs", "id") == [young_job]
    assert ram_ids(store) == {young_doc.id}
    assert store.sweep() == 0


def test_the_session_limit_counts_only_live_sessions(store: Store, clock: FakeClock) -> None:
    for _ in range(MAX_SESSIONS):
        store.create_session()
    with pytest.raises(SessionLimitError):
        store.create_session()
    clock.advance(TTL)
    store.create_session()


def test_the_document_limit_is_per_session(store: Store) -> None:
    _, a = store.create_session()
    _, b = store.create_session()
    for _ in range(MAX_DOCUMENTS_PER_SESSION):
        add_doc(store, a.id)
    with pytest.raises(DocumentLimitError):
        add_doc(store, a.id)
    add_doc(store, b.id)


def test_a_file_path_starts_with_empty_tables_even_if_rows_were_there(
    tmp_path: Path, clock: FakeClock
) -> None:
    path = str(tmp_path / "meta.db")
    with closing(Store(path, ttl_seconds=TTL, clock=clock)) as first:
        token, session = first.create_session()
        doc = add_doc(first, session.id)
        first.add_job(doc.id, "parse")
    raw = Path(path).read_bytes()
    assert token.encode() not in raw
    with closing(sqlite3.connect(path)) as peek:
        assert peek.execute("SELECT count(*) FROM sessions").fetchone() == (1,)

    with closing(Store(path, ttl_seconds=TTL, clock=clock)) as second:
        assert [column(second, t, "id") for t in TABLES] == [[], [], []]


def test_memory_is_the_default_database(store: Store) -> None:
    with store._lock:
        assert store._db.execute("PRAGMA database_list").fetchone()[2] == ""


def test_the_store_can_be_used_from_another_thread(store: Store) -> None:
    with ThreadPoolExecutor(1) as pool:
        token, _ = pool.submit(store.create_session).result()
    assert store.get_session(token) is not None


@pytest.mark.parametrize(
    "call",
    [
        lambda s: s.create_session(),
        lambda s: s.get_session("t"),
        lambda s: s.delete_session("s"),
        lambda s: s.add_document("s", filename="f", media_type="m", byte_count=1),
        lambda s: s.get_document("s", "d"),
        lambda s: s.add_job("d", "parse"),
        lambda s: s.sweep(),
        lambda s: s.ping(),
    ],
    ids=[
        "create_session",
        "get_session",
        "delete_session",
        "add_document",
        "get_document",
        "add_job",
        "sweep",
        "ping",
    ],
)
def test_every_public_call_waits_for_the_lock(
    store: Store, call: Callable[[Store], object]
) -> None:
    with ThreadPoolExecutor(1) as pool:
        with store._lock:
            future = pool.submit(call, store)
            with pytest.raises(TimeoutError):
                future.result(timeout=0.05)
        future.result(timeout=5)


def test_ping_is_true_until_the_store_is_closed(clock: FakeClock) -> None:
    s = Store(ttl_seconds=TTL, clock=clock)
    assert s.ping() is True
    s.close()
    assert s.ping() is False
