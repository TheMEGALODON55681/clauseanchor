"""Read-only score diagnostics on verified, completed dev_select candidates.

Run: python ml/scripts/diagnose_cuad_scores.py
Replays decoder_validation_v1 without model inference, then sweeps the positive
candidate pools of disjoint, original capped and diagnostic top-one decoders.
Writes score_diagnostic_v1/{identity,curves,report}.json. No calibrated model,
operating threshold, absence decision or production policy is created.
"""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import hashlib
import importlib.metadata
from itertools import groupby
from pathlib import Path
import re

import numpy as np

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from cuad_development import aggregate, match_counts, summarize
from review_cuad_decoder import COUNT_KEYS, load_checkpoint_reports, same
from run_cuad_baseline import atomic_json, run_lock
from prepare_cuad_baseline import verify_ignored_assets
from smoke_cuad_baseline import runtime_versions
import validate_cuad_decoder as validation

BASE = validation.BASE
VARIANTS = ("disjoint_full", "original_capped", "top_one_full_diagnostic")
TARGETS = (90, 95)
POLICY = {
    "version": 1, "partition": "dev_select", "variants": list(VARIANTS),
    "candidate_pool": "fixed_decoder_outputs_with_original_raw_margin_strictly_greater_than_zero",
    "score": "raw_start_plus_end_minus_window_null_score_not_a_probability",
    "cutoff": "include_margin_at_least_cutoff_with_whole_equal_score_groups",
    "curve": "every_distinct_positive_candidate_margin_plus_explicit_empty_output_point",
    "matching": "recompute_original_maximum_total_iou_assignment_for_each_changed_question",
    "diagnostic_precision_targets_percent": list(TARGETS),
    "diagnostic_point_choice": "max_recall_then_precision_then_fewer_outputs_then_higher_cutoff",
    "bootstrap": {"unit": "document_group", "replicates": 2000, "seed": 42,
                  "interval": "95_percent_percentile_conditional_on_fixed_cutoff",
                  "corrects_for_cutoff_selection_bias": False},
    "sparse_category_description": "fewer_than_20_gold_spans_or_10_positive_documents_not_a_release_rule",
    "production_threshold_selected": False, "calibration_fitted": False,
}
LIMITATIONS = [
    "Development diagnostics on the same dev_select data used for decoder review; not held-out performance.",
    "90% and 95% are empirical diagnostic targets, not guaranteed precision or release criteria.",
    "Best diagnostic points are selected on these data. Bootstrap intervals condition on that fixed cutoff and do not correct selection bias.",
    "Document bootstrap preserves within-document dependence; few documents or related templates can still make uncertainty estimates unreliable.",
    "A degenerate bootstrap interval after observing no errors is not evidence of guaranteed precision; resampling cannot reveal unobserved errors.",
    "Only the already selected positive-margin pools are filtered. Negative-margin, beam-pruned and unsupported answers are not recovered.",
    "Per-category target points are exploratory and are not combined into a category-specific deployment policy.",
    "No returned span is not an absence decision. False-highlight counts do not measure actual review time.",
    "Span correctness uses the existing one-to-one IoU criterion; exact boundaries are reported separately.",
]


