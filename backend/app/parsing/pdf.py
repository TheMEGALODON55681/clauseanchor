from __future__ import annotations

import io
import logging
import re
import statistics
import zlib
from bisect import bisect_left, bisect_right
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import accumulate, chain, groupby, islice, pairwise
from typing import Literal

import pdfplumber
from pdfminer.ascii85 import ascii85decode, asciihexdecode
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfminer.pdfpage import PDFPage
from pdfminer.pdftypes import (
    LITERALS_ASCII85_DECODE,
    LITERALS_ASCIIHEX_DECODE,
    LITERALS_FLATE_DECODE,
    LITERALS_LZW_DECODE,
    LITERALS_RUNLENGTH_DECODE,
    PDFStream,
    resolve1,
)
from pdfminer.psexceptions import PSException
from pdfplumber.page import Page
from pdfplumber.utils.exceptions import MalformedPDFException, PdfminerException

from app.parsing.assemble import TextAssembler
from app.parsing.errors import (
    MAX_DECODED_CONTENT_BYTES,
    MAX_PDF_PAGES,
    ErrorCode,
    ParseError,
    WarningCode,
)
from app.parsing.model import BlockKind, ParsedDocument, ParseWarning

# Amendment A7: a line pitch above this multiple of the page's median pitch starts a block.
PITCH_SPLIT_RATIO = 1.3
# Amendment A8 and the 1-B spec: a gutter is a strip at least this wide (points) that at most
# 40 percent of the rows touch, whose right edge lies in the middle 60 percent of the page.
GUTTER_MIN_WIDTH = 12.0
GUTTER_MAX_ROW_SHARE = 0.4
GUTTER_ZONE = (0.2, 0.8)
MIN_ROWS_AROUND_GUTTER = 2
EDGE_TOLERANCE = 1.0  # points of float noise at a column edge
INDENT_CHARS = 2  # a left edge further than this many median characters from the column edge

# A coarse numbering token at the start of a line: 1. or 1.1 or 1.1.1. or (a) or (iv) or (3).
# Bare numbers are left out, so "30 days" at the start of a wrapped line does not split.
_NUMBERING = re.compile(r"(?:\d+(?:\.\d+)+\.?|\d+\.|\([A-Za-z0-9]{1,4}\))\s")

# Amendment A9: a line whose middle sits in the top or bottom share of the page height is a
# header or footer candidate, and so is a page number that is the first or last row of the page.
# A candidate shaped like a page number is decoration at any page count: 3, Page 3,
# Page 3 of 10, 3/10 or - 3 -. Any other candidate must repeat.
MARGIN_SHARE = 0.08
MIN_REPEATS = 3  # pages, or half the pages when that is more
_PAGE_NUMBER = re.compile(
    r"[\s\-\N{EN DASH}\N{EM DASH}]*(?:page\s+)?\d{1,3}(?:\s*(?:of|/)\s*\d{1,3})?"
    r"[\s\-\N{EN DASH}\N{EM DASH}]*",
    re.IGNORECASE,
)

# Amendment A10: a page the images cover by more than this share is image-dominant. With fewer
# than SCANNED_MAX_CHARS characters outside the margins it is scanned. With fewer than
# PARTIAL_MAX_CHARS the document is partial, so a searchable scan (a page image over a real
# text layer) stays usable.
IMAGE_DOMINANT = 0.5
SCANNED_MAX_CHARS = 20
PARTIAL_MAX_CHARS = 200

# A glyph the font has no text for reaches us as (cid:N). A page is unreadable when more than
# this share of its glyphs are such tokens, and the file is partial.
UNMAPPED_MAX_SHARE = 0.25
_UNMAPPED = re.compile(r"\(cid:\d+\)")

_FLATE_CHUNK = 64 * 1024  # bytes of Flate output read per step while measuring a stream (A11)
_GROWING_FILTERS = (*LITERALS_FLATE_DECODE, *LITERALS_LZW_DECODE, *LITERALS_RUNLENGTH_DECODE)

# Both libraries put raw document bytes into log records and exception text (A1).
for _name in ("pdfminer", "pdfplumber"):
    logging.getLogger(_name).setLevel(logging.CRITICAL + 1)

# The closed tuple of library errors (A1). PSException is the base of every pdfminer error.
_LIBRARY_ERRORS = (
    PdfminerException,
    MalformedPDFException,
    PSException,
    TypeError,
    ValueError,
    AttributeError,
    AssertionError,
    KeyError,
    IndexError,
)


@dataclass(frozen=True, slots=True)
class _Box:
    """The text of a word or of a line of words, with its box in points from the page's top left."""

    text: str
    x0: float
    x1: float
    top: float
    bottom: float


