#!/usr/bin/env python3
"""Four spooky Halloween shorts for TikTok and YouTube (Oct. 20, 2026; Scoop: "make a few different shorts
and posts for retention rate", "make them really cool and spooky").

    python3 tools/video/belle-2026/shorts.py OUTDIR [belle-1 belle-2 hours ghost-train] [--stills]

Each one is 1080x1920, 30 fps, H.264 + AAC 48 kHz (the Daily Video's format), 10 to 21 seconds, made for
watching to the end: the hook is on screen in the first frame, captions follow the narrator word by word,
the picture changes every couple of seconds, and there's no slow intro or long end card.

The narration is the weather radio's voice (Kokoro-82M af_heart), recorded by voice.py in GitHub Actions
(voice/, with each word's timing). Everything else is made here: the pictures are drawn in code (no photos,
stock footage or AI pictures) and the music and sounds are written in code (no recordings). The facts are in
lines.json's notes; the trick-or-treat hours come from trick-or-treat.json (checked Oct. 20).
"""
import importlib.util
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ImageChops_sub = ImageChops.subtract

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vr = _load("video_render", os.path.join(REPO, "scripts", "video_render.py"))
hw = _load("halloween_make", os.path.join(REPO, "tools", "video", "halloween-2026", "make.py"))

W, H, FPS = vr.W, vr.H, vr.FPS
X0, CW = vr.X0, vr.CW
SR = 48000
BONE = (243, 234, 219)
SEPIA = (226, 206, 168)
INKC = (36, 26, 18)
BLOOD = (206, 38, 32)
EMBER = (255, 150, 40)
ORANGE, GOLDEN, CREAM, LAV = hw.ORANGE, hw.GOLDEN, hw.CREAM, hw.LAV
BASK = "/usr/share/fonts/truetype/baskerville/GFSBaskerville.otf"
LORA = "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
_fc = {}


def F(kind, size):
    key = (kind, int(size))
    if key not in _fc:
        if kind in ("bask", "lora"):   # Lora Bold for the old-time titles (GFS Baskerville turned out to be Greek-only)
            f = ImageFont.truetype(LORA, int(size))
            f.set_variation_by_name(b"Bold")
        elif kind == "mono":
            f = ImageFont.truetype(MONO, int(size))
        else:
            f = vr.font(kind, size)
        _fc[key] = f
    return _fc[key]


def T(text, kind, size, fill, stroke=0, stroke_fill=(0, 0, 0), tracking=0):
    """One line of text, cropped to its ink (with an outline if stroke)."""
    f = F(kind, size)
    if tracking:
        widths = [f.getlength(c) for c in text]
        w = int(sum(widths) + tracking * (len(text) - 1)) + 4 * stroke + 16
    else:
        w = int(f.getlength(text)) + 4 * stroke + 16
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (max(w, 1), asc + desc + 4 * stroke + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tracking:
        x = 8 + 2 * stroke
        for c, cw in zip(text, widths):
            d.text((x, 8 + 2 * stroke), c, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
            x += cw + tracking
    else:
        d.text((8 + 2 * stroke, 8 + 2 * stroke), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    box = img.getbbox()
    return img.crop(box) if box else img


def fitT(text, kind, size, fill, max_w=CW, min_size=30, **kw):
    s = size
    while s > min_size and F(kind, s).getlength(text) + kw.get("tracking", 0) * len(text) > max_w:
        s -= 4
    return T(text, kind, s, fill, **kw)


def glowT(img, color, radius=24, strength=0.7):
    g = vr.glow(img, color, radius=radius, strength=strength)
    return g, g.info["pad"]


def paste_c(frame, img, cx, cy, alpha=1.0):
    if alpha <= 0:
        return
    if alpha < 0.999:
        img = vr.with_alpha(img, alpha)
    frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def ease(u):
    return vr.ease(u)


def appear(u, at, dur=0.28):
    return ease((u - at) / dur) if u >= at else 0.0


# ---------------------------------------------------------------------------------------------
# Atmosphere: fog, grain, vignette, flicker, lightning
# ---------------------------------------------------------------------------------------------
def _noise_tex(w, h, scale, seed, blur):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8), "L").resize((w, h), Image.BICUBIC)
    return img.filter(ImageFilter.GaussianBlur(blur))


class Atmos:
    def __init__(self, tint=(200, 205, 215), fog=0.30, vignette=0.85, grain=16, seed=1):
        self.fogs = []
        win = np.clip(np.sin(np.linspace(0, np.pi, 900, dtype=np.float32)), 0, 1)[:, None] ** 1.6   # soft top and bottom edges
        for i, (sc, a) in enumerate(((180, fog), (110, fog * 0.7))):
            n = np.asarray(_noise_tex(W * 2, 900, sc, seed + i, 70), np.float32) / 255.0
            n = np.clip((n - 0.30) * 1.6, 0, 1) * win * a * 255
            layer = Image.new("RGBA", (W * 2, 900), tint + (0,))
            layer.putalpha(Image.fromarray(n.astype(np.uint8), "L"))
            self.fogs.append(layer)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.6)) ** 2)
        v = np.clip((d - 0.55) / 0.6, 0, 1) ** 1.6 * 255 * vignette
        self.vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.vig.putalpha(Image.fromarray(v.astype(np.uint8), "L"))
        rng = np.random.default_rng(seed + 9)
        self.grain = []
        for _ in range(6):
            g = rng.normal(128, 40, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)
            gi = Image.fromarray(g, "L").resize((W, H), Image.NEAREST)
            layer = Image.merge("RGBA", (gi, gi, gi, Image.new("L", (W, H), grain)))
            self.grain.append(layer)
        self.dark = [Image.new("RGBA", (W, H), (0, 0, 0, a)) for a in range(0, 60, 6)]
        self.flash = [Image.new("RGBA", (W, H), (210, 222, 255, a)) for a in range(0, 140, 14)]

    def fog(self, frame, t, y0=1050, y1=330, speed=(22, -14)):
        for i, (layer, y) in enumerate(zip(self.fogs, (y0, y1))):
            x = int((t * speed[i]) % W)
            frame.alpha_composite(layer.crop((x, 0, x + W, layer.height)), (0, y))

    def finish(self, frame, t, flicker=0.0, flash=0.0):
        frame.alpha_composite(self.vig)
        if flicker > 0:
            k = 0.5 + 0.5 * math.sin(t * 23.0) * math.sin(t * 7.3 + 1.1)
            frame.alpha_composite(self.dark[min(len(self.dark) - 1, int(k * flicker * (len(self.dark) - 1)))])
        if flash > 0.02:
            frame.alpha_composite(self.flash[min(len(self.flash) - 1, int(flash * (len(self.flash) - 1)))])
        frame.alpha_composite(self.grain[int(t * FPS) % len(self.grain)])


def lightning(u, at, length=0.32):
    """Flash brightness: two quick strikes and a short fade (a moment, not a whiteout)."""
    x = u - at
    if x < 0 or x > length:
        return 0.0
    return min(1.0, max(0.0, 1 - x / 0.06) * 0.8 + 0.6 * max(0.0, 1 - abs(x - 0.13) / 0.05) + 0.12 * max(0.0, 1 - x / length))


# ---------------------------------------------------------------------------------------------
# Drawings
# ---------------------------------------------------------------------------------------------
def aged_paper(w, h, seed=3, color=SEPIA):
    rng = np.random.default_rng(seed)
    base = np.ones((h, w, 3), np.float32) * np.array(color, np.float32)
    blot = np.asarray(_noise_tex(w, h, 30, seed, 12), np.float32)[..., None] / 255.0
    base *= 0.86 + 0.18 * blot
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]) / 60.0
    base *= (0.55 + 0.45 * np.clip(edge, 0, 1) ** 0.6)[..., None]
    base += rng.normal(0, 4, (h, w, 1)).astype(np.float32)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # ragged edge
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    pts = []
    for i in range(0, w, 14):
        pts.append((i, rng.uniform(0, 7)))
    for i in range(0, h, 14):
        pts.append((w - rng.uniform(0, 7), i))
    for i in range(w, 0, -14):
        pts.append((i, h - rng.uniform(0, 7)))
    for i in range(h, 0, -14):
        pts.append((rng.uniform(0, 7), i))
    md.polygon(pts, fill=255)
    img.putalpha(mask)
    return img


