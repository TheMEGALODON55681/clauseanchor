"""Resumable clean CUAD training; default invocation performs only TWO updates.

First pilot: python ml/scripts/train_cuad.py --device cuda --max-new-steps 2
Resume pilot: same command plus --resume
Decoder probe: --device cuda --resume --probe-dev-select (one complete question)
Full training: --device cuda --resume --full (only after reviewing the pilot)

Three fixed epoch lists, effective batch 16, linear 10% warmup/decay, gradient
clipping and checkpointing. Evaluate ALL dev_select windows after each epoch;
select by macro anchored-span F1 at fixed raw margin > 0, patience 2. No
calibration or policy/test inference. Save at 250 updates or 15 minutes, epoch
boundaries, and invocation limits. Keep two checkpoints, protecting best/latest.
Ctrl+C or an error recovers from the last COMPLETE saved checkpoint; partial
optimizer updates are never saved. Code/settings changes are rejected except
the explicit, hash-allowlisted --recover-amp transition from commit 5ffbc47.
"""

import argparse
from contextlib import ExitStack
import hashlib
import importlib.metadata
import math
import os
from pathlib import Path
import random
import re
import time

import numpy as np
import torch

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
import cuad_checkpoints as checkpoints
from cuad_development import POLICY as DECODE_POLICY, evaluate
from cuad_training import (AMP_MAX_RETRIES, LOSS_POLICY, FitWindowDataset, collate_windows, initialize_qa_model,
                           make_optimizer, optimizer_update, verify_training_plan)
from prepare_cuad_baseline import verify_ignored_assets
from prepare_cuad_training_assets import CONFIG, MODEL_DIR, SOURCE_PIN, validate_config, verify_local_assets
from run_cuad_baseline import atomic_json, run_lock
from smoke_cuad_baseline import runtime_versions

POLICY = {"version": 2, "seed": 42, "epochs": 3, "effective_batch": 16, "learning_rate": 2e-5,
          "warmup_ratio": 0.10, "scheduler": "one_based_linear_warmup_then_linear_decay",
          "weight_decay": 0.01, "max_gradient_norm": 1.0, "gradient_checkpointing": True,
          "checkpoint_steps": 250, "checkpoint_seconds": 900, "keep_checkpoints": 2,
          "evaluation": "all_dev_select_windows_after_each_epoch", "early_stop_patience": 2,
          "selection_metric": "dev_select_macro_anchored_span_f1", "ties": "keep_earlier_best",
          "nonfinite_gradients": "bounded_amp_scale_backoff_same_batch_and_rng_otherwise_fail",
          "amp_max_retries": AMP_MAX_RETRIES, "loss": LOSS_POLICY}
BASE = "data/processed/cuad"

# LF-normalized source hashes from the user's confirmed pre-fix commit 5ffbc47.
# No runtime, source, sampling, decoder or hyperparameter change is allowed.
LEGACY_CODE_SHA256 = {
    "cuad_training.py": "a3c5e1faead396aa5830d2443289afcd33903bcc97e40bf8290347c6f77a4c45",
    "train_cuad.py": "a6d5fa7626b944803a0a2954de695299ee52fa212db4eae28c1509810b46b81e",
    "cuad_checkpoints.py": "184c644413c025af6bdfc3666a46a34ce3a744d79cea35f6378e7f94afc167c2",
    "cuad_development.py": "612d57db13d7a38e1e565e5416b00f0160208150d7ece557caa6804b1d52f3d1",
}
LEGACY_POLICY = {**{k: v for k, v in POLICY.items() if k != "amp_max_retries"},
                 "version": 1, "nonfinite_gradients": "fail_without_advancing_saved_progress"}


