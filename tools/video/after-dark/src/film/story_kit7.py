"""Props for the Beatty Memorial Hospital short (story_kit7.py; added Nov. 14, 2026, for Westville's second story).
They register themselves in story_kit3.PROPS, so any tab_* scene can use them:

    hospital     a 1950s state hospital campus of the cottage plan: separate two-storey flat-roofed brick buildings
                 with rows of windows, a power-plant smokestack and a water tower. n=4 buildings   lit=0.3
                 wing="max"  one plain building with barred windows and a floodlight (a maximum security ward)
                 ruin=True   the nearest building half torn down: a broken roofline and open, empty floors
    prisonfence  a tall chain-link fence with coiled wire on top and floodlight poles, across the whole picture
    bowling      an empty old bowling alley: wooden lanes running back to pins under one hanging lamp
    excavator    a demolition excavator with its arm raised (no one in the cab)
    ward         a three-storey brick building with bars on the windows (the Indiana Hospital for Insane Criminals at
                 the state prison in Michigan City was described as a three-storey brick building with barred windows)
    prisonwall   a tall plain stone prison wall across the picture, with one small guard tower
    newprison    a new prison going up: long, low, pale concrete buildings with narrow windows, a fence line in front
    crane        a tower crane far off, over new construction

Nothing shows a patient, an inmate, a body, a real person's likeness, a sign or a brand.
"""
import math

import numpy as np

import story_kit3 as K3
from story_kit import WARM, hash2
from core import paint, smooth_path
import skia

prop = K3.prop
BRICK = "#2a1712"
BRICK2 = "#22130f"


def _bldg(c, L, x0, x1, y, h, lit, seed, bars=False, cols=None, rows=2):
    """One flat-roofed brick building from x0 to x1, base y, height h."""
    c.rect(x0, y - h, x1, y, BRICK if seed % 2 else BRICK2)
    c.rect(x0 - 6, y - h - 10, x1 + 6, y - h, "#120b08")                    # parapet
    n = cols or max(3, int((x1 - x0) / 46))
    ww = (x1 - x0) / n
    for r in range(rows):
        wy0 = y - h + 22 + r * (h - 34) / rows
        wy1 = wy0 + (h - 34) / rows - 24
        for k in range(n):
            wx0 = x0 + k * ww + ww * 0.25
            wx1 = wx0 + ww * 0.5
            on = hash2(k, r, seed) < lit
            c.rect(wx0, wy0, wx1, wy1, "#0a0807")
            if on:
                L.rect(wx0, wy0, wx1, wy1, WARM, 0.45)
            if bars:
                for b in range(1, 4):
                    bx = wx0 + (wx1 - wx0) * b / 4
                    c.line([(bx, wy0), (bx, wy1)], "#050505", 2.2)
    return (x0 + x1) / 2


