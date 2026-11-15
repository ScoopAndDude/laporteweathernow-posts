"""Props for the Lake Station short (the murder of George Wolf, 1888), added Nov. 15, 2026. They register in
story_kit3.PROPS like every prop, so a storyboard names them in "props": [{"p": "trackhouse", ...}].

    trackhouse  a small gable-front farmhouse of the 1870s-80s with a lean-to, a stoop and a front door.
                door="shut" | "open" (an open door shows a dark doorway with glow=0..1 of lamplight inside),
                lit=0..1 lights the windows, flip=True puts the lean-to on the left
    rocker      a wooden rocking chair, side on, empty
    boxstove    a cast-iron box stove on legs with its stovepipe; glow=0..1 the fire at the draft
    cane        a plain walking stick leaning against something (lean= px the top leans right)
    lamptable   a small table with a kerosene lamp, lit
    freightloco an 1880s 4-4-0 freight locomotive with a diamond stack and a big oil headlamp throwing a beam
                (x is the front of the pilot; flip=True faces it left; beam=0..1; smoke)
    boxcars     a string of wooden boxcars with roof walks and brake wheels (n, x = the string's middle)
    lanternman  a small railroad man holding up a lit lantern (raise_=False holds it low)
    poles       telegraph poles along the track, receding from (x, y) to (x2, y - rise), wires sagging
    switchlamp  a switch stand with its lamp lit (color="red" | "green")

People are small anonymous silhouettes. Nothing shows a body, a wound, a weapon or a real person's likeness.
The 1888 paper says where the house stood (half a mile west of Lake Station, about 15 rods north of the Michigan
Central) but not what it looked like, so the house is drawn generic.
"""
import math

import numpy as np

import story_kit3 as K3
import story_kit10 as K10
from story_kit import WARM
from core import smooth_path, paint

prop = K3.prop
IRON = "#121212"
WOOD = "#24160e"
WOOD_D = "#170d08"
BRASS = "#8a7038"


@prop
def trackhouse(c, L, x, y, s=1.0, door="shut", lit=0.5, glow=0.4, flip=False, seed=2, **k):
    """A small gable-front farmhouse with a lean-to, a stoop and a front door (see the top of this file)."""
    d = -1 if flip else 1
    r = np.random.default_rng(seed)
    out = []
    wall = "#0d0b09"
    hw, hh = 120 * s, 210 * s                                                     # the main block, gable end on
    x0, x1 = x - hw, x + hw
    lx0, lx1 = (x1, x1 + 130 * s) if d > 0 else (x0 - 130 * s, x0)               # the lean-to
    c.rect(lx0, y - 120 * s, lx1, y, "#0b0908")
    ex = x1 if d > 0 else x0                                                      # the lean-to's sloping roof
    fx = lx1 + 10 * s if d > 0 else lx0 - 10 * s
    c.poly([(ex, y - 168 * s), (fx, y - 112 * s), (fx, y - 104 * s), (ex, y - 158 * s)], "#060606")
    c.rect(x0, y - hh, x1, y, wall)
    for j in range(int(210 / 10)):                                                # clapboards
        c.line([(x0, y - j * 10 * s), (x1, y - j * 10 * s)], "#15110d", 1.0, 0.7)
    peak = y - hh - 120 * s                                                       # the front gable
    c.poly([(x0 - 14 * s, y - hh + 6 * s), (x, peak - 8 * s), (x1 + 14 * s, y - hh + 6 * s)], "#060606")
    c.poly([(x0 + 6 * s, y - hh + 2 * s), (x, peak + 10 * s), (x1 - 6 * s, y - hh + 2 * s)], wall)
    cx = x + 60 * s * d                                                           # a brick chimney at the back
    c.rect(cx - 13 * s, peak - 10 * s, cx + 13 * s, peak + 60 * s, "#1a1210")
    c.rect(cx - 16 * s, peak - 16 * s, cx + 16 * s, peak - 8 * s, "#140e0c")
    on = r.uniform() < lit                                                        # the attic window in the gable
    K3._win(c, L, x - 18 * s, y - hh - 76 * s, x + 18 * s, y - hh - 24 * s, on, k=0.45)
    if on:
        out.append((x, y - hh - 50 * s, (1.0, 0.74, 0.42), 40 * s, True, 0.25))
    dx = x - 52 * s * d                                                           # the front door, off-centre
    wx = x + 56 * s * d                                                           # and one window beside it
    on = r.uniform() < lit
    K3._win(c, L, wx - 24 * s, y - 176 * s, wx + 24 * s, y - 84 * s, on, k=0.5)
    c.line([(wx - 24 * s, y - 130 * s), (wx + 24 * s, y - 130 * s)], "#0a0806", 3 * s)
    c.line([(wx, y - 176 * s), (wx, y - 84 * s)], "#0a0806", 2 * s)
    c.rect(wx - 30 * s, y - 88 * s, wx + 30 * s, y - 80 * s, "#16120e")
    if on:
        out.append((wx, y - 130 * s, (1.0, 0.74, 0.42), 60 * s, True, 0.3))
    c.rect(dx - 30 * s, y - 166 * s, dx + 30 * s, y - 20 * s, "#16120e")          # the door frame
    if door == "open":
        c.rect(dx - 24 * s, y - 160 * s, dx + 24 * s, y - 20 * s, "#030202")
        if glow > 0:                                                              # lamplight deep inside
            L.rect(dx - 24 * s, y - 160 * s, dx + 24 * s, y - 20 * s, WARM, 0.22 * glow)
            c.rect(dx - 8 * s, y - 120 * s, dx + 20 * s, y - 40 * s, "#3a2a18", 0.35 * glow, blur=6 * s)
            out.append((dx + 6 * s, y - 90 * s, (1.0, 0.7, 0.36), 70 * s, True, 0.22 * glow))
        c.poly([(dx + 24 * s * d, y - 160 * s), (dx + 46 * s * d, y - 168 * s), (dx + 46 * s * d, y - 14 * s),
                (dx + 24 * s * d, y - 20 * s)], "#0a0705")                        # the door, swung open
    else:
        c.rect(dx - 24 * s, y - 160 * s, dx + 24 * s, y - 20 * s, "#090706")
        c.circle(dx + 16 * s * d, y - 92 * s, 3 * s, BRASS, 0.7)
    for j in range(2):                                                            # the stoop and its steps
        c.rect(dx - (44 - j * 8) * s, y - (20 - j * 10) * s, dx + (44 - j * 8) * s, y - (10 - j * 10) * s, "#1a1612")
    return out


