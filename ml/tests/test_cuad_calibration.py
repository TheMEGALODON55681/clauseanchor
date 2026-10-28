"""Synthetic tests for leakage boundaries, one method, provenance and resume.

No real dev_cal examples or trained weights are read by this suite.
"""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from datetime import datetime
from io import StringIO
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import expit
import torch

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'ml/scripts'))
import assess_cuad_calibration as runner
import cuad_calibration as cal
import test_cuad_decoder_validation as saved_fixture
from check_cuad_families import canonical_sha256, read_json
from cuad_checkpoints import replace_json
from cuad_development import match_counts
from run_cuad_baseline import atomic_json

POLICY=read_json(REPO/runner.CONFIG)


def examples():
    # Fixed artificial probabilities; there is deliberately no CUAD data here.
    rng=np.random.default_rng(119)
    rows=[]
    for family in range(30):
        for i in range(60):
            score=float(1+i/2)
            rows.append({'family_id':f'f{family}','category_id':'a' if i%2 else 'b',
                         'margin':score,'label':int(rng.random()<expit(score/7-2))})
    return rows,[f'f{i}' for i in range(30)]


class MethodTests(unittest.TestCase):
    def test_family_assignment_deterministic_order_independent_and_balanced(self):
        families=[f'f{i}' for i in range(37)]
        first=cal.family_folds(families,POLICY)
        self.assertEqual(first,cal.family_folds(list(reversed(families))+families,POLICY))
        counts=[list(first.values()).count(i) for i in range(5)]
        self.assertLessEqual(max(counts)-min(counts),1)

    def test_monotone_fit_finite_without_modifying_inputs(self):
        x=[1.]*50+[20.]*50; y=[0]*50+[1]*50; before=deepcopy((x,y))
        result=cal.fit_sigmoid(x,y,POLICY)
        self.assertEqual(result['status'],'fitted')
        p=cal.probabilities([1,5,10,20],result['parameters'])
        self.assertTrue(np.all(np.diff(p)>0)); self.assertTrue(np.all((p>0)&(p<1)))
        self.assertEqual((x,y),before)

    def test_missing_classes_no_fabricated_parameters(self):
        for x,y in [([],[]),([1]*100,[0]*100),([1]*20+[2]*19,[0]*20+[1]*19)]:
            f=cal.fit_sigmoid(x,y,POLICY)
            self.assertEqual(f['status'],'insufficient_training_classes'); self.assertIsNone(f['parameters'])

    def test_flat_and_reverse_relation_not_rescued_by_another_method(self):
        for x,y in [([1]*100,[0,1]*50),([1]*50+[20]*50,[1]*50+[0]*50)]:
            result=cal.fit_sigmoid(x,y,POLICY)
            self.assertEqual(result['status'],'flat_or_boundary_solution'); self.assertIsNone(result['parameters'])

    def test_optimizer_failure_explicit_no_retry(self):
        with patch.object(cal,'minimize',return_value=SimpleNamespace(success=False,x=np.array([1,1]),message='failed')) as op:
            result=cal.fit_sigmoid([1]*50+[20]*50,[0]*50+[1]*50,POLICY)
        self.assertEqual(op.call_count,1); self.assertEqual(result['status'],'optimizer_failed')

    def test_bad_margins_or_labels_rejected(self):
        for x,y in [([float('nan')],[1]),([0],[1]),([-1],[0]),([1],[2]),([1],[])]:
            with self.assertRaises(ValueError): cal.fit_sigmoid(x,y,POLICY)

    def test_oof_matches_independent_fit_excluding_entire_family_fold(self):
        rows,families=examples(); report,oof=cal.assess(rows,families,['a','b','empty'],POLICY)
        held_fold=2
        train=[r for r in oof if r['fold']!=held_fold]; held=[r for r in oof if r['fold']==held_fold]
        fit=cal.fit_sigmoid([r['margin'] for r in train],[r['label'] for r in train],POLICY)
        np.testing.assert_allclose([r['oof_probability'] for r in held],cal.probabilities([r['margin'] for r in held],fit['parameters']),rtol=0,atol=0)
        self.assertFalse(set(r['family_id'] for r in train)&set(r['family_id'] for r in held))
        self.assertTrue(all(r['baseline_probability']==(sum(r['label'] for r in train)+1)/(len(train)+2) for r in held))
        self.assertTrue(report['categories']['empty']['sparse_support'])
        self.assertEqual(report['categories']['empty']['validation_status'],'not_validated')
        self.assertFalse(report['runtime_activation']); self.assertFalse(report['absence_calibrated'])

    def test_held_out_labels_cannot_change_own_fold_fit_or_predictions(self):
        rows,families=examples(); folds=cal.family_folds(families,POLICY)
        a,oa=cal.assess(rows,families,['a','b'],POLICY)
        changed=[{**r,'label':1-r['label']} if folds[r['family_id']]==1 else r for r in rows]
        b,ob=cal.assess(changed,families,['a','b'],POLICY)
        self.assertEqual(a['fold_fits'][1],b['fold_fits'][1])
        self.assertEqual([r['oof_probability'] for r in oa if r['fold']==1],[r['oof_probability'] for r in ob if r['fold']==1])

    def test_bins_boundary_values_and_empty_bins_not_zero_reliability(self):
        m=cal.metrics([0,0,1,1],[0,.2,.8,1],['a','b','a','b'],POLICY)
        self.assertEqual([b['count'] for b in m['bins']],[1,1,0,0,2])
        self.assertIsNone(m['bins'][2]['observed_fraction'])
        self.assertAlmostEqual(m['brier'],.02); self.assertAlmostEqual(m['ece'],.1)

    def test_bootstrap_is_whole_family_not_independent_candidate_sampling(self):
        p=deepcopy(POLICY); p['reliability']['bootstrap_replicates']=200
        rows=[{'family_id':'a','oof_probability':.9,'baseline_probability':.5,'label':1}]*10
        rows += [{'family_id':'b','oof_probability':.9,'baseline_probability':.5,'label':0}]*10
        a=cal.family_bootstrap(rows,['a','b'],p); b=cal.family_bootstrap(rows,['a','b'],p)
        self.assertEqual(a,b)
        self.assertAlmostEqual(a['intervals']['brier']['lower'],.01)
        self.assertAlmostEqual(a['intervals']['brier']['upper'],.81)
        self.assertFalse(a['refit_uncertainty_included'])

    def test_zero_candidate_families_preserved_undefined_bootstrap_reported(self):
        rows=[{'family_id':'a','oof_probability':.5,'baseline_probability':.5,'label':1}]
        out=cal.family_bootstrap(rows,['a','b'],POLICY)
        self.assertEqual(out['families'],2); self.assertGreater(out['undefined_replicates'],0)

    def test_no_rows_produces_unvalidated_completed_assessment(self):
        report,rows=cal.assess([],['a','b'],['cat'],POLICY)
        self.assertEqual(rows,[]); self.assertEqual(report['status'],'unvalidated')
        self.assertIsNone(report['oof_metrics']); self.assertIsNone(report['full_refit']['parameters'])

    def test_late_assessment_cannot_pass(self):
        rows,families=examples(); report,_=cal.assess(rows,families,['a','b'],POLICY,in_time=False)
        self.assertEqual(report['status'],'unvalidated'); self.assertIn('completed_by_deadline',report['failed_checks'])

    def test_all_gates_must_pass_and_pass_does_not_activate_runtime(self):
        rows,families=examples(); policy=deepcopy(POLICY)
        # A deliberately permissive synthetic gate tests the decision wiring;
        # the production config remains pinned and unchanged.
        policy['reliability'].update(minimum_nonempty_bin_candidates=1,minimum_nonempty_bin_families=1,
                                    maximum_nonempty_bin_absolute_gap=1,maximum_ece_upper_95=1)
        report,_=cal.assess(rows,families,['a','b'],policy)
        self.assertEqual(report['status'],'pooled_oof_assessment_passed_policy_pending')
        self.assertFalse(report['runtime_activation'])
        for key,value in [('minimum_total_candidates',100000),('minimum_total_per_class',100000),
                          ('minimum_candidate_families',100000),('minimum_nonempty_bin_candidates',100000),
                          ('minimum_nonempty_bin_families',100000),('maximum_nonempty_bin_absolute_gap',0),('maximum_ece_upper_95',0)]:
            p=deepcopy(policy); p['reliability'][key]=value
            failed,_=cal.assess(rows,families,['a','b'],p)
            self.assertEqual(failed['status'],'unvalidated',key)


class InputAndRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name); f=saved_fixture.fixture(self.repo); self.f=f
        self.group=deepcopy(f.partition['groups'][0]); self.prompts={'c':'Synthetic category question'}
        for q in self.group['paragraphs'][0]['questions']: q['question']=self.prompts['c']
        self.freeze=read_json(REPO/'ml/configs/cuad_split_freeze.json')
        atomic_json(self.repo/'ml/configs/cuad_split_freeze.json',self.freeze)
        partition={'partition':'dev_cal','intended_role':'calibrator_fitting','groups':[self.group],
                   'freeze_canonical_sha256':canonical_sha256(self.freeze)}
        frozen={'freeze_canonical_sha256':canonical_sha256(self.freeze),'assignment_canonical_sha256':self.freeze['assignment_canonical_sha256'],
                'partitions':{'dev_cal':{'file':'dev_cal.json','canonical_sha256':canonical_sha256(partition),
                             'summary':{'questions':3,'exact_text_groups':1,'family_units':1,'answer_spans':3}},
                             'dev_policy':{'file':'MUST_NOT_READ'},'fit':{'file':'MUST_NOT_READ'}}}
        replace_json(self.repo/runner.FROZEN/'manifest.json',frozen)
        atomic_json(self.repo/runner.FROZEN/'dev_cal.json',partition)
        identity=read_json(f.feature/'identity.json'); identity['frozen_manifest_sha256']=canonical_sha256(frozen); identity['code_sha256']={}
        replace_json(f.feature/'identity.json',identity)
        relative=f'dev_cal/{canonical_sha256(self.group)[:24]}'
        self.directory=f.feature/relative; self.directory.parent.mkdir(exist_ok=True); shutil.move(f.directory,self.directory)
        shard=read_json(self.directory/'manifest.json'); shard.update(partition='dev_cal',source_group_sha256=canonical_sha256(self.group),feature_identity_sha256=canonical_sha256(identity))
        audits=[{'question_id':f'q{i}','category_id':'c','window_range':[i*3,i*3+3],'original_question_tokens':5,'used_question_tokens':5} for i in range(3)]
        replace_json(self.directory/'source.json',{'source_group':self.group,'question_audit':audits})
        shard['files']['source.json']=runner.file_spec(self.directory/'source.json'); replace_json(self.directory/'manifest.json',shard)
        manifest=read_json(f.feature/'manifest.json'); manifest['feature_identity_sha256']=canonical_sha256(identity)
        manifest['partitions']={s:[{'path':'MUST_NOT_READ'}] for s in ('fit','dev_select','dev_policy')}
        manifest['partitions']['dev_cal']=[{'path':relative,'manifest_sha256':canonical_sha256(shard),'summary':shard['summary']}]
        replace_json(f.feature/'manifest.json',manifest)
        self.policy=deepcopy(POLICY); self.policy['feature_manifest_sha256']=canonical_sha256(manifest)
        for name in runner.CODE_FILES:
            target=self.repo/'ml/scripts'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(REPO/'ml/scripts'/name,target)
        with redirect_stdout(StringIO()): self.tasks,self.inputs=runner.verify_inputs(self.repo,self.policy,self.prompts)
        self.root=self.repo/runner.ROOT; self.root.mkdir()

    def produce(self,task):
        # Existing-candidate record schema, deterministic synthetic coordinates.
        raw=[]
        for row in range(task['begin'],task['end']):
            a=(row-task['begin'])*10; c=saved_fixture.candidate(a,a+5,score=5.,row=row)
            c['text']=task['context'][a:a+5]; raw.append(c)
        return raw,[1]*3

    def invoke(self,full=True):
        with ExitStack() as stack:
            for name,value in [('read_policy',self.policy),('execution',{'device':'cpu','batch_size':1}),
                               ('verify_bundle',({}, {}, self.prompts)),('verify_freeze',None),('verify_ignored_assets',None),
                               ('now_ist',datetime(2026,10,29,tzinfo=runner.INDIA))]:
                stack.enter_context(patch.object(runner,name,return_value=value))
            stack.enter_context(patch.object(runner,'TorchBackend',return_value=SimpleNamespace(model=object(),device=torch.device('cpu'))))
            stack.enter_context(patch.object(runner,'infer_question',side_effect=lambda model,task,*args:self.produce(task)))
            stack.enter_context(redirect_stdout(StringIO()))
            return runner.run(self.repo,device='cpu',full=full)

    def test_only_dev_cal_files_are_read(self):
        observed=[]; real=runner.read_json
        def guarded(path):
            observed.append(Path(path).as_posix())
            self.assertNotIn('MUST_NOT_READ',str(path))
            self.assertNotIn(Path(path).name,('dev_policy.json','dev_select.json','fit.json'))
            return real(path)
        with patch.object(runner,'read_json',side_effect=guarded),redirect_stdout(StringIO()):
            tasks,inputs=runner.verify_inputs(self.repo,self.policy,self.prompts)
        self.assertEqual(len(tasks),3); self.assertEqual(inputs['coverage']['windows'],9)
        self.assertTrue(any(p.endswith('dev_cal.json') for p in observed))

    def test_corrupted_feature_array_rejected(self):
        with (self.directory/'offsets.npy').open('ab') as out: out.write(b'x')
        with self.assertRaises(ValueError): runner.verify_inputs(self.repo,self.policy,self.prompts)

    def test_wrong_question_prompt_rejected(self):
        with self.assertRaisesRegex(ValueError,'prompt'):
            runner.verify_inputs(self.repo,self.policy,{'c':'changed'})

    def test_changed_partition_rejected(self):
        p=self.repo/runner.FROZEN/'dev_cal.json'; value=read_json(p); value['partition']='dev_policy'; replace_json(p,value)
        with self.assertRaisesRegex(ValueError,'membership'): runner.verify_inputs(self.repo,self.policy,self.prompts)

    def test_wrong_feature_manifest_pin_rejected(self):
        p=deepcopy(self.policy); p['feature_manifest_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'feature manifest'): runner.verify_inputs(self.repo,p,self.prompts)

    def test_collect_pilot_resume_and_never_repeat_inference(self):
        with redirect_stdout(StringIO()):
            complete,records,new=runner.collect(self.root,self.tasks,'run',self.produce,2)
            self.assertFalse(complete); self.assertEqual((len(records),new),(2,2))
            with patch.object(self,'produce',wraps=self.produce) as producer:
                complete,records,new=runner.collect(self.root,self.tasks,'run',producer,None)
            self.assertTrue(complete); self.assertEqual((len(records),new,producer.call_count),(3,1,1))
            with patch.object(self,'produce',side_effect=AssertionError('no repeated inference')):
                self.assertTrue(runner.collect(self.root,self.tasks,'run',self.produce,None)[0])

    def test_actual_inference_helper_uses_all_windows_eval_and_no_grad(self):
        model=saved_fixture.FixedModel()
        def producer(task):
            return runner.infer_question(model,task,self.f.arrays,torch.device('cpu'),2)
        with redirect_stdout(StringIO()):
            complete,_,new=runner.collect(self.root,self.tasks,'run',producer,None)
        self.assertTrue(complete); self.assertEqual(new,3)
        self.assertEqual(sum(n for n,_,_ in model.calls),9)
        self.assertTrue(all(not training and not grad for _,training,grad in model.calls))
        for i in range(3):
            record=read_json(self.root/'questions'/f'{i:06d}.json')
            self.assertEqual(len(record['payload']['window_counts']),3)

    def test_interruption_preserves_completed_questions_and_resume(self):
        def interrupted(task):
            if task['question_id']=='q1': raise KeyboardInterrupt()
            return self.produce(task)
        with self.assertRaises(KeyboardInterrupt): runner.collect(self.root,self.tasks,'run',interrupted,None)
        before=(self.root/'questions/000000.json').read_bytes()
        with redirect_stdout(StringIO()):
            complete,_,new=runner.collect(self.root,self.tasks,'run',self.produce,None)
        self.assertTrue(complete); self.assertEqual(new,2)
        self.assertEqual((self.root/'questions/000000.json').read_bytes(),before)

    def test_corrupt_later_saved_record_fails_before_new_inference(self):
        with redirect_stdout(StringIO()): runner.collect(self.root,self.tasks,'run',self.produce,None)
        (self.root/'questions/000000.json').unlink()
        p=self.root/'questions/000002.json'; record=read_json(p); record['payload_sha256']='wrong'; replace_json(p,record)
        with patch.object(self,'produce',side_effect=AssertionError('must verify before infer')):
            with self.assertRaisesRegex(ValueError,'checksum'): runner.collect(self.root,self.tasks,'run',self.produce,None)

    def test_foreign_records_and_changed_identity_rejected(self):
        (self.root/'questions').mkdir(); atomic_json(self.root/'questions/foreign.json',{})
        with self.assertRaisesRegex(ValueError,'Foreign'): runner.collect(self.root,self.tasks,'run',self.produce,None)
        (self.root/'questions/foreign.json').unlink()
        with redirect_stdout(StringIO()): runner.collect(self.root,self.tasks,'run',self.produce,2)
        with self.assertRaisesRegex(ValueError,'identity'): runner.collect(self.root,self.tasks,'different',self.produce,None)

    def test_source_offsets_and_gold_labels_created_after_selection(self):
        with redirect_stdout(StringIO()): runner.collect(self.root,self.tasks,'run',self.produce,None)
        before=deepcopy(self.tasks)
        rows,report=runner.labeled_rows(self.tasks,self.root,'run')
        self.assertEqual(self.tasks,before); self.assertEqual(len(rows),9)
        self.assertEqual(report['all_selected_anchored']['micro']['gold'],3)
        self.assertEqual([r['label'] for r in rows[:3]],[1,1,0])
        self.assertTrue(all(r['start']<r['end'] and r['source_sha256'] for r in rows))

    def test_label_is_overlap_eligibility_not_threshold_dependent_assignment(self):
        tasks=deepcopy(self.tasks); tasks[0]['gold']=[{'start':0,'end':10}]
        def produce(t):
            raw,counts=self.produce(t)
            if t['question_id']=='q0':
                raw=raw[:2]; raw[1].update(start=5,end=10,text=t['context'][5:10]); counts=[1,1,0]
            return raw,counts
        with redirect_stdout(StringIO()): runner.collect(self.root,tasks,'run',produce,None)
        rows,report=runner.labeled_rows(tasks,self.root,'run')
        qrows=[r for r in rows if r['question_id']=='q0']
        self.assertEqual([r['label'] for r in qrows],[1,1])
        self.assertEqual(report['questions'][0]['anchored_counts']['tp'],1)

    def test_question_truncation_and_boundary_exclude_whole_question_only_from_fit(self):
        tasks=deepcopy(self.tasks); tasks[0]['original_question_tokens']=65
        def produce(t):
            raw,counts=self.produce(t)
            if t['question_id']=='q1': raw[0]['boundary_review']=True
            return raw,counts
        with redirect_stdout(StringIO()): runner.collect(self.root,tasks,'run',produce,None)
        rows,report=runner.labeled_rows(tasks,self.root,'run')
        self.assertEqual(len(rows),3); self.assertEqual({r['question_id'] for r in rows},{'q2'})
        self.assertEqual(report['processing_incomplete_questions'],2)
        self.assertEqual(report['all_selected_anchored']['micro']['predicted'],9)
        self.assertEqual(report['calibration_eligible_anchored_all_gold_denominator']['micro']['gold'],3)

    def test_zero_candidates_keep_gold_denominator_and_no_absence(self):
        with redirect_stdout(StringIO()): runner.collect(self.root,self.tasks,'run',lambda t:([],[0]*3),None)
        rows,report=runner.labeled_rows(self.tasks,self.root,'run')
        self.assertEqual(rows,[]); self.assertEqual(report['zero_candidate_questions'],3)
        self.assertEqual(report['all_selected_anchored']['micro']['fn'],3)
        self.assertNotIn('absent',str(report))

    def test_pipeline_partial_has_no_fit_then_full_and_verified_cache(self):
        with patch.object(runner,'assess',side_effect=AssertionError('partial must not fit')):
            self.assertIsNone(self.invoke(full=False))
        self.assertFalse((self.root/'results').exists())
        self.assertTrue((self.root/'identity.json').is_file())
        report=self.invoke(full=True)
        self.assertEqual(report['assessment']['status'],'unvalidated')
        self.assertFalse(report['model_weight_training_performed']); self.assertFalse(report['operating_policy_selected'])
        with patch.object(runner,'collect',side_effect=AssertionError('cache must not collect')):
            with patch.object(runner,'assess',side_effect=AssertionError('cache must not refit')):
                self.assertEqual(self.invoke(),report)

    def test_identity_written_before_inference_and_no_model_optimizer_loaded(self):
        original=self.produce
        def checked(task):
            self.assertTrue((self.root/'identity.json').is_file())
            return original(task)
        with patch.object(self,'produce',side_effect=checked),patch.object(torch,'load',side_effect=AssertionError('no training checkpoint')):
            self.invoke()

    def test_source_files_unchanged_after_full_assessment(self):
        paths=[*self.f.feature.rglob('*'),*(self.repo/runner.FROZEN).rglob('*')]
        before={p:p.read_bytes() for p in paths if p.is_file()}
        self.invoke()
        self.assertTrue(all(p.read_bytes()==value for p,value in before.items()))

    def test_verified_cache_remains_readable_after_deadline(self):
        expected=self.invoke()
        identity=read_json(self.root/'identity.json')
        with ExitStack() as stack:
            for name,value in [('read_policy',self.policy),('execution',identity['execution']),
                               ('verify_bundle',({}, {}, self.prompts)),('verify_freeze',None),('verify_ignored_assets',None),
                               ('now_ist',datetime(2026,11,3,tzinfo=runner.INDIA))]:
                stack.enter_context(patch.object(runner,name,return_value=value))
            stack.enter_context(patch.object(runner,'collect',side_effect=AssertionError('no new collection')))
            stack.enter_context(redirect_stdout(StringIO()))
            self.assertEqual(runner.run(self.repo,device='cpu',full=True),expected)

    def test_result_finishing_late_is_explicitly_unvalidated(self):
        times=iter([datetime(2026,11,2,23,59,tzinfo=runner.INDIA),datetime(2026,11,3,tzinfo=runner.INDIA)])
        with ExitStack() as stack:
            for name,value in [('read_policy',self.policy),('execution',{'device':'cpu'}),
                               ('verify_bundle',({}, {}, self.prompts)),('verify_freeze',None),('verify_ignored_assets',None)]:
                stack.enter_context(patch.object(runner,name,return_value=value))
            stack.enter_context(patch.object(runner,'now_ist',side_effect=lambda:next(times)))
            stack.enter_context(patch.object(runner,'TorchBackend',return_value=SimpleNamespace(model=object(),device=torch.device('cpu'))))
            stack.enter_context(patch.object(runner,'infer_question',side_effect=lambda model,task,*args:self.produce(task)))
            stack.enter_context(redirect_stdout(StringIO()))
            report=runner.run(self.repo,device='cpu',full=True)
        self.assertEqual(report['assessment']['status'],'unvalidated')
        self.assertIn('completed_by_deadline',report['assessment']['failed_checks'])

    def test_changed_runner_code_preserves_existing_outputs(self):
        self.invoke(full=False)
        p=self.repo/'ml/scripts/cuad_calibration.py'; p.write_text(p.read_text()+'\n# changed\n')
        with self.assertRaisesRegex(ValueError,'Existing file differs'): self.invoke()
        self.assertTrue((self.root/'questions/000000.json').is_file())

    def test_damaged_complete_report_or_raw_record_not_silently_regenerated(self):
        self.invoke()
        p=self.root/'results/report.json'; original=p.read_bytes(); p.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError,'damaged'): self.invoke()
        p.write_bytes(original)
        q=self.root/'questions/000002.json'; q.write_bytes(q.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'damaged'): self.invoke()

    def test_new_run_after_deadline_refused_without_loading_inputs(self):
        with patch.object(runner,'now_ist',return_value=datetime(2026,11,3,tzinfo=runner.INDIA)):
            with patch.object(runner,'execution',side_effect=AssertionError('must stop early')):
                with self.assertRaisesRegex(ValueError,'deadline passed'): runner.run(REPO)

    def test_config_cannot_be_retuned(self):
        path=self.repo/runner.CONFIG; p=deepcopy(POLICY); p['method']['l2']=.1; atomic_json(path,p)
        with self.assertRaisesRegex(ValueError,'config changed'): runner.read_policy(self.repo)


if __name__=='__main__':
    unittest.main()
