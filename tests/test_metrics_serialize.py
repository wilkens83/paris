"""Metrics + serialization (plan sections 20, 31)."""

import math

from paris import metrics
from paris.serialize import analysis_to_record, sensitivity_threshold
from paris.ui_bridge import run_single_prop


def _prop_form():
    return {
        "subject": "Test Player", "market": "shots", "side": "over", "line": 2.5,
        "distribution": "poisson", "over_odds": -130, "under_odds": 110,
        "base_rate_per90": 3.2, "matchup_multiplier": 1.05,
        "expected": 85, "certainty": "B", "opportunity_metric": "minutes",
        "form_rows": [{"window": "L10", "mean": 3.4, "stdev": 1.6}],
        "verified": True,
    }


def test_record_has_normalized_shape():
    rec = analysis_to_record(run_single_prop(_prop_form()), analysis_id="analysis_x")
    assert rec["analysis_id"] == "analysis_x"
    assert 0 <= rec["probabilities"]["over"] <= 1
    assert rec["market_math"]["type"] == "sportsbook"
    assert "edge_points" in rec["market_math"]
    assert rec["quality_gate"]["status"] in ("PASS", "WAIT", "NO BET")


def test_sensitivity_threshold_interpolates():
    a = run_single_prop(_prop_form())
    thr = sensitivity_threshold(a, target=0.5)
    # the sample prop crosses 50% somewhere within the 60-90 minutes grid
    assert thr is None or 60 <= thr <= 90


def test_brier_and_hit_rate():
    items = [
        {"model_probability": 0.6, "result": "HIT"},
        {"model_probability": 0.6, "result": "MISS"},
        {"model_probability": 0.8, "result": "HIT"},
        {"model_probability": 0.4, "result": "PUSH"},   # excluded
    ]
    assert math.isclose(metrics.hit_rate(items), 2 / 3)
    brier = metrics.brier_score(items)
    expected = ((0.6 - 1) ** 2 + (0.6 - 0) ** 2 + (0.8 - 1) ** 2) / 3
    assert math.isclose(brier, expected)


def test_calibration_buckets_assign_correctly():
    items = [
        {"model_probability": 0.62, "result": "HIT"},
        {"model_probability": 0.63, "result": "MISS"},
        {"model_probability": 0.72, "result": "HIT"},
    ]
    buckets = {b.label: b for b in metrics.calibration_buckets(items)}
    assert buckets["60-65%"].n == 2
    assert buckets["70-100%"].n == 1


def test_roi_settles_prices():
    items = [
        {"result": "HIT", "offered_odds": 100},   # +1
        {"result": "MISS", "offered_odds": -110},  # -1
    ]
    # staked 2 units, profit 1 - 1 = 0 -> ROI 0
    assert math.isclose(metrics.roi(items), 0.0)
