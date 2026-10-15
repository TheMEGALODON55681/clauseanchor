"""Generates every PDF fixture at test time with reportlab, so no binary file is committed."""

from __future__ import annotations

import io
import os
from collections.abc import Callable
from pathlib import Path

import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.parsing.errors import ErrorCode

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
