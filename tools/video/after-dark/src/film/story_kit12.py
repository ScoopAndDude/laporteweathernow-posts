"""Props for the Drumright short (the outlaw the Bureau freed and Officer Ulysses Lenox, 1924), added Nov. 15,
2026. They register in story_kit3.PROPS like every prop, so a storyboard names them in "props": [{"p": "derrick", ...}].

    derrick    a wooden oil derrick of the 1910s-20s (a "standard rig"): four legs tapering to the crown block,
               girts and crossed braces, a plank floor; house=True adds the walking beam on its samson post, the
               band wheel and the engine house beside it (flip=True puts them on the left); lit=0..1 a lantern
               on the derrick floor and a lit engine-house window
    oiltank    a riveted steel oil storage tank with a low conical roof and a stair up its side (w, h in px)
    hills      rolling hills, layer behind layer (layers, amp, seed), the nearest ridge at y, with clumps of
               blackjack and post oak along the ridges (trees=True)
    dirtroad   an unpaved road straight across the picture at y with wheel ruts (w = how deep it looks)
    dust       a drifting cloud of road dust (w, h, a)
    tourer     a touring car of the early 1920s, side on: folding top up, spoked wheels, running boards, one
               headlamp showing. flip=True faces it left; men=0..4 hats above the doors; lamps=0..1;
               flash=0..1 small gun flashes at the side (no gun is drawn); dust=0..1 dust thrown up behind it
    jailhouse  a two-storey stone jail with barred windows and an arched door (door="open" | "shut"; an open
               door throws lamplight out down the steps, glow=0..1); a lit lantern over the door
    outlaw     a man in a hat and a long coat walking away from us, alone (shadow=True: the long shadow a light
               behind him throws toward us)
    townbank   a one-storey brick bank of the 1910s with a stepped parapet, a big front window and a door with a
               transom, no lettering (lit=0..1 lights the window)
    courtroom  an empty courtroom: the judge's raised bench and high-backed chair, a witness box, the rail in
               front, a wall clock with no particular time and two tall windows letting in moonlight
    brickwall  a tall red-brick prison wall across the picture with a guard picket on it (x is the picket) and
               its searchlight beam (beam=0..1, aim= px the beam's far end lands left or right of the picket)

People are small anonymous silhouettes. Nothing shows a body, a wound, a gun, a real person's likeness or a brand.
No picture of the Avery bank, the officers' car or the robbers' car has been found, so they are drawn generic.
"""
import math

import numpy as np

import story_kit3 as K3
from story_kit import WARM, W, H
from core import smooth_path, paint

prop = K3.prop
INK = "#030304"
TIMBER = "#08090a"


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _mix(a, b, t):
    pa, pb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(int(round(pa[i] + (pb[i] - pa[i]) * t)) for i in range(3))


