"""The parse child's entry module, in process and as the real child."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from app import parse_worker
from app.parsing import ErrorCode, parse_document
from app.parsing.schema import from_json, to_json
from app.services.memcap import BACKEND_DIR
from tests.fixtures.build import VALID_NAMES, Fixtures


def test_a_valid_file_gives_the_full_form(fixture_bytes: dict[str, bytes]) -> None:
    raw = fixture_bytes["simple.pdf"]
    assert parse_worker.run(raw) == {"document": to_json(parse_document(raw))}


@pytest.mark.parametrize("name", VALID_NAMES)
def test_every_valid_fixture_comes_back_whole(name: str, fixture_bytes: dict[str, bytes]) -> None:
    result = parse_worker.run(fixture_bytes[name])
    sent = json.loads(json.dumps(result))
    assert from_json(sent["document"]) == parse_document(fixture_bytes[name])


def test_a_rejected_file_gives_its_code_and_no_document(fixtures: Fixtures) -> None:
    rejected = {name: code for name, (_, code) in fixtures.items() if code is not None}
    assert len(rejected) >= 25
    for name, code in rejected.items():
        raw = fixtures[name][0].read_bytes()
        assert parse_worker.run(raw) == {"error": code.value}, name


def test_a_memory_error_is_the_memory_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(data: bytes) -> None:
        raise MemoryError

    monkeypatch.setattr(parse_worker, "parse_document", refuse)
    assert parse_worker.run(b"anything") == {"error": "PARSE_MEMORY_LIMIT"}


def child(raw: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "app.parse_worker"],
        input=raw,
        capture_output=True,
        cwd=BACKEND_DIR,
        timeout=60,
        check=False,
    )


def test_the_real_child_reads_stdin_and_writes_one_ascii_json_object(
    fixture_bytes: dict[str, bytes],
) -> None:
    done = child(fixture_bytes["latin_unicode.pdf"])
    assert done.returncode == 0
    assert done.stderr == b""
    assert done.stdout.isascii()
    sent = json.loads(done.stdout)
    assert from_json(sent["document"]) == parse_document(fixture_bytes["latin_unicode.pdf"])


def test_the_real_child_reports_a_parser_error_with_exit_status_zero(
    fixture_bytes: dict[str, bytes],
) -> None:
    done = child(fixture_bytes["malformed.pdf"])
    assert done.returncode == 0
    assert json.loads(done.stdout) == {"error": ErrorCode.MALFORMED_FILE.value}
