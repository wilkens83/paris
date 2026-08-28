"""Human-readable rendering of an analysis (spec 60-62).

The Synthesizer only reads verified data + engine outputs (spec 4.14). It never
adds a number that did not come from the pipeline.
"""

from __future__ import annotations

from .match_analysis import MatchBoard
from .pipeline import Analysis


_DECISION_EMOJI = {
    "STRONG VALUE": "🟢",
    "VALUE": "🟢",
    "LEAN": "🟡",
    "FAIR": "⚪",
    "AVOID": "🔴",
    "NO BET": "⛔",
    "WAIT": "⏳",
}


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def _sign(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:+.1f}pp"


def render_prop(a: Analysis) -> str:
    p = a.prop
    proj = a.projection
    emoji = _DECISION_EMOJI.get(a.decision, "")
    lines: list[str] = []
    lines.append(f"### {p.subject} — {p.market} {p.market_line.line:g} {p.side.upper()}")
    lines.append("")
    lines.append(f"**Decision:** {emoji} {a.decision}   **Grade:** {a.grade}")
    lines.append("")
    lines.append(f"- Projection: **{proj.mu:.2f}**  (interval {proj.interval_low:.1f}–{proj.interval_high:.1f})")
    lines.append(f"- P({p.side.upper()}): **{_pct(a.p_side)}**   "
                 f"[{proj.over_under.distribution}]"
                 + (f"   push {_pct(proj.over_under.p_push)}" if proj.over_under.p_push else ""))
    if a.price is not None:
        pr = a.price
        lines.append(f"- Market fair P: {_pct(pr.prob_market_fair)}   "
                     f"Edge: **{_sign(pr.edge_points)}**   EV: {pr.ev_per_unit:+.3f}u")
        lines.append(f"- Fair odds (model): {pr.fair_odds_model:+.0f}   "
                     f"Offered: {pr.market_odds:+.0f}"
                     + (f"   hold {_pct(pr.hold)}" if pr.hold is not None else ""))
    if a.pickem is not None:
        pk = a.pickem
        lines.append(f"- Pick'em: favours **{pk.side}**  P={_pct(pk.p_side)}   "
                     f"edge_abs {pk.edge_abs:+.2f}  edge_rel {pk.edge_rel:+.1%}")
        if a.breakeven is not None:
            lines.append(f"- 2-leg break-even (independent ref): {_pct(a.breakeven)}")

    # data status / gate
    gate = a.gate
    status = "PASS" if gate.passed else gate.verdict
    lines.append(f"- Quality Gate: **{status}**"
                 + (f"  — {'; '.join(gate.reasons)}" if gate.reasons else ""))

    if proj.drivers:
        lines.append(f"- Drivers: {'; '.join(proj.drivers)}")

    if a.sensitivity:
        cells = "  ".join(f"{r.value:g}'→{_pct(r.p_side)}" for r in a.sensitivity)
        lines.append(f"- Sensitivity (minutes): {cells}")

    # adversarial
    if a.reasons_for:
        lines.append(f"- ✅ For: {'; '.join(a.reasons_for)}")
    if a.reasons_against:
        lines.append(f"- ⚠️  Against: {'; '.join(a.reasons_against)}")
    if a.invalidation:
        lines.append(f"- ⛔ Invalidation: {a.invalidation}")
    if p.sources:
        lines.append(f"- Sources: {', '.join(p.sources)}")
    lines.append("")
    return "\n".join(lines)


def _bucket(title: str, items: list[Analysis]) -> str:
    if not items:
        return ""
    out = [f"## {title}", ""]
    for a in items:
        out.append(render_prop(a))
    return "\n".join(out)


def render_board(board: MatchBoard) -> str:
    ev = board.request.event
    out: list[str] = []
    out.append(f"# 🎯 MATCH ANALYSIS — {ev.label}")
    out.append("")
    out.append(f"**Competition:** {ev.competition}   **Date:** {ev.date}"
               + (f"   **Venue:** {ev.venue}" if ev.venue else ""))
    out.append(f"**Sport:** {ev.sport}   **Props screened:** {len(board.analyses)}")
    out.append("")
    out.append("> The system's goal is never to force a bet. NO BET / WAIT is a valid "
               "outcome when the edge is not robust (spec 0).")
    out.append("")

    # one-line ranked summary
    out.append("## Board summary")
    out.append("")
    out.append("| Rank | Subject | Market | Line | Side | P(side) | Edge | Grade | Decision |")
    out.append("|---:|---|---|---:|---|---:|---:|---|---|")
    for i, a in enumerate(board.analyses, 1):
        p = a.prop
        out.append(
            f"| {i} | {p.subject} | {p.market} | {p.market_line.line:g} | {p.side.upper()} | "
            f"{_pct(a.p_side)} | {_sign(a.edge_points)} | {a.grade} | {a.decision} |"
        )
    out.append("")

    for title, items in [
        ("🟢 BEST BETS", board.best_bets),
        ("🟢 SECONDARY VALUE", board.secondary),
        ("🟡 LEANS", board.leans),
        ("⏳ WAIT", board.wait),
        ("🔴 AVOID", board.avoid),
        ("⛔ NO BET / FAIR", board.no_bet),
    ]:
        section = _bucket(title, items)
        if section:
            out.append(section)

    return "\n".join(out)
