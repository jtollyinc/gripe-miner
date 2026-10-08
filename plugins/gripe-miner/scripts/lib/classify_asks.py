"""Repeated-ask clustering — the "Automate this" lens (v0.3.0).

Finds prompts a person keeps typing across sessions and sums the token usage
spent answering each, so a cluster can be scored by frequency x cost and handed
to /automate as an automation candidate.

Stdlib only, local-only, no network. Precision over recall throughout: a missed
repeat costs nothing, a false "you keep asking for this" costs trust.

Three gates run before clustering, in this order:

1. origin  — Claude Code tags every user turn with promptSource / turnOrigin
             (see transcripts.prompt_origin). Turns the harness wrote itself
             (notifications, peer-agent messages, image captions, resume
             nudges) are never asks. Turns sent by a script (`claude -p`, the
             Agent SDK, a cron job) and slash-command invocations (origin
             "command": /deep-research, /commit ...) are ALREADY automated, so
             they are skipped by default and only clustered with
             include_scripted=True, where the cluster is flagged "scripted" so
             the skill talks about that routine's cost instead of proposing to
             automate an automation. Untagged turns (older Claude Code
             versions) fall back to the text-shape test SCRIPTED_SHAPE_RE.
2. shape   — pure acknowledgements ("yes", "ok", "continue") are not asks, and
             giant pastes (briefs, specs, logs) over GIANT_PASTE_CHAR_CAP are
             not something anyone retypes.
3. content — after normalisation (lowercase; strip URLs, paths, ids, numbers,
             punctuation; drop function words) a prompt must keep at least one
             significant word to cluster on.

Clustering is greedy single-pass. A prompt joins an existing cluster when
either test passes, else it starts a new one:
  - template: its first TEMPLATE_PREFIX_WORDS significant words, in order, equal
    the cluster's — the same opener with a different payload pasted after it
    (an email to classify, a roadmap item to review) is one routine, not many;
  - similarity: Jaccard over the whole significant-word set against the
    cluster's anchor (its FIRST member's set) is >= JACCARD_THRESHOLD.
Anchors never grow, so clusters can't drift wider than the threshold allows.
Single-word prompts therefore only cluster with identical single-word prompts.
"""
import re
from collections import Counter

from .classify_gripes import NOTIFY_START_RE

# NOTE: classify_gripes.NOISE_RE (lines starting "commit", "git ", "run ", "npm ",
# "python " ...) is deliberately NOT applied here. For the gripe lens a shell
# command is noise; for this lens "run the tests" typed twenty times is exactly
# the signal we want.

# --- gate 2: shape -----------------------------------------------------------

GIANT_PASTE_CHAR_CAP = 4000

# Harness-written text that reaches the transcript as a "user" turn. Always
# dropped, whatever the origin tag says. Built from the prefixes actually seen
# on real transcripts, not guessed. The resume nudge has been reworded across
# Claude Code versions ("Your response above was stopped by the token limit",
# "...was stopped by a safety classifier", "...was cut off mid-stream. Resume
# directly from where it stops"), so that branch matches the sentence shape —
# "your response/reply/output (above) was|got|has been stopped|cut off|
# interrupted|truncated" — rather than one wording. It is anchored at the start
# and needs the "your response ... was <halted>" frame, so "your response above
# was good, now add tests" or "cut off the trailing whitespace" stay asks.
INJECTED_RE = re.compile(
    r"^(?:\[image:|\[request interrupted|output token limit hit|"
    r"your (?:response|reply|output|answer|message)(?: above| earlier| so far)?"
    r" (?:was|got|has been|is being) (?:stopped|cut off|interrupted|truncated|halted)|"
    r"(?:the|your) (?:previous|last|prior) (?:response|reply|output|message) was (?:cut off|truncated|interrupted)|"
    r"another claude session sent a message|"
    r"this session is being continued from a previous conversation|"
    r"base directory for this skill:|caveat: the messages below|"
    r"api error|<task-notification>|<agent-message)",
    re.IGNORECASE,
)

