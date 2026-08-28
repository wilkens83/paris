"""Prop detail card: projection, market, quality, adversarial (plan 9, 12)."""

from __future__ import annotations

import streamlit as st

from paris.pipeline import Analysis

from .quality_gate import render_quality_gate
from .sensitivity import render_sensitivity

_EMOJI = {
    "STRONG VALUE": "🟢", "VALUE": "🟢", "LEAN": "🟡",
    "FAIR": "⚪", "AVOID": "🔴", "NO BET": "⛔", "WAIT": "⏳",
}


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x*100:.1f}%"


def render_prop_detail(analysis: Analysis) -> None:
    p = analysis.prop
    proj = analysis.projection
    ou = proj.over_under
    emoji = _EMOJI.get(analysis.decision, "")

    st.markdown(f"## {p.subject} — {p.market} {p.market_line.line:g} {p.side.upper()}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Decision", f"{emoji} {analysis.decision}")
    c2.metric("Grade", analysis.grade)
    c3.metric(f"P({p.side.upper()})", _pct(analysis.p_side))

    # projection
    st.subheader("Projection")
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("Central", f"{proj.mu:.2f}")
    pc2.metric("Interval", f"{proj.interval_low:.1f}–{proj.interval_high:.1f}")
    pc3.metric("Distribution", ou.distribution)
    pp1, pp2, pp3 = st.columns(3)
    pp1.metric("P(Over)", _pct(ou.p_over))
    pp2.metric("P(Under)", _pct(ou.p_under))
    pp3.metric("P(Push)", _pct(ou.p_push))
    if proj.drivers:
        st.caption("Drivers: " + "; ".join(proj.drivers))

    # market
    st.subheader("Market")
    if analysis.price is not None:
        pr = analysis.price
        m = st.columns(3)
        m[0].metric("Model P", _pct(pr.prob_model))
        m[1].metric("Market fair P", _pct(pr.prob_market_fair))
        m[2].metric("Edge", f"{pr.edge_points*100:+.1f}pp")
        m2 = st.columns(3)
        m2[0].metric("Fair odds (model)", f"{pr.fair_odds_model:+.0f}")
        m2[1].metric("Offered odds", f"{pr.market_odds:+.0f}")
        m2[2].metric("EV / unit", f"{pr.ev_per_unit:+.3f}")
        if pr.hold is not None:
            st.caption(f"Book hold: {_pct(pr.hold)}  ·  {p.market_line.book or 'book'} "
                       f"@ {p.market_line.timestamp or 'no timestamp'}")
    elif analysis.pickem is not None:
        pk = analysis.pickem
        m = st.columns(3)
        m[0].metric("Favored", pk.side)
        m[1].metric("P(MORE)", _pct(pk.p_more))
        m[2].metric("P(LESS)", _pct(pk.p_less))
        st.caption(f"edge_abs {pk.edge_abs:+.2f} · edge_rel {pk.edge_rel:+.1%}"
                   + (f" · 2-leg break-even {_pct(analysis.breakeven)}" if analysis.breakeven else ""))

    render_quality_gate(analysis)
    render_sensitivity(analysis)

    # adversarial (plan 12)
    st.subheader("Adversarial check")
    ac1, ac2 = st.columns(2)
    with ac1:
        st.markdown("**Why the model likes it**")
        for r in (analysis.reasons_for or ["—"]):
            st.markdown(f"- {r}")
    with ac2:
        st.markdown("**Why it can fail**")
        for r in (analysis.reasons_against or ["—"]):
            st.markdown(f"- {r}")
    if analysis.invalidation:
        st.error(f"Invalidation: {analysis.invalidation}")
    if p.sources:
        st.caption("Sources: " + ", ".join(p.sources))
