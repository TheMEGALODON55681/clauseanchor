# CUAD remaining training-only family review

Reviewed: 20 October 2026 (India time).

**Status:** assistant-assisted source-text review prepared for Tanishq.
This note examines all 37 training-only pairs left unexamined by the
[previous batch](CUAD_RemainingCrossSplitReview.md): **23 confirmed, 10 rejected,
four unresolved**. It covers 49 distinct source records, all in official train.
The [XACCT note](CUAD_XACCTTitleReview.md) separately documents manual inspection
of the one unparsed title.

These are documentary decisions. The family manifest, validator, title parser,
source text and annotations are unchanged. No exclusions, question holds,
internal partitions or training runs are implemented by these notes.

## Scope and reproducibility

- Repository checked: `main` at `c124fdcc0076ae48cc9acb0ac00773feea9c5763`.
- Full CUAD source SHA-256: `ed0b77d85bdf4014d7495800e8e4a70565b48ee6f8a2e5dca9cf8655dbf10eae`.
- Official archive: `The-Atticus-Project/cuad`, revision `67faa0e6023b04fcaae6cc09497ab00e5d63a2a2`; archive SHA-256 `f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a`.
- Title-screen version: `1.0.0`; canonical report SHA-256: `c9a962bba49d410bc12ddc90dabf5eeeb2458a6abf38face809968acb609c312`.
- Manifest version: `1.0.0`; canonical SHA-256: `7576938a012b45b30121887b6db7d9d9dd77e0886256a554c70085f3a8fc8dea`.
- Canonical hashes use sorted keys, compact JSON, UTF-8 and `ensure_ascii=False`, as in `check_cuad_families.py`.
- Attribution and source paths: [CUAD README](../../data/raw/cuad/README.md).

The existing loader reverified source/archive provenance, answer spans and
official membership. Candidate identities were checked against the frozen
report; every evidence range below was checked against the untouched source.
Review used targeted identity, party, date, purpose, attachment, amendment,
site and personnel passages plus the complete-context searches listed below.
It was not a clause-by-clause review of all 49 long records, annotation
adjudication, or an exhaustive search for every possible corpus relationship.

Ranges address `paragraphs[0].context`: zero-based Unicode code points, end
exclusive. T01–T49 are local aliases; the appendix gives canonical identities.
All source spellings, missing fields, redactions and conflicting details stay
as printed. Grouping never concatenates text or transfers an answer label.

**Confirmed** means `confirmed_related_for_split_grouping`, including connected
parent/attachment/amendment records. **Rejected** means the particular screened
family edge is unsupported by the reviewed evidence and the records identify
distinct agreements; reopen on stronger linkage evidence. **Unresolved** means
examined but neither confirmed nor cleared for independent partitioning.
These three documentary outcomes are not a new manifest schema.

## Candidate ledger

All pairs below are train / train. A pair is counted once even when its two
records are already connected transitively through another confirmed edge.

| Candidate | Records | Documentary decision |
|---|---|---|
| `title-022` | T01 / T02 | Confirmed |
| `title-027` | T04 / T05 | Confirmed |
| `title-031` | T06 / T07 | Confirmed |
| `title-032` | T06 / T08 | Confirmed |
| `title-033` | T06 / T09 | Confirmed |
| `title-034` | T10 / T11 | Confirmed |
| `title-035` | T02 / T03 | Confirmed |
| `title-036` | T12 / T13 | Confirmed |
| `title-038` | T14 / T15 | Confirmed |
| `title-040` | T16 / T17 | Confirmed |
| `title-041` | T18 / T19 | Confirmed |
| `title-042` | T07 / T08 | Confirmed |
| `title-043` | T07 / T09 | Confirmed |
| `title-044` | T20 / T21 | Confirmed |
| `title-045` | T08 / T09 | Confirmed |
| `title-047` | T22 / T23 | Confirmed |
| `title-048` | T22 / T24 | Confirmed |
| `title-049` | T22 / T25 | Confirmed |
| `title-050` | T23 / T24 | Confirmed |
| `title-051` | T23 / T25 | Confirmed |
| `title-052` | T24 / T25 | Confirmed |
| `title-053` | T27 / T28 | Confirmed |
| `title-054` | T29 / T30 | Confirmed |
| `title-056` | T31 / T32 | Rejected |
| `title-057` | T33 / T34 | Rejected |
| `title-058` | T35 / T34 | Rejected |
| `title-060` | T36 / T37 | Unresolved |
| `title-061` | T38 / T39 | Unresolved |
| `title-062` | T40 / T41 | Unresolved |
| `title-063` | T42 / T43 | Rejected |
| `title-064` | T44 / T45 | Unresolved |
| `title-065` | T46 / T47 | Rejected |
| `title-066` | T22 / T26 | Rejected |
| `title-067` | T23 / T26 | Rejected |
| `title-068` | T26 / T24 | Rejected |
| `title-069` | T26 / T25 | Rejected |
| `title-070` | T48 / T49 | Rejected |

## NETGEAR: extend the existing Ingram Micro family

**Confirm `title-022` and `title-035`.** T02 is the NETGEAR / Ingram Micro
Distributor Agreement, number N115, effective March 1, 1996. T01 explicitly
amends that agreement effective October 1, 1996. The complete T01 context is
also the exact suffix of T03 at `[3546, 8113)`. T01 and T03 are already joined
by the original lexical review; these two new edges add T02 to that family.
Do not count this as a second independent NETGEAR family or concatenate records.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent number, date and parties | T02 | `[280, 1170)` |
| Amendment parties, date and explicit parent reference | T01 | `[0, 430)` |
| Exact T01 context contained in T03 | T03 | `[3546, 8113)` |

## Kubient: master services agreement and Exhibit B

**Confirm `title-027`.** T05 is the February 5, 2020 master services agreement
between Kubient and The Associated Press. T04 identifies itself as Exhibit B,
dated March 26, 2020, and expressly incorporates itself into that dated master
agreement. Its separate date is an attachment date, not an identity conflict.

| Source evidence | Record | Exact range |
|---|---|---|
| Master agreement identity, date and parties | T05 | `[0, 465)` |
| Exhibit B date, parties and incorporation into the master | T04 | `[0, 325)` |

## Glu Mobile: agreement 12965 and three amendments

