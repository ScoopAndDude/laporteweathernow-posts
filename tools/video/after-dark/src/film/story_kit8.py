"""Props for the Portage and Lake Station shorts (story_kit8.py; added Nov. 14, 2026, for the Crisman gravestones
turned up at U.S. 20 and Crisman Road in 1962, and for Liverpool, Lake County's lost first county seat). They register
themselves in story_kit3.PROPS, so any tab_* scene can use them:

    foundstones  a pale, unpolished marble family monument and two small headstones (no inscriptions drawn)
                 buried=0..1  raw dirt heaped over their lower part   tilt=True  leaning, as if just turned up
                 lamp=True  a lantern set on the dirt, lighting them   mono=False  the two headstones only
    dirt         a raw excavation: a heap of fresh dirt and the dark lip of the pit in front (w=, h=)
    backhoe      a late-1950s tractor backhoe-loader: big rear wheels, a loader bucket in front, the digging arm
                 raised behind (flip=True faces the other way); no one in the seat
    routesign    a U.S. highway shield on a post (num="20"). Signs show only what is really on the real sign
    highway      a highway across the middle distance, a side road running toward the viewer, and telephone poles
                 with sagging wires along it (side=False: no side road; dashes=False: no centre line, lanes left vague)
    farmhouse    an 1870s two-storey frame farmhouse with a porch and a chimney; lit=[0/1, 0/1, 0/1] windows that
                 glow (upstairs left, upstairs right, downstairs); smoke=True a thin chimney plume
    bank         a high bank overgrown with brush rising across the picture (w, h; flip=True rises the other way).
                 Put trees on it with their y at the bank top (ground y minus h)
    confluence   a river winding toward the viewer from the horizon, a second river joining it from one side
                 (side=1 right, -1 left), a moon glint on the water (moon_x=); use in a land scene with "grass": false
    moonpath     the moon's reflection on open water: a column of short bright ripples down from the horizon
    stakes       a new town staked out on open ground: rows of survey stakes with small white flags
    timberframe  an unfinished two-storey timber-frame building: open studs and rafters, the lower part sided
                 (done=0..1), a ladder and scaffold poles, lumber stacked in front
    halfbuilt    a small building left unfinished, in silhouette only: walls partly up with a ragged top, no roof,
                 scaffold poles, a ladder and lumber (it doesn't say log or frame; sources differ for Liverpool's)
    scow         a flat-bottomed river scow carrying an unfinished building, two small figures poling it
                 (cargo="frame" the timber frame, cargo="halfbuilt" the silhouette)
    riders       n small horseback riders (story_kit2.horse with a rider), facing right (flip=True: left)
    wagon        a covered wagon and its two-horse team, facing right (flip=True: left; team=False: no horses)
    loghouse     a long log building with a chimney (Crown Point's first court house was a log building);
                 storeys=2 makes it two storeys high
    depot2       a two-storey board-and-batten railroad depot of the 1850s with deep eaves and a platform
    townfire     a few small, empty frame and log buildings burning at night: flames, smoke, sparks, flickering light

People are small anonymous silhouettes. Nothing shows a body, a real person's likeness, an inscription or a brand.
"""
import math
import os

import numpy as np
import skia

import art
import reels_common as C
import story_kit2 as K2
import story_kit3 as K3
from story_kit import W, WARM
from core import paint

prop = K3.prop
MARBLE = "#868a88"
MARBLE_D = "#5a5e5e"
MARBLE_L = "#aeb2ae"
DIRT = "#221a13"
DIRT_L = "#3a2d21"
_TF = {}


def _text(c, txt, cx, cy, size, color, fname="Inter-Bold.otf"):
    """Text centred on (cx, cy), drawn straight onto the canvas."""
    if fname not in _TF:
        _TF[fname] = skia.Typeface.MakeFromFile(os.path.join(C.FONTS, fname))
    f = skia.Font(_TF[fname], size)
    c.c.drawString(txt, cx - f.measureText(txt) / 2, cy + size * 0.36, f, paint(color))


def _rot(pts, x, y, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in pts]


# ------------------------------------------------------------------------------------------- the Crisman stones

def _headstone(c, x, y, w, h, tilt=0.0, col=MARBLE):
    """A small round-topped headstone, base centre (x, y), leaning tilt radians."""
    arc = [(-w / 2 * math.cos(math.pi * t / 12), -h + w * 0.28 * (1 - math.sin(math.pi * t / 12)) - w * 0.0)
           for t in range(13)]
    body = [(-w / 2, 0)] + [(px, py + w * 0.0) for px, py in arc] + [(w / 2, 0)]
    c.poly(_rot(body, x, y, tilt), col)
    side = [(w * 0.30, 0), (w * 0.30, -h * 0.80), (w / 2, -h * 0.74), (w / 2, 0)]
    c.poly(_rot(side, x, y, tilt), MARBLE_D, 0.75)
    rim = [(px * 0.86, py + h * 0.06) for px, py in arc[2:11]]
    c.line(_rot(rim, x, y, tilt), MARBLE_L, max(1.0, w * 0.03), 0.5)


