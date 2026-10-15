from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import replace

import pytest

from app.parsing.assemble import TextAssembler
from app.parsing.docx import parse_docx
from app.parsing.errors import WarningCode
from app.parsing.model import ParsedDocument, ParseWarning, StructureNode
from app.parsing.pdf import parse_pdf
from app.parsing.structure import build_structure
from tests.fixtures.build import build_docx, reference, related_part
from tests.test_invariants import assert_valid_nodes

LDQ = chr(0x201C)
RDQ = chr(0x201D)
ELLIPSIS = chr(0x2026)

Item = str | tuple[str, str, Mapping[str, int | str]]


def b(text: str, kind: str = "text", **locator: int | str) -> Item:
    """A block with a kind and a locator, for tests that need more than plain text."""
    return text, kind, locator


def document(*items: Item) -> ParsedDocument:
    assembler = TextAssembler()
    for item in items:
        text, kind, locator = (item, "text", {}) if isinstance(item, str) else item
        assembler.add_block(text.split("\n"), kind=kind, page=None, bbox=None, locator=locator)
    return assembler.build(media_type="text/plain", page_count=None)


def structure(*items: Item) -> tuple[list[StructureNode], list[ParseWarning]]:
    doc = document(*items)
    nodes, warnings = build_structure(doc.source_text, doc.blocks)
    assert_valid_nodes(doc, nodes)
    return list(nodes), list(warnings)


def outline(nodes: list[StructureNode]) -> list[tuple[str, str | None, int]]:
    return [(n.kind, n.label, n.level) for n in nodes]


def labels(nodes: list[StructureNode]) -> list[str | None]:
    return [n.label for n in nodes]


def parent_labels(nodes: list[StructureNode]) -> list[str | None]:
    by_id = {n.id: n for n in nodes}
    return [by_id[n.parent_id].label if n.parent_id else None for n in nodes]


def structure_of(
    name: str, fixture_bytes: dict[str, bytes]
) -> tuple[ParsedDocument, list[StructureNode], list[ParseWarning]]:
    parse = parse_docx if name.endswith(".docx") else parse_pdf
    doc = parse(fixture_bytes[name])
    nodes, warnings = build_structure(doc.source_text, doc.blocks)
    assert_valid_nodes(doc, nodes)
    return doc, list(nodes), list(warnings)


# Nesting and ranges (A20, A22)


def test_decimal_labels_nest_by_their_number_of_parts() -> None:
    nodes, warnings = structure(
        "1. Definitions",
        "1.1 In this Agreement the words have these meanings.",
        "1.1.1 A deeper limb.",
        "1.2 Another clause.",
        "2. Term",
    )
    assert outline(nodes) == [
        ("section", "1", 1),
        ("clause", "1.1", 2),
        ("subclause", "1.1.1", 3),
        ("clause", "1.2", 2),
        ("section", "2", 1),
    ]
    assert [n.parent_id for n in nodes] == [None, "n0001", "n0002", "n0001", None]
    assert warnings == []


def test_a_node_ends_where_the_next_node_at_its_level_or_above_starts() -> None:
    nodes, _ = structure("1. Definitions", "1.1 Alpha.", "More alpha.", "2. Term", "Tail.")
    assert [n.text for n in nodes] == [
        "1. Definitions\n1.1 Alpha.\nMore alpha.",
        "1.1 Alpha.\nMore alpha.",
        "2. Term\nTail.",
    ]


def test_a_node_ends_at_the_last_body_block_it_covers() -> None:
    nodes, _ = structure("1. Clause", "Body.", b("Page 1 of 1", "footer"), b("A note.", "footnote"))
    assert nodes[0].text == "1. Clause\nBody."


def test_a_node_that_spans_a_page_break_holds_the_page_furniture_between_its_blocks() -> None:
    nodes, _ = structure(
        "1. Clause",
        "Body one.",
        b("Page 1 of 2", "footer"),
        b("ACME AGREEMENT", "header"),
        "Body two.",
        "2. Next",
    )
    assert nodes[0].text == "1. Clause\nBody one.\nPage 1 of 2\nACME AGREEMENT\nBody two."


def test_blocks_that_are_not_body_text_never_start_a_node() -> None:
    nodes, _ = structure(
        b("1. Header text", "header"),
        b("2. Footer text", "footer"),
        b("3. Note text", "footnote"),
        "Plain body.",
    )
    assert nodes == []


# Letters and roman numerals (A20, A21)


def test_letters_sit_one_level_below_the_nearest_decimal_node() -> None:
    nodes, warnings = structure(
        "1.1 Intro.", "(a) First.", "(b) Second.", "1.2 Next.", "(a) Again."
    )
    assert outline(nodes) == [
        ("clause", "1.1", 2),
        ("subclause", "(a)", 3),
        ("subclause", "(b)", 3),
        ("clause", "1.2", 2),
        ("subclause", "(a)", 3),
    ]
    assert parent_labels(nodes) == [None, "1.1", "1.1", None, "1.2"]
    assert warnings == []


