"""Canton, Georgia (Oct. 26, 2026, Scoop's request): Riverview Cemetery's baby Marie, and the Chastain House up in
Fannin County.

    python3 reel_canton.py stills|video [times]

Sources:
- Riverview Cemetery, Canton (begun in 1844 on land Judge Joseph Donaldson gave). Ghost-tour guide Wilkie (author of
  "The Haunting History of Canton"): "A little baby on the tour pointed and said 'baby.' The baby was talking to the
  baby that was not visible." Asked the other baby's name, "he said, 'Marie.'" A baby named Marie, who died in 1891, is
  buried in the Brady plot; her grave "is the reported site of a paranormal experience." Rebecca Johnston, "Cemeteries
  offer haunting experience," Cherokee Tribune, Oct. 29, 2016.
- The Chastain House, Fannin County: stop 3 of the Fannin County Chamber of Commerce's Historic Heritage Trail (Lower
  Loop). Jason Coward and Mary Ann (Polly) Rogers Chastain built the "Big House" in 1850-55; their daughter Alice died
  of diphtheria at 10; in bad weather, neighbors used a downstairs room as a viewing room for their dead; "reportedly
  haunted." What visitors say (children laughing, small footsteps): a 2011 visitor's blog post ("Paranormal Activity:
  The Chastain House") and Georgia Cabins For You's Blue Ridge ghost-tour page (footsteps, laughter).
Scoop asked for "the champlain house in fennin county": the haunted house the Chamber lists there is the Chastain House.
Everything is drawn. No bodies are shown.
"""
import math
import os
import sys

import cv2
import numpy as np
import skia
from PIL import Image, ImageDraw

import reels_common as C
from reels_common import bs, vr, W, H, SR, T, fitT, glow, paste, scaled, appear, ease_out, dim, BONE
from core import fbm, add_spot, Canvas, poly_path, light_map, Fog
import art
from reel_frank import to_pil, zoom, Rain, flick
from reel_belle import typed, red_title
from reel_haunts import cv, night_sky, land, comp, sprite, put, finish, lab, ttl, scene, haunt_music, whispers, \
    GHOSTC, LANT

C.WEIGHT.update({"1891": 5.35, "1850s": 5.0})
NAME = "canton"
OUTFILE = "canton-georgia-baby-marie-and-the-chastain-house.mp4"
TITLE = "Canton, Georgia: Baby Marie and the Chastain House"
PALE = (190, 230, 255)


# --------------------------------------------------------------------------------------------- props

def lamb_stone(c, x, y, s=1.0, dark="#0b1113", rim="#86aaa2"):
    """A small infant's headstone with a lamb resting on top; (x, y) = the base's centre."""
    w, h = 130 * s, 120 * s
    art.rim_shape(c, poly_path([(x - w / 2, y), (x - w / 2, y - h), (x + w / 2, y - h), (x + w / 2, y)]), dark, rim,
                  (3, 3))
    top = y - h
    body = poly_path([(x - w * 0.42, top), (x - w * 0.46, top - 22 * s), (x - w * 0.3, top - 44 * s),
                      (x + w * 0.18, top - 46 * s), (x + w * 0.36, top - 30 * s), (x + w * 0.38, top)])
    art.rim_shape(c, body, dark, rim, (2, 2))
    head = skia.Path()
    head.addOval(skia.Rect(x - w * 0.56, top - 74 * s, x - w * 0.22, top - 36 * s))
    art.rim_shape(c, head, dark, rim, (2, 2))
    c.ellipse(x - w * 0.5, top - 64 * s, 12 * s, 6 * s, dark)                   # an ear


def obelisk(c, x, y, h, dark="#090e10", rim="#6f948c"):
    """A family monument: stepped base, tall shaft and pyramid cap; (x, y) = base centre."""
    b = h * 0.16
    art.rim_shape(c, poly_path([(x - b * 1.3, y), (x - b * 1.3, y - b * 0.5), (x + b * 1.3, y - b * 0.5),
                                (x + b * 1.3, y)]), dark, rim, (3, 3))
    art.rim_shape(c, poly_path([(x - b, y - b * 0.5), (x - b, y - b * 1.2), (x + b, y - b * 1.2), (x + b, y - b * 0.5)]),
                  dark, rim, (3, 3))
    art.rim_shape(c, poly_path([(x - b * 0.62, y - b * 1.2), (x - b * 0.42, y - h * 0.92), (x, y - h),
                                (x + b * 0.42, y - h * 0.92), (x + b * 0.62, y - b * 1.2)]), dark, rim, (3, 3))


