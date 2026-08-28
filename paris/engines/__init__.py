"""Deterministic quantitative engines (spec sections 21-27).

These modules never invent data. They only transform verified inputs:

    - market_math   : odds, vig removal, fair odds, edge, EV (spec 26)
    - distributions : projection -> P(Over)/P(Under) (spec 21-24)
    - prizepicks    : pick'em edge and break-even math (spec 27)
"""

from . import distributions, market_math, prizepicks

__all__ = ["market_math", "distributions", "prizepicks"]
