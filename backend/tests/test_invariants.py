from __future__ import annotations

import hashlib
from collections.abc import Sequence

import pytest

from app.parsing.docx import parse_docx
from app.parsing.errors import ParseError
from app.parsing.model import ParsedDocument, StructureNode
from app.parsing.pdf import parse_pdf
from app.parsing.structure import build_structure
from tests.fixtures.build import NAMES, Fixtures


def assert_valid_nodes(doc: ParsedDocument, nodes: Sequence[StructureNode]) -> None:
    """The node half of the invariant: every node slices back to its text, nodes come in order
    of start then level, and a child sits inside its parent and one level below it or deeper."""
    by_id = {node.id: node for node in nodes}
    assert len(by_id) == len(nodes)
    size = len(doc.source_text)
    previous = (-1, 0)
    for node in nodes:
        assert 0 <= node.start < node.end <= size
        assert doc.source_text[node.start : node.end] == node.text
        assert (node.start, node.level) >= previous
        previous = (node.start, node.level)
        if node.parent_id is not None:
            parent = by_id[node.parent_id]
            assert parent.start <= node.start
            assert node.end <= parent.end
            assert parent.level < node.level


@pytest.mark.parametrize("name", NAMES)
def test_offsets_slice_back_to_the_text_for_every_fixture(name: str, fixtures: Fixtures) -> None:
    path, expected = fixtures[name]
    parse = parse_docx if name.endswith(".docx") else parse_pdf
    if expected is not None:
        with pytest.raises(ParseError) as exc:
            parse(path.read_bytes())
        assert exc.value.code == expected
        return
    doc = parse(path.read_bytes())
    size = len(doc.source_text)
    assert doc.text_sha256 == hashlib.sha256(doc.source_text.encode("utf-8")).hexdigest()
    previous_end = 0
    for block in doc.blocks:
        assert previous_end <= block.start < block.end <= size
        assert doc.source_text[block.start : block.end] == block.text
        previous_end = block.end
    for start, end in doc.decorations:
        assert 0 <= start <= end <= size
    nodes, _ = build_structure(doc.source_text, doc.blocks)
    assert_valid_nodes(doc, nodes)
