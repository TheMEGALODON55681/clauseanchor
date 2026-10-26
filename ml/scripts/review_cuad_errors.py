"""Export source-grounded dev_select errors from the verified score diagnostic.

Run: python ml/scripts/review_cuad_errors.py
No inference or weight updates. Reproduce saved candidates and score diagnostics
before inspecting disjoint_full at its existing 90% exploratory target. Export
all false highlights and inexact matches, plus one missed gold occurrence per
category/observed candidate stage. Stage labels describe saved evidence, not
confirmed semantic causes. Outputs are immutable and safe to rerun.
"""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import hashlib
import importlib.metadata
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

import numpy as np
from scipy.optimize import linear_sum_assignment

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from cuad_development import aggregate, interval_iou, match_counts
import diagnose_cuad_scores as diagnostic
from review_cuad_decoder import load_checkpoint_reports, same
from run_cuad_baseline import atomic_json, run_lock
from prepare_cuad_baseline import verify_ignored_assets
from smoke_cuad_baseline import runtime_versions
import validate_cuad_decoder as validation

BASE = validation.BASE
STAGES = ("eligible_output_unmatched", "below_diagnostic_cutoff", "suppressed_by_disjoint",
          "nonpositive_saved_candidate", "no_eligible_saved_candidate")
POLICY = {
    "version": 1, "partition": "dev_select", "variant": "disjoint_full", "diagnostic_target_percent": 90,
    "matching": "existing_maximum_total_eligible_iou_assignment_iou_at_least_0.5",
    "gold": "unique_source_intervals_with_original_annotation_indices_retained",
    "miss_stage_order": list(STAGES), "miss_stage_labels_are_observations_not_confirmed_causes": True,
    "sample": "all_false_highlights_and_inexact_matches_one_miss_per_category_and_observed_stage",
    "miss_sample_order": "highest_eligible_disjoint_margin_then_best_raw_iou_then_raw_margin_then_question_and_span",
    "context_characters_each_side": 240, "maximum_other_category_hints": 3,
    "source_coordinates": "original_unicode_code_points_end_exclusive",
    "production_threshold_selected": False, "automatic_annotation_changes": False,
}
LIMITATIONS = [
    "This is a targeted dev_select review, not a random sample or held-out quality estimate.",
    "The 90% cutoff is reused from the development diagnostic; it is not a deployment policy.",
    "Matching uses IoU >= 0.5 and maximum total IoU, not maximum match count or exact boundaries.",
    "An evaluation false positive may expose annotation incompleteness; source review is still required.",
    "Other-category annotation overlap is a geometry hint, not proof of category confusion.",
    "Feature alignment describes complete training targets; an overlapping evaluation match can exist even when a complete target is unusable.",
    "Saved raw candidates retain per-window top-20 and 256-token limits. Missing raw candidates do not distinguish beam pruning from model scoring failure.",
    "Candidate-stage presence does not prove that changing that stage would recover a one-to-one match.",
    "Excerpts may omit definitions or cross-references elsewhere in a document; unresolved cases need more source context.",
    "No returned span is not proof of absence. No model, decoder, calibration, catalogue support or annotations are changed.",
]


def coordinates(span):
    return span["start"], span["end"]


def assignment(candidates, gold):
    """Expose the frozen scorer's assignments without changing its producer file."""
    unique = sorted({coordinates(g) for g in gold})
    pairs = []
    if candidates and unique:
        overlaps = np.array([[interval_iou(coordinates(c), g) for g in unique] for c in candidates])
        rows, cols = linear_sum_assignment(np.where(overlaps >= .5, overlaps, 0.), maximize=True)
        pairs = [(int(i), int(j)) for i, j in zip(rows, cols) if overlaps[i, j] >= .5]
    expected = match_counts(candidates, gold)
    observed = {"tp": len(pairs), "fp": len(candidates) - len(pairs), "fn": len(unique) - len(pairs),
                "predicted": len(candidates), "gold": len(unique), "original_gold_records": len(gold),
                "exact_matches": sum(coordinates(candidates[i]) == unique[j] for i, j in pairs),
                "start_error_sum": sum(abs(candidates[i]["start"] - unique[j][0]) for i, j in pairs),
                "end_error_sum": sum(abs(candidates[i]["end"] - unique[j][1]) for i, j in pairs)}
    same(observed, expected, "Error-review assignments differ from the frozen evaluator.")
    return unique, pairs


