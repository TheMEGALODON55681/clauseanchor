# Frozen candidate-only operating policy

Owner: Tanishq Arya. Declared and reviewed October 29, 2026, Asia/Calcutta.
Base commit: `d882596ac662507e7d1b9c5c978d04408c90357d`.

**Decision: retain the existing candidate-only v0 policy.** The dev_policy run
and supplied-evidence review are complete, ahead of November 4. This closes the
operating-policy decision with explicit quality limitations. It does not validate
confidence, enable automatic acceptance or establish release readiness.

## Reviewed execution and interrupted resume

Tanishq's 32 focused tests passed in 8.674 seconds. The real run completed
October 29 at **16:55:33 IST**, on the RTX 2050 using CUDA 12.6, Torch
2.9.1+cu126, FP16 autocast/SDPA, batch size 1 and TF32 disabled.

VS Code closed during collection and earlier console output was lost. The
reported resume is consistent with the files: **734 saved questions + 2 new
pilot questions = 736**, then **822 new questions = 1,558 total**. This was
resumed inference, not another training run or another policy experiment.
The hash-matched collector verifies all saved records before new inference;
unchanged records are reused rather than overwritten.

Coverage is **1,558 questions, 38 documents, 37 families, 41 CUAD categories,
54,622 completed windows and 991 unique gold spans**. All documents have all
41 category questions; calibration and policy family inventories are disjoint.
All 1,558 projected category results are `abstained`, including zero-output
questions. The five India categories remain unavailable for inference.

The final invocation reports 2,094.82 seconds (34 minutes 54.82 seconds). It
includes loading, the remaining 822 questions and measurement, excludes preceding
input verification and earlier invocations, and is **not total run time**, app
latency or a measured time saving. Lost console output does not require a rerun.

## Measured candidate quality

These are anchored development metrics for review suggestions, using one-to-one
maximum-total-character-IoU matching at IoU >=0.5. They are not official CUAD
word-set scores, accepted-finding accuracy or legal-quality guarantees.

| Actual output set | Returned | TP | FP | FN / 991 gold | Precision | Recall | Exact matches |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unvalidated review candidates | 3,128 | 680 | 2,448 | 311 | 21.739% | 68.618% | 564 |
| Accepted findings, disabled | 0 | 0 | 0 | 991 | Undefined / null | 0% | 0 |

Candidate exact-match recall is **56.912%**. Zero false accepted highlights with
zero acceptance is not a quality pass. All 46 catalogue entries stay
`not_validated`; **33 of 41 measured CUAD categories have sparse support** under
the fixed rule. The other eight are not thereby validated.

| Candidate count per document, all 38 documents | Mean | 95th percentile | Maximum |
|---|---:|---:|---:|
| False candidate highlights | 64.42 | 157.35 | 327 |
| Missed gold spans | 8.18 | 13.30 | 22 |
| Returned review candidates | 82.32 | 194.40 | 374 |

Every document received candidates. A false candidate highlight here means an
unmatched prediction under the benchmark's category/span criterion; it is not
an importance judgment or evidence of an unfamiliar clause. These counts expose
substantial review noise; they do not demonstrate useful time savings.

| Fixed descriptive family-bootstrap interval | Lower 95% endpoint | Upper 95% endpoint |
|---|---:|---:|
| Candidate precision | 18.505% | 25.786% |
| Candidate recall | 65.505% | 71.667% |
| Exact-match recall | 53.187% | 60.870% |
| Mean false candidate highlights/document | 47.89 | 84.52 |

All 2,000 whole-family replicates were defined. These intervals hold the policy
and predictions fixed; they do not include model/calibrator refit uncertainty
or establish performance on arbitrary uploads.

### Coverage, misses and processing limitations

| Question stratum | Questions | Gold | Candidates | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| No gold for that category | 1,052 | 0 | 763 | 0 | 763 | 0 |
| One gold span | 313 | 313 | 1,125 | 277 | 848 | 36 |
| Multiple gold spans | 193 | 678 | 1,240 | 403 | 837 | 275 |
| Processing complete | 1,125 | 779 | 2,243 | 534 | 1,709 | 245 |
| Processing incomplete | 433 | 212 | 885 | 146 | 739 | 66 |

