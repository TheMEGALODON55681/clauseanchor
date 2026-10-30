from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.scope import load_catalogue

# Tanishq's file, read in place. He changes catalogue_version and support_status as categories get
# validated, so no test here pins either one.
REAL = Path(__file__).resolve().parents[2] / "ml" / "configs" / "catalogue.json"

# The ten categories plan 4.3 annotates
ANNOTATED = {
    "in.arbitration",
    "in.seat_venue",
    "in.stamping_registration",
    "in.forum_selection",
    "in.dispute_escalation",
    "cuad.non_compete",
    "cuad.liquidated_damages",
    "cuad.cap_on_liability",
    "cuad.uncapped_liability",
    "cuad.governing_law",
}


def test_the_default_path_is_the_ml_file_from_any_working_directory(tmp_path: Path) -> None:
    # A fresh interpreter started elsewhere: in this process the working directory may already be
    # the repository root, and a path built from it would pass.
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from app.config import Settings; print(Settings().catalogue_path)"
    )
    backend = str(Path(__file__).resolve().parents[1])
    run = subprocess.run(
        [sys.executable, "-I", "-c", code, backend],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert Path(run.stdout.strip()) == REAL


def test_the_real_catalogue_loads_with_41_cuad_and_5_india_rows() -> None:
    categories = load_catalogue(Settings().catalogue_path).categories
    ids = [c.id for c in categories]
    assert len(ids) == len(set(ids)) == 46
    assert Counter(c.source for c in categories) == {"cuad": 41, "india_extension": 5}
    assert ANNOTATED - set(ids) == set()  # a failure lists the missing ids


def test_ready_and_capabilities_serve_the_real_file_unchanged() -> None:
    raw = json.loads(REAL.read_text(encoding="utf-8-sig"))
    with TestClient(create_app(Settings())) as client:
        ready = client.get("/api/v1/ready")
        capabilities = client.get("/api/v1/capabilities")
    assert ready.status_code == 200
    assert ready.json()["checks"]["catalogue"] == "ok"
    assert capabilities.status_code == 200
    body = capabilities.json()
    assert len(body["categories"]) == 46
    assert body["catalogue_version"] == raw["catalogue_version"]
    assert body["categories"] == raw["categories"]
