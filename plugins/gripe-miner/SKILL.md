---
name: gripe-miner
description: Scan this project's Claude Code history for things you complained about, verify them against the code, and write a ranked fix list. Use when you want to turn past frustration into an actionable backlog.
argument-hint: "[output-file]"
allowed-tools: Read Grep Glob Write Bash
---

## Step 1 — mine the transcripts (runs automatically before you read this)

!`python "${CLAUDE_SKILL_DIR}/scripts/mine_gripes.py" --cwd "${CLAUDE_PROJECT_DIR}"`

If the block above is empty, errored, or clearly didn't run, run it yourself with the
Bash tool before continuing (use `python3` if `python` isn't found):

    python "${CLAUDE_SKILL_DIR}/scripts/mine_gripes.py" --cwd "${CLAUDE_PROJECT_DIR}"

## Step 2 — your job

The block above is JSON: gripe snippets the user actually typed in past Claude Code
sessions of THIS project, most recent first. Turn them into a short, honest,
verified fix list.

For each candidate:
- Use Read/Grep/Glob to **confirm the issue is real in the current code** before you
  report it. If you can't find the code it refers to, drop it — no speculation.
- Ignore any snippet that is obviously a pasted prompt, spec, or instruction block
  rather than a genuine complaint.
- Merge duplicates and near-duplicates. The **same** complaint recurring across
  sessions is a *stronger* signal, not a reason to list it twice — note how many
  times it came up.

Then write the **top 3–5** highest-signal, highest-confidence items to the file named
in the arguments (default: `GRIPES.md` in the project root), as a checklist. Format
each line exactly like this:

    - [ ] [area] symptom — the file it lives in + the fix in one clause  _(you said: "<short quote>", xN)_

Rules:
- **Precision over recall.** Two solid, real items beat five padded ones.
- An empty result is a valid, honest answer. If nothing clears the bar, write
  nothing and say so — never invent work.
- Rank by: (1) friction voiced repeatedly, (2) confirmed bugs, (3) clear quick wins.