def code_sha(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_validation_identity(repo, identity, report, checkpoint_binding, feature_binding):
    run_sha = canonical_sha256(identity)
    same(identity["policy"], validation.POLICY, "Saved candidate collection policy differs.")
    same(identity["checkpoint"], checkpoint_binding, "Saved candidate checkpoint binding differs.")
    same(identity["features"], feature_binding, "Saved candidate feature binding differs.")
    require(report["validation_run_sha256"] == run_sha, "Validation report/identity digest differs.")
    require(report["status"] == "complete_dev_select_decoder_validation_for_review"
            and report["model_inference_performed"] is True, "Complete validation report required.")
    for key in ("decoder_adopted", "checkpoint_selection_changed", "training_performed",
                "calibration_performed", "operating_policy_selected", "official_test_evaluated"):
        require(report[key] is False, "Unexpected adoption, training or evaluation flag in validation report.")
    code = identity["code_sha256"]
    require({"validate_cuad_decoder.py", "review_cuad_decoder.py", "cuad_development.py",
             "prepare_cuad_features.py", "cuad_checkpoints.py"} <= set(code), "Missing validation producer hashes.")
    # A newly added diagnostic script is allowed. Every script recorded by the
    # original run must still match; never rewrite that run's identity.
    for name, digest in code.items():
        require(re.fullmatch(r"[A-Za-z0-9_]+\.py", name) is not None, "Invalid saved producer path.")
        require(code_sha(repo / "ml/scripts" / name) == digest, f"Recorded validation producer changed: {name}")
    return run_sha


def load_pools(root, tasks, run_sha, evaluation, saved_report):
    directory = root / "questions"
    expected = {f"{i:06d}.json" for i in range(len(tasks))}
    require({p.name for p in directory.glob("*.json")} == expected
            and set(saved_report["question_record_sha256"]) == expected,
            "Incomplete or foreign saved question records; finish validation first.")
    predictions = {p["question_id"]: p for p in evaluation["predictions"]}
    original_rows = {row["question_id"]: row for row in evaluation["per_question"]}
    rows, hashes, pools = {}, {}, {name: [] for name in VARIANTS}
    for i, task in enumerate(tasks):
        filename = f"{i:06d}.json"
        record = read_json(directory / filename)
        raw = validation.validate_record(record, task, run_sha)
        require(record["payload_sha256"] == saved_report["question_record_sha256"][filename],
                "Question record digest differs from completed report.")
        reference = {"prediction": predictions[task["question_id"]], "row": original_rows[task["question_id"]]}
        rows[i] = validation.score_question(task, raw, reference)
        selected, _ = validation.selections(raw)
        for name in VARIANTS:
            # Text and token maps have already been checked by record/source
            # validation. Keep only scoring fields to bound memory usage.
            pools[name].append([{k: c[k] for k in ("start", "end", "margin")} for c in selected[name]])
        hashes[filename] = record["payload_sha256"]
        if (i + 1) % 100 == 0 or i + 1 == len(tasks):
            print(f"  verified saved candidates: {i + 1}/{len(tasks)} questions", flush=True)
    reproduced = validation.aggregate_results(tasks, rows, evaluation)
    reproduced.update(validation_run_sha256=run_sha, question_record_sha256=hashes)
    same(reproduced, saved_report, "Completed validation report did not reproduce from saved candidates.")
    require(all(not ids for ids in reproduced["original_replay_differences"].values()),
            "Original decoder replay differs; review that before score diagnostics.")
    return pools


def curve_point(counts, categories, cutoff, documents):
    supported = [2 * categories[k]["tp"] / (categories[k]["predicted"] + categories[k]["gold"])
                 for k in sorted(categories) if categories[k]["gold"]]
    return {"minimum_margin": cutoff, "selection": "none" if cutoff is None else "margin_at_least",
            "micro": summarize(counts), "macro_f1": sum(supported) / len(supported) if supported else None,
            "false_highlights_per_document": counts["fp"] / documents}


def score_curves(tasks, pools):
    """Sweep whole score ties; recompute matching, never freeze TP/FP labels.

    Unchanged questions retain their exact counts. This is equivalent to full
    rescoring at each global cutoff without rerunning unchanged assignments.
    """
    require(len(tasks) == len(pools) > 0 and len({t["question_id"] for t in tasks}) == len(tasks),
            "Invalid score-diagnostic question coverage.")
    counts = [match_counts([], t["gold"]) for t in tasks]
    total, categories, documents = Counter(), defaultdict(Counter), defaultdict(set)
    events = []
    for i, (task, candidates) in enumerate(zip(tasks, pools)):
        category = task["category_id"]
        total.update(counts[i]); total["questions"] += 1
        categories[category].update(counts[i]); categories[category]["questions"] += 1
        documents[category].add(task["group_id"])
        require(all(type(c["margin"]) in (int, float) and np.isfinite(c["margin"]) and c["margin"] > 0 for c in candidates),
                "Diagnostic accepts finite positive-margin saved pools only.")
        require(candidates == sorted(candidates, key=lambda c: -c["margin"]), "Candidate score order differs.")
        events.extend((c["margin"], i, c) for c in candidates)
    group_count = len({t["group_id"] for t in tasks})
    global_curve = [curve_point(total, categories, None, group_count)]
    category_curves = {cat: [curve_point(c, {cat: c}, None, len(documents[cat]))] for cat, c in sorted(categories.items())}
    selected = [[] for _ in tasks]
    events.sort(key=lambda event: -event[0])  # Stable ties preserve each pool's original order.
    for score, tied in groupby(events, key=lambda event: event[0]):
        changed, changed_categories = set(), set()
        for _, i, candidate in tied:
            selected[i].append(candidate)
            changed.add(i)
        for i in sorted(changed):
            category = tasks[i]["category_id"]
            current = match_counts(selected[i], tasks[i]["gold"])
            delta = {k: current[k] - counts[i][k] for k in COUNT_KEYS}
            total.update(delta); categories[category].update(delta)
            counts[i] = current
            changed_categories.add(category)
        global_curve.append(curve_point(total, categories, float(score), group_count))
        for category in sorted(changed_categories):
            c = categories[category]
            category_curves[category].append(curve_point(c, {category: c}, float(score), len(documents[category])))
    return {"global": global_curve, "by_category": category_curves}


def target_point(curve, percent):
    eligible = [p for p in curve if p["micro"]["predicted"] > 0 and p["micro"]["gold"] > 0
                and p["micro"]["tp"] * 100 >= percent * p["micro"]["predicted"]]
    if not eligible:
        return None
    return max(eligible, key=lambda p: (p["micro"]["recall"], p["micro"]["precision"],
                                       -p["micro"]["predicted"], p["minimum_margin"]))


def bootstrap_documents(documents, replicates=2000, seed=42):
    require(type(replicates) is int and replicates > 0, "Bootstrap replicates must be positive.")
    result = {"method": "document_cluster_percentile", "replicates": replicates, "seed": seed,
              "documents": len(documents), "confidence_level": .95,
              "conditional_on_fixed_cutoff": True, "selection_bias_corrected": False}
    if len(documents) < 2:
        return {**result, "status": "insufficient_documents", "intervals": None}
    data = np.array([[d["tp"], d["predicted"], d["gold"], d["fp"]] for d in documents], dtype=np.int64)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(documents), size=(replicates, len(documents)))
    totals = data[draws].sum(axis=1)
    intervals = {}
    for name, numerator, denominator in (("precision", totals[:, 0], totals[:, 1]),
                                          ("recall", totals[:, 0], totals[:, 2]),
                                          ("false_highlights_per_document", totals[:, 3], np.full(replicates, len(documents)))):
        valid = denominator > 0
        values = numerator[valid] / denominator[valid]
        intervals[name] = {"lower": float(np.quantile(values, .025)) if len(values) else None,
                           "upper": float(np.quantile(values, .975)) if len(values) else None,
                           "valid_replicates": int(valid.sum()), "undefined_replicates": int((~valid).sum())}
    return {**result, "status": "descriptive_only", "intervals": intervals}


