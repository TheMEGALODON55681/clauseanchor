"""Party nodes and `name_span` (ParserContract.md section 8, parser 1.3.0).

Every name below is invented. No test holds text from a real contract."""

from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

import pytest
from clauseanchor_core.analyzer import context_from_parsed_document

from app.parsing import assemble, parse_document, structure
from app.parsing.assemble import TextAssembler
from app.parsing.model import ParsedDocument, StructureNode
from app.parsing.schema import SCHEMA, from_json, to_json
from app.parsing.structure import build_structure
from tests.fixtures.build import NAMES, Fixtures
from tests.test_contract import as_sent, violations
from tests.test_from_json import SMOKE
from tests.test_invariants import assert_valid_nodes
from tests.test_structure import document

QUILL = "Quillfeather Works Private Limited"
MARROW = "Marrowby Holdings Limited"
THISTLE = "Thistledown Freight LLP"
CLAUSES = ("1. Term of the agreement.", "2. Fees and payment.")


def parse(*items: str | tuple) -> tuple[ParsedDocument, list[StructureNode]]:
    doc = document(*items)
    nodes, _ = build_structure(doc.source_text, doc.blocks)
    assert_valid_nodes(doc, nodes)
    return doc, [n for n in nodes if n.kind == "party"]


def names(doc: ParsedDocument, parties: list[StructureNode]) -> list[str | None]:
    return [
        doc.source_text[p.name_span.start : p.name_span.end] if p.name_span else None
        for p in parties
    ]


# The three triggers


def test_a_between_line_and_an_and_line_make_two_parties_that_end_at_the_list_boundary() -> None:
    doc, parties = parse(
        "This agreement is made on 1 May 2020",
        "BETWEEN",
        f"{QUILL}, a company incorporated under the Companies Act, 2013",
        "AND",
        f"{MARROW}, having its registered office at 4 Elm Road",
        *CLAUSES,
    )
    assert [p.text for p in parties] == [
        f"{QUILL}, a company incorporated under the Companies Act, 2013",
        f"{MARROW}, having its registered office at 4 Elm Road",
    ]
    assert names(doc, parties) == [QUILL, MARROW]


def test_a_by_and_between_sentence_splits_at_the_top_level_and() -> None:
    doc, parties = parse(
        f"This agreement is made by and between {QUILL}, a company registered in Pune"
        f" and {MARROW}, of Delhi",
        *CLAUSES,
    )
    assert [p.text for p in parties] == [
        f"{QUILL}, a company registered in Pune",
        f"{MARROW}, of Delhi",
    ]
    assert names(doc, parties) == [QUILL, MARROW]


def test_an_and_inside_brackets_or_quotes_does_not_split_the_sentence() -> None:
    doc, parties = parse(
        f'Made by and between {QUILL} (trading as "Hale and Sons") and {MARROW}.',
        *CLAUSES,
    )
    assert names(doc, parties) == [QUILL, f"{MARROW}."]


def test_an_anchor_closes_its_party_and_the_defining_phrase_is_part_of_the_range() -> None:
    doc, parties = parse(
        f'{QUILL}, a company (hereinafter referred to as the "Supplier") of the first part',
        *CLAUSES,
    )
    assert [p.text for p in parties] == [
        f'{QUILL}, a company (hereinafter referred to as the "Supplier")'
    ]
    assert names(doc, parties) == [QUILL]


def test_an_anchor_with_called_closes_a_party_like_referred_to_as() -> None:
    doc, parties = parse(
        f'{QUILL} hereinafter called "Supplier", which expression includes its heirs',
        *CLAUSES,
    )
    assert [p.text for p in parties] == [f'{QUILL} hereinafter called "Supplier"']
    assert names(doc, parties) == [QUILL]


