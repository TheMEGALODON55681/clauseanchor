# CUAD source-span error review

Reviewed: 2026-10-26. Scope: exploratory assistant review of the frozen
`dev_select` source evidence. This records observations and hypotheses, not
independent annotation adjudication or a new performance estimate.

## Decision

Run one small, versioned comparison of boundary-aware candidate selection before
freezing the decoder for calibration. Investigate whether retaining alternative
boundaries and separately supported occurrences improves recall at a comparable
precision and false-highlight burden. Keep model weights fixed. The exact
algorithm and acceptance criteria must be recorded before that experiment runs.

This decision does not adopt a decoder or threshold. Ranking and category
confusion remain substantial problems; boundary changes alone are not expected
to resolve them. Calibration follows a frozen extraction/scoring design.

## Evidence and unchanged benchmark

Inputs: `error_review_v1/report.json`, the earlier score diagnostic and decoder
validation reports, and the frozen feature-source records. Report bindings,
counts, category totals and source coordinates were checked. The exporter
producer hash matches the supplied script. The user reported 367 tests passing
and successful reproduction of the saved candidates, score curves and diagnostic
before exporting these cases.

The review covers all 155 exported cases: all 24 false highlights, all 18
inexact matches, and 113 selected missed spans. These cases cover 39 documents
from 37 families. The misses are sampled by category and observed stage, with
preference for stronger available evidence; they are not a random sample of
the 718 misses. Related documents are not independent confirmations.

The reviewed setting is `disjoint_full` at the exploratory 90% precision point:
raw margin at least `15.6513671875`. A raw margin is not a probability.

| Quantity | Unchanged result |
|---|---:|
| Questions / annotated spans | 1,599 / 935 |
| Returned spans | 241 |
| Overlap matches / false highlights / misses | 217 / 24 / 718 |
| Precision / recall | 90.041% / 23.209% |
| Exact matches / exact-match recall | 199 / 21.283% |

Matching remains one-to-one maximum total eligible character IoU, with
IoU >= 0.5. It is not exact matching or maximum match count. A seemingly relevant
prediction can still be an incomplete user highlight. Do not reclassify it as
correct in these results merely because it contains related language.

The prior descriptive precision interval, 86.574%-93.470%, is conditional on
the chosen cutoff and does not correct development-set selection bias. Its
document bootstrap is not a family-level bootstrap. These results do not
establish performance on arbitrary uploaded documents.

## Missed-span census

| Observed stage | All misses | Exported examples |
|---|---:|---:|
| Eligible returned span unmatched | 0 | 0 |
| Eligible disjoint candidate below diagnostic cutoff | 438 | 40 |
| Eligible positive candidate suppressed by disjoint selection | 58 | 24 |
| Eligible saved candidate only at a nonpositive margin | 86 | 29 |
| No eligible saved raw candidate | 136 | 20 |
| Total | 718 | 113 |

These are ordered observations, not mutually exclusive causal diagnoses or
counts guaranteed to be recoverable by changing one stage. Saved raw candidates
are still limited to the per-window top 20 and a maximum length of 256 tokens.
Missing candidates do not distinguish search pruning from model scoring failure.

Of the 718 missed spans, 689 have a complete usable target in regular windows,
20 exceed 256 tokens, and 9 have no regular window containing the full target.
Thus 96.0% of misses cannot be explained simply by absence of a usable complete
target window. Conversely, failure of complete-target coverage does not rule out
a partial prediction meeting the overlap criterion.

Parties accounts for 100 of the 136 misses with no eligible raw candidate
(73.5%). This calls for a separate entity-boundary and occurrence analysis; one
sampled Parties case cannot explain all 100 misses.

### What the missed examples show

- In 38 of the 40 sampled below-cutoff cases, the highest-scoring eligible
  disjoint candidate exactly matches the gold interval. This demonstrates that
  correct boundaries can receive low scores. The sampling rule favors strong
  candidates, so 38/40 must not be generalized to all 438 cutoff misses.
- REWALK anti-assignment (`7166d63a5737ec5218f42d79`): a separately annotated
  null-and-void sentence has an exact candidate with margin 17.1221. A combined
  two-sentence span at 17.3955 suppresses it and matches only the first gold
  span. Both candidates exceed the reviewed cutoff.
- SightLife insurance (`b57836c5831976aed9d7f439`): an exact insurance-duration
  candidate at 16.0454 is suppressed by a coverage-plus-duration span at
  16.1782. Both exceed the cutoff, but one combined output cannot match both
  annotated occurrences.
