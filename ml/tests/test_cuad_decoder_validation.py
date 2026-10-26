"""Full-beam geometry, inference coverage, immutable resume and checkpoint loading."""

from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import torch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import canonical_sha256, read_json
from cuad_development import evaluate, match_counts
from cuad_checkpoints import file_spec, replace_json
from prepare_cuad_features import ARRAYS, COUNTS
from run_cuad_baseline import atomic_json
import validate_cuad_decoder as validation


def candidate(a, b, score=1., row=0, boundary=False):
    return {"start": a, "end": b, "margin": score, "window_row": row, "start_token": 2, "end_token": 2,
            "null_score": 0., "boundary_review": boundary, "text": "x" * (b - a)}


class FixedModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.bias = torch.nn.Parameter(torch.tensor(5.))
        self.calls = []

    def forward(self, input_ids, attention_mask):
        self.calls.append((len(input_ids), self.training, torch.is_grad_enabled()))
        logits = torch.zeros_like(input_ids, dtype=torch.float32)
        logits[:, 2] = self.bias
        return SimpleNamespace(start_logits=logits, end_logits=logits)


def fixture(repo):
    """Real typed feature files and source bindings; synthetic model/source."""
    feature = repo / validation.BASE / "features_v1"
    training = repo / validation.BASE / "clean_training_v1"
    training.mkdir(parents=True)
    context = "αβ🙂_" * 30
    gold_sets = [[(0, 5), (10, 15)], [], [(100, 120)]]
    questions = [{"question_id": f"q{i}", "category_id": "c", "is_impossible": not bool(spans),
                  "answers": [{"start": a, "end": b, "text": context[a:b]} for a, b in spans]}
                 for i, spans in enumerate(gold_sets)]
    group = {"group_id": "group", "family_id": "family", "official_split": "train",
             "paragraphs": [{"index": 0, "context": context, "questions": questions}]}
    partition = {"partition": "dev_select", "intended_role": "checkpoint_and_decoder_selection", "groups": [group]}
    relative = f"dev_select/{canonical_sha256(group)[:24]}"
    directory = feature / relative
    directory.mkdir(parents=True)
    arrays = {name: np.zeros((3 if name == "question_ranges" else 0 if name in ("gold_pairs", "gold_refs") else 9, *tail), dtype=dtype)
              for name, (dtype, tail) in ARRAYS.items()}
    arrays["input_ids"][:] = 1
    arrays["input_ids"][:, :4] = [0, 4, 5, 2]
    arrays["attention_mask"][:, :4] = 1
    arrays["sequence_ids"][:] = -1
    arrays["sequence_ids"][:, 1:3] = [0, 1]
    arrays["offsets"][:] = -1
    arrays["question_ranges"][:] = [[0, 3], [3, 6], [6, 9]]
    for row in range(9):
        arrays["offsets"][row, 2] = [(row % 3) * 10, (row % 3) * 10 + 5]
    specs = {}
    for name, array in arrays.items():
        path = directory / (name + ".npy")
        np.save(path, array, allow_pickle=False)
        specs[path.name] = {**file_spec(path), "dtype": array.dtype.str, "shape": list(array.shape)}
    atomic_json(directory / "source.json", {"source_group": group})
    specs["source.json"] = file_spec(directory / "source.json")
    frozen = {"fixture": "verified by mocked source-chain loader"}
    atomic_json(repo / validation.FROZEN_DIR / "manifest.json", frozen)
    identity = {"policy": validation.FEATURE_POLICY, "partition_roles": validation.ROLES,
                "training_source_sha256": validation.SOURCE_PIN, "frozen_manifest_sha256": canonical_sha256(frozen)}
    atomic_json(feature / "identity.json", identity)
    summary = {k: 0 for k in COUNTS}
    summary.update(groups=1, questions=3, windows=9)
    shard = {"feature_identity_sha256": canonical_sha256(identity), "partition": "dev_select", "group_id": "group",
             "family_id": "family", "source_group_sha256": canonical_sha256(group), "files": specs, "summary": summary}
    atomic_json(directory / "manifest.json", shard)
    manifest = {"complete": True, "feature_identity_sha256": canonical_sha256(identity),
                "partitions": {"dev_select": [{"path": relative, "manifest_sha256": canonical_sha256(shard), "summary": summary}],
                               "dev_cal": [{"path": "MUST_NOT_READ"}], "dev_policy": [{"path": "MUST_NOT_READ"}]}}
    atomic_json(feature / "manifest.json", manifest)
    plan_identity = {"feature_manifest_sha256": canonical_sha256(manifest), "feature_identity_sha256": canonical_sha256(identity)}
    plan = {"identity": plan_identity, "plan_sha256": canonical_sha256(plan_identity)}
    plan_path = f"{validation.BASE}/training_plan_v1"
    atomic_json(repo / plan_path / "manifest.json", plan)
    atomic_json(training / "identity.json", {"feature_directory": feature.relative_to(repo).as_posix(),
                "source_config_sha256": validation.SOURCE_PIN, "plan_directory": plan_path, "plan_sha256": plan["plan_sha256"]})
    evaluation = evaluate(FixedModel(), feature, torch.device("cpu"), batch_size=2)
    progress = {"history": [{"evaluation_sha256": canonical_sha256(evaluation), "macro_f1": evaluation["selection"]["macro_f1"]}],
                "best_score": evaluation["selection"]["macro_f1"]}
    with patch.object(validation, "load_frozen_partition", return_value=partition), redirect_stdout(StringIO()):
        tasks, binding = validation.verify_inputs(repo, feature, training, evaluation, progress)
    return SimpleNamespace(feature=feature, training=training, directory=directory, arrays=arrays,
                           evaluation=evaluation, progress=progress, tasks=tasks, binding=binding, partition=partition)


