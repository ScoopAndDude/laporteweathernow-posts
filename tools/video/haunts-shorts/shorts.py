#!/usr/bin/env python3
"""Three Shorts cut from the La Porte County hauntings documentary (Oct. 21, 2026; Scoop: "do all of these"), for
YouTube Shorts and TikTok, each pointing to the full documentary on YouTube.

    python3 tools/video/haunts-shorts/shorts.py OUTDIR [flagman lightning-bug keeper] [--stills | --at=1.0,5.5]

- flagman: the 1905 newspaper stories of a headless ghost flagging trains near La Porte.
- lightning-bug: Charles Cathcart's "lightning bug" and the drum that, he wrote, no one was playing.
- keeper: Harriet Colfax, who kept the Michigan City light for 43 years.

1080x1920, 30 fps, H.264 + AAC 48 kHz, made the same way as the Belle Gunness Halloween shorts (base.py): the
hook on screen in the first frame, captions that follow the narrator word by word, a new picture every few
seconds. The narration (lines.json) is the documentary's voice, recorded by voice.py in GitHub Actions. Every
picture is a real one from the documentary (tools/video/haunts-doc/images: public domain, CC0 or CC BY, each
CC BY one credited on screen); no stock footage or AI pictures. Music and sounds are written in code.
"""
import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import base as B  # noqa: E402
from base import (BONE, CW, INKC, SR, W, H, Scene, T, appear, credit, env_ar, fitT, glowT, kenburns,  # noqa: E402
                  lightning, lowpass, paste_c, shade, soft_dot, title, vr, word_at)

GOLD = (255, 196, 92)
RED = (232, 52, 40)
CYAN = (120, 214, 228)
LORA_IT = "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf"


# ---------------------------------------------------------------------------------------------
# The voice: years in the captions as numerals (the narrator says them in words)
# ---------------------------------------------------------------------------------------------
def _norm(s):
    return re.sub(r"[^a-z0-9-]", "", s.lower())


def numerals_in_captions():
    """Lines with "tts" were spoken with years in words ("nineteen oh five"); show them as "1905" again."""
    import json
    sys.path.insert(0, B.DOCDIR)
    import script  # the documentary's year_words / spoken
    lines = json.load(open(os.path.join(HERE, "lines.json"), encoding="utf-8"))["lines"]
    for ln in lines:
        if not ln.get("tts") or ln["id"] not in B.LINES:
            continue
        words = B.LINES[ln["id"]]["words"]
        for m in re.finditer(r"\b(1[89]\d0s|1[89]\d\d|20[0-2]\d)\b", ln["say"]):
            spoken = [_norm(w) for w in script.spoken(m.group(0)).split()]
            for i in range(len(words) - len(spoken) + 1):
                if [_norm(w[0]) for w in words[i:i + len(spoken)]] == spoken:
                    words[i:i + len(spoken)] = [[m.group(0), words[i][1], words[i + len(spoken) - 1][2]]]
                    break


# ---------------------------------------------------------------------------------------------
# Pictures
# ---------------------------------------------------------------------------------------------
def pic(f, tone="sepia", inset=0.0, crop=None):
    im = Image.open(os.path.join(B.IMGDIR, f)).convert("RGB")
    if crop:
        x0, y0, x1, y1 = crop
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    if inset:
        dx, dy = int(im.width * inset), int(im.height * inset)
        im = im.crop((dx, dy, im.width - dx, im.height - dy))
    if tone == "paper":
        g = ImageOps.autocontrast(im.convert("L"), cutoff=0.6)
        im = ImageOps.colorize(g, black=(30, 24, 18), mid=(140, 122, 96), white=(236, 222, 192))
    elif tone == "sepia":
        g = ImageEnhance.Contrast(ImageOps.autocontrast(im.convert("L"), cutoff=1)).enhance(1.12)
        im = ImageOps.colorize(g, black=(12, 9, 7), mid=(118, 94, 68), white=(238, 218, 180))
    elif tone in ("night", "night-lift"):
        if tone == "night-lift":                     # a dark picture: stretch and lift it first
            im = ImageOps.autocontrast(im, cutoff=0.8)
            im = Image.eval(im, lambda v: int(255 * (v / 255) ** 0.7))
        im = ImageEnhance.Color(im).enhance(0.3)
        im = ImageEnhance.Brightness(im).enhance(0.62)
        im = ImageEnhance.Contrast(im).enhance(1.22)
        arr = np.asarray(im, np.float32) * np.array([0.70, 0.86, 1.10], np.float32)
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    elif tone == "dusk":                             # a color postcard, a little darker and quieter
        im = ImageEnhance.Brightness(ImageEnhance.Color(im).enhance(0.85)).enhance(0.82)
    return im.convert("RGBA")