@prop
def derrick(c, L, x, y, s=1.0, lit=0.0, house=True, flip=False, rim=0.0, color=TIMBER, **k):
    """A wooden oil derrick of the 1910s-20s, with its engine house (see the top of this file); rim=0..1 a faint
    moonlit edge on the right-hand leg and the tops of the girts, so it reads against a night sky."""
    d = -1 if flip else 1
    out = []
    ht = 620 * s
    bw, tw = 110 * s, 18 * s
    fy = y - 22 * s                                                               # the derrick floor

    def lx(t, side):
        return x + side * (bw + (tw - bw) * t)

    def ly(t):
        return fy - (ht - 22 * s) * t

    c.rect(x - bw - 34 * s, fy, x + bw + 34 * s, fy + 10 * s, "#0d0e0f")           # plank floor on sills
    for px in (-bw - 28 * s, -10 * s, bw + 20 * s):
        c.rect(x + px, fy + 10 * s, x + px + 8 * s, y, color)
    for side in (-1, 1):                                                          # the four corner legs (two show)
        c.poly([(lx(0, side) - side * 6 * s, fy), (lx(0, side) + side * 2 * s, fy),
                (lx(1, side) + side * 1 * s, ly(1)), (lx(1, side) - side * 3 * s, ly(1))], color)
    lv = [1 - (1 - j / 10) ** 1.25 for j in range(11)]                            # girts, closer near the top
    for t in lv[1:]:
        c.line([(lx(t, -1), ly(t)), (lx(t, 1), ly(t))], color, max(1.2, 4.2 * s * (1 - 0.45 * t)))
    for t0, t1 in zip(lv, lv[1:]):                                                # crossed braces
        w = max(0.9, 2.2 * s * (1 - 0.4 * t0))
        c.line([(lx(t0, -1), ly(t0)), (lx(t1, 1), ly(t1))], color, w, 0.9)
        c.line([(lx(t0, 1), ly(t0)), (lx(t1, -1), ly(t1))], color, w, 0.9)
    top = ly(1)
    c.rect(x - tw - 16 * s, top - 6 * s, x + tw + 16 * s, top + 4 * s, color)     # the crown platform
    c.rect(x - 11 * s, top - 30 * s, x + 11 * s, top - 6 * s, color)              # crown block
    c.circle(x, top - 18 * s, 7 * s, "#141516")
    c.line([(x - 14 * s, top - 6 * s), (x, top - 54 * s), (x + 14 * s, top - 6 * s)], color, max(1.2, 3 * s))  # gin pole
    c.line([(x + 3 * s, top - 16 * s), (x + 3 * s, fy - 40 * s)], "#1a1b1c", max(0.8, 1.6 * s), 0.8)  # the drilling line
    if rim > 0:                                                                   # moonlight catching the timbers
        rc = "#6a8098"
        c.line([(lx(0, 1) + 2 * s, fy), (lx(1, 1) + 1 * s, ly(1))], rc, max(0.8, 1.6 * s), 0.35 * rim)
        c.line([(lx(0, -1) - 5 * s, fy), (lx(1, -1) - 2 * s, ly(1))], rc, max(0.6, 1.0 * s), 0.16 * rim)
        for t in lv[1:]:
            c.line([(lx(t, -1), ly(t) - 2 * s), (lx(t, 1), ly(t) - 2 * s)], rc, max(0.6, 1.0 * s), 0.2 * rim)
        c.line([(x - tw - 16 * s, top - 6 * s), (x + tw + 16 * s, top - 6 * s)], rc, max(0.6, 1.2 * s), 0.3 * rim)
    if house:
        sx = x + d * (bw + 70 * s)                                                # samson post and walking beam
        c.rect(sx - 8 * s, y - 150 * s, sx + 8 * s, y - 10 * s, color)
        c.poly([(sx - 26 * s, y), (sx, y - 70 * s), (sx + 26 * s, y)], color)
        c.line([(x + d * 18 * s, y - 128 * s), (sx + d * 150 * s, y - 166 * s)], color, max(2.0, 13 * s))
        bx = sx + d * 150 * s                                                     # pitman and band wheel
        c.line([(bx, y - 164 * s), (bx + d * 6 * s, y - 70 * s)], color, max(1.5, 6 * s))
        c.circle(bx + d * 6 * s, y - 70 * s, 58 * s, color)
        c.circle(bx + d * 6 * s, y - 70 * s, 47 * s, "#101112")
        for t in range(8):
            a = math.pi * t / 4
            c.line([(bx + d * 6 * s, y - 70 * s),
                    (bx + d * 6 * s + 47 * s * math.cos(a), y - 70 * s + 47 * s * math.sin(a))], color, max(1.0, 3 * s))
        ex0, ex1 = bx + d * 44 * s, bx + d * 280 * s                              # the engine house
        e0, e1 = min(ex0, ex1), max(ex0, ex1)
        c.rect(e0, y - 132 * s, e1, y, "#0b0c0d")
        c.poly([(e0 - 8 * s, y - 128 * s), ((e0 + e1) / 2, y - 176 * s), (e1 + 8 * s, y - 128 * s)], "#070808")
        for j in range(1, 12):                                                    # board-and-batten
            c.line([(e0 + j * (e1 - e0) / 12, y - 128 * s), (e0 + j * (e1 - e0) / 12, y)], "#131415", max(0.8, 1.2 * s), 0.7)
        stx = ex1 - d * 30 * s                                                    # the exhaust stack
        c.rect(stx - 6 * s, y - 250 * s, stx + 6 * s, y - 150 * s, "#0a0a0a")
        for j in range(4):
            c.ellipse(stx + d * j * 26 * s, y - (262 + j * 26) * s, (14 + j * 10) * s, (8 + j * 4) * s, "#4a4a4c",
                      0.10 - j * 0.02, blur=8 * s)
        wx = (e0 + e1) / 2 + d * 40 * s
        on = lit > 0
        K3._win(c, L, wx - 16 * s, y - 100 * s, wx + 16 * s, y - 64 * s, on, k=0.45)
        if on:
            out.append((wx, y - 82 * s, (1.0, 0.72, 0.4), 50 * s, True, 0.3 * lit))
    if lit > 0:                                                                   # a lantern on the derrick floor
        hx, hy = x - d * 34 * s, fy - 26 * s
        c.rect(hx - 6 * s, hy - 10 * s, hx + 6 * s, hy + 10 * s, "#ffd890", 0.9)
        L.circle(hx, hy, 12 * s, WARM, 0.7 * lit)
        out.append((hx, hy, (1.0, 0.76, 0.42), 70 * s, True, 0.5 * lit))
    return out


