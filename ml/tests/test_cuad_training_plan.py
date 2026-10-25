"""Guard fit-only sampling, gold coverage and immutable plan publication."""

from copy import deepcopy
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import read_json
from prepare_cuad_features import FeatureTokenizer, IGNORE, NEGATIVE, POSITIVE, build_shard
from prepare_cuad_training_plan import inspect_group, pools, prepare, sample_epoch, validate_selection


def record(qid, pos, neg, absent=False, partition="fit"):
    return {"question_id": qid, "positive_indices": pos, "negative_indices": neg,
            "is_impossible": absent, "partition": partition}


def sampling_fixture():
    return [record("positive-a", [0, 1], list(range(2, 10))),
            record("absent-a", [], list(range(10, 14)), True),
            record("absent-b", [], list(range(14, 19)), True),
            record("unsupported-positive", [], [19, 20, 21]),
            record("positive-b", [23], list(range(24, 31)))]


class CuadSamplingTests(unittest.TestCase):
    def test_all_positives_two_to_one_and_absent_minimum_are_preserved(self):
        rows = sampling_fixture()
        result = sample_epoch(rows, 1)
        indices = set(result["global_fit_window_indices"])
        self.assertTrue({0, 1, 23} <= indices)
        self.assertTrue(indices.intersection(range(10, 14)))
        self.assertTrue(indices.intersection(range(14, 19)))
        self.assertEqual(result["summary"]["negative_windows"], 6)
        self.assertEqual(result["summary"]["total_windows"], 9)
        self.assertEqual(result["summary"]["effective_negative_to_positive_ratio"], 2)

    def test_epochs_are_reproducible_and_change_without_mutating_candidates(self):
        rows = sampling_fixture()
        before = deepcopy(rows)
        first = [sample_epoch(rows, e) for e in (1, 2, 3)]
        self.assertEqual(first, [sample_epoch(rows, e) for e in (1, 2, 3)])
        self.assertNotEqual(first[0]["global_fit_window_indices"], first[1]["global_fit_window_indices"])
        self.assertEqual(rows, before)

    def test_unsupported_positive_and_ignored_windows_are_never_sampled(self):
        for epoch in (1, 2, 3):
            result = sample_epoch(sampling_fixture(), epoch)
            self.assertFalse(set(result["global_fit_window_indices"]) & {19, 20, 21, 22})
            self.assertEqual(result["summary"]["unsampled_positive_questions"], 1)

    def test_development_records_are_rejected(self):
        for split in ("dev_select", "dev_cal", "dev_policy"):
            rows = sampling_fixture()
            rows[0]["partition"] = split
            with self.assertRaisesRegex(ValueError, "fit records only"):
                sample_epoch(rows, 1)

    def test_every_absent_question_minimum_overrides_small_ratio_budget(self):
        rows = [record("p", [0], [])] + [record(f"n{i}", [], [i], True) for i in range(1, 5)]
        result = sample_epoch(rows, 1)
        self.assertEqual(set(result["global_fit_window_indices"]), set(range(5)))
        self.assertTrue(result["summary"]["minimum_overrode_ratio"])

    def test_negative_shortage_is_reported_without_replacement(self):
        result = sample_epoch([record("p", [0, 1], [2])], 1)
        self.assertEqual(set(result["global_fit_window_indices"]), {0, 1, 2})
        self.assertEqual(result["summary"]["negative_candidate_shortfall"], 3)

    def test_duplicate_global_indices_and_question_ids_are_rejected(self):
        rows = sampling_fixture()
        rows[1]["negative_indices"].append(0)
        with self.assertRaisesRegex(ValueError, "global feature index"):
            sample_epoch(rows, 1)
        rows = sampling_fixture()
        rows[1]["question_id"] = rows[0]["question_id"]
        with self.assertRaisesRegex(ValueError, "Repeated fit question"):
            sample_epoch(rows, 1)

    def test_absent_question_without_negative_and_fit_without_positive_fail(self):
        with self.assertRaisesRegex(ValueError, "Absent question"):
            sample_epoch([record("p", [0], []), record("n", [], [], True)], 1)
        with self.assertRaisesRegex(ValueError, "No usable positive"):
            sample_epoch([record("n", [], [0], True)], 1)

    def test_invalid_epoch_and_boolean_selected_index_fail(self):
        for epoch in (True, 0, 4):
            with self.assertRaisesRegex(ValueError, "Epoch"):
                sample_epoch(sampling_fixture(), epoch)
        with self.assertRaisesRegex(ValueError, "integers"):
            validate_selection([True], sampling_fixture())

    def test_selection_cannot_drop_positive_or_introduce_ignored_window(self):
        rows = sampling_fixture()
        selected = sample_epoch(rows, 1)["global_fit_window_indices"]
        changed = [22 if i == 0 else i for i in selected]
        with self.assertRaisesRegex(ValueError, "lost positives"):
            validate_selection(changed, rows)

    def test_duplicate_selected_window_fails(self):
        rows = sampling_fixture()
        selected = sample_epoch(rows, 1)["global_fit_window_indices"]
        with self.assertRaisesRegex(ValueError, "Repeated selected"):
            validate_selection(selected + [selected[0]], rows)

    def test_absent_question_cannot_be_omitted_even_if_total_budget_matches(self):
        rows = sampling_fixture()
        selected = [0, 1, 23, 2, 3, 4, 5, 10, 11]
        with self.assertRaisesRegex(ValueError, "absent question"):
            validate_selection(selected, rows)

    def test_plan_writes_small_outputs_and_reuses_them_without_feature_edits(self):
        rows = sampling_fixture()
        with TemporaryDirectory() as temp:
            repo = Path(temp)
            features = repo / "data/processed/cuad/features_v1"
            features.mkdir(parents=True)
            sentinel = features / "source.txt"
            sentinel.write_text("unchanged", encoding="utf-8")
            with redirect_stdout(StringIO()), patch("prepare_cuad_training_plan.verify_ignored_assets"), \
                 patch("prepare_cuad_training_plan.audit_features", return_value=({"gold_preserved": True}, rows, [], {"feature_identity_sha256": "test"})):
                first = prepare(repo)
                second = prepare(repo)
                self.assertEqual(first, second)
                self.assertEqual(sentinel.read_text(), "unchanged")
                output = repo / "data/processed/cuad/training_plan_v1"
                self.assertEqual(read_json(output / "manifest.json")["status"], "coverage_audited_fit_samples_prepared")
                (output / "epoch_1.json").write_text('{"changed": true}', encoding="utf-8")
                before = (output / "epoch_2.json").read_bytes()
                with self.assertRaisesRegex(ValueError, "preserved"):
                    prepare(repo)
                self.assertEqual((output / "epoch_2.json").read_bytes(), before)


class CuadFeatureCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        model = Path(__file__).resolve().parents[2] / "models/cuad_clean_backbone/roberta-base"
        if not (model / "tokenizer.json").is_file() or importlib.util.find_spec("transformers") is None:
            raise unittest.SkipTest("Prepare the pinned training tokenizer for feature-coverage integration tests.")
        cls.engine = FeatureTokenizer(model)

    def fixture(self):
        import numpy as np
        context = "Alpha beta payment clause. " * 160
        _, offsets = self.engine.context(context)
        def span(start, end):
            return {"start": start, "end": end, "text": context[start:end]}
        short = span(context.index("beta"), context.index("beta") + 4)
        long = span(offsets[0][0], offsets[399][1])
        gap = span(offsets[300][0], offsets[529][1])
        questions = []
        for qid, gold in (("positive", [short, deepcopy(short), long, gap]), ("absent", []), ("long-only", [long])):
            questions.append({"question_id": qid, "category_id": "cuad.example", "source_label": "Example",
                              "question": "Which payment?", "is_impossible": not bool(gold), "answers": gold,
                              "source_questions": [{"source_question_id": qid}]})
        group = {"group_id": "g1", "family_id": "f1", "source_titles": ["contract"], "official_split": "train",
                 "paragraphs": [{"index": 0, "context": context, "questions": questions}]}
        with TemporaryDirectory() as temp:
            path = Path(temp)
            manifest = build_shard(path, group, "fit", "test", self.engine)
            audit = read_json(path / "source.json")["question_audit"]
            arrays = {name: np.load(path / (name + ".npy"), allow_pickle=False)
                      for name in ("window_index", "question_ranges", "gold_pairs", "gold_refs", "sequence_ids", "offsets")}
        return group, audit, arrays, manifest

    def test_real_tokenizer_multi_answer_audit_preserves_counts_and_sampling_holds(self):
        group, audit, arrays, manifest = self.fixture()
        records, rows, issues = inspect_group(group, audit, arrays)
        self.assertEqual(sum(c["answer_occurrences"] for _, c in rows), 5)
        self.assertEqual(sum(c["covered_answer_occurrences"] for _, c in rows), manifest["summary"]["covered_answer_occurrences"])
        self.assertEqual(pools(records)[3], ["long-only"])
        self.assertTrue(any(i["positive_windows"] == 0 for i in issues))
        self.assertEqual(len(group["paragraphs"][0]["questions"][0]["answers"]), 4)

    def test_partial_or_long_window_cannot_be_relabelled_as_no_answer(self):
        import numpy as np
        group, audit, arrays, _ = self.fixture()
        start, end = arrays["question_ranges"][2]
        row = next(int(i) for i in range(int(start), int(end)) if arrays["window_index"][i, 2] == IGNORE)
        arrays["window_index"][row, 2] = NEGATIVE
        old = arrays["gold_pairs"]
        insertion = int(np.searchsorted(old[:, 0], row))
        arrays["gold_pairs"] = np.insert(old, insertion, [row, 0, 0], axis=0)
        arrays["gold_refs"][:, 0] += arrays["gold_refs"][:, 0] >= insertion
        audit[2]["negative_windows"] += 1
        audit[2]["ignored_windows"] -= 1
        with self.assertRaisesRegex(ValueError, "Gold-overlap"):
            inspect_group(group, audit, arrays)

    def test_omitted_complete_gold_pair_fails_even_after_adjusting_audit_counts(self):
        import numpy as np
        group, audit, arrays, _ = self.fixture()
        pair = int(np.flatnonzero(arrays["gold_pairs"][:, 1] > 0)[0])
        row = int(arrays["gold_pairs"][pair, 0])
        arrays["gold_pairs"] = np.delete(arrays["gold_pairs"], pair, axis=0)
        refs = arrays["gold_refs"]
        refs = refs[refs[:, 0] != pair]
        refs[:, 0] -= refs[:, 0] > pair
        arrays["gold_refs"] = refs
        arrays["window_index"][row, 2] = IGNORE
        audit[0]["positive_windows"] -= 1
        audit[0]["ignored_windows"] += 1
        for answer in audit[0]["answers"][:2]:
            answer["usable_windows"] = 0
        with self.assertRaisesRegex(ValueError, "complete gold target"):
            inspect_group(group, audit, arrays)

    def test_duplicate_joint_pair_cannot_inflate_training_probability(self):
        import numpy as np
        group, audit, arrays, _ = self.fixture()
        arrays["gold_pairs"] = np.vstack([arrays["gold_pairs"], arrays["gold_pairs"][0]])
        with self.assertRaisesRegex(ValueError, "Duplicate loss pair"):
            inspect_group(group, audit, arrays)

    def test_reference_cannot_select_an_unsupported_answer(self):
        group, audit, arrays, _ = self.fixture()
        arrays["gold_refs"][0, 1] = 2
        with self.assertRaisesRegex(ValueError, "Unsupported answer"):
            inspect_group(group, audit, arrays)

    def test_changed_source_offset_is_rejected(self):
        group, audit, arrays, _ = self.fixture()
        row, start, _ = arrays["gold_pairs"][0]
        arrays["offsets"][row, start, 0] += 1
        with self.assertRaisesRegex(ValueError, "offsets"):
            inspect_group(group, audit, arrays)

    def test_gold_pair_cannot_point_into_question_tokens(self):
        group, audit, arrays, _ = self.fixture()
        row, start, _ = arrays["gold_pairs"][0]
        arrays["sequence_ids"][row, start] = 0
        with self.assertRaisesRegex(ValueError, "question/special"):
            inspect_group(group, audit, arrays)

    def test_missing_question_range_and_changed_identity_are_rejected(self):
        group, audit, arrays, _ = self.fixture()
        arrays["question_ranges"][1, 0] += 1
        with self.assertRaisesRegex(ValueError, "Question ranges"):
            inspect_group(group, audit, arrays)
        group, audit, arrays, _ = self.fixture()
        audit[0]["question_id"] = "other"
        with self.assertRaisesRegex(ValueError, "identity"):
            inspect_group(group, audit, arrays)

    def test_invented_occurrence_coverage_and_wrong_truncation_are_rejected(self):
        group, audit, arrays, _ = self.fixture()
        audit[0]["answers"][0]["usable_windows"] += 1
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            inspect_group(group, audit, arrays)
        group, audit, arrays, _ = self.fixture()
        audit[0]["used_question_tokens"] = 65
        with self.assertRaisesRegex(ValueError, "truncation"):
            inspect_group(group, audit, arrays)

    def test_changed_context_stride_is_rejected(self):
        group, audit, arrays, _ = self.fixture()
        arrays["window_index"][1, 1] += 1
        with self.assertRaisesRegex(ValueError, "overlap"):
            inspect_group(group, audit, arrays)


if __name__ == "__main__":
    unittest.main()
