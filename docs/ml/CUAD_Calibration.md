# Frozen-extractor calibration assessment

Predeclared October 29, 2026, Asia/Calcutta, before opening dev_cal inference
results. Owner: Tanishq Arya. Base commit:
`25922ab9a1da2f517b044b98757c79b056c4c112`.
**Deadline: November 2, 2026, end of day IST. Assessment completed and reviewed
October 29; result: unvalidated.**
The October 29–November 7 execution window remains fixed.

The single decoder experiment is closed. Retain checkpoint-000022, the pinned
tokenizer, candidate generation, raw margin and `disjoint_full` selector described
in [CUAD_DecoderExperiment.md](CUAD_DecoderExperiment.md). The existing real
analyzer remains available for integration. This batch changes no runtime core
file, artifact payload, decoder or confidence field.

## Reviewed outcome: assessment complete, confidence remains null

Tanishq's run completed **October 29 at 02:04:04 IST**. His **37 focused tests
passed in 10.843 seconds**. The two-question pilot was preserved and reused; the
full invocation collected the remaining 1,556 questions. Coverage was **1,558
questions, 38 documents, 36 families, 41 categories, 68,405 windows and 915 unique
gold spans**, all from frozen dev_cal. The runtime was NVIDIA GeForce RTX 2050,
CUDA 12.6, Torch 2.9.1+cu126, FP16 autocast/SDPA, batch size 1, TF32 disabled.

The single predeclared method fitted successfully in all five family-held-out
folds and in the full refit. **The reliability gate failed**:
`nonempty_bin_gaps`. The following results describe the benchmark overlap-
eligibility target, not exactness, legal correctness or accepted-findings quality.

| Out-of-fold probability bin | Candidates | Families | Mean predicted | Observed eligible | Absolute gap | Bin-gap gate |
|---|---:|---:|---:|---:|---:|---|
| [0.0, 0.2) | 1,412 | 36 | 6.008% | 6.799% | 0.791 percentage points | Pass |
| [0.2, 0.4) | 280 | 36 | 28.822% | 16.429% | **12.394 percentage points** | **Fail** |
| [0.4, 0.6) | 212 | 36 | 51.056% | 46.698% | 4.357 percentage points | Pass |
| [0.6, 0.8) | 280 | 36 | 69.433% | 81.071% | **11.638 percentage points** | **Fail** |
| [0.8, 1.0] | 0 | 0 | — | — | — | No evidence |

The two failures exceed the fixed **10-percentage-point** limit. The [0.2,0.4)
bin overestimates eligibility; the [0.6,0.8) bin underestimates it. The aggregate
ECE does not override either failure. There were **no out-of-fold values >=0.8**
and no observations in the predeclared `p >=0.9` diagnostic subset. Empty bins
provide no high-confidence evidence.

Across **2,184 eligible candidates** (468 positive, 1,716 negative):

| Out-of-fold measure | Result | Descriptive family-bootstrap 95% interval |
|---|---:|---|
| Brier score | 0.103406 | 0.093125–0.116517 |
| Training-prevalence reference Brier | 0.169165 | Not separately reported |
| Paired Brier difference | -0.065759 | -0.080151 to -0.054850 |
| Log loss | 0.344546 | Not reported |
| ECE | 0.040156 | 0.029627–0.053327 |

All other predeclared checks passed, including pooled and nonempty-bin support,
fit completion, deadline, Brier improvement and the ECE upper endpoint. All 2,000
bootstrap replicates were defined. These conditional intervals do not include
refit uncertainty. **34 of 41 categories have sparse support** under the fixed
descriptive rule; none of the 41 categories is promoted to validated status.

### Extraction coverage and exclusions

| Candidate set on dev_cal | Returned | One-to-one TP | FP | FN / 915 gold | Precision | Recall | Exact matches |
|---|---:|---:|---:|---:|---:|---:|---:|
| All frozen positive-margin/disjoint candidates | 3,465 | 618 | 2,847 | 297 | 17.835% | 67.541% | 522 |
| Calibration-eligible questions only; all gold retained | 2,184 | 468 | 1,716 | 447 | 21.429% | 51.148% | 401 |

The all-candidate row includes incomplete-question outputs; it is not an accepted-
finding policy. Calibration excludes **1,281 distinct candidates** from 440
processing-incomplete questions. First-64-token question truncation affects 418
questions / 774 candidates; selected boundary review affects 29 questions / 566
candidates. Seven questions / 59 candidates have both reasons, so these reason
counts must not be added as disjoint totals. All windows ran; that does not erase
question truncation or boundary limitations. **749 questions produced zero
candidates**, which does not establish absence.

