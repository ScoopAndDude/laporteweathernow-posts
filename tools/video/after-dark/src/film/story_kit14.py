"""Props for the Wanatah Palm Sunday tornado short (April 11, 1965), added Nov. 15, 2026. They register in
story_kit3.PROPS like every prop, so a storyboard names them in "props": [{"p": "tornado", ...}].

    tornado      a tornado funnel from the ground at (x, y) up h px into the cloud base, narrow at the ground (base)
                 and wide at the top (top), leaning lean px, with a dust-and-debris cloud where it touches down
                 (debris=0..1). rope=True draws a thin, bending rope funnel instead
    stormbase    the dark, low base of a storm cloud across the picture, its underside at y, with a lowered wall
                 cloud at x (wall=0..1) and flash= flickering glows of lightning inside the cloud
    rainshaft    grey rain falling from a cloud base at y, h px down to the ground, slanted
    thunderhead  a towering storm cloud far off on the horizon at (x, y), lit on top by the low sun (lit=0..1)
    fields       spring farm fields from the horizon at y down, furrows running to a point at x
    countyroad   a two-lane country road from the bottom of the picture (centred at bx, w wide) to a point at x on
                 the horizon y, with telephone poles along it (poles=True)
    sedan65      a 1960s four-door sedan, side on (flip faces it left)
    photographer a man in a jacket and hat holding a camera to his eye, side on (flip faces left)
    church65     a white frame country church with a steeple, seen from the front, with steps; people= small figures
                 on the lawn, some holding palm fronds (palms=True)
    farmstead    a two-story farmhouse, a red gambrel-roof barn and a silo, with a windbreak of bare trees behind
                 (it's early April) (lit=True: a lamp in one window)
    houses65     a row of small 1940s houses far off (n, spread), a few windows lit, bare trees between them
    brokenbarn   after the storm: a barn with its roof torn open and siding gone, and a snapped tree beside it
    boards       broken boards on the ground (n, spread), or flying through the air (air=True, h)
    wallmap      a weather office's wall map of Indiana with storm marks across the north
    weatherdesk  a 1960s weather office desk with a black rotary telephone, papers and a desk lamp, and a teletype
                 machine beside it with paper curling out
    tvset65      a 1960s console television with rabbit ears, its screen glowing with words (text, two lines split
                 on "|")
    floorlamp    a tall floor lamp with a shade, lit

People are small anonymous silhouettes. Nothing shows a body, an injured person, or a real person's likeness.
"""
import math

import numpy as np

import art
import story_kit3 as K3
from story_kit import W, H
from story_kit8 import _text
from story_kit12 import _mix

prop = K3.prop
INK = "#040405"


def _rng(seed):
    return np.random.default_rng(seed)


# ------------------------------------------------------------------------------------------------- the storm

@prop
def tornado(c, L, x, y, s=1.0, h=480, top=150, base=26, lean=-40, debris=1.0, rope=False, tone="#0b0d0c",
            rim="#5c665e", seed=4, **k):
    """A tornado funnel standing on the ground at (x, y) (see the top of this file)."""
    r = _rng(seed)
    n = 48
    ph = r.uniform(0, 6.28)
    left, right, mids = [], [], []
    for i in range(n + 1):
        t = i / n                                     # 0 at the ground, 1 in the cloud base
        if rope:
            w = (base * 0.45 + (top * 0.3 - base * 0.45) * t ** 3) * s
            cx = x + lean * s * t ** 1.4 + 34 * s * math.sin(t * 4.6 + ph) * (1 - t) ** 0.6
        else:
            w = (base + (top - base) * t ** 2.7) * s * (1 + 0.06 * math.sin(t * 17 + ph))
            cx = x + lean * s * t ** 2 + 9 * s * math.sin(t * 6.5 + ph)
        yy = y - h * s * t
        left.append((cx - w / 2, yy))
        right.append((cx + w / 2, yy))
        mids.append((cx, yy, w))
    body = left + right[::-1]
    c.poly(body, tone, 0.5, blur=12 * s)                                     # the soft outer skin
    c.poly(body, tone, 0.96, blur=2.5 * s)
    c.line(left[3:-4], rim, max(1.0, 3.2 * s), 0.3, blur=2.5 * s)            # light on the western edge
    for j in range(8):                                                       # condensation bands wrapping it
        t = 0.1 + j * 0.105 + r.uniform(-0.025, 0.025)
        i = min(n, int(t * n))
        cx, yy, w = mids[i]
        c.line([(cx - w / 2, yy), (cx, yy + w * 0.09), (cx + w / 2, yy)], "#000000", max(0.8, 2.0 * s), 0.28,
               blur=1.5 * s)
    if debris > 0:                                                           # dust and debris where it touches
        for j in range(20):
            px = x + r.normal(0, 1) * base * 1.7 * s
            py = y - abs(r.normal(0, 1)) * 46 * s
            c.ellipse(px, py, r.uniform(34, 80) * s * debris, r.uniform(18, 40) * s * debris, "#25211b",
                      0.32 * debris, blur=16 * s)
        for j in range(int(70 * debris)):
            t = r.uniform(0.0, 0.42) ** 1.3
            i = min(n, int(t * n))
            cx, yy, w = mids[i]
            a = r.uniform(0, 6.28)
            rad = (w / 2) * r.uniform(1.2, 3.4) + 14 * s
            px = cx + math.cos(a) * rad
            py = yy + math.sin(a) * rad * 0.25
            ln = r.uniform(3, 12) * s
            ang = r.uniform(0, 3.14)
            c.line([(px - ln * math.cos(ang), py - ln * math.sin(ang)),
                    (px + ln * math.cos(ang), py + ln * math.sin(ang))], "#090807", max(0.8, 1.7 * s), 0.85)
    return []


