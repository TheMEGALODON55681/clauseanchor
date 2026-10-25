"""All-window dev_select decoding and anchored-span checkpoint selection.

Caller verifies the frozen feature/plan chain and holds its locks. No fit,
calibration, policy or official-test examples may enter this evaluator. Margin
> 0 is a fixed, uncalibrated decoder setting, NOT a deployment threshold.
Every original gold occurrence remains in the audit; identical annotations of
one character interval count once for occurrence matching. Distinct locations
with identical text remain separate. Long/uncovered gold stays in recall.
"""

from bisect import bisect_left, insort
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import linear_sum_assignment

from audit_cuad_questions import require
from check_cuad_families import read_json

POLICY = {"version": 1, "partition": "dev_select", "top_start_end": 20,
          "per_window_candidates": 20, "max_answer_tokens": 256, "nms_iou": 0.8,
          "candidate_cap": 50, "matching_iou": 0.5, "matching": "maximum_total_interval_iou",
          "selection_margin_strictly_greater_than": 0.0, "gold": "unique_source_intervals",
          "selection": "macro_category_anchored_span_f1", "calibrated": False,
          "boundary_candidates": "included_in_raw_metrics_review_only_for_deployment"}


def interval_iou(a, b):
    overlap = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    return overlap / (a[1] - a[0] + b[1] - b[0] - overlap)


def window_candidates(start, end, sequences, offsets, context, row, clipped_left, clipped_right):
    require(start.shape == end.shape == sequences.shape and offsets.shape == (len(start), 2)
            and np.isfinite(start).all() and np.isfinite(end).all(), "Invalid decoder logits or maps.")
    positions = np.flatnonzero(sequences == 1)
    require(len(positions) > 0, "Window has no context tokens.")
    spans = offsets[positions]
    require(((spans[:, 0] >= 0) & (spans[:, 0] <= spans[:, 1]) & (spans[:, 1] <= len(context))).all(),
            "Context offset outside source text.")
    valid = positions[spans[:, 0] < spans[:, 1]]
    require(len(valid) > 0, "No nonempty context token.")
    # Score ties resolve by lower token index, independent of sort implementation.
    starts = valid[np.lexsort((valid, -start[valid]))[:20]]
    ends = valid[np.lexsort((valid, -end[valid]))[:20]]
    null = float(start[0]) + float(end[0])
    candidates = []
    for s in starts:
        for e in ends:
            if not s <= e < s + 256:
                continue
            left, right = int(offsets[s, 0]), int(offsets[e, 1])
            require(0 <= left < right <= len(context), "Invalid decoded source interval.")
            candidates.append({"start": left, "end": right, "text": context[left:right],
                               "margin": float(start[s]) + float(end[e]) - null,
                               "window_row": int(row), "start_token": int(s), "end_token": int(e),
                               "null_score": null,
                               "boundary_review": bool((clipped_left and s == valid[0])
                                                       or (clipped_right and e == valid[-1]))})
    return sorted(candidates, key=lambda c: (-c["margin"], c["start"], c["end"], c["start_token"], c["end_token"]))[:20]


def deduplicate(candidates):
    """Exact-range dedup then score-ordered interval NMS; never concatenate."""
    ordered = sorted(candidates, key=lambda c: (-c["margin"], c["boundary_review"], c["start"], c["end"], c["window_row"]))
    exact = {}
    complete_ranges = {(c["start"], c["end"]) for c in candidates if not c["boundary_review"]}
    for item in ordered:
        key = (item["start"], item["end"])
        if key not in exact:
            exact[key] = {**item, "boundary_review": key not in complete_ranges}
            # Coordinates are identical; keep the highest score and note that
            # at least one window contained the complete same source interval.
    maximum_length = max((b - a for a, b in exact), default=0)
    kept, intervals = [], []
    for candidate in exact.values():
        a, b = candidate["start"], candidate["end"]
        left = bisect_left(intervals, (a - maximum_length,))
        right = bisect_left(intervals, (b,))
        if any(interval_iou((a, b), (x, y)) >= 0.8 for x, y in intervals[left:right]):
            continue
        kept.append(candidate)
        insort(intervals, (a, b))
    return kept


def match_counts(candidates, gold):
    predicted = [(c["start"], c["end"]) for c in candidates]
    unique_gold = sorted({(a["start"], a["end"]) for a in gold})
    require(all(0 <= a < b for a, b in predicted + unique_gold), "Invalid scoring interval.")
    matches = []
    if predicted and unique_gold:
        overlap = np.array([[interval_iou(p, g) for g in unique_gold] for p in predicted])
        rows, cols = linear_sum_assignment(np.where(overlap >= 0.5, overlap, 0.0), maximize=True)
        matches = [(predicted[i], unique_gold[j]) for i, j in zip(rows, cols) if overlap[i, j] >= 0.5]
    return {"tp": len(matches), "fp": len(predicted) - len(matches), "fn": len(unique_gold) - len(matches),
            "predicted": len(predicted), "gold": len(unique_gold), "original_gold_records": len(gold),
            "exact_matches": sum(p == g for p, g in matches),
            "start_error_sum": sum(abs(p[0] - g[0]) for p, g in matches),
            "end_error_sum": sum(abs(p[1] - g[1]) for p, g in matches)}