def detailed_point(tasks, pools, cutoff):
    require(len(tasks) == len(pools) > 0, "Invalid detailed-point question coverage.")
    rows, documents = [], defaultdict(Counter)
    strata = {"no_gold": [], "one_gold": [], "multiple_gold": []}
    absent_with_predictions, positive_without_predictions = 0, 0
    for task, values in zip(tasks, pools):
        kept = [] if cutoff is None else [c for c in values if c["margin"] >= cutoff]
        counts = match_counts(kept, task["gold"])
        row = {"question_id": task["question_id"], "category_id": task["category_id"], "result": counts}
        rows.append(row)
        documents[task["group_id"]].update(counts)
        documents[task["group_id"]]["questions"] += 1
        strata["no_gold" if not counts["gold"] else "one_gold" if counts["gold"] == 1 else "multiple_gold"].append(row)
        absent_with_predictions += bool(not counts["gold"] and kept)
        positive_without_predictions += bool(counts["gold"] and not kept)
    document_rows = [{"group_id": key, "counts": summarize(value)} for key, value in sorted(documents.items())]
    distributions = {}
    for label, key in (("false_highlights", "fp"), ("missed_gold_spans", "fn"), ("returned_spans", "predicted")):
        values = np.array([row["counts"][key] for row in document_rows])
        distributions[label] = {"mean": float(values.mean()), "median": float(np.median(values)),
                                "p90": float(np.quantile(values, .9)), "p95": float(np.quantile(values, .95)),
                                "min": int(values.min()), "max": int(values.max())}
    return {"minimum_margin": cutoff, "metrics": aggregate(rows, "result"),
            "strata": {key: aggregate(value, "result") if value else None for key, value in strata.items()},
            "absent_questions_with_predictions": absent_with_predictions,
            "positive_questions_without_predictions": positive_without_predictions,
            "documents_with_predictions": sum(d["counts"]["predicted"] > 0 for d in document_rows),
            "documents_with_false_highlights": sum(d["counts"]["fp"] > 0 for d in document_rows),
            "documents_with_all_gold_and_no_extras": sum(d["counts"]["gold"] > 0 and d["counts"]["fn"] == d["counts"]["fp"] == 0 for d in document_rows),
            "document_distributions": distributions, "per_document": document_rows,
            "uncertainty": bootstrap_documents([d["counts"] for d in document_rows], **{
                k: POLICY["bootstrap"][k] for k in ("replicates", "seed")})}


