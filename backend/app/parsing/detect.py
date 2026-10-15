from __future__ import annotations

import io
import zipfile
from typing import Literal

from app.parsing.errors import ErrorCode, ParseError


def detect_type(data: bytes) -> Literal["pdf", "docx"]:
    """Names the file type from its magic bytes. Nothing is extracted from the archive."""
    if not data:
        raise ParseError(ErrorCode.EMPTY_FILE)
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())
        except (zipfile.BadZipFile, ValueError):
            # ValueError covers a member name that is not valid UTF-8 under the UTF-8 flag.
            raise ParseError(ErrorCode.MALFORMED_FILE) from None
        # A macro-enabled document (.docm) carries a VBA project, which is never opened.
        if "word/document.xml" in names and "word/vbaProject.bin" not in names:
            return "docx"
    raise ParseError(ErrorCode.UNSUPPORTED_TYPE)