def test_a_letter_with_no_decimal_node_sits_below_the_nearest_open_node() -> None:
    nodes, _ = structure("ARTICLE I", "(a) First.", "(b) Second.")
    assert outline(nodes) == [
        ("heading", "ARTICLE I", 1),
        ("clause", "(a)", 2),
        ("clause", "(b)", 2),
    ]
    nodes, _ = structure("(a) First.", "(b) Second.")
    assert outline(nodes) == [("section", "(a)", 1), ("section", "(b)", 1)]


def test_i_under_b_is_a_roman_numeral_one_level_below_the_letter() -> None:
    nodes, warnings = structure("1.1 Intro.", "(a) First.", "(b) Second.", "(i) One.", "(ii) Two.")
    assert outline(nodes)[3:] == [("subclause", "(i)", 4), ("subclause", "(ii)", 4)]
    assert parent_labels(nodes)[3:] == ["(b)", "(b)"]
    assert warnings == []


def test_i_after_h_is_the_next_letter() -> None:
    letters = [f"({c}) Item." for c in "abcdefghij"]
    nodes, warnings = structure("1.1 Intro.", *letters)
    assert labels(nodes) == ["1.1", *(f"({c})" for c in "abcdefghij")]
    assert {n.level for n in nodes[1:]} == {3}
    assert warnings == []


def test_a_numeral_that_continues_both_ways_is_a_letter_with_a_warning() -> None:
    letters = [f"({c}) Item." for c in "abcdefghijklmnopqrstu"]
    nodes, warnings = structure(
        "1.1 Intro.", *letters, "(i) One.", "(ii) Two.", "(iii) Three.", "(iv) Four.", "(v) Five."
    )
    assert labels(nodes)[-2:] == ["(iv)", "(v)"]
    assert nodes[-2].level == 4
    assert nodes[-1].level == 3
    assert nodes[-1].parent_id == nodes[0].id
    assert warnings == [ParseWarning(WarningCode.NUMBERING_AMBIGUOUS)]


def test_the_ambiguity_warning_names_the_page_of_the_block() -> None:
    letters = [f"({c}) Item." for c in "abcdefghijklmnopqrstu"]
    doc = document(
        "1.1 Intro.", *letters, "(i) One.", "(ii) Two.", "(iii) Three.", "(iv) Four.", "(v) Five."
    )
    blocks = [replace(block, page=7) for block in doc.blocks]
    _, warnings = build_structure(doc.source_text, blocks)
    assert warnings == (ParseWarning(WarningCode.NUMBERING_AMBIGUOUS, 7),)


def test_doubled_letters_follow_z() -> None:
    letters = [f"({c}) Item." for c in "abcdefghijklmnopqrstuvwxyz"]
    nodes, _ = structure("1.1 Intro.", *letters, "(aa) Item.", "(bb) Item.")
    assert labels(nodes)[-2:] == ["(aa)", "(bb)"]
    assert {n.level for n in nodes[1:]} == {3}


# Acceptance (A21)


@pytest.mark.parametrize(
    "stray",
    [
        "30 days after the date of notice the Customer may end it.",
        "5. A jump from two to five.",
        "2.3 A cross reference with no section two point two before it.",
    ],
)
def test_a_number_that_does_not_continue_a_sequence_stays_body_text(stray: str) -> None:
    nodes, _ = structure("1. First.", "2. Second.", stray, "3. Third.")
    assert labels(nodes) == ["1", "2", "3"]


def test_a_block_that_is_only_a_bare_number_is_a_page_number_not_a_clause() -> None:
    # A page number printed mid-page is not marked as furniture, and it equals the next
    # clause number on the page that opens that clause. It may share its block with the line
    # printed under it.
    nodes, _ = structure(
        "1. First.", "2. Second.", "3", "3. Third.", "4\nSource: filing", "4. Fourth."
    )
    assert labels(nodes) == ["1", "2", "3", "4"]
    assert nodes[1].text == "2. Second.\n3"
    assert nodes[2].text == "3. Third.\n4\nSource: filing"
    assert nodes[3].text == "4. Fourth."


def test_a_decimal_label_has_up_to_five_parts_of_up_to_three_digits() -> None:
    nodes, _ = structure("1.1.1.1.1 Deep.")
    assert outline(nodes) == [("subclause", "1.1.1.1.1", 5)]
    assert structure("1.1.1.1.1.1 Too deep.")[0] == []
    nodes, _ = structure(b("Clause.", list_label="100."), b("Clause.", list_label="1000."))
    assert labels(nodes) == ["100"]


