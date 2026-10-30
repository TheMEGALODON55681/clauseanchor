from __future__ import annotations

from pathlib import Path

import pytest

from app.api.errors import ERRORS, JOB_ERRORS
from app.config import MAX_DOCUMENTS_PER_SESSION, MAX_SESSIONS, SWEEP_INTERVAL_SECONDS
from app.parsing import parse_document
from app.parsing.errors import ErrorCode
from app.services.parse_jobs import CHILD_CODES

API_MD = Path(__file__).parents[2] / "docs" / "app" / "API.md"
SETTINGS = [
    "ANALYZER",
    "ARTIFACTS_DIR",
    "DB_PATH",
    "SESSION_TTL_MINUTES",
    "PARSE_KILL_SECONDS",
    "PARSE_QUEUE_LENGTH",
    "PARSE_MEMORY_MIB",
]


@pytest.fixture(scope="module")
def api_md() -> str:
    return API_MD.read_text(encoding="utf-8")


def test_api_md_lists_every_error_code(api_md: str) -> None:
    assert [code for code in ERRORS if f"`{code}`" not in api_md] == []


def test_api_md_lists_every_environment_variable(api_md: str) -> None:
    assert [n for n in SETTINGS if f"`CLAUSEANCHOR_{n}`" not in api_md] == []


def test_api_md_names_each_limit_with_its_value(api_md: str) -> None:
    limits = {
        "MAX_SESSIONS": MAX_SESSIONS,
        "MAX_DOCUMENTS_PER_SESSION": MAX_DOCUMENTS_PER_SESSION,
        "SWEEP_INTERVAL_SECONDS": SWEEP_INTERVAL_SECONDS,
    }
    assert [n for n, v in limits.items() if f"`{n}` | {v} |" not in api_md] == []


def test_api_md_lists_every_job_error_code(api_md: str) -> None:
    assert [code for code in JOB_ERRORS if f"`{code}`" not in api_md] == []


def test_every_code_a_job_can_carry_has_a_message() -> None:
    carried = CHILD_CODES | {"PARSE_TIMEOUT", "PARSE_FAILED"}
    assert carried == set(JOB_ERRORS)
    # a parser code is either carried by a job or answered at the upload
    assert {code.value for code in ErrorCode} <= carried | set(ERRORS)
    for message, retryable in JOB_ERRORS.values():
        assert message.endswith(".")
        assert isinstance(retryable, bool)


def test_the_upload_media_types_are_the_ones_the_parser_writes(
    fixture_bytes: dict[str, bytes],
) -> None:
    from app.api.routes import _MEDIA_TYPES

    assert parse_document(fixture_bytes["simple.pdf"]).media_type == _MEDIA_TYPES["pdf"]
    assert parse_document(fixture_bytes["simple.docx"]).media_type == _MEDIA_TYPES["docx"]
