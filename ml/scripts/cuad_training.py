"""Fit-only CUAD loading, joint marginal loss and clean QA initialization.

Used by smoke_cuad_training.py; this module does not run training on import.
The caller holds the feature/plan locks and calls verify_training_plan once
before constructing datasets. NumPy maps are read-only; returned tensors own
copies. A small LRU bounds open shard files (including on Windows).
"""

from bisect import bisect_right
from collections import OrderedDict
import hashlib
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from prepare_cuad_training_plan import POLICY, audit_features, pools, same, sample_epoch


LOSS_POLICY = "negative_log_sum_of_unique_paired_start_end_probabilities_v1"


def verify_training_plan(repo, feature_root, plan_root):
    """Reconstruct saved evidence and all three epoch lists; never write data."""
    coverage, records, shards, bindings = audit_features(repo, feature_root)
    identity = {**bindings, "feature_directory": feature_root.relative_to(repo).as_posix(),
                "sampling_policy": POLICY,
                "producer_sha256": hashlib.sha256((repo / "ml/scripts/prepare_cuad_training_plan.py")
                                                   .read_bytes().replace(b"\r\n", b"\n")).hexdigest()}
    plan_sha = canonical_sha256(identity)
    _, _, _, skipped = pools(records)
    expected = {"coverage.json": {"plan_sha256": plan_sha, **coverage},
                "fit_index.json": {"plan_sha256": plan_sha, "shards": shards,
                                   "unsampled_positive_question_ids": skipped}}
    for epoch in range(1, 4):
        expected[f"epoch_{epoch}.json"] = {"plan_sha256": plan_sha, **sample_epoch(records, epoch)}
    manifest = {"status": "coverage_audited_fit_samples_prepared", "identity": identity,
                "plan_sha256": plan_sha, "files": {n: canonical_sha256(v) for n, v in expected.items()},
                "model_training_performed": False, "hard_negative_mining_performed": False,
                "baseline_reproduction_assessed": False}
    same(read_json(plan_root / "manifest.json"), manifest, "Training plan manifest differs; do not train.")
    for name, payload in expected.items():
        same(read_json(plan_root / name), payload, f"Training plan changed: {name}")
    return manifest, expected


class FitWindowDataset(Dataset):
    """Consume indices from a verified plan, without resampling or reshuffling."""

    def __init__(self, feature_root, shards, indices, cache_size=8):
        require(type(cache_size) is int and cache_size > 0, "Invalid shard cache size.")
        require(bool(shards) and bool(indices), "Empty fit dataset.")
        self.root, self.shards = Path(feature_root), shards
        self.indices = list(indices)
        self.ends, previous = [], 0
        for entry in shards:
            parts = entry["path"].split("/")
            require(len(parts) == 2 and parts[0] == "fit" and parts[1] not in ("", ".", "..")
                    and "\\" not in entry["path"], "Dataset accepts fit shard paths only.")
            start, end = entry["global_window_start"], entry["global_window_end"]
            require(type(start) is int and type(end) is int and start == previous < end,
                    "Fit index has a gap, overlap or invalid boundary.")
            self.ends.append(end)
            previous = end
        require(all(type(i) is int and 0 <= i < previous for i in self.indices)
                and len(set(self.indices)) == len(self.indices), "Invalid or repeated fit window index.")
        self.cache_size, self.cache = cache_size, OrderedDict()

    def __len__(self):
        return len(self.indices)

    def _arrays(self, shard_number):
        if shard_number not in self.cache:
            if len(self.cache) >= self.cache_size:
                _, old = self.cache.popitem(last=False)
                for array in old.values():
                    array._mmap.close()
            directory = self.root / self.shards[shard_number]["path"]
            arrays = {}
            try:
                for name in ("input_ids", "attention_mask", "window_index", "gold_pairs"):
                    arrays[name] = np.load(directory / (name + ".npy"), mmap_mode="r", allow_pickle=False)
            except Exception:
                for array in arrays.values():
                    array._mmap.close()
                raise
            self.cache[shard_number] = arrays
        self.cache.move_to_end(shard_number)
        return self.cache[shard_number]

    def __getitem__(self, position):
        global_index = self.indices[position]
        number = bisect_right(self.ends, global_index)
        row = global_index - self.shards[number]["global_window_start"]
        arrays = self._arrays(number)
        status = int(arrays["window_index"][row, 2])
        require(status in (0, 1), "Ignored window reached training.")
        all_pairs = arrays["gold_pairs"]
        left, right = np.searchsorted(all_pairs[:, 0], row, side="left"), np.searchsorted(all_pairs[:, 0], row, side="right")
        pairs = np.array(all_pairs[left:right, 1:], dtype=np.int64, copy=True)
        require(len(pairs) > 0 and ((status == 0 and pairs.tolist() == [[0, 0]])
                or (status == 1 and (pairs[:, 0] > 0).all())), "Invalid training target status.")
        return {"input_ids": torch.from_numpy(np.array(arrays["input_ids"][row], dtype=np.int64, copy=True)),
                "attention_mask": torch.from_numpy(np.array(arrays["attention_mask"][row], dtype=np.int64, copy=True)),
                "gold_pairs": torch.from_numpy(pairs), "global_index": global_index, "status": status}

    def close(self):
        for arrays in self.cache.values():
            for array in arrays.values():
                array._mmap.close()
        self.cache.clear()


