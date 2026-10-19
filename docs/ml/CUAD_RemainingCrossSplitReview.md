# CUAD remaining cross-split candidate review

Reviewed: 19 October 2026 (India time).

**Status:** assistant-assisted source-text review prepared for Tanishq.
This note examines the nine cross-split candidates remaining after the
[Cardlytics review](CUAD_CardlyticsFamilyReview.md), plus three associated
same-split candidates. Four pairs are confirmed, six are rejected for the
specific grouping proposed by the screen, and two remain unresolved.

The Cardlytics note and this note together examine 18 previously pending pairs:
10 confirmed, six rejected, and two unresolved. They document 16 resolved
decisions. They do not update the family manifest, apply exclusions, change
source text or annotations, assign internal partitions, or begin training.

## Scope and reproducibility

- Repository checked: `main` at `d8d6aca019fe38c9fe0d9f2819227b89f3f65310`.
- Source: `data/raw/cuad/CUAD_v1/CUAD_v1.json`, SHA-256
  `ed0b77d85bdf4014d7495800e8e4a70565b48ee6f8a2e5dca9cf8655dbf10eae`.
- Official archive: `The-Atticus-Project/cuad`, revision
  `67faa0e6023b04fcaae6cc09497ab00e5d63a2a2`, SHA-256
  `f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a`.
- Title screen: `ml/scripts/review_cuad_titles.py`, version `1.0.0`.
- Title-report canonical SHA-256:
  `c9a962bba49d410bc12ddc90dabf5eeeb2458a6abf38face809968acb609c312`.
- Family manifest: version `1.0.0`, canonical SHA-256
  `7576938a012b45b30121887b6db7d9d9dd77e0886256a554c70085f3a8fc8dea`.
- Canonical hashes use sorted keys, compact JSON, UTF-8 and
  `ensure_ascii=False`, as in `check_cuad_families.py`.
- Attribution: [CUAD README](../../data/raw/cuad/README.md).

The existing source loader reverified the pinned archive, source bytes,
answer spans and official memberships. Both screening reports were regenerated
in the assistant's workspace and their canonical hashes checked against the
recorded snapshots. This does not mean reports on Tanishq's laptop changed.

Review scope: full short contexts for SC, SA, SZ, RT, RA, ES and PC; targeted
identity, operative-purpose, attachment, date, contact and signature passages
for SM, RE, EE, PO, GL and GS; and the full-context literal searches listed
below. The long records were not reviewed clause by clause. This is an
agreement-family review, not annotation adjudication, a legal opinion, or a
proof that all possible business or template connections have been found.

Ranges refer to `paragraphs[0].context`, in untouched Unicode code points,
zero-based with the end excluded. Source identities and paragraph hashes are
listed in the appendix. Local aliases are shorthand, not canonical IDs.

## Decision meanings

- **Confirmed:** `confirmed_related_for_split_grouping`. The evidence supports
  one connected agreement family; it does not make the texts or labels identical.
- **Rejected:** the particular title-screen grouping is not supported by the
  reviewed evidence; the records describe distinct identified transactions.
  This does not assert the companies have no other relationship or prove the
  absence of all shared wording. Reopen if stronger source evidence appears.
- **Unresolved:** do not treat the pair as unrelated or the training member as
  cleared for internal use. Resolve the evidence/policy question before internal
  splits, or explicitly adopt and implement a separately documented conservative
  hold. No hold or new exclusion is implemented by this note.

These are documentary outcomes. Manifest 1.0.0 and its validator do not yet
consume title-screen decisions, rejected outcomes or unresolved cases.

## ScanSource: one Cisco family and a separate Zebra addendum

| Alias | Source content | Official split |
|---|---|---|
| SM | Cisco / ScanSource nonexclusive value-added distributor agreement | Train |
| SC | Exhibit C, Cisco software-license agreement | Train |
| SA | Amendment No. 3 to the Cisco / ScanSource agreement | Test |
| SZ | Zebra PartnerConnect / Xplore distribution addendum | Test |

**Confirm SM, SC and SA as one connected family.** SM expressly incorporates
Exhibit C, identifies it as the software-license agreement, and in section 9.1
maps its Customer references to Distributor. SC identifies itself as Exhibit C
and names Cisco as licensor. The shared source exhibit supports this direct
attachment evidence; its generic end-user wording alone would not establish
which distribution agreement it belongs to.