def cover(im, fx=0.5, fy=0.5, blur=0, bright=1.0):
    """The picture filling the frame (for a still background)."""
    out = ImageOps.fit(im.convert("RGB"), (W, H), Image.LANCZOS, centering=(fx, fy))
    if blur:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    if bright != 1.0:
        out = ImageEnhance.Brightness(out).enhance(bright)
    return out.convert("RGBA")


def shadowed(img, radius=18, alpha=0.75, offset=(6, 14)):
    pad = radius * 3
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    blk = Image.new("RGBA", img.size, (0, 0, 0, 255))
    blk.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    out.alpha_composite(blk, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(radius))
    out.alpha_composite(img, (pad, pad))
    return out


def clipping(f, width, tone="paper", rot=-1.0, seed=3, crop=None):
    """A newspaper cut-out with torn-looking edges and a shadow, ready to lay on the desk."""
    im = pic(f, tone, crop=crop).convert("RGB")
    k = width / im.width
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS).convert("RGBA")
    rng = np.random.default_rng(seed)
    w, h = im.size
    pts = [(x, rng.uniform(0, 7)) for x in range(0, w, 9)] + [(w - rng.uniform(0, 7), y) for y in range(0, h, 9)]
    pts += [(x, h - rng.uniform(0, 7)) for x in range(w, 0, -9)] + [(rng.uniform(0, 7), y) for y in range(h, 0, -9)]
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    im.putalpha(mask)
    return shadowed(im.rotate(rot, resample=Image.BICUBIC, expand=True))


def push(frame, img, u, dur, cx, cy, z=(1.0, 1.06), alpha=1.0):
    """A card held on screen and slowly pushed in."""
    k = min(1.0, max(0.0, u / max(0.1, dur)))
    k = k * k * (3 - 2 * k)
    s = z[0] + (z[1] - z[0]) * k
    out = img if abs(s - 1) < 1e-3 else img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)
    paste_c(frame, out, cx, cy, alpha)


def dim(frame, rect, amt, feather=28):
    """Darken everything but rect (screen pixels), the lines being read."""
    x0, y0, x1, y1 = rect
    xs = np.arange(W, dtype=np.float32)
    ys = np.arange(H, dtype=np.float32)
    dx = np.maximum(np.maximum(x0 - xs, xs - x1), 0)[None, :]
    dy = np.maximum(np.maximum(y0 - ys, ys - y1), 0)[:, None]
    inside = np.clip(1 - np.sqrt(dx * dx + dy * dy) / feather, 0, 1)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov.putalpha(Image.fromarray((amt * (1 - inside) * 255).astype(np.uint8), "L"))
    frame.alpha_composite(ov)


class Page:
    """A newspaper column or book page seen through a moving camera; boxes are fractions of the page."""

    def __init__(self, f, tone="paper", pad=0.7):
        im = pic(f, tone).convert("RGB")
        self.w0, self.h0 = im.size
        self.px, self.py = int(im.width * pad), int(im.height * pad)
        self.im = Image.new("RGB", (im.width + 2 * self.px, im.height + 2 * self.py), (12, 10, 8))
        self.im.paste(im, (self.px, self.py))

    def rect(self, box, across=0.92, cy=0.5):
        """The camera rectangle that shows the box's width across `across` of the screen, its middle at cy."""
        x0, y0, x1, y1 = box
        bw = (x1 - x0) * self.w0 / across
        bh = bw * H / W
        cx = self.px + (x0 + x1) / 2 * self.w0
        my = self.py + (y0 + y1) / 2 * self.h0
        return (cx - bw / 2, my - bh * cy, cx + bw / 2, my + bh * (1 - cy))

    def draw(self, frame, ra, rb, k, spot=None, spot_k=0.0):
        k = max(0.0, min(1.0, k))
        k = k * k * (3 - 2 * k)
        wa, wb = ra[2] - ra[0], rb[2] - rb[0]
        w = math.exp(math.log(wa) + (math.log(wb) - math.log(wa)) * k)
        kk = (wa - w) / (wa - wb) if abs(wa - wb) > 1e-6 else k
        cx = (ra[0] + ra[2]) / 2 * (1 - kk) + (rb[0] + rb[2]) / 2 * kk
        cy = (ra[1] + ra[3]) / 2 * (1 - kk) + (rb[1] + rb[3]) / 2 * kk
        h = w * H / W
        box = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
        box = [max(0.0, box[0]), max(0.0, box[1]), min(self.im.width, box[2]), min(self.im.height, box[3])]
        frame.alpha_composite(self.im.resize((W, H), Image.BICUBIC, box=tuple(box)).convert("RGBA"))
        if spot and spot_k > 0.004:
            s = W / (box[2] - box[0])
            r = ((self.px + spot[0] * self.w0 - box[0]) * s, (self.py + spot[1] * self.h0 - box[1]) * s,
                 (self.px + spot[2] * self.w0 - box[0]) * s, (self.py + spot[3] * self.h0 - box[1]) * s)
            dim(frame, (r[0] - 10, r[1] - 8, r[2] + 10, r[3] + 8), 0.66 * spot_k)


