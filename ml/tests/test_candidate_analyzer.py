"""Software tests only: tiny random QA weights and explicit test logits.

No selected-checkpoint quality claim. The separate smoke CLI requires the
actual exported checkpoint-000022 on Tanishq's machine.
"""

import ast
from contextlib import redirect_stdout
import io
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch
from safetensors.torch import save_file
from transformers import RobertaConfig, RobertaForQuestionAnswering

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ml"))
sys.path.insert(0, str(REPO / "ml/scripts"))
from clauseanchor_core import (
    AnalysisCancelled, AnalysisContext, CandidateOnlyAnalyzer, StructureNode,
    context_from_parsed_document, from_dict, text_digest, to_dict, validate_result,
)
from clauseanchor_core.artifacts import (
    CHECKPOINT, CODE_FILES, DECODER, FILES, PACKAGES, TOKENIZER_FILES,
    canonical_sha256, code_hashes, file_spec, read_json, verify_bundle, write_json,
)
from clauseanchor_core._inference import FeatureTokenizer, disjoint_candidates, window_candidates
from prepare_cuad_features import FeatureTokenizer as ReferenceTokenizer
from cuad_development import window_candidates as reference_window_candidates
from validate_cuad_decoder import selections


class ScriptedLogits:
    """Clearly a test double; receives real tokenizer encodings, not fixtures."""
    def __init__(self, spans=(), boundary=False):
        self.spans, self.boundary, self.calls = spans, boundary, 0

    def predict(self, rows):
        starts = np.full((len(rows), 512), -100., dtype=np.float32)
        ends = starts.copy()
        starts[:, 0] = ends[:, 0] = 0
        for j, row in enumerate(rows):
            positions = [i for i, s in enumerate(row.sequence_ids) if s == 1 and row.offsets[i][0] < row.offsets[i][1]]
            for a, b in self.spans:
                left = [i for i in positions if row.offsets[i][0] == a]
                right = [i for i in positions if row.offsets[i][1] == b]
                if left and right:
                    starts[j, left[0]], ends[j, right[-1]] = 5, 5
            if self.boundary and self.calls == 0 and j == 0:
                starts[j, positions[-1]] = ends[j, positions[-1]] = 20
        self.calls += 1
        return starts, ends


def test_bundle(root):
    assets = REPO / "models/cuad_clean_backbone/roberta-base"
    if not all((assets / n).is_file() for n in TOKENIZER_FILES):
        raise RuntimeError("Pinned tokenizer files are required. Use existing clean backbone assets; do not retrain.")
    (root / "tokenizer").mkdir(parents=True)
    for name in TOKENIZER_FILES:
        shutil.copyfile(assets / name, root / "tokenizer" / name)
    # Random tiny architecture is exclusively a test fixture, never exported by
    # export_candidate_analyzer.py or used by the non-fixture smoke command.
    config = RobertaConfig(vocab_size=50265, hidden_size=16, intermediate_size=24,
                          num_hidden_layers=1, num_attention_heads=2, num_labels=2,
                          max_position_embeddings=514, pad_token_id=1, bos_token_id=0, eos_token_id=2)
    with torch.random.fork_rng():
        torch.manual_seed(91)
        model = RobertaForQuestionAnswering(config)
    save_file(model.state_dict(), str(root / "model.safetensors"))
    config.to_json_file(str(root / "config.json"), use_diff=False)
    for name in ("catalogue.json", "category_questions.json"):
        shutil.copyfile(REPO / "ml/configs" / name, root / name)
    shutil.copyfile(REPO / "ml/configs/cuad_training_source.json", root / "training_source.json")
    shutil.copyfile(REPO / "ml/requirements-inference.txt", root / "requirements-inference.txt")
    write_json(root / "decoder.json", DECODER)
    write_json(root / "provenance.json", {"selected_checkpoint": CHECKPOINT, "test_only_random_weights": True})
    manifest = {"format": "clauseanchor-candidate-only-v0", "contract_version": "2.0", "checkpoint": CHECKPOINT,
                "files": {n: file_spec(root / n) for n in sorted(FILES)}, "code_sha256_lf": code_hashes(),
                "required_packages": PACKAGES}
    write_json(root / "manifest.json", manifest)
    return manifest


class CandidateAnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "artifact"
        cls.manifest = test_bundle(cls.root)
        cls.digest = canonical_sha256(cls.manifest)
        cls.analyzer = CandidateOnlyAnalyzer(cls.root, expected_manifest_sha256=cls.digest)
        cls.real_backend = cls.analyzer._backend

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.a = self.analyzer
        self.a._backend = ScriptedLogits()
        self.a.max_windows_per_category = None
        self.a.batch_size = 1
        self.source = "😊 café ₹500 e\u0301\r\nCedar signs.\r\nCedar signs.\r\n"

    def call(self, **changes):
        args = dict(document_text=self.source, doc_id="unit-test", text_sha256=text_digest(self.source),
                    category_ids=("cuad.governing_law",), context=AnalysisContext())
        args.update(changes)
        result = self.a.analyze(**args)
        validate_result(result, args["document_text"])
        self.assertEqual(from_dict(to_dict(result)), result)
        return result

    def test_actual_tiny_torch_forward_runs_without_fixture_replay(self):
        self.a._backend = self.real_backend
        result = self.call()
        self.assertEqual(result.mode, "real")
        self.assertEqual(result.categories[0].windows_done, 1)
        self.assertEqual(result.categories[0].status, "abstained")

    def test_null_confidence_multiple_occurrences_unicode_crlf(self):
        first = len("😊 café ₹500 e\u0301\r\n")
        second = first + len("Cedar signs.\r\n")
        self.a._backend = ScriptedLogits(((first, first + 5), (second, second + 5)))
        result = self.call()
        cat = result.categories[0]
        self.assertEqual([f.span.start for f in cat.clauses], [first, second])
        self.assertEqual(cat.unresolved_count, 2)
        self.assertTrue(cat.search_complete)
        for f in cat.clauses:
            self.assertEqual(f.span.text, "Cedar")
            self.assertEqual(f.status, "review_candidate")
            self.assertIsNone(f.confidence)
            self.assertEqual(f.calibration_scope, "unvalidated")
            self.assertEqual(f.confidence_band, "unvalidated")
            self.assertEqual(f.origin, "model")
            self.assertEqual((f.rule_flags, f.passages, f.retrieval_status), ([], [], "not_run"))
        self.assertEqual(len({f.id for f in cat.clauses}), 2)

    def test_zero_candidates_is_abstained_never_absent(self):
        c = self.call().categories[0]
        self.assertEqual((c.status, c.reason_code, c.unresolved_count), ("abstained", "unvalidated_model", 0))
        self.assertTrue(c.search_complete)
        self.assertIsNone(c.decision_confidence)

    def test_all_five_india_categories_unavailable_no_inference(self):
        ids = tuple(c for c in self.a.category_ids if c.startswith("in."))
        result = self.call(category_ids=ids)
        self.assertEqual(len(ids), 5)
        self.assertEqual(self.a._backend.calls, 0)
        self.assertTrue(all(c.status == "unavailable" and c.reason_code == "unsupported_india_extension"
                            and not c.search_complete and c.windows_total == 0 for c in result.categories))

    def test_parser_partial_keeps_candidates_but_not_completeness(self):
        first = len("😊 café ₹500 e\u0301\r\n")
        self.a._backend = ScriptedLogits(((first, first + 5),))
        result = self.call(context=AnalysisContext(parser_complete=False, warnings=["PARTIALLY_SCANNED_PDF"]))
        c = result.categories[0]
        self.assertFalse(c.search_complete)
        self.assertEqual(c.windows_done, c.windows_total)
        self.assertEqual(c.status, "abstained")
        self.assertEqual(c.unresolved_count, 1)
        self.assertIn("PARTIALLY_SCANNED_PDF", result.warnings)

    def test_informational_parser_warning_preserved_without_false_omission(self):
        result = self.call(context=AnalysisContext(warnings=["TEXT_BOX_CONTENT"]))
        self.assertTrue(result.categories[0].search_complete)
        self.assertIn("TEXT_BOX_CONTENT", result.warnings)

    def test_work_limit_retains_full_denominator_and_completed_candidates(self):
        self.source = "Cedar signs a monthly services agreement.\n" * 200
        self.a._backend = ScriptedLogits(((0, 5),))
        self.a.max_windows_per_category = 1
        c = self.call().categories[0]
        self.assertEqual(c.windows_done, 1)
        self.assertGreater(c.windows_total, 1)
        self.assertFalse(c.search_complete)
        self.assertEqual(c.status, "abstained")
        self.assertEqual(c.unresolved_count, 1)

    def test_zero_work_limit_unavailable(self):
        self.a.max_windows_per_category = 0
        c = self.call().categories[0]
        self.assertEqual((c.status, c.windows_done, c.windows_total), ("unavailable", 0, 1))
        self.assertFalse(c.search_complete)
        self.assertEqual(self.a._backend.calls, 0)

    def test_boundary_candidate_is_retained_with_incomplete_flag(self):
        self.source = "Monthly services and reports are due.\n" * 200
        self.a._backend = ScriptedLogits(boundary=True)
        result = self.call()
        self.assertTrue(result.categories[0].clauses)
        self.assertFalse(result.categories[0].search_complete)
        self.assertIn("boundary_review:cuad.governing_law", result.warnings)

    def test_question_truncation_is_visible(self):
        result = self.call(category_ids=("cuad.exclusivity",))
        self.assertIn("question_truncated_first64:cuad.exclusivity", result.warnings)
        self.assertFalse(result.categories[0].search_complete)

    def test_progress_is_global_monotone_and_matches_work(self):
        self.source = "Monthly services and reports are due.\n" * 100
        events = []
        result = self.call(category_ids=("in.arbitration", "cuad.governing_law", "cuad.document_name"), progress=events.append)
        total = sum(c.windows_total for c in result.categories)
        self.assertEqual([e.completed_units for e in events], list(range(total + 1)))
        self.assertTrue(all(e.total_units == total for e in events))

    def test_cancellation_before_tokenization_and_after_first_batch(self):
        with self.assertRaises(AnalysisCancelled):
            self.call(cancelled=lambda: True)
        self.assertEqual(self.a._backend.calls, 0)
        self.source = "Monthly services and reports are due.\n" * 100
        with self.assertRaises(AnalysisCancelled):
            self.call(cancelled=lambda: self.a._backend.calls > 0)
        self.assertEqual(self.a._backend.calls, 1)
        # The lock is released after cancellation.
        self.call()

    def test_bad_hash_unknown_duplicate_and_invalid_node_rejected(self):
        for changes in ({"text_sha256": "0" * 64}, {"category_ids": ("unknown",)},
                        {"category_ids": ("cuad.parties", "cuad.parties")},
                        {"context": AnalysisContext(structure_nodes=[StructureNode("x", None, "decoration", -1, 2)])}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.call(**changes)

    def test_empty_text_unavailable(self):
        self.source = " \r\n\t"
        c = self.call().categories[0]
        self.assertEqual((c.status, c.reason_code), ("unavailable", "no_analyzable_text"))

    def test_model_failure_does_not_return_success_and_lock_releases(self):
        with patch.object(self.a._backend, "predict", side_effect=RuntimeError("test model failure")):
            with self.assertRaisesRegex(RuntimeError, "test model failure"):
                self.call()
        self.call()

    def test_nonfinite_logits_fail_closed(self):
        bad = np.zeros((1, 512), dtype=np.float32)
        bad[0, 5] = np.nan
        with patch.object(self.a._backend, "predict", return_value=(bad, bad)):
            with self.assertRaisesRegex(ValueError, "Invalid decoder logits"):
                self.call()

    def test_parser_bridge_preserves_ranges_and_masks_decoration(self):
        self.source = "HEADER 😊\r\nCedar signs."
        parsed = SimpleNamespace(source_text=self.source, text_sha256=text_digest(self.source), nodes=(),
            decorations=((0, 8),), coverage=SimpleNamespace(partial=False),
            warnings=(SimpleNamespace(code="TEXT_BOX_CONTENT"),))
        context = context_from_parsed_document(parsed)
        self.assertEqual(context.structure_nodes, [StructureNode("clauseanchor.decoration.0", None, "decoration", 0, 8)])
        start = len("HEADER 😊\r\n")
        self.a._backend = ScriptedLogits(((start, start + 5),))
        result = self.call(context=context)
        self.assertEqual(result.categories[0].clauses[0].span.start, start)
        self.assertEqual(parsed.source_text, self.source)
        self.assertIn("decorations_masked_same_source_coordinates", result.warnings)

    def test_decoration_crossing_span_not_silently_rewritten(self):
        self.source = "Cedar\nHEADER\nservices"
        context = AnalysisContext(structure_nodes=[StructureNode("d", None, "decoration", 6, 12)])
        self.a._backend = ScriptedLogits(((0, len(self.source)),))
        result = self.call(context=context)
        c = result.categories[0]
        self.assertFalse(c.clauses)
        self.assertFalse(c.search_complete)
        self.assertIn("decoration_crossing_candidate_omitted:cuad.governing_law", result.warnings)

    def test_busy_instance_rejects_instead_of_uncancellable_queue(self):
        self.a._lock.acquire()
        try:
            with self.assertRaisesRegex(RuntimeError, "busy"):
                self.call()
        finally:
            self.a._lock.release()

    def test_manifest_and_every_payload_hash_checked_before_loading(self):
        with self.assertRaisesRegex(ValueError, "Manifest digest"):
            CandidateOnlyAnalyzer(self.root, expected_manifest_sha256="0" * 64)
        for name in ("model.safetensors", "config.json", "tokenizer/tokenizer.json", "category_questions.json"):
            path = self.root / name
            original = path.read_bytes()
            try:
                path.write_bytes(original + b" ")
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "hash/size"):
                    verify_bundle(self.root, self.digest)
            finally:
                path.write_bytes(original)

    def test_extra_tokenizer_override_and_unsupported_decoder_rejected(self):
        override = self.root / "tokenizer/added_tokens.json"
        override.write_text("{}")
        try:
            with self.assertRaisesRegex(ValueError, "Extra/missing"):
                verify_bundle(self.root, self.digest)
        finally:
            override.unlink()
        original = (self.root / "decoder.json").read_bytes()
        try:
            write_json(self.root / "decoder.json", {**DECODER, "margin_strictly_greater_than": 15.65})
            changed = deepcopy(self.manifest)
            changed["files"]["decoder.json"] = file_spec(self.root / "decoder.json")
            write_json(self.root / "manifest.json", changed)
            with self.assertRaisesRegex(ValueError, "Decoder settings"):
                verify_bundle(self.root, canonical_sha256(changed))
        finally:
            (self.root / "decoder.json").write_bytes(original)
            write_json(self.root / "manifest.json", self.manifest)

    def test_installed_code_change_rejected_even_with_valid_manifest_hash(self):
        changed = deepcopy(self.manifest)
        changed["code_sha256_lf"]["analyzer.py"] = "0" * 64
        try:
            write_json(self.root / "manifest.json", changed)
            with self.assertRaisesRegex(ValueError, "Installed inference code"):
                verify_bundle(self.root, canonical_sha256(changed))
        finally:
            write_json(self.root / "manifest.json", self.manifest)


