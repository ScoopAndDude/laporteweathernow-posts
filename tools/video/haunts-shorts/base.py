#!/usr/bin/env python3
"""The building blocks for the hauntings Shorts (Oct. 21, 2026), copied from the Belle Gunness Halloween shorts
(tools/video/belle-2026/shorts.py on the belle-video branch, made Oct. 20): fonts, fog/grain/flash, captions that
follow the narrator word by word, the narrator's voice, sounds and music written in code, and putting a short
together (1080x1920, 30 fps, H.264 + AAC 48 kHz). Changed here: the voice is read from voice/<id>.flac (the
documentary's voice.py), the pictures come from tools/video/haunts-doc/images, and render() takes the shorts."""


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
DOCDIR = os.path.join(REPO, "tools", "video", "haunts-doc")


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
# The voice (voice/<id>.flac and voice/voice.json, made by voice.py in GitHub Actions)
# ---------------------------------------------------------------------------------------------
VOICE_DIR = os.path.join(HERE, "voice")
LINES = {}


def load_voice():
    LINES.clear()
    p = os.path.join(VOICE_DIR, "voice.json")
    if os.path.exists(p):
        LINES.update({l["id"]: l for l in json.load(open(p, encoding="utf-8"))["lines"]})


def voice_clip(lid):
    """The line's audio at 48 kHz with the leading and trailing silence trimmed, and its word times."""
    import soundfile as sf
    a, rate = sf.read(os.path.join(VOICE_DIR, lid + ".flac"), dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
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


SHORTS = {}
PREFIX = "lpwn-haunted-"


def render(short, outdir, stills=False):
    spec = SHORTS[short]
    tl, total = timeline(spec)
    theme = spec["theme"]
    if theme.startswith("photo"):
        base = Image.new("RGBA", (W, H), (8, 8, 10, 255))
        atm = Atmos(tint=(196, 196, 204) if theme != "photo-warm" else (220, 190, 160),
                    fog=0.16 if theme != "photo-night" else 0.30, vignette=0.75, grain=16 if theme == "photo" else 10, seed=2)
    elif theme == "halloween":
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
    global BRAND
    BRAND = vr.brand_row()

    def frame_at(t):
        idx = max(i for i, s in enumerate(tl) if t >= s["start"] - 1e-9)
        seg = tl[idx]
        u = t - seg["start"]
        f = base.copy()
        if theme == "halloween":
            hw.animate(f, t)
        if theme == "woods":
            draw_woods(f, t, woods_ctx, total)
        if not theme.startswith("photo") or theme == "photo-night":
            atm.fog(f, t, y0=1050 if theme != "woods" else 980, y1=330)
        seg["scene"].draw(f, u, seg["words"], seg["scene"].ctx)
        if theme.startswith("photo"):
            f.alpha_composite(BRAND, (0, 175))
        caption(f, seg["words"], u)
        vr.progress(f, bars, t, total)
        flash = lightning(u, seg["scene"].flash_at) if seg["scene"].flash_at is not None else 0.0
        atm.finish(f, t, flicker=0.6 if theme in ("noir", "photo") else 0.0, flash=flash)
        return f

    os.makedirs(outdir, exist_ok=True)
    if isinstance(stills, (list, tuple)):                        # frames at these times (seconds)
        paths = []
        for t in stills:
            p = os.path.join(outdir, f"{short}-at-{t:05.2f}.png")
            frame_at(min(t, total - 0.01)).convert("RGB").save(p)
            paths.append(p)
        return paths
    if stills:
        p = os.path.join(outdir, f"{short}-still-0.png")          # the cover frame (0.4 s)
        frame_at(0.4).convert("RGB").save(p)
        paths = [p]
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
    out = os.path.join(outdir, f"{PREFIX}{short}.mp4")
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



# =============================================================================================
# Real pictures (Oct. 20, 2026; Scoop: "use real images"): 1908 photos of Belle Gunness and her farm (public
# domain, or scans shared under CC BY by Steve Shook), Hesston's No. 242 (Franklin Campbell, CC BY 2.0) and
# pumpkin patch photos (CC BY / CC0), from images/ (fetch_images.py). Only public domain, CC0 and CC BY
# pictures are used (no share-alike), and each CC BY one is credited on screen and in the post.
# =============================================================================================
import re as _re
from PIL import ImageEnhance, ImageOps


IMGDIR = os.path.join(DOCDIR, "images")
MANIFEST = {x["file"]: x for x in json.load(open(os.path.join(IMGDIR, "manifest.json"), encoding="utf-8"))}


def credit(f):
    m = MANIFEST[f]
    lic = (m.get("license") or "").strip()
    who = _re.sub(r"\s+from\s.*$", "", _re.sub(r"(Unknown author)+", "", m.get("artist") or "")).strip()
    if lic.lower().startswith(("public domain", "cc0")):
        return ""
    return f"Photo: {who} / {lic}"


def photo(f, tone, inset=0.0):
    im = Image.open(os.path.join(IMGDIR, f)).convert("RGB")
    if inset:
        dx, dy = int(im.width * inset), int(im.height * inset)
        im = im.crop((dx, dy, im.width - dx, im.height - dy))
    if tone == "sepia":
        g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
        g = ImageEnhance.Contrast(g).enhance(1.12)
        im = ImageOps.colorize(g, black=(12, 9, 7), mid=(118, 94, 68), white=(238, 218, 180))
    elif tone == "night":
        im = ImageEnhance.Color(im).enhance(0.3)
        im = ImageEnhance.Brightness(im).enhance(0.62)
        im = ImageEnhance.Contrast(im).enhance(1.22)
        arr = np.asarray(im, np.float32) * np.array([0.70, 0.86, 1.10], np.float32)
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    elif tone == "pumpkin":
        im = ImageEnhance.Brightness(im).enhance(0.66)
        im = ImageEnhance.Contrast(im).enhance(1.12)
    return im.convert("RGBA")


def kenburns(frame, im, u, dur, z=(1.0, 1.12), f0=(0.5, 0.5), f1=(0.5, 0.5)):
    """The photo fills the frame and slowly pushes in; returns a function mapping photo points to the screen."""
    k = min(1.0, max(0.0, u / max(0.1, dur)))
    k = k * k * (3 - 2 * k)
    zz = z[0] + (z[1] - z[0]) * k
    fx, fy = f0[0] + (f1[0] - f0[0]) * k, f0[1] + (f1[1] - f0[1]) * k
    s = max(W / im.width, H / im.height) * zz
    cw, ch = W / s, H / s
    cx = min(max(fx * im.width, cw / 2), im.width - cw / 2)
    cy = min(max(fy * im.height, ch / 2), im.height - ch / 2)
    x0, y0 = cx - cw / 2, cy - ch / 2
    frame.alpha_composite(im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch)))
    return lambda px, py: ((px * im.width - x0) * s, (py * im.height - y0) * s)


