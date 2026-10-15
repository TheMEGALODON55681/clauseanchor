from __future__ import annotations

import io
import re
import warnings
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass, field

from docx import Document
from docx.exceptions import PythonDocxError
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import NAMESPACE
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.exceptions import OpcError
from docx.opc.part import Part, XmlPart
from docx.oxml import parse_xml
from lxml import etree

from app.parsing.assemble import TextAssembler
from app.parsing.errors import (
    MAX_ARCHIVE_BYTES,
    MAX_TEXT_CHARS,
    ErrorCode,
    ParseError,
    WarningCode,
)
from app.parsing.model import BlockKind, ParsedDocument, ParseWarning

_MEDIA_TYPE = CT.WML_DOCUMENT
_W = f"{{{NAMESPACE.WML_MAIN}}}"
_R = f"{{{NAMESPACE.OFC_RELATIONSHIPS}}}"
_MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _w(name: str) -> str:
    return _W + name


# The closed tuple of library errors (A1). RuntimeError is the zipfile error for an encrypted
# member, and the base of NotImplementedError (a compression method zipfile lacks) and of
# RecursionError. TypeError to IndexError are the ones the PDF reader
# catches too: a package whose XML is well formed but the wrong shape fails inside python-docx
# with AttributeError (a content types part with the wrong root), KeyError and the like.
_LIBRARY_ERRORS = (
    zipfile.BadZipFile,
    zlib.error,
    EOFError,  # a deflate stream that ends early
    etree.LxmlError,
    OpcError,
    PythonDocxError,
    RuntimeError,
    TypeError,
    ValueError,
    AttributeError,
    AssertionError,
    KeyError,
    IndexError,
)

# Amendment A13: any of these, in any text part, is a tracked change.
_TRACKED = tuple(_w(name) for name in ("ins", "del", "moveFrom", "moveTo"))
_TEXT_PARTS = {
    CT.WML_DOCUMENT_MAIN,
    CT.WML_HEADER,
    CT.WML_FOOTER,
    CT.WML_FOOTNOTES,
    CT.WML_ENDNOTES,
}

# Amendment A14: containers the walk sees through. An `sdt` holds its content in `sdtContent`.
_WRAPPERS = {_w(name) for name in ("customXml", "smartTag", "fldSimple", "hyperlink")}
# Block-level children that carry no text and are not a loss: properties and range markers.
_IGNORED = {
    _w(name)
    for name in (
        "sectPr",
        "tblPr",
        "tblGrid",
        "tblPrEx",
        "trPr",
        "tcPr",
        "customXmlPr",
        "smartTagPr",
        "bookmarkStart",
        "bookmarkEnd",
        "proofErr",
        "permStart",
        "permEnd",
        "commentRangeStart",
        "commentRangeEnd",
    )
}

# What a run contributes (the same set as the library's Run.text). A page break or a column
# break contributes nothing, so the words around it fuse (A24).
_RUN_TEXT = {_w("tab"): "\t", _w("ptab"): "\t", _w("cr"): "\n", _w("noBreakHyphen"): "-"}
# Subtrees of a paragraph that hold no text, or hold a copy of text that is read elsewhere.
_NO_TEXT = {_MC_FALLBACK, _w("pPr"), _w("rPr")}

# Amendment A18: the variants of a header or a footer.
_VARIANTS = ("default", "first", "even")
# Word's own machinery inside footnotes.xml and endnotes.xml: a rule and a notice, not text.
_NOTE_SEPARATORS = {"separator", "continuationSeparator", "continuationNotice"}

# Amendment A17. Bounds on what a numbering part can make the parser build for each paragraph.
_LEVELS = 9
_MAX_LABEL = 100  # code points of a rendered label, and of a level's text before substitution
_MAX_STYLE_DEPTH = 32  # a basedOn chain deeper than this is a cycle or a hostile file
_MAX_LETTERS = 780  # Word's own limit for letter numbering, 26 letters repeated 30 times
_ON = {"1", "true", "on"}
_PLACEHOLDER = re.compile(r"%([1-9])")
_ROMAN = (
    ("m", 1000),
    ("cm", 900),
    ("d", 500),
    ("cd", 400),
    ("c", 100),
    ("xc", 90),
    ("l", 50),
    ("xl", 40),
    ("x", 10),
    ("ix", 9),
    ("v", 5),
    ("iv", 4),
    ("i", 1),
)


