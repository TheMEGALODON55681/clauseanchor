from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.fixtures.build import Fixtures, build_all
from tests.synthetic import FakeClock, synthetic_catalogue


@pytest.fixture(scope="session")
def fixtures(tmp_path_factory: pytest.TempPathFactory) -> Fixtures:
    return build_all(tmp_path_factory.mktemp("fixtures"))


@pytest.fixture(scope="session")
def fixture_bytes(fixtures: Fixtures) -> dict[str, bytes]:
    return {name: Path(path).read_bytes() for name, (path, _) in fixtures.items()}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No CLAUSEANCHOR_ variable from the developer's shell reaches a test."""
    for name in [n for n in os.environ if n.startswith("CLAUSEANCHOR_")]:
        monkeypatch.delenv(name)


@pytest.fixture
def catalogue_file(tmp_path: Path) -> Path:
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(synthetic_catalogue()), encoding="utf-8")
    return path


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_client(catalogue_file: Path, clock: FakeClock) -> Iterator[Callable[..., TestClient]]:
    """Builds an app on the synthetic catalogue and the fake clock, with its lifespan running.

    Keyword arguments override Settings fields. Every client closes when the test ends.
    """
    with ExitStack() as stack:

        def make(**overrides: object) -> TestClient:
            settings = replace(Settings(catalogue_path=catalogue_file), **overrides)
            return stack.enter_context(TestClient(create_app(settings, clock=clock)))

        yield make


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()
