# Category catalogue 1.0.0

This is the first product catalogue: 41 CUAD categories and five India extensions.
All 46 rows are `not_validated`. It defines category identity and scope; it is not
an accuracy result, a trained model, or evidence that arbitrary uploads can be analysed.

## Files and ownership

- Authoritative catalogue: `ml/configs/catalogue.json`.
- Read-only verifier: `ml/scripts/check_catalogue.py`.
- Source audit: `ml/scripts/audit_cuad_categories.py` and its reproducible,
  ignored `data/processed/cuad/category_audit.json` output.
- API contract: `docs/app/API.md`, section 5.

The JSON has exactly two top-level keys, `catalogue_version` and `categories`.
Each row has exactly `id`, `display_name`, `source`, and `support_status`.
`source` is `cuad` or `india_extension`. File order is the official CUAD table's
order followed by the five India extensions. Display grouping is a frontend concern.
Questions, descriptions, aliases, and provenance are deliberately outside this
four-field API file: adding them there would fail the backend's strict loader.

The checker verifies the current backend loader accepts the same rows and order.
It does not start an API server, install the deployment copy, change the default
backend path, or update the frontend adapter.

## Support vocabulary

| Value | Meaning |
|---|---|
| `not_validated` | No released evidence establishes usable calibrated category decisions for this category in the declared scope. Listing it does not enable real analysis or justify a confident absence. |
| `pooled` | A future released artifact explicitly assigns a shared calibration/decision policy, with its pooled scope, support counts, and limitations recorded. It must not imply category-specific validation. |
| `validated` | A future released artifact supplies the measured category-specific evidence, calibration, and decision policy required for the declared scope. This does not imply legal correctness or complete document coverage. |

Only `not_validated` is used in version 1.0.0. CUAD annotations and successful data
integrity checks are not model validation. The frontend mock's example `validated`
and `pooled` values must not be copied into the real capabilities response.

Support is different from a per-document core result (`found`, `absent`,
`abstained`, `unavailable`) and from sample/real mode or artifact readiness.
The four sample categories remain illustrative fixtures; the stub still accepts
only its fixed sample. Adding 46 catalogue rows does not expand the stub's inputs.

## Stable identity and source questions

IDs are explicit, namespaced identifiers, never regenerated from display names.
`cuad.uncapped_liability` and `cuad.governing_law` are confirmed in this catalogue.
The existing core IDs `cuad.cap_on_liability`, `cuad.non_compete`, `in.arbitration`,
and `in.seat_venue` are preserved.

CUAD source: The Atticus Project, repository `The-Atticus-Project/cuad`, revision
`67faa0e6023b04fcaae6cc09497ab00e5d63a2a2`, `category_descriptions.csv`, SHA-256
`7499950ee04d2ed2841c0f8ec2ef96b91be039bc2ea3c4edcc36334a465b1f36`.
See [CUAD attribution](../../data/raw/cuad/README.md).

The exact original CUAD question is the source audit's `question_exact`, keyed
by `official_table_label`, which matches this catalogue's `display_name` for
CUAD rows. Preserve the complete source question, its original category-label
capitalization, whitespace, and Unicode characters. Do not reconstruct it from
the display name. The audit explicitly handles the ten observed capitalization
aliases; it does not perform fuzzy matching.

The five India IDs and fixed prompts come from `ClauseAnchor_Plan.md` section 4.3:

| ID | Fixed question |
|---|---|
| `in.arbitration` | Which text provides for arbitration of disputes? |
| `in.seat_venue` | Which text states the seat or venue of arbitration? |
| `in.stamping_registration` | Which text addresses stamp duty, stamping or registration? |
| `in.forum_selection` | Which text selects courts or a judicial forum for disputes? |
| `in.dispute_escalation` | Which text requires negotiation, mediation or another step before formal dispute resolution? |

India categories have no CUAD labels. Their absence from CUAD must never become
negative training examples. This catalogue does not settle the separate Indian
study export schema or its five CUAD annotation prompts.

## Complete ID list and frontend migration

The last column names the current frontend mock ID. It is a migration reference,
not an accepted alias for live API requests. The adapter must use the full stable
ID in the first column, fetch support from capabilities, and update lookups and
sample mappings consistently. The two India renames require more than adding a
namespace prefix.

