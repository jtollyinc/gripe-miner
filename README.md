# Gripe Miner + Session Patterns + Automate

**Claude Code secretly logs every time you got frustrated, every time you hit the
same wall twice — and every prompt you keep retyping by hand. This reads all three
back.**

One plugin, three reinforcing lenses over the same local transcript mine:

- **Gripes** — the moments you actually complained: *"why does this keep
  resetting"*, *"this is so slow"*, *"I wish it just did X"*.
- **Session Patterns** — the loops that keep repeating even when you never said a
  word about it: the same error coming back, the same thing you keep re-explaining,
  the same "I'll fix that later" you never did, the same setup you redo every time.
- **Automate this** — the asks you keep typing across sessions, with the tokens
  they've burned so far, each paired with the cheapest durable fix: a skill, a
  hook, a script, a scheduled routine, a `CLAUDE.md` line, or an MCP connector.

Each candidate gets verified against your real code (and your existing skills,
hooks and scripts) before it reaches you — leads, not a to-do list. Run them
together and anything that shows up in more than one lens gets ranked higher,
because you both complained about it *and* kept hitting it *and* kept paying for it.

It is deliberately **quiet**: precision over recall, an empty result is a valid
answer, and it never pads the list.

---

## Install

```
/plugin marketplace add jtollyinc/gripe-miner
/plugin install gripe-miner@jtolly-tools
```

### Testing from this clone (not yet pushed)

This checkout hasn't been pushed to GitHub yet, so point the marketplace at the
local path instead:

```
/plugin marketplace add /opt/jollydesk/work/session-patterns-combined-20261007/gripe-miner
/plugin install gripe-miner@jtolly-tools
```

Then, in any project:

```
/gripe-miner          # gripes only → GRIPES.md
/session-patterns     # patterns only → PATTERNS.md
/automate             # repeated asks + token burn → AUTOMATIONS.md
/patterns             # all three, cross-linked → SESSION-INSIGHTS.md
```

Optionally name an output file for any of them: `/gripe-miner BACKLOG.md`.

## Requirements

- Claude Code
- **Python 3.8+ on your PATH** (the miners are stdlib-only — no pip installs)

## Commands

| Command | Mines | Writes | Use when |
|---|---|---|---|
| `/gripe-miner` | Things you complained about | `GRIPES.md` | You want just the voiced frustrations |
| `/session-patterns` | Repeating stuck/re-explain/defer/re-setup loops | `PATTERNS.md` | You want to see what keeps coming back |
| `/automate` | Prompts you keep retyping, and what they cost | `AUTOMATIONS.md` | You want fewer repeated prompts and a smaller token bill |
| `/patterns` | All three, merged | `SESSION-INSIGHTS.md` (sections: Reinforced, Gripes, Session Patterns, Automate this) | You want the full picture in one pass |

Each works standalone. `/patterns` doesn't replace the others — it runs all three
miners and adds a merged, cross-linked view on top.

## How it works

1. Each command runs a small stdlib-only script (`scripts/mine_gripes.py`,
   `scripts/mine_patterns.py` or `scripts/mine_asks.py`) that reads this project's
   transcripts under `~/.claude/projects/<encoded-cwd>/` and pulls out candidates —
   gripes via a tuned complaint regex, patterns via four theme regexes (`stuck`,
   `missing-context`, `deferral`, `reteach`), repeated asks by clustering
   normalised prompts that recur across sessions (default: 3 or more distinct
   sessions) and summing the token usage of the turns that answered them.
2. The current Claude session takes those candidates, **verifies each against your
   codebase** with Read/Grep/Glob and `git log` — and, for asks, against what you
   already have in `.claude/skills`, `.claude/commands`, settings hooks,
   `CLAUDE.md`, `scripts/` and schedulers — merges repeats, drops anything already
   fixed, already automated or unverifiable, and writes the top 3–5 survivors.
3. `/automate` then proposes, per surviving ask, the cheapest fix that fully covers
   it (CLAUDE.md line → script → skill → hook → scheduled routine → MCP, in that
   order of preference), with a concrete sketch and a savings figure that is always
   labeled as an estimate with its assumption shown. It only *suggests*: it never
   edits settings, hooks, crontabs or `CLAUDE.md`, and will scaffold a draft
   `SKILL.md` only after you explicitly say yes in the next message.
