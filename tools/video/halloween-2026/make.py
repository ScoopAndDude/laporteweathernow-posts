#!/usr/bin/env python3
"""A one-off Halloween fall fun video for TikTok and YouTube Shorts (Oct. 20, 2026; Scoop: "make it festive
for halloween").

    python3 tools/video/halloween-2026/make.py OUTDIR [stills]

Saves OUTDIR/halloween-fall-fun-2026.mp4 (1080x1920, 30 fps, H.264 + AAC 48 kHz: the Daily Video's format),
about 15.5 seconds, and OUTDIR/cover.jpg. With "stills" it saves one PNG per scene instead.

Same rules as the Daily Video: the places and hours come from the trick-or-treat page's fall fun list
(trick-or-treat.json, checked Oct. 20) and every number from the National Weather Service forecast for
La Porte (checked Oct. 20, 11:35 a.m.). The night sky, moon, bats and jack-o'-lanterns are drawn here, and
the music is written here, note by note: no recordings, no stock footage, no AI pictures or sounds.
"""
import importlib.util
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
_spec = importlib.util.spec_from_file_location("video_render", os.path.join(REPO, "scripts", "video_render.py"))
vr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vr)

W, H, FPS = vr.W, vr.H, vr.FPS
X0, CW = vr.X0, vr.CW
ORANGE = (255, 138, 0)
GOLDEN = (255, 186, 70)
CREAM = (255, 243, 224)
LAV = (226, 214, 247)
FAINT = (176, 160, 204)
PURPLE = (139, 63, 217)
ENTER, EXIT = 0.34, 0.18
TOTAL = 15.6
NAME = "halloween-fall-fun-2026.mp4"

# What it says (from trick-or-treat.json's fall fun list and the NWS forecast, both checked Oct. 20, 2026).
FARMS = [("Coulter's Farm", "Westville · hayrides on weekends"),
         ("Fischer Farm", "La Porte · $3 corn maze, open daily"),
         ("Garwood Orchard", "La Porte · u-pick and wagon rides")]
HAUNTS = [("Hesston Ghost Train", "Last weekend: Sat. & Sun., noon to 5"),
          ("Niles Scream Park", "Niles, Mich. · haunted houses at night")]
WEEKEND = [("SAT", 66, "Mostly sunny"), ("SUN", 69, "Mostly sunny")]
NIGHTS = "Nights: 41° Friday, 47° Saturday"


# ---------------------------------------------------------------------------------------------
# Drawings (at 3x, then scaled down so the edges are smooth)
# ---------------------------------------------------------------------------------------------
def _ss(size):
    return Image.new("RGBA", (size * 3, size * 3), (0, 0, 0, 0))


def pumpkin(size, face=True, body=True, glow_face=False):
    """A jack-o'-lantern, size px wide. body/face can be drawn apart so the face can flicker."""
    img = _ss(size)
    S = size * 3
    d = ImageDraw.Draw(img)
    if body:
        d.line([(0.50 * S, 0.24 * S), (0.53 * S, 0.12 * S), (0.60 * S, 0.06 * S)], fill=(63, 107, 34), width=int(0.07 * S))
        for cx, rx, col in ((0.30, 0.24, (217, 89, 10)), (0.70, 0.24, (217, 89, 10)), (0.50, 0.27, (242, 116, 17))):
            d.ellipse(((cx - rx) * S, 0.22 * S, (cx + rx) * S, 0.92 * S), fill=col)
        for cx in (0.40, 0.60):
            d.ellipse(((cx - 0.09) * S, 0.24 * S, (cx + 0.09) * S, 0.90 * S), fill=(255, 140, 42, 120))
    if face:
        col = (255, 214, 72)
        d.polygon([(0.30 * S, 0.50 * S), (0.38 * S, 0.37 * S), (0.46 * S, 0.50 * S)], fill=col)
        d.polygon([(0.54 * S, 0.50 * S), (0.62 * S, 0.37 * S), (0.70 * S, 0.50 * S)], fill=col)
        d.polygon([(0.46 * S, 0.60 * S), (0.50 * S, 0.53 * S), (0.54 * S, 0.60 * S)], fill=col)
        mouth = [(0.26 + 0.48 * i / 40, 0.64 + 0.15 * math.sin(math.pi * i / 40)) for i in range(41)]
        top = [(0.74, 0.64), (0.66, 0.69), (0.62, 0.66), (0.58, 0.72), (0.54, 0.68), (0.50, 0.70), (0.46, 0.68),
               (0.42, 0.72), (0.38, 0.66), (0.34, 0.69), (0.26, 0.64)]
        d.polygon([(x * S, y * S) for x, y in mouth + top], fill=col)
    out = img.resize((size, size), Image.LANCZOS)
    if glow_face:
        halo = out.filter(ImageFilter.GaussianBlur(size * 0.05))
        r = Image.new("RGBA", out.size, (255, 170, 40, 0))
        r.putalpha(halo.getchannel("A").point(lambda v: int(v * 0.9)))
        r.alpha_composite(out)
        out = r
    return out


