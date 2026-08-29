"""FastAPI backend: real analysis path + honest unavailable states.

Skipped entirely if FastAPI is not installed.
"""

import os

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

# ensure no creds leak into the test env -> exercises the not-configured path
os.environ.pop("API_FOOTBALL_KEY", None)
os.environ.pop("SPORTSGAMEODDS_API_KEY", None)

from paris.api import app  # noqa: E402

client = TestClient(app)


def test_health():
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_config_status_reports_missing():
    body = client.get("/api/v1/config/status").json()
    assert "API_FOOTBALL_KEY" in body["missing"]
    assert body["providers"]["api_football"]["configured"] is False


def test_events_today_not_configured():
    resp = client.get("/api/v1/events/today")
    assert resp.status_code == 503
    assert resp.json()["detail"]["status"] == "DATA SOURCE NOT CONFIGURED"
    assert resp.json()["detail"]["env_var"] == "API_FOOTBALL_KEY"


def test_props_not_configured():
    resp = client.get("/api/v1/events/evt_123/props")
    assert resp.status_code == 503
    assert resp.json()["detail"]["env_var"] == "SPORTSGAMEODDS_API_KEY"


def test_analyze_prop_real_path_with_supplied_logs():
    payload = {
        "subject": "Test Forward",
        "market": "shots",
        "side": "over",
        "market_line": {"line": 2.5, "over_odds": -130, "under_odds": 110, "book": "TEST"},
        "logs": [
            {"date": f"2026-03-{d:02d}", "minutes": 88, "started": True, "stats": {"shots": s}}
            for d, s in [(1, 4), (8, 3), (15, 5), (22, 2), (29, 4), (30, 3)]
        ],
        "opponent_allowed_per_game": 13.0,
        "league_avg_per_game": 11.0,
        "lineup_confirmed_start": True,
        "entity_confirmed": True,
    }
    body = client.post("/api/v1/analyze/prop", json=payload).json()
    assert body["decision"] in ("STRONG VALUE", "VALUE", "LEAN", "FAIR", "AVOID", "NO BET", "WAIT")
    assert body["verification"]["status"] in ("VERIFIED", "WAIT", "NO BET")
    # projection was derived, not typed
    assert body.get("projection") is not None


def test_analyze_prop_no_logs_is_unavailable():
    payload = {
        "subject": "Nobody", "market": "shots", "side": "over",
        "market_line": {"line": 2.5, "over_odds": -110, "under_odds": -110},
        "logs": [],
    }
    resp = client.post("/api/v1/analyze/prop", json=payload)
    assert resp.status_code == 422
    assert "REQUIRED LIVE DATA" in resp.json()["detail"]["status"]
