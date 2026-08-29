"""Automatic opportunity / minutes model (directive 11).

Derives starter probability, expected minutes and the P(60+/70+/75+/80+/90)
distribution from real recent minutes and start history — the user never types
expected minutes. Lineup confirmation, when available, overrides the estimate.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from ..contracts import Opportunity
from .models import GameLog


@dataclass
class MinutesModel:
    starter_probability: float
    expected_minutes: float
    low: float
    high: float
    p_60: float
    p_70: float
    p_75: float
    p_80: float
    p_90: float
    certainty: str                 # A/B/C/D lineup-certainty grade (spec 37)


def _p_at_least(minutes: list[float], threshold: float) -> float:
    if not minutes:
        return 0.0
    return sum(1 for m in minutes if m >= threshold) / len(minutes)


def build_minutes_model(
    logs: list[GameLog],
    *,
    lineup_confirmed_start: bool | None = None,
    injured: bool | None = None,
) -> MinutesModel:
    """Estimate the minutes distribution from recent appearances.

    ``lineup_confirmed_start`` (from a real lineup feed) upgrades certainty and
    the starter probability; ``injured`` forces the opportunity to zero.
    """
    recent = sorted(logs, key=lambda g: g.date, reverse=True)[:10]
    minutes = [g.minutes for g in recent]
    starts = [g.started for g in recent]

    if injured:
        return MinutesModel(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "D")

    starter_share = (sum(1 for s in starts if s) / len(starts)) if starts else 0.0
    started_minutes = [m for m, s in zip(minutes, starts) if s] or minutes

    if lineup_confirmed_start is True:
        starter_prob, certainty = 1.0, "A"
        base_minutes = started_minutes
    elif lineup_confirmed_start is False:
        return MinutesModel(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "A")
    else:
        starter_prob = round(starter_share, 4)
        # certainty from how consistently they start (projected lineup only)
        certainty = "B" if starter_share >= 0.8 else "C" if starter_share >= 0.5 else "D"
        base_minutes = started_minutes

    exp = statistics.fmean(base_minutes) if base_minutes else 0.0
    sd = statistics.pstdev(base_minutes) if len(base_minutes) > 1 else 8.0
    # blend by starter probability: a bench game contributes low minutes
    expected = round(starter_prob * exp, 2)

    return MinutesModel(
        starter_probability=starter_prob,
        expected_minutes=expected,
        low=round(max(0.0, exp - sd), 1),
        high=round(min(95.0, exp + sd), 1),
        p_60=round(starter_prob * _p_at_least(base_minutes, 60), 4),
        p_70=round(starter_prob * _p_at_least(base_minutes, 70), 4),
        p_75=round(starter_prob * _p_at_least(base_minutes, 75), 4),
        p_80=round(starter_prob * _p_at_least(base_minutes, 80), 4),
        p_90=round(starter_prob * _p_at_least(base_minutes, 90), 4),
        certainty=certainty,
    )


def to_opportunity(model: MinutesModel, notes: str = "") -> Opportunity:
    return Opportunity(
        metric="minutes",
        expected=model.expected_minutes,
        low=model.low,
        high=model.high,
        certainty=model.certainty,
        starter_prob=model.starter_probability,
        notes=notes,
    )
