"""Gripe classifier — tuned regex detection of genuine usability complaints in
human-typed Claude Code messages. Extracted verbatim from the original
mine_gripes.py so detection behavior doesn't drift; this is the reusable IP."""
import re

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


def classify(text):
    """Return (None, dedupe_key) if `text` reads as a genuine gripe, else None.
    Label is always None — gripes don't carry a theme, unlike pattern candidates."""
    if NOISE_RE.match(text) or NOTIFY_START_RE.match(text):
        return None
    if not COMPLAINT_RE.search(text):
        return None
    return (None, text.lower()[:120])
