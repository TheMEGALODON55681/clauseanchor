"""Prepare the general RoBERTa backbone and verify its fast tokenizer.

Run: python ml/scripts/prepare_cuad_training_assets.py
Uses the existing baseline environment. First run downloads about 502 MB.
Reuses hash-verified files offline; interrupted downloads restart on retry.
Stores assets in models/cuad_clean_backbone/roberta-base and an ignored report
at data/processed/cuad/training_assets.json. Existing differing files are kept.

This is the base masked-language-model checkpoint, NOT the released CUAD QA
checkpoint. A future trainer must initialize a new QA head with the fixed seed
and train on fit only. No model is instantiated and no dataset is tokenized here.
Safetensors headers and synthetic tokenizer probes are inspected on CPU.

New training uses 128 context-token overlap, unlike the faithful baseline's
legacy doc_stride=256 setting. Real-data feature building, multi-answer targets,
partial-boundary/long-answer handling, sampling and training remain separate.
"""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from prepare_cuad_baseline import acquire, publish, verify_file, verify_ignored_assets


CONFIG = "ml/configs/cuad_training_source.json"
SOURCE_PIN = "ae3423c4cacca8268a37eb8b123d74f00631438d6f9d92d30792b6a7896479ab"
MODEL_DIR = "models/cuad_clean_backbone/roberta-base"
REPORT = "data/processed/cuad/training_assets.json"
PACKAGES = {"transformers": "4.57.6", "tokenizers": "0.22.2", "safetensors": "0.7.0"}


def validate_config(config):
    require(canonical_sha256(config) == SOURCE_PIN,
            "Clean-training source or feature defaults changed; expected the pinned general RoBERTa backbone.")


def validate_model_metadata(config):
    expected = {"architectures": ["RobertaForMaskedLM"], "model_type": "roberta", "hidden_size": 768,
                "num_hidden_layers": 12, "num_attention_heads": 12, "vocab_size": 50265,
                "max_position_embeddings": 514, "bos_token_id": 0, "eos_token_id": 2, "pad_token_id": 1}
    require(all(config.get(k) == v for k, v in expected.items()), "Unexpected backbone architecture.")


def validate_tensor_shapes(shapes):
    require(shapes.get("roberta.embeddings.word_embeddings.weight") == [50265, 768]
            and shapes.get("roberta.embeddings.position_embeddings.weight") == [514, 768]
            and shapes.get("lm_head.dense.weight") == [768, 768], "Unexpected backbone tensor shapes.")
    require(all(name.startswith(("roberta.", "lm_head.")) for name in shapes),
            "Unexpected task-specific head; do not substitute the CUAD-trained checkpoint.")
    layers = {name.split(".")[3] for name in shapes if name.startswith("roberta.encoder.layer.")}
    require(layers == {str(i) for i in range(12)}, "Missing or extra backbone layers.")
    for index in range(12):
        require(shapes.get(f"roberta.encoder.layer.{index}.attention.self.query.weight") == [768, 768],
                "Unexpected encoder query tensor.")


def validate_window_maps(token_rows, offset_rows, sequence_rows, context, overlap=128):
    require(len(token_rows) == len(offset_rows) == len(sequence_rows) > 0, "Inconsistent tokenizer window rows.")
    covered = bytearray(len(context))
    context_rows = []
    for ids, offsets, sequences in zip(token_rows, offset_rows, sequence_rows):
        require(len(ids) == len(offsets) == len(sequences) == 512, "Expected padded 512-token windows.")
        require(sum(s == 0 for s in sequences) <= 64, "Probe question exceeds the configured token budget.")
        row = []
        for token, span, sequence in zip(ids, offsets, sequences):
            require(sequence in (None, 0, 1), "Unexpected tokenizer sequence ID.")
            require(len(span) == 2 and all(type(x) is int for x in span), "Invalid character offsets.")
            start, end = span
            if sequence is None:
                require((start, end) == (0, 0), "Special/padding token has source offsets.")
            elif sequence == 1:
                require(0 <= start <= end <= len(context), "Context offsets are not source code-point coordinates.")
                covered[start:end] = b"\1" * (end - start)
                row.append((token, start, end))
        require(bool(row), "Empty context window.")
        context_rows.append(row)
    require(all(covered[i] or char.isspace() for i, char in enumerate(context)), "Tokenizer windows lost source characters.")
    for previous, current in zip(context_rows, context_rows[1:]):
        require(len(previous) >= overlap and len(current) >= overlap
                and previous[-overlap:] == current[:overlap], "Context overlap differs from the specified 128 tokens.")
    return context_rows


