---
name: gripe-miner
description: Scan this project's Claude Code history for things you complained about, verify them against the code, and write a ranked fix list. Use when you want to turn past frustration into an actionable backlog.
argument-hint: "[output-file]"
allowed-tools: Read Grep Glob Write Bash
---

## Step 1 — mine the transcripts (runs automatically before you read this)

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_gripes.py" --cwd "${CLAUDE_PROJECT_DIR}"`

If the block above is empty, errored, or clearly didn't run, run it yourself with the
Bash tool before continuing (use `python3` if `python` isn't found):

    python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_gripes.py" --cwd "${CLAUDE_PROJECT_DIR}"

## Step 2 — triage against CURRENT reality (this is the whole value)

The block above is a list of **leads, not a to-do list.** Each was typed days or weeks
ago and **many are already fixed.** Your job is to find the few that are *still broken
today.* Be skeptical; default to dropping.

For each candidate, in order:

1. **Confirm it's real.** Use Read/Grep/Glob to find the code it refers to. Can't find
   it, or it's obviously a pasted prompt/spec rather than a complaint → drop.
2. **Check if it was already resolved after it was raised.** Each snippet has a date.
   Use the Bash tool to see whether the relevant area changed since then:

       git log --oneline --since="<gripe date>" -- <path/to/relevant/files>

   Read the commit subjects (and `git show` if unsure). If a later commit plausibly
   addresses the gripe, **drop it** and note "(looks fixed in <hash>)".
3. **Subjective/UX gripes you can't verify from code** ("feels clunky", "confusing") →
   drop unless the thing described is still plainly present in the code/UI.
4. **Merge duplicates**; note the recurrence count.

Then write the **top 3–5 still-open** items to the file named in the arguments
(default: `GRIPES.md` in the project root), as a checklist. Format each line exactly:

    - [ ] [area] symptom — the file it lives in + the fix in one clause  _(you said: "<short quote>", xN)_

Rules:
- **Default to dropping when unsure.** Better 2 confirmed-open items than 5 that might
  already be done — a stale list is worse than a short one.
- End the file with a one-line tally: `_Triaged N leads → M still open, K looked
  already-fixed, rest unverifiable._` so the user can see you actually checked.
- An empty result is a valid, honest answer. If nothing clears the bar, write nothing
  and say so — never invent work.

## Reinforcement (optional, cheap)

If `PATTERNS.md` or `SESSION-INSIGHTS.md` already exists in the project root (from
`/session-patterns` or `/patterns`), skim it. A gripe whose area also shows up there as
a recurring stuck-loop theme is a stronger signal — note it inline:
`_(also a recurring pattern — see PATTERNS.md)_`. Don't block on this; it's a bonus
cross-check, not a requirement.
