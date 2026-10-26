# ML phase status

Updated: 2026-10-26. Owner: Tanishq Arya.

| Phase | Status | Completion gate |
|---|---|---|
| 1. Interface | Core locally verified; teammate integration pending | Preserve the version 2.0 contract and exact offsets; confirm the backend adapter and all four category states |
| 2. CUAD data and official baseline | Frozen partitions and released-model baseline recorded | Preserve source/family exclusions and split provenance; keep released-model baseline metrics separate from the newly trained model |
| 5. Clean-split extraction training | Completed training run; selected checkpoint recorded | `clean_training_v1`: three epochs, 3,474 optimizer updates; best `checkpoint-000022`; recovery and completed state verified |
| 6. Evaluation and calibration | Source-span evidence reviewed; boundary/selection experiment, calibration and operating policy pending | Complete the ordered gates below before declaring usable calibrated category decisions |
| 7. Rules and corpus adapters | Pending | Reviewed rule tests, verified judgment provenance and licenses |
| 8. Retrieval | Pending | Exact passages, BM25/dense/hybrid comparison, labeled evaluation |
| 11. ML artifact release | Pending | Frozen model/decoder/calibration/policy artifacts, final evaluation, support limits, CPU benchmark and reproduction |
| 12. Joint integration | Pending | Real local demo, honest partial states, exact highlighting and measured review workload |

Keep the numbering aligned with ClauseAnchor_Plan.md. Phases 3, 4, 9 and 10 are primarily Aryan's app work. Update observed results after running each gate; do not mark future work complete because files have been named.

## Current handoff

- Last confirmed committed code: `ae8a8ec` (`feat(ml): add verified CUAD source error review and record findings`).
- User-reported local verification: 367 CUAD tests passed; the source-span
  exporter reproduced saved candidates, score curves and the diagnostic report.
- Handoff review on 2026-10-26: all 410 ML tests passed on the committed code
  (367 CUAD plus 43 core/interface and scope tests), with no skips. This is
  software verification, not a new model-quality measurement.
- Full development coverage: 39 documents, 41 categories, 45,748 windows and
  935 annotated answer spans. Original coordinates, scores and match counts
  reproduced exactly for every question.
- The latest completed run is source-span error-review export. All 155 exported
  cases have received an exploratory assistant review; annotation adjudication
  remains separate. No new training or inference was performed by that export.
- Review and measured limitations: [CUAD_DecoderReview.md](CUAD_DecoderReview.md).
- Source findings and the next experiment: [CUAD_SourceErrorReview.md](CUAD_SourceErrorReview.md).
- `disjoint_full` remains the primary comparison for the next experiment. It has not
  been adopted as an automatic-highlight policy, and the original checkpoint
  selection and training score remain unchanged.

## Ordered Phase 6 gates

### 6.1 Record the completed decoder review

Status: completed and recorded in CUAD_DecoderReview.md. No inference code,
model weights or catalogue support statuses were changed by that review.

### 6.2 Diagnose score quality on dev_select

Status: completed. `score_diagnostic_v1/report.json` and `curves.json` were
produced; the supplied report's bindings, arithmetic and document-bootstrap
calculations were checked. The source-span exporter also reproduced the complete
curves from saved candidates before collecting source examples.

Observed `disjoint_full` results on 935 gold spans:

| Diagnostic setting | Precision | Recall | Matched | False highlights | Missed gold |
|---|---:|---:|---:|---:|---:|
| Positive-margin baseline | 25.694% | 69.305% | 648 | 1,874 | 287 |
| Empirical precision >=90% | 90.041% | 23.209% | 217 | 24 | 718 |
| Empirical precision >=95% | 95.385% | 13.262% | 124 | 6 | 811 |

These use overlap matching; exact matches at the two filtered points are 199
and 116. The fixed-cutoff descriptive precision intervals are 86.574%-93.470%
and 91.851%-98.462%; they do not correct for selecting the cutoff on these data.
At the 90% point, governing law retains 33/36 gold spans, cap on liability 6/42,
and uncapped liability 0/10. Global precision is not a per-category guarantee.
Filtering exposes a cleaner subset, but these results do not establish useful
coverage for broad document review or quality on new documents.

Reuse `decoder_validation_v1/questions/*.json`, its identity and report, the
selected checkpoint's reference evaluation and the frozen source. Verify their
bindings and reproduce the recorded comparison before computing new results.
The summary report alone does not contain the candidate margins required for
this diagnostic. No additional GPU inference or weight updates are planned.

Use `disjoint_full` as the primary candidate and the original decoder as the
reference. Keep top-one as a diagnostic, since a category can have multiple
valid occurrences. Measure:

- Precision and recall as the raw score cutoff changes, with whole score ties
  handled consistently and one-to-one span matching recomputed for each set.
- Empirical recall at 90% and 95% precision, or an explicit unattainable result.
  These are diagnostic targets, not achieved quality claims or release gates.
- Exact-boundary matches, single-answer and multiple-answer results, category
  support counts, and false positives on genuinely absent categories.
- False highlights per document, missed spans per document and the distribution
  across documents, rather than only a pooled mean or macro F1.
- Uncertainty assessed at document level; avoid treating windows or related
  spans within a document as independent evidence. Flag sparse categories.

These curves are exploratory development results. Do not export a production
threshold or claim held-out performance from the best point on a dev_select
curve. A higher cutoff may reduce both false highlights and genuine findings.
For a fixed candidate pool, filtering cannot recover a missing candidate.

### 6.3 Decide whether the current extractor can support useful filtering

