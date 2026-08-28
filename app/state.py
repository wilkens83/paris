"""Streamlit session-state helpers and shared wiring.

Thin glue only. All contract-building lives in ``paris.ui_bridge`` (testable);
all numbers live in the engine. This module just holds per-session lists and a
cached store handle.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# make the repo root importable when Streamlit runs a page directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from paris.storage import AnalysisStore  # noqa: E402

DB_PATH = os.environ.get("PARIS_DB", str(_ROOT / "paris.db"))


def get_store() -> AnalysisStore:
    """One AnalysisStore per session (cached as a resource)."""
    if "store" not in st.session_state:
        st.session_state["store"] = AnalysisStore(DB_PATH)
    return st.session_state["store"]


def ensure_prop_list(key: str = "props") -> list[dict[str, Any]]:
    if key not in st.session_state:
        st.session_state[key] = []
    return st.session_state[key]


def blank_form_rows() -> list[dict[str, Any]]:
    return [
        {"window": w, "mean": None, "median": None, "stdev": None,
         "min": None, "max": None, "hit_rate_over": None}
        for w in ("L5", "L10", "L20", "Season")
    ]


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.markdown(
        "> The system's goal is **never to force a bet**. NO BET / WAIT are "
        "first-class outcomes."
    )
