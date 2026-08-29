"""FastAPI production backend (directive 24, 25, 30).

Serves real provider/stored data. When a required credential is missing, an
endpoint returns an explicit ``DATA SOURCE NOT CONFIGURED`` state with the exact
env var and setup hint — it never fabricates a response. When a configured
provider fails, it returns ``DATA SOURCE UNAVAILABLE``. Missing values are never
rendered as a real zero.

Run: ``uvicorn paris.api:app --reload``
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - import guard
    raise ImportError(
        "FastAPI is required for the API layer. Install with: pip install 'paris[api]'"
    ) from exc

from .config import get_settings
from .contracts import MarketLine
from .features import GameLog
from .orchestrator import analyze_market
from .providers.api_football import ApiFootballProvider
from .providers.base import ProviderNotConfigured, ProviderResult, ProviderUnavailable
from .providers.sports_game_odds import SportsGameOddsProvider
from .serialize import analysis_to_record
from .storage import AnalysisStore

app = FastAPI(title="PARIS", version="1.0.0",
              description="Production sports-betting decision-support API (live data).")


def _provider_call(fn, *args, **kwargs) -> ProviderResult:
    """Translate provider failures into explicit HTTP states (directive 25, 30)."""
    try:
        return fn(*args, **kwargs)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail={
            "status": "DATA SOURCE NOT CONFIGURED",
            "env_var": exc.env_var, "provider": exc.provider, "message": str(exc),
        })
    except ProviderUnavailable as exc:
        raise HTTPException(status_code=502, detail={
            "status": "DATA SOURCE UNAVAILABLE",
            "provider": exc.provider, "message": str(exc),
        })


def _envelope(result: ProviderResult) -> dict[str, Any]:
    p = result.provenance
    return {
        "status": "LIVE" if not result.is_stale(get_settings().market_freshness_seconds) else "STALE",
        "data": result.value,
        "provenance": {
            "provider": p.provider, "endpoint": p.endpoint,
            "retrieved_at": p.retrieved_at, "source_timestamp": p.source_timestamp,
            "age_seconds": result.age_seconds(),
        },
    }


# --------------------------------------------------------------------------- #
# health / config
# --------------------------------------------------------------------------- #
@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/config/status")
def config_status() -> dict[str, Any]:
    s = get_settings()
    return {
        "providers": {
            "api_football": {"configured": bool(s.api_football_key), "env_var": "API_FOOTBALL_KEY"},
            "sportsgameodds": {"configured": bool(s.sportsgameodds_key), "env_var": "SPORTSGAMEODDS_API_KEY"},
        },
        "database_url_configured": bool(s.database_url),
        "missing": s.missing(),
    }


# --------------------------------------------------------------------------- #
# events / lineups / injuries (API-Football)
# --------------------------------------------------------------------------- #
@app.get("/api/v1/events/today")
def events_today(league: int | None = None, season: int | None = None) -> dict[str, Any]:
    af = ApiFootballProvider()
    return _envelope(_provider_call(af.fixtures_today, date.today(), league, season))


@app.get("/api/v1/events/{event_id}")
def event(event_id: int) -> dict[str, Any]:
    return _envelope(_provider_call(ApiFootballProvider().fixture, event_id))


@app.get("/api/v1/events/{event_id}/lineups")
def event_lineups(event_id: int) -> dict[str, Any]:
    return _envelope(_provider_call(ApiFootballProvider().lineups, event_id))


@app.get("/api/v1/events/{event_id}/injuries")
def event_injuries(event_id: int) -> dict[str, Any]:
    return _envelope(_provider_call(ApiFootballProvider().injuries, event_id))


@app.get("/api/v1/events/{event_id}/props")
def event_props(event_id: str) -> dict[str, Any]:
    return _envelope(_provider_call(SportsGameOddsProvider().event_odds, event_id))


@app.get("/api/v1/players/{player_id}/history")
def player_history(player_id: int, season: int) -> dict[str, Any]:
    return _envelope(_provider_call(ApiFootballProvider().player_statistics, player_id, season))


# --------------------------------------------------------------------------- #
# analysis
# --------------------------------------------------------------------------- #
class GameLogIn(BaseModel):
    date: str
    opponent: str = ""
    is_home: bool = True
    started: bool = False
    minutes: float = 0.0
    stats: dict[str, float] = Field(default_factory=dict)


class MarketLineIn(BaseModel):
    line: float
    over_odds: float | None = None
    under_odds: float | None = None
    book: str = ""
    timestamp: str = ""
    payout_multiplier: float | None = None


class AnalyzePropIn(BaseModel):
    subject: str
    market: str
    side: str = "over"
    distribution: str = "auto"
    market_line: MarketLineIn
    logs: list[GameLogIn]
    opponent_allowed_per_game: float | None = None
    league_avg_per_game: float | None = None
    lineup_confirmed_start: bool | None = None
    injured: bool | None = None
    entity_confirmed: bool | None = None
    sources: list[str] = Field(default_factory=list)


@app.post("/api/v1/analyze/prop")
def analyze_prop_endpoint(req: AnalyzePropIn) -> dict[str, Any]:
    """Derive features from supplied real logs, verify, run the quant engine.

    This is the real analysis path: the caller provides normalized real game
    logs and a real market line; the system derives every model input.
    """
    logs = [GameLog(date=g.date, opponent=g.opponent, is_home=g.is_home,
                    started=g.started, minutes=g.minutes, stats=g.stats) for g in req.logs]
    if not logs:
        raise HTTPException(status_code=422, detail={
            "status": "WAIT — REQUIRED LIVE DATA IS NOT AVAILABLE",
            "message": "no game logs supplied; cannot derive features",
        })
    ml = MarketLine(**req.market_line.model_dump())
    out = analyze_market(
        subject=req.subject, market=req.market, side=req.side, market_line=ml,
        logs=logs, distribution=req.distribution,
        opponent_allowed_per_game=req.opponent_allowed_per_game,
        league_avg_per_game=req.league_avg_per_game,
        lineup_confirmed_start=req.lineup_confirmed_start, injured=req.injured,
        entity_confirmed=req.entity_confirmed, sources=req.sources,
    )
    verification = {"status": out.verification.status, "reasons": out.verification.reasons}
    if out.analysis is None:
        # no model could be built from real data — honest NO BET / WAIT
        return {
            "decision": out.decision,
            "verification": verification,
            "derivation": out.derivation,
            "data_gaps": out.data_gaps,
            "projection": None,
            "market_math": None,
        }
    record = analysis_to_record(out.analysis)
    record["verification"] = verification
    record["derivation"] = out.derivation
    record["data_gaps"] = out.data_gaps
    record["market_provenance"] = out.market_provenance
    return record


def _store() -> AnalysisStore:
    # SQLite is the current persistence (dev). PostgreSQL via DATABASE_URL is the
    # documented production target (see docs); a Postgres URL is not opened as a
    # SQLite path.
    return AnalysisStore(os.environ.get("PARIS_DB", "paris.db"))


@app.get("/api/v1/edge-finder")
def edge_finder(limit: int = 100) -> dict[str, Any]:
    store = _store()
    try:
        rows = store.list(limit=limit)
    finally:
        store.close()
    if not rows:
        return {"status": "NO CURRENT MARKET DATA", "candidates": []}
    return {"status": "LIVE", "candidates": rows}


@app.get("/api/v1/analyses/{analysis_id}")
def get_analysis(analysis_id: str) -> dict[str, Any]:
    store = _store()
    try:
        row = store.get(analysis_id)
    finally:
        store.close()
    if row is None:
        raise HTTPException(status_code=404, detail={"status": "UNAVAILABLE",
                                                     "message": f"no analysis {analysis_id}"})
    return dict(row)