def resolve_execution(root, identity, resume=False, recover_amp=False):
    """Keep the original run identity; bind a specific recovery in a sidecar.

    This only prepares the sidecar. Publish it AFTER successful checkpoint
    verification/restoration. Old checkpoint bytes and identity stay unchanged.
    New checkpoints bind the active execution identity in their hashed manifest.
    """
    path = root / "identity.json"
    amendment_path = root / "amp_recovery.json"
    saved = read_json(path) if path.exists() else identity
    if saved == identity:
        require(not amendment_path.exists(), "Unexpected AMP recovery record for an unchanged run.")
        require(not recover_amp, "--recover-amp requires the saved pre-fix run from commit 5ffbc47.")
        return saved, None
    expected_legacy = {**identity, "policy": LEGACY_POLICY, "code_sha256": LEGACY_CODE_SHA256}
    require(resume and saved == expected_legacy,
            "Run inputs, code or settings changed beyond the supported AMP fix; existing progress preserved.")
    amendment = {"version": 1, "reason": "recover_fp16_gradient_overflow_from_5ffbc47",
                 "original_run_sha256": canonical_sha256(saved),
                 "execution_sha256": canonical_sha256(identity), "execution_identity": identity}
    if amendment_path.exists():
        require(read_json(amendment_path) == amendment,
                "AMP recovery record or active code/settings changed; existing progress preserved.")
    else:
        require(recover_amp, "This pre-fix checkpoint needs --resume --recover-amp once; no files changed.")
    return saved, amendment


def learning_rate(completed_steps, total_steps):
    require(type(completed_steps) is int and type(total_steps) is int and 0 <= completed_steps < total_steps,
            "Invalid scheduler position.")
    warmup = math.ceil(total_steps * 0.10)
    number = completed_steps + 1
    factor = number / warmup if number <= warmup else (total_steps - number + 1) / (total_steps - warmup)
    return 2e-5 * factor


def initial_progress():
    return {"epoch": 0, "offset": 0, "global_step": 0, "examples_seen": 0,
            "epoch_loss_sum": 0.0, "history": [], "best_score": None,
            "best_checkpoint": None, "bad_evaluations": 0, "completed": False}


def validate_progress(progress, epoch_sizes):
    for key in ("epoch", "offset", "global_step", "examples_seen", "bad_evaluations"):
        require(type(progress[key]) is int and progress[key] >= 0, "Invalid integer training progress.")
    epoch, offset = progress["epoch"], progress["offset"]
    require(epoch <= len(epoch_sizes) and (epoch < len(epoch_sizes) or offset == 0), "Invalid epoch cursor.")
    if epoch < len(epoch_sizes):
        require(offset <= epoch_sizes[epoch] and (offset % 16 == 0 or offset == epoch_sizes[epoch]), "Cursor is inside an optimizer update.")
    steps = sum(math.ceil(n / 16) for n in epoch_sizes[:epoch]) + math.ceil(offset / 16)
    require(progress["global_step"] == steps and progress["examples_seen"] == sum(epoch_sizes[:epoch]) + offset,
            "Saved steps/examples disagree with sample position.")
    require(len(progress["history"]) == epoch and math.isfinite(progress["epoch_loss_sum"]), "Invalid evaluation history/loss.")
    require(type(progress["completed"]) is bool and progress["completed"] == (epoch == len(epoch_sizes) or progress["bad_evaluations"] >= 2),
            "Completion flag disagrees with training position.")
    scores = [e["macro_f1"] for e in progress["history"]]
    require(all(isinstance(s, (int, float)) and not isinstance(s, bool) and math.isfinite(s) and 0 <= s <= 1 for s in scores),
            "Invalid selection score.")
    require((not scores and progress["best_score"] is None and progress["best_checkpoint"] is None)
            or (scores and progress["best_score"] == max(scores) and isinstance(progress["best_checkpoint"], str)),
            "Best checkpoint does not match selection history.")