def label(frame, text, y=284, color=BONE):
    img = fitT(text, "bold", 34, color + (255,), max_w=CW, min_size=24, tracking=4)
    pill = Image.new("RGBA", (img.width + 44, img.height + 26), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle((0, 0, pill.width - 1, pill.height - 1), radius=pill.height // 2, fill=(8, 8, 10, 150))
    pill.alpha_composite(img, (22, 13))
    paste_c(frame, pill, W / 2, y)


def note(frame, text, y=1478):
    """A small line under the captions: a picture's credit, or what the picture is."""
    if text:
        img = fitT(text, "semi", 25, (235, 235, 235, 235), max_w=CW + 20, min_size=18, stroke=2, stroke_fill=(0, 0, 0))
        frame.alpha_composite(img, (B.X0 - 10, y))


def flash_over(frame, k):
    if k > 0.02:
        frame.alpha_composite(Image.new("RGBA", (W, H), (226, 232, 255, int(min(1.0, k) * 210))))


def paper_card(lines, w=880, seed=5):
    """An old sheet of paper with a few lines on it (a log entry, a quote)."""
    rows = []                                        # (text, font, line height)
    for text, size, italic in lines:
        f = ImageFont.truetype(LORA_IT if italic else B.LORA, size)
        f.set_variation_by_name(b"Italic" if italic else b"Bold")
        line = ""
        for wd in text.split():
            cand = (line + " " + wd).strip()
            if f.getlength(cand) > w - 110 and line:
                rows.append((line, f, int(size * 1.45)))
                line = wd
            else:
                line = cand
        rows.append((line, f, int(size * 1.45)))
    hh = 50 + sum(r[2] for r in rows) + 45
    p = B.aged_paper(w, hh, seed=seed)
    d = ImageDraw.Draw(p)
    y = 50
    for text, f, lh in rows:
        d.text((55, y), text, font=f, fill=INKC + (255,))
        y += lh
    return shadowed(p.rotate(-0.8, resample=Image.BICUBIC, expand=True))


# ---------------------------------------------------------------------------------------------
# The ending, the same in all three: the documentary's thumbnail and where to find it
# ---------------------------------------------------------------------------------------------
def pp_end(ctx):
    ctx["end_bg"] = cover(pic("lh-cards-03.jpg", "night", inset=0.04), fx=0.38, fy=0.45, blur=10, bright=0.55)
    th = Image.open(os.path.join(HERE, "doc-thumb.jpg")).convert("RGBA")
    tw = 940
    th = th.resize((tw, int(th.height * tw / th.width)), Image.LANCZOS)
    card = Image.new("RGBA", (th.width + 14, th.height + 14), (236, 230, 216, 255))
    card.alpha_composite(th, (7, 7))
    d = ImageDraw.Draw(card)
    cx, cy, r = card.width // 2, card.height // 2, 62           # a plain play button
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(0, 0, 0, 150))
    d.polygon([(cx - 20, cy - 32), (cx - 20, cy + 32), (cx + 36, cy)], fill=(255, 255, 255, 235))
    ctx["thumb"] = shadowed(card)
    ctx["end_credit"] = credit("lh-cards-03.jpg")


def p_end(frame, u, words, ctx):
    frame.alpha_composite(ctx["end_bg"])
    title(frame, "WATCH THE FULL DOCUMENTARY", "black", 56, BONE, 450, glow=(0, 0, 0), alpha=appear(u, 0.0, 0.2))
    push(frame, ctx["thumb"], u, 4.0, W / 2, 790, z=(0.96, 1.0), alpha=appear(u, 0.05, 0.25))
    title(frame, "on YouTube · 20 minutes", "bold", 44, (226, 220, 206), 1130, alpha=appear(u, 0.3, 0.3))
    note(frame, "Thumbnail: " + ctx["end_credit"].replace("Photo: ", "postcard by ") if ctx["end_credit"] else "")


# ---------------------------------------------------------------------------------------------
# 1. The headless flagman (1905)
# ---------------------------------------------------------------------------------------------
GHOST_A = [0.2105, 0.1750, 0.8789, 0.2386]     # np-ghost-03-col: run over by an engine near the water tank
GHOST_B = [0.1674, 0.6769, 0.8372, 0.7411]     # np-ghost-04-b: a boiler explosion


LOCO = [0.050, 0.405, 0.482, 0.985]             # rail-tank-02: the head-on photo, bottom left of the page


def pp_flag(ctx):
    ctx["desk"] = cover(pic("rail-tank-02.jpg", "night-lift", crop=LOCO), fx=0.5, fy=0.45, blur=8, bright=0.5)
    ctx["head"] = clipping("np-ghost-04-head.jpg", 720, rot=-1.4, seed=4)
    ctx["drawing"] = clipping("np-ghost-04-drawing.jpg", 700, rot=1.0, seed=7)
    ctx["panic"] = Page("np-ghost-01-col.jpg")
    ctx["loco"] = pic("rail-tank-02.jpg", "night-lift", crop=LOCO)
    pad = lambda b, dx, dy: [b[0] - dx, b[1] - dy, b[2] + dx, b[3] + dy]
    ctx["cole_a"] = clipping("np-ghost-03-col.jpg", 860, rot=-1.0, seed=11, crop=pad(GHOST_A, 0.02, 0.006))
    ctx["cole_b"] = clipping("np-ghost-04-b.jpg", 860, rot=0.8, seed=12, crop=pad(GHOST_B, 0.02, 0.005))
    pp_end(ctx)


def f1(frame, u, words, ctx):
    frame.alpha_composite(ctx["desk"])
    push(frame, ctx["head"], u, 6.0, W / 2, 735, z=(1.0, 1.07))
    shade(frame)
    label(frame, "LA PORTE, INDIANA · 1905")
    note(frame, "Barbour County Index, Medicine Lodge, Kan., Aug. 16, 1905 · Library of Congress")


def f2(frame, u, words, ctx):
    frame.alpha_composite(ctx["desk"])
    push(frame, ctx["drawing"], u, 6.0, W / 2, 735, z=(1.0, 1.08))
    shade(frame)
    label(frame, "A NEWSPAPER DRAWING · 1905")
    note(frame, "“The Headless Apparition,” Barbour County Index, 1905 · Library of Congress")


def f3(frame, u, words, ctx):
    pg = ctx["panic"]
    ra = pg.rect([0.06, 0.03, 0.72, 0.24], across=0.94, cy=0.42)
    rb = pg.rect([0.06, 0.55, 0.72, 0.71], across=0.94, cy=0.45)
    two = word_at(words, "Two", 0.0)
    pg.draw(frame, ra, rb, (u - two - 0.2) / 1.6, spot=[0.06, 0.552, 0.71, 0.708], spot_k=appear(u, two + 1.9, 0.5))
    shade(frame)
    label(frame, "THE VIRGINIA ENTERPRISE · JULY 7, 1905")
    note(frame, "The Virginia Enterprise, Virginia, Minn., July 7, 1905 · Library of Congress")


def f4(frame, u, words, ctx):
    agree = word_at(words, "agree", 4.5)
    kenburns(frame, ctx["loco"], u, 8.0, z=(1.0, 1.12), f0=(0.55, 0.42), f1=(0.50, 0.40))
    if u >= agree - 0.2:
        frame.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(150 * appear(u, agree - 0.2, 0.3)))))
    shade(frame)
    cole = word_at(words, "Cole", 1.0)
    if u < agree - 0.2:
        if u >= cole - 0.1:
            title(frame, "COLUMBUS COLE?", "bask", 104, BONE, 760, glow=(0, 0, 0), alpha=appear(u, cole - 0.1, 0.2))
        note(frame, "A locomotive, 1909 (public domain)")
    else:
        a = appear(u, agree - 0.15, 0.25)
        b = appear(u, agree + 0.35, 0.25)
        push(frame, ctx["cole_a"], u - agree, 3.0, W / 2, 560 + 30 * (1 - a), z=(1.0, 1.03), alpha=a)
        paste_c(frame, T("OR", "black", 64, RED + (255,), stroke=4), W / 2, 790, b)
        push(frame, ctx["cole_b"], u - agree, 3.0, W / 2, 1010 + 30 * (1 - b), z=(1.0, 1.03), alpha=b)
        note(frame, "Indianapolis Sentinel, in the New Haven Journal and Courier, Aug. 14 · Barbour County Index, Aug. 16")
    label(frame, "WHO WAS THE GHOST?")


