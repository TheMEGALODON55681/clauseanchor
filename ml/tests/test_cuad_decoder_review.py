"""Selector geometry, report/source integrity and read-only checkpoint review."""

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import canonical_sha256, read_json
from cuad_development import POLICY as ORIGINAL_POLICY, aggregate, match_counts
import cuad_checkpoints as checkpoints
import review_cuad_decoder as review
from run_cuad_baseline import atomic_json

CONTEXT = "αβ🙂_" * 40


def candidate(a, b, margin=1., boundary=False):
    return {"start": a, "end": b, "text": CONTEXT[a:b], "margin": margin,
            "null_score": 0., "window_row": 0, "start_token": 1, "end_token": 2,
            "boundary_review": boundary}


def fixture():
    groups = [{"group_id": "group", "official_split": "train", "paragraphs": [
        {"index": 0, "context": CONTEXT, "questions": []}]}]
    predictions, rows = [], []
    values = [
        ("multi", "a", [(0, 20), (40, 60)], [candidate(0, 20, 5), candidate(2, 12, 4), candidate(10, 30, 3),
                                                   candidate(40, 60, 2), candidate(70, 80, 1), candidate(80, 90, 0)]),
        ("absent", "b", [], [candidate(0, 10, 2), candidate(20, 30, -2)]),
        ("single", "a", [(0, 10)], [candidate(0, 10, 5), candidate(20, 30, -1)]),
    ]
    for qid, category, spans, candidates in values:
        gold = [{"start": a, "end": b, "text": CONTEXT[a:b]} for a, b in spans]
        groups[0]["paragraphs"][0]["questions"].append({"question_id": qid, "category_id": category,
                                                       "answers": gold, "is_impossible": not bool(gold)})
        predictions.append({"question_id": qid, "category_id": category, "group_id": "group", "paragraph_index": 0,
                            "windows": 1, "candidates": candidates, "uncapped_candidate_count": len(candidates),
                            "truncated": False, "absence_allowed": False})
        rows.append({"question_id": qid, "category_id": category,
                     "selection": match_counts([c for c in candidates if c["margin"] > 0], gold),
                     "unfiltered": match_counts(candidates, gold), "uncapped": match_counts(candidates, gold)})
    e = {"policy": deepcopy(ORIGINAL_POLICY), "status": "complete_dev_select", "selection_eligible": True,
         "calibration_performed": False, "deployment_decisions_produced": False,
         "questions": 3, "windows": 3, "predictions": predictions, "per_question": rows,
         "truncated_questions": 0, "cap_matched_gold_difference": 0}
    e.update({key: aggregate(rows, key) for key in ("selection", "unfiltered", "uncapped")})
    p = {"epoch": 3, "offset": 0, "global_step": 3, "examples_seen": 3, "bad_evaluations": 0,
         "completed": True, "epoch_loss_sum": 0., "best_checkpoint": "checkpoint-000001",
         "best_score": e["selection"]["macro_f1"], "history": []}
    for epoch in range(1, 4):
        p["history"].append({"epoch": epoch, "global_step": epoch, "mean_fit_loss": 1.,
                             "macro_f1": p["best_score"], "evaluation_sha256": canonical_sha256(e)})
    partition = {"partition": "dev_select", "intended_role": "checkpoint_and_decoder_selection", "groups": groups}
    return e, p, partition


def reseal(e, p):
    p["history"][-1]["evaluation_sha256"] = canonical_sha256(e)
    return e, p


