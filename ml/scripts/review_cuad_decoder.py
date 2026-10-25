"""Compare five fixed selectors on saved dev_select candidates, without inference.

Run: python ml/scripts/review_cuad_decoder.py
Reads the completed clean_training_v1 run's selected checkpoint and verified
frozen dev_select source. Hash-checks checkpoint files without deserializing
weights. Writes decoder_review_v1/report.json only; original scores/checkpoint
selection are unchanged. No training, calibration or operating-policy fitting.

All alternatives reuse the existing top-50 pool and fixed raw margin > 0.
This cannot undo per-window pruning, original NMS or the global candidate cap.
The top-one rule is a diagnostic, not a multi-answer replacement. Results are
development experiments, not held-out test estimates or a deployment policy.
"""

import argparse
from collections import Counter
import hashlib
import math
from pathlib import Path
import re

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
import cuad_checkpoints as checkpoints
from cuad_development import POLICY as ORIGINAL_POLICY, aggregate, interval_iou, match_counts
from freeze_cuad_splits import load_frozen_partition
from prepare_cuad_baseline import verify_file, verify_ignored_assets
from run_cuad_baseline import atomic_json, run_lock
from train_cuad import validate_progress

BASE = "data/processed/cuad"
VARIANTS = ("original", "top_one_diagnostic", "iou_0_5", "containment_0_8", "disjoint")
POLICY = {"version": 1, "partition": "dev_select", "candidate_source": "saved_top_50_after_original_nms",
          "margin_strictly_greater_than": 0.0, "variants": list(VARIANTS),
          "ties": "preserve_saved_candidate_order",
          "iou_0_5": "greedy_score_order_suppress_iou_at_least_0.5",
          "containment_0_8": "greedy_score_order_suppress_intersection_over_shorter_at_least_0.8",
          "disjoint": "greedy_score_order_suppress_any_positive_character_overlap",
          "gold_used_by_selector": False, "threshold_search": False,
          "automatic_adoption": False, "checkpoint_reselection": False}
LIMITATIONS = [
    "All variants use one checkpoint and the same already-pruned top-50 candidate pool.",
    "Discarded per-window, original-NMS and global-cap candidates cannot be recovered here.",
    "The original uncapped metrics are integrity-checked aggregates, not rescored uncapped candidates.",
    "Top-one may discard valid additional clauses; stronger suppression may discard nested valid answers.",
    "This is dev_select experimentation. The original checkpoint score and selection remain unchanged.",
    "No calibrated confidence, absence decision, deployment threshold or held-out test claim is produced.",
]
COUNT_KEYS = ("tp", "fp", "fn", "predicted", "gold", "original_gold_records", "exact_matches",
              "start_error_sum", "end_error_sum")


def same(actual, expected, message):
    require(canonical_sha256(actual) == canonical_sha256(expected), message)


def ordered(candidates):
    # Original exact-dedup can resolve a boundary flag after ordering. Preserve
    # its saved order within equal margins instead of inventing a new tie rule.
    return sorted(candidates, key=lambda c: -c["margin"])


def select_candidates(candidates, variant):
    """Use scores and geometry only. Never merge text or use gold/answer counts."""
    require(variant in VARIANTS, "Unknown decoder comparison variant.")
    values = ordered([c for c in candidates if c["margin"] > 0])
    if variant == "original":
        return values
    if variant == "top_one_diagnostic":
        return values[:1]
    kept = []
    for c in values:
        a, b = c["start"], c["end"]
        conflict = False
        for other in kept:
            x, y = other["start"], other["end"]
            overlap = max(0, min(b, y) - max(a, x))
            if variant == "iou_0_5":
                conflict = interval_iou((a, b), (x, y)) >= .5
            elif variant == "containment_0_8":
                conflict = overlap / min(b - a, y - x) >= .8
            else:
                conflict = overlap > 0
            if conflict:
                break
        if not conflict:
            kept.append(c)
    return kept