# ---------------------------------------------------------------------------------------------
# 2. Cathcart's lightning bug (the 1850s)
# ---------------------------------------------------------------------------------------------
def pp_cath(ctx):
    ctx["seance"] = pic("seance-23.jpg", "night", inset=0.03)
    ctx["h07"] = Page("hardinge-07.jpg")
    ctx["h08"] = Page("hardinge-08.jpg")
    ctx["table"] = pic("table-turning-27.jpg", "sepia", inset=0.03)
    ctx["table_n"] = pic("table-turning-27.jpg", "night", inset=0.03)
    ctx["reg"] = Page("register1859-01.jpg")
    pp_end(ctx)


def g1(frame, u, words, ctx):
    kenburns(frame, ctx["seance"], u, 7.0, z=(1.15, 1.32), f0=(0.42, 0.52), f1=(0.47, 0.54))
    shade(frame)
    label(frame, "LA PORTE, INDIANA · THE 1850s")
    title(frame, "THE SPIRIT ROOM", "bask", 112, BONE, 1205, glow=(0, 0, 0))
    note(frame, "A séance photo, 1909 · Bain News Service (public domain)")


def g2(frame, u, words, ctx):
    pg = ctx["h07"]
    ra = pg.rect([0.10, 0.40, 0.96, 0.66], across=0.96, cy=0.46)
    rb = pg.rect([0.12, 0.47, 0.94, 0.60], across=0.96, cy=0.46)
    pg.draw(frame, ra, rb, u / 2.5, spot=[0.13, 0.480, 0.93, 0.590], spot_k=appear(u, 1.4, 0.5))
    shade(frame)
    bug = word_at(words, "lightning", 99.0)
    if u < bug - 0.1:
        label(frame, "CHARLES W. CATHCART")
    else:
        g = T("HIS “LIGHTNING BUG”", "bask", 84, GOLD + (255,))
        gg, _ = glowT(g, (255, 150, 30), radius=28, strength=0.8)
        paste_c(frame, gg, W / 2, 330, appear(u, bug - 0.1, 0.2))
    note(frame, "His account, in Emma Hardinge, Modern American Spiritualism, 1870 (public domain)")


