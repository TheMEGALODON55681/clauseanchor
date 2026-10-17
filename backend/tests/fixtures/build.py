"""Generates every PDF fixture at test time with reportlab, and every DOCX fixture from raw
XML, so no binary file is committed."""

from __future__ import annotations

import io
import os
import zipfile
import zlib
from collections.abc import Callable, Collection, Iterable
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from PIL import Image
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.parsing.errors import (
    MAX_ARCHIVE_BYTES,
    MAX_DECODED_CONTENT_BYTES,
    MAX_PDF_PAGES,
    ErrorCode,
)

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


def _single_content_pdf(content: bytes) -> bytes:
    return _raw_pdf(
        {
            **_CATALOG,
            3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
            4: content,
        }
    )


def _bomb_content_bytes() -> bytes:
    return _single_content_pdf(_stream(_bomb(), b"/Filter /FlateDecode"))


def _bomb_double_flate_bytes() -> bytes:
    # The same bomb inside a second Flate stage. The first stage is about 9 KB, so a count
    # that stops after one filter sees a stream well inside the budget.
    return _single_content_pdf(
        _stream(zlib.compress(_bomb(), 9), b"/Filter [/FlateDecode /FlateDecode]")
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


def unmapped_pdf(*pages: tuple[int, int]) -> bytes:
    """One page per (letters, unmapped glyphs) pair. The letters are set in Helvetica. The
    glyphs are codes of a Type0 font that has no ToUnicode map, so pdfminer reads each as
    (cid:65): one glyph, eight characters."""
    kids = " ".join(f"{6 + 2 * n} 0 R" for n in range(len(pages)))
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids.encode(), len(pages)),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: b"<< /Type /Font /Subtype /Type0 /BaseFont /Helvetica /Encoding /Identity-H"
        b" /DescendantFonts [5 0 R] >>",
        5: b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Helvetica /CIDSystemInfo"
        b" << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> >>",
    }
    for n, (letters, glyphs) in enumerate(pages):
        content = b""
        if letters:
            content += b"BT /F0 11 Tf 72 700 Td (%s) Tj ET\n" % (b"a" * letters)
        if glyphs:
            content += b"BT /F1 11 Tf 72 650 Td <%s> Tj ET" % (b"0041" * glyphs)
        objects[6 + 2 * n] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R"
            b" /Resources << /Font << /F0 3 0 R /F1 4 0 R >> >> >>" % (7 + 2 * n)
        )
        objects[7 + 2 * n] = _stream(content)
    return _raw_pdf(objects)


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


# DOCX fixtures (A12 to A16). Hand-written packages, so every wrapper, text box and tracked
# change is exactly the markup under test. Text uses character references where a character
# would be invisible or ambiguous in this file.

_WML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_NAMESPACES = (
    f'xmlns:w="{_WML}" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
    'xmlns:v="urn:schemas-microsoft-com:vml" '
    'xmlns:o="urn:schemas-microsoft-com:office:office"'
)
_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
_OFFICE_DOCUMENT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_WML_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml"

# A related part: (member name, content type, relationship type, xml)
_Extra = tuple[str, str, str, str]


def _run(text: str) -> str:
    return f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _p(text: str) -> str:
    return f"<w:p>{_run(text)}</w:p>"


def _tc(*content: str) -> str:
    return f"<w:tc><w:tcPr/>{''.join(content)}</w:tc>"


def _tr(*cells: str) -> str:
    return f"<w:tr>{''.join(cells)}</w:tr>"


def _tbl(*rows: str) -> str:
    return f"<w:tbl><w:tblPr/><w:tblGrid/>{''.join(rows)}</w:tbl>"


