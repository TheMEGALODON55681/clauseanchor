"""One predeclared sigmoid assessment; no model inference or policy selection.

The binary event is overlap eligibility, not a fixed Hungarian match label.
Filtering changes assignments: policy evaluation must always rematch spans.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256


def family_folds(families, policy):
    rule = policy['reliability']
    ordered = sorted(set(families), key=lambda f: (canonical_sha256([rule['seed'], f]), f))
    return {f: i % rule['folds'] for i, f in enumerate(ordered)}


def fit_sigmoid(margins, labels, policy):
    rule = policy['method']
    x, y = np.asarray(margins, dtype=float), np.asarray(labels, dtype=float)
    require(x.ndim == y.ndim == 1 and len(x) == len(y)
            and np.isfinite(x).all() and (x > 0).all()
            and np.isin(y, [0, 1]).all(), 'Invalid calibration examples.')
    n1, n0 = int(y.sum()), int(len(y) - y.sum())
    result = {'positives': n1, 'negatives': n0, 'parameters': None}
    if min(n0, n1) < rule['minimum_training_examples_per_class']:
        return {**result, 'status': 'insufficient_training_classes'}
    scaled = x / rule['margin_scale']
    def objective(theta):
        a, b = theta
        z = a * scaled + b
        loss = np.mean(np.logaddexp(0, z) - y * z) + rule['l2'] * a * a / 2
        residual = expit(z) - y
        gradient = np.array([np.mean(residual * scaled) + rule['l2'] * a, np.mean(residual)])
        return loss, gradient
    fitted = minimize(objective, [rule['initial_slope'], np.log((n1 + 1) / (n0 + 1))],
                      method='L-BFGS-B', jac=True,
                      bounds=[rule['slope_bounds'], rule['intercept_bounds']],
                      options={'maxiter': rule['max_iterations'], 'ftol': rule['ftol'], 'gtol': rule['gtol']})
    if not fitted.success or not np.isfinite(fitted.x).all():
        return {**result, 'status': 'optimizer_failed', 'message': str(fitted.message)}
    a, b = map(float, fitted.x)
    if a <= 1e-8 or a >= rule['slope_bounds'][1] - 1e-8 or abs(b) >= rule['intercept_bounds'][1] - 1e-8:
        return {**result, 'status': 'flat_or_boundary_solution'}
    return {**result, 'status': 'fitted', 'parameters': {'slope': a, 'intercept': b,
            'margin_scale': rule['margin_scale'], 'minimum_training_margin': float(x.min()),
            'maximum_training_margin': float(x.max())}}


def probabilities(margins, parameters):
    x = np.asarray(margins, dtype=float)
    require(parameters is not None and np.isfinite(x).all(), 'Missing parameters/nonfinite margin.')
    return expit(parameters['slope'] * x / parameters['margin_scale'] + parameters['intercept'])


def metrics(labels, probs, families, policy, baseline=None):
    y, p = np.asarray(labels, dtype=float), np.asarray(probs, dtype=float)
    require(y.ndim == p.ndim == 1 and len(y) == len(p) == len(families)
            and np.isin(y, [0, 1]).all() and np.isfinite(p).all()
            and ((p >= 0) & (p <= 1)).all(), 'Invalid reliability rows.')
    n = len(y)
    bins = []
    edges = policy['reliability']['bins']
    for index, (lo, hi) in enumerate(zip(edges, edges[1:])):
        mask = (p >= lo) & ((p <= hi) if index == len(edges) - 2 else (p < hi))
        count = int(mask.sum())
        bins.append({'lower': lo, 'upper': hi, 'count': count,
                     'families': len({families[i] for i in np.flatnonzero(mask)}),
                     'mean_probability': float(p[mask].mean()) if count else None,
                     'observed_fraction': float(y[mask].mean()) if count else None,
                     'absolute_gap': float(abs(p[mask].mean() - y[mask].mean())) if count else None})
    clipped = np.clip(p, 1e-15, 1 - 1e-15)
    result = {'candidates': n, 'positives': int(y.sum()), 'negatives': int(n - y.sum()),
              'families': len(set(families)), 'bins': bins,
              'brier': float(np.mean((p - y) ** 2)) if n else None,
              'log_loss': float(np.mean(-y*np.log(clipped) - (1-y)*np.log1p(-clipped))) if n else None,
              'mean_probability': float(p.mean()) if n else None,
              'observed_fraction': float(y.mean()) if n else None,
              'ece': sum(b['count'] * b['absolute_gap'] for b in bins if b['count']) / n if n else None}
    if baseline is not None:
        b = np.asarray(baseline, dtype=float)
        require(b.shape == p.shape and np.isfinite(b).all() and ((b > 0) & (b < 1)).all(), 'Invalid baseline.')
        result['baseline_brier'] = float(np.mean((b-y)**2)) if n else None
        result['brier_difference'] = result['brier']-result['baseline_brier'] if n else None
    return result


def family_bootstrap(rows, all_families, policy):
    """Cluster percentile intervals conditional on fixed OOF predictions.

    Refit uncertainty is NOT included. Family units with zero eligible outputs
    remain in the resampling population; empty replicates are counted explicitly.
    """
    families = sorted(set(all_families)); rule = policy['reliability']
    if len(families) < 2 or not rows:
        return {'status': 'insufficient_families_or_candidates', 'intervals': None}
    indices = {f:i for i,f in enumerate(families)}
    # Per-family additive summaries: count, Brier, baseline Brier, then
    # per-bin count/sum(p)/sum(y). No row-independence assumption.
    nb = len(rule['bins'])-1
    sums = np.zeros((len(families), 3+3*nb))
    for row in rows:
        f = indices[row['family_id']]; p,y,b = row['oof_probability'],row['label'],row['baseline_probability']
        j = min(nb-1, int(np.searchsorted(rule['bins'],p,side='right')-1))
        sums[f,:3] += [1,(p-y)**2,(b-y)**2]
        sums[f,3+3*j:6+3*j] += [1,p,y]
    rng = np.random.default_rng(rule['seed'])
    values = {'brier': [], 'brier_difference': [], 'ece': []}; undefined=0
    for _ in range(rule['bootstrap_replicates']):
        total = sums[rng.integers(0,len(families),len(families))].sum(axis=0)
        n = total[0]
        if not n:
            undefined += 1
            continue
        bins = total[3:].reshape(nb,3)
        values['brier'].append(total[1]/n)
        values['brier_difference'].append((total[1]-total[2])/n)
        values['ece'].append(np.abs(bins[:,1]-bins[:,2]).sum()/n)
    intervals = {k:{'lower':float(np.quantile(v,.025)), 'upper':float(np.quantile(v,.975))}
                 for k,v in values.items()} if values['ece'] else None
    return {'status':'descriptive_fixed_oof_family_bootstrap', 'families':len(families),
            'replicates':rule['bootstrap_replicates'], 'undefined_replicates':undefined,
            'refit_uncertainty_included':False, 'intervals':intervals}


def assess(rows, all_families, categories, policy, in_time=True):
    """Rows contain only eligible frozen candidates. No thresholds are chosen."""
    folds = family_folds(all_families,policy); rule=policy['reliability']
    require(set(r['family_id'] for r in rows) <= set(folds), 'Unknown candidate family.')
    output=[{**r,'fold':folds[r['family_id']],'oof_probability':None,'baseline_probability':None} for r in rows]
    fitted_folds=[]
    for fold in range(rule['folds']):
        train=[r for r in output if r['fold']!=fold]; held=[r for r in output if r['fold']==fold]
        fit=fit_sigmoid([r['margin'] for r in train],[r['label'] for r in train],policy)
        fitted_folds.append({'fold':fold,'held_out_families':sorted(f for f,k in folds.items() if k==fold),
                             'train_candidates':len(train),'held_out_candidates':len(held),'fit':fit})
        if fit['parameters'] is not None:
            p=probabilities([r['margin'] for r in held],fit['parameters'])
            baseline=(sum(r['label'] for r in train)+1)/(len(train)+2)
            for row,value in zip(held,p): row.update(oof_probability=float(value),baseline_probability=baseline)
    refit=fit_sigmoid([r['margin'] for r in rows],[r['label'] for r in rows],policy)
    complete=bool(rows) and all(f['fit']['status']=='fitted' for f in fitted_folds)
    summary=uncertainty=None; by_category={}; high=None
    if complete:
        def describe(sub):
            return metrics([r['label'] for r in sub],[r['oof_probability'] for r in sub],
                           [r['family_id'] for r in sub],policy,[r['baseline_probability'] for r in sub])
        summary=describe(output); uncertainty=family_bootstrap(output,all_families,policy)
        high=describe([r for r in output if r['oof_probability']>=rule['high_probability_diagnostic_at_least']])
    for category in sorted(categories):
        sub=[r for r in output if r['category_id']==category]
        n1=sum(r['label'] for r in sub); n0=len(sub)-n1; nf=len({r['family_id'] for r in sub})
        by_category[category]={'candidates':len(sub),'positives':n1,'negatives':n0,'families':nf,
            'sparse_support':len(sub)<rule['category_sparse_below_candidates'] or min(n1,n0)<rule['category_sparse_below_each_class'] or nf<rule['category_sparse_below_families'],
            'oof_metrics':describe(sub) if complete else None, 'validation_status':'not_validated'}
    checks={'completed_by_deadline':bool(in_time),'all_folds_fitted':complete,'full_refit_fitted':refit['status']=='fitted'}
    if complete:
        intervals=uncertainty['intervals']
        checks.update(
            pooled_support=summary['candidates']>=rule['minimum_total_candidates'] and min(summary['positives'],summary['negatives'])>=rule['minimum_total_per_class'] and summary['families']>=rule['minimum_candidate_families'],
            nonempty_bin_support=all(b['count']>=rule['minimum_nonempty_bin_candidates'] and b['families']>=rule['minimum_nonempty_bin_families'] for b in summary['bins'] if b['count']),
            nonempty_bin_gaps=all(b['absolute_gap']<=rule['maximum_nonempty_bin_absolute_gap'] for b in summary['bins'] if b['count']),
            ece_upper_95=intervals is not None and intervals['ece']['upper']<=rule['maximum_ece_upper_95'],
            brier_gain_upper_95=intervals is not None and intervals['brier_difference']['upper']<0,
            no_undefined_bootstrap=uncertainty.get('undefined_replicates',1)==0)
    passed=all(checks.values())
    return {'status':'pooled_oof_assessment_passed_policy_pending' if passed else 'unvalidated',
            'checks':checks,'failed_checks':[k for k,v in checks.items() if not v],
            'family_folds':folds,'fold_fits':fitted_folds,'oof_metrics':summary,'uncertainty':uncertainty,
            'categories':by_category,'high_probability_diagnostic':high,'full_refit':refit,
            'runtime_activation':False,'absence_calibrated':False,'category_validation':False},output
