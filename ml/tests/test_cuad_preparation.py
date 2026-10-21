"""Preparation boundary, deduplication and exact-span tests; no data downloads."""

from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_cuad_inventory import build_groups
from cuad_review_policy import preparation_view, question_holds
from prepare_cuad_pool import build_pool, write_preparation


def fixture():
    mappings = [{"source_label": label, "category_id": cid, "question": "Find " + label,
                 "cuad_annotated": True}
                for label, cid in (("Terms", "cuad.terms"), ("Other", "cuad.other"),
                                   ("Anti-Assignment", "cuad.anti_assignment"),
                                   ("Exclusivity", "cuad.exclusivity"))]
    mappings.append({"source_label": None, "category_id": "in.arbitration",
                     "question": "Find arbitration", "cuad_annotated": False})
    full = {}
    for title in ("A", "A-copy", "B", "C", "D", "E"):
        context = ("" if title in ("A", "A-copy") else title + " ") + "😀 keep\r\nclause; clause\u00a0 "
        first, last = context.index("clause"), context.rindex("clause")
        qas = []
        for row in mappings[:-1]:
            label = row["source_label"]
            answers = ([{"answer_start": first, "text": "clause"},
                        {"answer_start": last, "text": "clause"},
                        {"answer_start": first, "text": "clause"}]
                       if label == "Terms" else [])
            if title == "A-copy" and label in ("Anti-Assignment", "Exclusivity"):
                answers = [{"answer_start": first, "text": "clause"}]
            qas.append({"id": title + "__" + label, "question": row["question"],
                        "is_impossible": not answers, "answers": answers})
        full[title] = {"title": title, "paragraphs": [{"context": context, "qas": qas}]}
    test = {"D": full["D"]}
    train = {t: d for t, d in full.items() if t not in test}
    groups = build_groups(full, train, test)
    ids = {d["title"]: g["group_id"] for g in groups for d in g["source_documents"]}
    view = preparation_view(groups, [(ids["A"], ids["B"]), (ids["D"], ids["E"])],
                            [(ids["C"], ids["D"])])
    return full, groups, view, mappings, question_holds(groups)


