"""Final benchmark inputs, bound records and two explicitly separated scores."""
from collections import Counter
import hashlib
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clauseanchor_core import from_dict, to_dict, text_digest, validate_result
from clauseanchor_core.artifacts import canonical_sha256, require
from clauseanchor_core._inference import window_count
from check_cuad_families import family_id
from cuad_candidate_policy import bootstrap_families, distribution, grouped
from cuad_development import aggregate, match_counts
from evaluate_cuad_baseline import score_predictions, reference_score, assert_parity, finite_json
from prepare_cuad_baseline import validate_reference_predictions

ARMS=('candidate','official')


def prepare_tasks(test,families,questions,tokenizer,config):
    """Only official-test source is required. Family decisions are already frozen."""
    docs=test['data']; expected={q['question']:q['category_id'] for q in questions}
    require(len(expected)==41,'Expected the frozen 41 CUAD prompts.')
    by_group={}; by_family={}
    for family in families['families']:
        require(family['family_id']==family_id(family['group_ids']),'Invalid family identity.')
        for gid in family['group_ids']:
            require(gid not in by_family,'Overlapping family membership.')
            by_family[gid]=family['family_id']
    for doc in docs:
        require(len(doc['paragraphs'])==1,'Reference path needs one full paragraph per document.')
        context=doc['paragraphs'][0]['context']
        gid='cuad-exact-v1:'+canonical_sha256([context])
        require(gid not in by_group,'Duplicate official-test source group.')
        by_group[gid]=doc
    excluded=set()
    for f in families['families']:
        members=set(f['group_ids']); present=members & set(by_group)
        if present and members-set(by_group): excluded.update(present)
    unresolved={g for d in families['title_decisions'] if d['decision']=='unresolved' for g in d['group_ids']} & set(by_group)
    require(len(docs)==config['official_test_documents']
            and len(excluded)==config['confirmed_overlap_excluded_documents']
            and len(docs)-len(excluded)==config['sensitivity_documents']
            and len(unresolved)==config['unresolved_retained_documents'] and not unresolved&excluded,
            'Frozen full/sensitivity membership counts differ.')
    tasks=[]; seen=set(); titles=set()
    for gid,doc in by_group.items():
        title=doc['title']; require(title not in titles,'Duplicate title.'); titles.add(title)
        paragraph=doc['paragraphs'][0]; source=paragraph['context']; raw,_=tokenizer.context(source)
        found=set()
        for q in paragraph['qas']:
            require(q['question'] in expected,'Official prompt differs from frozen runtime prompt.')
            cat=expected[q['question']]; require(cat not in found,'Repeated category in document.'); found.add(cat)
            require(q['id'] not in seen and q['id'].startswith(title+'__'),'Invalid/duplicate official question ID.'); seen.add(q['id'])
            # Preserve original IDs verbatim, including the evaluator's substring quirk.
            gold=[{'start':a['answer_start'],'end':a['answer_start']+len(a['text']),'text':a['text']} for a in q['answers']]
            require(all(type(a['start']) is int and 0<=a['start']<a['end']<=len(source)
                        and source[a['start']:a['end']]==a['text'] for a in gold),'Gold source slice differs.')
            require(type(q['is_impossible']) is bool and q['is_impossible']==(not gold),'Official answerability differs.')
            query,original=tokenizer.question(q['question'])
            task={'question_id':q['id'],'question':q['question'],'category_id':cat,'title':title,
                'group_id':gid,'family_id':by_family.get(gid,family_id([gid])),
                'context':source,'source_sha256':text_digest(source),'gold':gold,
                'in_sensitivity':gid not in excluded,'original_question_tokens':original,
                'windows_total':window_count(len(raw.ids),len(query.ids))}
            task['doc_id']=canonical_sha256([gid,task['source_sha256']])
            task['task_sha256']=canonical_sha256(task); tasks.append(task)
        require(found==set(expected.values()),'Missing official category coverage.')
    require(len(tasks)==config['official_test_questions'] and sum(len(t['gold']) for t in tasks)==config['official_test_answer_records'],
            'Official question/gold coverage differs.')
    return tasks,{'questions':len(tasks),'documents':len(docs),'families':len({t['family_id'] for t in tasks}),
        'categories':len(expected),'gold_records':sum(len(t['gold']) for t in tasks),
        'unique_gold_spans':sum(len({(g['start'],g['end']) for g in t['gold']}) for t in tasks),
        'candidate_windows_planned':sum(t['windows_total'] for t in tasks),
        'excluded_confirmed_overlap_titles':sorted(by_group[g]['title'] for g in excluded),
        'retained_unresolved_titles':sorted(by_group[g]['title'] for g in unresolved),
        'task_inventory_sha256':canonical_sha256([t['task_sha256'] for t in tasks])}


