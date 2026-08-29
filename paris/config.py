"""Runtime configuration from environment variables (directive 7, 30).

Secrets are NEVER hard-coded. Every credential comes from the environment (a
``.env`` file is loaded if present). When a required key is missing the system
reports the exact configuration requirement instead of falling back to fake data
(directive 8, 30).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (no dependency). Real env vars always win."""
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"):
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
        break


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_football_key: str | None = os.environ.get("API_FOOTBALL_KEY") or None
    api_football_base: str = os.environ.get("API_FOOTBALL_BASE", "https://v3.football.api-sports.io")
    sportsgameodds_key: str | None = os.environ.get("SPORTSGAMEODDS_API_KEY") or None
    sportsgameodds_base: str = os.environ.get("SPORTSGAMEODDS_BASE", "https://api.sportsgameodds.com")
    database_url: str | None = os.environ.get("DATABASE_URL") or None

    # freshness thresholds in seconds (directive 13, 34 of the UI plan)
    market_freshness_seconds: int = int(os.environ.get("PARIS_MARKET_FRESHNESS", "900"))
    http_timeout_seconds: float = float(os.environ.get("PARIS_HTTP_TIMEOUT", "15"))
    http_max_retries: int = int(os.environ.get("PARIS_HTTP_RETRIES", "3"))

    def missing(self) -> list[str]:
        """Names of unset credentials required for live data."""
        gaps = []
        if not self.api_football_key:
            gaps.append("API_FOOTBALL_KEY")
        if not self.sportsgameodds_key:
            gaps.append("SPORTSGAMEODDS_API_KEY")
        return gaps


def get_settings() -> Settings:
    # re-read each call so tests / a running server pick up a newly-set key
    _load_dotenv()
    return Settings(
        api_football_key=os.environ.get("API_FOOTBALL_KEY") or None,
        api_football_base=os.environ.get("API_FOOTBALL_BASE", "https://v3.football.api-sports.io"),
        sportsgameodds_key=os.environ.get("SPORTSGAMEODDS_API_KEY") or None,
        sportsgameodds_base=os.environ.get("SPORTSGAMEODDS_BASE", "https://api.sportsgameodds.com"),
        database_url=os.environ.get("DATABASE_URL") or None,
        market_freshness_seconds=int(os.environ.get("PARIS_MARKET_FRESHNESS", "900")),
        http_timeout_seconds=float(os.environ.get("PARIS_HTTP_TIMEOUT", "15")),
        http_max_retries=int(os.environ.get("PARIS_HTTP_RETRIES", "3")),
    )
