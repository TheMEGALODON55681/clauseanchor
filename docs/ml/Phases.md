# ML phase status

Updated: 2026-10-31, Asia/Calcutta. Owner: Tanishq Arya.

| Phase | Status | Completion gate |
|---|---|---|
| 1. Interface | Core and trained local DOCX/parser/API path verified; frontend check pending | Preserve the version 2.0 contract and exact offsets; retain all four core states with candidate-only runtime decisions |
| 2. CUAD data and official baseline | Frozen partitions and released-model baseline recorded | Preserve source/family exclusions and split provenance; keep released-model baseline metrics separate from the newly trained model |
| 5. Clean-split extraction training | Completed training run; selected checkpoint recorded | `clean_training_v1`: three epochs, 3,474 optimizer updates; best `checkpoint-000022`; recovery and completed state verified |
| 6. Evaluation and calibration | Final frozen evaluation completed and reviewed October 30; calibration unvalidated; candidate-only policy retained | Keep confidence null; report measured limitations; no test-based tuning |
| 7. Rules and corpus adapters | Deferred beyond this release | Reviewed rule tests, verified judgment provenance and licenses |
| 8. Retrieval | Deferred beyond this release | Exact passages, BM25/dense/hybrid comparison, labeled evaluation |
| 11. ML artifact release | Portable package and isolated CPU check completed/reviewed; release handoff prepared October 31; transfer/recipient verification pending | Preserve package/evidence hashes and measured support limits; hand off by November 7 |
| 12. Joint integration | Trained local DOCX/parser/API/CPU check completed and reviewed October 31; frontend/PDF/network/deployment unverified | Real local demo, honest partial states, exact highlighting and runtime; formal workload study deferred |

Keep the numbering aligned with ClauseAnchor_Plan.md. Phases 3, 4, 9 and 10 are primarily Aryan's app work. Update observed results after running each gate; do not mark future work complete because files have been named.

## Fixed release window: October 29–November 7, 2026

Deadlines are end of day Asia/Calcutta. October 28 is preparation; do not reset
the clock in a later chat. This is an extraction-focused research prototype,
not completion of rules, retrieval, India validation or the original programme.

| Deadline | Deliverable and exit condition |
|---|---|
| October 30 | Completed/reviewed October 28: real candidate-only AnalyzerProtocol adapter, checkpoint-000022 export and non-fixture smoke. See [RealAnalyzer.md](RealAnalyzer.md). |
| October 31 | Closed October 29: the one decoder variant failed its fixed gate; retain and freeze `disjoint_full`. No second experiment. |
| November 2 | Completed October 29: the one predeclared calibration assessment failed its bin-gap criterion; confidence stays null and scope unvalidated. |
| November 4 | Completed October 29: fixed dev_policy measurement reviewed; retain candidate-only output with documented limitations. Unsupported decisions stay abstained/unavailable; absence remains disabled. |
| November 5 | Completed and reviewed October 30: final frozen actual-analyzer evaluation and separate official reference comparison on full test and required sensitivity. No test-based tuning. |
| November 6 | Package CPU checks and trained local ASGI DOCX/parser/API integration completed/reviewed October 31. Frontend highlighting, PDF integration, network-server and deployment checks remain unverified; record their actual outcome. |
| November 7 | Versioned candidate-only package and reviewed limits are ready; [release handoff](ReleaseHandoff.md) prepared October 31. Artifact transfer and recipient acknowledgement remain unconfirmed. Fixes/handoff only, no further experiment. |

## Current handoff

- Remote main rechecked October 31: `06d615cc39104b547130cf6b79a57413ac624373`.
  Tanishq's four-file API verification commit `06d615c` is present. His packaging
  commit `4e137e9` is merged; his seven-file final-evaluation
  commit is `93d2942`. Aryan added catalogue
  loading (`829ac16`), document upload/parse jobs (`53f2ed1`) and analyzer-backed
  jobs (`49c2c17`). The real CPU analyzer path now exists, including parser
  context, progress/cancellation and partial states. Those commits were initially
  checked by source inspection; the trained local run is recorded below. The
  recent app commits leave ML unchanged.
  The prior empty phase document was restored at `f4b6500`; no repair is pending.
