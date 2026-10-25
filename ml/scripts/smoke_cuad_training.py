"""Exercise clean CUAD training with TWO updates (32 fit windows), then stop.

Run: python ml/scripts/smoke_cuad_training.py --device cuda
Uses the existing pinned environment and local general RoBERTa assets. No
network access, new sampling, development evaluation or checkpoint selection.
Default microbatch 2, accumulation 8; --batch-size 1 uses accumulation 16.
Both test an effective batch of 16. CUDA uses FP16 autocast and GradScaler;
CPU uses FP32. Gradient checkpointing and AdamW foreach=False reduce memory.

Only a small ignored JSON report is saved. Smoke-updated weights are discarded;
full training will start from the unchanged pinned general backbone. This is
an actual optimization check, NOT a trained deliverable or accuracy assessment.
The smoke uses fixed LR 2e-5; the full scheduler/resume/evaluator are future work.
"""

import argparse
from contextlib import ExitStack
import hashlib
import math
import os
from pathlib import Path
import re
import time

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from prepare_cuad_baseline import verify_ignored_assets
from prepare_cuad_training_assets import CONFIG, MODEL_DIR, SOURCE_PIN, validate_config, verify_local_assets
from run_cuad_baseline import atomic_json, run_lock
from smoke_cuad_baseline import runtime_versions


BASE = "data/processed/cuad"
STEPS, EFFECTIVE_BATCH = 2, 16


def print_report(report, reused=False):
    print("Existing smoke report verified; no optimization repeated." if reused else "Created training smoke report.")
    print(f"Successful optimizer updates: {len(report['updates'])}; fit windows consumed: {report['fit_windows_consumed']}")
    print(f"QA head changed: {report['qa_head_changed']}; encoder probe changed: {report['encoder_probe_changed']}")
    print(f"Peak CUDA allocated/reserved: {report['peak_cuda_allocated_mib']:.1f}/{report['peak_cuda_reserved_mib']:.1f} MiB")
    print("PASS: fit-only loader, paired marginal loss, backward pass and optimizer updates verified.")
    print("Smoke weights discarded; pinned backbone unchanged. Full training, evaluation and calibration remain pending.")


def validate_saved_report(report, identity):
    require(report["identity"] == identity and report["identity_sha256"] == canonical_sha256(identity),
            "Existing smoke belongs to different code, inputs or settings; use a new --run-name.")
    require(report["status"] == "training_smoke_passed" and len(report["updates"]) == STEPS
            and report["fit_windows_consumed"] == STEPS * EFFECTIVE_BATCH
            and report["qa_head_changed"] is True and report["encoder_probe_changed"] is True
            and report["full_training_completed"] is False and report["checkpoint_saved"] is False,
            "Existing smoke report is incomplete.")
    for update in report["updates"]:
        require(update["examples"] == EFFECTIVE_BATCH and math.isfinite(update["mean_loss"])
                and math.isfinite(update["gradient_norm_before_clip"]) and update["gradient_norm_before_clip"] > 0,
                "Existing smoke report has invalid optimization results.")


