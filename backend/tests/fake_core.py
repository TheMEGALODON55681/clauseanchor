"""Stand-ins for the core, so no test loads model weights or imports torch.

`FakeCore` replaces `CandidateOnlyAnalyzer` through the factory (`fake_core` fixture). The documents
are made up, and the only real text a test reads is the core's own sample, for stub mode.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from clauseanchor_core import (
    CONTRACT_VERSION,
    AnalysisCancelled,
    AnalysisResult,
    CategoryResult,
    ClauseFinding,
    ProgressEvent,
    Span,
    read_exact_text,
    text_digest,
)

from app.config import STUB_FIXTURE_DIR
from app.parsing.model import Coverage, ParsedDocument
from app.services.store import DocumentRecord, Session, Store

SAMPLE_TEXT = read_exact_text(STUB_FIXTURE_DIR / "sample_contract.txt")
DIGEST = "ef" * 32
MADE_UP_TEXT = "Madeup one sentence here.\n\nMadeup second sentence there."


def parsed_document(
    text: str = MADE_UP_TEXT, *, partial: bool = False, warnings: tuple = (), **fields: object
) -> ParsedDocument:
    return ParsedDocument(
        source_text=text,
        text_sha256=text_digest(text),
        parser_version="1.1.0",
        media_type="application/pdf",
        page_count=1,
        blocks=(),
        nodes=fields.pop("nodes", ()),  # type: ignore[arg-type]
        decorations=fields.pop("decorations", ()),  # type: ignore[arg-type]
        warnings=warnings,
        coverage=Coverage(pages_total=1, pages_with_text=1, chars=len(text), partial=partial),
    )


def add_parsed(store: Store, session: Session, parsed: ParsedDocument) -> DocumentRecord:
    """A document that has been uploaded and parsed, with no child process involved."""
    doc = store.add_document(
        session.id,
        filename="a.pdf",
        media_type=parsed.media_type,
        byte_count=len(parsed.source_text),
    )
    assert doc is not None
    job_id = store.add_job(doc.id, "parse")
    assert job_id is not None
    store.start_job(job_id)
    store.finish_job(job_id, parsed=parsed)
    return doc


def real_result(
    text: str,
    doc_id: str,
    category_ids: tuple[str, ...],
    *,
    unavailable: frozenset[str] = frozenset(),
    incomplete: frozenset[str] = frozenset(),
) -> AnalysisResult:
    """What the candidate-only analyzer returns: review candidates and abstentions, never a
    confidence, never `found` or `absent`. Unavailable ids have no windows."""
    digest = text_digest(text)
    categories = []
    for category_id in category_ids:
        if category_id in unavailable:
            categories.append(
                CategoryResult(
                    category_id, "unavailable", None, "unsupported_india_extension", False, 0, 0, 0
                )
            )
            continue
        finding = ClauseFinding(
            id=f"{doc_id}:{category_id}:1",
            category_id=category_id,
            span=Span(doc_id, digest, 0, 6, text[:6]),
            status="review_candidate",
            confidence=None,
            confidence_band="unvalidated",
            calibration_scope="unvalidated",
            origin="model",
        )
        done = category_id not in incomplete
        categories.append(
            CategoryResult(
                category_id,
                "abstained",
                None,
                "unvalidated_model",
                done,
                1,
                1 if done else 2,
                1,
                [finding],
            )
        )
    return AnalysisResult(CONTRACT_VERSION, doc_id, digest, DIGEST, "real", categories, [])


class FakeCore:
    """A stand-in for the CandidateOnlyAnalyzer class and for its instance.

    Calling it builds the "analyzer" (itself). `behave` is what `analyze` does: `default` answers
    with a valid result, `hold` runs until it is told to stop, `gated` runs until `release` is set.
    """

    def __init__(self) -> None:
        self.loads: list[tuple[object, dict[str, object]]] = []
        self.load_gate: threading.Event | None = None
        self.load_error: Exception | None = None
        self.calls: list[dict[str, object]] = []
        self.unavailable: frozenset[str] = frozenset()
        self.incomplete: frozenset[str] = frozenset()
        self.running = threading.Event()  # set when an analysis is under way
        self.release = threading.Event()  # lets `gated` finish
        self.saw_stop = threading.Event()  # set when `cancelled()` first said yes
        self.behave: Callable[..., AnalysisResult] = self.default
        self.category_ids: tuple[str, ...] = ()

    def __call__(self, artifact_dir: object, **kwargs: object) -> FakeCore:
        self.loads.append((artifact_dir, kwargs))
        if self.load_gate is not None:
            self.load_gate.wait(30)
        if self.load_error is not None:
            raise self.load_error
        return self

    def analyze(self, text: str, **kwargs: object) -> AnalysisResult:
        self.calls.append({"text": text, **kwargs})
        return self.behave(text, **kwargs)

    def default(
        self,
        text: str,
        *,
        doc_id: str,
        category_ids: tuple[str, ...],
        progress=None,
        cancelled=None,
        **_: object,
    ) -> AnalysisResult:
        total = len(category_ids)
        for index in range(total):
            self._check(cancelled)
            if progress:
                progress(ProgressEvent("inference", index + 1, total))
        return real_result(
            text, doc_id, category_ids, unavailable=self.unavailable, incomplete=self.incomplete
        )

    def hold(self, text: str, *, cancelled=None, **_: object) -> AnalysisResult:
        self.running.set()
        while True:
            self._check(cancelled)
            time.sleep(0.01)

    def gated(self, text: str, **kwargs: object) -> AnalysisResult:
        self.running.set()
        while not self.release.is_set():
            self._check(kwargs.get("cancelled"))  # type: ignore[arg-type]
            time.sleep(0.01)
        return self.default(text, **kwargs)  # type: ignore[arg-type]

    def _check(self, cancelled: Callable[[], bool] | None) -> None:
        if cancelled and cancelled():
            self.saw_stop.set()
            raise AnalysisCancelled("stopped")
