"""Party nodes and `name_span` (ParserContract.md section 8).

Only the preamble is read: the text before the first numbered node, or the first 5,000 code points
when there is none, and never more than the first 20,000 code points of either. A party is a
segment of that text that ends at a `hereinafter referred to as` or `hereinafter called` anchor,
or at a list boundary (a standalone AND line, a top level `and` in a `by and between` sentence,
or the end of the block). A preamble with no such segment gives no party and no warning. Offsets
are code points into the source text, as everywhere else."""

from __future__ import annotations

import re
from bisect import bisect_right
from collections.abc import Callable, Sequence
from dataclasses import replace

from app.parsing.model import Block, NameSpan, StructureNode

_WINDOW = 5000  # the preamble of a document with no numbered node
_CAP = 20_000  # the longest stretch searched: the work grows with the square of it (2-R, R4)
_LOOKBACK = 2000  # how far back a bracket or a quote is looked for
_REACH = 400  # a standalone AND line starts a party only this close to the party before it
_NAME_MAX = 150
_RUN_MAX = 3  # the longest numbered run a restart at 1 replaces (ParserContract.md 7.4)
_NUMBERED = ("section", "clause", "subclause", "schedule")
_QUOTES = "\"'" + "".join(map(chr, (0x201C, 0x201D, 0x2018, 0x2019)))
_LEAD = r"[\s:,\-" + chr(0x2013) + chr(0x2014) + "]*"  # between a lead-in word and a party

_ANCHOR = re.compile(r"\bhereinafter\s+(?:referred\s+to\s+as|called)\b", re.IGNORECASE)
_BY_AND_BETWEEN = re.compile(rf"\bby\s+and\s+between\b{_LEAD}", re.IGNORECASE)
_BETWEEN_LINE = re.compile(rf"^[ \t]*between\b{_LEAD}", re.IGNORECASE | re.MULTILINE)
_BETWEEN = re.compile(rf"\bbetween\b{_LEAD}", re.IGNORECASE)
_AND_LINE = re.compile(r"^[ \t]*and[ \t]*[:,]?[ \t]*(?:\n\s*|$)", re.IGNORECASE | re.MULTILINE)
_AND = re.compile(r"\band\b|&", re.IGNORECASE)
_SHORT_NAME = re.compile(
    rf"\s*(?:the\s+)?[{_QUOTES}][^{_QUOTES}]{{1,80}}[{_QUOTES}]", re.IGNORECASE
)
_MARKER = re.compile(r"(?:\d{1,2}[.)]|\(\w{1,3}\)|[A-Za-z][.)])[ \t]+(?![A-Z]\.)")  # not "R. K."
_ROLES = (  # a lone anchor closes a party only when it defines one of these
    "party|contractor|supplier|vendor|purchaser|buyer|seller|client|employer|owner|lessor|lessee"
    "|licensor|licensee|consultant|company|bank|institute|university|authority|government"
    "|disclosing party|receiving party|first party|second party"
)
_ROLE = re.compile(rf"(?:the\s+)?(?:{_ROLES})\b", re.IGNORECASE)
_TERM_REACH = 60  # how far past a bare anchor a short name is looked for
_TERM = re.compile(rf"[{_QUOTES}]([^{_QUOTES}]{{1,80}})[{_QUOTES}]")
_ITEM = re.compile(r"(?:\d{1,2}[.)]|\(\d{1,2}\))[ \t]+")  # the next item of a numbered party list
_NAME_END = re.compile(  # the name also stops where the defining phrase starts (section 8)
    r",|\(|\s(?:a company|having|represented|through|incorporated|registered|residing|acting"
    r"|hereinafter)\b",
    re.IGNORECASE,
)