def test_a_doubled_letter_is_the_only_multi_letter_label() -> None:
    letters = [f"({c}) Item." for c in "abcdefghijklmnopqrstuvwxyz"]
    nodes, _ = structure("1.1 Intro.", *letters, "(ab) Not a letter.")
    assert len(nodes) == 27


def test_a_label_with_a_full_stop_and_nothing_else_is_still_a_label() -> None:
    nodes, _ = structure("1.", "Text.", "2.", "Text.")
    assert labels(nodes) == ["1", "2"]


def test_a_label_may_run_straight_into_its_title() -> None:
    nodes, _ = structure("1.Intro.", "1.1Alpha.", "2.Next.")
    assert labels(nodes) == ["1", "1.1", "2"]


def test_a_restart_inside_a_long_run_is_a_list_and_not_a_new_sequence() -> None:
    nodes, _ = structure("1. A.", "2. B.", "3. C.", "4. D.", "1. List item.", "5. E.")
    assert labels(nodes) == ["1", "2", "3", "4", "5"]
    assert nodes[3].text == "4. D.\n1. List item."


def test_a_short_numbered_party_list_does_not_take_the_clause_numbers() -> None:
    nodes, _ = structure(
        "BETWEEN",
        "1. HealthGate Inc.",
        "2. The Hospital.",
        "1. Definitions",
        "1.1 Words.",
        "2. Term",
        "3. Fees",
    )
    assert labels(nodes)[1:] == ["1", "2", "1", "1.1", "2", "3"]
    assert nodes[3].text == "1. Definitions\n1.1 Words."


def test_a_restart_replaces_a_run_of_three_but_not_a_run_of_four() -> None:
    nodes, _ = structure("1. A.", "2. B.", "3. C.", "1. D.", "2. E.")
    assert labels(nodes) == ["1", "2", "3", "1", "2"]
    nodes, _ = structure("1. A.", "2. B.", "3. C.", "4. D.", "1. E.", "2. F.")
    assert labels(nodes) == ["1", "2", "3", "4"]


def test_a_restart_that_replaced_a_short_run_can_be_replaced_in_turn() -> None:
    nodes, _ = structure("1. A.", "2. B.", "3. C.", "1. D.", "2. E.", "3. F.", "1. G.", "2. H.")
    assert labels(nodes) == ["1", "2", "3", "1", "2", "3", "1", "2"]


def test_a_decimal_must_carry_the_number_of_the_open_decimal_above_it() -> None:
    nodes, _ = structure("1. Alpha.", "1.1 Beta.", "2.1 A reference, not a clause.")
    assert labels(nodes) == ["1", "1.1"]


def test_a_deeper_decimal_may_skip_a_level_that_has_no_node() -> None:
    nodes, _ = structure("1. Alpha.", "1.1.1 Deep.")
    assert outline(nodes) == [("section", "1", 1), ("subclause", "1.1.1", 3)]


def test_letters_restart_under_each_clause_even_after_a_long_run() -> None:
    items = ["1.1 One.", "(a) A.", "(b) B.", "(c) C.", "(d) D.", "1.2 Two.", "(a) A again."]
    nodes, _ = structure(*items)
    assert labels(nodes) == ["1.1", "(a)", "(b)", "(c)", "(d)", "1.2", "(a)"]


def test_a_wrapped_cross_reference_does_not_cut_the_clause() -> None:
    nodes, _ = structure(
        "1. Payment", "1.1 Fees are due as set out in", "4.2 above.", "1.2 Late fees.", "2. Term"
    )
    assert labels(nodes) == ["1", "1.1", "1.2", "2"]
    assert nodes[1].text == "1.1 Fees are due as set out in\n4.2 above."


def test_a_sequence_may_start_with_a_subnumber_when_the_parent_is_not_a_node() -> None:
    nodes, _ = structure("ARTICLE I", "1.1 First.", "1.2 Second.", "ARTICLE II", "2.1 Third.")
    assert labels(nodes) == ["ARTICLE I", "1.1", "1.2", "ARTICLE II", "2.1"]


def test_a_sequence_survives_a_heading_between_its_members() -> None:
    nodes, _ = structure("1. First.", "1.1 Alpha.", "TERMINATION", "1.2 Beta.", "2. Second.")
    assert labels(nodes) == ["1", "1.1", None, "1.2", "2"]


@pytest.mark.parametrize(
    "entry",
    [
        "1. Fees ................ 7",
        "1. Fees ....",
        "1. Fees . . . . . . 7",
        "1. Fees 7",
        "1.\tFees\t7",
        f"1. Fees{ELLIPSIS * 2} 7",
    ],
)
def test_contents_entries_never_become_nodes(entry: str) -> None:
    # The entry is numbered 1 so that, if it were read, it would open a sequence.
    nodes, _ = structure(entry, "1. First.", "2. Second.", "3. Fees.")
    assert labels(nodes) == ["1", "2", "3"]
    assert nodes[0].text == "1. First."


