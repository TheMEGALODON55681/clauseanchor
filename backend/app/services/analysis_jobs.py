"""The analysis queue: one worker thread, a FIFO with a named limit, and the one analyzer.

The worker thread loads the analyzer first (about 25 s for the real model), so the app answers
`/health` and `/ready` meanwhile, and then feeds the analyzer one job at a time. The core
serializes calls per instance and raises a busy error on concurrent ones, so one worker is the rule.

A job stops when someone sets `stopped_by`: a cancel, the time limit, a delete or a shutdown. The
core reads it through its `cancelled` callback between units and raises `AnalysisCancelled`. It
cannot interrupt a model call already under way, and it returns no partial result.

Lock order matches the parse queue: the store's lock, then this one. The worker never holds this
lock while it calls the store, and the store's `on_drop` hook (`cancel_documents`) takes this lock
and nothing else.
"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Literal

from clauseanchor_core import (
    AnalysisCancelled,
    AnalysisResult,
    AnalyzerProtocol,
    ProgressEvent,
    context_from_parsed_document,
)

from app.config import Settings
from app.parsing.model import ParsedDocument
from app.services.analysis import Scope, build_analyzer, check_result, processing_complete
from app.services.store import Store

log = logging.getLogger("clauseanchor.api")


@dataclass(slots=True)
class _Item:
    job_id: str
    document_id: str
    parsed: ParsedDocument | None  # None once the document is gone, so its text does not outlive it
    category_ids: tuple[str, ...]
    scope: Scope
    started: bool = False
    stopped_by: str | None = None  # "cancelled", "timeout", "gone" or "shutdown"


class AnalysisQueue:
    def __init__(self, store: Store, settings: Settings) -> None:
        self._store = store
        self._settings = settings
        self._limit = settings.analysis_queue_length
        self._timeout = settings.analysis_timeout_seconds
        self.state: Literal["loading", "ok", "failed"] = "loading"
        self.analyzer: AnalyzerProtocol | None = None
        # Unbounded: the limit counts the jobs that are still waiting, because a cancelled one
        # stays in the queue until the worker reaches it and must not hold a place
        self._queue: queue.Queue[_Item | None] = queue.Queue()
        self._items: dict[str, _Item] = {}  # by job id, from submit until the job is over
        self._lock = threading.Lock()
        self._closing = False
        self._thread = threading.Thread(target=self._work, name="analysis-worker", daemon=True)
        previous = store.on_drop

        def drop(document_ids: list[str]) -> None:
            previous(document_ids)  # the parse queue's hook comes first
            self.cancel_documents(document_ids)

        store.on_drop = drop

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        """Stops a running analysis and waits for the worker thread."""
        with self._lock:
            self._closing = True
            for item in self._items.values():
                self._halt(item, "shutdown")
        self._queue.put(None)  # wakes an idle worker. A busy one checks the flag
        if self._thread.is_alive():
            self._thread.join(timeout=30)

    def submit(
        self,
        job_id: str,
        document_id: str,
        parsed: ParsedDocument,
        category_ids: tuple[str, ...],
        scope: Scope,
    ) -> bool:
        """Queues one analysis. False when `analysis_queue_length` jobs are already waiting."""
        item = _Item(job_id, document_id, parsed, tuple(category_ids), scope)
        with self._lock:
            if (
                sum(not i.started and i.stopped_by is None for i in self._items.values())
                >= self._limit
            ):
                return False
            self._items[job_id] = item
            self._queue.put(item)  # inside the lock, so the order of the puts is the order here
        return True

    def cancel(self, job_id: str) -> bool:
        """Stops a waiting or running job. A waiting one ends at once, and a running one at the
        core's next check. False when the queue holds no such job."""
        with self._lock:
            item = self._items.get(job_id)
            if item is None:
                return False
            self._halt(item, "cancelled")
            waiting = not item.started
        if waiting:
            self._finish(job_id, "cancelled")
        return True

    def cancel_documents(self, document_ids: list[str]) -> None:
        """The store's `on_drop` hook. It runs under the store's lock and only sets flags, so the
        analyzer stops at its next check and the worker finds the document gone."""
        with self._lock:
            for item in self._items.values():
                if item.document_id in document_ids:
                    self._halt(item, "gone")

    def _halt(self, item: _Item, reason: str) -> None:
        """Marks the job stopped and drops its text. The caller holds the lock."""
        if item.stopped_by is None:
            item.stopped_by = reason
        item.parsed = None

    def _halt_for_time(self, item: _Item) -> None:
        with self._lock:
            self._halt(item, "timeout")

    def _work(self) -> None:
        try:
            analyzer = build_analyzer(self._settings)
        except Exception as error:
            # The message can name a path or a file (Rules section 5), so only the class is logged
            log.error("analyzer load failed: %s", type(error).__name__)
            self.state = "failed"
            return
        self.analyzer = analyzer
        self.state = "ok"
        while (item := self._queue.get()) is not None and not self._closing:
            try:
                self._run(item, analyzer)
            except Exception as error:
                # One bad job must not end the worker. Log the class name only.
                log.error("analysis job failed: %s", type(error).__name__)
                self._finish(item.job_id, "failed", error="ANALYSIS_FAILED")
            finally:
                with self._lock:
                    self._items.pop(item.job_id, None)

    def _finish(
        self,
        job_id: str,
        status: str,
        *,
        result: AnalysisResult | None = None,
        error: str | None = None,
    ) -> None:
        try:
            self._store.finish_analysis(job_id, status=status, result=result, error=error)
        except Exception as exc:
            log.error("analysis job could not be recorded: %s", type(exc).__name__)

    def _run(self, item: _Item, analyzer: AnalyzerProtocol) -> None:
        with self._lock:
            item.started = True
            parsed = item.parsed
            if item.stopped_by is not None or parsed is None:
                return  # cancelled or deleted while it waited, and `cancel` told the store
        if not self._store.start_job(item.job_id):
            return
        timer = threading.Timer(self._timeout, self._halt_for_time, (item,))
        timer.daemon = True
        timer.start()
        try:
            context = context_from_parsed_document(parsed, jurisdiction_scope=item.scope)
            result = analyzer.analyze(
                parsed.source_text,  # as the parser made it: never rebuilt or cleaned (D6)
                doc_id=item.document_id,
                text_sha256=parsed.text_sha256,
                category_ids=item.category_ids,
                context=context,
                progress=lambda event: self._progress(item, event),
                cancelled=lambda: item.stopped_by is not None,
            )
        except AnalysisCancelled:
            result = None
        except Exception as error:
            log.error("analysis failed: %s", type(error).__name__)
            self._finish(item.job_id, "failed", error="ANALYSIS_FAILED")
            return
        finally:
            timer.cancel()
        if result is None or item.stopped_by is not None:
            # Stopped, so nothing is stored even if the analyzer finished first. A delete or a
            # shutdown leaves nobody to tell.
            status = {"timeout": "timed_out", "gone": None, "shutdown": None}.get(
                item.stopped_by or "cancelled", "cancelled"
            )
            if status is not None:
                self._finish(item.job_id, status)
            return
        try:
            check_result(
                result,
                parsed=parsed,
                document_id=item.document_id,
                requested=item.category_ids,
                mode=self._settings.mode,
            )
        except Exception as error:
            log.error("analysis result refused: %s", type(error).__name__)
            self._finish(item.job_id, "failed", error="ANALYSIS_INVALID_RESULT")
            return
        status = "succeeded" if processing_complete(parsed, result) else "partial"
        self._finish(item.job_id, status, result=result)

    def _progress(self, item: _Item, event: ProgressEvent) -> None:
        self._store.set_progress(item.job_id, event.stage, event.completed_units, event.total_units)
