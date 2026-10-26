"""Resumable dev_select candidate collection before original NMS/top-50 pruning.

Default: two NEW questions, all their windows. Add --resume to reuse verified
question records; --full removes the new-question limit. Uses the completed
run's selected checkpoint without restoring an optimizer or changing weights.
The original top-20/window search and 256-token limit remain in place. This is
development experimentation, not decoder adoption or a deployment policy.
"""

import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import importlib.metadata
import math
import os
from pathlib import Path
import re

import numpy as np
import torch

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from cuad_development import aggregate, deduplicate, match_counts, window_candidates
from freeze_cuad_splits import FROZEN_DIR, load_frozen_partition
from prepare_cuad_baseline import verify_file, verify_ignored_assets
from prepare_cuad_features import POLICY as FEATURE_POLICY, ROLES, verify_shard
from prepare_cuad_training_assets import CONFIG, MODEL_DIR, SOURCE_PIN, validate_config, validate_model_metadata
from review_cuad_decoder import breakdown, load_checkpoint_reports, same, select_candidates, validate_reports
from run_cuad_baseline import atomic_json, run_lock
from smoke_cuad_baseline import runtime_versions

BASE = "data/processed/cuad"
COLUMNS = ("start", "end", "margin", "window_row", "start_token", "end_token", "null_score", "boundary_review")
FULL_RULES = {"top_one_full_diagnostic": "top_one_diagnostic", "iou_0_5_full": "iou_0_5",
              "containment_0_8_full": "containment_0_8", "disjoint_full": "disjoint"}
VARIANTS = ("original_capped", "original_uncapped", *FULL_RULES)
POLICY = {"version": 1, "partition": "dev_select", "candidate_source": "before_original_nms_and_top_50_cap",
          "top_start_end": 20, "per_window_candidates": 20, "max_answer_tokens": 256,
          "margin_strictly_greater_than": 0., "variants": list(VARIANTS),
          "exact_dedup": "original_score_and_boundary_tie_order_complete_counterpart_resolves_flag",
          "gold_used_by_selector": False, "threshold_search": False, "automatic_adoption": False}


def exact_candidates(raw):
    """Preserve original exact-dedup semantics without its overlap suppression."""
    complete = {(c["start"], c["end"]) for c in raw if not c["boundary_review"]}
    ordered = sorted(raw, key=lambda c: (-c["margin"], c["boundary_review"], c["start"], c["end"], c["window_row"]))
    result = {}
    for c in ordered:
        key = c["start"], c["end"]
        if key not in result:
            result[key] = {**c, "boundary_review": key not in complete}
    return list(result.values())


def selections(raw):
    original, exact = deduplicate(raw), exact_candidates(raw)
    result = {"original_capped": [c for c in original[:50] if c["margin"] > 0],
              "original_uncapped": [c for c in original if c["margin"] > 0]}
    result.update({name: select_candidates(exact, rule) for name, rule in FULL_RULES.items()})
    return result, original[:50]


