"""2-E: the committed OpenAPI schema, API.md against it, and the fields it must never hold."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.parsing.schema import SCHEMA as PARSER_SCHEMA
from app.scripts.export_openapi import OPENAPI_PATH, build_schema, main

API_MD = Path(__file__).parents[2] / "docs" / "app" / "API.md"
METHODS = {"get", "post", "put", "patch", "delete"}
HEADING = re.compile(r"^### `(GET|POST|PUT|PATCH|DELETE) (/\S+)`$", re.MULTILINE)
# A field named for a score, a verdict, a percentage or a risk or safety reading (API.md section 1)
FORBIDDEN = re.compile(r"score|verdict|percent|risk|safety", re.IGNORECASE)


@pytest.fixture(scope="module")
def api_md() -> str:
    return API_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    return json.loads(build_schema())


def routes_of(spec: dict[str, Any]) -> set[tuple[str, str]]:
    return {(m.upper(), p) for p, item in spec["paths"].items() for m in item if m in METHODS}


def gaps(api_md: str, spec: dict[str, Any]) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """(in API.md only, in the schema only)."""
    documented = set(HEADING.findall(api_md))
    return documented - routes_of(spec), routes_of(spec) - documented


def field_names(node: object) -> set[str]:
    """Every property name in a JSON Schema or an OpenAPI document, at any depth."""
    found: set[str] = set()
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            found |= set(props)
        for value in node.values():
            found |= field_names(value)
    elif isinstance(node, list):
        for value in node:
            found |= field_names(value)
    return found


# The committed file


def test_the_committed_schema_is_what_the_app_builds() -> None:
    # Git stores the file with LF. A Windows checkout with autocrlf turns them into CRLF.
    committed = OPENAPI_PATH.read_bytes().replace(b"\r\n", b"\n") if OPENAPI_PATH.exists() else b""
    assert committed == build_schema().encode("utf-8"), (
        "docs/app/openapi.json is out of date. From backend/, run: "
        "python -m app.scripts.export_openapi"
    )


def test_the_schema_has_sorted_keys_one_trailing_newline_and_only_ascii() -> None:
    text = build_schema()
    assert text.endswith("}\n") and not text.endswith("\n\n")
    assert text == json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n"
    assert text.isascii()


def test_the_script_writes_exactly_what_the_test_compares(tmp_path: Path) -> None:
    out = tmp_path / "openapi.json"
    main(out)
    assert out.read_bytes() == build_schema().encode("utf-8")
    assert b"\r" not in out.read_bytes()


# API.md against the schema


def test_every_route_in_api_md_is_in_the_schema_and_every_schema_route_is_in_api_md(
    api_md: str, spec: dict[str, Any]
) -> None:
    assert gaps(api_md, spec) == (set(), set())


def test_the_gap_check_sees_a_route_missing_from_either_side(
    api_md: str, spec: dict[str, Any]
) -> None:
    without_health = api_md.replace("### `GET /api/v1/health`", "### Health")
    assert gaps(without_health, spec) == (set(), {("GET", "/api/v1/health")})
    extra = api_md + "\n### `PATCH /api/v1/documents/{document_id}/party`\n"
    assert gaps(extra, spec) == ({("PATCH", "/api/v1/documents/{document_id}/party")}, set())


# No score, verdict or percentage


def test_no_field_in_the_schema_or_the_parser_output_is_a_score_a_verdict_or_a_percentage(
    spec: dict[str, Any],
) -> None:
    names = field_names(spec) | field_names(PARSER_SCHEMA)
    assert len(names) > 50  # the scan really walked both documents
    assert {n for n in names if FORBIDDEN.search(n)} == set()


def test_the_field_scan_sees_a_score_buried_in_a_schema() -> None:
    doctored = {
        "components": {
            "schemas": {
                "X": {
                    "properties": {
                        "a": {"items": [{"properties": {"risk_score": {"type": "number"}}}]}
                    }
                }
            }
        }
    }
    assert {n for n in field_names(doctored) if FORBIDDEN.search(n)} == {"risk_score"}