SA names Cisco and ScanSource and expressly refers to the agreement dated
January 22, 2007. SM's signature page supplies that date. SA and SC connect
through SM. The complete SC context is not an exact literal substring of SM.
Keep all three identities, coordinates and annotation sets separate.

**Reject joining SZ to that Cisco family.** SZ names Zebra companies and
Xplore, identifies a February 12, 2014 agreement renamed in April 2016, and
adds Xplore products following Zebra's acquisition. This identifies a different
distribution chain from the Cisco agreement and its 2010 amendment. A shared
distributor and the word "Distributor" in dataset titles are insufficient.

| Source evidence | Record | Exact range |
|---|---|---|
| Cisco and ScanSource agreement identity and parties | SM | `[329, 783)` |
| Exhibit C named in incorporated attachments | SM | `[1221, 1261)` |
| Section 9.1 applies Exhibit C and maps Customer to Distributor | SM | `[21925, 22151)` |
| Signature dates, including January 22, 2007 | SM | `[2481, 2517)` |
| Separate record identifies itself as Exhibit C software license | SC | `[15, 65)` |
| License identifies Cisco as licensor | SC | `[1421, 1586)` |
| Amendment identifies the parent agreement by date | SA | `[1055, 1156)` |
| Amendment signature dates retained as printed | SA | `[10822, 10848)` |
| Zebra addendum heading | SZ | `[328, 415)` |
| Different underlying agreement: February 2014, renamed April 2016 | SZ | `[2229, 2375)` |
| Xplore acquisition and product addition | SZ | `[2742, 2842)` |

| Candidate | Records | Official boundary | Decision |
|---|---|---|---|
| `title-014` | SA / SC | Test / train | Confirmed through SM |
| `title-015` | SA / SM | Test / train | Confirmed agreement/amendment chain |
| `title-037` | SC / SM | Train / train | Confirmed parent/attachment |
| `title-020` | SC / SZ | Train / test | Rejected: Cisco license versus Zebra/Xplore chain |
| `title-021` | SM / SZ | Train / test | Rejected: different named distribution agreements |
| `title-059` | SA / SZ | Test / test | Rejected: amendments to different agreements |

When a reviewed manifest revision is implemented, reserve SM and SC from all
new internal preparation because SA is in official test. Include SA among the
known-overlap sensitivity exclusions. SZ gets no such exclusion from these
decisions. Preserve the original signature dates and redactions; the 2019
dataset-title dates are not the agreements' effective dates.

## Gridiron: test-only endorsement family, separate biomass supply

| Alias | Source content | Official split |
|---|---|---|
| RE | NFL Alumni endorsement / logo-license agreement | Test |
| RA | Addendum I to the October 30, 2017 endorsement agreement | Test |
| RT | Shi Farms / Gridiron hemp-biomass supply agreement | Train |

**Confirm RE and RA as one test-only family.** RA expressly attaches to the
October 30, 2017 agreement between the NFLA, NFLA-NC and the Company, matching
RE, and adds CBD water to the licensed-product list.

**Reject joining RT to that endorsement family.** RT names EWSD 1, LLC doing
business as Shi Farms and Gridiron, and orders 30,000 pounds of hemp biomass.
It is a separate procurement transaction, whereas RE/RA concern NFL Alumni
endorsement, logo rights and related donations. Shared Gridiron identity,
business address, CBD subject matter or a possible real-world supply chain
does not establish the same agreement/attachment/amendment family. No claim
is made about whether the biomass ultimately entered an endorsed product.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent endorsement agreement date | RE | `[39, 101)` |
| NFLA logo-licensing purpose | RE | `[1287, 1455)` |
| Addendum expressly attaches to the October 30 parent | RA | `[853, 1068)` |
| CBD water added to licensed products | RA | `[1071, 1160)` |
| Addendum effective date | RA | `[105, 143)` |
| Separate addendum execution statement | RA | `[3006, 3070)` |
| Different counterparty: Shi Farms and Gridiron | RT | `[87, 234)` |
| Distinct hemp-biomass purchase | RT | `[857, 977)` |
| Supply agreement signature dates | RT | `[5603, 5634)` |

