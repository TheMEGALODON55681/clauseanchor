"""Generates every PDF fixture at test time with reportlab, so no binary file is committed."""

from __future__ import annotations

import io
import os
import zlib
from collections.abc import Callable, Collection
from pathlib import Path

import reportlab
from PIL import Image
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.parsing.errors import MAX_DECODED_CONTENT_BYTES, MAX_PDF_PAGES, ErrorCode

PAGE_WIDTH = 612.0  # US letter, in points
PAGE_HEIGHT = 792.0

Fixtures = dict[str, tuple[Path, ErrorCode | None]]


def _pdf(draw: Callable[[Canvas], None], **options: object) -> bytes:
    buffer = io.BytesIO()
    # invariant=1 pins ids and dates. Uncompressed pages keep document text visible in the
    # bytes, which is what makes a leak in an error message or a log record detectable.
    canvas = Canvas(
        buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT), invariant=1, pageCompression=0, **options
    )
    draw(canvas)
    canvas.save()
    return buffer.getvalue()


def _text(c: Canvas, x: float, y: float, s: str, font: str = "Helvetica", size: int = 11) -> None:
    """Draws s with its baseline y points below the top of the page."""
    c.setFont(font, size)
    c.drawString(x, PAGE_HEIGHT - y, s)


def _simple(c: Canvas) -> None:
    _text(c, 72, 90, "SERVICES AGREEMENT", "Helvetica-Bold", 14)
    _text(c, 72, 130, "1. Definitions")
    _text(c, 72, 158, "1.1 In this Agreement the following")
    _text(c, 72, 172, "words have these meanings.")
    _text(c, 90, 200, '(a) "Services" means the work')
    _text(c, 108, 228, "(i) described in Schedule 1.")
    c.showPage()
    _text(c, 72, 90, "2. Term")
    _text(c, 72, 118, "2.1 This Agreement starts on the Effective Date.")


def _two_column(c: Canvas) -> None:
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 90, "TWO COLUMN AGREEMENT")
    left = [
        "Left one alpha beta gamma",
        "Left two delta epsilon",
        "Left three zeta eta",
        "Left four theta iota",
    ]
    right = [
        "Right one kappa lambda mu",
        "Right two nu xi omicron",
        "Right three pi rho sigma",
        "Right four tau upsilon phi",
    ]
    for i, (a, b) in enumerate(zip(left, right, strict=True)):
        _text(c, 72, 140 + 14 * i, a)
        _text(c, 330, 140 + 14 * i, b)


def _long_lines(c: Canvas) -> None:
    first = [
        "The Supplier shall provide the Services to the Customer in accordance",
        "with the terms of this Agreement and all applicable laws, and shall",
        "exercise reasonable skill and care in the performance of its obligations",
        "under this Agreement, including the timely delivery of each deliverable",
        "described in the Schedule.",
    ]
    second = [
        "The Customer shall pay the Charges on the date the parties agree-",
        "ment becomes effective and shall not set off any amount.",
    ]
    for i, line in enumerate(first):
        _text(c, 72, 100 + 14 * i, line)
    for i, line in enumerate(second):
        _text(c, 72, 184 + 14 * i, line)


def _latin_unicode(c: Canvas) -> None:
    # Vera ships with reportlab and holds U+FB01, which the standard Helvetica cannot draw.
    path = os.path.join(os.path.dirname(reportlab.__file__), "fonts", "Vera.ttf")
    pdfmetrics.registerFont(TTFont("Vera", path))
    lines = [
        "\u201cSmart\u201d quotes and caf\u00e9 na\u00efve",
        "Non\u00a0breaking  double  spaces",
        "\ufb01nal terms",
    ]
    for i, line in enumerate(lines):
        _text(c, 72, 100 + 14 * i, line, "Vera", 12)


def _tight_clauses(c: Canvas) -> None:
    # Hanging indents with 6 pt between paragraphs (pitch 18 against 12 inside one).
    rows = [
        (72, "1.1 The Supplier shall perform the Services"),
        (90, "with reasonable skill and care."),
        (72, "1.2 The Customer shall pay the Charges"),
        (90, "within thirty days of invoice."),
        (72, '"Force Majeure" means an event beyond'),
        (90, "the reasonable control of a party."),
        (72, '"Party" means a party to this Agreement.'),
    ]
    y = 100.0
    for i, (x, line) in enumerate(rows):
        if i:
            y += 18 if x == 72 else 12
        _text(c, x, y, line, size=10)


