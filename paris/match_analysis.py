"""MODE B — Match Analysis orchestrator (spec 15 MODE B, 62, 66).

Takes a resolved match plus a set of props, runs the single-market pipeline on
each, ranks them by decision quality and buckets them into the final board:

    BEST BETS / SECONDARY VALUE / LEANS / AVOID / WAIT / NO BET

This is the "ask for a match analysis" core. It does not fetch live data — the
provider supplies verified numbers (spec 64) — it turns them into disciplined,
ranked decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import MatchRequest
from .pipeline import Analysis, analyze_prop


# Ordering for ranking: strongest decision first, then by edge magnitude.
_DECISION_RANK = {
    "STRONG VALUE": 0,
    "VALUE": 1,
    "LEAN": 2,
    "FAIR": 3,
    "WAIT": 4,
    "AVOID": 5,
    "NO BET": 6,
}

_BUCKET = {
    "STRONG VALUE": "best_bets",
    "VALUE": "best_bets",
    "LEAN": "leans",
    "FAIR": "no_bet",
    "AVOID": "avoid",
    "WAIT": "wait",
    "NO BET": "no_bet",
}


@dataclass
class MatchBoard:
    request: MatchRequest
    analyses: list[Analysis] = field(default_factory=list)
    best_bets: list[Analysis] = field(default_factory=list)
    secondary: list[Analysis] = field(default_factory=list)
    leans: list[Analysis] = field(default_factory=list)
    avoid: list[Analysis] = field(default_factory=list)
    wait: list[Analysis] = field(default_factory=list)
    no_bet: list[Analysis] = field(default_factory=list)


def _sort_key(a: Analysis):
    return (_DECISION_RANK.get(a.decision, 9), -abs(a.edge_points))


def analyze_match(request: MatchRequest) -> MatchBoard:
    analyses = [analyze_prop(p) for p in request.props]
    analyses.sort(key=_sort_key)

    board = MatchBoard(request=request, analyses=analyses)
    for a in analyses:
        bucket = _BUCKET.get(a.decision, "no_bet")
        getattr(board, bucket).append(a)

    # split BEST BETS into strong (A/A+ grade) vs secondary value
    strong, secondary = [], []
    for a in board.best_bets:
        (strong if a.grade in ("A+", "A") else secondary).append(a)
    board.best_bets = strong
    board.secondary = secondary
    return board
