/* Category catalogue: labels and grouping for display. The backend returns category_id only. */

export type Support = "validated" | "pooled" | "not_validated";
export type CatalogueEntry = { id: string; label: string; group: string; support: Support };

export const CATALOGUE_VERSION = "cat-2026.09-r1.1";

const G = {
  basics: "Basics",
  restrictions: "Restrictions",
  term: "Term and termination",
  money: "Money and liability",
  ip: "Intellectual property",
  other: "Other rights",
  india: "India-specific",
};

const rows: [string, string, string, Support][] = [
  ["document_name", "Document Name", G.basics, "validated"],
  ["parties", "Parties", G.basics, "validated"],
  ["agreement_date", "Agreement Date", G.basics, "validated"],
  ["effective_date", "Effective Date", G.basics, "validated"],
  ["expiration_date", "Expiration Date", G.basics, "not_validated"],
  ["renewal_term", "Renewal Term", G.basics, "validated"],
  ["notice_period_renewal", "Notice Period to Terminate Renewal", G.basics, "validated"],
  ["governing_law", "Governing Law", G.basics, "validated"],
  ["most_favored_nation", "Most Favored Nation", G.restrictions, "pooled"],
  ["non_compete", "Non-Compete", G.restrictions, "validated"],
  ["exclusivity", "Exclusivity", G.restrictions, "validated"],
  ["no_solicit_customers", "No-Solicit of Customers", G.restrictions, "validated"],
  ["competitive_restriction_exception", "Competitive Restriction Exception", G.restrictions, "pooled"],
  ["no_solicit_employees", "No-Solicit of Employees", G.restrictions, "validated"],
  ["non_disparagement", "Non-Disparagement", G.restrictions, "not_validated"],
  ["price_restrictions", "Price Restrictions", G.restrictions, "pooled"],
  ["volume_restriction", "Volume Restriction", G.restrictions, "pooled"],
  ["termination_for_convenience", "Termination for Convenience", G.term, "validated"],
  ["change_of_control", "Change of Control", G.term, "validated"],
  ["anti_assignment", "Anti-Assignment", G.term, "validated"],
  ["post_termination_services", "Post-Termination Services", G.term, "pooled"],
  ["revenue_profit_sharing", "Revenue/Profit Sharing", G.money, "validated"],
  ["minimum_commitment", "Minimum Commitment", G.money, "validated"],
  ["uncapped_liability", "Uncapped Liability", G.money, "validated"],
  ["cap_on_liability", "Cap on Liability", G.money, "validated"],
  ["liquidated_damages", "Liquidated Damages", G.money, "validated"],
  ["warranty_duration", "Warranty Duration", G.money, "pooled"],
  ["insurance", "Insurance", G.money, "not_validated"],
  ["audit_rights", "Audit Rights", G.money, "not_validated"],
  ["ip_ownership_assignment", "IP Ownership Assignment", G.ip, "validated"],
  ["joint_ip_ownership", "Joint IP Ownership", G.ip, "pooled"],
  ["license_grant", "License Grant", G.ip, "validated"],
  ["non_transferable_license", "Non-Transferable License", G.ip, "validated"],
  ["affiliate_license_licensor", "Affiliate License-Licensor", G.ip, "pooled"],
  ["affiliate_license_licensee", "Affiliate License-Licensee", G.ip, "pooled"],
  ["unlimited_license", "Unlimited/All-You-Can-Eat License", G.ip, "pooled"],
  ["irrevocable_perpetual_license", "Irrevocable or Perpetual License", G.ip, "validated"],
  ["source_code_escrow", "Source Code Escrow", G.ip, "pooled"],
  ["rofr_rofo_rofn", "ROFR/ROFO/ROFN", G.other, "validated"],
  ["covenant_not_to_sue", "Covenant Not to Sue", G.other, "pooled"],
  ["third_party_beneficiary", "Third Party Beneficiary", G.other, "pooled"],
  ["arbitration", "Arbitration", G.india, "validated"],
  ["seat_and_venue", "Seat and Venue", G.india, "validated"],
  ["stamping_registration", "Stamping and Registration", G.india, "not_validated"],
  ["jurisdiction_forum", "Jurisdiction / Forum Selection", G.india, "validated"],
  ["dispute_escalation", "Dispute Escalation", G.india, "pooled"],
];

export const CATALOGUE: CatalogueEntry[] = rows.map(([id, label, group, support]) => ({ id, label, group, support }));
export const GROUP_ORDER = Object.values(G);
export const CATEGORY_BY_ID: Record<string, CatalogueEntry> = Object.fromEntries(CATALOGUE.map((c) => [c.id, c]));
