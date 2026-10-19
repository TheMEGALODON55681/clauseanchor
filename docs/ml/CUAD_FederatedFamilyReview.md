# CUAD Federated services-family source review

Reviewed: 19 October 2026 (India time).

**Status:** assistant-assisted source-text review prepared for Tanishq. Four
source records are classified as one related document family for future split
isolation: the services agreement, its two amendments, and the explicitly linked
limited power of attorney. Three records are in official training and one is in
official test. The decision is `confirmed_related_for_split_grouping`.

This note resolves six title-screen candidates. It records a source-review
decision; the family manifest, generated reports, source annotations, official
memberships, and derived datasets have not been changed.

## Scope and reproducibility

- Repository checked: `main` at `dcdd327`, the source-title screen commit.
- Source: `data/raw/cuad/CUAD_v1/CUAD_v1.json`, SHA-256
  `ed0b77d85bdf4014d7495800e8e4a70565b48ee6f8a2e5dca9cf8655dbf10eae`.
- Official archive revision: `The-Atticus-Project/cuad` at
  `67faa0e6023b04fcaae6cc09497ab00e5d63a2a2`.
- Title screen: `ml/scripts/review_cuad_titles.py`, version `1.0.0`.
- Candidate snapshot: `data/processed/cuad/title_candidates.json`, canonical
  JSON SHA-256 `c9a962bba49d410bc12ddc90dabf5eeeb2458a6abf38face809968acb609c312`.
- Reviewed-family manifest snapshot: `ml/configs/cuad_family_manifest.json`,
  version `1.0.0`, canonical JSON SHA-256
  `7576938a012b45b30121887b6db7d9d9dd77e0886256a554c70085f3a8fc8dea`.
- Canonical JSON hashing uses sorted keys, compact separators, UTF-8, and
  `ensure_ascii=False`, as in `check_cuad_families.py`.
- Attribution: [CUAD README](../../data/raw/cuad/README.md).

The source loader reverified the pinned archive, source bytes, exact annotated
spans, and official memberships. All four complete contexts were inspected.
All ranges below address `paragraphs[0].context`, in zero-based Unicode code
points, with the end excluded. Paragraph hashes use the unchanged context
encoded as UTF-8. No normalized comparison text supplies annotation offsets.

## Family overview

| Local reference | Source content | Date stated in the opening | Official split |
|---|---|---|---|
| S | Services agreement | January 1, 2004 | Train |
| A1 | Amendment to the services agreement | March 30, 2009 | Train |
| A2 | Second amendment to the services agreement | March 1, 2016 | Train |
| P | Limited power of attorney referring to the services agreement | January 1, 2004 | Test |

S, A1, A2, and P are shorthand for this note, not new canonical document IDs.
The common `04_28_2020` title component is a screening hint; it is not the
effective date of all four instruments. The title's fund name also differs from
the named contracting parties: Federated Investment Management Company and
Federated Advisory Services Company. The original text establishes the links.

## Source identities

### S

```text
FEDERATEDGOVERNMENTINCOMESECURITIESINC_04_28_2020-EX-99.SERV AGREE-SERVICES AGREEMENT
```

- Exact-text group: `cuad-exact-v1:0c8ea7af1de1d140b21b7f4eaedcd45e6310fd78177f331363e8bcaaf5ac1cd8`.
- Official split: `train`.
- Paragraph: `0`; length: 11,043 Unicode code points.
- Context SHA-256: `2dfbd48812ceef61f37176296cc18ac26865a1fda32fd6f7dd42617d37a81b6d`.

### A1

```text
FEDERATEDGOVERNMENTINCOMESECURITIESINC_04_28_2020-EX-99.SERV AGREE-SERVICES AGREEMENT_AMENDMENT
```

- Exact-text group: `cuad-exact-v1:0badecfb27a0d110b91223d274a06b0713d39329cd0de962f6a5795f3ece340a`.
- Official split: `train`.
- Paragraph: `0`; length: 3,860 Unicode code points.
- Context SHA-256: `87cd114c450d1ae9b93fe66dc277a9d5bdc04b6885e5e90b86de20193a1cbd3f`.

### A2

```text
FEDERATEDGOVERNMENTINCOMESECURITIESINC_04_28_2020-EX-99.SERV AGREE-SERVICES AGREEMENT_SECONDAMENDMENT
```

- Exact-text group: `cuad-exact-v1:e294c17356892668cb33d5f6ed53411170684696dd7dc83939394c3371d87514`.
- Official split: `train`.
- Paragraph: `0`; length: 5,466 Unicode code points.
- Context SHA-256: `6947af5e0cc6772b8299809ec4362369562c778568d2e79fce38dae5e398bfcb`.

### P

```text
FEDERATEDGOVERNMENTINCOMESECURITIESINC_04_28_2020-EX-99.SERV AGREE-SERVICES AGREEMENT_POWEROF
```

- Exact-text group: `cuad-exact-v1:f8247974eb9bda782b5a4344a46d9f12a29ccced94fc6cdafe4dc95b83c2500f`.
- Official split: `test`.
- Paragraph: `0`; length: 14,384 Unicode code points.
- Context SHA-256: `df60e354f88a3b0120135e0886e3c6ff141309d8a0c253c0ac4c5a5b9ed50ce6`.

## Evidence establishing the relationship

### Services agreement and amendments

S names Federated Investment Management Company as the Adviser and Federated
Advisory Services Company as FASC. A1 and A2 identify those same parties and
explicitly refer to their services agreement dated January 1, 2004. A2 also
explicitly identifies the amendment dated March 30, 2009. These references
establish an agreement/amendment chain independently of the source filenames.

