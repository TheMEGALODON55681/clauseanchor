# CUAD Soupman franchise-family source review

Reviewed: 19 October 2026 (India time).

**Status:** assistant-assisted source-text review prepared for Tanishq. The
master franchise agreement, Attachment B guarantee form, Attachment C California
appendix, and related New York disclosure addendum are classified as one family
for future split isolation: `confirmed_related_for_split_grouping`. Two records
are in official training and two are in official test.

This note resolves six title-screen pairs. It groups related source documents;
it does not establish that blank forms were completed, signed, or enforceable.
No source text, annotation, family configuration, generated report, or prepared
split has been changed.

## Scope and reproducibility

- Repository checked: `main` at `16b55b3`, including the
  [PCQuote review](CUAD_PCQuoteFamilyReview.md).
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

The source loader reverified the pinned archive, source bytes, exact annotated
spans, and official memberships. The review inspected the three complete short
records and the main agreement's identity paragraph, contents list, cited
attachment/mediation/choice-of-law provisions, and closing materials. It was a
relationship review, not a clause-by-clause annotation audit of the long record.

All ranges address `paragraphs[0].context` in zero-based Unicode code points,
with the end excluded. Paragraph hashes use the unchanged context encoded as
UTF-8. Comparison or display normalization is not written to the source.

## Family overview

| Local reference | Actual source content | Official split |
|---|---|---|
| M | Kiosk Concepts / The Grilled Cheese Truck master franchise agreement, with closing materials and Attachment A | Test |
| B | Attachment B: guarantees of the master franchise agreement | Train |
| C | Attachment C: multi-state addendum, California appendix | Train |
| N | New York disclosure addendum naming the same franchisor and master franchisee | Test |

These references are shorthand, not new canonical IDs. The dataset title names
Soupman, while the master agreement names Kiosk Concepts, Inc. and The Grilled
Cheese Truck, Inc. as the parties. The 2015-08-14 source-title date is not filled
into the blank agreement or addendum effective-date fields.

## Source identities

### M

```text
SoupmanInc_20150814_8-K_EX-10.1_9230148_EX-10.1_Franchise Agreement1
```

- Exact-text group: `cuad-exact-v1:31e8e7018dd3e72fc13b3dc851887c0bedd4b3ca7402c70c4623889bde05eb85`.
- Official split: `test`.
- Paragraph: `0`; length: 144,235 Unicode code points.
- Context SHA-256: `9009d53b3f1c416872fa6d70cdc98940f7c62f25523b76b3fe231f0e11b3d0dc`.

### B

```text
SoupmanInc_20150814_8-K_EX-10.1_9230148_EX-10.1_Franchise Agreement2
```

- Exact-text group: `cuad-exact-v1:830f3b69669b402d5608b9e2149e3497bee1b68186d13ca39a7784ace8896e54`.
- Official split: `train`.
- Paragraph: `0`; length: 5,504 Unicode code points.
- Context SHA-256: `c7753fb51c35e8316aac93bf5821f4d7d6c78323972196fc8e6c679b954d5e6c`.

### C

```text
SoupmanInc_20150814_8-K_EX-10.1_9230148_EX-10.1_Franchise Agreement3
```

- Exact-text group: `cuad-exact-v1:b141a25c7c4869417c27a4a93d593b93db2e9549a58cee70622b743737654ec5`.
- Official split: `train`.
- Paragraph: `0`; length: 2,974 Unicode code points.
- Context SHA-256: `d1c74726a00a6c1eb413437fbe539764f8d45d86b077b93b5b48a4b71b2aa048`.

### N

```text
SoupmanInc_20150814_8-K_EX-10.1_9230148_EX-10.1_Franchise Agreement4
```

- Exact-text group: `cuad-exact-v1:9936e3a4f1a28354536090480af41a5f8c26ffa027059d882ed0b8047b96ea99`.
- Official split: `test`.
- Paragraph: `0`; length: 3,314 Unicode code points.
- Context SHA-256: `d3b48e403dce07c50842f80ffc6d9b03d5e22597822766851478b17923442743`.

## Source evidence

M's contents list explicitly identifies B as the guarantees attachment and C
as the multi-state addendum. Its operative provisions also refer to executing
a guarantee in the form attached as Attachment B. B and C identify themselves
as attachments to the master franchise agreement. C refers to the Original
Soupman website and describes the parent's non-binding mediation and New York
choice-of-law provisions, which can be located in M.

N identifies itself as a New York addendum to the disclosure document. Its
closing party blocks name Kiosk Concepts and The Grilled Cheese Truck as master
franchisee, matching M. In combination with the shared source-title exhibit,
franchise subject matter, and multi-state addendum context, this supports
including N in the same related-document family. N does not explicitly label
itself Attachment C, so this review does not invent that label or treat it as
an exact extracted clause from M.

