# CUAD PCQuote co-branding-family source review

Reviewed: 19 October 2026 (India time).

**Status:** assistant-assisted source-text review prepared for Tanishq. The
co-branding agreement, a Section 2 Part B amendment, and the document headed
Second Amendment are classified as one related family for future split
isolation. The decision is `confirmed_related_for_split_grouping`. Two records
are in official test; the Second Amendment record is in official training.

This note resolves three title-screen pairs. A December 1996 amendment-date
discrepancy remains recorded and unresolved. It does not prevent grouping the
related records, but the review does not reconstruct their precise legal
revision history or fill in redacted terms. No source, annotation, manifest,
generated-report, or split file has been changed.

## Scope and reproducibility

- Repository checked: `main` at `def8e3c`, including the preceding
  [Federated review](CUAD_FederatedFamilyReview.md).
- Source: `data/raw/cuad/CUAD_v1/CUAD_v1.json`, SHA-256
  `ed0b77d85bdf4014d7495800e8e4a70565b48ee6f8a2e5dca9cf8655dbf10eae`.
- Official archive: `The-Atticus-Project/cuad`, revision
  `67faa0e6023b04fcaae6cc09497ab00e5d63a2a2`.
- Title screen: `ml/scripts/review_cuad_titles.py`, version `1.0.0`.
- Candidate snapshot: `data/processed/cuad/title_candidates.json`, canonical
  JSON SHA-256 `c9a962bba49d410bc12ddc90dabf5eeeb2458a6abf38face809968acb609c312`.
- Family manifest snapshot: `ml/configs/cuad_family_manifest.json`, version
  `1.0.0`, canonical JSON SHA-256
  `7576938a012b45b30121887b6db7d9d9dd77e0886256a554c70085f3a8fc8dea`.
- Canonical hashing uses sorted keys, compact JSON separators, UTF-8, and
  `ensure_ascii=False`, as in `check_cuad_families.py`.
- Attribution: [CUAD README](../../data/raw/cuad/README.md).

The source loader reverified the pinned archive, source bytes, original spans,
and official memberships. All three complete contexts were inspected. Ranges
below address `paragraphs[0].context` in zero-based Unicode code points, with
the end excluded. Paragraph hashes use the unchanged context encoded as UTF-8.

## Family overview

| Local reference | Source content | Date stated in the opening | Official split |
|---|---|---|---|
| S | Co-branding agreement | October 11, 1996 | Test |
| A | Amendment to Section 2, Part B | December 9, 1996 | Test |
| A2 | Second Amendment to the co-branding agreement | February 23, 1998 | Train |

S, A, and A2 are shorthand within this note, not new canonical IDs. The common
1999-07-21 date and Exhibit 10.11 in the source titles are screening hints.
They are not substituted for the dates stated in the instruments.

## Source identities

### S

```text
PcquoteComInc_19990721_S-1A_EX-10.11_6377149_EX-10.11_Co-Branding Agreement1
```

- Exact-text group: `cuad-exact-v1:f4b6288c6a093315b536d8033d30ec22f3caa18225630a90d1b6e2219d4023f7`.
- Official split: `test`.
- Paragraph: `0`; length: 19,851 Unicode code points.
- Context SHA-256: `168e88036f475aca607e6652e1737b7ac92c79b17df3c5ae94ce5999d5e1284d`.

### A

```text
PcquoteComInc_19990721_S-1A_EX-10.11_6377149_EX-10.11_Co-Branding Agreement2
```

- Exact-text group: `cuad-exact-v1:1a665c30fce38c79925bc557e010a46007f784a7a24d265f4f3ae174f5cd3045`.
- Official split: `test`.
- Paragraph: `0`; length: 857 Unicode code points.
- Context SHA-256: `f4315bbc3c62769c0f78a6c62a6a452e9b0ebbc409a8f7ee6cd73de55a9e01c1`.

### A2

```text
PcquoteComInc_19990721_S-1A_EX-10.11_6377149_EX-10.11_Co-Branding Agreement3
```

- Exact-text group: `cuad-exact-v1:4918cec952a22441ae0ea55480dcaba7dff0245135a6f12585c4495cf603eaf8`.
- Official split: `train`.
- Paragraph: `0`; length: 2,558 Unicode code points.
- Context SHA-256: `6485dbaee5e11df2f5a7e8809acad1410c2ac2b535da0d4359f2ab0cb33a9180`.

## Evidence of the shared agreement

S is the co-branding agreement between PC Quote and the party abbreviated ABW.
Its Schedule A names PC Quote, Inc. and A.B. Watley, Inc. and repeats the
October 11, 1996 agreement date. A names those parties and specifically targets
Section 2 (Term), Part B of their co-branding agreement. A2 names the same
parties, explicitly references the October 11 agreement, and replaces Section
2 A and B. The PC Quote street address matches exactly between S and A2; the
ABW address also corresponds, with the state written as NY in S and New York
in A2. These references support grouping independently of matching filenames.