- First real adapter batch locally verified October 28: checkpoint-000022
  inference-only export, candidate-only adapter and non-fixture CPU smoke.
  Tanishq's 32 focused tests passed in 11.751 seconds; all 9 smoke windows ran,
  producing 5 unvalidated candidates. Load 24.35 seconds; inference 3.97 seconds
  on this one input. Supplied report passed independent contract/source-slice
  and receipt-binding checks. Actual artifact hashes and observed bad/overbroad
  candidates are recorded in [RealAnalyzer.md](RealAnalyzer.md).
- Cap-on-liability remains processing-incomplete because of first-64 question
  truncation; the India extension is unavailable. This is not complete app
  integration or validated extraction quality. No training/diagnostic rerun or
  decoder experiment occurred in that adapter batch. The October 30 local-adapter target is met early;
  the October 29–November 7 execution window and later deadlines are unchanged.
- User-reported local verification: 367 CUAD tests passed; the source-span
  exporter reproduced saved candidates, score curves and the diagnostic report.
- Handoff review on 2026-10-26: all 410 ML tests passed on the committed code
  (367 CUAD plus 43 core/interface and scope tests), with no skips. This is
  software verification, not a new model-quality measurement.
- Full development coverage: 39 documents, 41 categories, 45,748 windows and
  935 annotated answer spans. Original coordinates, scores and match counts
  reproduced exactly for every question.
- The earlier source-span error-review export is complete. All 155 exported
  cases have received an exploratory assistant review; annotation adjudication
  remains separate. No new training or inference was performed by that export.
- Review and measured limitations: [CUAD_DecoderReview.md](CUAD_DecoderReview.md).
- Source findings: [CUAD_SourceErrorReview.md](CUAD_SourceErrorReview.md).
- The single decoder experiment completed October 29 at 00:53:54 IST.
  Tanishq's 32 focused tests passed in 4.960 seconds. The candidate added one
  matched gold span against the required 19, so the predeclared gate failed.
  Report/identity bindings, arithmetic and gate were reviewed; see
  [CUAD_DecoderExperiment.md](CUAD_DecoderExperiment.md) for hashes, results and
  review limits. Retain `disjoint_full` and freeze the existing extractor now,
  ahead of October 31. Decoder experimentation is closed; no second variant.
- This freeze does not adopt a production cutoff or automatic-highlight policy.
  Checkpoint, tokenizer, generation and raw-score definition remain unchanged.
  The real adapter keeps null-confidence, unvalidated review candidates and
  honest abstained/unavailable states; zero candidates never establishes absence.
- Calibration assessment completed October 29 at 02:04:04 IST, before the
  November 2 deadline. Tanishq's 37 tests passed in 10.843 seconds. All 1,558
  dev_cal questions / 68,405 windows were processed. The one method was assessed
  on 2,184 eligible candidates across 36 families; OOF Brier 0.103406 and ECE
  0.040156. Two bins exceeded the fixed 0.10 absolute-gap limit, so the result
  is **unvalidated**. All other assessment checks passed; 34/41 categories have
  sparse support. See [CUAD_Calibration.md](CUAD_Calibration.md) for measured
  results, hashes and review limits. Retain null confidence and candidate-only
  behavior; no additional method or retraining attempt follows.
- Candidate-only policy measurement completed October 29 at 16:55:33 IST and
  its supplied evidence was reviewed. Tanishq's 32 tests passed in 8.674 seconds.
  After VS Code closed, collection resumed: 734 saved + 2 pilot + 822 final new
  questions = 1,558. Coverage is 38 documents / 37 families / 41 categories /
  54,622 windows / 991 gold spans. No training restart occurred.
