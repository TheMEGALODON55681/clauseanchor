# CUAD Cardlytics software-agreement family review

Reviewed: 19 October 2026 (India time).

**Status:** assistant-assisted source-text review prepared for Tanishq. The main
software agreement, customization template, later schedule/addendum, and product
license schedule are classified as one family for future split isolation:
`confirmed_related_for_split_grouping`. Three records are in official training;
the later schedule/addendum is in official test.

This note resolves six title-screen pairs. It retains the source's differing
agreement-date statements, unfinished template fields, and redactions. No source
text, annotation, family configuration, generated report, or split file changed.

## Scope and reproducibility

- Repository checked: `main` at `d8d6aca`, including the
  [Soupman review](CUAD_SoupmanFamilyReview.md).
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

The source loader reverified the pinned archive, source bytes, annotated spans,
and official memberships. The review inspected all three complete short
contexts and the long agreement's identity/signature page, contents list,
schedule definitions and references, and closing schedules. This is a
relationship review, not a complete annotation audit of the long agreement.

Ranges address `paragraphs[0].context` in zero-based Unicode code points, with
the end excluded. Paragraph hashes use the unchanged context encoded as UTF-8.

## Family overview

| Local reference | Actual source content | Official split |
|---|---|---|
| M | Software License, Customization and Maintenance Agreement, number CW251207, including schedules | Train |
| B | Schedule B customization template, with unfinished supplier and delivery-date fields | Train |
| S | Later schedule/addendum CW255039 referencing CW251207 and adding Offer Placement System software | Test |
| A | Schedule A product license form identifying Cardlytics OPS, version 3.0 | Train |

These labels are shorthand, not new canonical IDs. The shared 2018-01-12 title
date is not substituted for the agreement or addendum dates in the text.

## Source identities

### M

```text
CardlyticsInc_20180112_S-1_EX-10.16_11002987_EX-10.16_Maintenance Agreement1
```

- Exact-text group: `cuad-exact-v1:5a8626ce1052a7af2d7bb1b741b9f9c9c7ea55921d78a9bf09e43872422fc440`.
- Official split: `train`.
- Paragraph: `0`; length: 165,322 Unicode code points.
- Context SHA-256: `34eb96a3a62e11def90f97b12aa6aedc31d5fbdc2532fdf25d8dfa009dcd0369`.

### B

```text
CardlyticsInc_20180112_S-1_EX-10.16_11002987_EX-10.16_Maintenance Agreement2
```

- Exact-text group: `cuad-exact-v1:34f860050b3b0d3d0ec6d46d3cc1dba0751942a1a96d3cbf9d5ebedce7ce1b20`.
- Official split: `train`.
- Paragraph: `0`; length: 2,819 Unicode code points.
- Context SHA-256: `e6b28bd103980fa0e8d72c358702ac528a94cdd404a6112c32a083b182d2863c`.

### S

```text
CardlyticsInc_20180112_S-1_EX-10.16_11002987_EX-10.16_Maintenance Agreement3
```

- Exact-text group: `cuad-exact-v1:43d302fd787e2bd5a4c750124b617c519836774472403414f2dd9879c1d41cb6`.
- Official split: `test`.
- Paragraph: `0`; length: 1,707 Unicode code points.
- Context SHA-256: `9a5b359346f414dff69f8436603e30a6e9e3bb3671f8370dffaff3e6990b5256`.

### A

```text
CardlyticsInc_20180112_S-1_EX-10.16_11002987_EX-10.16_Maintenance Agreement4
```

- Exact-text group: `cuad-exact-v1:f506aae37b6bc361164432c59672b08aa91601465452640937693fa476211d21`.
- Official split: `train`.
- Paragraph: `0`; length: 5,327 Unicode code points.
- Context SHA-256: `dee1e23d3a909f6f4148d566f7a4ab45b876957083ed1d68004b1991c5d3a58b`.

## Evidence establishing the relationship

**M and S:** both display agreement number CW251207 and identify Cardlytics and
Bank of America. S separately identifies addendum CW255039, states its March 3,
2011 effective date, and incorporates a Schedule A for the Offer Placement
System into the existing software agreement. The shared agreement number is a
stronger link than the matching dataset titles.

**M and B:** M's contents list and definition 1.14 identify Schedule B as the
customization schedule. B has that heading and says it is attached to the same
named Software License, Customization and Maintenance Agreement. It is an
unfinished form in the supplied source package, not a completed customization
order inferred from other records.

**S and A:** S says the attached Schedule A describes Offer Placement System
software. A is headed Schedule A, names Cardlytics and Bank of America, says it
is issued under the software agreement, and lists Cardlytics OPS (Offer Placement
System) version 3.0. M also defines its product license schedule as Schedule A.
Together these establish the related schedule family without requiring raw
substring identity.

