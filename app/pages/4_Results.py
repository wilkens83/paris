"""Results & post-match audit (plan sections 18-19, spec 58)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state import get_store, page_header  # noqa: E402

from paris import metrics                  # noqa: E402
from paris.storage import ERROR_CATEGORIES  # noqa: E402

st.set_page_config(page_title="Results · PARIS", page_icon="🎯", layout="wide")
page_header("Results", "Resolve analyses after the match; track ROI, CLV, hit rate.")

store = get_store()
rows = store.list(limit=2000)
if not rows:
    st.info("No saved analyses yet.")
    st.stop()

summary = metrics.summarize(rows)
c = st.columns(6)
c[0].metric("Resolved", summary.n_resolved)
c[1].metric("Hit rate", f"{summary.hit_rate*100:.1f}%" if summary.hit_rate is not None else "—")
c[2].metric("ROI", f"{summary.roi*100:+.1f}%" if summary.roi is not None else "—")
c[3].metric("Avg CLV", f"{summary.average_clv:+.3f}" if summary.average_clv is not None else "—")
c[4].metric("Brier", f"{summary.brier:.4f}" if summary.brier is not None else "—")
c[5].metric("Log loss", f"{summary.log_loss:.4f}" if summary.log_loss is not None else "—")

st.divider()

# ---------------------------------------------------------------- resolve ---
st.subheader("Resolve an analysis")
pending = store.list(resolved=False, limit=500)
if pending:
    labels = {
        f'{r["subject"]} · {r["market"]} {r["line"]} {(r["side"] or "").upper()} · {r["analysis_id"][:16]}': r["analysis_id"]
        for r in pending
    }
    choice = st.selectbox("Pending analysis", list(labels.keys()))
    aid = labels[choice]
    rc1, rc2, rc3 = st.columns(3)
    actual = rc1.number_input("Actual stat", value=0.0, step=1.0)
    closing_line = rc2.number_input("Closing line (optional)", value=0.0, step=0.5) or None
    clv = rc3.number_input("CLV (optional)", value=0.0, step=0.01) or None
    err = st.selectbox("Error category (if a miss)", ["(none)"] + ERROR_CATEGORIES)
    if st.button("Save result"):
        store.resolve(
            aid, actual_stat=actual, closing_line=closing_line, clv=clv,
            error_category=(None if err == "(none)" else err),
        )
        st.success("Resolved. Metrics above will refresh on rerun.")
        st.rerun()
else:
    st.caption("Nothing pending — every saved analysis is resolved.")

st.divider()
st.subheader("All analyses")
st.dataframe(
    pd.DataFrame([
        {
            "Date": r["created_at"],
            "Player": r["subject"],
            "Prop": f'{r["market"]} {r["line"]} {(r["side"] or "").upper()}',
            "Model P": f'{(r.get("model_probability") or 0)*100:.1f}%',
            "Grade": r["grade"],
            "Decision": r["decision"],
            "Result": r.get("result") or "—",
            "CLV": (f'{r["clv"]:+.3f}' if r.get("clv") is not None else "—"),
        }
        for r in rows
    ]),
    use_container_width=True,
    hide_index=True,
)
