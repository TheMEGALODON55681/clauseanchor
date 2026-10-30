"""One frozen final evaluation, two fixed reporting arms, no test-based tuning.

Default: at most two NEW questions per arm; --full resumes both to completion.
No scores until both cover all 4,182 questions. No config/run-name overrides.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from assess_cuad_calibration import code_hash, now_ist
from clauseanchor_core.artifacts import canonical_sha256, file_spec, read_json, require, verify_bundle
from clauseanchor_core._inference import FeatureTokenizer
from cuad_final_evaluation import ARMS, prepare_tasks, make_record, validate_record, score_all
from cuad_final_engines import CandidateEngine, OfficialEngine, configure_arm, release_engine
from evaluate_cuad_baseline import load_reference, FAMILY_PATH
from prepare_cuad_baseline import CONFIG as BASELINE_CONFIG, MODEL_DIR, REFERENCE_DIR, verify_file, verify_ignored_assets, validate_config
from run_cuad_baseline import atomic_json, run_lock, initialize_runtime, CODE_FILES as BASELINE_CODE

CONFIG='ml/configs/cuad_final_evaluation_v1.json'
CONFIG_PIN='49dcbe415aa08384e238bfc4737edd1375d9154e3f95ebb713630c5db2bdeea9'
ROOT='data/processed/cuad/final_evaluation_v1'
ARTIFACT='models/clauseanchor_candidate_v0'
POLICY_ROOT='data/processed/cuad/candidate_policy_v1'
OUTPUTS=('report.json','official_curves.json','predictions.json')
CODE_FILES=tuple(sorted(set(BASELINE_CODE)|{'run_cuad_final_evaluation.py','cuad_final_evaluation.py','cuad_final_engines.py',
    'assess_cuad_calibration.py','cuad_candidate_policy.py','cuad_development.py'}))


def read_config(repo):
    config=read_json(repo/CONFIG)
    require(canonical_sha256(config)==CONFIG_PIN,'Final evaluation declaration changed; no test-based tuning.')
    return config


def verify_policy(repo,config):
    root=repo/POLICY_ROOT
    identity=read_json(root/'identity.json'); report=read_json(root/'results/report.json')
    policy=read_json(root/'results/operating_policy.json')
    require(canonical_sha256(identity)==config['policy_identity_sha256']
            and canonical_sha256(report)==config['policy_report_sha256']
            and canonical_sha256(policy)==config['operating_policy_sha256']
            and report['identity_sha256']==policy['identity_sha256']==canonical_sha256(identity)
            and report['operating_policy_sha256']==canonical_sha256(policy),'Reviewed operating-policy evidence changed.')
    declaration=read_json(repo/'ml/configs/cuad_candidate_policy_v1.json')
    require(declaration==identity['policy'] and canonical_sha256(declaration)==config['policy_config_sha256']
        and policy['artifact_manifest_sha256']==config['artifact_manifest_sha256']
        and policy['decision']=='retain_existing_candidate_only_v0' and policy['confidence'] is None
        and policy['accepted_findings_enabled'] is False and policy['absence_enabled'] is False
        and policy['runtime_changes'] is False and policy['measurement_complete'] is True
        and report['measured_by_deadline'] is True,'Expected the closed candidate-only policy.')
    for name,pin in identity['code_sha256_lf'].items():
        require(code_hash(repo/'ml/scripts'/name)==pin,'Frozen policy producer changed; no silent downstream repair.')
    return declaration,{'identity_sha256':canonical_sha256(identity),'report_sha256':canonical_sha256(report),
        'operating_policy_sha256':canonical_sha256(policy),'candidate_policy':policy}


def verify_inputs(repo,config):
    baseline=read_json(repo/BASELINE_CONFIG); validate_config(baseline)
    families=read_json(repo/FAMILY_PATH)
    require(canonical_sha256(baseline)==config['baseline_source_config_sha256']
            and canonical_sha256(families)==config['family_manifest_sha256'],'Baseline/family declaration changed.')
    expected={k:config['official_settings'][k] for k in baseline['reference_inference_settings']}
    require(expected==baseline['reference_inference_settings'],'Reference inference settings differ.')
    test_path=repo/baseline['official_test']['path']; verify_file(test_path,baseline['official_test'])
    # No original checkpoint/pickle is loaded; only its verified tokenizer and saved predictions.
    model=repo/MODEL_DIR/'roberta-base'
    tokenizer_files=('vocab.json','merges.txt','tokenizer_config.json','special_tokens_map.json','config.json')
    for name in (*tokenizer_files,'nbest_predictions_.json'):
        verify_file(model/name,baseline['members'][name])
    require(not any((model/n).exists() for n in ('added_tokens.json','tokenizer.json')),'Unpinned reference tokenizer assets.')
    for name in ('utils.py','evaluate.py','category_descriptions.csv'):
        verify_file(repo/REFERENCE_DIR/name,baseline['reference_files'][name])
    _,catalogue,prompts=verify_bundle(repo/ARTIFACT,config['artifact_manifest_sha256'])
    tokenizer=FeatureTokenizer(repo/ARTIFACT/'tokenizer')
    test=read_json(test_path)
    tasks,coverage=prepare_tasks(test,families,[{'question':q,'category_id':c} for c,q in prompts.items()],tokenizer,config)
    released=read_json(model/'nbest_predictions_.json')
    require(set(released)=={t['question_id'] for t in tasks},'Released reference IDs differ.')
    evidence={'official_test':baseline['official_test'],'family_manifest_sha256':canonical_sha256(families),
        'baseline_source_config_sha256':canonical_sha256(baseline),
        'released_predictions':baseline['members']['nbest_predictions_.json'],
        'reference_files':baseline['reference_files'],'reference_tokenizer':{n:baseline['members'][n] for n in tokenizer_files},
        'catalogue_support_statuses':{c['id']:c['support_status'] for c in catalogue['categories']},'coverage':coverage}
    return tasks,released,baseline,evidence


def record_paths(root,tasks,arm):
    return [root/arm/'questions'/f'{i:06d}.json' for i in range(len(tasks))]


def preflight_records(root,tasks,run_sha,artifact_sha):
    for arm in ARMS:
        paths=record_paths(root,tasks,arm)
        actual=set((root/arm/'questions').glob('*.json'))
        require(actual<=set(paths),'Foreign final question records; preserve them.')
        for t,path in zip(tasks,paths):
            if path.exists(): validate_record(read_json(path),t,run_sha,arm,artifact_sha)


def collect_arm(root,tasks,run_sha,arm,artifact_sha,factory,limit):
    engine=None; count=new=0
    configure_arm(arm)
    try:
        for task,path in zip(tasks,record_paths(root,tasks,arm)):
            if path.exists():
                validate_record(read_json(path),task,run_sha,arm,artifact_sha)
            elif limit is None or new<limit:
                if engine is None:
                    print(f'Loading clean checkpoint-000022 for {arm} arm...',flush=True); engine=factory()
                record=make_record(task,run_sha,arm,engine(task))
                validate_record(record,task,run_sha,arm,artifact_sha); atomic_json(path,record); new+=1
            else: continue
            count+=1
            if count%25==0 or count==len(tasks) or new==limit:
                print(f'  {arm}: completed/reused {count}/{len(tasks)}; new {new}',flush=True)
    finally:
        if engine is not None: release_engine(engine)
    return count,new


def load_results(root,tasks,run_sha,artifact_sha):
    return {arm:[validate_record(read_json(path),task,run_sha,arm,artifact_sha)
                 for task,path in zip(tasks,record_paths(root,tasks,arm))] for arm in ARMS}


def cached(root,identity,tasks):
    manifest=read_json(root/'results/manifest.json'); run_sha=canonical_sha256(identity)
    paths=[p for arm in ARMS for p in record_paths(root,tasks,arm)]
    require(manifest['identity_sha256']==run_sha and set(manifest['outputs'])==set(OUTPUTS)
            and set(manifest['records'])=={p.relative_to(root).as_posix() for p in paths},'Cached final inventory differs.')
    for arm in ARMS:
        require(set((root/arm/'questions').glob('*.json'))==set(record_paths(root,tasks,arm)),'Missing/foreign cached records.')
    for name,spec in manifest['outputs'].items(): require(file_spec(root/'results'/name)==spec,'Cached final output damaged; preserved.')
    for name,spec in manifest['records'].items(): require(file_spec(root/name)==spec,'Cached final record damaged; preserved.')
    report=read_json(root/'results/report.json')
    require(report['identity_sha256']==run_sha,'Cached final report identity differs.')
    return report


def print_report(report):
    for label,s in report['results'].items():
        a=s['frozen_candidate_pipeline_anchored']['candidate_metrics']['micro']
        precision='undefined' if a['precision'] is None else f"{100*a['precision']:.3f}%"
        recall='undefined' if a['recall'] is None else f"{100*a['recall']:.3f}%"
        print(f"{label}: actual candidate analyzer TP {a['tp']}, FP {a['fp']}, FN {a['fn']}; P {precision}; R {recall}",flush=True)
        for name,row in s['official_reference_comparison'].items():
            m=row['metrics']
            print(f"  {name}: official AUPR {100*m['aupr']:.3f}%; P@80R {100*m['prec_at_80_recall']:.3f}%; P@90R {100*m['prec_at_90_recall']:.3f}%",flush=True)
    print('Final evaluation complete; review pending. Reference benchmark scores are not deployed-analyzer accuracy.',flush=True)
    print('Candidate-only/null-confidence remains frozen. No tuning, training, calibration or parser-integration claim.',flush=True)
    print(f'Report: {ROOT}/results/report.json\nIdentity: {ROOT}/identity.json',flush=True)


def run(repo,device='cuda',full=False):
    repo=Path(repo); config=read_config(repo); root=repo/ROOT
    deadline=datetime.fromisoformat(config['deadline_ist'])
    require((root/'results').is_dir() or now_ist()<=deadline,'November 5 evaluation deadline passed; report incomplete and preserve records.')
    policy,closed=verify_policy(repo,config)  # Freeze evidence BEFORE opening test examples.
    torch,runtime=initialize_runtime(device)
    tasks,released,baseline,inputs=verify_inputs(repo,config)
    identity={'config':config,'config_sha256':CONFIG_PIN,'closed_policy':closed,'inputs':inputs,
        'runtime':runtime,'device':device,'code_sha256_lf':{n:code_hash(repo/'ml/scripts'/n) for n in CODE_FILES}}
    verify_ignored_assets(repo,[f'{ROOT}/{n}' for n in ('run.lock','identity.json','candidate/questions/000000.json',
        'official/questions/000000.json','results/report.json','results/predictions.json','results/official_curves.json','results/manifest.json')])
    with run_lock(root):
        if not (root/'identity.json').exists():
            require(not any(p.name!='run.lock' for p in root.iterdir()),'Nonempty final run lacks identity; preserved.')
        atomic_json(root/'identity.json',identity); run_sha=canonical_sha256(identity)
        if (root/'results').exists():
            report=cached(root,identity,tasks); print('Verified existing final evaluation; no inference/scoring repeated.',flush=True)
            print_report(report); return report
        preflight_records(root,tasks,run_sha,config['artifact_manifest_sha256'])
        factories={'candidate':lambda:CandidateEngine(repo/ARTIFACT,config['artifact_manifest_sha256'],device),
            'official':lambda:OfficialEngine(repo/ARTIFACT,repo/MODEL_DIR/'roberta-base',repo/REFERENCE_DIR/'utils.py',device)}
        started=time.perf_counter(); progress={}
        for arm in ARMS:
            done,new=collect_arm(root,tasks,run_sha,arm,config['artifact_manifest_sha256'],factories[arm],None if full else 2)
            progress[arm]={'completed_questions':done,'new_questions':new}
        if any(v['completed_questions']!=len(tasks) for v in progress.values()):
            print('PASS: partial final collection verified in both arms. No test metrics issued.',flush=True)
            print('Resume with the same --device and --full; completed questions are reused.',flush=True); return None
        results=load_results(root,tasks,run_sha,config['artifact_manifest_sha256'])
        print('Both fixed arms complete. Scoring full test and frozen sensitivity; no threshold selection...',flush=True)
        scores,curves=score_all(tasks,results,released,load_reference(repo,baseline),policy)
        predictions=[{**{k:t[k] for k in ('question_id','category_id','title','group_id','family_id','source_sha256','gold','in_sensitivity')},
            'core_result':results['candidate'][i],'official_reference':results['official'][i]} for i,t in enumerate(tasks)]
        completed=now_ist(); report={'status':'final_frozen_evaluation_complete_review_pending' if completed<=deadline else 'final_evaluation_completed_after_deadline',
            'identity_sha256':run_sha,'completed_at_ist':completed.isoformat(),'completed_by_deadline':completed<=deadline,
            'coverage':inputs['coverage'],'current_invocation':progress,'current_invocation_seconds':time.perf_counter()-started,
            'actual_candidate_windows':sum(x['categories'][0]['windows_done'] for x in results['candidate']),
            'official_reference_windows':sum(x['windows'] for x in results['official']),
            'results':scores,'official_curves_sha256':canonical_sha256(curves),'predictions_sha256':canonical_sha256(predictions),
            'training_calibration_decoder_or_policy_selection_performed':False,'runtime_or_artifact_changed':False,
            'accepted_findings_enabled':False,'absence_enabled':False,'parser_app_integration_verified':False,
            'limitations':['The actual frozen analyzer and the benchmark-only authors reference path are different reporting arms, never alternatives selected on test.',
                'Official AUPR/P@recall compare checkpoint weights under the authors inference/scoring path; they are not scores of the deployed disjoint pipeline.',
                'The released model used the original training pool; the clean checkpoint used the frozen fit subset. This is not a controlled equal-training experiment.',
                'The official n-best probability is an uncalibrated benchmark weight; it is never emitted as core confidence.',
                'Official evaluator threshold-grid and final-point quirks are preserved. No operating cutoff is chosen.',
                'Anchored family-bootstrap intervals are descriptive, conditional on fixed outputs; no refit uncertainty. Official metrics have no confidence intervals here.',
                'Sensitivity excludes nine already-reviewed overlap documents, retains two unresolved documents, and does not rule out unknown overlap.',
                'All gold and zero-output/incomplete questions remain in coverage. No candidate implies neither absence nor harmlessness.',
                'All categories remain not_validated; India, rules and retrieval are deferred. Benchmark source tests do not establish parser/app or arbitrary-upload quality.',
                'Invocation runtime excludes prior invocations and input verification; no total-runtime or time-saving claim.']}
        with TemporaryDirectory(prefix='.pending-results-',dir=root) as temp:
            stage=Path(temp)/'results'; stage.mkdir()
            values={'report.json':report,'official_curves.json':curves,'predictions.json':predictions}
            for name,value in values.items(): atomic_json(stage/name,value)
            atomic_json(stage/'manifest.json',{'identity_sha256':run_sha,
                'outputs':{name:file_spec(stage/name) for name in OUTPUTS},
                'records':{p.relative_to(root).as_posix():file_spec(p) for arm in ARMS for p in record_paths(root,tasks,arm)}})
            os.rename(stage,root/'results')
        print_report(report); return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',choices=('cuda','cpu'),default='cuda')
    parser.add_argument('--full',action='store_true')
    args=parser.parse_args()
    try: run(Path(__file__).resolve().parents[2],args.device,args.full)
    except KeyboardInterrupt:
        print('Stopped. Completed questions are preserved; repeat the same command to resume.',flush=True)
        raise SystemExit(130)
