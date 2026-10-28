"""The ONE predeclared boundary-selection experiment, CPU saved records only.

Run: python ml/scripts/experiment_cuad_decoder.py
No run-name, threshold or algorithm overrides. No model loading/inference.
All frozen producer files and the deployed candidate-only adapter stay intact.
"""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import importlib.metadata
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import numpy as np

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from cuad_checkpoints import file_spec
from cuad_development import aggregate, deduplicate, match_counts, summarize
from diagnose_cuad_scores import code_sha, score_curves, verify_validation_identity
from prepare_cuad_baseline import verify_file, verify_ignored_assets
from review_cuad_decoder import load_checkpoint_reports, same, select_candidates
from run_cuad_baseline import atomic_json, run_lock
from smoke_cuad_baseline import runtime_versions
import validate_cuad_decoder as validation

CONFIG = "ml/configs/cuad_decoder_boundary_v1.json"
CONFIG_PIN = "42add96675125ab1d27a1eb5d1e828a2178a545195994c3c0fd4a8747745c485"
SCORER_PIN = "3e5f2a3c1b4df15496fec51b57e4531a20cdc247fdf7ac902e3e434921a1809b"
ROOT = "data/processed/cuad/decoder_boundary_v1"
REFERENCE, CANDIDATE, ORIGINAL = "disjoint_full", "near_score_sentence_pack_v1", "original_capped"
VARIANTS = (REFERENCE, CANDIDATE, ORIGINAL)
INDIA = timezone(timedelta(hours=5, minutes=30))


def now_ist():
    return datetime.now(INDIA)


def read_policy(repo):
    policy = read_json(Path(repo) / CONFIG)
    require(canonical_sha256(policy) == CONFIG_PIN,
            "Predeclared experiment config changed. Do not start a second variant or sweep.")
    return policy


@lru_cache(maxsize=64)
def sentence_units(source, terminal_regex):
    """Heuristic source intervals, not a language model or annotation parser.

    No abbreviation exceptions, newline splitting, tokenization or normalization.
    Whitespace is skipped only when calculating unit starts; source is immutable.
    An unterminated final fragment never becomes a rescue unit.
    """
    units, previous = [], 0
    for match in re.finditer(terminal_regex, source):
        start, end = previous, match.end()
        while start < end and source[start].isspace():
            start += 1
        if any(c.isalnum() for c in source[start:end]):
            units.append((start, end))
        previous = end
    return tuple(units)


def sentence_pack(raw, source, policy):
    """Select ONLY existing candidates; no gold/category/document ID is passed."""
    rule = policy["algorithm"]
    values = [c for c in validation.exact_candidates(raw) if c["margin"] > 0]
    for c in values:
        require(type(c["start"]) is int and type(c["end"]) is int
                and 0 <= c["start"] < c["end"] <= len(source)
                and c["text"] == source[c["start"]:c["end"]], "Candidate source slice differs.")
    units = sentence_units(source, rule["sentence_terminal_regex"])
    starts = [a for a, _ in units]
    by_interval = {(c["start"], c["end"]): i for i, c in enumerate(values)}
    kept, replacements = [], 0
    selected_children = 0
    for index, parent in enumerate(values):
        a, b = parent["start"], parent["end"]
        if any(a < values[k]["end"] and b > values[k]["start"] for k in kept):
            continue
        children = []
        for left, right in units[bisect_left(starts, a):bisect_left(starts, b)]:
            child_index = by_interval.get((left, right))
            if right > b or child_index is None or child_index == index:
                continue
            child = values[child_index]
            gap = parent["margin"] - child["margin"]
            if (not child["boundary_review"] and rule["minimum_parent_minus_child_margin"] <= gap
                    <= rule["maximum_parent_minus_child_margin"]):
                children.append(child_index)
        if len(children) >= rule["minimum_eligible_sentence_children"]:
            kept.extend(children)
            replacements += 1
            selected_children += len(children)
        else:
            kept.append(index)
    # Restore raw-score order for whole-tie curves and the unchanged matcher.
    kept.sort(key=lambda i: (-values[i]["margin"], i))
    return [values[i] for i in kept], {"replaced_parent_spans": replacements,
                                      "sentence_children_selected": selected_children}


def feasible_point(point, policy):
    rule = policy["operating_point_comparison"]
    if point is None:
        return False
    m = point["micro"]
    return (m["predicted"] > 0 and m["gold"] > 0
            and m["tp"] * 100 >= rule["minimum_empirical_precision_percent"] * m["predicted"]
            and m["fp"] <= rule["maximum_false_highlights"])


