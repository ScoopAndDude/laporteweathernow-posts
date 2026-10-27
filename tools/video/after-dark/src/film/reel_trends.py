"""Three trend reels (Sun., Oct. 25, 2026): tonight's Hunter's Moon, Indiana's favorite Halloween candy, and the
clocks falling back next Sunday.

    python3 reel_trends.py moon|candy|dst stills|video [times]

Moon and sun (PyEphem, La Porte 41.6106 N, 86.7225 W, standard refraction, upper limb, rounded to the minute):
full moon Sun. Oct. 25, 11:12 PM CDT (04:11:45 UTC Oct. 26); moonrise 5:16 PM CDT at azimuth 69 (east-northeast);
sunset 5:51 PM CDT; Halloween moonrise 10:49 PM CDT (58% lit). The first full moon after the Harvest Moon (Sept. 26),
so the Hunter's Moon (Almanac.com lists it the same way). Not a supermoon (368,900 km), so the reel doesn't say so.
Tonight's sky: NWS point forecast for La Porte, as of 9:17 AM Sun. Oct. 25 ("Partly cloudy, with a low around 47").
Everything is drawn.
"""
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import reels_common as C
from reels_common import bs, vr, hw, W, H, SR, glow, paste, scaled, appear, ease, ease_out, dim
from core import fbm, add_spot, smoothstep, clamp01, Canvas
import art
from reel_frank import to_pil, zoom
from reel_hwfc import spooky_music, panel, label

ORANGE, GOLDEN, CREAM, LAV, FAINT, PURPLE = hw.ORANGE, hw.GOLDEN, hw.CREAM, hw.LAV, hw.FAINT, hw.PURPLE
X0, CW = vr.X0, vr.CW
INK = vr.INK
MOONGOLD = (255, 214, 150)

C.WEIGHT.update({"516": 3.35, "551": 4.35, "1112": 4.35, "1049": 4.35, "543": 4.35, "441": 4.35, "417": 4.35,
                 "2": 1.35, "NERDS": 1.35, "MM's": 3.35, "CandyStorecom's": 5.35})
OUTFILES = {"moon": "hunters-moon-tonight-la-porte.mp4", "candy": "indiana-favorite-halloween-candy-2026.mp4",
            "dst": "clocks-fall-back-la-porte-sunsets.mp4"}
TITLES = {"moon": "Hunter's Moon Tonight", "candy": "Indiana's Favorite Halloween Candy",
          "dst": "Clocks Fall Back Next Sunday"}


# ============================================================================================ painting helpers

def grad(stops, h=H, w=W):
    """stops: [(y px, (r, g, b) 0-255)] -> float RGB 0..1"""
    ys = np.arange(h, dtype=np.float32)
    col = np.stack([np.interp(ys, [s[0] for s in stops], [s[1][c] / 255.0 for s in stops]) for c in range(3)], 1)
    return np.repeat(col[:, None, :], w, axis=1).astype(np.float32)


# the main maria, roughly where they sit on the full moon (x right, y down, in moon radii)
MARIA = [(-0.36, -0.34, 0.30, 0.9), (0.15, -0.40, 0.17, 0.9), (0.33, -0.12, 0.21, 0.85), (0.70, -0.30, 0.10, 0.85),
         (-0.62, -0.02, 0.33, 0.55), (-0.20, 0.30, 0.18, 0.65), (0.56, 0.12, 0.15, 0.7), (0.40, 0.31, 0.09, 0.65),
         (-0.50, 0.42, 0.09, 0.7), (-0.03, 0.05, 0.12, 0.45), (-0.80, -0.38, 0.12, 0.5)]


