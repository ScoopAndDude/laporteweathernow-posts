#!/usr/bin/env python3
"""Render tall Pinterest pins (1000 x 1500) for the ScoopAndDude Etsy shop.

Reads etsy-pins/pins.json, downloads each listing photo from Etsy, and writes
etsy-pins/out/<slug>.jpg. The GitHub Action in .github/workflows/etsy-pins.yml
runs this whenever pins.json or this file changes, then commits the images.

To make new pins: add entries to pins.json and push. Each entry needs
slug, theme, image (an Etsy il_fullxfull URL), label, headline and sub.

Local test without internet:  python etsy-pins/render.py --offline
"""
import io
import json
import os
import sys
import time
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FONTS = os.path.join(REPO, "video", "fonts")
OUT = os.path.join(HERE, "out")
W, H = 1000, 1500

THEMES = {
    # prep, money and gag gifts: matches the existing dark ScoopAndDude pins
    "dark":     dict(bg="#141414", label="#F97316", head="#FFFFFF", sub="#CFCFCF", btn="#F97316", btn_text="#111111", stripes=True),
    # holiday and hosting printables
    "rust":     dict(bg="#FAF1E4", label="#A4502A", head="#3B2416", sub="#6B4E3D", btn="#A4502A", btn_text="#FFF7EE"),
    "green":    dict(bg="#12372A", label="#E0B15C", head="#F7F0E1", sub="#CFE0D4", btn="#E0B15C", btn_text="#12372A"),
    "red":      dict(bg="#FBF0EC", label="#B3262E", head="#2F4A34", sub="#5E4B45", btn="#B3262E", btn_text="#FFFFFF"),
    "maroon":   dict(bg="#6E1B26", label="#E7B96A", head="#F7EBDD", sub="#EBD3C7", btn="#E7B96A", btn_text="#4A1019"),
    "blue":     dict(bg="#EEF3FA", label="#3A5A8C", head="#23344F", sub="#4A5B73", btn="#3A5A8C", btn_text="#FFFFFF"),
    "lavender": dict(bg="#F1EFF8", label="#4B3F8C", head="#2A2550", sub="#5A547A", btn="#4B3F8C", btn_text="#FFFFFF"),
    "sage":     dict(bg="#EEF0EA", label="#2F4B3F", head="#1F2D27", sub="#4D5C55", btn="#2F4B3F", btn_text="#FFFFFF"),
    "blush":    dict(bg="#F8EFEA", label="#9A5B4F", head="#3A2622", sub="#6E544E", btn="#9A5B4F", btn_text="#FFFFFF"),
}
STRIPE = 26          # height of the hazard stripe band on dark pins
SIDE = 60            # left/right margin


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, f"Inter-{name}.otf"), size)


def text_w(draw, s, f, tracking=0):
    if not s:
        return 0
    return draw.textlength(s, font=f) + tracking * (len(s) - 1)


def wrap(draw, text, f, max_w):
    # "a • b • c" lists break between items, so no line ends on a bullet
    sep = " • " if " • " in text else " "
    words, lines, cur = text.split(sep), [], ""
    for w in words:
        t = (cur + sep + w) if cur else w
        if text_w(draw, t, f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def balance(draw, text, f, n, max_w):
    """Split a headline into n lines that are as even as possible (no lonely last word)."""
    parts = text.split(". ")
    if n == 2 and len(parts) == 2:  # two short sentences: one per line
        lines = [parts[0] + ".", parts[1]]
        if all(text_w(draw, l, f) <= max_w for l in lines):
            return lines
    words = text.split()
    if n <= 1 or len(words) <= n:
        return [text] if n <= 1 else words
    best, best_score = None, None
    def splits(start, k):
        if k == 1:
            yield [words[start:]]
            return
        for cut in range(start + 1, len(words) - k + 2):
            for rest in splits(cut, k - 1):
                yield [words[start:cut]] + rest
    for groups in splits(0, n):
        lines = [" ".join(g) for g in groups]
        widths = [text_w(draw, l, f) for l in lines]
        if max(widths) > max_w:
            continue
        score = (max(widths), sum((max(widths) - w) ** 2 for w in widths))
        if best_score is None or score < best_score:
            best, best_score = lines, score
    return best or wrap(draw, text, f, max_w)


def layout_head(draw, head, face):
    """Pick the headline size and line breaks: biggest size that fits in 3 lines."""
    max_w = W - 2 * SIDE
    parts = head.split(". ")
    if len(parts) == 2:  # "Half joke. Half actually useful." -> one sentence per line
        lines = [parts[0] + ".", parts[1]]
        for size in range(104, 54, -4):
            hf = font(face, size)
            if all(text_w(draw, l, hf) <= max_w for l in lines):
                return size, hf, lines
    for size in range(104, 54, -4):
        hf = font(face, size)
        lines = wrap(draw, head, hf, max_w)
        if len(lines) <= 3 and all(text_w(draw, l, hf) <= max_w for l in lines):
            if size <= 88 or len(lines) <= 2:
                break
    return size, hf, balance(draw, head, hf, len(lines), max_w)


def draw_centered(draw, y, s, f, fill, tracking=0):
    x = (W - text_w(draw, s, f, tracking)) / 2
    if tracking:
        for ch in s:
            draw.text((x, y), ch, font=f, fill=fill)
            x += draw.textlength(ch, font=f) + tracking
    else:
        draw.text((x, y), s, font=f, fill=fill)


def stripes(draw, y0):
    draw.rectangle([0, y0, W, y0 + STRIPE], fill="#111111")
    x = -STRIPE
    while x < W + STRIPE:
        draw.polygon([(x, y0 + STRIPE), (x + 20, y0 + STRIPE), (x + 20 + STRIPE, y0), (x + STRIPE, y0)], fill="#F97316")
        x += 44


def fetch(url, offline, ratio=(5, 4)):
    if offline:
        w, h = 2000, int(2000 * ratio[1] / ratio[0])
        img = Image.new("RGB", (w, h), "#8a8f98")
        d = ImageDraw.Draw(img)
        d.rectangle([40, 40, w - 40, h - 40], outline="#ffffff", width=12)
        d.text((w / 2 - 300, h / 2 - 60), "LISTING PHOTO", font=font("Black", 110), fill="#ffffff")
        return img
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ScoopAndDude-pins/1.0)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return Image.open(io.BytesIO(r.read())).convert("RGB")
        except Exception as e:  # network hiccup: wait and retry
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"could not download {url}: {last}")


