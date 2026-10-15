from __future__ import annotations

import hashlib

import pytest

from app.parsing.docx import parse_docx
from app.parsing.errors import ParseError
from app.parsing.pdf import parse_pdf
from tests.fixtures.build import NAMES, Fixtures


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
