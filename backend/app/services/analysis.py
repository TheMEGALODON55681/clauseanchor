"""The boundary with Tanishq's core (`clauseanchor_core`): the analyzer factory, the checks on
what comes back, and the app's own definitions over a result.

The backend imports public names from the core only, and never a training or inference module.
`CandidateOnlyAnalyzer` loads torch inside its constructor, so importing this module in stub mode
imports none of torch, transformers or numpy.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Literal, cast

from clauseanchor_core import (
    AnalysisResult,
    AnalyzerProtocol,
    CandidateOnlyAnalyzer,
    StubAnalyzer,
    text_digest,
    validate_result,
)

from app.config import STUB_FIXTURE_DIR, Settings
from app.parsing.model import ParsedDocument

Scope = Literal["india_review", "unspecified"]  # the core's own jurisdiction scopes

_CORE_MODE = {"sample": "stub", "real": "real"}


def build_analyzer(settings: Settings) -> AnalyzerProtocol:
    """The one analyzer of this process. It never falls back from real to the stub: a real run
    whose bundle fails to load raises, and `/ready` says so."""
    if settings.analyzer == "stub":
        return StubAnalyzer(STUB_FIXTURE_DIR)
    if settings.artifacts_dir is None or settings.artifacts_sha256 is None:
        raise ValueError("the real analyzer needs its artifacts directory and manifest digest")
    return CandidateOnlyAnalyzer(
        settings.artifacts_dir,
        expected_manifest_sha256=settings.artifacts_sha256,
        device="cpu",
        batch_size=1,
    )


def sample_refusal(
    analyzer: AnalyzerProtocol, parsed: ParsedDocument, category_ids: Collection[str]
) -> str | None:
    """Sample mode runs the stub, which takes only its own fixture text and its own categories
    (D7). The error code of the refusal, or None."""
    stub = cast(StubAnalyzer, analyzer)
    if parsed.text_sha256 != text_digest(stub.source_text):
        return "SAMPLE_MODE_ONLY"
    if not set(category_ids) <= set(stub.category_ids):
        return "VALIDATION_ERROR"
    return None


def check_result(
    result: AnalysisResult,
    *,
    parsed: ParsedDocument,
    document_id: str,
    requested: Sequence[str],
    mode: Literal["sample", "real"],
) -> None:
    """What a result must pass before the store takes it. Raises ValueError, and the caller logs
    the class and never the message. The core's `validate_result` checks spans, counts and the
    states against each other. The rest ties the result to this document, this mode and this
    request, so a stub result can never pass as a real one."""
    validate_result(result, parsed.source_text)
    if result.doc_id != document_id or result.mode != _CORE_MODE[mode]:
        raise ValueError("the result is for another document or another mode")
    if sorted(c.category_id for c in result.categories) != sorted(requested):
        raise ValueError("the result does not answer the categories that were asked for")
    if parsed.coverage.partial and any(c.status == "absent" for c in result.categories):
        # The parser says text may be missing, so nothing may read "not found" (ParserContract.md)
        raise ValueError("a partial parse cannot support an absent decision")


def processing_complete(parsed: ParsedDocument, result: AnalysisResult) -> bool:
    """API.md section 10. True only when the parse left nothing out and every requested category
    finished its search. A cancelled or timed-out job has no result, so it never gets here."""
    return not parsed.coverage.partial and all(c.search_complete for c in result.categories)


def decisions_resolved(result: AnalysisResult) -> int:
    """API.md section 10. An accepted decision is `found` or `absent`. An abstention or an
    unavailable category is not resolved."""
    return sum(c.status in ("found", "absent") for c in result.categories)