The full-resume invocation recorded 1,874.28 seconds (about 31 minutes 14 seconds).
This includes its model loading, remaining inference and assessment, excludes the
earlier pilot and preceding input verification, and is not an app latency benchmark
or a time-saving claim. No new extractor training, decoder change, operating-policy
selection or official-test evaluation occurred.

### Evidence review and decision

The assistant verified the four supplied files' canonical links and config/code
hashes; all question, coverage, exclusion and anchored-score totals; family fold
membership; every held-out probability and training-only baseline; category
support; and the gate. Reproducing the **same fixed** fold fits, full refit,
metrics and family bootstrap from the supplied rows matched the report within
numerical tolerance. This was verification, not another calibration experiment.
Probabilities reconstructed directly from recorded fold parameters differed by
at most `2.22e-16`. No method, regularization, bin or acceptance limit changed.

Raw question candidates, original source/features, weights and the result
manifest were not attached to this review. Their local provenance checks were
performed by the hash-matched runner; source-label correctness and model inference
were not independently rerun here. No extra source audit is required.

| Supplied evidence | Canonical JSON SHA-256 |
|---|---|
| Run identity | `1a7e8a7a49e2075873522444b6d73d2c39a00779ebe0dacda1612283be7d5ea4` |
| Report | `7ea42e1e9d291665ced08b015d56fe6179840a4b3abef04ad2ea2c02efe76683` |
| Offline calibrator | `73caec4f189b129d2ce061aa6d432808a04e838ea24ed05e71b741c3c7dd0f57` |
| Out-of-fold prediction rows | `01284476de8fffb753212ddb167e89bd76599a2fcede581e0943541f89aad29b` |

The retained full-refit parameters (slope 3.198843989561631, intercept
-4.39239300051517, margin scale 10) are **unvalidated offline evidence**, not
runtime confidence. Preserve all generated files, including the report's
`calibration_assessment_complete_review_pending` creation status. This separate
dated review records closure; do not rewrite generated evidence.

**Decision: retain the existing candidate-only analyzer, null confidence and
unvalidated scope.** The November 2 assessment deliverable is completed early
with an explicit failed validation outcome. No calibration-method search,
retraining or gate relaxation follows. Next, record the candidate-only operating
policy before dev_policy evaluation; the failed confidence prerequisite must not
be bypassed using policy data. The November 4–7 deadlines remain unchanged.

## Fixed inputs and partition boundary

- Local inference artifact: `models/clauseanchor_candidate_v0`, canonical manifest
  SHA-256 `ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8`.
  All payload hashes and installed core-code hashes are verified before loading.
- Frozen feature manifest SHA-256:
  `c0fa3a88ba60064fb5ed1b7099473922e7c436174f944ea9371f808bd67b6818`.
  The runner checks its identity, source/freeze links, every dev_cal shard's
  hashes, source slices, prompts, question ranges and complete coverage.
- Reviewed decoder experiment report/identity hashes are checked as freeze
  evidence; the experiment is not repeated.
- Only **dev_cal** source examples and feature arrays are opened. Existing
  manifests contain other partition metadata; no fit, dev_select, dev_policy
  or official-test example files are read for this assessment. There is no
  whole-pool reconstruction or new source audit.
- New inference covers every regular window of every frozen dev_cal question,
  including windows excluded from training loss. Neither gold arrays nor loss
  labels enter model inference. Model weights are never updated.
- Use the artifact-bound CUDA FP16-autocast/SDPA path by default, batch size 1,
  TF32 disabled. CPU FP32/SDPA can be explicitly chosen before starting. Device,
  batch size and runtime versions are recorded and cannot be mixed within a run.
  A CUDA assessment does not validate CPU probabilities or claim identical outputs.

Config: `ml/configs/cuad_calibration_v1.json`.
Canonical config SHA-256:
`8a85c12889b8159259b1de04fffb833a68eaa13088047e23062f9cc8bccd923e`.
The runner pins this digest. No method, fold, threshold, regularization or run-name
override is provided. Runtime flags do not authorize a calibration-method search.

## Exactly what the probability would describe

The candidate pool remains the frozen exact-dedup/positive-margin/disjoint pool,
without the exploratory 15.6513671875 cutoff. After selection, a candidate's
binary target is **whether its unchanged source interval has character IoU >=0.5
with at least one unique gold interval for the same question/category**.
Gold never generates or selects a candidate. Duplicate gold intervals count once;
distinct occurrences remain separate.

