from pathlib import Path

import yaml
from huggingface_hub import HfApi


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

    print("Checking CUAD source metadata on Hugging Face...")

    info = HfApi().dataset_info(
        repo_id=source["repo_id"],
        revision=source["revision"],
        timeout=30,
        token=False,
    )

    if info.sha != source["revision"]:
        raise ValueError("The returned revision does not match the pinned commit.")

    filenames = {item.rfilename for item in info.siblings or []}

    if source["filename"] not in filenames:
        raise ValueError(
            f"File not found at the pinned revision: {source['filename']}"
        )

    print(f"Repository: {source['repo_id']}")
    print(f"Revision: {info.sha}")
    print(f"File found: {source['filename']}")
    print("PASS: pinned revision and file listing verified.")
    print("No dataset downloaded.")


if __name__ == "__main__":
    main()