def collate_windows(examples):
    require(bool(examples) and all(len(e["gold_pairs"]) > 0 for e in examples), "Empty training target.")
    width = max(len(e["gold_pairs"]) for e in examples)
    pairs = torch.zeros((len(examples), width, 2), dtype=torch.long)
    valid = torch.zeros((len(examples), width), dtype=torch.bool)
    for i, example in enumerate(examples):
        n = len(example["gold_pairs"])
        pairs[i, :n] = example["gold_pairs"]
        valid[i, :n] = True
    return {"input_ids": torch.stack([e["input_ids"] for e in examples]),
            "attention_mask": torch.stack([e["attention_mask"] for e in examples]),
            "gold_pairs": pairs, "pair_mask": valid,
            "global_indices": [e["global_index"] for e in examples],
            "statuses": [e["status"] for e in examples]}


def joint_marginal_loss(start_logits, end_logits, gold_pairs, pair_mask):
    """Mean -log sum P(start)*P(end) over UNIQUE annotated pairs per window.

    FP32 log-softmax/logsumexp stay stable under autocast. Denominators include
    all sequence positions, as in standard extractive QA. Padded gold pairs
    contribute no probability. Starts and ends are NEVER marginalized separately.
    The sole target for a negative window is (0, 0); ignore windows are absent.
    """
    require(start_logits.ndim == 2 and start_logits.shape == end_logits.shape
            and start_logits.shape[0] > 0 and start_logits.shape[1] > 0, "Invalid logit shape.")
    require(gold_pairs.ndim == 3 and gold_pairs.shape[0] == len(start_logits)
            and gold_pairs.shape[2] == 2 and pair_mask.shape == gold_pairs.shape[:2]
            and gold_pairs.dtype == torch.long and pair_mask.dtype == torch.bool, "Invalid paired targets.")
    require(torch.isfinite(start_logits).all().item() and torch.isfinite(end_logits).all().item(), "Nonfinite logits.")
    require(pair_mask.any(dim=1).all().item(), "Every window needs at least one gold pair.")
    selected = gold_pairs[pair_mask]
    require(((selected[:, 0] >= 0) & (selected[:, 0] <= selected[:, 1])
             & (selected[:, 1] < start_logits.shape[1])).all().item(), "Gold pair outside logits.")
    for row, mask in zip(gold_pairs, pair_mask):
        active = row[mask]
        require(len(torch.unique(active, dim=0)) == len(active), "Duplicate gold pair would inflate probability.")
        require(not (active[:, 0] == 0).any().item() or active.tolist() == [[0, 0]], "Null cannot mix with positive targets.")
    safe = gold_pairs.masked_fill(~pair_mask.unsqueeze(-1), 0)
    starts = torch.log_softmax(start_logits.float(), dim=-1).gather(1, safe[:, :, 0])
    ends = torch.log_softmax(end_logits.float(), dim=-1).gather(1, safe[:, :, 1])
    return -torch.logsumexp((starts + ends).masked_fill(~pair_mask, -torch.inf), dim=1).mean()


