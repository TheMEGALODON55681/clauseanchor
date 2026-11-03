"""2-E: what a document read adds to the parser output and what it passes through unchanged
(API.md section 3, `GET /api/v1/documents/{document_id}`)."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
from fastapi.testclient import TestClient

import app.parsing
from app.api.routes import _document_json
from app.parsing import parse_document
from app.parsing.errors import WarningCode
from app.parsing.schema import to_json
from tests.fixtures.build import VALID_NAMES, build_docx
from tests.test_documents_api import get_document, open_session, settled, upload

# The warnings that set `coverage.partial` (ParserContract.md section 6)
PARTIAL_CODES = {
    WarningCode.PARTIALLY_SCANNED_PDF,
    WarningCode.UNMAPPED_GLYPHS,
    WarningCode.EMBEDDED_OBJECT,
    WarningCode.UNSUPPORTED_DOCX_FEATURE,
}
DETAIL_WORDS = {None, "altChunk", "unknown_block"}


def read(client: TestClient, raw: bytes) -> dict:
    """The `parsed` object of a document that went through upload, parse and read."""
    token = open_session(client)
    document_id, job_id = upload(client, token, raw)
    settled(client, token, job_id)
    response = get_document(client, token, document_id)
    assert response.status_code == 200
    return response.json()["parsed"]


def party_docx() -> bytes:
    """A made-up preamble: one party the detector can name and one it cannot (a name that
    starts in lower case reads as no name), then two clauses."""
    lines = (
        "BETWEEN",
        "Quillfeather Works Private Limited (hereinafter called the Buyer)",
        "AND",
        "marrowby holdings limited (hereinafter called the Seller)",
        "1. Term of the agreement.",
        "2. Fees and payment.",
    )
    return build_docx("".join(f"<w:p><w:r><w:t>{escape(t)}</w:t></w:r></w:p>" for t in lines))


# page on nodes


def test_a_pdf_node_has_the_page_of_the_block_that_holds_its_start(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    raw = fixture_bytes["simple.pdf"]
    parsed = read(client, raw)
    blocks = parse_document(raw).blocks
    for node in parsed["nodes"]:
        holder = next(b for b in blocks if b.start <= node["start"] < b.end)
        assert node["page"] == holder.page
    pages = {n["page"] for n in parsed["nodes"]}
    assert pages == {1, 2}
    # a node that starts inside a block, not at its start, still takes that block's page
    term = next(n for n in parsed["nodes"] if n["kind"] == "definition")
    assert all(b.start != term["start"] for b in blocks)
    assert term["page"] == 1


def test_a_docx_node_has_a_null_page(client: TestClient, fixture_bytes: dict[str, bytes]) -> None:
    nodes = read(client, fixture_bytes["simple.docx"])["nodes"]
    assert nodes
    assert all("page" in n and n["page"] is None for n in nodes)


@pytest.mark.parametrize("name", ["simple.pdf", "simple.docx"])
def test_the_read_adds_page_to_the_nodes_and_changes_nothing_else(
    client: TestClient, fixture_bytes: dict[str, bytes], name: str
) -> None:
    raw = fixture_bytes[name]
    parsed = read(client, raw)
    expected = json.loads(json.dumps(to_json(parse_document(raw))))
    assert [set(n) - set(m) for n, m in zip(parsed["nodes"], expected["nodes"], strict=True)] == [
        {"page"}
    ] * len(expected["nodes"])
    for node in parsed["nodes"]:
        del node["page"]
    assert parsed == expected


def test_a_node_whose_start_is_in_no_block_has_a_null_page(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_document(fixture_bytes["simple.pdf"])
    gap = doc.blocks[0].end  # the separator between the first two blocks
    assert all(not (b.start <= gap < b.end) for b in doc.blocks)
    lone = replace(doc.nodes[0], start=gap, end=gap + 1)
    assert _document_json(replace(doc, nodes=(lone,)))["nodes"][0]["page"] is None


# name_span


def test_a_party_node_has_a_name_span_and_no_other_node_has_the_key(client: TestClient) -> None:
    raw = party_docx()
    parsed = read(client, raw)
    text = parsed["source_text"]
    parties = [n for n in parsed["nodes"] if n["kind"] == "party"]
    assert len(parties) == 2
    assert all("name_span" in n for n in parties)
    assert all("name_span" not in n for n in parsed["nodes"] if n["kind"] != "party")
    span = parties[0]["name_span"]
    assert text[span["start"] : span["end"]] == "Quillfeather Works Private Limited"
    assert parties[0]["start"] <= span["start"] < span["end"] <= parties[0]["end"]
    assert parties[1]["name_span"] is None  # no name found: it reads as the whole node text


# parser warnings


def test_a_parser_warning_is_an_object_with_code_page_and_detail(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    scanned = read(client, fixture_bytes["partly_scanned.pdf"])["warnings"]
    assert {"code": "PARTIALLY_SCANNED_PDF", "page": 2, "detail": None} in scanned
    chunk = read(client, fixture_bytes["alt_chunk.docx"])["warnings"]
    assert {"code": "UNSUPPORTED_DOCX_FEATURE", "page": None, "detail": "altChunk"} in chunk
    for warning in scanned + chunk:
        assert isinstance(warning, dict)
        assert set(warning) == {"code", "page", "detail"}
        assert warning["code"] in {code.value for code in WarningCode}


@pytest.mark.parametrize(
    "name", ["scan_20_chars.pdf", "scan_199_chars.pdf", "free_text.pdf", "form_field.pdf"]
)
def test_a_searchable_scan_and_an_annotation_with_text_are_partial_with_no_warning(
    client: TestClient, fixture_bytes: dict[str, bytes], name: str
) -> None:
    parsed = read(client, fixture_bytes[name])
    assert parsed["coverage"]["partial"] is True
    assert {w["code"] for w in parsed["warnings"]}.isdisjoint(c.value for c in PARTIAL_CODES)


def test_no_fixture_gives_a_warning_detail_beyond_the_two_fixed_words(
    fixture_bytes: dict[str, bytes],
) -> None:
    seen = {w.detail for name in VALID_NAMES for w in parse_document(fixture_bytes[name]).warnings}
    assert seen <= DETAIL_WORDS
    assert seen - {None} == DETAIL_WORDS - {None}  # both are reached, so the check is not vacuous


def test_the_parser_builds_a_warning_detail_only_from_fixed_words() -> None:
    """`detail` reaches the client as it is, so it must never hold file text. Every place that
    builds a warning passes no detail, a literal, or the one name that is a choice of literals."""
    parsing = Path(app.parsing.__file__).parent
    checked = 0
    for path in parsing.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                position = {"ParseWarning": 2, "_warn": 1}.get(name or "")
                if position is None:
                    continue
                given = [k.value for k in node.keywords if k.arg == "detail"]
                if len(node.args) > position:
                    given.append(node.args[position])
                checked += 1
                for value in given:
                    assert isinstance(value, ast.Constant) or (
                        isinstance(value, ast.Name) and value.id == "detail"
                    ), f"{path.name}:{node.lineno} builds a detail from something else"
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "detail" for t in node.targets
            ):
                value = node.value
                branches = [value.body, value.orelse] if isinstance(value, ast.IfExp) else [value]
                assert all(isinstance(b, ast.Constant) for b in branches), (
                    f"{path.name}:{node.lineno} assigns a detail from something else"
                )
    assert checked >= 8  # the ParseWarning and _warn calls were found
