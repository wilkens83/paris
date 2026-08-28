"""Quality Gate visualization (plan section 10)."""

from __future__ import annotations

import streamlit as st

from paris.pipeline import Analysis

_LABELS = {
    "entity_verified": "Entity Verified",
    "data_sufficient": "Data Sufficient",
    "line_present": "Market Line Present",
    "model_completed": "Model Completed",
    "opportunity_certain": "Opportunity Certainty",
    "uncertainty_estimated": "Uncertainty Estimated",
}

_STATUS_COLOR = {"PASS": "🟢", "WAIT": "⏳", "NO BET": "⛔"}


def render_quality_gate(analysis: Analysis) -> None:
    gate = analysis.gate
    st.subheader("Quality Gate")
    for key, label in _LABELS.items():
        ok = gate.checks.get(key)
        if ok is None:
            continue
        mark = "✅" if ok else "❌"
        extra = ""
        if key == "opportunity_certain" and analysis.prop.opportunity:
            extra = f": {analysis.prop.opportunity.certainty}"
        st.markdown(f"{mark} {label}{extra}")

    status = gate.verdict
    icon = _STATUS_COLOR.get(status, "")
    st.markdown(f"### {icon} STATUS: {status}")
    if gate.reasons:
        st.info("Reason: " + "; ".join(gate.reasons))
