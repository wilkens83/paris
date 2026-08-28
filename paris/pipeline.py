"""Single-market pipeline + Quality Gate, grading and decision (spec 5, 28-33).

This is the deterministic execution graph for one prop:

    verified data -> projection -> distribution -> probability
        -> market math -> edge / EV -> sensitivity -> adversarial
        -> QUALITY GATE -> grade -> decision

The gate can (and often should) return NO BET / WAIT. Forcing a pick is
forbidden (spec 64.13).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import Prop
from .engines import market_math
from .engines.prizepicks import PickEmAssessment, assess_pickem, entry_breakeven
from .engines.projection import (
    Projection,
    SensitivityRow,
    build_projection,
    minutes_sensitivity,
)


# Decision thresholds, expressed in probability-points of edge over the fair
# market price. Tunable, and deliberately conservative — the system's job is not
# to find a bet (spec 0).
STRONG_EDGE = 0.06
VALUE_EDGE = 0.035
LEAN_EDGE = 0.015


@dataclass
class GateResult:
    passed: bool
    verdict: str                    # "PASS", "NO BET", or "WAIT"
    checks: dict[str, bool] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


@dataclass
class Analysis:
    prop: Prop
    projection: Projection
    gate: GateResult
    # market comparison (one of these two, depending on market type)
    price: market_math.PriceAssessment | None = None
    pickem: PickEmAssessment | None = None
    breakeven: float | None = None
    sensitivity: list[SensitivityRow] = field(default_factory=list)
    grade: str = "F"
    decision: str = "NO BET"
    reasons_for: list[str] = field(default_factory=list)
    reasons_against: list[str] = field(default_factory=list)
    invalidation: str = ""

    @property
    def p_side(self) -> float:
        over = self.prop.side.lower() in ("over", "more")
        return self.projection.over_under.p_over if over else self.projection.over_under.p_under

    @property
    def edge_points(self) -> float:
        if self.price is not None:
            return self.price.edge_points
        if self.pickem is not None:
            # vs implied 50/50 pick'em break-even when no explicit price
            be = self.breakeven if self.breakeven is not None else 0.5
            return self.pickem.p_side - be
        return 0.0

    @property
    def ev(self) -> float | None:
        return self.price.ev_per_unit if self.price is not None else None


# --------------------------------------------------------------------------- #
# Quality Gate (spec 30)
# --------------------------------------------------------------------------- #
def run_quality_gate(prop: Prop, projection: Projection) -> GateResult:
    checks: dict[str, bool] = {}
    reasons: list[str] = []

    checks["entity_verified"] = prop.verified
    if not prop.verified:
        reasons.append("critical data not verified by an independent check")

    has_base = prop.base_rate_per90 is not None or prop.per_game_rate is not None
    checks["data_sufficient"] = has_base and bool(prop.form)
    if not checks["data_sufficient"]:
        reasons.append("insufficient data (missing base rate or recent form)")

    checks["line_present"] = prop.market_line.line is not None
    checks["model_completed"] = projection is not None

    # opportunity / role certainty (spec 4.8, 37)
    opp = prop.opportunity
    certainty = (opp.certainty.upper() if opp else "D")
    checks["opportunity_certain"] = certainty in ("A", "B")
    if not checks["opportunity_certain"]:
        reasons.append(f"opportunity/role certainty is {certainty} (want A or B for a strong edge)")

    checks["uncertainty_estimated"] = projection.interval_high > projection.interval_low

    # WAIT beats NO BET when the only failure is an imminent lineup/role datum
    critical_fail = not (checks["entity_verified"] and checks["data_sufficient"]
                         and checks["line_present"] and checks["model_completed"])
    if critical_fail:
        return GateResult(passed=False, verdict="NO BET", checks=checks, reasons=reasons)
    if not checks["opportunity_certain"] and certainty in ("C", "D"):
        return GateResult(passed=False, verdict="WAIT", checks=checks, reasons=reasons)
    return GateResult(passed=True, verdict="PASS", checks=checks, reasons=reasons)


# --------------------------------------------------------------------------- #
# Grade (spec 31) & decision category (spec 33)
# --------------------------------------------------------------------------- #
def _grade(edge_points: float, gate: GateResult, robust: bool) -> str:
    if not gate.passed:
        return "D"
    e = abs(edge_points)
    if e >= STRONG_EDGE and robust:
        return "A+" if e >= STRONG_EDGE * 1.6 else "A"
    if e >= VALUE_EDGE:
        return "B+" if robust else "B"
    if e >= LEAN_EDGE:
        return "C"
    return "D"


def _decision(edge_points: float, gate: GateResult, robust: bool) -> str:
    if gate.verdict == "WAIT":
        return "WAIT"
    if not gate.passed:
        return "NO BET"
    e = edge_points
    if e >= STRONG_EDGE and robust:
        return "STRONG VALUE"
    if e >= VALUE_EDGE:
        return "VALUE"
    if e >= LEAN_EDGE:
        return "LEAN"
    if e <= -VALUE_EDGE:
        return "AVOID"
    return "FAIR"


def _is_robust(sensitivity: list[SensitivityRow], side_over: bool) -> bool:
    """The edge survives the fragile-assumption test (spec 28).

    Robust when the probability stays on the profitable side of 50% across the
    plausible middle of the sensitivity grid.
    """
    if not sensitivity:
        return True  # nothing fragile identified to test
    mids = sensitivity[1:-1] or sensitivity
    return all(r.p_side >= 0.5 for r in mids)


# --------------------------------------------------------------------------- #
# Adversarial / contrarian check (spec 29)
# --------------------------------------------------------------------------- #
def _adversarial(prop: Prop, projection: Projection) -> tuple[list[str], list[str], str]:
    over = prop.side.lower() in ("over", "more")
    reasons_for = list(prop.reasons_for)
    reasons_against = list(prop.reasons_against)

    # derive structural risks when none were supplied
    if not reasons_for:
        reasons_for.extend(projection.drivers[:2])
    if not reasons_against:
        opp = prop.opportunity
        if opp and opp.certainty.upper() in ("C", "D"):
            reasons_against.append("opportunity/role not yet certain — volume could collapse")
        if prop.matchup_multiplier < 1.0 and over:
            reasons_against.append("matchup suppresses this stat")
        if prop.matchup_multiplier > 1.0 and not over:
            reasons_against.append("matchup inflates this stat")
        margin = abs(projection.mu - prop.market_line.line)
        if margin < 0.5:
            reasons_against.append("projection sits very close to the line — low margin")

    invalidation = prop.invalidation
    if not invalidation:
        opp = prop.opportunity
        if opp and opp.metric == "minutes":
            invalidation = "benched / early substitution / role change at official lineup"
        else:
            invalidation = "official lineup or role change vs the projected setup"
    return reasons_for, reasons_against, invalidation


# --------------------------------------------------------------------------- #
# Orchestration for a single prop
# --------------------------------------------------------------------------- #
def analyze_prop(prop: Prop) -> Analysis:
    projection = build_projection(prop)
    gate = run_quality_gate(prop, projection)

    side_over = prop.side.lower() in ("over", "more")
    p_side = projection.over_under.p_over if side_over else projection.over_under.p_under

    price = None
    pickem = None
    breakeven = None
    line = prop.market_line

    if line.is_pickem:
        p_more = projection.over_under.p_over
        pickem = assess_pickem(line.line, projection.mu, p_more)
        if line.payout_multiplier:
            # 2-leg reference break-even; real entries depend on card size (spec 27)
            breakeven = entry_breakeven(2, line.payout_multiplier)
    else:
        price = market_math.assess_price(
            prob_model=p_side,
            market_odds=(line.over_odds if side_over else line.under_odds),
            over_odds=line.over_odds,
            under_odds=line.under_odds,
            side=prop.side,
        )

    sensitivity = minutes_sensitivity(prop)
    robust = _is_robust(sensitivity, side_over)

    analysis = Analysis(
        prop=prop,
        projection=projection,
        gate=gate,
        price=price,
        pickem=pickem,
        breakeven=breakeven,
        sensitivity=sensitivity,
    )

    edge_points = analysis.edge_points
    analysis.grade = _grade(edge_points, gate, robust)
    analysis.decision = _decision(edge_points, gate, robust)
    analysis.reasons_for, analysis.reasons_against, analysis.invalidation = _adversarial(
        prop, projection
    )
    return analysis
