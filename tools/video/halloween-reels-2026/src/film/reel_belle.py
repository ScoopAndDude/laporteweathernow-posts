"""Belle Gunness, Parts 3 and 4: Facebook reels (Oct. 22, 2026) in the series' own look.

    python3 reel_belle.py belle3|belle4 stills|video

Part 3, "The Newspaper Ad": her ad (re-created from its published text, and labeled that way), Andrew Helgelien
of South Dakota, her letters ("come prepared to stay forever"), January 1908.
Part 4, "Was the woman in the fire?": what Dr. Harry Long said about the body, the dentist and the coroner.
Photos: 1908 pictures of the case (public domain, or Steve Shook's scans under CC BY 2.0, credited on screen).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import reels_common as C
from reels_common import (bs, W, H, SR, BONE, SEPIA, INKC, BLOOD, RED, T, fitT, glow, paste, scaled, appear,
                          ease, ease_out, dim)

GEO = os.path.join(C.ROOT, "dl", "geo")


# ----------------------------------------------------------------------------- small helpers

def label_fn(text, t_end, y=284):
    img = glow(T(text, "bold", 34, BONE, tracking=4), (0, 0, 0), radius=14, strength=0.8)

    def draw(f, t):
        a = 1 - ease((t - (t_end - 0.3)) / 0.3)
        if a > 0:
            paste(f, img, W / 2, y, a)
    return draw


def typed(f, text, t, at, y, kind="mono", size=84, rate=0.06, x=None):
    n = int(max(0, min(len(text), (t - at) / rate + 1))) if t >= at else 0
    if n:
        full = T(text, kind, size, BONE, stroke=3)
        img = T(text[:n], kind, size, BONE, stroke=3)
        x0 = (W - full.width) // 2 if x is None else x
        f.alpha_composite(img, (int(x0), int(y - full.height / 2)))


def pencil(f, x0, x1, y, prog, width=7, color=BLOOD, seed=0):
    """A red pencil underline from x0 to x1 (screen px), drawn up to prog (0-1)."""
    if prog <= 0 or x1 <= x0:
        return
    S, pad = 3, int(width * 2 + 6)
    w, h = int(x1 - x0) + 2 * pad, int(width * 2 + 2 * pad)
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    xe = x0 + (x1 - x0) * min(1.0, prog)
    n = max(2, int((xe - x0) / 6))
    pts = [((x0 + (xe - x0) * i / n - x0 + pad) * S,
            (h / 2 + 2.2 * math.sin(i * 0.5 + seed) + (i / n) * 3 * math.sin(seed)) * S) for i in range(n + 1)]
    d.line(pts, fill=tuple(color) + (228,), width=int(width * S), joint="curve")
    img = img.resize((w, h), Image.LANCZOS)
    f.alpha_composite(img, (int(x0 - pad), int(y - h / 2)))


def scratch(dur=0.4, seed=0):
    """Pencil on paper."""
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n).astype(np.float32)
    x = x - bs.lowpass(x, 5)
    x = bs.lowpass(x, 3)
    t = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.6 * (0.55 + 0.45 * np.sin(2 * np.pi * 13 * t) ** 2)
    return (x * env * 0.5).astype(np.float32)


def trimmed(kind, dur, seed=3, fade=0.4):
    snd = bs.sfx(kind, np.random.default_rng(seed))[:int(dur * SR)]
    return snd * bs.env_ar(len(snd), fade, fade)


def credit(fname, what):
    c = bs.credit(fname)
    return (c + " · " + what) if c else what


# ----------------------------------------------------------------------------- Part 3: the ad, re-created

AD = [[("COMELY", "oldst_b"), ("WIDOW", "oldst_b"), ("who", "oldst"), ("owns", "oldst"), ("a", "oldst"),
       ("large", "oldst")],
      "farm in one of the finest districts",
      "in La Porte County, Indiana, desires",
      "to make the acquaintance of a gentle-",
      "man equally well provided, with view",
      "of joining fortunes. No replies by let-",
      "ter considered unless sender is will-",
      "ing to follow answer with personal visit.",
      "Triflers need not apply."]
PW, PH = 1400, 2300
COL = (270, 1130)
AD_TOP = 420


def build_page():
    page = bs.aged_paper(PW, PH, seed=21)
    d = ImageDraw.Draw(page)
    rng = np.random.default_rng(5)
    for x in (250, 1150):
        d.line((x, 40, x, PH - 40), fill=INKC + (140,), width=2)

    def ads(x0, x1, y, y_end):
        while y < y_end - 60:
            bh = int(min(rng.integers(150, 300), y_end - y))
            d.rectangle((x0, y, x0 + int((x1 - x0) * rng.uniform(0.5, 0.95)), y + 22), fill=(52, 38, 26, 215))
            bs.newsprint(d, x0, y + 34, x1, y + bh - 14, rng)
            y += bh + 16
            d.line((x0 + 30, y - 8, x1 - 30, y - 8), fill=INKC + (110,), width=1)
    ads(40, 232, 70, PH - 60)
    ads(1168, 1360, 40, PH - 60)
    ads(COL[0], COL[1], 60, AD_TOP - 40)
    # the column head
    head = T("PERSONAL.", "oldst_b", 78, INKC, tracking=8)
    page.alpha_composite(head, ((COL[0] + COL[1]) // 2 - head.width // 2, AD_TOP))
    d.line((COL[0], AD_TOP + 112, COL[1], AD_TOP + 112), fill=INKC + (230,), width=4)
    d.line((COL[0], AD_TOP + 122, COL[1], AD_TOP + 122), fill=INKC + (230,), width=1)
    # the ad, set like a 1905 classified: justified, hyphenated
    lines = []
    for ln in AD:
        lines.append(ln if isinstance(ln, list) else [(w, "oldst") for w in ln.split()])
    colw = COL[1] - COL[0]
    size = 52
    while True:
        widest = max(sum(C.font(k, size).getlength(w) for w, k in ln) + C.font("oldst", size).getlength(" ") *
                     (len(ln) - 1) for ln in lines[:-1])
        if widest <= colw - 4:
            break
        size -= 1
    space = C.font("oldst", size).getlength(" ")
    lh = int(size * 1.34)
    ink = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    di = ImageDraw.Draw(ink)
    boxes = []                 # per line: [(word, (x0, y0, x1, y1))]
    y = AD_TOP + 150
    for i, ln in enumerate(lines):
        ws = [C.font(k, size).getlength(w) for w, k in ln]
        gap = space if i == len(lines) - 1 else (colw - sum(ws)) / max(1, len(ln) - 1)
        x = COL[0]
        row = []
        for (w, k), ww in zip(ln, ws):
            f = C.font(k, size)
            di.text((x, y), w, font=f, fill=INKC + (240,))
            l, tp, r, b = f.getbbox(w)
            row.append((w, (x + l, y + tp, x + r, y + f.getmetrics()[0])))
            x += ww + gap
        boxes.append(row)
        y += lh
    ink = ink.filter(ImageFilter.GaussianBlur(0.55))
    # worn ink: a little uneven
    a = np.asarray(ink.getchannel("A"), np.float32)
    n = np.asarray(bs._noise_tex(PW, PH, 3, 11, 0.8), np.float32) / 255.0
    ink.putalpha(Image.fromarray(np.clip(a * (0.78 + 0.3 * n), 0, 255).astype(np.uint8), "L"))
    page.alpha_composite(ink)
    d.line(((COL[0] + COL[1]) // 2 - 120, y + 20, (COL[0] + COL[1]) // 2 + 120, y + 20), fill=INKC + (160,), width=2)
    ads(COL[0], COL[1], y + 60, PH - 60)
    return page, boxes


def phrase_box(boxes, line, i0, i1):
    ws = boxes[line][i0:i1 + 1]
    return (ws[0][1][0], min(b[1][1] for b in ws), ws[-1][1][2], max(b[1][3] for b in ws))


class PageCam:
    def __init__(self, keys, ys=760):
        self.keys, self.ys = keys, ys

    def at(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1:]
        for a, b in zip(ks, ks[1:]):
            if t <= b[0]:
                u = ease((t - a[0]) / max(1e-6, b[0] - a[0]))
                return tuple(a[i] + (b[i] - a[i]) * u for i in (1, 2, 3))
        return ks[-1][1:]

    def draw(self, f, page, t):
        s, cx, cy = self.at(t)
        bw, bh = W / s, H / s
        x0 = min(max(cx - (W / 2) / s, 0), page.width - bw)
        y0 = min(max(cy - self.ys / s, 0), page.height - bh)
        f.alpha_composite(page.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + bw, y0 + bh)))
        return lambda px, py: ((px - x0) * s, (py - y0) * s), s


def build_map():
    MW, MH = 1400, 2000
    m = bs.aged_paper(MW, MH, seed=9)
    k, lon0, lat0 = 84.0, -91.6, 43.6
    cl = math.cos(math.radians(43.5))

    def P(lon, lat):
        return (MW / 2 + (lon - lon0) * k * cl, MH / 2 - (lat - lat0) * k)

    S = 2
    big = Image.new("RGBA", (MW * S, MH * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)

    def rings(geom):
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for ring in poly:
                yield [(P(x, y)[0] * S, P(x, y)[1] * S) for x, y in ring]

    lakes = json.load(open(os.path.join(GEO, "ne_50m_lakes.geojson")))
    water = Image.new("L", (MW * S, MH * S), 0)
    dw = ImageDraw.Draw(water)
    for ft in lakes["features"]:
        if ft["properties"].get("name") in ("Lake Michigan", "Lake Superior", "Lake Huron", "Lake Erie",
                                            "Lake of the Woods", "Lake Winnebago", "Lake Saint Clair",
                                            "Lake Nipigon", "Lake Winnipeg"):
            for r in rings(ft["geometry"]):
                dw.polygon(r, fill=255)
    st = json.load(open(os.path.join(GEO, "ne_50m_admin_1_states_provinces_lakes.geojson")))
    for ft in st["features"]:
        if ft["properties"].get("admin") not in ("United States of America", "Canada"):
            continue
        for r in rings(ft["geometry"]):
            d.line(r + r[:1], fill=INKC + (150,), width=2 * S)
    big = big.resize((MW, MH), Image.LANCZOS)
    water = water.resize((MW, MH), Image.LANCZOS)
    # lakes: a darker wash with fine engraved lines
    wa = np.asarray(water, np.float32) / 255.0
    hatch = ((np.arange(MH)[:, None] % 9) < 2).astype(np.float32) * 0.5 + 0.5
    tint = Image.new("RGBA", (MW, MH), (96, 84, 66, 0))
    tint.putalpha(Image.fromarray((wa * hatch * 105).astype(np.uint8), "L"))
    m.alpha_composite(tint)
    m.alpha_composite(big)
    labels = [("S. DAK.", -99.4, 44.0), ("N. DAK.", -99.2, 47.3), ("MINN.", -94.3, 46.4), ("IOWA", -93.4, 42.05),
              ("NEBR.", -98.8, 41.55), ("WIS.", -89.9, 44.6), ("ILL.", -89.3, 40.2), ("IND.", -86.2, 39.75),
              ("MICH.", -84.8, 43.2), ("MO.", -92.5, 38.4)]
    for name, lon, lat in labels:
        img = T(name, "fell_sc", 40, INKC + (150,), tracking=6)
        x, y = P(lon, lat)
        m.alpha_composite(img, (int(x - img.width / 2), int(y - img.height / 2)))
    for name, lon, lat, rot in (("Lake Michigan", -87.05, 43.6, 72), ("Lake Superior", -87.6, 47.55, 8)):
        img = T(name, "fell_it", 30, INKC + (140,)).rotate(rot, expand=True, resample=Image.BICUBIC)
        x, y = P(lon, lat)
        m.alpha_composite(img, (int(x - img.width / 2), int(y - img.height / 2)))
    return m, P


def envelope(w=74):
    S = 3
    h = int(w * 0.64)
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((2 * S, 2 * S, (w - 2) * S, (h - 2) * S), fill=(244, 234, 214, 255), outline=INKC + (255,), width=3 * S)
    d.line([(2 * S, 2 * S), (w * S / 2, h * S * 0.58), ((w - 2) * S, 2 * S)], fill=INKC + (255,), width=3 * S)
    return img.resize((w, h), Image.LANCZOS)


def dot(r, color):
    S = 4
    img = Image.new("RGBA", (r * 2 * S + 8, r * 2 * S + 8), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((4, 4, 4 + r * 2 * S, 4 + r * 2 * S), fill=tuple(color) + (255,),
                                outline=(244, 234, 214, 255), width=S * 3)
    return img.resize((img.width // S, img.height // S), Image.LANCZOS)


def scribble(d, x0, x1, y, rng, a=95):
    """A line of loose handwriting too small to read: looping strokes, word by word."""
    x = x0
    while x < x1 - 60:
        letters = int(rng.integers(3, 9))
        pts = []
        for i in range(letters):
            tall = rng.random() < 0.22
            deep = (not tall) and rng.random() < 0.12
            ry = (19 if tall else 9) * rng.uniform(0.8, 1.15)
            for j in range(10):
                ph = 2 * math.pi * j / 10
                px = x + (i + j / 10) * 15 - 5.5 * math.sin(ph)
                py = y - ry * (0.5 - 0.5 * math.cos(ph)) + (12 * math.sin(ph / 2) if deep else 0)
                pts.append((px, py))
        if pts[-1][0] > x1:
            break
        d.line(pts, fill=INKC + (a,), width=3, joint="curve")
        x = pts[-1][0] + int(rng.integers(18, 34))


_cache = {}


def band(y0=1060, y1=1260, a=190):
    if "band" not in _cache:
        y = np.arange(H, dtype=np.float32)[:, None]
        g = np.clip((y - y0) / (y1 - y0), 0, 1) ** 1.2 * a
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        img.putalpha(Image.fromarray(np.repeat(g, W, axis=1).astype(np.uint8), "L"))
        _cache["band"] = img
    return _cache["band"]


def red_title(f, text, size, t, at, color=(250, 70, 56)):
    key = ("rt", text, size)
    if key not in _cache:
        img = fitT(text, "bask", size, color, max_w=C.CW, min_size=int(size * 0.5))
        g = glow(img, (0, 0, 0), radius=22, strength=1.0)
        g2 = glow(img, (150, 0, 0), radius=34, strength=0.6)
        out = Image.new("RGBA", (max(g.width, g2.width), max(g.height, g2.height)), (0, 0, 0, 0))
        out.alpha_composite(g2, ((out.width - g2.width) // 2, (out.height - g2.height) // 2))
        out.alpha_composite(g, ((out.width - g.width) // 2, (out.height - g.height) // 2))
        _cache[key] = out
    dx = int(np.random.default_rng(int(t * 1000)).normal(0, 6)) if 0 <= t - at < 0.25 else 0
    f.alpha_composite(C.alpha(band(), appear(t, at - 0.2, 0.2)))
    paste(f, _cache[key], W / 2 + dx, 1205, appear(t, at - 0.08, 0.1))


def build_belle3(R):
    t_ad, t_dis = R.at("Then one"), R.at("disappeared.")
    t_her = R.at("Her ad read:")
    t_com, t_owns, t_la = R.at("comely"), R.at("owns"), R.at("LaPorte County.")
    t_tri = R.at("Triflers")
    t_and, t_hel = R.at("Andrew"), R.at("Helgelien,")
    t_wrote, t_back = R.at("wrote back."), R.end("wrote back.")
    t_lett = R.at("Her letters")
    t_come = R.at("come prepared")
    t_in = R.at("In January")
    t_jan, t_nearly = R.at("January"), R.at("nearly")
    t_and2 = R.at("and was never")
    t_never = R.at("never seen")
    t_dbl = R.at("Double-tap")
    c1 = (t_ad - 0.14)                         # cuts, in the pauses
    c2 = (R.end("disappeared.") + t_her) / 2
    c3 = (R.end("apply.") + t_and) / 2
    c4 = (t_back + t_lett) / 2
    c5 = (R.end("forever.") + t_in) / 2
    c6 = t_and2 - 0.07
    c7 = (R.end("again.") + t_dbl) / 2

    shared = {}

    def prep_page(ctx):
        if "page" not in shared:
            shared["page"], shared["boxes"] = build_page()
        ctx.update(shared)
        b = shared["boxes"]
        ctx["ul"] = [(phrase_box(b, 0, 0, 1), t_com, 0.45), (phrase_box(b, 0, 3, 5), t_owns, 0.3),
                     (phrase_box(b, 1, 0, 0), t_owns + 0.3, 0.18), (phrase_box(b, 2, 1, 3), t_la, 0.5)]
        ctx["trif"] = phrase_box(b, 8, 0, 3)
        ctx["title"] = None

    tri = None

    def cam():
        b = shared["boxes"]
        x0, y0, x1, y1 = phrase_box(b, 8, 0, 3)
        hx = (x0 + x1) / 2
        ty = (y0 + y1) / 2
        top = b[0][0][1][1]
        return PageCam([(0.0, 1.12, 700, AD_TOP + 350 / 1.12), (c1, 1.08, 700, AD_TOP + 345 / 1.08),
                        (c2, 1.04, 700, AD_TOP + 320 / 1.04), (t_tri - 0.55, 1.1, 700, AD_TOP + 330 / 1.1),
                        (t_tri + 0.1, 1.72, hx, ty), (c3, 1.82, hx, ty)])

    def draw_page(f, u, t, ctx):
        if "cam" not in ctx:
            ctx["cam"] = cam()
        to, s = ctx["cam"].draw(f, ctx["page"], t)
        for (x0, y0, x1, y1), at, dur in ctx["ul"]:
            if t >= at:
                a, b2 = to(x0, y1 + 9)
                c, _ = to(x1, y1 + 9)
                pencil(f, a, c, b2, (t - at) / dur, width=max(5, int(4.5 * s)), seed=int(at * 10) % 7)
        x0, y0, x1, y1 = ctx["trif"]
        if t >= t_tri:
            (a, b2), (c, d2) = to(x0, y0), to(x1, y1)
            ww, hh = c - a, d2 - b2
            img = bs.red_circle((int(ww + 70), int(hh + 80)), (t - t_tri) / 0.75)
            f.alpha_composite(img, (int((a + c) / 2 - img.width / 2), int((b2 + d2) / 2 - img.height / 2)))
        bs.shade(f)
        if t < c1:
            f.alpha_composite(band())
            bs.title(f, "THE AD THAT LURED THEM", "bask", 84, BONE, 1205, glow=(0, 0, 0), alpha=1.0)
        bs.credit_line(f, "Re-created from the text of her ad")

    def prep_collage(ctx):
        ctx["im"] = bs.photo("belle-11.jpg", "sepia", inset=0.02)

    def draw_collage(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c2 - c1, z=(1.32, 1.46), f0=(0.63, 0.46), f1=(0.67, 0.43))
        bs.shade(f)
        if t >= t_dis - 0.05:
            red_title(f, "ONE OF THEM VANISHED", 92, t, t_dis)
        bs.credit_line(f, credit("belle-11.jpg", "photos from the case, 1908"))

    def prep_map(ctx):
        ctx["map"], ctx["P"] = build_map()
        ctx["env"] = envelope()
        ctx["dot"] = dot(13, BLOOD)
        ctx["ab"] = glow(T("ABERDEEN, S.D.", "oldst_b", 40, INKC), (244, 234, 214), radius=10, strength=0.9)
        ctx["lp"] = glow(T("LAPORTE, IND.", "oldst_b", 40, INKC), (244, 234, 214), radius=10, strength=0.9)

    def draw_map(f, u, t, ctx):
        P = ctx["P"]
        a0, b0 = P(-98.49, 45.46)
        a1, b1 = P(-86.72, 41.61)
        cam = PageCam([(c3, 1.0, (a0 + a1) / 2, (b0 + b1) / 2 + 40), (c4, 1.07, (a0 + a1) / 2 + 10, (b0 + b1) / 2 + 30)],
                      ys=700)
        to, s = cam.draw(f, ctx["map"], t)
        A, B = to(a0, b0), to(a1, b1)
        ctrl = ((A[0] + B[0]) / 2, min(A[1], B[1]) - 150)

        def bez(q):
            return ((1 - q) ** 2 * A[0] + 2 * (1 - q) * q * ctrl[0] + q * q * B[0],
                    (1 - q) ** 2 * A[1] + 2 * (1 - q) * q * ctrl[1] + q * q * B[1])
        r0, r1 = t_hel + 0.2, t_back + 0.05
        prog = ease((t - r0) / (r1 - r0)) if t >= r0 else 0.0
        if prog > 0:
            S = 2
            bx0 = int(min(A[0], B[0], ctrl[0]) - 20)
            by0 = int(min(A[1], B[1], ctrl[1]) - 20)
            bw = int(max(A[0], B[0], ctrl[0]) + 20) - bx0
            bh = int(max(A[1], B[1], ctrl[1]) + 20) - by0
            lay = Image.new("RGBA", (bw * S, bh * S), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            n = 60
            for i in range(n):
                q0, q1 = i / n, (i + 0.55) / n
                if q0 > prog:
                    break
                p0, p1 = bez(q0), bez(min(q1, prog))
                d.line([((p0[0] - bx0) * S, (p0[1] - by0) * S), ((p1[0] - bx0) * S, (p1[1] - by0) * S)],
                       fill=BLOOD + (235,), width=7 * S)
            f.alpha_composite(lay.resize((bw, bh), Image.LANCZOS), (bx0, by0))
        for (x, y) in (A, B):
            paste(f, ctx["dot"], x, y)
        paste(f, ctx["ab"], min(max(A[0], 70 + ctx["ab"].width / 2), 1000 - ctx["ab"].width / 2), A[1] - 52)
        paste(f, ctx["lp"], min(max(B[0], 70 + ctx["lp"].width / 2), 1000 - ctx["lp"].width / 2), B[1] + 50)
        if 0 < prog < 1:
            x, y = bez(prog)
            paste(f, ctx["env"], x, y - 4)
        if t >= r1:
            k = (t - r1) / 0.6
            if k < 1:
                paste(f, C.ring(16 + 50 * k, 5, BLOOD, 1 - k), B[0], B[1])
        bs.shade(f)
        bs.title(f, "ANDREW HELGELIEN", "bask", 88, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_and - 0.05, 0.2))
        bs.credit_line(f, "Map: Natural Earth")

    def prep_letter(ctx):
        ctx["face"] = bs.emerging("belle-08.jpg", "sepia", scale=3.0, blur=0.5)
        card = bs.aged_paper(880, 500, seed=17)
        d = ImageDraw.Draw(card)
        rng = np.random.default_rng(3)
        for y in (70, 122):
            scribble(d, 60, 820, y, rng)
        ctx["card"] = card
        f1 = C.font("fell_it", 88)
        words1, words2 = ["“…come", "prepared"], ["to", "stay", "forever.”"]
        ctx["words"] = []
        times = [R.at("come", t_come - 0.01), R.at("prepared", t_come), R.at("to stay"), R.at("stay"), R.at("forever.")]
        k = 0
        for row, ws in ((190, words1), (300, words2)):
            total = sum(f1.getlength(w) for w in ws) + f1.getlength(" ") * (len(ws) - 1)
            x = (880 - total) / 2
            for w in ws:
                ctx["words"].append((T(w, "fell_it", 88, INKC), x, row, times[k]))
                x += f1.getlength(w) + f1.getlength(" ")
                k += 1
        ctx["attr"] = T("— Belle Gunness, in a letter to Andrew Helgelien", "semi", 26, INKC + (200,))
        ctx["lab"] = glow(T("FROM HER LETTERS", "bold", 34, BONE, tracking=4), (0, 0, 0), radius=14, strength=0.9)

    def draw_letter(f, u, t, ctx):
        bs.float_in(f, ctx["face"], u, c5 - c4, w=(1150, 1260), focus=((0.41, 0.38), (0.41, 0.40)), at=(540, 520))
        dim(f, 0.25)
        bs.shade(f)
        card = ctx["card"].copy()
        for img, x, y, at in ctx["words"]:
            a = appear(t, at - 0.04, 0.18)
            if a > 0:
                card.alpha_composite(C.alpha(img, a), (int(x), int(y)))
        card.alpha_composite(ctx["attr"], (880 - ctx["attr"].width - 50, 420))
        rot = card.rotate(2.2, expand=True, resample=Image.BICUBIC)
        k = appear(t, c4 + 0.05, 0.4)
        paste(f, rot, W / 2, 1010 + 60 * (1 - k), k)
        paste(f, ctx["lab"], W / 2, 715, appear(t, c4 + 0.25, 0.3))

    def prep_farm(ctx):
        ctx["im"] = bs.photo("belle-farm-07.jpg", "sepia", inset=0.05)

    def draw_farm(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c6 - c5, z=(1.0, 1.12), f0=(0.42, 0.56), f1=(0.5, 0.55))
        bs.shade(f)
        typed(f, "JANUARY 1908", t, t_jan, 330)
        typed(f, "NEARLY $3,000", t, t_nearly, 440, size=64, rate=0.05)
        bs.credit_line(f, credit("belle-farm-07.jpg", "the Gunness farm, 1908"))

    def prep_pen(ctx):
        ctx["im"] = bs.photo("belle-farm-03.jpg", "sepia", inset=0.05)

    def draw_pen(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c7 - c6, z=(1.12, 1.24), f0=(0.6, 0.5), f1=(0.62, 0.47))
        bs.shade(f)
        if t >= t_never - 0.08:
            red_title(f, "NEVER SEEN ALIVE AGAIN", 96, t, t_never)
        bs.credit_line(f, credit("belle-farm-03.jpg", "the farm's hog pen, 1908"))

    def prep_end(ctx):
        ctx["im"] = bs.photo("belle-farm-13.jpg", "sepia", inset=0.05)
        ctx["cta"] = C.DoubleTap("FOR PART 4", "the clue that didn't fit")

    def draw_end(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, R.dur - c7, z=(1.05, 1.14), f0=(0.42, 0.62), f1=(0.47, 0.64))
        bs.embers(f, u, 0.55)
        bs.shade(f)
        ctx["cta"].draw(f, u)
        bs.credit_line(f, credit("belle-farm-13.jpg", "the farm after the fire, 1908"))

    scenes = [C.Scene(0.0, c1, draw_page, prep_page), C.Scene(c1, c2, draw_collage, prep_collage),
              C.Scene(c2, c3, draw_page, prep_page), C.Scene(c3, c4, draw_map, prep_map),
              C.Scene(c4, c5, draw_letter, prep_letter), C.Scene(c5, c6, draw_farm, prep_farm),
              C.Scene(c6, c7, draw_pen, prep_pen), C.Scene(c7, R.dur + 1, draw_end, prep_end)]
    film = C.Film(R, scenes, flashes=[(c6, 0.32)], label=label_fn("BELLE GUNNESS · PART 3", c3))
    ev = [("whoosh", 0.1, 1.0), (scratch(0.45, 1), t_com, 0.55), (scratch(0.3, 2), t_owns, 0.5),
          (scratch(0.45, 3), t_la, 0.55), ("hit", t_dis, 0.9), ("whoosh", c2, 0.8), (scratch(0.8, 4), t_tri, 0.6),
          ("hit", t_tri + 0.75, 0.6), ("whoosh", c3, 0.9), ("pop", t_back + 0.05, 0.9), ("whoosh", c4, 0.7),
          ("heartbeat", R.at("forever.") - 0.1, 1.0), ("type", t_jan, 1.0), ("type", t_nearly, 1.0),
          ("thunder", c6, 0.8), ("heartbeat", t_never, 1.0),
          ("pop", c7 + 0.12, 0.9), ("pop", c7 + 0.42, 0.9), ("hit", c7 + 0.5, 0.7)]
    return film, ev, "lullaby", "Belle Gunness, Part 3: The Newspaper Ad"


# ----------------------------------------------------------------------------- Part 4: the woman in the fire

def card_base(w, h, title, seed):
    card = bs.aged_paper(w, h, seed=seed)
    d = ImageDraw.Draw(card)
    head = fitT(title, "bask", 88, INKC, max_w=w - 112, min_size=50)
    card.alpha_composite(head, (56, 44))
    d.line((56, 44 + head.height + 26, w - 56, 44 + head.height + 26), fill=INKC + (200,), width=3)
    d.line((56, 44 + head.height + 34, w - 56, 44 + head.height + 34), fill=INKC + (200,), width=1)
    return card, 44 + head.height + 70


def type_lines(card, lines, t, y0, size=54, rate=0.022):
    """lines: [(text, at)] typed onto the card from their times, in a size that fits the card."""
    while size > 30 and max(C.font("typew", size).getlength(x) for x, _ in lines) > card.width - 100:
        size -= 2
    lh = int(size * 1.42)
    y = y0
    for text, at in lines:
        if t >= at:
            n = int(min(len(text), (t - at) / rate + 1))
            card.alpha_composite(T(text[:n], "typew", size, INKC), (52, int(y)))
        y += lh


def build_belle4(R):
    t_really = R.at("really")
    t_or = R.at("Or just")
    t_a = R.at("A doctor")
    t_doc, t_short, t_far = R.at("doctor"), R.at("shorter,"), R.at("far lighter.")
    t_it = R.at('"It')
    t_but = R.at("But her")
    t_dent, t_gold, t_cor = R.at("dentist"), R.at("gold"), R.at("coroner")
    t_work = R.at("work from")
    t_two, t_cant = R.at("Two"), R.at("can't")
    t_dbl = R.at("Double-tap")
    c1 = (R.end("Gunness?") + t_or) / 2
    c2 = (R.end("told?") + t_a) / 2
    c3 = (R.end("lighter.") + t_it) / 2
    c4 = (R.end('Gunness."', t_it) + t_but) / 2
    c5 = (R.end("Belle.", t_cor) + t_two) / 2
    c6 = (R.end("true.") + t_dbl) / 2

    def prep_fire(ctx):
        ctx["im"] = bs.photo("belle-farm-13.jpg", "sepia", inset=0.05)
        q = T("?", "bask", 560, (222, 34, 30))
        ctx["q"] = glow(q, (120, 0, 0), radius=40, strength=0.9)

    def draw_fire(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c1, z=(1.1, 1.2), f0=(0.42, 0.62), f1=(0.46, 0.64))
        bs.embers(f, u, 1.0)
        bs.shade(f)
        if t >= t_really - 0.1:
            s = 1.25 - 0.25 * appear(t, t_really - 0.1, 0.18)
            paste(f, scaled(ctx["q"], s), W / 2 + 40, 690, appear(t, t_really - 0.1, 0.18) * 0.92)
        bs.title(f, "THE WOMAN IN THE FIRE", "bask", 90, BONE, 1205, glow=(0, 0, 0), alpha=1.0)
        bs.credit_line(f, credit("belle-farm-13.jpg", "the farm after the fire, 1908"))

    def prep_card(ctx):
        im = bs.photo("belle-14.jpg", "sepia")
        bg = bs.photo("belle-farm-14.jpg", "sepia", inset=0.05).filter(ImageFilter.GaussianBlur(7))
        ctx["bg"] = bg
        hgt = 760
        pc = im.resize((int(im.width * hgt / im.height), hgt), Image.LANCZOS)
        fr = Image.new("RGBA", (pc.width + 24, pc.height + 24), (236, 228, 210, 255))
        fr.alpha_composite(pc, (12, 12))
        sh = Image.new("RGBA", (fr.width + 80, fr.height + 80), (0, 0, 0, 0))
        m = Image.new("L", sh.size, 0)
        ImageDraw.Draw(m).rectangle((40, 50, 40 + fr.width, 50 + fr.height), fill=170)
        sh.putalpha(m.filter(ImageFilter.GaussianBlur(18)))
        sh.alpha_composite(fr, (40, 40))
        ctx["pc"] = sh.rotate(-3, expand=True, resample=Image.BICUBIC)
        ctx["lab"] = glow(T("A 1908 POSTCARD", "bold", 34, BONE, tracking=4), (0, 0, 0), radius=14, strength=0.9)

    def draw_card(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c2 - c1, z=(1.05, 1.1))
        dim(f, 0.35)
        z = 0.97 + 0.05 * min(1.0, u / (c2 - c1))
        paste(f, scaled(ctx["pc"], z), W / 2, 705, appear(u, 0.0, 0.15))
        bs.shade(f)
        paste(f, ctx["lab"], W / 2, 1222, appear(u, 0.2, 0.25))
        bs.credit_line(f, credit("belle-14.jpg", "“the Woman Bluebeard” postcard, 1908"))

    def prep_body(ctx):
        ctx["im"] = bs.photo("belle-farm-15.jpg", "sepia", inset=0.05)
        ctx["card"], ctx["y0"] = card_base(880, 470, "THE BODY", 41)
        ctx["who"] = T("Dr. Harry Long, who knew her", "semi", 32, INKC + (210,))
        q1 = T("“It is not that", "bask", 92, BONE)
        q2 = T("of Mrs. Gunness.”", "bask", 92, BONE)
        ctx["q"] = [glow(q1, (0, 0, 0), radius=22, strength=0.9), glow(q2, (0, 0, 0), radius=22, strength=0.9)]
        ctx["qa"] = glow(T("— DR. HARRY LONG, 1908", "bold", 36, SEPIA, tracking=3), (0, 0, 0), radius=14,
                         strength=0.9)

    def bg_cellar(f, t, ctx):
        bs.kenburns(f, ctx["im"], t - c2, c4 - c2, z=(1.05, 1.2), f0=(0.5, 0.42), f1=(0.53, 0.46))
        dim(f, 0.3)
        bs.shade(f)

    def draw_body(f, u, t, ctx):
        bg_cellar(f, t, ctx)
        card = ctx["card"].copy()
        type_lines(card, [("— Nearly 5 inches shorter", t_short - 0.3), ("— Far lighter than Belle", t_far - 0.1)],
                   t, ctx["y0"])
        if t >= t_doc:
            card.alpha_composite(C.alpha(ctx["who"], appear(t, t_doc, 0.3)), (56, card.height - 74))
        k = appear(t, c2 + 0.05, 0.35)
        paste(f, card, W / 2, 760 + 70 * (1 - k), k)
        bs.credit_line(f, credit("belle-farm-15.jpg", "viewing the cellar, 1908"))

    def draw_quote(f, u, t, ctx):
        bg_cellar(f, t, ctx)
        dim(f, 0.25)
        # the quote, a line at a time with the narrator
        a1 = appear(t, t_it - 0.05, 0.25)
        a2 = appear(t, R.at("of Mrs.") - 0.05, 0.25)
        paste(f, ctx["q"][0], W / 2, 640, a1)
        paste(f, ctx["q"][1], W / 2, 770, a2)
        paste(f, ctx["qa"], W / 2, 905, appear(t, R.at('Gunness."', t_it) - 0.1, 0.3))
        bs.credit_line(f, credit("belle-farm-15.jpg", "viewing the cellar, 1908"))

    def prep_teeth(ctx):
        ctx["im"] = bs.photo("belle-farm-10.jpg", "sepia", inset=0.05)
        ctx["card"], ctx["y0"] = card_base(880, 470, "THE TEETH", 43)

    def draw_teeth(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c5 - c4, z=(1.0, 1.12), f0=(0.45, 0.55), f1=(0.52, 0.52))
        dim(f, 0.3)
        bs.shade(f)
        card = ctx["card"].copy()
        type_lines(card, [("— Her dentist: the gold dental", t_dent - 0.1), ("  work in the ashes was hers", t_work),
                          ("— The coroner: it was Belle", t_cor - 0.1)], t, ctx["y0"])
        k = appear(t, c4 + 0.05, 0.35)
        paste(f, card, W / 2, 760 + 70 * (1 - k), k)
        bs.credit_line(f, credit("belle-farm-10.jpg", "reviewing remains at the farm, 1908"))

    def prep_split(ctx):
        im = bs.photo("belle-07.jpg", "sepia")
        im = im.crop((0, 0, int(im.width * 0.83), im.height))
        w = 860
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
        rng = np.random.default_rng(12)
        ys = list(range(0, im.height + 40, 38))
        crack = [(w / 2 + 18 * math.sin(y * 0.021) + rng.uniform(-14, 14), y) for y in ys]
        left = Image.new("L", im.size, 0)
        ImageDraw.Draw(left).polygon([(0, 0)] + crack + [(0, im.height)], fill=255)
        right = Image.new("L", im.size, 255)
        right.paste(0, (0, 0), left)
        L_, R_ = im.copy(), im.copy()
        L_.putalpha(left)
        R_.putalpha(right)
        red = Image.new("RGBA", im.size, (150, 10, 10, 70))
        red.putalpha(Image.fromarray((np.asarray(left, np.float32) * 0.3).astype(np.uint8), "L"))
        ctx.update(L=L_, R=R_, red=red, crack=crack, size=im.size)
        ctx["lb1"] = glow(T("THE BODY", "bold", 36, BONE, tracking=4), (0, 0, 0), radius=14, strength=0.9)
        ctx["lb2"] = glow(T("THE TEETH", "bold", 36, BONE, tracking=4), (0, 0, 0), radius=14, strength=0.9)
        ctx["v1"] = glow(T("NOT HER", "bask", 84, RED), (120, 0, 0), radius=24, strength=0.85)
        ctx["v2"] = glow(T("HER", "bask", 84, BONE), (0, 0, 0), radius=24, strength=0.85)

    def draw_split(f, u, t, ctx):
        w, h = ctx["size"]
        k = ease_out((t - t_cant) / 0.28) if t >= t_cant else 0.0
        gap = 10 + 46 * k
        shake = np.random.default_rng(int(t * 1000)).normal(0, 9, 2) if 0 <= t - t_cant < 0.22 else (0, 0)
        x0, y0 = W / 2 - w / 2 + shake[0], 700 - h / 2 + shake[1]
        f.alpha_composite(ctx["L"], (int(x0 - gap / 2), int(y0)))
        f.alpha_composite(ctx["R"], (int(x0 + gap / 2), int(y0)))
        if t >= t_two:
            f.alpha_composite(C.alpha(ctx["red"], appear(t, t_two, 0.4)), (int(x0 - gap / 2), int(y0)))
        bs.shade(f)
        a1, a2 = appear(t, c5 + 0.1, 0.3), appear(t, c5 + 0.35, 0.3)
        paste(f, ctx["lb1"], 290, 345, a1)
        paste(f, ctx["v1"], 290, 1035, a1)
        paste(f, ctx["lb2"], 790, 345, a2)
        paste(f, ctx["v2"], 790, 1035, a2)
        bs.title(f, "TWO STORIES", "bask", 104, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_two - 0.05, 0.2))

    def prep_end(ctx):
        ctx["face"] = bs.emerging("belle-08.jpg", "sepia", scale=3.0, blur=0.5)
        ctx["cta"] = C.DoubleTap("FOR PART 5", "Los Angeles, 1931")

    def draw_end(f, u, t, ctx):
        bs.float_in(f, ctx["face"], u, R.dur - c6, w=(1250, 1330), focus=((0.41, 0.40), (0.41, 0.41)), at=(540, 470))
        dim(f, 0.2)
        bs.shade(f)
        ctx["cta"].draw(f, u)

    scenes = [C.Scene(0.0, c1, draw_fire, prep_fire), C.Scene(c1, c2, draw_card, prep_card),
              C.Scene(c2, c3, draw_body, prep_body), C.Scene(c3, c4, draw_quote, None),
              C.Scene(c4, c5, draw_teeth, prep_teeth), C.Scene(c5, c6, draw_split, prep_split),
              C.Scene(c6, R.dur + 1, draw_end, prep_end)]
    scenes[3].prep = lambda ctx: ctx.update(scenes[2].ctx) if scenes[2].ready else (prep_body(ctx))
    film = C.Film(R, scenes, flashes=[(0.3, 0.32), (c5, 0.22)], label=label_fn("BELLE GUNNESS · PART 4", c2))
    ev = [("thunder", 0.28, 0.9), (trimmed("fire", c1 + 0.4), 0.0, 0.5, "bed"), ("hit", t_really, 0.8),
          ("whoosh", c1, 0.7), ("whoosh", c2, 0.7), ("type", t_short - 0.3, 0.9), ("type", t_far - 0.1, 0.9),
          ("heartbeat", t_it - 0.05, 0.9), ("whoosh", c4, 0.7), ("type", t_dent - 0.1, 0.9), ("type", t_work, 0.9),
          ("type", t_cor - 0.1, 0.9), ("thud", c5, 0.7), ("hit", t_cant, 1.0),
          ("pop", c6 + 0.12, 0.9), ("pop", c6 + 0.42, 0.9), ("hit", c6 + 0.5, 0.7)]
    return film, ev, "lullaby", "Belle Gunness, Part 4: Was the Woman in the Fire Belle?"



# ----------------------------------------------------------------------------- Part 5: Los Angeles, 1931

def build_us_map():
    MW, MH = 2000, 2100
    k, lon0, lat0 = 55.0, -101.5, 38.0
    cl = math.cos(math.radians(38.0))

    def P(lon, lat):
        return (MW / 2 + (lon - lon0) * k * cl, MH / 2 - (lat - lat0) * k)

    m = bs.aged_paper(MW, MH, seed=19)
    S = 2

    def rings(geom):
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for ring in poly:
                yield [(P(x, y)[0] * S, P(x, y)[1] * S) for x, y in ring]

    def near(geom):
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        pts = [p for poly in polys for ring in poly for p in ring]
        return max(p[0] for p in pts) > -130 and min(p[0] for p in pts) < -70 and \
            max(p[1] for p in pts) > 15 and min(p[1] for p in pts) < 60

    land = Image.new("L", (MW * S, MH * S), 0)
    dl = ImageDraw.Draw(land)
    for ft in json.load(open(os.path.join(GEO, "ne_50m_land.geojson")))["features"]:
        if near(ft["geometry"]):
            g = ft["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                dl.polygon([(P(x, y)[0] * S, P(x, y)[1] * S) for x, y in poly[0]], fill=255)
    for ft in json.load(open(os.path.join(GEO, "ne_50m_lakes.geojson")))["features"]:
        if ft["properties"].get("name") in ("Lake Michigan", "Lake Superior", "Lake Huron", "Lake Erie",
                                            "Lake Ontario", "Great Salt Lake", "Lake of the Woods"):
            for r in rings(ft["geometry"]):
                dl.polygon(r, fill=0)
    lines = Image.new("RGBA", (MW * S, MH * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lines)
    st = json.load(open(os.path.join(GEO, "ne_50m_admin_1_states_provinces_lakes.geojson")))
    for ft in st["features"]:
        if ft["properties"].get("admin") not in ("United States of America", "Canada") or not near(ft["geometry"]):
            continue
        for r in rings(ft["geometry"]):
            d.line(r + r[:1], fill=INKC + (140,), width=2 * S)
    land = land.resize((MW, MH), Image.LANCZOS)
    lines = lines.resize((MW, MH), Image.LANCZOS)
    wa = 1 - np.asarray(land, np.float32) / 255.0
    hatch = ((np.arange(MH)[:, None] % 9) < 2).astype(np.float32) * 0.5 + 0.5
    tint = Image.new("RGBA", (MW, MH), (96, 84, 66, 0))
    tint.putalpha(Image.fromarray((wa * hatch * 100).astype(np.uint8), "L"))
    m.alpha_composite(tint)
    # the coast, inked
    edge = np.asarray(land.filter(ImageFilter.FIND_EDGES), np.float32)
    coast = Image.new("RGBA", (MW, MH), INKC + (0,))
    coast.putalpha(Image.fromarray(np.clip(edge * 1.6, 0, 200).astype(np.uint8), "L"))
    m.alpha_composite(coast)
    m.alpha_composite(lines)
    labels = [("CALIF.", -119.6, 37.2), ("NEV.", -116.9, 39.4), ("ARIZ.", -111.7, 34.3), ("UTAH", -111.6, 39.4),
              ("COLO.", -105.5, 39.0), ("N. MEX.", -106.1, 34.4), ("WYO.", -107.5, 43.0), ("NEBR.", -99.8, 41.5),
              ("KANS.", -98.4, 38.5), ("OKLA.", -97.4, 35.6), ("TEX.", -99.3, 31.4), ("MO.", -92.5, 38.4),
              ("IOWA", -93.4, 42.05), ("ILL.", -89.4, 39.4), ("ORE.", -120.6, 43.9),
              ("IDAHO", -114.6, 44.0), ("S. DAK.", -100.2, 44.4), ("ARK.", -92.4, 34.9)]
    for name, lon, lat in labels:
        img = T(name, "fell_sc", 40, INKC + (140,), tracking=6)
        x, y = P(lon, lat)
        m.alpha_composite(img, (int(x - img.width / 2), int(y - img.height / 2)))
    img = T("Pacific Ocean", "fell_it", 44, INKC + (150,))
    x, y = P(-124.2, 31.2)
    m.alpha_composite(img, (int(x - img.width / 2), int(y)))
    return m, P


def build_belle5(R):
    t_la, t_esther = R.at("In Los Angeles,"), R.at("Esther")
    t_charged, t_81, t_tb = R.at("was charged"), R.at("eighty-one-year-old"), R.at("tuberculosis")
    t_two, t_swore = R.at("Two people"), R.at("swore")
    t_trunk = R.at("In her trunk")
    t_no, t_proved = R.at("No one"), R.at("proved")
    t_dbl = R.at("Double-tap")
    c1 = (R.end("1931?") + t_la) / 2
    c2 = t_charged - 0.1
    c3 = (R.end("trial.") + t_two) / 2
    c4 = (R.end("Belle.", t_two) + t_trunk) / 2
    c5 = (R.end("Belle's.") + t_no) / 2
    c6 = (R.end("it.", t_no) + t_dbl) / 2
    shared = {}

    def prep_face(ctx):
        if "face" not in shared:
            shared["face"] = bs.emerging("belle-08.jpg", "sepia", scale=3.0, blur=0.5)
        ctx["face"] = shared["face"]

    def d_hook(f, u, t, ctx):
        bs.float_in(f, ctx["face"], u, c1, w=(1420, 1260), focus=((0.41, 0.40), (0.42, 0.42)), at=(540, 640))
        bs.shade(f)
        red_title(f, "ALIVE IN 1931?", 116, t, -0.2)

    def prep_map(ctx):
        if "map" not in shared:
            shared["map"], shared["P"] = build_us_map()
        ctx.update(map=shared["map"], P=shared["P"], dot=dot(13, BLOOD), env=None,
                   lp=glow(T("LAPORTE, IND.", "oldst_b", 40, INKC), (244, 234, 214), radius=10, strength=0.9),
                   la=glow(T("LOS ANGELES, CALIF.", "oldst_b", 40, INKC), (244, 234, 214), radius=10, strength=0.9))

    def route(ctx, to):
        P = ctx["P"]
        A, B = to(*P(-86.72, 41.61)), to(*P(-118.24, 34.05))
        ctrl = ((A[0] + B[0]) / 2, min(A[1], B[1]) - 170)
        return A, B, ctrl

    def bez(A, B, ctrl, q):
        return ((1 - q) ** 2 * A[0] + 2 * (1 - q) * q * ctrl[0] + q * q * B[0],
                (1 - q) ** 2 * A[1] + 2 * (1 - q) * q * ctrl[1] + q * q * B[1])

    cam = PageCam([(c1, 1.0, 1420, 960), (c1 + 0.5, 1.0, 1400, 965), (c2 - 0.3, 1.0, 470, 1140),
                   (c2, 1.0, 460, 1145)], ys=760)

    def d_map(f, u, t, ctx):
        to, s = cam.draw(f, ctx["map"], t)
        A, B, ctrl = route(ctx, to)
        r0, r1 = c1 + 0.35, c2 - 0.35
        prog = ease((t - r0) / (r1 - r0)) if t >= r0 else 0.0
        if prog > 0:
            S = 2
            xs = [A[0], B[0], ctrl[0]]
            ys = [A[1], B[1], ctrl[1]]
            bx0, by0 = int(min(xs) - 20), int(min(ys) - 20)
            bw, bh = int(max(xs) + 20) - bx0, int(max(ys) + 20) - by0
            lay = Image.new("RGBA", (bw * S, bh * S), (0, 0, 0, 0))
            dd = ImageDraw.Draw(lay)
            n = 70
            for i in range(n):
                q0, q1 = i / n, (i + 0.55) / n
                if q0 > prog:
                    break
                p0, p1 = bez(A, B, ctrl, q0), bez(A, B, ctrl, min(q1, prog))
                dd.line([((p0[0] - bx0) * S, (p0[1] - by0) * S), ((p1[0] - bx0) * S, (p1[1] - by0) * S)],
                        fill=BLOOD + (235,), width=7 * S)
            f.alpha_composite(lay.resize((bw, bh), Image.LANCZOS), (bx0, by0))
        for (x, y), lab, dy in ((A, ctx["lp"], 50), (B, ctx["la"], -52)):
            if -40 < x < W + 40:
                paste(f, ctx["dot"], x, y)
            if 70 + lab.width * 0.3 < x < 1000 - lab.width * 0.3:
                paste(f, lab, min(max(x, 70 + lab.width / 2), 1000 - lab.width / 2), y + dy)
        if t >= r1:
            k = (t - r1) / 0.6
            if k < 1:
                paste(f, C.ring(16 + 50 * k, 5, BLOOD, 1 - k), B[0], B[1])
        bs.shade(f)
        typed(f, "LOS ANGELES, 1931", t, t_la, 330, size=64, rate=0.04)
        bs.title(f, "ESTHER CARLSON", "bask", 96, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_esther - 0.05, 0.2))
        bs.credit_line(f, "Map: Natural Earth")

    def prep_card(ctx):
        prep_map(ctx)
        f = Image.new("RGBA", (W, H), (8, 8, 10, 255))
        cam.draw(f, ctx["map"], c2)
        ctx["bg"] = f.filter(ImageFilter.GaussianBlur(8))
        ctx["card"], ctx["y0"] = card_base(880, 470, "ESTHER CARLSON", 47)

    def d_card(f, u, t, ctx):
        f.alpha_composite(scaled(ctx["bg"], 1.0 + 0.04 * min(1.0, u / (c3 - c2))).crop((0, 0, W, H)))
        dim(f, 0.45)
        bs.shade(f)
        card = ctx["card"].copy()
        type_lines(card, [("— Charged with poisoning", t_charged), ("  August Lindstrom, 81", t_81 - 0.1),
                          ("— Died of TB before her trial", t_tb - 0.15)], t, ctx["y0"])
        k = appear(t, c2 + 0.02, 0.3)
        paste(f, card, W / 2, 760 + 60 * (1 - k), k)
        typed(f, "LOS ANGELES, 1931", t, -10, 330, size=64)

    def prep_split(ctx):
        im = bs.photo("belle-07.jpg", "sepia")
        im = im.crop((0, 0, int(im.width * 0.83), im.height))
        pw, ph = 420, 560
        sc = max(pw / im.width, ph / im.height)
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        x0, y0 = (im.width - pw) // 2, int((im.height - ph) * 0.25)
        left = im.crop((x0, y0, x0 + pw, y0 + ph))
        right = Image.new("RGBA", (pw, ph), (22, 18, 16, 255))
        cv = Image.new("L", (pw * 3, ph * 3), 0)
        dd = ImageDraw.Draw(cv)
        cx, by, s3 = pw * 1.5, ph * 3, 3.0
        dd.ellipse((cx - 150 * s3 * 0.9, by - 210 * s3 * 0.9, cx + 150 * s3 * 0.9, by + 120 * s3 * 0.9), fill=255)
        dd.rectangle((cx - 30 * s3, by - 300 * s3 * 0.9, cx + 30 * s3, by - 160 * s3 * 0.9), fill=255)
        dd.ellipse((cx - 62 * s3, by - 400 * s3 * 0.9, cx + 62 * s3, by - 250 * s3 * 0.9), fill=255)
        dd.ellipse((cx + 10 * s3, by - 445 * s3 * 0.9, cx + 75 * s3, by - 385 * s3 * 0.9), fill=255)
        sil = cv.resize((pw, ph), Image.LANCZOS)
        black = Image.new("RGBA", (pw, ph), (4, 3, 3, 255))
        black.putalpha(sil)
        right.alpha_composite(black)
        q = glow(T("?", "bask", 300, (222, 34, 30)), (120, 0, 0), radius=36, strength=0.9)
        right.alpha_composite(q, ((pw - q.width) // 2, int(ph * 0.28 - q.height / 2 + 40)))

        def framed(img):
            fr = Image.new("RGBA", (img.width + 20, img.height + 20), (236, 228, 210, 255))
            fr.alpha_composite(img.convert("RGBA"), (10, 10))
            return fr
        ctx["L"], ctx["R"] = framed(left), framed(right)
        ctx["l1"] = glow(T("BELLE · 1908", "bold", 36, BONE, tracking=4), (0, 0, 0), radius=14, strength=0.9)
        ctx["l2"] = glow(T("ESTHER · 1931", "bold", 36, BONE, tracking=4), (0, 0, 0), radius=14, strength=0.9)
        ctx["eq"] = glow(T("=", "bask", 160, (232, 40, 34)), (120, 0, 0), radius=26, strength=0.9)
        ctx["bg"] = bs.photo("belle-farm-14.jpg", "sepia", inset=0.05).filter(ImageFilter.GaussianBlur(9))

    def d_split(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c4 - c3, z=(1.05, 1.1))
        dim(f, 0.55)
        bs.shade(f)
        a1, a2 = appear(t, c3 + 0.02, 0.3), appear(t, c3 + 0.25, 0.3)
        paste(f, ctx["L"], 280, 760 + 40 * (1 - a1), a1)
        paste(f, ctx["R"], 800, 760 + 40 * (1 - a2), a2)
        paste(f, ctx["l1"], 280, 440, a1)
        paste(f, ctx["l2"], 800, 440, a2)
        if t >= t_swore - 0.05:
            k = appear(t, t_swore - 0.05, 0.15)
            paste(f, scaled(ctx["eq"], 1.4 - 0.4 * k), 540, 770, k)
        bs.title(f, "SWORE IT WAS BELLE", "bask", 92, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_swore - 0.1, 0.2))
        bs.credit_line(f, "Belle Gunness, public domain · farm photo: Steve Shook / CC BY 2.0")

    def prep_kids(ctx):
        ctx["im"] = bs.photo("belle-05.jpg", "sepia", inset=0.02)

    def d_kids(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c5 - c4, z=(1.0, 1.1), f0=(0.62, 0.5), f1=(0.63, 0.47))
        bs.shade(f)
        bs.title(f, "A PHOTO IN HER TRUNK", "bask", 88, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_trunk - 0.05, 0.2))
        bs.credit_line(f, "Belle Gunness's children: Library of Congress (public domain)")

    def prep_proof(ctx):
        ctx["im"] = bs.photo("belle-farm-13.jpg", "sepia", inset=0.05)
        ctx["stamp"] = bs.stamp([("NEVER", 96), ("PROVEN", 104)])

    def d_proof(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c6 - c5, z=(1.1, 1.16), f0=(0.44, 0.6), f1=(0.47, 0.62))
        dim(f, 0.3)
        bs.shade(f)
        if t >= t_proved - 0.1:
            k = appear(t, t_proved - 0.1, 0.12)
            sh = np.random.default_rng(int(t * 1000)).normal(0, 8, 2) if t - t_proved < 0.2 else (0, 0)
            paste(f, scaled(ctx["stamp"], 2.0 - 1.0 * k), W / 2 + sh[0], 760 + sh[1], min(1.0, k * 1.2))
        bs.credit_line(f, credit("belle-farm-13.jpg", "the farm after the fire, 1908"))

    def prep_end(ctx):
        prep_face(ctx)
        ctx["cta"] = C.DoubleTap("IF SHE GOT AWAY WITH IT", "Belle Gunness, Part 5")

    def d_end(f, u, t, ctx):
        bs.float_in(f, ctx["face"], u, R.dur - c6, w=(1250, 1330), focus=((0.41, 0.40), (0.41, 0.41)), at=(540, 470))
        dim(f, 0.2)
        bs.shade(f)
        ctx["cta"].draw(f, u)

    scenes = [C.Scene(0.0, c1, d_hook, prep_face), C.Scene(c1, c2, d_map, prep_map),
              C.Scene(c2, c3, d_card, prep_card), C.Scene(c3, c4, d_split, prep_split),
              C.Scene(c4, c5, d_kids, prep_kids), C.Scene(c5, c6, d_proof, prep_proof),
              C.Scene(c6, R.dur + 1, d_end, prep_end)]
    film = C.Film(R, scenes, flashes=[(0.35, 0.32)], label=label_fn("BELLE GUNNESS · PART 5", c1))
    ev = [("thunder", 0.33, 0.9), ("whoosh", c1, 0.7), ("type", t_la, 0.9), ("pop", c2 - 0.35, 0.8),
          ("whoosh", c2, 0.6), ("type", t_charged, 0.9), ("type", t_81 - 0.1, 0.9), ("type", t_tb - 0.15, 0.9),
          ("heartbeat", t_tb, 0.9), ("thud", c3, 0.7), ("hit", t_swore, 0.9), ("whoosh", c4, 0.6),
          ("hit", t_proved - 0.05, 1.0), ("pop", c6 + 0.12, 0.9), ("pop", c6 + 0.42, 0.9), ("hit", c6 + 0.5, 0.7)]
    return film, ev, "lullaby", "Belle Gunness, Part 5: Los Angeles, 1931"

BUILD = {"belle3": build_belle3, "belle4": build_belle4, "belle5": build_belle5}
FILES = {"belle3": "belle-gunness-part-3-the-newspaper-ad.mp4",
         "belle4": "belle-gunness-part-4-was-the-woman-in-the-fire-belle.mp4",
         "belle5": "belle-gunness-part-5-los-angeles-1931.mp4"}


def main(name, mode, times=None):
    R = C.Reel(name)
    film, ev, music, title = BUILD[name](R)
    if mode == "stills":
        ts = times or [0.4, 1.5, 2.9, 4.6, 6.6, 8.1, 9.6, 11.2, 12.8, 13.7, 15.5, 17.9, 19.6, 22.2, 23.9, 25.6, 26.6,
                       27.9]
        ts = [t for t in ts if t < R.dur]
        print(film.stills(ts, name))
        return
    os.makedirs(C.OUT, exist_ok=True)
    vid = os.path.join(C.OUT, "_" + name + "_video.mp4")
    film.video(vid, cover_t=0.6)
    mix = C.soundtrack(R, music, ev)
    out = os.path.join(C.OUT, FILES[name])
    C.finish(R, vid, mix, out, title)
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    ts = [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None
    main(sys.argv[1], sys.argv[2], ts)
