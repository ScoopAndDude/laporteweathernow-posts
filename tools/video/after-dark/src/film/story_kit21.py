"""Props for the Knox short (the night in 1910 when Earth was due to pass through the tail of Halley's Comet, and a
crowd on a Knox street corner came to see sparks that weren't there), added Nov. 16, 2026. They register in
story_kit3.PROPS like every prop.

    comet       a great comet low in the sky: a bright head and a long, faintly forked tail streaming up and away
                (ang = the tail's direction in degrees, 0 = straight up, negative leans left; length in px)
    storefronts a row of 1900s two-storey brick business blocks on a street corner, cornices and tall upper windows,
                awnings below; lit = share of lit windows; corner=True ends the row with a cross street at the right
    arclamp     an early electric street lamp: a tall pole with a carbon-arc globe on an arm (glows when lit)
    crowd1910   a crowd of townspeople seen from behind, men in hats and women in long skirts and wide hats, most
                faces turned up to the sky (n figures across spread px, rows deep; look = 0..1 how many look up)
    stargazer   a man in a dark coat and hat standing on a crate, one arm pointing up at the sky, a small brass
                telescope on a tripod beside him (flip=True points left); rim = the colour of a thin lamplight
                edge around him so he reads against dark storefronts (None for a plain silhouette);
                crate=False stands him on the sidewalk (the Knox account says only that he stood on the corner)
    sparks      tiny glowing motes drifting in the air above the crowd (n of them across w, between y and y-h);
                k = brightness: faint (0.3) for the moment only one man claims to see them, brighter as the
                crowd "sees" them too
    windowseal  a house window from inside at night, its cracks sealed with pasted paper strips and a rolled
                cloth along the sill, a small round tin on the sill (comet pills, no label), the comet beyond

Nothing shows a real person's likeness, a brand, a label or any lettering.
"""
import math

import numpy as np

import art
import story_kit3 as K3
from story_kit import W, H  # noqa: F401

prop = K3.prop
INK = "#050607"


def _rng(seed):
    return np.random.default_rng(seed)


@prop
def comet(c, L, x, y, s=1.0, ang=-28, length=820, k=1.0, seed=3, **kw):
    """A great comet with a long tail (see the top of this file)."""
    r = _rng(seed)
    a = math.radians(ang)
    ux, uy = math.sin(a), -math.cos(a)                                     # unit vector along the tail
    px, py = -uy, ux                                                       # across the tail
    for j in range(46):                                                    # the tail: overlapping soft streaks
        t = j / 45
        cx, cy = x + ux * length * t * s, y + uy * length * t * s
        wdt = (14 + 150 * t) * s
        c.ellipse(cx, cy, wdt, wdt * 0.5, "#9fb8c8", 0.05 * k * (1 - t * 0.7), blur=24 * s)
    for side, spread, br in ((-1, 0.10, 0.55), (1, 0.06, 0.4), (0, 0.0, 0.7)):
        pts = []
        for j in range(30):
            t = j / 29
            off = side * spread * length * t * t * s
            pts.append((x + ux * length * t * s + px * off, y + uy * length * t * s + py * off))
        for j in range(len(pts) - 1):
            t = j / 29
            c.line([pts[j], pts[j + 1]], "#cfe0ea", (10 - 8 * t) * s, 0.16 * br * k * (1 - t), blur=6 * s)
            L.line([pts[j], pts[j + 1]], "#cfe0ea", (8 - 6 * t) * s, 0.10 * br * k * (1 - t), blur=8 * s)
    c.glow(x, y, 60 * s, "#dfeaf2", 0.55 * k)
    c.circle(x, y, 7 * s, "#ffffff", 0.95)
    L.circle(x, y, 12 * s, "#e8f2ff", 0.8 * k, blur=6 * s)
    return [(x, y, (0.85, 0.92, 1.0), 70 * s * k, False)]


