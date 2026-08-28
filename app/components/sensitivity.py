"""Sensitivity analysis chart + value threshold (plan section 11)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from paris.pipeline import Analysis
from paris.serialize import sensitivity_threshold


def render_sensitivity(analysis: Analysis) -> None:
    rows = analysis.sensitivity
    if not rows:
        st.caption("No fragile assumption identified to stress-test for this prop.")
        return

    st.subheader("Sensitivity — expected opportunity")
    df = pd.DataFrame(
        {
            "Expected value": [r.value for r in rows],
            "P(side)": [round(r.p_side, 4) for r in rows],
        }
    ).set_index("Expected value")
    st.line_chart(df, y="P(side)")
    st.dataframe(
        df.assign(**{"P(side)": (df["P(side)"] * 100).map(lambda x: f"{x:.1f}%")}),
        use_container_width=True,
    )

    threshold = sensitivity_threshold(analysis, target=0.5)
    if threshold is not None:
        assumption = rows[0].assumption.replace("_", " ")
        st.warning(f"Model stops being value below **{threshold:g}** {assumption}.")
