"""Upload, read and delete a document, and read a parse job, through the app and real children."""

from __future__ import annotations

import io
import json
import logging
import subprocess
import sys
import tempfile
import uuid
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.errors import ERRORS, JOB_ERRORS
from app.config import MAX_DOCUMENTS_PER_SESSION, Settings
from app.main import create_app
from app.parsing import parse_document
from app.parsing.schema import to_json
from app.services import parse_jobs
from tests.fixtures.build import build_docx
from tests.synthetic import FakeClock, process_alive, snapshot, wait_until

DOCS = "/api/v1/documents"
JOBS = "/api/v1/jobs"
SESSIONS = "/api/v1/sessions"
CURRENT = "/api/v1/sessions/current"
LIMIT = 10 * 1024 * 1024
MakeClient = Callable[..., TestClient]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def open_session(client: TestClient) -> str:
    response = client.post(SESSIONS)
    assert response.status_code == 201
    return response.json()["token"]


def session_end(client: TestClient, token: str) -> datetime:
    """A document dies with its session, so it shows the session's own end time (D5)."""
    expires_at = client.app.state.store.get_session(token).expires_at
    return datetime.fromtimestamp(int(expires_at), UTC)


def post(client: TestClient, token: str, data: object, **headers: str):
    return client.post(DOCS, content=data, headers={**bearer(token), **headers})


def upload(client: TestClient, token: str, data: object, **headers: str) -> tuple[str, str]:
    response = post(client, token, data, **headers)
    assert response.status_code == 202, response.text
    body = response.json()
    return body["document_id"], body["parse_job_id"]


def get_job(client: TestClient, token: str, job_id: str):
    return client.get(f"{JOBS}/{job_id}", headers=bearer(token))


def get_document(client: TestClient, token: str, document_id: str):
    return client.get(f"{DOCS}/{document_id}", headers=bearer(token))


def settled(client: TestClient, token: str, job_id: str) -> dict:
    """The job once it succeeded or failed."""
    return wait_until(
        lambda: (
            (j := get_job(client, token, job_id).json())["status"] in ("succeeded", "failed") and j
        )
    )


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"] == ERRORS[code][1]
    assert error["retryable"] is ERRORS[code][2]
    assert error["details"] == {}
    assert uuid.UUID(error["request_id"])


def store_counts(client: TestClient) -> tuple[int, int]:
    store = client.app.state.store
    with store._lock:
        return (
            store._db.execute("SELECT count(*) FROM documents").fetchone()[0],
            store._db.execute("SELECT count(*) FROM jobs").fetchone()[0],
        )


# Upload: the session check, the size limit and the rejections


def test_upload_needs_a_session(client: TestClient, fixture_bytes: dict[str, bytes]) -> None:
    response = client.post(DOCS, content=fixture_bytes["simple.pdf"])
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_INVALID"
    assert store_counts(client) == (0, 0)


