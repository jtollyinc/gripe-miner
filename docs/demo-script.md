# Gripe Miner — demo video, recording-ready script

Target: one ~40s vertical short (TikTok / YouTube Shorts / Reels). Build the whole
edit around a single frame: **a gripe with `x3` next to it.**

## Before you hit record (10 min)

1. **Pick the project with the juiciest history.** Run the miner dry first so you
   know your numbers before recording:
   ```
   python C:\dev\gripe-miner\plugins\gripe-miner\scripts\mine_gripes.py
   ```
   You want a project where the output includes at least one gripe that repeats.
   If the top results are weak, try another project dir.
2. **Rehearse once off-camera.** Run `/gripe-miner` in a real terminal `claude`
   session (not the desktop app) so you know exactly what scrolls by and how long
   the verify stage takes. Note the "scanned N sessions" numbers — you'll say them.
3. **Terminal prep:** dark theme, font size ~18pt+ (phone-readable), window sized
   roughly 9:16-friendly (tall and narrow), close every other window, hide the
   taskbar clock/tray if it's cluttered.
4. **Record horizontal at full res, crop to vertical in the edit.** Easier than
   fighting a narrow window live. OBS or even Win+Alt+R is fine.
5. Delete any existing `GRIPES.md` in the demo project so the file-open moment is a
   first reveal.

## Shot list

| Time | Screen | You say (voiceover, casual) |
|------|--------|------|
| 0–3s | Black terminal, cursor blinking | "Claude Code secretly logs every time you got annoyed." |
| 3–6s | Type `/gripe-miner`, hit enter | "So I built a plugin that reads them back." |
| 6–14s | Miner scrolls: `scanned N sessions · found M gripes`, then Claude visibly Greps/Reads real files | "It doesn't just guess — watch it check every complaint against my actual code." |
| 14–30s | `GRIPES.md` opens. Slow scroll. Zoom the line ending in `(you said: "why does this keep resetting", x3)` | "Every item is my own words, quoted back at me." *(pause — let the x3 land)* |
| 30–37s | Hold on the x3 frame | "It found the bug I complained about three times and never fixed." |
| 37–40s | Cut to the two install lines, full screen | "Free, open source, nothing leaves your machine. Link in bio." |

Install lines for the end card:

```
/plugin marketplace add jtolly/gripe-miner
/plugin install gripe-miner@jtolly-tools
```

## Edit notes

- The **verify stage is the credibility beat** — don't cut it out entirely; speed-ramp
  it 4–8x so viewers see tool calls flying, then snap to normal speed for the reveal.
- Caption text on the hook frame ("your AI logs your frustration") for sound-off viewers.
- No music until the reveal, or something minimal — the terminal IS the aesthetic.
- One video, three uploads: TikTok, Shorts, Reels. Same file.

## Caption template

> Claude Code keeps a log of every time you got frustrated. I built a free plugin
> that mines it and hands you a ranked fix list — verified against your real code,
> quoting your own words back at you. 100% local. Repo in bio. #claudecode #buildinpublic #devtools

## Bio link

Point at `https://github.com/jtolly/gripe-miner` (push the repo first — see README).
