"""Frozen partition membership, exact content and readback integrity tests."""

from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import canonical_sha256
from freeze_cuad_splits import (
    FIXED, FROZEN_DIR, ROLES, build_bundle, load_frozen_partition,
    validate_saved_bundle, verified_inputs, write_bundle,
)
from propose_cuad_splits import SPLITS, assign_families, family_inventory, summarize
from test_cuad_splits import fixture as split_fixture


def fixture():
    pool, rows = split_fixture()
    pool.update({"bindings": {"fixture": True},
                 "span_coordinates": "zero-based paragraph-relative Unicode code points; end exclusive"})
    mapping = {"cuad.common": "cuad.document_name", "cuad.rare": "cuad.parties", "cuad.empty": "cuad.other"}
    pool["groups"][0]["source_titles"].append("doc-000-copy")
    pool["groups"][1]["family_id"] = pool["groups"][0]["family_id"]
    for g in pool["groups"]:
        p = g["paragraphs"][0]
        p["context"] = "😀 x; x\r\n"
        for q in p["questions"]:
            q["category_id"] = mapping[q["category_id"]]
            q["question"] = "Find " + q["category_id"]
            q["answers"] = ([{"start": 2, "end": 3, "text": "x"}, {"start": 5, "end": 6, "text": "x"}]
                            if q["category_id"] != "cuad.other" else [])
            q["is_impossible"] = not q["answers"]
            q["source_questions"] = [{"source_title": t, "source_question_id": t + "__" + q["category_id"]}
                                     for t in g["source_titles"]]
    for r in rows:
        r["category_id"] = mapping.get(r["category_id"], r["category_id"])
    assignments = assign_families(family_inventory(pool))
    summary, support, gaps = summarize(pool, assignments, rows)
    policy = {"fixture_policy": True}
    proposal = {"status": "awaiting_review_and_freeze", "ready_for_training": False,
                "policy_canonical_sha256": canonical_sha256(policy),
                "preparation_pool_canonical_sha256": canonical_sha256(pool),
                "assignment_canonical_sha256": canonical_sha256(assignments), "assignments": assignments}
    report = {"policy": policy, "proposal_canonical_sha256": canonical_sha256(proposal),
              "summary": summary, "category_support": support, "support_gaps": gaps}
    freeze = {**FIXED, "reviewed_proposal_commit": "1" * 40, "partition_roles": deepcopy(ROLES),
              "assignment_canonical_sha256": proposal["assignment_canonical_sha256"],
              "proposal_canonical_sha256": canonical_sha256(proposal),
              "proposal_report_canonical_sha256": canonical_sha256(report),
              "proposal_policy_canonical_sha256": canonical_sha256(policy),
              "preparation_pool_canonical_sha256": canonical_sha256(pool),
              "support_limitations": {
                  "categories_without_no_answer_examples_in_all_partitions": ["cuad.document_name", "cuad.parties"],
                  "per_category_presence_calibration_size_gate_met": False, "model_based_support_assessed": False}}
    return freeze, pool, proposal, report