def tokenizer_probes(tokenizer):
    require(tokenizer.is_fast and len(tokenizer) == 50265 and tokenizer.model_max_length == 512
            and (tokenizer.cls_token_id, tokenizer.sep_token_id, tokenizer.pad_token_id) == (0, 2, 1),
            "Unexpected fast tokenizer or special-token IDs.")
    pieces = [("\tPayment by ", False), ("café", True), (" is ", False), ("₹500", True),
              ("; spelling ", False), ("e\u0301", True), (" and symbol ", False), ("😊", True), (".\nEnd.", False)]
    context, targets = "", []
    for text, is_target in pieces:
        start = len(context)
        context += text
        if is_target:
            targets.append({"text": text, "start": start, "end": len(context)})
    def encode(text):
        return tokenizer("Which text specifies payment?", text, max_length=512, stride=128,
                         truncation="only_second", padding="max_length", return_overflowing_tokens=True,
                         return_offsets_mapping=True)
    encoding = encode(context)
    rows = validate_window_maps(encoding["input_ids"], encoding["offset_mapping"],
                               [encoding.sequence_ids(i) for i in range(len(encoding["input_ids"]))], context)
    require(len(rows) == 1, "Unexpected Unicode probe overflow.")
    for target in targets:
        selected = [(start, end) for _, start, end in rows[0]
                    if start < target["end"] and end > target["start"] and start < end]
        require(bool(selected) and min(s for s, _ in selected) == target["start"]
                and max(e for _, e in selected) == target["end"]
                and context[target["start"]:target["end"]] == target["text"],
                "Unicode source span did not align exactly with tokenizer offsets.")
    long_context = "Payment is due within thirty days.\n" * 180
    long_encoding = encode(long_context)
    long_rows = validate_window_maps(long_encoding["input_ids"], long_encoding["offset_mapping"],
        [long_encoding.sequence_ids(i) for i in range(len(long_encoding["input_ids"]))], long_context)
    require(len(long_rows) > 1, "Overflow probe did not create multiple windows.")
    require(all(ids[0] == tokenizer.cls_token_id for ids in long_encoding["input_ids"]),
            "Expected the null token at position zero in every window.")
    return {"unicode_targets": targets, "unicode_code_point_alignment_verified": True,
            "question_context_and_special_tokens_separated": True,
            "overflow_windows": len(long_rows), "context_token_overlap": 128,
            "complete_non_whitespace_coverage_verified": True, "null_token_index": 0,
            "scope": "synthetic_probes_only; real_dataset_features_not_created"}


def verify_local_assets(directory, config):
    for name, spec in config["files"].items():
        verify_file(directory / name, spec)
    require(not (directory / "added_tokens.json").exists()
            and not (directory / "special_tokens_map.json").exists(), "Unpinned tokenizer override file found.")
    validate_model_metadata(read_json(directory / "config.json"))
    from safetensors import safe_open
    # Inspect metadata only; do not load the 499 MB tensors or create a model.
    with safe_open(directory / "model.safetensors", framework="np") as handle:
        shapes = {name: handle.get_slice(name).get_shape() for name in handle.keys()}
    validate_tensor_shapes(shapes)
    from transformers import RobertaTokenizerFast
    tokenizer = RobertaTokenizerFast.from_pretrained(str(directory), local_files_only=True,
                                                    add_prefix_space=False, trim_offsets=True)
    return len(shapes), tokenizer_probes(tokenizer)