@dataclass(frozen=True, slots=True)
class _Page:
    width: float
    height: float
    words: list[_Box]
    image_share: float  # 0 to 1, the share of the page area that images cover


def _decoded_length(stream: PDFStream, limit: int) -> int:
    """The length of a stream after Flate, read in chunks and abandoned once it passes limit.
    Leading ASCII85 and ASCIIHex filters are undone first, since they never grow the data and
    producers such as reportlab put them in front of Flate. A second filter that can grow the
    data (Flate, LZW or RunLength) is counted as past the limit: pdfminer inflates each stage
    in full, and a content stream has no use for such a chain. Any other filter counts the
    stored length, which can only understate it (A11)."""
    names = [name for name, _ in stream.get_filters()]
    if sum(name in _GROWING_FILTERS for name in names) > 1:
        return limit + 1
    data = stream.get_rawdata() or b""
    if stream.decipher and stream.objid is not None and stream.genno is not None:
        data = stream.decipher(stream.objid, stream.genno, data, stream.attrs)
    total = 0
    try:
        while names and names[0] in (*LITERALS_ASCII85_DECODE, *LITERALS_ASCIIHEX_DECODE):
            decode = ascii85decode if names.pop(0) in LITERALS_ASCII85_DECODE else asciihexdecode
            data = decode(data)
        if not names or names[0] not in LITERALS_FLATE_DECODE:
            return len(data)
        inflater = zlib.decompressobj()
        while total <= limit:
            chunk = inflater.decompress(data, _FLATE_CHUNK)
            total += len(chunk)
            data = inflater.unconsumed_tail
            if len(chunk) < _FLATE_CHUNK:  # output was not capped, so none is waiting
                break
    except (zlib.error, ValueError):
        pass  # pdfminer keeps what a damaged stream yields, so what was counted stands
    return total


def _content_streams(page: PDFPage, seen: set[object]) -> Iterator[PDFStream]:
    """A page's content streams, then every Form XObject reachable from its resources, nested
    forms included. `seen` spans the document, so a shared stream is yielded once and a form
    that draws itself ends."""

    def first_visit(stream: PDFStream) -> bool:
        key = stream.objid if stream.objid is not None else id(stream)
        if key in seen:
            return False
        seen.add(key)
        return True

    for item in page.contents:
        stream = resolve1(item)
        if isinstance(stream, PDFStream) and first_visit(stream):
            yield stream
    scopes: list[object] = [page.resources]
    while scopes:
        resources = resolve1(scopes.pop())
        xobjects = resolve1(resources.get("XObject")) if isinstance(resources, dict) else None
        for item in xobjects.values() if isinstance(xobjects, dict) else ():
            form = resolve1(item)
            is_form = isinstance(form, PDFStream) and (
                getattr(resolve1(form.get("Subtype")), "name", None) == "Form"
            )
            if is_form and first_visit(form):
                yield form
                scopes.append(form.get("Resources"))


def _check_budget(pages: list[PDFPage]) -> None:
    """Amendment A11. Stops at the first stream that takes the running total past the budget,
    so a compressed bomb is never decoded in full."""
    left = MAX_DECODED_CONTENT_BYTES
    seen: set[object] = set()
    for page in pages:
        for stream in _content_streams(page, seen):
            left -= _decoded_length(stream, left)
            if left < 0:
                raise ParseError(ErrorCode.TOO_MUCH_TEXT)


def _has_annotation_text(annots: object) -> bool:
    """True when a Widget or FreeText annotation holds text. The layout never sees it (A10)."""
    items = resolve1(annots)
    for item in items if isinstance(items, list) else ():
        annot = resolve1(item)
        if not isinstance(annot, dict):
            continue
        if getattr(resolve1(annot.get("Subtype")), "name", None) not in ("Widget", "FreeText"):
            continue
        for key in ("Contents", "V"):
            value = resolve1(annot.get(key))
            if isinstance(value, bytes | str) and value.strip():
                return True
    return False


def _page(page: Page) -> _Page:
    width, height = float(page.width), float(page.height)
    covered = sum(
        max(0.0, min(image["x1"], width) - max(image["x0"], 0.0))
        * max(0.0, min(image["bottom"], height) - max(image["top"], 0.0))
        for image in page.images
    )
    return _Page(
        width,
        height,
        [
            _Box(w["text"], float(w["x0"]), float(w["x1"]), float(w["top"]), float(w["bottom"]))
            # expand_ligatures=False keeps U+FB01 as one character (A6)
            for w in page.extract_words(expand_ligatures=False)
            if w["text"]
        ],
        min(1.0, covered / (width * height)) if width * height > 0 else 0.0,
    )