def verify_inputs(repo, feature_root, training_root, evaluation, progress):
    partition = load_frozen_partition(repo, "dev_select")
    sources = validate_reports(evaluation, progress, partition)
    identity, manifest = [read_json(feature_root / n) for n in ("identity.json", "manifest.json")]
    identity_sha = canonical_sha256(identity)
    same(identity["policy"], FEATURE_POLICY, "Feature policy differs.")
    same(identity["partition_roles"], ROLES, "Feature partition roles differ.")
    require(identity["training_source_sha256"] == SOURCE_PIN
            and identity["frozen_manifest_sha256"] == canonical_sha256(read_json(repo / FROZEN_DIR / "manifest.json")),
            "Feature source/freeze binding differs.")
    require(manifest["complete"] is True and manifest["feature_identity_sha256"] == identity_sha,
            "Features incomplete or identity changed.")
    training = read_json(training_root / "identity.json")
    require(training["feature_directory"] == feature_root.relative_to(repo).as_posix()
            and training["source_config_sha256"] == SOURCE_PIN, "Training feature/source binding differs.")
    require(re.fullmatch(r"data/processed/cuad/[a-z0-9][a-z0-9_-]{0,47}", training["plan_directory"]), "Invalid training plan path.")
    plan = read_json(repo / training["plan_directory"] / "manifest.json")
    require(plan["plan_sha256"] == training["plan_sha256"] == canonical_sha256(plan["identity"])
            and plan["identity"]["feature_manifest_sha256"] == canonical_sha256(manifest)
            and plan["identity"]["feature_identity_sha256"] == identity_sha, "Trained feature/plan hashes differ.")
    groups, entries = partition["groups"], manifest["partitions"]["dev_select"]
    require(len(groups) == len(entries), "Missing development feature group.")
    tasks = []
    for group, entry in zip(groups, entries):
        group_sha = canonical_sha256(group)
        require(entry["path"] == f"dev_select/{group_sha[:24]}", "Feature shard order/path differs.")
        directory = feature_root / entry["path"]
        shard = verify_shard(directory, group, "dev_select", identity_sha)
        require(canonical_sha256(shard) == entry["manifest_sha256"], "Feature shard manifest changed.")
        same(shard["summary"], entry["summary"], "Feature shard counts differ.")
        questions = [q for p in group["paragraphs"] for q in p["questions"]]
        ranges = np.load(directory / "question_ranges.npy", allow_pickle=False)
        require(ranges.shape == (len(questions), 2), "Question range coverage differs.")
        previous = 0
        for question, (begin, end) in zip(questions, ranges.tolist()):
            require(begin == previous and end > begin, "Missing, overlapping or empty question windows.")
            previous = end
            qid = question["question_id"]
            binding = {"question_id": qid, "source_group_sha256": group_sha,
                       "shard_manifest_sha256": entry["manifest_sha256"], "begin": begin, "end": end}
            tasks.append({**sources[qid], **binding, "path": directory, "task_sha256": canonical_sha256(binding)})
        require(previous == shard["summary"]["windows"] and len(questions) == shard["summary"]["questions"],
                "Feature window/question totals differ.")
        print(f"  verified dev_select group {len(tasks)}/{len(sources)} questions", flush=True)
    require(len(tasks) == len(sources) and len({t["question_id"] for t in tasks}) == len(tasks)
            and sum(t["end"] - t["begin"] for t in tasks) == evaluation["windows"], "Development coverage differs.")
    windows = {p["question_id"]: p["windows"] for p in evaluation["predictions"]}
    require(all(t["end"] - t["begin"] == windows[t["question_id"]] for t in tasks), "Question window count changed.")
    return tasks, {"feature_manifest_sha256": canonical_sha256(manifest),
                   "frozen_dev_select_sha256": canonical_sha256(partition)}


class WindowMaps:
    def __init__(self):
        self.path, self.arrays = None, {}

    def close(self):
        for array in self.arrays.values():
            array._mmap.close()
        self.path, self.arrays = None, {}

    def get(self, path):
        if path != self.path:
            self.close()
            for name in ("input_ids", "attention_mask", "sequence_ids", "offsets"):
                self.arrays[name] = np.load(path / (name + ".npy"), mmap_mode="r", allow_pickle=False)
            self.path = path
        return self.arrays


def infer_question(model, task, arrays, device, batch_size):
    model.eval()
    raw, counts = [], []
    begin, end = task["begin"], task["end"]
    with torch.inference_mode():
        for offset in range(begin, end, batch_size):
            stop = min(offset + batch_size, end)
            ids = torch.tensor(np.array(arrays["input_ids"][offset:stop]), dtype=torch.long, device=device)
            mask = torch.tensor(np.array(arrays["attention_mask"][offset:stop]), dtype=torch.long, device=device)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                output = model(input_ids=ids, attention_mask=mask)
            starts, ends = output.start_logits.float().cpu().numpy(), output.end_logits.float().cpu().numpy()
            for j, row in enumerate(range(offset, stop)):
                values = window_candidates(starts[j], ends[j], arrays["sequence_ids"][row], arrays["offsets"][row],
                                           task["context"], row, row > begin, row < end - 1)
                raw.extend(values)
                counts.append(len(values))
    require(len(counts) == end - begin, "Incomplete question inference.")
    return raw, counts


def make_record(task, run_sha, raw, counts):
    payload = {"question_id": task["question_id"], "task_sha256": task["task_sha256"], "run_sha256": run_sha,
               "columns": list(COLUMNS), "window_counts": counts,
               "candidates": [[c[k] for k in COLUMNS] for c in raw]}
    return {"payload": payload, "payload_sha256": canonical_sha256(payload)}