def test_a_block_that_wraps_onto_a_number_is_not_a_contents_entry() -> None:
    nodes, _ = structure("1. Fees are set out in clause\n5")
    assert labels(nodes) == ["1"]


def test_a_roman_heading_followed_by_a_lower_case_word_is_running_text() -> None:
    nodes, _ = structure("I. agree that the above is true.")
    assert nodes == []


def test_a_trail_of_three_dots_is_not_a_dot_leader() -> None:
    nodes, _ = structure("1. Wait for it...", "2. Next.")
    assert labels(nodes) == ["1", "2"]


def test_a_contents_list_does_not_use_up_the_numbers() -> None:
    nodes, _ = structure(
        "1. Definitions 1", "2. Term 2", "1. Definitions", "1.1 Words.", "2. Term", "2.1 Starts."
    )
    assert labels(nodes) == ["1", "1.1", "2", "2.1"]


def test_a_numbered_line_ending_in_a_year_is_not_a_contents_entry() -> None:
    nodes, _ = structure("3.1 This Agreement is dated 5 May 2020")
    assert labels(nodes) == ["3.1"]


def test_a_heading_word_that_ends_in_its_own_number_is_not_a_contents_entry() -> None:
    nodes, _ = structure("ARTICLE 1", "1.1 First.", "SCHEDULE 1", "1. Fees.")
    assert labels(nodes) == ["ARTICLE 1", "1.1", "SCHEDULE 1", "1"]


# Headings and schedules (A20)


def test_article_and_roman_headings_are_level_one_headings() -> None:
    nodes, _ = structure("ARTICLE I", "Text.", "ARTICLE II", "Text.", "III. Roman heading", "Text.")
    assert outline(nodes) == [
        ("heading", "ARTICLE I", 1),
        ("heading", "ARTICLE II", 1),
        ("heading", "III", 1),
    ]


def test_a_numbered_section_heading_uses_its_part_count() -> None:
    nodes, _ = structure(
        "Section 2.1 Term. This Agreement starts on the date below.", "Clause 2.2 Fees."
    )
    assert outline(nodes) == [("heading", "Section 2.1", 2), ("heading", "Clause 2.2", 2)]


def test_an_all_caps_line_is_an_unnumbered_level_one_heading_that_closes_open_nodes() -> None:
    nodes, _ = structure("1. First.", "1.1 Alpha.", "SPECIAL TERMS", "Text under it.")
    assert outline(nodes) == [
        ("section", "1", 1),
        ("clause", "1.1", 2),
        ("heading", None, 1),
    ]
    assert nodes[0].text == "1. First.\n1.1 Alpha."
    assert nodes[2].text == "SPECIAL TERMS\nText under it."


@pytest.mark.parametrize(
    "line",
    [
        "A" * 81,
        "Termination and Renewal",
        "THIS AGREEMENT is made today.",
        "5. UPPER CASE BUT NUMBERED",
        "AB",
        "SERVICES AGREEMENT\nBETWEEN THE PARTIES NAMED BELOW AND THEIR SUCCESSORS IN TITLE ETC",
        "With a copy to:\nXXXXXXXXXXXXXXXX",  # redaction marks lift the share of the whole block
    ],
)
def test_a_line_that_is_not_a_short_all_caps_line_is_not_a_heading(line: str) -> None:
    nodes, _ = structure(line)
    assert [n for n in nodes if n.kind == "heading"] == []


def test_a_short_two_line_title_in_capitals_is_one_heading() -> None:
    nodes, _ = structure("MASTER SERVICES\nAGREEMENT")
    assert outline(nodes) == [("heading", None, 1)]


def test_a_wrapped_title_may_end_on_a_short_word() -> None:
    nodes, _ = structure("TERMS AND CONDITIONS\nOF")
    assert outline(nodes) == [("heading", None, 1)]


@pytest.mark.parametrize(
    ("line", "is_heading"), [("ABC de", True), ("AB cde", False), ("A" * 80, True)]
)
def test_a_heading_is_at_least_sixty_percent_capitals_and_at_most_eighty_characters(
    line: str, is_heading: bool
) -> None:
    nodes, _ = structure(line)
    assert bool(nodes) is is_heading


@pytest.mark.parametrize("line", ["INTERPRETATION ........ 4", "TERM AND TERMINATION\t7"])
def test_an_all_caps_contents_entry_is_not_a_heading(line: str) -> None:
    nodes, _ = structure(line, "Text.")
    assert nodes == []


