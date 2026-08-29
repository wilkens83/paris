"""Match Analyzer (directive 5, 14-16, 23, 25).

Primary workflow: select a real event, load its real player props, analyze.
Manual data entry is NOT the product — it lives in a clearly-labelled
Advanced / Developer Override at the bottom and is marked non-production.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.board import render_board as _render    # noqa: E402
from components.prop_form import prop_builder_form      # noqa: E402
from live import fetch_event_props, freshness_label, render_status_banner  # noqa: E402
from state import page_header                            # noqa: E402

from paris.providers import load_match                  # noqa: E402
from paris.ui_bridge import run_single_prop             # noqa: E402

st.set_page_config(page_title="Match Analyzer · PARIS", page_icon="🎯", layout="wide")
page_header("Match Analyzer", "Select a real event and prop — the system derives the numbers.")

# --------------------------------------------------------------- live flow ---
st.header("1 · Select a real event")
st.caption("Pick an event on the **Home** page, then paste its event id here to load real props.")
event_id = st.text_input("Event id (from a real odds provider)", value="")

if event_id.strip():
    st.header("2 · Real player props")
    status, result, detail = fetch_event_props(event_id.strip())
    if status in ("NOT_CONFIGURED", "UNAVAILABLE"):
        render_status_banner(status, detail)
    else:
        st.success(f"Loaded real market · {freshness_label(result)}")
        st.json(result.value if isinstance(result.value, (list, dict)) else {"data": result.value})
        st.info(
            "Prop normalization (provider props → derived Prop) runs through "
            "`paris.orchestrator.analyze_market` once a real odds provider is "
            "configured. Historical features, expected minutes and matchup are "
            "derived automatically — never typed."
        )
else:
    st.info("Enter an event id above to load real props, or configure providers on Home.")

# ---------------------------------------------- developer override (non-prod) ---
st.divider()
with st.expander("🛠️ Advanced / Developer Override — NON-PRODUCTION (manual entry & offline files)"):
    st.warning(
        "This panel is a developer utility. Manually-entered or file-loaded data "
        "is **not** live production data and must not be treated as such."
    )

    tab_file, tab_manual = st.tabs(["Offline match file", "Manual single prop"])

    with tab_file:
        st.caption("Analyze an offline match JSON (tests/fixtures or an exported file).")
        path = st.text_input("Path to match JSON", value="")
        if st.button("Analyze offline file") and path.strip():
            p = Path(path.strip())
            if not p.exists():
                st.error(f"File not found: {p}")
            else:
                try:
                    from paris.match_analysis import analyze_match
                    board = analyze_match(load_match(p))
                    _render(board)
                except Exception as exc:
                    st.error(f"Could not analyze: {exc}")

    with tab_manual:
        st.caption("Manually derive a single prop for engine debugging.")
        form = prop_builder_form("dev")
        if form is not None:
            try:
                analysis = run_single_prop(form)
                st.metric("Decision", analysis.decision)
                st.metric("Grade", analysis.grade)
                from components.prop_card import render_prop_detail
                render_prop_detail(analysis)
            except Exception as exc:
                st.error(f"Could not analyze: {exc}")
