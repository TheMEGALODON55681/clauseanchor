"""Verify CUAD category names and exact questions against the official table.

Run from the repository root: python ml/scripts/audit_cuad_categories.py
Requires build_cuad_inventory.py and audit_cuad_questions.py beside this file.
Uses the existing data.yaml and verified full/train/test files.

Downloads only the small category_descriptions.csv at the configured official
Git revision. Its checksum pins the reviewed table. Both the CSV and derived
category_audit.json stay under ignored data/ folders. Existing different files
are never overwritten. The report preserves source wording, including NBSPs.

This is a source audit, not the 46-category product catalogue or a statement of
model support. It does not alter annotations, document groups, or splits.
"""

from collections import Counter, defaultdict
import csv
import io
import json
from pathlib import Path
import re
from urllib.request import urlopen

from audit_cuad_questions import require
from build_cuad_inventory import load_sources, sha256


TABLE_FILENAME = "category_descriptions.csv"
TABLE_SHA256 = "7499950ee04d2ed2841c0f8ec2ef96b91be039bc2ea3c4edcc36334a465b1f36"
MAX_TABLE_BYTES = 256 * 1024
HEADERS = ["Category (incl. context and answer)", "Description", "Answer Format", "Group"]

# Reviewed JSON question-ID labels -> official CSV labels. No fuzzy matching.
LABEL_ALIASES = {
    "Cap On Liability": "Cap on Liability",
    "Change Of Control": "Change of Control",
    "Covenant Not To Sue": "Covenant Not to Sue",
    "Ip Ownership Assignment": "IP Ownership Assignment",
    "Irrevocable Or Perpetual License": "Irrevocable or Perpetual License",
    "Joint Ip Ownership": "Joint IP Ownership",
    "No-Solicit Of Customers": "No-Solicit of Customers",
    "No-Solicit Of Employees": "No-Solicit of Employees",
    "Notice Period To Terminate Renewal": "Notice Period to Terminate Renewal",
    "Termination For Convenience": "Termination for Convenience",
}


def parse_table(payload):
    require(sha256(payload) == TABLE_SHA256, "Official category table checksum differs.")
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    require(reader.fieldnames == HEADERS, "Unexpected official CSV columns.")
    table = {}
    for row in reader:
        require(set(row) == set(HEADERS) and all(isinstance(v, str) for v in row.values()),
                "Malformed category table row.")
        category = row[HEADERS[0]]
        description = row["Description"]
        require(category.startswith("Category: "), "Missing category prefix.")
        require(description.startswith("Description: "), "Missing description prefix.")
        label = category[len("Category: "):]
        require(label and label not in table, "Missing or repeated category name.")
        table[label] = {
            "description_exact": description[len("Description: "):],
            "source_csv_row": dict(row),
        }
    require(len(table) == 41, "Expected exactly 41 official category definitions.")
    for alias, target in LABEL_ALIASES.items():
        require(alias not in table and target in table, "Invalid explicit label alias.")
        require(alias.casefold() == target.casefold(), "Alias changes more than capitalization.")
    return table


def audit_categories(full, table):
    # Resolve only exact table names or the reviewed aliases above.
    mapping = {label: label for label in table}
    mapping.update(LABEL_ALIASES)
    variants = defaultdict(Counter)
    labels_seen = defaultdict(set)
    for title, document in full.items():
        prefix = title + "__"
        for paragraph in document["paragraphs"]:
            seen = set()
            for question in paragraph["qas"]:
                require(question["id"].startswith(prefix), "Unexpected source question ID.")
                source_label = question["id"][len(prefix):]
                require(source_label in mapping, f"Unknown CUAD label: {source_label}")
                official_label = mapping[source_label]
                require(official_label not in seen, f"Repeated category in {title}: {official_label}")
                seen.add(official_label)
                labels_seen[official_label].add(source_label)
                variants[official_label][question["question"]] += 1
                expected_question = (
                    f'Highlight the parts (if any) of this contract related to "{source_label}" '
                    'that should be reviewed by a lawyer. Details: '
                    + table[official_label]["description_exact"]
                )
                require(question["question"] == expected_question,
                        f"Question differs from the official definition: {question['id']}")
            require(seen == table.keys(), f"Missing category questions: {title}")
    require(variants.keys() == table.keys(), "Dataset does not cover the official categories.")

    categories = []
    for official_label in sorted(table):
        require(len(variants[official_label]) == 1,
                f"Multiple question wordings for: {official_label}")
        require(len(labels_seen[official_label]) == 1,
                f"Multiple source label spellings for: {official_label}")
        source_label = next(iter(labels_seen[official_label]))
        question, count = next(iter(variants[official_label].items()))
        categories.append({
            "source_question_label": source_label,
            "official_table_label": official_label,
            "mapping_kind": "exact" if source_label == official_label else "explicit_capitalization_alias",
            "question_exact": question,
            "original_question_records": count,
            **table[official_label],
        })
    return categories


