"""API settings, read once from CLAUSEANCHOR_ environment variables.

Parser limits (file size, page count, text length) live in the parser and are not set here.
An invalid value fails at startup with a message that names the variable and never the value.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PREFIX = "CLAUSEANCHOR_"

# API-owned limits, each with an environment variable of the same name under PREFIX.
SESSION_TTL_MINUTES = 60  # also the ceiling: the privacy promise is deletion within 60 minutes
PARSE_KILL_SECONDS = 120  # provisional, 2-C re-measures it (Phases.md, 2-C)
PARSE_QUEUE_LENGTH = 2  # queue capacity of plan 9.3

# Store limits and the sweep interval, not environment variables. Plan 9.2 names a 429 for the
# session limit and gives no number, and neither plan section gives a document limit, so these are
# proposals (Phases.md, 2-B).
MAX_SESSIONS = 25
MAX_DOCUMENTS_PER_SESSION = 5
SWEEP_INTERVAL_SECONDS = 30  # after expiry a session is unreachable at once and gone within this

DEFAULT_CATALOGUE_PATH = Path(__file__).parent / "catalogue.json"


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
    db_path: str = ":memory:"  # D8: D4 clears the tables at start, so a file only leaves traces
    session_ttl_minutes: int = SESSION_TTL_MINUTES
    parse_kill_seconds: int = PARSE_KILL_SECONDS
    parse_queue_length: int = PARSE_QUEUE_LENGTH
    # Not an environment variable: the catalogue is a file that ships with the code (D8)
    catalogue_path: Path = DEFAULT_CATALOGUE_PATH

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
        return cls(
            analyzer=analyzer,
            artifacts_dir=Path(artifacts) if artifacts else None,
            db_path=_text(env, "DB_PATH", ":memory:") or ":memory:",
            session_ttl_minutes=_int(
                env, "SESSION_TTL_MINUTES", SESSION_TTL_MINUTES, SESSION_TTL_MINUTES
            ),
            parse_kill_seconds=_int(env, "PARSE_KILL_SECONDS", PARSE_KILL_SECONDS),
            parse_queue_length=_int(env, "PARSE_QUEUE_LENGTH", PARSE_QUEUE_LENGTH),
        )