def prepare(repo):
    require(platform.python_version_tuple()[:2] == ("3", "12"), "Use the Python 3.12 clauseanchor environment.")
    versions = {name: importlib.metadata.version(name) for name in PACKAGES}
    require(versions == PACKAGES, "Expected the existing pinned baseline tokenizer dependencies.")
    config = read_json(repo / CONFIG)
    validate_config(config)
    specs = {f"{MODEL_DIR}/{name}": spec for name, spec in config["files"].items()}
    verify_ignored_assets(repo, [*specs, REPORT])
    require(not any((repo / MODEL_DIR / name).exists() for name in ("added_tokens.json", "special_tokens_map.json")),
            "Unpinned tokenizer override file found in the destination.")
    for relative, spec in specs.items():
        if (repo / relative).exists():
            verify_file(repo / relative, spec)
    parent = repo / "models/cuad_clean_backbone"
    parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".prepare-", dir=parent) as temporary:
        staging = Path(temporary)
        staged = {}
        for name, spec in config["files"].items():
            relative = f"{MODEL_DIR}/{name}"
            existing = repo / relative
            target = staging / name
            if existing.exists():
                # Small files and the large checkpoint remain outside Git. A
                # staging link avoids another 499 MB copy; fall back to copying
                # on filesystems that do not support hard links.
                import os
                import shutil
                try:
                    os.link(existing, target)
                except OSError:
                    shutil.copyfile(existing, target)
            else:
                print(f"Downloading pinned training asset: {name}", flush=True)
                url = f"https://huggingface.co/{config['repo_id']}/resolve/{config['revision']}/{name}?download=true"
                acquire(url, target, spec)
            staged[relative] = target
        tensor_count, probes = verify_local_assets(staging, config)
        report = {"report_version": 1, "status": "clean_training_backbone_and_tokenizer_verified",
            "source_config_canonical_sha256": SOURCE_PIN, "repo_id": config["repo_id"],
            "revision": config["revision"], "files": specs.copy(), "stored_tensors": tensor_count,
            "checkpoint_type": "general_pretrained_masked_language_model",
            "qa_head_initialized": False, "training_performed": False, "dataset_features_created": False,
            "baseline_reproduction_assessed": False, "feature_defaults": config["feature_defaults"],
            "tokenizer_probes": probes, "runtime": {"python": platform.python_version(), "packages": versions}}
        payload = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
        report_path = staging / "training_assets.json"
        report_path.write_bytes(payload)
        staged[REPORT] = report_path
        specs[REPORT] = {"size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        created = publish(repo, staged, specs)
    for relative, spec in specs.items():
        verify_file(repo / relative, spec)
    return report, created


def main():
    report, created = prepare(Path(__file__).resolve().parents[2])
    print("Pinned FacebookAI/roberta-base revision and six file hashes: verified")
    print(f"Base masked-language-model checkpoint: 12 layers; {report['stored_tensors']} stored tensors; no CUAD QA head")
    print("Fast tokenizer: Unicode code-point spans, sequence IDs and null token verified")
    print(f"Overflow probe: {report['tokenizer_probes']['overflow_windows']} windows; 128-token overlap; complete non-whitespace coverage")
    print("New-training defaults: length 512; question limit 64; overlap 128; answer limit 256")
    print(f"Created {created} asset/report files." if created else "Existing training assets match; no files changed.")
    print(f"Assets: {MODEL_DIR}/")
    print(f"Report: {REPORT}")
    print("PASS: base backbone and fast tokenizer ready for real-data feature preparation.")
    print("No dataset features, QA head or trained checkpoint created.")


if __name__ == "__main__":
    main()
