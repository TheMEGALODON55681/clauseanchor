"""Apply reviewed CUAD holds and deduplication before assigning internal splits.

Run: python ml/scripts/prepare_cuad_pool.py
Requires the existing pinned data, category table, question lookup and v2 review
manifest. No downloads or new dependencies. Outputs under ignored
data/processed/cuad/: preparation_pool.json and preparation_report.json.
Different existing outputs are never overwritten.

The pool contains eligible official-training exact-text groups only. Related
groups share a family ID but their contexts and annotations stay separate.
Agreeing duplicate questions become one logical question with all original IDs;
all answer occurrences (including multiplicity) remain intact. Disputed
questions are omitted, never converted into negative examples. India-extension
questions have no CUAD labels and are not inserted into this pool.

This is an unassigned logical-question pool, not tokenizer features or a fitted
model. Do not train on the whole pool. Internal fit/dev_select/dev_cal/dev_policy
assignment and category-support review remain separate steps. Official baseline
reproduction must continue to use the original official files.
"""

from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path

from audit_cuad_categories import TABLE_SHA256, audit_categories, parse_table, save_outputs
from audit_cuad_questions import annotation_signature, contexts, require
from build_category_questions import QUESTION_SET_VERSION, build_question_rows, check_india_prompts
from build_cuad_inventory import build_groups, load_sources, question_index, sha256
from check_catalogue import CATALOGUE_VERSION, validate_catalogue
from check_cuad_families import REPORT_PATH, canonical_sha256, family_id, read_json
from cuad_review_policy import LEGACY_PATH, TITLE_PATH, preparation_view, validate_review_manifest


POOL_VERSION = "1.0.0"
MANIFEST_PATH = "ml/configs/cuad_family_manifest.json"
QUESTIONS_PATH = "ml/configs/category_questions.json"
OUTPUT_DIR = "data/processed/cuad"


def validate_questions(catalogue, lookup, full, provenance, table_bytes):
    """Bind every category and exact prompt to the verified source definitions."""
    rows = validate_catalogue(catalogue)
    audited = audit_categories(full, parse_table(table_bytes))
    expected = build_question_rows(rows, audited)
    require(type(lookup["schema_version"]) is int and lookup["schema_version"] == 1
            and lookup["question_set_version"] == QUESTION_SET_VERSION
            and lookup["catalogue_version"] == CATALOGUE_VERSION,
            "Question lookup version changed.")
    require(lookup["catalogue_content_sha256"] == canonical_sha256(catalogue),
            "Question lookup catalogue binding differs.")
    require(canonical_sha256(lookup["provenance"]["cuad"]) == canonical_sha256(provenance)
            and lookup["provenance"]["category_table_sha256"] == TABLE_SHA256,
            "Question lookup source binding differs.")
    require(canonical_sha256(lookup["questions"]) == canonical_sha256(expected),
            "Question lookup differs from the audited source definitions.")
    return expected


