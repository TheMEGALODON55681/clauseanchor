"""Hand-calculated metric cases and reviewed sensitivity-boundary checks."""

from copy import deepcopy
import math
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from evaluate_cuad_baseline import (
    assert_parity, count_at_threshold, finite_json, matches, prepare_matches,
    score_predictions, sensitivity_titles, words,
)


def candidate(text, probability):
    return {"text": text, "probability": probability}


class CuadEvaluationTests(unittest.TestCase):
    def test_official_punctuation_slash_and_literal_space_behavior(self):
        self.assertEqual(words("A/B,;:."), {"a", "b"})
        self.assertEqual(words("a  b"), {"a", "", "b"})
        self.assertEqual(words("a\tb"), {"a\tb"})
        self.assertFalse(matches("a b", "a\tb"))

    def test_parties_substring_is_case_sensitive_and_category_specific(self):
        text = "ACME unrelated extra words here"
        self.assertTrue(matches("ACME", text, parties=True))
        self.assertFalse(matches("ACME", text, parties=False))
        self.assertFalse(matches("ACME", text.lower(), parties=True))
        prepared = prepare_matches({"contract__Parties": ["ACME"]},
                                   {"contract__Parties": [candidate(text, 1)]})
        self.assertEqual(count_at_threshold(prepared, .5), {"tp": 1, "fp": 0, "fn": 0})

    def test_strict_threshold_and_last_duplicate_probability(self):
        prepared = prepare_matches({"q": ["alpha"]},
                    {"q": [candidate("alpha", .9), candidate("alpha", .1),
                           candidate("beta", .5), candidate("", 1)]})
        self.assertEqual(count_at_threshold(prepared, .5), {"tp": 0, "fp": 0, "fn": 1})
        self.assertEqual(count_at_threshold(prepared, .499), {"tp": 0, "fp": 1, "fn": 1})

    def test_one_prediction_can_credit_multiple_and_duplicate_annotations(self):
        prepared = prepare_matches({"q": ["alpha", "alpha beta", "alpha"], "negative": []},
                    {"q": [candidate("alpha", .9), candidate("omega", .9)],
                     "negative": [candidate("omega", .9)]})
        # Exactly 0.5 Jaccard counts as a match; answer occurrences are not deduplicated.
        self.assertEqual(count_at_threshold(prepared, .5), {"tp": 3, "fp": 2, "fn": 0})

    def test_perfect_and_empty_predictions_have_hand_calculated_metrics(self):
        gold = {"q": ["alpha"]}
        perfect = score_predictions(gold, {"q": [candidate("alpha", 1)]})
        empty = score_predictions(gold, {"q": [candidate("", 1)]})
        self.assertEqual(perfect["metrics"], {"aupr": 1, "prec_at_80_recall": 1, "prec_at_90_recall": 1})
        self.assertEqual(empty["metrics"], {"aupr": 0, "prec_at_80_recall": 0, "prec_at_90_recall": 0})
        self.assertTrue(math.isnan(empty["precisions"][1]))
        self.assertIsNone(finite_json(empty)["precisions"][1])

    def test_original_precision_at_recall_omits_final_zero_threshold_point(self):
        result = score_predictions({"q": ["alpha"]}, {"q": [candidate("alpha", .0001)]})
        self.assertEqual(result["recalls"][-2:], [0, 1])
        self.assertEqual(result["metrics"], {"aupr": 1, "prec_at_80_recall": 0, "prec_at_90_recall": 0})

    def test_scoring_does_not_modify_annotations_or_predictions(self):
        gold = {"q": ["alpha beta", "alpha"]}
        predictions = {"q": [candidate("alpha", .8), candidate("", .2)]}
        before = deepcopy((gold, predictions))
        result = score_predictions(gold, predictions)
        self.assertEqual((gold, predictions), before)
        self.assertEqual(len(result["thresholds"]), 101)
        self.assertEqual(len(result["precisions"]), 102)

    def test_missing_or_extra_prediction_question_is_rejected(self):
        for predictions in ({}, {"q": [], "foreign": []}):
            with self.subTest(predictions=predictions), self.assertRaisesRegex(ValueError, "question IDs"):
                score_predictions({"q": ["alpha"]}, predictions)

    def test_correct_no_answer_does_not_inflate_true_positive_count(self):
        result = score_predictions({"negative": []}, {"negative": [candidate("", 1)]})
        self.assertTrue(all(c == {"tp": 0, "fp": 0, "fn": 0} for c in result["counts"]))
        self.assertEqual(result["metrics"], {"aupr": 0, "prec_at_80_recall": 0, "prec_at_90_recall": 0})

    def test_sensitivity_excludes_only_confirmed_cross_split_families(self):
        groups = [{"group_id": gid, "official_split": split,
                   "source_documents": [{"title": title} for title in titles]}
                  for gid, split, titles in (("tr0", "train", ["train0"]), ("tr1", "train", ["train1"]),
                                            ("known", "test", ["known-a", "known-b"]),
                                            ("test0", "test", ["test0"]), ("test1", "test", ["test1"]),
                                            ("unresolved", "test", ["unresolved"]))]
        families = [{"group_ids": ["tr0", "tr1", "known"]}, {"group_ids": ["test0", "test1"]}]
        before = deepcopy((groups, families))
        kept, excluded = sensitivity_titles(groups, families)
        self.assertEqual(kept, ["test0", "test1", "unresolved"])
        self.assertEqual(excluded, ["known-a", "known-b"])
        self.assertEqual((groups, families), before)

    def test_unknown_or_reused_family_members_are_rejected(self):
        groups = [{"group_id": g, "official_split": "test", "source_documents": [{"title": g}]}
                  for g in ("a", "b", "c")]
        for families in ([{"group_ids": ["a", "unknown"]}],
                         [{"group_ids": ["a", "b"]}, {"group_ids": ["b", "c"]}]):
            with self.subTest(families=families), self.assertRaisesRegex(ValueError, "family membership"):
                sensitivity_titles(groups, families)

    def test_parity_checks_curves_and_nan_states_as_well_as_summary_metrics(self):
        local = score_predictions({"q": ["alpha"]}, {"q": [candidate("alpha", 1)]})
        self.assertEqual(assert_parity(local, deepcopy(local)), 0)
        changed = deepcopy(local)
        changed["precisions"][5] = .9
        with self.assertRaisesRegex(ValueError, "parity failed"):
            assert_parity(local, changed)
        changed = deepcopy(local)
        changed["recalls"][1] = math.nan
        with self.assertRaisesRegex(ValueError, "finite/NaN"):
            assert_parity(local, changed)


if __name__ == "__main__":
    unittest.main()
