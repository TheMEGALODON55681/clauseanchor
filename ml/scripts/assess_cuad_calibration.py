"""Frozen extractor -> dev_cal only -> one predeclared calibration assessment.

Default: two NEW questions, no fitting/report. --full completes the same run.
Completed questions resume automatically; changed identities fail closed.
No checkpoint/decoder changes, policy selection or official-test reads.
"""
import argparse
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clauseanchor_core.artifacts import canonical_sha256, read_json, require, runtime_versions, verify_bundle, file_spec
from clauseanchor_core._inference import TorchBackend, disjoint_candidates
from cuad_calibration import assess, family_folds
from cuad_development import aggregate, interval_iou, match_counts
from prepare_cuad_features import POLICY as FEATURE_POLICY, ROLES, verify_shard
from prepare_cuad_training_assets import SOURCE_PIN
from prepare_cuad_baseline import verify_ignored_assets
from run_cuad_baseline import atomic_json, run_lock
from validate_cuad_decoder import WindowMaps, infer_question, make_record, validate_record

CONFIG='ml/configs/cuad_calibration_v1.json'
CONFIG_PIN='8a85c12889b8159259b1de04fffb833a68eaa13088047e23062f9cc8bccd923e'
ROOT='data/processed/cuad/calibration_v1'
FEATURES='data/processed/cuad/features_v1'
FROZEN='data/processed/cuad/frozen_v1'
ARTIFACT='models/clauseanchor_candidate_v0'
CODE_FILES=('assess_cuad_calibration.py','cuad_calibration.py','cuad_development.py',
            'prepare_cuad_features.py','prepare_cuad_training_assets.py','validate_cuad_decoder.py',
            'prepare_cuad_baseline.py','run_cuad_baseline.py','check_cuad_families.py','audit_cuad_questions.py')
INDIA=timezone(timedelta(hours=5,minutes=30))


def now_ist():
    return datetime.now(INDIA)


def code_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def read_policy(repo):
    policy=read_json(repo/CONFIG)
    require(canonical_sha256(policy)==CONFIG_PIN,'Predeclared calibration config changed; no method search is allowed.')
    return policy


def verify_freeze(repo, policy):
    root=repo/'data/processed/cuad/decoder_boundary_v1'
    ident=read_json(root/'identity.json'); report=read_json(root/'results/report.json')
    require(canonical_sha256(ident)==policy['decoder_experiment_identity_sha256']
            and canonical_sha256(report)==policy['decoder_experiment_report_sha256']
            and report['experiment_identity_sha256']==canonical_sha256(ident)
            and report['gate']['recommendation']=='disjoint_full' and not report['gate']['passed'],
            'Reviewed decoder freeze evidence differs; preserve it.')


