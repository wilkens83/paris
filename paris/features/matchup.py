"""Automatic matchup features (directive 12).

Derives a matchup multiplier from real opponent "allowed" rates versus the
league average — the user never enters ``matchup_multiplier``. The reasoning is
returned so the UI can display *why*, not ask for a number.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MatchupFeature:
    multiplier: float
    note: str
    opponent_allowed_per_game: float | None = None
    league_avg_per_game: float | None = None


# how strongly the opponent's allowed-rate ratio bends the projection. A cap
# keeps a single soft stat from dominating the model.
_SENSITIVITY = 0.6
_CAP = 0.25  # +/- 25%


def matchup_from_allowed(
    stat: str,
    opponent_allowed_per_game: float | None,
    league_avg_per_game: float | None,
) -> MatchupFeature:
    """Bend the projection by how much more/less the opponent concedes on this
    stat than a league-average opponent."""
    if not opponent_allowed_per_game or not league_avg_per_game or league_avg_per_game <= 0:
        return MatchupFeature(1.0, "matchup neutral (opponent allowed-rate unavailable)")

    ratio = opponent_allowed_per_game / league_avg_per_game
    raw = 1.0 + _SENSITIVITY * (ratio - 1.0)
    mult = max(1.0 - _CAP, min(1.0 + _CAP, raw))
    direction = "inflates" if mult > 1.0 else "suppresses" if mult < 1.0 else "neutral for"
    note = (
        f"opponent allows {opponent_allowed_per_game:g} {stat}/game vs league "
        f"{league_avg_per_game:g} → {direction} (x{mult:.3f})"
    )
    return MatchupFeature(
        multiplier=round(mult, 4),
        note=note,
        opponent_allowed_per_game=opponent_allowed_per_game,
        league_avg_per_game=league_avg_per_game,
    )