def _blank_page(c: Canvas) -> None:
    _text(c, 72, 100, "1. First page")
    c.showPage()
    c.showPage()
    _text(c, 72, 100, "3. Third page")


def _hanging_page_break(c: Canvas) -> None:
    # Page 2 opens on the indented tail of a definition that began on page 1.
    _text(c, 72, 100, '"Term" means the period that starts on the Effective Date', size=10)
    _text(c, 90, 112, "and runs until this Agreement ends", size=10)
    c.showPage()
    _text(c, 90, 100, "or is terminated under clause 9 or clause 10.", size=10)
    _text(c, 72, 118, '"Fee" means the amount payable', size=10)
    _text(c, 90, 130, "under Schedule 2.", size=10)
    _text(c, 72, 148, '"Day" means a calendar day.', size=10)


def _first_line_indent(c: Canvas) -> None:
    # The first line of each paragraph is indented and the rest sit at the left edge. A return
    # to the edge here is the paragraph's own second line, not a new paragraph.
    paragraphs = [
        [
            "The Supplier shall perform the Services with reasonable skill",
            "and care and in accordance with applicable law and shall notify",
            "the Customer of any matter that may delay delivery.",
        ],
        [
            "The Customer shall pay the Charges within thirty days of the",
            "date of each invoice and shall not set off any amount against",
            "the Charges without the written consent of the Supplier.",
        ],
        [
            "Either party may end this Agreement by written notice if the",
            "other commits a material breach and fails to remedy it within",
            "the period stated in that notice.",
        ],
    ]
    # The page opens on the tail of a paragraph from the page before, which sits at the edge.
    _text(c, 72, 100, "the notice period stated in clause 9 of this Agreement.", size=10)
    y = 118.0
    for lines in paragraphs:
        for i, line in enumerate(lines):
            _text(c, 90 if i == 0 else 72, y, line, size=10)
            y += 12
        y += 6


def _contents(c: Canvas) -> None:
    # Page numbers sit far right, outside the middle 60 percent, so this is no second column.
    _text(c, 72, 90, "CONTENTS", "Helvetica-Bold", 14)
    for i, (title, number) in enumerate(
        [("1. Definitions", "3"), ("2. Term", "5"), ("3. Fees", "7"), ("4. Termination", "9")]
    ):
        _text(c, 72, 140 + 14 * i, title)
        _text(c, 520, 140 + 14 * i, number)


def _three_column_table(c: Canvas) -> None:
    _text(c, 72, 90, "PRICE SCHEDULE", "Helvetica-Bold", 14)
    rows = [
        ("Item", "Quantity", "Price"),
        ("Steel bolt", "10", "0.50"),
        ("Brass nut", "25", "0.20"),
        ("Copper wire", "5", "3.10"),
        ("Rubber seal", "12", "0.75"),
    ]
    for i, row in enumerate(rows):
        for x, cell in zip((72, 250, 430), row, strict=True):
            _text(c, x, 140 + 14 * i, cell)


def _column_uncertain(c: Canvas) -> None:
    for y, a, b in [
        (100, "Left alpha one", "Right alpha one"),
        (114, "Left alpha two", "Right alpha two"),
        (170, "Left beta one", "Right beta one"),
        (184, "Left beta two", "Right beta two"),
    ]:
        _text(c, 72, y, a)
        _text(c, 330, y, b)
    _text(c, 72, 142, "This wide line deliberately crosses the gutter between the two columns")


def _furnished(
    count: int, header: str | None, header_pages: Collection[int], footer: str | None
) -> Callable[[Canvas], None]:
    """count pages of body text. The header sits on header_pages in the top margin (0.08 of the
    792 pt page is 63 pt), and the footer, with {n} and {total}, on every page in the bottom."""

    def draw(c: Canvas) -> None:
        for n in range(1, count + 1):
            if n > 1:
                c.showPage()
            if header and n in header_pages:
                _text(c, 72, 40, header, size=9)
            _text(c, 72, 100, f"{n}. Clause {n} of the Agreement")
            _text(c, 72, 128, f"The party shall comply with requirement {n}.")
            if footer:
                _text(c, 250, 760, footer.format(n=n, total=count), size=9)

    return draw