class GeometryTests(unittest.TestCase):
    def test_disjoint_applies_before_original_nms(self):
        # Original NMS keeps A and B, losing C. Disjoint then drops B.
        # Applying disjoint directly keeps A and C: C touches A without overlap.
        raw = [candidate(0, 10, 3), candidate(9, 20, 2), candidate(10, 20, 1)]
        result, capped = validation.selections(raw)
        self.assertEqual([(c["start"], c["end"]) for c in capped], [(0, 10), (9, 20)])
        self.assertEqual([(c["start"], c["end"]) for c in result["disjoint_full"]], [(0, 10), (10, 20)])

    def test_full_pool_can_keep_answers_beyond_global_cap(self):
        raw = [candidate(i * 10, i * 10 + 5, 100 - i, i) for i in range(60)]
        result, capped = validation.selections(raw)
        self.assertEqual(len(capped), 50)
        self.assertEqual(len(result["original_capped"]), 50)
        self.assertTrue(all(len(result[n]) == 60 for n in ("original_uncapped", "disjoint_full", "iou_0_5_full", "containment_0_8_full")))
        self.assertEqual(len(result["top_one_full_diagnostic"]), 1)

    def test_exact_dedup_keeps_score_and_resolves_complete_counterpart(self):
        raw = [candidate(0, 10, 4, boundary=True), candidate(0, 10, 2, row=1), candidate(20, 30, 1)]
        before = deepcopy(raw)
        exact = validation.exact_candidates(raw)
        self.assertEqual(len(exact), 2)
        self.assertEqual(exact[0]["margin"], 4)
        self.assertFalse(exact[0]["boundary_review"])
        self.assertEqual(raw, before)

    def test_ties_preserve_original_pre_resolution_order(self):
        raw = [candidate(10, 30, 3, boundary=True), candidate(0, 20, 3), candidate(10, 30, 1)]
        result, _ = validation.selections(raw)
        self.assertEqual(result["disjoint_full"][0]["start"], 0)

    def test_fixed_zero_margin_excluded_from_all_variants(self):
        result, _ = validation.selections([candidate(0, 10, 0), candidate(20, 30, -1)])
        self.assertTrue(all(not values for values in result.values()))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.f = fixture(self.repo)
        self.root = self.repo / "result"
        self.root.mkdir()
        self.model = FixedModel()
        self.producer = lambda task: validation.infer_question(self.model, task, self.f.arrays, torch.device("cpu"), 2)

    def collect(self, limit=2, producer=None):
        with redirect_stdout(StringIO()):
            return validation.process_questions(self.root, self.f.tasks, "run", producer or self.producer, self.f.evaluation, limit)

    def record(self):
        raw, counts = self.producer(self.f.tasks[0])
        return validation.make_record(self.f.tasks[0], "run", raw, counts)

    def verify_inputs(self):
        with patch.object(validation, "load_frozen_partition", return_value=self.f.partition) as load, redirect_stdout(StringIO()):
            result = validation.verify_inputs(self.repo, self.f.feature, self.f.training, self.f.evaluation, self.f.progress)
            load.assert_called_once_with(self.repo, "dev_select")
            return result

    def test_actual_shard_hashes_source_ranges_and_training_bindings_pass(self):
        tasks, binding = self.verify_inputs()
        self.assertEqual(tasks, self.f.tasks)
        self.assertEqual(binding, self.f.binding)

    def test_corrupt_feature_bytes_rejected_before_inference(self):
        with (self.f.directory / "input_ids.npy").open("ab") as handle:
            handle.write(b"corruption")
        with self.assertRaises(ValueError):
            self.verify_inputs()
        self.assertFalse(self.model.calls)

    def test_changed_training_plan_binding_rejected(self):
        path = self.f.training / "identity.json"
        identity = read_json(path)
        identity["plan_sha256"] = "wrong"
        replace_json(path, identity)
        with self.assertRaisesRegex(ValueError, "plan hashes"):
            self.verify_inputs()

    def test_foreign_or_reordered_shard_path_rejected(self):
        path = self.f.feature / "manifest.json"
        manifest = read_json(path)
        manifest["partitions"]["dev_select"][0]["path"] = "dev_cal/foreign"
        replace_json(path, manifest)
        with self.assertRaises(ValueError):
            self.verify_inputs()

    def test_all_windows_including_short_tail_eval_mode_no_grad_and_no_weight_change(self):
        before = self.model.bias.detach().clone()
        raw, counts = self.producer(self.f.tasks[0])
        self.assertEqual(self.model.calls, [(2, False, False), (1, False, False)])
        self.assertEqual(counts, [1, 1, 1])
        self.assertEqual([c["window_row"] for c in raw], [0, 1, 2])
        self.assertTrue(torch.equal(before, self.model.bias))
        self.assertIsNone(self.model.bias.grad)

    def test_unicode_record_roundtrip_reconstructs_source_text(self):
        raw = validation.validate_record(self.record(), self.f.tasks[0], "run")
        self.assertEqual(raw[0]["text"], self.f.tasks[0]["context"][:5])
        self.assertIn("🙂", raw[0]["text"])

    def test_record_checksum_identity_and_window_coverage_rejected(self):
        for mode in ("checksum", "task", "run", "coverage", "columns"):
            record = self.record()
            payload = record["payload"]
            if mode == "checksum":
                record["payload_sha256"] = "bad"
            else:
                if mode == "task":
                    payload["task_sha256"] = "wrong"
                elif mode == "run":
                    payload["run_sha256"] = "wrong"
                elif mode == "coverage":
                    payload["window_counts"].pop()
                else:
                    payload["columns"].reverse()
                record["payload_sha256"] = canonical_sha256(payload)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                validation.validate_record(record, self.f.tasks[0], "run")

    def test_bad_candidate_types_ranges_duplicates_order_and_counts_rejected(self):
        for mode in ("bool", "bounds", "row", "length", "duplicate", "order", "counts", "nan"):
            record = self.record()
            payload = record["payload"]
            c = payload["candidates"][0]
            if mode == "bool": c[0] = True
            elif mode == "bounds": c[1] = 10000
            elif mode == "row": c[3] = 1000
            elif mode == "length": c[5] = 300
            elif mode == "duplicate": payload["candidates"].insert(0, deepcopy(c))
            elif mode == "order": payload["candidates"].reverse()
            elif mode == "counts": payload["window_counts"][0] = 0
            elif mode == "nan": c[2] = float("nan")
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                record["payload_sha256"] = canonical_sha256(payload)
                validation.validate_record(record, self.f.tasks[0], "run")

    def test_resume_completes_only_missing_questions_and_replays_original(self):
        first, _ = self.collect()
        self.assertEqual(set(first), {0, 1})
        saved = {p.name: p.read_bytes() for p in (self.root / "questions").glob("*.json")}
        producer = Mock(side_effect=self.producer)
        rows, hashes = self.collect(limit=None, producer=producer)
        producer.assert_called_once_with(self.f.tasks[2])
        for name, contents in saved.items():
            self.assertEqual((self.root / "questions" / name).read_bytes(), contents)
        report = validation.aggregate_results(self.f.tasks, rows, self.f.evaluation)
        self.assertEqual(report["variants"]["original_capped"]["metrics"], self.f.evaluation["selection"])
        self.assertTrue(all(not ids for ids in report["original_replay_differences"].values()))
        self.assertEqual(len(hashes), 3)
        self.assertFalse(report["decoder_adopted"])
        self.assertFalse(report["official_test_evaluated"])
        self.assertEqual(report["variants"]["disjoint_full"]["metrics"]["micro"]["gold"], 3)
        self.assertEqual(report["variants"]["top_one_full_diagnostic"]["strata"]["multiple_gold"]["micro"]["recall"], .5)

    def test_crash_mid_question_keeps_completed_work_for_resume(self):
        producer = Mock(side_effect=[self.producer(self.f.tasks[0]), RuntimeError("interrupted")])
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            self.collect(limit=None, producer=producer)
        self.assertEqual(len(list((self.root / "questions").glob("*.json"))), 1)
        resumed, _ = self.collect(limit=None)
        self.assertEqual(set(resumed), {0, 1, 2})

    def test_partial_results_cannot_be_published_as_full(self):
        rows, _ = self.collect()
        with self.assertRaisesRegex(ValueError, "every development question"):
            validation.aggregate_results(self.f.tasks, rows, self.f.evaluation)
        self.assertFalse((self.root / "report.json").exists())

    def test_corrupt_saved_question_stops_before_new_model_call(self):
        self.collect(limit=1)
        path = self.root / "questions/000000.json"
        record = read_json(path)
        record["payload_sha256"] = "bad"
        replace_json(path, record)
        producer = Mock(side_effect=AssertionError("must not infer"))
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.collect(limit=None, producer=producer)
        producer.assert_not_called()

    def test_foreign_saved_question_is_rejected(self):
        (self.root / "questions").mkdir()
        atomic_json(self.root / "questions/999999.json", {})
        with self.assertRaisesRegex(ValueError, "Foreign"):
            self.collect()

    def test_identity_changes_and_implicit_overwrite_are_rejected(self):
        validation.bind_run(self.root, {"batch": 2}, False)
        self.collect(limit=1)
        with self.assertRaisesRegex(ValueError, "add --resume"):
            validation.bind_run(self.root, {"batch": 2}, False)
        with self.assertRaisesRegex(ValueError, "changed"):
            validation.bind_run(self.root, {"batch": 4}, True)
        self.assertEqual(validation.bind_run(self.root, {"batch": 2}, True), canonical_sha256({"batch": 2}))

    def test_original_replay_drift_is_reported_without_overwriting_reference(self):
        reference = {"prediction": deepcopy(self.f.evaluation["predictions"][0]), "row": self.f.evaluation["per_question"][0]}
        reference["prediction"]["candidates"][0]["margin"] += 1
        row = validation.score_question(self.f.tasks[0], self.producer(self.f.tasks[0])[0], reference)
        self.assertTrue(row["original_replay"]["coordinates_equal"])
        self.assertTrue(row["original_replay"]["counts_equal"])
        self.assertFalse(row["original_replay"]["scores_equal"])
        self.assertEqual(row["original_replay"]["max_margin_difference"], 1)

    def test_run_pilot_then_resume_writes_report_only_when_complete(self):
        # Exercise orchestration with real question files/inference; completed
        # checkpoint/source verification and model loading have separate tests.
        model_path = self.repo / validation.MODEL_DIR / "config.json"
        atomic_json(model_path, {"fixture": True})
        atomic_json(self.repo / validation.CONFIG, {"files": {"config.json": file_spec(model_path)}})
        with ExitStack() as stack, redirect_stdout(StringIO()):
            for name, value in (("load_checkpoint_reports", (self.f.evaluation, self.f.progress, {"selected_checkpoint": "checkpoint-000001", "run_sha256": "training"})),
                                ("verify_inputs", (self.f.tasks, self.f.binding)), ("runtime_versions", {"fixture": True}),
                                ("load_model", self.model)):
                stack.enter_context(patch.object(validation, name, return_value=value))
            for name in ("verify_ignored_assets", "validate_config", "validate_model_metadata"):
                stack.enter_context(patch.object(validation, name))
            first = validation.run(self.repo, device_name="cpu")
            output = self.repo / validation.BASE / "decoder_validation_v1"
            self.assertEqual(len(first), 2)
            self.assertFalse((output / "report.json").exists())
            final = validation.run(self.repo, device_name="cpu", resume=True, limit=None)
            self.assertEqual(len(final), 3)
            before = (output / "report.json").read_bytes()
            self.model.calls.clear()
            validation.run(self.repo, device_name="cpu", resume=True, limit=None)
            self.assertEqual((output / "report.json").read_bytes(), before)
            self.assertFalse(self.model.calls)


