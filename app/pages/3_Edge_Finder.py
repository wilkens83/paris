"""Edge Finder — filter & rank every saved candidate (plan section 15).

Ranking hierarchy (not EV alone): Quality-Gate PASS → opportunity certainty →
edge → EV → grade.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state import get_store, page_header  # noqa: E402

st.set_page_config(page_title="Edge Finder · PARIS", page_icon="🎯", layout="wide")
page_header("Edge Finder", "Rank saved candidates by decision quality — never EV alone.")

rows = get_store().list(limit=2000)
if not rows:
    st.info("No saved analyses yet. Analyze and save a match first.")
    st.stop()

# ----------------------------------------------------------------- filters ---
f = st.columns(5)
sports = sorted({r["sport"] for r in rows if r["sport"]})
sport = f[0].selectbox("Sport", ["(any)"] + sports)
min_prob = f[1].slider("Min model P", 0.0, 1.0, 0.5, 0.01)
min_edge = f[2].slider("Min edge (pp)", -20.0, 20.0, 0.0, 0.5) / 100.0
grades = ["(any)", "A+", "A", "B+", "B", "C", "D", "F"]
min_grade = f[3].selectbox("Min grade", grades)
verified_only = f[4].checkbox("Verified only", value=True)

certainties = st.multiselect("Opportunity certainty", ["A", "B", "C", "D"], default=["A", "B"])
pass_only = st.checkbox("Quality Gate PASS only", value=True)

_GRADE_ORDER = ["A+", "A", "B+", "B", "C", "D", "F"]


def _grade_ok(g: str) -> bool:
    if min_grade == "(any)":
        return True
    try:
        return _GRADE_ORDER.index(g) <= _GRADE_ORDER.index(min_grade)
    except ValueError:
        return False


def _keep(r: dict) -> bool:
    if sport != "(any)" and r["sport"] != sport:
        return False
    if (r.get("model_probability") or 0) < min_prob:
        return False
    if (r.get("edge") or -1) < min_edge:
        return False
    if not _grade_ok(r.get("grade") or "F"):
        return False
    if verified_only and not r.get("verified"):
        return False
    if certainties and (r.get("opportunity_certainty") or "D") not in certainties:
        return False
    if pass_only and r.get("decision") in ("NO BET",):
        return False
    return True


filtered = [r for r in rows if _keep(r)]

# ranking hierarchy (plan section 15)
_CERT_RANK = {"A": 0, "B": 1, "C": 2, "D": 3}


def _rank_key(r: dict):
    gate_pass = 0 if r.get("decision") not in ("NO BET",) else 1
    cert = _CERT_RANK.get(r.get("opportunity_certainty") or "D", 4)
    return (gate_pass, cert, -(r.get("edge") or 0), -(r.get("ev") or 0),
            _GRADE_ORDER.index(r["grade"]) if r.get("grade") in _GRADE_ORDER else 9)


filtered.sort(key=_rank_key)

st.caption(f"{len(filtered)} of {len(rows)} candidates match.")
st.dataframe(
    pd.DataFrame([
        {
            "Rank": i,
            "Player": r["subject"],
            "Prop": f'{r["market"]} {r["line"]} {(r["side"] or "").upper()}',
            "Model P": f'{(r.get("model_probability") or 0)*100:.1f}%',
            "Edge": f'{(r.get("edge") or 0)*100:+.1f}pp',
            "EV": (f'{r["ev"]:+.3f}' if r.get("ev") is not None else "—"),
            "Cert": r.get("opportunity_certainty") or "—",
            "Grade": r["grade"],
            "Decision": r["decision"],
        }
        for i, r in enumerate(filtered, 1)
    ]),
    use_container_width=True,
    hide_index=True,
)