def g3(frame, u, words, ctx):
    out = word_at(words, "out", 0.8)
    drum = word_at(words, "drum", 1.8)
    table = word_at(words, "table", 3.8)
    if u < table:                                    # the room, then the lights go out (just shapes left)
        beat = 0
        for k in range(3):
            if 0 <= u - (drum + 0.42 * k) < 0.12:
                beat = 1
        j = 0.004 * beat * (1 if int(u * 40) % 2 else -1)       # the drum shakes the room a little
        kenburns(frame, ctx["seance"], u + 7, 9.0, z=(1.15, 1.32), f0=(0.42 + j, 0.52), f1=(0.47 + j, 0.54))
        dark = 238 * min(1.0, u / max(0.2, out))
        frame.alpha_composite(Image.new("RGBA", (W, H), (2, 2, 4, int(dark))))
        if beat:
            frame.alpha_composite(soft_dot(240, (90, 70, 50), 60), (W // 2 - 480, 700 - 480))
    else:                                            # the lightning bug goes off
        k = min(1.0, (u - table) / 1.4)
        kenburns(frame, ctx["table"], u - table, 3.0, z=(1.10, 1.16), f0=(0.55, 0.50), f1=(0.55, 0.48))
        night = B.vr.with_alpha(ctx["table_n"], k) if k < 1 else ctx["table_n"]
        if k > 0:
            kenburns(frame, night, u - table, 3.0, z=(1.10, 1.16), f0=(0.55, 0.50), f1=(0.55, 0.48))
        flash_over(frame, lightning(u, table, length=0.5) * 1.1)
        note(frame, "A séance photo, 1909 · Bain News Service (public domain)")
    shade(frame)
    if out <= u < table:
        label(frame, "THE LIGHTS WENT OUT")


def g4(frame, u, words, ctx):
    pg = ctx["h08"]
    ra = pg.rect([0.03, 0.19, 0.88, 0.355], across=0.96, cy=0.46)
    rb = pg.rect([0.03, 0.27, 0.87, 0.34], across=0.96, cy=0.46)
    pg.draw(frame, ra, rb, u / 2.2, spot=[0.03, 0.294, 0.87, 0.324], spot_k=appear(u, 1.2, 0.5))
    shade(frame)
    label(frame, "IN HIS OWN WORDS")
    note(frame, "His account, in Emma Hardinge, Modern American Spiritualism, 1870 (public domain)")


def g5(frame, u, words, ctx):
    full = word_at(words, "full", 2.0)
    if u >= full - 0.15:
        p_end(frame, u - full + 0.15, words, ctx)
        return
    pg = ctx["reg"]
    ra = pg.rect([0.08, 0.28, 0.86, 0.44], across=0.94, cy=0.46)
    rb = pg.rect([0.20, 0.34, 0.86, 0.41], across=0.94, cy=0.46)
    pg.draw(frame, ra, rb, u / 1.5, spot=[0.37, 0.371, 0.80, 0.391], spot_k=appear(u, 0.5, 0.4))
    shade(frame)
    label(frame, "THE SPIRITUALIST REGISTER · 1858")
    title(frame, "“CATHCART'S SPIRIT ROOM”", "bask", 78, GOLD, 1205, glow=(0, 0, 0), alpha=appear(u, 0.3, 0.3))


# ---------------------------------------------------------------------------------------------
# 3. The keeper (Michigan City, 1861-1904)
# ---------------------------------------------------------------------------------------------
LANTERN_03 = (0.386, 0.402)    # the light on the 1933 night postcard (after the 4% inset)
LANTERN_OLD = (0.452, 0.190)   # the old lighthouse's lantern, 2007 photo


def pp_keep(ctx):
    ctx["night"] = pic("lh-cards-03.jpg", "dusk", inset=0.04)
    ctx["night_credit"] = credit("lh-cards-03.jpg")
    ctx["pier"] = pic("lh-cards-01.jpg", "sepia", inset=0.02)
    ctx["rough"] = pic("mc-lake-08.jpg", "sepia", inset=0.02)
    ctx["pier_credit"] = credit("lh-cards-01.jpg")
    ctx["rough_credit"] = credit("mc-lake-08.jpg")
    ctx["lights"] = pic("lhx-cat-05.jpg", "sepia", crop=[0.28, 0.31, 0.73, 0.69])
    ctx["old"] = pic("lh-old-01.jpg", "night")
    ctx["old_credit"] = credit("lh-old-01.jpg")
    ctx["log"] = paper_card([("May 28, 1873.", 46, True),
                             ("A terrible hurricane to-night at about the time of lighting up. "
                              "Narrowly escaped being swept into the lake.", 44, True)], w=880, seed=21)
    ctx["quote"] = paper_card([("“I could not bear to see anyone else light my lamp.”", 58, True),
                               ("Harriet Colfax, quoted in the Chicago Daily Tribune, Oct. 2, 1904", 30, False)], w=900, seed=23)
    pp_end(ctx)


def lamp(frame, x, y, k, flicker_t=None):
    if k <= 0.01:
        return
    if flicker_t is not None:
        k *= 0.75 + 0.25 * math.sin(flicker_t * 9.0) * math.sin(flicker_t * 3.7 + 1.0)
    frame.alpha_composite(soft_dot(70, (255, 214, 140), int(150 * k)), (int(x - 140), int(y - 140)))
    frame.alpha_composite(soft_dot(18, (255, 246, 220), int(255 * k)), (int(x - 36), int(y - 36)))


def k1(frame, u, words, ctx):
    to = kenburns(frame, ctx["night"], u, 7.5, z=(1.0, 1.08), f0=(0.30, 0.42), f1=(0.40, 0.44))
    lit = word_at(words, "lit", 5.5)
    lamp(frame, *to(*LANTERN_03), 0.35 + 0.65 * appear(u, lit - 0.2, 0.4), flicker_t=u)
    shade(frame)
    label(frame, "MICHIGAN CITY, INDIANA · 1861–1904")
    title(frame, "THE KEEPER WHO NEVER LEFT?", "bask", 84, BONE, 1205, glow=(0, 0, 0))
    note(frame, ctx["night_credit"] + " · Michigan City, a 1933 postcard")


def k2(frame, u, words, ctx):
    once = word_at(words, "Once", 4.0)
    if u < once - 0.1:
        kenburns(frame, ctx["pier"], u, once, z=(1.0, 1.05), f0=(0.78, 0.50), f1=(0.30, 0.48))
        shade(frame)
        hc = word_at(words, "Harriet", 0.0)
        title(frame, "HARRIET COLFAX", "bask", 104, BONE, 1205, glow=(0, 0, 0), alpha=appear(u, hc - 0.1, 0.25))
        label(frame, "THE PIER LIGHT")
        note(frame, ctx["pier_credit"] + " · the pier and its walkway, 1911")
    else:
        v = u - once + 0.1
        kenburns(frame, ctx["rough"], v, 5.0, z=(1.0, 1.10), f0=(0.40, 0.42), f1=(0.55, 0.40))
        shade(frame)
        push(frame, ctx["log"], v, 5.0, W / 2, 760, z=(1.0, 1.04), alpha=appear(v, 0.15, 0.3))
        label(frame, "FROM HER LOG")
        note(frame, ctx["rough_credit"] + " · a rough day on Lake Michigan, 1910")
        flash_over(frame, lightning(v, 0.0, length=0.45) * 0.9)


def k3(frame, u, words, ctx):
    quoted = word_at(words, "quoted", 3.0)
    kenburns(frame, ctx["lights"], u, 9.0, z=(1.0, 1.10), f0=(0.62, 0.45), f1=(0.66, 0.40))
    if u >= quoted - 0.2:
        frame.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(120 * appear(u, quoted - 0.2, 0.3)))))
    shade(frame)
    if u < quoted - 0.2:
        label(frame, "OCTOBER 1904")
        title(frame, "SHE RETIRED AT ABOUT 80", "bask", 84, BONE, 1205, glow=(0, 0, 0), alpha=appear(u, 0.6, 0.3))
    else:
        push(frame, ctx["quote"], u - quoted, 5.0, W / 2, 760, z=(1.0, 1.04), alpha=appear(u, quoted - 0.15, 0.3))
    note(frame, "Michigan City's lights, 1917 · U.S. Lighthouse Service (public domain)")


