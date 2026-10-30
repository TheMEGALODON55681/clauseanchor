"""Response shapes at the HTTP boundary. API.md documents each one.

A response model also filters: a field that is not declared here cannot leave the API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class Health(BaseModel):
    status: Literal["ok"]


class ReadyChecks(BaseModel):
    analyzer: Literal["ok", "artifacts_missing"]
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
    status: Literal["queued", "running", "succeeded", "partial", "failed", "cancelled"]
    error: JobError | None
