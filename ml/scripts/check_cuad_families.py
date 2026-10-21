"""Validate reviewed CUAD families without creating splits or changing data.

Run from the repository root: python ml/scripts/check_cuad_families.py
Requires the official downloads and the frozen similarity/title reports.
Uses only the project's existing data dependencies; no downloads are made.

Manifest 2.0.0 adds title decisions, manual title review and conservative holds.
The unchanged 1.0.0 snapshot remains reproducible and defines the title screen's
original IDs. Canonical JSON hashes ignore key order and file spacing.

Passing verifies prospective policy accounting. It does not write filtered
examples, adjudicate unresolved evidence, or authorize internal partitions.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path

from audit_cuad_questions import require
from build_cuad_inventory import build_groups, load_sources


REPORT_PATH = "data/processed/cuad/similarity_candidates.json"
LEGACY_MANIFEST_PATH = "ml/configs/cuad_family_manifest_v1.json"
POLICIES = {
    "internal_partitions": ["fit", "dev_select", "dev_cal", "dev_policy"],
    "related_records": "keep_connected_family_together",
    "cross_split_training_members": "exclude_from_all_internal_partitions",
    "official_memberships": "preserve",
    "test_reporting": "full_official_test_plus_separate_known_overlap_sensitivity",
    "source_annotations": "preserve_per_record_no_automatic_transfer",
    "duplicate_label_conflicts": "hold_disputed_questions_until_adjudicated",
}
REVIEW_DOCS = {
    True: "docs/ml/CUAD_CrossSplitReview.md",
    False: "docs/ml/CUAD_TrainingFamilyReview.md",
}
RELATIONSHIPS = {
    "agreement_variants", "parent_attachment", "agreement_attachment_coverage",
    "exact_context_containment",
}


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def family_id(group_ids):
    return "cuad-family-v1:" + canonical_sha256(sorted(group_ids))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Non-finite JSON value: {value}")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object, parse_constant=reject_constant)


def fields(value, expected, label):
    require(type(value) is dict and set(value) == set(expected),
            f"Unexpected or missing fields in {label}.")


def member_record(group):
    return {
        "group_id": group["group_id"],
        "official_split": group["official_split"],
        "source_titles": [d["title"] for d in group["source_documents"]],
        "paragraphs": group["paragraphs"],
    }


def components(ids, edges):
    parent = {key: key for key in ids}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for a, b in edges:
        require(a in parent and b in parent, "Edge refers to a nonmember group.")
        parent[root(a)] = root(b)
    result = {}
    for key in sorted(parent):
        result.setdefault(root(key), []).append(key)
    return sorted(result.values())


def validate_manifest(manifest, report, groups, provenance):
    """Validate the frozen v1 scope, also used to reproduce the title screen."""
    fields(manifest, {"manifest_version", "review_scope", "provenance", "policies",
                      "families", "expected_summary"}, "manifest")
    require(manifest["manifest_version"] == "1.0.0", "Unsupported family manifest version.")
    scope = manifest["review_scope"]
    fields(scope, {"screen_version", "candidate_report", "candidate_report_canonical_sha256",
                   "screen_candidates_reviewed", "broader_family_review",
                   "ready_for_internal_splits"}, "review_scope")
    require(scope["screen_version"] == report["screen_version"] == "1.0.0",
            "Screen version mismatch.")
    require(scope["candidate_report"] == REPORT_PATH, "Unexpected candidate-report path.")
    require(scope["candidate_report_canonical_sha256"] == canonical_sha256(report),
            "Candidate report changed; review the new screen before updating the manifest.")
    require(scope["screen_candidates_reviewed"] is True, "Candidate review is incomplete.")
    require(scope["broader_family_review"] == "pending"
            and scope["ready_for_internal_splits"] is False,
            "This manifest does not approve internal splits; broader review remains pending.")
    require(canonical_bytes(manifest["provenance"]) == canonical_bytes(provenance)
            == canonical_bytes(report["provenance"]), "Source provenance mismatch.")
    require(canonical_bytes(manifest["policies"]) == canonical_bytes(POLICIES),
            "Preparation policy changed; a separate reviewed revision is required.")

    by_id = {g["group_id"]: g for g in groups}
    require(len(by_id) == len(groups), "Duplicate source group ID.")
    candidates, candidate_edges = {}, set()
    for candidate in report["candidates"]:
        rid = candidate["review_id"]
        require(type(rid) is str and rid not in candidates, "Duplicate/invalid candidate ID.")
        pair = []
        for side in ("left", "right"):
            metadata = candidate[side]
            gid = metadata["group_id"]
            require(gid in by_id, "Candidate contains an unknown source group.")
            expected = member_record(by_id[gid])
            require(canonical_bytes({k: metadata[k] for k in expected}) == canonical_bytes(expected),
                    "Candidate source identity changed.")
            pair.append(gid)
        edge = tuple(sorted(pair))
        require(edge[0] != edge[1] and edge not in candidate_edges,
                "Self-pair or duplicate candidate edge.")
        cross = by_id[pair[0]]["official_split"] != by_id[pair[1]]["official_split"]
        require(candidate["crosses_official_split"] is cross, "Candidate split flag is wrong.")
        candidates[rid] = (edge, cross)
        candidate_edges.add(edge)

    require(type(manifest["families"]) is list, "families must be a list.")
    used_members, reviewed, all_edges = set(), set(), []
    family_splits = Counter()
    for family in manifest["families"]:
        fields(family, {"family_id", "members", "decisions"}, "family")
        require(type(family["members"]) is list and len(family["members"]) >= 2,
                "A reviewed family needs at least two distinct exact-text groups.")
        ids = []
        for member in family["members"]:
            fields(member, {"group_id", "official_split", "source_titles", "paragraphs"}, "member")
            gid = member["group_id"]
            require(gid in by_id and gid not in used_members, "Unknown or repeated family member.")
            require(canonical_bytes(member) == canonical_bytes(member_record(by_id[gid])),
                    "Family member identity, membership, or paragraph hash differs from source.")
            used_members.add(gid)
            ids.append(gid)
        require(family["family_id"] == family_id(ids), "Family ID does not match its members.")
        require(type(family["decisions"]) is list and family["decisions"], "Family needs review edges.")
        edges = []
        for decision in family["decisions"]:
            fields(decision, {"review_id", "group_ids", "decision", "relationship",
                              "evidence_document", "reason"}, "decision")
            rid = decision["review_id"]
            require(type(rid) is str and rid in candidates and rid not in reviewed,
                    "Unknown or repeated review ID.")
            expected_edge, cross = candidates[rid]
            require(type(decision["group_ids"]) is list
                    and canonical_bytes(decision["group_ids"]) == canonical_bytes(list(expected_edge)),
                    "Review edge does not match its screened pair in sorted order.")
            require(set(expected_edge) <= set(ids), "Review edge crosses declared families.")
            require(decision["decision"] == "confirmed_related_for_split_grouping",
                    "Unsupported or unreviewed decision.")
            require(decision["relationship"] in RELATIONSHIPS, "Unknown relationship.")
            require(decision["evidence_document"] == REVIEW_DOCS[cross], "Wrong evidence document.")
            require(type(decision["reason"]) is str and decision["reason"].strip(), "Missing review reason.")
            reviewed.add(rid)
            edges.append(expected_edge)
        require(len(components(ids, edges)) == 1, "Disconnected family; unrelated members cannot be merged.")
        all_edges.extend(edges)
        splits = {by_id[gid]["official_split"] for gid in ids}
        family_splits["cross" if len(splits) > 1 else next(iter(splits))] += 1
    require(reviewed == set(candidates), "Some screened candidates have no recorded decision.")

    # Components include unchanged singleton exact groups as well as reviewed families.
    all_components = components(by_id, all_edges)
    cross_groups, eligible_components = set(), []
    for ids in all_components:
        splits = {by_id[gid]["official_split"] for gid in ids}
        if len(splits) > 1:
            cross_groups.update(ids)
        elif splits == {"train"}:
            eligible_components.append(ids)
    eligible = {gid for ids in eligible_components for gid in ids}
    docs_by_split = Counter()
    excluded = Counter()
    for gid, group in by_id.items():
        count = len(group["source_documents"])
        docs_by_split[group["official_split"]] += count
        if gid in cross_groups:
            excluded[group["official_split"]] += count
    summary = {
        "source_documents": sum(docs_by_split.values()),
        "exact_text_groups": len(groups),
        "official_train_documents": docs_by_split["train"],
        "official_test_documents": docs_by_split["test"],
        "reviewed_candidate_pairs": len(reviewed),
        "reviewed_families": len(manifest["families"]),
        "reviewed_member_groups": len(used_members),
        "training_only_families": family_splits["train"],
        "cross_split_families": family_splits["cross"],
        "prospective_training_exclusions": excluded["train"],
        "prospective_eligible_training_documents": sum(len(by_id[g]["source_documents"]) for g in eligible),
        "prospective_eligible_exact_groups": len(eligible),
        "prospective_internal_family_units": len(eligible_components),
        "prospective_sensitivity_test_documents": docs_by_split["test"] - excluded["test"],
    }
    require(canonical_bytes(manifest["expected_summary"]) == canonical_bytes(summary),
            "Expected family counts differ from the verified source and decisions.")
    return summary


def main():
    repo_root = Path(__file__).resolve().parents[2]
    full, train, test, provenance = load_sources(repo_root)
    groups = build_groups(full, train, test)
    manifest = read_json(repo_root / "ml/configs/cuad_family_manifest.json")
    report = read_json(repo_root / REPORT_PATH)
    if manifest["manifest_version"] == "2.0.0":
        from cuad_review_policy import TITLE_PATH, validate_review_manifest

        require((repo_root / TITLE_PATH).is_file(),
                "Missing title report. Run python ml/scripts/review_cuad_titles.py first.")
        summary = validate_review_manifest(
            manifest, read_json(repo_root / LEGACY_MANIFEST_PATH), report,
            read_json(repo_root / TITLE_PATH), groups, provenance, evidence_root=repo_root,
        )
        print("Pinned sources, spans, archived manifest, reports and review evidence: verified")
        print("Family manifest version: 2.0.0")
        print(f"Lexical decisions: {summary['lexical_reviewed_pairs']}; title decisions: "
              f"{summary['title_reviewed_pairs']} ({summary['title_confirmed_pairs']} confirmed; "
              f"{summary['title_rejected_pairs']} rejected; {summary['title_unresolved_pairs']} unresolved)")
        print(f"Manual title reviews: {summary['manual_title_reviews']}")
        print(f"Training reservations: {summary['prospective_training_exclusions']} documents "
              f"({summary['confirmed_cross_split_training_exclusions']} confirmed cross-split; "
              f"{summary['unresolved_training_hold_documents']} unresolved holds; union counted)")
        print(f"Question holds: {summary['held_original_question_records']} original records; "
              f"{summary['held_group_category_questions']} group/category questions")
        print(f"Prospective internal pool: {summary['prospective_eligible_training_documents']} documents; "
              f"{summary['prospective_eligible_exact_groups']} exact groups; "
              f"{summary['prospective_internal_family_units']} family units")
        print(f"Official test: {summary['official_test_documents']}; known-overlap sensitivity: "
              f"{summary['prospective_sensitivity_test_documents']}")
        print("PASS: reviewed decisions, connected families and conservative holds verified.")
        print("Internal split assignment: not approved; preparation must enforce the validated policy.")
        print("Read-only check: no source edits, filtered examples or partitions written.")
        return
    summary = validate_manifest(manifest, report, groups, provenance)
    for relative in REVIEW_DOCS.values():
        require((repo_root / relative).is_file(), f"Missing evidence note: {relative}")
    print("Pinned source, spans, official memberships and candidate-report digest: verified")
    print(f"Family manifest version: {manifest['manifest_version']}")
    print(f"Reviewed candidate pairs: {summary['reviewed_candidate_pairs']}")
    print(f"Reviewed families: {summary['reviewed_families']} ({summary['training_only_families']} training-only; "
          f"{summary['cross_split_families']} cross-split)")
    print(f"Exact-text groups in reviewed families: {summary['reviewed_member_groups']}")
    print(f"Prospective training-side exclusions: {summary['prospective_training_exclusions']}")
    print(f"Prospective internal pool: {summary['prospective_eligible_training_documents']} documents; "
          f"{summary['prospective_eligible_exact_groups']} exact groups; "
          f"{summary['prospective_internal_family_units']} family units")
    print(f"Official test: {summary['official_test_documents']} documents; prospective sensitivity subset: "
          f"{summary['prospective_sensitivity_test_documents']}")
    print("PASS: reviewed relationships, connected families and handling policy verified.")
    print("Broader family review: pending. Internal split assignment: not approved.")
    print("Read-only check: no files changed; no exclusions, label changes or splits applied.")


if __name__ == "__main__":
    main()
