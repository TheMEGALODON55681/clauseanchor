"""Acquire the authors' CUAD RoBERTa-base checkpoint and reference predictions.

Run: python ml/scripts/prepare_cuad_baseline.py
First run downloads about 447 MB and keeps about 1 GB of ignored assets.
Uses the existing data environment; no Torch/Transformers installation or GPU.
No downloaded Python code or pickle checkpoint is executed/deserialized here.
The source config pins the complete archive, every member and reference file.
All content is verified before publication; differing existing files are kept
and cause failure. An interrupted download can be retried by rerunning this
command (it restarts that download). Completed assets are reused offline.

Released predictions are a reproduction reference, not a new inference run.
This checkpoint was trained on the original training split and must not be
used as the initialization for later clean-fit training/calibration claims.
"""

import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import stat
import subprocess
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen
from zipfile import ZipFile

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, fields, read_json


CONFIG = "ml/configs/cuad_baseline_source.json"
MODEL_DIR = "models/cuad_baseline"
REFERENCE_DIR = "data/external/cuad_baseline"
REPORT = "data/processed/cuad/baseline_assets.json"
MEMBERS = {"config.json", "pytorch_model.bin", "training_args.bin", "vocab.json", "merges.txt",
           "tokenizer_config.json", "special_tokens_map.json", "predictions_.json",
           "nbest_predictions_.json", "null_odds_.json"}
REFERENCES = {"readme.md", "run.sh", "train.py", "utils.py", "evaluate.py", "category_descriptions.csv"}
REPO_ID = "The-Atticus-Project/cuad"
REVISION = "67faa0e6023b04fcaae6cc09497ab00e5d63a2a2"
ARCHIVE_URL = "https://zenodo.org/api/records/4599830/files/roberta-base.zip/content"
CHUNK = 1024 * 1024


def validate_config(config):
    fields(config, {"config_version", "purpose", "archive", "members", "reference_source",
                    "reference_files", "official_test", "reference_inference_settings"}, "baseline source")
    require(type(config["config_version"]) is int and config["config_version"] == 1
            and config["purpose"] == "official_baseline_reference_assets", "Unsupported baseline source config.")
    require(config["reference_source"] == {"repo_id": REPO_ID, "revision": REVISION}, "Reference source changed.")
    fields(config["members"], MEMBERS, "checkpoint members")
    fields(config["reference_files"], REFERENCES, "reference files")
    archive = config["archive"]
    fields(archive, {"url", "size_bytes", "sha256", "published_md5"}, "archive")
    require(archive["url"] == ARCHIVE_URL and archive["size_bytes"] == 447429160
            and archive["published_md5"] == "63855b3d798f010164974cafc3ade2fa", "Released archive identity changed.")
    specs = [archive, config["official_test"], *config["members"].values(), *config["reference_files"].values()]
    for spec in specs:
        require(type(spec["size_bytes"]) is int and spec["size_bytes"] > 0, "Expected a positive integer file size.")
        require(type(spec["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", spec["sha256"]), "Invalid SHA-256.")
    test = config["official_test"]
    require(test["path"] == "data/raw/cuad/official/test.json"
            and test["source_documents"] == 102 and test["questions"] == 4182, "Official test identity changed.")
    settings = {"max_seq_length": 512, "doc_stride": 256, "max_query_length": 64,
                "max_answer_length": 512, "n_best_size": 20, "version_2_with_negative": True,
                "do_lower_case": False, "use_fast_tokenizer": False}
    require(canonical_sha256(config["reference_inference_settings"]) == canonical_sha256(settings),
            "Original baseline settings changed; these are separate from clean training settings.")


def verify_file(path, spec):
    require(path.is_file() and path.stat().st_size == spec["size_bytes"], f"File size differs: {path.name}")
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    require(digest == spec["sha256"], f"SHA-256 differs; existing files are not replaced: {path.name}")
    if "published_md5" in spec:
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "md5").hexdigest()
        require(digest == spec["published_md5"], "Archive differs from the published Zenodo MD5.")


def copy_checked(source, destination, spec, progress=False):
    """Bound memory and output size while copying a download or ZIP member."""
    total, digest = 0, hashlib.sha256()
    with destination.open("xb") as out:
        while chunk := source.read(CHUNK):
            previous = total
            total += len(chunk)
            require(total <= spec["size_bytes"], f"Content exceeds pinned size: {destination.name}")
            digest.update(chunk)
            out.write(chunk)
            if progress and total // (32 * CHUNK) != previous // (32 * CHUNK):
                print(f"  Downloaded {total // CHUNK} MiB", flush=True)
    require(total == spec["size_bytes"] and digest.hexdigest() == spec["sha256"],
            f"Downloaded/extracted content differs: {destination.name}")