@prop
def oiltank(c, L, x, y, s=1.0, w=260, h=150, color="#0b0c0d", **k):
    """A riveted steel oil storage tank with a low conical roof and a stair up its side."""
    hw, hh = w * s / 2, h * s
    c.rect(x - hw, y - hh, x + hw, y, color)
    for j in range(1, 5):                                                         # the courses of plate
        c.line([(x - hw, y - hh * j / 5), (x + hw, y - hh * j / 5)], "#16181a", max(0.8, 1.4 * s), 0.8)
    for j in range(1, 7):
        xx = x - hw + 2 * hw * j / 7
        c.line([(xx, y - hh), (xx, y)], "#131517", max(0.6, 1.0 * s), 0.6)
    c.poly([(x - hw - 5 * s, y - hh), (x, y - hh - 30 * s), (x + hw + 5 * s, y - hh)], "#090a0b")
    c.line([(x - hw, y - hh), (x, y - hh - 30 * s), (x + hw, y - hh)], "#3a4048", max(0.8, 1.4 * s), 0.3)
    c.line([(x - hw + 14 * s, y), (x + hw - 26 * s, y - hh)], "#1a1c1e", max(1.0, 3.5 * s))  # the stair
    c.line([(x - hw + 14 * s, y - 22 * s), (x + hw - 26 * s, y - hh - 22 * s)], "#1a1c1e", max(0.6, 1.2 * s), 0.8)
    for j in range(8):
        f = j / 8
        px = x - hw + 14 * s + (2 * hw - 40 * s) * f
        py = y - hh * f
        c.line([(px, py), (px, py - 22 * s)], "#1a1c1e", max(0.6, 1.0 * s), 0.8)
    return []


@prop
def hills(c, L, x, y, s=1.0, layers=3, amp=60, seed=1, trees=True, color="#030405", far="#0e141a", **k):
    """Rolling hills, layer behind layer, the nearest ridge at y, with oak clumps on the ridges."""
    r = np.random.default_rng(seed)
    for li in range(layers):
        f = li / max(1, layers - 1)
        base = y - (layers - 1 - li) * 72 * s
        col = _mix(far, color, f)
        p1, p2, p3 = r.uniform(0, 6.28, 3)
        a = amp * s * (0.55 + 0.55 * f)
        pts = []
        for xi in range(-40, W + 61, 12):
            v = (0.5 + 0.5 * math.sin(xi / (230 + 90 * li) + p1)) * (0.6 + 0.4 * math.sin(xi / 540 + p2)) \
                + 0.12 * math.sin(xi / 70 + p3)
            pts.append((xi, base - a * v))
        c.poly(pts + [(W + 60, H + 20), (-40, H + 20)], col, smooth=True)
        if trees:
            tc = _mix(col, "#000000", 0.35)
            xi = -20 + r.uniform(0, 40)
            while xi < W + 20:
                j = min(len(pts) - 1, max(0, int((xi + 40) / 12)))
                ty = pts[j][1]
                n = int(r.integers(2, 6))
                for q in range(n):
                    rr = r.uniform(7, 15) * s * (0.55 + 0.7 * f)
                    c.circle(xi + q * rr * 1.1, ty - rr * 0.55 + r.uniform(-2, 2) * s, rr, tc)
                xi += r.uniform(60, 170) * (0.7 + 0.6 * f)
    return []


@prop
def dirtroad(c, L, x, y, s=1.0, w=90, color="#251d15", **k):
    """An unpaved road straight across the picture at y, with wheel ruts."""
    hw = w * s / 2
    c.poly([(-20, y - hw), (W + 20, y - hw - 4 * s), (W + 20, y + hw + 6 * s), (-20, y + hw)], color)
    c.poly([(-20, y - hw), (W + 20, y - hw - 4 * s), (W + 20, y - hw + 6 * s), (-20, y - hw + 8 * s)], "#000000", 0.25,
           blur=4 * s)
    for off in (-0.45, -0.15, 0.2, 0.5):
        c.line([(-20, y + off * hw * 2 * 0.5 + 2 * s), (W + 20, y + off * hw * 2 * 0.5)], "#120d09", max(1.0, 4 * s), 0.55,
               blur=2 * s)
    return []


@prop
def dust(c, L, x, y, s=1.0, w=320, h=130, color="#a08c70", a=0.2, seed=1, **k):
    """A drifting cloud of road dust."""
    r = np.random.default_rng(seed)
    for j in range(16):
        px = x + r.uniform(-0.5, 0.5) * w * s
        py = y - r.uniform(0.0, 1.0) * h * s
        c.ellipse(px, py, r.uniform(40, 90) * s, r.uniform(22, 50) * s, color, a * r.uniform(0.5, 1.0), blur=18 * s)
    return []


