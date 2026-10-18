from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from app.api.errors import ERRORS

SECRET = "s3cret-input-4c1f"
NUMBER = "/api/v1/_probe/number"
ITEM = "/api/v1/_probe/item"
BOOM = "/api/v1/_probe/boom"
ENVELOPE_KEYS = {"code", "message", "request_id", "retryable", "details"}


class _Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int


@pytest.fixture
def probe(client: TestClient) -> TestClient:
    """The app with three routes that only tests have: path and query numbers, a body, a crash."""

    @client.app.get(NUMBER + "/{n}")
    async def number(n: int, q: int = 0) -> dict[str, int]:
        return {"n": n, "q": q}

    @client.app.post(ITEM)
    async def item(body: _Item) -> dict[str, int]:
        return {"count": body.count}

    @client.app.get(BOOM)
    async def boom() -> None:
        raise RuntimeError(f"exception text {SECRET}")

    return client


def _assert_envelope(response, status: int, code: str) -> dict:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert set(error) == ENVELOPE_KEYS
    assert error["code"] == code
    assert error["message"] == ERRORS[code][1]
    assert error["request_id"]
    assert error["retryable"] is ERRORS[code][2]
    assert error["details"] == {}
    return error


def test_unknown_path_is_a_404_envelope(client: TestClient) -> None:
    _assert_envelope(client.get("/api/v1/nothing-here"), 404, "NOT_FOUND")


def test_404_does_not_echo_the_path(client: TestClient) -> None:
    response = client.get(f"/api/v1/{SECRET}")
    assert response.status_code == 404
    assert SECRET not in response.text


def test_api_docs_pages_are_not_served(client: TestClient) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_wrong_method_is_a_405_envelope_with_the_allow_header(probe: TestClient) -> None:
    response = probe.post(f"{NUMBER}/1")
    _assert_envelope(response, 405, "METHOD_NOT_ALLOWED")
    assert "GET" in response.headers["allow"]


def test_each_response_gets_its_own_request_id(client: TestClient) -> None:
    ids = {client.get("/api/v1/nothing-here").json()["error"]["request_id"] for _ in range(3)}
    assert len(ids) == 3


@pytest.mark.parametrize(
    ("method", "url", "kwargs"),
    [
        ("get", f"{NUMBER}/{SECRET}", {}),
        ("get", f"{NUMBER}/1?q={SECRET}", {}),
        ("post", ITEM, {"json": {"count": SECRET}}),
        ("post", ITEM, {"json": {"count": 1, SECRET: 1}}),
        ("post", ITEM, {"content": f'{{"count": "{SECRET}" '.encode()}),
    ],
    ids=["path", "query", "body value", "body key", "malformed json"],
)
def test_422_is_an_envelope_and_echoes_nothing(
    probe: TestClient, method: str, url: str, kwargs: dict
) -> None:
    response = getattr(probe, method)(url, **kwargs)
    _assert_envelope(response, 422, "VALIDATION_ERROR")
    assert SECRET not in response.text


def test_500_is_an_envelope_with_no_exception_text(probe: TestClient) -> None:
    response = probe.get(BOOM)
    _assert_envelope(response, 500, "INTERNAL_ERROR")
    for leaked in (SECRET, "exception text", "RuntimeError", "Traceback"):
        assert leaked not in response.text


def test_500_logs_the_exception_type_and_not_its_text(
    probe: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        probe.get(BOOM)
    assert "RuntimeError" in caplog.text
    assert SECRET not in caplog.text
