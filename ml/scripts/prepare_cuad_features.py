"""Build auditable, memory-mapped features from the four frozen CUAD partitions.

Run: python ml/scripts/prepare_cuad_features.py
Optional pilot: --partition fit --limit-groups 1. Re-run without options to
finish; completed group shards are verified and reused. CPU only, using the
existing pinned tokenizer environment. No model, sampling or training occurs.

Outputs: ignored data/processed/cuad/features_v1/. Each exact-text group has
eight .npy arrays, source.json (unchanged logical source group plus audits), and
a checksum manifest. Incomplete temporary directories never count as shards.
Changed inputs/code/runtime or damaged outputs fail without overwriting saved
work. --run-name NAME selects a separate output directory if needed.

512 tokens, first 64 question tokens, 128 context-token overlap, 256 answer
tokens. All regular windows are retained, including every negative. Original
question text and gold occurrences stay intact. Unique complete gold pairs
are joint marginal-loss targets; duplicate annotations retain references but
never multiply probability mass. Partial/long/unmapped gold-only windows have
IGNORE targets, not null. Negatives use the CLS null token at index zero.

Offsets are original Unicode code points, end exclusive. Token targets can
cover a whole boundary subword; projected boundaries are explicitly audited.
Answers not covered by regular windows remain in the evaluation denominator.
No answer-dependent window placement, India labels, or official-test features.
Review the final report before implementing a separate fit-only trainer.
"""

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from copy import deepcopy
import gc
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import re
import shutil
from tempfile import TemporaryDirectory

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from freeze_cuad_splits import FROZEN_DIR, ROLES, build_bundle, validate_saved_bundle, verified_inputs
from prepare_cuad_baseline import verify_file, verify_ignored_assets
from prepare_cuad_training_assets import CONFIG, MODEL_DIR, PACKAGES, SOURCE_PIN, validate_config, verify_local_assets
from run_cuad_baseline import atomic_json, run_lock


OUTPUT_BASE = "data/processed/cuad"
NEGATIVE, POSITIVE, IGNORE = 0, 1, 2
POLICY = {"feature_version": 1, "max_seq_length": 512, "max_question_tokens": 64,
          "context_token_overlap": 128, "max_answer_tokens": 256,
          "question_truncation": "first_64_tokens_original_text_preserved",
          "windows": "regular_source_order_no_gold_dependent_placement",
          "targets": "unique_joint_start_end_pairs_with_original_occurrence_references",
          "partial_long_or_unmapped_only": "ignore_loss",
          "sampling": "none_all_windows_retained", "null_token_index": 0,
          "span_coordinates": "original_unicode_code_points_end_exclusive",
          "window_index_columns": ["question_index", "context_token_start", "target_status"],
          "gold_pairs_columns": ["window_row", "start_token", "end_token_inclusive"],
          "gold_refs_columns": ["gold_pair_row", "original_answer_index"],
          "target_status": {"negative": NEGATIVE, "positive": POSITIVE, "ignore": IGNORE}}
ARRAYS = {"input_ids": ("<i4", (512,)), "attention_mask": ("u1", (512,)),
          "sequence_ids": ("i1", (512,)), "offsets": ("<i4", (512, 2)),
          "window_index": ("<i4", (3,)), "gold_pairs": ("<i4", (3,)),
          "gold_refs": ("<i4", (2,)), "question_ranges": ("<i4", (2,))}
COUNTS = ("groups", "questions", "positive_questions", "no_answer_questions", "windows",
          "positive_windows", "negative_windows", "ignored_windows", "answer_occurrences",
          "covered_answer_occurrences", "long_answer_occurrences", "unmapped_answer_occurrences",
          "regular_window_gap_occurrences", "projected_boundary_occurrences",
          "positive_questions_without_usable_windows", "truncated_questions", "unique_gold_pairs")


def window_count(tokens, question_tokens):
    capacity = 512 - question_tokens - 4
    require(tokens > 0 and 0 < question_tokens <= 64, "Empty context or invalid question budget.")
    return 1 + max(0, math.ceil((tokens - capacity) / (capacity - 128)))


