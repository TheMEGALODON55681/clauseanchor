# CUAD cross-split text review

Reviewed: 19 October 2026 (India time).

**Status:** assistant-assisted source-text review prepared for Tanishq. The two
screened cross-split pairs are classified as related document families for
future split handling. This is a data-provenance decision, not legal advice,
annotation adjudication, or a measurement of model performance. No source files,
annotations, benchmark memberships, or prepared datasets have been changed.

## Scope and reproducibility

- Source: `data/raw/cuad/CUAD_v1/CUAD_v1.json`, SHA-256
  `ed0b77d85bdf4014d7495800e8e4a70565b48ee6f8a2e5dca9cf8655dbf10eae`.
- Official archive revision: `The-Atticus-Project/cuad` at
  `67faa0e6023b04fcaae6cc09497ab00e5d63a2a2`.
- Screen: `ml/scripts/review_cuad_similarity.py`, version `1.0.0`, committed
  at `4613263` before this review.
- Candidate report: `data/processed/cuad/similarity_candidates.json`.
- Attribution: [CUAD README](../../data/raw/cuad/README.md).

The screen examined 129,286 pairs of 509 exact-text groups and returned six
candidates. This note reviews only the two crossing official train/test
membership. The four training-only candidates remain pending.

All ranges below address `paragraphs[0].context` in the full source JSON. They
count Unicode code points, with start inclusive and end exclusive. Context
hashes use the untouched string encoded as UTF-8. Comparison normalization is
never written back to source text or used to move annotation offsets.

The earlier zero count of identical full texts across official splits remains
correct. The relationships here involve different full texts.

## Decision summary

| Candidate | Official membership | Classification for future grouping | Key evidence |
|---|---|---|---|
| `similarity-001` | Ideanomics: training / test | Related form and dated/signed agreement variants | Same named parties, shared long sections, filled versus blank date, and substantive licensing differences |
| `similarity-002` | Women's Golf: test / training | Parent agreement and contained closing/attachment text | The entire shorter record matches the longer record's suffix after whitespace normalization; explicit Exhibit A linkage |

Both decisions are `confirmed_related_for_split_grouping`. They do not authorize
merging texts or transferring labels between the records.

## similarity-001: Ideanomics content licence variants

**Train record**

```text
IdeanomicsInc_20160330_10-K_EX-10.26_9512211_EX-10.26_Content License Agreement
```

- Exact-text group: `cuad-exact-v1:496c0446e173090ccf5605b657cfd497da22c927d635540dcc969a87cf610c46`.
- Paragraph: `0`; length: 40,866 Unicode code points.
- Context SHA-256: `709a7a9cfe66a11f2b9ef2e18ea813e3fba4bd9a8ceb3816f0fbaf9664066e97`.

**Test record**

```text
IdeanomicsInc_20151124_8-K_EX-10.2_9354744_EX-10.2_Content License Agreement
```

- Exact-text group: `cuad-exact-v1:9b0df2e9e32f3bf7c19b0e61b331cf05e5ed2beb648be1d2b3075d36f204922c`.
- Paragraph: `0`; length: 35,189 Unicode code points.
- Context SHA-256: `c538e198298848d2e29a5e608ac164c5995768059b85485f564d184ae354f1c5`.

### Evidence and differences

The test record identifies itself as a form of a content licence agreement.
The training record has a filled effective date and `/s/` signatures. Both name
Beijing Sun Seven Stars Culture Development Limited and YOU ON DEMAND HOLDINGS,
INC. as the counterparties. These observations support a form/variant family;
they do not establish the legal validity or history of either instrument.

| Evidence | Training range | Test range |
|---|---|---|
| Effective-date phrase: filled December 21, 2015 versus a blank day/month in 2015 | `[78, 107)` | `[102, 131)` |
| Licensor name | `[156, 207)` | `[180, 231)` |
| Licensee name | `[369, 397)` | `[393, 421)` |
| Shared indemnification-section token sequence | `[25508, 27695)` | `[19828, 22016)` |
| Shared limitation-of-liability-section token sequence | `[32252, 34046)` | `[26591, 28389)` |

The two shared section ranges have identical casefolded `\w+` token sequences:
341 tokens and 295 tokens respectively. Their raw slices can have different
whitespace; no claim of byte equality is made. The training signature marker
`By: /s/ Bruno Wu` is at `[40546, 40562)`.

There are substantive differences, not merely formatting. For example, the
training text adds schedule-specific distribution, dubbing and editing
restrictions in its licence-grant provisions. A substantial part of that
material is visible in training `[4000, 8500)`. It also has expanded profit
participation provisions. Original annotations therefore remain tied to their
own document; labels are not interchangeable.

The screen found 4,912 shared distinct five-word phrases: Jaccard `0.761550`
and containment `0.933840`. These scores motivated inspection; the shared
parties, document structure, and original passages support the grouping decision.