ROLES = [
    "Party", "Contractor", "Supplier", "Vendor", "Purchaser", "Buyer", "Seller", "Client",
    "Employer", "Owner", "Lessor", "Lessee", "Licensor", "Licensee", "Consultant", "Company",
    "Bank", "Institute", "University", "Authority", "Government", "Disclosing Party",
    "Receiving Party", "First Party", "Second Party",
]  # fmt: skip


@pytest.mark.parametrize("role", ROLES)
def test_a_lone_anchor_for_a_party_role_makes_a_party(role: str) -> None:
    doc, parties = parse(f'{QUILL}, a company (hereinafter called the "{role}")', *CLAUSES)
    assert names(doc, parties) == [QUILL]


def test_a_lone_anchor_for_a_party_role_matches_in_any_case_and_without_quotes() -> None:
    _, loud = parse(f'{QUILL} (hereinafter called the "SUPPLIER")', *CLAUSES)
    _, bare = parse(f"{QUILL} (hereinafter called the Bank or SBI)", *CLAUSES)
    assert len(loud) == len(bare) == 1


def test_a_lone_anchor_with_a_bare_short_name_is_read_for_its_role_too() -> None:
    doc, parties = parse(
        f"{QUILL} hereinafter referred to as the Company, which expression includes heirs",
        *CLAUSES,
    )
    assert [p.text for p in parties] == [f"{QUILL} hereinafter referred to as"]
    assert names(doc, parties) == [QUILL]
    _, other = parse(f"{QUILL} hereinafter referred to as the Project, which is", *CLAUSES)
    assert other == []


@pytest.mark.parametrize(
    "tail",
    [
        '(hereinafter called "Widgets")',
        '(hereinafter called the "Contract Price")',
        "hereinafter called",
    ],
)
def test_a_lone_anchor_for_any_other_term_makes_no_party(tail: str) -> None:
    _, parties = parse(f"The fee is Rs 100 {tail}", *CLAUSES)
    assert parties == []


def test_a_defined_term_in_a_recital_after_the_parties_is_not_a_party() -> None:
    doc, parties = parse(
        "BETWEEN",
        f'{QUILL}, a company (hereinafter called "Supplier")',
        "AND",
        f'{MARROW}, a company (hereinafter called "Buyer")',
        'RECITAL the crates listed below (hereinafter called "the Cargo") are for sale',
        *CLAUSES,
    )
    assert names(doc, parties) == [QUILL, MARROW]


@pytest.mark.parametrize("lead", ["made between", "BETWEEN:", "By and between"])
def test_an_anchor_after_a_lead_in_word_makes_a_party_whatever_its_term(lead: str) -> None:
    doc, parties = parse(f'This deed is {lead} {QUILL} (hereinafter called "SBI")', *CLAUSES)
    assert names(doc, parties) == [QUILL]


def test_a_second_anchor_inside_the_defining_phrase_of_a_party_is_skipped() -> None:
    _, parties = parse(
        f'{QUILL} (hereinafter called "Supplier" and also hereinafter referred to as "Seller")',
        *CLAUSES,
    )
    assert len(parties) == 1


def test_the_triggers_match_in_any_case() -> None:
    doc, parties = parse(
        "Between",
        f'{QUILL} (HEREINAFTER CALLED "A")',
        "and",
        f'{MARROW} (Hereinafter Referred To As "B")',
        *CLAUSES,
    )
    assert names(doc, parties) == [QUILL, MARROW]


def test_an_anchor_inside_brackets_ends_at_the_matching_bracket() -> None:
    _, parties = parse(
        f'{QUILL} (hereinafter referred to as the "Supplier"'
        " (which expression includes its heirs)), of Pune",
        *CLAUSES,
    )
    assert parties[0].text.endswith("heirs))")


def test_two_parties_with_anchors_in_a_between_list() -> None:
    doc, parties = parse(
        "BETWEEN",
        f'{QUILL}, a company (hereinafter called "Supplier")',
        "AND",
        f'{MARROW}, a company (hereinafter called "Buyer")',
        *CLAUSES,
    )
    assert len(parties) == 2
    assert [p.parent_id for p in parties] == [None, None]
    assert [p.level for p in parties] == [1, 1]
    assert [p.label for p in parties] == [None, None]
    assert names(doc, parties) == [QUILL, MARROW]