def validate_record(record, task, run_sha):
    payload = record["payload"]
    require(record["payload_sha256"] == canonical_sha256(payload), "Question record checksum differs.")
    require(payload["question_id"] == task["question_id"] and payload["task_sha256"] == task["task_sha256"]
            and payload["run_sha256"] == run_sha and payload["columns"] == list(COLUMNS), "Question record identity differs.")
    counts, raw, observed = payload["window_counts"], [], Counter()
    require(len(counts) == task["end"] - task["begin"]
            and all(type(n) is int and 0 <= n <= 20 for n in counts), "Invalid per-window candidate counts.")
    seen, previous = set(), None
    for values in payload["candidates"]:
        require(isinstance(values, list) and len(values) == len(COLUMNS), "Invalid candidate columns.")
        c = dict(zip(COLUMNS, values))
        require(all(type(c[k]) is int for k in ("start", "end", "window_row", "start_token", "end_token"))
                and 0 <= c["start"] < c["end"] <= len(task["context"])
                and task["begin"] <= c["window_row"] < task["end"]
                and 0 < c["start_token"] <= c["end_token"] < 512
                and c["end_token"] - c["start_token"] < 256, "Invalid candidate coordinates.")
        require(all(type(c[k]) in (int, float) and math.isfinite(c[k]) for k in ("margin", "null_score"))
                and type(c["boundary_review"]) is bool, "Invalid candidate scores/flag.")
        key = (c["window_row"], -c["margin"], c["start"], c["end"], c["start_token"], c["end_token"])
        token_pair = c["window_row"], c["start_token"], c["end_token"]
        require((previous is None or previous <= key) and token_pair not in seen, "Candidate order or token pair differs.")
        previous = key
        seen.add(token_pair)
        observed[c["window_row"]] += 1
        raw.append({**c, "text": task["context"][c["start"]:c["end"]]})
    require(counts == [observed[i] for i in range(task["begin"], task["end"])], "Candidate counts differ from records.")
    return raw


def score_question(task, raw, reference):
    selected, capped = selections(raw)
    coordinate_fields = ("start", "end", "window_row", "start_token", "end_token", "boundary_review")
    old = reference["prediction"]["candidates"]
    coordinates_equal = [[c[k] for k in coordinate_fields] for c in capped] == [[c[k] for k in coordinate_fields] for c in old]
    variants = {name: {"counts": match_counts(values, task["gold"])} for name, values in selected.items()}
    for name, values in selected.items():
        variants[name].update({"errors": breakdown(values, task["gold"], variants[name]["counts"]["tp"]),
                               "boundary_predictions": sum(c["boundary_review"] for c in values)})
    return {"question_id": task["question_id"], "category_id": task["category_id"], "group_id": task["group_id"],
            "windows": task["end"] - task["begin"], "raw_candidates": len(raw), "exact_candidates": len(exact_candidates(raw)),
            "variants": variants, "original_replay": {
                "coordinates_equal": coordinates_equal,
                "scores_equal": coordinates_equal and all(c["margin"] == o["margin"] and c["null_score"] == o["null_score"] for c, o in zip(capped, old)),
                "max_margin_difference": max((abs(c["margin"] - o["margin"]) for c, o in zip(capped, old)), default=0.) if coordinates_equal else None,
                "counts_equal": variants["original_capped"]["counts"] == reference["row"]["selection"]}}


def aggregate_results(tasks, rows, original):
    require(set(rows) == set(range(len(tasks)))
            and all(rows[i]["question_id"] == task["question_id"] for i, task in enumerate(tasks)),
            "Full comparison requires every development question exactly once.")
    output = {}
    for name in VARIANTS:
        scored, strata, errors = [], {"no_gold": [], "one_gold": [], "multiple_gold": []}, Counter()
        absent, boundary = 0, 0
        for i in range(len(tasks)):
            v, row = rows[i]["variants"][name], rows[i]
            item = {"category_id": row["category_id"], "result": v["counts"]}
            scored.append(item)
            gold = v["counts"]["gold"]
            strata["no_gold" if not gold else "one_gold" if gold == 1 else "multiple_gold"].append(item)
            errors.update(v["errors"])
            absent += bool(not gold and v["counts"]["predicted"])
            boundary += v["boundary_predictions"]
        metrics = aggregate(scored, "result")
        require(sum(errors.values()) == metrics["micro"]["fp"], "False-positive decomposition differs.")
        output[name] = {"metrics": metrics, "strata": {k: aggregate(v, "result") if v else None for k, v in strata.items()},
                        "false_positive_breakdown": dict(errors), "absent_questions_with_predictions": absent,
                        "boundary_review_predictions": boundary}
    differences = {key: [rows[i]["question_id"] for i in range(len(tasks)) if not rows[i]["original_replay"][key]]
                   for key in ("coordinates_equal", "scores_equal", "counts_equal")}
    return {"status": "complete_dev_select_decoder_validation_for_review", "policy": POLICY,
            "questions": len(tasks), "windows": sum(t["end"] - t["begin"] for t in tasks),
            "original_macro_f1": original["selection"]["macro_f1"], "variants": output,
            "original_replay_differences": differences, "per_question": [rows[i] for i in range(len(tasks))],
            "limitations": ["Candidate search still uses top-20 starts/ends, top-20 pairs/window and a 256-token span limit.",
                            "Suppression may discard valid nested answers; top-one is a diagnostic only.",
                            "Raw margin > 0 is fixed and uncalibrated. These development scores are not held-out test estimates.",
                            "Fresh inference can differ numerically; inspect original replay differences before interpreting comparisons."],
            "decoder_adopted": False, "checkpoint_selection_changed": False, "model_inference_performed": True,
            "training_performed": False, "calibration_performed": False,
            "operating_policy_selected": False, "official_test_evaluated": False}