@prop
def tourer(c, L, x, y, s=1.0, flip=False, men=0, lamps=0.0, flash=0.0, dust=0.0, top=True,
           color="#060707", dustcol="#a08c70", seed=1, **k):
    """A touring car of the early 1920s, side on (see the top of this file)."""
    d = -1 if flip else 1
    r = np.random.default_rng(seed)
    out = []

    def X(v):
        return x + d * v * s

    def P(pts):
        return [(X(a), y - b * s) for a, b in pts]

    if dust > 0:                                                                  # dust thrown up behind
        for j in range(14):
            px = X(-260 - r.uniform(0, 380))
            py = y - r.uniform(0, 120) * s
            c.ellipse(px, py, r.uniform(50, 110) * s, r.uniform(26, 60) * s, dustcol, 0.2 * dust * r.uniform(0.5, 1),
                      blur=20 * s)
    body = "#0a0b0c"
    for wx in (-168, 176):                                                        # the wheels
        c.circle(X(wx), y - 58 * s, 58 * s, "#050505")
        c.circle(X(wx), y - 58 * s, 41 * s, "#121314")
        for t in range(12):
            a = 2 * math.pi * t / 12 + 0.2
            c.line([(X(wx), y - 58 * s), (X(wx) + 40 * s * math.cos(a), y - 58 * s + 40 * s * math.sin(a))],
                   "#1e1f20", max(1.0, 4 * s))
        c.circle(X(wx), y - 58 * s, 11 * s, "#1a1a1a")
    c.poly(P([(-262, 66), (-250, 172), (-232, 178), (60, 178), (60, 72), (-262, 66)]), body)   # the body (tub)
    c.poly(P([(-262, 66), (-276, 86), (-276, 150), (-262, 172)]), body)           # its rounded back
    c.poly(P([(60, 98), (60, 166), (226, 160), (232, 102)]), body)                # the hood
    for j in range(5):                                                            # hood louvers
        c.line(P([(120 + j * 18, 112), (126 + j * 18, 146)]), "#1a1b1c", max(0.8, 2 * s))
    c.poly(P([(226, 92), (252, 92), (254, 178), (228, 176)]), "#0d0e0f")          # the radiator
    c.rect(min(X(234), X(246)), y - 188 * s, max(X(234), X(246)), y - 178 * s, "#1c1c1c")
    c.line(P([(-110, 168), (-110, 92)]), "#16171a", max(0.8, 1.6 * s))           # door seams
    c.line(P([(-10, 168), (-10, 92)]), "#16171a", max(0.8, 1.6 * s))
    c.line(P([(-262, 112), (60, 116), (230, 118)]), "#1a1b1d", max(0.8, 1.4 * s), 0.7)  # body crease
    fend = "#040404"
    for wx in (-168, 176):                                                        # fenders sweeping to the board
        c.poly(P([(wx - 74, 52), (wx - 64, 98), (wx - 30, 124), (wx + 30, 124), (wx + 66, 100), (wx + 82, 70),
                  (wx + 70, 66), (wx + 52, 92), (wx + 24, 112), (wx - 24, 112), (wx - 54, 92), (wx - 62, 56)]),
               fend, smooth=True)
    c.rect(min(X(-100), X(110)), y - 58 * s, max(X(-100), X(110)), y - 50 * s, fend)  # running board
    c.poly(P([(60, 176), (78, 176), (96, 268), (86, 270)]), "#0e0f10")            # windshield post, raked
    c.poly(P([(64, 178), (88, 268), (92, 268), (70, 178)]), "#4a5a66", 0.25)      # glass glint
    c.ellipse(X(40), y - 200 * s, 16 * s, 5 * s, "#0c0c0c")                       # steering wheel
    c.line(P([(40, 200), (70, 168)]), "#0c0c0c", max(1.0, 3 * s))
    for sx in (-30, -186):                                                        # seat backs
        c.rect(min(X(sx), X(sx + 26)), y - 214 * s, max(X(sx), X(sx + 26)), y - 176 * s, "#0c0c0d", r=6 * s)
    seats = [6, -146, 34, -118][:max(0, min(4, men))]
    for j, hx in enumerate(seats):                                                # men in hats, seen over the doors
        hy = y - (214 + r.uniform(-4, 4)) * s
        c.rect(X(hx) - 13 * s, hy, X(hx) + 13 * s, y - 176 * s, INK)
        c.circle(X(hx), hy - 10 * s, 10 * s, INK)
        c.ellipse(X(hx), hy - 17 * s, 18 * s, 4 * s, INK)
        c.rect(X(hx) - 10 * s, hy - 32 * s, X(hx) + 10 * s, hy - 17 * s, INK, r=3 * s)
    if top:                                                                       # the folding top, up
        c.poly(P([(92, 270), (100, 278), (-200, 282), (-262, 250), (-282, 206), (-266, 204), (-250, 244),
                  (-196, 268), (88, 264)]), "#0b0a09", smooth=True)
        for bx in (-60, -170):                                                    # bows and side irons
            c.line(P([(bx, 278), (bx + 6, 196)]), "#0b0a09", max(1.0, 3 * s))
        c.line(P([(-262, 204), (-200, 196), (60, 196)]), "#0b0a09", max(1.0, 2.5 * s))
    hx, hy = X(250), y - 160 * s                                                  # the headlamp drum
    c.ellipse(hx, hy, 15 * s, 19 * s, "#141414")
    c.ellipse(X(258), hy, 6 * s, 15 * s, "#ffe8b0" if lamps > 0 else "#3a3a36", 0.9 if lamps > 0 else 0.6)
    if lamps > 0:
        L.circle(X(260), hy, 18 * s, "#ffd890", 0.7 * lamps)
        out.append((X(262), hy, (1.0, 0.88, 0.62), 70 * s, False, 0.7 * lamps))
        ex = X(900)
        c.poly([(X(262), hy - 10 * s), (ex, hy - 90 * s), (ex, hy + 120 * s), (X(262), hy + 12 * s)],
               "#fff0c8", 0.05 * lamps, blur=20 * s)
    c.circle(X(-270), y - 120 * s, 6 * s, "#ff3a20", 0.8)                         # tail lamp
    if flash > 0:                                                                 # gun flashes, no gun drawn
        for j, (fx, fy) in enumerate(((14, 210), (-128, 206))):
            px, py = X(fx), y - fy * s
            for q in range(9):                                                    # a spray of sparks toward us
                a = math.pi / 2 + (q - 4) * 0.42 + (0.15 if j else -0.1)
                ln = (34 if q in (3, 4, 5) else 20) * s
                c.line([(px, py), (px + ln * math.cos(a) * 1.3, py + ln * math.sin(a) * 0.8)], "#ffe2a0",
                       max(0.8, 1.8 * s), 0.85 * flash)
            c.circle(px, py, 4.5 * s, "#fffbe8", flash)
            L.circle(px, py, 12 * s, "#ffc070", 0.55 * flash)
            out.append((px, py, (1.0, 0.72, 0.34), 46 * s, True, 0.7 * flash))
    return out


