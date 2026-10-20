# CUAD unresolved-case handling policy

Prepared: 20 October 2026. Repository checked: `ba443bf82c55105632779b3b1b1b610b965b03eb`.

**Status:** proposed preparation policy, prepared for Tanishq's review and adoption.
Committing this note records adoption of the policy; implementation remains a
separate manifest/checker change. No records, labels or splits are changed here.

## Decision

Use conservative holds for the six unresolved title pairs and retain the existing
question-level hold for the AduroBioTech annotation conflict. This settles how
new preparation will handle uncertainty without claiming the underlying
relationships or disputed labels have been resolved.

The evidence remains in the [cross-split review](CUAD_RemainingCrossSplitReview.md),
[training review](CUAD_RemainingTrainingFamilyReview.md), and
[duplicate-label review](CUAD_DataReview.md). Their source identities and evidence
ranges are not repeated here. The [XACCT disposition](CUAD_XACCTTitleReview.md)
adds no hold or family edge.

## 1. Document-level relationship holds

Reserve every official-training member of these pairs from all four new internal
partitions: `fit`, `dev_select`, `dev_cal` and `dev_policy`. Held records must not
contribute training examples, negative mining, model selection, calibration,
threshold selection or scored clean-development evaluation. Source inspection
and provenance checks remain permitted.

| Candidate | Unresolved connection | Training records held | Official test records retained |
|---|---|---:|---:|
| `title-013` | GPAQ: media license and Village sponsorship/services | 1 | 1 |
| `title-018` | EcoScience: endorsement and Kaya Fest sponsorship | 1 | 1 |
| `title-060` | Vertex: Marrero production and rail-facility agreements | 2 | 0 |
| `title-061` | Reynolds: supply and transition-services agreements | 2 | 0 |
| `title-062` | XLI: Light Sheets promotion and distribution | 2 | 0 |
| `title-064` | Kiromic: joint venture and Rotino consultancy | 2 | 0 |
| Total | Six examined but unresolved pairs | **10** | **2** |

Keep each relationship status `unresolved`. Do not turn a hold into a confirmed
family edge or an unrelated decision. The four training-only pairs are withheld
on both sides; they are not assigned together to a development partition.

Apply holds to exact-text groups, including all source identities, and propagate
them through any confirmed family containing a held group. Under the current
confirmed graph these ten records are ten distinct singleton groups, all outside
the already reserved cross-split families. Future graph changes require a new
count and closure check; never silently release a connected member.

## 2. AduroBioTech question-level hold

Keep both original AduroBioTech records in their one exact-text group. Retain
their source annotations unchanged. Hold **Anti-Assignment**
(`cuad.anti_assignment`) and **Exclusivity** (`cuad.exclusivity`) for both copies:
four original question records, representing two conflicting group/category
questions.

The hold excludes all derived examples for those questions from supervised loss,
negative mining, model selection, calibration, threshold selection and scored
clean-development evaluation. Do not convert either empty answer list into a
negative example, choose the positive copy, or union the conflicting answers.

The other 39 agreeing categories remain eligible, subject to the normal group
split and deduplication rules. Preserve their distinct answer occurrences and
both source identities. The duplicate group is not among the ten document holds,
so this question hold removes no additional whole document or family unit.

Label adjudication is deferred. It is not a prerequisite to preparation if the
question hold is explicitly implemented and verified.

## 3. Benchmark and count boundaries

Preserve the original **408 train / 102 test** memberships, source text and labels.
The holds govern new derived preparation only. Official baseline reproduction
continues to follow the authors' protocol and report all 102 test documents.
Later holds cannot undo the released baseline's historical training exposure.

Keep the known-overlap-excluded sensitivity subset at **93 test documents**,
based solely on confirmed cross-split families. The two unresolved test records
remain in both the full test and that sensitivity subset and must be disclosed
as unresolved. Do not relabel the subset as overlap-free. No additional
uncertainty-excluded test subset is introduced by this policy.

| Prospective quantity | Confirmed relationships only | With relationship holds |
|---|---:|---:|
| Reserved official-training documents | 13 | 23 |
| Eligible source training documents | 395 | **385** |
| Eligible exact-text groups | 394 | **384** |
| Eligible internal family units | 374 | **364** |
| Full official test documents | 102 | **102** |
| Known-overlap-excluded sensitivity test documents | 93 | **93** |

The 385-document figure retains both AduroBioTech source identities; it is not
the number of deduplicated training examples. Feature/example counts and
category support must be measured after the holds and deduplication are applied.
Unsupported categories must remain explicit rather than lifting holds to fill
their counts.

## 4. Implementation and reopening gates

The next code change must represent all 70 title decisions (48 confirmed,
16 rejected, six unresolved), the XACCT manual disposition, these document holds,
and the duplicate-question hold alongside the original lexical families. Pin
the frozen title-report canonical SHA-256:

`c9a962bba49d410bc12ddc90dabf5eeeb2458a6abf38face809968acb609c312`.

Validate candidate identities, connected families, hold propagation, question
identities and the totals above. An unchanged manifest 1.0.0 still reports its
old counts; changing only expected counts is insufficient. The preparation code
must enforce the holds before writing any internal assignments or examples.

Internal splitting remains unapproved until that implementation passes its
checks. Document any later release from a hold with new evidence, reviewer,
date and versioned policy; recompute affected counts and derived artifacts.
Do not choose a relationship, label or hold release using held-out model scores.

## Validation of this proposal

The two latest review files match their committed copies at the checked revision.
Using the previously verified source inventory, pinned screening reports and
recorded confirmed edges, an in-memory component calculation verified the ten
held singleton groups, no overlap with prior cross-split reservations, the
separate AduroBioTech group, and the **385 / 384 / 364** totals. This calculation
does not apply filtering or establish exhaustive family discovery.
