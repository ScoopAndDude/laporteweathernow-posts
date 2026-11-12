"""Tableaux: story illustrations built from props (added Nov. 12, 2026, to remake the scheduled shorts with
pictures that show the story). One scene kind, many pictures: the storyboard lists what stands in the picture.

  "scene": {"kind": "tab_lake" | "tab_land" | "tab_town" | "tab_room" | "tab_rail",    (same picture code; the name
            picks the background sound: waves / wind+owl / wind / room+creak / rumble+whistle)
            "sky": "dusk" | "blue" | "dawn" | "night" | "storm" | "room",   "moon": [x, y, r] (optional)
            "wall": "#1a100c"  (sky "room": the wall colour)
            "ground": {"type": "water" | "land" | "snow" | "sand" | "street" | "floor", "y": 1150},
            "props": [{"p": "steamer", "x": 540, "y": 1150, "s": 1.0, ...}, ...],     drawn in order, back to front
            "glows": [{"x": 300, "y": 900, "r": 120, "color": [1, 0.5, 0.2], "k": 0.6, "flick": true}],
            + everything a Shot understands (move, amount, fog, rain, snow, ghost, ghost_x, ghost_y, orbs)}

Each prop is placed by its bottom centre (x, y) and scale s. PROPS at the bottom lists them all; `python3
story_kit3.py sheet` draws every prop on one sheet (shorts/out/_props.jpg). Keep what matters above y 1250.
People are small anonymous silhouettes. Nothing shows a body, a real person's likeness or a brand.
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw

import art
import story_kit as K
from story_kit import Shot, W, H, WARM, hash2
from core import add_spot, smooth_path, paint
from reel_haunts import cv, comp, layer_from_pil
from reel_frank import flick
from story_kit2 import sky as mk_sky, leafy, DUSK, BLUE, DAWN, NIGHT, wagon, horse, walkers, touring_car

STORM = [(0.0, "#050608"), (0.4, "#0e1318"), (0.62, "#1a2228"), (1.0, "#161c20")]
SKIES = {"dusk": DUSK, "blue": BLUE, "dawn": DAWN, "night": NIGHT, "storm": STORM}
GROUND = {"water": {"dusk": "#2a2630", "blue": "#0e2030", "dawn": "#4a4a58", "night": "#081420", "storm": "#0c1216"},
          "land": "#070908", "snow": "#56626c", "sand": "#3a372e", "street": "#101214", "floor": "#150d09"}
INK = "#050607"
PROPS = {}


def prop(f):
    PROPS[f.__name__] = f
    return f


def _win(c, L, x0, y0, x1, y1, on, col="#070606", k=0.6):
    c.rect(x0, y0, x1, y1, col)
    if on:
        L.rect(x0, y0, x1, y1, WARM, k)


# ------------------------------------------------------------------------------------------- ships and the lake

@prop
def steamer(c, L, x, y, s=1.0, wheel=False, lit=True, smoke=True, color=INK, **k):
    """A Great Lakes passenger steamer, side on, bow to the right. wheel=True: a sidewheeler (1850s-60s)."""
    c.poly([(x - 300 * s, y - 50 * s), (x + 250 * s, y - 50 * s), (x + 320 * s, y - 62 * s), (x + 270 * s, y),
            (x - 280 * s, y)], color)
    for d, (a, b, t) in enumerate(((-250, 200, 96), (-200, 130, 138))):
        c.rect(x + a * s, y - t * s, x + b * s, y - (t - 44) * s, "#0b0d0f")
        for j in range(int((b - a) // 34)):
            wx = x + (a + 12 + j * 34) * s
            _win(c, L, wx, y - (t - 10) * s, wx + 14 * s, y - (t - 30) * s, lit and hash2(j, d, 3) > 0.3)
    c.rect(x + 70 * s, y - 176 * s, x + 130 * s, y - 138 * s, "#0b0d0f")                 # the pilot house
    _win(c, L, x + 80 * s, y - 168 * s, x + 122 * s, y - 150 * s, lit)
    c.rect(x - 60 * s, y - 250 * s, x - 22 * s, y - 138 * s, color)                       # the stack
    c.rect(x - 60 * s, y - 236 * s, x - 22 * s, y - 224 * s, "#3a1a14")
    for mx in (-210, 190):
        c.line([(x + mx * s, y - 96 * s), (x + mx * s, y - 300 * s)], color, 4 * s)
    if wheel:
        c.c.drawPath(smooth_path([(x - 150 * s, y - 20 * s), (x - 130 * s, y - 120 * s), (x - 60 * s, y - 150 * s),
                                  (x + 10 * s, y - 120 * s), (x + 30 * s, y - 20 * s)], True, k=0.16), paint("#101316"))
    if smoke:
        for j in range(7):
            c.circle(x - (60 + j * 46) * s, y - (262 + j * 16) * s, (20 + j * 9) * s, "#20262a", 0.5 - j * 0.05)
    return [(x + 316 * s, y - 70 * s)]


@prop
def schooner(c, L, x, y, s=1.0, trees=False, sails=True, flag=False, color=INK, **k):
    """A three-masted lake schooner, bow to the right. trees=True: a deck load of evergreens (the Rouse Simmons)."""
    c.poly([(x - 250 * s, y - 46 * s), (x + 230 * s, y - 46 * s), (x + 300 * s, y - 66 * s), (x + 236 * s, y),
            (x - 232 * s, y)], color)
    c.line([(x + 290 * s, y - 64 * s), (x + 400 * s, y - 96 * s)], color, 5 * s)
    for i, mx in enumerate((-160, 0, 150)):
        top = y - (420 - i * 12) * s
        c.line([(x + mx * s, y - 46 * s), (x + mx * s, top)], color, 6 * s)
        if sails:
            c.poly([(x + (mx + 8) * s, y - 90 * s), (x + (mx + 8) * s, top + 60 * s), (x + (mx + 104) * s, top + 110 * s),
                    (x + (mx + 122) * s, y - 96 * s)], "#34383a", 0.95)
            c.line([(x + (mx + 8) * s, top + 60 * s), (x + (mx + 104) * s, top + 110 * s)], color, 3 * s)
    if sails:
        c.poly([(x + 158 * s, y - 380 * s), (x + 390 * s, y - 96 * s), (x + 170 * s, y - 100 * s)], "#2e3234", 0.9)
    if trees:
        for j in range(14):
            tx = x + (-220 + j * 32) * s
            pine(c, L, tx, y - 44 * s, 0.28 * s * (0.8 + 0.5 * hash2(j, 1, 7)), color="#0c1a12")
        pine(c, L, x + 150 * s, y - 396 * s, 0.2 * s, color="#0c1a12")
    if flag:
        c.rect(x - 4 * s, y - 440 * s, x + 40 * s, y - 414 * s, "#5a1a16")


@prop
def freighter(c, L, x, y, s=1.0, lit=True, color=INK, **k):
    """A long lake freighter of the 1930s: pilot house at the bow (right), cabins and stack at the stern."""
    c.poly([(x - 420 * s, y - 60 * s), (x + 380 * s, y - 60 * s), (x + 440 * s, y - 76 * s), (x + 400 * s, y),
            (x - 410 * s, y)], color)
    c.rect(x + 300 * s, y - 150 * s, x + 380 * s, y - 60 * s, "#0b0d0f")
    _win(c, L, x + 312 * s, y - 138 * s, x + 370 * s, y - 118 * s, lit)
    c.rect(x - 400 * s, y - 120 * s, x - 270 * s, y - 60 * s, "#0b0d0f")
    for j in range(3):
        _win(c, L, x + (-388 + j * 40) * s, y - 104 * s, x + (-370 + j * 40) * s, y - 84 * s, lit and j != 1)
    c.rect(x - 350 * s, y - 220 * s, x - 310 * s, y - 120 * s, color)
    c.rect(x - 350 * s, y - 206 * s, x - 310 * s, y - 192 * s, "#3a3a34")
    for j in range(9):
        c.rect(x + (-240 + j * 58) * s, y - 70 * s, x + (-200 + j * 58) * s, y - 60 * s, "#15181a")
    for mx in (-250, 280):
        c.line([(x + mx * s, y - 60 * s), (x + mx * s, y - 230 * s)], color, 3 * s)
    for j in range(6):
        c.circle(x - (360 + j * 44) * s, y - (232 + j * 12) * s, (16 + j * 8) * s, "#20262a", 0.45 - j * 0.05)


@prop
def griffon(c, L, x, y, s=1.0, color=INK, **k):
    """A small 17th-century sailing ship (La Salle's Griffon): high stern, two masts with square sails."""
    c.poly([(x - 170 * s, y - 110 * s), (x - 110 * s, y - 70 * s), (x + 150 * s, y - 60 * s), (x + 220 * s, y - 90 * s),
            (x + 160 * s, y), (x - 150 * s, y)], color)
    c.line([(x + 210 * s, y - 88 * s), (x + 300 * s, y - 130 * s)], color, 5 * s)
    for mx, top in ((-30, 380), (110, 320)):
        c.line([(x + mx * s, y - 60 * s), (x + mx * s, y - top * s)], color, 6 * s)
        for lv, (a, b, hw) in enumerate(((top - 30, top - 150, 80), (top - 160, 110, 104))):
            c.c.drawPath(smooth_path([(x + (mx - hw) * s, y - a * s), (x + (mx + hw) * s, y - a * s),
                                      (x + (mx + hw + 14) * s, y - b * s), (x + (mx - hw - 6) * s, y - b * s)], True,
                                     k=0.08), paint("#3c3a34", a=0.95))
    c.poly([(x - 30 * s, y - 380 * s), (x - 30 * s, y - 410 * s), (x + 30 * s, y - 395 * s)], "#5a5648")


@prop
def boat(c, L, x, y, s=1.0, lamp=False, net=False, color=INK, **k):
    """A small open boat (a surfboat or fishing boat). lamp=True: a lantern in the bow. net=True: a net over the side."""
    c.poly([(x - 110 * s, y - 34 * s), (x + 120 * s, y - 34 * s), (x + 150 * s, y - 48 * s), (x + 110 * s, y),
            (x - 96 * s, y)], color)
    c.line([(x - 10 * s, y - 34 * s), (x - 10 * s, y - 150 * s)], color, 4 * s)
    if net:
        for j in range(7):
            c.line([(x + (-90 + j * 14) * s, y - 34 * s), (x + (-120 + j * 20) * s, y + 60 * s)], "#2a3030", 1.5 * s, 0.8)
        for j in range(4):
            c.line([(x - 120 * s, y - (10 - j * 20) * s), (x + 10 * s, y - (10 - j * 20) * s)], "#2a3030", 1.5 * s, 0.6)
    return [(x + 120 * s, y - 70 * s)] if lamp else None


@prop
def plane(c, L, x, y, s=1.0, color="#07090b", **k):
    """A four-engine propeller airliner of 1950 (a DC-4), seen from the side and a little below, flying right."""
    c.c.drawPath(smooth_path([(x - 260 * s, y - 6 * s), (x - 100 * s, y - 34 * s), (x + 200 * s, y - 30 * s),
                              (x + 280 * s, y - 6 * s), (x + 200 * s, y + 16 * s), (x - 200 * s, y + 12 * s)], True,
                             k=0.16), paint(color))
    c.poly([(x - 250 * s, y - 8 * s), (x - 300 * s, y - 100 * s), (x - 240 * s, y - 100 * s), (x - 170 * s, y - 20 * s)], color)
    c.poly([(x - 20 * s, y), (x + 80 * s, y), (x - 40 * s, y + 150 * s), (x - 110 * s, y + 150 * s)], color)
    for ex, ey in ((-18, 60), (-56, 112)):
        c.ellipse(x + ex * s, y + ey * s, 40 * s, 13 * s, color)
    for j in range(9):
        L.circle(x + (-60 + j * 28) * s, y - 14 * s, 4 * s, WARM, 0.8)
    return [(x - 300 * s, y - 100 * s, (1.0, 0.2, 0.15)), (x - 100 * s, y + 150 * s, (0.3, 1.0, 0.4))]


@prop
def pier(c, L, x, y, s=1.0, n=7, **k):
    """A timber dock running out from the left."""
    c.rect(x - 400 * s, y - 34 * s, x + 200 * s, y - 20 * s, "#15110d")
    for j in range(n):
        c.rect(x + (-390 + j * 90) * s, y - 34 * s, x + (-376 + j * 90) * s, y + 60 * s, "#0c0907")


@prop
def flotsam(c, L, x, y, s=1.0, what="planks", n=9, seed=0, **k):
    """Things washed up along a beach: what="planks" (wreckage), "trees" (evergreens) or "crates"."""
    r = np.random.default_rng(seed)
    for j in range(n):
        px = x + (r.uniform(-1, 1) * 420) * s
        py = y + r.uniform(-18, 40) * s
        if what == "trees":
            a = r.uniform(-0.3, 0.3)
            for t in range(5):
                hw = (34 - t * 6) * s
                cx_ = px + t * 30 * s
                c.poly([(cx_, py - hw + a * 20), (cx_ + 44 * s, py + a * 20), (cx_, py + hw * 0.5 + a * 20)], "#0e2014")
        elif what == "crates":
            c.rect(px, py - 40 * s, px + 54 * s, py, "#241a10")
            c.line([(px, py - 20 * s), (px + 54 * s, py - 20 * s)], "#0c0907", 2)
        else:
            a = r.uniform(-0.5, 0.5)
            ln = r.uniform(60, 150) * s
            c.line([(px, py), (px + ln * math.cos(a), py + ln * math.sin(a) * 0.4)], "#2a2016", r.uniform(6, 12) * s)


@prop
def dog(c, L, x, y, s=1.0, color=INK, **k):
    """A small terrier standing on the shore, facing right."""
    c.ellipse(x, y - 34 * s, 40 * s, 18 * s, color)
    c.circle(x + 44 * s, y - 56 * s, 16 * s, color)
    c.poly([(x + 52 * s, y - 58 * s), (x + 76 * s, y - 52 * s), (x + 54 * s, y - 44 * s)], color)
    c.poly([(x + 36 * s, y - 68 * s), (x + 40 * s, y - 86 * s), (x + 50 * s, y - 68 * s)], color)
    for lx in (-28, -14, 18, 30):
        c.line([(x + lx * s, y - 24 * s), (x + lx * s, y)], color, 7 * s)
    c.line([(x - 38 * s, y - 40 * s), (x - 52 * s, y - 70 * s)], color, 5 * s)


@prop
def iceblocks(c, L, x, y, s=1.0, **k):
    """An ice harvest: a sawn channel of open water, cut blocks stacked beside it and a horse-drawn sled."""
    c.poly([(x - 300 * s, y), (x + 140 * s, y - 60 * s), (x + 200 * s, y - 40 * s), (x - 200 * s, y + 40 * s)], "#0a1620")
    for j in range(6):
        for t in range(1 + j % 3):
            bx, by = x + (-260 + j * 70) * s, y - (70 + t * 34) * s + j * 4 * s
            c.rect(bx, by, bx + 60 * s, by + 32 * s, "#9ab4c4", 0.85)
            c.line([(bx, by), (bx + 60 * s, by)], "#d8e8f0", 2, 0.8)
    horse(c, x + 300 * s, y - 30 * s, 0.9 * s)
    c.rect(x + 150 * s, y - 60 * s, x + 250 * s, y - 40 * s, INK)
    art.figure(c, x + 60 * s, y - 20 * s, 120 * s, color=INK, coat=True, hat="cap")


# ------------------------------------------------------------------------------------------- nature

@prop
def pine(c, L, x, y, s=1.0, color="#050a08", **k):
    c.rect(x - 8 * s, y - 60 * s, x + 8 * s, y, color)
    for t in range(5):
        hw = (130 - t * 22) * s
        yy = y - (50 + t * 78) * s
        c.poly([(x - hw, yy), (x, yy - 150 * s), (x + hw, yy)], color)


@prop
def tree(c, L, x, y, s=1.0, bare=False, seed=0, color="#060b09", **k):
    if bare:
        art.tree(c, x, y, 560 * s, seed=seed, depth=7, spread=0.6)
    else:
        leafy(c, x, y, 560 * s, seed, color=color)


@prop
def stones(c, L, x, y, s=1.0, n=7, seed=0, toppled=False, spread=420, **k):
    """Old headstones. toppled=True: some lie fallen or broken."""
    r = np.random.default_rng(seed)
    for j in range(n):
        gx = x + (-1 + 2 * (j + r.uniform(0, 0.6)) / n) * spread * s
        hh, ww = r.uniform(70, 130) * s, r.uniform(44, 64) * s
        gy = y + r.uniform(-12, 22) * s
        if toppled and r.uniform() < 0.55:
            c.poly([(gx - hh * 0.6, gy), (gx - hh * 0.5, gy - ww * 0.5), (gx + hh * 0.5, gy - ww * 0.3), (gx + hh * 0.6, gy)],
                   "#2c3234")
        else:
            c.c.drawPath(smooth_path([(gx - ww / 2, gy), (gx - ww / 2, gy - hh * 0.8), (gx, gy - hh),
                                      (gx + ww / 2, gy - hh * 0.8), (gx + ww / 2, gy)], True, k=0.14), paint("#2c3234"))
            c.line([(gx - ww / 2, gy - hh * 0.8), (gx, gy - hh)], "#5a686a", 2, 0.6)


@prop
def elephant(c, L, x, y, s=1.0, flip=False, **k):
    """A stone elephant statue on a plinth, trunk lowered (Showmen's Rest)."""
    f = -1 if flip else 1
    st = "#4a4e50"
    c.rect(x - 110 * s, y - 60 * s, x + 110 * s, y, "#3a3d3f")
    c.line([(x - 110 * s, y - 60 * s), (x + 110 * s, y - 60 * s)], "#8a9092", 2, 0.6)
    c.ellipse(x - f * 10 * s, y - 150 * s, 80 * s, 52 * s, st)
    c.circle(x + f * 70 * s, y - 170 * s, 40 * s, st)
    c.ellipse(x + f * 46 * s, y - 166 * s, 22 * s, 36 * s, "#3e4244")
    c.c.drawPath(smooth_path([(x + f * 96 * s, y - 176 * s), (x + f * 112 * s, y - 130 * s), (x + f * 104 * s, y - 70 * s),
                              (x + f * 90 * s, y - 70 * s), (x + f * 88 * s, y - 140 * s)], True, k=0.16), paint(st))
    for lx in (-62, -26, 22, 52):
        c.rect(x + f * lx * s - 13 * s, y - 116 * s, x + f * lx * s + 13 * s, y - 60 * s, st)


@prop
def reeds(c, L, x, y, s=1.0, **k):
    art.reeds(c, y, x - 300 * s, x + 300 * s, "#060a08", n=int(120 * s), hmin=50, hmax=170)


@prop
def dune(c, L, x, y, s=1.0, color="#34322a", **k):
    """A mound of sand. Draw it after a building to bury the building's lower part."""
    c.c.drawPath(smooth_path([(x - 620 * s, y + 40), (x - 300 * s, y - 120 * s), (x, y - 260 * s), (x + 280 * s, y - 150 * s),
                              (x + 620 * s, y + 40), (x + 620 * s, y + 400), (x - 620 * s, y + 400)], True, k=0.16),
                 paint(color))
    c.line([(x - 300 * s, y - 120 * s), (x, y - 260 * s), (x + 280 * s, y - 150 * s)], "#6a665a", 2, 0.35)


@prop
def pond(c, L, x, y, s=1.0, **k):
    c.ellipse(x, y, 300 * s, 46 * s, "#0c1c26")
    c.ellipse(x - 40 * s, y - 6 * s, 120 * s, 8 * s, "#3a5868", 0.4)


@prop
def campfire(c, L, x, y, s=1.0, **k):
    for a in (-0.5, 0.5):
        c.line([(x - 40 * s, y - a * 10), (x + 40 * s, y + a * 10)], "#1a100a", 12 * s)
    return [(x, y - 30 * s, (1.0, 0.5, 0.15), 130 * s, True)]


@prop
def dogman(c, L, x, y, s=1.0, **k):
    """The legend's creature: a tall upright figure with a dog's head, half hidden, eyes catching the light."""
    art.figure(c, x, y, 420 * s, color="#020303", coat=True, arms=((14, 8), (-14, -8)))
    hy = y - 404 * s
    c.poly([(x - 34 * s, hy), (x + 20 * s, hy - 20 * s), (x + 78 * s, hy + 14 * s), (x + 20 * s, hy + 36 * s),
            (x - 30 * s, hy + 34 * s)], "#020303")
    for ex in (-26, 6):
        c.poly([(x + ex * s, hy - 6 * s), (x + (ex + 6) * s, hy - 50 * s), (x + (ex + 22) * s, hy - 10 * s)], "#020303")
    return [(x + 14 * s, hy + 6 * s, (1.0, 0.85, 0.3), 5 * s, False), (x + 34 * s, hy + 10 * s, (1.0, 0.85, 0.3), 5 * s, False)]


# ------------------------------------------------------------------------------------------- buildings

def _box(c, L, x0, top, x1, y, wall, rows, cols, lit, seed, ww=30, wh=64, k=0.55, arch=None):
    c.rect(x0, top, x1, y, wall)
    hgt = (y - top) / rows
    for r_ in range(rows):
        for j in range(cols):
            wx = x0 + (x1 - x0) * (j + 0.5) / cols - ww / 2
            wy = top + hgt * r_ + (hgt - wh) * 0.4
            _win(c, L, wx, wy, wx + ww, wy + wh, hash2(j + seed, r_, 5) < lit, k=k)
            if arch:
                c.c.drawPath(smooth_path([(wx - 3, wy + 4), (wx + ww / 2, wy - ww * 0.4), (wx + ww + 3, wy + 4)], False),
                             paint(arch, stroke=4))


@prop
def farm(c, L, x, y, s=1.0, lit=1, truck=False, **k):
    """A farmstead: a gable farmhouse with a porch, a gambrel barn, a silo and a board fence."""
    hx = x - 190 * s
    c.rect(hx - 120 * s, y - 170 * s, hx + 120 * s, y, "#0b0c0c")
    c.poly([(hx - 136 * s, y - 166 * s), (hx, y - 280 * s), (hx + 136 * s, y - 166 * s)], "#080909")
    c.rect(hx - 140 * s, y - 80 * s, hx + 140 * s, y - 70 * s, "#080909")
    for j, wx in enumerate((-80, 50)):
        _win(c, L, hx + wx * s, y - 140 * s, hx + (wx + 34) * s, y - 92 * s, lit and j == 0)
    bx = x + 200 * s
    c.rect(bx - 150 * s, y - 180 * s, bx + 150 * s, y, "#1a0c0a")
    c.poly([(bx - 160 * s, y - 176 * s), (bx - 110 * s, y - 270 * s), (bx, y - 320 * s), (bx + 110 * s, y - 270 * s),
            (bx + 160 * s, y - 176 * s)], "#0a0808")
    c.rect(bx - 50 * s, y - 110 * s, bx + 50 * s, y, "#0c0606")
    c.line([(bx - 50 * s, y - 110 * s), (bx + 50 * s, y)], "#3a2a22", 3 * s)
    c.line([(bx + 50 * s, y - 110 * s), (bx - 50 * s, y)], "#3a2a22", 3 * s)
    sx = x + 420 * s
    c.rect(sx - 40 * s, y - 330 * s, sx + 40 * s, y, "#15181a")
    c.c.drawPath(smooth_path([(sx - 42 * s, y - 328 * s), (sx, y - 380 * s), (sx + 42 * s, y - 328 * s)], True),
                 paint("#0c0e10"))
    for j in range(12):
        fx = x + (-520 + j * 50) * s
        c.rect(fx, y - 50 * s, fx + 6 * s, y + 6 * s, INK)
    c.rect(x - 520 * s, y - 40 * s, x + 40 * s, y - 34 * s, INK)
    if truck:
        truck_(c, L, x - 20 * s, y + 60 * s, s * 0.9)


def truck_(c, L, x, y, s=1.0, **k):
    c.rect(x - 150 * s, y - 100 * s, x + 40 * s, y - 34 * s, "#0c0d0e")
    for j in range(3):
        c.rect(x + (-140 + j * 60) * s, y - 150 * s, x + (-96 + j * 60) * s, y - 100 * s, "#1c140c")
    c.rect(x + 40 * s, y - 120 * s, x + 110 * s, y - 34 * s, "#0c0d0e")
    c.rect(x + 110 * s, y - 80 * s, x + 170 * s, y - 34 * s, "#0c0d0e")
    for wx in (-90, 120):
        c.circle(x + wx * s, y - 26 * s, 28 * s, "#030405")


PROPS["truck"] = truck_


@prop
def cabin(c, L, x, y, s=1.0, lit=True, cross=False, **k):
    """A log cabin; cross=True makes it a log chapel."""
    c.rect(x - 130 * s, y - 130 * s, x + 130 * s, y, "#0b0908")
    for j in range(7):
        c.line([(x - 130 * s, y - (16 + j * 17) * s), (x + 130 * s, y - (16 + j * 17) * s)], "#2a1c12", 2, 0.8)
    c.poly([(x - 148 * s, y - 126 * s), (x, y - 232 * s), (x + 148 * s, y - 126 * s)], "#080706")
    c.rect(x - 22 * s, y - 80 * s, x + 22 * s, y, "#050404")
    _win(c, L, x - 96 * s, y - 96 * s, x - 62 * s, y - 50 * s, lit)
    if cross:
        c.rect(x - 4 * s, y - 290 * s, x + 4 * s, y - 228 * s, "#070605")
        c.rect(x - 20 * s, y - 274 * s, x + 20 * s, y - 266 * s, "#070605")
    else:
        c.rect(x + 70 * s, y - 250 * s, x + 96 * s, y - 170 * s, "#070605")


@prop
def chapel(c, L, x, y, s=1.0, lit=False, burning=False, **k):
    """A white frame country chapel with a small belfry. burning=True: fire in the windows and the roof."""
    wall = "#3a3d3c" if not burning else "#1a1210"
    c.rect(x - 150 * s, y - 190 * s, x + 150 * s, y, wall)
    c.poly([(x - 166 * s, y - 186 * s), (x, y - 300 * s), (x + 166 * s, y - 186 * s)], "#0c0c0c")
    c.rect(x - 34 * s, y - 370 * s, x + 34 * s, y - 280 * s, wall)
    c.poly([(x - 44 * s, y - 366 * s), (x, y - 440 * s), (x + 44 * s, y - 366 * s)], "#0c0c0c")
    c.rect(x - 24 * s, y - 100 * s, x + 24 * s, y, "#0a0808")
    out = []
    for wx in (-116, -70, 70, 116):
        c.rect(x + (wx - 13) * s, y - 150 * s, x + (wx + 13) * s, y - 70 * s, "#0a0808")
        if lit or burning:
            L.rect(x + (wx - 13) * s, y - 150 * s, x + (wx + 13) * s, y - 70 * s, "#ff8a30" if burning else WARM, 0.9)
        if burning:
            out.append((x + wx * s, y - 120 * s, (1.0, 0.45, 0.1), 70 * s, True))
    if burning:
        for fx, fy, fr in ((-60, 300, 150), (40, 330, 190), (110, 250, 120), (0, 200, 240)):
            out.append((x + fx * s, y - fy * s, (1.0, 0.4, 0.08), fr * s, True))
    return out


@prop
def pavilion(c, L, x, y, s=1.0, **k):
    """An open-sided picnic pavilion: a low roof on posts."""
    c.poly([(x - 190 * s, y - 130 * s), (x, y - 200 * s), (x + 190 * s, y - 130 * s)], "#0c0d0e")
    c.rect(x - 190 * s, y - 132 * s, x + 190 * s, y - 120 * s, "#15181a")
    for px in (-170, -60, 60, 170):
        c.rect(x + (px - 5) * s, y - 122 * s, x + (px + 5) * s, y, "#0c0d0e")


@prop
def mansion(c, L, x, y, s=1.0, style="italianate", lit=0.4, seed=0, **k):
    """A big brick house. style="italianate": three storeys with bracketed eaves and a square central tower (the
    Dole Mansion); "settlement": a two-storey Italianate brick house with a columned porch and a cupola (Hull-House);
    "victorian": a tall frame Queen Anne with a corner turret and a porch."""
    if style == "victorian":
        K.victorian(c, L, x - 300 * s, y, s * 1.2, lit=k.get("wins", (0, 1, 0, 0, 0, 0)))
        return
    rows = 3 if style == "italianate" else 2
    w, h = 330 * s, (130 * rows) * s
    wall = "#2a1614" if style == "italianate" else "#32181a"
    _box(c, L, x - w, y - h, x + w, y, wall, rows, 7, lit, seed, ww=30 * s, wh=74 * s, arch="#7a7264")
    c.rect(x - w - 16 * s, y - h - 16 * s, x + w + 16 * s, y - h, "#0c0b0a")
    c.poly([(x - w - 10 * s, y - h - 14 * s), (x - w + 60 * s, y - h - 60 * s), (x + w - 60 * s, y - h - 60 * s),
            (x + w + 10 * s, y - h - 14 * s)], "#0e0d0c")
    if style == "italianate":
        c.rect(x - 60 * s, y - h - 170 * s, x + 60 * s, y - h, wall)
        c.rect(x - 72 * s, y - h - 184 * s, x + 72 * s, y - h - 168 * s, "#0c0b0a")
        c.poly([(x - 66 * s, y - h - 182 * s), (x - 30 * s, y - h - 240 * s), (x + 30 * s, y - h - 240 * s),
                (x + 66 * s, y - h - 182 * s)], "#0e0d0c")
        _win(c, L, x - 16 * s, y - h - 140 * s, x + 16 * s, y - h - 70 * s, lit > 0.2)
    else:
        c.rect(x - 44 * s, y - h - 120 * s, x + 44 * s, y - h - 56 * s, wall)
        c.poly([(x - 56 * s, y - h - 118 * s), (x, y - h - 170 * s), (x + 56 * s, y - h - 118 * s)], "#0e0d0c")
    c.rect(x - 150 * s, y - 130 * s, x + 150 * s, y - 116 * s, "#8a8274")                 # the porch
    for px in (-140, -70, 70, 140):
        c.rect(x + (px - 6) * s, y - 118 * s, x + (px + 6) * s, y, "#8a8274")
    c.rect(x - 26 * s, y - 100 * s, x + 26 * s, y, "#0a0808")


@prop
def rowhouses(c, L, x, y, s=1.0, n=6, lit=0.3, seed=0, small=False, **k):
    """A row of city houses or shopfronts (small=True: a row of identical little wartime houses)."""
    if small:
        for j in range(n):
            hx = x + (j - (n - 1) / 2) * 190 * s
            c.rect(hx - 70 * s, y - 80 * s, hx + 70 * s, y, "#101314")
            c.poly([(hx - 84 * s, y - 78 * s), (hx, y - 140 * s), (hx + 84 * s, y - 78 * s)], "#0a0c0d")
            _win(c, L, hx - 44 * s, y - 60 * s, hx - 14 * s, y - 28 * s, hash2(j, seed, 2) < lit + 0.3)
            c.rect(hx + 14 * s, y - 60 * s, hx + 40 * s, y, "#060708")
        return
    for j in range(n):
        bw = 190 * s
        bx = x + (j - n / 2) * bw
        hh = (300 + 90 * hash2(j, seed, 1)) * s
        wall = ("#1c1210", "#241412", "#1a1412", "#201614")[j % 4]
        _box(c, L, bx, y - hh, bx + bw - 6 * s, y, wall, 3, 3, lit, seed + j * 7, ww=30 * s, wh=58 * s)
        c.rect(bx - 4 * s, y - hh - 16 * s, bx + bw - 2 * s, y - hh, "#0c0a09")


@prop
def clinic(c, L, x, y, s=1.0, sign="CLINIC", lit=0.5, **k):
    """A low, flat-roofed 1970s medical building with a band of windows and a sign by the door."""
    c.rect(x - 400 * s, y - 170 * s, x + 400 * s, y, "#2a2622")
    c.rect(x - 416 * s, y - 190 * s, x + 416 * s, y - 166 * s, "#15130f")
    for j in range(9):
        wx = x + (-380 + j * 84) * s
        if 3 <= j <= 4:
            continue
        _win(c, L, wx, y - 130 * s, wx + 64 * s, y - 60 * s, hash2(j, 3, 1) < lit, col="#0c1014")
    c.rect(x - 110 * s, y - 150 * s, x + 50 * s, y, "#0c1014")
    L.rect(x - 110 * s, y - 150 * s, x + 50 * s, y, "#cfe0ff", 0.35)
    return ("sign", sign, x - 30 * s, y - 220 * s, 260 * s, 50 * s) if sign else None


@prop
def library(c, L, x, y, s=1.0, sign="LIBRARY", lit=0.6, **k):
    """A one-storey brick public library with tall windows and a sign over the entrance."""
    c.rect(x - 420 * s, y - 220 * s, x + 420 * s, y, "#2c1a14")
    c.rect(x - 436 * s, y - 240 * s, x + 436 * s, y - 216 * s, "#12100e")
    for j in range(8):
        wx = x + (-390 + j * 100) * s
        if j in (3, 4):
            continue
        _win(c, L, wx, y - 190 * s, wx + 56 * s, y - 40 * s, hash2(j, 9, 1) < lit, col="#0a0c10")
    c.rect(x - 90 * s, y - 250 * s, x + 110 * s, y, "#1a1210")
    _win(c, L, x - 60 * s, y - 150 * s, x + 80 * s, y, True, col="#0a0c10", k=0.5)
    return ("sign", sign, x + 10 * s, y - 200 * s, 190 * s, 44 * s)


@prop
def plant(c, L, x, y, s=1.0, lit=0.7, **k):
    """A wartime ordnance plant: long low loading-line buildings, a water tower, floodlights and a wire fence."""
    for j, (bx, bw) in enumerate(((-360, 330), (20, 420))):
        c.rect(x + bx * s, y - 110 * s, x + (bx + bw) * s, y, "#15171a")
        c.poly([(x + bx * s, y - 108 * s), (x + (bx + 30) * s, y - 140 * s), (x + (bx + bw - 30) * s, y - 140 * s),
                (x + (bx + bw) * s, y - 108 * s)], "#0c0e10")
        for t in range(int(bw // 46)):
            _win(c, L, x + (bx + 14 + t * 46) * s, y - 84 * s, x + (bx + 40 + t * 46) * s, y - 50 * s,
                 hash2(t, j, 4) < lit)
    tx = x - 80 * s
    for lx in (-34, 34):
        c.line([(tx + lx * s, y), (tx + lx * 0.5 * s, y - 300 * s)], INK, 5 * s)
    c.ellipse(tx, y - 340 * s, 70 * s, 48 * s, "#12161a")
    c.rect(x + 380 * s, y - 400 * s, x + 410 * s, y - 110 * s, "#0c0e10")
    out = []
    for fx in (-420, 300):
        c.rect(x + fx * s - 3, y - 230 * s, x + fx * s + 3, y, INK)
        out.append((x + fx * s, y - 236 * s, (1.0, 0.92, 0.75), 90 * s, False))
    for j in range(24):
        c.rect(x + (-520 + j * 46) * s, y + 10 * s, x + (-517 + j * 46) * s, y + 80 * s, INK)
    for t in range(3):
        c.line([(x - 520 * s, y + (20 + t * 20) * s), (x + 540 * s, y + (20 + t * 20) * s)], "#2a3034", 1.5, 0.8)
    return out


@prop
def bunker(c, L, x, y, s=1.0, **k):
    """An earth-covered ammunition bunker (an "igloo"): a grassed mound with a concrete front and a steel door."""
    c.c.drawPath(smooth_path([(x - 230 * s, y), (x - 150 * s, y - 110 * s), (x, y - 160 * s), (x + 150 * s, y - 110 * s),
                              (x + 230 * s, y)], True, k=0.16), paint("#0a100c"))
    c.poly([(x - 90 * s, y), (x - 76 * s, y - 126 * s), (x + 76 * s, y - 126 * s), (x + 90 * s, y)], "#4a4c4a")
    c.rect(x - 40 * s, y - 96 * s, x + 40 * s, y, "#15181a")
    c.line([(x, y - 96 * s), (x, y)], "#2a3034", 3 * s)


@prop
def gatehouse(c, L, x, y, s=1.0, lit=0.15, **k):
    """A limestone prison front: a castle-like gatehouse with crenellated towers, and the wall running off both sides."""
    st = "#5a5648"
    c.rect(x - 560 * s, y - 210 * s, x + 560 * s, y, "#46433a")
    for j in range(22):
        c.rect(x + (-560 + j * 52) * s, y - 228 * s, x + (-534 + j * 52) * s, y - 208 * s, "#46433a")
    _box(c, L, x - 190 * s, y - 330 * s, x + 190 * s, y, st, 3, 5, lit, 2, ww=26 * s, wh=62 * s)
    for tx in (-190, 190):
        c.rect(x + (tx - 56) * s, y - 440 * s, x + (tx + 56) * s, y, st)
        for j in range(4):
            c.rect(x + (tx - 56 + j * 30) * s, y - 462 * s, x + (tx - 40 + j * 30) * s, y - 438 * s, st)
        for wy in (380, 280, 180):
            c.rect(x + (tx - 8) * s, y - wy * s, x + (tx + 8) * s, y - (wy - 50) * s, "#0a0a0a")
    c.c.drawPath(smooth_path([(x - 50 * s, y), (x - 50 * s, y - 110 * s), (x, y - 150 * s), (x + 50 * s, y - 110 * s),
                              (x + 50 * s, y)], True, k=0.14), paint("#0a0a0a"))
    for j in range(6):
        c.line([(x + (-40 + j * 16) * s, y - 120 * s), (x + (-40 + j * 16) * s, y)], "#2a2a28", 3 * s)


@prop
def quarry(c, L, x, y, s=1.0, **k):
    """A limestone quarry: a stepped rock face, cut blocks, a wooden derrick and a half-built wall."""
    for j in range(4):
        c.rect(x + (-560 + j * 60) * s, y - (420 - j * 100) * s, x + (-100 + j * 90) * s, y, ("#4a4840", "#545046")[j % 2])
    c.line([(x + 250 * s, y), (x + 250 * s, y - 380 * s)], "#1a1410", 9 * s)
    c.line([(x + 250 * s, y - 60 * s), (x + 60 * s, y - 330 * s)], "#1a1410", 7 * s)
    c.line([(x + 250 * s, y - 380 * s), (x + 60 * s, y - 330 * s)], "#0c0a08", 2 * s)
    c.line([(x + 60 * s, y - 330 * s), (x + 60 * s, y - 170 * s)], "#0c0a08", 2 * s)
    c.rect(x + 20 * s, y - 170 * s, x + 100 * s, y - 120 * s, "#6a665a")
    for j in range(5):
        for t in range(1 + (j < 3) + (j < 2)):
            bx = x + (330 + j * 76) * s
            c.rect(bx, y - (52 + t * 52) * s, bx + 72 * s, y - t * 52 * s, "#5a5648")
            c.line([(bx, y - (52 + t * 52) * s), (bx + 72 * s, y - (52 + t * 52) * s)], "#8a8676", 2, 0.6)
    walkers(c, x + 60 * s, x + 260 * s, y + 30 * s, 120 * s, 4, seed=5)


@prop
def sawmill(c, L, x, y, s=1.0, lit=0.5, sunk=0.0, **k):
    """A lumber town: a big sawmill with a stack, a few frame houses and stacks of sawn lumber."""
    c.rect(x - 330 * s, y - 210 * s, x - 20 * s, y, "#1c1410")
    c.poly([(x - 346 * s, y - 206 * s), (x - 175 * s, y - 300 * s), (x - 4 * s, y - 206 * s)], "#0e0b09")
    for j in range(5):
        _win(c, L, x + (-310 + j * 58) * s, y - 160 * s, x + (-284 + j * 58) * s, y - 110 * s, hash2(j, 2, 2) < lit)
    c.rect(x - 60 * s, y - 420 * s, x - 30 * s, y - 200 * s, "#0e0b09")
    for j, hx in enumerate((110, 290, 450)):
        hh = (150 + j * 20) * s
        c.rect(x + (hx - 70) * s, y - hh, x + (hx + 70) * s, y, "#18120e")
        c.poly([(x + (hx - 84) * s, y - hh + 4), (x + hx * s, y - hh - 80 * s), (x + (hx + 84) * s, y - hh + 4)], "#0c0a08")
        _win(c, L, x + (hx - 16) * s, y - hh + 30 * s, x + (hx + 16) * s, y - hh + 80 * s, hash2(j, 5, 2) < lit)
    for j in range(4):
        for t in range(4):
            c.rect(x + (-520 + j * 46) * s, y - (20 + t * 18) * s, x + (-480 + j * 46) * s, y - (6 + t * 18) * s, "#3a2c1c")


@prop
def fort(c, L, x, y, s=1.0, **k):
    """A small log stockade with a blockhouse and a flag (a French fort of the 1670s)."""
    for j in range(26):
        px = x + (-330 + j * 26) * s
        hh = (150 + 14 * hash2(j, 1, 9)) * s
        c.poly([(px, y), (px, y - hh), (px + 12 * s, y - hh - 22 * s), (px + 24 * s, y - hh), (px + 24 * s, y)], "#120d09")
    c.rect(x - 70 * s, y - 250 * s, x + 70 * s, y - 130 * s, "#0e0a07")
    c.poly([(x - 90 * s, y - 246 * s), (x, y - 320 * s), (x + 90 * s, y - 246 * s)], "#0a0705")
    c.line([(x + 180 * s, y - 150 * s), (x + 180 * s, y - 400 * s)], INK, 4 * s)
    c.rect(x + 182 * s, y - 400 * s, x + 250 * s, y - 356 * s, "#8a8674", 0.9)


@prop
def lightstation(c, L, x, y, s=1.0, lit=True, **k):
    """A brick keeper's house with an octagonal brick light tower attached (the White River Light Station)."""
    br = "#4a3a2a"
    c.rect(x - 60 * s, y - 180 * s, x + 260 * s, y, br)
    c.poly([(x - 76 * s, y - 176 * s), (x + 100 * s, y - 280 * s), (x + 276 * s, y - 176 * s)], "#12100e")
    for j, wx in enumerate((0, 90, 180)):
        _win(c, L, x + wx * s, y - 130 * s, x + (wx + 36) * s, y - 60 * s, lit and j != 1)
    c.poly([(x - 190 * s, y), (x - 176 * s, y - 380 * s), (x - 84 * s, y - 380 * s), (x - 70 * s, y)], br)
    c.line([(x - 130 * s, y), (x - 130 * s, y - 380 * s)], "#3a2c20", 3 * s)
    c.rect(x - 196 * s, y - 396 * s, x - 64 * s, y - 378 * s, "#12100e")
    c.rect(x - 166 * s, y - 450 * s, x - 94 * s, y - 396 * s, "#0c0e10")
    c.poly([(x - 176 * s, y - 448 * s), (x - 130 * s, y - 500 * s), (x - 84 * s, y - 448 * s)], "#12100e")
    for wy in (300, 180):
        c.rect(x - 142 * s, y - wy * s, x - 118 * s, y - (wy - 50) * s, "#0a0808")
    return [(x - 130 * s, y - 424 * s, (1.0, 0.92, 0.7), 60 * s, False)] if lit else None


@prop
def capitol(c, L, x, y, s=1.0, **k):
    """A domed capitol far off, pale against the sky (for "served in Congress")."""
    st = "#5a5c5c"
    c.rect(x - 380 * s, y - 120 * s, x + 380 * s, y, st)
    for j in range(20):
        c.rect(x + (-370 + j * 38) * s, y - 110 * s, x + (-358 + j * 38) * s, y, "#3a3c3c")
    c.poly([(x - 120 * s, y - 118 * s), (x, y - 170 * s), (x + 120 * s, y - 118 * s)], st)
    c.rect(x - 90 * s, y - 240 * s, x + 90 * s, y - 150 * s, st)
    c.c.drawPath(smooth_path([(x - 84 * s, y - 236 * s), (x - 60 * s, y - 330 * s), (x, y - 372 * s), (x + 60 * s, y - 330 * s),
                              (x + 84 * s, y - 236 * s)], True, k=0.16), paint(st))
    c.rect(x - 10 * s, y - 420 * s, x + 10 * s, y - 366 * s, st)


@prop
def cityfire(c, L, x, y, s=1.0, **k):
    """A city skyline far off with a great fire behind it (Chicago, 1871)."""
    out = []
    for j in range(16):
        bw = 60 * s
        bx = x + (-480 + j * 60) * s
        hh = (90 + 160 * hash2(j, 3, 1)) * s
        c.rect(bx, y - hh, bx + bw - 4, y, "#070606")
    for fx, fr in ((-300, 200), (-60, 280), (220, 220)):
        out.append((x + fx * s, y - 150 * s, (1.0, 0.4, 0.1), fr * s, True))
    return out


# ------------------------------------------------------------------------------------------- rails and roads

@prop
def tracks(c, L, x, y, s=1.0, **k):
    c.rect(-20, y, W + 20, y + 8 * s, "#34383a")
    for j in range(0, W + 40, int(34 * s)):
        c.rect(j, y + 8 * s, j + 18 * s, y + 18 * s, "#141618")


@prop
def railcars(c, L, x, y, s=1.0, n=3, what="sleeper", lit=0.5, loco=False, **k):
    """Old railroad cars on a track: what="sleeper" (wooden circus sleeping cars with lit windows), "coach" (steel
    troop coaches) or "box". loco=True puts a steam locomotive at the right-hand end."""
    col = {"sleeper": "#2a1410", "coach": "#101416", "box": "#3a1c14"}[what]
    for j in range(n):
        bx = x + (j - n / 2) * 330 * s
        c.rect(bx, y - 150 * s, bx + 310 * s, y - 30 * s, col)
        c.c.drawPath(smooth_path([(bx - 6 * s, y - 148 * s), (bx + 30 * s, y - 174 * s), (bx + 280 * s, y - 174 * s),
                                  (bx + 316 * s, y - 148 * s)], True, k=0.1), paint("#0c0a09"))
        if what != "box":
            for t in range(8):
                _win(c, L, bx + (20 + t * 35) * s, y - 122 * s, bx + (42 + t * 35) * s, y - 86 * s,
                     hash2(t, j, 6) < lit)
        for wx in (40, 86, 224, 270):
            c.circle(bx + wx * s, y - 16 * s, 20 * s, "#050506")
    out = []
    if loco:
        lx = x + (n / 2) * 330 * s + 20 * s
        c.rect(lx, y - 120 * s, lx + 230 * s, y - 30 * s, INK)
        c.rect(lx, y - 180 * s, lx + 80 * s, y - 30 * s, INK)
        c.rect(lx + 170 * s, y - 180 * s, lx + 196 * s, y - 120 * s, INK)
        for wx in (40, 110, 180):
            c.circle(lx + wx * s, y - 22 * s, 26 * s, "#050506")
        out.append((lx + 236 * s, y - 100 * s, (1.0, 0.9, 0.6), 60 * s, False))
    return out


@prop
def car(c, L, x, y, s=1.0, era=1920, **k):
    """A car at the curb: era=1920 a touring car; era=1955 a sedan."""
    if era < 1940:
        hd = touring_car(c, x, y, s, color="#020304")
        return [(hd[0], hd[1], (1.0, 0.9, 0.6), 50 * s, False)]
    from reel_haunts import car as car50
    car50(c, x, y, s * 0.8)


@prop
def roadgate(c, L, x, y, s=1.0, **k):
    """A dead-end road closed by a steel gate, running back into the trees."""
    c.poly([(x - 260 * s, y + 500 * s), (x + 260 * s, y + 500 * s), (x + 60 * s, y - 60 * s), (x - 60 * s, y - 60 * s)], "#15181a")
    c.line([(x, y + 480 * s), (x, y - 40 * s)], "#3a3a30", 3 * s, 0.6)
    if not k.get("gate", True):                       # gate=False: an open road
        return
    for px in (-190, 190):
        c.rect(x + (px - 8) * s, y - 20 * s, x + (px + 8) * s, y + 130 * s, "#3a3d3a")
    for t in range(3):
        c.rect(x - 190 * s, y + (10 + t * 34) * s, x + 190 * s, y + (20 + t * 34) * s, "#5a5d54")
    c.line([(x - 190 * s, y + 20 * s), (x + 190 * s, y + 88 * s)], "#5a5d54", 6 * s)


@prop
def fence(c, L, x, y, s=1.0, **k):
    art.fence(c, y, x - 520 * s, x + 520 * s, spacing=int(46 * s), h=int(90 * s))


@prop
def signpost(c, L, x, y, s=1.0, text="", marker=False, **k):
    """A sign on posts (marker=True: a cast historical marker on one post). The text must be what is really there."""
    if marker:
        c.rect(x - 6 * s, y - 150 * s, x + 6 * s, y, "#1a1c1a")
        return ("sign", text, x, y - 230 * s, 330 * s, 150 * s, (22, 40, 30), (214, 196, 130))
    for px in (-120, 120):
        c.rect(x + (px - 5) * s, y - 130 * s, x + (px + 5) * s, y, "#1a140e")
    return ("sign", text, x, y - 150 * s, 300 * s, 70 * s, (60, 44, 28), (226, 214, 186))


@prop
def chain(c, L, x, y, s=1.0, n=26, **k):
    """A heavy anchor chain laid across a lawn, with an anchor at one end."""
    for j in range(n):
        lx = x + (-420 + j * 32) * s
        ly = y + 12 * s * math.sin(j * 0.5)
        c.c.drawOval(__import__("skia").Rect.MakeXYWH(lx, ly - 12 * s, 36 * s, 22 * s), paint("#6a6e70", stroke=6 * s))
    ax = x + 440 * s
    c.line([(ax, y - 120 * s), (ax, y + 30 * s)], "#4a4e50", 12 * s)
    c.c.drawPath(smooth_path([(ax - 70 * s, y - 30 * s), (ax - 40 * s, y + 30 * s), (ax, y + 44 * s), (ax + 40 * s, y + 30 * s),
                              (ax + 70 * s, y - 30 * s)], False), paint("#4a4e50", stroke=12 * s))
    c.line([(ax - 40 * s, y - 100 * s), (ax + 40 * s, y - 100 * s)], "#4a4e50", 10 * s)


@prop
def people(c, L, x, y, s=1.0, n=8, spread=300, seed=0, queue=False, **k):
    """A group of small anonymous figures (queue=True: a line waiting, facing right)."""
    walkers(c, x - spread * s, x + spread * s, y, 150 * s, n, seed=seed, color="#030405")


@prop
def lumberjacks(c, L, x, y, s=1.0, **k):
    walkers(c, x - 160 * s, x + 160 * s, y, 150 * s, 4, seed=3, color="#030405")
    c.line([(x + 180 * s, y), (x + 230 * s, y - 120 * s)], "#2a2016", 5 * s)


# ------------------------------------------------------------------------------------------- interiors

@prop
def window(c, L, x, y, s=1.0, moon=True, **k):
    c.rect(x - 90 * s, y - 330 * s, x + 90 * s, y, "#0a1420")
    c.rect(x - 98 * s, y - 338 * s, x + 98 * s, y - 330 * s, "#3a281c")
    c.line([(x, y - 330 * s), (x, y)], "#3a281c", 6 * s)
    c.line([(x - 90 * s, y - 165 * s), (x + 90 * s, y - 165 * s)], "#3a281c", 6 * s)
    L.rect(x - 90 * s, y - 330 * s, x + 90 * s, y, "#6a8aa8", 0.25)


@prop
def door(c, L, x, y, s=1.0, ajar=False, locked=False, light=True, **k):
    c.rect(x - 80 * s, y - 380 * s, x + 80 * s, y, "#24160e")
    c.rect(x - 66 * s, y - 366 * s, x + 66 * s, y, "#1a100a")
    if ajar:
        c.poly([(x - 66 * s, y - 366 * s), (x + 10 * s, y - 350 * s), (x + 10 * s, y + 14 * s), (x - 66 * s, y)], "#2e1c12")
        if light:
            L.rect(x + 10 * s, y - 366 * s, x + 66 * s, y, WARM, 0.5)
    else:
        for py in (350, 170):
            c.rect(x - 50 * s, y - py * s, x + 50 * s, y - (py - 150) * s, "#20130c")
    c.circle(x + (46 if not ajar else -4) * s, y - 180 * s, 7 * s, "#8a7a4a")
    if locked:
        c.rect(x + 30 * s, y - 230 * s, x + 60 * s, y - 214 * s, "#8a7a4a")


@prop
def seance(c, L, x, y, s=1.0, stick=True, **k):
    """A dark parlour: a round table with empty chairs, and a bass drum on a stand with its stick in the air above it."""
    for cx_ in (-250, 250, -120, 120):
        c.rect(x + (cx_ - 34) * s, y - 250 * s, x + (cx_ + 34) * s, y - 110 * s, "#1a0f0a")
        c.rect(x + (cx_ - 40) * s, y - 120 * s, x + (cx_ + 40) * s, y - 100 * s, "#1a0f0a")
        c.rect(x + (cx_ - 36) * s, y - 100 * s, x + (cx_ - 28) * s, y, "#1a0f0a")
        c.rect(x + (cx_ + 28) * s, y - 100 * s, x + (cx_ + 36) * s, y, "#1a0f0a")
    c.ellipse(x, y - 150 * s, 230 * s, 44 * s, "#2a1810")
    c.rect(x - 16 * s, y - 150 * s, x + 16 * s, y, "#1c100a")
    dx, dy = x + 420 * s, y - 190 * s
    c.circle(dx, dy, 124 * s, "#3a2a1c")
    c.circle(dx, dy, 108 * s, "#b8ac90")
    c.line([(dx - 90 * s, y), (dx - 40 * s, dy + 110 * s)], "#1a0f0a", 8 * s)
    c.line([(dx + 90 * s, y), (dx + 40 * s, dy + 110 * s)], "#1a0f0a", 8 * s)
    if stick:
        c.line([(dx - 30 * s, dy - 300 * s), (dx - 6 * s, dy - 140 * s)], "#6a5030", 9 * s)
        c.circle(dx - 4 * s, dy - 128 * s, 22 * s, "#c8bca0")


@prop
def parlor(c, L, x, y, s=1.0, mirror=True, **k):
    """A keeper's parlour: a table laid with silverware, an oil lamp, a chair and a mirror on the wall."""
    c.rect(x - 260 * s, y - 160 * s, x + 260 * s, y - 140 * s, "#2a1810")
    for lx in (-240, 240):
        c.rect(x + (lx - 8) * s, y - 140 * s, x + (lx + 8) * s, y, "#1c100a")
    c.rect(x - 280 * s, y - 150 * s, x + 280 * s, y - 136 * s, "#8a8272", 0.5)
    for px in (-150, 0, 150):
        c.ellipse(x + px * s, y - 166 * s, 44 * s, 9 * s, "#b8b4a8")
        c.line([(x + (px - 62) * s, y - 172 * s), (x + (px - 62) * s, y - 150 * s)], "#d8d8d0", 3 * s)
        c.line([(x + (px + 62) * s, y - 176 * s), (x + (px + 74) * s, y - 152 * s)], "#d8d8d0", 3 * s)
    c.rect(x + 210 * s, y - 230 * s, x + 236 * s, y - 166 * s, "#5a4420")
    out = [(x + 223 * s, y - 246 * s, (1.0, 0.75, 0.4), 150 * s, True)]
    if mirror:
        c.ellipse(x - 300 * s, y - 520 * s, 96 * s, 130 * s, "#5a4420")
        c.ellipse(x - 300 * s, y - 520 * s, 82 * s, 116 * s, "#1c2a30")
        c.ellipse(x - 296 * s, y - 540 * s, 34 * s, 44 * s, "#5a7078", 0.28)
    return out


@prop
def smoke(c, L, x, y, s=1.0, **k):
    """A thin curl of smoke rising (cigar smoke with no smoker)."""
    pts = [(x + 26 * s * math.sin(t * 0.9), y - t * 60 * s) for t in range(9)]
    c.c.drawPath(smooth_path(pts, False), paint("#9aa4a8", a=0.35, stroke=10 * s, blur=6))
    c.c.drawPath(smooth_path([(px + 30 * s, py - 20 * s) for px, py in pts[2:]], False),
                 paint("#9aa4a8", a=0.2, stroke=16 * s, blur=10))


@prop
def stairs(c, L, x, y, s=1.0, **k):
    """A narrow staircase turning up into the dark, with a handrail."""
    for j in range(11):
        u = j / 10.0
        sy = y - j * 62 * s
        hw = (200 - 60 * u) * s
        ox = 90 * u * u * s
        c.rect(x + ox - hw, sy - 62 * s, x + ox + hw, sy, ("#2a1810", "#24140e")[j % 2])
        c.line([(x + ox - hw, sy - 62 * s), (x + ox + hw, sy - 62 * s)], "#4a3020", 3, 0.7)
    c.line([(x + 210 * s, y - 130 * s), (x + 250 * s, y - 760 * s)], "#3a2418", 12 * s)
    c.rect(x + 196 * s, y - 150 * s, x + 224 * s, y, "#24160e")


@prop
def bunk(c, L, x, y, s=1.0, **k):
    """A ship's cabin: an empty bunk with a blanket thrown back, and a porthole."""
    c.rect(x - 300 * s, y - 170 * s, x + 220 * s, y - 110 * s, "#2a1a10")
    c.rect(x - 300 * s, y - 110 * s, x + 220 * s, y, "#1c110a")
    c.rect(x - 290 * s, y - 196 * s, x + 210 * s, y - 166 * s, "#8a8674", 0.8)
    c.poly([(x - 60 * s, y - 196 * s), (x + 210 * s, y - 196 * s), (x + 210 * s, y - 120 * s), (x + 40 * s, y - 150 * s)], "#3a4a5a")
    c.ellipse(x - 230 * s, y - 206 * s, 50 * s, 16 * s, "#b8b4a4")
    px, py = x + 20 * s, y - 520 * s
    c.circle(px, py, 84 * s, "#6a5a30")
    c.circle(px, py, 66 * s, "#0c1c2a")
    L.circle(px, py, 66 * s, "#6a8aa8", 0.3)


@prop
def shelves(c, L, x, y, s=1.0, n=3, ramp=False, **k):
    """Library stacks: tall bookcases either side of an aisle. ramp=True: a ramp with a handrail up the middle."""
    r = np.random.default_rng(4)
    for side in (-1, 1):
        for j in range(n):
            bx = x + side * (200 + j * 150) * s
            hh = (700 - j * 60) * s
            c.rect(bx - 60 * s, y - hh, bx + 60 * s, y, "#1c120c")
            for sh in range(int(hh // (70 * s))):
                yy = y - hh + 16 * s + sh * 70 * s
                bxx = bx - 52 * s
                while bxx < bx + 46 * s:
                    bw = r.uniform(7, 16) * s
                    col = ("#5a2a20", "#2a4a3a", "#3a3a5a", "#6a5a30", "#4a2a3a")[int(r.integers(0, 5))]
                    c.rect(bxx, yy + r.uniform(0, 10) * s, bxx + bw, yy + 56 * s, col, 0.8)
                    bxx += bw + 1
    if ramp:
        c.poly([(x - 120 * s, y), (x + 120 * s, y), (x + 70 * s, y - 300 * s), (x - 70 * s, y - 300 * s)], "#3a3630")
        c.line([(x + 120 * s, y - 110 * s), (x + 70 * s, y - 400 * s)], "#8a8a80", 6 * s)
        c.line([(x - 120 * s, y - 110 * s), (x - 70 * s, y - 400 * s)], "#8a8a80", 6 * s)


@prop
def slime(c, L, x, y, s=1.0, **k):
    """A workroom wall with green slime running down it, and a paint can and ladder (the library's own story)."""
    r = np.random.default_rng(8)
    for j in range(26):
        sx = x + (-460 + j * 37) * s
        ln = r.uniform(160, 620) * s
        c.line([(sx, y - 900 * s), (sx + r.uniform(-8, 8), y - 900 * s + ln)], "#3a8a2a", r.uniform(10, 26) * s, 0.75)
        c.circle(sx, y - 900 * s + ln, r.uniform(10, 18) * s, "#4aa838", 0.8)
    c.rect(x - 470 * s, y - 930 * s, x + 500 * s, y - 880 * s, "#3a8a2a", 0.7)
    for lx in (250, 350):
        c.line([(x + lx * s, y), (x + (lx + (300 - lx) * 0.3) * s, y - 420 * s)], "#5a4a30", 9 * s)
    for t in range(5):
        c.line([(x + 262 * s, y - (60 + t * 80) * s), (x + 338 * s, y - (60 + t * 80) * s)], "#5a4a30", 6 * s)
    c.rect(x - 60 * s, y - 70 * s, x + 10 * s, y, "#8a8a84")


@prop
def examroom(c, L, x, y, s=1.0, missing=False, **k):
    """A clinic exam room: an exam table and a steel tray of instruments (missing=True: the tray is empty)."""
    c.rect(x - 380 * s, y - 150 * s, x - 40 * s, y - 120 * s, "#4a5a5a")
    c.rect(x - 380 * s, y - 190 * s, x - 280 * s, y - 150 * s, "#5a6a6a")
    for lx in (-360, -60):
        c.rect(x + (lx - 6) * s, y - 120 * s, x + (lx + 6) * s, y, "#8a9090")
    c.rect(x + 120 * s, y - 220 * s, x + 380 * s, y - 206 * s, "#a8b0b0")
    c.rect(x + 244 * s, y - 206 * s, x + 256 * s, y, "#8a9090")
    if not missing:
        for j in range(5):
            c.line([(x + (150 + j * 44) * s, y - 250 * s), (x + (170 + j * 44) * s, y - 222 * s)], "#e0e8e8", 4 * s)
    else:
        for j in range(5):
            c.line([(x + (150 + j * 44) * s, y - 250 * s), (x + (170 + j * 44) * s, y - 222 * s)], "#5a6464", 2 * s, 0.5)


@prop
def cases(c, L, x, y, s=1.0, **k):
    """Museum display cases with small objects, under picture frames."""
    for j in (-1, 0, 1):
        bx = x + j * 300 * s
        c.rect(bx - 120 * s, y - 130 * s, bx + 120 * s, y, "#24160e")
        c.rect(bx - 120 * s, y - 260 * s, bx + 120 * s, y - 130 * s, "#1a2a30", 0.6)
        L.rect(bx - 120 * s, y - 260 * s, bx + 120 * s, y - 130 * s, WARM, 0.18)
        for t in range(3):
            c.rect(bx + (-80 + t * 60) * s, y - 170 * s, bx + (-50 + t * 60) * s, y - 134 * s, "#8a7a5a")
        c.rect(bx - 70 * s, y - 520 * s, bx + 70 * s, y - 360 * s, "#5a4420")
        c.rect(bx - 56 * s, y - 506 * s, bx + 56 * s, y - 374 * s, "#2a2620")


@prop
def studio(c, L, x, y, s=1.0, phones=False, **k):
    """A 1980s radio studio: a desk with a microphone on a boom, a turntable and (phones=True) blinking phone lines."""
    c.rect(x - 420 * s, y - 150 * s, x + 420 * s, y - 120 * s, "#2a2420")
    c.rect(x - 400 * s, y - 120 * s, x + 400 * s, y, "#1a1612")
    c.rect(x - 330 * s, y - 190 * s, x - 90 * s, y - 150 * s, "#15181a")
    c.circle(x - 210 * s, y - 196 * s, 90 * s, "#0a0a0a")
    c.circle(x - 210 * s, y - 196 * s, 26 * s, "#8a2a20")
    c.line([(x + 320 * s, y - 150 * s), (x + 260 * s, y - 420 * s), (x + 80 * s, y - 360 * s)], "#5a5e60", 8 * s)
    c.ellipse(x + 60 * s, y - 352 * s, 44 * s, 26 * s, "#8a8e90")
    out = [("sign", "ON AIR", x - 250 * s, y - 760 * s, 260 * s, 80 * s, (120, 20, 16), (255, 230, 220)),
           (x - 250 * s, y - 760 * s, (1.0, 0.2, 0.15), 150 * s, True)]
    if phones:
        c.rect(x + 150 * s, y - 196 * s, x + 380 * s, y - 150 * s, "#15181a")
        for j in range(6):
            out.append((x + (172 + j * 36) * s, y - 174 * s, (1.0, 0.7, 0.2), 9 * s, True))
    return out


@prop
def telegraph(c, L, x, y, s=1.0, **k):
    """A telegraph desk at night: a key and sounder, a paper form and a green-shaded lamp."""
    c.rect(x - 380 * s, y - 150 * s, x + 380 * s, y - 126 * s, "#2a1a10")
    c.rect(x - 360 * s, y - 126 * s, x + 360 * s, y, "#1c110a")
    c.rect(x - 220 * s, y - 166 * s, x - 60 * s, y - 150 * s, "#c8c0a8")
    c.rect(x + 40 * s, y - 170 * s, x + 170 * s, y - 150 * s, "#3a2a1c")
    c.line([(x + 60 * s, y - 180 * s), (x + 150 * s, y - 196 * s)], "#b89a40", 7 * s)
    c.circle(x + 154 * s, y - 198 * s, 12 * s, "#15110d")
    c.rect(x + 262 * s, y - 280 * s, x + 274 * s, y - 150 * s, "#6a5a30")
    c.poly([(x + 200 * s, y - 280 * s), (x + 230 * s, y - 330 * s), (x + 306 * s, y - 330 * s), (x + 336 * s, y - 280 * s)], "#1c5a34")
    return [(x + 268 * s, y - 250 * s, (1.0, 0.8, 0.5), 170 * s, True)]


@prop
def calendar(c, L, x, y, s=1.0, text="1987", **k):
    return ("sign", text, x, y, 300 * s, 180 * s, (226, 220, 200), (150, 24, 20))


# ------------------------------------------------------------------------------------------- the scene

def _sign(img, text, cx, cy, w, h, bg=(226, 214, 186), fg=(30, 22, 16)):
    w, h = int(max(40, w)), int(max(20, h))
    im = Image.new("RGBA", (w, h), bg + (255,))
    d = ImageDraw.Draw(im)
    d.rectangle((2, 2, w - 3, h - 3), outline=tuple(int(v * 0.5) for v in fg) + (255,), width=2)
    lines = str(text).split("|")
    size = int(h / (len(lines) * 1.5))
    f = K.C.font("oldst_b", max(10, size))
    while max(f.getlength(t) for t in lines) > w - 16 and f.size > 10:
        f = K.C.font("oldst_b", int(f.size) - 1)
    th = f.size * 1.2 * len(lines)
    for i, t in enumerate(lines):
        d.text(((w - f.getlength(t)) / 2, (h - th) / 2 + i * f.size * 1.2), t, font=f, fill=fg + (255,))
    comp(img, layer_from_pil(im, int(cx - w / 2), int(cy - h / 2)), 0.85)


class Tableau(Shot):
    """A picture built from props (see the top of this file)."""
    focus = (540, 980)
    fog_d = 0.08

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        skyn = p.get("sky", "blue")
        g = dict(p.get("ground") or {"type": "land", "y": 1180})
        lift = float(p.get("lift", 130))          # everything sits this much higher, clear of the captions
        gy = float(g.get("y", 1180)) - lift
        if "ghost_y" in self.p:
            self.p["ghost_y"] = float(self.p["ghost_y"]) - lift
        else:
            self.p["ghost_y"] = gy + 70
        if skyn == "room":
            img = np.zeros((H, W, 3), np.float32)
            wall = np.array(K.C.hex_rgb(p.get("wall", "#150d0a")) if hasattr(K.C, "hex_rgb") else
                            [int(p.get("wall", "#150d0a")[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
            img[:] = wall
        else:
            moon = p.get("moon")
            night = skyn in ("night", "blue")
            img = mk_sky(SKIES[skyn], 900 + self.seed, moon=tuple(moon) if moon else None,
                         stars=(380 if night else 0), clouds=0.6 if skyn == "storm" else 0.35)
        c, L = cv(), cv()
        gt = g.get("type", "land")
        if skyn == "room":
            for j in range(8):
                c.rect(j * 140 - 10, gy - 420, j * 140 + 110, gy - 30, "#000000", 0.14)
            c.rect(0, gy - 446, W, gy - 432, "#000000", 0.3)
            c.poly([(0, gy), (W, gy), (W, H), (0, H)], g.get("color", GROUND["floor"]))
            for j in range(9):
                c.line([(540 + (j - 4) * 130, gy), (540 + (j - 4) * 330, H)], "#000000", 2, 0.35)
        else:
            col = g.get("color") or (GROUND["water"][skyn] if gt == "water" else GROUND[gt])
            c.poly([(-20, gy), (W + 20, gy), (W + 20, H), (-20, H)], col)
            if gt == "water":
                for j in range(40):
                    yy = gy + 6 + j * 9
                    xa = hash2(j, 1, self.seed) * 900
                    c.line([(xa, yy), (xa + 80 + hash2(j, 2, self.seed) * 260, yy)], "#8aa0b0", 1.6, 0.14)
            elif gt == "street":
                c.rect(-20, gy, W + 20, gy + 22, "#34342f")
            elif gt == "snow":
                c.line([(-20, gy), (W + 20, gy)], "#a8b8c4", 3, 0.5)
        self.spots = []
        signs = []
        for pr in p.get("props", []):
            pr = dict(pr)
            f = PROPS[pr.pop("p")]
            x, s = float(pr.pop("x", 540)), float(pr.pop("s", 1.0))
            y = float(pr.pop("y")) - lift if "y" in pr else gy
            res = f(c, L, x, y, s, **pr)
            for it in ([res] if isinstance(res, tuple) else (res or [])):
                if it and it[0] == "sign":
                    signs.append(it[1:])
                elif it:
                    it = tuple(it)
                    col = it[2] if len(it) > 2 else (1.0, 0.9, 0.6)
                    self.spots.append((it[0], it[1], col, it[3] if len(it) > 3 else 40 * s, bool(it[4]) if len(it) > 4 else False))
        if gt != "water" and skyn != "room" and p.get("grass", True) and gt in ("land",):
            art.grass(c, gy + 60, 0, W, "#040605", n=320, hmin=12, hmax=56, seed=51 + self.seed)
        comp(img, c.rgba())
        for sg in signs:
            _sign(img, *sg)
        for gl in p.get("glows", []):
            self.spots.append((gl["x"], gl["y"] - lift, tuple(gl.get("color", (1.0, 0.8, 0.5))), gl.get("r", 80),
                               bool(gl.get("flick"))) + ((gl.get("k", 0.5),)))
        self.img = img
        self.lights = L.rgba()[..., :3]

    def animate(self, out, t, u):
        for i, sp in enumerate(self.spots):
            x, y, col, r, fl = sp[:5]
            k = sp[5] if len(sp) > 5 else 0.5
            f = flick(t, i * 3 + 1) if fl else 1.0
            add_spot(out, x, y, r, col, k * f)
            if r > 20:
                add_spot(out, x, y, max(4, r * 0.12), (1.0, 0.95, 0.8), 1.2 * f)


AMB = {"tab_lake": ("waves", None), "tab_land": ("wind", "owl"), "tab_town": ("wind", None),
       "tab_room": ("room", "creak"), "tab_rail": ("rumble", "whistle")}
for _k, _v in AMB.items():
    K.KINDS[_k] = Tableau
    K.AMBIENCE[_k] = _v


if __name__ == "__main__" and sys.argv[1:] == ["sheet"]:
    names = sorted(PROPS)
    cols = 8
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 270, rows * 300), (20, 24, 28))
    for i, n in enumerate(names):
        interior = n in ("window", "door", "seance", "parlor", "smoke", "stairs", "bunk", "shelves", "slime", "examroom",
                         "cases", "studio", "telegraph", "calendar")
        sc = {"kind": "tab_land", "sky": "room" if interior else "dusk", "fog": 0, "move": "still",
              "ground": {"type": "floor" if interior else "land", "y": 1300},
              "props": [{"p": n, "x": 540, "y": 1300, "s": 0.8}]}
        try:
            fr = Tableau(sc).render(1.0, 1.0)
            im = Image.fromarray((np.clip(fr, 0, 1) * 255).astype(np.uint8)).crop((0, 400, 1080, 1600)).resize((270, 300))
            ImageDraw.Draw(im).text((6, 4), n, fill=(255, 220, 120))
        except Exception as e:                      # show which prop failed on the sheet
            im = Image.new("RGB", (270, 300), (90, 0, 0))
            ImageDraw.Draw(im).text((6, 4), n + ": " + repr(e)[:200], fill=(255, 255, 255))
            print("FAILED", n, repr(e))
        sheet.paste(im, ((i % cols) * 270, (i // cols) * 300))
    sheet.save(K.C.ROOT + "/shorts/out/_props.jpg" if hasattr(K.C, "ROOT") else "_props.jpg", quality=88)
    print("sheet done", len(names))


def band(c, L, x, y, s=1.0, color="#3a372e", **k):
    """A foreground strip of ground from y down (a beach in front of the water, a lawn in front of a street)."""
    c.poly([(-20, y), (W + 20, y - 14), (W + 20, H), (-20, H)], color)


PROPS["band"] = band