The first three rows partition the questions; the last two are a separate
partition and must not be added to them. Multiple-gold recall is 59.440%, compared
with 88.498% for one-gold questions. There are **741 zero-candidate questions**,
including **15 gold-bearing questions**. Of the 1,052 no-gold questions, 326
received candidates. Zero output never becomes an absence decision.

All windows completed, but **433 questions remain processing-incomplete**:
first-64-token question truncation affects 418 questions / 715 candidates;
selected boundary review affects 20 questions / 206 candidates. Five questions /
36 candidates have both reasons. The union is 433 questions / 885 candidates,
so reason counts must not be added without subtracting their overlap.
All these candidates remain explicitly unvalidated, with `search_complete=false`.
All 991 gold spans stay in overall recall; incomplete questions are not hidden.

## Evidence verification and limits

The assistant checked canonical evidence links, the frozen config and all 12
producer-code hashes, calibration provenance, complete question/category grids,
family separation, window totals, every projection's strict wire schema and
candidate-only fields, source/ID bindings, span lengths and disjointness.
All 3,128 candidates have null confidence, unvalidated band/scope and model
origin. Rules/passages are empty and retrieval is `not_run`.

The review independently reproduced per-question arithmetic, pooled/category/
document/family aggregation, support flags, strata, distributions and the same
fixed 2,000-sample family bootstrap from the supplied rows. No new inference,
training, threshold search, calibration fit or official-test scoring occurred.

The original source/gold, raw question records, feature arrays, weights and result
manifest were not attached. Exact source-slice equality, raw selection, underlying
gold matching and saved-record/model provenance were checked locally by the
hash-matched runner; they were not independently rerun here. Projection schema,
length and identity checks alone do not replace those source checks. No extra
source audit or repeated run is required for this closure.

| Supplied evidence | Canonical JSON SHA-256 |
|---|---|
| Run identity | `e4447a38c43cb5aab911ac37fb9b4ea45a0e11144e4b103d84af632ea02c8209` |
| Report | `667ea70dde0998124fdf84bb0691a670efe2fea67abf160af722dabe54e546f4` |
| Operating policy | `63141c142fee44491c3d4830229b02d5d1d73880861ce9ab2884fbad96780310` |
| Projections | `b97aa3c26a17a05a4557a59bbfaf03812da9ffb182d67d82864c0ec95b2a0331` |

Keep generated evidence unchanged, including the report's creation status
`candidate_only_policy_measured_review_pending`. This dated document records the
subsequent review and decision; do not rewrite generated reports to mark approval.

## Policy fixed before measurement

The decoder experiment is closed with `disjoint_full` retained. Calibration
failed its predeclared reliability gate and its sigmoid stays offline. Candidate
selection remains exact interval deduplication, raw margin strictly greater than
zero, then the existing greedy disjoint selection without a global candidate cap.
The exploratory cutoff 15.6513671875 is not adopted. A raw margin is not confidence.

| Situation | Contract 2.0 behavior retained |
|---|---|
| Real candidate | `review_candidate`, null confidence, unvalidated band/scope, origin `model` |
| Supported and processed category | `abstained` with `unvalidated_model` or `processing_incomplete_unvalidated` reason |
| Zero candidates after processing | Still `abstained`, never `absent` |
| Question truncation, selected boundary issue or partial processing | Available candidates remain review-only; honest incomplete status and reasons |
| Unsupported or unprocessed category | `unavailable`, with a reason |
| Accepted findings and absence decisions | Disabled |

Exact end-exclusive Unicode codepoint offsets are preserved. Neutral manual
review is unchanged: only accepted findings contribute coverage; incomplete
inventories/counts stay null. Zero items is not harmlessness or proof that nothing
was missed. Rules/retrieval and India validation remain deferred.

The automatic-acceptance requirements were predeclared before dev_policy:

| Requirement | Fixed engineering standard, not an achieved claim |
|---|---|
| Confidence and processing | Validated for requested scope; complete eligible processing |
| Accepted precision | At least 95%; undefined for an empty accepted set |
| Accepted recall | At least 50% of all gold, including misses/incomplete questions |
| False accepted highlights/document | Mean at most 1; p95 at most 3 |
| Category evidence | At least 50 accepted spans, 20 gold spans, 10 positive families and 10 no-gold families per category |
| Absence | Disabled without separately validated evidence; no claimed absence error rate |

