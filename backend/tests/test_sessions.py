from __future__ import annotations

import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.auth import require_session
from app.api.errors import ERRORS
from app.config import MAX_SESSIONS, ConfigError, Settings
from app.main import create_app
from app.services.store import Session, Store
from tests.synthetic import FakeClock, snapshot

SESSIONS = "/api/v1/sessions"
CURRENT = "/api/v1/sessions/current"
WHO = "/api/v1/_probe/who"
TTL = 3600
MakeClient = Callable[..., TestClient]


@pytest.fixture
def probe(client: TestClient) -> TestClient:
    """The app with one route that only tests have, behind the bearer check 2-C will reuse."""

    @client.app.get(WHO)
    async def who(session: Annotated[Session, Depends(require_session)]) -> dict[str, str]:
        return {"id": session.id}

    return client


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def open_session(client: TestClient) -> str:
    response = client.post(SESSIONS)
    assert response.status_code == 201
    return response.json()["token"]


def store_of(client: TestClient) -> Store:
    return client.app.state.store


def session_rows(client: TestClient) -> int:
    store = store_of(client)
    with store._lock:
        return store._db.execute("SELECT count(*) FROM sessions").fetchone()[0]


def assert_invalid(response, token: str) -> None:
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    error = response.json()["error"]
    assert error["code"] == "SESSION_INVALID"
    assert error["message"] == ERRORS["SESSION_INVALID"][1]
    assert error["retryable"] is False
    assert error["details"] == {}
    # The reply never repeats the credential, in the body or in any header
    assert token not in response.text
    assert all(token not in value for value in response.headers.values())


def test_create_returns_the_token_once_with_a_fixed_expiry(
    client: TestClient, clock: FakeClock
) -> None:
    clock.advance(0.75)  # the expiry shown is rounded down to a whole second, never up
    response = client.post(SESSIONS)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"token", "expires_at"}
    assert datetime.fromisoformat(body["expires_at"]) == datetime.fromtimestamp(
        int(clock.now + TTL), UTC
    )


def test_the_ttl_comes_from_the_setting(make_client: MakeClient, clock: FakeClock) -> None:
    body = make_client(session_ttl_minutes=30).post(SESSIONS).json()
    assert datetime.fromisoformat(body["expires_at"]) == datetime.fromtimestamp(
        int(clock.now + 1800), UTC
    )


def test_a_post_body_is_ignored(client: TestClient) -> None:
    assert client.post(SESSIONS, json={"anything": 1}).status_code == 201


