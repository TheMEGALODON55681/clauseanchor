from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.scope import SCOPE_NOTICE, CatalogueError, Category, load_catalogue
from tests.synthetic import synthetic_catalogue


def _write(tmp_path: Path, data: object) -> Path:
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _reason(path: Path) -> str:
    with pytest.raises(CatalogueError) as err:
        load_catalogue(path)
    return err.value.reason


def _doc(**top: object) -> dict:
    return {**synthetic_catalogue(), **top}


def _row(**changes: object) -> dict:
    return {**synthetic_catalogue()["categories"][0], **changes}


def test_loads_a_valid_catalogue(tmp_path: Path) -> None:
    catalogue = load_catalogue(_write(tmp_path, synthetic_catalogue()))
    assert catalogue.version == "synthetic-test-0"
    assert [c.id for c in catalogue.categories] == [
        "synthetic.alpha",
        "synthetic.beta",
        "synthetic.gamma",
    ]
    assert catalogue.categories[1] == Category(
        "synthetic.beta", "Synthetic Beta", "india_extension", "synthetic_status_b"
    )


def test_a_byte_order_mark_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "catalogue.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(synthetic_catalogue()).encode("utf-8"))
    assert load_catalogue(path).version == "synthetic-test-0"


def test_no_file_is_missing(tmp_path: Path) -> None:
    assert _reason(tmp_path / "nope.json") == "missing"


def test_a_directory_is_missing(tmp_path: Path) -> None:
    assert _reason(tmp_path) == "missing"


@pytest.mark.parametrize("raw", [b"", b"{not json", b"\xff\xfe\x00"])
def test_unreadable_content_is_invalid(tmp_path: Path, raw: bytes) -> None:
    path = tmp_path / "catalogue.json"
    path.write_bytes(raw)
    assert _reason(path) == "invalid"


BROKEN = {
    "top level is a list": [_doc()],
    "no version": {"categories": synthetic_catalogue()["categories"]},
    "empty version": _doc(catalogue_version=" "),
    "version not text": _doc(catalogue_version=3),
    "extra top-level key": _doc(extra=1),
    "no categories": _doc(categories=[]),
    "categories not a list": _doc(categories={}),
    "row not an object": _doc(categories=["text"]),
    "row missing a key": _doc(categories=[{"id": "x", "source": "cuad", "support_status": "s"}]),
    "row with an extra key": _doc(categories=[_row(description="text")]),
    "blank id": _doc(categories=[_row(id=" ")]),
    "id not text": _doc(categories=[_row(id=5)]),
    "unknown source": _doc(categories=[_row(source="other")]),
    "source not text": _doc(categories=[_row(source=[])]),
    "blank support status": _doc(categories=[_row(support_status="")]),
    "duplicate id": _doc(categories=[_row(), _row(display_name="Other name")]),
}


@pytest.mark.parametrize("doc", BROKEN.values(), ids=BROKEN.keys())
def test_a_catalogue_that_breaks_the_shape_is_invalid(tmp_path: Path, doc: object) -> None:
    assert _reason(_write(tmp_path, doc)) == "invalid"


def test_scope_notice_is_the_text_in_the_review_scope_section() -> None:
    phases = Path(__file__).parents[2] / "docs" / "app" / "Phases.md"
    assert f'this exact text: "{SCOPE_NOTICE}"' in phases.read_text(encoding="utf-8")
