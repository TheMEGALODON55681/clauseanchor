"""Offset decoding, maximum-overlap matching and complete development coverage."""

from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import numpy as np
import torch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from cuad_development import aggregate, deduplicate, evaluate, interval_iou, match_counts, window_candidates


def candidate(start, end, margin=1., row=0, boundary=False):
    return {"start": start, "end": end, "margin": margin, "window_row": row,
            "boundary_review": boundary, "text": "x" * (end - start)}


def window_fixture():
    context = "αβ🙂 payment due"
    start, end = np.zeros(8), np.zeros(8)
    start[3], end[4] = 8, 9
    sequences = np.array([-1, 0, -1, 1, 1, 1, -1, -1])
    offsets = np.array([[-1, -1], [-1, -1], [-1, -1], [0, 3], [4, 11], [12, 15], [-1, -1], [-1, -1]])
    return start, end, sequences, offsets, context


class DecoderTests(unittest.TestCase):
    def test_source_slice_is_unicode_code_points_and_null_margin_is_subtracted(self):
        args = window_fixture()
        args[0][0], args[1][0] = 2, 3
        result = window_candidates(*args, row=7, clipped_left=False, clipped_right=False)
        self.assertEqual((result[0]["start"], result[0]["end"]), (0, 11))
        self.assertEqual(result[0]["text"], "αβ🙂 payment")
        self.assertEqual(result[0]["margin"], 12)
        self.assertEqual(result[0]["window_row"], 7)

    def test_question_special_padding_logits_cannot_become_spans(self):
        args = window_fixture()
        args[0][1], args[1][7] = 10000, 10000
        result = window_candidates(*args, row=0, clipped_left=False, clipped_right=False)
        self.assertTrue(result)
        self.assertTrue(all(c["start_token"] in (3, 4, 5) and c["end_token"] in (3, 4, 5) for c in result))

    def test_bad_source_maps_and_nonfinite_logits_fail(self):
        for kind in ("offset", "nan"):
            args = window_fixture()
            if kind == "offset":
                args[3][4, 1] = 100
            else:
                args[0][3] = np.nan
            with self.assertRaises(ValueError):
                window_candidates(*args, row=0, clipped_left=False, clipped_right=False)

    def test_length_limit_and_candidate_beam_are_enforced(self):
        n = 300
        start, end = np.zeros(n), np.zeros(n)
        start[1], end[299] = 100, 100
        sequences = np.ones(n, dtype=np.int8)
        sequences[0] = -1
        offsets = np.column_stack([np.arange(n), np.arange(n) + 1])
        result = window_candidates(start, end, sequences, offsets, "x" * n, 0, False, False)
        self.assertLessEqual(len(result), 20)
        self.assertTrue(all(c["end_token"] - c["start_token"] + 1 <= 256 for c in result))
        self.assertFalse(any(c["start_token"] == 1 and c["end_token"] == 299 for c in result))

    def test_score_ties_are_deterministic_and_clipped_edges_are_flagged(self):
        args = window_fixture()
        args[0][:] = 0
        args[1][:] = 0
        first = window_candidates(*args, row=0, clipped_left=True, clipped_right=True)
        self.assertEqual(first, window_candidates(*args, row=0, clipped_left=True, clipped_right=True))
        self.assertEqual((first[0]["start"], first[0]["end"]), (0, 3))
        self.assertTrue(first[0]["boundary_review"])

    def test_exact_and_high_iou_duplicates_keep_best_score_without_merging_distant_spans(self):
        result = deduplicate([candidate(0, 100, 3), candidate(0, 100, 4, 1), candidate(5, 95, 2), candidate(200, 250, 1)])
        self.assertEqual([(c["start"], c["end"], c["margin"]) for c in result], [(0, 100, 4), (200, 250, 1)])

    def test_complete_exact_counterpart_resolves_boundary_review_flag(self):
        clipped = candidate(0, 50, 5, boundary=True)
        self.assertTrue(deduplicate([clipped])[0]["boundary_review"])
        result = deduplicate([clipped, candidate(0, 50, 2, row=1)])
        self.assertEqual(result[0]["margin"], 5)
        self.assertFalse(result[0]["boundary_review"])

    def test_nms_matches_simple_reference_for_overlapping_intervals(self):
        rng = np.random.default_rng(42)
        values = [candidate(int(a), int(a + b), float(m), row=i) for i, (a, b, m) in enumerate(
            zip(rng.integers(0, 500, 100), rng.integers(1, 100, 100), rng.random(100)))]
        reference = []
        for value in sorted(values, key=lambda c: -c["margin"]):
            if all(interval_iou((value["start"], value["end"]), (r["start"], r["end"])) < .8 for r in reference):
                reference.append(value)
        self.assertEqual(deduplicate(values), reference)