- The fixed policy returned 3,128 review candidates: 680 TP / 2,448 FP / 311 FN,
  precision 21.739%, recall 68.618%, 564 exact matches. Mean false candidate
  highlights/document is 64.42; 433 questions remain processing-incomplete,
  741 have zero candidates, and 33/41 categories have sparse support. These
  limitations do not justify automatic acceptance. See
  [CUAD_CandidatePolicy.md](CUAD_CandidatePolicy.md) for hashes, uncertainty,
  strata, restart accounting and review limits. Retain null confidence and the
  unchanged candidate-only policy; its final test evaluation is recorded below.

- Final evaluation completed October 30 at 10:15:24 IST and the supplied
  evidence was reviewed. Tanishq's 35 focused tests passed in 80.387 seconds
  after the one-line Windows test-path normalization fix. Both arms contain
  all 4,182 questions; the final invocation reused the entire candidate arm
  and completed the remaining 411 official-reference questions. This was
  resumed evaluation inference, not training. No recollection is required.
- Actual analyzer full-test results: 8,174 review candidates, 1,797 TP / 6,377 FP /
  846 FN, precision 21.984%, recall 67.991%, 1,488 exact matches. Sensitivity
  precision is 21.712%, recall 67.964%. There are 1,176 processing-incomplete
  full-test questions and 2,242 zero-output questions, including 36 with gold.
  Automatic acceptance and absence remain disabled; all categories unvalidated.
- The separate clean-checkpoint authors-reference path has official AUPR
  43.635% versus the released reference's 42.586%. Clean P@80R and P@90R are zero
  under the unchanged official lookup grid; these are not deployed-analyzer
  accuracy. See [CUAD_FinalEvaluation.md](CUAD_FinalEvaluation.md) for both
  slices, uncertainty, score interpretation, hashes, resume accounting and
  review limits. Final evaluation is closed early; packaging/integration remains
  due November 6 and release handoff November 7.

- Portable package built and isolated CPU smoke completed October 31 at
  13:56:32 IST; supplied receipt/report/binding review passed. Tanishq's 23
  packaging tests passed in 76.350 seconds. The previously delivered 17 neutral
  manual-review fixture tests also passed assistant-side; that feature is unchanged.
- Release `clauseanchor-candidate-prototype-v0` has outer manifest SHA-256
  `29b4553786eb4e9f8cba8f6fb2244358406d101e460f77f3200542386ff84184`.
  The receipt records a 509,869,238-byte ZIP. CPU load was 25.81 seconds; the
  full authored-source call took 3.34 seconds and completed 8/8 windows with
  seven candidates. Partial and limited calls added three returned slices;
  all 10 exact source slices and candidate-only fields passed independent review.
- Cancellation before inference/after one window, work-limit denominators,
  all five unsupported India categories and simulated partial parser/decoration
  transport behaved as declared. All confidence remains null; no acceptance
  or absence is enabled. These are package checks, not new accuracy measurements.
- Preserve the tested ZIP, source, original instructions and generated JSON.
  [CandidateReleaseVerification.md](CandidateReleaseVerification.md) records the
  hashes, observed results, noisy outputs and review limits separately from the
  immutable package snapshot. No rebuild or model/evaluation rerun is required.
  At that package-check stage, actual parser/API/UI integration and deploy-host
  loading were unverified. The following local DOCX/API check closes part of
  that gap; November 6/7 deadlines are unchanged.
- Trained Windows local DOCX/parser/API/CPU check completed October 31 at
  14:28:33 IST and supplied evidence review passed. Tanishq's 18 tests passed
  in 7.208 seconds. Actual app startup to readiness took 17.47 seconds. Complete
  and genuinely partial DOCX calls finished 4/4 and 5/5 windows, returning five
  candidates each in 1.86 and 2.01 seconds of API analysis wall time.
- All 10 returned slices match the parser's exact source coordinates; core/API
  results, hashes, reasons, progress and header exclusion agree. The complete
  call is processing-complete but resolves zero decisions. The partial call
  preserves omitted-content/query-truncation warnings, incomplete searches and
  unavailable India arbitration. Confidence remains null and scope unvalidated.
  A newline and unrelated service-report sentence remain noisy governing-law
  candidates; exact slicing is not evidence of correct clause extraction.
