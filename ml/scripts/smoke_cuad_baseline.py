"""Run the pinned CUAD checkpoint on one fixed, complete official-test question.

Run: python ml/scripts/smoke_cuad_baseline.py
CPU only, float32, eager attention, at most four CPU threads. Requires the
previously downloaded assets and requirements-baseline.txt. No model downloads,
training, label-based selection, truncation of the contract, or GPU are needed.

This checks the modern Python 3.12 runtime, legacy slow-tokenizer windows, and
the authors' hash-verified decoder. It does NOT establish full-test reproduction
or a calibrated confidence. The authors' checkpoint saw original training data;
it must not initialize later clean-fit training.
"""

import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

from audit_cuad_categories import save_outputs
from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from evaluate_cuad_baseline import SOURCE_PIN
from prepare_cuad_baseline import (
    CONFIG, MODEL_DIR, REFERENCE_DIR, validate_config, validate_model_metadata,
    validate_reference_predictions, verify_file, verify_ignored_assets,
)


PACKAGES = {"torch": "2.9.1", "transformers": "4.57.6", "tokenizers": "0.22.2",
            "safetensors": "0.7.0", "numpy": "2.3.5"}
REPORT = "data/processed/cuad/baseline_smoke.json"
MODEL_FILES = ("config.json", "pytorch_model.bin", "vocab.json", "merges.txt",
               "tokenizer_config.json", "special_tokens_map.json")
SMOKE_QID = ("LohaCompanyltd_20191209_F-1_EX-10.16_11917878_EX-10.16_Supply Agreement"
             "__Document Name")


def runtime_versions():
    require(platform.python_version_tuple()[:2] == ("3", "12"), "Use the Python 3.12 clauseanchor environment.")
    versions = {}
    for name, expected in PACKAGES.items():
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise ValueError("Install ml/requirements-baseline.txt first.") from error
        require(versions[name].split("+")[0] == expected,
                f"Expected {name}=={expected}; found {versions[name]}. Install the pinned baseline requirements.")
    return {"python": platform.python_version(), **versions}


def select_question(test):
    """Fixed source-order selection; never use answer labels to build input."""
    document = test["data"][0]
    paragraph = document["paragraphs"][0]
    question = paragraph["qas"][0]
    require(question["id"] == SMOKE_QID, "Fixed smoke question changed.")
    return {"data": [{"title": document["title"], "paragraphs": [{
        "context": paragraph["context"],
        "qas": [{"id": question["id"], "question": question["question"]}],
    }]}]}


def validate_loading(info):
    # Legacy RoBERTa serialized this deterministic buffer; modern versions do not.
    require(not info.get("missing_keys") and not info.get("mismatched_keys")
            and not info.get("error_msgs"), "Checkpoint parameters were missing, mismatched or not loaded.")
    require(set(info.get("unexpected_keys", [])) <= {"roberta.embeddings.position_ids"},
            "Unexpected checkpoint parameters; refusing a partial model load.")


def validate_coverage(features, word_count):
    require(bool(features) and word_count > 0, "No input windows or context words.")
    covered = set()
    for feature in features:
        require(len(feature.input_ids) == 512 and len(feature.attention_mask) == 512,
                "Unexpected baseline window length.")
        require(feature.token_to_orig_map and all(0 <= i < 512 for i in feature.token_to_orig_map),
                "Invalid context-token mapping.")
        covered.update(feature.token_to_orig_map.values())
    require(covered == set(range(word_count)), "Incomplete contract coverage; refusing a truncated smoke run.")


def compare_reference(fresh, released, fresh_top, released_top):
    same_texts = [c["text"] for c in fresh] == [c["text"] for c in released]
    return {"top_prediction_matches": fresh_top == released_top,
            "ranked_candidate_texts_match": same_texts,
            "maximum_probability_difference_if_same_ranking":
                max(abs(a["probability"] - b["probability"]) for a, b in zip(fresh, released))
                if same_texts else None,
            "full_test_inference_parity_verified": False}


