"""Build a reproducible CUAD exact-text inventory; do not prepare training data.

Run from the repository root: python ml/scripts/build_cuad_inventory.py
Requires the verified official files and audit_cuad_questions.py beside this file.
Output: data/processed/cuad/inventory.json (ignored by Git).

Groups compare the ordered, unmodified paragraph contexts. Group IDs hash their
compact JSON array, encoded as UTF-8 (ensure_ascii=False). Paragraph hashes instead
hash each context's UTF-8 bytes directly. Neither method normalizes the text.
Offsets are paragraph-relative Unicode code points, with exclusive end positions.

This records pending annotation conflicts under docs/ml/CUAD_DataReview.md's
policy. It does not filter examples, merge answers, adjudicate labels, or create
validation/calibration splits. Exact matching is not a near-duplicate audit.
"""

from collections import Counter, defaultdict
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import yaml

from audit_cuad_questions import (
    annotation_signature,
    check_test,
    check_training,
    contexts,
    inspect_records,
    require,
)


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def load_sources(repo_root):
    config = yaml.safe_load(
        (repo_root / "ml/configs/data.yaml").read_text(encoding="utf-8")
    )
    require(config["config_version"] == 1, "Expected config_version: 1")
    raw_dir = (repo_root / config["storage"]["raw_dir"]).resolve()
    official_dir = (repo_root / config["storage"]["official_dir"]).resolve()
    require(raw_dir.is_relative_to(repo_root / "data"), "raw_dir must be inside data/.")
    require(official_dir.is_relative_to(raw_dir), "official_dir must be inside raw_dir.")
    paths = {
        "full": raw_dir / config["cuad"]["filename"],
        "train": official_dir / "train_separate_questions.json",
        "test": official_dir / "test.json",
    }
    manifest = json.loads((raw_dir / "source_manifest.json").read_text(encoding="utf-8"))
    require(manifest["manifest_version"] == 1, "Unsupported source manifest version.")
    for field in ("repo_id", "repo_type", "revision", "filename"):
        require(manifest[field] == config["cuad"][field], f"Source mismatch: {field}")

    source = config["cuad_official"]
    archive_bytes = (official_dir / "data.zip").read_bytes()
    require(sha256(archive_bytes) == source["archive_sha256"], "Archive checksum changed.")
    members = [source[f"{role}_member"] for role in paths]
    require(len(set(members)) == 3, "Expected three distinct archive members.")
    indexed, files = {}, {}
    with ZipFile(io.BytesIO(archive_bytes)) as archive:
        for role, path in paths.items():
            member = source[f"{role}_member"]
            require(archive.namelist().count(member) == 1, f"Ambiguous ZIP member: {member}")
            payload = path.read_bytes()
            require(payload == archive.read(member), f"Local {role} JSON differs from archive.")
            files[role] = {
                "path": path.relative_to(repo_root).as_posix(),
                "archive_member": member,
                "sha256": sha256(payload),
                "size_bytes": len(payload),
            }
            indexed[role], _ = inspect_records(json.loads(payload), role)
    require(files["full"]["sha256"] == manifest["sha256"], "Full-source checksum changed.")
    require(files["full"]["size_bytes"] == manifest["size_bytes"], "Full-source size changed.")

    full, train, test = (indexed[role] for role in ("full", "train", "test"))
    require(not (train.keys() & test.keys()), "Official splits share source titles.")
    require(train.keys() | test.keys() == full.keys(), "Official splits do not cover the source.")
    check_training(train, full)
    check_test(test, full)
    provenance = {
        "full_source": config["cuad"],
        "official_archive": source,
        "files": files,
    }
    return full, train, test, provenance


def question_index(document):
    # annotation_signature validates the prefix and uniqueness of these keys.
    prefix_length = len(document["title"]) + 2
    return {
        (index, question["id"][prefix_length:]): question
        for index, paragraph in enumerate(document["paragraphs"])
        for question in paragraph["qas"]
    }