def overlap(c, span):
    return interval_iou(coordinates(c), span)


def eligible(values, span):
    return [c for c in values if overlap(c, span) >= .5]


def miss_stage(span, raw, selected, kept):
    if eligible(kept, span):
        return STAGES[0]
    if eligible(selected, span):
        return STAGES[1]
    if any(c["margin"] > 0 for c in eligible(raw, span)):
        return STAGES[2]
    if eligible(raw, span):
        return STAGES[3]
    return STAGES[4]


def snippet(context, span):
    a, b = span
    require(0 <= a < b <= len(context), "Review span is outside frozen source.")
    radius = POLICY["context_characters_each_side"]
    left, right = max(0, a - radius), min(len(context), b + radius)
    return {"start": a, "end": b, "text": context[a:b], "excerpt_start": left,
            "excerpt_end": right, "before": context[left:a], "after": context[b:right]}


def candidate_evidence(candidate, span, context):
    if candidate is None:
        return None
    return {**{k: candidate[k] for k in validation.COLUMNS},
            "iou_with_focus": overlap(candidate, span), "source": snippet(context, coordinates(candidate))}


def best_overlap(values, span):
    return max(values, key=lambda c: (overlap(c, span), c["margin"], -c["start"], -c["end"]), default=None)


def highest_eligible(values, span):
    return max(eligible(values, span), key=lambda c: c["margin"], default=None)


def source_metadata(task, source):
    """Source/audit bytes were hash-checked by verify_inputs before this read."""
    group = source["source_group"]
    require(group["group_id"] == task["group_id"] and group["official_split"] == "train"
            and canonical_sha256(group) == task["source_group_sha256"], "Review source binding differs.")
    questions = [(p, q) for p in group["paragraphs"] for q in p["questions"] if q["question_id"] == task["question_id"]]
    audits = [a for a in source["question_audit"] if a["question_id"] == task["question_id"]]
    require(len(questions) == len(audits) == 1, "Missing or duplicate source question/audit.")
    paragraph, question = questions[0]
    audit = audits[0]
    require(paragraph["context"] == task["context"] and paragraph["index"] == task["paragraph_index"]
            and question["category_id"] == audit["category_id"] == task["category_id"]
            and audit["window_range"] == [task["begin"], task["end"]], "Source question/audit identity differs.")
    same(question["answers"], task["gold"], "Source review gold changed.")
    require(len(audit["answers"]) == len(task["gold"])
            and [a["answer_index"] for a in audit["answers"]] == list(range(len(task["gold"]))),
            "Feature answer-audit coverage differs.")
    return {"source_titles": group.get("source_titles", []), "family_id": group["family_id"],
            "question": question["question"], "feature_audit": audit}


def feature_evidence(task, audit, span):
    return [a for gold, a in zip(task["gold"], audit["answers"]) if coordinates(gold) == span]


def coverage_label(evidence):
    require(bool(evidence), "Missed gold lacks a feature audit.")
    if any(a["usable_windows"] > 0 for a in evidence):
        return "complete_target_in_regular_windows"
    reasons = {a["reason"] for a in evidence}
    if "longer_than_256_tokens" in reasons:
        return "longer_than_256_tokens"
    if "unmapped_boundary" in reasons:
        return "unmapped_boundary"
    require(reasons == {None}, "Unexpected feature alignment reason.")
    return "no_regular_window_contains_complete_target"


def other_category_index(tasks):
    result = defaultdict(set)
    for t in tasks:
        for a in t["gold"]:
            result[t["group_id"], t["paragraph_index"]].add((t["category_id"], a["start"], a["end"]))
    return result


