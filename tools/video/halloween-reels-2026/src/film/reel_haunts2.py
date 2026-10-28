"""More La Porte legends (Oct. 25, 2026): Pine Lake Cemetery, Orr Lake Road's doctor, and a countdown of four.

    python3 reel_haunts2.py pinelake|orr2|top4 stills|video [times]

Sources:
- Pine Lake Cemetery: first burial 1858; when the original city cemetery fell into disrepair in 1871 its burials were
  moved here, many reinterred as "unknown burials"; afterward came reports of "one woman found upside down and twisted
  in her coffin and believed to be buried alive"; "a smaller mass burial site for unknown victims" of Belle Gunness, the
  remains of "roughly 10 men" split between two caskets; "mist-like shadows" above the stones and orbs in photos.
  Ashley Hood, Haunted Cemeteries of Indiana (2020), via Jeff Mayes, La Porte County Herald-Dispatch, Oct. 22, 2020.
- Orr Lake Road's doctor: "sometime in the 1900s" a doctor, his wife and his daughter; after they died he allegedly kept
  their bodies in barrels; on a full moon he and a servant with a hook for a hand are said to go into the woods with a
  lantern. Patricia Harrison, "La Porte County's Top 10 Most Haunted," The News-Dispatch, Oct. 23, 2011.
- The countdown: those two, Patton Cemetery (a neighbor hears people talking at night and sees no one; the same 2011
  list) and Posey Chapel Cemetery (bells, bouncing lights, a woman in white; Hood and the hauntings page).
Everything is drawn. No bodies are shown.
"""
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

import reels_common as C
from reels_common import bs, vr, W, H, SR, T, fitT, glow, paste, scaled, appear, ease, ease_out, dim, BONE
from core import fbm, add_spot, Canvas, smooth_path, poly_path, paint, light_map, Fog, smoothstep, clamp01
import art
from reel_frank import to_pil, zoom, flick
from reel_belle import typed, red_title
from reel_haunts import (cv, night_sky, land, comp, layer_from_pil, sprite, put, Bouncers, grade, finish, road, lab,
                         ttl, scene, TownCemetery, Shadows, PoseyWide, PoseyWhite, Folklore, haunt_music, whispers,
                         steps, scrape, LANT, GHOSTC)

C.WEIGHT.update({"1871": 5.35, "1900s": 4.35, "1858": 5.35})
OUTFILES = {"pinelake": "pine-lake-cemetery-buried-alive.mp4", "orr2": "orr-lake-road-the-doctors-lantern.mp4",
            "top4": "la-porte-county-4-places-the-dead-dont-rest.mp4"}
TITLES = {"pinelake": "Pine Lake Cemetery", "orr2": "Orr Lake Road: The Doctor's Lantern",
          "top4": "4 Places in La Porte County Where the Dead Don't Rest"}
MINT = (170, 255, 214)


# --------------------------------------------------------------------------------------------- props

def pine(c, x, y, h, color="#040607", seed=0):
    """A ragged evergreen silhouette, (x, y) = base of the trunk."""
    r = np.random.default_rng(seed)
    c.rect(x - h * 0.02, y - h * 0.12, x + h * 0.02, y, color)
    tiers = 7
    for k in range(tiers):
        f = k / (tiers - 1)
        ty = y - h * (0.1 + 0.85 * f)
        wd = h * (0.34 * (1 - f) + 0.05)
        pts = [(x - wd, ty + h * 0.07)]
        for j in range(1, 6):
            xx = x - wd + 2 * wd * j / 6
            pts.append((xx, ty + h * 0.07 - r.uniform(0.0, 0.03) * h))
        pts += [(x + wd, ty + h * 0.07), (x + r.uniform(-0.01, 0.01) * h, ty - h * 0.12)]
        c.poly(pts, color)


def coffin_pts(cx, cy, L, Wd, ang):
    """A six-sided ("toe-pincher") coffin outline, seen from above, rotated by ang (radians)."""
    rel = [(-L / 2, -Wd * 0.30), (-L / 2 + 0.27 * L, -Wd / 2), (L / 2, -Wd * 0.24), (L / 2, Wd * 0.24),
           (-L / 2 + 0.27 * L, Wd / 2), (-L / 2, Wd * 0.30)]
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in rel]


def coffin(c, cx, cy, L, Wd, ang=0.0, depth=26, lid=None, wood="#2a1a10", edge="#a07a52", inside="#010101"):
    """Body (with a side face for depth) and an optional lid offset (dx, dy, dang) left ajar."""
    body = coffin_pts(cx, cy, L, Wd, ang)
    side = [(x, y + depth) for x, y in body]
    c.poly(side, "#120a06")
    c.poly(body, inside if lid is not None else wood)
    if lid is None:
        for k in range(1, 4):                                     # plank seams
            f = k / 4
            a = (body[0][0] * (1 - f) + body[5][0] * f, body[0][1] * (1 - f) + body[5][1] * f)
            b = (body[2][0] * (1 - f) + body[3][0] * f, body[2][1] * (1 - f) + body[3][1] * f)
            c.line([a, b], "#140c07", 2, 0.8)
        c.line(body + body[:1], edge, 3, 0.55)
        return
    c.line(body + body[:1], edge, 3, 0.45)
    dx, dy, dang = lid
    lp = coffin_pts(cx + dx, cy + dy, L * 1.02, Wd * 1.02, ang + dang)
    c.poly([(x, y + 10) for x, y in lp], "#0a0604", blur=6)           # the lid's shadow
    c.poly(lp, wood)
    for k in range(1, 4):
        f = k / 4
        a = (lp[0][0] * (1 - f) + lp[5][0] * f, lp[0][1] * (1 - f) + lp[5][1] * f)
        b = (lp[2][0] * (1 - f) + lp[3][0] * f, lp[2][1] * (1 - f) + lp[3][1] * f)
        c.line([a, b], "#140c07", 2, 0.8)
    c.line(lp + lp[:1], edge, 3, 0.6)


