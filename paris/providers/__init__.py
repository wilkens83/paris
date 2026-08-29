"""Data providers (directive 6).

Real providers bring live/historical data into the system with full provenance
and NO silent fallback to fake data:

    - ApiFootballProvider     : fixtures, teams, players, stats, lineups, injuries
    - SportsGameOddsProvider  : sportsbook events, player props, lines, prices

``FileProvider`` is retained ONLY for tests, offline import/export and
reproducibility (directive 2, 6) — it is not a production data source.
"""

from .api_football import ApiFootballProvider
from .base import (
    DataProvider,
    Provenance,
    ProviderError,
    ProviderNotConfigured,
    ProviderResult,
    ProviderUnavailable,
)
from .file_provider import FileProvider, load_match
from .sports_game_odds import SportsGameOddsProvider

__all__ = [
    "DataProvider",
    "Provenance",
    "ProviderResult",
    "ProviderError",
    "ProviderNotConfigured",
    "ProviderUnavailable",
    "ApiFootballProvider",
    "SportsGameOddsProvider",
    "FileProvider",
    "load_match",
]
