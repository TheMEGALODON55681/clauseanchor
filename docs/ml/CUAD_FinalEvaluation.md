# Frozen final extraction evaluation

Owner: Tanishq Arya. Protocol declared October 29, 2026; results reviewed
October 30, Asia/Calcutta. Base commit:
`8614cc1503d90625d1d4359fedf690133f1dfda5`.

**Final evaluation is complete. Retain the frozen candidate-only prototype.**
The November 5 evaluation deadline is met early. Confidence remains null,
calibration scope unvalidated, and automatic acceptance and absence disabled.
These results do not establish parser/app integration, arbitrary-upload quality
or time savings. Packaging/integration checks remain due November 6 and release
handoff November 7; the October 29–November 7 window is unchanged.

## Execution and interrupted resume

Tanishq's 35 focused tests passed in **80.387 seconds**. The Windows-only test
path assertion was corrected by recording `Path(path).as_posix()` instead of
`str(path)`. This changes the test's path normalization, not the evaluator,
checkpoint, protocol or saved inference identity.

The run completed **October 30 at 10:15:24 IST** on the RTX 2050, CUDA 12.6,
Torch 2.9.1+cu126, Python 3.12.14, Transformers 4.57.6, Tokenizers 0.22.2,
NumPy 2.3.5 and Safetensors 0.7.0. Each fixed arm contains **4,182 questions**.
The actual analyzer processed **138,972 windows**; the authors reference path
processed **154,627**. The different window counts follow their fixed settings.

Collection was interrupted and resumed. The supplied partial log shows the
official arm at **3,771/4,182, including two new questions**; the final invocation
reused all **4,182 candidate-arm questions** and completed the remaining **411
official-arm questions**. This was resumed evaluation inference, not training
or a second experiment. Lost console output does not require recollection.

The final invocation took **1,257.31 seconds (20 minutes 57.31 seconds)**. It
excludes prior invocations and input verification and is not total evaluation
time, app latency or a time-saving measurement.

## Fixed scope and two reporting arms

The full official test contains **102 documents, 99 frozen families, 41 CUAD
categories and 2,643 gold spans**. All documents retain all 41 questions,
including no-answer, zero-output and processing-incomplete questions.

The predeclared sensitivity slice contains **93 documents, 92 families, 3,813
questions and 2,441 gold spans**. It removes the nine previously confirmed
overlap documents and retains both unresolved documents and confirmed test-only
families. The exact titles are recorded in the report. This is known-overlap
sensitivity, not a guarantee that all overlap has been eliminated.

Both arms were fixed before test scoring; neither can be selected or promoted
using the results:

| Arm | Frozen computation | Meaning |
|---|---|---|
| Actual candidate analyzer | Original source text; unchanged positive-margin disjoint decoder; all windows; batch 1; CUDA FP16 autocast/SDPA, CPU FP32/SDPA; no global candidate cap | Anchored accuracy of the actual candidate-only pipeline on CUAD text |
| Clean checkpoint through authors reference path | Same exported checkpoint weights; pinned slow tokenizer; length 512, stride 256, query limit 64, answer limit 512, n-best 20; FP32/eager, batch 1, deterministic algorithms | Official benchmark comparison with the authors' pinned released predictions |

TF32 is disabled in both arms. The reference path preserves the original
word-set Jaccard, Parties substring, threshold-grid and final-point behavior.
Its n-best `probability` is an uncalibrated benchmark weight and never becomes
core confidence. The authors' released model used the original training pool;
the clean checkpoint used the frozen fit subset. This is not an equal-training
controlled experiment. The reference path is a reporting arm, not another
decoder experiment or the deployed analyzer's accuracy.

## Actual candidate-analyzer results

Anchored scoring uses one-to-one maximum-total character-IoU matching at
IoU >=0.5. Exact boundaries are counted separately. All gold remains in recall.

| Slice | Candidates | TP | FP | FN | Precision | Recall | Exact matches | Exact-match recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full official test | 8,174 | 1,797 | 6,377 | 846 | 21.984% | 67.991% | 1,488 | 56.300% |
| Known-overlap sensitivity | 7,641 | 1,659 | 5,982 | 782 | 21.712% | 67.964% | 1,366 | 55.961% |

