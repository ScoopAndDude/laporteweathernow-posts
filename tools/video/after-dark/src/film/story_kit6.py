"""Props for the 1865 Lincoln funeral train short (story_kit6.py; added Nov. 14, 2026, for Westville).
They register themselves in story_kit3.PROPS, so any tab_* scene can use them:

    funeraltrain  an 1860s American-type steam locomotive (balloon stack, box headlamp, cowcatcher) with its tender and
                  n wooden coaches, all hung with black mourning swags trimmed in white. x = the cowcatcher's tip.
                  n=3 coaches   flip=True  facing left   lamp=True  headlamp lit   smoke=True   lit=0.4 coach windows
    arch          an arch over the track wound with evergreens and dotted with roses (no words on it)
                  w=440 (span)   h=470 (height)
    bonfire       a big log fire by the track at night, flames and sparks, flickering light
    mourners      a crowd of small anonymous figures, men bareheaded, women in long dresses, a few children
                  n=14   spread=360   seed=0   rows=2 (the back row smaller and paler)
                  flags=0.0  share holding up small white flags with a black fringe   torches=0.0  share holding torches
    depot         a small 1860s board-and-batten railroad depot with deep bracketed eaves and a platform
                  lit=True  a lamp in the window
    haze          morning mist lying on the fields just below the horizon, so dark figures read against it
                  (y = the horizon; depth=190 pixels; color="#6a5a60"; a=0.55)
    trackview     the track seen from between the rails, running away to the horizon (x = the vanishing point,
                  y = the horizon, w = half the gauge at the bottom of the frame, default 260). Something standing on
                  the track with its base at screen height yb is gauge(yb) = 2*w*(yb - y)/(1920 - y) pixels wide.
    locofront     the same 1860s locomotive seen head-on, draped in black (x = centre, y = base on the rail,
                  g = the gauge in pixels at that distance; lamp=True)   rear=True  the back of the last coach instead

Skies "morning" (a clear early-morning sky) and "overcast" (a grey morning sky), for daytime scenes in any tab_* kind.

People are small anonymous silhouettes only. Nothing shows a body, a coffin, a real person's likeness or a brand.
"""
import math

import numpy as np

import art
import story_kit3 as K3
from story_kit import WARM, hash2
from core import smooth_path, paint

prop = K3.prop
INK = "#07080a"
# a grey overcast morning (Lincoln's train reached Westville about 7:40 a.m. on May 1, 1865: full daylight, likely cloudy)
K3.SKIES["morning"] = [(0.0, "#2a4666"), (0.35, "#456684"), (0.55, "#7590a6"), (0.63, "#a6b4bf"), (1.0, "#56636e")]
K3.SKIES["overcast"] = [(0.0, "#3a4450"), (0.35, "#525c68"), (0.55, "#6c747e"), (0.63, "#858b93"), (1.0, "#565c64")]
TRIM = "#d8d4c8"


def _swags(c, x0, x1, y, n, depth, s, col="#000000", trim=TRIM):
    """A row of mourning swags hanging from y between x0 and x1, each with a pale trim line and a rosette."""
    wd = (x1 - x0) / n
    for j in range(n):
        a, b = x0 + j * wd, x0 + (j + 1) * wd
        pts = [(a, y)]
        for t in np.linspace(0, 1, 14):
            pts.append((a + (b - a) * t, y + depth * 4 * t * (1 - t)))
        pts.append((b, y))
        c.poly(pts, col, 0.95, smooth=False)
        c.line([(a + (b - a) * t, y + depth * 4 * t * (1 - t) + 1.5 * s) for t in np.linspace(0, 1, 14)], trim,
               1.3 * s, 0.32)
    for j in range(n + 1):
        rx = x0 + j * wd
        c.circle(rx, y + 2 * s, 5 * s, trim, 0.38)
        c.circle(rx, y + 2 * s, 2.5 * s, "#000000", 1.0)


def _wheel(c, x, y, r, s, spokes=10, col="#050506"):
    c.circle(x, y, r, col)
    c.circle(x, y, r * 0.78, "#15171a", 0.9)
    for j in range(spokes):
        a = j * math.tau / spokes
        c.line([(x, y), (x + math.cos(a) * r * 0.8, y + math.sin(a) * r * 0.8)], col, 3 * s)
    c.circle(x, y, r * 0.2, col)


