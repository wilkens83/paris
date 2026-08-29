"""Developer / offline CLI utility (directive 4, 40).

This is a DEVELOPER UTILITY, not the product. The production workflow is the
live-data app/API (real events → real props → derive → verify → analyze). This
command analyzes an explicit offline match JSON — useful for tests,
reproducibility and debugging the quant engine.

Usage:
    python -m paris analyze <match.json>     # analyze an offline match file
    python -m paris config                    # show live-data configuration status
"""

from __future__ import annotations

import sys
from pathlib import Path

from .config import get_settings
from .match_analysis import analyze_match
from .providers import load_match
from .report import render_board


def _run_file(path: str) -> int:
    request = load_match(path)
    board = analyze_match(request)
    print(render_board(board))
    return 0


def _config() -> int:
    s = get_settings()
    print("PARIS live-data configuration:")
    print(f"  API_FOOTBALL_KEY        : {'set' if s.api_football_key else 'NOT CONFIGURED'}")
    print(f"  SPORTSGAMEODDS_API_KEY  : {'set' if s.sportsgameodds_key else 'NOT CONFIGURED'}")
    print(f"  DATABASE_URL            : {'set' if s.database_url else 'not set (SQLite dev default)'}")
    missing = s.missing()
    if missing:
        print("\nMissing required live-data credentials: " + ", ".join(missing))
        print("Real fixtures/props cannot be loaded until these are set (see .env.example).")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    cmd, *rest = argv
    if cmd == "config":
        return _config()
    if cmd == "analyze":
        if not rest:
            print("Provide a match JSON path: python -m paris analyze <file.json>", file=sys.stderr)
            return 2
        path = rest[0]
        if not Path(path).exists():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
        return _run_file(path)
    print(f"Unknown command: {cmd}\n", file=sys.stderr)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
