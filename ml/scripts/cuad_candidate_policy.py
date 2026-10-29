"""Offline candidate-only policy projection and fixed-policy measurements.

No model, calibrated probabilities, threshold search or automatic acceptance.
CUAD sources have no parser decorations; this is not parser/app integration.
"""
from collections import Counter, defaultdict
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clauseanchor_core import AnalysisResult, CategoryResult, ClauseFinding, Span, text_digest, validate_result
from clauseanchor_core.artifacts import canonical_sha256, require
from clauseanchor_core._inference import disjoint_candidates
from cuad_development import aggregate, match_counts, summarize


def project_result(task, selected, artifact_sha, *, windows_done=None, parser_complete=True):
    """Project saved real candidates to v2; gold is never used in this function.

    Status/reasons match CandidateOnlyAnalyzer for an undecorated source. This
    projection is validated offline, not represented as a fresh analyzer call.
    """
    source=task['context']; digest=text_digest(source)
    doc_id=canonical_sha256([task['group_id'], digest]); cat=task['category_id']
    total=task['end']-task['begin']; done=total if windows_done is None else windows_done
    require(type(done) is int and 0<=done<=total and total>0,'Invalid completed window count.')
    require(done>0 or not selected,'Unprocessed question cannot have findings.')
    issues=[]
    if done<total: issues.append('window_limit')
    if task['original_question_tokens']>64: issues.append('question_truncated_first64')
    if any(c['boundary_review'] for c in selected): issues.append('boundary_review')
    warnings=['experimental_candidate_only_unvalidated','bounded_candidate_generation_not_exhaustive','rules_and_retrieval_not_run']
    if not parser_complete: warnings.append('parser_incomplete')
    warnings.extend(f'{issue}:{cat}' for issue in issues)
    complete=parser_complete and not issues
    clauses=[]
    for c in selected:
        require(c['text']==source[c['start']:c['end']],'Candidate source slice differs.')
        clauses.append(ClauseFinding(canonical_sha256([digest,doc_id,cat,c['start'],c['end']]), cat,
            Span(doc_id,digest,c['start'],c['end'],c['text']), 'review_candidate', None, 'unvalidated','unvalidated','model'))
    reason='unvalidated_model' if complete else 'processing_incomplete_unvalidated'
    if done==0: reason='window_limit_not_processed'
    result=AnalysisResult('2.0',doc_id,digest,artifact_sha,'real',[
        CategoryResult(cat,'abstained' if done else 'unavailable',None,reason,complete,done,total,len(clauses),clauses)],warnings)
    validate_result(result,source)
    return result


def distribution(values):
    a=np.asarray(values,dtype=float)
    return {'mean':float(a.mean()),'p95':float(np.quantile(a,.95)),'max':int(a.max())} if len(a) else None


def grouped(rows,key):
    groups=defaultdict(Counter)
    for row in rows:
        groups[row[key]].update(row['candidate_counts'])
        groups[row[key]]['questions']+=1
    return [{key:name,'counts':summarize(counts)} for name,counts in sorted(groups.items())]


def bootstrap_families(rows,policy):
    rule=policy['evaluation']; families=defaultdict(Counter); documents=defaultdict(set)
    for row in rows:
        families[row['family_id']].update(row['candidate_counts'])
        documents[row['family_id']].add(row['group_id'])
    names=sorted(families)
    if len(names)<2:
        return {'status':'insufficient_families','families':len(names),'intervals':None}
    values=np.array([[families[f]['tp'],families[f]['predicted'],families[f]['gold'],families[f]['fp'],
                      families[f]['exact_matches'],len(documents[f])] for f in names],dtype=float)
    rng=np.random.default_rng(rule['bootstrap_seed'])
    samples={k:[] for k in ('precision','recall','exact_match_recall','false_highlights_per_document')}
    undefined={k:0 for k in samples}
    for _ in range(rule['bootstrap_replicates']):
        tp,pred,gold,fp,exact,docs=values[rng.integers(0,len(names),len(names))].sum(axis=0)
        for name,num,den in [('precision',tp,pred),('recall',tp,gold),('exact_match_recall',exact,gold),('false_highlights_per_document',fp,docs)]:
            if den: samples[name].append(num/den)
            else: undefined[name]+=1
    intervals={name:{'lower':float(np.quantile(v,.025)) if v else None,'upper':float(np.quantile(v,.975)) if v else None,
                     'valid_replicates':len(v),'undefined_replicates':undefined[name]} for name,v in samples.items()}
    return {'status':'descriptive_fixed_policy_family_bootstrap','families':len(names),
            'replicates':rule['bootstrap_replicates'],'intervals':intervals,'refit_uncertainty_included':False}


