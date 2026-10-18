"""The bearer check. Every route that needs a session depends on `require_session`."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.store import Session

# auto_error is off so that a missing header and a wrong scheme get the same envelope as a bad token
_bearer = HTTPBearer(auto_error=False)


def require_session(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Session:
    """The live session for the bearer token, or a 401 that does not say which check failed.

    A missing, malformed, unknown or expired token gets one reply. The store drops an expired
    session when it finds one, so after that it looks the same as an unknown one.
    """
    session = None
    if credentials is not None:
        session = request.app.state.store.get_session(credentials.credentials)
    if session is None:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})
    return session