@prop
def funeraltrain(c, L, x, y, s=1.0, n=3, flip=False, lamp=True, smoke=True, lit=0.4, drape=True, **k):
    """An 1865 funeral train: a black-draped 4-4-0 locomotive, its tender and n wooden coaches. x = cowcatcher tip.
    drape=False: the same train with no black swags or rosette (an ordinary 1850s-1860s train)."""
    d = -1 if flip else 1

    def X(v):                                    # v = distance back from the cowcatcher tip
        return x - d * v * s

    def R(a, b, top, bot, col, al=1.0, r=0):
        c.rect(min(X(a), X(b)), y - top * s, max(X(a), X(b)), y - bot * s, col, al, r=r * s)

    body = "#0d0f12"
    out = []
    # coaches first (behind the engine), back to front
    for j in range(n):
        a = 420 + j * 300
        b = a + 286
        R(a, b, 150, 30, "#1c1410")
        R(a + 30, b - 30, 168, 148, "#120d0b")                                  # clerestory
        c.c.drawPath(smooth_path([(X(a - 4), y - 150 * s), (X(a + 20), y - 164 * s), (X(b - 20), y - 164 * s),
                                  (X(b + 4), y - 150 * s)], True, k=0.1), paint("#0b0908"))
        R(a - 10, a, 120, 40, "#0b0908")
        R(b, b + 10, 120, 40, "#0b0908")                                        # end platforms
        for t in range(7):
            wa = a + 22 + t * 36
            on = hash2(t, j, 11) < lit
            R(wa, wa + 18, 126, 92, "#070606")
            if on:
                L.rect(min(X(wa), X(wa + 18)), y - 126 * s, max(X(wa), X(wa + 18)), y - 92 * s, WARM, 0.5)
        if drape:
            _swags(c, min(X(a + 6), X(b - 6)), max(X(a + 6), X(b - 6)), y - 146 * s, 4, 16 * s, s)
        if drape:
            _swags(c, min(X(a + 6), X(b - 6)), max(X(a + 6), X(b - 6)), y - 84 * s, 5, 12 * s, s)
        for wv in (a + 36, a + 74, b - 74, b - 36):
            _wheel(c, X(wv), y - 16 * s, 17 * s, s, spokes=6)
    # tender
    R(312, 404, 104, 38, body)
    R(316, 400, 112, 104, "#090a0c")
    if drape:
        _swags(c, min(X(318), X(398)), max(X(318), X(398)), y - 100 * s, 2, 14 * s, s)
    for wv in (330, 362, 386):
        _wheel(c, X(wv), y - 16 * s, 15 * s, s, spokes=6)
    # cab
    R(232, 300, 176, 52, body)
    c.poly([(X(222), y - 176 * s), (X(310), y - 176 * s), (X(306), y - 188 * s), (X(226), y - 188 * s)], "#050607")
    R(246, 284, 160, 124, "#070606")
    L.rect(min(X(246), X(284)), y - 160 * s, max(X(246), X(284)), y - 124 * s, WARM, 0.18)
    # boiler, domes, bell, running board
    R(56, 236, 118, 64, body, r=18)
    R(44, 70, 128, 58, "#0a0b0d", r=6)                                           # smokebox
    for cx, hh in ((128, 30), (186, 22)):
        c.c.drawPath(smooth_path([(X(cx - 18), y - 116 * s), (X(cx - 12), y - (116 + hh) * s), (X(cx + 12), y - (116 + hh) * s),
                                  (X(cx + 18), y - 116 * s)], True, k=0.25), paint("#0b0c0f"))
    c.circle(X(158), y - 128 * s, 8 * s, "#0b0c0f")
    R(40, 300, 66, 58, "#050607")
    if drape:
        _swags(c, min(X(76), X(226)), max(X(76), X(226)), y - 66 * s, 4, 14 * s, s)
    if drape:
        c.circle(X(146), y - 96 * s, 10 * s, TRIM, 0.55)                             # a rosette on the boiler side
        c.circle(X(146), y - 96 * s, 5 * s, "#000000")
    # balloon stack
    R(58, 74, 168, 124, "#08090b")
    c.poly([(X(42), y - 214 * s), (X(90), y - 214 * s), (X(74), y - 168 * s), (X(58), y - 168 * s)], "#08090b")
    c.rect(min(X(40), X(92)), y - 222 * s, max(X(40), X(92)), y - 212 * s, "#08090b")
    # headlamp
    R(24, 56, 162, 128, "#0a0b0d", r=3)
    c.rect(min(X(24), X(56)), y - 168 * s, max(X(24), X(56)), y - 162 * s, "#050607")
    # cylinders, pilot and wheels
    R(50, 96, 70, 36, "#0a0b0d", r=6)
    c.poly([(X(0), y - 4 * s), (X(46), y - 4 * s), (X(46), y - 46 * s)], "#0a0b0d")
    for t in range(5):
        c.line([(X(8 + t * 8), y - 4 * s), (X(46), y - (12 + t * 7) * s)], "#1a1c1f", 2 * s, 0.8)
    for wv in (72, 108):
        _wheel(c, X(wv), y - 15 * s, 15 * s, s, spokes=6)
    for wv in (166, 226):
        _wheel(c, X(wv), y - 33 * s, 33 * s, s)
    c.line([(X(166), y - 33 * s), (X(226), y - 33 * s)], "#1a1c1f", 5 * s)
    if smoke:
        for j in range(9):
            c.circle(X(66 + j * 52), y - (236 + j * 22) * s, (22 + j * 11) * s, "#262b30", 0.5 - j * 0.045)
    if lamp:
        out.append((X(14), y - 145 * s, (1.0, 0.9, 0.6), 70 * s, False, 0.7))
    return out