def test_three_parties() -> None:
    doc, parties = parse(
        "BETWEEN",
        f'{QUILL}, a company (hereinafter called "First")',
        "AND",
        f'{MARROW}, a company (hereinafter called "Second")',
        "AND",
        f"{THISTLE}, having its office in Goa",
        *CLAUSES,
    )
    assert names(doc, parties) == [QUILL, MARROW, THISTLE]


def test_a_second_party_in_the_same_sentence_starts_after_the_connective() -> None:
    doc, parties = parse(
        f'By and between {QUILL} (hereinafter called "Supplier"), with an office in Pune and'
        f' {MARROW} (hereinafter called "Buyer"), with an office in Delhi.',
        *CLAUSES,
    )
    assert names(doc, parties) == [QUILL, MARROW]


# Where a name stops


@pytest.mark.parametrize(
    "tail",
    [
        ", a company",
        " (formerly Mills)",
        " a company incorporated",
        " having its office",
        " represented by its director",
        " through its partner",
        " incorporated in Goa",
        " registered in Goa",
        " residing at Pune",
        " acting by its agent",
    ],
)
def test_a_name_stops_before_each_stop_word(tail: str) -> None:
    doc, parties = parse(f'BETWEEN\n{QUILL}{tail} (hereinafter called "S")', *CLAUSES)
    assert names(doc, parties) == [QUILL]


def test_the_stop_words_match_in_any_case() -> None:
    doc, parties = parse(f'BETWEEN\n{QUILL} HAVING its office (hereinafter called "S")', *CLAUSES)
    assert names(doc, parties) == [QUILL]


def test_a_name_loses_its_surrounding_spaces_and_quotes() -> None:
    doc, parties = parse(f'BETWEEN\n  "{QUILL}" , a company (hereinafter called "S")', *CLAUSES)
    assert names(doc, parties) == [QUILL]


def test_a_numbered_party_marker_is_not_part_of_the_name() -> None:
    doc, parties = parse(
        "BETWEEN",
        f'(1) {QUILL}, a company (hereinafter called "A")',
        "AND",
        f'B. {MARROW}, a company (hereinafter called "B")',
        *CLAUSES,
    )
    assert names(doc, parties) == [QUILL, MARROW]


def test_an_initial_is_not_taken_for_a_list_marker() -> None:
    doc, parties = parse('BETWEEN\nR. K. Traders, a firm (hereinafter called "S")', *CLAUSES)
    assert names(doc, parties) == ["R. K. Traders"]


@pytest.mark.parametrize(
    "first",
    [
        "the " + QUILL,
        "X" * 151,
        ", a company incorporated in Goa",
    ],
    ids=["lowercase", "overlong", "empty"],
)
def test_a_name_that_cannot_be_isolated_is_null_and_the_node_stands_for_it(first: str) -> None:
    _, parties = parse(f'BETWEEN\n{first} (hereinafter called "S")', *CLAUSES)
    assert len(parties) == 1
    assert parties[0].name_span is None


def test_a_name_of_exactly_150_code_points_is_kept() -> None:
    long_name = "N" * 150
    doc, parties = parse(f'BETWEEN\n{long_name} (hereinafter called "S")', *CLAUSES)
    assert names(doc, parties) == [long_name]


# What gives no party


def test_a_preamble_with_no_trigger_gives_no_party_and_no_warning() -> None:
    doc = document(
        "Notice about the agreement",
        "Issued on 1 May 2020 for general information",
        *CLAUSES,
    )
    nodes, warnings = build_structure(doc.source_text, doc.blocks)
    assert [n.kind for n in nodes if n.kind == "party"] == []
    assert warnings == ()


