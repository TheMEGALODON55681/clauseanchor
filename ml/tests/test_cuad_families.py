"""Family-boundary regression checks using synthetic data; no CUAD download needed."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import (
    POLICIES, REPORT_PATH, REVIEW_DOCS, canonical_sha256, family_id,
    member_record, read_json, validate_manifest,
)


def synthetic_fixture():
    # A has two source documents with identical text. A-B-C is one training
    # family. D-E crosses official train/test, so only D is a training exclusion.
    groups = []
    for name in "ABCDE":
        groups.append({
            "group_id": "cuad-exact-v1:" + canonical_sha256([name]),
            "official_split": "test" if name == "E" else "train",
            "paragraphs": [{"index": 0, "code_points": 1,
                            "text_sha256": hashlib.sha256(name.encode()).hexdigest()}],
            "source_documents": [{"title": name}]
                                + ([{"title": "A-copy"}] if name == "A" else []),
        })
    provenance = {"fixture": "synthetic_source_snapshot"}
    candidates = []
    for i, (a, b) in enumerate(((0, 1), (1, 2), (3, 4)), start=1):
        candidates.append({
            "review_id": f"similarity-{i:03d}",
            "left": member_record(groups[a]), "right": member_record(groups[b]),
            "crosses_official_split": b == 4,
        })
    report = {"screen_version": "1.0.0", "provenance": provenance,
              "candidates": candidates}
    families = []
    for indices, pair_indices in (((0, 1, 2), (0, 1)), ((3, 4), (2,))):
        members = [member_record(groups[i]) for i in indices]
        decisions = []
        for i in pair_indices:
            c = candidates[i]
            decisions.append({
                "review_id": c["review_id"],
                "group_ids": sorted([c["left"]["group_id"], c["right"]["group_id"]]),
                "decision": "confirmed_related_for_split_grouping",
                "relationship": "agreement_variants",
                "evidence_document": REVIEW_DOCS[c["crosses_official_split"]],
                "reason": "Synthetic reviewed relationship for the boundary test.",
            })
        families.append({"family_id": family_id([m["group_id"] for m in members]),
                         "members": members, "decisions": decisions})
    expected = {
        "source_documents": 6, "exact_text_groups": 5,
        "official_train_documents": 5, "official_test_documents": 1,
        "reviewed_candidate_pairs": 3, "reviewed_families": 2,
        "reviewed_member_groups": 5, "training_only_families": 1,
        "cross_split_families": 1, "prospective_training_exclusions": 1,
        "prospective_eligible_training_documents": 4,
        "prospective_eligible_exact_groups": 3,
        "prospective_internal_family_units": 1,
        "prospective_sensitivity_test_documents": 0,
    }
    manifest = {
        "manifest_version": "1.0.0",
        "review_scope": {"screen_version": "1.0.0", "candidate_report": REPORT_PATH,
                         "candidate_report_canonical_sha256": canonical_sha256(report),
                         "screen_candidates_reviewed": True, "broader_family_review": "pending",
                         "ready_for_internal_splits": False},
        "provenance": deepcopy(provenance), "policies": deepcopy(POLICIES),
        "families": families, "expected_summary": expected,
    }
    # These represent separately loaded files, so they must not share mutable
    # paragraph dictionaries when a test corrupts just one input.
    return tuple(deepcopy(value) for value in (manifest, report, groups, provenance))


class CuadFamilyTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.report, self.groups, self.provenance = synthetic_fixture()

    def validate(self):
        return validate_manifest(self.manifest, self.report, self.groups, self.provenance)

    def test_connected_family_preserves_records_and_reserves_test_boundary(self):
        before = deepcopy((self.manifest, self.report, self.groups, self.provenance))
        result = self.validate()
        self.assertEqual(result["prospective_eligible_training_documents"], 4)
        self.assertEqual(result["prospective_internal_family_units"], 1)
        self.assertEqual(result["official_test_documents"], 1)
        self.assertEqual(before, (self.manifest, self.report, self.groups, self.provenance))

    def test_changed_screen_is_not_silently_accepted(self):
        self.report["candidates"].pop()
        with self.assertRaisesRegex(ValueError, "Candidate report changed"):
            self.validate()

    def test_changed_source_hash_is_rejected(self):
        self.groups[0]["paragraphs"][0]["text_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Candidate source identity"):
            self.validate()

    def test_changed_manifest_member_title_is_rejected(self):
        self.manifest["families"][0]["members"][0]["source_titles"] = ["wrong-title"]
        with self.assertRaisesRegex(ValueError, "Family member identity"):
            self.validate()

    def test_missing_bridge_cannot_leave_disconnected_family(self):
        self.manifest["families"][0]["decisions"].pop()
        with self.assertRaisesRegex(ValueError, "Disconnected family"):
            self.validate()

    def test_unrelated_components_cannot_be_merged(self):
        a, b = self.manifest["families"]
        a["members"].extend(b["members"])
        a["decisions"].extend(b["decisions"])
        a["family_id"] = family_id([m["group_id"] for m in a["members"]])
        self.manifest["families"] = [a]
        with self.assertRaisesRegex(ValueError, "Disconnected family"):
            self.validate()

    def test_group_cannot_belong_to_two_families(self):
        a, b = self.manifest["families"]
        b["members"].append(deepcopy(a["members"][0]))
        b["family_id"] = family_id([m["group_id"] for m in b["members"]])
        with self.assertRaisesRegex(ValueError, "repeated family member"):
            self.validate()

    def test_omitting_whole_family_leaves_unreviewed_candidates(self):
        self.manifest["families"].pop()
        with self.assertRaisesRegex(ValueError, "no recorded decision"):
            self.validate()

    def test_wrong_cross_split_flag_fails_even_with_updated_report_digest(self):
        self.report["candidates"][-1]["crosses_official_split"] = False
        self.manifest["review_scope"]["candidate_report_canonical_sha256"] = canonical_sha256(self.report)
        with self.assertRaisesRegex(ValueError, "split flag is wrong"):
            self.validate()

    def test_candidate_review_does_not_approve_splits(self):
        self.manifest["review_scope"]["ready_for_internal_splits"] = True
        with self.assertRaisesRegex(ValueError, "does not approve internal splits"):
            self.validate()

    def test_changed_boundary_policy_is_rejected(self):
        self.manifest["policies"]["cross_split_training_members"] = "allow_training"
        with self.assertRaisesRegex(ValueError, "Preparation policy changed"):
            self.validate()

    def test_boolean_cannot_substitute_for_integer_expected_count(self):
        self.manifest["expected_summary"]["prospective_internal_family_units"] = True
        with self.assertRaisesRegex(ValueError, "Expected family counts"):
            self.validate()

    def test_duplicate_keys_and_nonfinite_values_are_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            for payload in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
                with self.subTest(payload=payload):
                    path.write_text(payload, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        read_json(path)

    def test_report_digest_ignores_json_spacing_and_key_order(self):
        reserialized = json.loads(json.dumps(self.report, sort_keys=True, indent=4))
        self.assertEqual(canonical_sha256(self.report), canonical_sha256(reserialized))


if __name__ == "__main__":
    unittest.main()
