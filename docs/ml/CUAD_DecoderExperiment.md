# The single bounded decoder experiment

Declared: October 28, 2026, before this variant's development results.
Result reviewed and reference frozen: October 29, 2026, Asia/Calcutta.
Owner: Tanishq Arya. Base: `74fc4b312410fc9e29eba82e7ef2eb4c3da579ee`.
**Freeze deadline: October 31, 2026, end of day Asia/Calcutta.**
The October 29–November 7 execution window remains unchanged.

The real candidate-only analyzer, verified local export and CPU smoke are already
complete. This batch performs the one optional selection experiment allowed by
the handoff. It does not modify that analyzer, its artifact hashes, source
annotations, scoring protocol, checkpoint-000022 or frozen producer files.
No new inference, training, source audit or unfamiliar-clause classifier is added.

## Reviewed outcome: retain disjoint_full; experiment closed

Tanishq's run completed on **October 29 at 00:53:54 IST**, before the October 31
deadline. All **32 focused tests passed in 4.960 seconds** on his environment.
The submitted report and identity match the predeclared config and runner.

At each decoder's reported highest-recall whole-tie point meeting both the
90% empirical precision and 24-false-highlight constraints:

| Decoder | Raw cutoff | Matched / 935 | False | Returned | Precision | Recall | Exact | Multiple-answer matched / 601 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| disjoint_full | 15.6513671875 | 217 | 24 | 241 | 90.041% | 23.209% | 199 | 78 |
| near_score_sentence_pack_v1 | 15.6513671875 | 218 | 24 | 242 | 90.083% | 23.316% | 200 | 79 |
| original_capped | 16.17822265625 | 166 | 18 | 184 | 90.217% | 17.754% | 155 | 59 |

**The gate failed:** the candidate added **1 matched gold span**, short of the
predeclared **19**. This is about **0.107 percentage points of recall**. Exact
matches and multiple-answer matches each increased by one; source-integrity,
feasibility and deadline checks passed in the local run. Those checks do not
override the failed gain requirement. Keep the existing `disjoint_full` decoder;
do not adopt, retune or run another candidate variant.

The selector changed two questions, in Renewal Term and Non-Compete. At the
selected global cutoffs, only Renewal Term's counts change: +1 TP, +1 exact,
-1 FN and no FP increase. There are no category regressions **at these selected
points**. This does not mean there are no regressions at every cutoff: at the
full positive-margin baseline, Non-Compete has one additional FP. That candidate
baseline totals 650 TP / 1,875 FP / 285 FN, compared with the reference's
648 / 1,874 / 287. All 41 category results remain in the report; **26 have sparse
support** under the predeclared rule. No category gains validated status.

At the selected point, both reference and candidate have mean 0.615 false
highlights/document, p95 2 and maximum 3 across 39 documents. The retained
reference still misses **718/935** gold spans at that exploratory point. These
are explored dev_select measurements, not calibrated confidence, held-out
performance, a broad-review acceptance result or measured time savings.

### Review evidence and limits

The assistant checked config/code hashes, report-to-identity binding, expected
coverage, aggregate arithmetic from all 1,599 question rows for each baseline
and selected point, single/multiple/no-gold strata, category deltas and support,
document totals/distributions, and the gate calculation. Existing tracked ML
files remain byte-identical to `74fc4b3`; the experiment added separate files.
The user's run checked raw/source provenance and computed the complete curves.
Raw candidate/source files, `curves.json` and the result manifest were not
attached to this review, so their contents and the global cutoff search were
not independently rerun here. No new source audit or experiment is required.

| Evidence | SHA-256 |
|---|---|
| Submitted report, canonical JSON | `55e7f255678ed124a8e8897d94199f22010ddba158fb530feca5aff8da34360d` |
| Submitted report, file bytes | `aa76e0a10875e78488e8437cc7d56a7970d5d3d2d522b8aa027699e2561caa42` |
| Experiment identity, canonical JSON | `fad88d65a5e3fbfb6758e085dbd02266355afcb38a8cb42fbe6dd54f71de43f2` |
| Submitted identity, file bytes | `835da5e91cbf23219622e2da136ea5a712342de838c35ece2f019be0b879e9d3` |
| Experiment runner, LF-normalized | `db03ff5eac93d61abb8813d224bc5889f8b0e0788c15c63e2b744656914478b6` |
| Existing curve scorer, LF-normalized | `3e5f2a3c1b4df15496fec51b57e4531a20cdc247fdf7ac902e3e434921a1809b` |
| Curves, canonical hash recorded by the run; file not attached | `ca8aa7e7692564652ece8c819dc2fb2b10e49b0fd9b483b705b0d94c404d7a78` |

