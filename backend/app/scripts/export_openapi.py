"""Development tool: writes docs/app/openapi.json, the app's OpenAPI document (API.md section 11).

    python -m app.scripts.export_openapi

Run it from backend/ after any change to a route or a response model. A test fails while the
committed file differs from what the app builds."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings
from app.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parents[3] / "docs" / "app" / "openapi.json"


def build_schema() -> str:
    """The document as text, with sorted keys, a two-space indent, ASCII only and one trailing
    newline, so the same app gives the same bytes. The settings are the dataclass defaults and
    not the environment: stub mode and an in-memory database. The app is built and never started,
    so no worker thread and no child process runs."""
    app = create_app(Settings())
    try:
        spec = app.openapi()
    finally:
        app.state.store.close()
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def main(path: Path = OPENAPI_PATH) -> None:
    path.write_bytes(build_schema().encode("utf-8"))
    print(f"wrote {path.name}")


if __name__ == "__main__":
    main()