def add_parties(
    source_text: str, blocks: Sequence[Block], nodes: tuple[StructureNode, ...]
) -> tuple[StructureNode, ...]:
    """The nodes of the document with its party nodes added, in order of start then level, and
    with fresh ids. The numbered clause nodes that a numbered party list opened are replaced by
    the party nodes."""
    end, listed = _preamble(source_text, nodes)
    spans = _segments(source_text[: min(end, _CAP)], blocks)
    if not spans:
        return nodes
    parties = [
        StructureNode(
            f"party{i}",
            None,
            "party",
            None,
            1,
            s,
            e,
            source_text[s:e],
            _name_span(source_text, s, e),
        )
        for i, (s, e) in enumerate(spans)
    ]
    dropped = {n.id: n for n in listed if any(n.start < e and s < n.end for s, e in spans)}
    merged = sorted(
        [*(n for n in nodes if n.id not in dropped), *parties], key=lambda n: (n.start, n.level)
    )
    new_id = {n.id: f"n{i:04d}" for i, n in enumerate(merged, 1)}

    def parent(node: StructureNode) -> str | None:
        parent_id = node.parent_id
        while parent_id in dropped:  # a child of a replaced item goes up to its parent
            parent_id = dropped[parent_id].parent_id
        return new_id[parent_id] if parent_id else None

    return tuple(replace(n, id=new_id[n.id], parent_id=parent(n)) for n in merged)


def _preamble(text: str, nodes: Sequence[StructureNode]) -> tuple[int, list[StructureNode]]:
    """Where the preamble ends, and the false clause nodes in front of that point. A party or
    recital list of up to three level 1 numbers before the clauses is replaced by a restart at 1
    (7.4), and the nodes it opened stay behind in the tree."""
    numbered = [n for n in nodes if n.kind in _NUMBERED or (n.kind == "heading" and n.label)]
    if not numbered:
        return min(len(text), _WINDOW), []

    def item(node: StructureNode, number: int) -> bool:
        return node.kind == "section" and node.level == 1 and node.label == str(number)

    run = 0
    while run < min(_RUN_MAX, len(numbered)) and item(numbered[run], run + 1):
        run += 1
    if run and run < len(numbered) and item(numbered[run], 1):
        return numbered[run].start, numbered[:run]
    return numbered[0].start, []


def _segments(text: str, blocks: Sequence[Block]) -> list[tuple[int, int]]:
    starts = [b.start for b in blocks]

    def block(pos: int) -> tuple[int, int]:
        """The block that holds pos, or the next one when pos sits in a separator."""
        i = bisect_right(starts, pos) - 1
        if i < 0 or pos >= blocks[i].end:
            i += 1
        if i >= len(blocks):
            return pos, len(text)
        return blocks[i].start, max(blocks[i].start, min(blocks[i].end, len(text)))

    anchored: list[tuple[int, int, int]] = []  # where the lead-in ended, start, end
    floor = 0
    for anchor in _ANCHOR.finditer(text):
        if anchor.start() < floor:
            continue  # inside the defining phrase of the party before
        end = _phrase_end(text, anchor)
        lead, led = _lead_end(text, floor, anchor.start(), block)
        start = _after_marker(text, lead)
        if not (led or _is_role(text, anchor.end(), end)):
            continue  # a lone anchor that defines something else than a party
        if text[start : anchor.start()].strip() and not any(
            start < e and s < end for _, s, e in anchored
        ):
            anchored.append((lead, start, end))
        floor = end
    spans = [(start, end) for _, start, end in anchored]
    seen = {lead for lead, _, _ in anchored}

    openers = [(m, "sentence") for m in _BY_AND_BETWEEN.finditer(text)]
    openers += [(m, "list") for m in _BETWEEN_LINE.finditer(text)]
    openers += [(m, "and") for m in _AND_LINE.finditer(text)]
    for match, kind in sorted(openers, key=lambda item: item[0].start()):
        start = _after_marker(text, match.end())
        if match.end() in seen or not _starts_party(text, start):
            continue
        if any(s <= start < e for s, e in spans):
            continue
        if kind == "and" and not any(
            match.start() - _REACH <= e <= match.start() for _, e in spans
        ):
            continue  # an AND line that follows no party is not a list boundary
        end = block(start)[1]
        stop = _AND_LINE.search(text, start, end)
        if stop:
            end = stop.start()
        pieces = [(start, end)]
        while kind == "list" and not stop:  # a numbered list: each item is a party
            first, last = block(pieces[-1][1] + 1)
            item = _ITEM.match(text, first)
            if first < pieces[-1][1] or not item:
                break
            pieces.append((item.end(), last))
        if kind == "sentence":  # the connective of the sentence splits the parties
            joint = next(
                (
                    m
                    for m in _AND.finditer(text, start, end)
                    if not _open_at(text, start, m.start())
                ),
                None,
            )
            if joint:
                pieces = [(start, joint.start()), (_after_marker(text, joint.end()), end)]
        spans += [(s, len(text[:e].rstrip())) for s, e in pieces if text[s:e].strip()]

    kept: list[tuple[int, int]] = []
    for span in sorted(spans):
        if not kept or span[0] >= kept[-1][1]:
            kept.append(span)
    return kept