def summarize_policy(tasks, raw_pools, policy):
    """Select fixed candidates, validate v2 projections, then score against gold."""
    require(len(tasks)>0,'Empty policy question coverage.')
    rows=[]; projections=[]
    for task,raw in zip(tasks,raw_pools,strict=True):
        selected=disjoint_candidates(raw)
        result=project_result(task,selected,policy['artifact_manifest_sha256'])
        category=result.categories[0]
        candidate_counts=match_counts(selected,task['gold']); accepted_counts=match_counts([],task['gold'])
        reasons=[w.split(':',1)[0] for w in result.warnings if w.endswith(':'+task['category_id'])]
        rows.append({'question_id':task['question_id'],'group_id':task['group_id'],'family_id':task['family_id'],
                     'category_id':task['category_id'],'source_sha256':result.text_sha256,'candidate_counts':candidate_counts,
                     'accepted_counts':accepted_counts,'search_complete':category.search_complete,
                     'processing_issues':reasons,'windows_done':category.windows_done,'windows_total':category.windows_total,
                     'category_status':category.status,'reason_code':category.reason_code,'unresolved_count':category.unresolved_count})
        projections.append({'question_id':task['question_id'],'group_id':task['group_id'],'family_id':task['family_id'],
                            'core_result':result,'diagnostic_raw_margins':[c['margin'] for c in selected]})
    metrics=aggregate(rows,'candidate_counts'); accepted=aggregate(rows,'accepted_counts')
    documents=grouped(rows,'group_id'); families=grouped(rows,'family_id')
    distributions={label:distribution([d['counts'][field] for d in documents]) for label,field in
                   [('false_highlights','fp'),('missed_gold_spans','fn'),('returned_review_candidates','predicted')]}
    strata={}
    for name,predicate in [('no_gold',lambda r:r['candidate_counts']['gold']==0),('one_gold',lambda r:r['candidate_counts']['gold']==1),
                           ('multiple_gold',lambda r:r['candidate_counts']['gold']>1),('processing_complete',lambda r:r['search_complete']),
                           ('processing_incomplete',lambda r:not r['search_complete'])]:
        sub=[r for r in rows if predicate(r)]
        strata[name]=aggregate(sub,'candidate_counts') if sub else None
    support={}; rule=policy['evaluation']
    for cat in sorted(metrics['categories']):
        sub=[r for r in rows if r['category_id']==cat]
        positive={r['family_id'] for r in sub if r['candidate_counts']['gold']>0}
        negative={r['family_id'] for r in sub if r['candidate_counts']['gold']==0}
        gold=sum(r['candidate_counts']['gold'] for r in sub)
        support[cat]={'gold_spans':gold,'positive_families':len(positive),'no_gold_families':len(negative),
                      'sparse_support':gold<rule['category_sparse_gold_below'] or len(positive)<rule['category_sparse_positive_families_below'] or len(negative)<rule['category_sparse_no_gold_families_below'],
                      'catalogue_support_status':'not_validated','candidate_metrics':metrics['categories'][cat],
                      'accepted_metrics':accepted['categories'][cat]}
    blockers=['calibration_unvalidated','no_validated_category_confidence','no_validated_absence_artifact']
    # These are measurements of the ACTUAL empty accepted set. Do not substitute
    # candidate TP/FP or undefined precision with a flattering value of 1.0.
    auto=policy['automatic_acceptance_prerequisites']; am=accepted['micro']
    checks={'validated_confidence':False,'accepted_precision':am['precision'] is not None and am['precision']>=auto['minimum_accepted_precision'],
            'accepted_recall':am['recall'] is not None and am['recall']>=auto['minimum_accepted_recall_all_gold'],
            'false_accepted_highlight_limits':0<=auto['maximum_mean_false_accepted_highlights_per_document'] and 0<=auto['maximum_p95_false_accepted_highlights_per_document'],
            'accepted_category_support':False}
    return {'candidate_metrics':metrics,'accepted_metrics':accepted,'per_question':rows,'per_document':documents,'per_family':families,
            'candidate_document_distributions':distributions,'candidate_strata':strata,'category_support':support,
            'candidate_uncertainty':bootstrap_families(rows,policy),
            'category_states':dict(Counter(r['category_status'] for r in rows)),
            'processing_incomplete_questions':sum(not r['search_complete'] for r in rows),
            'zero_candidate_questions':sum(not r['candidate_counts']['predicted'] for r in rows),
            'positive_questions_without_candidates':sum(r['candidate_counts']['gold']>0 and not r['candidate_counts']['predicted'] for r in rows),
            'automatic_acceptance':{'enabled':False,'prerequisite_blockers':blockers,'checks':checks,
                'false_accepted_highlights_per_document':{'mean':0.,'p95':0.,'max':0},
                'zero_false_accepted_highlights_is_a_quality_pass':False},
            'absence':{'enabled':False,'decisions':0,'error_rate':None,'reason':'not_assessed_no_validated_absence_artifact'},
            'contract_and_source_projection_checks_passed':True,'projection_is_live_parser_integration':False},projections