@prop
def stormbase(c, L, x, y, s=1.0, w=1500, tone="#0a0d0d", wall=1.0, flash=2, seed=7, **k):
    """The dark underside of a storm cloud at y, with a lowered wall cloud at x (see the top of this file)."""
    r = _rng(seed)
    for j in range(30):                                                      # the heavy mass above the base
        px = x + r.uniform(-0.55, 0.55) * w * s
        py = y - r.uniform(40, 260) * s
        c.ellipse(px, py, r.uniform(130, 280) * s, r.uniform(60, 130) * s, tone, r.uniform(0.45, 0.8), blur=32 * s)
    for j in range(46):                                                      # a ragged, lumpy underside
        px = x + r.uniform(-0.55, 0.55) * w * s
        py = y - r.uniform(0, 34) * s
        c.ellipse(px, py, r.uniform(40, 120) * s, r.uniform(14, 32) * s, tone, r.uniform(0.4, 0.85), blur=12 * s)
    if wall > 0:                                                             # the lowered, turning wall cloud
        ww = 230 * s
        for j in range(14):
            px = x + r.uniform(-1, 1) * ww * 0.62
            py = y + r.uniform(8, 66) * s * wall
            c.ellipse(px, py, r.uniform(60, 125) * s, r.uniform(22, 46) * s, tone, 0.75, blur=10 * s)
        for j in range(5):
            yy = y + (16 + j * 13) * s * wall
            c.line([(x - ww * 0.72, yy), (x, yy + 7 * s), (x + ww * 0.72, yy)], "#3c4642", max(1.0, 2 * s), 0.12,
                   blur=3 * s)
    for j in range(int(flash)):                                              # lightning lighting the cloud
        px = x + r.uniform(-0.45, 0.45) * w * s
        py = y - r.uniform(70, 180) * s
        c.ellipse(px, py, 230 * s, 120 * s, "#7a8aa6", 0.1, blur=70 * s)
        L.ellipse(px, py, 200 * s, 110 * s, "#9ab0d8", 0.05, blur=70 * s)
    return []


@prop
def rainshaft(c, L, x, y, s=1.0, w=260, h=520, slant=-0.22, a=0.3, seed=5, **k):
    """Rain falling from a cloud base at y to the ground (see the top of this file)."""
    r = _rng(seed)
    hw, dx = w * s / 2, slant * h * s
    c.poly([(x - hw, y), (x + hw, y), (x + hw + dx, y + h * s), (x - hw + dx, y + h * s)], "#283034", a, blur=26 * s)
    for j in range(46):
        px = x + r.uniform(-1, 1) * hw
        c.line([(px, y + r.uniform(0, 40) * s), (px + dx, y + h * s)], "#3a4448", max(0.8, 1.4 * s), a * 0.45,
               blur=2 * s)
    return []


@prop
def thunderhead(c, L, x, y, s=1.0, lit=1.0, tone="#3a3e48", top="#c4a27a", seed=9, **k):
    """A towering storm cloud far off, its base on the horizon at (x, y) (see the top of this file)."""
    r = _rng(seed)
    hh = 600 * s
    for j in range(60):                                                      # the tower: cauliflower puffs
        t = r.uniform(0, 1) ** 0.8
        py = y - 60 * s - t * hh
        wid = (330 - 120 * t) * s
        px = x + r.uniform(-0.5, 0.5) * wid + 30 * s * t
        col = _mix(tone, top, min(1.0, max(0.0, t * 1.1 - 0.15)) * lit)
        rr = r.uniform(60, 110) * s * (1.1 - 0.4 * t)
        c.circle(px, py, rr, col, 0.9, blur=8 * s)
        c.circle(px - rr * 0.3, py - rr * 0.3, rr * 0.6, _mix(col, "#ffe8c8", 0.25 * lit), 0.35, blur=10 * s)
    for j in range(30):                                                      # the anvil spreading downwind
        t = j / 29
        px = x + (-140 + t * 760) * s
        py = y - hh - 40 * s + r.uniform(-14, 14) * s + t * 30 * s
        c.ellipse(px, py, r.uniform(80, 140) * s, r.uniform(26, 40) * s * (1 - 0.5 * t), _mix(tone, top, 0.75 * lit),
                  0.85 - 0.5 * t, blur=12 * s)
    c.ellipse(x + 10 * s, y - 50 * s, 300 * s, 70 * s, "#1c1e24", 0.9, blur=18 * s)                      # dark base
    c.poly([(x - 150 * s, y - 40 * s), (x + 110 * s, y - 40 * s), (x + 70 * s, y), (x - 190 * s, y)], "#20242a", 0.55,
           blur=16 * s)                                                                                  # its rain
    return []