def test_a_heading_word_with_nothing_after_it_is_still_a_heading() -> None:
    nodes, _ = structure("Section 1", "Text.", "Section 2", "Text.")
    assert labels(nodes) == ["Section 1", "Section 2"]


def test_an_article_line_is_a_heading_only_up_to_eighty_characters() -> None:
    assert labels(structure("ARTICLE 1 " + "X" * 70)[0]) == ["ARTICLE 1"]
    assert structure("ARTICLE 1 " + "X" * 71)[0] == []


def test_a_word_heading_label_holds_on_a_long_paragraph() -> None:
    nodes, _ = structure(b("The Parties agree as follows: " + "x" * 100, list_label="ARTICLE I"))
    assert outline(nodes) == [("heading", "ARTICLE I", 1)]


def test_an_all_caps_title_in_its_own_block_belongs_to_the_label_before_it() -> None:
    nodes, _ = structure(
        "ARTICLE 1",
        "Text.",
        "ARTICLE 2",
        "REGULATORY MATTERS",
        "2.1 Alpha.",
        "2.2 Beta.",
        "ARTICLE 3",
        "Text.",
    )
    assert outline(nodes) == [
        ("heading", "ARTICLE 1", 1),
        ("heading", "ARTICLE 2", 1),
        ("clause", "2.1", 2),
        ("clause", "2.2", 2),
        ("heading", "ARTICLE 3", 1),
    ]
    assert parent_labels(nodes)[2:4] == ["ARTICLE 2", "ARTICLE 2"]
    assert nodes[1].text.startswith("ARTICLE 2\nREGULATORY MATTERS\n2.1 Alpha.")


def test_a_schedule_title_in_capitals_keeps_the_schedule_open() -> None:
    nodes, _ = structure("SCHEDULE A", "MARKETING AFFILIATE", "1. Fees.", "2. Term.")
    assert outline(nodes) == [("schedule", "SCHEDULE A", 1), ("clause", "1", 2), ("clause", "2", 2)]


def test_a_bare_number_takes_a_capitals_title_too() -> None:
    nodes, _ = structure("1.", "DEFINITIONS", "1.1 Alpha.")
    assert outline(nodes) == [("section", "1", 1), ("clause", "1.1", 2)]


@pytest.mark.parametrize(
    "items",
    [
        ("ARTICLE 1", "Some body text.", "REGULATORY MATTERS"),
        ("ARTICLE 1 FEES", "PAYMENT TERMS"),
        ("ARTICLE 1", "REGULATORY MATTERS", "PAYMENT TERMS"),
    ],
)
def test_only_the_block_straight_after_a_bare_label_is_its_title(items: tuple[str, ...]) -> None:
    nodes, _ = structure(*items)
    assert outline(nodes)[-1] == ("heading", None, 1)


def test_a_schedule_numbers_from_one_even_after_a_long_run() -> None:
    nodes, _ = structure("1. A.", "2. B.", "3. C.", "4. D.", "SCHEDULE 1", "1. Fees.", "2. Term.")
    assert outline(nodes)[4:] == [
        ("schedule", "SCHEDULE 1", 1),
        ("clause", "1", 2),
        ("clause", "2", 2),
    ]


def test_a_schedule_resets_to_level_one_and_puts_decimals_one_deeper() -> None:
    nodes, _ = structure(
        "1. Services.",
        "1.1 Alpha.",
        "SCHEDULE 1",
        "1. Fees.",
        "1.1 Rate.",
        "(a) Band.",
        "SCHEDULE 2",
        "1. Other.",
    )
    assert outline(nodes) == [
        ("section", "1", 1),
        ("clause", "1.1", 2),
        ("schedule", "SCHEDULE 1", 1),
        ("clause", "1", 2),
        ("subclause", "1.1", 3),
        ("subclause", "(a)", 4),
        ("schedule", "SCHEDULE 2", 1),
        ("clause", "1", 2),
    ]
    assert parent_labels(nodes)[2:] == [None, "SCHEDULE 1", "1", "1.1", None, "SCHEDULE 2"]


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("EXHIBIT A", "EXHIBIT A"),
        ("Annexure A - Fees", "Annexure A"),
        ("APPENDIX 1", "APPENDIX 1"),
        ("Schedule I", "Schedule I"),
        ("Schedule 1. Services", "Schedule 1"),
    ],
)
def test_schedule_words_start_a_schedule_node(line: str, label: str) -> None:
    nodes, _ = structure(line, "Text.")
    assert outline(nodes) == [("schedule", label, 1)]


@pytest.mark.parametrize(
    "ids",
    [("1", "2", "3"), ("A", "B", "C"), ("I", "II", "III")],
)
def test_schedules_continue_by_number_letter_or_numeral(ids: tuple[str, ...]) -> None:
    items: list[Item] = []
    for ident in ids:
        items += [f"SCHEDULE {ident}", "Text."]
    nodes, _ = structure(*items)
    assert labels(nodes) == [f"SCHEDULE {ident}" for ident in ids]


