"""Score the released CUAD predictions and compare with the original evaluator.

Install: python -m pip install -r ml/requirements-evaluation.txt
Run: python ml/scripts/evaluate_cuad_baseline.py
Requires previously prepared baseline assets and official source data. No
downloads, checkpoint loading, training or new inference occur in this script.

The benchmark uses word-set Jaccard, not ClauseAnchor's later character-span
metrics or calibrated confidence. Preserve the original evaluator's behavior:
literal-space tokens (including empty tokens), four punctuation removals,
case-sensitive Parties substring matching, credit for every annotated answer,
last probability for duplicate prediction text, strict threshold comparisons,
and the original NumPy threshold grid. P@recall omits the last curve point
because the original evaluator zips 102 curve points with 101 thresholds.
We preserve that quirk for parity; no operating threshold is selected here.

Report both the full official test and the reviewed known-overlap sensitivity
subset. The latter is not a guarantee of no unknown overlap. These scores use
the authors' saved predictions and do not complete fresh-inference parity.
"""

from contextlib import contextmanager
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform

from audit_cuad_categories import save_outputs
from audit_cuad_questions import require
from build_cuad_inventory import build_groups, load_sources
from check_cuad_families import canonical_sha256, read_json
from prepare_cuad_baseline import CONFIG, MODEL_DIR, REFERENCE_DIR, verify_file, verify_ignored_assets


SOURCE_PIN = "5e955b87316a118b22336c5c5aef5a9760d4f272f48456340c02ea47e82b07b0"
FAMILY_PIN = "382e22fc2d10b135951866761e80922829c58d79445fe0e51c57d31b1d781f6a"
FAMILY_PATH = "ml/configs/cuad_family_manifest.json"
PACKAGES = {"numpy": "2.3.5", "pandas": "2.2.3", "scikit-learn": "1.8.0", "scipy": "1.17.0"}
OUTPUTS = ("data/processed/cuad/baseline_evaluation.json", "data/processed/cuad/baseline_evaluation_curves.json")
TOLERANCE = 1e-12


def words(text):
    for punctuation in (".", ",", ";", ":"):
        text = text.replace(punctuation, "")
    return set(text.lower().replace("/", " ").split(" "))


def matches(answer, prediction, parties=False):
    a, p = words(answer), words(prediction)
    return len(a & p) / len(a | p) >= 0.5 or (parties and answer in prediction)


def prepare_matches(answers, predictions):
    """Precompute overlap once; threshold sweeps then use only probabilities."""
    require(set(answers) == set(predictions), "Prediction question IDs differ from evaluation questions.")
    prepared = []
    for qid, gold in answers.items():
        require(all(type(a) is str and a for a in gold), "Empty or invalid annotated answer.")
        by_text = {}
        for candidate in predictions[qid]:
            text, probability = candidate["text"], candidate["probability"]
            require(type(text) is str and type(probability) in (int, float)
                    and math.isfinite(probability) and 0 <= probability <= 1, "Invalid prediction candidate.")
            if text != "":
                by_text[text] = probability
        candidates = [(probability, {i for i, answer in enumerate(gold)
                                     if matches(answer, text, "Parties" in qid)})
                      for text, probability in by_text.items()]
        prepared.append((len(gold), candidates))
    return prepared


def count_at_threshold(prepared, threshold):
    tp = fp = fn = 0
    for answer_count, candidates in prepared:
        covered = set()
        for probability, matching_answers in candidates:
            if probability > threshold:
                covered.update(matching_answers)
                fp += not matching_answers
        tp += len(covered)
        fn += answer_count - len(covered)
    return {"tp": tp, "fp": fp, "fn": fn}


def precision_envelope(precisions):
    result = list(reversed(precisions))
    for i in range(1, len(result)):
        result[i] = max(result[i - 1], result[i])
    return list(reversed(result))


def summarize_curve(precisions, recalls):
    envelope = precision_envelope(precisions)
    area = sum((recalls[i + 1] - recalls[i]) * (envelope[i + 1] + envelope[i]) / 2
               for i in range(len(recalls) - 1))
    def precision_at(recall_target):
        # Preserve the original zip-length behavior, including the omitted last point.
        return next((p for p, r in zip(envelope[:-1], recalls[:-1]) if r >= recall_target), 0)
    return {"aupr": 0 if math.isnan(area) else area,
            "prec_at_80_recall": precision_at(.8), "prec_at_90_recall": precision_at(.9)}


