"""Props for the Michigan City pier-light short (the Sheridan keepers: South Manitou Island, 1878, and Michigan City's
East Pierhead Light), added Nov. 15, 2026. They register in story_kit3.PROPS like every prop, so a storyboard names
them in "props": [{"p": "pierhead", ...}].

    pierhead      Michigan City's 1904 East Pierhead Light: a white, steel-clad fog-signal building with a red hip
                  roof and the octagonal white tower rising from it, lantern lit (lit, beam=0..1, aim=-1|1 the side
                  the beam falls), at the end of a concrete pier, with the elevated catwalk on steel A-frames running
                  in from x0 (walk=False leaves it off). x is the building's middle, y the waterline
    islandlight   a tall white conical lighthouse tower (South Manitou Island's is 104 feet) with a black lantern
                  and gallery, a small keeper's house joined to it, on a low island shore with dunes and cedars
                  (lit, house=True, shore= px of shore each side)
    smallboat     a small open sailboat, side on, one mast and a spritsail (sail=False: mast only). capsized=True
                  draws only its overturned hull low in the water. No people are drawn in it
    icefloes      pieces of floating ice on open water from y down (n, spread, depth); far pieces are smaller
    towergallery  close on the top of a lighthouse tower: the lantern room, its dome and the gallery railing; boys=0..2
                  small figures standing at the rail with their backs to us, looking out over the water (to the
                  left); lit=0..1 the lamp

People are small anonymous silhouettes. Nothing shows a body, a person in the water, or a real person's likeness.
"""
import math

import numpy as np

import story_kit3 as K3
from story_kit import WARM, W, H
from core import smooth_path, paint

prop = K3.prop
INK = "#030304"


@prop
def pierhead(c, L, x, y, s=1.0, lit=True, beam=0.7, aim=1, walk=True, x0=-20, wall="#8e979e", **k):
    """Michigan City's 1904 East Pierhead Light at the end of its pier (see the top of this file)."""
    out = []
    deck = y - 34 * s                                                            # the concrete pier
    c.rect(x0, deck, x + 150 * s, y + 6 * s, "#2a2e32")
    c.rect(x0, deck, x + 150 * s, deck + 6 * s, "#4a5056", 0.8)
    c.line([(x0, y + 4 * s), (x + 150 * s, y + 4 * s)], "#000000", max(1.0, 3 * s), 0.5)
    bw, bh = 120 * s, 120 * s                                                     # the fog-signal building
    bx0, bx1 = x - bw, x + bw
    c.rect(bx0, deck - bh, bx1, deck, wall)
    for j in range(1, 12):                                                        # steel cladding seams
        c.line([(bx0 + j * 2 * bw / 12, deck - bh), (bx0 + j * 2 * bw / 12, deck)], "#000000", max(0.6, 1.0 * s), 0.12)
    for wx in (-70, 0, 70):                                                       # windows and a door
        c.rect(x + (wx - 13) * s, deck - 92 * s, x + (wx + 13) * s, deck - 56 * s, "#141a20")
    c.rect(x + 22 * s, deck - 50 * s, x + 50 * s, deck, "#1a2026")
    roof = "#4a1c16"
    c.poly([(bx0 - 12 * s, deck - bh), (x - 60 * s, deck - bh - 52 * s), (x + 60 * s, deck - bh - 52 * s),
            (bx1 + 12 * s, deck - bh)], roof)                                    # the hip roof
    c.line([(bx0 - 12 * s, deck - bh), (bx1 + 12 * s, deck - bh)], "#2a0e0a", max(1.0, 3 * s))
    ty0 = deck - bh - 40 * s                                                      # the octagonal tower
    tt = ty0 - 170 * s
    c.poly([(x - 30 * s, ty0), (x - 25 * s, tt), (x + 25 * s, tt), (x + 30 * s, ty0)], wall)
    c.poly([(x - 30 * s, ty0), (x - 25 * s, tt), (x + 25 * s, tt), (x + 30 * s, ty0)], "#ffffff", 0.1)
    for f in (-0.5, 0.0, 0.5):                                                    # its facets
        c.line([(x + f * 52 * s, ty0), (x + f * 44 * s, tt)], "#8a939a", max(0.6, 1.2 * s), 0.8)
    c.rect(x - 9 * s, ty0 - 80 * s, x + 9 * s, ty0 - 52 * s, "#141a20")
    c.rect(x - 40 * s, tt - 6 * s, x + 40 * s, tt + 2 * s, "#1a1a1a")             # gallery deck and rail
    c.line([(x - 40 * s, tt - 26 * s), (x + 40 * s, tt - 26 * s)], "#1a1a1a", max(1.0, 2 * s))
    for q in range(9):
        c.line([(x - 40 * s + q * 10 * s, tt - 26 * s), (x - 40 * s + q * 10 * s, tt - 6 * s)], "#1a1a1a",
               max(0.6, 1.2 * s))
    ly0, ly1 = tt - 60 * s, tt - 6 * s                                            # the lantern
    c.rect(x - 22 * s, ly0, x + 22 * s, ly1, "#ffe2a0" if lit else "#1c2228", 0.9 if lit else 1.0)
    for q in range(1, 4):
        c.line([(x - 22 * s + q * 11 * s, ly0), (x - 22 * s + q * 11 * s, ly1)], "#202020", max(0.6, 1.4 * s))
    c.poly([(x - 26 * s, ly0), (x, ly0 - 26 * s), (x + 26 * s, ly0)], roof)        # dome and ventilator
    c.circle(x, ly0 - 30 * s, 5 * s, "#1a1a1a")
    if lit:
        cy = (ly0 + ly1) / 2
        L.circle(x, cy, 40 * s, "#ffd890", 0.8)
        out.append((x, cy, (1.0, 0.88, 0.6), 160 * s, False, 0.85))
        if beam > 0:
            ex = x + aim * 900 * s
            c.poly([(x, cy - 8 * s), (ex, cy - 120 * s), (ex, cy + 150 * s), (x, cy + 8 * s)], "#fff0c8", 0.06 * beam,
                   blur=22 * s)
            L.poly([(x, cy - 8 * s), (ex, cy - 90 * s), (ex, cy + 120 * s), (x, cy + 8 * s)], "#ffe0a0", 0.15 * beam,
                   blur=30 * s)
    if walk:                                                                      # the elevated catwalk
        wy = deck - 78 * s
        end = bx0
        steel, frame = "#4e555c", "#3a4046"
        c.rect(x0, wy - 6 * s, end, wy + 2 * s, steel)
        c.line([(x0, wy - 6 * s), (end, wy - 6 * s)], "#8a929a", max(0.8, 1.4 * s), 0.6)   # moonlit edge
        c.line([(x0, wy - 34 * s), (end, wy - 34 * s)], steel, max(1.0, 2.2 * s))           # hand rail
        c.line([(x0, wy - 18 * s), (end, wy - 18 * s)], steel, max(0.6, 1.2 * s), 0.8)
        px = end - 20 * s
        while px > x0:
            c.line([(px, wy - 34 * s), (px, wy)], steel, max(0.6, 1.4 * s))
            c.line([(px - 16 * s, deck), (px, wy + 2 * s), (px + 16 * s, deck)], frame, max(1.0, 3 * s))  # A-frame
            c.line([(px - 10 * s, deck - 26 * s), (px + 10 * s, deck - 26 * s)], frame, max(0.6, 1.6 * s))
            px -= 64 * s
    return out


