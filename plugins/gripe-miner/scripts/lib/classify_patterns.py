"""Session Patterns classifier (v0) — detects repeating loops in human-typed
Claude Code messages: the same stuck point, the same re-explaining, the same
"I'll fix that later", the same re-setup.

Invented from the Session Patterns one-pager themes (no shipped product to
extract regex from yet, unlike the gripe classifier) — expect this to need
tuning once it sees real triage results. Reuses the gripe classifier's noise
filters so shell-command lines and task-notification payloads don't pollute
either lens the same way.
"""
import re

from .classify_gripes import NOISE_RE, NOTIFY_START_RE

# Theme -> regex. Order matters only for which label wins when a message could
# plausibly match more than one; first match wins.
THEMES = (
    ("stuck", re.compile(
        r"\b("
        r"same (?:error|issue|problem|bug)|still (?:broken|not working|failing)|"
        r"keeps? failing|back to this (?:same\s+)?(?:issue|error|problem|bug)?|"
        r"this again|same (?:break|thing) (?:again|as before)|keeps? happening"
        r")\b",
        re.IGNORECASE,
    )),
    ("missing-context", re.compile(
        r"\b("
        r"as i said|as i mentioned|i (?:already|just) told you|i (?:already )?mentioned (?:this|that)|"
        r"remember (?:that|when|i said)|you forgot|re-?explain|start over|"
        r"like i said|i told you (?:this|that) (?:already|before)"
        r")\b",
        re.IGNORECASE,
    )),
    ("deferral", re.compile(
        r"\b("
        r"i'?ll fix (?:that|this|it)(?: later)?|fix (?:that|this|it) later|"
        r"for now|\btodo\b|workaround|temporary (?:fix|hack|solution)|"
        r"come back to (?:this|that)|skip (?:this|that|it) for now|"
        r"leave (?:it|this|that) for (?:now|later)|deal with (?:it|this|that) later"
        r")\b",
        re.IGNORECASE,
    )),
    ("reteach", re.compile(
        r"\b("
        r"set ?up again|reinstall|reconfigure|have to redo|do this every time|"
        r"every monday|every time i open|redo this (?:again|every time)|"
        r"start from scratch again"
        r")\b",
        re.IGNORECASE,
    )),
)


def classify(text):
    """Return (theme, dedupe_key) if `text` reads as a recurring-pattern candidate,
    else None. Dedupe key is theme-scoped so the same phrase under two themes
    (shouldn't normally happen — first match wins) doesn't collide."""
    if NOISE_RE.match(text) or NOTIFY_START_RE.match(text):
        return None
    for theme, rx in THEMES:
        if rx.search(text):
            return (theme, f"{theme}:{text.lower()[:100]}")
    return None
