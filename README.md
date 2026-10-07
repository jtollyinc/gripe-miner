# Gripe Miner + Session Patterns

**Claude Code secretly logs every time you got frustrated — and every time you hit
the same wall twice. This reads both back.**

One plugin, two reinforcing lenses over the same local transcript mine:

- **Gripes** — the moments you actually complained: *"why does this keep
  resetting"*, *"this is so slow"*, *"I wish it just did X"*.
- **Session Patterns** — the loops that keep repeating even when you never said a
  word about it: the same error coming back, the same thing you keep re-explaining,
  the same "I'll fix that later" you never did, the same setup you redo every time.

Each candidate gets verified against your real code before it reaches you — leads,
not a to-do list. Run them together and anything that shows up in **both** lenses
gets ranked higher, because you both complained about it *and* kept hitting it.

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
/patterns             # both, cross-linked → SESSION-INSIGHTS.md
```

Optionally name an output file for any of the three: `/gripe-miner BACKLOG.md`.

## Requirements

- Claude Code
- **Python 3.8+ on your PATH** (the miners are stdlib-only — no pip installs)

## Commands

| Command | Mines | Writes | Use when |
|---|---|---|---|
| `/gripe-miner` | Things you complained about | `GRIPES.md` | You want just the voiced frustrations |
| `/session-patterns` | Repeating stuck/re-explain/defer/re-setup loops | `PATTERNS.md` | You want to see what keeps coming back |
| `/patterns` | Both, merged | `SESSION-INSIGHTS.md` (sections: Reinforced, Gripes, Session Patterns) | You want the full picture in one pass |

Each works standalone. `/patterns` doesn't replace the other two — it runs both
miners and adds a merged, cross-linked view on top.

## How it works

1. Each command runs a small stdlib-only script (`scripts/mine_gripes.py` or
   `scripts/mine_patterns.py`) that reads this project's transcripts under
   `~/.claude/projects/<encoded-cwd>/` and pulls out candidate lines — gripes via a
   tuned complaint regex, patterns via four theme regexes (`stuck`,
   `missing-context`, `deferral`, `reteach`) — most recent first, deduped.
2. The current Claude session takes those candidates, **verifies each against your
   codebase** with Read/Grep/Glob and `git log`, merges repeats (noting recurrence),
   drops anything already fixed or unverifiable, and writes the top 3–5 survivors.
3. `/patterns` does both of the above, then — as a judgment call, not a regex —
   checks whether a gripe and a pattern point at the same area. If so, it's
   **Reinforced** and ranked above either lens alone.

No second process is spawned and **nothing leaves your machine** — both miners make
no network calls and only read your own local transcripts.

## Optional: a start-of-session nudge

`hooks/hooks.json.example` will, on each session start, print a one-line count of
un-triaged gripes and un-triaged session patterns (silent on either line when
there's nothing to report). It's **off by default** — rename it to `hooks/hooks.json`
to opt in.

## Assumptions / known gaps (v0)

- The Session Patterns classifier is **invented from the one-pager's themes**, not
  extracted from a shipped product the way the gripe regex was (that one came from
  real Weekend Scan history). Expect it to need tuning once it's seen real triage
  results — it's deliberately conservative (regex-only, no NLP) in the meantime.
- Cross-linking in `/patterns` is a model judgment call on textual/area overlap, not
  a deterministic match — by design, since "same area" isn't something a regex can
  reliably decide.

## Roadmap

- `v0.1` — `/gripe-miner` command.
- `v0.2` — Session Patterns added as a sibling lens (`/session-patterns`, `/patterns`).
- A consumer **browser-extension** sibling that does the same for your ChatGPT /
  Claude.ai chat history, fully local. See [`docs/product-spec.md`](docs/product-spec.md).

## License

MIT © 2026 [JTolly](https://jollydesk.work)
