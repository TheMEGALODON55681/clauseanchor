from __future__ import annotations

import hashlib
import io
import logging
import random
import zipfile

import pytest
from pdfplumber.page import Page

from app.parsing.assemble import TextAssembler
from app.parsing.detect import detect_type
from app.parsing.errors import ErrorCode, ParseError, WarningCode
from app.parsing.model import ParsedDocument, ParseWarning
from app.parsing.pdf import parse_pdf
from tests.fixtures.build import PAGE_HEIGHT, PAGE_WIDTH

SWEEP_MUTANTS = 300


def texts(doc: ParsedDocument) -> list[str]:
    return [block.text for block in doc.blocks]


def make_zip(*names: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, b"<x/>")
    return buffer.getvalue()


# detect_type


def test_detect_type_names_a_pdf_and_a_docx(fixture_bytes: dict[str, bytes]) -> None:
    assert detect_type(fixture_bytes["simple.pdf"]) == "pdf"
    assert detect_type(make_zip("[Content_Types].xml", "word/document.xml")) == "docx"


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"", ErrorCode.EMPTY_FILE),
        (b"plain text", ErrorCode.UNSUPPORTED_TYPE),
        (
            b"\xd0\xcf\x11\xe0" + bytes(64),
            ErrorCode.UNSUPPORTED_TYPE,
        ),  # legacy .doc, encrypted OOXML
        (make_zip("xl/workbook.xml"), ErrorCode.UNSUPPORTED_TYPE),
        (make_zip("word/document.xml", "word/vbaProject.bin"), ErrorCode.UNSUPPORTED_TYPE),
        (b"PK\x03\x04" + b"junk" * 16, ErrorCode.MALFORMED_FILE),
    ],
)
def test_detect_type_rejects_with_a_fixed_code(data: bytes, code: ErrorCode) -> None:
    with pytest.raises(ParseError) as exc:
        detect_type(data)
    assert exc.value.code == code
    assert exc.value.__context__ is None or exc.value.__suppress_context__


# parse_pdf: text, order and offsets


def test_simple_pdf_gives_numbered_clauses_as_blocks_with_page_separators(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["simple.pdf"])
    assert texts(doc) == [
        "SERVICES AGREEMENT",
        "1. Definitions",
        "1.1 In this Agreement the following\nwords have these meanings.",
        '(a) "Services" means the work',
        "(i) described in Schedule 1.",
        "2. Term",
        "2.1 This Agreement starts on the Effective Date.",
    ]
    assert doc.source_text == (
        "SERVICES AGREEMENT\n1. Definitions\n1.1 In this Agreement the following\n"
        'words have these meanings.\n(a) "Services" means the work\n(i) described in '
        "Schedule 1.\n\n2. Term\n2.1 This Agreement starts on the Effective Date."
    )
    assert [b.page for b in doc.blocks] == [1, 1, 1, 1, 1, 2, 2]
    assert [dict(b.locator) for b in doc.blocks] == [
        {"page": 1, "block": 1},
        {"page": 1, "block": 2},
        {"page": 1, "block": 3},
        {"page": 1, "block": 4},
        {"page": 1, "block": 5},
        {"page": 2, "block": 1},
        {"page": 2, "block": 2},
    ]
    assert {b.kind for b in doc.blocks} == {"text"}
    assert doc.media_type == "application/pdf"
    assert doc.page_count == 2
    assert doc.warnings == ()
    assert doc.decorations == ()
    assert (doc.coverage.pages_total, doc.coverage.pages_with_text) == (2, 2)
    assert (doc.coverage.chars, doc.coverage.partial) == (len(doc.source_text), False)
    assert doc.text_sha256 == hashlib.sha256(doc.source_text.encode("utf-8")).hexdigest()


