"""Drawn icons for the power-outage prep shorts (Oct. 2026). Flat shapes, drawn at 3x and scaled down so the edges
are smooth, in the Daily Video's palette. No logos, no real products, no people.

    import blackout_art as BA
    BA.house(420, lit=False), BA.flashlight(300), BA.fridge(300, badge="4 HR") ...
"""
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from reels_common import vr

AMBER = (255, 190, 70)
WARM = (255, 214, 120)
CREAM = (246, 238, 222)
SLATE = (92, 104, 128)
STEEL = (150, 162, 184)
NAVY = (18, 24, 44)
DARK = (34, 40, 60)
RED = (232, 64, 56)
GREEN = (90, 210, 120)
WATER = (120, 190, 255)


def _canvas(size, k=3):
    S = size * k
    return Image.new("RGBA", (S, S), (0, 0, 0, 0)), S


def _down(img, size):
    return img.resize((size, size), Image.LANCZOS)


def _font(kind, px):
    return vr.font(kind, px) if hasattr(vr, "font") else ImageFont.load_default()


def _text_center(d, cx, cy, text, kind, px, fill):
    f = _font(kind, px)
    b = d.textbbox((0, 0), text, font=f)
    d.text((cx - (b[2] - b[0]) / 2 - b[0], cy - (b[3] - b[1]) / 2 - b[1]), text, font=f, fill=fill)


def glow_behind(img, color=AMBER, radius=30, strength=0.6):
    """A soft glow of `color` behind the shape (its alpha), returned at the same size (no padding)."""
    a = img.split()[3].filter(ImageFilter.GaussianBlur(radius))
    g = Image.new("RGBA", img.size, color + (0,))
    g.putalpha(a.point(lambda v: int(v * strength)))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(g)
    out.alpha_composite(img)
    return out