**Decision:** keep both texts distinct, but treat these records as one related
family for split isolation. Neither text contains the other as an exact literal
substring.

## similarity-002: Women's Golf parent agreement and attachment

**Test record**

```text
WOMENSGOLFUNLIMITEDINC_03_29_2000-EX-10.13-ENDORSEMENT AGREEMENT
```

- Exact-text group: `cuad-exact-v1:25760695ffcc7d9c73db7a9d3d0babca55eb4b01b9910ef849c5f717c4ede83b`.
- Paragraph: `0`; length: 32,371 Unicode code points.
- Context SHA-256: `4409b6e45aec52486aef45e86a94f12aaa5c36246a131e1d7311585a9d37ad39`.

**Train record**

```text
WOMENSGOLFUNLIMITEDINC_03_29_2000-EX-10.13-ENDORSEMENT AGREEMENT - Intellectual Property Rights                 Confidentiality and Non-Use Obligations Agreement
```

- Exact-text group: `cuad-exact-v1:b5e4d537dbb1da2d53c36c627b8d00b090eb1f352d2fe8d2af53caf5c3e90393`.
- Paragraph: `0`; length: 7,042 Unicode code points.
- Context SHA-256: `326b491f5f1079ba35a2f03ae6a9dd9c009668e7e2a8156dedf3bbaf553b1d34`.

### Evidence and differences

The longer test record is the endorsement agreement naming SQUARE TWO GOLF INC.
and KATHY WHITWORTH. The shorter training record begins with closing provisions
11.6 and 11.7, continues through signatures, and includes Exhibit A: the
intellectual-property, confidentiality and non-use agreement. It is not an
independent unrelated contract with coincidentally similar boilerplate.

| Evidence | Test range (longer parent) | Training range (shorter record) |
|---|---|---|
| Section 11.7 heading | `[25508, 25572)` | `[294, 358)` |
| Exhibit A heading | `[26585, 26594)` | `[1339, 1348)` |
| Explicit statement that this is part of the parties' endorsement agreement | `[26934, 26986)` | `[1680, 1732)` |
| Matching complete word-token sequence of the shorter record | `[25203, 32371)` | `[1, 7042)` |

The last row contains the same 953 case-sensitive `\w+` tokens, in order.
The training range starts at 1 because its leading hyphen is not a word token.
More strongly, joining whitespace-separated pieces with one space makes the
entire training text exactly the suffix of the test text:

```python
" ".join(test_context.split()).endswith(" ".join(train_context.split()))
# True
```

Raw substring containment is false because spacing differs. This comparison
only establishes the relationship; the original contexts remain unchanged.

All 931 distinct five-word phrases from the shorter comparison text occur in
the longer one: containment `1.000000`, Jaccard `0.211447`. The lower Jaccard
reflects the longer parent agreement's additional material.

**Decision:** treat the two records as one parent/attachment family for split
isolation. Retain their separate source identities, contexts, and annotations.

## Handling rules for subsequent preparation

1. **Official benchmark:** preserve all 408 official training documents and all
   102 official test documents for the faithful benchmark workflow. Preserve the
   raw archive, source JSON, and original labels.
2. **New model's internal development pool:** reserve every confirmed family
   that touches official test membership. Exclude its training-side members
   from `fit`, `dev_select`, `dev_cal`, and `dev_policy`. Do not move test records
   into training. Apply this only through a versioned derived-data manifest
   after family review, with explicit exclusion reasons.
3. **Current count implication:** these two decisions identify two distinct
   training records for that exclusion. Before further review or family merges,
   408 training records would become 406, and 407 exact-text training groups
   would become 405. These are provisional counts, not a final prepared split;
   no exclusion has been implemented yet.
4. **Reporting:** retain the full 102-document official-test result. Also define
   a clearly named sensitivity subset excluding these two related test records
   (100 documents at this review stage), and report its category support counts.
   Record this data-based rule before inspecting model results. Broader family
   review may expand it; freeze the final manifest before evaluation.
5. **Released checkpoint:** filtering future training inputs cannot undo any
   exposure in an already trained model. Do not describe the released baseline
   as newly decontaminated or call the 100-document subset the official score.
6. **Annotation independence:** do not copy, union, or reconcile either pair's
   labels merely because the texts are related. This review does not resolve
   the separate AduroBioTech Anti-Assignment/Exclusivity disagreements.

## Remaining work

- Review the four training-only candidate pairs, including any family links
  shared between candidates.
- Keep broader template/related-document checks open: this lexical screen does
  not prove all related records were found.
- Encode the reviewed families and exclusions in a small versioned manifest,
  then implement and verify their use before assigning internal partitions.
- Continue the independent duplicate-label review documented in
  [CUAD_DataReview.md](CUAD_DataReview.md).

This note records the source evidence and preparation policy. It does not mark
family preparation, dataset splitting, model training, or evaluation complete.