def test_a_pdf_is_accepted_with_202_and_both_ids(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    token = open_session(client)
    response = post(client, token, fixture_bytes["simple.pdf"])
    assert response.status_code == 202
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {"document_id", "parse_job_id", "expires_at"}
    assert uuid.UUID(body["document_id"]) != uuid.UUID(body["parse_job_id"])
    assert datetime.fromisoformat(body["expires_at"]) == session_end(client, token)
    assert settled(client, token, body["parse_job_id"])["status"] == "succeeded"


def test_the_type_comes_from_the_bytes_and_never_from_the_header(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    token = open_session(client)
    document_id, _ = upload(
        client, token, fixture_bytes["simple.docx"], **{"Content-Type": "text/plain"}
    )
    pdf_id, _ = upload(client, token, fixture_bytes["simple.pdf"], **{"Content-Type": "image/png"})
    assert (
        get_document(client, token, document_id)
        .json()["media_type"]
        .endswith("wordprocessingml.document")
    )
    assert get_document(client, token, pdf_id).json()["media_type"] == "application/pdf"
    refused = post(client, token, b"just some text", **{"Content-Type": "application/pdf"})
    assert_error(refused, 415, "UNSUPPORTED_TYPE")


def test_a_declared_length_over_the_limit_is_refused_before_the_body_is_read(
    client: TestClient,
) -> None:
    token = open_session(client)
    response = post(client, token, b"%PDF-1.4", **{"Content-Length": str(LIMIT + 1)})
    assert_error(response, 413, "FILE_TOO_LARGE")
    assert store_counts(client) == (0, 0)


def test_a_body_that_lies_about_its_length_is_stopped_at_the_limit(client: TestClient) -> None:
    token = open_session(client)
    response = post(client, token, b"\0" * (LIMIT + 1), **{"Content-Length": "100"})
    assert_error(response, 413, "FILE_TOO_LARGE")
    assert store_counts(client) == (0, 0)


def test_a_body_with_no_length_is_stopped_at_the_limit(client: TestClient) -> None:
    token = open_session(client)

    def chunks() -> Iterator[bytes]:
        for _ in range(LIMIT // 65536 + 1):
            yield b"\0" * 65536

    response = post(client, token, chunks())
    assert_error(response, 413, "FILE_TOO_LARGE")
    assert store_counts(client) == (0, 0)


def test_a_length_header_that_is_not_a_number_does_not_help_a_big_body(client: TestClient) -> None:
    token = open_session(client)
    response = post(client, token, b"\0" * (LIMIT + 1), **{"Content-Length": "lots"})
    assert_error(response, 413, "FILE_TOO_LARGE")


def test_an_empty_body_is_refused(client: TestClient) -> None:
    token = open_session(client)
    assert_error(post(client, token, b""), 400, "EMPTY_FILE")
    assert store_counts(client) == (0, 0)


def word_package_with(member: str | None) -> bytes:
    """A real package with one member added, or with its document part gone when member is None."""
    buffer = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(build_docx("<w:p/>"))) as source,
        zipfile.ZipFile(buffer, "w") as target,
    ):
        for name in source.namelist():
            if member is not None or name != "word/document.xml":
                target.writestr(name, source.read(name))
        if member is not None:
            target.writestr(member, b"x")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "data",
    [
        b"just some text",
        b"\x89PNG\r\n\x1a\n" + b"\0" * 64,
        word_package_with(None),  # a ZIP with no word/document.xml
        word_package_with("word/vbaProject.bin"),  # a macro-enabled document
        b" " * 2000 + b"%PDF-1.4",  # the header is past the first 1,024 bytes
    ],
    ids=["text", "png", "no document part", "macros", "late pdf header"],
)
def test_a_file_that_is_not_a_pdf_or_docx_is_refused(client: TestClient, data: bytes) -> None:
    token = open_session(client)
    assert_error(post(client, token, data), 415, "UNSUPPORTED_TYPE")
    assert store_counts(client) == (0, 0)