def align_answers(context, offsets, answers):
    """Map gold in the FULL context so windows cannot cut Unicode byte pieces.

    Repeated byte-BPE offsets select the earliest start and latest end piece.
    Trimmed whitespace boundaries are reported as unmapped, never relocated or
    silently stripped. Original annotations are not modified.
    """
    valid = [(i, s, e) for i, (s, e) in enumerate(offsets) if s < e]
    starts, ends = [r[1] for r in valid], [r[2] for r in valid]
    require(starts == sorted(starts) and ends == sorted(ends), "Nonmonotonic source offsets.")
    result = []
    for index, answer in enumerate(answers):
        start, end = answer["start"], answer["end"]
        require(type(start) is int and type(end) is int and 0 <= start < end <= len(context)
                and context[start:end] == answer["text"], "Gold span differs from the original source.")
        first, last = bisect_right(ends, start), bisect_left(starts, end) - 1
        row = {"answer_index": index, "start_token": None, "end_token": None,
               "token_length": None, "projected_start": None, "projected_end": None,
               "exact_boundaries": False, "reason": "unmapped_boundary", "usable_windows": 0}
        if (0 <= first <= last < len(valid) and valid[first][1] <= start < valid[first][2]
                and valid[last][1] < end <= valid[last][2]):
            a, b = valid[first][0], valid[last][0]
            row.update(start_token=a, end_token=b, token_length=b - a + 1,
                       projected_start=offsets[a][0], projected_end=offsets[b][1],
                       exact_boundaries=(offsets[a][0] == start and offsets[b][1] == end),
                       reason="longer_than_256_tokens" if b - a + 1 > 256 else None)
        result.append(row)
    return result


def window_targets(answers, aligned, token_start, positions, offsets):
    """Return status and unique local pairs -> original answer occurrence IDs."""
    token_end = token_start + len(positions)
    visible = [offsets[p] for p in positions if offsets[p][0] < offsets[p][1]]
    require(bool(visible), "Context window contains no source characters.")
    left, right = min(s for s, _ in visible), max(e for _, e in visible)
    pairs, intersects = {}, False
    for answer, row in zip(answers, aligned):
        a, b = row["start_token"], row["end_token"]
        if a is not None:
            intersects |= a < token_end and b >= token_start
            if row["reason"] is None and token_start <= a <= b < token_end:
                pair = (positions[a - token_start], positions[b - token_start])
                pairs.setdefault(pair, []).append(row["answer_index"])
                row["usable_windows"] += 1
        else:
            intersects |= answer["start"] < right and answer["end"] > left
    if pairs:
        return POSITIVE, pairs
    return (IGNORE, {}) if intersects else (NEGATIVE, {(0, 0): []})


