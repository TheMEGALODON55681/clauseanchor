"""Clause structure tree and defined terms (amendments A19 to A22).

Works on block text and block offsets only. A label counts only when it continues a sequence or
starts one, so a number inside running text, a cross reference or a contents page does not
become a node."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple

from app.parsing.errors import WarningCode
from app.parsing.model import Block, ParseWarning, StructureNode

_BODY = ("text", "table_cell")
_SHORT = 80  # the longest line that reads as a heading
_SHORT_RUN = 3  # a numbered run this short may be replaced by a restart at 1
_KINDS = ("section", "clause", "subclause")  # by level, level 3 and deeper share the last

_DECIMAL = r"\d{1,3}(?:\.\d{1,3}){0,4}"
# What ends a heading label: an optional full stop, then white space or the end, and no lower
# case word on the same line. "Section 3 of this Agreement" is running text, "Section 3 Fees" is
# a heading. The look-ahead sits after the full stop so that backtracking cannot skip it.
_END = r"\.?(?=\s|$)(?![ \t]+[a-z])"
_NUMBER = re.compile(rf"({_DECIMAL})\.?(?=\s|$|[A-Z])")  # "10.Title" runs on, as some files do
_PAREN = re.compile(r"\(([a-z]{1,10})\)(?=\s|$)")
_ROMAN_HEADING = re.compile(r"([IVXLC]+)\.(?=\s|$)(?![ \t]+[a-z])")
_WORD = re.compile(rf"(?i:(article|section|clause))\s+({_DECIMAL}|[IVXLC]+)\b{_END}")
_SCHEDULE = re.compile(
    rf"(?i:schedule|annexure|appendix|exhibit)\s+(\d{{1,3}}|[IVXLC]+|[A-Z])\b{_END}"
)
_ROMAN_FORM = re.compile(r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})")
_NUMERALS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

# A contents line carries a dot leader, or ends in a page number (a space or a tab, then one
# to three digits). A year ends a line too, and has four digits.
_LEADER = re.compile(r"(?:\.\s?){4,}|" + chr(0x2026))
_PAGE_NUMBER = re.compile(r"\s\d{1,3}$")

_QUOTES = '"' + chr(0x201C) + chr(0x201D)
_TERM = rf"[{_QUOTES}]([^{_QUOTES}]{{1,80}})[{_QUOTES}]"
_VERB = r"(?:means|shall\s+mean|(?:has|have|shall\s+have)\s+the\s+meanings?|refers?\s+to)\b"
_DEFINITION = re.compile(rf"{_TERM},?\s+{_VERB}|\((?:the\s+)?{_TERM}\)", re.IGNORECASE)


class _Reading(NamedTuple):
    family: str  # dec, top, schedule, letter or roman
    parts: tuple[int, ...]  # the decimal parts, or the one numeral value
    kind: str  # "numbered" takes its kind from its level


class _Label(NamedTuple):
    text: str
    end: int  # where the label ends in the string it was read from
    readings: tuple[_Reading, ...]
    short: bool  # a schedule, article or roman heading counts only on a short line


@dataclass(slots=True)
class _Node:
    kind: str
    label: str | None
    level: int
    start: int
    end: int
    parent: _Node | None
    index: int
    family: str = ""
    parts: tuple[int, ...] = ()


def _roman(token: str) -> int | None:
    token = token.upper()
    if not token or _ROMAN_FORM.fullmatch(token) is None:
        return None
    following = token[1:] + " "
    return sum(
        -_NUMERALS[c] if _NUMERALS.get(n, 0) > _NUMERALS[c] else _NUMERALS[c]
        for c, n in zip(token, following, strict=True)
    )


def _parts(number: str) -> tuple[int, ...]:
    return tuple(int(part) for part in number.split("."))


def _parse(source: str) -> _Label | None:
    """Reads one label from the start of source: a schedule, an article or section heading, a
    letter or numeral in brackets, a roman heading, or a decimal number."""
    if m := _SCHEDULE.match(source):
        ident = m[1]
        if ident.isdigit():
            values: tuple[int | None, ...] = (int(ident),)
        else:  # a single letter such as C is a letter and a numeral
            values = (_roman(ident), ord(ident) - 64 if len(ident) == 1 else None)
        readings = tuple(_Reading("schedule", (v,), "schedule") for v in values if v)
        return _Label(m[0].rstrip("."), m.end(), readings, True) if readings else None
    if m := _WORD.match(source):
        ident = m[2]
        text = m[0].rstrip(".")
        if ident[0].isdigit():
            parts = _parts(ident)
            if m[1].lower() != "article":
                return _Label(text, m.end(), (_Reading("dec", parts, "heading"),), False)
            value = parts[0] if len(parts) == 1 else None
        else:
            value = _roman(ident)
        if not value:
            return None
        return _Label(text, m.end(), (_Reading("top", (value,), "heading"),), True)
    if m := _PAREN.match(source):
        token = m[1]
        found: list[_Reading] = []
        if len(set(token)) == 1:  # a to z, then aa, bb and on, as Word numbers letters
            value = 26 * (len(token) - 1) + ord(token[0]) - 96
            found.append(_Reading("letter", (value,), "numbered"))
        if value := _roman(token):
            found.append(_Reading("roman", (value,), "numbered"))
        return _Label(m[0], m.end(), tuple(found), False) if found else None
    if m := _ROMAN_HEADING.match(source):
        value = _roman(m[1])
        return (
            _Label(m[1], m.end(), (_Reading("top", (value,), "heading"),), True) if value else None
        )
    if m := _NUMBER.match(source):
        return _Label(m[1], m.end(), (_Reading("dec", _parts(m[1]), "numbered"),), False)
    return None


def _is_contents(text: str, rest: str) -> bool:
    """A contents entry: a dot leader anywhere in the block, or a one line block that ends in a
    page number once the label is taken off."""
    if _LEADER.search(text):
        return True
    return "\n" not in text and _PAGE_NUMBER.search(rest.strip()) is not None


def _is_caps_heading(text: str) -> bool:
    """A short block of capitals. Each line has to be mostly capitals, so that a block of
    redaction marks under a mixed case line is not one."""
    joined = text.replace("\n", " ")
    if len(joined) > _SHORT or _is_contents(text, joined):
        return False
    lines = [[c for c in line if c.isalpha()] for line in text.split("\n")]
    return sum(map(len, lines)) >= 3 and all(
        5 * sum(c.isupper() for c in letters) >= 3 * len(letters) for letters in lines
    )


def _outer_tables(blocks: Sequence[Block]) -> list[tuple[int, int]]:
    """Block index ranges of the tables that sit outside every other table. A nested table's
    cells fall inside its outer table's range, so it has no node of its own."""
    spans: dict[int | str, list[int]] = {}
    for index, block in enumerate(blocks):
        if block.kind == "table_cell":
            spans.setdefault(block.locator.get("table", 0), [index, index])[1] = index
    outer: list[tuple[int, int]] = []
    for first, last in sorted((s[0], s[1]) for s in spans.values()):
        if not outer or first > outer[-1][1]:
            outer.append((first, last))
    return outer


