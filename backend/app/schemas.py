"""Response shapes at the HTTP boundary. API.md documents each one.

A response model also filters: a field that is not declared here cannot leave the API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

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