def _read(data: bytes) -> tuple[list[_Page], bool]:
    """Returns the pages, and whether any annotation holds text. The only place library errors
    are caught. The page count and the content budget are settled before any text is read."""
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            sources = list(islice(PDFPage.create_pages(pdf.doc), MAX_PDF_PAGES + 1))
            if len(sources) > MAX_PDF_PAGES:
                raise ParseError(ErrorCode.TOO_MANY_PAGES)
            _check_budget(sources)
            pages = pdf.pages
            return [_page(p) for p in pages], any(
                _has_annotation_text(p.page_obj.annots) for p in pages
            )
    except PdfminerException as error:
        wrapped = error.args[0] if error.args else None
        if isinstance(wrapped, PDFPasswordIncorrect):
            raise ParseError(ErrorCode.ENCRYPTED_PDF) from None
        raise ParseError(ErrorCode.MALFORMED_FILE) from None
    except _LIBRARY_ERRORS:
        raise ParseError(ErrorCode.MALFORMED_FILE) from None


def _group(words: list[_Box], tolerance: float) -> list[list[_Box]]:
    """Clusters words into rows by `top`, from the first word of each row."""
    rows: list[list[_Box]] = []
    for word in sorted(words, key=lambda w: (w.top, w.x0)):
        if rows and word.top - rows[-1][0].top <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
    return rows


def _line(words: list[_Box]) -> _Box:
    ordered = sorted(words, key=lambda w: w.x0)
    return _Box(
        " ".join(w.text for w in ordered),
        min(w.x0 for w in words),
        max(w.x1 for w in words),
        min(w.top for w in words),
        max(w.bottom for w in words),
    )


def _gutters(rows: list[list[_Box]]) -> list[float]:
    """Returns the right edge of every gutter: a strip of at least GUTTER_MIN_WIDTH points that
    at most GUTTER_MAX_ROW_SHARE of the rows touch and that has text on both sides."""
    deltas: dict[float, int] = {}
    ordered_rows = [sorted(row, key=lambda w: w.x0) for row in rows]
    for row in ordered_rows:
        spans: list[list[float]] = []
        for word in row:
            if spans and word.x0 <= spans[-1][1]:
                spans[-1][1] = max(spans[-1][1], word.x1)
            else:
                spans.append([word.x0, word.x1])
        for start, end in spans:
            deltas[start] = deltas.get(start, 0) + 1
            deltas[end] = deltas.get(end, 0) - 1
    limit = GUTTER_MAX_ROW_SHARE * len(rows)
    xs = sorted(deltas)
    runs: list[list[float]] = []
    open_run = False
    count = 0
    for x, following in pairwise(xs):
        count += deltas[x]
        if count > limit:
            open_run = False
        elif open_run:
            runs[-1][1] = following
        else:
            runs.append([x, following])
            open_run = True
    edges = [end for start, end in runs if end - start >= GUTTER_MIN_WIDTH]
    # A row reads as "columns" at an edge (see _sides) when the split falls in one of its gaps of
    # GUTTER_MIN_WIDTH or more and no word on the left reaches the edge. Each such gap holds a
    # range of edges, so the rows are counted per edge with a difference array and not by testing
    # every row at every edge. `splits` is each edge as _sides compares it, so ties come out alike.
    splits = [edge - EDGE_TOLERANCE for edge in edges]
    rows_at = [0] * (len(edges) + 1)
    for row in ordered_rows:
        reach = list(accumulate((w.x1 for w in row), max))
        for k in range(1, len(row)):
            if row[k].x0 - reach[k - 1] < GUTTER_MIN_WIDTH:
                continue
            first = max(bisect_right(splits, row[k - 1].x0), bisect_left(edges, reach[k - 1]))
            last = bisect_right(splits, row[k].x0)
            if first < last:
                rows_at[first] += 1
                rows_at[last] -= 1
    counts = accumulate(rows_at)  # one longer than edges, for the closing decrement
    return [e for e, n in zip(edges, counts, strict=False) if n >= MIN_ROWS_AROUND_GUTTER]


def _sides(row: list[_Box], edge: float) -> tuple[list[_Box], list[_Box], str]:
    """Splits a row at a gutter's right edge. The third item is "crossing" when the row reads
    across the gutter, "columns" when words sit on both sides of a gap, otherwise "one"."""
    left = [w for w in row if w.x0 < edge - EDGE_TOLERANCE]
    right = [w for w in row if w.x0 >= edge - EDGE_TOLERANCE]
    spans = any(w.x1 > edge for w in left)
    if left and right:
        gap = min(w.x0 for w in right) - max(w.x1 for w in left)
        return left, right, "crossing" if spans or gap < GUTTER_MIN_WIDTH else "columns"
    return left, right, "crossing" if spans else "one"