@prop
def storefronts(c, L, x, y, s=1.0, n=4, lit=0.3, corner=True, seed=5, color="#120e0c", **kw):
    """A row of brick business blocks (see the top of this file)."""
    r = _rng(seed)
    bw = 210 * s
    total = n * bw
    x0 = x - total / 2
    out = []
    for j in range(n):
        bx0 = x0 + j * bw
        bh = r.uniform(270, 330) * s
        c.rect(bx0, y - bh, bx0 + bw - 4 * s, y, color)
        c.rect(bx0 - 3 * s, y - bh - 16 * s, bx0 + bw - 1 * s, y - bh, "#0a0807")          # cornice
        for q in range(int(bw / (6 * s))):                                 # dentils under the cornice
            c.rect(bx0 + q * 6 * s, y - bh, bx0 + q * 6 * s + 3 * s, y - bh + 5 * s, "#080605")
        for q in range(3):                                                 # tall upper windows
            wx = bx0 + (q + 0.5) * (bw - 4 * s) / 3
            on = r.uniform() < lit
            c.rect(wx - 18 * s, y - bh + 40 * s, wx + 18 * s, y - bh + 130 * s, "#ffb45c" if on else "#060708", 0.9 if on else 1.0)
            c.poly([(wx - 20 * s, y - bh + 40 * s), (wx, y - bh + 26 * s), (wx + 20 * s, y - bh + 40 * s)], "#0a0807")
            if on:
                L.rect(wx - 18 * s, y - bh + 40 * s, wx + 18 * s, y - bh + 130 * s, "#ffb45c", 0.6)
        sh = 110 * s                                                       # the shopfront and its awning
        on = r.uniform() < lit * 1.4
        c.rect(bx0 + 14 * s, y - sh, bx0 + bw - 18 * s, y - 12 * s, "#ffb45c" if on else "#07080a", 0.8 if on else 1.0)
        if on:
            L.rect(bx0 + 14 * s, y - sh, bx0 + bw - 18 * s, y - 12 * s, "#ffb45c", 0.5)
            out.append((bx0 + bw / 2, y - sh / 2, (1.0, 0.75, 0.45), 90 * s, False))
        c.poly([(bx0 + 6 * s, y - sh - 8 * s), (bx0 + bw - 10 * s, y - sh - 8 * s), (bx0 + bw, y - sh + 30 * s),
                (bx0 - 4 * s, y - sh + 30 * s)], ["#3a1a14", "#1e2a22", "#2a2418"][j % 3])
        for q in range(8):                                                 # awning stripes
            sx0 = bx0 + q * bw / 8
            c.poly([(sx0 + 6 * s, y - sh - 8 * s), (sx0 + 6 * s + bw / 16, y - sh - 8 * s), (sx0 + bw / 16, y - sh + 30 * s),
                    (sx0 - 2 * s, y - sh + 30 * s)], "#000000", 0.25)
    if corner:
        c.rect(x0 + total, y - 2 * s, x0 + total + 300 * s, y + 4 * s, "#2a2a26", 0.7)     # the cross street's curb
    return out


@prop
def arclamp(c, L, x, y, s=1.0, lit=True, flip=False, **kw):
    """An early electric street lamp (see the top of this file)."""
    d = -1 if flip else 1
    c.rect(x - 5 * s, y - 470 * s, x + 5 * s, y, "#0c0d0e")
    c.rect(x - 12 * s, y - 30 * s, x + 12 * s, y, "#0c0d0e")
    c.line([(x, y - 460 * s), (x + d * 70 * s, y - 470 * s)], "#0c0d0e", 5 * s)
    gx, gy = x + d * 70 * s, y - 445 * s
    c.line([(gx, y - 470 * s), (gx, gy - 14 * s)], "#0c0d0e", 3 * s)
    c.ellipse(gx, gy, 13 * s, 17 * s, "#fff4dc" if lit else "#2a2a28", 0.95)
    if lit:
        L.circle(gx, gy, 20 * s, "#fff0d0", 0.9, blur=10 * s)
        return [(gx, gy, (1.0, 0.95, 0.85), 160 * s, False)]
    return []


