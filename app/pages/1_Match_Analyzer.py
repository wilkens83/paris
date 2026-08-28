"""Match Analyzer — the first fully functional page (plan sections 5-9, 37)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # app/ importable

from components.board import render_board          # noqa: E402
from components.prop_form import prop_builder_form  # noqa: E402
from state import ensure_prop_list, get_store, page_header  # noqa: E402

from paris.ui_bridge import run_match               # noqa: E402
from paris.providers import load_match              # noqa: E402

st.set_page_config(page_title="Match Analyzer · PARIS", page_icon="🎯", layout="wide")
page_header("Match Analyzer", "Build a match, add props, run the engine.")

props = ensure_prop_list("props")

# ------------------------------------------------------------------ event ---
st.header("1 · Event")
e1, e2, e3 = st.columns(3)
sport = e1.text_input("Sport", value="football")
competition = e2.text_input("Competition", value="La Liga")
venue = e3.text_input("Venue", value="")
e4, e5, e6 = st.columns(3)
home = e4.text_input("Home team", value="Real Madrid")
away = e5.text_input("Away team", value="Barcelona")
date = e6.text_input("Date (YYYY-MM-DD)", value="")
kickoff = st.text_input("Kickoff (ISO timestamp, optional)", value="")

event_data = {
    "sport": sport, "competition": competition, "home": home, "away": away,
    "date": date, "venue": venue, "kickoff": kickoff,
}

# demo loader
with st.expander("Load the bundled demo match instead"):
    if st.button("Load Real Madrid vs Barcelona demo"):
        demo = Path(__file__).resolve().parents[2] / "examples" / "real_madrid_vs_barcelona.json"
        req = load_match(demo)
        st.session_state["props"] = [
            {
                "subject": p.subject, "market": p.market, "side": p.side,
                "line": p.market_line.line, "over_odds": p.market_line.over_odds,
                "under_odds": p.market_line.under_odds, "book": p.market_line.book,
                "payout_multiplier": p.market_line.payout_multiplier,
                "distribution": p.distribution, "base_rate_per90": p.base_rate_per90,
                "per_game_rate": p.per_game_rate, "variance_hint": p.variance_hint,
                "matchup_multiplier": p.matchup_multiplier, "matchup_note": p.matchup_note,
                "opportunity_metric": (p.opportunity.metric if p.opportunity else "minutes"),
                "expected": (p.opportunity.expected if p.opportunity else None),
                "low": (p.opportunity.low if p.opportunity else None),
                "high": (p.opportunity.high if p.opportunity else None),
                "certainty": (p.opportunity.certainty if p.opportunity else "C"),
                "starter_prob": (p.opportunity.starter_prob if p.opportunity else None),
                "form": [f.__dict__ for f in p.form],
                "verified": p.verified, "sources": p.sources,
                "reasons_for": p.reasons_for, "reasons_against": p.reasons_against,
                "invalidation": p.invalidation,
            }
            for p in req.props
        ]
        st.session_state.update({
            "_demo_event": {
                "sport": req.event.sport, "competition": req.event.competition,
                "home": req.event.home, "away": req.event.away, "date": req.event.date,
                "venue": req.event.venue, "kickoff": req.event.kickoff,
            }
        })
        st.success(f"Loaded {len(req.props)} demo props. Scroll down to analyze.")
        st.rerun()

if "_demo_event" in st.session_state:
    event_data = st.session_state["_demo_event"]

# ------------------------------------------------------------------ props ---
st.header("2 · Props")
st.caption(f"{len(props)} prop(s) staged.")
new_prop = prop_builder_form("match")
if new_prop is not None:
    props.append(new_prop)
    st.success(f"Added {new_prop['subject']} — {new_prop['market']}.")

if props:
    st.subheader("Staged props")
    for i, p in enumerate(props):
        cols = st.columns([6, 1])
        cols[0].write(f"**{p['subject']}** · {p['market']} {p['line']} {p['side'].upper()}")
        if cols[1].button("Remove", key=f"rm_{i}"):
            props.pop(i)
            st.rerun()
    if st.button("Clear all props"):
        st.session_state["props"] = []
        st.rerun()

# ---------------------------------------------------------------- analyze ---
st.header("3 · Analyze")
if st.button("🎯 ANALYZE MATCH", type="primary", disabled=not props):
    try:
        board = run_match(event_data, props)
    except Exception as exc:  # surface contract errors cleanly
        st.error(f"Could not analyze: {exc}")
    else:
        st.session_state["last_board"] = board
        render_board(board)
        if st.button("💾 Save all to database"):
            ids = get_store().save_board(board)
            st.success(f"Saved {len(ids)} analyses.")
elif "last_board" in st.session_state:
    st.info("Showing the last board (edit props and re-analyze to refresh).")
    render_board(st.session_state["last_board"])