Preserve the generated report's `single_decoder_experiment_complete_review_pending`
status and `decoder_adopted=false`: they describe the runner's state at creation.
This separate dated review records the decision; do not edit the report or identity.

### Extractor freeze

Freeze the existing candidate-only artifact at `models/clauseanchor_candidate_v0`:

- Checkpoint: `checkpoint-000022`; exported weights SHA-256
  `cd508f9eb20d43047dcfbefe37be0c32ff17f14712ce09aa9f263fbb8320ab36`.
- Artifact manifest canonical SHA-256:
  `ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8`.
  It binds the tokenizer, model config, category questions, decoder and runtime
  files; loading instructions and the previously verified smoke are in
  [RealAnalyzer.md](RealAnalyzer.md). No export or smoke rerun is needed for this
  documentation-only decision.
- Preserve the pinned tokenizer/source config `ml/configs/cuad_training_source.json`
  and artifact-bound implementation at `74fc4b3`. Sequence length 512, first 64
  question tokens, context overlap 128, answer limit 256, top 20 starts/ends and
  at most 20 pairs/window remain fixed.
- Preserve same-window start-plus-end minus CLS-start-plus-end raw margin,
  exact deduplication/tie and boundary-flag handling, then greedy `disjoint_full`
  suppression of positive character overlap; touching spans remain allowed,
  and there is no global top-50 cap. The v0 returns strictly positive margins.
- Preserve exact source slices, decoration handling and incomplete-processing
  reasons. CPU FP32/SDPA and CUDA FP16-autocast/SDPA remain separately identified
  runtime paths, without a claim of numerically identical predictions.

**Do not install 15.6513671875 as an application threshold.** It was only a
comparison cutoff on explored data. The running analyzer stays candidate-only:
`review_candidate`, null confidence, unvalidated scope, abstained/unavailable
categories with reasons, and no absence inferred from zero candidates. Neutral
manual review is unchanged. Calibration and operating policy are still pending.

## Predeclared algorithm: near_score_sentence_pack_v1

The completed source review showed some broad candidates suppressing separate
sentence candidates. This variant tests that narrow mechanism. It cannot repair
missing candidates, category confusion or general score quality. The fixed
1.0-point allowance is an engineering constant, not a tuned or calibrated value.

1. Use all existing raw candidates from `decoder_validation_v1`. Apply the
   existing exact deduplication, including its tie order and complete-window
   counterpart handling, then keep strictly positive raw margins.
2. Compute sentence units from immutable source using the exact regex in
   `ml/configs/cuad_decoder_boundary_v1.json`: `.`, `!` or `?`, optional closing
   quotes/brackets, then whitespace or source end. A unit begins after the prior
   terminal and intervening Unicode whitespace. It must contain an alphanumeric
   character. An unterminated tail is not a complete unit. There are no special
   category, document, abbreviation, heading or newline rules.
3. Scan candidates in the original exact-pool order. Skip a candidate if it
   positively overlaps an already kept interval; touching intervals are allowed.
4. For an otherwise eligible parent, find existing, properly contained candidates
   whose ranges exactly equal complete sentence units, have a resolved
   `boundary_review=false`, and have raw margins between parent margin minus
   **1.0** and parent margin, inclusive.
5. If **at least two** such sentence candidates exist, keep all of them instead
   of the parent. Otherwise keep the parent. The units are disjoint; no candidate
   is split, trimmed, concatenated or created. Existing offsets and scores remain.
6. Sort the resulting pool by descending original raw margin, with the original
   exact-pool index breaking ties. Curve filtering uses that unchanged raw margin.

Only source text and existing candidate geometry/scores enter the selector.
Gold annotations enter scoring only. A standalone punctuation candidate is not
automatically removed by this variant; it is not an extra cleanup experiment.
Abbreviations and valid multi-sentence answers may be mishandled by the heuristic.
Those possible losses must appear in the comparison, not be hidden or tuned away.

The pinned config's canonical SHA-256 is:
`42add96675125ab1d27a1eb5d1e828a2178a545195994c3c0fd4a8747745c485`.
The runner rejects config changes and has no algorithm/threshold/run-name flags.

## Fixed exit rule

