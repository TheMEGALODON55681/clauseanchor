"""Download and verify the pinned official CUAD benchmark split files."""

import hashlib
import io
import json
import re
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import yaml


MAX_ARCHIVE_BYTES = 32 * 1024 * 1024


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def document_index(payload, label):
    documents = json.loads(payload)["data"]
    if not isinstance(documents, list) or not documents:
        raise ValueError(f"{label}: expected a non-empty document list.")

    indexed = {}
    for document in documents:
        title = document["title"]
        contexts = tuple(p["context"] for p in document["paragraphs"])
        if not isinstance(title, str) or not title or title in indexed:
            raise ValueError(f"{label}: missing or duplicate document title.")
        if not contexts or any(not isinstance(text, str) for text in contexts):
            raise ValueError(f"{label}: invalid document context.")
        indexed[title] = contexts
    return indexed


def main():
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "ml" / "configs" / "data.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["config_version"] != 1:
        raise ValueError("Expected config_version: 1")

    source = config["cuad_official"]
    if not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
        raise ValueError("The official revision must be a full commit hash.")
    if not re.fullmatch(r"[0-9a-f]{64}", source["archive_sha256"]):
        raise ValueError("Expected a complete archive SHA-256 checksum.")

    raw_dir = (repo_root / config["storage"]["raw_dir"]).resolve()
    output_dir = (repo_root / config["storage"]["official_dir"]).resolve()
    if not raw_dir.is_relative_to(repo_root / "data"):
        raise ValueError("The raw directory must be inside data/.")
    if output_dir == raw_dir or not output_dir.is_relative_to(raw_dir):
        raise ValueError("The official directory must be a subfolder of raw_dir.")

    # Check the existing full dataset before using it as our reference.
    full_path = raw_dir / config["cuad"]["filename"]
    source_manifest = json.loads(
        (raw_dir / "source_manifest.json").read_text(encoding="utf-8")
    )
    for field in ("repo_id", "repo_type", "revision", "filename"):
        if source_manifest[field] != config["cuad"][field]:
            raise ValueError(f"Full-source manifest disagrees with config: {field}")
    local_full = full_path.read_bytes()
    if sha256(local_full) != source_manifest["sha256"]:
        raise ValueError("The existing full dataset has changed.")

    url = (
        f"https://raw.githubusercontent.com/{source['repo_id']}/"
        f"{source['revision']}/{source['archive_path']}"
    )
    archive_path = output_dir / "data.zip"
    if archive_path.exists():
        print("Checking the previously downloaded official archive...")
        with archive_path.open("rb") as file:
            archive_bytes = file.read(MAX_ARCHIVE_BYTES + 1)
    else:
        print("Downloading the pinned official CUAD archive (about 18 MB)...")
        with urlopen(url, timeout=30) as response:
            archive_bytes = response.read(MAX_ARCHIVE_BYTES + 1)

    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds the 32 MiB download limit.")
    if sha256(archive_bytes) != source["archive_sha256"]:
        raise ValueError("Official archive checksum mismatch; no files saved.")
    print("Archive checksum: matches the pinned checksum")

    members = {role: source[f"{role}_member"] for role in ("full", "train", "test")}
    if len(set(members.values())) != 3:
        raise ValueError("Full, train, and test must name different ZIP members.")
    with ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = archive.namelist()
        for name in members.values():
            if names.count(name) != 1:
                raise ValueError(f"ZIP member missing or duplicated: {name}")
        # Read only the named files. Do not extract arbitrary archive paths.
        payloads = {role: archive.read(name) for role, name in members.items()}

    if payloads["full"] != local_full:
        raise ValueError("Archive's full dataset differs from the existing JSON.")
    print("Full dataset: byte-for-byte match with the existing CUAD JSON")

    indexed = {role: document_index(data, role) for role, data in payloads.items()}
    full, train, test = (indexed[role] for role in ("full", "train", "test"))
    if train.keys() & test.keys():
        raise ValueError("A document title appears in both training and test.")
    if train.keys() | test.keys() != full.keys():
        raise ValueError("The two splits do not cover exactly the full dataset.")
    for split in (train, test):
        for title, contexts in split.items():
            if contexts != full[title]:
                raise ValueError(f"Split text differs from the full source: {title}")
    if set(train.values()) & set(test.values()):
        raise ValueError("Identical full text appears in both training and test.")

    # Fixed output names avoid treating ZIP member names as filesystem paths.
    output_files = {
        "data.zip": archive_bytes,
        "train_separate_questions.json": payloads["train"],
        "test.json": payloads["test"],
    }
    counts = {role: len(documents) for role, documents in indexed.items()}
    repeated_training_texts = len(train) - len(set(train.values()))
    manifest = {
        "manifest_version": 1,
        "source": dict(source, url=url),
        "full_source_sha256": sha256(local_full),
        "document_counts": counts,
        "repeated_training_text_entries": repeated_training_texts,
        "checks": {
            "full_source_bytes_match": True,
            "split_contexts_match_full_source": True,
            "split_titles_cover_full_source": True,
            "shared_train_test_titles": 0,
            "shared_train_test_exact_texts": 0,
        },
        "files": {
            name: {"size_bytes": len(data), "sha256": sha256(data)}
            for name, data in output_files.items()
        },
    }
    output_files["manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    # Check every existing output before writing any new output.
    for name, data in output_files.items():
        path = output_dir / name
        if path.exists() and path.read_bytes() != data:
            raise ValueError(f"Existing output differs; it was not replaced: {path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in output_files.items():
        path = output_dir / name
        if not path.exists():
            with path.open("xb") as file:
                file.write(data)

    print(f"Training contracts: {len(train):,}")
    print(f"Test contracts: {len(test):,}")
    print(f"Total contracts: {len(full):,}")
    print("Shared train/test titles: 0")
    print("Shared train/test exact full texts: 0")
    print(f"Repeated full-text entries within training: {repeated_training_texts}")
    print("The official split is preserved; no records were removed.")
    print(f"Saved in: {output_dir.relative_to(repo_root).as_posix()}")
    print("PASS: official archive and document split verified.")


if __name__ == "__main__":
    main()
