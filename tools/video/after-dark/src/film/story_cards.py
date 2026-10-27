"""Text cards drawn over a scene in a La Porte After Dark short: a year, a quote, a newspaper headline (re-set from
the published text), a map with pins, or a photo (public domain, CC0 or CC BY only, credited on screen).

    draw(frame, spec, t, t_on, t_off, ctx)   frame: PIL RGBA; t: the reel clock; t_on/t_off: when it shows

Card specs (all text is ALL CAPS-safe; keep it short):
    {"kind": "year", "label": "YEAR OF DEATH", "value": "1925", "note": "NATIONAL PARK SERVICE"}
    {"kind": "quote", "lines": ["I too, am driftwood."], "by": "ALICE GRAY'S DIARY"}
    {"kind": "headline", "paper": "THE CHESTERTON TRIBUNE", "date": "NOVEMBER 16, 1916",
     "lines": ["NYMPH ALICE NOW", "A \\"DIANA\\""], "body": ["optional re-set lines of the article"]}
    {"kind": "map", "center": "Crown Point", "span": 0.9, "pins": ["Crown Point", "La Porte"], "hot": "Crown Point",
     "route": ["Crown Point", "Peotone"], "notes": {"Peotone": "hostages let go"}}
    (a route is a dashed line between pins: draw only legs the sources document)
    {"kind": "photo", "file": "path/to/picture.jpg", "credit": "Library of Congress, public domain"}
A headline or quote must be the real published words. If the exact words aren't known, use a "year" card or a
label instead: never invent a headline.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import reels_common as C
from reels_common import bs, W, H, T, fitT, glow, paste, appear, scaled, BONE, RED

HERE = os.path.dirname(os.path.abspath(__file__))
INK = (40, 30, 22, 255)
_cache = {}


def _font_file(name, size):
    from PIL import ImageFont
    key = ("file", name, int(size))
    if key not in _cache:
        _cache[key] = ImageFont.truetype(os.path.join(C.FONTS, name), int(size))
    return _cache[key]


def fit_font(kind, text, size, max_w, min_size=24):
    s = int(size)
    while s > min_size and C.font(kind, s).getlength(text) > max_w:
        s -= 2
    return C.font(kind, s)


# --------------------------------------------------------------------------------------------- year

def year_card(spec):
    w, h = 980, 620
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    parts = []
    if spec.get("label"):
        parts.append((glow(T(spec["label"].upper(), "bold", 44, (226, 226, 220), tracking=6), (0, 0, 0), 14, 0.9), 0))
    v = str(spec.get("value", ""))
    parts.append((glow(fitT(v, "black", 260, (246, 244, 236), max_w=w - 40, min_size=120), (0, 0, 0), 30, 0.9), 1))
    if spec.get("note"):
        parts.append((glow(fitT(spec["note"].upper(), "xbold", 46, RED, max_w=w - 40, min_size=26, tracking=3),
                           (90, 0, 0), 20, 0.7), 2))
    y = 40
    for im, k in parts:
        img.alpha_composite(im, ((w - im.width) // 2, y))
        y += im.height + (6 if k == 0 else 4)
    return img


# --------------------------------------------------------------------------------------------- quote

def quote_card(spec):
    w = 900
    f = C.font("typew", 50)
    lines = []
    for ln in spec.get("lines", []):
        words, cur = ln.split(), ""
        for wd in words:
            test = (cur + " " + wd).strip()
            if f.getlength(test) > w - 140 and cur:
                lines.append(cur)
                cur = wd
            else:
                cur = test
        if cur:
            lines.append(cur)
    h = 150 + 70 * len(lines) + (80 if spec.get("by") else 0)
    card = bs.aged_paper(w, h, seed=int(spec.get("seed", 31)))
    d = ImageDraw.Draw(card)
    d.text((44, 18), "“", font=C.font("lora_sb", 120), fill=(120, 40, 30, 255))
    y = 96
    for ln in lines:
        d.text(((w - f.getlength(ln)) / 2, y), ln, font=f, fill=INK)
        y += 70
    if spec.get("by"):
        fb = C.font("fell_sc", 40)
        by = "— " + spec["by"]
        d.text(((w - fb.getlength(by)) / 2, y + 20), by, font=fb, fill=(70, 50, 34, 255))
    return card.rotate(float(spec.get("tilt", -1.5)), resample=Image.BICUBIC, expand=True)


# --------------------------------------------------------------------------------------------- headline

def headline_card(spec):
    w = 920
    paper = spec.get("paper", "").upper()
    date = spec.get("date", "").upper()
    heads = [x.upper() for x in spec.get("lines", [])]
    body = spec.get("body", [])
    fm = _font_file("UnifrakturMaguntia.ttf", 66)
    if fm.getlength(spec.get("paper", "")) > w - 80:
        fm = _font_file("UnifrakturMaguntia.ttf", int(66 * (w - 80) / fm.getlength(spec.get("paper", ""))))
    fd = C.font("oldst", 26)
    fh = [fit_font("oldst_b", hl, 92, w - 90, 40) for hl in heads]
    fb = C.font("oldst", 30)
    h = 60 + 86 + 50 + sum(int(f.size * 1.08) for f in fh) + 40 + (len(body) * 40 if body else 4 * 26) + 50
    card = bs.aged_paper(w, h, seed=int(spec.get("seed", 23)), color=(222, 210, 184))
    d = ImageDraw.Draw(card)
    name = spec.get("paper", "")
    d.text(((w - fm.getlength(name)) / 2, 34), name, font=fm, fill=INK)
    y = 34 + 86
    d.line([(40, y), (w - 40, y)], fill=(60, 46, 34, 255), width=3)
    d.text(((w - fd.getlength(date)) / 2, y + 8), date, font=fd, fill=(60, 46, 34, 255))
    y += 44
    d.line([(40, y), (w - 40, y)], fill=(60, 46, 34, 255), width=2)
    y += 22
    for hl, f in zip(heads, fh):
        d.text(((w - f.getlength(hl)) / 2, y), hl, font=f, fill=(24, 18, 14, 255))
        y += int(f.size * 1.08)
    y += 16
    d.line([(w / 2 - 120, y), (w / 2 + 120, y)], fill=(80, 60, 44, 255), width=2)
    y += 24
    if body:
        for ln in body:
            d.text((60, y), ln, font=fb, fill=(50, 40, 30, 255))
            y += 40
    else:                                                             # unreadable column lines, not invented text
        r = np.random.default_rng(int(spec.get("seed", 23)))
        for k in range(4):
            x0 = 60
            while x0 < w - 80:
                ln = r.uniform(30, 120)
                d.rectangle((x0, y + 6, min(w - 60, x0 + ln), y + 14), fill=(120, 104, 86, 150))
                x0 += ln + r.uniform(8, 14)
            y += 26
    card = card.rotate(float(spec.get("tilt", 1.2)), resample=Image.BICUBIC, expand=True)
    return card


# --------------------------------------------------------------------------------------------- map

_REGION = None


def region():
    global _REGION
    if _REGION is None:
        _REGION = json.load(open(os.path.join(HERE, "data", "region.json")))
    return _REGION


def map_card(spec, w=960, h=860):
    import skia
    from core import Canvas, poly_path, paint
    R = region()
    towns = R["towns"]
    cen = spec.get("center", "La Porte")
    lat0, lon0 = towns[cen] if isinstance(cen, str) else cen
    span = float(spec.get("span", 0.9))                               # degrees of latitude top to bottom
    k = math.cos(math.radians(lat0))
    sy = h / span
    sx = sy * k

    def P(lon, lat):
        return (w / 2 + (lon - lon0) * sx, h / 2 - (lat - lat0) * sy)

    c = Canvas(w, h)
    c.rect(0, 0, w, h, "#0d1416")
    tint = {"IN": "#16211f", "IL": "#0f1516", "MI": "#121a1b"}
    for co in R["counties"]:
        for ring in co["rings"]:
            pts = [P(x, y) for x, y in ring]
            c.poly(pts, tint.get(co["state"], "#121b1d"))
            c.c.drawPath(poly_path(pts), paint("#2c3f41", 1.0, stroke=1.6))
    for ring in R["lake"][:1]:
        pts = [P(x, y) for x, y in ring]
        c.poly(pts, "#0b2330")
        c.c.drawPath(poly_path(pts), paint("#3d6a78", 1.0, stroke=2.4))
    img = Image.fromarray((np.clip(c.rgba(), 0, 1) * 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(img)
    lab_f = C.font("bold", 30)
    small = C.font("semi", 26)
    note_f = C.font("semi", 24)
    # pins and their labels first, so the state names can stay clear of them
    hot = spec.get("hot")
    notes = spec.get("notes") or {}
    marks, taken = [], []
    for name in spec.get("pins", [cen] if isinstance(cen, str) else []):
        if name not in towns:
            raise KeyError("map: no town %r in data/region.json (add it with its coordinates)" % name)
        x, y = P(towns[name][1], towns[name][0])
        note = notes.get(name)
        tw = max(lab_f.getlength(name.upper()), note_f.getlength(note.upper()) if note else 0)
        tx = x + 18 if x + 18 + tw < w - 10 else x - 18 - tw
        marks.append((name, x, y, name == hot, tx, note))
        taken.append((min(x - 16, tx), y - 22, max(x + 16, tx + tw), y + (46 if note else 16)))

    def free(r):
        return all(r[2] < q[0] or r[0] > q[2] or r[3] < q[1] or r[1] > q[3] for q in taken)

    # the lake's and states' names, in the first spot that's in view and clear
    for txt, spots, col in (("LAKE MICHIGAN", ((-87.2, 41.9), (-87.0, 42.0), (-86.9, 41.85)), (120, 170, 190, 220)),
                            ("ILLINOIS", ((-87.78, 41.32), (-87.8, 41.5), (-87.85, 41.2), (-87.75, 41.62)),
                             (150, 160, 156, 200)),
                            ("INDIANA", ((-86.95, 41.3), (-87.05, 41.2), (-86.8, 41.45)), (170, 184, 176, 210)),
                            ("MICHIGAN", ((-86.35, 42.0), (-86.5, 41.95)), (150, 160, 156, 200))):
        tw = small.getlength(txt)
        for lon, lat in spots:
            tx, ty = P(lon, lat)
            r = (tx - tw / 2 - 6, ty - 4, tx + tw / 2 + 6, ty + 32)
            if 20 < r[0] and r[2] < w - 20 and 20 < ty < h - 50 and free(r):
                d.text((tx - tw / 2, ty), txt, font=small, fill=col)
                taken.append(r)
                break
    route = spec.get("route")
    if route and all(r in towns for r in route):
        pts = [P(towns[r][1], towns[r][0]) for r in route]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = int(math.hypot(x1 - x0, y1 - y0) / 18)
            for i in range(n):
                if i % 2 == 0:
                    a, b = i / n, (i + 0.6) / n
                    d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)],
                           fill=(255, 210, 120, 230), width=5)
    for name, x, y, is_hot, tx, note in marks:
        r = 9 if not is_hot else 13
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255) if not is_hot else (242, 64, 52, 255),
                  outline=(0, 0, 0, 255), width=3)
        d.text((tx + 2, y - 18 + 2), name.upper(), font=lab_f, fill=(0, 0, 0, 200))
        d.text((tx, y - 18), name.upper(), font=lab_f, fill=(240, 238, 230, 255) if not is_hot else (255, 214, 72, 255))
        if note:
            d.text((tx + 2, y + 16 + 2), note.upper(), font=note_f, fill=(0, 0, 0, 200))
            d.text((tx, y + 16), note.upper(), font=note_f, fill=(255, 196, 120, 255))
    marks = [(n_, x, y, h_) for n_, x, y, h_, _, _ in marks]
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=26, fill=255)
    img.putalpha(mask)
    frame = Image.new("RGBA", (w + 12, h + 12), (0, 0, 0, 0))
    ImageDraw.Draw(frame).rounded_rectangle((0, 0, w + 11, h + 11), radius=30, fill=(230, 228, 220, 255))
    frame.alpha_composite(img, (6, 6))
    return frame, [(n, x + 6, y + 6, hot_) for n, x, y, hot_ in marks]


# --------------------------------------------------------------------------------------------- photo

def photo_card(spec):
    im = Image.open(spec["file"]).convert("RGB")
    w = 900
    s = w / im.width
    im = im.resize((w, int(im.height * s)), Image.LANCZOS)
    if im.height > 1000:
        y0 = (im.height - 1000) // 2
        im = im.crop((0, y0, w, y0 + 1000))
    a = np.asarray(im, np.float32)
    if spec.get("tone", "sepia") == "sepia":
        g = a.mean(axis=2, keepdims=True)
        a = g * np.array([1.06, 0.97, 0.82], np.float32)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    frame = Image.new("RGBA", (im.width + 28, im.height + 28), (236, 230, 216, 255))
    frame.alpha_composite(im, (14, 14))
    return frame.rotate(float(spec.get("tilt", -1.0)), resample=Image.BICUBIC, expand=True)


BUILD = {"year": year_card, "quote": quote_card, "headline": headline_card, "photo": photo_card}


def draw(frame, spec, t, t_on, t_off, ctx, y=None):
    """Draw the card: it rises in at t_on, sits with a slow drift and fades by t_off."""
    kind = spec["kind"]
    if "img" not in ctx:
        if kind == "map":
            ctx["img"], ctx["marks"] = map_card(spec)
        else:
            ctx["img"] = BUILD[kind](spec)
        sh = Image.new("RGBA", (ctx["img"].width + 80, ctx["img"].height + 80), (0, 0, 0, 0))
        sh.alpha_composite(Image.new("RGBA", ctx["img"].size, (0, 0, 0, 170)), (40, 40))
        ctx["shadow"] = sh.filter(ImageFilter.GaussianBlur(22))
    if t < t_on - 0.01 or (t_off is not None and t > t_off + 0.3):
        return
    a = appear(t, t_on, 0.35)
    if t_off is not None:
        a *= 1 - C.ease((t - (t_off - 0.25)) / 0.3)
    if a <= 0.003:
        return
    img = ctx["img"]
    cy = y if y is not None else spec.get("y", 760 if kind != "map" else 800)
    drift = 1.0 + 0.025 * min(1.0, max(0.0, t - t_on) / 5.0)
    rise = 26 * (1 - a)
    im = scaled(img, drift)
    paste(frame, ctx["shadow"], W / 2 + 10, cy + rise + 16, a * 0.9)
    paste(frame, im, W / 2, cy + rise, a)
    if kind == "map" and a > 0.5:                                     # the hot pin pulses
        for name, x, yy, hot in ctx["marks"]:
            if hot:
                k = (t * 1.2) % 1.0
                r = 14 + 46 * k
                ring = C.ring(r * drift, 4, (242, 64, 52), 0.8 * (1 - k))
                paste(frame, ring, W / 2 - im.width / 2 + x * drift, cy + rise - im.height / 2 + yy * drift, a)
    if kind == "photo" and spec.get("credit"):
        bs.credit_line(frame, spec["credit"])
