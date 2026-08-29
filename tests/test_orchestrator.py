"""End-to-end derive → verify → analyze over normalized real-shaped data.

This exercises the production analysis path without any external network: the
caller supplies normalized game logs (as a real provider would), and the system
derives every model input, verifies, and runs the quant engine.
"""

from paris.contracts import MarketLine
from paris.orchestrator import analyze_market
from tests.fixtures.game_logs import sample_shot_logs


def test_analyze_market_derives_everything():
    out = analyze_market(
        subject="Test Forward",
        market="shots",
        side="over",
        market_line=MarketLine(line=2.5, over_odds=-130, under_odds=110, book="TEST"),
        logs=sample_shot_logs(),
        opponent_allowed_per_game=13.0,
        league_avg_per_game=11.0,
        lineup_confirmed_start=True,
        entity_confirmed=True,
        sources=["test fixture"],
    )
    a = out.analysis
    # nothing was typed: base rate, form, opportunity, matchup all derived
    assert a.prop.base_rate_per90 is not None
    assert a.prop.form  # windows derived
    assert a.prop.opportunity is not None
    assert a.prop.matchup_multiplier != 1.0
    # confirmed start + confirmed entity + sufficient data -> VERIFIED
    assert out.verification.status == "VERIFIED"
    assert a.prop.verified is True
    assert a.decision in ("STRONG VALUE", "VALUE", "LEAN", "FAIR", "AVOID")
    assert out.derivation  # human-readable reasoning present


def test_unconfirmed_entity_forces_wait_or_nobet():
    out = analyze_market(
        subject="Test Forward",
        market="shots",
        side="over",
        market_line=MarketLine(line=2.5, over_odds=-130, under_odds=110),
        logs=sample_shot_logs(),
        entity_confirmed=None,          # not independently confirmed
        lineup_confirmed_start=None,
    )
    assert out.verification.status in ("WAIT", "NO BET")
    assert out.analysis.decision in ("WAIT", "NO BET")


def test_no_logs_is_no_bet():
    out = analyze_market(
        subject="Nobody",
        market="shots",
        side="over",
        market_line=MarketLine(line=2.5, over_odds=-110, under_odds=-110),
        logs=[],
        entity_confirmed=True,
    )
    # no history -> insufficient data -> NO BET, never invented (no model at all)
    assert out.verification.status == "NO BET"
    assert out.analysis is None
    assert out.decision == "NO BET"