class CuadFreezeTests(unittest.TestCase):
    def setUp(self):
        self.args = fixture()
        self.freeze, self.pool, self.proposal, self.report = self.args

    def repin(self):
        """Even coordinated edits must pass independent membership checks."""
        self.proposal["preparation_pool_canonical_sha256"] = canonical_sha256(self.pool)
        self.proposal["assignment_canonical_sha256"] = canonical_sha256(self.proposal["assignments"])
        self.freeze["preparation_pool_canonical_sha256"] = canonical_sha256(self.pool)
        self.freeze["assignment_canonical_sha256"] = self.proposal["assignment_canonical_sha256"]
        self.freeze["proposal_canonical_sha256"] = canonical_sha256(self.proposal)
        self.report["proposal_canonical_sha256"] = canonical_sha256(self.proposal)
        self.freeze["proposal_report_canonical_sha256"] = canonical_sha256(self.report)

    def test_complete_disjoint_partitioning_preserves_every_group_exactly(self):
        before = deepcopy(self.args)
        bundle = build_bundle(*self.args)
        self.assertEqual(self.args, before)
        self.assertEqual(set(bundle), {"manifest.json", *(s + ".json" for s in SPLITS)})
        actual = [g for s in SPLITS for g in bundle[s + ".json"]["groups"]]
        self.assertEqual(sorted(actual, key=lambda g: g["group_id"]), self.pool["groups"])
        self.assertEqual(len({g["group_id"] for g in actual}), 40)
        self.assertEqual(sum(len(g["source_titles"]) for g in actual), 41)
        for s in SPLITS:
            part = bundle[s + ".json"]
            self.assertEqual(part["intended_role"], ROLES[s])
            self.assertFalse(part["tokenized"])
            for g in part["groups"]:
                for q in g["paragraphs"][0]["questions"]:
                    for answer in q["answers"]:
                        self.assertEqual(g["paragraphs"][0]["context"][answer["start"]:answer["end"]], answer["text"])
        bundle["fit.json"]["groups"][0]["paragraphs"][0]["context"] = "changed output"
        self.assertEqual(self.args, before)

    def test_stale_pool_cannot_use_old_freeze(self):
        self.pool["groups"][0]["paragraphs"][0]["context"] += "changed"
        with self.assertRaisesRegex(ValueError, "Frozen preparation pool"):
            build_bundle(*self.args)

    def test_changed_assignment_cannot_use_old_freeze(self):
        self.proposal["assignments"][0]["proposed_split"] = "dev_cal"
        # Ensure an actual change regardless of the fixture allocator's ordering.
        self.proposal["assignments"][0]["source_titles"].append("foreign")
        with self.assertRaisesRegex(ValueError, "Frozen proposal digest"):
            build_bundle(*self.args)

    def test_partial_family_is_rejected_even_after_repinning(self):
        joined = next(a for a in self.proposal["assignments"] if len(a["group_ids"]) > 1)
        joined["group_ids"].pop()
        self.repin()
        with self.assertRaisesRegex(ValueError, "complete family"):
            build_bundle(*self.args)

    def test_omitted_family_is_rejected_even_after_repinning(self):
        self.proposal["assignments"].pop()
        self.repin()
        with self.assertRaisesRegex(ValueError, "omit eligible"):
            build_bundle(*self.args)

    def test_official_test_is_rejected_even_after_repinning(self):
        self.pool["groups"][0]["official_split"] = "test"
        self.repin()
        with self.assertRaisesRegex(ValueError, "Official test"):
            build_bundle(*self.args)

    def test_development_role_cannot_be_changed_to_weight_training(self):
        self.freeze["partition_roles"]["dev_cal"] = "weight_training"
        with self.assertRaisesRegex(ValueError, "Partition roles"):
            build_bundle(*self.args)

    def test_missing_question_cannot_pass_reviewed_counts_after_repinning(self):
        self.pool["groups"][0]["paragraphs"][0]["questions"].pop()
        self.repin()
        with self.assertRaisesRegex(ValueError, "partition counts differ"):
            build_bundle(*self.args)

    def test_unmeasured_model_support_cannot_be_marked_assessed(self):
        self.freeze["support_limitations"]["model_based_support_assessed"] = True
        with self.assertRaisesRegex(ValueError, "support limitations differ"):
            build_bundle(*self.args)

    def test_repeat_write_and_verified_partition_loading(self):
        bundle = build_bundle(*self.args)
        with TemporaryDirectory() as folder:
            repo = Path(folder)
            directory = repo / FROZEN_DIR
            self.assertEqual(write_bundle(directory, bundle), 5)
            self.assertEqual(write_bundle(directory, bundle), 0)
            with patch("freeze_cuad_splits.verified_inputs", return_value=self.args):
                self.assertEqual(load_frozen_partition(repo, "dev_cal"), bundle["dev_cal.json"])
                with self.assertRaisesRegex(ValueError, "Unknown internal partition"):
                    load_frozen_partition(repo, "test")

    def test_saved_partition_or_manifest_tampering_is_rejected(self):
        bundle = build_bundle(*self.args)
        for name in ("fit.json", "manifest.json"):
            with self.subTest(name=name), TemporaryDirectory() as folder:
                directory = Path(folder)
                write_bundle(directory, bundle)
                changed = deepcopy(bundle[name])
                if name == "fit.json":
                    changed["groups"][0]["paragraphs"][0]["questions"][0]["answers"] = []
                else:
                    changed["partitions"]["fit"]["canonical_sha256"] = "0" * 64
                (directory / name).write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Frozen file differs"):
                    validate_saved_bundle(directory, bundle)

    def test_conflicting_existing_partition_prevents_all_writes(self):
        bundle = build_bundle(*self.args)
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "dev_cal.json").write_bytes(b"keep this file")
            with self.assertRaisesRegex(ValueError, "not replaced"):
                write_bundle(directory, bundle)
            self.assertFalse((directory / "fit.json").exists())
            self.assertFalse((directory / "manifest.json").exists())
            self.assertEqual((directory / "dev_cal.json").read_bytes(), b"keep this file")

    def test_missing_partition_is_rejected(self):
        bundle = build_bundle(*self.args)
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            write_bundle(directory, bundle)
            (directory / "dev_policy.json").unlink()
            with self.assertRaisesRegex(ValueError, "Missing frozen file"):
                validate_saved_bundle(directory, bundle)

    def test_saved_proposal_must_match_source_reconstruction(self):
        with TemporaryDirectory() as folder:
            repo = Path(folder)
            directory = repo / "data/processed/cuad"
            directory.mkdir(parents=True)
            changed = deepcopy(self.proposal)
            changed["assignments"].pop()
            (directory / "split_proposal.json").write_text(json.dumps(changed), encoding="utf-8")
            (directory / "split_report.json").write_text(json.dumps(self.report), encoding="utf-8")
            with patch("freeze_cuad_splits.propose", return_value=(self.proposal, self.report)):
                with self.assertRaisesRegex(ValueError, "verified reconstruction"):
                    verified_inputs(repo)


if __name__ == "__main__":
    unittest.main()
