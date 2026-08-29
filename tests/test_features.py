"""Automatic feature engines (directive 10-12)."""

import math

from paris.features import (
    build_historical_features,
    build_minutes_model,
    matchup_from_allowed,
    to_opportunity,
)
from tests.fixtures.game_logs import sample_shot_logs


def test_historical_windows_and_rate():
    logs = sample_shot_logs()
    hist = build_historical_features(logs, "shots", line=2.5)
    labels = {w.window for w in hist.windows}
    assert {"L5", "L10", "L20", "Season"} <= labels
    # per-90 rate derived from real minutes and shot totals, > 0
    assert hist.rate_per90 is not None and hist.rate_per90 > 0
    # season hit rate over 2.5 is between 0 and 1 and computed, not typed
    season = next(w for w in hist.windows if w.window == "Season")
    assert season.hit_rate_over is not None
    assert 0.0 <= season.hit_rate_over <= 1.0


def test_historical_empty_logs():
    hist = build_historical_features([], "shots", line=2.5)
    assert hist.n_games == 0
    assert hist.rate_per90 is None
    assert hist.windows == []


def test_minutes_model_projected():
    logs = sample_shot_logs()
    m = build_minutes_model(logs)
    assert 0 < m.expected_minutes <= 95
    assert 0 <= m.starter_probability <= 1
    assert m.certainty in ("A", "B", "C", "D")
    assert 0 <= m.p_90 <= 1


def test_minutes_model_confirmed_start_upgrades_certainty():
    logs = sample_shot_logs()
    m = build_minutes_model(logs, lineup_confirmed_start=True)
    assert m.certainty == "A"
    assert m.starter_probability == 1.0


def test_minutes_model_injured_zeroes_opportunity():
    m = build_minutes_model(sample_shot_logs(), injured=True)
    assert m.expected_minutes == 0.0
    opp = to_opportunity(m)
    assert opp.expected == 0.0
    assert opp.certainty == "D"


def test_matchup_multiplier_from_allowed():
    # opponent concedes more shots than league average -> multiplier > 1
    up = matchup_from_allowed("shots", opponent_allowed_per_game=14, league_avg_per_game=11)
    assert up.multiplier > 1.0
    # concedes fewer -> < 1
    down = matchup_from_allowed("shots", opponent_allowed_per_game=8, league_avg_per_game=11)
    assert down.multiplier < 1.0
    # missing data -> neutral
    neutral = matchup_from_allowed("shots", None, None)
    assert neutral.multiplier == 1.0


def test_matchup_multiplier_is_capped():
    extreme = matchup_from_allowed("shots", opponent_allowed_per_game=100, league_avg_per_game=1)
    assert extreme.multiplier <= 1.25