def _body_in_margin(c: Canvas) -> None:
    # The first line sits in the top margin and the paragraph under it keeps the same pitch.
    _text(c, 72, 58, "PREAMBLE OF THE AGREEMENT", size=10)
    _text(c, 72, 70, "The parties agree to the terms below and shall", size=10)
    _text(c, 72, 82, "perform them in good faith at all times.", size=10)
    # The last body paragraph ends just above the bottom margin, which starts at 729 pt.
    for i, line in enumerate(
        [
            "The Supplier shall deliver the goods to the Customer",
            "at the place named in the Order and shall bear the",
            "risk of loss until delivery is complete.",
        ]
    ):
        _text(c, 72, 676 + 12 * i, line, size=10)
    _text(c, 72, 760, "5 Fees are payable on demand", size=9)  # starts with a digit, no page number


def _page_numbers_off_margin(c: Canvas) -> None:
    # The top margin is 63 pt and the bottom margin starts at 729 pt. No number here sits in one
    # of them, except on page 4.
    _text(c, 300, 100, "1")  # page 1: the first row of the page
    _text(c, 72, 130, "The party shall comply with the first requirement")
    _text(c, 72, 144, "of the Agreement without delay.")
    c.showPage()
    _text(c, 72, 100, "The party shall comply with the second requirement")  # page 2: the last row
    _text(c, 72, 114, "of the Agreement without delay.")
    _text(c, 300, 400, "2")
    c.showPage()
    _text(c, 72, 100, "The party shall comply with the third requirement")  # page 3: neither
    _text(c, 72, 114, "of the Agreement without delay.")
    _text(c, 300, 142, "3")
    _text(c, 72, 170, "The party shall keep the records of the Agreement")
    _text(c, 72, 184, "for the period it sets out.")
    c.showPage()
    _text(c, 300, 40, "4", size=9)  # page 4: a lone number in the top margin
    c.showPage()
    _text(c, 300, 400, "5")  # page 5: a lone number half way down


def _two_column_page_number(c: Canvas) -> None:
    # The number is centred, so it falls in the left column's stream and would be read before
    # the right column.
    _two_column(c)
    c.setFont("Helvetica", 11)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 300, "1")


def _scan(
    c: Canvas, x: float = 0, width: float = PAGE_WIDTH, y: float = 0, height: float = PAGE_HEIGHT
) -> None:
    """Draws a picture and no text, as a scanner would. By default it fills the page."""
    image = Image.linear_gradient("L").resize((64, 80))
    c.drawImage(ImageReader(image), x, y, width, height)


def _scanned(c: Canvas) -> None:
    _scan(c)
    c.showPage()
    _scan(c)


def _scanned_stamp(c: Canvas) -> None:
    _scan(c)
    # A Bates stamp with a legend, in the bottom margin: over 20 characters, none of them counted.
    _text(c, 300, 770, "ACME HOLDINGS CONFIDENTIAL 000123", size=9)


def _partly_scanned(c: Canvas) -> None:
    _text(c, 72, 100, "1. Parties")
    _text(c, 72, 128, "1.1 This Agreement is made between the parties named below.")
    c.showPage()
    _scan(c)
    _text(c, 400, 770, "ACME 000002", size=9)  # a stamp keeps the scanned page from being blank


def _scan_with_chars(count: int) -> Callable[[Canvas], None]:
    """A page picture over an invisible text layer of exactly count characters, in 5-letter words
    that all sit outside the margins."""
    text = ("abcde" * count)[:count]
    words = [text[i : i + 5] for i in range(0, count, 5)]

    def draw(c: Canvas) -> None:
        _scan(c)
        layer = c.beginText(72, PAGE_HEIGHT - 100)
        layer.setFont("Helvetica", 11)
        layer.setTextRenderMode(3)
        for i in range(0, len(words), 8):
            layer.textLine(" ".join(words[i : i + 8]))
        c.drawText(layer)

    return draw


def _scanned_most_of_page(c: Canvas) -> None:
    _scan(c, width=0.6 * PAGE_WIDTH)  # image-dominant at a 0.6 share


def _image_mostly_off_page(c: Canvas) -> None:
    # A 1200 by 2376 pt picture of which a 245 by 792 pt strip (a 0.4 share) lands on the page.
    _scan(c, x=367, width=1200, y=-PAGE_HEIGHT, height=3 * PAGE_HEIGHT)
    _text(c, 72, 100, "Short cover note")


def _all_blank(c: Canvas) -> None:
    c.showPage()
    c.showPage()


def _form_field(c: Canvas) -> None:
    _text(c, 72, 100, "Name of the Customer:")
    c.acroForm.textfield(
        name="customer", value="Acme Holdings", x=250, y=PAGE_HEIGHT - 110, width=200, height=20
    )


def _free_text(c: Canvas) -> None:
    _text(c, 72, 100, "1. Notices")
    c.freeTextAnnotation(
        "Reviewer note: confirm the notice address",
        DA="/Helv 12 Tf 0 g",
        Rect=(72, 600, 400, 640),
    )