# Text-shape stand-in for the origin tag on transcripts that don't carry one:
# role-prompt preambles, markdown-headed briefs, probe/health-check phrasing,
# "STOP — before this counts as done" self-review injections. A person opening
# an interactive message with "# Title" or "You are a..." is rare enough that
# losing the odd one is the right precision-over-recall trade.
SCRIPTED_SHAPE_RE = re.compile(
    r"^(?:#{1,6}\s|=+\s|you are (?:a|an|the|claude|on|running|reviewing|acting|now|working|operating)\b|"
    r"(?:reply|respond|answer) with (?:exactly|only)\b|stop\s*[—–-]+\s*before|"
    r"(?:job|task|brief|persona|system prompt)\s*(?:id)?\s*[:—–-])",
    re.IGNORECASE,
)

# Pure acknowledgements — not an ask, never worth clustering. Only consulted on
# short texts, so the repetition can't backtrack on anything long.
ACK_RE = re.compile(
    r"^(?:(?:yes|yep|yeah|ya|y|ok|okay|k|kk|sure|fine|good|great|cool|nice|perfect|right|correct|"
    r"go|go ahead|go for it|do it|ship it|continue|proceed|next|keep going|carry on|resume|"
    r"sounds good|looks good|lgtm|approved|agreed|thanks|thank you|thx|ty|no|nope|nah|"
    r"please|yes please|please continue|please proceed|"
    r"(?:please )?(?:continue|resume|pick up|carry on)(?: from)? where you left off|"
    r"(?:please )?(?:continue|resume) from where (?:it|you) (?:stopped|stops|left off))"
    r"[\s.!,]*)+$",
    re.IGNORECASE,
)
ACK_MAX_CHARS = 60

# --- gate 3: content ---------------------------------------------------------

_URL_RE = re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.IGNORECASE)
_UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
# Drive-letter or ~/ paths of any depth; POSIX absolute paths only when they have
# >= 2 segments, so a slash command like "/deploy" survives as the word "deploy".
_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|~/)[\w.\\/-]*|/[\w.-]+(?:/[\w.-]+)+")
_HEX_RE = re.compile(r"\b[0-9a-f]{7,}\b", re.IGNORECASE)  # commit hashes, ids
_NUM_RE = re.compile(r"\b\d+(?:[.,:]\d+)*\b")
_APOS_RE = re.compile(r"['’`]")
_NONWORD_RE = re.compile(r"[^a-z\s]")

# Function words, politeness and feedback words that carry no ask. Action verbs
# (run, check, show, fix, deploy, build, test, commit, push, update ...) are kept
# on purpose — the verb IS the ask.
STOPWORDS = frozenset("""
a an the and or but if then than so as of to in on at by for from with without into
onto over under up down out off about around through between after before during while
until again further once here there where when why how what which who whom whose this
that these those is are was were be been being am do does did doing have has had having
will would shall should can could may might must i me my mine myself we us our ours you
your yours he him his she her hers it its itself they them their theirs im ive id ill
youre youve youd youll weve theyre theyve thats whats heres theres lets isnt arent wasnt
werent dont doesnt didnt wont wouldnt cant cannot couldnt shouldnt havent hasnt hadnt
not no nor yes yeah yep ok okay please pls thanks thank thx just also too very really
quite still even only some any all both each every either neither more most much many
few little own same other another such ever never always often sometimes now already
yet soon ago sure fine good great cool nice right well hey hi hello want wants wanted
need needs needed like likes rather able go going gonna get got gets getting let
""".split())

MIN_SIGNIFICANT_CHARS = 2


def normalize(text):
    """Canonical form used for clustering identity only; display keeps the original."""
    t = text.lower()
    t = _URL_RE.sub(" ", t)
    t = _UUID_RE.sub(" ", t)
    t = _PATH_RE.sub(" ", t)
    t = _HEX_RE.sub(" ", t)
    t = _NUM_RE.sub(" ", t)
    t = _APOS_RE.sub("", t)
    t = _NONWORD_RE.sub(" ", t)
    return " ".join(t.split())