@prop
def rocker(c, L, x, y, s=1.0, color="#0e0906", **k):
    """A wooden rocking chair, side on, empty."""
    run = [(x - 120 * s, y - 18 * s), (x - 60 * s, y - 2 * s), (x, y), (x + 60 * s, y - 2 * s), (x + 110 * s, y - 20 * s)]
    c.line(run, color, 8 * s)                                                     # the curved runner
    for lx in (-70, 60):                                                          # legs
        c.line([(x + lx * s, y - 4 * s), (x + (lx + 4) * s, y - 150 * s)], color, 8 * s)
    c.line([(x - 80 * s, y - 150 * s), (x + 74 * s, y - 150 * s)], color, 12 * s)  # the seat
    c.line([(x - 80 * s, y - 150 * s), (x - 104 * s, y - 360 * s)], color, 9 * s)   # the back posts, raked
    c.line([(x - 60 * s, y - 150 * s), (x - 84 * s, y - 356 * s)], color, 6 * s)
    for j in range(4):                                                            # spindles
        f = (j + 1) / 5
        c.line([(x - 80 * s + 20 * s * f, y - 152 * s), (x - 104 * s + 20 * s * f, y - 350 * s)], color, 3 * s)
    c.line([(x - 108 * s, y - 360 * s), (x - 78 * s, y - 356 * s)], color, 12 * s)  # top rail
    c.line([(x - 92 * s, y - 250 * s), (x + 58 * s, y - 236 * s), (x + 70 * s, y - 226 * s)], color, 7 * s)  # arm
    c.line([(x + 62 * s, y - 150 * s), (x + 60 * s, y - 230 * s)], color, 6 * s)
    return []


@prop
def boxstove(c, L, x, y, s=1.0, glow=0.6, **k):
    """A cast-iron box stove on legs with its stovepipe going up."""
    out = []
    for lx in (-80, 66):
        c.rect(x + lx * s, y - 40 * s, x + (lx + 14) * s, y, IRON)
    c.rect(x - 96 * s, y - 150 * s, x + 96 * s, y - 36 * s, IRON, r=8 * s)
    c.rect(x - 104 * s, y - 160 * s, x + 104 * s, y - 146 * s, "#1c1c1c")
    c.line([(x - 90 * s, y - 120 * s), (x + 90 * s, y - 120 * s)], "#202020", 2 * s)
    c.rect(x - 40 * s, y - 110 * s, x + 40 * s, y - 56 * s, "#0a0a0a")              # the draft door
    if glow > 0:
        for j in range(5):
            c.rect(x - 32 * s + j * 16 * s, y - 100 * s, x - 26 * s + j * 16 * s, y - 66 * s, "#ff8a3a", 0.5 * glow)
        L.rect(x - 34 * s, y - 102 * s, x + 34 * s, y - 64 * s, "#ff7a2a", 0.4 * glow)
        out.append((x, y - 84 * s, (1.0, 0.5, 0.2), 120 * s, True, 0.4 * glow))
    c.rect(x + 50 * s, y - 520 * s, x + 74 * s, y - 158 * s, "#161616")            # the stovepipe
    c.rect(x + 46 * s, y - 330 * s, x + 78 * s, y - 322 * s, "#1e1e1e")
    return out


