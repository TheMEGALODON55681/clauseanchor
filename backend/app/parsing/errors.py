from __future__ import annotations

from enum import StrEnum

MAX_INPUT_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_TEXT_CHARS = 500_000  # code points of source_text, separators included
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024  # total uncompressed size of a DOCX archive


class ErrorCode(StrEnum):
    UNSUPPORTED_TYPE = "UNSUPPORTED_TYPE"
    EMPTY_FILE = "EMPTY_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    MALFORMED_FILE = "MALFORMED_FILE"
    ENCRYPTED_PDF = "ENCRYPTED_PDF"
    SCANNED_PDF = "SCANNED_PDF"
    TOO_MANY_PAGES = "TOO_MANY_PAGES"
    TOO_MUCH_TEXT = "TOO_MUCH_TEXT"
    ARCHIVE_TOO_LARGE = "ARCHIVE_TOO_LARGE"
    ARCHIVE_UNSAFE = "ARCHIVE_UNSAFE"
    TRACKED_CHANGES_PRESENT = "TRACKED_CHANGES_PRESENT"
    NO_TEXT_FOUND = "NO_TEXT_FOUND"


class WarningCode(StrEnum):
    COLUMN_ORDER_UNCERTAIN = "COLUMN_ORDER_UNCERTAIN"
    MORE_THAN_TWO_COLUMNS = "MORE_THAN_TWO_COLUMNS"
    BLANK_PAGE = "BLANK_PAGE"
    NUMBERING_AMBIGUOUS = "NUMBERING_AMBIGUOUS"
    NUMBERING_NOT_RENDERED = "NUMBERING_NOT_RENDERED"
    TEXT_BOX_CONTENT = "TEXT_BOX_CONTENT"
    EMBEDDED_OBJECT = "EMBEDDED_OBJECT"
    UNSUPPORTED_DOCX_FEATURE = "UNSUPPORTED_DOCX_FEATURE"
    # A warning, not an error: an executed contract often ends in a scanned signature page.
    PARTIALLY_SCANNED_PDF = "PARTIALLY_SCANNED_PDF"


class ParseError(Exception):
    """Rejects the whole file. The message is the code alone, so no document text can leak."""

    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code)
        self.code = code
