from pathlib import Path

from paris import analyze_match, analyze_prop, load_match, render_board
from paris.contracts import MarketLine, Opportunity, Prop, FormWindow

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "real_madrid_vs_barcelona.json"


def _strong_prop() -> Prop:
    return Prop(
        subject="Test Player",
        market="shots",
        side="over",
        market_line=MarketLine(line=2.5, over_odds=-130, under_odds=110),
        distribution="poisson",
        base_rate_per90=3.2,
        form=[FormWindow(window="L10", mean=3.4, stdev=1.6)],
        opportunity=Opportunity(metric="minutes", expected=85, certainty="B"),
        matchup_multiplier=1.05,
        verified=True,
    )


def test_strong_prop_produces_value_or_stronger():
    a = analyze_prop(_strong_prop())
    assert a.gate.passed
    assert a.p_side > 0.5
    assert a.price is not None
    assert a.decision in ("STRONG VALUE", "VALUE")


def test_unverified_prop_is_no_bet():
    p = _strong_prop()
    p.verified = False
    a = analyze_prop(p)
    assert not a.gate.passed
    assert a.decision == "NO BET"


def test_uncertain_opportunity_waits():
    p = _strong_prop()
    p.opportunity.certainty = "C"
    a = analyze_prop(p)
    assert a.gate.verdict == "WAIT"
    assert a.decision == "WAIT"


def test_projection_requires_a_base_rate():
    p = _strong_prop()
    p.base_rate_per90 = None
    p.per_game_rate = None
    try:
        analyze_prop(p)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_match_board_buckets_and_renders():
    request = load_match(EXAMPLE)
    board = analyze_match(request)
    # every prop lands in exactly one bucket
    total = (len(board.best_bets) + len(board.secondary) + len(board.leans)
             + len(board.avoid) + len(board.wait) + len(board.no_bet))
    assert total == len(board.analyses) == len(request.props)
    # the rotation-risk prop (certainty C) must be a WAIT
    assert any(a.prop.subject == "Rodrygo" and a.decision == "WAIT" for a in board.analyses)
    # renders without error and mentions the match
    text = render_board(board)
    assert "Real Madrid vs Barcelona" in text
    assert "Board summary" in text


def test_pickem_prop_scored():
    request = load_match(EXAMPLE)
    board = analyze_match(request)
    lewa = next(a for a in board.analyses if a.prop.subject == "Robert Lewandowski")
    assert lewa.pickem is not None
    assert lewa.pickem.side in ("MORE", "LESS")