def summarize(counts):
    tp, predicted, gold = counts["tp"], counts["predicted"], counts["gold"]
    return {**dict(counts), "precision": tp / predicted if predicted else None,
            "recall": tp / gold if gold else None,
            "f1": 2 * tp / (predicted + gold) if gold else None,
            "exact_match_recall": counts["exact_matches"] / gold if gold else None,
            "mean_start_error": counts["start_error_sum"] / tp if tp else None,
            "mean_end_error": counts["end_error_sum"] / tp if tp else None}


def aggregate(rows, key):
    categories = defaultdict(Counter)
    for row in rows:
        categories[row["category_id"]].update(row[key])
        categories[row["category_id"]]["questions"] += 1
    scored = {cat: summarize(counts) for cat, counts in sorted(categories.items())}
    supported = [c["f1"] for c in scored.values() if c["f1"] is not None]
    total = sum(categories.values(), Counter())
    # Counter addition drops zero values, so restore metric keys explicitly.
    for name in ("tp", "fp", "fn", "predicted", "gold", "original_gold_records", "exact_matches", "start_error_sum", "end_error_sum"):
        total.setdefault(name, 0)
    return {"categories": scored, "micro": summarize(total),
            "macro_f1": sum(supported) / len(supported) if supported else None,
            "supported_categories": len(supported), "unsupported_categories": [c for c, v in scored.items() if v["f1"] is None]}


def evaluate(model, feature_root, device, batch_size=4, probe=False):
    """Probe: first fixed question, all its windows, never selection eligible."""
    require(type(batch_size) is int and batch_size > 0, "Invalid evaluation batch size.")
    root = Path(feature_root)
    manifest = read_json(root / "manifest.json")
    entries = manifest["partitions"]["dev_select"]
    require(bool(entries) and all(e["path"].startswith("dev_select/") and len(e["path"].split("/")) == 2
                                and e["path"].split("/")[1] not in ("", ".", "..")
                                and "\\" not in e["path"] for e in entries), "Evaluator accepts dev_select only.")
    model.eval()
    rows, predictions, window_total, question_total = [], [], 0, 0
    expected_questions = sum(e["summary"]["questions"] for e in entries)
    expected_windows = sum(e["summary"]["windows"] for e in entries)
    with torch.inference_mode():
        for entry in entries:
            directory = root / entry["path"]
            source = read_json(directory / "source.json")["source_group"]
            require(source["official_split"] == "train", "Official test cannot enter development selection.")
            questions = [(p, q) for p in source["paragraphs"] for q in p["questions"]]
            arrays = {}
            try:
                for name in ("input_ids", "attention_mask", "sequence_ids", "offsets", "question_ranges"):
                    arrays[name] = np.load(directory / (name + ".npy"), mmap_mode="r", allow_pickle=False)
                for qi, (paragraph, question) in enumerate(questions):
                    begin, end = map(int, arrays["question_ranges"][qi])
                    candidates = []
                    for offset in range(begin, end, batch_size):
                        stop = min(offset + batch_size, end)
                        ids = torch.tensor(np.array(arrays["input_ids"][offset:stop]), dtype=torch.long, device=device)
                        mask = torch.tensor(np.array(arrays["attention_mask"][offset:stop]), dtype=torch.long, device=device)
                        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                            output = model(input_ids=ids, attention_mask=mask)
                        starts, ends = output.start_logits.float().cpu().numpy(), output.end_logits.float().cpu().numpy()
                        for j, row in enumerate(range(offset, stop)):
                            candidates.extend(window_candidates(starts[j], ends[j], arrays["sequence_ids"][row], arrays["offsets"][row],
                                                                paragraph["context"], row, row > begin, row < end - 1))
                        window_total += stop - offset
                    uncapped = deduplicate(candidates)
                    capped = uncapped[:50]
                    selected = [c for c in capped if c["margin"] > 0]
                    gold = question["answers"]
                    rows.append({"question_id": question["question_id"], "category_id": question["category_id"],
                                 "selection": match_counts(selected, gold), "unfiltered": match_counts(capped, gold),
                                 "uncapped": match_counts(uncapped, gold)})
                    predictions.append({"question_id": question["question_id"], "category_id": question["category_id"],
                                        "group_id": source["group_id"], "paragraph_index": paragraph["index"],
                                        "windows": end - begin, "candidates": capped,
                                        "uncapped_candidate_count": len(uncapped), "truncated": len(uncapped) >= 50,
                                        "absence_allowed": False})
                    question_total += 1
                    if probe:
                        break
                    if question_total % 100 == 0:
                        print(f"  dev_select: {question_total}/{expected_questions} questions; {window_total} windows", flush=True)
            finally:
                for array in arrays.values():
                    array._mmap.close()
            if probe:
                break
    require(probe or (question_total == expected_questions and window_total == expected_windows), "Incomplete development coverage.")
    require(len({r["question_id"] for r in rows}) == len(rows), "Repeated development question.")
    result = {"policy": POLICY, "status": "probe_only" if probe else "complete_dev_select",
              "selection_eligible": not probe, "questions": question_total, "windows": window_total,
              "selection": aggregate(rows, "selection"), "unfiltered": aggregate(rows, "unfiltered"),
              "uncapped": aggregate(rows, "uncapped"), "truncated_questions": sum(p["truncated"] for p in predictions),
              "per_question": rows, "predictions": predictions,
              "deployment_decisions_produced": False, "calibration_performed": False}
    result["cap_matched_gold_difference"] = result["uncapped"]["micro"]["tp"] - result["unfiltered"]["micro"]["tp"]
    return result