| Stable ID | Display name | Current frontend mock ID |
|---|---|---|
| `cuad.document_name` | Document Name | `document_name` |
| `cuad.parties` | Parties | `parties` |
| `cuad.agreement_date` | Agreement Date | `agreement_date` |
| `cuad.effective_date` | Effective Date | `effective_date` |
| `cuad.expiration_date` | Expiration Date | `expiration_date` |
| `cuad.renewal_term` | Renewal Term | `renewal_term` |
| `cuad.notice_period_renewal` | Notice Period to Terminate Renewal | `notice_period_renewal` |
| `cuad.governing_law` | Governing Law | `governing_law` |
| `cuad.most_favored_nation` | Most Favored Nation | `most_favored_nation` |
| `cuad.non_compete` | Non-Compete | `non_compete` |
| `cuad.exclusivity` | Exclusivity | `exclusivity` |
| `cuad.no_solicit_customers` | No-Solicit of Customers | `no_solicit_customers` |
| `cuad.competitive_restriction_exception` | Competitive Restriction Exception | `competitive_restriction_exception` |
| `cuad.no_solicit_employees` | No-Solicit of Employees | `no_solicit_employees` |
| `cuad.non_disparagement` | Non-Disparagement | `non_disparagement` |
| `cuad.termination_for_convenience` | Termination for Convenience | `termination_for_convenience` |
| `cuad.rofr_rofo_rofn` | Rofr/Rofo/Rofn | `rofr_rofo_rofn` |
| `cuad.change_of_control` | Change of Control | `change_of_control` |
| `cuad.anti_assignment` | Anti-Assignment | `anti_assignment` |
| `cuad.revenue_profit_sharing` | Revenue/Profit Sharing | `revenue_profit_sharing` |
| `cuad.price_restrictions` | Price Restrictions | `price_restrictions` |
| `cuad.minimum_commitment` | Minimum Commitment | `minimum_commitment` |
| `cuad.volume_restriction` | Volume Restriction | `volume_restriction` |
| `cuad.ip_ownership_assignment` | IP Ownership Assignment | `ip_ownership_assignment` |
| `cuad.joint_ip_ownership` | Joint IP Ownership | `joint_ip_ownership` |
| `cuad.license_grant` | License Grant | `license_grant` |
| `cuad.non_transferable_license` | Non-Transferable License | `non_transferable_license` |
| `cuad.affiliate_license_licensor` | Affiliate License-Licensor | `affiliate_license_licensor` |
| `cuad.affiliate_license_licensee` | Affiliate License-Licensee | `affiliate_license_licensee` |
| `cuad.unlimited_license` | Unlimited/All-You-Can-Eat-License | `unlimited_license` |
| `cuad.irrevocable_perpetual_license` | Irrevocable or Perpetual License | `irrevocable_perpetual_license` |
| `cuad.source_code_escrow` | Source Code Escrow | `source_code_escrow` |
| `cuad.post_termination_services` | Post-Termination Services | `post_termination_services` |
| `cuad.audit_rights` | Audit Rights | `audit_rights` |
| `cuad.uncapped_liability` | Uncapped Liability | `uncapped_liability` |
| `cuad.cap_on_liability` | Cap on Liability | `cap_on_liability` |
| `cuad.liquidated_damages` | Liquidated Damages | `liquidated_damages` |
| `cuad.warranty_duration` | Warranty Duration | `warranty_duration` |
| `cuad.insurance` | Insurance | `insurance` |
| `cuad.covenant_not_to_sue` | Covenant Not to Sue | `covenant_not_to_sue` |
| `cuad.third_party_beneficiary` | Third Party Beneficiary | `third_party_beneficiary` |
| `in.arbitration` | Arbitration | `arbitration` |
| `in.seat_venue` | Seat and Venue | `seat_and_venue` |
| `in.stamping_registration` | Stamping and Registration | `stamping_registration` |
| `in.forum_selection` | Jurisdiction / Forum Selection | `jurisdiction_forum` |
| `in.dispute_escalation` | Dispute Escalation | `dispute_escalation` |

## Verification and app handoff

From the repository root, after the existing data audits have passed:

```powershell
python .\ml\scripts\check_catalogue.py
```

Expected: catalogue 1.0.0; 46 unique IDs; 41 CUAD and five India categories; all
46 `not_validated`; 41 source question mappings; four preserved sample IDs;
acceptance by the current backend loader. This check is read-only and uses the
already verified local sources. No backend dependencies need installing.

The API currently defaults to `backend/app/catalogue.json`. Aryan can install an
exact deployment copy of `ml/configs/catalogue.json` at that path and restart the
API. Keep the ML file authoritative, check byte equality on updates, and add the
backend regression test that pins 41 CUAD rows, five India rows, 46 unique IDs,
the version, support statuses, and the complete capabilities response. The
backend loader accepting this ML file alone does not close app Phase 2-A.
The frontend adapter still needs the migration above.

Every published catalogue change must use a new catalogue version. Never reuse
an ID for a different concept. Support upgrades require recorded model/policy
artifacts and evaluation evidence, with checks and app deployment updated in the
same coordinated release. Parser and core contract versions are separate.