Full-test micro F1 is **33.225%** and macro category F1 **35.226%**; sensitivity
micro F1 is **32.910%** and macro F1 **34.962%**. These describe review candidates,
not accepted findings or calibrated decisions. The actual accepted set is empty:
precision undefined/null, recall zero, and all gold missed by that empty set.
Zero false accepted findings is not a quality pass. No absence decision or
absence error rate is produced.

| Count per document | Full mean | Full p95 | Full max | Sensitivity mean | Sensitivity p95 | Sensitivity max |
|---|---:|---:|---:|---:|---:|---:|
| False candidate highlights | 62.52 | 198.25 | 597 | 64.32 | 179.00 | 597 |
| Missed gold spans | 8.29 | 18.85 | 31 | 8.41 | 17.20 | 31 |
| Returned review candidates | 80.14 | 219.40 | 663 | 82.16 | 212.80 | 663 |

This is a noisy suggestion pool. A benchmark false positive is an unmatched
prediction under the category/span criterion, not an importance judgment or a
new negative training label. No formal workload study or efficiency claim is
added.

The fixed 2,000-replicate whole-family bootstrap, seed 20261029, reproduces these
descriptive 95% percentile intervals:

| Metric | Full official test | Known-overlap sensitivity |
|---|---|---|
| Candidate precision | 19.618%–24.766% | 19.245%–24.618% |
| Candidate recall | 65.581%–70.329% | 65.311%–70.345% |
| Exact-match recall | 53.750%–58.877% | 53.297%–58.538% |
| False candidate highlights/document | 47.89–79.63 | 49.36–83.31 |

All replicates are defined. Intervals are conditional on fixed outputs and do
not include model/calibrator refit uncertainty. No confidence intervals for the
official benchmark metrics are claimed.

## Completeness, support and abstention

All planned candidate windows ran, but **1,176/4,182 questions remain
processing-incomplete**: 1,122 have first-64 question truncation, 68 have boundary
review flags, and 14 have both. Those questions contain 678 gold spans and 2,431
candidates. Completion of collection does not erase these limitations.

There are **2,242 zero-candidate questions**, including **36 with gold**. All
4,182 category states are `abstained`, with appropriate reasons and completeness
flags. Every emitted finding is `review_candidate`, model-origin,
null-confidence and unvalidated. Zero output never means absence.

| Full-test stratum | Questions | Gold | Candidates | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| No gold | 2,938 | 0 | 1,668 | 0 | 1,668 | 0 |
| One gold | 762 | 762 | 2,659 | 666 | 1,993 | 96 |
| Multiple gold | 482 | 1,881 | 3,847 | 1,131 | 2,716 | 750 |
| Processing complete | 3,006 | 1,965 | 5,743 | 1,348 | 4,395 | 617 |
| Processing incomplete | 1,176 | 678 | 2,431 | 449 | 1,982 | 229 |

The first three rows partition by gold count; the last two partition the same
questions by completeness. They must not all be added together. Among no-gold
questions, 732 return at least one candidate.

Sensitivity retains 1,074 processing-incomplete questions and 2,000 zero-output
questions, including 30 with gold. All 3,813 sensitivity category states are
abstained. In both slices, **16/41 measured categories have sparse support**
under the fixed gold/positive-family/no-gold-family rule. The others are not
thereby validated: all 46 catalogue entries remain `not_validated`, and the five
India extensions remain unavailable for inference. Rules and retrieval are
deferred. Neutral manual review and full-source access remain unchanged; only
accepted findings contribute coverage.

## Official benchmark comparison

These scores are for the authors reference inference/scoring path and must not
be presented as the actual disjoint analyzer's accuracy.

| Slice and weights | Official AUPR | Official P@80R | Official P@90R |
|---|---:|---:|---:|
| Full: clean checkpoint | 43.635% | 0.000% | 0.000% |
| Full: authors released reference | 42.586% | 31.131% | 0.000% |
| Sensitivity: clean checkpoint | 44.024% | 0.000% | 0.000% |
| Sensitivity: authors released reference | 42.992% | 31.008% | 0.000% |

Clean-minus-released AUPR is **+1.049 percentage points** on full test and
**+1.032 points** on sensitivity. This does not establish overall superiority:
the P@80R result is worse and training exposure differs. Original-evaluator
parity errors reported by the local run are at most **5.56e-17**.