# ------------------------------------------------------------------------------------------------- the land

@prop
def fields(c, L, x, y, s=1.0, rows=18, color="#12160e", furrow="#000000", wheat="#1c2814", **k):
    """Spring farm fields from the horizon at y down, furrows running to a point at x."""
    c.poly([(-20, y), (W + 20, y), (W + 20, H), (-20, H)], color)
    c.poly([(-20, y), (W + 20, y), (W + 20, y + 46 * s), (-20, y + 46 * s)], wheat, 0.8)   # a green field far off
    for j in range(rows + 1):
        fx = -1100 + j * (3280 / rows)
        c.line([(x, y + 46 * s), (fx, H)], furrow, max(1.0, 2.4 * s), 0.32)
    for yy in (y, y + 46 * s, y + 150 * s):
        c.line([(-20, yy), (W + 20, yy)], "#000000", max(1.0, 2 * s), 0.3)
    return []


@prop
def countyroad(c, L, x, y, s=1.0, w=560, bx=280, poles=True, color="#18191a", **k):
    """A two-lane road from the bottom of the picture to a point at x on the horizon y (see the top of this file)."""
    hw = w / 2
    c.poly([(x - 3, y), (x + 3, y), (bx + hw, H + 10), (bx - hw, H + 10)], color)
    c.line([(x - 3, y), (bx - hw, H + 10)], "#2e2c28", max(1.0, 3 * s), 0.6)
    c.line([(x + 3, y), (bx + hw, H + 10)], "#2e2c28", max(1.0, 3 * s), 0.6)
    for j in range(16):                                                      # the centre line
        t0, t1 = (j / 16) ** 1.7, ((j + 0.45) / 16) ** 1.7
        p0 = (x + (bx - x) * t0, y + (H - y) * t0)
        p1 = (x + (bx - x) * t1, y + (H - y) * t1)
        c.line([p0, p1], "#7a6c3a", max(0.6, 7 * s * t1), 0.5)
    if poles:
        tops = []
        for j in range(8):
            t = 0.015 + (j / 8) ** 1.8 * 0.98
            px = x + 14 + (bx + hw + 150 - x - 14) * t
            py = y + (H - y) * t
            ph = (16 + 760 * t) * s
            wd = max(1.0, 11 * s * t + 1)
            c.line([(px, py), (px, py - ph)], "#040404", wd)
            arm = (6 + 46 * t) * s
            c.line([(px - arm, py - ph * 0.94), (px + arm, py - ph * 0.94)], "#040404", max(1.0, wd * 0.5))
            tops.append((px, py - ph * 0.94, arm))
        for (ax, ay, aa), (bx2, by, ba) in zip(tops, tops[1:]):             # wires sagging between them
            for side in (-1, 1):
                p0, p1 = (ax + side * aa * 0.8, ay), (bx2 + side * ba * 0.8, by)
                mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + abs(p1[0] - p0[0]) * 0.06 + 4)
                c.line([p0, mid, p1], "#050505", max(0.6, 1.2 * s), 0.7)
    return []


@prop
def sedan65(c, L, x, y, s=1.0, flip=False, color="#262a30", **k):
    """A 1960s four-door sedan, side on (see the top of this file)."""
    f = -1 if flip else 1

    def P(pts):
        return [(x + f * px * s, y + py * s) for px, py in pts]
    body = [(-258, -36), (-264, -70), (-256, -102), (-236, -114), (-204, -104), (-130, -104), (-104, -166),
            (58, -170), (122, -110), (250, -98), (264, -78), (260, -36)]
    c.poly(P(body), color)
    c.poly(P([(-112, -110), (-92, -158), (54, -161), (110, -110)]), "#0c1014")                    # the glass
    c.line(P([(-22, -162), (-26, -108)]), color, max(1.0, 7 * s))                                 # door pillar
    c.line(P([(-252, -72), (256, -72)]), "#8a9098", max(0.8, 2.4 * s), 0.55)                       # chrome strip
    c.line(P([(-236, -114), (-130, -104)]), "#9aa0a8", max(0.6, 1.6 * s), 0.35)                    # the fin's edge
    c.line(P([(-30, -104), (-30, -40)]), "#000000", max(0.6, 1.4 * s), 0.4)                        # door seams
    c.line(P([(100, -100), (100, -40)]), "#000000", max(0.6, 1.4 * s), 0.4)
    hx0, hx1 = sorted((x + f * 250 * s, x + f * 262 * s))
    c.rect(hx0, y - 84 * s, hx1, y - 70 * s, "#c8c0a0", 0.5)                                       # headlamp
    tx0, tx1 = sorted((x - f * 262 * s, x - f * 250 * s))
    c.rect(tx0, y - 96 * s, tx1, y - 80 * s, "#5a1410", 0.9)                                       # tail lamp
    for wx in (-168, 170):                                                                        # wheels
        cx = x + f * wx * s
        c.circle(cx, y - 32 * s, 44 * s, "#030303")
        c.circle(cx, y - 32 * s, 34 * s, "#0a0a0a")
        c.circle(cx, y - 32 * s, 17 * s, "#6a6e74", 0.7)
    c.line([(x - 270 * s, y - 34 * s), (x + 270 * s, y - 34 * s)], "#7a8088", max(0.8, 3 * s), 0.5)  # bumpers
    return []


