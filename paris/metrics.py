"""Calibration & performance metrics (plan sections 19-20, spec 25/59).

Pure functions over resolved analyses. A resolved item is a dict with at least
``model_probability`` (the P assigned to the chosen side) and ``result``
("HIT"/"MISS"/"PUSH"). Pushes are excluded from calibration scoring.

Never confuse a hit rate, a score, or a grade with a calibrated probability
(spec 25) — these functions keep them distinct.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable


def _binary_outcomes(items: Iterable[dict[str, Any]]) -> list[tuple[float, int]]:
    """Return (p, y) pairs, dropping pushes and rows missing p or result."""
    out: list[tuple[float, int]] = []
    for it in items:
        p = it.get("model_probability")
        res = (it.get("result") or "").upper()
        if p is None or res not in ("HIT", "MISS"):
            continue
        out.append((float(p), 1 if res == "HIT" else 0))
    return out


def brier_score(items: Iterable[dict[str, Any]]) -> float | None:
    pairs = _binary_outcomes(items)
    if not pairs:
        return None
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def log_loss(items: Iterable[dict[str, Any]], eps: float = 1e-12) -> float | None:
    pairs = _binary_outcomes(items)
    if not pairs:
        return None
    total = 0.0
    for p, y in pairs:
        p = min(max(p, eps), 1 - eps)
        total += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return total / len(pairs)


def hit_rate(items: Iterable[dict[str, Any]]) -> float | None:
    pairs = _binary_outcomes(items)
    if not pairs:
        return None
    return sum(y for _, y in pairs) / len(pairs)


@dataclass
class CalibrationBucket:
    label: str
    low: float
    high: float
    n: int = 0
    hits: int = 0
    prob_sum: float = 0.0

    @property
    def actual(self) -> float | None:
        return self.hits / self.n if self.n else None

    @property
    def predicted(self) -> float | None:
        return self.prob_sum / self.n if self.n else None


# the plan's buckets (section 20)
_BUCKET_EDGES = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.01)]


def calibration_buckets(items: Iterable[dict[str, Any]]) -> list[CalibrationBucket]:
    buckets = [
        CalibrationBucket(label=f"{int(lo*100)}-{int(min(hi,1.0)*100)}%", low=lo, high=hi)
        for lo, hi in _BUCKET_EDGES
    ]
    for p, y in _binary_outcomes(items):
        for b in buckets:
            if b.low <= p < b.high:
                b.n += 1
                b.hits += y
                b.prob_sum += p
                break
    return buckets


def calibration_error(items: Iterable[dict[str, Any]]) -> float | None:
    """Expected Calibration Error: n-weighted mean |predicted - actual| over buckets."""
    buckets = [b for b in calibration_buckets(items) if b.n]
    total = sum(b.n for b in buckets)
    if not total:
        return None
    return sum(b.n * abs(b.predicted - b.actual) for b in buckets) / total


def roi(items: Iterable[dict[str, Any]]) -> float | None:
    """Realized ROI per unit staked, using stored EV odds when available.

    A HIT returns the offered-odds profit, a MISS loses 1 unit, PUSH is void.
    Rows without ``offered_odds`` are skipped (no price to settle against).
    """
    staked = 0.0
    profit = 0.0
    for it in items:
        res = (it.get("result") or "").upper()
        odds = it.get("offered_odds")
        if res == "PUSH" or odds is None:
            continue
        if res not in ("HIT", "MISS"):
            continue
        staked += 1.0
        if res == "HIT":
            profit += (odds / 100.0) if odds > 0 else (100.0 / abs(odds))
        else:
            profit -= 1.0
    return profit / staked if staked else None


def average_clv(items: Iterable[dict[str, Any]]) -> float | None:
    vals = [it["clv"] for it in items if it.get("clv") is not None]
    return sum(vals) / len(vals) if vals else None


@dataclass
class PerformanceSummary:
    n_resolved: int
    hit_rate: float | None = None
    brier: float | None = None
    log_loss: float | None = None
    calibration_error: float | None = None
    roi: float | None = None
    average_clv: float | None = None
    buckets: list[CalibrationBucket] = field(default_factory=list)


def summarize(items: Iterable[dict[str, Any]]) -> PerformanceSummary:
    items = list(items)
    resolved = [it for it in items if (it.get("result") or "").upper() in ("HIT", "MISS", "PUSH")]
    return PerformanceSummary(
        n_resolved=len(resolved),
        hit_rate=hit_rate(items),
        brier=brier_score(items),
        log_loss=log_loss(items),
        calibration_error=calibration_error(items),
        roi=roi(items),
        average_clv=average_clv(items),
        buckets=calibration_buckets(items),
    )
