---
name: patterns
description: Run both the gripe miner and the session-pattern miner over this project's Claude Code history in one pass, cross-link anything that shows up in both lenses, and write one combined report. Use when you want the full picture instead of running the two miners separately.
argument-hint: "[output-file]"
allowed-tools: Read Grep Glob Write Bash
---

This is the unified view: same transcript mine as `/gripe-miner` and `/session-patterns`,
run together so a complaint you voiced once and a loop that keeps repeating can
reinforce each other instead of sitting in two separate files.

## Step 1 — mine both lenses (runs automatically before you read this)

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_gripes.py" --cwd "${CLAUDE_PROJECT_DIR}"`

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_patterns.py" --cwd "${CLAUDE_PROJECT_DIR}"`

If either block above is empty, errored, or clearly didn't run, run it yourself with the
Bash tool (use `python3` if `python` isn't found):

    python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_gripes.py" --cwd "${CLAUDE_PROJECT_DIR}"
    python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_patterns.py" --cwd "${CLAUDE_PROJECT_DIR}"

## Step 2 — triage each list on its own terms first

Apply the exact same skepticism as the solo skills — do this before cross-linking,
not instead of it:

**Gripes** (see `/gripe-miner`'s rules): confirm each against the code with
Read/Grep/Glob, check `git log --oneline --since="<date>" -- <path>` for fixes
already shipped, drop anything unverifiable or already fixed, merge duplicates.

**Session Patterns** (see `/session-patterns`'s rules): confirm each theme
(`stuck` / `missing-context` / `deferral` / `reteach`) reflects a real recurring
loop and not a one-off, verify against the code, drop anything already resolved,
merge duplicates.

Default to dropping when unsure in both lists. Leads, not todos.

## Step 3 — cross-link (this is what makes combining them stronger)

This step has no regex to lean on — it's a judgment call, which is why it lives in
the model, not the script. Read both triaged lists side by side and look for overlap:
a gripe and a pattern that point at the **same area** (same file, same feature, same
symptom), even if worded differently.

- When a gripe's area also shows up as a stuck-loop pattern (or vice versa), that's a
  **Reinforced** item — rank it higher than either lens alone would, because the human
  both complained about it once *and* kept hitting it.
- A pattern may cite a gripe's exact quote when it reinforces, and vice versa.
- Don't force a link that isn't really there — a gripe about slow build times and a
  "deferral" pattern about an unrelated TODO are not the same area. When genuinely
  unsure, leave the item in its own section rather than inventing a link.

## Step 4 — write the combined report

Write to the file named in the arguments (default: `SESSION-INSIGHTS.md` in the
project root), with these sections in order:

1. **Reinforced** — items confirmed in both lenses. Format each line:

       - [ ] [area] plain-language title — the fix/next move in one clause  _(pattern xN + gripe: "<short quote>")_

2. **Gripes** — remaining triaged-open gripes not already listed under Reinforced,
   same format as `/gripe-miner`'s output.
3. **Session Patterns** — remaining triaged-live patterns not already listed under
   Reinforced, same format as `/session-patterns`'s output.

Cap each section at the top 3–5 items (Reinforced first, since it's the strongest
signal). End the file with one tally line covering all three sections, e.g.:

    _Triaged N gripe leads + M pattern leads → R reinforced, G gripes-only, P patterns-only, rest dropped (fixed or unverifiable)._

Rules:
- An empty result in any section is valid and honest — never invent a link or a leak
  just to fill a section.
- Running `/gripe-miner` or `/session-patterns` alone still works exactly as before;
  this skill doesn't replace them, it adds the merged view on top.