def inference_input(task):
    """Original reference input with no answers, answerability or gold offsets."""
    return {'data':[{'title':task['title'],'paragraphs':[{'context':task['context'],
        'qas':[{'id':task['question_id'],'question':task['question']}]}]}]}


def make_record(task,run_sha,arm,result):
    body={'question_id':task['question_id'],'task_sha256':task['task_sha256'],
          'run_sha256':run_sha,'arm':arm,'result':result}
    return {'payload':body,'payload_sha256':canonical_sha256(body)}


def validate_record(record,task,run_sha,arm,artifact_sha):
    require(set(record)=={'payload','payload_sha256'},'Invalid final record envelope.')
    body=record['payload']
    require(set(body)=={'question_id','task_sha256','run_sha256','arm','result'}
        and record['payload_sha256']==canonical_sha256(body)
        and body['question_id']==task['question_id'] and body['task_sha256']==task['task_sha256']
        and body['run_sha256']==run_sha and body['arm']==arm in ARMS,'Final record binding/checksum differs.')
    result=body['result']
    if arm=='official':
        require(set(result)=={'windows','prediction','candidates','null_score_difference'}
                and type(result['windows']) is int and result['windows']>0,'Invalid reference result.')
        qid=task['question_id']
        validate_reference_predictions(inference_input(task),{qid:result['candidates']},
                                       {qid:result['prediction']},{qid:result['null_score_difference']})
    else:
        core=from_dict(result); validate_result(core,task['context'])
        require(core.mode=='real' and core.artifact_manifest_sha256==artifact_sha
                and core.doc_id==task['doc_id'] and len(core.categories)==1,'Analyzer result source/identity differs.')
        c=core.categories[0]
        require(c.category_id==task['category_id'] and c.status=='abstained' and c.decision_confidence is None
                and c.windows_done==c.windows_total==task['windows_total'] and c.windows_done>0,
                'Analyzer output must include every planned window and abstain.')
        base=['experimental_candidate_only_unvalidated','bounded_candidate_generation_not_exhaustive','rules_and_retrieval_not_run']
        issues=[w for w in core.warnings if w not in base]
        allowed=[f"{w}:{c.category_id}" for w in ('question_truncated_first64','boundary_review')]
        require(all(w in allowed for w in issues) and all(w in core.warnings for w in base)
                and (allowed[0] in issues)==(task['original_question_tokens']>64)
                and c.search_complete==(not issues)
                and c.reason_code==('unvalidated_model' if c.search_complete else 'processing_incomplete_unvalidated'),
                'Analyzer completeness/reasons differ.')
        intervals=[]
        for f in c.clauses:
            require(f.status=='review_candidate' and f.confidence is None
                and f.confidence_band==f.calibration_scope=='unvalidated' and f.origin=='model'
                and not f.rule_flags and not f.passages and f.retrieval_status=='not_run'
                and f.id==canonical_sha256([core.text_sha256,core.doc_id,c.category_id,f.span.start,f.span.end]),
                'Frozen candidate-only contract changed.')
            intervals.append((f.span.start,f.span.end))
        intervals.sort(); require(all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:])),'Overlapping final candidates.')
    return result