**Confirm `title-031`, `title-032`, `title-033`, `title-042`, `title-043` and
`title-045`.** T06 is Wireless Content License Agreement 12965 dated December
16, 2004; T09, T08 and T07 are amendments 1, 2 and 3. Each amendment identifies
the parent by its number and date. T09 records the Fox assignment to Fox Mobile
Entertainment and Sorrent's change of name to Glu Mobile. These passages explain
the party-name differences without silently normalizing source names. All four
records form one connected family; amendment-to-amendment pairs connect through
the parent and explicit amendment history.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent number, date and original parties | T06 | `[0, 600)` |
| Amendment 1, Fox assignment and licensee name change | T09 | `[0, 1040)` |
| Amendment 2 parent reference and former licensee name | T08 | `[0, 455)` |
| Amendment 3 and prior amendment dates | T07 | `[0, 422)` |

## HealthGate: hosting agreement and escrow schedule

**Confirm `title-034`.** T10 identifies HealthGate, Blackwell and Munksgaard,
defines the Escrow Agreement by reference to the Fourth Schedule, and requires
it in section 29. T11 starts with Schedule 3 project-manager material, then
contains Schedule 4 escrow instructions, the HealthGate Electronic Journal
Proprietary Software name and the instruction that HealthGate and Blackwell
sign the escrow agreement. This is attachment evidence, not merely a shared
hosting-related title. Do not represent all of T11 as a single executed escrow
instrument: its context includes preliminary schedule material and a form.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent identity and publisher parties | T10 | `[0, 750)` |
| Escrow defined by the Fourth Schedule | T10 | `[3718, 4036)` |
| Section 29 requirement to maintain the escrow agreement | T10 | `[52196, 52385)` |
| Schedules, escrow package name and intended signers | T11 | `[1426, 2450)` |

## Old API: agency agreement and certificate form

**Confirm `title-036` for split grouping, with source discrepancies preserved.**
T12 is the Tribute Pharmaceuticals Canada agency agreement dated May 21, 2015.
Its Schedule A requires an agent / U.S. affiliate certificate in the form of
Exhibit I. T13 is expressly Exhibit I to Schedule A, the Agents' Certificate,
and concerns the same U.S. offering process in the shared source exhibit.
However, T13 prints May 22, 2015 for its referenced agreements, omits "Canada"
from the corporation name, and leaves agent and affiliate names blank. The
attachment reference and matching certificate role support grouping; they do
not authorize changing the date, resolving the legal entity spelling, or
treating this form as an executed certificate.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent date, corporation and agents | T12 | `[0, 760)` |
| Schedule A requires the Exhibit I certificate | T12 | `[94945, 95404)` |
| Exhibit I identity, differing date/name and blanks | T13 | `[0, 650)` |

## Playboy: content agreement and supplier form

**Confirm `title-038`.** T15 is the eFashion Solutions / Playboy.com agreement
effective January 15, 2008. It requires supplier/subcontractor agreements in
the form attached as Exhibit 8. T14 is that numbered supplier/subcontractor
form and identifies the Playboy properties. Supplier and purchaser fields are
blank; their values must not be inferred or copied from the parent annotations.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent identity, date and parties | T15 | `[0, 975)` |
| Operative requirement to use the Exhibit 8 form | T15 | `[31720, 32244)` |
| Exhibit 8 heading and blank supplier/purchaser fields | T14 | `[0, 650)` |

## Pelican: software development agreement and Appendix A

**Confirm `title-040`.** T17 names DOT COM LLC / Seattle Software Developers
and Pelican Delivers, dates the agreement December 3, 2018, and incorporates
the Phase 1 statement of work in Appendix A. T16 identifies itself as that
Appendix A statement of work for the Pelican Delivers application project.
Preserve the source's printed "OBA" wording; this note does not correct it.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent identity, date and parties | T17 | `[0, 465)` |
| Phase 1 deliverables and Appendix A incorporation | T17 | `[720, 1405)` |
| Pelican project and Appendix A attachment statement | T16 | `[0, 1020)` |

## NEON: distributor agreement and first amendment

**Confirm `title-041`.** T19 is the January 1, 1996 agreement between
Peregrine/Bridge Transfer and NEON Systems. T18 expressly identifies that
parent in its January 1, 1999 first amendment. T18 also contains leading
Exhibit C / D form captions; retain those in the original record and offsets.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent operative date and parties | T19 | `[1913, 2155)` |
| Leading exhibit captions and explicit amendment identity | T18 | `[0, 1090)` |

## Azul: maintenance agreement and amendment 1

**Confirm `title-044`, retaining the printed identifier difference.** T20 is
the Azul / ATR Global Maintenance Agreement of March 9, 2015, headed
`DS/CS-3957/14 issue 7`. T21 expressly amends a Global Maintenance Agreement
of the same date and issue between the same parties but prints
`DS/C-3957/14 Issue 7`. T21 is dated January 6, 2016. The direct amendment
reference, date and parties support grouping despite that discrepancy; no
source identifier is corrected and no annotation is transferred.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent identifier, issue, parties and date | T20 | `[326, 521)` |
| Amendment title, printed parent identifier, date and parties | T21 | `[0, 320)` |
| Amendment date | T21 | `[701, 819)` |

## BellRing: manufacturing family and separate Fonterra supply

**Confirm `title-047` through `title-052`.** T22 is the July 1, 2017
Stremicks Heritage / Premier manufacturing agreement. T25, T23 and T24 are
amendments 1, 2 and 3, each naming that parent. Join these four records.

**Reject `title-066` through `title-069`.** T26 instead identifies a master
supply agreement dated October 31, 2019 between Premier Nutrition Company,
LLC and Fonterra (USA), concerning raw ingredients. It permits delivery to
PNC or third-party manufacturers; that generic route does not identify the
Heritage agreement. The manufacturing records contain no literal "Fonterra";
T26 contains no "Heritage", "Stremick" or "Jasper". Shared Premier business
and a possible supply-chain connection alone do not establish the screened
agreement-family edges. Reopen if a specific incorporated contract, project
dependency or other source linkage is found.

| Source evidence | Record | Exact range |
|---|---|---|
| Manufacturing parent parties and date | T22 | `[215, 760)` |
| Amendment 1 parent reference | T25 | `[0, 540)` |
| Amendment 2 parent reference | T23 | `[0, 540)` |
| Amendment 3 parent reference | T24 | `[0, 550)` |
| Fonterra parties, date and raw-material purpose | T26 | `[195, 1130)` |
| Delivery provision for PNC or third-party manufacturers | T26 | `[1300, 1920)` |

