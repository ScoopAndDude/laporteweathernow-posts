"""Props for the Wanatah petrified-woman short (the 1891 newspaper hoax), added Nov. 15, 2026. They register in
story_kit3.PROPS like every prop, so a storyboard names them in "props": [{"p": "bogpit", ...}].

    bogpit       an abandoned bog-iron pit in a marsh: a ragged hole with ochre gravel walls and still, rust-dark
                 water. glint=0..1 a pale sky reflection, rust=0..1 the orange sheen, plank=True an old board
                 across one side, seed
    railfence    a zigzag split-rail fence (w= half its width in px, h= its height)
    homestead    a small 1850s frame farmhouse: a steep gable roof, a lean-to kitchen and a fieldstone chimney
                 (lit=0..1 lights the windows, flip=True puts the lean-to on the right)
    lane         a dirt lane winding from (x, y), where it is wide, away to (x2, y2), where it is a thread
    walker       one small woman in a long dress and a shawl, walking away from us
    pitmen       a few small men in hats and coats standing at the far edge of a pit (n, seed; poles=True gives
                 the two at the ends long poles)
    handpress    a generic 19th-century iron hand press with a sheet on its bed (no maker's name or ornament)
    typecase     a printer's type cabinet with its slanted case, and printed sheets (unreadable) drying on a line
    rolltop      an editor's roll-top desk: pigeonholes, an oil lamp, a paper spike, a paste pot and scissors
    darkwater    close on the pit's still water from its edge: the far wall's layers, rust and sky in the water,
                 reeds on the near bank (h= the water's height)
    hanglamp     an oil lamp hanging on a chain, lit
    coach        an 1890s wooden passenger coach on its track: clerestory roof, lit windows, an end platform with
                 steps (flip=True puts the platform on the left; lit=0..1)
    stationlamp  a lamp on a post, lit

People are small anonymous silhouettes. Nothing shows a body, a real person's likeness or a brand. The 1891 story
was a hoax: the pictures show the pit, the men, the press and the train, and never the woman it described.
"""
import math

import numpy as np

import story_kit3 as K3
from story_kit import WARM
from core import smooth_path, paint

prop = K3.prop
IRON = "#121212"
IRON_L = "#2c2c2c"
WOOD = "#24160e"
WOOD_D = "#170d08"
BRASS = "#8a7038"
PAPER = "#cfc6ae"
INK = "#030304"


def _ring(x, cy, a, b, f, n, rng, jit):
    """Points on a ragged ellipse (centre x, cy; semi-axes a, b), each radius times f and a seeded wobble."""
    w = rng.uniform(-jit, jit, n)
    w = (w + np.roll(w, 1) + np.roll(w, -1)) / 3.0
    return [(x + a * (f + w[i]) * math.cos(2 * math.pi * i / n), cy + b * (f + w[i]) * math.sin(2 * math.pi * i / n))
            for i in range(n)]