@prop
def photographer(c, L, x, y, s=1.0, flip=False, color=INK, **k):
    """A man in a jacket and hat holding a camera to his eye, side on (see the top of this file)."""
    f = -1 if flip else 1

    def P(pts):
        return [(x + f * px * s, y + py * s) for px, py in pts]
    c.poly(P([(-14, 0), (-10, -78), (10, -78), (14, 0), (6, 0), (0, -50), (-6, 0)]), color)        # legs
    c.poly(P([(-24, -74), (-26, -128), (-16, -150), (16, -150), (24, -128), (22, -74)]), color)   # jacket
    c.circle(x + f * 2 * s, y - 166 * s, 15 * s, color)                                          # head
    c.poly(P([(-16, -176), (-12, -190), (14, -190), (18, -176)]), color)                         # hat
    c.line(P([(-26, -176), (28, -176)]), color, max(1.0, 4 * s))                                 # its brim
    c.poly(P([(10, -150), (30, -150), (26, -160), (12, -160)]), color)                           # arms raised
    c.line(P([(16, -146), (30, -160)]), color, max(1.0, 9 * s))
    cx0, cx1 = sorted((x + f * 20 * s, x + f * 46 * s))
    c.rect(cx0, y - 176 * s, cx1, y - 154 * s, "#0c0c0e")                                          # the camera
    c.circle(x + f * 48 * s, y - 165 * s, 6 * s, "#2a2e34")
    return []


@prop
def church65(c, L, x, y, s=1.0, people=10, palms=True, lit=False, seed=3, wall="#a8a294", **k):
    """A white frame country church with a steeple, from the front (see the top of this file)."""
    r = _rng(seed)
    nw, nh = 170 * s, 200 * s
    c.poly([(x - nw, y), (x - nw, y - nh), (x, y - nh - 120 * s), (x + nw, y - nh), (x + nw, y)], wall)  # the nave
    c.poly([(x - nw - 14 * s, y - nh + 6 * s), (x, y - nh - 132 * s), (x + nw + 14 * s, y - nh + 6 * s),
            (x + nw, y - nh), (x, y - nh - 120 * s), (x - nw, y - nh)], "#24201c")              # the roof edge
    for j in range(1, 9):                                                    # clapboards
        yy = y - j * nh / 9
        c.line([(x - nw, yy), (x + nw, yy)], "#000000", max(0.6, 1.0 * s), 0.1)
    tw = 46 * s                                                              # the steeple
    c.rect(x - tw, y - nh - 150 * s, x + tw, y, wall)
    c.rect(x - tw, y - nh - 150 * s, x + tw, y, "#ffffff", 0.06)
    c.rect(x - tw - 6 * s, y - nh - 156 * s, x + tw + 6 * s, y - nh - 146 * s, "#24201c")
    c.rect(x - 28 * s, y - nh - 140 * s, x + 28 * s, y - nh - 96 * s, "#141210")                    # belfry opening
    c.poly([(x - tw - 4 * s, y - nh - 156 * s), (x, y - nh - 330 * s), (x + tw + 4 * s, y - nh - 156 * s)], "#24201c")
    c.line([(x, y - nh - 330 * s), (x, y - nh - 380 * s)], "#24201c", max(1.0, 5 * s))           # the cross
    c.line([(x - 16 * s, y - nh - 362 * s), (x + 16 * s, y - nh - 362 * s)], "#24201c", max(1.0, 5 * s))
    c.poly([(x - 22 * s, y), (x - 22 * s, y - 70 * s), (x, y - 92 * s), (x + 22 * s, y - 70 * s), (x + 22 * s, y)],
           "#2a1c14")                                                        # the door
    for wx in (-112, 112):                                                   # arched windows
        cx = x + wx * s
        c.poly([(cx - 20 * s, y - 50 * s), (cx - 20 * s, y - 136 * s), (cx, y - 158 * s), (cx + 20 * s, y - 136 * s),
                (cx + 20 * s, y - 50 * s)], "#ffd890" if lit else "#1a1e22", 0.9)
        if lit:
            L.circle(cx, y - 104 * s, 40 * s, "#ffcf80", 0.4)
    c.rect(x - 60 * s, y, x + 60 * s, y + 10 * s, "#6a665c")                                       # steps
    c.rect(x - 74 * s, y + 10 * s, x + 74 * s, y + 20 * s, "#5a564e")
    c.poly([(x - nw, y - nh), (x - nw, y), (x - nw + 10 * s, y), (x - nw + 10 * s, y - nh)], "#ffe8c0", 0.18)  # sun
    for j in range(int(people)):                                             # people on the lawn
        px = x + r.choice([-1, 1]) * r.uniform(90, 330) * s
        py = y + r.uniform(30, 90) * s
        ps = r.uniform(0.55, 0.75) * s
        hh = 110 * ps
        c.poly([(px - 9 * ps, py), (px - 12 * ps, py - hh * 0.62), (px - 7 * ps, py - hh * 0.82),
                (px + 7 * ps, py - hh * 0.82), (px + 12 * ps, py - hh * 0.62), (px + 9 * ps, py)], INK)
        c.circle(px, py - hh * 0.9, 9 * ps, INK)
        if palms and r.random() < 0.5:                                       # a palm frond held up
            fx, fy = px + 12 * ps, py - hh * 0.6
            tip = (fx + r.uniform(4, 16) * ps, fy - 46 * ps)
            c.line([(fx, fy), tip], "#2a3a1c", max(1.0, 3 * ps))
            for q in range(5):
                t = 0.35 + q * 0.13
                bx, by = fx + (tip[0] - fx) * t, fy + (tip[1] - fy) * t
                c.line([(bx, by), (bx - 10 * ps, by - 4 * ps)], "#2e4220", max(0.8, 2 * ps))
                c.line([(bx, by), (bx + 10 * ps, by - 4 * ps)], "#2e4220", max(0.8, 2 * ps))
    return []