class FrozenParityTests(unittest.TestCase):
    def test_copied_functions_ast_identical_to_frozen_producers(self):
        def nodes(path):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text()).body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        actual = nodes(REPO / "ml/clauseanchor_core/_inference.py")
        for path, names in (("prepare_cuad_features.py", ("FeatureTokenizer", "window_count")),
                            ("cuad_development.py", ("window_candidates",)),
                            ("validate_cuad_decoder.py", ("exact_candidates",))):
            reference = nodes(REPO / "ml/scripts" / path)
            for name in names:
                self.assertEqual(actual[name], reference[name], name)

    def test_actual_tokenizer_unicode_overflow_and_long_question_parity(self):
        path = REPO / "models/cuad_clean_backbone/roberta-base"
        actual, reference = FeatureTokenizer(path), ReferenceTokenizer(path)
        context = "😊 café e\u0301 ₹500.\r\nCedar services are due.\n" * 160
        question = "Which terms govern? " * 50
        raw, offsets = actual.context(context)
        other_raw, other_offsets = reference.context(context)
        self.assertEqual((raw.ids, offsets), (other_raw.ids, other_offsets))
        rows = list(actual.windows(raw, offsets, question))
        other = list(reference.windows(other_raw, other_offsets, question))
        self.assertGreater(len(rows), 1)
        self.assertEqual(len(rows), len(other))
        for (start, enc, positions), (os, oe, op) in zip(rows, other):
            self.assertEqual((start, enc.ids, enc.offsets, enc.sequence_ids, enc.attention_mask, positions),
                             (os, oe.ids, oe.offsets, oe.sequence_ids, oe.attention_mask, op))

    def test_random_logits_generation_and_disjoint_selection_parity(self):
        rng = np.random.default_rng(42)
        source = "abcdefghij" * 100
        raw = []
        for row in range(8):
            starts, ends = rng.normal(size=(2, 512)).astype(np.float32)
            seq = np.array([-1] * 12 + [1] * 480 + [-1] * 20)
            offsets = np.zeros((512, 2), dtype=int)
            offsets[12:492] = np.array([(row * 30 + i, row * 30 + i + 1) for i in range(480)])
            args = (starts, ends, seq, offsets, source, row, row > 0, row < 7)
            actual = window_candidates(*args)
            self.assertEqual(actual, reference_window_candidates(*args))
            raw.extend(actual)
        self.assertEqual(disjoint_candidates(raw), selections(raw)[0]["disjoint_full"])

    def test_ties_duplicates_complete_counterpart_and_touching_ranges(self):
        def c(a, b, score, boundary=False, row=0):
            return {"start": a, "end": b, "margin": score, "boundary_review": boundary, "window_row": row}
        raw = [c(0, 5, 10, True), c(0, 5, 9), c(5, 10, 10), c(0, 10, 10), c(20, 22, 0), c(30, 35, -1)]
        result = disjoint_candidates(raw)
        self.assertEqual(result, selections(raw)[0]["disjoint_full"])
        self.assertEqual([(c["start"], c["end"]) for c in result], [(0, 10)])


