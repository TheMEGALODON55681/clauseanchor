/* The 46 categories: the ids the API takes (ml/configs/catalogue.json), with a label and a group for display. The API serves its own
   display_name and support_status too, and the frontend keeps its own wording and the seven groups. A test holds the ids equal to the file. */

export type CatalogueEntry = { id: string; label: string; group: string };

const G = {
  basics: "Basics",
  restrictions: "Restrictions",
  term: "Term and termination",
  money: "Money and liability",
  ip: "Intellectual property",
  other: "Other rights",
  india: "India-specific",
};

const rows: [string, string, string][] = [
  ["cuad.document_name", "Document Name", G.basics],
  ["cuad.parties", "Parties", G.basics],
  ["cuad.agreement_date", "Agreement Date", G.basics],
  ["cuad.effective_date", "Effective Date", G.basics],
  ["cuad.expiration_date", "Expiration Date", G.basics],
  ["cuad.renewal_term", "Renewal Term", G.basics],
  ["cuad.notice_period_renewal", "Notice Period to Terminate Renewal", G.basics],
  ["cuad.governing_law", "Governing Law", G.basics],
  ["cuad.most_favored_nation", "Most Favored Nation", G.restrictions],
  ["cuad.non_compete", "Non-Compete", G.restrictions],
  ["cuad.exclusivity", "Exclusivity", G.restrictions],
  ["cuad.no_solicit_customers", "No-Solicit of Customers", G.restrictions],
  ["cuad.competitive_restriction_exception", "Competitive Restriction Exception", G.restrictions],
  ["cuad.no_solicit_employees", "No-Solicit of Employees", G.restrictions],
  ["cuad.non_disparagement", "Non-Disparagement", G.restrictions],
  ["cuad.price_restrictions", "Price Restrictions", G.restrictions],
  ["cuad.volume_restriction", "Volume Restriction", G.restrictions],
  ["cuad.termination_for_convenience", "Termination for Convenience", G.term],
  ["cuad.change_of_control", "Change of Control", G.term],
  ["cuad.anti_assignment", "Anti-Assignment", G.term],
  ["cuad.post_termination_services", "Post-Termination Services", G.term],
  ["cuad.revenue_profit_sharing", "Revenue/Profit Sharing", G.money],
  ["cuad.minimum_commitment", "Minimum Commitment", G.money],
  ["cuad.uncapped_liability", "Uncapped Liability", G.money],
  ["cuad.cap_on_liability", "Cap on Liability", G.money],
  ["cuad.liquidated_damages", "Liquidated Damages", G.money],
  ["cuad.warranty_duration", "Warranty Duration", G.money],
  ["cuad.insurance", "Insurance", G.money],
  ["cuad.audit_rights", "Audit Rights", G.money],
  ["cuad.ip_ownership_assignment", "IP Ownership Assignment", G.ip],
  ["cuad.joint_ip_ownership", "Joint IP Ownership", G.ip],
  ["cuad.license_grant", "License Grant", G.ip],
  ["cuad.non_transferable_license", "Non-Transferable License", G.ip],
  ["cuad.affiliate_license_licensor", "Affiliate License-Licensor", G.ip],
  ["cuad.affiliate_license_licensee", "Affiliate License-Licensee", G.ip],
  ["cuad.unlimited_license", "Unlimited/All-You-Can-Eat License", G.ip],
  ["cuad.irrevocable_perpetual_license", "Irrevocable or Perpetual License", G.ip],
  ["cuad.source_code_escrow", "Source Code Escrow", G.ip],
  ["cuad.rofr_rofo_rofn", "ROFR/ROFO/ROFN", G.other],
  ["cuad.covenant_not_to_sue", "Covenant Not to Sue", G.other],
  ["cuad.third_party_beneficiary", "Third Party Beneficiary", G.other],
  ["in.arbitration", "Arbitration", G.india],
  ["in.seat_venue", "Seat and Venue", G.india],
  ["in.stamping_registration", "Stamping and Registration", G.india],
  ["in.forum_selection", "Jurisdiction / Forum Selection", G.india],
  ["in.dispute_escalation", "Dispute Escalation", G.india],
];

export const CATALOGUE: CatalogueEntry[] = rows.map(([id, label, group]) => ({ id, label, group }));
/** The five India-specific categories, which the switch on step 3 adds to the list. */
export const INDIA_IDS: string[] = CATALOGUE.filter((c) => c.group === G.india).map((c) => c.id);
export const GROUP_ORDER = Object.values(G);
export const CATEGORY_BY_ID: Record<string, CatalogueEntry> = Object.fromEntries(CATALOGUE.map((c) => [c.id, c]));