@pytest.mark.parametrize(
    "line",
    [
        "Schedule 1 sets out the fees that are payable under this Agreement and how they change.",
        "Exhibit A sets out the services.",
        "Exhibit to this Agreement.",
        "Schedule 2 of the Agreement lists the fees.",
    ],
)
def test_a_schedule_word_in_running_text_is_not_a_schedule(line: str) -> None:
    nodes, _ = structure("1. First.", line)
    assert labels(nodes) == ["1"]


@pytest.mark.parametrize(
    "line",
    [
        "Section 3 of this Agreement applies.",
        "Clause 1.1 provides that fees are due.",
        "Section 2.1 above",
    ],
)
def test_a_section_word_in_running_text_is_not_a_heading(line: str) -> None:
    nodes, _ = structure("1. First.", line)
    assert labels(nodes) == ["1"]


def test_a_number_run_into_an_exhibit_is_not_a_schedule() -> None:
    nodes, _ = structure("Exhibit 10.2", "1. First.")
    assert labels(nodes) == ["1"]


# Definitions


@pytest.mark.parametrize(
    ("text", "term"),
    [
        ('"Affiliate" means an entity under common control.', "Affiliate"),
        ('"Affiliate" shall mean an entity under common control.', "Affiliate"),
        ('"Fees" has the meaning given in clause 5.', "Fees"),
        ('"Fees" have the meanings given in clause 5.', "Fees"),
        ('"Fees" shall have the meaning given in clause 5.', "Fees"),
        ('"Term" refers to the period of this Agreement.', "Term"),
        (f"{LDQ}Affiliate{RDQ} means an entity under common control.", "Affiliate"),
        ('This Agreement is made with ABC Ltd (the "Supplier") on that date.', "Supplier"),
        ('This Agreement is made with ABC Ltd ("Supplier") on that date.', "Supplier"),
        (f"This Agreement is made with ABC Ltd (the {LDQ}Supplier{RDQ}) on that date.", "Supplier"),
        ('"Confidential Information," means anything marked secret.', "Confidential Information"),
        ('"Fee" Means the price.', "Fee"),
        ('This Agreement is made with ABC Ltd (The "Supplier") on that date.', "Supplier"),
    ],
)
def test_definitions_span_the_quoted_term(text: str, term: str) -> None:
    doc = document(text)
    nodes, _ = build_structure(doc.source_text, doc.blocks)
    assert_valid_nodes(doc, nodes)
    assert len(nodes) == 1
    node = nodes[0]
    assert (node.kind, node.label, node.level, node.parent_id) == ("definition", term, 1, None)
    assert node.text[0] in {'"', LDQ} and node.text[-1] in {'"', RDQ, ","}
    assert doc.source_text[node.start : node.end] == node.text


def test_a_definition_is_a_leaf_one_level_below_its_container() -> None:
    nodes, _ = structure(
        "1. Definitions", '1.1 "Services" means the work.', '"Fees" means the price.', "2. Term"
    )
    assert outline(nodes) == [
        ("section", "1", 1),
        ("clause", "1.1", 2),
        ("definition", "Services", 3),
        ("definition", "Fees", 3),
        ("section", "2", 1),
    ]
    assert parent_labels(nodes) == [None, "1", "1.1", "1.1", None]


def test_a_definition_at_the_start_of_a_labelled_block_comes_after_its_container() -> None:
    nodes, _ = structure(b('"Services" means the work.', list_label="1.1"))
    assert outline(nodes) == [("clause", "1.1", 2), ("definition", "Services", 3)]


def test_two_definitions_in_one_block() -> None:
    nodes, _ = structure('"A" means one thing and "B" means another.')
    assert labels(nodes) == ["A", "B"]


@pytest.mark.parametrize(
    "text",
    [
        'The word "Services" is used in the schedule.',
        'See "Appendix A" for details.',
        '"" means nothing.',
        '" Spaced " means nothing.',
        "'Affiliate' means an entity under common control.",
    ],
)
def test_a_quoted_phrase_that_is_not_defined_is_not_a_definition(text: str) -> None:
    nodes, _ = structure(text)
    assert nodes == []


# Word numbering (A17 labels)


def test_a_list_label_names_the_node(fixture_bytes: dict[str, bytes]) -> None:
    doc, nodes, warnings = structure_of("numbering_levels.docx", fixture_bytes)
    assert outline(nodes) == [
        ("section", "1", 1),
        ("clause", "1.1", 2),
        ("clause", "1.2", 2),
        ("subclause", "(a)", 3),
        ("subclause", "(b)", 3),
        ("subclause", "(i)", 4),
        ("clause", "1.3", 2),
        ("subclause", "(a)", 3),
        ("section", "2", 1),
        ("clause", "2.1", 2),
    ]
    assert warnings == []
    assert "1.1" not in doc.source_text


