from __future__ import annotations

import pytest

import app.parsing as parsing
from app.parsing import ErrorCode, ParseError, WarningCode, parse_document
from app.parsing.docx import parse_docx
from app.parsing.errors import MAX_INPUT_BYTES
from app.parsing.pdf import parse_pdf
from tests.fixtures.build import NAMES, Fixtures, build_docx
from tests.test_invariants import assert_valid_nodes

# A paragraph that anchors a VML text box, so the reader raises TEXT_BOX_CONTENT.
_BOX = (
    "<w:p><w:r><w:pict><v:shape><v:textbox><w:txbxContent>"
    "<w:p><w:r><w:t>Boxed.</w:t></w:r></w:p>"
    "</w:txbxContent></v:textbox></v:shape></w:pict></w:r></w:p>"
)


def paragraph(text: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


def test_only_the_entry_point_the_models_and_the_code_lists_are_public() -> None:
    assert set(parsing.__all__) == {
        "ErrorCode",
        "ParseError",
        "ParsedDocument",
        "WarningCode",
        "parse_document",
    }


@pytest.mark.parametrize("name", NAMES)
def test_every_fixture_parses_or_raises_its_registered_code(name: str, fixtures: Fixtures) -> None:
    path, expected = fixtures[name]
    data = path.read_bytes()
    if expected is not None:
        with pytest.raises(ParseError) as exc:
            parse_document(data)
        assert exc.value.code == expected
        return
    doc = parse_document(data)
    direct = (parse_docx if name.endswith(".docx") else parse_pdf)(data)
    assert doc.source_text == direct.source_text
    assert doc.blocks == direct.blocks
    assert_valid_nodes(doc, doc.nodes)


def test_the_structure_tree_is_attached_to_the_parsed_document(fixtures: Fixtures) -> None:
    doc = parse_document(fixtures["simple.docx"][0].read_bytes())
    assert [(n.kind, n.label) for n in doc.nodes] == [
        ("heading", None),
        ("section", "1"),
        ("clause", "1.1"),
        ("subclause", "(a)"),
        ("definition", "Services"),
        ("section", "2"),
        ("clause", "2.1"),
    ]


def test_reader_warnings_come_first_and_structure_warnings_follow() -> None:
    # (i) to (v) after (a) to (u) continue both the letters and a numeral run, which is the
    # structure builder's ambiguity warning.
    letters = "".join(paragraph(f"({c}) Item.") for c in "abcdefghijklmnopqrstu")
    numerals = "".join(paragraph(f"({n}) Item.") for n in ("i", "ii", "iii", "iv", "v"))
    doc = parse_document(build_docx(_BOX + paragraph("1.1 Intro.") + letters + numerals))
    assert [w.code for w in doc.warnings] == [
        WarningCode.TEXT_BOX_CONTENT,
        WarningCode.NUMBERING_AMBIGUOUS,
    ]


def test_empty_input_is_rejected() -> None:
    with pytest.raises(ParseError) as exc:
        parse_document(b"")
    assert exc.value.code == ErrorCode.EMPTY_FILE


def test_input_over_the_size_limit_is_rejected_before_its_type_is_read() -> None:
    with pytest.raises(ParseError) as exc:
        parse_document(b"%PDF-" + bytes(MAX_INPUT_BYTES))
    assert exc.value.code == ErrorCode.FILE_TOO_LARGE


def test_input_of_exactly_the_size_limit_is_read() -> None:
    with pytest.raises(ParseError) as exc:
        parse_document(b"PK\x03\x04" + bytes(MAX_INPUT_BYTES - 4))
    assert exc.value.code == ErrorCode.MALFORMED_FILE


def test_a_file_that_is_neither_pdf_nor_docx_is_unsupported() -> None:
    with pytest.raises(ParseError) as exc:
        parse_document(b"plain text, not a document")
    assert exc.value.code == ErrorCode.UNSUPPORTED_TYPE