def train_updates(model, optimizer, scaler, dataset, progress, total_steps, batch_size, device):
    """One completed effective batch, including a correctly weighted short tail."""
    start, stop = progress["offset"], min(progress["offset"] + 16, len(dataset))
    require(start < stop, "Epoch needs evaluation, not another update.")
    batches = [collate_windows([dataset[i] for i in range(left, min(left + batch_size, stop))])
               for left in range(start, stop, batch_size)]
    rate = learning_rate(progress["global_step"], total_steps)
    for group in optimizer.param_groups:
        group["lr"] = rate
    result = optimizer_update(model, optimizer, scaler, batches, device)
    # These counters advance only after a successful optimizer update.
    progress["offset"] = stop
    progress["global_step"] += 1
    progress["examples_seen"] += stop - start
    progress["epoch_loss_sum"] += result["mean_loss"] * (stop - start)
    return {**result, "learning_rate": rate}


def record_evaluation(progress, evaluation, epoch_size):
    require(evaluation["selection_eligible"] is True and evaluation["status"] == "complete_dev_select",
            "Partial/probe evaluation cannot select a checkpoint.")
    score = evaluation["selection"]["macro_f1"]
    require(score is not None and math.isfinite(score) and 0 <= score <= 1, "No supported checkpoint-selection score.")
    improved = progress["best_score"] is None or score > progress["best_score"]
    progress["history"].append({"epoch": progress["epoch"] + 1, "global_step": progress["global_step"],
                                "macro_f1": score, "mean_fit_loss": progress["epoch_loss_sum"] / epoch_size,
                                "evaluation_sha256": canonical_sha256(evaluation)})
    progress["best_score"] = score if improved else progress["best_score"]
    progress["bad_evaluations"] = 0 if improved else progress["bad_evaluations"] + 1
    progress["epoch"] += 1
    progress["offset"] = 0
    progress["epoch_loss_sum"] = 0.0
    progress["completed"] = progress["epoch"] == 3 or progress["bad_evaluations"] >= 2
    return improved


