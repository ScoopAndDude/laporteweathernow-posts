"""Props for the City West short (the 1836 boomtown in the Indiana Dunes), added Nov. 16, 2026. They register in
story_kit3.PROPS like every prop, so a storyboard names them in "props": [{"p": "hotel1836", ...}].

    hotel1836    a big two-storey 1830s frame hotel with a long front porch, chimneys and a hitching rail; lit= how
                 many windows glow (0..1); empty=True: dark windows, a door hanging open, sand against the porch
    frame1836    a row of small 1830s frame houses (n, spread); lit= share of lit windows; empty=True as above
    stagecoach   an 1830s stagecoach with four horses and a driver, side on (flip faces it left)
    watermill    a small water-powered sawmill on a creek bank, its wheel turning in the stream, a log pile by it
    platmap      a town plat on a desk by candlelight: a grid of blocks between a creek and the lake shore, a quill
                 and an inkwell (no lettering)
    skyglow      the glow of a far-off fire on the horizon at (x, y), with smoke rising (no flames shown up close)
    marram       tufts of dune grass along y between x0 and x1 (w wide), for a beach today
    beach        a sand beach on the left of a lake picture, its shoreline running from (x, H) back to the horizon at
                 (x2, y), with low dunes behind it (dunes=True); sand= colour

Nothing shows a body, an injured person, or a real person's likeness: the stagecoach's passengers aren't shown.
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


def _framehouse(c, L, x, y, s, r, lit, empty, wall="#2a2622", w=70, h=88):
    """One gable-front 1830s frame house; returns its light spots."""
    out = []
    hw, hh = w * s, h * s
    c.rect(x - hw, y - hh, x + hw, y, wall)
    c.poly([(x - hw - 6 * s, y - hh), (x, y - hh - 56 * s), (x + hw + 6 * s, y - hh)], "#120f0d")
    for j in range(1, 8):
        c.line([(x - hw, y - j * hh / 8), (x + hw, y - j * hh / 8)], "#000000", max(0.6, 1 * s), 0.18)
    c.rect(x - 14 * s, y - 52 * s, x + 14 * s, y, "#0a0807")                                   # door
    if empty:
        c.poly([(x + 14 * s, y - 52 * s), (x + 30 * s, y - 48 * s), (x + 30 * s, y + 2 * s), (x + 14 * s, y)], "#1a1612")
    for wx in (-42, 42):
        cx, cy = x + wx * s, y - 52 * s
        on = (not empty) and r.random() < lit
        c.rect(cx - 12 * s, cy - 16 * s, cx + 12 * s, cy + 16 * s, "#ffcf80" if on else "#0c0e12", 0.95)
        if on:
            L.circle(cx, cy, 34 * s, "#ffc070", 0.35, blur=12 * s)
            out.append((cx, cy, (1.0, 0.8, 0.5), 30 * s, False))
        elif empty:
            c.line([(cx - 12 * s, cy + 16 * s), (cx + 12 * s, cy - 16 * s)], "#2e2822", max(0.8, 2 * s), 0.8)
    c.rect(x + 20 * s, y - hh - 40 * s, x + 32 * s, y - hh - 10 * s, "#120f0d")                 # chimney
    if empty:                                                                # sand drifted against it
        c.poly([(x - hw - 30 * s, y + 4 * s), (x - hw + 10 * s, y - 26 * s), (x - 20 * s, y - 10 * s), (x + 10 * s, y + 4 * s)],
               "#3a3428", 0.95)
    return out


@prop
def hotel1836(c, L, x, y, s=1.0, lit=0.8, empty=False, seed=3, **k):
    """A big two-storey 1830s frame hotel with a long front porch (see the top of this file)."""
    r = _rng(seed)
    out = []
    hw, hh = 230 * s, 200 * s
    wall = "#2e2a24" if not empty else "#24211d"
    c.rect(x - hw, y - hh, x + hw, y, wall)
    c.poly([(x - hw - 12 * s, y - hh), (x - hw + 60 * s, y - hh - 70 * s), (x + hw - 60 * s, y - hh - 70 * s),
            (x + hw + 12 * s, y - hh)], "#14110e")                            # a hipped roof
    for cx in (x - hw + 80 * s, x + hw - 80 * s):
        c.rect(cx - 10 * s, y - hh - 104 * s, cx + 10 * s, y - hh - 40 * s, "#14110e")           # chimneys
    for j in range(1, 14):
        c.line([(x - hw, y - j * hh / 14), (x + hw, y - j * hh / 14)], "#000000", max(0.6, 1 * s), 0.15)
    for row, wy in enumerate((-150, -64)):                                  # two rows of windows
        for j in range(7):
            cx = x - hw + 40 * s + j * (2 * hw - 80 * s) / 6
            cy = y + wy * s
            on = (not empty) and r.random() < lit
            c.rect(cx - 13 * s, cy - 20 * s, cx + 13 * s, cy + 20 * s, "#ffcf80" if on else "#0c0e12", 0.95)
            if on:
                L.circle(cx, cy, 36 * s, "#ffc070", 0.3, blur=12 * s)
                out.append((cx, cy, (1.0, 0.8, 0.5), 28 * s, False))
            elif empty and r.random() < 0.5:
                c.line([(cx - 13 * s, cy + 20 * s), (cx + 13 * s, cy - 20 * s)], "#2e2822", max(0.8, 2 * s), 0.8)
    c.rect(x - hw - 10 * s, y - 108 * s, x + hw + 10 * s, y - 98 * s, "#14110e")                 # porch roof
    for j in range(9):
        px = x - hw + j * (2 * hw) / 8
        c.line([(px, y - 98 * s), (px, y)], "#14110e", max(1.0, 5 * s))
    c.rect(x - 70 * s, y - hh - 10 * s, x + 70 * s, y - hh + 22 * s, "#3a3228")                   # a blank sign board
    c.rect(x - 22 * s, y - 60 * s, x + 22 * s, y, "#0a0807")                                       # front door
    if empty:
        c.poly([(x + 22 * s, y - 60 * s), (x + 40 * s, y - 54 * s), (x + 40 * s, y + 2 * s), (x + 22 * s, y)], "#1a1612")
        c.poly([(x - hw - 80 * s, y + 6 * s), (x - hw + 20 * s, y - 40 * s), (x - hw + 140 * s, y - 14 * s), (x - hw + 200 * s, y + 6 * s)],
               "#3a3428", 0.95)                                              # sand on the porch
    else:
        c.line([(x + hw + 40 * s, y - 40 * s), (x + hw + 200 * s, y - 40 * s)], "#14110e", max(1.0, 4 * s))  # hitching rail
        for px in (hw + 50, hw + 190):
            c.line([(x + px * s, y - 40 * s), (x + px * s, y)], "#14110e", max(1.0, 4 * s))
    return out


@prop
def frame1836(c, L, x, y, s=1.0, n=4, spread=600, lit=0.6, empty=False, seed=5, **k):
    """A row of small 1830s frame houses (see the top of this file)."""
    r = _rng(seed)
    out = []
    for j in range(int(n)):
        px = x - spread * s / 2 + (j + 0.5) * spread * s / n + r.uniform(-14, 14) * s
        ps = s * r.uniform(0.85, 1.05)
        out += _framehouse(c, L, px, y + r.uniform(-6, 6) * s, ps, r, lit, empty)
    return out


@prop
def stagecoach(c, L, x, y, s=1.0, flip=False, **k):
    """An 1830s stagecoach with four horses and a driver, side on (see the top of this file)."""
    f = -1 if flip else 1

    def P(pts):
        return [(x + f * px * s, y + py * s) for px, py in pts]
    for wx, rr in ((-70, 46), (60, 40)):                                     # wheels
        cx = x + f * wx * s
        c.circle(cx, y - rr * s, rr * s, INK)
        c.circle(cx, y - rr * s, (rr - 7) * s, "#1a1612")
        for a in range(0, 360, 30):
            ang = math.radians(a)
            c.line([(cx, y - rr * s), (cx + math.cos(ang) * (rr - 7) * s, y - rr * s + math.sin(ang) * (rr - 7) * s)],
                   INK, max(0.8, 2 * s))
    c.poly(P([(-110, -60), (-120, -150), (-96, -176), (80, -176), (104, -150), (96, -60), (40, -48), (-60, -48)]), "#24170f")
    for a0, a1 in ((-70, -10), (10, 66)):                                    # windows
        wx0, wx1 = sorted((x + f * a0 * s, x + f * a1 * s))
        c.rect(wx0, y - 156 * s, wx1, y - 112 * s, "#0c0e12")
    c.line(P([(-120, -176), (104, -176)]), "#0c0806", max(1.0, 5 * s))
    c.poly(P([(-100, -176), (-90, -196), (70, -196), (84, -176)]), "#1a120c", 0.9)                # luggage on top
    c.poly(P([(96, -120), (150, -132), (150, -116), (100, -100)]), "#1a120c")                     # driver's box
    c.circle(x + f * 132 * s, y - 176 * s, 11 * s, INK)                                             # the driver
    c.poly(P([(120, -168), (146, -168), (150, -128), (118, -128)]), INK)
    c.line(P([(146, -150), (200, -132), (290, -118)]), INK, max(0.8, 1.5 * s))                     # reins
    for j, hx in enumerate((210, 330)):                                      # two pairs of horses
        for dz in (0, 1):
            ox = hx + dz * 16
            col = INK if dz else "#0a0807"
            bx0, by0 = x + f * (ox + 10) * s, y - 92 * s
            c.ellipse(bx0, by0, 52 * s, 22 * s, col)                          # body
            c.poly(P([(ox + 40, -104), (ox + 58, -142), (ox + 70, -150), (ox + 94, -136), (ox + 90, -128), (ox + 72, -130),
                      (ox + 62, -104), (ox + 54, -84)]), col)                  # neck and head
            c.poly(P([(ox + 60, -146), (ox + 64, -158), (ox + 68, -146)]), col)   # ear
            c.line(P([(ox - 40, -96), (ox - 52, -60)]), col, max(1.0, 4 * s))  # tail
            for lx, fwd in ((-30, -4), (-20, 6), (36, -6), (46, 6)):           # legs
                c.line(P([(ox + lx, -80), (ox + lx + fwd * 0.5, -40), (ox + lx + fwd, 0)]), col, max(1.0, 5 * s))
    c.line(P([(104, -84), (380, -96)]), INK, max(0.8, 2 * s))                                       # the pole
    return []


@prop
def watermill(c, L, x, y, s=1.0, seed=7, **k):
    """A small water-powered sawmill on a creek bank, its wheel in the stream (see the top of this file)."""
    r = _rng(seed)
    c.poly([(x - 260 * s, y + 30 * s), (x + 260 * s, y + 30 * s), (x + 300 * s, y + 70 * s), (x - 300 * s, y + 70 * s)],
           "#0e1a24")                                                        # the creek
    for j in range(10):
        px = x + r.uniform(-240, 240) * s
        c.line([(px, y + 44 * s), (px + 30 * s, y + 44 * s)], "#5a7088", max(0.8, 2 * s), 0.4)
    c.rect(x - 120 * s, y - 120 * s, x + 80 * s, y + 30 * s, "#221c16")
    c.poly([(x - 130 * s, y - 120 * s), (x - 20 * s, y - 190 * s), (x + 90 * s, y - 120 * s)], "#110e0b")
    for j in range(1, 9):
        c.line([(x - 120 * s + j * 25 * s, y - 120 * s), (x - 120 * s + j * 25 * s, y + 30 * s)], "#000000", max(0.6, 1 * s), 0.2)
    wx, wy, wr = x + 130 * s, y - 10 * s, 70 * s                             # the wheel
    for a in range(0, 360, 20):
        ang = math.radians(a)
        c.line([(wx + math.cos(ang) * wr * 0.2, wy + math.sin(ang) * wr * 0.2), (wx + math.cos(ang) * wr, wy + math.sin(ang) * wr)],
               "#0a0807", max(1.0, 4 * s))
    art_ring = [(wx + math.cos(math.radians(a)) * wr, wy + math.sin(math.radians(a)) * wr) for a in range(0, 370, 10)]
    c.line(art_ring, "#0a0807", max(1.0, 6 * s))
    c.circle(wx, wy, 10 * s, "#0a0807")
    for j in range(5):                                                       # a pile of logs
        c.ellipse(x - 190 * s + j * 14 * s, y + 10 * s - (j % 2) * 16 * s, 50 * s, 12 * s, "#1a120c")
        c.circle(x - 150 * s + j * 14 * s, y + 10 * s - (j % 2) * 16 * s, 11 * s, "#3a2a1a")
    return []


@prop
def platmap(c, L, x, y, s=1.0, **k):
    """A town plat on a desk by candlelight (see the top of this file)."""
    out = []
    dt = y - 240 * s                                                         # the desk top
    c.rect(x - 420 * s, dt, x + 420 * s, dt + 26 * s, "#2a1a0e")
    c.rect(x - 400 * s, dt + 26 * s, x - 340 * s, y, "#1e1208")
    c.rect(x + 340 * s, dt + 26 * s, x + 400 * s, y, "#1e1208")
    px0, px1, py0, py1 = x - 300 * s, x + 260 * s, dt - 18 * s, dt - 4 * s
    c.poly([(px0, py1), (px0 + 30 * s, py0 - 150 * s), (px1 + 20 * s, py0 - 150 * s), (px1, py1)], "#bfb291")  # the paper
    def M(u, v):                                                             # map coords on the tilted sheet
        top = py0 - 150 * s
        yy = top + (py1 - top) * v
        xl = px0 + 30 * s * (1 - v)
        xr = px1 + 20 * s * (1 - v)
        return (xl + (xr - xl) * u, yy)
    c.line([M(0.02, 0.08), M(0.3, 0.12), M(0.6, 0.07), M(0.98, 0.1)], "#2a3a52", max(1.0, 3 * s))  # the lake shore
    creek = [M(0.56 + 0.025 * math.sin(t * 5.0), 0.1 + 0.88 * t) for t in [i / 30 for i in range(31)]]
    c.line(creek, "#2a3a52", max(1.0, 2.4 * s))                               # the creek
    for i in range(6):                                                       # the street grid
        u = 0.08 + i * 0.16
        c.line([M(u, 0.2), M(u, 0.92)], "#3a2a1a", max(0.6, 1.4 * s), 0.85)
    for j in range(5):
        v = 0.2 + j * 0.18
        c.line([M(0.08, v), M(0.88, v)], "#3a2a1a", max(0.6, 1.4 * s), 0.85)
    cx, cy = x + 330 * s, dt                                                 # a candle
    c.rect(cx - 10 * s, cy - 70 * s, cx + 10 * s, cy, "#d8ccb0")
    c.ellipse(cx, cy - 82 * s, 6 * s, 12 * s, "#ffd890")
    L.circle(cx, cy - 80 * s, 160 * s, "#ffbf60", 0.3, blur=60 * s)
    out.append((cx, cy - 82 * s, (1.0, 0.8, 0.45), 90 * s, True))
    ix = x - 360 * s                                                         # inkwell and quill
    c.rect(ix - 16 * s, dt - 26 * s, ix + 16 * s, dt, "#0a0a0c")
    c.line([(ix, dt - 26 * s), (ix + 40 * s, dt - 120 * s)], "#d8d0c0", max(1.0, 3 * s))
    c.poly([(ix + 30 * s, dt - 96 * s), (ix + 52 * s, dt - 130 * s), (ix + 44 * s, dt - 94 * s)], "#d8d0c0", 0.9)
    return out


@prop
def skyglow(c, L, x, y, s=1.0, seed=9, **k):
    """The glow of a far-off fire on the horizon at (x, y), with smoke rising (see the top of this file)."""
    r = _rng(seed)
    L.ellipse(x, y - 30 * s, 320 * s, 130 * s, "#ff5a1a", 0.22, blur=80 * s)
    L.ellipse(x, y - 10 * s, 160 * s, 50 * s, "#ff8a3a", 0.35, blur=30 * s)
    c.ellipse(x, y - 30 * s, 300 * s, 110 * s, "#7a2a10", 0.22, blur=70 * s)
    for j in range(14):                                                      # smoke
        t = j / 13
        c.ellipse(x + (20 + 160 * t) * s + r.uniform(-20, 20) * s, y - (60 + 420 * t) * s, (50 + 110 * t) * s, (30 + 60 * t) * s,
                  "#2a1a12", 0.45 * (1 - 0.6 * t), blur=26 * s)
    return [(x, y - 14 * s, (1.0, 0.45, 0.15), 70 * s, True)]


@prop
def marram(c, L, x, y, s=1.0, w=900, seed=11, color="#0a0d08", **k):
    """Tufts of dune grass along y (see the top of this file)."""
    r = _rng(seed)
    for j in range(int(w * s / 22)):
        px = x - w * s / 2 + j * 22 + r.uniform(-8, 8)
        py = y + r.uniform(-10, 10) * s
        for q in range(7):
            hh = r.uniform(30, 70) * s
            lean = r.uniform(-0.5, 0.5) * hh
            c.line([(px, py), (px + lean * 0.5, py - hh * 0.6), (px + lean, py - hh)], color, max(0.8, 1.8 * s))
    return []


@prop
def beach(c, L, x, y, s=1.0, x2=760, dunes=True, sand="#3a342a", seed=13, **k):
    """A sand beach on the left of a lake picture (see the top of this file)."""
    r = _rng(seed)
    pts = [(-20, y), (x2, y)]
    for i in range(1, 21):
        t = i / 20
        pts.append((x2 + (x - x2) * t + 24 * math.sin(t * 7 + seed) * t, y + (H - y) * t))
    pts += [(-20, H + 10)]
    c.poly(pts, sand)
    edge = pts[1:-1]
    c.line(edge, "#5a5a54", max(1.0, 3 * s), 0.5, blur=2)                     # the wet edge
    c.line([(px + 10 * (py - y) / (H - y) + 6, py) for px, py in edge], "#aab4bc", max(1.0, 2 * s), 0.18, blur=3)  # a little surf
    if dunes:                                                                # low dunes along the back of the beach
        ridge = [(-20, y + 4)]
        for i in range(0, 13):
            u = i / 12
            ridge.append((-20 + (x2 + 20) * u, y - (30 + 40 * abs(math.sin(u * 5.3 + seed))) * s * (1 - 0.5 * u)))
        ridge.append((x2, y + 4))
        c.poly(ridge, "#221f1a")
    return []