- 2TheMart renewal (`380d6864ac49b046238cdb12`): an exact renewal sentence at
  16.9897 is suppressed by a three-sentence span at 17.2476. The longer span
  fails the 0.5 IoU threshold against either separately annotated answer.
- Parties (`ecddc9290cecef38c326a137`): a candidate combines two company names;
  its best overlap with the focused name is 0.4894. This is evidence to inspect
  answer units, not a reason to lower the benchmark matching threshold.
- Three sampled OTIS licensing questions share a 534-token gold span. The
  256-token candidate limit prevents a complete candidate, although their
  shared source means these are not three independent failure examples.
- Several nonpositive examples contain substantive category evidence, while
  others expose ambiguous taxonomy or annotations fragmented at page breaks.
  Automatically lowering the cutoff or treating every unmatched candidate as
  a verified negative would require evidence this review does not supply.

## All 24 false highlights

The following grouping is provisional and exclusive only for organizing this
review: 8 extent/segmentation cases, 6 occurrence/instrument-scope cases,
4 category/evidence concerns and 6 unresolved scope/annotation cases. It is
not a replacement confusion matrix. Every row remains a benchmark false
positive. Case IDs resolve to the unchanged generated report.

| Case ID | Category / document | Source observation |
|---|---|---|
| `75968b706160244448b0a158` | Agreement date / GLOBALTECH | Extent: selected date is inside a much longer annotated opening sentence; IoU 0.2212. |
| `0373a6011cf1999a66c0e4aa` | Agreement date / VNUE | Occurrence: same date value appears in the introduction and signature block; annotation selects the latter. |
| `ff3b83d0417b570a12c70a21` | Anti-assignment / RISE | Extent: consent sentence omits the following other-party assignment exception included in gold; IoU 0.4567. |
| `d8366198434873690cf5c789` | Audit rights / Zounds | Extent: selected audit-schedule sentence omits the wider access-right grant; IoU 0.2927. |
| `3d3fd3baefb484818210b554` | Cap on liability / NANOPHASE | Extent: explicit purchase-price cap is narrower than gold, which also includes a damages exclusion; IoU 0.4276. |
| `f63c09ba79b0ec6cfd73e80b` | Cap on liability / Zounds | Category concern: liquidated damages for employee solicitation do not by themselves establish the requested liability cap. |
| `cdcbf17f25d4fe2123e524cf` | Document name / FUSION | Occurrence: predicted title heading matches the document name; gold instead marks the same words in a liability section. |
| `b3980b98545224dbee47b787` | Document name / ELECTRAMECCANICA | Occurrence: heading versus repeated title in the introductory sentence. |
| `332b8a814548a7d2519b4a87` | Effective date / IMAGEWARE | Extent: entire date-definition sentence is returned where gold marks only the date; IoU 0.1771. |
| `3a22cbfa58011bddcb54453b` | Effective date / OTIS | Evidence concern: cover agreement date is substituted for effective-date evidence; the date's role requires definition/context checking. |
| `704e877552e496d939e7c620` | Exclusivity / BIOCEPT | Category error: selected sentence states non-exclusive activity; exclusivity evidence is in the following sentence. |
| `4f4d6e36e187ebc3e098efe6` | Expiration date / RISE | Category error: selected sentence establishes effectiveness, while the following sentence gives the term. |
| `f38821725c257f80c9c65cb7` | Expiration date / ARMSTRONG | Unresolved scope: a component trademark-license term is selected instead of the agreement's broader term provision. |
| `4242ffa14e197acd2246f8bf` | Expiration date / ARMSTRONG | Same scope issue in a related document from the same family; not independent evidence. |
| `d8969832971571e0f3299b94` | Governing law / ARMSTRONG | Instrument scope: an assignment annex has the same jurisdiction as annotated clauses elsewhere. |
| `1ca5d1f578111d8482db4d32` | Governing law / Prudential | Extent: selected governing-law sentence is narrower than gold, which includes an entire-agreement sentence; IoU 0.3080. |
| `958a7939faba2dc38d11a1cf` | Governing law / Loop | Instrument scope: assignment-annex clause versus main-agreement clause, both referring to Delaware. |
| `a26a9c225cb93874d9fe36e9` | Insurance / DYNAMEX | Extent: cargo coverage is returned, but other required coverages and insured-party provisions are omitted; IoU 0.2667. |
| `df28ed3430710a98d89668e0` | License grant / ELECTRAMECCANICA | Unresolved taxonomy: manufacturing-right grant versus annotated IP licenses. |
| `1906cc2a033410d0f5b9b672` | License grant / LinkPlus | Unresolved taxonomy: office-space license versus intended IP-license category scope. |
| `02eca3aedb97a9124e4d0f9f` | Parties / ARMSTRONG | Instrument/occurrence scope: company name is selected from a patent-assignment exhibit rather than the annotated main introduction. |
| `eda5309886d4069b50231120` | Renewal term / BIOCEPT | Possible annotation omission: unannotated sentence explicitly describes successive one-year renewals by written agreement. |
| `dc0bc37e8c4deb7a9cc52a4c` | Renewal term / 2TheMart | Segmentation: three sentences encompass separate gold spans but overlap neither sufficiently; maximum IoU 0.3347. |
| `782b8fe7827eadf53534b650` | Renewal term / REWALK | Unresolved scope: renewal conditions require agreement on a future period rather than specifying that period now. |