@prop
def jailhouse(c, L, x, y, s=1.0, door="open", glow=0.7, lamp=True, seed=4, **k):
    """A two-storey stone jail with barred windows and an arched door (see the top of this file)."""
    r = np.random.default_rng(seed)
    out = []
    hw, ht = 300 * s, 430 * s
    x0, x1 = x - hw, x + hw
    stone = "#17171a"
    c.rect(x0, y - ht, x1, y, stone)
    rows = int(ht / (22 * s))
    for j in range(rows):                                                         # rough-cut courses
        yy = y - j * 22 * s
        c.line([(x0, yy), (x1, yy)], "#0c0c0e", max(0.8, 1.5 * s), 0.8)
        off = (j % 2) * 30 * s
        xx = x0 + off
        while xx < x1:
            c.line([(xx, yy), (xx, yy - 22 * s)], "#0c0c0e", max(0.6, 1.2 * s), 0.6)
            if r.uniform() < 0.25:
                c.rect(xx + 2 * s, yy - 20 * s, xx + 56 * s, yy - 2 * s, "#222226", 0.35)
            xx += r.uniform(46, 72) * s
    c.rect(x0 - 14 * s, y - ht - 26 * s, x1 + 14 * s, y - ht, "#101012")          # the cornice and parapet
    c.rect(x0 - 6 * s, y - ht - 54 * s, x1 + 6 * s, y - ht - 26 * s, stone)
    c.line([(x0 - 14 * s, y - ht - 26 * s), (x1 + 14 * s, y - ht - 26 * s)], "#3a3e44", max(0.8, 1.5 * s), 0.35)
    c.rect(x0 - 10 * s, y - 214 * s, x1 + 10 * s, y - 202 * s, "#101012")         # the belt course

    def barred(wx, wy0, wy1, ww):
        c.rect(wx - ww, wy0, wx + ww, wy1, "#040405")
        c.rect(wx - ww - 6 * s, wy1, wx + ww + 6 * s, wy1 + 8 * s, "#26262a")
        n = max(2, int(2 * ww / (11 * s)))
        for q in range(1, n):
            bx = wx - ww + 2 * ww * q / n
            c.line([(bx, wy0), (bx, wy1)], "#2a2a2e", max(1.0, 2.6 * s))
        c.line([(wx - ww, (wy0 + wy1) / 2), (wx + ww, (wy0 + wy1) / 2)], "#2a2a2e", max(1.0, 2.6 * s))

    for wx in (-225, -95, 95, 225):                                               # upper cell windows
        barred(x + wx * s, y - 380 * s, y - 280 * s, 22 * s)
    for wx in (-200, 200):                                                        # lower windows
        barred(x + wx * s, y - 170 * s, y - 80 * s, 26 * s)
    dw, dh = 54 * s, 170 * s                                                      # the arched doorway
    pts = [(x - dw, y - 18 * s), (x - dw, y - dh)]
    for q in range(13):
        a = math.pi - math.pi * q / 12
        pts.append((x + dw * math.cos(a), y - dh - dw * 0.7 * math.sin(a)))
    pts.append((x + dw, y - 18 * s))
    c.poly([(px - (8 * s if px < x else -8 * s), py - 8 * s) for px, py in pts], "#0c0c0e")
    if door == "open":
        c.poly(pts, "#2a1a0c")
        if glow > 0:
            L.poly(pts, WARM, 0.5 * glow)
            c.poly(pts, "#ffb060", 0.35 * glow, blur=10 * s)
            out.append((x, y - 100 * s, (1.0, 0.68, 0.34), 140 * s, False, 0.45 * glow))
            c.poly([(x - dw, y), (x + dw, y), (x + 3.2 * dw, y + 420 * s), (x - 2.6 * dw, y + 420 * s)],
                   "#ffb060", 0.10 * glow, blur=26 * s)                           # light thrown out toward us
            L.poly([(x - dw, y), (x + dw, y), (x + 3.0 * dw, y + 380 * s), (x - 2.4 * dw, y + 380 * s)],
                   WARM, 0.14 * glow, blur=30 * s)
        c.poly([(x + dw, y - 18 * s), (x + dw + 46 * s, y - 10 * s), (x + dw + 46 * s, y - dh - 30 * s),
                (x + dw, y - dh - 10 * s)], "#120c08")                            # the door, swung open
        for q in range(4):
            yy = y - (40 + q * 46) * s
            c.line([(x + dw + 2 * s, yy), (x + dw + 44 * s, yy + 4 * s)], "#2a2a2e", max(1.0, 3 * s))
    else:
        c.poly(pts, "#120c08")
        for q in range(4):
            c.line([(x - dw, y - (40 + q * 40) * s), (x + dw, y - (40 + q * 40) * s)], "#2a2a2e", max(1.0, 3 * s))
    for j in range(3):                                                            # the steps
        c.rect(x - (dw + 30 * s) - j * 14 * s, y - 18 * s + j * 9 * s, x + (dw + 30 * s) + j * 14 * s,
               y - 9 * s + j * 9 * s, "#1e1e22")
    if lamp:                                                                      # lantern over the door
        lx_, ly_ = x, y - dh - dw * 0.7 - 34 * s
        c.line([(lx_, ly_ - 26 * s), (lx_, ly_ - 12 * s)], "#0c0c0c", max(1.0, 3 * s))
        c.rect(lx_ - 9 * s, ly_ - 12 * s, lx_ + 9 * s, ly_ + 14 * s, "#ffd890", 0.85)
        c.rect(lx_ - 12 * s, ly_ - 16 * s, lx_ + 12 * s, ly_ - 12 * s, "#0c0c0c")
        L.circle(lx_, ly_, 16 * s, WARM, 0.7)
        out.append((lx_, ly_, (1.0, 0.78, 0.45), 100 * s, True, 0.6))
    return out