class CuadPreparationTests(unittest.TestCase):
    def setUp(self):
        self.args = fixture()
        self.full, self.groups, self.view, self.mapping, self.holds = self.args

    def run_pool(self):
        return build_pool(*self.args)

    def gid(self, title):
        return next(g["group_id"] for g in self.groups
                    if title in [d["title"] for d in g["source_documents"]])

    def test_accounting_after_holds_and_deduplication(self):
        pool, summary, _ = self.run_pool()
        self.assertEqual(summary, {
            "source_documents": 3, "exact_text_groups": 2, "family_units": 1,
            "original_questions_before_question_holds": 12,
            "held_original_question_records": 4, "held_group_category_questions": 2,
            "deduplicated_original_question_records": 2,
            "questions": 6, "positive_questions": 2, "no_answer_questions": 4, "answer_spans": 6,
        })
        self.assertEqual({t for g in pool for t in g["source_titles"]}, {"A", "A-copy", "B"})
        self.assertEqual(len({g["family_id"] for g in pool}), 1)

    def test_no_input_mutation(self):
        before = deepcopy(self.args)
        self.run_pool()
        self.assertEqual(before, self.args)

    def test_order_changes_do_not_change_output(self):
        expected = self.run_pool()
        changed = deepcopy(self.args)
        full, groups, view, _, _ = changed
        for document in full.values():
            for p in document["paragraphs"]:
                p["qas"].reverse()
                for q in p["qas"]:
                    q["answers"].reverse()
        groups.reverse()
        for g in groups:
            g["source_documents"].reverse()
        view["eligible_components"].reverse()
        for component in view["eligible_components"]:
            component.reverse()
        self.assertEqual(expected, build_pool(*changed))

    def test_exact_context_unicode_offsets_and_answer_multiplicity(self):
        pool, _, _ = self.run_pool()
        a = next(g for g in pool if "A" in g["source_titles"])
        p = a["paragraphs"][0]
        self.assertEqual(p["context"], "😀 keep\r\nclause; clause\u00a0 ")
        q = next(q for q in p["questions"] if q["category_id"] == "cuad.terms")
        self.assertEqual([(a["start"], a["end"]) for a in q["answers"]], [(8, 14), (8, 14), (16, 22)])
        self.assertEqual(q["source_questions"], [
            {"source_title": "A", "source_question_id": "A__Terms"},
            {"source_title": "A-copy", "source_question_id": "A-copy__Terms"},
        ])
        for answer in q["answers"]:
            self.assertEqual(p["context"][answer["start"]:answer["end"]], answer["text"])

    def test_held_questions_are_absent_not_negative(self):
        pool, _, _ = self.run_pool()
        a = next(g for g in pool if "A" in g["source_titles"])
        self.assertEqual({q["source_label"] for q in a["paragraphs"][0]["questions"]}, {"Terms", "Other"})

    def test_related_contexts_and_labels_stay_separate(self):
        pool, _, support = self.run_pool()
        self.assertEqual(len(pool), 2)
        self.assertNotEqual(pool[0]["paragraphs"][0]["context"], pool[1]["paragraphs"][0]["context"])
        b = next(g for g in pool if g["source_titles"] == ["B"])
        anti = next(q for q in b["paragraphs"][0]["questions"] if q["source_label"] == "Anti-Assignment")
        self.assertTrue(anti["is_impossible"])
        self.assertEqual(anti["answers"], [])
        terms = next(r for r in support if r["category_id"] == "cuad.terms")
        self.assertEqual(terms["positive_questions"], 2)
        self.assertEqual(terms["positive_family_units"], 1)

    def test_unannotated_india_category_never_becomes_negative(self):
        pool, _, support = self.run_pool()
        self.assertFalse(any(q["category_id"].startswith("in.") for g in pool
                             for p in g["paragraphs"] for q in p["questions"]))
        india = next(r for r in support if r["category_id"] == "in.arbitration")
        self.assertEqual(india["annotation_status"], "unannotated_in_cuad")
        self.assertEqual(india["questions"], 0)
        self.assertEqual(india["no_answer_questions"], 0)

    def test_official_test_cannot_enter_pool(self):
        self.view["eligible_components"].append([self.gid("D")])
        with self.assertRaisesRegex(ValueError, "Official test"):
            self.run_pool()

    def test_reserved_training_cannot_enter_pool(self):
        for title in ("C", "E"):
            with self.subTest(title=title):
                self.view["eligible_components"].append([self.gid(title)])
                with self.assertRaisesRegex(ValueError, "Reserved group"):
                    self.run_pool()
                self.view["eligible_components"].pop()

    def test_a_group_cannot_repeat_in_separate_families(self):
        self.view["eligible_components"].append([self.gid("A")])
        with self.assertRaisesRegex(ValueError, "multiple eligible"):
            self.run_pool()

    def test_unheld_conflict_cannot_choose_a_copy(self):
        self.holds.pop()
        with self.assertRaisesRegex(ValueError, "Unheld duplicate annotations"):
            self.run_pool()

    def test_hold_must_cover_both_source_question_ids(self):
        self.holds[0]["source_question_ids"].pop()
        with self.assertRaisesRegex(ValueError, "hold identity"):
            self.run_pool()

    def test_nonexistent_eligible_question_hold_is_rejected(self):
        self.holds.append({**self.holds[0], "paragraph_index": 99})
        with self.assertRaisesRegex(ValueError, "hold was not applied"):
            self.run_pool()

    def test_changed_context_is_rejected(self):
        self.full["A-copy"]["paragraphs"][0]["context"] += "changed"
        with self.assertRaisesRegex(ValueError, "contexts differ"):
            self.run_pool()

    def test_changed_span_is_rejected(self):
        self.full["B"]["paragraphs"][0]["qas"][0]["answers"][0]["answer_start"] += 1
        with self.assertRaisesRegex(ValueError, "span does not match"):
            self.run_pool()

    def test_missing_question_is_not_synthesized_as_negative(self):
        self.full["B"]["paragraphs"][0]["qas"].pop()
        with self.assertRaisesRegex(ValueError, "Missing or extra"):
            self.run_pool()

    def test_question_wording_cannot_be_rewritten(self):
        self.mapping[0]["question"] = "Simplified question"
        with self.assertRaisesRegex(ValueError, "Exact source question"):
            self.run_pool()

    def test_existing_different_report_prevents_both_writes(self):
        with TemporaryDirectory() as folder:
            repo = Path(folder)
            output = repo / "data/processed/cuad"
            output.mkdir(parents=True)
            report_path = output / "preparation_report.json"
            report_path.write_bytes(b"preserve existing report")
            with self.assertRaisesRegex(ValueError, "not replaced"):
                write_preparation(repo, {"groups": []}, {"summary": {}})
            self.assertFalse((output / "preparation_pool.json").exists())
            self.assertEqual(report_path.read_bytes(), b"preserve existing report")

    def test_repeated_save_does_not_change_outputs(self):
        with TemporaryDirectory() as folder:
            repo = Path(folder)
            pool, report = {"groups": []}, {"summary": {}}
            self.assertEqual(write_preparation(repo, pool, report), 2)
            self.assertEqual(write_preparation(repo, pool, report), 0)


if __name__ == "__main__":
    unittest.main()