def test_an_anchor_after_the_first_clause_is_not_read() -> None:
    _, parties = parse(*CLAUSES, f'3. Notices go to {QUILL} (hereinafter called "Supplier").')
    assert parties == []


def test_a_between_line_without_a_party_after_it_gives_nothing() -> None:
    _, parties = parse("Notes", "BETWEEN", *CLAUSES)
    assert parties == []


def test_a_document_without_a_clause_reads_only_the_first_5000_code_points() -> None:
    padding = "x " * 2600
    _, near = parse(f'BETWEEN\n{QUILL} (hereinafter called "S")', padding)
    _, far = parse(padding, f'BETWEEN\n{QUILL} (hereinafter called "S")')
    assert len(near) == 1
    assert far == []


def test_a_long_stretch_of_connectives_inside_one_bracket_is_read_in_linear_time() -> None:
    doc = document(
        "BETWEEN",
        f'{QUILL} (hereinafter called "Supplier")',
        "(" + " and" * 60000 + f' {MARROW} (hereinafter called "Buyer")',
        *CLAUSES,
    )
    started = time.perf_counter()
    build_structure(doc.source_text, doc.blocks)
    assert (
        time.perf_counter() - started < 1.5
    )  # 3 to 4 s when the bracket check re-reads the stretch


# Numbered party lists and the false clause nodes behind them


def test_a_numbered_party_list_gives_party_nodes_and_no_false_clause_nodes() -> None:
    doc = document(
        "BETWEEN",
        f'1. {QUILL}, a company (hereinafter called "Supplier")',
        f'2. {MARROW}, a company (hereinafter called "Buyer")',
        "1. Term of the agreement.",
        "2. Fees and payment.",
    )
    nodes, _ = build_structure(doc.source_text, doc.blocks)
    assert_valid_nodes(doc, nodes)
    assert [n.kind for n in nodes] == ["heading", "party", "party", "section", "section"]
    parties = [n for n in nodes if n.kind == "party"]
    assert names(doc, parties) == [QUILL, MARROW]
    clauses = [n for n in nodes if n.kind == "section"]
    assert [c.label for c in clauses] == ["1", "2"]
    assert all(c.start >= parties[-1].end for c in clauses)


def test_a_numbered_party_list_keeps_the_ids_in_order_and_the_parents_whole() -> None:
    doc = document(
        "BETWEEN",
        f'1. {QUILL} (hereinafter called "Supplier")',
        f'2. {MARROW} (hereinafter called "Buyer")',
        "1. Term of the agreement.",
        "(a) The term is one year.",
        "(b) The term may be renewed.",
        "2. Fees and payment.",
    )
    nodes, _ = build_structure(doc.source_text, doc.blocks)
    assert_valid_nodes(doc, nodes)
    assert [n.id for n in nodes] == [f"n{i:04d}" for i in range(1, len(nodes) + 1)]
    by_id = {n.id: n for n in nodes}
    letters = [n for n in nodes if n.label in ("(a)", "(b)")]
    assert [by_id[n.parent_id].label for n in letters] == ["1", "1"]


def test_a_recital_list_that_holds_no_party_keeps_its_nodes() -> None:
    doc = document(
        "BETWEEN",
        f'{QUILL} (hereinafter called "A")',
        "1. First recital text.",
        "2. Second recital text.",
        "1. Term of the agreement.",
        "2. Fees and payment.",
    )
    nodes, _ = build_structure(doc.source_text, doc.blocks)
    assert [n.label for n in nodes if n.kind == "section"] == ["1", "2", "1", "2"]
    assert [n.kind for n in nodes].count("party") == 1


# Line endings and code points


