"""Props for the Fish Lake short (Swift & Co.'s ice houses near Fish Lake, LaPorte County, and the 1897 handcar
death on the Grand Trunk), added Nov. 16, 2026. They register in story_kit3.PROPS like every prop.

    handcar   an 1890s railroad pump handcar, side on, on the rails at y: a flat deck on four small wheels with a
              walking-beam pump handle. n = figures aboard (0 for an empty car); jump=True draws them leaping off
              both sides, arms out (no one hit, no one lying on the ground); flip mirrors it
    icehouse  a huge windowless 1890s ice house: board walls, a low roof, and an inclined elevator running up its
              side to the loading doors at the top. w, h its size (default about 500 x 300 px at s=1); snow=True
              snow on the roof; fire=0..1 flames along the roof line and from the doors with smoke (no people);
              ruin=True only the low foundation and a few posts are left
    icecrew   a crew of n men in short winter coats over trousers, with caps, on the ice (spread px wide), a few bent
              to their work, no tools (art.figure's flared coat reads as a dress, so they are drawn here)
    iceharvest  story_kit3's iceblocks (sawn channel, stacked blocks, horse and sled) with the sled driver drawn the
              same way; driver=False leaves him out

Nothing shows a body, an injured person, a real person's likeness, a brand or any lettering.
"""
import math

import numpy as np

import art
import story_kit3 as K3
from story_kit import W, H

prop = K3.prop
INK = "#040405"


def _rng(seed):
    return np.random.default_rng(seed)


@prop
def handcar(c, L, x, y, s=1.0, n=4, jump=False, flip=False, seed=3, color=INK, **k):
    """An 1890s pump handcar on the rails at y (see the top of this file)."""
    r = _rng(seed)
    d = -1 if flip else 1
    dw, dh = 150 * s, 14 * s
    for wx in (-0.62, 0.62):                                                 # wheels
        c.circle(x + wx * dw, y - 12 * s, 13 * s, color)
        c.circle(x + wx * dw, y - 12 * s, 5 * s, "#1c1e20")
    c.rect(x - dw, y - 26 * s - dh, x + dw, y - 26 * s, color)               # the deck
    c.rect(x - 10 * s, y - 92 * s, x + 10 * s, y - 40 * s, color)            # the pump post
    tilt = 0.18 if not jump else -0.35
    hx0, hy0 = x - 95 * s, y - 100 * s - tilt * 60 * s                       # the walking-beam handle
    hx1, hy1 = x + 95 * s, y - 100 * s + tilt * 60 * s
    c.line([(hx0, hy0), (hx1, hy1)], color, max(1.0, 7 * s))
    for hx, hy in ((hx0, hy0), (hx1, hy1)):
        c.line([(hx - 22 * s, hy), (hx + 22 * s, hy)], color, max(1.0, 6 * s))
    if n <= 0:
        return []
    if not jump:
        for j in range(int(n)):
            fx = x + (-0.8 + 1.6 * j / max(1, n - 1)) * dw * 0.8
            art.figure(c, fx, y - 40 * s, 128 * s, color=color, coat=True, hat="cap",
                       arms=((40, 70), (-40, -70)))
        return []
    for j in range(int(n)):                                                  # men leaping clear, both sides
        side = -1 if j % 2 == 0 else 1
        fx = x + side * (dw + r.uniform(30, 120) * s)
        fy = y - 40 * s - r.uniform(30, 90) * s
        art.figure(c, fx, fy, 118 * s, color=color, coat=True, hat="cap", lean=side * 0.9,
                   arms=((105, 85), (-105, -85)), legs=(28, -28))
    return []


