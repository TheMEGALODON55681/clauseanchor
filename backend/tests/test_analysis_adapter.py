"""The app's definitions over a core result (API.md section 10): what counts as complete and as
resolved, and the checks a result passes before the store takes it."""

from __future__ import annotations

from dataclasses import replace

import pytest
from clauseanchor_core import CategoryResult

from app.services.analysis import check_result, decisions_resolved, processing_complete
from tests.fake_core import MADE_UP_TEXT, parsed_document, real_result

IDS = ("cat.one", "cat.two")


def category(status: str, *, complete: bool = True) -> CategoryResult:
    return CategoryResult("c", status, None, None, complete, 1, 1 if complete else 2, 0)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("partial_parse", "incomplete", "expected"),
    [
        (False, frozenset(), True),
        (True, frozenset(), False),  # the parse left text out
        (False, frozenset({"cat.two"}), False),  # one search did not finish
        (True, frozenset({"cat.one", "cat.two"}), False),
    ],
)
def test_processing_is_complete_only_when_the_parse_and_every_search_were(
    partial_parse: bool, incomplete: frozenset[str], expected: bool
) -> None:
    parsed = parsed_document(partial=partial_parse)
    result = real_result(MADE_UP_TEXT, "d", IDS, incomplete=incomplete)
    assert processing_complete(parsed, result) is expected


def test_an_unavailable_category_keeps_processing_from_being_complete() -> None:
    result = real_result(MADE_UP_TEXT, "d", IDS, unavailable=frozenset({"cat.two"}))
    assert processing_complete(parsed_document(), result) is False


def test_only_an_accepted_decision_is_resolved() -> None:
    result = replace(
        real_result(MADE_UP_TEXT, "d", IDS),
        categories=[
            category("found"),
            category("absent"),
            category("abstained"),
            category("unavailable", complete=False),
        ],
    )
    assert decisions_resolved(result) == 2


def test_a_run_of_review_candidates_resolves_nothing_though_every_search_finished() -> None:
    result = real_result(MADE_UP_TEXT, "d", IDS)
    assert processing_complete(parsed_document(), result) is True
    assert decisions_resolved(result) == 0


def accepted(result):
    return check_result(
        result, parsed=parsed_document(), document_id="d", requested=IDS, mode="real"
    )


def test_a_valid_result_for_the_request_passes() -> None:
    assert accepted(real_result(MADE_UP_TEXT, "d", IDS)) is None


@pytest.mark.parametrize(
    "change",
    [
        lambda r: replace(r, doc_id="other"),
        lambda r: replace(r, mode="stub"),
        lambda r: replace(r, categories=list(reversed(r.categories))[:1]),
    ],
    ids=["doc", "mode", "categories"],
)
def test_a_result_for_another_document_mode_or_request_is_refused(change) -> None:
    with pytest.raises(ValueError):
        accepted(change(real_result(MADE_UP_TEXT, "d", IDS)))


def test_a_sample_run_wants_a_stub_result_and_a_real_run_wants_a_real_one() -> None:
    result = real_result(MADE_UP_TEXT, "d", IDS)
    with pytest.raises(ValueError):
        check_result(
            result, parsed=parsed_document(), document_id="d", requested=IDS, mode="sample"
        )
