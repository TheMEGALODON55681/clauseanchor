from __future__ import annotations

import base64
import binascii
import hashlib
import io
import logging
import random
import zipfile
import zlib
from collections.abc import Callable

import pdfplumber
import pytest
from pdfminer.pdfpage import PDFPage
from pdfminer.pdftypes import PDFStream
from pdfminer.psparser import LIT
from pdfplumber.page import Page

from app.parsing import pdf as pdf_module
from app.parsing.assemble import TextAssembler
from app.parsing.detect import detect_type
from app.parsing.errors import MAX_PDF_PAGES, ErrorCode, ParseError, WarningCode
from app.parsing.model import ParsedDocument, ParseWarning
from app.parsing.pdf import parse_pdf
from tests.fixtures.build import PAGE_HEIGHT, PAGE_WIDTH

SWEEP_MUTANTS = 300
CHUNK = pdf_module._FLATE_CHUNK


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
    assert doc.warnings == (ParseWarning(WarningCode.BLANK_PAGE, page=2),)
    assert doc.coverage.partial is False


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


# parse_pdf: decoration (A9)


def kinds(doc: ParsedDocument) -> list[str]:
    return [block.kind for block in doc.blocks]


def test_a_repeated_header_and_a_numbered_footer_are_decoration_on_every_page(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["header_footer.pdf"])
    assert kinds(doc) == ["header", "text", "footer"] * 6
    assert [b.text for b in doc.blocks if b.kind == "header"] == ["ACME SERVICES AGREEMENT"] * 6
    assert [b.text for b in doc.blocks if b.kind == "footer"] == [
        f"Page {n} of 6" for n in range(1, 7)
    ]
    assert doc.decorations == tuple((b.start, b.end) for b in doc.blocks if b.kind != "text")
    assert [dict(b.locator)["block"] for b in doc.blocks[:3]] == [1, 2, 3]
    assert doc.warnings == ()


def test_a_page_number_is_decoration_even_in_a_one_page_file(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["page_number_one_page.pdf"])
    assert [(b.kind, b.text) for b in doc.blocks][1:] == [("footer", "- 1 -")]
    assert kinds(doc)[0] == "text"
    assert len(doc.decorations) == 1


def test_a_header_on_two_pages_is_text_but_page_numbers_on_them_are_decoration(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["furniture_two_pages.pdf"])
    assert kinds(doc) == ["text", "text", "footer"] * 2
    assert [b.text for b in doc.blocks if b.text == "CONFIDENTIAL"] == ["CONFIDENTIAL"] * 2


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("header_two_of_three.pdf", "text"),  # needs all three pages
        ("header_three_of_seven.pdf", "text"),  # needs four, the half rounded up
        ("header_four_of_seven.pdf", "header"),
    ],
)
def test_a_repeated_line_needs_three_pages_and_half_the_pages_from_six(
    name: str, kind: str, fixture_bytes: dict[str, bytes]
) -> None:
    doc = parse_pdf(fixture_bytes[name])
    drafts = [b for b in doc.blocks if b.text == "DRAFT"]
    assert drafts
    assert {b.kind for b in drafts} == {kind}
    assert len(doc.decorations) == (len(drafts) if kind == "header" else 0)


def test_a_body_line_in_the_margin_is_its_own_text_block(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["body_in_margin.pdf"])
    # The paragraph in the middle of the list ends just above the bottom margin, and the last
    # line starts with a digit but is no page number.
    assert texts(doc) == [
        "PREAMBLE OF THE AGREEMENT",
        "The parties agree to the terms below and shall\nperform them in good faith at all times.",
        "The Supplier shall deliver the goods to the Customer\n"
        "at the place named in the Order and shall bear the\n"
        "risk of loss until delivery is complete.",
        "5 Fees are payable on demand",
    ]
    assert kinds(doc) == ["text"] * 4
    assert doc.decorations == ()


def test_a_page_number_that_opens_or_closes_a_page_is_decoration_outside_the_margins(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["page_numbers_off_margin.pdf"])
    assert [(b.page, b.kind, b.text) for b in doc.blocks] == [
        (1, "header", "1"),
        (
            1,
            "text",
            "The party shall comply with the first requirement\nof the Agreement without delay.",
        ),
        (
            2,
            "text",
            "The party shall comply with the second requirement\nof the Agreement without delay.",
        ),
        (2, "footer", "2"),
        (
            3,
            "text",
            "The party shall comply with the third requirement\nof the Agreement without delay.",
        ),
        (3, "text", "3"),  # between two paragraphs: neither the first nor the last row
        (
            3,
            "text",
            "The party shall keep the records of the Agreement\nfor the period it sets out.",
        ),
        (4, "header", "4"),  # a lone number in the top margin stays a header
        (5, "footer", "5"),  # a lone number elsewhere is a footer
    ]
    assert len(doc.decorations) == 4