class FeatureTokenizer:
    def __init__(self, directory):
        from tokenizers import Tokenizer
        from transformers import RobertaTokenizerFast
        self.tokenizer = RobertaTokenizerFast.from_pretrained(
            str(directory), local_files_only=True, add_prefix_space=False, trim_offsets=True)
        self.backend = self.tokenizer.backend_tokenizer
        self.backend.no_padding()
        self.backend.no_truncation()
        # Apply the postprocessor ONCE after truncation to avoid double-trimming
        # RoBERTa's whitespace offsets. Preserve global source coordinates.
        self.raw = Tokenizer.from_str(self.backend.to_str())
        self.raw.post_processor = None
        self.raw.no_padding()
        self.raw.no_truncation()
        self.questions = {}

    def question(self, text):
        if text not in self.questions:
            encoding = self.raw.encode(text, add_special_tokens=False)
            original = len(encoding.ids)
            require(original > 0, "Empty question tokens.")
            encoding.truncate(64)
            self.questions[text] = (encoding, original)
        return self.questions[text]

    def context(self, text):
        raw = self.raw.encode(text, add_special_tokens=False)
        require(len(raw.ids) > 0, "Empty context.")
        offsets = self.backend.post_process(raw, add_special_tokens=False).offsets
        covered = bytearray(len(text))
        for start, end in offsets:
            require(0 <= start <= end <= len(text), "Context offsets are not source code points.")
            covered[start:end] = b"\1" * (end - start)
        require(all(covered[i] or c.isspace() for i, c in enumerate(text)), "Tokenizer lost source characters.")
        return raw, offsets

    def windows(self, raw_context, full_offsets, question):
        query, _ = self.question(question)
        query_ids, source_ids = query.ids, raw_context.ids
        capacity = 512 - len(query_ids) - 4
        context = deepcopy(raw_context)
        context.truncate(capacity, stride=128)
        rows = [context, *context.overflowing]
        require(len(rows) == window_count(len(source_ids), len(query_ids)), "Wrong overflow count.")
        for index, part in enumerate(rows):
            start = index * (capacity - 128)
            encoding = self.backend.post_process(query, part, add_special_tokens=True)
            encoding.pad(512, pad_id=1, pad_token="<pad>")
            ids, offsets, sequences = encoding.ids, encoding.offsets, encoding.sequence_ids
            positions = [i for i, s in enumerate(sequences) if s == 1]
            require(len(ids) == 512 and ids[0] == 0 and len(positions) == len(part.ids), "Unexpected pair layout or null token.")
            require([ids[i] for i in positions] == source_ids[start:start + len(positions)]
                    and [offsets[i] for i in positions] == full_offsets[start:start + len(positions)],
                    "Overflow lost context token identity or source offsets.")
            require([ids[i] for i, s in enumerate(sequences) if s == 0] == query_ids,
                    "Question truncation differs from the first 64 tokens.")
            yield start, encoding, positions


