#!/usr/bin/env python3
"""LPWN Reels: hook on the first frame, under 12 seconds.

1080x1920, 30 fps, H.264 + silent AAC 48 kHz (the Reels format the daily video uses).
Look: LPWN brand kit black/orange/amber, Inter type, no AI pictures.

Usage: python3 render_reels.py [slug-prefix ...]   (no args = every reel)
Writes out/<file>.mp4, out/<file>.jpg (cover = first frame) and check/<file>.png (contact sheet).
"""
import math
import os
import random
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CHECK = os.path.join(HERE, "check")

FONT_DIR = "/usr/share/fonts/opentype/inter"
FONT_FILES = {
    "black": "InterDisplay-Black.otf",
    "xbold": "Inter-ExtraBold.otf",
    "bold": "Inter-Bold.otf",
    "semi": "Inter-SemiBold.otf",
    "med": "Inter-Medium.otf",
}
_fonts = {}


def font(kind, size):
    key = (kind, int(size))
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONT_DIR, FONT_FILES[kind]), int(size))
    return _fonts[key]


# LPWN brand kit
BLACK = (20, 20, 20)      # #141414
ORANGE = (255, 138, 0)    # #FF8A00
AMBER = (255, 180, 0)     # #FFB400
WHITE = (255, 255, 255)
GRAY = (172, 168, 162)
RED = (236, 64, 52)
TAG_COLORS = {"o": ORANGE, "a": AMBER, "w": WHITE, "g": GRAY, "r": RED}

MARGIN_X = 90
MAX_W = W - 2 * MARGIN_X      # 900
CONTENT_CY = 790              # visual center of the message
SOURCE_Y = 1262               # baseline of the source line
FOOTER_CY = 1352              # center of the website pill
PROGRESS_Y = 312

# ---------------------------------------------------------------- text helpers
TAG = re.compile(r"\[(/?)([oawgr])\]")


def plain(markup):
    return TAG.sub("", markup)


def parse_rich(markup, default):
    """Words as lists of (text, color) pieces; [o]..[/o] marks orange, [a] amber, [r] red, [g] gray."""
    pieces, stack, pos = [], [default], 0
    for m in TAG.finditer(markup):
        if m.start() > pos:
            pieces.append((markup[pos:m.start()], stack[-1]))
        if m.group(1):
            if len(stack) > 1:
                stack.pop()
        else:
            stack.append(TAG_COLORS[m.group(2)])
        pos = m.end()
    if pos < len(markup):
        pieces.append((markup[pos:], stack[-1]))
    words, cur = [], []
    for text, col in pieces:
        for part in re.split(r"( )", text):
            if part == " ":
                if cur:
                    words.append(cur)
                    cur = []
            elif part:
                cur.append((part, col))
    if cur:
        words.append(cur)
    return words


def word_w(word, fnt):
    return sum(fnt.getlength(t) for t, _ in word)


def line_w(line, fnt):
    return sum(word_w(w, fnt) for w in line) + fnt.getlength(" ") * (len(line) - 1)


def wrap(words, fnt, max_w):
    lines, cur = [], []
    for w in words:
        if cur and line_w(cur + [w], fnt) > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def balance(words, fnt, max_w):
    """Wrap, then even out line lengths so the last line isn't a lonely word."""
    lines = wrap(words, fnt, max_w)
    if len(lines) < 2:
        return lines
    best, best_w = lines, max(line_w(l, fnt) for l in lines)
    lo = int(max_w * 0.55)
    for mw in range(int(max_w), lo, -10):
        trial = wrap(words, fnt, mw)
        if len(trial) != len(lines):
            break
        tw = max(line_w(l, fnt) for l in trial)
        if tw < best_w:
            best, best_w = trial, tw
    return best


def cap_h(fnt):
    return -fnt.getbbox("H", anchor="ls")[1]


def desc_h(fnt):
    return fnt.getbbox("gjpqy", anchor="ls")[3]


def draw_line(d, line, fnt, x, baseline):
    space = fnt.getlength(" ")
    for i, word in enumerate(line):
        for text, col in word:
            d.text((x, baseline), text, font=fnt, fill=col + (255,), anchor="ls")
            x += fnt.getlength(text)
        if i < len(line) - 1:
            x += space


def tracked_width(text, fnt, track):
    return sum(fnt.getlength(c) for c in text) + track * (len(text) - 1)


def draw_tracked(d, text, fnt, x, baseline, color, track):
    for c in text:
        d.text((x, baseline), c, font=fnt, fill=color + (255,), anchor="ls")
        x += fnt.getlength(c) + track


