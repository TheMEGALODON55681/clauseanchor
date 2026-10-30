"""The parse queue: a bounded queue in the app process, one worker thread, one child per parse.

Each upload's bytes wait here in RAM, and the worker sends them to a child process
(`app.parse_worker`) over stdin. The child gets a memory cap and a wall-clock kill, and it runs
exactly one parse. The parent rebuilds the ParsedDocument from the JSON the child writes and hands
it to the store. Nothing is written to disk, and the child's stderr is discarded.

Lock order: the store's lock, then this one. The worker never holds this lock while it calls the
store, and the store's `on_drop` hook (`kill_documents`) takes this lock and nothing else.
"""

from __future__ import annotations

import contextlib
import json
import logging
import queue
import sys
import threading
from dataclasses import dataclass

from app.config import Settings
from app.parsing.errors import ErrorCode
from app.parsing.model import ParsedDocument
from app.parsing.schema import from_json
from app.services.memcap import CappedProcess
from app.services.store import Store

log = logging.getLogger("clauseanchor.api")

WORKER_ARGS = [sys.executable, "-m", "app.parse_worker"]  # tests swap this for stand-in children
# The codes a child may report: the parser's, bar the three that stop at the upload (the child
# reads the same bytes the upload checked), and the one a MemoryError gives
_UPLOAD_CODES = {"EMPTY_FILE", "FILE_TOO_LARGE", "UNSUPPORTED_TYPE"}
CHILD_CODES = frozenset(code.value for code in ErrorCode) - _UPLOAD_CODES | {"PARSE_MEMORY_LIMIT"}
# A child that came this close to its cap may have had an allocation refused
CAP_HIT_SHARE = 0.95


@dataclass(slots=True)
class _Item:
    job_id: str
    document_id: str
    data: bytes | None  # None once the document is gone, so its bytes do not outlive it
    capped: CappedProcess | None = None
    stopped_by: str | None = None  # "timeout", "gone" or "shutdown"


class ParseQueue:
    def __init__(self, store: Store, settings: Settings) -> None:
        self._store = store
        self._kill_seconds = settings.parse_kill_seconds
        self._memory_bytes = settings.parse_memory_mib * 1024 * 1024
        self._queue: queue.Queue[_Item | None] = queue.Queue(maxsize=settings.parse_queue_length)
        self._items: dict[str, _Item] = {}  # by document id, from submit until its parse is over
        self._lock = threading.Lock()
        self._closing = False
        self._thread = threading.Thread(target=self._work, name="parse-worker", daemon=True)
        store.on_drop = self.kill_documents

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        """Kills the running child and waits for it and for the worker thread."""
        with self._lock:
            self._closing = True
            for item in self._items.values():
                self._halt(item, "shutdown")
        with contextlib.suppress(queue.Full):
            self._queue.put_nowait(None)  # wakes an idle worker. A busy one checks the flag
        if self._thread.is_alive():
            self._thread.join(timeout=30)

    def submit(self, document_id: str, job_id: str, data: bytes) -> bool:
        """Queues one parse. False when `parse_queue_length` parses are already waiting."""
        item = _Item(job_id, document_id, data)
        with self._lock:
            self._items[document_id] = item  # before the put, so the worker finds it
            try:
                self._queue.put_nowait(item)
            except queue.Full:
                del self._items[document_id]
                return False
        return True

    def kill_documents(self, document_ids: list[str]) -> None:
        """The store's `on_drop` hook. It runs under the store's lock. A waiting job loses its
        bytes, and a running one loses its child, which has exited when this returns."""
        children = []
        with self._lock:
            for document_id in document_ids:
                item = self._items.get(document_id)
                if item is not None:
                    self._halt(item, "gone")
                    if item.capped is not None:
                        children.append(item.capped)
        for child in children:
            child.wait(5)

    def _halt(self, item: _Item, reason: str) -> None:
        """Marks the job stopped, drops its bytes and kills its child. The caller holds the lock."""
        if item.stopped_by is None:
            item.stopped_by = reason
        item.data = None
        if item.capped is not None:
            item.capped.kill()

    def _stop_for_time(self, item: _Item) -> None:
        with self._lock:
            if item.stopped_by is None:
                self._halt(item, "timeout")

    def _work(self) -> None:
        while (item := self._queue.get()) is not None and not self._closing:
            try:
                self._run(item)
            except Exception as error:
                # One bad job must not end the worker. Log the class name only (Rules section 5).
                log.error("parse job failed: %s", type(error).__name__)
                self._fail(item)
            finally:
                with self._lock:
                    self._items.pop(item.document_id, None)
                item.data = None

    def _fail(self, item: _Item) -> None:
        try:
            self._store.finish_job(item.job_id, error="PARSE_FAILED")
        except Exception as error:
            log.error("parse job could not be recorded: %s", type(error).__name__)

    def _run(self, item: _Item) -> None:
        with self._lock:
            data = item.data
        if data is None or not self._store.start_job(item.job_id):
            return  # the document was deleted while it waited
        with self._lock:
            if item.stopped_by is not None:
                return  # deleted between the check above and now
            item.data = None
            item.capped = CappedProcess(WORKER_ARGS, self._memory_bytes)
        capped = item.capped
        timer = threading.Timer(self._kill_seconds, self._stop_for_time, (item,))
        timer.daemon = True
        timer.start()
        try:
            # The child joined its cap before this first byte, and the timer ends it if it never
            # reads: a write to a child that does not read would otherwise block for ever.
            out, _ = capped.popen.communicate(data)
        finally:
            timer.cancel()
            capped.kill()  # a no-op once the child is gone, and the end of it if communicate broke
            capped.wait(5)
            peak = capped.peak_bytes()
            with self._lock:
                item.capped = None  # so kill_documents cannot reach the job once it is closed
            capped.close()
        if item.stopped_by in ("gone", "shutdown"):
            return  # the document is gone or the app is closing, so there is nobody to tell
        if item.stopped_by == "timeout":
            self._store.finish_job(item.job_id, error="PARSE_TIMEOUT")
            return
        parsed, error = self._read(out, capped.popen.returncode, peak)
        self._store.finish_job(item.job_id, parsed=parsed, error=error)

    def _read(
        self, out: bytes, returncode: int, peak: int | None
    ) -> tuple[ParsedDocument | None, str | None]:
        # lxml turns a refused allocation into a read error and a library can swallow one, so
        # the child's own code is not trusted once it came near its cap.
        if peak is not None and peak >= CAP_HIT_SHARE * self._memory_bytes:
            return None, "PARSE_MEMORY_LIMIT"
        if returncode != 0:
            return None, "PARSE_FAILED"
        try:
            result = json.loads(out)
            if "error" in result:
                code = result["error"]
                return None, code if code in CHILD_CODES else "PARSE_FAILED"
            return from_json(result["document"]), None
        except (ValueError, KeyError, TypeError):
            return None, "PARSE_FAILED"
