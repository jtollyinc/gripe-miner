# Gripe Miner

**Your Claude Code transcripts already know what's wasting your time. This plugin reads them back: the things you complained about, the loops you keep hitting, and the prompts you keep retyping, with the tokens each one has burned.**

<!-- TODO(demo): drop demo/gripe-miner-demo.gif into demo/ and this line goes live. -->
![Gripe Miner demo](demo/gripe-miner-demo.gif)

One plugin, three lenses over the same local transcript mine:

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

Runs locally. Reads only your own transcripts. Makes no network calls.

---

## Install

Two commands inside Claude Code:

```
/plugin marketplace add jtollyinc/gripe-miner
/plugin install gripe-miner@jtolly-tools
```

Then, in any project:

```
/gripe-miner:gripe-miner        # gripes only → GRIPES.md
/gripe-miner:session-patterns   # patterns only → PATTERNS.md
/gripe-miner:automate           # repeated asks + token burn → AUTOMATIONS.md
/gripe-miner:patterns           # all three, cross-linked → SESSION-INSIGHTS.md
```

Installed plugin skills are namespaced as `/<plugin>:<skill>`, so these are the
names that always work. The short forms (`/automate`, `/patterns`,
`/session-patterns`, `/gripe-miner`) also resolve as long as nothing else on your
machine defines a skill or command with the same name. The rest of this README
uses the short forms.

Optionally name an output file for any of them: `/gripe-miner:gripe-miner BACKLOG.md`.

### Install from a local clone

To try a checkout before it's published (or your own fork), point the
marketplace at the directory instead of the GitHub slug:

```
/plugin marketplace add /path/to/gripe-miner
/plugin install gripe-miner@jtolly-tools
```

### Updating

```
/plugin marketplace update jtolly-tools
/plugin uninstall gripe-miner@jtolly-tools
/plugin install gripe-miner@jtolly-tools
```

(`/plugin update gripe-miner@jtolly-tools` does the uninstall + install in one
step on Claude Code versions that support it.) Then restart Claude Code —
`/exit`, then `claude` — so the new skill files and scripts are loaded; a
running session keeps the old copy.

## Requirements

- Claude Code
- **Python 3.8+ on your PATH** (the miners are stdlib-only — no pip installs)

## Commands

| Command (namespaced / short) | Mines | Writes | Use when |
|---|---|---|---|
| `/gripe-miner:gripe-miner` / `/gripe-miner` | Things you complained about | `GRIPES.md` | You want just the voiced frustrations |
| `/gripe-miner:session-patterns` / `/session-patterns` | Repeating stuck/re-explain/defer/re-setup loops | `PATTERNS.md` | You want to see what keeps coming back |
| `/gripe-miner:automate` / `/automate` | Prompts you keep retyping, and what they cost | `AUTOMATIONS.md` | You want fewer repeated prompts and a smaller token bill |
| `/gripe-miner:patterns` / `/patterns` | All three, merged | `SESSION-INSIGHTS.md` (sections: Reinforced, Gripes, Session Patterns, Automate this) | You want the full picture in one pass |

Each works standalone. `/patterns` doesn't replace the others — it runs all three
miners and adds a merged, cross-linked view on top.

## What it found on a real history

Run with `--all --days 60` across the author's three machines (one Linux server
running scheduled jobs, two Windows machines used interactively), covering
60 days of Claude Code transcripts. Dollar figures are **API list-price
equivalents** computed from the token counts, not an actual bill.

- **3.8 billion tokens, about $5.4k list-price equivalent.** 94% of those tokens
  were cache reads. The cost driver was long sessions re-reading their own
  history and the model tier they ran on, not how much got typed.
- **A scheduled "is this roadmap item done?" checker** was spawning a full
  Claude Code process on an Opus-tier model to produce a one-line JSON answer:
  240+ runs in two weeks, roughly 56K tokens of cache write per run for a
  171-token answer, about $120 list-equivalent. Fix: cache by evidence hash,
  cache failures too, and run the judgement on a small model.
- **A trip-email extractor** was doing the same thing: 250+ single-shot spawns
  over a month, about $80. Same fix.
- **An older model tier still in muscle memory** (typed as a `/model` switch
  32 times) cost about $570 more over the 60 days than its successor would have,
  because its cache reads were priced 4x higher at the same input/output price.
- **Doubled work is measurable.** One landing page took 44 sessions in 8 days
  (prompts repeating "do NOT rebuild from scratch"); a verify loop re-ran
  "not actually fixed" five times; each rejection started a fresh session that
  re-read everything.

