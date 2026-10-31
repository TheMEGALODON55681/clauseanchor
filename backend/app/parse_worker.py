"""The parse child: `python -m app.parse_worker`.

It reads one file from stdin, parses it, and writes one JSON object to stdout: `{"document": ...}`
(the full form of `to_json`) or `{"error": CODE}` for a ParseError. The API parent starts a new
child for every parse, because the DOCX reader changes the process-wide warnings filter (B13).
Nothing is written to disk or logged. The parent discards stderr, since library messages can hold
document text.
"""

from __future__ import annotations

import json
import sys

from app.parsing import ParseError, parse_document
from app.parsing.schema import to_json


def run(data: bytes) -> dict[str, object]:
    try:
        return {"document": to_json(parse_document(data))}
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