@prop
def islandlight(c, L, x, y, s=1.0, lit=True, house=True, shore=420, **k):
    """A tall white conical lighthouse on a low island shore (see the top of this file)."""
    out = []
    r = np.random.default_rng(7)
    sh = shore * s                                                                # the island: dunes and cedars
    pts = [(x - sh - 160 * s, y + 4 * s)]
    for q in range(17):
        f = q / 16
        px = x - sh + f * 2 * sh
        pts.append((px, y - (18 + 30 * math.sin(f * math.pi) + 10 * math.sin(f * 17)) * s))
    pts.append((x + sh + 180 * s, y + 4 * s))
    c.poly(pts, "#0c0f0e", smooth=True)
    c.poly([(x - sh - 150 * s, y + 4 * s), (x + sh + 170 * s, y + 4 * s), (x + sh + 140 * s, y - 8 * s),
            (x - sh - 120 * s, y - 8 * s)], "#3a3a34", 0.7)                         # a pale strip of beach
    for q in range(26):
        px = x - sh + r.uniform(0, 2 * sh)
        if abs(px - x) < 90 * s:
            continue
        h = r.uniform(40, 110) * s
        base = y - (16 + 26 * math.sin((px - x + sh) / (2 * sh) * math.pi)) * s
        c.poly([(px - h * 0.22, base), (px, base - h), (px + h * 0.22, base)], "#060908")
    tb, tt, ht = 34 * s, 19 * s, 560 * s                                          # the tower
    top = y - 30 * s - ht
    c.poly([(x - tb, y - 30 * s), (x - tt, top), (x + tt, top), (x + tb, y - 30 * s)], "#b9bfc2")
    c.poly([(x + tb * 0.2, y - 30 * s), (x + tt * 0.2, top), (x + tt, top), (x + tb, y - 30 * s)], "#000000", 0.18)
    for q in range(3):                                                            # small windows up the tower
        wy = y - 30 * s - ht * (0.3 + q * 0.22)
        c.rect(x - 4 * s, wy - 9 * s, x + 4 * s, wy + 9 * s, "#1a2026")
    c.rect(x - 34 * s, top - 6 * s, x + 34 * s, top + 4 * s, "#0c0c0c")           # gallery
    c.line([(x - 34 * s, top - 26 * s), (x + 34 * s, top - 26 * s)], "#0c0c0c", max(1.0, 2 * s))
    for q in range(8):
        c.line([(x - 34 * s + q * 68 * s / 7, top - 26 * s), (x - 34 * s + q * 68 * s / 7, top - 6 * s)], "#0c0c0c",
               max(0.6, 1.2 * s))
    ly0, ly1 = top - 64 * s, top - 6 * s                                          # lantern, dome, ventilator
    c.rect(x - 20 * s, ly0, x + 20 * s, ly1, "#ffe2a0" if lit else "#1a2026", 0.9 if lit else 1.0)
    c.line([(x, ly0), (x, ly1)], "#101010", max(0.6, 1.4 * s))
    c.poly([(x - 24 * s, ly0), (x, ly0 - 28 * s), (x + 24 * s, ly0)], "#0c0c0c")
    c.circle(x, ly0 - 32 * s, 5 * s, "#0c0c0c")
    if lit:
        cy = (ly0 + ly1) / 2
        L.circle(x, cy, 34 * s, "#ffd890", 0.8)
        out.append((x, cy, (1.0, 0.88, 0.6), 150 * s, False, 0.85))
    if house:                                                                     # keeper's house and passage
        hx0, hx1 = x + 60 * s, x + 230 * s
        c.rect(x + tb - 6 * s, y - 104 * s, hx0, y - 28 * s, "#3a2419")              # the passageway
        c.poly([(x + tb - 8 * s, y - 104 * s), (hx0, y - 104 * s), (hx0, y - 112 * s), (x + tb - 8 * s, y - 112 * s)], "#0e0806")
        c.rect(hx0, y - 150 * s, hx1, y - 26 * s, "#2c1a14")
        c.poly([(hx0 - 10 * s, y - 150 * s), ((hx0 + hx1) / 2, y - 205 * s), (hx1 + 10 * s, y - 150 * s)], "#0e0806")
        for q in range(3):
            wx = hx0 + 30 * s + q * 50 * s
            on = lit and q == 1
            K3._win(c, L, wx - 10 * s, y - 120 * s, wx + 10 * s, y - 84 * s, on, k=0.45)
            if on:
                out.append((wx, y - 102 * s, (1.0, 0.74, 0.42), 40 * s, True, 0.3))
    return out


