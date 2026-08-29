"""SportsGameOdds real market provider (directive 7, 13).

Wraps the real REST API for sportsbook events, player props and prices. Returns
``ProviderResult`` with provider payload + provenance. Missing key raises
``ProviderNotConfigured``; request failure raises ``ProviderUnavailable``. No
fabricated lines or prices (directive 19).

Reference: https://sportsgameodds.com/docs/
"""

from __future__ import annotations

from typing import Any

from ..config import Settings, get_settings
from .base import DataProvider, Provenance, ProviderResult
from .http import get_json

ENV_VAR = "SPORTSGAMEODDS_API_KEY"


class SportsGameOddsProvider(DataProvider):
    name = "SportsGameOdds"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def required_env_var(self) -> str:
        return ENV_VAR

    def is_configured(self) -> bool:
        return bool(self.settings.sportsgameodds_key)

    # ------------------------------------------------------------------ #
    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        self.require_configured()
        headers = {
            "X-Api-Key": self.settings.sportsgameodds_key or "",
            "Accept": "application/json",
        }
        return get_json(
            f"{self.settings.sportsgameodds_base}/{endpoint.lstrip('/')}",
            provider=self.name,
            headers=headers,
            params=params,
            timeout=self.settings.http_timeout_seconds,
            max_retries=self.settings.http_max_retries,
        )

    def _result(self, endpoint: str, payload: Any, raw_id: str | None = None) -> ProviderResult:
        value = payload.get("data", payload) if isinstance(payload, dict) else payload
        return ProviderResult(
            value=value,
            provenance=Provenance(provider=self.name, endpoint=endpoint, raw_external_id=raw_id),
        )

    # ------------------------------------------------------------------ #
    def events(self, league_id: str | None = None, sport_id: str = "SOCCER",
               date_from: str | None = None) -> ProviderResult:
        params = {"sportID": sport_id, "leagueID": league_id, "startsAfter": date_from}
        return self._result("v2/events", self._get("v2/events", params))

    def event_odds(self, event_id: str) -> ProviderResult:
        """All markets (including player props) with lines and prices for one event."""
        return self._result("v2/events", self._get("v2/events", {"eventID": event_id}),
                            raw_id=event_id)