def build_groups(full, train, test):
    require(not (train.keys() & test.keys()), "Official splits share source titles.")
    require(train.keys() | test.keys() == full.keys(), "Official splits do not cover the source.")
    by_text = defaultdict(list)
    for title, document in full.items():
        by_text[contexts(document)].append(title)

    groups, seen_group_ids = [], set()
    for text_sequence, source_titles in by_text.items():
        titles = sorted(source_titles)
        splits = {"train" if title in train else "test" for title in titles}
        require(len(splits) == 1, "Identical text appears in both official splits.")
        encoded = json.dumps(text_sequence, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        group_id = "cuad-exact-v1:" + sha256(encoded)
        require(group_id not in seen_group_ids, "Group ID collision.")
        seen_group_ids.add(group_id)

        signatures = {title: annotation_signature(full[title]) for title in titles}
        questions = {title: question_index(full[title]) for title in titles}
        keys = set().union(*(signature.keys() for signature in signatures.values()))
        conflicts = []
        for key in sorted(keys):
            if all(signatures[title].get(key) == signatures[titles[0]].get(key) for title in titles[1:]):
                continue
            annotations = []
            for title in titles:
                question = questions[title].get(key)
                # Missing records must remain distinguishable from empty answers.
                entry = {"source_title": title, "record_present": question is not None}
                if question is not None:
                    entry.update({
                        "source_question_id": question["id"],
                        "is_impossible": question["is_impossible"],
                        "spans": sorted(
                            [{"start": a["answer_start"], "end": a["answer_start"] + len(a["text"])}
                             for a in question["answers"]],
                            key=lambda span: (span["start"], span["end"]),
                        ),
                    })
                annotations.append(entry)
            conflicts.append({
                "paragraph_index": key[0],
                "source_label": key[1],
                "review_status": "pending_adjudication",
                "derived_use_policy": "exclude_from_supervised_loss_and_scored_evaluation_until_adjudicated",
                "source_annotations": annotations,
            })
        groups.append({
            "group_id": group_id,
            "official_split": next(iter(splits)),
            "paragraphs": [
                {"index": index, "code_points": len(text), "text_sha256": sha256(text.encode("utf-8"))}
                for index, text in enumerate(text_sequence)
            ],
            "source_documents": [
                {"title": title, "original_question_count": len(questions[title])}
                for title in titles
            ],
            "agreeing_category_question_count": len(keys) - len(conflicts),
            "annotation_conflicts": conflicts,
        })
    return sorted(groups, key=lambda group: group["group_id"])


def summarize(groups):
    documents, split_groups = Counter(), Counter()
    for group in groups:
        split_groups[group["official_split"]] += 1
        documents[group["official_split"]] += len(group["source_documents"])
    conflicts = [conflict for group in groups for conflict in group["annotation_conflicts"]]
    return {
        "source_documents": sum(documents.values()),
        "exact_text_groups": len(groups),
        "documents_by_official_split": dict(sorted(documents.items())),
        "groups_by_official_split": dict(sorted(split_groups.items())),
        "duplicate_text_groups": sum(len(group["source_documents"]) > 1 for group in groups),
        "conflicting_group_category_questions": len(conflicts),
        "original_question_records_flagged": sum(
            annotation["record_present"] for conflict in conflicts
            for annotation in conflict["source_annotations"]
        ),
    }


def save_inventory(path, inventory):
    payload = (json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if path.exists():
        require(path.read_bytes() == payload, f"Existing inventory differs; it was not replaced: {path}")
        return "Existing inventory matches; no files changed."
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(payload)
    return "Inventory created."


def main():
    repo_root = Path(__file__).resolve().parents[2]
    full, train, test, provenance = load_sources(repo_root)
    print("Source bytes, official question layout, and exact answer spans: verified")
    groups = build_groups(full, train, test)
    summary = summarize(groups)
    inventory = {
        "inventory_version": 1,
        "purpose": "exact_text_group_inventory_only",
        "provenance": provenance,
        "group_id_algorithm": "cuad-exact-v1: + SHA-256 of UTF-8 compact JSON array of ordered, unmodified paragraph contexts; ensure_ascii=False",
        "paragraph_hash_algorithm": "SHA-256 of UTF-8 unmodified context",
        "span_coordinates": "zero-based paragraph-relative Unicode code points; end exclusive",
        "review_policy_document": "docs/ml/CUAD_DataReview.md",
        "preparation_status": {
            "label_adjudication": "pending",
            "near_duplicate_and_related_contract_review": "pending",
            "training_examples_filtered": False,
            "agreeing_examples_deduplicated": False,
            "derived_splits_assigned": False,
        },
        "summary": summary,
        "groups": groups,
    }
    output_path = (repo_root / "data/processed/cuad/inventory.json").resolve()
    require(output_path.is_relative_to(repo_root / "data"), "Output must be inside data/.")
    result = save_inventory(output_path, inventory)
    print(f"Source documents: {summary['source_documents']:,}")
    print(f"Exact-text groups: {summary['exact_text_groups']:,}")
    for split in ("train", "test"):
        print(f"Official {split}: {summary['documents_by_official_split'].get(split, 0):,} documents; "
              f"{summary['groups_by_official_split'].get(split, 0):,} groups")
    print(f"Duplicate text groups: {summary['duplicate_text_groups']}")
    print(f"Conflicting group/category questions: {summary['conflicting_group_category_questions']}")
    print(f"Original question records flagged for review: {summary['original_question_records_flagged']}")
    print(result)
    print(f"Output: {output_path.relative_to(repo_root).as_posix()}")
    print("PASS: inventory verified; official source files unchanged.")
    print("No training examples filtered or merged; no derived splits assigned.")


if __name__ == "__main__":
    main()
