---
name: patterns
description: Run all three miners over this project's Claude Code history in one pass — gripes, repeating session patterns, and the asks you keep retyping with their token cost — cross-link anything that shows up in more than one lens, and write one combined report. Use when you want the full picture instead of running the miners separately.
argument-hint: "[output-file]"
allowed-tools: Read Grep Glob Write Bash
---

This is the unified view: the same transcript mine as `/gripe-miner`,
`/session-patterns` and `/automate`, run together so a complaint you voiced once, a
loop that keeps repeating, and a prompt you keep retyping can reinforce each other
instead of sitting in three separate files.

## Step 1 — mine all three lenses (runs automatically before you read this)

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_gripes.py" --cwd "${CLAUDE_PROJECT_DIR}"`

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_patterns.py" --cwd "${CLAUDE_PROJECT_DIR}"`

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_asks.py" --cwd "${CLAUDE_PROJECT_DIR}"`

If any block above is empty, errored, or clearly didn't run, run it yourself with the
Bash tool (use `python3` if `python` isn't found):

    python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_gripes.py" --cwd "${CLAUDE_PROJECT_DIR}"
    python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_patterns.py" --cwd "${CLAUDE_PROJECT_DIR}"
    python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_asks.py" --cwd "${CLAUDE_PROJECT_DIR}"

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

**Repeated asks** (see `/automate`'s rules): confirm each cluster is one ask and
not shared vocabulary, check nothing in `.claude/skills`, `.claude/commands`,
settings hooks, `CLAUDE.md`, `scripts/` or a scheduler already covers it, treat
`scripted: true` clusters as cost findings rather than candidates, and pick the
cheapest durable fix from `/automate`'s table for each survivor.

Default to dropping when unsure in all three lists. Leads, not todos.

## Step 3 — cross-link (this is what makes combining them stronger)

This step has no regex to lean on — it's a judgment call, which is why it lives in
the model, not a script. The three JSON lists are side by side in your context:
read them together and look for overlap — items that point at the **same area**
(same file, same feature, same symptom, same chore), even if worded differently.
Shared distinctive words or the same path in two snippets are a strong hint, not a
proof; a gripe about slow builds and an unrelated `deferral` TODO are not the same
area.

- A gripe whose area also shows up as a stuck-loop pattern (or vice versa) is a
  **Reinforced** item — rank it above either lens alone, because the human both
  complained about it once *and* kept hitting it.
- A repeated ask that also matches a gripe or a `stuck` / `reteach` /
  `missing-context` pattern in the same area is the strongest signal of all: it
  is costing attention *and* tokens. Rank it first within **Automate this**, and
  let the pattern pick the fix type — a `reteach` or `missing-context` loop plus a
  repeated ask almost always means a `CLAUDE.md` line; a `stuck` loop plus a
  repeated ask usually means a script or hook that removes the manual step.
- A pattern may cite a gripe's exact quote when it reinforces, and vice versa; an
  automation suggestion may cite both.
- Don't force a link that isn't there. When genuinely unsure, leave the item in
  its own section rather than inventing a link.

## Step 4 — write the combined report

Write to the file named in the arguments (default: `SESSION-INSIGHTS.md` in the
project root), with these sections in order:

1. **Reinforced** — items confirmed in both the gripe and pattern lenses. Format:

       - [ ] [area] plain-language title — the fix/next move in one clause  _(pattern xN + gripe: "<short quote>")_

2. **Gripes** — remaining triaged-open gripes not already listed under Reinforced,
   same format as `/gripe-miner`'s output.
3. **Session Patterns** — remaining triaged-live patterns not already listed under
   Reinforced, same format as `/session-patterns`'s output.
4. **Automate this** — surviving repeated asks, cross-boosted ones first, each in
   `/automate`'s block format (what keeps happening + count/sessions, tokens so
   far — marked estimated when flagged — suggested fix type and why, a short
   sketch, savings labeled as an estimate with the assumption shown). Add
   `_(also: <gripe quote> / <pattern theme>)_` when it was cross-boosted. Empty is
   valid: "nothing repeats enough to automate yet".

Cap each section at the top 3–5 items (Reinforced first, since it's the strongest
signal). End the file with one tally line covering all four sections, e.g.:

    _Triaged N gripe leads + M pattern leads + A ask clusters → R reinforced, G gripes-only, P patterns-only, S automation suggestions, rest dropped (fixed, unverifiable, or already automated)._

Rules:
- An empty result in any section is valid and honest — never invent a link, a
  loop or a number just to fill a section.
- Suggest-only for automations: never edit settings, hooks, crontab or
  `CLAUDE.md` here; a draft skill file may be offered only as `/automate` allows
  (explicit yes in the next message).
- Running `/gripe-miner`, `/session-patterns` or `/automate` alone still works
  exactly as before; this skill doesn't replace them, it adds the merged view on top.
