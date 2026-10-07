"""Shared Claude Code transcript access for both miners (gripes + session patterns).

No classification lives here — this only locates a project's transcript folder and
walks the human-typed messages inside it. mine_gripes.py and mine_patterns.py each
supply a `classify(text) -> (label, dedupe_key) | None` callback that decides what
counts for their lens.

Stdlib only. Reads nothing but local ~/.claude transcripts. No network calls.
"""
import glob
import json
import os
import re


def strip_injections(text):
    """Remove harness/system-injected tag blocks that get prepended to user turns,
    so classifiers only see what the human actually typed."""
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


def mine(dirs, cutoff, classify):
    """Walk every project dir, run `classify(text)` on each genuinely human-typed
    message, and collect what it keeps.

    classify(text) must return None (skip) or a (label, dedupe_key) tuple — label
    is lens-specific (e.g. a pattern theme, or None for gripes), dedupe_key groups
    near-duplicates so only the first occurrence is kept.

    Returns (hits, scanned) where hits is a list of (timestamp, snippet, label),
    newest-file-scanned-first is NOT guaranteed — callers sort/limit themselves.
    """
    hits, seen, scanned = [], set(), 0
    for tdir in dirs:
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
                        if not text or len(text) < 12:
                            continue
                        result = classify(text)
                        if result is None:
                            continue
                        label, key = result
                        if key in seen:
                            continue
                        seen.add(key)
                        ts = (o.get("timestamp") or "")[:10]
                        hits.append((ts, text[:280], label))
            except OSError:
                continue
    return hits, scanned
