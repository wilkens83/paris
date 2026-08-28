"""Command-line entry point — "ask for a match analysis".

Usage:
    python -m paris analyze <match.json>     # analyse a match file
    python -m paris analyze                   # interactive: ask for the match
    python -m paris demo                      # run the bundled example

The interactive mode implements the activation command (spec 66): give it a
match, it resolves the event, runs the graph and prints the ranked board.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .match_analysis import analyze_match
from .providers import load_match
from .report import render_board

_EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
_DEMO = _EXAMPLES / "real_madrid_vs_barcelona.json"


def _run_file(path: str) -> int:
    request = load_match(path)
    board = analyze_match(request)
    print(render_board(board))
    return 0


def _interactive() -> int:
    print("=== paris — Match Analysis (MODE B) ===")
    print("Which match do you want to analyze?")
    print("Enter the path to a verified match JSON file")
    print(f"(or press Enter to run the bundled demo: {_DEMO.name})")
    try:
        answer = input("> ").strip()
    except EOFError:
        answer = ""
    if not answer:
        if not _DEMO.exists():
            print("No demo file found. Provide a match JSON path.", file=sys.stderr)
            return 1
        return _run_file(str(_DEMO))
    if not Path(answer).exists():
        print(f"File not found: {answer}", file=sys.stderr)
        return 1
    return _run_file(answer)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return _interactive()

    cmd, *rest = argv
    if cmd == "analyze":
        if rest:
            path = rest[0]
            if not Path(path).exists():
                print(f"File not found: {path}", file=sys.stderr)
                return 1
            return _run_file(path)
        return _interactive()
    if cmd == "demo":
        if not _DEMO.exists():
            print("Demo file missing.", file=sys.stderr)
            return 1
        return _run_file(str(_DEMO))
    if cmd in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    print(f"Unknown command: {cmd}\n", file=sys.stderr)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