@prop
def cane(c, L, x, y, s=1.0, lean=40, **k):
    """A plain walking stick leaning against something."""
    c.line([(x, y), (x + lean * s, y - 240 * s)], "#2a1c12", 6 * s)
    c.line([(x + lean * s, y - 240 * s), (x + (lean + 26) * s, y - 248 * s), (x + (lean + 34) * s, y - 238 * s)],
           "#2a1c12", 6 * s)
    return []


@prop
def lamptable(c, L, x, y, s=1.0, lit=True, **k):
    """A small table with a kerosene lamp."""
    c.rect(x - 90 * s, y - 190 * s, x + 90 * s, y - 176 * s, "#2a1a10")
    for lx in (-80, 70):
        c.rect(x + lx * s, y - 176 * s, x + (lx + 10) * s, y, "#1a100a")
    c.rect(x - 74 * s, y - 70 * s, x + 74 * s, y - 62 * s, "#1a100a")
    out = []
    lx = x
    c.ellipse(lx, y - 196 * s, 30 * s, 8 * s, BRASS)
    c.poly([(lx - 24 * s, y - 196 * s), (lx + 24 * s, y - 196 * s), (lx + 18 * s, y - 236 * s), (lx - 18 * s, y - 236 * s)],
           "#5a4a3a", 0.8)
    c.rect(lx - 7 * s, y - 246 * s, lx + 7 * s, y - 236 * s, BRASS)
    c.c.drawPath(smooth_path([(lx - 10 * s, y - 246 * s), (lx - 17 * s, y - 280 * s), (lx - 10 * s, y - 314 * s),
                              (lx + 10 * s, y - 314 * s), (lx + 17 * s, y - 280 * s), (lx + 10 * s, y - 246 * s)], True),
                 paint("#e8dcc0", 0.35))
    if lit:
        c.ellipse(lx, y - 276 * s, 5 * s, 12 * s, "#ffd890", 0.95)
        out.append((lx, y - 278 * s, (1.0, 0.72, 0.38), 240 * s, True, 0.65))
    return out