def test_block_bboxes_sit_inside_the_page_and_wrap_the_text(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["simple.pdf"])
    for block in doc.blocks:
        assert block.bbox is not None
        x0, top, x1, bottom = block.bbox
        assert 0 <= x0 < x1 <= PAGE_WIDTH
        assert 0 <= top < bottom <= PAGE_HEIGHT
    title = doc.blocks[0].bbox
    assert title is not None
    assert title[0] == pytest.approx(72.0, abs=0.5)
    assert title[1] == pytest.approx(90 - 14, abs=4)


def test_two_columns_read_left_column_then_right_after_a_full_width_title(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["two_column.pdf"])
    assert texts(doc) == [
        "TWO COLUMN AGREEMENT",
        "Left one alpha beta gamma\nLeft two delta epsilon\nLeft three zeta eta\n"
        "Left four theta iota",
        "Right one kappa lambda mu\nRight two nu xi omicron\nRight three pi rho sigma\n"
        "Right four tau upsilon phi",
    ]
    assert doc.warnings == ()


def test_a_wrapped_paragraph_stays_one_block_and_spacing_starts_the_next(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["long_lines.pdf"])
    assert len(doc.blocks) == 2
    assert doc.blocks[0].text.count("\n") == 4
    assert doc.blocks[0].text.startswith("The Supplier shall provide")
    assert doc.blocks[1].text.startswith("The Customer shall pay")


def test_a_word_hyphenated_across_a_line_break_is_left_as_it_is(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["long_lines.pdf"])
    assert "the parties agree-\nment becomes effective" in doc.source_text


def test_ligatures_survive_and_space_runs_and_nbsp_become_single_spaces(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["latin_unicode.pdf"])
    assert doc.source_text == (
        "\u201cSmart\u201d quotes and caf\u00e9 na\u00efve\n"
        "Non breaking double spaces\n"
        "\ufb01nal terms"
    )
    assert "\ufb01" in doc.source_text


def test_hanging_indents_keep_a_clause_together_and_a_return_to_the_edge_starts_a_block(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["tight_clauses.pdf"])
    assert texts(doc) == [
        "1.1 The Supplier shall perform the Services\nwith reasonable skill and care.",
        "1.2 The Customer shall pay the Charges\nwithin thirty days of invoice.",
        '"Force Majeure" means an event beyond\nthe reasonable control of a party.',
        '"Party" means a party to this Agreement.',
    ]


def test_a_blank_page_adds_no_block_and_keeps_the_page_numbers(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["blank_page.pdf"])
    assert doc.source_text == "1. First page\n\n3. Third page"
    assert [b.page for b in doc.blocks] == [1, 3]
    assert (doc.coverage.pages_total, doc.coverage.pages_with_text) == (3, 2)


def test_a_page_that_opens_on_an_indented_tail_still_splits_later_hanging_paragraphs(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["hanging_page_break.pdf"])
    assert [(b.page, b.text) for b in doc.blocks] == [
        (
            1,
            '"Term" means the period that starts on the Effective Date\n'
            "and runs until this Agreement ends",
        ),
        (2, "or is terminated under clause 9 or clause 10."),
        (2, '"Fee" means the amount payable\nunder Schedule 2.'),
        (2, '"Day" means a calendar day.'),
    ]


def test_a_first_line_indent_does_not_cut_a_paragraph_after_its_first_line(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["first_line_indent.pdf"])
    assert [b.text.count("\n") for b in doc.blocks] == [0, 2, 2, 2]
    assert doc.blocks[2].text.startswith("The Customer shall pay")


def test_page_numbers_far_right_stay_on_their_row_and_raise_no_warning(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["contents.pdf"])
    assert doc.source_text == ("CONTENTS\n1. Definitions 3\n2. Term 5\n3. Fees 7\n4. Termination 9")
    assert doc.warnings == ()


