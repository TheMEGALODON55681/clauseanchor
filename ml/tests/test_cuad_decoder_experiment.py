"""One selector, fixed exit gate, complete whole-tie curves and immutable runs."""

from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from datetime import datetime
from io import StringIO
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import experiment_cuad_decoder as experiment
from check_cuad_families import canonical_sha256, read_json
from cuad_development import aggregate, match_counts, summarize
from diagnose_cuad_scores import score_curves
from run_cuad_baseline import atomic_json
import test_cuad_score_diagnostic as saved_fixture
import validate_cuad_decoder as validation

REPO = SCRIPTS.parents[1]
POLICY = experiment.read_policy(REPO)


def candidate(source, start, end, margin, row=0, boundary=False):
    return {"start": start, "end": end, "margin": margin, "text": source[start:end],
            "window_row": row, "boundary_review": boundary, "start_token": 1,
            "end_token": 2, "null_score": 0.}


def pair():
    source = "Alpha agrees.\r\nBeta pays."
    split = len("Alpha agrees.\r\n")
    raw = [candidate(source, 0, len(source), 18), candidate(source, 0, split - 2, 17.5),
           candidate(source, split, len(source), 17.2)]
    return source, raw


def point(tp=217, fp=24, exact=199, cutoff=15., gold=935):
    counts = {"tp": tp, "fp": fp, "fn": gold - tp, "predicted": tp + fp,
              "gold": gold, "original_gold_records": gold, "exact_matches": exact,
              "start_error_sum": 0, "end_error_sum": 0}
    return {"minimum_margin": cutoff, "micro": summarize(counts)}


def summaries(candidate_tp=236, candidate_fp=24, exact=199, multi=78):
    def item(p, n):
        return {"point": p, "details": {"strata": {"multiple_gold": {"micro": {"tp": n}}}}}
    return {experiment.REFERENCE: item(point(), 78),
            experiment.CANDIDATE: item(point(candidate_tp, candidate_fp, exact), multi)}


