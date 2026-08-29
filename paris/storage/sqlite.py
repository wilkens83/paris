"""SQLite persistence for saved analyses and post-match audit (plan 18-20).

Deliberately dependency-free (stdlib ``sqlite3``). The store persists the
normalized record from ``paris.serialize`` so the schema and the engine stay
decoupled: anything not columnized still lives in the JSON ``payload``.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..contracts import Event
from ..pipeline import Analysis
from ..serialize import analysis_to_record

_SCHEMA = Path(__file__).with_name("schema.sql")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_analysis_id() -> str:
    return f"analysis_{uuid.uuid4().hex[:12]}"


# post-event error categories (spec 58)
ERROR_CATEGORIES = [
    "minutes/opportunity", "role", "lineup", "possession", "matchup",
    "variance", "game_script", "bad_data", "market", "unpredictable_event",
]


class AnalysisStore:
    def __init__(self, path: str | Path = "paris.db"):
        self.path = str(path)
        # check_same_thread=False: Streamlit reruns each script in a fresh
        # thread, so one cached store is used across threads. A lock serializes
        # access so those cross-thread uses stay safe.
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "AnalysisStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # write
    # ------------------------------------------------------------------ #
    def save(self, analysis: Analysis, event: Event | None = None, analysis_id: str | None = None) -> str:
        aid = analysis_id or new_analysis_id()
        rec = analysis_to_record(analysis, event=event, analysis_id=aid)
        mm = rec.get("market_math") or {}
        row = {
            "analysis_id": aid,
            "created_at": _now_iso(),
            "model_version": rec["model_version"],
            "sport": rec["sport"],
            "event": rec["event"],
            "subject": rec["subject"],
            "market": rec["market"],
            "line": rec["line"],
            "side": rec["side"],
            "projection": rec["projection"],
            "interval_low": rec["interval"][0],
            "interval_high": rec["interval"][1],
            "distribution": rec["distribution"],
            "model_probability": rec["p_side"],
            "market_probability": mm.get("fair_probability") or mm.get("p_side"),
            "edge": rec["edge_points"],
            "fair_odds": mm.get("fair_odds"),
            "offered_odds": mm.get("offered_odds"),
            "ev": rec["ev_per_unit"],
            "grade": rec["grade"],
            "decision": rec["decision"],
            "opportunity_expected": rec["opportunity_expected"],
            "opportunity_certainty": rec["opportunity_certainty"],
            "verified": 1 if rec["verified"] else 0,
            "sources": json.dumps(rec["sources"]),
            "payload": json.dumps(rec),
        }
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row)
        with self._lock:
            self._conn.execute(
                f"INSERT OR REPLACE INTO analyses ({cols}) VALUES ({placeholders})", row
            )
            self._conn.commit()
        return aid

    def save_board(self, board, event: Event | None = None) -> list[str]:
        """Persist every analysis in a MatchBoard, returning their ids."""
        ev = event or board.request.event
        return [self.save(a, event=ev) for a in board.analyses]

    def resolve(
        self,
        analysis_id: str,
        *,
        actual_stat: float,
        result: str | None = None,
        actual_opportunity: float | None = None,
        closing_line: float | None = None,
        closing_price: float | None = None,
        clv: float | None = None,
        error_category: str | None = None,
    ) -> None:
        """Fill post-event audit fields (plan 18 / spec 58).

        If ``result`` is omitted it is inferred from the line and actual stat.
        """
        row = self.get(analysis_id)
        if row is None:
            raise KeyError(analysis_id)
        line = row["line"]
        side = (row["side"] or "over").lower()
        if result is None:
            result = _grade_result(actual_stat, line, side)
        projection_error = actual_stat - row["projection"]
        with self._lock:
            self._conn.execute(
                """
                UPDATE analyses SET
                    actual_stat = ?, actual_opportunity = ?, result = ?,
                    closing_line = ?, closing_price = ?, clv = ?,
                    projection_error = ?, error_category = ?, resolved_at = ?
                WHERE analysis_id = ?
                """,
                (
                    actual_stat, actual_opportunity, result,
                    closing_line, closing_price, clv,
                    projection_error, error_category, _now_iso(),
                    analysis_id,
                ),
            )
            self._conn.commit()

    # ------------------------------------------------------------------ #
    # read
    # ------------------------------------------------------------------ #
    def get(self, analysis_id: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM analyses WHERE analysis_id = ?", (analysis_id,))
            return cur.fetchone()

    def list(
        self,
        *,
        decision: str | None = None,
        resolved: bool | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        clauses, params = [], []
        if decision:
            clauses.append("decision = ?")
            params.append(decision)
        if resolved is True:
            clauses.append("result IS NOT NULL")
        elif resolved is False:
            clauses.append("result IS NULL")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._lock:
            cur = self._conn.execute(
                f"SELECT * FROM analyses {where} ORDER BY created_at DESC LIMIT ?", params
            )
            return [dict(r) for r in cur.fetchall()]

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]


def _grade_result(actual: float, line: float, side: str) -> str:
    if actual == line:
        return "PUSH"
    over = side in ("over", "more")
    hit = (actual > line) if over else (actual < line)
    return "HIT" if hit else "MISS"
