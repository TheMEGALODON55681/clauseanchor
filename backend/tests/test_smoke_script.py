"""The CI smoke script (app/scripts/smoke_test.py) against the API itself, on a fake core.

The workflow runs the script against the real image, and only a run on GitHub proves that. These
tests prove the rest: the made-up PDF is one our parser reads, and the script's steps, checks and
failure messages are right, so a red run on GitHub points at the image and not at the script.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.parsing import parse_document
from app.scripts import smoke_test
from app.scripts.smoke_test import Send, SmokeFailure

MakeClient = Callable[..., TestClient]


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(
        '<script type="module" src="/assets/app-1a2b3c4d.js"></script><div id="root"></div>',
        encoding="utf-8",
    )
    (root / "assets" / "app-1a2b3c4d.js").write_text("export default 1\n", encoding="utf-8")
    return root


def through(client: TestClient) -> Send:
    """The script's `send`, answered by the app in the test process instead of over a socket."""

    def send(method, path, *, token=None, body=None, headers=None):
        sent = dict(headers or {})
        if token:
            sent["Authorization"] = f"Bearer {token}"
        response = client.request(method, path, content=body, headers=sent)
        return response.status_code, dict(response.headers), response.content

    return send


def test_the_made_up_pdf_is_one_the_parser_reads() -> None:
    doc = parse_document(smoke_test.synthetic_pdf())
    assert "Testland" in doc.source_text
    assert doc.warnings == ()
    assert not doc.coverage.partial


def good_analysis() -> dict:
    return {
        "mode": "real",
        "categories": [
            {
                "category_id": "x.a",
                "windows_total": 3,
                "clauses": [{"status": "review_candidate", "confidence": None, "origin": "model"}],
            },
            {"category_id": "x.b", "windows_total": 3, "clauses": []},
        ],
    }


def test_a_candidate_only_analysis_passes_and_counts_its_findings() -> None:
    assert smoke_test.check_analysis(good_analysis()) == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "accepted"),
        ("confidence", 0.9),
        ("origin", "fixture"),
    ],
)
def test_a_finding_that_claims_more_than_a_candidate_fails(field: str, value: object) -> None:
    analysis = good_analysis()
    analysis["categories"][0]["clauses"][0][field] = value
    with pytest.raises(SmokeFailure, match=field):
        smoke_test.check_analysis(analysis)


def test_an_analysis_where_the_model_read_no_window_fails() -> None:
    analysis = good_analysis()
    for category in analysis["categories"]:
        category["windows_total"] = 0
    with pytest.raises(SmokeFailure, match="windows"):
        smoke_test.check_analysis(analysis)


def test_a_sample_mode_analysis_fails() -> None:
    analysis = good_analysis() | {"mode": "sample"}
    with pytest.raises(SmokeFailure, match="mode"):
        smoke_test.check_analysis(analysis)


def test_the_script_passes_against_the_api_on_a_fake_core(
    make_client: MakeClient, tmp_path: Path, fake_core: object, dist: Path, capsys
) -> None:
    client = make_client(
        analyzer="real", artifacts_dir=tmp_path, artifacts_sha256="ab" * 32, frontend_dist=dist
    )
    tokens: list[str] = []
    answer = through(client)

    def send(method, path, *, token=None, body=None, headers=None):
        tokens.extend([token] if token else [])
        return answer(method, path, token=token, body=body, headers=headers)

    smoke_test.smoke(send, ready_timeout=5, job_timeout=10, interval=0.02)
    assert "findings: 1" in capsys.readouterr().out
    # the script ends its session, so the token no longer works
    again = {"Authorization": f"Bearer {tokens[0]}"}
    assert client.delete("/api/v1/sessions/current", headers=again).status_code == 401


def test_the_script_names_the_step_that_failed(make_client: MakeClient, dist: Path) -> None:
    # stub mode: the page is served, and the analyzer is not real
    client = make_client(frontend_dist=dist)
    with pytest.raises(SmokeFailure, match="mode"):
        smoke_test.smoke(through(client), ready_timeout=5, job_timeout=10, interval=0.02)


def test_the_script_fails_when_the_app_page_is_missing(
    make_client: MakeClient, tmp_path: Path, fake_core: object
) -> None:
    client = make_client(analyzer="real", artifacts_dir=tmp_path, artifacts_sha256="ab" * 32)
    with pytest.raises(SmokeFailure, match="app page"):
        smoke_test.smoke(through(client), ready_timeout=5, job_timeout=10, interval=0.02)


def test_the_script_gives_up_when_the_analyzer_never_loads(
    make_client: MakeClient, tmp_path: Path, fake_core
) -> None:
    fake_core.load_error = RuntimeError("no weights")
    client = make_client(analyzer="real", artifacts_dir=tmp_path, artifacts_sha256="ab" * 32)
    with pytest.raises(SmokeFailure, match="not ready"):
        smoke_test.smoke(through(client), ready_timeout=0.3, job_timeout=1, interval=0.05)