def newsprint(d, x0, y0, x1, y1, rng, size=13, gap=8):
    """Rows of tiny "words": print too small to read, like a newspaper seen from across the room."""
    y = y0
    while y + size <= y1:
        x = x0
        while x < x1 - 20:
            wlen = rng.integers(18, 70)
            if x + wlen > x1:
                break
            d.rectangle((x, y + 3, x + wlen, y + size - 2), fill=(60, 46, 32, int(rng.integers(150, 215))))
            x += wlen + rng.integers(7, 12)
        y += size + gap


def newspaper_page():
    w, h = 900, 1040
    img = aged_paper(w, h, seed=5)
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(12)
    d.line((40, 120, w - 40, 120), fill=INKC + (220,), width=3)
    d.line((40, 128, w - 40, 128), fill=INKC + (220,), width=1)
    head = T("PERSONAL", "bask", 96, INKC + (255,), tracking=6)
    img.alpha_composite(head, ((w - head.width) // 2, 22))
    col = (w - 120) // 2
    ads = []
    for c in range(2):
        x0 = 50 + c * (col + 20)
        y = 150
        while y < h - 90:
            bh = int(rng.integers(120, 210))
            bh = min(bh, h - 70 - y)
            d.rectangle((x0, y, x0 + col, y + 26), fill=(52, 38, 26, 230))   # the ad's first line, in bold
            newsprint(d, x0, y + 36, x0 + col, y + bh - 14, rng)
            ads.append((x0, y, x0 + col, y + bh))
            y += bh + 14
            d.line((x0 + 30, y - 7, x0 + col - 30, y - 7), fill=INKC + (120,), width=1)
    return img, ads


def red_circle(size, progress):
    """A hand-drawn red ink circle, drawn up to `progress` (0-1)."""
    w, h = size
    img = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    if progress <= 0:
        return img
    d = ImageDraw.Draw(img)
    pts = []
    n = int(140 * min(1, progress))
    for i in range(n):
        a = 2 * math.pi * (i / 120) - 2.2
        wob = 1 + 0.04 * math.sin(i * 0.37) + 0.025 * math.sin(i * 1.3)
        r = 1.0 + 0.06 * (i / 140)
        pts.append((20 + w / 2 + (w / 2) * math.cos(a) * wob * r, 20 + h / 2 + (h / 2) * math.sin(a) * wob * r))
    if len(pts) > 1:
        d.line(pts, fill=BLOOD + (235,), width=9, joint="curve")
    return img


def lady(w=600, h=780, col=(16, 12, 10, 255)):
    """An Edwardian woman's silhouette in profile, with a wide plumed hat (drawn, 3x then scaled)."""
    S = 3
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    P = lambda pts: [(x * S, y * S) for x, y in pts]
    E = lambda cx, cy, rx, ry: d.ellipse(((cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S), fill=col)
    # shoulders, puffed sleeves and a high collar
    d.polygon(P([(90, 780), (120, 655), (190, 605), (262, 585), (338, 585), (410, 605), (480, 655), (510, 780)]), fill=col)
    E(160, 650, 78, 66)
    E(440, 650, 78, 66)
    d.polygon(P([(262, 470), (338, 470), (350, 600), (250, 600)]), fill=col)
    # head and face, facing left
    E(305, 395, 86, 104)
    d.polygon(P([(232, 318), (214, 352), (206, 378), (182, 404), (200, 416), (196, 428), (203, 438), (198, 449),
                 (207, 462), (214, 478), (238, 500), (290, 505), (300, 330)]), fill=col)
    E(378, 380, 56, 52)          # hair, put up
    # the hat: brim, crown, ribbon and a long plume
    brim = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(brim)
    bd.ellipse((60 * S, 262 * S, 540 * S, 352 * S), fill=col)
    brim = brim.rotate(7, center=(300 * S, 307 * S), resample=Image.BICUBIC)
    img.alpha_composite(brim)
    E(318, 262, 124, 74)
    plume = [(380, 230), (420, 170), (470, 120), (530, 92), (575, 98), (548, 122), (505, 150), (470, 190), (440, 232), (410, 262)]
    d.polygon(P(plume), fill=col)
    for i in range(9):
        x = 420 + i * 16
        y = 170 - i * 8
        d.line(P([(x, y), (x + 24, y - 30)]), fill=col, width=4 * S)
    return img.resize((w, h), Image.LANCZOS)


def cameo(w=640, h=820):
    """An oval portrait frame with the silhouette inside."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    inner = aged_paper(w - 70, h - 70, seed=21, color=(214, 188, 140))
    yy, xx = np.mgrid[0:inner.height, 0:inner.width].astype(np.float32)
    k = np.sqrt(((xx - inner.width / 2) / (inner.width / 2)) ** 2 + ((yy - inner.height / 2) / (inner.height / 2)) ** 2)
    shade = (1 - 0.55 * np.clip(k, 0, 1) ** 2)[..., None]
    arr = np.asarray(inner, np.float32)
    arr[..., :3] *= shade
    inner = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    sil = lady(inner.width - 60, inner.height - 30)
    inner.alpha_composite(sil, (40, 40))
    mask = Image.new("L", inner.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, inner.width - 1, inner.height - 1), fill=255)
    inner.putalpha(mask)
    d = ImageDraw.Draw(img)
    for i, c in enumerate(((60, 42, 16), (196, 152, 70), (240, 206, 120), (150, 108, 40), (92, 64, 22))):
        r = 6 * i
        d.ellipse((r, r, w - 1 - r, h - 1 - r), outline=c + (255,), width=8)
    for k2 in range(36):
        a = 2 * math.pi * k2 / 36
        bx, by = w / 2 + (w / 2 - 16) * math.cos(a), h / 2 + (h / 2 - 16) * math.sin(a)
        d.ellipse((bx - 6, by - 6, bx + 6, by + 6), fill=(236, 200, 110, 255))
    img.alpha_composite(inner, (35, 35))
    return img


def bare_tree(h, seed, col=(6, 6, 9, 255)):
    rng = np.random.default_rng(seed)
    w = int(h * 0.9)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def branch(x, y, ang, length, width, depth):
        if depth == 0 or length < 8:
            return
        x2, y2 = x + length * math.cos(ang), y - length * math.sin(ang)
        d.line((x, y, x2, y2), fill=col, width=max(1, int(width)))
        for _ in range(2 + (depth > 3)):
            branch(x2, y2, ang + rng.uniform(-0.75, 0.75), length * rng.uniform(0.58, 0.78), width * 0.66, depth - 1)

    branch(w / 2, h, math.pi / 2 + rng.uniform(-0.08, 0.08), h * 0.32, h * 0.045, 7)
    return img


def farmhouse(w=760, h=520, col=(8, 8, 11, 255)):
    """A two-story farmhouse silhouette; returns the image and its window boxes."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((140, 220, 520, h), fill=col)                      # main house
    d.polygon([(110, 230), (330, 70), (550, 230)], fill=col)       # gable roof
    d.rectangle((420, 90, 456, 190), fill=col)                     # chimney
    d.rectangle((520, 320, 700, h), fill=col)                      # wing
    d.polygon([(505, 330), (610, 250), (715, 330)], fill=col)
    d.rectangle((90, 400, 520, 418), fill=col)                     # porch roof
    for x in (100, 210, 320, 430):
        d.rectangle((x, 418, x + 10, h), fill=col)
    wins = [(190, 260, 240, 330), (300, 260, 350, 330), (410, 260, 460, 330), (300, 140, 350, 200), (570, 380, 620, 440)]
    return img, wins


_flame = {}


def flame_sprite(r):
    if r not in _flame:
        s = int(r * 2.6)
        yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
        cx, cy = s / 2, s * 0.58
        dist = np.sqrt(((xx - cx) / (r * 0.75)) ** 2 + ((yy - cy) / (r * 1.25)) ** 2)
        a = np.clip(1 - dist, 0, 1) ** 1.3
        core = np.clip(1 - dist * 1.8, 0, 1)
        rgb = np.stack([np.full_like(a, 255), 110 + 140 * core, 20 + 120 * core ** 2], -1)
        arr = np.dstack([rgb, a * 235]).astype(np.uint8)
        _flame[r] = Image.fromarray(arr, "RGBA").filter(ImageFilter.GaussianBlur(r * 0.08))
    return _flame[r]


_soft = {}


def soft_dot(r, color, alpha=255):
    key = (r, color, alpha)
    if key not in _soft:
        s = int(r * 4)
        img = Image.new("RGBA", (s, s), color + (0,))
        m = Image.new("L", (s, s), 0)
        ImageDraw.Draw(m).ellipse((r, r, 3 * r, 3 * r), fill=alpha)
        img.putalpha(m.filter(ImageFilter.GaussianBlur(r * 0.6)))
        _soft[key] = img
    return _soft[key]


def fire(frame, ox, oy, wins, u, start, strength=1.0):
    """Flames on the house (ox, oy is the house image's top-left), growing from `start` (scene seconds)."""
    if u < start:
        return 0.0
    k = min(1.0, (u - start) / 1.4) * strength
    rng = np.random.default_rng(int(u * FPS))
    # the windows glow first
    for (x0, y0, x1, y1) in wins:
        g = soft_dot(46, (255, 140, 30), 200)
        frame.alpha_composite(vr.with_alpha(g, min(1, 0.4 + k)), (int(ox + (x0 + x1) / 2 - g.width / 2), int(oy + (y0 + y1) / 2 - g.height / 2)))
    # flames along the roof and out of the windows
    seeds = [(140 + i * 26, 220) for i in range(15)] + [(110 + i * 30, 230 - (i * 160 / 7 if i <= 7 else (14 - i) * 160 / 7)) for i in range(15)]
    seeds += [((x0 + x1) / 2, y0) for (x0, y0, x1, y1) in wins]
    n = int(70 * k)
    for _ in range(n):
        sx, sy = seeds[rng.integers(0, len(seeds))]
        life = rng.random()
        r = int(18 + 38 * rng.random() * (1 - life) * (0.5 + k))
        if r < 6:
            continue
        x = ox + sx + rng.normal(0, 14) + math.sin(u * 6 + sx) * 6
        y = oy + sy - life * (160 + 140 * k) - r
        spr = flame_sprite(min(64, r))
        frame.alpha_composite(vr.with_alpha(spr, 0.85 * (1 - life) ** 0.6), (int(x - spr.width / 2), int(y - spr.height / 2)))
    # embers
    for i in range(int(40 * k)):
        ph = (u * (0.6 + (i % 7) * 0.08) + i * 0.137) % 1.0
        x = ox + 120 + (i * 97) % 520 + 30 * math.sin(u * 2 + i)
        y = oy + 200 - ph * 640
        frame.alpha_composite(soft_dot(4, (255, 190, 80), int(255 * (1 - ph))), (int(x), int(y)))
    return k


def lantern(frame, x, y, u, i):
    sway = math.sin(u * 1.6 + i * 1.7) * 10
    glow = soft_dot(70, (255, 200, 110), 120)
    frame.alpha_composite(glow, (int(x + sway - glow.width / 2), int(y - glow.height / 2)))
    core = soft_dot(14, (255, 236, 180), 255)
    frame.alpha_composite(core, (int(x + sway - core.width / 2), int(y - core.height / 2)))


def stamp(text_lines, color=BLOOD):
    lines = [T(t, "lora", s, color + (255,), tracking=4) for t, s in text_lines]
    w = max(l.width for l in lines) + 80
    h = sum(l.height for l in lines) + 30 * (len(lines) - 1) + 70
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, w - 5, h - 5), radius=16, outline=color + (255,), width=10)
    y = 35
    for l in lines:
        img.alpha_composite(l, ((w - l.width) // 2, y))
        y += l.height + 30
    # worn ink
    rng = np.random.default_rng(4)
    a = np.asarray(img.getchannel("A"), np.float32)
    holes = (np.asarray(_noise_tex(w, h, 6, 4, 1.5), np.float32) / 255.0) > 0.62
    a[holes] *= 0.35
    img.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
    return img.rotate(-9, expand=True, resample=Image.BICUBIC)


def locomotive(w=640, col=(5, 5, 8, 255)):
    h = int(w * 0.5)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((90, 110, 470, 230), radius=50, fill=col)        # boiler
    d.rectangle((420, 50, 600, 240), fill=col)                          # cab
    d.rectangle((400, 36, 620, 58), fill=col)                           # cab roof
    d.polygon([(120, 110), (110, 30), (170, 30), (160, 110)], fill=col)  # smokestack
    d.rectangle((96, 18, 184, 34), fill=col)
    d.ellipse((230, 76, 290, 120), fill=col)                            # dome
    d.polygon([(40, 250), (90, 200), (90, 262)], fill=col)              # cowcatcher
    d.rectangle((70, 228, 610, 252), fill=col)
    for cx, r in ((170, 44), (290, 44), (410, 44), (540, 30)):
        d.ellipse((cx - r, 262 - r, cx + r, 262 + r), fill=col)
    d.line((170, 262, 410, 262), fill=(30, 30, 36, 255), width=8)
    d.rectangle((470, 80, 540, 140), fill=(255, 196, 90, 230))          # cab window, lit
    return img, (92, 150)                                               # headlight spot


# ---------------------------------------------------------------------------------------------
# Captions that follow the voice, a few words at a time
# ---------------------------------------------------------------------------------------------
def chunks(words, max_chars=16):
    out, cur = [], []
    for wd in words:
        text = wd[0]
        if not text.strip():
            continue
        if text in ",.:;!?" and cur:
            cur[-1] = [cur[-1][0] + text, cur[-1][1], wd[2]]
            continue
        cand = " ".join(w[0] for w in cur + [wd])
        if cur and (len(cand) > max_chars or cur[-1][0][-1:] in ".?!:"):
            out.append(cur)
            cur = []
        cur.append(list(wd))
    if cur:
        out.append(cur)
    return out


def caption(frame, words, t, y=1340, size=84, hi=(255, 214, 72)):
    groups = chunks(words)
    cur = None
    for g in groups:
        if g[0][1] - 0.05 <= t:
            cur = g
    if cur is None or t > cur[-1][2] + 0.6:
        return
    f = F("black", size)
    parts = []
    for wd in cur:
        active = wd[1] - 0.02 <= t < (wd[2] + 0.02)
        done = t >= wd[1]
        col = hi if active else ((255, 255, 255) if done else (255, 255, 255))
        img = T(wd[0], "black", size, col + (255,), stroke=8, stroke_fill=(0, 0, 0))
        if active:
            img = img.resize((int(img.width * 1.08), int(img.height * 1.08)), Image.BICUBIC)
        parts.append(img)
    space = int(f.getlength(" "))
    total = sum(p.width for p in parts) + space * (len(parts) - 1)
    if total > CW + 40:
        scale = (CW + 40) / total
        parts = [p.resize((max(1, int(p.width * scale)), max(1, int(p.height * scale))), Image.BICUBIC) for p in parts]
        space = int(space * scale)
        total = sum(p.width for p in parts) + space * (len(parts) - 1)
    x = (W - total) // 2
    pop = min(1.0, (t - cur[0][1] + 0.05) / 0.12)
    for p in parts:
        frame.alpha_composite(vr.with_alpha(p, max(0.2, pop)), (x, int(y - p.height / 2)))
        x += p.width + space


# ---------------------------------------------------------------------------------------------
# The voice
# ---------------------------------------------------------------------------------------------
VOICE = json.load(open(os.path.join(HERE, "voice", "voice.json"), encoding="utf-8"))
LINES = {l["id"]: l for l in VOICE["lines"]}


def voice_clip(lid):
    """The line's audio at 48 kHz with the leading and trailing silence trimmed, and its word times."""
    with wave.open(os.path.join(HERE, "voice", lid + ".wav")) as w:
        rate = w.getframerate()
        raw = w.readframes(w.getnframes())
        width = w.getsampwidth()
    a = (np.frombuffer(raw, "<i2").astype(np.float32) / 32768) if width == 2 else np.frombuffer(raw, "<f4")
    words = LINES[lid]["words"]
    start = max(0.0, words[0][1] - 0.06) if words else 0.0
    end = min(len(a) / rate, (words[-1][2] + 0.18) if words else len(a) / rate)
    a = a[int(start * rate):int(end * rate)]
    n = int(len(a) * SR / rate)
    a48 = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)
    return a48, [[wd[0], wd[1] - start, wd[2] - start] for wd in words]


def word_at(words, word, default=0.0):
    for wd in words:
        if wd[0].lower().strip(",.?!:") == word.lower():
            return wd[1]
    return default


# ---------------------------------------------------------------------------------------------
# Backgrounds
# ---------------------------------------------------------------------------------------------
def gradient(top, bottom):
    k = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    arr = np.array(top, np.float32) * (1 - k) + np.array(bottom, np.float32) * k
    arr = np.repeat(arr, W, axis=1)
    arr += np.random.default_rng(2).normal(0, 1.6, (H, W, 1)).astype(np.float32)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    return img


def noir_base():
    img = gradient((20, 22, 30), (5, 5, 8))
    m = soft_dot(70, (230, 225, 210), 130)                 # a moon behind haze
    img.alpha_composite(m, (120, 300))
    img.alpha_composite(vr.brand_row(), (0, 175))
    return img


def woods_base():
    img = gradient((14, 26, 32), (3, 6, 8))
    glow = soft_dot(160, (190, 220, 230), 70)
    img.alpha_composite(glow, (W - 560, 120))
    moon = Image.new("RGBA", (190, 190), (0, 0, 0, 0))
    ImageDraw.Draw(moon).ellipse((0, 0, 189, 189), fill=(236, 240, 228, 255))
    img.alpha_composite(moon, (W - 335, 255))
    img.alpha_composite(vr.brand_row(), (0, 175))
    return img


def tree_strip(height, seed, count, col):
    strip = Image.new("RGBA", (W * 2, height), (0, 0, 0, 0))
    rng = np.random.default_rng(seed)
    for i in range(count):
        th = int(height * rng.uniform(0.7, 1.0))
        tr = bare_tree(th, seed * 10 + i, col)
        x = int(i * (W * 2) / count + rng.uniform(-60, 60))
        strip.alpha_composite(tr, (x % (W * 2 - tr.width), height - th))
    return strip


# ---------------------------------------------------------------------------------------------
# Scenes. Each is drawn at u seconds into the scene; `words` are the narrator's word times in scene time.
# ---------------------------------------------------------------------------------------------
class Scene:
    def __init__(self, line, draw, prep=None, sfx=None, lead=0.08, gap=0.16, flash_at=None):
        self.line, self.draw, self.prep, self.sfx = line, draw, prep, sfx or []
        self.lead, self.gap, self.flash_at = lead, gap, flash_at
        self.ctx = {}


def title(frame, text, kind, size, color, y, glow=None, alpha=1.0, jitter=0.0, max_w=CW):
    img = fitT(text, kind, size, color + (255,), max_w=max_w, min_size=int(size * 0.5))
    if glow:
        img, pad = glowT(img, glow, radius=26, strength=0.75)
    dx = int(np.random.default_rng(int(jitter * 1000)).normal(0, 6)) if jitter else 0
    paste_c(frame, img, W / 2 + dx, y, alpha)


# --- Belle Gunness, part 1
def prep_paper(ctx):
    ctx["paper"], ads = newspaper_page()
    ctx["ad"] = ads[1]


def draw_a1(frame, u, words, ctx):
    paper = ctx["paper"].copy()
    x0, y0, x1, y1 = ctx["ad"]
    ring = red_circle((x1 - x0 + 40, y1 - y0 + 40), (u - 0.7) / 1.0)
    paper.alpha_composite(ring, (x0 - 40, y0 - 40))
    z = 0.70 + 0.08 * min(1.0, u / 5.5)
    img = paper.resize((int(paper.width * z), int(paper.height * z)), Image.BICUBIC).rotate(-2 + 1.2 * min(1, u / 5), expand=True, resample=Image.BICUBIC)
    paste_c(frame, img, W / 2 + 24 * min(1, u / 5), 745)
    never = word_at(words, "never", 3.0)
    label = T("LA PORTE, INDIANA", "bold", 34, BONE + (255,), tracking=4)
    paste_c(frame, label, W / 2, 284)
    if u < never:
        title(frame, "THEY ANSWERED HER ADS", "bask", 84, BONE, 1222, glow=(0, 0, 0), alpha=appear(u, 0.0, 0.12))
    else:
        title(frame, "NEVER SEEN AGAIN", "bask", 104, (240, 60, 50), 1222, glow=(120, 0, 0), jitter=u if u - never < 0.25 else 0)


def prep_cameo(ctx):
    ctx["cameo"] = cameo()


def draw_a2(frame, u, words, ctx):
    z = 1.0 + 0.05 * min(1, u / 2.4)
    c = ctx["cameo"]
    paste_c(frame, c.resize((int(c.width * z * 0.92), int(c.height * z * 0.92)), Image.BICUBIC), W / 2, 720)
    at = word_at(words, "Belle", 0.8)
    if u >= at - 0.1:
        title(frame, "BELLE GUNNESS", "bask", 132, BONE, 1185, glow=(150, 10, 10), jitter=u if u - at < 0.2 else 0)


def prep_farm(ctx):
    ctx["house"], ctx["wins"] = farmhouse()
    ctx["trees"] = [bare_tree(620, 7), bare_tree(520, 9), bare_tree(560, 13)]
    hill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(hill)
    pts = [(x, 110 - 40 * math.sin(x / W * math.pi) + 8 * math.sin(x / 37)) for x in range(0, W + 1, 10)]
    d.polygon(pts + [(W, H), (0, H)], fill=(6, 6, 9, 255))
    ctx["hill"] = hill


def draw_house_scene(frame, u, ctx, fire_at=None, strength=1.0, smolder=False):
    ox, oy = (W - ctx["house"].width) // 2 + 20, 600
    k = 0.0
    if fire_at is not None:
        kk = min(1.0, max(0.0, (u - fire_at) / 1.4)) * strength
        if kk > 0:
            g = soft_dot(300, (255, 110, 20), int(150 * kk))
            frame.alpha_composite(g, (W // 2 - g.width // 2, 640 - g.height // 2))
    frame.alpha_composite(ctx["trees"][0], (-160, 520))
    frame.alpha_composite(ctx["trees"][1], (W - 360, 600))
    frame.alpha_composite(ctx["hill"], (0, 1040))
    frame.alpha_composite(ctx["house"], (ox, oy))
    if fire_at is not None:
        k = fire(frame, ox, oy, ctx["wins"], u, fire_at, strength)
    if smolder:
        for i in range(26):
            ph = (u * 0.25 + i * 0.173) % 1.0
            x = ox + 150 + (i * 53) % 420 + 40 * math.sin(u * 0.7 + i)
            y = oy + 140 - ph * 500
            frame.alpha_composite(soft_dot(46 + int(60 * ph), (40, 38, 40), int(120 * (1 - ph))), (int(x - 60), int(y - 60)))
        for i in range(18):
            ph = (u * 0.5 + i * 0.211) % 1.0
            frame.alpha_composite(soft_dot(3, (255, 150, 60), int(230 * (1 - ph))), (int(ox + 160 + (i * 71) % 400), int(oy + 220 - ph * 260)))
    return k


def draw_a3(frame, u, words, ctx):
    burned = word_at(words, "burned", 2.0)
    draw_house_scene(frame, u, ctx, fire_at=burned - 0.3)
    april = word_at(words, "April", 0.3)
    text = "APRIL 28, 1908"
    n = int(max(0, min(len(text), (u - april) / 0.06)))
    if n:
        typed = T(text[:n], "mono", 84, BONE + (255,))
        frame.alpha_composite(typed, ((W - T(text, "mono", 84, BONE + (255,)).width) // 2, 330))


def draw_a4(frame, u, words, ctx):
    draw_house_scene(frame, u, ctx, smolder=True)
    title(frame, "WHAT THEY DUG UP NEXT", "bask", 84, BONE, 360, glow=(0, 0, 0), alpha=appear(u, 0.0, 0.15))
    at = word_at(words, "part", 1.4)
    if u >= at - 0.15:
        img = T("PART 2", "bask", 230, (230, 40, 34, 255))
        g, pad = glowT(img, (140, 0, 0), radius=34, strength=0.9)
        j = 1 if u - at < 0.3 else 0
        if j:   # a glitch: the red splits for a moment
            rng = np.random.default_rng(int(u * 1000))
            for dx in (-12, 12):
                frame.alpha_composite(vr.with_alpha(g, 0.35), (int(W / 2 - g.width / 2 + dx + rng.normal(0, 4)), int(1150 - g.height / 2)))
        paste_c(frame, g, W / 2, 1150)


# --- Belle Gunness, part 2
def draw_b1(frame, u, words, ctx):
    c = ctx["cameo"]
    z = 0.94 + 0.05 * min(1, u / 3)
    paste_c(frame, c.resize((int(c.width * z), int(c.height * z)), Image.BICUBIC), W / 2, 720)
    at = word_at(words, "really", 1.2)
    if u >= at - 0.1:
        q = T("?", "bask", 560, (220, 34, 30, 255))
        g, pad = glowT(q, (120, 0, 0), radius=40, strength=0.9)
        s = 1.25 - 0.25 * appear(u, at - 0.1, 0.18)
        g2 = g.resize((int(g.width * s), int(g.height * s)), Image.BICUBIC)
        paste_c(frame, g2, W / 2 + 40, 700, appear(u, at - 0.1, 0.18))
    title(frame, "WAS IT REALLY BELLE?", "bask", 96, BONE, 1190, glow=(0, 0, 0))


def prep_field(ctx):
    prep_farm(ctx)
    m = Image.new("RGBA", (W, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(m)
    for i, (x, w2) in enumerate(((60, 220), (300, 260), (590, 230), (820, 240))):
        d.ellipse((x, 120 + 18 * (i % 2), x + w2, 260 + 18 * (i % 2)), fill=(18, 13, 10, 255))
    for x in (250, 560, 860):   # shovels
        d.line((x, 40, x + 18, 170), fill=(10, 10, 12, 255), width=9)
        d.polygon([(x + 6, 160), (x + 40, 160), (x + 36, 214), (x + 12, 214)], fill=(10, 10, 12, 255))
    ctx["mounds"] = m


def draw_b2(frame, u, words, ctx):
    frame.alpha_composite(ctx["trees"][2], (W - 420, 560))
    frame.alpha_composite(ctx["hill"], (0, 960))
    frame.alpha_composite(ctx["mounds"], (0, 920))
    for i, (x, y) in enumerate(((180, 1010), (430, 960), (690, 1030), (900, 980), (560, 1120))):
        lantern(frame, x, y, u, i)
    found = word_at(words, "found", 1.8)
    eleven = word_at(words, "eleven", found + 1.0)
    if u >= found - 0.1:
        n = int(min(11, max(1, 11 * (u - found + 0.1) / max(0.3, eleven - found + 0.2))))
        num = T(f"{n}+" if n >= 11 else str(n), "black", 300, BONE + (255,))
        g, pad = glowT(num, (150, 10, 10), radius=36, strength=0.85)
        paste_c(frame, g, W / 2, 560)
        lab = T("REMAINS FOUND ON HER FARM", "bold", 44, BONE + (255,), tracking=3)
        paste_c(frame, lab, W / 2, 760, appear(u, found, 0.3))
    else:
        title(frame, "THEY DUG UP THE FARM", "bask", 92, BONE, 560, glow=(0, 0, 0))


def prep_poster(ctx):
    prep_cameo(ctx)
    p = aged_paper(780, 1000, seed=33)
    head = fitT("HAVE YOU SEEN HER?", "bask", 84, INKC + (255,), max_w=700)
    p.alpha_composite(head, ((p.width - head.width) // 2, 50))
    d = ImageDraw.Draw(p)
    d.line((60, 160, 720, 160), fill=INKC + (200,), width=3)
    c = ctx["cameo"].resize((470, 602), Image.LANCZOS)
    p.alpha_composite(c, ((p.width - c.width) // 2, 200))
    rng = np.random.default_rng(8)
    newsprint(d, 80, 830, 700, 960, rng, size=12, gap=9)
    ctx["poster"] = p
    ctx["stamp"] = stamp([("DNA TEST", 84), ("NO ANSWER", 92)])


def draw_b3(frame, u, words, ctx):
    dna = word_at(words, "DNA", 3.2)
    shake = (np.random.default_rng(int(u * 1000)).normal(0, 9, 2) if 0 <= u - dna < 0.22 else (0, 0))
    p = ctx["poster"]
    z = 0.92 + 0.04 * min(1, u / 6)
    paste_c(frame, p.resize((int(p.width * z), int(p.height * z)), Image.BICUBIC), W / 2 + shake[0], 740 + shake[1])
    if u >= dna:
        s = 1.0 + 1.2 * (1 - appear(u, dna, 0.12))
        st = ctx["stamp"]
        st2 = st.resize((int(st.width * s), int(st.height * s)), Image.BICUBIC)
        paste_c(frame, st2, W / 2 + shake[0], 1010 + shake[1], min(1, appear(u, dna, 0.08) * 1.2))
    else:
        title(frame, "SEEN ALIVE FOR YEARS?", "bask", 84, BONE, 1250, glow=(0, 0, 0), alpha=appear(u, 0.2, 0.2))


def prep_museum(ctx):
    c = aged_paper(860, 760, seed=44)
    y = 60
    for text, kind, size, col, gap in (("SEE HER STORY", "bask", 104, INKC, 26), ("Belle Gunness exhibit", "lora", 54, BLOOD, 34),
                                       ("La Porte County", "lora", 60, INKC, 8), ("Historical Society Museum", "lora", 60, INKC, 36),
                                       ("2405 Indiana Ave., La Porte", "semi", 44, INKC, 14), ("Tue.-Sat., 10 a.m. to 4:30 p.m.", "semi", 42, INKC, 0)):
        img = fitT(text, kind, size, col + (255,), max_w=760)
        c.alpha_composite(img, ((c.width - img.width) // 2, y))
        y += img.height + gap
        if text == "Belle Gunness exhibit":
            ImageDraw.Draw(c).line((120, y - 16, 740, y - 16), fill=INKC + (160,), width=2)
    ctx["card"] = c


def draw_b4(frame, u, words, ctx):
    for i, (x, y) in enumerate(((150, 1180), (930, 1120))):
        lantern(frame, x, y, u, i)
    c = ctx["card"]
    z = 0.95 + 0.04 * min(1, u / 4)
    paste_c(frame, c.resize((int(c.width * z), int(c.height * z)), Image.BICUBIC), W / 2, 760, appear(u, 0.0, 0.18))


# --- Trick-or-treat hours (Halloween night)
TOWNS_5_7 = ["La Porte", "Michigan City", "Westville", "Wanatah", "Kingsford Heights", "Long Beach", "Trail Creek",
             "Rolling Prairie", "Union Mills"]


def draw_c1(frame, u, words, ctx):
    a, pad = glowT(fitT("TRICK-OR-TREAT", "black", 150, ORANGE + (255,)), (255, 110, 0), 30, 0.7)
    paste_c(frame, a, W / 2, 560)
    paste_c(frame, fitT("HOURS", "black", 250, CREAM + (255,)), W / 2, 760)
    paste_c(frame, fitT("every La Porte County town", "xbold", 62, LAV + (255,)), W / 2, 930)
    at = word_at(words, "Save", 2.4)
    if u >= at - 0.1:
        pill = vr.pill("SAVE THIS", "black", 58, (16, 8, 26), GOLDEN + (255,), padx=46, pady=24)
        s = 1.15 - 0.15 * appear(u, at - 0.1, 0.16)
        paste_c(frame, pill.resize((int(pill.width * s), int(pill.height * s)), Image.BICUBIC), W / 2, 1090)


def draw_c2(frame, u, words, ctx):
    ban = vr.pill("SAT · OCT. 31 · 5 TO 7 PM", "black", 58, (16, 8, 26), GOLDEN + (255,), padx=40, pady=24)
    paste_c(frame, ban, W / 2, 420, appear(u, 0.0, 0.15))
    pk = hw.pumpkin(54, glow_face=True)
    for i, town in enumerate(TOWNS_5_7):
        col, row = (i % 2, i // 2)
        a = appear(u, 0.25 + 0.16 * i, 0.2)
        if a <= 0:
            continue
        x = 110 + col * 470
        y = 560 + row * 112
        t = fitT(town, "xbold", 52, CREAM + (255,), max_w=380)
        frame.alpha_composite(vr.with_alpha(pk, a), (x, int(y - pk.height / 2)))
        frame.alpha_composite(vr.with_alpha(t, a), (x + 70, int(y - t.height / 2 + 4 * (1 - a))))


def draw_c3(frame, u, words, ctx):
    lc = word_at(words, "LaCrosse", 0.2)
    pp = word_at(words, "Pottawattamie", 2.6)
    for i, ((name, line), at) in enumerate(((("LaCrosse", "Sat., Oct. 31 · 5 to 7:30 PM"), lc), (("Pottawattamie Park", "Sun., Oct. 25 · 3 to 5 PM · early!"), pp))):
        a = appear(u, at - 0.1, 0.22)
        if a > 0:
            c = hw.card(name, line, ORANGE if i == 0 else (139, 63, 217), hw.pumpkin(110, glow_face=True))
            frame.alpha_composite(vr.with_alpha(c, a), (X0 - 10, int(470 + i * 220 + 30 * (1 - a))))
    note = fitT("Hanna & Michiana Shores: not announced yet", "semi", 40, LAV + (255,))
    paste_c(frame, note, W / 2, 960, appear(u, pp + 1.2, 0.3))
    url = vr.pill("laporteweathernow.com", "xbold", 50, (16, 8, 26), GOLDEN + (255,), padx=36, pady=20)
    paste_c(frame, url, W / 2, 1060, appear(u, pp + 1.4, 0.3))


# --- The Hesston Ghost Train (dark woods)
def prep_woods(ctx):
    ctx["strips"] = [tree_strip(900, 3, 7, (14, 22, 26, 255)), tree_strip(1000, 5, 6, (8, 12, 15, 255)), tree_strip(1150, 8, 4, (3, 4, 6, 255))]
    loco, ctx["lamp"] = locomotive()
    loco = loco.transpose(Image.FLIP_LEFT_RIGHT)        # facing right, the way it goes
    a = loco.getchannel("A")
    rim = Image.new("RGBA", loco.size, (150, 176, 196, 0))
    rim.putalpha(ImageChops_sub(a.filter(ImageFilter.MaxFilter(7)), a).point(lambda v: int(v * 0.8)))
    lit = Image.new("RGBA", (loco.width + 8, loco.height + 8), (0, 0, 0, 0))
    lit.alpha_composite(rim, (6, 0))
    lit.alpha_composite(loco, (4, 4))
    ctx["loco"] = lit
    g = hw.ghost(150).filter(ImageFilter.GaussianBlur(2.5))
    ctx["ghost"] = g
    band = np.clip(np.sin(np.linspace(0, np.pi, 420)), 0, 1)[:, None] ** 2 * 70
    mist = Image.new("RGBA", (W, 420), (170, 192, 204, 0))
    mist.putalpha(Image.fromarray(np.repeat(band, W, axis=1).astype(np.uint8), "L"))
    ctx["mist"] = mist


def draw_woods(frame, t, ctx, total):
    for strip, speed, y in zip(ctx["strips"], (14, 30, 60), (440, 400, 380)):
        x = int((t * speed) % W)
        frame.alpha_composite(strip.crop((x, 0, x + W, strip.height)), (0, y))
    for i, (gx, gy) in enumerate(((180, 760), (840, 690), (520, 610))):
        a = 0.12 + 0.30 * (0.5 + 0.5 * math.sin(t * 1.1 + i * 2.1))
        frame.alpha_composite(vr.with_alpha(ctx["ghost"], a), (gx - 75, int(gy + 16 * math.sin(t * 1.6 + i))))
    frame.alpha_composite(ctx["mist"], (0, 930))        # pale mist behind the train, so it stands out
    d = ImageDraw.Draw(frame)
    d.rectangle((0, 1236, W, 1250), fill=(4, 4, 6, 255))
    loco = ctx["loco"]
    w = loco.width
    xpos = lambda tt: -0.35 * w + (W - 0.85 * w + 0.35 * w) * max(0.0, min(1.0, tt / total))   # always in frame
    x = xpos(t)
    y = 1236 - loco.height + 10
    lx, ly = x + w - 52, y + ctx["lamp"][1]
    beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(beam).polygon([(lx, ly - 14), (lx + 640, ly - 160), (lx + 640, ly + 160), (lx, ly + 14)], fill=(255, 230, 150, 44))
    frame.alpha_composite(beam)
    # steam: puffs left behind where the stack was a moment ago, rising and spreading
    for i in range(10):
        age = ((t * 1.1 + i / 10.0) % 1.0) * 2.2
        ex = xpos(t - age) + w - 150
        r = int(26 + 64 * age)
        a = int(120 * max(0.0, 1 - age / 2.2))
        frame.alpha_composite(soft_dot(r, (214, 218, 222), a), (int(ex - 40 * age - 2 * r), int(y + 10 - 140 * age - 2 * r)))
    frame.alpha_composite(loco, (int(x), int(y)))
    frame.alpha_composite(soft_dot(22, (255, 236, 170), 255), (int(lx - 44), int(ly - 44)))


def draw_d1(frame, u, words, ctx):
    k = 0.75 + 0.25 * (0.5 + 0.5 * math.sin(u * 31) * math.sin(u * 13))
    img = fitT("LAST CHANCE", "black", 170, (int(235 * k), 40, 36, 255))
    g, pad = glowT(img, (160, 0, 0), 34, 0.9)
    paste_c(frame, g, W / 2, 440)
    paste_c(frame, fitT("HESSTON GHOST TRAIN", "bask", 96, BONE + (255,)), W / 2, 600, appear(u, 0.15, 0.2))


def draw_d2(frame, u, words, ctx):
    pill = vr.pill("SAT & SUN · NOON TO 5", "black", 56, (10, 10, 12), GOLDEN + (255,), padx=40, pady=24)
    paste_c(frame, pill, W / 2, 430, appear(u, 0.0, 0.15))
    last = word_at(words, "last", 3.5)
    paste_c(frame, fitT("LAST WEEKEND THIS YEAR", "bask", 76, BONE + (255,)), W / 2, 560, appear(u, last - 0.1, 0.2))
    paste_c(frame, fitT("Hesston Steam Museum, La Porte · adults $11, kids $7", "semi", 36, LAV + (255,)), W / 2, 650, appear(u, 0.6, 0.3))


SHORTS = {
    "belle-1": {"theme": "noir", "music": "lullaby", "scenes": [
        Scene("a1", draw_a1, prep_paper, sfx=[("whoosh", 0.0)], lead=0.0),
        Scene("a2", draw_a2, prep_cameo, sfx=[("thunder", 0.0)], flash_at=0.0),
        Scene("a3", draw_a3, prep_farm, sfx=[("type", "April"), ("fire", "burned")]),
        Scene("a4", draw_a4, prep_farm, sfx=[("heartbeat", 0.0), ("hit", "part")], gap=0.6)]},
    "belle-2": {"theme": "noir", "music": "lullaby", "scenes": [
        Scene("b1", draw_b1, prep_cameo, sfx=[("thunder", 0.0), ("hit", "really")], lead=0.0, flash_at=0.0),
        Scene("b2", draw_b2, prep_field, sfx=[("heartbeat", "found")]),
        Scene("b3", draw_b3, prep_poster, sfx=[("thud", "DNA")]),
        Scene("b4", draw_b4, prep_museum, sfx=[("whoosh", 0.0)], gap=0.7)]},
    "hours": {"theme": "halloween", "music": "organ", "scenes": [
        Scene("c1", draw_c1, sfx=[("whoosh", 0.0), ("pop", "Save")], lead=0.0),
        Scene("c2", draw_c2, sfx=[("whoosh", 0.0)]),
        Scene("c3", draw_c3, sfx=[("pop", "LaCrosse"), ("pop", "Pottawattamie")], gap=0.8)]},
    "ghost-train": {"theme": "woods", "music": "drone", "scenes": [
        Scene("d1", draw_d1, prep_woods, sfx=[("whistle", 0.05)], lead=0.0),
        Scene("d2", draw_d2, prep_woods, sfx=[("whistle", "last")], gap=0.6)]},
}


# ---------------------------------------------------------------------------------------------
# Sound, written here
# ---------------------------------------------------------------------------------------------
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, n):
    win = np.hanning(n)
    return np.convolve(x, win / win.sum(), mode="same").astype(np.float32)


def env_ar(n, a, r):
    e = np.ones(n, np.float32)
    a, r = max(1, int(a * SR)), max(1, int(r * SR))
    e[:min(a, n)] = np.linspace(0, 1, min(a, n))
    e[-min(r, n):] *= np.linspace(1, 0, min(r, n))
    return e


def sfx(kind, rng):
    if kind == "thunder":
        n = int(3.2 * SR)
        t = np.arange(n) / SR
        crack = rng.normal(0, 1, n).astype(np.float32)
        crack = (crack - lowpass(crack, 9)) * np.exp(-t / 0.05) * 0.9
        rumble = lowpass(rng.normal(0, 1, n).astype(np.float32), 600) * 9
        rumble *= np.exp(-t / 1.1) * (1 + 0.6 * np.sin(2 * np.pi * 0.9 * t) ** 2)
        return crack + rumble
    if kind == "fire":
        n = int(9 * SR)
        x = np.zeros(n, np.float32)
        for _ in range(int(9 * 30)):
            i = rng.integers(0, n - 400)
            x[i:i + 300] += rng.normal(0, 1, 300).astype(np.float32) * np.exp(-np.arange(300) / 40) * rng.uniform(0.2, 0.9)
        roar = lowpass(rng.normal(0, 1, n).astype(np.float32), 300) * 4
        return (x * 0.5 + roar * 0.6) * env_ar(n, 1.0, 1.0)
    if kind == "heartbeat":
        n = int(2.2 * SR)
        x = np.zeros(n, np.float32)
        for beat in (0.0, 0.85, 1.7):
            for off, f, amp in ((0.0, 58, 1.0), (0.24, 48, 0.7)):
                i = int((beat + off) * SR)
                m = int(0.16 * SR)
                if i + m >= n:
                    continue
                tt = np.arange(m) / SR
                x[i:i + m] += (np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.05) * amp).astype(np.float32)
        return x * 0.9
    if kind in ("thud", "hit"):
        n = int(1.0 * SR)
        tt = np.arange(n) / SR
        f = 70 * (1 + 1.5 * np.exp(-tt / 0.02))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / (0.18 if kind == "thud" else 0.3))
        noise = lowpass(rng.normal(0, 1, n).astype(np.float32), 30) * np.exp(-tt / 0.04) * 0.6
        return (x + noise).astype(np.float32) * (0.9 if kind == "thud" else 0.6)
    if kind == "type":
        n = int(1.2 * SR)
        x = np.zeros(n, np.float32)
        for k in range(14):
            i = int(k * 0.06 * SR)
            m = int(0.018 * SR)
            b = rng.normal(0, 1, m).astype(np.float32)
            x[i:i + m] += (b - lowpass(b, 5)) * np.exp(-np.arange(m) / 120) * 0.7
        return x
    if kind == "whoosh":
        n = int(0.6 * SR)
        x = lowpass(rng.normal(0, 1, n).astype(np.float32), 120) * 4
        return x * np.sin(np.pi * np.linspace(0, 1, n)) ** 2 * 0.5
    if kind == "pop":
        n = int(0.25 * SR)
        tt = np.arange(n) / SR
        return (np.sin(2 * np.pi * (500 + 700 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.05) * 0.35).astype(np.float32)
    if kind == "whistle":
        n = int(1.8 * SR)
        tt = np.arange(n) / SR
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * tt)
        x = np.zeros(n, np.float32)
        for f in (440, 554, 659):
            ph = 2 * np.pi * f * np.cumsum(vib) / SR
            x += (np.sin(ph) + 0.3 * np.sin(2 * ph)).astype(np.float32)
        breath = lowpass(rng.normal(0, 1, n).astype(np.float32), 20) * 0.6
        return (x / 3 + breath) * env_ar(n, 0.12, 0.6) * 0.32
    return np.zeros(1, np.float32)


def music_bed(kind, seconds, rng):
    n = int(seconds * SR)
    out = np.zeros(n, np.float32)
    t = np.arange(n) / SR

    def add(sig, start):
        i = int(start * SR)
        if i < n:
            j = min(n, i + len(sig))
            out[i:j] += sig[:j - i]

    if kind in ("lullaby", "drone"):
        # a low drone that slowly beats against itself, and wind
        for f, a in ((hz(45), 0.10), (hz(45) * 1.004, 0.10), (hz(52), 0.05)):
            out += (np.sin(2 * np.pi * f * t) * a).astype(np.float32)
        wind = lowpass(rng.normal(0, 1, n).astype(np.float32), 900) * 7
        out += wind * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t + 1)) * 0.5
    if kind == "lullaby":
        # a music box, slightly out of tune, in A minor
        notes = [76, 81, 84, 83, 81, 76, 77, 76, 74, 77, 81, 80, 81, 76, 72, 71, 69, 72, 76, 75, 76, 81, 79, 77]
        beat = 0.46
        for i in range(int(seconds / beat)):
            m = notes[i % len(notes)]
            f = hz(m) * (1 + rng.uniform(-0.006, 0.006))
            d = 1.4
            tt = np.arange(int(d * SR)) / SR
            tone = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt) + 0.15 * np.sin(2 * np.pi * 2.76 * f * tt)
            add((tone * np.exp(-tt / 0.4) * np.minimum(1, tt / 0.004) * 0.10).astype(np.float32), i * beat)
    if kind == "drone":
        # the train: chuffs that speed up
        chuff_t, gap = 0.2, 0.42
        while chuff_t < seconds:
            m = int(0.16 * SR)
            b = rng.normal(0, 1, m).astype(np.float32)
            b = (b - lowpass(b, 6)) * np.exp(-np.arange(m) / (0.05 * SR)) * 0.35
            add(b, chuff_t)
            chuff_t += gap
            gap = max(0.24, gap * 0.985)
    if kind == "organ":
        beat = 60 / 100
        bar = 4 * beat
        chords = [(50, 3), (46, 4), (43, 3), (45, 4)]
        for b in range(int(seconds / bar) + 1):
            root, third = chords[b % 4]
            length = bar + 0.4
            tt = np.arange(int(length * SR)) / SR
            pad = np.zeros_like(tt, dtype=np.float32)
            for semis in (0, third, 7, 12):
                f = hz(root + semis)
                ph = 2 * np.pi * f * tt
                pad += (np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)).astype(np.float32)
            add(pad * env_ar(len(tt), 0.15, 0.45) * 0.022, b * bar)
            for k, semis in enumerate([0, third, 7, 12, 7, third, 7, 12]):
                ts = b * bar + k * beat / 2
                tt2 = np.arange(int(0.8 * SR)) / SR
                f = hz(root + 24 + semis)
                tone = np.sin(2 * np.pi * f * tt2) + 0.25 * np.sin(2 * np.pi * 2 * f * tt2)
                add((tone * np.exp(-tt2 / 0.3) * np.minimum(1, tt2 / 0.004) * 0.08).astype(np.float32), ts)
            for k in (0, 2):
                tt3 = np.arange(int(0.4 * SR)) / SR
                f = hz(root - 12) * (1 + 0.5 * np.exp(-tt3 / 0.03))
                add((np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt3 / 0.14) * np.minimum(1, tt3 / 0.004) * 0.3).astype(np.float32), b * bar + k * beat)
    return out


# ---------------------------------------------------------------------------------------------
# Putting a short together
# ---------------------------------------------------------------------------------------------
def timeline(spec):
    t = 0.0
    out = []
    for sc in spec["scenes"]:
        audio, words = voice_clip(sc.line)
        vstart = t + sc.lead
        dur = sc.lead + len(audio) / SR + sc.gap
        out.append({"scene": sc, "start": t, "dur": dur, "vstart": vstart, "audio": audio,
                    "words": [[w0, w1 + sc.lead, w2 + sc.lead] for w0, w1, w2 in words]})
        t += dur
    return out, t


BED_FX = ("fire", "heartbeat", "thunder")   # long sounds: pulled down under the narrator; the short hits stay


def soundtrack(spec, tl, total, seed=5):
    rng = np.random.default_rng(seed)
    n = int((total + 0.3) * SR)
    music = music_bed(spec["music"], total + 0.3, rng)[:n]
    duck = np.ones(n, np.float32)
    voice = np.zeros(n, np.float32)
    bed = np.zeros(n, np.float32)
    hits = np.zeros(n, np.float32)
    for seg in tl:
        i = int(seg["vstart"] * SR)
        a = seg["audio"]
        j = min(n, i + len(a))
        voice[i:j] += a[:j - i]
        duck[max(0, i - int(0.12 * SR)):j] = 0.0
        for kind, when in seg["scene"].sfx:
            at = when if isinstance(when, (int, float)) else word_at(seg["words"], when, 0.0)
            snd = sfx(kind, rng)
            k = max(0, int((seg["start"] + at - (0.22 if kind == "whoosh" else 0.0)) * SR))
            if kind == "fire":
                keep = max(1, int((seg["dur"] - at) * SR))
                snd = snd[:keep] * env_ar(min(len(snd), keep), 0.4, 0.4) * 0.45
            if kind == "thunder":
                snd = snd * 0.7
            m = min(n, k + len(snd))
            (bed if kind in BED_FX else hits)[k:m] += snd[:m - k]
    duck = lowpass(duck, int(0.1 * SR))            # 1 where nobody's talking, 0 under the voice
    mix = (voice * 2.0                             # the narrator first
           + music * (0.25 + 0.75 * duck) * 0.55   # about 12 dB under the voice while she talks
           + bed * (0.35 + 0.65 * duck) * 0.55
           + hits * 0.5)
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    fade = int(0.25 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix / max(1e-6, float(np.max(np.abs(mix)))) * 0.92


def render(short, outdir, stills=False):
    spec = SHORTS[short]
    tl, total = timeline(spec)
    theme = spec["theme"]
    if theme == "halloween":
        hw.FACES[:] = [hw.face_layer(s) for _, _, s, _ in hw.PUMPKINS]
        base = hw.night_base()
        atm = Atmos(tint=(170, 150, 210), fog=0.22, vignette=0.6, grain=10, seed=4)
    elif theme == "woods":
        base = woods_base()
        atm = Atmos(tint=(190, 205, 210), fog=0.34, vignette=0.85, grain=14, seed=6)
    else:
        base = noir_base()
        atm = Atmos(tint=(196, 196, 204), fog=0.30, vignette=0.9, grain=18, seed=2)
    for seg in tl:
        sc = seg["scene"]
        if sc.prep and not sc.ctx:
            shared = next((s2["scene"].ctx for s2 in tl if s2["scene"].prep is sc.prep and s2["scene"].ctx), None)
            if shared:
                sc.ctx.update(shared)
            else:
                sc.prep(sc.ctx)
    if theme == "woods":
        woods_ctx = next(seg["scene"].ctx for seg in tl if seg["scene"].ctx)
    bars = [{"start": s["start"], "dur": s["dur"]} for s in tl]

    def frame_at(t):
        idx = max(i for i, s in enumerate(tl) if t >= s["start"] - 1e-9)
        seg = tl[idx]
        u = t - seg["start"]
        f = base.copy()
        if theme == "halloween":
            hw.animate(f, t)
        if theme == "woods":
            draw_woods(f, t, woods_ctx, total)
        atm.fog(f, t, y0=1050 if theme != "woods" else 980, y1=330)
        seg["scene"].draw(f, u, seg["words"], seg["scene"].ctx)
        caption(f, seg["words"], u)
        vr.progress(f, bars, t, total)
        flash = lightning(u, seg["scene"].flash_at) if seg["scene"].flash_at is not None else 0.0
        atm.finish(f, t, flicker=0.6 if theme == "noir" else 0.0, flash=flash)
        return f

    os.makedirs(outdir, exist_ok=True)
    if stills:
        paths = []
        for k, seg in enumerate(tl):
            t = seg["start"] + min(seg["dur"] - 0.05, max(seg["words"][-1][2] - 0.2, 0.5) if seg["words"] else 1.0)
            p = os.path.join(outdir, f"{short}-still-{k + 1}.png")
            frame_at(t).convert("RGB").save(p)
            paths.append(p)
        return paths
    track = os.path.join(outdir, f"{short}.wav")
    mix = soundtrack(spec, tl, total)
    with wave.open(track, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    n = int(math.ceil(total * FPS))
    out = os.path.join(outdir, f"lpwn-halloween-{short}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", track,
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-g", str(FPS * 2), "-keyint_min", str(FPS * 2), "-sc_threshold", "0", "-r", str(FPS),
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-ar", "48000", "-ac", "2",
           "-c:a", "aac", "-b:a", "160k", "-t", f"{n / FPS:.3f}", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        f = frame_at(i / FPS)
        if i == int(0.4 * FPS):
            f.convert("RGB").save(os.path.join(outdir, f"{short}-cover.jpg"), quality=90)
        proc.stdin.write(f.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg couldn't make " + short)
    print(f"Made {out}: {total:.1f} s, {n} frames, {os.path.getsize(out) / 1e6:.1f} MB")
    return [out]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    outdir, names = args[0], (args[1:] or list(SHORTS))
    for name in names:
        print("\n".join(render(name, outdir, stills="--stills" in sys.argv)))