@prop
def farmstead(c, L, x, y, s=1.0, lit=False, flip=False, seed=5, wall="#6c675c", barn="#4e1c15", **k):
    """A farmhouse, a gambrel-roof barn and a silo, with a windbreak (see the top of this file)."""
    r = _rng(seed)
    f = -1 if flip else 1
    out = []
    for j in range(6):                                                       # the windbreak behind, still bare
        px = x + f * (-340 + j * 56 + r.uniform(-12, 12)) * s                # in early April
        art.tree(c, px, y, r.uniform(250, 330) * s, seed=seed * 7 + j, color="#050706", depth=6, spread=0.62)
    hx = x - f * 150 * s                                                     # the house
    hw, hh = 100 * s, 170 * s
    c.rect(hx - hw, y - hh, hx + hw, y, wall)
    c.poly([(hx - hw - 10 * s, y - hh), (hx, y - hh - 92 * s), (hx + hw + 10 * s, y - hh)], "#1c1c1a")
    c.rect(hx + 40 * s, y - hh - 90 * s, hx + 62 * s, y - hh - 30 * s, "#1c1c1a")                    # chimney
    c.rect(hx - hw - 6 * s, y - 78 * s, hx + hw + 6 * s, y - 68 * s, "#1c1c1a")                      # porch roof
    for px in (-90, -30, 30, 90):
        c.line([(hx + px * s, y - 68 * s), (hx + px * s, y)], "#2a2824", max(1.0, 4 * s))
    for wx, wy in ((-50, -140), (50, -140), (-56, -48), (56, -48)):
        lamp = lit and (wx, wy) == (-56, -48)
        c.rect(hx + (wx - 16) * s, y + (wy - 22) * s, hx + (wx + 16) * s, y + (wy + 22) * s,
               "#ffcf80" if lamp else "#121416", 0.95)
        if lamp:
            L.circle(hx + wx * s, y + wy * s, 30 * s, "#ffcf80", 0.5)
            out.append((hx + wx * s, y + wy * s, (1.0, 0.82, 0.5), 70 * s, False))
    bx = x + f * 120 * s                                                     # the barn
    bw, bh = 140 * s, 150 * s
    c.rect(bx - bw, y - bh, bx + bw, y, barn)
    c.poly([(bx - bw - 8 * s, y - bh), (bx - bw + 46 * s, y - bh - 80 * s), (bx, y - bh - 120 * s),
            (bx + bw - 46 * s, y - bh - 80 * s), (bx + bw + 8 * s, y - bh)], "#1a1210")
    for j in range(1, 14):
        c.line([(bx - bw + j * 2 * bw / 14, y - bh), (bx - bw + j * 2 * bw / 14, y)], "#000000", max(0.6, 1.0 * s),
               0.18)
    c.rect(bx - 54 * s, y - 120 * s, bx + 54 * s, y, "#3a140f")                                     # the big doors
    for d in (-1, 1):
        x0, x1 = bx + d * 54 * s, bx
        c.line([(x0, y - 120 * s), (x1, y)], "#8a7a6a", max(0.8, 2.4 * s), 0.35)
        c.line([(x0, y), (x1, y - 120 * s)], "#8a7a6a", max(0.8, 2.4 * s), 0.35)
    c.rect(bx - 20 * s, y - bh - 60 * s, bx + 20 * s, y - bh - 20 * s, "#140c0a")                  # hay door
    sx = x + f * 330 * s                                                     # the silo
    c.rect(sx - 34 * s, y - 330 * s, sx + 34 * s, y, "#5e5e58")
    c.ellipse(sx, y - 330 * s, 34 * s, 26 * s, "#3a3a36")
    for j in range(1, 9):
        c.line([(sx - 34 * s, y - j * 36 * s), (sx + 34 * s, y - j * 36 * s)], "#000000", max(0.6, 1.2 * s), 0.25)
    return out