def coping(c, x0, y0, x1, y1, depth, color="#111819", top="#26363a"):
    """The low granite curb around a family plot, seen in perspective: front edge y1, back edge y0."""
    inset = (x1 - x0) * 0.16
    w = 16
    c.poly([(x0, y1), (x1, y1), (x1 - inset, y0), (x0 + inset, y0)], "#080c0d")         # the plot's ground
    c.poly([(x0 + inset - w * 0.4, y0 - w * 0.3), (x1 - inset + w * 0.4, y0 - w * 0.3), (x1 - inset + w * 0.4, y0 + w * 0.4),
            (x0 + inset - w * 0.4, y0 + w * 0.4)], top)                                  # back curb
    c.poly([(x0 - w, y1), (x0 + inset - w * 0.4, y0 - w * 0.3), (x0 + inset + w * 0.4, y0 - w * 0.3), (x0 + w, y1)], top)
    c.poly([(x1 + w, y1), (x1 - inset + w * 0.4, y0 - w * 0.3), (x1 - inset - w * 0.4, y0 - w * 0.3), (x1 - w, y1)], top)
    c.poly([(x0 - w, y1 - w * 0.6), (x1 + w, y1 - w * 0.6), (x1 + w, y1 + depth), (x0 - w, y1 + depth)], color)
    c.poly([(x0 - w, y1 - w * 0.6), (x1 + w, y1 - w * 0.6), (x1 + w, y1), (x0 - w, y1)], top)
    c.line([(x0 - w, y1 - w * 0.6), (x1 + w, y1 - w * 0.6)], "#5d7f7a", 2.5, 0.6)


def double_porch_house(c, lights, x, y, s=1.0, lit=(), body="#233033", trim="#3c4c4e", dark="#070a0b",
                       rim="#6a8a88", glass="#0b1214", window="#ffb45c"):
    """A two-storey 1850s north-Georgia farmhouse: side-gabled roof, brick chimney at each end and a two-level front
    porch across the middle. (x, y) = bottom-left corner. Returns the upper porch's floor line (x0, x1, y)."""
    Wd, Hh, roof_h = 640 * s, 330 * s, 96 * s
    for cx in (x + 34 * s, x + Wd - 34 * s):                                            # end chimneys
        c.rect(cx - 24 * s, y - Hh - roof_h - 64 * s, cx + 24 * s, y - Hh + 6 * s, "#0b0d0e")
        c.rect(cx - 30 * s, y - Hh - roof_h - 70 * s, cx + 30 * s, y - Hh - roof_h - 58 * s, "#0b0d0e")
        c.line([(cx - 24 * s, y - Hh - roof_h - 64 * s), (cx - 24 * s, y - Hh)], rim, 2, 0.35)
    art.rim_shape(c, poly_path([(x - 18 * s, y - Hh), (x + Wd + 18 * s, y - Hh), (x + Wd - 12 * s, y - Hh - roof_h),
                                (x + 12 * s, y - Hh - roof_h)]), dark, rim, (3, 3))
    c.rect(x, y - Hh, x + Wd, y, body)
    for k in range(1, 26):                                                              # clapboards
        yy = y - Hh + k * Hh / 26
        c.line([(x, yy), (x + Wd, yy)], "#141c1e", 1.6, 0.55)
    c.line([(x + 2 * s, y - Hh), (x + 2 * s, y)], rim, 3, 0.5)                          # moonlit corner board
    c.rect(x - 8 * s, y - 6 * s, x + Wd + 8 * s, y + 18 * s, "#0d1112")                 # stone foundation
    ww, wh = 54 * s, 92 * s
    p0, p1 = x + Wd * 0.3, x + Wd * 0.7                                                 # the porch's ends
    floors = (y - Hh * 0.5, y)
    wins = []
    for fy in floors:
        top = fy - Hh * 0.5 + 40 * s
        for wx in (x + Wd * 0.09, x + Wd * 0.2, x + Wd * 0.75, x + Wd * 0.86):
            wins.append((wx, top))
    for i, (wx, wy) in enumerate(wins):
        on = lit[i] if i < len(lit) else 0
        c.rect(wx - 5 * s, wy - 5 * s, wx + ww + 5 * s, wy + wh + 5 * s, trim)
        c.rect(wx, wy, wx + ww, wy + wh, glass)
        if on:
            lights.rect(wx, wy, wx + ww, wy + wh, window, 0.9 * on)
            lights.glow(wx + ww / 2, wy + wh / 2, 130 * s, window, 0.3 * on)
            lights.rect(wx + ww / 2 - 2 * s, wy, wx + ww / 2 + 2 * s, wy + wh, "#000000", 1.0)
            lights.rect(wx, wy + wh * 0.48, wx + ww, wy + wh * 0.48 + 4 * s, "#000000", 1.0)
        else:
            c.line([(wx + ww / 2, wy), (wx + ww / 2, wy + wh)], trim, 3 * s, 0.8)
            c.line([(wx, wy + wh * 0.5), (wx + ww, wy + wh * 0.5)], trim, 3 * s, 0.8)
    # doors, one on each floor, behind the porch
    for fy in floors:
        c.rect(x + Wd * 0.5 - 34 * s, fy - 118 * s, x + Wd * 0.5 + 34 * s, fy, "#0a0e0f")
        c.rect(x + Wd * 0.5 - 40 * s, fy - 124 * s, x + Wd * 0.5 + 40 * s, fy - 118 * s, trim)
    # the two-level porch
    c.rect(p0 - 10 * s, y - Hh - 4 * s, p1 + 10 * s, y - Hh + 14 * s, "#10171a")       # porch roof edge
    c.rect(p0, floors[0] - 4 * s, p1, floors[0] + 14 * s, "#10171a")                    # upper floor / lower ceiling
    for fy, ftop in ((floors[1], floors[0] + 14 * s), (floors[0], y - Hh + 14 * s)):
        for px in np.linspace(p0, p1 - 12 * s, 5):
            c.rect(px, ftop, px + 12 * s, fy, trim)
            c.line([(px + 1, ftop), (px + 1, fy)], rim, 2, 0.4)
    rail_y = floors[0] - 46 * s                                                          # upper railing
    c.line([(p0, rail_y), (p1, rail_y)], trim, 5 * s)
    for bx in np.arange(p0 + 10 * s, p1, 16 * s):
        c.line([(bx, rail_y), (bx, floors[0] - 4 * s)], trim, 2.5 * s, 0.85)
    for k in range(4):                                                                   # front steps
        c.rect(x + Wd * 0.5 - (80 - k * 10) * s, y + 18 * s + k * 14 * s, x + Wd * 0.5 + (80 - k * 10) * s,
               y + 30 * s + k * 14 * s, "#0e1314")
    return p0, p1, floors[0]


