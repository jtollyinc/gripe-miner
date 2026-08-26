"""Fully-automated Gripe Miner demo video: renders terminal footage with PIL,
pipes raw frames to ffmpeg, mixes the edge-tts voiceover, outputs vertical MP4."""
import subprocess, math, sys, os

W, H = 1080, 1920
FPS = 30
BG = (13, 17, 23)          # gh-dark background
PANEL = (22, 27, 34)
GREEN = (63, 185, 80)
BLUE = (88, 166, 255)
DIM = (139, 148, 158)
FG = (230, 237, 243)
YELLOW = (250, 200, 60)
RED = (248, 81, 73)
ACCENT = (188, 140, 255)   # purple accent (JollyOS-ish)

from PIL import Image, ImageDraw, ImageFont

FONTS = r"C:\Windows\Fonts"
mono   = ImageFont.truetype(os.path.join(FONTS, "consola.ttf"), 34)
mono_b = ImageFont.truetype(os.path.join(FONTS, "consolab.ttf"), 34)
mono_big = ImageFont.truetype(os.path.join(FONTS, "consolab.ttf"), 44)
cap_big  = ImageFont.truetype(os.path.join(FONTS, "segoeuib.ttf"), 78)
cap_med  = ImageFont.truetype(os.path.join(FONTS, "segoeuib.ttf"), 46)

LINE_H = 46
TERM_X, TERM_Y = 48, 240   # terminal content origin
TERM_W = W - 96

# ---- timeline -------------------------------------------------------------
# (name, length_s, vo_file, vo_start_s_global)  vo starts computed below
BEATS = [
    ("hook",   3.9),
    ("type",   3.2),
    ("mine",   6.5),
    ("reveal", 5.2),
    ("zoom",   4.6),
    ("card",   5.5),
]
starts = {}
t = 0.0
for name, ln in BEATS:
    starts[name] = t
    t += ln
TOTAL = t
VO_DELAY_MS = {  # per-clip delay into the global timeline
    "b1": int((starts["hook"] + 0.30) * 1000),
    "b2": int((starts["type"] + 0.20) * 1000),
    "b3": int((starts["mine"] + 0.35) * 1000),
    "b4": int((starts["reveal"] + 0.30) * 1000),
    "b5": int((starts["zoom"] + 0.40) * 1000),
    "b6": int((starts["card"] + 0.30) * 1000),
}

# ---- content --------------------------------------------------------------
MINE_LINES = [
    (GREEN, "* Running mine_gripes.py..."),
    (DIM,   "  scanned 97 sessions - found 60 gripe candidates"),
    (BLUE,  "* Grep(pattern: \"session reset\", path: src/)"),
    (BLUE,  "* Read(src/web_app.py)"),
    (BLUE,  "* Grep(pattern: \"reconnect\", path: lib/)"),
    (BLUE,  "* Read(lib/claude-cli.ts)"),
    (DIM,   "  verifying 12 leads against the codebase..."),
    (GREEN, "  OK 3 still open - 8 already fixed - 1 dropped"),
    (GREEN, "* Write(GRIPES.md)"),
]
GRIPES = [
    ("# GRIPES.md", ACCENT, False),
    ("", FG, False),
    ("[ ] Dashboard session resets on refresh", FG, True),   # highlighted
    ("    (you said: \"why does this keep", YELLOW, True),
    ("     resetting\", x3)", YELLOW, True),
    ("", FG, False),
    ("[ ] Phantom duplicate background tasks", FG, False),
    ("    (you said: \"why does it say you're", DIM, False),
    ("     running two tasks?\")", DIM, False),
    ("", FG, False),
    ("[ ] Dev-server connection instability", FG, False),
    ("    (you said: \"why is my connection so", DIM, False),
    ("     unstable?\")", DIM, False),
]

