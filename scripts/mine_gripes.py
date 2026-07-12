#!/usr/bin/env python
r"""
Gripe Miner — read this project's Claude Code transcripts and surface the moments
you got frustrated, so they can be turned into a ranked fix list.

Stdlib only. Cross-platform. Reads nothing but your own local ~/.claude transcripts;
writes nothing (prints JSON to stdout). No network calls, ever.

Usage:
    python mine_gripes.py --cwd "C:\path\to\project"    # mine one project's history
    python mine_gripes.py --all                          # mine every project
    python mine_gripes.py --cwd . --count-only           # just a one-line count
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

# Windows consoles default to cp1252 and choke on smart quotes / bullets; force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# ── Gripe detection (tuned regex — the core of the tool) ─────────────────────
# Phrases that mark a genuine usability gripe / friction / wish in a human message.
COMPLAINT_RE = re.compile(
    r"\b("
    r"annoy\w*|frustrat\w*|hate|clunky|jank\w*|flak\w*|buggy|glitch\w*|"
    r"tedious|painful|a pain|confus\w*|clumsy|awkward|ugly|"
    r"too many|too much|too slow|so slow|really slow|laggy|sluggish|"
    r"doesn'?t work|not working|isn'?t working|won'?t work|broke\w*|"
    r"keeps? (?:break|fail|crash|resett|forget|losing|doing)|"
    r"every time|each time|keep having to|have to keep|always has to|"
    r"why (?:does|is|do|isn'?t|can'?t|won'?t)|"
    r"wish (?:it|there|i|we|this)|it should|should (?:be|just|automatically)|"
    r"i don'?t like|i really don'?t like|makes no sense|doesn'?t make sense|"
    r"stupid|dumb|hard to (?:find|use|read|see|tell)|difficult to|"
    r"can'?t (?:find|tell|see|figure)|not obvious|not clear|unclear|"
    r"hate that|annoying that|weird that|odd that|inconsistent"
    r")\b",
    re.IGNORECASE,
)

# Lines that are clearly not gripes even if a keyword matches (reduce noise).
NOISE_RE = re.compile(r"^(commit|git |run |ls |cd |cat |npm |python |\.\\|\./)", re.IGNORECASE)

# Background task/agent/workflow completion payloads arrive as user turns but are
# machine output, not something the human typed — skip any message that opens with one.
NOTIFY_START_RE = re.compile(
    r'^(dynamic workflow\s+"|agent\s+"|sub-?agent\s+"|task\s+".*?"\s+(completed|finished))',
    re.IGNORECASE,
)


def strip_injections(text):
    """Remove harness/system-injected tag blocks that get prepended to user turns,
    so we mine only what the human actually typed."""
    text = re.sub(r"<task-notification>.*?</status>\s*", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(
        r"<(system-reminder|command-name|command-message|command-args|"
        r"local-command-stdout|local-command-stderr|user-memory-input)>.*?</\1>\s*",
        " ", text, flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(r"</?[a-z][^>]*>", " ", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def transcript_dir(cwd):
    """Claude Code stores a project's transcripts under a folder whose name is the
    absolute cwd with every non-alphanumeric char replaced by '-'.
    e.g.  C:\\dev\\New project  ->  C--dev-New-project"""
    enc = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd))
    d = os.path.join(os.path.expanduser("~"), ".claude", "projects", enc)
    return d if os.path.isdir(d) else None


def all_project_dirs():
    root = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    return [p for p in glob.glob(os.path.join(root, "*")) if os.path.isdir(p)]


def mine_dir(tdir, cutoff, seen, hits):
    """Pull the human's gripe messages out of one project's transcript folder.
    Only genuine typed prompts count: type=='user', role=='user', STRING content
    (tool results arrive as list content / toolUseResult and are skipped)."""
    scanned = 0
    for path in glob.glob(os.path.join(tdir, "*.jsonl")):
        try:
            if os.path.getmtime(path) < cutoff:
                continue
        except OSError:
            continue
        scanned += 1
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if '"user"' not in line:
                        continue
                    try:
                        o = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    if o.get("type") != "user" or o.get("isSidechain"):
                        continue
                    if "toolUseResult" in o:
                        continue
                    msg = o.get("message") or {}
                    if msg.get("role") != "user":
                        continue
                    content = msg.get("content")
                    if not isinstance(content, str):
                        continue  # list content = tool result, not a typed message
                    text = strip_injections(content).strip()
                    if not text or len(text) < 12 or NOISE_RE.match(text):
                        continue
                    if NOTIFY_START_RE.match(text):
                        continue
                    if not COMPLAINT_RE.search(text):
                        continue
                    snippet = text[:280]
                    key = snippet.lower()[:120]
                    if key in seen:
                        continue
                    seen.add(key)
                    ts = (o.get("timestamp") or "")[:10]
                    hits.append((ts, snippet))
        except OSError:
            continue
    return scanned


def mine(cwd, days, scan_all, limit):
    cutoff = datetime.datetime.now().timestamp() - days * 86400
    dirs = all_project_dirs() if scan_all else [d for d in [transcript_dir(cwd)] if d]
    hits, seen, scanned = [], set(), 0
    for d in dirs:
        scanned += mine_dir(d, cutoff, seen, hits)
    hits.sort(key=lambda h: h[0], reverse=True)
    return hits[:limit], scanned, dirs


def main():
    ap = argparse.ArgumentParser(description="Mine Claude Code transcripts for gripes.")
    ap.add_argument("--cwd", default=os.getcwd(), help="Project whose transcripts to mine.")
    ap.add_argument("--days", type=int, default=60, help="How far back to look (days).")
    ap.add_argument("--limit", type=int, default=60, help="Max snippets to return.")
    ap.add_argument("--all", action="store_true", help="Mine every project, not just --cwd.")
    ap.add_argument("--count-only", action="store_true", help="Print a one-line count, not JSON.")
    a = ap.parse_args()

    hits, scanned, dirs = mine(a.cwd, a.days, a.all, a.limit)

    if a.count_only:
        # Silence over noise: print nothing when there's nothing worth surfacing.
        if hits:
            print(f"gripe-miner: {len(hits)} complaint(s) across {scanned} session(s) "
                  f"in the last {a.days} days - run /gripe-miner to triage.")
        return

    if not dirs:
        print(json.dumps({
            "gripes": [], "scanned_sessions": 0, "project": os.path.abspath(a.cwd),
            "note": "No Claude Code transcript folder found for this project. "
                    "Try --all, or check ~/.claude/projects.",
        }, indent=2))
        return

    print(json.dumps({
        "gripes": [{"date": ts, "text": s} for ts, s in hits],
        "scanned_sessions": scanned,
        "project": os.path.abspath(a.cwd),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