@prop
def arch(c, L, x, y, s=1.0, w=440, h=470, **k):
    """An arch over the track wound with evergreens and dotted with roses. No words on it."""
    r = np.random.default_rng(int(k.get("seed", 3)))
    hw = w / 2 * s
    top = y - h * s
    spring = top + hw                                     # where the half-circle meets the posts
    green = ("#0a1a10", "#0e2316", "#123020", "#081409")
    pts = []
    for t in np.linspace(0, 1, 70):                       # up one post, over the top, down the other
        if t < 0.3:
            pts.append((x - hw, y - (y - spring) * (t / 0.3)))
        elif t < 0.7:
            a = math.pi * (1 - (t - 0.3) / 0.4)
            pts.append((x + math.cos(a) * hw, spring - math.sin(a) * hw))
        else:
            pts.append((x + hw, spring + (y - spring) * ((t - 0.7) / 0.3)))
    for px, py in pts:                                    # the evergreen, in clumps
        for _ in range(5):
            c.circle(px + r.uniform(-16, 16) * s, py + r.uniform(-16, 16) * s, r.uniform(9, 16) * s,
                     green[int(r.integers(0, 4))])
    for px, py in pts[::2]:                               # roses
        if r.uniform() < 0.75:
            col = ("#b8506a", "#d0707e", "#9a3048", "#e8a0a8")[int(r.integers(0, 4))]
            c.circle(px + r.uniform(-13, 13) * s, py + r.uniform(-13, 13) * s, r.uniform(4, 7) * s, col, 0.95)
    for side in (-1, 1):                                  # a wreath on each post
        wx, wy = x + side * hw, y - (y - spring) * 0.55
        for j in range(18):
            a = j * math.tau / 18
            c.circle(wx + math.cos(a) * 30 * s, wy + math.sin(a) * 30 * s, 10 * s, green[j % 4])
        for j in range(6):
            a = j * math.tau / 6 + 0.3
            c.circle(wx + math.cos(a) * 30 * s, wy + math.sin(a) * 30 * s, 5 * s, "#c86070", 0.95)


@prop
def bonfire(c, L, x, y, s=1.0, **k):
    """A big log fire beside the track at night: flames, sparks and flickering light."""
    r = np.random.default_rng(int(k.get("seed", 5)))
    for a in (-0.35, 0.0, 0.35):
        c.line([(x - 70 * s * math.cos(a), y - 4 * s + 30 * s * math.sin(a)),
                (x + 70 * s * math.cos(a), y - 4 * s - 30 * s * math.sin(a))], "#1a0e08", 14 * s)
    for j in range(7):
        fx = x + (j - 3) * 16 * s
        fh = (90 - abs(j - 3) * 18) * s * r.uniform(0.8, 1.15)
        c.poly([(fx - 22 * s, y - 8 * s), (fx + 22 * s, y - 8 * s), (fx + 6 * s, y - fh * 0.6), (fx, y - fh),
                (fx - 8 * s, y - fh * 0.55)], "#e0702a", 0.85, smooth=True)
        c.poly([(fx - 11 * s, y - 8 * s), (fx + 11 * s, y - 8 * s), (fx + 2 * s, y - fh * 0.55), (fx - 4 * s, y - fh * 0.4)],
               "#ffd27a", 0.8, smooth=True)
    for j in range(16):
        c.circle(x + r.uniform(-60, 60) * s, y - r.uniform(110, 260) * s, r.uniform(1.5, 3.2) * s, "#ffb050",
                 r.uniform(0.4, 0.9))
    return [(x, y - 50 * s, (1.0, 0.55, 0.2), 230 * s, True, 0.85)]


