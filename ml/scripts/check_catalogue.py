"""Check catalogue 1.0.0 against CUAD, the sample, and the current backend loader.

Run from the repository root: python ml/scripts/check_catalogue.py
Read-only; uses the already downloaded, pinned CUAD files. No backend server,
new dependencies, network access, or model is required.
"""

from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys

from audit_cuad_categories import audit_categories, parse_table
from audit_cuad_questions import require
from build_cuad_inventory import load_sources


CATALOGUE_VERSION = "1.0.0"
ROW_FIELDS = {"id", "display_name", "source", "support_status"}

# Explicit, reviewed identities. Never derive an ID by slugifying a label.
# Order follows the official CUAD description table.
CUAD_IDS = {
    "Document Name": "cuad.document_name",
    "Parties": "cuad.parties",
    "Agreement Date": "cuad.agreement_date",
    "Effective Date": "cuad.effective_date",
    "Expiration Date": "cuad.expiration_date",
    "Renewal Term": "cuad.renewal_term",
    "Notice Period to Terminate Renewal": "cuad.notice_period_renewal",
    "Governing Law": "cuad.governing_law",
    "Most Favored Nation": "cuad.most_favored_nation",
    "Non-Compete": "cuad.non_compete",
    "Exclusivity": "cuad.exclusivity",
    "No-Solicit of Customers": "cuad.no_solicit_customers",
    "Competitive Restriction Exception": "cuad.competitive_restriction_exception",
    "No-Solicit of Employees": "cuad.no_solicit_employees",
    "Non-Disparagement": "cuad.non_disparagement",
    "Termination for Convenience": "cuad.termination_for_convenience",
    "Rofr/Rofo/Rofn": "cuad.rofr_rofo_rofn",
    "Change of Control": "cuad.change_of_control",
    "Anti-Assignment": "cuad.anti_assignment",
    "Revenue/Profit Sharing": "cuad.revenue_profit_sharing",
    "Price Restrictions": "cuad.price_restrictions",
    "Minimum Commitment": "cuad.minimum_commitment",
    "Volume Restriction": "cuad.volume_restriction",
    "IP Ownership Assignment": "cuad.ip_ownership_assignment",
    "Joint IP Ownership": "cuad.joint_ip_ownership",
    "License Grant": "cuad.license_grant",
    "Non-Transferable License": "cuad.non_transferable_license",
    "Affiliate License-Licensor": "cuad.affiliate_license_licensor",
    "Affiliate License-Licensee": "cuad.affiliate_license_licensee",
    "Unlimited/All-You-Can-Eat-License": "cuad.unlimited_license",
    "Irrevocable or Perpetual License": "cuad.irrevocable_perpetual_license",
    "Source Code Escrow": "cuad.source_code_escrow",
    "Post-Termination Services": "cuad.post_termination_services",
    "Audit Rights": "cuad.audit_rights",
    "Uncapped Liability": "cuad.uncapped_liability",
    "Cap on Liability": "cuad.cap_on_liability",
    "Liquidated Damages": "cuad.liquidated_damages",
    "Warranty Duration": "cuad.warranty_duration",
    "Insurance": "cuad.insurance",
    "Covenant Not to Sue": "cuad.covenant_not_to_sue",
    "Third Party Beneficiary": "cuad.third_party_beneficiary",
}

INDIA_IDS = {
    "Arbitration": "in.arbitration",
    "Seat and Venue": "in.seat_venue",
    "Stamping and Registration": "in.stamping_registration",
    "Jurisdiction / Forum Selection": "in.forum_selection",
    "Dispute Escalation": "in.dispute_escalation",
}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Repeated JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)


