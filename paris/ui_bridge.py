"""UI bridge — turn raw form input into engine contracts (plan 5-8, 33, 37).

The Streamlit frontend collects strings and numbers from widgets; this module
is the single, testable place that assembles them into ``Event``, ``Prop`` and
``MatchRequest`` objects and runs the engine. No numbers are computed here — it
only marshals input and delegates to ``analyze_match`` / ``analyze_prop``.
"""

from __future__ import annotations

from typing import Any

from .contracts import Event, MatchRequest, Prop
from .match_analysis import MatchBoard, analyze_match
from .pipeline import Analysis, analyze_prop

MARKETS = [
    "shots", "shots_on_target", "passes", "tackles", "clearances",
    "assists", "goals", "saves", "interceptions", "fouls", "cards",
]
DISTRIBUTIONS = ["auto", "poisson", "negbin", "normal"]
SIDES = ["over", "under", "more", "less"]
CERTAINTY = ["A", "B", "C", "D"]
OPPORTUNITY_METRICS = ["minutes", "plate_appearances", "innings", "snaps", "routes", "toi", "possessions"]


def _num(v: Any) -> float | None:
    """Blank/None -> None, otherwise float. Empty strings become None."""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        if v == "":
            return None
        return float(v)
    return float(v)


def _clean_list(items: Any) -> list[str]:
    """Split a newline/comma list or pass through an existing list, dropping blanks."""
    if not items:
        return []
    if isinstance(items, str):
        parts = [p.strip() for chunk in items.splitlines() for p in chunk.split(",")]
        return [p for p in parts if p]
    return [str(i).strip() for i in items if str(i).strip()]


def form_rows_to_dicts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert recent-form table rows (L5/L10/L20/Season) into FormWindow dicts.

    A row with no window label or no mean is skipped — the table editor always
    ships four blank rows.
    """
    out: list[dict[str, Any]] = []
    for row in rows or []:
        window = (row.get("window") or row.get("Window") or "").strip()
        mean = _num(row.get("mean", row.get("Mean")))
        if not window or mean is None:
            continue
        out.append({
            "window": window,
            "mean": mean,
            "median": _num(row.get("median", row.get("Median"))),
            "stdev": _num(row.get("stdev", row.get("SD"))),
            "min": _num(row.get("min", row.get("Min"))),
            "max": _num(row.get("max", row.get("Max"))),
            "hit_rate_over": _num(row.get("hit_rate_over", row.get("Historical Hit Rate"))),
        })
    return out


def build_event(data: dict[str, Any]) -> Event:
    return Event.from_dict({
        "sport": data.get("sport", "football"),
        "competition": data.get("competition", ""),
        "home": data["home"],
        "away": data["away"],
        "date": data.get("date", ""),
        "venue": data.get("venue", ""),
        "kickoff": data.get("kickoff", ""),
    })


def build_prop(data: dict[str, Any]) -> Prop:
    """Assemble a Prop from a flat UI dict. Raises ValueError on missing basics."""
    subject = (data.get("subject") or "").strip()
    if not subject:
        raise ValueError("prop requires a subject/player name")
    line = _num(data.get("line"))
    if line is None:
        raise ValueError(f"prop '{subject}' requires a market line")

    market_line = {
        "line": line,
        "over_odds": _num(data.get("over_odds")),
        "under_odds": _num(data.get("under_odds")),
        "book": (data.get("book") or "").strip(),
        "timestamp": (data.get("timestamp") or "").strip(),
        "payout_multiplier": _num(data.get("payout_multiplier")),
    }

    opportunity = None
    if data.get("expected") not in (None, ""):
        opportunity = {
            "metric": data.get("opportunity_metric", "minutes"),
            "expected": _num(data.get("expected")),
            "low": _num(data.get("low")),
            "high": _num(data.get("high")),
            "certainty": data.get("certainty", "C"),
            "starter_prob": _num(data.get("starter_prob")),
            "notes": (data.get("opportunity_notes") or "").strip(),
        }

    prop_dict = {
        "subject": subject,
        "market": data.get("market", "shots"),
        "side": data.get("side", "over"),
        "market_line": market_line,
        "distribution": data.get("distribution", "auto"),
        "base_rate_per90": _num(data.get("base_rate_per90")),
        "per_game_rate": _num(data.get("per_game_rate")),
        "form": data.get("form") or form_rows_to_dicts(data.get("form_rows", [])),
        "opportunity": opportunity,
        "matchup_multiplier": _num(data.get("matchup_multiplier")) or 1.0,
        "matchup_note": (data.get("matchup_note") or "").strip(),
        "variance_hint": _num(data.get("variance_hint")),
        "verified": bool(data.get("verified", False)),
        "sources": _clean_list(data.get("sources")),
        "reasons_for": _clean_list(data.get("reasons_for")),
        "reasons_against": _clean_list(data.get("reasons_against")),
        "invalidation": (data.get("invalidation") or "").strip(),
    }
    return Prop.from_dict(prop_dict)


def build_match_request(event_data: dict[str, Any], prop_dicts: list[dict[str, Any]]) -> MatchRequest:
    event = build_event(event_data)
    props = [build_prop(p) for p in prop_dicts]
    return MatchRequest(event=event, props=props)


def run_match(event_data: dict[str, Any], prop_dicts: list[dict[str, Any]]) -> MatchBoard:
    return analyze_match(build_match_request(event_data, prop_dicts))


def run_single_prop(data: dict[str, Any]) -> Analysis:
    return analyze_prop(build_prop(data))
