"""Synthetic software checks; no real policy/test examples or trained weights."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from datetime import datetime
from io import StringIO
from pathlib import Path
import shutil
import sys
from threading import Lock
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'ml/scripts'))
import evaluate_candidate_policy as runner
import cuad_candidate_policy as policy_module
import cuad_calibration
import test_cuad_calibration as calibration_fixture
import test_cuad_decoder_validation as decoder_fixture
from clauseanchor_core import CandidateOnlyAnalyzer, AnalysisContext, to_dict, from_dict, validate_result, text_digest
from clauseanchor_core._inference import window_candidates, disjoint_candidates
from check_cuad_families import canonical_sha256, read_json
from cuad_checkpoints import replace_json
from run_cuad_baseline import atomic_json

POLICY=read_json(REPO/runner.CONFIG)


def task(qid='q',group='d',family='f',gold=((0,5),),tokens=5):
    source='αβ🙂_ abcde\r\nRepeated. Repeated.'
    return {'question_id':qid,'group_id':group,'family_id':family,'category_id':'c','context':source,
            'begin':0,'end':1,'original_question_tokens':tokens,
            'gold':[{'start':a,'end':b,'text':source[a:b]} for a,b in gold]}


def candidate(t,a=0,b=5,margin=3.,boundary=False):
    c=decoder_fixture.candidate(a,b,score=margin,boundary=boundary)
    c['text']=t['context'][a:b]
    return c


class PolicyTests(unittest.TestCase):
    def test_perfect_candidate_quality_cannot_enable_automatic_acceptance(self):
        t=task(); result,projections=policy_module.summarize_policy([t],[[candidate(t)]],POLICY)
        self.assertEqual(result['candidate_metrics']['micro']['precision'],1)
        self.assertEqual(result['accepted_metrics']['micro']['predicted'],0)
        self.assertIsNone(result['accepted_metrics']['micro']['precision'])
        self.assertEqual(result['accepted_metrics']['micro']['recall'],0)
        self.assertFalse(result['automatic_acceptance']['enabled'])
        self.assertFalse(result['automatic_acceptance']['zero_false_accepted_highlights_is_a_quality_pass'])
        self.assertFalse(result['absence']['enabled']); self.assertIsNone(result['absence']['error_rate'])
        clause=projections[0]['core_result'].categories[0].clauses[0]
        self.assertEqual(clause.status,'review_candidate'); self.assertIsNone(clause.confidence)

    def test_zero_outputs_remain_abstained_with_all_gold_missed(self):
        t=task(gold=((0,5),(6,11)))
        summary,projected=policy_module.summarize_policy([t],[[]],POLICY)
        c=projected[0]['core_result'].categories[0]
        self.assertEqual(c.status,'abstained'); self.assertEqual(c.reason_code,'unvalidated_model')
        self.assertTrue(c.search_complete); self.assertEqual(c.unresolved_count,0)
        self.assertEqual(summary['candidate_metrics']['micro']['fn'],2)
        self.assertEqual(summary['positive_questions_without_candidates'],1)

    def test_no_gold_no_outputs_is_never_absence(self):
        t=task(gold=())
        summary,p=policy_module.summarize_policy([t],[[]],POLICY)
        self.assertEqual(p[0]['core_result'].categories[0].status,'abstained')
        self.assertIsNone(summary['accepted_metrics']['micro']['recall'])
        self.assertEqual(summary['absence']['decisions'],0)

    def test_incomplete_candidates_retained_with_reasons_and_all_denominators(self):
        t=task(tokens=65)
        summary,projected=policy_module.summarize_policy([t],[[candidate(t,boundary=True)]],POLICY)
        c=projected[0]['core_result'].categories[0]
        self.assertFalse(c.search_complete); self.assertEqual(c.reason_code,'processing_incomplete_unvalidated')
        self.assertEqual(c.unresolved_count,1); self.assertEqual(summary['candidate_metrics']['micro']['gold'],1)
        self.assertEqual(summary['per_question'][0]['processing_issues'],['question_truncated_first64','boundary_review'])
        self.assertEqual(summary['candidate_strata']['processing_incomplete']['micro']['predicted'],1)

    def test_unprocessed_category_is_unavailable_not_absent(self):
        t=task(); c=policy_module.project_result(t,[],POLICY['artifact_manifest_sha256'],windows_done=0).categories[0]
        self.assertEqual(c.status,'unavailable'); self.assertFalse(c.search_complete)
        self.assertEqual(c.reason_code,'window_limit_not_processed')
        with self.assertRaises(ValueError): policy_module.project_result(t,[candidate(t)],POLICY['artifact_manifest_sha256'],windows_done=0)

    def test_partial_parser_remains_incomplete(self):
        t=task(); r=policy_module.project_result(t,[candidate(t)],POLICY['artifact_manifest_sha256'],parser_complete=False)
        self.assertFalse(r.categories[0].search_complete); self.assertIn('parser_incomplete',r.warnings)

    def test_exact_unicode_crlf_repeated_occurrence_and_serialization(self):
        t=task(); start=t['context'].rindex('Repeated.')
        selected=[candidate(t,0,5),candidate(t,start,start+9)]
        r=policy_module.project_result(t,selected,POLICY['artifact_manifest_sha256'])
        roundtrip=from_dict(to_dict(r)); validate_result(roundtrip,t['context'])
        self.assertEqual(roundtrip,r)
        self.assertEqual(roundtrip.categories[0].clauses[1].span.start,start)
        self.assertTrue(all(c.origin=='model' and not c.rule_flags and not c.passages and c.retrieval_status=='not_run' for c in r.categories[0].clauses))

    def test_changed_source_slice_rejected(self):
        t=task(); c=candidate(t); c['text']='wrong'
        with self.assertRaisesRegex(ValueError,'source slice'): policy_module.project_result(t,[c],POLICY['artifact_manifest_sha256'])

    def test_projection_never_reads_gold(self):
        class Guard(dict):
            def __getitem__(self,key):
                if key=='gold': raise AssertionError('gold must not determine policy')
                return super().__getitem__(key)
        t=task(); r=policy_module.project_result(Guard(t),[candidate(t)],POLICY['artifact_manifest_sha256'])
        self.assertEqual(r.categories[0].status,'abstained')

    def test_no_diagnostic_cutoff_top_one_or_top50_added(self):
        t=task(); t['context']='x'*140; t['gold']=[]
        raw=[candidate(t,i*2,i*2+1,margin=.001) for i in range(60)]
        raw += [candidate(t,130,131,margin=0),candidate(t,132,133,margin=-1)]
        summary,projected=policy_module.summarize_policy([t],[raw],POLICY)
        self.assertEqual(summary['candidate_metrics']['micro']['predicted'],60)
        self.assertEqual(len(projected[0]['core_result'].categories[0].clauses),60)

    def test_one_to_one_matching_not_fixed_overlap_labels(self):
        t=task(gold=((0,10),))
        summary,_=policy_module.summarize_policy([t],[[candidate(t,0,5),candidate(t,5,10)]],POLICY)
        m=summary['candidate_metrics']['micro']
        self.assertEqual((m['tp'],m['fp'],m['fn']),(1,1,0))

    def test_document_and_family_counts_include_zero_outputs(self):
        ts=[task('a','d1','f1'),task('b','d1','f1',gold=()),task('c','d2','f1'),task('d','d3','f2')]
        pools=[[candidate(ts[0])],[candidate(ts[1])],[],[]]
        s,_=policy_module.summarize_policy(ts,pools,POLICY)
        self.assertEqual(len(s['per_document']),3); self.assertEqual(len(s['per_family']),2)
        self.assertAlmostEqual(s['candidate_document_distributions']['false_highlights']['mean'],1/3)
        self.assertEqual(s['candidate_strata']['no_gold']['micro']['fp'],1)
        self.assertEqual(s['candidate_uncertainty']['families'],2)

    def test_bootstrap_resamples_whole_family_including_multiple_documents(self):
        rows=[]
        for doc,family,tp,pred,gold in [('a','f1',1,1,1),('b','f1',0,1,1),('c','f2',0,0,1)]:
            rows.append({'group_id':doc,'family_id':family,'candidate_counts':{'tp':tp,'predicted':pred,'gold':gold,'fp':pred-tp,'exact_matches':tp}})
        a=policy_module.bootstrap_families(rows,POLICY); b=policy_module.bootstrap_families(rows,POLICY)
        self.assertEqual(a,b); self.assertAlmostEqual(a['intervals']['precision']['lower'],.5)
        self.assertAlmostEqual(a['intervals']['precision']['upper'],.5)
        self.assertGreater(a['intervals']['precision']['undefined_replicates'],0)
        self.assertEqual(a['intervals']['recall']['lower'],0)
        self.assertEqual(a['intervals']['recall']['upper'],.5)
        self.assertEqual(a['intervals']['false_highlights_per_document']['upper'],.5)

    def test_sparse_category_support_never_promoted(self):
        t=task(); s,_=policy_module.summarize_policy([t],[[candidate(t)]],POLICY)
        support=s['category_support']['c']
        self.assertTrue(support['sparse_support']); self.assertEqual(support['catalogue_support_status'],'not_validated')
        self.assertEqual(s['candidate_uncertainty']['status'],'insufficient_families')

    def test_missing_or_extra_pools_fail_instead_of_partial_metrics(self):
        t=task()
        for pools in ([],[[],[]]):
            with self.assertRaises(ValueError): policy_module.summarize_policy([t],iter(pools),POLICY)

    def test_source_and_input_candidates_immutable(self):
        t=task(); raw=[candidate(t)]; before=deepcopy((t,raw))
        policy_module.summarize_policy([t],[raw],POLICY)
        self.assertEqual((t,raw),before)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.fixture=calibration_fixture.InputAndRunnerTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f=self.fixture; self.repo=f.repo; self.policy=deepcopy(POLICY); self.prompts=f.prompts
        frozen=read_json(self.repo/runner.FROZEN/'manifest.json'); part=read_json(self.repo/runner.FROZEN/'dev_cal.json')
        part.update(partition='dev_policy',intended_role='operating_threshold_selection')
        atomic_json(self.repo/runner.FROZEN/'dev_policy.json',part)
        entry=frozen['partitions'].pop('dev_cal'); entry.update(file='dev_policy.json',canonical_sha256=canonical_sha256(part))
        frozen['partitions']['dev_policy']=entry; frozen['partitions']['dev_cal']={'file':'MUST_NOT_READ'}
        replace_json(self.repo/runner.FROZEN/'manifest.json',frozen)
        identity=read_json(f.f.feature/'identity.json'); identity['frozen_manifest_sha256']=canonical_sha256(frozen)
        replace_json(f.f.feature/'identity.json',identity)
        self.directory=f.f.feature/'dev_policy'/f.directory.name; self.directory.parent.mkdir(); shutil.move(f.directory,self.directory)
        shard=read_json(self.directory/'manifest.json'); shard.update(partition='dev_policy',feature_identity_sha256=canonical_sha256(identity))
        replace_json(self.directory/'manifest.json',shard)
        manifest=read_json(f.f.feature/'manifest.json'); manifest['feature_identity_sha256']=canonical_sha256(identity)
        manifest['partitions']['dev_cal']=[{'path':'MUST_NOT_READ'}]
        manifest['partitions']['dev_policy']=[{'path':'dev_policy/'+self.directory.name,'manifest_sha256':canonical_sha256(shard),'summary':shard['summary']}]
        replace_json(f.f.feature/'manifest.json',manifest)
        self.policy['feature_manifest_sha256']=canonical_sha256(manifest)
        for name in runner.CODE_FILES:
            dst=self.repo/'ml/scripts'/name; shutil.copyfile(REPO/'ml/scripts'/name,dst)
        self.root=self.repo/runner.ROOT; self.root.mkdir()
        self.catalogue={'categories':[{'id':'c'},{'id':'in.arbitration'}]}
        self.calibration={'status':'unvalidated','family_ids':['independent_calibration_family']}
        with redirect_stdout(StringIO()): self.tasks,self.inputs=runner.verify_inputs(self.repo,self.policy,self.prompts)

    def invoke(self,full=True,now=None,**extra):
        with ExitStack() as stack:
            defaults={'read_policy':self.policy,'execution':{'device':'cpu','batch_size':1},
                      'verify_bundle':({},self.catalogue,self.prompts),'verify_calibration':self.calibration,
                      'verify_ignored_assets':None,'now_ist':now or datetime(2026,10,29,tzinfo=runner.INDIA)}
            defaults.update(extra)
            for name,value in defaults.items(): stack.enter_context(patch.object(runner,name,return_value=value))
            stack.enter_context(patch.object(runner,'TorchBackend',return_value=SimpleNamespace(model=decoder_fixture.FixedModel(),device=torch.device('cpu'))))
            stack.enter_context(redirect_stdout(StringIO()))
            return runner.run(self.repo,device='cpu',full=full)

    def test_actual_no_grad_all_window_inference_projected_contract(self):
        report=self.invoke()
        self.assertEqual(report['coverage']['windows'],9)
        self.assertEqual(sum(q['windows_done'] for q in report['measurement']['per_question']),9)
        rows=read_json(self.root/'results/projections.json')
        for t,row in zip(self.tasks,rows):
            result=from_dict(row['core_result']); validate_result(result,t['context'])
            self.assertEqual(result.categories[0].status,'abstained')
            self.assertTrue(all(c.confidence is None and c.status=='review_candidate' for c in result.categories[0].clauses))

    def test_pilot_never_scores_then_full_reuses_without_fitting(self):
        with patch.object(runner,'summarize_policy',side_effect=AssertionError('no partial metrics')):
            self.assertIsNone(self.invoke(full=False))
        self.assertTrue((self.root/'identity.json').is_file()); self.assertFalse((self.root/'results').exists())
        first=(self.root/'questions/000000.json').read_bytes()
        with patch.object(cuad_calibration,'fit_sigmoid',side_effect=AssertionError('no fitting')):
            with patch.object(cuad_calibration,'assess',side_effect=AssertionError('no recalibration')):
                r=self.invoke()
        self.assertEqual(r['current_invocation_new_questions'],1)
        self.assertEqual((self.root/'questions/000000.json').read_bytes(),first)
        self.assertFalse(r['calibration_fitted_or_applied']); self.assertFalse(r['threshold_search_performed'])

    def test_identity_written_before_model_call(self):
        original=runner.infer_question
        def checked(*args):
            self.assertTrue((self.root/'identity.json').is_file())
            return original(*args)
        with patch.object(runner,'infer_question',side_effect=checked): self.invoke()

    def test_complete_cache_reused_without_collection_or_scoring_after_deadline(self):
        r=self.invoke()
        with patch.object(runner,'collect',side_effect=AssertionError('no fresh inference')):
            with patch.object(runner,'summarize_policy',side_effect=AssertionError('no repeated metrics')):
                self.assertEqual(self.invoke(now=datetime(2026,11,5,tzinfo=runner.INDIA)),r)

    def test_new_late_run_refused(self):
        with patch.object(runner,'read_policy',return_value=self.policy),patch.object(runner,'now_ist',return_value=datetime(2026,11,5,tzinfo=runner.INDIA)):
            with patch.object(runner,'execution',side_effect=AssertionError('must stop before loading')):
                with self.assertRaisesRegex(ValueError,'deadline passed'): runner.run(self.repo)

    def test_late_finish_retains_policy_but_marks_deadline_missed(self):
        times=iter([datetime(2026,11,4,tzinfo=runner.INDIA),datetime(2026,11,5,tzinfo=runner.INDIA)])
        original=runner.summarize_policy
        def late(*args):
            # Change only the post-measurement clock, never any model/result data.
            runner.now_ist.return_value=datetime(2026,11,5,tzinfo=runner.INDIA)
            return original(*args)
        with patch.object(runner,'summarize_policy',side_effect=late): r=self.invoke(now=next(times))
        self.assertFalse(r['measured_by_deadline'])
        self.assertEqual(r['status'],'policy_evaluation_completed_after_deadline')
        self.assertFalse(r['measurement']['automatic_acceptance']['enabled'])

    def test_only_policy_example_files_opened(self):
        real=runner.read_json; opened=[]
        def checked(path):
            opened.append(str(path)); self.assertNotIn('MUST_NOT_READ',str(path))
            self.assertNotIn(Path(path).name,('dev_cal.json','dev_select.json','fit.json'))
            return real(path)
        with patch.object(runner,'read_json',side_effect=checked),redirect_stdout(StringIO()):
            runner.verify_inputs(self.repo,self.policy,self.prompts)
        self.assertTrue(any(s.endswith('dev_policy.json') for s in opened))

    def test_calibration_family_leakage_blocks_model_loading(self):
        with patch.object(runner,'infer_question',side_effect=AssertionError('must stop first')):
            with self.assertRaisesRegex(ValueError,'family leakage'):
                self.invoke(verify_calibration={'family_ids':['family']})

    def test_bad_feature_hash_wrong_role_and_prompt_fail(self):
        p=deepcopy(self.policy); p['feature_manifest_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'manifest'): runner.verify_inputs(self.repo,p,self.prompts)
        with self.assertRaisesRegex(ValueError,'prompt'): runner.verify_inputs(self.repo,self.policy,{'c':'changed'})
        path=self.repo/runner.FROZEN/'dev_policy.json'; value=read_json(path); value['intended_role']='calibrator_fitting'; replace_json(path,value)
        with self.assertRaisesRegex(ValueError,'membership'): runner.verify_inputs(self.repo,self.policy,self.prompts)

    def test_damaged_feature_array_fails_before_inference(self):
        path=self.directory/'offsets.npy'; path.write_bytes(path.read_bytes()+b'x')
        with self.assertRaises(ValueError): self.invoke()

    def test_changed_config_and_code_rejected_with_records_preserved(self):
        path=self.repo/runner.CONFIG; p=deepcopy(POLICY); p['minimum_raw_margin_exclusive']=15.65; atomic_json(path,p)
        with self.assertRaisesRegex(ValueError,'policy changed'): runner.read_policy(self.repo)
        self.invoke(full=False); before=(self.root/'questions/000000.json').read_bytes()
        code=self.repo/'ml/scripts/cuad_candidate_policy.py'; code.write_text(code.read_text()+'\n# changed\n')
        with self.assertRaisesRegex(ValueError,'Existing file differs'): self.invoke()
        self.assertEqual((self.root/'questions/000000.json').read_bytes(),before)

    def test_damaged_report_or_record_not_recomputed(self):
        self.invoke(); path=self.root/'results/report.json'; raw=path.read_bytes(); path.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError,'damaged'): self.invoke()
        path.write_bytes(raw); path=self.root/'questions/000002.json'; path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'damaged'): self.invoke()

    def test_all_source_files_preserved(self):
        paths=[p for root in (self.repo/runner.FROZEN,self.repo/runner.FEATURES) for p in root.rglob('*') if p.is_file()]
        before={p:p.read_bytes() for p in paths}; self.invoke()
        self.assertTrue(all(p.read_bytes()==b for p,b in before.items()))

    def test_policy_artifact_keeps_india_unavailable_and_all_support_unvalidated(self):
        self.invoke(); artifact=read_json(self.root/'results/operating_policy.json')
        self.assertEqual(artifact['categories'],[{'id':'c','support_status':'not_validated','inference_available':True},
            {'id':'in.arbitration','support_status':'not_validated','inference_available':False}])
        self.assertIsNone(artifact['confidence']); self.assertFalse(artifact['runtime_changes'])
        self.assertFalse(artifact['accepted_findings_enabled']); self.assertFalse(artifact['absence_enabled'])

    def test_calibration_evidence_pins_and_unvalidated_status_required(self):
        directory=self.repo/'data/processed/cuad/calibration_v1'; directory.mkdir(exist_ok=True)
        identity={'inputs':{'feature_manifest_sha256':self.policy['feature_manifest_sha256']},'family_folds':{'other':0}}
        calibrator={'identity_sha256':canonical_sha256(identity),'status':'unvalidated','runtime_activation':False,
                    'absence_calibration':False,'artifact_manifest_sha256':self.policy['artifact_manifest_sha256']}
        report={'identity_sha256':canonical_sha256(identity),'calibrator_sha256':canonical_sha256(calibrator),'assessment':{'status':'unvalidated'}}
        p=deepcopy(self.policy); p.update(calibration_identity_sha256=canonical_sha256(identity),calibration_report_sha256=canonical_sha256(report),calibrator_sha256=canonical_sha256(calibrator))
        atomic_json(directory/'identity.json',identity); atomic_json(directory/'results/calibrator.json',calibrator); atomic_json(directory/'results/report.json',report)
        self.assertEqual(runner.verify_calibration(self.repo,p)['family_ids'],['other'])
        calibrator['runtime_activation']=True; replace_json(directory/'results/calibrator.json',calibrator)
        with self.assertRaisesRegex(ValueError,'evidence differs'): runner.verify_calibration(self.repo,p)

    def test_projection_parity_with_actual_analyzer_on_scripted_windows(self):
        arrays=self.fixture.f.arrays; t=deepcopy(self.tasks[0]); t['original_question_tokens']=65
        model=decoder_fixture.FixedModel()
        raw,_=runner.infer_question(model,t,arrays,torch.device('cpu'),2)
        selected=disjoint_candidates(raw); projected=policy_module.project_result(t,selected,POLICY['artifact_manifest_sha256'])
        class Tokenizer:
            def context(self,source): return SimpleNamespace(ids=list(range(1000))),None
            def question(self,question): return SimpleNamespace(ids=list(range(64))),65
            def windows(self,*args):
                for row in range(3):
                    yield row,SimpleNamespace(ids=arrays['input_ids'][row].tolist(),attention_mask=arrays['attention_mask'][row].tolist(),
                        sequence_ids=[None if s==-1 else int(s) for s in arrays['sequence_ids'][row]],offsets=arrays['offsets'][row].tolist()),[2]
        class Backend:
            def predict(self,encodings):
                starts=np.zeros((len(encodings),512),np.float32); starts[:,2]=5
                return starts,starts.copy()
        analyzer=object.__new__(CandidateOnlyAnalyzer)
        analyzer._lock=Lock(); analyzer._tokenizer=Tokenizer(); analyzer._backend=Backend()
        analyzer._manifest_sha256=POLICY['artifact_manifest_sha256']; analyzer._questions={'c':'q'}
        analyzer.category_ids=('c',); analyzer.batch_size=2; analyzer.max_windows_per_category=None
        actual=analyzer.analyze(t['context'],doc_id=projected.doc_id,text_sha256=text_digest(t['context']),category_ids=('c',),context=AnalysisContext())
        self.assertEqual(to_dict(actual),to_dict(projected))


if __name__=='__main__': unittest.main()
