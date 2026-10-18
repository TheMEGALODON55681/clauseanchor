"""Read-only audit of CUAD question expansion, spans, and exact duplicates."""

from collections import Counter, defaultdict
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import yaml


def require(condition, message):
    if not condition:
        raise ValueError(message)


def answer_counts(answers):
    # Order is irrelevant; positions, text, and duplicate counts are preserved.
    return Counter((answer["answer_start"], answer["text"]) for answer in answers)


def question_metadata(question, ignore_id=False):
    excluded = {"answers", "id"} if ignore_id else {"answers"}
    return {key: value for key, value in question.items() if key not in excluded}


def inspect_records(dataset, label):
    documents = dataset["data"]
    require(isinstance(documents, list) and documents, f"{label}: no documents.")
    indexed = {}
    seen_ids = set()
    counts = Counter()
    for document in documents:
        title = document["title"]
        require(isinstance(title, str) and title, f"{label}: invalid title.")
        require(title not in indexed, f"{label}: duplicate title: {title}")
        indexed[title] = document
        require(document["paragraphs"], f"{label}: document has no paragraphs.")
        for paragraph in document["paragraphs"]:
            context = paragraph["context"]
            require(isinstance(context, str), f"{label}: invalid context.")
            require(paragraph["qas"], f"{label}: paragraph has no questions.")
            for question in paragraph["qas"]:
                qid = question["id"]
                require(isinstance(qid, str) and qid, f"{label}: invalid question id.")
                require(qid not in seen_ids, f"{label}: duplicate question id: {qid}")
                seen_ids.add(qid)
                require(isinstance(question["question"], str), f"Invalid question: {qid}")
                answers = question["answers"]
                require(isinstance(answers, list), f"Invalid answers: {qid}")
                require(
                    type(question["is_impossible"]) is bool
                    and question["is_impossible"] == (not answers),
                    f"Answer state disagrees with the annotations: {qid}",
                )
                counts["questions"] += 1
                counts["empty" if not answers else "single" if len(answers) == 1 else "multi"] += 1
                for answer in answers:
                    start, text = answer["answer_start"], answer["text"]
                    valid = (
                        type(start) is int and isinstance(text, str) and bool(text)
                        and 0 <= start and start + len(text) <= len(context)
                        and context[start:start + len(text)] == text
                    )
                    require(valid, f"{label}: invalid answer span: {qid}")
                    counts["spans"] += 1
    return indexed, counts


def paired_paragraphs(document, original):
    actual = document["paragraphs"]
    expected = original["paragraphs"]
    require(len(actual) == len(expected), "Paragraph counts differ from the source.")
    for paragraph, source_paragraph in zip(actual, expected, strict=True):
        require(
            paragraph["context"] == source_paragraph["context"],
            f"Context differs from the source: {document['title']}",
        )
        yield paragraph, source_paragraph


def check_training(train, full):
    logical_questions = 0
    for title, document in train.items():
        for paragraph, source_paragraph in paired_paragraphs(document, full[title]):
            originals = {q["id"]: q for q in source_paragraph["qas"]}
            groups = defaultdict(dict)
            for question in paragraph["qas"]:
                base_id, separator, suffix = question["id"].rpartition("_")
                require(separator and suffix.isdecimal(), "Missing training record suffix.")
                require(base_id in originals, f"Unknown source question: {base_id}")
                number = int(suffix)
                require(number not in groups[base_id], f"Repeated training suffix: {base_id}")
                groups[base_id][number] = question
            require(groups.keys() == originals.keys(), "Training source questions differ.")
            for qid, original in originals.items():
                records = groups[qid]
                expected_count = max(1, len(original["answers"]))
                require(set(records) == set(range(expected_count)), f"Missing training rows: {qid}")
                combined_answers = []
                for record in records.values():
                    require(
                        question_metadata(record, ignore_id=True)
                        == question_metadata(original, ignore_id=True),
                        f"Training question metadata differs: {qid}",
                    )
                    require(
                        len(record["answers"]) == int(bool(original["answers"])),
                        f"Expected one answer per positive training row: {qid}",
                    )
                    combined_answers.extend(record["answers"])
                require(
                    answer_counts(combined_answers) == answer_counts(original["answers"]),
                    f"Training answers differ from the source: {qid}",
                )
                logical_questions += 1
    return logical_questions