def process_questions(root, tasks, run_sha, producer, evaluation, limit=2):
    require(limit is None or (type(limit) is int and limit > 0), "New-question limit must be positive.")
    predictions = {p["question_id"]: p for p in evaluation["predictions"]}
    reference_rows = {p["question_id"]: p for p in evaluation["per_question"]}
    directory = root / "questions"
    directory.mkdir(parents=True, exist_ok=True)
    expected = {f"{i:06d}.json" for i in range(len(tasks))}
    require(all(p.name in expected for p in directory.glob("*.json")), "Foreign question record found.")
    rows, hashes = {}, {}
    # Verify ALL saved records before making any new model calls.
    for i, task in enumerate(tasks):
        path = directory / f"{i:06d}.json"
        if path.exists():
            record = read_json(path)
            raw = validate_record(record, task, run_sha)
            rows[i] = score_question(task, raw, {"prediction": predictions[task["question_id"]], "row": reference_rows[task["question_id"]]})
            hashes[path.name] = record["payload_sha256"]
    print(f"Verified saved questions: {len(rows)}/{len(tasks)}", flush=True)
    new = 0
    for i, task in enumerate(tasks):
        if i in rows or (limit is not None and new >= limit):
            continue
        raw, counts = producer(task)
        record = make_record(task, run_sha, raw, counts)
        raw = validate_record(record, task, run_sha)
        row = score_question(task, raw, {"prediction": predictions[task["question_id"]], "row": reference_rows[task["question_id"]]})
        atomic_json(directory / f"{i:06d}.json", record)
        rows[i], hashes[f"{i:06d}.json"] = row, record["payload_sha256"]
        new += 1
        replay = row["original_replay"]
        print(f"Saved question {i + 1}/{len(tasks)}: {row['windows']} windows; {len(raw)} raw candidates; "
              f"original coordinates/counts/scores match: {replay['coordinates_equal']}/{replay['counts_equal']}/{replay['scores_equal']}", flush=True)
    return rows, hashes


def load_model(config_path, checkpoint_dir, progress, binding, device):
    from transformers import RobertaConfig, RobertaForQuestionAnswering
    config = RobertaConfig.from_json_file(str(config_path))
    config.num_labels, config._attn_implementation = 2, "sdpa"
    model = RobertaForQuestionAnswering(config)
    payload = torch.load(checkpoint_dir / "training.pt", map_location="cpu", weights_only=True)
    manifest = read_json(checkpoint_dir / "manifest.json")
    require(payload["run_sha256"] == binding["run_sha256"], "Checkpoint run identity differs.")
    same(payload["progress"], progress, "Checkpoint progress differs.")
    require(payload.get("execution_sha256") == manifest.get("execution_sha256"), "Checkpoint execution identity differs.")
    model.load_state_dict(payload["model"], strict=True)
    del payload
    require(all(torch.isfinite(p).all().item() for p in model.parameters()), "Checkpoint contains non-finite weights.")
    return model.requires_grad_(False).to(device).eval()


def bind_run(root, identity, resume):
    path = root / "identity.json"
    if path.exists():
        same(read_json(path), identity, "Validation inputs/code/runtime/batch changed; use a separate --run-name.")
        require(resume or not any((root / "questions").glob("*.json")), "Saved questions exist; add --resume.")
    else:
        require(not resume, "No validation identity exists to resume.")
        require(not any(p.name != "run.lock" for p in root.iterdir()), "Nonempty output lacks its identity.")
        atomic_json(path, identity)
    return canonical_sha256(identity)


