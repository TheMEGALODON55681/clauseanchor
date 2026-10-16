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
from tests.fixtures.build import (
    abstract_num,
    build_docx,
    end_section,
    level_xml,
    listed,
    num_xml,
    override_xml,
    reference,
    related_part,
    style_xml,
)

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
    data: bytes,
    member: str,
    *,
    compressed: int | None = None,
    size: int | None = None,
    crc: int | None = None,
) -> bytes:
    """Rewrites the compressed size, the uncompressed size or the checksum the central
    directory declares for one member."""
    out = bytearray(data)
    at = out.find(b"PK")
    while at >= 0:
        (name_length,) = struct.unpack_from("<H", out, at + 28)
        if out[at + 46 : at + 46 + name_length] == member.encode():
            if crc is not None:
                struct.pack_into("<I", out, at + 16, crc)
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


def test_the_size_limit_is_inclusive_and_counts_the_bytes_read(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    data = fixture_bytes["simple.docx"]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        total = sum(member.file_size for member in archive.infolist())
    monkeypatch.setattr(docx_module, "MAX_ARCHIVE_BYTES", total)
    assert parse_docx(data).blocks
    monkeypatch.setattr(docx_module, "MAX_ARCHIVE_BYTES", total - 1)
    assert rejects(data) == ErrorCode.ARCHIVE_TOO_LARGE


def test_the_limit_stops_a_member_in_the_middle_of_its_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The step is smaller than the member, so the limit trips before the member is all read.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", bytes(64))
    monkeypatch.setattr(docx_module, "_READ_STEP", 8)
    monkeypatch.setattr(docx_module, "MAX_ARCHIVE_BYTES", 16)
    assert rejects(buffer.getvalue()) == ErrorCode.ARCHIVE_TOO_LARGE


def test_a_member_that_lies_about_its_size_is_cut_short_and_refused(
    fixture_bytes: dict[str, bytes],
) -> None:
    # zipfile stops a member at its declared size. The cut data then fails its checksum.
    data = declare(fixture_bytes["simple.docx"], "word/document.xml", size=8)
    assert rejects(data) == ErrorCode.MALFORMED_FILE


def stored_members(data: bytes, monkeypatch: pytest.MonkeyPatch) -> dict[str, tuple[int, int]]:
    """Parses data and returns (method, size) of every member the library was handed."""
    seen: dict[str, tuple[int, int]] = {}
    real = docx_module.Document

    def spy(source: io.BytesIO) -> object:
        with zipfile.ZipFile(source) as archive:
            seen.update({m.filename: (m.compress_type, m.file_size) for m in archive.infolist()})
        return real(source)

    monkeypatch.setattr(docx_module, "Document", spy)
    parse_docx(data)
    return seen


def test_the_library_is_handed_every_member_stored_at_its_real_size(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    data = fixture_bytes["simple.docx"]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        original = {m.filename: m.file_size for m in archive.infolist()}
    handed = stored_members(data, monkeypatch)
    assert handed == {name: (zipfile.ZIP_STORED, size) for name, size in original.items()}


def test_a_member_that_lies_and_matches_its_checksum_is_cut_and_handed_over_stored(
    fixture_bytes: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The declared size is 100 and the checksum fits the first 100 bytes, so zipfile accepts
    # the cut. Left alone, python-docx would inflate all 3 MiB (up to 1 GiB for a larger
    # member) before the cut. The stored copy holds the 100 bytes and nothing else.
    padding = bytes(3 * 1024 * 1024)
    buffer = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(fixture_bytes["simple.docx"])) as source,
        zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        for name in source.namelist():
            target.writestr(name, source.read(name))
        target.writestr("word/media/padding.bin", padding)
    data = declare(
        buffer.getvalue(), "word/media/padding.bin", size=100, crc=zlib.crc32(padding[:100])
    )
    handed = stored_members(data, monkeypatch)
    assert handed["word/media/padding.bin"] == (zipfile.ZIP_STORED, 100)


def test_a_member_whose_compressed_data_ends_early_is_malformed(
    fixture_bytes: dict[str, bytes],
) -> None:
    data = declare(fixture_bytes["simple.docx"], "word/document.xml", compressed=20)
    assert rejects(data) == ErrorCode.MALFORMED_FILE


def test_an_encrypted_member_is_malformed(fixture_bytes: dict[str, bytes]) -> None:
    assert rejects(patch_headers(fixture_bytes["simple.docx"])) == ErrorCode.MALFORMED_FILE


@pytest.mark.parametrize("method", [zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA, 9, 99])
def test_a_member_that_is_neither_stored_nor_deflated_is_unsafe(
    method: int, fixture_bytes: dict[str, bytes]
) -> None:
    # zipfile has no output limit for bzip2 and lzma, so the method is refused before any read.
    data = patch_headers(fixture_bytes["simple.docx"], method=method)
    assert rejects(data) == ErrorCode.ARCHIVE_UNSAFE


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


# A17: numbering

DECIMAL = abstract_num(0, level_xml(0, "decimal", "%1."))
MULTILEVEL = abstract_num(
    0,
    level_xml(0, "decimal", "%1."),
    level_xml(1, "decimal", "%1.%2"),
    level_xml(2, "lowerLetter", "(%3)"),
)
NUMBERING_WARNING = [(WarningCode.NUMBERING_NOT_RENDERED, None)]


def labels(doc: ParsedDocument) -> list[int | str | None]:
    return [block.locator.get("list_label") for block in doc.blocks]


def numbered(body: str, *definitions: str, styles: str = "") -> ParsedDocument:
    extras = [related_part("numbering", "".join(definitions))]
    if styles:
        extras.append(related_part("styles", styles))
    return parse_docx(build_docx(body, extras))


def test_style_linked_numbering_labels_paragraphs_that_carry_no_numpr(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_docx(fixture_bytes["list_number_style.docx"])
    assert labels(doc) == ["1.", None, "2.", "3."]
    # The label is locator data. The text is the file's, so no offset moves.
    assert doc.source_text == "First item.\nBetween.\nSecond item.\nThird item."
    assert doc.warnings == ()
    assert doc.coverage.partial is False


def test_composite_labels_and_the_restart_of_deeper_levels(fixture_bytes: dict[str, bytes]) -> None:
    doc = parse_docx(fixture_bytes["numbering_levels.docx"])
    assert labels(doc) == ["1.", "1.1", "1.2", "(a)", "(b)", "(i)", "1.3", "(a)", "2.", "2.1"]
    assert doc.warnings == ()
    assert locators(doc)[1] == {"part": "document", "paragraph": 2, "list_label": "1.1"}


def test_a_style_chain_gives_the_list_and_the_level_from_different_styles() -> None:
    styles = (
        style_xml("Normal", default=True)
        + style_xml("Base", num_id=1)
        + style_xml("Child", based_on="Base", level=1)
        + style_xml("Grand", based_on="Child")
    )
    styles += style_xml("Other", based_on="Base", num_id=2)  # its own list beats its base's
    body = (
        listed("A.", style="Base")
        + listed("B.", style="Child")
        + listed("C.", style="Grand")
        + listed("D.", style="Grand", level=0)  # a direct level beats the one the style gives
        + listed("E.", style="Other")
    )
    nums = num_xml(1, 0) + num_xml(2, 0, override_xml(0, start=9))
    doc = numbered(body, MULTILEVEL, nums, styles=styles)
    assert labels(doc) == ["1.", "1.1", "1.2", "2.", "9."]


def test_a_paragraph_with_no_style_takes_the_default_paragraph_style() -> None:
    # A table style can be a default too, and it comes later in the part. It is not the one.
    table_default = '<w:style w:type="table" w:default="1" w:styleId="TableNormal"/>'
    styles = style_xml("Normal", default=True, num_id=1) + table_default
    doc = numbered(paragraph("A.") + paragraph("B."), DECIMAL, num_xml(1, 0), styles=styles)
    assert labels(doc) == ["1.", "2."]


def test_a_level_whose_text_is_blank_gives_no_label() -> None:
    abstract = abstract_num(0, level_xml(0, "decimal", "   "))
    doc = numbered(listed("A.", num_id=1, level=0), abstract, num_xml(1, 0))
    assert labels(doc) == [None]
    assert doc.warnings == ()


def test_numbers_and_levels_are_read_strictly() -> None:
    for value in ("-1", "+1", "1.5", "", "1" * 10, chr(0x663)):  # the last is Arabic-Indic three
        with pytest.raises(docx_module._Unrendered):
            docx_module._number(value)
    assert docx_module._number("007") == 7
    assert docx_module._number(None) is None
    namespace = docx_module.NAMESPACE.WML_MAIN
    long_text = f'<w:lvl xmlns:w="{namespace}"><w:lvlText w:val="{"x" * 101}"/></w:lvl>'
    with pytest.raises(docx_module._Unrendered):
        docx_module._level(docx_module.etree.fromstring(long_text))


def test_numid_zero_switches_off_a_list_the_style_gives() -> None:
    styles = style_xml("Normal", default=True) + style_xml("Item", num_id=1)
    body = (
        listed("A.", style="Item")
        + listed("B.", style="Item", num_id=0)
        + listed("C.", style="Item")
    )
    doc = numbered(body, DECIMAL, num_xml(1, 0), styles=styles)
    assert labels(doc) == ["1.", None, "2."]
    assert doc.warnings == ()


def test_start_values_and_start_overrides() -> None:
    abstract = abstract_num(0, level_xml(0, "decimal", "%1.", start=3))
    nums = num_xml(1, 0) + num_xml(2, 0, override_xml(0, start=7)) + num_xml(3, 0)
    body = "".join(
        listed(text, num_id=n, level=0)
        for text, n in [("a", 1), ("b", 1), ("c", 2), ("d", 2), ("e", 1), ("f", 3)]
    )
    # Num 2 counts on its own from 7. Num 3 has no override, so it continues num 1.
    assert labels(numbered(body, abstract, nums)) == ["3.", "4.", "7.", "8.", "5.", "6."]


def test_a_level_with_no_start_begins_at_zero() -> None:
    abstract = (
        '<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:numFmt w:val="decimal"/>'
        '<w:lvlText w:val="%1."/></w:lvl></w:abstractNum>'
    )
    body = listed("A.", num_id=1, level=0) + listed("B.", num_id=1, level=0)
    assert labels(numbered(body, abstract, num_xml(1, 0))) == ["0.", "1."]


def test_a_replacement_level_in_a_num_changes_the_text() -> None:
    replacement = level_xml(0, "upperLetter", "Part %1")
    nums = num_xml(1, 0, override_xml(0, level=replacement))
    doc = numbered(listed("A.", num_id=1, level=0), DECIMAL, nums)
    assert labels(doc) == ["Part A"]


def test_legal_numbering_shows_every_number_as_a_decimal() -> None:
    abstract = abstract_num(
        0,
        level_xml(0, "upperRoman", "ARTICLE %1"),
        level_xml(1, "decimal", "%1.%2", extra="<w:isLgl/>"),
        level_xml(2, "decimal", "%1.%2.%3"),
    )
    body = "".join(listed("x", num_id=1, level=n) for n in (0, 1, 2))
    assert labels(numbered(body, abstract, num_xml(1, 0))) == ["ARTICLE I", "1.1", "I.1.1"]


def test_lvl_restart_zero_never_restarts_and_a_value_restarts_after_that_level() -> None:
    never = abstract_num(
        0,
        level_xml(0, "decimal", "%1."),
        level_xml(1, "decimal", "%2.", extra='<w:lvlRestart w:val="0"/>'),
    )
    body = "".join(listed("x", num_id=1, level=n) for n in (0, 1, 1, 0, 1))
    assert labels(numbered(body, never, num_xml(1, 0))) == ["1.", "1.", "2.", "2.", "3."]

    # Level 4 restarts only after a paragraph of level 2 (restart value 2) or a shallower one.
    after_two = abstract_num(
        0,
        level_xml(0, "decimal", "%1."),
        level_xml(1, "decimal", "%2."),
        level_xml(2, "decimal", "%3."),
        level_xml(3, "decimal", "%4.", extra='<w:lvlRestart w:val="2"/>'),
    )
    body = "".join(listed("x", num_id=1, level=n) for n in (0, 1, 2, 3, 2, 3, 1, 3))
    got = labels(numbered(body, after_two, num_xml(1, 0)))
    assert [got[3], got[5], got[7]] == ["1.", "2.", "1."]


@pytest.mark.parametrize(
    ("fmt", "number", "expected"),
    [
        ("decimal", 12, "12"),
        ("lowerLetter", 1, "a"),
        ("lowerLetter", 26, "z"),
        ("lowerLetter", 27, "aa"),
        ("lowerLetter", 28, "bb"),
        ("upperLetter", 53, "AAA"),
        ("lowerRoman", 4, "iv"),
        ("lowerRoman", 9, "ix"),
        ("lowerRoman", 1994, "mcmxciv"),
        ("upperRoman", 3999, "MMMCMXCIX"),
        ("upperRoman", 14, "XIV"),
    ],
)
def test_number_formats(fmt: str, number: int, expected: str) -> None:
    assert docx_module._format(number, fmt) == expected


@pytest.mark.parametrize(
    ("fmt", "number"),
    [
        ("lowerLetter", 0),
        ("lowerLetter", 781),
        ("upperRoman", 0),
        ("upperRoman", 4000),
        ("decimalZero", 5),
        ("japaneseCounting", 1),
        ("ordinal", 1),
    ],
)
def test_formats_and_values_that_cannot_be_rendered_are_refused(fmt: str, number: int) -> None:
    with pytest.raises(docx_module._Unrendered):
        docx_module._format(number, fmt)


def test_an_unsupported_format_is_not_rendered_and_warns_once() -> None:
    abstract = abstract_num(
        0, level_xml(0, "japaneseCounting", "%1"), level_xml(1, "decimal", "%2.")
    )
    body = "".join(listed("x", num_id=1, level=n) for n in (0, 0, 1))
    doc = numbered(body, abstract, num_xml(1, 0))
    assert texts(doc) == ["x", "x", "x"]  # the text is read, only the label is missing
    assert labels(doc) == [None, None, "1."]
    assert warnings_of(doc) == NUMBERING_WARNING
    assert doc.coverage.partial is False


def test_bullets_have_no_number_to_render_so_no_label_and_no_warning() -> None:
    abstract = abstract_num(0, level_xml(0, "bullet", "&#8226;"), level_xml(1, "none", ""))
    body = listed("A.", num_id=1, level=0) + listed("B.", num_id=1, level=1)
    doc = numbered(body, abstract, num_xml(1, 0))
    assert labels(doc) == [None, None]
    assert doc.warnings == ()


def unresolved(case: str) -> ParsedDocument:
    item = listed("A.", num_id=9 if case == "unknown_num" else 1, level=5 if case == "level" else 0)
    garbage_id = DECIMAL.replace('abstractNumId="0"', 'abstractNumId="x"')
    garbage_start = abstract_num(0, level_xml(0, "decimal", "%1.", start=1)).replace(
        'w:start w:val="1"', 'w:start w:val="-3"'
    )
    definitions = {
        "missing_abstract": num_xml(1, 7),
        "garbage_id": garbage_id + num_xml(1, 0),
        "garbage_value": garbage_start + num_xml(1, 0),
    }.get(case, DECIMAL + num_xml(1, 0))
    if case == "no_part":
        return parse_docx(build_docx(item))
    return numbered(item, definitions)


@pytest.mark.parametrize(
    "case",
    ["no_part", "unknown_num", "level", "missing_abstract", "garbage_id", "garbage_value"],
)
def test_a_numbered_paragraph_that_cannot_be_resolved_keeps_its_text_and_warns(case: str) -> None:
    doc = unresolved(case)
    assert texts(doc) == ["A."]
    assert labels(doc) == [None]
    assert warnings_of(doc) == NUMBERING_WARNING


def test_an_empty_numbered_paragraph_still_counts() -> None:
    empty = '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr></w:p>'
    body = listed("One.", num_id=1, level=0) + empty + listed("Three.", num_id=1, level=0)
    assert labels(numbered(body, DECIMAL, num_xml(1, 0))) == ["1.", "3."]


def test_a_label_in_a_cell_needs_a_block_of_one_paragraph() -> None:
    def cell(*content: str) -> str:
        return f"<w:tc><w:tcPr/>{''.join(content)}</w:tc>"

    only = cell(listed("Only.", num_id=1, level=0))
    pair = cell(listed("First.", num_id=1, level=0), listed("Second.", num_id=1, level=0))
    table = f"<w:tbl><w:tblPr/><w:tr>{only}{pair}</w:tr></w:tbl>"
    doc = numbered(table + listed("After.", num_id=1, level=0), DECIMAL, num_xml(1, 0))
    assert [(b.text, b.locator.get("list_label")) for b in doc.blocks] == [
        ("Only.", "1."),
        ("First.\nSecond.", None),  # two paragraphs, one block, so no single label fits
        ("After.", "4."),  # the counters counted all four
    ]
    assert warnings_of(doc) == NUMBERING_WARNING


def test_a_text_box_paragraph_counts_after_its_anchor_and_before_the_next_paragraph() -> None:
    inner = listed("Boxed.", num_id=1, level=0)
    box = f"<w:r><w:pict><w:txbxContent>{inner}</w:txbxContent></w:pict></w:r>"
    anchor = (
        '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
        f"<w:r><w:t>Anchor.</w:t></w:r>{box}</w:p>"
    )
    doc = numbered(anchor + listed("After.", num_id=1, level=0), DECIMAL, num_xml(1, 0))
    assert [(b.text, b.locator.get("list_label")) for b in doc.blocks] == [
        ("Anchor.", "1."),
        ("Boxed.", "2."),
        ("After.", "3."),
    ]


def test_a_style_cycle_is_not_rendered() -> None:
    styles = style_xml("A", based_on="B") + style_xml("B", based_on="A")
    doc = numbered(listed("Cycle.", style="A"), DECIMAL, num_xml(1, 0), styles=styles)
    assert labels(doc) == [None]
    assert warnings_of(doc) == NUMBERING_WARNING


def test_a_hostile_numbering_part_is_refused_cheaply() -> None:
    # A level text of 50 placeholders makes a label longer than any real one, and a counter of
    # ten digits is not a counter. Neither may cost time or memory per paragraph.
    abstract = abstract_num(
        0, level_xml(0, "decimal", "%1" * 50), level_xml(1, "decimal", "%2.", start=10**9)
    )
    body = "".join(listed("x", num_id=1, level=n) for n in (0, 1) * 2500)
    started = time.perf_counter()
    doc = numbered(body, abstract, num_xml(1, 0))
    assert time.perf_counter() - started < 3
    shown = labels(doc)
    assert all(label is None or len(str(label)) <= 100 for label in shown)
    assert shown[1] is None  # the level with a ten digit start is not rendered at all
    assert shown[-2] is None  # level 1 outgrew the limit once its counter had four digits
    assert warnings_of(doc) == NUMBERING_WARNING


# A18: headers, footers and notes


def test_headers_and_footers_follow_the_body_each_part_once(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_docx(fixture_bytes["header_footer.docx"])
    assert [(b.kind, b.text) for b in doc.blocks] == [
        ("text", "Cover."),
        ("text", "Body of the agreement."),
        ("header", "ACME SERVICES AGREEMENT"),
        ("header", "DRAFT"),
        ("footer", "CONFIDENTIAL"),
        ("footer", "Page 1"),
        ("footer", "Even page footer."),
    ]
    # Section 2 names a second header part with the first one's text, and the footer part of
    # section 1 again. Neither adds a block.
    page = {"section": 1, "variant": "default"}
    assert locators(doc)[2:] == [
        {"part": "header", **page, "paragraph": 1},
        {"part": "header", "section": 1, "variant": "first", "paragraph": 1},
        {"part": "footer", **page, "table": 1, "row": 1, "cell": 1, "segment": 1},
        {"part": "footer", **page, "table": 1, "row": 1, "cell": 2, "segment": 1},
        {"part": "footer", "section": 2, "variant": "even", "paragraph": 1},
    ]
    assert doc.decorations == tuple((b.start, b.end) for b in doc.blocks[2:])
    assert doc.warnings == ()


def test_notes_follow_the_page_parts_and_skip_word_separators(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc = parse_docx(fixture_bytes["notes.docx"])
    assert [(b.kind, b.text) for b in doc.blocks] == [
        ("text", "Claim."),
        ("text", "Closing."),
        ("footnote", "First note."),
        ("footnote", "Second note."),
        ("footnote", "Its second paragraph."),
        ("footnote", "An endnote."),
    ]
    assert locators(doc)[2:] == [
        {"part": "footnotes", "id": 1, "paragraph": 1},
        {"part": "footnotes", "id": 2, "paragraph": 1},
        {"part": "footnotes", "id": 2, "paragraph": 2},
        {"part": "endnotes", "id": 1, "paragraph": 1},
    ]
    assert doc.decorations == ()  # a note is not furniture


def test_a_part_named_by_many_sections_is_read_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    real = docx_module._Walk.part

    def counting(self: object, root: object, scope: dict[str, object], kind: str) -> None:
        calls.append(scope["part"])
        real(self, root, scope, kind)  # type: ignore[arg-type]

    monkeypatch.setattr(docx_module._Walk, "part", counting)
    body = end_section(reference("header", "default", 1)) * 500 + paragraph("Body.")
    doc = parse_docx(build_docx(body, [related_part("header", paragraph("Running head."))]))
    assert calls.count("header") == 1
    assert texts(doc) == ["Body.", "Running head."]


def test_a_section_property_kept_inside_a_property_change_is_not_a_section() -> None:
    old = f"<w:sectPr>{reference('header', 'default', 1)}</w:sectPr>"
    change = (
        '<w:pPrChange w:id="1" w:author="Drafter" w:date="2026-01-01T00:00:00Z">'
        f"<w:pPr>{old}</w:pPr></w:pPrChange>"
    )
    body = f"<w:p><w:pPr>{change}</w:pPr><w:r><w:t>Body.</w:t></w:r></w:p>"
    doc = parse_docx(build_docx(body, [related_part("header", paragraph("Old header."))]))
    assert texts(doc) == ["Body."]


def test_a_reference_to_a_part_that_is_not_there_is_malformed() -> None:
    body = end_section(reference("header", "default", 9)) + paragraph("Body.")
    assert rejects(build_docx(body)) == ErrorCode.MALFORMED_FILE


def test_a_text_box_in_a_footer_carries_the_footers_locator() -> None:
    box = f"<w:r><w:pict><w:txbxContent>{paragraph('Boxed.')}</w:txbxContent></w:pict></w:r>"
    footer = f"<w:p><w:r><w:t>Anchor.</w:t></w:r>{box}</w:p>"
    section = reference("footer", "default", 1)
    data = build_docx(paragraph("Body."), [related_part("footer", footer)], section=section)
    doc = parse_docx(data)
    assert [(b.kind, b.text) for b in doc.blocks][1:] == [
        ("footer", "Anchor."),
        ("footer", "Boxed."),
    ]
    assert locators(doc)[2] == {
        "part": "footer",
        "section": 1,
        "variant": "default",
        "textbox": 1,
        "paragraph": 1,
    }
    assert warnings_of(doc) == [(WarningCode.TEXT_BOX_CONTENT, None)]
    assert doc.coverage.partial is False


def test_the_same_text_in_a_header_and_a_footer_is_kept_twice() -> None:
    extras = [
        related_part("header", paragraph("Same.")),
        related_part("footer", paragraph("Same.")),
    ]
    section = reference("header", "default", 1) + reference("footer", "default", 2)
    doc = parse_docx(build_docx(paragraph("Body."), extras, section=section))
    assert [(b.kind, b.text) for b in doc.blocks] == [
        ("text", "Body."),
        ("header", "Same."),
        ("footer", "Same."),
    ]


def test_tables_and_text_boxes_are_numbered_within_each_part() -> None:
    table = "<w:tbl><w:tblPr/><w:tr><w:tc><w:tcPr/>{}</w:tc></w:tr></w:tbl>"
    inner = f"<w:txbxContent>{paragraph('Boxed.')}</w:txbxContent>"
    box = f"<w:p><w:r><w:pict>{inner}</w:pict></w:r></w:p>"
    body = table.format(paragraph("Body cell.")) + box
    footer = table.format(paragraph("Footer cell.")) + box
    section = reference("footer", "default", 1)
    doc = parse_docx(build_docx(body, [related_part("footer", footer)], section=section))
    ours = [
        (b.locator["part"], b.locator.get("table"), b.locator.get("textbox")) for b in doc.blocks
    ]
    assert ours == [
        ("document", 1, None),
        ("document", None, 1),
        ("footer", 1, None),
        ("footer", None, 1),
    ]


def test_a_part_dropped_as_a_duplicate_does_not_use_up_the_text_budget() -> None:
    # Two sections name a header part of their own with the same text, so one is kept. The
    # dropped one must not count, or the footer that follows would pass the limit.
    head = "h" * 100
    extras = [
        related_part("header", paragraph(head)),
        related_part("header", paragraph(head), 2),
        related_part("footer", paragraph("f" * 100)),
    ]
    body = end_section(reference("header", "default", 1)) + paragraph("b" * (MAX_TEXT_CHARS - 210))
    final = reference("header", "default", 2) + reference("footer", "default", 3)
    doc = parse_docx(build_docx(body, extras, section=final))
    assert [b.kind for b in doc.blocks] == ["text", "header", "footer"]


def test_page_parts_come_before_notes() -> None:
    extras = [
        related_part("footnotes", f'<w:footnote w:id="1">{paragraph("Note.")}</w:footnote>'),
        related_part("header", paragraph("Head.")),
    ]
    section = reference("header", "default", 2)
    doc = parse_docx(build_docx(paragraph("Body."), extras, section=section))
    assert [(b.kind, b.text) for b in doc.blocks] == [
        ("text", "Body."),
        ("header", "Head."),
        ("footnote", "Note."),
    ]


def test_page_part_text_counts_toward_the_text_limit() -> None:
    extras = [related_part("header", paragraph("a" * MAX_TEXT_CHARS))]
    section = reference("header", "default", 1)
    data = build_docx(paragraph("Body."), extras, section=section)
    assert rejects(data) == ErrorCode.TOO_MUCH_TEXT


def test_a_note_with_no_id_is_malformed() -> None:
    notes = related_part("footnotes", f"<w:footnote>{paragraph('Note.')}</w:footnote>")
    assert rejects(build_docx(paragraph("Body."), [notes])) == ErrorCode.MALFORMED_FILE


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
        ("numbering_levels.docx", True),
        ("list_number_style.docx", True),
        ("header_footer.docx", True),
        ("notes.docx", True),
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


def test_an_external_relationship_of_a_read_type_is_not_followed() -> None:
    # The footnotes relationship points outside the package. Nothing is fetched or read, and the
    # file still parses.
    data = build_docx(paragraph("Body."), [related_part("footnotes", "")])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        rels = archive.read("word/_rels/document.xml.rels").decode()
    external = rels.replace(
        'Target="footnotes.xml"', 'Target="https://example.org/n.xml" TargetMode="External"'
    )
    assert external != rels
    package = rezip_with(data, "word/_rels/document.xml.rels", external.encode())
    assert texts(parse_docx(package)) == ["Body."]