- Cancellation requested at 1/105 windows stopped at 2/105, returning no completed
  result. Session deletion returned 204 and old-token access 401. See
  [CandidateAPIIntegration.md](CandidateAPIIntegration.md) for measured evidence,
  hashes and review limits. This uses local ASGI requests and the real parser
  subprocess/model, not a network server. Frontend highlighting, PDF integration
  and deployment remain unverified. No model/evaluation rerun, frozen artifact,
  backend or manual-review change is required; release handoff remains pending.
- [ReleaseHandoff.md](ReleaseHandoff.md) now prepares the final extraction-release
  handoff: exact local ZIP/companion paths, independent artifact hashes, recipient
  loading instructions, frozen quality limits and named app gaps. The tested ZIP
  and packaged pre-build documents remain unchanged. This is documentation only;
  no new experiment, inference collection, test suite or rebuild is needed.
  Artifact transfer and recipient verification have not been confirmed, so the
  release is not labelled delivered or deployed. Keep November 6/7 and record
  remaining app checks honestly; deferred ML scope stays deferred.

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

Status: completed October 29. All 155 source-review cases remain reviewed; the
single allowed decoder experiment failed its promotion gate. The existing
checkpoint/tokenizer/generation/disjoint decoder/raw-score definition is frozen.

The one candidate was predeclared as `near_score_sentence_pack_v1` in
`ml/configs/cuad_decoder_boundary_v1.json`; algorithm and fixed gate are in
[CUAD_DecoderExperiment.md](CUAD_DecoderExperiment.md), with the reviewed result
and frozen artifact hashes. The runtime adapter/export remains unchanged.

At the fixed whole-tie comparison points, the reference has 217 TP / 24 FP /
718 FN, 199 exact matches and 78 matches in multiple-gold questions. The candidate
has 218 / 24 / 717, 200 exact and 79 multiple-gold matches. Its +1 TP misses the
required +19. There are no category regressions at those selected points; 26/41
categories have sparse support. The candidate has one extra Non-Compete FP at
the positive-margin baseline. Neither result validates probabilities or broad
review quality. Keep the existing reference; do not promote the diagnostic raw
cutoff to the app. Calibration and operating-policy decisions remain separate.

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

The completed source review motivated the ONE decoder experiment, now closed.
No further source-audit prerequisite, unfamiliar-clause classifier,
verifier, hyperparameter sweep, extra dev_select candidate collection or retraining
branch is in this release. Real integration continues using the frozen existing
disjoint reference. Section 6.5 retains its positive-margin pool as unvalidated
review candidates; it establishes no automatic-acceptance cutoff.

The deterministic algorithm and following promotion rule were written into a
versioned config before execution. Checkpoint-000022 stayed fixed; only saved
candidates/source were used. Gold scored outputs without generating or selecting
boundaries. No document-specific rules or source-annotation changes were made.

The predeclared rule, retained for the record: on all 1,599 dev_select questions /
935 gold spans, choose each decoder's
highest-recall whole-tie operating point satisfying BOTH empirical precision
>=90% and at most 24 false highlights. Recompute the existing disjoint reference
under the same rule; retain the original-decoder comparison. Promote the one
candidate only if it adds at least 19 matched gold spans, with no decrease in
exact-match count or matched spans in multiple-gold questions, and passes all
source-integrity/provenance checks. Report category regressions and sparse
support. If any gate fails, evidence is missing or time expires, retain the
existing disjoint reference. Freeze by October 31 either way.

This is an engineering decision on explored development data, not calibrated
confidence or a production quality guarantee. No new variant follows failure.
Freeze checkpoint, tokenizer, generation, decoder and score definition before
calibration. A post-freeze correctness repair gets a new artifact identity and
explicit downstream revalidation; do not hide its deadline cost.

### 6.4 Fit and assess confidence calibration on dev_cal

Status: assessment completed and reviewed October 29; **unvalidated**. The
November 2 assessment deliverable is met with an explicit failed reliability
gate. The frozen extractor and null-confidence candidate-only output remain.

