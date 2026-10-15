from __future__ import annotations

import io
import logging
import re
import statistics
from dataclasses import dataclass
from itertools import chain, groupby, pairwise

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfminer.psexceptions import PSException
from pdfplumber.utils.exceptions import MalformedPDFException, PdfminerException

from app.parsing.assemble import TextAssembler
from app.parsing.errors import ErrorCode, ParseError, WarningCode
from app.parsing.model import ParsedDocument, ParseWarning

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


def _read(data: bytes) -> list[tuple[float, list[_Box]]]:
    """Returns (page width, words) per page. The only place library errors are caught."""
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return [
                (
                    float(page.width),
                    [
                        _Box(
                            w["text"],
                            float(w["x0"]),
                            float(w["x1"]),
                            float(w["top"]),
                            float(w["bottom"]),
                        )
                        # expand_ligatures=False keeps U+FB01 as one character (A6)
                        for w in page.extract_words(expand_ligatures=False)
                        if w["text"]
                    ],
                )
                for page in pdf.pages
            ]
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
    for row in rows:
        spans: list[list[float]] = []
        for word in sorted(row, key=lambda w: w.x0):
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
    edges = []
    for start, end in runs:
        if end - start < GUTTER_MIN_WIDTH:
            continue
        around = sum(1 for row in rows if _sides(row, end)[2] == "columns")
        if around >= MIN_ROWS_AROUND_GUTTER:
            edges.append(end)
    return edges


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
        # ponytail: three or more columns keep row order, so a real 3-column article reads
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


def parse_pdf(data: bytes) -> ParsedDocument:
    pages = _read(data)
    # Everything below works on plain data and sits outside the try in _read. The assembler
    # raises ValueError for an empty block, a caller bug that A1's catch tuple must not hide.
    assembler = TextAssembler()
    warnings: list[ParseWarning] = []
    for number, (width, words) in enumerate(pages, start=1):
        assembler.new_page()
        if not words:
            continue
        tolerance = statistics.median(w.bottom - w.top for w in words) / 2
        streams, warning = _streams(words, width, tolerance)
        if warning:
            warnings.append(ParseWarning(warning, page=number))
        char_width = statistics.median((w.x1 - w.x0) / len(w.text) for w in words)
        for index, lines in enumerate(_blocks(streams, char_width), start=1):
            assembler.add_block(
                [line.text for line in lines],
                kind="text",
                page=number,
                bbox=(
                    min(line.x0 for line in lines),
                    min(line.top for line in lines),
                    max(line.x1 for line in lines),
                    max(line.bottom for line in lines),
                ),
                locator={"page": number, "block": index},
            )
    return assembler.build(media_type="application/pdf", page_count=len(pages), warnings=warnings)
