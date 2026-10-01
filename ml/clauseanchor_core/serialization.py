"""Strict JSON conversion and schema export for the core dataclasses."""

from dataclasses import asdict, fields, is_dataclass
import json
import math
from types import UnionType
from typing import Literal, Union, get_args, get_origin, get_type_hints

from .contract import AnalysisResult


def to_dict(result: AnalysisResult) -> dict:
    return asdict(result)


def to_json(result: AnalysisResult) -> str:
    return json.dumps(to_dict(result), ensure_ascii=False, indent=2, allow_nan=False)


def _decode(kind, value):
    origin, args = get_origin(kind), get_args(kind)
    if origin in (UnionType, Union):
        for option in args:
            try:
                return _decode(option, value)
            except (TypeError, ValueError):
                continue
        raise ValueError("Value does not match its declared union type.")
    if origin is Literal:
        if value not in args:
            raise ValueError("Unknown literal value.")
        return value
    if origin is list:
        if not isinstance(value, list):
            raise ValueError("Expected a JSON array.")
        return [_decode(args[0], item) for item in value]
    if kind is type(None):
        if value is not None:
            raise ValueError("Expected null.")
        return None
    if is_dataclass(kind):
        if not isinstance(value, dict):
            raise ValueError("Expected a JSON object.")
        names = {f.name for f in fields(kind)}
        if set(value) != names:
            raise ValueError(f"Missing or extra fields for {kind.__name__}.")
        hints = get_type_hints(kind)
        return kind(**{name: _decode(hints[name], value[name]) for name in names})
    if kind is float:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Expected a finite JSON number.")
        return float(value)
    if kind in (int, str, bool):
        if type(value) is not kind:
            raise ValueError(f"Expected {kind.__name__}.")
        return value
    raise TypeError(f"Unsupported wire type: {kind}")


def from_dict(value: dict) -> AnalysisResult:
    return _decode(AnalysisResult, value)


def result_json_schema() -> dict:
    definitions: dict = {}

    def visit(kind):
        origin, args = get_origin(kind), get_args(kind)
        if origin in (UnionType, Union):
            return {"anyOf": [visit(item) for item in args]}
        if origin is Literal:
            return {"enum": list(args)}
        if origin is list:
            return {"type": "array", "items": visit(args[0])}
        if kind is type(None):
            return {"type": "null"}
        primitives = {str: "string", int: "integer", float: "number", bool: "boolean"}
        if kind in primitives:
            return {"type": primitives[kind]}
        if is_dataclass(kind):
            name = kind.__name__
            if name not in definitions:
                definitions[name] = {}
                hints = get_type_hints(kind)
                definitions[name] = {
                    "type": "object", "additionalProperties": False,
                    "required": [f.name for f in fields(kind)],
                    "properties": {f.name: visit(hints[f.name]) for f in fields(kind)},
                }
            return {"$ref": f"#/$defs/{name}"}
        raise TypeError(f"Unsupported schema type: {kind}")

    root = visit(AnalysisResult)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **root,
            "$defs": definitions}
