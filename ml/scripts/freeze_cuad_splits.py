"""Freeze the reviewed CUAD assignment and materialize four logical partitions.

Run: python ml/scripts/freeze_cuad_splits.py
Requires the existing preparation/proposal outputs and cuad_split_freeze.json.
Writes ignored data/processed/cuad/frozen_v1/{manifest,fit,dev_select,dev_cal,
dev_policy}.json. No new dependencies or downloads. Differing existing outputs
are preserved and cause failure.

The tracked freeze configuration adopts one reviewed assignment digest. The
proposal policy and historical review manifests remain unchanged. A freeze
locks membership for later feature preparation; it does not establish baseline
reproduction, tokenizer correctness, trained weights or calibration support.

Each partition retains exact contexts, logical questions, multiple answers and
source identities. No further filtering, label changes or answer expansion.
Only fit is intended for weight training; development roles stay separate.
Future feature builders should use load_frozen_partition() to revalidate the
source-to-proposal-to-freeze chain and reject altered saved partitions.
"""

from copy import deepcopy
import json
from pathlib import Path
import re

from audit_cuad_categories import save_outputs
from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, fields, read_json
from prepare_cuad_pool import OUTPUT_DIR
from propose_cuad_splits import SPLITS, propose


FREEZE_PATH = "ml/configs/cuad_split_freeze.json"
FROZEN_DIR = "data/processed/cuad/frozen_v1"
ROLES = {"fit": "weight_training", "dev_select": "checkpoint_and_decoder_selection",
         "dev_cal": "calibrator_fitting", "dev_policy": "operating_threshold_selection"}
FIXED = {"freeze_version": "1.0.0", "split_id": "cuad-clean-v1", "scope": "partition_membership_only"}
DIGESTS = ("assignment_canonical_sha256", "proposal_canonical_sha256", "proposal_report_canonical_sha256",
           "proposal_policy_canonical_sha256", "preparation_pool_canonical_sha256")


def validate_freeze(freeze, pool, proposal, report):
    fields(freeze, set(FIXED) | set(DIGESTS) | {"reviewed_proposal_commit", "partition_roles", "support_limitations"},
           "split freeze")
    require(canonical_sha256({k: freeze[k] for k in FIXED}) == canonical_sha256(FIXED),
            "Unsupported freeze version, identity or scope.")
    require(type(freeze["reviewed_proposal_commit"]) is str
            and re.fullmatch(r"[0-9a-f]{40}", freeze["reviewed_proposal_commit"]),
            "Expected the full reviewed proposal commit.")
    require(canonical_sha256(freeze["partition_roles"]) == canonical_sha256(ROLES), "Partition roles changed.")
    require(proposal["status"] == "awaiting_review_and_freeze" and proposal["ready_for_training"] is False,
            "Expected an unmodified proposal snapshot.")
    require(freeze["proposal_canonical_sha256"] == canonical_sha256(proposal)
            == report["proposal_canonical_sha256"], "Frozen proposal digest differs.")
    require(freeze["proposal_report_canonical_sha256"] == canonical_sha256(report), "Reviewed support report differs.")
    require(freeze["assignment_canonical_sha256"] == proposal["assignment_canonical_sha256"]
            == canonical_sha256(proposal["assignments"]), "Reviewed assignment digest differs.")
    require(freeze["preparation_pool_canonical_sha256"] == proposal["preparation_pool_canonical_sha256"]
            == canonical_sha256(pool), "Frozen preparation pool differs.")
    require(freeze["proposal_policy_canonical_sha256"] == proposal["policy_canonical_sha256"]
            == canonical_sha256(report["policy"]), "Frozen proposal policy differs.")
    annotated = [r for r in report["category_support"] if r["annotation_status"] == "cuad_annotated"]
    no_negatives = sorted(r["category_id"] for r in annotated
                          if all(r["splits"][s]["no_answer_questions"] == 0 for s in SPLITS))
    require(no_negatives == ["cuad.document_name", "cuad.parties"]
            and all(r["splits"]["dev_cal"]["questions"] < 50 for r in annotated),
            "Reviewed support limitations changed; revise the freeze before proceeding.")
    expected_limits = {"categories_without_no_answer_examples_in_all_partitions": no_negatives,
                       "per_category_presence_calibration_size_gate_met": False,
                       "model_based_support_assessed": False}
    require(canonical_sha256(freeze["support_limitations"]) == canonical_sha256(expected_limits),
            "Freeze support limitations differ from the reviewed counts.")