def test_crlf_line_endings_give_the_same_parties_as_lf() -> None:
    text = (
        f'BETWEEN\n{QUILL}, a company\n(hereinafter called "A")\n'
        f'AND\n{MARROW}, a company\n(hereinafter called "B")'
    )

    def parse_with(newline: str) -> ParsedDocument:
        asm = TextAssembler()
        asm.add_block([text.replace("\n", newline)], kind="text", page=None, bbox=None, locator={})
        asm.add_block(list(CLAUSES), kind="text", page=None, bbox=None, locator={})
        doc = asm.build(media_type="text/plain", page_count=None)
        nodes, _ = build_structure(doc.source_text, doc.blocks)
        return replace(doc, nodes=nodes)

    lf, crlf = parse_with("\n"), parse_with("\r\n")
    assert "\r" not in crlf.source_text
    assert lf.source_text == crlf.source_text

    def spans(d: ParsedDocument) -> list[tuple]:
        return [(n.start, n.end, n.name_span) for n in d.nodes if n.kind == "party"]

    assert spans(lf) == spans(crlf)
    assert len(spans(lf)) == 2


def test_offsets_are_code_points_when_the_name_has_non_ascii_and_astral_characters() -> None:
    name = "Ørsted Ægir Måne \U0001d504 Limited"
    doc, parties = parse(
        "\U0001f4dc Agreement \U0001f4dc",
        "BETWEEN",
        f'{name}, a company (hereinafter called "S")',
        *CLAUSES,
    )
    (party,) = parties
    assert party.start == doc.source_text.index(name)
    assert names(doc, parties) == [name]
    assert party.name_span.end - party.name_span.start == len(name)
    # The text before the party holds characters that take two UTF-16 units, so a count in
    # UTF-16 units or bytes would put the party elsewhere.
    assert len(doc.source_text[: party.start].encode("utf-16-le")) // 2 > party.start


# The shape of the result


def doc_with_parties() -> ParsedDocument:
    doc = document(
        "SERVICE AGREEMENT",
        "BETWEEN",
        f'{QUILL}, a company (hereinafter called "Supplier")',
        "AND",
        f"the {MARROW}, a company",
        *CLAUSES,
    )
    nodes, warnings = build_structure(doc.source_text, doc.blocks)
    return replace(doc, nodes=nodes, warnings=warnings)


def as_pdf(doc: ParsedDocument) -> ParsedDocument:
    """The schema allows only the two real media types."""
    return replace(doc, media_type="application/pdf", page_count=1)


def test_a_party_has_the_fields_of_section_8_and_no_other_node_has_a_name_span() -> None:
    doc = doc_with_parties()
    parties = [n for n in doc.nodes if n.kind == "party"]
    assert len(parties) == 2
    assert all(n.name_span is None for n in doc.nodes if n.kind != "party")
    assert parties[1].name_span is None  # the name starts in lower case
    for p in parties[:1]:
        assert p.start <= p.name_span.start < p.name_span.end <= p.end
        assert doc.source_text[p.start : p.end] == p.text


def test_the_json_form_has_name_span_on_party_nodes_only() -> None:
    data = as_sent(as_pdf(doc_with_parties()), text=True)
    for node in data["nodes"]:
        assert ("name_span" in node) == (node["kind"] == "party")
    spans = [n["name_span"] for n in data["nodes"] if n["kind"] == "party"]
    assert set(spans[0]) == {"start", "end"}
    assert spans[1] is None
    assert violations(data, SCHEMA) == []


def test_the_text_free_form_keeps_the_name_span_and_leaks_no_name() -> None:
    doc = as_pdf(doc_with_parties())
    data = as_sent(doc, text=False)
    party = next(n for n in data["nodes"] if n["kind"] == "party")
    assert party["label"] is None
    assert "text" not in party
    assert party["name_span"]["end"] > party["name_span"]["start"]
    assert QUILL not in json.dumps(data)
    assert violations(data, SCHEMA) == []


def test_the_json_round_trip_keeps_the_parties() -> None:
    doc = as_pdf(doc_with_parties())
    data = to_json(doc)
    assert from_json(data) == doc
    assert to_json(from_json(json.loads(json.dumps(data)))) == data


