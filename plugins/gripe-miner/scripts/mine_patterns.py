#!/usr/bin/env python
r"""
Session Patterns miner — read this project's Claude Code transcripts and surface
repeating loops: the same stuck point, the same re-explaining, the same "I'll fix
that later," the same re-setup. Patterns, not gripes — a sibling lens over the
same transcript mine as mine_gripes.py.

Stdlib only. Cross-platform. Reads nothing but your own local ~/.claude transcripts;
writes nothing (prints JSON to stdout). No network calls, ever.

Usage:
    python mine_patterns.py --cwd "C:\path\to\project"    # mine one project's history
    python mine_patterns.py --all                          # mine every project
    python mine_patterns.py --cwd . --count-only           # just a one-line count
"""
import argparse
import datetime
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.transcripts import transcript_dir, all_project_dirs, mine  # noqa: E402
from lib.classify_patterns import classify  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Mine Claude Code transcripts for repeating session patterns.")
    ap.add_argument("--cwd", default=os.getcwd(), help="Project whose transcripts to mine.")
    ap.add_argument("--days", type=int, default=60, help="How far back to look (days).")
    ap.add_argument("--limit", type=int, default=60, help="Max snippets to return.")
    ap.add_argument("--all", action="store_true", help="Mine every project, not just --cwd.")
    ap.add_argument("--count-only", action="store_true", help="Print a one-line count, not JSON.")
    a = ap.parse_args()

    cutoff = datetime.datetime.now().timestamp() - a.days * 86400
    dirs = all_project_dirs() if a.all else [d for d in [transcript_dir(a.cwd)] if d]
    hits, scanned = mine(dirs, cutoff, classify)
    hits.sort(key=lambda h: h[0], reverse=True)
    hits = hits[:a.limit]

    if a.count_only:
        if hits:
            print(f"session-patterns: {len(hits)} recurring theme(s) across {scanned} session(s) "
                  f"in the last {a.days} days - run /session-patterns to triage.")
        return

    if not dirs:
        print(json.dumps({
            "patterns": [], "scanned_sessions": 0, "project": os.path.abspath(a.cwd),
            "note": "No Claude Code transcript folder found for this project. "
                    "Try --all, or check ~/.claude/projects.",
        }, indent=2))
        return

    print(json.dumps({
        "patterns": [{"date": ts, "theme": label, "text": s} for ts, s, label in hits],
        "scanned_sessions": scanned,
        "project": os.path.abspath(a.cwd),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
