from __future__ import annotations

import io
import logging
import random
import struct
import time
import warnings
import zipfile
import zlib

import pytest

from app.parsing import docx as docx_module
from app.parsing.assemble import TextAssembler
from app.parsing.docx import parse_docx
from app.parsing.errors import MAX_TEXT_CHARS, ErrorCode, ParseError, WarningCode
from app.parsing.model import ParsedDocument
from tests.fixtures.build import build_docx

SWEEP_MUTANTS = 300
NBSP = "\N{NO-BREAK SPACE}"


def texts(doc: ParsedDocument) -> list[str]:
    return [block.text for block in doc.blocks]


def locators(doc: ParsedDocument) -> list[dict[str, int | str]]:
    return [dict(block.locator) for block in doc.blocks]


def warnings_of(doc: ParsedDocument) -> list[tuple[str, str | None]]:
    return [(w.code, w.detail) for w in doc.warnings]


def paragraph(text: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


def rejects(data: bytes) -> ErrorCode:
    with pytest.raises(ParseError) as exc:
        parse_docx(data)
    assert exc.value.__context__ is None or exc.value.__suppress_context__
    return exc.value.code


def patch_headers(data: bytes, *, flag_bit: int = 0, method: int | None = None) -> bytes:
    """Sets one general purpose flag bit, or the compression method, in every local and central
    header of a package."""
    out = bytearray(data)
    for signature, flags_at, method_at in ((b"PK\x03\x04", 6, 8), (b"PK\x01\x02", 8, 10)):
        at = out.find(signature)
        while at >= 0:
            if method is None:
                (flags,) = struct.unpack_from("<H", out, at + flags_at)
                struct.pack_into("<H", out, at + flags_at, flags | (1 << flag_bit))
            else:
                struct.pack_into("<H", out, at + method_at, method)
            at = out.find(signature, at + 4)
    return bytes(out)


def declare(
    data: bytes, member: str, *, compressed: int | None = None, size: int | None = None
) -> bytes:
    """Rewrites the compressed or uncompressed size the central directory declares for one
    member."""
    out = bytearray(data)
    at = out.find(b"PK")
    while at >= 0:
        (name_length,) = struct.unpack_from("<H", out, at + 28)
        if out[at + 46 : at + 46 + name_length] == member.encode():
            if compressed is not None:
                struct.pack_into("<I", out, at + 20, compressed)
            if size is not None:
                struct.pack_into("<I", out, at + 24, size)
            return bytes(out)
        at = out.find(b"PK", at + 4)
    raise AssertionError(member)


# A12: the archive


@pytest.mark.parametrize(
    ("name", "unsafe"),
    [
        ("../evil.txt", True),
        ("word/../../evil.txt", True),
        ("..\\evil.txt", True),
        ("word\\..\\..\\evil.txt", True),
        ("C:\\evil.txt", True),
        ("c:/evil.txt", True),
        ("/etc/evil.txt", True),
        ("\\\\server\\share\\evil.txt", True),
        ("word/document.xml", False),
        ("[Content_Types].xml", False),
        ("word/media/image..1.png", False),
        ("word\\media\\image.png", False),
    ],
)
def test_unsafe_names_are_recognised_after_backslashes_become_slashes(
    name: str, unsafe: bool
) -> None:
    assert docx_module._unsafe(name) is unsafe


def test_the_name_check_runs_before_any_member_is_read() -> None:
    entry = zipfile.ZipInfo("placeholder.txt")
    entry.filename = "../evil.txt"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", b"not xml at all")
        archive.writestr(entry, b"x")
    assert rejects(buffer.getvalue()) == ErrorCode.ARCHIVE_UNSAFE


def test_the_size_limit_is_inclusive_and_counts_declared_sizes(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    data = fixture_bytes["simple.docx"]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        total = sum(member.file_size for member in archive.infolist())
    monkeypatch.setattr(docx_module, "MAX_ARCHIVE_BYTES", total)
    assert parse_docx(data).blocks
    monkeypatch.setattr(docx_module, "MAX_ARCHIVE_BYTES", total - 1)
    assert rejects(data) == ErrorCode.ARCHIVE_TOO_LARGE


def test_a_member_that_lies_about_its_size_is_cut_short_and_refused(
    fixture_bytes: dict[str, bytes],
) -> None:
    # zipfile stops a member at its declared size, so a small claim cannot hide a large
    # member. The cut data then fails its checksum.
    data = declare(fixture_bytes["simple.docx"], "word/document.xml", size=8)
    assert rejects(data) == ErrorCode.MALFORMED_FILE


def test_a_member_whose_compressed_data_ends_early_is_malformed(
    fixture_bytes: dict[str, bytes],
) -> None:
    data = declare(fixture_bytes["simple.docx"], "word/document.xml", compressed=20)
    assert rejects(data) == ErrorCode.MALFORMED_FILE


def test_an_encrypted_member_is_malformed(fixture_bytes: dict[str, bytes]) -> None:
    assert rejects(patch_headers(fixture_bytes["simple.docx"])) == ErrorCode.MALFORMED_FILE


def test_an_unsupported_compression_method_is_malformed(fixture_bytes: dict[str, bytes]) -> None:
    data = patch_headers(fixture_bytes["simple.docx"], method=99)
    assert rejects(data) == ErrorCode.MALFORMED_FILE


def test_bytes_that_are_not_a_package_are_malformed(fixture_bytes: dict[str, bytes]) -> None:
    assert rejects(b"plain text") == ErrorCode.MALFORMED_FILE
    assert rejects(fixture_bytes["simple.pdf"]) == ErrorCode.MALFORMED_FILE


def test_a_package_without_a_main_document_is_malformed() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", b"<Types/>")
    assert rejects(buffer.getvalue()) == ErrorCode.MALFORMED_FILE


def test_a_document_part_with_no_body_is_malformed(fixture_bytes: dict[str, bytes]) -> None:
    empty = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
    data = rezip_with(fixture_bytes["simple.docx"], "word/document.xml", empty)
    assert rejects(data) == ErrorCode.MALFORMED_FILE


def test_overlapping_entries_are_malformed(fixture_bytes: dict[str, bytes]) -> None:
    data = fixture_bytes["simple.docx"]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        first = archive.infolist()[0]
    longer = declare(data, first.filename, compressed=first.compress_size + 200)
    assert rejects(longer) == ErrorCode.MALFORMED_FILE


def test_a_warning_from_the_archive_reader_does_not_escape(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    # zipfile warns about a duplicate header offset, and the text holds a name from the file.
    real = docx_module.Document

    def noisy(source: object) -> object:
        warnings.warn("Overlapped entries: 'name' (possible zip bomb)", stacklevel=2)
        return real(source)

    monkeypatch.setattr(docx_module, "Document", noisy)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert parse_docx(fixture_bytes["simple.docx"]).blocks
    assert caught == []


@pytest.mark.parametrize(
    "error",
    [
        EOFError(),
        zlib.error(),
        NotImplementedError(),
        RecursionError(),
        TypeError(),
        ValueError(),
        AttributeError(),
        AssertionError(),
        KeyError(),
        IndexError(),
    ],
    ids=lambda error: type(error).__name__,
)
def test_each_library_error_type_maps_to_malformed_file(
    error: Exception, fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object) -> None:
        raise error

    monkeypatch.setattr(docx_module, "Document", fail)
    assert rejects(fixture_bytes["simple.docx"]) == ErrorCode.MALFORMED_FILE


def test_an_error_outside_the_tuple_is_not_hidden(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object) -> None:
        raise ZeroDivisionError

    monkeypatch.setattr(docx_module, "Document", fail)
    with pytest.raises(ZeroDivisionError):
        parse_docx(fixture_bytes["simple.docx"])


# A13: tracked changes


def test_an_element_named_ins_in_another_namespace_is_not_a_tracked_change(
    fixture_bytes: dict[str, bytes],
) -> None:
    assert texts(parse_docx(fixture_bytes["foreign_ins.docx"])) == ["Before.", "Kept.", "After."]


# A14: wrappers and unknown blocks


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("wrap_sdt.docx", ["Inside a block control."]),
        ("wrap_sdt_inline.docx", ["Before inside after"]),
        ("wrap_smart_tag.docx", ["Dated 1 May."]),
        ("wrap_fld_simple.docx", ["Page 7"]),
        ("wrap_custom_xml.docx", ["Inside custom xml."]),
        ("wrap_hyperlink.docx", ["See Schedule 1."]),
        ("wrap_sdt_row.docx", ["Row in a control."]),
        ("wrap_sdt_cell.docx", ["Cell in a control."]),
    ],
)
def test_text_inside_a_wrapper_is_read_once_with_no_warning(
    name: str, expected: list[str], fixture_bytes: dict[str, bytes]
) -> None:
    doc = parse_docx(fixture_bytes[name])
    assert texts(doc) == expected
    assert doc.warnings == ()
    assert doc.coverage.partial is False


@pytest.mark.parametrize(
    ("name", "detail"), [("alt_chunk.docx", "altChunk"), ("unknown_block.docx", "unknown_block")]
)
def test_an_unknown_block_is_skipped_with_a_warning_and_partial(
    name: str, detail: str, fixture_bytes: dict[str, bytes]
) -> None:
    doc = parse_docx(fixture_bytes[name])
    assert texts(doc) == ["Before.", "After."]
    assert warnings_of(doc) == [(WarningCode.UNSUPPORTED_DOCX_FEATURE, detail)]
    assert doc.coverage.partial is True


@pytest.mark.parametrize("name", ["simple.docx", "tables.docx", "run_content.docx"])
def test_section_properties_and_table_properties_raise_no_warning(
    name: str, fixture_bytes: dict[str, bytes]
) -> None:
    doc = parse_docx(fixture_bytes[name])
    assert doc.warnings == ()
    assert doc.coverage.partial is False


@pytest.mark.parametrize(
    "wrapper",
    [
        'w:customXml w:element="clause"',
        'w:smartTag w:uri="urn:example" w:element="date"',
        'w:fldSimple w:instr=" PAGE "',
        'w:hyperlink w:anchor="schedule1"',
    ],
)
def test_a_wrapper_around_whole_paragraphs_is_seen_through(wrapper: str) -> None:
    tag = wrapper.split()[0]
    doc = parse_docx(build_docx(f"<{wrapper}>{paragraph('Inside.')}</{tag}>{paragraph('After.')}"))
    assert texts(doc) == ["Inside.", "After."]
    assert doc.warnings == ()


def test_markers_between_blocks_raise_no_warning() -> None:
    markers = (
        '<w:bookmarkStart w:id="0" w:name="clause"/><w:bookmarkEnd w:id="0"/>'
        '<w:proofErr w:type="spellStart"/><w:permStart w:id="1"/><w:permEnd w:id="1"/>'
        '<w:commentRangeStart w:id="2"/><w:commentRangeEnd w:id="2"/>'
    )
    doc = parse_docx(build_docx(paragraph("A.") + markers + paragraph("B.")))
    assert texts(doc) == ["A.", "B."]
    assert doc.warnings == ()
    assert doc.coverage.partial is False


@pytest.mark.parametrize(
    "body",
    [
        '<w:tbl><w:altChunk r:id="rId9"/><w:tr><w:tc><w:p>{}</w:p></w:tc></w:tr></w:tbl>',
        '<w:tbl><w:tr><w:altChunk r:id="rId9"/><w:tc><w:p>{}</w:p></w:tc></w:tr></w:tbl>',
    ],
    ids=["in a table", "in a row"],
)
def test_an_unknown_child_of_a_table_or_a_row_is_skipped_with_a_warning(body: str) -> None:
    doc = parse_docx(build_docx(body.format("<w:r><w:t>Cell.</w:t></w:r>")))
    assert texts(doc) == ["Cell."]
    assert warnings_of(doc) == [(WarningCode.UNSUPPORTED_DOCX_FEATURE, "altChunk")]
    assert doc.coverage.partial is True


# A15: text boxes and embedded objects


def test_alternate_content_yields_the_box_once_right_after_its_anchor(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_docx(fixture_bytes["textbox_alternate_content.docx"])
    assert texts(doc) == ["Anchor text.", "Boxed first.", "Boxed second.", "After the anchor."]
    assert locators(doc) == [
        {"part": "document", "paragraph": 1},
        {"part": "document", "textbox": 1, "paragraph": 1},
        {"part": "document", "textbox": 1, "paragraph": 2},
        {"part": "document", "paragraph": 2},
    ]
    assert [block.kind for block in doc.blocks] == ["text"] * 4
    assert doc.source_text.count("Boxed first.") == 1
    assert warnings_of(doc) == [(WarningCode.TEXT_BOX_CONTENT, None)]
    assert doc.coverage.partial is False


def test_bare_vml_yields_each_box_once_and_numbers_them_in_order(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_docx(fixture_bytes["textbox_vml.docx"])
    assert texts(doc) == ["Anchor text.", "Boxed in VML.", "Middle.", "Anchor text.", "Second box."]
    assert [loc.get("textbox") for loc in locators(doc)] == [None, 1, None, None, 2]
    assert warnings_of(doc) == [(WarningCode.TEXT_BOX_CONTENT, None)]


def test_a_box_inside_a_box_is_numbered_before_the_rest_of_its_outer_box(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_docx(fixture_bytes["textbox_nested.docx"])
    assert texts(doc) == ["Anchor text.", "Outer box.", "Inner box.", "Outer tail."]
    assert locators(doc)[1:] == [
        {"part": "document", "textbox": 1, "paragraph": 1},
        {"part": "document", "textbox": 2, "paragraph": 1},
        {"part": "document", "textbox": 1, "paragraph": 3},
    ]


def test_a_box_in_a_cell_splits_the_cell_text_around_it(fixture_bytes: dict[str, bytes]) -> None:
    doc = parse_docx(fixture_bytes["textbox_in_cell.docx"])
    assert [(b.kind, b.text) for b in doc.blocks] == [
        ("table_cell", "Cell before.\nAnchor text."),
        ("text", "Boxed in a cell."),
        ("table_cell", "Cell after."),
    ]
    cell = {"part": "document", "table": 1, "row": 1, "cell": 1}
    assert locators(doc) == [
        {**cell, "segment": 1},
        {"part": "document", "textbox": 1, "paragraph": 1},
        {**cell, "segment": 2},
    ]


def test_an_embedded_object_sets_partial_and_warns(fixture_bytes: dict[str, bytes]) -> None:
    doc = parse_docx(fixture_bytes["embedded_object.docx"])
    assert texts(doc) == ["Before.", "After."]
    assert warnings_of(doc) == [(WarningCode.EMBEDDED_OBJECT, None)]
    assert doc.coverage.partial is True


# A16: cells and paragraphs


def test_tables_are_numbered_and_empty_cells_are_skipped(fixture_bytes: dict[str, bytes]) -> None:
    doc = parse_docx(fixture_bytes["tables.docx"])
    assert [(b.kind, b.text) for b in doc.blocks] == [
        ("text", "Parties"),
        ("table_cell", "A1"),
        ("table_cell", "B1"),
        ("table_cell", "A2a\nA2b"),
        ("text", "Between."),
        ("table_cell", "C1"),
    ]
    assert locators(doc) == [
        {"part": "document", "paragraph": 1},
        {"part": "document", "table": 1, "row": 1, "cell": 1, "segment": 1},
        {"part": "document", "table": 1, "row": 1, "cell": 2, "segment": 1},
        {"part": "document", "table": 1, "row": 2, "cell": 1, "segment": 1},
        {"part": "document", "paragraph": 2},
        {"part": "document", "table": 2, "row": 1, "cell": 1, "segment": 1},
    ]


def test_text_before_and_after_a_nested_table_is_flushed_as_separate_blocks(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_docx(fixture_bytes["nested_table.docx"])
    assert texts(doc) == [
        "Outer before.",
        "Inner one.",
        "Inner two.",
        "Outer after.",
        "Second cell.",
    ]
    # Preorder: the outer table is 1 and the table inside it is 2.
    assert [(loc["table"], loc["cell"], loc["segment"]) for loc in locators(doc)] == [
        (1, 1, 1),
        (2, 1, 1),
        (2, 2, 1),
        (1, 1, 2),
        (1, 2, 1),
    ]


# Run content


def test_run_content_follows_the_run_text_rules(fixture_bytes: dict[str, bytes]) -> None:
    doc = parse_docx(fixture_bytes["run_content.docx"])
    assert texts(doc) == [
        "Term\t30-day",  # a tab, and a no-break hyphen as ASCII
        "first\nsecond\nthird",  # a line break and a carriage return
        "beforeafter",  # a page break adds nothing, so the words fuse (A24)
        f"two  spaces and{NBSP}nbsp",  # spaces and U+00A0 are kept
        "a b",  # a run of one space between two runs
        "result",  # field code text is not read, its result is
    ]


def test_empty_and_blank_paragraphs_make_no_block_but_still_count(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_docx(fixture_bytes["empty_paragraphs.docx"])
    assert texts(doc) == ["First.", "Second."]
    assert [loc["paragraph"] for loc in locators(doc)] == [3, 5]


def test_the_document_has_no_pages_and_blocks_join_with_a_newline(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_docx(fixture_bytes["simple.docx"])
    assert doc.media_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert doc.page_count is None
    assert (doc.coverage.pages_total, doc.coverage.pages_with_text) == (None, None)
    assert {block.page for block in doc.blocks} == {None}
    assert doc.source_text == "\n".join(texts(doc))
    assert doc.coverage.chars == len(doc.source_text)


def test_a_document_with_only_an_image_has_no_text() -> None:
    data = build_docx("<w:p><w:r><w:drawing/></w:r></w:p>")
    assert rejects(data) == ErrorCode.NO_TEXT_FOUND


# Entities and limits


def test_nested_entities_are_not_expanded(fixture_bytes: dict[str, bytes]) -> None:
    started = time.perf_counter()
    doc = parse_docx(fixture_bytes["entity_bomb.docx"])
    assert time.perf_counter() - started < 2
    assert doc.source_text == "Visible."


def test_the_text_limit_is_inclusive_and_stops_the_walk_before_the_assembler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert parse_docx(build_docx(paragraph("a" * MAX_TEXT_CHARS))).coverage.chars == MAX_TEXT_CHARS
    assert rejects(build_docx(paragraph("a" * (MAX_TEXT_CHARS + 1)))) == ErrorCode.TOO_MUCH_TEXT

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the assembler ran")

    monkeypatch.setattr(TextAssembler, "add_block", refuse)
    two = paragraph("a" * (MAX_TEXT_CHARS // 2 + 1)) * 2
    assert rejects(build_docx(two)) == ErrorCode.TOO_MUCH_TEXT


def test_an_empty_block_from_the_assembler_stays_a_value_error(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    # A1 puts ValueError in the DOCX catch tuple. The assembler call must sit outside that try,
    # or this caller bug would come back as MALFORMED_FILE.
    real = TextAssembler.add_block
    monkeypatch.setattr(
        TextAssembler, "add_block", lambda self, lines, **kw: real(self, [""], **kw)
    )
    with pytest.raises(ValueError, match="block has no text") as exc:
        parse_docx(fixture_bytes["simple.docx"])
    assert not isinstance(exc.value, ParseError)


# A1: damaged files


def mutate(data: bytes, rng: random.Random) -> bytes:
    out = bytearray(data)
    for _ in range(rng.randint(1, 4)):
        out[rng.randrange(len(out))] ^= rng.randint(1, 255)
    return bytes(out)


def rezip_with(data: bytes, member: str, content: bytes) -> bytes:
    """The same package with one member replaced, so every checksum is right again."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(buffer, "w") as target:
        for name in source.namelist():
            target.writestr(name, content if name == member else source.read(name))
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("name", "xml_only"),
    [
        ("simple.docx", False),
        ("simple.docx", True),
        ("textbox_alternate_content.docx", True),
        ("nested_table.docx", True),
    ],
)
def test_damaged_files_give_a_parse_or_a_parse_error_and_leak_nothing(
    name: str,
    xml_only: bool,
    fixture_bytes: dict[str, bytes],
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = fixture_bytes[name]
    # With a plain byte flip the zip checksum catches most damage, so a second kind of mutant
    # damages one XML member and repacks the package, which is what reaches the XML readers.
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        members = {n: archive.read(n) for n in archive.namelist() if n.endswith((".xml", ".rels"))}
    rng = random.Random(20261015)
    caplog.set_level(logging.DEBUG)
    parsed = rejected = 0
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(SWEEP_MUTANTS):
            if xml_only:
                member = rng.choice(list(members))
                mutant = rezip_with(original, member, mutate(members[member], rng))
            else:
                mutant = mutate(original, rng)
            try:
                doc = parse_docx(mutant)
            except ParseError as error:
                rejected += 1
                assert str(error) == error.code.value
                assert error.__context__ is None or error.__suppress_context__
            else:
                parsed += 1
                first = doc.blocks[0]
                assert doc.source_text[first.start : first.end] == first.text
    assert parsed and rejected  # the sweep reaches both outcomes
    assert caught == []
    assert caplog.records == []