@prop
def outlaw(c, L, x, y, s=1.0, shadow=True, skew=0.0, color=INK, **k):
    """A man in a hat and a long coat walking away from us, alone (skew= px the far end of his shadow moves right)."""
    u = s
    if shadow:                                                                    # thrown toward us by a light behind
        c.poly([(x - 18 * u, y), (x + 18 * u, y), (x + (60 + skew) * u, y + 300 * u), (x + (-40 + skew) * u, y + 310 * u)],
               "#000000", 0.5, blur=10 * u)
    c.poly([(x - 4 * u, y - 70 * u), (x - 12 * u, y - 70 * u), (x - 20 * u, y - 4 * u), (x - 8 * u, y)], color)  # legs, mid-stride
    c.poly([(x + 3 * u, y - 70 * u), (x + 12 * u, y - 70 * u), (x + 16 * u, y - 12 * u), (x + 6 * u, y - 10 * u)], color)
    c.poly([(x - 25 * u, y - 52 * u), (x + 25 * u, y - 52 * u), (x + 21 * u, y - 140 * u), (x + 14 * u, y - 150 * u),
            (x - 14 * u, y - 150 * u), (x - 21 * u, y - 140 * u)], color)          # the long coat
    c.line([(x - 22 * u, y - 140 * u), (x - 27 * u, y - 86 * u)], color, 9 * u)   # arms hanging
    c.line([(x + 22 * u, y - 140 * u), (x + 26 * u, y - 88 * u)], color, 9 * u)
    c.rect(x - 6 * u, y - 160 * u, x + 6 * u, y - 148 * u, color)                 # neck
    c.circle(x, y - 168 * u, 11 * u, color)                                       # head
    c.ellipse(x, y - 175 * u, 20 * u, 4.5 * u, color)                             # hat brim
    c.rect(x - 11 * u, y - 192 * u, x + 11 * u, y - 175 * u, color, r=4 * u)      # crown
    return []


