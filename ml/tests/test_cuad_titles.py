"""Regression checks for title screening; synthetic titles, no dataset required."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from review_cuad_titles import parse_title, screen_titles, title_signals


def group(key, titles, split="train"):
    return {"group_id": key, "official_split": split,
            "source_documents": [{"title": t} for t in titles],
            "paragraphs": [{"index": 0, "code_points": 1, "text_sha256": "0" * 64}]}


def fixture():
    base = "ACME,INC_01_02_2020-EX-10.2-AGREEMENT"
    groups = [
        group("a", [base, base + "(1)"]),
        group("b", ["AcmeInc_20200102_8-K_EX-10.02_123_EX-10.02_Attachment"]),
        group("c", ["ACMEINC_02_02_2021-EX-10.8-AGREEMENT"], "test"),
        group("d", ["OTHER,INC_01_02_2020-EX-10.2-AGREEMENT"]),
        group("e", ["UnstructuredTitleWithoutKnownSeparator"]),
    ]
    manifest = {"families": [{"family_id": "synthetic-family-ab",
                               "members": [{"group_id": "a"}, {"group_id": "b"}]}]}
    return groups, manifest


class CuadTitleTests(unittest.TestCase):
    def test_two_filename_formats_and_exhibit_zero_padding(self):
        a = parse_title("ACME,INC_01_02_2020-EX-10.2-AGREEMENT")
        b = parse_title("AcmeInc_20200102_8-K_EX-10.02_123_EX-10.02_Attachment")
        self.assertEqual(a["issuer_key"], "acmeinc")
        self.assertEqual(a["filing_date_from_title"], "2020-01-02")
        self.assertEqual(title_signals(a, b)[-1], "matching_title_date_and_exhibit")
        self.assertEqual(b["exhibit_label_from_title"], "EX-10.02")

    def test_underscores_in_issuer_are_not_mistaken_for_date_boundary(self):
        m = parse_title("BABCOCK_WILCOXENTERPRISES,INC_08_04_2015-EX-10.17-AGREEMENT")
        self.assertEqual(m["issuer_text"], "BABCOCK_WILCOXENTERPRISES,INC")
        self.assertEqual(m["filing_date_from_title"], "2015-08-04")
        self.assertEqual(m["exhibit_key"], "ex-10.17")

    def test_plain_title_keeps_unknown_date_and_exhibit_unknown(self):
        title = "LECLANCHE\u0301 S.A. - JOINT DEVELOPMENT _ MARKETING AGREEMENT"
        m = parse_title(title)
        self.assertEqual(m["source_title"], title)
        self.assertEqual(m["issuer_key"], "leclanch\u00e9sa")
        self.assertIsNone(m["filing_date_from_title"])
        self.assertIsNone(m["exhibit_key"])
        self.assertEqual(m["issues"], [])

    def test_nonstandard_exhibit_and_empty_description(self):
        titles = [
            "ExampleInc_20191227_1-A_EX1A-6 MAT CTRCT_11933379_EX1A-6 MAT CTRCT_License Agreement",
            "EXAMPLE,INC_03_31_2020-EX1A-1 UNDR AGMT-SERVICES AGREEMENT",
            "MSCIINC_02_28_2008-EX-10.10-",
        ]
        for title in titles:
            with self.subTest(title=title):
                m = parse_title(title)
                self.assertIsNotNone(m["exhibit_key"])
                self.assertEqual(m["issues"], [])

    def test_conflicting_exhibit_labels_are_not_silently_selected(self):
        m = parse_title("ExampleInc_20191227_1-A_EX-10.1_11933379_EX-10.2_Agreement")
        self.assertEqual(m["issuer_key"], "exampleinc")
        self.assertIsNone(m["exhibit_key"])
        self.assertIn("conflicting_title_exhibit_labels", m["issues"])

    def test_invalid_calendar_date_is_reported(self):
        m = parse_title("ExampleInc_02_30_2020-EX-10.1-AGREEMENT")
        self.assertEqual(m["issuer_key"], "exampleinc")
        self.assertIsNone(m["filing_date_from_title"])
        self.assertIn("invalid_title_date", m["issues"])

    def test_unstructured_issuer_is_exposed_without_guessing(self):
        m = parse_title("XACCT Technologies, Inc.SUPPORT AND MAINTENANCE AGREEMENT")
        self.assertIsNone(m["issuer_key"])
        self.assertEqual(m["issues"], ["unparsed_issuer"])

    def test_two_missing_dates_do_not_count_as_a_date_match(self):
        a = parse_title("Acme Inc. - Master Services Agreement")
        b = parse_title("ACME INC - Amendment")
        self.assertEqual(title_signals(a, b), ["matching_issuer_key"])

    def test_exact_duplicates_collapse_and_new_pairs_stay_pending(self):
        groups, manifest = fixture()
        result = screen_titles(groups, manifest)
        self.assertEqual(result["summary"]["source_documents"], 6)
        self.assertEqual(result["summary"]["candidate_group_pairs"], 3)
        self.assertEqual(result["summary"]["same_exact_group_title_pairs_skipped"], 1)
        self.assertEqual(result["summary"]["already_in_reviewed_family"], 1)
        self.assertEqual(result["summary"]["pending_cross_split_pairs"], 2)
        self.assertEqual(result["summary"]["titles_without_issuer_key"], 1)
        ab = next(c for c in result["candidates"] if c["left"]["group_id"] == "a"
                  and c["right"]["group_id"] == "b")
        self.assertEqual(len(ab["title_evidence"]), 2)
        self.assertEqual(ab["strongest_title_signal"], "matching_title_date_and_exhibit")
        self.assertFalse(any("d" in (c["left"]["group_id"], c["right"]["group_id"])
                             for c in result["candidates"]))

    def test_existing_family_membership_includes_transitive_pairs(self):
        groups, manifest = fixture()
        manifest["families"][0]["members"].append({"group_id": "c"})
        result = screen_titles(groups, manifest)
        self.assertEqual(result["summary"]["already_in_reviewed_family"], 3)
        self.assertEqual(result["summary"]["pending_source_review"], 0)

    def test_screen_is_deterministic_and_does_not_change_inputs(self):
        groups, manifest = fixture()
        before = deepcopy((groups, manifest))
        first = screen_titles(groups, manifest)
        second = screen_titles(list(reversed(groups)), manifest)
        self.assertEqual(first, second)
        self.assertEqual(before, (groups, manifest))


if __name__ == "__main__":
    unittest.main()
