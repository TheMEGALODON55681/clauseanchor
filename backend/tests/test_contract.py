"""The JSON form of a parsed document, its schema, and the command line that prints it."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.parsing import ParsedDocument, parse_document
from app.parsing.errors import MAX_INPUT_BYTES
from app.parsing.schema import SCHEMA, to_json
from app.scripts.parse_file import main
from tests.fixtures.build import (
    VALID_NAMES,
    Fixtures,
    abstract_num,
    build_docx,
    level_xml,
    listed,
    num_xml,
    related_part,
)

SCHEMA_FILE = Path(__file__).parents[2] / "docs" / "app" / "parser_output.schema.json"


def _is(value: object, name: str) -> bool:
    if name in ("integer", "number") and isinstance(value, bool):
        return False
    python = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": int | float,
        "boolean": bool,
        "null": type(None),
    }[name]
    return isinstance(value, python)


def violations(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """A checker for the small subset of JSON Schema that schema.py uses: type, enum, pattern,
    minimum, required, properties, additionalProperties, items, minItems, maxItems and $ref
    into $defs. Returns one line per problem."""
    if "$ref" in schema:
        return violations(value, SCHEMA["$defs"][schema["$ref"].rsplit("/", 1)[1]], path)
    kinds = schema.get("type", [])
    names = [kinds] if isinstance(kinds, str) else kinds
    if names and not any(_is(value, name) for name in names):
        return [f"{path}: expected {names}"]
    found: list[str] = []
    if "enum" in schema and value not in schema["enum"]:
        found.append(f"{path}: not one of the allowed values")
    if (
        "pattern" in schema
        and isinstance(value, str)
        and not re.fullmatch(schema["pattern"], value)
    ):
        found.append(f"{path}: does not match its pattern")
    if "minimum" in schema and isinstance(value, int | float) and value < schema["minimum"]:
        found.append(f"{path}: below the minimum")
    if isinstance(value, dict):
        found += [
            f"{path}.{key}: missing" for key in schema.get("required", []) if key not in value
        ]
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                found += violations(item, properties[key], f"{path}.{key}")
            elif extra is False:
                found.append(f"{path}.{key}: not allowed")
            elif isinstance(extra, dict):
                found += violations(item, extra, f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get(
            "maxItems", len(value)
        ):
            found.append(f"{path}: wrong length")
        for index, item in enumerate(value):
            found += violations(item, schema.get("items", {}), f"{path}[{index}]")
    return found


def as_sent(doc: ParsedDocument, *, text: bool) -> dict[str, Any]:
    """The document as it arrives after a round trip through JSON."""
    return json.loads(json.dumps(to_json(doc, text=text)))


# The JSON form and its schema


@pytest.mark.parametrize("text", [True, False], ids=["with_text", "without_text"])
@pytest.mark.parametrize("name", VALID_NAMES)
def test_every_parsed_fixture_matches_the_schema(name: str, text: bool, fixtures: Fixtures) -> None:
    doc = parse_document(fixtures[name][0].read_bytes())
    assert violations(as_sent(doc, text=text), SCHEMA) == []


def without_text(full: dict[str, Any]) -> dict[str, Any]:
    """What the text-free form must equal: the full form minus every field that holds the file's
    own words, which are the text fields, a Word numbering label and a defined term."""
    bare = copy.deepcopy(full)
    del bare["source_text"]
    for block in bare["blocks"]:
        del block["text"]
        block["locator"].pop("list_label", None)
    for node in bare["nodes"]:
        del node["text"]
        if node["kind"] == "definition":
            node["label"] = None
    return bare


def test_the_text_fields_are_left_out_and_nothing_else(fixtures: Fixtures) -> None:
    doc = parse_document(fixtures["simple.docx"][0].read_bytes())
    full, bare = as_sent(doc, text=True), as_sent(doc, text=False)
    assert "source_text" in full
    assert "source_text" not in bare
    assert all("text" in item for item in [*full["blocks"], *full["nodes"]])
    assert not any("text" in item for item in [*bare["blocks"], *bare["nodes"]])
    assert without_text(full) == bare


def labelled_docx() -> bytes:
    """A numbered paragraph whose level text is free text, a numbered paragraph the structure
    builder reads as a clause, and a defined term."""
    numbering = related_part(
        "numbering",
        abstract_num(0, level_xml(0, "decimal", "Clause %1 SECRET-LABEL"))
        + abstract_num(1, level_xml(0, "decimal", "%1."))
        + num_xml(1, 0)
        + num_xml(2, 1),
    )
    body = (
        listed("Numbered by free text.", num_id=1)
        + listed("Fees are payable.", num_id=2)
        + listed('"Secret Widget Pricing" means the list price.')
    )
    return build_docx(body, [numbering])


def test_text_free_output_leaves_out_the_numbering_text_and_the_defined_term() -> None:
    doc = parse_document(labelled_docx())
    full = as_sent(doc, text=True)
    bare = as_sent(doc, text=False)
    assert "SECRET-LABEL" in json.dumps(full)
    assert [n["label"] for n in full["nodes"] if n["kind"] == "definition"] == [
        "Secret Widget Pricing"
    ]
    assert "SECRET-LABEL" not in json.dumps(bare)
    assert "Secret Widget Pricing" not in json.dumps(bare)
    assert violations(bare, SCHEMA) == []
    assert without_text(full) == bare
    assert as_sent(doc, text=True) == full  # building the text-free form left the document alone


def test_offsets_slice_back_to_the_text_after_a_trip_through_json(fixtures: Fixtures) -> None:
    sent = as_sent(parse_document(fixtures["simple.pdf"][0].read_bytes()), text=True)
    for item in [*sent["blocks"], *sent["nodes"]]:
        assert sent["source_text"][item["start"] : item["end"]] == item["text"]


def test_the_checker_catches_a_document_that_breaks_the_schema(fixtures: Fixtures) -> None:
    good = as_sent(parse_document(fixtures["simple.pdf"][0].read_bytes()), text=True)
    assert violations(good, SCHEMA) == []

    def broken(change: Any) -> list[str]:
        bad = copy.deepcopy(good)
        change(bad)
        return violations(bad, SCHEMA)

    assert broken(lambda d: d.update(extra=1))
    assert broken(lambda d: d.pop("coverage"))
    assert broken(lambda d: d.update(text_sha256="XYZ"))
    assert broken(lambda d: d["blocks"][0].update(kind="margin"))
    assert broken(lambda d: d["blocks"][0].update(start="0"))
    assert broken(lambda d: d["blocks"][0].update(bbox=[1, 2, 3]))
    assert broken(lambda d: d["blocks"][0]["locator"].update(page=[1]))
    assert broken(
        lambda d: d["warnings"].append({"code": "NOT_A_CODE", "page": None, "detail": None})
    )
    assert broken(lambda d: d["coverage"].update(partial="no"))


def test_the_committed_schema_file_is_the_schema() -> None:
    assert json.loads(SCHEMA_FILE.read_text(encoding="utf-8")) == SCHEMA


# The command line (A23)


def run(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    status = main(list(args))
    captured = capsys.readouterr()
    return status, captured.out, captured.err


def test_the_cli_prints_json_without_any_text_field_by_default(
    fixtures: Fixtures, capsys: pytest.CaptureFixture[str]
) -> None:
    path = fixtures["simple.pdf"][0]
    status, out, err = run(capsys, str(path))
    assert status == 0
    assert err == ""
    sent = json.loads(out)
    assert violations(sent, SCHEMA) == []
    assert "source_text" not in sent
    assert not any("text" in item for item in [*sent["blocks"], *sent["nodes"]])
    assert sent == as_sent(parse_document(path.read_bytes()), text=False)


def test_the_cli_prints_the_text_with_the_text_flag(
    fixtures: Fixtures, capsys: pytest.CaptureFixture[str]
) -> None:
    path = fixtures["simple.docx"][0]
    status, out, _ = run(capsys, str(path), "--text")
    assert status == 0
    assert json.loads(out) == as_sent(parse_document(path.read_bytes()), text=True)


def test_the_cli_summary_counts_what_the_parser_found(
    fixtures: Fixtures, capsys: pytest.CaptureFixture[str]
) -> None:
    path = fixtures["simple.pdf"][0]
    doc = parse_document(path.read_bytes())
    status, out, _ = run(capsys, str(path), "--summary")
    assert status == 0
    assert out.splitlines() == [
        f"pages: {doc.page_count}",
        f"blocks: {len(doc.blocks)}",
        f"nodes: {len(doc.nodes)}",
        f"decorations: {len(doc.decorations)}",
        f"warnings: {len(doc.warnings)}",
        f"partial: {'yes' if doc.coverage.partial else 'no'}",
    ]


def test_the_cli_summary_of_a_docx_has_no_page_count(
    fixtures: Fixtures, capsys: pytest.CaptureFixture[str]
) -> None:
    _, out, _ = run(capsys, str(fixtures["simple.docx"][0]), "--summary")
    assert out.splitlines()[0] == "pages: none"


def test_the_cli_refuses_a_file_over_the_limit_without_reading_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    big = tmp_path / "big.pdf"
    with big.open("wb") as handle:
        handle.truncate(MAX_INPUT_BYTES + 1)

    def read(self: Path) -> bytes:
        raise AssertionError("the file was read")

    monkeypatch.setattr(Path, "read_bytes", read)
    status, out, err = run(capsys, str(big))
    assert (status, out, err.strip()) == (2, "", "FILE_TOO_LARGE")


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("corrupt_zip.docx", "MALFORMED_FILE"),
        ("encrypted.pdf", "ENCRYPTED_PDF"),
        ("scanned.pdf", "SCANNED_PDF"),
    ],
)
def test_a_parse_error_prints_its_code_and_exits_with_status_2(
    name: str, code: str, fixtures: Fixtures, capsys: pytest.CaptureFixture[str]
) -> None:
    status, out, err = run(capsys, str(fixtures[name][0]))
    assert status == 2
    assert out == ""
    assert err.strip() == code
