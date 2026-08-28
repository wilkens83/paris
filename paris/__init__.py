"""paris — a disciplined sports-betting decision-support system.

Implements the "Système Maître" master spec: an agentic pipeline that turns a
match analysis request into ranked, gated, honestly-priced decisions — and is
happy to answer NO BET.

Primary entry point (MODE B — Match Analysis):

    from paris import analyze_match, load_match, render_board

    board = analyze_match(load_match("examples/real_madrid_vs_barcelona.json"))
    print(render_board(board))
"""

from .contracts import Event, MarketLine, MatchRequest, Prop
from .match_analysis import MatchBoard, analyze_match
from .pipeline import Analysis, analyze_prop
from .providers import load_match
from .report import render_board, render_prop

__version__ = "1.0.0"

__all__ = [
    "Event",
    "Prop",
    "MarketLine",
    "MatchRequest",
    "Analysis",
    "MatchBoard",
    "analyze_prop",
    "analyze_match",
    "load_match",
    "render_board",
    "render_prop",
]
