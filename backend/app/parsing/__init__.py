from __future__ import annotations

from dataclasses import replace

from app.parsing.detect import detect_type
from app.parsing.docx import parse_docx
from app.parsing.errors import MAX_INPUT_BYTES, ErrorCode, ParseError, WarningCode
from app.parsing.model import ParsedDocument
from app.parsing.pdf import parse_pdf
from app.parsing.structure import build_structure

__all__ = ["ErrorCode", "ParseError", "ParsedDocument", "WarningCode", "parse_document"]


def parse_document(data: bytes) -> ParsedDocument:
    """Parses one PDF or DOCX held in memory. Raises ParseError with a fixed code when the file
    cannot be read completely. The structure tree needs the finished text, so it is built here
    and attached to the reader's result, and its warnings follow the reader's."""
    if len(data) > MAX_INPUT_BYTES:
        raise ParseError(ErrorCode.FILE_TOO_LARGE)
    kind = detect_type(data)  # raises EMPTY_FILE and UNSUPPORTED_TYPE
    doc = parse_pdf(data) if kind == "pdf" else parse_docx(data)
    nodes, warnings = build_structure(doc.source_text, doc.blocks)
    return replace(doc, nodes=nodes, warnings=(*doc.warnings, *warnings))
