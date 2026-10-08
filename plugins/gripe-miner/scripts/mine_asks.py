#!/usr/bin/env python
r"""
Ask Miner — the "Automate this" lens. Reads this project's Claude Code transcripts,
clusters the prompts you keep typing across sessions, and sums the token usage
spent answering each cluster, so /automate can propose the cheapest durable fix
(skill, hook, script, scheduled routine, CLAUDE.md line, MCP connector) for
whatever you keep asking for by hand.

Stdlib only. Cross-platform. Reads nothing but your own local ~/.claude transcripts;
writes nothing (prints JSON to stdout). No network calls, ever.

Token numbers come from message.usage on the assistant turns that followed each
prompt, deduplicated by message id so streamed chunks aren't double counted. A turn
with no usage field falls back to a chars/4 estimate and flags its cluster
"tokens_estimated": true. Nothing is invented beyond that fallback.

Prompts sent by scripts (`claude -p`, the Agent SDK, cron jobs) and slash-command
runs (/deep-research, /commit ...) are already automated, so they are skipped by
default; --include-scripted clusters them too, flagged "scripted", when you want
to see what your routines cost.

--days is applied per message by its own timestamp (file mtime only when a record
has none), so a long-running session file contributes only the prompts inside the
window.

Usage:
    python mine_asks.py --cwd "C:\path\to\project"    # mine one project's history
    python mine_asks.py --all                          # mine every project
    python mine_asks.py --cwd . --count-only           # just a one-line count
    python mine_asks.py --all --include-scripted       # routines too, flagged
"""
import argparse
import datetime
import glob
import json
import os
import sys

# Windows consoles default to cp1252 and choke on smart quotes / bullets; force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.transcripts import transcript_dir, all_project_dirs, iter_prompts  # noqa: E402
from lib.classify_asks import cluster, summarize, usage_totals, WEIGHTS  # noqa: E402

SCORE_DOC = "count x tokens.weighted (weighted = input-token equivalents, see `weighting`)"


def main():
    ap = argparse.ArgumentParser(description="Mine Claude Code transcripts for repeated asks + token burn.")
    ap.add_argument("--cwd", default=os.getcwd(), help="Project whose transcripts to mine.")
    ap.add_argument("--days", type=int, default=60, help="How far back to look (days).")
    ap.add_argument("--limit", type=int, default=15, help="Max clusters to return.")
    ap.add_argument("--min-sessions", type=int, default=3,
                    help="Distinct sessions a cluster must span to count (default 3).")
    ap.add_argument("--include-scripted", action="store_true",
                    help="Also cluster prompts sent by scripts / claude -p and slash-command runs (flagged \"scripted\").")
    ap.add_argument("--all", action="store_true", help="Mine every project, not just --cwd.")
    ap.add_argument("--count-only", action="store_true", help="Print a one-line count, not JSON.")
    a = ap.parse_args()

    cutoff = datetime.datetime.now().timestamp() - a.days * 86400
    dirs = all_project_dirs() if a.all else [d for d in [transcript_dir(a.cwd)] if d]

    # Same "scanned" semantics as mine_gripes.py / mine_patterns.py: every *.jsonl
    # touched inside the window is opened and counts, whether or not it yielded a
    # prompt. The window itself is applied per message (see iter_prompts), so a
    # recently-touched file contributes only the prompts actually in it.
    scanned = 0
    for tdir in dirs:
        for path in glob.glob(os.path.join(tdir, "*.jsonl")):
            try:
                if os.path.getmtime(path) >= cutoff:
                    scanned += 1
            except OSError:
                continue

    prompts = list(iter_prompts(dirs, cutoff))
    token_totals = usage_totals(prompts)  # everything in the window, whatever its origin
    raw_clusters, stats = cluster(prompts, include_scripted=a.include_scripted)
    clusters = summarize(raw_clusters, min_sessions=a.min_sessions, limit=a.limit)

    if a.count_only:
        # Silence over noise: print nothing when nothing repeats enough to automate.
        if clusters:
            burned = sum(c["tokens"]["weighted"] for c in clusters)
            print(f"ask-miner: {len(clusters)} repeated-ask cluster(s) across {scanned} session(s) "
                  f"in the last {a.days} days (~{burned:,} weighted tokens) - run /automate for suggestions.")
        return

    if not dirs:
        print(json.dumps({
            "clusters": [], "scanned_sessions": 0, "project": os.path.abspath(a.cwd),
            "token_totals": usage_totals([]),
            "note": "No Claude Code transcript folder found for this project. "
                    "Try --all, or check ~/.claude/projects.",
        }, indent=2))
        return

    out = {
        "clusters": clusters,
        "scanned_sessions": scanned,
        "project": os.path.abspath(a.cwd),
        "token_totals": token_totals,
        "prompts": stats,
        "days": a.days,
        "since": datetime.datetime.fromtimestamp(cutoff).strftime("%Y-%m-%d"),
        "min_sessions": a.min_sessions,
        "include_scripted": a.include_scripted,
        "weighting": WEIGHTS,
        "score": SCORE_DOC,
    }
    if not clusters:
        out["note"] = (f"Nothing repeats across {a.min_sessions}+ sessions in the last {a.days} days"
                       + ("" if a.include_scripted else
                          f" ({stats['skipped']['scripted']} script-sent prompts and "
                          f"{stats['skipped']['command']} slash-command runs were skipped; "
                          f"--include-scripted clusters those too)") + ".")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
