"""One fixed candidate-only policy on dev_policy; no threshold search or calibration.

Default: two NEW questions. --full resumes the same run and measures it once.
No core/artifact changes and no official-test reads.
"""
from contextlib import ExitStack
from datetime import datetime
import argparse
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time

import numpy as np

from assess_cuad_calibration import (
    ARTIFACT, FEATURES, FROZEN, INDIA, CODE_FILES as COLLECTION_CODE_FILES,
    code_hash, collect, execution, now_ist,
)
from clauseanchor_core import to_dict
from clauseanchor_core.artifacts import canonical_sha256, read_json, require, verify_bundle, file_spec
from clauseanchor_core._inference import TorchBackend
from cuad_candidate_policy import summarize_policy
from prepare_cuad_features import POLICY as FEATURE_POLICY, ROLES, verify_shard
from prepare_cuad_training_assets import SOURCE_PIN
from prepare_cuad_baseline import verify_ignored_assets
from run_cuad_baseline import atomic_json, run_lock
from validate_cuad_decoder import WindowMaps, infer_question, validate_record

CONFIG='ml/configs/cuad_candidate_policy_v1.json'
CONFIG_PIN='898260dea6b0b71b598a36ec668e62fa7f7ec18ce213596cd0b4a38555ef9180'
ROOT='data/processed/cuad/candidate_policy_v1'
CODE_FILES=tuple(sorted(set(COLLECTION_CODE_FILES)|{'evaluate_candidate_policy.py','cuad_candidate_policy.py'}))


def read_policy(repo):
    policy=read_json(repo/CONFIG)
    require(canonical_sha256(policy)==CONFIG_PIN,'Predeclared candidate policy changed; no threshold or method search is allowed.')
    return policy


def verify_calibration(repo,policy):
    root=repo/'data/processed/cuad/calibration_v1'
    identity=read_json(root/'identity.json'); report=read_json(root/'results/report.json')
    calibrator=read_json(root/'results/calibrator.json')
    require(canonical_sha256(identity)==policy['calibration_identity_sha256']
            and canonical_sha256(report)==policy['calibration_report_sha256']
            and canonical_sha256(calibrator)==policy['calibrator_sha256']
            and report['identity_sha256']==calibrator['identity_sha256']==canonical_sha256(identity)
            and report['calibrator_sha256']==canonical_sha256(calibrator), 'Reviewed calibration evidence differs; preserve it.')
    require(report['assessment']['status']==calibrator['status']=='unvalidated'
            and calibrator['runtime_activation'] is False and calibrator['absence_calibration'] is False
            and calibrator['artifact_manifest_sha256']==policy['artifact_manifest_sha256']
            and identity['inputs']['feature_manifest_sha256']==policy['feature_manifest_sha256'],
            'Expected the frozen unvalidated calibration outcome; no automatic confidence activation.')
    return {'identity_sha256':canonical_sha256(identity),'report_sha256':canonical_sha256(report),
            'calibrator_sha256':canonical_sha256(calibrator),'status':'unvalidated',
            'family_ids':sorted(identity['family_folds'])}