def _two_columns(
    rows: list[list[_Box]], edge: float, tolerance: float
) -> tuple[list[list[_Box]], bool]:
    """Orders a two-column page as bands: lines that cross the gutter stand alone, and every
    run of column rows gives the left column then the right. The flag is True when a crossing
    run sits between two column runs, because then the reading order is a guess."""
    split = [(row, *_sides(row, edge)) for row in rows]
    streams: list[list[_Box]] = []
    crossing_runs: list[bool] = []
    for crossing, group in groupby(split, key=lambda item: item[3] == "crossing"):
        run = list(group)
        crossing_runs.append(crossing)
        if crossing:
            streams.append([_line(row) for row, *_ in run])
        else:
            left = list(chain.from_iterable(item[1] for item in run))
            right = list(chain.from_iterable(item[2] for item in run))
            streams += [
                [_line(g) for g in _group(side, tolerance)] for side in (left, right) if side
            ]
    return streams, any(crossing_runs[1:-1])


def _streams(
    words: list[_Box], width: float, tolerance: float
) -> tuple[list[list[_Box]], WarningCode | None]:
    rows = _group(words, tolerance)
    edges = _gutters(rows)
    if len(edges) > 1:
        # Ceiling: three or more columns keep row order, so a real 3-column article reads
        # across. Tables are the common case and read right that way.
        return [[_line(row) for row in rows]], WarningCode.MORE_THAN_TWO_COLUMNS
    if len(edges) == 1 and GUTTER_ZONE[0] * width <= edges[0] <= GUTTER_ZONE[1] * width:
        streams, uncertain = _two_columns(rows, edges[0], tolerance)
        return streams, WarningCode.COLUMN_ORDER_UNCERTAIN if uncertain else None
    return [[_line(row) for row in rows]], None


def _blocks(streams: list[list[_Box]], char_width: float) -> list[list[_Box]]:
    """Splits each stream of lines into blocks (A7). A line starts a block when the pitch from
    the line above exceeds PITCH_SPLIT_RATIO times the page's median pitch, when it begins with
    a numbering token, or when it returns to the stream's left edge from an indent. The return
    counts only for a block that began at the edge (a hanging indent), because a first-line
    indent also returns to the edge on its second line and that is no new paragraph. The first
    block of a stream always counts, since it may open on the tail of a paragraph from the
    page before."""
    pitches = [b.top - a.top for stream in streams for a, b in pairwise(stream)]
    limit = PITCH_SPLIT_RATIO * statistics.median(pitches) if pitches else float("inf")
    indent = INDENT_CHARS * char_width
    blocks: list[list[_Box]] = []
    for stream in streams:
        edge = min(line.x0 for line in stream)
        blocks.append([stream[0]])
        for above, line in pairwise(stream):
            opener = blocks[-1][0]
            if (
                line.top - above.top > limit
                or _NUMBERING.match(line.text)
                or (
                    line.x0 - edge <= indent < above.x0 - edge
                    and (opener is stream[0] or opener.x0 - edge <= indent)
                )
            ):
                blocks.append([line])
            else:
                blocks[-1].append(line)
    return blocks


def _unmapped_share(words: list[_Box]) -> float:
    """The share of a page's glyphs that have no text mapping. Each (cid:N) token is one glyph,
    however many characters it takes, so it is swapped for one character before counting."""
    glyphs = unmapped = 0
    for word in words:
        plain, found = _UNMAPPED.subn("x", word.text)
        glyphs += len(plain)
        unmapped += found
    return unmapped / glyphs if glyphs else 0.0