def test_a_page_number_in_the_left_half_of_two_columns_is_read_last(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["two_column_page_number.pdf"])
    assert texts(doc) == [
        "TWO COLUMN AGREEMENT",
        "Left one alpha beta gamma\nLeft two delta epsilon\nLeft three zeta eta\n"
        "Left four theta iota",
        "Right one kappa lambda mu\nRight two nu xi omicron\nRight three pi rho sigma\n"
        "Right four tau upsilon phi",
        "1",
    ]
    assert kinds(doc) == ["text", "text", "text", "footer"]
    assert doc.warnings == ()


PAGE_NUMBERS = ["3", "Page 3", "PAGE 12 OF 40", "3/10", "- 3 -", "\N{EN DASH} 3 \N{EN DASH}"]
NOT_PAGE_NUMBERS = [
    "2024",
    "Page",
    "3 Fees",
    "Section 3",
    "1.1",
    "(a)",
    "Page 3 of",
    "Exhibit 10.1",
]


@pytest.mark.parametrize("line", PAGE_NUMBERS + NOT_PAGE_NUMBERS)
def test_page_number_shapes(line: str) -> None:
    assert bool(pdf_module._PAGE_NUMBER.fullmatch(line)) is (line in PAGE_NUMBERS)


# parse_pdf: scanned pages and partial reads (A10)


@pytest.mark.parametrize(
    "name",
    ["scanned.pdf", "scanned_stamp.pdf", "scanned_most_of_page.pdf", "scan_19_chars.pdf"],
)
def test_a_file_whose_every_page_is_scanned_is_rejected(
    name: str, fixture_bytes: dict[str, bytes]
) -> None:
    # The stamp sits in the margin, so it does not count as text on the page.
    with pytest.raises(ParseError) as exc:
        parse_pdf(fixture_bytes[name])
    assert exc.value.code == ErrorCode.SCANNED_PDF
    assert str(exc.value) == "SCANNED_PDF"


