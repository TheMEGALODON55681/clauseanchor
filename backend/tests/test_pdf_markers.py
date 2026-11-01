"""Part 2-0D: a PDF line that opens with a list item marker starts a block, and the cut moves no
character of the text."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest

from app.parsing import pdf as pdf_module
from app.parsing.model import ParsedDocument
from app.parsing.pdf import parse_pdf
from tests.fixtures.build import GUARD_LINES, MARKER_LINES, VALID_NAMES, list_pdf
from tests.test_from_json import SMOKE

# The cut rule of parser 1.1.0, which 1.2.0 widens. The offset tests patch it back in.
RULE_1_1_0 = re.compile(r"(?:\d+(?:\.\d+)+\.?|\d+\.|\([A-Za-z0-9]{1,4}\))\s")

SHAPES = [
    ("a)", "b)"),
    ("(a)", "(b)"),
    ("1)", "2)"),
    ("(1)", "(2)"),
    ("i.", "ii."),
    ("(i)", "(ii)"),
    ("A.", "B."),
    ("iv)", "v)"),
    ("1.", "2."),
    ("1.1", "1.2"),
    ("(vii)", "(viii)"),
    ("II.", "III."),
]
PDF_NAMES = [name for name in VALID_NAMES if name.endswith(".pdf")]
SMOKE_PDFS = [path for path in SMOKE if path.suffix.lower() == ".pdf"]


def texts(doc: ParsedDocument) -> list[str]:
    return [block.text for block in doc.blocks]


def at_1_1_0(raw: bytes, monkeypatch: pytest.MonkeyPatch) -> ParsedDocument:
    monkeypatch.setattr(
        pdf_module, "_marker", lambda text: "numbering" if RULE_1_1_0.match(text) else None
    )
    return parse_pdf(raw)


@pytest.mark.parametrize(("first", "second"), SHAPES, ids=[a for a, _ in SHAPES])
def test_a_line_that_opens_with_a_list_marker_starts_a_block(first: str, second: str) -> None:
    lead = "The Supplier shall do the following:"
    lines = [lead, f"{first} deliver the items;", f"{second} provide the documents."]
    assert texts(parse_pdf(list_pdf(*lines))) == lines


@pytest.mark.parametrize("marker", ["a)", "i.", "1)", "(a)"])
def test_an_item_may_start_with_a_number(marker: str) -> None:
    lines = ["The notice periods are:", f"{marker} 30 days after notice;", f"{marker} 60 days."]
    assert texts(parse_pdf(list_pdf(*lines))) == lines


def test_a_bracketed_number_is_a_label_even_before_an_amount_word() -> None:
    lines = ["The rent is paid:", "(1) per month for the unit;", "(2) per day for any delay."]
    assert texts(parse_pdf(list_pdf(*lines))) == lines


@pytest.mark.parametrize("glyph", ["\N{BULLET}", "\N{MIDDLE DOT}"], ids=["bullet", "middle_dot"])
def test_a_bullet_glyph_starts_a_block(glyph: str) -> None:
    lines = ["The Supplier shall provide:", f"{glyph} the items;", f"{glyph} the documents."]
    assert texts(parse_pdf(list_pdf(*lines))) == lines


@pytest.mark.parametrize("glyph", pdf_module._BULLETS)
def test_every_glyph_of_the_bullet_set_is_a_marker(glyph: str) -> None:
    assert pdf_module._marker(f"{glyph} an item") == "item"


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("a) text", True),
        ("a)\ttext", True),
        ("a)", False),
        ("a) ", False),
        ("a)text", False),
        ("30 days after notice", False),
        ("\N{BULLET}", False),
    ],
)
def test_a_marker_needs_a_space_or_tab_and_then_text(line: str, expected: bool) -> None:
    assert (pdf_module._marker(line) is not None) is expected


@pytest.mark.parametrize("name", GUARD_LINES)
def test_a_line_that_only_looks_like_a_marker_stays_in_its_block(name: str) -> None:
    lines = GUARD_LINES[name]
    assert texts(parse_pdf(list_pdf(*lines))) == ["\n".join(lines)]


def test_a_marker_still_cuts_after_a_guard_line() -> None:
    lines = [*GUARD_LINES["initial"], "a) a real item"]
    assert len(parse_pdf(list_pdf(*lines)).blocks) == 2


def test_a_paragraph_that_returns_to_the_edge_after_indented_items_keeps_its_block(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["list_indented.pdf"])
    assert [b.text.count("\n") + 1 for b in doc.blocks] == [1, 1, 2, 1]
    assert doc.blocks[3].text.startswith("The Buyer shall pay")


def test_a_numbered_paragraph_with_a_first_line_indent_is_not_cut_at_its_second_line(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["numbered_first_line_indent.pdf"])
    assert [b.text.count("\n") + 1 for b in doc.blocks] == [1, 2, 2, 2]


def test_the_marker_fixture_has_one_block_per_line_where_1_1_0_fused_most_of_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = list_pdf(*MARKER_LINES)
    assert len(parse_pdf(raw).blocks) == len(MARKER_LINES)
    assert len(at_1_1_0(raw, monkeypatch).blocks) < len(MARKER_LINES) // 2


def assert_only_the_blocks_differ(raw: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    new = parse_pdf(raw)
    with monkeypatch.context() as patch:
        old = at_1_1_0(raw, patch)
    assert new.source_text == old.source_text
    assert new.text_sha256 == old.text_sha256
    # Everything else is equal too: the version, the decorations, the warnings and the coverage.
    assert replace(new, blocks=()) == replace(old, blocks=())


@pytest.mark.parametrize("name", PDF_NAMES)
def test_the_cut_moves_no_character_of_any_fixture(
    name: str, fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_only_the_blocks_differ(fixture_bytes[name], monkeypatch)


@pytest.mark.parametrize("name", [n for n in PDF_NAMES if n != "list_guards.pdf"])
def test_the_cut_loses_no_block_start_of_1_1_0(
    name: str, fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only a guard removes a cut, and list_guards.pdf is the file made of guard lines."""
    new = parse_pdf(fixture_bytes[name])
    old = at_1_1_0(fixture_bytes[name], monkeypatch)
    assert {b.start for b in old.blocks} <= {b.start for b in new.blocks}


@pytest.mark.skipif(not SMOKE_PDFS, reason="the real-file smoke set is not on this machine")
@pytest.mark.parametrize("path", SMOKE_PDFS, ids=[f"smoke-{i}" for i in range(len(SMOKE_PDFS))])
def test_the_cut_moves_no_character_of_a_smoke_file(
    path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_only_the_blocks_differ(path.read_bytes(), monkeypatch)