def boxwood(c, x, y, r, seed=0, color="#050808", rim="#2c4442"):
    rr = np.random.default_rng(seed)
    for k in range(7):
        a = rr.uniform(0, math.pi)
        c.circle(x + math.cos(a) * r * 0.6, y - r * 0.5 - math.sin(a) * r * 0.35, r * rr.uniform(0.45, 0.65), color)
    c.ellipse(x, y - r * 0.4, r * 1.05, r * 0.55, color)


def mountains(img, seed, base=1030):
    """Layered Blue Ridge ridges fading into fog, farthest first."""
    for k, (b, amp, sc, col, fa) in enumerate(((base - 300, 120, 520, "#13252b", 0.35), (base - 210, 110, 420, "#0f1e23", 0.3),
                                               (base - 120, 90, 360, "#0b171b", 0.28), (base - 30, 60, 300, "#081114", 0.25))):
        art.hills(img, b, amp, sc, col, seed + k * 7, rim="#3e5c5a", rim_w=2.5, rim_a=0.25)
        art.fog_band(img, b + 18, 60, "#5f8584", fa, seed=seed + k * 7 + 1)


# --------------------------------------------------------------------------------------------- scenes

class Riverview:
    """Riverview Cemetery at night: two big oaks, rows of old stones and obelisks, a gravel lane, and a tour guide's
    flashlight with a toddler pointing at the graves."""

    def __init__(self, seed=0, group=True):
        img = night_sky(301 + seed, moon=(830, 370, 50), clouds=0.36)
        land(img, 1090, 310 + seed, far="#0b1418")
        c = cv()
        art.tree(c, 110, 1130, 1000, seed=311 + seed, depth=8, spread=0.8, lean=0.06)
        art.tree(c, 990, 1120, 920, seed=312 + seed, depth=8, spread=0.74, lean=-0.08)
        art.gravestones(c, 1098, 60, 1030, 22, seed=313 + seed, hmin=24, hmax=60,
                        kinds=("round", "slab", "obelisk", "round"))
        art.gravestones(c, 1176, -20, 1100, 13, seed=314 + seed, hmin=64, hmax=140,
                        kinds=("round", "slab", "obelisk", "cross", "round"))
        c.poly([(-20, 1240), (W + 20, 1232), (W + 20, H), (-20, H)], "#06090a")
        c.poly([(500, 1110), (600, 1110), (960, H), (120, H)], "#10171a", 0.85)          # the gravel lane
        self.group = group
        if group:
            adult = art.figure(c, 380, 1215, 400, color="#010203", coat=True, arms=((8, 4), (58, 16)), legs=(5, -4))
            self.torch = adult["hands"][1]
            kid = art.figure(c, 470, 1215, 205, color="#010203", child=True, arms=((10, 6), (118, -8)), legs=(5, -4))
            self.kid_hand = kid["hands"][1]
        art.grass(c, 1640, 0, W, "#030506", n=440, hmin=14, hmax=60, seed=33 + seed)
        if group:
            yy = np.arange(H, dtype=np.float32)[:, None]
            xx = np.arange(W, dtype=np.float32)[None, :]
            halo = np.exp(-(((xx - 430) / 260.0) ** 2 + ((yy - 1080) / 120.0) ** 2))
            img += halo[..., None] * np.array([0.05, 0.075, 0.08], np.float32)
        comp(img, c.rgba())
        self.img = img
        if group:
            tx, ty = self.torch
            beam = Canvas(W, H)
            beam.poly([(tx + 8, ty - 5), (tx + 8, ty + 5), (900, 1150), (760, 1040)], "#ffffff", 1.0, blur=22)
            self.beam = beam.rgba()[..., 3] * 0.2
            self.pool = light_map(H, W, 830, 1110, 200, power=1.6)
        self.fog = Fog(seed=301 + seed, scale=300, color="#86aaa4", density=0.22, top=0.5, bottom=0.85, speed=18, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        if self.group:
            fl = 0.92 + 0.08 * flick(t, 2)
            warm = np.array([1.0, 0.92, 0.78], np.float32)
            out += self.beam[..., None] * warm * fl
            out += self.pool[..., None] * warm * 0.2 * fl
            add_spot(out, self.torch[0] + 8, self.torch[1], 16, (1.0, 0.95, 0.85), 0.9)
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.06, 6.0, 560, 1050)


