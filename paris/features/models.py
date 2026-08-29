"""Normalized inputs to the feature engines (directive 10-12, 28).

A ``GameLog`` is one appearance from a real game-log source, normalized. The
feature engines consume lists of these — they never take hand-typed numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GameLog:
    date: str                       # ISO date of the fixture
    opponent: str = ""
    is_home: bool = True
    started: bool = False
    minutes: float = 0.0
    stats: dict[str, float] = field(default_factory=dict)   # e.g. {"shots": 3, "sot": 1}
    provenance: dict[str, Any] = field(default_factory=dict)

    def stat(self, name: str) -> float:
        return float(self.stats.get(name, 0.0))
