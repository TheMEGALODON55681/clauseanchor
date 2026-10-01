"""Contract and regression checks for the scope handoff, not browser tests."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_scope_fixtures.py"
SPEC = importlib.util.spec_from_file_location("scope_fixture_check", MODULE_PATH)
scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scope)


class ScopeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.families = scope.load_families()
        cls.cases = {case["id"]: case for family in cls.families for case in family["cases"]}

    def case(self, suffix="01-supported-and-outside"):
        return deepcopy(self.cases["scope-" + suffix])

    def test_all_sixteen_frozen_expectations(self):
        self.assertEqual(len(self.families), 8)
        self.assertEqual(len(self.cases), 16)
        for case in self.cases.values():
            with self.subTest(case=case["id"]):
                scope.verify_case(case)

    def test_every_substantive_character_belongs_to_exactly_one_unit(self):
        for case in self.cases.values():
            with self.subTest(case=case["id"]):
                observed = scope.observe(case)
                text = case["document"]["text"]
                counts = [0] * len(text)
                for unit in observed["navigation"]["display_units"]:
                    self.assertEqual(text[unit["start"]:unit["end"]], unit["text"])
                    for i in range(unit["start"], unit["end"]):
                        counts[i] += 1
                self.assertTrue(all(count <= 1 for count in counts))
                self.assertTrue(all(counts[i] == 1 for i, c in enumerate(text) if not c.isspace()))

    def test_emoji_offsets_and_second_occurrence_are_distinct(self):
        case = self.case("07-unicode-repeat-overlap-nesting")
        text = case["document"]["text"]
        selected = case["core_result"]["categories"][0]["clauses"][0]["span"]
        self.assertGreater(selected["start"], text.find(selected["text"]))
        utf16 = len(text[:selected["start"]].encode("utf-16-le")) // 2
        self.assertEqual(utf16, selected["start"] + 1)
        selected["start"] = utf16
        with self.assertRaises(ValueError):
            scope.observe(case)

    def test_review_candidates_cannot_complete_accepted_coverage(self):
        case = self.case("03-mixed-paragraph")
        category = case["core_result"]["categories"][0]
        for finding in category["clauses"]:
            finding["status"] = "review_candidate"
        category.update(status="abstained", reason_code="fixture_uncertainty", unresolved_count=2)
        nav = scope.observe(case)["navigation"]
        self.assertEqual(nav["accepted_finding_ids"], [])
        self.assertEqual(len(nav["review_candidate_ids"]), 2)
        self.assertEqual(nav["display_units"][0]["coverage"], "none")
        self.assertEqual(nav["manual_review_count"], 1)

    def test_unrequested_categories_do_not_contribute_coverage(self):
        case = self.case("07-cross-category-union")
        case["requested_category_ids"] = case["requested_category_ids"][:1]
        case["core_result"]["categories"] = case["core_result"]["categories"][:1]
        nav = scope.observe(case)["navigation"]
        self.assertEqual(nav["display_units"][0]["coverage"], "partial")
        self.assertEqual(nav["accepted_finding_ids"], ["cap-part"])

    def test_each_incomplete_signal_blocks_completed_inventory(self):
        for signal in ("parser", "job", "stage", "truncation", "boundary", "category"):
            with self.subTest(signal=signal):
                case = self.case()
                if signal == "parser":
                    case["parser"]["complete"] = False
                elif signal == "job":
                    case["job"]["status"] = "partial"
                elif signal == "stage":
                    case["job"]["unfinished_stages"] = ["retrieval"]
                elif signal == "truncation":
                    case["job"]["candidate_search_truncated"] = True
                elif signal == "boundary":
                    case["job"]["boundary_coverage_complete"] = False
                else:
                    case["core_result"]["categories"][0].update(search_complete=False, windows_total=2)
                nav = scope.observe(case)["navigation"]
                self.assertEqual(nav["status"], "processing_incomplete")
                self.assertIsNone(nav["manual_review_items"])
                self.assertIsNone(nav["manual_review_count"])

    def test_incomplete_parsing_cannot_claim_absence(self):
        case = self.case("02-outside-only")
        case["parser"]["complete"] = False
        with self.assertRaisesRegex(ValueError, "must not claim absence"):
            scope.observe(case)

    def test_cancelled_case_has_no_invented_core_result(self):
        case = self.case("06-cancelled")
        self.assertIsNone(case["core_result"])
        self.assertEqual(scope.observe(case)["category_states"], {})
        case["job"]["status"] = "completed"
        with self.assertRaisesRegex(ValueError, "Only cancelled"):
            scope.observe(case)

    def test_missing_regions_have_locators_not_fabricated_text_offsets(self):
        case = self.case("06-parser-omission")
        self.assertEqual(set(case["parser"]["unavailable_regions"][0]), {"locator", "reason"})
        case["parser"]["complete"] = True
        with self.assertRaisesRegex(ValueError, "Missing source regions"):
            scope.observe(case)

    def test_proposed_category_cannot_claim_supported_decision(self):
        case = self.case("08-proposed-requested")
        category = case["core_result"]["categories"][-1]
        category.update(status="abstained", reason_code="unvalidated")
        with self.assertRaisesRegex(ValueError, "Proposed category"):
            scope.observe(case)

    def test_hash_and_document_identity_changes_are_rejected(self):
        for target in ("source", "core_id", "span_id"):
            with self.subTest(target=target):
                case = self.case()
                if target == "source":
                    case["document"]["text"] += " altered"
                elif target == "core_id":
                    case["document"]["doc_id"] = "different-document"
                else:
                    case["core_result"]["categories"][0]["clauses"][0]["span"]["doc_id"] = "different-document"
                with self.assertRaises(ValueError):
                    scope.observe(case)

    def test_fixture_confidence_cannot_be_misrepresented(self):
        case = self.case()
        case["core_result"]["categories"][0]["clauses"][0]["confidence"] = 0.99
        with self.assertRaisesRegex(ValueError, "claims model confidence"):
            scope.observe(case)

    def test_unknown_requested_category_is_rejected(self):
        case = self.case()
        case["requested_category_ids"].append("unknown.category")
        with self.assertRaisesRegex(ValueError, "Requested category scope"):
            scope.observe(case)

    def test_corrupted_expectations_fail_even_when_inputs_are_valid(self):
        for target in ("missing_manual_item", "all_clear", "zero_instead_of_unknown"):
            with self.subTest(target=target):
                case = self.case("06-parser-omission" if target == "zero_instead_of_unknown"
                                 else "01-supported-and-outside")
                if target == "missing_manual_item":
                    case["expected"]["navigation"]["manual_review_items"] = []
                elif target == "all_clear":
                    case["expected"]["presentation"]["safety_verdict_allowed"] = True
                else:
                    case["expected"]["navigation"]["manual_review_count"] = 0
                with self.assertRaisesRegex(ValueError, "expected/reference mismatch"):
                    scope.verify_case(case)

    def test_broken_hierarchy_falls_back_without_omitting_text(self):
        for defect in ("cycle", "missing_parent", "bad_range"):
            with self.subTest(defect=defect):
                case = self.case()
                node = case["parser"]["nodes"][0]
                if defect == "cycle":
                    node["parent_id"] = node["id"]
                elif defect == "missing_parent":
                    node["parent_id"] = "missing"
                else:
                    node["end"] = len(case["document"]["text"]) + 1
                observed = scope.observe(case)
                self.assertEqual(observed["navigation"]["unit_source"], "paragraph_fallback")
                self.assertEqual(len(observed["navigation"]["display_units"]), 2)

    def test_manifest_detects_changed_fixture_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "scope"
            shutil.copytree(scope.FIXTURES, root)
            path = root / "01_supported_and_outside.json"
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                scope.load_families(root)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"state": "absent", "state": "found"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                scope.read_json(path)


if __name__ == "__main__":
    unittest.main()
