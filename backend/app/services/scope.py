"""The review scope: the fixed notice and the category catalogue.

The catalogue is Tanishq's (41 CUAD categories plus 5 India extensions), so this module
invents no id. `load_catalogue` is the only place that knows where it comes from.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# The exact text of Phases.md, "Review scope". A constant, never generated.
SCOPE_NOTICE = (
    "This review checks the listed clause categories. Other provisions and interactions between "
    "clauses may need manual review. Unhighlighted text is not a safety assessment."
)

SOURCES = ("cuad", "india_extension")
_FIELDS = {"id", "display_name", "source", "support_status"}


@dataclass(frozen=True, slots=True)
class Category:
    id: str
    display_name: str
    source: str
    support_status: str


@dataclass(frozen=True, slots=True)
class Catalogue:
    version: str
    categories: tuple[Category, ...]


class CatalogueError(Exception):
    """`reason` is `missing` (no readable file) or `invalid` (the file breaks the shape)."""

    def __init__(self, reason: Literal["missing", "invalid"]) -> None:
        super().__init__(reason)
        self.reason = reason


def _text(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def load_catalogue(path: Path) -> Catalogue:
    try:
        # utf-8-sig: Windows editors add a byte order mark that plain utf-8 would reject
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError:
        raise CatalogueError("missing") from None
    except ValueError:  # bad JSON and bad UTF-8 both
        raise CatalogueError("invalid") from None
    rows = data.get("categories") if isinstance(data, dict) else None
    if not (
        isinstance(rows, list)
        and rows
        and set(data) == {"catalogue_version", "categories"}
        and _text(data["catalogue_version"])
    ):
        raise CatalogueError("invalid")
    categories: list[Category] = []
    seen: set[str] = set()
    for row in rows:
        if not (
            isinstance(row, dict)
            and set(row) == _FIELDS
            and all(_text(v) for v in row.values())
            and row["source"] in SOURCES
            and row["id"] not in seen
        ):
            raise CatalogueError("invalid")
        seen.add(row["id"])
        categories.append(Category(**row))
    return Catalogue(data["catalogue_version"], tuple(categories))
