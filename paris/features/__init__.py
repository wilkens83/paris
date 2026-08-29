"""Automatic feature engines (directive 10-12).

These turn real, normalized game logs and opponent stats into the model inputs
the quant engine needs — so the user never types base rates, L5/L10, expected
minutes or a matchup multiplier.
"""

from .historical import HistoricalFeatures, build_historical_features
from .matchup import MatchupFeature, matchup_from_allowed
from .models import GameLog
from .opportunity import MinutesModel, build_minutes_model, to_opportunity

__all__ = [
    "GameLog",
    "HistoricalFeatures",
    "build_historical_features",
    "MinutesModel",
    "build_minutes_model",
    "to_opportunity",
    "MatchupFeature",
    "matchup_from_allowed",
]