@prop
def smallboat(c, L, x, y, s=1.0, sail=True, capsized=False, flip=False, color="#060707", **k):
    """A small open sailboat, side on, or just its overturned hull (see the top of this file)."""
    d = -1 if flip else 1

    def X(v):
        return x + d * v * s

    if capsized:                                                                  # keel up, low in the water
        c.poly([(X(-110), y), (X(-96), y - 22 * s), (X(-20), y - 34 * s), (X(70), y - 30 * s), (X(112), y - 8 * s),
                (X(116), y)], color, smooth=True)
        c.line([(X(-90), y - 26 * s), (X(100), y - 20 * s)], "#2a3036", max(0.8, 1.6 * s), 0.6)
        for q in range(4):
            c.ellipse(X(-110 + q * 75), y + 2 * s, 30 * s, 4 * s, "#c8d4dc", 0.25, blur=2 * s)
        return []
    c.poly([(X(-110), y - 34 * s), (X(-96), y - 6 * s), (X(80), y - 4 * s), (X(118), y - 40 * s), (X(100), y - 44 * s),
            (X(-104), y - 40 * s)], color, smooth=True)                          # the hull
    c.line([(X(-104), y - 40 * s), (X(108), y - 44 * s)], "#2a2e32", max(0.8, 1.6 * s), 0.7)  # gunwale
    for q in range(5):                                                            # ripples at the waterline
        c.ellipse(X(-120 + q * 60), y, 34 * s, 4 * s, "#c8d4dc", 0.2, blur=2 * s)
    mx = X(20)
    c.line([(mx, y - 40 * s), (mx, y - 230 * s)], color, max(1.0, 4 * s))         # the mast
    if sail:                                                                      # a spritsail
        c.poly([(mx + d * 3 * s, y - 220 * s), (mx + d * 3 * s, y - 62 * s), (X(108), y - 70 * s), (X(118), y - 236 * s)],
               "#4a4840", 0.92)
        c.line([(mx, y - 66 * s), (X(118), y - 236 * s)], color, max(0.8, 2 * s))  # the sprit
    return []


