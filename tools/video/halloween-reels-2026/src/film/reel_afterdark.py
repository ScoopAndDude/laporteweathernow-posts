"""La Porte After Dark (Oct. 2026): Belle Gunness Part 8 (the woman in Los Angeles), Part 7 (Ray Lamphere) and the
Sept. 26, 1933 Michigan City prison break, in the Belle series' look (same shared drawing, captions, sound and mix as
reel_belle6.py).

    python3 reel_afterdark.py belle8|belle7|break33 stills|video [times]

Everything on screen is typeset or drawn here; no newspaper images are reproduced. The only photos are the Belle Gunness
series' (portraits: public domain; farm photos: Steve Shook, CC BY 2.0), credited on screen.
Facts (all supplied and checked by Scoop, nothing added): see each build's docstring.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import reels_common as C
from reels_common import bs, vr, W, H, SR, T, fitT, glow, paste, scaled, appear, ease, ease_out, dim, BONE, SEPIA, \
    INKC, BLOOD, GOLD
from reel_belle import label_fn, typed, red_title, credit, dot, scribble, PageCam, card_base, type_lines, \
    build_us_map
from reel_belle6 import build_chi_map

C.EXTRA["fraktur"] = "UnifrakturMaguntia.ttf"
C.WEIGHT.update({"1907": 4.4, "1909": 4.4, "1933": 4.7, "1910": 4.4, "1931?": 5.0, "1931": 5.0})
TEAL = (120, 230, 210)
PAPER = (244, 234, 214)
AI_LINE = "Narration is an AI voice."


# ----------------------------------------------------------------------------- shared pieces

def tl(entries, rate=0.022):
    """[(text, at)] where at=None continues the line above: typed right after it, in the same breath."""
    out, prev_end = [], 0.0
    for text, at in entries:
        if at is None:
            at = prev_end
        out.append((text, at))
        prev_end = at + len(text) * rate
    return out


def dark_bg(seed=5):
    """A drawn, textured dark ground (no photo) for the 1933 reel."""
    im = bs.aged_paper(1400, 2000, seed=seed)
    arr = np.asarray(im.convert("RGB"), np.float32) * np.array([0.42, 0.38, 0.34], np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA").filter(ImageFilter.GaussianBlur(6))


def card_h(lines, size=46):
    return int(200 + len(lines) * size * 1.42 + 10)


def blur_bg(fname, inset=0.05, blur=9):
    return bs.photo(fname, "sepia", inset=inset).filter(ImageFilter.GaussianBlur(blur))


def card_scene(c0, c1, title, entries, bg, seed, date=None, date_at=None, cred=None, big=None, ytop=420, size=46,
               cw=940, over=None, pic=None):
    """A re-set paper card over a dimmed, blurred photo: the card's heading, then its lines typed in time with the voice.
    big: (text, at) a bask title near the captions; over(f, u, t, ctx, ytop, ch) draws on top of the card."""
    entries = tl(entries)
    ch = card_h(entries, size)

    def prep(ctx):
        ctx["bg"] = blur_bg(bg) if bg else dark_bg()
        ctx["card"], ctx["y0"] = card_base(cw, ch, title, seed)

    def draw(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c1 - c0, z=(1.05, 1.1))
        dim(f, 0.5)
        bs.shade(f)
        card = ctx["card"].copy()
        type_lines(card, entries, t, ctx["y0"], size=size)
        k = appear(t, c0 + 0.02, 0.3)
        paste(f, card, W / 2, ytop + ch / 2 + 50 * (1 - k), k)
        if over:
            over(f, u, t, ctx, ytop, ch)
        if date:
            typed(f, date, t, date_at if date_at is not None else c0 + 0.05, 330, size=64, rate=0.045)
        if big:
            bs.title(f, big[0], "bask", 88, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, big[1] - 0.1, 0.25))
        if cred:
            bs.credit_line(f, cred)
    return C.Scene(c0, c1, draw, prep)


def stamp_over(lines, at, y_off, rot=0.0, ctxkey="stamp"):
    """Returns an `over` hook that slams a stamp onto the card at time `at`."""
    def over(f, u, t, ctx, ytop, ch):
        if ctxkey not in ctx:
            ctx[ctxkey] = bs.stamp(lines)
        if t >= at - 0.1:
            k = appear(t, at - 0.1, 0.12)
            sh = np.random.default_rng(int(t * 1000)).normal(0, 8, 2) if t - at < 0.2 else (0, 0)
            paste(f, scaled(ctx[ctxkey], 2.0 - 1.0 * k), W / 2 + sh[0], ytop + ch + y_off + sh[1], min(1.0, k * 1.2))
    return over


def man_icon(h, color):
    S = 3
    w = int(h * 0.62)
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, r = w * S / 2, w * S * 0.2
    d.ellipse((cx - r, 0, cx + r, 2 * r), fill=tuple(color) + (255,))
    d.rounded_rectangle((cx - w * S * 0.46, 2 * r + h * S * 0.05, cx + w * S * 0.46, h * S + w * S * 0.3),
                        radius=int(w * S * 0.25), fill=tuple(color) + (255,))
    return img.resize((w, h), Image.LANCZOS)


def pistol_icon(w, color):
    S = 3
    h = int(w * 0.68)
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = w * S / 100.0
    c = tuple(color) + (255,)
    d.rectangle((2 * u, 6 * u, 92 * u, 24 * u), fill=c)                       # slide and barrel
    d.polygon([(60 * u, 24 * u), (92 * u, 24 * u), (78 * u, 66 * u), (54 * u, 66 * u)], fill=c)   # grip
    d.polygon([(44 * u, 24 * u), (60 * u, 24 * u), (58 * u, 36 * u), (46 * u, 36 * u)], fill=c)
    d.arc((38 * u, 22 * u, 62 * u, 46 * u), 0, 180, fill=c, width=int(3.2 * u))   # trigger guard
    d.rectangle((88 * u, 2 * u, 95 * u, 7 * u), fill=c)                       # rear sight
    return img.resize((w, h), Image.LANCZOS)


class EndCard:
    """La Porte After Dark's end card: the series name, the site, the sources, and the AI-voice disclosure."""

    def __init__(self, bgname, sources, line2):
        self.bg = blur_bg(bgname, blur=10) if isinstance(bgname, str) else bgname
        self.a = glow(fitT("LA PORTE AFTER DARK", "bask", 112, BONE, max_w=C.CW + 40, min_size=50), (0, 0, 0),
                      radius=26, strength=0.9)
        self.b = glow(fitT(line2, "lora", 56, (250, 70, 56), max_w=C.CW + 40, min_size=34), (0, 0, 0), radius=18,
                      strength=0.9)
        self.url = glow(T("laporteweathernow.com", "black", 70, GOLD), (0, 0, 0), radius=20, strength=0.9)
        self.ai = glow(T(AI_LINE, "lora", 50, BONE), (0, 0, 0), radius=16, strength=0.9)
        self.src = [glow(T(s, "bold", 31, (226, 214, 190)), (0, 0, 0), radius=10, strength=0.9) for s in sources]

    def draw(self, f, u, dur):
        bs.kenburns(f, self.bg, u, dur, z=(1.05, 1.1))
        dim(f, 0.55)
        bs.shade(f)
        paste(f, self.a, W / 2, 520, appear(u, 0.1, 0.35))
        paste(f, self.b, W / 2, 680, appear(u, 0.35, 0.3))
        paste(f, self.url, W / 2, 860, appear(u, 0.6, 0.3))
        paste(f, self.ai, W / 2, 985, appear(u, 0.9, 0.3))
        for i, s in enumerate(self.src):
            paste(f, s, W / 2, 1110 + 44 * i, appear(u, 1.1 + 0.12 * i, 0.3))