def bat(size, up):
    """A bat silhouette, size px wide, wings up or down."""
    img = _ss(size)
    S = size * 3
    d = ImageDraw.Draw(img)
    cx, cy, k = 0.5 * S, 0.5 * S, 0.48 * S
    wing = ([(0.10, -0.05), (0.35, -0.45), (0.60, -0.62), (0.85, -0.52), (1.00, -0.30), (0.86, -0.25), (0.72, -0.05),
             (0.56, -0.15), (0.42, 0.05), (0.28, -0.02), (0.12, 0.12)] if up else
            [(0.10, -0.05), (0.35, 0.00), (0.62, 0.08), (0.86, 0.22), (1.00, 0.42), (0.82, 0.36), (0.70, 0.50),
             (0.56, 0.36), (0.42, 0.48), (0.28, 0.30), (0.12, 0.18)])
    col = (9, 4, 16)
    for sgn in (1, -1):
        d.polygon([(cx + sgn * x * k, cy + y * k) for x, y in wing], fill=col)
    d.ellipse((cx - 0.13 * k, cy - 0.17 * k, cx + 0.13 * k, cy + 0.27 * k), fill=col)
    d.ellipse((cx - 0.10 * k, cy - 0.30 * k, cx + 0.10 * k, cy - 0.10 * k), fill=col)
    for sgn in (1, -1):
        d.polygon([(cx + sgn * 0.09 * k, cy - 0.24 * k), (cx + sgn * 0.06 * k, cy - 0.40 * k), (cx + sgn * 0.02 * k, cy - 0.27 * k)], fill=col)
    return img.resize((size, size), Image.LANCZOS)


def ghost(size):
    img = _ss(size)
    S = size * 3
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.18 * S, 0.08 * S, 0.82 * S, 0.80 * S), radius=int(0.32 * S), fill=(246, 240, 255))
    for i in range(4):
        x = 0.18 + 0.16 * i
        d.ellipse((x * S, 0.70 * S, (x + 0.16) * S, 0.92 * S), fill=(246, 240, 255))
    d.ellipse((0.35 * S, 0.32 * S, 0.45 * S, 0.46 * S), fill=(30, 12, 44))
    d.ellipse((0.55 * S, 0.32 * S, 0.65 * S, 0.46 * S), fill=(30, 12, 44))
    d.ellipse((0.44 * S, 0.52 * S, 0.56 * S, 0.64 * S), fill=(30, 12, 44))
    return img.resize((size, size), Image.LANCZOS)


MOON = (884, 300, 92)       # center x, center y, radius
PUMPKINS = [(70, 1590, 250, 0.0), (390, 1490, 330, 1.3), (770, 1610, 230, 2.1)]   # x, y, size, flicker phase


