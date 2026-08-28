"""PrizePicks / pick'em math (spec 27).

When the market gives no traditional per-side price, we still lead with the
probability, not the projection-minus-line gap. Absolute and relative edges are
reported, but the choice of MORE / LESS is driven by P(MORE) / P(LESS).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PickEmAssessment:
    line: float
    projection: float
    p_more: float
    p_less: float
    edge_abs: float       # projection - line
    edge_rel: float       # (projection - line) / line
    side: str             # "MORE" or "LESS", whichever the model favours
    p_side: float         # probability of the favoured side


def assess_pickem(line: float, projection: float, p_more: float) -> PickEmAssessment:
    p_less = 1.0 - p_more
    edge_abs = projection - line
    edge_rel = edge_abs / line if line != 0 else 0.0
    if p_more >= p_less:
        side, p_side = "MORE", p_more
    else:
        side, p_side = "LESS", p_less
    return PickEmAssessment(
        line=line,
        projection=projection,
        p_more=p_more,
        p_less=p_less,
        edge_abs=edge_abs,
        edge_rel=edge_rel,
        side=side,
        p_side=p_side,
    )


def entry_breakeven(n_legs: int, payout_multiplier: float) -> float:
    """Per-leg break-even win probability for an N-pick flex/power entry.

    For a straight power-play (all legs must hit) the entry wins with
    probability p^n (independent legs), so break-even per leg is:

        p_be = (1 / payout_multiplier) ** (1 / n)

    Correlated legs must not be multiplied naively (spec 56) — this is the
    independent-leg reference point only.
    """
    if n_legs <= 0 or payout_multiplier <= 0:
        raise ValueError("n_legs and payout_multiplier must be positive")
    return (1.0 / payout_multiplier) ** (1.0 / n_legs)
