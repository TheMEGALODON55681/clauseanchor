"""Protect source alignment, multi-answer targets, partition binding and resume."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import canonical_sha256, read_json
from prepare_cuad_features import (
    IGNORE, NEGATIVE, POSITIVE, FeatureTokenizer, align_answers, bind_features,
    build_shard, verify_shard, window_count, window_targets,
)


def answer(context, start, end):
    return {"start": start, "end": end, "text": context[start:end]}


def targets(context, gold, first, last, limit_offsets=None):
    offsets = limit_offsets or [(i, i + 1) for i in range(len(context))]
    aligned = align_answers(context, offsets, gold)
    positions = list(range(4, 4 + last - first))
    local = [(0, 0)] * 4 + offsets[first:last]
    return window_targets(gold, aligned, first, positions, local), aligned


class CuadFeatureTargetTests(unittest.TestCase):
    def test_unicode_byte_pieces_use_earliest_start_and_latest_end(self):
        context, offsets = "₹😊x", [(0, 1)] * 3 + [(1, 2)] * 4 + [(2, 3)]
        rows = align_answers(context, offsets, [answer(context, 0, 2)])
        self.assertEqual((rows[0]["start_token"], rows[0]["end_token"]), (0, 6))
        (status, pairs), _ = targets(context, [answer(context, 0, 2)], 1, 8, offsets)
        self.assertEqual((status, pairs), (IGNORE, {}))

    def test_multiple_answers_form_joint_pairs_without_cross_combinations(self):
        context = "abcdefghij"
        (status, pairs), _ = targets(context, [answer(context, 1, 3), answer(context, 7, 9)], 0, 10)
        self.assertEqual((status, pairs), (POSITIVE, {(5, 6): [0], (11, 12): [1]}))
        self.assertNotIn((5, 12), pairs)

    def test_duplicate_annotations_share_one_target_and_keep_both_references(self):
        context = "abcdef"
        (status, pairs), aligned = targets(context, [answer(context, 1, 3)] * 2, 0, 6)
        self.assertEqual((status, pairs), (POSITIVE, {(5, 6): [0, 1]}))
        self.assertEqual([r["usable_windows"] for r in aligned], [1, 1])

    def test_partial_only_window_is_ignored_never_null(self):
        context = "abcdefghij"
        (status, pairs), _ = targets(context, [answer(context, 2, 8)], 0, 5)
        self.assertEqual((status, pairs), (IGNORE, {}))

    def test_complete_answer_remains_positive_when_another_is_clipped(self):
        context = "abcdefghij"
        (status, pairs), _ = targets(context, [answer(context, 1, 2), answer(context, 3, 8)], 0, 5)
        self.assertEqual((status, pairs), (POSITIVE, {(5, 5): [0]}))

    def test_true_negative_and_outside_gold_windows_use_null(self):
        context = "abcdefghij"
        for gold in ([], [answer(context, 7, 9)]):
            (status, pairs), _ = targets(context, gold, 0, 5)
            self.assertEqual((status, pairs), (NEGATIVE, {(0, 0): []}))

    def test_long_answer_keeps_gold_but_cannot_be_positive_or_null(self):
        context = "x" * 400
        gold = [answer(context, 0, 257)]
        original = deepcopy(gold)
        (status, pairs), aligned = targets(context, gold, 0, 400)
        self.assertEqual((status, pairs), (IGNORE, {}))
        self.assertEqual(aligned[0]["reason"], "longer_than_256_tokens")
        self.assertEqual(gold, original)

    def test_exact_256_token_answer_is_allowed(self):
        context = "x" * 400
        (status, pairs), _ = targets(context, [answer(context, 0, 256)], 0, 400)
        self.assertEqual((status, pairs), (POSITIVE, {(4, 259): [0]}))

    def test_whitespace_boundary_is_reported_without_stripping_or_relocation(self):
        context = " ab ab"
        gold = [answer(context, 0, 3)]
        (status, pairs), aligned = targets(context, gold, 0, 3, [(1, 3), (4, 6), (6, 6)])
        self.assertEqual((status, pairs), (IGNORE, {}))
        self.assertEqual(aligned[0]["reason"], "unmapped_boundary")
        self.assertEqual(gold[0]["text"], " ab")

    def test_subword_boundary_projection_is_explicit_and_original_gold_is_preserved(self):
        context = "payment"
        gold = [answer(context, 1, 4)]
        row = align_answers(context, [(0, 3), (3, 7)], gold)[0]
        self.assertEqual((row["projected_start"], row["projected_end"]), (0, 7))
        self.assertFalse(row["exact_boundaries"])
        self.assertEqual(gold[0], {"start": 1, "end": 4, "text": "aym"})

    def test_changed_source_span_fails_instead_of_searching_for_a_matching_copy(self):
        with self.assertRaisesRegex(ValueError, "original source"):
            align_answers("aa bb aa", [(0, 2), (3, 5), (6, 8)], [{"start": 3, "end": 5, "text": "aa"}])

    def test_regular_windows_can_miss_a_legal_answer_without_inventing_negatives(self):
        # 444-token capacity and step 316: answer crosses the first window end
        # and starts before the second window. Neither is a negative example.
        context = "x" * 800
        for first, last in ((0, 444), (316, 760)):
            (status, pairs), aligned = targets(context, [answer(context, 250, 450)], first, last)
            self.assertEqual((status, pairs), (IGNORE, {}))
            self.assertIsNone(aligned[0]["reason"])
            self.assertEqual(aligned[0]["usable_windows"], 0)

    def test_changed_identity_preserves_existing_output(self):
        with TemporaryDirectory() as temp:
            root, identity = Path(temp), {"partition": "fit", "policy": "fixed"}
            self.assertEqual(bind_features(root, identity), canonical_sha256(identity))
            before = (root / "identity.json").read_bytes()
            bind_features(root, identity)
            with self.assertRaisesRegex(ValueError, "changed"):
                bind_features(root, {**identity, "partition": "dev_select"})
            self.assertEqual((root / "identity.json").read_bytes(), before)

    def test_orphaned_outputs_cannot_be_adopted_into_new_run(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "fit").mkdir()
            with self.assertRaisesRegex(ValueError, "lacks its identity"):
                bind_features(root, {"version": 1})


class CuadFeatureTokenizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model_dir = Path(__file__).resolve().parents[2] / "models/cuad_clean_backbone/roberta-base"
        if (not (cls.model_dir / "tokenizer.json").is_file()
                or importlib.util.find_spec("transformers") is None
                or importlib.util.find_spec("numpy") is None):
            raise unittest.SkipTest("Run prepare_cuad_training_assets.py in the pinned environment for tokenizer/shard integration tests.")
        cls.engine = FeatureTokenizer(cls.model_dir)

    def test_short_question_windows_match_native_fast_tokenizer(self):
        from transformers import RobertaTokenizerFast
        native = RobertaTokenizerFast.from_pretrained(str(self.model_dir), local_files_only=True,
                                                     add_prefix_space=False, trim_offsets=True)
        context, question = "Payment is café ₹500, e\u0301 and 😊.\n" * 150, "Which payment is due?"
        reference = native(question, context, max_length=512, stride=128, truncation="only_second",
                           padding="max_length", return_overflowing_tokens=True, return_offsets_mapping=True)
        raw, offsets = self.engine.context(context)
        rows = list(self.engine.windows(raw, offsets, question))
        self.assertGreater(len(rows), 1)
        self.assertEqual(len(rows), len(reference["input_ids"]))
        for i, (_, row, _) in enumerate(rows):
            self.assertEqual(row.ids, reference["input_ids"][i])
            self.assertEqual(row.offsets, reference["offset_mapping"][i])
            self.assertEqual(row.sequence_ids, reference.sequence_ids(i))

    def test_long_question_uses_exact_first_64_tokens_and_context_overlap_is_128(self):
        question, context = "Which obligation applies? " * 30, "Pay in thirty days. " * 250
        raw, offsets = self.engine.context(context)
        rows = list(self.engine.windows(raw, offsets, question))
        expected_query = self.engine.raw.encode(question, add_special_tokens=False).ids[:64]
        self.assertEqual(len(expected_query), 64)
        self.assertEqual(len(rows), window_count(len(raw.ids), 64))
        previous = None
        for _, row, positions in rows:
            self.assertEqual([token for token, seq in zip(row.ids, row.sequence_ids) if seq == 0], expected_query)
            current = [(row.ids[i], row.offsets[i]) for i in positions]
            if previous is not None:
                self.assertEqual(previous[-128:], current[:128])
            previous = current

    def test_unicode_source_coordinates_cover_combining_and_multibyte_characters(self):
        context = "Payment: café ₹500 e\u0301 😊."
        raw, offsets = self.engine.context(context)
        for text in ("café", "₹500", "e\u0301", "😊"):
            start = context.index(text)
            gold = [answer(context, start, start + len(text))]
            aligned = align_answers(context, offsets, gold)
            self.assertTrue(aligned[0]["exact_boundaries"])
            token_start, enc, positions = next(self.engine.windows(raw, offsets, "What payment?"))
            status, pairs = window_targets(gold, aligned, token_start, positions, enc.offsets)
            self.assertEqual(status, POSITIVE)
            a, b = next(iter(pairs))
            self.assertEqual(context[enc.offsets[a][0]:enc.offsets[b][1]], text)

    def fixture(self):
        context = "Payment is café ₹500. " * 50
        start = context.index("₹500")
        gold = answer(context, start, start + 4)
        questions = [{"question_id": "positive", "category_id": "cuad.payment", "source_label": "Payment",
                      "question": "Which payment applies? " * 25, "is_impossible": False,
                      "answers": [gold, deepcopy(gold)], "source_questions": [{"source_question_id": "original-1"}]},
                     {"question_id": "absent", "category_id": "cuad.other", "source_label": "Other",
                      "question": "What other obligation?", "is_impossible": True,
                      "answers": [], "source_questions": [{"source_question_id": "original-2"}]}]
        return {"group_id": "g1", "family_id": "f1", "official_split": "train", "source_titles": ["contract"],
                "paragraphs": [{"index": 0, "context": context, "code_points": len(context), "questions": questions}]}

    def test_shard_preserves_source_gold_and_can_be_read_as_memory_maps(self):
        import numpy as np
        group = self.fixture()
        original = deepcopy(group)
        with TemporaryDirectory() as temp:
            path = Path(temp)
            manifest = build_shard(path, group, "fit", "identity", self.engine)
            self.assertEqual(verify_shard(path, group, "fit", "identity"), manifest)
            self.assertEqual(group, original)
            self.assertEqual(read_json(path / "source.json")["source_group"], original)
            self.assertEqual(manifest["summary"]["answer_occurrences"], 2)
            self.assertEqual(manifest["summary"]["truncated_questions"], 1)
            ids = np.load(path / "input_ids.npy", mmap_mode="r", allow_pickle=False)
            self.assertIsInstance(ids, np.memmap)
            self.assertEqual(ids.shape[1], 512)
            del ids
            pairs = np.load(path / "gold_pairs.npy", allow_pickle=False)
            refs = np.load(path / "gold_refs.npy", allow_pickle=False)
            positives = [i for i, (_, start, _) in enumerate(pairs) if start != 0]
            self.assertTrue(positives)
            for index in positives:
                self.assertEqual(refs[refs[:, 0] == index, 1].tolist(), [0, 1])

    def test_shard_rejects_cross_partition_reuse_or_changed_source(self):
        with TemporaryDirectory() as temp:
            path, group = Path(temp), self.fixture()
            build_shard(path, group, "fit", "identity", self.engine)
            with self.assertRaisesRegex(ValueError, "binding"):
                verify_shard(path, group, "dev_select", "identity")
            changed = deepcopy(group)
            changed["paragraphs"][0]["questions"][0]["answers"].pop()
            with self.assertRaisesRegex(ValueError, "binding"):
                verify_shard(path, changed, "fit", "identity")

    def test_corrupted_array_cannot_be_silently_reused(self):
        with TemporaryDirectory() as temp:
            path, group = Path(temp), self.fixture()
            build_shard(path, group, "fit", "identity", self.engine)
            file = path / "input_ids.npy"
            data = bytearray(file.read_bytes())
            data[-1] ^= 1
            file.write_bytes(data)
            with self.assertRaises(ValueError):
                verify_shard(path, group, "fit", "identity")

    def test_unreferenced_sidecar_does_not_change_verified_features(self):
        with TemporaryDirectory() as temp:
            path, group = Path(temp), self.fixture()
            expected = build_shard(path, group, "fit", "identity", self.engine)
            (path / "unrelated-sync-file.tmp").write_bytes(b"not a feature")
            self.assertEqual(verify_shard(path, group, "fit", "identity"), expected)

    def test_missing_required_array_is_still_rejected(self):
        with TemporaryDirectory() as temp:
            path, group = Path(temp), self.fixture()
            build_shard(path, group, "fit", "identity", self.engine)
            (path / "offsets.npy").unlink()
            with self.assertRaises(ValueError):
                verify_shard(path, group, "fit", "identity")

    def test_no_answer_windows_are_identical_when_only_annotations_change(self):
        import numpy as np
        group, absent = self.fixture(), self.fixture()
        for q in absent["paragraphs"][0]["questions"]:
            q["answers"], q["is_impossible"] = [], True
        with TemporaryDirectory() as a, TemporaryDirectory() as b:
            build_shard(Path(a), group, "fit", "identity", self.engine)
            build_shard(Path(b), absent, "fit", "identity", self.engine)
            for filename in ("input_ids.npy", "attention_mask.npy", "offsets.npy", "sequence_ids.npy", "question_ranges.npy"):
                np.testing.assert_array_equal(np.load(Path(a) / filename), np.load(Path(b) / filename))
            self.assertTrue((np.load(Path(b) / "window_index.npy")[:, 2] == NEGATIVE).all())
            self.assertEqual(np.load(Path(b) / "gold_refs.npy").shape, (0, 2))


if __name__ == "__main__":
    unittest.main()
