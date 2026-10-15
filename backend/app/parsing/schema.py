"""The JSON form of a ParsedDocument and its JSON Schema (docs/app/ParserContract.md).

`python -m app.parsing.schema` prints the schema. A test keeps the committed copy in
docs/app/parser_output.schema.json equal to it, and checks it against every parsed fixture."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, get_args, get_type_hints

from app.parsing.errors import WarningCode
from app.parsing.model import BlockKind, ParsedDocument, StructureNode

_OFFSET = {"type": "integer", "minimum": 0}
_PAGE = {"type": ["integer", "null"], "minimum": 1}


def _object(properties: dict[str, Any], optional: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [name for name in properties if name not in optional],
        "properties": properties,
    }


SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "ParsedDocument",
    **_object(
        {
            "source_text": {"type": "string"},
            "text_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "parser_version": {"type": "string"},
            "media_type": {
                "enum": [
                    "application/pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ]
            },
            "page_count": _PAGE,
            "blocks": {"type": "array", "items": {"$ref": "#/$defs/Block"}},
            "nodes": {"type": "array", "items": {"$ref": "#/$defs/StructureNode"}},
            "decorations": {
                "type": "array",
                "items": {"type": "array", "items": _OFFSET, "minItems": 2, "maxItems": 2},
            },
            "warnings": {"type": "array", "items": {"$ref": "#/$defs/ParseWarning"}},
            "coverage": {"$ref": "#/$defs/Coverage"},
        },
        optional=("source_text",),
    ),
    "$defs": {
        "Block": _object(
            {
                "id": {"type": "string"},
                "kind": {"enum": list(get_args(BlockKind))},
                "start": _OFFSET,
                "end": _OFFSET,
                "text": {"type": "string"},
                "page": _PAGE,
                "bbox": {
                    "type": ["array", "null"],
                    "items": {"type": "number"},
                    "minItems": 4,
                    "maxItems": 4,
                },
                "locator": {
                    "type": "object",
                    "additionalProperties": {"type": ["integer", "string"]},
                },
            },
            optional=("text",),
        ),
        "StructureNode": _object(
            {
                "id": {"type": "string"},
                "parent_id": {"type": ["string", "null"]},
                "kind": {"enum": list(get_args(get_type_hints(StructureNode)["kind"]))},
                "label": {"type": ["string", "null"]},
                "level": {"type": "integer", "minimum": 1},
                "start": _OFFSET,
                "end": _OFFSET,
                "text": {"type": "string"},
            },
            optional=("text",),
        ),
        "ParseWarning": _object(
            {
                "code": {"enum": [code.value for code in WarningCode]},
                "page": _PAGE,
                "detail": {"type": ["string", "null"]},
            }
        ),
        "Coverage": _object(
            {
                "pages_total": _PAGE,
                "pages_with_text": {"type": ["integer", "null"], "minimum": 0},
                "chars": _OFFSET,
                "partial": {"type": "boolean"},
            }
        ),
    },
}


def to_json(doc: ParsedDocument, *, text: bool = True) -> dict[str, Any]:
    """The document as plain data that json.dumps accepts. Without `text` the document text,
    the block text and the node text are left out, and every offset is still there."""
    data = asdict(doc)
    if not text:
        data.pop("source_text")
        for item in (*data["blocks"], *data["nodes"]):
            item.pop("text")
    return data


if __name__ == "__main__":
    print(json.dumps(SCHEMA, indent=2))