def run(repo, device_name="cuda", batch_size=2, eval_batch_size=4, feature_run="features_v1",
        plan_run="training_plan_v1", run_name="clean_training_v1", resume=False, limit=2, probe=False,
        recover_amp=False):
    require(device_name in ("cpu", "cuda") and batch_size in (1, 2) and eval_batch_size in (1, 2, 4), "Invalid batch/device settings.")
    require(limit is None or (type(limit) is int and limit > 0), "Step limit must be positive.")
    for name in (feature_run, plan_run, run_name):
        require(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", name) is not None, "Invalid run name.")
    require(len({feature_run, plan_run, run_name}) == 3, "Input and output directories must differ.")
    versions = runtime_versions()
    require(importlib.metadata.version("scipy") == "1.17.0", "Use pinned scipy==1.17.0 for matching.")
    versions["scipy"] = "1.17.0"
    require(device_name != "cuda" or torch.cuda.is_available(), "CUDA is unavailable.")
    device = torch.device(device_name)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    feature_root, plan_root, root = [repo / BASE / name for name in (feature_run, plan_run, run_name)]
    require(feature_root.is_dir() and plan_root.is_dir(), "Prepare features and epoch lists first.")
    verify_ignored_assets(repo, [f"{BASE}/{run_name}/{n}" for n in
                               ("identity.json", "latest.json", "run.lock", "checkpoints/checkpoint-000001/training.pt", "dev_probe_step_000004.json")])
    with ExitStack() as stack:
        for directory in (feature_root, plan_root, root):
            stack.enter_context(run_lock(directory))
        print("Verifying frozen features, saved samples and clean backbone...", flush=True)
        plan_manifest, payloads = verify_training_plan(repo, feature_root, plan_root)
        config = read_json(repo / CONFIG)
        validate_config(config)
        verify_local_assets(repo / MODEL_DIR, config)
        epochs = [payloads[f"epoch_{e}.json"]["global_fit_window_indices"] for e in range(1, 4)]
        sizes = list(map(len, epochs))
        total_steps = sum(math.ceil(n / 16) for n in sizes)
        identity = {"policy": POLICY, "decoder_policy": DECODE_POLICY, "source_config_sha256": SOURCE_PIN,
                    "plan_sha256": plan_manifest["plan_sha256"], "runtime": versions,
                    "feature_directory": feature_root.relative_to(repo).as_posix(),
                    "plan_directory": plan_root.relative_to(repo).as_posix(),
                    "device": device_name, "device_name": torch.cuda.get_device_name(0) if device_name == "cuda" else "CPU",
                    "device_capability": list(torch.cuda.get_device_capability(0)) if device_name == "cuda" else None,
                    "batch_size": batch_size, "gradient_accumulation": 16 // batch_size, "eval_batch_size": eval_batch_size,
                    "precision": "fp16_autocast" if device_name == "cuda" else "fp32", "attention": "sdpa",
                    "total_optimizer_steps": total_steps, "epoch_sizes": sizes, "bitwise_cuda_reproducibility_claimed": False,
                    "code_sha256": {name: hashlib.sha256((repo / "ml/scripts" / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                                    for name in ("cuad_training.py", "cuad_development.py", "cuad_checkpoints.py", "train_cuad.py")}}
        execution_sha = canonical_sha256(identity)
        original_identity, amendment = resolve_execution(root, identity, resume, recover_amp)
        run_sha = canonical_sha256(original_identity)
        has_saved = (root / "latest.json").exists()
        require(not has_saved or resume, "Saved training exists. Add --resume; never overwrite it.")
        require(not resume or has_saved, "No complete checkpoint to resume.")
        require(not probe or has_saved, "Save a training checkpoint before a decoder probe.")
        atomic_json(root / "identity.json", original_identity)
        print(f"Device: {identity['device_name']}; microbatch {batch_size}; accumulation {16 // batch_size}; "
              f"maximum {total_steps} optimizer steps; warmup {math.ceil(total_steps * .1)}", flush=True)
        model = initialize_qa_model(repo / MODEL_DIR).to(device)
        optimizer = make_optimizer(model)
        scaler = torch.amp.GradScaler("cuda", enabled=device_name == "cuda", init_scale=256.0)
        progress = (checkpoints.restore(root, run_sha, model, optimizer, scaler,
                                        execution_sha=execution_sha, allow_legacy=amendment is not None)
                    if has_saved else initial_progress())
        validate_progress(progress, sizes)
        if amendment is not None:
            atomic_json(root / "amp_recovery.json", amendment)
            print("Verified AMP recovery: original checkpoint restored; bounded same-batch retries enabled. "
                  "Original run identity preserved; new execution recorded in amp_recovery.json.", flush=True)
        if probe:
            path = root / f"dev_probe_step_{progress['global_step']:06d}.json"
            binding = {"run_sha256": run_sha, "checkpoint_manifest_sha256": read_json(root / "latest.json")["manifest_sha256"]}
            if path.exists():
                report = read_json(path)
                require(report["binding"] == binding and report["evaluation"]["selection_eligible"] is False, "Existing probe differs.")
            else:
                report = {"binding": binding, "evaluation": evaluate(model, feature_root, device, eval_batch_size, probe=True)}
                atomic_json(path, report)
            print(f"PASS: decoder probe completed {report['evaluation']['questions']} fixed question, "
                  f"all {report['evaluation']['windows']} windows; checkpoint selection unchanged.")
            print(f"Report: {path.relative_to(repo).as_posix()}")
            return progress
        if progress["completed"]:
            print(f"Training already complete. Selected checkpoint: {progress['best_checkpoint']}; macro F1 {progress['best_score']:.6f}")
            return progress
        starting_step = progress["global_step"]
        saved_step = starting_step if has_saved else -1
        last_save = time.monotonic()
        started = time.perf_counter()
        dataset, dataset_epoch = None, None
        try:
            while not progress["completed"]:
                epoch = progress["epoch"]
                if progress["offset"] == sizes[epoch]:
                    if dataset is not None:
                        dataset.close()
                        dataset, dataset_epoch = None, None
                    # Save the completed epoch before any lengthy development pass.
                    progress = checkpoints.save(root, run_sha, model, optimizer, scaler, progress,
                                                execution_sha=execution_sha)
                    print(f"Evaluating ALL dev_select questions after epoch {epoch + 1}...", flush=True)
                    evaluation = evaluate(model, feature_root, device, eval_batch_size)
                    improved = record_evaluation(progress, evaluation, sizes[epoch])
                    progress = checkpoints.save(root, run_sha, model, optimizer, scaler, progress, evaluation, improved,
                                                execution_sha=execution_sha)
                    validate_progress(progress, sizes)
                    saved_step, last_save = progress["global_step"], time.monotonic()
                    print(f"Epoch {epoch + 1}: macro anchored-span F1 {evaluation['selection']['macro_f1']:.6f}; "
                          f"new best: {improved}; consecutive non-improvements: {progress['bad_evaluations']}", flush=True)
                    continue
                if limit is not None and progress["global_step"] - starting_step >= limit:
                    break
                if dataset_epoch != epoch:
                    if dataset is not None:
                        dataset.close()
                    dataset = FitWindowDataset(feature_root, payloads["fit_index.json"]["shards"], epochs[epoch])
                    dataset_epoch = epoch
                result = train_updates(model, optimizer, scaler, dataset, progress, total_steps, batch_size, device)
                if progress["global_step"] - starting_step <= 5 or progress["global_step"] % 10 == 0:
                    print(f"Step {progress['global_step']}/{total_steps}; epoch {epoch + 1}; windows {progress['offset']}/{sizes[epoch]}; "
                          f"loss {result['mean_loss']:.6f}; lr {result['learning_rate']:.9g}", flush=True)
                if progress["global_step"] % 250 == 0 or time.monotonic() - last_save >= 900:
                    progress = checkpoints.save(root, run_sha, model, optimizer, scaler, progress,
                                                execution_sha=execution_sha)
                    saved_step, last_save = progress["global_step"], time.monotonic()
            if progress["global_step"] != saved_step:
                progress = checkpoints.save(root, run_sha, model, optimizer, scaler, progress,
                                            execution_sha=execution_sha)
            validate_progress(progress, sizes)
        finally:
            if dataset is not None:
                dataset.close()
        print(f"New optimizer updates: {progress['global_step'] - starting_step}; total saved: {progress['global_step']}/{total_steps}")
        print(f"Fit windows consumed so far: {progress['examples_seen']}; training-loop seconds this invocation: {time.perf_counter() - started:.1f}")
        print(f"Best checkpoint: {progress['best_checkpoint']}" if progress["history"] else "Development selection pending: no full epoch evaluated yet.")
        print("PASS: completed training state saved; resume restores weights, optimizer, AMP scaler, RNG and sample position.")
        print(f"Training complete: {progress['completed']}; output: {root.relative_to(repo).as_posix()}")
        print("No calibration, policy selection or official-test inference performed.")
        return progress


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--batch-size", type=int, choices=(1, 2), default=2)
    parser.add_argument("--eval-batch-size", type=int, choices=(1, 2, 4), default=4)
    parser.add_argument("--feature-run", default="features_v1")
    parser.add_argument("--plan-run", default="training_plan_v1")
    parser.add_argument("--run-name", default="clean_training_v1")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--recover-amp", action="store_true",
                        help="Resume the exact pre-fix 5ffbc47 run with audited AMP overflow recovery.")
    parser.add_argument("--probe-dev-select", action="store_true")
    limit = parser.add_mutually_exclusive_group()
    limit.add_argument("--max-new-steps", type=int, default=2)
    limit.add_argument("--full", action="store_true")
    args = parser.parse_args()
    try:
        run(Path(__file__).resolve().parents[2], args.device, args.batch_size, args.eval_batch_size,
            args.feature_run, args.plan_run, args.run_name, args.resume,
            None if args.full else args.max_new_steps, args.probe_dev_select, args.recover_amp)
    except KeyboardInterrupt:
        raise SystemExit("Interrupted. No partial update was saved. Resume from the last complete checkpoint with --resume.")


if __name__ == "__main__":
    main()