The method was predeclared in `ml/configs/cuad_calibration_v1.json` and
[CUAD_Calibration.md](CUAD_Calibration.md): one pooled monotone regularized sigmoid,
five whole-family folds, out-of-fold reliability/support checks and the same-method
full refit. The target is candidate overlap eligibility, not exactness, absence or
one-to-one accepted precision. Processing-incomplete questions are excluded from
confidence fitting while all gold spans remain in miss/recall reporting. The new
runner opened dev_cal examples only and preserved frozen artifacts. All 37 focused
software tests passed before delivery and on Tanishq's machine. The supplied
identity, calibrator, report and OOF rows were reviewed; the unchanged procedure's
fits, predictions, metrics, family bootstrap and gate were reproduced from those
rows. No model inference or alternative-method experiment was rerun in that review.

Of 3,465 raw selected candidates, 2,184 were eligible for calibration (468
overlap-eligible, 1,716 ineligible). The [0.2,0.4) probability bin predicted
28.822% eligibility versus 16.429% observed; [0.6,0.8) predicted 69.433% versus
81.071% observed. Their 12.394- and 11.638-percentage-point gaps exceed the fixed
10-point limit. The overall ECE does not override this failure. No OOF values
reached 0.8, and 34/41 categories have sparse support. All categories remain
unvalidated; the fitted parameters stay offline with runtime activation false.
No gate relaxation, new calibration method or retraining branch follows.

Use only `dev_cal` to fit the calibration component. The extractor's weights
remain fixed during this step. Evaluate probability reliability with an
appropriate held-out or out-of-fold check within that calibration procedure;
training fit alone is not validation. Record the scope, sample counts and
uncertainty of every category-specific or pooled calibration claim.

A score is not a probability merely because it is high or transformed to the
interval [0, 1]. Confidence remains null outside validated scope. Simple score
rescaling cannot create missing answers or guarantee useful ranking.

### 6.5 Select the operating policy on dev_policy

Status: completed and reviewed October 29, ahead of November 4. **Retain the
existing candidate-only v0 policy.** Config and evaluation rules were fixed
before dev_policy. Calibration failure already blocked automatic acceptance;
no threshold search, calibrator application, decoder change or retraining occurred.

The [policy document](CUAD_CandidatePolicy.md) records the predeclared engineering
requirements: validated confidence and complete processing, accepted precision
at least 95%, all-gold accepted recall at least 50%, mean false accepted highlights
per document at most 1 and p95 at most 3, plus minimum category evidence. The
actual accepted set is empty: precision null, recall zero on the 991 gold spans.
Zero accepted false positives is not a quality success; no absence decision or
absence error rate is produced. Candidate metrics cannot replace accepted metrics.

On all 1,558 dev_policy questions, the unchanged fallback returned 3,128 review
candidates with 680 anchored matches, 2,448 false highlights, 311 misses and 564
exact matches. Precision is 21.739%, recall 68.618%. The fixed whole-family
bootstrap gives descriptive 95% intervals of 18.505%–25.786% precision and
65.505%–71.667% recall. Mean false candidate highlights/document is 64.42
(p95 157.35, maximum 327); mean missed gold/document is 8.18. This is a noisy
candidate pool, not validated automatic extraction or measured review efficiency.

All windows completed; 433 questions still have truncation/boundary issues.
All gold remains in recall and incomplete candidates retain visible limitations.
There are 741 zero-output questions, including 15 with gold. All 1,558 projected
category states are abstained. All catalogue categories remain not_validated;
33 of the 41 measured categories have sparse support. India extensions remain
unavailable for inference. Neutral manual review is unchanged.

The assistant verified supplied hashes/code bindings, coverage and projection
invariants, and reproduced aggregation, support flags and the fixed family
bootstrap from the rows. Full source/gold and raw question records were not
attached; local source equality, matching and saved-record checks rely on the
hash-matched runner. No source audit, model rerun or new experiment is required.
Offline projections do not establish live parser/app integration. Preserve the
generated report's creation status; the dated Markdown review records closure.

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