def choose_point(curve, policy):
    eligible = [p for p in curve if feasible_point(p, policy)]
    return max(eligible, key=lambda p: (p["micro"]["recall"], p["micro"]["precision"],
               -p["micro"]["predicted"], p["minimum_margin"]), default=None)


def detail(tasks, pools, cutoff):
    rows, documents = [], defaultdict(Counter)
    strata = {"no_gold": [], "one_gold": [], "multiple_gold": []}
    for task, pool in zip(tasks, pools):
        kept = [] if cutoff is None else [c for c in pool if c["margin"] >= cutoff]
        counts = match_counts(kept, task["gold"])
        row = {"question_id": task["question_id"], "category_id": task["category_id"], "counts": counts}
        rows.append(row)
        strata["no_gold" if not counts["gold"] else "one_gold" if counts["gold"] == 1 else "multiple_gold"].append(row)
        documents[task["group_id"]].update(counts)
        documents[task["group_id"]]["questions"] += 1
    per_document = [{"group_id": g, "counts": summarize(c)} for g, c in sorted(documents.items())]
    distributions = {}
    for label, field in (("false_highlights", "fp"), ("missed_gold_spans", "fn"), ("returned_spans", "predicted")):
        values = np.array([d["counts"][field] for d in per_document])
        distributions[label] = {"mean": float(values.mean()), "p95": float(np.quantile(values, .95)),
                                "max": int(values.max())}
    return {"minimum_margin": cutoff, "metrics": aggregate(rows, "counts"),
            "strata": {k: aggregate(v, "counts") if v else None for k, v in strata.items()},
            "per_document": per_document, "document_distributions": distributions,
            "per_question": rows}


def multi_matches(details):
    value = details["strata"]["multiple_gold"]
    return value["micro"]["tp"] if value else 0


def gate(summaries, policy, *, integrity, in_time):
    reference, candidate = summaries[REFERENCE], summaries[CANDIDATE]
    checks = {"source_integrity": bool(integrity), "completed_by_deadline": bool(in_time),
              "reference_has_feasible_point": feasible_point(reference["point"], policy),
              "candidate_has_feasible_point": feasible_point(candidate["point"], policy)}
    gain = None
    if checks["reference_has_feasible_point"] and checks["candidate_has_feasible_point"]:
        r, c = reference["point"]["micro"], candidate["point"]["micro"]
        gain = c["tp"] - r["tp"]
        checks.update(extra_matched_gold_at_least_19=gain >= policy["operating_point_comparison"]["promotion_minimum_extra_matched_gold"],
                      no_exact_match_loss=c["exact_matches"] >= r["exact_matches"],
                      no_multiple_answer_match_loss=multi_matches(candidate["details"]) >= multi_matches(reference["details"]))
    passed = all(checks.values())
    return {"passed": passed, "checks": checks, "failed_checks": [k for k, v in checks.items() if not v],
            "extra_matched_gold": gain, "recommendation": CANDIDATE if passed else REFERENCE,
            "automatic_adoption": False,
            "meaning": "engineering_comparison_on_explored_dev_select_not_calibration_or_production_policy"}


def category_comparison(tasks, summaries):
    output = {}
    for cat in sorted({t["category_id"] for t in tasks}):
        relevant = [t for t in tasks if t["category_id"] == cat]
        gold = sum(len({(g["start"], g["end"]) for g in t["gold"]}) for t in relevant)
        positive = len({t["group_id"] for t in relevant if t["gold"]})
        at_point = {name: v["details"]["metrics"]["categories"][cat] if v["details"] else None
                    for name, v in summaries.items()}
        ref, candidate = at_point[REFERENCE], at_point[CANDIDATE]
        delta = {k: candidate[k] - ref[k] for k in ("tp", "fp", "fn", "exact_matches")} if ref and candidate else None
        output[cat] = {"gold_spans": gold, "positive_documents": positive,
                       "sparse_support": gold < 20 or positive < 10, "at_selected_global_points": at_point,
                       "candidate_minus_reference": delta,
                       "regression": (delta["tp"] < 0 or delta["fp"] > 0 or delta["exact_matches"] < 0) if delta else None,
                       "support_status_changed": False}
    return output


