"""API-Football (API-Sports) real data provider (directive 7).

Wraps the real v3 REST API: fixtures, teams, players + statistics, lineups and
injuries. Every method returns a ``ProviderResult`` carrying the raw provider
payload plus provenance. No method fabricates data — a missing key raises
``ProviderNotConfigured`` and a request failure raises ``ProviderUnavailable``.

Reference: https://www.api-football.com/documentation-v3
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..config import Settings, get_settings
from .base import DataProvider, Provenance, ProviderResult
from .http import get_json

ENV_VAR = "API_FOOTBALL_KEY"


class ApiFootballProvider(DataProvider):
    name = "API-Football"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def required_env_var(self) -> str:
        return ENV_VAR

    def is_configured(self) -> bool:
        return bool(self.settings.api_football_key)

    # ------------------------------------------------------------------ #
    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        self.require_configured()
        headers = {
            "x-apisports-key": self.settings.api_football_key or "",
            "Accept": "application/json",
        }
        return get_json(
            f"{self.settings.api_football_base}/{endpoint.lstrip('/')}",
            provider=self.name,
            headers=headers,
            params=params,
            timeout=self.settings.http_timeout_seconds,
            max_retries=self.settings.http_max_retries,
        )

    def _result(self, endpoint: str, payload: Any, raw_id: str | None = None) -> ProviderResult:
        # API-Football wraps rows in {"response": [...]}
        value = payload.get("response", payload) if isinstance(payload, dict) else payload
        return ProviderResult(
            value=value,
            provenance=Provenance(provider=self.name, endpoint=endpoint, raw_external_id=raw_id),
        )

    # ------------------------------------------------------------------ #
    # fixtures / events
    # ------------------------------------------------------------------ #
    def fixtures_today(self, on: date | None = None, league: int | None = None,
                       season: int | None = None) -> ProviderResult:
        day = (on or date.today()).isoformat()
        params = {"date": day, "league": league, "season": season}
        return self._result("fixtures", self._get("fixtures", params), raw_id=day)

    def fixture(self, fixture_id: int) -> ProviderResult:
        return self._result("fixtures", self._get("fixtures", {"id": fixture_id}),
                            raw_id=str(fixture_id))

    def lineups(self, fixture_id: int) -> ProviderResult:
        return self._result("fixtures/lineups", self._get("fixtures/lineups", {"fixture": fixture_id}),
                            raw_id=str(fixture_id))

    def injuries(self, fixture_id: int | None = None, team: int | None = None,
                 season: int | None = None) -> ProviderResult:
        params = {"fixture": fixture_id, "team": team, "season": season}
        return self._result("injuries", self._get("injuries", params))

    # ------------------------------------------------------------------ #
    # players / statistics (real game-log source)
    # ------------------------------------------------------------------ #
    def players(self, team: int, season: int) -> ProviderResult:
        params = {"team": team, "season": season}
        return self._result("players", self._get("players", params))

    def player_statistics(self, player_id: int, season: int) -> ProviderResult:
        params = {"id": player_id, "season": season}
        return self._result("players", self._get("players", params), raw_id=str(player_id))

    def team_statistics(self, team: int, league: int, season: int) -> ProviderResult:
        params = {"team": team, "league": league, "season": season}
        return self._result("teams/statistics", self._get("teams/statistics", params),
                            raw_id=str(team))