def house(size, lit=True):
    """A house: roof, chimney, four windows (warm when lit, dark when the power's out) and a door."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    body = (0.18 * S, 0.46 * S, 0.82 * S, 0.88 * S)
    d.polygon([(0.10 * S, 0.50 * S), (0.50 * S, 0.16 * S), (0.90 * S, 0.50 * S)], fill=SLATE)
    d.rectangle((0.66 * S, 0.22 * S, 0.74 * S, 0.40 * S), fill=SLATE)
    d.rectangle(body, fill=(70, 80, 104))
    win = WARM if lit else (28, 32, 46)
    for (x, y) in ((0.26, 0.54), (0.58, 0.54)):
        d.rounded_rectangle((x * S, y * S, (x + 0.16) * S, (y + 0.13) * S), radius=0.015 * S, fill=win)
        d.line(((x + 0.08) * S, y * S, (x + 0.08) * S, (y + 0.13) * S), fill=(70, 80, 104), width=int(0.012 * S))
    d.rounded_rectangle((0.43 * S, 0.70 * S, 0.57 * S, 0.88 * S), radius=0.02 * S, fill=(52, 58, 80))
    d.ellipse((0.535 * S, 0.785 * S, 0.555 * S, 0.805 * S), fill=AMBER if lit else STEEL)
    out = _down(img, size)
    return glow_behind(out, AMBER, radius=size // 10, strength=0.45) if lit else out


def bulb(size, on=False):
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    glass = AMBER if on else (60, 66, 88)
    d.ellipse((0.26 * S, 0.12 * S, 0.74 * S, 0.60 * S), fill=glass)
    d.polygon([(0.34 * S, 0.50 * S), (0.66 * S, 0.50 * S), (0.60 * S, 0.68 * S), (0.40 * S, 0.68 * S)], fill=glass)
    for i, y in enumerate((0.69, 0.75, 0.81)):
        d.rounded_rectangle((0.38 * S, y * S, 0.62 * S, (y + 0.045) * S), radius=0.02 * S, fill=STEEL)
    d.polygon([(0.44 * S, 0.865 * S), (0.56 * S, 0.865 * S), (0.53 * S, 0.90 * S), (0.47 * S, 0.90 * S)], fill=SLATE)
    if on:
        d.line((0.44 * S, 0.50 * S, 0.47 * S, 0.36 * S, 0.50 * S, 0.46 * S, 0.53 * S, 0.36 * S, 0.56 * S, 0.50 * S),
               fill=(255, 250, 220), width=int(0.018 * S))
    out = _down(img, size)
    return glow_behind(out, AMBER, radius=size // 8, strength=0.7) if on else out


def flashlight(size, on=True):
    """A flashlight pointing up and to the right, with its beam."""
    img, S = _canvas(size)
    beam = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if on:
        db = ImageDraw.Draw(beam)
        db.polygon([(0.52 * S, 0.40 * S), (0.98 * S, 0.02 * S), (1.0 * S, 0.40 * S), (0.62 * S, 0.50 * S)],
                   fill=(255, 236, 160, 120))
        beam = beam.filter(ImageFilter.GaussianBlur(0.02 * S))
    img.alpha_composite(beam)
    body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle((0.10 * S, 0.43 * S, 0.50 * S, 0.57 * S), radius=0.05 * S, fill=(70, 80, 104))
    d.polygon([(0.48 * S, 0.40 * S), (0.62 * S, 0.34 * S), (0.62 * S, 0.66 * S), (0.48 * S, 0.60 * S)], fill=STEEL)
    d.rectangle((0.60 * S, 0.34 * S, 0.64 * S, 0.66 * S), fill=WARM if on else SLATE)
    d.rounded_rectangle((0.24 * S, 0.47 * S, 0.32 * S, 0.53 * S), radius=0.02 * S, fill=AMBER if on else SLATE)
    body = body.rotate(32, resample=Image.BICUBIC, center=(0.42 * S, 0.5 * S))
    img.alpha_composite(body)
    return _down(img, size)


def candle(size):
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.40 * S, 0.40 * S, 0.60 * S, 0.86 * S), radius=0.03 * S, fill=CREAM)
    d.line((0.50 * S, 0.40 * S, 0.50 * S, 0.33 * S), fill=(40, 40, 40), width=int(0.012 * S))
    d.ellipse((0.44 * S, 0.14 * S, 0.56 * S, 0.34 * S), fill=AMBER)
    d.ellipse((0.475 * S, 0.22 * S, 0.525 * S, 0.33 * S), fill=(255, 250, 220))
    return _down(img, size)


def no(img, size=None):
    """A red circle and slash over an icon ('don't')."""
    s = img.width
    out = img.copy()
    d = ImageDraw.Draw(out)
    w = max(6, s // 14)
    d.ellipse((w, w, s - w, s - w), outline=RED + (255,), width=w)
    d.line((s * 0.22, s * 0.22, s * 0.78, s * 0.78), fill=RED + (255,), width=w)
    return out


def plug(size):
    """A plug pulled out of its outlet."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.08 * S, 0.24 * S, 0.40 * S, 0.76 * S), radius=0.05 * S, fill=(70, 80, 104))
    for y in (0.38, 0.56):
        d.rounded_rectangle((0.20 * S, y * S, 0.28 * S, (y + 0.07) * S), radius=0.01 * S, fill=NAVY)
    d.rounded_rectangle((0.56 * S, 0.34 * S, 0.80 * S, 0.66 * S), radius=0.05 * S, fill=STEEL)
    for y in (0.40, 0.55):
        d.rectangle((0.46 * S, y * S, 0.56 * S, (y + 0.05) * S), fill=CREAM)
    d.line((0.80 * S, 0.50 * S, 0.88 * S, 0.50 * S, 0.92 * S, 0.70 * S, 0.98 * S, 0.80 * S), fill=STEEL,
           width=int(0.04 * S), joint="curve")
    return _down(img, size)


def fridge(size, badge=None, badge_color=AMBER):
    """A refrigerator, door shut, with an optional clock badge ('4 HR')."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.24 * S, 0.06 * S, 0.70 * S, 0.94 * S), radius=0.05 * S, fill=(214, 222, 236))
    d.line((0.24 * S, 0.38 * S, 0.70 * S, 0.38 * S), fill=STEEL, width=int(0.014 * S))
    for (y0, y1) in ((0.14, 0.30), (0.46, 0.66)):
        d.rounded_rectangle((0.30 * S, y0 * S, 0.335 * S, y1 * S), radius=0.015 * S, fill=SLATE)
    if badge:
        cx, cy, r = 0.72 * S, 0.70 * S, 0.21 * S
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=NAVY, outline=badge_color, width=int(0.022 * S))
        _text_center(d, cx, cy, badge, "black", int((0.13 if len(badge) <= 4 else 0.105) * S), badge_color)
    return _down(img, size)


def thermometer(size, text="40°", color=WATER):
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.42 * S, 0.08 * S, 0.58 * S, 0.74 * S), radius=0.08 * S, fill=CREAM)
    d.ellipse((0.34 * S, 0.64 * S, 0.66 * S, 0.96 * S), fill=CREAM)
    d.rounded_rectangle((0.47 * S, 0.36 * S, 0.53 * S, 0.80 * S), radius=0.03 * S, fill=color)
    d.ellipse((0.39 * S, 0.69 * S, 0.61 * S, 0.91 * S), fill=color)
    for y in (0.18, 0.26, 0.34, 0.42, 0.50, 0.58):
        d.line((0.58 * S, y * S, 0.64 * S, y * S), fill=STEEL, width=int(0.012 * S))
    return _down(img, size)


