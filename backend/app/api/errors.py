"""The error envelope: one fixed shape for every error response.

Messages are fixed templates. Nothing from the request or from an exception goes into one,
because both can carry contract text (Rules section 5).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Mapping

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger("clauseanchor.api")

# code: (status, message, retryable). API.md lists the same table.
ERRORS: dict[str, tuple[int, str, bool]] = {
    "VALIDATION_ERROR": (422, "The request is not valid.", False),
    "SESSION_INVALID": (401, "The session token is missing, invalid or expired.", False),
    "NOT_FOUND": (404, "No such resource.", False),
    "METHOD_NOT_ALLOWED": (405, "This method is not allowed here.", False),
    "SESSION_LIMIT": (429, "Too many sessions are active. Try again later.", True),
    "FILE_TOO_LARGE": (413, "The file is larger than 10 MiB.", False),
    "EMPTY_FILE": (400, "The file is empty.", False),
    "UNSUPPORTED_TYPE": (415, "The file is not a PDF or a DOCX.", False),
    "DOCUMENT_LIMIT": (
        429,
        "This session already holds as many documents as it can. Delete one to upload another.",
        False,
    ),
    "QUEUE_FULL": (429, "Too many files are waiting to be read. Try again shortly.", True),
    "INTERNAL_ERROR": (500, "Something went wrong on the server.", False),
    "NOT_READY": (503, "The service is not ready.", True),
    "CATALOGUE_UNAVAILABLE": (503, "The category catalogue is not available.", False),
}


# The code a failed parse job carries: code: (message, retryable). These never become an HTTP
# status. They are the parser's codes that a file can reach after the upload checks, and the three
# API codes for a child that was killed or failed. API.md lists the same table.
JOB_ERRORS: dict[str, tuple[str, bool]] = {
    "MALFORMED_FILE": ("The file could not be read.", False),
    "ENCRYPTED_PDF": ("The PDF needs a password to open.", False),
    "SCANNED_PDF": ("The PDF is scanned, so it holds no text to read.", False),
    "TOO_MANY_PAGES": ("The PDF has more than 100 pages.", False),
    "TOO_MUCH_TEXT": ("The file holds more text than can be processed.", False),
    "ARCHIVE_TOO_LARGE": ("The file expands to more than 100 MiB.", False),
    "ARCHIVE_UNSAFE": ("The structure of the file is not allowed.", False),
    "TRACKED_CHANGES_PRESENT": (
        "The document has tracked changes. Accept all changes and upload it again.",
        False,
    ),
    "NO_TEXT_FOUND": ("The file holds no text.", False),
    "PARSE_TIMEOUT": ("Reading the file took too long.", False),
    "PARSE_MEMORY_LIMIT": ("Reading the file needed more memory than is allowed.", False),
    "PARSE_FAILED": ("Reading the file failed.", True),
}


def error_response(
    code: str,
    details: dict[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    status, message, retryable = ERRORS[code]
    body = {
        "error": {
            "code": code,
            "message": message,
            "request_id": str(uuid.uuid4()),
            "retryable": retryable,
            "details": details or {},
        }
    }
    return JSONResponse(body, status_code=status, headers=headers)


def _reply(code: str) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handle(request: Request, exc: Exception) -> JSONResponse:
        # Nothing from exc goes into the body: FastAPI's own 422 repeats the submitted input.
        # Only the headers carry over (Starlette puts Allow on a 405).
        return error_response(code, headers=getattr(exc, "headers", None))

    return handle


def install_error_handling(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _reply("VALIDATION_ERROR"))
    # The bearer check raises a bare 401, so the headers it carries (WWW-Authenticate) pass through
    app.add_exception_handler(401, _reply("SESSION_INVALID"))
    app.add_exception_handler(404, _reply("NOT_FOUND"))
    app.add_exception_handler(405, _reply("METHOD_NOT_ALLOWED"))

    @app.middleware("http")
    async def guard_responses(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # A handler for Exception runs inside Starlette's server-error layer, which sends its
        # reply and then raises again, so the server logs a traceback with the exception text.
        # Catching the crash here keeps that text out of the reply and out of the log.
        try:
            response = await call_next(request)
        except Exception as exc:
            log.error("unhandled %s", type(exc).__name__)
            response = error_response("INTERNAL_ERROR")
        # Session and document replies hold tokens and contract text, and none is worth caching.
        response.headers["Cache-Control"] = "no-store"
        return response