def _monument(c, x, y, s, tilt=0.0, col=MARBLE):
    """A family monument: a wide base, a tall die and a peaked cap."""
    parts = [
        ([(-80, 0), (-80, -40), (80, -40), (80, 0)], col),                                     # base
        ([(-56, -40), (-56, -170), (56, -170), (56, -40)], col),                               # die
        ([(-68, -170), (-68, -186), (0, -232), (68, -186), (68, -170)], col),                  # cap
        ([(28, -40), (28, -170), (56, -170), (56, -40)], MARBLE_D),                            # shaded side of the die
        ([(48, 0), (48, -40), (80, -40), (80, 0)], MARBLE_D),
    ]
    for pts, cc in parts:
        c.poly(_rot([(px * s, py * s) for px, py in pts], x, y, tilt), cc, 0.92 if cc == MARBLE_D else 1.0)
    c.line(_rot([(-50 * s, -150 * s), (50 * s, -150 * s)], x, y, tilt), MARBLE_L, 2 * s, 0.45)    # carved band
    c.line(_rot([(-50 * s, -60 * s), (50 * s, -60 * s)], x, y, tilt), MARBLE_D, 2 * s, 0.5)


@prop
def foundstones(c, L, x, y, s=1.0, buried=0.3, tilt=True, lamp=False, mono=True, seed=4, **k):
    """The Crisman stones: a family monument and two headstones of unpolished marble (no inscriptions drawn)."""
    r = np.random.default_rng(seed)
    out = []
    if mono:
        _monument(c, x, y - 6 * s, s, -0.05 if tilt else 0.0)
    for dx, a in ((-170, -0.16), (172, 0.11)):
        _headstone(c, x + dx * s, y + 22 * s, 78 * s, 124 * s, a if tilt else 0.0)
    if buried > 0:
        hh = 160 * s * buried
        pts = [(x - 380 * s, y + 70 * s)]
        for j in range(31):
            f = j / 30
            pts.append((x - 380 * s + 760 * s * f,
                        y + 46 * s - hh * (math.sin(math.pi * f) ** 0.5) * (0.82 + 0.3 * r.uniform())))
        pts.append((x + 380 * s, y + 70 * s))
        c.poly(pts, DIRT, smooth=True)
        for j in range(46):
            f = r.uniform(0.05, 0.95)
            top = y + 46 * s - hh * math.sin(math.pi * f) ** 0.5
            cx = x - 380 * s + 760 * s * f
            c.ellipse(cx, r.uniform(top + 10 * s, y + 60 * s), r.uniform(6, 15) * s, r.uniform(4, 8) * s, DIRT_L, 0.8)
    if lamp:                                              # a lantern set down on the dirt, lighting them
        lx, ly = x - 300 * s, y + 30 * s
        c.rect(lx - 13 * s, ly - 44 * s, lx + 13 * s, ly - 6 * s, "#2a2018", r=4 * s)
        c.rect(lx - 9 * s, ly - 40 * s, lx + 9 * s, ly - 12 * s, "#ffd080", 0.9)
        c.rect(lx - 16 * s, ly - 8 * s, lx + 16 * s, ly, "#140f0b", r=3 * s)
        c.rect(lx - 10 * s, ly - 52 * s, lx + 10 * s, ly - 44 * s, "#140f0b", r=3 * s)
        c.c.drawPath(_sag(lx - 11 * s, ly - 52 * s, lx + 11 * s, ly - 52 * s, -9 * s), paint("#140f0b", stroke=2.5 * s))
        out.append((lx, ly - 26 * s, (1.0, 0.82, 0.55), 30 * s, True, 0.9))
        L.circle(lx + 120 * s, ly - 110 * s, 300 * s, "#ffcf8a", 0.22, blur=60 * s)
    return out


@prop
def dirt(c, L, x, y, s=1.0, w=640, h=150, seed=2, pit=True, **k):
    """A raw excavation: a heap of fresh dirt, and the dark lip of the pit in front of it."""
    r = np.random.default_rng(seed)
    if pit:
        c.ellipse(x + 60 * s, y + 70 * s, w * 0.62 * s, 52 * s, "#020202")
        c.ellipse(x + 60 * s, y + 60 * s, w * 0.62 * s, 40 * s, "#0b0907")
        c.ellipse(x + 60 * s, y + 74 * s, w * 0.56 * s, 34 * s, "#010101")
    pts = [(x - w / 2 * s, y + 6 * s)]
    for j in range(33):
        f = j / 32
        pts.append((x - w / 2 * s + w * s * f, y - h * s * (math.sin(math.pi * f) ** 0.8) * (0.86 + 0.24 * r.uniform())))
    pts.append((x + w / 2 * s, y + 6 * s))
    c.poly(pts, DIRT, smooth=True)
    for j in range(60):
        f = r.uniform(0.04, 0.96)
        top = y - h * s * math.sin(math.pi * f) ** 0.8
        c.ellipse(x - w / 2 * s + w * s * f, r.uniform(top + 8 * s, y), r.uniform(5, 15) * s, r.uniform(3, 8) * s,
                  DIRT_L, r.uniform(0.5, 0.9))


