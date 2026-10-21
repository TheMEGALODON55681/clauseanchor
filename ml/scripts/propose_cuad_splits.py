"""Propose deterministic, family-isolated CUAD splits for review before freezing.

Run: python ml/scripts/propose_cuad_splits.py
Requires prepare_cuad_pool.py outputs and ml/configs/cuad_split_policy.json.
Writes ignored data/processed/cuad/split_proposal.json and split_report.json.
No downloads, new dependencies, source edits, training or final split approval.

Plan v1.2 section 4.2 specifies 70/10/10/10 and seed 42. Integer targets apply
to original source-document counts, including both duplicate identities. Whole
confirmed families remain indivisible. Multi-document families are placed first
(largest first), balanced against their own 70/10/10/10 document quotas, to avoid
concentrating that entire cohort in fit or leaving unfillable small capacities. Remaining families
are assigned using iterative rare-label stratification. Labels are positive
category presence per independent family, not answer/window counts. This is a
deterministic heuristic, not an optimality or per-category support guarantee.

For the multi-document cohort, its document-quota deficit takes priority. Then
choose by rare-label quota deficit, normalized deficits across the family's
labels, and remaining document capacity. SHA-256 ties incorporate
seed 42, avoiding runtime-specific RNG and dictionary-order effects. There is
one fixed run: no search over seeds and no use of model scores or test labels.
Infeasible exact document targets fail rather than splitting a family.

The report exposes missing positive/no-answer support. It does not establish
calibration or threshold support, which also requires independent predictions.
Proposals cannot authorize training or replace baseline benchmark files. The
review manifest's approval flag remains unchanged; a later freeze must record
the reviewed assignment digest before downstream training can consume it.
"""

from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path

from audit_cuad_categories import save_outputs
from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, fields, read_json
from prepare_cuad_pool import OUTPUT_DIR, prepare


POLICY_PATH = "ml/configs/cuad_split_policy.json"
SPLITS = ("fit", "dev_select", "dev_cal", "dev_policy")
PERCENTAGES = dict(zip(SPLITS, (70, 10, 10, 10)))
ALGORITHM = "cohort_balanced_iterative_multilabel_family_v1"
FIXED_POLICY = {
    "split_policy_version": "1.0.0", "scope": "proposal_only",
    "plan_reference": "ClauseAnchor_Plan.md v1.2, section 4.2",
    "algorithm": ALGORITHM, "seed": 42, "split_percentages": PERCENTAGES,
    "size_unit": "source_documents",
    "stratification_unit": "positive_category_presence_per_family",
    "integer_rounding": "largest_remainder_ties_in_split_order",
}
BINDINGS = ("preparation_pool_canonical_sha256", "family_manifest_canonical_sha256",
            "question_set_canonical_sha256")


def validate_policy(policy, pool, preparation_report):
    fields(policy, set(FIXED_POLICY) | set(BINDINGS), "split policy")
    require(canonical_sha256({k: policy[k] for k in FIXED_POLICY}) == canonical_sha256(FIXED_POLICY),
            "Split policy differs from the reviewed version, ratios, seed or proposal scope.")
    require(policy[BINDINGS[0]] == canonical_sha256(pool) == preparation_report["pool_canonical_sha256"],
            "Prepared pool differs from the pinned split input.")
    for name in BINDINGS[1:]:
        require(policy[name] == pool["bindings"][name] == preparation_report["bindings"][name],
                "Preparation input binding changed.")