Status: export completed and all 155 cases reviewed by the assistant; a bounded
decoder experiment and the final extraction/scoring design remain pending.

The exporter produced `error_review_v1/report.json` and `review.md`. Its counts,
source evidence and bindings were checked. The separate
[source review](CUAD_SourceErrorReview.md) records observations for all 24 false
highlights, all 18 inexact matches and the 113 targeted missed-span examples.
Keep the generated report and original annotations unchanged; assistant review
does not change the report's human-adjudication status or benchmark scores.

At the exploratory 90% point, the 718 misses comprise 438 below-cutoff cases,
58 suppressed cases, 86 with only nonpositive eligible saved candidates, and
136 without an eligible saved candidate. These stage labels are observations,
not confirmed causes or guaranteed recoverable counts. Of the misses, 689 have
a usable complete target window, 20 exceed 256 tokens and 9 lack a regular
window containing the full target. Parties accounts for 100 of the 136 misses
without an eligible saved candidate.

The reviewed evidence includes merged clauses suppressing separate answers,
entity/date extent differences, repeated occurrences and genuine category
mistakes. The targeted miss sample is not a prevalence estimate. A benchmark
false positive is not automatically a verified negative training example.

Next, define and evaluate a small versioned boundary-aware candidate-selection
comparison on the saved candidates and source text, with fixed model weights.
Preserve alternative answer boundaries and multi-span capability; do not choose
boundaries using gold annotations. Compare the full dev_select results against
disjoint_full and the original decoder at comparable empirical precision and
false-highlight burden. Record exact-boundary and multiple-answer recall,
category regressions and sparse support. Keep calibration and deployment-policy
selection pending until a justified extraction/scoring design is frozen.

If score separation is useful, freeze the candidate generation, decoder, score
features, matching definition and selected checkpoint before calibration. If
it is inadequate, record the specific failure and evaluate the smallest
justified change, such as candidate coverage, a verifier or further fine-tuning.
Do not initiate retraining solely because the fixed-margin F1 is low. Do not
promise that calibration alone can repair a weak extractor.

Any model, candidate or scoring change starts a new versioned experiment and
requires renewed development validation. It must not reuse incompatible saved
results or quietly overwrite the completed training/validation runs.

### 6.4 Fit and assess confidence calibration on dev_cal

Status: pending a frozen extractor and scoring design.

Use only `dev_cal` to fit the calibration component. The extractor's weights
remain fixed during this step. Evaluate probability reliability with an
appropriate held-out or out-of-fold check within that calibration procedure;
training fit alone is not validation. Record the scope, sample counts and
uncertainty of every category-specific or pooled calibration claim.

A score is not a probability merely because it is high or transformed to the
interval [0, 1]. Confidence remains null outside validated scope. Simple score
rescaling cannot create missing answers or guarantee useful ranking.

### 6.5 Select the operating policy on dev_policy

Status: pending calibrated outputs from the frozen pipeline.

Before selecting thresholds, record the acceptance criteria for precision,
minimum useful recall, false highlights per document, absence errors and
supported scope. Choose operating thresholds on `dev_policy`, separately from
calibrator fitting. Report achieved rates, denominators and uncertainty; high
precision on a tiny number of returned answers is not a sufficient success.

Preserve the existing [core interface](Interface.md):

- `found`: at least one accepted occurrence; additional occurrences may remain
  unresolved.
- `abstained`: insufficient evidence for a supported final decision; return a
  reason instead of automatic low-confidence highlights.
- `unavailable`: required processing or capability did not run.
- `absent`: complete eligible search and a separately validated absence
  decision. Filtering out all candidate spans is not proof of absence.

Preserve the [catalogue support vocabulary](CategoryCatalogue.md). A category
does not become `validated` from a nonzero development F1. Pooled support must
be explicitly documented, and the five India extensions are not validated by
CUAD results. Parser limitations and partial coverage must remain visible.

If policy selection exposes a need to redesign the model or score features,
record that the policy data has influenced development and revise the evaluation
protocol. Do not silently turn dev_policy into another unrestricted tuning set.

### 6.6 Freeze and evaluate the complete pipeline

Status: pending the preceding gates.

Freeze model, tokenizer, candidate generation, decoder, calibrator, policy and
supported categories before final evaluation. Evaluate the declared benchmark
scope and required overlap-sensitivity slice separately. The previously run
released-model official baseline is not a final result for this trained model.
Do not use official-test results to tune thresholds or choose decoder variants.

For the intended product scope, add a separately annotated, representative
document evaluation before generalizing from CUAD to arbitrary uploads. Keep
new evaluation documents outside development and respect document/family
grouping. Report misses as well as false highlights and abstentions.

## Workload validation and remaining product work

At joint integration, measure review time and correction effort with and without
ClauseAnchor on comparable documents. Account for order/learning effects and
inspect missed clauses, not only the highlights users see. A release must meet
the recorded extraction and support criteria and demonstrate useful assistance;
the existence of an interface is not evidence that review work is reduced.

The subsequent rules, corpus adapters, retrieval, artifact packaging and joint
integration phases remain in the plan. A future stronger verifier or retraining
branch is conditional on measured failures; neither is started by this update.

## Working cadence

Prepare one small batch, install it in VS Code, run its relevant checks, review
the actual output, then commit and push through VS Code Source Control. Supply
a descriptive commit message rather than terminal Git commands. Keep weights,
feature arrays, saved candidate records and generated JSON reports outside Git;
commit code, tests, configurations and measured Markdown summaries.