@prop
def backhoe(c, L, x, y, s=1.0, flip=False, **k):
    """A late-1950s tractor backhoe-loader, the digging arm raised (no one in the seat). Faces right; flip=True left."""
    d = -1 if flip else 1
    INK = "#0b0b0c"

    def X(v):
        return x + d * v * s

    c.circle(X(-70), y - 62 * s, 62 * s, INK)                                    # rear wheel
    c.circle(X(-70), y - 62 * s, 26 * s, "#1c1d1f")
    c.circle(X(110), y - 34 * s, 34 * s, INK)                                    # front wheel
    c.circle(X(110), y - 34 * s, 14 * s, "#1c1d1f")
    c.poly([(X(-110), y - 90 * s), (X(150), y - 80 * s), (X(160), y - 40 * s), (X(-110), y - 52 * s)], INK)   # frame
    c.poly([(X(30), y - 82 * s), (X(150), y - 80 * s), (X(150), y - 126 * s), (X(40), y - 130 * s)], "#121214")  # hood
    c.line([(X(120), y - 126 * s), (X(120), y - 160 * s)], INK, 6 * s)                                        # exhaust
    c.line([(X(-30), y - 90 * s), (X(-30), y - 170 * s)], INK, 4 * s)                                        # seat post
    c.rect(min(X(-50), X(-12)), y - 128 * s, max(X(-50), X(-12)), y - 112 * s, INK)                       # seat
    c.line([(X(10), y - 104 * s), (X(-2), y - 150 * s)], INK, 4 * s)                                         # steering
    c.line([(X(150), y - 70 * s), (X(220), y - 40 * s)], INK, 9 * s)                                         # loader arms
    c.poly([(X(206), y - 6 * s), (X(262), y - 6 * s), (X(268), y - 62 * s), (X(224), y - 66 * s)], INK)      # bucket
    p0 = (X(-120), y - 80 * s)                                                                              # backhoe
    p1 = (X(-250), y - 250 * s)
    p2 = (X(-330), y - 120 * s)
    c.line([p0, p1], INK, 16 * s)
    c.line([p1, p2], INK, 12 * s)
    c.poly([p2, (p2[0] - d * 36 * s, p2[1] + 22 * s), (p2[0] - d * 14 * s, p2[1] + 60 * s), (p2[0] + d * 22 * s, p2[1] + 30 * s)],
           INK)
    c.line([(X(-120), y - 40 * s), (X(-150), y)], INK, 6 * s)                                                # stabilizer
    return []


@prop
def routesign(c, L, x, y, s=1.0, num="20", **k):
    """A U.S. highway route marker on a post: a white shield with black numerals on a black square plate."""
    c.rect(x - 5 * s, y - 250 * s, x + 5 * s, y, "#1c1e1c")
    c.rect(x - 56 * s, y - 360 * s, x + 56 * s, y - 248 * s, "#0a0a0a", r=5 * s)
    cx, cy, sw, sh = x, y - 304 * s, 92 * s, 96 * s
    shield = [(-0.50, -0.40), (-0.30, -0.50), (0.0, -0.43), (0.30, -0.50), (0.50, -0.40), (0.47, 0.02),
              (0.36, 0.28), (0.0, 0.50), (-0.36, 0.28), (-0.47, 0.02)]
    c.poly([(cx + px * sw, cy + py * sh) for px, py in shield], "#e6e6e0", smooth=True)
    _text(c, num, cx, cy + 4 * s, 46 * s, "#0a0a0a")