def _plain_annotations(c: Canvas) -> None:
    # A blank field, a link and a sticky note: none is a Widget or FreeText with text.
    _text(c, 72, 100, "Name of the Customer:")
    c.acroForm.textfield(
        name="customer", value=" ", x=250, y=PAGE_HEIGHT - 110, width=200, height=20
    )
    c.linkURL("https://example.org", (72, 90, 200, 110))
    c.textAnnotation("Internal note", Rect=(300, 600, 320, 620))


def _many_pages(count: int) -> Callable[[Canvas], None]:
    def draw(c: Canvas) -> None:
        for n in range(1, count + 1):
            if n > 1:
                c.showPage()
            _text(c, 72, 100, f"Page body {n}")

    return draw


def _raw_pdf(objects: dict[int, bytes]) -> bytes:
    """Writes numbered objects with a classic xref table, for files reportlab will not make."""
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for number, body in objects.items():
        offsets[number] = len(out)
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    size = max(objects) + 1
    start = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for number in range(1, size):
        out += b"%010d 00000 n \n" % offsets[number]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, start)
    return bytes(out)


def _stream(data: bytes, entries: bytes = b"") -> bytes:
    return b"<< /Length %d %s >>\nstream\n%s\nendstream" % (len(data), entries, data)


_FORM = b"/Type /XObject /Subtype /Form /BBox [0 0 612 792]"
_CATALOG = {
    1: b"<< /Type /Catalog /Pages 2 0 R >>",
    2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
}


def _bomb() -> bytes:
    """About 9 KB that decode to one byte more than the content budget."""
    return zlib.compress(b" " * (MAX_DECODED_CONTENT_BYTES + 1), 9)


def _bomb_content_bytes() -> bytes:
    return _raw_pdf(
        {
            **_CATALOG,
            3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
            4: _stream(_bomb(), b"/Filter /FlateDecode"),
        }
    )


def _bomb_form_bytes() -> bytes:
    # The page draws form A, which draws form B, and B holds the bomb and names A again.
    return _raw_pdf(
        {
            **_CATALOG,
            3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
            b" /Resources << /XObject << /A 5 0 R >> >> >>",
            4: _stream(b"/A Do"),
            5: _stream(b"/B Do", _FORM + b" /Resources << /XObject << /B 6 0 R >> >>"),
            6: _stream(
                _bomb(), _FORM + b" /Filter /FlateDecode /Resources << /XObject << /A 5 0 R >> >>"
            ),
        }
    )


def _bomb_encrypted_bytes() -> bytes:
    # reportlab compresses the page and then encrypts the stream, so the budget has to decipher
    # before it inflates. The padding is whitespace, which a content stream ignores.
    buffer = io.BytesIO()
    canvas = Canvas(
        buffer,
        pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
        invariant=1,
        pageCompression=1,
        encrypt=StandardEncryption("", ownerPassword="owner"),
    )
    canvas._code.append(" " * (MAX_DECODED_CONTENT_BYTES + 1))
    canvas.save()
    return buffer.getvalue()


def _form_cycle_bytes() -> bytes:
    # Forms A and B name each other in their resources and neither draws the other.
    return _raw_pdf(
        {
            **_CATALOG,
            3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
            b" /Resources << /Font << /F0 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >>"
            b" /XObject << /A 5 0 R >> >> >>",
            4: _stream(b"BT /F0 11 Tf 72 700 Td (Cycle ends) Tj ET /A Do"),
            5: _stream(b"q Q", _FORM + b" /Resources << /XObject << /B 6 0 R >> >>"),
            6: _stream(b"q Q", _FORM + b" /Resources << /XObject << /A 5 0 R >> >>"),
        }
    )


def _simple_bytes() -> bytes:
    return _pdf(_simple)


