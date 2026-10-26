"""Whole-score ties, assignment changes, document uncertainty and saved-run replay."""

from collections import defaultdict
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import canonical_sha256, read_json
from cuad_checkpoints import replace_json
from cuad_development import aggregate, match_counts
from run_cuad_baseline import atomic_json
import diagnose_cuad_scores as diagnostic
import validate_cuad_decoder as validation
from test_cuad_decoder_validation import FixedModel, fixture


def candidate(a, b, score):
    return {"start": a, "end": b, "margin": score}


def task(qid, group, category, gold):
    return {"question_id": qid, "group_id": group, "category_id": category,
            "gold": [{"start": a, "end": b} for a, b in gold]}


def example():
    tasks = [task("q1", "d1", "a", [(0, 20), (30, 40)]), task("q2", "d1", "b", []),
             task("q3", "d2", "a", [(0, 10)]), task("q4", "d3", "b", [(0, 10)])]
    pools = [[candidate(0, 10, 5), candidate(0, 20, 3), candidate(30, 40, 2)],
             [candidate(50, 60, 5)], [candidate(0, 10, 4)], []]
    return tasks, pools


class CurveTests(unittest.TestCase):
    def test_sweep_matches_brute_force_rescoring_at_every_global_cutoff(self):
        tasks, pools = example()
        curves = diagnostic.score_curves(tasks, pools)
        self.assertEqual([p["minimum_margin"] for p in curves["global"]], [None, 5., 4., 3., 2.])
        for point in curves["global"]:
            cutoff = point["minimum_margin"]
            rows = [{"category_id": t["category_id"], "result": match_counts(
                [] if cutoff is None else [c for c in values if c["margin"] >= cutoff], t["gold"])}
                    for t, values in zip(tasks, pools)]
            expected = aggregate(rows, "result")
            self.assertEqual(point["micro"], expected["micro"])
            self.assertEqual(point["macro_f1"], expected["macro_f1"])

    def test_score_ties_are_included_together_across_questions(self):
        tasks = [task("a", "d1", "a", [(0, 10)]), task("b", "d2", "a", [])]
        pools = [[candidate(0, 10, 4)], [candidate(20, 30, 4)]]
        curve = diagnostic.score_curves(tasks, pools)["global"]
        self.assertEqual(len(curve), 2)
        self.assertEqual(curve[-1]["micro"]["precision"], .5)
        self.assertIsNone(diagnostic.target_point(curve, 90))

    def test_score_ties_within_one_question_do_not_offer_a_partial_prefix(self):
        tasks = [task("q", "d", "a", [(0, 10)])]
        pools = [[candidate(0, 10, 2), candidate(20, 30, 2)]]
        curve = diagnostic.score_curves(tasks, pools)["global"]
        self.assertEqual(len(curve), 2)
        self.assertEqual(curve[-1]["micro"]["predicted"], 2)

    def test_matching_is_recomputed_instead_of_filtering_frozen_match_labels(self):
        tasks = [task("q", "d", "a", [(0, 20)])]
        pools = [[candidate(0, 10, 3), candidate(0, 20, 2)]]
        curve = diagnostic.score_curves(tasks, pools)["global"]
        # At full output the exact lower-scored span wins the assignment.
        # Once it is filtered out the higher-scored partial span becomes a TP.
        self.assertEqual(curve[1]["micro"]["tp"], 1)
        self.assertEqual(curve[1]["micro"]["exact_matches"], 0)
        self.assertEqual(curve[2]["micro"]["tp"], 1)
        self.assertEqual(curve[2]["micro"]["exact_matches"], 1)

    def test_empty_output_never_satisfies_a_precision_target(self):
        curves = diagnostic.score_curves([task("q", "d", "a", [(0, 10)])], [[]])
        point = curves["global"][0]
        self.assertIsNone(point["micro"]["precision"])
        self.assertEqual(point["micro"]["recall"], 0)
        self.assertIsNone(diagnostic.target_point(curves["global"], 95))

    def test_target_selects_highest_recall_including_exact_target_boundary(self):
        tasks = [task(str(i), str(i), "a", [(0, 10)] if i < 9 else []) for i in range(10)]
        pools = [[candidate(0, 10, 10 - i)] for i in range(10)]
        curve = diagnostic.score_curves(tasks, pools)["global"]
        # The 90%-precise endpoint has no extra recall: the earlier perfect
        # point wins the declared precision tiebreak. A 90% point is eligible.
        self.assertEqual(diagnostic.target_point(curve, 90)["micro"]["predicted"], 9)
        self.assertIsNotNone(diagnostic.target_point([curve[-1]], 90))
        self.assertIsNone(diagnostic.target_point([curve[-1]], 95))

    def test_target_handles_nonmonotonic_precision_without_interpolation(self):
        tasks = [task(str(i), str(i), "a", [(0, 10)] if i in (0, 2, 3) else []) for i in range(4)]
        pools = [[candidate(0, 10, 4 - i)] for i in range(4)]
        curve = diagnostic.score_curves(tasks, pools)["global"]
        self.assertEqual(diagnostic.target_point(curve, 75)["micro"]["tp"], 3)
        self.assertEqual(diagnostic.target_point(curve, 90)["micro"]["tp"], 1)

    def test_missing_candidate_gold_remains_in_every_recall_denominator(self):
        tasks = [task("q", "d", "a", [(0, 10), (1000, 2000)])]
        curve = diagnostic.score_curves(tasks, [[candidate(0, 10, 1)]])["global"]
        self.assertTrue(all(p["micro"]["gold"] == 2 for p in curve))
        self.assertEqual(diagnostic.target_point(curve, 95)["micro"]["recall"], .5)

    def test_category_curves_keep_absent_questions_and_unsupported_categories(self):
        tasks = [task("q1", "d1", "absent", []), task("q2", "d2", "present", [(0, 10)]),
                 task("q3", "d3", "present", [])]
        pools = [[candidate(0, 10, 3)], [candidate(0, 10, 2)], [candidate(20, 30, 1)]]
        curves = diagnostic.score_curves(tasks, pools)
        self.assertIsNone(curves["by_category"]["absent"][-1]["micro"]["recall"])
        c = curves["by_category"]["present"][-1]
        self.assertEqual(c["micro"]["questions"], 2)
        self.assertEqual(c["micro"]["precision"], .5)
        self.assertIsNone(diagnostic.target_point(curves["by_category"]["absent"], 90))

    def test_inputs_are_preserved(self):
        tasks, pools = example()
        before = deepcopy((tasks, pools))
        diagnostic.score_curves(tasks, pools)
        self.assertEqual((tasks, pools), before)

    def test_invalid_pool_order_scores_or_coverage_fail(self):
        tasks = [task("q", "d", "a", [(0, 10)])]
        for pools in ([], [[candidate(0, 10, 0)]], [[candidate(0, 10, float("nan"))]],
                      [[candidate(0, 10, 1), candidate(20, 30, 2)]]):
            with self.subTest(pools=pools), self.assertRaises(ValueError):
                diagnostic.score_curves(tasks, pools)

    def test_randomized_curves_equal_independent_full_rescoring(self):
        rng = np.random.default_rng(12)
        for repeat in range(12):
            tasks, pools = [], []
            for i in range(6):
                gold = [(int(a), int(a + length)) for a, length in zip(rng.integers(0, 30, 3), rng.integers(2, 20, 3))]
                tasks.append(task(str(i), str(i // 2), str(i % 2), gold if i % 3 else []))
                values = [candidate(int(a), int(a + length), int(score)) for a, length, score in
                          zip(rng.integers(0, 30, 8), rng.integers(2, 20, 8), rng.integers(1, 7, 8))]
                pools.append(sorted(values, key=lambda c: -c["margin"]))
            curves = diagnostic.score_curves(tasks, pools)
            for point in curves["global"]:
                rows = [{"category_id": t["category_id"], "result": match_counts(
                    [c for c in values if point["minimum_margin"] is not None and c["margin"] >= point["minimum_margin"]], t["gold"])}
                        for t, values in zip(tasks, pools)]
                self.assertEqual(point["micro"], aggregate(rows, "result")["micro"], repeat)


class DocumentTests(unittest.TestCase):
    def test_strata_and_document_burden_use_documents_not_questions(self):
        tasks, pools = example()
        result = diagnostic.detailed_point(tasks, pools, 0.)
        self.assertEqual(len(result["per_document"]), 3)
        self.assertEqual(result["document_distributions"]["false_highlights"]["mean"], 2 / 3)
        self.assertEqual(result["document_distributions"]["false_highlights"]["max"], 2)
        self.assertEqual(result["strata"]["multiple_gold"]["micro"]["gold"], 2)
        self.assertEqual(result["strata"]["no_gold"]["micro"]["fp"], 1)
        self.assertEqual(result["positive_questions_without_predictions"], 1)
        self.assertEqual(result["documents_with_predictions"], 2)

    def test_bootstrap_resamples_whole_document_totals_and_is_reproducible(self):
        documents = [{"tp": 2, "predicted": 4, "gold": 5, "fp": 2},
                     {"tp": 8, "predicted": 10, "gold": 10, "fp": 2}]
        first = diagnostic.bootstrap_documents(documents, 1000, 7)
        self.assertEqual(first, diagnostic.bootstrap_documents(documents, 1000, 7))
        p = first["intervals"]["precision"]
        self.assertEqual((p["lower"], p["upper"]), (.5, .8))
        self.assertEqual(first["intervals"]["false_highlights_per_document"]["lower"], 2.)
        self.assertFalse(first["selection_bias_corrected"])

    def test_bootstrap_counts_undefined_precision_replicates(self):
        documents = [{"tp": 1, "predicted": 1, "gold": 1, "fp": 0},
                     {"tp": 0, "predicted": 0, "gold": 1, "fp": 0}]
        precision = diagnostic.bootstrap_documents(documents, 200, 5)["intervals"]["precision"]
        self.assertGreater(precision["undefined_replicates"], 0)
        self.assertEqual(precision["undefined_replicates"] + precision["valid_replicates"], 200)

    def test_one_document_does_not_get_a_spurious_confidence_interval(self):
        result = diagnostic.bootstrap_documents([{"tp": 1, "predicted": 1, "gold": 1, "fp": 0}])
        self.assertEqual(result["status"], "insufficient_documents")
        self.assertIsNone(result["intervals"])

    def test_empty_predictions_have_no_precision_interval(self):
        result = diagnostic.bootstrap_documents([{"tp": 0, "predicted": 0, "gold": 1, "fp": 0}] * 3)
        self.assertIsNone(result["intervals"]["precision"]["lower"])
        self.assertEqual(result["intervals"]["recall"]["upper"], 0.)


class SavedRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.f = fixture(self.repo)
        self.root = self.repo / diagnostic.BASE / "decoder_validation_v1"
        (self.root / "questions").mkdir(parents=True)
        scripts = self.repo / "ml/scripts"
        scripts.mkdir(parents=True)
        for name in ("validate_cuad_decoder.py", "review_cuad_decoder.py", "cuad_development.py", "prepare_cuad_features.py",
                     "cuad_checkpoints.py", "diagnose_cuad_scores.py"):
            (scripts / name).write_bytes((SCRIPTS / name).read_bytes())
        self.checkpoint = {"fixture_checkpoint_binding": True}
        self.identity = {"policy": validation.POLICY, "checkpoint": self.checkpoint, "features": self.f.binding,
                         "code_sha256": {p.name: diagnostic.code_sha(p) for p in scripts.glob("*.py") if p.name != "diagnose_cuad_scores.py"}}
        self.run_sha = canonical_sha256(self.identity)
        atomic_json(self.root / "identity.json", self.identity)
        import torch
        producer = lambda t: validation.infer_question(FixedModel(), t, self.f.arrays, torch.device("cpu"), 2)
        with redirect_stdout(StringIO()):
            rows, hashes = validation.process_questions(self.root, self.f.tasks, self.run_sha, producer, self.f.evaluation, None)
        self.report = validation.aggregate_results(self.f.tasks, rows, self.f.evaluation)
        self.report.update(validation_run_sha256=self.run_sha, question_record_sha256=hashes)
        atomic_json(self.root / "report.json", self.report)

    def load(self):
        with redirect_stdout(StringIO()):
            return diagnostic.load_pools(self.root, self.f.tasks, self.run_sha, self.f.evaluation, self.report)

    def test_recorded_code_must_match_but_new_diagnostic_script_is_allowed(self):
        self.assertEqual(diagnostic.verify_validation_identity(self.repo, self.identity, self.report,
                                                               self.checkpoint, self.f.binding), self.run_sha)
        path = self.repo / "ml/scripts/cuad_development.py"
        path.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "producer changed"):
            diagnostic.verify_validation_identity(self.repo, self.identity, self.report, self.checkpoint, self.f.binding)

    def test_wrong_feature_checkpoint_policy_or_report_identity_rejected(self):
        for mode in ("feature", "checkpoint", "policy", "digest", "adopted"):
            identity, report = deepcopy(self.identity), deepcopy(self.report)
            if mode == "feature": identity["features"] = {}
            elif mode == "checkpoint": identity["checkpoint"] = {}
            elif mode == "policy": identity["policy"] = {}
            elif mode == "digest": report["validation_run_sha256"] = "wrong"
            else: report["decoder_adopted"] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                diagnostic.verify_validation_identity(self.repo, identity, report, self.checkpoint, self.f.binding)

    def test_complete_report_reproduces_and_score_pool_baselines_match(self):
        pools = self.load()
        with redirect_stdout(StringIO()):
            summary, curves = diagnostic.diagnose(self.f.tasks, pools, self.report)
        for name in diagnostic.VARIANTS:
            self.assertEqual(summary[name]["baseline"]["metrics"], self.report["variants"][name]["metrics"])
            self.assertEqual(curves[name]["global"][-1]["micro"], self.report["variants"][name]["metrics"]["micro"])
            for target in summary[name]["targets"].values():
                self.assertFalse(target["production_threshold_selected"])

    def test_missing_or_foreign_records_stop_before_curve_generation(self):
        path = self.root / "questions/000001.json"
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.load()
        path.write_bytes(original)
        atomic_json(self.root / "questions/999999.json", {})
        with self.assertRaisesRegex(ValueError, "foreign"):
            self.load()

    def test_resealed_candidate_change_is_rejected_by_completed_report_digest(self):
        path = self.root / "questions/000000.json"
        record = read_json(path)
        record["payload"]["candidates"][0][2] += 1
        record["payload_sha256"] = canonical_sha256(record["payload"])
        replace_json(path, record)
        with self.assertRaisesRegex(ValueError, "digest differs"):
            self.load()

    def test_changed_metrics_in_completed_report_are_rejected(self):
        self.report["variants"]["disjoint_full"]["metrics"]["micro"]["tp"] += 1
        with self.assertRaisesRegex(ValueError, "did not reproduce"):
            self.load()

    def test_nonzero_original_replay_differences_are_rejected(self):
        # Build a self-consistent report of score drift to ensure the final
        # replay guard rejects it, rather than only checking report equality.
        self.f.evaluation["predictions"][0]["candidates"][0]["margin"] += 1
        with redirect_stdout(StringIO()):
            rows, hashes = validation.process_questions(self.root, self.f.tasks, self.run_sha,
                lambda t: self.fail("must not infer"), self.f.evaluation, None)
        self.report = validation.aggregate_results(self.f.tasks, rows, self.f.evaluation)
        self.report.update(validation_run_sha256=self.run_sha, question_record_sha256=hashes)
        with self.assertRaisesRegex(ValueError, "Original decoder replay differs"):
            self.load()

    def runner_patches(self, stack):
        stack.enter_context(patch.object(diagnostic, "load_checkpoint_reports", return_value=(self.f.evaluation, self.f.progress, self.checkpoint)))
        stack.enter_context(patch.object(validation, "verify_inputs", return_value=(self.f.tasks, self.f.binding)))
        stack.enter_context(patch.object(diagnostic, "runtime_versions", return_value={"fixture": True}))
        stack.enter_context(patch.object(diagnostic, "verify_ignored_assets"))
        stack.enter_context(patch.object(validation, "infer_question", side_effect=AssertionError("must not infer")))
        stack.enter_context(patch.object(validation, "load_model", side_effect=AssertionError("must not load weights")))
        stack.enter_context(patch("torch.load", side_effect=AssertionError("must not deserialize weights")))

    def test_end_to_end_report_is_reusable_without_inference_and_inputs_preserved(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with ExitStack() as stack, redirect_stdout(StringIO()):
            self.runner_patches(stack)
            first = diagnostic.run(self.repo)
            second = diagnostic.run(self.repo)
        self.assertEqual(first, second)
        output = self.repo / diagnostic.BASE / "score_diagnostic_v1"
        self.assertEqual(first["curves_sha256"], canonical_sha256(read_json(output / "curves.json")))
        for key in ("model_inference_performed", "training_performed", "calibration_performed", "operating_policy_selected", "decoder_adopted", "official_test_evaluated"):
            self.assertFalse(first[key])
        for relative, contents in before.items():
            self.assertEqual((self.root / relative).read_bytes(), contents)

    def test_differing_output_is_preserved_on_rerun(self):
        with ExitStack() as stack, redirect_stdout(StringIO()):
            self.runner_patches(stack)
            diagnostic.run(self.repo)
            path = self.repo / diagnostic.BASE / "score_diagnostic_v1/report.json"
            path.write_bytes(b"preserve existing unfamiliar report")
            with self.assertRaisesRegex(ValueError, "Existing file differs"):
                diagnostic.run(self.repo)
            self.assertEqual(path.read_bytes(), b"preserve existing unfamiliar report")

    def test_changed_output_identity_is_rejected(self):
        output = self.repo / "output"
        output.mkdir()
        diagnostic.bind_output(output, {"one": 1})
        with self.assertRaisesRegex(ValueError, "changed"):
            diagnostic.bind_output(output, {"one": 2})

    def test_unsafe_or_overlapping_run_names_fail_before_input_reads(self):
        for kwargs in ({"run_name": "../escape"}, {"run_name": "decoder_validation_v1"}, {"training_run": "features_v1"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                diagnostic.run(self.repo, **kwargs)


if __name__ == "__main__":
    unittest.main()