def make_case(kind, span, task, metadata, raw, selected, kept, other, prediction=None, matched_gold=None):
    context = task["context"]
    identifier = {"question_id": task["question_id"], "kind": kind, "span": list(span)}
    nearest = sorted({coordinates(a) for a in task["gold"]}, key=lambda g: (
        -interval_iou(span, g), max(0, g[0] - span[1], span[0] - g[1]), g))[:3]
    hints = [{"category_id": cat, "start": a, "end": b, "iou": interval_iou(span, (a, b))}
             for cat, a, b in other[task["group_id"], task["paragraph_index"]]
             if cat != task["category_id"] and interval_iou(span, (a, b)) >= .5]
    hints.sort(key=lambda h: (-h["iou"], h["category_id"], h["start"], h["end"]))
    raw_best, selected_best = best_overlap(raw, span), best_overlap(selected, span)
    raw_eligible, selected_eligible = highest_eligible(raw, span), highest_eligible(selected, span)
    result = {**identifier, "case_id": canonical_sha256(identifier)[:24],
              "group_id": task["group_id"], "paragraph_index": task["paragraph_index"],
              "category_id": task["category_id"], "source_titles": metadata["source_titles"],
              "family_id": metadata["family_id"], "question": metadata["question"],
              "source_context_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
              "focus": snippet(context, span), "review_status": "pending", "confirmed_error_cause": None,
              "all_question_gold_intervals": [list(g) for g in sorted({coordinates(a) for a in task["gold"]})],
              "nearest_same_category_gold": [snippet(context, g) for g in nearest],
              "other_category_annotation_overlaps": hints[:POLICY["maximum_other_category_hints"]],
              "other_category_annotation_overlap_count": len(hints),
              "best_saved_raw_overlap": candidate_evidence(raw_best, span, context),
              "best_disjoint_overlap": candidate_evidence(selected_best, span, context),
              "highest_scoring_eligible_raw": candidate_evidence(raw_eligible, span, context),
              "highest_scoring_eligible_disjoint": candidate_evidence(selected_eligible, span, context),
              "question_tokens": {k: metadata["feature_audit"][k] for k in ("original_question_tokens", "used_question_tokens")},
              "prediction": candidate_evidence(prediction, span, context),
              "matched_gold": snippet(context, matched_gold) if matched_gold else None}
    if kind == "missed_gold":
        stage = miss_stage(span, raw, selected, kept)
        evidence = feature_evidence(task, metadata["feature_audit"], span)
        result.update(observed_stage=stage, feature_alignment=evidence, complete_target_coverage=coverage_label(evidence))
        # The first overlapping kept span is the greedy suppression witness.
        suppressed = highest_eligible([c for c in validation.exact_candidates(raw) if c["margin"] > 0], span)
        witness = next((c for c in selected if suppressed is not None
                        and min(c["end"], suppressed["end"]) > max(c["start"], suppressed["start"])), None)
        result["overlapping_disjoint_output"] = candidate_evidence(witness, span, context) if stage == STAGES[2] else None
    return result


def miss_priority(case):
    selected, raw = case["highest_scoring_eligible_disjoint"], case["best_saved_raw_overlap"]
    return (-(selected["margin"] if selected else -float("inf")),
            -(raw["iou_with_focus"] if raw else 0.), -(raw["margin"] if raw else -float("inf")),
            case["question_id"], case["focus"]["start"], case["focus"]["end"])


