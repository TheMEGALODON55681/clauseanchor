"""Source review: frozen matching, observable stages, sampling and provenance."""

from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import torch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_cuad_families import canonical_sha256, read_json
from cuad_checkpoints import replace_json
from cuad_development import match_counts
from run_cuad_baseline import atomic_json
import diagnose_cuad_scores as diagnostic
import review_cuad_errors as review
import validate_cuad_decoder as validation
from test_cuad_decoder_validation import FixedModel, candidate, fixture


class EvidenceTests(unittest.TestCase):
    def test_assignments_preserve_duplicate_gold_and_distinct_occurrences(self):
        gold = [{"start": 0, "end": 10}, {"start": 0, "end": 10}, {"start": 20, "end": 30}]
        unique, pairs = review.assignment([candidate(0, 10), candidate(0, 9)], gold)
        self.assertEqual(unique, [(0, 10), (20, 30)])
        self.assertEqual(pairs, [(0, 0)])

    def test_assignments_recompute_after_filtering(self):
        gold = [{"start": 0, "end": 20}]
        values = [candidate(0, 10, 3), candidate(0, 20, 2)]
        self.assertEqual(review.assignment(values, gold)[1], [(1, 0)])
        self.assertEqual(review.assignment(values[:1], gold)[1], [(0, 0)])

    def test_randomized_assignment_exposure_matches_frozen_counts(self):
        rng = np.random.default_rng(15)
        for _ in range(50):
            values = [candidate(int(a), int(a + b)) for a, b in zip(rng.integers(0, 30, 7), rng.integers(1, 30, 7))]
            gold = [{"start": int(a), "end": int(a + b)} for a, b in zip(rng.integers(0, 30, 4), rng.integers(1, 30, 4))]
            unique, pairs = review.assignment(values, gold)
            self.assertEqual(len(pairs), match_counts(values, gold)["tp"])
            self.assertEqual(len({i for i, _ in pairs}), len(pairs))
            self.assertEqual(len({j for _, j in pairs}), len(pairs))

    def test_empty_and_no_gold_assignments(self):
        self.assertEqual(review.assignment([], [{"start": 0, "end": 2}]), ([(0, 2)], []))
        self.assertEqual(review.assignment([candidate(0, 2)], []), ([], []))

    def test_observable_miss_stages_use_candidate_presence_and_score_sign(self):
        c = candidate(0, 10, 5)
        for raw, selected, kept, expected in [([c], [c], [c], review.STAGES[0]),
                                            ([c], [c], [], review.STAGES[1]),
                                            ([c], [], [], review.STAGES[2]),
                                            ([candidate(0, 10, 0)], [], [], review.STAGES[3]),
                                            ([candidate(0, 10, -2)], [], [], review.STAGES[3]),
                                            ([candidate(0, 4, 20)], [], [], review.STAGES[4]),
                                            ([], [], [], review.STAGES[4])]:
            with self.subTest(expected=expected):
                self.assertEqual(review.miss_stage((0, 10), raw, selected, kept), expected)

    def test_half_overlap_is_eligible_and_touching_is_not(self):
        self.assertEqual(review.miss_stage((0, 20), [candidate(0, 10)], [], []), review.STAGES[2])
        self.assertEqual(review.miss_stage((0, 20), [candidate(20, 30)], [], []), review.STAGES[4])

    def test_unicode_snippets_keep_exact_code_point_offsets(self):
        context = 'α🙂 e\u0301\r\nकानून'
        result = review.snippet(context, (1, 5))
        self.assertEqual(result['text'], '🙂 e\u0301')
        self.assertEqual(result['before'] + result['text'] + result['after'], context)
        for span in [(-1, 2), (1, 1), (0, len(context) + 1)]:
            with self.assertRaises(ValueError):
                review.snippet(context, span)

    def test_feature_coverage_is_separate_from_candidate_stage(self):
        for row, expected in [({'usable_windows': 2, 'reason': None}, 'complete_target_in_regular_windows'),
                              ({'usable_windows': 0, 'reason': None}, 'no_regular_window_contains_complete_target'),
                              ({'usable_windows': 0, 'reason': 'longer_than_256_tokens'}, 'longer_than_256_tokens'),
                              ({'usable_windows': 0, 'reason': 'unmapped_boundary'}, 'unmapped_boundary')]:
            self.assertEqual(review.coverage_label([row]), expected)
        with self.assertRaises(ValueError):
            review.coverage_label([])

    def test_markdown_source_cannot_close_its_literal_fence(self):
        text = '```\n<script>not executable</script>\n````\n# not a heading'
        rendered = review.fenced(text)
        self.assertTrue(rendered.startswith('`````text\n'))
        self.assertTrue(rendered.endswith('\n`````\n'))


class SavedReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.f = fixture(self.repo)
        self.validation_root = self.repo / review.BASE / 'decoder_validation_v1'
        self.validation_root.mkdir()
        scripts = self.repo / 'ml/scripts'
        scripts.mkdir(parents=True)
        for name in ('validate_cuad_decoder.py', 'review_cuad_decoder.py', 'cuad_development.py', 'prepare_cuad_features.py',
                     'cuad_checkpoints.py', 'diagnose_cuad_scores.py', 'review_cuad_errors.py'):
            (scripts / name).write_bytes((SCRIPTS / name).read_bytes())
        # Add the source/audit fields consumed by the new review. The existing
        # feature/checkpoint-chain loaders are mocked at the integration boundary;
        # their actual hash checks are covered by the existing validation tests.
        source = read_json(self.f.directory / 'source.json')
        source['question_audit'] = []
        for i, (q, task) in enumerate(zip(source['source_group']['paragraphs'][0]['questions'], self.f.tasks)):
            q['question'] = 'Highlight the clause for category c.'
            source['question_audit'].append({'question_id': q['question_id'], 'category_id': 'c',
                'window_range': [task['begin'], task['end']], 'original_question_tokens': 8, 'used_question_tokens': 8,
                'answers': [{'answer_index': j, 'start_token': None, 'end_token': None, 'token_length': None,
                             'projected_start': None, 'projected_end': None, 'exact_boundaries': False,
                             'usable_windows': 0, 'reason': 'unmapped_boundary'} for j in range(len(task['gold']))]})
        replace_json(self.f.directory / 'source.json', source)
        for task in self.f.tasks:
            task['source_group_sha256'] = canonical_sha256(source['source_group'])
            task['task_sha256'] = canonical_sha256({k: task[k] for k in ('question_id', 'source_group_sha256', 'shard_manifest_sha256', 'begin', 'end')})
        self.checkpoint = {'fixture_checkpoint': True}
        identity = {'policy': validation.POLICY, 'checkpoint': self.checkpoint, 'features': self.f.binding,
                    'code_sha256': {p.name: diagnostic.code_sha(p) for p in scripts.glob('*.py')
                                   if p.name not in ('diagnose_cuad_scores.py', 'review_cuad_errors.py')}}
        self.run_sha = canonical_sha256(identity)
        atomic_json(self.validation_root / 'identity.json', identity)
        with redirect_stdout(StringIO()):
            rows, hashes = validation.process_questions(self.validation_root, self.f.tasks, self.run_sha,
                lambda t: validation.infer_question(FixedModel(), t, self.f.arrays, torch.device('cpu'), 2), self.f.evaluation, None)
        self.validation_report = validation.aggregate_results(self.f.tasks, rows, self.f.evaluation)
        self.validation_report.update(validation_run_sha256=self.run_sha, question_record_sha256=hashes)
        atomic_json(self.validation_root / 'report.json', self.validation_report)
        self.score_root = self.repo / review.BASE / 'score_diagnostic_v1'
        with ExitStack() as stack, redirect_stdout(StringIO()):
            self.patches(stack)
            self.score_report = diagnostic.run(self.repo)
        # This toy model cannot reach 90% precision. Source tracing can still be
        # unit-tested at a deliberately specified fixture cutoff. The run-level
        # integrity tests below keep the actual saved diagnostic unchanged.
        self.fixture_score = deepcopy(self.score_report)
        with redirect_stdout(StringIO()):
            self.pools = diagnostic.load_pools(self.validation_root, self.f.tasks, self.run_sha, self.f.evaluation, self.validation_report)
        details = diagnostic.detailed_point(self.f.tasks, self.pools['disjoint_full'], 10.)
        self.fixture_score['variants']['disjoint_full']['targets']['90'] = {
            'point': {'minimum_margin': 10., 'micro': details['metrics']['micro']}, 'details': details}

    def patches(self, stack):
        for module in (review, diagnostic):
            stack.enter_context(patch.object(module, 'load_checkpoint_reports', return_value=(self.f.evaluation, self.f.progress, self.checkpoint)))
            stack.enter_context(patch.object(module, 'runtime_versions', return_value={'fixture': True}))
            stack.enter_context(patch.object(module, 'verify_ignored_assets'))
        stack.enter_context(patch.object(validation, 'verify_inputs', return_value=(self.f.tasks, self.f.binding)))
        stack.enter_context(patch.object(validation, 'infer_question', side_effect=AssertionError('must not infer')))
        stack.enter_context(patch.object(validation, 'load_model', side_effect=AssertionError('must not load weights')))
        stack.enter_context(patch('torch.load', side_effect=AssertionError('must not deserialize weights')))

    def verify(self):
        with redirect_stdout(StringIO()):
            return review.verify_score_diagnostic(self.repo, self.score_root, self.checkpoint, self.f.binding,
                self.validation_report, self.f.tasks, self.pools,
                {'training': 'clean_training_v1', 'features': 'features_v1', 'validation': 'decoder_validation_v1'})

    def build(self):
        with redirect_stdout(StringIO()):
            return review.build_review(self.f.tasks, self.validation_root, self.validation_report, self.fixture_score)

    def test_full_diagnostic_and_curves_reproduce(self):
        self.assertEqual(self.verify(), self.score_report)

    def test_all_false_highlights_exported_and_miss_census_preserved(self):
        result = self.build()
        self.assertEqual(result['metrics']['micro']['tp'], 2)
        self.assertEqual(result['case_counts']['false_highlight'], 7)
        self.assertEqual(result['missed_gold_by_observed_stage']['no_eligible_saved_candidate'], 1)
        misses = [c for c in result['cases'] if c['kind'] == 'missed_gold']
        self.assertEqual(misses[0]['focus']['text'], self.f.tasks[2]['context'][100:120])
        self.assertEqual(misses[0]['feature_alignment'][0]['answer_index'], 0)
        self.assertTrue(all(c['review_status'] == 'pending' and c['confirmed_error_cause'] is None for c in result['cases']))

    def test_sampling_is_deterministic_and_does_not_drop_miss_counts(self):
        details = diagnostic.detailed_point(self.f.tasks, self.pools['disjoint_full'], 11.)
        self.fixture_score['variants']['disjoint_full']['targets']['90'] = {
            'point': {'minimum_margin': 11., 'micro': details['metrics']['micro']}, 'details': details}
        result = self.build()
        self.assertEqual(result, self.build())
        self.assertEqual(result['missed_gold_by_observed_stage']['below_diagnostic_cutoff'], 2)
        self.assertEqual(result['missed_gold_by_observed_stage']['no_eligible_saved_candidate'], 1)
        self.assertEqual(result['case_counts']['missed_gold'], 2)

    def test_suppressed_candidate_has_actual_overlap_witness(self):
        task = self.f.tasks[0]
        source = read_json(self.f.directory / 'source.json')
        metadata = review.source_metadata(task, source)
        raw = [candidate(0, 20, 20), candidate(0, 5, 19)]
        selected = validation.selections(raw)[0]['disjoint_full']
        case = review.make_case('missed_gold', (0, 5), task, metadata, raw, selected, selected,
                                review.other_category_index(self.f.tasks))
        self.assertEqual(case['observed_stage'], 'suppressed_by_disjoint')
        self.assertEqual(case['highest_scoring_eligible_raw']['margin'], 19)
        self.assertEqual(case['overlapping_disjoint_output']['margin'], 20)

    def test_boundary_case_keeps_assigned_gold_and_source_offsets(self):
        task = self.f.tasks[0]
        metadata = review.source_metadata(task, read_json(self.f.directory / 'source.json'))
        prediction = candidate(0, 4, 20)
        case = review.make_case('boundary_match', (0, 4), task, metadata, [prediction], [prediction], [prediction],
                                review.other_category_index(self.f.tasks), prediction, (0, 5))
        self.assertEqual(case['focus']['text'], task['context'][0:4])
        self.assertEqual(case['matched_gold']['text'], task['context'][0:5])
        self.assertIsNone(case['confirmed_error_cause'])

    def test_stage_priority_does_not_mistake_rematching_for_filtering(self):
        # An eligible high-scoring output can be assigned to another gold span;
        # a lower score on an alternative is not enough to call it a cutoff loss.
        values = [candidate(0, 10, 20), candidate(0, 20, 5)]
        self.assertEqual(review.miss_stage((0, 20), values, values, values[:1]), 'eligible_output_unmatched')

    def test_other_category_hints_include_only_same_source_and_overlap(self):
        tasks = deepcopy(self.f.tasks)
        tasks[1]['category_id'] = 'another_category'
        tasks[1]['gold'] = [{'start': 0, 'end': 5}, {'start': 10, 'end': 15}]
        tasks[2]['paragraph_index'] = 1
        tasks[2]['category_id'] = 'wrong_paragraph'
        tasks[2]['gold'] = [{'start': 0, 'end': 5}]
        task = tasks[0]
        metadata = review.source_metadata(task, read_json(self.f.directory / 'source.json'))
        c = candidate(0, 5)
        case = review.make_case('false_highlight', (0, 5), task, metadata, [c], [c], [c], review.other_category_index(tasks), c)
        self.assertEqual(case['other_category_annotation_overlaps'],
                         [{'category_id': 'another_category', 'start': 0, 'end': 5, 'iou': 1.0}])

    def test_other_category_hints_do_not_use_a_different_document(self):
        tasks = deepcopy(self.f.tasks)
        tasks[1]['gold'] = [{'start': 0, 'end': 5}]
        tasks[1]['category_id'] = 'different'
        tasks[2]['group_id'] = 'other_document'
        tasks[2]['gold'] = [{'start': 20, 'end': 25}]
        index = review.other_category_index(tasks)
        self.assertIn(('different', 0, 5), index['group', 0])
        self.assertNotIn(('c', 20, 25), index['group', 0])

    def test_source_context_or_audit_mismatch_is_rejected(self):
        source = read_json(self.f.directory / 'source.json')
        source['question_audit'][0]['window_range'] = [0, 1]
        replace_json(self.f.directory / 'source.json', source)
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            self.build()

    def test_record_change_after_verification_is_rejected(self):
        path = self.validation_root / 'questions/000000.json'
        data = read_json(path)
        data['payload']['candidates'][0][2] += 1
        data['payload_sha256'] = canonical_sha256(data['payload'])
        replace_json(path, data)
        with self.assertRaisesRegex(ValueError, 'changed after'):
            self.build()

    def test_changed_report_metrics_rejected(self):
        report = deepcopy(self.score_report)
        report['variants']['disjoint_full']['baseline']['metrics']['micro']['tp'] += 1
        replace_json(self.score_root / 'report.json', report)
        with self.assertRaisesRegex(ValueError, 'did not reproduce'):
            self.verify()

    def test_resealed_curve_change_is_rejected_by_reproduction(self):
        curves = read_json(self.score_root / 'curves.json')
        curves['variants']['disjoint_full']['global'][0]['micro']['gold'] += 1
        report = deepcopy(self.score_report)
        report['curves_sha256'] = canonical_sha256(curves)
        replace_json(self.score_root / 'curves.json', curves)
        replace_json(self.score_root / 'report.json', report)
        with self.assertRaisesRegex(ValueError, 'curves did not reproduce'):
            self.verify()

    def test_changed_diagnostic_producer_is_rejected(self):
        (self.repo / 'ml/scripts/diagnose_cuad_scores.py').write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'producer changed'):
            self.verify()

    def test_unattainable_target_does_not_create_review_cases(self):
        with self.assertRaisesRegex(ValueError, 'unattainable'):
            review.build_review(self.f.tasks, self.validation_root, self.validation_report, self.score_report)

    def test_end_to_end_no_inference_and_immutable_rerun(self):
        # Make all saved candidates score zero except genuine q0 spans. Rebuild
        # the toy source evaluation/records so the real score diagnostic has an
        # attainable target; no diagnostic functions are stubbed in this test.
        for i, task in enumerate(self.f.tasks):
            path = self.validation_root / 'questions' / f'{i:06d}.json'
            record = read_json(path)
            raw = validation.validate_record(record, task, self.run_sha)
            for c in raw:
                c['margin'] = 10. if i == 0 and c['start'] in (0, 10) else 0.
            raw.sort(key=lambda c: (c['window_row'], -c['margin'], c['start'], c['end'], c['start_token'], c['end_token']))
            record = validation.make_record(task, self.run_sha, raw, record['payload']['window_counts'])
            replace_json(path, record)
            selected, capped = validation.selections(raw)
            self.f.evaluation['predictions'][i]['candidates'] = capped
            self.f.evaluation['per_question'][i]['selection'] = match_counts(selected['original_capped'], task['gold'])
        with redirect_stdout(StringIO()):
            rows, hashes = validation.process_questions(self.validation_root, self.f.tasks, self.run_sha,
                lambda t: self.fail('must not infer'), self.f.evaluation, None)
        self.validation_report = validation.aggregate_results(self.f.tasks, rows, self.f.evaluation)
        self.validation_report.update(validation_run_sha256=self.run_sha, question_record_sha256=hashes)
        replace_json(self.validation_root / 'report.json', self.validation_report)
        # New fixture diagnostic input version, retaining the original toy run.
        with ExitStack() as stack, redirect_stdout(StringIO()):
            self.patches(stack)
            diagnostic.run(self.repo, run_name='score_fixture_v2')
            before = {p: p.read_bytes() for directory in (self.validation_root, self.repo / review.BASE / 'score_fixture_v2')
                      for p in directory.rglob('*') if p.is_file()}
            first = review.run(self.repo, diagnostic_run='score_fixture_v2')
            second = review.run(self.repo, diagnostic_run='score_fixture_v2')
            self.assertEqual(first, second)
            for path, payload in before.items():
                self.assertEqual(path.read_bytes(), payload)
            output = self.repo / review.BASE / 'error_review_v1'
            self.assertEqual(first['review_identity_sha256'], canonical_sha256(read_json(output / 'identity.json')))
            self.assertFalse(first['human_review_completed'])
            self.assertEqual(first['review']['metrics']['micro']['tp'], 2)
            self.assertEqual(first['review']['metrics']['micro']['fp'], 0)
            path = output / 'review.md'
            path.write_text('keep my notes', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Existing file differs'):
                review.run(self.repo, diagnostic_run='score_fixture_v2')
            self.assertEqual(path.read_text(), 'keep my notes')

    def test_invalid_or_overlapping_run_names_fail(self):
        for kwargs in ({'run_name': '../escape'}, {'run_name': 'score_diagnostic_v1'}, {'diagnostic_run': 'features_v1'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                review.run(self.repo, **kwargs)


if __name__ == '__main__':
    unittest.main()