def draw_pill(d, text, fnt, cx, cy, bg, fg, pad_x, pad_y, track=0):
    ch = cap_h(fnt)
    tw = tracked_width(text, fnt, track)
    w, h = tw + 2 * pad_x, ch + 2 * pad_y
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=h / 2, fill=bg + (255,))
    draw_tracked(d, text, fnt, cx - tw / 2, y0 + pad_y + ch, fg, track)
    return w, h


# ---------------------------------------------------------------- message blocks
def fit_size(row):
    kind = row.get("font", "black")
    words = parse_rich(row["text"], row.get("color", WHITE))
    size = row["size"]
    while size > 24 and line_w(words, font(kind, size)) > MAX_W:
        size -= 4
    return size


def prepare(rows):
    rows = [dict(r) for r in rows]
    groups = {}
    for r in rows:
        if r["t"] == "big":
            r["size"] = fit_size(r)
            if r.get("fit"):
                groups.setdefault(r["fit"], []).append(r)
    for members in groups.values():
        s = min(m["size"] for m in members)
        for m in members:
            m["size"] = s
    return rows


def row_metrics(r):
    t = r["t"]
    if t == "gap":
        return dict(h=r["h"])
    if t in ("big", "text"):
        kind = r.get("font", "black" if t == "big" else "xbold")
        color = r.get("color", WHITE)
        size = r["size"]
        while True:
            f = font(kind, size)
            words = parse_rich(r["text"], color)
            lines = [words] if t == "big" else balance(words, f, r.get("max_w", MAX_W))
            if t == "big" or len(lines) <= r.get("max_lines", 4) or size <= 30:
                break
            size -= 2
        ch = cap_h(f)
        lead = r.get("lead", 0.16 if t == "big" else 0.46) * size
        dh = desc_h(f) * 0.85 if re.search(r"[gjpqy,]", plain(r["text"])) else 0
        h = len(lines) * ch + (len(lines) - 1) * lead + dh
        return dict(h=h, f=f, lines=lines, ch=ch, lead=lead)
    if t == "label":
        f = font(r.get("font", "semi"), r["size"])
        return dict(h=cap_h(f), f=f)
    if t == "pill":
        f = font(r.get("font", "black"), r["size"])
        pad_y = int(r["size"] * 0.46)
        return dict(h=cap_h(f) + 2 * pad_y, f=f, pad_y=pad_y)
    raise ValueError(t)


def render_block(rows, cy=CONTENT_CY):
    rows = prepare(rows)
    mets = [row_metrics(r) for r in rows]
    total = sum(m["h"] for m in mets)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = cy - total / 2
    for r, m in zip(rows, mets):
        t = r["t"]
        if t in ("big", "text"):
            for i, line in enumerate(m["lines"]):
                baseline = y + m["ch"] + i * (m["ch"] + m["lead"])
                draw_line(d, line, m["f"], (W - line_w(line, m["f"])) / 2, baseline)
        elif t == "label":
            track = r.get("track", 0)
            tw = tracked_width(r["text"], m["f"], track)
            draw_tracked(d, r["text"], m["f"], (W - tw) / 2, y + m["h"], r.get("color", GRAY), track)
        elif t == "pill":
            draw_pill(d, r["text"], m["f"], W / 2, y + m["h"] / 2, r["bg"], r["fg"],
                      int(r["size"] * 0.9), m["pad_y"], r.get("track", 3))
        y += m["h"]
    bbox = img.getbbox()
    if not bbox:
        raise ValueError("empty block")
    if bbox[1] < PROGRESS_Y + 40 or bbox[3] > SOURCE_Y - 50:
        print(f"  ! block runs into the header/footer area: {bbox}", file=sys.stderr)
    return img.crop(bbox), bbox


# ---------------------------------------------------------------- background
_grid = None


def grid():
    global _grid
    if _grid is None:
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        _grid = (xs, ys)
    return _grid