def k4(frame, u, words, ctx):
    dark = word_at(words, "dark", 2.0)
    watch = word_at(words, "watch", 5.5)
    to = kenburns(frame, ctx["old"], u, 7.0, z=(1.05, 1.22), f0=(0.47, 0.40), f1=(0.46, 0.25))
    x, y = to(*LANTERN_OLD)
    on = 1.0 - appear(u, dark - 0.1, 0.5)
    lamp(frame, x, y, on)
    if u >= watch - 0.3:                              # a faint light comes back, as the story goes
        lamp(frame, x, y, 0.45 * appear(u, watch - 0.3, 0.8), flicker_t=u)
    shade(frame)
    if u < watch - 0.3:
        label(frame, "OCTOBER 1904")
        title(frame, "THE LIGHT WENT OUT", "bask", 92, BONE, 1205, glow=(0, 0, 0), alpha=appear(u, dark - 0.1, 0.3))
    else:
        label(frame, "THE OLD LIGHTHOUSE, MICHIGAN CITY")
        title(frame, "STILL KEEPING WATCH?", "bask", 92, BONE, 1205, glow=(0, 0, 0), alpha=appear(u, watch - 0.3, 0.3))
    note(frame, ctx["old_credit"] + " · the old lighthouse, now a museum")


# ---------------------------------------------------------------------------------------------
# Sounds added for these three (the rest are the Belle shorts' sounds)
# ---------------------------------------------------------------------------------------------
_base_sfx = B.sfx


