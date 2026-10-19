# CUAD training-family source review

Reviewed: 19 October 2026 (India time).

**Status:** assistant-assisted source-text review prepared for Tanishq. All four
training-only candidates from similarity screen 1.0.0 are classified as
`confirmed_related_for_split_grouping`. They connect seven source documents
into three families. This note records evidence and future preparation rules;
it does not implement grouping, exclusions, annotation changes, or splits.

A family is a set of related source records that must stay together in a future
internal partition. It can contain different agreement versions or a parent
agreement and an attachment. Family membership does not make their texts or
annotations interchangeable.

## Scope and reproducibility

- Full source: `data/raw/cuad/CUAD_v1/CUAD_v1.json`, SHA-256
  `ed0b77d85bdf4014d7495800e8e4a70565b48ee6f8a2e5dca9cf8655dbf10eae`.
- Official archive: `The-Atticus-Project/cuad`, revision
  `67faa0e6023b04fcaae6cc09497ab00e5d63a2a2`.
- Screen: `ml/scripts/review_cuad_similarity.py`, version `1.0.0`, introduced
  in commit `4613263`.
- Generated candidates: `data/processed/cuad/similarity_candidates.json`.
- Repository checked: `main` at `626990f`, which includes the preceding
  [cross-split review](CUAD_CrossSplitReview.md).
- Source attribution: [CUAD README](../../data/raw/cuad/README.md).

The source loader reverified the pinned archive, source-file bytes, original
answer spans, and official memberships. All seven records below belong to the
**official training split**. Their lengths, hashes, identities, evidence ranges,
and family counts were checked against the source JSON.

All ranges address `paragraphs[0].context`, in zero-based Unicode code points,
with the end excluded. Context hashes use the unchanged string encoded as UTF-8.
Word-token comparisons are evidence checks only; they do not supply annotation
offsets or alter source text.

## Decision summary

| Candidate | Records below | Relationship | Family |
|---|---|---|---|
| `similarity-003` | L1 and C1 | Related domain-name/content licence records, with different exhibit coverage | Leju / China Real Estate |
| `similarity-006` | L2 and C1 | Separately stored Exhibit B corresponding to the larger record's Exhibit B | Leju / China Real Estate |
| `similarity-004` | A1 and A2 | Related intellectual-property agreement records, with different attachment coverage | Armstrong |
| `similarity-005` | N1 and N2 | Complete shorter context is an exact suffix of the longer context | NETGEAR / Ingram Micro |

C1 is shared by candidates 003 and 006. Therefore L1, C1, and L2 form **one
three-member family**, even though the screen did not flag L1 against L2.
Treating the two edges as independent two-member groups would permit related
material to cross partitions.

| Candidate | Shared distinct five-word phrases | Jaccard | Containment |
|---|---:|---:|---:|
| `similarity-003` | 6,445 | 0.920057 | 0.975924 |
| `similarity-004` | 7,864 | 0.846502 | 0.969787 |
| `similarity-005` | 553 | 0.619955 | 1.000000 |
| `similarity-006` | 288 | 0.041928 | 0.926045 |

These are screening scores, not model-quality measurements or probabilities.
Low Jaccard can coexist with a strong attachment relationship when one record
is much shorter than the other.

## Source identities

L1, C1, L2, A1, A2, N1, and N2 are local shorthand for this note only. They are
not new canonical document IDs or family IDs. Every record has one paragraph.

### L1

```text
LejuHoldingsLtd_20140121_DRS (on F-1)_EX-10.26_8473102_EX-10.26_Content License Agreement1
```

- Exact-text group: `cuad-exact-v1:1ba4a1ff167c30273cb0680cb323acb187edd67c17c020b9c1aede8cca3d46e8`.
- Context length: 46,696 Unicode code points.
- Context SHA-256: `edb50810e93b97e83365e7e66f2bf583cfee3981ea1ffdbbcb9f0783d9050e2e`.

### C1

```text
ChinaRealEstateInformationCorp_20090929_F-1_EX-10.32_4771615_EX-10.32_Content License Agreement
```

- Exact-text group: `cuad-exact-v1:c2466bae8d8436ab8001f7729c9a7836c6037753fe68e1a15219a68283fcd182`.
- Context length: 49,191 Unicode code points.
- Context SHA-256: `8881b5815dde9e3f52c43311f80baaf25e10dd15ed5b52740e94ca4a0aba433a`.

### L2

```text
LejuHoldingsLtd_20140121_DRS (on F-1)_EX-10.26_8473102_EX-10.26_Content License Agreement2
```

- Exact-text group: `cuad-exact-v1:073b83439a183fb911be23eade348bb07e38d33035e3351c0f3e930a52e8638b`.
- Context length: 2,180 Unicode code points.
- Context SHA-256: `01ebcd4dc1fdc164d0f68fd217be2b99ba76c39f5d842288808a1dca8c8d839c`.

