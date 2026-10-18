import hashlib
import json
import re
from pathlib import Path

import yaml
from huggingface_hub import hf_hub_download


def main():
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "ml" / "configs" / "data.yaml"

    with config_path.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if config["config_version"] != 1:
        raise ValueError("Expected config_version: 1")

    source = config["cuad"]

    if source["repo_type"] != "dataset":
        raise ValueError("CUAD repo_type must be 'dataset'.")

    if not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
        raise ValueError("The revision must be a full commit hash.")

    raw_dir = (repo_root / config["storage"]["raw_dir"]).resolve()

    if not raw_dir.is_relative_to(repo_root / "data"):
        raise ValueError("The download directory must be inside data/.")

    print("Downloading the pinned CUAD JSON file...")

    downloaded_path = Path(
        hf_hub_download(
            repo_id=source["repo_id"],
            repo_type=source["repo_type"],
            revision=source["revision"],
            filename=source["filename"],
            local_dir=raw_dir,
            token=False,
            etag_timeout=30,
        )
    )

    with downloaded_path.open("rb") as file:
        checksum = hashlib.file_digest(file, "sha256").hexdigest()

    manifest = {
        "manifest_version": 1,
        "repo_id": source["repo_id"],
        "repo_type": source["repo_type"],
        "revision": source["revision"],
        "filename": source["filename"],
        "local_path": downloaded_path.relative_to(repo_root).as_posix(),
        "size_bytes": downloaded_path.stat().st_size,
        "sha256": checksum,
    }

    manifest_path = raw_dir / "source_manifest.json"

    if manifest_path.exists():
        with manifest_path.open(encoding="utf-8") as file:
            previous_manifest = json.load(file)

        if previous_manifest != manifest:
            raise ValueError(
                "The file or source details differ from the saved manifest. "
                "The existing manifest has not been replaced."
            )
    else:
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"File: {manifest['local_path']}")
    print(f"Size: {manifest['size_bytes']:,} bytes")
    print(f"SHA-256: {checksum}")
    print(f"Manifest: {manifest_path.relative_to(repo_root).as_posix()}")
    print("PASS: CUAD file ready; source and checksum recorded.")


if __name__ == "__main__":
    main()