def smoke(repo, device_name="cuda", batch_size=2, feature_run="features_v1",
          plan_run="training_plan_v1", run_name="training_smoke_v1"):
    import torch
    from torch.utils.data import DataLoader
    from cuad_training import (LOSS_POLICY, FitWindowDataset, collate_windows, initialize_qa_model,
                               make_optimizer, optimizer_update, verify_training_plan)
    require(device_name in ("cpu", "cuda") and type(batch_size) is int and batch_size in (1, 2), "Invalid smoke settings.")
    for name in (feature_run, plan_run, run_name):
        require(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", name) is not None, "Invalid run name.")
    require(len({feature_run, plan_run, run_name}) == 3, "Inputs and smoke output must have separate directories.")
    runtime = runtime_versions()
    require(device_name != "cuda" or torch.cuda.is_available(), "CUDA is unavailable in this environment.")
    device = torch.device(device_name)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    torch.manual_seed(42)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    config = read_json(repo / CONFIG)
    validate_config(config)
    feature_root, plan_root, output = [repo / BASE / name for name in (feature_run, plan_run, run_name)]
    require(feature_root.is_dir() and plan_root.is_dir(), "Prepare features and the training plan first.")
    verify_ignored_assets(repo, [f"{BASE}/{run_name}/report.json", f"{BASE}/{run_name}/run.lock"])
    with ExitStack() as stack:
        # Use the same input-lock order as the plan producer.
        for directory in (feature_root, plan_root, output):
            stack.enter_context(run_lock(directory))
        print("Verifying frozen features and all three saved epoch lists...", flush=True)
        manifest, payloads = verify_training_plan(repo, feature_root, plan_root)
        verify_local_assets(repo / MODEL_DIR, config)
        indices = payloads["epoch_1.json"]["global_fit_window_indices"][:STEPS * EFFECTIVE_BATCH]
        require(len(indices) == STEPS * EFFECTIVE_BATCH, "Insufficient epoch-1 samples for smoke.")
        identity = {"smoke_version": 1, "source_config_sha256": SOURCE_PIN,
                    "plan_sha256": manifest["plan_sha256"], "plan_directory": plan_root.relative_to(repo).as_posix(),
                    "runtime": runtime, "device": device_name,
                    "device_name": torch.cuda.get_device_name(0) if device_name == "cuda" else "CPU",
                    "device_capability": list(torch.cuda.get_device_capability(0)) if device_name == "cuda" else None,
                    "code_sha256": {name: hashlib.sha256((repo / "ml/scripts" / name).read_bytes()
                                                        .replace(b"\r\n", b"\n")).hexdigest()
                                    for name in ("cuad_training.py", "smoke_cuad_training.py")},
                    "seed": 42, "batch_size": batch_size, "gradient_accumulation": EFFECTIVE_BATCH // batch_size,
                    "optimizer_steps": STEPS, "learning_rate": 2e-5, "weight_decay": 0.01,
                    "max_gradient_norm": 1.0, "precision": "fp16_autocast" if device_name == "cuda" else "fp32",
                    "gradient_checkpointing": True, "attention": "sdpa", "loss": LOSS_POLICY,
                    "global_fit_window_indices": indices, "selection": "first_32_in_saved_epoch_1_order",
                    "bitwise_reproducibility_claimed": False, "scheduler": "none_smoke_only"}
        report_path = output / "report.json"
        if report_path.exists():
            report = read_json(report_path)
            validate_saved_report(report, identity)
            print_report(report, reused=True)
            return report
        dataset = FitWindowDataset(feature_root, payloads["fit_index.json"]["shards"], indices)
        stack.callback(dataset.close)
        # num_workers=0 avoids Windows worker duplication and open-memmap transfer.
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0,
                            collate_fn=collate_windows, drop_last=False)
        print("Pinned general backbone and fit-only samples: verified", flush=True)
        print(f"Device: {identity['device_name']}; {identity['precision']}; microbatch {batch_size}; "
              f"accumulation {identity['gradient_accumulation']}; effective batch {EFFECTIVE_BATCH}", flush=True)
        print("Initializing new QA head on the general RoBERTa backbone...", flush=True)
        model = initialize_qa_model(repo / MODEL_DIR).to(device)
        optimizer = make_optimizer(model)
        scaler = torch.amp.GradScaler("cuda", enabled=device_name == "cuda", init_scale=256.0)
        head = model.qa_outputs.weight
        encoder = model.roberta.encoder.layer[-1].output.dense.weight
        head_before, encoder_before = head.detach().cpu().clone(), encoder.detach().cpu().clone()
        if device_name == "cuda":
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
        begin, updates, consumed, statuses = time.perf_counter(), [], [], []
        iterator = iter(loader)
        for step in range(STEPS):
            batches = [next(iterator) for _ in range(identity["gradient_accumulation"])]
            for batch in batches:
                consumed.extend(batch["global_indices"])
                statuses.extend(batch["statuses"])
            result = optimizer_update(model, optimizer, scaler, batches, device)
            updates.append(result)
            print(f"Optimizer update {step + 1}/{STEPS}: mean loss {result['mean_loss']:.6f}; "
                  f"gradient norm {result['gradient_norm_before_clip']:.6f}; {result['examples']} fit windows", flush=True)
        require(consumed == indices and 0 in statuses and 1 in statuses, "Smoke order or positive/negative coverage differs.")
        head_changed = not torch.equal(head_before, head.detach().cpu())
        encoder_changed = not torch.equal(encoder_before, encoder.detach().cpu())
        require(head_changed and encoder_changed, "QA head or encoder failed to update.")
        require(all(torch.isfinite(p).all().item() for p in model.parameters()), "Optimizer created nonfinite weights.")
        if device_name == "cuda":
            torch.cuda.synchronize()
        report = {"identity": identity, "identity_sha256": canonical_sha256(identity), "status": "training_smoke_passed",
                  "updates": updates, "fit_windows_consumed": len(consumed),
                  "positive_windows": statuses.count(1), "negative_windows": statuses.count(0),
                  "qa_head_changed": head_changed, "encoder_probe_changed": encoder_changed,
                  "peak_cuda_allocated_mib": torch.cuda.max_memory_allocated() / 2**20 if device_name == "cuda" else 0.0,
                  "peak_cuda_reserved_mib": torch.cuda.max_memory_reserved() / 2**20 if device_name == "cuda" else 0.0,
                  "optimization_seconds": time.perf_counter() - begin,
                  "smoke_optimization_performed": True, "full_training_completed": False,
                  "checkpoint_saved": False, "development_evaluation_performed": False,
                  "calibration_performed": False, "baseline_reproduction_assessed": False}
        validate_saved_report(report, identity)
        atomic_json(report_path, report)
        print_report(report)
        print(f"Report: {report_path.relative_to(repo).as_posix()}")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--batch-size", type=int, choices=(1, 2), default=2)
    parser.add_argument("--feature-run", default="features_v1")
    parser.add_argument("--plan-run", default="training_plan_v1")
    parser.add_argument("--run-name", default="training_smoke_v1")
    args = parser.parse_args()
    try:
        smoke(Path(__file__).resolve().parents[2], args.device, args.batch_size, args.feature_run, args.plan_run, args.run_name)
    except Exception as error:
        import torch
        if isinstance(error, torch.cuda.OutOfMemoryError):
            raise SystemExit("CUDA ran out of memory. No trained checkpoint was saved. Close GPU-heavy apps and retry with "
                             "--batch-size 1 --run-name training_smoke_b1 (effective batch remains 16).") from error
        raise


if __name__ == "__main__":
    main()
