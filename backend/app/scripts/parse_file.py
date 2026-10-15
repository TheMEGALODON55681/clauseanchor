"""Development tool: parses a local file and prints the result. Nothing is written to disk.

    python -m app.scripts.parse_file CONTRACT.pdf [--text] [--summary]

The JSON leaves out every text field unless --text is given, so a result can be pasted into a
ticket without the contract. A ParseError prints its code to stderr and exits with status 2."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from app.parsing import ParseError, parse_document
from app.parsing.schema import to_json


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="parse_file", description="Parse a PDF or DOCX file and print the result."
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("--text", action="store_true", help="include source_text and block text")
    parser.add_argument("--summary", action="store_true", help="print counts instead of JSON")
    args = parser.parse_args(argv)
    try:
        doc = parse_document(args.path.read_bytes())
    except ParseError as error:
        print(error.code, file=sys.stderr)
        return 2
    if args.summary:
        pages = "none" if doc.page_count is None else doc.page_count
        print(f"pages: {pages}")
        print(f"blocks: {len(doc.blocks)}")
        print(f"nodes: {len(doc.nodes)}")
        print(f"decorations: {len(doc.decorations)}")
        print(f"warnings: {len(doc.warnings)}")
        print(f"partial: {'yes' if doc.coverage.partial else 'no'}")
    else:
        print(json.dumps(to_json(doc, text=args.text), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
