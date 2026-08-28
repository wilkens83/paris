"""Model Health — calibration & scoring (plan section 20, spec 25)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state import get_store, page_header  # noqa: E402

from paris import metrics                  # noqa: E402

st.set_page_config(page_title="Model Health · PARIS", page_icon="🎯", layout="wide")
page_header("Model Health", "Is a 70% bucket actually winning ~70%? (spec 25)")

rows = get_store().list(limit=5000)
summary = metrics.summarize(rows)

c = st.columns(5)
c[0].metric("Resolved", summary.n_resolved)
c[1].metric("Brier", f"{summary.brier:.4f}" if summary.brier is not None else "—")
c[2].metric("Log loss", f"{summary.log_loss:.4f}" if summary.log_loss is not None else "—")
c[3].metric("Calibration err", f"{summary.calibration_error*100:.1f}pp" if summary.calibration_error is not None else "—")
c[4].metric("ROI", f"{summary.roi*100:+.1f}%" if summary.roi is not None else "—")

st.subheader("Calibration by bucket")
if summary.n_resolved == 0:
    st.info("Resolve some analyses on the Results page to populate calibration.")
else:
    df = pd.DataFrame([
        {
            "Bucket": b.label,
            "N": b.n,
            "Predicted": (f"{b.predicted*100:.1f}%" if b.predicted is not None else "—"),
            "Actual": (f"{b.actual*100:.1f}%" if b.actual is not None else "—"),
        }
        for b in summary.buckets
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)

    chart = pd.DataFrame({
        "Bucket": [b.label for b in summary.buckets],
        "Predicted": [(b.predicted or 0) for b in summary.buckets],
        "Actual": [(b.actual or 0) for b in summary.buckets],
    }).set_index("Bucket")
    st.bar_chart(chart)
    st.caption("A 70% bucket winning materially less than 70% is evidence of overconfidence.")
