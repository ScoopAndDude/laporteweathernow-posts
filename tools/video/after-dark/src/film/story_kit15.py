"""Props for the Moody's Light short (a ghost-light legend near Rensselaer, Indiana), added Nov. 15, 2026. They
register in story_kit3.PROPS like every prop, so a storyboard names them in "props": [{"p": "gravelroad", ...}].

    gravelroad   a straight gravel road from the bottom of the picture (centred at bx, w wide) to a point at x on the
                 horizon y, with wheel ruts, loose gravel and weedy edges
    cornwall     a row of corn stalks w wide along y, h tall (dry=True: late-season brown), for a field edge; stack
                 several, smaller toward the horizon, for depth
    ghostlight   a floating light with a soft halo at (x, y): r its size, red=True the "blood red" colour some
                 accounts give; it flickers
    ghostfarmer  a faint, see-through old farmer in a hat holding a lantern out (a = how faint); flip faces him left
    firehouse    a two-storey farmhouse at night with fire in its windows and smoke rising (no people); fire=0 the
                 same house dark (lamp=True: one dim window), for a before-and-after pair of beats
    oldhouse     an empty, falling-down farmhouse: sagging roof, boarded windows, a broken porch, weeds
    stump        a hollow tree stump
    carback      a 1990s car seen from behind, its headlights throwing beams up the road toward x2 on the horizon
                 at y2 (flash=0..1 makes the beams brighter), tail lamps lit
    hunters      ghost hunters on the road at night: n figures with flashlights and one camera on a tripod
    farlights    a pair of car headlights far off at (x, y), small and bright

Nothing shows a body, a hanging, an injured person, or a real person's likeness.
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
def gravelroad(c, L, x, y, s=1.0, bx=540, w=900, color="#24211c", seed=3, **k):
    """A straight gravel road from the bottom of the picture to a point at x on the horizon y."""
    r = _rng(seed)
    hw = w / 2
    c.poly([(x - 2, y), (x + 2, y), (bx + hw, H + 10), (bx - hw, H + 10)], color)
    for side in (-1, 1):                                                     # wheel ruts
        c.line([(x + side * 1, y), (bx + side * hw * 0.42, H + 10)], "#141210", max(1.0, 14 * s), 0.45, blur=4 * s)
    for j in range(900):                                                     # loose gravel, denser up close
        t = r.uniform(0, 1) ** 0.6
        px = x + (bx - x) * t + r.uniform(-1, 1) * (2 + hw * t)
        py = y + (H - y) * t
        c.circle(px, py, max(0.6, 2.2 * t * s), "#5a5246", 0.35)
    for side in (-1, 1):                                                     # weedy edges
        for j in range(160):
            t = r.uniform(0, 1) ** 0.7
            ex = x + (bx - x) * t + side * (2 + hw * t)
            ey = y + (H - y) * t
            hh = (4 + 40 * t) * s * r.uniform(0.6, 1.3)
            c.line([(ex, ey), (ex + r.uniform(-0.4, 0.4) * hh, ey - hh)], "#0a0c08", max(0.8, 2.4 * t * s + 0.5), 0.9)
    return []


@prop
def cornwall(c, L, x, y, s=1.0, w=600, h=170, dry=True, color=None, seed=5, gap=0.0, **k):
    """A row of corn stalks w wide along y, h tall (see the top of this file)."""
    r = _rng(seed)
    col = color or ("#050504" if dry else "#040604")
    step = max(5.0, 11 * s)
    n = int(w * s / step) + 1
    x0 = x - w * s / 2
    for j in range(n):
        if gap and r.random() < gap:
            continue
        px = x0 + j * step + r.uniform(-3, 3) * s
        hh = h * s * r.uniform(0.82, 1.12)
        lean = r.uniform(-0.08, 0.08) * hh
        top = (px + lean, y - hh)
        c.line([(px, y), (px + lean * 0.5, y - hh * 0.55), top], col, max(1.0, 3.2 * s))
        for q in range(int(r.integers(3, 6))):                               # leaves
            t = r.uniform(0.25, 0.85)
            bx, by = px + lean * t, y - hh * t
            d = r.choice([-1, 1])
            ln = hh * r.uniform(0.22, 0.38)
            droop = ln * r.uniform(0.2, 0.6)
            c.line([(bx, by), (bx + d * ln * 0.5, by - ln * 0.25), (bx + d * ln, by + droop)], col,
                   max(0.8, 2.2 * s))
        c.line([top, (top[0] + r.uniform(-6, 6) * s, top[1] - 14 * s)], col, max(0.8, 1.6 * s))  # the tassel
        if r.random() < 0.4:                                                 # an ear
            t = r.uniform(0.35, 0.55)
            c.ellipse(px + lean * t + 5 * s, y - hh * t, 4 * s, 11 * s, col)
    return []


@prop
def ghostlight(c, L, x, y, s=1.0, r=12, red=False, halo=1.0, **k):
    """A floating light with a soft halo (see the top of this file)."""
    core = "#ff6a50" if red else "#fff0b8"
    glow = "#ff3a20" if red else "#ffd77a"
    L.circle(x, y, r * 9 * s, glow, 0.16 * halo, blur=r * 5 * s)
    L.circle(x, y, r * 3.2 * s, glow, 0.35 * halo, blur=r * 1.6 * s)
    c.circle(x, y, r * 1.4 * s, glow, 0.5, blur=r * 0.8 * s)
    c.circle(x, y, r * 0.7 * s, core, 0.95, blur=1.5 * s)
    col = (1.0, 0.45, 0.32) if red else (1.0, 0.88, 0.55)
    return [(x, y, col, r * 4 * s, True)]


@prop
def ghostfarmer(c, L, x, y, s=1.0, a=0.42, flip=False, color="#a8bccc", **k):
    """A faint, see-through old farmer holding a lantern out (see the top of this file)."""
    f = -1 if flip else 1

    def P(pts):
        return [(x + f * px * s, y + py * s) for px, py in pts]
    body = [(-22, 0), (-18, -84), (-26, -150), (-14, -176), (16, -176), (24, -150), (30, -96), (20, 0), (8, 0),
            (2, -62), (-6, 0)]
    for blur, al in ((10 * s, a * 0.35), (2.5 * s, a)):
        c.poly(P(body), color, al, blur=blur)
        c.circle(x + f * 4 * s, y - 192 * s, 15 * s, color, al, blur=blur)
        c.poly(P([(-30, -202), (-12, -212), (20, -212), (36, -202), (20, -198), (-14, -198)]), color, al, blur=blur)
        c.line(P([(18, -160), (52, -132), (70, -126)]), color, max(1.0, 10 * s), al, blur=blur)   # the arm, out
    lx, ly = x + f * 74 * s, y - 104 * s                                        # the lantern
    c.line([(lx, ly - 30 * s), (x + f * 70 * s, y - 126 * s)], "#c8d4dc", max(1.0, 2 * s), a)
    c.rect(lx - 9 * s, ly - 26 * s, lx + 9 * s, ly, "#ffe6a0", 0.85, r=3 * s)
    L.circle(lx, ly - 12 * s, 110 * s, "#ffcf70", 0.22, blur=50 * s)
    L.circle(lx, ly - 12 * s, 26 * s, "#ffe2a0", 0.5, blur=8 * s)
    return [(lx, ly - 12 * s, (1.0, 0.85, 0.5), 60 * s, True)]


@prop
def firehouse(c, L, x, y, s=1.0, fire=1.0, lamp=False, seed=7, **k):
    """A two-storey farmhouse at night with fire in its windows and smoke rising (see the top of this file).
    fire=0 draws the same house dark, with no smoke (lamp=True: one dim lit window)."""
    r = _rng(seed)
    out = []
    for j in range(16 if fire > 0 else 0):                                   # smoke drifting up and away
        t = j / 15
        px = x + (20 + 260 * t) * s + r.uniform(-20, 20) * s
        py = y - (330 + 520 * t) * s
        c.ellipse(px, py, (60 + 120 * t) * s, (40 + 70 * t) * s, "#1a1714", 0.5 * (1 - t * 0.6), blur=26 * s)
    hw, hh = 150 * s, 230 * s
    c.rect(x - hw, y - hh, x + hw, y, "#0d0b0a")
    c.poly([(x - hw - 14 * s, y - hh), (x, y - hh - 120 * s), (x + hw + 14 * s, y - hh)], "#070605")
    c.rect(x + 70 * s, y - hh - 110 * s, x + 96 * s, y - hh - 40 * s, "#070605")             # chimney
    c.rect(x - hw - 8 * s, y - 92 * s, x + hw + 8 * s, y - 80 * s, "#070605")                # porch roof
    for px in (-130, -50, 50, 130):
        c.line([(x + px * s, y - 80 * s), (x + px * s, y)], "#070605", max(1.0, 5 * s))
    wins = [(-80, -170), (0, -170), (80, -170), (-80, -48), (80, -48)]
    if fire <= 0:                                                            # the same house, dark
        for j, (wx, wy) in enumerate(wins):
            cx, cy = x + wx * s, y + wy * s
            lit = lamp and j == 4
            c.rect(cx - 20 * s, cy - 28 * s, cx + 20 * s, cy + 28 * s, "#e8b060" if lit else "#151821", 0.8 if lit else 0.9)
            if lit:
                L.circle(cx, cy, 50 * s, "#ffc070", 0.25, blur=20 * s)
                out.append((cx, cy, (1.0, 0.75, 0.4), 30 * s, False))
        return out
    for j, (wx, wy) in enumerate(wins):
        cx, cy = x + wx * s, y + wy * s
        hot = fire * (0.6 + 0.4 * r.random())
        c.rect(cx - 20 * s, cy - 28 * s, cx + 20 * s, cy + 28 * s, "#ff8a2a", 0.95 * hot)
        c.rect(cx - 20 * s, cy - 28 * s, cx + 20 * s, cy + 28 * s, "#ffd070", 0.5 * hot, blur=4 * s)
        L.circle(cx, cy, 70 * s, "#ff7a20", 0.35 * hot, blur=30 * s)
        out.append((cx, cy, (1.0, 0.55, 0.2), 50 * s, True))
    for j in range(3):                                                       # flames out of the top windows
        cx = x + (-80 + j * 80) * s
        cy = y - 198 * s
        c.poly([(cx - 16 * s, cy), (cx - 6 * s, cy - (30 + r.uniform(0, 26)) * s), (cx + 2 * s, cy - 12 * s),
                (cx + 8 * s, cy - (24 + r.uniform(0, 30)) * s), (cx + 16 * s, cy)], "#ffb040", 0.85 * fire, blur=2 * s)
    c.line([(x - hw - 14 * s, y - hh), (x, y - hh - 120 * s), (x + hw + 14 * s, y - hh)], "#ff8a3a", max(1.0, 3 * s),
           0.35 * fire, blur=3 * s)                                          # firelight on the roof edge
    L.ellipse(x, y + 20 * s, 340 * s, 60 * s, "#ff6a1a", 0.18 * fire, blur=40 * s)            # and on the ground
    return out


@prop
def oldhouse(c, L, x, y, s=1.0, seed=9, wall="#3a3530", **k):
    """An empty, falling-down farmhouse (see the top of this file)."""
    r = _rng(seed)
    art.tree(c, x + 240 * s, y, 360 * s, seed=seed + 2, color="#060706", depth=6, spread=0.6)
    hw, hh = 140 * s, 220 * s
    c.poly([(x - hw, y), (x - hw, y - hh), (x + hw, y - hh + 14 * s), (x + hw, y)], wall)    # walls, out of true
    c.poly([(x - hw - 16 * s, y - hh + 2 * s), (x - 10 * s, y - hh - 104 * s), (x + 30 * s, y - hh - 70 * s),
            (x + hw + 16 * s, y - hh + 16 * s)], "#1a1714")                   # a sagging roof
    for j in range(5):                                                       # holes where shingles are gone
        px = x + r.uniform(-90, 90) * s
        py = y - hh - r.uniform(10, 60) * s
        c.rect(px - 9 * s, py - 6 * s, px + 9 * s, py + 6 * s, "#3a4250", 0.55)
    for j in range(1, 10):
        yy = y - j * hh / 10
        c.line([(x - hw, yy), (x + hw, yy + j * 1.4 * s)], "#000000", max(0.6, 1 * s), 0.2)
    for wx, wy in ((-70, -160), (70, -156), (-70, -50), (70, -48)):          # boarded windows
        cx, cy = x + wx * s, y + wy * s
        c.rect(cx - 22 * s, cy - 30 * s, cx + 22 * s, cy + 30 * s, "#0a0908")
        c.line([(cx - 24 * s, cy - 26 * s), (cx + 24 * s, cy + 24 * s)], "#6a5a46", max(1.0, 6 * s), 0.8)
        c.line([(cx - 24 * s, cy + 24 * s), (cx + 24 * s, cy - 26 * s)], "#6a5a46", max(1.0, 6 * s), 0.8)
    c.rect(x - 18 * s, y - 92 * s, x + 18 * s, y, "#060505")                                  # the doorway, no door
    c.poly([(x - hw - 10 * s, y - 92 * s), (x + 20 * s, y - 92 * s), (x + hw + 10 * s, y - 60 * s),
            (x + hw + 10 * s, y - 50 * s), (x + 20 * s, y - 82 * s), (x - hw - 10 * s, y - 82 * s)], "#141210")  # porch roof
    c.line([(x - 120 * s, y - 84 * s), (x - 120 * s, y)], "#141210", max(1.0, 5 * s))
    c.line([(x + 110 * s, y - 56 * s), (x + 96 * s, y - 4 * s)], "#141210", max(1.0, 5 * s))
    for j in range(140):                                                     # weeds
        px = x + r.uniform(-1, 1) * 300 * s
        hh2 = r.uniform(20, 70) * s
        c.line([(px, y + r.uniform(0, 30) * s), (px + r.uniform(-12, 12) * s, y - hh2)], "#080a07", max(0.8, 2 * s), 0.9)
    for j in range(5):                                                       # a broken fence
        px = x - 300 * s + j * 46 * s
        c.line([(px, y + 20 * s), (px + r.uniform(-8, 8) * s, y - 50 * s)], "#141210", max(1.0, 5 * s))
    c.line([(x - 300 * s, y - 20 * s), (x - 130 * s, y - 34 * s)], "#141210", max(1.0, 4 * s))
    return []


@prop
def stump(c, L, x, y, s=1.0, **k):
    """A hollow tree stump."""
    c.poly([(x - 46 * s, y), (x - 40 * s, y - 70 * s), (x - 30 * s, y - 96 * s), (x - 14 * s, y - 80 * s),
            (x - 2 * s, y - 104 * s), (x + 12 * s, y - 84 * s), (x + 26 * s, y - 98 * s), (x + 38 * s, y - 72 * s),
            (x + 48 * s, y)], "#0b0907")
    c.ellipse(x, y - 78 * s, 26 * s, 10 * s, "#020202")                      # the hollow
    for d in (-1, 1):                                                        # roots
        c.poly([(x + d * 40 * s, y - 20 * s), (x + d * 80 * s, y + 6 * s), (x + d * 40 * s, y + 4 * s)], "#0b0907")
    c.line([(x - 30 * s, y - 90 * s), (x - 34 * s, y - 10 * s)], "#3a3228", max(0.8, 2 * s), 0.5)
    return []


@prop
def carback(c, L, x, y, s=1.0, x2=540, y2=1050, flash=0.6, **k):
    """A 1990s car seen from behind, its headlights throwing beams up the road (see the top of this file)."""
    out = []
    bw = 150 * s
    c.poly([(x - bw * 1.6, y - 20 * s), (x + bw * 1.6, y - 20 * s), (x + bw * 3.2, H + 10), (x - bw * 3.2, H + 10)],
           "#000000", 0.6, blur=40 * s)                                      # the unlit road behind the car
    for side in (-1, 1):                                                     # the beams, ahead of the car
        hx = x + side * bw * 0.8
        tip = (x2 + side * 40, y2 + 6)
        L.poly([(hx - 18 * s, y - 70 * s), (hx + 18 * s, y - 70 * s), (tip[0] + 60, tip[1]), (tip[0] - 60, tip[1])],
               "#fff0c8", 0.18 + 0.25 * flash, blur=26 * s)
        c.poly([(hx - 18 * s, y - 60 * s), (hx + 18 * s, y - 60 * s), (tip[0] + 40, tip[1] + 30),
                (tip[0] - 40, tip[1] + 30)], "#e8d8b0", 0.08 + 0.1 * flash, blur=26 * s)
    py = y - (y - y2) * 0.45                                                 # where the beams pool on the road
    L.ellipse((x + x2) / 2, py, 190 * s, 26 * s, "#fff0c8", 0.25 + 0.3 * flash, blur=18 * s)
    c.ellipse((x + x2) / 2, py, 180 * s, 22 * s, "#e0d0a8", 0.15 + 0.15 * flash, blur=16 * s)
    c.poly([(x - bw, y - 30 * s), (x - bw + 6 * s, y - 92 * s), (x - bw * 0.72, y - 104 * s), (x - bw * 0.58, y - 156 * s),
            (x + bw * 0.58, y - 156 * s), (x + bw * 0.72, y - 104 * s), (x + bw - 6 * s, y - 92 * s), (x + bw, y - 30 * s)],
           "#0e0f12")                                                        # the body from behind
    c.poly([(x - bw * 0.54, y - 110 * s), (x - bw * 0.46, y - 148 * s), (x + bw * 0.46, y - 148 * s),
            (x + bw * 0.54, y - 110 * s)], "#1c2228")                         # rear window
    c.poly([(x - bw * 0.54, y - 110 * s), (x - bw * 0.46, y - 148 * s), (x + bw * 0.46, y - 148 * s),
            (x + bw * 0.54, y - 110 * s)], "#fff0c8", 0.08 + 0.1 * flash)     # the beams seen through it
    for side in (-1, 1):                                                     # tail lamps
        tx = x + side * bw * 0.78
        c.rect(tx - 22 * s, y - 92 * s, tx + 22 * s, y - 74 * s, "#c0281c", 0.95)
        L.circle(tx, y - 83 * s, 40 * s, "#ff2a14", 0.3, blur=14 * s)
        out.append((tx, y - 83 * s, (1.0, 0.2, 0.12), 26 * s, False))
        c.rect(x + side * bw * 0.95 - 22 * s, y - 34 * s, x + side * bw * 0.95 + 22 * s, y + 4 * s, "#030303")  # tyres
    c.rect(x - bw, y - 40 * s, x + bw, y - 28 * s, "#1a1b1e")                                 # bumper
    c.rect(x - 30 * s, y - 66 * s, x + 30 * s, y - 52 * s, "#2a2c30")                         # plate
    return out


@prop
def hunters(c, L, x, y, s=1.0, n=3, spread=260, seed=13, **k):
    """Ghost hunters on the road at night with flashlights and a camera on a tripod."""
    r = _rng(seed)
    out = []
    for j in range(int(n)):
        px = x - spread * s / 2 + j * spread * s / max(1, n - 1)
        ps = s * r.uniform(0.9, 1.05)
        hh = 160 * ps
        c.poly([(px - 12 * ps, y), (px - 16 * ps, y - hh * 0.6), (px - 10 * ps, y - hh * 0.82), (px + 10 * ps, y - hh * 0.82),
                (px + 16 * ps, y - hh * 0.6), (px + 12 * ps, y)], INK)
        c.circle(px, y - hh * 0.9, 12 * ps, INK)
        if j != 1:                                                           # a flashlight beam up the road
            fx, fy = px + 14 * ps, y - hh * 0.62
            d = -1 if px > x else 1
            L.poly([(fx, fy - 3 * ps), (fx, fy + 3 * ps), (fx + d * 160 * ps, fy - 40 * ps), (fx + d * 160 * ps, fy - 90 * ps)],
                   "#e8f0ff", 0.18, blur=16 * ps)
            out.append((fx, fy, (0.9, 0.95, 1.0), 14 * ps, False))
        else:                                                                # a camera on a tripod
            tx = px + 46 * ps
            for d in (-1, 0, 1):
                c.line([(tx, y - 100 * ps), (tx + d * 22 * ps, y)], INK, max(1.0, 3 * ps))
            c.rect(tx - 14 * ps, y - 116 * ps, tx + 14 * ps, y - 98 * ps, INK)
            c.circle(tx, y - 108 * ps, 3 * ps, "#ff3020", 0.9)
    return out


@prop
def farlights(c, L, x, y, s=1.0, gap=26, **k):
    """A pair of car headlights far off."""
    out = []
    for d in (-1, 1):
        px = x + d * gap * s / 2
        L.circle(px, y, 16 * s, "#fff2c8", 0.3, blur=8 * s)
        c.circle(px, y, 3.2 * s, "#fff8e0", 1.0)
        out.append((px, y, (1.0, 0.95, 0.8), 12 * s, False))
    L.circle(x, y, 60 * s, "#fff0c0", 0.06, blur=30 * s)
    return out