def acquire(url, destination, spec):
    request = Request(url, headers={"User-Agent": "ClauseAnchor-CUAD-baseline/1.0"})
    with urlopen(request, timeout=60) as response:
        copy_checked(response, destination, spec, progress=spec["size_bytes"] > 32 * CHUNK)
    verify_file(destination, spec)


def check_archive(archive, members):
    expected = {"roberta-base/", *("roberta-base/" + name for name in members)}
    names = archive.namelist()
    require(len(names) == len(expected) and set(names) == expected, "Unexpected, missing or duplicate ZIP members.")
    for info in archive.infolist():
        require(not stat.S_ISLNK(info.external_attr >> 16) and not (info.flag_bits & 1),
                "Symlink or encrypted ZIP member rejected.")
        if info.filename == "roberta-base/":
            require(info.is_dir() and info.file_size == 0, "Invalid archive directory.")
        else:
            require(info.file_size == members[info.filename.split("/")[1]]["size_bytes"], "ZIP member size differs.")


def validate_reference_predictions(test, nbest, predictions, null_odds):
    ids = [q["id"] for d in test["data"] for p in d["paragraphs"] for q in p["qas"]]
    require(len(ids) == len(set(ids)), "Duplicate official test question ID.")
    for value in (nbest, predictions, null_odds):
        require(type(value) is dict and set(value) == set(ids), "Released prediction IDs differ from official test.")
    count = 0
    for qid in ids:
        candidates = nbest[qid]
        require(type(candidates) is list and bool(candidates), "Missing candidate list.")
        for candidate in candidates:
            fields(candidate, {"text", "probability", "start_logit", "end_logit"}, "released candidate")
            require(type(candidate["text"]) is str, "Candidate text must be a string.")
            for key in ("probability", "start_logit", "end_logit"):
                require(type(candidate[key]) in (int, float) and math.isfinite(candidate[key]), "Invalid candidate number.")
            require(0 <= candidate["probability"] <= 1, "Probability outside [0, 1].")
        require(math.isclose(sum(c["probability"] for c in candidates), 1, rel_tol=0, abs_tol=1e-6),
                "Candidate probabilities do not sum to one.")
        require(type(predictions[qid]) is str, "Invalid released top prediction.")
        require(type(null_odds[qid]) in (int, float) and math.isfinite(null_odds[qid]), "Invalid released null score.")
        count += len(candidates)
    return {"source_documents": len(test["data"]), "questions": len(ids), "nbest_candidates": count}


def validate_model_metadata(model_config, tokenizer_config):
    expected = {"architectures": ["RobertaForQuestionAnswering"], "model_type": "roberta",
                "hidden_size": 768, "num_hidden_layers": 12, "num_attention_heads": 12, "vocab_size": 50265}
    require(all(model_config.get(k) == v for k, v in expected.items()), "Unexpected released model architecture.")
    require(tokenizer_config.get("do_lower_case") is False
            and tokenizer_config.get("add_prefix_space") is False
            and tokenizer_config.get("model_max_length") == 512, "Unexpected released tokenizer settings.")


def publish(repo, staged, specs):
    """Check every existing destination before publishing any missing file."""
    for relative in staged:
        path = repo / relative
        if path.exists():
            verify_file(path, specs[relative])
    created = 0
    for relative, source in staged.items():
        target = repo / relative
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation cannot replace a file created after the preflight.
        with target.open("xb") as out, source.open("rb") as incoming:
            try:
                shutil.copyfileobj(incoming, out, CHUNK)
            except BaseException:
                out.close()
                target.unlink()
                raise
        created += 1
    return created


def verify_ignored_assets(repo, paths):
    """Use binary, NUL-delimited paths so Windows newlines cannot alter them."""
    encoded = {path.encode("utf-8") for path in paths}
    ignored = subprocess.run(["git", "check-ignore", "--stdin", "-z"],
                             input=b"\0".join(path.encode("utf-8") for path in paths) + b"\0",
                             cwd=repo, capture_output=True, check=False)
    require(ignored.returncode in (0, 1),
            f"Git ignore check failed (exit {ignored.returncode}): "
            + ignored.stderr.decode("utf-8", errors="replace").strip())
    require(not ignored.stdout or ignored.stdout.endswith(b"\0"), "Malformed Git ignore output.")
    actual = set(ignored.stdout.split(b"\0")[:-1]) if ignored.stdout else set()
    require(actual <= encoded, "Git returned unexpected asset paths.")
    missing = sorted(path.decode("utf-8") for path in encoded - actual)
    require(not missing,
            "Baseline assets are not ignored or are already tracked: " + ", ".join(missing)
            + ". No downloads started; check these paths in Git before proceeding.")