| Candidate | Records | Official boundary | Decision |
|---|---|---|---|
| `title-055` | RE / RA | Test / test | Confirmed explicit endorsement/addendum chain |
| `title-016` | RT / RE | Train / test | Rejected: supply purchase versus endorsement |
| `title-017` | RT / RA | Train / test | Rejected: supply purchase versus endorsement addendum |

This test-only family creates no training reservation or known cross-split
sensitivity exclusion. Both test records remain in all official-test reporting.
Preserve RA's November 7 effective-date statement and separate November 22
execution statement. Preserve all original addresses and source spelling;
the printed supply specifications are not corrected or treated as legal advice.

## SPI Energy: distinct solar projects

PO is a Solar Tax Partners 1 / Solar Power operations-and-maintenance agreement
for Aerojet Phase 1 in Rancho Cordova, California, with a 3.6 MW system in its
Exhibit A and December 11, 2009 signature dates. PC is a June 2014 cooperation
agreement between the Fenyi County government and Xinyu Xinwei New Energy for
a 50MWp project in Yangqiao. Its referenced town-level cooperation agreement
is not PO's 2009 EPC agreement or its California facility.

The different counterparties, identified sites, capacities and transaction
purposes support **rejecting `title-019` (PO / PC, train / test)**. Shared
dataset issuer and solar-energy subject matter do not establish one family.
This decision creates no new reservation or sensitivity exclusion.

| Source evidence | Record | Exact range |
|---|---|---|
| Aerojet site and service provider | PO | `[205, 317)` |
| Owner and service-provider parties | PO | `[506, 626)` |
| Actual referenced EPC agreement | PO | `[3734, 3832)` |
| Signature date | PO | `[40669, 40692)` |
| 3.6 MW installation in Exhibit A | PO | `[41228, 41269)` |
| Separate 50MWp Yangqiao project | PC | `[16, 127)` |
| Fenyi government and Xinyu Xinwei parties | PC | `[130, 217)` |
| Reference is to the Yangqiao town cooperation agreement | PC | `[1292, 1480)` |
| 2014 signature date | PC | `[2709, 2722)` |

## GPAQ: unresolved shared-project boundary

GL is a media-license agreement involving PFHOF, HOF Village Media Group and,
for a specified provision, HOFV. It references a December 11, 2018 master
transaction and defines a September 16, 2019 merger agreement. GS is the
December 2018 sponsorship-and-services agreement between HOFV/PFHOF and
Constellation, covering energy products/services and Village sponsorship.

The parties overlap and both records concern the actual Hall of Fame Village
project. This is more evidence than issuer-name similarity. However, the
reviewed source does not identify one record as an amendment, attachment or
replacement of the other, and GS's sponsorship-rights exhibit is redacted.
The master-transaction reference must not be assumed to include GS merely
because the dates and project are nearby.

**`title-013` (GS / GL, test / train) remains unresolved.** No confirmed
family edge or new exclusion is counted. This is not a clearance for GL to
enter an internal partition.

| Source evidence | Record | Exact range |
|---|---|---|
| Media-license agreement heading | GL | `[28, 51)` |
| Parties, including PFHOF and HOFV | GL | `[232, 602)` |
| Media agreement references a master transaction and the Village | GL | `[664, 1081)` |
| Merger agreement definition names a separate September 2019 transaction | GL | `[4579, 4671)` |
| Sponsorship/services parties and December 2018 date | GS | `[376, 665)` |
| The same Village project, with a different sponsorship/services purpose | GS | `[1192, 1363)` |
| Sponsorship-rights exhibit is redacted | GS | `[54438, 54477)` |

**Follow-up:** inspect the referenced master transaction and its agreement
schedule, if available from the original filing, for a specific link to the
Constellation agreement. If no decisive evidence is available, explicitly
decide whether project-linked agreements of this kind require a conservative
hold for the intended evaluation scope. Record that rule and its count effect
before implementing splits, without using model scores to choose the outcome.

## EcoScience: unresolved shared address and promotion

EE is the November 2017 Stephen Marley endorsement agreement for ESSI products,
including UseHerbo and Herbo Wallet. ES is the April 2018 Fruit of Life
Productions / EcoScience Kaya Fest sponsorship, whose benefits include Herbo
promotion. The named counterparties and immediate contractual duties differ.