class _Builder:
    def __init__(self) -> None:
        self.nodes: list[_Node] = []
        self.stack: list[_Node] = []  # the open nodes, each deeper than the one below it
        # The last number accepted in each sequence and how long its run is: decimals by their
        # prefix, letters and numerals by the node they sit under.
        self.last: dict[tuple[object, ...], tuple[int, int]] = {}
        self.warnings: dict[ParseWarning, None] = {}
        self.body_end = 0  # end of the last body block read, where an open node ends
        self.titled = False  # the last block was a label with nothing after it

    def read(self, block: Block, table: _Node | None) -> None:
        if table is None:
            self._label(block)
        else:
            self.titled = False
        container = table or (self.stack[-1] if self.stack else None)
        for m in _DEFINITION.finditer(block.text):
            group = 1 if m[1] is not None else 2
            term = m[group]
            label = " ".join(term.rstrip(",.;").split())
            if term != term.strip() or not label:
                continue
            level = container.level + 1 if container else 1
            start = block.start + m.start(group) - 1  # the node holds the quotes
            self._add("definition", label, level, start, block.start + m.end(group) + 1, container)
        self.body_end = block.end

    def table(self, start: int, end: int) -> _Node:
        parent = self.stack[-1] if self.stack else None
        return self._add("table", None, parent.level + 1 if parent else 1, start, end, parent)

    def finish(
        self, source_text: str
    ) -> tuple[tuple[StructureNode, ...], tuple[ParseWarning, ...]]:
        for node in self.stack:
            node.end = self.body_end
        # Nodes are created in document order, a container before what it holds, so the order
        # of creation is the order of start and then level, and gives the ids.
        nodes = tuple(
            StructureNode(
                f"n{n.index + 1:04d}",
                f"n{n.parent.index + 1:04d}" if n.parent else None,
                n.kind,
                n.label,
                n.level,
                n.start,
                n.end,
                source_text[n.start : n.end],
            )
            for n in self.nodes
        )
        return nodes, tuple(self.warnings)

    def _add(
        self,
        kind: str,
        label: str | None,
        level: int,
        start: int,
        end: int,
        parent: _Node | None,
        family: str = "",
        parts: tuple[int, ...] = (),
    ) -> _Node:
        node = _Node(kind, label, level, start, end, parent, len(self.nodes), family, parts)
        self.nodes.append(node)
        return node

    def _open(
        self,
        block: Block,
        kind: str,
        label: str | None,
        level: int,
        family: str,
        parts: tuple[int, ...],
    ) -> None:
        while self.stack and self.stack[-1].level >= level:
            self.stack.pop().end = self.body_end
        parent = self.stack[-1] if self.stack else None
        node = self._add(kind, label, level, block.start, block.end, parent, family, parts)
        self.stack.append(node)

    def _label(self, block: Block) -> None:
        text = block.text
        titled, self.titled = self.titled, False
        given = block.locator.get("list_label")
        typed = not isinstance(given, str)  # a Word list label is read instead of the text
        label = _parse(text if typed else str(given))
        if label is None:
            # Capitals straight after a bare label are its title, and the label's node stays
            # open: otherwise the title would close it and take its clauses.
            if typed and not titled and _is_caps_heading(text):
                self._open(block, "heading", None, 1, "heading", ())
            return
        rest = text[label.end :] if typed else text
        if _is_contents(text, rest):
            return
        first, line = label.readings[0], text.split("\n", 1)[0]
        if typed and first.family == "dec" and first.kind == "numbered" and line == label.text:
            return  # a bare number with no full stop and no title is a page number
        if typed and label.short and len(line) > _SHORT:
            return
        best, score, ambiguous = None, 0, False
        for reading in label.readings:
            fit = self._fit(reading, listed=not typed)
            if fit > score:
                best, score = reading, fit
            elif fit == score == 2:
                ambiguous = True  # both readings continue a sequence: the first one stays
        if best is None:
            return
        if ambiguous:
            self.warnings[ParseWarning(WarningCode.NUMBERING_AMBIGUOUS, block.page)] = None
        level = self._level(best)
        kind = _KINDS[min(level, 3) - 1] if best.kind == "numbered" else best.kind
        key = self._key(best)
        current, length = self.last.get(key, (0, 0))
        number = best.parts[-1]
        if best.family == "schedule":
            self.last.clear()  # numbering starts again inside a schedule
        self.last[key] = (number, length + 1 if number == current + 1 else 1)
        self._open(block, kind, label.text, level, best.family, best.parts)
        self.titled = not rest.strip()

    def _fit(self, reading: _Reading, *, listed: bool) -> int:
        """2 when the reading continues its sequence, 1 when it starts one at 1, 0 when it
        does neither. A restart replaces only a short run: a party or recital list that comes
        before the clauses. A longer run restarting is a list inside a clause. A Word list's
        first top-level number may be above 1, because Word counts the empty paragraphs that
        the blocks leave out."""
        if reading.family == "dec" and not self._prefix_open(reading.parts[:-1]):
            return 0
        current, length = self.last.get(self._key(reading), (0, 0))
        number = reading.parts[-1]
        if current and number == current + 1:
            return 2
        if number == 1 and length <= _SHORT_RUN:
            return 1
        return int(listed and not current and reading.family == "dec" and len(reading.parts) == 1)

    def _prefix_open(self, prefix: tuple[int, ...]) -> bool:
        """A decimal under an open decimal of the same depth must carry that decimal's number.
        With none open the prefix is free, so ARTICLE I may be followed by 1.1."""
        for node in reversed(self.stack):
            if node.family == "dec" and len(node.parts) == len(prefix):
                return node.parts == prefix
        return True

    def _key(self, reading: _Reading) -> tuple[object, ...]:
        if reading.family == "dec":
            return ("dec", reading.parts[:-1])
        if reading.family in ("letter", "roman"):
            parent = self._parent(reading.family)
            return (reading.family, parent.index if parent else -1)
        return (reading.family,)

    def _level(self, reading: _Reading) -> int:
        if reading.family == "dec":
            in_schedule = bool(self.stack) and self.stack[0].family == "schedule"
            return len(reading.parts) + in_schedule
        if reading.family in ("letter", "roman"):
            parent = self._parent(reading.family)
            return parent.level + 1 if parent else 1
        return 1

    def _parent(self, family: str) -> _Node | None:
        """What a letter or a numeral sits under: the nearest open decimal (a letter) or letter
        (a numeral), else the nearest open node that is not a sibling of the same sort."""
        if family == "letter":
            preferred, siblings = "dec", ("letter", "roman")
        else:
            preferred, siblings = "letter", ("roman",)
        for node in reversed(self.stack):
            if node.family == preferred:
                return node
        for node in reversed(self.stack):
            if node.family not in siblings:
                return node
        return None


def build_structure(
    source_text: str, blocks: Sequence[Block]
) -> tuple[tuple[StructureNode, ...], tuple[ParseWarning, ...]]:
    """The clause tree of one document, and the warnings its numbering raised. Header, footer
    and footnote blocks are skipped. Nodes come in order of start, then level."""
    builder = _Builder()
    tables = iter(_outer_tables(blocks))
    span = next(tables, None)
    table: _Node | None = None
    for index, block in enumerate(blocks):
        if span and index == span[0]:
            table = builder.table(block.start, blocks[span[1]].end)
        if block.kind in _BODY:
            builder.read(block, table)
        if span and index == span[1]:
            span, table = next(tables, None), None
    return builder.finish(source_text)
