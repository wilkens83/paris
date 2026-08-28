"""UI input -> contracts (plan section 33)."""

from paris.ui_bridge import (
    build_event,
    build_match_request,
    build_prop,
    form_rows_to_dicts,
    run_single_prop,
)


def _base_prop_form():
    return {
        "subject": "Test Player",
        "market": "shots",
        "side": "over",
        "line": 2.5,
        "distribution": "poisson",
        "over_odds": -130,
        "under_odds": 110,
        "book": "SAMPLE",
        "base_rate_per90": 3.2,
        "matchup_multiplier": 1.05,
        "opportunity_metric": "minutes",
        "expected": 85,
        "certainty": "B",
        "form_rows": [
            {"window": "L10", "mean": 3.4, "stdev": 1.6, "median": None,
             "min": None, "max": None, "hit_rate_over": None},
            {"window": "L5", "mean": None},  # skipped: no mean
        ],
        "verified": True,
        "sources": "official stats, probable XI",
    }


def test_form_rows_skips_incomplete():
    rows = form_rows_to_dicts([
        {"window": "L10", "mean": 3.4},
        {"window": "", "mean": 2.0},
        {"window": "Season", "mean": None},
    ])
    assert len(rows) == 1
    assert rows[0]["window"] == "L10"


def test_build_prop_maps_fields():
    p = build_prop(_base_prop_form())
    assert p.subject == "Test Player"
    assert p.market_line.line == 2.5
    assert p.market_line.over_odds == -130
    assert p.base_rate_per90 == 3.2
    assert p.opportunity is not None and p.opportunity.certainty == "B"
    assert len(p.form) == 1                    # incomplete row dropped
    assert p.sources == ["official stats", "probable XI"]
    assert p.verified is True


def test_build_prop_requires_subject():
    form = _base_prop_form()
    form["subject"] = "  "
    try:
        build_prop(form)
        assert False
    except ValueError:
        pass


def test_run_single_prop_produces_value():
    a = run_single_prop(_base_prop_form())
    assert a.gate.passed
    assert a.decision in ("STRONG VALUE", "VALUE", "LEAN")


def test_build_match_request_roundtrip():
    event = {"sport": "football", "home": "A", "away": "B", "competition": "X", "date": "2026-01-01"}
    req = build_match_request(event, [_base_prop_form()])
    assert req.event.home == "A"
    assert len(req.props) == 1


def test_pickem_when_no_odds():
    form = _base_prop_form()
    form["over_odds"] = None
    form["under_odds"] = None
    form["side"] = "more"
    a = run_single_prop(form)
    assert a.pickem is not None
    assert a.price is None