def test_the_schema_lists_the_kind_and_requires_the_key_only_on_a_party() -> None:
    node = SCHEMA["$defs"]["StructureNode"]
    assert "party" in node["properties"]["kind"]["enum"]
    assert "name_span" not in node["required"]
    assert node["if"]["properties"]["kind"] == {"const": "party"}
    assert node["then"] == {"required": ["name_span"]}
    assert node["else"] == {"properties": {"name_span": False}}


# Nothing outside the preamble moves


def test_the_parties_lie_inside_the_preamble_and_the_rest_of_the_tree_is_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc = document(
        "SERVICE AGREEMENT",
        "BETWEEN",
        f'{QUILL}, a company (hereinafter called "Supplier")',
        "AND",
        f'{MARROW}, a company (hereinafter called "Buyer")',
        "1. Term of the agreement.",
        f'(a) Terms are set by {THISTLE} (hereinafter called "Agent").',
        '2. "Fees" means the amounts in Schedule 1.',
        "SCHEDULE 1",
    )
    with_parties, _ = build_structure(doc.source_text, doc.blocks)
    monkeypatch.setattr(structure, "add_parties", lambda text, blocks, nodes: nodes)
    without, _ = build_structure(doc.source_text, doc.blocks)

    clause = next(n for n in with_parties if n.kind == "section")
    parties = [n for n in with_parties if n.kind == "party"]
    assert len(parties) == 2
    assert all(p.end <= clause.start for p in parties)

    def shape(nodes, keep):
        return [(n.kind, n.label, n.level, n.start, n.end, n.text) for n in nodes if keep(n)]

    assert shape(with_parties, lambda n: n.kind != "party") == shape(without, lambda n: True)


def without_the_party_step(
    path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ParsedDocument, ParsedDocument]:
    data = path.read_bytes()
    new = parse_document(data)
    monkeypatch.setattr(structure, "add_parties", lambda text, blocks, nodes: nodes)
    return new, parse_document(data)


def assert_only_the_nodes_differ(new: ParsedDocument, old: ParsedDocument) -> None:
    assert (new.source_text, new.text_sha256) == (old.source_text, old.text_sha256)
    assert replace(new, nodes=()) == replace(old, nodes=())

    def shapes(doc: ParsedDocument) -> set[tuple]:
        return {(n.kind, n.label, n.level, n.start, n.end) for n in doc.nodes if n.kind != "party"}

    # The step adds party nodes and may drop the false clause nodes of a numbered party list. It
    # never adds or moves any other node.
    assert shapes(new) <= shapes(old)


@pytest.mark.parametrize("name", NAMES)
def test_the_party_step_changes_no_character_of_any_fixture(
    name: str, fixtures: Fixtures, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, expected = fixtures[name]
    if expected is not None:
        pytest.skip("the fixture is refused")
    assert_only_the_nodes_differ(*without_the_party_step(path, monkeypatch))


@pytest.mark.skipif(not SMOKE, reason="the real-file smoke set is not on this machine")
@pytest.mark.parametrize("path", SMOKE, ids=[f"smoke-{i}" for i in range(len(SMOKE))])
def test_the_party_step_changes_no_character_of_a_smoke_file(
    path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_only_the_nodes_differ(*without_the_party_step(path, monkeypatch))


# The version, and the core bridge


def test_the_parser_version_is_1_3_0() -> None:
    assert assemble.PARSER_VERSION == "1.3.0"
    assert document("Some text").parser_version == "1.3.0"


def test_the_core_bridge_takes_party_nodes_unchanged() -> None:
    doc = doc_with_parties()
    context = context_from_parsed_document(doc)
    kinds = [n.kind for n in context.structure_nodes]
    assert kinds.count("party") == 2
    by_id = {n.id: n for n in context.structure_nodes}
    for node in doc.nodes:
        bridged = by_id[node.id]
        assert (bridged.parent_id, bridged.kind, bridged.start, bridged.end) == (
            node.parent_id,
            node.kind,
            node.start,
            node.end,
        )
