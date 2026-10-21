"""Deterministic grouping and support accounting; synthetic data, no downloads."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import canonical_sha256
from propose_cuad_splits import (
    FIXED_POLICY, SPLITS, assign_families, family_inventory, integer_targets,
    summarize, validate_assignments, validate_policy,
)


def fixture(n=40):
    groups = []
    for i in range(n):
        questions = [{"category_id": cid, "answers": [{"start": 0, "end": 1, "text": "x"}] if positive else []}
                     for cid, positive in (("cuad.common", True), ("cuad.rare", i < 10), ("cuad.empty", False))]
        groups.append({"group_id": f"g{i:03}", "family_id": f"f{i:03}", "source_titles": [f"doc-{i:03}"],
                       "official_split": "train", "paragraphs": [{"questions": questions}]})
    rows = [{"category_id": cid, "annotation_status": "cuad_annotated"}
            for cid in ("cuad.common", "cuad.rare", "cuad.empty")]
    rows.append({"category_id": "in.arbitration", "annotation_status": "unannotated_in_cuad"})
    return {"groups": groups}, rows


class CuadSplitTests(unittest.TestCase):
    def test_largest_remainder_document_targets(self):
        self.assertEqual(integer_targets(385), dict(zip(SPLITS, (270, 39, 38, 38))))
        self.assertEqual(sum(integer_targets(7).values()), 7)
        with self.assertRaises(ValueError):
            integer_targets(True)

    def test_reproducible_under_input_order_changes_without_mutation(self):
        pool, _ = fixture()
        before = deepcopy(pool)
        families = family_inventory(pool)
        expected = assign_families(families)
        self.assertEqual(pool, before)
        pool["groups"].reverse()
        for g in pool["groups"]:
            g["paragraphs"][0]["questions"].reverse()
        self.assertEqual(expected, assign_families(list(reversed(family_inventory(pool)))))
        self.assertEqual(families, family_inventory(before))

    def test_seed_controls_ties_and_default_is_42(self):
        families = family_inventory(fixture()[0])
        self.assertEqual(assign_families(families), assign_families(families, 42))
        self.assertNotEqual(assign_families(families, 42), assign_families(families, 43))

    def test_rare_label_distributed_when_exact_quotas_are_feasible(self):
        pool, rows = fixture()
        assignments = assign_families(family_inventory(pool))
        summary, support, _ = summarize(pool, assignments, rows)
        self.assertEqual([summary[s]["source_documents"] for s in SPLITS], [28, 4, 4, 4])
        rare = next(r for r in support if r["category_id"] == "cuad.rare")
        self.assertEqual([rare["splits"][s]["positive_family_units"] for s in SPLITS], [7, 1, 1, 1])

    def test_families_and_duplicate_identities_are_indivisible(self):
        pool, rows = fixture()
        pool["groups"][1]["family_id"] = pool["groups"][0]["family_id"]
        pool["groups"][2]["source_titles"].append("duplicate-copy")
        families = family_inventory(pool)
        assignments = assign_families(families)
        validate_assignments(assignments, families)
        joined = next(a for a in assignments if a["family_id"] == "f000")
        self.assertEqual(joined["group_ids"], ["g000", "g001"])
        duplicate = next(a for a in assignments if a["family_id"] == "f002")
        self.assertEqual(duplicate["source_titles"], ["doc-002", "duplicate-copy"])
        summary, _, _ = summarize(pool, assignments, rows)
        self.assertEqual({s: summary[s]["source_documents"] for s in SPLITS}, integer_targets(41))
        self.assertEqual(sum(r["family_units"] for r in summary.values()), 39)
        self.assertEqual(sum(r["exact_text_groups"] for r in summary.values()), 40)

    def test_pool_test_record_cannot_be_assigned(self):
        pool, _ = fixture()
        pool["groups"][0]["official_split"] = "test"
        with self.assertRaisesRegex(ValueError, "Official test"):
            family_inventory(pool)

    def test_multi_document_cohort_is_not_concentrated_in_fit(self):
        pool, rows = fixture()
        for i in range(20):
            pool["groups"][i]["family_id"] = f"pair-{i // 2}"
        assignments = assign_families(family_inventory(pool))
        summary, _, _ = summarize(pool, assignments, rows)
        self.assertEqual([summary[s]["multi_source_document_families"] for s in SPLITS], [7, 1, 1, 1])
        self.assertEqual([summary[s]["source_documents"] for s in SPLITS], [28, 4, 4, 4])

    def test_repeated_group_or_source_identity_is_rejected(self):
        for field in ("group_id", "source_titles"):
            with self.subTest(field=field):
                pool, _ = fixture()
                pool["groups"][1][field] = deepcopy(pool["groups"][0][field])
                with self.assertRaisesRegex(ValueError, "Repeated exact group|Source title"):
                    family_inventory(pool)

    def test_unannotated_question_cannot_be_used_for_stratification(self):
        pool, _ = fixture()
        pool["groups"][0]["paragraphs"][0]["questions"][0]["category_id"] = "in.arbitration"
        with self.assertRaisesRegex(ValueError, "Unannotated extension"):
            family_inventory(pool)

    def test_families_with_no_positive_labels_are_still_assigned(self):
        pool, _ = fixture()
        for g in pool["groups"]:
            for q in g["paragraphs"][0]["questions"]:
                q["answers"] = []
        assignments = assign_families(family_inventory(pool))
        self.assertEqual(len(assignments), 40)
        self.assertEqual({s: sum(a["proposed_split"] == s for a in assignments) for s in SPLITS}, integer_targets(40))

    def test_infeasible_targets_do_not_split_or_drop_families(self):
        pool, _ = fixture(4)
        for i, g in enumerate(pool["groups"]):
            g["family_id"] = f"family-{i // 2}"
        with self.assertRaisesRegex(ValueError, "cannot fit.*whole family"):
            assign_families(family_inventory(pool))

    def test_missing_duplicated_or_changed_assignments_are_rejected(self):
        families = family_inventory(fixture()[0])
        valid = assign_families(families)
        variants = [valid[:-1], valid + [valid[0]], deepcopy(valid), deepcopy(valid)]
        variants[2][0]["group_ids"].append("foreign-group")
        variants[3][0]["proposed_split"] = "official_test"
        for variant in variants:
            with self.subTest(variant=variant[0]):
                with self.assertRaisesRegex(ValueError, "Assignments differ"):
                    validate_assignments(variant, families)

    def test_support_counts_keep_missing_annotations_distinct(self):
        pool, rows = fixture()
        summary, support, gaps = summarize(pool, assign_families(family_inventory(pool)), rows)
        self.assertEqual(sum(s["questions"] for s in summary.values()), 120)
        self.assertEqual(sum(s["positive_questions"] for s in summary.values()), 50)
        self.assertEqual(sum(s["no_answer_questions"] for s in summary.values()), 70)
        self.assertEqual(sum(s["answer_spans"] for s in summary.values()), 50)
        self.assertEqual(len(gaps), 8)  # common: no negatives; empty: no positives, in all four parts.
        india = next(r for r in support if r["category_id"] == "in.arbitration")
        self.assertEqual(india["annotation_status"], "unannotated_in_cuad")
        self.assertTrue(all(r["questions"] == 0 for r in india["splits"].values()))
        self.assertFalse(any(g["category_id"] == "in.arbitration" for g in gaps))

    def test_policy_scope_ratios_and_seed_cannot_change_silently(self):
        pool = {"bindings": {"family_manifest_canonical_sha256": "a" * 64,
                              "question_set_canonical_sha256": "b" * 64}}
        report = {"pool_canonical_sha256": canonical_sha256(pool), "bindings": deepcopy(pool["bindings"])}
        policy = {**deepcopy(FIXED_POLICY), "preparation_pool_canonical_sha256": canonical_sha256(pool),
                  **pool["bindings"]}
        validate_policy(policy, pool, report)
        for key, value in (("scope", "approved_for_training"), ("seed", 43),
                           ("split_percentages", dict(zip(SPLITS, (80, 10, 5, 5))))):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "Split policy differs"):
                    validate_policy({**policy, key: value}, pool, report)

    def test_preparation_digest_mismatch_is_rejected(self):
        pool = {"bindings": {"family_manifest_canonical_sha256": "a" * 64,
                              "question_set_canonical_sha256": "b" * 64}}
        report = {"pool_canonical_sha256": canonical_sha256(pool), "bindings": deepcopy(pool["bindings"])}
        policy = {**deepcopy(FIXED_POLICY), "preparation_pool_canonical_sha256": "0" * 64, **pool["bindings"]}
        with self.assertRaisesRegex(ValueError, "Prepared pool differs"):
            validate_policy(policy, pool, report)


if __name__ == "__main__":
    unittest.main()