def verify_inputs(repo, policy, prompts):
    """Read manifest metadata and dev_cal examples ONLY, never other split files.

    The previously verified feature-manifest digest is the trust anchor, binding
    feature identity -> frozen manifest -> exact dev_cal sources and shards.
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
    entry=frozen['partitions']['dev_cal']
    require(entry['file']=='dev_cal.json','Unexpected calibration partition path.')
    partition=read_json(repo/FROZEN/'dev_cal.json')
    require(canonical_sha256(partition)==entry['canonical_sha256']
            and partition['partition']=='dev_cal' and partition['intended_role']=='calibrator_fitting'
            and partition['freeze_canonical_sha256']==canonical_sha256(freeze), 'Wrong calibration membership/role.')
    groups=partition['groups']; entries=manifest['partitions']['dev_cal']; tasks=[]
    require(len(groups)==len(entries)>0,'Missing calibration feature group.')
    for group,part in zip(groups,entries):
        require(group['official_split']=='train','Official-test example in calibration.')
        group_sha=canonical_sha256(group)
        require(part['path']==f'dev_cal/{group_sha[:24]}','Invalid calibration shard path/order.')
        directory=root/part['path']; shard=verify_shard(directory,group,'dev_cal',canonical_sha256(identity))
        require(canonical_sha256(shard)==part['manifest_sha256'] and shard['summary']==part['summary'],
                'Calibration shard changed.')
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
        print(f'  verified dev_cal: {len(tasks)} questions',flush=True)
    coverage={'questions':len(tasks),'documents':len(groups),'families':len({t['family_id'] for t in tasks}),
              'categories':len({t['category_id'] for t in tasks}),'windows':sum(t['end']-t['begin'] for t in tasks),
              'gold_spans':sum(len({(g['start'],g['end']) for g in t['gold']}) for t in tasks)}
    summary=entry['summary']
    require(len({t['question_id'] for t in tasks})==len(tasks)
            and coverage['questions']==summary['questions'] and coverage['documents']==summary['exact_text_groups']
            and coverage['families']==summary['family_units']
            and sum(len(t['gold']) for t in tasks)==summary['answer_spans'], 'Incomplete calibration coverage.')
    return tasks,{'feature_manifest_sha256':canonical_sha256(manifest),'dev_cal_sha256':canonical_sha256(partition),
                 'frozen_manifest_sha256':canonical_sha256(frozen),'coverage':coverage}


def execution(device,batch_size):
    import torch
    require(device in ('cpu','cuda') and type(batch_size) is int and batch_size>0,'Invalid device/batch size.')
    require(device!='cuda' or torch.cuda.is_available(),'CUDA unavailable. Choose CPU explicitly before starting this run.')
    require(importlib.metadata.version('scipy')=='1.17.0','Use existing scipy==1.17.0.')
    torch.manual_seed(20261029)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    return {'runtime':runtime_versions(),'scipy':'1.17.0','device':device,'batch_size':batch_size,
            'precision':'fp16_autocast' if device=='cuda' else 'fp32','attention':'sdpa','tf32':False,
            'cuda_version':torch.version.cuda,'device_name':torch.cuda.get_device_name(0) if device=='cuda' else 'cpu',
            'bitwise_reproducibility_claimed':False}


def collect(root,tasks,run_sha,producer,limit):
    """Only producer performs inference. It is created lazily for unfinished work."""
    require(limit is None or (type(limit) is int and limit>0),'Invalid new-question limit.')
    expected={f'{i:06d}.json' for i in range(len(tasks))}
    directory=root/'questions'; directory.mkdir(exist_ok=True)
    require({p.name for p in directory.glob('*.json')}<=expected,'Foreign question records found.')
    # Validate every saved record before issuing even one additional model call.
    for i,task in enumerate(tasks):
        path=directory/f'{i:06d}.json'
        if path.exists(): validate_record(read_json(path),task,run_sha)
    new=done=0; records=[]
    for i,task in enumerate(tasks):
        path=directory/f'{i:06d}.json'
        if path.exists():
            record=read_json(path); validate_record(record,task,run_sha)
        elif limit is None or new<limit:
            raw,counts=producer(task)
            record=make_record(task,run_sha,raw,counts)
            validate_record(record,task,run_sha)
            atomic_json(path,record); new+=1
        else:
            continue
        records.append(path); done+=1
        if done%25==0 or new==limit or done==len(tasks):
            print(f'  completed/reused {done}/{len(tasks)} questions; new {new}',flush=True)
    return done==len(tasks),records,new


def labeled_rows(tasks,root,run_sha):
    rows=[]; counts=[]; eligible_counts=[]; question_summary=[]; excluded=Counter()
    for i,task in enumerate(tasks):
        raw=validate_record(read_json(root/'questions'/f'{i:06d}.json'),task,run_sha)
        selected=disjoint_candidates(raw)
        # Inference/selection never receives gold. Labels are created only now.
        reasons=[]
        if task['original_question_tokens']>64: reasons.append('question_truncated_first64')
        if any(c['boundary_review'] for c in selected): reasons.append('selected_boundary_review')
        for reason in reasons: excluded[reason]+=len(selected)
        gold=sorted({(g['start'],g['end']) for g in task['gold']})
        counts.append({'category_id':task['category_id'],'counts':match_counts(selected,task['gold'])})
        eligible_counts.append({'category_id':task['category_id'],'counts':match_counts([] if reasons else selected,task['gold'])})
        for c in selected:
            if reasons: continue
            overlap=max((interval_iou((c['start'],c['end']),g) for g in gold),default=0.)
            rows.append({'question_id':task['question_id'],'group_id':task['group_id'],'family_id':task['family_id'],
                         'category_id':task['category_id'],'source_sha256':hashlib.sha256(task['context'].encode()).hexdigest(),
                         'start':c['start'],'end':c['end'],'margin':c['margin'],
                         'label':int(overlap>=.5),'maximum_gold_iou':overlap,
                         'exact_gold_span':(c['start'],c['end']) in gold})
        question_summary.append({'question_id':task['question_id'],'category_id':task['category_id'],
                                 'group_id':task['group_id'],'family_id':task['family_id'],
                                 'windows_completed':task['end']-task['begin'],'windows_total':task['end']-task['begin'],
                                 'returned_candidates':len(selected),'calibration_eligible':not reasons,
                                 'exclusion_reasons':reasons,'anchored_counts':counts[-1]['counts']})
    return rows,{'all_selected_anchored':aggregate(counts,'counts'),
                 'calibration_eligible_anchored_all_gold_denominator':aggregate(eligible_counts,'counts'),
                 'questions':question_summary,'excluded_candidate_reason_counts_nonexclusive':dict(excluded),
                 'zero_candidate_questions':sum(q['returned_candidates']==0 for q in question_summary),
                 'processing_incomplete_questions':sum(not q['calibration_eligible'] for q in question_summary)}


def cached(root,identity):
    manifest=read_json(root/'results/manifest.json')
    require(manifest['identity_sha256']==canonical_sha256(identity)
            and set(manifest['results'])=={'report.json','calibrator.json','oof_predictions.json'}, 'Cached result binding differs.')
    expected={f'questions/{i:06d}.json' for i in range(identity['inputs']['coverage']['questions'])}
    require(set(manifest['records'])==expected,'Cached question inventory differs.')
    require({f'questions/{p.name}' for p in (root/'questions').glob('*.json')}==expected,'Cached records missing/foreign.')
    for name,spec in manifest['results'].items(): require(file_spec(root/'results'/name)==spec,'Cached result damaged; preserved.')
    for name,spec in manifest['records'].items(): require(file_spec(root/name)==spec,'Cached input record damaged; preserved.')
    report=read_json(root/'results/report.json')
    require(report['identity_sha256']==canonical_sha256(identity),'Cached report identity differs.')
    return report


def print_report(report):
    assessment=report['assessment']; print(f"Calibration assessment: {assessment['status']}",flush=True)
    if assessment['oof_metrics']:
        m=assessment['oof_metrics']
        print(f"OOF overlap-eligibility: {m['candidates']} candidates; Brier {m['brier']:.6f}; ECE {m['ece']:.6f}",flush=True)
    print(f"Failed checks: {assessment['failed_checks']}",flush=True)
    print('Runtime remains candidate-only/null-confidence. No policy or test scoring.',flush=True)
    print(f'Report: {ROOT}/results/report.json\nIdentity: {ROOT}/identity.json',flush=True)


def run(repo,device='cuda',batch_size=1,full=False):
    repo=Path(repo); policy=read_policy(repo); root=repo/ROOT
    deadline=datetime.fromisoformat(policy['assessment_deadline_ist'])
    require((root/'results').is_dir() or now_ist()<=deadline,
            'November 2 calibration deadline passed. Keep confidence null; report incomplete assessment.')
    require((repo/FEATURES).is_dir() and (repo/FROZEN).is_dir(),'Missing frozen local inputs; do not regenerate training/features.')
    runtime=execution(device,batch_size)
    verify_ignored_assets(repo,[f'{ROOT}/{p}' for p in ('run.lock','identity.json','questions/000000.json','results/report.json','results/manifest.json','results/calibrator.json','results/oof_predictions.json')])
    with ExitStack() as stack:
        for directory in (repo/FROZEN,repo/FEATURES,root): stack.enter_context(run_lock(directory))
        verify_freeze(repo,policy)
        print('Verifying frozen inference artifact and dev_cal features...',flush=True)
        _,_,prompts=verify_bundle(repo/ARTIFACT,policy['artifact_manifest_sha256'])
        tasks,inputs=verify_inputs(repo,policy,prompts)
        identity={'policy':policy,'config_sha256':CONFIG_PIN,'inputs':inputs,'execution':runtime,
                  'family_folds':family_folds([t['family_id'] for t in tasks],policy),
                  'code_sha256_lf':{n:code_hash(repo/'ml/scripts'/n) for n in CODE_FILES}}
        if not (root/'identity.json').exists():
            require(not any(p.name!='run.lock' for p in root.iterdir()),'Nonempty calibration run lacks identity; preserved.')
        atomic_json(root/'identity.json',identity)
        run_sha=canonical_sha256(identity)
        if (root/'results').exists():
            report=cached(root,identity)
            print('Existing assessment verified/reused; no inference or fitting.',flush=True)
            print_report(report); return report
        backend=None; maps=WindowMaps()
        def producer(task):
            nonlocal backend
            if backend is None:
                print('Loading verified checkpoint-000022 inference weights...',flush=True)
                backend=TorchBackend(repo/ARTIFACT,device)
            # Existing verified feature IDs/offsets; all windows, including gold-ignored
            # training windows. No loss, gold arrays or optimizer enter this call.
            return infer_question(backend.model,task,maps.get(task['path']),backend.device,batch_size)
        started=time.perf_counter()
        try: complete,records,new=collect(root,tasks,run_sha,producer,None if full else 2)
        finally: maps.close()
        if not complete:
            print(f'PASS: partial collection verified; {len(records)}/{len(tasks)} questions, {new} new. No calibration fitted.',flush=True)
            print('Repeat the same device/batch command with --full. Completed questions are reused.',flush=True)
            return None
        print('All dev_cal questions collected. Fitting the ONE predeclared family-held-out procedure...',flush=True)
        rows,extraction=labeled_rows(tasks,root,run_sha)
        assessment,oof=assess(rows,[t['family_id'] for t in tasks],{t['category_id'] for t in tasks},policy)
        completed=now_ist()
        if completed>deadline:
            assessment['checks']['completed_by_deadline']=False
            assessment['failed_checks']=list(dict.fromkeys([*assessment['failed_checks'],'completed_by_deadline']))
            assessment['status']='unvalidated'
        calibrator={'format':'clauseanchor-offline-calibration-assessment-v1','identity_sha256':run_sha,
                    'status':assessment['status'],'parameters':assessment['full_refit']['parameters'],
                    'event':policy['label'],'support':policy['support'],'execution':runtime,
                    'runtime_activation':False,'category_validation':False,'absence_calibration':False,
                    'requires_separate_operating_policy':True,'artifact_manifest_sha256':policy['artifact_manifest_sha256']}
        report={'status':'calibration_assessment_complete_review_pending','identity_sha256':run_sha,
                'completed_at_ist':completed.isoformat(),'coverage':inputs['coverage'],'assessment':assessment,
                'extraction':extraction,'calibrator_sha256':canonical_sha256(calibrator),
                'oof_predictions_sha256':canonical_sha256(oof),'current_invocation_seconds':time.perf_counter()-started,
                'current_invocation_new_questions':new,'model_weight_training_performed':False,
                'decoder_changed':False,'operating_policy_selected':False,'official_test_evaluated':False,
                'limitations':['OOF reliability is for benchmark overlap eligibility, not exactness, legal correctness, absence or one-to-one accepted precision.',
                    'All model weights and decoder are frozen; sigmoid fitting is not extractor retraining.',
                    'Family bootstrap conditions on fixed OOF predictions and does not include calibrator refit uncertainty.',
                    'Pooled checks are engineering screens, not proof of population/category calibration.',
                    'Incomplete questions and out-of-range/new precision paths have no validated confidence.',
                    'A passed offline assessment cannot activate confidence or accepted findings without a separate reviewed policy.']}
        with TemporaryDirectory(prefix='.pending-results-',dir=root) as temp:
            stage=Path(temp)/'results'; stage.mkdir()
            for name,value in [('report.json',report),('calibrator.json',calibrator),('oof_predictions.json',oof)]: atomic_json(stage/name,value)
            atomic_json(stage/'manifest.json',{'identity_sha256':run_sha,
                'results':{n:file_spec(stage/n) for n in ('report.json','calibrator.json','oof_predictions.json')},
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
