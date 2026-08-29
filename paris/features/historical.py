"""Automatic historical features from real game logs (directive 10).

Given normalized game logs and a market, derive the L5/L10/L20/Season windows,
the long-term per-90 rate, variance and the hit rate relative to the current
line — none of which the user types. Historical hit rate is computed and carried
separately from any model probability (directive 17, UI plan 14).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from ..contracts import FormWindow
from .models import GameLog


def _sorted_recent(logs: list[GameLog]) -> list[GameLog]:
    return sorted(logs, key=lambda g: g.date, reverse=True)


def _window(logs: list[GameLog], stat: str, label: str, line: float | None) -> FormWindow | None:
    vals = [g.stat(stat) for g in logs]
    if not vals:
        return None
    hit = None
    if line is not None and vals:
        hit = sum(1 for v in vals if v > line) / len(vals)
    return FormWindow(
        window=label,
        mean=round(statistics.fmean(vals), 4),
        median=round(statistics.median(vals), 4),
        stdev=(round(statistics.pstdev(vals), 4) if len(vals) > 1 else 0.0),
        minimum=min(vals),
        maximum=max(vals),
        hit_rate_over=(round(hit, 4) if hit is not None else None),
    )


@dataclass
class HistoricalFeatures:
    windows: list[FormWindow]
    rate_per90: float | None            # long-term per-90 rate for the stat
    season_mean: float | None
    variance: float | None              # season variance for the count law
    minutes_trend: float | None         # L5 mean minutes minus season mean minutes
    starter_share: float | None         # fraction of games started (season)
    n_games: int


def build_historical_features(
    logs: list[GameLog], stat: str, line: float | None = None
) -> HistoricalFeatures:
    logs = _sorted_recent(logs)
    windows: list[FormWindow] = []
    for label, n in (("L5", 5), ("L10", 10), ("L20", 20)):
        w = _window(logs[:n], stat, label, line)
        if w:
            windows.append(w)
    season = _window(logs, stat, "Season", line)
    if season:
        windows.append(season)

    # long-term per-90 rate from real minutes and stat totals
    total_min = sum(g.minutes for g in logs)
    total_stat = sum(g.stat(stat) for g in logs)
    rate_per90 = round((total_stat / total_min) * 90.0, 4) if total_min > 0 else None

    season_minutes = statistics.fmean([g.minutes for g in logs]) if logs else None
    l5_minutes = statistics.fmean([g.minutes for g in logs[:5]]) if logs else None
    minutes_trend = (
        round(l5_minutes - season_minutes, 2)
        if (l5_minutes is not None and season_minutes is not None) else None
    )
    starter_share = round(sum(1 for g in logs if g.started) / len(logs), 4) if logs else None

    return HistoricalFeatures(
        windows=windows,
        rate_per90=rate_per90,
        season_mean=(season.mean if season else None),
        variance=(season.variance if season else None),
        minutes_trend=minutes_trend,
        starter_share=starter_share,
        n_games=len(logs),
    )
