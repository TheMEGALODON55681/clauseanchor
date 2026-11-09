"""The built frontend, served by the API when `CLAUSEANCHOR_FRONTEND_DIST` names it (4-B).

The dist here is a made-up folder with the same shape as the Vite build: `index.html`,
hashed files in `assets/`, and unhashed files beside them.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigError

INDEX = '<!doctype html><title>Made up</title><div id="root"></div>'
ASSET = "/assets/index-1a2b3c4d.js"
ASSET_TEXT = "export default 1\n"
IMMUTABLE = "public, max-age=31536000, immutable"
MakeClient = Callable[..., TestClient]


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "fonts").mkdir()
    (root / "index.html").write_text(INDEX, encoding="utf-8")
    (root / ASSET.lstrip("/")).write_bytes(ASSET_TEXT.encode())  # bytes: no Windows newline change
    (root / "fonts" / "plain.woff2").write_bytes(b"wOF2")
    (root / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    return root


@pytest.fixture
def web(make_client: MakeClient, dist: Path) -> TestClient:
    return make_client(frontend_dist=dist)


def _envelope(response, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/json"
    assert response.json()["error"]["code"] == code


def test_the_root_serves_index_html(web: TestClient) -> None:
    response = web.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == INDEX


def test_an_asset_is_served(web: TestClient) -> None:
    response = web.get(ASSET)
    assert response.status_code == 200
    assert response.text == ASSET_TEXT


def test_a_font_is_served_with_a_font_type(web: TestClient) -> None:
    # Python's own table has no .woff2, and a slim Linux image has no /etc/mime.types
    assert web.get("/fonts/plain.woff2").headers["content-type"] == "font/woff2"


def test_the_api_still_answers_json(web: TestClient) -> None:
    response = web.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("method", ["get", "post", "delete"])
@pytest.mark.parametrize("path", ["/api/v1/nothing-here", "/api/nothing-here", "/api", "/api/"])
def test_an_unknown_api_path_is_the_404_envelope_and_never_index_html(
    web: TestClient, method: str, path: str
) -> None:
    response = getattr(web, method)(path)
    _envelope(response, 404, "NOT_FOUND")
    assert "Made up" not in response.text


def test_a_wrong_method_on_an_api_route_keeps_its_405_and_allow_header(web: TestClient) -> None:
    response = web.post("/api/v1/health")
    _envelope(response, 405, "METHOD_NOT_ALLOWED")
    assert "GET" in response.headers["allow"]


def test_a_trailing_slash_on_an_api_route_still_redirects(web: TestClient) -> None:
    response = web.get("/api/v1/health/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].endswith("/api/v1/health")


def test_a_missing_file_is_the_404_envelope(web: TestClient) -> None:
    _envelope(web.get("/no-such-file.js"), 404, "NOT_FOUND")


def test_a_static_file_refuses_a_write_with_the_envelope(web: TestClient) -> None:
    response = web.post("/")
    _envelope(response, 405, "METHOD_NOT_ALLOWED")
    assert "GET" in response.headers["allow"]


@pytest.mark.parametrize("path", ["/", ASSET, "/favicon.svg"])
def test_nothing_is_served_when_the_setting_is_unset(client: TestClient, path: str) -> None:
    _envelope(client.get(path), 404, "NOT_FOUND")


@pytest.mark.parametrize("path", ["/", "/favicon.svg", "/fonts/plain.woff2", "/api/v1/health"])
def test_everything_but_a_hashed_asset_stays_uncached(web: TestClient, path: str) -> None:
    assert web.get(path).headers["cache-control"] == "no-store"


def test_a_hashed_asset_may_be_cached_for_good(web: TestClient) -> None:
    assert web.get(ASSET).headers["cache-control"] == IMMUTABLE


def test_a_missing_asset_is_never_cached(web: TestClient) -> None:
    response = web.get("/assets/gone-9f9f9f9f.js")
    _envelope(response, 404, "NOT_FOUND")
    assert response.headers["cache-control"] == "no-store"


def test_a_dist_without_index_html_stops_the_start_and_names_the_variable_only(
    make_client: MakeClient, tmp_path: Path
) -> None:
    with pytest.raises(ConfigError, match="CLAUSEANCHOR_FRONTEND_DIST") as err:
        make_client(frontend_dist=tmp_path / "no-such-folder-xyz")
    assert "no-such-folder-xyz" not in str(err.value)
