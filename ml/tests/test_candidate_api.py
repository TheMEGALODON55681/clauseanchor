"""Software checks with tiny RANDOM test weights, never checkpoint quality evidence.

The positive path uses the actual app, DOCX parser subprocess and CPU analyzer.
Only report-persistence tests replace inference; no backend source is modified.
"""
from copy import deepcopy
import hashlib
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO/'ml/scripts'), str(REPO/'ml/tests')]
import smoke_candidate_api as smoke
from test_candidate_analyzer import test_bundle
from clauseanchor_core.artifacts import canonical_sha256, read_json, write_json


class ActualAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.artifact = Path(cls.temp.name)/'tiny-random-test-model'
        cls.digest = canonical_sha256(test_bundle(cls.artifact))
        cls.journal = {}
        smoke.run_probe(REPO, cls.artifact, cls.digest, cls.journal)

    def setUp(self):
        self.item = deepcopy(self.journal['documents']['complete'])

    def check(self, item=None):
        item = item or self.item
        return smoke.check_analysis(item['document']['parsed'],item['document']['id'],
            item['analysis_request']['category_ids'],item['analysis'],item['analysis_progress'][-1],self.digest)

    def first_clause(self):
        return next(f for c in self.item['analysis']['categories'] for f in c['clauses'])

    def test_actual_cpu_parser_api_path_and_cancel(self):
        self.assertTrue(self.journal['actual_cpu_analyzer_loaded'])
        self.assertGreater(self.journal['candidate_slices_checked'], 0)
        self.assertEqual(self.journal['cancellation']['analysis']['status'], 'cancelled')
        self.assertEqual(self.journal['session_cleanup'], {'delete_status':204,'old_token_status':401})
        self.check()
        self.check(deepcopy(self.journal['documents']['partial']))

    def test_no_session_token_in_saved_journal(self):
        def keys(value):
            if isinstance(value, dict):
                for k,v in value.items():
                    yield k
                    yield from keys(v)
            elif isinstance(value, list):
                for v in value: yield from keys(v)
        self.assertFalse({'token','Authorization','headers'} & set(keys(self.journal)))

    def test_changed_source_rejected(self):
        self.item['document']['parsed']['source_text'] += 'altered'
        with self.assertRaises(ValueError): self.check()

    def test_off_by_one_api_offsets_rejected(self):
        self.first_clause()['span']['start'] += 1
        with self.assertRaises(ValueError): self.check()

    def test_fixture_replay_origin_rejected(self):
        self.first_clause()['origin'] = 'fixture'
        with self.assertRaises(ValueError): self.check()

    def test_accepted_null_confidence_rejected(self):
        self.first_clause()['status'] = 'accepted'
        with self.assertRaises(ValueError): self.check()

    def test_invented_confidence_rejected(self):
        self.first_clause()['confidence'] = .99
        with self.assertRaises(ValueError): self.check()

    def test_fake_resolved_decision_rejected(self):
        self.item['analysis']['decision_coverage']['resolved'] = 1
        with self.assertRaises(ValueError): self.check()

    def test_wrong_loaded_artifact_rejected(self):
        self.item['analysis']['artifact_manifest_sha256'] = '0'*64
        with self.assertRaises(ValueError): self.check()

    def test_partial_document_cannot_be_complete(self):
        self.item = deepcopy(self.journal['documents']['partial'])
        self.item['analysis']['processing_complete'] = True
        with self.assertRaises(ValueError): self.check()

    def test_lost_parser_warning_rejected(self):
        self.item = deepcopy(self.journal['documents']['partial'])
        self.item['analysis']['warnings'].remove('UNSUPPORTED_DOCX_FEATURE')
        with self.assertRaises(ValueError): self.check()

    def test_zero_candidates_never_becomes_absence(self):
        # Validator accepts an honest empty abstention, but refuses absent.
        for c in self.item['analysis']['categories']:
            c['clauses'] = []; c['unresolved_count'] = 0
        self.check()
        self.item['analysis']['categories'][0]['status'] = 'absent'
        with self.assertRaises(ValueError): self.check()

    def test_dropped_requested_category_rejected(self):
        self.item['analysis']['categories'].pop()
        with self.assertRaises(ValueError): self.check()


class EvidenceTests(unittest.TestCase):
    def test_authored_docx_is_repeatable_and_partial_case_differs(self):
        a = smoke.authored_docx()
        self.assertEqual(a, smoke.authored_docx())
        self.assertNotEqual(hashlib.sha256(a).digest(),hashlib.sha256(smoke.authored_docx(True)).digest())

    def test_progress_rejects_regression_denominator_change_and_overrun(self):
        point = lambda done,total: {'completed_units':done,'total_units':total}
        smoke.check_progress([point(0,None),point(0,4),point(1,4),point(4,4)])
        for snapshots in ([point(2,4),point(1,4)], [point(1,4),point(2,5)], [point(5,4)]):
            with self.subTest(snapshots=snapshots), self.assertRaises(ValueError):
                smoke.check_progress(snapshots)

    def test_backend_pin_ignores_only_windows_line_endings(self):
        self.assertEqual(canonical_sha256(smoke.backend_hashes(REPO)),smoke.BACKEND_PIN)
        with TemporaryDirectory() as temp:
            root = Path(temp); (root/'backend/app').mkdir(parents=True)
            for name in ('app/main.py','requirements.txt','constraints.txt'):
                (root/'backend'/name).write_bytes(b'a\nb\n')
            baseline = smoke.backend_hashes(root)
            (root/'backend/app/main.py').write_bytes(b'a\r\nb\r\n')
            self.assertEqual(baseline,smoke.backend_hashes(root))
            (root/'backend/app/main.py').write_bytes(b'a\r\nchanged\r\n')
            self.assertNotEqual(baseline,smoke.backend_hashes(root))

    def test_failed_run_is_preserved_without_claiming_inference(self):
        with TemporaryDirectory() as temp, patch.object(smoke,'preflight',return_value={'test_only':True}), \
                patch.object(smoke,'run_probe',side_effect=ValueError('test startup failure')) as probe, redirect_stdout(io.StringIO()):
            root = Path(temp)
            with self.assertRaisesRegex(ValueError,'test startup failure'): smoke.run(root)
            report = read_json(root/smoke.ROOT/'results/report.json')
            self.assertEqual(report['status'],'incomplete_or_failed')
            self.assertFalse(report['selected_checkpoint_cpu_inference'])
            with self.assertRaisesRegex(ValueError,'preserved'): smoke.run(root)
            self.assertEqual(probe.call_count,1)

    def test_cached_pass_checks_bytes_and_does_not_repeat_inference(self):
        def test_only_probe(repo, artifact, digest, journal):
            journal['candidate_slices_checked'] = 1
        with TemporaryDirectory() as temp, patch.object(smoke,'preflight',return_value={'test_only':True}), \
                patch.object(smoke,'run_probe',side_effect=test_only_probe) as probe, redirect_stdout(io.StringIO()):
            root = Path(temp)
            smoke.run(root); smoke.run(root)
            self.assertEqual(probe.call_count,1)
            path = root/smoke.ROOT/'results/report.json'
            altered = read_json(path); altered['frontend_verified'] = True; write_json(path,altered)
            with self.assertRaisesRegex(ValueError,'differs'): smoke.run(root)
            self.assertEqual(probe.call_count,1)


if __name__ == '__main__':
    unittest.main()
