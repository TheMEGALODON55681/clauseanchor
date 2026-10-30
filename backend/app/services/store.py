"""Sessions, documents and jobs: metadata in SQLite, content in RAM (D4, D5).

SQLite holds ids, a hash of each session token, timestamps, sizes, the media type and job state.
It never holds text, spans or the file name. The RAM dict holds the rest of each document, keyed
by document id.

One lock guards the single SQLite connection and the RAM dict together. Every public method takes
it, and every private helper assumes it is held. A session and everything it owns leave RAM and
SQLite in one critical section, so no reader sees one without the other.

`on_drop` hears the ids of every document that leaves, before it goes, and runs under the lock.
The parse queue uses it to kill the child of a document that is gone. A hook must not call back
into the store.
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from app.config import MAX_DOCUMENTS_PER_SESSION, MAX_SESSIONS
from app.parsing.model import ParsedDocument

# Created in code at every start. The DROPs are D4: a file path keeps no rows from an earlier run.
_SCHEMA = """
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS sessions;
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX sessions_expiry ON sessions (expires_at);
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    media_type TEXT NOT NULL,
    byte_count INTEGER NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX documents_session ON documents (session_id);
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('parse', 'analysis')),
    status TEXT NOT NULL
        CHECK (status IN ('queued', 'running', 'succeeded', 'partial', 'failed', 'cancelled')),
    error TEXT,  -- a fixed code from errors.py, never text from the file
    created_at REAL NOT NULL
);
CREATE INDEX jobs_document ON jobs (document_id);
"""


class SessionLimitError(Exception):
    """MAX_SESSIONS sessions are alive."""


class DocumentLimitError(Exception):
    """The session already holds MAX_DOCUMENTS_PER_SESSION documents."""


@dataclass(frozen=True, slots=True)
class Session:
    id: str
    expires_at: float  # seconds since the epoch, as the clock reports them


@dataclass(slots=True)
class DocumentRecord:
    """What RAM holds for one document. The file name lives here and never in SQLite."""

    id: str
    session_id: str
    expires_at: float  # the session's, copied at creation (D5)
    filename: str
    media_type: str
    byte_count: int
    status: str = "parsing"  # parsing, parsed or failed: the parse job's outcome, mirrored here
    parsed: ParsedDocument | None = None


@dataclass(frozen=True, slots=True)
class JobRecord:
    id: str
    document_id: str
    kind: str
    status: str
    error: str | None


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Store:
    def __init__(
        self,
        db_path: str = ":memory:",
        *,
        ttl_seconds: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._documents: dict[str, DocumentRecord] = {}
        self.on_drop: Callable[[list[str]], None] = lambda ids: None
        # One connection for the life of the app, because every :memory: connection is its own
        # database. It is shared across threads, so the lock above serialises its use.
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def ping(self) -> bool:
        try:
            with self._lock:
                self._db.execute("SELECT 1")
        except sqlite3.Error:
            return False
        return True

    def create_session(self) -> tuple[str, Session]:
        """Returns the token, which exists nowhere else, and the session."""
        token = secrets.token_urlsafe(32)
        with self._lock:
            now = self._clock()
            (live,) = self._db.execute(
                "SELECT count(*) FROM sessions WHERE expires_at > ?", (now,)
            ).fetchone()
            if live >= MAX_SESSIONS:
                raise SessionLimitError
            # Fixed at creation: no lookup moves it, so the 60-minute promise holds.
            session = Session(str(uuid.uuid4()), now + self._ttl)
            with self._db:
                self._db.execute(
                    "INSERT INTO sessions (id, token_hash, created_at, expires_at)"
                    " VALUES (?, ?, ?, ?)",
                    (session.id, _digest(token), now, session.expires_at),
                )
        return token, session

    def get_session(self, token: str) -> Session | None:
        # The lookup is by hash, so the stored value is not the credential and its position in an
        # index tells an attacker nothing about the token.
        with self._lock:
            row = self._db.execute(
                "SELECT id, expires_at FROM sessions WHERE token_hash = ?", (_digest(token),)
            ).fetchone()
            if row is None:
                return None
            if row[1] <= self._clock():
                self._drop_session(row[0])
                return None
            return Session(*row)

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            self._drop_session(session_id)

    def add_document(
        self, session_id: str, *, filename: str, media_type: str, byte_count: int
    ) -> DocumentRecord | None:
        """None when the session is gone. Raises DocumentLimitError when it is full."""
        with self._lock:
            now = self._clock()
            row = self._db.execute(
                "SELECT expires_at FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                return None
            if row[0] <= now:
                self._drop_session(session_id)
                return None
            (held,) = self._db.execute(
                "SELECT count(*) FROM documents WHERE session_id = ?", (session_id,)
            ).fetchone()
            if held >= MAX_DOCUMENTS_PER_SESSION:
                raise DocumentLimitError
            doc = DocumentRecord(
                str(uuid.uuid4()), session_id, row[0], filename, media_type, byte_count
            )
            with self._db:
                self._db.execute(
                    "INSERT INTO documents"
                    " (id, session_id, media_type, byte_count, created_at, expires_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (doc.id, session_id, media_type, byte_count, now, doc.expires_at),
                )
            self._documents[doc.id] = doc
            return doc

    def get_document(self, session_id: str, document_id: str) -> DocumentRecord | None:
        """The document if this session owns it and it has not expired, else None."""
        with self._lock:
            doc = self._live_document(document_id, self._clock())
            return doc if doc is not None and doc.session_id == session_id else None

    def delete_document(self, session_id: str, document_id: str) -> bool:
        """False when this session has no such document. Its job rows go with it."""
        with self._lock:
            doc = self._live_document(document_id, self._clock())
            if doc is None or doc.session_id != session_id:
                return False
            self.on_drop([document_id])
            del self._documents[document_id]
            with self._db:
                # ON DELETE CASCADE takes the jobs
                self._db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            return True

    def add_job(self, document_id: str, kind: str) -> str | None:
        """A queued job row. None when the document is gone."""
        with self._lock:
            now = self._clock()
            if self._live_document(document_id, now) is None:
                return None
            job_id = str(uuid.uuid4())
            with self._db:
                self._db.execute(
                    "INSERT INTO jobs (id, document_id, kind, status, created_at)"
                    " VALUES (?, ?, ?, 'queued', ?)",
                    (job_id, document_id, kind, now),
                )
            return job_id

    def get_job(self, session_id: str, job_id: str) -> JobRecord | None:
        """The job if this session owns its document and the document has not expired."""
        with self._lock:
            row = self._db.execute(
                "SELECT id, document_id, kind, status, error FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if row is None:
                return None
            doc = self._live_document(row[1], self._clock())
            return JobRecord(*row) if doc is not None and doc.session_id == session_id else None

    def start_job(self, job_id: str) -> bool:
        """Queued to running. False when the job is gone with its document, or is not queued."""
        with self._lock, self._db:
            changed = self._db.execute(
                "UPDATE jobs SET status = 'running' WHERE id = ? AND status = 'queued'", (job_id,)
            )
            return changed.rowcount == 1

    def finish_job(
        self, job_id: str, *, parsed: ParsedDocument | None = None, error: str | None = None
    ) -> None:
        """Records a parse result or a failure code. Nothing happens when the document is gone,
        so a parse that finishes after its document was deleted leaves no trace."""
        if (parsed is None) == (error is None):
            raise ValueError("a job finishes with a result or an error code")
        with self._lock:
            row = self._db.execute(
                "SELECT document_id FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            doc = None if row is None else self._documents.get(row[0])
            if doc is None:
                return
            with self._db:
                self._db.execute(
                    "UPDATE jobs SET status = ?, error = ? WHERE id = ?",
                    ("failed" if error else "succeeded", error, job_id),
                )
            doc.parsed, doc.status = parsed, "failed" if error else "parsed"

    def sweep(self) -> int:
        """Deletes every expired session and what it owns. Returns how many sessions went."""
        with self._lock:
            expired = [
                row[0]
                for row in self._db.execute(
                    "SELECT id FROM sessions WHERE expires_at <= ?", (self._clock(),)
                )
            ]
            for session_id in expired:
                self._drop_session(session_id)
            return len(expired)

    def _live_document(self, document_id: str, now: float) -> DocumentRecord | None:
        doc = self._documents.get(document_id)
        if doc is not None and doc.expires_at <= now:
            self._drop_session(doc.session_id)
            return None
        return doc

    def _drop_session(self, session_id: str) -> None:
        ids = [
            row[0]
            for row in self._db.execute(
                "SELECT id FROM documents WHERE session_id = ?", (session_id,)
            )
        ]
        if ids:
            self.on_drop(ids)
        # RAM first, so the content is gone even if the SQLite delete fails
        for document_id in ids:
            self._documents.pop(document_id, None)
        with self._db:
            # ON DELETE CASCADE takes the documents and, through them, the jobs
            self._db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