def source_questions(partition):
    require(partition["partition"] == "dev_select"
            and partition["intended_role"] == "checkpoint_and_decoder_selection", "Only dev_select may be compared.")
    result, groups = {}, set()
    for group in partition["groups"]:
        require(group["official_split"] == "train" and group["group_id"] not in groups,
                "Duplicate group or official-test source in decoder review.")
        groups.add(group["group_id"])
        for paragraph in group["paragraphs"]:
            context = paragraph["context"]
            for question in paragraph["questions"]:
                qid = question["question_id"]
                require(qid not in result and question["is_impossible"] is (not bool(question["answers"])),
                        "Repeated question or inconsistent answerability.")
                for answer in question["answers"]:
                    a, b = answer["start"], answer["end"]
                    require(type(a) is int and type(b) is int and 0 <= a < b <= len(context)
                            and context[a:b] == answer["text"], "Frozen gold text/offset differs.")
                result[qid] = {"category_id": question["category_id"], "group_id": group["group_id"],
                               "paragraph_index": paragraph["index"], "context": context, "gold": question["answers"]}
    require(bool(result), "No dev_select questions.")
    return result


def validate_counts(counts, original_gold):
    require(set(counts) == set(COUNT_KEYS)
            and all(type(v) is int and v >= 0 for v in counts.values()), "Invalid saved match counts.")
    require(counts["tp"] + counts["fp"] == counts["predicted"]
            and counts["tp"] + counts["fn"] == counts["gold"]
            and counts["exact_matches"] <= counts["tp"]
            and counts["original_gold_records"] == len(original_gold)
            and counts["gold"] == len({(a["start"], a["end"]) for a in original_gold}),
            "Saved match totals or gold denominator differ.")


def validate_reports(evaluation, progress, partition):
    """Reproduce original capped scoring and validate every saved source span."""
    same(evaluation["policy"], ORIGINAL_POLICY, "Unsupported original decoder policy.")
    require(evaluation["status"] == "complete_dev_select" and evaluation["selection_eligible"] is True
            and evaluation["calibration_performed"] is False and evaluation["deployment_decisions_produced"] is False,
            "Partial/probe or deployed evaluation cannot enter this review.")
    require(bool(progress["history"]) and progress["history"][-1]["evaluation_sha256"] == canonical_sha256(evaluation)
            and progress["history"][-1]["macro_f1"] == evaluation["selection"]["macro_f1"]
            and progress["best_score"] == evaluation["selection"]["macro_f1"],
            "Evaluation does not match selected checkpoint progress.")
    sources = source_questions(partition)
    predictions, saved = evaluation["predictions"], evaluation["per_question"]
    require(len(predictions) == len(saved) == evaluation["questions"] == len(sources), "Incomplete question coverage.")
    by_id = {r["question_id"]: r for r in saved}
    require(len(by_id) == len(saved) and set(by_id) == set(sources)
            and {p["question_id"] for p in predictions} == set(sources), "Duplicate, missing or foreign question IDs.")
    windows, cap_flags = 0, 0
    for prediction in predictions:
        qid = prediction["question_id"]
        source, row = sources[qid], by_id[qid]
        require(prediction["category_id"] == row["category_id"] == source["category_id"]
                and prediction["group_id"] == source["group_id"]
                and prediction["paragraph_index"] == source["paragraph_index"], "Prediction/source identity differs.")
        require(type(prediction["windows"]) is int and prediction["windows"] > 0
                and prediction["absence_allowed"] is False, "Invalid window count or deployment absence flag.")
        windows += prediction["windows"]
        count, candidates = prediction["uncapped_candidate_count"], prediction["candidates"]
        require(type(count) is int and count >= 0 and len(candidates) == min(count, 50)
                and prediction["truncated"] is (count >= 50), "Candidate cap metadata differs.")
        cap_flags += prediction["truncated"]
        intervals = set()
        for c in candidates:
            a, b = c["start"], c["end"]
            require(type(a) is int and type(b) is int and 0 <= a < b <= len(source["context"])
                    and c["text"] == source["context"][a:b], "Candidate text/offset differs from frozen source.")
            require((a, b) not in intervals, "Repeated exact candidate interval.")
            intervals.add((a, b))
            require(all(type(c[k]) in (int, float) and math.isfinite(c[k]) for k in ("margin", "null_score"))
                    and type(c["boundary_review"]) is bool, "Invalid candidate score or boundary flag.")
            require(all(type(c[k]) is int for k in ("window_row", "start_token", "end_token"))
                    and c["window_row"] >= 0 and 0 < c["start_token"] <= c["end_token"] < 512
                    and c["end_token"] - c["start_token"] + 1 <= 256, "Invalid candidate token indices.")
        require(candidates == ordered(candidates), "Candidate score/tie order differs.")
        for mode in ("selection", "unfiltered", "uncapped"):
            validate_counts(row[mode], source["gold"])
        same(match_counts(select_candidates(candidates, "original"), source["gold"]), row["selection"],
             "Original selected match counts did not reproduce.")
        same(match_counts(candidates, source["gold"]), row["unfiltered"], "Original capped match counts did not reproduce.")
        require(row["uncapped"]["predicted"] == count, "Uncapped count differs from metadata.")
    require(windows == evaluation["windows"] and cap_flags == evaluation["truncated_questions"], "Coverage totals differ.")
    for mode in ("selection", "unfiltered", "uncapped"):
        same(aggregate(saved, mode), evaluation[mode], f"Saved {mode} aggregate differs from question counts.")
    require(evaluation["cap_matched_gold_difference"] == evaluation["uncapped"]["micro"]["tp"]
            - evaluation["unfiltered"]["micro"]["tp"], "Cap match difference is inconsistent.")
    return sources


