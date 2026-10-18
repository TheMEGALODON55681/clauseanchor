import hashlib
import json
from pathlib import Path

import yaml


def main():
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "ml" / "configs" / "data.yaml"

    with config_path.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if config["config_version"] != 1:
        raise ValueError("Expected config_version: 1")

    source = config["cuad"]
    raw_dir = repo_root / config["storage"]["raw_dir"]
    data_path = raw_dir / source["filename"]
    manifest_path = raw_dir / "source_manifest.json"

    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)

    for field in ("repo_id", "repo_type", "revision", "filename"):
        if manifest[field] != source[field]:
            raise ValueError(f"Configuration and manifest disagree: {field}")

    raw_bytes = data_path.read_bytes()
    checksum = hashlib.sha256(raw_bytes).hexdigest()

    if checksum != manifest["sha256"]:
        raise ValueError("The dataset checksum differs from the saved manifest.")

    print("Checksum: matches the saved manifest")

    dataset = json.loads(raw_bytes)
    documents = dataset["data"]

    if not isinstance(documents, list) or not documents:
        raise ValueError("Expected a non-empty list of documents.")

    counts = {
        "Documents": len(documents),
        "Paragraphs": 0,
        "Questions": 0,
        "Questions without answers": 0,
        "Questions with multiple answers": 0,
        "Answer spans": 0,
        "Invalid spans": 0,
    }
    examples = []

    for document_index, document in enumerate(documents):
        for paragraph_index, paragraph in enumerate(document["paragraphs"]):
            counts["Paragraphs"] += 1
            context = paragraph["context"]

            if not isinstance(context, str):
                raise ValueError("A paragraph context is not a string.")

            for question in paragraph["qas"]:
                counts["Questions"] += 1
                answers = question["answers"]

                if not isinstance(answers, list):
                    raise ValueError("A question's answers must be a list.")

                if not answers:
                    counts["Questions without answers"] += 1
                elif len(answers) > 1:
                    counts["Questions with multiple answers"] += 1

                for answer_index, answer in enumerate(answers):
                    counts["Answer spans"] += 1
                    start = answer.get("answer_start")
                    text = answer.get("text")

                    valid = (
                        type(start) is int
                        and isinstance(text, str)
                        and len(text) > 0
                        and start >= 0
                        and start + len(text) <= len(context)
                        and context[start:start + len(text)] == text
                    )

                    if not valid:
                        counts["Invalid spans"] += 1

                        if len(examples) < 5:
                            examples.append(
                                f"document={document_index}, "
                                f"paragraph={paragraph_index}, "
                                f"question={question['id']}, "
                                f"answer={answer_index}"
                            )

    for name, value in counts.items():
        print(f"{name}: {value:,}")

    if counts["Answer spans"] == 0:
        raise SystemExit("CHECK FAILED: no annotated answer spans found.")

    if counts["Invalid spans"]:
        print("\nFirst invalid span locations:")
        for example in examples:
            print(example)

        raise SystemExit(
            "CHECK FAILED: some answer positions do not match. "
            "The dataset has not been changed."
        )

    print("PASS: all annotated spans match their exact context positions.")
    print("Inspection only: no files changed.")


if __name__ == "__main__":
    main()