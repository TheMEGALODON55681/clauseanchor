from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import analysis, parse_jobs
from tests.fake_core import FakeCore
from tests.fixtures.build import Fixtures, build_all
from tests.synthetic import FakeClock, synthetic_catalogue, wait_until


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
def make_client(
    catalogue_file: Path, clock: FakeClock, spawned: list[subprocess.Popen[bytes]]
) -> Iterator[Callable[..., TestClient]]:
    """Builds an app on the synthetic catalogue and the fake clock, with its lifespan running.

    Keyword arguments override Settings fields. Every client closes when the test ends, and then
    `spawned` checks that no parse child is left. The analyzer loads in a thread of the app, so
    `make` waits for it to leave `loading`, unless the test passes `loaded=False` to watch it.
    """
    with ExitStack() as stack:

        def make(*, loaded: bool = True, **overrides: object) -> TestClient:
            settings = replace(Settings(catalogue_path=catalogue_file), **overrides)
            made = stack.enter_context(TestClient(create_app(settings, clock=clock)))
            if loaded:
                wait_until(lambda: made.app.state.analysis_queue.state != "loading")
            return made

        yield make


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


@pytest.fixture
def fake_core(monkeypatch: pytest.MonkeyPatch) -> FakeCore:
    """Real mode on a fake: `CandidateOnlyAnalyzer` in the factory becomes this object, so no
    test loads weights. Build the app with analyzer="real" and any directory and digest."""
    core = FakeCore()
    monkeypatch.setattr(analysis, "CandidateOnlyAnalyzer", core)
    return core


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[subprocess.Popen[bytes]]]:
    """Every parse child the app starts during a test. One still alive at the end fails the test."""
    made: list[subprocess.Popen[bytes]] = []
    real = parse_jobs.CappedProcess

    class Recorded(real):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            made.append(self.popen)

    monkeypatch.setattr(parse_jobs, "CappedProcess", Recorded)
    yield made
    leaked = [child for child in made if child.poll() is None]
    for child in leaked:
        child.kill()
        child.wait()
    assert leaked == []


@pytest.fixture
def hanging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[], int]:
    """Parse children that never finish. The first one writes its interpreter's pid to a file and
    sleeps. The returned function waits for that file and gives the pid, so a test can check
    the interpreter itself is gone, and not only the launcher that Popen holds on Windows."""
    pid_file = tmp_path / "child.pid"
    code = "import os, sys, time; open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(600)"
    monkeypatch.setattr(parse_jobs, "WORKER_ARGS", [sys.executable, "-c", code, str(pid_file)])

    def child_pid() -> int:
        return wait_until(lambda: pid_file.exists() and int(pid_file.read_text() or 0))

    return child_pid