def breakdown(candidates, gold, tp):
    counts = Counter({"additional_eligible_overlaps": 0, "partial_overlap_only": 0, "zero_overlap": 0})
    eligible = 0
    for c in candidates:
        best = max((interval_iou((c["start"], c["end"]), (a["start"], a["end"])) for a in gold), default=0.)
        if best >= .5:
            eligible += 1
        else:
            counts["partial_overlap_only" if best > 0 else "zero_overlap"] += 1
    counts["additional_eligible_overlaps"] = eligible - tp
    return dict(counts)


def review_reports(evaluation, progress, partition):
    sources = validate_reports(evaluation, progress, partition)
    output = {}
    for variant in VARIANTS:
        rows, strata = [], {"no_gold": [], "one_gold": [], "multiple_gold": []}
        errors = Counter()
        positive_no_predictions, positive_no_matches, absent_with_predictions, boundary = 0, 0, 0, 0
        for prediction in evaluation["predictions"]:
            source = sources[prediction["question_id"]]
            selected = select_candidates(prediction["candidates"], variant)
            counts = match_counts(selected, source["gold"])
            row = {"question_id": prediction["question_id"], "category_id": source["category_id"], "result": counts}
            rows.append(row)
            strata["no_gold" if not counts["gold"] else "one_gold" if counts["gold"] == 1 else "multiple_gold"].append(row)
            positive_no_predictions += bool(counts["gold"] and not selected)
            positive_no_matches += bool(counts["gold"] and not counts["tp"])
            absent_with_predictions += bool(not counts["gold"] and selected)
            boundary += sum(c["boundary_review"] for c in selected)
            errors.update(breakdown(selected, source["gold"], counts["tp"]))
        summary = aggregate(rows, "result")
        require(sum(errors.values()) == summary["micro"]["fp"], "False-positive decomposition differs.")
        output[variant] = {"metrics": summary,
                           "strata": {k: aggregate(v, "result") if v else None for k, v in strata.items()},
                           "false_positive_breakdown": dict(errors), "boundary_review_predictions": boundary,
                           "positive_questions_with_no_predictions": positive_no_predictions,
                           "positive_questions_with_no_matches": positive_no_matches,
                           "absent_questions_with_predictions": absent_with_predictions,
                           "selected_span_count": summary["micro"]["predicted"]}
    multi = [v for v in VARIANTS if v != "top_one_diagnostic"]
    leading = max(multi, key=lambda v: output[v]["metrics"]["macro_f1"])
    return {"status": "development_decoder_comparison_only", "policy": POLICY, "limitations": LIMITATIONS,
            "questions": len(sources), "groups": len({s["group_id"] for s in sources.values()}),
            "original_windows": evaluation["windows"], "original_macro_f1": evaluation["selection"]["macro_f1"],
            "original_gold": evaluation["selection"]["micro"]["gold"],
            "candidate_cap_actually_removed_candidates_for_questions": sum(p["uncapped_candidate_count"] > 50 for p in evaluation["predictions"]),
            "original_pool_recall": {mode: evaluation[mode]["micro"]["recall"] for mode in ("selection", "unfiltered", "uncapped")},
            "variants": output, "leading_multispan_variant_for_review_only": leading,
            "decoder_adopted": False, "checkpoint_selection_changed": False,
            "model_inference_performed": False, "training_performed": False, "calibration_performed": False,
            "operating_policy_selected": False, "official_test_evaluated": False}