@prop
def hospital(c, L, x, y, s=1.0, n=4, lit=0.3, wing="", ruin=False, seed=1, bars=True, flood=True, **k):
    """A cottage-plan state hospital of about 1950: separate brick buildings, a smokestack and a water tower."""
    out = []
    # the water tower and the power plant's stack, behind
    tx = x + 330 * s
    for lx in (-30, 30):
        c.line([(tx + lx * s, y - 70 * s), (tx + lx * 0.4 * s, y - 330 * s)], "#0c0c0d", 5 * s)
    c.c.drawOval(skia.Rect.MakeLTRB(tx - 52 * s, y - 400 * s, tx + 52 * s, y - 320 * s), paint("#0e0e10"))
    c.rect(tx - 52 * s, y - 362 * s, tx + 52 * s, y - 336 * s, "#0e0e10")
    sx = x - 360 * s
    c.rect(sx - 16 * s, y - 470 * s, sx + 16 * s, y - 60 * s, "#120a08")
    c.rect(sx - 19 * s, y - 478 * s, sx + 19 * s, y - 466 * s, "#0a0606")
    for j in range(6):
        c.circle(sx + (10 + j * 26) * s, y - (500 + j * 18) * s, (14 + j * 7) * s, "#2a2d30", 0.4 - j * 0.05)
    # the far row of buildings, then the near ones
    for j in range(n):
        bx = x + (j - (n - 1) / 2) * 260 * s
        _bldg(c, L, bx - 105 * s, bx + 105 * s, y - 40 * s, 120 * s, lit * 0.8, seed * 7 + j, rows=2)
    if wing == "max":
        mx0, mx1 = x - 250 * s, x + 250 * s
        _bldg(c, L, mx0, mx1, y + 30 * s, 170 * s, lit, seed * 13, bars=bars, cols=9, rows=2)
        if flood:
            c.line([(x + 270 * s, y + 30 * s), (x + 270 * s, y - 230 * s)], "#0a0a0b", 5 * s)
            c.rect(x + 256 * s, y - 238 * s, x + 284 * s, y - 226 * s, "#1a1a1c")
            out.append((x + 270 * s, y - 228 * s, (0.85, 0.9, 1.0), 70 * s, False, 0.45))
    elif ruin:
        base, top = y + 30 * s, 160 * s
        _bldg(c, L, x - 230 * s, x + 10 * s, base, top, 0.0, seed * 5, rows=2, cols=5)
        r = np.random.default_rng(seed)
        c.rect(x + 10 * s, base - top * 0.42, x + 230 * s, base, BRICK)            # what is left of the rest
        pts = [(x + 10 * s, base - top), (x + 10 * s, base - top * 0.42)]
        for t in np.linspace(0, 1, 12):                                           # a jagged broken wall
            pts.append((x + 10 * s + 220 * s * t, base - top * (0.42 + 0.3 * r.uniform() * (1 - t) ** 0.7)))
        pts.append((x + 230 * s, base - top * 0.42))
        c.poly(pts[:2] + pts[2:], BRICK, smooth=False)
        c.rect(x + 14 * s, base - top * 0.4, x + 200 * s, base - top * 0.06, "#080505")   # the open, empty inside
        c.line([(x + 14 * s, base - top * 0.22), (x + 200 * s, base - top * 0.22)], "#1a1210", 5 * s)
        for k2 in range(6):
            bx = x + (30 + k2 * 30) * s
            c.line([(bx, base - top * 0.42), (bx + 6 * s, base - top * 0.5 - r.uniform(0, 18) * s)], "#3a3530", 1.5 * s)
        for k2 in range(22):                                                    # rubble
            c.circle(x + r.uniform(150, 330) * s, base - r.uniform(0, 34) * s, r.uniform(7, 20) * s,
                     ("#2a1a14", "#3a2a22", "#1a1210")[k2 % 3])
    else:
        _bldg(c, L, x - 230 * s, x + 230 * s, y + 30 * s, 160 * s, lit, seed * 5, rows=2)
        c.rect(x - 40 * s, y + 30 * s - 70 * s, x + 40 * s, y + 30 * s, "#0d0806")           # entrance
        c.rect(x - 60 * s, y + 30 * s - 82 * s, x + 60 * s, y + 30 * s - 70 * s, "#1a120e")
    return out


@prop
def prisonfence(c, L, x, y, s=1.0, h=230, poles=True, **k):
    """A tall chain-link fence with coiled wire along the top, across the picture; floodlight poles behind it."""
    W = 1080
    out = []
    if poles:
        for px in (160, 920):
            c.line([(px, y), (px, y - (h + 260) * s)], "#0b0c0d", 6 * s)
            c.rect(px - 22 * s, y - (h + 270) * s, px + 22 * s, y - (h + 252) * s, "#1a1b1d")
            out.append((px, y - (h + 256) * s, (0.85, 0.9, 1.0), 80 * s, False, 0.42))
    for j in range(0, W + 60, int(150 * s)):
        c.line([(j, y), (j, y - h * s)], "#141618", 5 * s)
    step = 18 * s
    for j in np.arange(-h * s, W + h * s, step):                                # the diamond mesh, faint
        c.line([(j, y), (j + h * s, y - h * s)], "#3a3e42", 1.0, 0.35)
        c.line([(j, y - h * s), (j + h * s, y)], "#3a3e42", 1.0, 0.35)
    c.line([(-10, y - h * s), (W + 10, y - h * s)], "#2a2d30", 4 * s)
    for j in np.arange(0, W + 40, 22 * s):                                       # coiled wire
        c.c.drawCircle(j, y - (h + 22) * s, 20 * s, paint("#5a5e62", a=0.75, stroke=1.6))
    return out


