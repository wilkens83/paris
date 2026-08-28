"""Reusable prop-builder form (plan sections 6-7).

Renders the prop inputs, the recent-form table editor, opportunity and
verification fields, and returns a flat dict on submit (or None). The dict is
consumed by ``paris.ui_bridge.build_prop`` — this component computes nothing.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from paris.ui_bridge import CERTAINTY, DISTRIBUTIONS, MARKETS, OPPORTUNITY_METRICS, SIDES

_FORM_COLUMNS = ["window", "mean", "median", "stdev", "min", "max", "hit_rate_over"]


def _blank_form_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"window": w, "mean": None, "median": None, "stdev": None,
             "min": None, "max": None, "hit_rate_over": None}
            for w in ("L5", "L10", "L20", "Season")
        ],
        columns=_FORM_COLUMNS,
    )


def prop_builder_form(key_prefix: str = "prop", pickem: bool = False) -> dict[str, Any] | None:
    """Draw the builder. Returns a prop dict when the user clicks Add, else None."""
    with st.form(key=f"{key_prefix}_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        subject = c1.text_input("Player / Subject", key=f"{key_prefix}_subject")
        market = c2.selectbox("Market", MARKETS, key=f"{key_prefix}_market")
        side = c3.selectbox("Side", SIDES, key=f"{key_prefix}_side",
                            index=(2 if pickem else 0))

        c4, c5, c6 = st.columns(3)
        line = c4.number_input("Line", value=2.5, step=0.5, key=f"{key_prefix}_line")
        distribution = c5.selectbox("Distribution", DISTRIBUTIONS, key=f"{key_prefix}_dist")
        book = c6.text_input("Book / platform", key=f"{key_prefix}_book",
                            value=("PrizePicks" if pickem else ""))

        over_odds = under_odds = payout = None
        if pickem:
            payout = st.number_input("Payout multiplier (optional)", value=0.0, step=0.5,
                                     key=f"{key_prefix}_payout") or None
        else:
            o1, o2, o3 = st.columns(3)
            over_odds = o1.number_input("Over odds (American)", value=-110, step=5,
                                        key=f"{key_prefix}_over")
            under_odds = o2.number_input("Under odds (American)", value=-110, step=5,
                                         key=f"{key_prefix}_under")
            o3.text_input("Timestamp (ISO, optional)", key=f"{key_prefix}_ts")

        st.markdown("**Model inputs**")
        m1, m2, m3 = st.columns(3)
        base90 = m1.number_input("Base rate / 90 (football)", value=0.0, step=0.1,
                                 key=f"{key_prefix}_b90") or None
        pergame = m2.number_input("Per-game rate (other)", value=0.0, step=0.1,
                                  key=f"{key_prefix}_pg") or None
        variance = m3.number_input("Variance hint (optional)", value=0.0, step=0.5,
                                   key=f"{key_prefix}_var") or None
        mm1, mm2 = st.columns([1, 2])
        matchup = mm1.number_input("Matchup multiplier", value=1.0, step=0.05,
                                   key=f"{key_prefix}_mm")
        matchup_note = mm2.text_input("Matchup note", key=f"{key_prefix}_mnote")

        st.markdown("**Opportunity** (plan 6) — leave expected blank to skip the gate")
        op1, op2, op3, op4 = st.columns(4)
        metric = op1.selectbox("Metric", OPPORTUNITY_METRICS, key=f"{key_prefix}_ometric")
        expected = op2.number_input("Expected", value=0.0, step=1.0, key=f"{key_prefix}_exp") or None
        low = op3.number_input("Low", value=0.0, step=1.0, key=f"{key_prefix}_low") or None
        high = op4.number_input("High", value=0.0, step=1.0, key=f"{key_prefix}_high") or None
        oc1, oc2 = st.columns(2)
        certainty = oc1.selectbox("Certainty A/B/C/D", CERTAINTY, index=2, key=f"{key_prefix}_cert")
        starter = oc2.number_input("Starter probability", value=0.0, step=0.05,
                                   min_value=0.0, max_value=1.0, key=f"{key_prefix}_sp") or None

        st.markdown("**Recent form** (plan 7) — historical hit rate is *not* a probability")
        form_df = st.data_editor(
            _blank_form_df(), num_rows="dynamic", use_container_width=True,
            key=f"{key_prefix}_form_editor",
        )

        st.markdown("**Verification** (spec 64)")
        v1, v2 = st.columns([1, 3])
        verified = v1.checkbox("Verified", key=f"{key_prefix}_verified")
        sources = v2.text_input("Sources (comma-separated)", key=f"{key_prefix}_sources")
        reasons_for = st.text_input("Reasons for (comma-separated)", key=f"{key_prefix}_rf")
        reasons_against = st.text_input("Reasons against (comma-separated)", key=f"{key_prefix}_ra")
        invalidation = st.text_input("Invalidation condition", key=f"{key_prefix}_inv")

        submitted = st.form_submit_button("➕ Add prop")

    if not submitted:
        return None
    if not subject.strip():
        st.error("A player/subject name is required.")
        return None

    rows = form_df.to_dict("records") if hasattr(form_df, "to_dict") else list(form_df)
    return {
        "subject": subject,
        "market": market,
        "side": side,
        "line": line,
        "distribution": distribution,
        "book": book,
        "over_odds": over_odds,
        "under_odds": under_odds,
        "payout_multiplier": payout,
        "timestamp": st.session_state.get(f"{key_prefix}_ts", ""),
        "base_rate_per90": base90,
        "per_game_rate": pergame,
        "variance_hint": variance,
        "matchup_multiplier": matchup,
        "matchup_note": matchup_note,
        "opportunity_metric": metric,
        "expected": expected,
        "low": low,
        "high": high,
        "certainty": certainty,
        "starter_prob": starter,
        "form_rows": rows,
        "verified": verified,
        "sources": sources,
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "invalidation": invalidation,
    }
