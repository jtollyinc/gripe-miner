# Gripe Miner — product spec (dev plugin + consumer extension)

*Captured 2026-07-12. One insight — "your AI chat history is a log of everything
that frustrates you" — shipped as two products for two audiences.*

---

## The insight

Claude Code (and ChatGPT, and Claude.ai) quietly stores every conversation you've
ever had. Buried in there is a running, honest record of every time you got
frustrated or wished something existed. Gripe Miner reads that back and turns it
into an actionable list. Same core idea, two very different shapes:

- **Dev version** — a Claude Code plugin. Reads your local transcripts, verifies
  each gripe against your code, writes a ranked fix queue.
- **Consumer version** — a browser extension. Reads your ChatGPT / Claude.ai
  history, surfaces recurring frustrations and wishes, exports a to-do list.
  100% local.

The origin is real code: the Weekend Scan in the UBM repo
(`.claude/hooks/weekend_scan.py`) already mines gripes from Claude Code
transcripts. The reusable IP is the complaint-detection regex + transcript parser;
everything else there is personal wiring (Telegram, FIXQUEUE, Task Scheduler).

---

## Part A — Gripe Miner (Claude Code plugin / dev)

### What was extracted from `weekend_scan.py`

| From weekend_scan.py | Action | Why |
|---|---|---|
| `COMPLAINT_RE`, `NOISE_RE`, `NOTIFY_START_RE` | Keep verbatim | The IP. Tuned gripe detection. |
| `strip_injections()`, `mine_complaints()` | Keep, generalize | Derive transcript dir from cwd, not hardcoded. |
| `build_weekly_prompt()` logic | Move into `SKILL.md` | "confirm, rank, precision over recall" becomes the skill body. |
| `run_claude()` subprocess spawn | Delete | A plugin runs *inside* the current session — no second `claude -p`. |
| Telegram helpers | Delete | Delivery = write a markdown file. |
| `append_to_fixqueue` / dedup | Keep, generalize | Output to a configurable `GRIPES.md`. |
| Monthly landscape mode | Drop | Different tool. |
| `register-scans.ps1` (Task Scheduler) | Replace | Optional Claude Code SessionStart hook, opt-in. |

### Structure (this repo)

```
gripe-miner/
├── .claude-plugin/
│   ├── plugin.json          plugin manifest
│   └── marketplace.json     single-plugin marketplace, source "."
├── SKILL.md                 single-skill-at-root → /gripe-miner
├── scripts/mine_gripes.py   extracted miner, stdlib-only, cross-platform
├── hooks/hooks.json.example opt-in start-of-session nudge (off by default)
├── docs/product-spec.md     this file
├── README.md · LICENSE · .gitignore
```

### Flow

`/gripe-miner` → the SKILL's `!` shell block runs `mine_gripes.py` (deterministic
regex mining, outputs JSON of candidate gripes into context) → the current session
verifies each against the code with Read/Grep/Glob, merges repeats, writes the top
3–5 to `GRIPES.md`, each line quoting the user's own words with a recurrence count.

### Distribution

```
/plugin marketplace add jtollyinc/gripe-miner
/plugin install gripe-miner@jtolly-tools
```

(Requires pushing this repo to GitHub as `jtollyinc/gripe-miner` first.)

### Demo video (~40s)

