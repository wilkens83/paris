"""PARIS — Today's Events home (directive 14, 25, 30).

Loads real current events from configured providers. No demo fallback: if a
live source is not configured, the honest state is shown with setup guidance.
"""

from __future__ import annotations

import streamlit as st

from live import config_status, fetch_today_events, freshness_label, render_status_banner
from state import get_store, page_header

st.set_page_config(page_title="PARIS", page_icon="🎯", layout="wide")

page_header(
    "🎯 PARIS — Live Sports-Betting Analytics",
    "Real events → real props → automatic features → verification → quantitative "
    "model → edge / EV → decision.",
)

cfg = config_status()
if cfg["missing"]:
    st.subheader("Configuration")
    st.error("🔌 Live data is not fully configured.")
    cols = st.columns(2)
    cols[0].metric("API-Football", "configured" if cfg["api_football"] else "NOT CONFIGURED")
    cols[1].metric("SportsGameOdds", "configured" if cfg["sportsgameodds"] else "NOT CONFIGURED")
    st.markdown(
        "PARIS is a **live-data product**. It does not ship demo matches. Set the "
        "missing credentials to load real events:\n\n"
        f"`{'`, `'.join(cfg['missing'])}`\n\n"
        "Copy `.env.example` to `.env`, add your keys, and reload. "
        "See the **PRODUCTION LIVE-DATA POLICY** in the README."
    )

st.subheader("Today's events")
status, result, detail = fetch_today_events()
if status in ("NOT_CONFIGURED", "UNAVAILABLE"):
    render_status_banner(status, detail)
else:
    fixtures = result.value or []
    if not fixtures:
        st.info("No events returned for today from the configured provider.")
    else:
        st.caption(f"API-Football · {freshness_label(result)} · {len(fixtures)} fixtures")
        for fx in fixtures:
            teams = fx.get("teams", {})
            home = teams.get("home", {}).get("name", "?")
            away = teams.get("away", {}).get("name", "?")
            fixture = fx.get("fixture", {})
            fid = fixture.get("id", "?")
            when = fixture.get("date", "")
            status_txt = fixture.get("status", {}).get("long", "")
            c = st.columns([5, 2, 2])
            c[0].markdown(f"**{home} vs {away}**  \n`event {fid}`")
            c[1].caption(when)
            c[2].caption(status_txt)

st.divider()

# secondary: saved analyses summary (persistence)
store = get_store()
rows = store.list(limit=1000)
st.subheader("Saved analyses")
if not rows:
    st.caption("No analyses saved yet.")
else:
    value = [r for r in rows if r.get("decision") in ("STRONG VALUE", "VALUE")]
    waits = [r for r in rows if r.get("decision") == "WAIT"]
    c = st.columns(4)
    c[0].metric("Analyses", len(rows))
    c[1].metric("Value candidates", len(value))
    c[2].metric("WAIT", len(waits))
    c[3].metric("Resolved", len([r for r in rows if r.get("result")]))