@prop
def bowling(c, L, x, y, s=1.0, n=4, **k):
    """An empty old bowling alley seen from the foul line: lanes running back to pins under one hanging lamp."""
    vx, vy = x, y - 300 * s
    c.rect(x - 600, vy - 260 * s, x + 600, vy + 4 * s, "#0c0807")               # the back wall, behind the pins
    c.rect(x - 600, vy - 4 * s, x + 600, vy + 6 * s, "#050403")
    for j in range(n):
        a = (j - (n - 1) / 2) * 230 * s
        b = (j - (n - 1) / 2) * 92 * s
        c.poly([(x + a - 100 * s, y + 500 * s), (x + a + 100 * s, y + 500 * s), (vx + b + 40 * s, vy), (vx + b - 40 * s, vy)],
               "#3e2a16" if j % 2 else "#362412", 0.95, smooth=False)
        c.poly([(x + a + 100 * s, y + 500 * s), (x + a + 122 * s, y + 500 * s), (vx + b + 48 * s, vy), (vx + b + 40 * s, vy)],
               "#120c08", smooth=False)                                          # the gutters
        for p, (px, py) in enumerate(((0, 0), (-12, -7), (12, -7), (-24, -14), (0, -14), (24, -14),
                                      (-36, -21), (-12, -21), (12, -21), (36, -21))):
            bx, by = vx + b + px * 0.75 * s, vy - 16 * s + py * 0.6 * s
            c.ellipse(bx, by, 5 * s, 11 * s, "#e8e2d4", 0.95)
            c.circle(bx, by - 13 * s, 3.6 * s, "#e8e2d4", 0.95)
            c.rect(bx - 4.5 * s, by - 8 * s, bx + 4.5 * s, by - 6 * s, "#8a1a14", 0.9)
    c.line([(x, vy - 520 * s), (x, vy - 160 * s)], "#0a0a0a", 2 * s)
    c.c.drawPath(smooth_path([(x - 40 * s, vy - 140 * s), (x + 40 * s, vy - 140 * s), (x + 14 * s, vy - 166 * s),
                              (x - 14 * s, vy - 166 * s)], True), paint("#1a1a1a"))
    return [(x, vy - 130 * s, (1.0, 0.85, 0.55), 170 * s, True, 0.4)]


@prop
def excavator(c, L, x, y, s=1.0, flip=False, **k):
    """A demolition excavator, arm raised toward a wall (no one in the cab)."""
    d = -1 if flip else 1
    INK = "#0a0a0b"
    c.rect(x - 120 * s, y - 40 * s, x + 120 * s, y, INK, r=18 * s)                # tracks
    for j in range(6):
        c.circle(x + (-95 + j * 38) * s, y - 20 * s, 12 * s, "#1a1b1c")
    c.rect(x - 90 * s, y - 120 * s, x + 90 * s, y - 40 * s, "#141416")            # body
    c.rect(x + d * 10 * s if d > 0 else x - 80 * s, y - 190 * s, x + 80 * s if d > 0 else x - 10 * s, y - 120 * s, "#111113")
    c.rect(x + (20 if d > 0 else -70) * s, y - 180 * s, x + (70 if d > 0 else -20) * s, y - 140 * s, "#2a3036", 0.8)
    p0 = (x + d * 60 * s, y - 110 * s)
    p1 = (x + d * 200 * s, y - 330 * s)
    p2 = (x + d * 300 * s, y - 210 * s)
    c.line([p0, p1], INK, 22 * s)
    c.line([p1, p2], INK, 16 * s)
    c.poly([(p2[0], p2[1]), (p2[0] + d * 40 * s, p2[1] + 30 * s), (p2[0] + d * 10 * s, p2[1] + 70 * s),
            (p2[0] - d * 26 * s, p2[1] + 40 * s)], INK, smooth=False)