def related_part(kind: str, content: str, n: int = 1) -> _Extra:
    """A part the document relates to: header, footer, footnotes, endnotes, styles or
    numbering. Headers and footers are numbered, so one package can hold several."""
    root = {"header": "hdr", "footer": "ftr"}.get(kind, kind)
    name = f"{kind}{n}" if kind in ("header", "footer") else kind
    xml = f"{_XML}<w:{root} {_NAMESPACES}>{content}</w:{root}>"
    return (f"word/{name}.xml", f"{_WML_TYPE}.{kind}+xml", f"{_OFFICE_DOCUMENT}/{kind}", xml)


def level_xml(index: int, fmt: str, text: str, *, start: int = 1, extra: str = "") -> str:
    return (
        f'<w:lvl w:ilvl="{index}"><w:start w:val="{start}"/><w:numFmt w:val="{fmt}"/>'
        f'{extra}<w:lvlText w:val="{text}"/></w:lvl>'
    )


def abstract_num(abstract_id: int, *levels: str) -> str:
    return f'<w:abstractNum w:abstractNumId="{abstract_id}">{"".join(levels)}</w:abstractNum>'


def num_xml(num_id: int, abstract_id: int, *overrides: str) -> str:
    return (
        f'<w:num w:numId="{num_id}"><w:abstractNumId w:val="{abstract_id}"/>'
        f"{''.join(overrides)}</w:num>"
    )


def override_xml(index: int, *, start: int | None = None, level: str = "") -> str:
    inner = f'<w:startOverride w:val="{start}"/>' if start is not None else ""
    return f'<w:lvlOverride w:ilvl="{index}">{inner}{level}</w:lvlOverride>'


def style_xml(
    style_id: str,
    *,
    based_on: str | None = None,
    num_id: int | None = None,
    level: int | None = None,
    default: bool = False,
) -> str:
    base = f'<w:basedOn w:val="{based_on}"/>' if based_on else ""
    numbering = ""
    if num_id is not None or level is not None:
        ilvl = f'<w:ilvl w:val="{level}"/>' if level is not None else ""
        numid = f'<w:numId w:val="{num_id}"/>' if num_id is not None else ""
        numbering = f"<w:pPr><w:numPr>{ilvl}{numid}</w:numPr></w:pPr>"
    marker = ' w:default="1"' if default else ""
    return (
        f'<w:style w:type="paragraph"{marker} w:styleId="{style_id}">'
        f'<w:name w:val="{style_id}"/>{base}{numbering}</w:style>'
    )


def listed(
    text: str, *, num_id: int | None = None, level: int | None = None, style: str | None = None
) -> str:
    """A paragraph with direct numbering properties, a style, or both."""
    ilvl = f'<w:ilvl w:val="{level}"/>' if level is not None else ""
    numid = f'<w:numId w:val="{num_id}"/>' if num_id is not None else ""
    numbering = f"<w:numPr>{ilvl}{numid}</w:numPr>" if ilvl or numid else ""
    pstyle = f'<w:pStyle w:val="{style}"/>' if style else ""
    return f"<w:p><w:pPr>{pstyle}{numbering}</w:pPr>{_run(text)}</w:p>"


def reference(kind: str, variant: str, n: int) -> str:
    """A header or footer reference to relationship rId<n>. build_docx numbers the extras from 1
    in the order given."""
    return f'<w:{kind}Reference w:type="{variant}" r:id="rId{n}"/>'


def end_section(*references: str) -> str:
    """An empty paragraph that carries the properties of the section it ends."""
    return f"<w:p><w:pPr><w:sectPr>{''.join(references)}</w:sectPr></w:pPr></w:p>"


