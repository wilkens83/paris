"""Live-data helpers + honest failure states for the UI (directive 25, 30).

No demo fallback. Each fetch returns a (status, payload, detail) tuple where
status is one of: LIVE, STALE, NOT_CONFIGURED, UNAVAILABLE. The pages render the
matching banner and never substitute fake data.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from paris.config import get_settings  # noqa: E402
from paris.providers import (  # noqa: E402
    ApiFootballProvider,
    ProviderNotConfigured,
    ProviderResult,
    ProviderUnavailable,
    SportsGameOddsProvider,
)


def config_status() -> dict[str, Any]:
    s = get_settings()
    return {
        "api_football": bool(s.api_football_key),
        "sportsgameodds": bool(s.sportsgameodds_key),
        "database_url": bool(s.database_url),
        "missing": s.missing(),
    }


def _call(fn, *args, **kwargs) -> tuple[str, Any, str]:
    try:
        result: ProviderResult = fn(*args, **kwargs)
    except ProviderNotConfigured as exc:
        return "NOT_CONFIGURED", None, str(exc)
    except ProviderUnavailable as exc:
        return "UNAVAILABLE", None, str(exc)
    status = "STALE" if result.is_stale(get_settings().market_freshness_seconds) else "LIVE"
    return status, result, ""


def fetch_today_events(league: int | None = None, season: int | None = None):
    return _call(ApiFootballProvider().fixtures_today, date.today(), league, season)


def fetch_event_props(event_id: str):
    return _call(SportsGameOddsProvider().event_odds, event_id)


def render_status_banner(status: str, detail: str = "") -> None:
    """Render the honest state for a failed/degraded fetch (directive 25)."""
    if status == "NOT_CONFIGURED":
        st.error("🔌 DATA SOURCE NOT CONFIGURED")
        st.caption(detail or "A required live-data credential is not set.")
        st.markdown(
            "Set the missing credential(s) in the environment or a `.env` file "
            "(see `.env.example`), then reload. PARIS never substitutes demo data."
        )
    elif status == "UNAVAILABLE":
        st.warning("⚠️ DATA SOURCE UNAVAILABLE")
        st.caption(detail or "The provider is configured but did not respond.")
    elif status == "STALE":
        st.warning("🕒 MARKET DATA STALE — refresh required before betting.")


def freshness_label(result: ProviderResult) -> str:
    age = result.age_seconds()
    if age is None:
        return "freshness unknown"
    if age < 90:
        return f"updated {int(age)} sec ago"
    if age < 5400:
        return f"updated {int(age // 60)} min ago"
    return f"updated {int(age // 3600)} h ago"
