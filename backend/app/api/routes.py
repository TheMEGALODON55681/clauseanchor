from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.errors import error_response
from app.schemas import Capabilities, CategorySpec, ErrorResponse, Health, Ready, ReadyChecks
from app.services.scope import SCOPE_NOTICE

router = APIRouter(prefix="/api/v1")

_UNAVAILABLE = {503: {"model": ErrorResponse}}


@router.get("/health", response_model=Health)
async def health() -> Health:
    """Liveness only. It checks no dependency, so a probe cannot fail on a missing catalogue."""
    return Health(status="ok")


@router.get("/ready", response_model=Ready, responses=_UNAVAILABLE)
async def ready(request: Request) -> Ready | JSONResponse:
    settings = request.app.state.settings
    analyzer_ok = settings.analyzer == "stub" or (
        settings.artifacts_dir is not None and settings.artifacts_dir.is_dir()
    )
    checks = ReadyChecks(
        analyzer="ok" if analyzer_ok else "artifacts_missing",
        catalogue=request.app.state.catalogue_status,
    )
    if checks.analyzer == "ok" and checks.catalogue == "ok":
        return Ready(ready=True, checks=checks)
    return error_response("NOT_READY", details={"checks": checks.model_dump()})


@router.get("/capabilities", response_model=Capabilities, responses=_UNAVAILABLE)
async def capabilities(request: Request) -> Capabilities | JSONResponse:
    catalogue = request.app.state.catalogue
    if catalogue is None:
        return error_response("CATALOGUE_UNAVAILABLE")
    return Capabilities(
        scope_notice=SCOPE_NOTICE,
        mode=request.app.state.settings.mode,
        catalogue_version=catalogue.version,
        categories=[
            CategorySpec.model_validate(c, from_attributes=True) for c in catalogue.categories
        ],
    )