@prop
def highway(c, L, x, y, s=1.0, side=True, poles=True, dashes=True, **k):
    """A highway across the picture at y, a side road running toward the viewer at x, telephone poles.
    dashes=False: no centre line, so the picture doesn't say how many lanes there were."""
    c.poly([(-20, y), (W + 20, y), (W + 20, y + 52 * s), (-20, y + 52 * s)], "#16181b")
    c.line([(-20, y + 1), (W + 20, y + 1)], "#2a2d30", 2, 0.8)
    for j in range(0, W + 60, int(76 * s)) if dashes else ():
        c.rect(j, y + 24 * s, j + 36 * s, y + 28 * s, "#9a9478", 0.55)
    if side:
        c.poly([(x - 70 * s, y + 52 * s), (x + 70 * s, y + 52 * s), (x + 520 * s, y + 900 * s), (x - 520 * s, y + 900 * s)],
               "#141619")
        c.line([(x - 70 * s, y + 52 * s), (x - 520 * s, y + 900 * s)], "#2a2b2c", 3, 0.6)
        c.line([(x + 70 * s, y + 52 * s), (x + 520 * s, y + 900 * s)], "#2a2b2c", 3, 0.6)
    if poles:
        tops = []
        for j in range(7):
            px = -60 + j * 200
            ph = 250 * s
            c.line([(px, y - 4 * s), (px, y - ph)], "#0b0c0d", 6 * s)
            c.line([(px - 34 * s, y - ph + 18 * s), (px + 34 * s, y - ph + 18 * s)], "#0b0c0d", 4 * s)
            tops.append((px, y - ph + 18 * s))
        for (ax, ay), (bx, by) in zip(tops, tops[1:]):
            for off in (-26, 26):
                mx = (ax + bx) / 2
                c.c.drawPath(_sag(ax + off * s, ay, bx + off * s, by, 16 * s), paint("#0b0c0d", 0.9, stroke=1.4))


def _sag(ax, ay, bx, by, d):
    p = skia.Path()
    p.moveTo(ax, ay)
    p.quadTo((ax + bx) / 2, (ay + by) / 2 + 2 * d, bx, by)
    return p


@prop
def farmhouse(c, L, x, y, s=1.0, lit=(0, 1, 0), smoke=True, brick=False, **k):
    """An 1870s two-storey gable-front frame farmhouse with a porch and a chimney.
    brick=True (Nov. 21, 2026, for the Gunness house, 'a square house of red brick'): dark red brick walls."""
    wall = "#2e1812" if brick else "#13110e"
    x0, x1 = x - 120 * s, x + 120 * s
    c.rect(x0, y - 250 * s, x1, y, wall)
    c.poly([(x0 - 16 * s, y - 246 * s), (x, y - 372 * s), (x1 + 16 * s, y - 246 * s)], wall)
    c.line([(x0 - 16 * s, y - 246 * s), (x, y - 372 * s), (x1 + 16 * s, y - 246 * s)], "#070605", 9 * s)
    for j in range(40 if brick else 16):
        yy = y - (12 + j * (6 if brick else 15)) * s
        c.line([(x0, yy), (x1, yy)], "#1a0d09" if brick else "#1d1914", 1.0 if brick else 1.2, 0.6 if brick else 0.7)
    wins = [(-76, -224, -40, -160), (40, -224, 76, -160), (-76, -112, -40, -50)]
    out = []
    for i, (a, b, cc, d) in enumerate(wins):
        on = i < len(lit) and lit[i]
        K3._win(c, L, x + a * s, y + b * s, x + cc * s, y + d * s, on)
        if on:
            out.append((x + (a + cc) / 2 * s, y + (b + d) / 2 * s, (1.0, 0.74, 0.42), 80 * s, True, 0.45))
    c.rect(x - 16 * s, y - 330 * s, x + 16 * s, y - 296 * s, "#070605")                     # attic window, dark
    c.rect(x + 30 * s, y - 112 * s, x + 68 * s, y, "#070605")                               # door
    c.poly([(x0 - 34 * s, y - 130 * s), (x1 + 34 * s, y - 130 * s), (x1 + 44 * s, y - 112 * s), (x0 - 44 * s, y - 112 * s)],
           "#090807")
    for px in (-148, -62, 62, 148):
        c.rect(x + (px - 4) * s, y - 112 * s, x + (px + 4) * s, y, "#090807")
    cx = x + 66 * s
    c.rect(cx - 15 * s, y - 360 * s, cx + 15 * s, y - 290 * s, "#0b0908")
    if smoke:
        for j in range(9):
            c.circle(cx + j * 12 * s, y - (384 + j * 34) * s, (12 + j * 4) * s, "#4a4c50", 0.10)
    return out


@prop
def bank(c, L, x, y, s=1.0, w=1200, h=230, seed=3, flip=False, **k):
    """A high bank overgrown with brush: it rises across the picture and runs on as a wooded top."""
    r = np.random.default_rng(seed)
    d = -1 if flip else 1
    rise0, rise1 = x - d * w * 0.42 * s, x - d * w * 0.10 * s
    edge = W + 40 if d > 0 else -40
    top = []
    n = 40
    for j in range(n + 1):
        f = j / n
        px = rise0 + (edge - rise0) * f
        if (px - rise1) * d < 0:
            g = (px - rise0) / (rise1 - rise0)
            py = y - h * s * (0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, g))))
        else:
            py = y - h * s * (0.96 + 0.06 * r.uniform())
        top.append((px, py))
    c.poly([(rise0, y + 4)] + top + [(edge, y + 4)], "#040605", smooth=True)
    for px, py in top[::2]:
        c.line([(px - 18 * s, py + 2), (px + 18 * s, py + 2)], "#24323a", 2, 0.35)
    for j in range(90):                                   # brush along the top edge
        f = r.uniform(0.0, 1.0)
        i = int(f * n)
        px, py = top[i]
        rr = r.uniform(14, 34) * s
        c.circle(px + r.uniform(-14, 14) * s, py - rr * r.uniform(0.2, 0.8), rr, "#050807")
    return []


