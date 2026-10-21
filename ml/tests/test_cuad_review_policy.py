"""Hold propagation and fail-closed review validation; no downloads required."""

from copy import deepcopy
import hashlib
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import canonical_sha256, member_record, read_json
from cuad_review_policy import (
    LEGACY_PATH, TITLE_PATH, POLICY_DOC, REVIEW_POLICIES, REVIEW_DOCS,
    evidence_digest, preparation_view, question_holds, validate_review_manifest,
)
from test_cuad_families import synthetic_fixture


def review_fixture():
    legacy, similarity, groups, provenance = synthetic_fixture()
    for name in "FGHIJK":
        groups.append({
            "group_id": "cuad-exact-v1:" + canonical_sha256([name]),
            "official_split": "test" if name == "G" else "train",
            "paragraphs": [{"index": 0, "code_points": 1,
                            "text_sha256": hashlib.sha256(name.encode()).hexdigest()}],
            "source_documents": [{"title": name}] + ([{"title": "K-copy"}] if name == "K" else []),
        })
    groups[-1]["annotation_conflicts"] = [{
        "paragraph_index": 0, "source_label": "Anti-Assignment", "review_status": "pending_adjudication",
        "source_annotations": [{"source_question_id": title + "__Anti-Assignment"}
                               for title in ("K", "K-copy")],
    }]
    legacy["expected_summary"].update({
        "source_documents": 13, "exact_text_groups": 11,
        "official_train_documents": 11, "official_test_documents": 2,
        "prospective_eligible_training_documents": 10,
        "prospective_eligible_exact_groups": 8,
        "prospective_internal_family_units": 6,
        "prospective_sensitivity_test_documents": 1,
    })
    candidates, decisions = [], []
    for n, (a, b, status) in enumerate([(0,5,"unresolved"), (7,8,"confirmed"),
                                       (8,9,"rejected"), (9,6,"unresolved"),
                                       (3,4,"already")], start=1):
        covered = status == "already"
        rid = f"title-{n:03}"
        candidates.append({
            "review_id": rid, "left": member_record(groups[a]), "right": member_record(groups[b]),
            "crosses_official_split": groups[a]["official_split"] != groups[b]["official_split"],
            "review_status": "already_in_reviewed_family" if covered else "pending_source_review",
            "existing_family_id": legacy["families"][1]["family_id"] if covered else None,
        })
        if not covered:
            decisions.append({"review_id": rid, "group_ids": sorted([groups[a]["group_id"],groups[b]["group_id"]]),
                              "decision": status, "evidence_document": "docs/ml/SyntheticReview.md",
                              "reason": "Synthetic reviewed decision."})
    title_records = [{"source_title": d["title"], "group_id": g["group_id"],
                      "official_split": g["official_split"],
                      "issues": ["unparsed_issuer"] if d["title"] == "K" else []}
                     for g in groups for d in g["source_documents"]]
    titles = {"title_screen_version": "1.0.0", "provenance": provenance,
              "family_manifest_version": "1.0.0", "family_manifest_canonical_sha256": canonical_sha256(legacy),
              "candidates": candidates, "titles": title_records}
    manual = [{"source_title": "K", "group_id": groups[-1]["group_id"],
               "decision": "reviewed_no_additional_edge", "evidence_document": "docs/ml/SyntheticReview.md",
               "reason": "No additional edge supported by the fixture."}]
    edges = [d["group_ids"] for f in legacy["families"] for d in f["decisions"]]
    edges += [d["group_ids"] for d in decisions if d["decision"] == "confirmed"]
    view = preparation_view(groups, edges, [d["group_ids"] for d in decisions if d["decision"] == "unresolved"])
    docs = set(REVIEW_DOCS.values()) | {POLICY_DOC, "docs/ml/SyntheticReview.md", "docs/ml/CUAD_DataReview.md"}
    expected = {
        "source_documents": 13, "exact_text_groups": 11,
        "official_train_documents": 11, "official_test_documents": 2,
        "lexical_reviewed_pairs": 3, "title_reviewed_pairs": 4, "title_already_reviewed_pairs": 1,
        "title_confirmed_pairs": 1, "title_rejected_pairs": 1, "title_unresolved_pairs": 2,
        "manual_title_reviews": 1, "reviewed_families": 3,
        "training_only_families": 2, "cross_split_families": 1, "test_only_families": 0,
        "confirmed_cross_split_training_exclusions": 1, "unresolved_training_hold_documents": 6,
        "prospective_training_exclusions": 7, "prospective_eligible_training_documents": 4,
        "prospective_eligible_exact_groups": 3, "prospective_internal_family_units": 2,
        "prospective_sensitivity_test_documents": 1,
        "held_group_category_questions": 1, "held_original_question_records": 2,
    }
    m = {"manifest_version": "2.0.0", "review_scope": {
        "legacy_manifest": LEGACY_PATH, "legacy_manifest_canonical_sha256": canonical_sha256(legacy),
        "title_candidate_report": TITLE_PATH, "title_report_canonical_sha256": canonical_sha256(titles),
        "title_screen_version": "1.0.0", "broader_family_review": "screened_candidates_reviewed_with_holds",
        "ready_for_internal_splits": False},
        "provenance": provenance, "policies": deepcopy(REVIEW_POLICIES),
        "title_decisions": decisions, "manual_title_reviews": manual,
        "families": view["families"], "document_holds": view["document_holds"],
        "question_holds": question_holds(groups),
        "evidence_documents": {p: hashlib.sha256(b"approved review\n").hexdigest() for p in docs},
        "expected_summary": expected}
    return tuple(deepcopy(v) for v in (m, legacy, similarity, titles, groups, provenance))


