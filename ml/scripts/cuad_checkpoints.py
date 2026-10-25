"""Transactional local training checkpoints. Caller holds the run lock.

A checkpoint contains model, AdamW, AMP scaler, RNG and training position.
Publish the complete directory before replacing latest.json. Never restore an
unfinished directory or silently fall back from a corrupt latest checkpoint.
Keep two committed checkpoints, protecting both the latest and selected best.
"""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
from tempfile import NamedTemporaryFile, TemporaryDirectory

import numpy as np
import torch

from audit_cuad_questions import require
from check_cuad_families import canonical_sha256, read_json
from prepare_cuad_baseline import verify_file
from run_cuad_baseline import atomic_json

NAME = re.compile(r"checkpoint-[0-9]{6}")


def file_spec(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return {"size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def replace_json(path, value):
    """Only mutable pointer; previous file survives any failure before replace."""
    pending = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=".pointer-", suffix=".tmp", delete=False) as handle:
            pending = Path(handle.name)
            handle.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, path)
    finally:
        if pending is not None and pending.exists():
            pending.unlink()


def rng_state(device):
    numpy_state = np.random.get_state()
    return {"torch": torch.get_rng_state(), "cuda": torch.cuda.get_rng_state_all() if device.type == "cuda" else [],
            "python": random.getstate(), "numpy": [numpy_state[0], numpy_state[1].tolist(),
                                                     int(numpy_state[2]), int(numpy_state[3]), float(numpy_state[4])]}


def restore_rng(state, device):
    torch.set_rng_state(state["torch"])
    require(len(state["cuda"]) == (torch.cuda.device_count() if device.type == "cuda" else 0), "RNG device count differs.")
    if device.type == "cuda":
        torch.cuda.set_rng_state_all(state["cuda"])
    random.setstate(state["python"])
    name, values, position, has_gauss, cached = state["numpy"]
    np.random.set_state((name, np.asarray(values, dtype=np.uint32), position, has_gauss, cached))


def latest(root, run_sha):
    pointer = read_json(root / "latest.json")
    name = pointer["checkpoint"]
    require(isinstance(name, str) and NAME.fullmatch(name) and pointer["run_sha256"] == run_sha, "Invalid checkpoint pointer.")
    directory = root / "checkpoints" / name
    manifest = read_json(directory / "manifest.json")
    require(manifest["run_sha256"] == run_sha and manifest["checkpoint"] == name
            and pointer["manifest_sha256"] == canonical_sha256(manifest), "Checkpoint manifest changed.")
    require(set(manifest["files"]) in ({"training.pt", "progress.json"}, {"training.pt", "progress.json", "evaluation.json"}),
            "Unexpected checkpoint contents.")
    for filename, spec in manifest["files"].items():
        verify_file(directory / filename, spec)
    return directory, manifest, read_json(directory / "progress.json")


def save(root, run_sha, model, optimizer, scaler, progress, evaluation=None, new_best=False):
    root = Path(root)
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    previous = None
    if (root / "latest.json").exists():
        old_pointer = read_json(root / "latest.json")
        require(old_pointer["run_sha256"] == run_sha and NAME.fullmatch(old_pointer["checkpoint"]),
                "Existing checkpoint pointer belongs to another run.")
        previous = old_pointer["checkpoint"]
    existing = sorted(p for p in checkpoints.iterdir() if p.is_dir() and NAME.fullmatch(p.name))
    generation = max((int(p.name.split("-")[1]) for p in existing), default=0) + 1
    require(generation <= 999999, "Checkpoint generation overflow.")
    name = f"checkpoint-{generation:06d}"
    state = deepcopy(progress)
    if new_best:
        require(evaluation is not None and evaluation["selection_eligible"] is True, "Probe cannot become best checkpoint.")
        state["best_checkpoint"] = name
    if state.get("best_checkpoint") and state["best_checkpoint"] != name:
        require(NAME.fullmatch(state["best_checkpoint"]) and (checkpoints / state["best_checkpoint"] / "manifest.json").is_file(),
                "Selected best checkpoint is missing.")
    expected_bytes = sum(p.numel() * p.element_size() for p in model.parameters()) * 3
    require(shutil.disk_usage(root).free > expected_bytes + 256 * 1024**2, "Not enough free disk space for a safe checkpoint save.")
    device = next(model.parameters()).device
    with TemporaryDirectory(prefix=".pending-", dir=checkpoints) as temporary:
        staging = Path(temporary)
        payload = {"run_sha256": run_sha, "progress": state, "model": model.state_dict(),
                   "optimizer": optimizer.state_dict(), "scaler": scaler.state_dict(), "rng": rng_state(device)}
        with (staging / "training.pt").open("wb") as handle:
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        atomic_json(staging / "progress.json", state)
        names = ["training.pt", "progress.json"]
        if evaluation is not None:
            atomic_json(staging / "evaluation.json", evaluation)
            names.append("evaluation.json")
        manifest = {"run_sha256": run_sha, "checkpoint": name,
                    "files": {filename: file_spec(staging / filename) for filename in names}}
        atomic_json(staging / "manifest.json", manifest)
        os.replace(staging, checkpoints / name)
    replace_json(root / "latest.json", {"run_sha256": run_sha, "checkpoint": name,
                                       "manifest_sha256": canonical_sha256(manifest)})
    # Only prune after the new complete checkpoint is the committed latest.
    keep = {name}
    if state.get("best_checkpoint"):
        keep.add(state["best_checkpoint"])
    owned = []
    for path in [*existing, checkpoints / name]:
        if (path / "manifest.json").is_file() and read_json(path / "manifest.json").get("run_sha256") == run_sha:
            owned.append(path)
    if len(keep) < 2 and previous is not None:
        keep.add(previous)
    for path in owned:
        if path.name not in keep:
            shutil.rmtree(path)
    print(f"Saved {name}: optimizer step {state['global_step']}; next epoch index {state['epoch']}, window offset {state['offset']}", flush=True)
    return state


def restore(root, run_sha, model, optimizer, scaler):
    directory, manifest, progress = latest(Path(root), run_sha)
    # Restricted state-dict loading; never deserialize arbitrary Python classes.
    payload = torch.load(directory / "training.pt", map_location="cpu", weights_only=True)
    require(payload["run_sha256"] == run_sha and canonical_sha256(payload["progress"]) == canonical_sha256(progress),
            "Checkpoint state and progress disagree.")
    model.load_state_dict(payload["model"], strict=True)
    optimizer.load_state_dict(payload["optimizer"])
    scaler.load_state_dict(payload["scaler"])
    restore_rng(payload["rng"], next(model.parameters()).device)
    print(f"Restored {directory.name}: optimizer step {progress['global_step']}", flush=True)
    return progress