@prop
def mourners(c, L, x, y, s=1.0, n=14, spread=360, seed=0, rows=2, flags=0.0, torches=0.0, **k):
    """A crowd of small anonymous figures: men bareheaded, women in long dresses, a few children.
    flags = share holding up small white flags with a black fringe; torches = share holding torches."""
    rng = np.random.default_rng(seed)
    out = []
    for row in range(rows - 1, -1, -1):                   # back row first
        m = n if row == 0 else max(3, int(n * 0.8))
        hh = 150 * s * (0.8 if row else 1.0)
        col = "#10141a" if row else "#030405"
        yy = y - row * 26 * s
        for j in range(m):
            fx = x - spread * s + 2 * spread * s * (j + rng.uniform(-0.3, 0.3) + (0.5 if row else 0)) / max(1, m)
            child = rng.uniform() < 0.2
            woman = (not child) and rng.uniform() < 0.45
            h = hh * (0.62 if child else rng.uniform(0.92, 1.05))
            hold = None
            u = rng.uniform()
            if u < flags:
                hold = "flag"
            elif u < flags + torches and not child:
                hold = "torch"
            arms = ((8, 4), (-8, -4))
            if hold:
                arms = ((8, 4), (150, 20)) if rng.uniform() < 0.5 else ((150, 20), (-8, -4))
            f = art.figure(c, fx, yy, h, color=col, child=child, dress=woman, bonnet=woman and rng.uniform() < 0.5,
                           arms=arms, legs=(3, -3), lean=0.0)
            if not hold:
                continue
            hands = f["hands"]
            hx, hy = max(hands, key=lambda p: -p[1])     # the raised hand
            if hold == "flag":
                c.line([(hx, hy + 6 * s), (hx, hy - 46 * s)], "#2a2622", 2 * s)
                fw, fh = 30 * s, 20 * s
                c.rect(hx, hy - 46 * s, hx + fw, hy - 46 * s + fh, "#e6e2d6", 0.95)
                for t in range(7):                        # the black mourning fringe
                    c.line([(hx + t * fw / 6, hy - 46 * s + fh), (hx + t * fw / 6, hy - 46 * s + fh + 6 * s)],
                           "#000000", 1.6 * s)
                c.rect(hx + fw - 3 * s, hy - 46 * s, hx + fw, hy - 46 * s + fh, "#000000")
            else:
                c.line([(hx, hy + 10 * s), (hx, hy - 34 * s)], "#2a1a10", 3 * s)
                c.poly([(hx - 7 * s, hy - 34 * s), (hx + 7 * s, hy - 34 * s), (hx + 2 * s, hy - 56 * s), (hx, hy - 64 * s)],
                       "#f08a30", 0.95, smooth=True)
                c.circle(hx, hy - 40 * s, 5 * s, "#ffd890", 0.9)
                out.append((hx, hy - 44 * s, (1.0, 0.6, 0.25), 70 * s, True, 0.55))
    return out