def score_predictions(answers, predictions):
    import numpy as np
    thresholds = [float(x) for x in np.arange(0.99, 0, -0.01)] + [.001, 0]
    prepared = prepare_matches(answers, predictions)
    precisions, recalls, counts = [1.0], [0.0], []
    for threshold in thresholds:
        c = count_at_threshold(prepared, threshold)
        counts.append(c)
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        precisions.append(tp / (tp + fp) if tp + fp else math.nan)
        recalls.append(tp / (tp + fn) if tp + fn else math.nan)
    return {"metrics": summarize_curve(precisions, recalls), "precisions": precisions,
            "recalls": recalls, "thresholds": thresholds, "counts": counts}


def assert_parity(local, reference):
    errors = []
    def compare(a, b):
        if math.isnan(a) and math.isnan(b):
            return
        require(math.isfinite(a) and math.isfinite(b), "Official evaluator parity failed: finite/NaN disagreement.")
        errors.append(abs(a - b))
    for name in ("precisions", "recalls", "thresholds"):
        require(len(local[name]) == len(reference[name]), "Official evaluator parity failed: curve length.")
        for a, b in zip(local[name], reference[name]):
            compare(a, b)
    for name in ("aupr", "prec_at_80_recall", "prec_at_90_recall"):
        compare(local["metrics"][name], reference["metrics"][name])
    error = max(errors, default=0)
    require(error <= TOLERANCE, f"Official evaluator parity failed: maximum absolute difference {error}.")
    return error


def sensitivity_titles(groups, families):
    by_id = {g["group_id"]: g for g in groups}
    excluded, seen = set(), set()
    for family in families:
        ids = family["group_ids"]
        require(len(ids) >= 2 and len(set(ids)) == len(ids)
                and set(ids) <= set(by_id) and not (set(ids) & seen), "Invalid confirmed family membership.")
        seen.update(ids)
        if {by_id[g]["official_split"] for g in ids} == {"train", "test"}:
            excluded.update(ids)
    def titles(selected):
        return sorted(d["title"] for g in groups if g["official_split"] == "test"
                      and ((g["group_id"] in excluded) == selected) for d in g["source_documents"])
    return titles(False), titles(True)


@contextmanager
def directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def load_reference(repo, config):
    path = repo / REFERENCE_DIR
    for name in ("evaluate.py", "category_descriptions.csv"):
        verify_file(path / name, config["reference_files"][name])
    spec = importlib.util.spec_from_file_location("_cuad_pinned_reference", path / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    # The unmodified evaluator loads its category CSV relative to the working directory.
    with directory(path):
        spec.loader.exec_module(module)
    return module


def reference_score(reference, answers, predictions):
    precisions, recalls, thresholds = reference.get_precisions_recalls(predictions, answers)
    metrics = {"aupr": float(reference.get_aupr(precisions, recalls)),
               "prec_at_80_recall": float(reference.get_prec_at_recall(precisions, recalls, thresholds, .8)[0]),
               "prec_at_90_recall": float(reference.get_prec_at_recall(precisions, recalls, thresholds, .9)[0])}
    return {"metrics": metrics, "precisions": precisions, "recalls": recalls, "thresholds": thresholds}


def finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: finite_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_json(v) for v in value]
    return value