def moon_sprite(r, warm=1.0, seed=3, contrast=1.0):
    """A full moon r px in radius. warm 0..1 tints it toward a rising, orange moon (more orange at the bottom).
    Returns (rgb, alpha) float arrays (n, n, 3) / (n, n)."""
    n = 2 * r + 6
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    c = n / 2
    x, y = (xx - c) / r, (yy - c) / r
    d = np.sqrt(x * x + y * y)
    a = smoothstep(1.0, 1.0 - 1.8 / r, d).astype(np.float32)
    s = max(8, n // 3)
    nz = cv2.resize(fbm(s, s, scale=max(3.0, s / 6.0), octaves=4, seed=seed), (n, n), interpolation=cv2.INTER_CUBIC)
    nz2 = cv2.resize(fbm(s, s, scale=max(2.0, s / 18.0), octaves=3, seed=seed + 5), (n, n), interpolation=cv2.INTER_CUBIC)
    dark = np.zeros_like(d)
    for mx, my, mr, k in MARIA:
        e = np.sqrt((x - mx) ** 2 + (y - my) ** 2) / mr
        dark = np.maximum(dark, k * smoothstep(1.7, 0.15, e + 0.55 * (nz - 0.5)))
    dark = cv2.GaussianBlur(dark, (0, 0), max(1.0, r / 40))
    tycho = np.exp(-((x + 0.12) ** 2 + (y - 0.70) ** 2) / 0.004)
    lum = (1 - 0.22 * d ** 2) * (1 - 0.24 * contrast * dark) * (0.94 + 0.09 * nz2) + 0.10 * tycho
    v = clamp01((y + 1) / 2)[..., None]
    pale = np.array([0.98, 0.97, 0.92], np.float32)
    top = pale * (1 - warm) + np.array([1.0, 0.86, 0.60], np.float32) * warm
    bot = pale * (1 - warm) + np.array([1.0, 0.64, 0.34], np.float32) * warm
    col = (top * (1 - v) + bot * v) * lum[..., None]
    return col.astype(np.float32), a


def halo_sprite(r, color, k1=0.9, k2=3.2, s1=0.32, s2=0.55, reach=4.5):
    """Soft additive glow around a moon of radius r (n x n x 3)."""
    n = int(2 * r * reach)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.sqrt((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / r
    e = np.maximum(d - 0.95, 0)
    g = (np.exp(-e * k1) * s1 + np.exp(-e * k2) * s2) * smoothstep(reach, reach * 0.6, d)
    return (g[..., None] * np.array(color, np.float32) / 255.0).astype(np.float32)


def add_at(frame, spr, cx, cy, k=1.0):
    hh, ww = spr.shape[:2]
    x0, y0 = int(round(cx - ww / 2)), int(round(cy - hh / 2))
    X0_, Y0_, X1_, Y1_ = max(0, x0), max(0, y0), min(W, x0 + ww), min(H, y0 + hh)
    if X1_ > X0_ and Y1_ > Y0_:
        frame[Y0_:Y1_, X0_:X1_] += spr[Y0_ - y0:Y1_ - y0, X0_ - x0:X1_ - x0] * k


def over_at(frame, col, a, cx, cy, k=1.0):
    hh, ww = a.shape
    x0, y0 = int(round(cx - ww / 2)), int(round(cy - hh / 2))
    X0_, Y0_, X1_, Y1_ = max(0, x0), max(0, y0), min(W, x0 + ww), min(H, y0 + hh)
    if X1_ > X0_ and Y1_ > Y0_:
        aa = a[Y0_ - y0:Y1_ - y0, X0_ - x0:X1_ - x0, None] * k
        frame[Y0_:Y1_, X0_:X1_] = frame[Y0_:Y1_, X0_:X1_] * (1 - aa) + col[Y0_ - y0:Y1_ - y0, X0_ - x0:X1_ - x0] * aa


def comp_layer(frame, lay):
    """lay: premultiplied float RGBA, full frame."""
    frame *= (1 - lay[..., 3:4])
    frame += lay[..., :3]
    return frame


def ridge_layer(base, amp, scale, color, seed, rim=None, rim_a=0.0, rim_w=3.0, y_max=H):
    prof = art.ridge(W, base, amp, scale, seed)
    yy = np.arange(H, dtype=np.float32)[:, None]
    cov = clamp01(yy - prof[None, :] + 0.5) * (yy < y_max)
    lay = np.zeros((H, W, 4), np.float32)
    lay[..., :3] = cov[..., None] * np.array(color, np.float32) / 255.0
    if rim is not None:
        rimm = np.exp(-np.maximum(yy - prof[None, :], 0) / rim_w) * cov * rim_a
        lay[..., :3] += rimm[..., None] * np.array(rim, np.float32) / 255.0
    lay[..., 3] = cov
    return lay, prof


def town(c, base, seed=2, color="#100f22", lit="#ffc27a", x0=0, x1=W, steeple=None, tower=None, lit_p=0.35):
    """Small-town rooftops along a shoreline, with a few lit windows, a church steeple and a water tower."""
    r = np.random.default_rng(seed)
    x = x0 - 20
    wins = []
    while x < x1 + 20:
        w = r.uniform(70, 150)
        h = r.uniform(46, 96) * (1.5 if r.uniform() < 0.18 else 1.0)
        roof = r.uniform(18, 40)
        if r.uniform() < 0.25:                          # a tree between houses
            tx = x + w * 0.5
            th = r.uniform(80, 150)
            c.ellipse(tx, base - th * 0.62, th * 0.34, th * 0.42, color)
            c.rect(tx - 5, base - th * 0.3, tx + 5, base, color)
            x += th * 0.5
            continue
        c.poly([(x, base), (x, base - h), (x + w * 0.5, base - h - roof), (x + w, base - h), (x + w, base)], color)
        if r.uniform() < 0.4:                           # chimney
            cx = x + w * r.uniform(0.6, 0.8)
            c.rect(cx, base - h - roof * 0.8, cx + 12, base - h - roof * 0.2, color)
        for _ in range(int(r.integers(0, 3))):
            if r.uniform() < lit_p:
                wx = x + r.uniform(12, w - 30)
                wy = base - r.uniform(18, h - 14)
                wins.append((wx, wy))
        x += w + r.uniform(4, 26)
    if steeple:
        sx, sh = steeple
        c.rect(sx - 46, base - sh * 0.45, sx + 46, base, color)
        c.poly([(sx - 46, base - sh * 0.45), (sx, base - sh * 0.58), (sx + 46, base - sh * 0.45)], color)
        c.rect(sx - 22, base - sh * 0.72, sx + 22, base - sh * 0.5, color)
        c.poly([(sx - 26, base - sh * 0.72), (sx, base - sh), (sx + 26, base - sh * 0.72)], color)
    if tower:
        tx, th = tower
        for lx in (-34, -12, 12, 34):
            c.line([(tx + lx * 0.6, base - th + 40), (tx + lx * 1.25, base)], color, 6)
        c.line([(tx - 40, base - th * 0.45), (tx + 40, base - th * 0.45)], color, 4)
        c.rect(tx - 58, base - th - 28, tx + 58, base - th + 44, color, r=14)
        c.ellipse(tx, base - th - 28, 58, 22, color)
        c.poly([(tx - 50, base - th - 38), (tx, base - th - 76), (tx + 50, base - th - 38)], color)
    for wx, wy in wins:
        c.rect(wx, wy, wx + 14, wy + 12, lit, a=0.9)
    return wins


# ============================================================================================ HUNTER'S MOON

SKY_DUSK = [(0, (9, 14, 40)), (380, (22, 28, 74)), (640, (48, 46, 108)), (800, (104, 80, 136)), (900, (170, 116, 148)),
            (955, (200, 138, 150)), (995, (160, 126, 156)), (1030, (132, 116, 152)), (1100, (132, 116, 152))]
SKY_DAY = [(0, (62, 110, 188)), (420, (98, 146, 206)), (760, (150, 180, 214)), (930, (206, 198, 206)),
           (990, (226, 206, 196)), (1100, (226, 206, 196))]
SKY_NIGHT = [(0, (3, 6, 20)), (500, (8, 14, 38)), (1100, (16, 26, 58)), (1500, (20, 30, 62)), (1920, (12, 18, 40))]


class Dusk:
    """Looking east across a lake at dusk: the full moon coming up behind the trees and rooftops of town."""

    MR = 160

    def __init__(self, y0=1100, y1=800, rise=(0.0, 4.9), mx=560, drift=6.0):
        self.y0, self.y1, self.rise, self.mx, self.drift = y0, y1, rise, mx, drift
        sky = grad(SKY_DUSK)
        art.stars_only(sky, 110, 4, 560, k=0.55)
        self.sky = sky
        self.moon, self.ma = moon_sprite(self.MR, warm=0.85, seed=3)
        self.halo = halo_sprite(self.MR, (255, 170, 110), s1=0.22, s2=0.5)
        # far shore: a treeline, then the town in front of it
        trees, _ = ridge_layer(1000, 26, 90, (34, 28, 60), 11, rim=(255, 170, 140), rim_a=0.18)
        c = Canvas(W, H)
        self.wins = town(c, 1080, seed=7, color="#120f26", steeple=(870, 250), tower=(190, 190))
        c.rect(0, 1078, W, 1090, "#120f26")
        townl = c.rgba()
        lay = trees.copy()
        lay[..., :3] = lay[..., :3] * (1 - townl[..., 3:4]) + townl[..., :3]
        lay[..., 3] = 1 - (1 - lay[..., 3]) * (1 - townl[..., 3])
        lay[1086:] = 0
        self.far = lay
        # the lake: the sky's colours, darker, with long ripples
        ly0, ly1 = 1086, H
        self.ly0 = ly0
        hh = ly1 - ly0
        rip = cv2.resize(fbm(hh // 2, W // 24, scale=6, octaves=4, seed=5), (W, hh), interpolation=cv2.INTER_CUBIC)
        k = np.linspace(0, 1, hh, dtype=np.float32)[:, None]
        top = np.array([118, 96, 140], np.float32) / 255
        bot = np.array([14, 14, 36], np.float32) / 255
        water = (top * (1 - k ** 0.5)[..., None] + bot * (k ** 0.5)[..., None]) * (0.86 + 0.26 * rip[..., None])
        self.water = water.astype(np.float32)
        self.rip = rip
        # near shore: reeds and grass in silhouette
        c2 = Canvas(W, H)
        c2.poly([(0, 1560), (240, 1530), (520, 1556), (800, 1520), (W, 1540), (W, H), (0, H)], "#05050c", smooth=False)
        art.reeds(c2, 1560, 0, 360, "#05050c", n=90, hmin=60, hmax=220, seed=3)
        art.reeds(c2, 1546, 760, W, "#05050c", n=70, hmin=50, hmax=190, seed=4)
        art.grass(c2, 1556, 0, W, "#05050c", n=420, hmin=12, hmax=50, seed=5)
        self.near = c2.rgba()
        yy = np.arange(hh, dtype=np.float32)
        self.ry = yy
        self.rnz = np.random.default_rng(9).uniform(0, 6.28, hh).astype(np.float32)

    def moon_y(self, t):
        a, b = self.rise
        return self.y0 + (self.y1 - self.y0) * ease_out((t - a) / (b - a)) if t < b else self.y1 - self.drift * (t - b)

    def render(self, t, u, zoom_k=0.0):
        out = self.sky.copy()
        my = self.moon_y(t)
        add_at(out, self.halo, self.mx, my, 1.0)
        over_at(out, self.moon, self.ma, self.mx, my)
        comp_layer(out, self.far)
        # water and the moon's broken reflection
        ly0 = self.ly0
        wat = self.water.copy()
        up = clamp01((1080 - (my + self.MR * 0.2)) / 160.0)            # how far the moon has cleared the trees
        if up > 0:
            yy = self.ry
            depth = yy / len(yy)
            width = self.MR * (0.55 + 0.9 * depth)
            wob = 14 * np.sin(yy * 0.045 + t * 1.7) + 8 * np.sin(yy * 0.13 - t * 2.3)
            xs = np.arange(W, dtype=np.float32)[None, :]
            col = np.exp(-((xs - self.mx - wob[:, None]) / width[:, None]) ** 2)
            streak = np.clip(np.sin(yy * 0.55 + self.rnz * 0.6 - t * 3.2) * 0.5 + 0.5, 0, 1) ** 2.2
            streak = streak[:, None] * (0.55 + 0.45 * self.rip)
            fade = (1 - depth * 0.75)[:, None]
            ref = (col * streak * fade * up)[..., None] * np.array([1.0, 0.72, 0.42], np.float32) * 0.85
            wat = wat + ref
        out[ly0:] = wat
        for wx, wy in self.wins:                                   # window lights, reflected
            add_spot(out, wx + 7, 1086 + (1086 - wy) * 0.35, 3.0, (1.0, 0.7, 0.35), 0.18)
        comp_layer(out, self.near)
        if zoom_k:
            out = zoom(out, 1 + zoom_k, self.mx, 900)
        return out


class DayEast:
    """Late afternoon, looking east-northeast: a pale moon just clearing the trees, in daylight."""

    def __init__(self, mx=540, y0=1000, y1=930, dur=6.2):
        self.mx, self.y0, self.y1, self.dur = mx, y0, y1, dur
        sky = grad(SKY_DAY)
        n = cv2.resize(fbm(H // 6, W // 20, scale=14, octaves=5, seed=12), (W, H), interpolation=cv2.INTER_CUBIC)
        yy = np.arange(H, dtype=np.float32)[:, None]
        wisps = smoothstep(0.6, 0.92, n) * smoothstep(250, 420, yy) * smoothstep(900, 700, yy)
        sky += (wisps * 0.09)[..., None] * np.array([1.0, 0.97, 0.95], np.float32)
        self.sky = sky
        self.moon, self.ma = moon_sprite(60, warm=0.15, seed=8, contrast=0.6)
        self.halo = halo_sprite(60, (255, 245, 235), s1=0.05, s2=0.12, reach=3)
        trees, _ = ridge_layer(985, 22, 70, (66, 74, 62), 21, rim=(255, 196, 120), rim_a=0.45, rim_w=4)
        fields = np.zeros((H, W, 4), np.float32)
        g = grad([(0, (58, 66, 52)), (1040, (58, 66, 52)), (1500, (34, 40, 34)), (1920, (20, 24, 22))])
        fields[1012:, :, :3] = g[1012:]
        fields[1012:, :, 3] = 1
        self.trees = trees
        self.fields = fields

    def render(self, t, u):
        out = self.sky.copy()
        my = self.y0 + (self.y1 - self.y0) * min(1.0, u / self.dur)
        add_at(out, self.halo, self.mx, my)
        over_at(out, self.moon, self.ma, self.mx, my, 0.92)
        comp_layer(out, self.trees)
        comp_layer(out, self.fields)
        return out


class NightHigh:
    """The moon high over town, with clouds drifting past (partly cloudy)."""

    MR = 175

    def __init__(self, mx=540, my=640, speed=46.0, dur=8.0):
        self.mx, self.my, self.speed = mx, my, speed
        sky = grad(SKY_NIGHT)
        art.stars_only(sky, 320, 6, 1300, k=0.8)
        self.moon, self.ma = moon_sprite(self.MR, warm=0.0, seed=4)
        halo = halo_sprite(self.MR, (190, 210, 255), s1=0.30, s2=0.5, reach=5)
        add_at(sky, halo, mx, my)
        self.sky = sky
        cw = W + int(speed * dur) + 40
        n = fbm(H // 3, cw // 3, scale=70, octaves=6, seed=17)
        n = cv2.resize(n, (cw, H), interpolation=cv2.INTER_CUBIC)
        yy = np.arange(H, dtype=np.float32)[:, None]
        band = smoothstep(640, 820, yy) * smoothstep(1330, 1080, yy)
        self.dens = (smoothstep(0.55, 0.82, n) * band * 0.85).astype(np.float32)
        xx = np.arange(W, dtype=np.float32)[None, :]
        dmoon = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2)
        disc = smoothstep(self.MR * 1.05, self.MR * 0.8, dmoon)
        self.lit = ((np.exp(-dmoon / 300.0) * 0.75 + 0.08) * (1 - 0.85 * disc)).astype(np.float32)
        trees, _ = ridge_layer(1600, 30, 80, (6, 8, 18), 31)
        c = Canvas(W, H)
        town(c, 1660, seed=12, color="#06070f", lit_p=0.5)
        tl = c.rgba()
        trees[..., :3] = trees[..., :3] * (1 - tl[..., 3:4]) + tl[..., :3]
        trees[..., 3] = 1 - (1 - trees[..., 3]) * (1 - tl[..., 3])
        self.ground = trees

    def render(self, t, u):
        out = self.sky.copy()
        over_at(out, self.moon, self.ma, self.mx, self.my)
        off = int(self.speed * u)
        d = self.dens[:, off:off + W]
        # clouds: dark bodies, silvered near the moon; thin enough to glow through
        body = np.array([0.10, 0.12, 0.20], np.float32)
        edge = d * (1 - d) * 4
        silver = (self.lit * (0.45 * edge + 0.18 * d))[..., None] * np.array([0.78, 0.82, 0.95], np.float32)
        a = (d * 0.7)[..., None]
        out = out * (1 - a) + body * a + silver
        comp_layer(out, self.ground)
        return out


def night_nomoon():
    """The Halloween videos' night background with no moon in the sky (it hasn't risen yet)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    k = (yy / H)[..., None]
    top, mid, bottom = (np.array(c, np.float32) for c in ((34, 14, 58), (22, 9, 38), (8, 4, 15)))
    img = np.where(k < 0.55, top * (1 - k / 0.55) + mid * (k / 0.55), mid * (1 - (k - 0.55) / 0.45) + bottom * ((k - 0.55) / 0.45))
    low = np.clip(1 - np.sqrt((xx - W * 0.5) ** 2 + ((yy - H * 0.86) * 1.4) ** 2) / 700, 0, 1) ** 2 * 0.22
    img = img * (1 - low[..., None]) + np.array((255, 120, 20), np.float32) * low[..., None]
    img = img + np.random.default_rng(7).normal(0, 2.0, (H, W, 1)).astype(np.float32)
    base = Image.fromarray(np.dstack([np.clip(img, 0, 255).astype(np.uint8), np.full((H, W), 255, np.uint8)]), "RGBA")
    hill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hill)
    pts = [(x, 1770 - 60 * math.sin(x / W * math.pi * 1.3 + 0.4) - 25 * math.sin(x / 90)) for x in range(0, W + 1, 12)]
    hd.polygon(pts + [(W, H), (0, H)], fill=(10, 5, 18))
    base.alpha_composite(hill)
    for x, y, s, _ in hw.PUMPKINS:
        base.alpha_composite(hw.pumpkin(s, face=False), (x, y))
    return base


def night_anim(frame, t):
    for x, y, r, ph, f in hw.STARS:
        a = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * f * t + ph))
        frame.alpha_composite(vr.with_alpha(hw.star_sprite(r), a), (x - r * 3, y - r * 3))
    for i, (x, y, s, ph) in enumerate(hw.PUMPKINS):
        a = 0.80 + 0.20 * math.sin(2 * math.pi * 1.7 * t + ph) * math.sin(2 * math.pi * 0.53 * t + 2 * ph)
        fc = hw.FACES[i]
        frame.alpha_composite(vr.with_alpha(fc, max(0.55, min(1.0, a))), (x - fc.info["pad"], y - fc.info["pad"]))


def phase_icon(size, lit=0.58, waning=True, color=(250, 236, 190)):
    """A gibbous (or crescent) moon icon: lit fraction `lit`, lit side on the left when waning."""
    S = 4
    n = size * S
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x, y = (xx - n / 2) / (n / 2 - S), (yy - n / 2) / (n / 2 - S)
    if waning:
        x = -x
    disc = (x * x + y * y) <= 1
    b = 2 * lit - 1                                   # terminator ellipse's half-width
    xt = b * np.sqrt(np.clip(1 - y * y, 0, 1))
    litm = disc & (x >= -xt)
    a = np.zeros((n, n, 4), np.uint8)
    a[disc] = (70, 62, 96, 255)
    a[litm] = color + (255,)
    im = Image.fromarray(a, "RGBA").resize((size, size), Image.LANCZOS)
    return im


def arrow_down(w=70, h=96, color=GOLDEN):
    S = 4
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((w * S * 0.36, 0, w * S * 0.64, h * S * 0.55), fill=color + (255,))
    d.polygon([(0, h * S * 0.5), (w * S, h * S * 0.5), (w * S * 0.5, h * S)], fill=color + (255,))
    return im.resize((w, h), Image.LANCZOS)


def moon_card(name, line, accent, art_img):
    return hw.card(name, line, accent, art_img)


def timeline_card():
    """Halloween evening, 5 PM to midnight: trick-or-treat, sunset, and the moon not up until 10:49."""
    w, h = CW + 20, 380
    p = panel(w, h, accent=(170, 140, 255))
    x0, x1 = 64, w - 64

    def X(hh):
        return x0 + (hh - 17) / 7 * (x1 - x0)
    ty = 250
    d = ImageDraw.Draw(p)
    d.rounded_rectangle((x0, ty - 7, x1, ty + 7), radius=7, fill=(92, 70, 130, 255))
    for hh in range(17, 25):
        x = X(hh)
        d.line((x, ty + 16, x, ty + 34), fill=FAINT + (255,), width=3)
        t = "12" if hh == 24 else str(hh - 12)
        lab = vr.text_img(t, "bold", 32, FAINT)
        p.alpha_composite(lab, (int(x - lab.width / 2), ty + 42))
    pm = vr.text_img("PM", "bold", 26, FAINT, tracking=2)
    p.alpha_composite(pm, (int(X(17) - pm.width / 2), ty + 84))
    return p, X, ty


def build_moon(R):
    t_hunt = R.at("the Hunter's Moon,")
    t_516 = R.at("5:16.")
    t_look = R.at("Look east-northeast.")
    t_sun = R.at("The sun")
    t_551 = R.at("5:51,")
    t_day = R.at("daylight.")
    t_full = R.at("It's officially")
    t_1112 = R.at("11:12")
    t_pc = R.at("partly cloudy.")
    t_hall = R.at("On Halloween,")
    t_1049 = R.at("10:49,")
    t_flash = R.at("bring a flashlight")
    t_tot = R.at("trick-or-treat.")
    c1 = (R.end("5:16.") + t_look) / 2
    c2 = (R.end("daylight.") + t_full) / 2
    c3 = (R.end("cloudy.") + t_hall) / 2
    c4 = (R.end("trick-or-treat.") + R.at("Double-tap")) / 2
    times_src = "Moon and sun times calculated for La Porte"

    def p_hook(ctx):
        ctx["s"] = Dusk(rise=(0.0, c1 + 0.2))
        ctx["lab"] = label("Full moon · Tonight, Oct. 25")
        big = vr.fit_line("HUNTER'S MOON", "black", 150, MOONGOLD, CW + 40, min_size=90)
        ctx["t1"] = vr.glow(big, (255, 120, 40), radius=30, strength=0.7)
        ctx["pill"] = vr.pill("Rises 5:16 PM over La Porte", "xbold", 50, (20, 12, 30), MOONGOLD + (255,),
                              padx=34, pady=18)

    def d_hook(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u, zoom_k=0.03 * min(1.0, u / 5))))
        f.alpha_composite(ctx["lab"], (X0, 330))
        k = ease_out(u / 0.6)
        paste(f, scaled(ctx["t1"], 1.06 - 0.06 * k), W / 2, 470)
        a = appear(t, t_516 - 0.1, 0.3)
        if a > 0:
            paste(f, scaled(ctx["pill"], 1.12 - 0.12 * a), W / 2, 590, a)

    def p_look(ctx):
        ctx["s"] = DayEast(dur=c2 - c1)
        ctx["lab"] = label("Where to look")
        ctx["cards"] = [moon_card("Moonrise 5:16 PM", "Low in the east-northeast", MOONGOLD, vr.icon("moon", 112)),
                        moon_card("Sunset 5:51 PM", "So it comes up in daylight", ORANGE, vr.icon("sun", 124))]
        ctx["arrow"] = arrow_down()
        ticks = Image.new("RGBA", (W, 130), (0, 0, 0, 0))
        dd = ImageDraw.Draw(ticks)
        for az in np.arange(22.5, 120, 11.25):
            x = 540 + (az - 69.4) * 12
            major = abs(az / 22.5 - round(az / 22.5)) < 1e-6
            dd.line((x, 0, x, 26 if major else 14), fill=(255, 255, 255, 230 if major else 150), width=4 if major else 3)
        for name, az in (("NE", 45), ("ENE", 67.5), ("E", 90)):
            x = 540 + (az - 69.4) * 12
            col = GOLDEN if name == "ENE" else CREAM
            tx = vr.text_img(name, "black", 48 if name == "ENE" else 40, col)
            ticks.alpha_composite(tx, (int(x - tx.width / 2), 38))
        ctx["ticks"] = ticks

    def d_look(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        for i, (card, at) in enumerate(zip(ctx["cards"], (t_look - 0.1, t_551 - 0.1))):
            a = appear(t, at, 0.3)
            if a > 0:
                f.alpha_composite(C.alpha(card, a), (int(X0 - 10 - 40 * (1 - a)), 404 + i * 196))
        a = appear(t, t_look + 0.15, 0.3)
        if a > 0:
            bob = 12 * math.sin((t - t_look) * 4.2)
            my = ctx["s"].y0 + (ctx["s"].y1 - ctx["s"].y0) * min(1.0, u / ctx["s"].dur)
            paste(f, ctx["arrow"], 540, my - 120 + bob, a)
        f.alpha_composite(C.alpha(ctx["ticks"], appear(u, 0.15, 0.4)), (0, 1022))
        bs.credit_line(f, times_src)

    def p_full(ctx):
        ctx["s"] = NightHigh(dur=c3 - c2 + 0.5)
        ctx["lab"] = label("Officially full")
        tm = vr.text_img("11:12 PM", "black", 190, CREAM)
        ctx["tm"] = vr.glow(tm, (40, 60, 140), radius=28, strength=0.9)
        ctx["sub"] = vr.glow(vr.text_img("Tonight · Sun., Oct. 25", "xbold", 48, LAV), (0, 0, 0), radius=16,
                             strength=0.9)
        ctx["pill"] = vr.pill("Tonight: Partly cloudy · Low 47°", "bold", 44, INK, (20, 34, 74, 245),
                              border=(150, 196, 255), icon=vr.icon("moon-cloud", 58), padx=28, pady=14)

    def d_full(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        a = appear(t, t_1112 - 0.1, 0.3)
        if a > 0:
            paste(f, scaled(ctx["tm"], 1.1 - 0.1 * a), W / 2, 975, a)
            paste(f, ctx["sub"], W / 2, 1090, appear(t, t_1112 + 0.35, 0.3))
        a2 = appear(t, t_pc - 0.1, 0.3)
        if a2 > 0:
            paste(f, scaled(ctx["pill"], 1.1 - 0.1 * a2), W / 2, 1205, a2)
        bs.credit_line(f, "Forecast: National Weather Service · Times calculated for La Porte")

    def p_hall(ctx):
        if not hw.FACES:
            hw.FACES[:] = [hw.face_layer(s) for _, _, s, _ in hw.PUMPKINS]
        ctx["bg"] = night_nomoon()
        ctx["lab"] = label("Halloween · Sat., Oct. 31")
        ctx["l2"] = vr.text_img("MOONRISE", "black", 64, LAV, tracking=6)
        tm = vr.text_img("10:49 PM", "black", 180, MOONGOLD)
        ctx["tm"] = vr.glow(tm, (255, 120, 0), radius=28, strength=0.6)
        ctx["card"], ctx["X"], ctx["ty"] = timeline_card()
        ctx["pk"] = hw.pumpkin(70, glow_face=True)
        ctx["sun"] = vr.icon("sun", 64)
        ctx["gib"] = phase_icon(78, 0.58)
        ctx["tot"] = vr.text_img("TRICK-OR-TREAT", "black", 30, (255, 200, 120), tracking=2)
        ctx["dark"] = vr.text_img("NO MOON YET", "black", 30, LAV, tracking=3)
        ctx["mr"] = vr.text_img("10:49", "xbold", 34, MOONGOLD)
        ctx["flash"] = vr.pill("Bring a flashlight", "xbold", 48, (16, 8, 26), MOONGOLD + (255,), padx=34, pady=18)

    def d_hall(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_anim(f, t)
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        paste(f, ctx["l2"], W / 2, 440, appear(t, t_hall + 0.1, 0.3))
        a = appear(t, t_1049 - 0.1, 0.3)
        if a > 0:
            paste(f, scaled(ctx["tm"], 1.1 - 0.1 * a), W / 2, 560, a)
        a = appear(u, 0.25, 0.35)
        if a <= 0:
            return
        card = ctx["card"].copy()
        X, ty = ctx["X"], ctx["ty"]
        d = ImageDraw.Draw(card)
        gk = ease_out((t - t_hall - 0.3) / 0.5) if t >= t_hall + 0.3 else 0.0
        if gk > 0:                                              # trick-or-treat, 5 to 7
            d.rounded_rectangle((X(17), ty - 13, X(17) + (X(19) - X(17)) * gk, ty + 13), radius=13,
                                fill=ORANGE + (255,))
            card.alpha_composite(C.alpha(ctx["pk"], gk), (int((X(17) + X(19)) / 2 - 35), ty - 118))
            card.alpha_composite(C.alpha(ctx["tot"], gk), (int((X(17) + X(19)) / 2 - ctx["tot"].width / 2), ty - 44))
        k2 = appear(t, t_1049 - 0.05, 0.35)                     # moonrise 10:49
        if k2 > 0:
            xm = X(22 + 49 / 60)
            card.alpha_composite(C.alpha(ctx["gib"], k2), (int(xm - 39), int(ty - 110 - 20 * (1 - k2))))
            card.alpha_composite(C.alpha(ctx["mr"], k2), (int(xm - ctx["mr"].width / 2), ty - 150))
            d.line((xm, ty - 26, xm, ty + 14), fill=MOONGOLD + (255,), width=4)
        k3 = appear(t, t_1049 + 0.4, 0.35)
        if k3 > 0:                                              # the dark stretch before it rises
            card.alpha_composite(C.alpha(ctx["dark"], k3), (int((X(19.2) + X(22.4)) / 2 - ctx["dark"].width / 2),
                                                             ty - 44))
        f.alpha_composite(C.alpha(card, a), (X0 - 10, int(690 + 30 * (1 - a))))
        a4 = appear(t, t_flash - 0.05, 0.3)
        if a4 > 0:
            paste(f, scaled(ctx["flash"], 1.12 - 0.12 * a4), W / 2, 1160, a4)
        bs.credit_line(f, times_src)

    def p_end(ctx):
        ctx["s"] = Dusk(y0=520, y1=520, rise=(0.0, 0.01), mx=540, drift=0.0)
        ctx["cta"] = C.DoubleTap("IF YOU'RE GOING OUT", "Moonrise 5:16 PM · look east-northeast", color1=MOONGOLD,
                                 glow1=(255, 120, 40), kind1="black", size1=96, y=520)
        ctx["url"] = vr.pill("laporteweathernow.com", "xbold", 52, (16, 8, 26), MOONGOLD + (255,), padx=38, pady=22)

    def d_end(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        ctx["cta"].draw(f, u)
        paste(f, ctx["url"], W / 2, 1190, appear(u, 0.9, 0.3))

    scenes = [C.Scene(0.0, c1, d_hook, p_hook), C.Scene(c1, c2, d_look, p_look), C.Scene(c2, c3, d_full, p_full),
              C.Scene(c3, c4, d_hall, p_hall), C.Scene(c4, R.dur + 1, d_end, p_end)]
    for sc in scenes:
        sc.flicker = 0.0
    atm = bs.Atmos(tint=(210, 204, 216), fog=0.03, vignette=0.4, grain=6, seed=8)
    film = C.Film(R, scenes, flashes=[], flicker=0.0, atmos=atm)

    import sfx as X
    owl = X.owl(seed=24)
    ev = [("whoosh", c1, 0.5), ("pop", t_516 - 0.1, 0.6), ("pop", t_look - 0.1, 0.55), ("pop", t_551 - 0.1, 0.55),
          ("whoosh", c2, 0.5), (owl, c2 + 0.5, 0.35, "bed"), ("pop", t_1112 - 0.1, 0.6), ("pop", t_pc - 0.1, 0.5),
          ("whoosh", c3, 0.5), ("pop", t_1049 - 0.08, 0.6), ("pop", t_flash - 0.05, 0.5), ("pop", c4 + 0.12, 0.9),
          ("pop", c4 + 0.42, 0.9), ("hit", c4 + 0.5, 0.5)]
    music = spooky_music(R.dur + 1, theremin=((0.1, 3.0, (69, 76, 74, 72)), (c4 + 0.2, 2.2, (74, 79, 76))))
    return film, ev, music, TITLES["moon"], 4.6


# ============================================================================================ INDIANA'S CANDY
# CandyStore.com's 2026 state rankings (projected Halloween sales; 18 years of sales data, recent years weighted
# more), as reported by NBC (Oct. 8, 2026) and BroBible (Oct. 5, 2026): Indiana NERDS Gummy Clusters, Illinois Sour
# Patch Kids, Michigan Starburst, Ohio Blow Pops, Kentucky Reese's Cups; U.S. top five M&M's, Sour Patch Kids,
# Skittles, Reese's Cups, NERDS Gummy Clusters; 12 states changed favorites, 7 of them from chocolate to non-chocolate.
# Candy is drawn generically (no packaging, logos or characters); brand names appear only as text.

import json  # noqa: E402

import skia  # noqa: E402
from core import paint, lin  # noqa: E402

GEO = os.path.join(C.ROOT, "dl", "geo")
PICKS = {"US-IN": ("INDIANA", ["NERDS", "Gummy", "Clusters"]), "US-IL": ("ILLINOIS", ["Sour Patch", "Kids"]),
         "US-MI": ("MICHIGAN", ["Starburst"]), "US-OH": ("OHIO", ["Blow Pops"]), "US-KY": ("KENTUCKY", ["Reese's Cups"])}
LABEL_AT = {"US-IN": (-86.28, 39.75), "US-IL": (-89.3, 40.05), "US-MI": (-84.7, 43.35), "US-OH": (-82.75, 40.2),
            "US-KY": (-85.1, 37.6)}
PINK = (255, 92, 170)
VIOLET = (150, 90, 255)
COSL = math.cos(math.radians(41.0))
CANDY_SRC = "Rankings: CandyStore.com, 2026 (sales data)"


class CandyMap:
    BOX = (-97.0, -75.0, 33.5, 49.5)

    def __init__(self):
        lon0, lon1, lat0, lat1 = self.BOX

        def rings_of(geom):
            polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
            out = []
            for poly in polys:
                for ring in poly:
                    a = np.array(ring, np.float64)
                    if a[:, 0].max() < lon0 or a[:, 0].min() > lon1 or a[:, 1].max() < lat0 or a[:, 1].min() > lat1:
                        continue
                    out.append(a)
            return out
        st = json.load(open(os.path.join(GEO, "ne_50m_admin_1_states_provinces_lakes.geojson")))
        self.shapes = []
        for ft in st["features"]:
            iso = ft["properties"].get("iso_3166_2") or ""
            if iso.startswith("US-") or iso.startswith("CA-"):
                rs = rings_of(ft["geometry"])
                if rs:
                    self.shapes.append((iso, rs))
        lk = json.load(open(os.path.join(GEO, "ne_50m_lakes.geojson")))
        self.lakes = []
        for ft in lk["features"]:
            if ft["properties"].get("name") in ("Lake Michigan", "Lake Huron", "Lake Erie", "Lake Saint Clair",
                                                "Lake Superior", "Lake Ontario"):
                self.lakes += rings_of(ft["geometry"])
        yy = np.arange(H, dtype=np.float32)
        self.fade = (smoothstep(380, 480, yy) * smoothstep(1310, 1230, yy)).astype(np.float32)
        self.labels = {}
        for iso, (name, lines) in PICKS.items():
            big = 40 if iso != "US-IN" else 34
            imgs = [vr.text_img(name, "bold", 22, (255, 226, 180), tracking=3)]
            imgs += [vr.text_img(t, "black", big, CREAM) for t in lines]
            w = max(i.width for i in imgs) + 24
            h = sum(i.height for i in imgs) + 6 * (len(imgs) - 1) + 16
            lab = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            y = 8
            for i in imgs:
                lab.alpha_composite(i, ((w - i.width) // 2, y))
                y += i.height + 6
            self.labels[iso] = vr.glow(lab, (20, 0, 30), radius=10, strength=1.0)

    @staticmethod
    def xy(view, lon, lat):
        lonc, latc, k, cx, cy = view
        return cx + (lon - lonc) * k * COSL, cy - (lat - latc) * k

    def path(self, view, rings):
        lonc, latc, k, cx, cy = view
        p = skia.Path()
        p.setFillType(skia.PathFillType.kEvenOdd)
        for a in rings:
            xs = cx + (a[:, 0] - lonc) * (k * COSL)
            ys = cy - (a[:, 1] - latc) * k
            p.addPoly([skia.Point(float(x), float(y)) for x, y in zip(xs, ys)], True)
        return p

    def render(self, view, lit, la_porte=1.0):
        """lit: {iso: 0..1} for the neighbours whose pick has been named."""
        c = Canvas(W, H)
        cv_ = c.c
        for a in self.lakes:
            pth = self.path(view, [a])
            cv_.drawPath(pth, paint("#0e1745", 0.95))
            cv_.drawPath(pth, paint("#3c4f9a", 0.8, stroke=2))
        hl = None
        for iso, rs in self.shapes:
            pth = self.path(view, rs)
            if iso == "US-IN":
                hl = pth
                continue
            k = lit.get(iso, 0.0)
            if iso.startswith("CA-"):
                fill, edge, ew = "#1e1033", "#4a3470", 1.5
            else:
                f0, f1 = np.array([42, 21, 70]), np.array([104, 50, 160])
                e0, e1 = np.array([96, 66, 140]), np.array([255, 196, 110])
                fill = "#%02x%02x%02x" % tuple(int(v) for v in f0 * (1 - k) + f1 * k)
                edge = "#%02x%02x%02x" % tuple(int(v) for v in e0 * (1 - k) + e1 * k)
                ew = 2 + 2 * k
            cv_.drawPath(pth, paint(fill, 0.96))
            cv_.drawPath(pth, paint(edge, 0.9, stroke=ew))
        if hl is not None:
            b = hl.getBounds()
            cv_.drawPath(hl, paint("#ff5caa", 0.55, blur=26))
            sh = lin((b.left(), b.top()), (b.right(), b.bottom()), ["#ff5caa", "#b05cff", "#7a4dff"])
            cv_.drawPath(hl, paint(None, 1.0, shader=sh))
            cv_.drawPath(hl, paint("#fff3e0", 0.95, stroke=4))
        if la_porte > 0:
            x, y = self.xy(view, -86.7225, 41.6106)
            cv_.drawCircle(x, y, 22, paint("#ffd648", 0.35 * la_porte, blur=10))
            cv_.drawCircle(x, y, 10, paint("#ffd648", la_porte))
            cv_.drawCircle(x, y, 10, paint("#1a0a26", la_porte, stroke=3))
        arr = c.surface.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType,
                                                    alphaType=skia.AlphaType.kUnpremul_AlphaType)
        arr = arr.copy()
        arr[..., 3] = (arr[..., 3].astype(np.float32) * self.fade[:, None]).astype(np.uint8)
        return Image.fromarray(arr, "RGBA")


def gummy_cluster(size, seed=1):
    """A generic gummy cluster: a lumpy ball of tiny crunchy candy pebbles."""
    S = 3
    n = size * S
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    cols = [(255, 92, 170), (170, 100, 255), (90, 200, 255), (255, 214, 72), (255, 140, 60), (255, 120, 200)]
    R = n * 0.40
    pts = []
    for _ in range(320):
        ang = r.uniform(0, 2 * math.pi)
        rad = R * math.sqrt(r.uniform(0, 1))
        x = n / 2 + rad * math.cos(ang)
        y = n / 2 + rad * math.sin(ang) * 0.92
        pts.append((y, x, r.integers(len(cols)), r.uniform(0.085, 0.13) * R, r.uniform(0, math.pi)))
    pts.sort()
    for y, x, ci, pr, rot in pts:
        col = cols[ci]
        rx, ry = pr * 1.15, pr * 0.85
        shade = 0.55 + 0.45 * (1 - (y - n / 2 + R) / (2 * R))
        dark = tuple(int(v * 0.55) for v in col)
        d.ellipse((x - rx, y - ry + pr * 0.18, x + rx, y + ry + pr * 0.18), fill=dark + (255,))
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=tuple(int(v * shade + 40 * (1 - shade)) for v in col) + (255,))
        d.ellipse((x - rx * 0.45, y - ry * 0.7, x - rx * 0.05, y - ry * 0.25), fill=(255, 255, 255, 150))
    im = im.resize((size, size), Image.LANCZOS)
    return im


def choc_bar(w=560, h=250):
    """A plain chocolate bar, half out of its foil (no brand)."""
    S = 3
    W_, H_ = w * S, h * S
    im = Image.new("RGBA", (W_ + 40 * S, H_ + 40 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = 20 * S, 20 * S
    d.rounded_rectangle((ox, oy, ox + W_, oy + H_), radius=22 * S, fill=(70, 38, 22, 255))
    cols, rows = 5, 2
    gw, gh = W_ / cols, H_ / rows
    for i in range(cols):
        for j in range(rows):
            x0, y0 = ox + i * gw + 10 * S, oy + j * gh + 10 * S
            x1, y1 = ox + (i + 1) * gw - 10 * S, oy + (j + 1) * gh - 10 * S
            d.rounded_rectangle((x0, y0, x1, y1), radius=10 * S, fill=(128, 76, 46, 255))
            d.rounded_rectangle((x0 + 12 * S, y0 + 12 * S, x1, y1), radius=10 * S, fill=(58, 30, 16, 255))
            d.rounded_rectangle((x0 + 12 * S, y0 + 12 * S, x1 - 12 * S, y1 - 12 * S), radius=8 * S,
                                fill=(98, 56, 32, 255))
    fx = ox + W_ * 0.56                                    # the foil over the right side, crinkled
    r = np.random.default_rng(3)
    pts = [(fx + r.uniform(-14, 14) * S, oy - 12 * S + k * (H_ + 24 * S) / 12) for k in range(13)]
    poly = pts + [(ox + W_ + 16 * S, oy + H_ + 12 * S), (ox + W_ + 16 * S, oy - 12 * S)]
    d.polygon(poly, fill=(196, 200, 210, 255))
    for k in range(9):
        x = fx + (k + 0.5) * (ox + W_ + 16 * S - fx) / 9 + r.uniform(-8, 8) * S
        d.line((x, oy - 10 * S, x + r.uniform(-30, 30) * S, oy + H_ + 10 * S),
               fill=(255, 255, 255, 120) if k % 2 else (130, 136, 150, 140), width=int(5 * S))
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    return im.rotate(8, expand=True, resample=Image.BICUBIC)


def rank_slot(n, w=CW + 20, h=124):
    p = panel(w, h, accent=(120, 96, 170), fill=(30, 13, 48, 200))
    d = ImageDraw.Draw(p)
    d.ellipse((24, (h - 84) // 2, 108, (h + 84) // 2), outline=GOLDEN + (200,), width=4)
    num = vr.text_img(str(n), "black", 56, GOLDEN)
    p.alpha_composite(num, (66 - num.width // 2, (h - num.height) // 2))
    d.rounded_rectangle((134, h // 2 - 8, w - 60, h // 2 + 8), radius=8, fill=(90, 66, 130, 160))
    return p


def rank_row(n, name, choc, w=CW + 20, h=124):
    p = panel(w, h, accent=GOLDEN if n == 1 else (170, 140, 255))
    d = ImageDraw.Draw(p)
    d.ellipse((24, (h - 84) // 2, 108, (h + 84) // 2), fill=GOLDEN + (255,))
    num = vr.text_img(str(n), "black", 56, (26, 10, 34))
    p.alpha_composite(num, (66 - num.width // 2, (h - num.height) // 2))
    tag = vr.pill("CHOCOLATE" if choc else "NOT CHOCOLATE", "bold", 24, CREAM if choc else (10, 30, 30),
                  (122, 72, 40, 255) if choc else (120, 230, 210, 255), padx=16, pady=8)
    nm = vr.fit_line(name, "xbold", 56, CREAM, w - 150 - tag.width - 40, min_size=36)
    p.alpha_composite(nm, (134, (h - nm.height) // 2))
    p.alpha_composite(tag, (w - tag.width - 26, (h - tag.height) // 2))
    return p


def build_candy(R):
    t_isnt = R.at("isn't chocolate.")
    t_nerds = R.at("It's NERDS")
    t_gummy = R.at("Gummy Clusters,")
    t_rank = R.at("CandyStore.com's")
    t_ill = R.at("Illinois picked")
    t_mich = R.at("Michigan went")
    t_ohio = R.at("Ohio chose")
    t_top = R.at("the top five")
    rows_t = [R.at("M&M's,"), R.at("Sour Patch", after=t_top), R.at("Skittles,"), R.at("Reese's"),
              R.at("NERDS Gummy", after=t_top)]
    t_agree = R.at("Agree?")
    t_dt = R.at("Double-tap,")
    c1 = (R.end("chocolate.") + t_nerds) / 2
    c2 = (R.end("rankings.") + R.at("Next door,")) / 2
    c3 = (R.end("Blow Pops.") + R.at("Across the")) / 2
    c4 = (R.end("Clusters.", after=t_top) + t_agree) / 2
    V_IN = (-86.45, 39.8, 135.0, 540.0, 952.0)
    V_ALL = (-86.0, 41.15, 80.0, 540.0, 840.0)

    def base(ctx):
        if not hw.FACES:
            hw.FACES[:] = [hw.face_layer(s) for _, _, s, _ in hw.PUMPKINS]
        ctx["bg"] = hw.night_base()

    def p_hook(ctx):
        base(ctx)
        ctx["lab"] = label("Halloween 2026 · Indiana")
        a = vr.fit_line("INDIANA'S #1", "black", 160, ORANGE, CW + 40, min_size=90)
        ctx["t1"] = vr.glow(a, (255, 110, 0), radius=30, strength=0.65)
        ctx["t2"] = vr.glow(vr.fit_line("HALLOWEEN CANDY", "black", 112, CREAM, CW + 20, min_size=70), (0, 0, 0),
                            radius=20, strength=0.8)
        ctx["bar"] = choc_bar(680, 300)
        ctx["stamp"] = bs.stamp([("NOT CHOCOLATE", 80)], color=(240, 56, 64))

    def d_hook(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_layers_bats(f, t)
        f.alpha_composite(ctx["lab"], (X0, 330))
        k = ease_out(u / 0.6)
        paste(f, scaled(ctx["t1"], 1.06 - 0.06 * k), W / 2, 470)
        paste(f, ctx["t2"], W / 2, 610)
        bob = 8 * math.sin(t * 2.0)
        sh = 0.0
        a = appear(t, t_isnt + 0.25, 0.18)
        if a > 0:
            sh = 10 * math.exp(-(t - t_isnt - 0.25) * 9) * math.sin((t - t_isnt) * 60)
        paste(f, ctx["bar"], W / 2 + sh, 975 + bob)
        if a > 0:
            paste(f, scaled(ctx["stamp"], 1.5 - 0.5 * a), W / 2, 975, a)

    def p_in(ctx):
        base(ctx)
        ctx["map"] = CandyMap()
        ctx["lab"] = label("Indiana · 2026 rankings")
        ctx["n1"] = vr.glow(vr.text_img("NERDS", "black", 176, (255, 120, 190)), (255, 40, 140), radius=32,
                            strength=0.7)
        ctx["n2"] = vr.glow(vr.fit_line("GUMMY CLUSTERS", "black", 92, CREAM, CW, min_size=60), (0, 0, 0), radius=18,
                            strength=0.8)
        ctx["g1"], ctx["g2"], ctx["g3"] = gummy_cluster(230, 1), gummy_cluster(170, 2), gummy_cluster(130, 3)
        ctx["lp"] = vr.glow(vr.text_img("La Porte", "xbold", 34, (255, 226, 150)), (20, 0, 30), radius=10,
                            strength=1.0)
        ctx["src"] = vr.glow(vr.text_img("in CandyStore.com's 2026 state rankings", "semi", 36, LAV), (0, 0, 0),
                             radius=12, strength=0.9)

    def d_in(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_anim_nobats(f, t)
        m = ctx["map"]
        a = appear(u, 0.0, 0.4)
        f.alpha_composite(C.alpha(m.render(V_IN, {}), a))
        x, y = m.xy(V_IN, -86.7225, 41.6106)
        paste(f, ctx["lp"], x + 24 + ctx["lp"].width / 2, y - 4, a)
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        a1 = appear(t, t_nerds + 0.2, 0.3)
        if a1 > 0:
            paste(f, scaled(ctx["n1"], 1.15 - 0.15 * a1), W / 2, 454, a1)
        a2 = appear(t, t_gummy - 0.05, 0.3)
        if a2 > 0:
            paste(f, ctx["n2"], W / 2, 562, a2)
            for g, gx, gy, ph in ((ctx["g1"], 170, 930, 0.0), (ctx["g2"], 905, 1010, 1.3), (ctx["g3"], 860, 800, 2.4)):
                bob = 10 * math.sin(t * 2.4 + ph)
                k = ease_out((t - t_gummy) / 0.4) if t > t_gummy else 0
                paste(f, scaled(g, 0.6 + 0.4 * k), gx, gy + bob, a2)
        a3 = appear(t, t_rank - 0.1, 0.3)
        if a3 > 0:
            paste(f, ctx["src"], W / 2, 622, a3)
        bs.credit_line(f, CANDY_SRC + " · Map: Natural Earth")

    def p_nb(ctx):
        base(ctx)
        ctx["map"] = CandyMap()
        ctx["lab"] = label("Next door")
        ctx["n1"] = vr.glow(vr.text_img("NERDS", "black", 176, (255, 120, 190)), (255, 40, 140), radius=32,
                            strength=0.7)
        ctx["n2"] = vr.glow(vr.fit_line("GUMMY CLUSTERS", "black", 92, CREAM, CW, min_size=60), (0, 0, 0), radius=18,
                            strength=0.8)

    def d_nb(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_anim_nobats(f, t)
        m = ctx["map"]
        z = ease(u / 0.9)
        view = tuple(a + (b - a) * z for a, b in zip(V_IN, V_ALL))
        lit = {"US-IL": appear(t, t_ill + 0.1, 0.35), "US-MI": appear(t, t_mich - 0.05, 0.35),
               "US-OH": appear(t, t_ohio - 0.05, 0.35), "US-KY": appear(t, t_ohio + 1.0, 0.35)}
        f.alpha_composite(m.render(view, lit, la_porte=1 - z))
        out = 1 - ease(u / 0.5)
        if out > 0:
            paste(f, ctx["n1"], W / 2, 454, out)
            paste(f, ctx["n2"], W / 2, 562, out)
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.3, 0.3)), (X0, 330))
        for iso in ("US-IN", "US-IL", "US-MI", "US-OH", "US-KY"):
            k = appear(u, 0.6, 0.3) if iso == "US-IN" else lit[iso]
            if k > 0:
                x, y = m.xy(view, *LABEL_AT[iso])
                paste(f, scaled(m.labels[iso], 1.12 - 0.12 * k), x, y, k)
        bs.credit_line(f, CANDY_SRC + " · Map: Natural Earth")

    def p_top(ctx):
        base(ctx)
        ctx["lab"] = label("America's top 5 · 2026")
        names = [("M&M's", True), ("Sour Patch Kids", False), ("Skittles", False), ("Reese's Cups", True),
                 ("NERDS Gummy Clusters", False)]
        ctx["rows"] = [rank_row(i + 1, n, ch) for i, (n, ch) in enumerate(names)]
        ctx["slots"] = [rank_slot(i + 1) for i in range(5)]
        ctx["note"] = vr.pill("This year, 7 states switched from chocolate", "bold", 36, INK, (20, 50, 60, 240),
                              border=(120, 230, 210), padx=26, pady=12)

    def d_top(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_anim_nobats(f, t)
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        for i, (row, slot, at) in enumerate(zip(ctx["rows"], ctx["slots"], rows_t)):
            s0 = appear(u, 0.05 + 0.08 * i, 0.25)
            a = appear(t, at - 0.12, 0.28)
            y = 405 + i * 140
            if s0 > 0 and a < 1:
                f.alpha_composite(C.alpha(slot, s0 * (1 - a)), (X0 - 10, y))
            if a > 0:
                paste(f, scaled(row, 1.06 - 0.06 * a), W / 2, y + row.height / 2, a)
        a = appear(t, rows_t[-1] + 0.9, 0.3)
        if a > 0:
            paste(f, ctx["note"], W / 2, 1150, a)
        bs.credit_line(f, CANDY_SRC)

    def p_end(ctx):
        base(ctx)
        ctx["agree"] = vr.glow(vr.text_img("AGREE?", "black", 190, CREAM), (255, 110, 0), radius=30, strength=0.6)
        ctx["cta"] = C.DoubleTap("AND TELL US", "the best candy to get in La Porte", color1=GOLDEN,
                                 glow1=(255, 120, 0), kind1="black", size1=110, y=520)

    def d_end(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_layers_bats(f, t)
        a = appear(t, t_agree - 0.08, 0.2) * (1 - ease((t - t_dt + 0.1) / 0.25))
        if a > 0:
            paste(f, scaled(ctx["agree"], 1.2 - 0.2 * min(1.0, a)), W / 2, 800, a)
        ctx["cta"].draw(f, t - (t_dt - 0.1))

    scenes = [C.Scene(0.0, c1, d_hook, p_hook), C.Scene(c1, c2, d_in, p_in), C.Scene(c2, c3, d_nb, p_nb),
              C.Scene(c3, c4, d_top, p_top), C.Scene(c4, R.dur + 1, d_end, p_end)]
    for sc in scenes:
        sc.flicker = 0.0
    atm = bs.Atmos(tint=(204, 198, 214), fog=0.04, vignette=0.42, grain=7, seed=8)
    film = C.Film(R, scenes, flashes=[], flicker=0.0, atmos=atm)
    ev = [("hit", t_isnt + 0.25, 0.8), ("whoosh", c1, 0.6), ("pop", t_nerds + 0.2, 0.7), ("pop", t_gummy, 0.6),
          ("pop", t_rank - 0.1, 0.4), ("whoosh", c2 + 0.1, 0.5), ("pop", t_ill + 0.1, 0.6), ("pop", t_mich - 0.05, 0.6),
          ("pop", t_ohio - 0.05, 0.6), ("pop", t_ohio + 1.0, 0.35), ("whoosh", c3, 0.6)]
    ev += [("pop", at - 0.12, 0.6) for at in rows_t]
    ev += [("pop", t_agree - 0.08, 0.7), ("pop", t_dt + 0.02, 0.9), ("pop", t_dt + 0.32, 0.9), ("hit", t_dt + 0.4, 0.5)]
    music = spooky_music(R.dur + 1, theremin=((0.1, 2.6, (69, 74, 72, 69)), (t_dt, 2.4, (74, 77, 74))))
    return film, ev, music, TITLES["candy"], 3.4


def night_layers_bats(f, t):
    hw.animate(f, t)


def night_anim_nobats(f, t):
    for x, y, r, ph, fr in hw.STARS:
        a = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * fr * t + ph))
        f.alpha_composite(vr.with_alpha(hw.star_sprite(r), a), (x - r * 3, y - r * 3))
    for i, (x, y, s, ph) in enumerate(hw.PUMPKINS):
        a = 0.80 + 0.20 * math.sin(2 * math.pi * 1.7 * t + ph) * math.sin(2 * math.pi * 0.53 * t + 2 * ph)
        fc = hw.FACES[i]
        f.alpha_composite(vr.with_alpha(fc, max(0.55, min(1.0, a))), (x - fc.info["pad"], y - fc.info["pad"]))


# ============================================================================================ CLOCKS FALL BACK
# Daylight saving time ends Sun. Nov. 1, 2026 at 2 AM (the first Sunday in November); La Porte County keeps Central
# time. Sun times (PyEphem, La Porte, rounded to the minute): sunset Oct. 31 5:43 PM CDT, Nov. 1 4:41 PM CST,
# Dec. 1 4:17 PM; the year's earliest is around Dec. 8 (4:16:31, so 4:17). Sunrise Oct. 31 7:18 AM CDT, Nov. 1
# 6:19 AM CST.

import datetime as _dt  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

SKY_EVE = [(0, (12, 14, 42)), (520, (34, 30, 86)), (980, (88, 48, 116)), (1300, (176, 80, 100)),
           (1520, (248, 138, 82)), (1640, (255, 184, 112)), (1920, (255, 184, 112))]
SUNSET_SRC = "Sun times calculated for La Porte (Central time)"


def sun_times(d0, d1):
    """[(date, sunset as local clock hours)] for La Porte."""
    import ephem
    CT = ZoneInfo("America/Chicago")
    out = []
    d = d0
    while d <= d1:
        start = _dt.datetime(d.year, d.month, d.day, tzinfo=CT).astimezone(_dt.timezone.utc).replace(tzinfo=None)
        o = ephem.Observer()
        o.lat, o.lon, o.pressure, o.horizon = "41.6106", "-86.7225", 0, "-0:34"
        o.date = ephem.Date(start)
        s = o.next_setting(ephem.Sun()).datetime().replace(tzinfo=_dt.timezone.utc).astimezone(CT)
        out.append((d, s.hour + s.minute / 60 + s.second / 3600))
        d += _dt.timedelta(days=1)
    return out


def sun_sprite(r):
    n = 2 * r + 6
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.sqrt((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / r
    a = smoothstep(1.0, 1.0 - 2.0 / r, d).astype(np.float32)
    v = clamp01((yy - n / 2) / r * 0.5 + 0.5)[..., None]
    col = np.array([1.0, 0.92, 0.66], np.float32) * (1 - v) + np.array([1.0, 0.62, 0.30], np.float32) * v
    return (col * (1 - 0.08 * d[..., None] ** 2)).astype(np.float32), a


class Evening:
    """Dusk over La Porte's rooftops; the sun slips under the horizon as the reel goes."""

    def __init__(self, total):
        sky = grad(SKY_EVE)
        art.stars_only(sky, 140, 14, 700, k=0.5)
        self.sky = sky
        self.total = total
        self.sun, self.sa = sun_sprite(120)
        self.halo = halo_sprite(120, (255, 150, 70), s1=0.30, s2=0.55, reach=5)
        lay, _ = ridge_layer(1640, 20, 80, (26, 12, 32), 41)
        c = Canvas(W, H)
        town(c, 1700, seed=21, color="#160b1e", steeple=(820, 230), tower=(230, 170), lit_p=0.5)
        c.rect(0, 1698, W, H, "#160b1e")
        tl = c.rgba()
        lay[..., :3] = lay[..., :3] * (1 - tl[..., 3:4]) + tl[..., :3]
        lay[..., 3] = 1 - (1 - lay[..., 3]) * (1 - tl[..., 3])
        self.fg = lay

    def render(self, t):
        out = self.sky.copy()
        y = 1590 + 130 * min(1.0, t / self.total)
        add_at(out, self.halo, 540, y)
        over_at(out, self.sun, self.sa, 540, y)
        comp_layer(out, self.fg)
        return out


class Clock:
    """An analog wall clock; draw(hours) puts the hands at that time (2.0 -> 1.0 runs the minute hand backward)."""

    INKP = (40, 17, 64, 255)

    def __init__(self, r):
        self.r, self.S = r, 2
        R = r * self.S
        self.n = n = int(2 * r * 1.1) * self.S
        face = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        d = ImageDraw.Draw(face)
        c = n / 2
        d.ellipse((c - R * 1.07, c - R * 1.07, c + R * 1.07, c + R * 1.07), fill=(255, 138, 0, 255))
        d.ellipse((c - R * 1.02, c - R * 1.02, c + R * 1.02, c + R * 1.02), fill=self.INKP)
        d.ellipse((c - R, c - R, c + R, c + R), fill=(255, 243, 224, 255))
        for k in range(60):
            a = 2 * math.pi * k / 60
            major = k % 5 == 0
            r0, r1 = R * (0.80 if major else 0.87), R * 0.93
            d.line((c + r0 * math.sin(a), c - r0 * math.cos(a), c + r1 * math.sin(a), c - r1 * math.cos(a)),
                   fill=self.INKP, width=max(2, int(R * (0.03 if major else 0.012))))
        fnt = vr.font("black", int(R * 0.19))
        for h in range(1, 13):
            a = 2 * math.pi * h / 12
            d.text((c + R * 0.645 * math.sin(a), c - R * 0.645 * math.cos(a)), str(h), font=fnt, fill=self.INKP,
                   anchor="mm")
        self.face = face

    def draw(self, hours):
        im = self.face.copy()
        d = ImageDraw.Draw(im)
        c, R = self.n / 2, self.r * self.S

        def hand(a, length, width):
            x, y = c + length * math.sin(a), c - length * math.cos(a)
            xb, yb = c - length * 0.16 * math.sin(a), c + length * 0.16 * math.cos(a)
            d.line((xb, yb, x, y), fill=self.INKP, width=int(width))
            d.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=self.INKP)
        hand(2 * math.pi * (hours % 12) / 12, R * 0.48, R * 0.075)
        hand(2 * math.pi * (hours % 1), R * 0.75, R * 0.048)
        d.ellipse((c - R * 0.075, c - R * 0.075, c + R * 0.075, c + R * 0.075), fill=(255, 138, 0, 255))
        return im.resize((self.n // self.S, self.n // self.S), Image.LANCZOS)


def back_arrow(r, width=16, color=GOLDEN):
    """A curved arrow running counter-clockwise from 12 to 9 o'clock, around a clock of radius r."""
    S = 3
    n = int(2 * (r + width * 3)) * S
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n / 2
    R = r * S
    d.arc((c - R, c - R, c + R, c + R), 180, 300, fill=color + (255,), width=width * S)
    x, y = c - R, c + 0.0
    h = width * S * 2.4
    d.polygon([(x - h * 0.75, y - h * 0.1), (x + h * 0.75, y - h * 0.1), (x, y + h * 0.95)], fill=color + (255,))
    return im.resize((n // S, n // S), Image.LANCZOS)


def fmt_clock(hh):
    h = int(hh)
    m = int(round((hh - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return "%d:%02d" % (h - 12 if h > 12 else h, m)


def sunset_chart(data, w=CW + 20, h=700):
    """Panel + plot geometry for the sunset line (local clock time, 4 to 6 PM)."""
    p = panel(w, h, accent=(255, 150, 80), fill=(34, 16, 52, 232))
    d = ImageDraw.Draw(p)
    x0, x1, y0, y1 = 120, w - 50, 70, h - 120
    n = len(data) - 1

    def X(i):
        return x0 + (x1 - x0) * i / n

    def Y(hh):
        return y1 - (y1 - y0) * (hh - 16.0) / 2.0
    for hh, lab_ in ((16.0, "4 PM"), (17.0, "5 PM"), (18.0, "6 PM")):
        d.line((x0, Y(hh), x1, Y(hh)), fill=(120, 96, 170, 140), width=2)
        t = vr.text_img(lab_, "bold", 30, FAINT)
        p.alpha_composite(t, (x0 - 18 - t.width, int(Y(hh) - t.height / 2)))
    for i, (day, _) in enumerate(data):
        if (day.month, day.day) in ((10, 25), (11, 1), (12, 1), (12, 31)):
            d.line((X(i), y1 + 6, X(i), y1 + 22), fill=FAINT + (255,), width=3)
            if (day.month, day.day) == (10, 25):
                continue
            t = vr.text_img(day.strftime("%b. %-d").upper().replace("OCT.", "OCT.").replace("DEC.", "DEC."),
                            "bold", 28, FAINT)
            tx = min(max(X(i) - t.width / 2, 20), w - t.width - 16)
            p.alpha_composite(t, (int(tx), y1 + 30))
    pts = [(X(i), Y(hh)) for i, (_, hh) in enumerate(data)]
    return p, pts, X, Y


def build_dst(R):
    t_week = R.at("One week")
    t_jump = R.at("jump an hour")
    t_dst = R.at("Daylight saving")
    t_2am = R.at("2 AM")
    t_set = R.at("set your clocks")
    t_sat = R.at("Saturday night.")
    t_hal = R.at("Halloween's sunset")
    t_543 = R.at("5:43.")
    t_next = R.at("The next night,")
    t_441 = R.at("4:41.")
    t_keeps = R.at("keeps sliding,")
    t_417 = R.at("4:17")
    t_love = R.at("Love it")
    t_dt = R.at("Double-tap")
    c1 = (R.end("earlier.") + t_dst) / 2
    c2 = (R.end("night.", after=t_dst) + t_hal) / 2
    c3 = (R.end("4:41.") + R.at("And it")) / 2
    c4 = (R.end("December.") + t_love) / 2
    data = sun_times(_dt.date(2026, 10, 25), _dt.date(2026, 12, 31))
    ev_bg = {"bg": None}

    def bg(f, t):
        if ev_bg["bg"] is None:
            ev_bg["bg"] = Evening(R.dur)
        f.alpha_composite(to_pil(ev_bg["bg"].render(t)))

    def p_hook(ctx):
        ctx["lab"] = label("One week from today · Sun., Nov. 1")
        a = vr.fit_line("CLOCKS FALL BACK", "black", 132, GOLDEN, CW + 40, min_size=80)
        ctx["t1"] = vr.glow(a, (255, 110, 0), radius=30, strength=0.65)
        ctx["t2"] = vr.glow(vr.fit_line("Sunsets jump an hour earlier", "xbold", 58, CREAM, CW, min_size=40),
                            (0, 0, 0), radius=16, strength=0.9)
        ctx["clock"] = Clock(235)
        ctx["arrow"] = back_arrow(292)

    def d_hook(f, u, t, ctx):
        bg(f, t)
        f.alpha_composite(ctx["lab"], (X0, 330))
        k = ease_out(u / 0.6)
        paste(f, scaled(ctx["t1"], 1.06 - 0.06 * k), W / 2, 465)
        paste(f, ctx["t2"], W / 2, 572, appear(t, t_jump - 0.2, 0.3))
        hrs = 2.0 - ease((t - 0.35) / 2.9)
        paste(f, ctx["clock"].draw(hrs), W / 2, 935)
        sp = 1.0 if t < 3.3 else max(0.0, 1 - (t - 3.3) / 0.4)
        if sp > 0:
            paste(f, ctx["arrow"], W / 2, 935, 0.9 * sp)

    def p_ends(ctx):
        ctx["lab"] = label("Daylight saving time ends")
        box = Image.new("RGBA", (CW + 20, 260), (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle((0, 0, CW + 19, 259), radius=34, fill=(20, 10, 34, 236),
                                              outline=GOLDEN + (170,), width=3)
        ctx["box"] = box
        ctx["day"] = vr.text_img("SUN., NOV. 1", "bold", 34, FAINT, tracking=4)
        ctx["t2"] = vr.text_img("2:00 AM", "black", 150, CREAM)
        ctx["t1"] = vr.text_img("1:00 AM", "black", 150, GOLDEN)
        ctx["c1"] = hw.card("Fall back Saturday night", "That's Halloween: do it before bed", ORANGE,
                            vr.icon("moon", 112))
        ctx["c2"] = hw.card("Phones change on their own", "Reset the oven and microwave clocks", (170, 140, 255),
                            Clock(50).draw(1.0))

    def d_ends(f, u, t, ctx):
        bg(f, t)
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        a = appear(u, 0.05, 0.35)
        if a <= 0:
            return
        box = ctx["box"].copy()
        box.alpha_composite(ctx["day"], ((box.width - ctx["day"].width) // 2, 26))
        k = ease_out((t - t_set - 0.2) / 0.45) if t > t_set + 0.2 else 0.0      # the flip: 2:00 rolls up to 1:00
        top = 70
        clip = Image.new("RGBA", box.size, (0, 0, 0, 0))
        y2 = top - int(150 * k)
        y1 = top + int(150 * (1 - k))
        if k < 1:
            clip.alpha_composite(C.alpha(ctx["t2"], 1 - k), ((box.width - ctx["t2"].width) // 2, max(-200, y2)))
        if k > 0:
            clip.alpha_composite(C.alpha(ctx["t1"], k), ((box.width - ctx["t1"].width) // 2, y1))
        m = Image.new("L", box.size, 0)
        ImageDraw.Draw(m).rectangle((0, 64, box.width, box.height - 8), fill=255)
        clip.putalpha(Image.fromarray(np.minimum(np.asarray(clip.getchannel("A")), np.asarray(m)), "L"))
        box.alpha_composite(clip)
        f.alpha_composite(C.alpha(box, a), (X0 - 10, 410))
        for card, at, y in ((ctx["c1"], t_sat - 0.15, 700), (ctx["c2"], t_sat + 0.55, 892)):
            a2 = appear(t, at, 0.3)
            if a2 > 0:
                f.alpha_composite(C.alpha(card, a2), (int(X0 - 10 - 40 * (1 - a2)), y))

    def p_sun(ctx):
        ctx["lab"] = label("Sunset in La Porte")
        ctx["d1"] = vr.text_img("HALLOWEEN · SAT., OCT. 31", "bold", 36, LAV, tracking=3)
        ctx["s1"] = vr.glow(vr.text_img("5:43 PM", "black", 176, GOLDEN), (255, 110, 0), radius=26, strength=0.5)
        ctx["d2"] = vr.text_img("SUN., NOV. 1", "bold", 36, LAV, tracking=3)
        ctx["s2"] = vr.glow(vr.text_img("4:41 PM", "black", 176, (255, 128, 80)), (255, 60, 0), radius=26,
                            strength=0.5)
        ctx["drop"] = vr.pill("1 hour earlier", "xbold", 44, (20, 10, 30), (255, 150, 80, 255),
                              icon=arrow_down(34, 46, (20, 10, 30)), padx=28, pady=14)
        ctx["rise"] = vr.pill("Sunrise comes earlier too: 7:18 to 6:19 AM", "bold", 38, INK, (20, 10, 34, 236),
                              border=(255, 186, 70), icon=vr.icon("sun", 48), padx=24, pady=12)

    def d_sun(f, u, t, ctx):
        bg(f, t)
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        a = appear(t, t_hal - 0.1, 0.3)
        paste(f, ctx["d1"], W / 2, 440, a)
        a = appear(t, t_543 - 0.1, 0.3)
        if a > 0:
            paste(f, scaled(ctx["s1"], 1.1 - 0.1 * a), W / 2, 545, a)
        a = appear(t, t_next - 0.05, 0.3)
        if a > 0:
            paste(f, ctx["drop"], W / 2, 690 + 14 * (1 - a), a)
            paste(f, ctx["d2"], W / 2, 800, a)
        a = appear(t, t_441 - 0.1, 0.3)
        if a > 0:
            paste(f, scaled(ctx["s2"], 1.1 - 0.1 * a), W / 2, 905, a)
        a = appear(t, t_441 + 0.6, 0.3)
        if a > 0:
            paste(f, ctx["rise"], W / 2, 1090, a)
        bs.credit_line(f, SUNSET_SRC)

    def p_chart(ctx):
        ctx["lab"] = label("Sunset, Oct. 25 to Dec. 31")
        ctx["panel"], ctx["pts"], ctx["X"], ctx["Y"] = sunset_chart(data)
        i_n1 = [i for i, (d, _) in enumerate(data) if (d.month, d.day) == (11, 1)][0]
        i_min = min(range(len(data)), key=lambda i: data[i][1])
        ctx["i"] = (i_n1, i_min)
        ctx["l543"] = vr.text_img("5:43", "xbold", 34, GOLDEN)
        ctx["l441"] = vr.text_img("4:41", "xbold", 34, (255, 150, 100))
        ctx["fb"] = vr.text_img("CLOCKS FALL BACK", "bold", 24, FAINT, tracking=2)
        ctx["l417"] = vr.glow(vr.text_img("4:17 PM", "black", 56, CREAM), (255, 90, 0), radius=16, strength=0.6)
        ctx["earl"] = vr.text_img("EARLIEST, AROUND DEC. 8", "bold", 26, (255, 200, 150), tracking=2)

    def d_chart(f, u, t, ctx):
        bg(f, t)
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        a = appear(u, 0.05, 0.35)
        if a <= 0:
            return
        p = ctx["panel"].copy()
        d = ImageDraw.Draw(p)
        pts = ctx["pts"]
        i_n1, i_min = ctx["i"]
        k1 = ease_out(u / 0.6)                                   # Oct. 25 to Nov. 1 (with the jump) first
        k2 = ease((t - t_keeps + 0.1) / (t_417 - t_keeps + 0.6)) if t > t_keeps - 0.1 else 0.0
        upto = int(i_n1 * k1) if k2 <= 0 else i_n1 + int((len(pts) - 1 - i_n1) * k2)
        seg1 = pts[:min(upto, i_n1 - 1) + 1]
        if len(seg1) > 1:
            d.line(seg1, fill=GOLDEN + (255,), width=8, joint="curve")
        if upto >= i_n1 - 1 and k1 > 0.95:
            xa, ya = pts[i_n1 - 1]
            xb, yb = pts[i_n1]
            for yy in np.arange(ya, yb, 18):                     # the jump, dashed
                d.line((xb, yy, xb, min(yb, yy + 9)), fill=(255, 150, 100, 255), width=5)
            p.alpha_composite(ctx["l543"], (int(xb + 14), int(ya - 24)))
            p.alpha_composite(ctx["l441"], (int(xb - ctx["l441"].width - 14), int(yb - 24)))
            p.alpha_composite(ctx["fb"], (int(xb + 16), int((ya + yb) / 2 - 14)))
        if upto > i_n1:
            seg2 = pts[i_n1:upto + 1]
            d.line(seg2, fill=(255, 150, 100, 255), width=8, joint="curve")
        a3 = appear(t, t_417 - 0.1, 0.3)
        if a3 > 0 and upto >= i_min:
            x, y = pts[i_min]
            d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=CREAM + (255,), outline=(255, 90, 0, 255), width=4)
            p.alpha_composite(C.alpha(ctx["l417"], a3), (int(x - ctx["l417"].width / 2), int(y - 236)))
            p.alpha_composite(C.alpha(ctx["earl"], a3), (int(x - ctx["earl"].width / 2), int(y - 118)))
            for yy in np.arange(y - 76, y - 18, 16):
                d.line((x, yy, x, yy + 8), fill=(255, 200, 150, 200), width=3)
        f.alpha_composite(C.alpha(p, a), (X0 - 10, 410))
        bs.credit_line(f, SUNSET_SRC)

    def p_end(ctx):
        ctx["l1"] = vr.glow(vr.text_img("LOVE IT", "black", 170, CREAM), (255, 110, 0), radius=28, strength=0.6)
        ctx["l2"] = vr.glow(vr.text_img("OR HATE IT?", "black", 150, GOLDEN), (255, 110, 0), radius=28, strength=0.6)
        ctx["cta"] = C.DoubleTap("IF YOU'LL TAKE IT", "the extra hour of sleep, Saturday night", color1=GOLDEN,
                                 glow1=(255, 120, 0), kind1="black", size1=104, y=520)

    def d_end(f, u, t, ctx):
        bg(f, t)
        a = appear(t, t_love - 0.08, 0.25) * (1 - ease((t - t_dt + 0.1) / 0.25))
        if a > 0:
            paste(f, scaled(ctx["l1"], 1.15 - 0.15 * min(1.0, a)), W / 2, 700, a)
            paste(f, scaled(ctx["l2"], 1.15 - 0.15 * min(1.0, a)), W / 2, 880, a)
        ctx["cta"].draw(f, t - (t_dt - 0.1))

    scenes = [C.Scene(0.0, c1, d_hook, p_hook), C.Scene(c1, c2, d_ends, p_ends), C.Scene(c2, c3, d_sun, p_sun),
              C.Scene(c3, c4, d_chart, p_chart), C.Scene(c4, R.dur + 1, d_end, p_end)]
    for sc in scenes:
        sc.flicker = 0.0
    atm = bs.Atmos(tint=(214, 206, 214), fog=0.03, vignette=0.38, grain=6, seed=8)
    film = C.Film(R, scenes, flashes=[], flicker=0.0, atmos=atm)
    import sfx as X
    ticks = X.clock_ticks(3.2, seed=8, rate=6.0)
    ticks2 = X.clock_ticks(1.2, seed=9, rate=2.0)
    ev = [(ticks * 0.9, 0.3, 0.8, "hits"), ("whoosh", c1, 0.5), ("pop", t_2am - 0.1, 0.45), (ticks2, t_set + 0.1, 0.6, "hits"),
          ("whoosh", t_set + 0.2, 0.35), ("pop", t_sat - 0.15, 0.55), ("pop", t_sat + 0.55, 0.5), ("whoosh", c2, 0.5),
          ("pop", t_543 - 0.1, 0.6), ("pop", t_441 - 0.1, 0.6), ("pop", t_441 + 0.6, 0.4), ("whoosh", c3, 0.5),
          ("pop", t_417 - 0.1, 0.6), ("pop", t_love - 0.08, 0.7), ("pop", t_dt + 0.02, 0.9), ("pop", t_dt + 0.32, 0.9),
          ("hit", t_dt + 0.4, 0.5)]
    music = music_box_bed(R.dur + 1)
    return film, ev, music, TITLES["dst"], 3.6


def music_box_bed(seconds, bpm=100):
    """A brighter cousin of the Halloween music box: I-V-vi-IV in C, pad, arpeggio and a soft bass."""
    n = int(seconds * SR)
    out = np.zeros(n, np.float32)
    beat = 60 / bpm
    bar = 4 * beat
    chords = [(48, "M"), (43, "M"), (45, "m"), (41, "M")] * 4

    def add(sig, start):
        i = int(start * SR)
        if i >= n:
            return
        j = min(n, i + len(sig))
        out[i:j] += sig[:j - i]

    def env(length, attack, release):
        m = int(length * SR)
        e = np.ones(m, np.float32)
        a_, r_ = min(m, max(1, int(attack * SR))), min(m, max(1, int(release * SR)))
        e[:a_] = np.linspace(0, 1, a_)
        e[-r_:] *= np.linspace(1, 0, r_)
        return e
    for b, (root, kind) in enumerate(chords):
        start = b * bar
        if start >= seconds:
            break
        length = min(bar + 0.45, seconds - start)
        tt = np.arange(int(length * SR)) / SR
        third = 3 if kind == "m" else 4
        pad = np.zeros_like(tt, dtype=np.float32)
        for semis in (0, third, 7, 12):
            fq = hw.hz(root + 12 + semis)
            for det in (-0.0015, 0.0015):
                ph = 2 * np.pi * fq * (1 + det) * tt
                pad += (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)).astype(np.float32)
        add(pad * env(length, 0.25, 0.5) * 0.022, start)
        up = [0, 7, 12, third + 12, 7, 12, third + 12, 19]
        for k, semis in enumerate(up):
            ts = start + k * beat / 2
            if ts >= seconds:
                break
            tt2 = np.arange(int(0.9 * SR)) / SR
            fq = hw.hz(root + 24 + semis)
            tone = np.sin(2 * np.pi * fq * tt2) + 0.22 * np.sin(2 * np.pi * 2 * fq * tt2) + 0.1 * np.sin(
                2 * np.pi * 2.76 * fq * tt2)
            add((tone * np.exp(-tt2 / 0.3) * np.minimum(1, tt2 / 0.004) * 0.1).astype(np.float32), ts)
        for k in (0, 2):
            ts = start + k * beat
            tt3 = np.arange(int(0.6 * SR)) / SR
            fq = hw.hz(root - 12)
            add((np.sin(2 * np.pi * fq * tt3) * np.exp(-tt3 / 0.22) * np.minimum(1, tt3 / 0.006) * 0.3).astype(
                np.float32), ts)
    fade = int(0.8 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(out * 1.4) / np.tanh(1.4)
    return out / max(1e-6, float(np.max(np.abs(out)))) * 0.89


BUILDERS = {"moon": build_moon, "candy": build_candy, "dst": build_dst}


def main(name, mode, times=None):
    R = C.Reel(name)
    film, ev, music, title, cover_t = BUILDERS[name](R)
    if mode == "stills":
        ts = times or [0.0, 1.5, 3.5, 4.8, 6.0, 8.0, 10.5, 12.5, 14.5, 16.0, 17.5, 19.0, 21.0, 22.6, 23.6]
        print(film.stills([t for t in ts if t < R.dur], name))
        return
    vid = os.path.join(C.OUT, "_%s_video.mp4" % name)
    film.video(vid, cover_t=cover_t)
    mix = C.soundtrack(R, music, ev, music_gain=0.45)
    out = os.path.join(C.OUT, OUTFILES[name])
    C.finish(R, vid, mix, out, title)
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None)