def lantern(c, x, y, s=1.0, color="#0a0b0c"):
    """A hand lantern hanging from (x, y): bail, cap, glass and base."""
    c.line([(x - 10 * s, y + 6 * s), (x, y - 8 * s), (x + 10 * s, y + 6 * s)], color, 2.5 * s)
    c.poly([(x - 14 * s, y + 8 * s), (x + 14 * s, y + 8 * s), (x + 10 * s, y + 2 * s), (x - 10 * s, y + 2 * s)], color)
    c.rect(x - 12 * s, y + 8 * s, x + 12 * s, y + 40 * s, "#ffcf7a", 0.95, r=6 * s)
    c.rect(x - 15 * s, y + 40 * s, x + 15 * s, y + 46 * s, color)
    return (x, y + 24 * s)


def barrel(c, x, y, h, color="#2a1a10", hoop="#0d0805", lit=0.0):
    """A wooden barrel standing on the floor at (x, y), lit a little from the left."""
    w = h * 0.62
    pts = [(x - w * 0.42, y), (x - w * 0.5, y - h * 0.5), (x - w * 0.42, y - h), (x + w * 0.42, y - h),
           (x + w * 0.5, y - h * 0.5), (x + w * 0.42, y)]
    c.poly(pts, color, smooth=True)
    for f in (0.12, 0.3, 0.7, 0.88):                                   # hoops, bowed with the bulge
        yy = y - h * f
        bulge = 1 - abs(f - 0.5) * 0.36
        c.line([(x - w * 0.5 * bulge, yy), (x, yy + h * 0.025), (x + w * 0.5 * bulge, yy)], hoop, h * 0.03)
    for k in range(-3, 4):                                             # staves
        xs = x + k * w * 0.13
        c.line([(xs * 0.98 + x * 0.02, y - h * 0.02), (xs * 1.04 - x * 0.04, y - h * 0.5),
                (xs * 0.98 + x * 0.02, y - h * 0.98)], "#140c07", 1.5, 0.7)
    c.ellipse(x, y - h, w * 0.42, h * 0.06, "#1d120b")
    if lit:
        c.poly([(x - w * 0.42, y), (x - w * 0.5, y - h * 0.5), (x - w * 0.42, y - h), (x - w * 0.25, y - h),
                (x - w * 0.32, y - h * 0.5), (x - w * 0.25, y)], "#8a5a30", 0.35 * lit, smooth=True)


def hook_arm(c, x, y, s=1.0, color="#030405"):
    """A curved hook where a hand would be, at (x, y)."""
    c.line([(x, y - 4 * s), (x, y + 16 * s)], color, 5 * s)
    pts = [(x + 12 * s * math.sin(a), y + 16 * s + 12 * s * (1 - math.cos(a))) for a in np.linspace(0, math.pi * 1.25, 12)]
    c.line([(x, y + 16 * s)] + pts, color, 4 * s)


def night_lake_sky(seed, moon, clouds=0.3, glow_k=0.6):
    return art.sky(W, H, stops=[(0.0, "#020507"), (0.3, "#07131a"), (0.5, "#11252c"), (0.58, "#1d363b"),
                                (1.0, "#22393d")], moon=moon, stars=480, clouds=clouds, seed=seed,
                   cloud_band=(0.0, 0.48), star_max_y=0.55, moon_glow=glow_k)


# --------------------------------------------------------------------------------------------- PINE LAKE CEMETERY

class Exhume:
    """1871: lantern light at an old graveyard, an open grave and a coffin hauled up onto the grass."""

    def __init__(self):
        img = night_sky(51, moon=(830, 350, 46), clouds=0.45)
        land(img, 960, 140, far="#0b161a")
        c = cv()
        art.tree(c, 100, 990, 880, seed=151, depth=8, spread=0.7, lean=0.1)
        art.tree(c, 1000, 980, 760, seed=152, depth=8, spread=0.62, lean=-0.12)
        art.gravestones(c, 978, 230, 900, 13, seed=153, hmin=26, hmax=72, tilt=0.25, rim="#5a7c76")
        c.poly([(-20, 1000), (W + 20, 990), (W + 20, H), (-20, H)], "#080c0d")
        c.poly([(390, 1118), (740, 1118), (782, 1196), (350, 1196)], "#000000")             # the open grave
        c.poly([(760, 1124), (880, 1074), (990, 1104), (1030, 1196), (770, 1200)], "#121614", smooth=True)
        coffin(c, 420, 1046, 400, 124, ang=-0.05, depth=34, wood="#3a2616", edge="#c09060")
        fig1 = art.figure(c, 870, 1124, 380, color="#030405", hat="brim", arms=((24, 40), (-28, -36)), legs=(8, -4))
        h1 = fig1["hands"]
        c.line([(h1[0][0] - 20, h1[0][1] - 40), (h1[1][0] + 60, h1[1][1] + 160)], "#030405", 7)      # shovel
        c.poly([(h1[1][0] + 48, h1[1][1] + 150), (h1[1][0] + 92, h1[1][1] + 168), (h1[1][0] + 80, h1[1][1] + 210),
                (h1[1][0] + 40, h1[1][1] + 196)], "#030405")
        fig2 = art.figure(c, 170, 1134, 360, color="#030405", hat="cap", arms=((12, 6), (-70, -40)), legs=(4, -6))
        hx, hy = fig2["hands"][1]
        self.lamp = lantern(c, hx, hy, s=1.2)
        art.grass(c, 1260, 0, W, "#030506", n=420, hmin=16, hmax=60, seed=21)
        comp(img, c.rgba())
        self.img = img
        lx, ly = self.lamp
        self.light = light_map(H, W, lx + 120, ly + 120, 1150, power=1.1)
        self.fog = Fog(seed=51, scale=300, color="#86aaa4", density=0.2, top=0.5, bottom=0.8, speed=18, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        fl = flick(t, 5)
        out += self.light[..., None] * np.array(LANT, np.float32) * 0.75 * fl
        lx, ly = self.lamp
        add_spot(out, lx, ly, 34, (1.0, 0.75, 0.4), 0.9 * fl)
        add_spot(out, lx, ly, 8, (1.0, 0.95, 0.8), 1.5)
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.06, 6.0, 520, 1050)