class ExporterTests(unittest.TestCase):
    def setUp(self):
        from cuad_development import POLICY
        from export_candidate_analyzer import PRODUCER_PINS
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "ml/scripts").mkdir(parents=True)
        (self.repo / "ml/configs").mkdir()
        for name in PRODUCER_PINS:
            shutil.copyfile(REPO / "ml/scripts" / name, self.repo / "ml/scripts" / name)
        for name in ("catalogue.json", "category_questions.json", "cuad_training_source.json"):
            shutil.copyfile(REPO / "ml/configs" / name, self.repo / "ml/configs" / name)
        shutil.copyfile(REPO / "ml/requirements-inference.txt", self.repo / "ml/requirements-inference.txt")
        assets = self.repo / "models/cuad_clean_backbone/roberta-base"
        assets.mkdir(parents=True)
        for name in TOKENIZER_FILES:
            shutil.copyfile(REPO / "models/cuad_clean_backbone/roberta-base" / name, assets / name)
        config = RobertaConfig(vocab_size=50265, hidden_size=16, intermediate_size=24,
                              num_hidden_layers=1, num_attention_heads=2, num_labels=2,
                              max_position_embeddings=514)
        self.model = RobertaForQuestionAnswering(config)
        self.training = self.repo / "data/processed/cuad/clean_training_v1"
        self.checkpoint = self.training / "checkpoints" / CHECKPOINT
        self.checkpoint.mkdir(parents=True)
        identity = {"epoch_sizes": [16, 16, 16], "decoder_policy": POLICY,
                    "source_config_sha256": canonical_sha256(read_json(self.repo / "ml/configs/cuad_training_source.json")),
                    "code_sha256": {"cuad_development.py": PRODUCER_PINS["cuad_development.py"]}}
        run_sha = canonical_sha256(identity)
        progress = {"epoch": 3, "offset": 0, "global_step": 3, "examples_seen": 48,
                    "bad_evaluations": 0, "completed": True, "epoch_loss_sum": 0.,
                    "history": [{"macro_f1": .1}, {"macro_f1": .2}, {"macro_f1": .3}],
                    "best_score": .3, "best_checkpoint": CHECKPOINT}
        write_json(self.training / "identity.json", identity)
        write_json(self.checkpoint / "progress.json", progress)
        write_json(self.checkpoint / "evaluation.json", {"selection_eligible": True, "test_only": True})
        torch.save({"run_sha256": run_sha, "execution_sha256": run_sha, "progress": progress,
                    "model": self.model.state_dict(), "optimizer": {}, "test_only": True}, self.checkpoint / "training.pt")
        self.manifest = {"checkpoint": CHECKPOINT, "run_sha256": run_sha, "execution_sha256": run_sha,
                         "files": {n: file_spec(self.checkpoint / n) for n in ("training.pt", "progress.json", "evaluation.json")}}
        self.publish_manifest()
        from review_cuad_decoder import load_checkpoint_reports
        _, _, binding = load_checkpoint_reports(self.training)
        validation = {"checkpoint": binding, "test_only": True}
        validation_dir = self.repo / "data/processed/cuad/decoder_validation_v1"
        validation_dir.mkdir()
        write_json(validation_dir / "identity.json", validation)
        self.validation_pin = canonical_sha256(validation)

    def publish_manifest(self):
        write_json(self.checkpoint / "manifest.json", self.manifest)
        write_json(self.training / "latest.json", {"checkpoint": CHECKPOINT,
            "run_sha256": self.manifest["run_sha256"], "manifest_sha256": canonical_sha256(self.manifest)})

    def export(self):
        from export_candidate_analyzer import export
        # Only substitute the large architecture instantiation and Git's ignore
        # check. Completed-state / checkpoint file verification stays real.
        with patch("prepare_cuad_baseline.verify_ignored_assets"), \
             patch("export_candidate_analyzer.VALIDATION_IDENTITY_PIN", self.validation_pin), \
             patch("validate_cuad_decoder.load_model", return_value=self.model) as loader, \
             redirect_stdout(io.StringIO()):
            result = export(self.repo)
        return result, loader.call_count

    def test_export_inventory_hashes_loading_and_idempotence(self):
        receipt, calls = self.export()
        self.assertEqual(calls, 1)
        root = self.repo / receipt["artifact_directory"]
        manifest, _, _ = verify_bundle(root, receipt["manifest_canonical_sha256"])
        self.assertEqual(set(manifest["files"]), FILES)
        self.assertFalse((root / "training.pt").exists())
        analyzer = CandidateOnlyAnalyzer(root, expected_manifest_sha256=receipt["manifest_canonical_sha256"])
        for name, tensor in analyzer._backend.model.state_dict().items():
            self.assertTrue(torch.equal(tensor, self.model.state_dict()[name]), name)
        second, calls = self.export()
        self.assertEqual(receipt, second)
        self.assertEqual(calls, 0)

    def test_checkpoint_corruption_rejected_before_export(self):
        with (self.checkpoint / "training.pt").open("ab") as f:
            f.write(b"changed")
        with self.assertRaises(ValueError):
            self.export()
        self.assertFalse((self.repo / "models/clauseanchor_candidate_v0").exists())

    def test_unbound_checkpoint_metadata_rejected(self):
        self.validation_pin = "0" * 64
        with self.assertRaisesRegex(ValueError, "previously verified"):
            self.export()

    def test_rewritten_manifest_cannot_bypass_saved_receipt(self):
        receipt, _ = self.export()
        root = self.repo / receipt["artifact_directory"]
        manifest = read_json(root / "manifest.json")
        manifest["untrusted_change"] = True
        write_json(root / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "Manifest digest mismatch"):
            self.export()

    def test_smoke_harness_does_not_pass_vacuous_zero_candidate_slices(self):
        from smoke_candidate_analyzer import run
        with torch.no_grad():
            self.model.qa_outputs.weight.zero_()
            self.model.qa_outputs.bias.zero_()
        receipt, _ = self.export()
        fixtures = self.repo / "ml/fixtures"
        fixtures.mkdir()
        shutil.copyfile(REPO / "ml/fixtures/sample_contract.txt", fixtures / "sample_contract.txt")
        report_path = self.repo / "software-smoke-test.json"
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "zero candidates"):
            run(self.repo, self.repo / receipt["artifact_directory"], receipt["manifest_canonical_sha256"],
                "cpu", 1, report_path)
        report = read_json(report_path)
        self.assertEqual(report["status"], "incomplete_no_candidate_slices")
        self.assertEqual(report["exact_source_slices_checked"], 0)
        self.assertTrue(report["cancellation_checked"])

    def test_different_completed_checkpoint_rejected_without_model_load(self):
        other = "checkpoint-000021"
        progress = read_json(self.checkpoint / "progress.json")
        progress["best_checkpoint"] = other
        write_json(self.checkpoint / "progress.json", progress)
        self.manifest["files"]["progress.json"] = file_spec(self.checkpoint / "progress.json")
        self.manifest["checkpoint"] = other
        write_json(self.checkpoint / "manifest.json", self.manifest)
        self.checkpoint.rename(self.checkpoint.parent / other)
        write_json(self.training / "latest.json", {"checkpoint": other,
            "run_sha256": self.manifest["run_sha256"], "manifest_sha256": canonical_sha256(self.manifest)})
        with self.assertRaisesRegex(ValueError, "not checkpoint-000022"):
            self.export()


if __name__ == "__main__":
    unittest.main()
