"""Checkpoint transactions, resumed optimization and trainer state transitions."""

from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import random
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import cuad_checkpoints as checkpoints
from check_cuad_families import canonical_sha256, read_json
from cuad_training import FitWindowDataset, make_optimizer
from train_cuad import initial_progress, learning_rate, record_evaluation, run, train_updates, validate_progress


class TinyQA(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.embeddings = torch.nn.Embedding(16, 8)
        self.dropout = torch.nn.Dropout(.2)
        self.qa_outputs = torch.nn.Linear(8, 2)

    def forward(self, input_ids, attention_mask):
        logits = self.qa_outputs(self.dropout(self.embeddings(input_ids)))
        return SimpleNamespace(start_logits=logits[:, :, 0], end_logits=logits[:, :, 1])


def components():
    model = TinyQA()
    return model, make_optimizer(model), torch.amp.GradScaler("cuda", enabled=False)


def make_dataset(root, n=17):
    directory = root / "fit/a"
    directory.mkdir(parents=True)
    values = {"input_ids": np.tile([0, 2, 3, 4, 5, 1], (n, 1)).astype(np.int32),
              "attention_mask": np.tile([1, 1, 1, 1, 1, 0], (n, 1)).astype(np.uint8),
              "window_index": np.array([[0, 0, i % 2] for i in range(n)], dtype=np.int32),
              "gold_pairs": np.array([[i, 2, 3] if i % 2 else [i, 0, 0] for i in range(n)], dtype=np.int32)}
    for name, value in values.items():
        np.save(directory / (name + ".npy"), value, allow_pickle=False)
    shards = [{"path": "fit/a", "global_window_start": 0, "global_window_end": n}]
    return FitWindowDataset(root, shards, list(range(n)))


def evaluation(score=.5, probe=False):
    return {"status": "probe_only" if probe else "complete_dev_select", "selection_eligible": not probe,
            "selection": {"macro_f1": score}, "questions": 1, "windows": 3}


class SchedulerTests(unittest.TestCase):
    def test_warmup_and_decay_use_full_training_horizon_even_for_pilot(self):
        total = 3474
        self.assertAlmostEqual(learning_rate(0, total), 2e-5 / 348)
        self.assertAlmostEqual(learning_rate(347, total), 2e-5)
        self.assertAlmostEqual(learning_rate(348, total), 2e-5)
        self.assertGreater(learning_rate(total - 1, total), 0)
        self.assertLess(learning_rate(total - 1, total), learning_rate(0, total))
        self.assertTrue(all(learning_rate(i, total) >= learning_rate(i + 1, total) for i in range(348, total - 1)))

    def test_invalid_schedule_position_and_partial_update_cursor_fail(self):
        for step, total in ((True, 10), (-1, 10), (10, 10), (0, 0)):
            with self.assertRaises(ValueError):
                learning_rate(step, total)
        for key, value in (("offset", 3), ("global_step", 1), ("examples_seen", 2), ("completed", True)):
            progress = {**initial_progress(), key: value}
            with self.assertRaises(ValueError):
                validate_progress(progress, [17, 17, 17])

    def test_probe_cannot_select_checkpoint_and_ties_count_as_non_improvement(self):
        progress = initial_progress()
        with self.assertRaisesRegex(ValueError, "Partial/probe"):
            record_evaluation(progress, evaluation(probe=True), 17)
        self.assertTrue(record_evaluation(progress, evaluation(.5), 17))
        self.assertFalse(record_evaluation(progress, evaluation(.5), 17))
        self.assertFalse(record_evaluation(progress, evaluation(.4), 17))
        self.assertTrue(progress["completed"])
        self.assertEqual(progress["best_score"], .5)
        self.assertEqual(progress["bad_evaluations"], 2)


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2)
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model, self.optimizer, self.scaler = components()

    def save(self, progress=None, evaluation_result=None, new_best=False):
        with redirect_stdout(StringIO()):
            return checkpoints.save(self.root, "run", self.model, self.optimizer, self.scaler,
                                    progress or initial_progress(), evaluation_result, new_best)

    def test_rng_roundtrip_restores_torch_python_and_numpy_sequences(self):
        torch.manual_seed(8)
        random.seed(8)
        np.random.seed(8)
        self.save()
        expected = (torch.rand(4), random.random(), np.random.random(4))
        replacement = components()
        with redirect_stdout(StringIO()):
            checkpoints.restore(self.root, "run", *replacement)
        torch.testing.assert_close(torch.rand(4), expected[0], rtol=0, atol=0)
        self.assertEqual(random.random(), expected[1])
        np.testing.assert_array_equal(np.random.random(4), expected[2])

    def test_resumed_dropout_adam_and_short_tail_match_uninterrupted_updates(self):
        data = make_dataset(self.root / "features")
        self.addCleanup(data.close)
        state = initial_progress()
        torch.manual_seed(42)
        first = train_updates(self.model, self.optimizer, self.scaler, data, state, 6, 2, torch.device("cpu"))
        self.assertEqual(first["examples"], 16)
        self.save(state)
        expected = train_updates(self.model, self.optimizer, self.scaler, data, state, 6, 2, torch.device("cpu"))
        expected_model, expected_optimizer, expected_state = deepcopy(self.model.state_dict()), deepcopy(self.optimizer.state_dict()), deepcopy(state)
        model, optimizer, scaler = components()
        with redirect_stdout(StringIO()):
            resumed = checkpoints.restore(self.root, "run", model, optimizer, scaler)
        actual = train_updates(model, optimizer, scaler, data, resumed, 6, 2, torch.device("cpu"))
        self.assertEqual(actual["examples"], 1)
        self.assertEqual(actual, expected)
        self.assertEqual(resumed, expected_state)
        validate_progress(resumed, [17, 17, 17])
        for key, value in model.state_dict().items():
            torch.testing.assert_close(value, expected_model[key], rtol=0, atol=0)
        for key, entry in optimizer.state_dict()["state"].items():
            for field, value in entry.items():
                torch.testing.assert_close(value, expected_optimizer["state"][key][field], rtol=0, atol=0)

    def test_corrupt_checkpoint_is_rejected_before_deserialization(self):
        self.save()
        pointer = read_json(self.root / "latest.json")
        path = self.root / "checkpoints" / pointer["checkpoint"] / "training.pt"
        with path.open("ab") as handle:
            handle.write(b"changed")
        with patch("cuad_checkpoints.torch.load") as load, self.assertRaises(ValueError):
            checkpoints.restore(self.root, "run", self.model, self.optimizer, self.scaler)
        load.assert_not_called()

    def test_wrong_run_or_unsafe_pointer_is_rejected(self):
        self.save()
        with self.assertRaises(ValueError):
            checkpoints.latest(self.root, "other-run")
        pointer = read_json(self.root / "latest.json")
        pointer["checkpoint"] = "../escape"
        (self.root / "latest.json").write_text(json.dumps(pointer), encoding="utf-8")
        with self.assertRaises(ValueError):
            checkpoints.latest(self.root, "run")

    def test_failed_state_save_preserves_previous_latest(self):
        self.save()
        before = (self.root / "latest.json").read_bytes()
        with patch("cuad_checkpoints.torch.save", side_effect=OSError("disk failure")), self.assertRaises(OSError):
            self.save()
        self.assertEqual((self.root / "latest.json").read_bytes(), before)
        self.assertEqual(len(list((self.root / "checkpoints").iterdir())), 1)
        checkpoints.latest(self.root, "run")

    def test_failed_pointer_publication_ignores_orphan_and_keeps_committed_backup(self):
        self.save()
        first = read_json(self.root / "latest.json")["checkpoint"]
        with patch("cuad_checkpoints.replace_json", side_effect=OSError("pointer failure")), self.assertRaises(OSError):
            self.save()
        self.assertEqual(checkpoints.latest(self.root, "run")[0].name, first)
        self.save()
        self.assertEqual({p.name for p in (self.root / "checkpoints").iterdir()}, {first, "checkpoint-000003"})

    def test_two_checkpoint_retention_protects_best_and_latest(self):
        state = self.save(evaluation_result=evaluation(.7), new_best=True)
        best = state["best_checkpoint"]
        for _ in range(3):
            state = self.save(state)
        remaining = {p.name for p in (self.root / "checkpoints").iterdir()}
        self.assertEqual(remaining, {best, read_json(self.root / "latest.json")["checkpoint"]})
        self.assertEqual(len(remaining), 2)

    def test_low_disk_space_and_probe_best_promotion_are_rejected(self):
        with patch("cuad_checkpoints.shutil.disk_usage", return_value=SimpleNamespace(free=0)), self.assertRaisesRegex(ValueError, "disk space"):
            self.save()
        with self.assertRaisesRegex(ValueError, "Probe"):
            self.save(evaluation_result=evaluation(probe=True), new_best=True)
        self.assertFalse((self.root / "latest.json").exists())


class RunnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        scripts = self.repo / "ml/scripts"
        scripts.mkdir(parents=True)
        for name in ("cuad_training.py", "cuad_development.py", "cuad_checkpoints.py", "train_cuad.py"):
            (scripts / name).write_text("# fixture\n", encoding="utf-8")
        config = self.repo / "ml/configs/cuad_training_source.json"
        config.parent.mkdir()
        config.write_text("{}", encoding="utf-8")
        self.features = self.repo / "data/processed/cuad/features_v1"
        self.data = make_dataset(self.features)
        self.addCleanup(self.data.close)
        (self.repo / "data/processed/cuad/training_plan_v1").mkdir()
        payloads = {"fit_index.json": {"shards": self.data.shards}}
        for e in range(1, 4):
            payloads[f"epoch_{e}.json"] = {"global_fit_window_indices": list(range(17))}
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for target in ("verify_ignored_assets", "validate_config", "verify_local_assets"):
            self.stack.enter_context(patch("train_cuad." + target))
        self.stack.enter_context(patch("train_cuad.runtime_versions", return_value={"torch": "fixture"}))
        self.stack.enter_context(patch("train_cuad.verify_training_plan", return_value=({"plan_sha256": "fixture"}, payloads)))
        self.stack.enter_context(patch("train_cuad.initialize_qa_model", side_effect=lambda *args: TinyQA()))
        self.evaluator = self.stack.enter_context(patch("train_cuad.evaluate", side_effect=lambda *args, **kwargs: evaluation(probe=kwargs.get("probe", False))))
        self.stack.enter_context(redirect_stdout(StringIO()))

    def test_full_small_run_evaluates_each_epoch_and_preserves_best(self):
        result = run(self.repo, device_name="cpu", limit=None)
        self.assertEqual(result["global_step"], 6)
        self.assertEqual(result["examples_seen"], 51)
        self.assertEqual(len(result["history"]), 3)
        self.assertTrue(result["completed"])
        self.assertEqual(self.evaluator.call_count, 3)
        root = self.repo / "data/processed/cuad/clean_training_v1"
        remaining = {p.name for p in (root / "checkpoints").iterdir()}
        self.assertEqual(len(remaining), 2)
        self.assertIn(result["best_checkpoint"], remaining)
        self.assertEqual(run(self.repo, device_name="cpu", limit=None, resume=True), result)
        self.assertEqual(self.evaluator.call_count, 3)

    def test_pilot_resume_advances_without_reusing_examples_or_changing_horizon(self):
        first = run(self.repo, device_name="cpu", limit=1)
        self.assertEqual((first["global_step"], first["offset"]), (1, 16))
        self.evaluator.assert_not_called()
        second = run(self.repo, device_name="cpu", limit=1, resume=True)
        self.assertEqual((second["global_step"], second["epoch"], second["offset"]), (2, 1, 0))
        self.assertEqual(second["examples_seen"], 17)
        identity = read_json(self.repo / "data/processed/cuad/clean_training_v1/identity.json")
        self.assertEqual(identity["total_optimizer_steps"], 6)

    def test_error_during_evaluation_resumes_pending_evaluation_without_retraining_epoch(self):
        self.evaluator.side_effect = RuntimeError("interrupted evaluation")
        with self.assertRaisesRegex(RuntimeError, "interrupted evaluation"):
            run(self.repo, device_name="cpu", limit=None)
        root = self.repo / "data/processed/cuad/clean_training_v1"
        identity = read_json(root / "identity.json")
        saved = checkpoints.latest(root, canonical_sha256(identity))[2]
        self.assertEqual((saved["global_step"], saved["epoch"], saved["offset"]), (2, 0, 17))
        self.evaluator.side_effect = lambda *args, **kwargs: evaluation()
        finished = run(self.repo, device_name="cpu", limit=None, resume=True)
        self.assertEqual((finished["global_step"], finished["examples_seen"]), (6, 51))

    def test_existing_run_requires_resume_and_rejects_setting_or_code_changes(self):
        run(self.repo, device_name="cpu", limit=1)
        with self.assertRaisesRegex(ValueError, "Add --resume"):
            run(self.repo, device_name="cpu", limit=1)
        with self.assertRaisesRegex(ValueError, "settings changed"):
            run(self.repo, device_name="cpu", limit=1, resume=True, batch_size=1)
        (self.repo / "ml/scripts/train_cuad.py").write_text("# edited\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "settings changed"):
            run(self.repo, device_name="cpu", limit=1, resume=True)

    def test_probe_does_not_change_checkpoint_or_selection_history(self):
        first = run(self.repo, device_name="cpu", limit=1)
        root = self.repo / "data/processed/cuad/clean_training_v1"
        before = (root / "latest.json").read_bytes()
        after = run(self.repo, device_name="cpu", resume=True, probe=True)
        self.assertEqual(first, after)
        self.assertEqual((root / "latest.json").read_bytes(), before)
        self.assertTrue((root / "dev_probe_step_000001.json").is_file())
        self.assertFalse(read_json(root / "dev_probe_step_000001.json")["evaluation"]["selection_eligible"])


if __name__ == "__main__":
    unittest.main()