@prop
def crane(c, L, x, y, s=1.0, **k):
    """A tower crane far off over new construction, with a red light on top."""
    INK = "#0e1012"
    c.line([(x, y), (x, y - 520 * s)], INK, 7 * s)
    for j in range(13):
        yy = y - j * 40 * s
        c.line([(x - 9 * s, yy), (x + 9 * s, yy - 40 * s)], INK, 1.6 * s)
    c.line([(x - 120 * s, y - 520 * s), (x + 360 * s, y - 520 * s)], INK, 6 * s)
    c.line([(x, y - 580 * s), (x + 360 * s, y - 520 * s)], INK, 2 * s)
    c.line([(x, y - 580 * s), (x - 120 * s, y - 520 * s)], INK, 2 * s)
    c.line([(x + 240 * s, y - 520 * s), (x + 240 * s, y - 380 * s)], INK, 1.5 * s)
    c.rect(x - 120 * s, y - 530 * s, x - 70 * s, y - 506 * s, INK)
    return [(x, y - 584 * s, (1.0, 0.25, 0.2), 26 * s, True, 0.8)]


@prop
def ward(c, L, x, y, s=1.0, lit=0.25, seed=2, **k):
    """A three-storey brick building with bars on its windows."""
    _bldg(c, L, x - 260 * s, x + 260 * s, y, 250 * s, lit, seed, bars=True, cols=10, rows=3)
    c.rect(x - 268 * s, y - 262 * s, x + 268 * s, y - 250 * s, "#120b08")


@prop
def prisonwall(c, L, x, y, s=1.0, h=200, tower=True, **k):
    """A tall plain stone prison wall across the picture, with one small guard tower."""
    c.rect(-20, y - h * s, 1100, y, "#3a3a36")
    for j in range(0, 1100, int(60 * s)):                                        # stone courses, faint
        c.line([(j, y - h * s), (j, y)], "#2e2e2a", 1.2, 0.5)
    for r in range(1, 6):
        yy = y - h * s * r / 6
        c.line([(-20, yy), (1100, yy)], "#2e2e2a", 1.2, 0.5)
    c.rect(-20, y - (h + 10) * s, 1100, y - h * s, "#2a2a26")
    out = []
    if tower:
        tx = x + 360 * s
        c.rect(tx - 40 * s, y - (h + 150) * s, tx + 40 * s, y - h * s, "#34342f")
        c.poly([(tx - 56 * s, y - (h + 150) * s), (tx + 56 * s, y - (h + 150) * s), (tx, y - (h + 196) * s)], "#1e1e1b", smooth=False)
        c.rect(tx - 26 * s, y - (h + 130) * s, tx + 26 * s, y - (h + 100) * s, "#0a0908")
        L.rect(tx - 26 * s, y - (h + 130) * s, tx + 26 * s, y - (h + 100) * s, WARM, 0.3)
        out.append((tx, y - (h + 115) * s, (1.0, 0.85, 0.6), 40 * s, False, 0.35))
    return out


@prop
def newprison(c, L, x, y, s=1.0, **k):
    """A new prison going up: long, low, pale concrete buildings with narrow windows, a fence line in front."""
    for j, (dx, w, h) in enumerate(((-220, 300, 110), (120, 360, 140), (430, 220, 90))):
        x0, x1 = x + (dx - w / 2) * s, x + (dx + w / 2) * s
        c.rect(x0, y - h * s, x1, y, "#6a6e70" if j % 2 else "#5e6264")
        c.rect(x0 - 4 * s, y - (h + 8) * s, x1 + 4 * s, y - h * s, "#4a4e50")
        for t in range(int(w / 28)):
            wx = x0 + (14 + t * 28) * s
            c.rect(wx, y - (h - 22) * s, wx + 5 * s, y - 26 * s, "#202426")
    for j in range(0, 1100, int(90 * s)):
        c.line([(j, y + 30 * s), (j, y - 90 * s)], "#2a2e30", 3 * s)
    c.line([(-10, y - 90 * s), (1100, y - 90 * s)], "#2a2e30", 2 * s)