@prop
def icehouse(c, L, x, y, s=1.0, w=520, h=300, snow=False, fire=0.0, ruin=False, flip=False, seed=5,
             wall="#2a2622", roof="#151311", **k):
    """A huge windowless ice house with an inclined elevator up its side (see the top of this file)."""
    r = _rng(seed)
    d = -1 if flip else 1
    hw, hh = w * s / 2, h * s
    out = []
    if ruin:                                                                 # only the foundation is left
        c.rect(x - hw, y - 16 * s, x + hw, y, "#3a3632")
        for j in range(7):
            px = x - hw + r.uniform(0.05, 0.95) * 2 * hw
            ph = r.uniform(20, 70) * s
            c.rect(px - 5 * s, y - ph, px + 5 * s, y, "#1a1714")
        return out
    c.rect(x - hw, y - hh, x + hw, y, wall)                                  # the walls
    for j in range(1, int(2 * hw / (14 * s))):                               # vertical boards
        bx = x - hw + j * 14 * s
        c.line([(bx, y - hh), (bx, y)], "#000000", max(0.6, 1.2 * s), 0.25)
    rp = 70 * s
    c.poly([(x - hw - 14 * s, y - hh), (x - hw + rp * 1.4, y - hh - rp), (x + hw - rp * 1.4, y - hh - rp),
            (x + hw + 14 * s, y - hh)], roof)                                # a low hip roof
    if snow:
        c.poly([(x - hw - 14 * s, y - hh), (x - hw + rp * 1.4, y - hh - rp), (x + hw - rp * 1.4, y - hh - rp),
                (x + hw + 14 * s, y - hh), (x + hw + 4 * s, y - hh - 10 * s), (x + hw - rp * 1.4, y - hh - rp + 12 * s),
                (x - hw + rp * 1.4, y - hh - rp + 12 * s), (x - hw - 4 * s, y - hh - 10 * s)], "#b8c4cc", 0.85)
    for j in range(5):                                                       # loading doors near the top
        dx = x - hw + (j + 0.5) * 2 * hw / 5
        c.rect(dx - 16 * s, y - hh + 14 * s, dx + 16 * s, y - hh + 66 * s, "#0d0b09")
    ex0 = x + d * (hw + 260 * s)                                             # the inclined elevator
    ey0 = y + 10 * s
    ex1 = x + d * (hw - 30 * s)
    ey1 = y - hh + 20 * s
    for off in (0, 22 * s):
        c.line([(ex0, ey0 - off), (ex1, ey1 - off)], "#120f0c", max(1.0, 8 * s))
    steps = 9
    for j in range(steps + 1):                                               # its trestle legs
        t = j / steps
        px, py = ex0 + (ex1 - ex0) * t, ey0 + (ey1 - ey0) * t
        c.line([(px, py), (px, y)], "#120f0c", max(1.0, 4 * s))
        if j < steps:
            qx, qy = ex0 + (ex1 - ex0) * (t + 1 / steps), ey0 + (ey1 - ey0) * (t + 1 / steps)
            c.line([(px, y), (qx, qy)], "#120f0c", max(0.8, 2 * s), 0.8)
    if fire > 0:
        for j in range(int(10 + 14 * fire)):                                 # flames along the roof
            fx = x - hw + r.uniform(0.05, 0.95) * 2 * hw
            fh = r.uniform(60, 190) * s * fire
            base = y - hh - rp * r.uniform(0.2, 0.9)
            c.poly([(fx - 26 * s, base + 10 * s), (fx + r.uniform(-12, 12) * s, base - fh), (fx + 26 * s, base + 10 * s)],
                   "#ff8a2a", 0.85, blur=6 * s)
            c.poly([(fx - 12 * s, base + 6 * s), (fx + r.uniform(-6, 6) * s, base - fh * 0.6), (fx + 12 * s, base + 6 * s)],
                   "#ffd27a", 0.8, blur=3 * s)
        for j in range(5):                                                   # fire in the doors
            dx = x - hw + (j + 0.5) * 2 * hw / 5
            c.rect(dx - 16 * s, y - hh + 14 * s, dx + 16 * s, y - hh + 66 * s, "#ff9a3a", 0.9 * fire)
            L.rect(dx - 16 * s, y - hh + 14 * s, dx + 16 * s, y - hh + 66 * s, "#ffb45c", 0.8 * fire)
        for j in range(6):                                                   # smoke
            sx = x + r.uniform(-0.6, 0.6) * hw
            c.circle(sx, y - hh - rp - r.uniform(80, 360) * s, r.uniform(60, 120) * s, "#1a1614", 0.5, blur=30 * s)
        out.append((x, y - hh - rp * 0.5, (1.0, 0.55, 0.2), 260 * s * fire, True))
        out.append((x - hw * 0.5, y - hh, (1.0, 0.6, 0.25), 140 * s * fire, True))
        out.append((x + hw * 0.5, y - hh, (1.0, 0.6, 0.25), 140 * s * fire, True))
    return out


def _workman(c, fx, fy, h, bent=False, side=1, color=INK):
    """A 1890s workman: cap, short straight coat over trousers (not the flared coat, which reads as a dress)."""
    art.figure(c, fx, fy, h, color=color, coat=False, hat="cap", legs=(5, -5),
               lean=(0.8 if bent else 0.0) * side,
               arms=((30, 60), (-30, -60)) if bent else ((10, 6), (-10, -6)))
    c.poly([(fx - 0.094 * h, fy - 0.55 * h), (fx + 0.094 * h, fy - 0.55 * h),
            (fx + 0.106 * h, fy - 0.30 * h), (fx - 0.106 * h, fy - 0.30 * h)], color, smooth=False)


@prop
def icecrew(c, L, x, y, s=1.0, n=5, spread=260, seed=4, color=INK, **k):
    """A work crew of n men in short winter coats, trousers and caps standing on the ice, a few bent to their work;
    no tools drawn (the sources don't say what they held)."""
    r = _rng(seed)
    for j in range(int(n)):
        fx = x - spread * s / 2 + (j + 0.5) * spread * s / n + r.uniform(-14, 14) * s
        h = r.uniform(124, 134) * s
        bent = r.random() < 0.4
        _workman(c, fx, y + r.uniform(-6, 6) * s, h * (0.9 if bent else 1.0), bent=bent,
                 side=(1 if r.random() < 0.5 else -1), color=color)
    return []


@prop
def iceharvest(c, L, x, y, s=1.0, driver=True, **k):
    """story_kit3's iceblocks (sawn channel, stacked blocks, horse and sled) with the driver drawn as a workman in a
    short coat and trousers."""
    c.poly([(x - 300 * s, y), (x + 140 * s, y - 60 * s), (x + 200 * s, y - 40 * s), (x - 200 * s, y + 40 * s)], "#0a1620")
    for j in range(6):
        for t in range(1 + j % 3):
            bx, by = x + (-260 + j * 70) * s, y - (70 + t * 34) * s + j * 4 * s
            c.rect(bx, by, bx + 60 * s, by + 32 * s, "#9ab4c4", 0.85)
            c.line([(bx, by), (bx + 60 * s, by)], "#d8e8f0", 2, 0.8)
    K3.horse(c, x + 300 * s, y - 30 * s, 0.9 * s)
    c.rect(x + 150 * s, y - 60 * s, x + 250 * s, y - 40 * s, INK)
    if driver:
        _workman(c, x + 60 * s, y - 20 * s, 124 * s)
    return []
