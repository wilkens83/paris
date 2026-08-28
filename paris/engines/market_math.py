"""Market Math Engine — sportsbook price mathematics.

Implements section 26 of the master spec: convert odds, remove the vig,
compute fair odds, edge and expected value. Every function here is pure and
deterministic — the LLM must never invent a price, only feed verified odds
into these formulas.

American ("moneyline") odds convention is used throughout:
    -150  means risk 150 to win 100
    +130  means risk 100 to win 130
"""

from __future__ import annotations

from dataclasses import dataclass


def implied_prob(american_odds: float) -> float:
    """Implied probability of a single American price (spec 26.1).

    Negative odds:  P = |odds| / (|odds| + 100)
    Positive odds:  P = 100 / (odds + 100)
    """
    if american_odds == 0:
        raise ValueError("American odds cannot be 0")
    if american_odds < 0:
        o = abs(american_odds)
        return o / (o + 100.0)
    return 100.0 / (american_odds + 100.0)


def remove_vig_two_way(over_odds: float, under_odds: float) -> tuple[float, float]:
    """Remove the bookmaker margin from a two-sided market (spec 26.2).

    Returns (fair_over, fair_under) — the no-vig probabilities that sum to 1.
    """
    raw_over = implied_prob(over_odds)
    raw_under = implied_prob(under_odds)
    total = raw_over + raw_under
    if total <= 0:
        raise ValueError("Invalid odds: implied total is non-positive")
    return raw_over / total, raw_under / total


def hold_percent(over_odds: float, under_odds: float) -> float:
    """The book's hold (overround) on a two-way market, in probability points."""
    return implied_prob(over_odds) + implied_prob(under_odds) - 1.0


def fair_odds(prob: float) -> float:
    """Convert a probability into fair American odds (spec 26.4).

    p > 0.5 -> negative odds ; p < 0.5 -> positive odds.
    """
    if not 0.0 < prob < 1.0:
        raise ValueError("Probability must be strictly between 0 and 1")
    if prob > 0.5:
        return -(prob / (1.0 - prob)) * 100.0
    return ((1.0 - prob) / prob) * 100.0


def profit_per_unit(american_odds: float) -> float:
    """Profit on a winning 1-unit stake (spec 26.5).

    Positive odds:  profit = odds / 100
    Negative odds:  profit = 100 / |odds|
    """
    if american_odds == 0:
        raise ValueError("American odds cannot be 0")
    if american_odds > 0:
        return american_odds / 100.0
    return 100.0 / abs(american_odds)


def expected_value(prob_win: float, american_odds: float) -> float:
    """EV of a 1-unit bet given the model win probability (spec 26.5).

    EV = P_win * profit - (1 - P_win)
    """
    profit = profit_per_unit(american_odds)
    return prob_win * profit - (1.0 - prob_win)


def edge(prob_model: float, prob_market_fair: float) -> float:
    """Probability-point edge over the no-vig market price (spec 26.3)."""
    return prob_model - prob_market_fair


@dataclass(frozen=True)
class PriceAssessment:
    """Complete market-math verdict for one side of one market."""

    prob_model: float
    prob_market_fair: float
    edge_points: float          # model minus fair, in probability points
    edge_relative: float        # edge as a fraction of the fair probability
    fair_odds_model: float      # the price the model thinks is fair
    market_odds: float          # the price actually offered
    ev_per_unit: float          # EV at the offered price
    hold: float | None = None   # book hold if the opposite side was supplied


def assess_price(
    prob_model: float,
    market_odds: float,
    over_odds: float | None = None,
    under_odds: float | None = None,
    side: str = "over",
) -> PriceAssessment:
    """Full price assessment for the chosen side.

    If both ``over_odds`` and ``under_odds`` are given, the market fair
    probability is computed no-vig; otherwise it falls back to the raw implied
    probability of the offered price (a weaker comparison, flagged by hold=None).
    """
    if over_odds is not None and under_odds is not None:
        fair_over, fair_under = remove_vig_two_way(over_odds, under_odds)
        prob_market_fair = fair_over if side.lower() in ("over", "more") else fair_under
        hold = hold_percent(over_odds, under_odds)
    else:
        prob_market_fair = implied_prob(market_odds)
        hold = None

    e = edge(prob_model, prob_market_fair)
    rel = e / prob_market_fair if prob_market_fair > 0 else 0.0
    return PriceAssessment(
        prob_model=prob_model,
        prob_market_fair=prob_market_fair,
        edge_points=e,
        edge_relative=rel,
        fair_odds_model=fair_odds(prob_model),
        market_odds=market_odds,
        ev_per_unit=expected_value(prob_model, market_odds),
        hold=hold,
    )
