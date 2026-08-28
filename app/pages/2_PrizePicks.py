"""PrizePicks analyzer (plan section 16). Manual props or JSON import."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.prop_card import render_prop_detail  # noqa: E402
from components.prop_form import prop_builder_form   # noqa: E402
from state import ensure_prop_list, page_header      # noqa: E402

from paris.ui_bridge import run_single_prop          # noqa: E402

st.set_page_config(page_title="PrizePicks · PARIS", page_icon="🎯", layout="wide")
page_header("PrizePicks Analyzer", "Pick'em props led by P(MORE) / P(LESS), not the gap.")

picks = ensure_prop_list("pp_props")

tab_manual, tab_json = st.tabs(["➕ Add prop manually", "📄 Import JSON"])

with tab_manual:
    new = prop_builder_form("pp", pickem=True)
    if new is not None:
        picks.append(new)
        st.success(f"Added {new['subject']}.")

with tab_json:
    raw = st.text_area("Paste a JSON list of props (pick'em: omit odds).", height=180)
    if st.button("Load JSON") and raw.strip():
        try:
            data = json.loads(raw)
            items = data if isinstance(data, list) else data.get("props", [])
            for it in items:
                ml = it.get("market_line", {})
                picks.append({
                    "subject": it.get("subject", ""),
                    "market": it.get("market", "shots"),
                    "side": it.get("side", "more"),
                    "line": ml.get("line", it.get("line")),
                    "distribution": it.get("distribution", "auto"),
                    "base_rate_per90": it.get("base_rate_per90"),
                    "per_game_rate": it.get("per_game_rate"),
                    "variance_hint": it.get("variance_hint"),
                    "book": ml.get("book", "PrizePicks"),
                    "payout_multiplier": ml.get("payout_multiplier"),
                    "matchup_multiplier": it.get("matchup_multiplier", 1.0),
                    "expected": (it.get("opportunity") or {}).get("expected"),
                    "certainty": (it.get("opportunity") or {}).get("certainty", "C"),
                    "opportunity_metric": (it.get("opportunity") or {}).get("metric", "minutes"),
                    "form": it.get("form", []),
                    "verified": it.get("verified", False),
                    "sources": it.get("sources", []),
                })
            st.success(f"Imported {len(items)} props.")
        except Exception as exc:
            st.error(f"Bad JSON: {exc}")

if picks and st.button("Clear all"):
    st.session_state["pp_props"] = []
    st.rerun()

if picks:
    st.header("Results")
    analyses = []
    for p in picks:
        try:
            analyses.append(run_single_prop(p))
        except Exception as exc:
            st.warning(f"Skipped {p.get('subject')}: {exc}")

    table = []
    for a in analyses:
        pk = a.pickem
        table.append({
            "Player": a.prop.subject,
            "Market": a.prop.market,
            "Line": a.prop.market_line.line,
            "Projection": round(a.projection.mu, 2),
            "P(MORE)": f"{a.projection.over_under.p_over*100:.1f}%",
            "P(LESS)": f"{a.projection.over_under.p_under*100:.1f}%",
            "Favored": (pk.side if pk else "—"),
            "Grade": a.grade,
            "Decision": a.decision,
        })
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

    # groups (plan section 16)
    def _group(name, pred):
        items = [a for a in analyses if pred(a)]
        if items:
            st.subheader(name)
            for a in items:
                with st.expander(f"{a.prop.subject} — {a.prop.market} {a.prop.market_line.line:g}"):
                    render_prop_detail(a)

    _group("BEST MORE", lambda a: a.pickem and a.pickem.side == "MORE" and a.gate.passed)
    _group("BEST LESS", lambda a: a.pickem and a.pickem.side == "LESS" and a.gate.passed)
    _group("⏳ WAIT", lambda a: a.decision == "WAIT")
    _group("PASS", lambda a: a.decision in ("NO BET", "FAIR", "AVOID"))