def verify_inputs(repo, policy, prompts):
    """Read manifest metadata and dev_policy examples ONLY, never other split files.

    The previously verified feature-manifest digest is the trust anchor, binding
    feature identity -> frozen manifest -> exact dev_policy sources and shards.
    No reconstruction of the whole pool (which would read policy/test) is used.
    """
    root=repo/FEATURES
    manifest=read_json(root/'manifest.json'); identity=read_json(root/'identity.json')
    frozen=read_json(repo/FROZEN/'manifest.json'); freeze=read_json(repo/'ml/configs/cuad_split_freeze.json')
    require(canonical_sha256(manifest)==policy['feature_manifest_sha256'] and manifest['complete'] is True,
            'Frozen feature manifest changed or incomplete; do not rebuild features.')
    require(manifest['feature_identity_sha256']==canonical_sha256(identity)
            and identity['policy']==FEATURE_POLICY and identity['partition_roles']==ROLES
            and identity['training_source_sha256']==SOURCE_PIN
            and identity['frozen_manifest_sha256']==canonical_sha256(frozen), 'Feature/freeze binding differs.')
    require(frozen['freeze_canonical_sha256']==canonical_sha256(freeze)
            and frozen['assignment_canonical_sha256']==freeze['assignment_canonical_sha256'], 'Membership freeze changed.')
    for name,pin in identity['code_sha256'].items():
        require(name in ('prepare_cuad_features.py','prepare_cuad_training_assets.py')
                and code_hash(repo/'ml/scripts'/name)==pin, 'Frozen feature producer differs.')
    entry=frozen['partitions']['dev_policy']
    require(entry['file']=='dev_policy.json','Unexpected policy partition path.')
    partition=read_json(repo/FROZEN/'dev_policy.json')
    require(canonical_sha256(partition)==entry['canonical_sha256']
            and partition['partition']=='dev_policy' and partition['intended_role']=='operating_threshold_selection'
            and partition['freeze_canonical_sha256']==canonical_sha256(freeze), 'Wrong policy membership/role.')
    groups=partition['groups']; entries=manifest['partitions']['dev_policy']; tasks=[]
    require(len(groups)==len(entries)>0,'Missing policy feature group.')
    for group,part in zip(groups,entries):
        require(group['official_split']=='train','Official-test example in policy.')
        group_sha=canonical_sha256(group)
        require(part['path']==f'dev_policy/{group_sha[:24]}','Invalid policy shard path/order.')
        directory=root/part['path']; shard=verify_shard(directory,group,'dev_policy',canonical_sha256(identity))
        require(canonical_sha256(shard)==part['manifest_sha256'] and shard['summary']==part['summary'],
                'Policy shard changed.')
        source=read_json(directory/'source.json')
        audits=source['question_audit']
        pairs=[(p,q) for p in group['paragraphs'] for q in p['questions']]
        ranges=np.load(directory/'question_ranges.npy',allow_pickle=False)
        require(ranges.shape==(len(pairs),2) and len(audits)==len(pairs),'Question coverage changed.')
        previous=0
        for (paragraph,q),(begin,end),audit in zip(pairs,ranges.tolist(),audits):
            require(begin==previous and end>begin,'Empty/noncontiguous question windows.'); previous=end
            qid=q['question_id']; cid=q['category_id']; context=paragraph['context']
            require(cid in prompts and q['question']==prompts[cid], 'Question differs from frozen runtime prompt.')
            require(audit['question_id']==qid and audit['category_id']==cid and audit['window_range']==[begin,end]
                    and type(audit['original_question_tokens']) is int and audit['original_question_tokens']>0
                    and audit['used_question_tokens']==min(64,audit['original_question_tokens']), 'Question audit differs.')
            require(all(type(g['start']) is int and type(g['end']) is int and 0<=g['start']<g['end']<=len(context)
                        and context[g['start']:g['end']]==g['text'] for g in q['answers']), 'Gold source slice differs.')
            binding={'question_id':qid,'source_group_sha256':group_sha,'shard_manifest_sha256':part['manifest_sha256'],
                     'begin':begin,'end':end,'original_question_tokens':audit['original_question_tokens']}
            tasks.append({**binding,'task_sha256':canonical_sha256(binding),'path':directory,'context':context,
                          'group_id':group['group_id'],'family_id':group['family_id'],'category_id':cid,'gold':q['answers']})
        require(previous==shard['summary']['windows'] and len(pairs)==shard['summary']['questions'], 'Shard totals differ.')
        print(f'  verified dev_policy: {len(tasks)} questions',flush=True)
    coverage={'questions':len(tasks),'documents':len(groups),'families':len({t['family_id'] for t in tasks}),
              'categories':len({t['category_id'] for t in tasks}),'windows':sum(t['end']-t['begin'] for t in tasks),
              'gold_spans':sum(len({(g['start'],g['end']) for g in t['gold']}) for t in tasks)}
    summary=entry['summary']
    require(len({t['question_id'] for t in tasks})==len(tasks)
            and coverage['questions']==summary['questions'] and coverage['documents']==summary['exact_text_groups']
            and coverage['families']==summary['family_units']
            and sum(len(t['gold']) for t in tasks)==summary['answer_spans'], 'Incomplete policy coverage.')
    return tasks,{'feature_manifest_sha256':canonical_sha256(manifest),'dev_policy_sha256':canonical_sha256(partition),
                 'frozen_manifest_sha256':canonical_sha256(frozen),'coverage':coverage}