def test_a_list_label_is_read_instead_of_the_text() -> None:
    nodes, _ = structure(b("2.5 typed text", list_label="1."), b("Plain.", list_label="1.1"))
    assert labels(nodes) == ["1", "1.1"]


def test_a_list_label_in_a_contents_style_line_is_still_ignored() -> None:
    nodes, _ = structure(b("Fees\t7", list_label="1."), b("Fees", list_label="1."))
    assert labels(nodes) == ["1"]
    assert nodes[0].text == "Fees"


def test_a_word_list_may_open_above_one_because_empty_paragraphs_count() -> None:
    nodes, _ = structure(
        b("Services.", list_label="2."), b("Fees.", list_label="3."), b("Rate.", list_label="3.1")
    )
    assert outline(nodes) == [("section", "2", 1), ("section", "3", 1), ("clause", "3.1", 2)]


@pytest.mark.parametrize("label", ["(c)", "2.3", "ARTICLE III", "SCHEDULE 2"])
def test_only_a_top_level_decimal_may_open_above_one(label: str) -> None:
    nodes, _ = structure(b("Text.", list_label=label))
    assert nodes == []


def test_a_word_numeral_after_a_clause_label_is_a_roman_numeral() -> None:
    nodes, _ = structure(
        b("Clause.", list_label="1.1"), b("One.", list_label="(i)"), b("Two.", list_label="(ii)")
    )
    assert labels(nodes) == ["1.1", "(i)", "(ii)"]


def test_a_list_label_that_equals_the_whole_text_is_still_a_label() -> None:
    nodes, _ = structure(b("1", list_label="1."))
    assert labels(nodes) == ["1"]


def test_a_word_label_that_jumps_inside_a_running_list_is_still_rejected() -> None:
    nodes, _ = structure(b("Services.", list_label="1."), b("Fees.", list_label="5."))
    assert labels(nodes) == ["1"]


def test_typed_numbers_still_have_to_open_at_one() -> None:
    nodes, _ = structure("2. Services.", "3. Fees.")
    assert nodes == []


def test_a_bullet_or_unreadable_label_makes_no_node() -> None:
    nodes, _ = structure(b("Item.", list_label="Step one:"), b("Item.", list_label="x"))
    assert nodes == []


# Tables


def test_a_table_is_one_leaf_node_with_its_cells(fixture_bytes: dict[str, bytes]) -> None:
    doc, nodes, _ = structure_of("tables.docx", fixture_bytes)
    assert outline(nodes) == [("table", None, 1), ("table", None, 1)]
    assert [n.text for n in nodes] == ["A1\nB1\nA2a\nA2b", "C1"]
    assert doc.source_text == "Parties\nA1\nB1\nA2a\nA2b\nBetween.\nC1"


def test_a_nested_table_has_no_node_of_its_own(fixture_bytes: dict[str, bytes]) -> None:
    doc, nodes, _ = structure_of("nested_table.docx", fixture_bytes)
    assert [(n.kind, n.start, n.end) for n in nodes] == [("table", 0, len(doc.source_text))]


def test_a_table_after_a_nested_table_still_has_its_node() -> None:
    nodes, _ = structure(
        b("A1", "table_cell", table=1, row=1, cell=1, segment=1),
        b("N1", "table_cell", table=2, row=1, cell=1, segment=1),
        b("A2", "table_cell", table=1, row=1, cell=2, segment=1),
        "Between.",
        b("C1", "table_cell", table=3, row=1, cell=1, segment=1),
    )
    assert [(n.kind, n.text) for n in nodes] == [("table", "A1\nN1\nA2"), ("table", "C1")]


def test_capitals_after_a_table_are_not_the_title_of_the_label_before_it() -> None:
    nodes, _ = structure(
        "ARTICLE 1", b("Cell.", "table_cell", table=1, row=1, cell=1, segment=1), "NOTICES"
    )
    assert outline(nodes) == [("heading", "ARTICLE 1", 1), ("table", None, 2), ("heading", None, 1)]


def test_a_table_sits_below_the_open_node_and_numbers_inside_it_are_not_read() -> None:
    nodes, _ = structure(
        "1. Fees",
        b("1.1 Not a clause", "table_cell", table=1, row=1, cell=1, segment=1),
        b("(a) Nor this", "table_cell", table=1, row=1, cell=2, segment=1),
        b("2. Nor a section", "table_cell", table=1, row=2, cell=1, segment=1),
        "2. Term",
    )
    assert outline(nodes) == [("section", "1", 1), ("table", None, 2), ("section", "2", 1)]
    assert parent_labels(nodes) == [None, "1", None]
    assert nodes[0].text.endswith("2. Nor a section")


