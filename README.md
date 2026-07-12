# Gripe Miner

**Claude Code secretly logs every time you got frustrated. This reads them back and turns them into a fix list.**

Gripe Miner scans your local Claude Code transcripts for the moments you actually
complained — *"why does this keep resetting"*, *"this is so slow"*, *"I wish it just
did X"* — then asks the model to confirm each one against your real code and hand
you a short, ranked, checkbox backlog. The complaint you voiced three times and
never fixed? It surfaces that.

It is deliberately **quiet**: precision over recall, an empty result is a valid
answer, and it never pads the list.

---

## Install

```
/plugin marketplace add jtolly/gripe-miner
/plugin install gripe-miner@jtolly-tools
```

Then, in any project:

```
/gripe-miner
```

Optionally name an output file: `/gripe-miner BACKLOG.md` (defaults to `GRIPES.md`).

## Requirements

- Claude Code
- **Python 3.8+ on your PATH** (the miner is stdlib-only — no pip installs)

## How it works

1. `/gripe-miner` runs `scripts/mine_gripes.py`, which reads this project's
   transcripts under `~/.claude/projects/<encoded-cwd>/` and pulls out the lines
   you typed that match a tuned "gripe" pattern (most recent first, deduped).
2. The current Claude session takes those candidates, **verifies each against your
   codebase** with Read/Grep/Glob, merges repeats (noting how often each came up),
   and writes the top 3–5 to `GRIPES.md` — each item quoting your own words.

No second process is spawned and **nothing leaves your machine** — the miner makes
no network calls and only reads your own local transcripts.

## Optional: a start-of-session nudge

`hooks/hooks.json.example` will, on each session start, print a one-line count of
un-triaged gripes (and stay silent when there are none). It's **off by default** —
rename it to `hooks/hooks.json` to opt in.

## Roadmap

- `v0.1` — `/gripe-miner` command (this)
- A consumer **browser-extension** sibling that does the same for your ChatGPT /
  Claude.ai chat history, fully local. See [`docs/product-spec.md`](docs/product-spec.md).

## License

MIT © 2026 Jaron Tolly