class ReviewPolicyTests(unittest.TestCase):
    def setUp(self):
        self.m, self.legacy, self.sim, self.titles, self.groups, self.provenance = review_fixture()

    def validate(self, root=None):
        return validate_review_manifest(self.m, self.legacy, self.sim, self.titles,
                                        self.groups, self.provenance, evidence_root=root)

    def repin_titles(self):
        self.m["review_scope"]["title_report_canonical_sha256"] = canonical_sha256(self.titles)

    def test_policy_counts_and_nonmutation(self):
        before = deepcopy((self.m,self.legacy,self.sim,self.titles,self.groups,self.provenance))
        result = self.validate()
        self.assertEqual(result["prospective_eligible_training_documents"], 4)
        self.assertEqual(result["prospective_internal_family_units"], 2)
        self.assertEqual(result["held_original_question_records"], 2)
        self.assertEqual(before,(self.m,self.legacy,self.sim,self.titles,self.groups,self.provenance))

    def test_hold_reaches_transitive_family_and_all_duplicate_identities(self):
        held = self.m["document_holds"]
        self.assertEqual(set(held), {self.groups[i]["group_id"] for i in [0,1,2,5,9]})
        self.assertEqual(self.validate()["unresolved_training_hold_documents"], 6)

    def test_unresolved_test_member_stays_in_sensitivity(self):
        edges = [d["group_ids"] for f in self.legacy["families"] for d in f["decisions"]]
        edges += [d["group_ids"] for d in self.m["title_decisions"] if d["decision"]=="confirmed"]
        v = preparation_view(self.groups,edges,[d["group_ids"] for d in self.m["title_decisions"] if d["decision"]=="unresolved"])
        self.assertEqual(v["sensitivity_test_groups"], [self.groups[6]["group_id"]])
        self.assertEqual({g for ids in v["eligible_components"] for g in ids},
                         {self.groups[i]["group_id"] for i in [7,8,10]})

    def test_missing_hold_is_rejected_even_with_changed_expected_counts(self):
        self.m["document_holds"].remove(self.groups[1]["group_id"])
        self.m["expected_summary"]["prospective_eligible_training_documents"] += 1
        with self.assertRaisesRegex(ValueError,"Document holds"):
            self.validate()

    def test_extra_hold_or_test_hold_is_rejected(self):
        for index in [6,7]:
            with self.subTest(index=index):
                saved = self.m["document_holds"][:]
                self.m["document_holds"] = sorted(saved + [self.groups[index]["group_id"]])
                with self.assertRaisesRegex(ValueError,"Document holds"):
                    self.validate()
                self.m["document_holds"] = saved

    def test_unresolved_edges_cannot_be_used_as_confirmed_families(self):
        self.m["families"][0]["group_ids"].append(self.groups[5]["group_id"])
        with self.assertRaisesRegex(ValueError,"Confirmed families"):
            self.validate()

    def test_pending_candidate_cannot_disappear(self):
        self.m["title_decisions"].pop()
        with self.assertRaisesRegex(ValueError,"no recorded decision"):
            self.validate()

    def test_duplicate_decision_is_rejected(self):
        self.m["title_decisions"].append(deepcopy(self.m["title_decisions"][0]))
        with self.assertRaisesRegex(ValueError,"duplicate title decision"):
            self.validate()

    def test_wrong_decision_edge_is_rejected(self):
        self.m["title_decisions"][0]["group_ids"] = self.m["title_decisions"][1]["group_ids"]
        with self.assertRaisesRegex(ValueError,"does not match candidate"):
            self.validate()

    def test_unsupported_decision_is_rejected(self):
        self.m["title_decisions"][0]["decision"] = "assume_unrelated"
        with self.assertRaisesRegex(ValueError,"Unsupported title decision"):
            self.validate()

    def test_changed_screen_requires_review(self):
        self.titles["candidates"].pop()
        with self.assertRaisesRegex(ValueError,"Title candidate report changed"):
            self.validate()

    def test_wrong_split_flag_is_rejected_after_digest_update(self):
        self.titles["candidates"][0]["crosses_official_split"] = True
        self.repin_titles()
        with self.assertRaisesRegex(ValueError,"split flag"):
            self.validate()

    def test_wrong_source_identity_is_rejected_after_digest_update(self):
        self.titles["candidates"][0]["right"]["source_titles"] = ["wrong"]
        self.repin_titles()
        with self.assertRaisesRegex(ValueError,"source identity"):
            self.validate()

    def test_legacy_coverage_flag_cannot_hide_pending_review(self):
        self.titles["candidates"][0]["review_status"] = "already_in_reviewed_family"
        self.repin_titles()
        with self.assertRaisesRegex(ValueError,"legacy-family status"):
            self.validate()

    def test_archive_binding_is_required(self):
        self.m["review_scope"]["legacy_manifest_canonical_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError,"Archived lexical manifest"):
            self.validate()

    def test_report_must_bind_to_same_archive(self):
        self.titles["family_manifest_canonical_sha256"] = "0"*64
        self.repin_titles()
        with self.assertRaisesRegex(ValueError,"does not reference"):
            self.validate()

    def test_missing_manual_title_review_is_rejected(self):
        self.m["manual_title_reviews"] = []
        with self.assertRaisesRegex(ValueError,"Missing manual title review"):
            self.validate()

    def test_incomplete_question_hold_cannot_select_a_preferred_copy(self):
        self.m["question_holds"][0]["source_question_ids"].pop()
        with self.assertRaisesRegex(ValueError,"Question holds"):
            self.validate()

    def test_removing_question_hold_or_changing_category_is_rejected(self):
        for change in [[], [{**self.m["question_holds"][0],"category_id":"cuad.exclusivity"}]]:
            with self.subTest(change=change):
                self.m["question_holds"] = change
                with self.assertRaisesRegex(ValueError,"Question holds"):
                    self.validate()

    def test_unreviewed_conflict_category_fails_closed(self):
        self.groups[-1]["annotation_conflicts"][0]["source_label"] = "New Category"
        with self.assertRaisesRegex(ValueError,"New conflicting category"):
            self.validate()

    def test_premature_split_approval_is_rejected(self):
        self.m["review_scope"]["ready_for_internal_splits"] = True
        with self.assertRaisesRegex(ValueError,"does not approve internal splits"):
            self.validate()

    def test_boolean_count_is_not_an_integer_count(self):
        self.m["expected_summary"]["prospective_sensitivity_test_documents"] = True
        with self.assertRaisesRegex(ValueError,"Expected review counts"):
            self.validate()

    def test_changed_hold_policy_is_rejected(self):
        self.m["policies"]["unresolved_relationships"] = "allow_training"
        with self.assertRaisesRegex(ValueError,"handling policy changed"):
            self.validate()

    def test_evidence_requires_exact_content_but_accepts_windows_line_endings(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            for rel in self.m["evidence_documents"]:
                p=root/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b"approved review\r\n")
            self.validate(root)
            p=root/POLICY_DOC; p.write_text("changed policy\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"Evidence document changed"):
                self.validate(root)
            p.unlink()
            with self.assertRaisesRegex(ValueError,"Missing evidence document"):
                self.validate(root)

    def test_release_archive_keeps_the_reviewed_screen_identity(self):
        repo = Path(__file__).resolve().parents[2]
        legacy = read_json(repo/LEGACY_PATH)
        self.assertEqual(canonical_sha256(legacy),"7576938a012b45b30121887b6db7d9d9dd77e0886256a554c70085f3a8fc8dea")
        active = read_json(repo/"ml/configs/cuad_family_manifest.json")
        self.assertEqual(active["review_scope"]["legacy_manifest_canonical_sha256"],canonical_sha256(legacy))


if __name__ == "__main__":
    unittest.main()