# ------------------------------------------------------------------------------------------- Liverpool, 1836 to 1840s

@prop
def confluence(c, L, x, y, s=1.0, col="#0c1722", glint="#9fb4c4", moon_x=None, seed=5, side=1, **k):
    """A river winding toward the viewer from the horizon (y), with a second river joining it from one side in the
    middle distance (side=1 from the right, -1 from the left)."""
    r = np.random.default_rng(seed)

    def band(pts):
        left = [(cx - hw, cy) for cx, cy, hw in pts]
        right = [(cx + hw, cy) for cx, cy, hw in reversed(pts)]
        c.poly(left + right, col, smooth=True)
        return pts

    main = band([(x - 70 * s, y + 2, 7 * s), (x + 30 * s, y + 50 * s, 22 * s), (x - 40 * s, y + 140 * s, 48 * s),
                 (x + 50 * s, y + 290 * s, 92 * s), (x - 30 * s, y + 520 * s, 160 * s), (x + 40 * s, y + 900 * s, 260 * s)])
    band([(x + side * 430 * s, y + 30 * s, 8 * s), (x + side * 320 * s, y + 90 * s, 20 * s),
          (x + side * 180 * s, y + 160 * s, 34 * s), (x + side * 40 * s, y + 220 * s, 56 * s), (x - side * 10 * s, y + 250 * s, 60 * s)])

    def at(yy):                                           # the main channel's centre and half-width at a height
        for (x0, y0, h0), (x1, y1, h1) in zip(main, main[1:]):
            if y0 <= yy <= y1:
                f = (yy - y0) / max(1e-6, y1 - y0)
                return x0 + (x1 - x0) * f, h0 + (h1 - h0) * f
        return main[-1][0], main[-1][2]

    for j in range(80):                                   # ripples
        f = r.uniform(0.02, 1.0)
        yy = y + 20 * s + 860 * s * f ** 1.3
        cx, hw = at(yy)
        px = cx + r.uniform(-0.75, 0.75) * hw
        ln = (8 + 60 * f) * s
        c.line([(px - ln / 2, yy), (px + ln / 2, yy)], glint, 1.2 + 1.4 * f, 0.10 + 0.12 * f)
    if moon_x is not None:
        for j in range(36):
            yy = y + 30 * s + j * 24 * s
            cx, hw = at(yy)
            if abs(moon_x - cx) > hw:
                continue
            ln = min(hw, (10 + j * 3.0) * s) * r.uniform(0.6, 1.2)
            mx = moon_x + r.uniform(-6, 6) * s
            c.line([(mx - ln / 2, yy), (mx + ln / 2, yy)], glint, 2.0, max(0.06, 0.5 - j * 0.012))
    return []


@prop
def moonpath(c, L, x, y, s=1.0, n=34, glint="#b8c8d4", w=120, **k):
    """The moon's reflection on open water: a column of short bright ripples from y (the horizon) down."""
    r = np.random.default_rng(int(k.get("seed", 9)))
    for j in range(n):
        yy = y + 6 * s + j * (14 + j * 0.6) * s
        ln = (w * 0.15 + w * j / n) * s * r.uniform(0.5, 1.2)
        mx = x + r.uniform(-0.35, 0.35) * w * s * (j / n)
        c.line([(mx - ln / 2, yy), (mx + ln / 2, yy)], glint, 1.6 + 2.2 * j / n, max(0.08, 0.6 - j * 0.014))
    return []


@prop
def stakes(c, L, x, y, s=1.0, rows=4, n=9, seed=1, **k):
    """A town being laid out: rows of survey stakes with small white flags, nearer rows bigger."""
    r = np.random.default_rng(seed)
    for row in range(rows):
        depth = (row + 1) / rows
        yy = y + (10 + 170 * depth ** 1.7) * s
        h = (16 + 74 * depth ** 1.5) * s
        span = (340 + 360 * depth) * s
        for j in range(n):
            sx = x - span + 2 * span * (j + 0.5 + r.uniform(-0.22, 0.22)) / n
            c.line([(sx, yy), (sx, yy - h)], "#3a3022", max(1.4, 4.2 * depth * s))
            c.poly([(sx, yy - h), (sx + h * 0.34, yy - h * 0.9), (sx, yy - h * 0.8)], "#d8d2c4", 0.88)