def build_pool(full, groups, view, questions, holds):
    """Build from source-derived groups and an already validated policy view."""
    by_id = {g["group_id"]: g for g in groups}
    by_label = {q["source_label"]: q for q in questions if q["cuad_annotated"]}
    require(len(by_label) == sum(q["cuad_annotated"] for q in questions),
            "Duplicate source labels in question mapping.")
    held = {(h["group_id"], h["paragraph_index"], h["source_label"]): h for h in holds}
    require(len(held) == len(holds), "Duplicate question hold.")
    support = {q["category_id"]: Counter() for q in questions}
    annotated_families, positive_families = defaultdict(set), defaultdict(set)
    counts = Counter()
    output, seen_groups, seen_holds = [], set(), set()
    for component in sorted(view["eligible_components"]):
        fid = family_id(sorted(component))
        require(bool(component), "Empty eligible component.")
        for gid in sorted(component):
            require(gid not in seen_groups, "Group occurs in multiple eligible components.")
            seen_groups.add(gid)
            g = by_id[gid]
            require(g["official_split"] == "train", "Official test cannot enter the preparation pool.")
            require(gid not in view["reserved_training_groups"], "Reserved group cannot enter the pool.")
            titles = sorted(d["title"] for d in g["source_documents"])
            source = full[titles[0]]
            indices = {title: question_index(full[title]) for title in titles}
            signatures = {title: annotation_signature(full[title]) for title in titles}
            require(all(contexts(full[t]) == contexts(source) for t in titles),
                    "Exact-text group contexts differ.")
            counts["source_documents"] += len(titles)
            counts["original_questions_before_question_holds"] += sum(len(qs) for qs in indices.values())
            paragraphs = []
            for index, paragraph in enumerate(source["paragraphs"]):
                context = paragraph["context"]
                expected_keys = {(index, label) for label in by_label}
                require(all({key for key in qs if key[0] == index} == expected_keys
                            for qs in indices.values()), "Missing or extra annotated category questions.")
                prepared_questions = []
                for label, mapping in sorted(by_label.items()):
                    key, hold_key = (index, label), (gid, index, label)
                    originals = [{"source_title": title, "source_question_id": indices[title][key]["id"]}
                                 for title in titles]
                    if hold_key in held:
                        hold = held[hold_key]
                        require(hold["category_id"] == mapping["category_id"]
                                and hold["source_question_ids"] == sorted(q["source_question_id"] for q in originals),
                                "Question hold identity differs.")
                        seen_holds.add(hold_key)
                        counts["held_original_question_records"] += len(originals)
                        counts["held_group_category_questions"] += 1
                        continue
                    require(all(signatures[t][key] == signatures[titles[0]][key] for t in titles),
                            "Unheld duplicate annotations disagree.")
                    q = indices[titles[0]][key]
                    require(q["question"] == mapping["question"], "Exact source question differs from lookup.")
                    require(type(q["is_impossible"]) is bool and q["is_impossible"] == (not q["answers"]),
                            "Source answer state differs.")
                    answers = []
                    for answer in sorted(q["answers"], key=lambda a: (a["answer_start"], a["text"])):
                        start, text = answer["answer_start"], answer["text"]
                        require(type(start) is int and isinstance(text, str) and bool(text), "Invalid source span.")
                        end = start + len(text)
                        require(0 <= start < end <= len(context) and context[start:end] == text,
                                "Source answer span does not match exact context.")
                        answers.append({"start": start, "end": end, "text": text})
                    category_id = mapping["category_id"]
                    prepared_questions.append({
                        "question_id": "cuad-pool-question-v1:" + canonical_sha256([gid, index, category_id]),
                        "category_id": category_id, "source_label": label,
                        "question": q["question"], "is_impossible": q["is_impossible"],
                        "answers": answers, "source_questions": originals,
                    })
                    stat = support[category_id]
                    stat["questions"] += 1
                    stat["positive_questions" if answers else "no_answer_questions"] += 1
                    stat["answer_spans"] += len(answers)
                    annotated_families[category_id].add(fid)
                    if answers:
                        positive_families[category_id].add(fid)
                    counts["deduplicated_original_question_records"] += len(originals) - 1
                paragraphs.append({"index": index, "context": context,
                                   "code_points": len(context), "text_sha256": sha256(context.encode("utf-8")),
                                   "questions": prepared_questions})
            output.append({"group_id": gid, "family_id": fid, "official_split": "train",
                           "source_titles": titles, "paragraphs": paragraphs})
    applicable_holds = {key for key in held if key[0] in seen_groups}
    require(seen_holds == applicable_holds, "An eligible-group question hold was not applied.")
    support_rows = []
    for q in questions:
        cid = q["category_id"]
        support_rows.append({
            "category_id": cid,
            "annotation_status": "cuad_annotated" if q["cuad_annotated"] else "unannotated_in_cuad",
            **{k: support[cid][k] for k in ("questions", "positive_questions", "no_answer_questions", "answer_spans")},
            "annotated_family_units": len(annotated_families[cid]),
            "positive_family_units": len(positive_families[cid]),
        })
    summary = {key: counts[key] for key in (
        "source_documents", "original_questions_before_question_holds", "held_original_question_records",
        "held_group_category_questions", "deduplicated_original_question_records")}
    summary.update({"exact_text_groups": len(output), "family_units": len(view["eligible_components"])})
    summary.update({key: sum(row[key] for row in support_rows)
                    for key in ("questions", "positive_questions", "no_answer_questions", "answer_spans")})
    require(summary["original_questions_before_question_holds"] == summary["questions"]
            + summary["held_original_question_records"] + summary["deduplicated_original_question_records"],
            "Prepared question accounting differs.")
    return sorted(output, key=lambda g: g["group_id"]), summary, support_rows