def test_one_scanned_page_among_text_pages_is_a_warning_and_a_partial_read(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_pdf(fixture_bytes["partly_scanned.pdf"])
    assert texts(doc)[:2] == [
        "1. Parties",
        "1.1 This Agreement is made between the parties named below.",
    ]
    assert doc.warnings == (ParseWarning(WarningCode.PARTIALLY_SCANNED_PDF, page=2),)
    assert doc.coverage.partial is True
    # The stamp on page 2 is a block, but page 2 has no readable text.
    assert [b.page for b in doc.blocks] == [1, 1, 2]
    assert (doc.coverage.pages_total, doc.coverage.pages_with_text) == (2, 1)


@pytest.mark.parametrize(
    ("name", "partial"),
    [
        ("scan_20_chars.pdf", True),  # no longer scanned, still too thin to trust
        ("scan_199_chars.pdf", True),
        ("scan_200_chars.pdf", False),  # a searchable scan stays usable
    ],
)
def test_a_page_image_over_a_thin_text_layer_is_partial_not_scanned(
    name: str, partial: bool, fixture_bytes: dict[str, bytes]
) -> None:
    doc = parse_pdf(fixture_bytes[name])
    assert doc.coverage.partial is partial
    assert doc.warnings == ()
    assert (len(doc.blocks), doc.coverage.pages_with_text) == (1, 1)


def test_an_image_that_covers_under_half_the_page_does_not_make_it_scanned(
    fixture_bytes: dict[str, bytes],
) -> None:
    # Most of this picture lies off the page, and only a 0.4 share of the page is covered.
    doc = parse_pdf(fixture_bytes["image_mostly_off_page.pdf"])
    assert doc.source_text == "Short cover note"
    assert doc.coverage.partial is False
    assert doc.warnings == ()


def test_a_file_of_blank_pages_has_no_text(fixture_bytes: dict[str, bytes]) -> None:
    with pytest.raises(ParseError) as exc:
        parse_pdf(fixture_bytes["all_blank.pdf"])
    assert exc.value.code == ErrorCode.NO_TEXT_FOUND


@pytest.mark.parametrize(
    ("name", "partial"),
    [("form_field.pdf", True), ("free_text.pdf", True), ("plain_annotations.pdf", False)],
)
def test_annotation_text_the_layout_cannot_see_makes_the_read_partial(
    name: str, partial: bool, fixture_bytes: dict[str, bytes]
) -> None:
    doc = parse_pdf(fixture_bytes[name])
    assert doc.coverage.partial is partial
    assert doc.warnings == ()


def test_an_owner_password_only_file_parses_like_the_plain_one(
    fixture_bytes: dict[str, bytes],
) -> None:
    plain = parse_pdf(fixture_bytes["simple.pdf"])
    assert parse_pdf(fixture_bytes["owner_only.pdf"]).source_text == plain.source_text


# parse_pdf: limits (A11)


@pytest.fixture
def no_text_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fails the test if anything reads page text or decodes a whole stream."""

    def refuse(*args: object, **kwargs: object) -> None:
        pytest.fail("text was read or a stream was decoded")

    monkeypatch.setattr(Page, "extract_words", refuse)
    monkeypatch.setattr(PDFStream, "decode", refuse)


def test_a_file_of_more_than_100_pages_is_rejected_before_any_text_is_read(
    fixture_bytes: dict[str, bytes], no_text_extraction: None
) -> None:
    with pytest.raises(ParseError) as exc:
        parse_pdf(fixture_bytes["too_many_pages.pdf"])
    assert exc.value.code == ErrorCode.TOO_MANY_PAGES


def test_exactly_100_pages_parse(fixture_bytes: dict[str, bytes]) -> None:
    doc = parse_pdf(fixture_bytes["hundred_pages.pdf"])
    assert doc.page_count == MAX_PDF_PAGES
    assert len(doc.blocks) == MAX_PDF_PAGES


@pytest.mark.parametrize("name", ["bomb_content.pdf", "bomb_form.pdf", "bomb_encrypted.pdf"])
def test_a_stream_that_decodes_past_the_budget_is_rejected_without_being_decoded(
    name: str, fixture_bytes: dict[str, bytes], no_text_extraction: None
) -> None:
    assert len(fixture_bytes[name]) < 16 * 1024
    with pytest.raises(ParseError) as exc:
        parse_pdf(fixture_bytes[name])
    assert exc.value.code == ErrorCode.TOO_MUCH_TEXT


def test_forms_that_name_each_other_end_and_the_text_is_read(
    fixture_bytes: dict[str, bytes],
) -> None:
    assert parse_pdf(fixture_bytes["form_cycle.pdf"]).source_text == "Cycle ends"


def test_the_budget_counts_every_page_and_passes_exactly_at_the_limit(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    data = fixture_bytes["simple.pdf"]
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        total = sum(
            len(stream.get_data())
            for page in PDFPage.create_pages(pdf.doc)
            for stream in page.contents
        )
    monkeypatch.setattr(pdf_module, "MAX_DECODED_CONTENT_BYTES", total)
    assert parse_pdf(data).page_count == 2
    monkeypatch.setattr(pdf_module, "MAX_DECODED_CONTENT_BYTES", total - 1)
    with pytest.raises(ParseError) as exc:
        parse_pdf(data)
    assert exc.value.code == ErrorCode.TOO_MUCH_TEXT


def flate_stream(size: int) -> PDFStream:
    return PDFStream({"Filter": LIT("FlateDecode")}, zlib.compress(b"a" * size))


@pytest.mark.parametrize("size", [0, 1, CHUNK - 1, CHUNK, CHUNK + 1, 3 * CHUNK, 3 * CHUNK + 1])
def test_a_flate_stream_is_measured_exactly_across_chunk_boundaries(size: int) -> None:
    assert pdf_module._decoded_length(flate_stream(size), 10**9) == size


def test_a_flate_stream_is_abandoned_soon_after_it_passes_the_limit() -> None:
    measured = pdf_module._decoded_length(flate_stream(50 * CHUNK), CHUNK)
    assert CHUNK < measured <= 2 * CHUNK


def a85(data: bytes) -> bytes:
    return base64.a85encode(data, adobe=True)


@pytest.mark.parametrize(
    ("encode", "name"), [(a85, "ASCII85Decode"), (binascii.hexlify, "ASCIIHexDecode")]
)
def test_an_ascii_filter_in_front_of_flate_is_undone_before_measuring(
    encode: Callable[[bytes], bytes], name: str
) -> None:
    raw = encode(zlib.compress(b"a" * 100_000))
    stream = PDFStream({"Filter": [LIT(name), LIT("FlateDecode")]}, raw)
    assert pdf_module._decoded_length(stream, 10**9) == 100_000


def test_other_filters_count_their_stored_length_and_damaged_streams_do_not_raise() -> None:
    lzw = PDFStream({"Filter": LIT("LZWDecode")}, b"x" * 20)
    assert pdf_module._decoded_length(lzw, 10**9) == 20
    for name in ("FlateDecode", "ASCII85Decode"):
        damaged = PDFStream({"Filter": LIT(name)}, b"not a valid stream")
        assert pdf_module._decoded_length(damaged, 10**9) == 0


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


@pytest.mark.parametrize(
    ("name", "words"),
    [
        ("simple.pdf", ("SERVICES", "Definitions", "Supplier", "Effective", "Schedule")),
        ("partly_scanned.pdf", ("Parties", "Agreement", "parties")),  # an image and a stamp
        ("form_field.pdf", ("Customer", "Acme", "Holdings")),  # a widget with a value
    ],
)
def test_byte_flipped_files_give_a_parse_or_a_parse_error_and_leak_nothing(
    name: str,
    words: tuple[str, ...],
    fixture_bytes: dict[str, bytes],
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = fixture_bytes[name]
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