def build_review(tasks, validation_root, validation_report, score_report):
    target = score_report["variants"][POLICY["variant"]]["targets"][str(POLICY["diagnostic_target_percent"])]["point"]
    require(target is not None, "The recorded 90% diagnostic target is unattainable; review the score report first.")
    cutoff = target["minimum_margin"]
    all_cases, samples, summaries, scored = [], {}, {}, []
    other = other_category_index(tasks)
    source_path, source = None, None
    for i, task in enumerate(tasks):
        if task["path"] != source_path:
            source_path, source = task["path"], read_json(task["path"] / "source.json")
        metadata = source_metadata(task, source)
        record = read_json(validation_root / "questions" / f"{i:06d}.json")
        require(record["payload_sha256"] == validation_report["question_record_sha256"][f"{i:06d}.json"],
                "Question record changed after diagnostic verification.")
        raw = validation.validate_record(record, task, validation_report["validation_run_sha256"])
        selected = validation.selections(raw)[0][POLICY["variant"]]
        kept = [c for c in selected if c["margin"] >= cutoff]
        gold, pairs = assignment(kept, task["gold"])
        matched_predictions, matched_gold = {i for i, _ in pairs}, {j for _, j in pairs}
        counts = match_counts(kept, task["gold"])
        scored.append({"category_id": task["category_id"], "counts": counts})
        category = summaries.setdefault(task["category_id"], {"counts": Counter(), "miss_stages": Counter(), "miss_feature_coverage": Counter()})
        category["counts"].update(counts)
        for j, c in enumerate(kept):
            if j not in matched_predictions:
                all_cases.append(make_case("false_highlight", coordinates(c), task, metadata, raw, selected, kept, other, c))
        for p, g in pairs:
            if coordinates(kept[p]) != gold[g]:
                all_cases.append(make_case("boundary_match", coordinates(kept[p]), task, metadata, raw, selected, kept, other, kept[p], gold[g]))
        for j, span in enumerate(gold):
            if j in matched_gold:
                continue
            case = make_case("missed_gold", span, task, metadata, raw, selected, kept, other)
            category["miss_stages"][case["observed_stage"]] += 1
            category["miss_feature_coverage"][case["complete_target_coverage"]] += 1
            key = task["category_id"], case["observed_stage"]
            if key not in samples or miss_priority(case) < miss_priority(samples[key]):
                samples[key] = case
        if (i + 1) % 100 == 0 or i + 1 == len(tasks):
            print(f"  traced source questions: {i + 1}/{len(tasks)}", flush=True)
    metrics = aggregate(scored, "counts")
    same(metrics, score_report["variants"][POLICY["variant"]]["targets"]["90"]["details"]["metrics"],
         "Error-review cutoff metrics differ from the saved diagnostic.")
    all_cases.extend(samples.values())
    all_cases.sort(key=lambda c: (c["kind"], c["category_id"], c["question_id"], c["span"]))
    stages, coverage = Counter(), Counter()
    for row in summaries.values():
        require(sum(row["miss_stages"].values()) == sum(row["miss_feature_coverage"].values()) == row["counts"]["fn"],
                "Missed-span census differs from evaluation.")
        stages.update(row["miss_stages"]); coverage.update(row["miss_feature_coverage"])
    kind_counts = Counter(c["kind"] for c in all_cases)
    require(kind_counts["false_highlight"] == metrics["micro"]["fp"]
            and kind_counts["boundary_match"] == metrics["micro"]["tp"] - metrics["micro"]["exact_matches"],
            "Error-review case coverage differs.")
    return {"minimum_margin_for_diagnostic_only": cutoff, "metrics": metrics,
            "missed_gold_by_observed_stage": {s: stages[s] for s in STAGES},
            "missed_gold_by_complete_target_coverage": dict(coverage), "categories": summaries,
            "case_counts": dict(kind_counts), "case_count": len(all_cases), "cases": all_cases}


def verify_score_diagnostic(repo, root, checkpoint, features, validation_report, tasks, pools, names):
    identity, report, curve_file = [read_json(root / n) for n in ("identity.json", "report.json", "curves.json")]
    expected_identity = {"policy": diagnostic.POLICY, "runtime": identity["runtime"], "checkpoint": checkpoint,
                         "features": features, "validation_run_sha256": validation_report["validation_run_sha256"],
                         "validation_report_sha256": canonical_sha256(validation_report),
                         "producer_sha256": diagnostic.code_sha(repo / "ml/scripts/diagnose_cuad_scores.py"), "input_runs": names}
    same(identity, expected_identity, "Saved score-diagnostic inputs or producer changed.")
    same(report["binding"], identity, "Score report identity differs.")
    require(report["diagnostic_identity_sha256"] == canonical_sha256(identity)
            and report["curves_sha256"] == canonical_sha256(curve_file), "Score-diagnostic digest differs.")
    require(report["status"] == "development_score_diagnostic_only", "Complete development score diagnostic required.")
    for key in ("model_inference_performed", "training_performed", "calibration_performed", "operating_policy_selected",
                "decoder_adopted", "official_test_evaluated"):
        require(report[key] is False, "Unexpected score-diagnostic action flag.")
    require(report["questions"] == len(tasks) and report["windows"] == validation_report["windows"]
            and report["groups"] == len({t["group_id"] for t in tasks}), "Score-diagnostic coverage differs.")
    same(report["policy"], diagnostic.POLICY, "Score-diagnostic policy differs.")
    same(report["limitations"], diagnostic.LIMITATIONS, "Score-diagnostic limitations differ.")
    reproduced, curves = diagnostic.diagnose(tasks, pools, validation_report)
    same(reproduced, report["variants"], "Saved score diagnostic did not reproduce.")
    same(curve_file, {"diagnostic_identity_sha256": canonical_sha256(identity), "policy": diagnostic.POLICY, "variants": curves},
         "Saved score curves did not reproduce.")
    return report