def check_test(test, full):
    for title, document in test.items():
        for paragraph, source_paragraph in paired_paragraphs(document, full[title]):
            originals = {q["id"]: q for q in source_paragraph["qas"]}
            actual = {q["id"]: q for q in paragraph["qas"]}
            require(actual.keys() == originals.keys(), "Test source questions differ.")
            for qid, question in actual.items():
                original = originals[qid]
                require(
                    question_metadata(question) == question_metadata(original),
                    f"Test question metadata differs: {qid}",
                )
                require(
                    answer_counts(question["answers"]) == answer_counts(original["answers"]),
                    f"Test answers differ from the source: {qid}",
                )


def contexts(document):
    return tuple(paragraph["context"] for paragraph in document["paragraphs"])


def annotation_signature(document):
    signature = {}
    prefix = document["title"] + "__"
    for index, paragraph in enumerate(document["paragraphs"]):
        for question in paragraph["qas"]:
            require(question["id"].startswith(prefix), "Unexpected source question id format.")
            label = question["id"][len(prefix):]
            key = (index, label)
            require(key not in signature, "Repeated source category within a paragraph.")
            signature[key] = (
                question["question"], question["is_impossible"],
                answer_counts(question["answers"]),
            )
    return signature


def main():
    repo_root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load(
        (repo_root / "ml" / "configs" / "data.yaml").read_text(encoding="utf-8")
    )
    require(config["config_version"] == 1, "Expected config_version: 1")
    source = config["cuad_official"]
    raw_dir = repo_root / config["storage"]["raw_dir"]
    official_dir = repo_root / config["storage"]["official_dir"]
    paths = {
        "full": raw_dir / config["cuad"]["filename"],
        "train": official_dir / "train_separate_questions.json",
        "test": official_dir / "test.json",
    }
    archive_bytes = (official_dir / "data.zip").read_bytes()
    require(
        hashlib.sha256(archive_bytes).hexdigest() == source["archive_sha256"],
        "The official archive checksum has changed.",
    )
    datasets = {}
    with ZipFile(io.BytesIO(archive_bytes)) as archive:
        for role, path in paths.items():
            member = source[f"{role}_member"]
            require(archive.namelist().count(member) == 1, f"Ambiguous ZIP member: {member}")
            payload = path.read_bytes()
            require(payload == archive.read(member), f"Local {role} JSON differs from the archive.")
            datasets[role] = json.loads(payload)
    print("Source bytes: all three JSON files match the pinned official archive")

    indexed = {}
    counts = {}
    for role, dataset in datasets.items():
        indexed[role], counts[role] = inspect_records(dataset, role)
    full, train, test = (indexed[role] for role in ("full", "train", "test"))
    require(not (train.keys() & test.keys()), "Train and test share document titles.")
    require(train.keys() | test.keys() == full.keys(), "Split titles do not cover the full source.")
    require(
        not ({contexts(d) for d in train.values()} & {contexts(d) for d in test.values()}),
        "Identical full text appears in both train and test.",
    )
    logical_questions = check_training(train, full)
    check_test(test, full)

    print(f"Original questions in training contracts: {logical_questions:,}")
    print(f"Official training question records: {counts['train']['questions']:,}")
    print(f"Training records without answers: {counts['train']['empty']:,}")
    print(f"Training records with one answer: {counts['train']['single']:,}")
    print(f"Training records with multiple answers: {counts['train']['multi']:,}")
    print(f"Test questions: {counts['test']['questions']:,}")
    print(f"Test questions with multiple answers: {counts['test']['multi']:,}")
    print("Source-to-split answer differences: 0 (answer order is ignored)")
    for role in ("full", "train", "test"):
        print(f"Exact answer spans checked ({role}): {counts[role]['spans']:,}")

    groups = defaultdict(list)
    for title in train:
        groups[contexts(full[title])].append(title)
    duplicates = sorted(sorted(titles) for titles in groups.values() if len(titles) > 1)
    print(f"Exact duplicate text groups within training: {len(duplicates)}")
    for number, titles in enumerate(duplicates, start=1):
        print(f"\nDuplicate group {number}:")
        for title in titles:
            print(f"  {title}")
        signatures = [annotation_signature(full[title]) for title in titles]
        keys = set().union(*(signature.keys() for signature in signatures))
        differing_labels = sorted({
            label for paragraph, label in keys
            if any(signature.get((paragraph, label)) != signatures[0].get((paragraph, label))
                   for signature in signatures[1:])
        })
        print("  Labels with different annotations: " + (", ".join(differing_labels) or "none"))

    print("\nPASS: official question layout, source answer coverage, and exact spans verified.")
    if duplicates:
        print("REVIEW: keep each duplicate group together in future training/validation splits.")
        print("Review annotation differences before deciding how to use duplicate records.")
    print("Read-only audit: no files changed.")


if __name__ == "__main__":
    main()