@prop
def houses65(c, L, x, y, s=1.0, n=6, spread=560, seed=8, lit=0.5, **k):
    """A row of small 1940s houses far off, a few windows lit (see the top of this file)."""
    r = _rng(seed)
    out = []
    for j in range(int(n)):
        px = x - spread * s / 2 + (j + 0.5) * spread * s / n + r.uniform(-8, 8) * s
        w, hh = r.uniform(34, 44) * s, r.uniform(26, 32) * s
        c.rect(px - w, y - hh, px + w, y, "#0b0d0e")
        c.poly([(px - w - 5 * s, y - hh), (px, y - hh - 24 * s), (px + w + 5 * s, y - hh)], "#060708")
        if r.random() < lit:
            wx = px + r.uniform(-0.5, 0.5) * w
            c.rect(wx - 6 * s, y - hh * 0.75, wx + 6 * s, y - hh * 0.35, "#ffcc80", 0.9)
            out.append((wx, y - hh * 0.55, (1.0, 0.8, 0.5), 26 * s, False))
    for j in range(int(n)):                                                  # bare yard trees
        px = x + r.uniform(-0.55, 0.55) * spread * s
        art.tree(c, px, y, r.uniform(60, 90) * s, seed=seed * 5 + j, color="#050706", depth=5, spread=0.6)
    return out


@prop
def brokenbarn(c, L, x, y, s=1.0, flip=False, color="#3e1812", seed=11, **k):
    """After the storm: a barn with its roof torn open, and a snapped tree (see the top of this file)."""
    r = _rng(seed)
    f = -1 if flip else 1
    bw, bh = 150 * s, 160 * s
    x0, x1 = x - f * bw, x + f * bw
    c.poly([(x0, y), (x0, y - bh), (x0 + f * 50 * s, y - bh - 82 * s), (x, y - bh - 124 * s), (x, y)], color)
    c.poly([(x, y), (x, y - bh + 30 * s), (x + f * 60 * s, y - bh + 70 * s), (x + f * 110 * s, y - 70 * s),
            (x1, y - 50 * s), (x1, y)], color)                                # the torn side, siding gone above
    c.poly([(x0 - f * 8 * s, y - bh), (x0 + f * 50 * s, y - bh - 82 * s), (x, y - bh - 124 * s),
            (x + f * 16 * s, y - bh - 116 * s), (x0 + f * 56 * s, y - bh - 72 * s), (x0 + f * 4 * s, y - bh + 4 * s)],
           "#160e0c")                                                        # what's left of the roof
    for j in range(6):                                                       # bare rafters
        t = (j + 1) / 7
        rx = x + f * t * bw
        top = y - bh - 124 * s + t * (60 * s)
        c.line([(rx, top + r.uniform(0, 20) * s), (rx + f * r.uniform(-6, 6) * s, y - bh + 40 * s * t)], "#120c0a",
               max(1.0, 5 * s))
    c.line([(x, y - bh - 124 * s), (x1 - f * 20 * s, y - bh - 60 * s)], "#120c0a", max(1.0, 6 * s))
    for j in range(1, 10):
        c.line([(x0 + f * j * bw / 10, y - bh), (x0 + f * j * bw / 10, y)], "#000000", max(0.6, 1 * s), 0.2)
    dx0, dx1 = sorted((x0 + f * 40 * s, x0 + f * 110 * s))
    c.rect(dx0, y - 110 * s, dx1, y, "#160a08")                                                     # open door
    tx = x1 + f * 170 * s                                                    # the snapped tree
    c.poly([(tx - 16 * s, y), (tx - 12 * s, y - 210 * s), (tx - 2 * s, y - 236 * s), (tx + 4 * s, y - 214 * s),
            (tx + 14 * s, y - 226 * s), (tx + 16 * s, y)], "#070605")
    c.poly([(tx + f * 20 * s, y - 6 * s), (tx + f * 280 * s, y - 30 * s), (tx + f * 290 * s, y - 12 * s),
            (tx + f * 24 * s, y + 6 * s)], "#070605")                        # its top, on the ground
    for j in range(7):                                                       # its broken limbs
        px = tx + f * r.uniform(60, 280) * s
        c.line([(px, y - 18 * s), (px + r.uniform(-30, 30) * s, y - r.uniform(40, 90) * s)], "#070605",
               max(1.0, 4 * s))
    return []


@prop
def boards(c, L, x, y, s=1.0, n=20, spread=560, air=False, h=380, color="#2a1c14", seed=12, **k):
    """Broken boards on the ground, or flying (see the top of this file)."""
    r = _rng(seed)
    for j in range(int(n)):
        px = x + r.uniform(-0.5, 0.5) * spread * s
        py = y - (r.uniform(20, h) * s if air else r.uniform(-30, 20) * s)
        ln = r.uniform(30, 80) * s * (0.6 if air else 1.0)
        a = r.uniform(0, 3.14) if air else r.uniform(-0.35, 0.35)
        c.line([(px - ln / 2 * math.cos(a), py - ln / 2 * math.sin(a)), (px + ln / 2 * math.cos(a), py + ln / 2 * math.sin(a))],
               color if not air else "#0a0806", max(1.0, r.uniform(4, 8) * s * (0.6 if air else 1.0)))
    return []


# ------------------------------------------------------------------------------------------------- indoors

_INDIANA = [(-87.53, 41.76), (-84.81, 41.76), (-84.81, 39.10), (-85.00, 38.75), (-85.40, 38.73), (-85.60, 38.45),
            (-85.90, 38.25), (-86.10, 38.00), (-86.30, 38.15), (-86.50, 37.95), (-86.80, 37.98), (-87.10, 37.78),
            (-87.40, 37.93), (-87.60, 37.83), (-87.90, 37.90), (-88.05, 37.82), (-87.95, 38.10), (-87.75, 38.30),
            (-87.55, 38.60), (-87.50, 38.90), (-87.60, 39.20), (-87.53, 39.35)]