def read_pools(root,tasks,run_sha):
    # Keep only one question's raw candidates in memory; no input is rewritten.
    for i,task in enumerate(tasks):
        yield validate_record(read_json(root/'questions'/f'{i:06d}.json'),task,run_sha)


def cached(root,identity):
    manifest=read_json(root/'results/manifest.json')
    expected_results={'report.json','operating_policy.json','projections.json'}
    expected_records={f'questions/{i:06d}.json' for i in range(identity['inputs']['coverage']['questions'])}
    require(manifest['identity_sha256']==canonical_sha256(identity)
            and set(manifest['results'])==expected_results and set(manifest['records'])==expected_records,
            'Cached policy result binding/inventory differs.')
    require({f'questions/{p.name}' for p in (root/'questions').glob('*.json')}==expected_records,
            'Cached question records missing/foreign.')
    for name,spec in manifest['results'].items(): require(file_spec(root/'results'/name)==spec,'Cached policy result damaged; preserved.')
    for name,spec in manifest['records'].items(): require(file_spec(root/name)==spec,'Cached candidate record damaged; preserved.')
    report=read_json(root/'results/report.json')
    require(report['identity_sha256']==canonical_sha256(identity),'Cached report identity differs.')
    return report


def print_report(report):
    summary=report['measurement']; m=summary['candidate_metrics']['micro']
    p='undefined' if m['precision'] is None else f"{100*m['precision']:.3f}%"
    r='undefined' if m['recall'] is None else f"{100*m['recall']:.3f}%"
    print('Policy: retain existing candidate-only v0; confidence null; automatic acceptance/absence disabled.',flush=True)
    print(f"Review candidates: {m['predicted']}; TP {m['tp']}; FP {m['fp']}; FN {m['fn']}; P {p}; R {r}",flush=True)
    print(f"Processing-incomplete questions: {summary['processing_incomplete_questions']}; zero-candidate questions: {summary['zero_candidate_questions']}",flush=True)
    print('Accepted findings: 0; accepted precision undefined. Projection checks are not live parser/app integration.',flush=True)
    print(f"Measured by deadline: {report['measured_by_deadline']}; no tuning, refitting or official-test scoring.",flush=True)
    print(f'Report: {ROOT}/results/report.json\nIdentity: {ROOT}/identity.json',flush=True)