@prop
def freightloco(c, L, x, y, s=1.0, flip=False, beam=0.8, smoke=True, **k):
    """An 1880s 4-4-0 freight locomotive with a diamond stack and a big oil headlamp (see the top of this file)."""
    d = -1 if flip else 1
    out = []
    col = "#0c0d0e"

    def X(v):
        return x - d * v * s

    def P(pts):
        return [(X(a), y - b * s) for a, b in pts]

    c.poly(P([(0, 6), (46, 6), (46, 78), (30, 78)]), col)                         # the pilot (cowcatcher)
    for j in range(5):
        c.line([(X(4 + j * 9), y - 8 * s), (X(40), y - 70 * s)], "#1e2022", 2 * s)
    c.rect(min(X(46), X(400)), y - 96 * s, max(X(46), X(400)), y - 78 * s, col)   # the frame
    c.rect(min(X(56), X(130)), y - 230 * s, max(X(56), X(130)), y - 96 * s, col, r=6 * s)  # smokebox
    c.rect(min(X(110), X(330)), y - 214 * s, max(X(110), X(330)), y - 112 * s, "#101214", r=40 * s)  # boiler
    for bx in (170, 250):                                                         # boiler bands
        c.line([(X(bx), y - 212 * s), (X(bx), y - 114 * s)], "#2a2c2e", 2 * s)
    c.poly(P([(78, 230), (108, 230), (122, 330), (64, 330)]), col)                # the diamond stack
    c.poly(P([(58, 330), (128, 330), (112, 352), (74, 352)]), col)
    c.rect(min(X(196), X(230)), y - 250 * s, max(X(196), X(230)), y - 210 * s, col, r=14 * s)  # sand dome
    c.rect(min(X(262), X(292)), y - 246 * s, max(X(262), X(292)), y - 210 * s, col, r=14 * s)  # steam dome
    c.rect(min(X(330), X(470)), y - 300 * s, max(X(330), X(470)), y - 96 * s, "#0e0f10")   # the cab
    c.poly(P([(320, 300), (480, 300), (474, 316), (326, 316)]), col)
    wy0, wy1 = y - 280 * s, y - 214 * s                                           # cab window, firelit
    c.rect(min(X(352), X(400)), wy0, max(X(352), X(400)), wy1, "#070505")
    L.rect(min(X(352), X(400)), wy0, max(X(352), X(400)), wy1, "#ff7a30", 0.35)
    out.append((X(376), (wy0 + wy1) / 2, (1.0, 0.5, 0.2), 60 * s, True, 0.3))
    for wx in (210, 310):                                                         # two big drivers
        c.circle(X(wx), y - 50 * s, 50 * s, "#141516")
        c.circle(X(wx), y - 50 * s, 40 * s, "#0a0b0c")
        for t in range(10):
            a = 2 * math.pi * t / 10
            c.line([(X(wx), y - 50 * s), (X(wx) + 40 * s * math.cos(a), y - 50 * s + 40 * s * math.sin(a))],
                   "#1e2022", 2.5 * s)
    c.line([(X(210), y - 50 * s), (X(310), y - 50 * s)], "#2a2c2e", 6 * s)        # side rod
    for wx in (80, 135):                                                          # leading truck
        c.circle(X(wx), y - 24 * s, 24 * s, "#141516")
    c.rect(min(X(486), X(700)), y - 190 * s, max(X(486), X(700)), y - 70 * s, "#0e0f10")   # the tender
    c.poly(P([(490, 190), (696, 190), (680, 214), (520, 220)]), "#060606")        # coal heaped on it
    for wx in (530, 580, 610, 660):
        c.circle(X(wx), y - 26 * s, 26 * s, "#141516")
    hx, hy = X(70), y - 262 * s                                                   # the big box headlamp
    c.rect(hx - 34 * s, hy - 30 * s, hx + 34 * s, hy + 30 * s, "#141414")
    c.circle(X(52), hy, 22 * s, "#ffe8b0", 0.95)
    L.circle(X(52), hy, 30 * s, "#ffd890", 0.8)
    out.append((X(52), hy, (1.0, 0.86, 0.6), 110 * s, False, 0.9))
    if beam > 0:                                                                  # its beam, thrown ahead
        ex = X(-900)
        c.poly([(X(40), hy - 18 * s), (ex, hy - 160 * s), (ex, hy + 190 * s), (X(40), hy + 20 * s)],
               "#fff0c8", 0.07 * beam, blur=26 * s)
        L.poly([(X(40), hy - 18 * s), (ex, hy - 130 * s), (ex, hy + 160 * s), (X(40), hy + 18 * s)],
               "#ffe0a0", 0.16 * beam, blur=34 * s)
    if smoke:
        for j in range(6):
            c.ellipse(X(90 + j * 70), y - (380 + j * 30) * s, (40 + j * 18) * s, (22 + j * 8) * s, "#4a4a4c",
                      0.10 - j * 0.012, blur=14 * s)
    return out


@prop
def boxcars(c, L, x, y, s=1.0, n=4, seed=3, **k):
    """A string of wooden boxcars with roof walks and brake wheels; x is the middle of the string."""
    r = np.random.default_rng(seed)
    cw, gap = 330 * s, 18 * s
    tot = n * cw + (n - 1) * gap
    for i in range(n):
        x0 = x - tot / 2 + i * (cw + gap)
        x1 = x0 + cw
        col = ("#1e0e0a", "#1a0c08", "#22100b")[int(r.integers(0, 3))]
        c.rect(x0, y - 250 * s, x1, y - 70 * s, col)
        for j in range(int(cw / (12 * s))):                                       # vertical boards
            c.line([(x0 + j * 12 * s, y - 248 * s), (x0 + j * 12 * s, y - 72 * s)], "#120806", 1.0, 0.6)
        c.line([(x0, y - 250 * s), (x1, y - 70 * s)], "#120806", 3 * s, 0.6)       # the X bracing
        c.line([(x0, y - 70 * s), (x1, y - 250 * s)], "#120806", 3 * s, 0.6)
        mx = (x0 + x1) / 2                                                        # the sliding door
        c.rect(mx - 50 * s, y - 236 * s, mx + 50 * s, y - 76 * s, "#140a07")
        c.line([(mx - 60 * s, y - 238 * s), (mx + 60 * s, y - 238 * s)], "#0a0a0a", 3 * s)
        c.rect(x0 - 6 * s, y - 262 * s, x1 + 6 * s, y - 250 * s, "#0e0806")       # roof and roof walk
        c.rect(x0 + 10 * s, y - 268 * s, x1 - 10 * s, y - 262 * s, "#1a120c")
        bx = x1 - 20 * s                                                          # brake wheel on its staff
        c.line([(bx, y - 262 * s), (bx, y - 300 * s)], "#0a0a0a", 3 * s)
        c.ellipse(bx, y - 300 * s, 16 * s, 4 * s, "#0a0a0a")
        c.line([(x0 + 4 * s, y - 120 * s), (x0 + 4 * s, y - 240 * s)], "#0a0a0a", 2 * s)   # ladder
        for j in range(5):
            c.line([(x0 - 4 * s, y - 130 * s - j * 22 * s), (x0 + 12 * s, y - 130 * s - j * 22 * s)], "#0a0a0a", 2 * s)
        for tx in (x0 + 60 * s, x1 - 60 * s):                                     # trucks
            c.rect(tx - 44 * s, y - 64 * s, tx + 44 * s, y - 42 * s, "#0a0a0a")
            for wx in (-24, 24):
                c.circle(tx + wx * s, y - 22 * s, 20 * s, "#121314")
        c.rect(x1, y - 98 * s, x1 + gap, y - 90 * s, "#0a0a0a")                    # link-and-pin coupler
    return []