def describe_target(curve, percent):
    point = target_point(curve, percent)
    nonempty = [p for p in curve if p["micro"]["predicted"]]
    highest = max(nonempty, key=lambda p: (p["micro"]["precision"], p["micro"]["tp"], -p["micro"]["predicted"]), default=None)
    return {"precision_target": percent / 100,
            "status": "attainable_on_dev_select_only" if point is not None else "unattainable_in_saved_positive_pool",
            "point": point, "highest_observed_precision_point": highest,
            "production_threshold_selected": False}


def diagnose(tasks, pools, saved_report):
    report, curves = {}, {}
    for name in VARIANTS:
        print(f"Sweeping saved scores: {name}...", flush=True)
        curve = score_curves(tasks, pools[name])
        baseline = detailed_point(tasks, pools[name], 0.)
        same(baseline["metrics"], saved_report["variants"][name]["metrics"], "Baseline aggregate changed during score diagnostic.")
        same(baseline["metrics"]["micro"], curve["global"][-1]["micro"], "Curve endpoint differs from full positive pool.")
        targets = {}
        for percent in TARGETS:
            entry = describe_target(curve["global"], percent)
            if entry["point"] is not None:
                entry["details"] = detailed_point(tasks, pools[name], entry["point"]["minimum_margin"])
                same(entry["details"]["metrics"]["micro"], entry["point"]["micro"], "Target cutoff rescoring differs.")
            targets[str(percent)] = entry
        categories = {}
        for category, points in curve["by_category"].items():
            relevant = [task for task in tasks if task["category_id"] == category]
            gold_documents = {task["group_id"] for task in relevant if task["gold"]}
            gold = points[-1]["micro"]["gold"]
            categories[category] = {
                "questions": len(relevant), "documents": len({task["group_id"] for task in relevant}),
                "gold_spans": gold, "positive_documents": len(gold_documents),
                "sparse_support_descriptive_flag": gold < 20 or len(gold_documents) < 10,
                "baseline": baseline["metrics"]["categories"][category],
                "own_category_diagnostic_targets": {str(p): describe_target(points, p) for p in TARGETS},
                "at_global_diagnostic_targets": {str(p): targets[str(p)]["details"]["metrics"]["categories"][category]
                                                  if "details" in targets[str(p)] else None for p in TARGETS},
                "support_status_changed": False,
            }
        report[name] = {"baseline": baseline, "targets": targets, "categories": categories,
                        "distinct_positive_score_groups": len(curve["global"]) - 1}
        curves[name] = curve
    return report, curves


def bind_output(root, identity):
    if (root / "identity.json").exists():
        same(read_json(root / "identity.json"), identity, "Diagnostic inputs/code/runtime changed; use a separate --run-name.")
    else:
        require(not any(p.name != "run.lock" for p in root.iterdir()), "Nonempty diagnostic output lacks its identity.")
        atomic_json(root / "identity.json", identity)


def print_summary(report):
    def pct(value):
        return "n/a" if value is None else f"{value * 100:.3f}%"
    for name in VARIANTS:
        value = report["variants"][name]
        baseline = value["baseline"]["metrics"]["micro"]
        print(f"{name}: baseline P {pct(baseline['precision'])}; R {pct(baseline['recall'])}; "
              f"{baseline['tp']}/{baseline['gold']} matched; {baseline['fp']} false highlights")
        for percent in TARGETS:
            target = value["targets"][str(percent)]
            point = target["point"]
            if point is None:
                print(f"  Target P >= {percent}%: UNATTAINABLE in the saved positive pool")
                continue
            m, details = point["micro"], target["details"]
            print(f"  Target P >= {percent}%: empirical P {pct(m['precision'])}; R {pct(m['recall'])}; "
                  f"exact R {pct(m['exact_match_recall'])}; {m['tp']}/{m['gold']} matched; "
                  f"{m['fp']} false; {m['predicted']} returned; {details['documents_with_predictions']}/{report['groups']} documents receive outputs")
            distribution = details["document_distributions"]["false_highlights"]
            print(f"    False highlights/document: mean {distribution['mean']:.3f}; p95 {distribution['p95']:.3f}; max {distribution['max']}")
            ci = details["uncertainty"]["intervals"]
            if ci is not None:
                p, recall = ci["precision"], ci["recall"]
                print(f"    Descriptive document-bootstrap intervals: P [{pct(p['lower'])}, {pct(p['upper'])}]; "
                      f"R [{pct(recall['lower'])}, {pct(recall['upper'])}] (fixed cutoff; selection bias not corrected)")
    print("PASS: saved-candidate score diagnostic complete; dev_select exploration only.")
    print("No inference, retraining, calibration fitting, deployment threshold selection or official-test scoring performed.")