### A1

```text
ARMSTRONGFLOORING,INC_01_07_2019-EX-10.2-INTELLECTUAL PROPERTY AGREEMENT
```

- Exact-text group: `cuad-exact-v1:1571c735d94f7aef8a458d0182be8c57662e2a4ba737b08003b8a86af637e958`.
- Context length: 69,759 Unicode code points.
- Context SHA-256: `8ff1a7503594d70ad15a6cdad9242ff5d5d8ca9db2e75074d02834d9b1b47b3d`.

### A2

```text
ArmstrongFlooringInc_20190107_8-K_EX-10.2_11471795_EX-10.2_Intellectual Property Agreement
```

- Exact-text group: `cuad-exact-v1:aa870826a1af38874d1b4fa36e4c4bcde0f2c70e392ebb24172f5441f55a2bfc`.
- Context length: 56,858 Unicode code points.
- Context SHA-256: `4311463a9da996c008b3c16e323d32c517ed1b785f283a30ee1aceccacf90558`.

### N1

```text
NETGEAR,INC_04_21_2003-EX-10.16- AMENDMENT #2 TO THE DISTRIBUTION AGREEMENT
```

- Exact-text group: `cuad-exact-v1:04993e9fb171451eb13473b9cdf36d9ec5d6e0f3f6c39e193ec0d8db3bfc34a0`.
- Context length: 4,567 Unicode code points.
- Context SHA-256: `40b9a08eaf9a9a4cb8062d44af4289e0cb7732b2fe464b083505594978f1b776`.

### N2

```text
NETGEAR,INC_04_21_2003-EX-10.16-AMENDMENT TO THE DISTRIBUTOR AGREEMENT BETWEEN INGRAM MICRO AND NETGEAR
```

- Exact-text group: `cuad-exact-v1:aacfd33dfc6f28e8a4dd6cd384df7ab9ad8f865545d5c18c39c6ae94af5d2f63`.
- Context length: 8,113 Unicode code points.
- Context SHA-256: `a26d0a46ae672963f96e729745f458b9684cbee0ac2b723045a6fe227cbd1fd7`.

## Leju / China Real Estate: candidates 003 and 006

### L1 and C1: agreement records

Both records identify the domain-name/content licence parties as Beijing SINA
Internet Information Service Co., Ltd. and Beijing Yisheng Leju Information
Services Co., Ltd. Both refer to the SINA/CRIC share purchase agreement dated
July 23, 2009 and the earlier domain-name licence dated May 8, 2008. The recitals
explicitly connect the earlier licence's termination to Exhibit B.

Long sections match in word order, beyond the shared parties and document title:

| Evidence | L1 range | C1 range | Equal casefolded word tokens |
|---|---|---|---:|
| Shared agreement sequence | `[10931, 14641)` | `[10956, 14686)` | 596 |
| Further shared agreement sequence | `[36431, 40030)` | `[36626, 40241)` | 583 |

The main agreement signature blocks in **both** records contain `/s/ Charles
Chao` and `/s/ Fei Cao`. Their source headings, extraction spacing, and filing
footers differ. L1 retains a Chinese company name that is missing from C1's
opening parenthesis. L1 ends after Exhibit A's licensed domain names; C1
continues with Exhibit B, starting at `[46988, 46997)`.

Neither full context is an exact literal substring of the other. The grouping
is supported by the shared agreement content and explicit exhibit links; it
does not assert identical legal instruments or identical source annotations.

### L2 and C1: the termination exhibit

L2 starts with Exhibit B, the mutual termination agreement between Beijing SINA
and Shanghai SINA Leju Information Technology Co. Ltd. It refers to the same
May 8, 2008 domain-name licence and contains the same five numbered provisions
as Exhibit B within C1: termination, entire agreement, governing law,
counterparts, and successors/assigns.

| Evidence | L2 range | C1 range | Equal casefolded word tokens |
|---|---|---|---:|
| Exhibit heading through the five provisions and signature-page marker | `[0, 1778)` | `[46988, 48763)` | 272 |

Filing footers, whitespace, and page-number placement differ. Neither raw nor
whitespace-collapsed full-context containment holds, so this is not recorded as
an exact substring match. The attachment identity, named parties, earlier
agreement reference, and matching provisions establish the relationship.

**Decision:** keep L1, C1, and L2 together as one family in future internal
partitioning. Retain all three records with their own contexts and labels.

## Armstrong: candidate 004

A1 and A2 begin with the same intellectual-property agreement dated December
31, 2018. Both name Armstrong Flooring, Inc., AFI Licensing LLC, AHF Holding,
Inc. (formerly Tarzan HoldCo, Inc.), and Armstrong Hardwood Flooring Company.
Both refer to the stock purchase agreement dated November 14, 2018.