@prop
def lanternman(c, L, x, y, s=1.0, raise_=True, lit=True, lean=0.0, color="#030304", **k):
    """A small railroad man holding up a lit lantern."""
    K10._man(c, x, y, 150 * s, lean, 0, color)
    u = s
    hx, hy = (x + 24 * u, y - 150 * u) if raise_ else (x + 22 * u, y - 70 * u)
    c.line([(x + 10 * u, y - 112 * u), (hx, hy + 14 * u)], color, 6 * u)        # the arm
    c.line([(hx, hy + 14 * u), (hx, hy + 22 * u)], "#1a1a1a", 1.5 * u)
    c.rect(hx - 7 * u, hy + 22 * u, hx + 7 * u, hy + 44 * u, "#ffd890" if lit else "#2a2a2a", 0.9)
    c.rect(hx - 9 * u, hy + 18 * u, hx + 9 * u, hy + 22 * u, "#1a1a1a")
    c.rect(hx - 9 * u, hy + 44 * u, hx + 9 * u, hy + 48 * u, "#1a1a1a")
    if lit:
        L.circle(hx, hy + 33 * u, 14 * u, WARM, 0.7)
        return [(hx, hy + 33 * u, (1.0, 0.76, 0.42), 90 * u, True, 0.6)]
    return []


@prop
def poles(c, L, x, y, s=1.0, x2=1100, rise=60, n=6, h=300, color="#0a0a0a", **k):
    """Telegraph poles along the track, from (x, y) where they are tall to (x2, y - rise) where they are small,
    with their wires sagging between them."""
    tops = []
    for i in range(n):
        f = i / max(1, n - 1)
        z = 1.0 + f * 3.0                                                         # farther poles are smaller
        px = x + (x2 - x) * (1 - 1 / z) / (1 - 1 / 4.0)
        py = y - rise * (1 - 1 / z) / (1 - 1 / 4.0)
        ph = h * s / z
        c.line([(px, py), (px, py - ph)], color, max(2.0, 9 * s / z))
        c.line([(px - 30 * s / z, py - ph + 14 * s / z), (px + 30 * s / z, py - ph + 14 * s / z)], color,
               max(1.5, 5 * s / z))
        tops.append((px, py - ph + 14 * s / z, s / z))
    for (ax, ay, sa), (bx, by, sb) in zip(tops, tops[1:]):
        for off in (-22, 22):
            p0, p1 = (ax + off * sa, ay), (bx + off * sb, by)
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + 12 * sa)
            c.line([p0, mid, p1], "#202224", 1.2, 0.8)
    return []


@prop
def switchlamp(c, L, x, y, s=1.0, color="red", **k):
    """A railroad switch stand with its lamp lit (color="red" | "green")."""
    col = {"red": ((1.0, 0.25, 0.18), "#ff4a30"), "green": ((0.3, 1.0, 0.5), "#4aff7a")}[color]
    c.rect(x - 4 * s, y - 120 * s, x + 4 * s, y, "#0c0c0c")
    c.rect(x - 16 * s, y - 10 * s, x + 16 * s, y, "#0c0c0c")
    c.rect(x - 14 * s, y - 150 * s, x + 14 * s, y - 120 * s, "#1a1a1a")
    c.circle(x, y - 135 * s, 8 * s, col[1], 0.95)
    L.circle(x, y - 135 * s, 12 * s, col[1], 0.8)
    return [(x, y - 135 * s, col[0], 70 * s, True, 0.6)]