## BioAmber: development agreement and first amendment

**Confirm `title-053`.** T28 is the Cargill / BioAmber development agreement
of April 15, 2010. T27 expressly names that agreement and those parties in its
first amendment, effective July 5, 2011 upon signature. Preserve redactions
and each record's own annotations.

| Source evidence | Record | Exact range |
|---|---|---|
| Parent identity, date and parties | T28 | `[130, 660)` |
| First amendment and parent identity | T27 | `[0, 575)` |

## PF Hospitality: Pizza Fusion franchise and Appendix C

**Confirm `title-054`.** T30 is the Pizza Fusion franchise form; its contents
and operative confidentiality/noncompetition provisions require the Appendix
C form. T29 identifies itself as Appendix C, the sample nondisclosure and
noncompetition agreement between the franchisee and its personnel. It retains
blank names and dates. The dataset issuer title is not substituted for the
actual Pizza Fusion parties, and no hypothetical franchisee is invented.

| Source evidence | Record | Exact range |
|---|---|---|
| Appendix C listed and Pizza Fusion parent identity | T30 | `[1207, 1700)` |
| Operative confidentiality requirement for Appendix C | T30 | `[104449, 104819)` |
| Section 17.3 requires the Appendix C covenant | T30 | `[136400, 136850)` |
| Appendix C heading, blanks and franchise relationship | T29 | `[0, 1170)` |

## Distinct agreements under repeated issuer titles

**Reject the following six candidates.** These decisions concern the specific
screened agreement-family edges. They do not assert absence of all corporate,
commercial or template relationships.

| Candidate | Records | Source-grounded distinction |
|---|---|---|
| `title-056` | T31 / T32 | Newegg / Allied sponsorship of the HyperX arena in 2019 versus WPT / Zynga poker-content licensing in 2018. |
| `title-057` | T33 / T34 | SINA domain-license termination form versus the Baidu Internet Channel Cooperation Agreement. |
| `title-058` | T35 / T34 | SINA domain/content license, including SINA-domain Exhibit A, versus a separately identified Baidu-domain channel agreement. |
| `title-063` | T42 / T43 | iShip / Mail Boxes Etc. shipping services and co-branding versus Intuit / Stamps.com sponsorship on Intuit properties. |
| `title-065` | T46 / T47 | Tarek El Moussa / T&B training development in 2019 versus Robbie Fowler / Celebrity Speakers endorsement of Property Academy under a 2012 primary agreement. |
| `title-070` | T48 / T49 | BookingEntertainment venue-contract promotion versus Anthemic's specifically dated FLOODfest Chicago sponsorship. |

For Leju, T34 does mention "SINA Leju" as Party B's existing business, and
Beijing Yisheng Leju appears in both T34 and T35. Those connections are not
ignored: the reviewed operative rights concern different provider domains
and separately identified agreements. T35's SINA license and T33's attached
termination remain in their already recorded family (which has a third member
in manifest 1.0.0). Rejecting a Baidu edge does not dissolve that family.
T34's SINA-brand recital is not an incorporation of T35 or T33.

The complete-context searches below supplement the positive identity and
purpose evidence. A zero literal count is not proof that no relationship can
exist under a different spelling, omitted schedule or external record.

| Source evidence | Record | Exact range |
|---|---|---|
| Newegg / Allied parties and HyperX arena purpose | T31 | `[0, 980)` |
| WPT / Zynga parties and poker-content purpose | T32 | `[0, 1850)` |
| SINA termination and May 8, 2008 parent reference | T33 | `[0, 610)` |
| Baidu agreement number and parties | T34 | `[0, 1060)` |
| SINA Leju recital acknowledged in review | T34 | `[1480, 1900)` |
| Baidu second-tier domains in operative authorization | T34 | `[9690, 10130)` |
| SINA domain-license parties and transaction reference | T35 | `[0, 1030)` |
| Exhibit A lists the licensed SINA domains | T35 | `[46539, 46677)` |
| iShip / MBE agreement identity and service purpose | T42 | `[0, 1400)` |
| Intuit / Stamps.com agreement identity and sites | T43 | `[0, 1350)` |
| T&B / Tarek El Moussa agreement and date | T46 | `[0, 560)` |
| Robbie Fowler, Property Academy and separate primary agreement | T47 | `[0, 965)` |
| BookingEntertainment / VNUE identity and purpose | T48 | `[0, 850)` |
| Thirty-venue engagement | T48 | `[2141, 2276)` |
| Anthemic / VNUE event and event dates | T49 | `[0, 650)` |

## Four training-only pairs remain unresolved

These pairs were examined, not cleared. None is added as a confirmed edge and
none is marked unrelated. All eight records remain a review blocker before
internal split assignment. A conservative hold would need an explicit policy
and implementation; this note does not apply one.

| Candidate | Records | Evidence and remaining question |
|---|---|---|
| `title-060` | T36 / T37 | T36 concerns Bunker One / Vertex output from a Marrero production facility in 2020. T37 concerns Magellan (formerly Marrero Terminal) / Omega operation of a rail facility at 5000 River Road, Marrero, in 2010. The city matches, but the reviewed text does not establish whether these are connected assets or a successor agreement chain. Confirm the asset/corporate provenance or explicitly choose a conservative hold. |
| `title-061` | T38 / T39 | Reynolds / Pactiv supply in 2019 and the RGHI / RCP IPO transition-services package in 2020 have a possible corporate-separation connection. T39 names Pactiv benefit plans. Neither reviewed passage ties T38 into the transition package. Establish whether they share a specific transaction family or explicitly hold both. |
| `title-062` | T40 / T41 | Both start December 1, 2015, share Bosch International and concern Light Sheets: West Coast Customs promotion versus Bosch Technologies distribution rights. This could be a coordinated product transaction, but no direct incorporation or dependency was found in the reviewed passages. Establish the linkage or explicitly hold both. |
| `title-064` | T44 / T45 | The Kiromic / MoliPharma joint venture includes Gianluca Rotino in a bracketed steering-committee example. T45 separately retains Rotino for general consulting and business-development services. The example does not prove appointment or that the consultancy services are for this joint venture. Establish the personnel/project linkage or explicitly hold both. |