def anchored(tasks,core_results,policy):
    rows=[]
    for t,result in zip(tasks,core_results,strict=True):
        c=result['categories'][0]
        selected=[f['span'] for f in c['clauses']]
        rows.append({'question_id':t['question_id'],'group_id':t['group_id'],'family_id':t['family_id'],
            'category_id':t['category_id'],'candidate_counts':match_counts(selected,t['gold']),
            'accepted_counts':match_counts([],t['gold']),'search_complete':c['search_complete'],
            'processing_issues':[w.split(':',1)[0] for w in result['warnings'] if w.endswith(':'+t['category_id'])],
            'windows_done':c['windows_done'],'windows_total':c['windows_total'],'category_status':c['status']})
    documents=grouped(rows,'group_id'); categories=aggregate(rows,'candidate_counts')
    support={}
    for cat,metrics in categories['categories'].items():
        rs=[r for r in rows if r['category_id']==cat]
        pos=len({r['family_id'] for r in rs if r['candidate_counts']['gold']})
        neg=len({r['family_id'] for r in rs if not r['candidate_counts']['gold']})
        support[cat]={'gold':metrics['gold'],'positive_families':pos,'no_gold_families':neg,
            'sparse':metrics['gold']<20 or pos<10 or neg<10,'catalogue_status':'not_validated'}
    strata={}
    for name,pred in [('no_gold',lambda r:r['candidate_counts']['gold']==0),('one_gold',lambda r:r['candidate_counts']['gold']==1),
        ('multiple_gold',lambda r:r['candidate_counts']['gold']>1),('processing_complete',lambda r:r['search_complete']),
        ('processing_incomplete',lambda r:not r['search_complete'])]:
        sub=[r for r in rows if pred(r)]; strata[name]=aggregate(sub,'candidate_counts') if sub else None
    return {'candidate_metrics':categories,'accepted_metrics':aggregate(rows,'accepted_counts'),
        'per_question':rows,'per_document':documents,'per_family':grouped(rows,'family_id'),
        'document_distributions':{label:distribution([d['counts'][field] for d in documents]) for label,field in
            [('false_highlights','fp'),('missed_gold','fn'),('review_candidates','predicted')]},
        'strata':strata,'category_support':support,'candidate_uncertainty':bootstrap_families(rows,policy),
        'category_states':dict(Counter(r['category_status'] for r in rows)),
        'processing_incomplete_questions':sum(not r['search_complete'] for r in rows),
        'zero_candidate_questions':sum(not r['candidate_counts']['predicted'] for r in rows),
        'positive_questions_without_candidates':sum(r['candidate_counts']['gold']>0 and not r['candidate_counts']['predicted'] for r in rows),
        'accepted_findings_enabled':False,'absence':{'enabled':False,'decisions':0,'error_rate':None},
        'actual_analyzer_called_on_benchmark_text':True,'parser_app_integration_claimed':False}


def score_all(tasks,results,released,reference,policy):
    require(set(results)==set(ARMS) and all(len(results[a])==len(tasks) for a in ARMS),'Both final arms must be complete.')
    scores={}; curves={}
    for label,indices in [('full_official_test',list(range(len(tasks)))),
                          ('known_overlap_sensitivity',[i for i,t in enumerate(tasks) if t['in_sensitivity']])]:
        ts=[tasks[i] for i in indices]
        answers={t['question_id']:[g['text'] for g in t['gold']] for t in ts}
        trained={tasks[i]['question_id']:results['official'][i]['candidates'] for i in indices}
        baseline={qid:released[qid] for qid in answers}
        compare={}; curves[label]={}
        # The baseline is reused from pinned released predictions; no baseline inference.
        for name,predictions in [('clean_checkpoint_reference_path',trained),('authors_released_reference',baseline)]:
            local=score_predictions(answers,predictions)
            original=reference_score(reference,answers,predictions)
            error=assert_parity(local,original)
            require(all(math.isfinite(v) for v in local['metrics'].values()),'Undefined official aggregate metric.')
            compare[name]={'metrics':local['metrics'],'original_evaluator_metrics':original['metrics'],
                'maximum_absolute_parity_error':error,'maximum_recall_including_last_point':max(local['recalls']),
                'maximum_recall_on_P_at_recall_grid':max(local['recalls'][:-1])}
            curves[label][name]=finite_json({k:v for k,v in local.items() if k!='metrics'})
        delta={k:compare['clean_checkpoint_reference_path']['metrics'][k]-compare['authors_released_reference']['metrics'][k]
               for k in compare['clean_checkpoint_reference_path']['metrics']}
        scores[label]={'questions':len(ts),'documents':len({t['group_id'] for t in ts}),
            'source_titles':sorted({t['title'] for t in ts}), 'official_reference_comparison':compare,
            'official_clean_minus_released':delta,
            'frozen_candidate_pipeline_anchored':anchored(ts,[results['candidate'][i] for i in indices],policy)}
    return scores,curves
