"""Offline, fail-closed verification for the candidate-only inference export."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform


CHECKPOINT = "checkpoint-000022"
PACKAGES = {"numpy": "2.3.5", "torch": "2.9.1", "transformers": "4.57.6",
            "tokenizers": "0.22.2", "safetensors": "0.7.0"}
TOKENIZER_FILES = ("config.json", "merges.txt", "tokenizer.json", "tokenizer_config.json", "vocab.json")
FILES = {"model.safetensors", "config.json", "catalogue.json", "category_questions.json",
         "decoder.json", "requirements-inference.txt", "provenance.json", "training_source.json",
         *(f"tokenizer/{name}" for name in TOKENIZER_FILES)}
CODE_FILES = ("__init__.py", "contract.py", "serialization.py", "stub.py",
              "artifacts.py", "_inference.py", "analyzer.py")
DECODER = {
    "version": "candidate-only-v0-disjoint-reference", "checkpoint": CHECKPOINT,
    "max_seq_length": 512, "max_question_tokens": 64, "context_token_overlap": 128,
    "max_answer_tokens": 256, "top_start_end": 20, "per_window_candidates": 20,
    "null_token_index": 0, "margin_strictly_greater_than": 0.0,
    "score": "start_plus_end_minus_same_window_cls_start_plus_end",
    "exact_dedup": "score_boundary_start_end_row_order_complete_counterpart_resolves_flag",
    "selection": "greedy_disjoint_full_positive_character_overlap_no_global_cap",
    "attention": "sdpa", "cpu_precision": "fp32", "cuda_precision": "fp16_autocast",
    "calibrated": False, "automatic_acceptance": False, "absence_allowed": False,
    "decoration_transport": "structure_nodes_kind_decoration_v1",
    "decoration_view": "same_length_spaces_preserve_whitespace_omit_crossing_candidates",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_bytes().decode("utf-8"))


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def write_json(path, value):
    Path(path).write_bytes((json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                                     allow_nan=False) + "\n").encode("utf-8"))


def file_spec(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return {"size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def verify_file(path, spec):
    require(Path(path).is_file() and not Path(path).is_symlink(), f"Missing/linked artifact: {path}")
    require(file_spec(path) == spec, f"Artifact hash/size mismatch: {path}")


def code_hashes():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in CODE_FILES}


def runtime_versions():
    require(platform.python_version_tuple()[:2] == ("3", "12"), "Use Python 3.12.")
    versions = {name: importlib.metadata.version(name) for name in PACKAGES}
    require(all(versions[n].split("+")[0] == v for n, v in PACKAGES.items()),
            f"Inference dependencies differ from pinned versions: {versions}")
    return {"python": platform.python_version(), "packages": versions}


def verify_bundle(directory, expected_sha256):
    """The independently supplied canonical manifest digest is the trust anchor."""
    root = Path(directory)
    require(isinstance(expected_sha256, str) and len(expected_sha256) == 64
            and all(c in "0123456789abcdef" for c in expected_sha256), "Supply the export's manifest SHA-256.")
    manifest = read_json(root / "manifest.json")
    require(canonical_sha256(manifest) == expected_sha256, "Manifest digest mismatch.")
    require(manifest.get("format") == "clauseanchor-candidate-only-v0"
            and manifest.get("checkpoint") == CHECKPOINT and manifest.get("contract_version") == "2.0",
            "Wrong inference artifact format/checkpoint/contract.")
    require(set(manifest["files"]) == FILES, "Unexpected artifact inventory.")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    require(actual == FILES | {"manifest.json"}
            and not any(p.is_symlink() for p in root.rglob("*")), "Extra/missing/linked bundle files.")
    for name, spec in manifest["files"].items():
        verify_file(root / name, spec)
    require(manifest["code_sha256_lf"] == code_hashes(), "Installed inference code differs; export a new artifact version.")
    require(read_json(root / "decoder.json") == DECODER, "Decoder settings differ.")
    require(manifest["required_packages"] == PACKAGES, "Runtime requirements differ.")
    provenance = read_json(root / "provenance.json")
    require(provenance["selected_checkpoint"] == CHECKPOINT, "Wrong checkpoint provenance.")
    catalogue, prompts = read_json(root / "catalogue.json"), read_json(root / "category_questions.json")
    require(prompts["catalogue_content_sha256"] == canonical_sha256(catalogue), "Question/catalogue binding differs.")
    rows, questions = catalogue["categories"], prompts["questions"]
    require(len(rows) == len(questions) == 46 and len({r["id"] for r in rows}) == 46
            and {r["category_id"] for r in questions} == {r["id"] for r in rows}, "Invalid category inventory.")
    require(all(r["support_status"] == "not_validated" for r in rows), "v0 must not claim validated categories.")
    supported = {r["id"] for r in rows if r["source"] == "cuad"}
    require(len(supported) == 41 and all(bool(q["cuad_annotated"]) == (q["category_id"] in supported)
            and isinstance(q["question"], str) and q["question"] for q in questions), "Invalid prompt support.")
    return manifest, catalogue, {q["category_id"]: q["question"] for q in questions if q["category_id"] in supported}