@prop
def timberframe(c, L, x, y, s=1.0, done=0.3, scaffold=True, ladder=True, lumber=True, col="#0d0a07", **k):
    """An unfinished two-storey timber-frame building seen from the gable end: studs, girts, rafters."""
    w2, hh, rf = 160 * s, 250 * s, 130 * s
    x0, x1 = x - w2, x + w2
    bm = 7 * s
    if done > 0:
        c.rect(x0, y - hh * done, x1, y, "#16110c")
        for j in range(int(hh * done / (9 * s))):
            c.line([(x0, y - j * 9 * s), (x1, y - j * 9 * s)], "#0a0806", 1.2 * s, 0.8)
    for j in range(9):
        px = x0 + j * 2 * w2 / 8
        c.line([(px, y), (px, y - hh)], col, bm if j in (0, 8) else bm * 0.6)
    for yy in (y, y - hh * 0.5, y - hh):
        c.line([(x0 - 5 * s, yy), (x1 + 5 * s, yy)], col, bm)
    for sx, d in ((x0, 1), (x1, -1)):
        c.line([(sx, y - hh * 0.5 - 46 * s), (sx + d * 46 * s, y - hh * 0.5)], col, bm * 0.6)
        c.line([(sx, y - hh + 46 * s), (sx + d * 46 * s, y - hh)], col, bm * 0.6)
    c.line([(x0 - 14 * s, y - hh + 10 * s), (x, y - hh - rf), (x1 + 14 * s, y - hh + 10 * s)], col, bm)
    for j in (1, 2, 3):
        gx = j * w2 / 4
        top = rf * (1 - gx / w2)
        for sgn in (-1, 1):
            c.line([(x + sgn * gx, y - hh), (x + sgn * gx, y - hh - top)], col, bm * 0.5)
    c.line([(x, y - hh), (x, y - hh - rf)], col, bm * 0.7)
    c.line([(x - w2 * 0.5, y - hh - rf * 0.5), (x + w2 * 0.5, y - hh - rf * 0.5)], col, bm * 0.6)
    if scaffold:
        for px in (x0 - 50 * s, x0 - 14 * s):
            c.line([(px, y), (px, y - hh * 0.75)], col, 5 * s)
        c.line([(x0 - 60 * s, y - hh * 0.5), (x0 - 4 * s, y - hh * 0.5)], col, 8 * s)
    if ladder:
        a, b = (x1 + 70 * s, y), (x1 + 6 * s, y - hh * 0.9)
        for off in (-12, 12):
            c.line([(a[0] + off * s, a[1]), (b[0] + off * s, b[1])], col, 4 * s)
        for t in range(1, 10):
            f = t / 10
            px, py = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            c.line([(px - 12 * s, py), (px + 12 * s, py)], col, 3 * s)
    if lumber:
        for t in range(4):
            c.rect(x - 250 * s + t * 6 * s, y + (16 - t * 10) * s, x - 90 * s + t * 6 * s, y + (24 - t * 10) * s, "#1c150e")
    return []


@prop
def halfbuilt(c, L, x, y, s=1.0, col="#0c0a08", poles=True, ladder=True, lumber=True, **k):
    """A small building left unfinished, in silhouette: walls partly up with a ragged top and no roof."""
    w2 = 150 * s
    top = [(x - w2, y - 150 * s), (x - w2 * 0.38, y - 150 * s), (x - w2 * 0.38, y - 120 * s), (x + w2 * 0.18, y - 120 * s),
           (x + w2 * 0.18, y - 88 * s), (x + w2 * 0.6, y - 88 * s), (x + w2 * 0.6, y - 58 * s), (x + w2, y - 58 * s)]
    c.poly([(x - w2, y)] + top + [(x + w2, y)], col)
    if poles:
        for px, ph in ((x - w2 - 34 * s, 240), (x - w2 + 4 * s, 218), (x + w2 * 0.6, 170), (x + w2 + 22 * s, 150)):
            c.line([(px, y), (px, y - ph * s)], col, 5 * s)
        c.line([(x - w2 - 44 * s, y - 124 * s), (x - w2 + 14 * s, y - 124 * s)], col, 7 * s)
    if ladder:
        a, b = (x + w2 + 60 * s, y), (x + w2 * 0.7, y - 120 * s)
        for off in (-10, 10):
            c.line([(a[0] + off * s, a[1]), (b[0] + off * s, b[1])], col, 4 * s)
        for t in range(1, 8):
            f = t / 8
            px, py = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            c.line([(px - 10 * s, py), (px + 10 * s, py)], col, 3 * s)
    if lumber:
        for t in range(4):
            c.rect(x - 250 * s + t * 6 * s, y + (16 - t * 10) * s, x - 100 * s + t * 6 * s, y + (24 - t * 10) * s, "#1c150e")
    return []