def initialize_qa_model(directory, seed=42):
    """Caller verifies pinned asset hashes first; require every encoder tensor."""
    from safetensors.torch import load_file
    from transformers import RobertaConfig, RobertaForQuestionAnswering
    torch.manual_seed(seed)
    config = RobertaConfig.from_json_file(str(Path(directory) / "config.json"))
    config.num_labels = 2
    config._attn_implementation = "sdpa"
    model = RobertaForQuestionAnswering(config)
    stored = load_file(str(Path(directory) / "model.safetensors"), device="cpu")
    # The pinned older checkpoint serialized this deterministic buffer. Modern
    # Transformers reconstructs it instead of including it in state_dict().
    position_ids = stored.pop("roberta.embeddings.position_ids", None)
    if position_ids is not None:
        require(position_ids.dtype == torch.long
                and torch.equal(position_ids, model.roberta.embeddings.position_ids),
                "Serialized position IDs differ from the model's deterministic buffer.")
    expected = {k for k in model.state_dict() if k.startswith("roberta.")}
    encoder = {k: v for k, v in stored.items() if k.startswith("roberta.")}
    require(set(encoder) == expected and all(k.startswith(("roberta.", "lm_head.")) for k in stored),
            "Backbone tensor keys differ; refusing partial loading or a task checkpoint.")
    loaded = model.load_state_dict(encoder, strict=False)
    require(set(loaded.missing_keys) == {"qa_outputs.weight", "qa_outputs.bias"}
            and not loaded.unexpected_keys, "Unexpected QA initialization result.")
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    return model


def make_optimizer(model):
    decay, no_decay = [], []
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            (no_decay if name.endswith(".bias") or "LayerNorm.weight" in name else decay).append(parameter)
    # foreach=False avoids an extra parameter-sized tensor list on a 4 GB GPU.
    return torch.optim.AdamW([{"params": decay, "weight_decay": 0.01},
                             {"params": no_decay, "weight_decay": 0.0}], lr=2e-5, foreach=False)


def optimizer_update(model, optimizer, scaler, microbatches, device):
    """Accumulate an example-weighted mean; never silently skip an AMP update."""
    require(bool(microbatches), "Empty optimizer update.")
    total = sum(len(b["input_ids"]) for b in microbatches)
    require(total > 0, "No training examples.")
    model.train()
    optimizer.zero_grad(set_to_none=True)
    mean_loss = 0.0
    for batch in microbatches:
        inputs = {k: batch[k].to(device) for k in ("input_ids", "attention_mask", "gold_pairs", "pair_mask")}
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=scaler.is_enabled()):
            output = model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"])
            loss = joint_marginal_loss(output.start_logits, output.end_logits, inputs["gold_pairs"], inputs["pair_mask"])
        require(torch.isfinite(loss).item(), "Nonfinite training loss.")
        weight = len(batch["input_ids"]) / total
        scaler.scale(loss * weight).backward()
        mean_loss += float(loss.detach()) * weight
    scaler.unscale_(optimizer)
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True, foreach=False)
    require(torch.isfinite(norm).item() and norm.item() > 0, "Gradients are nonfinite or zero; no optimizer step taken.")
    scale = scaler.get_scale()
    scaler.step(optimizer)
    scaler.update()
    require(scaler.get_scale() >= scale, "AMP skipped an update; smoke is incomplete.")
    optimizer.zero_grad(set_to_none=True)
    return {"mean_loss": mean_loss, "gradient_norm_before_clip": float(norm), "examples": total}