This is **benchmark overlap eligibility**, not exact-span correctness, legal
correctness, importance, category presence, absence or calibrated one-to-one
precision. For example, two disjoint half-spans can each be eligible for the same
gold span; a one-to-one assignment can count only one match. This definition
avoids treating a threshold-dependent Hungarian assignment as a fixed label.
Future policy evaluation must recompute the unchanged maximum-total-IoU matching
after filtering. It must not sum eligibility labels as accepted true positives.

Fit and reliability checks use only candidates from questions where all windows
completed, the question was not truncated beyond 64 tokens, and **none of the
selected candidates** has an unresolved boundary-review flag. This mirrors the
v0's question-level processing-completeness limitation. All excluded candidates
remain in the raw anchored metrics and exclusion counts. Every gold span remains
in both reported recall denominators, including gold from excluded questions.
Zero-output questions remain in coverage and miss counts; zero outputs never mean
absence. No India-category, parser-document or absence calibration is attempted.

## The one method

Fit one pooled, monotone, regularized logistic sigmoid:

`p = sigmoid(slope * raw_margin / 10 + intercept)`.

Minimize mean binary log loss plus `0.001 * slope² / 2`, with equal weight per
eligible candidate, no class weights and no per-category fit. The slope is bounded
to [0, 50], intercept to [-50, 50]. Use SciPy 1.17.0 L-BFGS-B with analytic
gradient, at most 1,000 iterations, `ftol=1e-12`, `gtol=1e-8`; initialize slope
at zero and intercept from training odds with one pseudo-count per class.
The scale of 10 and penalty are fixed engineering choices, not tuned results.

Each fit needs at least 20 positive and 20 negative eligible candidates. Missing
classes, failed optimization, a flat slope or a bound-limited solution gives an
explicit unusable fit. There is no hidden fallback, retry with another method,
isotonic experiment, category-specific adjustment or model retraining.

## Reliability assessment fixed before results

Use **five folds of whole frozen contract families** within dev_cal. Sort family
IDs by the canonical SHA-256 of `[20261029, family_id]`, then assign round-robin.
All documents, questions and candidates in a family share its fold. Assignment
uses no outcomes. Families with no eligible candidates remain in the inventory.

For each fold, fit only on the other four folds, then predict the held-out fold.
Each candidate is assessed once using a calibrator that did not see its family.
The reference probability for that fold is its training-set prevalence with one
pseudo-count per class. There is no fitting on dev_select or dev_policy.

Report out-of-fold Brier score, log loss, mean probability, observed fraction,
five fixed reliability bins [0,.2,.4,.6,.8,1] and count-weighted expected
calibration error (ECE). Bins are left-closed/right-open, except the final bin
includes one. Empty bins have null rates, not perfect calibration. Brier score
reflects more than reliability, so it is assessed alongside bin gaps and support.

Use 2,000 whole-family percentile-bootstrap replicates, seed 20261029, for
descriptive 95% intervals on Brier, paired Brier difference from the training-
prevalence reference, and ECE. Resample whole families, including zero-eligible
families. Predictions stay fixed: these intervals **do not include calibrator
refit uncertainty** or establish a population guarantee. Count empty replicates.

All these **engineering assessment gates** must pass:

| Check | Predeclared requirement |
|---|---|
| Fit and deadline | All five fold fits and the same-method full refit succeed; assessment finishes by November 2 IST |
| Pooled support | At least 500 eligible candidates, 50 positives, 50 negatives and 20 contributing families |
| Every nonempty probability bin | At least 50 candidates and 10 contributing families |
| Every nonempty bin's absolute calibration gap | At most 0.10 |
| ECE uncertainty | Descriptive bootstrap upper 95% endpoint at most 0.10 |
| Improvement over prevalence reference | Paired Brier-difference upper 95% endpoint strictly below zero |
| Undefined bootstrap replicates | None |

Report every category separately. Flag sparse support below 100 candidates,
20 examples of either class, or 10 contributing families. These are descriptive
support flags, **not category validation gates that automatically promote support**.
Report the fixed `p >= 0.9` subset descriptively; this is not a chosen acceptance
threshold or an automatic-highlighting decision.

After the out-of-fold assessment, refit the same sigmoid on all eligible dev_cal
candidates. Store its parameters and observed margin range in a separate offline
artifact. The out-of-fold assessment evaluates the fitting procedure; the final
refit's training predictions do not become a new held-out reliability result.

