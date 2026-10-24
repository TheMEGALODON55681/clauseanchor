"""Guard smoke-run scope, full-context coverage and complete checkpoint loading."""

from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from smoke_cuad_baseline import (
    SMOKE_QID, compare_reference, select_question, validate_coverage, validate_loading,
)


class CuadSmokeTests(unittest.TestCase):
    def test_fixed_input_ignores_labels_and_preserves_complete_context(self):
        test = {"data": [{"title": "contract", "paragraphs": [{"context": "start α\nend",
            "qas": [{"id": SMOKE_QID, "question": "Name?", "answers": [{"text": "secret"}],
                     "is_impossible": False}, {"id": "later", "question": "Other?"}]}]}]}
        before = deepcopy(test)
        selected = select_question(test)
        self.assertEqual(test, before)
        paragraph = selected["data"][0]["paragraphs"][0]
        self.assertEqual(paragraph["context"], "start α\nend")
        self.assertEqual(paragraph["qas"], [{"id": SMOKE_QID, "question": "Name?"}])
        test["data"][0]["paragraphs"][0]["qas"][0]["answers"] = []
        test["data"][0]["paragraphs"][0]["qas"][0]["is_impossible"] = True
        self.assertEqual(select_question(test), selected)

    def test_changed_first_question_is_not_silently_substituted(self):
        with self.assertRaisesRegex(ValueError, "Fixed smoke question"):
            select_question({"data": [{"title": "t", "paragraphs": [{"context": "x",
                "qas": [{"id": "different", "question": "q"}]}]}]})

    def test_partial_checkpoint_loading_is_rejected(self):
        validate_loading({"missing_keys": [], "unexpected_keys": ["roberta.embeddings.position_ids"],
                          "mismatched_keys": [], "error_msgs": []})
        for key, value in (("missing_keys", ["qa_outputs.weight"]),
                           ("unexpected_keys", ["another_model.weight"]),
                           ("mismatched_keys", ["qa_outputs.bias"]), ("error_msgs", ["failed"])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_loading({key: value})

    def test_all_context_words_must_be_covered_across_windows(self):
        def window(words):
            return SimpleNamespace(input_ids=[0] * 512, attention_mask=[1] * 512,
                                   token_to_orig_map=dict(enumerate(words, 10)))
        validate_coverage([window([0, 1]), window([1, 2, 3])], 4)
        for windows in ([], [window([0, 1, 3])], [window([0, 1, 2, 3, 4])]):
            with self.subTest(windows=len(windows)), self.assertRaises(ValueError):
                validate_coverage(windows, 4)
        invalid = window([0])
        invalid.input_ids.pop()
        with self.assertRaisesRegex(ValueError, "window length"):
            validate_coverage([invalid], 1)

    def test_comparison_does_not_treat_top_match_as_full_parity(self):
        fresh = [{"text": "a", "probability": .7}, {"text": "", "probability": .3}]
        reference = [{"text": "a", "probability": .6}, {"text": "b", "probability": .4}]
        result = compare_reference(fresh, reference, "a", "a")
        self.assertTrue(result["top_prediction_matches"])
        self.assertFalse(result["ranked_candidate_texts_match"])
        self.assertIsNone(result["maximum_probability_difference_if_same_ranking"])
        self.assertFalse(result["full_test_inference_parity_verified"])
        reference[1]["text"] = ""
        result = compare_reference(fresh, reference, "a", "a")
        self.assertTrue(result["ranked_candidate_texts_match"])
        self.assertAlmostEqual(result["maximum_probability_difference_if_same_ranking"], .1)


if __name__ == "__main__":
    unittest.main()