def sfx(kind, rng):
    if kind == "wail":                                # three long, falling cries
        n = int(2.6 * SR)
        x = np.zeros(n, np.float32)
        for st in (0.0, 0.75, 1.5):
            d = 0.7
            m = int(d * SR)
            tt = np.arange(m) / SR
            f = (520 + 360 * np.sin(np.pi * tt / d)) * (1 + 0.025 * np.sin(2 * np.pi * 6 * tt))
            ph = 2 * np.pi * np.cumsum(f) / SR
            tone = np.sin(ph) + 0.35 * np.sin(2 * ph + 0.3)
            i = int(st * SR)
            x[i:i + m] += (tone * np.sin(np.pi * tt / d) ** 1.5 * 0.2).astype(np.float32)
        return x + lowpass(rng.normal(0, 1, n).astype(np.float32), 40) * 0.25 * env_ar(n, 0.2, 0.8)
    if kind == "drum3":                               # a bass drum, three beats
        n = int(1.6 * SR)
        x = np.zeros(n, np.float32)
        for st in (0.0, 0.42, 0.84):
            m = int(0.5 * SR)
            tt = np.arange(m) / SR
            f = 55 * (1 + 1.2 * np.exp(-tt / 0.03))
            hit = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.22)
            thump = lowpass(rng.normal(0, 1, m).astype(np.float32), 25) * np.exp(-tt / 0.03) * 0.5
            i = int(st * SR)
            x[i:i + m] += ((hit + thump) * 0.85).astype(np.float32)
        return x
    if kind == "flare":                               # the lightning bug going off
        n = int(1.2 * SR)
        tt = np.arange(n) / SR
        noise = rng.normal(0, 1, n).astype(np.float32)
        burst = (noise - lowpass(noise, 4)) * np.exp(-tt / 0.09) * 0.8
        body = lowpass(noise, 60) * np.exp(-tt / 0.35) * 3
        crack = np.zeros(n, np.float32)
        for _ in range(28):
            i = int(rng.uniform(0, 0.9) * SR)
            m = 200
            crack[i:i + m] += rng.normal(0, 1, m).astype(np.float32) * np.exp(-np.arange(m) / 30) * rng.uniform(0.2, 0.6)
        return (burst + body + crack * np.exp(-tt / 0.5)) * 0.6
    if kind == "waves":                               # surf on the lake
        n = int(12 * SR)
        t = np.arange(n) / SR
        noise = rng.normal(0, 1, n).astype(np.float32)
        swell = (0.45 + 0.55 * np.sin(2 * np.pi * 0.13 * t - 1.2) ** 2).astype(np.float32)
        surf = lowpass(noise, 260) * 6 * swell + (noise - lowpass(noise, 7)) * 0.05 * swell
        return surf * env_ar(n, 1.0, 2.0) * 0.6
    return _base_sfx(kind, rng)