def test_the_token_opens_the_protected_route(probe: TestClient) -> None:
    token = open_session(probe)
    response = probe.get(WHO, headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["id"]


def test_the_scheme_is_case_insensitive(probe: TestClient) -> None:
    token = open_session(probe)
    response = probe.get(WHO, headers={"Authorization": f"bearer {token}"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "header",
    [
        None,
        "Basic {token}",
        "Token {token}",
        "{token}",
        "Bearer",
        "Bearer ",
        "Bearer %%not-a-token%%",
        "Bearer " + "A" * 43,
    ],
    ids=[
        "missing header",
        "wrong scheme",
        "other scheme",
        "no scheme",
        "no token",
        "empty token",
        "garbage token",
        "unknown token",
    ],
)
def test_every_bad_header_is_a_401_envelope_with_the_challenge(
    probe: TestClient, header: str | None
) -> None:
    token = open_session(probe)
    headers = {} if header is None else {"Authorization": header.format(token=token)}
    assert_invalid(probe.get(WHO, headers=headers), token)
    assert_invalid(probe.delete(CURRENT, headers=headers), token)
    assert session_rows(probe) == 1


def test_an_expired_token_is_one_tick_valid_then_a_401(probe: TestClient, clock: FakeClock) -> None:
    token = open_session(probe)
    clock.advance(TTL - 1)
    assert probe.get(WHO, headers=bearer(token)).status_code == 200
    clock.advance(1)
    assert_invalid(probe.get(WHO, headers=bearer(token)), token)
    assert session_rows(probe) == 0


def test_polling_does_not_extend_the_session(probe: TestClient, clock: FakeClock) -> None:
    token = open_session(probe)
    for _ in range(5):
        clock.advance(TTL // 6)
        assert probe.get(WHO, headers=bearer(token)).status_code == 200
    clock.advance(TTL // 6)
    assert probe.get(WHO, headers=bearer(token)).status_code == 401


def test_delete_ends_the_session_with_a_204_and_no_body(probe: TestClient) -> None:
    token = open_session(probe)
    other = open_session(probe)
    response = probe.delete(CURRENT, headers=bearer(token))
    assert response.status_code == 204
    assert response.content == b""
    assert_invalid(probe.get(WHO, headers=bearer(token)), token)
    assert_invalid(probe.delete(CURRENT, headers=bearer(token)), token)
    assert probe.get(WHO, headers=bearer(other)).status_code == 200


def test_delete_takes_the_sessions_documents_and_jobs(probe: TestClient) -> None:
    token = open_session(probe)
    store = store_of(probe)
    session = store.get_session(token)
    doc = store.add_document(
        session.id, filename="a.pdf", media_type="application/pdf", byte_count=1
    )
    store.add_job(doc.id, "parse")
    assert probe.delete(CURRENT, headers=bearer(token)).status_code == 204
    assert store.get_document(session.id, doc.id) is None
    with store._lock:
        counts = [
            store._db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("sessions", "documents", "jobs")
        ]
        assert counts == [0, 0, 0]
        assert store._documents == {}


def test_the_session_limit_is_a_429_until_a_session_expires(
    client: TestClient, clock: FakeClock
) -> None:
    for _ in range(MAX_SESSIONS):
        assert client.post(SESSIONS).status_code == 201
    response = client.post(SESSIONS)
    assert response.status_code == 429
    error = response.json()["error"]
    assert error["code"] == "SESSION_LIMIT"
    assert error["retryable"] is True
    assert error["message"] == ERRORS["SESSION_LIMIT"][1]
    clock.advance(TTL)
    assert client.post(SESSIONS).status_code == 201


@pytest.mark.parametrize(
    ("method", "url"),
    [("post", SESSIONS), ("delete", CURRENT), ("get", "/api/v1/nothing-here"), ("get", WHO)],
)
def test_session_responses_are_not_cacheable(probe: TestClient, method: str, url: str) -> None:
    token = open_session(probe)
    response = getattr(probe, method)(url, headers=bearer(token))
    assert response.headers["cache-control"] == "no-store"


def test_the_lifespan_sweep_removes_expired_sessions_with_no_request(
    make_client: MakeClient, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.main.SWEEP_INTERVAL_SECONDS", 0.01)
    client = make_client()
    open_session(client)
    assert session_rows(client) == 1
    clock.advance(TTL)
    deadline = time.monotonic() + 5
    while session_rows(client) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert session_rows(client) == 0


def test_the_sweep_survives_a_failed_run(
    make_client: MakeClient,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr("app.main.SWEEP_INTERVAL_SECONDS", 0.01)
    calls = {"n": 0}
    real_sweep = Store.sweep

    def flaky(self: Store) -> int:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("secret exception text")
        return real_sweep(self)

    monkeypatch.setattr(Store, "sweep", flaky)
    client = make_client()
    open_session(client)
    clock.advance(TTL)
    deadline = time.monotonic() + 5
    while session_rows(client) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert session_rows(client) == 0
    assert "RuntimeError" in caplog.text
    assert "secret exception text" not in caplog.text


def test_a_database_that_cannot_open_stops_the_start_and_names_the_variable(
    tmp_path: Path, catalogue_file: Path
) -> None:
    missing = tmp_path / "no" / "such" / "dir" / "meta.db"
    with pytest.raises(ConfigError, match="CLAUSEANCHOR_DB_PATH") as err:
        create_app(Settings(catalogue_path=catalogue_file, db_path=str(missing)))
    assert str(missing) not in str(err.value)


def test_a_file_database_works_through_the_api(make_client: MakeClient, tmp_path: Path) -> None:
    client = make_client(db_path=str(tmp_path / "meta.db"))
    token = open_session(client)
    assert client.delete(CURRENT, headers=bearer(token)).status_code == 204


def test_a_whole_session_cycle_writes_nothing_to_the_temp_directory_or_the_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, catalogue_file: Path, clock: FakeClock
) -> None:
    work, temp = tmp_path / "cwd", tmp_path / "tmp"
    work.mkdir()
    temp.mkdir()
    monkeypatch.chdir(work)
    for name in ("TMP", "TEMP", "TMPDIR"):
        monkeypatch.setenv(name, str(temp))
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    backend = Path(__file__).parents[1]
    before = snapshot(backend)

    settings = Settings(catalogue_path=catalogue_file)
    assert settings.db_path == ":memory:"
    with TestClient(create_app(settings, clock=clock)) as client:
        token = open_session(client)
        session = store_of(client).get_session(token)
        doc = store_of(client).add_document(
            session.id, filename="a.pdf", media_type="application/pdf", byte_count=1
        )
        store_of(client).add_job(doc.id, "parse")
        gone = open_session(client)
        clock.advance(TTL)
        store_of(client).sweep()
        assert client.delete(CURRENT, headers=bearer(gone)).status_code == 401
        fresh = open_session(client)
        assert client.delete(CURRENT, headers=bearer(fresh)).status_code == 204

    assert list(work.iterdir()) == []
    assert list(temp.iterdir()) == []
    assert snapshot(backend) == before


def test_the_sweep_loop_stops_when_the_app_stops(
    catalogue_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.main.SWEEP_INTERVAL_SECONDS", 0.01)
    with TestClient(create_app(Settings(catalogue_path=catalogue_file))) as client:
        sweeper = client.app.state.sweeper
        assert not sweeper.done()
    assert sweeper.done()