| Source evidence | Record | Exact range |
|---|---|---|
| Agreement number CW251207 | M | `[314, 341)` |
| Effective date printed on the main agreement | M | `[343, 367)` |
| Cardlytics company name on the main agreement | M | `[369, 400)` |
| Contents-list identification of the customization schedule | M | `[3068, 3102)` |
| Definition explicitly identifying customization Schedule B | M | `[6202, 6299)` |
| Definition explicitly identifying product license Schedule A | M | `[11745, 11844)` |
| Customization form heading | B | `[0, 34)` |
| Explicit attachment statement naming the software agreement | B | `[36, 140)` |
| Unfilled supplier-name placeholder | B | `[229, 251)` |
| Unfilled customization-delivery-date placeholder | B | `[906, 953)` |
| Same agreement number CW251207 in the later schedule | S | `[107, 134)` |
| Separate addendum number | S | `[227, 235)` |
| Later schedule effective-date statement | S | `[272, 310)` |
| November 5, 2010 description of the underlying agreement | S | `[549, 583)` |
| Incorporation of Schedule A for the Offer Placement System | S | `[1209, 1347)` |
| Product license form heading | A | `[42, 82)` |
| Software-agreement reference in the product schedule opening | A | `[84, 197)` |
| Bank of America and Cardlytics party identification | A | `[240, 310)` |
| OPS product and version | A | `[2910, 2961)` |
| Reference to a distinct General Services Agreement schedule | A | `[1141, 1185)` |
| Delivery date retained as TBD | A | `[3517, 3536)` |

## Source differences and limits

**Agreement date:** M prints `11/4/10` as its effective date. S describes the
underlying agreement as dated November 5, 2010. M's signature dates separately
show `11/8/10` and `11/4/10`. Preserve each statement without selecting a
corrected date or substituting signature dates. The matching CW251207 number,
agreement title and parties support family membership despite the discrepancy.

**Unfinished fields:** B retains `<<enter Company Name>>` and delivery-date
placeholders, specification/price instructions, and blank signature fields.
A includes TBD delivery/installation fields and redacted values. Do not fill
these from another record, assume a completed order, or infer hidden terms.

**Different agreements referenced:** A also refers to Schedule B of a General
Services Agreement. That reference is not automatically the same schedule as
B, which is the customization template for the Software License, Customization
and Maintenance Agreement. Keep those agreement contexts distinct. This review
does not invent a separate available source record for the referenced General
Services Agreement.

None of B, S, or A is an exact literal substring of M as a complete context.
All four records retain separate source identities, coordinates and labels.
Grouping does not concatenate their text, reconcile annotations, or infer
absence of clauses from unfinished or redacted content.

## Candidate decisions

| Candidate | Records | Official boundary | Relationship basis |
|---|---|---|---|
| `title-006` | B / S | Train / test | Related through M and its schedule structure |
| `title-007` | S / M | Test / train | Matching CW251207 agreement number, named agreement and parties |
| `title-008` | S / A | Test / train | Schedule A incorporation and matching Offer Placement System product |
| `title-029` | B / M | Train / train | Explicit customization Schedule B definition and form attachment statement |
| `title-030` | B / A | Train / train | Both are schedules within the same software-agreement family |
| `title-039` | M / A | Train / train | Product Schedule A definition, named agreement and parties |

All six are `confirmed_related_for_split_grouping`. Some relationships are
transitive through M; they do not require every record to name every other one.

## Handling in subsequent preparation

1. Keep M, B, S, and A in one connected family. Do not isolate the training-side
   template or product schedule from the test-side addendum.
2. Under [CUAD_CrossSplitReview.md](CUAD_CrossSplitReview.md), reserve the family
   for new internal preparation because it touches official test. Exclude M,
   B, and A from `fit`, `dev_select`, `dev_cal`, and `dev_policy` when the derived
   rules are implemented. S remains in official test.
3. Preserve all official 408-training/102-test memberships, original text, and
   annotations. No source records are deleted or moved between official splits.
4. Retain full official-test reporting. Add S to the exclusions for the
   separately named known-overlap-excluded sensitivity subset when revising the
   manifest; freeze this rule before inspecting model results.
5. Keep the independent AduroBioTech annotation disagreements pending under
   [CUAD_DataReview.md](CUAD_DataReview.md). This review adjudicates no labels.

## Provisional cumulative count effect

The four Cardlytics groups are distinct from the families in manifest 1.0.0
and the subsequent Federated, PCQuote, and Soupman reviews. Connecting the
verified groups only in memory gives these prospective counts; no revised
manifest, applied exclusions, or internal partitions were written.

| Measure | Through Soupman review | Also including Cardlytics review |
|---|---:|---:|
| Official training documents | 408 | 408 |
| Training documents reserved due to known cross-split families | 8 | 11 |
| Eligible documents for new internal preparation | 400 | 397 |
| Eligible exact-text groups | 399 | 396 |
| Eligible family units for internal partitioning | 395 | 392 |
| Full official test documents | 102 | 102 |
| Prospective known-overlap-excluded sensitivity test documents | 95 | 94 |

Counts remain provisional. The actual family manifest is still version 1.0.0,
whose checker continues to show the earlier 406-document prospective pool and
100-document sensitivity subset until a reviewed configuration update.

## Review milestone and remaining work

The Federated, PCQuote, Soupman, and Cardlytics notes now cover all 12 initially
pending cross-split pairs with matching title date and exhibit. That priority
batch is reviewed; it does not complete the broader family audit.

This note resolves three cross-split and three training-only pairs. **49 of
the 70 new title candidates remain:** nine cross-split, 38 training-only, and
two test-only pairs. The one unparsed source title also requires inspection.

The remaining cross-split candidates have weaker title hints: matching date
without matching exhibit, or issuer name alone. Review their source text before
confirming or rejecting a family relationship. Generated reports retain their
original statuses; incorporate documented decisions into a versioned manifest
and validate connected families before assigning internal partitions.

## Batch continuation

The subsequent [cross-split batch review](CUAD_RemainingCrossSplitReview.md)
examines the remaining nine cross-split candidates and three associated
same-split pairs. Its cumulative figures include this Cardlytics note.
Both notes are documentary decisions; neither updates manifest 1.0.0.