Compare exactly three pools: existing `disjoint_full`, this one candidate, and
the original capped decoder. Use all **1,599 questions, 935 unique gold spans,
39 documents, 41 categories and 45,748 windows** from `dev_select`.

For EACH decoder, evaluate every distinct positive raw-margin cutoff with whole
equal-score groups. Recompute the unchanged one-to-one maximum-total eligible
character-IoU assignment (IoU >=0.5) when outputs change. Choose the highest-recall
point satisfying BOTH empirical precision **>=90%** and **<=24 false highlights**.
Break recall ties by higher precision, fewer outputs, then higher cutoff. Empty
outputs never satisfy the gate. No interpolation or cutting a score tie is allowed.

Recommend the candidate only if both it and the reference have feasible points,
the candidate finds **at least 19 additional matched gold spans**, neither exact
matches nor matched spans in multiple-gold questions decrease, all source and
provenance checks pass, and the run completes by the fixed deadline. All category
results/regressions, sparse support, exact/multiple-answer results and document
false-highlight/miss distributions are recorded. The original decoder is a
comparison, not a third adoption option.

If any gate fails, evidence is missing, or time runs out, retain `disjoint_full`.
There is no second variant, gap sweep, new candidate collection or retraining.
The result is an engineering decision on explored development data, not a
production precision guarantee, calibration artifact or held-out quality claim.

## Recorded execution command on Windows

The one experiment is complete. These commands document its execution; do not
rerun tests or the experiment merely to install this Markdown result update.

From the repository root in the existing conda environment:

```powershell
conda activate clauseanchor
python -m unittest discover -s ml/tests -p "test_cuad_decoder_experiment.py"
python ml/scripts/experiment_cuad_decoder.py
```

Run the experiment only after the focused tests pass. Keep the existing package
versions; no installation/upgrade command is needed. This is CPU work over saved
records. It hashes the existing checkpoint files but never loads their tensors.
Input verification and scoring can take time; progress is printed every 100
questions and before each of the three curves. No runtime estimate is claimed.

The runner verifies the completed source/feature/checkpoint bindings and the
previously recorded validation identity/report hashes. It checks every saved
question payload against that report. It recomputes the existing disjoint and
original baselines as integrity checks and compares all three pools under the
new fixed exit rule. It does not rerun the previous score-diagnostic or source-
review workflow, collect new candidates, or read calibration/policy/test examples.

Before selecting candidates, it writes an immutable input/config/code/runtime
identity. Results publish together only after the complete comparison. A normal
repeat verifies/reuses an existing result without another comparison. A changed
identity or damaged result fails and is preserved. An interrupted run can resume
the identical experiment by repeating the same command; no alternate run name is
offered. New runs after October 31 are refused; completed results can still be
read. A run finishing late must recommend the existing reference.

The console output and these two files were supplied and reviewed October 29:

- `data/processed/cuad/decoder_boundary_v1/results/report.json`
- `data/processed/cuad/decoder_boundary_v1/identity.json`

Full global/category curves and result checksums remain alongside the report in
`results/curves.json` and `results/manifest.json`; preserve them locally. Keep all
generated output ignored by Git. If a check fails, send the exact error; do not
regenerate completed inputs, edit a hash or start another variant.

## Software verification before delivery

All **32 focused tests passed** in the assistant's Python 3.12 environment on
October 28. Tests cover source/Unicode preservation, existing-candidate-only
selection, whole-score ties, the exact 19-match gate, other failure conditions,
category regressions, changed/corrupt inputs, no model loading/inference during
the runner, immutable result reuse and deadline handling. Existing core and
producer files remain byte-identical to commit `74fc4b3`. These are synthetic
software checks. Tanishq's real dev_select run and subsequent review are recorded
above; passing tests is separate from the failed model-improvement gate.

## Next gate

The October 31 freeze target is met on October 29: retain the existing extractor
and close decoder experimentation. The current candidate-only engine remains
available for Aryan's integration. Parser-to-app integration is still unverified.
Next, predeclare one simple calibration procedure and its held-out/out-of-fold
reliability/support assessment before opening dev_cal results. The freeze does
not itself validate probabilities or select a production policy.

Calibration assessment stays due November 2; operating-policy decision November
4; frozen final evaluation November 5; integration checks November 6; release
handoff November 7. Confidence remains null and scope unvalidated until actual
evidence supports otherwise. Rules, retrieval and India validation remain deferred;
neutral manual review and exact source offsets remain required.