However, **EE's contact address for Stephen Marley corresponds to ES's address
for Fruit of Life Productions**: street number 16115, SW 117th Avenue, Suite
21-A, Miami, Florida 33177. The raw strings differ in punctuation and retain
the extracted `117t h` spelling. This comparison does not rewrite either source.
The common counterparty address and brand make an automatic rejection too
strong. They also do not establish corporate identity, agency, or an amendment
relationship. EE allows additional paid appearances, but that is not proof
that ES is an order under EE.

**`title-018` (EE / ES, train / test) remains unresolved.** No family edge or
additional exclusion is counted; EE is not cleared for internal preparation.

| Source evidence | Record | Exact range |
|---|---|---|
| Stephen Marley endorsement identity and date | EE | `[83, 254)` |
| Herbo branding in the endorsement | EE | `[1413, 1442)` |
| Additional appearances require an additional agreed fee | EE | `[3213, 3383)` |
| Talent contact address | EE | `[8997, 9067)` |
| Sponsorship identity and April 2018 date | ES | `[73, 215)` |
| Kaya Fest event | ES | `[324, 358)` |
| Herbo promotion in event benefits | ES | `[968, 1039)` |
| Promoter contact address corresponds to the talent address | ES | `[7185, 7287)` |

**Follow-up:** inspect the associated original filings or identified event
documents for an explicit link between the endorsement and sponsorship, or
document a conservative campaign-family hold if the evidence stays ambiguous.
Do not infer affiliation from an address alone, fill missing attachments, or
treat silence in the supplied contexts as proof of independence.

## Full-context search checks and limits

These case-insensitive literal searches were run on the complete, unchanged
contexts. Every listed term returned zero occurrences in the indicated records.
They supplement the positive identity evidence; absence of a literal string
does not prove that a paraphrased or external relationship is absent.

| Records searched | Terms with zero literal matches |
|---|---|
| SM, SC, SA | `Zebra`; `Xplore` |
| SZ | `Cisco` |
| RT | `NFLA`; `Football`; `Food For Athletes`; `endorsement` |
| RE, RA | `Shi Farms`; `EWSD`; `biomass` |
| PO | `Fenyi`; `Yangqiao`; `Xinyu`; `Xinwei` |
| PC | `Aerojet`; `Rancho Cordova`; `Solar Tax Partners` |
| GL | `Constellation`; `SPONSORSHIP AND SERVICES AGREEMENT` |
| GS | `MEDIA LICENSE AGREEMENT`; `Master Transaction Agreement` |
| EE | `Kaya`; `Fruit of Life` |
| ES | `Stephen`; `Marley` |

## Prospective cumulative effect

Confirmed edges were combined in memory with manifest 1.0.0 and the committed
Federated, PCQuote and Soupman decisions. Rejected and unresolved pairs add
no edges. Cardlytics adds three training-side reservations and one test-side
sensitivity exclusion; the Cisco family adds two and one respectively. The
Gridiron endorsement family is test-only and changes neither count.

| Measure | Committed through Soupman | Including Cardlytics | Including this batch |
|---|---:|---:|---:|
| Official training documents | 408 | 408 | 408 |
| Prospective training reservations for confirmed cross-split families | 8 | 11 | 13 |
| Prospective eligible training documents | 400 | 397 | 395 |
| Prospective eligible exact-text groups | 399 | 396 | 394 |
| Prospective eligible family units | 395 | 392 | 390 |
| Full official test documents | 102 | 102 | 102 |
| Prospective known-overlap-excluded sensitivity test documents | 95 | 94 | 93 |

**These are counts for confirmed relationships only, not a final cleared
training pool.** The two unresolved cross-split pairs, the unreviewed
training-only candidates and the unparsed title remain open. Future resolution
or a separately approved conservative hold can change these figures. The
AduroBioTech annotation conflicts also remain unresolved and have not been
implemented as training filtering.

The unchanged manifest 1.0.0 checker still reports **406 documents, 405 exact
groups, 401 family units and 100 sensitivity-test documents**. It is expected
to differ from the prospective documentary counts. Do not change expected
counts alone or treat this note as an applied data-preparation update.

## Remaining review work

Of the 70 initially pending title pairs, the three committed family reviews
resolved 15. These two new notes resolve 16 more and explicitly leave two
examined pairs unresolved. **39 pairs therefore remain open:**

