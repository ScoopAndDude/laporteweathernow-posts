"""Props for the Saugatuck short (the Felt Mansion near Saugatuck, Michigan: the summer house Dorr Felt built for his
wife, Agnes, who died weeks after they moved in; later a seminary school, a convent, a state police post beside a
prison, and now a township museum with a ghost legend), added Nov. 16, 2026. They register in story_kit3.PROPS like
every prop.

    feltmansion  the house, front on, as the National Register description has it: a three-storey yellow-brick
                 Classical Revival main block of six bays under a steep slate roof, limestone sills and keystones,
                 a limestone entrance portico in the middle, and slightly recessed four-bay wings (drawn two storeys,
                 with round-arched first-floor windows and three-part casements above). lit = share of lit windows;
                 one = (row, col) of a single lit window in the main block; tone darkens the brick for night
    addingmachine a key-driven adding machine of the 1900s on a desk under a lamp, a panelled office wall behind:
                 a dark metal case, columns of round keys and a row of small result windows (no maker's name or lettering)
    frenchdoors  a dark room at night: a pair of tall glazed French doors, the left one standing open on darkness,
                 moonlight falling across the floor from a window out of the picture
    schoolprison the seminary's big 1960s brick school building (four storeys, flat roof, rows of windows), which the
                 state turned into a prison: bars=True puts bars on the windows (pair it with prisonfence);
                 bars=False for the school years

Nothing shows a real person's likeness, a body, a brand, a logo or any lettering.
"""
import math

import numpy as np

import art
import story_kit3 as K3
from story_kit import W, H  # noqa: F401

prop = K3.prop
INK = "#050607"
WARM = "#ffc27a"


def _rng(seed):
    return np.random.default_rng(seed)


def _shade(hexcol, k):
    """Darken (k < 1) or lighten (k > 1) a #rrggbb colour."""
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    f = lambda v: max(0, min(255, int(v * k)))
    return "#%02x%02x%02x" % (f(r), f(g), f(b))


def _window(c, L, x0, y0, x1, y1, on, s, sash=True, glass="#0a0b0d", glow=0.6):
    c.rect(x0, y0, x1, y1, WARM if on else glass, 0.92 if on else 1.0)
    if on:
        L.rect(x0, y0, x1, y1, WARM, glow)
    if sash:
        c.rect(x0, (y0 + y1) / 2 - 1.5 * s, x1, (y0 + y1) / 2 + 1.5 * s, "#1a1612", 0.9)


# ------------------------------------------------------------------------------------------- the house