def _split(page: _Page) -> tuple[list[_Box], list[_Box], list[_Box], float]:
    """Splits a page's words by their vertical middle into the top margin, the body and the
    bottom margin (A9). A page number that is the page's first or last row counts as margin
    wherever it sits. The margins come back as lines and the body as words. The last item is
    the row tolerance, which every word on the page sets."""
    if not page.words:
        return [], [], [], 0.0
    tolerance = statistics.median(w.bottom - w.top for w in page.words) / 2
    edge = MARGIN_SHARE * page.height
    top: list[_Box] = []
    body: list[_Box] = []
    bottom: list[_Box] = []
    for word in page.words:
        middle = (word.top + word.bottom) / 2
        (top if middle < edge else bottom if middle > page.height - edge else body).append(word)
    # A page whose text stops half way down has its number mid-page, and on a two-column page
    # that number would join the left column and be read before the right one. The last row is
    # tried first, so a page that holds only a number gets a footer.
    rows = _group(page.words, tolerance)
    for row, zone in ((rows[-1], bottom), (rows[0], top)):
        in_body = {id(w) for w in body}
        if _PAGE_NUMBER.fullmatch(_line(row).text) and all(id(w) in in_body for w in row):
            taken = {id(w) for w in row}
            body = [w for w in body if id(w) not in taken]
            zone += row
    return (
        [_line(row) for row in _group(top, tolerance)],
        body,
        [_line(row) for row in _group(bottom, tolerance)],
        tolerance,
    )


def _key(text: str) -> str:
    """A margin line as the repetition rule compares it: lowercase, digits as #, spaces folded.
    Used for comparison only, never written back."""
    return " ".join(re.sub(r"\d", "#", text.lower()).split())


def _repeated(headers: list[list[_Box]], footers: list[list[_Box]]) -> set[tuple[str, str]]:
    """The (zone, key) pairs that recur on at least MIN_REPEATS pages and on at least half of
    all pages (A9)."""
    found: dict[tuple[str, str], set[int]] = {}
    for zone, per_page in (("header", headers), ("footer", footers)):
        for number, lines in enumerate(per_page):
            for line in lines:
                found.setdefault((zone, _key(line.text)), set()).add(number)
    needed = max(MIN_REPEATS, (len(headers) + 1) // 2)
    return {pair for pair, numbers in found.items() if len(numbers) >= needed}


def _kind(
    zone: Literal["header", "footer"], line: _Box, repeated: set[tuple[str, str]]
) -> BlockKind:
    if _PAGE_NUMBER.fullmatch(line.text) or (zone, _key(line.text)) in repeated:
        return zone
    return "text"


def parse_pdf(data: bytes) -> ParsedDocument:
    pages, annotated = _read(data)
    # Everything below works on plain data and sits outside the try in _read. The assembler
    # raises ValueError for an empty block, a caller bug that A1's catch tuple must not hide.
    split = [_split(page) for page in pages]
    repeated = _repeated([header for header, *_ in split], [footer for _, _, footer, _ in split])
    warnings: list[ParseWarning] = []
    scanned: list[int] = []
    content = 0  # pages that hold text or an image
    partial = annotated
    assembler = TextAssembler()
    for number, (page, (header, body, footer, tolerance)) in enumerate(
        zip(pages, split, strict=True), start=1
    ):
        assembler.new_page()
        if page.words or page.image_share:
            content += 1
        else:
            warnings.append(ParseWarning(WarningCode.BLANK_PAGE, page=number))
        if page.image_share > IMAGE_DOMINANT:
            chars = sum(len(w.text) for w in body)
            if chars < SCANNED_MAX_CHARS:
                scanned.append(number)
                warnings.append(ParseWarning(WarningCode.PARTIALLY_SCANNED_PDF, page=number))
            elif chars < PARTIAL_MAX_CHARS:
                partial = True
        if _unmapped_share(page.words) > UNMAPPED_MAX_SHARE:
            partial = True
            warnings.append(ParseWarning(WarningCode.UNMAPPED_GLYPHS, page=number))
        # Each margin candidate gets a block of its own, so decoration never fuses into text.
        groups: list[tuple[BlockKind, list[_Box]]] = [
            (_kind("header", line, repeated), [line]) for line in header
        ]
        if body:
            streams, warning = _streams(body, page.width, tolerance)
            if warning:
                warnings.append(ParseWarning(warning, page=number))
            char_width = statistics.median((w.x1 - w.x0) / len(w.text) for w in page.words)
            groups += [("text", lines) for lines in _blocks(streams, char_width)]
        groups += [(_kind("footer", line, repeated), [line]) for line in footer]
        for index, (kind, lines) in enumerate(groups, start=1):
            assembler.add_block(
                [line.text for line in lines],
                kind=kind,
                page=number,
                bbox=(
                    min(line.x0 for line in lines),
                    min(line.top for line in lines),
                    max(line.x1 for line in lines),
                    max(line.bottom for line in lines),
                ),
                locator={"page": number, "block": index},
            )
    if scanned and len(scanned) == content:
        raise ParseError(ErrorCode.SCANNED_PDF)
    return assembler.build(
        media_type="application/pdf",
        page_count=len(pages),
        warnings=warnings,
        partial=partial or bool(scanned),
        unreadable_pages=scanned,
    )