def run(repo,device='cuda',batch_size=1,full=False):
    repo=Path(repo); policy=read_policy(repo); root=repo/ROOT
    deadline=datetime.fromisoformat(policy['decision_deadline_ist'])
    require((root/'results').is_dir() or now_ist()<=deadline,
            'November 4 policy deadline passed. Retain candidate-only output and report policy evaluation incomplete.')
    require((repo/FEATURES).is_dir() and (repo/FROZEN).is_dir(),'Missing frozen local inputs; do not regenerate training/features.')
    runtime=execution(device,batch_size)
    verify_ignored_assets(repo,[f'{ROOT}/{p}' for p in ('run.lock','identity.json','questions/000000.json',
        'results/report.json','results/manifest.json','results/operating_policy.json','results/projections.json')])
    with ExitStack() as stack:
        for directory in (repo/FROZEN,repo/FEATURES,root): stack.enter_context(run_lock(directory))
        calibration=verify_calibration(repo,policy)
        print('Verifying frozen artifact, failed calibration binding and dev_policy inputs...',flush=True)
        _,catalogue,prompts=verify_bundle(repo/ARTIFACT,policy['artifact_manifest_sha256'])
        tasks,inputs=verify_inputs(repo,policy,prompts)
        require(not set(t['family_id'] for t in tasks)&set(calibration['family_ids']), 'Calibration/policy family leakage.')
        identity={'policy':policy,'config_sha256':CONFIG_PIN,'inputs':inputs,'execution':runtime,
                  'calibration_evidence':calibration,
                  'code_sha256_lf':{n:code_hash(repo/'ml/scripts'/n) for n in CODE_FILES}}
        if not (root/'identity.json').exists():
            require(not any(p.name!='run.lock' for p in root.iterdir()),'Nonempty policy run lacks identity; preserved.')
        atomic_json(root/'identity.json',identity); run_sha=canonical_sha256(identity)
        if (root/'results').exists():
            report=cached(root,identity)
            print('Existing policy result verified/reused; no new inference or evaluation.',flush=True)
            print_report(report); return report
        backend=None; maps=WindowMaps()
        def producer(task):
            nonlocal backend
            if backend is None:
                print('Loading verified checkpoint-000022 inference weights...',flush=True)
                backend=TorchBackend(repo/ARTIFACT,device)
            return infer_question(backend.model,task,maps.get(task['path']),backend.device,batch_size)
        started=time.perf_counter()
        try: complete,records,new=collect(root,tasks,run_sha,producer,None if full else 2)
        finally: maps.close()
        if not complete:
            print(f'PASS: partial policy collection verified; {len(records)}/{len(tasks)} questions, {new} new. No policy metrics issued.',flush=True)
            print('Repeat the same device/batch command with --full; completed questions are reused.',flush=True)
            return None
        print('All dev_policy questions collected. Measuring the ONE fixed candidate-only policy...',flush=True)
        measurement,projected=summarize_policy(tasks,read_pools(root,tasks,run_sha),policy)
        projections=[{**row,'core_result':to_dict(row['core_result'])} for row in projected]
        completed=now_ist(); in_time=completed<=deadline
        operating_policy={'format':'clauseanchor-candidate-policy-v1','identity_sha256':run_sha,
            'decision':'retain_existing_candidate_only_v0','measured_by_deadline':in_time,
            'artifact_manifest_sha256':policy['artifact_manifest_sha256'],'config_sha256':CONFIG_PIN,
            'confidence':None,'confidence_band':'unvalidated','calibration_scope':'unvalidated',
            'calibrator_applied':False,'accepted_findings_enabled':False,'absence_enabled':False,
            'runtime_changes':False,'categories':[{'id':c['id'],'support_status':'not_validated',
                'inference_available':c['id'] in prompts} for c in catalogue['categories']],
            'core_contract':'2.0','manual_review':'unchanged_no_accepted_coverage_no_importance_claim',
            'calibration_evidence':calibration,'evaluated_partition':'dev_policy',
            'measurement_complete':True,'release_readiness_or_quality_certified':False}
        report={'status':'candidate_only_policy_measured_review_pending' if in_time else 'policy_evaluation_completed_after_deadline',
            'identity_sha256':run_sha,'completed_at_ist':completed.isoformat(),'coverage':inputs['coverage'],
            'measured_by_deadline':in_time,'measurement':measurement,
            'operating_policy_sha256':canonical_sha256(operating_policy),'projections_sha256':canonical_sha256(projections),
            'current_invocation_new_questions':new,'current_invocation_seconds':time.perf_counter()-started,
            'threshold_search_performed':False,'calibration_fitted_or_applied':False,'model_weight_training_performed':False,
            'decoder_changed':False,'official_test_evaluated':False,'runtime_changed':False,
            'limitations':['Review-candidate anchored metrics are not accepted-finding precision or legal-quality guarantees.',
                'Empty accepted precision is null; zero false accepted highlights with zero acceptance is not success.',
                'All unique gold spans remain in recall, including incomplete and zero-output questions.',
                'Family-bootstrap intervals are descriptive for this fixed policy, with no refit uncertainty.',
                'CUAD text has no parser decorations; validated offline v2 projections do not establish parser/app integration.',
                'All catalogue categories remain unvalidated; India extensions, rules, retrieval and absence are unavailable/unimplemented.',
                'Candidate counts are not a measured workload or time-saving study.']}
        with TemporaryDirectory(prefix='.pending-results-',dir=root) as temp:
            stage=Path(temp)/'results'; stage.mkdir()
            values={'report.json':report,'operating_policy.json':operating_policy,'projections.json':projections}
            for name,value in values.items(): atomic_json(stage/name,value)
            atomic_json(stage/'manifest.json',{'identity_sha256':run_sha,
                'results':{name:file_spec(stage/name) for name in values},
                'records':{p.relative_to(root).as_posix():file_spec(p) for p in records}})
            os.rename(stage,root/'results')
        print_report(report); return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',choices=('cpu','cuda'),default='cuda')
    parser.add_argument('--batch-size',type=int,choices=(1,2,4),default=1)
    parser.add_argument('--full',action='store_true')
    args=parser.parse_args()
    run(Path(__file__).resolve().parents[2],args.device,args.batch_size,args.full)
