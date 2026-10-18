from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.auth import require_session
from app.api.errors import error_response
from app.schemas import (
    Capabilities,
    CategorySpec,
    ErrorResponse,
    Health,
    NewSession,
    Ready,
    ReadyChecks,
)
from app.services.scope import SCOPE_NOTICE
from app.services.store import Session, SessionLimitError

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
    # The lifespan starts the expiry sweep. Without it a session outlives its hour in RAM.
    sweeper = request.app.state.sweeper
    checks = ReadyChecks(
        analyzer="ok" if analyzer_ok else "artifacts_missing",
        catalogue=request.app.state.catalogue_status,
        store="ok" if sweeper is not None and not sweeper.done() else "sweep_stopped",
        database="ok" if request.app.state.store.ping() else "unavailable",
    )
    if all(value == "ok" for value in checks.model_dump().values()):
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


@router.post(
    "/sessions",
    status_code=201,
    response_model=NewSession,
    responses={429: {"model": ErrorResponse}},
)
async def create_session(request: Request) -> NewSession | JSONResponse:
    """Starts a session. The token is in this reply and nowhere else. It takes no body."""
    try:
        token, session = request.app.state.store.create_session()
    except SessionLimitError:
        return error_response("SESSION_LIMIT")
    # Whole seconds, rounded down: the client never sees a later end than the store holds
    return NewSession(token=token, expires_at=datetime.fromtimestamp(int(session.expires_at), UTC))


@router.delete("/sessions/current", status_code=204, responses={401: {"model": ErrorResponse}})
async def delete_current_session(
    request: Request, session: Annotated[Session, Depends(require_session)]
) -> Response:
    """Ends the session now and deletes its documents and jobs from RAM and SQLite."""
    request.app.state.store.delete_session(session.id)
    return Response(status_code=204)