def prepare(repo):
    """Validate all inputs before creating any derived output."""
    full, train, test, provenance = load_sources(repo)
    groups = build_groups(full, train, test)
    manifest, legacy = read_json(repo / MANIFEST_PATH), read_json(repo / LEGACY_PATH)
    verified = validate_review_manifest(manifest, legacy, read_json(repo / REPORT_PATH),
                                       read_json(repo / TITLE_PATH), groups, provenance, evidence_root=repo)
    catalogue, lookup = read_json(repo / "ml/configs/catalogue.json"), read_json(repo / QUESTIONS_PATH)
    table = (repo / provenance["files"]["train"]["path"]).parent / "category_descriptions.csv"
    require(table.is_file(), "Missing category table. Run python ml/scripts/audit_cuad_categories.py first.")
    check_india_prompts(repo)
    questions = validate_questions(catalogue, lookup, full, provenance, table.read_bytes())
    confirmed = [d["group_ids"] for f in legacy["families"] for d in f["decisions"]]
    confirmed += [d["group_ids"] for d in manifest["title_decisions"] if d["decision"] == "confirmed"]
    unresolved = [d["group_ids"] for d in manifest["title_decisions"] if d["decision"] == "unresolved"]
    view = preparation_view(groups, confirmed, unresolved)
    prepared, summary, support = build_pool(full, groups, view, questions, manifest["question_holds"])
    for actual, expected in (("source_documents", "prospective_eligible_training_documents"),
                             ("exact_text_groups", "prospective_eligible_exact_groups"),
                             ("family_units", "prospective_internal_family_units")):
        require(summary[actual] == verified[expected], "Prepared pool differs from validated eligibility.")
    bindings = {
        "source": provenance, "family_manifest_version": manifest["manifest_version"],
        "family_manifest_canonical_sha256": canonical_sha256(manifest),
        "question_set_version": lookup["question_set_version"],
        "question_set_canonical_sha256": canonical_sha256(lookup),
        "catalogue_canonical_sha256": canonical_sha256(catalogue),
    }
    pool = {
        "pool_version": POOL_VERSION, "purpose": "filtered_unassigned_cuad_training_pool",
        "bindings": bindings,
        "span_coordinates": "zero-based paragraph-relative Unicode code points; end exclusive",
        "preparation_status": {"document_holds_applied": True, "question_holds_applied": True,
                               "agreeing_duplicate_questions_deduplicated": True,
                               "internal_partitions_assigned": False, "tokenized": False,
                               "ready_for_training": False},
        "groups": prepared,
    }
    by_id = {g["group_id"]: g for g in groups}
    def titles(ids):
        return sorted(d["title"] for gid in ids for d in by_id[gid]["source_documents"])
    unresolved_test = sorted({gid for edge in unresolved for gid in edge if by_id[gid]["official_split"] == "test"})
    reservations = [{"group_id": gid, "source_titles": titles([gid]),
                     "confirmed_cross_split": gid in view["cross_split_groups"],
                     "unresolved_family_hold": gid in view["document_holds"]}
                    for gid in view["reserved_training_groups"]]
    report = {
        "report_version": POOL_VERSION, "pool_canonical_sha256": canonical_sha256(pool),
        "bindings": deepcopy(bindings), "summary": summary, "validated_policy_summary": verified,
        "reserved_training_groups": reservations, "question_holds": deepcopy(manifest["question_holds"]),
        "category_support": support,
        "benchmark_membership": {
            "full_official_test_source_titles": sorted(test),
            "known_overlap_excluded_sensitivity_source_titles": titles(view["sensitivity_test_groups"]),
            "unresolved_test_source_titles_retained_in_both": titles(unresolved_test),
        },
        "limitations": [
            "Whole-pool counts are not fit/development support or model performance.",
            "No internal assignments or tokenizer features; do not train on the entire pool.",
            "Official baseline reproduction still uses the unchanged official source files.",
            "Known-overlap sensitivity does not establish absence of unknown overlap.",
        ],
    }
    return pool, report


def write_preparation(repo, pool, report):
    output_dir = (repo / OUTPUT_DIR).resolve()
    require(output_dir.is_relative_to((repo / "data").resolve()), "Output must stay inside repository data/.")
    outputs = {output_dir / name: (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
               for name, value in (("preparation_pool.json", pool), ("preparation_report.json", report))}
    return save_outputs(outputs)


def main():
    repo = Path(__file__).resolve().parents[2]
    pool, report = prepare(repo)
    created = write_preparation(repo, pool, report)
    s = report["summary"]
    print("Pinned sources, reviewed policy, category definitions and question lookup: verified")
    print(f"Prepared pool: {s['source_documents']} source documents; {s['exact_text_groups']} exact groups; {s['family_units']} family units")
    print(f"Training documents reserved: {report['validated_policy_summary']['prospective_training_exclusions']}")
    print(f"Question holds applied in eligible groups: {s['held_original_question_records']} original records; {s['held_group_category_questions']} group/category questions")
    print(f"Agreeing duplicate question records removed: {s['deduplicated_original_question_records']}")
    print(f"Prepared logical questions: {s['questions']} ({s['positive_questions']} positive; {s['no_answer_questions']} no-answer)")
    print(f"Exact answer occurrences preserved: {s['answer_spans']}")
    print("Category support recorded for 41 CUAD categories; 5 India categories remain unannotated.")
    print(f"Created {created} preparation files." if created else "Existing preparation outputs match; no files changed.")
    print(f"Outputs: {OUTPUT_DIR}/preparation_pool.json and preparation_report.json")
    print("PASS: holds applied and agreeing questions deduplicated; original source files unchanged.")
    print("No internal partitions or tokenizer features created; do not train on the entire pool.")


if __name__ == "__main__":
    main()