Unvalidated calibration blocked acceptance before this run. The actual empty
accepted set also fails the precision/recall/support requirements; its zero-FP
limit check is vacuous and does not override those failures. No category is
promoted and no absence error rate is invented. Candidate metrics must not be
substituted into accepted-finding gates. The retained fallback is a candidate-only
research prototype with visible limitations, not a failed gate silently lowered.

## Frozen inputs and measurement procedure

Config: `ml/configs/cuad_candidate_policy_v1.json`, canonical SHA-256
`898260dea6b0b71b598a36ec668e62fa7f7ec18ce213596cd0b4a38555ef9180`.
The runner pins the complete config and reviewed calibration identity/report/
calibrator hashes; it never fits or applies the calibrator.

- Inference artifact: `models/clauseanchor_candidate_v0`, manifest
  `ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8`.
- Feature manifest:
  `c0fa3a88ba60064fb5ed1b7099473922e7c436174f944ea9371f808bd67b6818`.
- Frozen dev_policy partition:
  `e5b9b7e65c0c0f67623d317d0fc6884ca31ce75eaa1b90146376c563f78ac51e`.

Only dev_policy example files and shards are read; shared manifests contain other
partition metadata. No fit/dev_select/dev_cal examples or official-test examples
are opened. Hashes bind frozen sources, prompts, windows, membership and code.
Gold scores unchanged candidates; it never enters model computation or selection.
CUDA uses FP16-autocast/SDPA and CPU FP32/SDPA. Device, batch size and versions are
fixed in the run identity; CUDA results do not establish CPU output equality.

Score all unique gold intervals with the unchanged one-to-one maximum-total-IoU
matching, reporting exact matches separately. Keep zero-output and incomplete
questions in all-gold recall. Report no-gold/one-gold/multiple-gold and processing
strata, per-category/document/family results and document distributions.
Bootstrap whole families, including zero-output documents, 2,000 times with seed
20261029. Undefined replicates are explicit and excluded from quantiles.
Sparse support means fewer than 20 gold spans, 10 positive families or 10 no-gold
families; a family can contribute both kinds of question. The inherited metric
field `supported_categories` counts categories with gold/F1, not validated scope.

Projections are offline contract 2.0 representations of collected model output,
not fresh analyzer calls or live parser/app integration. Raw margins are separate
diagnostics. CUAD sources contain no parser decorations. The policy JSON records
the existing behavior; the analyzer does not load it. Core code and model export
remain unchanged; neither re-export nor confidence activation is needed.

## Recorded execution and next step

Execution is complete. These commands are retained for reproducibility;
**do not rerun them to install this documentation-only review update**:

```powershell
conda activate clauseanchor
python -m unittest discover -s ml/tests -p "test_cuad_candidate_policy.py"
python ml/scripts/evaluate_candidate_policy.py --device cuda
python ml/scripts/evaluate_candidate_policy.py --device cuda --full
```

The default call collects at most two new questions with no partial metrics;
`--full` resumes the same identity. Completed records publish atomically, are
verified before new work, and survive interruption. Completed results verify and
reuse without inference/scoring. Keep device/batch/code/config unchanged. Preserve
any failed or damaged run rather than deleting records or bypassing hashes.
Starting/resuming incomplete work after November 4 is refused; a late finish is
marked late. This run finished before the existing deadline.

The four reviewed files are `identity.json`, `results/report.json`,
`results/operating_policy.json` and `results/projections.json`, beneath
`data/processed/cuad/candidate_policy_v1`. Preserve `questions/` and
`results/manifest.json` locally. Generated evidence, features and weights remain
ignored by Git. Commit code/config/tests and this measured documentation.

All 32 focused synthetic tests passed before delivery and on Tanishq's machine.
They cover resume/cache integrity, split isolation/hashes, all-window no-gradient
collection, exact offsets, incomplete/zero states, matching, family bootstrap,
no fitting/search and projection parity with the analyzer on scripted windows.
No code changed during this result review and no software-test rerun is needed.

Next: freeze the available candidate-only pipeline and complete final evaluation
by **November 5**, keeping official-protocol and anchored scores separate and
never tuning on test. Packaging/integration checks remain due **November 6**,
release handoff **November 7**. Actual parser integration remains pending and
must be named if unavailable. Rules, retrieval, India validation and the formal
workload study remain deferred; no new experiment follows poor candidate quality.