@prop
def townbank(c, L, x, y, s=1.0, lit=0.3, flip=False, seed=2, **k):
    """A one-storey brick bank of the 1910s with a stepped parapet, no lettering (see the top of this file)."""
    d = -1 if flip else 1
    out = []
    hw, ht = 230 * s, 280 * s
    x0, x1 = x - hw, x + hw
    brick, brick_d, stone = "#24130e", "#170b08", "#3a342e"
    c.rect(x0, y - ht, x1, y, brick)
    c.poly([(x0, y - ht), (x - 90 * s, y - ht), (x - 90 * s, y - ht - 34 * s), (x + 90 * s, y - ht - 34 * s),
            (x + 90 * s, y - ht), (x1, y - ht), (x1, y - ht - 8 * s), (x0, y - ht - 8 * s)], brick)
    c.rect(x - 96 * s, y - ht - 42 * s, x + 96 * s, y - ht - 34 * s, stone)       # coping on the raised parapet
    c.rect(x0 - 6 * s, y - ht - 14 * s, x1 + 6 * s, y - ht - 6 * s, stone)
    c.rect(x - 60 * s, y - ht - 26 * s, x + 60 * s, y - ht - 6 * s, "#2e2822")    # a blank stone panel
    for j in range(int(ht / (9 * s))):                                            # brick courses
        c.line([(x0, y - j * 9 * s), (x1, y - j * 9 * s)], brick_d, max(0.6, 1.0 * s), 0.55)
    c.rect(x0 - 4 * s, y - 220 * s, x1 + 4 * s, y - 208 * s, stone)               # the cornice band
    for px in (x0, x1 - 26 * s):                                                  # corner pilasters
        c.rect(px, y - 208 * s, px + 26 * s, y, brick_d)
    wx0, wx1 = (x - 170 * s, x + 40 * s) if d > 0 else (x - 40 * s, x + 170 * s)  # the big front window
    on = lit > 0
    c.rect(wx0, y - 190 * s, wx1, y - 52 * s, "#0d1216")
    if on:
        L.rect(wx0, y - 190 * s, wx1, y - 52 * s, WARM, 0.22 * lit)
        c.rect(wx0, y - 190 * s, wx1, y - 52 * s, "#ffcc80", 0.12 * lit)
        out.append(((wx0 + wx1) / 2, y - 120 * s, (1.0, 0.74, 0.42), 120 * s, False, 0.25 * lit))
    c.line([(wx0, y - 160 * s), (wx1, y - 160 * s)], "#1a1210", max(1.0, 4 * s))    # transom bar
    c.line([((wx0 + wx1) / 2, y - 160 * s), ((wx0 + wx1) / 2, y - 52 * s)], "#1a1210", max(1.0, 3 * s))
    c.rect(wx0 - 6 * s, y - 52 * s, wx1 + 6 * s, y - 42 * s, stone)               # stone sill
    c.rect(wx0, y - 42 * s, wx1, y - 4 * s, brick_d)
    dx = x + 115 * s * d                                                          # the door and its transom
    c.rect(dx - 34 * s, y - 196 * s, dx + 34 * s, y, "#1a1210")
    c.rect(dx - 28 * s, y - 190 * s, dx + 28 * s, y - 160 * s, "#0d1216")
    c.rect(dx - 28 * s, y - 154 * s, dx + 28 * s, y - 4 * s, "#0a0706")
    c.rect(dx - 20 * s, y - 140 * s, dx + 20 * s, y - 70 * s, "#0d1216")
    c.circle(dx - 18 * s * d, y - 66 * s, 3 * s, "#8a7038", 0.7)
    c.rect(x0 - 12 * s, y - 4 * s, x1 + 12 * s, y + 6 * s, "#1c1a18")             # the sidewalk edge
    return out


@prop
def courtroom(c, L, x, y, s=1.0, moon=0.7, spread=330, **k):
    """An empty courtroom (see the top of this file); spread= how far each window stands from the middle."""
    out = []
    wood, wood_d = "#24160e", "#160d08"
    for wx in (-spread, spread):                                                  # two tall windows and their light
        wx = x + wx * s
        w0, w1, top, bot = wx - 70 * s, wx + 70 * s, y - 780 * s, y - 360 * s
        pts = [(w0, bot), (w0, top)]
        for q in range(13):
            a = math.pi - math.pi * q / 12
            pts.append((wx + 70 * s * math.cos(a), top - 50 * s * math.sin(a)))
        pts.append((w1, bot))
        c.poly([(px + (10 * s if px > wx else -10 * s), py - 8 * s) for px, py in pts] , "#0e0907")
        c.poly(pts, "#0e1a2a")
        c.poly(pts, "#3a5070", 0.35 * moon, blur=6 * s)
        for q in range(1, 4):
            c.line([(w0, top + (bot - top) * q / 4), (w1, top + (bot - top) * q / 4)], "#0e0907", max(1.0, 4 * s))
        c.line([(wx, top - 50 * s), (wx, bot)], "#0e0907", max(1.0, 4 * s))
        c.poly([(w0, bot), (w1, bot), (w1 + 120 * s, y + 160 * s), (w0 + 40 * s, y + 160 * s)], "#8aa6c8",
               0.07 * moon, blur=24 * s)
        L.poly([(w0, bot), (w1, bot), (w1 + 120 * s, y + 160 * s), (w0 + 40 * s, y + 160 * s)], "#9ab6d8",
               0.08 * moon, blur=30 * s)
    c.rect(x - 280 * s, y - 250 * s, x + 280 * s, y - 70 * s, wood_d, 0.6)         # wainscot behind the bench
    cx, cy = x, y - 590 * s                                                       # the wall clock
    c.circle(cx, cy, 40 * s, wood_d)
    c.circle(cx, cy, 32 * s, "#c8bea0", 0.75)
    c.line([(cx, cy), (cx + 6 * s, cy - 22 * s)], "#1a1410", max(1.0, 3 * s))
    c.line([(cx, cy), (cx - 16 * s, cy + 8 * s)], "#1a1410", max(1.0, 2.5 * s))
    c.rect(x - 52 * s, y - 520 * s, x + 52 * s, y - 330 * s, wood_d, r=10 * s)    # the high-backed chair
    c.rect(x - 44 * s, y - 510 * s, x + 44 * s, y - 330 * s, "#2a1810", r=8 * s)
    c.rect(x - 240 * s, y - 340 * s, x + 240 * s, y - 318 * s, wood)              # the bench and its panels
    c.rect(x - 230 * s, y - 318 * s, x + 230 * s, y, wood_d)
    for j in range(4):
        px = x - 210 * s + j * 110 * s
        c.rect(px, y - 296 * s, px + 90 * s, y - 40 * s, wood, 0.8)
        c.rect(px + 8 * s, y - 288 * s, px + 82 * s, y - 48 * s, wood_d, 0.9)
    c.rect(x - 240 * s, y - 8 * s, x + 240 * s, y, "#0e0805")
    bx = x + 330 * s                                                              # the witness box
    c.rect(bx - 70 * s, y - 210 * s, bx + 70 * s, y - 196 * s, wood)
    c.rect(bx - 64 * s, y - 196 * s, bx + 64 * s, y, wood_d)
    c.rect(bx - 54 * s, y - 180 * s, bx + 54 * s, y - 24 * s, wood, 0.6)
    c.rect(bx - 30 * s, y - 300 * s, bx + 30 * s, y - 210 * s, wood_d, 0.9, r=6 * s)   # its chair back
    ry = y + 230 * s                                                              # the rail, nearer to us
    c.rect(-20, ry - 150 * s, W + 20, ry - 134 * s, wood)
    for j in range(-1, int(W / (34 * s)) + 2):
        px = j * 34 * s
        c.rect(px, ry - 134 * s, px + 10 * s, ry, wood_d)
    c.rect(-20, ry - 8 * s, W + 20, ry, wood)
    return out