def smoke(repo):
    versions = runtime_versions()
    config = read_json(repo / CONFIG)
    validate_config(config)
    require(canonical_sha256(config) == SOURCE_PIN, "Baseline source configuration changed.")
    root = repo / MODEL_DIR / "roberta-base"
    reference = repo / REFERENCE_DIR / "utils.py"
    verify_file(repo / config["official_test"]["path"], config["official_test"])
    for name in (*MODEL_FILES, "nbest_predictions_.json", "predictions_.json"):
        verify_file(root / name, config["members"][name])
    verify_file(reference, config["reference_files"]["utils.py"])
    validate_model_metadata(read_json(root / "config.json"), read_json(root / "tokenizer_config.json"))
    verify_ignored_assets(repo, [REPORT])
    selected = select_question(read_json(repo / config["official_test"]["path"]))
    paragraph = selected["data"][0]["paragraphs"][0]
    question = paragraph["qas"][0]
    print("Pinned checkpoint, tokenizer, decoder and official test: verified", flush=True)

    # Imports are delayed so policy tests do not need to load Torch.
    import torch
    from transformers import RobertaForQuestionAnswering, RobertaTokenizer
    from transformers.data.processors.squad import (
        SquadExample, SquadResult, squad_convert_example_to_features,
        squad_convert_example_to_features_init,
    )

    threads = min(4, os.cpu_count() or 1)
    torch.set_num_threads(threads)
    tokenizer = RobertaTokenizer.from_pretrained(
        str(root), local_files_only=True, do_lower_case=False, add_prefix_space=False,
    )
    require(not tokenizer.is_fast and tokenizer.pad_token_id == 1 and tokenizer.cls_token_id == 0,
            "Expected the released slow RoBERTa tokenizer.")
    example = SquadExample(qas_id=question["id"], question_text=question["question"],
                           context_text=paragraph["context"], answer_text=None,
                           start_position_character=None, title=selected["data"][0]["title"],
                           answers=[], is_impossible=False)
    # The sequential inner converter avoids Windows multiprocessing. It is the
    # same converter called by the original train.py's batch wrapper.
    squad_convert_example_to_features_init(tokenizer)
    features = squad_convert_example_to_features(example, max_seq_length=512,
                    doc_stride=256, max_query_length=64, padding_strategy="max_length", is_training=False)
    for i, feature in enumerate(features):
        feature.example_index, feature.unique_id = 0, 1000000000 + i
    validate_coverage(features, len(example.doc_tokens))
    print(f"Fixed smoke question: {question['id']}", flush=True)
    print(f"Complete contract: {len(features)} windows; CPU float32; {threads} threads", flush=True)
    print("Loading verified checkpoint...", flush=True)
    model, loading = RobertaForQuestionAnswering.from_pretrained(
        str(root), local_files_only=True, use_safetensors=False, weights_only=True,
        output_loading_info=True, attn_implementation="eager", dtype=torch.float32,
    )
    validate_loading(loading)
    model = model.to("cpu").eval()
    results = []
    with torch.inference_mode():
        for i, feature in enumerate(features):
            output = model(input_ids=torch.tensor([feature.input_ids], dtype=torch.long),
                           attention_mask=torch.tensor([feature.attention_mask], dtype=torch.long))
            require(tuple(output.start_logits.shape) == (1, 512)
                    and tuple(output.end_logits.shape) == (1, 512)
                    and torch.isfinite(output.start_logits).all().item()
                    and torch.isfinite(output.end_logits).all().item(), "Invalid model logits.")
            results.append(SquadResult(feature.unique_id, output.start_logits[0].tolist(),
                                       output.end_logits[0].tolist()))
            print(f"  Inference window {i + 1}/{len(features)}", flush=True)

    spec = importlib.util.spec_from_file_location("clauseanchor_pinned_cuad_decoder", reference)
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    with TemporaryDirectory(prefix="cuad-smoke-") as tmp:
        paths = [Path(tmp) / name for name in ("predictions.json", "nbest.json", "null_odds.json")]
        decoder.compute_predictions_logits(selected, [example], features, results, 20, 512, False,
            *(str(path) for path in paths), False, True, 0.0, tokenizer)
        predictions, nbest, null_odds = [read_json(path) for path in paths]
    candidates = [{k: c[k] for k in ("text", "probability", "start_logit", "end_logit")}
                  for c in nbest[question["id"]]]
    validate_reference_predictions(selected, {question["id"]: candidates}, predictions, null_odds)
    released = read_json(root / "nbest_predictions_.json")[question["id"]]
    released_top = read_json(root / "predictions_.json")[question["id"]]
    comparison = compare_reference(candidates, released, predictions[question["id"]], released_top)
    report = {"report_version": 1, "status": "single_question_cpu_inference_verified",
        "source_config_canonical_sha256": SOURCE_PIN, "official_test": config["official_test"],
        "checkpoint_sha256": config["members"]["pytorch_model.bin"]["sha256"],
        "decoder_sha256": config["reference_files"]["utils.py"]["sha256"],
        "runtime_versions": versions, "cpu_threads": threads, "dtype": "float32",
        "attention_implementation": "eager", "reference_inference_settings": config["reference_inference_settings"],
        "null_score_diff_threshold": 0.0, "selection": "first source document, paragraph and question; no labels",
        "question_id": question["id"], "input_canonical_sha256": canonical_sha256(selected),
        "source_documents": 1, "questions": 1, "windows": len(features), "complete_context_coverage": True,
        "prediction": predictions[question["id"]], "released_prediction": released_top,
        "candidates": candidates, "null_score_difference": null_odds[question["id"]],
        "released_prediction_comparison": comparison, "checkpoint_loading": loading,
        "baseline_reproduction_complete": False, "training_performed": False,
        "calibration_performed": False, "policy_threshold_selected": False}
    # No times or durations: repeated runs in the same runtime can reuse the report.
    content = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    created = save_outputs({repo / REPORT: content.encode("utf-8")})
    return report, created


def main():
    report, created = smoke(Path(__file__).resolve().parents[2])
    comparison = report["released_prediction_comparison"]
    print(f"Fresh prediction: {report['prediction']!r}")
    print(f"Released top prediction matches: {comparison['top_prediction_matches']}")
    print(f"Released candidate ranking matches: {comparison['ranked_candidate_texts_match']}")
    print("Created smoke report." if created else "Existing smoke report matches; no files changed.")
    print(f"Report: {REPORT}")
    print("PASS: checkpoint loaded and all windows of one fixed question completed on CPU.")
    print("Full-test fresh inference and reproduction checks remain pending. No training or calibration performed.")


if __name__ == "__main__":
    main()