@prop
def depot(c, L, x, y, s=1.0, lit=True, **k):
    """A small 1860s board-and-batten railroad depot with deep bracketed eaves and a wooden platform."""
    c.rect(x - 330 * s, y - 14 * s, x + 330 * s, y, "#16130f")                    # platform
    c.rect(x - 230 * s, y - 150 * s, x + 230 * s, y - 14 * s, "#141210")
    for j in range(int(460 / 14)):
        bx = x - 230 * s + j * 14 * s
        c.line([(bx, y - 150 * s), (bx, y - 14 * s)], "#0a0908", 1.4 * s, 0.9)
    c.poly([(x - 290 * s, y - 150 * s), (x + 290 * s, y - 150 * s), (x + 200 * s, y - 228 * s), (x - 200 * s, y - 228 * s)],
           "#0a0a0b")
    for bx in (-210, -110, 0, 110, 210):
        c.line([(x + bx * s, y - 150 * s), (x + (bx + (12 if bx > 0 else -12)) * s, y - 128 * s)], "#0a0a0b", 4 * s)
    c.rect(x - 30 * s, y - 120 * s, x + 30 * s, y - 14 * s, "#070606")             # door
    for wx in (-160, -100, 80, 140):
        c.rect(x + wx * s, y - 120 * s, x + (wx + 34) * s, y - 60 * s, "#070606")
    if lit:
        L.rect(x + 80 * s, y - 120 * s, x + 114 * s, y - 60 * s, WARM, 0.55)
        return [(x + 97 * s, y - 90 * s, (1.0, 0.8, 0.5), 50 * s, True, 0.4)]


@prop
def trackview(c, L, x, y, s=1.0, w=260, **k):
    """The track seen from between the rails, running away to a vanishing point at (x, y)."""
    H = 1920
    bed = [(x - w * 2.2, H + 40), (x + w * 2.2, H + 40), (x + 6, y), (x - 6, y)]
    c.poly(bed, "#17181a", 0.9, smooth=False)
    z = 1.0
    while True:                                            # ties, closer together with distance
        f = 1.0 / z
        ty = y + (H + 40 - y) * f
        if ty - y < 3:
            break
        hw = w * 1.45 * f
        th = max(1.5, 26 * f)
        c.rect(x - hw, ty - th, x + hw, ty, "#0e0f10")
        z += 0.55
    for side in (-1, 1):
        c.poly([(x + side * (w - 9), H + 40), (x + side * (w + 9), H + 40), (x + side * 1.2, y), (x + side * 0.8, y)],
               "#4a4e50", 0.95, smooth=False)


def gauge(yb, y, w=260):
    return 2 * w * (yb - y) / (1920 - y)