def _lead_end(
    text: str, floor: int, at: int, block: Callable[[int], tuple[int, int]]
) -> tuple[int, bool]:
    """Where the party that an anchor at `at` closes begins, before any list marker, and whether
    a lead-in word led to it: after the last lead-in word or AND line since the party before,
    else after the last top level `and` of the stretch that follows that party, else at the start
    of the block. An anchor with no lead-in word is lone."""
    tokens = [
        m.end()
        for rx in (_BETWEEN, _AND_LINE)  # the word also ends `by and between`
        for m in rx.finditer(text, floor, at)
    ]
    if tokens:
        return max(tokens), True
    if floor:
        joints = [
            m.end() for m in _AND.finditer(text, floor, at) if not _open_at(text, floor, m.start())
        ]
        return (joints[-1] if joints else floor), False
    return block(at)[0], False


def _is_role(text: str, after: int, end: int) -> bool:
    """Whether the short name that a defining phrase gives is a party role (Supplier, Bank...):
    the quoted name inside the phrase, else the words that follow the anchor."""
    quoted = _TERM.search(text, after, end)
    term = quoted[1] if quoted else text[after : max(end, after + _TERM_REACH)]
    return _ROLE.match(term.strip(" ()\t\r\n")) is not None


def _phrase_end(text: str, anchor: re.Match[str]) -> int:
    """The end of the defining phrase: the bracket that holds the anchor, else the quoted short
    name that follows it, else the anchor words."""
    before = text[: anchor.start()].rstrip()
    if before.endswith("("):
        depth = 0
        for i in range(len(before) - 1, min(len(text), len(before) + 500)):
            depth += (text[i] == "(") - (text[i] == ")")
            if depth == 0:
                return i + 1
    short = _SHORT_NAME.match(text, anchor.end())
    return short.end() if short else anchor.end()


def _open_at(text: str, low: int, pos: int) -> bool:
    """Whether `pos` sits inside brackets or quotes that opened after `low`. Only the last
    _LOOKBACK code points are read, so a long stretch of connectives costs linear time."""
    head = text[max(low, pos - _LOOKBACK) : pos]
    return (
        head.count("(") > head.count(")")
        or head.count('"') % 2 == 1
        or head.count(_QUOTES[2]) > head.count(_QUOTES[3])
    )


def _starts_party(text: str, pos: int) -> bool:
    """Whether a party can begin here: a word, a quote or a bracketed blank, not a stray dot."""
    return pos < len(text) and (text[pos].isalnum() or text[pos] in _QUOTES + "[")


def _after_marker(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    marker = _MARKER.match(text, pos)
    return marker.end() if marker else pos


def _name_span(text: str, start: int, end: int) -> NameSpan | None:
    """The name alone: from the first character that is not a space to before the first stop,
    trimmed of spaces and quotes. None when that is empty, over 150 code points or starts in
    lower case, and the whole node text then stands for the name."""
    stop = _NAME_END.search(text, start, end)
    low, high = start, stop.start() if stop else end
    while low < high and (text[low].isspace() or text[low] in _QUOTES):
        low += 1
    while high > low and (text[high - 1].isspace() or text[high - 1] in _QUOTES):
        high -= 1
    if low == high or high - low > _NAME_MAX or text[low].islower():
        return None
    return NameSpan(low, high)
