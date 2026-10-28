"""Export selected local training weights; no training or dataset inference.

Run from repository root: python ml/scripts/export_candidate_analyzer.py
Weights remain ignored. Existing artifacts are verified, never overwritten.
"""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clauseanchor_core.artifacts import (
    CHECKPOINT, DECODER, FILES, PACKAGES, TOKENIZER_FILES, canonical_sha256,
    code_hashes, file_spec, read_json, require, runtime_versions, verify_bundle,
    verify_file, write_json,
)

ARTIFACT_DIR = "models/clauseanchor_candidate_v0"
RECEIPT = "data/processed/cuad/candidate_adapter_v0/export_receipt.json"
# Previously verified in the October 28 handoff. Read metadata only: no replay.
VALIDATION_IDENTITY_PIN = "f47f3b426894fca493d8e963148b024630c05167bf5a5dde7ecfb1114d1a16e7"
CONFIG_PINS = {
    "catalogue.json": "23f239d3a9dac1971c05455090651b346189f4c522e5ccd0993f14c29a3f0b65",
    "category_questions.json": "8381cd8b00a8f90a9f9f21032a3cadc35af784d804374e6ee774097fe54d4709",
}
PRODUCER_PINS = {
    "prepare_cuad_features.py": "d82a943a534c02a064ac2290ab0fcef04b9505a31c6b7e6f1cf2ea8ad1131981",
    "cuad_development.py": "612d57db13d7a38e1e565e5416b00f0160208150d7ece557caa6804b1d52f3d1",
    "validate_cuad_decoder.py": "6632389eacd9cb7c7cf7c5182527e01b1325bd9c4ac7070859857d34f292b7a5",
    "review_cuad_decoder.py": "ac878a0c2cf60781be4ebe04dd53ef34ed7973d3cc67a028dcf04c327b7a92a4",
}