def generator(size):
    """A portable generator: frame, engine box, wheels, exhaust."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.14 * S, 0.34 * S, 0.86 * S, 0.76 * S), radius=0.04 * S, fill=(232, 160, 40))
    d.rounded_rectangle((0.22 * S, 0.42 * S, 0.58 * S, 0.68 * S), radius=0.03 * S, fill=(60, 66, 88))
    d.rounded_rectangle((0.64 * S, 0.44 * S, 0.80 * S, 0.54 * S), radius=0.02 * S, fill=(60, 66, 88))
    d.line((0.14 * S, 0.30 * S, 0.86 * S, 0.30 * S), fill=(40, 44, 60), width=int(0.03 * S))
    for x in (0.14, 0.86):
        d.line((x * S, 0.30 * S, x * S, 0.80 * S), fill=(40, 44, 60), width=int(0.03 * S))
    for x in (0.24, 0.76):
        d.ellipse(((x - 0.08) * S, 0.72 * S, (x + 0.08) * S, 0.88 * S), fill=(30, 32, 44))
        d.ellipse(((x - 0.03) * S, 0.77 * S, (x + 0.03) * S, 0.83 * S), fill=STEEL)
    for i, (x, y, r) in enumerate(((0.80, 0.22, 0.05), (0.86, 0.13, 0.065), (0.93, 0.04, 0.05))):
        d.ellipse(((x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S), fill=(150, 156, 170, 150 - 40 * i))
    return _down(img, size)


def co_alarm(size, text="CO"):
    """A round smoke/CO alarm with its light on."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.ellipse((0.08 * S, 0.08 * S, 0.92 * S, 0.92 * S), fill=(232, 236, 244))
    d.ellipse((0.18 * S, 0.18 * S, 0.82 * S, 0.82 * S), outline=STEEL, width=int(0.02 * S))
    for k in range(10):
        a = 2 * math.pi * k / 10
        x, y = 0.5 + 0.25 * math.cos(a), 0.5 + 0.25 * math.sin(a)
        d.ellipse(((x - 0.02) * S, (y - 0.02) * S, (x + 0.02) * S, (y + 0.02) * S), fill=STEEL)
    _text_center(d, 0.5 * S, 0.47 * S, text, "black", int(0.17 * S), (40, 46, 66))
    d.ellipse((0.47 * S, 0.62 * S, 0.53 * S, 0.68 * S), fill=GREEN)
    return _down(img, size)