def load_pools(root, tasks, run_sha, saved_report, policy):
    expected = {f"{i:06d}.json" for i in range(len(tasks))}
    require({p.name for p in (root / "questions").glob("*.json")} == expected
            and set(saved_report["question_record_sha256"]) == expected, "Incomplete/foreign saved question records.")
    pools, changes = {n: [] for n in VARIANTS}, []
    for i, task in enumerate(tasks):
        name = f"{i:06d}.json"
        record = read_json(root / "questions" / name)
        raw = validation.validate_record(record, task, run_sha)
        require(record["payload_sha256"] == saved_report["question_record_sha256"][name],
                "Candidate record differs from the completed validation report.")
        exact = validation.exact_candidates(raw)
        selected = {REFERENCE: select_candidates(exact, "disjoint"),
                    ORIGINAL: [c for c in deduplicate(raw)[:50] if c["margin"] > 0]}
        selected[CANDIDATE], stats = sentence_pack(raw, task["context"], policy)
        require(all(task["context"][c["start"]:c["end"]] == c["text"] for v in selected.values() for c in v),
                "Selected span differs from immutable source.")
        fields = ("start", "end", "margin")
        for variant, values in selected.items():
            pools[variant].append([{k: c[k] for k in fields} for c in values])
        if stats["replaced_parent_spans"]:
            changes.append({"question_id": task["question_id"], "category_id": task["category_id"], **stats})
        if (i + 1) % 100 == 0 or i + 1 == len(tasks):
            print(f"  verified/selected saved records: {i + 1}/{len(tasks)}", flush=True)
    return pools, changes


def check_coverage(tasks, policy):
    observed = {"questions": len(tasks), "gold_spans": sum(len({(g["start"], g["end"]) for g in t["gold"]}) for t in tasks),
                "documents": len({t["group_id"] for t in tasks}), "categories": len({t["category_id"] for t in tasks}),
                "windows": sum(t["end"] - t["begin"] for t in tasks)}
    same(observed, policy["expected_coverage"], "Expected complete dev_select coverage differs.")
    return observed


def cached_result(root, identity):
    manifest = read_json(root / "manifest.json")
    require(manifest["experiment_identity_sha256"] == canonical_sha256(identity)
            and set(manifest["files"]) == {"report.json", "curves.json"}, "Result manifest binding differs.")
    for name, spec in manifest["files"].items():
        verify_file(root / name, spec)
    report, curves = read_json(root / "report.json"), read_json(root / "curves.json")
    require(report["experiment_identity_sha256"] == curves["experiment_identity_sha256"] == canonical_sha256(identity)
            and report["curves_sha256"] == canonical_sha256(curves), "Result report/curve binding differs.")
    return report


def print_summary(report):
    for name, value in report["variants"].items():
        point = value["point"]
        if point is None:
            print(f"{name}: no feasible whole-tie point at precision >=90% and false highlights <=24")
            continue
        c = point["micro"]
        print(f"{name}: cutoff {point['minimum_margin']:.9g}; {c['tp']}/{c['gold']} matched; "
              f"P {100*c['precision']:.3f}%; R {100*c['recall']:.3f}%; FP {c['fp']}; "
              f"exact {c['exact_matches']}; multiple-answer matched {multi_matches(value['details'])}")
    decision = report["gate"]
    print(f"Gate: {'PASS' if decision['passed'] else 'FAIL'}; additional matches: {decision['extra_matched_gold']}")
    print(f"Recommendation: {decision['recommendation']}; failed checks: {decision['failed_checks']}")
    print(f"Category regressions: {report['category_regressions']}")
    print("One experiment complete. No automatic adoption, model inference, training, calibration or official-test scoring.")
    print(f"Report: {ROOT}/results/report.json")
    print(f"Identity: {ROOT}/identity.json")