def integer_targets(total):
    """Hamilton rounding; tie order is fit/select/cal/policy, recorded in policy."""
    require(type(total) is int and total >= 0, "Invalid target count.")
    targets = {s: total * PERCENTAGES[s] // 100 for s in SPLITS}
    order = sorted(SPLITS, key=lambda s: (-(total * PERCENTAGES[s] % 100), SPLITS.index(s)))
    for s in order[:total - sum(targets.values())]:
        targets[s] += 1
    return targets


def family_inventory(pool):
    families, seen_groups, seen_titles = {}, set(), set()
    for g in pool["groups"]:
        gid, fid = g["group_id"], g["family_id"]
        require(g["official_split"] == "train", "Official test cannot enter internal split proposals.")
        require(gid not in seen_groups, "Repeated exact group in pool.")
        seen_groups.add(gid)
        require(bool(g["source_titles"]) and len(set(g["source_titles"])) == len(g["source_titles"]),
                "Empty or repeated source titles within a group.")
        require(not seen_titles.intersection(g["source_titles"]), "Source title occurs in multiple groups.")
        seen_titles.update(g["source_titles"])
        f = families.setdefault(fid, {"family_id": fid, "group_ids": [], "source_titles": [], "labels": set()})
        f["group_ids"].append(gid)
        f["source_titles"].extend(g["source_titles"])
        for p in g["paragraphs"]:
            for q in p["questions"]:
                require(q["category_id"].startswith("cuad."), "Unannotated extension cannot enter stratification.")
                if q["answers"]:
                    f["labels"].add(q["category_id"])
    require(bool(families), "Preparation pool is empty.")
    return [{"family_id": fid, "group_ids": sorted(f["group_ids"]),
             "source_titles": sorted(f["source_titles"]), "labels": sorted(f["labels"])}
            for fid, f in sorted(families.items())]


def tie(seed, *parts):
    return canonical_sha256([seed, *parts])


def assign_families(families, seed=42):
    """One deterministic greedy run with exact source-document capacities."""
    pending = {f["family_id"]: f for f in families}
    require(len(pending) == len(families) and bool(pending), "Empty or repeated family IDs.")
    total_documents = sum(len(f["source_titles"]) for f in families)
    targets = integer_targets(total_documents)
    remaining = dict(targets)
    large_targets = integer_targets(sum(len(f["source_titles"]) for f in families if len(f["source_titles"]) > 1))
    large_assigned = Counter()
    label_total = Counter(label for f in families for label in f["labels"])
    label_remaining = label_total.copy()
    label_target = {label: integer_targets(n) for label, n in label_total.items()}
    assigned_labels = {s: Counter() for s in SPLITS}
    assigned = {}
    while pending:
        large = [f for f in pending.values() if len(f["source_titles"]) > 1]
        focus = min((label for label, n in label_remaining.items() if n > 0),
                    key=lambda label: (label_remaining[label], tie(seed, "label", label)), default=None)
        if large:
            largest = max(len(f["source_titles"]) for f in large)
            candidates = [f for f in large if len(f["source_titles"]) == largest]
        else:
            candidates = [f for f in pending.values() if focus is None or focus in f["labels"]]
        def family_rank(f):
            return (sum((Fraction(1, label_remaining[label]) for label in f["labels"]), Fraction()),
                    tie(seed, "family", f["family_id"]))
        chosen = max(candidates, key=family_rank)
        fid, labels, size = chosen["family_id"], chosen["labels"], len(chosen["source_titles"])
        if large:
            focus = min(labels, key=lambda label: (label_remaining[label], tie(seed, "label", label)), default=None)
        available = [s for s in SPLITS if remaining[s] >= size]
        require(bool(available), "Exact document targets cannot fit a remaining whole family; review split policy.")
        def split_rank(s):
            return (
                large_targets[s] - large_assigned[s] if large else 0,
                label_target[focus][s] - assigned_labels[s][focus] if focus else 0,
                sum((Fraction(label_target[label][s] - assigned_labels[s][label], label_total[label])
                     for label in labels), Fraction()),
                Fraction(remaining[s], targets[s]) if targets[s] else Fraction(),
                remaining[s], tie(seed, "split", fid, s),
            )
        selected = max(available, key=split_rank)
        assigned[fid] = selected
        remaining[selected] -= size
        if large:
            large_assigned[selected] += size
        assigned_labels[selected].update(labels)
        label_remaining.subtract(labels)
        del pending[fid]
    require(all(n == 0 for n in remaining.values()), "Document targets were not met.")
    return [{"family_id": f["family_id"], "proposed_split": assigned[f["family_id"]],
             "group_ids": f["group_ids"], "source_titles": f["source_titles"]}
            for f in sorted(families, key=lambda f: f["family_id"])]


def validate_assignments(assignments, families, seed=42):
    """Reject omitted, duplicated, changed or nonreproducible assignments."""
    expected = assign_families(families, seed)
    require(canonical_sha256(assignments) == canonical_sha256(expected),
            "Assignments differ from the complete deterministic family proposal.")
    return {r["family_id"]: r["proposed_split"] for r in assignments}


def summarize(pool, assignments, category_rows):
    by_family = {r["family_id"]: r["proposed_split"] for r in assignments}
    counts = {s: Counter() for s in SPLITS}
    family_sets = {s: set() for s in SPLITS}
    per_category = {(s, r["category_id"]): Counter() for s in SPLITS for r in category_rows}
    category_sets = defaultdict(set)
    for a in assignments:
        if len(a["source_titles"]) > 1:
            counts[a["proposed_split"]]["multi_source_document_families"] += 1
            counts[a["proposed_split"]]["source_documents_in_multi_source_document_families"] += len(a["source_titles"])
    for g in pool["groups"]:
        split, fid, gid = by_family[g["family_id"]], g["family_id"], g["group_id"]
        counts[split]["source_documents"] += len(g["source_titles"])
        counts[split]["exact_text_groups"] += 1
        family_sets[split].add(fid)
        for p in g["paragraphs"]:
            for q in p["questions"]:
                cid = q["category_id"]
                stat = per_category[(split, cid)]
                state = "positive_questions" if q["answers"] else "no_answer_questions"
                for counter in (counts[split], stat):
                    counter["questions"] += 1
                    counter[state] += 1
                    counter["answer_spans"] += len(q["answers"])
                category_sets[(split, cid, "annotated_family_units")].add(fid)
                category_sets[(split, cid, "annotated_exact_groups")].add(gid)
                if q["answers"]:
                    category_sets[(split, cid, "positive_family_units")].add(fid)
                    category_sets[(split, cid, "positive_exact_groups")].add(gid)
    metric_keys = ("questions", "positive_questions", "no_answer_questions", "answer_spans")
    summary = {s: {**{k: counts[s][k] for k in ("source_documents", "exact_text_groups", *metric_keys,
                                              "multi_source_document_families", "source_documents_in_multi_source_document_families")},
                   "family_units": len(family_sets[s])} for s in SPLITS}
    support, gaps = [], []
    for row in category_rows:
        cid = row["category_id"]
        split_support = {}
        for s in SPLITS:
            stat = per_category[(s, cid)]
            split_support[s] = {
                **{k: stat[k] for k in metric_keys},
                **{k: len(category_sets[(s, cid, k)]) for k in (
                    "annotated_family_units", "annotated_exact_groups", "positive_family_units", "positive_exact_groups")},
            }
            if row["annotation_status"] == "cuad_annotated":
                for metric, reason in (("positive_questions", "no_positive_examples"),
                                       ("no_answer_questions", "no_no_answer_examples")):
                    if stat[metric] == 0:
                        gaps.append({"category_id": cid, "split": s, "reason": reason})
        support.append({"category_id": cid, "annotation_status": row["annotation_status"], "splits": split_support})
    return summary, support, gaps


def propose(repo):
    # Reconstruct independently from pinned raw inputs; never trust an edited pool
    # merely because an accompanying report was edited to match it.
    expected_pool, expected_report = prepare(repo)
    pool = read_json(repo / OUTPUT_DIR / "preparation_pool.json")
    preparation_report = read_json(repo / OUTPUT_DIR / "preparation_report.json")
    require(canonical_sha256(pool) == canonical_sha256(expected_pool)
            and canonical_sha256(preparation_report) == canonical_sha256(expected_report),
            "Saved preparation outputs differ from validated source reconstruction.")
    policy = read_json(repo / POLICY_PATH)
    validate_policy(policy, pool, preparation_report)
    families = family_inventory(pool)
    assignments = assign_families(families, policy["seed"])
    validate_assignments(assignments, families, policy["seed"])
    summary, support, gaps = summarize(pool, assignments, preparation_report["category_support"])
    proposal = {
        "proposal_version": "1.0.0", "status": "awaiting_review_and_freeze", "ready_for_training": False,
        "policy_canonical_sha256": canonical_sha256(policy),
        "preparation_pool_canonical_sha256": canonical_sha256(pool),
        "assignment_canonical_sha256": canonical_sha256(assignments),
        "assignments": assignments,
    }
    report = {
        "report_version": "1.0.0", "proposal_canonical_sha256": canonical_sha256(proposal),
        "policy": policy, "document_targets": integer_targets(preparation_report["summary"]["source_documents"]),
        "summary": summary, "category_support": support, "support_gaps": gaps,
        "unannotated_category_ids": [r["category_id"] for r in support if r["annotation_status"] == "unannotated_in_cuad"],
        "limitations": [
            "A split proposal is not frozen training authorization.",
            "Positive examples in a partition do not establish calibration or operating-threshold support.",
            "Per-category presence calibration needs 50 items; these small development partitions cannot provide that.",
            "Calibration fallbacks and review-only categories must follow plan section 6.4 after predictions exist.",
            "No official test annotations or model predictions were used to assign families.",
        ],
    }
    return proposal, report


def main():
    repo = Path(__file__).resolve().parents[2]
    proposal, report = propose(repo)
    output = (repo / OUTPUT_DIR).resolve()
    require(output.is_relative_to((repo / "data").resolve()), "Output must stay inside repository data/.")
    payloads = {output / name: (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
                for name, value in (("split_proposal.json", proposal), ("split_report.json", report))}
    created = save_outputs(payloads)
    print("Pinned preparation pool, source reconstruction and split policy: verified")
    print("Proposal: 70/10/10/10 by source documents; seed 42; whole-family multi-label stratification")
    for s in SPLITS:
        c = report["summary"][s]
        print(f"{s}: {c['source_documents']} source documents; {c['exact_text_groups']} exact groups; "
              f"{c['family_units']} families; {c['questions']} questions")
    print(f"Category/partition support gaps: {len(report['support_gaps'])}; see split_report.json")
    print("India-extension categories: 5 unannotated; no synthetic negative labels added")
    print(f"Assignment SHA-256: {proposal['assignment_canonical_sha256']}")
    print(f"Created {created} split proposal files." if created else "Existing proposal outputs match; no files changed.")
    print(f"Outputs: {OUTPUT_DIR}/split_proposal.json and split_report.json")
    print("PASS: complete deterministic proposal; all families remain together; official sources unchanged.")
    print("Proposal only: review and freeze the assignment digest before training. No tokenizer features created.")


if __name__ == "__main__":
    main()