def chrome(d):
    d.rectangle([0, 0, W, 160], fill=PANEL)
    for i, c in enumerate([RED, YELLOW, GREEN]):
        d.ellipse([48 + i * 56, 62, 84 + i * 56, 98], fill=c)
    d.text((W // 2, 80), "claude", font=mono_b, fill=DIM, anchor="mm")

def caption(d, text, y=1700, font=cap_med, fill=FG):
    d.text((W // 2 + 3, y + 3), text, font=font, fill=(0, 0, 0), anchor="mm")
    d.text((W // 2, y), text, font=font, fill=fill, anchor="mm")

def cursor_on(tsec):
    return (tsec % 1.0) < 0.55

def base_frame():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)

def draw_prompt(d, typed, tsec, y):
    d.text((TERM_X, y), "> ", font=mono_b, fill=GREEN)
    d.text((TERM_X + 42, y), typed, font=mono_b, fill=FG)
    if cursor_on(tsec):
        w = d.textlength(typed, font=mono_b)
        d.rectangle([TERM_X + 46 + w, y, TERM_X + 46 + w + 20, y + 38], fill=FG)

def frame_at(tg):
    """Render the frame for global time tg."""
    img, d = base_frame()
    chrome(d)
    if tg < starts["type"]:
        # HOOK: empty terminal + big caption
        tl = tg - starts["hook"]
        draw_prompt(d, "", tg, TERM_Y)
        caption(d, "Claude Code secretly logs", 860, cap_big)
        caption(d, "every time you got annoyed.", 960, cap_big, YELLOW)
    elif tg < starts["mine"]:
        # TYPE: /gripe-miner typed out
        tl = tg - starts["type"]
        cmd = "/gripe-miner"
        n = min(len(cmd), int(tl / 1.1 * len(cmd)))
        draw_prompt(d, cmd[:n], tg, TERM_Y)
        caption(d, "So I built a plugin that reads them back.")
    elif tg < starts["reveal"]:
        # MINE: output scrolls in
        tl = tg - starts["mine"]
        d.text((TERM_X, TERM_Y), "> ", font=mono_b, fill=GREEN)
        d.text((TERM_X + 42, TERM_Y), "/gripe-miner", font=mono_b, fill=FG)
        shown = min(len(MINE_LINES), int(tl / 5.4 * len(MINE_LINES)) + 1)
        for i in range(shown):
            col, txt = MINE_LINES[i]
            d.text((TERM_X, TERM_Y + (i + 2) * LINE_H), txt, font=mono, fill=col)
        caption(d, "It checks every complaint")
        caption(d, "against my actual code.", 1770)
    elif tg < starts["card"]:
        # REVEAL + ZOOM: GRIPES.md file view
        in_zoom = tg >= starts["zoom"]
        tl = tg - starts["reveal"]
        d.rectangle([24, 200, W - 24, 1560], fill=PANEL)
        d.text((48, 224), "GRIPES.md", font=mono_b, fill=ACCENT)
        d.line([24, 290, W - 24, 290], fill=BG, width=3)
        if not in_zoom:
            shown = min(len(GRIPES), int(tl / 3.4 * len(GRIPES)) + 1)
        else:
            shown = len(GRIPES)
        for i in range(shown):
            txt, col, hl = GRIPES[i]
            y = 330 + i * LINE_H
            if hl and in_zoom:
                d.rectangle([36, y - 6, W - 36, y + 40], fill=(60, 50, 14))
            d.text((60, y), txt, font=mono, fill=col)
        if in_zoom:
            # animated zoom onto the highlighted block
            zl = tg - starts["zoom"]
            f = 1.0 + 0.38 * min(1.0, zl / 1.6)
            cx, cy = int(W * 0.36), 330 + 3 * LINE_H   # center of highlight block (left-weighted so text isn't clipped)
            cw, ch = W / f, H / f
            x0 = max(0, min(W - cw, cx - cw / 2))
            y0 = max(0, min(H - ch, cy - ch / 2))
            img = img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
            d = ImageDraw.Draw(img)
            caption(d, "Complained three times.", 1640)
            caption(d, "Never fixed. It remembered.", 1710, fill=YELLOW)
        else:
            caption(d, "Every item is my own words,", 1680)
            caption(d, "quoted back at me.", 1750)
    else:
        # CARD: install lines
        tl = tg - starts["card"]
        d.text((W // 2, 560), "GRIPE MINER", font=ImageFont.truetype(
            os.path.join(FONTS, "segoeuib.ttf"), 110), fill=ACCENT, anchor="mm")
        d.text((W // 2, 680), "your frustration, productized", font=cap_med, fill=DIM, anchor="mm")
        d.rectangle([48, 860, W - 48, 1130], fill=PANEL)
        d.text((84, 910), "/plugin marketplace add", font=mono_big, fill=GREEN)
        d.text((84, 970), "    jtollyinc/gripe-miner", font=mono_big, fill=FG)
        d.text((84, 1040), "/plugin install", font=mono_big, fill=GREEN)
        d.text((84, 1100), "    gripe-miner@jtolly-tools", font=mono_big, fill=FG)
        caption(d, "Free  ·  MIT  ·  100% local", 1300, cap_med, YELLOW)
        caption(d, "Link in bio.", 1420)
    return img

# ---- encode ---------------------------------------------------------------
out = sys.argv[1] if len(sys.argv) > 1 else "gripe-miner-demo.mp4"
vo = lambda n: os.path.join("vo", n + ".mp3")
fc_parts, mix_ins = [], ""
for i, clip in enumerate(["b1", "b2", "b3", "b4", "b5", "b6"]):
    fc_parts.append(f"[{i+1}:a]adelay={VO_DELAY_MS[clip]}|{VO_DELAY_MS[clip]}[a{i}]")
    mix_ins += f"[a{i}]"
fc = ";".join(fc_parts) + f";{mix_ins}amix=inputs=6:normalize=0[aout]"

cmd = ["ffmpeg", "-y",
       "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
for clip in ["b1", "b2", "b3", "b4", "b5", "b6"]:
    cmd += ["-i", vo(clip)]
cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-t", f"{TOTAL:.2f}", "-shortest", out]

proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
total_frames = int(TOTAL * FPS)
for n in range(total_frames):
    frm = frame_at(n / FPS)
    proc.stdin.write(frm.tobytes())
    if n % 150 == 0:
        print(f"frame {n}/{total_frames}", flush=True)
proc.stdin.close()
proc.wait()
print(f"done: {out} ({TOTAL:.1f}s, {total_frames} frames), exit {proc.returncode}")