@prop
def feltmansion(c, L, x, y, s=1.0, lit=0.15, one=None, tone=1.0, seed=3, **k):
    """The Felt Mansion, front on (see the top of this file)."""
    r = _rng(seed)
    if isinstance(one, list):
        one = tuple(one)
    brick = _shade("#9a8250", tone)
    brick_w = _shade("#86703f", tone)                                      # the recessed wings, a little darker
    stone = _shade("#b8b0a0", tone)
    slate = _shade("#262a2e", min(1.0, tone + 0.1))
    bay, story = 66 * s, 92 * s
    mw = 6 * bay                                                           # the six-bay main block
    m0, m1 = x - mw / 2, x + mw / 2
    mtop = y - 3 * story
    ww_, wtop = 4 * 58 * s, y - 2 * story                                  # the four-bay wings, two storeys
    out = []
    for side in (-1, 1):                                                   # wings first, behind the main block
        w0 = m0 - ww_ if side < 0 else m1
        w1 = m0 if side < 0 else m1 + ww_
        c.rect(w0, wtop, w1, y, brick_w)
        c.poly([(w0 - 6 * s, wtop), (w0 + 22 * s * (1 if side < 0 else 0), wtop - 58 * s),
                (w1 - 22 * s * (0 if side < 0 else 1), wtop - 58 * s), (w1 + 6 * s, wtop)], slate)
        c.rect(w0 - 6 * s, wtop - 3 * s, w1 + 6 * s, wtop + 4 * s, _shade(stone, 0.7))          # the cornice
        for j in range(4):
            cx = w0 + (j + 0.5) * ww_ / 4
            on = (r.uniform() < lit)
            ax0, ax1, ay0, ay1 = cx - 15 * s, cx + 15 * s, y - story + 18 * s, y - 14 * s     # round-arched, ground floor
            _window(c, L, ax0, ay0, ax1, ay1, on, s, sash=False)
            c.ellipse(cx, ay0, 15 * s, 13 * s, WARM if on else "#0a0b0d", 0.92 if on else 1.0)
            c.line([(ax0 - 3 * s, ay1 + 3 * s), (ax1 + 3 * s, ay1 + 3 * s)], stone, 3 * s)
            on = (r.uniform() < lit)                                       # three-part casement above
            _window(c, L, cx - 21 * s, wtop + 20 * s, cx + 21 * s, wtop + story - 26 * s, on, s, sash=False)
            for q in (-1, 1):
                c.rect(cx + q * 7 * s - 1.2 * s, wtop + 20 * s, cx + q * 7 * s + 1.2 * s, wtop + story - 26 * s, "#1a1612")
            c.line([(cx - 24 * s, wtop + story - 23 * s), (cx + 24 * s, wtop + story - 23 * s)], stone, 3 * s)
        jx = m0 if side < 0 else m1                                        # the shadow where the wing steps back
        c.rect(jx - (10 * s if side < 0 else 0), wtop, jx + (0 if side < 0 else 10 * s), y, "#000000", 0.35)
    c.rect(m0, mtop, m1, y, brick)                                         # the main block
    c.poly([(m0 - 10 * s, mtop), (m0 + 34 * s, mtop - 112 * s), (m1 - 34 * s, mtop - 112 * s), (m1 + 10 * s, mtop)], slate)
    for q in range(5):                                                     # slate courses
        yy = mtop - 18 * s - q * 19 * s
        c.line([(m0 + 4 * s + q * 6 * s, yy), (m1 - 4 * s - q * 6 * s, yy)], "#000000", 1.2 * s, 0.35)
    c.rect(m0 - 10 * s, mtop - 4 * s, m1 + 10 * s, mtop + 6 * s, stone)    # the cornice
    for row in range(3):
        for j in range(6):
            cx = m0 + (j + 0.5) * bay
            if row == 2 and j in (2, 3):
                continue                                                   # the portico covers the middle bays below
            wy0 = mtop + row * story + 20 * s
            wy1 = mtop + (row + 1) * story - 18 * s
            on = (one == (row, j)) if one is not None else (r.uniform() < lit)
            _window(c, L, cx - 15 * s, wy0, cx + 15 * s, wy1, on, s)
            c.rect(cx - 19 * s, wy1, cx + 19 * s, wy1 + 4 * s, stone)      # limestone sill
            c.poly([(cx - 6 * s, wy0), (cx + 6 * s, wy0), (cx + 4 * s, wy0 - 9 * s), (cx - 4 * s, wy0 - 9 * s)], stone)  # keystone
            if row == 1:                                                   # a decorative panel below the 2nd-floor windows
                c.rect(cx - 16 * s, wy1 + 14 * s, cx + 16 * s, wy1 + 30 * s, _shade(stone, 0.85))
    # the limestone entrance portico over the two middle bays
    p0, p1 = x - 1.05 * bay, x + 1.05 * bay
    c.rect(p0 - 8 * s, y - story - 4 * s, p1 + 8 * s, y - story + 16 * s, stone)          # entablature
    for px in (p0, p0 + 18 * s, p1 - 18 * s, p1):
        c.rect(px - 7 * s, y - story + 16 * s, px + 7 * s, y, stone)
    c.rect(x - 22 * s, y - story + 34 * s, x + 22 * s, y, "#0c0a08")       # the door
    if one == "door" or (lit > 0.5):
        L.rect(x - 22 * s, y - story + 34 * s, x + 22 * s, y, WARM, 0.5)
    c.rect(p0 - 14 * s, y - 8 * s, p1 + 14 * s, y, _shade(stone, 0.8))     # steps
    c.rect(m0 - ww_ - 8 * s, y - 6 * s, m1 + ww_ + 8 * s, y + 2 * s, _shade(stone, 0.55))  # the foundation
    return out


# ------------------------------------------------------------------------------------------- the adding machine

