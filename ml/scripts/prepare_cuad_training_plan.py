"""Audit saved CUAD features and prepare deterministic fit-only epoch samples.

Run: python ml/scripts/prepare_cuad_training_plan.py
Requires the completed features_v1 directory and existing frozen source files.
No downloads, GPU, retokenization or model loading. Verifies all feature-file
hashes, source bindings and target semantics, then writes small ignored JSON
files in data/processed/cuad/training_plan_v1/. Existing different outputs are
preserved. --feature-run and --run-name select other named directories.

Keep every fit positive window. Sample negatives without replacement at 2:1,
including at least one for every genuinely absent question. That minimum takes
precedence if it exceeds the ratio budget; shortages are reported explicitly.
Positive questions with zero usable windows contribute NO training windows;
their original gold remains in the frozen data and evaluation denominator.
Ignore-loss windows are never sampled. Three shuffled, reproducible epoch lists
use PCG64 and SeedSequence([42, epoch]). No hard-negative mining is performed.

Development partitions are audited but never enter the sampler. Their complete
regular windows and original gold remain unchanged. This implements sample
selection only; a dataloader, joint marginal loss and trainer are still needed.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
from pathlib import Path
import platform
import re

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from freeze_cuad_splits import FROZEN_DIR, ROLES, build_bundle, validate_saved_bundle, verified_inputs
from prepare_cuad_baseline import verify_ignored_assets
from prepare_cuad_features import COUNTS, IGNORE, NEGATIVE, POLICY as FEATURE_POLICY, POSITIVE, verify_shard
from prepare_cuad_training_assets import CONFIG, PACKAGES, SOURCE_PIN, validate_config
from run_cuad_baseline import atomic_json, run_lock


POLICY = {"sampling_version": 1, "partition": "fit", "seed": 42, "epochs": 3,
          "negative_to_positive_window_ratio": 2, "minimum_negative_per_genuinely_absent_question": 1,
          "positive_windows": "keep_all", "ignored_windows": "never_sample",
          "positive_questions_without_usable_windows": "sample_no_windows_preserve_original_gold",
          "negative_budget": "min(available,max(2*positive_windows,genuinely_absent_questions))",
          "negative_draw": "one_uniform_per_absent_question_then_uniform_remaining_without_replacement",
          "shuffle": "PCG64_SeedSequence_seed_and_one_based_epoch",
          "hard_negative_mining": False, "development_window_sampling": False}
STATS = ("questions", "positive_questions", "no_answer_questions", "positive_windows", "negative_windows",
         "ignored_windows", "answer_occurrences", "covered_answer_occurrences", "long_answer_occurrences",
         "unmapped_answer_occurrences", "regular_window_gap_occurrences", "projected_boundary_occurrences",
         "positive_questions_without_usable_windows", "truncated_questions", "unique_gold_pairs")


def same(left, right, message):
    require(canonical_sha256(left) == canonical_sha256(right), message)


def inspect_group(group, audit, arrays, global_start=0, partition="fit"):
    """Cross-check labels, paired targets and occurrence references before sampling."""
    import numpy as np
    require(partition in ROLES, "Unknown partition.")
    questions = [(p, q) for p in group["paragraphs"] for q in p["questions"]]
    index, ranges = arrays["window_index"], arrays["question_ranges"]
    pairs, refs = arrays["gold_pairs"], arrays["gold_refs"]
    n, nq = len(index), len(questions)
    require(n > 0 and len(audit) == nq and ranges.shape == (nq, 2), "Question/audit shape differs.")
    require(np.isin(index[:, 2], [NEGATIVE, POSITIVE, IGNORE]).all(), "Unknown target status.")
    require(pairs.ndim == 2 and pairs.shape[1] == 3 and refs.ndim == 2 and refs.shape[1] == 2,
            "Invalid pair/reference shape.")
    if len(pairs):
        require(((pairs[:, 0] >= 0) & (pairs[:, 0] < n)).all()
                and ((pairs[:, 1] >= 0) & (pairs[:, 1] <= pairs[:, 2]) & (pairs[:, 2] < 512)).all(),
                "Pair outside its window.")
        require(len(np.unique(pairs, axis=0)) == len(pairs), "Duplicate loss pair.")
        require((pairs[1:, 0] >= pairs[:-1, 0]).all(), "Pairs are not in window order.")
        null = pairs[:, 1] == 0
        require((pairs[null, 2] == 0).all() and (index[pairs[null, 0], 2] == NEGATIVE).all(), "Invalid null target.")
        positive = pairs[~null]
        require((index[positive[:, 0], 2] == POSITIVE).all()
                and (positive[:, 2] - positive[:, 1] + 1 <= 256).all(), "Unsupported positive target.")
        require((arrays["sequence_ids"][positive[:, 0], positive[:, 1]] == 1).all()
                and (arrays["sequence_ids"][positive[:, 0], positive[:, 2]] == 1).all(),
                "Gold target selects question/special tokens.")
    else:
        null = np.zeros(0, dtype=bool)
    pair_counts = np.bincount(pairs[:, 0], minlength=n)
    require((pair_counts[index[:, 2] == NEGATIVE] == 1).all()
            and (pair_counts[index[:, 2] == POSITIVE] >= 1).all()
            and (pair_counts[index[:, 2] == IGNORE] == 0).all(), "Window targets disagree with loss status.")
    if len(refs):
        require(((refs[:, 0] >= 0) & (refs[:, 0] < len(pairs)) & (refs[:, 1] >= 0)).all(), "Invalid gold reference.")
        require(len(np.unique(refs, axis=0)) == len(refs), "Repeated occurrence reference.")
    ref_counts = np.bincount(refs[:, 0], minlength=len(pairs))
    require((ref_counts[null] == 0).all() and (ref_counts[~null] > 0).all(), "Null/gold references disagree.")
    by_question = defaultdict(list)
    for pair_index, answer_index in refs.tolist():
        row = int(pairs[pair_index, 0])
        by_question[int(index[row, 0])].append((pair_index, answer_index))
    require(set(by_question) <= set(range(nq)), "Reference points to an unknown question.")
    records, rows, issues, previous_end = [], [], [], 0
    for qi, ((paragraph, question), saved) in enumerate(zip(questions, audit)):
        begin, end = map(int, ranges[qi])
        require(begin == previous_end and begin < end <= n and (index[begin:end, 0] == qi).all(),
                "Question ranges are incomplete, overlapping or misassigned.")
        previous_end = end
        require(saved["question_index"] == qi and saved["question_id"] == question["question_id"]
                and saved["category_id"] == question["category_id"] and saved["paragraph_index"] == paragraph["index"]
                and saved["window_range"] == [begin, end], "Question audit identity differs from source.")
        qlen = saved["original_question_tokens"]
        require(type(qlen) is int and qlen > 0 and saved["used_question_tokens"] == min(qlen, 64), "Invalid question truncation audit.")
        status = index[begin:end, 2]
        starts = index[begin:end, 1]
        context_counts = np.sum(arrays["sequence_ids"][begin:end] == 1, axis=1)
        capacity = 512 - min(qlen, 64) - 4
        step = capacity - 128
        token_total = int(starts[-1] + context_counts[-1])
        require(np.array_equal(starts, np.arange(end - begin) * step)
                and (context_counts > 0).all()
                and np.array_equal(context_counts, np.minimum(capacity, token_total - starts)),
                "Regular context windows have gaps or wrong overlap.")
        positives = np.flatnonzero(status == POSITIVE) + begin + global_start
        negatives = np.flatnonzero(status == NEGATIVE) + begin + global_start
        ignored = int(np.sum(status == IGNORE))
        require([saved[k] for k in ("positive_windows", "negative_windows", "ignored_windows")]
                == [len(positives), len(negatives), ignored], "Audit window counts differ from arrays.")
        gold = question["answers"]
        require(question["is_impossible"] is (not bool(gold)) and len(saved["answers"]) == len(gold), "Gold answerability differs.")
        if not gold:
            require(len(negatives) == end - begin, "Genuinely absent question has nonnegative windows.")
        used = Counter()
        for pair_index, answer_index in by_question[qi]:
            require(answer_index < len(gold), "Occurrence reference exceeds the source gold list.")
            row, start, stop = map(int, pairs[pair_index])
            mapped, original = saved["answers"][answer_index], gold[answer_index]
            require(mapped["reason"] is None, "Unsupported answer has a positive target.")
            left = int(arrays["offsets"][row, start, 0])
            right = int(arrays["offsets"][row, stop, 1])
            require(left == mapped["projected_start"] and right == mapped["projected_end"]
                    and 0 <= left <= original["start"] < original["end"] <= right <= len(paragraph["context"]),
                    "Target offsets differ from their original answer occurrence.")
            context_positions = np.flatnonzero(arrays["sequence_ids"][row] == 1)
            require(len(context_positions) > 0 and np.all(np.diff(context_positions) == 1), "Noncontiguous context tokens.")
            base = int(index[row, 1]) - int(context_positions[0])
            require(start + base == mapped["start_token"] and stop + base == mapped["end_token"],
                    "Target tokens differ from their global context positions.")
            used[answer_index] += 1
        counts = Counter({k: 0 for k in STATS})
        counts.update(questions=1, positive_questions=int(bool(gold)), no_answer_questions=int(not gold),
                      positive_windows=len(positives), negative_windows=len(negatives), ignored_windows=ignored,
                      positive_questions_without_usable_windows=int(bool(gold) and not len(positives)),
                      truncated_questions=int(qlen > 64), unique_gold_pairs=len({p for p, _ in by_question[qi]}))
        uncovered = []
        expected_positive = np.zeros(end - begin, dtype=bool)
        intersects = np.zeros(end - begin, dtype=bool)
        for ai, (original, mapped) in enumerate(zip(gold, saved["answers"])):
            require(mapped["answer_index"] == ai and type(mapped["usable_windows"]) is int
                    and mapped["usable_windows"] == used[ai], "Gold occurrence coverage differs from target references.")
            reason = mapped["reason"]
            require(reason in (None, "longer_than_256_tokens", "unmapped_boundary"), "Unknown unsupported-answer reason.")
            if reason != "unmapped_boundary":
                length = mapped["token_length"]
                require(type(length) is int and length == mapped["end_token"] - mapped["start_token"] + 1
                        and 0 <= mapped["start_token"] <= mapped["end_token"] < token_total
                        and ((length > 256) == (reason == "longer_than_256_tokens")), "Answer-length audit differs.")
                require(type(mapped["exact_boundaries"]) is bool
                        and mapped["exact_boundaries"] == (mapped["projected_start"] == original["start"]
                                                           and mapped["projected_end"] == original["end"]),
                        "Projected boundary audit differs.")
                a, b = mapped["start_token"], mapped["end_token"]
                intersects |= (a < starts + context_counts) & (b >= starts)
                complete = (starts <= a) & (b < starts + context_counts) if reason is None else np.zeros(len(starts), dtype=bool)
                require(int(np.sum(complete)) == used[ai], "A complete gold target was omitted or duplicated.")
                expected_positive |= complete
            else:
                spans = arrays["offsets"][begin:end]
                visible = (arrays["sequence_ids"][begin:end] == 1) & (spans[:, :, 0] < spans[:, :, 1])
                left = np.min(np.where(visible, spans[:, :, 0], np.iinfo(np.int32).max), axis=1)
                right = np.max(np.where(visible, spans[:, :, 1], -1), axis=1)
                intersects |= (original["start"] < right) & (original["end"] > left)
            require(not reason or used[ai] == 0, "Unsupported occurrence unexpectedly covered.")
            counts["answer_occurrences"] += 1
            counts["covered_answer_occurrences"] += int(used[ai] > 0)
            counts["long_answer_occurrences"] += int(reason == "longer_than_256_tokens")
            counts["unmapped_answer_occurrences"] += int(reason == "unmapped_boundary")
            counts["regular_window_gap_occurrences"] += int(reason is None and used[ai] == 0)
            counts["projected_boundary_occurrences"] += int(mapped["start_token"] is not None and not mapped["exact_boundaries"])
            if not used[ai]:
                uncovered.append({"answer_index": ai, "start": original["start"], "end": original["end"],
                                  "token_length": mapped["token_length"], "reason": reason or "regular_window_gap"})
        expected_status = np.where(expected_positive, POSITIVE, np.where(intersects, IGNORE, NEGATIVE))
        require(np.array_equal(status, expected_status), "Gold-overlap windows were mislabeled as positive, ignored or negative.")
        records.append({"partition": partition, "question_id": question["question_id"], "is_impossible": not bool(gold),
                        "positive_indices": positives, "negative_indices": negatives})
        rows.append((question["category_id"], dict(counts)))
        if uncovered:
            issues.append({"partition": partition, "group_id": group["group_id"], "family_id": group["family_id"],
                           "question_id": question["question_id"], "category_id": question["category_id"],
                           "positive_windows": len(positives), "uncovered_answers": uncovered})
    require(previous_end == n, "Trailing windows are not assigned to a question.")
    return records, rows, issues


def pools(records):
    import numpy as np
    require(bool(records) and all(r["partition"] == "fit" for r in records), "Sampler accepts fit records only.")
    require(len({r["question_id"] for r in records}) == len(records), "Repeated fit question.")
    positives, negatives, absent, skipped = [], [], [], []
    all_indices = []
    for r in records:
        pos, neg = np.asarray(r["positive_indices"], dtype=np.int64), np.asarray(r["negative_indices"], dtype=np.int64)
        require(pos.ndim == neg.ndim == 1 and type(r["is_impossible"]) is bool, "Invalid sampling record.")
        all_indices.extend([pos, neg])
        if r["is_impossible"]:
            require(len(pos) == 0 and len(neg) > 0, "Absent question lacks valid negative candidates.")
            absent.append(neg)
        if len(pos) or r["is_impossible"]:
            positives.append(pos)
            negatives.append(neg)
        else:
            skipped.append(r["question_id"])
    all_indices = np.concatenate(all_indices)
    require((all_indices >= 0).all() and len(np.unique(all_indices)) == len(all_indices), "Repeated/invalid global feature index.")
    positive = np.concatenate(positives) if positives else np.array([], dtype=np.int64)
    negative = np.concatenate(negatives) if negatives else np.array([], dtype=np.int64)
    require(len(positive) > 0, "No usable positive fit windows; do not train.")
    return positive, negative, absent, skipped


def validate_selection(selected, records):
    import numpy as np
    require(type(selected) is list and all(type(i) is int for i in selected), "Selected indices must be integers.")
    positive, negative, absent, skipped = pools(records)
    chosen = np.asarray(selected, dtype=np.int64)
    require(len(np.unique(chosen)) == len(chosen), "Repeated selected window.")
    require(np.isin(positive, chosen).all() and np.isin(chosen, np.concatenate([positive, negative])).all(),
            "Selection lost positives or included ignored/unsupported windows.")
    chosen_set = set(selected)
    require(all(any(int(i) in chosen_set for i in candidates) for candidates in absent),
            "A genuinely absent question has no sampled negative.")
    budget = min(len(negative), max(2 * len(positive), len(absent)))
    require(len(chosen) == len(positive) + budget, "Wrong negative sampling budget.")
    return {"positive_windows": len(positive), "negative_windows": budget, "total_windows": len(chosen),
            "genuinely_absent_questions_covered": len(absent), "unsampled_positive_questions": len(skipped),
            "available_negative_candidates": len(negative), "effective_negative_to_positive_ratio": budget / len(positive),
            "minimum_overrode_ratio": len(absent) > 2 * len(positive),
            "negative_candidate_shortfall": max(0, max(2 * len(positive), len(absent)) - len(negative))}


def sample_epoch(records, epoch):
    import numpy as np
    require(type(epoch) is int and 1 <= epoch <= POLICY["epochs"], "Epoch must be 1..3.")
    positive, negative, absent, _ = pools(records)
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([POLICY["seed"], epoch])))
    mandatory = np.asarray([rng.choice(candidates) for candidates in absent], dtype=np.int64)
    budget = min(len(negative), max(2 * len(positive), len(absent)))
    remaining = np.setdiff1d(negative, mandatory, assume_unique=True)
    extra = rng.choice(remaining, size=budget - len(mandatory), replace=False)
    selected = rng.permutation(np.concatenate([positive, mandatory, extra])).tolist()
    return {"epoch": epoch, "global_fit_window_indices": selected, "summary": validate_selection(selected, records)}


def audit_features(repo, feature_root):
    """Read the existing artifacts, independently cross-checking target tables."""
    import numpy as np
    validate_config(read_json(repo / CONFIG))
    bundle = validate_saved_bundle(repo / FROZEN_DIR, build_bundle(*verified_inputs(repo)))
    identity, manifest, report = [read_json(feature_root / n) for n in ("identity.json", "manifest.json", "report.json")]
    identity_sha = canonical_sha256(identity)
    same(identity["policy"], FEATURE_POLICY, "Feature policy differs.")
    same(identity["partition_roles"], ROLES, "Partition roles differ.")
    require(identity["training_source_sha256"] == SOURCE_PIN
            and identity["frozen_manifest_sha256"] == canonical_sha256(bundle["manifest.json"]), "Feature source/freeze binding differs.")
    pins = {**PACKAGES, "numpy": "2.3.5"}
    require(identity["runtime"]["packages"] == pins
            and {p: importlib.metadata.version(p) for p in pins} == pins
            and identity["runtime"]["python"] == platform.python_version(), "Feature runtime differs; use the pinned environment.")
    code = {n: hashlib.sha256((repo / "ml/scripts" / n).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for n in ("prepare_cuad_features.py", "prepare_cuad_training_assets.py")}
    same(identity["code_sha256"], code, "Feature producer code differs.")
    require(manifest["complete"] is True and manifest["feature_identity_sha256"] == identity_sha
            and report["feature_identity_sha256"] == identity_sha
            and manifest["report_sha256"] == canonical_sha256(report), "Feature run/report is incomplete or changed.")
    require(set(manifest["partitions"]) == set(ROLES), "Missing or extra feature partition.")
    fit_records, fit_shards, issues, category = [], [], [], defaultdict(Counter)
    summaries, fit_offset = {}, 0
    for split in ROLES:
        groups, entries = bundle[split + ".json"]["groups"], manifest["partitions"][split]
        require(len(groups) == len(entries), "Missing feature group.")
        total = Counter({k: 0 for k in COUNTS})
        for group, entry in zip(groups, entries):
            expected_path = f"{split}/{canonical_sha256(group)[:24]}"
            require(entry["path"] == expected_path, "Feature shard order/path differs from frozen groups.")
            directory = feature_root / expected_path
            shard = verify_shard(directory, group, split, identity_sha)
            require(canonical_sha256(shard) == entry["manifest_sha256"], "Shard manifest digest differs.")
            same(shard["summary"], entry["summary"], "Shard summary differs from run manifest.")
            arrays = {name: np.load(directory / (name + ".npy"), mmap_mode="r", allow_pickle=False)
                      for name in ("window_index", "question_ranges", "gold_pairs", "gold_refs", "sequence_ids", "offsets")}
            try:
                source = read_json(directory / "source.json")
                records, rows, missed = inspect_group(group, source["question_audit"], arrays, fit_offset if split == "fit" else 0, split)
                calculated = Counter({k: 0 for k in COUNTS})
                calculated.update(groups=1, windows=len(arrays["window_index"]))
                for cat, counts in rows:
                    calculated.update(counts)
                    category[(split, cat)].update(counts)
                same(dict(calculated), shard["summary"], "Target-derived counts differ from feature summary.")
                if split == "fit":
                    fit_records.extend(records)
                    fit_shards.append({"path": expected_path, "group_id": group["group_id"], "global_window_start": fit_offset,
                                       "global_window_end": fit_offset + calculated["windows"], "manifest_sha256": entry["manifest_sha256"]})
                    fit_offset += calculated["windows"]
                issues.extend(missed)
                total.update(calculated)
            finally:
                arrays.clear()
        same(dict(total), report["partitions"][split], "Partition counts differ from feature report.")
        summaries[split] = dict(total)
        print(f"Audited {split}: {total['questions']} questions; {total['positive_questions_without_usable_windows']} positive questions without usable windows", flush=True)
    coverage = {"partition_summary": summaries,
                "category_summary": [{"partition": s, "category_id": c, **dict(counts)} for (s, c), counts in sorted(category.items())],
                "questions_with_uncovered_answers": issues,
                "support_limitations": bundle["manifest.json"]["support_limitations"],
                "original_gold_preserved": True, "development_windows_changed": False,
                "interpretation": "Annotation/feature coverage only, not model accuracy or calibration support."}
    bindings = {"feature_identity_sha256": identity_sha, "feature_manifest_sha256": canonical_sha256(manifest),
                "feature_report_sha256": canonical_sha256(report)}
    return coverage, fit_records, fit_shards, bindings


def prepare(repo, feature_run="features_v1", name="training_plan_v1"):
    require(all(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", s) for s in (feature_run, name)), "Invalid run name.")
    require(name != feature_run, "Training plan must have a separate output directory.")
    feature_root, output = [repo / "data/processed/cuad" / n for n in (feature_run, name)]
    require(feature_root.is_dir(), "Run prepare_cuad_features.py first.")
    names = ["coverage.json", "fit_index.json", "epoch_1.json", "epoch_2.json", "epoch_3.json", "manifest.json", "run.lock"]
    verify_ignored_assets(repo, [f"data/processed/cuad/{name}/{n}" for n in names])
    with run_lock(feature_root):
        coverage, records, shards, bindings = audit_features(repo, feature_root)
        epochs = [sample_epoch(records, e) for e in range(1, 4)]
        _, _, _, skipped = pools(records)
        identity = {**bindings, "feature_directory": feature_root.relative_to(repo).as_posix(), "sampling_policy": POLICY,
                    "producer_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()}
        plan_sha = canonical_sha256(identity)
        payloads = {"coverage.json": {"plan_sha256": plan_sha, **coverage},
                    "fit_index.json": {"plan_sha256": plan_sha, "shards": shards,
                                       "unsampled_positive_question_ids": skipped}}
        for epoch in epochs:
            payloads[f"epoch_{epoch['epoch']}.json"] = {"plan_sha256": plan_sha, **epoch}
        payloads["manifest.json"] = {"status": "coverage_audited_fit_samples_prepared", "identity": identity,
                                    "plan_sha256": plan_sha, "files": {n: canonical_sha256(v) for n, v in payloads.items()},
                                    "model_training_performed": False, "hard_negative_mining_performed": False,
                                    "baseline_reproduction_assessed": False}
        with run_lock(output):
            # Validate every existing output before publishing any missing file.
            for filename, value in payloads.items():
                if (output / filename).exists():
                    same(read_json(output / filename), value, f"Existing training plan differs; preserved: {filename}")
            created = sum(atomic_json(output / filename, value) for filename, value in payloads.items())
    for epoch in epochs:
        c = epoch["summary"]
        print(f"Epoch {epoch['epoch']}: {c['positive_windows']} positive + {c['negative_windows']} negative = {c['total_windows']} fit windows; "
              f"{c['genuinely_absent_questions_covered']} absent questions covered")
    print(f"Fit positive questions sampled zero times because they have no usable positive window: {len(skipped)}")
    print("All positive fit windows retained; ignored windows and development partitions excluded from training samples.")
    print("Original gold, regular feature arrays and evaluation denominators unchanged.")
    print(f"Created {created} files." if created else "Existing training plan matches; no files changed.")
    print(f"Output: data/processed/cuad/{name}/")
    print("PASS: coverage audited and three deterministic epoch lists verified.")
    print("No dataloader, QA head, loss optimization, model training, calibration or policy selection performed.")
    return payloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-run", default="features_v1")
    parser.add_argument("--run-name", default="training_plan_v1")
    args = parser.parse_args()
    prepare(Path(__file__).resolve().parents[2], args.feature_run, args.run_name)


if __name__ == "__main__":
    main()