Poor candidate quality is recorded. Do not redesign the model, fit another
calibrator or use dev_policy to choose a new cutoff. Retain the declared behavior
for the final frozen evaluation; no quality or release-readiness claim is added.

### 6.6 Freeze and evaluate the complete pipeline

Status: completed and reviewed October 30, ahead of November 5. The predeclared
protocol in `ml/configs/cuad_final_evaluation_v1.json` evaluated both fixed arms
on the full official test and known-overlap sensitivity. The frozen decoder,
failed calibration outcome and retained candidate-only policy remain unchanged.
No official-test result selects a threshold, model, decoder or calibration method.

The [final evaluation record](CUAD_FinalEvaluation.md) contains measured results,
artifact identities and explicit review limits. Full coverage is 102 documents /
99 families / 4,182 questions / 2,643 gold spans. Sensitivity contains 93 documents /
92 families / 3,813 questions / 2,441 gold spans, excluding nine already-reviewed
confirmed-overlap documents while retaining two unresolved documents.

The actual candidate analyzer's anchored precision/recall is 21.984%/67.991% on
full test and 21.712%/67.964% on sensitivity. Full-test false candidate highlights
per document average 62.52 (p95 198.25, maximum 597); missed gold averages 8.29.
The 95% descriptive whole-family intervals are 19.618%–24.766% precision and
65.581%–70.329% recall. Sixteen of 41 measured categories have sparse support;
all 46 catalogue entries remain not_validated. These measurements support an
honestly labelled noisy candidate-only prototype, not automatic acceptance or
validated absence. Null confidence and neutral manual review are preserved.

The separate authors-reference inference path yields clean-checkpoint official
AUPR 43.635% full / 44.024% sensitivity, versus released-reference 42.586% / 42.992%.
Clean P@80R and P@90R are zero because the preserved P@recall grid does not reach
those targets. This is not a claim of zero correct predictions or of overall
superiority from AUPR. It is also not the deployed disjoint pipeline's accuracy;
training exposure and inference settings differ between reporting contexts.

The supplied predictions reproduce all anchored matching and aggregate results,
support flags, fixed family bootstrap and clean-reference official curves. The
review checked contract/source-ID structural invariants and both arms' curve
arithmetic. Full source strings, weights, raw caches and released raw predictions
were not supplied; corresponding local checks were not independently rerun here.
Keep the generated JSON creation status unchanged; dated Markdown records review
closure. There is no new source audit, inference rerun or post-test tuning step.

Representative arbitrary-upload/India validation remains outside this release;
CUAD evidence cannot establish that scope. The portable ML package and isolated
CPU checks were completed/reviewed October 31, followed by the trained local ASGI
DOCX/parser/API/CPU smoke that day. Frontend highlighting, PDF integration,
network-server and deployment checks remain unverified; record actual outcomes
by November 6. Aryan owns parser/backend/frontend/deployment. Release handoff
remains November 7; do not imply complete app validation from the local smoke.

## Deferred scope and retained manual review

Rules, verified judgment corpus/retrieval, the five India extensions and the
Indian annotation/validation study remain deferred beyond this extraction
release. No dates beyond November 7 are promised. A formal controlled review-time
study is also parked; do not claim measured time savings without doing it.
Keep false highlights, misses, runtime and integration checks in this release.

Preserve full source access and the neutral manual-review navigation in
[ScopeFixtures.md](ScopeFixtures.md): only accepted findings contribute coverage;
review candidates remain separate. Incomplete work gives null completed inventory
and count. Zero candidates/items does not establish absence, harmlessness or that
nothing important was missed. Benchmark false positives are not an importance
classifier or automatic negative training labels. No additional source audit is
a prerequisite for the adapter, decoder freeze or calibration.

## Working cadence

Prepare one small batch, install it in VS Code, run its relevant checks, review
the actual output, then provide the exact staging list and descriptive commit
message for Tanishq to use in VS Code Source Control. Do not commit/push on his
behalf or supply terminal commit/push commands. Keep weights,
feature arrays, saved candidate records and generated JSON reports outside Git;
commit code, tests, configurations and measured Markdown summaries.