def prepare(repo):
    config = read_json(repo / CONFIG)
    validate_config(config)
    verify_file(repo / config["official_test"]["path"], config["official_test"])
    archive_relative = MODEL_DIR + "/roberta-base.zip"
    specs = {archive_relative: config["archive"]}
    specs.update({MODEL_DIR + "/roberta-base/" + n: s for n, s in config["members"].items()})
    specs.update({REFERENCE_DIR + "/" + n: s for n, s in config["reference_files"].items()})
    paths = [*specs, REPORT]
    for relative in paths:
        require((repo / relative).resolve().is_relative_to(repo.resolve()), "Asset path escapes the repository.")
    verify_ignored_assets(repo, paths)
    for relative, spec in specs.items():
        if (repo / relative).exists():
            verify_file(repo / relative, spec)
    model_dir = repo / MODEL_DIR
    model_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".prepare-", dir=model_dir) as temp:
        staging, staged = Path(temp), {}
        archive_path = repo / archive_relative
        if not archive_path.exists():
            archive_path = staging / "roberta-base.zip"
            print("Downloading authors' RoBERTa-base archive (447.4 MB)...", flush=True)
            acquire(config["archive"]["url"], archive_path, config["archive"])
        staged[archive_relative] = archive_path
        with ZipFile(archive_path) as archive:
            check_archive(archive, config["members"])
            for name, spec in config["members"].items():
                relative = MODEL_DIR + "/roberta-base/" + name
                path = repo / relative
                if not path.exists():
                    path = staging / name
                    with archive.open("roberta-base/" + name) as source:
                        copy_checked(source, path, spec)
                staged[relative] = path
        for name, spec in config["reference_files"].items():
            relative = REFERENCE_DIR + "/" + name
            path = repo / relative
            if not path.exists():
                path = staging / ("reference-" + name)
                print(f"Downloading pinned reference: {name}", flush=True)
                acquire(f"https://raw.githubusercontent.com/{REPO_ID}/{REVISION}/{name}", path, spec)
            staged[relative] = path
        model_files = {n: staged[MODEL_DIR + "/roberta-base/" + n] for n in MEMBERS}
        validate_model_metadata(read_json(model_files["config.json"]), read_json(model_files["tokenizer_config.json"]))
        counts = validate_reference_predictions(read_json(repo / config["official_test"]["path"]),
                    *(read_json(model_files[n]) for n in ("nbest_predictions_.json", "predictions_.json", "null_odds_.json")))
        require(all(counts[k] == config["official_test"][k] for k in ("source_documents", "questions")),
                "Official test counts differ.")
        report = {"manifest_version": 1, "status": "baseline_reference_assets_verified",
                  "source_config_canonical_sha256": canonical_sha256(config), "reference_source": config["reference_source"],
                  "official_test": config["official_test"], "released_prediction_counts": counts,
                  "files": specs.copy(), "reference_inference_settings": config["reference_inference_settings"],
                  "new_inference_run_completed": False, "evaluator_parity_verified": False,
                  "baseline_reproduction_complete": False,
                  "training_exposure": "original_official_train; not a clean-fit initialization"}
        payload = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        report_path = staging / "baseline_assets.json"
        report_path.write_bytes(payload)
        specs[REPORT] = {"size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        staged[REPORT] = report_path
        created = publish(repo, staged, specs)
    for relative, spec in specs.items():
        verify_file(repo / relative, spec)
    return created, counts


def main():
    created, counts = prepare(Path(__file__).resolve().parents[2])
    print("Published archive MD5, pinned SHA-256 and all extracted file hashes: verified")
    print("Model metadata: CUAD RoBERTa-base QA; 12 layers; hidden size 768")
    print(f"Official test: {counts['source_documents']} documents; {counts['questions']} questions; unchanged")
    print(f"Released predictions: {counts['questions']} question IDs; {counts['nbest_candidates']} candidates verified")
    print("Original inference settings recorded: length 512; stride 256; slow tokenizer")
    print(f"Created {created} baseline asset files." if created else "Existing baseline assets match; no files changed.")
    print(f"Manifest: {REPORT}")
    print("PASS: authors' checkpoint, reference predictions and source files prepared; all assets ignored by Git.")
    print("No model loaded or trained. Evaluator parity and fresh inference remain pending.")


if __name__ == "__main__":
    main()