class SelectorTests(unittest.TestCase):
    def test_config_identity_is_fixed(self):
        self.assertEqual(canonical_sha256(POLICY), experiment.CONFIG_PIN)
        self.assertEqual(POLICY["maximum_candidate_variants"], 1)
        self.assertEqual(POLICY["expected_coverage"]["gold_spans"], 935)

    def test_exact_sentence_children_replace_broad_parent(self):
        source, raw = pair()
        before = deepcopy(raw)
        selected, stats = experiment.sentence_pack(raw, source, POLICY)
        self.assertEqual(selected, raw[1:])
        self.assertEqual(stats, {"replaced_parent_spans": 1, "sentence_children_selected": 2})
        self.assertEqual(raw, before)

    def test_no_boundary_creation_or_splitting_from_parent_alone(self):
        source, raw = pair()
        selected, stats = experiment.sentence_pack(raw[:1], source, POLICY)
        self.assertEqual(selected, raw[:1])
        self.assertEqual(stats["replaced_parent_spans"], 0)

    def test_one_eligible_child_does_not_replace_parent(self):
        source, raw = pair()
        self.assertEqual(experiment.sentence_pack(raw[:2], source, POLICY)[0], raw[:1])

    def test_exact_one_point_gap_allowed_but_larger_gap_not_allowed(self):
        source, raw = pair()
        raw[1]["margin"] = raw[2]["margin"] = 17.
        self.assertEqual(len(experiment.sentence_pack(raw, source, POLICY)[0]), 2)
        raw[2]["margin"] = 16.9999
        self.assertEqual(experiment.sentence_pack(raw, source, POLICY)[0], raw[:1])

    def test_clipped_child_requires_complete_counterpart(self):
        source, raw = pair()
        raw[1]["boundary_review"] = True
        self.assertEqual(experiment.sentence_pack(raw, source, POLICY)[0], raw[:1])
        raw.append({**raw[1], "margin": 2, "window_row": 1, "boundary_review": False})
        selected, _ = experiment.sentence_pack(raw, source, POLICY)
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["margin"], 17.5)
        self.assertFalse(selected[0]["boundary_review"])

    def test_raw_scores_and_source_unicode_crlf_are_preserved(self):
        source = '  😊 Café pays ₹500.\r\n“Beta agrees!”\nTail without stop'
        units = experiment.sentence_units(source, POLICY["algorithm"]["sentence_terminal_regex"])
        self.assertEqual([source[a:b] for a, b in units], ['😊 Café pays ₹500.', '“Beta agrees!”'])
        raw = [candidate(source, units[0][0], units[-1][1], 8)]
        raw += [candidate(source, a, b, 7.5) for a, b in units]
        selected, _ = experiment.sentence_pack(raw, source, POLICY)
        self.assertEqual(selected, raw[1:])
        self.assertEqual([c["margin"] for c in selected], [7.5, 7.5])

    def test_unterminated_tail_and_punctuation_only_units_are_not_rescue_sentences(self):
        source = ". ! Alpha. Tail"
        units = experiment.sentence_units(source, POLICY["algorithm"]["sentence_terminal_regex"])
        self.assertEqual([source[a:b] for a, b in units], ["Alpha."])

    def test_repeated_wording_remains_at_distinct_offsets(self):
        source = "Alpha pays. Alpha pays."
        units = experiment.sentence_units(source, POLICY["algorithm"]["sentence_terminal_regex"])
        raw = [candidate(source, 0, len(source), 9)] + [candidate(source, a, b, 8.5) for a, b in units]
        selected, _ = experiment.sentence_pack(raw, source, POLICY)
        self.assertEqual([c["text"] for c in selected], ["Alpha pays."] * 2)
        self.assertEqual([c["start"] for c in selected], [0, 12])

    def test_overlapping_higher_scored_output_keeps_priority(self):
        source, raw = pair()
        high = candidate(source, 0, 5, 20)
        selected, stats = experiment.sentence_pack([high, *raw], source, POLICY)
        self.assertEqual(selected, [high, raw[2]])
        self.assertEqual(stats["replaced_parent_spans"], 0)

    def test_touching_intervals_survive_ordinary_disjoint_selection(self):
        source = "abcdefghij"
        raw = [candidate(source, 0, 5, 2), candidate(source, 5, 10, 1)]
        self.assertEqual(experiment.sentence_pack(raw, source, POLICY)[0], raw)

    def test_nonpositive_children_cannot_be_rescued(self):
        source, raw = pair()
        raw[0]["margin"] = .5
        raw[1]["margin"] = 0
        raw[2]["margin"] = -.1
        self.assertEqual(experiment.sentence_pack(raw, source, POLICY)[0], raw[:1])

    def test_candidate_with_wrong_source_text_is_rejected(self):
        source, raw = pair()
        raw[0]["text"] = "rewritten"
        with self.assertRaisesRegex(ValueError, "source slice"):
            experiment.sentence_pack(raw, source, POLICY)

    def test_selector_cannot_access_gold_or_category_metadata(self):
        source, raw = pair()
        class Guard(dict):
            def __getitem__(self, key):
                if key in ("gold", "category_id", "question_id", "group_id"):
                    raise AssertionError("selector used annotation/identity")
                return super().__getitem__(key)
        guarded = [Guard({**c, "gold": object(), "category_id": object()}) for c in raw]
        actual = experiment.sentence_pack(guarded, source, POLICY)[0]
        self.assertEqual([(c["start"], c["end"]) for c in actual], [(c["start"], c["end"]) for c in raw[1:]])