No conclusion about actual facility ownership, corporate succession, a
consultant's appointment, or legal effectiveness is inferred beyond the
printed source. The source checks here are insufficient to settle those
four relationships.

| Source evidence | Record | Exact range |
|---|---|---|
| JSMA parties, commencement date and Marrero output | T36 | `[250, 1340)` |
| O&M parties, former name and Marrero rail-site address | T37 | `[1750, 2800)` |
| Reynolds / Pactiv supply date, parties and purpose | T38 | `[0, 1030)` |
| TSA parties, blank agreement date and IPO separation | T39 | `[0, 1500)` |
| Pactiv plans in the transition-services schedule | T39 | `[83550, 84320)` |
| Sponsorship parties, date and Light Sheets purpose | T40 | `[0, 850)` |
| Alliance date, parties, product and distribution rights | T41 | `[0, 1790)` |
| Kiromic / MoliPharma joint-venture parties | T44 | `[180, 680)` |
| Rotino in an explicitly bracketed committee example | T44 | `[5930, 6380)` |
| Rotino consultancy identity, date and general scope | T45 | `[130, 760)` |
| Exhibit A business-development consulting services | T45 | `[17200, 17790)` |

## Complete-context literal checks

Case-insensitive literal searches over the full untouched context:

| Records | Literals | Matches |
|---|---|---|
| T22, T23, T24, T25 | `Fonterra` | 0 each, in every listed record |
| T26 | `Heritage`, `Stremick`, `Jasper` | 0 each, in every listed record |
| T31 | `Zynga`, `WPT` | 0 each, in every listed record |
| T32 | `Newegg`, `HyperX` | 0 each, in every listed record |
| T33, T35 | `Baidu` | 0 each, in every listed record |
| T35 | `baidu.com`, `leju.com` | 0 each, in every listed record |
| T36 | `Magellan`, `Omega`, `5000`, `River Road` | 0 each, in every listed record |
| T37 | `Bunker`, `Vertex` | 0 each, in every listed record |
| T38 | `Transition`, `separation`, `initial public` | 0 each, in every listed record |
| T39 | `Master Supply`, `Supply Agreement` | 0 each, in every listed record |
| T40 | `Bosch Technologies`, `Strategic Alliance` | 0 each, in every listed record |
| T41 | `West Coast`, `RMF` | 0 each, in every listed record |
| T42 | `Intuit`, `Quicken`, `QuickBooks` | 0 each, in every listed record |
| T43 | `iShip`, `Mail Boxes` | 0 each, in every listed record |
| T45 | `Moli`, `joint venture` | 0 each, in every listed record |
| T46 | `Fowler`, `Tigrent`, `Property Academy` | 0 each, in every listed record |
| T47 | `Moussa`, `T&B`, `Tarek` | 0 each, in every listed record |
| T48 | `Anthemic`, `FLOOD`, `Virgin` | 0 each, in every listed record |
| T49 | `BookingEntertainment` | 0 each, in every listed record |

For T43, whole-word case-insensitive `\bMBE\b` also has zero matches. A raw
substring search for `MBE` yields eight matches inside "number"; those are not
references to Mail Boxes Etc. Positive connections (Leju's SINA recital,
Reynolds' Pactiv plans and Kiromic's Rotino example) are recorded above rather
than discarded because the other agreement title is absent.

## Cumulative accounting and remaining gate

This completes examination of the frozen title screen's **70 initially pending
pairs**. It does not certify exhaustive corpus-wide family discovery.

| Boundary | Confirmed | Rejected | Unresolved | Examined |
|---|---:|---:|---:|---:|
| Cross official train/test | 14 | 5 | 2 | 21 |
| Training only | 31 | 10 | 4 | 45 |
| Test only | 3 | 1 | 0 | 4 |
| Total | 48 | 16 | 6 | 70 |

The frozen report also has five pairs already covered by manifest families:
75 candidate pairs in all. The original six lexical decisions remain recorded
in manifest 1.0.0; these are a separate screen, not six more title candidates.
The regenerated title report still prints its original 70 pending statuses.
This note records review outcomes without rewriting that pinned snapshot.

| Quantity | Manifest 1.0.0 only | Prior notes cumulatively | Including this note |
|---|---:|---:|---:|
| Prospective training documents | 406 | 395 | 395 |
| Prospective training exact-text groups | 405 | 394 | 394 |
| Prospective internal family units | 401 | 390 | 374 |
| Prospective known-overlap-excluded test sensitivity documents | 100 | 93 | 93 |

The final column uses only confirmed edges from the original manifest and all
review notes. These 23 training-only edges reduce the number of training family
units by 16 through connected components. They do not add cross-split exclusions.
Official source membership remains **408 train / 102 test**, with all 102 test
records retained for primary reporting. The 93-record sensitivity figure is
prospective and its eventual rule must be frozen before model results.

**395 is not a cleared training pool.** Six pairs remain unresolved:
`title-013` (GPAQ), `title-018` (EcoScience), `title-060` (Vertex), `title-061`
(Reynolds), `title-062` (XLI), and `title-064` (Kiromic). The two cross-split
cases are explained in the [previous review](CUAD_RemainingCrossSplitReview.md).
No extra unresolved-case hold has been subtracted from these figures.
The AduroBioTech duplicate-label conflict also remains unresolved; no questions
have been adjudicated or removed.

Before internal splits: settle these six relationships or document and implement
an explicit conservative handling rule; resolve the duplicate-label handling;
then extend the manifest and validator to consume the reviewed title decisions
and verify the resulting counts and gates. A successful existing checker still
reports only the original manifest's figures and `ready_for_internal_splits`
remains false. No current note authorizes skipping those gates.

## Source identity appendix

Each alias is one source document and one exact-text group with one paragraph.
Group IDs hash the ordered context list; context hashes below hash the individual
UTF-8 context. They are different identities and are not interchangeable.

### T01

```text
NETGEAR,INC_04_21_2003-EX-10.16- AMENDMENT #2 TO THE DISTRIBUTION AGREEMENT
```

- Exact-text group: `cuad-exact-v1:04993e9fb171451eb13473b9cdf36d9ec5d6e0f3f6c39e193ec0d8db3bfc34a0`.
- Official split: `train`; paragraph: `0`; length: 4,567 Unicode code points.
- Context SHA-256: `40b9a08eaf9a9a4cb8062d44af4289e0cb7732b2fe464b083505594978f1b776`.

