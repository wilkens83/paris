"""Model Engine — build a central projection and its distribution (spec 21).

The projection is transparent and explainable, never a black box. It starts
from a long-term base rate, scales it by projected opportunity, then applies a
recent-form nudge and a matchup multiplier. Each step is recorded so the
AI Analyzer (spec 16.8) can explain what pushes the number up or down.

    mu = base_rate  x  opportunity_scale  x  form_factor  x  matchup_multiplier
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import Prop
from .distributions import OverUnder, prob_over


# Weight given to recent form when nudging the long-term base rate. Recent form
# is a signal, never a probability (spec 1) — so it only bends the base rate,
# it does not replace it.
FORM_WEIGHT = 0.35


@dataclass
class Projection:
    mu: float
    interval_low: float
    interval_high: float
    over_under: OverUnder
    drivers: list[str] = field(default_factory=list)   # human-readable reasoning
    variance_used: float | None = None


def _form_factor(prop: Prop, base: float) -> tuple[float, str | None]:
    """Blend the most relevant recent-form mean toward the base rate.

    Uses L10 if present, else L5, else Season. Returns a multiplicative factor
    on the base rate and a note describing the adjustment.
    """
    by_window = {f.window.upper(): f for f in prop.form}
    chosen = by_window.get("L10") or by_window.get("L5") or by_window.get("SEASON")
    if not chosen or base <= 0:
        return 1.0, None
    ratio = chosen.mean / base
    # pull only part-way toward recent form
    factor = 1.0 + FORM_WEIGHT * (ratio - 1.0)
    note = f"recent form ({chosen.window} mean {chosen.mean:g} vs base {base:g}) -> x{factor:.3f}"
    return factor, note


def _opportunity_scale(prop: Prop) -> tuple[float, str | None]:
    """Scale by projected opportunity.

    Football: base_rate_per90 is scaled by expected_minutes / 90 (spec 35).
    Other sports: per_game_rate is used as-is unless an explicit opportunity
    metric is provided, in which case it scales linearly against a reference.
    """
    opp = prop.opportunity
    if prop.base_rate_per90 is not None:
        minutes = opp.expected if opp else 90.0
        scale = minutes / 90.0
        return scale, f"minutes gate {minutes:g}/90 -> x{scale:.3f}"
    return 1.0, None


def build_projection(prop: Prop) -> Projection:
    """Produce the central projection and score it against the market line."""
    drivers: list[str] = []

    # 1. base rate (long-term) ------------------------------------------------
    if prop.base_rate_per90 is not None:
        base = prop.base_rate_per90
        drivers.append(f"base rate {base:g} per 90'")
    elif prop.per_game_rate is not None:
        base = prop.per_game_rate
        drivers.append(f"base rate {base:g} per game")
    else:
        raise ValueError(
            f"Prop {prop.subject}/{prop.market}: no base_rate_per90 or per_game_rate — "
            "cannot project without a verified long-term rate"
        )

    mu = base

    # 2. opportunity scale ----------------------------------------------------
    scale, note = _opportunity_scale(prop)
    mu *= scale
    if note:
        drivers.append(note)

    # 3. recent-form nudge ----------------------------------------------------
    factor, note = _form_factor(prop, base)
    mu *= factor
    if note:
        drivers.append(note)

    # 4. matchup multiplier ---------------------------------------------------
    if prop.matchup_multiplier != 1.0:
        mu *= prop.matchup_multiplier
        drivers.append(
            f"matchup x{prop.matchup_multiplier:.3f}"
            + (f" ({prop.matchup_note})" if prop.matchup_note else "")
        )

    # 5. distribution & probability ------------------------------------------
    variance = prop.variance_hint
    if variance is None:
        # fall back to a recent-window variance if provided
        for f in prop.form:
            if f.variance is not None:
                variance = f.variance
                break

    ou = prob_over(
        prop.market_line.line,
        mu,
        variance=variance,
        kind=prop.distribution,
    )

    # plausible interval: +/- ~1 sd for continuous, else a count-based band
    if variance is not None and variance > 0:
        import math

        sd = math.sqrt(variance)
        low, high = max(0.0, mu - sd), mu + sd
    else:
        import math

        sd = math.sqrt(mu) if mu > 0 else 0.0  # Poisson sd
        low, high = max(0.0, mu - sd), mu + sd

    return Projection(
        mu=mu,
        interval_low=low,
        interval_high=high,
        over_under=ou,
        drivers=drivers,
        variance_used=variance,
    )


# --------------------------------------------------------------------------- #
# Sensitivity analysis (spec 28)
# --------------------------------------------------------------------------- #
@dataclass
class SensitivityRow:
    assumption: str
    value: float
    p_side: float


def minutes_sensitivity(prop: Prop, grid: list[float] | None = None) -> list[SensitivityRow]:
    """Vary expected minutes and recompute the chosen side's probability.

    Only meaningful for a per-90 football rate. Returns an empty list otherwise.
    """
    if prop.base_rate_per90 is None:
        return []
    grid = grid or [60.0, 70.0, 80.0, 90.0]
    rows: list[SensitivityRow] = []
    side_over = prop.side.lower() in ("over", "more")
    for minutes in grid:
        clone = _clone_with_minutes(prop, minutes)
        proj = build_projection(clone)
        p = proj.over_under.p_over if side_over else proj.over_under.p_under
        rows.append(SensitivityRow(assumption="expected_minutes", value=minutes, p_side=p))
    return rows


def _clone_with_minutes(prop: Prop, minutes: float) -> Prop:
    import copy

    clone = copy.deepcopy(prop)
    if clone.opportunity is None:
        from ..contracts import Opportunity

        clone.opportunity = Opportunity(metric="minutes", expected=minutes)
    else:
        clone.opportunity.expected = minutes
    return clone