def file_spec(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {"size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def group_inputs(group, tokenizer):
    contexts, questions, total = {}, [], 0
    for paragraph in group["paragraphs"]:
        raw, offsets = tokenizer.context(paragraph["context"])
        contexts[paragraph["index"]] = raw, offsets
        for question in paragraph["questions"]:
            query, original_length = tokenizer.question(question["question"])
            n = window_count(len(raw.ids), len(query.ids))
            questions.append((paragraph, question, original_length, total, total + n))
            total += n
    require(total > 0, "Empty source group.")
    return contexts, questions, total


def build_shard(directory, group, partition, identity_sha, tokenizer):
    """Write into a private staging directory; publish only on success."""
    import numpy as np
    contexts, questions, total = group_inputs(group, tokenizer)
    estimated = total * (512 * 14 + 12) + 8 * 1024 * 1024
    require(shutil.disk_usage(directory).free >= estimated * 1.1,
            "Insufficient disk space for the next shard; completed shards are preserved.")
    arrays, specs = {}, {}
    pairs, refs, audits = [], [], []
    counts = Counter({k: 0 for k in COUNTS})
    counts.update(groups=1, questions=len(questions), windows=total)
    try:
        for name in ("input_ids", "attention_mask", "sequence_ids", "offsets", "window_index", "question_ranges"):
            dtype, tail = ARRAYS[name]
            shape = (len(questions) if name == "question_ranges" else total, *tail)
            arrays[name] = np.lib.format.open_memmap(directory / (name + ".npy"), mode="w+", dtype=dtype, shape=shape)
        for qi, (paragraph, question, q_length, begin, end) in enumerate(questions):
            context, answers = paragraph["context"], question["answers"]
            raw, offsets = contexts[paragraph["index"]]
            require(question["is_impossible"] is (not bool(answers)), "Question answerability differs from gold.")
            aligned = align_answers(context, offsets, answers)
            arrays["question_ranges"][qi] = (begin, end)
            statuses, observed = Counter(), 0
            for wi, (token_start, encoding, positions) in enumerate(tokenizer.windows(raw, offsets, question["question"])):
                row = begin + wi
                require(row < end, "Too many windows.")
                status, targets = window_targets(answers, aligned, token_start, positions, encoding.offsets)
                arrays["input_ids"][row] = encoding.ids
                arrays["attention_mask"][row] = encoding.attention_mask
                arrays["sequence_ids"][row] = [-1 if s is None else s for s in encoding.sequence_ids]
                arrays["offsets"][row] = [span if s == 1 else (-1, -1)
                                            for span, s in zip(encoding.offsets, encoding.sequence_ids)]
                arrays["window_index"][row] = (qi, token_start, status)
                for (start, stop), occurrences in sorted(targets.items()):
                    pair_index = len(pairs)
                    pairs.append((row, start, stop))
                    refs.extend((pair_index, original) for original in occurrences)
                statuses[status] += 1
                observed += 1
            require(begin + observed == end, "Incomplete question windows.")
            counts["positive_questions" if answers else "no_answer_questions"] += 1
            counts["truncated_questions"] += int(q_length > 64)
            counts["positive_questions_without_usable_windows"] += int(bool(answers) and not statuses[POSITIVE])
            for status, name in ((NEGATIVE, "negative_windows"), (POSITIVE, "positive_windows"), (IGNORE, "ignored_windows")):
                counts[name] += statuses[status]
            for answer in aligned:
                counts["answer_occurrences"] += 1
                counts["covered_answer_occurrences"] += int(answer["usable_windows"] > 0)
                counts["long_answer_occurrences"] += int(answer["reason"] == "longer_than_256_tokens")
                counts["unmapped_answer_occurrences"] += int(answer["reason"] == "unmapped_boundary")
                counts["regular_window_gap_occurrences"] += int(answer["reason"] is None and not answer["usable_windows"])
                counts["projected_boundary_occurrences"] += int(answer["start_token"] is not None and not answer["exact_boundaries"])
            audits.append({"question_index": qi, "paragraph_index": paragraph["index"],
                           "question_id": question["question_id"], "category_id": question["category_id"],
                           "original_question_tokens": q_length, "used_question_tokens": min(q_length, 64),
                           "window_range": [begin, end], "positive_windows": statuses[POSITIVE],
                           "negative_windows": statuses[NEGATIVE], "ignored_windows": statuses[IGNORE], "answers": aligned})
        for name, values in (("gold_pairs", pairs), ("gold_refs", refs)):
            dtype, tail = ARRAYS[name]
            np.save(directory / (name + ".npy"), np.asarray(values, dtype=dtype).reshape((-1, *tail)), allow_pickle=False)
        counts["unique_gold_pairs"] = sum(start != 0 for _, start, _ in pairs)
        for name in arrays:
            arrays[name].flush()
        for name, (dtype, tail) in ARRAYS.items():
            rows = len(pairs) if name == "gold_pairs" else len(refs) if name == "gold_refs" else len(questions) if name == "question_ranges" else total
            specs[name + ".npy"] = {"dtype": np.dtype(dtype).str, "shape": [rows, *tail]}
    finally:
        # No memmap views escape this function. Close before Windows renaming.
        arrays.clear()
        gc.collect()
    write_json(directory / "source.json", {"source_group": group, "question_audit": audits})
    for name in [*specs, "source.json"]:
        specs.setdefault(name, {}).update(file_spec(directory / name))
    manifest = {"feature_identity_sha256": identity_sha, "partition": partition, "group_id": group["group_id"],
                "family_id": group["family_id"], "source_group_sha256": canonical_sha256(group),
                "summary": dict(counts), "files": specs}
    write_json(directory / "manifest.json", manifest)
    return manifest


def verify_shard(directory, group, partition, identity_sha):
    """Check hashes and typed array schema before reusing a shard."""
    import numpy as np
    manifest = read_json(directory / "manifest.json")
    require(manifest["feature_identity_sha256"] == identity_sha and manifest["partition"] == partition
            and manifest["group_id"] == group["group_id"] and manifest["family_id"] == group["family_id"]
            and manifest["source_group_sha256"] == canonical_sha256(group), "Feature shard source/partition binding differs.")
    expected_files = {name + ".npy" for name in ARRAYS} | {"source.json"}
    # Sync/indexing software can create temporary sidecars. Read ONLY the exact
    # manifest-declared names; unrelated files cannot become features. Every
    # required file still has to exist and match its size, hash and array schema.
    require(set(manifest["files"]) == expected_files, "Unexpected declared shard file set.")
    for name, spec in manifest["files"].items():
        verify_file(directory / name, spec)
        if name.endswith(".npy"):
            value = np.load(directory / name, mmap_mode="r", allow_pickle=False)
            dtype, tail = ARRAYS[name[:-4]]
            require(value.dtype == np.dtype(dtype) and value.dtype.str == spec["dtype"]
                    and list(value.shape) == spec["shape"] and value.shape[1:] == tail, "Feature array shape/dtype differs.")
            del value
    source = read_json(directory / "source.json")
    require(canonical_sha256(source["source_group"]) == canonical_sha256(group), "Saved source group differs from frozen source.")
    require(set(manifest["summary"]) == set(COUNTS)
            and all(type(v) is int and v >= 0 for v in manifest["summary"].values()), "Invalid feature counts.")
    return manifest


def bind_features(root, identity):
    path = root / "identity.json"
    digest = canonical_sha256(identity)
    if path.exists():
        require(canonical_sha256(read_json(path)) == digest,
                "Feature inputs/code/runtime changed; existing work preserved. Use a separate --run-name.")
    else:
        require(not any(p.name != "run.lock" for p in root.iterdir()), "Nonempty feature directory lacks its identity.")
        atomic_json(path, identity)
    return digest


def prepare(repo, partition=None, limit=None, name="features_v1"):
    require(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", name) is not None, "Invalid feature run name.")
    require(partition is None or partition in ROLES, "Unknown partition.")
    require(limit is None or (type(limit) is int and limit > 0), "Group limit must be a positive integer.")
    require(platform.python_version_tuple()[:2] == ("3", "12"), "Use the Python 3.12 clauseanchor environment.")
    pins = {**PACKAGES, "numpy": "2.3.5"}
    versions = {package: importlib.metadata.version(package) for package in pins}
    require(versions == pins, "Expected the existing pinned tokenizer/numpy dependencies.")
    config = read_json(repo / CONFIG)
    validate_config(config)
    verify_local_assets(repo / MODEL_DIR, config)
    bundle = validate_saved_bundle(repo / FROZEN_DIR, build_bundle(*verified_inputs(repo)))
    frozen = bundle["manifest.json"]
    identity = {"policy": POLICY, "training_source_sha256": SOURCE_PIN,
                "frozen_manifest_sha256": canonical_sha256(frozen), "partition_roles": ROLES,
                "runtime": {"python": platform.python_version(), "packages": versions},
                "code_sha256": {n: hashlib.sha256((repo / "ml/scripts" / n).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                                for n in ("prepare_cuad_features.py", "prepare_cuad_training_assets.py")}}
    root = repo / OUTPUT_BASE / name
    # Separate calls avoid Windows command-line length limits.
    for split in ROLES:
        verify_ignored_assets(repo, [str((root / split / "sample" / f).relative_to(repo)).replace("\\", "/")
                                    for f in [*(n + ".npy" for n in ARRAYS), "manifest.json", "source.json"]])
    verify_ignored_assets(repo, [f"{OUTPUT_BASE}/{name}/{n}" for n in ("run.lock", "identity.json", "manifest.json", "report.json")])
    tokenizer = FeatureTokenizer(repo / MODEL_DIR)
    print("Pinned backbone/tokenizer and source-to-frozen partition chain: verified", flush=True)
    print("CPU feature preparation; all regular windows retained; no model loaded", flush=True)
    new, entries = 0, {}
    with run_lock(root):
        identity_sha = bind_features(root, identity)
        for split in ROLES:
            entries[split] = []
            groups = bundle[split + ".json"]["groups"]
            for index, group in enumerate(groups):
                directory = root / split / canonical_sha256(group)[0:24]
                if directory.exists():
                    manifest = verify_shard(directory, group, split, identity_sha)
                elif (partition is None or partition == split) and (limit is None or new < limit):
                    directory.parent.mkdir(parents=True, exist_ok=True)
                    print(f"Preparing {split} group {index + 1}/{len(groups)}...", flush=True)
                    with TemporaryDirectory(prefix=".pending-", dir=directory.parent) as temp:
                        stage = Path(temp) / "shard"
                        stage.mkdir()
                        build_shard(stage, group, split, identity_sha, tokenizer)
                        manifest = verify_shard(stage, group, split, identity_sha)
                        require(not directory.exists(), "Shard destination appeared; preserved.")
                        stage.rename(directory)
                    new += 1
                else:
                    continue
                entries[split].append({"path": directory.relative_to(root).as_posix(),
                                       "manifest_sha256": canonical_sha256(manifest), "summary": manifest["summary"]})
        complete = all(len(entries[s]) == len(bundle[s + ".json"]["groups"]) for s in ROLES)
        summaries = {s: {k: sum(e["summary"][k] for e in entries[s]) for k in COUNTS} for s in ROLES}
        if complete:
            for split, summary in summaries.items():
                expected = frozen["partitions"][split]["summary"]
                require(all(summary[k] == expected[k] for k in ("questions", "positive_questions", "no_answer_questions"))
                        and summary["answer_occurrences"] == expected["answer_spans"], "Frozen source counts were not preserved.")
            report = {"status": "features_complete_audit_review_required", "feature_identity_sha256": identity_sha,
                      "partitions": summaries, "support_limitations": frozen["support_limitations"],
                      "unannotated_india_categories": 5, "synthetic_negative_labels_added": 0,
                      "training_performed": False, "ready_for_training": False, "baseline_reproduction_assessed": False,
                      "review_required": ["question_truncation", "projected_token_boundaries", "long_or_unmapped_answers",
                                          "answers_missing_from_regular_windows", "positive_questions_without_usable_windows"],
                      "evaluation_gold": "All original answer occurrences retained, including unsupported targets."}
            atomic_json(root / "report.json", report)
            atomic_json(root / "manifest.json", {"feature_identity_sha256": identity_sha, "partitions": entries,
                                                 "report_sha256": canonical_sha256(report), "complete": True})
        saved = sum(len(v) for v in entries.values())
        total_groups = sum(len(bundle[s + ".json"]["groups"]) for s in ROLES)
        print(f"New group shards: {new}; saved: {saved}/{total_groups}", flush=True)
        for split, c in summaries.items():
            print(f"{split}: {c['questions']} questions; {c['windows']} windows "
                  f"({c['positive_windows']} positive; {c['negative_windows']} negative; {c['ignored_windows']} ignored)", flush=True)
        totals = Counter()
        for c in summaries.values():
            totals.update(c)
        print(f"Gold occurrences: {totals['answer_occurrences']}; usable: {totals['covered_answer_occurrences']}; "
              f"long: {totals['long_answer_occurrences']}; unmapped: {totals['unmapped_answer_occurrences']}; "
              f"regular-window gaps: {totals['regular_window_gap_occurrences']}")
        print(f"Truncated questions: {totals['truncated_questions']}; positive questions without usable windows: "
              f"{totals['positive_questions_without_usable_windows']}")
        print("PASS: all frozen features verified; review feature report before training." if complete
              else "PASS: limited feature run verified; rerun without --partition/--limit-groups to finish.")
        print(f"Output: {OUTPUT_BASE}/{name}/")
        print("No sampling, QA head, model training, calibration or operating-policy selection performed.")
    return summaries, complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partition", choices=tuple(ROLES))
    parser.add_argument("--limit-groups", type=int)
    parser.add_argument("--run-name", default="features_v1")
    args = parser.parse_args()
    prepare(Path(__file__).resolve().parents[2], args.partition, args.limit_groups, args.run_name)


if __name__ == "__main__":
    main()
