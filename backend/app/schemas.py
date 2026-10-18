"""Response shapes at the HTTP boundary. API.md documents each one.

A response model also filters: a field that is not declared here cannot leave the API.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    status: Literal["ok"]


class ReadyChecks(BaseModel):
    analyzer: Literal["ok", "artifacts_missing"]
    catalogue: Literal["ok", "missing", "invalid"]


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


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool
    details: dict[str, object]


class ErrorResponse(BaseModel):
    error: ErrorBody
