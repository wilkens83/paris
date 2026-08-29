"""Assemble a fully-derived Prop from real features (directive 5, 10-12).

This is the bridge that replaces manual data entry: given real game logs, a real
market line and real opponent stats, it derives every model input the quant
engine needs and returns a ``Prop``. The user selects a market; the system fills
the numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import MarketLine, Prop
from .features import (
    GameLog,
    build_historical_features,
    build_minutes_model,
    matchup_from_allowed,
    to_opportunity,
)


@dataclass
class AssembledProp:
    prop: Prop
    reasons: list[str]              # human-readable derivation notes
    data_gaps: list[str]            # missing pieces that lower confidence


def assemble_prop(
    *,
    subject: str,
    market: str,
    side: str,
    market_line: MarketLine,
    logs: list[GameLog],
    distribution: str = "auto",
    opponent_allowed_per_game: float | None = None,
    league_avg_per_game: float | None = None,
    lineup_confirmed_start: bool | None = None,
    injured: bool | None = None,
    sources: list[str] | None = None,
) -> AssembledProp:
    reasons: list[str] = []
    gaps: list[str] = []

    hist = build_historical_features(logs, market, market_line.line)
    if hist.n_games == 0:
        gaps.append("no game logs available")
    if hist.rate_per90 is None:
        gaps.append("no minutes to derive a per-90 rate")

    minutes = build_minutes_model(
        logs, lineup_confirmed_start=lineup_confirmed_start, injured=injured
    )
    opportunity = to_opportunity(
        minutes,
        notes=("confirmed start" if lineup_confirmed_start else "projected from recent minutes"),
    )
    reasons.append(
        f"expected minutes {minutes.expected_minutes:g} "
        f"(starter p={minutes.starter_probability:.0%}, certainty {minutes.certainty})"
    )

    matchup = matchup_from_allowed(market, opponent_allowed_per_game, league_avg_per_game)
    reasons.append(matchup.note)
    if matchup.multiplier == 1.0 and opponent_allowed_per_game is None:
        gaps.append("opponent allowed-rate unavailable (matchup neutral)")

    if hist.rate_per90 is not None:
        reasons.append(f"long-term rate {hist.rate_per90:g}/90 from {hist.n_games} games")

    prop = Prop(
        subject=subject,
        market=market,
        side=side,
        market_line=market_line,
        distribution=distribution,
        base_rate_per90=hist.rate_per90,
        form=hist.windows,
        opportunity=opportunity,
        matchup_multiplier=matchup.multiplier,
        matchup_note=matchup.note,
        variance_hint=hist.variance,
        verified=False,                 # the verifier decides this, not assembly
        sources=sources or [],
    )
    return AssembledProp(prop=prop, reasons=reasons, data_gaps=gaps)