@prop
def icefloes(c, L, x, y, s=1.0, n=26, spread=1100, depth=420, seed=3, color="#a8b6c0", **k):
    """Pieces of floating ice on open water from y down; far pieces are smaller."""
    r = np.random.default_rng(seed)
    for q in range(n):
        f = r.uniform(0, 1) ** 1.6                                                # more of them far away
        py = y + 8 * s + f * depth * s
        z = 0.25 + f * 1.4
        px = x + r.uniform(-0.5, 0.5) * spread * (0.6 + f) * s
        w = r.uniform(40, 120) * z * s
        hgt = w * r.uniform(0.12, 0.22)
        pts = []
        for t in range(7):
            a = 2 * math.pi * t / 7
            pts.append((px + math.cos(a) * w * r.uniform(0.7, 1.0), py + math.sin(a) * hgt * r.uniform(0.7, 1.0)))
        c.poly(pts, color, 0.55 + 0.25 * f, smooth=True)
        c.poly([(p0, p1 + hgt * 0.5) for p0, p1 in pts], "#000000", 0.18, smooth=True)
    return []


@prop
def towergallery(c, L, x, y, s=1.0, boys=2, lit=0.6, tone="#7c858a", **k):
    """Close on the top of a lighthouse tower with small figures at the gallery rail (see the top of this file)."""
    out = []
    c.poly([(x - 150 * s, y), (x - 120 * s, H + 40), (x + 330 * s, H + 40), (x + 300 * s, y)], tone)  # tower top
    c.poly([(x + 120 * s, y), (x + 150 * s, H + 40), (x + 330 * s, H + 40), (x + 300 * s, y)], "#000000", 0.2)
    lx0, lx1 = x + 10 * s, x + 260 * s                                            # the lantern room
    top = y - 330 * s
    c.rect(lx0, top, lx1, y - 20 * s, "#2a3238")
    for q in range(1, 5):
        c.line([(lx0 + q * (lx1 - lx0) / 5, top), (lx0 + q * (lx1 - lx0) / 5, y - 20 * s)], "#0e0e0e", max(1.0, 4 * s))
    c.line([(lx0, (top + y) / 2), (lx1, (top + y) / 2)], "#0e0e0e", max(1.0, 3 * s))
    if lit > 0:
        L.rect(lx0 + 20 * s, top + 20 * s, lx1 - 20 * s, y - 40 * s, "#ffd890", 0.5 * lit)
        c.ellipse((lx0 + lx1) / 2, (top + y) / 2, 40 * s, 60 * s, "#ffe8b0", 0.8 * lit)
        out.append(((lx0 + lx1) / 2, (top + y) / 2, (1.0, 0.86, 0.58), 260 * s, False, 0.7 * lit))
    c.poly([(lx0 - 20 * s, top), ((lx0 + lx1) / 2, top - 120 * s), (lx1 + 20 * s, top)], "#0e0e0e")  # the dome
    c.circle((lx0 + lx1) / 2, top - 128 * s, 12 * s, "#0e0e0e")
    for j in range(max(0, min(2, boys))):                                         # boys at the rail, backs to us
        bx = x - 150 * s + j * 70 * s
        hgt = (150 - j * 14) * s
        c.rect(bx - 10 * s, y - 16 * s - hgt * 0.45, bx - 3 * s, y - 16 * s, INK)
        c.rect(bx + 3 * s, y - 16 * s - hgt * 0.45, bx + 10 * s, y - 16 * s, INK)
        c.poly([(bx - 16 * s, y - 16 * s - hgt * 0.4), (bx + 16 * s, y - 16 * s - hgt * 0.4),
                (bx + 13 * s, y - 16 * s - hgt * 0.85), (bx - 13 * s, y - 16 * s - hgt * 0.85)], INK)
        c.circle(bx, y - 16 * s - hgt * 0.94, 10 * s, INK)
        c.ellipse(bx, y - 16 * s - hgt * 1.0, 13 * s, 3 * s, INK)                # a cap
    c.rect(x - 230 * s, y - 16 * s, x + 380 * s, y + 6 * s, "#121212")           # the gallery deck
    rail = y - 120 * s
    c.line([(x - 230 * s, rail), (x + 380 * s, rail)], "#121212", max(1.0, 5 * s))
    c.line([(x - 230 * s, y - 64 * s), (x + 380 * s, y - 64 * s)], "#121212", max(0.8, 2.5 * s))
    for q in range(16):
        px = x - 230 * s + q * 610 * s / 15
        c.line([(px, rail), (px, y - 14 * s)], "#121212", max(0.8, 3 * s))
    return out
