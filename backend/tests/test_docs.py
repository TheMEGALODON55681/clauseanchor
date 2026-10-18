from __future__ import annotations

from pathlib import Path

import pytest

from app.api.errors import ERRORS

API_MD = Path(__file__).parents[2] / "docs" / "app" / "API.md"
SETTINGS = [
    "ANALYZER",
    "ARTIFACTS_DIR",
    "DB_PATH",
    "SESSION_TTL_MINUTES",
    "PARSE_KILL_SECONDS",
    "PARSE_QUEUE_LENGTH",
]


@pytest.fixture(scope="module")
def api_md() -> str:
    return API_MD.read_text(encoding="utf-8")


def test_api_md_lists_every_error_code(api_md: str) -> None:
    assert [code for code in ERRORS if f"`{code}`" not in api_md] == []


def test_api_md_lists_every_environment_variable(api_md: str) -> None:
    assert [n for n in SETTINGS if f"`CLAUSEANCHOR_{n}`" not in api_md] == []
