"""Training math, mmap isolation, source bindings and optimizer-update checks."""

from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
import json
import math
from pathlib import Path
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

from check_cuad_families import canonical_sha256, read_json
from cuad_training import (FitWindowDataset, collate_windows, initialize_qa_model, joint_marginal_loss,
                           make_optimizer, optimizer_update, verify_training_plan)
from prepare_cuad_training_plan import prepare
from smoke_cuad_training import validate_saved_report


def example(index=0, pairs=((2, 3),), status=1):
    return {"input_ids": torch.tensor([0, 4, 5, 6, 7, 2, 1, 1]),
            "attention_mask": torch.tensor([1, 1, 1, 1, 1, 1, 0, 0]),
            "gold_pairs": torch.tensor(pairs, dtype=torch.long), "global_index": index, "status": status}


class MarginalLossTests(unittest.TestCase):
    def test_joint_pairs_do_not_include_cross_answer_combinations(self):
        logits = torch.log(torch.tensor([[0.1, 0.2, 0.3, 0.4]]))
        loss = joint_marginal_loss(logits, logits, torch.tensor([[[1, 1], [2, 3]]]), torch.tensor([[True, True]]))
        self.assertAlmostEqual(loss.item(), -math.log(0.2 * 0.2 + 0.3 * 0.4), places=6)
        self.assertNotAlmostEqual(loss.item(), -math.log((0.2 + 0.3) * (0.2 + 0.4)), places=3)

    def test_single_null_is_sum_of_start_and_end_cross_entropies(self):
        start, end = torch.tensor([[1., -2., 3.]]), torch.tensor([[3., 2., 1.]])
        loss = joint_marginal_loss(start, end, torch.tensor([[[0, 0]]]), torch.tensor([[True]]))
        expected = -torch.log_softmax(start, -1)[0, 0] - torch.log_softmax(end, -1)[0, 0]
        torch.testing.assert_close(loss, expected)

    def test_padding_does_not_add_null_probability_or_require_valid_coordinates(self):
        logits = torch.zeros(2, 8)
        batch = collate_windows([example(pairs=((2, 3), (4, 5))), example(1, ((0, 0),), 0)])
        batch["gold_pairs"][1, 1] = torch.tensor([-99, 999])
        loss = joint_marginal_loss(logits, logits, batch["gold_pairs"], batch["pair_mask"])
        self.assertAlmostEqual(loss.item(), (-math.log(2 / 64) - math.log(1 / 64)) / 2, places=6)

    def test_duplicate_pair_is_rejected_instead_of_double_counted(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            joint_marginal_loss(torch.zeros(1, 8), torch.zeros(1, 8), torch.tensor([[[2, 3], [2, 3]]]), torch.tensor([[True, True]]))

    def test_empty_mask_and_null_positive_mixture_are_rejected(self):
        for pairs, mask in [([[[1, 2]]], [[False]]), ([[[0, 0], [2, 3]]], [[True, True]]), ([[[0, 2]]], [[True]])]:
            with self.assertRaises(ValueError):
                joint_marginal_loss(torch.zeros(1, 8), torch.zeros(1, 8), torch.tensor(pairs), torch.tensor(mask))

    def test_invalid_target_bounds_and_dtypes_are_rejected(self):
        for pairs in ([[[-1, 2]]], [[[3, 2]]], [[[2, 8]]]):
            with self.assertRaises(ValueError):
                joint_marginal_loss(torch.zeros(1, 8), torch.zeros(1, 8), torch.tensor(pairs), torch.tensor([[True]]))
        with self.assertRaises(ValueError):
            joint_marginal_loss(torch.zeros(1, 8), torch.zeros(1, 8), torch.zeros(1, 1, 2), torch.tensor([[True]]))

    def test_nonfinite_logits_fail_closed(self):
        logits = torch.zeros(1, 8)
        logits[0, 4] = float("nan")
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            joint_marginal_loss(logits, torch.zeros(1, 8), torch.tensor([[[2, 3]]]), torch.tensor([[True]]))

    def test_extreme_half_logits_have_finite_fp32_loss_and_gradients(self):
        start = torch.tensor([[1000., -1000., -900., 0.]], dtype=torch.float16, requires_grad=True)
        end = torch.tensor([[1000., -800., -900., 0.]], dtype=torch.float16, requires_grad=True)
        loss = joint_marginal_loss(start, end, torch.tensor([[[1, 2]]]), torch.tensor([[True]]))
        self.assertEqual(loss.dtype, torch.float32)
        loss.backward()
        self.assertTrue(torch.isfinite(loss) and torch.isfinite(start.grad).all() and torch.isfinite(end.grad).all())

    def test_multi_answer_gradients_match_explicit_probability_sum(self):
        torch.manual_seed(7)
        start, end = torch.randn(1, 6, requires_grad=True), torch.randn(1, 6, requires_grad=True)
        loss = joint_marginal_loss(start, end, torch.tensor([[[1, 2], [3, 4]]]), torch.tensor([[True, True]]))
        actual = torch.autograd.grad(loss, (start, end), retain_graph=True)
        p, q = start.softmax(-1), end.softmax(-1)
        expected = torch.autograd.grad(-(p[0, 1] * q[0, 2] + p[0, 3] * q[0, 4]).log(), (start, end))
        for a, b in zip(actual, expected):
            torch.testing.assert_close(a, b)


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.shards = []
        for name, offset, statuses, pairs in [("a", 0, [1, 0, 2], [[0, 2, 3], [0, 4, 5], [1, 0, 0]]),
                                              ("b", 3, [1, 0], [[0, 1, 2], [1, 0, 0]])]:
            directory = self.root / "fit" / name
            directory.mkdir(parents=True)
            values = {"input_ids": np.tile(np.arange(8, dtype=np.int32) + offset, (len(statuses), 1)),
                      "attention_mask": np.ones((len(statuses), 8), dtype=np.uint8),
                      "window_index": np.array([[0, 0, s] for s in statuses], dtype=np.int32),
                      "gold_pairs": np.array(pairs, dtype=np.int32)}
            for key, value in values.items():
                np.save(directory / (key + ".npy"), value, allow_pickle=False)
            self.shards.append({"path": f"fit/{name}", "global_window_start": offset,
                                "global_window_end": offset + len(statuses)})

    def dataset(self, indices):
        result = FitWindowDataset(self.root, self.shards, indices, cache_size=1)
        self.addCleanup(result.close)
        return result

    def test_global_boundary_lookup_and_plan_order_are_preserved(self):
        data = self.dataset([3, 0, 1, 4])
        self.assertEqual([data[i]["global_index"] for i in range(len(data))], [3, 0, 1, 4])
        self.assertEqual(data[0]["input_ids"][0], 3)
        self.assertEqual(data[1]["gold_pairs"].tolist(), [[2, 3], [4, 5]])
        self.assertEqual(data[2]["gold_pairs"].tolist(), [[0, 0]])

    def test_evicted_maps_close_and_returned_tensors_are_independent(self):
        data = self.dataset([0, 3])
        first = data[0]
        mapped = data.cache[0]["input_ids"]._mmap
        data[1]
        self.assertTrue(mapped.closed)
        first["input_ids"][0] = 99
        self.assertEqual(data[0]["input_ids"][0], 0)
        data.close()
        self.assertFalse(data.cache)

    def test_ignored_window_cannot_be_loaded(self):
        with self.assertRaisesRegex(ValueError, "Ignored"):
            self.dataset([2])[0]

    def test_development_paths_and_path_traversal_are_rejected(self):
        for path in ("dev_select/a", "dev_cal/a", "dev_policy/a", "fit/..", "fit/../a", "fit/a\\b"):
            shards = deepcopy(self.shards)
            shards[0]["path"] = path
            with self.assertRaisesRegex(ValueError, "fit shard"):
                FitWindowDataset(self.root, shards, [0])

    def test_duplicate_out_of_bounds_boolean_indices_and_index_gaps_fail(self):
        for indices in ([0, 0], [-1], [5], [True]):
            with self.assertRaises(ValueError):
                self.dataset(indices)
        for start in (2, 4, True):
            shards = deepcopy(self.shards)
            shards[1]["global_window_start"] = start
            with self.assertRaises(ValueError):
                FitWindowDataset(self.root, shards, [0])

    def test_collation_preserves_all_gold_pairs_and_builds_padding_mask(self):
        batch = collate_windows([self.dataset([0])[0], self.dataset([1])[0]])
        self.assertEqual(batch["pair_mask"].tolist(), [[True, True], [True, False]])
        self.assertEqual(batch["gold_pairs"][0].tolist(), [[2, 3], [4, 5]])
        self.assertEqual(batch["input_ids"].dtype, torch.long)
        self.assertEqual(batch["attention_mask"].dtype, torch.long)


class PlanBindingTests(unittest.TestCase):
    def test_saved_plan_reconstruction_rejects_edited_epoch_even_with_updated_digest(self):
        records = [{"partition": "fit", "question_id": "p", "is_impossible": False,
                    "positive_indices": [0], "negative_indices": [1, 2]},
                   {"partition": "fit", "question_id": "n", "is_impossible": True,
                    "positive_indices": [], "negative_indices": [3, 4]}]
        result = ({"partition_summary": {}}, records, [{"path": "fit/a"}], {"feature_identity_sha256": "fixture"})
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "ml/scripts"
            scripts.mkdir(parents=True)
            (scripts / "prepare_cuad_training_plan.py").write_bytes((SCRIPTS / "prepare_cuad_training_plan.py").read_bytes())
            features = root / "data/processed/cuad/features_v1"
            features.mkdir(parents=True)
            plan = root / "data/processed/cuad/training_plan_v1"
            with patch("prepare_cuad_training_plan.audit_features", return_value=result), \
                 patch("prepare_cuad_training_plan.verify_ignored_assets"), redirect_stdout(StringIO()):
                prepare(root)
            with patch("cuad_training.audit_features", return_value=result):
                verify_training_plan(root, features, plan)
                epoch = read_json(plan / "epoch_1.json")
                epoch["global_fit_window_indices"].reverse()
                (plan / "epoch_1.json").write_text(json.dumps(epoch), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "changed"):
                    verify_training_plan(root, features, plan)
                manifest = read_json(plan / "manifest.json")
                manifest["files"]["epoch_1.json"] = canonical_sha256(epoch)
                (plan / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "manifest differs"):
                    verify_training_plan(root, features, plan)


class TinyQA(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = torch.nn.Embedding(16, 4)
        self.qa_outputs = torch.nn.Linear(4, 2)

    def forward(self, input_ids, attention_mask):
        logits = self.qa_outputs(self.embedding(input_ids))
        return SimpleNamespace(start_logits=logits[:, :, 0], end_logits=logits[:, :, 1])


class OptimizationTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2)

    def test_unequal_microbatches_match_full_batch_parameter_update(self):
        torch.manual_seed(12)
        first, second = TinyQA(), TinyQA()
        second.load_state_dict(first.state_dict())
        samples = [example(), example(1, ((0, 0),), 0), example(2, ((2, 3), (4, 5)))]
        one = [collate_windows(samples)]
        split = [collate_windows(samples[:1]), collate_windows(samples[1:])]
        results = []
        for model, batches in ((first, one), (second, split)):
            results.append(optimizer_update(model, make_optimizer(model), torch.amp.GradScaler("cuda", enabled=False),
                                            batches, torch.device("cpu")))
        for p, q in zip(first.parameters(), second.parameters()):
            torch.testing.assert_close(p, q)
        self.assertAlmostEqual(results[0]["mean_loss"], results[1]["mean_loss"], places=6)
        self.assertTrue(all(p.grad is None for p in first.parameters()))

    def test_nonfinite_loss_does_not_change_parameters(self):
        model = TinyQA()
        before = deepcopy(model.state_dict())
        output = SimpleNamespace(start_logits=torch.full((1, 8), float("nan")), end_logits=torch.zeros(1, 8))
        with patch.object(model, "forward", return_value=output), self.assertRaisesRegex(ValueError, "Nonfinite"):
            optimizer_update(model, make_optimizer(model), torch.amp.GradScaler("cuda", enabled=False),
                             [collate_windows([example()])], torch.device("cpu"))
        for k, v in model.state_dict().items():
            torch.testing.assert_close(v, before[k])

    def test_optimizer_excludes_bias_and_layernorm_from_weight_decay(self):
        model = torch.nn.Module()
        model.dense, model.LayerNorm = torch.nn.Linear(4, 4), torch.nn.LayerNorm(4)
        optimizer = make_optimizer(model)
        decayed = {id(p) for group in optimizer.param_groups if group["weight_decay"] for p in group["params"]}
        self.assertEqual(decayed, {id(model.dense.weight)})
        self.assertTrue(all(group["foreach"] is False for group in optimizer.param_groups))

    def test_general_encoder_load_is_exact_and_new_qa_head_is_seeded(self):
        from transformers import RobertaConfig, RobertaForMaskedLM
        config = RobertaConfig(vocab_size=32, hidden_size=16, num_hidden_layers=1, num_attention_heads=2,
                               intermediate_size=24, max_position_embeddings=18)
        with TemporaryDirectory() as tmp:
            original = RobertaForMaskedLM(config)
            original.save_pretrained(tmp, safe_serialization=True)
            first, second = initialize_qa_model(tmp), initialize_qa_model(tmp)
            torch.testing.assert_close(first.qa_outputs.weight, second.qa_outputs.weight, rtol=0, atol=0)
            for name, value in first.roberta.state_dict().items():
                torch.testing.assert_close(value, original.roberta.state_dict()[name], rtol=0, atol=0)
            self.assertTrue(first.is_gradient_checkpointing)
            optimizer_update(first, make_optimizer(first), torch.amp.GradScaler("cuda", enabled=False),
                             [collate_windows([example(), example(1, ((0, 0),), 0)])], torch.device("cpu"))
            self.assertFalse(torch.equal(first.qa_outputs.weight, second.qa_outputs.weight))

    def test_partial_encoder_or_saved_qa_checkpoint_is_rejected(self):
        from safetensors.torch import load_file, save_file
        from transformers import RobertaConfig, RobertaForMaskedLM
        config = RobertaConfig(vocab_size=32, hidden_size=16, num_hidden_layers=1, num_attention_heads=2,
                               intermediate_size=24, max_position_embeddings=18)
        with TemporaryDirectory() as tmp:
            RobertaForMaskedLM(config).save_pretrained(tmp, safe_serialization=True)
            file = Path(tmp) / "model.safetensors"
            original = load_file(str(file))
            for mode in ("missing", "qa"):
                state = dict(original)
                if mode == "missing":
                    del state["roberta.embeddings.word_embeddings.weight"]
                else:
                    state["qa_outputs.weight"] = torch.zeros(2, 16)
                # Release the file mapping before replacing it on Windows.
                copied = {k: v.clone() for k, v in state.items()}
                del state
                if mode == "missing":
                    original = {k: v.clone() for k, v in original.items()}
                save_file(copied, str(file))
                with self.assertRaisesRegex(ValueError, "refusing partial"):
                    initialize_qa_model(tmp)

    def test_legacy_position_buffer_is_verified_before_omission(self):
        from safetensors.torch import load_file, save_file
        from transformers import RobertaConfig, RobertaForMaskedLM
        config = RobertaConfig(vocab_size=32, hidden_size=16, num_hidden_layers=1, num_attention_heads=2,
                               intermediate_size=24, max_position_embeddings=18)
        with TemporaryDirectory() as tmp:
            RobertaForMaskedLM(config).save_pretrained(tmp, safe_serialization=True)
            file = Path(tmp) / "model.safetensors"
            state = {k: v.clone() for k, v in load_file(str(file)).items()}
            state["roberta.embeddings.position_ids"] = torch.arange(18).unsqueeze(0)
            save_file(state, str(file))
            initialize_qa_model(tmp)
            state["roberta.embeddings.position_ids"][0, 3] = 0
            save_file(state, str(file))
            with self.assertRaisesRegex(ValueError, "position IDs"):
                initialize_qa_model(tmp)

    def test_completed_smoke_report_cannot_change_identity_or_claim_skipped_updates(self):
        identity = {"test": "identity"}
        report = {"identity": identity, "identity_sha256": canonical_sha256(identity),
                  "status": "training_smoke_passed", "updates": [
                      {"examples": 16, "mean_loss": 12., "gradient_norm_before_clip": 3.}] * 2,
                  "fit_windows_consumed": 32, "qa_head_changed": True, "encoder_probe_changed": True,
                  "full_training_completed": False, "checkpoint_saved": False}
        validate_saved_report(report, identity)
        for key, value in (("updates", report["updates"][:1]), ("qa_head_changed", False), ("full_training_completed", True)):
            changed = {**report, key: value}
            with self.assertRaises(ValueError):
                validate_saved_report(changed, identity)
        with self.assertRaises(ValueError):
            validate_saved_report(report, {"test": "different"})


if __name__ == "__main__":
    unittest.main()