def fenced(value):
    # Source text can itself contain Markdown fences or HTML. Keep it literal.
    fence = "`" * max(3, 1 + max((len(m.group()) for m in re.finditer(r"`+", value)), default=0))
    return f"{fence}text\n{value}\n{fence}\n"


def render_review(report):
    review = report["review"]
    m = review["metrics"]["micro"]
    lines = ["# CUAD targeted source-span review", "", "Status: pending human review; no changes adopted.", "",
             f"Development diagnostic only: {m['tp']} matched, {m['fp']} false highlights, {m['fn']} missed gold spans.",
             "Counts below cover every question. Missed-span excerpts are a targeted sample.", "",
             "| Observed candidate stage | Missed spans |", "|---|---:|"]
    lines += [f"| {stage} | {count} |" for stage, count in review["missed_gold_by_observed_stage"].items()]
    lines += ["", "For each case, assess category meaning, annotation completeness, span boundaries and missing context.",
              "Do not treat automatic stage labels or other-category overlaps as confirmed causes.",
              "Record conclusions separately; keep this generated evidence unchanged.", "", "## Limitations", ""]
    lines += ["- " + limitation for limitation in LIMITATIONS]
    for c in review["cases"]:
        lines += ["", f"## {c['kind']} / {c['category_id']} / {c['case_id']}", "",
                  f"Question: `{c['question_id']}`", f"Group: `{c['group_id']}`", "", "Source title(s):", fenced("\n".join(c["source_titles"])),
                  "Category question:", fenced(c["question"]), f"Source offsets: [{c['focus']['start']}, {c['focus']['end']})", ""]
        if c["kind"] == "missed_gold":
            lines += [f"Observed stage: `{c['observed_stage']}`; complete-target coverage: `{c['complete_target_coverage']}`.", ""]
        lines += ["Context before:", fenced(c["focus"]["before"]), "Focus span:", fenced(c["focus"]["text"]),
                  "Context after:", fenced(c["focus"]["after"])]
        for key in ("prediction", "highest_scoring_eligible_disjoint", "best_saved_raw_overlap", "overlapping_disjoint_output"):
            value = c.get(key)
            if value:
                lines += [f"{key}: margin {value['margin']:.6f}; IoU with focus {value['iou_with_focus']:.3f}; "
                          f"source [{value['start']}, {value['end']}); boundary flag {value['boundary_review']}.", fenced(value["source"]["text"])]
        for gold in c["nearest_same_category_gold"]:
            lines += [f"Same-category annotated span [{gold['start']}, {gold['end']}):", fenced(gold["text"])]
        if c["matched_gold"]:
            gold = c["matched_gold"]
            lines += [f"Assigned gold span [{gold['start']}, {gold['end']}):", fenced(gold["text"])]
        if c["other_category_annotation_overlaps"]:
            lines += ["Other-category annotation overlaps (hints only):"]
            lines += [f"- {h['category_id']} [{h['start']}, {h['end']}), IoU {h['iou']:.3f}" for h in c["other_category_annotation_overlaps"]]
    return "\n".join(lines) + "\n"