class _Unrendered(Exception):
    """A list paragraph whose number cannot be computed. It never leaves this module and
    carries no document text."""


@dataclass(frozen=True, slots=True)
class _Item:
    kind: BlockKind
    text: str
    locator: dict[str, int | str]


@dataclass(slots=True)
class _Cell:
    """The text of one table cell, flushed as a block before and after anything nested."""

    locator: dict[str, int | str]
    lines: list[str] = field(default_factory=list)
    labels: list[str | None] = field(default_factory=list)  # one per line
    segment: int = 0


@dataclass(frozen=True, slots=True)
class _Level:
    start: int
    fmt: str
    text: str
    legal: bool  # isLgl: every number in the text shows as a decimal
    restart: int | None  # lvlRestart: 0 never, n after a paragraph of level n or shallower


@dataclass(frozen=True, slots=True)
class _List:
    """One w:num. `key` names the counters it shares: nums of one abstractNum continue each
    other, except a num with a startOverride, which counts on its own."""

    key: tuple[str, int]
    levels: dict[int, _Level]
    starts: dict[int, int]

    def start(self, index: int) -> int:
        return self.starts.get(index, self.levels[index].start)


def _val(element: etree._Element | None, name: str) -> str | None:
    """The w:val of a named child, or None when the child or the attribute is absent."""
    child = None if element is None else element.find(_w(name))
    return None if child is None else child.get(_w("val"))


def _number(value: str | None) -> int | None:
    """An unsigned integer attribute: None when absent, and a refusal when it is anything but
    a short run of digits, because a counter built from it cannot be trusted."""
    if value is None:
        return None
    if len(value) > 9 or not value.isascii() or not value.isdecimal():
        raise _Unrendered
    return int(value)


