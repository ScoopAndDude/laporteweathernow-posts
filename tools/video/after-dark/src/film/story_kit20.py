"""Props for the Kingsbury Ordnance Plant contamination shorts (the remade Kingsford Heights short and the new
Kingsbury short, Scoop, Nov. 16, 2026: "include how toxic and contaminated from the munitions plant it is"),
added Nov. 16, 2026. They register in story_kit3.PROPS like every prop.

    plumecut    a cut-away of the ground under the old plant: the surface at y, sandy layers, the water table, and
                a dark plume sinking from under the old buildings (at src, 0..1 across w) into the groundwater and
                drifting along it (plume = strength, drift = -1..1 sideways along the water table).
                buildings=True draws the long low plant buildings on the surface above the source; ruin=True
                draws them roofless. Nothing is drawn under any house.
    monwell     a groundwater monitoring well: a locked steel protective casing on a small concrete pad, ringed
                by yellow bollards; cut=True also shows the pipe running down below the surface
    drums       old 55-gallon steel drums half-buried in dirt, rusted, dented and tipped, a dark stain around
                them; dig=True adds the arm and bucket of a modern excavator digging them out from the right
    warnsign    a cable gate closing a two-track lane into tall grass, with a warning sign on a post beside it;
                text is the sign's words. Signs show only words really on the real sign: the DNR's map legend
                says "Contaminated Area/No Trespassing" but its real signs' words aren't known, so the Kingsbury
                shorts use sign=False (the gate alone) and put the legend's words on a quote card.
                lane=False leaves out the lane and gate
    lineruins   the old plant's long one-storey line buildings as ruins: rows of bare concrete walls with empty
                window openings in the grass, roofs gone (n rows across spread px, receding)
    shellstack  artillery shells standing in rows on wooden pallets, as a loading line turned them out (no fuzes)

Nothing shows a person hurt, a body, a real person's likeness, a brand or a logo. The only lettering is the
warning sign's text.
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


def _wave(x, seed, amp, k=1.0):
    return amp * (math.sin(x * 0.011 * k + seed) * 0.6 + math.sin(x * 0.027 * k + seed * 1.7) * 0.4)


def _band_poly(x0, x1, ytop_f, ybot_f, step=12):
    pts = [(xx, ytop_f(xx)) for xx in np.arange(x0, x1 + step, step)]
    pts += [(xx, ybot_f(xx)) for xx in np.arange(x1, x0 - step, -step)]
    return pts


def _longbuilding(c, L, bx, by, bw, bh, s, roof=True, ruin=False, lit=0.0, seed=1, color="#14171a"):
    """A long low one-storey plant building (side on), bottom left at (bx - bw/2, by)."""
    r = _rng(seed)
    x0, x1 = bx - bw / 2, bx + bw / 2
    if ruin:
        top = [(x0, by - bh * r.uniform(0.55, 0.8))]
        xx = x0
        while xx < x1:
            xx = min(x1, xx + r.uniform(18, 46) * s)
            top.append((xx, by - bh * r.uniform(0.35, 0.95)))
        c.poly([(x0, by)] + top + [(x1, by)], "#3a3b38")
        c.poly([(x0, by)] + [(px, py + 6 * s) for px, py in top] + [(x1, by)], "#2a2b29", 0.6)
    else:
        c.rect(x0, by - bh, x1, by, color)
        if roof:
            c.rect(x0 - 6 * s, by - bh - 7 * s, x1 + 6 * s, by - bh, "#0b0d0f")
    nwin = max(3, int(bw / (34 * s)))
    for j in range(nwin):                                                  # small windows in a row
        wx = x0 + (j + 0.5) * bw / nwin
        wy0, wy1 = by - bh * 0.62, by - bh * 0.34
        if ruin:
            c.rect(wx - 7 * s, wy0, wx + 7 * s, wy1, "#0e0f0e")
        else:
            on = r.uniform() < lit
            c.rect(wx - 6 * s, wy0, wx + 6 * s, wy1, "#ffb45c" if on else "#06070a", 0.9 if on else 1.0)
            if on:
                L.rect(wx - 6 * s, wy0, wx + 6 * s, wy1, "#ffb45c", 0.7)


# ------------------------------------------------------------------------------------------- the ground, cut open

@prop
def plumecut(c, L, x, y, s=1.0, w=1240, depth=420, plume=1.0, src=0.62, drift=0.55, water=0.6, buildings=True,
             ruin=False, bs=1.7, seed=4, **k):
    """A cut-away of the ground under the old plant with a dark plume in it (see the top of this file)."""
    r = _rng(seed)
    x0, x1 = x - w / 2, x + w / 2
    d = depth * s
    wy = y + water * d                                                     # the water table
    layers = [(0.0, 0.07, "#2a2117"), (0.07, 0.3, "#5a4930"), (0.3, 0.52, "#6a5838"), (0.52, 1.0, "#4b4436")]
    for j, (a0, a1, col) in enumerate(layers):
        c.poly(_band_poly(x0, x1, lambda xx, a=a0, j=j: y + a * d + (_wave(xx, seed + j, 6 * s) if a > 0 else 0),
                          lambda xx, a=a1, j=j: y + a * d + _wave(xx, seed + j + 1, 6 * s)), col)
    for j in range(260):                                                   # sand grains and pebbles
        gx, gy = r.uniform(x0, x1), y + r.uniform(0.06, 0.98) * d
        c.circle(gx, gy, r.uniform(0.8, 2.4) * s, "#8a7a5a" if r.uniform() < 0.6 else "#2e281f", 0.55)
    c.poly(_band_poly(x0, x1, lambda xx: wy + _wave(xx, seed + 9, 4 * s), lambda xx: y + d), "#28465a", 0.38)
    c.line([(xx, wy + _wave(xx, seed + 9, 4 * s)) for xx in np.arange(x0, x1 + 10, 10)], "#7fb0c8", 2.4 * s, 0.75)
    for j in range(9):                                                     # ripples in the saturated sand
        rx = r.uniform(x0 + 60, x1 - 60)
        ry = wy + r.uniform(0.15, 0.85) * (y + d - wy)
        c.line([(rx - 30 * s, ry), (rx + 30 * s, ry)], "#8fbcd2", 1.4 * s, 0.25)
    if plume > 0:
        sx = x0 + src * w
        sdir = 1 if drift >= 0 else -1
        pts = []                                                           # a sinking column, then a tongue along the water
        for j in range(26):
            t = j / 25
            px = sx + sdir * abs(drift) * w * 0.42 * max(0.0, t - 0.35) / 0.65 + _wave(t * 900, seed + 3, 10 * s)
            py = y + 12 * s + (wy - y + 0.18 * (y + d - wy)) * min(1.0, t / 0.4)
            pts.append((px, py))
        for j, (px, py) in enumerate(pts):
            t = j / 25
            rad = (22 + 70 * t) * s
            c.ellipse(px, py, rad * (1.0 + 1.6 * max(0, t - 0.35)), rad * 0.62, "#10160a", 0.42 * plume, blur=14 * s)
        for j, (px, py) in enumerate(pts[::2]):
            c.ellipse(px, py, (18 + 40 * j / 13) * s, (10 + 16 * j / 13) * s, "#34401a", 0.45 * plume, blur=8 * s)
        for j in range(int(140 * plume)):                                  # specks in the plume
            t = r.uniform(0.05, 1.0)
            i = min(25, int(t * 25))
            px, py = pts[i]
            spread = (22 + 80 * t) * s
            c.circle(px + r.normal(0, spread * (1 + 1.2 * max(0, t - 0.35))), py + r.normal(0, spread * 0.4),
                     r.uniform(1.0, 2.6) * s, "#d2d47e", r.uniform(0.35, 0.75))
    c.rect(x0, y - 3 * s, x1, y + 2 * s, "#0b0c09")                         # the surface line
    for j in range(int(w / (9 * s))):                                      # grass along the top
        gx = x0 + j * 9 * s + r.uniform(-3, 3) * s
        gh = r.uniform(6, 22) * s
        c.line([(gx, y), (gx + r.uniform(-4, 4) * s, y - gh)], "#0a0d08", max(1.0, 1.6 * s))
    if buildings:
        sx = x0 + src * w
        for j, (off, bw, bh) in enumerate(((-0.2, 260, 70), (0.04, 300, 78), (0.25, 200, 64))):
            bx = sx + off * w
            if x0 + 40 < bx < x1 - 40:
                _longbuilding(c, L, bx, y, bw * s * bs * 0.75, bh * s * bs, s * bs, ruin=ruin, seed=seed + j)
        c.poly([(sx - 0.36 * w, y), (sx - 0.32 * w, y - 30 * s * bs), (sx - 0.28 * w, y)], "#0c0f0b")   # earth berms
        c.poly([(sx + 0.15 * w, y), (sx + 0.175 * w, y - 26 * s * bs), (sx + 0.2 * w, y)], "#0c0f0b")
    return []


@prop
def monwell(c, L, x, y, s=1.0, bollards=True, cut=False, **k):
    """A groundwater monitoring well (see the top of this file)."""
    c.ellipse(x, y + 4 * s, 120 * s, 22 * s, "#000000", 0.35, blur=6 * s)
    c.poly([(x - 92 * s, y), (x + 92 * s, y), (x + 80 * s, y - 16 * s), (x - 80 * s, y - 16 * s)], "#6e6c66")
    c.rect(x - 92 * s, y - 2 * s, x + 92 * s, y + 4 * s, "#4a4844")
    cw, ch = 44 * s, 150 * s                                               # the steel protective casing
    c.rect(x - cw / 2, y - 16 * s - ch, x + cw / 2, y - 16 * s, "#2c3134")
    c.rect(x - cw / 2, y - 16 * s - ch, x - cw / 2 + 7 * s, y - 16 * s, "#4a5256")
    c.rect(x - cw / 2 - 5 * s, y - 16 * s - ch - 14 * s, x + cw / 2 + 5 * s, y - 16 * s - ch, "#3a4144")
    c.rect(x + cw / 2 - 2 * s, y - 16 * s - ch + 10 * s, x + cw / 2 + 10 * s, y - 16 * s - ch + 22 * s, "#8a8a80")
    c.circle(x + cw / 2 + 4 * s, y - 16 * s - ch + 30 * s, 6 * s, "#9a9a8e")       # the padlock
    c.rect(x - 8 * s, y - 16 * s - ch * 0.55, x + 8 * s, y - 16 * s - ch * 0.47, "#6a7074")  # a blank tag plate
    if bollards:
        for bx, by, bs in ((-120, 10, 1.0), (120, 10, 1.0), (-70, -30, 0.8), (70, -30, 0.8)):
            px, py = x + bx * s, y + by * s
            bh, bw = 120 * s * bs, 13 * s * bs
            c.rect(px - bw, py - bh, px + bw, py, "#c9a21c")
            c.rect(px - bw, py - bh, px - bw + 4 * s, py, "#e6c54a", 0.7)
            c.ellipse(px, py - bh, bw, bw * 0.45, "#e0bc3a")
            for q in (0.3, 0.6):
                c.rect(px - bw, py - bh * q - 5 * s, px + bw, py - bh * q + 5 * s, "#1a1a16", 0.8)
    if cut:
        c.rect(x - 9 * s, y + 6 * s, x + 9 * s, y + 360 * s, "#d8d8d0", 0.55)
        for j in range(8):
            c.line([(x - 9 * s, y + 280 * s + j * 10 * s), (x + 9 * s, y + 280 * s + j * 10 * s)], "#000000", 1.2 * s, 0.6)
    return []


# ------------------------------------------------------------------------------------------- drums and the dig

def _drum(c, cx, cy, s, ang, rust, r, sunk):
    """One 55-gallon drum standing (ang = tilt in degrees), centre bottom at (cx, cy)."""
    dw, dh = 52 * s, 80 * s
    body = ["#2e3a44", "#3a3020", "#40362a", "#2a3238"][int(r.integers(0, 4))]
    c.c.save()
    c.c.rotate(ang, cx, cy)
    c.rect(cx - dw / 2, cy - dh, cx + dw / 2, cy, body)
    c.rect(cx - dw / 2, cy - dh, cx - dw / 2 + 8 * s, cy, "#ffffff", 0.07)
    for q in (0.33, 0.66):                                                 # rolling hoops
        c.rect(cx - dw / 2, cy - dh * q - 2.5 * s, cx + dw / 2, cy - dh * q + 2.5 * s, "#000000", 0.4)
    c.ellipse(cx, cy - dh, dw / 2, 7 * s, "#1a1a18")
    c.ellipse(cx, cy - dh, dw / 2 - 4 * s, 5 * s, body)
    for j in range(int(3 + 6 * rust)):                                     # rust blooms and streaks
        rx = cx + r.uniform(-0.45, 0.45) * dw
        ry = cy - r.uniform(0.1, 0.95) * dh
        c.ellipse(rx, ry, r.uniform(4, 12) * s, r.uniform(3, 9) * s, "#7a3c16", r.uniform(0.4, 0.8), blur=2 * s)
        c.line([(rx, ry), (rx + r.uniform(-2, 2) * s, ry + r.uniform(8, 26) * s)], "#5a2a10", 1.6 * s, 0.6)
    if r.uniform() < 0.4:                                                  # a dent
        c.ellipse(cx + r.uniform(-0.2, 0.2) * dw, cy - dh * r.uniform(0.3, 0.7), 9 * s, 13 * s, "#000000", 0.35, blur=3 * s)
    c.c.restore()


@prop
def drums(c, L, x, y, s=1.0, n=16, spread=760, sunk=0.45, rows=3, stain=True, dig=False, seed=6,
          dirt="#2c2419", **k):
    """Old drums half-buried in the dirt (see the top of this file)."""
    r = _rng(seed)
    if stain:
        c.ellipse(x, y - 10 * s, spread * 0.55, 60 * s, "#0a0b08", 0.75, blur=18 * s)
        c.ellipse(x + 40 * s, y - 6 * s, spread * 0.3, 28 * s, "#2a3424", 0.35, blur=8 * s)   # a dull sheen
    per = max(1, n // rows)
    for row in range(rows):                                                # back rows first
        rs = s * (0.62 + 0.19 * row)
        ry = y - (rows - 1 - row) * 46 * s
        for j in range(per):
            cx = x - spread / 2 + (j + 0.5 + r.uniform(-0.25, 0.25)) * spread / per
            ang = r.uniform(-14, 14) if r.uniform() < 0.6 else r.uniform(-32, 32)
            _drum(c, cx, ry + 8 * rs, rs, ang, r.uniform(0.4, 1.0), r, sunk)
        mound = []                                                         # dirt heaped over the drums' lower part
        mx0, mx1 = x - spread / 2 - 90 * s, x + spread / 2 + 90 * s
        for xx in np.arange(mx0, mx1 + 1, 14 * s):
            edge = min(1.0, (xx - mx0) / (120 * s), (mx1 - xx) / (120 * s))   # slopes down at both ends
            mound.append((xx, ry + 30 * s - (110 * rs * sunk + 30 * s) * max(0.0, edge) + _wave(xx, seed + row, 9 * s) * edge))
        c.poly([(mx0, ry + 40 * s)] + mound + [(mx1, ry + 40 * s)], dirt, smooth=False)
        c.line(mound, "#4a3c2a", 2.2 * s, 0.6)
        for j in range(40):
            c.circle(r.uniform(x - spread / 2, x + spread / 2), ry - r.uniform(0, 60) * rs * sunk,
                     r.uniform(1, 3) * s, "#6a5a40", 0.5)
    if dig:                                                                # an excavator's arm and bucket, from the right
        bx, by = x + spread * 0.42, y - 60 * s
        boom = [(x + spread * 0.75, y - 360 * s), (x + spread * 0.55, y - 330 * s), (bx + 40 * s, y - 170 * s)]
        c.line(boom[:2], "#c79a22", 30 * s)
        c.line(boom[1:], "#c79a22", 24 * s)
        c.line([(x + spread * 0.75, y - 360 * s), (x + spread * 0.75 + 30 * s, y - 420 * s)], "#c79a22", 34 * s)
        c.line([(x + spread * 0.62, y - 300 * s), (bx + 52 * s, y - 210 * s)], "#7a7a74", 6 * s)    # a ram
        c.poly([(bx - 50 * s, by - 60 * s), (bx + 50 * s, by - 110 * s), (bx + 64 * s, by - 20 * s),
                (bx + 10 * s, by + 18 * s), (bx - 56 * s, by - 6 * s)], "#2a2a26")
        for j in range(5):                                                 # teeth
            tx = bx - 50 * s + j * 22 * s
            c.poly([(tx, by - 4 * s + j * 4 * s), (tx + 10 * s, by + 14 * s + j * 4 * s), (tx + 18 * s, by - 2 * s + j * 4 * s)], "#1a1a18")
        _drum(c, bx + 6 * s, by - 18 * s, s * 0.8, -58, 0.9, r, 0)
    return []


# ------------------------------------------------------------------------------------------- the sign

@prop
def warnsign(c, L, x, y, s=1.0, text="CONTAMINATED AREA|NO TRESPASSING", lane=True, sign=True, seed=3, **k):
    """A warning sign where a cable gate closes a lane into tall grass (see the top of this file)."""
    r = _rng(seed)
    if lane:                                                               # a two-track lane running into the field
        for side in (-1, 1):
            c.poly([(x + side * 70 * s, y + 140 * s), (x + side * 130 * s, y + 140 * s),
                    (x + side * 22 * s, y - 120 * s), (x + side * 12 * s, y - 120 * s)], "#2a261c", 0.9)
        for side in (-1, 1):                                               # the gate posts and a sagging cable
            px = x + side * 210 * s
            c.rect(px - 9 * s, y - 120 * s, px + 9 * s, y + 20 * s, "#26282a")
            c.ellipse(px, y - 120 * s, 10 * s, 4 * s, "#3a3c3e")
        c.line([(x - 210 * s, y - 90 * s), (x - 70 * s, y - 70 * s), (x + 70 * s, y - 70 * s), (x + 210 * s, y - 90 * s)],
               "#9a9a90", 3 * s, 0.85)
    sx = x - (300 if lane else 0) * s                                      # the sign post
    if sign:
        c.rect(sx - 7 * s, y - 330 * s, sx + 7 * s, y + 20 * s, "#2c2e30")
        c.rect(sx - 7 * s, y - 330 * s, sx - 3 * s, y + 20 * s, "#4a4e50")
    for j in range(int(220 * s)):                                          # tall grass
        gx = x + r.uniform(-560, 560) * s
        gy = y + r.uniform(-20, 150) * s
        gh = r.uniform(40, 120) * s * (0.6 + 0.6 * (gy - y + 20 * s) / (170 * s))
        c.line([(gx, gy), (gx + r.uniform(-14, 14) * s, gy - gh)], "#0b0e08" if r.uniform() < 0.7 else "#1e2414",
               max(1.0, r.uniform(1.2, 2.6) * s))
    if not sign:
        return []
    return ("sign", text, sx, y - 250 * s, 330 * s, 150 * s, (222, 196, 70), (24, 20, 14))


# ------------------------------------------------------------------------------------------- the old plant

@prop
def lineruins(c, L, x, y, s=1.0, n=5, spread=980, seed=8, **k):
    """Roofless concrete line buildings in the grass (see the top of this file)."""
    r = _rng(seed)
    for j in range(n):                                                     # far rows first
        t = j / max(1, n - 1)
        ry = y - (1 - t) * 190 * s
        rs = s * (0.5 + 0.9 * t)
        bw = r.uniform(0.55, 0.85) * spread * (0.6 + 0.5 * t)
        bx = x + r.uniform(-0.25, 0.25) * spread
        _longbuilding(c, L, bx, ry, bw, 92 * rs, rs, ruin=True, seed=seed + j)
        for q in range(int(40 * rs)):                                      # grass and saplings in front
            gx = bx + r.uniform(-0.55, 0.55) * bw
            c.line([(gx, ry + 2 * s), (gx + r.uniform(-6, 6) * rs, ry - r.uniform(10, 40) * rs)], "#0a0d08",
                   max(1.0, 1.8 * rs))
        if r.uniform() < 0.6:
            tx = bx + r.uniform(-0.4, 0.4) * bw
            art.tree(c, tx, ry, r.uniform(90, 160) * rs, seed=seed + 30 + j, color="#050806", depth=6, spread=0.5)
    return []


@prop
def shellstack(c, L, x, y, s=1.0, rows=3, cols=8, seed=2, **k):
    """Artillery shells standing on pallets (see the top of this file)."""
    r = _rng(seed)
    for row in range(rows):                                                # back row first
        rs = s * (0.72 + 0.28 * row / max(1, rows - 1))
        ry = y - (rows - 1 - row) * 105 * s
        pw = cols * 34 * rs
        c.rect(x - pw / 2 - 10 * rs, ry - 12 * rs, x + pw / 2 + 10 * rs, ry, "#4a3420")       # the pallet
        for q in range(5):
            c.rect(x - pw / 2 - 10 * rs + q * (pw + 20 * rs) / 5, ry - 12 * rs,
                   x - pw / 2 - 10 * rs + q * (pw + 20 * rs) / 5 + 4 * rs, ry, "#2a1c10")
        for j in range(cols):
            cx = x - pw / 2 + (j + 0.5) * pw / cols
            bh, bw = 92 * rs, 11 * rs
            base = ry - 12 * rs
            c.rect(cx - bw, base - bh * 0.72, cx + bw, base, "#3e4a2a")
            c.rect(cx - bw, base - bh * 0.72, cx - bw + 4 * rs, base, "#6a7a46", 0.6)
            c.rect(cx - bw - 1 * rs, base - bh * 0.18, cx + bw + 1 * rs, base - bh * 0.12, "#b06a2a")  # copper band
            c.poly([(cx - bw, base - bh * 0.72), (cx - bw * 0.55, base - bh * 0.92), (cx, base - bh),
                    (cx + bw * 0.55, base - bh * 0.92), (cx + bw, base - bh * 0.72)], "#3a4428", smooth=True)
    return []
