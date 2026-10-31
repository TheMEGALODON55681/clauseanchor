"""Start, read and cancel an analysis through the app: stub mode on the core's own sample, real
mode on a fake core, and the errors on both."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import fields, replace
from datetime import datetime
from pathlib import Path

import pytest
from clauseanchor_core import (
    CONTRACT_VERSION,
    CategoryResult,
    ClauseFinding,
    Passage,
    RuleFlag,
    Span,
    StubAnalyzer,
)
from fastapi.testclient import TestClient

from app.api.errors import ERRORS, JOB_ERRORS
from app.config import DEFAULT_CATALOGUE_PATH, STUB_FIXTURE_DIR
from app.schemas import CategoryView, ClauseView, PassageView, RuleFlagView, SpanView
from app.services.scope import SCOPE_NOTICE
from tests.fake_core import (
    DIGEST,
    MADE_UP_TEXT,
    SAMPLE_TEXT,
    FakeCore,
    add_parsed,
    parsed_document,
    real_result,
)
from tests.synthetic import wait_until

SESSIONS = "/api/v1/sessions"
IDS = ["synthetic.alpha", "synthetic.beta", "synthetic.gamma"]
REAL = {"analyzer": "real", "artifacts_dir": Path("unused"), "artifacts_sha256": DIGEST}
ENDED = ("succeeded", "partial", "failed", "cancelled", "timed_out")
SECRET = "SECRET-CONTRACT-WORDS-77"
MakeClient = Callable[..., TestClient]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def open_session(client: TestClient) -> str:
    return client.post(SESSIONS).json()["token"]


def new_document(client: TestClient, token: str, parsed=None):
    store = client.app.state.store
    return add_parsed(store, store.get_session(token), parsed or parsed_document())


def body(ids=IDS, scope="unspecified") -> dict:
    return {"category_ids": ids, "jurisdiction_scope": scope}


def start(client: TestClient, token: str, document_id: str, payload=None):
    return client.post(
        f"/api/v1/documents/{document_id}/analyses",
        json=body() if payload is None else payload,
        headers=bearer(token),
    )


def started(client: TestClient, token: str, document_id: str, payload=None) -> tuple[str, str]:
    response = start(client, token, document_id, payload)
    assert response.status_code == 202, response.text
    assert set(response.json()) == {"analysis_id", "job_id"}
    return response.json()["analysis_id"], response.json()["job_id"]


def job(client: TestClient, token: str, job_id: str) -> dict:
    return client.get(f"/api/v1/jobs/{job_id}", headers=bearer(token)).json()


def analysis(client: TestClient, token: str, analysis_id: str):
    return client.get(f"/api/v1/analyses/{analysis_id}", headers=bearer(token))


def settle(client: TestClient, token: str, job_id: str, *statuses: str) -> dict:
    return wait_until(
        lambda: (j := job(client, token, job_id))["status"] in (statuses or ENDED) and j
    )


def cancel(client: TestClient, token: str, job_id: str):
    return client.post(f"/api/v1/jobs/{job_id}/cancel", headers=bearer(token))


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"] == ERRORS[code][1]
    assert error["retryable"] is ERRORS[code][2]
    assert uuid.UUID(error["request_id"])


def keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


@pytest.fixture
def real(make_client: MakeClient, fake_core: FakeCore) -> TestClient:
    return make_client(**REAL)


@pytest.fixture
def stub(make_client: MakeClient) -> TestClient:
    return make_client(catalogue_path=DEFAULT_CATALOGUE_PATH)


# --- stub mode, end to end ---------------------------------------------------------------------


def test_stub_mode_analyses_the_sample_from_start_to_result(stub: TestClient) -> None:
    token = open_session(stub)
    document = new_document(stub, token, parsed_document(SAMPLE_TEXT))
    ids = list(StubAnalyzer(STUB_FIXTURE_DIR).category_ids)
    analysis_id, job_id = started(stub, token, document.id, body(ids, "india_review"))

    ended = settle(stub, token, job_id)
    assert ended["status"] in ("succeeded", "partial")
    assert (ended["kind"], ended["document_id"], ended["analysis_id"]) == (
        "analysis",
        document.id,
        analysis_id,
    )
    assert (ended["completed_units"], ended["total_units"]) == (len(ids), len(ids))

    response = analysis(stub, token, analysis_id)
    assert response.status_code == 200
    result = response.json()
    assert set(result) == {
        "id",
        "document_id",
        "text_sha256",
        "contract_version",
        "artifact_manifest_sha256",
        "status",
        "mode",
        "jurisdiction_scope",
        "created_at",
        "finished_at",
        "scope_notice",
        "catalogue_version",
        "processing_complete",
        "decision_coverage",
        "categories",
        "warnings",
    }
    assert result["scope_notice"].encode("utf-8") == SCOPE_NOTICE.encode("utf-8")
    assert (result["id"], result["document_id"], result["status"]) == (
        analysis_id,
        document.id,
        ended["status"],
    )
    assert (result["mode"], result["jurisdiction_scope"]) == ("sample", "india_review")
    assert result["contract_version"] == CONTRACT_VERSION
    assert [c["category_id"] for c in result["categories"]] == ids
    states = {c["status"] for c in result["categories"]}
    assert {"found", "absent", "abstained", "unavailable"} >= states
    # Resolved counts an accepted decision only, and an abstention is not one
    resolved = sum(c["status"] in ("found", "absent") for c in result["categories"])
    assert result["decision_coverage"] == {"resolved": resolved, "requested": len(ids)}
    complete = all(c["search_complete"] for c in result["categories"])
    assert result["processing_complete"] is complete
    assert (ended["status"] == "succeeded") is complete
    for category in result["categories"]:
        for clause in category["clauses"]:
            span = clause["span"]
            assert SAMPLE_TEXT[span["start"] : span["end"]] == span["text"]
            assert clause["origin"] == "fixture"
    assert datetime.fromisoformat(result["created_at"]) <= datetime.fromisoformat(
        result["finished_at"]
    )


def test_no_field_anywhere_carries_a_verdict_a_score_or_a_percentage(stub: TestClient) -> None:
    token = open_session(stub)
    document = new_document(stub, token, parsed_document(SAMPLE_TEXT))
    ids = list(StubAnalyzer(STUB_FIXTURE_DIR).category_ids)
    analysis_id, job_id = started(stub, token, document.id, body(ids))
    settle(stub, token, job_id)
    found = keys(analysis(stub, token, analysis_id).json()) | keys(job(stub, token, job_id))
    banned = ("score", "verdict", "risk", "percent", "safety", "grade", "rating", "overall")
    assert [k for k in found if any(word in k.lower() for word in banned)] == []


def test_sample_mode_refuses_an_uploaded_document_with_a_409(stub: TestClient) -> None:
    token = open_session(stub)
    document = new_document(stub, token, parsed_document(MADE_UP_TEXT))
    ids = list(StubAnalyzer(STUB_FIXTURE_DIR).category_ids)
    assert_error(start(stub, token, document.id, body(ids)), 409, "SAMPLE_MODE_ONLY")
    assert (
        stub.app.state.store.get_document(
            stub.app.state.store.get_session(token).id, document.id
        ).analysis
        is None
    )


def test_sample_mode_takes_only_the_categories_the_sample_holds(stub: TestClient) -> None:
    token = open_session(stub)
    document = new_document(stub, token, parsed_document(SAMPLE_TEXT))
    held = set(StubAnalyzer(STUB_FIXTURE_DIR).category_ids)
    other = next(
        c["id"]
        for c in stub.get("/api/v1/capabilities").json()["categories"]
        if c["id"] not in held
    )
    assert_error(start(stub, token, document.id, body([other])), 422, "VALIDATION_ERROR")


# --- real mode, on a fake core -----------------------------------------------------------------


def test_review_candidates_pass_through_as_they_are_and_resolve_nothing(real: TestClient) -> None:
    token = open_session(real)
    document = new_document(real, token)
    analysis_id, job_id = started(real, token, document.id)
    assert settle(real, token, job_id)["status"] == "succeeded"
    result = analysis(real, token, analysis_id).json()
    assert (result["mode"], result["processing_complete"]) == ("real", True)
    assert result["decision_coverage"] == {"resolved": 0, "requested": 3}
    assert result["artifact_manifest_sha256"] == DIGEST
    for category in result["categories"]:
        assert category["status"] == "abstained"
        assert category["decision_confidence"] is None
        (clause,) = category["clauses"]
        assert (clause["status"], clause["confidence"], clause["origin"]) == (
            "review_candidate",
            None,
            "model",
        )
        assert (clause["confidence_band"], clause["calibration_scope"]) == (
            "unvalidated",
            "unvalidated",
        )


def test_an_unavailable_india_category_leaves_the_run_partial(
    real: TestClient, fake_core: FakeCore
) -> None:
    fake_core.unavailable = frozenset({"synthetic.beta"})
    token = open_session(real)
    document = new_document(real, token)
    analysis_id, job_id = started(real, token, document.id)
    assert settle(real, token, job_id)["status"] == "partial"
    result = analysis(real, token, analysis_id).json()
    by_id = {c["category_id"]: c for c in result["categories"]}
    assert by_id["synthetic.beta"]["status"] == "unavailable"
    assert by_id["synthetic.beta"]["reason_code"] == "unsupported_india_extension"
    assert (result["status"], result["processing_complete"]) == ("partial", False)
    assert result["decision_coverage"] == {"resolved": 0, "requested": 3}


def test_a_partial_parse_is_incomplete_and_no_category_reads_absent(real: TestClient) -> None:
    token = open_session(real)
    document = new_document(real, token, parsed_document(partial=True))
    analysis_id, job_id = started(real, token, document.id)
    assert settle(real, token, job_id)["status"] == "partial"
    result = analysis(real, token, analysis_id).json()
    assert result["processing_complete"] is False
    assert all(c["status"] != "absent" for c in result["categories"])
    assert result["scope_notice"] == SCOPE_NOTICE


def test_the_response_declares_exactly_the_fields_the_core_holds(real: TestClient) -> None:
    """A field the core adds must be added here on purpose: nothing leaks by default."""
    pairs = [
        (CategoryView, CategoryResult),
        (ClauseView, ClauseFinding),
        (SpanView, Span),
        (RuleFlagView, RuleFlag),
        (PassageView, Passage),
    ]
    for view, core in pairs:
        assert set(view.model_fields) == {f.name for f in fields(core)}, view.__name__


def test_an_analysis_that_has_not_ended_is_a_snapshot_with_no_categories(
    real: TestClient, fake_core: FakeCore
) -> None:
    fake_core.behave = fake_core.gated
    token = open_session(real)
    document = new_document(real, token)
    analysis_id, job_id = started(real, token, document.id)
    wait_until(fake_core.running.is_set)
    snapshot = analysis(real, token, analysis_id).json()
    assert (snapshot["status"], snapshot["categories"], snapshot["finished_at"]) == (
        "running",
        [],
        None,
    )
    assert (snapshot["processing_complete"], snapshot["artifact_manifest_sha256"]) == (False, None)
    assert snapshot["decision_coverage"] == {"resolved": 0, "requested": 3}
    assert snapshot["scope_notice"] == SCOPE_NOTICE
    fake_core.release.set()
    settle(real, token, job_id)


def test_a_new_analysis_replaces_the_documents_previous_one(real: TestClient) -> None:
    token = open_session(real)
    document = new_document(real, token)
    first, first_job = started(real, token, document.id)
    settle(real, token, first_job)
    second, second_job = started(real, token, document.id, body(IDS[:1], "india_review"))
    settle(real, token, second_job)
    assert analysis(real, token, first).status_code == 404
    latest = analysis(real, token, second).json()
    assert (latest["jurisdiction_scope"], latest["decision_coverage"]["requested"]) == (
        "india_review",
        1,
    )


# --- requests that are refused -----------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        body(["synthetic.alpha", "no.such.id"]),
        body([]),
        body(["synthetic.alpha", "synthetic.alpha"]),
        body(None),
        body("synthetic.alpha"),
        {"jurisdiction_scope": "unspecified"},
        {"category_ids": IDS},
        {**body(), "extra": 1},
        body(IDS, "everywhere"),
        body(IDS, None),
        body([1, 2]),
    ],
    ids=[
        "unknown",
        "empty",
        "duplicate",
        "null",
        "string",
        "no-ids",
        "no-scope",
        "extra-field",
        "bad-scope",
        "null-scope",
        "numbers",
    ],
)
def test_a_bad_request_is_a_422_that_echoes_nothing(real: TestClient, payload: object) -> None:
    token = open_session(real)
    document = new_document(real, token)
    response = start(real, token, document.id, payload)
    assert_error(response, 422, "VALIDATION_ERROR")
    assert "no.such.id" not in response.text


def test_a_body_that_is_not_json_is_a_422(real: TestClient) -> None:
    token = open_session(real)
    document = new_document(real, token)
    response = real.post(
        f"/api/v1/documents/{document.id}/analyses",
        content=b"not json",
        headers={**bearer(token), "Content-Type": "application/json"},
    )
    assert_error(response, 422, "VALIDATION_ERROR")


def test_a_document_that_is_not_parsed_yet_cannot_be_analysed(real: TestClient) -> None:
    token = open_session(real)
    store = real.app.state.store
    waiting = store.add_document(
        store.get_session(token).id, filename="a.pdf", media_type="application/pdf", byte_count=1
    )
    assert_error(start(real, token, waiting.id), 409, "DOCUMENT_NOT_PARSED")


def test_a_session_runs_one_analysis_and_the_next_start_is_a_409(
    real: TestClient, fake_core: FakeCore
) -> None:
    fake_core.behave = fake_core.gated
    token = open_session(real)
    first, second = new_document(real, token), new_document(real, token)
    _, job_id = started(real, token, first.id)
    assert_error(start(real, token, second.id), 409, "ANALYSIS_IN_PROGRESS")
    assert_error(start(real, token, first.id), 409, "ANALYSIS_IN_PROGRESS")
    fake_core.release.set()
    settle(real, token, job_id)
    assert start(real, token, second.id).status_code == 202


def test_a_full_queue_answers_429_and_leaves_no_job_behind(
    make_client: MakeClient, fake_core: FakeCore
) -> None:
    client = make_client(**REAL, analysis_queue_length=1)
    fake_core.behave = fake_core.gated
    first, second, third = (open_session(client) for _ in range(3))
    started(client, first, new_document(client, first).id)
    wait_until(fake_core.running.is_set)
    started(client, second, new_document(client, second).id)  # waits
    refused = new_document(client, third)
    assert_error(start(client, third, refused.id), 429, "ANALYSIS_QUEUE_FULL")
    store = client.app.state.store
    assert store.get_document(store.get_session(third).id, refused.id).analysis is None
    fake_core.release.set()


@pytest.mark.parametrize("state", ["loading", "failed"])
def test_no_analysis_starts_until_the_analyzer_is_loaded(
    make_client: MakeClient, fake_core: FakeCore, state: str
) -> None:
    if state == "loading":
        fake_core.load_gate = threading.Event()
    else:
        fake_core.load_error = RuntimeError(SECRET)
    client = make_client(**REAL, loaded=state == "failed")
    wait_until(lambda: fake_core.loads)
    token = open_session(client)
    document = new_document(client, token)
    response = start(client, token, document.id)
    assert_error(response, 503, "NOT_READY")
    assert response.json()["error"]["details"] == {"checks": {"analyzer": state}}
    assert SECRET not in response.text
    if fake_core.load_gate is not None:
        fake_core.load_gate.set()


# --- one session never reaches another's ----------------------------------------------------------


def test_another_sessions_ids_give_404_on_every_analysis_route(
    real: TestClient, fake_core: FakeCore
) -> None:
    fake_core.behave = fake_core.gated
    owner, stranger = open_session(real), open_session(real)
    document = new_document(real, owner)
    analysis_id, job_id = started(real, owner, document.id)
    wait_until(fake_core.running.is_set)
    assert_error(start(real, stranger, document.id), 404, "NOT_FOUND")
    assert_error(analysis(real, stranger, analysis_id), 404, "NOT_FOUND")
    assert_error(cancel(real, stranger, job_id), 404, "NOT_FOUND")
    assert_error(real.get(f"/api/v1/jobs/{job_id}", headers=bearer(stranger)), 404, "NOT_FOUND")
    assert job(real, owner, job_id)["status"] == "running"  # the stranger changed nothing
    fake_core.release.set()
    settle(real, owner, job_id)


def test_unknown_ids_give_404_and_a_bad_token_gives_401(real: TestClient) -> None:
    token = open_session(real)
    assert_error(start(real, token, "no-such-document"), 404, "NOT_FOUND")
    assert_error(analysis(real, token, "no-such-analysis"), 404, "NOT_FOUND")
    assert_error(cancel(real, token, "no-such-job"), 404, "NOT_FOUND")
    for call in (
        lambda: real.post("/api/v1/documents/x/analyses", json=body()),
        lambda: real.get("/api/v1/analyses/x"),
        lambda: real.post("/api/v1/jobs/x/cancel"),
    ):
        assert_error(call(), 401, "SESSION_INVALID")


# --- cancel, time limit, failures --------------------------------------------------------------


def test_cancel_stops_a_running_analysis_and_it_keeps_no_result(
    real: TestClient, fake_core: FakeCore
) -> None:
    fake_core.behave = fake_core.hold
    token = open_session(real)
    document = new_document(real, token)
    analysis_id, job_id = started(real, token, document.id)
    wait_until(fake_core.running.is_set)
    response = cancel(real, token, job_id)
    assert response.status_code == 202
    assert response.json()["id"] == job_id
    assert settle(real, token, job_id)["status"] == "cancelled"
    result = analysis(real, token, analysis_id).json()
    assert (result["status"], result["categories"], result["processing_complete"]) == (
        "cancelled",
        [],
        False,
    )
    assert result["decision_coverage"]["resolved"] == 0


def test_cancel_ends_a_waiting_analysis_at_once(real: TestClient, fake_core: FakeCore) -> None:
    fake_core.behave = fake_core.gated
    first, second = open_session(real), open_session(real)
    started(real, first, new_document(real, first).id)
    wait_until(fake_core.running.is_set)
    _, waiting = started(real, second, new_document(real, second).id)
    response = cancel(real, second, waiting)
    assert (response.status_code, response.json()["status"]) == (202, "cancelled")
    fake_core.release.set()


def test_a_job_that_has_ended_or_is_a_parse_cannot_be_cancelled(real: TestClient) -> None:
    token = open_session(real)
    document = new_document(real, token)
    _, job_id = started(real, token, document.id)
    settle(real, token, job_id)
    assert_error(cancel(real, token, job_id), 409, "JOB_NOT_CANCELLABLE")
    store = real.app.state.store
    parse_job = next(
        r[0]
        for r in store._db.execute("SELECT id FROM jobs WHERE kind = 'parse'")  # one per document
    )
    assert_error(cancel(real, token, parse_job), 409, "JOB_NOT_CANCELLABLE")


def test_an_analysis_over_the_time_limit_is_marked_timed_out(
    make_client: MakeClient, fake_core: FakeCore
) -> None:
    client = make_client(**REAL, analysis_timeout_seconds=0.3)
    fake_core.behave = fake_core.hold
    token = open_session(client)
    document = new_document(client, token)
    analysis_id, job_id = started(client, token, document.id)
    assert settle(client, token, job_id)["status"] == "timed_out"
    result = analysis(client, token, analysis_id).json()
    assert (result["status"], result["categories"], result["processing_complete"]) == (
        "timed_out",
        [],
        False,
    )


def test_an_analyzer_error_is_a_failed_job_with_a_fixed_message_and_no_text_anywhere(
    real: TestClient, fake_core: FakeCore, caplog: pytest.LogCaptureFixture
) -> None:
    def breaks(text, **_):
        raise RuntimeError(f"{SECRET} {text[:12]}")

    fake_core.behave = breaks
    token = open_session(real)
    document = new_document(real, token)
    with caplog.at_level(logging.DEBUG):
        analysis_id, job_id = started(real, token, document.id)
        failed = settle(real, token, job_id)
        shown = analysis(real, token, analysis_id).text + real.get("/ready").text
    message, retryable = JOB_ERRORS["ANALYSIS_FAILED"]
    assert failed["error"] == {"code": "ANALYSIS_FAILED", "message": message, "retryable": True}
    assert retryable is True
    assert "RuntimeError" in caplog.text
    for place in (caplog.text, shown, str(failed)):
        assert SECRET not in place
        assert MADE_UP_TEXT[:12] not in place


def test_an_invalid_result_is_a_failed_job_and_is_never_served(
    real: TestClient, fake_core: FakeCore
) -> None:
    fake_core.behave = lambda text, *, doc_id, category_ids, **_: replace(
        real_result(text, doc_id, category_ids), doc_id="another"
    )
    token = open_session(real)
    document = new_document(real, token)
    analysis_id, job_id = started(real, token, document.id)
    failed = settle(real, token, job_id)
    message, _ = JOB_ERRORS["ANALYSIS_INVALID_RESULT"]
    assert failed["error"] == {
        "code": "ANALYSIS_INVALID_RESULT",
        "message": message,
        "retryable": False,
    }
    result = analysis(real, token, analysis_id).json()
    assert (result["status"], result["categories"], result["processing_complete"]) == (
        "failed",
        [],
        False,
    )


# --- delete cancels ------------------------------------------------------------------------------


def test_deleting_the_document_mid_analysis_cancels_it(
    real: TestClient, fake_core: FakeCore
) -> None:
    fake_core.behave = fake_core.hold
    token = open_session(real)
    document = new_document(real, token)
    analysis_id, job_id = started(real, token, document.id)
    wait_until(fake_core.running.is_set)
    assert real.delete(f"/api/v1/documents/{document.id}", headers=bearer(token)).status_code == 204
    wait_until(fake_core.saw_stop.is_set)
    assert_error(analysis(real, token, analysis_id), 404, "NOT_FOUND")
    assert_error(real.get(f"/api/v1/jobs/{job_id}", headers=bearer(token)), 404, "NOT_FOUND")


def test_deleting_the_session_mid_analysis_cancels_it(
    real: TestClient, fake_core: FakeCore
) -> None:
    fake_core.behave = fake_core.hold
    token = open_session(real)
    document = new_document(real, token)
    started(real, token, document.id)
    wait_until(fake_core.running.is_set)
    assert real.delete(f"{SESSIONS}/current", headers=bearer(token)).status_code == 204
    wait_until(fake_core.saw_stop.is_set)
    assert real.get("/api/v1/analyses/x", headers=bearer(token)).status_code == 401


def test_a_session_that_expires_mid_analysis_cancels_it(
    real: TestClient, fake_core: FakeCore, clock
) -> None:
    fake_core.behave = fake_core.hold
    token = open_session(real)
    document = new_document(real, token)
    started(real, token, document.id)
    wait_until(fake_core.running.is_set)
    clock.advance(3601)
    real.app.state.store.sweep()
    wait_until(fake_core.saw_stop.is_set)


# --- /ready --------------------------------------------------------------------------------------


def test_ready_reports_the_analyzer_loading_then_ok(
    make_client: MakeClient, fake_core: FakeCore
) -> None:
    fake_core.load_gate = threading.Event()
    client = make_client(**REAL, loaded=False)
    wait_until(lambda: fake_core.loads)
    waiting = client.get("/api/v1/ready")
    assert waiting.status_code == 503
    assert waiting.json()["error"]["details"]["checks"]["analyzer"] == "loading"
    assert client.get("/api/v1/health").status_code == 200  # the app answers while it loads
    fake_core.load_gate.set()
    wait_until(lambda: client.get("/api/v1/ready").status_code == 200)


def test_ready_reports_a_failed_load_and_logs_only_the_class(
    make_client: MakeClient, fake_core: FakeCore, caplog: pytest.LogCaptureFixture
) -> None:
    fake_core.load_error = ValueError(f"{SECRET} at /some/path")
    with caplog.at_level(logging.DEBUG):
        client = make_client(**REAL)
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["error"]["details"]["checks"]["analyzer"] == "failed"
    assert "ValueError" in caplog.text
    assert SECRET not in caplog.text + response.text


def test_a_real_bundle_that_does_not_exist_is_failed_and_never_the_stub(
    make_client: MakeClient, tmp_path: Path
) -> None:
    client = make_client(**{**REAL, "artifacts_dir": tmp_path / "absent"})
    checks = client.get("/api/v1/ready").json()["error"]["details"]["checks"]
    assert checks["analyzer"] == "failed"
    assert client.app.state.analysis_queue.analyzer is None
    assert str(tmp_path) not in client.get("/api/v1/ready").text