def _package(files: dict[str | zipfile.ZipInfo, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


_PAGE_SIZE = '<w:pgSz w:w="12240" w:h="15840"/>'


def _docx_files(
    body: str, extras: Iterable[_Extra] = (), prolog: str = "", section: str = _PAGE_SIZE
) -> dict[str, bytes | str]:
    extras = list(extras)
    overrides = "".join(
        f'<Override PartName="/{name}" ContentType="{content_type}"/>'
        for name, content_type, _, _ in extras
    )
    relationships = "".join(
        f'<Relationship Id="rId{n}" Type="{kind}" Target="{name.removeprefix("word/")}"/>'
        for n, (name, _, kind, _) in enumerate(extras, start=1)
    )
    packages = "http://schemas.openxmlformats.org/package/2006"
    files: dict[str, bytes | str] = {
        "[Content_Types].xml": (
            f'{_XML}<Types xmlns="{packages}/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
            'relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/word/document.xml" ContentType="{_WML_TYPE}.document.main+xml"/>'
            f"{overrides}</Types>"
        ),
        "_rels/.rels": (
            f'{_XML}<Relationships xmlns="{packages}/relationships">'
            f'<Relationship Id="rId1" Type="{_OFFICE_DOCUMENT}/officeDocument" '
            'Target="word/document.xml"/></Relationships>'
        ),
        "word/document.xml": (
            f"{_XML}{prolog}<w:document {_NAMESPACES}><w:body>{body}"
            f"<w:sectPr>{section}</w:sectPr></w:body></w:document>"
        ),
    }
    if extras:
        files["word/_rels/document.xml.rels"] = (
            f'{_XML}<Relationships xmlns="{packages}/relationships">{relationships}</Relationships>'
        )
        files.update({name: xml for name, _, _, xml in extras})
    return files


def build_docx(
    body: str, extras: Iterable[_Extra] = (), prolog: str = "", section: str = _PAGE_SIZE
) -> bytes:
    """A package whose body is the given WordprocessingML, for fixtures and inline tests. The
    body's closing sectPr holds `section`."""
    return _package(_docx_files(body, extras, prolog, section))


def build_zip(member_name: str) -> bytes:
    """A valid package plus one member with exactly this name. The name is set after the entry
    is made, because ZipInfo rewrites a backslash to a slash on Windows when it is built."""
    entry = zipfile.ZipInfo("placeholder.txt")
    entry.filename = member_name
    return _package({**_docx_files(_p("Body text.")), entry: b"x"})


def _archive_too_large() -> bytes:
    """One sparse member of 101 MiB, which deflates to about 100 KB."""
    buffer = io.BytesIO()
    megabyte = bytes(1024 * 1024)
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for name, content in _docx_files(_p("Body text.")).items():
            archive.writestr(name, content)
        with archive.open("word/media/blank.bin", "w") as member:
            for _ in range(MAX_ARCHIVE_BYTES // len(megabyte) + 1):
                member.write(megabyte)
    return buffer.getvalue()


def _simple_docx() -> bytes:
    return build_docx(
        _p("SERVICES AGREEMENT")
        + _p("1. Definitions")
        + _p("1.1 In this Agreement the following words have these meanings.")
        + _p('(a) "Services" means the work described in Schedule 1.')
        + _p("2. Term")
        + _p("2.1 This Agreement starts on the Effective Date.")
    )


def _corrupt_zip() -> bytes:
    data = _simple_docx()
    return data[: len(data) * 6 // 10]


_CHANGE = 'w:id="1" w:author="Drafter" w:date="2026-01-01T00:00:00Z"'


def _tracked(markup: str) -> Callable[[], bytes]:
    return lambda: build_docx(_p("Before.") + f"<w:p>{markup}</w:p>" + _p("After."))


def _doc(*body: str) -> Callable[[], bytes]:
    return lambda: build_docx("".join(body))


_SDT = '<w:sdt><w:sdtPr><w:alias w:val="Field"/></w:sdtPr><w:sdtContent>{}</w:sdtContent></w:sdt>'
_OMATH = (
    '<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
    "<m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></m:oMathPara>"
)


def _anchor(*inner: str) -> str:
    return f"<w:p>{_run('Anchor text.')}<w:r>{''.join(inner)}</w:r></w:p>"


def _vml_box(*paragraphs: str) -> str:
    content = f"<w:txbxContent>{''.join(paragraphs)}</w:txbxContent>"
    return f"<w:pict><v:shape><v:textbox>{content}</v:textbox></v:shape></w:pict>"


def _alternate_content() -> str:
    # Word writes the DrawingML box and a VML copy of it. Only the first one is read.
    paragraphs = _p("Boxed first.") + _p("Boxed second.")
    drawing = (
        '<mc:Choice Requires="wps"><w:drawing><wp:anchor><a:graphic><a:graphicData><wps:wsp>'
        f"<wps:txbx><w:txbxContent>{paragraphs}</w:txbxContent></wps:txbx>"
        "</wps:wsp></a:graphicData></a:graphic></wp:anchor></w:drawing></mc:Choice>"
    )
    fallback = f"<mc:Fallback>{_vml_box(paragraphs)}</mc:Fallback>"
    anchor = _anchor(f"<mc:AlternateContent>{drawing}{fallback}</mc:AlternateContent>")
    return anchor + _p("After the anchor.")


def _nested_boxes() -> str:
    inner = _vml_box(_p("Inner box."))
    outer = _vml_box(_p("Outer box."), f"<w:p><w:r>{inner}</w:r></w:p>", _p("Outer tail."))
    return _anchor(outer)


_RUN_CONTENT = (
    f"<w:p>{_run('Term')}<w:r><w:tab/></w:r>{_run('30')}<w:r><w:noBreakHyphen/></w:r>"
    f"{_run('day')}</w:p>"
    "<w:p><w:r><w:t>first</w:t><w:br/><w:t>second</w:t><w:cr/><w:t>third</w:t></w:r></w:p>"
    '<w:p><w:r><w:t>before</w:t><w:br w:type="page"/><w:t>after</w:t></w:r></w:p>'
    '<w:p><w:r><w:t xml:space="preserve">two  spaces and&#160;nbsp</w:t></w:r></w:p>'
    f"<w:p>{_run('a')}{_run(' ')}{_run('b')}</w:p>"
    '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> PAGE </w:instrText>'
    '</w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    f'{_run("result")}<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
)
_EMPTY_PARAGRAPHS = (
    "<w:p/>" + _p("   ") + _p("First.") + "<w:p><w:r><w:t>&#160;</w:t></w:r></w:p>" + _p("Second.")
)


def _entity_prolog() -> str:
    """Nested entities that would expand to 400,000 characters. The parser refuses any DOCTYPE,
    so none of them is ever expanded."""
    declared = ['<!ENTITY a "' + "a" * 40 + '">']
    for inner, outer in zip("abcd", "bcde", strict=True):
        declared.append(f'<!ENTITY {outer} "' + f"&{inner};" * 10 + '">')
    return "<!DOCTYPE w:document [" + "".join(declared) + "]>"


# Numbering (A17) and page parts (A18)
_MULTILEVEL = abstract_num(
    0,
    level_xml(0, "decimal", "%1."),
    level_xml(1, "decimal", "%1.%2"),
    level_xml(2, "lowerLetter", "(%3)"),
    level_xml(3, "lowerRoman", "(%4)"),
)


def _list_number_style() -> bytes:
    # The paragraphs carry no numPr of their own. The style does.
    styles = related_part(
        "styles", style_xml("Normal", default=True) + style_xml("ListNumber", num_id=1)
    )
    numbering = related_part(
        "numbering", abstract_num(0, level_xml(0, "decimal", "%1.")) + num_xml(1, 0)
    )
    body = (
        listed("First item.", style="ListNumber")
        + _p("Between.")
        + listed("Second item.", style="ListNumber")
        + listed("Third item.", style="ListNumber")
    )
    return build_docx(body, [styles, numbering])


def _numbering_levels() -> bytes:
    numbering = related_part("numbering", _MULTILEVEL + num_xml(1, 0))
    items = (
        (0, "Definitions."),
        (1, "Clause one."),
        (1, "Clause two."),
        (2, "First limb."),
        (2, "Second limb."),
        (3, "First part."),
        (1, "Clause three."),
        (2, "Restarted limb."),
        (0, "Term."),
        (1, "Clause one again."),
    )
    return build_docx("".join(listed(t, num_id=1, level=n) for n, t in items), [numbering])


def _after_h(level: int, count: int) -> bytes:
    """Letters (a) to (h) on level 2, then `count` more paragraphs on `level`. Level 3 is a
    numeral list, so they read (i), (ii) and on. Level 2 is the same list as the letters, so
    they read (i) as the ninth letter, then (j)."""
    numbering = related_part("numbering", _MULTILEVEL + num_xml(1, 0))
    items = [(0, "Services."), (1, "Clause one."), *[(2, "Item.")] * 8, *[(level, "Last.")] * count]
    return build_docx("".join(listed(t, num_id=1, level=n) for n, t in items), [numbering])


def _empty_numbered() -> bytes:
    # Word shows a number for an empty numbered paragraph and counts it. The reader leaves the
    # empty block out, so the label after each one is a number too high: 1, 2, 4, 4.1, 4.3.
    numbering = related_part("numbering", _MULTILEVEL + num_xml(1, 0))
    items = (
        (0, "Services."),
        (0, "Fees."),
        (0, ""),
        (0, "Term."),
        (1, "First term clause."),
        (1, ""),
        (1, "Third term clause."),
        (2, "First limb."),
        (2, ""),
        (2, "Third limb."),
        (0, "Notices."),
    )
    return build_docx("".join(listed(t, num_id=1, level=n) for n, t in items), [numbering])


def _header_footer() -> bytes:
    # Section 1 names a default and a first-page header and a default footer. Section 2 names a
    # second header part with the same text as the first, the footer part again, and an
    # even-page footer.
    extras = [
        related_part("header", _p("ACME SERVICES AGREEMENT"), 1),
        related_part("header", _p("DRAFT"), 2),
        related_part("footer", _tbl(_tr(_tc(_p("CONFIDENTIAL")), _tc(_p("Page 1")))), 1),
        related_part("header", _p("ACME SERVICES AGREEMENT"), 3),
        related_part("footer", _p("Even page footer."), 2),
    ]
    body = _p("Cover.") + end_section(
        reference("header", "default", 1),
        reference("header", "first", 2),
        reference("footer", "default", 3),
    )
    final = (
        reference("header", "default", 4)
        + reference("footer", "default", 3)
        + reference("footer", "even", 5)
        + _PAGE_SIZE
    )
    return build_docx(body + _p("Body of the agreement."), extras, section=final)


def _notes() -> bytes:
    # Word's own notes hold no text. These hold some, so a reader that skips them by type, and
    # not because they happen to be empty, is the one under test.
    separators = (
        '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r>'
        f"{_run('Separator text.')}</w:p></w:footnote>"
        '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/>'
        f"</w:r>{_run('Continuation text.')}</w:p></w:footnote>"
        '<w:footnote w:type="continuationNotice" w:id="-2">'
        f"{_p('Notice text.')}</w:footnote>"
    )
    footnotes = related_part(
        "footnotes",
        separators
        + f'<w:footnote w:id="1">{_p("First note.")}</w:footnote>'
        + f'<w:footnote w:id="2">{_p("Second note.")}{_p("Its second paragraph.")}</w:footnote>',
    )
    endnotes = related_part(
        "endnotes",
        separators.replace("footnote", "endnote")
        + f'<w:endnote w:id="1">{_p("An endnote.")}</w:endnote>',
    )
    reference_run = '<w:r><w:footnoteReference w:id="1"/></w:r>'
    body = f"<w:p>{_run('Claim.')}{reference_run}</w:p>" + _p("Closing.")
    return build_docx(body, [footnotes, endnotes])


def _word_notes() -> bytes:
    # Footnotes and endnotes as Word writes them: a separator with id -1 and a continuation
    # separator with id 0, neither with text, then the notes from 1. Each note opens with its
    # reference mark and a space. A signed id is legal only on the two typed ones, so they have
    # to be skipped before any id is read.
    def separators(kind: str) -> str:
        spacing = '<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
        return "".join(
            f'<w:{kind} w:type="{type_}" w:id="{note_id}"><w:p>{spacing}<w:r><w:{type_}/></w:r>'
            f"</w:p></w:{kind}>"
            for type_, note_id in (("separator", -1), ("continuationSeparator", 0))
        )

    def note(kind: str, number: int, text: str) -> str:
        title = kind.capitalize()
        return (
            f'<w:{kind} w:id="{number}"><w:p><w:pPr><w:pStyle w:val="{title}Text"/></w:pPr>'
            f'<w:r><w:rPr><w:rStyle w:val="{title}Reference"/></w:rPr><w:{kind}Ref/></w:r>'
            f'<w:r><w:t xml:space="preserve"> {text}</w:t></w:r></w:p></w:{kind}>'
        )

    parts = [
        related_part(
            f"{kind}s",
            separators(kind) + note(kind, 1, f"First {kind}.") + note(kind, 2, f"Second {kind}."),
        )
        for kind in ("footnote", "endnote")
    ]
    return build_docx(_p("Claim.") + _p("Closing."), parts)


def _contents_tab() -> bytes:
    # A contents list typed as number, tab, title, tab, page number. A Word contents field
    # copies the heading text, so the typed number survives into the file.
    def entry(number: str, title: str, page: str) -> str:
        tab = "<w:r><w:tab/></w:r>"
        return f"<w:p>{_run(number)}{tab}{_run(title)}{tab}{_run(page)}</w:p>"

    return build_docx(
        _p("CONTENTS")
        + entry("1.", "Definitions", "1")
        + entry("2.", "Term of Agreement", "2")
        + entry("3.", "Fees", "4")
        + _p("1. Definitions")
        + _p("1.1 Words have the meanings given here.")
        + _p("2. Term of Agreement")
        + _p("2.1 This Agreement starts on the Effective Date.")
        + _p("3. Fees")
        + _p("3.1 The Customer pays the Fees.")
    )


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
    "bomb_double_flate.pdf": (_bomb_double_flate_bytes, ErrorCode.TOO_MUCH_TEXT),
    "bomb_form.pdf": (_bomb_form_bytes, ErrorCode.TOO_MUCH_TEXT),
    "bomb_encrypted.pdf": (_bomb_encrypted_bytes, ErrorCode.TOO_MUCH_TEXT),
    "form_cycle.pdf": (_form_cycle_bytes, None),
    # Glyphs with no text mapping
    "unmapped_all.pdf": (lambda: unmapped_pdf((0, 3)), None),
    "unmapped_page_two.pdf": (lambda: unmapped_pdf((20, 0), (1, 3)), None),
    # DOCX archive safety (A12)
    "simple.docx": (_simple_docx, None),
    "zip_dotdot.docx": (lambda: build_zip("../evil.txt"), ErrorCode.ARCHIVE_UNSAFE),
    "zip_backslash.docx": (lambda: build_zip("..\\evil.txt"), ErrorCode.ARCHIVE_UNSAFE),
    "zip_drive_letter.docx": (lambda: build_zip("C:\\evil.txt"), ErrorCode.ARCHIVE_UNSAFE),
    "zip_absolute.docx": (lambda: build_zip("/etc/evil.txt"), ErrorCode.ARCHIVE_UNSAFE),
    "zip_dots_in_name.docx": (lambda: build_zip("word/media/image..1.png"), None),
    "archive_too_large.docx": (_archive_too_large, ErrorCode.ARCHIVE_TOO_LARGE),
    "corrupt_zip.docx": (_corrupt_zip, ErrorCode.MALFORMED_FILE),
    # Tracked changes (A13)
    "tracked_insert.docx": (
        _tracked(f"<w:ins {_CHANGE}>{_run('Added.')}</w:ins>"),
        ErrorCode.TRACKED_CHANGES_PRESENT,
    ),
    "tracked_delete.docx": (
        _tracked(f"<w:del {_CHANGE}><w:r><w:delText>Gone.</w:delText></w:r></w:del>"),
        ErrorCode.TRACKED_CHANGES_PRESENT,
    ),
    "tracked_move_from.docx": (
        _tracked(f"<w:moveFrom {_CHANGE}>{_run('Moved.')}</w:moveFrom>"),
        ErrorCode.TRACKED_CHANGES_PRESENT,
    ),
    "tracked_move_to.docx": (
        _tracked(f"<w:moveTo {_CHANGE}>{_run('Moved.')}</w:moveTo>"),
        ErrorCode.TRACKED_CHANGES_PRESENT,
    ),
    "tracked_other_prefix.docx": (
        _tracked(f'<x:ins xmlns:x="{_WML}" {_CHANGE}>{_run("Added.")}</x:ins>'),
        ErrorCode.TRACKED_CHANGES_PRESENT,
    ),
    "tracked_paragraph_mark.docx": (
        _doc(f"<w:p><w:pPr><w:rPr><w:ins {_CHANGE}/></w:rPr></w:pPr>{_run('Marked.')}</w:p>"),
        ErrorCode.TRACKED_CHANGES_PRESENT,
    ),
    "tracked_in_header.docx": (
        lambda: build_docx(
            _p("Body."),
            [related_part("header", f"<w:p><w:ins {_CHANGE}>{_run('Header.')}</w:ins></w:p>")],
        ),
        ErrorCode.TRACKED_CHANGES_PRESENT,
    ),
    "tracked_in_footnotes.docx": (
        lambda: build_docx(
            _p("Body."),
            [
                related_part(
                    "footnotes",
                    f'<w:footnote w:id="1"><w:p><w:del {_CHANGE}><w:r><w:delText>Note.'
                    "</w:delText></w:r></w:del></w:p></w:footnote>",
                )
            ],
        ),
        ErrorCode.TRACKED_CHANGES_PRESENT,
    ),
    # The element name alone is not enough: the namespace decides.
    "foreign_ins.docx": (_tracked(f'{_run("Kept.")}<x:ins xmlns:x="urn:example:other"/>'), None),
    # Wrappers (A14), one fixture each
    "wrap_sdt.docx": (_doc(_SDT.format(_p("Inside a block control."))), None),
    "wrap_sdt_inline.docx": (
        _doc(f"<w:p>{_run('Before ')}{_SDT.format(_run('inside'))}{_run(' after')}</w:p>"),
        None,
    ),
    "wrap_smart_tag.docx": (
        _doc(
            f'<w:p><w:smartTag w:uri="urn:example" w:element="date">{_run("Dated 1 May.")}'
            "</w:smartTag></w:p>"
        ),
        None,
    ),
    "wrap_fld_simple.docx": (
        _doc(f'<w:p>{_run("Page ")}<w:fldSimple w:instr=" PAGE ">{_run("7")}</w:fldSimple></w:p>'),
        None,
    ),
    "wrap_custom_xml.docx": (
        _doc(f'<w:customXml w:element="clause">{_p("Inside custom xml.")}</w:customXml>'),
        None,
    ),
    "wrap_hyperlink.docx": (
        _doc(
            f'<w:p>{_run("See ")}<w:hyperlink w:anchor="schedule1">{_run("Schedule 1")}'
            f"</w:hyperlink>{_run('.')}</w:p>"
        ),
        None,
    ),
    "wrap_sdt_row.docx": (_doc(_tbl(_SDT.format(_tr(_tc(_p("Row in a control.")))))), None),
    "wrap_sdt_cell.docx": (_doc(_tbl(_tr(_SDT.format(_tc(_p("Cell in a control.")))))), None),
    "alt_chunk.docx": (_doc(_p("Before."), '<w:altChunk r:id="rId9"/>', _p("After.")), None),
    "unknown_block.docx": (_doc(_p("Before."), _OMATH, _p("After.")), None),
    # Text boxes and embedded objects (A15)
    "textbox_alternate_content.docx": (_doc(_alternate_content()), None),
    "textbox_vml.docx": (
        _doc(
            _anchor(_vml_box(_p("Boxed in VML."))),
            _p("Middle."),
            _anchor(_vml_box(_p("Second box."))),
        ),
        None,
    ),
    "textbox_nested.docx": (_doc(_nested_boxes()), None),
    "textbox_in_cell.docx": (
        _doc(
            _tbl(
                _tr(
                    _tc(
                        _p("Cell before."),
                        _anchor(_vml_box(_p("Boxed in a cell."))),
                        _p("Cell after."),
                    )
                )
            )
        ),
        None,
    ),
    "embedded_object.docx": (
        _doc(
            _p("Before."),
            '<w:p><w:r><w:object><v:shape/><o:OLEObject Type="Embed" ProgID="Excel.Sheet.12"/>'
            "</w:object></w:r></w:p>",
            _p("After."),
        ),
        None,
    ),
    # Tables (A16)
    "tables.docx": (
        _doc(
            _p("Parties"),
            _tbl(
                _tr(_tc(_p("A1")), _tc(_p("B1"))),
                _tr(_tc(_p("A2a"), _p("A2b")), _tc("<w:p/>")),
            ),
            _p("Between."),
            _tbl(_tr(_tc(_p("C1")))),
        ),
        None,
    ),
    "nested_table.docx": (
        _doc(
            _tbl(
                _tr(
                    _tc(
                        _p("Outer before."),
                        _tbl(_tr(_tc(_p("Inner one.")), _tc(_p("Inner two.")))),
                        _p("Outer after."),
                    ),
                    _tc(_p("Second cell.")),
                )
            )
        ),
        None,
    ),
    # Run content, empty paragraphs and entities
    "run_content.docx": (_doc(_RUN_CONTENT), None),
    "empty_paragraphs.docx": (_doc(_EMPTY_PARAGRAPHS), None),
    "entity_bomb.docx": (
        lambda: build_docx(
            _p("Visible.") + "<w:p><w:r><w:t>&e;</w:t></w:r></w:p>", prolog=_entity_prolog()
        ),
        ErrorCode.MALFORMED_FILE,
    ),
    # Numbering (A17)
    "list_number_style.docx": (_list_number_style, None),
    "numbering_levels.docx": (_numbering_levels, None),
    "empty_numbered.docx": (_empty_numbered, None),
    "numeral_after_h.docx": (lambda: _after_h(3, 3), None),
    "letter_after_h.docx": (lambda: _after_h(2, 2), None),
    # Page parts and notes (A18)
    "header_footer.docx": (_header_footer, None),
    "notes.docx": (_notes, None),
    "word_notes.docx": (_word_notes, None),
    # A typed contents list with tab-separated page numbers (A21)
    "contents_tab.docx": (_contents_tab, None),
}

NAMES = tuple(_BUILDERS)
VALID_NAMES = tuple(name for name, (_, expected) in _BUILDERS.items() if expected is None)


def build_all(directory: Path) -> Fixtures:
    """Writes every fixture into directory and maps its name to (path, expected error code)."""
    built: Fixtures = {}
    for name, (make, expected) in _BUILDERS.items():
        path = directory / name
        path.write_bytes(make())
        built[name] = (path, expected)
    return built
