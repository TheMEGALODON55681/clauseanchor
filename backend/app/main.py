"""The FastAPI app. `create_app(settings)` builds one, so tests bring their own settings.

Run it with `uvicorn app.main:create_app --factory`, which reads the environment.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.errors import install_error_handling
from app.api.routes import router
from app.config import Settings
from app.services.scope import CatalogueError, load_catalogue


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = Settings.from_env() if settings is None else settings
    # The interactive docs pages load their scripts from a CDN, and every route sits under /api/v1
    app = FastAPI(
        title="ClauseAnchor API",
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )
    app.state.settings = settings
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