4. `/patterns` does all of the above, then — as a judgment call, not a regex —
   checks whether items from different lenses point at the same area. A gripe plus
   a pattern is **Reinforced**; a repeated ask plus either is ranked first under
   **Automate this**, and the pattern picks the fix type (a re-teach loop plus a
   repeated ask almost always means a `CLAUDE.md` line).

No second process is spawned and **nothing leaves your machine** — the miners make
no network calls and only read your own local transcripts.

## How tokens are measured (`/automate`)

- Every assistant message in a Claude Code transcript carries `message.usage` with
  `input_tokens`, `output_tokens`, `cache_creation_input_tokens` and
  `cache_read_input_tokens`. The miner attributes to each prompt the usage of every
  assistant message that followed it, up to the next prompt. Tool results, image
  captions and other harness-generated turns don't start a new prompt, so their
  follow-on usage stays with the prompt that caused it.
- Claude Code writes one JSONL line per streamed content block, all sharing the
  same `message.id` and the same usage snapshot. Each id is counted **once**. On the
  machine this was built on, the per-session sums matched Claude Code's own
  `cost-state` totals exactly in 705 of 738 sessions and never exceeded them; the
  rest were under-counted because subagent transcripts (`<session>/subagents/`)
  are not walked. Totals are therefore a floor, never an over-count.
- Components are reported separately (`input`, `output`, `cache_create`,
  `cache_create_1h`, `cache_read`), plus `fresh` (input + output + cache_create),
  `total`, and `weighted` — input-token equivalents at Anthropic's list-price ratios:
  output ×5, cache write ×1.25 (×2 for the 1-hour TTL Claude Code uses), cache read
  ×0.1. Raw cache reads dominate volume but are cheap; `weighted` is what the
  ranking uses (`score = count × weighted`, so frequency deliberately counts twice).
- If a turn has no usage field, its output is estimated at `len(text) / 4` and the
  cluster is flagged `"tokens_estimated": true`. Nothing is invented beyond that.
- Prompts sent by scripts (`claude -p`, the Agent SDK, cron jobs — Claude Code tags
  them `promptSource: "sdk"`) are already automations, so they are skipped by
  default and reported with `--include-scripted` as `"scripted": true` clusters,
  which the skill treats as a cost finding rather than something to automate.

## Optional: a start-of-session nudge

`hooks/hooks.json.example` will, on each session start, print a one-line count of
un-triaged gripes, un-triaged session patterns, and repeated-ask clusters (silent
on any line when there's nothing to report). It's **off by default** — rename it
to `hooks/hooks.json` to opt in; delete the `mine_asks.py` entry if you only want
the first two.

## Assumptions / known gaps (v0)

- The Session Patterns classifier is **invented from the one-pager's themes**, not
  extracted from a shipped product the way the gripe regex was (that one came from
  real Weekend Scan history). Expect it to need tuning once it's seen real triage
  results — it's deliberately conservative (regex-only, no NLP) in the meantime.
- Cross-linking in `/patterns` is a model judgment call on textual/area overlap, not
  a deterministic match — by design, since "same area" isn't something a regex can
  reliably decide.
- Repeated-ask clustering is word overlap (Jaccard ≥ 0.6 over significant words,
  plus a "same first six significant words" rule for templated prompts with a
  variable payload). It knows nothing about intent; the skill's triage is where
  "same words" becomes "same ask". Prompts over 4,000 characters are skipped as
  pasted material, so a routine that pastes long payloads is under-counted.
- The human / scripted / injected split relies on the `promptSource` and
  `turnOrigin` fields Claude Code writes on each user turn (verified on 2.1.258
  and 2.1.278; when they were introduced is not known). Transcripts without them
  fall back to a text-shape test (role-prompt preambles, markdown-headed briefs,
  probe phrasing); a person who opens a message with `# Title` or `You are a…`
  will be mistaken for a script there.
- Subagent spend is not attributed; usage before the first prompt of a resumed
  session is dropped. Token totals are floors.

## Roadmap

- `v0.1` — `/gripe-miner` command.
- `v0.2` — Session Patterns added as a sibling lens (`/session-patterns`, `/patterns`).
- `v0.3` — Automate this: repeated-ask clustering + token burn (`/automate`,
  `AUTOMATIONS.md`), wired into `/patterns` as a third section.
- A consumer **browser-extension** sibling that does the same for your ChatGPT /
  Claude.ai chat history, fully local. See [`docs/product-spec.md`](docs/product-spec.md).

## License

MIT © 2026 [JTolly](https://jollydesk.work)