def run(repo, training_run="clean_training_v1", feature_run="features_v1", validation_run="decoder_validation_v1",
        run_name="score_diagnostic_v1"):
    names = (training_run, feature_run, validation_run, run_name)
    require(all(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", n) for n in names)
            and len(set(names)) == 4, "Invalid or overlapping run names.")
    runtime = runtime_versions()
    require(importlib.metadata.version("scipy") == "1.17.0", "Use pinned scipy==1.17.0 for matching.")
    runtime["scipy"] = "1.17.0"
    training_root, feature_root, validation_root, root = [repo / BASE / name for name in names]
    require(all(path.is_dir() for path in (training_root, feature_root, validation_root)), "Required completed input run is missing.")
    verify_ignored_assets(repo, [f"{BASE}/{run_name}/{n}" for n in ("identity.json", "report.json", "curves.json", "run.lock")])
    with ExitStack() as stack:
        for directory in (feature_root, training_root, validation_root, root):
            stack.enter_context(run_lock(directory))
        print("Verifying checkpoint hashes and frozen development features; no model will be loaded...", flush=True)
        evaluation, progress, checkpoint_binding = load_checkpoint_reports(training_root)
        tasks, feature_binding = validation.verify_inputs(repo, feature_root, training_root, evaluation, progress)
        saved_identity = read_json(validation_root / "identity.json")
        saved_report = read_json(validation_root / "report.json")
        run_sha = verify_validation_identity(repo, saved_identity, saved_report, checkpoint_binding, feature_binding)
        identity = {"policy": POLICY, "runtime": runtime, "checkpoint": checkpoint_binding, "features": feature_binding,
                    "validation_run_sha256": run_sha, "validation_report_sha256": canonical_sha256(saved_report),
                    "producer_sha256": code_sha(repo / "ml/scripts/diagnose_cuad_scores.py"),
                    "input_runs": {"training": training_run, "features": feature_run, "validation": validation_run}}
        bind_output(root, identity)
        pools = load_pools(validation_root, tasks, run_sha, evaluation, saved_report)
        print("PASS: all saved question records and the complete decoder comparison reproduced.", flush=True)
        summaries, curves = diagnose(tasks, pools, saved_report)
        curve_file = {"diagnostic_identity_sha256": canonical_sha256(identity), "policy": POLICY, "variants": curves}
        report = {"status": "development_score_diagnostic_only", "policy": POLICY, "limitations": LIMITATIONS,
                  "binding": identity, "diagnostic_identity_sha256": canonical_sha256(identity),
                  "curves_sha256": canonical_sha256(curve_file), "questions": len(tasks),
                  "groups": len({t["group_id"] for t in tasks}), "windows": saved_report["windows"],
                  "variants": summaries, "model_inference_performed": False, "training_performed": False,
                  "calibration_performed": False, "operating_policy_selected": False,
                  "decoder_adopted": False, "official_test_evaluated": False}
        atomic_json(root / "curves.json", curve_file)
        atomic_json(root / "report.json", report)
        print_summary(report)
        print(f"Report: {BASE}/{run_name}/report.json")
        print(f"Curves: {BASE}/{run_name}/curves.json")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-run", default="clean_training_v1")
    parser.add_argument("--feature-run", default="features_v1")
    parser.add_argument("--validation-run", default="decoder_validation_v1")
    parser.add_argument("--run-name", default="score_diagnostic_v1")
    args = parser.parse_args()
    run(Path(__file__).resolve().parents[2], args.training_run, args.feature_run, args.validation_run, args.run_name)


if __name__ == "__main__":
    main()