@prop
def wallmap(c, L, x, y, s=1.0, marks=True, **k):
    """A weather office's wall map of Indiana, centred on (x, y) (see the top of this file)."""
    mw, mh = 230 * s, 300 * s
    c.rect(x - mw - 10 * s, y - mh - 10 * s, x + mw + 10 * s, y + mh + 10 * s, "#2a1c12")            # frame
    c.rect(x - mw, y - mh, x + mw, y + mh, "#6e6858")                                               # paper
    for j in range(1, 8):
        c.line([(x - mw, y - mh + j * mh / 4), (x + mw, y - mh + j * mh / 4)], "#000000", 1, 0.08)
        c.line([(x - mw + j * mw / 4, y - mh), (x - mw + j * mw / 4, y + mh)], "#000000", 1, 0.08)
    sc = 1.7 * mh / 4.1
    cx0 = x - (88.1 - 86.45) * 0.766 * sc

    def P(lon, lat):
        return (cx0 + (lon + 88.1) * 0.766 * sc, y - mh * 0.85 + (41.76 - lat) * sc)
    pts = [P(lo, la) for lo, la in _INDIANA]
    c.poly(pts, "#b8ae92")
    c.line(pts + [pts[0]], "#1a120c", max(1.0, 4 * s), 0.95)
    for j in range(1, 6):                                                    # faint county lines
        lat = 41.76 - j * 0.66
        c.line([P(-87.53, lat), P(-84.81, lat)], "#2a2018", 1, 0.15)
    if marks:
        for lo, la in ((-86.95, 41.42), (-86.70, 41.30), (-86.45, 41.45), (-86.10, 41.55), (-85.80, 41.60),
                       (-85.95, 41.30), (-86.30, 40.40), (-85.65, 40.55), (-85.00, 40.70)):
            px, py = P(lo, la)
            c.line([(px - 7 * s, py - 7 * s), (px + 7 * s, py + 7 * s)], "#7a1410", max(1.0, 3.2 * s))
            c.line([(px - 7 * s, py + 7 * s), (px + 7 * s, py - 7 * s)], "#7a1410", max(1.0, 3.2 * s))
    _text(c, "INDIANA", x, y + mh * 0.86, 26 * s, "#2a2018")
    return []


@prop
def weatherdesk(c, L, x, y, s=1.0, lamp=True, **k):
    """A 1960s weather office desk with a rotary telephone, and a teletype beside it (see the top of this file)."""
    out = []
    dt = y - 250 * s                                                         # the desk
    c.rect(x - 280 * s, dt, x + 200 * s, dt + 22 * s, "#3a2616")
    c.rect(x - 268 * s, dt + 22 * s, x - 120 * s, y, "#2a1a0e")
    c.rect(x + 60 * s, dt + 22 * s, x + 188 * s, y, "#2a1a0e")
    for j in range(3):
        yy = dt + 40 * s + j * 64 * s
        c.rect(x - 256 * s, yy, x - 132 * s, yy + 52 * s, "#000000", 0.18)
        c.rect(x - 206 * s, yy + 22 * s, x - 182 * s, yy + 28 * s, "#8a7a5a", 0.6)
    c.rect(x - 60 * s, dt - 4 * s, x + 50 * s, dt, "#c8c0a8", 0.8)                                 # papers
    c.rect(x - 40 * s, dt - 8 * s, x + 64 * s, dt - 4 * s, "#bab29a", 0.8)
    px, py = x - 170 * s, dt                                                 # the rotary telephone
    c.poly([(px - 50 * s, py), (px - 40 * s, py - 44 * s), (px + 40 * s, py - 44 * s), (px + 50 * s, py)], "#050505")
    c.ellipse(px, py - 30 * s, 22 * s, 9 * s, "#1c1c1c")
    c.ellipse(px, py - 30 * s, 9 * s, 4 * s, "#3a3a3a")
    c.poly([(px - 62 * s, py - 52 * s), (px - 56 * s, py - 66 * s), (px + 56 * s, py - 66 * s), (px + 62 * s, py - 52 * s),
            (px + 40 * s, py - 46 * s), (px - 40 * s, py - 46 * s)], "#050505")   # the handset in its cradle
    c.line([(px + 50 * s, py - 6 * s), (px + 80 * s, py + 6 * s), (px + 110 * s, py + 40 * s)], "#050505",
           max(1.0, 3 * s))                                                  # its cord
    if lamp:                                                                 # a desk lamp
        lx = x + 150 * s
        c.rect(lx - 30 * s, dt - 8 * s, lx + 30 * s, dt, "#141414")
        c.line([(lx, dt - 8 * s), (lx - 10 * s, dt - 110 * s), (lx - 60 * s, dt - 150 * s)], "#141414", max(1.0, 5 * s))
        c.poly([(lx - 100 * s, dt - 130 * s), (lx - 66 * s, dt - 176 * s), (lx - 30 * s, dt - 140 * s)], "#1a1a1a")
        L.ellipse(lx - 60 * s, dt - 20 * s, 120 * s, 40 * s, "#ffcf80", 0.25, blur=30 * s)
        out.append((lx - 66 * s, dt - 128 * s, (1.0, 0.85, 0.55), 70 * s, False))
    tx = x + 330 * s                                                         # the teletype on its stand
    c.rect(tx - 70 * s, y - 230 * s, tx + 70 * s, y, "#1e2022")
    c.rect(tx - 96 * s, y - 330 * s, tx + 96 * s, y - 230 * s, "#3a3e40")
    c.rect(tx - 96 * s, y - 330 * s, tx + 96 * s, y - 318 * s, "#5a5e60", 0.6)
    c.rect(tx - 80 * s, y - 258 * s, tx + 80 * s, y - 238 * s, "#141618")                         # its keyboard
    for j in range(10):
        c.circle(tx - 70 * s + j * 15.5 * s, y - 248 * s, 4 * s, "#8a8e90", 0.6)
    c.poly([(tx - 50 * s, y - 330 * s), (tx - 46 * s, y - 420 * s), (tx - 10 * s, y - 446 * s), (tx + 40 * s, y - 430 * s),
            (tx + 50 * s, y - 330 * s)], "#d8d0b8", 0.85)                      # paper rising out of it
    for j in range(6):
        yy = y - 344 * s - j * 14 * s
        c.line([(tx - 40 * s, yy), (tx + (10 + 20 * (j % 2)) * s, yy)], "#000000", max(0.6, 1.4 * s), 0.4)
    c.poly([(tx + 50 * s, y - 330 * s), (tx + 90 * s, y - 300 * s), (tx + 110 * s, y - 200 * s), (tx + 96 * s, y - 120 * s),
            (tx + 80 * s, y - 200 * s), (tx + 66 * s, y - 290 * s)], "#ccc4ac", 0.8)    # and curling down
    return out