@prop
def addingmachine(c, L, x, y, s=1.0, lamp=True, seed=5, **k):
    """A key-driven adding machine on a desk under a lamp (see the top of this file)."""
    r = _rng(seed)
    c.rect(-20, -20, W + 20, y, "#16110d")                                  # an office wall behind the desk
    for j in range(int(W / (120 * s)) + 2):                                # panelling
        px = j * 120 * s
        c.rect(px + 10 * s, y - 520 * s, px + 110 * s, y - 60 * s, "#1c1610")
        c.line([(px + 10 * s, y - 520 * s), (px + 110 * s, y - 520 * s)], "#2a2016", 2 * s)
    c.rect(-20, y, W + 20, y + 260 * s, "#2a1a10")                         # the desk top, front edge
    c.rect(-20, y, W + 20, y + 10 * s, "#3a2616")
    for j in range(8):                                                     # wood grain
        yy = y + 30 * s + j * 26 * s
        c.line([(-20, yy), (W + 20, yy + r.uniform(-6, 6) * s)], "#1e120a", 2 * s, 0.6)
    if lamp:
        L.circle(x, y - 120 * s, 380 * s, "#ffcf8a", 0.12, blur=120 * s)
    bw, bd = 420 * s, 230 * s                                              # the case, seen from the front and above
    c.ellipse(x, y + 8 * s, bw * 0.62, 26 * s, "#000000", 0.45, blur=10 * s)
    c.poly([(x - bw / 2, y), (x + bw / 2, y), (x + bw / 2 - 30 * s, y - bd), (x - bw / 2 + 30 * s, y - bd)], "#14161a")
    c.poly([(x - bw / 2, y), (x + bw / 2, y), (x + bw / 2, y - 34 * s), (x - bw / 2, y - 34 * s)], "#1c1f24")
    for j in range(8):                                                     # the result windows along the front
        wx = x - bw / 2 + 40 * s + j * (bw - 80 * s) / 7
        c.rect(wx - 9 * s, y - 27 * s, wx + 9 * s, y - 11 * s, "#d8cfb4")
        c.rect(wx - 9 * s, y - 27 * s, wx + 9 * s, y - 24 * s, "#000000", 0.4)
    c.poly([(x - bw / 2 + 4 * s, y - 36 * s), (x + bw / 2 - 4 * s, y - 36 * s), (x + bw / 2 - 32 * s, y - bd + 4 * s),
            (x - bw / 2 + 32 * s, y - bd + 4 * s)], "#22262c")                 # the key deck
    cols, rows = 9, 9
    for row in range(rows):                                                # columns of round keys, back rows smaller
        t = row / (rows - 1)
        yy = y - 52 * s - t * (bd - 80 * s)
        half = bw / 2 - 52 * s - t * 24 * s
        kr = (8.5 - 3 * t) * s
        for j in range(cols):
            kx = x - half + j * (2 * half) / (cols - 1)
            c.ellipse(kx, yy + 2.5 * s, kr, kr * 0.6, "#000000", 0.7)
            c.ellipse(kx, yy, kr, kr * 0.6, "#a89c84" if (j % 2 == 0) else "#3a3a3c")
            c.ellipse(kx - kr * 0.25, yy - kr * 0.15, kr * 0.35, kr * 0.2, "#ffffff", 0.25)
    c.line([(x - bw / 2 + 30 * s, y - bd), (x + bw / 2 - 30 * s, y - bd)], "#5a6068", 2.5 * s, 0.8)   # bright edges
    c.line([(x - bw / 2, y - 34 * s), (x + bw / 2, y - 34 * s)], "#4a5058", 2.5 * s, 0.8)
    c.poly([(x + bw / 2 - 30 * s, y - bd), (x + bw / 2, y), (x + bw / 2 + 6 * s, y - 4 * s), (x + bw / 2 - 26 * s, y - bd - 4 * s)],
           "#0a0b0d")
    for j in range(3):                                                     # papers on the desk
        px, py = x - 330 * s + j * 18 * s, y + 70 * s + j * 6 * s
        c.poly([(px, py), (px + 170 * s, py - 8 * s), (px + 182 * s, py + 104 * s), (px + 10 * s, py + 112 * s)], "#cfc6ae", 0.9)
    for j in range(6):
        px, py = x - 316 * s, y + 96 * s + j * 14 * s
        c.line([(px, py), (px + 130 * s, py - 6 * s)], "#7a7262", 1.6 * s, 0.7)
    return []


# ------------------------------------------------------------------------------------------- the doors

