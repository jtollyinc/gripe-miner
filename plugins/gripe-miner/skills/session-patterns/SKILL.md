---
name: session-patterns
description: Scan this project's Claude Code history for repeating loops — the same stuck point, the same re-explaining, the same "I'll fix that later", the same re-setup — verify each against the code, and write a ranked pattern report. Use when you want to see what keeps coming back, not just what annoyed you once.
argument-hint: "[output-file]"
allowed-tools: Read Grep Glob Write Bash
---

## Step 1 — mine the transcripts (runs automatically before you read this)

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_patterns.py" --cwd "${CLAUDE_PROJECT_DIR}"`

If the block above is empty, errored, or clearly didn't run, run it yourself with the
Bash tool before continuing (use `python3` if `python` isn't found):

    python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_patterns.py" --cwd "${CLAUDE_PROJECT_DIR}"

Each candidate carries a `theme`: `stuck` (same error/break, still failing), `missing-context`
(re-explaining, "I already told you"), `deferral` ("I'll fix later", TODO, workaround), or
`reteach` (re-setup, reinstall, "every time I open this").

## Step 2 — triage against CURRENT reality (this is the whole value)

These are **leads, not a to-do list.** The classifier is a regex over one typed message —
it has no idea whether the loop actually repeated, or whether it's already resolved. Your
job is to turn raw candidates into the few *real, still-live* patterns. Be skeptical;
default to dropping.

For each candidate, in order:

1. **Confirm it's a real recurring loop, not a one-off.** A single "I'll fix this later"
   is not a pattern — look for the same theme + same area showing up more than once
   across the mined candidates, or search the transcripts/git log yourself for repeats.
   One-off, isolated mentions → drop.
2. **Verify against the code when you can.** Use Read/Grep/Glob to find the area it
   refers to. Can't find it, or it reads like a pasted prompt/spec rather than something
   the human actually hit → drop.
3. **Check if it's already resolved.** Use the Bash tool:

       git log --oneline --since="<earliest date>" -- <path/to/relevant/files>

   If a later commit plausibly closes the loop (fixes the recurring error, adds the
   missing setup step, finishes the deferred work), **drop it** and note "(looks fixed
   in <hash>)".
4. **Unverifiable/subjective loops** you can't tie to a specific file or repeatable
   symptom → drop unless the underlying cause is still plainly present.
5. **Merge duplicates** across sessions; note the recurrence count.

Then write the **top 3–5 still-live** patterns to the file named in the arguments
(default: `PATTERNS.md` in the project root), ranked most-recurring/most-costly first,
as a checklist with a plain-language title and a next useful move in one clause:

    - [ ] [theme] plain-language title — what keeps happening + the one next move  _(you said: "<short quote>", recurs xN)_

Rules:
- Leads, not todos — **default to dropping when unsure.**
- **Never invent a loop.** If the mined candidates don't support a pattern, leave it out.
- An empty result is valid and honest. Silence over noise.
- End the file with a one-line tally: `_Triaged N leads → M still live, K looked
  already-fixed, rest unverifiable._`

## Reinforcement (optional, cheap)

If `GRIPES.md` or `SESSION-INSIGHTS.md` already exists in the project root (from
`/gripe-miner` or `/patterns`), skim it. A stuck-loop pattern whose area also shows up
there as a one-off gripe is a stronger signal — note it inline:
`_(also complained about directly — see GRIPES.md)_`. Don't block on this; it's a bonus
cross-check, not a requirement.
