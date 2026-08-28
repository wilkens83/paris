import math

from paris.engines import market_math as mm


def test_implied_prob_negative():
    assert mm.implied_prob(-150) == 150 / 250


def test_implied_prob_positive():
    assert mm.implied_prob(130) == 100 / 230


def test_remove_vig_sums_to_one():
    over, under = mm.remove_vig_two_way(-110, -110)
    assert math.isclose(over + under, 1.0)
    assert math.isclose(over, 0.5)


def test_hold_positive_for_juiced_market():
    assert mm.hold_percent(-110, -110) > 0


def test_fair_odds_roundtrip():
    # prob -> fair odds -> implied prob should recover the probability
    for p in (0.35, 0.5001, 0.62, 0.8):
        odds = mm.fair_odds(p)
        assert math.isclose(mm.implied_prob(odds), p, rel_tol=1e-9)


def test_profit_per_unit():
    assert mm.profit_per_unit(100) == 1.0
    assert mm.profit_per_unit(-200) == 0.5
    assert mm.profit_per_unit(150) == 1.5


def test_ev_break_even_at_fair_price():
    # at exactly fair odds, EV should be ~0
    p = 0.6
    odds = mm.fair_odds(p)
    assert abs(mm.expected_value(p, odds)) < 1e-9


def test_assess_price_edge_and_ev():
    a = mm.assess_price(prob_model=0.60, market_odds=-120, over_odds=-120, under_odds=100, side="over")
    # no-vig fair over should be below the raw implied of -120
    assert a.prob_market_fair < mm.implied_prob(-120)
    assert a.edge_points == a.prob_model - a.prob_market_fair
    assert a.hold is not None and a.hold > 0
