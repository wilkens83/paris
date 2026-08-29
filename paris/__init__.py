"""paris — a production sports-betting decision-support system.

Real data → automatic feature derivation → verification → quantitative model →
probability → market math → edge/EV → quality gate → decision. The system never
fabricates data: when a required live source is missing it says so and stops the
affected analysis (see PRODUCTION LIVE-DATA POLICY in the docs).

Production analysis path:

    from paris.orchestrator import analyze_market   # derive → verify → analyze
    from paris.providers import ApiFootballProvider, SportsGameOddsProvider

The quantitative core (``analyze_match``/``analyze_prop``) is preserved and only
ever consumes normalized, derived inputs. ``load_match`` is retained for
tests/offline use only, not the production workflow.
"""

from .assemble import assemble_prop
from .contracts import Event, MarketLine, MatchRequest, Prop
from .match_analysis import MatchBoard, analyze_match
from .orchestrator import OrchestratedAnalysis, analyze_market
from .pipeline import Analysis, analyze_prop
from .providers import load_match
from .report import render_board, render_prop
from .serialize import analysis_to_record

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
    "analyze_market",
    "assemble_prop",
    "OrchestratedAnalysis",
    "load_match",
    "render_board",
    "render_prop",
    "analysis_to_record",
]