class GateTests(unittest.TestCase):
    def test_gate_accepts_exactly_19_additional_matches(self):
        result = experiment.gate(summaries(), POLICY, integrity=True, in_time=True)
        self.assertTrue(result["passed"])
        self.assertEqual(result["extra_matched_gold"], 19)
        self.assertFalse(result["automatic_adoption"])

    def test_each_failed_condition_retains_reference(self):
        cases = [(summaries(candidate_tp=235), True, True), (summaries(candidate_fp=25), True, True),
                 (summaries(exact=198), True, True), (summaries(multi=77), True, True),
                 (summaries(), False, True), (summaries(), True, False)]
        for values, integrity, in_time in cases:
            result = experiment.gate(values, POLICY, integrity=integrity, in_time=in_time)
            self.assertFalse(result["passed"], values)
            self.assertEqual(result["recommendation"], experiment.REFERENCE)

    def test_missing_feasible_reference_or_candidate_fails(self):
        for name in (experiment.REFERENCE, experiment.CANDIDATE):
            data = summaries()
            data[name] = {"point": None, "details": None}
            result = experiment.gate(data, POLICY, integrity=True, in_time=True)
            self.assertFalse(result["passed"])
            self.assertIsNone(result["extra_matched_gold"])

    def test_fp_budget_changes_point_even_when_precision_target_passes(self):
        rejected = point(tp=260, fp=25, cutoff=1)
        accepted = point(tp=217, fp=24, cutoff=2)
        self.assertGreaterEqual(rejected["micro"]["precision"], .9)
        self.assertEqual(experiment.choose_point([rejected, accepted], POLICY), accepted)

    def test_exact_precision_boundary_is_inclusive_and_empty_output_is_not_feasible(self):
        p = point(tp=216, fp=24)
        self.assertTrue(experiment.feasible_point(p, POLICY))
        self.assertFalse(experiment.feasible_point(point(tp=215, fp=24), POLICY))
        self.assertFalse(experiment.feasible_point(point(tp=0, fp=0), POLICY))

    def test_tie_breaks_are_fixed(self):
        values = [point(tp=200, fp=20, cutoff=2), point(tp=200, fp=10, cutoff=1),
                  point(tp=200, fp=10, cutoff=3)]
        self.assertEqual(experiment.choose_point(values, POLICY), values[2])

    def test_whole_score_tie_cannot_be_partially_selected_to_fit_budget(self):
        tasks = [{"question_id": str(i), "category_id": "cat", "group_id": str(i),
                  "gold": [{"start": 0, "end": 10}] if i < 225 else []} for i in range(250)]
        pools = [[{"start": 0, "end": 10, "margin": 2.}] for _ in tasks]
        curve = score_curves(tasks, pools)["global"]
        self.assertEqual(len(curve), 2)
        self.assertEqual(curve[1]["micro"]["precision"], .9)
        self.assertEqual(curve[1]["micro"]["fp"], 25)
        self.assertIsNone(experiment.choose_point(curve, POLICY))

    def test_curve_matches_full_rescoring_and_detail_at_each_cutoff(self):
        tasks = [{"question_id": "q1", "category_id": "a", "group_id": "d1", "gold": [{"start": 0, "end": 20}]},
                 {"question_id": "q2", "category_id": "a", "group_id": "d1", "gold": []},
                 {"question_id": "q3", "category_id": "b", "group_id": "d2", "gold": [{"start": 0, "end": 10}, {"start": 30, "end": 40}]}]
        pools = [[{"start": 0, "end": 10, "margin": 3}, {"start": 0, "end": 20, "margin": 2}],
                 [{"start": 5, "end": 10, "margin": 2}], [{"start": 0, "end": 10, "margin": 3}]]
        for p in score_curves(tasks, pools)["global"]:
            d = experiment.detail(tasks, pools, p["minimum_margin"])
            self.assertEqual(d["metrics"]["micro"], p["micro"])
            self.assertEqual(len(d["per_document"]), 2)
            self.assertEqual(d["strata"]["multiple_gold"]["micro"]["gold"], 2)

    def test_category_regressions_and_sparse_support_are_explicit(self):
        tasks = [{"question_id": "q", "group_id": "d", "category_id": "a", "gold": [{"start": 0, "end": 10}]}]
        ref = experiment.detail(tasks, [[{"start": 0, "end": 10, "margin": 2}]], 1)
        worse = experiment.detail(tasks, [[{"start": 20, "end": 30, "margin": 2}]], 1)
        result = experiment.category_comparison(tasks, {experiment.REFERENCE: {"details": ref},
            experiment.CANDIDATE: {"details": worse}, experiment.ORIGINAL: {"details": ref}})["a"]
        self.assertTrue(result["regression"])
        self.assertTrue(result["sparse_support"])
        self.assertEqual(result["candidate_minus_reference"], {"tp": -1, "fp": 1, "fn": 1, "exact_matches": -1})


