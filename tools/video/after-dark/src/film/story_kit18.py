"""Props for the Kingsford Heights short (the wartime town built for Kingsbury Ordnance Plant workers, where most of
the houses stood empty), added Nov. 16, 2026 (as story_kit18: City West's kit took the number 16 the same morning). They register in story_kit3.PROPS like every prop, so a
storyboard names them in "props": [{"p": "bungalows", ...}].

    bungalows   a curving street of small one-storey 1940s houses, all alike, running from the near end (nx, ny) to a
                point x on the horizon y. lit = the share of houses with a lit window (0.05 reads as "almost no one
                home"); gaps = the share of lots left empty; trees = yard trees (0 for a brand-new town); side =
                "both" | "left" | "right"; curve bends the street (negative bends it the other way); new=True draws
                bare raw-wood houses with no lights (a town still going up)
    ringplan    the town plan seen from the air, tilted: curved streets in rings around a town centre at (x, y), with
                rows of tiny house roofs along them and a few radial streets (rings, r0 inner radius, dr ring spacing,
                squash = how flat the tilt makes the rings, gap = the opening in the rings in degrees, lit = lit share)
    housecrate  a small prefab house taken apart for shipping: wall panels with window openings stacked on skids, a
                roof section beside them, crate slats (no people)

Nothing shows a body, a real person's likeness, a brand or any lettering.
"""
import math

import numpy as np

import art
import story_kit3 as K3
from story_kit import W, H

prop = K3.prop
WARM = K3.WARM


def _rng(seed):
    return np.random.default_rng(seed)


def _bez(p0, p1, p2, t):
    a = (1 - t) ** 2
    b = 2 * (1 - t) * t
    d = t * t
    return (a * p0[0] + b * p1[0] + d * p2[0], a * p0[1] + b * p1[1] + d * p2[1])


def _bez_d(p0, p1, p2, t):
    return (2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0]),
            2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1]))


def _t_at_y(p0, p1, p2, yy):
    lo, hi = 0.0, 1.0                     # the curve's y falls from p0 (near) to p2 (horizon)
    for _ in range(40):
        mid = (lo + hi) / 2
        if _bez(p0, p1, p2, mid)[1] > yy:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _house(c, L, hx, hy, sc, r, lit, new=False, wall="#2a2e35", roof="#121418", rim="#7d8796"):
    """One small side-gabled 1940s house, front to the viewer, bottom centre at (hx, hy)."""
    w, h = 210 * sc, 92 * sc
    rh = 58 * sc
    ov = 12 * sc
    if new:
        wall, roof, rim = "#4a3e30", "#2c241c", "#9a8a72"
    top = hy - h
    c.rect(hx - w / 2, top, hx + w / 2, hy, wall)
    c.poly([(hx - w / 2 - ov, top), (hx - w / 2 + rh * 1.1, top - rh), (hx + w / 2 - rh * 1.1, top - rh),
            (hx + w / 2 + ov, top)], roof)
    if sc > 0.12:
        c.line([(hx - w / 2 - ov, top), (hx - w / 2 + rh * 1.1, top - rh), (hx + w / 2 - rh * 1.1, top - rh)],
               rim, max(0.8, 2.2 * sc), 0.35)
    if r.random() < 0.6:                                                     # a stubby chimney
        cx = hx + r.uniform(-0.25, 0.25) * w
        c.rect(cx - 9 * sc, top - rh * 0.8 - 18 * sc, cx + 9 * sc, top - rh * 0.55, roof)
    dx = hx + r.choice([-0.18, 0.0, 0.18]) * w                               # the door
    c.rect(dx - 15 * sc, hy - 60 * sc, dx + 15 * sc, hy, "#08090b")
    c.rect(dx - 24 * sc, hy - 6 * sc, dx + 24 * sc, hy, "#3a3c3e", 0.8)      # the stoop
    out = []
    on = (not new) and r.random() < lit
    which = r.integers(0, 2)
    for j, side in enumerate((-1, 1)):                                       # two windows
        wx = hx + side * w * 0.30
        x0, x1 = wx - 22 * sc, wx + 22 * sc
        y0, y1 = hy - 70 * sc, hy - 34 * sc
        if new:
            c.rect(x0, y0, x1, y1, "#16120e")
            continue
        lit_here = on and j == which
        c.rect(x0, y0, x1, y1, "#ffcc80" if lit_here else "#07080a", 0.95 if lit_here else 1.0)
        if lit_here:
            L.rect(x0, y0, x1, y1, WARM, 0.7)
            out.append((wx, (y0 + y1) / 2, (1.0, 0.78, 0.45), max(10.0, 46 * sc), False))
        c.line([(wx, y0), (wx, y1)], "#000000", max(0.6, 1.6 * sc), 0.6)
    if new:                                                                  # raw studs showing
        for j in range(1, 8):
            c.line([(hx - w / 2 + j * w / 8, top), (hx - w / 2 + j * w / 8, hy)], "#2a2016", max(0.6, 1.4 * sc), 0.5)
    return out


