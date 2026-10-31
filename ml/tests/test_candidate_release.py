"""Package/integration-harness software tests; no selected model or CUAD data."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO/'ml'), str(REPO/'ml/scripts')]
import package_candidate_release as package
import check_candidate_release as check
from clauseanchor_core import (
    AnalysisCancelled, AnalysisResult, CategoryResult, ClauseFinding, ProgressEvent, Span, text_digest,
)


def small_tree(root):
    root.mkdir(parents=True)
    (root/'runtime.txt').write_text('test payload, not model weights', encoding='utf-8')
    manifest = {'version': package.VERSION, 'core_contract_version': '2.0',
        'artifact_manifest_sha256': package.ARTIFACT_PIN, 'final_evidence_sha256': package.FINAL_PINS,
        'candidate_only': True, 'confidence': None, 'accepted_findings_enabled': False,
        'absence_enabled': False, 'parser_app_integration_verified': False,
        'files': {'runtime.txt': package.file_spec(root/'runtime.txt')}}
    package.write_json(root/package.MANIFEST, manifest)
    return manifest, package.canonical_sha256(manifest)


def zip_tree(root, path):
    with ZipFile(path, 'w') as archive:
        for p in root.rglob('*'):
            if p.is_file(): archive.write(p, p.relative_to(root).as_posix())


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = self.root/'tree'
        self.manifest, self.digest = small_tree(self.tree)
        self.archive = self.root/'package.zip'
        zip_tree(self.tree, self.archive)

    def test_roundtrip_streamed_archive_and_tree(self):
        destination = self.root/'unpacked'; destination.mkdir()
        self.assertEqual(package.verify_zip(self.archive, self.digest, destination), self.manifest)
        self.assertEqual(package.verify_tree(destination, self.digest), self.manifest)
        self.assertEqual((destination/'runtime.txt').read_bytes(), (self.tree/'runtime.txt').read_bytes())

    def test_wrong_external_digest_rejected(self):
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            package.verify_zip(self.archive, '0'*64)

    def test_mutated_payload_rejected_before_any_extraction(self):
        (self.tree/'runtime.txt').write_text('x'*self.manifest['files']['runtime.txt']['size_bytes'])
        zip_tree(self.tree, self.archive)
        target = self.root/'unpacked'; target.mkdir()
        with self.assertRaisesRegex(ValueError, 'damaged'):
            package.verify_zip(self.archive, self.digest, target)
        self.assertEqual(list(target.iterdir()), [])

    def test_extra_archive_file_rejected(self):
        with ZipFile(self.archive, 'a') as archive: archive.writestr('extra.py', 'unexpected')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            package.verify_zip(self.archive, self.digest)

    def test_duplicate_archive_file_rejected(self):
        with self.assertWarns(UserWarning):
            with ZipFile(self.archive, 'a') as archive: archive.writestr('runtime.txt', 'duplicate')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            package.verify_zip(self.archive, self.digest)

    def test_windows_case_collision_rejected(self):
        with ZipFile(self.archive, 'a') as archive: archive.writestr('RUNTIME.TXT', 'duplicate on Windows')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            package.verify_zip(self.archive, self.digest)

    def test_unsafe_paths_rejected(self):
        for name in ['../escape', '/absolute', 'C:/drive', 'a\\windows', 'a//double', './dot', 'a/../b', 'trailing.', 'trailing ']:
            with self.subTest(name=name), self.assertRaises(ValueError): package.safe_name(name)

    def test_zip_symlink_rejected(self):
        with ZipFile(self.archive, 'w') as archive:
            archive.write(self.tree/package.MANIFEST, package.MANIFEST)
            link = ZipInfo('runtime.txt'); link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, 'x'*self.manifest['files']['runtime.txt']['size_bytes'])
        with self.assertRaisesRegex(ValueError, 'Linked'):
            package.verify_zip(self.archive, self.digest)

    def test_nonempty_extraction_directory_preserved(self):
        with self.assertRaisesRegex(ValueError, 'empty'):
            package.verify_zip(self.archive, self.digest, self.tree)
        self.assertTrue((self.tree/'runtime.txt').exists())

    def test_tree_mutation_and_extra_file_rejected(self):
        (self.tree/'unexpected.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'inventory'): package.verify_tree(self.tree, self.digest)
        (self.tree/'unexpected.txt').unlink()
        (self.tree/'runtime.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'damaged'): package.verify_tree(self.tree, self.digest)

    def test_candidate_policy_cannot_be_promoted(self):
        m = deepcopy(self.manifest); m['accepted_findings_enabled'] = True
        with self.assertRaisesRegex(ValueError, 'policy'):
            package.validate_manifest(m, package.canonical_sha256(m))


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        tree = self.root/'source'
        self.manifest, self.digest = small_tree(tree)
        self.inputs = ({'runtime.txt': tree/'runtime.txt'}, self.manifest)

    def build(self):
        with patch.object(package, 'source_inputs', return_value=self.inputs), redirect_stdout(io.StringIO()):
            return package.build(self.root)

    def test_build_publishes_verified_package_then_reuses_without_rewrite(self):
        first = self.build()
        path = self.root/package.ROOT/'package'/package.ZIP_NAME
        before = path.read_bytes()
        self.assertEqual(self.build(), first)
        self.assertEqual(path.read_bytes(), before)
        package.verify_zip(path, self.digest)

    def test_changed_source_does_not_overwrite_package(self):
        self.build()
        path = self.root/package.ROOT/'package'/package.ZIP_NAME
        before = path.read_bytes()
        self.manifest['files']['runtime.txt']['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'inputs differ'): self.build()
        self.assertEqual(path.read_bytes(), before)

    def test_failed_build_leaves_no_published_package(self):
        with patch.object(package, 'verify_zip', side_effect=ValueError('test interruption')):
            with self.assertRaisesRegex(ValueError, 'test interruption'): self.build()
        self.assertFalse((self.root/package.ROOT/'package').exists())
        self.assertFalse(list((self.root/package.ROOT).glob('.pending-*')))
        self.build()

    def test_damaged_existing_archive_is_not_rebuilt(self):
        self.build()
        path = self.root/package.ROOT/'package'/package.ZIP_NAME
        path.write_bytes(b'damaged')
        with self.assertRaisesRegex(ValueError, 'archive differs'): self.build()
        self.assertEqual(path.read_bytes(), b'damaged')

    def test_final_input_pin_rejects_changed_evidence_before_packaging(self):
        # No tensor loader, dataset or real export is touched by this unit test.
        fake = self.root/'repo'
        core = fake/'ml/clauseanchor_core'; core.mkdir(parents=True)
        (core/'__init__.py').write_text('')
        final = fake/package.FINAL; final.mkdir(parents=True)
        package.write_json(final/'identity.json', {'changed': True})
        import clauseanchor_core
        with patch.object(clauseanchor_core, '__file__', str(core/'__init__.py')), \
             patch('clauseanchor_core.artifacts.verify_bundle', return_value=(
                 {'files': {'model.safetensors': {'sha256': package.WEIGHTS_PIN}}}, {}, {})):
            with self.assertRaisesRegex(ValueError, 'final evidence differs'): package.source_inputs(fake)


class SimulatedAnalyzer:
    """Explicit harness double, never a model-quality or non-fixture inference test."""
    category_ids = ('cuad.document_name', 'cuad.governing_law', 'cuad.cap_on_liability',
                    'in.arbitration', 'in.dispute_escalation', 'in.forum_selection', 'in.seat_venue', 'in.stamping_registration')
    max_windows_per_category = None
    def __init__(self, empty=False, bad_confidence=False, ignore_limit=False, ignore_cancel=False):
        self.empty, self.bad_confidence = empty, bad_confidence
        self.ignore_limit, self.ignore_cancel = ignore_limit, ignore_cancel

    def analyze(self, text, *, doc_id, text_sha256, category_ids, context, progress=None, cancelled=None):
        def cancel():
            if cancelled and cancelled() and not self.ignore_cancel: raise AnalysisCancelled('test-double cancellation')
        cancel()
        active = [c for c in category_ids if c.startswith('cuad.') and text.strip()]
        total, done = 3*len(active), 0
        if progress: progress(ProgressEvent('inference', 0, total))
        warnings = [*context.warnings, 'experimental_candidate_only_unvalidated',
                    'bounded_candidate_generation_not_exhaustive', 'rules_and_retrieval_not_run']
        if not context.parser_complete: warnings.append('parser_incomplete')
        if context.structure_nodes: warnings.append('decorations_masked_same_source_coordinates')
        categories = []
        for name in category_ids:
            cancel()
            if name not in active:
                reason = 'unsupported_india_extension' if name.startswith('in.') else 'no_analyzable_text'
                categories.append(CategoryResult(name, 'unavailable', None, reason, False, 0, 0, 0))
                continue
            limit = 3 if self.max_windows_per_category is None or self.ignore_limit else min(3, self.max_windows_per_category)
            for _ in range(limit):
                done += 1
                if progress: progress(ProgressEvent('inference', done, total))
                cancel()
            truncated = name == 'cuad.cap_on_liability'
            if truncated: warnings.append('question_truncated_first64:'+name)
            if limit < 3: warnings.append('window_limit:'+name)
            clauses = []
            if limit and not self.empty:
                start = text.index('This Agreement'); end = start+14
                clauses = [ClauseFinding('test-'+name, name, Span(doc_id, text_sha256, start, end, text[start:end]),
                    'review_candidate', 0.8 if self.bad_confidence else None, 'unvalidated', 'unvalidated', 'model')]
            complete = context.parser_complete and not truncated and limit == 3
            reason = 'unvalidated_model' if complete else 'processing_incomplete_unvalidated'
            if limit == 0: reason = 'window_limit_not_processed'
            categories.append(CategoryResult(name, 'abstained' if limit else 'unavailable', None, reason,
                                             complete, limit, 3, len(clauses), clauses))
        return AnalysisResult('2.0', doc_id, text_sha256, package.ARTIFACT_PIN, 'real', categories, warnings)


class BehaviorHarnessTests(unittest.TestCase):
    def exercise(self, analyzer):
        with redirect_stdout(io.StringIO()): return check.exercise(analyzer)

    def test_complete_partial_unsupported_work_limits_and_cancellation(self):
        a = SimulatedAnalyzer()
        output = self.exercise(a)
        self.assertGreater(output['exact_source_slices_checked'], 0)
        self.assertEqual(set(output['cases']), {'full', 'simulated_parser_partial', 'window_limited', 'not_processed', 'empty_source'})
        self.assertTrue(output['cancellation']['after_first_window']['raised_AnalysisCancelled'])
        self.assertIsNone(a.max_windows_per_category)

    def test_zero_candidates_never_asserts_absence_or_fabricates_slice_pass(self):
        output = self.exercise(SimulatedAnalyzer(empty=True))
        self.assertEqual(output['exact_source_slices_checked'], 0)
        self.assertGreater(output['zero_processed_candidate_sets'], 0)
        self.assertTrue(all(c['status'] in ('abstained', 'unavailable')
            for case in output['cases'].values() for c in case['result']['categories']))

    def test_non_null_confidence_rejected(self):
        with self.assertRaises(ValueError): self.exercise(SimulatedAnalyzer(bad_confidence=True))

    def test_hidden_work_limit_completion_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Work limit'): self.exercise(SimulatedAnalyzer(ignore_limit=True))

    def test_swallowed_cancellation_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Cancellation returned'): self.exercise(SimulatedAnalyzer(ignore_cancel=True))

    def test_cached_check_binds_report_to_release_and_detects_damage(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            report = {'release_manifest_sha256': 'a'*64, 'device': 'cpu', 'status': 'passed'}
            package.write_json(root/'report.json', report)
            package.write_json(root/'manifest.json', {'release_manifest_sha256': 'a'*64, 'report': package.file_spec(root/'report.json')})
            self.assertEqual(check.cached_check(root, 'a'*64), report)
            with self.assertRaises(ValueError): check.cached_check(root, 'b'*64)
            (root/'report.json').write_text('{}')
            with self.assertRaises(ValueError): check.cached_check(root, 'a'*64)


class IsolatedRuntimeTests(unittest.TestCase):
    def test_extracted_tiny_random_model_in_fresh_isolated_process(self):
        # Existing adapter helper creates clearly labelled random test weights.
        # Production pins/files are NEVER edited; replacements live only in temp.
        from test_candidate_analyzer import test_bundle
        from clauseanchor_core.artifacts import CODE_FILES
        with TemporaryDirectory() as t:
            root = Path(t); bundle = root/'bundle'; bundle.mkdir()
            artifact = bundle/package.ARTIFACT
            artifact_manifest = test_bundle(artifact)
            self.assertTrue(package.read_json(artifact/'provenance.json')['test_only_random_weights'])
            test_pin = package.canonical_sha256(artifact_manifest)
            core = bundle/'ml/clauseanchor_core'; core.mkdir(parents=True)
            for name in CODE_FILES: shutil.copyfile(REPO/'ml/clauseanchor_core'/name, core/name)
            scripts = bundle/'ml/scripts'; scripts.mkdir()
            for name in ('package_candidate_release.py', 'check_candidate_release.py'):
                source = (REPO/'ml/scripts'/name).read_text(encoding='utf-8')
                (scripts/name).write_text(source.replace(package.ARTIFACT_PIN, test_pin), encoding='utf-8')
            manifest = {'version': package.VERSION, 'core_contract_version': '2.0',
                'artifact_manifest_sha256': test_pin, 'final_evidence_sha256': package.FINAL_PINS,
                'candidate_only': True, 'confidence': None, 'accepted_findings_enabled': False,
                'absence_enabled': False, 'parser_app_integration_verified': False,
                'files': {p.relative_to(bundle).as_posix(): package.file_spec(p) for p in bundle.rglob('*') if p.is_file()}}
            package.write_json(bundle/package.MANIFEST, manifest)
            digest = package.canonical_sha256(manifest)
            output = root/'cpu_check'
            env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                       OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
            command = [sys.executable, '-I', '-B', str(scripts/'check_candidate_release.py'),
                '--bundle-root', str(bundle), '--expected-release-sha256', digest, '--output', str(output)]
            proc = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stdout+'\n'+proc.stderr)
            report = package.read_json(output/'report.json')
            self.assertEqual(report['status'], 'passed')
            self.assertTrue(report['core_imported_from_extracted_bundle'])
            self.assertFalse(report['live_parser_tested'])
            self.assertGreater(report['checks']['exact_source_slices_checked'], 0)
            # The child also proves this is not an import from the editable repo.
            self.assertFalse(any(bundle.rglob('*.pyc')))


if __name__ == '__main__':
    unittest.main()