- **0–3s (hook):** black terminal — *"Claude Code secretly logs every time you got annoyed."*
- **3–6s:** *"So I built a plugin that reads them back."* Type `/gripe-miner`.
- **6–14s:** miner scrolls `scanned 43 sessions · found 12 gripes`; then Claude
  visibly Greps/Reads real files (the credibility beat — it checks, doesn't guess).
- **14–30s:** `GRIPES.md` opens; 4 checkboxes, each ending in your quoted words:
  *"…(you said: 'why does this keep resetting', x3)"*. Let the **x3** land.
- **30–40s (payoff + CTA):** *"It found the bug I complained about 3 times and never
  fixed."* Then the two install lines. *"Free. Link in bio."*

Build the edit around a single frame: a gripe with **x3** next to it.

---

## Part B — Gripe (consumer browser extension)

### The reframe

Consumers have no codebase. The product isn't "bugs" — it's **self-insight + a
to-do list mined from your AI chats**: *"You talk to ChatGPT more honestly than you
talk to anyone. This reads it back."* Names: Gripe / Hindsight / Sift / Afterthought.

### Architecture (reuses the ChatGPT-scrape tech already built for the Data Vault)

```
manifest v3 extension
├── content script  → reads chat.openai.com / claude.ai conversation DOM
├── worker          → same COMPLAINT_RE + strip logic, ported to JS
├── popup UI        → grouped: "Frustrations · Wishes · Recurring" + export
└── storage         → IndexedDB, 100% local
```

Two decisions that make or break it:
1. **Ship 100% local, no API key, day one.** Regex classifier runs in the browser;
   nothing uploads. For a consumer AI product that's the *headline feature*.
2. **Don't fight the DOM forever.** Offer both live-scrape (the demo wow) and
   "import your official export.zip" (the robust fallback). Live scraping is
   fragile — bake in the fallback from the start.

### Demo video (~40s)

- **0–4s (hook):** packed ChatGPT sidebar — *"Your ChatGPT history knows what
  frustrates you better than you do."*
- **4–8s:** click the extension icon; it sweeps chats — *"reading 200 chats… on your device."*
- **8–24s:** popup fills, grouped: *You keep wishing for* → "meal-plan around
  leftovers (asked 5×)"; *You keep struggling with* → "your sleep schedule (11 chats)".
- **24–32s:** cut to an empty Network tab — *"Nothing uploaded. Check yourself."*
- **32–40s:** one click → export to a to-do list. *"Free. Chrome store link below."*

### Risks
- DOM fragility (mitigated by export-import fallback).
- Chrome Web Store review scrutiny for reading ChatGPT history — defense: fully
  local + open source.
- Higher polish bar than a CLI; the popup needs a designer's eye.

---

## Dev vs. consumer

| | Gripe Miner (plugin) | Gripe (extension) |
|---|---|---|
| Audience | Claude Code devs — small, hungry, high-trust | ChatGPT users — enormous, casual |
| Net-new code | ~nothing; package what exists | scraper (have it) + JS port + real UI |
| Time to ship | a weekend | 2–3 weekends + store review |
| Distribution | marketplace (2 lines) | Chrome Web Store (reviewed) |
| Virality ceiling | low reach, high credibility | high reach, high polish-cost |
| Best content angle | "it caught the bug I ignored 3×" | "reads your chats, uploads nothing" |
| What it proves | you ship real dev tooling | you ship real *products* |

## Positioning — the "two markets" flex

The narrative is **"one insight → two products for two audiences."** That's a
product-thinking flex, not just a coding one: the same idea needs a different shape
for a dev vs. a consumer. A single post — *"I found one weird idea in my AI history
and turned it into two completely different products; here's how I decided what
changed"* — is itself strong content and makes both launches feel intentional.

## Sequencing

Ship the **plugin first** (this weekend): nearly free to build, gets you through the
whole build → publish → post loop once on low stakes, and the dev audience's trust
is the foundation for launch #2. Then the extension lands with the "…and here's the
same idea for everyone" hook already set up.

---

## Part C — combined plugin: Gripe Miner + Session Patterns (v0.2.0, 2026-10-07)

### Why combined, not a second marketplace plugin

The Session Patterns promo pack (`/opt/jollydesk/work/session-patterns-promo/`)
frames Session Patterns as a sibling product with *soft* ancestry to Gripe Miner —
own name, own one-pager, own CTA. Jaron overrode that for the plugin itself: one
install, two reinforcing lenses, more power per line of install instructions than
two separate marketplace entries would give a Claude Code user. The marketplace
identity stays `gripe-miner` (same `plugin.json` name, same GitHub repo target);
only user-facing copy (README, descriptions) says "Gripe Miner + Session Patterns."
If Session Patterns ever graduates to its own standalone pitch (site page, video),
that's a marketing decision layered on top — it doesn't require forking the plugin.

### What Session Patterns is, here

Not a shipped product being extracted (unlike Part A, which extracted real regex
from `weekend_scan.py`). The one-pager and 90s script describe a *promise*
("repeating themes: same stuck point, same missing context, same 'I'll fix that
later'") with no reference implementation. Part C's classifier (`classify_patterns.py`)
is a v0 invention from those themes, split into four regex-detected labels: `stuck`,
`missing-context`, `deferral`, `reteach`. Treat it as a first draft that needs tuning
against real triage results — the gripe classifier had years of real Weekend Scan
runs behind its regex; this one doesn't yet.

### Structure (added to the Part A layout)

```
plugins/gripe-miner/
├── .claude-plugin/plugin.json      version 0.2.0, description covers both lenses
├── skills/
│   ├── gripe-miner/SKILL.md        moved from plugin root (was single-skill-at-root)
│   ├── session-patterns/SKILL.md   new — mirrors gripe-miner's triage rigor
│   └── patterns/SKILL.md           new — unified: runs both, cross-links, merges
├── scripts/
│   ├── lib/
│   │   ├── transcripts.py          shared walker: transcript_dir, strip_injections, mine()
│   │   ├── classify_gripes.py      COMPLAINT_RE / NOISE_RE / NOTIFY_START_RE (moved verbatim)
│   │   └── classify_patterns.py    new — four theme regexes, reuses gripes' noise filters
│   ├── mine_gripes.py              thin CLI now, same flags/output as Part A
│   └── mine_patterns.py            new CLI, same flag surface, outputs {"patterns": [...]}
└── hooks/hooks.json.example        now nudges both miners' counts, still opt-in
```

Moving the sole `SKILL.md` out of the plugin root and under `skills/<name>/` was
required once a second and third skill needed to coexist — Claude Code's plugin
layout only supports one root-level `SKILL.md`. All three skills reference scripts
via `${CLAUDE_PLUGIN_ROOT}/scripts/...` (not `${CLAUDE_SKILL_DIR}`) so the path holds
regardless of which skill's directory is resolved.

### Reinforcement — the mechanism, concretely

`/patterns` runs both miners, triages each list with the same per-item rigor as the
solo skills (verify against code, check `git log` for fixes, drop stale leads), then
does one more pass: read both triaged lists and look for a gripe and a pattern that
point at the same area (same file/feature/symptom). That's a **model judgment call**,
not a script step — "same area" isn't reliably regex-matchable across two
differently-worded snippets. Matches get promoted to a `Reinforced` section, ranked
above either lens alone, citing both the gripe quote and the pattern's recurrence
count. This is documented as a known soft spot: no automated test can verify the
cross-link logic beyond "does the skill body instruct it correctly," since the
judgment happens inside a live Claude session, not in `mine_patterns.py`.

### Open questions for Jaron

- Tune `classify_patterns.py`'s four regexes once real `/session-patterns` runs
  produce false positives/negatives — v0 is a best-guess from the one-pager, not
  measured against real transcripts the way the gripe regex was.
- Decide whether Session Patterns ever gets its own marketing moment (the promo pack
  still exists, untouched, at `/opt/jollydesk/work/session-patterns-promo/`) separate
  from "it's a mode of Gripe Miner."

---

## Part D — third lens: "Automate this" (v0.3.0, 2026-10-07)

### The ask, verbatim

> "can we have it go as far as suggesting tools or routines or automations for
> things a user keeps asking for and burning lots of tokens, I think that's where
> this could really be useful."

Gripes say what annoyed you; patterns say what keeps recurring; this lens says
what it *costs* — and what to build so you stop paying it.

### What the transcripts actually contain (verified, not assumed)

- Every assistant line carries `message.usage.{input_tokens, output_tokens,
  cache_creation_input_tokens, cache_read_input_tokens}` plus a
  `cache_creation.{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}` split.
  On the build machine 17,132 of 17,132 assistant lines had it.
- Claude Code writes one JSONL line per streamed content block. 5,730 of 8,456
  message ids spanned more than one line (up to 19), and every line of the same
  id carried an identical usage snapshot — so dedup by `message.id` is both
  necessary and sufficient. Fallbacks: `requestId`, then the line `uuid`.
- Each user turn is tagged `promptSource` (`typed` / `sdk` / `system`) and
  `turnOrigin` (`human` / `sdk` / `task_notification` / `peer`) — seen on Claude
  Code 2.1.258 and 2.1.278; when the tags were introduced is not known. Untagged
  turns on those versions were all harness-generated (image captions, token-limit
  notices); on older versions they could be anything.
- A `cost-state` line per session carries Claude Code's own per-model totals. The
  miner's per-session sums matched it exactly in 705 of 738 sessions and never
  exceeded it (the under-counts are subagent transcripts, which are not walked).

### Pipeline (added to the Part C layout)

```
scripts/
├── lib/
│   ├── transcripts.py      + prompt_origin(), iter_prompts()  — mine() untouched
│   └── classify_asks.py    gates → normalise → cluster → score
├── mine_asks.py            CLI, same flag surface as its siblings + --min-sessions, --include-scripted
skills/
├── automate/SKILL.md       /automate → AUTOMATIONS.md
└── patterns/SKILL.md       now runs all three, adds "Automate this" section
```

`iter_prompts()` yields one record per user prompt with the usage of every
assistant message up to the next prompt attached. Tool results, sidechain prompts
and harness turns don't start a new record, so their follow-on usage stays with
the human prompt that caused it. A turn without usage is estimated at
`len(text)//4` output tokens and flags the record `estimated`.

`classify_asks` runs three gates (origin → shape → content), normalises (lowercase;
strip URLs, paths, ids, numbers, punctuation; drop function words but keep action
verbs — the verb *is* the ask), then clusters greedily: a prompt joins a cluster
when its first six significant words match in order (a templated opener with a
variable payload is one routine) or when Jaccard over significant words against
the cluster's first member is ≥ 0.6. Clusters survive only across ≥ 3 distinct
sessions (configurable). Score = `count × weighted`, where `weighted` is
input-token equivalents at list-price ratios (output ×5, cache write ×1.25 or ×2
for the 1-hour TTL, cache read ×0.1) — documented in the JSON itself under
`weighting` and `score`.

### Scripted prompts are a cost finding, not a candidate

Prompts tagged `sdk` were sent by a script, a cron job or `claude -p` — they are
already automations, so suggesting to automate them is circular. They are skipped
by default (`prompts.skipped.scripted` says how many) and included with
`--include-scripted` as `"scripted": true` clusters, which the skill may report
under "Routines and what they cost" (cheaper model, tighter prompt, fewer runs)
but never as an automation suggestion. On the build machine this distinction was
the whole ballgame: 901 of 1,292 prompts in the window were script-sent, 3 were
human-typed, and the two biggest routines fired 240 and 44 times.

### The suggestion step

`/automate` triages like its siblings (one ask? already automated? still
applies?) and then picks the first row of a fixed table that fully covers the
ask: CLAUDE.md line → script/CLI → skill → hook → scheduled routine → MCP, in
that order because cheaper and more durable comes first and no-model beats model.
Every suggestion carries the user's own words with count and sessions, the tokens
burned so far (marked estimated when flagged), the fix type and why, a concrete
sketch, and a savings figure that is always labeled an estimate with its
assumption shown (observed rate × assumed per-ask reduction: 30–50 % for a skill
or CLAUDE.md line, 90 %+ when the model leaves the loop). Suggest-only: the skill
never edits settings, hooks, crontabs or CLAUDE.md, and writes a draft
`.claude/skills/<name>/SKILL.md` only after an explicit yes in the next message.

### Cross-boost in /patterns

Model judgment, not script. A script-level join was considered and rejected: the
three JSON lists sit side by side in context, and word overlap between a gripe
and an ask is a hint the model can already see, not a proof worth encoding. The
rule the skill applies: an ask that matches a gripe or a `stuck` / `reteach` /
`missing-context` pattern in the same area ranks first under "Automate this", and
the pattern picks the fix type (re-teach + repeated ask → CLAUDE.md line; stuck +
repeated ask → script or hook).

### Open questions for Jaron

- The default excludes script-sent prompts. On a box like jollyserver, where
  almost everything arrives via claude-job, `/automate` will mostly say "nothing
  repeats" — the interesting view there is `--include-scripted`. Should the skill
  auto-fall-back to that mode when `prompts.eligible` is tiny?
- Subagent spend and the 4,000-character paste cap both make totals floors. Worth
  lifting either once a real `/automate` run shows it matters.
- Thresholds (Jaccard 0.6, six-word template opener, three sessions) were set for
  precision on synthetic and this box's data, not tuned on a laptop full of
  genuinely typed prompts. First real run on jtollygr is the tuning data.
