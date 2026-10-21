"""Validate the reviewed title decisions and conservative preparation holds.

Version 2 extends the archived lexical manifest without rewriting either screen.
This module computes prospective eligibility; it writes no splits or examples.
"""

from collections import Counter
import hashlib

from audit_cuad_questions import require
from check_cuad_families import (
    LEGACY_MANIFEST_PATH, POLICIES, REVIEW_DOCS, canonical_sha256, components, family_id, fields,
    member_record, validate_manifest,
)


LEGACY_PATH = LEGACY_MANIFEST_PATH
TITLE_PATH = "data/processed/cuad/title_candidates.json"
POLICY_DOC = "docs/ml/CUAD_UnresolvedHandlingPolicy.md"
REVIEW_POLICIES = {
    **POLICIES,
    "unresolved_relationships": "hold_training_members_and_confirmed_family_closure",
    "unresolved_test_records": "retain_in_full_and_known_overlap_sensitivity",
    "held_question_uses": "exclude_loss_mining_selection_calibration_policy_and_scoring",
}
CONFLICT_CATEGORIES = {
    "Anti-Assignment": "cuad.anti_assignment",
    "Exclusivity": "cuad.exclusivity",
}
DECISIONS = {"confirmed", "rejected", "unresolved"}


def evidence_digest(path):
    """Normalize checkout line endings for prose only, never for source data."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def nonempty_text(value, label):
    require(type(value) is str and bool(value.strip()), f"Missing {label}.")


def question_holds(groups):
    """All source conflicts must be represented, including both duplicate copies."""
    result = []
    for group in groups:
        for conflict in group.get("annotation_conflicts", []):
            label = conflict["source_label"]
            require(label in CONFLICT_CATEGORIES,
                    "New conflicting category requires a reviewed hold-policy revision.")
            require(conflict["review_status"] == "pending_adjudication",
                    "Annotation review status changed; revise the policy.")
            result.append({
                "group_id": group["group_id"],
                "paragraph_index": conflict["paragraph_index"],
                "source_label": label,
                "category_id": CONFLICT_CATEGORIES[label],
                "source_question_ids": sorted(a["source_question_id"]
                                              for a in conflict["source_annotations"]),
                "evidence_document": "docs/ml/CUAD_DataReview.md",
            })
    return sorted(result, key=lambda q: (q["group_id"], q["paragraph_index"], q["source_label"]))


def preparation_view(groups, confirmed_edges, unresolved_edges):
    """Derive confirmed components, training reservations and sensitivity membership.

    Unresolved edges never join components. Their training endpoints seed holds,
    which cover all training members of any affected confirmed component.
    Call only with validated decisions; this is not split authorization.
    """
    by_id = {g["group_id"]: g for g in groups}
    cc = components(by_id, confirmed_edges)
    seeds = {gid for edge in unresolved_edges for gid in edge
             if by_id[gid]["official_split"] == "train"}
    cross, held, eligible = set(), set(), []
    for ids in cc:
        splits = {by_id[g]["official_split"] for g in ids}
        if len(splits) > 1:
            cross.update(ids)
        if seeds.intersection(ids):
            held.update(g for g in ids if by_id[g]["official_split"] == "train")
        if splits == {"train"} and not seeds.intersection(ids):
            eligible.append(ids)
    return {
        "families": [{"family_id": family_id(ids), "group_ids": ids}
                     for ids in cc if len(ids) > 1],
        "document_holds": sorted(held),
        "eligible_components": eligible,
        "cross_split_groups": sorted(cross),
        "reserved_training_groups": sorted(held | {
            g for g in cross if by_id[g]["official_split"] == "train"}),
        "sensitivity_test_groups": sorted(g for g in by_id
                                          if by_id[g]["official_split"] == "test" and g not in cross),
    }


def summarize(groups, legacy, decisions, manual_reviews, holds, view, already_count):
    by_id = {g["group_id"]: g for g in groups}
    def documents(ids):
        return sum(len(by_id[g]["source_documents"]) for g in ids)

    counts = Counter(d["decision"] for d in decisions)
    family_splits = Counter()
    for f in view["families"]:
        splits = {by_id[g]["official_split"] for g in f["group_ids"]}
        family_splits["cross" if len(splits) > 1 else next(iter(splits))] += 1
    eligible = [g for ids in view["eligible_components"] for g in ids]
    return {
        "source_documents": documents(by_id), "exact_text_groups": len(groups),
        "official_train_documents": documents(g for g in by_id if by_id[g]["official_split"] == "train"),
        "official_test_documents": documents(g for g in by_id if by_id[g]["official_split"] == "test"),
        "lexical_reviewed_pairs": sum(len(f["decisions"]) for f in legacy["families"]),
        "title_reviewed_pairs": len(decisions), "title_already_reviewed_pairs": already_count,
        "title_confirmed_pairs": counts["confirmed"], "title_rejected_pairs": counts["rejected"],
        "title_unresolved_pairs": counts["unresolved"], "manual_title_reviews": len(manual_reviews),
        "reviewed_families": len(view["families"]),
        "training_only_families": family_splits["train"],
        "cross_split_families": family_splits["cross"], "test_only_families": family_splits["test"],
        "confirmed_cross_split_training_exclusions": documents(
            g for g in view["cross_split_groups"] if by_id[g]["official_split"] == "train"),
        "unresolved_training_hold_documents": documents(view["document_holds"]),
        "prospective_training_exclusions": documents(view["reserved_training_groups"]),
        "prospective_eligible_training_documents": documents(eligible),
        "prospective_eligible_exact_groups": len(eligible),
        "prospective_internal_family_units": len(view["eligible_components"]),
        "prospective_sensitivity_test_documents": documents(view["sensitivity_test_groups"]),
        "held_group_category_questions": len(holds),
        "held_original_question_records": sum(len(q["source_question_ids"]) for q in holds),
    }


def validate_review_manifest(manifest, legacy, similarity, titles, groups, provenance,
                             *, evidence_root=None):
    """Verify v2 against source-derived inventory and the frozen v1/title snapshots."""
    validate_manifest(legacy, similarity, groups, provenance)
    fields(manifest, {"manifest_version", "review_scope", "provenance", "policies",
                      "title_decisions", "manual_title_reviews", "families", "document_holds",
                      "question_holds", "evidence_documents", "expected_summary"}, "review manifest")
    require(manifest["manifest_version"] == "2.0.0", "Unsupported review manifest version.")
    scope = manifest["review_scope"]
    fields(scope, {"legacy_manifest", "legacy_manifest_canonical_sha256", "title_candidate_report",
                   "title_report_canonical_sha256", "title_screen_version", "broader_family_review",
                   "ready_for_internal_splits"}, "review scope")
    require(scope["legacy_manifest"] == LEGACY_PATH
            and scope["legacy_manifest_canonical_sha256"] == canonical_sha256(legacy),
            "Archived lexical manifest changed.")
    require(scope["title_candidate_report"] == TITLE_PATH
            and scope["title_report_canonical_sha256"] == canonical_sha256(titles),
            "Title candidate report changed.")
    require(scope["title_screen_version"] == titles["title_screen_version"] == "1.0.0",
            "Title screen version changed.")
    require(titles["family_manifest_version"] == legacy["manifest_version"]
            and titles["family_manifest_canonical_sha256"] == canonical_sha256(legacy),
            "Title report does not reference the archived lexical manifest.")
    require(canonical_sha256(manifest["provenance"]) == canonical_sha256(provenance)
            == canonical_sha256(titles["provenance"]), "Review source provenance mismatch.")
    require(scope["broader_family_review"] == "screened_candidates_reviewed_with_holds"
            and scope["ready_for_internal_splits"] is False,
            "Review manifest does not approve internal splits.")
    require(canonical_sha256(manifest["policies"]) == canonical_sha256(REVIEW_POLICIES),
            "Conservative handling policy changed.")
    by_id = {g["group_id"]: g for g in groups}
    legacy_family = {m["group_id"]: f["family_id"]
                     for f in legacy["families"] for m in f["members"]}
    pending, seen, edges_seen, already = {}, set(), set(), 0
    for c in titles["candidates"]:
        rid = c["review_id"]
        require(type(rid) is str and rid not in seen, "Duplicate title candidate ID.")
        seen.add(rid)
        pair = []
        for side in ("left", "right"):
            member = c[side]
            gid = member["group_id"]
            require(gid in by_id and canonical_sha256(member) == canonical_sha256(member_record(by_id[gid])),
                    "Title candidate source identity changed.")
            pair.append(gid)
        edge = tuple(sorted(pair))
        require(edge[0] != edge[1] and edge not in edges_seen, "Duplicate or self title edge.")
        edges_seen.add(edge)
        require(c["crosses_official_split"] is (by_id[edge[0]]["official_split"] != by_id[edge[1]]["official_split"]),
                "Title candidate split flag is wrong.")
        fid = legacy_family.get(edge[0])
        covered = fid is not None and fid == legacy_family.get(edge[1])
        require(c["review_status"] == ("already_in_reviewed_family" if covered else "pending_source_review")
                and c["existing_family_id"] == (fid if covered else None),
                "Title screen's legacy-family status is inconsistent.")
        if covered:
            already += 1
        else:
            pending[rid] = list(edge)

    used_docs = set(REVIEW_DOCS.values()) | {POLICY_DOC}
    confirmed = [d["group_ids"] for f in legacy["families"] for d in f["decisions"]]
    unresolved, nonconfirmed, reviewed = [], [], set()
    require(type(manifest["title_decisions"]) is list, "Title decisions must be a list.")
    for d in manifest["title_decisions"]:
        fields(d, {"review_id", "group_ids", "decision", "evidence_document", "reason"}, "title decision")
        rid = d["review_id"]
        require(type(rid) is str and rid in pending and rid not in reviewed,
                "Unknown or duplicate title decision.")
        require(d["group_ids"] == pending[rid], "Title decision edge does not match candidate.")
        require(type(d["decision"]) is str and d["decision"] in DECISIONS, "Unsupported title decision.")
        nonempty_text(d["reason"], "title decision reason")
        nonempty_text(d["evidence_document"], "title evidence document")
        used_docs.add(d["evidence_document"])
        reviewed.add(rid)
        if d["decision"] == "confirmed":
            confirmed.append(d["group_ids"])
        else:
            nonconfirmed.append(d["group_ids"])
            if d["decision"] == "unresolved":
                unresolved.append(d["group_ids"])
    require(reviewed == set(pending), "Some pending title candidates have no recorded decision.")

    source_titles = {d["title"]: g for g in groups for d in g["source_documents"]}
    issue_titles, seen_titles = {}, set()
    for t in titles["titles"]:
        title = t["source_title"]
        require(title in source_titles and title not in seen_titles, "Unknown or duplicate source title.")
        g = source_titles[title]
        require(t["group_id"] == g["group_id"] and t["official_split"] == g["official_split"],
                "Screened title identity changed.")
        seen_titles.add(title)
        if t["issues"]:
            issue_titles[title] = t["group_id"]
    require(seen_titles == set(source_titles), "Title report omits source titles.")
    require(type(manifest["manual_title_reviews"]) is list, "Manual title reviews must be a list.")
    reviewed_titles = set()
    for d in manifest["manual_title_reviews"]:
        fields(d, {"source_title", "group_id", "decision", "evidence_document", "reason"}, "manual title review")
        title = d["source_title"]
        require(title in issue_titles and title not in reviewed_titles
                and d["group_id"] == issue_titles[title], "Unknown, duplicate or changed manual title review.")
        require(d["decision"] == "reviewed_no_additional_edge", "Unsupported manual title disposition.")
        nonempty_text(d["reason"], "manual title reason")
        nonempty_text(d["evidence_document"], "manual title evidence")
        used_docs.add(d["evidence_document"])
        reviewed_titles.add(title)
    require(reviewed_titles == set(issue_titles), "Missing manual title review.")

    view = preparation_view(groups, confirmed, unresolved)
    require(canonical_sha256(manifest["families"]) == canonical_sha256(view["families"]),
            "Confirmed families differ from connected reviewed edges.")
    component_of = {g: i for i, ids in enumerate(components(by_id, confirmed)) for g in ids}
    require(all(component_of[a] != component_of[b] for a, b in nonconfirmed),
            "A rejected or unresolved pair is already connected; reopen its review.")
    require(manifest["document_holds"] == view["document_holds"],
            "Document holds do not match unresolved training-family closure.")
    holds = question_holds(groups)
    require(canonical_sha256(manifest["question_holds"]) == canonical_sha256(holds),
            "Question holds differ from the source annotation conflicts.")
    used_docs.update(q["evidence_document"] for q in holds)
    evidence = manifest["evidence_documents"]
    require(type(evidence) is dict and set(evidence) == used_docs, "Evidence document inventory differs.")
    for relative, digest in evidence.items():
        require(relative.startswith("docs/ml/") and relative.endswith(".md")
                and ".." not in relative.split("/") and "\\" not in relative,
                "Invalid evidence document path.")
        require(type(digest) is str and len(digest) == 64
                and all(c in "0123456789abcdef" for c in digest), "Invalid evidence digest.")
        if evidence_root is not None:
            path = evidence_root / relative
            require(path.is_file(), f"Missing evidence document: {relative}")
            require(evidence_digest(path) == digest, f"Evidence document changed: {relative}")
    summary = summarize(groups, legacy, manifest["title_decisions"], manifest["manual_title_reviews"],
                        holds, view, already)
    require(canonical_sha256(manifest["expected_summary"]) == canonical_sha256(summary),
            "Expected review counts differ from verified decisions and holds.")
    return summary
