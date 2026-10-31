"""The analyzer factory, and the promise that stub mode loads no model library."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from clauseanchor_core import StubAnalyzer, read_exact_text

from app.config import STUB_FIXTURE_DIR, Settings
from app.services import analysis

BACKEND = Path(__file__).parents[1]
DIGEST = "cd" * 32


def test_stub_mode_builds_the_stub_from_the_core_fixture() -> None:
    analyzer = analysis.build_analyzer(Settings())
    assert isinstance(analyzer, StubAnalyzer)
    assert analyzer.source_text == read_exact_text(STUB_FIXTURE_DIR / "sample_contract.txt")


def test_real_mode_builds_the_candidate_only_analyzer_on_cpu_with_the_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[object, dict[str, object]]] = []

    class Fake:
        def __init__(self, artifact_dir: object, **kwargs: object) -> None:
            seen.append((artifact_dir, kwargs))

    monkeypatch.setattr(analysis, "CandidateOnlyAnalyzer", Fake)
    settings = Settings(analyzer="real", artifacts_dir=tmp_path, artifacts_sha256=DIGEST)
    assert isinstance(analysis.build_analyzer(settings), Fake)
    assert seen == [
        (tmp_path, {"expected_manifest_sha256": DIGEST, "device": "cpu", "batch_size": 1})
    ]


@pytest.mark.parametrize("missing", ["artifacts_dir", "artifacts_sha256"])
def test_real_mode_with_incomplete_settings_fails_and_never_builds_the_stub(
    tmp_path: Path, missing: str
) -> None:
    fields = {"artifacts_dir": tmp_path, "artifacts_sha256": DIGEST}
    fields[missing] = None  # type: ignore[assignment]
    with pytest.raises(ValueError):
        analysis.build_analyzer(Settings(analyzer="real", **fields))  # type: ignore[arg-type]


def test_a_directory_that_is_not_a_bundle_fails_and_is_not_replaced_by_the_stub(
    tmp_path: Path,
) -> None:
    # The core checks the manifest before it reaches any model code, so this needs no torch
    with pytest.raises(OSError):
        analysis.build_analyzer(
            Settings(analyzer="real", artifacts_dir=tmp_path, artifacts_sha256=DIGEST)
        )


def test_the_core_and_the_app_in_stub_mode_import_no_model_library() -> None:
    code = textwrap.dedent(
        """
        import json, sys, time
        import clauseanchor_core
        from fastapi.testclient import TestClient
        from app.config import Settings
        from app.main import create_app

        with TestClient(create_app(Settings())) as client:
            end = time.monotonic() + 60
            while client.get("/api/v1/ready").status_code != 200:
                if time.monotonic() > end:
                    raise SystemExit("never ready")
                time.sleep(0.05)
            state = client.app.state.analysis_queue.state
        banned = ("torch", "transformers", "numpy")
        print(json.dumps({"state": state, "loaded": [m for m in banned if m in sys.modules]}))
        """
    )
    done = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, timeout=180
    )
    assert done.returncode == 0
    assert json.loads(done.stdout.splitlines()[-1]) == {"state": "ok", "loaded": []}