def test_an_unreadable_archive_is_accepted_and_fails_on_its_job(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    token = open_session(client)
    document_id, job_id = upload(client, token, fixture_bytes["corrupt_zip.docx"])
    job = settled(client, token, job_id)
    assert (job["status"], job["error"]["code"]) == ("failed", "MALFORMED_FILE")
    assert get_document(client, token, document_id).json()["status"] == "failed"


def test_a_refusal_never_repeats_the_name_or_the_content(client: TestClient) -> None:
    token = open_session(client)
    name = "Secret%20Merger%20Terms.txt"
    response = post(
        client,
        token,
        b"confidential clause text",
        **{"Content-Disposition": f"attachment; filename*=UTF-8''{name}"},
    )
    assert_error(response, 415, "UNSUPPORTED_TYPE")
    assert "Secret" not in response.text
    assert "confidential" not in response.text


# The file name


NAMES = [
    ("attachment; filename*=UTF-8''Master%20Agreement.pdf", "Master Agreement.pdf"),
    ("attachment; filename*=utf-8''Rs%E2%82%B9.pdf", "Rs" + chr(0x20B9) + ".pdf"),
    ("attachment; filename*=UTF-8''..%2F..%2Fsecret.pdf", "secret.pdf"),
    ("attachment; filename*=UTF-8''dir%5Cname.pdf", "name.pdf"),
    ("attachment; filename*=UTF-8''a%00b%0Ac%7F.pdf", "abc.pdf"),
    ("attachment; filename*=UTF-8''%FF%FE.pdf", "document.pdf"),
    ("attachment; filename*=UTF-8''..", "document.pdf"),
    ("attachment; filename*=UTF-8''", "document.pdf"),
    ("attachment; filename*=ISO-8859-1''a.pdf", "document.pdf"),
    ('attachment; filename="plain.pdf"', "document.pdf"),
    ("attachment", "document.pdf"),
    ("this is not a header value", "document.pdf"),
    ("attachment; filename*=UTF-8''" + "a" * 300 + ".pdf", "a" * 255),
]


@pytest.mark.parametrize(("header", "expected"), NAMES)
def test_the_name_comes_from_filename_star_and_is_cleaned(
    client: TestClient, fixture_bytes: dict[str, bytes], header: str, expected: str
) -> None:
    token = open_session(client)
    document_id, _ = upload(
        client, token, fixture_bytes["simple.pdf"], **{"Content-Disposition": header}
    )
    assert get_document(client, token, document_id).json()["filename"] == expected


def test_a_docx_without_a_name_is_called_document_docx(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    token = open_session(client)
    document_id, _ = upload(client, token, fixture_bytes["simple.docx"])
    assert get_document(client, token, document_id).json()["filename"] == "document.docx"


def test_the_name_stays_in_ram_and_never_reaches_sqlite(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    token = open_session(client)
    upload(
        client,
        token,
        fixture_bytes["simple.pdf"],
        **{"Content-Disposition": "attachment; filename*=UTF-8''VeryDistinctiveName.pdf"},
    )
    store = client.app.state.store
    with store._lock:
        assert "VeryDistinctiveName" not in "\n".join(store._db.iterdump())


# Limits on documents and on the queue


def test_a_sixth_document_gets_429_and_a_deleted_one_frees_its_slot(
    make_client: MakeClient, hanging: Callable[[], int]
) -> None:
    client = make_client(parse_queue_length=10)
    token = open_session(client)
    ids = [
        upload(client, token, b"%PDF-1.4 " + bytes([i]))[0]
        for i in range(MAX_DOCUMENTS_PER_SESSION)
    ]
    assert_error(post(client, token, b"%PDF-1.4 more"), 429, "DOCUMENT_LIMIT")
    assert store_counts(client)[0] == MAX_DOCUMENTS_PER_SESSION
    assert client.delete(f"{DOCS}/{ids[0]}", headers=bearer(token)).status_code == 204
    upload(client, token, b"%PDF-1.4 again")


def test_a_full_queue_gets_429_and_leaves_nothing_behind(
    make_client: MakeClient, hanging: Callable[[], int]
) -> None:
    client = make_client(parse_queue_length=1)
    token = open_session(client)
    _, first_job = upload(client, token, b"%PDF-1.4 a")
    wait_until(lambda: get_job(client, token, first_job).json()["status"] == "running")
    upload(client, token, b"%PDF-1.4 b")  # takes the one place in the queue
    refused = post(client, token, b"%PDF-1.4 c")
    assert_error(refused, 429, "QUEUE_FULL")
    # assert_error reads the flag from the table it checks, so the value is pinned here
    assert refused.json()["error"]["retryable"] is True
    assert store_counts(client) == (2, 2)


# Reading a document and a job


def test_a_parsed_document_carries_its_metadata_and_the_full_parser_output(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    token = open_session(client)
    raw = fixture_bytes["simple.pdf"]
    document_id, job_id = upload(client, token, raw)
    settled(client, token, job_id)
    response = get_document(client, token, document_id)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "id",
        "filename",
        "status",
        "media_type",
        "byte_count",
        "expires_at",
        "parsed",
    }
    assert (body["id"], body["status"], body["byte_count"]) == (document_id, "parsed", len(raw))
    assert body["media_type"] == "application/pdf"
    assert datetime.fromisoformat(body["expires_at"]) == session_end(client, token)
    # The whole output: text, blocks, nodes, decorations, warnings and coverage
    assert body["parsed"] == json.loads(json.dumps(to_json(parse_document(raw))))


def test_a_document_that_is_still_parsing_has_no_output_yet(
    client: TestClient, hanging: Callable[[], int]
) -> None:
    token = open_session(client)
    document_id, _ = upload(client, token, b"%PDF-1.4 x")
    body = get_document(client, token, document_id).json()
    assert (body["status"], body["parsed"]) == ("parsing", None)


def test_a_document_that_failed_has_no_output(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    token = open_session(client)
    document_id, job_id = upload(client, token, fixture_bytes["scanned.pdf"])
    settled(client, token, job_id)
    body = get_document(client, token, document_id).json()
    assert (body["status"], body["parsed"]) == ("failed", None)


def test_a_job_shows_its_state_and_a_fixed_error_when_it_failed(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    token = open_session(client)
    document_id, good = upload(client, token, fixture_bytes["simple.pdf"])
    assert settled(client, token, good) == {
        "id": good,
        "kind": "parse",
        "document_id": document_id,
        "analysis_id": None,
        "status": "succeeded",
        "stage": None,
        "completed_units": 0,
        "total_units": None,
        "error": None,
    }
    _, bad = upload(client, token, fixture_bytes["encrypted.pdf"])
    message, retryable = JOB_ERRORS["ENCRYPTED_PDF"]
    assert settled(client, token, bad)["error"] == {
        "code": "ENCRYPTED_PDF",
        "message": message,
        "retryable": retryable,
    }


def test_a_queued_job_says_queued(make_client: MakeClient, hanging: Callable[[], int]) -> None:
    client = make_client()
    token = open_session(client)
    _, first = upload(client, token, b"%PDF-1.4 a")
    wait_until(lambda: get_job(client, token, first).json()["status"] == "running")
    _, second = upload(client, token, b"%PDF-1.4 b")
    assert get_job(client, token, second).json()["status"] == "queued"


@pytest.mark.parametrize("path", [DOCS, JOBS])
def test_reading_needs_a_session(client: TestClient, path: str) -> None:
    assert client.get(f"{path}/anything").status_code == 401


def test_another_sessions_document_and_job_are_404_never_403(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    owner, other = open_session(client), open_session(client)
    document_id, job_id = upload(client, owner, fixture_bytes["simple.pdf"])
    settled(client, owner, job_id)
    for response in (
        get_document(client, other, document_id),
        get_job(client, other, job_id),
        client.delete(f"{DOCS}/{document_id}", headers=bearer(other)),
    ):
        assert_error(response, 404, "NOT_FOUND")
    # The refusal looks like an unknown id, and nothing was deleted
    assert_error(get_document(client, owner, "no-such-document"), 404, "NOT_FOUND")
    assert get_document(client, owner, document_id).json()["status"] == "parsed"


def test_unknown_ids_are_404_whatever_they_look_like(client: TestClient) -> None:
    token = open_session(client)
    for bad in ("no-such-id", str(uuid.uuid4()), "%00", "a" * 2000):
        assert_error(get_document(client, token, bad), 404, "NOT_FOUND")
        assert_error(get_job(client, token, bad), 404, "NOT_FOUND")


# Delete


def test_delete_returns_204_and_the_document_and_job_are_gone(
    client: TestClient, fixture_bytes: dict[str, bytes]
) -> None:
    token = open_session(client)
    document_id, job_id = upload(client, token, fixture_bytes["simple.pdf"])
    settled(client, token, job_id)
    response = client.delete(f"{DOCS}/{document_id}", headers=bearer(token))
    assert (response.status_code, response.content) == (204, b"")
    assert_error(get_document(client, token, document_id), 404, "NOT_FOUND")
    assert_error(get_job(client, token, job_id), 404, "NOT_FOUND")
    assert_error(client.delete(f"{DOCS}/{document_id}", headers=bearer(token)), 404, "NOT_FOUND")
    assert store_counts(client) == (0, 0)


def test_deleting_a_document_mid_parse_kills_its_child(
    make_client: MakeClient, hanging: Callable[[], int], spawned: list[subprocess.Popen[bytes]]
) -> None:
    client = make_client()
    token = open_session(client)
    document_id, job_id = upload(client, token, b"%PDF-1.4 x")
    pid = hanging()
    assert [child.poll() for child in spawned] == [None]
    assert client.delete(f"{DOCS}/{document_id}", headers=bearer(token)).status_code == 204
    assert [child.poll() is not None for child in spawned] == [True]
    assert not process_alive(pid)
    assert_error(get_job(client, token, job_id), 404, "NOT_FOUND")


def test_deleting_the_session_kills_the_child(
    make_client: MakeClient, hanging: Callable[[], int], spawned: list[subprocess.Popen[bytes]]
) -> None:
    client = make_client()
    token = open_session(client)
    upload(client, token, b"%PDF-1.4 x")
    pid = hanging()
    assert client.delete(CURRENT, headers=bearer(token)).status_code == 204
    assert [child.poll() is not None for child in spawned] == [True]
    assert not process_alive(pid)


def test_an_expired_session_loses_its_child(
    make_client: MakeClient,
    hanging: Callable[[], int],
    spawned: list[subprocess.Popen[bytes]],
    clock: FakeClock,
) -> None:
    client = make_client()
    token = open_session(client)
    _, job_id = upload(client, token, b"%PDF-1.4 x")
    pid = hanging()
    clock.advance(3600)
    assert_error(get_job(client, token, job_id), 401, "SESSION_INVALID")
    assert [child.poll() is not None for child in spawned] == [True]
    assert not process_alive(pid)


def test_closing_the_app_kills_the_running_child(
    catalogue_file: Path, hanging: Callable[[], int], spawned: list[subprocess.Popen[bytes]]
) -> None:
    settings = Settings(catalogue_path=catalogue_file)
    with TestClient(create_app(settings)) as client:
        token = open_session(client)
        upload(client, token, b"%PDF-1.4 x")
        pid = hanging()
        assert [child.poll() for child in spawned] == [None]
    assert [child.poll() is not None for child in spawned] == [True]
    assert not process_alive(pid)


def test_a_timeout_through_the_api(make_client: MakeClient, hanging: Callable[[], int]) -> None:
    client = make_client(parse_kill_seconds=1)
    token = open_session(client)
    document_id, job_id = upload(client, token, b"%PDF-1.4 x" + b"x" * 1_000_000)
    job = settled(client, token, job_id)
    assert (job["status"], job["error"]["code"]) == ("failed", "PARSE_TIMEOUT")
    assert not process_alive(hanging())
    assert get_document(client, token, document_id).json()["status"] == "failed"


def test_a_memory_kill_through_the_api(make_client: MakeClient) -> None:
    client = make_client(parse_memory_mib=64)
    token = open_session(client)
    _, job_id = upload(client, token, build_docx("<w:p/>" * 700_000))
    assert settled(client, token, job_id)["error"]["code"] == "PARSE_MEMORY_LIMIT"


def test_a_child_that_fails_is_retryable(
    make_client: MakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        parse_jobs, "WORKER_ARGS", [sys.executable, "-c", "import sys; sys.exit(3)"]
    )
    client = make_client()
    token = open_session(client)
    _, job_id = upload(client, token, b"%PDF-1.4 x")
    assert settled(client, token, job_id)["error"] == {
        "code": "PARSE_FAILED",
        "message": "Reading the file failed.",
        "retryable": True,
    }


# What must not leave the process


def test_a_file_that_makes_pdfminer_complain_leaks_nothing_through_stderr(
    client: TestClient,
    fixture_bytes: dict[str, bytes],
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)
    token = open_session(client)
    document_id, job_id = upload(client, token, fixture_bytes["unmapped_all.pdf"])
    assert settled(client, token, job_id)["status"] == "succeeded"
    seen = capfd.readouterr()
    replies = get_document(client, token, document_id).text + get_job(client, token, job_id).text
    for text in (caplog.text, seen.out, seen.err):
        assert "pdfminer" not in text
        assert "pdffont" not in text
    assert "pdffont" not in replies


def test_the_fixture_really_does_make_pdfminer_complain(
    fixture_bytes: dict[str, bytes], caplog: pytest.LogCaptureFixture
) -> None:
    """The check above means little unless this file produces a warning once the parser's own
    silencing is lifted. Here it is lifted for one parse in this process."""
    log = logging.getLogger("pdfminer")
    before = log.level
    log.setLevel(logging.WARNING)
    try:
        parse_document(fixture_bytes["unmapped_all.pdf"])
    finally:
        log.setLevel(before)
    assert any(record.name.startswith("pdfminer") for record in caplog.records)


# D3: the upload body stays in RAM


def ten_mib_docx() -> bytes:
    """A real package of exactly 10 MiB: a stored member of zeros pads it out."""
    base = build_docx("<w:p><w:r><w:t>Padded.</w:t></w:r></w:p>")

    def pack(pad: int) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as target:
            with zipfile.ZipFile(io.BytesIO(base)) as source:
                for name in source.namelist():
                    target.writestr(name, source.read(name))
            target.writestr(
                zipfile.ZipInfo("word/media/pad.bin", (2026, 1, 1, 0, 0, 0)), bytes(pad)
            )
        return buffer.getvalue()

    return pack(LIMIT - len(pack(0)))


def test_a_10_mib_upload_parses_end_to_end_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, catalogue_file: Path, clock: FakeClock
) -> None:
    raw = ten_mib_docx()
    assert len(raw) == LIMIT
    work, temp = tmp_path / "cwd", tmp_path / "tmp"
    work.mkdir()
    temp.mkdir()
    monkeypatch.chdir(work)
    for name in ("TMP", "TEMP", "TMPDIR"):
        monkeypatch.setenv(name, str(temp))  # the child inherits these
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    backend = Path(__file__).parents[1]
    before = snapshot(backend)

    settings = replace(Settings(catalogue_path=catalogue_file), parse_memory_mib=512)
    with TestClient(create_app(settings, clock=clock)) as client:
        token = open_session(client)
        document_id, job_id = upload(client, token, raw)
        assert settled(client, token, job_id)["status"] == "succeeded"
        assert get_document(client, token, document_id).json()["parsed"]["source_text"] == "Padded."

    assert list(work.iterdir()) == []
    assert list(temp.iterdir()) == []
    assert snapshot(backend) == before


def test_one_more_byte_than_the_limit_is_refused(client: TestClient) -> None:
    token = open_session(client)
    assert_error(post(client, token, b"\0" * (LIMIT + 1)), 413, "FILE_TOO_LARGE")


# The OpenAPI document


def test_openapi_describes_the_raw_body(client: TestClient) -> None:
    spec = client.get("/api/v1/openapi.json").json()
    upload_op = spec["paths"]["/api/v1/documents"]["post"]
    assert "application/octet-stream" in upload_op["requestBody"]["content"]
    assert upload_op["requestBody"]["required"] is True
    assert set(upload_op["responses"]) >= {"202", "400", "413", "415", "429"}
    assert "/api/v1/jobs/{job_id}" in spec["paths"]
    assert "delete" in spec["paths"]["/api/v1/documents/{document_id}"]
