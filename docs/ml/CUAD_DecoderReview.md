# CUAD full-candidate decoder review

Date: 2026-10-26. Owner: Tanishq Arya.
Code base: `34a7e3f`.

## Review decision

Carry `disjoint_full` forward as the primary candidate for the score-quality
diagnostic in [ML Phase 6.2](Phases.md#62-diagnose-score-quality-on-dev_select).
It gives the highest macro F1 among the tested multi-span variants and reduces
false positives substantially relative to the original decoder. Its current
precision is insufficient to establish useful automatic highlighting.

This is a development-review decision. No decoder is adopted in production, no
operating threshold is selected, no catalogue category is upgraded, and the
original best-checkpoint selection and training metrics remain unchanged.
Top-one remains a diagnostic because it discards additional valid answers for
the same category. Containment remains a recorded comparison, not an additional
automatic policy.

## Evidence and scope

Tanishq reported 314 passing CUAD tests, a successful two-question GPU pilot and
successful full validation using `checkpoint-000022` from `clean_training_v1`.
Training had already completed at 3,474 optimizer updates. The validation run
reused the selected weights without updating them.

The supplied report is
`data/processed/cuad/decoder_validation_v1/report.json`. This review reconciled
the report's per-question counts with its category and overall totals and
checked its false-positive decomposition and coverage. It also aggregated the
question records by document. The underlying weights and saved raw candidate
files were not supplied for this report review; their verification is recorded
by the user's validation runner, not independently repeated here.

| Provenance item | Value |
|---|---|
| Validation run SHA-256 | `f47f3b426894fca493d8e963148b024630c05167bf5a5dde7ecfb1114d1a16e7` |
| Supplied report byte SHA-256 | `a7eefd2094717909fdabcc643de5521ed54ba7addfb99f2cd3f52d78fbea6c03` |
| Report canonical JSON SHA-256 | `6e2dce9e233ed8e2c0e47978566398d30552df1bb94026d5a9e1ec033b4c50a9` |
| Question record digests in report | 1,599 |
| Partition | `dev_select` only |
| Coverage | 39 document groups; 41 categories; 1,599 questions; 45,748 windows |
| Annotated answer spans | 935 |
| Original replay differences | 0 coordinate differences; 0 score differences; 0 match-count differences |

Canonical JSON hashing uses sorted keys, compact separators, UTF-8 with
`ensure_ascii=False`, and `allow_nan=False`, as in the existing scripts.
The recorded digests bind this review to the supplied artifact; they are not
substitutes for the runner's source and checkpoint verification.

The experiment collects candidates before original overlap suppression and the
global top-50 cap. It still searches only the top 20 start/end tokens, retains
at most 20 pairs per window, and limits spans to 256 tokens. It is not an
exhaustive enumeration of every possible answer span.

## Measured comparison

All variants below use the fixed, uncalibrated raw margin greater than zero.
Precision and recall are pooled span metrics; macro F1 averages category F1.
Matching is the existing one-to-one maximum-total interval IoU assignment with
eligibility at IoU at least 0.5. Exact boundaries are a separate measure.

| Variant | Precision | Recall | Macro F1 | Emitted spans | Multiple-answer recall |
|---|---:|---:|---:|---:|---:|
| `original_capped` | 6.311% | 75.936% | 13.173% | 11,251 | 66.889% |
| `original_uncapped` | 5.978% | 75.936% | 12.933% | 11,876 | 66.889% |
| `top_one_full_diagnostic` | 49.811% | 42.246% | 43.063% | 793 | 22.130% |
| `iou_0_5_full` | 9.438% | 74.866% | 18.250% | 7,417 | 65.557% |
| `containment_0_8_full` | 25.038% | 69.733% | 37.735% | 2,604 | 59.068% |
| `disjoint_full` | 25.694% | 69.305% | 38.303% | 2,522 | 58.569% |

Multiple-answer recall concerns questions with several annotated answers for
the same category, not merely documents containing several clause categories.
There are 171 such questions and 601 annotated spans in that stratum.

### What improved and what remains unresolved

- Original capped output contains 710 matched spans, 225 misses and 10,541
  false positives. Disjoint contains 648 matched spans, 287 misses and 1,874
  false positives: 8,667 fewer false positives at the cost of 62 fewer matches.
- Removing the top-50 cap alone adds 625 positive-margin outputs and no new
  matches under the unchanged original decoder.
- Disjoint improves category F1 in 39 of 41 categories relative to the original
  capped decoder, with two ties. Relative to containment, it improves 24
  categories, ties 16 and worsens one. This is descriptive development evidence,
  not a statistical significance claim.
- Compared with containment, disjoint removes 78 false positives and loses four
  matches. Its aggregate lead does not establish that overlap suppression is
  appropriate for every valid nested clause.
- Disjoint's 1,874 false positives comprise 1,797 with no annotated overlap and
  77 with partial overlap below the matching criterion. The report records no
  additional eligible-overlap false positives for this variant. Thus 95.9% of
  its remaining false positives are not explained by annotated overlap alone.
  Source-level inspection is still required before calling them verified
  semantic errors or using them as negative training examples.
- On 1,094 genuinely absent category questions, disjoint emits predictions for
  306 questions, totaling 608 false positives. Suppressing overlaps has not
  established a reliable absence decision.
- Disjoint records 553 exact-boundary matches out of 935 gold spans (59.144%
  exact-match recall). Its 69.305% overlap recall is not exact extraction
  accuracy or document accuracy.

## Document and category limits

Aggregating disjoint results over all 41 category questions per document gives:

- At least one matched answer in 38 of 39 documents.
- At least half the annotated answers matched in 37 of 39 documents.
- Zero of 39 documents with every annotated answer matched and no extra
  predictions. In fact, each document has at least one miss and one false
  positive under this variant.

The documents contain 8 to 51 annotated answer spans, with median 23. These
results do not predict a fixed number of successful arbitrary documents, nor
do they directly measure a hypothetical collection with ten clauses each.
Macro F1 is not the fraction of fully correct documents. An unhighlighted
passage is not evidence that a document is safe to sign.

Category results vary and some denominators are small. For example, governing
law has 35 matches from 36 gold spans and 23 false positives; non-compete has
eight matches from eight gold spans but 63 false positives. Source-code escrow
has only one gold span. High recall or F1 on such small supports is not enough
to publish a category-specific reliability claim.

## Next action and unchanged boundaries

Implement a read-only score-quality diagnostic on the saved dev_select
candidates, with the provenance and matching checks described in Phase 6.2.
Measure retained recall at increasing empirical precision and document-level
false-highlight burden. Treat unattainable precision targets and negligible
coverage as explicit failures rather than selecting a flattering point.

The current report does not retain individual candidate margins. The next
diagnostic must use the existing `decoder_validation_v1/questions/*.json`
records and frozen source instead of inferring a precision-recall curve from
aggregate counts or requesting another training run.

No calibration, operating-policy selection, official-test evaluation for this
checkpoint, model retraining, real analyzer enablement or support-status change
is performed by this review. The ordered plan adds calibration, abstention,
conditional model improvement and review-workload validation at their proper
stages; existing rules, retrieval and integration work remain pending.