@prop
def brickwall(c, L, x, y, s=1.0, h=360, beam=0.8, aim=-520, lit=True, **k):
    """A tall red-brick prison wall across the picture with a guard picket and its searchlight (see the top)."""
    out = []
    top = y - h * s
    brick, brick_d = "#2a1511", "#190b08"
    c.rect(-20, top, W + 20, y, brick)
    for j in range(int(h / 10) + 1):                                              # courses
        c.line([(-20, y - j * 10 * s), (W + 20, y - j * 10 * s)], brick_d, max(0.6, 1.0 * s), 0.5)
    for px in range(-40, W + 60, int(190 * s)):                                   # pilasters
        c.rect(px, top + 10 * s, px + 30 * s, y, brick_d, 0.85)
    c.rect(-20, top - 14 * s, W + 20, top, "#3a2a24")                             # coping
    c.line([(-20, top - 14 * s), (W + 20, top - 14 * s)], "#6a5a50", max(0.8, 1.4 * s), 0.25)
    pw, ph = 70 * s, 120 * s                                                      # the picket on the wall
    c.rect(x - pw, top - 14 * s - ph, x + pw, top - 14 * s, "#120c0a")
    for q in range(3):                                                            # its windows
        wx = x - pw + 14 * s + q * 44 * s
        c.rect(wx, top - 14 * s - ph + 26 * s, wx + 30 * s, top - 14 * s - ph + 70 * s, "#ffd890" if lit else "#0c0c0e",
               0.75 if lit else 1.0)
    if lit:
        L.rect(x - pw + 14 * s, top - ph + 12 * s, x + pw - 14 * s, top - ph + 56 * s, WARM, 0.35)
        out.append((x, top - ph + 34 * s, (1.0, 0.78, 0.45), 90 * s, True, 0.35))
    c.poly([(x - pw - 16 * s, top - 14 * s - ph), (x, top - 14 * s - ph - 56 * s), (x + pw + 16 * s, top - 14 * s - ph)],
           "#0a0706")                                                             # the roof
    c.rect(x - pw - 18 * s, top - 18 * s, x + pw + 18 * s, top - 12 * s, "#0a0706")   # the walk around it
    for q in range(8):
        px = x - pw - 18 * s + q * (2 * pw + 36 * s) / 7
        c.line([(px, top - 18 * s), (px, top - 40 * s)], "#0a0706", max(0.8, 2 * s))
    c.line([(x - pw - 18 * s, top - 40 * s), (x + pw + 18 * s, top - 40 * s)], "#0a0706", max(0.8, 2 * s))
    if beam > 0:                                                                  # the searchlight
        sx, sy = x + pw + 10 * s, top - 14 * s - ph - 8 * s
        c.circle(sx, sy, 10 * s, "#fff4d0", 0.95)
        ex, ey = x + aim * s, y + 260 * s
        c.poly([(sx, sy - 6 * s), (ex - 160 * s, ey), (ex + 160 * s, ey), (sx, sy + 6 * s)], "#fff2cc", 0.06 * beam,
               blur=18 * s)
        L.poly([(sx, sy - 6 * s), (ex - 130 * s, ey), (ex + 130 * s, ey), (sx, sy + 6 * s)], "#ffe8b0", 0.14 * beam,
               blur=26 * s)
        out.append((sx, sy, (1.0, 0.95, 0.8), 80 * s, False, 0.8 * beam))
    return out