def _format(number: int, fmt: str) -> str:
    """A counter in one of the formats a contract uses. Any other format is not rendered."""
    if fmt == "decimal":
        return str(number)
    if fmt in ("lowerLetter", "upperLetter") and 1 <= number <= _MAX_LETTERS:
        # Word repeats the letter past z: aa, bb, cc, then aaa.
        text = chr(ord("a") + (number - 1) % 26) * ((number - 1) // 26 + 1)
    elif fmt in ("lowerRoman", "upperRoman") and 1 <= number <= 3999:
        text = ""
        for symbol, value in _ROMAN:
            count, number = divmod(number, value)
            text += symbol * count
    else:
        raise _Unrendered
    return text if fmt.startswith("lower") else text.upper()


def _level(element: etree._Element) -> _Level:
    text = _val(element, "lvlText") or ""
    if len(text) > _MAX_LABEL:
        raise _Unrendered
    legal = element.find(_w("isLgl"))
    return _Level(
        # The schema says an absent start is 0. Word writes it every time.
        start=_number(_val(element, "start")) or 0,
        fmt=_val(element, "numFmt") or "decimal",
        text=text,
        legal=legal is not None and legal.get(_w("val"), "1") in _ON,
        restart=_number(_val(element, "lvlRestart")),
    )


def _levels(abstract: etree._Element) -> dict[int, _Level]:
    levels: dict[int, _Level] = {}
    for element in abstract.findall(_w("lvl")):
        with suppress(_Unrendered):  # a level that cannot be read is a level not rendered
            index = _number(element.get(_w("ilvl")))
            if index is not None and index < _LEVELS:
                levels[index] = _level(element)
    return levels


class _Numbering:
    """Computes the label of a list paragraph (A17): the level's text with each %n replaced by
    the counter of level n. The label goes into the block locator and never into source_text.

    Ceiling: nums of one abstractNum share counters unless one has a startOverride. Word's
    finer rules for a restart inside one num (a lvl override with no startOverride, a restart
    in the middle of a list) are not modelled. Upgrade when a real contract renders wrong.
    """

    def __init__(self, styles: etree._Element | None, numbering: etree._Element | None) -> None:
        # style id -> (numId, ilvl, basedOn), kept as text and read when a paragraph uses it
        self._styles: dict[str, tuple[str | None, str | None, str | None]] = {}
        self._default_style: str | None = None
        self._lists: dict[int, _List] = {}
        self._counters: dict[tuple[str, int], list[int | None]] = {}
        if styles is not None:
            self._read_styles(styles)
        if numbering is not None:
            self._read_numbering(numbering)

    def _read_styles(self, root: etree._Element) -> None:
        for style in root.findall(_w("style")):
            style_id = style.get(_w("styleId"))
            if style.get(_w("type")) != "paragraph" or style_id is None:
                continue
            if style.get(_w("default")) in _ON:
                self._default_style = style_id
            properties = style.find(_w("pPr"))
            numbering = None if properties is None else properties.find(_w("numPr"))
            self._styles[style_id] = (
                _val(numbering, "numId"),
                _val(numbering, "ilvl"),
                _val(style, "basedOn"),
            )

    def _read_numbering(self, root: etree._Element) -> None:
        abstracts: dict[int, dict[int, _Level]] = {}
        for abstract in root.findall(_w("abstractNum")):
            with suppress(_Unrendered):
                abstract_id = _number(abstract.get(_w("abstractNumId")))
                if abstract_id is not None:
                    abstracts[abstract_id] = _levels(abstract)
        for num in root.findall(_w("num")):
            with suppress(_Unrendered):
                self._add(num, abstracts)

    def _add(self, num: etree._Element, abstracts: dict[int, dict[int, _Level]]) -> None:
        num_id = _number(num.get(_w("numId")))
        abstract_id = _number(_val(num, "abstractNumId"))
        if num_id is None or abstract_id not in abstracts:
            return
        levels = dict(abstracts[abstract_id])
        starts: dict[int, int] = {}
        for override in num.findall(_w("lvlOverride")):
            index = _number(override.get(_w("ilvl")))
            if index is None or index >= _LEVELS:
                continue
            replacement = override.find(_w("lvl"))
            if replacement is not None:
                levels[index] = _level(replacement)
            start = _number(_val(override, "startOverride"))
            if start is not None:
                starts[index] = start
        key = ("num", num_id) if starts else ("abstract", abstract_id)
        self._lists[num_id] = _List(key, levels, starts)

    def _style_numbering(self, style_id: str | None) -> tuple[int | None, int | None]:
        """The numId and ilvl a paragraph style gives, nearest style first through basedOn. A
        paragraph with no style gets the default paragraph style."""
        num_id = level = None
        current = style_id or self._default_style
        for _ in range(_MAX_STYLE_DEPTH):
            if current is None:
                break
            own_num, own_level, current = self._styles.get(current, (None, None, None))
            if num_id is None:
                num_id = _number(own_num)
            if level is None:
                level = _number(own_level)
        else:
            if current is not None:
                raise _Unrendered
        return num_id, level

    def label(self, paragraph: etree._Element) -> str | None:
        """The label of a paragraph, None when it is not numbered or its number is not text.
        Raises _Unrendered when it is numbered and the label cannot be worked out. The counters
        advance first, so a later paragraph still counts this one."""
        properties = paragraph.find(_w("pPr"))
        direct = None if properties is None else properties.find(_w("numPr"))
        style_num, style_level = self._style_numbering(_val(properties, "pStyle"))
        num_id = _number(_val(direct, "numId"))
        if num_id is None:
            num_id = style_num
        if not num_id:  # no numbering, or numId 0, which switches an inherited list off
            return None
        index = _number(_val(direct, "ilvl"))
        if index is None:
            index = style_level or 0
        definition = self._lists.get(num_id)
        level = None if definition is None else definition.levels.get(index)
        if definition is None or level is None:
            raise _Unrendered
        counters = self._counters.setdefault(definition.key, [None] * _LEVELS)
        for deeper in range(index + 1, _LEVELS):
            after = definition.levels[deeper].restart if deeper in definition.levels else None
            # Without lvlRestart a level restarts after any shallower one.
            if index <= (deeper - 1 if after is None else after - 1):
                counters[deeper] = None
        current = counters[index]
        counters[index] = definition.start(index) if current is None else current + 1
        if level.fmt in ("bullet", "none"):
            return None  # there is no number to render

        def number(match: re.Match[str]) -> str:
            target = int(match[1]) - 1
            if target not in definition.levels:
                raise _Unrendered
            value = counters[target]
            return _format(
                definition.start(target) if value is None else value,
                "decimal" if level.legal else definition.levels[target].fmt,
            )

        text = _PLACEHOLDER.sub(number, level.text)
        if len(text) > _MAX_LABEL:
            raise _Unrendered
        return text if text.strip() else None


def _unsafe(name: str) -> bool:
    path = name.replace("\\", "/")
    return (
        path.startswith("/") or re.match(r"[A-Za-z]:", path) is not None or ".." in path.split("/")
    )


def _check_archive(data: bytes) -> None:
    """Amendment A12. Reads the member list only. The declared sizes bound every later read,
    because zipfile stops a member at its declared size."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
    if any(_unsafe(member.filename) for member in members):
        raise ParseError(ErrorCode.ARCHIVE_UNSAFE)
    if sum(member.file_size for member in members) > MAX_ARCHIVE_BYTES:
        raise ParseError(ErrorCode.ARCHIVE_TOO_LARGE)


def _children(element: etree._Element) -> Iterator[etree._Element]:
    for child in element:
        if child.tag == _w("sdt"):
            content = child.find(_w("sdtContent"))
            if content is not None:
                yield from _children(content)
        elif child.tag in _WRAPPERS:
            yield from _children(child)
        else:
            yield child


def _root(part: Part) -> etree._Element:
    return part.element if isinstance(part, XmlPart) else parse_xml(part.blob)


def _related(part: Part, reltype: str) -> Iterator[Part]:
    """The parts this part relates to by one relationship type. An external target is not a
    part, and nothing is ever fetched from it."""
    for relationship in part.rels.values():
        if relationship.reltype == reltype and not relationship.is_external:
            yield relationship.target_part


def _sections(body: etree._Element) -> Iterator[etree._Element]:
    """The section properties of each section in order: those at the end of a paragraph, and
    the one that closes the body. A sectPr inside a property change is the old copy."""
    for element in body.iter(_w("sectPr")):
        parent = element.getparent()
        if parent is body or (parent.tag == _w("pPr") and parent.getparent().tag == _w("p")):
            yield element


class _Walk:
    """Turns the parts into plain items, in document order. It holds no assembler, so the
    assembler's own errors stay outside the library try block (A1)."""

    def __init__(self, numbering: _Numbering) -> None:
        self.items: list[_Item] = []
        self.warnings: dict[tuple[str, str | None], None] = {}  # ordered, no repeats
        self.partial = False
        self._numbering = numbering
        self._chars = 0
        self._scope: dict[str, int | str] = {}
        self._kind: BlockKind = "text"
        self._tables = 0
        self._textboxes = 0

    def _warn(self, code: WarningCode, detail: str | None = None) -> None:
        self.warnings[(code, detail)] = None

    def _emit(self, kind: BlockKind, text: str, locator: dict[str, int | str]) -> None:
        # The assembler enforces the limit too. This stops a huge part before it is all read.
        self._chars += len(text)
        if self._chars > MAX_TEXT_CHARS:
            raise ParseError(ErrorCode.TOO_MUCH_TEXT)
        self.items.append(_Item(kind, text, locator))

    def _unknown(self, child: etree._Element) -> None:
        """A14: an unknown block-level child is skipped, with a warning and partial."""
        if not isinstance(child.tag, str) or child.tag in _IGNORED:
            return  # a comment or processing instruction, or a marker that holds no text
        self.partial = True
        detail = "altChunk" if child.tag == _w("altChunk") else "unknown_block"
        self._warn(WarningCode.UNSUPPORTED_DOCX_FEATURE, detail)

    def _paragraph(self, paragraph: etree._Element) -> tuple[str, list[etree._Element]]:
        """The text of a paragraph, and the text boxes it anchors. Text box content is not
        part of the paragraph, and neither is the Fallback copy of a drawing (A15)."""
        parts: list[str] = []
        boxes: list[etree._Element] = []
        stack = [iter(paragraph)]
        while stack:
            for child in stack[-1]:
                tag = child.tag
                if tag == _w("t"):
                    parts.append(child.text or "")
                elif tag in _RUN_TEXT:
                    parts.append(_RUN_TEXT[tag])
                elif tag == _w("br"):
                    if child.get(_w("type"), "textWrapping") == "textWrapping":
                        parts.append("\n")
                elif tag == _w("txbxContent"):
                    boxes.append(child)
                elif tag not in _NO_TEXT:
                    if tag == _w("object"):
                        self.partial = True
                        self._warn(WarningCode.EMBEDDED_OBJECT)
                    stack.append(iter(child))
                    break
            else:
                stack.pop()
        return "".join(parts), boxes

    def _label(self, paragraph: etree._Element) -> str | None:
        try:
            return self._numbering.label(paragraph)
        except _Unrendered:
            self._warn(WarningCode.NUMBERING_NOT_RENDERED)
            return None

    def flow(
        self,
        container: etree._Element,
        scope: dict[str, int | str],
        cell: _Cell | None = None,
    ) -> None:
        """Walks the block-level children of a part, a text box or a cell. In a cell the
        paragraphs gather into one block, flushed before a nested table or a text box."""
        count = 0
        for child in _children(container):
            if child.tag == _w("p"):
                count += 1
                text, boxes = self._paragraph(child)
                label = self._label(child)  # every list paragraph counts, empty ones too
                if text.strip():
                    if cell is None:
                        locator = {**scope, "paragraph": count}
                        if label:
                            locator["list_label"] = label
                        self._emit(self._kind, text, locator)
                    else:
                        cell.lines.append(text)
                        cell.labels.append(label)
                if boxes:
                    self._flush(cell)
                    for box in boxes:
                        self._textbox(box)
            elif child.tag == _w("tbl"):
                self._flush(cell)
                self._table(child)
            else:
                self._unknown(child)
        self._flush(cell)

    def _flush(self, cell: _Cell | None) -> None:
        if cell is not None and cell.lines:
            cell.segment += 1
            locator = {**cell.locator, "segment": cell.segment}
            first = cell.labels[0]
            if len(cell.lines) == 1 and first:
                locator["list_label"] = first
            elif any(cell.labels):
                # One block holds several paragraphs, so a label has no paragraph to sit on.
                self._warn(WarningCode.NUMBERING_NOT_RENDERED)
            kind = "table_cell" if self._kind == "text" else self._kind
            self._emit(kind, "\n".join(cell.lines), locator)
            cell.lines.clear()
            cell.labels.clear()

    def _textbox(self, content: etree._Element) -> None:
        self._textboxes += 1
        self._warn(WarningCode.TEXT_BOX_CONTENT)
        self.flow(content, {**self._scope, "textbox": self._textboxes})

    def _table(self, table: etree._Element) -> None:
        self._tables += 1
        number, row = self._tables, 0
        for child in _children(table):
            if child.tag != _w("tr"):
                self._unknown(child)
                continue
            row += 1
            column = 0
            for cell in _children(child):
                if cell.tag != _w("tc"):
                    self._unknown(cell)
                    continue
                column += 1
                locator: dict[str, int | str] = {
                    **self._scope,
                    "table": number,
                    "row": row,
                    "cell": column,
                }
                self.flow(cell, {}, _Cell(locator))

    def part(self, root: etree._Element, scope: dict[str, int | str], kind: BlockKind) -> None:
        """Reads one part, or one note. Tables and text boxes are numbered within it."""
        self._scope, self._kind = scope, kind
        self._tables = self._textboxes = 0
        self.flow(root, scope)

    def page_parts(self, document: Part, body: etree._Element) -> None:
        """A18: every header and footer variant of every section, each part read once. Nothing
        is read for a variant a section does not name, because Word shows the previous
        section's part there and that part is read at the section that names it."""
        walked: set[Part] = set()  # bounds the work: a part named by 3,000 sections is read once
        seen: set[tuple[str, tuple[str, ...]]] = set()  # the same text twice is kept once
        for number, section in enumerate(_sections(body), start=1):
            for kind in ("header", "footer"):
                references = section.findall(_w(f"{kind}Reference"))
                names = {ref.get(_w("type")): ref.get(_R + "id") for ref in references}
                for variant in _VARIANTS:
                    if (relationship := names.get(variant)) is None:
                        continue
                    target = document.related_parts[relationship]
                    if target in walked:
                        continue
                    walked.add(target)
                    start, chars = len(self.items), self._chars
                    scope: dict[str, int | str] = {
                        "part": kind,
                        "section": number,
                        "variant": variant,
                    }
                    self.part(_root(target), scope, kind)
                    texts = (kind, tuple(item.text for item in self.items[start:]))
                    if texts in seen:
                        del self.items[start:]
                        self._chars = chars
                    seen.add(texts)

    def notes(self, document: Part) -> None:
        """A18: footnotes, then endnotes. Both come out as kind `footnote`, and the locator's
        part says which."""
        for reltype, name in ((RT.FOOTNOTES, "footnotes"), (RT.ENDNOTES, "endnotes")):
            for target in _related(document, reltype):
                for note in _root(target):
                    if note.tag != _w(name.removesuffix("s")):
                        continue
                    if note.get(_w("type")) in _NOTE_SEPARATORS:
                        continue
                    scope: dict[str, int | str] = {"part": name, "id": int(note.get(_w("id")))}
                    self.part(note, scope, "footnote")


def _read(data: bytes) -> _Walk:
    """Returns the walked document. The only place library errors are caught. The archive
    checks run first, and no member is read before they pass."""
    try:
        _check_archive(data)
        with warnings.catch_warnings():
            # zipfile warns about overlapping entries and puts the member name in the text.
            # That name is file content, and it should not reach a server log.
            warnings.simplefilter("ignore")
            document = Document(io.BytesIO(data))
        for part in document.part.package.iter_parts():
            if part.content_type in _TEXT_PARTS and (
                next(_root(part).iter(*_TRACKED), None) is not None
            ):
                raise ParseError(ErrorCode.TRACKED_CHANGES_PRESENT)
        body = document.element.find(_w("body"))
        if body is None:
            raise ParseError(ErrorCode.MALFORMED_FILE)
        styles, numbering = (
            next((_root(part) for part in _related(document.part, reltype)), None)
            for reltype in (RT.STYLES, RT.NUMBERING)
        )
        walk = _Walk(_Numbering(styles, numbering))
        walk.part(body, {"part": "document"}, "text")
        walk.page_parts(document.part, body)
        walk.notes(document.part)
        return walk
    except _LIBRARY_ERRORS:
        raise ParseError(ErrorCode.MALFORMED_FILE) from None


def parse_docx(data: bytes) -> ParsedDocument:
    walk = _read(data)
    # The assembler raises ValueError for an empty block, a caller bug that A1's catch tuple
    # must not hide, so it runs outside the try in _read.
    assembler = TextAssembler()
    for item in walk.items:
        assembler.add_block([item.text], kind=item.kind, page=None, bbox=None, locator=item.locator)
    return assembler.build(
        media_type=_MEDIA_TYPE,
        page_count=None,
        warnings=[ParseWarning(code, detail=detail) for code, detail in walk.warnings],
        partial=walk.partial,
    )