class MatchingTests(unittest.TestCase):
    def test_assignment_maximizes_total_overlap_instead_of_greedy_score_order(self):
        # First prediction matches both; greedily giving it gold 0 loses gold 1.
        predictions = [candidate(0, 15), candidate(0, 10)]
        gold = [{"start": 0, "end": 10}, {"start": 5, "end": 15}]
        result = match_counts(predictions, gold)
        self.assertEqual(result["tp"], 2)
        self.assertEqual(result["fp"], 0)
        self.assertEqual(result["fn"], 0)

    def test_identical_annotations_are_one_occurrence_but_distant_same_text_is_separate(self):
        gold = [{"start": 0, "end": 10}, {"start": 0, "end": 10}, {"start": 20, "end": 30}]
        result = match_counts([candidate(0, 10)], gold)
        self.assertEqual(result["original_gold_records"], 3)
        self.assertEqual(result["gold"], 2)
        self.assertEqual(result["fn"], 1)
        self.assertEqual(result["exact_matches"], 1)

    def test_long_and_uncovered_gold_remain_in_false_negative_denominator(self):
        result = match_counts([], [{"start": 0, "end": 10000}, {"start": 12000, "end": 12100}])
        self.assertEqual(result["fn"], 2)
        self.assertEqual(result["gold"], 2)

    def test_iou_boundary_and_endpoint_errors_are_reported(self):
        result = match_counts([candidate(0, 10)], [{"start": 0, "end": 20}])
        self.assertEqual(result["tp"], 1)
        self.assertEqual(result["exact_matches"], 0)
        self.assertEqual(result["end_error_sum"], 10)
        self.assertEqual(match_counts([candidate(0, 10)], [{"start": 0, "end": 21}])["tp"], 0)

    def test_undefined_precision_and_unsupported_category_f1_are_null(self):
        rows = [{"category_id": "a", "selection": match_counts([], [{"start": 0, "end": 5}])},
                {"category_id": "b", "selection": match_counts([candidate(0, 5)], [])}]
        result = aggregate(rows, "selection")
        self.assertIsNone(result["categories"]["a"]["precision"])
        self.assertEqual(result["categories"]["a"]["f1"], 0)
        self.assertIsNone(result["categories"]["b"]["f1"])
        self.assertEqual(result["macro_f1"], 0)
        self.assertEqual(result["supported_categories"], 1)

    def test_macro_f1_weights_categories_equally(self):
        perfect = match_counts([candidate(0, 10)], [{"start": 0, "end": 10}])
        missed = match_counts([], [{"start": 0, "end": 10}])
        rows = [{"category_id": "a", "selection": perfect}] * 5 + [{"category_id": "b", "selection": missed}]
        result = aggregate(rows, "selection")
        self.assertEqual(result["macro_f1"], .5)
        self.assertAlmostEqual(result["micro"]["f1"], 10 / 11)


class FixedModel(torch.nn.Module):
    def forward(self, input_ids, attention_mask):
        logits = torch.zeros_like(input_ids, dtype=torch.float32)
        logits[:, 2] = 5
        return SimpleNamespace(start_logits=logits, end_logits=logits)


class CoverageTests(unittest.TestCase):
    def fixture(self, root, windows=3):
        directory = root / "dev_select/a"
        directory.mkdir(parents=True)
        context = "x" * (windows * 10 + 5)
        source = {"group_id": "group", "official_split": "train", "paragraphs": [{"index": 0, "context": context,
                  "questions": [{"question_id": "q", "category_id": "c", "answers": [{"start": 0, "end": len(context)}]}]}]}
        (directory / "source.json").write_text(json.dumps({"source_group": source}), encoding="utf-8")
        arrays = {"input_ids": np.zeros((windows, 4), dtype=np.int32), "attention_mask": np.ones((windows, 4), dtype=np.uint8),
                  "sequence_ids": np.tile([-1, 0, 1, -1], (windows, 1)).astype(np.int8),
                  "offsets": np.full((windows, 4, 2), -1, dtype=np.int32), "question_ranges": np.array([[0, windows]], dtype=np.int32)}
        for i in range(windows):
            arrays["offsets"][i, 2] = [i * 10, i * 10 + 5]
        for name, value in arrays.items():
            np.save(directory / (name + ".npy"), value, allow_pickle=False)
        manifest = {"partitions": {"dev_select": [{"path": "dev_select/a", "summary": {"questions": 1, "windows": windows}}],
                                   "dev_cal": [{"path": "MUST_NOT_BE_READ"}], "dev_policy": [{"path": "MUST_NOT_BE_READ"}]}}
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    def test_all_windows_and_original_gold_are_scored_without_reading_other_partitions(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            report = evaluate(FixedModel(), root, torch.device("cpu"), batch_size=2)
            self.assertEqual(report["windows"], 3)
            self.assertEqual(report["questions"], 1)
            self.assertTrue(report["selection_eligible"])
            self.assertEqual(report["selection"]["micro"]["gold"], 1)
            self.assertEqual(report["selection"]["micro"]["fn"], 1)
            self.assertEqual(report["predictions"][0]["uncapped_candidate_count"], 3)

    def test_probe_covers_whole_question_but_is_never_selection_eligible(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            report = evaluate(FixedModel(), root, torch.device("cpu"), batch_size=2, probe=True)
            self.assertEqual(report["windows"], 3)
            self.assertEqual(report["status"], "probe_only")
            self.assertFalse(report["selection_eligible"])

    def test_cap_and_uncapped_recall_audit_do_not_permit_absence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, 51)
            report = evaluate(FixedModel(), root, torch.device("cpu"), batch_size=4)
            prediction = report["predictions"][0]
            self.assertEqual(len(prediction["candidates"]), 50)
            self.assertEqual(prediction["uncapped_candidate_count"], 51)
            self.assertTrue(prediction["truncated"])
            self.assertFalse(prediction["absence_allowed"])
            self.assertEqual(report["uncapped"]["micro"]["predicted"], 51)

    def test_incomplete_coverage_and_wrong_partition_are_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.fixture(root)
            manifest["partitions"]["dev_select"][0]["summary"]["windows"] = 4
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                evaluate(FixedModel(), root, torch.device("cpu"))
            manifest["partitions"]["dev_select"][0]["path"] = "dev_cal/a"
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dev_select only"):
                evaluate(FixedModel(), root, torch.device("cpu"))


if __name__ == "__main__":
    unittest.main()