## Exit and runtime behavior

If any required check fails, record `unvalidated` with reasons. If every check
passes, record `pooled_oof_assessment_passed_policy_pending`. In both cases:

- The calibrator is an offline assessment artifact with `runtime_activation=false`.
  It is not a drop-in replacement for the existing analyzer manifest.
- Existing real findings remain `review_candidate`, with null confidence and
  unvalidated scope. Supported processed categories stay `abstained`; unsupported
  or unprocessed capabilities stay `unavailable`, with honest reasons/completeness.
- No category becomes validated, no absence probability is produced, and no
  `accepted` finding or new core status is introduced. Manual review is unchanged.
- Out-of-range margins, processing-incomplete questions, other precision paths,
  India extensions and arbitrary parser uploads receive no validated confidence.
- A failed assessment ends this method attempt. Keep the candidate-only prototype;
  do not lower gates, retune, open a retraining branch or search other methods.

Before dev_policy results are opened, a separate batch must record the
candidate-only operating policy and evaluation criteria, including recall, false
highlights and supported scope. The failed calibration prerequisite prevents
confidence/automatic-acceptance activation; dev_policy must not become another
calibration attempt. The policy decision remains due November 4, final frozen evaluation
November 5, packaging/integration checks November 6 and release handoff November 7.

## Recorded Windows execution

The assessment is complete. These commands are retained for reproducibility;
do not rerun them merely to install this documentation-only result update.

From the repository root, in the existing environment:

```powershell
conda activate clauseanchor
python -m unittest discover -s ml/tests -p "test_cuad_calibration.py"
python ml/scripts/assess_cuad_calibration.py --device cuda
python ml/scripts/assess_cuad_calibration.py --device cuda --full
```

Run each command only after the preceding one succeeds. The first runner call
processes at most two new questions and **does not fit** calibration on partial
data. After its `PASS: partial collection verified` line, `--full` reuses those
records and completes inference, fitting and assessment. No package upgrades,
checkpoint export or completed diagnostic reruns are needed.

Choose `--device cpu` in both runner commands only if choosing CPU before the
first run. Once identity/records exist, do not change device, batch size, code or
config. If CUDA is unavailable or a command fails, send the exact error and
preserve the run. Do not delete results or bypass a hash to force a second run.

The fixed output directory is `data/processed/cuad/calibration_v1`. Identity,
code/config/runtime hashes and fold membership are saved before inference.
Completed questions publish atomically and are checked before new inference.
Ctrl+C preserves them; repeat the same command to resume. Results publish
together only after all questions and assessment finish. Completed runs are
verified and reused without inference/refitting. A new run after November 2 is
refused; a run finishing late is unvalidated; completed results remain readable.

The console output and these four files were supplied and reviewed October 29:

- `data/processed/cuad/calibration_v1/identity.json`
- `data/processed/cuad/calibration_v1/results/report.json`
- `data/processed/cuad/calibration_v1/results/calibrator.json`
- `data/processed/cuad/calibration_v1/results/oof_predictions.json`

Preserve `questions/` and `results/manifest.json` locally. Generated records,
reports, calibrator files, features and model weights remain ignored by Git.
The measured Markdown summary is committed separately from these generated files.

## Software verification and current evidence

All **37 focused tests passed** in the assistant's Python 3.12 / CPU environment
on October 29. Synthetic tests cover family isolation, held-out-label invariance,
sigmoid failure cases, bins and cluster bootstrap, support gates, dev_cal-only
file access, source/hash failures, all-window no-gradient inference, incomplete
question exclusion, zero candidates, interrupted resume, deadline handling and
verified cached-result reuse. Existing tracked ML files remain byte-identical to
`25922ab`; model artifact hashes are unchanged.

The assistant did not run real model inference. Tanishq's real dev_cal run and
the subsequent verification of its supplied outputs are recorded above. Software
tests passed; the predeclared reliability gate failed. No calibrated-confidence
claim is created by the software pass or by successful sigmoid optimization.

Method background: the [scikit-learn calibration guide](https://scikit-learn.org/stable/modules/calibration.html)
describes sigmoid mappings, separate fitting/evaluation data, reliability diagrams
and the limits of interpreting Brier score alone. This batch implements its own
explicitly specified regularized, monotone fit with SciPy; it does not call
`CalibratedClassifierCV` or train the extractor inside cross-validation.
