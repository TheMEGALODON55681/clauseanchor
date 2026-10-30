"""Synthetic final-run checks; pinned evaluator/decoder code, no CUAD examples or trained weights."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import hashlib
import json
import shutil
import sys
import unittest
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'ml/scripts'))
import run_cuad_final_evaluation as runner
import cuad_final_evaluation as final
import cuad_final_engines as engines
from assess_cuad_calibration import INDIA
from clauseanchor_core import from_dict, to_dict, validate_result
from clauseanchor_core.artifacts import canonical_sha256, read_json
from cuad_candidate_policy import project_result
from evaluate_cuad_baseline import load_reference, matches
from prepare_cuad_baseline import CONFIG as BASELINE_CONFIG, REFERENCE_DIR, MODEL_DIR
from run_cuad_baseline import atomic_json
from cuad_checkpoints import replace_json

CONFIG=read_json(REPO/runner.CONFIG)
POLICY=read_json(REPO/'ml/configs/cuad_candidate_policy_v1.json')
QUESTIONS=[q for q in read_json(REPO/'ml/configs/category_questions.json')['questions'] if q['cuad_annotated']]
NOW=datetime(2026,10,29,tzinfo=INDIA)


def spec(path):
    return {'size_bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


class Tokenizer:
    def context(self,text): return SimpleNamespace(ids=list(range(1000))),[]
    def question(self,text):
        n=65 if 'Governing Law' in text else 8
        return SimpleNamespace(ids=list(range(min(n,64)))),n


def fixture():
    docs=[]
    for i in range(5):
        source=f'alpha beta ACME 🙂\r\nRepeated. Repeated. {i}'; title=f'doc{i}'
        qas=[]
        for j,q in enumerate(QUESTIONS):
            label='Parties' if q['category_id']=='cuad.parties' else str(j)
            answers=[{'answer_start':0,'text':'alpha'}] if j==0 else []
            if j==1: answers=[{'answer_start':11,'text':'ACME'}]
            qas.append({'id':title+'__'+label,'question':q['question'],'answers':answers,'is_impossible':not answers})
        docs.append({'title':title,'paragraphs':[{'context':source,'qas':qas}]})
    gids=['cuad-exact-v1:'+canonical_sha256([d['paragraphs'][0]['context']]) for d in docs]
    fs=[{'group_ids':[gids[0],'train-group']},{'group_ids':[gids[1],gids[2]]}]
    for f in fs: f['family_id']=final.family_id(f['group_ids'])
    families={'families':fs,'title_decisions':[{'decision':'unresolved','group_ids':[gids[3],gids[4]]}]}
    config=deepcopy(CONFIG); config.update(official_test_documents=5,official_test_questions=205,
        official_test_answer_records=10,sensitivity_documents=4,confirmed_overlap_excluded_documents=1,unresolved_retained_documents=2)
    tasks,coverage=final.prepare_tasks({'data':docs},families,QUESTIONS,Tokenizer(),config)
    return {'data':docs},families,config,tasks,coverage


def candidate_result(t,empty=False,boundary=False):
    selected=[] if empty else [{'start':0,'end':5,'text':t['context'][:5],'margin':4.,'boundary_review':boundary}]
    return to_dict(project_result({**t,'begin':0,'end':t['windows_total']},selected,CONFIG['artifact_manifest_sha256']))


def official_result(t):
    return {'windows':4,'prediction':'alpha','candidates':[
        {'text':'alpha','probability':.8,'start_logit':2.,'end_logit':2.},
        {'text':'','probability':.2,'start_logit':1.,'end_logit':1.}], 'null_score_difference':-2.}


class InputTests(unittest.TestCase):
    def setUp(self): self.test,self.families,self.config,self.tasks,self.coverage=fixture()

    def test_config_is_pinned_and_has_two_fixed_non_promoting_arms(self):
        self.assertEqual(canonical_sha256(CONFIG),runner.CONFIG_PIN)
        self.assertEqual(set(CONFIG['arms']),set(final.ARMS))
        self.assertFalse(CONFIG['training_calibration_decoder_or_policy_selection'])
        self.assertFalse(CONFIG['candidate_settings']['accepted_findings'])
        self.assertEqual(CONFIG['official_settings']['precision'],'fp32')

    def test_sensitivity_retains_test_only_family_and_unresolved(self):
        self.assertEqual(self.coverage['excluded_confirmed_overlap_titles'],['doc0'])
        self.assertEqual(self.coverage['retained_unresolved_titles'],['doc3','doc4'])
        self.assertEqual({t['title'] for t in self.tasks if t['in_sensitivity']},{'doc1','doc2','doc3','doc4'})
        self.assertEqual(self.coverage['families'],4)

    def test_complete_grid_source_hash_windows_and_original_gold(self):
        self.assertEqual(len(self.tasks),205)
        self.assertEqual(self.coverage['gold_records'],10)
        t=self.tasks[0]; self.assertEqual(t['context'][t['gold'][0]['start']:t['gold'][0]['end']],'alpha')
        self.assertEqual(t['source_sha256'],hashlib.sha256(t['context'].encode()).hexdigest())
        self.assertEqual(t['task_sha256'],canonical_sha256({k:v for k,v in t.items() if k!='task_sha256'}))
        self.assertTrue(all(t['windows_total']>1 for t in self.tasks))

    def test_tasks_do_not_modify_original_source_or_annotations(self):
        before=deepcopy((self.test,self.families))
        final.prepare_tasks(self.test,self.families,QUESTIONS,Tokenizer(),self.config)
        self.assertEqual((self.test,self.families),before)

    def test_missing_duplicate_prompt_and_bad_source_offset_fail(self):
        for change in ['missing','duplicate','prompt','offset']:
            data=deepcopy(self.test); qs=data['data'][0]['paragraphs'][0]['qas']
            if change=='missing': qs.pop()
            elif change=='duplicate': qs.append(deepcopy(qs[0]))
            elif change=='prompt': qs[0]['question']='unknown'
            else: qs[0]['answers'][0]['answer_start']=1
            with self.subTest(change=change),self.assertRaises(ValueError):
                final.prepare_tasks(data,self.families,QUESTIONS,Tokenizer(),self.config)

    def test_changed_sensitivity_counts_and_family_identity_fail(self):
        p=deepcopy(self.config); p['sensitivity_documents']=5
        with self.assertRaises(ValueError): final.prepare_tasks(self.test,self.families,QUESTIONS,Tokenizer(),p)
        f=deepcopy(self.families); f['families'][0]['family_id']='changed'
        with self.assertRaises(ValueError): final.prepare_tasks(self.test,f,QUESTIONS,Tokenizer(),self.config)

    def test_reference_input_never_reads_gold(self):
        class Guard(dict):
            def __getitem__(self,k):
                if k=='gold': raise AssertionError('gold passed to inference')
                return super().__getitem__(k)
        result=final.inference_input(Guard(self.tasks[0]))
        q=result['data'][0]['paragraphs'][0]['qas'][0]
        self.assertEqual(set(q),{'id','question'})

    def test_candidate_engine_calls_actual_protocol_with_unchanged_source(self):
        t=self.tasks[0]; calls=[]
        class Analyzer:
            def analyze(self,text,**kw):
                calls.append((text,kw)); return from_dict(candidate_result(t))
        engine=object.__new__(engines.CandidateEngine); engine.analyzer=Analyzer()
        result=engine(t); text,args=calls[0]
        self.assertEqual(text,t['context']); self.assertEqual(args['category_ids'],(t['category_id'],))
        self.assertEqual(args['text_sha256'],t['source_sha256']); self.assertTrue(args['context'].parser_complete)
        self.assertNotIn('gold',args); validate_result(from_dict(result),t['context'])


class RecordAndMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Existing hash-pinned evaluator code only. No dataset/model is opened.
        cls.reference=load_reference(REPO,read_json(REPO/BASELINE_CONFIG))
    def setUp(self): _,_,_,self.tasks,_=fixture(); self.t=self.tasks[0]
    def check(self,t,value,arm='candidate'):
        record=final.make_record(t,'a'*64,arm,value)
        return final.validate_record(record,t,'a'*64,arm,CONFIG['artifact_manifest_sha256'])

    def test_candidate_record_strict_source_contract_and_roundtrip(self):
        value=candidate_result(self.t); self.assertEqual(self.check(self.t,value),value)
        changed=deepcopy(value); changed['categories'][0]['clauses'][0]['span']['text']='wrong'
        with self.assertRaisesRegex(ValueError,'source slice'): self.check(self.t,changed)

    def test_null_candidate_never_accepted_and_no_output_never_absent(self):
        value=candidate_result(self.t); value['categories'][0]['clauses'][0]['status']='accepted'
        with self.assertRaises(ValueError): self.check(self.t,value)
        value=candidate_result(self.t,empty=True); self.assertEqual(self.check(self.t,value)['categories'][0]['status'],'abstained')
        value['categories'][0]['status']='absent'
        with self.assertRaises(ValueError): self.check(self.t,value)

    def test_incomplete_question_keeps_candidates_and_flags(self):
        t=next(t for t in self.tasks if t['original_question_tokens']>64)
        value=self.check(t,candidate_result(t,boundary=True)); c=value['categories'][0]
        self.assertFalse(c['search_complete']); self.assertEqual(len(c['clauses']),1)
        value['categories'][0]['windows_done']-=1
        with self.assertRaises(ValueError): self.check(t,value)

    def test_record_cannot_change_arm_run_task_or_payload(self):
        r=final.make_record(self.t,'a'*64,'candidate',candidate_result(self.t))
        for name,change in [('run_sha256','b'*64),('arm','official'),('task_sha256','b'*64)]:
            x=deepcopy(r); x['payload'][name]=change; x['payload_sha256']=canonical_sha256(x['payload'])
            with self.assertRaises(ValueError): final.validate_record(x,self.t,'a'*64,'candidate',CONFIG['artifact_manifest_sha256'])
        r['payload']['result']['mode']='stub'
        with self.assertRaises(ValueError): final.validate_record(r,self.t,'a'*64,'candidate',CONFIG['artifact_manifest_sha256'])

    def test_reference_softmax_stays_outside_core_and_malformed_output_fails(self):
        self.check(self.t,official_result(self.t),'official')
        bad=official_result(self.t); bad['candidates'][0]['probability']=.7
        with self.assertRaises(ValueError): self.check(self.t,bad,'official')
        bad=official_result(self.t); bad['windows']=0
        with self.assertRaises(ValueError): self.check(self.t,bad,'official')

    def test_anchored_all_gold_retained_with_empty_outputs(self):
        ts=self.tasks[:41]; cores=[candidate_result(t,empty=True) for t in ts]
        result=final.anchored(ts,cores,POLICY); micro=result['candidate_metrics']['micro']
        self.assertEqual(micro['fn'],2); self.assertIsNone(micro['precision']); self.assertEqual(micro['recall'],0)
        self.assertFalse(result['absence']['enabled']); self.assertIsNone(result['absence']['error_rate'])
        self.assertIsNone(result['accepted_metrics']['micro']['precision'])

    def test_original_reference_parity_and_separated_anchored_comparison(self):
        tasks=self.tasks
        results={'candidate':[candidate_result(t) for t in tasks],'official':[official_result(t) for t in tasks]}
        released={t['question_id']:official_result(t)['candidates'] for t in tasks}
        before=deepcopy((results,released))
        scores,curves=final.score_all(tasks,results,released,self.reference,POLICY)
        self.assertEqual((results,released),before)
        self.assertEqual(scores['known_overlap_sensitivity']['documents'],4)
        for s in scores.values():
            self.assertTrue(all(v==0 for v in s['official_clean_minus_released'].values()))
            for value in s['official_reference_comparison'].values(): self.assertLessEqual(value['maximum_absolute_parity_error'],1e-12)
            self.assertFalse(s['frozen_candidate_pipeline_anchored']['accepted_findings_enabled'])
        curve=curves['full_official_test']['clean_checkpoint_reference_path']
        self.assertEqual(len(curve['thresholds']),101); self.assertEqual(len(curve['precisions']),102)

    def test_official_parties_and_duplicate_answer_credit_remain_different_from_anchored(self):
        self.assertTrue(matches('ACME','ACME unrelated extra tokens here',True))
        self.assertFalse(matches('ACME','ACME unrelated extra tokens here',False))
        from evaluate_cuad_baseline import score_predictions,reference_score,assert_parity
        gold={'x__Parties':['ACME','ACME']}; pred={'x__Parties':[{'text':'ACME unrelated extra tokens here','probability':1.}]}
        a=score_predictions(gold,pred); b=reference_score(self.reference,gold,pred)
        self.assertEqual(assert_parity(a,b),0); self.assertEqual(a['counts'][-1]['tp'],2)

    def test_partial_arm_cannot_receive_test_scores(self):
        with self.assertRaisesRegex(ValueError,'both|Both'):
            final.score_all(self.tasks,{'candidate':[],'official':[]},{},self.reference,POLICY)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory(); self.addCleanup(temp.cleanup); self.repo=Path(temp.name)
        self.test,self.families,self.config,self.tasks,self.coverage=fixture()
        self.root=self.repo/runner.ROOT
        self.released={t['question_id']:official_result(t)['candidates'] for t in self.tasks}
        self.baseline=read_json(REPO/BASELINE_CONFIG)
        self.reference=load_reference(REPO,self.baseline)
        for name in runner.CODE_FILES:
            path=self.repo/'ml/scripts'/name; path.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(REPO/'ml/scripts'/name,path)
        self.inputs={'coverage':self.coverage}; self.calls=CounterLike()
    def engine(self,arm):
        outer=self
        class Engine:
            def __call__(self,t):
                outer.calls[arm]+=1
                if outer.calls.get('raise_arm')==arm and outer.calls[arm]==2: raise KeyboardInterrupt()
                return candidate_result(t) if arm=='candidate' else official_result(t)
        return Engine()
    def invoke(self,full=True,now=NOW,**overrides):
        with ExitStack() as stack:
            defaults={'read_config':self.config,'verify_policy':(POLICY,{'frozen':True}),
                'initialize_runtime':(None,{'fixed':'runtime'}),'verify_inputs':(self.tasks,self.released,self.baseline,self.inputs),
                'verify_ignored_assets':None,'now_ist':now,'load_reference':self.reference}
            defaults.update(overrides)
            for k,v in defaults.items(): stack.enter_context(patch.object(runner,k,return_value=v))
            stack.enter_context(patch.object(runner,'CandidateEngine',side_effect=lambda *a:self.engine('candidate')))
            stack.enter_context(patch.object(runner,'OfficialEngine',side_effect=lambda *a:self.engine('official')))
            stack.enter_context(patch.object(runner,'configure_arm'))
            stack.enter_context(patch.object(runner,'release_engine'))
            stack.enter_context(redirect_stdout(StringIO()))
            return runner.run(self.repo,'cpu',full)

    def test_pilot_then_full_reuses_both_arms_and_records(self):
        with patch.object(runner,'score_all',side_effect=AssertionError('no partial scoring')): self.assertIsNone(self.invoke(full=False))
        self.assertEqual(self.calls['candidate'],2); self.assertEqual(self.calls['official'],2)
        first=(self.root/'candidate/questions/000000.json').read_bytes()
        result=self.invoke(); self.assertEqual(result['current_invocation']['candidate']['new_questions'],203)
        self.assertEqual(self.calls['candidate'],205); self.assertEqual(self.calls['official'],205)
        self.assertEqual((self.root/'candidate/questions/000000.json').read_bytes(),first)
        self.assertFalse(result['training_calibration_decoder_or_policy_selection_performed'])
        self.assertFalse(result['accepted_findings_enabled'])

    def test_interruption_preserves_finished_question_and_resumes(self):
        self.calls['raise_arm']='candidate'
        with self.assertRaises(KeyboardInterrupt): self.invoke(full=False)
        self.assertTrue((self.root/'candidate/questions/000000.json').exists())
        self.assertFalse((self.root/'candidate/questions/000001.json').exists())
        self.calls['raise_arm']=None
        result=self.invoke(); self.assertEqual(result['current_invocation']['candidate']['new_questions'],204)

    def test_saved_record_in_other_arm_checked_before_any_new_inference(self):
        self.invoke(full=False); before=dict(self.calls)
        path=self.root/'official/questions/000000.json'; path.write_text('{}')
        with self.assertRaises(ValueError): self.invoke()
        self.assertEqual(self.calls,before)

    def test_identity_published_before_first_model_call(self):
        original=self.engine
        def checked(arm):
            self.assertTrue((self.root/'identity.json').exists()); return original(arm)
        with patch.object(self,'engine',side_effect=checked): self.invoke(full=False)

    def test_completed_cache_reuses_without_scoring_or_inference_after_deadline(self):
        report=self.invoke(); before=dict(self.calls)
        with patch.object(runner,'score_all',side_effect=AssertionError('no scoring')):
            self.assertEqual(self.invoke(now=datetime(2026,11,6,tzinfo=INDIA)),report)
        self.assertEqual(self.calls,before)

    def test_late_start_refused_before_opening_test(self):
        with patch.object(runner,'read_config',return_value=self.config),patch.object(runner,'now_ist',return_value=datetime(2026,11,6,tzinfo=INDIA)):
            with patch.object(runner,'verify_inputs',side_effect=AssertionError('must stop first')):
                with self.assertRaisesRegex(ValueError,'deadline passed'): runner.run(self.repo)

    def test_late_finish_is_disclosed_without_policy_change(self):
        original=runner.score_all
        def late(*a):
            runner.now_ist.return_value=datetime(2026,11,6,tzinfo=INDIA); return original(*a)
        with patch.object(runner,'score_all',side_effect=late): result=self.invoke()
        self.assertFalse(result['completed_by_deadline']); self.assertFalse(result['accepted_findings_enabled'])

    def test_changed_code_identity_rejected_preserving_records(self):
        self.invoke(full=False); path=self.root/'candidate/questions/000000.json'; before=path.read_bytes()
        code=self.repo/'ml/scripts/cuad_final_engines.py'; code.write_bytes(code.read_bytes()+b'\n#changed\n')
        with self.assertRaisesRegex(ValueError,'Existing file differs'): self.invoke()
        self.assertEqual(path.read_bytes(),before)

    def test_missing_foreign_or_damaged_cached_files_fail(self):
        self.invoke(); p=self.root/'results/report.json'; raw=p.read_bytes(); p.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError,'damaged'): self.invoke()
        p.write_bytes(raw); foreign=self.root/'candidate/questions/999999.json'; foreign.write_text('{}')
        with self.assertRaisesRegex(ValueError,'foreign'): self.invoke()
        foreign.unlink(); (self.root/'official/questions/000001.json').unlink()
        with self.assertRaisesRegex(ValueError,'Missing'): self.invoke()

    def test_changed_config_digest_is_rejected(self):
        path=self.repo/runner.CONFIG; path.parent.mkdir(parents=True,exist_ok=True)
        value=deepcopy(CONFIG); value['candidate_settings']['accepted_findings']=True; atomic_json(path,value)
        with self.assertRaisesRegex(ValueError,'declaration changed'): runner.read_config(self.repo)

    def test_policy_freeze_checked_before_test_open(self):
        with patch.object(runner,'read_config',return_value=self.config),patch.object(runner,'now_ist',return_value=NOW):
            with patch.object(runner,'verify_policy',side_effect=ValueError('frozen policy changed')):
                with patch.object(runner,'verify_inputs',side_effect=AssertionError('test opened too early')):
                    with self.assertRaisesRegex(ValueError,'frozen policy'): runner.run(self.repo)


class CounterLike(dict):
    def __missing__(self,k): return 0


class VerificationTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory(); self.addCleanup(temp.cleanup); self.repo=Path(temp.name)
        self.test,self.families,self.config,self.tasks,self.coverage=fixture()
        self.base=read_json(REPO/BASELINE_CONFIG)
        path=self.repo/self.base['official_test']['path']; atomic_json(path,self.test)
        self.base['official_test'].update(spec(path))
        model=self.repo/MODEL_DIR/'roberta-base'; model.mkdir(parents=True)
        for name in ('vocab.json','merges.txt','tokenizer_config.json','special_tokens_map.json','config.json'):
            p=model/name; p.write_text('{"fixture":true}'); self.base['members'][name]=spec(p)
        p=model/'nbest_predictions_.json'
        atomic_json(p,{t['question_id']:official_result(t)['candidates'] for t in self.tasks}); self.base['members'][p.name]=spec(p)
        dest=self.repo/REFERENCE_DIR; dest.mkdir(parents=True)
        for name in ('utils.py','evaluate.py','category_descriptions.csv'): shutil.copyfile(REPO/REFERENCE_DIR/name,dest/name)
        atomic_json(self.repo/BASELINE_CONFIG,self.base); atomic_json(self.repo/runner.FAMILY_PATH,self.families)
        self.config['baseline_source_config_sha256']=canonical_sha256(self.base)
        self.config['family_manifest_sha256']=canonical_sha256(self.families)
        self.catalogue=read_json(REPO/'ml/configs/catalogue.json')
        self.prompts={q['category_id']:q['question'] for q in QUESTIONS}
    def verify(self):
        with patch.object(runner,'FeatureTokenizer',return_value=Tokenizer()),patch.object(runner,'verify_bundle',return_value=({},self.catalogue,self.prompts)):
            return runner.verify_inputs(self.repo,self.config)

    def test_only_official_test_examples_are_read_no_training_or_dev(self):
        opened=[]; real=runner.read_json
        def guard(path):
            opened.append(Path(path).as_posix())
            self.assertNotIn(Path(path).name,('train_separate_questions.json','CUAD_v1.json','fit.json','dev_cal.json','dev_policy.json','dev_select.json'))
            return real(path)
        with patch.object(runner,'read_json',side_effect=guard): tasks,released,_,evidence=self.verify()
        self.assertEqual(len(tasks),205); self.assertEqual(len(released),205)
        self.assertTrue(any(p.endswith('/official/test.json') for p in opened))
        self.assertEqual(evidence['coverage'],self.coverage)

    def test_corrupt_test_tokenizer_and_decoder_assets_fail(self):
        for p in [self.repo/self.base['official_test']['path'],self.repo/MODEL_DIR/'roberta-base/vocab.json',self.repo/REFERENCE_DIR/'utils.py']:
            raw=p.read_bytes();p.write_bytes(raw+b' ')
            with self.subTest(path=p.name),self.assertRaises(ValueError): self.verify()
            p.write_bytes(raw)

    def test_extra_reference_tokenizer_file_fails(self):
        (self.repo/MODEL_DIR/'roberta-base/tokenizer.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Unpinned'): self.verify()

    def test_wrong_family_or_source_config_pin_fails(self):
        for key in ('family_manifest_sha256','baseline_source_config_sha256'):
            original=self.config[key]; self.config[key]='0'*64
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'declaration changed'): self.verify()
            self.config[key]=original

    def policy_fixture(self):
        declaration=deepcopy(POLICY)
        path=self.repo/'ml/scripts/evaluate_candidate_policy.py';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('# frozen fixture\n')
        identity={'policy':declaration,'code_sha256_lf':{path.name:runner.code_hash(path)}}
        policy={'identity_sha256':canonical_sha256(identity),'artifact_manifest_sha256':CONFIG['artifact_manifest_sha256'],
            'decision':'retain_existing_candidate_only_v0','confidence':None,'accepted_findings_enabled':False,
            'absence_enabled':False,'runtime_changes':False,'measurement_complete':True}
        report={'identity_sha256':canonical_sha256(identity),'operating_policy_sha256':canonical_sha256(policy),'measured_by_deadline':True}
        atomic_json(self.repo/'ml/configs/cuad_candidate_policy_v1.json',declaration)
        root=self.repo/runner.POLICY_ROOT
        for relative,value in [('identity.json',identity),('results/report.json',report),('results/operating_policy.json',policy)]: atomic_json(root/relative,value)
        config=deepcopy(CONFIG);config.update(policy_identity_sha256=canonical_sha256(identity),policy_report_sha256=canonical_sha256(report),operating_policy_sha256=canonical_sha256(policy))
        return config,path

    def test_policy_closed_evidence_verified_and_changed_code_rejected(self):
        config,path=self.policy_fixture(); declaration,evidence=runner.verify_policy(self.repo,config)
        self.assertEqual(declaration,POLICY);self.assertFalse(evidence['candidate_policy']['accepted_findings_enabled'])
        path.write_text('# different\n')
        with self.assertRaisesRegex(ValueError,'producer changed'): runner.verify_policy(self.repo,config)

    def test_changed_policy_report_hash_is_rejected(self):
        config,_=self.policy_fixture(); p=self.repo/runner.POLICY_ROOT/'results/report.json';value=read_json(p)
        value['measured_by_deadline']=False;replace_json(p,value)
        with self.assertRaisesRegex(ValueError,'evidence changed'): runner.verify_policy(self.repo,config)


class RealReferenceEngineTests(unittest.TestCase):
    def test_tiny_random_qa_uses_original_reference_path_all_windows_no_grad(self):
        import torch
        from safetensors.torch import save_file
        from tokenizers import ByteLevelBPETokenizer
        from transformers import RobertaConfig,RobertaForQuestionAnswering,RobertaTokenizer
        with TemporaryDirectory() as folder:
            root=Path(folder); tokdir=root/'tok'; artifact=root/'model'; tokdir.mkdir(); artifact.mkdir()
            bpe=ByteLevelBPETokenizer(); bpe.train_from_iterator(['alpha beta gamma delta ACME contract '*100],
                vocab_size=280,min_frequency=2,special_tokens=['<s>','<pad>','</s>','<unk>','<mask>'])
            bpe.save_model(str(tokdir))
            tok=RobertaTokenizer(vocab_file=str(tokdir/'vocab.json'),merges_file=str(tokdir/'merges.txt'),model_max_length=512)
            tok.save_pretrained(tokdir)
            config=RobertaConfig(vocab_size=len(tok),hidden_size=16,num_hidden_layers=1,num_attention_heads=2,
                                intermediate_size=32,max_position_embeddings=514,num_labels=2)
            model=RobertaForQuestionAnswering(config); config.to_json_file(artifact/'config.json')
            save_file(model.state_dict(),str(artifact/'model.safetensors')); del model
            with patch.object(torch,'load',side_effect=AssertionError('no pickle/released weights')):
                engine=engines.OfficialEngine(artifact,tokdir,REPO/REFERENCE_DIR/'utils.py','cpu')
            self.assertFalse(any(p.requires_grad for p in engine.model.parameters()))
            calls=[]
            def checked(module,inputs):
                self.assertFalse(torch.is_grad_enabled()); self.assertFalse(module.training); calls.append(1)
            hook=engine.model.register_forward_pre_hook(checked)
            task={'title':'tiny','question_id':'tiny__Document Name','question':'Which contract?',
                  'context':'alpha beta gamma delta '*300}
            result=engine(task); hook.remove()
            self.assertGreater(result['windows'],1); self.assertEqual(len(calls),result['windows'])
            self.assertAlmostEqual(sum(c['probability'] for c in result['candidates']),1)
            self.assertTrue(all(p.dtype==torch.float32 for p in engine.model.parameters()))
            self.assertEqual(engine.model.config._attn_implementation,'eager')
            self.assertEqual(set(result),{'windows','prediction','candidates','null_score_difference'})
            engines.release_engine(engine)


if __name__=='__main__': unittest.main()