def validate_catalogue(data):
    require(isinstance(data, dict) and set(data) == {"catalogue_version", "categories"},
            "Catalogue must have exactly catalogue_version and categories.")
    require(data["catalogue_version"] == CATALOGUE_VERSION, "This checker expects catalogue 1.0.0.")
    rows = data["categories"]
    require(isinstance(rows, list) and len(rows) == 46, "Expected 46 catalogue categories.")
    expected = [
        (category_id, name, source)
        for source, mapping in (("cuad", CUAD_IDS), ("india_extension", INDIA_IDS))
        for name, category_id in mapping.items()
    ]
    seen = set()
    for row, identity in zip(rows, expected, strict=True):
        require(isinstance(row, dict) and set(row) == ROW_FIELDS,
                "Each category must have exactly the four API fields.")
        require(all(isinstance(value, str) and value.strip() for value in row.values()),
                "Category values must be nonempty strings.")
        require(re.fullmatch(r"(?:cuad|in)\.[a-z][a-z0-9_]*", row["id"]), "Invalid namespaced ID.")
        require(row["id"] not in seen, "Repeated category ID.")
        seen.add(row["id"])
        require((row["id"], row["display_name"], row["source"]) == identity,
                f"Category identity or frozen order differs: {row['id']}")
        require(row["support_status"] == "not_validated",
                "Catalogue 1.0.0 cannot claim measured model support.")
    return rows


def check_backend_loader(repo_root, catalogue_path, expected_rows):
    # scope.py currently uses only the standard library. Load that specific file,
    # without importing the app factory or requiring FastAPI on the ML laptop.
    scope_path = repo_root / "backend/app/services/scope.py"
    require(scope_path.is_file(), "Backend catalogue loader missing; pull the current repository.")
    name = "_clauseanchor_catalogue_check_scope"
    spec = importlib.util.spec_from_file_location(name, scope_path)
    require(spec is not None and spec.loader is not None, "Cannot load backend scope module.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        loaded = module.load_catalogue(catalogue_path)
        actual = [
            {"id": row.id, "display_name": row.display_name,
             "source": row.source, "support_status": row.support_status}
            for row in loaded.categories
        ]
        require(loaded.version == CATALOGUE_VERSION and actual == expected_rows,
                "Backend loader changed the catalogue fields or order.")
    finally:
        sys.modules.pop(name, None)


def main():
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "ml/configs/catalogue.json"
    rows = validate_catalogue(read_json(path))
    full, _, _, provenance = load_sources(repo_root)
    table_path = (repo_root / provenance["files"]["train"]["path"]).parent / "category_descriptions.csv"
    require(table_path.is_file(), "Run audit_cuad_categories.py to obtain the pinned category table first.")
    table = parse_table(table_path.read_bytes())
    require(table.keys() == CUAD_IDS.keys(), "CUAD identity map differs from the official category set.")
    audited = audit_categories(full, table)
    require(len({CUAD_IDS[item["official_table_label"]] for item in audited}) == 41,
            "CUAD question labels do not map one-to-one to catalogue IDs.")

    sample = read_json(repo_root / "ml/fixtures/sample_analysis.json")
    sample_ids = {row["category_id"] for row in sample["categories"]}
    require(sample_ids == {"cuad.cap_on_liability", "cuad.non_compete", "in.arbitration", "in.seat_venue"},
            "Sample category scope changed; review catalogue compatibility.")
    require(sample_ids <= {row["id"] for row in rows}, "Existing sample IDs were lost.")
    check_backend_loader(repo_root, path, rows)
    counts = Counter(row["source"] for row in rows)
    print(f"Catalogue version: {CATALOGUE_VERSION}")
    print(f"Unique category IDs: {len(rows)}")
    print(f"CUAD categories: {counts['cuad']}")
    print(f"India extensions: {counts['india_extension']}")
    print("Support status: not_validated for all 46 categories")
    print(f"Verified CUAD category/question mappings: {len(audited)}")
    print(f"Existing sample category IDs preserved: {len(sample_ids)}")
    print("Current backend loader: accepted all 46 rows without changes")
    print("PASS: catalogue 1.0.0, source mappings, and backend file compatibility verified.")
    print("Read-only check: no files changed; backend installation and frontend adapter are separate steps.")


if __name__ == "__main__":
    main()