def jug(size, fill_level=0.8):
    """A one-gallon water jug."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.24 * S, 0.26 * S, 0.76 * S, 0.94 * S), radius=0.08 * S, fill=(200, 226, 255, 150))
    top = 0.94 - 0.62 * fill_level
    d.rounded_rectangle((0.26 * S, top * S, 0.74 * S, 0.92 * S), radius=0.07 * S, fill=WATER + (230,))
    d.rounded_rectangle((0.40 * S, 0.12 * S, 0.54 * S, 0.27 * S), radius=0.02 * S, fill=(200, 226, 255, 170))
    d.rounded_rectangle((0.39 * S, 0.08 * S, 0.55 * S, 0.14 * S), radius=0.02 * S, fill=(70, 130, 220))
    d.arc((0.54 * S, 0.16 * S, 0.80 * S, 0.50 * S), start=-80, end=80, fill=(200, 226, 255, 200), width=int(0.04 * S))
    return _down(img, size)


def phone(size, level=0.6):
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.28 * S, 0.06 * S, 0.72 * S, 0.94 * S), radius=0.07 * S, fill=(40, 46, 66))
    d.rounded_rectangle((0.31 * S, 0.12 * S, 0.69 * S, 0.86 * S), radius=0.04 * S, fill=(22, 26, 40))
    d.rounded_rectangle((0.38 * S, 0.36 * S, 0.62 * S, 0.62 * S), radius=0.02 * S, outline=CREAM, width=int(0.02 * S))
    d.rectangle((0.62 * S, 0.45 * S, 0.65 * S, 0.53 * S), fill=CREAM)
    c = GREEN if level > 0.3 else RED
    d.rectangle((0.40 * S, 0.38 * S, (0.40 + 0.20 * level) * S, 0.60 * S), fill=c)
    return _down(img, size)


def calendar(size, big="90", small="DAYS", color=AMBER):
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.10 * S, 0.14 * S, 0.90 * S, 0.92 * S), radius=0.06 * S, fill=CREAM)
    d.rounded_rectangle((0.10 * S, 0.14 * S, 0.90 * S, 0.34 * S), radius=0.06 * S, fill=color)
    d.rectangle((0.10 * S, 0.26 * S, 0.90 * S, 0.34 * S), fill=color)
    for x in (0.30, 0.70):
        d.rounded_rectangle(((x - 0.03) * S, 0.06 * S, (x + 0.03) * S, 0.22 * S), radius=0.02 * S, fill=SLATE)
    _text_center(d, 0.5 * S, 0.60 * S, big, "black", int(0.36 * S), NAVY)
    _text_center(d, 0.5 * S, 0.83 * S, small, "black", int(0.10 * S), SLATE)
    return _down(img, size)


def distance(width, label="20 FT", color=AMBER):
    """A two-headed arrow with a distance label, for 'keep it this far away'."""
    k = 3
    W_, H_ = width * k, 70 * k
    img = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = H_ * 0.70
    d.line((12 * k, y, W_ - 12 * k, y), fill=color, width=5 * k)
    for x, s in ((12 * k, 1), (W_ - 12 * k, -1)):
        d.polygon([(x, y), (x + s * 26 * k, y - 14 * k), (x + s * 26 * k, y + 14 * k)], fill=color)
    _text_center(d, W_ / 2, H_ * 0.26, label, "black", 44 * k, color)
    return img.resize((width, 70), Image.LANCZOS)


def flame(size, color=(255, 140, 40)):
    """A gas flame (for 'never heat with a gas oven, stove or grill')."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.polygon([(0.50 * S, 0.10 * S), (0.70 * S, 0.42 * S), (0.76 * S, 0.62 * S), (0.70 * S, 0.80 * S),
               (0.50 * S, 0.90 * S), (0.30 * S, 0.80 * S), (0.24 * S, 0.62 * S), (0.30 * S, 0.42 * S)], fill=color)
    d.polygon([(0.50 * S, 0.40 * S), (0.62 * S, 0.62 * S), (0.60 * S, 0.78 * S), (0.50 * S, 0.84 * S),
               (0.40 * S, 0.78 * S), (0.38 * S, 0.62 * S)], fill=(255, 220, 120))
    d.rounded_rectangle((0.18 * S, 0.88 * S, 0.82 * S, 0.94 * S), radius=0.02 * S, fill=STEEL)
    return _down(img, size)