@prop
def bungalows(c, L, x, y, s=1.0, nx=260, ny=1500, n=10, lit=0.08, gaps=0.0, trees=0.0, side="both", curve=0.35,
              street=True, new=False, seed=7, **k):
    """A curving street of small one-storey 1940s houses (see the top of this file)."""
    r = _rng(seed)
    p0, p2 = (nx, ny), (x, y)
    mx, my = (p0[0] + p2[0]) / 2, (p0[1] + p2[1]) / 2
    p1 = (mx + curve * (p2[1] - p0[1]) * 0.9, my)                           # bend the street sideways
    span = ny - y
    out = []
    if street:                                                               # the street itself
        left, right = [], []
        for j in range(61):
            t = j / 60
            px, py = _bez(p0, p1, p2, t)
            sc = max(0.02, (py - y) / span) * s
            dx, dy = _bez_d(p0, p1, p2, t)
            ln = math.hypot(dx, dy) or 1
            nxv, nyv = -dy / ln, dx / ln
            hw = 120 * sc
            left.append((px + nxv * hw, py + nyv * hw * 0.25))
            right.append((px - nxv * hw, py - nyv * hw * 0.25))
        c.poly(left + right[::-1], "#1c1e21")
        c.poly(left + right[::-1], "#000000", 0.25, blur=3)
    homes = []
    sides = {"both": (-1, 1), "left": (1,), "right": (-1,)}[side]
    for i in range(int(n)):                                                  # equal spacing on the ground
        f = 1.0 / (1.0 + i * 0.55)                                           # perspective: nearer = bigger
        yy = y + span * f
        t = _t_at_y(p0, p1, p2, yy)
        px, py = _bez(p0, p1, p2, t)
        sc = max(0.03, (py - y) / span) * s
        dx, dy = _bez_d(p0, p1, p2, t)
        ln = math.hypot(dx, dy) or 1
        nxv = -dy / ln
        for sd in sides:
            if r.random() < gaps:
                continue
            hx = px + sd * nxv * (120 + 150) * sc
            homes.append((py, hx, sc))
    homes.sort()                                                             # far ones first
    for py, hx, sc in homes:
        out += _house(c, L, hx, py, sc, r, lit, new=new)
        if trees > 0 and r.random() < trees:
            tx = hx + r.choice([-1, 1]) * 150 * sc
            art.tree(c, tx, py + 4 * sc, r.uniform(150, 230) * sc, seed=int(r.integers(1, 9999)), color="#050706",
                     depth=5, spread=0.7)
    return out