def run(repo, device_name="cuda", batch_size=4, training_run="clean_training_v1", feature_run="features_v1",
        run_name="decoder_validation_v1", resume=False, limit=2):
    names = (training_run, feature_run, run_name)
    require(all(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", n) for n in names)
            and len(set(names)) == 3, "Invalid or overlapping run names.")
    require(device_name in ("cpu", "cuda") and type(batch_size) is int and batch_size in (1, 2, 4), "Invalid device/batch size.")
    require(limit is None or (type(limit) is int and limit > 0), "New-question limit must be positive.")
    versions = runtime_versions()
    require(importlib.metadata.version("scipy") == "1.17.0", "Use pinned scipy==1.17.0.")
    versions["scipy"] = "1.17.0"
    require(device_name != "cuda" or torch.cuda.is_available(), "CUDA is unavailable.")
    device = torch.device(device_name)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.manual_seed(42)
    training_root, feature_root, root = [repo / BASE / n for n in names]
    require(training_root.is_dir() and feature_root.is_dir(), "Training/features directory missing.")
    verify_ignored_assets(repo, [f"{BASE}/{run_name}/{n}" for n in ("identity.json", "report.json", "run.lock", "questions/000000.json")])
    with ExitStack() as stack:
        for directory in (feature_root, training_root, root):
            stack.enter_context(run_lock(directory))
        print("Verifying completed checkpoint hashes, saved evaluation and frozen development features...", flush=True)
        evaluation, progress, checkpoint_binding = load_checkpoint_reports(training_root)
        tasks, feature_binding = verify_inputs(repo, feature_root, training_root, evaluation, progress)
        source_config = read_json(repo / CONFIG)
        validate_config(source_config)
        config_path = repo / MODEL_DIR / "config.json"
        verify_file(config_path, source_config["files"]["config.json"])
        validate_model_metadata(read_json(config_path))
        identity = {"policy": POLICY, "checkpoint": checkpoint_binding, "features": feature_binding,
                    "runtime": versions, "device": device_name, "batch_size": batch_size,
                    "hardware": torch.cuda.get_device_name(0) if device_name == "cuda" else "CPU",
                    "device_capability": list(torch.cuda.get_device_capability(0)) if device_name == "cuda" else None,
                    "precision": "fp16_autocast" if device_name == "cuda" else "fp32", "attention": "sdpa",
                    "bitwise_cuda_reproducibility_claimed": False,
                    "code_sha256": {p.name: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                                    for p in sorted((repo / "ml/scripts").glob("*.py"))}}
        run_sha = bind_run(root, identity, resume)
        model, maps = None, WindowMaps()
        def produce(task):
            nonlocal model
            if model is None:
                print(f"Loading selected weights: {checkpoint_binding['selected_checkpoint']}; evaluation only...", flush=True)
                model = load_model(config_path, training_root / "checkpoints" / checkpoint_binding["selected_checkpoint"],
                                   progress, checkpoint_binding, device)
            return infer_question(model, task, maps.get(task["path"]), device, batch_size)
        try:
            rows, hashes = process_questions(root, tasks, run_sha, produce, evaluation, limit)
        finally:
            maps.close()
        complete = len(rows) == len(tasks)
        if complete:
            report = aggregate_results(tasks, rows, evaluation)
            report.update({"validation_run_sha256": run_sha, "question_record_sha256": hashes})
            atomic_json(root / "report.json", report)
            for name, variant in report["variants"].items():
                m = variant["metrics"]
                def pct(v):
                    return "n/a" if v is None else f"{100 * v:.3f}%"
                print(f"{name}: P {pct(m['micro']['precision'])}; R {pct(m['micro']['recall'])}; macro F1 {pct(m['macro_f1'])}; spans {m['micro']['predicted']}")
            print("Original replay differences:", {k: len(v) for k, v in report["original_replay_differences"].items()})
            print(f"Report: {BASE}/{run_name}/report.json")
        else:
            require(not (root / "report.json").exists(), "Full report exists but question records are missing.")
        print(f"PASS: {len(rows)}/{len(tasks)} complete questions saved and verified; full comparison complete: {complete}")
        print("No training, decoder adoption, calibration, operating-policy selection or official-test inference performed.")
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--batch-size", type=int, choices=(1, 2, 4), default=4)
    parser.add_argument("--training-run", default="clean_training_v1")
    parser.add_argument("--feature-run", default="features_v1")
    parser.add_argument("--run-name", default="decoder_validation_v1")
    parser.add_argument("--resume", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--max-new-questions", type=int, default=2)
    group.add_argument("--full", action="store_true")
    args = parser.parse_args()
    try:
        run(Path(__file__).resolve().parents[2], args.device, args.batch_size, args.training_run, args.feature_run,
            args.run_name, args.resume, None if args.full else args.max_new_questions)
    except KeyboardInterrupt:
        print("Stopped. Completed question records are preserved; add --resume on the next invocation.")


if __name__ == "__main__":
    main()
