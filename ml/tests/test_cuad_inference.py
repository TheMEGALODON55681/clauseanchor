"""Resume, integrity, atomic publication and full-test completeness checks."""

from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import canonical_sha256, read_json
from run_cuad_baseline import (
    aggregate, atomic_json, bind_run, cache_tokenizer, inference_inputs, load_completed,
    make_record, output_name, process_questions, question_id, run_lock, validate_record,
)


def source():
    return {"data": [{"title": title, "paragraphs": [{"context": "full α\ncontract ending",
        "qas": [{"id": title + "__q", "question": "Where?", "answers": [{"text": "secret"}],
                 "is_impossible": False}]}]} for title in ("first", "second")]}


def result():
    return {"windows": 2, "prediction": "full", "null_score_difference": -1.0,
            "candidates": [{"text": "full", "probability": .75, "start_logit": 1.0, "end_logit": 1.0},
                           {"text": "", "probability": .25, "start_logit": 0.0, "end_logit": 0.0}]}


class CuadInferenceTests(unittest.TestCase):
    def setUp(self):
        self.inputs = inference_inputs(source())
        self.identity = {"runtime": "test-only", "source": "fixture"}
        self.run_id = canonical_sha256(self.identity)

    def test_inputs_preserve_source_order_and_context_without_gold_labels(self):
        test = source()
        before = deepcopy(test)
        inputs = inference_inputs(test)
        self.assertEqual(test, before)
        self.assertEqual([question_id(s) for s in inputs], ["first__q", "second__q"])
        for item in inputs:
            paragraph = item["data"][0]["paragraphs"][0]
            self.assertEqual(paragraph["context"], "full α\ncontract ending")
            self.assertEqual(set(paragraph["qas"][0]), {"id", "question"})

    def test_duplicate_ids_and_multiple_paragraphs_are_rejected(self):
        test = source()
        test["data"][1]["paragraphs"][0]["qas"][0]["id"] = "first__q"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            inference_inputs(test)
        test = source()
        test["data"][0]["paragraphs"] *= 2
        with self.assertRaisesRegex(ValueError, "one complete paragraph"):
            inference_inputs(test)

    def test_record_detects_corruption(self):
        record = make_record(0, self.inputs[0], self.run_id, result())
        validate_record(record, 0, self.inputs[0], self.run_id)
        record["payload"]["prediction"] = "changed"
        with self.assertRaisesRegex(ValueError, "digest"):
            validate_record(record, 0, self.inputs[0], self.run_id)

    def test_rehashed_record_cannot_move_to_another_input_or_runtime(self):
        for key, value in (("input_sha256", "wrong"), ("run_sha256", "other"),
                           ("question_index", True), ("question_id", "other__q")):
            record = make_record(0, self.inputs[0], self.run_id, result())
            record["payload"][key] = value
            record["payload_sha256"] = canonical_sha256(record["payload"])
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "different input or run"):
                validate_record(record, 0, self.inputs[0], self.run_id)

    def test_rehashed_invalid_probabilities_or_windows_fail(self):
        for change in ("probability", "windows", "fields"):
            value = result()
            if change == "probability":
                value["candidates"][0]["probability"] = .5
            elif change == "windows":
                value["windows"] = True
            else:
                value["candidates"][0]["extra"] = 0
            record = make_record(0, self.inputs[0], self.run_id, value)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_record(record, 0, self.inputs[0], self.run_id)

    def test_atomic_write_reuses_matching_files_and_preserves_differing_files(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "value.json"
            self.assertTrue(atomic_json(path, {"x": 1}))
            before = path.read_bytes()
            self.assertFalse(atomic_json(path, {"x": 1}))
            with self.assertRaisesRegex(ValueError, "preserved"):
                atomic_json(path, {"x": 2})
            self.assertEqual(path.read_bytes(), before)

    def test_interruption_before_publish_leaves_no_partial_question(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("run_cuad_baseline.os.replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    atomic_json(root / "question.json", {"data": "complete"})
            self.assertEqual(list(root.iterdir()), [])

    def test_lock_blocks_second_runner_and_releases_after_exception(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "stop"):
                with run_lock(root):
                    with self.assertRaisesRegex(ValueError, "Another process"):
                        with run_lock(root):
                            pass
                    raise RuntimeError("stop")
            with run_lock(root):
                self.assertTrue((root / "run.lock").is_file())

    def test_resume_skips_completed_questions_after_interruption(self):
        with TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            root = Path(directory)
            calls = []
            def interrupted(selected):
                calls.append(question_id(selected))
                if len(calls) == 2:
                    raise KeyboardInterrupt()
                return result()
            with run_lock(root):
                bind_run(root, self.identity)
                with self.assertRaises(KeyboardInterrupt):
                    process_questions(root, self.inputs, self.run_id, interrupted)
            self.assertEqual(list(load_completed(root, self.inputs, self.run_id)), [0])
            calls.clear()
            def resumed(selected):
                calls.append(question_id(selected))
                return result()
            with run_lock(root):
                completed, new = process_questions(root, self.inputs, self.run_id, resumed)
                self.assertEqual((len(completed), new), (2, 1))
                self.assertEqual(calls, ["second__q"])
                _, new = process_questions(root, self.inputs, self.run_id, resumed, limit=2)
                self.assertEqual(new, 0)

    def test_identity_changes_and_unbound_results_are_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            bind_run(root, self.identity)
            with self.assertRaisesRegex(ValueError, "identity differs"):
                bind_run(root, {**self.identity, "runtime": "other-device"})
            self.assertEqual(read_json(root / "run.json"), self.identity)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_json(root / "questions/000000.json", {})
            with self.assertRaisesRegex(ValueError, "without a run manifest"):
                bind_run(root, self.identity)

    def test_partial_run_cannot_publish_full_outputs(self):
        record = make_record(0, self.inputs[0], self.run_id, result())
        with self.assertRaisesRegex(ValueError, "every question"):
            aggregate(self.inputs, {0: record}, self.run_id)
        with TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            root = Path(directory)
            completed, new = process_questions(root, self.inputs, self.run_id, lambda _: result(), limit=1)
            self.assertEqual((len(completed), new), (1, 1))
            self.assertFalse((root / "manifest.json").exists())
            for invalid in (0, True, -1, 3):
                with self.assertRaisesRegex(ValueError, "limit"):
                    process_questions(root, self.inputs, self.run_id, lambda _: result(), limit=invalid)

    def test_aggregation_preserves_all_ids_and_rejects_foreign_saved_files(self):
        records = {i: make_record(i, selected, self.run_id, result()) for i, selected in enumerate(self.inputs)}
        predictions, nbest, null_odds = aggregate(self.inputs, records, self.run_id)
        self.assertEqual(set(predictions), {"first__q", "second__q"})
        self.assertEqual(set(predictions), set(nbest))
        self.assertEqual(set(predictions), set(null_odds))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_json(root / "questions/999999.json", records[0])
            with self.assertRaisesRegex(ValueError, "filename"):
                load_completed(root, self.inputs, self.run_id)

    def test_cached_tokenization_preserves_options_and_returns_independent_lists(self):
        calls = []
        def tokenize(text, **kwargs):
            calls.append((text, kwargs))
            return ["prefix" if kwargs.get("add_prefix_space") else "plain", text]
        tokenizer = SimpleNamespace(tokenize=tokenize)
        cache_tokenizer(tokenizer)
        first = tokenizer.tokenize("α", add_prefix_space=True)
        first.append("mutated")
        self.assertEqual(tokenizer.tokenize("α", add_prefix_space=True), ["prefix", "α"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(tokenizer.tokenize("α", add_prefix_space=False), ["plain", "α"])
        self.assertEqual(len(calls), 2)

    def test_run_names_cannot_escape_output_directory(self):
        self.assertEqual(output_name("cuda", None), "cuda-fp32")
        self.assertEqual(output_name("cpu", None), "cpu-fp32")
        for name in ("../other", "/absolute", "a/b", "a\\b", "a" * 49):
            with self.assertRaisesRegex(ValueError, "run name"):
                output_name("cuda", name)


if __name__ == "__main__":
    unittest.main()
