from __future__ import annotations

import io
import re
import warnings
import zipfile
import zlib
from collections.abc import Iterator
from dataclasses import dataclass, field

from docx import Document
from docx.exceptions import PythonDocxError
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import NAMESPACE
from docx.opc.exceptions import OpcError
from docx.opc.part import XmlPart
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
    segment: int = 0


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


class _Walk:
    """Turns the body into plain items, in document order. It holds no assembler, so the
    assembler's own errors stay outside the library try block (A1)."""

    def __init__(self) -> None:
        self.items: list[_Item] = []
        self.warnings: dict[tuple[str, str | None], None] = {}  # ordered, no repeats
        self.partial = False
        self._chars = 0
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

    def flow(
        self,
        container: etree._Element,
        scope: dict[str, int | str],
        cell: _Cell | None = None,
    ) -> None:
        """Walks the block-level children of the body, a text box or a cell. In a cell the
        paragraphs gather into one block, flushed before a nested table or a text box."""
        count = 0
        for child in _children(container):
            if child.tag == _w("p"):
                count += 1
                text, boxes = self._paragraph(child)
                if text.strip():
                    if cell is None:
                        self._emit("text", text, {**scope, "paragraph": count})
                    else:
                        cell.lines.append(text)
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
            self._emit("table_cell", "\n".join(cell.lines), locator)
            cell.lines.clear()

    def _textbox(self, content: etree._Element) -> None:
        self._textboxes += 1
        self._warn(WarningCode.TEXT_BOX_CONTENT)
        self.flow(content, {"part": "document", "textbox": self._textboxes})

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
                    "part": "document",
                    "table": number,
                    "row": row,
                    "cell": column,
                }
                self.flow(cell, {}, _Cell(locator))


def _read(data: bytes) -> _Walk:
    """Returns the walked body. The only place library errors are caught. The archive checks
    run first, and no member is read before they pass."""
    try:
        _check_archive(data)
        with warnings.catch_warnings():
            # zipfile warns about overlapping entries and puts the member name in the text.
            # That name is file content, and it should not reach a server log.
            warnings.simplefilter("ignore")
            document = Document(io.BytesIO(data))
        for part in document.part.package.iter_parts():
            if part.content_type in _TEXT_PARTS:
                root = part.element if isinstance(part, XmlPart) else parse_xml(part.blob)
                if next(root.iter(*_TRACKED), None) is not None:
                    raise ParseError(ErrorCode.TRACKED_CHANGES_PRESENT)
        body = document.element.find(_w("body"))
        if body is None:
            raise ParseError(ErrorCode.MALFORMED_FILE)
        walk = _Walk()
        walk.flow(body, {"part": "document"})
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
