# CUAD XACCT unparsed-title review

Reviewed: 20 October 2026 (India time).

**Status:** assistant-assisted manual source inspection prepared for Tanishq.
The sole unparsed title in the frozen title screen has now been inspected.
This note records its source identity and the limit of the available evidence;
it does not change the parser, rename the record, create a family edge or clear
the corpus for internal splits.

## Snapshot and finding

- Repository checked: `main` at `c124fdcc0076ae48cc9acb0ac00773feea9c5763`.
- Full source SHA-256: `ed0b77d85bdf4014d7495800e8e4a70565b48ee6f8a2e5dca9cf8655dbf10eae`.
- Title report: `data/processed/cuad/title_candidates.json`, screen version `1.0.0`, canonical SHA-256 `c9a962bba49d410bc12ddc90dabf5eeeb2458a6abf38face809968acb609c312`.
- Source/archive attribution: [CUAD README](../../data/raw/cuad/README.md).
- Related review and outstanding gates: [remaining training review](CUAD_RemainingTrainingFamilyReview.md).

The original title runs the company name into the agreement heading and has
neither of the date/exhibit filename formats recognized by the current screen.
The report records `format: unparsed`, issue `unparsed_issuer`, and null issuer,
filing-date and exhibit fields. Keep that pinned output unchanged.

Manual reading identifies **XACCT Technologies, Inc.** in the title and operative
party passage. The context is a support and maintenance form with a blank
licensee and blank effective day/month in 2000. Its heading prints
`DRAFT (Americas) 1/12/00 (Rev 1)` with additional source spacing. That marker
is not evidence of a filing date or an executed agreement date. `EXHIBIT 10.16`
comes from the context, not from a successful filename parse. Do not fill null
title-derived fields from those context details or invent an effective date.

The form provides maintenance/support for a product licensed under XACCT's End
User Software License Agreement and incorporates that license's other terms
except where superseded. This establishes a referenced agreement type; it does
not identify a second CUAD record or authorize importing absent text or labels.

## Evidence and search scope

The opening identity, draft marker, blank fields and incorporation passages were
read. All 510 source titles and all paragraph contexts were searched
case-insensitively for the literal `xacct`. Exactly one title and one document
context matched: this record, with 48 context matches. No separately identifiable
XACCT license record was located by that search. This limited result does not
prove that no differently named, redacted or template-related record exists.
The full document was not reviewed clause by clause, and no external filing
search was used to reconstruct missing metadata.

Ranges address paragraph 0 of the untouched context: zero-based Unicode code
points, end exclusive. They were checked against the source bytes and identity.

| Source evidence | Record | Exact range |
|---|---|---|
| Context exhibit heading | X1 | `[0, 13)` |
| Draft revision marker and agreement heading | X1 | `[15, 95)` |
| XACCT identity, blank effective date and blank licensee | X1 | `[102, 583)` |
| Referenced End User Software License Agreement and incorporation | X1 | `[585, 1141)` |

## Documentary disposition

Manual inspection of the unparsed-title item is complete with limitations
recorded. **No additional family edge or exclusion is supported by the inspected
evidence.** Preserve the record as its existing official-training singleton
for prospective confirmed-edge accounting; that is not independent approval to
assign it to an internal partition. Do not mark a nonexistent candidate pair
as rejected, and do not remove this record because its title cannot be parsed.

A future manifest/review registry should record this manual disposition and
the frozen report identity without pretending the parser has been corrected.
If new linkage evidence appears, reopen the family review. The original report
will continue to show one unparsed title until a separately versioned screen
change is implemented and reviewed.

The existing manifest remains at version 1.0.0 with broader review pending and
internal splits not approved. This inspection changes none of the prospective
counts in the companion note and resolves none of the six outstanding pair
decisions or the AduroBioTech annotation conflict.

## Source identity

### X1

```text
XACCT Technologies, Inc.SUPPORT AND MAINTENANCE AGREEMENT
```

- Exact-text group: `cuad-exact-v1:16f9c516114a2cd2f66096a8aa028645d82055f306a4363638b559283d881b0a`.
- Official split: `train`; paragraph: `0`; length: 14,193 Unicode code points.
- Context SHA-256: `caf3ed803f22678ad41977cc950225b240d52506d14ad45a3e619f50a4f3fb5b`.