def atomic_text(path, value):
    payload = value.encode("utf-8")
    if path.exists():
        require(path.read_bytes() == payload, f"Existing file differs; preserved: {path}")
        return
    temporary = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=".pending-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload); handle.flush(); os.fsync(handle.fileno())
        require(not path.exists(), "Review destination appeared; preserved.")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(repo, training_run="clean_training_v1", feature_run="features_v1", validation_run="decoder_validation_v1",
        diagnostic_run="score_diagnostic_v1", run_name="error_review_v1"):
    names = (training_run, feature_run, validation_run, diagnostic_run, run_name)
    require(all(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", n) for n in names) and len(set(names)) == 5,
            "Invalid or overlapping run names.")
    runtime = runtime_versions()
    require(importlib.metadata.version("scipy") == "1.17.0", "Use pinned scipy==1.17.0 for matching.")
    runtime["scipy"] = "1.17.0"
    training_root, feature_root, validation_root, diagnostic_root, root = [repo / BASE / n for n in names]
    require(all(p.is_dir() for p in (training_root, feature_root, validation_root, diagnostic_root)), "Required completed input run is missing.")
    verify_ignored_assets(repo, [f"{BASE}/{run_name}/{n}" for n in ("identity.json", "report.json", "review.md", "run.lock")])
    with ExitStack() as stack:
        for directory in (feature_root, training_root, validation_root, diagnostic_root, root):
            stack.enter_context(run_lock(directory))
        print("Verifying completed checkpoint, frozen features, saved candidates and score diagnostic...", flush=True)
        evaluation, progress, checkpoint = load_checkpoint_reports(training_root)
        tasks, features = validation.verify_inputs(repo, feature_root, training_root, evaluation, progress)
        validation_identity, validation_report = [read_json(validation_root / n) for n in ("identity.json", "report.json")]
        run_sha = diagnostic.verify_validation_identity(repo, validation_identity, validation_report, checkpoint, features)
        pools = diagnostic.load_pools(validation_root, tasks, run_sha, evaluation, validation_report)
        score_report = verify_score_diagnostic(repo, diagnostic_root, checkpoint, features, validation_report, tasks, pools,
                                              {"training": training_run, "features": feature_run, "validation": validation_run})
        del pools
        identity = {"policy": POLICY, "runtime": runtime, "diagnostic_report_sha256": canonical_sha256(score_report),
                    "diagnostic_identity_sha256": score_report["diagnostic_identity_sha256"],
                    "producer_sha256": diagnostic.code_sha(repo / "ml/scripts/review_cuad_errors.py"),
                    "input_runs": {"training": training_run, "features": feature_run, "validation": validation_run, "diagnostic": diagnostic_run}}
        diagnostic.bind_output(root, identity)
        print("PASS: saved candidates, complete score curves and diagnostic report reproduced.", flush=True)
        review = build_review(tasks, validation_root, validation_report, score_report)
        report = {"status": "development_source_error_review_pending", "policy": POLICY, "limitations": LIMITATIONS,
                  "binding": identity, "review_identity_sha256": canonical_sha256(identity),
                  "questions": len(tasks), "groups": len({t["group_id"] for t in tasks}), "review": review,
                  **{key: False for key in ("model_inference_performed", "training_performed", "decoder_adopted", "calibration_performed",
                                            "operating_policy_selected", "official_test_evaluated", "annotations_changed", "human_review_completed")}}
        atomic_json(root / "report.json", report)
        atomic_text(root / "review.md", render_review(report))
        print(f"Review cases: {review['case_count']}; {review['case_counts']}")
        for stage, count in review["missed_gold_by_observed_stage"].items():
            print(f"  {stage}: {count}")
        print("PASS: source-span review exported; semantic causes remain pending review.")
        print("No inference, training, decoder adoption, calibration, deployment-policy selection or official-test scoring performed.")
        print(f"Report: {BASE}/{run_name}/report.json\nReadable review: {BASE}/{run_name}/review.md")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag, default in (("training-run", "clean_training_v1"), ("feature-run", "features_v1"),
                          ("validation-run", "decoder_validation_v1"), ("diagnostic-run", "score_diagnostic_v1"), ("run-name", "error_review_v1")):
        parser.add_argument("--" + flag, default=default)
    args = parser.parse_args()
    try:
        run(Path(__file__).resolve().parents[2], **vars(args))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"FAIL: {error}\n")


if __name__ == "__main__":
    main()