def test_a_word_with_no_text_is_dropped_before_layout(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    # A font whose ToUnicode map is damaged can give a word with no characters. Layout divides
    # by word length, and an empty line would reach the assembler as an empty block.
    clean = parse_pdf(fixture_bytes["simple.pdf"])
    real = Page.extract_words
    empty = {"text": "", "x0": 72.0, "x1": 72.0, "top": 60.0, "bottom": 70.0}
    monkeypatch.setattr(Page, "extract_words", lambda self, **kw: [*real(self, **kw), empty])
    assert parse_pdf(fixture_bytes["simple.pdf"]) == clean


def test_a_table_page_keeps_top_to_bottom_order_and_warns_of_more_than_two_columns(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["three_column_table.pdf"])
    assert doc.source_text == (
        "PRICE SCHEDULE\nItem Quantity Price\nSteel bolt 10 0.50\nBrass nut 25 0.20\n"
        "Copper wire 5 3.10\nRubber seal 12 0.75"
    )
    assert doc.warnings == (ParseWarning(WarningCode.MORE_THAN_TWO_COLUMNS, page=1),)


def test_a_full_width_line_between_column_rows_warns_that_order_is_uncertain(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["column_uncertain.pdf"])
    assert texts(doc) == [
        "Left alpha one\nLeft alpha two",
        "Right alpha one\nRight alpha two",
        "This wide line deliberately crosses the gutter between the two columns",
        "Left beta one\nLeft beta two",
        "Right beta one\nRight beta two",
    ]
    assert doc.warnings == (ParseWarning(WarningCode.COLUMN_ORDER_UNCERTAIN, page=1),)


# parse_pdf: errors (A1)


def test_a_truncated_file_raises_malformed_file_with_no_context_and_only_the_code(
    fixture_bytes: dict[str, bytes],
) -> None:
    with pytest.raises(ParseError) as exc:
        parse_pdf(fixture_bytes["malformed.pdf"])
    assert exc.value.code == ErrorCode.MALFORMED_FILE
    assert str(exc.value) == "MALFORMED_FILE"
    assert exc.value.__suppress_context__


def test_a_password_protected_file_raises_encrypted_pdf(
    fixture_bytes: dict[str, bytes],
) -> None:
    with pytest.raises(ParseError) as exc:
        parse_pdf(fixture_bytes["encrypted.pdf"])
    assert exc.value.code == ErrorCode.ENCRYPTED_PDF
    assert exc.value.__suppress_context__


def test_an_empty_block_from_the_assembler_stays_a_value_error(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    # A1 puts ValueError in the PDF catch tuple. The assembler call must sit outside that try,
    # or this caller bug would come back as MALFORMED_FILE.
    real = TextAssembler.add_block
    monkeypatch.setattr(
        TextAssembler, "add_block", lambda self, lines, **kw: real(self, [""], **kw)
    )
    with pytest.raises(ValueError, match="block has no text") as exc:
        parse_pdf(fixture_bytes["simple.pdf"])
    assert not isinstance(exc.value, ParseError)


def test_byte_flipped_files_give_a_parse_or_a_parse_error_and_leak_nothing(
    fixture_bytes: dict[str, bytes], caplog: pytest.LogCaptureFixture
) -> None:
    original = fixture_bytes["simple.pdf"]
    words = ("SERVICES", "Definitions", "Supplier", "Effective", "Schedule")
    rng = random.Random(20261015)
    caplog.set_level(logging.DEBUG)
    parsed = rejected = 0
    for _ in range(SWEEP_MUTANTS):
        mutant = bytearray(original)
        for _ in range(rng.randint(1, 4)):
            mutant[rng.randrange(len(mutant))] ^= rng.randint(1, 255)
        try:
            doc = parse_pdf(bytes(mutant))
        except ParseError as error:
            rejected += 1
            assert str(error) == error.code.value
            assert error.__context__ is None or error.__suppress_context__
        else:
            parsed += 1
            assert doc.source_text[doc.blocks[0].start : doc.blocks[0].end] == doc.blocks[0].text
    assert parsed and rejected  # the sweep reaches both outcomes
    assert [r for r in caplog.records if r.name.startswith("pdfminer")] == []
    assert not [r for r in caplog.records if any(w in r.getMessage() for w in words)]