### T02

```text
NETGEAR,INC_04_21_2003-EX-10.16-DISTRIBUTOR AGREEMENT
```

- Exact-text group: `cuad-exact-v1:451dac44b1c3af9e17238377f5297ed1121605651eef739138c04aa31b8c7bc7`.
- Official split: `train`; paragraph: `0`; length: 41,501 Unicode code points.
- Context SHA-256: `1b4a0744754138176a7a3081a9c89a859248df2013a56f6ef13eeccbc264c9a1`.

### T03

```text
NETGEAR,INC_04_21_2003-EX-10.16-AMENDMENT TO THE DISTRIBUTOR AGREEMENT BETWEEN INGRAM MICRO AND NETGEAR
```

- Exact-text group: `cuad-exact-v1:aacfd33dfc6f28e8a4dd6cd384df7ab9ad8f865545d5c18c39c6ae94af5d2f63`.
- Official split: `train`; paragraph: `0`; length: 8,113 Unicode code points.
- Context SHA-256: `a26d0a46ae672963f96e729745f458b9684cbee0ac2b723045a6fe227cbd1fd7`.

### T04

```text
KUBIENT,INC_07_02_2020-EX-10.14-MASTER SERVICES AGREEMENT_Part2
```

- Exact-text group: `cuad-exact-v1:2f14d55171e68b8bb464513adbadcbb44243fe6b7729884f75174bee8c668494`.
- Official split: `train`; paragraph: `0`; length: 7,600 Unicode code points.
- Context SHA-256: `1145d34d95146782b28cc3959f1cf8a5b57d4745b59589c0ca95afaae636cd42`.

### T05

```text
KUBIENT,INC_07_02_2020-EX-10.14-MASTER SERVICES AGREEMENT_Part1
```

- Exact-text group: `cuad-exact-v1:812e9c2c1091369a44917781ace8283559d1bc26eac545cc4e863337ba6818c4`.
- Official split: `train`; paragraph: `0`; length: 26,108 Unicode code points.
- Context SHA-256: `6fedeb5bf615d4fb66911bb8e92299535ee320b2f913aa3acd8dabf6c90df986`.

### T06

```text
GluMobileInc_20070319_S-1A_EX-10.09_436630_EX-10.09_Content License Agreement1
```

- Exact-text group: `cuad-exact-v1:3ecde3fb9f9228b8215b9ea765affb120cf07293bc51aea46642f357f568c6b6`.
- Official split: `train`; paragraph: `0`; length: 112,794 Unicode code points.
- Context SHA-256: `ed6d0e01ab253bf488839d449bc4a98ad1c1d99b0f098c7d09e86b040b24a2ab`.

### T07

```text
GluMobileInc_20070319_S-1A_EX-10.09_436630_EX-10.09_Content License Agreement4
```

- Exact-text group: `cuad-exact-v1:68c9bb4c74f857c02d261ac9aac2a8ba7574ef0a8b3513f05128bac5b90e3877`.
- Official split: `train`; paragraph: `0`; length: 1,902 Unicode code points.
- Context SHA-256: `b5dc6d1ea4c6ac711270a5b019707577e67579deb69b5bc6f6507b33a096987c`.

### T08

```text
GluMobileInc_20070319_S-1A_EX-10.09_436630_EX-10.09_Content License Agreement3
```

- Exact-text group: `cuad-exact-v1:80c37884ed9d06f3478ca1e48b13a9ed04e71c3693a332c7d82b96b94e1043b5`.
- Official split: `train`; paragraph: `0`; length: 3,422 Unicode code points.
- Context SHA-256: `94668aaf575826c5eaf742f573598bef6e34719f96d475c69c157a47d300f990`.

### T09

```text
GluMobileInc_20070319_S-1A_EX-10.09_436630_EX-10.09_Content License Agreement2
```

- Exact-text group: `cuad-exact-v1:c8b46a8d5c3201f047d991112b7e9a66726fa990e722ba4150a9b70ccf6e8756`.
- Official split: `train`; paragraph: `0`; length: 11,954 Unicode code points.
- Context SHA-256: `ab313de5385c0998e3242d39c567f21c4297e4f1c9eafbda33998f330deda36c`.

### T10

```text
HEALTHGATEDATACORP_11_24_1999-EX-10.1-HOSTING AND MANAGEMENT AGREEMENT (1)
```

- Exact-text group: `cuad-exact-v1:44d3129af6e1879917728169fec6fe598cc1cf8bec5d0959ba067870fad3eadc`.
- Official split: `train`; paragraph: `0`; length: 148,691 Unicode code points.
- Context SHA-256: `8180c54f224250c10362b5d159032157a5d30a1821b0897f392c971a8764925a`.

### T11

```text
HEALTHGATEDATACORP_11_24_1999-EX-10.1-HOSTING AND MANAGEMENT AGREEMENT - Escrow Agreement
```

- Exact-text group: `cuad-exact-v1:525904f1cdf56b4a2ff6df6c296ae1584fc7981cd4da4dab7e831c63f6f3fc90`.
- Official split: `train`; paragraph: `0`; length: 35,612 Unicode code points.
- Context SHA-256: `a882b126b747c9f0fbdd79a2d197e132d6b06ca49335e3f02291557d324c10fd`.

### T12

```text
OLDAPIWIND-DOWNLTD_01_08_2016-EX-1.3-AGENCY AGREEMENT1
```

- Exact-text group: `cuad-exact-v1:4c93bf1e0e0c6de9d48c21cf2e36504a44b4447a6b5c7fccca1385ea33cc8848`.
- Official split: `train`; paragraph: `0`; length: 98,009 Unicode code points.
- Context SHA-256: `96f162f2cb658cc49c87f9f1209c5bea1a72fe97d4d60d35c0d06012f2342a66`.

### T13

```text
OLDAPIWIND-DOWNLTD_01_08_2016-EX-1.3-AGENCY AGREEMENT2
```

- Exact-text group: `cuad-exact-v1:b7959d4c9ab61154735ddfee2ef6a88815f3b96d6eba168fe68915c1b67bd875`.
- Official split: `train`; paragraph: `0`; length: 3,886 Unicode code points.
- Context SHA-256: `67c067411b536fb05eb5e9c3cc55f7dca50cc24c49fd0ec11f93b11cc7d7de01`.

