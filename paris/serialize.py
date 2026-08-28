"""Normalized (JSON-friendly) views of engine outputs (plan section 31).

The UI, the storage layer and any future FastAPI response all need the same
flat, serializable view of an ``Analysis``. Centralizing it here keeps that
shape in one place and out of the frontend — the frontend must never recompute
numbers (plan section 2 / 39).
"""

from __future__ import annotations

from typing import Any

from .pipeline import Analysis

__version__ = "1.0.0"
MODEL_VERSION = f"paris-{__version__}"


def analysis_to_record(analysis: Analysis, *, event=None, analysis_id: str | None = None) -> dict[str, Any]:
    """Flatten an Analysis into the normalized record used everywhere downstream.

    ``event`` (a contracts.Event) is optional context so a stored record knows
    which match it belongs to.
    """
    p = analysis.prop
    proj = analysis.projection
    ou = proj.over_under

    record: dict[str, Any] = {
        "analysis_id": analysis_id,
        "model_version": MODEL_VERSION,
        # entity
        "sport": getattr(event, "sport", ""),
        "event": getattr(event, "label", ""),
        "subject": p.subject,
        "market": p.market,
        "line": p.market_line.line,
        "side": p.side,
        # projection / distribution
        "projection": round(proj.mu, 4),
        "interval": [round(proj.interval_low, 4), round(proj.interval_high, 4)],
        "distribution": ou.distribution,
        "probabilities": {
            "over": round(ou.p_over, 6),
            "under": round(ou.p_under, 6),
            "push": round(ou.p_push, 6),
        },
        "p_side": round(analysis.p_side, 6),
        # decision
        "grade": analysis.grade,
        "decision": analysis.decision,
        # quality gate
        "quality_gate": {
            "status": analysis.gate.verdict,
            "passed": analysis.gate.passed,
            "checks": dict(analysis.gate.checks),
            "reasons": list(analysis.gate.reasons),
        },
        # opportunity
        "opportunity_metric": (p.opportunity.metric if p.opportunity else None),
        "opportunity_expected": (p.opportunity.expected if p.opportunity else None),
        "opportunity_certainty": (p.opportunity.certainty if p.opportunity else None),
        # verification
        "verified": p.verified,
        "sources": list(p.sources),
        # adversarial
        "reasons_for": list(analysis.reasons_for),
        "reasons_against": list(analysis.reasons_against),
        "invalidation": analysis.invalidation,
        "drivers": list(proj.drivers),
        # sensitivity
        "sensitivity": [
            {"assumption": r.assumption, "value": r.value, "p_side": round(r.p_side, 6)}
            for r in analysis.sensitivity
        ],
    }

    # market comparison — sportsbook or pick'em
    if analysis.price is not None:
        pr = analysis.price
        record["market"] = record["market"]  # keep market name
        record["market_math"] = {
            "type": "sportsbook",
            "fair_probability": round(pr.prob_market_fair, 6),
            "model_probability": round(pr.prob_model, 6),
            "edge_points": round(pr.edge_points, 6),
            "edge_relative": round(pr.edge_relative, 6),
            "fair_odds": round(pr.fair_odds_model, 1),
            "offered_odds": pr.market_odds,
            "ev_per_unit": round(pr.ev_per_unit, 6),
            "hold": (round(pr.hold, 6) if pr.hold is not None else None),
            "book": p.market_line.book,
            "timestamp": p.market_line.timestamp,
        }
    elif analysis.pickem is not None:
        pk = analysis.pickem
        record["market_math"] = {
            "type": "pickem",
            "p_more": round(pk.p_more, 6),
            "p_less": round(pk.p_less, 6),
            "favored_side": pk.side,
            "p_side": round(pk.p_side, 6),
            "edge_abs": round(pk.edge_abs, 4),
            "edge_relative": round(pk.edge_rel, 6),
            "breakeven": (round(analysis.breakeven, 6) if analysis.breakeven is not None else None),
            "book": p.market_line.book,
            "timestamp": p.market_line.timestamp,
        }
    else:
        record["market_math"] = None

    record["edge_points"] = round(analysis.edge_points, 6)
    record["ev_per_unit"] = (round(analysis.ev, 6) if analysis.ev is not None else None)
    return record


def sensitivity_threshold(analysis: Analysis, target: float = 0.5) -> float | None:
    """Interpolate the assumption value where P(side) crosses ``target``.

    Answers the plan's "model stops being value below N minutes" (section 11).
    Returns None when the grid never crosses the target.
    """
    rows = analysis.sensitivity
    if len(rows) < 2:
        return None
    for a, b in zip(rows, rows[1:]):
        lo, hi = (a, b) if a.p_side <= b.p_side else (b, a)
        if lo.p_side <= target <= hi.p_side and hi.p_side != lo.p_side:
            frac = (target - lo.p_side) / (hi.p_side - lo.p_side)
            return round(lo.value + frac * (hi.value - lo.value), 2)
    return None
