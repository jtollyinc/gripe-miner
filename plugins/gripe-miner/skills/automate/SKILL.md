---
name: automate
description: Find what you keep asking Claude Code for by hand — the same prompt recurring across sessions, and the tokens it burns — check that nothing already automates it, and propose the cheapest durable fix for each (skill, hook, script, scheduled routine, CLAUDE.md line, MCP connector). Use when you want fewer repeated prompts and a smaller token bill.
argument-hint: "[output-file]"
allowed-tools: Read Grep Glob Write Bash
---

## Step 1 — mine the transcripts (runs automatically before you read this)

!`python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_asks.py" --cwd "${CLAUDE_PROJECT_DIR}"`

If the block above is empty, errored, or clearly didn't run, run it yourself with the
Bash tool before continuing (use `python3` if `python` isn't found):

    python "${CLAUDE_PLUGIN_ROOT}/scripts/mine_asks.py" --cwd "${CLAUDE_PROJECT_DIR}"

Useful variants: `--all` (every project on this machine — asks that cross projects
are the best automation candidates), `--days 120`, `--min-sessions 2` (looser),
`--include-scripted` (also cluster prompts sent by scripts / `claude -p` / cron;
those come back flagged `"scripted": true` and are a *cost* finding, never an
automation candidate — they already are one).

What you get: `clusters[]`, each with `representative` (the most common wording),
`examples` (up to 3 wordings), `count`, `sessions`, `projects`, `first_seen`,
`last_seen`, `turns`, `models`, `tokens` — `input`, `output`, `cache_create`,
`cache_create_1h`, `cache_read`, `fresh` (= input + output + cache_create),
`total`, and `weighted` (input-token equivalents at list-price ratios; the
`weighting` object in the JSON shows the exact multipliers) — `tokens_estimated`
(true when a turn lacked usage data and was estimated from text length),
`scripted`, and `score` (= count × weighted). `token_totals` is the spend
attributed to *every* prompt in the window, so you can say what share a cluster
is. `prompts.skipped` says how many prompts were set aside and why.

## Step 2 — triage (leads, not a to-do list)

The clusterer is word overlap over normalised text. It cannot tell whether two
prompts want the same *outcome*, only that they use the same words. Be skeptical;
default to dropping.

For each cluster, in order:

1. **Is it one ask?** Read the `examples`. Different requests that happen to share
   vocabulary, or a pasted spec / log / brief rather than a request → drop. Several
   clusters that are plainly the same routine with a different payload (same
   opener, different item) → merge them in your write-up and sum counts and tokens.
2. **Is it already automated?** Look before proposing anything:
   `.claude/skills/*/SKILL.md`, `.claude/commands/*.md`, hooks in
   `.claude/settings.json` and `.claude/settings.local.json`, `CLAUDE.md` /
   `AGENTS.md`, `scripts/`, `Makefile`, `package.json` scripts, `.github/workflows/`,
   and any crontab / systemd timer / Task Scheduler mention in the docs. Glance at
   `~/.claude/settings.json` hooks too (read only). If something already covers the
   ask, drop it — unless the person keeps asking anyway, in which case the fix is
   discoverability: a `CLAUDE.md` line naming the existing command.
3. **Does it still apply?** `git log --oneline --since="<last_seen>" -- <area>`;
   if what was being asked for has since been removed or finished → drop.
4. **`scripted: true` clusters** are already automations. Never propose automating
   them. If one is expensive, the finding is cost: a cheaper model, a tighter
   prompt, fewer runs, or prompt caching — and only when the numbers justify a line.

## Step 3 — pick the cheapest durable fix

One suggestion per surviving cluster. Take the FIRST row that fully covers the ask;
cheaper and more durable rows come first:

| What keeps happening | Suggest | Why this type |
|---|---|---|
| The same instruction, context or preference re-taught each session | `CLAUDE.md` line (or a memory entry) | Zero machinery; read on every session start |
| A deterministic job that needs no model (rename, convert, collect, check) | Script / CLI tool | No tokens, testable, usable outside Claude |
| The same multi-step task, on demand | Skill / slash command | One short invocation replaces a re-typed brief |
| Something that should happen at a moment in the session, unprompted | Hook: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop` | Removes the ask entirely |
| Needs to run on a clock, not when someone remembers | Scheduled routine: cron / systemd timer / Windows Task Scheduler running a script, or `claude -p "<prompt>"` | Humans forget, timers don't |
| Repeatedly fetching or pasting data from an outside system | MCP server / connector | Replaces copy-paste with a tool call |

Prefer no-model over model. A skill that calls a script beats a skill that
re-derives the work every time.

## Step 4 — write the report

Write to the file named in the arguments (default: `AUTOMATIONS.md` in the project
root). For each suggestion, in rank order:

    ### 1. <plain-language title>
    - **What keeps happening:** "<short quote of their own words>" — N times across S sessions (P projects), first <date>, last <date>
    - **Tokens so far:** T total (F fresh, C cache-read), ~W weighted  _(estimated — some turns lacked usage data)_
    - **Suggested fix:** <type> — <one clause on why this type>
    - **Sketch:**
      ```
      <SKILL.md frontmatter + opening lines / hook JSON / cron line / CLAUDE.md line / script outline>
      ```
    - **Estimated savings:** ~X weighted tokens/month and ~N fewer prompts/month  _(estimate: assumes the ask keeps recurring at the observed rate of N per D days and that the fix removes about Y % of the per-ask cost)_

The "estimated" tag on the tokens line appears only when `tokens_estimated` is
true. Savings rule of thumb, stated in the report every time: a `CLAUDE.md` line
or a skill removes the re-explaining and warm-up turns, not the work — assume
30–50 %; a script, hook or timer that takes the model out of the loop — assume
90 %+. Per-ask cost = `weighted / count`; monthly rate = `count / days × 30`.
Numbers from the miner are measured; everything after "assumes" is yours — keep
the label on it.

End with one tally line:
`_Triaged N clusters → M suggestions, K already automated, rest dropped (noise or no longer applies)._`

Rules:
- **Default to dropping when unsure.** Three suggestions someone will act on beat
  eight they will skim.
- **Never invent numbers.** Token figures come from the miner, flagged when
  estimated. If the miner returned no clusters, write that nothing repeats enough
  to automate yet (quote `prompts.total` and `prompts.eligible`) and stop — an
  empty result is a valid, honest answer.
- Scripted clusters, if reported at all, go in a separate short section
  "Routines and what they cost", suggestion-free unless the cost finding is real.

## Step 5 — optional scaffold (only on explicit confirmation)

Suggest-only is the default. After writing the report you MAY ask one question —
"Want me to write a draft `.claude/skills/<name>/SKILL.md` for #1?" — and then end
your turn. Write the draft only if the person's NEXT message explicitly says yes,
and write nothing but that one file. Never edit `.claude/settings*.json`,
`hooks.json`, a crontab, systemd units, Task Scheduler or `CLAUDE.md` yourself —
put the snippet in the report for them to paste.

## Reinforcement (optional, cheap)

If `GRIPES.md`, `PATTERNS.md` or `SESSION-INSIGHTS.md` exists in the project root
(from `/gripe-miner`, `/session-patterns` or `/patterns`), skim it. An ask that
also shows up there as a gripe or a stuck / re-teach loop is a stronger candidate —
note it inline: `_(also a recurring pattern — see PATTERNS.md)_`. A re-teach or
missing-context pattern plus a repeated ask almost always means a `CLAUDE.md` line.