def build_bundle(freeze, pool, proposal, report):
    """Construct immutable logical partitions, with independent membership checks."""
    validate_freeze(freeze, pool, proposal, report)
    by_group = {g["group_id"]: g for g in pool["groups"]}
    require(len(by_group) == len(pool["groups"]), "Repeated group in preparation pool.")
    by_family = {}
    for g in pool["groups"]:
        require(g["official_split"] == "train", "Official test cannot enter frozen internal partitions.")
        by_family.setdefault(g["family_id"], []).append(g["group_id"])
    selected = {s: [] for s in SPLITS}
    seen_families, seen_groups = set(), set()
    for a in proposal["assignments"]:
        fields(a, {"family_id", "proposed_split", "group_ids", "source_titles"}, "assignment")
        fid, split = a["family_id"], a["proposed_split"]
        require(split in SPLITS and fid in by_family and fid not in seen_families, "Invalid or repeated family assignment.")
        require(a["group_ids"] == sorted(by_family[fid]), "Assignment does not preserve a complete family.")
        require(a["source_titles"] == sorted(t for gid in a["group_ids"] for t in by_group[gid]["source_titles"]),
                "Assignment source identities differ.")
        seen_families.add(fid)
        for gid in a["group_ids"]:
            require(gid not in seen_groups, "Group assigned more than once.")
            seen_groups.add(gid)
            selected[split].append(by_group[gid])
    require(seen_groups == set(by_group) and seen_families == set(by_family), "Assignments omit eligible pool members.")
    common = {"split_id": freeze["split_id"], "freeze_canonical_sha256": canonical_sha256(freeze),
              "assignment_canonical_sha256": freeze["assignment_canonical_sha256"],
              "preparation_pool_canonical_sha256": freeze["preparation_pool_canonical_sha256"]}
    bundle, entries = {}, {}
    for split in SPLITS:
        groups = sorted(selected[split], key=lambda g: g["group_id"])
        require(bool(groups), "Frozen partition is empty.")
        questions = [q for g in groups for p in g["paragraphs"] for q in p["questions"]]
        counts = {"source_documents": sum(len(g["source_titles"]) for g in groups), "exact_text_groups": len(groups),
                  "family_units": len({g["family_id"] for g in groups}), "questions": len(questions),
                  "positive_questions": sum(bool(q["answers"]) for q in questions),
                  "no_answer_questions": sum(not q["answers"] for q in questions),
                  "answer_spans": sum(len(q["answers"]) for q in questions)}
        require(canonical_sha256(counts) == canonical_sha256({k: report["summary"][split][k] for k in counts}),
                "Materialized partition counts differ from the reviewed report.")
        value = {**common, "partition": split, "intended_role": ROLES[split],
                 "purpose": "logical_questions_for_feature_preparation", "tokenized": False,
                 "source_bindings": deepcopy(pool["bindings"]), "span_coordinates": pool["span_coordinates"],
                 "groups": deepcopy(groups)}
        filename = split + ".json"
        bundle[filename] = value
        entries[split] = {"file": filename, "canonical_sha256": canonical_sha256(value), "summary": counts}
    bundle["manifest.json"] = {
        **common, "frozen_manifest_version": "1.0.0", "status": "membership_frozen",
        "scope": freeze["scope"], "partitions": entries,
        "reviewed_proposal_commit": freeze["reviewed_proposal_commit"],
        "proposal_canonical_sha256": freeze["proposal_canonical_sha256"],
        "proposal_report_canonical_sha256": freeze["proposal_report_canonical_sha256"],
        "support_limitations": deepcopy(freeze["support_limitations"]),
    }
    return bundle


def verified_inputs(repo):
    expected_proposal, expected_report = propose(repo)
    proposal = read_json(repo / OUTPUT_DIR / "split_proposal.json")
    report = read_json(repo / OUTPUT_DIR / "split_report.json")
    require(canonical_sha256(proposal) == canonical_sha256(expected_proposal)
            and canonical_sha256(report) == canonical_sha256(expected_report),
            "Saved split proposal/report differ from verified reconstruction.")
    return (read_json(repo / FREEZE_PATH), read_json(repo / OUTPUT_DIR / "preparation_pool.json"), proposal, report)


def write_bundle(directory, bundle):
    payloads = {directory / name: (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
                for name, value in bundle.items()}
    return save_outputs(payloads)


def validate_saved_bundle(directory, expected):
    """Verify against source reconstruction, not just checksums stored beside data."""
    actual = {}
    for name, value in expected.items():
        path = directory / name
        require(path.is_file(), f"Missing frozen file: {name}. Run freeze_cuad_splits.py first.")
        actual[name] = read_json(path)
        require(canonical_sha256(actual[name]) == canonical_sha256(value), f"Frozen file differs: {name}")
    return actual


def load_frozen_partition(repo, partition):
    """Source-verified input for later feature preparation; no training approval."""
    require(partition in SPLITS, "Unknown internal partition.")
    expected = build_bundle(*verified_inputs(repo))
    return validate_saved_bundle(repo / FROZEN_DIR, expected)[partition + ".json"]


def main():
    repo = Path(__file__).resolve().parents[2]
    bundle = build_bundle(*verified_inputs(repo))
    directory = (repo / FROZEN_DIR).resolve()
    require(directory.is_relative_to((repo / "data").resolve()), "Frozen output must stay inside repository data/.")
    created = write_bundle(directory, bundle)
    validate_saved_bundle(directory, bundle)
    manifest = bundle["manifest.json"]
    print("Source-to-preparation-to-proposal chain and reviewed freeze digests: verified")
    print(f"Frozen split: {manifest['split_id']}; membership only")
    for split in SPLITS:
        c = manifest["partitions"][split]["summary"]
        print(f"{split}: {c['source_documents']} source documents; {c['exact_text_groups']} exact groups; "
              f"{c['family_units']} families; {c['questions']} questions")
    print(f"Assignment SHA-256: {manifest['assignment_canonical_sha256']}")
    print("Source text, questions, answer occurrences, holds and partition roles: preserved")
    print("Support limitations retained: eight no-answer gaps; per-category presence calibration size gate unmet")
    print(f"Created {created} frozen files." if created else "Existing frozen files match; no files changed.")
    print(f"Output: {FROZEN_DIR}/ (manifest.json plus four partition files)")
    print("PASS: frozen partitions verified, disjoint and complete; official sources unchanged.")
    print("Baseline reproduction, tokenizer features and model training remain pending.")


if __name__ == "__main__":
    main()