The same run also found the plugin's own blind spots, which are listed under
[Assumptions / known gaps](#assumptions--known-gaps) below.

## Privacy

- Everything runs on your machine. The miners are stdlib Python scripts that
  read `~/.claude/projects/<encoded-cwd>/*.jsonl` and nothing else.
- No network calls, no telemetry, no second process. The only model involved is
  the Claude Code session you are already in, which reads the miner's JSON
  output exactly as it would read any other file in your project.
- The output files (`GRIPES.md`, `PATTERNS.md`, `AUTOMATIONS.md`,
  `SESSION-INSIGHTS.md`) quote your own prompts back at you. They are written
  into the project you ran the command in, so treat them like any other file
  with your words in it before committing them.

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
  Slash-command runs (`/deep-research …`, `/commit`) are treated the same way:
  the invocation is one prompt with origin `command` and the text `/name args`,
  the expanded command body the harness writes right after it is folded into
  that prompt (never clustered on its own), and the usage of the answer is
  charged to it.
- Harness-written user turns — image captions, "your response above was cut off
  mid-stream" resume nudges, the local-command caveat, IDE context — never start
  a prompt. Their follow-on usage stays with the prompt that caused it.
- `--days` is applied per message, by each record's own timestamp (file mtime
  only for records without one). A session file that was touched yesterday but
  started months ago contributes only the prompts inside the window.

## Optional: a start-of-session nudge

`hooks/hooks.json.example` will, on each session start, print a one-line count of
un-triaged gripes, un-triaged session patterns, and repeated-ask clusters (silent
on any line when there's nothing to report). It's **off by default** — rename it
to `hooks/hooks.json` to opt in; delete the `mine_asks.py` entry if you only want
the first two.

## Assumptions / known gaps

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
- **Claude desktop app prompts are tagged `promptSource: "sdk"`** by the harness,
  so on a machine where you mostly type into the desktop app the typed-only view
  of `/automate` sees almost nothing. Use `--include-scripted` there. Found on the
  60-day run above; a fix is on the roadmap.
- Forked or resumed sessions duplicate transcript files: the same `message.id`
  can appear in several files and will count once per file in ask clusters, so a
  single conversation copied into eight files looks like eight sessions.
- The gripe and pattern lenses have no typed/scripted filter yet: on a box that
  mostly runs scripted jobs, job briefs and boilerplate will dominate both lists.
- Subagent spend is not attributed; usage before the first prompt of a resumed
  session is dropped. Token totals are floors.
- Slash-command expansion detection relies on the body being the user turn that
  immediately follows the `<command-name>` record, flagged `isMeta` or written
  within 10 seconds of it. That shape was derived from documented transcript
  behaviour, not observed on the machine this was built on (which has almost no
  interactive sessions); a command whose body arrives later than that would be
  clustered as a typed ask again.

## Changelog

- `v0.3.1` — three `/automate` false positives fixed, all found on a real
  1,950-prompt history where every "repeated ask" was harness text:
  - the `<local-command-caveat>` sentence (and `ide_opened_file` /
    `ide_selection` context) is stripped with its content, not just its tags;
  - the resume nudge is recognised in its current wording ("…was cut off
    mid-stream…") and reasonable variants, not only "…was stopped";
  - `--days` filters per message by timestamp instead of per file by mtime, for
    all three miners (gripes and patterns included — a recently-touched session
    file no longer drags its whole history into the window);
  - slash-command runs are classified as `command` (already automated, skipped
    unless `--include-scripted`) and their expanded bodies are never clustered;
  - harness `isMeta` turns (captions, nudges) no longer split a prompt's usage;
  - regression tests under `tests/` (`python -m unittest` from the repo root).
- `v0.3.0` — Automate this lens.

## Roadmap

- `v0.1` — `/gripe-miner` command.
- `v0.2` — Session Patterns added as a sibling lens (`/session-patterns`, `/patterns`).
- `v0.3` — Automate this: repeated-ask clustering + token burn (`/automate`,
  `AUTOMATIONS.md`), wired into `/patterns` as a third section.
- Next: a typed/scripted filter for the gripe and pattern lenses, desktop-app
  prompt origin handled correctly, forked-session dedupe by `message.id`, and
  subagent spend attributed to the prompt that spawned it.
- **Gripe**, a consumer browser-extension sibling that does the same for your
  ChatGPT / Claude.ai chat history, fully local. v0 is built and in testing.
  See [`docs/product-spec.md`](docs/product-spec.md).

## License

MIT © 2026 [JTolly](https://jollydesk.work)
