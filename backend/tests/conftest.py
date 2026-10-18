from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.fixtures.build import Fixtures, build_all
from tests.synthetic import synthetic_catalogue


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
def make_client(catalogue_file: Path) -> Callable[..., TestClient]:
    """Builds an app on the synthetic catalogue. Keyword arguments override Settings fields."""

    def make(**overrides: object) -> TestClient:
        settings = replace(Settings(catalogue_path=catalogue_file), **overrides)
        return TestClient(create_app(settings))

    return make


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()
