"""Real GradScaler overflow, same-batch replay and legacy checkpoint recovery."""

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cuad_checkpoints as checkpoints
from check_cuad_families import canonical_sha256, read_json
from cuad_training import AMP_MAX_RETRIES, collate_windows, make_optimizer, optimizer_update
from train_cuad import (LEGACY_CODE_SHA256, LEGACY_POLICY, POLICY, initial_progress,
                        resolve_execution, run, train_updates)
import test_cuad_trainer as fixtures


def example(index=0):
    return {"input_ids": torch.tensor([0, 2, 3, 4, 5, 1]),
            "attention_mask": torch.tensor([1, 1, 1, 1, 1, 0]),
            "gold_pairs": torch.tensor([[2, 3]] if index % 2 else [[0, 0]]),
            "global_index": index, "status": index % 2}


def assert_tree_equal(test, actual, expected):
    if isinstance(actual, torch.Tensor):
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    elif isinstance(actual, dict):
        test.assertEqual(set(actual), set(expected))
        for key in actual:
            assert_tree_equal(test, actual[key], expected[key])
    elif isinstance(actual, (list, tuple)):
        test.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            assert_tree_equal(test, a, b)
    else:
        test.assertEqual(actual, expected)


class AmpUpdateTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2)
        torch.manual_seed(31)
        self.device = torch.device("cpu")
        self.model = fixtures.TinyQA()
        self.optimizer = make_optimizer(self.model)
        # Real public GradScaler state machine on CPU, with FP16 autocast.
        self.scaler = torch.amp.GradScaler("cpu", init_scale=256.)
        self.batches = [collate_windows([example(i)]) for i in range(4)]

    def update(self):
        with redirect_stdout(StringIO()):
            return optimizer_update(self.model, self.optimizer, self.scaler, self.batches, self.device)

    def inject_once(self, value=float("inf")):
        calls = []
        def hook(gradient):
            calls.append(1)
            return torch.full_like(gradient, value) if len(calls) == 1 else gradient
        handle = self.model.qa_outputs.weight.register_hook(hook)
        self.addCleanup(handle.remove)
        return calls

    def test_overflow_replays_same_microbatches_and_dropout_then_performs_one_adam_step(self):
        reference = deepcopy(self.model)
        calls = self.inject_once()
        seen = []
        hook = self.model.dropout.register_forward_hook(lambda m, a, result: seen.append(result.detach().clone()))
        self.addCleanup(hook.remove)
        rng = torch.get_rng_state()
        with patch.object(self.optimizer, "step", wraps=self.optimizer.step) as step, \
                patch("torch.nn.utils.clip_grad_norm_", wraps=torch.nn.utils.clip_grad_norm_) as clip:
            result = self.update()
        self.assertEqual(step.call_count, 1)
        self.assertEqual(clip.call_count, 1)
        self.assertEqual(len(calls), 8)
        self.assertEqual(result["amp_overflow_retries"], 1)
        self.assertEqual(result["examples"], 4)
        self.assertEqual(result["loss_scale"], 128.)
        for first, second in zip(seen[:4], seen[4:]):
            torch.testing.assert_close(first, second, rtol=0, atol=0)
        end_rng = torch.get_rng_state()
        torch.set_rng_state(rng)
        ref_optimizer = make_optimizer(reference)
        expected = optimizer_update(reference, ref_optimizer, torch.amp.GradScaler("cpu", init_scale=128.),
                                    self.batches, self.device)
        self.assertEqual(result["mean_loss"], expected["mean_loss"])
        assert_tree_equal(self, self.model.state_dict(), reference.state_dict())
        assert_tree_equal(self, self.optimizer.state_dict(), ref_optimizer.state_dict())
        torch.testing.assert_close(torch.get_rng_state(), end_rng, rtol=0, atol=0)
        self.assertTrue(all(p.grad is None for p in self.model.parameters()))

    def test_nan_gradient_also_backs_off_without_reaching_adam(self):
        self.inject_once(float("nan"))
        with patch.object(self.optimizer, "step", wraps=self.optimizer.step) as step:
            result = self.update()
        self.assertEqual(result["amp_overflow_retries"], 1)
        self.assertEqual(step.call_count, 1)
        self.assertTrue(all(torch.isfinite(p).all() for p in self.model.parameters()))

    def test_persistent_overflow_is_bounded_and_preserves_populated_adam_state(self):
        self.update()
        weights, state = deepcopy(self.model.state_dict()), deepcopy(self.optimizer.state_dict())
        handle = self.model.qa_outputs.weight.register_hook(lambda g: torch.full_like(g, float("inf")))
        self.addCleanup(handle.remove)
        with patch.object(self.optimizer, "step", wraps=self.optimizer.step) as step, \
                self.assertRaisesRegex(ValueError, f"after {AMP_MAX_RETRIES} retries"):
            self.update()
        step.assert_not_called()
        assert_tree_equal(self, self.model.state_dict(), weights)
        assert_tree_equal(self, self.optimizer.state_dict(), state)
        self.assertTrue(all(p.grad is None for p in self.model.parameters()))

    def test_fp32_nonfinite_gradients_fail_without_retry_or_update(self):
        self.scaler = torch.amp.GradScaler("cpu", enabled=False)
        self.inject_once()
        with patch.object(self.optimizer, "step", wraps=self.optimizer.step) as step, \
                self.assertRaisesRegex(ValueError, "Nonfinite FP32"):
            self.update()
        step.assert_not_called()
        self.assertTrue(all(p.grad is None for p in self.model.parameters()))

    def test_forward_nan_still_fails_without_scale_backoff(self):
        before = deepcopy(self.model.state_dict())
        output = SimpleNamespace(start_logits=torch.full((1, 6), float("nan")), end_logits=torch.zeros(1, 6))
        with patch.object(self.model, "forward", return_value=output), self.assertRaisesRegex(ValueError, "Nonfinite logits"):
            self.update()
        self.assertEqual(self.scaler.get_scale(), 256.)
        assert_tree_equal(self, self.model.state_dict(), before)

    def test_finite_gradients_with_overflowing_norm_still_fail_before_adam(self):
        handle = self.model.qa_outputs.weight.register_hook(lambda g: torch.full_like(g, 1e30))
        self.addCleanup(handle.remove)
        with patch.object(self.optimizer, "step", wraps=self.optimizer.step) as step, \
                self.assertRaisesRegex(RuntimeError, "non-finite"):
            self.update()
        step.assert_not_called()

    def test_successful_retry_advances_sample_and_scheduler_position_only_once(self):
        self.inject_once()
        progress = initial_progress()
        with redirect_stdout(StringIO()):
            result = train_updates(self.model, self.optimizer, self.scaler,
                                   [example(i) for i in range(17)], progress, 6, 2, self.device)
        self.assertEqual(result["amp_overflow_retries"], 1)
        self.assertEqual((progress["global_step"], progress["offset"], progress["examples_seen"]), (1, 16, 16))
        self.assertAlmostEqual(progress["epoch_loss_sum"], result["mean_loss"] * 16)

    def test_exhausted_retries_do_not_advance_training_progress(self):
        handle = self.model.qa_outputs.weight.register_hook(lambda g: torch.full_like(g, float("inf")))
        self.addCleanup(handle.remove)
        progress = initial_progress()
        with redirect_stdout(StringIO()), self.assertRaisesRegex(ValueError, "overflow persisted"):
            train_updates(self.model, self.optimizer, self.scaler,
                          [example(i) for i in range(17)], progress, 6, 2, self.device)
        self.assertEqual(progress, initial_progress())

    def test_reduced_scale_and_next_dropout_update_survive_checkpoint_roundtrip(self):
        self.inject_once()
        progress = initial_progress()
        dataset = [example(i) for i in range(32)]
        with TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            root = Path(tmp)
            train_updates(self.model, self.optimizer, self.scaler, dataset, progress, 6, 2, self.device)
            checkpoints.save(root, "run", self.model, self.optimizer, self.scaler, progress, execution_sha="fix")
            expected = train_updates(self.model, self.optimizer, self.scaler, dataset, progress, 6, 2, self.device)
            weights, optimizer_state = deepcopy(self.model.state_dict()), deepcopy(self.optimizer.state_dict())
            model = fixtures.TinyQA()
            optimizer = make_optimizer(model)
            scaler = torch.amp.GradScaler("cpu", init_scale=256.)
            resumed = checkpoints.restore(root, "run", model, optimizer, scaler, execution_sha="fix")
            self.assertEqual(scaler.get_scale(), 128.)
            result = train_updates(model, optimizer, scaler, dataset, resumed, 6, 2, self.device)
            self.assertEqual(result, expected)
            self.assertEqual(resumed, progress)
            assert_tree_equal(self, model.state_dict(), weights)
            assert_tree_equal(self, optimizer.state_dict(), optimizer_state)
            self.assertEqual(scaler.state_dict(), self.scaler.state_dict())


class RecoveryIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.current = {"policy": deepcopy(POLICY), "runtime": {"torch": "pinned"}, "batch_size": 2,
                        "plan_sha256": "frozen", "code_sha256": {"patched": "hash"}, "decoder_policy": {"threshold": 0}}
        self.legacy = {**self.current, "policy": LEGACY_POLICY, "code_sha256": LEGACY_CODE_SHA256}
        self.write_identity(self.legacy)

    def write_identity(self, value):
        (self.root / "identity.json").write_text(json.dumps(value), encoding="utf-8")

    def test_recovery_is_explicit_and_does_not_rewrite_original_identity(self):
        original = (self.root / "identity.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "--recover-amp once"):
            resolve_execution(self.root, self.current, resume=True)
        saved, amendment = resolve_execution(self.root, self.current, resume=True, recover_amp=True)
        self.assertEqual(saved, self.legacy)
        self.assertEqual(amendment["original_run_sha256"], canonical_sha256(self.legacy))
        self.assertEqual(amendment["execution_sha256"], canonical_sha256(self.current))
        self.assertEqual((self.root / "identity.json").read_bytes(), original)
        self.assertFalse((self.root / "amp_recovery.json").exists())

    def test_recovery_rejects_changes_to_data_runtime_batches_decoder_or_old_code(self):
        for key, value in (("plan_sha256", "other"), ("runtime", {}), ("batch_size", 1),
                           ("decoder_policy", {}), ("code_sha256", {**LEGACY_CODE_SHA256, "train_cuad.py": "unknown"})):
            self.write_identity({**self.legacy, key: value})
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "beyond the supported AMP fix"):
                resolve_execution(self.root, self.current, resume=True, recover_amp=True)

    def test_recorded_recovery_allows_normal_resume_but_rejects_changed_amendment_or_code(self):
        _, amendment = resolve_execution(self.root, self.current, resume=True, recover_amp=True)
        path = self.root / "amp_recovery.json"
        path.write_text(json.dumps(amendment), encoding="utf-8")
        self.assertEqual(resolve_execution(self.root, self.current, resume=True), (self.legacy, amendment))
        with self.assertRaisesRegex(ValueError, "active code/settings changed"):
            resolve_execution(self.root, {**self.current, "code_sha256": {"patched": "different"}}, resume=True)
        path.write_text(json.dumps({**amendment, "execution_sha256": "damaged"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "recovery record"):
            resolve_execution(self.root, self.current, resume=True, recover_amp=True)

    def test_new_run_cannot_claim_legacy_recovery(self):
        self.write_identity(self.current)
        with self.assertRaisesRegex(ValueError, "requires the saved pre-fix run"):
            resolve_execution(self.root, self.current, resume=True, recover_amp=True)


class RecoveryRunnerTests(unittest.TestCase):
    def setUp(self):
        # Use existing tiny repository/feature fixtures; run the real runner.
        fixtures.RunnerIntegrationTests.setUp(self)

    def legacy_checkpoint(self):
        result = run(self.repo, device_name="cpu", limit=1)
        root = self.repo / "data/processed/cuad/clean_training_v1"
        identity = read_json(root / "identity.json")
        legacy = {**identity, "policy": LEGACY_POLICY, "code_sha256": LEGACY_CODE_SHA256}
        run_sha = canonical_sha256(legacy)
        directory, manifest, _ = checkpoints.latest(root, canonical_sha256(identity))
        payload = torch.load(directory / "training.pt", weights_only=True)
        payload["run_sha256"] = run_sha
        del payload["execution_sha256"]
        torch.save(payload, directory / "training.pt")
        manifest["run_sha256"] = run_sha
        del manifest["execution_sha256"]
        manifest["files"]["training.pt"] = checkpoints.file_spec(directory / "training.pt")
        for path, value in ((root / "identity.json", legacy), (directory / "manifest.json", manifest),
                            (root / "latest.json", {"run_sha256": run_sha, "checkpoint": directory.name,
                                                     "manifest_sha256": canonical_sha256(manifest)})):
            path.write_bytes((json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                                        allow_nan=False) + "\n").encode("utf-8"))
        return root, result, directory

    def test_legacy_restore_records_patch_then_normal_resume_saves_execution_binding(self):
        root, first, directory = self.legacy_checkpoint()
        original_identity = (root / "identity.json").read_bytes()
        original_payload = (directory / "training.pt").read_bytes()
        original_pointer = (root / "latest.json").read_bytes()
        recovered = run(self.repo, device_name="cpu", resume=True, recover_amp=True, probe=True)
        self.assertEqual(recovered, first)
        self.assertEqual((root / "identity.json").read_bytes(), original_identity)
        self.assertEqual((directory / "training.pt").read_bytes(), original_payload)
        self.assertEqual((root / "latest.json").read_bytes(), original_pointer)
        amendment = read_json(root / "amp_recovery.json")
        second = run(self.repo, device_name="cpu", resume=True, limit=1)
        self.assertEqual(second["global_step"], first["global_step"] + 1)
        _, manifest, _ = checkpoints.latest(root, canonical_sha256(read_json(root / "identity.json")))
        self.assertEqual(manifest["execution_sha256"], amendment["execution_sha256"])
        final = run(self.repo, device_name="cpu", resume=True, limit=None)
        self.assertEqual(final["global_step"], 6)
        self.assertTrue(final["completed"])

    def test_corrupt_legacy_checkpoint_cannot_create_recovery_record(self):
        root, _, directory = self.legacy_checkpoint()
        with (directory / "training.pt").open("ab") as stream:
            stream.write(b"corrupt")
        with self.assertRaises(ValueError):
            run(self.repo, device_name="cpu", resume=True, recover_amp=True)
        self.assertFalse((root / "amp_recovery.json").exists())

    def test_changed_execution_marker_is_rejected_before_loading_weights(self):
        root, _, _ = self.legacy_checkpoint()
        run(self.repo, device_name="cpu", resume=True, recover_amp=True, limit=1)
        saved = read_json(root / "identity.json")
        model, optimizer, scaler = fixtures.components()
        with patch("cuad_checkpoints.torch.load") as load, self.assertRaisesRegex(ValueError, "execution identity differs"):
            checkpoints.restore(root, canonical_sha256(saved), model, optimizer, scaler,
                                execution_sha="wrong", allow_legacy=True)
        load.assert_not_called()

    def test_missing_recovery_flag_stops_before_changing_legacy_files(self):
        root, _, _ = self.legacy_checkpoint()
        pointer = (root / "latest.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "--recover-amp once"):
            run(self.repo, device_name="cpu", resume=True)
        self.assertEqual((root / "latest.json").read_bytes(), pointer)
        self.assertFalse((root / "amp_recovery.json").exists())


if __name__ == "__main__":
    unittest.main()