- **Two examined but unresolved cross-split pairs:** `title-013` and `title-018`.
- **37 unexamined training-only pairs:**
  `title-022`, `title-027`, `title-031`, `title-032`, `title-033`, `title-034`, `title-035`, `title-036`, `title-038`, `title-040`, `title-041`, `title-042`, `title-043`, `title-044`, `title-045`, `title-047`, `title-048`, `title-049`, `title-050`, `title-051`, `title-052`, `title-053`, `title-054`, `title-056`, `title-057`, `title-058`, `title-060`, `title-061`, `title-062`, `title-063`, `title-064`, `title-065`, `title-066`, `title-067`, `title-068`, `title-069`, `title-070`.
- No test-only candidate remains open within this title-screen snapshot.

All 21 initially pending cross-split pairs have now been examined across the
review notes; 19 have decisions and two remain unresolved. Examination is not
the same as resolving a pair or proving the broader family audit complete.
The unparsed `XACCT Technologies, Inc.SUPPORT AND MAINTENANCE AGREEMENT` title
still needs its separate inspection.

Keep the original generated reports frozen. After the remaining review work,
a versioned manifest/checker change must represent confirmed, rejected and
unresolved outcomes, validate connected families and implement any approved
holds together. Internal partitioning and training remain blocked pending
that reviewed preparation step. All 102 official test documents stay in the
primary benchmark; any sensitivity subset is additional reporting with a rule
frozen before model-result inspection.

## Appendix: exact source identities

### SM

```text
ScansourceInc_20190822_10-K_EX-10.38_11793958_EX-10.38_Distributor Agreement1
```

- Exact-text group: `cuad-exact-v1:78541613a74bc16d31309b79b24e413390c4dd9ca817c6b646bd7a9bacafc816`.
- Official split: `train`.
- Paragraph: `0`; length: 84,384 Unicode code points.
- Context SHA-256: `78d91abf7c1efc2a3a2458c5257d3c6e3fd1ec36154a3342bf253b04f5cababc`.

### SC

```text
ScansourceInc_20190822_10-K_EX-10.38_11793958_EX-10.38_Distributor Agreement2
```

- Exact-text group: `cuad-exact-v1:4cd6bb8fa83da8c48011f3bd2210f6eac647e03a0aab9d7bbfd8d14cb8a0f1b4`.
- Official split: `train`.
- Paragraph: `0`; length: 13,330 Unicode code points.
- Context SHA-256: `c08a73bd964c8116ae2b4badae2fb1faa040b362f479830e2edd73294de50399`.

### SA

```text
ScansourceInc_20190822_10-K_EX-10.39_11793959_EX-10.39_Distributor Agreement
```

- Exact-text group: `cuad-exact-v1:42e8c2a860190ef6da4616f43e5360953cd1257504f81bf173f481c44c9e358d`.
- Official split: `test`.
- Paragraph: `0`; length: 10,891 Unicode code points.
- Context SHA-256: `73c1a2a9f68cdab2e62518200def5559058e20553d14f8dff4a6b7574d516416`.

### SZ

```text
ScansourceInc_20190509_10-Q_EX-10.2_11661422_EX-10.2_Distributor Agreement
```

- Exact-text group: `cuad-exact-v1:8c9c60e6a1e419e4149e67e76c4ed130e56dedce2ec1674201764a3c30361efd`.
- Official split: `test`.
- Paragraph: `0`; length: 14,149 Unicode code points.
- Context SHA-256: `4996dfa734c77a1825fb95e4916c09bd264181e35d455e10717433d1709b2aee`.

### RE

```text
GridironBionutrientsInc_20171206_8-K_EX-10.1_10972555_EX-10.1_Endorsement Agreement
```

- Exact-text group: `cuad-exact-v1:8bb7576126d1e4f0c2a4692fb491d513da9d8895bad1d87ec29d447f3aff52ea`.
- Official split: `test`.
- Paragraph: `0`; length: 29,208 Unicode code points.
- Context SHA-256: `9bd93106c7da5a5256d055fa02684886b2e86c21f993f5461274e2b65d46b38b`.

### RA

```text
GridironBionutrientsInc_20171206_8-K_EX-10.2_10972556_EX-10.2_Endorsement Agreement
```