def night_base():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    k = (yy / H)[..., None]
    top, mid, bottom = (np.array(c, np.float32) for c in ((44, 18, 72), (27, 11, 46), (9, 5, 17)))
    img = np.where(k < 0.55, top * (1 - k / 0.55) + mid * (k / 0.55), mid * (1 - (k - 0.55) / 0.45) + bottom * ((k - 0.55) / 0.45))
    mx, my, mr = MOON
    dist = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2)
    g = np.clip(1 - dist / 620, 0, 1) ** 2.2 * 0.42
    img = img * (1 - g[..., None]) + np.array((255, 196, 110), np.float32) * g[..., None]
    low = np.clip(1 - np.sqrt((xx - W * 0.5) ** 2 + ((yy - H * 0.86) * 1.4) ** 2) / 700, 0, 1) ** 2 * 0.22   # pumpkin glow
    img = img * (1 - low[..., None]) + np.array((255, 120, 20), np.float32) * low[..., None]
    img = img + np.random.default_rng(7).normal(0, 2.0, (H, W, 1)).astype(np.float32)
    base = Image.fromarray(np.dstack([np.clip(img, 0, 255).astype(np.uint8), np.full((H, W), 255, np.uint8)]), "RGBA")
    # the moon
    S = 3
    m = Image.new("RGBA", (mr * 2 * S, mr * 2 * S), (0, 0, 0, 0))
    md = ImageDraw.Draw(m)
    md.ellipse((0, 0, mr * 2 * S - 1, mr * 2 * S - 1), fill=(255, 238, 180))
    craters = Image.new("RGBA", m.size, (0, 0, 0, 0))   # on their own layer, blended in (drawing them straight on would cut holes)
    cd = ImageDraw.Draw(craters)
    for cx, cy, r, a in ((0.62, 0.60, 0.15, 60), (0.36, 0.36, 0.09, 48), (0.68, 0.30, 0.06, 40)):
        cd.ellipse(((cx - r) * mr * 2 * S, (cy - r) * mr * 2 * S, (cx + r) * mr * 2 * S, (cy + r) * mr * 2 * S), fill=(214, 172, 92, a))
    m.alpha_composite(craters)
    m = m.resize((mr * 2, mr * 2), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))
    base.alpha_composite(m, (mx - mr, my - mr))
    # the hill and the pumpkins on it
    hill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hill)
    pts = [(x, 1770 - 60 * math.sin(x / W * math.pi * 1.3 + 0.4) - 25 * math.sin(x / 90)) for x in range(0, W + 1, 12)]
    hd.polygon(pts + [(W, H), (0, H)], fill=(10, 5, 18))
    base.alpha_composite(hill)
    for x, y, s, _ in PUMPKINS:
        base.alpha_composite(pumpkin(s, face=False), (x, y))
    base.alpha_composite(vr.brand_row(), (0, 175))
    return base


STARS = [(int(x), int(y), int(r), float(ph), float(f)) for x, y, r, ph, f in zip(
    np.random.default_rng(3).uniform(30, W - 30, 70), np.random.default_rng(4).uniform(130, 1350, 70),
    np.random.default_rng(5).choice([1, 1, 2, 2, 3], 70), np.random.default_rng(6).uniform(0, 6.28, 70),
    np.random.default_rng(8).uniform(0.4, 1.4, 70))]
STARS = [st for st in STARS if math.hypot(st[0] - MOON[0], st[1] - MOON[1]) > MOON[2] + 14]   # none on the moon
_STAR = {r: None for r in (1, 2, 3)}


def star_sprite(r):
    if _STAR[r] is None:
        s = Image.new("RGBA", (r * 6, r * 6), (0, 0, 0, 0))
        ImageDraw.Draw(s).ellipse((r * 2, r * 2, r * 4, r * 4), fill=(255, 255, 255, 255))
        _STAR[r] = s.filter(ImageFilter.GaussianBlur(r * 0.6))
    return _STAR[r]


BATS = [  # start x, y, speed px/s, bob, size, flap period
    (-140, 330, 92, 14, 120, 0.26), (380, 420, 70, 12, 86, 0.21), (760, 300, -60, 10, 100, 0.24), (1180, 450, -84, 12, 70, 0.19)]
_bat_frames = {}