| Evidence | A1 range | A2 range | Equal casefolded word tokens |
|---|---|---|---:|
| Section 9 prosecution, maintenance and enforcement sequence | `[21350, 24767)` | `[21742, 25159)` | 525 |
| Survival provision and following agreement sequence | `[27539, 30860)` | `[28029, 31350)` | 540 |

A2 includes recurring filing-source footers, shifting later offsets. Both
contain trademark presentation guidelines. A2 ends after the Exhibit A
trademark licence heading, an attachment indication, and a source footer.
A1 continues with additional attachment text: the Exhibit B form of patent
assignment heading is at `[54904, 54941)`, followed later by a form of trademark
assignment and its schedule. A2 does not contain that Exhibit B heading or the
corresponding assignment forms.

Neither full context is an exact literal substring of the other. The shared
agreement and differing attachment coverage support family membership; these
are still separate source records with different text lengths and coordinates.

**Decision:** keep A1 and A2 together in future internal partitioning. Do not
fill missing attachment labels in one record using annotations from the other.

## NETGEAR / Ingram Micro: candidate 005

The complete shorter context N1 occurs literally at the end of N2:

```python
N2_context[3546:8113] == N1_context[0:4567]
# True: exact original-string equality, with no normalization.
```

N1 contains an amendment effective October 1, 1996, followed by the July 15,
1998 amendment numbered 2. Both concern NETGEAR and Ingram Micro. N2 adds
preceding distribution-agreement provisions and an exhibit before the shared
amendment material. The source title of N1 names Amendment 2, but its context
contains both amendment sections; this review follows the actual context.

The exact suffix relationship is stronger evidence than the screening score.
The 4,567 matching code points still have different document-relative offsets:
N1 begins at 0 while the corresponding material begins at 3,546 in N2.

**Decision:** keep N1 and N2 together in future internal partitioning. Retain
both source records. Do not assume their annotation sets agree merely because
the shorter text is exactly contained in the longer one.

## Rules for subsequent preparation

1. **Family isolation:** assign an entire connected family to one internal
   partition: `fit`, `dev_select`, `dev_cal`, or `dev_policy`. Windowing or
   question expansion must inherit that assignment; they must not independently
   split related records.
2. **Source preservation:** keep original titles, exact-text group IDs, contexts,
   labels, and official train/test memberships. A family is a grouping unit,
   not a replacement text or permission to deduplicate examples automatically.
3. **Annotation independence:** do not copy answers, union labels, or infer
   absence across family members. All existing spans remain tied to their own
   paragraph and source identity. Any weighting or annotation reconciliation
   requires a separate recorded decision.
4. **Cross-split handling:** retain the policy in
   [CUAD_CrossSplitReview.md](CUAD_CrossSplitReview.md). For a new clean-split
   model, reserve confirmed families touching official test and exclude their
   training members from all internal training/development partitions. The
   official benchmark membership itself stays unchanged.
5. **Duplicate-label hold:** the separate AduroBioTech Anti-Assignment and
   Exclusivity disagreements in [CUAD_DataReview.md](CUAD_DataReview.md) remain
   pending. This review does not adjudicate them or lift their proposed hold.

## Provisional count reconciliation

The following counts were checked by connecting the six reviewed candidate
pairs over the verified 509 exact-text groups. They describe the planned
handling of currently known families; no prepared split has been written.

| Stage | Training-source documents | Exact-text groups | Units for internal partitioning |
|---|---:|---:|---:|
| Official training membership | 408 | 407 | 407 before related-family grouping |
| After reserving the two known cross-split families | 406 | 405 | 405 before training-family grouping |
| After grouping the three training-only families | 406 | 405 | 401 |

The seven training-only member groups become three family units, a reduction
of four units. The earlier exact-duplicate group already accounts for the
one-document difference between document and exact-group counts. Grouping
retains records; it does not remove four documents.

These decisions add no new test-side exclusions. The full official test still
has 102 documents; the previously described known-overlap-excluded sensitivity
subset would currently have 100. All counts remain subject to broader family
review before a final manifest is frozen.

## Completion boundary and next step

All six candidates returned by screen 1.0.0 now have source-review decisions:
two in the cross-split note and four here. This completes review of that
candidate list, not a proof that the dataset contains no other related records.
The lexical thresholds can miss other templates or related contracts.

The generated screen report still says `pending_manual_review`; it is an
unaltered screening artifact, not the decision store. These Markdown reviews
record the decisions until they are encoded in a versioned family manifest.

Next, encode the reviewed relationships and cross-split handling in that
manifest, verify identities and connected-family consistency, and complete the
remaining broader checks before assigning internal partitions. Model training,
annotation adjudication, and evaluation have not started in this step.