Eight false highlights overlap same-category gold but fail its extent criterion.
The other sixteen have zero gold overlap; that alone does not establish that
their text is irrelevant. The title and repeated-date cases illustrate why
benchmark errors need source review before reuse as negative training labels.

## All 18 inexact matches

- Eleven differ only in punctuation: eight Parties spans include a trailing
  comma; three expiration/governing-law spans differ by a final period.
- One license-grant span omits a list marker (`836e401ed6aeab7b7a021d85`).
- Two annotations contain awkward trailing fragments: the Zounds document name
  (`0eb8d9855febe14cd8e38d8c`) and EMV effective date
  (`fb12158e164308605f645ece`). Preserve these annotations in the benchmark.
- Four spans expand or combine provisions: REWALK anti-assignment
  (`9f7b25daca2c8eb0f67a4b14`), ASHWORTH insurance
  (`9c5a8978aa158b72a07b0ad6`), DYNAMEX insurance
  (`9d878c72cd3b5c7e0b250dfc`) and SightLife insurance
  (`3e0070412f9d8f8b40c838cb`). Some combined spans suppress a separately
  annotated answer, even though the combined span earns one overlap match.

None of these eighteen predictions has the existing boundary-review flag set.
That flag therefore does not capture the observed answer-unit problems.

## Next experiment and evaluation gate

1. Define a small set of deterministic candidate-selection alternatives using
   saved candidates and source text. Keep alternatives for individual entities,
   dates and clause occurrences; avoid a universal sentence expansion rule.
   Gold coordinates may score outputs but must never choose their boundaries.
2. Compare on the entire frozen `dev_select` set against `disjoint_full` and
   the original decoder. Recompute one-to-one matching and score curves,
   including exact boundaries, multiple-answer recall, category results,
   absent-category false positives and false highlights per document.
3. Assess recall at comparable empirical precision and workload, with explicit
   category regressions and support counts. A better development result is a
   reason for further validation, not a deployed quality guarantee. If the
   small experiment fails, record that outcome instead of expanding rules
   indefinitely around the reviewed examples.
4. Freeze a justified extraction and scoring design before fitting calibration
   on `dev_cal`. Assess category-aware calibration only where support permits;
   keep `dev_policy` for the declared operating-policy decision and the official
   test for final frozen evaluation.

Negation, date-role confusion and damages-versus-cap distinctions require
category evidence or better scoring; punctuation cleanup cannot establish
them. A verifier or stronger ranking experiment remains a later option if the
measured failures justify it. No weight updates are initiated by this review.

Preserve the original JSON and annotations, including its generated
`human_review_completed: false` and pending case fields. This separate assistant
review does not certify human adjudication. No-output results remain uncertainty,
not a validated assertion that a clause is absent.

## Reproduction identifiers

Canonical JSON hashes use the project's sorted-key, compact UTF-8 encoding.

| Artifact | SHA-256 |
|---|---|
| Uploaded error-report bytes | `f30d7cdc0bc9e3b20e1614162c1fc5ee745885ba56ff0746869286c8300d4fce` |
| Canonical error report | `5b2cb7f9c6063895f181e153b5c7591c7f736b0328475a1264743576ce68f819` |
| Review identity | `4cfdaf3ba8d2ade4a1088ca80de637e6aa0fa8dc65a223f64b02ef8a20eef789` |
| Exporter producer | `c6da24afa758c3622a25cba0d3adb46b0c5c57aa7350181559e0cd0c034c9137` |
| Canonical score diagnostic | `311ecefff9cbeb440c59229a91f72245e93bf2f55f56dfe8956ab204007effed` |
| Score-diagnostic identity | `fdc3d81a6cf3da3cc66cea44b879b6c8dfa2554ddf1aa943b2835c8f9241c9c3` |

Training remains `clean_training_v1`, selected `checkpoint-000022`; features
remain `features_v1`; saved candidates remain `decoder_validation_v1`.