def bottle(size):
    """A pill bottle (for medicine that needs the fridge)."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.28 * S, 0.10 * S, 0.72 * S, 0.26 * S), radius=0.03 * S, fill=CREAM)
    d.rounded_rectangle((0.30 * S, 0.24 * S, 0.70 * S, 0.90 * S), radius=0.05 * S, fill=(236, 150, 60, 235))
    d.rounded_rectangle((0.33 * S, 0.40 * S, 0.67 * S, 0.70 * S), radius=0.02 * S, fill=CREAM)
    d.rectangle((0.48 * S, 0.45 * S, 0.52 * S, 0.65 * S), fill=RED)
    d.rectangle((0.40 * S, 0.53 * S, 0.60 * S, 0.57 * S), fill=RED)
    return _down(img, size)


def trash(size):
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.26 * S, 0.30 * S, 0.74 * S, 0.92 * S), radius=0.04 * S, fill=(92, 104, 128))
    d.rounded_rectangle((0.20 * S, 0.20 * S, 0.80 * S, 0.30 * S), radius=0.03 * S, fill=(122, 134, 158))
    d.rounded_rectangle((0.42 * S, 0.12 * S, 0.58 * S, 0.21 * S), radius=0.03 * S, outline=(122, 134, 158),
                        width=int(0.03 * S))
    for x in (0.38, 0.50, 0.62):
        d.line((x * S, 0.38 * S, x * S, 0.84 * S), fill=(70, 80, 104), width=int(0.03 * S))
    return _down(img, size)


def garage(size, inside=None):
    """A garage with its door rolled up, and something parked inside."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.polygon([(0.04 * S, 0.40 * S), (0.50 * S, 0.10 * S), (0.96 * S, 0.40 * S)], fill=SLATE)
    d.rectangle((0.10 * S, 0.37 * S, 0.90 * S, 0.94 * S), fill=(70, 80, 104))
    d.rectangle((0.20 * S, 0.50 * S, 0.80 * S, 0.94 * S), fill=(20, 24, 36))
    for k in range(3):
        y = 0.43 + 0.025 * k
        d.rectangle((0.20 * S, y * S, 0.80 * S, (y + 0.018) * S), fill=STEEL)
    out = _down(img, size)
    if inside is not None:
        out.alpha_composite(inside, ((size - inside.width) // 2, int(0.94 * size) - inside.height))
    return out


def oven(size):
    """A kitchen range: four burners and an oven door."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0.16 * S, 0.22 * S, 0.84 * S, 0.92 * S), radius=0.04 * S, fill=(214, 222, 236))
    d.rectangle((0.16 * S, 0.22 * S, 0.84 * S, 0.34 * S), fill=(60, 66, 88))
    for x in (0.30, 0.43, 0.57, 0.70):
        d.ellipse(((x - 0.035) * S, 0.255 * S, (x + 0.035) * S, 0.305 * S), fill=STEEL)
    d.rounded_rectangle((0.24 * S, 0.46 * S, 0.76 * S, 0.84 * S), radius=0.03 * S, fill=(40, 46, 66))
    d.rounded_rectangle((0.32 * S, 0.40 * S, 0.68 * S, 0.43 * S), radius=0.015 * S, fill=SLATE)
    return _down(img, size)


def grill(size):
    """A kettle grill on three legs."""
    img, S = _canvas(size)
    d = ImageDraw.Draw(img)
    d.chord((0.18 * S, 0.14 * S, 0.82 * S, 0.62 * S), start=180, end=360, fill=(50, 54, 70))
    d.ellipse((0.47 * S, 0.12 * S, 0.53 * S, 0.17 * S), fill=STEEL)
    d.rectangle((0.16 * S, 0.37 * S, 0.84 * S, 0.40 * S), fill=STEEL)
    d.chord((0.18 * S, 0.20 * S, 0.82 * S, 0.70 * S), start=0, end=180, fill=(60, 66, 88))
    for (x0, x1) in ((0.30, 0.22), (0.70, 0.78), (0.50, 0.50)):
        d.line((x0 * S, 0.62 * S, x1 * S, 0.92 * S), fill=STEEL, width=int(0.03 * S))
    return _down(img, size)