class SelectorTests(unittest.TestCase):
    def test_all_rules_preserve_distinct_neighbouring_answers(self):
        values = [candidate(0, 10, 5), candidate(10, 20, 4), candidate(40, 60, 3)]
        for variant in ("original", "iou_0_5", "containment_0_8", "disjoint"):
            self.assertEqual(review.select_candidates(values, variant), values)

    def test_iou_suppression_includes_exact_half_boundary(self):
        values = [candidate(0, 20, 3), candidate(0, 10, 2), candidate(20, 30, 1)]
        self.assertEqual(review.select_candidates(values, "iou_0_5"), [values[0], values[2]])

    def test_containment_rejects_nested_fragment_that_iou_keeps(self):
        values = [candidate(0, 100, 3), candidate(20, 25, 2), candidate(120, 130, 1)]
        self.assertEqual(review.select_candidates(values, "iou_0_5"), values)
        self.assertEqual(review.select_candidates(values, "containment_0_8"), [values[0], values[2]])

    def test_containment_threshold_and_disjoint_rule_are_different(self):
        values = [candidate(0, 20, 3), candidate(6, 26, 2)]
        self.assertEqual(review.select_candidates(values, "containment_0_8"), values)
        self.assertEqual(review.select_candidates(values, "disjoint"), values[:1])

    def test_fixed_margin_excludes_zero_and_negative_without_gold(self):
        for variant in review.VARIANTS:
            self.assertEqual(review.select_candidates([candidate(0, 10, 0), candidate(20, 30, -1)], variant), [])

    def test_top_one_is_only_one_even_when_two_distinct_answers_exist(self):
        values = [candidate(0, 10, 5), candidate(20, 30, 4)]
        self.assertEqual(review.select_candidates(values, "top_one_diagnostic"), values[:1])

    def test_score_ties_preserve_saved_order_after_boundary_resolution(self):
        values = [candidate(20, 40, 3, True), candidate(0, 30, 3, False)]
        self.assertEqual(review.select_candidates(values, "original"), values)
        self.assertEqual(review.select_candidates(values, "disjoint"), values[:1])

    def test_selectors_do_not_mutate_inputs_or_combine_intervals(self):
        values = [candidate(0, 20, 5), candidate(10, 30, 4), candidate(50, 60, 3)]
        before = deepcopy(values)
        for variant in review.VARIANTS:
            selected = review.select_candidates(values, variant)
            self.assertTrue(all(any(c is original for original in values) for c in selected))
        self.assertEqual(values, before)

    def test_unknown_selector_fails(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            review.select_candidates([], "fit_threshold")


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.e, self.p, self.source = fixture()

    def validate(self):
        reseal(self.e, self.p)
        return review.validate_reports(self.e, self.p, self.source)

    def test_original_metrics_reproduce_and_multigold_recall_is_reported(self):
        before = deepcopy((self.e, self.p, self.source))
        result = review.review_reports(self.e, self.p, self.source)
        self.assertEqual(result["variants"]["original"]["metrics"], self.e["selection"])
        self.assertEqual(result["variants"]["top_one_diagnostic"]["strata"]["multiple_gold"]["micro"]["recall"], .5)
        self.assertEqual(result["variants"]["disjoint"]["strata"]["multiple_gold"]["micro"]["recall"], 1.)
        self.assertEqual(result["variants"]["disjoint"]["absent_questions_with_predictions"], 1)
        self.assertFalse(result["decoder_adopted"])
        self.assertFalse(result["checkpoint_selection_changed"])
        self.assertEqual((self.e, self.p, self.source), before)

    def test_corrupt_report_hash_is_rejected(self):
        self.e["windows"] += 1
        with self.assertRaisesRegex(ValueError, "checkpoint progress"):
            review.validate_reports(self.e, self.p, self.source)

    def test_calibration_partition_official_test_and_probe_are_rejected(self):
        for mode in ("partition", "official", "probe"):
            self.e, self.p, self.source = fixture()
            if mode == "partition":
                self.source["partition"] = "dev_cal"
            elif mode == "official":
                self.source["groups"][0]["official_split"] = "test"
            else:
                self.e["status"] = "probe_only"
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.validate()

    def test_wrong_text_unicode_offsets_or_category_are_rejected(self):
        for field, value in (("text", "wrong"), ("start", -1), ("start", True)):
            self.e, self.p, self.source = fixture()
            self.e["predictions"][0]["candidates"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "text/offset"):
                self.validate()
        self.e, self.p, self.source = fixture()
        self.e["predictions"][0]["category_id"] = "other"
        with self.assertRaisesRegex(ValueError, "identity differs"):
            self.validate()

    def test_duplicate_missing_or_foreign_questions_fail(self):
        for mode in ("duplicate", "missing", "foreign"):
            self.e, self.p, self.source = fixture()
            if mode == "duplicate":
                self.e["predictions"][1] = deepcopy(self.e["predictions"][0])
            elif mode == "missing":
                self.e["predictions"].pop()
            else:
                self.e["predictions"][0]["question_id"] = "unseen"
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.validate()

    def test_changed_counts_aggregate_policy_or_cap_metadata_fail(self):
        for mode in ("counts", "aggregate", "policy", "cap"):
            self.e, self.p, self.source = fixture()
            if mode == "counts":
                self.e["per_question"][0]["selection"]["fp"] += 1
            elif mode == "aggregate":
                self.e["selection"]["micro"]["tp"] += 1
            elif mode == "policy":
                self.e["policy"]["matching_iou"] = .1
            else:
                self.e["predictions"][0]["uncapped_candidate_count"] += 1
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.validate()

    def test_foreign_group_bad_gold_or_missing_source_question_fail(self):
        for mode in ("group", "gold", "missing"):
            self.e, self.p, self.source = fixture()
            if mode == "group":
                self.e["predictions"][0]["group_id"] = "foreign"
            elif mode == "gold":
                self.source["groups"][0]["paragraphs"][0]["questions"][0]["answers"][0]["text"] = "bad"
            else:
                self.source["groups"][0]["paragraphs"][0]["questions"].pop()
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.validate()

    def test_error_decomposition_uses_one_to_one_matching_and_preserves_denominator(self):
        gold = [{"start": 0, "end": 20}]
        values = [candidate(0, 20), candidate(0, 10), candidate(0, 5), candidate(30, 40)]
        self.assertEqual(review.breakdown(values, gold, 1),
                         {"additional_eligible_overlaps": 1, "partial_overlap_only": 1, "zero_overlap": 1})
        result = review.review_reports(self.e, self.p, self.source)
        self.assertTrue(all(v["metrics"]["micro"]["gold"] == 3 for v in result["variants"].values()))

    def test_uncapped_aggregate_is_not_claimed_as_rescored(self):
        result = review.review_reports(self.e, self.p, self.source)
        self.assertTrue(any("not rescored uncapped" in s for s in result["limitations"]))
        self.assertNotIn("uncapped_variant", result["variants"])
        self.assertFalse(result["operating_policy_selected"])


class CheckpointReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.root = self.repo / review.BASE / "clean_training_v1"
        self.directory = self.root / "checkpoints/checkpoint-000001"
        self.directory.mkdir(parents=True)
        self.e, self.p, self.source = fixture()
        import hashlib
        code_sha = hashlib.sha256((SCRIPTS / "cuad_development.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        self.identity = {"epoch_sizes": [1, 1, 1], "decoder_policy": ORIGINAL_POLICY,
                         "code_sha256": {"cuad_development.py": code_sha}}
        self.run_sha = canonical_sha256(self.identity)
        atomic_json(self.root / "identity.json", self.identity)
        self.write_checkpoint()

    def write_checkpoint(self):
        (self.directory / "training.pt").write_bytes(b"opaque checkpoint bytes: never deserialize in a report review")
        for name, data in (("progress.json", self.p), ("evaluation.json", self.e)):
            path = self.directory / name
            path.write_bytes((json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode())
        self.manifest = {"run_sha256": self.run_sha, "checkpoint": self.directory.name,
                         "files": {name: checkpoints.file_spec(self.directory / name)
                                   for name in ("training.pt", "progress.json", "evaluation.json")}}
        checkpoints.replace_json(self.directory / "manifest.json", self.manifest)
        checkpoints.replace_json(self.root / "latest.json", {"checkpoint": self.directory.name,
            "run_sha256": self.run_sha, "manifest_sha256": canonical_sha256(self.manifest)})

    def test_checkpoint_hashes_verified_without_deserializing_model(self):
        with patch("cuad_checkpoints.torch.load", side_effect=AssertionError("must not load model")):
            e, p, binding = review.load_checkpoint_reports(self.root)
        self.assertEqual((e, p), (self.e, self.p))
        self.assertEqual(binding["selected_checkpoint"], "checkpoint-000001")

    def test_corrupt_checkpoint_and_unfinished_training_rejected(self):
        with (self.directory / "training.pt").open("ab") as stream:
            stream.write(b"corrupted")
        with self.assertRaises(ValueError):
            review.load_checkpoint_reports(self.root)
        self.p["completed"] = False
        self.write_checkpoint()
        with self.assertRaises(ValueError):
            review.load_checkpoint_reports(self.root)

    def test_output_is_reusable_and_preserves_checkpoint_and_differing_reports(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(review, "verify_ignored_assets"), \
                patch.object(review, "load_frozen_partition", return_value=self.source) as load, redirect_stdout(StringIO()):
            first = review.run(self.repo)
            second = review.run(self.repo)
            self.assertEqual(first, second)
            self.assertTrue(all(c.args[1] == "dev_select" for c in load.call_args_list))
            report = self.repo / review.BASE / "decoder_review_v1/report.json"
            report.write_bytes(b"keep unfamiliar content")
            with self.assertRaisesRegex(ValueError, "Existing file differs"):
                review.run(self.repo)
            self.assertEqual(report.read_bytes(), b"keep unfamiliar content")
        for path, contents in before.items():
            self.assertEqual((self.root / path).read_bytes(), contents)

    def test_unsafe_or_overlapping_names_fail_before_reads(self):
        for training, output in (("../escape", "review"), ("same", "same"), ("valid", "../escape")):
            with self.subTest(training=training, output=output), self.assertRaises(ValueError):
                review.run(self.repo, training, output)


if __name__ == "__main__":
    unittest.main()
