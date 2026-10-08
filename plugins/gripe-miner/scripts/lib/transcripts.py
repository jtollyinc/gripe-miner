"""Shared Claude Code transcript access for all three miners (gripes, session
patterns, repeated asks).

No classification lives here — this only locates a project's transcript folder and
walks the human-typed messages inside it. mine_gripes.py and mine_patterns.py each
supply a `classify(text) -> (label, dedupe_key) | None` callback that decides what
counts for their lens. mine_asks.py uses iter_prompts() instead, which also carries
each prompt's token usage and origin metadata.

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


# ---------------------------------------------------------------------------
# "Automate this" lens support (v0.3.0). Additive only: nothing above changed.
# ---------------------------------------------------------------------------

def prompt_origin(record):
    """Classify a user-turn JSONL record by the metadata Claude Code writes on it,
    without looking at the text.

    Returns one of:
      "human"    — a person typed it (turnOrigin "human" or promptSource "typed")
      "scripted" — sent programmatically: `claude -p`, the Agent SDK, a cron job
                   (promptSource "sdk")
      "injected" — written by the harness itself: task notifications, peer-agent
                   messages, other system-sourced turns
      "unknown"  — the record carries neither field. Older Claude Code versions
                   never wrote them, and current ones omit them on some turns the
                   harness generates (image captions, token-limit notices), so
                   callers must fall back to a text test for this bucket.

    Field names and values verified against real transcripts written by Claude
    Code 2.1.258 and 2.1.278 (promptSource: typed/sdk/system; turnOrigin:
    human/sdk/task_notification/peer).
    """
    turn_origin = record.get("turnOrigin")
    prompt_source = record.get("promptSource")
    if turn_origin == "human" or prompt_source == "typed":
        return "human"
    if turn_origin in ("task_notification", "peer") or prompt_source == "system":
        return "injected"
    if prompt_source == "sdk" or turn_origin == "sdk":
        return "scripted"
    return "unknown"


def _typed_text(content):
    """The readable text of a user turn, or None when it isn't a prompt at all.
    String content is a typed message. A list is accepted only when every block is
    a text block (some SDK clients send prompts that way); anything carrying a
    tool_result is the harness feeding a tool's output back, not a new prompt."""
    if isinstance(content, str):
        return content
    if isinstance(content, list) and content:
        parts = []
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                return None
            parts.append(block.get("text") or "")
        return "\n".join(parts)
    return None


def _text_chars(content):
    if isinstance(content, str):
        return len(content)
    chars = 0
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                chars += len(block["text"])
    return chars


def new_usage():
    """One prompt's attributed token usage, split the way the API reports it.
    cache_create_1h is the subset of cache_create written with the 1-hour TTL
    (billed 2x instead of 1.25x) — kept separate so cost weighting can be exact."""
    return {"input": 0, "output": 0, "cache_create": 0, "cache_create_1h": 0, "cache_read": 0}


def iter_prompts(dirs, cutoff):
    """Walk every project dir and yield one record per user prompt, carrying the
    token usage of every assistant message that followed it up to the next prompt.

    Yielded dict: {"project", "session", "timestamp", "date", "origin", "text",
    "usage": new_usage(), "turns", "models": set(), "estimated"}.

    How attribution works, and the three traps it avoids:
    - Usage comes from message.usage on assistant lines (input_tokens,
      output_tokens, cache_creation_input_tokens, cache_read_input_tokens, plus
      the cache_creation.ephemeral_1h_input_tokens breakdown) — names verified
      against real transcripts, not assumed.
    - Claude Code writes one JSONL line per streamed content block, all sharing
      the same message.id and the SAME usage snapshot (verified: 0 differing
      snapshots across 8,456 message ids on this box, up to 19 lines per id).
      Each id is counted once per session file; requestId / line uuid are the
      fallbacks when message.id is missing.
    - Tool results and harness-generated turns (image captions, notifications,
      sidechain prompts) do NOT start a new prompt: their follow-on usage stays
      with the human prompt that caused it. API-error lines carry zero usage and
      are skipped entirely.
    - A turn with no usage field at all is estimated at len(text)//4 output
      tokens and the record is flagged "estimated" so nothing exact-looking is
      ever fabricated. Usage before the first prompt in a file (resumed
      sessions) has nothing to attach to and is dropped, so totals are a floor.
    - Subagent transcripts (<session>/subagents/*.jsonl) are not walked; their
      spend is not attributed. Also a floor.

    Every prompt is yielded regardless of origin — callers decide what counts.
    """
    for tdir in dirs:
        for path in glob.glob(os.path.join(tdir, "*.jsonl")):
            try:
                if os.path.getmtime(path) < cutoff:
                    continue
            except OSError:
                continue
            session_id = os.path.splitext(os.path.basename(path))[0]
            current = None
            seen_ids = set()
            try:
                with open(path, encoding="utf-8") as fh:
                    for line in fh:
                        if '"user"' not in line and '"assistant"' not in line:
                            continue
                        try:
                            o = json.loads(line)
                        except (json.JSONDecodeError, ValueError):
                            continue
                        otype = o.get("type")
                        msg = o.get("message") or {}
                        if otype == "user":
                            if o.get("isSidechain") or "toolUseResult" in o:
                                continue
                            if msg.get("role") != "user":
                                continue
                            raw = _typed_text(msg.get("content"))
                            if raw is None:
                                continue
                            text = strip_injections(raw).strip()
                            if not text or len(text) < 12:
                                continue
                            if current is not None:
                                yield current
                            ts = o.get("timestamp") or ""
                            current = {
                                "project": tdir,
                                "session": session_id,
                                "timestamp": ts,
                                "date": ts[:10],
                                "origin": prompt_origin(o),
                                "text": text,
                                "usage": new_usage(),
                                "turns": 0,
                                "models": set(),
                                "estimated": False,
                            }
                        elif otype == "assistant":
                            if current is None or o.get("isApiErrorMessage"):
                                continue
                            key = msg.get("id") or o.get("requestId") or o.get("uuid")
                            if key in seen_ids:
                                continue
                            seen_ids.add(key)
                            current["turns"] += 1
                            model = msg.get("model")
                            if model:
                                current["models"].add(model)
                            usage = msg.get("usage")
                            if isinstance(usage, dict):
                                u = current["usage"]
                                u["input"] += usage.get("input_tokens") or 0
                                u["output"] += usage.get("output_tokens") or 0
                                u["cache_create"] += usage.get("cache_creation_input_tokens") or 0
                                breakdown = usage.get("cache_creation")
                                if isinstance(breakdown, dict):
                                    u["cache_create_1h"] += breakdown.get("ephemeral_1h_input_tokens") or 0
                                u["cache_read"] += usage.get("cache_read_input_tokens") or 0
                            else:
                                current["usage"]["output"] += _text_chars(msg.get("content")) // 4
                                current["estimated"] = True
                if current is not None:
                    yield current
            except OSError:
                continue