def export(repo):
    # Import the completed-run verifier only in this development-side exporter.
    # Deployment has no dependency on ml/scripts or the training data tree.
    from prepare_cuad_training_assets import CONFIG, MODEL_DIR, validate_config
    from prepare_cuad_baseline import verify_ignored_assets
    from review_cuad_decoder import load_checkpoint_reports
    from run_cuad_baseline import run_lock
    from validate_cuad_decoder import load_model
    from safetensors.torch import save_file
    import torch

    repo = Path(repo)
    runtime = runtime_versions()
    for name, pin in PRODUCER_PINS.items():
        actual = hashlib.sha256((repo / "ml/scripts" / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        require(actual == pin, f"Frozen producer changed: {name}")
    for name, pin in CONFIG_PINS.items():
        require(canonical_sha256(read_json(repo / "ml/configs" / name)) == pin, f"Category config changed: {name}")
    target = repo / ARTIFACT_DIR
    verify_ignored_assets(repo, [f"{ARTIFACT_DIR}/{n}" for n in FILES | {"manifest.json"}] + [RECEIPT])
    target.parent.mkdir(parents=True, exist_ok=True)
    training = repo / "data/processed/cuad/clean_training_v1"
    require(training.is_dir(), "Missing local clean_training_v1. Use the machine holding checkpoint-000022; do not retrain.")
    # The existing verifier checks all manifest file hashes and the completed
    # latest -> selected-best chain. It does not rescore or run the model.
    with run_lock(training):
        print("Verifying completed-run and selected checkpoint hashes...", flush=True)
        _, progress, binding = load_checkpoint_reports(training)
        require(binding["selected_checkpoint"] == CHECKPOINT, "Selected checkpoint is not checkpoint-000022.")
        validation = read_json(repo / "data/processed/cuad/decoder_validation_v1/identity.json")
        require(canonical_sha256(validation) == VALIDATION_IDENTITY_PIN
                and validation["checkpoint"] == binding,
                "Checkpoint differs from the previously verified decoder-validation identity; preserve files for review.")
        checkpoint = training / "checkpoints" / CHECKPOINT
        source = read_json(repo / CONFIG)
        validate_config(source)
        assets = repo / MODEL_DIR
        for name in ("config.json", *TOKENIZER_FILES):
            verify_file(assets / name, source["files"][name])
        require(not any((assets / n).exists() for n in ("added_tokens.json", "special_tokens_map.json")),
                "Unpinned tokenizer override found.")
        identity = read_json(training / "identity.json")
        require(identity["source_config_sha256"] == canonical_sha256(source),
                "Training run is not bound to the pinned clean source/tokenizer.")
        selected_manifest = read_json(checkpoint / "manifest.json")
        execution = selected_manifest.get("execution_sha256")
        recovery = None
        if (training / "amp_recovery.json").exists():
            recovery = read_json(training / "amp_recovery.json")
            require(recovery["original_run_sha256"] == binding["run_sha256"]
                    and recovery["execution_sha256"] == canonical_sha256(recovery["execution_identity"])
                    and execution == recovery["execution_sha256"], "AMP execution binding differs.")
        else:
            require(execution in (None, canonical_sha256(identity)), "Missing execution provenance.")
        provenance = {
            **binding, "input_checkpoint_files": selected_manifest["files"],
            "verified_validation_identity_sha256": VALIDATION_IDENTITY_PIN,
            "training_identity": identity, "amp_recovery": recovery,
            "checkpoint_execution_sha256": execution,
            "producer_sha256_lf": PRODUCER_PINS, "config_canonical_sha256": CONFIG_PINS,
            "exporter_sha256_lf": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "source_repository_commit": "f4b6500ff78f2bef7022cd837870ad04b64adc94",
            "export_runtime": runtime, "weight_source": "selected_clean_training_state_dict",
            "training_performed": False, "dataset_inference_performed": False,
        }
        if target.exists():
            manifest = read_json(target / "manifest.json")
            digest = canonical_sha256(manifest)
            require((repo / RECEIPT).is_file(),
                    "Existing export lacks its receipt. Preserve/move that incomplete bundle before re-export; do not overwrite it.")
            verify_bundle(target, read_json(repo / RECEIPT)["manifest_canonical_sha256"])
            require(read_json(target / "provenance.json") == provenance,
                    "Existing export has different provenance; preserve it and choose a new version in code.")
            print("Existing export verified; no artifact replaced.")
        else:
            with TemporaryDirectory(prefix=".candidate-export-", dir=target.parent) as temporary:
                staging = Path(temporary) / "bundle"
                (staging / "tokenizer").mkdir(parents=True)
                print("Loading the verified training state on CPU and exporting only QA weights...", flush=True)
                model = load_model(assets / "config.json", checkpoint, progress, binding, torch.device("cpu"))
                save_file({n: p.detach().cpu().contiguous() for n, p in model.state_dict().items()},
                          str(staging / "model.safetensors"))
                model.config.architectures = ["RobertaForQuestionAnswering"]
                model.config.to_json_file(str(staging / "config.json"), use_diff=False)
                del model
                for name in TOKENIZER_FILES:
                    shutil.copyfile(assets / name, staging / "tokenizer" / name)
                for name in CONFIG_PINS:
                    shutil.copyfile(repo / "ml/configs" / name, staging / name)
                shutil.copyfile(repo / CONFIG, staging / "training_source.json")
                shutil.copyfile(repo / "ml/requirements-inference.txt", staging / "requirements-inference.txt")
                write_json(staging / "decoder.json", DECODER)
                write_json(staging / "provenance.json", provenance)
                manifest = {"format": "clauseanchor-candidate-only-v0", "contract_version": "2.0",
                            "checkpoint": CHECKPOINT, "files": {n: file_spec(staging / n) for n in sorted(FILES)},
                            "code_sha256_lf": code_hashes(), "required_packages": PACKAGES,
                            "validation_scope": "unvalidated", "release_status": "experimental_candidate_only"}
                write_json(staging / "manifest.json", manifest)
                digest = canonical_sha256(manifest)
                verify_bundle(staging, digest)
                # No replacement: rename fails if another process already published a bundle.
                os.rename(staging, target)
    receipt = {"artifact_directory": ARTIFACT_DIR, "checkpoint": CHECKPOINT,
               "manifest_canonical_sha256": digest, "manifest_file_sha256": file_spec(target / "manifest.json")["sha256"],
               "weights_sha256": manifest["files"]["model.safetensors"]["sha256"]}
    destination = repo / RECEIPT
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        require(read_json(destination) == receipt, "Existing receipt differs; it was preserved.")
    else:
        write_json(destination, receipt)
    print(f"PASS: verified inference export from {CHECKPOINT}")
    print(f"Artifact directory: {ARTIFACT_DIR}")
    print(f"Manifest SHA-256 (canonical JSON): {digest}")
    print(f"Weights SHA-256: {receipt['weights_sha256']}")
    print(f"Receipt: {RECEIPT}")
    print("Real-model smoke still required. No calibration or model-quality claim.")
    return receipt


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    export(Path(__file__).resolve().parents[2])
