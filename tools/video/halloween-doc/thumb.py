#!/usr/bin/env python3
"""The YouTube thumbnails (1280x720) for the History of Halloween film: a 1900s postcard in full color on the
left, a big line on the right, and the film's red MYTH stamp slapped over it. Three variants for YouTube's
Test & Compare (Scoop picks):

    python3 tools/video/halloween-doc/thumb.py OUTDIR

  a: "EVERYTHING YOU KNOW ABOUT HALLOWEEN IS WRONG" with the MYTH stamp
  b: "THE REAL HISTORY OF HALLOWEEN" with a torn 1917 headline ("Tricks or treats")
  c: "TRICK OR TREAT BEGAN AS A THREAT" with the 1866 dead-cats line
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc  # noqa: E402

TW, TH = 1280, 720
CREAM = (244, 236, 214)
RED = (214, 44, 36)


def picture(name, crop=None, warm=1.15):
    im = Image.open(doc.img_path(name)).convert("RGB")
    if crop:
        x0, y0, x1, y1 = crop
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    im = ImageOps.autocontrast(im, cutoff=0.5)
    im = ImageEnhance.Color(im).enhance(warm)
    im = ImageEnhance.Contrast(im).enhance(1.12)
    return im


def scrap(text, by, w=520, rot=-4.0, seed=1):
    """A torn strip of old newsprint with a line of type on it."""
    t = doc.text(text, "old-b", 44, (30, 26, 22, 255))
    while t.width > w - 60:
        w += 40
    h = t.height + 56 + (36 if by else 0)
    paper = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rng = np.random.default_rng(seed)
    pts = []
    for x in range(0, w + 1, 24):                       # ragged top and bottom edges
        pts.append((x, int(rng.uniform(0, 9))))
    for x in range(w, -1, -24):
        pts.append((x, h - int(rng.uniform(0, 9))))
    ImageDraw.Draw(paper).polygon(pts, fill=(236, 226, 198, 255))
    grain = (rng.normal(0, 7, (h, w))).astype(np.int16)
    arr = np.asarray(paper).astype(np.int16)
    arr[..., :3] = np.clip(arr[..., :3] + grain[..., None], 0, 255)
    paper = Image.fromarray(arr.astype(np.uint8))
    paper.paste(t, ((w - t.width) // 2, 22), t)
    if by:
        b = doc.text(by, "inter-m", 22, (90, 80, 70, 255))
        paper.paste(b, ((w - b.width) // 2, 22 + t.height + 8), b)
    return paper.rotate(rot, expand=True, resample=Image.BICUBIC)


def shadowed(bg, img, x, y, radius=16):
    sh = doc.glow(img, (0, 0, 0), radius=radius, strength=1.0)
    bg.paste(sh, (x - (sh.width - img.width) // 2, y - (sh.height - img.height) // 2), sh)


def finish(bg, out):
    rng = np.random.default_rng(3)
    arr = np.asarray(bg, np.float32)
    arr += rng.normal(0, 4, arr.shape[:2])[..., None]
    yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
    dd = np.sqrt(((xx - TW / 2) / (TW * 0.66)) ** 2 + ((yy - TH / 2) / (TH * 0.66)) ** 2)
    arr *= np.clip(1.2 - dd * 0.45, 0.55, 1.0)[..., None]
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(out, quality=92)
    print("thumbnail", out)


def base(name, crop, left_w=0.56):
    bg = Image.new("RGB", (TW, TH), (14, 10, 8))
    p = picture(name, crop)
    k = max(TW * left_w / p.width, TH / p.height)
    p = p.resize((int(p.width * k), int(p.height * k)), Image.LANCZOS)
    p = p.crop((0, (p.height - TH) // 2, min(p.width, int(TW * left_w) + 120), (p.height - TH) // 2 + TH))
    m = np.ones((p.height, p.width), np.float32)
    xs = np.linspace(0, 1, p.width)[None, :]
    m *= np.clip((1.0 - xs) / 0.22, 0, 1) ** 1.2
    bg.paste(p, (0, 0), Image.fromarray((m * 255).astype(np.uint8)))
    return bg


def title_block(bg, lines, x_right=TW - 48, y=96, gap=6):
    for s, size, colr in lines:
        t = doc.text(s, "inter-b", size, colr + (255,), stroke=5, stroke_fill=(0, 0, 0))
        shadowed(bg, t, x_right - t.width, y, 14)
        y += t.height + gap
    return y


def make(outdir):
    os.makedirs(outdir, exist_ok=True)
    # a: the witch postcard, "EVERYTHING YOU KNOW ABOUT HALLOWEEN IS WRONG", the MYTH stamp
    bg = base("pc-witch-07.jpg", [0.0, 0.0, 0.72, 1.0], 0.52)
    y = title_block(bg, [("EVERYTHING", 92, CREAM), ("YOU KNOW ABOUT", 62, CREAM), ("HALLOWEEN", 104, (255, 196, 72)), ("IS WRONG", 104, CREAM)], y=70)
    st = doc.stamp_img("MYTH", "red", 140, -12.0)
    shadowed(bg, st, TW - 70 - st.width, 430, 18)
    sub = doc.text("THE REAL HISTORY · A LA PORTE WEATHER NOW FILM", "inter-b", 26, (226, 220, 206, 255), tracking=2, stroke=3)
    bg.paste(sub, (TW - 48 - sub.width, TH - 60), sub)
    finish(bg, os.path.join(outdir, "thumb-a.jpg"))

    # b: the devils-and-pumpkins postcard, "THE REAL HISTORY OF HALLOWEEN", the 1917 scrap
    bg = base("pc-jol-04.jpg", [0.0, 0.0, 1.0, 0.78], 0.52)
    y = title_block(bg, [("THE REAL", 84, CREAM), ("HISTORY OF", 84, CREAM), ("HALLOWEEN", 112, (255, 196, 72))], y=72)
    sc = scrap("“‘Tricks or treats’ you could hear the gangs call out.”", "The Sault Daily Star, Nov. 1, 1917", 640, -3.5, 2)
    shadowed(bg, sc, TW - 60 - sc.width, y + 20, 18)
    st = doc.stamp_img("WE CHECKED", "green", 72, -8.0)
    shadowed(bg, st, TW - 60 - st.width, TH - 150, 14)
    finish(bg, os.path.join(outdir, "thumb-b.jpg"))

    # c: the 1938 trick-or-treaters, "TRICK OR TREAT BEGAN AS A THREAT", the 1866 scrap
    bg = base("hw-us-16.jpg", None, 0.54)
    y = title_block(bg, [("TRICK OR TREAT", 92, (255, 196, 72)), ("BEGAN AS", 84, CREAM), ("A THREAT", 112, CREAM)], y=84)
    sc = scrap("“…hanging dead cats to door-bells.”", "Philadelphia, Oct. 31, 1866", 560, 3.0, 5)
    shadowed(bg, sc, TW - 60 - sc.width, y + 24, 18)
    finish(bg, os.path.join(outdir, "thumb-c.jpg"))


if __name__ == "__main__":
    doc.load_manifests()
    make(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