def run(repo):
    repo = Path(repo)
    policy = read_policy(repo)
    require(code_sha(repo / "ml/scripts/diagnose_cuad_scores.py") == SCORER_PIN, "Frozen curve scorer changed.")
    deadline = datetime.fromisoformat(policy["freeze_deadline_ist"])
    root = repo / ROOT
    # Verification of a completed result remains allowed after the freeze date.
    require((root / "results").is_dir() or now_ist() <= deadline,
            "October 31 deadline passed. Retain disjoint_full; do not launch the experiment.")
    runtime = runtime_versions()
    require(importlib.metadata.version("scipy") == "1.17.0", "Use pinned scipy==1.17.0.")
    runtime["scipy"] = "1.17.0"
    training, features, saved = [repo / validation.BASE / name for name in
                                ("clean_training_v1", "features_v1", "decoder_validation_v1")]
    require(all(p.is_dir() for p in (training, features, saved)), "Missing completed local input run; do not regenerate it.")
    verify_ignored_assets(repo, [f"{ROOT}/{n}" for n in ("identity.json", "run.lock", "results/report.json", "results/curves.json", "results/manifest.json")])
    with ExitStack() as stack:
        for path in (features, training, saved, root):
            stack.enter_context(run_lock(path))
        print("Verifying selected checkpoint and frozen source/candidate bindings; no weights will be loaded...", flush=True)
        evaluation, progress, checkpoint = load_checkpoint_reports(training)
        require(checkpoint["selected_checkpoint"] == policy["checkpoint"], "Selected checkpoint changed.")
        tasks, feature_binding = validation.verify_inputs(repo, features, training, evaluation, progress)
        coverage = check_coverage(tasks, policy)
        saved_identity, saved_report = read_json(saved / "identity.json"), read_json(saved / "report.json")
        same(canonical_sha256(saved_identity), policy["validation_identity_sha256"], "Previously verified validation identity changed.")
        same(canonical_sha256(saved_report), policy["validation_report_sha256"], "Previously verified validation report changed.")
        run_sha = verify_validation_identity(repo, saved_identity, saved_report, checkpoint, feature_binding)
        identity = {"config": policy, "config_sha256": CONFIG_PIN, "runtime": runtime,
                    "checkpoint": checkpoint, "features": feature_binding, "validation_run_sha256": run_sha,
                    "validation_report_sha256": canonical_sha256(saved_report),
                    "experiment_code_sha256_lf": code_sha(repo / "ml/scripts/experiment_cuad_decoder.py"),
                    "scoring_code_sha256_lf": code_sha(repo / "ml/scripts/diagnose_cuad_scores.py")}
        # Immutable binding is written BEFORE candidate selection/curve results.
        atomic_json(root / "identity.json", identity)
        if (root / "results").exists():
            report = cached_result(root / "results", identity)
            print("Existing completed experiment verified and reused; no new comparison run.")
            print_summary(report)
            return report
        pools, changes = load_pools(saved, tasks, run_sha, saved_report, policy)
        summaries, curves = {}, {}
        for name in VARIANTS:
            print(f"Whole-tie comparison: {name}...", flush=True)
            baseline = detail(tasks, pools[name], 0.)
            if name != CANDIDATE:
                same(baseline["metrics"], saved_report["variants"][name]["metrics"], "Existing reference/comparison baseline changed.")
            curves[name] = score_curves(tasks, pools[name])
            same(curves[name]["global"][-1]["micro"], baseline["metrics"]["micro"], "Curve endpoint differs.")
            point = choose_point(curves[name]["global"], policy)
            selected = detail(tasks, pools[name], point["minimum_margin"]) if point else None
            if selected:
                same(selected["metrics"]["micro"], point["micro"], "Selected point rescoring differs.")
            summaries[name] = {"baseline": baseline, "point": point, "details": selected}
        completed = now_ist()
        comparison = category_comparison(tasks, summaries)
        curve_file = {"experiment_identity_sha256": canonical_sha256(identity), "variants": curves}
        report = {"status": "single_decoder_experiment_complete_review_pending", "coverage": coverage,
                  "experiment_identity_sha256": canonical_sha256(identity), "policy": policy,
                  "completed_at_ist": completed.isoformat(), "curves_sha256": canonical_sha256(curve_file),
                  "variants": summaries, "gate": gate(summaries, policy, integrity=True, in_time=completed <= deadline),
                  "categories": comparison, "category_regressions": [c for c, v in comparison.items() if v["regression"]],
                  "changed_questions": changes, "changed_question_count": len(changes),
                  "source_integrity_passed": True, "model_inference_performed": False, "training_performed": False,
                  "calibration_performed": False, "operating_policy_selected": False,
                  "decoder_adopted": False, "official_test_evaluated": False,
                  "limitations": ["Explored dev_select engineering result, not held-out generalization or guaranteed precision.",
                      "One-to-one character IoU scoring is unchanged; exact and multiple-answer matches are separate gates.",
                      "Sentence boundaries are a fixed punctuation heuristic; abbreviations, headings and multi-sentence answers can be mishandled.",
                      "No missing/negative-margin or pruned candidates can be recovered; no new span boundaries are generated.",
                      "Sparse category support and all category regressions are reported; no validated category status is created.",
                      "Failure, missing evidence or a late result retains the existing disjoint reference; no second variant."]}
        with TemporaryDirectory(prefix=".pending-results-", dir=root) as temp:
            destination = Path(temp) / "results"
            destination.mkdir()
            atomic_json(destination / "curves.json", curve_file)
            atomic_json(destination / "report.json", report)
            atomic_json(destination / "manifest.json", {"experiment_identity_sha256": canonical_sha256(identity),
                        "files": {n: file_spec(destination / n) for n in ("report.json", "curves.json")}})
            os.rename(destination, root / "results")
        print_summary(report)
        return report


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    run(Path(__file__).resolve().parents[2])