class ModelLoadingTests(unittest.TestCase):
    def setUp(self):
        from transformers import RobertaConfig, RobertaForQuestionAnswering
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        config = RobertaConfig(vocab_size=16, hidden_size=16, num_hidden_layers=1,
                               num_attention_heads=2, intermediate_size=32, max_position_embeddings=514,
                               hidden_dropout_prob=0., attention_probs_dropout_prob=0.)
        config.to_json_file(self.root / "config.json")
        self.payload = {"run_sha256": "training", "execution_sha256": "recovery", "progress": {"completed": True},
                        "model": RobertaForQuestionAnswering(config).state_dict(), "optimizer": {"must_not_restore": True}}
        atomic_json(self.root / "manifest.json", {"execution_sha256": "recovery"})

    def load(self):
        torch.save(self.payload, self.root / "training.pt")
        return validation.load_model(self.root / "config.json", self.root, {"completed": True},
                                     {"run_sha256": "training"}, torch.device("cpu"))

    def test_real_tiny_roberta_checkpoint_load_and_inference(self):
        model = self.load()
        self.assertFalse(model.training)
        self.assertTrue(all(not p.requires_grad for p in model.parameters()))
        for name, value in model.state_dict().items():
            self.assertTrue(torch.equal(value, self.payload["model"][name]))
        with TemporaryDirectory() as temp:
            f = fixture(Path(temp))
            before = {name: value.clone() for name, value in model.state_dict().items()}
            raw, counts = validation.infer_question(model, f.tasks[0], f.arrays, torch.device("cpu"), 2)
            self.assertEqual(len(counts), 3)
            self.assertTrue(raw)
            self.assertTrue(all(torch.equal(value, model.state_dict()[name]) for name, value in before.items()))

    def test_wrong_run_progress_execution_and_missing_weights_fail(self):
        original = deepcopy(self.payload)
        for mode in ("run", "progress", "execution", "weights"):
            self.payload = deepcopy(original)
            if mode == "run": self.payload["run_sha256"] = "other"
            elif mode == "progress": self.payload["progress"] = {}
            elif mode == "execution": self.payload["execution_sha256"] = "other"
            else: self.payload["model"].pop(next(iter(self.payload["model"])))
            with self.subTest(mode=mode), self.assertRaises((ValueError, RuntimeError)):
                self.load()

    def test_nonfinite_checkpoint_weights_fail_before_inference(self):
        next(iter(self.payload["model"].values())).fill_(float("nan"))
        with self.assertRaisesRegex(ValueError, "non-finite"):
            self.load()


if __name__ == "__main__":
    unittest.main()