class FamilyPlot:
    """The Brady plot: a granite curb, the family's obelisk, two headstones and a baby's small stone with a lamb on
    top. A faint light hangs over the small stone. The camera moves in on it."""

    def __init__(self, dur=9.0):
        self.dur = dur
        img = night_sky(331, moon=(860, 360, 46), clouds=0.42)
        land(img, 800, 333, far="#0b1418")
        c = cv()
        art.tree(c, 60, 860, 820, seed=341, depth=8, spread=0.72, lean=0.1)
        art.gravestones(c, 804, 300, 1060, 12, seed=342, hmin=22, hmax=50, kinds=("round", "slab", "obelisk"))
        c.poly([(-20, 830), (W + 20, 822), (W + 20, H), (-20, H)], "#070b0c")
        coping(c, 130, 900, 950, 1130, 34)
        obelisk(c, 450, 1000, 520)
        art.gravestones(c, 1030, 230, 231, 1, seed=343, hmin=190, hmax=191, tilt=0.0, dark="#0a1012", rim="#7a9e96",
                        kinds=("round",))
        art.gravestones(c, 1020, 620, 621, 1, seed=344, hmin=170, hmax=171, tilt=0.0, dark="#0a1012", rim="#7a9e96",
                        kinds=("slab",))
        lamb_stone(c, 800, 1112, s=1.35)
        art.grass(c, 1190, 0, W, "#030506", n=460, hmin=14, hmax=60, seed=44)
        comp(img, c.rgba())
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        img += np.exp(-((yy - 1040) / 160.0) ** 2) * np.array([0.03, 0.045, 0.05], np.float32)
        self.img = img
        self.fog = Fog(seed=331, scale=280, color="#86aaa4", density=0.26, top=0.5, bottom=0.85, speed=14, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        self.fog.apply(out, t)
        k = min(1.0, u / 1.2)
        bob = 10 * math.sin(t * 1.3)
        glow_a = (0.55 + 0.25 * math.sin(t * 2.1)) * k
        add_spot(out, 800, 860 + bob, 60, GHOSTC, 0.10 * glow_a)
        add_spot(out, 800, 860 + bob, 9, GHOSTC, 0.8 * glow_a)
        add_spot(out, 800, 860 + bob, 3.5, (1, 1, 1), 0.6 * glow_a)
        add_spot(out, 800, 1000, 80, GHOSTC, 0.05 * glow_a)                              # its glow on the stone
        p = ease_out(min(1.0, u / self.dur))
        return zoom(out, 1.0 + 0.24 * p, 540 + 200 * p, 980)


class ChastainHouse:
    """The Chastain House at night below layered mountain ridges: boxwoods, a split-rail fence, old trees.
    kids=True puts two faint small figures on the upper porch."""

    def __init__(self, seed=0, lit=True, kids=False, close=False):
        img = night_sky(361 + seed, moon=(250, 360, 54), clouds=0.3)
        mountains(img, 371 + seed, base=1000)
        c = cv()
        lights = cv()
        art.tree(c, 1010, 1180, 900, seed=381 + seed, depth=8, spread=0.7, lean=-0.1)
        art.tree(c, 40, 1170, 760, seed=382 + seed, depth=8, spread=0.62, lean=0.1)
        c.poly([(-20, 1100), (W + 20, 1090), (W + 20, H), (-20, H)], "#060a0b")
        self.porch = double_porch_house(c, lights, 220, 1150, s=1.0, lit=(0, 0, 0, 0, 0, 0, 0, 1) if lit else ())
        for k, (bx, br) in enumerate(((170, 70), (900, 64), (100, 52), (970, 50))):
            boxwood(c, bx, 1200, br, seed=390 + k)
        art.fence(c, 1300, -20, 1100, spacing=60, h=60, seed=12, broken=0.25)
        art.grass(c, 1420, 0, W, "#030506", n=460, hmin=14, hmax=70, seed=46 + seed)
        comp(img, c.rgba())
        self.lights = lights.rgba()[..., :3]
        self.img = img
        self.kids = kids
        self.close = close
        if kids:
            self.kid = [sprite(lambda k, d=d: art.figure(k, 60, 196, 150, color="#ffffff", child=True, dress=d,
                                                      arms=((10, 4), (-6, -2)), legs=(3, -3)), 120, 200, blur=3.5)
                        for d in (True, False)]
        self.fog = Fog(seed=361 + seed, scale=320, color="#7fa39e", density=0.2, top=0.45, bottom=0.75, speed=16, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        out += self.lights * (0.8 + 0.2 * flick(t, 6))
        if self.kids:
            p0, p1, fy = self.porch
            for i, m in enumerate(self.kid):
                a = (0.3 + 0.18 * math.sin(t * 1.7 + i * 2.1)) * min(1.0, u / 1.0)
                a *= 0.6 + 0.4 * max(0.0, math.sin(t * 0.9 + i)) ** 2
                x = p0 + 80 + i * 150 + 18 * math.sin(t * 0.6 + i)
                put(out, m, x, fy - 2, (0.62, 0.78, 0.86), a)
        self.fog.apply(out, t)
        if self.close:
            return finish(out, t, u, 1.18, 1.3, 5.0, 540, 940)
        return finish(out, t, u, 1.0, 1.07, 6.0, 540, 1000)


class ViewingRoom:
    """Downstairs on a stormy night: plank walls, rain on the window, a candle on a small table and a row of empty
    chairs along the wall. No one is shown."""

    def __init__(self):
        img = np.zeros((H, W, 3), np.float32)
        yy = np.arange(H, dtype=np.float32)[:, None]
        xx = np.arange(W, dtype=np.float32)[None, :]
        boards = (np.abs(((xx + 20) % 110) - 55) > 52).astype(np.float32)
        grain = cv2.resize(fbm(H // 6, W // 2, scale=8, octaves=4, seed=401), (W, H), interpolation=cv2.INTER_CUBIC)
        wall = (0.07 + 0.05 * grain) * (1 - 0.6 * boards)
        img += (wall * (yy < 1170))[..., None] * np.array([0.85, 0.72, 0.58], np.float32)
        floor = cv2.resize(fbm(H // 4, W // 4, scale=14, octaves=5, seed=402), (W, H), interpolation=cv2.INTER_CUBIC)
        img += ((0.04 + 0.03 * floor) * (yy >= 1170))[..., None] * np.array([0.8, 0.66, 0.52], np.float32)
        self.win = (600, 470, 920, 930)                                                   # the window
        x0, y0, x1, y1 = self.win
        img[y0:y1, x0:x1] = np.array([0.03, 0.05, 0.065], np.float32)
        c = cv()
        c.rect(0, 1164, W, 1178, "#0a0604", 0.9, blur=3)
        c.rect(x0 - 18, y0 - 18, x1 + 18, y0, "#24170e")
        c.rect(x0 - 18, y1, x1 + 18, y1 + 26, "#24170e")
        c.rect(x0 - 18, y0, x0, y1, "#24170e")
        c.rect(x1, y0, x1 + 18, y1, "#24170e")
        c.rect((x0 + x1) / 2 - 6, y0, (x0 + x1) / 2 + 6, y1, "#1c120a")
        c.rect(x0, (y0 + y1) / 2 - 6, x1, (y0 + y1) / 2 + 6, "#1c120a")
        for k, cx in enumerate((120, 280, 980)):                                         # empty chairs on the wall
            wood = "#4a301c"
            c.rect(cx - 50, 1000, cx + 50, 1014, wood)
            c.rect(cx - 50, 800, cx - 40, 1150, wood)
            c.rect(cx + 40, 800, cx + 50, 1150, wood)
            for yb in (840, 890, 940):
                c.rect(cx - 44, yb, cx + 44, yb + 9, wood)
            c.rect(cx + 32, 1014, cx + 42, 1150, "#2a1a0e")
        c.rect(330, 1060, 560, 1076, "#5a3a22")                                           # the little table
        c.rect(350, 1076, 362, 1180, "#3a2516")
        c.rect(528, 1076, 540, 1180, "#3a2516")
        self.wick = art.candle(c, 445, 1060, 70, 22)
        comp(img, c.rgba())
        self.img = img
        self.rain = Rain(170, (x0, y0, x1, y1), seed=5, speed=1500, length=40, slant=0.12, a=(0.15, 0.4))
        self.mask = np.zeros((H, W), np.float32)
        self.mask[y0:y1, x0:x1] = 1.0
        self.light = light_map(H, W, 445, 1000, 1000, power=1.05)
        self.fog = Fog(seed=403, scale=260, color="#5a4a3a", density=0.1, top=0.0, bottom=0.8, speed=8, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        fl = flick(t, 7)
        out *= (0.5 + 1.9 * self.light[..., None] * fl)
        out += self.light[..., None] * np.array(LANT, np.float32) * 0.2 * fl
        self.rain.draw(out, t, k=1.0, color=(0.55, 0.65, 0.75), mask=self.mask)
        wx, wy = self.wick
        art.candle_flame(out, wx, wy, 11, t, seed=4, k=1.0)
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.06, 6.0, 540, 950)


def bubble(text):
    """A comment box with a blinking cursor, like the documentary's closing card."""
    f = C.font("semi", 44)
    w = int(f.getlength(text)) + 90
    img = Image.new("RGBA", (w + 40, 130), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 10, 20 + w, 100), radius=26, fill=(242, 240, 234, 240))
    d.polygon([(60, 98), (92, 98), (56, 124)], fill=(242, 240, 234, 240))
    d.text((52, 30), text, font=f, fill=(70, 70, 76, 255))
    return img, 52 + f.getlength(text) + 6


# --------------------------------------------------------------------------------------------- the reel

def build(R):
    t_canton = R.at("Canton, Georgia,")
    t_baby = R.at("baby.")
    t_no = R.at("There was")
    t_asked = R.at("When they")
    t_marie = R.at("Marie.")
    t_buried = R.at("The baby buried")
    t_1891 = R.at("1891.")
    t_hour = R.at("An hour")
    t_fannin = R.at("Fannin County,")
    t_house = R.at("the Chastain House")
    t_1850 = R.at("1850s.")
    t_alice = R.at("Alice")
    t_ten = R.at("ten.")
    t_bad = R.at("In bad")
    t_room = R.at("a room")
    t_vis = R.at("Visitors say")
    t_kids = R.at("children laughing,")
    t_little = R.at("little footsteps.")
    t_comment = R.at("Comment your")
    c1 = (R.end("baby.") + t_no) / 2
    c2 = (R.end("1891.") + t_hour) / 2
    c3 = (R.end("1850s.") + R.at("The Chastains")) / 2
    c4 = (R.end("downstairs.") + t_vis) / 2
    c5 = t_comment - 0.15

    def d_open(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("CANTON, GEORGIA")
        paste(f, ctx["l"], W / 2, 300)
        red_title(f, "RIVERVIEW CEMETERY", 100, t, -0.2)
        typed(f, "\"BABY.\"", t, t_baby - 0.1, 440, size=120, rate=0.07)
        bs.credit_line(f, "A ghost-tour guide's story, in the Cherokee Tribune (2016)")

    def p_plot(ctx):
        ctx["s"] = FamilyPlot(dur=c2 - c1)
        ctx["l"] = lab("WHAT THE GUIDE SAYS")
        ctx["l2"] = lab("THE BABY BURIED HERE", 34, (200, 214, 206))

    def d_plot(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        paste(f, ctx["l"], W / 2, 300, appear(t, c1 + 0.05, 0.3) * (1 - appear(t, t_buried - 0.3, 0.3)))
        typed(f, "\"MARIE.\"", t, t_marie - 0.1, 440, size=120, rate=0.07)
        paste(f, ctx["l2"], W / 2, 300, appear(t, t_buried - 0.1, 0.3))
        typed(f, "MARIE · 1891", t, t_1891 - 0.25, 580, size=80, rate=0.05)
        bs.credit_line(f, "Riverview Cemetery, Canton · Cherokee Tribune (2016)")

    def p_house(ctx):
        ctx["s"] = ChastainHouse(seed=0, lit=True)
        ctx["l"] = lab("AN HOUR NORTH · FANNIN COUNTY")
        ctx["n"] = ttl("THE CHASTAIN HOUSE", 88)

    def d_house(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        paste(f, ctx["l"], W / 2, 300, appear(t, c2 + 0.05, 0.3))
        a = appear(t, t_house - 0.1, 0.3)
        paste(f, ctx["n"], W / 2, 430 + 12 * (1 - a), a)
        typed(f, "SINCE THE 1850s", t, t_1850 - 0.5, 545, size=66, rate=0.04)
        bs.credit_line(f, "History: Fannin County Chamber of Commerce")

    def p_room(ctx):
        ctx["s"] = ViewingRoom()
        ctx["l"] = lab("THE CHASTAINS' DAUGHTER")
        ctx["l2"] = lab("IN BAD WEATHER", 34, (200, 214, 206))

    def d_room(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        paste(f, ctx["l"], W / 2, 300, appear(t, c3 + 0.05, 0.3) * (1 - appear(t, t_bad - 0.3, 0.3)))
        typed(f, "ALICE, AGE 10", t, t_alice - 0.1, 430, size=96, rate=0.05)
        paste(f, ctx["l2"], W / 2, 300, appear(t, t_bad - 0.1, 0.3))
        if t >= t_room - 0.3:
            red_title(f, "THE VIEWING ROOM", 100, t, t_room - 0.1)
        bs.credit_line(f, "History: Fannin County Chamber of Commerce")

    def p_kids(ctx):
        ctx["s"] = ChastainHouse(seed=1, lit=False, kids=True, close=True)
        ctx["l"] = lab("WHAT VISITORS SAY")

    def d_kids(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        paste(f, ctx["l"], W / 2, 300, appear(t, c4 + 0.05, 0.3))
        typed(f, "CHILDREN LAUGHING", t, t_kids - 0.1, 430, size=72, rate=0.04)
        typed(f, "LITTLE FOOTSTEPS", t, t_little - 0.1, 530, size=72, rate=0.04)
        bs.credit_line(f, "Visitors' accounts, 2011-2026")

    def p_end(ctx):
        ctx["s"] = ChastainHouse(seed=2, lit=True)
        ctx["q"] = glow(fitT("COMMENT YOUR TOWN", "bask", 104, BONE, max_w=C.CW, min_size=60), (0, 0, 0), radius=24,
                        strength=0.95)
        ctx["q2"] = glow(fitT("IT COULD BE NEXT", "bask", 120, (250, 70, 56), max_w=C.CW, min_size=60), (150, 0, 0),
                         radius=34, strength=0.7)
        ctx["b"], ctx["cur"] = bubble("Your town, your state")
        ctx["pill"] = vr.pill("The Chastain House: view it from the road", "xbold", 38, (10, 20, 18),
                              (170, 255, 214, 255), padx=26, pady=14)

    def d_end(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u + 6.0)))
        bs.shade(f)
        dim(f, 0.4 * appear(u, 0.0, 0.3))
        paste(f, ctx["q"], W / 2, 430, appear(u, 0.0, 0.25))
        paste(f, ctx["q2"], W / 2, 560, appear(u, 0.15, 0.25))
        b = ctx["b"]
        a = appear(u, 0.4, 0.3)
        paste(f, b, W / 2, 740 + 10 * (1 - a), a)
        if a > 0.9 and int(u * 2.2) % 2 == 0:
            x0 = W / 2 - b.width / 2 + ctx["cur"]
            dr = ImageDraw.Draw(f)
            dr.rectangle((x0, 740 - 30, x0 + 4, 740 + 16), fill=(70, 70, 76, 255))
        paste(f, ctx["pill"], W / 2, 900, appear(u, 0.6, 0.3))
        bs.credit_line(f, "Cherokee Tribune (2016) · Fannin County Chamber · All pictures drawn")

    scenes = [C.Scene(0.0, c1, d_open, scene(Riverview)), C.Scene(c1, c2, d_plot, p_plot),
              C.Scene(c2, c3, d_house, p_house), C.Scene(c3, c4, d_room, p_room),
              C.Scene(c4, c5, d_kids, p_kids), C.Scene(c5, R.dur + 1, d_end, p_end, flicker=0.0)]
    scenes[3].flicker = 0.4
    atm = bs.Atmos(tint=(196, 204, 206), fog=0.08, vignette=0.58, grain=12, seed=17)
    flashes = [(0.35, 0.3), (t_bad + 0.2, 0.25), (t_room + 0.9, 0.2)]
    film = C.Film(R, scenes, flashes=flashes, flicker=0.2, atmos=atm)

    import sfx as X
    import audio as AU
    n = int((R.dur + 0.5) * SR)
    wind = X.wind(R.dur + 0.5, seed=41, strength=0.75).mean(1)[:n]
    N = AU.N
    lull = X.music_box([(N["E5"], 1), (N["G5"], 1), (N["E5"], 1), (N["D5"], 1), (N["C5"], 2), (None, 1),
                        (N["E5"], 1), (N["D5"], 1), (N["C5"], 1), (N["A4"], 2)], start_gap=0.5, seed=27).mean(1)
    rain = X.rain(c4 - c3 + 0.6, seed=44).mean(1)
    kid_steps = small_steps(c5 - c4)
    ev = [(wind, 0.0, 0.5, "bed"), (X.thunder(5.0, seed=12).mean(1), 0.37, 0.55, "bed"), ("hit", 0.05, 0.6),
          (X.owl(seed=24).mean(1), 1.2, 0.3), ("type", t_baby - 0.1, 0.9), ("whoosh", c1, 0.5),
          (lull, c1 + 0.3, 0.42, "bed"), ("type", t_marie - 0.1, 0.9), ("type", t_1891 - 0.25, 0.8),
          ("whoosh", c2, 0.5), ("type", t_1850 - 0.5, 0.7), ("whoosh", c3, 0.5), (rain, c3, 0.55, "bed"),
          ("type", t_alice - 0.1, 0.8), (X.thunder(4.5, seed=13).mean(1), t_bad + 0.2, 0.6, "bed"),
          ("hit", t_room - 0.1, 0.7), (X.creak(1.8, seed=23).mean(1), t_room + 0.4, 0.4), ("whoosh", c4, 0.5),
          (kid_steps, c4 + 0.4, 0.45, "bed"), (whispers(c5 - c4, seed=12), c4 + 0.2, 0.3, "bed"),
          ("type", t_kids - 0.1, 0.7), ("type", t_little - 0.1, 0.7), ("whoosh", c5, 0.5),
          ("pop", c5 + 0.4, 0.6), ("pop", c5 + 0.75, 0.5)]
    return film, ev, haunt_music(R, seed=130, prog=6)


def small_steps(dur, seed=6):
    """Light, quick little footsteps across a wooden floor upstairs."""
    import sfx as X
    r = np.random.default_rng(seed)
    out = np.zeros(int(dur * SR), np.float32)
    t = 0.1
    while t < dur - 0.3:
        m = int(0.06 * SR)
        x = X.bp(r.normal(0, 1, m).astype(np.float32), 300, 2600) * np.exp(-np.linspace(0, 9, m))
        i = int(t * SR)
        out[i:i + m] += x[: len(out) - i] * r.uniform(0.5, 1.0)
        t += r.uniform(0.17, 0.26) if r.random() > 0.15 else r.uniform(0.6, 0.9)
    out = X.reverb(X.stereo(out / max(1e-6, np.abs(out).max()) * 0.6, 0.2), rt=1.2, wet=0.4).mean(1)
    return out.astype(np.float32)


def main(mode, times=None):
    R = C.Reel(NAME, tail=1.4)
    film, ev, music = build(R)
    if mode == "stills":
        ts = times or [round(R.dur * k / 12, 2) for k in range(12)]
        print(film.stills([t for t in ts if t < R.dur], NAME))
        return
    vid = os.path.join(C.OUT, "_%s_video.mp4" % NAME)
    film.video(vid, cover_t=0.8)
    mix = C.soundtrack(R, music, ev, music_gain=0.5)
    out = os.path.join(C.OUT, OUTFILE)
    C.finish(R, vid, mix, out, TITLE)
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    main(sys.argv[1], [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None)
