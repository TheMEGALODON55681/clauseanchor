from __future__ import annotations

import hashlib

import pytest

from app.parsing.assemble import TextAssembler
from app.parsing.errors import MAX_TEXT_CHARS, ErrorCode, ParseError, WarningCode
from app.parsing.model import Block, BlockKind, ParsedDocument, ParseWarning

PDF = "application/pdf"


def add(asm: TextAssembler, *lines: str, kind: BlockKind = "text", page: int | None = 1) -> Block:
    return asm.add_block(lines, kind=kind, page=page, bbox=None, locator={})


def build(asm: TextAssembler, page_count: int | None = 1) -> ParsedDocument:
    return asm.build(media_type=PDF, page_count=page_count)


def assert_invariant(doc: ParsedDocument) -> None:
    for block in doc.blocks:
        assert 0 <= block.start <= block.end <= len(doc.source_text)
        assert doc.source_text[block.start : block.end] == block.text
    assert doc.text_sha256 == hashlib.sha256(doc.source_text.encode("utf-8")).hexdigest()


def test_lines_join_with_newline_and_lose_trailing_spaces_and_tabs() -> None:
    asm = TextAssembler()
    add(asm, "a  ", "b\t", " c")
    doc = build(asm)
    assert doc.source_text == "a\nb\n c"
    assert_invariant(doc)


def test_separators_between_blocks_and_pages() -> None:
    asm = TextAssembler()
    add(asm, "one")
    add(asm, "two")
    asm.new_page()
    add(asm, "three", page=2)
    add(asm, "four", page=2)
    doc = build(asm, page_count=2)
    assert doc.source_text == "one\ntwo\n\nthree\nfour"
    assert_invariant(doc)


def test_new_page_adds_nothing_before_first_block_and_is_idempotent() -> None:
    asm = TextAssembler()
    asm.new_page()
    add(asm, "one")
    asm.new_page()
    asm.new_page()
    add(asm, "two", page=2)
    assert build(asm, page_count=2).source_text == "one\n\ntwo"


def test_crlf_and_bare_cr_become_lf() -> None:
    asm = TextAssembler()
    block = add(asm, "a \r\nb", "c\rd\r")
    doc = build(asm)
    assert block.text == "a\nb\nc\nd\n"
    assert_invariant(doc)


@pytest.mark.parametrize("lines", [(), ("",), (" \t",)])
def test_block_without_text_is_refused(lines: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        add(TextAssembler(), *lines)


def test_no_blocks_raises_no_text_found() -> None:
    with pytest.raises(ParseError) as exc:
        build(TextAssembler())
    assert exc.value.code == ErrorCode.NO_TEXT_FOUND


@pytest.mark.parametrize("lines", [("\u00a0",), ("", ""), (" ", "\u3000")])
def test_whitespace_only_text_raises_no_text_found(lines: tuple[str, ...]) -> None:
    asm = TextAssembler()
    add(asm, *lines)
    with pytest.raises(ParseError) as exc:
        build(asm)
    assert exc.value.code == ErrorCode.NO_TEXT_FOUND


def test_text_of_exactly_the_limit_is_accepted() -> None:
    asm = TextAssembler()
    add(asm, "x" * MAX_TEXT_CHARS)
    assert len(build(asm).source_text) == MAX_TEXT_CHARS == 500_000


def test_text_one_past_the_limit_raises_too_much_text_counting_separators() -> None:
    asm = TextAssembler()
    add(asm, "x" * (MAX_TEXT_CHARS - 1))
    with pytest.raises(ParseError) as exc:
        add(asm, "y")
    assert exc.value.code == ErrorCode.TOO_MUCH_TEXT
    assert str(exc.value) == "TOO_MUCH_TEXT"


@pytest.mark.parametrize(
    "sample",
    [
        "अनुबंध",
        "📄",
        "e\u0301",
        "\u201cquoted\u201d and \u2018single\u2019",
        "a\u00a0b",
        "\ufb01nal",
    ],
)
def test_unicode_survives_unchanged_with_code_point_offsets(sample: str) -> None:
    asm = TextAssembler()
    first = add(asm, sample)
    second = add(asm, "next")
    doc = build(asm)
    assert doc.source_text[first.start : first.end].encode("utf-8") == sample.encode("utf-8")
    assert second.start == len(sample) + 1
    assert_invariant(doc)


def test_lone_surrogate_raises_malformed_file_without_context() -> None:
    asm = TextAssembler()
    add(asm, "a\ud800b")
    with pytest.raises(ParseError) as exc:
        build(asm)
    assert exc.value.code == ErrorCode.MALFORMED_FILE
    assert exc.value.__suppress_context__


def test_blocks_get_sequential_ids_and_keep_their_fields() -> None:
    asm = TextAssembler()
    bbox = (1.0, 2.0, 3.0, 4.0)
    first = asm.add_block(["a"], kind="text", page=1, bbox=bbox, locator={"page": 1})
    second = asm.add_block(["b"], kind="table_cell", page=None, bbox=None, locator={"table": 0})
    assert first == Block("b0001", "text", 0, 1, "a", 1, bbox, {"page": 1})
    assert second == Block("b0002", "table_cell", 2, 3, "b", None, None, {"table": 0})
    assert build(asm).blocks == (first, second)


def test_decorations_are_the_header_and_footer_blocks() -> None:
    asm = TextAssembler()
    header = add(asm, "Header", kind="header")
    add(asm, "Body")
    add(asm, "Note", kind="footnote")
    footer = add(asm, "Page 1", kind="footer")
    doc = build(asm)
    assert doc.decorations == ((header.start, header.end), (footer.start, footer.end))
    assert_invariant(doc)


def test_coverage_and_metadata_for_a_pdf() -> None:
    asm = TextAssembler()
    add(asm, "one", page=1)
    asm.new_page()
    asm.new_page()
    add(asm, "three", page=3)
    warning = ParseWarning(WarningCode.BLANK_PAGE, page=2)
    doc = asm.build(media_type=PDF, page_count=3, warnings=[warning], partial=True)
    assert (doc.parser_version, doc.media_type, doc.page_count) == ("1.0.0", PDF, 3)
    assert doc.nodes == ()
    assert doc.warnings == (warning,)
    assert (doc.coverage.pages_total, doc.coverage.pages_with_text) == (3, 2)
    assert (doc.coverage.chars, doc.coverage.partial) == (len(doc.source_text), True)


def test_coverage_page_counts_are_none_for_a_docx() -> None:
    asm = TextAssembler()
    add(asm, "body", page=None)
    doc = asm.build(media_type="docx", page_count=None)
    assert (doc.coverage.pages_total, doc.coverage.pages_with_text) == (None, None)
    assert doc.coverage.partial is False
