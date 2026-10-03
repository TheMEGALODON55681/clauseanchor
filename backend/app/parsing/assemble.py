from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from app.parsing.errors import MAX_TEXT_CHARS, ErrorCode, ParseError
from app.parsing.model import Block, BlockKind, Coverage, ParsedDocument, ParseWarning

PARSER_VERSION = "1.0.0"


class TextAssembler:
    """Builds source_text and fixes each block's offsets at the moment it is appended."""

    def __init__(self) -> None:
        self._pieces: list[str] = []
        self._length = 0  # running code-point count, so positions never come from a search
        self._blocks: list[Block] = []
        self._page_break = False

    def new_page(self) -> None:
        self._page_break = True

    def add_block(
        self,
        lines: Sequence[str],
        *,
        kind: BlockKind,
        page: int | None,
        bbox: tuple[float, float, float, float] | None,
        locator: Mapping[str, int | str],
    ) -> Block:
        text = "\n".join(
            part.rstrip(" \t")
            for line in lines
            for part in line.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        )
        if not text:
            # Callers skip empty paragraphs and cells; an empty block here is a caller bug.
            raise ValueError("block has no text")
        if not self._blocks:
            separator = ""
        elif self._page_break:
            separator = "\n\n"
        else:
            separator = "\n"
        start = self._length + len(separator)
        end = start + len(text)
        if end > MAX_TEXT_CHARS:
            raise ParseError(ErrorCode.TOO_MUCH_TEXT)
        self._pieces += (separator, text)
        self._length = end
        self._page_break = False
        block = Block(f"b{len(self._blocks) + 1:04d}", kind, start, end, text, page, bbox, locator)
        self._blocks.append(block)
        return block

    def build(
        self,
        *,
        media_type: str,
        page_count: int | None,
        warnings: Sequence[ParseWarning] = (),
        partial: bool = False,
    ) -> ParsedDocument:
        source_text = "".join(self._pieces)
        try:
            encoded = source_text.encode("utf-8")
        except UnicodeEncodeError:
            # A lone surrogate cannot be hashed or serialised, so the file is unusable.
            raise ParseError(ErrorCode.MALFORMED_FILE) from None
        if not source_text.strip():
            raise ParseError(ErrorCode.NO_TEXT_FOUND)
        blocks = tuple(self._blocks)
        return ParsedDocument(
            source_text=source_text,
            text_sha256=hashlib.sha256(encoded).hexdigest(),
            parser_version=PARSER_VERSION,
            media_type=media_type,
            page_count=page_count,
            blocks=blocks,
            nodes=(),
            decorations=tuple((b.start, b.end) for b in blocks if b.kind in ("header", "footer")),
            warnings=tuple(warnings),
            coverage=Coverage(
                pages_total=page_count,
                pages_with_text=None if page_count is None else len({b.page for b in blocks}),
                chars=len(source_text),
                partial=partial,
            ),
        )