@prop
def frenchdoors(c, L, x, y, s=1.0, ajar=0.55, seed=7, **k):
    """French doors in a dark room at night, one standing open (see the top of this file)."""
    wall = "#14100e"
    c.rect(-20, -20, W + 20, H + 20, wall)
    for j in range(int(W / (36 * s)) + 2):                                 # faint wallpaper stripes
        c.rect(j * 36 * s, -20, j * 36 * s + 12 * s, y - 210 * s, "#1a1512", 0.7)
    c.rect(-20, y - 210 * s, W + 20, y - 196 * s, "#2a1f18")               # chair rail
    for j in range(int(W / (150 * s)) + 2):                                # wainscot panels
        px = j * 150 * s + 20 * s
        c.rect(px, y - 180 * s, px + 110 * s, y - 30 * s, "#1c1612")
    c.rect(-20, y, W + 20, H + 20, "#1a120c")                              # the floor
    for j in range(14):
        c.line([(-20, y + j * 22 * s), (W + 20, y + j * 22 * s)], "#120c08", 2 * s, 0.7)
    dw, dh = 300 * s, 620 * s                                              # the doorway
    x0, x1, top = x - dw / 2, x + dw / 2, y - dh
    c.rect(x0 - 26 * s, top - 26 * s, x1 + 26 * s, y, "#2a2018")           # the frame
    c.rect(x0, top, x1, y, "#020203")                                      # darkness beyond
    lw = dw / 2
    # the right leaf, closed
    c.rect(x, top, x1, y, "#2e2419")
    for row in range(5):
        for col in range(3):
            gx0 = x + 12 * s + col * (lw - 24 * s) / 3
            gy0 = top + 14 * s + row * (dh - 40 * s) / 5
            c.rect(gx0 + 3 * s, gy0 + 3 * s, gx0 + (lw - 24 * s) / 3 - 3 * s, gy0 + (dh - 40 * s) / 5 - 3 * s, "#0c1016")
            c.rect(gx0 + 3 * s, gy0 + 3 * s, gx0 + 9 * s, gy0 + (dh - 40 * s) / 5 - 3 * s, "#8aa0b8", 0.12)
    c.circle(x + 16 * s, y - dh * 0.48, 6 * s, "#a08a5a")
    # the left leaf, swung open into the room (drawn foreshortened, hinged at x0)
    ow = lw * (1 - ajar * 0.75)
    grow = 70 * s * ajar
    c.poly([(x0, top), (x0 - ow, top - grow), (x0 - ow, y + grow), (x0, y)], "#2a2016")
    for row in range(5):
        for col in range(3):
            fa = col / 3
            fb = (col + 1) / 3
            ya = top + 14 * s + row * (dh - 40 * s) / 5
            yb = top + 14 * s + (row + 1) * (dh - 40 * s) / 5 - 6 * s

            def pt(f, yy):
                return (x0 - ow * f, yy + (yy - (top + y) / 2) * (grow / (dh / 2)) * f)
            c.poly([pt(fa + 0.03, ya), pt(fb - 0.03, ya), pt(fb - 0.03, yb), pt(fa + 0.03, yb)], "#0b0f15")
    c.poly([(x0, y), (x0 - ow, y + grow), (x0 - ow + 40 * s, y + grow + 160 * s), (x0 + 60 * s, y + 150 * s)], "#000000", 0.25)
    # moonlight from a window out of the picture, falling across the floor
    mx0, my0 = W * 0.70, y + 60 * s                                         # a window's patch, skewed across the boards
    quad = [(mx0, my0), (mx0 + 260 * s, my0 - 20 * s), (mx0 + 180 * s, my0 + 250 * s), (mx0 - 110 * s, my0 + 280 * s)]
    c.poly(quad, "#b8c8dc", 0.13)
    (ax, ay), (bx, by), (cx_, cy_), (dx, dy) = quad
    c.line([((ax + bx) / 2, (ay + by) / 2), ((cx_ + dx) / 2, (cy_ + dy) / 2)], wall, 8 * s, 0.9)     # the window's cross
    c.line([((ax + dx) / 2, (ay + dy) / 2), ((bx + cx_) / 2, (by + cy_) / 2)], wall, 8 * s, 0.9)
    L.poly(quad, "#c8d8ec", 0.06)
    return []


# ------------------------------------------------------------------------------------------- the prison

@prop
def schoolprison(c, L, x, y, s=1.0, n=16, storeys=4, lit=0.2, bars=True, seed=11, **k):
    """The seminary's big 1960s school building, later the prison (see the top of this file)."""
    r = _rng(seed)
    sh = 60 * s
    bw, bh = 900 * s, storeys * sh
    x0, x1 = x - bw / 2, x + bw / 2
    c.rect(x0, y - bh, x1, y, "#3e2e24")                                    # brick, flat roof
    c.rect(x0 - 8 * s, y - bh - 10 * s, x1 + 8 * s, y - bh, "#1a1614")
    for row in range(storeys):
        yy = y - bh + row * sh
        c.rect(x0, yy + sh - 6 * s, x1, yy + sh - 3 * s, "#2a1f19", 0.8)    # floor bands
        for j in range(n):
            wx = x0 + (j + 0.5) * bw / n
            wy0 = yy + 14 * s
            on = r.uniform() < lit
            c.rect(wx - 16 * s, wy0, wx + 16 * s, wy0 + 30 * s, WARM if on else "#0b0c0e", 0.9 if on else 1.0)
            if on:
                L.rect(wx - 16 * s, wy0, wx + 16 * s, wy0 + 30 * s, WARM, 0.5)
            if bars:
                for q in (-6, 6):
                    c.rect(wx + q * s - 1.2 * s, wy0, wx + q * s + 1.2 * s, wy0 + 30 * s, "#1a1a1a")
    c.rect(x - 70 * s, y - bh - 40 * s, x + 70 * s, y - bh, "#3e2e24")      # a stair tower over the entrance
    c.rect(x - 78 * s, y - bh - 48 * s, x + 78 * s, y - bh - 40 * s, "#1a1614")
    c.rect(x - 40 * s, y - 70 * s, x + 40 * s, y, "#14100e")                # the entrance
    c.rect(x - 60 * s, y - 82 * s, x + 60 * s, y - 70 * s, "#2a2420")
    return []