def _shade():
    a = np.zeros((H, 1), np.float32)
    y = np.arange(H, dtype=np.float32)[:, None]
    a += np.clip(1 - y / 720, 0, 1) ** 1.3 * 175                      # dark at the top, for titles
    a += np.clip((y - 1080) / 420, 0, 1) ** 1.2 * 205                 # and at the bottom, for captions
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.putalpha(Image.fromarray(np.repeat(np.clip(a, 0, 230), W, axis=1).astype(np.uint8), "L"))
    return img


SHADE = None


def shade(frame):
    global SHADE
    if SHADE is None:
        SHADE = _shade()
    frame.alpha_composite(SHADE)


def credit_line(frame, text):
    if text:
        img = T(text, "semi", 25, (235, 235, 235, 235), stroke=2, stroke_fill=(0, 0, 0))
        frame.alpha_composite(img, (X0 - 10, 1478))


def embers(frame, u, k, n=46):
    """Embers rising and an orange glow from below (over a photo)."""
    if k <= 0:
        return
    g = soft_dot(380, (255, 104, 20), int(120 * k))
    frame.alpha_composite(g, (W // 2 - g.width // 2, 1250 - g.height // 2))
    for i in range(int(n * k)):
        ph = (u * (0.35 + (i % 9) * 0.05) + i * 0.137) % 1.0
        x = (i * 211) % W + 40 * math.sin(u * 1.7 + i)
        y = 1500 - ph * 1250
        frame.alpha_composite(soft_dot(3 + i % 3, (255, 180, 70), int(255 * (1 - ph) * k)), (int(x), int(y)))


def ghosts_over(frame, t, ctx, spots=((150, 760), (830, 640), (500, 560))):
    for i, (gx, gy) in enumerate(spots):
        a = 0.10 + 0.28 * (0.5 + 0.5 * math.sin(t * 1.1 + i * 2.1))
        frame.alpha_composite(vr.with_alpha(ctx["ghost"], a), (gx - 75, int(gy + 16 * math.sin(t * 1.6 + i))))


def emerging(f, tone, scale=2.0, blur=0.9, edge=(0.14, 0.10, 0.22, 0.30)):
    """A small portrait made ready to float in the dark: the halftone and JPEG blocks softened,
    enlarged once (sharpened after), and the edges faded to black (left, top, right, bottom)."""
    im = photo(f, tone).convert("RGB").filter(ImageFilter.GaussianBlur(blur))
    im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=3, percent=70, threshold=2))
    w, h = im.size
    x = np.arange(w, dtype=np.float32)[None, :] / w
    y = np.arange(h, dtype=np.float32)[:, None] / h
    m = np.clip(np.minimum(x / edge[0], (1 - x) / edge[2]), 0, 1) * np.clip(np.minimum(y / edge[1], (1 - y) / edge[3]), 0, 1)
    m = m * m * (3 - 2 * m)
    arr = np.asarray(im, np.float32) * m[..., None]
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    out.putalpha(Image.fromarray((m * 255).astype(np.uint8), "L"))
    return out


def float_in(frame, im, u, dur, w=(1180, 1400), focus=((0.41, 0.42), (0.41, 0.40)), at=(540, 640)):
    """The portrait, width w[0] -> w[1] px over the scene, with its focus point held at `at` on screen."""
    k = min(1.0, max(0.0, u / max(0.1, dur)))
    k = k * k * (3 - 2 * k)
    ww = w[0] + (w[1] - w[0]) * k
    hh = ww * im.height / im.width
    fx = focus[0][0] + (focus[1][0] - focus[0][0]) * k
    fy = focus[0][1] + (focus[1][1] - focus[0][1]) * k
    frame.alpha_composite(im.resize((int(ww), int(hh)), Image.BICUBIC), (int(at[0] - fx * ww), int(at[1] - fy * hh)))