class LakeCemetery:
    """Pine Lake Cemetery at night: the lake beyond, pines, rows of small plain stones. mist=True adds the shadows."""

    def __init__(self, seed=0, mist=False, close=False):
        img = night_lake_sky(61 + seed, moon=(240, 360, 52), clouds=0.32)
        hz = 900
        yy = np.arange(H, dtype=np.float32)[:, None]
        xx = np.arange(W, dtype=np.float32)[None, :]
        art.hills(img, hz - 30, 22, 500, "#0a1519", 161 + seed, rim="#36514f", rim_w=3, rim_a=0.3)
        lake = ((yy >= hz) & (yy < hz + 70)).astype(np.float32) * np.ones((1, W), np.float32)
        ripple = cv2.resize(fbm(H // 8, W // 2, scale=6, octaves=3, seed=162), (W, H), interpolation=cv2.INTER_CUBIC)
        water = np.array([0.025, 0.045, 0.055], np.float32) * (0.7 + 0.6 * ripple[..., None])
        glint = np.exp(-((xx - 240) / np.maximum(4.0, 22 + (yy - hz) * 0.5)) ** 2) * (yy > hz) * (0.25 + 0.75 * ripple)
        water = water + (glint * 0.7)[..., None] * np.array([0.7, 0.85, 0.82], np.float32)
        img = img * (1 - lake[..., None]) + water * lake[..., None]
        c = cv()
        c.poly([(-20, hz + 56), (W + 20, hz + 52), (W + 20, H), (-20, H)], "#081012")
        for k, (px, ph) in enumerate(((60, 560), (180, 420), (905, 640), (1025, 500), (760, 330))):
            pine(c, px, hz + 74, ph, seed=170 + k)
        if close:
            art.gravestones(c, 1050, 40, 1040, 16, seed=171 + seed, hmin=56, hmax=110, tilt=0.12, rim="#7fa49c",
                            kinds=("round", "slab"))
            art.gravestones(c, 1270, -30, 1110, 5, seed=172 + seed, hmin=180, hmax=270, tilt=0.06, dark="#0a1012",
                            rim="#86aaa2", kinds=("round", "slab"))
        else:
            for row, (yb, hmin, hmax, n) in enumerate(((1000, 26, 46, 20), (1070, 40, 70, 16), (1170, 64, 104, 12),
                                                      (1310, 100, 160, 7))):
                art.gravestones(c, yb, -20, W + 20, n, seed=180 + row + seed, hmin=hmin, hmax=hmax, tilt=0.08,
                                rim="#6f948c", kinds=("round", "slab"))
        art.grass(c, 1360, 0, W, "#030506", n=460, hmin=14, hmax=60, seed=31 + seed)
        comp(img, c.rgba())
        img += np.exp(-((yy - 1020) / 220.0) ** 2)[..., None] * np.array([0.03, 0.045, 0.05], np.float32)
        self.img = img
        self.mist = mist
        self.fog = Fog(seed=61 + seed, scale=300, color="#86aaa4", density=0.2 if not mist else 0.3, top=0.5,
                       bottom=0.85, speed=20, w=W, h=H)
        if mist:
            r = np.random.default_rng(7 + seed)
            self.wisps = []
            for i in range(7):
                wd, ht = r.uniform(180, 340), r.uniform(60, 120)
                m = sprite(lambda k, wd=wd, ht=ht: k.ellipse(wd / 2 + 20, ht / 2 + 20, wd / 2, ht / 2, "#ffffff"),
                           int(wd + 40), int(ht + 40), blur=18.0)
                self.wisps.append(dict(m=m, x=r.uniform(80, 1000), y=r.uniform(960, 1180), v=r.uniform(-14, 14),
                                       ph=r.uniform(0, 6.28), dark=i % 2 == 0))

    def render(self, t, u, z=(1.0, 1.05)):
        out = self.img.copy()
        self.fog.apply(out, t)
        if self.mist:
            for g in self.wisps:
                a = (0.42 + 0.22 * math.sin(t * 0.7 + g["ph"])) * min(1.0, u / 1.0)
                x = g["x"] + g["v"] * t
                y = g["y"] + 12 * math.sin(t * 0.5 + g["ph"])
                if g["dark"]:
                    put(out, g["m"], x, y, (0.0, 0.01, 0.015), min(0.85, a * 1.3), mode="dark")
                else:
                    put(out, g["m"], x, y, (0.45, 0.58, 0.56), a * 0.6)
        return finish(out, t, u, z[0], z[1], 5.0, 540, 1050)


class CoffinClose:
    """Close on an old coffin in the dirt, its lid pushed aside, a lantern on the ground."""

    def __init__(self):
        img = np.zeros((H, W, 3), np.float32)
        n = cv2.resize(fbm(H // 4, W // 4, scale=18, octaves=5, seed=71), (W, H), interpolation=cv2.INTER_CUBIC)
        img += (0.035 + 0.04 * n)[..., None] * np.array([0.9, 0.75, 0.6], np.float32)                # dirt
        c = cv()
        coffin(c, 520, 1020, 700, 230, ang=0.12, depth=46, lid=(60, -150, -0.16))
        self.lamp = lantern(c, 900, 1180, s=1.6)
        c.rect(860, 1250, 940, 1262, "#000000", 0.5, blur=6)
        art.grass(c, 1500, 0, W, "#030405", n=300, hmin=10, hmax=50, seed=41)
        comp(img, c.rgba())
        self.img = img
        lx, ly = self.lamp
        self.light = light_map(H, W, lx, ly, 820, power=1.1)
        self.fog = Fog(seed=71, scale=280, color="#86aaa4", density=0.14, top=0.3, bottom=0.9, speed=16, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        fl = flick(t, 9)
        out += self.light[..., None] * np.array(LANT, np.float32) * 0.85 * fl
        lx, ly = self.lamp
        add_spot(out, lx, ly, 40, (1.0, 0.75, 0.4), 0.9 * fl)
        add_spot(out, lx, ly, 9, (1.0, 0.95, 0.8), 1.5)
        self.fog.apply(out, t)
        return finish(out, t, u, 1.1, 1.0, 6.0, 540, 1000)


class TwoCaskets:
    """Moonlight on two plain caskets side by side in an open trench."""

    def __init__(self):
        img = night_sky(81, moon=(800, 360, 48), clouds=0.4)
        land(img, 880, 181, far="#0b161a")
        c = cv()
        for k, (px, ph) in enumerate(((80, 560), (1000, 520))):
            pine(c, px, 930, ph, seed=190 + k)
        art.gravestones(c, 912, 220, 880, 10, seed=191, hmin=24, hmax=56, rim="#5a7c76", kinds=("round", "slab"))
        c.poly([(-20, 940), (W + 20, 932), (W + 20, H), (-20, H)], "#070b0c")
        c.poly([(150, 990), (930, 990), (990, 1270), (90, 1270)], "#010202")                    # the trench
        coffin(c, 350, 1120, 250, 124, ang=math.pi / 2 - 0.04, depth=26, wood="#2a1e14", edge="#9a8466")
        coffin(c, 730, 1120, 250, 124, ang=math.pi / 2 + 0.05, depth=26, wood="#2a1e14", edge="#9a8466")
        art.grass(c, 1300, 0, W, "#030506", n=420, hmin=14, hmax=60, seed=51)
        comp(img, c.rgba())
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        img += np.exp(-((yy - 1110) / 160.0) ** 2) * np.array([0.04, 0.055, 0.06], np.float32)       # moonlight in the pit
        self.img = img
        self.fog = Fog(seed=81, scale=300, color="#86aaa4", density=0.22, top=0.45, bottom=0.8, speed=18, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.06, 6.0, 540, 1100)


def build_pinelake(R):
    t_1871 = R.at("1871,")
    t_story = R.at("a story came")
    t_many = R.at("Many of")
    t_pine = R.at("Pine Lake Cemetery,")
    t_unk = R.at("unknown.")
    t_people = R.at("People say")
    t_upside = R.at("upside down")
    t_buried = R.at("buried alive.")
    t_mass = R.at("a mass grave:")
    t_ten = R.at("about ten")
    t_belle = R.at("Belle Gunness's")
    t_two = R.at("two caskets.")
    t_vis = R.at("Visitors report")
    t_dbl = R.at("double-tap")
    c1 = (R.end("coffins.") + t_many) / 2
    c2 = (R.end("unknown.") + t_people) / 2
    c3 = (R.end("alive.") + R.at("Pine Lake also")) / 2
    c4 = (R.end("caskets.") + t_vis) / 2
    c5 = t_dbl - 0.15

    def d_dig(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("LAPORTE'S OLD CITY CEMETERY")
        paste(f, ctx["l"], W / 2, 300)
        typed(f, "1871", t, t_1871 - 0.1, 420, size=120, rate=0.07)
        red_title(f, "BURIED ALIVE?", 120, t, -0.2)

    def d_rows(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("PINE LAKE CEMETERY · LAPORTE")
            ctx["l2"] = lab("FIRST BURIAL: 1858", 30, (200, 214, 206))
        paste(f, ctx["l"], W / 2, 300, appear(t, c1 + 0.05, 0.3))
        paste(f, ctx["l2"], W / 2, 350, appear(t, t_pine + 0.3, 0.3))
        typed(f, "UNKNOWN", t, t_unk - 0.15, 470, size=110, rate=0.06)

    def d_coffin(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("WHAT PEOPLE SAY")
        paste(f, ctx["l"], W / 2, 300, appear(t, c2 + 0.05, 0.3))
        typed(f, "UPSIDE DOWN", t, t_upside - 0.1, 420, size=92, rate=0.05)
        typed(f, "AND TWISTED", t, t_upside + 0.75, 520, size=92, rate=0.05)
        if t >= t_buried - 0.3:
            red_title(f, "AS IF BURIED ALIVE", 104, t, t_buried - 0.1)

    def p_mass(ctx):
        ctx["s"] = TwoCaskets()
        ctx["l"] = lab("A MASS GRAVE")
        ctx["n1"] = ttl("ABOUT 10 UNKNOWN MEN", 70)
        ctx["n2"] = glow(T("from Belle Gunness's farm", "fell_it", 50, (226, 214, 190)), (0, 0, 0), radius=14,
                         strength=0.9)
        ctx["n3"] = ttl("TWO CASKETS", 70)

    def d_mass(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        paste(f, ctx["l"], W / 2, 300, appear(t, t_mass - 0.1, 0.3))
        a1 = appear(t, t_ten - 0.1, 0.3)
        paste(f, ctx["n1"], W / 2, 420 + 14 * (1 - a1), a1)
        paste(f, ctx["n2"], W / 2, 510, appear(t, t_belle - 0.05, 0.3))
        a3 = appear(t, t_two - 0.1, 0.3)
        paste(f, ctx["n3"], W / 2, 640 + 14 * (1 - a3), a3)

    def d_mist(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("SHADOWS LIKE MIST")
        paste(f, ctx["l"], W / 2, 300, appear(t, c4 + 0.05, 0.3))

    def p_end(ctx):
        ctx["s"] = LakeCemetery(seed=2, mist=True)
        ctx["cta"] = C.DoubleTap("FOR THE NEXT LEGEND", "Please visit in daylight", color1=MINT, glow1=(20, 120, 80),
                                 kind1="bask", size1=96, y=520)

    def d_end(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u + 5.0)))
        bs.shade(f)
        ctx["cta"].draw(f, u)

    scenes = [C.Scene(0.0, c1, d_dig, scene(Exhume)), C.Scene(c1, c2, d_rows, scene(LakeCemetery)),
              C.Scene(c2, c3, d_coffin, scene(CoffinClose)), C.Scene(c3, c4, d_mass, p_mass),
              C.Scene(c4, c5, d_mist, scene(LakeCemetery, seed=1, mist=True, close=True)),
              C.Scene(c5, R.dur + 1, d_end, p_end, flicker=0.0)]
    scenes[2].flicker = 0.45
    atm = bs.Atmos(tint=(196, 204, 206), fog=0.08, vignette=0.6, grain=12, seed=9)
    film = C.Film(R, scenes, flashes=[(0.35, 0.3)], flicker=0.2, atmos=atm)

    import sfx as X
    n = int((R.dur + 0.5) * SR)
    wind = X.wind(R.dur + 0.5, seed=36, strength=0.8).mean(1)[:n]
    hum = X.eerie_hum(c5 - c4 + 1.0, seed=39, f=47.0).mean(1)
    dig = scrape(c1 - 0.5, seed=11)
    ev = [(wind, 0.0, 0.5, "bed"), (X.thunder(5.0, seed=10).mean(1), 0.37, 0.6, "bed"), ("hit", 0.05, 0.6),
          (dig, 0.6, 0.45, "bed"), ("type", t_1871 - 0.1, 0.9), ("hit", t_story, 0.5), ("whoosh", c1, 0.5),
          (X.owl(seed=24).mean(1), c1 + 0.6, 0.3), ("type", t_unk - 0.15, 0.9), ("whoosh", c2, 0.5),
          (X.creak(2.0, seed=13).mean(1), c2 + 0.2, 0.55), ("type", t_upside - 0.1, 0.8),
          ("type", t_upside + 0.75, 0.8), (X.heartbeat(2.6, bpm=70).mean(1), t_buried - 1.2, 0.5, "bed"),
          ("hit", t_buried - 0.1, 0.8), ("whoosh", c3, 0.5), ("pop", t_ten - 0.1, 0.5), ("pop", t_two - 0.1, 0.5),
          ("whoosh", c4, 0.5), (hum, c4, 0.8, "bed"), (whispers(c5 - c4, seed=6), c4 + 0.3, 0.45, "bed"),
          ("pop", c5 + 0.12, 0.9), ("pop", c5 + 0.42, 0.9), ("hit", c5 + 0.5, 0.6)]
    return film, ev, haunt_music(R, seed=90, prog=6), TITLES["pinelake"]


# --------------------------------------------------------------------------------------------- ORR LAKE: THE DOCTOR

class FullMoonRoad:
    """Orr Lake Road under a big full moon, the lake catching its light."""

    def __init__(self, sign=True):
        mx, my, mr = 300, 470, 100
        img = night_lake_sky(131, moon=(mx, my, mr), clouds=0.22, glow_k=0.9)
        hz = 1010
        art.hills(img, hz - 20, 26, 460, "#0a1519", 181, rim="#46645f", rim_w=3, rim_a=0.35)
        yy = np.arange(H, dtype=np.float32)[:, None]
        xx = np.arange(W, dtype=np.float32)[None, :]
        lake = ((yy >= hz) & (yy < 1300)).astype(np.float32) * np.ones((1, W), np.float32)
        lake *= np.clip((700 - xx - (yy - hz) * 0.9) / 30.0, 0, 1)
        ripple = cv2.resize(fbm(H // 8, W // 2, scale=6, octaves=3, seed=182), (W, H), interpolation=cv2.INTER_CUBIC)
        water = np.array([0.025, 0.048, 0.058], np.float32) * (0.7 + 0.6 * ripple[..., None])
        glint = np.exp(-((xx - mx) / (34 + (yy - hz) * 0.32)) ** 2) * (yy > hz) * (0.25 + 0.75 * ripple)
        water = water + (glint * 1.0)[..., None] * np.array([0.75, 0.88, 0.85], np.float32)
        img = img * (1 - lake[..., None]) + water * lake[..., None]
        ground = ((yy >= hz) * (1 - lake)).astype(np.float32)
        img = img * (1 - ground[..., None]) + np.array([0.018, 0.03, 0.034], np.float32) * ground[..., None]
        c = cv()
        road(c, 760, hz + 4, bottom=(520, 1300), color="#17242a", edge="#3a5856", curve=0.3)
        for k, (tx, th) in enumerate(((920, 860), (1040, 1040), (700, 300), (820, 420), (640, 220))):
            art.tree(c, tx, hz + 10 + (th > 500) * (th * 0.28), th, seed=190 + k, depth=7, spread=0.6, lean=-0.18)
        for k in range(9):
            art.tree(c, 40 + k * 70, hz - 8, 70 + 40 * (k % 3), seed=200 + k, depth=5, spread=0.6)
        art.grass(c, 1500, 0, W, "#030506", n=420, hmin=20, hmax=90, seed=14)
        if sign:
            c.rect(786, 760, 802, 1640, "#0b0f10")
            c.line([(788, 760), (788, 1640)], "#44585a", 2, 0.6)
        comp(img, c.rgba())
        if sign:
            from reel_haunts import street_sign
            comp(img, layer_from_pil(street_sign("ORR LAKE RD"), 794 - 280, 640))
        self.img = img
        self.fog = Fog(seed=131, scale=320, color="#7fa39e", density=0.2, top=0.5, bottom=0.66, speed=22, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.07, 4.0, 520, 900)


class LakeHouse:
    """An old farmhouse by the lake, one window lit upstairs."""

    def __init__(self):
        img = night_lake_sky(141, moon=(880, 380, 60), clouds=0.3)
        land(img, 1120, 141, far="#0a1418")
        c = cv()
        lights = cv()
        art.farmhouse(c, lights, 240, 1150, s=1.05, lit=(0, 1, 0, 0, 0))
        art.tree(c, 120, 1160, 980, seed=211, depth=8, spread=0.7, lean=0.1)
        art.tree(c, 980, 1150, 780, seed=212, depth=8, spread=0.62, lean=-0.14)
        art.fence(c, 1220, -20, 1100, spacing=40, h=70, seed=8, broken=0.3)
        art.grass(c, 1300, 0, W, "#030506", n=420, hmin=14, hmax=60, seed=15)
        comp(img, c.rgba())
        self.lights = lights.rgba()[..., :3]
        self.img = img
        self.fog = Fog(seed=141, scale=300, color="#86aaa4", density=0.22, top=0.5, bottom=0.8, speed=18, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        out += self.lights * (0.8 + 0.2 * flick(t, 4))
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.07, 6.0, 470, 900)


class Cellar:
    """A dark cellar: plank walls, a dirt floor and two barrels in a swinging lantern's light. No bodies shown."""

    def __init__(self):
        img = np.zeros((H, W, 3), np.float32)
        yy = np.arange(H, dtype=np.float32)[:, None]
        xx = np.arange(W, dtype=np.float32)[None, :]
        boards = (np.abs(((xx + 30) % 120) - 60) > 56).astype(np.float32)
        grain = cv2.resize(fbm(H // 6, W // 2, scale=8, octaves=4, seed=91), (W, H), interpolation=cv2.INTER_CUBIC)
        wall = (0.08 + 0.06 * grain) * (1 - 0.65 * boards)
        img += (wall * (yy < 1150))[..., None] * np.array([0.9, 0.7, 0.55], np.float32)
        floor = cv2.resize(fbm(H // 4, W // 4, scale=14, octaves=5, seed=92), (W, H), interpolation=cv2.INTER_CUBIC)
        img += ((0.05 + 0.04 * floor) * (yy >= 1150))[..., None] * np.array([0.85, 0.72, 0.6], np.float32)
        c = cv()
        c.rect(0, 1142, W, 1156, "#0a0604", 0.9, blur=3)
        barrel(c, 350, 1290, 440, color="#4a3020", hoop="#1a100a", lit=1.0)
        barrel(c, 730, 1270, 410, color="#442c1c", hoop="#1a100a", lit=1.0)
        comp(img, c.rgba())
        self.img = img
        self.fog = Fog(seed=93, scale=260, color="#5a4a3a", density=0.12, top=0.0, bottom=0.8, speed=10, w=W, h=H)
        self.lamp = Canvas(W, H)

    def render(self, t, u):
        out = self.img.copy()
        sw = math.sin(t * 1.9) * 0.18
        px, py = 540, 260
        lx, ly = px + math.sin(sw) * 380, py + math.cos(sw) * 380
        lm = light_map(H, W, lx, ly + 120, 1100, power=1.0)
        fl = flick(t, 11)
        out *= (0.4 + 1.5 * lm[..., None] * fl)
        out += lm[..., None] * np.array(LANT, np.float32) * 0.22 * fl
        c = Canvas(W, H)
        c.line([(px, 0), (px, py - 60), (lx, ly - 30)], "#050403", 4)
        lantern(c, lx, ly - 30, s=1.8)
        comp(out, c.rgba())
        add_spot(out, lx, ly + 14, 60, (1.0, 0.75, 0.4), 0.6 * fl)
        add_spot(out, lx, ly + 14, 14, (1.0, 0.95, 0.8), 1.4)
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.05, 4.0, 540, 1050)


class LanternWoods:
    """Full moon through bare trees; a lantern moving into the woods with two figures, one with a hook."""

    def __init__(self, dur=6.0):
        self.dur = dur
        img = night_lake_sky(151, moon=(760, 420, 96), clouds=0.25, glow_k=0.85)
        land(img, 1080, 151, far="#0a1418")
        c = cv()
        for k in range(14):
            tx = -40 + k * 86 + (k % 3) * 18
            th = 700 + (k * 137) % 500
            art.tree(c, tx, 1100 + (k % 4) * 30, th, seed=220 + k, depth=7, spread=0.55, lean=((k % 5) - 2) * 0.05)
        c.poly([(-20, 1180), (W + 20, 1170), (W + 20, H), (-20, H)], "#040708")
        art.grass(c, 1400, 0, W, "#030405", n=460, hmin=14, hmax=70, seed=16)
        comp(img, c.rgba())
        self.img = img
        self.walk = []
        self.lamp_pt = (100, 360)
        for lg in (12, 3, -12, 3):
            store = {}

            def draw(k, lg=lg, store=store):
                f1 = art.figure(k, 170, 600, 560, color="#ffffff", coat=True, hat="brim", arms=((22, 16), (-6, -4)),
                                legs=(lg, -lg))
                f2 = art.figure(k, 370, 600, 520, color="#ffffff", coat=True, arms=((6, 2), (-16, -28)),
                                legs=(-lg, lg))
                hx, hy = f2["hands"][1]
                hook_arm(k, hx, hy, s=2.2, color="#ffffff")
                lx, ly = f1["hands"][0]
                store["lamp"] = lantern(k, lx, ly, s=2.0, color="#ffffff")
            self.walk.append(sprite(draw, 520, 640))
            self.lamp_pt = store["lamp"]
        self.fog = Fog(seed=151, scale=300, color="#86aaa4", density=0.26, top=0.5, bottom=0.85, speed=16, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        p = min(1.0, u / self.dur)
        s = 0.74 - 0.40 * p
        x = 560 + 140 * p
        y = 1290 - 120 * p
        m = self.walk[int(u * 4) % 4]
        mm = cv2.resize(m, (max(2, int(m.shape[1] * s)), max(2, int(m.shape[0] * s))))
        lx = x - m.shape[1] * s / 2 + self.lamp_pt[0] * s
        ly = y - m.shape[0] * s + self.lamp_pt[1] * s
        lm = light_map(H, W, lx, ly, 520 * (0.5 + s), power=1.3)
        fl = flick(t, 13)
        out += lm[..., None] * np.array(LANT, np.float32) * 0.5 * fl
        put(out, mm, x, y, (0.006, 0.008, 0.01), 0.96, mode="dark")
        add_spot(out, lx, ly, 40 * s + 10, (1.0, 0.75, 0.4), 0.9 * fl)
        add_spot(out, lx, ly, 8 * s + 3, (1.0, 0.95, 0.8), 1.6)
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.06, 6.0, 640, 1150)


def folk_card(title, lines):
    card = bs.aged_paper(900, 640, seed=29)
    d = ImageDraw.Draw(card)
    f1 = C.font("fell_sc", 60)
    f2 = C.font("typew", 40)
    d.text(((900 - f1.getlength(title)) / 2, 70), title, font=f1, fill=(42, 30, 20, 255))
    d.line([(120, 162), (780, 162)], fill=(90, 70, 50, 200), width=3)
    for i, ln in enumerate(lines):
        d.text(((900 - f2.getlength(ln)) / 2, 214 + i * 58), ln, font=f2, fill=(52, 40, 28, 255))
    return card.rotate(-2.0, resample=Image.BICUBIC, expand=True)


def build_orr2(R):
    t_full = R.at("Tonight's a")
    t_orr = R.at("On Orr")
    t_walks = R.at("doctor walks.")
    t_some = R.at("Sometime in")
    t_1900 = R.at("1900s,")
    t_doc = R.at("a doctor lived")
    t_when = R.at("When they")
    t_cant = R.at("couldn't let")
    t_kept = R.at("He kept")
    t_barrels = R.at("barrels.")
    t_on = R.at("On full-moon")
    t_lant = R.at("his lantern")
    t_hook = R.at("a hook")
    t_no = R.at("There's no")
    t_people = R.at("People live")
    t_dbl = R.at("double-tap")
    c1 = (R.end("walks.") + t_some) / 2
    c2 = (R.end("daughter.") + t_when) / 2
    c3 = (R.end("barrels.") + t_on) / 2
    c4 = (R.end("hand.") + t_no) / 2
    c5 = t_dbl - 0.15

    def d_road(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("FULL MOON TONIGHT · ORR LAKE ROAD")
        paste(f, ctx["l"], W / 2, 300)
        red_title(f, "THE DOCTOR'S LANTERN", 104, t, -0.2)

    def d_house(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("THE STORY GOES")
        paste(f, ctx["l"], W / 2, 300, appear(t, c1 + 0.05, 0.3))
        typed(f, "SOMETIME IN THE 1900s", t, t_1900 - 0.4, 420, size=74, rate=0.04)

    def d_cellar(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if t >= t_cant - 0.3:
            red_title(f, "HE COULDN'T LET THEM GO", 92, t, t_cant - 0.1)
        typed(f, "BARRELS", t, t_barrels - 0.15, 420, size=110, rate=0.06)

    def d_woods(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("ON FULL-MOON NIGHTS")
        paste(f, ctx["l"], W / 2, 300, appear(t, c3 + 0.05, 0.3))

    def p_folk(ctx):
        ctx["s"] = Folklore()
        ctx["card"] = folk_card("Orr Lake Road's Doctor", ["A LaPorte County legend", "",
                                                           "\"La Porte County's Top 10", "Most Haunted,\"",
                                                           "The News-Dispatch, 2011"])
        ctx["stamp"] = bs.stamp([("NO", 96), ("RECORD", 104)], color=(220, 58, 44))
        ctx["keep"] = vr.pill("People live here: keep rolling", "xbold", 44, (10, 20, 18), MINT + (255,), padx=30,
                              pady=16)

    def d_folk(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        a = appear(t, c4 + 0.05, 0.35)
        paste(f, ctx["card"], W / 2, 760 + 30 * (1 - a), a)
        if t >= t_no + 0.3:
            k = appear(t, t_no + 0.3, 0.12)
            paste(f, scaled(ctx["stamp"], 1.0 + 1.0 * (1 - k)), W / 2 + 180, 1135, min(1.0, k * 1.2))
        paste(f, ctx["keep"], W / 2, 400, appear(t, t_people - 0.1, 0.3))
        bs.shade(f)
        bs.credit_line(f, "Legend: The News-Dispatch (Michigan City), 2011")

    def p_end(ctx):
        ctx["s"] = FullMoonRoad(sign=False)
        ctx["cta"] = C.DoubleTap("FOR THE NEXT LEGEND", "and keep rolling on Orr Lake Road", color1=(255, 120, 100),
                                 glow1=(140, 0, 0), kind1="bask", size1=96, y=520)

    def d_end(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u + 4.0)))
        bs.shade(f)
        ctx["cta"].draw(f, u)

    scenes = [C.Scene(0.0, c1, d_road, scene(FullMoonRoad)), C.Scene(c1, c2, d_house, scene(LakeHouse)),
              C.Scene(c2, c3, d_cellar, scene(Cellar)), C.Scene(c3, c4, d_woods, scene(LanternWoods, dur=c4 - c3)),
              C.Scene(c4, c5, d_folk, p_folk, flicker=0.0), C.Scene(c5, R.dur + 1, d_end, p_end, flicker=0.0)]
    scenes[2].flicker = 0.5
    atm = bs.Atmos(tint=(196, 204, 206), fog=0.08, vignette=0.58, grain=12, seed=11)
    film = C.Film(R, scenes, flashes=[], flicker=0.2, atmos=atm)

    import sfx as X
    n = int((R.dur + 0.5) * SR)
    wind = X.wind(R.dur + 0.5, seed=37, strength=0.7).mean(1)[:n]
    ev = [(wind, 0.0, 0.5, "bed"), (X.owl(seed=24).mean(1), 0.9, 0.35), ("hit", t_walks, 0.5), ("whoosh", c1, 0.5),
          ("type", t_1900 - 0.4, 0.7), ("whoosh", c2, 0.5), (X.creak(2.4, seed=21).mean(1), c2 + 0.1, 0.5),
          ("hit", t_cant - 0.1, 0.7), ("type", t_barrels - 0.15, 0.8),
          (X.heartbeat(c3 - c2, bpm=64).mean(1), c2 + 0.3, 0.45, "bed"), ("whoosh", c3, 0.5),
          (steps(c4 - c3, seed=8), c3 + 0.2, 0.4, "bed"), (X.creak(1.4, seed=22).mean(1), t_lant, 0.3),
          ("hit", t_hook, 0.5), ("whoosh", c4, 0.5), ("hit", t_no + 0.3, 0.8), ("pop", t_people - 0.1, 0.5),
          ("pop", c5 + 0.12, 0.9), ("pop", c5 + 0.42, 0.9), ("hit", c5 + 0.5, 0.6)]
    return film, ev, haunt_music(R, seed=100, prog=9), TITLES["orr2"]


# --------------------------------------------------------------------------------------------- THE COUNTDOWN

def badge(n):
    img = glow(T("No. %d" % n, "bask", 150, MINT), (20, 120, 80), radius=30, strength=0.8)
    return img


def build_top4(R):
    t_four = R.at("Four places")
    t_n4, t_n3, t_n2 = R.at("Number four:"), R.at("Number three:"), R.at("Number two:")
    t_n1 = R.at("And number one:")
    t_orr = R.at("Orr Lake Road,")
    t_pine = R.at("Pine Lake Cemetery,")
    t_patton = R.at("Patton Cemetery,")
    t_posey = R.at("Posey Chapel")
    t_bells = R.at("bells,")
    t_white = R.at("woman in white.")
    t_which = R.at("Which one")
    t_tell = R.at("Tell us")
    c1 = t_n4 - 0.2
    c2 = t_n3 - 0.2
    c3 = t_n2 - 0.2
    c4 = t_n1 - 0.2
    c5 = t_which - 0.2

    def d_open(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("LAPORTE COUNTY · 4 PLACES")
            ctx["t1"] = glow(fitT("WHERE THE DEAD", "bask", 104, BONE, max_w=C.CW, min_size=60), (0, 0, 0), radius=24,
                             strength=0.95)
            ctx["t2"] = glow(fitT("DON'T REST", "bask", 150, (250, 70, 56), max_w=C.CW, min_size=60), (150, 0, 0),
                             radius=34, strength=0.7)
        paste(f, ctx["l"], W / 2, 300)
        k = ease_out(u / 0.6)
        paste(f, scaled(ctx["t1"], 1.06 - 0.06 * k), W / 2, 520)
        paste(f, scaled(ctx["t2"], 1.06 - 0.06 * k), W / 2, 660)

    def make_item(n, name, line, at_name, scene_cls, *args, **kw):
        def prep(ctx):
            ctx["s"] = scene_cls(*args, **kw)
            ctx["b"] = badge(n)
            ctx["nm"] = ttl(name, 76)
            ctx["ln"] = glow(T(line, "fell_it", 46, (226, 214, 190)), (0, 0, 0), radius=14, strength=0.9)

        def draw(f, u, t, ctx):
            f.alpha_composite(to_pil(ctx["s"].render(t, u)))
            bs.shade(f)
            a = appear(u, 0.0, 0.25)
            paste(f, scaled(ctx["b"], 1.25 - 0.25 * a), W / 2, 390, a)
            a2 = appear(t, at_name - 0.1, 0.3)
            paste(f, ctx["nm"], W / 2, 540 + 12 * (1 - a2), a2)
            paste(f, ctx["ln"], W / 2, 630, appear(t, at_name + 0.7, 0.3))
        return prep, draw

    p4, d4 = make_item(4, "ORR LAKE ROAD", "a doctor's lantern, under a full moon", t_orr, LanternWoods, dur=c2 - c1)
    p3, d3 = make_item(3, "PINE LAKE CEMETERY", "shadows like mist over a mass grave", t_pine, LakeCemetery, seed=3,
                       mist=True, close=True)
    p2, d2 = make_item(2, "PATTON CEMETERY", "voices, and no one there", t_patton, Shadows)
    p1, d1 = make_item(1, "POSEY CHAPEL CEMETERY", "bells, lights and a woman in white", t_posey, PoseyWhite)

    def p_end(ctx):
        ctx["s"] = TownCemetery(seed=5, fog_d=0.34)
        ctx["q"] = glow(fitT("WHICH ONE WOULD", "bask", 96, BONE, max_w=C.CW, min_size=60), (0, 0, 0), radius=24,
                        strength=0.95)
        ctx["q2"] = glow(fitT("YOU VISIT?", "bask", 140, MINT, max_w=C.CW, min_size=60), (20, 120, 80), radius=30,
                         strength=0.8)
        names = ["1 · Posey Chapel", "2 · Patton", "3 · Pine Lake", "4 · Orr Lake Road"]
        ctx["pills"] = [vr.pill(nm, "xbold", 44, (10, 20, 18), MINT + (255,), padx=28, pady=14) for nm in names]
        ctx["c"] = glow(T("Tell us in the comments", "fell_it", 54, (226, 214, 190)), (0, 0, 0), radius=14,
                        strength=0.9)

    def d_end(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        dim(f, 0.35 * appear(u, 0.0, 0.3))
        paste(f, ctx["q"], W / 2, 420, appear(u, 0.0, 0.25))
        paste(f, ctx["q2"], W / 2, 545, appear(u, 0.1, 0.25))
        for i, pl in enumerate(ctx["pills"]):
            a = appear(u, 0.35 + 0.12 * i, 0.25)
            paste(f, pl, W / 2, 700 + i * 104 + 10 * (1 - a), a)
        paste(f, ctx["c"], W / 2, 1150, appear(t, t_tell - 0.05, 0.3))

    scenes = [C.Scene(0.0, c1, d_open, scene(TownCemetery, seed=4, fog_d=0.3)), C.Scene(c1, c2, d4, p4),
              C.Scene(c2, c3, d3, p3), C.Scene(c3, c4, d2, p2), C.Scene(c4, c5, d1, p1),
              C.Scene(c5, R.dur + 1, d_end, p_end, flicker=0.0)]
    atm = bs.Atmos(tint=(196, 204, 206), fog=0.08, vignette=0.58, grain=12, seed=13)
    film = C.Film(R, scenes, flashes=[(0.35, 0.3)], flicker=0.2, atmos=atm)

    import sfx as X
    n = int((R.dur + 0.5) * SR)
    wind = X.wind(R.dur + 0.5, seed=38, strength=0.8).mean(1)[:n]
    bell = lambda sd, f0: X.lp(X.bell(f=f0, dur=6.0, seed=sd).mean(1), 2400)
    ev = [(wind, 0.0, 0.5, "bed"), (X.thunder(5.0, seed=11).mean(1), 0.37, 0.6, "bed"), ("hit", 0.05, 0.6),
          ("hit", c1 + 0.05, 0.7), (steps(c2 - c1, seed=9), c1 + 0.3, 0.35, "bed"), ("hit", c2 + 0.05, 0.7),
          (whispers(c3 - c2, seed=7), c2 + 0.3, 0.35, "bed"), ("hit", c3 + 0.05, 0.7),
          (whispers(c4 - c3, seed=8), c3 + 0.3, 0.5, "bed"), ("hit", c4 + 0.05, 0.8),
          (bell(7, 196.0), t_bells, 0.5, "bed"), (bell(9, 210.0), t_white, 0.35, "bed"), ("whoosh", c5, 0.5)]
    ev += [("pop", c5 + 0.35 + 0.12 * i, 0.5) for i in range(4)]
    return film, ev, haunt_music(R, seed=110, prog=4), TITLES["top4"]


BUILD = {"pinelake": build_pinelake, "orr2": build_orr2, "top4": build_top4}


def main(name, mode, times=None):
    R = C.Reel(name)
    film, ev, music, title = BUILD[name](R)
    if mode == "stills":
        ts = times or [round(R.dur * k / 12, 2) for k in range(12)]
        print(film.stills([t for t in ts if t < R.dur], name))
        return
    vid = os.path.join(C.OUT, "_%s_video.mp4" % name)
    film.video(vid, cover_t=0.8)
    mix = C.soundtrack(R, music, ev, music_gain=0.5)
    out = os.path.join(C.OUT, OUTFILES[name])
    C.finish(R, vid, mix, out, title)
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None)