def animate(frame, t):
    for x, y, r, ph, f in STARS:
        a = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * f * t + ph))
        sp = star_sprite(r)
        frame.alpha_composite(vr.with_alpha(sp, a), (x - r * 3, y - r * 3))
    for i, (x0, y0, v, bob, size, per) in enumerate(BATS):
        up = int(t / per) % 2 == 0
        key = (size, up)
        if key not in _bat_frames:
            _bat_frames[key] = bat(size, up)
        span = W + 300
        x = (x0 + v * t + 150) % span - 150
        y = y0 + bob * math.sin(2 * math.pi * 0.6 * t + i)
        frame.alpha_composite(_bat_frames[key], (int(x - size / 2), int(y - size / 2)))
    for i, (x, y, s, ph) in enumerate(PUMPKINS):
        a = 0.80 + 0.20 * math.sin(2 * math.pi * 1.7 * t + ph) * math.sin(2 * math.pi * 0.53 * t + 2 * ph)
        frame.alpha_composite(vr.with_alpha(FACES[i], max(0.55, min(1.0, a))), (x - FACES[i].info["pad"], y - FACES[i].info["pad"]))


def face_layer(size):
    f = pumpkin(size, body=False, glow_face=True)
    pad = int(size * 0.12)
    big = Image.new("RGBA", (size + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
    halo = Image.new("RGBA", big.size, (255, 150, 30, 0))
    mask = Image.new("L", big.size, 0)
    mask.paste(f.getchannel("A"), (pad, pad))
    halo.putalpha(mask.filter(ImageFilter.GaussianBlur(size * 0.06)).point(lambda v: int(v * 0.7)))
    big.alpha_composite(halo)
    big.alpha_composite(f, (pad, pad))
    big.info["pad"] = pad
    return big


# ---------------------------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------------------------
L = vr.Layer


def label(text, color=GOLDEN):
    return vr.text_img(text.upper(), "bold", 36, color, tracking=4)


def glowing(text, weight, size, color, glow_color, max_w=CW, min_size=90):
    img = vr.fit_line(text, weight, size, color, max_w, min_size=min_size)
    g = vr.glow(img, glow_color, radius=30, strength=0.6)
    return img, g


def card(name, line, accent, art=None):
    w, h = CW + 20, 176
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=30, fill=(40, 17, 64, 232), outline=accent + (150,), width=3)
    d.rounded_rectangle((0, 0, 16, h - 1), radius=8, fill=accent + (255,))
    nm = vr.fit_line(name, "xbold", 60, CREAM, w - 210, min_size=44)
    ln = vr.fit_line(line, "semi", 40, LAV, w - 210, min_size=30)
    y = (h - nm.height - 16 - ln.height) // 2
    img.alpha_composite(nm, (46, y))
    img.alpha_composite(ln, (46, y + nm.height + 16))
    if art is not None:
        img.alpha_composite(art, (w - art.width - 26, (h - art.height) // 2))
    return img


def hook():
    lab = label("This weekend · Oct. 24-25")
    a, ag = glowing("SPOOKY", "black", 230, ORANGE, (255, 110, 0))
    b = vr.fit_line("fall fun", "black", 170, CREAM, CW)
    c = vr.fit_line("near La Porte", "xbold", 84, LAV, CW)
    s = vr.fit_para("Pumpkins, hayrides, a ghost train and haunted houses", "semi", 50, LAV, CW, max_lines=2, min_size=40, align="center")
    items = [(lab, 40), (a, 6), (b, 30), (c, 50), (s, 0)]
    ys = vr.stack_center(items, top=360, bottom=1420)
    pad = ag.info["pad"]
    return [L(lab, vr.centered(lab), ys[0], delay=0.0), L(ag, vr.centered(a) - pad, ys[1] - pad, delay=0.12, zoom=0.03),
            L(b, vr.centered(b), ys[2], delay=0.30), L(c, vr.centered(c), ys[3], delay=0.42), L(s, vr.centered(s), ys[4], delay=0.62)]


def farms():
    lab = label("Pumpkin patches")
    head = vr.fit_line("Pick your pumpkin", "black", 104, CREAM, CW)
    art = pumpkin(118, glow_face=True)
    cards = [card(n, l, ORANGE, art) for n, l in FARMS]
    items = [(lab, 26), (head, 44)] + [(c, 26) for c in cards[:-1]] + [(cards[-1], 0)]
    ys = vr.stack_center(items, top=350, bottom=1430)
    out = [L(lab, vr.centered(lab), ys[0]), L(head, vr.centered(head), ys[1], delay=0.08)]
    out += [L(c, X0 - 10, y, delay=0.30 + 0.22 * i) for i, (c, y) in enumerate(zip(cards, ys[2:]))]
    return out


def haunts():
    lab = label("Spooky rides", (196, 160, 255))
    a, ag = glowing("BOO!", "black", 250, CREAM, PURPLE)
    g = ghost(116)
    cards = [card(n, l, PURPLE, g) for n, l in HAUNTS]
    note = vr.fit_line("Niles is on Eastern time, an hour ahead", "semi", 36, FAINT, CW, min_size=28)
    items = [(lab, 20), (a, 40), (cards[0], 26), (cards[1], 26), (note, 0)]
    ys = vr.stack_center(items, top=350, bottom=1430)
    pad = ag.info["pad"]
    return [L(lab, vr.centered(lab), ys[0]), L(ag, vr.centered(a) - pad, ys[1] - pad, delay=0.06, zoom=0.04),
            L(cards[0], X0 - 10, ys[2], delay=0.34), L(cards[1], X0 - 10, ys[3], delay=0.56), L(note, vr.centered(note), ys[4], delay=0.8)]


def forecast():
    lab = label("Weekend forecast")
    head = vr.fit_line("Pumpkin-picking weather", "black", 84, CREAM, CW)
    w, h = (CW - 30) // 2, 470
    panels = []
    for day, temp, words in WEEKEND:
        p = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(p)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=(40, 17, 64, 232), outline=ORANGE + (150,), width=3)
        dl = vr.text_img(day, "black", 58, GOLDEN, tracking=4)
        ic = vr.icon("sun", 170)
        tp = vr.text_img(f"{temp}°", "black", 150, CREAM)
        wd = vr.fit_line(words, "semi", 40, LAV, w - 40, min_size=30)
        y = 30
        for im, gap in ((dl, 8), (ic, 0), (tp, 14), (wd, 0)):
            p.alpha_composite(im, ((w - im.width) // 2, y))
            y += im.height + gap
        panels.append(p)
    nights = vr.fit_line(NIGHTS, "semi", 46, LAV, CW, min_size=34)
    src = vr.text_img("National Weather Service forecast, Oct. 20", "semi", 30, FAINT)
    row = Image.new("RGBA", (CW, h), (0, 0, 0, 0))
    items = [(lab, 24), (head, 40), (row, 36), (nights, 26), (src, 0)]
    ys = vr.stack_center(items, top=350, bottom=1430)
    return [L(lab, vr.centered(lab), ys[0]), L(head, vr.centered(head), ys[1], delay=0.06),
            L(panels[0], X0, ys[2], delay=0.26), L(panels[1], X0 + w + 30, ys[2], delay=0.42),
            L(nights, vr.centered(nights), ys[3], delay=0.62), L(src, vr.centered(src), ys[4], delay=0.7)]


def ending():
    logo = vr.rounded(Image.open(os.path.join(vr.ASSETS, "logo-512.png")).convert("RGBA").resize((250, 250), Image.LANCZOS), 40)
    a = vr.fit_line("Hours for every spot", "xbold", 70, CREAM, CW)
    url = vr.pill("laporteweathernow.com", "xbold", 54, (16, 8, 26), GOLDEN + (255,), padx=40, pady=24)
    b = vr.fit_line("Trick-or-treat hours & fall fun", "semi", 46, LAV, CW, min_size=34)
    c, cg = glowing("Happy Halloween!", "black", 108, ORANGE, (255, 110, 0), min_size=70)
    src = vr.text_img("Source: National Weather Service", "semi", 28, FAINT)
    items = [(logo, 40), (a, 30), (url, 26), (b, 54), (c, 40), (src, 0)]
    ys = vr.stack_center(items, top=330, bottom=1440)
    pad = cg.info["pad"]
    return [L(logo, vr.centered(logo), ys[0]), L(a, vr.centered(a), ys[1], delay=0.08), L(url, vr.centered(url), ys[2], delay=0.18),
            L(b, vr.centered(b), ys[3], delay=0.28), L(cg, vr.centered(c) - pad, ys[4] - pad, delay=0.42, zoom=0.03),
            L(src, vr.centered(src), ys[5], delay=0.5)]


SCENES = [("hook", 0.0, 3.4, hook), ("farms", 3.4, 3.7, farms), ("haunts", 7.1, 3.3, haunts),
          ("forecast", 10.4, 2.9, forecast), ("end", 13.3, 2.3, ending)]


def build():
    return [{"id": i, "start": s, "dur": d, "layers": f()} for i, s, d, f in SCENES]


def frame_at(t, scenes, base, cache):
    idx = max(i for i, sc in enumerate(scenes) if t >= sc["start"])
    sc = scenes[idx]
    u = t - sc["start"]
    last = idx == len(scenes) - 1
    exit_a = 1.0 if last else max(0.0, min(1.0, (sc["start"] + sc["dur"] - t) / EXIT))
    frame = base.copy()
    animate(frame, t)
    settled = exit_a >= 0.999 and all(u - Lr.delay >= ENTER for Lr in sc["layers"])
    if settled and sc["id"] in cache:
        frame.alpha_composite(cache[sc["id"]])
    else:
        top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for Lr in sc["layers"]:
            if Lr.zoom:
                continue
            a = vr.ease((u - Lr.delay) / ENTER)
            if a <= 0:
                continue
            top.alpha_composite(vr.with_alpha(Lr.img, a * exit_a), (Lr.x, Lr.y + int(Lr.rise * (1 - a))))
        if settled:
            cache[sc["id"]] = top.copy()
        frame.alpha_composite(top)
    for Lr in sc["layers"]:          # the zooming titles, every frame
        if not Lr.zoom:
            continue
        a = vr.ease((u - Lr.delay) / ENTER) * exit_a
        if a <= 0:
            continue
        z = 1 + Lr.zoom * min(1.0, u / max(0.1, sc["dur"]))
        img = Lr.img.resize((int(Lr.img.width * z), int(Lr.img.height * z)), Image.BILINEAR)
        x, y = Lr.x - (img.width - Lr.img.width) // 2, Lr.y - (img.height - Lr.img.height) // 2
        frame.alpha_composite(vr.with_alpha(img, a), (x, y + int(Lr.rise * (1 - min(1.0, a / max(exit_a, 1e-6))))))
    vr.progress(frame, scenes, t, TOTAL)
    return frame


# ---------------------------------------------------------------------------------------------
# Music, written here: a spooky waltz-free 4/4 in D minor (96 beats a minute), organ chords, a music-box
# arpeggio, a heartbeat bass and a theremin glide at the start and the end.
# ---------------------------------------------------------------------------------------------
SR = 48000


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def music(seconds):
    n = int(seconds * SR)
    out = np.zeros(n, np.float32)
    t_all = np.arange(n) / SR
    beat = 60 / 96
    bar = 4 * beat
    chords = [(50, "m"), (46, "M"), (43, "m"), (45, "M"), (50, "m"), (46, "M"), (50, "m")]   # D3 Bb2 G2 A2 D3 Bb2 D3

    def add(sig, start):
        i = int(start * SR)
        if i >= n:
            return
        j = min(n, i + len(sig))
        out[i:j] += sig[:j - i]

    def env(length, attack, release):
        m = int(length * SR)
        e = np.ones(m, np.float32)
        a = max(1, int(attack * SR))
        r = max(1, int(release * SR))
        e[:a] = np.linspace(0, 1, a)
        e[-r:] *= np.linspace(1, 0, r)
        return e

    for b, (root, kind) in enumerate(chords):
        start = b * bar
        if start >= seconds:
            break
        length = min(bar + 0.45, seconds - start)
        tt = np.arange(int(length * SR)) / SR
        third = 3 if kind == "m" else 4
        pad = np.zeros_like(tt, dtype=np.float32)
        for semis in (0, third, 7, 12):
            f = hz(root + semis)
            for det in (-0.0018, 0.0018):
                vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * tt)
                ph = 2 * np.pi * f * (1 + det) * np.cumsum(vib) / SR
                pad += (np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.22 * np.sin(3 * ph) + 0.1 * np.sin(4 * ph)).astype(np.float32)
        add(pad * env(length, 0.18, 0.5) * 0.028, start)
        # music box: up and down the chord in eighth notes, two octaves up
        up = [0, third, 7, 12, 7, third, 7, 12] if b % 2 == 0 else [12, 7, third, 7, 0, third, 7, third]
        for k, semis in enumerate(up):
            ts = start + k * beat / 2
            if ts >= seconds:
                break
            dur = 0.9
            tt2 = np.arange(int(dur * SR)) / SR
            f = hz(root + 24 + semis)
            tone = np.sin(2 * np.pi * f * tt2) + 0.25 * np.sin(2 * np.pi * 2 * f * tt2) + 0.12 * np.sin(2 * np.pi * 2.76 * f * tt2)
            click = np.minimum(1, tt2 / 0.004)   # a 4 ms fade-in, so a note doesn't click
            add((tone * np.exp(-tt2 / 0.32) * click * 0.11).astype(np.float32), ts)
        # heartbeat bass on beats 1 and 3
        for k in (0, 2):
            ts = start + k * beat
            dur = 0.5
            tt3 = np.arange(int(dur * SR)) / SR
            f = hz(root - 12) * (1 + 0.5 * np.exp(-tt3 / 0.03))
            ph = 2 * np.pi * np.cumsum(f) / SR
            add((np.sin(ph) * np.exp(-tt3 / 0.16) * np.minimum(1, tt3 / 0.004) * 0.34).astype(np.float32), ts)
    # theremin: a wobbly glide, at the start and over the end card
    for start, length, path in ((0.0, 2.6, (69, 74, 72, 69)), (13.3, 2.2, (74, 77, 74))):
        tt4 = np.arange(int(length * SR)) / SR
        knots = np.linspace(0, length, len(path))
        midi = np.interp(tt4, knots, np.array(path, np.float32))
        f = 440.0 * 2 ** ((midi - 69) / 12) * (1 + 0.016 * np.sin(2 * np.pi * 6.3 * tt4))
        ph = 2 * np.pi * np.cumsum(f) / SR
        add((np.sin(ph) * env(length, 0.35, 0.8) * 0.12).astype(np.float32), start)
    # a soft whoosh at each scene change
    rng = np.random.default_rng(11)
    for start in [s for _, s, _, _ in SCENES[1:]]:
        length = 0.5
        noise = rng.normal(0, 1, int(length * SR)).astype(np.float32)
        win = np.hanning(160)
        noise = np.convolve(noise, win / win.sum(), mode="same")   # a soft, low whoosh, not a hiss
        e = np.sin(np.pi * np.linspace(0, 1, len(noise))) ** 2
        add(noise * e * 0.5, start - 0.22)
    fade = int(0.8 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(out * 1.4) / np.tanh(1.4)
    return out / max(1e-6, float(np.max(np.abs(out)))) * 0.89


def write_wav(path, a):
    pcm = (np.clip(a, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


FACES = []


def main(outdir, stills=False):
    os.makedirs(outdir, exist_ok=True)
    FACES[:] = [face_layer(s) for _, _, s, _ in PUMPKINS]
    base = night_base()
    scenes = build()
    cache = {}
    if stills:
        for sc in scenes:
            t = sc["start"] + min(sc["dur"] - EXIT - 0.05, 1.4)
            frame_at(t, scenes, base, cache).convert("RGB").save(os.path.join(outdir, f"still-{sc['id']}.png"))
        print("stills in", outdir)
        return 0
    track = os.path.join(outdir, "music.wav")
    write_wav(track, music(TOTAL + 0.2))
    n = int(math.ceil(TOTAL * FPS))
    out = os.path.join(outdir, NAME)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", track,
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-g", str(FPS * 2), "-keyint_min", str(FPS * 2), "-sc_threshold", "0", "-r", str(FPS),
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-ar", "48000", "-ac", "2",
           "-c:a", "aac", "-b:a", "160k", "-t", f"{n / FPS:.3f}", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS
        f = frame_at(t, scenes, base, cache)
        if i == int(1.6 * FPS):
            f.convert("RGB").save(os.path.join(outdir, "cover.jpg"), quality=90)
        proc.stdin.write(f.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg couldn't make the video")
    print(f"Made {out}: {TOTAL} seconds, {n} frames, {os.path.getsize(out) / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], stills=len(sys.argv) > 2 and sys.argv[2] == "stills"))