The zero P@80R is expected under the unchanged evaluator. Its P@recall lookup
omits the last curve point. The clean checkpoint reaches only **76.617%** recall
on that lookup grid (**77.018%** sensitivity). Including the omitted final point
raises maximum recall to **85.358%** (**85.416%** sensitivity), but does not change
the official P@80R result. The zero does not mean zero correct predictions.
No alternate threshold grid, operating cutoff or post-test tuning is adopted.

## Reviewed evidence and limits

The supplied `identity.json`, `report.json`, `official_curves.json` and
`predictions.json` were reviewed on October 30. Their canonical hash bindings,
predeclared config, embedded frozen operating policy, question coverage and
family/sensitivity memberships agree. Eleven producer files available at remote
main `8614cc1` match their recorded LF-normalized hashes. The three new
final-evaluation producer files were not supplied as source in this review;
their digests remain recorded in the identity. Tanishq reports all 35 tests pass.

From the supplied predictions and gold spans, the review reproduced every
anchored question count, aggregate, category/document/family result, stratum,
support flag, distribution and fixed bootstrap interval. It checked strict
contract schemas, null-confidence statuses, source-ID/hash bindings, span text
lengths, finding IDs and disjointness. The clean checkpoint's saved reference
predictions reproduce all official curve counts and scores. Both arms' curve
arithmetic, original-evaluator metric agreement, maximum recalls and score
differences also agree.

Full source strings, model weights, raw per-question cache records and the
authors' released raw predictions were not attached. Exact source-slice equality,
model provenance and cache validation are checks of the local runner, not newly
re-executed checks in this review. Released-reference candidate matching and the
unmodified original evaluator were not independently rerun here. Hash consistency
is not a substitute for those distinctions. No new audit or inference rerun is
required to close this supplied-evidence review.

Keep generated JSON unchanged, including its creation-time status
`final_frozen_evaluation_complete_review_pending`. This dated Markdown records
review closure without rewriting the frozen evidence.

## Artifact identities

All values below are SHA-256 of canonical JSON except the explicitly labelled
weights byte hash.

| Artifact | SHA-256 |
|---|---|
| Final config | `49dcbe415aa08384e238bfc4737edd1375d9154e3f95ebb713630c5db2bdeea9` |
| Final identity | `0de0bbd440ebc2ba3797c84e82c18dd074ba9b6a42d36f055a849bd531946a7c` |
| Final report | `83d670a3f90b41a5ba289112ee2465620a7617ba774689af0519ef95ed11cf6d` |
| Official curves | `02d2e7507b777137cc61a9ab9496b41b3767b4cde1218dab5e390c03acd9f769` |
| Predictions | `2c57488f550c3119bd01382b7da86a7f29d56f80794c44b702b74c536ab2627f` |
| Frozen operating policy | `63141c142fee44491c3d4830229b02d5d1d73880861ce9ab2884fbad96780310` |
| Inference manifest | `ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8` |
| Weights, byte hash recorded at export | `cd508f9eb20d43047dcfbefe37be0c32ff17f14712ce09aa9f263fbb8320ab36` |

## Reproduction and remaining release work

Preserve `data/processed/cuad/final_evaluation_v1/` and the verified model bundle
locally, outside Git. Results are under `results/`; identity is at the run root.
The existing runner verifies saved identities and records before reuse. A valid
complete cached run returns without collecting or scoring again. Do not delete
records to force a fresh test run, change device/settings within an identity,
or use test results to revise extraction, calibration or policy.

The original commands, retained for reproduction rather than a requested rerun:

```powershell
conda activate clauseanchor
python -m unittest discover -s ml/tests -p "test_cuad_final_evaluation.py"
python ml/scripts/run_cuad_final_evaluation.py --device cuda
python ml/scripts/run_cuad_final_evaluation.py --device cuda --full
```

Packaging/integration checks are next, due November 6: verified CPU loading,
source-offset and partial-state behavior, progress/cancellation and the app
boundary if Aryan's integration is available. Existing smoke evidence is retained
in [RealAnalyzer.md](RealAnalyzer.md); it is not an app benchmark. Tanishq owns
`ml/` and `docs/ml/`; Aryan owns parser/backend/frontend/deployment. Name missing
live integration explicitly. Release handoff is due November 7 with the same
candidate-only label and measured limitations. No decoder variant, recalibration,
retraining, source-audit prerequisite or formal workload study is added.
