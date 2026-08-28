"""Match board summary table + bucketed sections (plan section 8)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from paris.match_analysis import MatchBoard
from paris.pipeline import Analysis

from .prop_card import render_prop_detail

_EMOJI = {
    "STRONG VALUE": "🟢", "VALUE": "🟢", "LEAN": "🟡",
    "FAIR": "⚪", "AVOID": "🔴", "NO BET": "⛔", "WAIT": "⏳",
}


def _row(rank: int, a: Analysis) -> dict:
    p = a.prop
    return {
        "Rank": rank,
        "Player": p.subject,
        "Market": p.market,
        "Line": p.market_line.line,
        "Side": p.side.upper(),
        "Model P": f"{a.p_side*100:.1f}%",
        "Edge": f"{a.edge_points*100:+.1f}pp",
        "EV": (f"{a.ev:+.3f}" if a.ev is not None else "—"),
        "Grade": a.grade,
        "Decision": a.decision,
    }


def render_board_summary(board: MatchBoard) -> None:
    if not board.analyses:
        st.info("No props analyzed yet.")
        return
    df = pd.DataFrame([_row(i, a) for i, a in enumerate(board.analyses, 1)])
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_board(board: MatchBoard, expand_details: bool = True) -> None:
    ev = board.request.event
    st.markdown(f"# 🎯 {ev.label}")
    st.caption(f"{ev.competition} · {ev.date} · {ev.sport}"
               + (f" · {ev.venue}" if ev.venue else ""))

    # summary metrics (plan section 4)
    value = len(board.best_bets) + len(board.secondary)
    cols = st.columns(5)
    cols[0].metric("Props", len(board.analyses))
    cols[1].metric("Value candidates", value)
    cols[2].metric("Leans", len(board.leans))
    cols[3].metric("WAIT", len(board.wait))
    cols[4].metric("NO BET / Avoid", len(board.no_bet) + len(board.avoid))

    st.subheader("Board summary")
    render_board_summary(board)

    sections = [
        ("🟢 BEST BETS", board.best_bets),
        ("🟢 SECONDARY VALUE", board.secondary),
        ("🟡 LEANS", board.leans),
        ("⏳ WAIT", board.wait),
        ("🔴 AVOID", board.avoid),
        ("⛔ NO BET / FAIR", board.no_bet),
    ]
    for title, items in sections:
        if not items:
            continue
        st.markdown(f"## {title}")
        for a in items:
            label = f"{_EMOJI.get(a.decision,'')} {a.prop.subject} — {a.prop.market} " \
                    f"{a.prop.market_line.line:g} {a.prop.side.upper()}  ·  {a.grade}"
            with st.expander(label, expanded=(expand_details and title.endswith("BEST BETS"))):
                render_prop_detail(a)
