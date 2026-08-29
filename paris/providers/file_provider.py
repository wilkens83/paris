"""File-based provider — TEST / OFFLINE USE ONLY (directive 2, 6).

Loads a MatchRequest from a JSON document. This is NOT a production data source
and must never back the normal user workflow. It exists only for:
- deterministic automated tests (see tests/fixtures/),
- offline import/export and reproducibility,
- an explicit user-supplied file in a clearly-labelled developer/expert mode.

Production data comes from the real providers (ApiFootballProvider,
SportsGameOddsProvider), never from this file loader.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..contracts import MatchRequest


class FileProvider:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> MatchRequest:
        if not self.path.exists():
            raise FileNotFoundError(f"Match file not found: {self.path}")
        with self.path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return MatchRequest.from_dict(data)


def load_match(path: str | Path) -> MatchRequest:
    return FileProvider(path).load()