@prop
def scow(c, L, x, y, s=1.0, polers=2, cargo="frame", **k):
    """A flat-bottomed river scow carrying an unfinished building, poled by two small figures."""
    c.rect(x - 290 * s, y + 6 * s, x + 290 * s, y + 46 * s, "#000000", 0.35, blur=8)            # its shadow on the water
    if cargo == "halfbuilt":
        halfbuilt(c, L, x + 10 * s, y - 40 * s, s * 0.85, poles=False, ladder=False, lumber=False)
    else:
        timberframe(c, L, x + 10 * s, y - 40 * s, s * 0.6, done=0.6, scaffold=False, ladder=False, lumber=False)
    c.poly([(x - 310 * s, y - 42 * s), (x + 310 * s, y - 42 * s), (x + 276 * s, y + 6 * s), (x - 276 * s, y + 6 * s)],
           "#0a0806")
    c.line([(x - 310 * s, y - 42 * s), (x + 310 * s, y - 42 * s)], "#2e2418", 3 * s, 0.8)
    for j, px in enumerate((-250, 252)[:polers]):
        fx = x + px * s
        art.figure(c, fx, y - 42 * s, 104 * s, color="#040506", hat="brim", arms=((30, 50), (30, 50)), lean=0.15)
        d = -1 if j == 0 else 1
        c.line([(fx + d * 14 * s, y - 140 * s), (fx + d * 74 * s, y + 52 * s)], "#0a0806", 4 * s)
    return []


@prop
def riders(c, L, x, y, s=1.0, n=2, spread=150, flip=False, color="#050607", **k):
    """Small horseback riders, facing right (flip=True: facing left)."""
    for j in range(n):
        hx = x + (j - (n - 1) / 2) * spread * s
        if flip:
            c.c.save()
            c.c.translate(2 * hx, 0)
            c.c.scale(-1, 1)
        K2.horse(c, hx, y + j * 6 * s, s, color=color, rider=True)
        if flip:
            c.c.restore()
    return []


@prop
def wagon(c, L, x, y, s=1.0, team=True, flip=False, **k):
    """A covered wagon and its two-horse team, facing right (flip=True: facing left)."""
    if flip:
        c.c.save()
        c.c.translate(2 * x, 0)
        c.c.scale(-1, 1)
    K2.wagon(c, x, y, s)
    if team:
        K2.horse(c, x + 150 * s, y, s * 0.95)
        K2.horse(c, x + 172 * s, y + 5 * s, s * 0.95)
    if flip:
        c.c.restore()
    return []


@prop
def loghouse(c, L, x, y, s=1.0, lit=True, storeys=1, **k):
    """A long log building with a shake roof and a chimney at one end (storeys=2: two storeys high)."""
    w2, h = 240 * s, (150 if storeys < 2 else 270) * s
    c.rect(x - w2, y - h, x + w2, y, "#0b0908")
    for j in range(int(h / (16.5 * s))):
        yy = y - (8 + j * 16.5) * s
        c.line([(x - w2 - 10 * s, yy), (x + w2 + 10 * s, yy)], "#2a1c12", 3 * s, 0.85)
    c.poly([(x - w2 - 26 * s, y - h + 6 * s), (x - w2 + 70 * s, y - h - 104 * s), (x + w2 - 70 * s, y - h - 104 * s),
            (x + w2 + 26 * s, y - h + 6 * s)], "#080706")
    c.rect(x + w2 - 50 * s, y - h - 150 * s, x + w2 - 16 * s, y - h - 40 * s, "#0a0807")
    c.rect(x - 24 * s, y - 92 * s, x + 24 * s, y, "#050404")
    out = []
    for i, wx in enumerate((-160, 110)):
        on = lit and i == 0
        K3._win(c, L, x + wx * s, y - 104 * s, x + (wx + 40) * s, y - 56 * s, on)
        if on:
            out.append((x + (wx + 20) * s, y - 80 * s, (1.0, 0.8, 0.5), 60 * s, True, 0.4))
    if storeys >= 2:
        for wx in (-160, -40, 110):
            K3._win(c, L, x + wx * s, y - 224 * s, x + (wx + 40) * s, y - 180 * s, False)
    return out