def load_checkpoint_reports(root):
    """Verify hashes, but never torch.load or change an existing training file."""
    identity = read_json(root / "identity.json")
    run_sha = canonical_sha256(identity)
    _, latest_manifest, latest_progress = checkpoints.latest(root, run_sha)
    validate_progress(latest_progress, identity["epoch_sizes"])
    require(latest_progress["completed"] is True, "Finish training before comparing its selected checkpoint.")
    name = latest_progress["best_checkpoint"]
    require(isinstance(name, str) and checkpoints.NAME.fullmatch(name), "Invalid selected checkpoint name.")
    directory = root / "checkpoints" / name
    manifest = read_json(directory / "manifest.json")
    require(manifest["checkpoint"] == name and manifest["run_sha256"] == run_sha
            and set(manifest["files"]) == {"training.pt", "progress.json", "evaluation.json"}, "Invalid selected checkpoint manifest.")
    if name != latest_manifest["checkpoint"]:
        for filename, spec in manifest["files"].items():
            verify_file(directory / filename, spec)
    else:
        same(manifest, latest_manifest, "Checkpoint manifest changed during review.")
    evaluation, progress = [read_json(directory / n) for n in ("evaluation.json", "progress.json")]
    validate_progress(progress, identity["epoch_sizes"])
    require(progress["best_checkpoint"] == name and progress["best_score"] == latest_progress["best_score"],
            "Selected checkpoint and completed run disagree.")
    same(identity["decoder_policy"], ORIGINAL_POLICY, "Training used a different original decoder.")
    code_hash = hashlib.sha256((Path(__file__).parent / "cuad_development.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    require(identity["code_sha256"]["cuad_development.py"] == code_hash, "Original scoring implementation changed.")
    return evaluation, progress, {"run_sha256": run_sha, "selected_checkpoint": name,
                                  "checkpoint_manifest_sha256": canonical_sha256(manifest),
                                  "latest_manifest_sha256": canonical_sha256(latest_manifest),
                                  "evaluation_sha256": canonical_sha256(evaluation), "progress_sha256": canonical_sha256(progress)}


def print_summary(report):
    print(f"Verified {report['questions']} dev_select questions, {report['groups']} groups and {report['original_gold']} gold spans.")
    print("Variant | precision | recall | macro F1 | emitted spans | multiple-gold recall")
    for name in VARIANTS:
        row = report["variants"][name]
        metrics, multi = row["metrics"], row["strata"]["multiple_gold"]
        def pct(value):
            return "n/a" if value is None else f"{100 * value:.3f}%"
        print(f"{name}: {pct(metrics['micro']['precision'])} | {pct(metrics['micro']['recall'])} | "
              f"{pct(metrics['macro_f1'])} | {row['selected_span_count']} | {pct(multi['micro']['recall'] if multi else None)}")
    print(f"Leading multi-span variant for review only: {report['leading_multispan_variant_for_review_only']}")
    print("PASS: saved-candidate comparison verified; no decoder adopted or checkpoint selection changed.")
    print("No inference, training, calibration, operating-policy selection or official-test scoring performed.")


def run(repo, training_run="clean_training_v1", output_run="decoder_review_v1"):
    require(all(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", n) for n in (training_run, output_run))
            and training_run != output_run, "Invalid or overlapping run names.")
    root, output = repo / BASE / training_run, repo / BASE / output_run
    require(root.is_dir(), "Completed training directory is missing.")
    verify_ignored_assets(repo, [f"{BASE}/{output_run}/report.json", f"{BASE}/{output_run}/run.lock"])
    with run_lock(root), run_lock(output):
        print("Verifying completed checkpoint hashes and saved development reports...", flush=True)
        evaluation, progress, binding = load_checkpoint_reports(root)
        print("Verifying frozen dev_select source and reproducing original metrics...", flush=True)
        partition = load_frozen_partition(repo, "dev_select")
        report = review_reports(evaluation, progress, partition)
        report["binding"] = {**binding, "frozen_dev_select_sha256": canonical_sha256(partition),
                             "producer_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()}
        created = atomic_json(output / "report.json", report)
    print("Created comparison report." if created else "Existing comparison report verified and reused.")
    print_summary(report)
    print(f"Report: {BASE}/{output_run}/report.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-run", default="clean_training_v1")
    parser.add_argument("--run-name", default="decoder_review_v1")
    args = parser.parse_args()
    run(Path(__file__).resolve().parents[2], args.training_run, args.run_name)


if __name__ == "__main__":
    main()