def make_base(reel, glow_color):
    xs, ys = grid()
    top = np.array([26, 25, 24], np.float32)
    bot = np.array([13, 13, 13], np.float32)
    k = (ys / H)[..., None]
    base = top * (1 - k) + bot * k
    dx = (xs - W / 2) / (W * 0.62)
    dy = (ys - CONTENT_CY) / (H * 0.30)
    g = np.exp(-(dx * dx + dy * dy) * 1.5)
    base = base + g[..., None] * np.array(glow_color, np.float32) * 0.14
    vx, vy = (xs - W / 2) / (W / 2), (ys - H / 2) / (H / 2)
    base = base * (1 - 0.30 * np.clip((vx * vx + vy * vy) / 2, 0, 1) ** 1.2)[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(img)

    # header: wordmark left, series pill right
    d.text((MARGIN_X, 232), "LA PORTE", font=font("black", 52), fill=WHITE + (255,), anchor="ls")
    draw_tracked(d, "WEATHER NOW", font("xbold", 25), MARGIN_X + 2, 270, ORANGE, 5.5)
    pf = font("black", 30)
    pw = tracked_width(reel["pill"], pf, 2.5) + 2 * 26
    draw_pill(d, reel["pill"], pf, W - MARGIN_X - pw / 2, 232, ORANGE, BLACK, 26, 16, track=2.5)

    # footer: source line and website
    if reel.get("source"):
        sf = font("med", 34)
        d.text(((W - sf.getlength(reel["source"])) / 2, SOURCE_Y), reel["source"], font=sf,
               fill=GRAY + (255,), anchor="ls")
    draw_pill(d, "laporteweathernow.com", font("xbold", 44), W / 2, FOOTER_CY, ORANGE, BLACK, 42, 25)
    return img


# ---------------------------------------------------------------- weather layer
class Particles:
    def __init__(self, kind, seed):
        self.kind = kind
        rng = random.Random(seed)
        self.p = []
        if kind == "rain":
            for _ in range(62):
                self.p.append(dict(x=rng.uniform(0, W + 400), y=rng.uniform(0, H + 200), L=rng.uniform(40, 95),
                                   a=int(rng.uniform(40, 80)), v=rng.uniform(1300, 1900), w=rng.choice([2, 2, 3])))
        elif kind == "snow":
            for _ in range(105):
                r = rng.uniform(2, 6.5)
                self.p.append(dict(x=rng.uniform(0, W), y=rng.uniform(0, H + 40), r=r,
                                   a=int(rng.uniform(70, 150) * (0.65 + r / 18)), v=40 + r * 26 + rng.uniform(-10, 10),
                                   amp=rng.uniform(12, 40), fq=rng.uniform(0.2, 0.6), ph=rng.uniform(0, 6.28)))
        elif kind in ("frost", "sparkle"):
            n = 70 if kind == "frost" else 54
            for _ in range(n):
                self.p.append(dict(x=rng.uniform(0, W), y=rng.uniform(0, H), r=rng.uniform(1.6, 4.2),
                                   a=rng.uniform(70, 175), v=rng.uniform(-16, -4) if kind == "frost" else rng.uniform(-42, -16),
                                   fq=rng.uniform(0.35, 1.1), ph=rng.uniform(0, 6.28)))

    def draw(self, d, t):
        k = self.kind
        if k == "rain":
            ang = math.radians(13)
            tx, sx, sy = math.tan(ang), math.sin(ang), math.cos(ang)
            for p in self.p:
                yr = p["y"] + p["v"] * t
                y = yr % (H + 200) - 100
                x = (p["x"] + yr * tx) % (W + 400) - 200
                d.line([(x, y), (x - p["L"] * sx, y - p["L"] * sy)], fill=(176, 196, 222, p["a"]), width=p["w"])
        elif k == "snow":
            for p in self.p:
                y = (p["y"] + p["v"] * t) % (H + 40) - 20
                x = p["x"] + p["amp"] * math.sin(2 * math.pi * p["fq"] * t + p["ph"])
                r = p["r"]
                d.ellipse([x - r, y - r, x + r, y + r], fill=(236, 242, 255, p["a"]))
        else:
            col = (206, 228, 255) if k == "frost" else (255, 198, 122)
            for p in self.p:
                y = (p["y"] + p["v"] * t) % H
                x = p["x"]
                tw = 0.5 + 0.5 * math.sin(2 * math.pi * p["fq"] * t + p["ph"])
                a = int(p["a"] * (0.25 + 0.75 * tw))
                r = p["r"]
                d.ellipse([x - r, y - r, x + r, y + r], fill=col + (a,))
                if k == "frost" and r > 3:
                    s = r * 3.2
                    d.line([(x - s, y), (x + s, y)], fill=col + (a // 2,), width=2)
                    d.line([(x, y - s), (x, y + s)], fill=col + (a // 2,), width=2)


# ---------------------------------------------------------------- animation
ENTER, EXIT = 0.38, 0.22


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in(x):
    return x ** 3


def beat_state(b, t, first, last):
    if t < b["start"] - 1e-9 or (t >= b["end"] - 1e-9 and not last):
        return None
    alpha, dy, scale = 1.0, 0.0, 1.0
    if not first and t < b["start"] + ENTER:
        p = ease_out((t - b["start"]) / ENTER)
        alpha, dy, scale = p, (1 - p) * 60, 0.94 + 0.06 * p
    if not last and t > b["end"] - EXIT:
        q = ease_in((t - (b["end"] - EXIT)) / EXIT)
        alpha *= 1 - q
        dy -= q * 40
    return alpha, dy, scale


def draw_progress(d, t, dur):
    x0, x1, h = MARGIN_X, W - MARGIN_X, 8
    d.rounded_rectangle([x0, PROGRESS_Y, x1, PROGRESS_Y + h], radius=4, fill=(255, 255, 255, 34))
    xe = x0 + (x1 - x0) * min(1.0, t / dur)
    if xe - x0 >= h:
        d.rounded_rectangle([x0, PROGRESS_Y, xe, PROGRESS_Y + h], radius=4, fill=ORANGE + (255,))


def render_reel(reel):
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CHECK, exist_ok=True)
    beats = reel["beats"]
    t0 = 0.0
    for b in beats:
        b["start"], t0 = t0, t0 + b["dur"]
        b["end"] = t0
    dur = t0
    n = int(round(dur * FPS))
    blocks = [render_block(b["rows"]) for b in beats]

    keys = reel.get("glow", [(0.0, ORANGE)])
    bases = {}
    for _, col in keys:
        if col not in bases:
            bases[col] = make_base(reel, col)
    arrays = {c: np.asarray(img, dtype=np.float32) for c, img in bases.items()} if len(bases) > 1 else {}

    def base_at(t):
        idx = max(i for i, (kt, _) in enumerate(keys) if kt <= t + 1e-9)
        kt, col = keys[idx]
        if idx == 0 or t - kt >= 0.45:
            return bases[col]
        w = (t - kt) / 0.45
        prev = keys[idx - 1][1]
        mix = arrays[prev] * (1 - w) + arrays[col] * w
        return Image.fromarray(mix.astype(np.uint8), "RGBA")

    parts = Particles(reel["particles"], seed=sum(map(ord, reel["file"])))
    mp4 = os.path.join(OUT, reel["file"] + ".mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
           "-map", "0:v", "-map", "1:a", "-shortest",
           "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-g", "60", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    sample_t = [0.0] + [b["start"] + b["dur"] * 0.62 for b in beats] + [dur - 1 / FPS]
    sample_f = sorted({min(n - 1, int(round(s * FPS))) for s in sample_t})
    samples = []
    for i in range(n):
        t = i / FPS
        frame = base_at(t).copy()
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        parts.draw(od, t)
        draw_progress(od, t, dur)
        frame.alpha_composite(ov)
        for bi, b in enumerate(beats):
            st = beat_state(b, t, bi == 0, bi == len(beats) - 1)
            if st is None or st[0] <= 0.003:
                continue
            alpha, dy, scale = st
            im, bbox = blocks[bi]
            x, y = bbox[0], bbox[1]
            if abs(scale - 1) > 1e-3:
                nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
                cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
                im = im.resize((nw, nh), Image.BICUBIC)
                x, y = cx - nw / 2, cy - nh / 2
            if alpha < 0.999:
                a = im.getchannel("A").point(lambda v, al=alpha: int(v * al))
                im = im.copy()
                im.putalpha(a)
            frame.alpha_composite(im, dest=(int(round(x)), int(round(y + dy))))
        rgb = frame.convert("RGB")
        proc.stdin.write(rgb.tobytes())
        if i == 0:
            rgb.save(os.path.join(OUT, reel["file"] + ".jpg"), quality=90)
        if i in sample_f:
            samples.append(rgb.resize((360, 640), Image.LANCZOS))
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit(f"ffmpeg failed for {reel['file']}")
    sheet = Image.new("RGB", (360 * len(samples) + 10 * (len(samples) - 1), 640), (255, 255, 255))
    for k, s in enumerate(samples):
        sheet.paste(s, (k * 370, 0))
    sheet.save(os.path.join(CHECK, reel["file"] + ".png"))
    print(f"{reel['file']}.mp4  {dur:.1f} s  {os.path.getsize(mp4) / 1e6:.1f} MB")


# ---------------------------------------------------------------- the five Reels
SRC = "Source: National Weather Service"
NO_HYPE = dict(t="text", text="No hype. Just the forecast.", size=48, color=GRAY, font="semi")

REELS = [
    dict(file="lpwn-reel-1-rain-chance", pill="MYTH-BUSTER #1", particles="rain", source=SRC, beats=[
        dict(dur=2.8, rows=[
            dict(t="label", text="WHAT DOES", size=46, color=GRAY, track=10),
            dict(t="gap", h=30),
            dict(t="big", text="[o]40%[/o]", size=380),
            dict(t="gap", h=40),
            dict(t="big", text="CHANCE OF RAIN", size=124, fit="h"),
            dict(t="gap", h=22),
            dict(t="big", text="REALLY MEAN?", size=124, fit="h"),
        ]),
        dict(dur=2.8, rows=[
            dict(t="big", text="[o]NOT[/o]", size=300),
            dict(t="gap", h=40),
            dict(t="text", text="rain for 40% of the day.", size=88, font="black"),
        ]),
        dict(dur=2.9, rows=[
            dict(t="text", text="It’s a", size=80),
            dict(t="gap", h=24),
            dict(t="big", text="[o]4 IN 10[/o]", size=250),
            dict(t="gap", h=30),
            dict(t="text", text="chance [o]your spot[/o] gets measurable rain.", size=78),
            dict(t="gap", h=34),
            dict(t="text", text="Measurable = at least 0.01 inch during that forecast period.", size=44,
                 color=GRAY, font="semi"),
        ]),
        dict(dur=2.6, rows=[
            dict(t="text", text="So at 40%?", size=84),
            dict(t="gap", h=36),
            dict(t="big", text="[o]KEEP AN[/o]", size=150, fit="u"),
            dict(t="gap", h=30),
            dict(t="big", text="[o]UMBRELLA[/o]", size=150, fit="u"),
            dict(t="gap", h=30),
            dict(t="big", text="[o]IN THE CAR.[/o]", size=150, fit="u"),
            dict(t="gap", h=48),
            NO_HYPE,
        ]),
    ]),
    dict(file="lpwn-reel-2-watch-vs-warning", pill="MYTH-BUSTER #2", particles="rain", source=SRC,
         glow=[(0.0, ORANGE), (2.8, AMBER), (5.6, RED), (8.4, ORANGE)], beats=[
        dict(dur=2.8, rows=[
            dict(t="big", text="[a]WATCH[/a]", size=230, fit="w"),
            dict(t="gap", h=22),
            dict(t="text", text="or", size=72, color=GRAY),
            dict(t="gap", h=30),
            dict(t="big", text="[r]WARNING?[/r]", size=230, fit="w"),
            dict(t="gap", h=56),
            dict(t="text", text="Only one means act now.", size=76),
        ]),
        dict(dur=2.8, rows=[
            dict(t="pill", text="WATCH", size=60, bg=AMBER, fg=BLACK),
            dict(t="gap", h=60),
            dict(t="text", text="The ingredients are there. It could happen.", size=80),
            dict(t="gap", h=60),
            dict(t="big", text="[a]GET READY.[/a]", size=170),
        ]),
        dict(dur=2.8, rows=[
            dict(t="pill", text="WARNING", size=60, bg=RED, fg=WHITE),
            dict(t="gap", h=60),
            dict(t="text", text="It’s happening or about to.", size=80),
            dict(t="gap", h=60),
            dict(t="big", text="[r]ACT NOW.[/r]", size=200),
        ]),
        dict(dur=2.7, rows=[
            dict(t="text", text="Easy way to remember:", size=56, color=GRAY, font="semi"),
            dict(t="gap", h=46),
            dict(t="big", text="[a]WATCH[/a] = GET READY", size=110, fit="m"),
            dict(t="gap", h=34),
            dict(t="big", text="[r]WARNING[/r] = ACT NOW", size=110, fit="m"),
            dict(t="gap", h=60),
            dict(t="text", text="Save this for storm season.", size=58),
        ]),
    ]),
    dict(file="lpwn-reel-3-frost-at-36", pill="MYTH-BUSTER #3", particles="frost", source=SRC, beats=[
        dict(dur=2.8, rows=[
            dict(t="big", text="FROST", size=250, fit="f"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]AT 36°F?[/o]", size=250, fit="f"),
            dict(t="gap", h=60),
            dict(t="text", text="Yep. Here’s why.", size=84),
        ]),
        dict(dur=2.8, rows=[
            dict(t="text", text="Official temperatures are measured about", size=74),
            dict(t="gap", h=36),
            dict(t="big", text="[o]6 FEET UP[/o]", size=210),
            dict(t="gap", h=36),
            dict(t="text", text="off the ground.", size=74),
        ]),
        dict(dur=3.0, rows=[
            dict(t="text", text="On clear, calm nights the ground and your windshield can get", size=74),
            dict(t="gap", h=44),
            dict(t="big", text="[o]SEVERAL DEGREES[/o]", size=130, fit="c"),
            dict(t="gap", h=30),
            dict(t="big", text="[o]COLDER.[/o]", size=130, fit="c"),
        ]),
        dict(dur=2.6, rows=[
            dict(t="text", text="Clear, calm, and a low in the mid-30s?", size=70),
            dict(t="gap", h=46),
            dict(t="big", text="[o]COVER YOUR[/o]", size=150, fit="p"),
            dict(t="gap", h=30),
            dict(t="big", text="[o]PLANTS.[/o]", size=150, fit="p"),
            dict(t="gap", h=50),
            NO_HYPE,
        ]),
    ]),
    dict(file="lpwn-reel-4-lake-effect", pill="MYTH-BUSTER #4", particles="snow", source=SRC, beats=[
        dict(dur=3.0, rows=[
            dict(t="text", text="How can La Porte get", size=84),
            dict(t="gap", h=30),
            dict(t="big", text="[o]BURIED[/o]", size=260),
            dict(t="gap", h=30),
            dict(t="text", text="while Chicago stays sunny?", size=84),
        ]),
        dict(dur=3.0, rows=[
            dict(t="text", text="Cold air blows across", size=78),
            dict(t="gap", h=34),
            dict(t="big", text="[o]WARMER[/o]", size=160, fit="l"),
            dict(t="gap", h=28),
            dict(t="big", text="[o]LAKE WATER[/o]", size=160, fit="l"),
            dict(t="gap", h=34),
            dict(t="text", text="and picks up heat and moisture.", size=72),
        ]),
        dict(dur=3.0, rows=[
            dict(t="text", text="The air rises and drops snow in", size=76),
            dict(t="gap", h=34),
            dict(t="big", text="[o]NARROW BANDS[/o]", size=150),
            dict(t="gap", h=34),
            dict(t="text", text="downwind of the lake.", size=76),
        ]),
        dict(dur=2.6, rows=[
            dict(t="text", text="One town gets", size=84, font="black"),
            dict(t="gap", h=22),
            dict(t="big", text="[o]BURIED.[/o]", size=180, fit="b"),
            dict(t="gap", h=50),
            dict(t="text", text="The next gets a", size=84, font="black"),
            dict(t="gap", h=22),
            dict(t="big", text="[o]DUSTING.[/o]", size=180, fit="b"),
            dict(t="gap", h=50),
            dict(t="text", text="That’s lake-effect snow.", size=56, color=GRAY, font="semi"),
        ]),
    ]),
    dict(file="lpwn-reel-5-send-your-sky", pill="COMMUNITY", particles="sparkle", source=None, beats=[
        dict(dur=3.0, rows=[
            dict(t="text", text="Calling all La Porte", size=84),
            dict(t="gap", h=34),
            dict(t="big", text="[o]SKY[/o]", size=230, fit="s"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]WATCHERS[/o]", size=230, fit="s"),
            dict(t="gap", h=50),
            dict(t="text", text="Sunrises. Storms. Frost. First snow.", size=60, color=GRAY, font="semi"),
        ]),
        dict(dur=3.0, rows=[
            dict(t="big", text="SEND US", size=170, fit="y"),
            dict(t="gap", h=28),
            dict(t="big", text="[o]YOUR SKY.[/o]", size=170, fit="y"),
            dict(t="gap", h=54),
            dict(t="text", text="Comment with a photo or message the Page.", size=68),
        ]),
        dict(dur=3.0, rows=[
            dict(t="text", text="We’ll feature the best ones", size=76),
            dict(t="gap", h=34),
            dict(t="big", text="[o]WITH YOUR[/o]", size=170, fit="n"),
            dict(t="gap", h=28),
            dict(t="big", text="[o]NAME.[/o]", size=170, fit="n"),
            dict(t="gap", h=54),
            dict(t="text", text="Only send photos you took yourself.", size=50, color=GRAY, font="semi"),
        ]),
    ]),
]

if __name__ == "__main__":
    want = sys.argv[1:]
    for reel in REELS:
        if not want or any(reel["file"].startswith(w) or w in reel["file"] for w in want):
            render_reel(reel)
