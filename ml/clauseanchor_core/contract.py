"""Versioned, framework-independent data structures for core analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import math
from typing import Callable, Literal, Protocol

CONTRACT_VERSION = "2.0"
CategoryStatus = Literal["found", "absent", "abstained", "unavailable"]
CandidateStatus = Literal["accepted", "review_candidate"]
ConfidenceBand = Literal["higher", "review", "unvalidated"]
CalibrationScope = Literal["per_category", "pooled", "unvalidated"]


def text_digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Span:
    doc_id: str
    text_sha256: str
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class StructureNode:
    id: str
    parent_id: str | None
    kind: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    jurisdiction_scope: Literal["india_review", "unspecified"] = "unspecified"
    parser_complete: bool = True
    structure_nodes: list[StructureNode] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RuleFlag:
    rule_id: str
    version: str
    label_key: str
    note: str
    statute_citations: list[str]
    authority_ids: list[str]
    evidence_spans: list[Span]
    scope_status: str


@dataclass(frozen=True, slots=True)
class Passage:
    id: str
    judgment_id: str
    case_name: str
    court: str
    year: int | None
    citation: str
    source_url: str
    start: int
    end: int
    text: str
    judgment_text_sha256: str
    corpus_version: str
    authority_status: str
    provenance_status: str
    rank: int


@dataclass(frozen=True, slots=True)
class ClauseFinding:
    id: str
    category_id: str
    span: Span
    status: CandidateStatus
    confidence: float | None
    confidence_band: ConfidenceBand
    calibration_scope: CalibrationScope
    origin: Literal["model", "fixture"]
    rule_flags: list[RuleFlag] = field(default_factory=list)
    passages: list[Passage] = field(default_factory=list)
    retrieval_status: str = "not_run"


@dataclass(frozen=True, slots=True)
class CategoryResult:
    category_id: str
    status: CategoryStatus
    decision_confidence: float | None
    reason_code: str | None
    search_complete: bool
    windows_done: int
    windows_total: int
    unresolved_count: int
    clauses: list[ClauseFinding] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    contract_version: str
    doc_id: str
    text_sha256: str
    artifact_manifest_sha256: str
    mode: Literal["stub", "real"]
    categories: list[CategoryResult]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    stage: str
    completed_units: int
    total_units: int


class AnalysisCancelled(RuntimeError):
    """Raised when the caller requests cancellation between units of work."""


class AnalyzerProtocol(Protocol):
    def analyze(
        self,
        document_text: str,
        *,
        doc_id: str,
        text_sha256: str,
        category_ids: tuple[str, ...],
        context: AnalysisContext,
        progress: Callable[[ProgressEvent], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> AnalysisResult: ...


def validate_probability(value: float | None) -> None:
    if value is not None and (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
    ):
        raise ValueError("Confidence must be null or a finite number in [0, 1].")


def validate_span(span: Span, source_text: str, doc_id: str) -> None:
    if span.doc_id != doc_id or span.text_sha256 != text_digest(source_text):
        raise ValueError("Span source identity mismatch.")
    if type(span.start) is not int or type(span.end) is not int:
        raise ValueError("Offsets must be integers, not booleans or strings.")
    if not 0 <= span.start < span.end <= len(source_text):
        raise ValueError("Span range is outside the source text.")
    if source_text[span.start:span.end] != span.text:
        raise ValueError("Span text does not equal the exact source slice.")


def validate_result(result: AnalysisResult, source_text: str) -> None:
    if result.contract_version != CONTRACT_VERSION:
        raise ValueError("Unsupported contract version.")
    if not result.doc_id or result.text_sha256 != text_digest(source_text):
        raise ValueError("Result source identity mismatch.")
    if result.mode not in ("stub", "real"):
        raise ValueError("Invalid result mode.")
    digest = result.artifact_manifest_sha256
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid artifact manifest digest.")
    categories: set[str] = set()
    finding_ids: set[str] = set()
    for category in result.categories:
        if not category.category_id or category.category_id in categories:
            raise ValueError("Empty or duplicate category ID.")
        categories.add(category.category_id)
        if category.status not in ("found", "absent", "abstained", "unavailable"):
            raise ValueError("Invalid category status.")
        validate_probability(category.decision_confidence)
        counts = (category.windows_done, category.windows_total, category.unresolved_count)
        if any(type(n) is not int or n < 0 for n in counts):
            raise ValueError("Invalid work counts.")
        if category.windows_done > category.windows_total:
            raise ValueError("Completed work exceeds total work.")
        if category.search_complete and category.windows_done != category.windows_total:
            raise ValueError("Complete search has unfinished windows.")
        accepted = 0
        unresolved = 0
        for finding in category.clauses:
            if not finding.id or finding.id in finding_ids:
                raise ValueError("Empty or duplicate finding ID.")
            finding_ids.add(finding.id)
            if finding.category_id != category.category_id:
                raise ValueError("Finding category mismatch.")
            if finding.status not in ("accepted", "review_candidate"):
                raise ValueError("Invalid candidate status.")
            if finding.calibration_scope not in ("per_category", "pooled", "unvalidated"):
                raise ValueError("Invalid calibration scope.")
            if finding.confidence_band not in ("higher", "review", "unvalidated"):
                raise ValueError("Invalid confidence band.")
            if finding.origin != ("fixture" if result.mode == "stub" else "model"):
                raise ValueError("Fixture and model provenance cannot be mixed.")
            validate_span(finding.span, source_text, result.doc_id)
            validate_probability(finding.confidence)
            if finding.confidence is None and finding.confidence_band == "higher":
                raise ValueError("Missing confidence cannot have a higher band.")
            if result.mode == "real" and finding.status == "accepted":
                if finding.confidence is None or finding.calibration_scope == "unvalidated":
                    raise ValueError("Real accepted findings require validated confidence.")
            accepted += finding.status == "accepted"
            unresolved += finding.status == "review_candidate"
            for flag in finding.rule_flags:
                for evidence in flag.evidence_spans:
                    validate_span(evidence, source_text, result.doc_id)
            for passage in finding.passages:
                if not passage.citation or not passage.source_url:
                    raise ValueError("Passage provenance is incomplete.")
                if not 0 <= passage.start < passage.end:
                    raise ValueError("Invalid judgment passage range.")
                if passage.end - passage.start != len(passage.text):
                    raise ValueError("Judgment passage length mismatch.")
                # Exact judgment-source comparison belongs to retrieval validation.
        if category.unresolved_count != unresolved:
            raise ValueError("Unresolved count does not match review candidates.")
        if category.status == "found" and accepted == 0:
            raise ValueError("Found requires at least one accepted occurrence.")
        if category.status != "found" and accepted:
            raise ValueError("Accepted occurrences require a found category.")
        if category.status == "absent":
            if not category.search_complete or category.clauses:
                raise ValueError("Absent requires complete search and no candidates.")
            if result.mode == "real" and category.decision_confidence is None:
                raise ValueError("Real absence requires a calibrated decision confidence.")
        if category.status in ("abstained", "unavailable") and not category.reason_code:
            raise ValueError("Unresolved states require a reason code.")
        if category.status == "unavailable" and category.search_complete:
            raise ValueError("Unavailable search cannot be complete.")