@prop
def bogpit(c, L, x, y, s=1.0, glint=0.6, rust=0.7, plank=True, seed=4, **k):
    """An abandoned bog-iron pit (see the top of this file). (x, y) is the middle of its near lip."""
    r = np.random.default_rng(seed)
    a, b = 320 * s, 95 * s
    cy = y - b
    amp = [(2, 0.07), (3, 0.05), (5, 0.03), (7, 0.015)]
    ph = r.uniform(0, 2 * math.pi, len(amp))

    def rad(t):
        return 1.0 + sum(av * math.sin(kk * t + ph[i]) for i, (kk, av) in enumerate(amp))

    def P(t, f=1.0):
        q = rad(t) * f
        return (x + a * q * math.cos(t), cy + b * q * math.sin(t))

    def Q(t):                                                                        # the waterline on the far wall
        q = rad(t)
        return (x + a * q * math.cos(t) * (0.95 + 0.05 * math.cos(t) ** 2), cy + b * q * math.sin(t) * 0.52)

    ring = lambda f, n=48: [P(2 * math.pi * i / n, f) for i in range(n)]
    c.poly(ring(1.28), "#0b0907", 0.9, smooth=True, blur=12 * s)                    # trampled mud, soft-edged
    c.poly(ring(1.1), "#100b08", smooth=True, blur=6 * s)
    c.poly(ring(1.0), "#1a110a", smooth=True)                                       # the far wall
    for u, col, wd, al in ((0.0, "#0c0906", 0.16, 1.0), (0.22, "#2a160a", 0.07, 0.7), (0.38, "#1c1a18", 0.08, 0.6),
                           (0.52, "#3a1e0c", 0.05, 0.6), (0.68, "#22140a", 0.08, 0.6), (0.88, "#0c0806", 0.10, 0.9)):
        pts = []
        for i in range(41):
            t = math.pi + math.pi * i / 40
            (px, py), (qx, qy) = P(t), Q(t)
            pts.append((px + (qx - px) * u, py + (qy - py) * u + r.uniform(-1.2, 1.2) * s))
        c.line(pts, col, wd * b, al)
    for j in range(18):                                                              # roots hanging from the lip
        t = r.uniform(math.pi * 1.12, math.pi * 1.88)
        px, py = P(t)
        ln = r.uniform(10, 30) * s
        c.line([(px, py), (px + r.uniform(-5, 5) * s, py + ln * 0.5), (px + r.uniform(-6, 6) * s, py + ln)],
               "#080604", r.uniform(1.2, 2.4) * s, 0.9)
    for j in range(22):                                                              # a few dark stones
        t = r.uniform(math.pi * 1.06, math.pi * 1.94)
        (px, py), (qx, qy) = P(t), Q(t)
        u = r.uniform(0.25, 0.8)
        c.ellipse(px + (qx - px) * u, py + (qy - py) * u, r.uniform(2, 5) * s, r.uniform(1.5, 3) * s,
                  ("#2a2016", "#140e08", "#3a2412")[j % 3], 0.6)
    water = [P(math.pi * i / 30) for i in range(31)] + [Q(math.pi + math.pi * i / 30) for i in range(1, 30)]
    c.poly(water, "#060505", smooth=True)                                            # still, dark water
    c.poly([Q(math.pi + math.pi * i / 30) for i in range(31)] +
           [(x + a * 0.8 * math.cos(math.pi - math.pi * i / 30), cy + b * 0.05) for i in range(31)],
           "#1c2028", 0.45, smooth=True, blur=10 * s)                               # the far side holds the sky
    c.poly(water, "#4a240c", 0.20 * rust, smooth=True, blur=8 * s)                  # a rust tint
    for j in range(4):                                                               # rust scum near the edges
        t = r.uniform(0.3, math.pi - 0.3)
        px, py = P(t, 0.86)
        c.ellipse(px, py - 6 * s, r.uniform(50, 100) * s, r.uniform(4, 7) * s, "#6a3410", 0.15 * rust, blur=8 * s)
    if glint > 0:                                                                    # the sky in the water
        c.ellipse(x + 40 * s, cy - 0.32 * b, 130 * s, 3 * s, "#aab6c0", 0.14 * glint, blur=4 * s)
        c.ellipse(x - 90 * s, cy - 0.12 * b, 70 * s, 2.5 * s, "#aab6c0", 0.08 * glint, blur=3 * s)
        L.ellipse(x + 40 * s, cy - 0.32 * b, 130 * s, 5 * s, "#6a7c8c", 0.10 * glint, blur=8 * s)
    if plank:                                                                        # an old board across one side
        p0 = P(math.pi * 1.08, 1.12)
        p1 = (x - a * 0.4, cy + b * 0.45)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        n = math.hypot(dx, dy)
        ox, oy = -dy / n * 9 * s, dx / n * 9 * s
        c.poly([(p0[0] + ox, p0[1] + oy), (p1[0] + ox, p1[1] + oy), (p1[0] - ox, p1[1] - oy), (p0[0] - ox, p0[1] - oy)],
               "#1a120c")
        c.line([p0, p1], "#2a1e14", 2 * s, 0.6)
    sx, sy = P(math.pi * 1.78, 1.04)                                                 # a leaning stake on the far lip
    c.line([(sx, sy + 6 * s), (sx + 22 * s, sy - 90 * s)], "#1a120c", 7 * s)
    for side in (-1, 1):                                                             # reeds and cattails at the ends
        for j in range(26):
            bx = x + side * a * r.uniform(0.95, 1.3)
            by = cy + r.uniform(-0.5, 0.9) * b
            hh = r.uniform(50, 150) * s
            lean = r.uniform(-14, 14) * s
            c.line([(bx, by), (bx + lean, by - hh)], "#070806", r.uniform(2, 4) * s)
            if j % 5 == 0:
                c.ellipse(bx + lean * 0.96, by - hh * 0.92, 4 * s, 13 * s, "#120c08")
    for j in range(80):                                                              # grass along the near lip
        t = r.uniform(0.12, math.pi - 0.12)
        bx, by = P(t, 1.02)
        c.line([(bx, by + 6 * s), (bx + r.uniform(-6, 6) * s, by - r.uniform(12, 38) * s)], "#060705", 2.2 * s)
    return []