def route_map_scene(c0, c1, r0, r1, date, date_at, title, title_at, B_lonlat, dest_label, shared, cred="Map: Natural Earth"):
    """Part 5's map: La Porte, then the line across the country (pan from the Midwest to the destination)."""
    def prep(ctx):
        if "map" not in shared:
            shared["map"], shared["P"] = build_us_map()
        ctx.update(map=shared["map"], P=shared["P"], dot=dot(13, BLOOD),
                   lp=glow(T("LA PORTE, IND.", "oldst_b", 40, INKC), PAPER, radius=10, strength=0.9),
                   la=glow(T(dest_label, "oldst_b", 40, INKC), PAPER, radius=10, strength=0.9))
    cam = PageCam([(c0, 1.0, 1420, 960), (c0 + 0.5, 1.0, 1400, 965), (r1 - 0.2, 1.0, 470, 1140), (r1, 1.0, 460, 1145)],
                  ys=760)

    def bez(A, B, ctrl, q):
        return ((1 - q) ** 2 * A[0] + 2 * (1 - q) * q * ctrl[0] + q * q * B[0],
                (1 - q) ** 2 * A[1] + 2 * (1 - q) * q * ctrl[1] + q * q * B[1])

    def draw(f, u, t, ctx):
        to, s = cam.draw(f, ctx["map"], t)
        P = ctx["P"]
        A, B = to(*P(-86.72, 41.61)), to(*P(*B_lonlat))
        ctrl = ((A[0] + B[0]) / 2, min(A[1], B[1]) - 170)
        prog = ease((t - r0) / (r1 - r0)) if t >= r0 else 0.0
        if prog > 0:
            S = 2
            xs, ys = [A[0], B[0], ctrl[0]], [A[1], B[1], ctrl[1]]
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
        typed(f, date, t, date_at, 330, size=64, rate=0.04)
        bs.title(f, title, "bask", 96, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, title_at - 0.05, 0.2))
        bs.credit_line(f, cred)
    return C.Scene(c0, c1, draw, prep)


