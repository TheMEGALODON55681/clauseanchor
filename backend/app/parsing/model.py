from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

# Offsets everywhere are code points into ParsedDocument.source_text, end exclusive.

BlockKind = Literal["text", "table_cell", "header", "footer", "footnote"]


@dataclass(frozen=True, slots=True)
class Block:
    id: str
    kind: BlockKind
    start: int
    end: int
    text: str
    page: int | None
    bbox: tuple[float, float, float, float] | None
    locator: Mapping[str, int | str]


@dataclass(frozen=True, slots=True)
class StructureNode:
    id: str
    parent_id: str | None
    kind: Literal["heading", "section", "clause", "subclause", "schedule", "definition", "table"]
    label: str | None
    level: int
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class ParseWarning:
    code: str
    page: int | None = None
    detail: str | None = None  # a short fixed string, never document text


@dataclass(frozen=True, slots=True)
class Coverage:
    pages_total: int | None
    pages_with_text: int | None
    chars: int
    partial: bool  # True means content may be missing, so nothing may be reported "not found"


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    source_text: str
    text_sha256: str  # sha256 of source_text.encode("utf-8"), lowercase hex
    parser_version: str
    media_type: str
    page_count: int | None  # None for DOCX
    blocks: tuple[Block, ...]  # reading order
    nodes: tuple[StructureNode, ...]
    decorations: tuple[tuple[int, int], ...]  # header and footer block ranges
    warnings: tuple[ParseWarning, ...]
    coverage: Coverage