def save_outputs(outputs):
    # Check both outputs before creating either. Preserve unfamiliar existing data.
    for path, payload in outputs.items():
        if path.exists():
            require(path.read_bytes() == payload, f"Existing file differs; it was not replaced: {path}")
    created = 0
    for path, payload in outputs.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(payload)
            created += 1
    return created


def main():
    repo_root = Path(__file__).resolve().parents[2]
    full, _, _, provenance = load_sources(repo_root)
    print("Pinned CUAD source and official splits: verified")
    source = provenance["official_archive"]
    require(re.fullmatch(r"[0-9a-f]{40}", source["revision"]), "Expected a full official Git revision.")
    source_url = f"https://raw.githubusercontent.com/{source['repo_id']}/{source['revision']}/{TABLE_FILENAME}"
    official_dir = (repo_root / provenance["files"]["train"]["path"]).parent
    table_path = official_dir / TABLE_FILENAME
    report_path = (repo_root / "data/processed/cuad/category_audit.json").resolve()
    require(report_path.is_relative_to(repo_root / "data"), "Report must be inside data/.")
    if table_path.exists():
        print("Checking the previously downloaded official category table...")
        with table_path.open("rb") as source_file:
            payload = source_file.read(MAX_TABLE_BYTES + 1)
    else:
        print("Downloading the pinned official category table (about 9 KB)...")
        with urlopen(source_url, timeout=30) as response:
            payload = response.read(MAX_TABLE_BYTES + 1)
    require(len(payload) <= MAX_TABLE_BYTES, "Category table exceeds the download limit.")
    table = parse_table(payload)
    categories = audit_categories(full, table)
    counts = Counter(category["mapping_kind"] for category in categories)
    questions = sum(category["original_question_records"] for category in categories)
    report = {
        "audit_version": 1,
        "purpose": "CUAD_source_category_and_question_audit_only",
        "provenance": provenance,
        "category_table_source": {
            "repo_id": source["repo_id"],
            "revision": source["revision"],
            "filename": TABLE_FILENAME,
            "url": source_url,
            "sha256": sha256(payload),
            "size_bytes": len(payload),
            "local_path": table_path.relative_to(repo_root).as_posix(),
        },
        "summary": {
            "source_documents": len(full),
            "category_count": len(categories),
            "original_question_records": questions,
            "exact_name_matches": counts["exact"],
            "explicit_capitalization_aliases": counts["explicit_capitalization_alias"],
            "unknown_labels": 0,
            "question_definition_mismatches": 0,
        },
        "categories": categories,
    }
    report_bytes = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    created = save_outputs({table_path: payload, report_path: report_bytes})
    print("Category table checksum: matches the pinned checksum")
    print(f"Official category definitions: {len(table)}")
    print(f"Dataset categories: {len(categories)}")
    print(f"Exact category-name matches: {counts['exact']}")
    print(f"Explicit capitalization aliases: {counts['explicit_capitalization_alias']}")
    print(f"Original questions checked: {questions:,}")
    print(f"Categories with one consistent question: {len(categories)}")
    print("Unknown labels: 0")
    print("Question-definition mismatches: 0")
    print(f"Source table: {table_path.relative_to(repo_root).as_posix()}")
    print(f"Audit report: {report_path.relative_to(repo_root).as_posix()}")
    print(f"Created {created} files." if created else "Existing outputs match; no files changed.")
    print("PASS: all 41 CUAD category definitions and exact questions verified.")
    print("Source annotations, document groups, and splits unchanged; product catalogue still pending.")


if __name__ == "__main__":
    main()
