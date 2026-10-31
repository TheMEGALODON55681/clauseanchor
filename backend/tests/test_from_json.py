"""from_json: the parent process rebuilds the ParsedDocument that the child sent as JSON (2-C)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.parsing import parse_document
from app.parsing.schema import from_json, to_json
from tests.fixtures.build import VALID_NAMES

DATA = Path(__file__).parents[2] / "data"
SMOKE = sorted([*DATA.glob("cuad_smoke/*/*"), *DATA.glob("docx_smoke/*/*.docx")])


def over_the_wire(data: dict) -> dict:
    """What the parent sees: the child's JSON, decoded, so every tuple is a list."""
    return json.loads(json.dumps(data))


def assert_round_trip(raw: bytes) -> None:
    doc = parse_document(raw)
    form = to_json(doc)
    assert to_json(from_json(form)) == form
    assert to_json(from_json(over_the_wire(form))) == form
    assert from_json(over_the_wire(form)) == doc


@pytest.mark.parametrize("name", VALID_NAMES)
def test_every_fixture_survives_the_round_trip(name: str, fixture_bytes: dict[str, bytes]) -> None:
    assert_round_trip(fixture_bytes[name])


@pytest.mark.skipif(not SMOKE, reason="the real-file smoke set is not on this machine")
@pytest.mark.parametrize("path", SMOKE, ids=[f"smoke-{i}" for i in range(len(SMOKE))])
def test_every_smoke_file_survives_the_round_trip(path: Path) -> None:
    assert_round_trip(path.read_bytes())


def test_the_rebuilt_document_has_the_parser_types(fixture_bytes: dict[str, bytes]) -> None:
    doc = from_json(over_the_wire(to_json(parse_document(fixture_bytes["simple.pdf"]))))
    assert isinstance(doc.blocks, tuple)
    assert isinstance(doc.nodes, tuple)
    assert isinstance(doc.warnings, tuple)
    assert all(isinstance(pair, tuple) for pair in doc.decorations)
    assert all(isinstance(block.bbox, tuple) for block in doc.blocks)
    assert doc.source_text[doc.blocks[0].start : doc.blocks[0].end] == doc.blocks[0].text


def test_a_changed_text_is_rejected(fixture_bytes: dict[str, bytes]) -> None:
    form = over_the_wire(to_json(parse_document(fixture_bytes["simple.pdf"])))
    form["source_text"] = "X" + form["source_text"][1:]
    with pytest.raises(ValueError, match="text_sha256"):
        from_json(form)


def test_a_changed_hash_is_rejected(fixture_bytes: dict[str, bytes]) -> None:
    form = over_the_wire(to_json(parse_document(fixture_bytes["simple.pdf"])))
    form["text_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="text_sha256"):
        from_json(form)


def test_the_text_free_form_cannot_be_rebuilt(fixture_bytes: dict[str, bytes]) -> None:
    doc = parse_document(fixture_bytes["simple.pdf"])
    with pytest.raises(ValueError, match="text_sha256"):
        from_json(to_json(doc, text=False))


def test_the_error_message_holds_no_document_text(fixture_bytes: dict[str, bytes]) -> None:
    doc = parse_document(fixture_bytes["simple.pdf"])
    form = over_the_wire(to_json(replace(doc, text_sha256="0" * 64)))
    with pytest.raises(ValueError) as err:
        from_json(form)
    assert doc.source_text[:20] not in str(err.value)