def _malformed_bytes() -> bytes:
    data = _simple_bytes()
    return data[: len(data) * 6 // 10]


_BUILDERS: dict[str, tuple[Callable[[], bytes], ErrorCode | None]] = {
    "simple.pdf": (_simple_bytes, None),
    "two_column.pdf": (lambda: _pdf(_two_column), None),
    "long_lines.pdf": (lambda: _pdf(_long_lines), None),
    "latin_unicode.pdf": (lambda: _pdf(_latin_unicode), None),
    "tight_clauses.pdf": (lambda: _pdf(_tight_clauses), None),
    "blank_page.pdf": (lambda: _pdf(_blank_page), None),
    "hanging_page_break.pdf": (lambda: _pdf(_hanging_page_break), None),
    "first_line_indent.pdf": (lambda: _pdf(_first_line_indent), None),
    "contents.pdf": (lambda: _pdf(_contents), None),
    "three_column_table.pdf": (lambda: _pdf(_three_column_table), None),
    "column_uncertain.pdf": (lambda: _pdf(_column_uncertain), None),
    "malformed.pdf": (_malformed_bytes, ErrorCode.MALFORMED_FILE),
    "encrypted.pdf": (lambda: _pdf(_simple, encrypt="secret"), ErrorCode.ENCRYPTED_PDF),
    # Decoration (A9)
    "header_footer.pdf": (
        lambda: _pdf(_furnished(6, "ACME SERVICES AGREEMENT", range(1, 7), "Page {n} of {total}")),
        None,
    ),
    "page_number_one_page.pdf": (lambda: _pdf(_furnished(1, None, (), "- {n} -")), None),
    "furniture_two_pages.pdf": (
        lambda: _pdf(_furnished(2, "CONFIDENTIAL", (1, 2), "Page {n} of {total}")),
        None,
    ),
    "header_two_of_three.pdf": (lambda: _pdf(_furnished(3, "DRAFT", (1, 2), None)), None),
    "header_three_of_seven.pdf": (lambda: _pdf(_furnished(7, "DRAFT", (1, 2, 3), None)), None),
    "header_four_of_seven.pdf": (lambda: _pdf(_furnished(7, "DRAFT", (1, 2, 3, 4), None)), None),
    "body_in_margin.pdf": (lambda: _pdf(_body_in_margin), None),
    "page_numbers_off_margin.pdf": (lambda: _pdf(_page_numbers_off_margin), None),
    "two_column_page_number.pdf": (lambda: _pdf(_two_column_page_number), None),
    # Scanned pages and partial reads (A10)
    "scanned.pdf": (lambda: _pdf(_scanned), ErrorCode.SCANNED_PDF),
    "scanned_stamp.pdf": (lambda: _pdf(_scanned_stamp), ErrorCode.SCANNED_PDF),
    "partly_scanned.pdf": (lambda: _pdf(_partly_scanned), None),
    "scan_19_chars.pdf": (lambda: _pdf(_scan_with_chars(19)), ErrorCode.SCANNED_PDF),
    "scan_20_chars.pdf": (lambda: _pdf(_scan_with_chars(20)), None),
    "scan_199_chars.pdf": (lambda: _pdf(_scan_with_chars(199)), None),
    "scan_200_chars.pdf": (lambda: _pdf(_scan_with_chars(200)), None),
    "scanned_most_of_page.pdf": (lambda: _pdf(_scanned_most_of_page), ErrorCode.SCANNED_PDF),
    "image_mostly_off_page.pdf": (lambda: _pdf(_image_mostly_off_page), None),
    "all_blank.pdf": (lambda: _pdf(_all_blank), ErrorCode.NO_TEXT_FOUND),
    "form_field.pdf": (lambda: _pdf(_form_field), None),
    "free_text.pdf": (lambda: _pdf(_free_text), None),
    "plain_annotations.pdf": (lambda: _pdf(_plain_annotations), None),
    "owner_only.pdf": (
        lambda: _pdf(
            _simple,
            encrypt=StandardEncryption("", ownerPassword="owner", canCopy=0, canModify=0),
        ),
        None,
    ),
    # Limits (A11)
    "hundred_pages.pdf": (lambda: _pdf(_many_pages(MAX_PDF_PAGES)), None),
    "too_many_pages.pdf": (lambda: _pdf(_many_pages(MAX_PDF_PAGES + 1)), ErrorCode.TOO_MANY_PAGES),
    "bomb_content.pdf": (_bomb_content_bytes, ErrorCode.TOO_MUCH_TEXT),
    "bomb_form.pdf": (_bomb_form_bytes, ErrorCode.TOO_MUCH_TEXT),
    "bomb_encrypted.pdf": (_bomb_encrypted_bytes, ErrorCode.TOO_MUCH_TEXT),
    "form_cycle.pdf": (_form_cycle_bytes, None),
}

NAMES = tuple(_BUILDERS)


def build_all(directory: Path) -> Fixtures:
    """Writes every fixture into directory and maps its name to (path, expected error code)."""
    built: Fixtures = {}
    for name, (make, expected) in _BUILDERS.items():
        path = directory / name
        path.write_bytes(make())
        built[name] = (path, expected)
    return built
