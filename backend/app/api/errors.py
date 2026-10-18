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
    "NOT_FOUND": (404, "No such resource.", False),
    "METHOD_NOT_ALLOWED": (405, "This method is not allowed here.", False),
    "INTERNAL_ERROR": (500, "Something went wrong on the server.", False),
    "NOT_READY": (503, "The service is not ready.", True),
    "CATALOGUE_UNAVAILABLE": (503, "The category catalogue is not available.", False),
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
    app.add_exception_handler(404, _reply("NOT_FOUND"))
    app.add_exception_handler(405, _reply("METHOD_NOT_ALLOWED"))

    @app.middleware("http")
    async def contain_crashes(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # A handler for Exception runs inside Starlette's server-error layer, which sends its
        # reply and then raises again, so the server logs a traceback with the exception text.
        # Catching the crash here keeps that text out of the reply and out of the log.
        try:
            return await call_next(request)
        except Exception as exc:
            log.error("unhandled %s", type(exc).__name__)
            return error_response("INTERNAL_ERROR")