@prop
def locofront(c, L, x, y, s=1.0, g=60, lamp=True, rear=False, smoke=True, **k):
    """An 1860s locomotive seen head-on and draped in black; rear=True: the back of the last coach, going away."""
    g = g * s
    out = []
    if rear:
        c.rect(x - 1.05 * g, y - 2.55 * g, x + 1.05 * g, y - 0.35 * g, "#1a120f")
        c.c.drawPath(smooth_path([(x - 1.1 * g, y - 2.5 * g), (x - 0.6 * g, y - 2.85 * g), (x + 0.6 * g, y - 2.85 * g),
                                  (x + 1.1 * g, y - 2.5 * g)], True, k=0.2), paint("#0b0908"))
        c.rect(x - 0.3 * g, y - 2.2 * g, x + 0.3 * g, y - 0.55 * g, "#070606")          # end door
        c.rect(x - 1.15 * g, y - 0.55 * g, x + 1.15 * g, y - 0.42 * g, "#0b0908")      # platform
        for px in (-1.05, -0.6, 0.6, 1.05):
            c.line([(x + px * g, y - 0.55 * g), (x + px * g, y - 1.1 * g)], "#0b0908", max(1, 0.06 * g))
        c.line([(x - 1.1 * g, y - 1.1 * g), (x + 1.1 * g, y - 1.1 * g)], "#0b0908", max(1, 0.06 * g))
        _swags(c, x - 1.0 * g, x + 1.0 * g, y - 2.45 * g, 3, 0.22 * g, max(0.3, g / 60))
        for wx in (-0.7, 0.7):
            c.ellipse(x + wx * g, y - 0.18 * g, 0.18 * g, 0.2 * g, "#050506")
        if smoke:
            for j in range(7):
                c.circle(x + (0.2 + j * 0.25) * g, y - (3.3 + j * 0.45) * g, (0.35 + j * 0.16) * g, "#262b30",
                         0.42 - j * 0.05)
        return out
    c.rect(x - 1.0 * g, y - 2.35 * g, x + 1.0 * g, y - 1.5 * g, "#040506")              # the cab behind
    c.rect(x - 1.08 * g, y - 2.45 * g, x + 1.08 * g, y - 2.32 * g, "#020303")
    for wx in (-0.78, 0.55):                                                            # cab front windows
        c.rect(x + wx * g, y - 2.2 * g, x + (wx + 0.23) * g, y - 1.84 * g, "#0c0a08")
        L.rect(x + wx * g, y - 2.2 * g, x + (wx + 0.23) * g, y - 1.84 * g, WARM, 0.12)
    c.rect(x - 1.02 * g, y - 0.98 * g, x + 1.02 * g, y - 0.9 * g, "#050607")            # running boards
    for side in (-1, 1):                                                                # cylinders
        c.rect(min(x + side * 0.6 * g, x + side * 1.0 * g), y - 0.92 * g, max(x + side * 0.6 * g, x + side * 1.0 * g),
               y - 0.6 * g, "#0b0c0e", r=0.08 * g)
    c.circle(x, y - 1.42 * g, 0.7 * g, "#2a2e34")                                       # smokebox front
    c.circle(x, y - 1.42 * g, 0.62 * g, "#0a0b0d")
    c.circle(x, y - 1.42 * g, 0.5 * g, "#1c1f24")
    for j in range(8):                                                                  # door bolts
        a = j * math.tau / 8
        c.circle(x + math.cos(a) * 0.42 * g, y - 1.42 * g + math.sin(a) * 0.42 * g, 0.03 * g, "#3a3e44")
    c.circle(x, y - 1.42 * g, 0.07 * g, "#050607")
    c.rect(x - 0.12 * g, y - 2.62 * g, x + 0.12 * g, y - 2.0 * g, "#08090b")            # stack
    c.poly([(x - 0.42 * g, y - 3.15 * g), (x + 0.42 * g, y - 3.15 * g), (x + 0.12 * g, y - 2.6 * g),
            (x - 0.12 * g, y - 2.6 * g)], "#08090b", smooth=False)
    c.rect(x - 0.46 * g, y - 3.24 * g, x + 0.46 * g, y - 3.12 * g, "#08090b")
    c.rect(x - 0.34 * g, y - 2.4 * g, x + 0.34 * g, y - 1.98 * g, "#0a0b0d", r=0.04 * g)  # headlamp
    c.rect(x - 0.4 * g, y - 2.46 * g, x + 0.4 * g, y - 2.38 * g, "#050607")
    c.rect(x - 0.98 * g, y - 0.66 * g, x + 0.98 * g, y - 0.48 * g, "#0a0b0d")            # buffer beam
    c.poly([(x - 0.95 * g, y), (x + 0.95 * g, y), (x + 0.28 * g, y - 0.48 * g), (x - 0.28 * g, y - 0.48 * g)],
           "#0a0b0d", smooth=False)                                                     # cowcatcher
    for t in range(-4, 5):
        c.line([(x + t * 0.22 * g, y), (x + t * 0.065 * g, y - 0.48 * g)], "#1a1c1f", max(1, 0.03 * g), 0.8)
    for wx in (-0.85, 0.85):
        c.ellipse(x + wx * g, y - 0.3 * g, 0.16 * g, 0.3 * g, "#050506")
    ss = max(0.3, g / 60)
    _swags(c, x - 0.95 * g, x + 0.95 * g, y - 0.66 * g, 2, 0.2 * g, ss)                # mourning on the beam
    _swags(c, x - 0.62 * g, x + 0.62 * g, y - 1.98 * g, 2, 0.22 * g, ss)               # and under the lamp
    if smoke:
        for j in range(8):
            c.circle(x + (0.15 + j * 0.3) * g, y - (3.5 + j * 0.42) * g, (0.38 + j * 0.2) * g, "#262b30", 0.45 - j * 0.05)
    if lamp:
        c.circle(x, y - 2.19 * g, 0.15 * g, "#fff4d0", 0.95)
        out.append((x, y - 2.19 * g, (1.0, 0.9, 0.6), 0.8 * g, False, 0.45))
    return out


@prop
def haze(c, L, x, y, s=1.0, depth=190, color="#6a5a60", a=0.55, **k):
    """Morning mist on the fields just below the horizon (strongest at the horizon, fading toward the viewer)."""
    n = 48
    for j in range(n):
        f = j / n
        c.rect(-20, y + depth * f - 1, 1100, y + depth * (f + 1.0 / n) + 1, color, a * (1 - f) ** 2)