@prop
def ringplan(c, L, x, y, s=1.0, rings=4, r0=150, dr=105, squash=0.38, gap=46, lit=0.06, spokes=(205, 290, 335),
             seed=4, **k):
    """The town plan from the air: curved streets in rings around a centre (see the top of this file)."""
    r = _rng(seed)
    out = []
    a0 = math.radians(90 + gap / 2)                                          # the opening faces the viewer
    a1 = math.radians(90 - gap / 2 + 360)
    outer = (r0 + (rings - 1) * dr) * s

    def pt(R, a):
        return (x + R * math.cos(a), y + R * squash * math.sin(a))

    def width(py):                                                           # nearer (lower) streets are wider
        return max(2.0, (5.0 + 6.0 * (py - (y - outer * squash)) / (2 * outer * squash + 1)) * s)

    c.ellipse(x, y, outer * 1.18, outer * squash * 1.18, "#0d120e", 0.9)     # cleared ground around the town
    for i in range(rings):                                                   # the ring streets
        R = (r0 + i * dr) * s
        m = 140
        pts = [pt(R, a0 + (a1 - a0) * j / m) for j in range(m + 1)]
        for j in range(m):
            c.line([pts[j], pts[j + 1]], "#3a3d40", width(pts[j][1]), 0.95)
    ry0 = pt(r0 * s * 0.55, math.radians(90))[1]                             # the road in, widening toward us
    c.poly([(x - 6 * s, ry0), (x + 6 * s, ry0), (x + 60 * s, H + 20), (x - 60 * s, H + 20)], "#2e3134", 0.95)
    for a in spokes:                                                         # a few radial streets
        ar = math.radians(a)
        c.line([pt(r0 * s * 0.55, ar), pt(outer + 40 * s, ar)], "#34373a", 5 * s, 0.9)
    roofs = []
    for i in range(rings):                                                   # houses on both sides of each ring
        for off in (-0.28, 0.28):
            R = (r0 + i * dr + off * dr) * s
            if R < r0 * s * 0.6:
                continue
            m = int(2 * math.pi * R / (24 * s))
            for j in range(m):
                a = a0 + (a1 - a0) * (j + 0.5) / m
                if any(abs(((math.degrees(a) - sp + 180) % 360) - 180) < 5 for sp in spokes):
                    continue
                if r.random() < 0.06:
                    continue
                px, py = pt(R, a)
                roofs.append((py, px, a))
    roofs.sort()
    for py, px, a in roofs:
        d = 0.55 + 0.45 * (py - (y - outer * squash)) / (2 * outer * squash + 1)
        hw, hh = 9 * s * d, 6 * s * d
        c.rect(px - hw, py - hh, px + hw, py + hh * 0.4, "#2c3036")         # the house
        c.poly([(px - hw - 1, py - hh), (px, py - hh - 5 * s * d), (px + hw + 1, py - hh)], "#15171b")
        if r.random() < lit:
            L.circle(px, py - hh * 0.2, 7 * s * d, WARM, 0.6, blur=3)
            c.rect(px - 2.5 * s * d, py - hh * 0.6, px + 2.5 * s * d, py, "#ffcc80", 0.95)
            out.append((px, py - hh * 0.3, (1.0, 0.78, 0.45), 14 * s * d, False))
    c.ellipse(x, y, r0 * s * 0.5, r0 * s * 0.5 * squash, "#121a12")         # the green at the centre
    c.rect(x - 34 * s, y - 34 * s, x + 34 * s, y, "#30343a")                 # a civic building on it
    c.poly([(x - 42 * s, y - 34 * s), (x, y - 58 * s), (x + 42 * s, y - 34 * s)], "#16181c")
    for j in range(7):                                                       # trees on the green
        a = r.uniform(0, 2 * math.pi)
        tx, ty = x + math.cos(a) * r0 * s * 0.38, y + math.sin(a) * r0 * s * 0.38 * squash
        c.circle(tx, ty - 6 * s, 9 * s, "#0a100b")
    return out


@prop
def housecrate(c, L, x, y, s=1.0, seed=2, flip=False, **k):
    """A prefab house taken apart for shipping, crated on skids (see the top of this file)."""
    r = _rng(seed)
    f = -1 if flip else 1
    for j in range(3):                                                       # skids
        sx = x + (j - 1) * 120 * s
        c.rect(sx - 70 * s, y - 14 * s, sx + 70 * s, y, "#1a140e")
    for j in range(5):                                                       # stacked wall panels
        yy = y - 14 * s - j * 22 * s
        ox = r.uniform(-6, 6) * s
        c.rect(x - 200 * s + ox, yy - 20 * s, x + 200 * s + ox, yy, "#3e3428")
        c.line([(x - 200 * s + ox, yy - 20 * s), (x + 200 * s + ox, yy - 20 * s)], "#8a7a62", max(0.8, 1.6 * s), 0.4)
    py = y - 14 * s - 110 * s                                                # the top panel, standing: window holes
    c.rect(x - 190 * s, py - 120 * s, x + 190 * s, py, "#4a3e30")
    for wx in (-110, 110):
        c.rect(x + (wx - 30) * s, py - 92 * s, x + (wx + 30) * s, py - 44 * s, "#0a0806")
    c.rect(x - 22 * s, py - 104 * s, x + 22 * s, py, "#0a0806")             # the door hole
    for j in range(6):                                                       # crate slats
        sx = x - 200 * s + j * 80 * s
        c.line([(sx, py - 124 * s), (sx + 30 * s, y - 14 * s)], "#2a2016", max(1.0, 6 * s), 0.9)
    rx = x + f * 330 * s                                                     # a roof section, leaning
    c.poly([(rx - f * 110 * s, y), (rx + f * 30 * s, y - 170 * s), (rx + f * 120 * s, y - 160 * s), (rx + f * 10 * s, y)],
           "#221c16")
    for j in range(1, 6):
        t = j / 6
        c.line([(rx - f * 110 * s + f * 120 * s * t, y), (rx + f * 30 * s + f * 90 * s * t, y - 170 * s + 10 * s * t)],
               "#120e0a", max(0.8, 2 * s), 0.8)
    return []
