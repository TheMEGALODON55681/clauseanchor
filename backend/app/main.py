"""The FastAPI app. `create_app(settings)` builds one, so tests bring their own settings.

Run it with `uvicorn app.main:create_app --factory`, which reads the environment.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    # The analysis worker loads the analyzer in its own thread, about 25 s for the real model.
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


def create_app(settings: Settings | None = None, clock: Callable[[], float] = time.time) -> FastAPI:
    """`clock` is the one source of time for expiry, so tests move it by hand."""
    settings = Settings.from_env() if settings is None else settings
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
    return app