class SavedExperimentTests(unittest.TestCase):
    def setUp(self):
        self.fixture = saved_fixture.SavedRunTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.repo, self.saved, self.tasks = f.repo, f.root, f.f.tasks
        scripts = self.repo / "ml/scripts"
        shutil.copyfile(SCRIPTS / "experiment_cuad_decoder.py", scripts / "experiment_cuad_decoder.py")
        self.policy = deepcopy(POLICY)
        self.policy["expected_coverage"] = {"questions": 3, "gold_spans": 3, "documents": 1, "categories": 1, "windows": 9}
        self.policy["validation_identity_sha256"] = f.run_sha
        self.policy["validation_report_sha256"] = canonical_sha256(f.report)
        self.policy["checkpoint"] = "synthetic-test-checkpoint"
        self.checkpoint = {**f.checkpoint, "selected_checkpoint": "synthetic-test-checkpoint"}
        f.identity["checkpoint"] = self.checkpoint
        # The old fixture record run SHA stays unchanged: mock only the enclosing
        # identity verifier, while real candidate payload hashes/maps are checked.
        self.time = datetime(2026, 10, 29, tzinfo=experiment.INDIA)

    def patches(self, stack):
        f = self.fixture
        stack.enter_context(patch.object(experiment, "read_policy", return_value=self.policy))
        stack.enter_context(patch.object(experiment, "load_checkpoint_reports", return_value=(f.f.evaluation, f.f.progress, self.checkpoint)))
        stack.enter_context(patch.object(validation, "verify_inputs", return_value=(f.f.tasks, f.f.binding)))
        stack.enter_context(patch.object(experiment, "runtime_versions", return_value={"test_only": True}))
        stack.enter_context(patch.object(experiment, "verify_ignored_assets"))
        stack.enter_context(patch.object(experiment, "now_ist", return_value=self.time))
        stack.enter_context(patch.object(experiment, "verify_validation_identity", return_value=f.run_sha))
        stack.enter_context(patch.object(validation, "infer_question", side_effect=AssertionError("must not infer")))
        stack.enter_context(patch.object(validation, "load_model", side_effect=AssertionError("must not load model")))
        stack.enter_context(patch("torch.load", side_effect=AssertionError("must not deserialize checkpoint")))

    def run_experiment(self):
        with ExitStack() as stack, redirect_stdout(StringIO()):
            self.patches(stack)
            return experiment.run(self.repo)

    def test_full_runner_binds_before_selection_and_reuses_results(self):
        before = {p.relative_to(self.saved): p.read_bytes() for p in self.saved.rglob("*") if p.is_file()}
        original = experiment.sentence_pack
        def check_bound(*args):
            self.assertTrue((self.repo / experiment.ROOT / "identity.json").is_file())
            return original(*args)
        with patch.object(experiment, "sentence_pack", side_effect=check_bound):
            report = self.run_experiment()
        with patch.object(experiment, "load_pools", side_effect=AssertionError("must reuse completed result")):
            self.assertEqual(self.run_experiment(), report)
        for relative, data in before.items():
            self.assertEqual((self.saved / relative).read_bytes(), data)
        self.assertEqual(set(report["variants"]), set(experiment.VARIANTS))
        for key in ("model_inference_performed", "training_performed", "calibration_performed", "operating_policy_selected", "decoder_adopted", "official_test_evaluated"):
            self.assertFalse(report[key])
        self.assertFalse(report["gate"]["passed"])

    def test_candidate_file_change_and_missing_file_fail(self):
        path = self.saved / "questions/000000.json"
        record = read_json(path)
        record["payload"]["candidates"][0][2] += .1
        record["payload_sha256"] = canonical_sha256(record["payload"])
        path.write_text(__import__("json").dumps(record))
        with self.assertRaisesRegex(ValueError, "differs from the completed"):
            self.run_experiment()
        path.unlink()
        with self.assertRaisesRegex(ValueError, "Incomplete/foreign"):
            self.run_experiment()

    def test_coverage_guard_cannot_drop_questions_or_gold(self):
        self.policy["expected_coverage"]["gold_spans"] = 2
        with self.assertRaisesRegex(ValueError, "complete dev_select coverage"):
            self.run_experiment()

    def test_altered_reference_metrics_are_rejected(self):
        report = self.fixture.report
        report["variants"][experiment.REFERENCE]["metrics"]["micro"]["tp"] += 1
        path = self.saved / "report.json"
        path.write_text(__import__("json").dumps(report))
        self.policy["validation_report_sha256"] = canonical_sha256(report)
        with self.assertRaisesRegex(ValueError, "baseline changed"):
            self.run_experiment()

    def test_changed_experiment_code_cannot_start_another_run(self):
        self.run_experiment()
        path = self.repo / "ml/scripts/experiment_cuad_decoder.py"
        path.write_text(path.read_text() + "\n# changed\n")
        with self.assertRaisesRegex(ValueError, "Existing file differs"):
            self.run_experiment()

    def test_corrupted_completed_report_is_preserved_and_rejected(self):
        self.run_experiment()
        path = self.repo / experiment.ROOT / "results/report.json"
        path.write_bytes(b"preserve changed report")
        with self.assertRaises(ValueError):
            self.run_experiment()
        self.assertEqual(path.read_bytes(), b"preserve changed report")

    def test_deadline_blocks_new_execution_but_allows_reading_completed_result(self):
        self.time = datetime(2026, 11, 1, tzinfo=experiment.INDIA)
        with self.assertRaisesRegex(ValueError, "deadline passed"):
            self.run_experiment()
        self.time = datetime(2026, 10, 31, tzinfo=experiment.INDIA)
        report = self.run_experiment()
        self.time = datetime(2026, 11, 1, tzinfo=experiment.INDIA)
        self.assertEqual(self.run_experiment(), report)

    def test_run_finishing_after_deadline_cannot_promote(self):
        with ExitStack() as stack, redirect_stdout(StringIO()):
            self.patches(stack)
            stack.enter_context(patch.object(experiment, "now_ist", side_effect=[
                datetime(2026, 10, 31, 23, 59, tzinfo=experiment.INDIA),
                datetime(2026, 11, 1, 0, 1, tzinfo=experiment.INDIA)]))
            result = experiment.run(self.repo)
        self.assertFalse(result["gate"]["checks"]["completed_by_deadline"])
        self.assertEqual(result["gate"]["recommendation"], experiment.REFERENCE)

    def test_config_tweak_is_rejected_without_new_algorithm_run(self):
        path = self.repo / experiment.CONFIG
        path.parent.mkdir(parents=True, exist_ok=True)
        altered = deepcopy(POLICY)
        altered["algorithm"]["maximum_parent_minus_child_margin"] = 2
        atomic_json(path, altered)
        with self.assertRaisesRegex(ValueError, "Predeclared experiment config changed"):
            experiment.read_policy(self.repo)


if __name__ == "__main__":
    unittest.main()