def significant_words(norm):
    return frozenset(w for w in norm.split() if w not in STOPWORDS and len(w) >= MIN_SIGNIFICANT_CHARS)


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# Prompts whose first N significant words match in order share an opener — the
# fingerprint of a template. Six is long enough that two different asks almost
# never share it, short enough to sit before the variable payload begins.
TEMPLATE_PREFIX_WORDS = 6


def template_key(norm):
    """The ordered first TEMPLATE_PREFIX_WORDS significant words, or None when the
    prompt is too short to have an opener worth matching on."""
    words = [w for w in norm.split() if w not in STOPWORDS and len(w) >= MIN_SIGNIFICANT_CHARS]
    if len(words) < TEMPLATE_PREFIX_WORDS:
        return None
    return tuple(words[:TEMPLATE_PREFIX_WORDS])


def ineligible_reason(prompt, include_scripted=False):
    """Why this prompt can't be an ask to automate, or None if it can.
    Also decides prompt["scripted"] (True when a script, not a person, sent it,
    or when it is a slash command — already automated either way)."""
    text = prompt["text"].lstrip("\ufeff").strip()
    origin = prompt.get("origin", "unknown")
    prompt["scripted"] = origin in ("scripted", "command")
    if origin == "command":
        # A slash command (/deep-research, /commit ...) is an automation that
        # already exists; its expanded body never reaches here (transcripts
        # folds it into this record). Clustered only on request, as a cost line.
        return None if include_scripted else "command"
    if origin == "injected" or INJECTED_RE.match(text) or NOTIFY_START_RE.match(text):
        return "injected"
    if origin == "unknown" and SCRIPTED_SHAPE_RE.match(text):
        prompt["scripted"] = True
    if prompt["scripted"] and not include_scripted:
        return "scripted"
    if len(text) > GIANT_PASTE_CHAR_CAP:
        return "too_long"
    if len(text) <= ACK_MAX_CHARS and ACK_RE.match(text):
        return "ack"
    return None


# --- clustering ----------------------------------------------------------------

JACCARD_THRESHOLD = 0.6


def cluster(prompts, include_scripted=False):
    """Group eligible prompts into clusters of near-identical asks.

    Returns (clusters, stats). Each cluster is {"anchor": frozenset, "members": [...]};
    stats counts what was considered and why prompts were skipped.
    """
    clusters = []
    index = {}  # significant word -> [cluster index, ...] (anchor words only)
    templates = {}  # template_key -> cluster index of the first cluster opened with it
    stats = {"total": 0, "eligible": 0,
             "skipped": {"injected": 0, "scripted": 0, "command": 0, "too_long": 0, "ack": 0, "too_short": 0}}
    for p in prompts:
        stats["total"] += 1
        reason = ineligible_reason(p, include_scripted)
        if reason:
            stats["skipped"][reason] += 1
            continue
        norm = normalize(p["text"])
        sig = significant_words(norm)
        if not sig:
            stats["skipped"]["too_short"] += 1
            continue
        stats["eligible"] += 1
        p["norm"] = norm
        tkey = template_key(norm)
        if tkey is not None and tkey in templates:
            clusters[templates[tkey]]["members"].append(p)
            continue
        candidates = set()
        for w in sig:
            candidates.update(index.get(w, ()))
        best_idx, best_sim = None, 0.0
        for ci in candidates:
            sim = _jaccard(sig, clusters[ci]["anchor"])
            if sim > best_sim:
                best_sim, best_idx = sim, ci
        if best_idx is not None and best_sim >= JACCARD_THRESHOLD:
            clusters[best_idx]["members"].append(p)
        else:
            clusters.append({"anchor": sig, "members": [p]})
            ci = len(clusters) - 1
            for w in sig:
                index.setdefault(w, []).append(ci)
            if tkey is not None:
                templates.setdefault(tkey, ci)
    return clusters, stats