### T14

```text
PlayboyEnterprisesInc_20090220_10-QA_EX-10.2_4091580_EX-10.2_Content License Agreement_ Marketing Agreement_ Sales-Purchase Agreement2
```

- Exact-text group: `cuad-exact-v1:536e97693c306864899c900066552dbe43bbdab1ba2f2d082c9a67228362d2dd`.
- Official split: `train`; paragraph: `0`; length: 3,558 Unicode code points.
- Context SHA-256: `ccf10e1bed833697efe7893f85d96df2676b18d49671b9bf2465de2388862247`.

### T15

```text
PlayboyEnterprisesInc_20090220_10-QA_EX-10.2_4091580_EX-10.2_Content License Agreement_ Marketing Agreement_ Sales-Purchase Agreement1
```

- Exact-text group: `cuad-exact-v1:68445e22c58bf0cf9c1b80b3df3f0712782b13735b3729e388847122db9396fc`.
- Official split: `train`; paragraph: `0`; length: 117,118 Unicode code points.
- Context SHA-256: `cb53054735cbbd216f4c96ff4ddcb0d36713de751760ee0b97e33c2c76555d21`.

### T16

```text
PelicanDeliversInc_20200211_S-1_EX-10.3_11975895_EX-10.3_Development Agreement1
```

- Exact-text group: `cuad-exact-v1:648a6df5bdf3449e62bc1d27007a43d16591323fa36c5a755ad5999c4ea10fc9`.
- Official split: `train`; paragraph: `0`; length: 16,590 Unicode code points.
- Context SHA-256: `21e9032b30a1e12d7f39af1f855c90633884e5d9026b1c2b3e84110fcc4bf017`.

### T17

```text
PelicanDeliversInc_20200211_S-1_EX-10.3_11975895_EX-10.3_Development Agreement2
```

- Exact-text group: `cuad-exact-v1:6aad1e1e571af0c973f060278073e0bc5b78df20cc419932d87389eeceb45f78`.
- Official split: `train`; paragraph: `0`; length: 32,093 Unicode code points.
- Context SHA-256: `277cb9d06eed8f04cb35b2aed3b4eb280783165422d41cd083a27a884737630d`.

### T18

```text
NEONSYSTEMSINC_03_01_1999-EX-10.5-DISTRIBUTOR AGREEMENT_Amendment
```

- Exact-text group: `cuad-exact-v1:65d40347454dc227e2e61ec4b3f1cc69ceda226c14057ebec260c1000e41f62a`.
- Official split: `train`; paragraph: `0`; length: 21,994 Unicode code points.
- Context SHA-256: `9efa34e33b135d9bdc6e0fa949b22953b5a1675efa39c7222cf7d2ddc2251ebf`.

### T19

```text
NEONSYSTEMSINC_03_01_1999-EX-10.5-DISTRIBUTOR AGREEMENT_New
```

- Exact-text group: `cuad-exact-v1:eaa9c158b838c90db91853fc6d4ca49060f2a5275bc5a4139798018234bd1b56`.
- Official split: `train`; paragraph: `0`; length: 61,463 Unicode code points.
- Context SHA-256: `acf1fbe6de84c75f0410f1f51cb94315d533cc5c97ffeb364aa99e00fc8b3958`.

### T20

```text
AzulSa_20170303_F-1A_EX-10.3_9943903_EX-10.3_Maintenance Agreement1
```

- Exact-text group: `cuad-exact-v1:804285fe8619e819c5affaa8c8b0f7b204a8de6b7471e8f6f634e9093d9552f0`.
- Official split: `train`; paragraph: `0`; length: 233,248 Unicode code points.
- Context SHA-256: `ae387a12fe0b3198004076f49e1991600b5993c656a4de3866786d3f7ec2a1df`.

### T21

```text
AzulSa_20170303_F-1A_EX-10.3_9943903_EX-10.3_Maintenance Agreement2
```

- Exact-text group: `cuad-exact-v1:efc8cf212b36ec33c5c6c33561b81b34116baf669acd47c572acd0bb84132997`.
- Official split: `train`; paragraph: `0`; length: 16,870 Unicode code points.
- Context SHA-256: `2d98d5344e92fe02c4726bc483ff9f00facbfa8161d3877cd522d8f6ac4ac2a1`.

### T22

```text
BellringBrandsInc_20190920_S-1_EX-10.12_11817081_EX-10.12_Manufacturing Agreement1
```

- Exact-text group: `cuad-exact-v1:87dc2e1cd9b5243d4287c88beda7bf865a7ce5d75316daab6a0514cb5d080644`.
- Official split: `train`; paragraph: `0`; length: 42,473 Unicode code points.
- Context SHA-256: `282c8f55337dd7866bdbad178bcefe679017c2be4e1ae80a37fef98acf995e44`.

### T23

```text
BellringBrandsInc_20190920_S-1_EX-10.12_11817081_EX-10.12_Manufacturing Agreement3
```

- Exact-text group: `cuad-exact-v1:8baf03ddd067f02df5dd84766e5f27a4764010fa12c02e65a7dbf09a7029112e`.
- Official split: `train`; paragraph: `0`; length: 8,024 Unicode code points.
- Context SHA-256: `063435deaed983bff69035a1db93843b925146affc740e05cc2e99778995e589`.

### T24

```text
BellringBrandsInc_20190920_S-1_EX-10.12_11817081_EX-10.12_Manufacturing Agreement4
```

- Exact-text group: `cuad-exact-v1:953a47e2d6df5c8c6bd62fbd32d0068ea5ba354816a9de113bd705b6a906fc91`.
- Official split: `train`; paragraph: `0`; length: 1,742 Unicode code points.
- Context SHA-256: `2f5c0ad9164da9c7acb685fe4b1a2a5e0c141ca97ca8daacd3dfd25832e2ecf4`.

### T25

```text
BellringBrandsInc_20190920_S-1_EX-10.12_11817081_EX-10.12_Manufacturing Agreement2
```

- Exact-text group: `cuad-exact-v1:9709a8c9366069a76260c3e8795618c9f19205d88425b7419e5b090b7b8ffe51`.
- Official split: `train`; paragraph: `0`; length: 2,274 Unicode code points.
- Context SHA-256: `f7c0f6916366509e9e27a7e89ff4658bf08533469d01b633a9ecb903eb856e0b`.