| Source evidence | Record | Exact range |
|---|---|---|
| Opening agreement date | S | `[534, 547)` |
| Schedule A heading naming both parties and the agreement date | S | `[19510, 19617)` |
| Section 2 Term heading | S | `[3826, 3834)` |
| PC Quote address in the agreement | S | `[677, 724)` |
| Heading identifying the Section 2 Part B amendment | A | `[8, 67)` |
| Stated December 9 amendment effective date | A | `[153, 184)` |
| PC Quote party name in the opening | A | `[200, 214)` |
| A.B. Watley party name in the opening | A | `[254, 271)` |
| Two signature dates in the source | A | `[746, 777)` |
| Redaction marker after the introductory paragraph | A | `[490, 495)` |
| Stated February 23, 1998 date | A2 | `[200, 226)` |
| Explicit October 11 agreement reference and December 10 amendment reference | A2 | `[522, 599)` |
| Same PC Quote address in the Second Amendment | A2 | `[299, 346)` |
| Instruction replacing Section 2 A and B | A2 | `[1346, 1482)` |
| Redaction marker where replacement wording would appear | A2 | `[1484, 1489)` |

## Source differences and limits

**Amendment-date discrepancy:** A states December 9, 1996 as its effective date.
A2's recital instead says the underlying agreement was amended on December 10,
1996. A's signature block separately shows December 5 and December 12, 1996.
Preserve all four date statements as written. This review does not choose a
corrected date, equate an effective date with a signature date, or assert that
A is definitively the exact December 10 amendment referenced in A2. A and A2
are grouped through their common agreement and parties.

**Party-name variation:** S's opening spells the ABW name as `AB Wately, Inc.`;
its signature block and Schedule A instead use `A.B. WATLEY, INC.`. A and A2
use Watley forms. The party abbreviations, addresses, signature/schedule names,
and explicit agreement reference support the relationship. No source spelling
or offset is corrected by this review.

**Redactions:** the source marks omitted content with `[***]`. A's amendment
terms and A2's replacement wording are not available in full. The family
relationship does not reveal their contents. Do not reconstruct the term
length, termination conditions, or other hidden language, and do not infer
missing annotations from related records. Preserve all original labels and
spans pending any separate annotation review.

## Candidate decisions

| Candidate | Records | Official boundary | Decision basis |
|---|---|---|---|
| `title-003` | A / A2 | Test / train | Same co-branding agreement, parties, and Section 2 subject matter; December date discrepancy retained |
| `title-009` | A2 / S | Train / test | A2 explicitly identifies S by its October 11 date, parties, and addresses |
| `title-026` | A / S | Test / test | A identifies the parties' co-branding agreement and its Section 2 Term, Part B |

All three are `confirmed_related_for_split_grouping`. S, A, and A2 form one
connected family. This is not a claim that their full texts, annotations, or
redacted provisions are interchangeable.

## Handling in subsequent preparation

1. Keep all three exact-text groups in one family. The test-only S/A pair also
   matters because it connects to the training-side A2 record.
2. Under [CUAD_CrossSplitReview.md](CUAD_CrossSplitReview.md), reserve this family
   for new internal preparation because it touches official test. Exclude A2
   from `fit`, `dev_select`, `dev_cal`, and `dev_policy` when the derived rules
   are implemented. S and A remain in official test.
3. Preserve the official 408-training/102-test memberships and original
   annotations. Do not delete records or move test material into training.
4. Retain full official-test reporting. Include both S and A in the exclusions
   for the separately named known-overlap-excluded sensitivity subset when the
   manifest is revised. Freeze that derived rule before examining model scores.
5. The unrelated AduroBioTech label disagreements remain pending under
   [CUAD_DataReview.md](CUAD_DataReview.md).

## Provisional count effect

The three PCQuote groups are distinct from the families in manifest 1.0.0 and
from the four Federated groups. Applying the documented grouping rules only
in memory yields the following cumulative prospective counts; no exclusion,
manifest revision, or internal partition has been written.

| Measure | Including Federated review | Also including PCQuote review |
|---|---:|---:|
| Official training documents | 408 | 408 |
| Training documents reserved due to known cross-split families | 5 | 6 |
| Eligible documents for new internal preparation | 403 | 402 |
| Eligible exact-text groups | 402 | 401 |
| Eligible family units for internal partitioning | 398 | 397 |
| Full official test documents | 102 | 102 |
| Prospective known-overlap-excluded sensitivity test documents | 99 | 97 |

These remain provisional. The actual family manifest is still version 1.0.0,
so its checker continues to report its earlier 406-document prospective pool
and 100-document sensitivity subset until a reviewed configuration update.

## Remaining work

This note resolves two cross-split and one test-only pair. Together with the
six pairs resolved by the Federated note, **61 of the 70 new title candidates
remain:** 16 cross-split, 42 training-only, and three test-only pairs. The one
unparsed source title still requires its own inspection.

Generated reports retain their original screening statuses. Record subsequent
source decisions separately, then incorporate them into a versioned manifest
and verify the combined connected families before assigning internal splits.