@prop
def crowd1910(c, L, x, y, s=1.0, n=26, spread=1000, rows=3, look=0.85, seed=7, **kw):
    """A crowd seen from behind, faces turned up (see the top of this file)."""
    r = _rng(seed)
    per = max(1, n // rows)
    for row in range(rows):                                                # back rows first, smaller
        rs = s * (0.62 + 0.38 * row / max(1, rows - 1))
        ry = y - (rows - 1 - row) * 40 * s
        for j in range(per):
            fx = x - spread / 2 + (j + 0.5 + r.uniform(-0.3, 0.3)) * spread / per
            h = r.uniform(150, 182) * rs
            woman = r.uniform() < 0.42
            up = r.uniform() < look
            col = "#040506" if row == rows - 1 else ["#08090b", "#0b0c0e"][row % 2]
            info = art.figure(c, fx, ry, h, color=col, dress=woman, coat=not woman,
                              hat=None if woman else ("brim" if r.uniform() < 0.7 else "cap"),
                              arms=((8, 4), (-8, -4)), legs=(3, -3), lean=r.uniform(-0.3, 0.3))
            hx, hy, hr = info["head"]
            if woman:                                                      # a wide hat with a crown
                c.ellipse(hx, hy - hr * 0.55, hr * 2.4, hr * 0.42, col)
                c.ellipse(hx, hy - hr * 1.0, hr * 1.1, hr * 0.75, col)
            if up:                                                         # the face tipped up: a sliver of chin
                c.ellipse(hx + r.uniform(-0.3, 0.3) * hr, hy - hr * 0.2, hr * 0.62, hr * 0.32, "#1a1714", 0.55)
    return []


@prop
def stargazer(c, L, x, y, s=1.0, flip=False, scope=True, rim="#5a4a34", crate=True, **kw):
    """A man on a crate pointing at the sky, a telescope beside him (see the top of this file)."""
    d = -1 if flip else 1
    base = y
    if crate:
        c.rect(x - 46 * s, y - 52 * s, x + 46 * s, y, "#2a1e14")          # the crate
        for q in range(3):
            c.line([(x - 46 * s, y - 52 * s + q * 17 * s), (x + 46 * s, y - 52 * s + q * 17 * s)], "#120c08", 2 * s)
        c.line([(x - 46 * s, y - 52 * s), (x + 46 * s, y)], "#120c08", 2 * s, 0.7)
        base = y - 52 * s
    arms = ((20, 10), (165, 10)) if not flip else ((165, 10), (20, 10))
    if rim:                                                                # a thin rim of lamplight around him,
        for ox, oy in ((-2.5 * s, -1.5 * s), (2.5 * s, -1.5 * s), (0, -3 * s)):  # so he reads against dark storefronts
            art.figure(c, x + ox, base + oy, 210 * s, color=rim, coat=True, hat="brim", arms=arms,
                       legs=(4, -4), lean=-0.15 * d)
    art.figure(c, x, base, 210 * s, color=INK, coat=True, hat="brim", arms=arms, legs=(4, -4), lean=-0.15 * d)
    if scope:
        tx = x + d * 130 * s
        for lg in (-1, 0, 1):                                              # the tripod
            c.line([(tx, y - 120 * s), (tx + lg * 34 * s, y)], "#100c08", 4 * s)
        c.line([(tx - d * 20 * s, y - 110 * s), (tx + d * 70 * s, y - 180 * s)], "#7a5a28", 15 * s)   # the tube
        c.line([(tx + d * 62 * s, y - 174 * s), (tx + d * 74 * s, y - 183 * s)], "#b08a3a", 18 * s)
    return []


@prop
def sparks(c, L, x, y, s=1.0, n=60, w=900, h=500, k=0.6, seed=9, **kw):
    """Glowing motes drifting above the crowd (see the top of this file)."""
    r = _rng(seed)
    out = []
    for j in range(n):
        px, py = x + r.uniform(-w / 2, w / 2), y - r.uniform(0, h)
        rad = r.uniform(1.5, 4.0) * s
        c.circle(px, py, rad, "#ffcf7a", min(1.0, 0.6 * k + 0.2))
        L.circle(px, py, rad * 3, "#ffb04a", 0.5 * k, blur=4 * s)
        if j % 6 == 0:
            out.append((px, py, (1.0, 0.75, 0.35), 18 * s * k, True))
    return out


@prop
def windowseal(c, L, x, y, s=1.0, seed=4, **kw):
    """A sealed window seen from inside, a tin on the sill (see the top of this file)."""
    r = _rng(seed)
    ww, wh = 420 * s, 560 * s
    x0, y0 = x - ww / 2, y - wh
    wall = "#0f0b08"                                                       # the room's wall all around the window
    c.rect(-20, -20, W + 20, y0 - 30 * s, wall)
    c.rect(-20, y + 40 * s, W + 20, H + 20, wall)
    c.rect(-20, y0 - 30 * s, x0 - 30 * s, y + 40 * s, wall)
    c.rect(x0 + ww + 30 * s, y0 - 30 * s, W + 20, y + 40 * s, wall)
    for (fx0, fy0, fx1, fy1) in ((x0 - 30 * s, y0 - 30 * s, x0 + ww + 30 * s, y0), (x0 - 30 * s, y, x0 + ww + 30 * s, y + 40 * s),
                                 (x0 - 30 * s, y0, x0, y), (x0 + ww, y0, x0 + ww + 30 * s, y)):
        c.rect(fx0, fy0, fx1, fy1, "#1c140e")                              # the window frame
    c.rect(x0 + ww / 2 - 7 * s, y0, x0 + ww / 2 + 7 * s, y, "#1c140e")     # muntins
    c.rect(x0, y0 + wh / 2 - 7 * s, x0 + ww, y0 + wh / 2 + 7 * s, "#1c140e")
    for (ax, ay, bx, by) in ((0, 0, 1, 0), (0, 1, 1, 1), (0, 0, 0, 1), (1, 0, 1, 1), (0.5, 0, 0.5, 1), (0, 0.5, 1, 0.5)):
        sx0, sy0 = x0 + ax * ww, y0 + ay * wh                              # pasted paper strips over the cracks
        sx1, sy1 = x0 + bx * ww, y0 + by * wh
        if sy0 == sy1:
            c.rect(sx0, sy0 - 9 * s, sx1, sy0 + 9 * s, "#cfc4a6", 0.85)
        else:
            c.rect(sx0 - 9 * s, sy0, sx0 + 9 * s, sy1, "#cfc4a6", 0.85)
    c.rect(x0 - 50 * s, y + 4 * s, x0 + ww + 50 * s, y + 28 * s, "#2a1e14")  # the sill
    for q in range(9):                                                     # a rolled cloth along the sill
        c.circle(x0 + 20 * s + q * (ww - 40 * s) / 8, y - 6 * s, 16 * s, "#5a4a3a")
    tx = x0 + ww * 0.78                                                    # a small round tin, no label
    c.rect(tx - 34 * s, y - 50 * s, tx + 34 * s, y - 10 * s, "#8a8478")
    c.ellipse(tx, y - 50 * s, 34 * s, 9 * s, "#a8a294")
    c.ellipse(tx, y - 10 * s, 34 * s, 9 * s, "#6a6458")
    return []