### T26

```text
BELLRINGBRANDS,INC_02_07_2020-EX-10.18-MASTER SUPPLY AGREEMENT
```

- Exact-text group: `cuad-exact-v1:8fcf75ae1160e1c5fd36435bd238dbc468306abf90b30d42721fc3af59073d5f`.
- Official split: `train`; paragraph: `0`; length: 37,876 Unicode code points.
- Context SHA-256: `4db35cae428d32e800d78491fbda9306df3b93ae8bb5c4c48a899e4943eb21d8`.

### T27

```text
BIOAMBERINC_04_10_2013-EX-10.34-DEVELOPMENT AGREEMENT - First Amendment
```

- Exact-text group: `cuad-exact-v1:b42bc5c5ccb3e95e48b14148274f015153a91807481a1007102710138883d97b`.
- Official split: `train`; paragraph: `0`; length: 6,390 Unicode code points.
- Context SHA-256: `59549da8c312d822619526f527abcd108a142d5270a28b0223d69491bbde125e`.

### T28

```text
BIOAMBERINC_04_10_2013-EX-10.34-DEVELOPMENT AGREEMENT (1)
```

- Exact-text group: `cuad-exact-v1:bb56fd6f1849a5d23e4a1223b38ecbd8218a00c0cb5b9979023664c74af921b5`.
- Official split: `train`; paragraph: `0`; length: 38,733 Unicode code points.
- Context SHA-256: `65b642a2a325f2b974d30da010140e775df5226de003f971dfc32ac30b522915`.

### T29

```text
PfHospitalityGroupInc_20150923_10-12G_EX-10.1_9266710_EX-10.1_Franchise Agreement3
```

- Exact-text group: `cuad-exact-v1:bcf2fd3d8fa28d85a5102c596856e118e3cdc78183e5da1501a118bfe7df4676`.
- Official split: `train`; paragraph: `0`; length: 6,772 Unicode code points.
- Context SHA-256: `6a5932ec6cc584c1976b516aae469c6f8f2335db1c65d008e2ab596b35b7a2de`.

### T30

```text
PfHospitalityGroupInc_20150923_10-12G_EX-10.1_9266710_EX-10.1_Franchise Agreement1
```

- Exact-text group: `cuad-exact-v1:e5bc3405b7c8811022636e193aed3ce9117d13a2ffb1c202a7012c3f7baa6958`.
- Official split: `train`; paragraph: `0`; length: 152,649 Unicode code points.
- Context SHA-256: `3d9aa8e816a1271c5169e51a03dd88439b1278c21ce57cb28b786e22335108e4`.

### T31

```text
AlliedEsportsEntertainmentInc_20190815_8-K_EX-10.34_11788308_EX-10.34_Sponsorship Agreement
```

- Exact-text group: `cuad-exact-v1:f169dc817c1909b0febbfb113867eb4f37b3a8ac08f58a0240370bcd7900e761`.
- Official split: `train`; paragraph: `0`; length: 37,796 Unicode code points.
- Context SHA-256: `e9a7e542a3a9941c3879ac170c7ade20c2c3bf456c8b5c9a4554d622f199e271`.

### T32

```text
AlliedEsportsEntertainmentInc_20190815_8-K_EX-10.19_11788293_EX-10.19_Content License Agreement
```

- Exact-text group: `cuad-exact-v1:fa958daf1b8feca371578c1fa597718730e710e70bebf0377767aeacce7c0d5c`.
- Official split: `train`; paragraph: `0`; length: 35,504 Unicode code points.
- Context SHA-256: `82411b6956e9a2144f8a1440891954249156112d44057c01f778ae577ab864a9`.

### T33

```text
LejuHoldingsLtd_20140121_DRS (on F-1)_EX-10.26_8473102_EX-10.26_Content License Agreement2
```

- Exact-text group: `cuad-exact-v1:073b83439a183fb911be23eade348bb07e38d33035e3351c0f3e930a52e8638b`.
- Official split: `train`; paragraph: `0`; length: 2,180 Unicode code points.
- Context SHA-256: `01ebcd4dc1fdc164d0f68fd217be2b99ba76c39f5d842288808a1dca8c8d839c`.

### T34

```text
LEJUHOLDINGSLTD_03_12_2014-EX-10.34-INTERNET CHANNEL COOPERATION AGREEMENT
```

- Exact-text group: `cuad-exact-v1:677fdd783bbbf77af015c65c56a1affee45889bbfeedea3e0338c47686cfa66d`.
- Official split: `train`; paragraph: `0`; length: 37,031 Unicode code points.
- Context SHA-256: `3b8e37d6654f64e03346182fcd4f0b40066df4fec0de37b9220345cf8d37ffbc`.

### T35

```text
LejuHoldingsLtd_20140121_DRS (on F-1)_EX-10.26_8473102_EX-10.26_Content License Agreement1
```

- Exact-text group: `cuad-exact-v1:1ba4a1ff167c30273cb0680cb323acb187edd67c17c020b9c1aede8cca3d46e8`.
- Official split: `train`; paragraph: `0`; length: 46,696 Unicode code points.
- Context SHA-256: `edb50810e93b97e83365e7e66f2bf583cfee3981ea1ffdbbcb9f0783d9050e2e`.

### T36

```text
VertexEnergyInc_20200113_8-K_EX-10.1_11943624_EX-10.1_Marketing Agreement
```

- Exact-text group: `cuad-exact-v1:4fe803d07fe2278a6b23755d91ecefe5565a72d08dfdde085c867ba84d43ad5b`.
- Official split: `train`; paragraph: `0`; length: 45,072 Unicode code points.
- Context SHA-256: `480cfbb8c3b84fd4e2e8bfb0a218b1b20d5c4634dc99a7defbd89c68f933ee88`.

### T37

```text
VERTEXENERGYINC_08_14_2014-EX-10.24-OPERATION AND MAINTENANCE AGREEMENT
```

- Exact-text group: `cuad-exact-v1:d6d2e12a6cd12a1a860eaf13690277edce0df700969112e7b9a122461f856131`.
- Official split: `train`; paragraph: `0`; length: 57,254 Unicode code points.
- Context SHA-256: `4b2cb71fad30b513054df0fcbe35d333dfb5b0b2267ff0733589427ad5e7327c`.

