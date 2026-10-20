#!/usr/bin/env python3
"""The YouTube thumbnail (1280x720): Belle's portrait on the left, the title on the right.

    python3 tools/video/belle-doc/thumb.py OUT.jpg [variant]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc  # noqa: E402

TW, TH = 1280, 720


def portrait():
    im = Image.open(doc.img_path("belle-08.jpg")).convert("L")
    im = ImageOps.autocontrast(im, cutoff=0.8)
    im = ImageEnhance.Contrast(im).enhance(1.15)
    im = im.resize((im.width * 3, im.height * 3), Image.LANCZOS).filter(ImageFilter.UnsharpMask(3, 80, 2))
    col = ImageOps.colorize(im, black=(10, 6, 5), mid=(128, 96, 70), white=(246, 228, 196))
    return col


def make(out, variant="a"):
    bg = Image.new("RGB", (TW, TH), (14, 10, 8))
    p = portrait()
    k = TH * 1.18 / p.height
    p = p.resize((int(p.width * k), int(p.height * k)), Image.LANCZOS)
    # fade the portrait into the dark on the right
    x0 = -40
    mask = Image.new("L", p.size, 255)
    m = np.ones((p.height, p.width), np.float32)
    xs = np.linspace(0, 1, p.width)[None, :]
    m *= np.clip((1.0 - xs) / 0.32, 0, 1) ** 1.2
    ys = np.linspace(0, 1, p.height)[:, None]
    m *= np.clip((1.0 - ys) / 0.25, 0, 1)
    mask = Image.fromarray((m * 255).astype(np.uint8))
    bg.paste(p, (x0, -int(p.height * 0.08)), mask)
    # red glow behind the text
    glow = Image.new("RGB", (TW, TH), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((620, 120, 1280, 640), fill=(120, 14, 10))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    bg = Image.fromarray(np.clip(np.asarray(bg, np.int16) + np.asarray(glow, np.int16) * 0.55, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(bg)
    if variant == "a":
        lines = [("LA PORTE'S", "lora-b", 78, (240, 228, 206)), ("BLACK", "lora-b", 150, (236, 46, 36)), ("WIDOW", "lora-b", 150, (236, 46, 36))]
    else:
        lines = [("THE WIDOW'S", "lora-b", 80, (240, 228, 206)), ("FARM", "lora-b", 180, (236, 46, 36))]
    y = 120
    for s, kind, size, colr in lines:
        t = doc.text(s, kind, size, colr + (255,), stroke=4, stroke_fill=(0, 0, 0))
        sh = doc.glow(t, (0, 0, 0), radius=16, strength=1.0)
        bg.paste(sh, (TW - 60 - t.width - (sh.width - t.width) // 2, y - (sh.height - t.height) // 2), sh)
        y += t.height + 18
    sub = doc.text("BELLE GUNNESS · 1908", "inter-b", 34, (230, 214, 186, 255), tracking=3)
    bg.paste(sub, (TW - 60 - sub.width, y + 14), sub)
    # film grain and a vignette
    rng = np.random.default_rng(3)
    arr = np.asarray(bg, np.float32)
    arr += rng.normal(0, 6, arr.shape[:2])[..., None]
    yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
    dd = np.sqrt(((xx - TW / 2) / (TW * 0.62)) ** 2 + ((yy - TH / 2) / (TH * 0.62)) ** 2)
    arr *= np.clip(1.25 - dd * 0.55, 0.45, 1.0)[..., None]
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(out, quality=92)
    print("thumbnail", out)


if __name__ == "__main__":
    doc.load_manifests()
    make(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "a")