def newspaper_card(name, dateline, body_lines, seed, w=940, size=44):
    """A typeset newspaper-style card (our own lettering: not a reproduction of any page). Returns (card, y0)."""
    h = int(250 + len(body_lines) * size * 1.42 + 40)
    card = bs.aged_paper(w, h, seed=seed)
    d = ImageDraw.Draw(card)
    head = fitT(name, "fraktur", 84, INKC, max_w=w - 100, min_size=40)
    card.alpha_composite(head, ((w - head.width) // 2, 28))
    y = 28 + head.height + 14
    d.line((40, y, w - 40, y), fill=INKC + (210,), width=3)
    d.line((40, y + 7, w - 40, y + 7), fill=INKC + (210,), width=1)
    dl = fitT(dateline, "oldst_b", 34, INKC, max_w=w - 100, min_size=22, tracking=2)
    card.alpha_composite(dl, ((w - dl.width) // 2, y + 20))
    y2 = y + 20 + dl.height + 12
    d.line((40, y2, w - 40, y2), fill=INKC + (160,), width=1)
    return card, y2 + 34, h


# ----------------------------------------------------------------------------- Part 8

def build_belle8(R):
    """Belle Gunness, Part 8: the woman in Los Angeles. Facts: retired lumberman August Lindstrom died in Los Angeles
    (Feb. 9, 1931); housekeeper Esther Carlson and neighbor Anna Erickson were charged with poisoning him for the $2,000
    in his bank account; county chemists testified there was enough poison in his body to kill 10 men; word spread
    that Carlson might be Belle Gunness and people who had known Belle were brought to see her; the papers disagree:
    Evening Star (Washington, D.C.) May 5, 1931, friends of Belle denied it; South Bend News-Times May 15, 1931, two
    men had been positive; Carlson, seriously ill with TB, got a separate trial and died in a Los Angeles hospital May
    6, 1931, before trial; asked if she had poisoned him, the only audible reply was a mumble that might have been
    'yes' (Indianapolis Times, May 7, 1931); Erickson was acquitted; never proved. Never says Carlson WAS Belle."""
    t_aug, t_house, t_chem = R.at("August"), R.at("His housekeeper,"), R.at("Chemists")
    t_ten, t_word, t_see = R.at("ten men."), R.at("Word spread"), R.at("brought")
    t_but, t_tb, t_asked = R.at("But Carlson"), R.at("tuberculosis,"), R.at("Asked")
    t_mumb, t_pap, t_one = R.at("mumbled"), R.at("The papers"), R.at("One said")
    t_anot, t_neigh = R.at("Another said"), R.at("The neighbor")
    t_whe, t_prov, t_fol = R.at("Whether Carlson"), R.at("proved."), R.at("Follow")
    t_charged, t_died = R.at("charged"), R.at("died before")
    c1 = (R.end("1931?") + t_aug) / 2
    c2 = t_house - 0.12
    c3 = t_chem - 0.12
    c4 = t_word - 0.12
    c5 = t_but - 0.12
    c6 = t_asked - 0.12
    c7 = t_pap - 0.12
    c8 = t_neigh - 0.12
    c9 = t_fol - 0.12
    shared = {}
    SRC = "Sources: Evening Star (Washington, D.C.), May 5, 1931 · The Indianapolis Times, May 7, 1931 · "\
          "South Bend News-Times, May 15, 1931 (Library of Congress, Chronicling America)"

    def p_hook(ctx):
        if "face" not in shared:
            shared["face"] = bs.emerging("belle-08.jpg", "sepia", scale=3.0, blur=0.5)
        ctx["face"] = shared["face"]

    def d_hook(f, u, t, ctx):
        bs.float_in(f, ctx["face"], u, c1, w=(1420, 1260), focus=((0.41, 0.40), (0.42, 0.42)), at=(540, 640))
        bs.shade(f)
        red_title(f, "LOS ANGELES, 1931?", 104, t, -0.2)
        bs.credit_line(f, "Belle Gunness portrait: public domain")

    s_map = route_map_scene(c1, c2, c1 + 0.35, c2 - 0.4, "FEBRUARY 1931", c1 + 0.05, "AUGUST LINDSTROM", t_aug,
                            (-118.24, 34.05), "LOS ANGELES, CALIF.", shared)

    # the charges, typeset like a clipping
    s_card = card_scene(c2, c3, "POISONING CHARGES", [
        ("— Housekeeper: Esther Carlson", t_house + 0.1),
        ("— Neighbor: Anna Erickson", R.at("and a neighbor") - 0.05),
        ("— Charged with poisoning", t_charged - 0.1), ("  August Lindstrom", None),
        ("— Said to be for the $2,000", t_charged + 0.7), ("  in his bank account", None)],
        "belle-farm-14.jpg", 61, date="LOS ANGELES, 1931", date_at=c2 + 0.02,
        cred="Photo: Steve Shook / CC BY 2.0 · cards typeset from the reports")

    # ten men's worth of poison
    def p_ten(ctx):
        ctx["bg"] = blur_bg("belle-farm-13.jpg")
        ctx["men"] = [man_icon(250, BONE), man_icon(250, (235, 70, 56))]
        ctx["lab"] = glow(T("COUNTY CHEMISTS' TESTIMONY", "bold", 34, BONE, tracking=4), (0, 0, 0), radius=14,
                          strength=0.9)

    def d_ten(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c4 - c3, z=(1.05, 1.1))
        dim(f, 0.62)
        bs.shade(f)
        paste(f, ctx["lab"], W / 2, 430, appear(t, c3 + 0.1, 0.3))
        step = (t_ten - 0.1 - (t_chem + 0.9)) / 10
        for i in range(10):
            at = t_chem + 0.9 + i * step
            a = appear(t, at, 0.15)
            red = t >= t_ten - 0.15
            x = 150 + (i % 5) * 195
            y = 700 + (i // 5) * 340
            paste(f, ctx["men"][1 if red else 0], x, y - 18 * (1 - a), a)
        bs.title(f, "ENOUGH TO KILL 10 MEN", "bask", 88, BONE, 1205, glow=(0, 0, 0),
                 alpha=appear(t, t_ten - 0.9, 0.25))
        bs.credit_line(f, "Drawn graphic · county chemists, as reported in 1931")

    # word spread
    def p_split(ctx):
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
        ctx["l2"] = glow(T("ESTHER CARLSON", "bold", 36, BONE, tracking=4), (0, 0, 0), radius=14, strength=0.9)
        ctx["bg"] = blur_bg("belle-farm-14.jpg")

    def d_split(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c5 - c4, z=(1.05, 1.1))
        dim(f, 0.55)
        bs.shade(f)
        a1, a2 = appear(t, c4 + 0.02, 0.3), appear(t, t_word + 0.9, 0.3)
        paste(f, ctx["L"], 280, 760 + 40 * (1 - a1), a1)
        paste(f, ctx["R"], 800, 760 + 40 * (1 - a2), a2)
        paste(f, ctx["l1"], 280, 440, a1)
        paste(f, ctx["l2"], 800, 440, a2)
        bs.title(f, "BROUGHT TO SEE HER", "bask", 92, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_see - 0.1, 0.2))
        bs.credit_line(f, "Belle Gunness: public domain · farm photo: Steve Shook / CC BY 2.0")

    s_tb = card_scene(c5, c6, "ESTHER CARLSON", [
        ("— Seriously ill with", t_tb - 1.0), ("  tuberculosis", None),
        ("— Separate trial", t_tb + 0.5),
        ("— Died May 6, 1931,", t_died - 0.05), ("  Los Angeles hospital", None),
        ("— Before her trial", t_died + 0.55)],
        "belle-farm-13.jpg", 53, date="MAY 1931", date_at=c5 + 0.05,
        cred="Photo: Steve Shook / CC BY 2.0 · the farm after the fire, 1908")

    # the mumble
    def p_mum(ctx):
        ctx["bg"] = blur_bg("belle-farm-15.jpg", blur=14)
        ctx["lab"] = glow(T("THE ONLY AUDIBLE REPLY", "bold", 38, BONE, tracking=5), (0, 0, 0), radius=14, strength=0.9)
        ctx["src"] = glow(T("The Indianapolis Times, May 7, 1931", "oldst_b", 34, PAPER), (0, 0, 0), radius=12,
                          strength=0.9)
        S = 2
        bw, bh = 800, 360
        img = Image.new("RGBA", ((bw + 40) * S, (bh + 120) * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((20 * S, 10 * S, (bw + 20) * S, (bh + 10) * S), radius=60 * S, fill=PAPER + (255,),
                            outline=INKC + (255,), width=5 * S)
        d.polygon([(150 * S, (bh + 5) * S), (260 * S, (bh + 5) * S), (120 * S, (bh + 110) * S)], fill=PAPER + (255,),
                  outline=INKC + (255,))
        d.polygon([(158 * S, (bh + 2) * S), (252 * S, (bh + 2) * S), (130 * S, (bh + 95) * S)], fill=PAPER + (255,))
        ctx["bub"] = img.resize((img.width // S, img.height // S), Image.LANCZOS)

    def d_mum(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c7 - c6, z=(1.05, 1.1))
        dim(f, 0.62)
        bs.shade(f)
        paste(f, ctx["lab"], W / 2, 450, appear(t, c6 + 0.1, 0.3))
        paste(f, ctx["bub"], W / 2, 770, appear(t, t_asked + 0.6, 0.3))
        txt = "mmm…"
        if t >= t_mumb:
            n = int(min(len(txt), (t - t_mumb) / 0.12 + 1))
            img = T(txt[:n], "typew", 130, INKC)
            paste(f, img, W / 2, 745)
        if t >= t_mumb + 0.9:
            paste(f, T("yes?", "fell_it", 96, (160, 40, 34)), W / 2 + 160, 840, appear(t, t_mumb + 0.9, 0.5) * 0.9)
        paste(f, ctx["src"], W / 2, 1060, appear(t, t_mumb + 0.2, 0.3))
        bs.title(f, "MAYBE “YES”", "bask", 92, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_mumb + 0.9, 0.25))
        bs.credit_line(f, "Photo: Steve Shook / CC BY 2.0 · Indianapolis Times via Chronicling America")

    # the papers disagree
    def p_pap(ctx):
        ctx["bg"] = blur_bg("belle-farm-14.jpg", blur=12)
        ctx["c1"], ctx["y1"], ctx["h1"] = newspaper_card("Evening Star", "WASHINGTON, D.C. · MAY 5, 1931",
                                                         ["Reported:", "friends of Belle denied it"], 11)
        ctx["c2"], ctx["y2"], ctx["h2"] = newspaper_card("South Bend News-Times", "SOUTH BEND, IND. · MAY 15, 1931",
                                                         ["Said:", "two men had been positive"], 12)

    def d_pap(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c8 - c7, z=(1.05, 1.1))
        dim(f, 0.58)
        bs.shade(f)
        for key, y, at, ln in (("1", 420, t_one, [("Reported:", None), ("friends of Belle denied it", None)]),
                               ("2", 800, t_anot, [("Said:", None), ("two men had been positive", None)])):
            card, y0, h = ctx["c" + key], ctx["y" + key], ctx["h" + key]
            card = card.copy()
            lines = tl([(ln[0][0], at - 0.05), (ln[1][0], at + 0.25)])
            type_lines(card, lines, t, y0, size=44)
            k = appear(t, at - 0.35, 0.3)
            paste(f, card, W / 2, y + h / 2 + 40 * (1 - k), k)
        typed(f, "THE PAPERS DISAGREED", t, c7 + 0.05, 330, size=52, rate=0.04)
        bs.credit_line(f, "Chronicling America (Library of Congress) · cards typeset, not reproduced")

    s_end_card = card_scene(c8, c9, "THE VERDICTS", [
        ("— Anna Erickson:", t_neigh + 0.05), ("  acquitted", None),
        ("— Esther Carlson:", t_whe - 0.1), ("  died before trial", None),
        ("— Was she Belle?", t_whe + 0.6), ("  Never proved", None)],
        "belle-farm-13.jpg", 57, date="1931", date_at=c8 + 0.05,
        over=stamp_over([("NEVER", 96), ("PROVEN", 104)], t_prov - 0.1, 140),
        cred="Photo: Steve Shook / CC BY 2.0 · the farm after the fire, 1908")

    end = EndCard("belle-farm-15.jpg",
                  ["Evening Star, May 5, 1931 · Indianapolis Times, May 7, 1931",
                   "South Bend News-Times, May 15, 1931",
                   "Library of Congress, Chronicling America"], "Belle Gunness, Part 8")

    def d_end(f, u, t, ctx):
        end.draw(f, u, R.dur - c9)

    scenes = [C.Scene(0.0, c1, d_hook, p_hook), s_map, s_card, C.Scene(c3, c4, d_ten, p_ten),
              C.Scene(c4, c5, d_split, p_split), s_tb, C.Scene(c6, c7, d_mum, p_mum), C.Scene(c7, c8, d_pap, p_pap),
              s_end_card, C.Scene(c9, R.dur + 1, d_end, None)]
    film = C.Film(R, scenes, flashes=[(0.35, 0.32)], label=label_fn("BELLE GUNNESS · PART 8", c1))
    ev = [("thunder", 0.33, 0.9), ("whoosh", c1, 0.7), ("type", c1 + 0.05, 0.9), ("pop", c2 - 0.4, 0.8),
          ("whoosh", c2, 0.6), ("type", t_house + 0.1, 0.8), ("type", t_charged - 0.1, 0.8),
          ("whoosh", c3, 0.6), ("pop", t_chem + 0.9, 0.5), ("hit", t_ten - 0.15, 0.9),
          ("whoosh", c4, 0.6), ("pop", t_word + 0.9, 0.7), ("whoosh", c5, 0.6), ("type", t_tb - 1.0, 0.8),
          ("heartbeat", t_died, 0.7), ("whoosh", c6, 0.6), ("pop", t_asked + 0.6, 0.6), ("thud", t_mumb, 0.7),
          ("whoosh", c7, 0.6), ("pop", t_one - 0.3, 0.7), ("pop", t_anot - 0.3, 0.7), ("whoosh", c8, 0.6),
          ("type", t_neigh + 0.05, 0.8), ("hit", t_prov - 0.1, 1.0), ("whoosh", c9, 0.6), ("pop", c9 + 0.3, 0.8)]
    return film, ev, "lullaby", "Belle Gunness, Part 8: The Woman in Los Angeles"


# ----------------------------------------------------------------------------- Part 7

def jail_bars(bgname, c0, c1, date, date_at, big, big_at, cred):
    def prep(ctx):
        ctx["bg"] = blur_bg(bgname, blur=11)
        S = 2
        img = Image.new("RGBA", (W * S, 1500 * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i in range(9):
            x = (110 + i * 107) * S
            d.rounded_rectangle((x - 14 * S, 0, x + 14 * S, 1500 * S), radius=14 * S, fill=(14, 12, 12, 255))
            d.rounded_rectangle((x - 6 * S, 0, x - 1 * S, 1500 * S), radius=3 * S, fill=(58, 54, 50, 255))
        for y in (360, 1060):
            d.rectangle((60 * S, (y - 20) * S, (W - 60) * S, (y + 20) * S), fill=(14, 12, 12, 255))
        ctx["bars"] = img.resize((W, 1500), Image.LANCZOS)

    def draw(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c1 - c0, z=(1.05, 1.1))
        dim(f, 0.55)
        k = appear(t, c0 + 0.1, 0.5)
        f.alpha_composite(C.alpha(ctx["bars"], k), (0, 250))
        bs.shade(f)
        typed(f, date, t, date_at, 330, size=72, rate=0.05)
        bs.title(f, big, "bask", 92, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, big_at - 0.1, 0.25))
        bs.credit_line(f, cred)
    return C.Scene(c0, c1, draw, prep)


def build_belle7(R):
    """Belle Gunness, Part 7: the only man convicted. Facts: Ray Lamphere worked Belle's farm from Aug. 1907 until she
    fired him in Feb. 1908; after the April 28, 1908 fire he was tried; in Nov. a jury found him guilty of arson but not
    murder; died in custody Dec. 30, 1909; in Jan. 1910 the Rev. E. A. Schell made public a confession Lamphere had given
    him; one newspaper that month says he admitted killing four people but denied setting the fire; other accounts say he
    helped bury victims and Belle escaped alive; the records don't agree. Sources: La Porte County Historical Society
    Museum; Fort Wayne Sentinel, Jan. 19, 1910."""
    t_ray, t_fired = R.at("Ray Lamphere"), R.at("fired")
    t_after, t_jury = R.at("After the"), R.at("A jury")
    t_arson, t_murder = R.at("arson,"), R.at("murder.")
    t_died, t_weeks = R.at("He died"), R.at("Weeks later")
    t_conf, t_one = R.at("confession"), R.at("One newspaper")
    t_four, t_fire = R.at("four"), R.at("fire.", t_one)
    t_other, t_bury = R.at("Other accounts"), R.at("bury")
    t_rec, t_dis = R.at("The records"), R.at("agree.")
    t_fol = R.at("Follow")
    c1 = (R.end("case.") + t_ray) / 2
    c2 = t_after - 0.12
    c3 = t_died - 0.12
    c4 = t_weeks - 0.12
    c5 = t_one - 0.12
    c6 = t_other - 0.12
    c7 = t_rec - 0.12
    c8 = t_fol - 0.12
    SRC = ["La Porte County Historical Society Museum", "Fort Wayne Sentinel, Jan. 19, 1910"]

    def p_hook(ctx):
        ctx["im"] = bs.photo("belle-farm-07.jpg", "sepia", inset=0.03)

    def d_hook(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c1, z=(1.1, 1.2), f0=(0.5, 0.55), f1=(0.52, 0.58))
        bs.shade(f)
        red_title(f, "THE ONLY ONE CONVICTED", 96, t, -0.2)
        bs.credit_line(f, credit("belle-farm-07.jpg", "the Gunness farm, 1908"))

    # Aug. 1907 -> Feb. 1908 on a drawn bar
    def p_bar(ctx):
        ctx["bg"] = blur_bg("belle-farm-10.jpg")
        ctx["card"], ctx["y0"] = card_base(940, 640, "RAY LAMPHERE", 71)
        ctx["stamp"] = bs.stamp([("FIRED", 130)])

    def d_bar(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c2 - c1, z=(1.05, 1.1))
        dim(f, 0.5)
        bs.shade(f)
        card = ctx["card"].copy()
        d = ImageDraw.Draw(card)
        y = ctx["y0"] + 40
        card.alpha_composite(T("Worked Belle's farm", "typew", 46, INKC), (52, y))
        x0, x1, yb = 90, 850, y + 190
        prog = ease((t - (t_ray + 1.2)) / (t_fired - 0.1 - (t_ray + 1.2)))
        d.line((x0, yb, x1, yb), fill=INKC + (120,), width=6)
        for i in range(7):
            xx = x0 + (x1 - x0) * i / 6
            d.line((xx, yb - 16, xx, yb + 16), fill=INKC + (200,), width=4)
        d.line((x0, yb, x0 + (x1 - x0) * prog, yb), fill=BLOOD + (255,), width=12)
        d.ellipse((x0 + (x1 - x0) * prog - 14, yb - 14, x0 + (x1 - x0) * prog + 14, yb + 14), fill=BLOOD + (255,))
        card.alpha_composite(T("AUG. 1907", "typew", 40, INKC), (x0 - 40, yb + 40))
        card.alpha_composite(T("FEB. 1908", "typew", 40, INKC), (x1 - 150, yb + 40))
        k = appear(t, c1 + 0.02, 0.3)
        paste(f, card, W / 2, 420 + 320 + 50 * (1 - k), k)
        if t >= t_fired - 0.1:
            kk = appear(t, t_fired - 0.1, 0.12)
            sh = np.random.default_rng(int(t * 1000)).normal(0, 8, 2) if t - t_fired < 0.2 else (0, 0)
            paste(f, scaled(ctx["stamp"], 2.0 - 1.0 * kk), W / 2 + sh[0], 1010 + sh[1], min(1.0, kk * 1.2))
        typed(f, "1907 – 1908", t, c1 + 0.05, 330, size=72, rate=0.05)
        bs.credit_line(f, credit("belle-farm-10.jpg", "the Gunness farm"))

    s_trial = card_scene(c2, c3, "THE TRIAL", [
        ("— The farm burned", t_after - 0.05), ("  April 28, 1908", None),
        ("— Lamphere went on trial", t_after + 1.4),
        ("— Nov. 1908: jury says", t_jury), ("  Arson: GUILTY", t_arson - 0.4),
        ("  Murder: NOT GUILTY", t_murder - 0.7)],
        "belle-farm-13.jpg", 63, date="NOVEMBER 1908", date_at=c2 + 0.05,
        over=stamp_over([("GUILTY OF", 66), ("ARSON", 120)], t_murder + 0.7, 140),
        cred=credit("belle-farm-13.jpg", "the farm after the fire, 1908"))

    s_died = jail_bars("belle-farm-14.jpg", c3, c4, "DEC. 30, 1909", c3 + 0.05, "DIED IN CUSTODY", t_died + 0.5,
                       credit("belle-farm-14.jpg", "the farm, 1908 · bars drawn"))

    # the confession: a letter
    def p_conf(ctx):
        ctx["bg"] = blur_bg("belle-farm-15.jpg", blur=14)
        env = bs.aged_paper(860, 620, seed=29)
        d = ImageDraw.Draw(env)
        rng = np.random.default_rng(12)
        for y in range(120, 560, 52):
            scribble(d, 70, 780 - int(rng.integers(0, 140)), y, rng, a=150)
        d.line((70, 520, 340, 520), fill=INKC + (170,), width=3)
        ctx["env"] = env.rotate(-2.5, resample=Image.BICUBIC, expand=True)
        ctx["lab"] = glow(T("MADE PUBLIC BY THE REV. E. A. SCHELL", "bold", 32, BONE, tracking=3), (0, 0, 0),
                          radius=14, strength=0.9)

    def d_conf(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c5 - c4, z=(1.05, 1.1))
        dim(f, 0.58)
        bs.shade(f)
        a = appear(t, c4 + 0.05, 0.4)
        paste(f, ctx["env"], W / 2, 760 + 40 * (1 - a), a)
        paste(f, ctx["lab"], W / 2, 450, appear(t, t_weeks + 0.5, 0.3))
        typed(f, "JANUARY 1910", t, c4 + 0.05, 330, size=72, rate=0.05)
        bs.title(f, "A CONFESSION", "bask", 92, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_conf - 0.1, 0.25))
        bs.credit_line(f, credit("belle-farm-15.jpg", "viewing the cellar, 1908 · letter drawn"))

    # two accounts
    s_one = card_scene(c5, c6, "ONE NEWSPAPER, JAN. 1910", [
        ("— Admitted killing", t_one + 0.4), ("  four people", None),
        ("— Denied setting", t_fire - 1.2), ("  the fire", None)],
        "belle-farm-13.jpg", 77, date="HIS STORY", date_at=c5 + 0.05,
        cred="Fort Wayne Sentinel, Jan. 19, 1910 · La Porte Co. Historical Society Museum")

    s_other = card_scene(c6, c7, "OTHER ACCOUNTS", [
        ("— Helped bury victims", t_bury - 0.6),
        ("— Belle escaped alive", R.at("escaped") - 0.4)],
        "belle-farm-14.jpg", 79, date="HIS STORY, AGAIN", date_at=c6 + 0.05,
        cred="Fort Wayne Sentinel, Jan. 19, 1910 · La Porte Co. Historical Society Museum")

    def p_dis(ctx):
        ctx["bg"] = blur_bg("belle-farm-15.jpg", blur=12)
        ctx["stamp"] = bs.stamp([("RECORDS", 100), ("DISAGREE", 100)])

    def d_dis(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c8 - c7, z=(1.05, 1.1))
        dim(f, 0.5)
        bs.shade(f)
        if t >= t_dis - 0.5:
            kk = appear(t, t_dis - 0.5, 0.12)
            sh = np.random.default_rng(int(t * 1000)).normal(0, 8, 2) if t - (t_dis - 0.4) < 0.2 else (0, 0)
            paste(f, scaled(ctx["stamp"], 2.0 - 1.0 * kk), W / 2 + sh[0], 760 + sh[1], min(1.0, kk * 1.2))
        bs.credit_line(f, credit("belle-farm-15.jpg", "viewing the cellar, 1908"))

    end = EndCard("belle-farm-15.jpg", ["La Porte County Historical Society Museum",
                                        "Fort Wayne Sentinel, Jan. 19, 1910"], "Belle Gunness, Part 7")

    def d_end(f, u, t, ctx):
        end.draw(f, u, R.dur - c8)

    scenes = [C.Scene(0.0, c1, d_hook, p_hook), C.Scene(c1, c2, d_bar, p_bar), s_trial, s_died,
              C.Scene(c4, c5, d_conf, p_conf), s_one, s_other, C.Scene(c7, c8, d_dis, p_dis),
              C.Scene(c8, R.dur + 1, d_end, None)]
    film = C.Film(R, scenes, flashes=[(0.35, 0.32)], label=label_fn("BELLE GUNNESS · PART 7", c1))
    ev = [("thunder", 0.33, 0.9), ("whoosh", c1, 0.7), ("type", c1 + 0.05, 0.9), ("hit", t_fired - 0.1, 1.0),
          ("whoosh", c2, 0.6), ("type", t_after - 0.05, 0.8), ("type", t_jury, 0.8), ("hit", t_murder + 0.7, 1.0),
          ("whoosh", c3, 0.6), ("type", c3 + 0.05, 0.9), ("thud", t_died + 0.5, 0.7), ("whoosh", c4, 0.6),
          ("type", c4 + 0.05, 0.9), ("pop", t_weeks + 0.5, 0.6), ("whoosh", c5, 0.6), ("type", t_one + 0.4, 0.8),
          ("whoosh", c6, 0.6), ("type", t_bury - 0.6, 0.8), ("hit", t_dis - 0.5, 1.0), ("whoosh", c8, 0.6),
          ("pop", c8 + 0.3, 0.8)]
    return film, ev, "lullaby", "Belle Gunness, Part 7: The Only Man Convicted"


# ----------------------------------------------------------------------------- the 1933 break

def build_break33(R):
    """Ten men, three pistols. Facts: on Sept. 26, 1933 ten inmates escaped the Indiana State Prison in Michigan City
    (La Porte County) using three pistols John Dillinger had smuggled in; he was paroled that May and arrested in Dayton,
    Ohio on Sept. 22, so he was not there; Harry Pierpont and Charles Makley were among the ten; on Oct. 12 they freed
    Dillinger from the jail in Lima, Ohio, and Sheriff Jess Sarber was killed; how the guns got in is not known for
    sure, the most widely believed theory is boxes of thread for the shirt factory. Names no one hurt in the break.
    Sources: History.com; Wikipedia (Harry Pierpont, Indiana State Prison); Chicago Tribune, Sept. 1933."""
    t_ten, t_three, t_dill = R.at("Ten men."), R.at("Three pistols."), R.at("Dillinger wasn't")
    t_sept, t_esc = R.at("On September"), R.at("escaped")
    t_used, t_smug = R.at("They used"), R.at("smuggled")
    t_he, t_may, t_arr = R.at("But he'd"), R.at("May"), R.at("Dayton,")
    t_harry, t_oct, t_lima = R.at("Harry Pierpont"), R.at("On October"), R.at("Lima,")
    t_sher = R.at("Sheriff Jess")
    t_how, t_nok, t_theory = R.at("How did"), R.at("No one"), R.at("The most")
    t_thread = R.at("thread")
    t_fol = R.at("Follow")
    c1 = (R.end("there.") + t_sept) / 2
    c2 = (R.end("City.") + t_used) / 2
    c3 = (R.end("in.", t_smug) + t_he) / 2
    c4 = (R.end("Ohio", t_he) + t_harry) / 2 if False else t_harry - 0.12
    c5 = t_how - 0.12
    c6 = t_fol - 0.12
    shared = {}
    SRC = ["History.com · Wikipedia (Harry Pierpont; Indiana State Prison)", "Chicago Tribune, Sept. 1933"]

    def p_hook(ctx):
        ctx["bg"] = dark_bg()
        ctx["men"] = [man_icon(230, BONE), man_icon(230, (235, 70, 56))]
        ctx["gun"] = [pistol_icon(250, (236, 226, 204)) for _ in range(3)]
        ctx["ghost"] = man_icon(230, (120, 112, 100))

    def d_hook(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c1, z=(1.05, 1.1))
        dim(f, 0.7)
        bs.shade(f)
        for i in range(10):
            at = 0.5 + i * (t_three - 0.3 - 0.5) / 10
            a = appear(t, at, 0.15)
            x = 160 + (i % 5) * 190
            y = 560 + (i // 5) * 270
            paste(f, ctx["men"][0], x, y - 14 * (1 - a), a)
        for i in range(3):
            a = appear(t, t_three + 0.1 + i * 0.25, 0.2)
            paste(f, scaled(ctx["gun"][i], 0.8), 215 + i * 325, 1060 - 16 * (1 - a), a)
        if t >= t_dill + 0.2:
            a = appear(t, t_dill + 0.2, 0.4)
            paste(f, T("?", "bask", 300, (222, 34, 30)), 540, 760, a * 0.9)
        red_title(f, "TEN MEN. THREE PISTOLS.", 92, t, -0.2)
        bs.credit_line(f, "Drawn graphic · history: History.com, Wikipedia, Chicago Tribune (Sept. 1933)")

    def p_map(ctx):
        if "chi" not in shared:
            shared["chi"], shared["P"] = build_chi_map()
        ctx.update(map=shared["chi"], P=shared["P"], dot=dot(13, BLOOD),
                   mc=glow(T("MICHIGAN CITY", "oldst_b", 40, INKC), PAPER, radius=10, strength=0.9),
                   lp=glow(T("LA PORTE", "oldst", 34, INKC), PAPER, radius=10, strength=0.9),
                   cnt=glow(T("LA PORTE COUNTY", "fell_sc", 38, INKC, tracking=6), PAPER, radius=10, strength=0.6))

    cam = PageCam([(c1, 1.0, 700, 1000), (c1 + 1.0, 1.4, 760, 940), (c2, 1.65, 770, 920)], ys=800)

    def d_map(f, u, t, ctx):
        to, s = cam.draw(f, ctx["map"], t)
        P = ctx["P"]
        A = to(*P(-86.895, 41.707))     # Michigan City
        L = to(*P(-86.72, 41.61))       # La Porte
        paste(f, ctx["dot"], L[0], L[1])
        paste(f, ctx["lp"], L[0] + 40, L[1] + 44, 0.9)
        paste(f, ctx["dot"], A[0], A[1])
        paste(f, ctx["mc"], A[0] - 40, A[1] - 52)
        k = (t - (t_esc - 0.3)) / 0.7
        if 0 <= k < 1:
            paste(f, C.ring(18 + 90 * k, 6, BLOOD, 1 - k), A[0], A[1])
        bs.shade(f)
        typed(f, "SEPT. 26, 1933", t, c1 + 0.05, 330, size=72, rate=0.05)
        bs.title(f, "INDIANA STATE PRISON", "bask", 82, BONE, 1205, glow=(0, 0, 0),
                 alpha=appear(t, t_sept + 1.6, 0.25))
        bs.credit_line(f, "Map: Natural Earth, U.S. Census Bureau")
    s_map = C.Scene(c1, c2, d_map, p_map)

    # three pistols, smuggled in
    def p_guns(ctx):
        ctx["bg"] = dark_bg()
        ctx["gun"] = pistol_icon(300, (236, 226, 204))
        ctx["lab"] = glow(T("SMUGGLED IN BY JOHN DILLINGER", "bold", 34, BONE, tracking=3), (0, 0, 0), radius=14,
                          strength=0.9)

    def d_guns(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c3 - c2, z=(1.05, 1.1))
        dim(f, 0.7)
        bs.shade(f)
        paste(f, ctx["lab"], W / 2, 460, appear(t, t_smug - 0.5, 0.3))
        for i in range(3):
            a = appear(t, t_used + 0.5 + i * 0.35, 0.2)
            paste(f, ctx["gun"], 540, 640 + i * 190 - 20 * (1 - a), a)
        bs.title(f, "THREE PISTOLS", "bask", 96, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_used + 0.4, 0.25))
        bs.credit_line(f, "Drawn graphic")

    # Dillinger's timeline
    s_tl = card_scene(c3, c4, "JOHN DILLINGER", [
        ("— May 1933: paroled", t_may - 0.1),
        ("— Sept. 22: arrested in", t_arr - 1.0), ("  Dayton, Ohio", None),
        ("— Sept. 26: the break.", t_arr + 1.2), ("  He was not there.", None)],
        None, 91, date="1933", date_at=c3 + 0.05,
        over=stamp_over([("NOT", 100), ("THERE", 110)], t_arr + 2.5, 150),
        cred="Drawn graphic · typeset card")

    s_lima = card_scene(c4, c5, "OCT. 12, 1933", [
        ("— Harry Pierpont and", t_harry + 0.1), ("  Charles Makley, two of", None), ("  the ten, free Dillinger", None),
        ("  from the jail in", None), ("  Lima, Ohio", None),
        ("— Sheriff Jess Sarber", t_sher - 0.1), ("  is killed", None)],
        None, 93, date="LIMA, OHIO", date_at=c4 + 0.05, ytop=400,
        cred="Drawn graphic · typeset card")

    # how did the guns get in
    def p_thread(ctx):
        ctx["bg"] = dark_bg()
        S = 3
        w, h = 760, 560
        img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        wood, edge = (176, 138, 88, 255), (92, 66, 36, 255)

        def crate(x, y, cw, ch):
            d.rectangle((x * S, y * S, (x + cw) * S, (y + ch) * S), fill=wood, outline=edge, width=5 * S)
            for yy in range(y + ch // 3, y + ch, ch // 3):
                d.line((x * S, yy * S, (x + cw) * S, yy * S), fill=edge, width=3 * S)
            d.line((x * S, y * S, (x + cw) * S, (y + ch) * S), fill=edge, width=3 * S)
            d.line((x * S, (y + ch) * S, (x + cw) * S, y * S), fill=edge, width=3 * S)
        crate(20, 270, 330, 260)
        crate(380, 270, 330, 260)
        crate(200, 20, 330, 250)
        # a spool of thread beside the stack
        for i, c in enumerate(((224, 224, 232, 255), (176, 40, 40, 255), (224, 224, 232, 255))):
            pass
        ctx["crates"] = img.resize((w, h), Image.LANCZOS)
        sp = Image.new("RGBA", (200 * S, 240 * S), (0, 0, 0, 0))
        dd = ImageDraw.Draw(sp)
        dd.rounded_rectangle((20 * S, 10 * S, 180 * S, 40 * S), radius=8 * S, fill=wood, outline=edge, width=4 * S)
        dd.rounded_rectangle((20 * S, 200 * S, 180 * S, 230 * S), radius=8 * S, fill=wood, outline=edge, width=4 * S)
        dd.rectangle((40 * S, 40 * S, 160 * S, 200 * S), fill=(216, 60, 52, 255))
        for yy in range(48, 200, 12):
            dd.line((40 * S, yy * S, 160 * S, yy * S), fill=(150, 30, 30, 255), width=3 * S)
        ctx["spool"] = sp.resize((200, 240), Image.LANCZOS)
        ctx["lab"] = glow(T("NOT KNOWN FOR SURE", "bold", 36, BONE, tracking=4), (0, 0, 0), radius=14, strength=0.9)
        ctx["theory"] = glow(T("THE MOST BELIEVED THEORY", "bold", 34, BONE, tracking=4), (0, 0, 0), radius=14,
                             strength=0.9)

    def d_thread(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c6 - c5, z=(1.05, 1.1))
        dim(f, 0.7)
        bs.shade(f)
        paste(f, ctx["lab"], W / 2, 450, appear(t, t_how, 0.3) * (1 - appear(t, t_theory - 0.2, 0.2)))
        if t < t_theory - 0.2:
            q = appear(t, t_how + 0.1, 0.3)
            paste(f, T("?", "bask", 420, (222, 34, 30)), 540, 800, q * 0.95)
        else:
            a = appear(t, t_theory - 0.2, 0.3)
            paste(f, ctx["theory"], W / 2, 450, a)
            paste(f, ctx["crates"], 460, 790 + 20 * (1 - a), a)
            paste(f, ctx["spool"], 880, 910 + 20 * (1 - a), appear(t, t_thread - 0.4, 0.3))
        bs.title(f, "BOXES OF THREAD?" if t >= t_theory - 0.2 else "HOW DID THEY GET IN?", "bask", 88, BONE, 1205,
                 glow=(0, 0, 0), alpha=appear(t, t_how + 0.2, 0.25))
        bs.credit_line(f, "Drawn graphic · theory: shirt factory thread shipments (History.com, Wikipedia)")

    end = EndCard(dark_bg(), SRC + ["All pictures are drawn graphics"],
                  "The 1933 Prison Break")

    def d_end(f, u, t, ctx):
        end.draw(f, u, R.dur - c6)

    scenes = [C.Scene(0.0, c1, d_hook, p_hook), s_map, C.Scene(c2, c3, d_guns, p_guns), s_tl, s_lima,
              C.Scene(c5, c6, d_thread, p_thread), C.Scene(c6, R.dur + 1, d_end, None)]
    film = C.Film(R, scenes, flashes=[(0.35, 0.32)], label=label_fn("LA PORTE AFTER DARK · 1933", c1))
    ev = [("thunder", 0.33, 0.9), ("hit", t_three, 0.8), ("whoosh", c1, 0.7), ("type", c1 + 0.05, 0.9),
          ("pop", t_esc - 0.3, 0.8), ("whoosh", c2, 0.6), ("pop", t_used + 0.5, 0.6), ("pop", t_used + 0.85, 0.6),
          ("pop", t_used + 1.2, 0.6), ("whoosh", c3, 0.6), ("type", c3 + 0.05, 0.9), ("type", t_may - 0.1, 0.8),
          ("hit", t_arr + 2.4, 1.0), ("whoosh", c4, 0.6), ("type", t_harry + 0.1, 0.8), ("thud", t_sher, 0.7),
          ("whoosh", c5, 0.6), ("heartbeat", t_how, 0.7), ("pop", t_theory, 0.7), ("whoosh", c6, 0.6),
          ("pop", c6 + 0.3, 0.8)]
    return film, ev, "lullaby", "La Porte After Dark: The 1933 Prison Break"


BUILD = {"belle8": build_belle8, "belle7": build_belle7, "break33": build_break33}
FILES = {"belle8": "belle-gunness-part-8-the-woman-in-los-angeles.mp4",
         "belle7": "belle-gunness-part-7-the-only-man-convicted.mp4",
         "break33": "ten-men-three-pistols-1933-prison-break.mp4"}


def main(name, mode, times=None):
    R = C.Reel(name)
    film, ev, music, title = BUILD[name](R)
    if mode == "stills":
        ts = times or [round(R.dur * k / 18, 2) for k in range(18)]
        print(R.dur, film.stills([t for t in ts if t < R.dur], name))
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
    main(sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None)
