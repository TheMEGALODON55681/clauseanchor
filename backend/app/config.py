"""API settings, read once from CLAUSEANCHOR_ environment variables.

Parser limits (file size, page count, text length) live in the parser and are not set here.
An invalid value fails at startup with a message that names the variable and never the value.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PREFIX = "CLAUSEANCHOR_"

# API-owned limits, each with an environment variable of the same name under PREFIX.
SESSION_TTL_MINUTES = 60  # also the ceiling: the privacy promise is deletion within 60 minutes
PARSE_KILL_SECONDS = 120  # the slowest parse measured in 2-C took 23 s (Phases.md, 2-C)
PARSE_QUEUE_LENGTH = 2  # queue capacity of plan 9.3: parses that can wait while one runs
PARSE_MEMORY_MIB = 1536  # 1.2 GiB for a 500,000-character PDF, 2.5 GiB for a 100 MiB DOCX bomb

# Store limits and the sweep interval, not environment variables. Plan 9.2 names a 429 for the
# session limit and gives no number, and neither plan section gives a document limit, so these are
# proposals (Phases.md, 2-B).
MAX_SESSIONS = 25
MAX_DOCUMENTS_PER_SESSION = 5
SWEEP_INTERVAL_SECONDS = 30  # after expiry a session is unreachable at once and gone within this

# Analysis limits, constants and not variables (D8 names none). Plan 9.3 gives the queue and the
# 30 minutes. Nothing here measured the real model, so the time is a proposal (Phases.md, 2-D).
ANALYSIS_QUEUE_LENGTH = 2  # analyses that can wait while one runs
ANALYSIS_TIMEOUT_SECONDS = 1800  # one analysis, from the moment it starts running

# Tanishq's files, read in place. Found from this file and not from the working directory.
_ML = Path(__file__).resolve().parents[2] / "ml"
DEFAULT_CATALOGUE_PATH = _ML / "configs" / "catalogue.json"
STUB_FIXTURE_DIR = _ML / "fixtures"

_DIGEST = re.compile(r"[0-9a-f]{64}")


class ConfigError(ValueError):
    """An environment variable holds a value the API cannot use."""


def _text(env: Mapping[str, str], key: str, default: str | None) -> str | None:
    raw = env.get(PREFIX + key)
    if raw is None:
        return default
    if not raw.strip():
        raise ConfigError(f"{PREFIX}{key} must not be empty")
    return raw


def _int(env: Mapping[str, str], key: str, default: int, maximum: int | None = None) -> int:
    raw = env.get(PREFIX + key)
    if raw is None:
        return default
    # ASCII digits only (int() also takes "1_0" and other scripts), at most 9 so int() stays cheap
    if raw.isascii() and raw.isdigit() and len(raw) <= 9 and int(raw) >= 1:
        value = int(raw)
        if maximum is None or value <= maximum:
            return value
    limit = "at least 1" if maximum is None else f"from 1 to {maximum}"
    raise ConfigError(f"{PREFIX}{key} must be a whole number {limit}")


@dataclass(frozen=True, slots=True)
class Settings:
    analyzer: Literal["stub", "real"] = "stub"
    artifacts_dir: Path | None = None
    artifacts_sha256: str | None = None  # the canonical manifest digest, the trust anchor (D8)
    db_path: str = ":memory:"  # D8: D4 clears the tables at start, so a file only leaves traces
    session_ttl_minutes: int = SESSION_TTL_MINUTES
    parse_kill_seconds: int = PARSE_KILL_SECONDS
    parse_queue_length: int = PARSE_QUEUE_LENGTH
    parse_memory_mib: int = PARSE_MEMORY_MIB
    # Not environment variables: the catalogue is a file in the repository (D8), and the two
    # analysis limits are constants that a test moves through here
    catalogue_path: Path = DEFAULT_CATALOGUE_PATH
    analysis_queue_length: int = ANALYSIS_QUEUE_LENGTH
    analysis_timeout_seconds: float = ANALYSIS_TIMEOUT_SECONDS

    @property
    def mode(self) -> Literal["sample", "real"]:
        return "sample" if self.analyzer == "stub" else "real"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        analyzer = _text(env, "ANALYZER", "stub")
        if analyzer not in ("stub", "real"):
            raise ConfigError(f"{PREFIX}ANALYZER must be stub or real")
        artifacts = _text(env, "ARTIFACTS_DIR", None)
        if analyzer == "real" and artifacts is None:
            raise ConfigError(f"{PREFIX}ARTIFACTS_DIR is required when {PREFIX}ANALYZER is real")
        digest = _text(env, "ARTIFACTS_SHA256", None)
        if analyzer == "real" and digest is None:
            raise ConfigError(f"{PREFIX}ARTIFACTS_SHA256 is required when {PREFIX}ANALYZER is real")
        if digest is not None and not _DIGEST.fullmatch(digest):
            raise ConfigError(f"{PREFIX}ARTIFACTS_SHA256 must be 64 lowercase hexadecimal digits")
        return cls(
            analyzer=analyzer,
            artifacts_dir=Path(artifacts) if artifacts else None,
            artifacts_sha256=digest,
            db_path=_text(env, "DB_PATH", ":memory:") or ":memory:",
            session_ttl_minutes=_int(
                env, "SESSION_TTL_MINUTES", SESSION_TTL_MINUTES, SESSION_TTL_MINUTES
            ),
            parse_kill_seconds=_int(env, "PARSE_KILL_SECONDS", PARSE_KILL_SECONDS),
            parse_queue_length=_int(env, "PARSE_QUEUE_LENGTH", PARSE_QUEUE_LENGTH),
            parse_memory_mib=_int(env, "PARSE_MEMORY_MIB", PARSE_MEMORY_MIB),
        )
