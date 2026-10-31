from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from urllib.parse import unquote

from clauseanchor_core import CONTRACT_VERSION
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.auth import require_session
from app.api.errors import JOB_ERRORS, error_response
from app.parsing import ErrorCode, ParseError
from app.parsing.detect import detect_type
from app.parsing.errors import MAX_INPUT_BYTES
from app.parsing.schema import to_json
from app.schemas import (
    Analysis,
    AnalysisRequest,
    Capabilities,
    CategorySpec,
    CategoryView,
    DecisionCoverage,
    DocumentView,
    ErrorResponse,
    Health,
    Job,
    JobError,
    NewAnalysis,
    NewSession,
    Ready,
    ReadyChecks,
    Upload,
)
from app.services.analysis import decisions_resolved, processing_complete, sample_refusal
from app.services.scope import SCOPE_NOTICE
from app.services.store import (
    AnalysisActiveError,
    DocumentLimitError,
    JobRecord,
    Session,
    SessionLimitError,
)

router = APIRouter(prefix="/api/v1")

_UNAVAILABLE = {503: {"model": ErrorResponse}}
_UNAUTHORIZED = {401: {"model": ErrorResponse}}
_NOT_FOUND = {404: {"model": ErrorResponse}}
_CONFLICT = {409: {"model": ErrorResponse}}
# The two strings the parser writes into ParsedDocument.media_type. A test keeps them equal.
_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_FILENAME_STAR = re.compile(r"filename\*\s*=\s*utf-8''([^;\s]*)", re.IGNORECASE)
_PATH_SEPARATORS = re.compile(r"[\\/]")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def _utc(seconds: float) -> datetime:
    """Whole seconds, rounded down: the client never sees a later end than the store holds."""
    return datetime.fromtimestamp(int(seconds), UTC)


def _filename(content_disposition: str | None, extension: Literal["pdf", "docx"]) -> str:
    """The name from `filename*=UTF-8''...` (RFC 5987), cleaned, or `document.pdf` or
    `document.docx`. A plain `filename=` is not read. The name is for display only: it keeps no
    directory part and no control character, and it lives in RAM (Rules section 5)."""
    found = _FILENAME_STAR.search(content_disposition or "")
    if found:
        try:
            name = unquote(found.group(1), encoding="utf-8", errors="strict")
        except UnicodeDecodeError:
            name = ""
        name = _CONTROL_CHARACTERS.sub("", _PATH_SEPARATORS.split(name)[-1])[:255].strip()
        if name.strip("."):
            return name
    return f"document.{extension}"


async def _read_body(request: Request) -> bytes | None:
    """The raw body, or None once it passes 10 MiB. It counts what arrives, so a missing or a
    false Content-Length changes nothing. The body stays in RAM (D3)."""
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_INPUT_BYTES:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/health", response_model=Health)
async def health() -> Health:
    """Liveness only. It checks no dependency, so a probe cannot fail on a missing catalogue."""
    return Health(status="ok")


