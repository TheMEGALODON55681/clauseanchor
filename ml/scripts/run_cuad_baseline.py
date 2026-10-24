"""Resumable fresh CUAD inference and official-metric evaluation.

GPU pilot: python ml/scripts/run_cuad_baseline.py --limit-questions 2
Full run/resume: python ml/scripts/run_cuad_baseline.py
CPU verification: add --device cpu (uses a separate output directory).

Requires the prepared assets and baseline dependencies. For Windows CUDA use:
python -m pip install torch==2.9.1+cu126 --index-url https://download.pytorch.org/whl/cu126

Batch size 1, float32, eager attention, TF32 off. Only one question's windows
and logits are held at a time. Each completed question is atomically saved.
Ctrl+C preserves completed questions; restart with the same command to resume.
Saved results from different code, assets, runtimes or devices cannot be mixed.
--limit-questions selects a prefix in source order, independent of gold labels;
it does not change the run identity, and partial runs never receive test scores.

After all 4182 questions, score the full test and reviewed sensitivity subset
using both the local and original evaluators. Report differences against the
released predictions for review; do not assert reproduction based on a chosen
post-hoc tolerance. Never train, calibrate or select an operating threshold.
"""

import argparse
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory
import time

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from evaluate_cuad_baseline import (
    FAMILY_PATH, FAMILY_PIN, PACKAGES as EVALUATION_PACKAGES, SOURCE_PIN,
    assert_parity, evaluate as evaluate_released, finite_json, load_reference,
    reference_score, score_predictions,
)
from prepare_cuad_baseline import (
    CONFIG, MODEL_DIR, REFERENCE_DIR, validate_config, validate_model_metadata,
    validate_reference_predictions, verify_file, verify_ignored_assets,
)
from smoke_cuad_baseline import MODEL_FILES, runtime_versions, validate_coverage, validate_loading


OUTPUT_BASE = "data/processed/cuad/baseline_inference"
FINAL_FILES = ("predictions.json", "nbest_predictions.json", "null_odds.json",
               "evaluation.json", "evaluation_curves.json", "manifest.json")
CODE_FILES = ("run_cuad_baseline.py", "smoke_cuad_baseline.py", "prepare_cuad_baseline.py",
              "evaluate_cuad_baseline.py", "audit_cuad_questions.py", "check_cuad_families.py",
              "build_cuad_inventory.py", "audit_cuad_categories.py")
CANDIDATE_FIELDS = ("text", "probability", "start_logit", "end_logit")


def inference_inputs(test):
    inputs, seen = [], set()
    for document in test["data"]:
        require(len(document["paragraphs"]) == 1, "Original decoder requires one complete paragraph per contract.")
        paragraph = document["paragraphs"][0]
        for q in paragraph["qas"]:
            require(q["id"] not in seen, "Duplicate official question ID.")
            seen.add(q["id"])
            inputs.append({"data": [{"title": document["title"], "paragraphs": [{
                "context": paragraph["context"], "qas": [{"id": q["id"], "question": q["question"]}],
            }]}]})
    return inputs


def question_id(selected):
    return selected["data"][0]["paragraphs"][0]["qas"][0]["id"]