@prop
def tvset65(c, L, x, y, s=1.0, text="TORNADO|WATCH", glow=0.8, **k):
    """A 1960s console television, its screen glowing with words (see the top of this file)."""
    out = []
    cw, ch = 230 * s, 300 * s
    top = y - 46 * s - ch
    for lx in (-200, 200):                                                   # legs
        c.line([(x + lx * s, y - 46 * s), (x + lx * 1.06 * s, y)], "#1a1008", max(1.0, 8 * s))
    c.rect(x - cw, top, x + cw, y - 46 * s, "#3a2414", r=10 * s)                                   # the cabinet
    c.rect(x - cw, top, x + cw, top + 10 * s, "#5a3a20", 0.6)
    sx0, sx1, sy0, sy1 = x - cw + 26 * s, x + 70 * s, top + 30 * s, y - 76 * s
    c.rect(sx0 - 8 * s, sy0 - 8 * s, sx1 + 8 * s, sy1 + 8 * s, "#0a0a0a", r=26 * s)
    c.rect(sx0, sy0, sx1, sy1, "#262e34", r=22 * s)                                                # the screen
    c.rect(sx0, sy0, sx1, sy1, "#7a92a6", 0.22 * glow, blur=14 * s, r=22 * s)
    lines = text.split("|")
    mx, my = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    for j, ln in enumerate(lines):                                           # white letters on the bulletin
        _text(c, ln, mx, my + (j - (len(lines) - 1) / 2) * 52 * s, 46 * s, "#e8eef2")
    for j in range(14):                                                      # the speaker grille
        yy = sy0 + 10 * s + j * 14 * s
        c.line([(x + 96 * s, yy), (x + cw - 24 * s, yy)], "#000000", max(0.6, 3 * s), 0.5)
    for j in range(2):                                                       # knobs
        c.circle(x + 160 * s, sy1 - 30 * s - j * 46 * s, 13 * s, "#c8b890", 0.8)
    ax, ay = x - 40 * s, top                                                 # rabbit ears
    c.ellipse(ax, ay - 8 * s, 34 * s, 10 * s, "#141414")
    c.line([(ax - 6 * s, ay - 12 * s), (ax - 110 * s, ay - 200 * s)], "#8a8e90", max(1.0, 3 * s))
    c.line([(ax + 6 * s, ay - 12 * s), (ax + 90 * s, ay - 210 * s)], "#8a8e90", max(1.0, 3 * s))
    L.rect(sx0, sy0, sx1, sy1, "#9ab4d0", 0.16 * glow, blur=40 * s)
    L.ellipse(x, y + 30 * s, 300 * s, 60 * s, "#8aa4c4", 0.12 * glow, blur=40 * s)              # its light on the floor
    return out


@prop
def floorlamp(c, L, x, y, s=1.0, lit=True, **k):
    """A tall floor lamp with a shade (see the top of this file)."""
    c.ellipse(x, y - 4 * s, 46 * s, 10 * s, "#141414")
    c.line([(x, y - 6 * s), (x, y - 430 * s)], "#1a1a1a", max(1.0, 6 * s))
    c.poly([(x - 50 * s, y - 420 * s), (x - 34 * s, y - 500 * s), (x + 34 * s, y - 500 * s), (x + 50 * s, y - 420 * s)],
           "#c8a870" if lit else "#3a3022", 0.9)
    out = []
    if lit:
        L.circle(x, y - 450 * s, 70 * s, "#ffcf80", 0.25)
        out.append((x, y - 440 * s, (1.0, 0.82, 0.5), 80 * s, False))
    return out