| Source evidence | Record | Exact range |
|---|---|---|
| Blank day/month and 2015 year in the agreement opening | M | `[6266, 6328)` |
| Named franchisor in the agreement opening | M | `[6367, 6411)` |
| Named master franchisee in the agreement opening | M | `[6530, 6582)` |
| Contents listing for B guarantees and C multi-state addendum | M | `[6012, 6081)` |
| Operative reference to the guarantee form as Attachment B | M | `[128714, 128778)` |
| Operative non-binding mediation heading, after the contents list | M | `[130979, 131005)` |
| New York choice-of-law wording in the parent record | M | `[130156, 130246)` |
| Schedule of Principals marked Not Applicable | M | `[143134, 143173)` |
| Explicit Attachment B and guarantees heading | B | `[0, 85)` |
| N/A entry in the master-franchisee field | B | `[249, 274)` |
| Explicit Attachment C, multi-state addendum and California heading | C | `[0, 87)` |
| Original Soupman website reference | C | `[2683, 2706)` |
| Reference to the parent agreement requiring non-binding mediation | C | `[1296, 1358)` |
| Reference to the parent agreement applying New York law | C | `[1791, 1867)` |
| New York addendum heading | N | `[0, 67)` |
| Disclosure-document subject identified by the addendum | N | `[70, 148)` |
| Kiosk Concepts party block | N | `[3055, 3075)` |
| The Grilled Cheese Truck master-franchisee party block | N | `[3152, 3201)` |
| Blank addendum day/month and 2015 year | N | `[2942, 2981)` |

## Form status and interpretation limits

B contains an N/A master-franchisee entry, blank guarantor/date fields, and
letter-spaced extraction in its opening sentence. M marks its Schedule of
Principals Not Applicable; M and N also have blank date/signature fields. Keep
these details exactly as supplied. The family relationship does not establish
an executed guarantee or permit filling blank names, dates, or signatures.

C's California appendix discusses the parent agreement, whereas N discusses
items in the disclosure document. Preserve that distinction. This review
identifies the document relationship; it does not decide current state-law
requirements or the enforceability of any provision.

None of the three complete shorter contexts is an exact literal substring of
M. They are separate source records with their own coordinates and annotations.
Do not concatenate them into a replacement parent context, transfer labels,
or infer that a clause missing from one record is absent from the wider family.

## Candidate decisions

| Candidate | Records | Official boundary | Relationship basis |
|---|---|---|---|
| `title-004` | M / B | Test / train | Named Attachment B in M and the guarantee form's own heading |
| `title-005` | M / C | Test / train | Listed Attachment C, its own heading, brand reference and parent-provision references |
| `title-010` | B / N | Train / test | Related through M and the same franchise-document family |
| `title-011` | N / C | Test / train | Related through M and the state-specific franchise/disclosure materials |
| `title-028` | M / N | Test / test | Same named parties in the master-franchisee blocks and associated disclosure addendum |
| `title-046` | B / C | Train / train | Both are named attachments to M |

All six are `confirmed_related_for_split_grouping`. Some links are transitive
through M; the decision does not assert that every document directly names all
other family members or that their substantive terms are identical.

## Handling in subsequent preparation

1. Keep M, B, C, and N in one connected family. Do not isolate B/C as a separate
   training-only family when their parent and related addendum are in test.
2. Under [CUAD_CrossSplitReview.md](CUAD_CrossSplitReview.md), reserve this family
   for new internal preparation because it touches official test. Exclude B
   and C from `fit`, `dev_select`, `dev_cal`, and `dev_policy` when implementing
   the derived policy. M and N remain in official test.
3. Preserve the official 408-training/102-test memberships, original contexts,
   and labels. No source records are deleted or moved between official splits.
4. Retain full official-test reporting. Include M and N in the exclusions for
   the separately named known-overlap-excluded sensitivity subset when revising
   the manifest; freeze this rule before inspecting model scores.
5. Continue the independent duplicate-label review in
   [CUAD_DataReview.md](CUAD_DataReview.md). This family review adjudicates no
   clause annotations and does not lift the AduroBioTech conflict hold.

## Provisional cumulative count effect

The four Soupman groups are distinct from manifest 1.0.0's families and the
subsequently reviewed Federated and PCQuote groups. Applying their combined
relationships only in memory gives the following prospective counts. No
exclusion, manifest revision, or internal partition has been written.

| Measure | Through PCQuote review | Also including Soupman review |
|---|---:|---:|
| Official training documents | 408 | 408 |
| Training documents reserved due to known cross-split families | 6 | 8 |
| Eligible documents for new internal preparation | 402 | 400 |
| Eligible exact-text groups | 401 | 399 |
| Eligible family units for internal partitioning | 397 | 395 |
| Full official test documents | 102 | 102 |
| Prospective known-overlap-excluded sensitivity test documents | 97 | 95 |

These counts remain provisional. The unchanged version 1.0.0 family checker
continues to report its earlier 406-document prospective pool and 100-document
sensitivity subset until a reviewed configuration update incorporates the notes.

## Remaining work

This note resolves four cross-split, one training-only, and one test-only pair.
Together with the Federated and PCQuote reviews, **55 of the 70 new title-screen
candidates remain:** 12 cross-split, 41 training-only, and two test-only pairs.
The one unparsed title still requires a separate inspection.

The generated report retains its original screening statuses. Record further
source decisions separately, then revise and validate the combined family
manifest before assigning internal partitions.