def paste_photo(canvas, photo, box, dark):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    scale = min(bw / photo.width, bh / photo.height)
    pw, ph = int(photo.width * scale), int(photo.height * scale)
    photo = photo.resize((pw, ph), Image.LANCZOS)
    px, py = x0 + (bw - pw) // 2, y0 + (bh - ph) // 2
    radius = 18
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=radius, fill=255)
    # soft shadow
    shadow = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([40, 52, 40 + pw, 52 + ph], radius=radius,
                                             fill=(0, 0, 0, 150 if dark else 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.paste(shadow, (px - 40, py - 40), shadow)
    canvas.paste(photo, (px, py), mask)
    if dark:  # thin edge so black product photos don't melt into the background
        ImageDraw.Draw(canvas).rounded_rectangle([px, py, px + pw - 1, py + ph - 1], radius=radius, outline="#3a3a3a", width=2)


def render(pin, offline=False):
    t = THEMES[pin["theme"]]
    dark = bool(t.get("stripes"))
    canvas = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(canvas)
    top = STRIPE if dark else 0
    if dark:
        stripes(d, 0)
        stripes(d, H - STRIPE)

    # label
    y = top + 52
    lf = font("Bold", 28)
    draw_centered(d, y, pin["label"].upper(), lf, t["label"], tracking=3)
    y += 34 + 24

    # headline: largest size that fits in 3 lines
    head = pin["headline"].upper() if dark else pin["headline"]
    face = "Black" if dark else "ExtraBold"
    size, hf, lines = layout_head(d, head, face)
    lh = int(size * 1.06)
    for line in lines:
        draw_centered(d, y, line, hf, t["head"])
        y += lh
    head_bottom = y + 8

    # bottom block, laid out from the bottom up
    bottom = H - (STRIPE if dark else 0)
    footer_y = bottom - 74
    btn_h = 84
    btn_y1 = footer_y - 34
    btn_y0 = btn_y1 - btn_h
    sf = font("SemiBold", 33)
    sub_lines = wrap(d, pin["sub"], sf, W - 2 * SIDE)[:2]
    sub_h = 44 * len(sub_lines)
    sub_y = btn_y0 - 30 - sub_h

    # photo between the headline and the sub line
    photo = fetch(pin["image"], offline, ratio=tuple(pin.get("_ratio", (5, 4))))
    paste_photo(canvas, photo, (SIDE - 10, head_bottom + 26, W - SIDE + 10, sub_y - 34), dark)
    d = ImageDraw.Draw(canvas)

    for i, line in enumerate(sub_lines):
        draw_centered(d, sub_y + i * 44, line, sf, t["sub"])

    # button
    cta = "INSTANT DOWNLOAD • SHOP NOW" if dark else "Instant download • Shop on Etsy"
    bf = font("ExtraBold", 33)
    bw = max(640, text_w(d, cta, bf) + 120)
    bx0 = (W - bw) / 2
    d.rounded_rectangle([bx0, btn_y0, bx0 + bw, btn_y1], radius=btn_h // 2, fill=t["btn"])
    bb = d.textbbox((0, 0), cta, font=bf)
    d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], btn_y0 + (btn_h - (bb[3] - bb[1])) / 2 - bb[1]), cta, font=bf, fill=t["btn_text"])

    # footer
    if dark:
        ff = font("Black", 40)
        parts = [("SCOOP", "#FFFFFF"), ("AND", "#F97316"), ("DUDE", "#FFFFFF")]
        total = sum(d.textlength(p, font=ff) for p, _ in parts) + 6 * 2
        x = (W - total) / 2
        for p, c in parts:
            d.text((x, footer_y), p, font=ff, fill=c)
            x += d.textlength(p, font=ff) + 6
    else:
        draw_centered(d, footer_y + 4, "ScoopAndDude on Etsy", font("SemiBold", 30), t["sub"])
    return canvas


def main():
    offline = "--offline" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    spec = json.load(open(os.path.join(HERE, "pins.json")))
    os.makedirs(OUT, exist_ok=True)
    made = 0
    for pin in spec["pins"]:
        if only and pin["slug"] not in only:
            continue
        img = render(pin, offline)
        path = os.path.join(OUT, pin["slug"] + ".jpg")
        img.save(path, "JPEG", quality=90, optimize=True, progressive=True)
        made += 1
        print("wrote", os.path.relpath(path, REPO))
    print(f"{made} pins rendered")


if __name__ == "__main__":
    main()
