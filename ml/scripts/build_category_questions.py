"""Build the versioned category-to-question lookup for catalogue 1.0.0.

Run from the repository root: python ml/scripts/build_category_questions.py
Output: ml/configs/category_questions.json (commit this small configuration).
Uses existing local CUAD files; no downloads, model, or new dependencies.

CUAD questions are copied exactly from verified source records, not rewritten
from display labels. India prompts match the five definitions in
docs/ml/CategoryCatalogue.md. They have no CUAD annotations: their missing labels
must never become negative examples. This file is not the separate Indian-study
annotation export contract or a replacement for its five CUAD study prompts.

This only creates question metadata. It does not prepare examples, assign
splits, adjudicate duplicate labels, or enable extraction. An existing output
with different content is preserved and causes an error.
"""

import json
from pathlib import Path
import re

from audit_cuad_categories import TABLE_SHA256, audit_categories, parse_table
from audit_cuad_questions import require
from build_cuad_inventory import load_sources, sha256
from check_catalogue import CATALOGUE_VERSION, CUAD_IDS, INDIA_IDS, read_json, validate_catalogue


QUESTION_SET_VERSION = "1.0.0"
INDIA_QUESTIONS = {
    "in.arbitration": "Which text provides for arbitration of disputes?",
    "in.seat_venue": "Which text states the seat or venue of arbitration?",
    "in.stamping_registration": "Which text addresses stamp duty, stamping or registration?",
    "in.forum_selection": "Which text selects courts or a judicial forum for disputes?",
    "in.dispute_escalation": "Which text requires negotiation, mediation or another step before formal dispute resolution?",
}


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def check_india_prompts(repo_root):
    note = (repo_root / "docs/ml/CategoryCatalogue.md").read_text(encoding="utf-8-sig")
    pairs = re.findall(r"^\| `(in\.[a-z_]+)` \| ([^|\r\n]+) \|$", note, flags=re.MULTILINE)
    require(len(pairs) == 5 and len(dict(pairs)) == 5, "Expected five unique India prompt definitions.")
    require(dict(pairs) == INDIA_QUESTIONS, "India prompt definitions changed; review the question-set version.")
    require(set(INDIA_QUESTIONS) == set(INDIA_IDS.values()), "India prompts do not match the catalogue IDs.")


def build_question_rows(catalogue_rows, audited):
    by_id = {}
    for item in audited:
        label = item["official_table_label"]
        require(label in CUAD_IDS, f"Unknown official CUAD category: {label}")
        category_id = CUAD_IDS[label]
        require(category_id not in by_id, "Repeated CUAD category mapping.")
        by_id[category_id] = item
    require(set(by_id) == set(CUAD_IDS.values()), "Incomplete CUAD question mapping.")

    rows = []
    for category in catalogue_rows:
        category_id = category["id"]
        if category["source"] == "cuad":
            item = by_id[category_id]
            require(item["official_table_label"] == category["display_name"], "CUAD label mapping changed.")
            row = {
                "category_id": category_id,
                "question": item["question_exact"],
                "question_role": "cuad_benchmark",
                "source_label": item["source_question_label"],
                "cuad_annotated": True,
            }
        else:
            require(category["source"] == "india_extension" and category_id in INDIA_QUESTIONS,
                    f"Unknown India extension: {category_id}")
            row = {
                "category_id": category_id,
                "question": INDIA_QUESTIONS[category_id],
                "question_role": "india_extension",
                "source_label": None,
                "cuad_annotated": False,
            }
        require(isinstance(row["question"], str) and row["question"].strip(), "Empty question.")
        rows.append(row)
    require(len(rows) == len({row["category_id"] for row in rows}) == 46,
            "Expected one question for each of 46 unique category IDs.")
    require(sum(row["cuad_annotated"] for row in rows) == 41, "Expected 41 CUAD-annotated categories.")
    return rows


def save_questions(path, document):
    if path.exists():
        require(read_json(path) == document,
                f"Existing question set differs; it was not replaced: {path}")
        return "Existing question set matches; no files changed."
    payload = (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(payload)
    return "Question set created."


def main():
    repo_root = Path(__file__).resolve().parents[2]
    catalogue = read_json(repo_root / "ml/configs/catalogue.json")
    catalogue_rows = validate_catalogue(catalogue)
    check_india_prompts(repo_root)
    full, _, _, provenance = load_sources(repo_root)
    table_path = (repo_root / provenance["files"]["train"]["path"]).parent / "category_descriptions.csv"
    require(table_path.is_file(), "Run audit_cuad_categories.py to obtain the category table first.")
    audited = audit_categories(full, parse_table(table_path.read_bytes()))
    rows = build_question_rows(catalogue_rows, audited)
    document = {
        "schema_version": 1,
        "question_set_version": QUESTION_SET_VERSION,
        "catalogue_version": CATALOGUE_VERSION,
        "catalogue_content_sha256": sha256(canonical_bytes(catalogue)),
        "content_digest_encoding": "UTF-8 JSON with sorted keys, ensure_ascii=False, compact separators; no trailing newline",
        "provenance": {
            "cuad": provenance,
            "category_table_sha256": TABLE_SHA256,
            "cuad_attribution": "docs/data attribution: data/raw/cuad/README.md; CUAD by The Atticus Project, CC BY 4.0",
            "india_prompts": {
                "document": "docs/ml/CategoryCatalogue.md",
                "section": "Stable identity and source questions",
                "prompt_map_content_sha256": sha256(canonical_bytes(INDIA_QUESTIONS)),
            },
        },
        "usage": {
            "cuad_questions": "Preserve exact source wording for benchmark preparation; do not reconstruct from display names.",
            "india_questions": "Project extension prompts; no CUAD annotations exist for these categories.",
            "cuad_annotated": "Annotation coverage only, not model support or per-record eligibility after duplicate review.",
            "missing_labels": "Unannotated categories are unknown, never negative examples.",
            "annotation_study": "The Indian-study export schema and its five CUAD study prompts are separate contracts.",
        },
        "questions": rows,
    }
    output = repo_root / "ml/configs/category_questions.json"
    result = save_questions(output, document)
    print(f"Catalogue version: {CATALOGUE_VERSION}")
    print(f"Question-set version: {QUESTION_SET_VERSION}")
    print(f"Unique category-to-question mappings: {len(rows)}")
    print("CUAD questions copied exactly from verified source: 41")
    print("India-extension prompts matched to project definitions: 5")
    print("India categories marked unannotated in CUAD: 5")
    print("Question order matches catalogue order: yes")
    print(result)
    print(f"Output: {output.relative_to(repo_root).as_posix()}")
    print("PASS: versioned question lookup and source provenance verified.")
    print("No training examples or splits created; catalogue support statuses unchanged.")


if __name__ == "__main__":
    main()
