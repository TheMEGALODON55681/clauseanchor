"""The parse child: `python -m app.parse_worker`.

It reads one file from stdin, parses it, and writes one JSON object to stdout: `{"document": ...}`
(the full form of `to_json`) or `{"error": CODE}` for a ParseError, or for a document of more than
MAX_BLOCKS_AND_NODES blocks and nodes (TOO_MUCH_TEXT). The API parent starts a new
child for every parse, because the DOCX reader changes the process-wide warnings filter (B13).
Nothing is written to disk or logged. The parent discards stderr, since library messages can hold
document text.
"""

from __future__ import annotations

import json
import sys

from app.config import MAX_BLOCKS_AND_NODES
from app.parsing import ErrorCode, ParseError, parse_document
from app.parsing.schema import to_json


def run(data: bytes) -> dict[str, object]:
    try:
        document = parse_document(data)
        # The child pays for a file of many small blocks, so the parent never receives or stores it
        if len(document.blocks) + len(document.nodes) > MAX_BLOCKS_AND_NODES:
            return {"error": ErrorCode.TOO_MUCH_TEXT.value}
        return {"document": to_json(document)}
    except ParseError as error:
        return {"error": error.code.value}
    except MemoryError:
        return {"error": "PARSE_MEMORY_LIMIT"}


def main() -> int:
    data = sys.stdin.buffer.read()
    # json.dumps escapes every non-ASCII character, so the bytes need no encoding agreement
    sys.stdout.buffer.write(json.dumps(run(data)).encode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
