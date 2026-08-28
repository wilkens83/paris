"""Storage: save, list, resolve, audit (plan sections 18-19)."""

from pathlib import Path

from paris import analyze_match, analyze_prop, load_match
from paris.storage import AnalysisStore
from paris.ui_bridge import run_single_prop

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "real_madrid_vs_barcelona.json"


def _store(tmp_path) -> AnalysisStore:
    return AnalysisStore(tmp_path / "test.db")


def _prop_form():
    return {
        "subject": "Test Player", "market": "shots", "side": "over", "line": 2.5,
        "distribution": "poisson", "over_odds": -130, "under_odds": 110,
        "base_rate_per90": 3.2, "matchup_multiplier": 1.05,
        "expected": 85, "certainty": "B", "opportunity_metric": "minutes",
        "form_rows": [{"window": "L10", "mean": 3.4, "stdev": 1.6}],
        "verified": True,
    }


def test_save_and_get(tmp_path):
    store = _store(tmp_path)
    a = run_single_prop(_prop_form())
    aid = store.save(a)
    assert store.count() == 1
    row = store.get(aid)
    assert row is not None
    assert row["subject"] == "Test Player"
    assert row["decision"] == a.decision
    assert row["model_probability"] is not None


def test_save_board(tmp_path):
    store = _store(tmp_path)
    board = analyze_match(load_match(EXAMPLE))
    ids = store.save_board(board)
    assert len(ids) == len(board.analyses)
    assert store.count() == len(board.analyses)


def test_resolve_infers_result(tmp_path):
    store = _store(tmp_path)
    aid = store.save(run_single_prop(_prop_form()))
    # actual 4 shots vs line 2.5 over -> HIT
    store.resolve(aid, actual_stat=4)
    row = store.get(aid)
    assert row["result"] == "HIT"
    assert row["projection_error"] is not None
    # a miss
    aid2 = store.save(run_single_prop(_prop_form()))
    store.resolve(aid2, actual_stat=1)
    assert store.get(aid2)["result"] == "MISS"


def test_list_filters_resolved(tmp_path):
    store = _store(tmp_path)
    aid = store.save(run_single_prop(_prop_form()))
    store.save(run_single_prop(_prop_form()))
    store.resolve(aid, actual_stat=4)
    assert len(store.list(resolved=True)) == 1
    assert len(store.list(resolved=False)) == 1