@prop
def railfence(c, L, x, y, s=1.0, w=520, h=86, seed=1, color="#0a0806", **k):
    """A zigzag split-rail fence."""
    r = np.random.default_rng(seed)
    step = 92 * s
    n = int(2 * w * s / step) + 1
    pts = [(x - w * s + i * step, y + (8 if i % 2 else -8) * s) for i in range(n)]
    for i in range(n - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        for f in (0.22, 0.46, 0.7, 0.94):
            j0, j1 = r.uniform(-4, 4) * s, r.uniform(-4, 4) * s
            c.line([(ax - 8 * s, ay - h * s * f + j0), (bx + 8 * s, by - h * s * f + j1)], color, 6 * s)
    for (px, py) in pts:
        c.line([(px, py + 2 * s), (px + r.uniform(-3, 3) * s, py - h * s - 6 * s)], color, 5 * s)
    return []


@prop
def homestead(c, L, x, y, s=1.0, lit=1.0, flip=False, seed=3, **k):
    """A small 1850s frame farmhouse with a lean-to and a fieldstone chimney."""
    d = -1 if flip else 1
    r = np.random.default_rng(seed)
    x0, x1 = x - 170 * s, x + 170 * s
    top = y - 200 * s
    wall = "#0e0c0a"
    out = []
    lx0, lx1 = (x0 - 120 * s, x0) if d > 0 else (x1, x1 + 120 * s)              # the lean-to kitchen
    c.rect(lx0, y - 120 * s, lx1, y, "#0c0a08")
    c.poly([(lx0 - 8 * s, y - 112 * s), (lx1 + 8 * s, y - 112 * s), (lx1 + 8 * s, y - 150 * s) if d > 0 else
            (lx1, y - 168 * s), (lx0, y - 168 * s) if d > 0 else (lx0 - 8 * s, y - 150 * s)], "#070606")
    c.rect(x0, top, x1, y, wall)                                                   # the main house, clapboards
    for j in range(int(200 / 11)):
        c.line([(x0, y - j * 11 * s), (x1, y - j * 11 * s)], "#16120e", 1.0, 0.7)
    ridge = top - 110 * s                                                          # steep gable roof, end-on
    c.poly([(x0 - 14 * s, top + 4 * s), (x1 + 14 * s, top + 4 * s), (x1 - 40 * s, ridge), (x0 + 40 * s, ridge)],
           "#060606")
    c.line([(x0 + 40 * s, ridge), (x1 - 40 * s, ridge)], "#1a1612", 2 * s, 0.6)
    chx = x1 - 70 * s if d > 0 else x0 + 70 * s                                    # fieldstone chimney
    c.rect(chx - 22 * s, ridge - 40 * s, chx + 22 * s, top - 30 * s, "#1c1a18")
    for j in range(14):
        c.ellipse(chx + r.uniform(-14, 14) * s, ridge - 30 * s + r.uniform(0, 100) * s, r.uniform(5, 9) * s,
                  r.uniform(3, 6) * s, ("#2a2826", "#121110")[j % 2], 0.9)
    c.rect(chx - 26 * s, ridge - 46 * s, chx + 26 * s, ridge - 38 * s, "#141312")
    c.ellipse(chx + 10 * s, ridge - 80 * s, 26 * s, 14 * s, "#5a5650", 0.10, blur=8)  # a thread of smoke
    c.ellipse(chx + 34 * s, ridge - 128 * s, 38 * s, 18 * s, "#5a5650", 0.07, blur=10)
    dxw = (-100, 100) if d > 0 else (100, -100)
    for wx in (dxw[0], 40 * d):                                                    # two windows, six over six
        on = r.uniform() < lit
        wx0, wx1 = x + (wx - 26) * s, x + (wx + 26) * s
        K3._win(c, L, wx0, y - 150 * s, wx1, y - 66 * s, on, k=0.55)
        c.line([(wx0, y - 108 * s), (wx1, y - 108 * s)], "#0a0806", 3 * s)
        for f in (1 / 3, 2 / 3):
            c.line([(wx0 + (wx1 - wx0) * f, y - 150 * s), (wx0 + (wx1 - wx0) * f, y - 66 * s)], "#0a0806", 2 * s)
        c.rect(wx0 - 5 * s, y - 70 * s, wx1 + 5 * s, y - 62 * s, "#16120e")
        if on:
            out.append(((wx0 + wx1) / 2, y - 108 * s, (1.0, 0.74, 0.42), 70 * s, True, 0.35))
    dx0 = x + (dxw[1] - 28) * s                                                    # the door, shut
    c.rect(dx0, y - 136 * s, dx0 + 56 * s, y, "#090706")
    c.rect(dx0 - 10 * s, y - 6 * s, dx0 + 66 * s, y, "#16120e")
    return out


@prop
def lane(c, L, x, y, s=1.0, x2=900, rise=300, w=150, color="#221d17", a=0.85, **k):
    """A dirt lane from (x, y), w px wide, winding away to a thread at (x2, y - rise)."""
    y2 = y - rise
    n = 40
    p0, p3 = np.array([x, y], float), np.array([x2, y2], float)
    p1 = np.array([x + (x2 - x) * 0.1, y - (y - y2) * 0.5])
    p2 = np.array([x2 - (x2 - x) * 0.4, y2 + (y - y2) * 0.22])
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        q = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3
        hw = (w * s / 2) * (1 - t) ** 1.25 + 1.5
        left.append((q[0] - hw, q[1]))
        right.append((q[0] + hw, q[1]))
    c.poly(left + right[::-1], color, a, blur=2)
    return []


def _woman(c, x, y, h, color=INK, back=True):
    """One small woman in a long skirt and a shawl, from behind (h = her height in px)."""
    u = h / 150.0
    c.poly([(x - 13 * u, y - 92 * u), (x + 13 * u, y - 92 * u), (x + 31 * u, y - 4 * u), (x + 24 * u, y),
            (x - 26 * u, y), (x - 32 * u, y - 5 * u)], color, smooth=False)                  # the skirt
    c.poly([(x - 9 * u, y - 128 * u), (x + 9 * u, y - 128 * u), (x + 24 * u, y - 104 * u), (x + 12 * u, y - 76 * u),
            (x, y - 70 * u), (x - 12 * u, y - 76 * u), (x - 24 * u, y - 104 * u)], color)    # the shawl
    c.circle(x, y - 138 * u, 9.5 * u, color)                                                    # head, hair up
    c.circle(x + 2 * u, y - 147 * u, 5 * u, color)
    c.ellipse(x - 9 * u, y + 1 * u, 6 * u, 2.5 * u, color)                                      # a heel showing
    return []


@prop
def walker(c, L, x, y, s=1.0, color=INK, **k):
    """One small woman in a long dress and a shawl, walking away from us."""
    _woman(c, x, y, 150 * s, color)
    return []


def _man(c, x, y, h, lean=0.0, pole=0, color=INK, inv=False, a=1.0, blur=0):
    """A small man in a hat and a long coat; lean shifts his shoulders (px at h=150); pole=-1/1 a pole held down.
    inv=True draws him upside down below y, as a reflection in water."""
    u = h / 150.0
    lx = lean * u
    sg = -1 if inv else 1

    def Y(v):
        return y - sg * v * u

    def R(x0, v0, x1, v1, **kw):
        c.poly([(x0, Y(v0)), (x1, Y(v0)), (x1, Y(v1)), (x0, Y(v1))], color, a, blur=blur)

    R(x - 9 * u, 52, x - 3 * u, 0)                                                              # legs
    R(x + 3 * u, 52, x + 9 * u, 0)
    c.poly([(x - 20 * u, Y(46)), (x + 20 * u, Y(46)), (x + 16 * u + lx, Y(118)), (x - 16 * u + lx, Y(118))],
           color, a, blur=blur)                                                                 # the coat
    c.circle(x + lx * 1.15, Y(128), 9 * u, color, a, blur=blur)                                 # head
    c.ellipse(x + lx * 1.15, Y(135), 16 * u, 3.5 * u, color, a, blur=blur)                      # hat brim
    R(x + lx * 1.15 - 9 * u, 150, x + lx * 1.15 + 9 * u, 135)
    if pole:
        hx, hy = x + lx + 12 * u * pole, Y(100)
        c.line([(hx, hy), (hx + pole * 60 * u, Y(-40))], color, 3.2 * u, a, blur=blur)
        c.line([(hx, hy), (hx - pole * 18 * u, hy - sg * 36 * u)], color, 3.2 * u, a, blur=blur)
        c.line([(x + lx, Y(112)), (hx, hy)], color, 6 * u, a, blur=blur)
    return []


@prop
def pitmen(c, L, x, y, s=1.0, n=4, seed=1, spread=230, color=INK, poles=True, **k):
    """A few small men at the far edge of a pit, looking down; poles=True: the two at the ends hold long poles."""
    r = np.random.default_rng(seed)
    xs = np.linspace(x - spread * s, x + spread * s, n) + r.uniform(-20, 20, n) * s
    for i, px in enumerate(xs):
        side = -1 if px < x else 1
        lean = -side * r.uniform(4, 12)                                                         # leaning in
        pole = (side if i in (0, n - 1) and poles else 0) * -1
        _man(c, px, y + r.uniform(-6, 6) * s, 150 * s * r.uniform(0.92, 1.04), lean, pole, color)
    return []


@prop
def darkwater(c, L, x, y, s=1.0, h=760, seed=3, rust=1.0, sky="#46546a", **k):
    """Close on the pit's still water from its edge: the far wall's layers at the top, rust blooms and the pale sky
    in the water, slow rings, and the near bank's reeds in front. y is the near bank, h the water's height."""
    r = np.random.default_rng(seed)
    top = y - h
    c.rect(-20, top, 1100, y, "#070606")
    for j in range(24):                                                              # the sky, held at the far edge
        c.rect(-20, top + j * 12 * s, 1100, top + (j + 1) * 12 * s, sky, 0.5 * (1 - j / 24) ** 1.5)
    for j in range(9):                                                               # rust blooms in the water
        bx, by = r.uniform(60, 1020), r.uniform(top + 0.25 * h, y - 60)
        c.ellipse(bx, by, r.uniform(120, 260) * s, r.uniform(18, 40) * s, "#5a2a0a", 0.24 * rust, blur=22 * s)
    c.ellipse(x + 120 * s, top + 0.14 * h, 300 * s, 4 * s, "#c8d0d8", 0.18, blur=4 * s)  # a glint
    for j in range(3):                                                               # slow rings on the surface
        c.ellipse(x - 140 * s, top + 0.5 * h, (90 + j * 70) * s, (12 + j * 9) * s, "#8a96a0", 0.06, blur=2)
    wall = top - 150 * s                                                             # the far wall's layers
    for j, (col, hh) in enumerate((("#0c0906", 34), ("#2a160a", 22), ("#1c1a18", 24), ("#3a1e0c", 14),
                                   ("#22140a", 30), ("#0c0806", 26))):
        y0 = wall + sum(v for _, v in (("", 34), ("", 22), ("", 24), ("", 14), ("", 30), ("", 26))[:j]) * s
        pts = [(-20, y0)] + [(xx, y0 + 5 * s * math.sin(xx / 90.0 + j)) for xx in range(0, 1101, 60)]
        pts += [(1100, y0 + hh * s + 4), (-20, y0 + hh * s + 4)]
        c.poly(pts, col, 0.95)
    for j in range(50):                                                              # stones in the gravel
        c.ellipse(r.uniform(-10, 1090), wall + r.uniform(30, 140) * s, r.uniform(3, 7) * s, r.uniform(2, 4) * s,
                  ("#4a3a2a", "#1a120a", "#5a3a20")[j % 3], 0.75)
    for j in range(24):                                                              # roots hanging from the lip
        bx = r.uniform(-10, 1090)
        ln = r.uniform(30, 90) * s
        c.line([(bx, wall + 20 * s), (bx + r.uniform(-8, 8) * s, wall + 20 * s + ln * 0.5),
                (bx + r.uniform(-10, 10) * s, wall + 20 * s + ln)], "#0a0704", r.uniform(1.4, 2.6) * s, 0.9)
    for j in range(46):                                                              # grass along the top of the wall
        bx = r.uniform(-10, 1090)
        c.line([(bx, wall + 4 * s), (bx + r.uniform(-8, 8) * s, wall - r.uniform(20, 60) * s)], "#060705", 2.4 * s)
    c.poly([(-20, y - 30 * s)] + [(xx, y - 30 * s - 18 * s * math.sin(xx / 140.0)) for xx in range(0, 1101, 50)] +
           [(1100, y + 400), (-20, y + 400)], "#0a0806")                             # the near bank, mud
    for j in range(90):                                                              # reeds on the near bank
        bx = r.uniform(-20, 1100)
        if 300 < bx < 780 and r.uniform() < 0.7:
            continue
        hh = r.uniform(120, 420) * s * (1.3 if bx < 200 or bx > 880 else 0.8)
        lean = r.uniform(-22, 22) * s
        c.line([(bx, y + 20 * s), (bx + lean, y + 20 * s - hh)], "#050605", r.uniform(2.5, 5) * s)
        if j % 6 == 0:
            c.ellipse(bx + lean * 0.96, y + 20 * s - hh * 0.92, 6 * s, 20 * s, "#0c0806")
    return []


@prop
def hanglamp(c, L, x, y, s=1.0, **k):
    """An oil lamp hanging from the ceiling on a chain; y is the bottom of the lamp."""
    c.line([(x, -10), (x, y - 70 * s)], "#1a1612", 2.5 * s)
    c.poly([(x - 60 * s, y - 70 * s), (x + 60 * s, y - 70 * s), (x + 20 * s, y - 92 * s), (x - 20 * s, y - 92 * s)],
           "#2a2420")                                                                # the shade
    c.c.drawPath(smooth_path([(x - 14 * s, y - 70 * s), (x - 22 * s, y - 40 * s), (x - 12 * s, y - 6 * s),
                              (x + 12 * s, y - 6 * s), (x + 22 * s, y - 40 * s), (x + 14 * s, y - 70 * s)], True),
                 paint("#e8dcc0", 0.35))
    c.ellipse(x, y - 34 * s, 6 * s, 13 * s, "#ffd890", 0.95)
    c.ellipse(x, y, 16 * s, 6 * s, BRASS)
    return [(x, y - 36 * s, (1.0, 0.72, 0.38), 300 * s, True, 0.7)]


@prop
def handpress(c, L, x, y, s=1.0, sheet=True, **k):
    """A generic 19th-century iron hand press, seen from the front, with a sheet on its bed."""
    c.rect(x - 200 * s, y - 34 * s, x + 200 * s, y, IRON)                                      # the base and feet
    for fx in (-190, 150):
        c.rect(x + fx * s, y - 10 * s, x + (fx + 40) * s, y + 4 * s, "#0a0a0a")
    for ux in (-150, 112):                                                                       # the two uprights
        c.rect(x + ux * s, y - 440 * s, x + (ux + 38) * s, y - 34 * s, IRON)
        c.line([(x + (ux + 8) * s, y - 430 * s), (x + (ux + 8) * s, y - 44 * s)], IRON_L, 2 * s, 0.7)
    arch = [(x - 150 * s, y - 436 * s)] + [(x - 150 * s * math.cos(math.pi * t / 16),
                                            y - 436 * s - 60 * s * math.sin(math.pi * t / 16)) for t in range(17)]
    c.line(arch, IRON, 34 * s)                                                                   # the arched crown
    c.rect(x - 150 * s, y - 400 * s, x + 150 * s, y - 368 * s, IRON)                             # the head
    c.rect(x - 12 * s, y - 368 * s, x + 12 * s, y - 300 * s, IRON_L)                             # spindle and toggle
    c.rect(x - 100 * s, y - 300 * s, x + 100 * s, y - 266 * s, IRON)                             # the platen
    c.line([(x - 96 * s, y - 268 * s), (x + 96 * s, y - 268 * s)], IRON_L, 2 * s, 0.8)
    c.rect(x - 330 * s, y - 236 * s, x + 320 * s, y - 214 * s, IRON)                             # the rails and bed
    for lx in (-322, 300):                                                                       # rail legs
        c.rect(x + lx * s, y - 214 * s, x + (lx + 18) * s, y, IRON)
    tp = [(x - 330 * s, y - 238 * s), (x - 220 * s, y - 238 * s), (x - 250 * s, y - 420 * s), (x - 352 * s, y - 412 * s)]
    c.line(tp + [tp[0]], IRON_L, 8 * s)                                                         # the tympan, raised
    if sheet:
        c.poly([(tp[0][0] + 10 * s, tp[0][1] - 8 * s), (tp[1][0] - 12 * s, tp[1][1] - 8 * s),
                (tp[2][0] - 8 * s, tp[2][1] + 10 * s), (tp[3][0] + 8 * s, tp[3][1] + 10 * s)], PAPER, 0.9)
        c.rect(x - 90 * s, y - 248 * s, x + 90 * s, y - 238 * s, PAPER, 0.9)                     # a sheet on the bed
    bar = [(x + 150 * s, y - 330 * s), (x + 230 * s, y - 318 * s), (x + 300 * s, y - 290 * s)]  # the bar
    c.line(bar, IRON, 14 * s)
    c.line([(x + 296 * s, y - 292 * s), (x + 336 * s, y - 270 * s)], "#3a2416", 18 * s)
    c.circle(x + 340 * s, y - 225 * s, 22 * s, IRON_L)                                          # the rounce handle
    c.line([(x + 340 * s, y - 225 * s), (x + 362 * s, y - 200 * s)], IRON_L, 6 * s)
    return []


@prop
def typecase(c, L, x, y, s=1.0, line=True, seed=2, **k):
    """A printer's type cabinet with its slanted case, and printed sheets drying on a line above."""
    r = np.random.default_rng(seed)
    c.rect(x - 170 * s, y - 250 * s, x + 170 * s, y, WOOD)                                      # the cabinet
    for j in range(7):                                                                           # shallow drawers
        yy = y - 236 * s + j * 32 * s
        c.rect(x - 160 * s, yy, x + 160 * s, yy + 26 * s, WOOD_D)
        c.rect(x - 14 * s, yy + 10 * s, x + 14 * s, yy + 15 * s, BRASS, 0.8)
    tray = [(x - 186 * s, y - 252 * s), (x + 186 * s, y - 252 * s), (x + 166 * s, y - 360 * s), (x - 166 * s, y - 360 * s)]
    c.poly(tray, "#3a2a1a")                                                                     # the slanted case
    for j in range(1, 8):                                                                        # its compartments
        f = j / 8
        yl = y - 252 * s - 108 * s * f
        hw = 186 * s - 20 * s * f
        c.line([(x - hw, yl), (x + hw, yl)], "#160e08", 2 * s)
    for j in range(1, 14):
        f = j / 14
        c.line([(x - 186 * s + 372 * s * f, y - 252 * s), (x - 166 * s + 332 * s * f, y - 360 * s)], "#160e08", 2 * s)
    c.rect(x + 40 * s, y - 300 * s, x + 130 * s, y - 286 * s, "#6a6a66")                        # a composing stick
    if line:                                                                                     # sheets drying above
        y0 = y - 640 * s
        c.line([(x - 330 * s, y0), (x, y0 + 16 * s), (x + 330 * s, y0)], "#1a1612", 2 * s)
        for j in range(5):
            px = x - 270 * s + j * 135 * s
            py = y0 + 16 * s * (1 - abs(px - x) / (330 * s)) + 2 * s
            rot = r.uniform(-0.04, 0.04)
            pts = [(-46, 0), (46, 0), (46, 120), (-46, 120)]
            ca, sa = math.cos(rot), math.sin(rot)
            c.poly([(px + (a * ca - b * sa) * s, py + (a * sa + b * ca) * s) for a, b in pts], PAPER, 0.9)
            for t in range(9):                                                                   # unreadable columns
                yy = 16 + t * 11
                for cx0 in (-40, 4):
                    p0 = (px + ((cx0) * ca - yy * sa) * s, py + ((cx0) * sa + yy * ca) * s)
                    p1 = (px + ((cx0 + 36) * ca - yy * sa) * s, py + ((cx0 + 36) * sa + yy * ca) * s)
                    c.line([p0, p1], "#6a6250", 1.6 * s, 0.55)
            c.rect(px - 4 * s, py - 6 * s, px + 4 * s, py + 6 * s, "#3a2a1a")
    return []


@prop
def rolltop(c, L, x, y, s=1.0, lamp=True, seed=5, **k):
    """An editor's roll-top desk with pigeonholes, an oil lamp, a paper spike, a paste pot and scissors."""
    r = np.random.default_rng(seed)
    out = []
    for px in (-270, 110):                                                                       # two pedestals
        c.rect(x + px * s, y - 200 * s, x + (px + 160) * s, y, WOOD)
        for j in range(4):
            yy = y - 190 * s + j * 47 * s
            c.rect(x + (px + 10) * s, yy, x + (px + 150) * s, yy + 40 * s, WOOD_D)
            c.circle(x + (px + 80) * s, yy + 20 * s, 4 * s, BRASS)
    c.rect(x - 282 * s, y - 218 * s, x + 282 * s, y - 200 * s, "#3a2416")                       # the writing bed
    for side in (-1, 1):                                                                         # curved side panels
        sx = x + side * 262 * s
        c.poly([(sx - 14 * s, y - 218 * s), (sx + 14 * s, y - 218 * s), (sx + 14 * s, y - 330 * s),
                (sx + 4 * s * side, y - 400 * s), (sx - 14 * s * side, y - 430 * s), (sx - 14 * s, y - 330 * s)], WOOD)
    c.rect(x - 250 * s, y - 432 * s, x + 250 * s, y - 392 * s, "#1e120a")                       # the rolled-up tambour
    for j in range(5):
        c.line([(x - 250 * s, y - 428 * s + j * 8 * s), (x + 250 * s, y - 428 * s + j * 8 * s)], "#0c0806", 1.4 * s)
    c.rect(x - 248 * s, y - 392 * s, x + 248 * s, y - 220 * s, "#0c0806")                        # the pigeonholes
    for row in range(3):
        for col in range(8):
            cx0 = x - 244 * s + col * 61 * s
            cy0 = y - 386 * s + row * 52 * s
            c.rect(cx0, cy0, cx0 + 55 * s, cy0 + 46 * s, "#160d08")
            if r.uniform() < 0.55:                                                               # papers stuffed in
                c.rect(cx0 + 6 * s, cy0 + r.uniform(10, 22) * s, cx0 + 49 * s, cy0 + 46 * s, PAPER, 0.75)
    c.rect(x - 60 * s, y - 238 * s, x + 90 * s, y - 220 * s, PAPER, 0.9)                         # papers on the bed
    c.line([(x - 40 * s, y - 230 * s), (x + 70 * s, y - 230 * s)], "#6a6250", 1.4 * s, 0.6)
    sx = x + 160 * s                                                                             # the paper spike
    c.ellipse(sx, y - 220 * s, 22 * s, 6 * s, IRON)
    c.line([(sx, y - 222 * s), (sx, y - 300 * s)], "#5a5a56", 3 * s)
    for j in range(6):
        c.poly([(sx - 26 * s, y - 230 * s - j * 9 * s), (sx + 24 * s, y - 234 * s - j * 9 * s),
                (sx + 22 * s, y - 228 * s - j * 9 * s), (sx - 24 * s, y - 224 * s - j * 9 * s)], PAPER, 0.85)
    px = x + 220 * s                                                                             # paste pot and brush
    c.rect(px - 14 * s, y - 250 * s, px + 14 * s, y - 220 * s, "#2a2a30", r=4 * s)
    c.line([(px, y - 246 * s), (px + 18 * s, y - 296 * s)], "#3a2416", 4 * s)
    for t, ang in ((0, 0.35), (1, -0.35)):                                                       # scissors
        ex, ey = x + 30 * s + math.cos(ang) * 50 * s, y - 224 * s - math.sin(ang) * 10 * s
        c.line([(x + 30 * s, y - 224 * s), (ex, ey)], "#6a6a66", 2.5 * s)
        c.circle(x + 30 * s - math.cos(ang) * 14 * s, y - 224 * s + math.sin(ang) * 6 * s, 6 * s, "#6a6a66", 0.9)
    if lamp:
        lx = x - 180 * s
        c.ellipse(lx, y - 222 * s, 40 * s, 10 * s, BRASS)
        c.poly([(lx - 30 * s, y - 224 * s), (lx + 30 * s, y - 224 * s), (lx + 22 * s, y - 272 * s),
                (lx - 22 * s, y - 272 * s)], "#6a5428")
        c.rect(lx - 8 * s, y - 284 * s, lx + 8 * s, y - 272 * s, BRASS)
        c.c.drawPath(smooth_path([(lx - 12 * s, y - 284 * s), (lx - 20 * s, y - 322 * s), (lx - 12 * s, y - 362 * s),
                                  (lx + 12 * s, y - 362 * s), (lx + 20 * s, y - 322 * s), (lx + 12 * s, y - 284 * s)], True),
                     paint("#e8dcc0", 0.35))
        c.ellipse(lx, y - 318 * s, 6 * s, 14 * s, "#ffd890", 0.9)
        out.append((lx, y - 322 * s, (1.0, 0.72, 0.38), 280 * s, True, 0.75))
    ch = x - 20 * s                                                                              # the chair
    c.rect(ch - 70 * s, y - 116 * s, ch + 70 * s, y - 96 * s, "#100906")
    for lx2 in (-64, 54):
        c.rect(ch + lx2 * s, y - 96 * s, ch + (lx2 + 10) * s, y + 40 * s, "#100906")
    c.line([(ch - 62 * s, y - 116 * s), (ch - 56 * s, y - 300 * s), (ch + 56 * s, y - 300 * s), (ch + 62 * s, y - 116 * s)],
           "#100906", 10 * s)
    return out


@prop
def coach(c, L, x, y, s=1.0, lit=0.8, flip=False, seed=6, **k):
    """An 1890s wooden passenger coach on its track (see the top of this file). x is the coach's middle."""
    d = -1 if flip else 1
    r = np.random.default_rng(seed)
    out = []
    c.rect(-20, y - 4 * s, 1100, y + 10 * s, "#2c2e30")                                          # the rail and ties
    for j in range(0, 1120, int(40 * s)):
        c.rect(j, y + 6 * s, j + 22 * s, y + 18 * s, "#141210")
    x0, x1 = x - 460 * s, x + 460 * s
    b0, b1 = y - 330 * s, y - 104 * s
    for tx in (x0 + 140 * s, x1 - 140 * s):                                                      # two trucks
        c.rect(tx - 90 * s, y - 70 * s, tx + 90 * s, y - 40 * s, "#0c0c0c")
        for wx in (-50, 50):
            c.circle(tx + wx * s, y - 30 * s, 28 * s, "#141414")
            c.circle(tx + wx * s, y - 30 * s, 8 * s, "#3a3a3a")
    c.line([(x0 + 60 * s, b1), (x - 120 * s, y - 60 * s), (x + 120 * s, y - 60 * s), (x1 - 60 * s, b1)],
           "#0a0a0a", 4 * s)                                                                     # truss rods
    c.rect(x0, b0, x1, b1, "#1b100a")                                                            # the body
    c.line([(x0, b0 + 46 * s), (x1, b0 + 46 * s)], "#8a6a30", 2 * s, 0.6)                        # pinstripes
    c.line([(x0, b1 - 40 * s), (x1, b1 - 40 * s)], "#8a6a30", 2 * s, 0.5)
    nwin = 11
    for i in range(nwin):                                                                        # arched windows
        wx = x0 + 70 * s + i * (x1 - x0 - 140 * s) / (nwin - 1)
        on = r.uniform() < lit
        top, bot = b0 + 60 * s, b0 + 150 * s
        pts = [(wx - 20 * s, bot), (wx - 20 * s, top + 20 * s)]
        pts += [(wx - 20 * s * math.cos(math.pi * t / 8), top + 20 * s - 20 * s * math.sin(math.pi * t / 8)) for t in range(9)]
        pts += [(wx + 20 * s, top + 20 * s), (wx + 20 * s, bot)]
        c.poly(pts, "#070606")
        if on:
            L.poly(pts, WARM, 0.55)
            out.append((wx, (top + bot) / 2, (1.0, 0.74, 0.42), 46 * s, False, 0.22))
    c.poly([(x0 - 30 * s, b0), (x1 + 30 * s, b0), (x1 + 10 * s, b0 - 22 * s), (x0 - 10 * s, b0 - 22 * s)], "#0a0806")
    c.rect(x0 + 50 * s, b0 - 58 * s, x1 - 50 * s, b0 - 20 * s, "#140c08")                        # the clerestory
    for i in range(18):
        cx0 = x0 + 70 * s + i * (x1 - x0 - 140 * s) / 18
        c.rect(cx0, b0 - 50 * s, cx0 + 22 * s, b0 - 30 * s, "#070606")
        if r.uniform() < lit * 0.7:
            L.rect(cx0, b0 - 50 * s, cx0 + 22 * s, b0 - 30 * s, WARM, 0.35)
    c.poly([(x0 + 40 * s, b0 - 58 * s), (x1 - 40 * s, b0 - 58 * s), (x1 - 60 * s, b0 - 70 * s), (x0 + 60 * s, b0 - 70 * s)],
           "#0a0806")
    ex = x1 if d > 0 else x0                                                                     # the end platform
    e2 = ex + d * 80 * s
    c.rect(min(ex, e2), b1 - 4 * s, max(ex, e2), b1 + 8 * s, "#0e0a08")
    c.line([(e2, b1), (e2, b0 + 40 * s)], "#2a2a2a", 4 * s)                                      # railing post
    c.line([(ex, b0 + 70 * s), (e2, b0 + 70 * s)], "#2a2a2a", 4 * s)
    for j in range(3):                                                                           # the steps down
        sx0 = e2 - d * (16 + j * 6) * s
        sy = b1 + (26 + j * 26) * s
        c.rect(min(sx0, sx0 - d * 46 * s), sy, max(sx0, sx0 - d * 46 * s), sy + 8 * s, "#1a1612")
    c.line([(e2, b1), (e2 - d * 10 * s, b1 + 90 * s)], "#1a1612", 4 * s)
    door = ex - d * 6 * s                                                                        # the end door, lit
    c.rect(min(door, door - d * 44 * s), b0 + 40 * s, max(door, door - d * 44 * s), b1, "#0a0605")
    L.rect(min(door, door - d * 44 * s), b0 + 52 * s, max(door, door - d * 44 * s), b0 + 140 * s, WARM, 0.5 * lit)
    c.poly([(ex, b0 - 22 * s), (e2 + d * 6 * s, b0 - 10 * s), (e2 + d * 6 * s, b0 - 2 * s), (ex, b0 - 8 * s)], "#0a0806")
    return out


@prop
def stationlamp(c, L, x, y, s=1.0, **k):
    """A lamp on a post, lit."""
    c.rect(x - 5 * s, y - 300 * s, x + 5 * s, y, "#0c0c0c")
    c.rect(x - 16 * s, y - 304 * s, x + 16 * s, y - 296 * s, "#0c0c0c")
    c.poly([(x - 18 * s, y - 304 * s), (x + 18 * s, y - 304 * s), (x + 22 * s, y - 350 * s), (x - 22 * s, y - 350 * s)],
           "#2a2420")
    c.rect(x - 14 * s, y - 344 * s, x + 14 * s, y - 310 * s, "#ffd890", 0.85)
    L.rect(x - 14 * s, y - 344 * s, x + 14 * s, y - 310 * s, WARM, 0.8)
    c.poly([(x - 28 * s, y - 350 * s), (x + 28 * s, y - 350 * s), (x, y - 372 * s)], "#0c0c0c")
    return [(x, y - 327 * s, (1.0, 0.76, 0.45), 150 * s, True, 0.55)]
