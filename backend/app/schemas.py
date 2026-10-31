"""Response shapes at the HTTP boundary. API.md documents each one.

A response model also filters: a field that is not declared here cannot leave the API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JobStatus = Literal["queued", "running", "succeeded", "partial", "failed", "cancelled", "timed_out"]


class Health(BaseModel):
    status: Literal["ok"]


class ReadyChecks(BaseModel):
    analyzer: Literal["ok", "loading", "failed"]
    catalogue: Literal["ok", "missing", "invalid"]
    store: Literal["ok", "sweep_stopped"]
    database: Literal["ok", "unavailable"]


class Ready(BaseModel):
    ready: bool
    checks: ReadyChecks


class CategorySpec(BaseModel):
    id: str
    display_name: str
    source: Literal["cuad", "india_extension"]
    support_status: str


class Capabilities(BaseModel):
    scope_notice: str
    mode: Literal["sample", "real"]
    catalogue_version: str
    categories: list[CategorySpec]


class NewSession(BaseModel):
    token: str
    expires_at: datetime


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool
    details: dict[str, object]


class ErrorResponse(BaseModel):
    error: ErrorBody


class Upload(BaseModel):
    document_id: str
    parse_job_id: str
    expires_at: datetime


class DocumentView(BaseModel):
    id: str
    filename: str
    status: Literal["parsing", "parsed", "failed"]
    media_type: str
    byte_count: int
    expires_at: datetime
    # The full parser output once parsed, in the shape of docs/app/parser_output.schema.json
    parsed: dict[str, Any] | None


class JobError(BaseModel):
    code: str
    message: str
    retryable: bool


class Job(BaseModel):
    id: str
    kind: Literal["parse", "analysis"]
    document_id: str
    analysis_id: str | None  # an analysis job only
    status: JobStatus
    # The core's own stage word and its unit counts (an analysis job only; a parse has no counts)
    stage: str | None
    completed_units: int
    total_units: int | None
    error: JobError | None


class AnalysisRequest(BaseModel):
    """Unknown fields are refused (plan 9.1). The ids and the scope are both required (D1)."""

    model_config = ConfigDict(extra="forbid")

    category_ids: list[str] = Field(min_length=1)
    jurisdiction_scope: Literal["india_review", "unspecified"]


class NewAnalysis(BaseModel):
    analysis_id: str
    job_id: str


# The views below carry the core's records field for field. Each is its own model, so a field
# the core adds stays inside the API until someone adds it here on purpose (a test compares).
class SpanView(BaseModel):
    doc_id: str
    text_sha256: str
    start: int
    end: int
    text: str


class RuleFlagView(BaseModel):
    rule_id: str
    version: str
    label_key: str
    note: str
    statute_citations: list[str]
    authority_ids: list[str]
    evidence_spans: list[SpanView]
    scope_status: str


class PassageView(BaseModel):
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


class ClauseView(BaseModel):
    id: str
    category_id: str
    span: SpanView
    status: Literal["accepted", "review_candidate"]
    confidence: float | None
    confidence_band: Literal["higher", "review", "unvalidated"]
    calibration_scope: Literal["per_category", "pooled", "unvalidated"]
    origin: Literal["model", "fixture"]
    rule_flags: list[RuleFlagView]
    passages: list[PassageView]
    retrieval_status: str


class CategoryView(BaseModel):
    category_id: str
    status: Literal["found", "absent", "abstained", "unavailable"]
    decision_confidence: float | None
    reason_code: str | None
    search_complete: bool
    windows_done: int
    windows_total: int
    unresolved_count: int
    clauses: list[ClauseView]


class DecisionCoverage(BaseModel):
    resolved: int
    requested: int


class Analysis(BaseModel):
    id: str
    document_id: str
    text_sha256: str
    contract_version: str
    artifact_manifest_sha256: str | None  # null until a result exists
    status: JobStatus
    mode: Literal["sample", "real"]
    jurisdiction_scope: Literal["india_review", "unspecified"]
    created_at: datetime
    finished_at: datetime | None
    scope_notice: str
    catalogue_version: str
    processing_complete: bool
    decision_coverage: DecisionCoverage
    categories: list[CategoryView]  # empty until the job has a result
    warnings: list[str]