def output_name(device, name):
    name = name or f"{device}-fp32"
    require(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", name) is not None, "Invalid run name.")
    return name


@contextmanager
def run_lock(root):
    """OS locks release even after a crash; a surviving lock file is harmless."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / "run.lock").open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError("Another process is using this run directory. Use one runner at a time.") from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_json(path, value):
    """Caller holds run_lock. Preserve differing files; publish only complete JSON."""
    payload = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    if path.exists():
        require(path.read_bytes() == payload, f"Existing file differs; preserved: {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=".pending-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        require(not path.exists(), f"Destination appeared during write; preserved: {path}")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def bind_run(root, identity):
    path = root / "run.json"
    if path.exists():
        require(read_json(path) == identity,
                "Saved run identity differs (code/runtime/device/settings). Preserve it and use a new --run-name.")
    else:
        require(not any((root / "questions").glob("*.json"))
                and not any((root / name).exists() for name in FINAL_FILES), "Results exist without a run manifest.")
        atomic_json(path, identity)
    return canonical_sha256(identity)


def make_record(index, selected, run_id, result):
    body = {"question_index": index, "question_id": question_id(selected),
            "input_sha256": canonical_sha256(selected), "run_sha256": run_id, **result}
    return {"payload": body, "payload_sha256": canonical_sha256(body)}


def validate_record(record, index, selected, run_id):
    require(set(record) == {"payload", "payload_sha256"}, "Invalid question record envelope.")
    body = record["payload"]
    require(canonical_sha256(body) == record["payload_sha256"], "Saved question digest differs.")
    require(set(body) == {"question_index", "question_id", "input_sha256", "run_sha256", "windows",
                          "prediction", "candidates", "null_score_difference"}, "Invalid question record fields.")
    require(type(body["question_index"]) is int and body["question_index"] == index
            and body["question_id"] == question_id(selected)
            and body["input_sha256"] == canonical_sha256(selected)
            and body["run_sha256"] == run_id, "Saved question belongs to a different input or run.")
    require(type(body["windows"]) is int and body["windows"] > 0, "Invalid saved window count.")
    qid = body["question_id"]
    validate_reference_predictions(selected, {qid: body["candidates"]}, {qid: body["prediction"]},
                                   {qid: body["null_score_difference"]})
    return body


def load_completed(root, inputs, run_id):
    allowed = {f"{i:06d}.json": i for i in range(len(inputs))}
    completed = {}
    for path in sorted((root / "questions").glob("*.json")):
        require(path.name in allowed, "Unexpected saved question filename.")
        index = allowed[path.name]
        record = read_json(path)
        validate_record(record, index, inputs[index], run_id)
        completed[index] = record
    return completed


def process_questions(root, inputs, run_id, producer, limit=None):
    require(limit is None or (type(limit) is int and 1 <= limit <= len(inputs)), "Invalid question limit.")
    completed = load_completed(root, inputs, run_id)
    print(f"Verified saved progress: {len(completed)}/{len(inputs)} questions", flush=True)
    new = 0
    for index in range(limit or len(inputs)):
        if index in completed:
            continue
        selected = inputs[index]
        print(f"Question {index + 1}/{len(inputs)}: {question_id(selected)}", flush=True)
        result = producer(selected)
        record = make_record(index, selected, run_id, result)
        validate_record(record, index, selected, run_id)
        atomic_json(root / "questions" / f"{index:06d}.json", record)
        completed[index] = record
        new += 1
        print(f"  Saved {len(completed)}/{len(inputs)}; {result['windows']} windows; "
              f"prediction {result['prediction'][:100]!r}", flush=True)
    return completed, new


def aggregate(inputs, completed, run_id):
    require(set(completed) == set(range(len(inputs))), "Full-test outputs require every question; partial run preserved.")
    predictions, nbest, null_odds = {}, {}, {}
    for index, selected in enumerate(inputs):
        body = validate_record(completed[index], index, selected, run_id)
        qid = body["question_id"]
        require(qid not in predictions, "Duplicate question during aggregation.")
        predictions[qid], nbest[qid], null_odds[qid] = body["prediction"], body["candidates"], body["null_score_difference"]
    return predictions, nbest, null_odds


def cache_tokenizer(tokenizer):
    """Cache repeated words across category questions; return independent lists."""
    original = tokenizer.tokenize
    @lru_cache(maxsize=65536)
    def cached(text, kwargs):
        return tuple(original(text, **dict(kwargs)))
    def tokenize(text, **kwargs):
        return list(cached(text, tuple(sorted(kwargs.items()))))
    tokenizer.tokenize = tokenize


def initialize_runtime(device):
    versions = runtime_versions()
    for package, expected in EVALUATION_PACKAGES.items():
        require(importlib.metadata.version(package) == expected, "Install the pinned evaluation requirements.")
    versions.update({name: importlib.metadata.version(name) for name in ("regex", "huggingface-hub")})
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    os.environ["TORCH_ALLOW_TF32_CUBLAS_OVERRIDE"] = "0"
    import torch
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    hardware = {"device": device, "machine": platform.machine(), "system": platform.system(),
                "processor": platform.processor(), "cpu_threads": torch.get_num_threads()}
    if device == "cuda":
        require(torch.version.cuda == "12.6" and torch.cuda.is_available(),
                "CUDA 12.6 GPU runtime unavailable. Install torch==2.9.1+cu126 from the cu126 index; "
                "if already installed, share the CUDA/driver error. No CPU fallback was started.")
        properties = torch.cuda.get_device_properties(0)
        driver = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                                capture_output=True, text=True, timeout=10, check=False)
        require(driver.returncode == 0 and driver.stdout.strip(), "Could not record the NVIDIA driver version.")
        hardware.update({"gpu_name": properties.name, "gpu_memory_bytes": properties.total_memory,
                         "compute_capability": [properties.major, properties.minor],
                         "cuda_runtime": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
                         "driver_versions": sorted(set(driver.stdout.splitlines())),
                         "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES")})
    require(device in {"cpu", "cuda"}, "Unsupported device.")
    return torch, {"packages": versions, "hardware": hardware}


class InferenceEngine:
    def __init__(self, torch, root, reference, device):
        from transformers import RobertaForQuestionAnswering, RobertaTokenizer
        self.torch, self.device = torch, device
        self.tokenizer = RobertaTokenizer.from_pretrained(str(root), local_files_only=True,
                                                        do_lower_case=False, add_prefix_space=False)
        require(not self.tokenizer.is_fast and self.tokenizer.pad_token_id == 1
                and self.tokenizer.cls_token_id == 0, "Unexpected tokenizer.")
        cache_tokenizer(self.tokenizer)
        print(f"Loading verified checkpoint on {device}; batch 1; float32; eager attention; TF32 off...", flush=True)
        self.model, loading = RobertaForQuestionAnswering.from_pretrained(str(root), local_files_only=True,
            use_safetensors=False, weights_only=True, output_loading_info=True,
            attn_implementation="eager", dtype=torch.float32)
        validate_loading(loading)
        self.model.to(device).eval()
        spec = importlib.util.spec_from_file_location("clauseanchor_full_cuad_decoder", reference)
        self.decoder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.decoder)

    def __call__(self, selected):
        from transformers.data.processors.squad import (
            SquadExample, SquadResult, squad_convert_example_to_features, squad_convert_example_to_features_init,
        )
        torch = self.torch
        doc = selected["data"][0]
        paragraph = doc["paragraphs"][0]
        q = paragraph["qas"][0]
        example = SquadExample(qas_id=q["id"], question_text=q["question"], context_text=paragraph["context"],
            answer_text=None, start_position_character=None, title=doc["title"], answers=[], is_impossible=False)
        squad_convert_example_to_features_init(self.tokenizer)
        features = squad_convert_example_to_features(example, max_seq_length=512, doc_stride=256,
            max_query_length=64, padding_strategy="max_length", is_training=False)
        for index, feature in enumerate(features):
            feature.example_index, feature.unique_id = 0, 1000000000 + index
        validate_coverage(features, len(example.doc_tokens))
        results, last_update = [], time.monotonic()
        with torch.inference_mode():
            for index, feature in enumerate(features):
                output = self.model(input_ids=torch.tensor([feature.input_ids], dtype=torch.long, device=self.device),
                    attention_mask=torch.tensor([feature.attention_mask], dtype=torch.long, device=self.device))
                require(tuple(output.start_logits.shape) == (1, 512) and tuple(output.end_logits.shape) == (1, 512)
                        and torch.isfinite(output.start_logits).all().item()
                        and torch.isfinite(output.end_logits).all().item(), "Invalid model logits.")
                results.append(SquadResult(feature.unique_id, output.start_logits[0].cpu().tolist(),
                                           output.end_logits[0].cpu().tolist()))
                if time.monotonic() - last_update >= 15:
                    print(f"  Window {index + 1}/{len(features)}", flush=True)
                    last_update = time.monotonic()
        with TemporaryDirectory(prefix="cuad-predict-") as tmp:
            paths = [Path(tmp) / name for name in ("predictions.json", "nbest.json", "null_odds.json")]
            self.decoder.compute_predictions_logits(selected, [example], features, results, 20, 512, False,
                *(str(path) for path in paths), False, True, 0.0, self.tokenizer)
            predictions, nbest, null_odds = [read_json(path) for path in paths]
        return {"windows": len(features), "prediction": predictions[q["id"]],
                "candidates": [{key: candidate[key] for key in CANDIDATE_FIELDS} for candidate in nbest[q["id"]]],
                "null_score_difference": null_odds[q["id"]]}


def score_fresh(test, nbest, released_report, reference):
    by_title = {doc["title"]: doc for doc in test["data"]}
    results, curves = {}, {}
    for label, previous in released_report["results"].items():
        dataset = {"data": [by_title[title] for title in previous["source_titles"]]}
        answers = reference.get_answers(dataset)
        selected = {qid: nbest[qid] for qid in answers}
        print(f"Scoring fresh {label}: {len(answers)} questions...", flush=True)
        local = score_predictions(answers, selected)
        original = reference_score(reference, answers, selected)
        error = assert_parity(local, original)
        require(all(math.isfinite(v) for v in local["metrics"].values()), "Undefined fresh aggregate metric.")
        results[label] = {"source_documents": len(dataset["data"]), "questions": len(answers),
            "source_titles": previous["source_titles"], "metrics": local["metrics"],
            "original_evaluator_metrics": original["metrics"], "maximum_absolute_evaluator_parity_error": error,
            "released_metrics": previous["metrics"],
            "fresh_minus_released": {k: local["metrics"][k] - previous["metrics"][k] for k in local["metrics"]},
            "maximum_recall_including_final_point": max(local["recalls"]),
            "maximum_recall_on_official_precision_at_recall_grid": max(local["recalls"][:-1])}
        curves[label] = finite_json({k: v for k, v in local.items() if k != "metrics"})
    return results, curves


def finish(repo, root, test, inputs, completed, run_id, config):
    predictions, nbest, null_odds = aggregate(inputs, completed, run_id)
    counts = validate_reference_predictions(test, nbest, predictions, null_odds)
    # Reconstructs sources and reviewed family membership, verifies package and
    # source pins, and recomputes the released reference scores without writing.
    released_report, _ = evaluate_released(repo)
    results, curves = score_fresh(test, nbest, released_report, load_reference(repo, config))
    released_root = repo / MODEL_DIR / "roberta-base"
    released_top = read_json(released_root / "predictions_.json")
    released_nbest = read_json(released_root / "nbest_predictions_.json")
    report = {"report_version": 1, "status": "fresh_inference_scored_reproduction_review_pending",
        "run_sha256": run_id, "fresh_inference_complete": True, "baseline_reproduction_complete": False,
        "training_performed": False, "calibration_performed": False, "policy_threshold_selected": False,
        "metric_scale": "0_to_1", "results": results,
        "top_prediction_matches": sum(predictions[q] == released_top[q] for q in predictions),
        "ranked_candidate_text_matches": sum([c["text"] for c in nbest[q]] == [c["text"] for c in released_nbest[q]]
                                             for q in predictions),
        "excluded_confirmed_overlap_test_titles": released_report["excluded_confirmed_overlap_test_titles"],
        "retained_unresolved_test_titles": released_report["retained_unresolved_test_titles"],
        "limitations": released_report["limitations"] + [
            "Fresh-vs-released differences require review; no post-hoc acceptance tolerance was selected."]}
    artifacts = dict(zip(FINAL_FILES[:5], (predictions, nbest, null_odds, report, curves)))
    for name, value in artifacts.items():
        atomic_json(root / name, value)
    atomic_json(root / "manifest.json", {"manifest_version": 1, "run_sha256": run_id,
        "status": "complete_fresh_inference_and_scoring", **counts,
        "windows": sum(r["payload"]["windows"] for r in completed.values()),
        "question_record_digests": [completed[i]["payload_sha256"] for i in range(len(inputs))],
        "output_canonical_sha256": {name: canonical_sha256(value) for name, value in artifacts.items()},
        "baseline_reproduction_complete": False})
    for label, result in results.items():
        m = result["metrics"]
        print(f"{label}: AUPR {100*m['aupr']:.3f}%; P@80R {100*m['prec_at_80_recall']:.3f}%; "
              f"P@90R {100*m['prec_at_90_recall']:.3f}%", flush=True)
        print(f"  Fresh minus released (percentage points): "
              + str({k: round(100*v, 6) for k, v in result["fresh_minus_released"].items()}), flush=True)
    print(f"Released top predictions matched: {report['top_prediction_matches']}/{len(inputs)}")
    print("PASS: all 4182 fresh predictions scored; local and original evaluators agree.")
    print("Review fresh-vs-released differences before declaring baseline reproduction complete.")


def run(repo, device="cuda", limit=None, name=None):
    config = read_json(repo / CONFIG)
    validate_config(config)
    require(canonical_sha256(config) == SOURCE_PIN, "Baseline source configuration changed.")
    require(canonical_sha256(read_json(repo / FAMILY_PATH)) == FAMILY_PIN, "Reviewed family policy changed.")
    model_root = repo / MODEL_DIR / "roberta-base"
    verify_file(repo / config["official_test"]["path"], config["official_test"])
    for filename in (*MODEL_FILES, "predictions_.json", "nbest_predictions_.json"):
        verify_file(model_root / filename, config["members"][filename])
    require(not any((model_root / name).exists() for name in ("added_tokens.json", "tokenizer.json")),
            "Unpinned extra tokenizer assets found in the released checkpoint directory.")
    reference = repo / REFERENCE_DIR / "utils.py"
    for filename in ("utils.py", "evaluate.py", "category_descriptions.csv"):
        verify_file(repo / REFERENCE_DIR / filename, config["reference_files"][filename])
    validate_model_metadata(read_json(model_root / "config.json"), read_json(model_root / "tokenizer_config.json"))
    test = read_json(repo / config["official_test"]["path"])
    inputs = inference_inputs(test)
    require(len(test["data"]) == 102 and len(inputs) == 4182, "Official test counts changed.")
    require(limit is None or (type(limit) is int and 1 <= limit <= len(inputs)), "Question limit must be 1..4182.")
    relative = f"{OUTPUT_BASE}/{output_name(device, name)}"
    paths = [relative + "/" + n for n in ("run.lock", "run.json", *FINAL_FILES)]
    paths.extend(f"{relative}/questions/{i:06d}.json" for i in range(len(inputs)))
    verify_ignored_assets(repo, paths)
    torch, runtime = initialize_runtime(device)
    code_digests = {n: hashlib.sha256((repo / "ml/scripts" / n).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                    for n in CODE_FILES}
    identity = {"run_version": 1, "source_config_sha256": SOURCE_PIN, "family_manifest_sha256": FAMILY_PIN,
        "source_documents": 102, "questions": 4182, "runtime": runtime, "code_sha256": code_digests,
        "settings": {**config["reference_inference_settings"], "batch_size": 1, "dtype": "float32",
            "attention_implementation": "eager", "tf32": False, "deterministic_algorithms": True,
            "cublas_workspace_config": ":4096:8", "null_score_diff_threshold": 0.0}}
    root = repo / relative
    print("Pinned checkpoint, tokenizer, decoder, official test and family policy: verified", flush=True)
    print(f"Device: {device}; {runtime['hardware'].get('gpu_name', runtime['hardware']['processor'])}", flush=True)
    engine = None
    def produce(selected):
        nonlocal engine
        if engine is None:
            engine = InferenceEngine(torch, model_root, reference, device)
        return engine(selected)
    with run_lock(root):
        run_id = bind_run(root, identity)
        completed, new = process_questions(root, inputs, run_id, produce, limit)
        print(f"New questions this run: {new}; total saved: {len(completed)}/{len(inputs)}", flush=True)
        if len(completed) == len(inputs):
            finish(repo, root, test, inputs, completed, run_id, config)
        else:
            print("PASS: limited inference run saved and verified; full-test evaluation remains pending.")
        print(f"Output directory: {relative}")
        print("No training, calibration or operating-policy selection performed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--limit-questions", type=int, default=None)
    parser.add_argument("--run-name", default=None, help="New directory name for a deliberately separate runtime/run.")
    args = parser.parse_args()
    try:
        run(Path(__file__).resolve().parents[2], args.device, args.limit_questions, args.run_name)
    except KeyboardInterrupt:
        print("\nStopped. Completed questions are saved. Rerun the same command to resume.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
