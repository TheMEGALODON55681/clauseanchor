"""The FastAPI app. `create_app(settings)` builds one, so tests bring their own settings.

Run it with `uvicorn app.main:create_app --factory`, which reads the environment.
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import sqlite3
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send

from app.api.errors import install_error_handling
from app.api.routes import router
from app.config import PREFIX, SWEEP_INTERVAL_SECONDS, ConfigError, Settings
from app.services.analysis_jobs import AnalysisQueue
from app.services.parse_jobs import ParseQueue
from app.services.scope import CatalogueError, load_catalogue
from app.services.store import Store

log = logging.getLogger("clauseanchor.api")


async def _sweep_forever(store: Store) -> None:
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            store.sweep()
        except Exception as exc:
            # One failed pass must not end the sweep. Log the class name only (Rules section 5).
            log.error("sweep failed: %s", type(exc).__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    sweeper = asyncio.create_task(_sweep_forever(app.state.store))
    app.state.sweeper = sweeper
    app.state.parse_queue.start()
    # The analysis worker loads the analyzer in its own thread: 42.6 s for the real model on the
    # first run and 6.2 s on the second (BuildLog, 2-D.1).
    # The app serves meanwhile, and /ready says `loading`.
    app.state.analysis_queue.start()
    try:
        yield
    finally:
        sweeper.cancel()
        await asyncio.gather(sweeper, return_exceptions=True)
        # Each stop ends what is running and waits for it, off the event loop
        await asyncio.to_thread(app.state.parse_queue.stop)
        await asyncio.to_thread(app.state.analysis_queue.stop)
        app.state.store.close()


def _serve_frontend(app: FastAPI, dist: Path) -> None:
    """Serves the built frontend from `dist` to every request that no API route claims.

    It takes the router's `default`, the handler for a request that matches nothing, so it never
    sees a request an API route can answer: a wrong method keeps its 405 and its Allow header, a
    trailing slash its redirect, and an unknown /api path its 404 envelope instead of index.html.
    The app uses hash routes, so a file that does not exist is a 404 and needs no fallback.
    """
    # Python's table has no .woff2, and a slim Linux image has no mime.types to add it
    mimetypes.add_type("font/woff2", ".woff2")
    files = StaticFiles(directory=dist, html=True)
    not_found = app.router.not_found

    async def frontend(scope: Scope, receive: Receive, send: Send) -> None:
        path = scope["path"]
        if path == "/api" or path.startswith("/api/"):
            await not_found(scope, receive, send)
        else:
            await files(scope, receive, send)

    app.router.default = frontend


def create_app(settings: Settings | None = None, clock: Callable[[], float] = time.time) -> FastAPI:
    """`clock` is the one source of time for expiry, so tests move it by hand."""
    settings = Settings.from_env() if settings is None else settings
    dist = settings.frontend_dist
    if dist is not None and not (dist / "index.html").is_file():
        # Name the variable and not the path, as every other bad setting does
        raise ConfigError(f"{PREFIX}FRONTEND_DIST must be a folder that holds index.html")
    # The interactive docs pages load their scripts from a CDN, and every route sits under /api/v1
    app = FastAPI(
        title="ClauseAnchor API",
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
        lifespan=_lifespan,
    )
    app.state.settings = settings
    try:
        app.state.store = Store(
            settings.db_path, ttl_seconds=settings.session_ttl_minutes * 60, clock=clock
        )
    except sqlite3.Error:
        # Name the variable and not the path, as every other bad setting does
        raise ConfigError(f"{PREFIX}DB_PATH cannot be opened") from None
    app.state.uploads_in_flight = 0  # counted on the event loop, so it needs no lock
    app.state.sweeper = None  # the lifespan starts it
    app.state.parse_queue = ParseQueue(app.state.store, settings)  # and this one
    app.state.analysis_queue = AnalysisQueue(app.state.store, settings)  # and this one
    # Loaded once at start. A missing or broken file is a state to report, not a crash:
    # /ready says which, and /capabilities answers 503.
    try:
        app.state.catalogue = load_catalogue(settings.catalogue_path)
        app.state.catalogue_status = "ok"
    except CatalogueError as err:
        app.state.catalogue = None
        app.state.catalogue_status = err.reason
    install_error_handling(app)
    app.include_router(router)
    if dist is not None:
        _serve_frontend(app, dist)
    return app