# --- scoring -------------------------------------------------------------------

# Cost weighting, in "input-token equivalents". Ratios are Anthropic's list-price
# ratios: output costs 5x input on every current model; a prompt-cache write costs
# 1.25x (5-minute TTL) or 2x (1-hour TTL, which Claude Code uses); a cache read
# costs ~0.1x. Raw totals are still reported alongside — this only drives `score`
# and the `weighted` figure, so cheap cache reads (which dominate raw volume)
# don't outrank genuinely expensive asks.
WEIGHTS = {"input": 1.0, "output": 5.0, "cache_create_5m": 1.25, "cache_create_1h": 2.0, "cache_read": 0.1}


def weighted_tokens(u):
    cc_1h = min(u["cache_create_1h"], u["cache_create"])
    cc_5m = u["cache_create"] - cc_1h
    return int(round(
        u["input"] * WEIGHTS["input"]
        + u["output"] * WEIGHTS["output"]
        + cc_5m * WEIGHTS["cache_create_5m"]
        + cc_1h * WEIGHTS["cache_create_1h"]
        + u["cache_read"] * WEIGHTS["cache_read"]
    ))


def usage_totals(prompts):
    """Sum usage over any iterable of prompt records into the public tokens shape."""
    t = {"input": 0, "output": 0, "cache_create": 0, "cache_create_1h": 0, "cache_read": 0}
    for p in prompts:
        for k in t:
            t[k] += p["usage"][k]
    t["fresh"] = t["input"] + t["output"] + t["cache_create"]
    t["total"] = t["fresh"] + t["cache_read"]
    t["weighted"] = weighted_tokens(t)
    return t


def _one_line(text, limit):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def summarize(clusters, min_sessions=3, limit=15):
    """Keep clusters spanning >= min_sessions distinct sessions, score them, and
    return the top `limit` as plain dicts ready for JSON.

    score = count x weighted tokens. Because `weighted` already sums over every
    occurrence, frequency effectively counts twice — deliberately, so something
    asked twenty times outranks one expensive job asked three times.
    """
    out = []
    for c in clusters:
        members = c["members"]
        sessions = {m["session"] for m in members}
        if len(sessions) < min_sessions:
            continue
        projects = {m["project"] for m in members}
        dates = sorted(m["date"] for m in members if m["date"])
        tokens = usage_totals(members)

        # Representative = the most common normalised wording, shown via its
        # shortest original; examples = up to 3 distinct wordings.
        forms = Counter(m["norm"] for m in members)
        top_form, top_n = forms.most_common(1)[0]
        pool = members if top_n == 1 else [m for m in members if m["norm"] == top_form]
        rep = min((m["text"] for m in pool), key=len)
        examples, seen_forms = [], set()
        for m in sorted(members, key=lambda m: (m["norm"] != top_form, len(m["text"]))):
            if m["norm"] in seen_forms:
                continue
            seen_forms.add(m["norm"])
            examples.append(_one_line(m["text"], 160))
            if len(examples) >= 3:
                break

        models = Counter()
        for m in members:
            models.update(m["models"])
        scripted_members = sum(1 for m in members if m.get("scripted"))

        out.append({
            "id": None,
            "representative": _one_line(rep, 200),
            "examples": examples,
            "count": len(members),
            "sessions": len(sessions),
            "projects": len(projects),
            "first_seen": dates[0] if dates else None,
            "last_seen": dates[-1] if dates else None,
            "turns": sum(m["turns"] for m in members),
            "models": [name for name, _ in models.most_common(5)],
            "tokens": tokens,
            "tokens_estimated": any(m["estimated"] for m in members),
            "scripted": scripted_members * 2 > len(members),
            "score": len(members) * tokens["weighted"],
        })
    out.sort(key=lambda c: (-c["score"], -c["count"], c["representative"]))
    out = out[:limit]
    for i, c in enumerate(out, start=1):
        c["id"] = f"ask-{i}"
    return out
