"""PARIS — analyst workstation home / dashboard (plan sections 1, 4)."""

from __future__ import annotations

import streamlit as st

from state import get_store, page_header

st.set_page_config(page_title="PARIS", page_icon="🎯", layout="wide")

page_header(
    "🎯 PARIS — Analyst Workstation",
    "Disciplined sports-betting decision support. Verified data → model → "
    "probability → market → edge → quality gate → decision.",
)

store = get_store()
rows = store.list(limit=1000)

resolved = [r for r in rows if r.get("result")]
value = [r for r in rows if r.get("decision") in ("STRONG VALUE", "VALUE")]
waits = [r for r in rows if r.get("decision") == "WAIT"]
nobet = [r for r in rows if r.get("decision") in ("NO BET", "AVOID", "FAIR")]
edges = [r["edge"] for r in rows if r.get("edge") is not None]

st.subheader("Saved analyses")
c = st.columns(5)
c[0].metric("Props analyzed", len(rows))
c[1].metric("Value candidates", len(value))
c[2].metric("WAIT", len(waits))
c[3].metric("NO BET / Avoid", len(nobet))
c[4].metric("Avg model edge", f"{(sum(edges)/len(edges)*100):+.1f}pp" if edges else "—")

st.divider()
st.markdown(
    """
### Where to go

- **Match Analyzer** — build a match, add props, run the engine, read the ranked board.
- **PrizePicks** — analyze pick'em props with MORE/LESS probabilities.
- **Edge Finder** — filter and rank every saved candidate by decision quality.
- **Results** — resolve analyses after the match and see ROI / CLV / hit rate.
- **Model Health** — calibration buckets, Brier score, log loss.

The frontend never computes betting numbers — every figure comes from the
`paris` engine (plan §2 / §39).
"""
)

if rows:
    st.subheader("Most recent")
    st.dataframe(
        [
            {
                "Created": r["created_at"],
                "Event": r["event"],
                "Player": r["subject"],
                "Market": r["market"],
                "Line": r["line"],
                "Decision": r["decision"],
                "Grade": r["grade"],
                "Result": r.get("result") or "—",
            }
            for r in rows[:15]
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No saved analyses yet. Start in **Match Analyzer**.")
