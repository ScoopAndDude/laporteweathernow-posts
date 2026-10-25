#!/usr/bin/env python3
"""The YouTube thumbnail (1280x720) for the Stanley Hotel documentary.

    python3 tools/video/stanley-doc/thumb.py OUT.jpg [variant]

a: the drawn door of Room 217 on the left, "ROOM 217" and "THE REAL SHINING HOTEL" on the right.
b: a photo of the hotel (pass the picture's file name as a third argument), darkened, with the same words.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc  # noqa: E402

TW, TH = 1280, 720


def door_bg():
    """The drawn door, moved to the left third (the plain wall to its right is continued as a mirror image)."""
    base, strip, (sw, sh) = doc.door_scene("217", 1)
    vw = sw / 1.12
    vh = vw * TH / TW
    cx, cy = sw * 0.5, sh * 0.48
    box = (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)
    f = base.view_array(box, (TW, TH)).astype(np.float32) * 1.1 + strip.view_array(box, (TW, TH)).astype(np.float32) * 1.25
    shift = 300
    f = np.concatenate([f[:, shift:], np.flip(f[:, TW - shift:], axis=1)], axis=1)
    return Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))


def photo_bg(name):
    im = Image.open(doc.img_path(name)).convert("RGB")
    k = max(TW / im.width, TH / im.height)
    im = im.resize((int(im.width * k) + 1, int(im.height * k) + 1), Image.LANCZOS)
    x0, y0 = (im.width - TW) // 2, (im.height - TH) // 2
    im = im.crop((x0, y0, x0 + TW, y0 + TH))
    im = ImageEnhance.Color(im).enhance(0.55)
    im = ImageEnhance.Brightness(im).enhance(0.62)
    arr = np.asarray(im, np.float32) * np.array([0.86, 0.92, 1.06], np.float32)        # toward night
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def make(out, variant="a", photo=None):
    bg = door_bg() if variant == "a" else photo_bg(photo)
    # darken the right side for the words
    arr = np.asarray(bg, np.float32)
    xs = np.linspace(0, 1, TW)[None, :, None]
    arr *= np.clip(1.25 - xs * 0.85, 0.35, 1.0) if variant == "a" else np.clip(1.15 - xs * 0.7, 0.4, 1.0)
    bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    glow = Image.new("RGB", (TW, TH), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse((700, 140, 1300, 600), fill=(120, 14, 10))
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    bg = Image.fromarray(np.clip(np.asarray(bg, np.int16) + np.asarray(glow, np.int16) * 0.5, 0, 255).astype(np.uint8))
    lines = [("ROOM", "lora-b", 118, (240, 228, 206)), ("217", "lora-b", 250, (236, 46, 36))]
    y = 70
    right = TW - 70
    for s, kind, size, colr in lines:
        t = doc.text(s, kind, size, colr + (255,), stroke=5, stroke_fill=(0, 0, 0))
        sh = doc.glow(t, (0, 0, 0), radius=18, strength=1.0)
        bg.paste(sh, (right - t.width - (sh.width - t.width) // 2, y - (sh.height - t.height) // 2), sh)
        y += t.height + 22
    for s in ("THE REAL", "SHINING HOTEL"):
        sub = doc.text(s, "inter-b", 52, (240, 226, 200, 255), tracking=3, stroke=3, stroke_fill=(0, 0, 0))
        bg.paste(sub, (right - sub.width, y + 8), sub)
        y += sub.height + 14
    rng = np.random.default_rng(3)
    arr = np.asarray(bg, np.float32)
    arr += rng.normal(0, 5, arr.shape[:2])[..., None]
    yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
    dd = np.sqrt(((xx - TW / 2) / (TW * 0.62)) ** 2 + ((yy - TH / 2) / (TH * 0.62)) ** 2)
    arr *= np.clip(1.25 - dd * 0.5, 0.5, 1.0)[..., None]
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(out, quality=92)
    print("thumbnail", out)


if __name__ == "__main__":
    doc.load_manifests()
    make(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "a", sys.argv[3] if len(sys.argv) > 3 else None)