@router.get("/ready", response_model=Ready, responses=_UNAVAILABLE)
async def ready(request: Request) -> Ready | JSONResponse:
    # The lifespan starts the expiry sweep. Without it a session outlives its hour in RAM.
    sweeper = request.app.state.sweeper
    checks = ReadyChecks(
        analyzer=request.app.state.analysis_queue.state,
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
    return NewSession(token=token, expires_at=_utc(session.expires_at))


@router.delete("/sessions/current", status_code=204, responses=_UNAUTHORIZED)
async def delete_current_session(
    request: Request, session: Annotated[Session, Depends(require_session)]
) -> Response:
    """Ends the session now and deletes its documents and jobs from RAM and SQLite. A parse that
    is still running loses its child."""
    request.app.state.store.delete_session(session.id)
    return Response(status_code=204)


@router.post(
    "/documents",
    status_code=202,
    response_model=Upload,
    responses={
        **_UNAUTHORIZED,
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def upload_document(
    request: Request, session: Annotated[Session, Depends(require_session)]
) -> Upload | JSONResponse:
    """Takes the file as the raw body, queues a parse and answers at once. The type comes from
    the bytes. The session check runs first, so a stranger's body is never read."""
    declared = request.headers.get("content-length", "")
    if (
        declared.isascii()
        and declared.isdigit()
        and len(declared) < 19
        and int(declared) > MAX_INPUT_BYTES
    ):
        return error_response("FILE_TOO_LARGE")
    data = await _read_body(request)
    if data is None:
        return error_response("FILE_TOO_LARGE")
    try:
        kind = await asyncio.to_thread(detect_type, data)
    except ParseError as error:
        if error.code is ErrorCode.EMPTY_FILE:
            return error_response("EMPTY_FILE")
        if error.code is ErrorCode.UNSUPPORTED_TYPE:
            return error_response("UNSUPPORTED_TYPE")
        kind = "docx"  # an archive that cannot be read: the parse job reports MALFORMED_FILE

    store = request.app.state.store
    try:
        document = store.add_document(
            session.id,
            filename=_filename(request.headers.get("content-disposition"), kind),
            media_type=_MEDIA_TYPES[kind],
            byte_count=len(data),
        )
    except DocumentLimitError:
        return error_response("DOCUMENT_LIMIT")
    job_id = None if document is None else store.add_job(document.id, "parse")
    if document is None or job_id is None:  # the session ended while the body arrived
        return error_response("SESSION_INVALID", headers={"WWW-Authenticate": "Bearer"})
    if not request.app.state.parse_queue.submit(document.id, job_id, data):
        store.delete_document(session.id, document.id)
        return error_response("QUEUE_FULL")
    return Upload(
        document_id=document.id, parse_job_id=job_id, expires_at=_utc(document.expires_at)
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentView,
    responses={**_UNAUTHORIZED, **_NOT_FOUND},
)
def read_document(
    document_id: str, request: Request, session: Annotated[Session, Depends(require_session)]
) -> DocumentView | JSONResponse:
    """The document's metadata and, once it is parsed, the full parser output. Another session's
    id gets the same 404 as an unknown one."""
    document = request.app.state.store.get_document(session.id, document_id)
    if document is None:
        return error_response("NOT_FOUND")
    return DocumentView(
        id=document.id,
        filename=document.filename,
        status=document.status,
        media_type=document.media_type,
        byte_count=document.byte_count,
        expires_at=_utc(document.expires_at),
        parsed=None if document.parsed is None else to_json(document.parsed),
    )


@router.delete(
    "/documents/{document_id}",
    status_code=204,
    responses={**_UNAUTHORIZED, **_NOT_FOUND},
)
def delete_document(
    document_id: str, request: Request, session: Annotated[Session, Depends(require_session)]
) -> Response:
    """Deletes the document and its jobs. A parse that is still running loses its child first."""
    if not request.app.state.store.delete_document(session.id, document_id):
        return error_response("NOT_FOUND")
    return Response(status_code=204)


def _job_view(job: JobRecord) -> Job:
    error = None
    if job.error is not None:
        message, retryable = JOB_ERRORS[job.error]
        error = JobError(code=job.error, message=message, retryable=retryable)
    return Job(
        id=job.id,
        kind=job.kind,
        document_id=job.document_id,
        analysis_id=job.analysis_id,
        status=job.status,
        stage=job.stage,
        completed_units=job.completed_units,
        total_units=job.total_units,
        error=error,
    )


@router.get("/jobs/{job_id}", response_model=Job, responses={**_UNAUTHORIZED, **_NOT_FOUND})
def read_job(
    job_id: str, request: Request, session: Annotated[Session, Depends(require_session)]
) -> Job | JSONResponse:
    job = request.app.state.store.get_job(session.id, job_id)
    return error_response("NOT_FOUND") if job is None else _job_view(job)


@router.post(
    "/jobs/{job_id}/cancel",
    status_code=202,
    response_model=Job,
    responses={**_UNAUTHORIZED, **_NOT_FOUND, **_CONFLICT},
)
def cancel_job(
    job_id: str, request: Request, session: Annotated[Session, Depends(require_session)]
) -> Job | JSONResponse:
    """Stops an analysis that is waiting or running. A waiting one ends before this returns. A
    running one ends at the core's next check, so the reply can still say `running`."""
    store = request.app.state.store
    job = store.get_job(session.id, job_id)
    if job is None:
        return error_response("NOT_FOUND")
    if job.kind != "analysis" or job.status not in ("queued", "running"):
        return error_response("JOB_NOT_CANCELLABLE")
    request.app.state.analysis_queue.cancel(job_id)
    return _job_view(store.get_job(session.id, job_id) or job)


@router.post(
    "/documents/{document_id}/analyses",
    status_code=202,
    response_model=NewAnalysis,
    responses={
        **_UNAUTHORIZED,
        **_NOT_FOUND,
        **_CONFLICT,
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def start_analysis(
    document_id: str,
    body: AnalysisRequest,
    request: Request,
    session: Annotated[Session, Depends(require_session)],
) -> NewAnalysis | JSONResponse:
    """Queues an analysis of a parsed document and answers at once. The checks run in order and
    stop at the first that fails (API.md section 10)."""
    state, store = request.app.state, request.app.state.store
    document = store.get_document(session.id, document_id)
    if document is None:
        return error_response("NOT_FOUND")
    parsed = document.parsed
    if document.status != "parsed" or parsed is None:
        return error_response("DOCUMENT_NOT_PARSED")
    queue = state.analysis_queue
    if queue.state != "ok":
        return error_response("NOT_READY", details={"checks": {"analyzer": queue.state}})
    if state.catalogue is None:
        return error_response("CATALOGUE_UNAVAILABLE")
    ids = tuple(body.category_ids)
    # Ids come from the catalogue and nowhere else. A repeat or a stranger is a bad request.
    if len(set(ids)) != len(ids) or not set(ids) <= {c.id for c in state.catalogue.categories}:
        return error_response("VALIDATION_ERROR")
    if state.settings.analyzer == "stub":
        refusal = sample_refusal(queue.analyzer, parsed, ids)
        if refusal is not None:
            return error_response(refusal)
    try:
        added = store.add_analysis_job(session.id, document.id, ids, body.jurisdiction_scope)
    except AnalysisActiveError:
        return error_response("ANALYSIS_IN_PROGRESS")
    if added is None:  # the document went while the checks ran
        return error_response("NOT_FOUND")
    job_id, analysis_id = added
    if not queue.submit(job_id, document.id, parsed, ids, body.jurisdiction_scope):
        store.delete_job(job_id)
        return error_response("ANALYSIS_QUEUE_FULL")
    return NewAnalysis(analysis_id=analysis_id, job_id=job_id)


@router.get(
    "/analyses/{analysis_id}",
    response_model=Analysis,
    responses={**_UNAUTHORIZED, **_NOT_FOUND, **_UNAVAILABLE},
)
def read_analysis(
    analysis_id: str, request: Request, session: Annotated[Session, Depends(require_session)]
) -> Analysis | JSONResponse:
    """The analysis as it stands: a snapshot with no categories while the job waits or runs, and
    after a cancel, a time-out or a failure. Only a result puts categories in it."""
    found = request.app.state.store.get_analysis(session.id, analysis_id)
    catalogue = request.app.state.catalogue
    if found is None:
        return error_response("NOT_FOUND")
    if catalogue is None:
        return error_response("CATALOGUE_UNAVAILABLE")
    job, document = found
    record, parsed = document.analysis, document.parsed
    if record is None or parsed is None:  # cannot happen: get_analysis returns a document with both
        return error_response("NOT_FOUND")
    result = record.result
    return Analysis(
        id=record.analysis_id,
        document_id=document.id,
        text_sha256=parsed.text_sha256,
        contract_version=CONTRACT_VERSION,
        artifact_manifest_sha256=None if result is None else result.artifact_manifest_sha256,
        status=job.status,
        mode=request.app.state.settings.mode,
        jurisdiction_scope=record.jurisdiction_scope,
        created_at=_utc(job.created_at),
        finished_at=None if job.finished_at is None else _utc(job.finished_at),
        scope_notice=SCOPE_NOTICE,
        catalogue_version=catalogue.version,
        processing_complete=result is not None and processing_complete(parsed, result),
        decision_coverage=DecisionCoverage(
            resolved=0 if result is None else decisions_resolved(result),
            requested=len(record.category_ids),
        ),
        categories=[]
        if result is None
        else [CategoryView.model_validate(c, from_attributes=True) for c in result.categories],
        warnings=[] if result is None else list(result.warnings),
    )
