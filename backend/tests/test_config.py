from __future__ import annotations

from pathlib import Path

import pytest

from app.config import ConfigError, Settings

INT_VARS = ["SESSION_TTL_MINUTES", "PARSE_KILL_SECONDS", "PARSE_QUEUE_LENGTH", "PARSE_MEMORY_MIB"]
DIGEST = "ab" * 32


def test_defaults() -> None:
    s = Settings.from_env({})
    assert s.analyzer == "stub"
    assert s.mode == "sample"
    assert s.artifacts_dir is None
    assert s.db_path == ":memory:"
    assert s.session_ttl_minutes == 60
    assert s.parse_kill_seconds == 120
    assert s.parse_queue_length == 2
    assert s.parse_memory_mib == 1536


def test_every_variable_is_read(tmp_path: Path) -> None:
    s = Settings.from_env(
        {
            "CLAUSEANCHOR_ANALYZER": "real",
            "CLAUSEANCHOR_ARTIFACTS_DIR": str(tmp_path),
            "CLAUSEANCHOR_ARTIFACTS_SHA256": DIGEST,
            "CLAUSEANCHOR_DB_PATH": "sessions.db",
            "CLAUSEANCHOR_SESSION_TTL_MINUTES": "30",
            "CLAUSEANCHOR_PARSE_KILL_SECONDS": "45",
            "CLAUSEANCHOR_PARSE_QUEUE_LENGTH": "5",
            "CLAUSEANCHOR_PARSE_MEMORY_MIB": "512",
        }
    )
    assert (s.analyzer, s.mode) == ("real", "real")
    assert (s.artifacts_dir, s.artifacts_sha256) == (tmp_path, DIGEST)
    assert s.db_path == "sessions.db"
    assert (s.session_ttl_minutes, s.parse_kill_seconds, s.parse_queue_length) == (30, 45, 5)
    assert s.parse_memory_mib == 512


def test_reads_the_process_environment_when_given_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUSEANCHOR_PARSE_QUEUE_LENGTH", "7")
    assert Settings.from_env().parse_queue_length == 7


def test_bad_analyzer_names_the_variable_and_not_the_value() -> None:
    with pytest.raises(ConfigError) as err:
        Settings.from_env({"CLAUSEANCHOR_ANALYZER": "bogus-value-xyz"})
    assert "CLAUSEANCHOR_ANALYZER" in str(err.value)
    assert "bogus-value-xyz" not in str(err.value)


def test_real_analyzer_requires_an_artifacts_dir() -> None:
    with pytest.raises(ConfigError, match="CLAUSEANCHOR_ARTIFACTS_DIR"):
        Settings.from_env({"CLAUSEANCHOR_ANALYZER": "real"})


def test_real_analyzer_requires_the_manifest_digest(tmp_path: Path) -> None:
    env = {"CLAUSEANCHOR_ANALYZER": "real", "CLAUSEANCHOR_ARTIFACTS_DIR": str(tmp_path)}
    with pytest.raises(ConfigError, match="CLAUSEANCHOR_ARTIFACTS_SHA256"):
        Settings.from_env(env)
    env["CLAUSEANCHOR_ARTIFACTS_SHA256"] = DIGEST
    assert Settings.from_env(env).artifacts_sha256 == DIGEST


@pytest.mark.parametrize(
    "value", ["", " ", "ab" * 31, "ab" * 33, "AB" * 32, "xy" * 32, "ab" * 32 + "\n"]
)
def test_a_bad_manifest_digest_names_the_variable_and_not_the_value(value: str) -> None:
    with pytest.raises(ConfigError) as err:
        Settings.from_env({"CLAUSEANCHOR_ARTIFACTS_SHA256": value})
    assert "CLAUSEANCHOR_ARTIFACTS_SHA256" in str(err.value)
    assert value.strip() == "" or value.strip() not in str(err.value)


def test_the_stub_ignores_a_missing_digest_and_the_analysis_limits_are_not_variables() -> None:
    s = Settings.from_env({"CLAUSEANCHOR_ANALYSIS_QUEUE_LENGTH": "9"})
    assert s.artifacts_sha256 is None
    assert (s.analysis_queue_length, s.analysis_timeout_seconds) == (2, 1800)


@pytest.mark.parametrize("name", ["ARTIFACTS_DIR", "DB_PATH"])
def test_empty_text_value_is_refused(name: str) -> None:
    with pytest.raises(ConfigError, match=f"CLAUSEANCHOR_{name}"):
        Settings.from_env({f"CLAUSEANCHOR_{name}": "  "})


@pytest.mark.parametrize("name", INT_VARS)
@pytest.mark.parametrize("value", ["abc", "0", "-5", "", " 5", "1_0", "٣", "1.5", "9" * 30])
def test_bad_number_is_refused(name: str, value: str) -> None:
    with pytest.raises(ConfigError, match=f"CLAUSEANCHOR_{name}"):
        Settings.from_env({f"CLAUSEANCHOR_{name}": value})


@pytest.mark.parametrize("name", INT_VARS)
def test_bad_number_message_does_not_echo_the_value(name: str) -> None:
    with pytest.raises(ConfigError) as err:
        Settings.from_env({f"CLAUSEANCHOR_{name}": "no-such-number-xyz"})
    assert "no-such-number-xyz" not in str(err.value)


def test_session_ttl_cannot_pass_the_sixty_minute_promise() -> None:
    assert Settings.from_env({"CLAUSEANCHOR_SESSION_TTL_MINUTES": "60"}).session_ttl_minutes == 60
    with pytest.raises(ConfigError, match="CLAUSEANCHOR_SESSION_TTL_MINUTES"):
        Settings.from_env({"CLAUSEANCHOR_SESSION_TTL_MINUTES": "61"})
