"""File-based verified-data provider.

Loads a MatchRequest from a JSON document. The JSON is the "verified data"
boundary: whoever authors it (a human analyst, or an upstream Research +
Verifier stage) is asserting the numbers are checked and sourced. The pipeline
then does only deterministic math on top.
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