B.sfx = sfx
B.BED_FX = ("fire", "heartbeat", "thunder", "waves")


# ---------------------------------------------------------------------------------------------
# The three shorts
# ---------------------------------------------------------------------------------------------
B.SHORTS.update({
    "flagman": {"theme": "photo-night", "music": "drone", "scenes": [
        Scene("f1", f1, pp_flag, sfx=[("whistle", 0.05)], lead=0.0),
        Scene("f2", f2, pp_flag, sfx=[("whoosh", 0.0)]),
        Scene("f3", f3, pp_flag, sfx=[("whoosh", 0.0), ("wail", "shrieks")]),
        Scene("f4", f4, pp_flag, sfx=[("thud", "Cole"), ("hit", "agree")]),
        Scene("f5", p_end, pp_flag, sfx=[("whoosh", 0.0)], gap=0.9)]},
    "lightning-bug": {"theme": "photo-night", "music": "lullaby", "scenes": [
        Scene("g1", g1, pp_cath, sfx=[("whoosh", 0.0), ("heartbeat", 0.3)], lead=0.0),
        Scene("g2", g2, pp_cath, sfx=[("whoosh", 0.0)]),
        Scene("g3", g3, pp_cath, sfx=[("drum3", "drum"), ("flare", "table")]),
        Scene("g4", g4, pp_cath, sfx=[("whoosh", 0.0)]),
        Scene("g5", g5, pp_cath, sfx=[("hit", "believer"), ("whoosh", "full")], gap=0.9)]},
    "keeper": {"theme": "photo-night", "music": "lullaby", "scenes": [
        Scene("k1", k1, pp_keep, sfx=[("waves", 0.0)], lead=0.0),
        Scene("k2", k2, pp_keep, sfx=[("thunder", "Once"), ("waves", "swept")]),
        Scene("k3", k3, pp_keep, sfx=[("whoosh", "quoted")]),
        Scene("k4", k4, pp_keep, sfx=[("thud", "dark"), ("heartbeat", "watch")]),
        Scene("k5", p_end, pp_keep, sfx=[("whoosh", 0.0)], gap=0.9)]},
})
B.PREFIX = "lpwn-haunted-"

# Every picture each short shows (for the post's credits)
CREDITS = {
    "flagman": ["np-ghost-04-head.jpg", "np-ghost-04-drawing.jpg", "np-ghost-01-col.jpg", "rail-tank-02.jpg",
                "np-ghost-03-col.jpg", "np-ghost-04-b.jpg", "lh-cards-03.jpg"],
    "lightning-bug": ["seance-23.jpg", "hardinge-07.jpg", "table-turning-27.jpg", "hardinge-08.jpg", "register1859-01.jpg",
                      "lh-cards-03.jpg"],
    "keeper": ["lh-cards-03.jpg", "lh-cards-01.jpg", "mc-lake-08.jpg", "lhx-cat-05.jpg", "lh-old-01.jpg"],
}


if __name__ == "__main__":
    B.load_voice()
    numerals_in_captions()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    outdir, names = args[0], (args[1:] or list(B.SHORTS))
    at = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--at=")), None)
    for name in names:
        stills = [float(x) for x in at.split(",")] if at else ("--stills" in sys.argv)
        print("\n".join(B.render(name, outdir, stills=stills)))
