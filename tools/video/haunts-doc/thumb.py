#!/usr/bin/env python3
"""The YouTube thumbnail (1280x720): the old Michigan City lighthouse at night on the left, the title on the right.

    python3 tools/video/haunts-doc/thumb.py OUT.jpg PICTURE [crop x0,y0,x1,y1] [variant]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc  # noqa: E402

TW, TH = 1280, 720


def night(name, crop=None):
    """The picture as a cold, moonlit night: dark blue-gray, with the sky darkened from the top."""
    im = Image.open(doc.img_path(name)).convert("L")
    if crop:
        x0, y0, x1, y1 = crop
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    im = ImageOps.autocontrast(im, cutoff=1.0)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    col = ImageOps.colorize(im, black=(4, 6, 9), mid=(58, 74, 86), white=(206, 222, 226))
    return col


def make(out, name, crop=None, variant="a"):
    bg = Image.new("RGB", (TW, TH), (6, 8, 10))
    p = night(name, crop)
    k = max(TW * 0.78 / p.width, TH / p.height)
    p = p.resize((int(p.width * k), int(p.height * k)), Image.LANCZOS)
    m = np.ones((p.height, p.width), np.float32)
    xs = np.linspace(0, 1, p.width)[None, :]
    m *= np.clip((1.0 - xs) / 0.35, 0, 1) ** 1.3                 # fade out to the right, under the title
    mask = Image.fromarray((m * 255).astype(np.uint8))
    bg.paste(p, (0, (TH - p.height) // 2), mask)
    # a lamp in the lantern: a warm glow where the light would be (variant b leaves it dark)
    glow = Image.new("RGB", (TW, TH), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((700, 110, 1300, 640), fill=(20, 70, 84))
    glow = glow.filter(ImageFilter.GaussianBlur(130))
    arr = np.asarray(bg, np.int16) + np.asarray(glow, np.int16) * 0.6
    bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    lines = [("HAUNTED", "lora-b", 150, (240, 234, 220)), ("LA PORTE", "lora-b", 92, (120, 214, 228)), ("COUNTY", "lora-b", 92, (120, 214, 228))]
    y = 128
    for s, kind, size, colr in lines:
        t = doc.text(s, kind, size, colr + (255,), stroke=4, stroke_fill=(0, 0, 0))
        sh = doc.glow(t, (0, 0, 0), radius=18, strength=1.0)
        bg.paste(sh, (TW - 56 - t.width - (sh.width - t.width) // 2, y - (sh.height - t.height) // 2), sh)
        y += t.height + 14
    sub = doc.text("WHAT'S REAL · WHAT'S LEGEND", "inter-b", 32, (226, 220, 206, 255), tracking=3)
    bg.paste(sub, (TW - 56 - sub.width, y + 16), sub)
    rng = np.random.default_rng(3)
    arr = np.asarray(bg, np.float32)
    arr += rng.normal(0, 5, arr.shape[:2])[..., None]
    yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
    dd = np.sqrt(((xx - TW / 2) / (TW * 0.62)) ** 2 + ((yy - TH / 2) / (TH * 0.62)) ** 2)
    arr *= np.clip(1.25 - dd * 0.55, 0.45, 1.0)[..., None]
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(out, quality=92)
    print("thumbnail", out)


if __name__ == "__main__":
    doc.load_manifests()
    crop = [float(v) for v in sys.argv[3].split(",")] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
    make(sys.argv[1], sys.argv[2], crop, sys.argv[4] if len(sys.argv) > 4 else "a")