| Source evidence | Record | Exact range |
|---|---|---|
| Agreement's dated-and-effective phrase, January 1, 2004 | S | `[111, 152)` |
| Adviser name in the opening | S | `[180, 219)` |
| FASC name in the opening | S | `[269, 304)` |
| Amendment's dated-and-effective phrase, March 30, 2009 | A1 | `[71, 111)` |
| Explicit reference to the services agreement dated January 1, 2004 | A1 | `[526, 572)` |
| Heading identifying the amendment to Exhibit A | A1 | `[1711, 1756)` |
| Second amendment's dated-and-effective phrase, March 1, 2016 | A2 | `[84, 123)` |
| Explicit reference to the services agreement dated January 1, 2004 | A2 | `[544, 590)` |
| Explicit reference to the amendment dated March 30, 2009 | A2 | `[1063, 1121)` |
| Heading identifying the second amendment to Exhibit A | A2 | `[2286, 2338)` |

The texts contain different material. S sets out services, fees, liability,
duration, and exhibits. A1 replaces the administration/risk-management section
of Exhibit A for specified accounts. A2 supplements Exhibit A with equity
trading/settlement, fundamental-analysis, and quantitative-analysis services.
Grouping does not authorize combining these texts into a reconstructed contract
or transferring their annotations.

### Limited power of attorney

P appoints FASC to act for the Adviser and explicitly connects that authority
to the services agreement dated January 1, 2004 between the same parties. It
also states that the power of attorney terminates automatically when the
services agreement is cancelled or terminated. This is substantive linkage,
beyond a shared company name or generic contract wording.

| Source evidence | Record | Exact range |
|---|---|---|
| Opening statement dated January 1, 2004 | P | `[27, 86)` |
| Services agreement's date and identification of its parties | P | `[1065, 1140)` |
| Automatic termination linked to cancellation/termination of the services agreement | P | `[7168, 7307)` |
| Schedule 1 heading with its own October 1, 2016 date and March 1, 2020 revision | P | `[10494, 10583)` |

P is a separate related instrument, not a duplicate of S or either amendment.
Its context also contains the funds/accounts schedule. The schedule's dates
are retained as written; they are not substituted for the opening date or
reconciled by this review. This is a provenance/grouping decision, not a
reconstruction or adjudication of the instruments' legal history.

## Candidate decisions

All six candidate pairs below are `confirmed_related_for_split_grouping`.
Direct cross-references and the common underlying agreement establish one
connected four-record family. Some pair relationships are transitive through S;
this does not imply that every record names every other record directly.

| Candidate | Records | Official boundary | Evidence basis |
|---|---|---|---|
| `title-001` | A1 / P | Train / test | Both explicitly refer to S and the same parties |
| `title-002` | S / P | Train / test | P identifies S by date/parties and links its termination to S |
| `title-012` | A2 / P | Train / test | Both explicitly refer to S and the same parties |
| `title-023` | A1 / S | Train / train | A1 identifies and amends S |
| `title-024` | A1 / A2 | Train / train | A2 expressly references A1's March 30, 2009 date |
| `title-025` | S / A2 | Train / train | A2 identifies and supplements S |

## Handling in subsequent preparation

1. Treat all four exact-text groups as one connected family. Do not create a
   separate training-only subfamily for S/A1/A2 while leaving P outside it.
2. Under the policy in [CUAD_CrossSplitReview.md](CUAD_CrossSplitReview.md),
   reserve this family for the new model's internal preparation because it
   touches official test. Its three training records must be excluded from
   `fit`, `dev_select`, `dev_cal`, and `dev_policy` when the derived policy is
   implemented. P remains in official test.
3. Preserve the official 408-training/102-test memberships and original source
   annotations. Do not delete records, move P into training, or rewrite source
   texts. Keep this derived exclusion separate from the faithful benchmark.
4. Retain full official-test reporting and update the separately named
   known-overlap-excluded sensitivity subset when the reviewed manifest is
   revised. Record that rule before inspecting model results.
5. Do not infer new clause labels from the relationship. The independent
   AduroBioTech annotation disagreements in
   [CUAD_DataReview.md](CUAD_DataReview.md) remain unresolved.

## Provisional count effect

All four groups are distinct from the groups in manifest 1.0.0. Combining this
review with its already recorded families gives the following prospective
counts. They were checked by connecting the verified group IDs in memory;
no revised manifest, exclusions, or partitions were written.

| Measure | Manifest 1.0.0 decisions | Including this review |
|---|---:|---:|
| Official training documents | 408 | 408 |
| Training documents reserved due to known cross-split families | 2 | 5 |
| Eligible documents for new internal preparation | 406 | 403 |
| Eligible exact-text groups | 405 | 402 |
| Eligible family units for internal partitioning | 401 | 398 |
| Full official test documents | 102 | 102 |
| Prospective known-overlap-excluded sensitivity test documents | 100 | 99 |

These counts remain provisional because additional title candidates still
require review. The current `check_cuad_families.py` output should continue to
show the manifest 1.0.0 values until its versioned configuration is updated.

## Remaining work

This note resolves three cross-split and three training-only pairs from the
70 pending title-screen candidates. **64 remain:** 18 cross-split, 42
training-only, and four test-only pairs. The report's one unparsed title also
requires inspection; it is separate from those pair counts.

The generated report retains its original pending statuses. It is a frozen
screening snapshot; this Markdown note is the new decision record. Incorporate
these decisions into a versioned manifest after the next review steps, then
verify the combined connected families before preparing internal splits.