def evaluate(repo):
    installed = {name: importlib.metadata.version(name) for name in PACKAGES}
    require(installed == PACKAGES, "Evaluation package versions differ. Run: python -m pip install -r ml/requirements-evaluation.txt")
    config, manifest = read_json(repo / CONFIG), read_json(repo / FAMILY_PATH)
    require(canonical_sha256(config) == SOURCE_PIN, "Reviewed baseline source configuration changed.")
    require(canonical_sha256(manifest) == FAMILY_PIN, "Reviewed family policy changed.")
    verify_file(repo / config["official_test"]["path"], config["official_test"])
    prediction_path = repo / MODEL_DIR / "roberta-base/nbest_predictions_.json"
    verify_file(prediction_path, config["members"]["nbest_predictions_.json"])
    full, train, test, provenance = load_sources(repo)
    require(canonical_sha256(provenance) == canonical_sha256(manifest["provenance"]), "Family source provenance differs.")
    groups = build_groups(full, train, test)
    kept, excluded = sensitivity_titles(groups, manifest["families"])
    require(len(test) == 102 and len(kept) == 93 and len(excluded) == 9, "Reviewed sensitivity counts changed.")
    by_id = {g["group_id"]: g for g in groups}
    unresolved = sorted({d["title"] for decision in manifest["title_decisions"] if decision["decision"] == "unresolved"
                         for gid in decision["group_ids"] if by_id[gid]["official_split"] == "test"
                         for d in by_id[gid]["source_documents"]})
    require(len(unresolved) == 2 and set(unresolved) <= set(kept), "Unresolved test documents must remain in sensitivity.")
    predictions = read_json(prediction_path)
    reference = load_reference(repo, config)
    all_ids = {q["id"] for doc in test.values() for p in doc["paragraphs"] for q in p["qas"]}
    require(len(all_ids) == 4182 and set(predictions) == all_ids, "Released prediction IDs differ from the complete official test.")
    results, curves = {}, {}
    for label, titles in (("full_official_test", sorted(test)), ("known_overlap_sensitivity", kept)):
        dataset = {"data": [test[t] for t in titles]}
        answers = reference.get_answers(dataset)
        selected = {qid: predictions[qid] for qid in answers}
        print(f"Scoring {label}: {len(titles)} documents; {len(answers)} questions...", flush=True)
        local = score_predictions(answers, selected)
        original = reference_score(reference, answers, selected)
        error = assert_parity(local, original)
        require(all(math.isfinite(v) for v in local["metrics"].values()), "Undefined aggregate baseline metric.")
        results[label] = {"source_documents": len(titles), "questions": len(answers),
                          "positive_questions": sum(bool(a) for a in answers.values()),
                          "no_answer_questions": sum(not a for a in answers.values()),
                          "annotated_answers": sum(len(a) for a in answers.values()),
                          "metrics": local["metrics"], "original_evaluator_metrics": original["metrics"],
                          "maximum_recall_including_final_point": max(local["recalls"]),
                          "maximum_recall_on_official_precision_at_recall_grid": max(local["recalls"][:-1]),
                          "maximum_absolute_parity_error": error, "source_titles": titles}
        curves[label] = finite_json({k: v for k, v in local.items() if k != "metrics"})
    report = {"report_version": "1.0.0", "status": "released_prediction_evaluator_parity_verified",
              "prediction_origin": "authors_released_predictions", "fresh_inference_verified": False,
              "baseline_reproduction_complete": False, "policy_threshold_selected": False,
              "metric_protocol": "unmodified_official_word_set_jaccard_v1_with_parties_substring",
              "metric_scale": "0_to_1", "parity_tolerance": TOLERANCE,
              "source_config_canonical_sha256": SOURCE_PIN, "family_manifest_canonical_sha256": FAMILY_PIN,
              "source_provenance": provenance, "prediction_file_sha256": config["members"]["nbest_predictions_.json"]["sha256"],
              "evaluator_file_sha256": config["reference_files"]["evaluate.py"]["sha256"],
              "runtime": {"python": platform.python_version(), "packages": installed},
              "excluded_confirmed_overlap_test_titles": excluded, "retained_unresolved_test_titles": unresolved,
              "limitations": ["The released checkpoint used original official training data; not clean-fit initialization.",
                              "Sensitivity excludes only reviewed confirmed overlap; unknown overlap can remain.",
                              "These are benchmark text-overlap scores, not calibrated probabilities or legal-risk labels.",
                              "Original P@recall zip-length behavior is preserved; the final curve point is omitted."],
              "results": results, "curves_canonical_sha256": canonical_sha256(curves)}
    return report, curves


def main():
    repo = Path(__file__).resolve().parents[2]
    for relative in OUTPUTS:
        require((repo / relative).resolve().is_relative_to(repo), "Evaluation output escapes repository.")
    verify_ignored_assets(repo, OUTPUTS)
    report, curves = evaluate(repo)
    outputs = {repo / name: (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
               for name, value in zip(OUTPUTS, (report, curves))}
    created = save_outputs(outputs)
    for name, result in report["results"].items():
        m = result["metrics"]
        print(f"{name}: AUPR {100*m['aupr']:.3f}%; P@80R {100*m['prec_at_80_recall']:.3f}%; P@90R {100*m['prec_at_90_recall']:.3f}%")
        print(f"  Maximum original-evaluator difference: {result['maximum_absolute_parity_error']:.3g}")
    print("Official test preserved: 102 documents. Sensitivity: 93; excludes 9 confirmed-overlap documents; retains 2 unresolved.")
    print(f"Created {created} evaluation files." if created else "Existing evaluation files match; no files changed.")
    print(f"Results: {OUTPUTS[0]}")
    print("PASS: released predictions scored; local curves and metrics match the pinned original evaluator.")
    print("Fresh model inference, clean training, calibration and operating-policy selection remain pending.")


if __name__ == "__main__":
    main()