### T38

```text
ReynoldsConsumerProductsInc_20191115_S-1_EX-10.18_11896469_EX-10.18_Supply Agreement
```

- Exact-text group: `cuad-exact-v1:51cce0855a5417a689a4bdbe6e1b58ec41ab3e5331ed0c38e93f77835abd287b`.
- Official split: `train`; paragraph: `0`; length: 61,710 Unicode code points.
- Context SHA-256: `8c63d9a33c82bdae898b8511f7e476205323844dfee40ce52765fc08e2a5f200`.

### T39

```text
ReynoldsConsumerProductsInc_20200121_S-1A_EX-10.22_11948918_EX-10.22_Service Agreement
```

- Exact-text group: `cuad-exact-v1:97756f300a7602d09c3249f6f4f8f4d9c8dffda00b7fa6c39e1b46efc8a7e332`.
- Official split: `train`; paragraph: `0`; length: 112,910 Unicode code points.
- Context SHA-256: `0ddc8b40e5ad7b4f6b1a9d2a921cc7ab2e5d4076a4dcd2575b10b59fc2e6f6d2`.

### T40

```text
XLITECHNOLOGIES,INC_12_11_2015-EX-10.1-Sponsorship Agreement
```

- Exact-text group: `cuad-exact-v1:60ec1411ee5a21b7f444d88a72cc8ffa76efd3722a15f1f848b053c57d7c2106`.
- Official split: `train`; paragraph: `0`; length: 18,240 Unicode code points.
- Context SHA-256: `8bfbb8ed601688097ffffff9dc9c11bb709e677d2a9fd00ab6f5b5c5daf6f6f5`.

### T41

```text
XLITECHNOLOGIES,INC_12_02_2015-EX-10.02-STRATEGIC ALLIANCE AGREEMENT
```

- Exact-text group: `cuad-exact-v1:82036ac559e23794546e59accc93def9c447bd7f66b4bae967dc68c527dd7ad7`.
- Official split: `train`; paragraph: `0`; length: 5,712 Unicode code points.
- Context SHA-256: `f472689ea796c2becb882fee8be93608f3c2191bae6efb59e164044ec55dc1ee`.

### T42

```text
StampscomInc_20001114_10-Q_EX-10.47_2631630_EX-10.47_Co-Branding Agreement
```

- Exact-text group: `cuad-exact-v1:64e9e245ab8e2d2c1ccdeda9a92e405ad50186c0913f5d80edca30142f1cb83e`.
- Official split: `train`; paragraph: `0`; length: 87,014 Unicode code points.
- Context SHA-256: `0fec47f78bf4f1f6a230d495bbb23c91106f96cbb2d53f556c0d7ada09c850fc`.

### T43

```text
STAMPSCOMINC_06_24_1999-EX-10.18-SPONSORSHIP AGREEMENT
```

- Exact-text group: `cuad-exact-v1:eb7ccc0ee504d0aff7906f3528566e69655d0008d35ebd725de76adfd54114aa`.
- Official split: `train`; paragraph: `0`; length: 40,856 Unicode code points.
- Context SHA-256: `9f065ac5ffd4d1c95be4c7e8f97967f77bc5689952f589429095e6a59003416f`.

### T44

```text
KIROMICBIOPHARMA,INC_04_08_2020-EX-10.28-JOINT VENTURE AGREEMENT
```

- Exact-text group: `cuad-exact-v1:69b68bff5ed90636c9bee47d5c233af471ee5e7a21697c79906a70e4d4c4b5c3`.
- Official split: `train`; paragraph: `0`; length: 36,610 Unicode code points.
- Context SHA-256: `5d49e97e8deb2ed6d588cdc8604572b6d70ffbe137f42be03a0548c1441e8d6b`.

### T45

```text
KIROMICBIOPHARMA,INC_05_11_2020-EX-10.23-CONSULTING AGREEMENT
```

- Exact-text group: `cuad-exact-v1:b7637b4197c88e484d9471903a33dd481bd5ba9d22278840bb3ee2545602f0a8`.
- Official split: `train`; paragraph: `0`; length: 18,403 Unicode code points.
- Context SHA-256: `aacd48ab914fdede120150e2da4e222b342fa4f963a830384f8c848e9bf738a9`.

### T46

```text
LegacyEducationAllianceInc_20200330_10-K_EX-10.18_12090678_EX-10.18_Development Agreement
```

- Exact-text group: `cuad-exact-v1:71df1c590a862d37ab3208dfa0d1a61892d4c4c671e08067e185d04f5c06f411`.
- Official split: `train`; paragraph: `0`; length: 46,255 Unicode code points.
- Context SHA-256: `b7a8cea1bb15131ce75906b63a977426b7aef9300215424caf5c25bb8c92d337`.

### T47

```text
LegacyEducationAllianceInc_20141110_8-K_EX-10.9_8828866_EX-10.9_Endorsement Agreement
```

- Exact-text group: `cuad-exact-v1:7e501da05a846c09bf525dc793839d3d72ffbe202c9226de2360400ca8187ad9`.
- Official split: `train`; paragraph: `0`; length: 19,913 Unicode code points.
- Context SHA-256: `58078cc191465e413069fc8ab1a717e56e50e10ca476f5f79f734d0638943280`.

### T48

```text
VnueInc_20150914_8-K_EX-10.1_9259571_EX-10.1_Promotion Agreement
```

- Exact-text group: `cuad-exact-v1:c2f798432f519dffd4b4cba191732df70ed1fe51fdb4f7c5e2e3157de07ef590`.
- Official split: `train`; paragraph: `0`; length: 10,553 Unicode code points.
- Context SHA-256: `1cf474e83b78700c764b3d756a6ad0c4720327f851361993144fe2e734144f7d`.

### T49

```text
VNUE,INC_07_10_2015-EX-10.1-SPONSORSHIP AGREEMENT
```

- Exact-text group: `cuad-exact-v1:cabe18b1a2a73b1a9340e8d1b6955f37c7a0f1a1868757404fa4a875b0ba935e`.
- Official split: `train`; paragraph: `0`; length: 20,487 Unicode code points.
- Context SHA-256: `e3ce39469d5b67b169af1e3b0164b3457fdbf324855320d8cc5637f9f432a5d1`.
