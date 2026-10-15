from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.build import Fixtures, build_all


@pytest.fixture(scope="session")
def fixtures(tmp_path_factory: pytest.TempPathFactory) -> Fixtures:
    return build_all(tmp_path_factory.mktemp("fixtures"))


@pytest.fixture(scope="session")
def fixture_bytes(fixtures: Fixtures) -> dict[str, bytes]:
    return {name: Path(path).read_bytes() for name, (path, _) in fixtures.items()}
