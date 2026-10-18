from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigError
from app.main import create_app
from app.services.scope import SCOPE_NOTICE
from tests.synthetic import synthetic_catalogue

HEALTH = "/api/v1/health"
READY = "/api/v1/ready"
CAPABILITIES = "/api/v1/capabilities"

MakeClient = Callable[..., TestClient]


def _error(response, status: int, code: str) -> dict:
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    return error


def test_openapi_is_served_under_api_v1_and_every_path_sits_there(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    paths = set(response.json()["paths"])
    assert {HEALTH, READY, CAPABILITIES} <= paths
    assert all(path.startswith("/api/v1/") for path in paths)


def test_create_app_without_settings_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUSEANCHOR_ANALYZER", "bogus")
    with pytest.raises(ConfigError, match="CLAUSEANCHOR_ANALYZER"):
        create_app()


def test_health_is_ok(client: TestClient) -> None:
    response = client.get(HEALTH)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_checks_no_dependency(make_client: MakeClient, tmp_path: Path) -> None:
    client = make_client(
        catalogue_path=tmp_path / "absent.json", analyzer="real", artifacts_dir=tmp_path / "absent"
    )
    assert client.get(HEALTH).status_code == 200


def test_ready_when_analyzer_and_catalogue_are_fine(client: TestClient) -> None:
    response = client.get(READY)
    assert response.status_code == 200
    assert response.json() == {"ready": True, "checks": {"analyzer": "ok", "catalogue": "ok"}}


def test_not_ready_without_a_catalogue(make_client: MakeClient, tmp_path: Path) -> None:
    response = make_client(catalogue_path=tmp_path / "absent.json").get(READY)
    error = _error(response, 503, "NOT_READY")
    assert error["details"] == {"checks": {"analyzer": "ok", "catalogue": "missing"}}
    assert error["retryable"] is True


def test_not_ready_with_an_invalid_catalogue(make_client: MakeClient, tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    error = _error(make_client(catalogue_path=bad).get(READY), 503, "NOT_READY")
    assert error["details"]["checks"]["catalogue"] == "invalid"


@pytest.mark.parametrize("missing", ["no directory", "no setting"])
def test_real_analyzer_without_its_artifacts_is_not_ready(
    make_client: MakeClient, tmp_path: Path, missing: str
) -> None:
    artifacts = tmp_path / "absent" if missing == "no directory" else None
    response = make_client(analyzer="real", artifacts_dir=artifacts).get(READY)
    error = _error(response, 503, "NOT_READY")
    assert error["details"]["checks"] == {"analyzer": "artifacts_missing", "catalogue": "ok"}
    assert str(tmp_path) not in response.text


def test_real_analyzer_with_its_artifacts_is_ready(make_client: MakeClient, tmp_path: Path) -> None:
    response = make_client(analyzer="real", artifacts_dir=tmp_path).get(READY)
    assert response.status_code == 200


def test_capabilities_lists_the_scope_mode_version_and_categories(client: TestClient) -> None:
    response = client.get(CAPABILITIES)
    assert response.status_code == 200
    body = response.json()
    # An exact key set: a score, verdict or completeness field would fail here
    assert set(body) == {"scope_notice", "mode", "catalogue_version", "categories"}
    assert body["mode"] == "sample"
    assert body["catalogue_version"] == "synthetic-test-0"
    assert body["categories"] == synthetic_catalogue()["categories"]


def test_capabilities_mode_comes_from_the_analyzer(make_client: MakeClient, tmp_path: Path) -> None:
    client = make_client(analyzer="real", artifacts_dir=tmp_path)
    assert client.get(CAPABILITIES).json()["mode"] == "real"


def test_scope_notice_in_the_response_equals_the_constant_byte_for_byte(
    client: TestClient,
) -> None:
    notice = client.get(CAPABILITIES).json()["scope_notice"]
    assert notice.encode("utf-8") == SCOPE_NOTICE.encode("utf-8")


def test_capabilities_without_a_catalogue_is_a_503(make_client: MakeClient, tmp_path: Path) -> None:
    response = make_client(catalogue_path=tmp_path / "absent.json").get(CAPABILITIES)
    error = _error(response, 503, "CATALOGUE_UNAVAILABLE")
    assert error["retryable"] is False


def test_capabilities_with_an_invalid_catalogue_is_a_503(
    make_client: MakeClient, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"catalogue_version": "x", "categories": []}', encoding="utf-8")
    _error(make_client(catalogue_path=bad).get(CAPABILITIES), 503, "CATALOGUE_UNAVAILABLE")
