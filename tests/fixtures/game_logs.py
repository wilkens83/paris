"""Synthetic game logs for deterministic tests ONLY (directive 2).

These are test fixtures. They must never be imported by production runtime code.
They emulate the normalized shape a real provider (API-Football) would yield.
"""

from __future__ import annotations

from paris.features import GameLog


def sample_shot_logs() -> list[GameLog]:
    """12 appearances of a wide forward taking shots, mostly starting."""
    rows = [
        ("2026-03-01", 4, 88, True),
        ("2026-03-08", 3, 90, True),
        ("2026-03-15", 5, 76, True),
        ("2026-03-22", 2, 61, True),
        ("2026-04-01", 4, 90, True),
        ("2026-04-05", 3, 84, True),
        ("2026-04-12", 1, 70, True),
        ("2026-04-19", 4, 90, True),
        ("2026-04-26", 2, 45, False),
        ("2026-05-01", 3, 90, True),
        ("2026-05-05", 5, 83, True),
        ("2026-05-10", 2, 67, True),
    ]
    return [
        GameLog(date=d, opponent="Opp", is_home=(i % 2 == 0), started=st,
                minutes=mins, stats={"shots": shots})
        for i, (d, shots, mins, st) in enumerate(rows)
    ]