- Exact-text group: `cuad-exact-v1:a2ec08d844cc8641b4e731258c35f9c3dbda446c37558f4c3dabb5a8d391a96e`.
- Official split: `test`.
- Paragraph: `0`; length: 3,456 Unicode code points.
- Context SHA-256: `496339cad48b3918f42897cff2281cc85952d83f41eae5ca04e48ddf20768009`.

### RT

```text
GRIDIRONBIONUTRIENTS,INC_02_05_2020-EX-10.3-SUPPLY AGREEMENT
```

- Exact-text group: `cuad-exact-v1:101741281922f1b20675cc48bffa8fae789becb4174f7f8d671f6784f75ca1c2`.
- Official split: `train`.
- Paragraph: `0`; length: 5,713 Unicode code points.
- Context SHA-256: `afc2435e7661797197d3fbc891439f9d04dd58801e6203c0f43ac83fbdd8ebad`.

### PO

```text
SPIENERGYCO,LTD_03_09_2011-EX-99.5-OPERATIONS AND MAINTENANCE AGREEMENT
```

- Exact-text group: `cuad-exact-v1:3a7fe94345a741c0793b7d4cc9eed7b99f1d52abe855576fac8afc7099626bca`.
- Official split: `train`.
- Paragraph: `0`; length: 54,160 Unicode code points.
- Context SHA-256: `51d2e78315b1adab437d58922567571704bb637b575c9c730471d0bbc52486e9`.

### PC

```text
SPIENERGYCO,LTD_07_10_2014-EX-10-Cooperation Agreement of 50MWp Photovoltaic Grid-connected Power Generation Project in Yangqiao of~1
```

- Exact-text group: `cuad-exact-v1:ac14eb636bfe9073602f10cf4a1b6dde8ac4e37b3f0326f468b50a4fbd494930`.
- Official split: `test`.
- Paragraph: `0`; length: 2,811 Unicode code points.
- Context SHA-256: `33df36be3890377b0d92b21ad5eab450d4df8d5890341c1efd208a7bb270c034`.

### GL

```text
GpaqAcquisitionHoldingsInc_20200123_S-4A_EX-10.6_11951677_EX-10.6_License Agreement
```

- Exact-text group: `cuad-exact-v1:75251e416bb04b4fe9a30ea4b80f7c4606c67d29bb67dd705a65a5b44b50b57c`.
- Official split: `train`.
- Paragraph: `0`; length: 45,234 Unicode code points.
- Context SHA-256: `800df8b986eb8c9ed75feab8e09dec3371698bfc3ff9697748a9d19f8dcb1ed6`.

### GS

```text
GpaqAcquisitionHoldingsInc_20200123_S-4A_EX-10.8_11951679_EX-10.8_Service Agreement
```

- Exact-text group: `cuad-exact-v1:2f6d12b1b89ba2aafba57934885509c281fd322944dfe1e6bf88549fd8468f7d`.
- Official split: `test`.
- Paragraph: `0`; length: 55,075 Unicode code points.
- Context SHA-256: `9d8942925e1900a35876bf5398d788b28095ea16e207899b0e7d60afb9e44857`.

### EE

```text
EcoScienceSolutionsInc_20171117_8-K_EX-10.1_10956472_EX-10.1_Endorsement Agreement
```

- Exact-text group: `cuad-exact-v1:2d7de823692d398321e73ba2e205e667ef0028b219ca6a519401501d8a85f04f`.
- Official split: `train`.
- Paragraph: `0`; length: 18,104 Unicode code points.
- Context SHA-256: `4294c59e488ca8db726621f1a024bfe8213ae06fa6c88226b6bcd20b23cb0ec8`.

### ES

```text
EcoScienceSolutionsInc_20180406_8-K_EX-10.1_11135398_EX-10.1_Sponsorship Agreement
```

- Exact-text group: `cuad-exact-v1:df47e7bb4dfd1d895472a6a414eae6024dc174c2000ff469c0d1ac61d6c86708`.
- Official split: `test`.
- Paragraph: `0`; length: 8,052 Unicode code points.
- Context SHA-256: `a2bbc78780c5eee0b15768c43c3dd8b15181d714d98273f4a6c4f2478e76a02d`.