def test_a_definition_in_a_table_cell_sits_below_the_table() -> None:
    nodes, _ = structure(
        b('"Fee" means the price.', "table_cell", table=1, row=1, cell=1, segment=1),
        b("Total", "table_cell", table=1, row=1, cell=2, segment=1),
    )
    assert outline(nodes) == [("table", None, 1), ("definition", "Fee", 2)]
    assert parent_labels(nodes) == [None, None]
    assert nodes[1].parent_id == nodes[0].id


# Order and ids


def test_ids_run_in_order_of_start_then_level() -> None:
    nodes, _ = structure("1. First.", '1.1 "Fee" means the price.', "2. Second.")
    assert [n.id for n in nodes] == ["n0001", "n0002", "n0003", "n0004"]
    assert [n.start for n in nodes] == sorted(n.start for n in nodes)


def test_a_document_with_no_structure_gives_no_nodes() -> None:
    nodes, warnings = structure("Just a paragraph of plain text.")
    assert (nodes, warnings) == ([], [])


# Real fixtures


def test_simple_pdf(fixture_bytes: dict[str, bytes]) -> None:
    _, nodes, warnings = structure_of("simple.pdf", fixture_bytes)
    assert outline(nodes) == [
        ("heading", None, 1),
        ("section", "1", 1),
        ("clause", "1.1", 2),
        ("subclause", "(a)", 3),
        ("definition", "Services", 4),
        ("subclause", "(i)", 4),
        ("section", "2", 1),
        ("clause", "2.1", 2),
    ]
    assert warnings == []


def test_simple_docx(fixture_bytes: dict[str, bytes]) -> None:
    _, nodes, warnings = structure_of("simple.docx", fixture_bytes)
    assert outline(nodes) == [
        ("heading", None, 1),
        ("section", "1", 1),
        ("clause", "1.1", 2),
        ("subclause", "(a)", 3),
        ("definition", "Services", 4),
        ("section", "2", 1),
        ("clause", "2.1", 2),
    ]
    assert warnings == []


def test_a_pdf_contents_page_makes_no_clause_nodes(fixture_bytes: dict[str, bytes]) -> None:
    _, nodes, _ = structure_of("contents.pdf", fixture_bytes)
    assert outline(nodes) == [("heading", None, 1)]


def test_a_docx_contents_list_with_tab_page_numbers_makes_no_clause_nodes(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc, nodes, _ = structure_of("contents_tab.docx", fixture_bytes)
    assert labels(nodes) == [None, "1", "1.1", "2", "2.1", "3", "3.1"]
    assert nodes[0].text == "CONTENTS\n1.\tDefinitions\t1\n2.\tTerm of Agreement\t2\n3.\tFees\t4"
    assert all(n.start >= doc.source_text.index("1. Definitions\n") for n in nodes[1:])


def test_page_furniture_stays_out_of_the_end_of_the_last_node(
    fixture_bytes: dict[str, bytes],
) -> None:
    doc, nodes, _ = structure_of("header_footer.pdf", fixture_bytes)
    assert labels(nodes) == ["1", "2", "3", "4", "5", "6"]
    assert nodes[-1].text.endswith("The party shall comply with requirement 6.")
    assert nodes[-1].end < len(doc.source_text)


def test_docx_page_parts_and_notes_stay_out_of_the_last_node() -> None:
    note = '<w:footnote w:id="1"><w:p><w:r><w:t>A note.</w:t></w:r></w:p></w:footnote>'
    extras = [
        related_part("header", "<w:p><w:r><w:t>ACME AGREEMENT</w:t></w:r></w:p>"),
        related_part("footnotes", note),
    ]
    section = reference("header", "default", 1) + '<w:pgSz w:w="12240" w:h="15840"/>'
    body = "<w:p><w:r><w:t>1. Clause</w:t></w:r></w:p><w:p><w:r><w:t>Body.</w:t></w:r></w:p>"
    doc = parse_docx(build_docx(body, extras, section=section))
    nodes, _ = build_structure(doc.source_text, doc.blocks)
    assert_valid_nodes(doc, nodes)
    assert doc.source_text == "1. Clause\nBody.\nACME AGREEMENT\nA note."
    assert [n.text for n in nodes] == ["1. Clause\nBody."]


# Limits


def test_a_large_document_is_read_in_linear_time() -> None:
    items: list[Item] = []
    for i in range(1, 4001):
        items += [f"{i}. Clause.", '(a) "Term" means x.', "(b) Next.", "(i) Deep."]
    started = time.perf_counter()
    doc = document(*items)
    nodes, _ = build_structure(doc.source_text, doc.blocks)
    assert time.perf_counter() - started < 5
    assert len(nodes) > 4000