@prop
def depot2(c, L, x, y, s=1.0, lit=True, **k):
    """A two-storey board-and-batten railroad depot of the 1850s: deep eaves between the floors, a hipped roof."""
    c.rect(x - 330 * s, y - 14 * s, x + 330 * s, y, "#16130f")                    # platform
    c.rect(x - 220 * s, y - 140 * s, x + 220 * s, y - 14 * s, "#141210")             # ground floor
    c.rect(x - 190 * s, y - 266 * s, x + 190 * s, y - 150 * s, "#131110")            # upper floor
    for x0, x1, y0, y1 in ((x - 220 * s, x + 220 * s, y - 140 * s, y - 14 * s), (x - 190 * s, x + 190 * s, y - 266 * s, y - 150 * s)):
        for j in range(int((x1 - x0) / (14 * s))):
            bx = x0 + j * 14 * s
            c.line([(bx, y0), (bx, y1)], "#0a0908", 1.4 * s, 0.9)
    c.poly([(x - 280 * s, y - 136 * s), (x + 280 * s, y - 136 * s), (x + 240 * s, y - 158 * s), (x - 240 * s, y - 158 * s)],
           "#0a0a0b")                                                                 # the eaves over the platform
    for bx in (-200, -100, 0, 100, 200):
        c.line([(x + bx * s, y - 136 * s), (x + (bx + (12 if bx > 0 else -12)) * s, y - 116 * s)], "#0a0a0b", 4 * s)
    c.poly([(x - 214 * s, y - 262 * s), (x + 214 * s, y - 262 * s), (x + 120 * s, y - 330 * s), (x - 120 * s, y - 330 * s)],
           "#0a0a0b")                                                                 # hipped roof
    c.rect(x + 80 * s, y - 370 * s, x + 104 * s, y - 310 * s, "#0b0b0c")              # chimney
    c.rect(x - 30 * s, y - 110 * s, x + 30 * s, y - 14 * s, "#070606")
    for wx in (-170, -110, 80, 140):
        c.rect(x + wx * s, y - 112 * s, x + (wx + 32) * s, y - 56 * s, "#070606")
    for wx in (-150, -60, 30, 120):
        c.rect(x + wx * s, y - 246 * s, x + (wx + 30) * s, y - 190 * s, "#070606")
    out = []
    if lit:
        L.rect(x + 80 * s, y - 112 * s, x + 112 * s, y - 56 * s, WARM, 0.55)
        L.rect(x - 60 * s, y - 246 * s, x - 30 * s, y - 190 * s, WARM, 0.4)
        out.append((x + 96 * s, y - 84 * s, (1.0, 0.8, 0.5), 50 * s, True, 0.4))
    return out


def _flame(c, fx, base, fw, fh):
    c.poly([(fx - fw, base), (fx + fw, base), (fx + fw * 0.3, base - fh * 0.6), (fx, base - fh),
            (fx - fw * 0.4, base - fh * 0.55)], "#e0702a", 0.85, smooth=True)
    c.poly([(fx - fw * 0.5, base), (fx + fw * 0.5, base), (fx + fw * 0.1, base - fh * 0.55),
            (fx - fw * 0.2, base - fh * 0.4)], "#ffd27a", 0.8, smooth=True)


@prop
def townfire(c, L, x, y, s=1.0, n=4, seed=7, **k):
    """A few small, empty frame and log buildings burning at night: no one is shown."""
    r = np.random.default_rng(seed)
    out = []
    for j in range(40):                                   # smoke drifting up and away to the right
        sx = x + r.uniform(-320, 260) * s + j * 9 * s
        c.circle(sx, y - (240 + j * 21) * s, r.uniform(34, 80) * s, "#1e1916", 0.16)
    xs = [x + (j - (n - 1) / 2) * 240 * s + r.uniform(-24, 24) * s for j in range(n)]
    for j, bx in enumerate(xs):
        bw, bh = r.uniform(150, 210) * s, r.uniform(110, 165) * s
        c.rect(bx - bw / 2, y - bh, bx + bw / 2, y, "#120b07")
        if j % 2:                                         # log walls
            for t in range(int(bh / (16 * s))):
                c.line([(bx - bw / 2, y - (8 + t * 16) * s), (bx + bw / 2, y - (8 + t * 16) * s)], "#2a160c", 2 * s, 0.8)
        c.poly([(bx - bw / 2 - 10 * s, y - bh), (bx - bw * 0.12, y - bh - 76 * s), (bx + bw * 0.02, y - bh - 52 * s),
                (bx + bw * 0.16, y - bh - 64 * s), (bx + bw / 2 + 10 * s, y - bh)], "#0a0705")
        for wx in (-0.32, 0.14):
            wx0 = bx + wx * bw
            c.rect(wx0, y - bh * 0.72, wx0 + 28 * s, y - bh * 0.4, "#2a0e04")
            L.rect(wx0, y - bh * 0.72, wx0 + 28 * s, y - bh * 0.4, "#ff7a22", 0.9)
        for f in range(7):
            _flame(c, bx + r.uniform(-0.46, 0.46) * bw, y - bh - r.uniform(-10, 40) * s, r.uniform(16, 30) * s,
                   r.uniform(70, 170) * s)
        out.append((bx, y - bh - 30 * s, (1.0, 0.45, 0.12), 240 * s, True, 0.8))
    for j in range(70):
        c.circle(x + r.uniform(-460, 460) * s, y - r.uniform(160, 640) * s, r.uniform(1.2, 3.2) * s, "#ffb050",
                 r.uniform(0.35, 0.9))
    return out
