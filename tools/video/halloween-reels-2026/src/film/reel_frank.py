"""Frankenstein, Dracula and the Year Without a Summer: a Facebook reel (Oct. 22, 2026).

    python3 reel_frank.py stills|video

Facts: Mount Tambora (Sumbawa, Indonesia) erupted in April 1815; 1816 was the "Year Without a Summer". In June 1816
Lord Byron (28), Mary Godwin, soon Mary Shelley (18), Percy Shelley and John Polidori (20) were kept indoors by the
weather at the Villa Diodati on Lake Geneva, and Byron proposed that each write a ghost story. Mary's became
Frankenstein (1818); Polidori's The Vampyre (1819) started the vampire craze that led to Dracula (1897).
Everything is drawn here; the two title pages are re-set from the 1818 and 1819 editions (public domain).
"""
import math
import os
import sys

import cv2
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFilter

import reels_common as C
from reels_common import bs, vr, hw, W, H, SR, T, fitT, glow, paste, scaled, appear, ease, ease_out, dim, BONE, \
    SEPIA, INKC, RED
from core import fbm, add_spot, Canvas, smooth_path, paint, lin, rad, light_map
import art

ICE = (214, 232, 250)


def to_pil(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB").convert("RGBA")


def vgrad(stops):
    return art.vgrad(H, W, stops)


def zoom(img, z, cx=W / 2, cy=H / 2):
    """Scale a float frame about (cx, cy) and crop back to W x H."""
    if abs(z - 1) < 1e-4:
        return img
    M = np.array([[z, 0, cx * (1 - z)], [0, z, cy * (1 - z)]], np.float32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


class Rain:
    def __init__(self, n, box, seed=1, speed=2300, length=56, slant=0.2, a=(0.10, 0.28)):
        r = np.random.default_rng(seed)
        self.box = box
        x0, y0, x1, y1 = box
        self.x = r.uniform(x0 - 150, x1 + 50, n)
        self.y = r.uniform(y0, y1, n)
        self.v = r.uniform(0.8, 1.2, n) * speed
        self.a = r.uniform(*a, n)
        self.L, self.slant = length, slant

    def draw(self, frame, t, k=1.0, color=(0.75, 0.82, 0.9), mask=None):
        x0, y0, x1, y1 = self.box
        lay = np.zeros(frame.shape[:2], np.float32)
        h = y1 - y0
        for i in range(len(self.x)):
            y = y0 + (self.y[i] - y0 + self.v[i] * t) % h
            x = self.x[i] + self.slant * (y - y0)
            L = self.L * self.v[i] / 2300
            cv2.line(lay, (int(x), int(y)), (int(x - self.slant * L), int(y - L)), float(self.a[i]), 1, cv2.LINE_AA)
        if mask is not None:
            lay *= mask
        frame += lay[..., None] * np.array(color, np.float32) * k


class Snow:
    def __init__(self, n, seed=3):
        r = np.random.default_rng(seed)
        self.x, self.y = r.uniform(-50, W + 50, n), r.uniform(0, H, n)
        self.v = r.uniform(60, 170, n)
        self.s = r.uniform(1.0, 3.2, n)
        self.ph = r.uniform(0, 6.28, n)

    def draw(self, frame, t, k=1.0):
        for i in range(len(self.x)):
            y = (self.y[i] + self.v[i] * t) % (H + 40) - 20
            x = self.x[i] + 30 * math.sin(t * 0.9 + self.ph[i]) + 25 * t
            add_spot(frame, x % (W + 60) - 30, y, self.s[i], (0.95, 0.97, 1.0), 0.55 * k)


def flick(t, seed=0):
    return 0.86 + 0.08 * math.sin(t * 11.0 + seed) * math.sin(t * 3.7 + 1.3 * seed) + 0.05 * math.sin(t * 23.0 + seed)


def bolt_pts(x0, y0, x1, y1, seed, n=12, jag=40):
    r = np.random.default_rng(seed)
    pts = []
    for i in range(n + 1):
        u = i / n
        pts.append((x0 + (x1 - x0) * u + (r.uniform(-jag, jag) if 0 < i < n else 0), y0 + (y1 - y0) * u))
    return pts


def draw_bolt(frame, pts, k):
    if k <= 0.01:
        return
    lay = np.zeros(frame.shape[:2], np.float32)
    p = np.array(pts, np.int32)
    cv2.polylines(lay, [p], False, 1.0, 3, cv2.LINE_AA)
    g = cv2.GaussianBlur(lay, (0, 0), 9)
    frame += (lay[..., None] * np.array([0.9, 0.95, 1.0]) + g[..., None] * np.array([0.5, 0.6, 1.0]) * 2.0) * k


def mask_from(fn, w=W, h=H):
    cv = Canvas(w, h)
    fn(cv)
    return cv.rgba()[..., 3]


def cloud_tex(h, w, scale, seed):
    n = fbm(h // 2, w // 2, scale=scale / 2, octaves=6, seed=seed)
    return cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)


# ----------------------------------------------------------------------------- F1: a study on a stormy night

WIN = (290, 790, 580, 1000)      # x0, x1, arch centre y, bottom


def window_path(inset=0.0):
    x0, x1, cy, yb = WIN
    r = (x1 - x0) / 2 - inset
    p = skia.Path()
    p.moveTo(x0 + inset, yb)
    p.lineTo(x0 + inset, cy)
    p.arcTo(skia.Rect((x0 + x1) / 2 - r, cy - r, (x0 + x1) / 2 + r, cy + r), 180, 180, False)
    p.lineTo(x1 - inset, yb)
    p.close()
    return p


def spine(w, h, color, title, seed, size=64):
    """A leather book spine lying flat, with gold bands and a gold title."""
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    shade = 0.45 + 0.55 * np.sin(np.pi * np.clip(yy * 0.96 + 0.02, 0, 1)) ** 0.6
    n = fbm(h, w, scale=6, octaves=3, seed=seed)
    img = np.ones((h, w, 3), np.float32) * np.array(color, np.float32)
    img *= (0.82 + 0.3 * n)[..., None] * shade[..., None]
    gold = np.array([0.80, 0.63, 0.30], np.float32)
    for bx in (34, 46, w - 47, w - 35):
        img[:, bx:bx + 5] = gold * (0.5 + 0.5 * shade)[..., None]
    rgba = np.dstack([img, np.ones((h, w), np.float32)])
    t = T(title, "bask", size, (214, 176, 92), tracking=6)
    ta = np.asarray(t, np.float32) / 255.0
    th, tw = ta.shape[:2]
    x, y = (w - tw) // 2, (h - th) // 2
    sh = np.zeros_like(rgba[..., 0])
    sh[y + 2:y + 2 + th, x + 1:x + 1 + tw] = ta[..., 3]
    rgba[..., :3] *= (1 - 0.55 * sh[..., None])                      # pressed into the leather
    a = ta[..., 3:4]
    rgba[y:y + th, x:x + tw, :3] = rgba[y:y + th, x:x + tw, :3] * (1 - a) + ta[..., :3] * a * \
        (0.75 + 0.35 * shade[y:y + th, :, None])
    return rgba


class Study:
    def __init__(self):
        rng = np.random.default_rng(1)
        wall = vgrad([(0, (0.060, 0.048, 0.040)), (1, (0.095, 0.072, 0.054))])
        wall *= (0.85 + 0.3 * fbm(H, W, scale=40, octaves=4, seed=2))[..., None]
        self.win_a = mask_from(lambda cv: cv.c.drawPath(window_path(), paint("#ffffff")))
        # the window frame and its bars
        frame = Canvas(W, H)
        frame.c.drawPath(window_path(-16), paint("#140e0a"))
        frame.c.drawPath(window_path(0), paint("#ffffff", mode=skia.BlendMode.kClear))
        x0, x1, cy, yb = WIN
        frame.rect((x0 + x1) / 2 - 8, cy - (x1 - x0) / 2, (x0 + x1) / 2 + 8, yb, "#140e0a")
        frame.rect(x0, 760, x1, 776, "#140e0a")
        frame.rect(x0 - 40, yb, x1 + 40, yb + 26, "#1e150f")         # the sill
        fr = frame.rgba()
        self.room = wall * (1 - self.win_a[..., None])
        self.room = self.room * (1 - fr[..., 3:4]) + fr[..., :3]
        self.room_a = np.clip(1 - self.win_a + fr[..., 3], 0, 1)
        # the desk
        dy = 1125
        grain = cv2.resize(fbm(40, W // 4, scale=4, octaves=3, seed=5), (W, H - dy), interpolation=cv2.INTER_CUBIC)
        desk = np.ones((H - dy, W, 3), np.float32) * np.array([0.16, 0.10, 0.06], np.float32)
        desk *= (0.7 + 0.5 * grain)[..., None]
        desk[:6] *= 1.6
        self.room[dy:] = desk
        self.room_a[dy:] = 1
        # the books
        for (bx0, by0, bw, bh, col, title, sd) in ((200, 1005, 680, 120, (0.12, 0.20, 0.14), "FRANKENSTEIN", 7),
                                                   (245, 895, 590, 110, (0.34, 0.07, 0.06), "DRACULA", 8)):
            sp = spine(bw, bh, col, title, sd)
            a = sp[..., 3:4]
            self.room[by0:by0 + bh, bx0:bx0 + bw] = self.room[by0:by0 + bh, bx0:bx0 + bw] * (1 - a) + sp[..., :3] * a
            self.room_a[by0:by0 + bh, bx0:bx0 + bw] = 1
        top = Canvas(W, H)
        top.poly([(250, 895), (830, 895), (812, 878), (268, 878)], "#2a0806")
        # the candle in a brass holder on top of the stack
        top.ellipse(700, 880, 74, 13, "#6a4a1e")
        top.ellipse(700, 876, 60, 10, "#a37a36")
        self.wick = art.candle(top, 700, 874, 180, 54)
        self.top = top.rgba()                     # the stack's top and the candle, lit on their own
        self.light = light_map(H, W, self.wick[0], self.wick[1] - 20, 700, power=1.3)[..., None]
        wl = np.zeros((H, W), np.float32)
        wl[:] = light_map(H, W, 540, 700, 900, power=1.0)
        self.winlight = wl[..., None]
        self.sky = vgrad([(0, (0.05, 0.07, 0.10)), (0.5, (0.10, 0.13, 0.17)), (1, (0.16, 0.18, 0.22))])
        self.clouds = cloud_tex(H, W + 400, 300, 11)
        self.rain = Rain(260, (WIN[0], 330, WIN[1], WIN[3]), seed=4, a=(0.12, 0.35))
        self.bolts = {1.25: bolt_pts(470, 340, 560, 900, 5), 5.2: bolt_pts(640, 340, 520, 920, 9)}

    def render(self, t, u):
        L = max([bs.lightning(t, at, 0.35) for at in self.bolts] + [0.0])
        off = int(t * 14) % 400
        cl = self.clouds[:, off:off + W]
        sky = self.sky * (0.75 + 0.6 * cl[..., None]) + L * 0.8 * cl[..., None] * np.array([0.7, 0.75, 0.9])
        for at, pts in self.bolts.items():
            draw_bolt(sky, pts, max(0.0, 1 - (t - at) / 0.22) if t >= at else 0.0)
        self.rain.draw(sky, t, mask=self.win_a)
        f = flick(t)
        lit = self.room * (0.34 + 2.4 * self.light * f * np.array([1.0, 0.74, 0.46]) + 0.9 * L * self.winlight)
        out = sky * (1 - self.room_a[..., None]) + lit * self.room_a[..., None]
        a = self.top[..., 3:4]
        out = out * (1 - a) + self.top[..., :3] * (0.42 + 0.38 * f) * np.array([1.0, 0.9, 0.8])
        add_spot(out, self.wick[0], self.wick[1] - 30, 70, (1.0, 0.62, 0.28), 0.22 * f)
        art.candle_flame(out, self.wick[0], self.wick[1], 30, t, seed=3, k=1.15)
        return zoom(out, 1.0 + 0.05 * min(1.0, u / 5.8), 540, 900)


# ----------------------------------------------------------------------------- F2: Tambora

class Volcano:
    def __init__(self):
        self.sky = vgrad([(0, (0.02, 0.015, 0.02)), (0.45, (0.08, 0.03, 0.025)), (0.72, (0.30, 0.09, 0.03)),
                          (1, (0.05, 0.03, 0.03))])
        r = np.random.default_rng(3)
        cx, cy = 540, 990
        left, right = [], []
        for i in range(41):
            u = i / 40
            dy = (1480 - cy) * u ** 0.62
            left.append((cx - 70 - 700 * u + r.uniform(-8, 8) * u, cy + dy + r.uniform(-6, 6) * u))
            right.append((cx + 70 + 700 * u + r.uniform(-8, 8) * u, cy + dy + r.uniform(-6, 6) * u))
        pts = list(reversed(left)) + right + [(1300, 1500), (-300, 1500)]
        self.mount = mask_from(lambda cv: cv.poly(pts, "#ffffff", smooth=False))
        self.cx, self.cy = cx, cy
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.6) ** 2)
        self.rim = (np.exp(-d / 210.0) * self.mount)[..., None] * np.array([1.0, 0.36, 0.08], np.float32)
        self.glow = np.exp(-d / 330.0)[..., None] * np.array([1.0, 0.42, 0.10], np.float32)
        # lava running down the slopes
        lv = np.zeros((H, W), np.float32)
        for k, (sx, ex, sd) in enumerate(((-30, -330, 1), (25, 290, 2), (-60, -520, 3), (50, 470, 4))):
            p = bolt_pts(cx + sx, cy + 8, cx + ex, cy + 260 + abs(ex) * 0.35, sd + 20, n=16, jag=14)
            cv2.polylines(lv, [np.array(p, np.int32)], False, 1.0 - 0.15 * k, 4 + (k % 2) * 2, cv2.LINE_AA)
        self.lava = lv * self.mount
        self.lava_g = cv2.GaussianBlur(self.lava, (0, 0), 7)
        # the sea, and the glow on it
        sea = np.zeros((H, W), np.float32)
        sea[1500:] = 1
        self.sea = sea
        streak = cv2.resize(fbm(H // 8, W // 2, scale=6, octaves=3, seed=9), (W, H), interpolation=cv2.INTER_CUBIC)
        self.refl = (streak * np.exp(-np.abs(xx - cx) / 160.0) * np.clip((yy - 1500) / 420, 0, 1) ** 0.5 *
                     np.exp(-(yy - 1500) / 300.0) * sea)[..., None] * np.array([1.0, 0.45, 0.12])
        self.plume_tex = fbm(H + 900, W, scale=150, octaves=6, seed=17)
        self.yy, self.xx = yy, xx
        self.embers = core_embers(cx)
        self.bolts = {7.15: bolt_pts(500, 420, 610, 760, 31, jag=30), 8.3: bolt_pts(650, 360, 520, 700, 33, jag=34)}

    def render(self, t, u, t_erupt):
        e = ease_out((t - t_erupt) / 0.8) if t >= t_erupt else 0.0
        out = self.sky.copy()
        out += self.glow * (0.35 + 0.35 * e)
        # the ash column, widening as it rises
        cx, cy = self.cx, self.cy
        off = int((t * 70 + e * 60) % 900)
        n = self.plume_tex[900 - off:900 - off + H]
        rise = np.clip((cy - self.yy) / 900.0, 0, 1.4)
        halfw = 80 + (cy - self.yy) * (0.42 + 0.25 * e) + 70 * (n - 0.5)
        col = np.clip(1 - np.abs(self.xx - cx - 40 * rise) / np.maximum(halfw, 1), 0, 1)
        col = np.clip(col * 2.2, 0, 1) * (self.yy < cy + 10) * np.clip((cy + 10 - self.yy) / 40, 0, 1)
        col *= np.clip(1.25 - rise * 0.35, 0, 1)
        a = col * (0.55 + 0.45 * n)
        ash = np.array([0.11, 0.09, 0.085], np.float32) * (0.6 + 0.8 * n[..., None])
        under = np.exp(-np.clip(cy - self.yy, 0, None) / (260 + 160 * e))[..., None] * \
            np.array([1.0, 0.38, 0.08]) * (0.9 + 0.6 * e)
        out = out * (1 - a[..., None]) + (ash + under * (0.7 + 0.3 * n[..., None])) * a[..., None]
        for at, pts in self.bolts.items():
            if at <= t < at + 0.25:
                draw_bolt(out, pts, 0.9 * (1 - (t - at) / 0.25))
        # the mountain, lit from the crater, and the lava
        m = self.mount[..., None]
        out = out * (1 - m) + (np.array([0.035, 0.025, 0.025]) + self.rim * (0.8 + 0.5 * e)) * m
        fl = 0.8 + 0.2 * math.sin(t * 9) * math.sin(t * 4.1)
        lava = (self.lava[..., None] * np.array([1.0, 0.75, 0.3]) + self.lava_g[..., None] * np.array([1.0, 0.35, 0.05])
                * 1.4) * fl * (0.75 + 0.4 * e)
        out += lava
        # the sea
        s = self.sea[..., None]
        out = out * (1 - s) + (np.array([0.012, 0.012, 0.02]) + self.refl * (0.8 + 0.7 * e)) * s
        self.embers.draw(out, t * (1 + 0.6 * e), k=0.8 + 0.8 * e)
        if t >= t_erupt:                                    # the blast: a flash and a shake
            k = max(0.0, 1 - (t - t_erupt) / 0.5)
            out += k * 0.5 * np.array([1.0, 0.55, 0.2], np.float32)
            sh = np.random.default_rng(int(t * 1000)).normal(0, 12 * k, 2)
            out = cv2.warpAffine(out, np.array([[1, 0, sh[0]], [0, 1, sh[1]]], np.float32), (W, H),
                                 borderMode=cv2.BORDER_REFLECT)
        return zoom(out, 1.0 + 0.06 * min(1.0, u / 3.0), 540, 1000)


def core_embers(cx):
    from core import Embers
    return Embers(140, cx - 60, cx + 60, 990, rise=520, spread=240, life=(1.0, 2.6), size=(1.2, 2.8), seed=6,
                  color=(1.0, 0.5, 0.12))


# ----------------------------------------------------------------------------- F3: 1816, no summer

class ColdSummer:
    def __init__(self):
        sky = vgrad([(0, (0.30, 0.33, 0.37)), (0.6, (0.50, 0.52, 0.55)), (1, (0.30, 0.31, 0.32))])
        cl = cloud_tex(H, W, 260, 21)
        sky *= (0.85 + 0.3 * cl[..., None])
        self.base = sky
        far = art.ridge(W, 1130, 70, 260, seed=4)
        near = art.ridge(W, 1270, 60, 380, seed=6)
        yy = np.arange(H, dtype=np.float32)[:, None]
        mfar = np.clip((yy - far[None, :]) / 2.0, 0, 1)
        mnear = np.clip((yy - near[None, :]) / 2.0, 0, 1)
        self.base = self.base * (1 - mfar[..., None]) + np.array([0.33, 0.36, 0.40]) * mfar[..., None]
        field = vgrad([(0, (0.26, 0.29, 0.27)), (1, (0.12, 0.13, 0.13))])
        field *= (0.85 + 0.3 * fbm(H, W, scale=30, octaves=4, seed=8))[..., None]
        frost = np.clip(fbm(H, W, scale=8, octaves=3, seed=9) - 0.55, 0, 1)[..., None] * 0.9
        field = field + frost * np.array([0.8, 0.85, 0.9])
        self.base = self.base * (1 - mnear[..., None]) + field * mnear[..., None]
        house = Canvas(W, H)
        hx, hy = 760, int(near[760]) + 4
        house.poly([(hx - 90, hy), (hx - 90, hy - 80), (hx, hy - 140), (hx + 90, hy - 80), (hx + 90, hy)], "#1d2024")
        house.rect(hx + 40, hy - 150, hx + 58, hy - 100, "#1d2024")
        house.poly([(hx + 110, hy), (hx + 110, hy - 70), (hx + 170, hy - 110), (hx + 230, hy - 70), (hx + 230, hy)],
                   "#22262a")
        for i in range(70):
            x = (i * 37) % W
            house.line([(x, H - 20), (x + 6, H - 140 - (i * 53) % 160)], "#1a1c1e", 3)
        hr = house.rgba()
        self.base = self.base * (1 - hr[..., 3:4]) + hr[..., :3]
        self.base *= np.array([0.94, 0.98, 1.05], np.float32)
        self.snow = Snow(420)
        self.smoke = (hx + 49, hy - 150)

    def render(self, t, u):
        out = self.base.copy()
        for i in range(10):
            ph = ((t * 0.35 + i / 10) % 1.0)
            add_spot(out, self.smoke[0] + 60 * ph + 10 * math.sin(i), self.smoke[1] - 150 * ph, 6 + 20 * ph,
                     (0.6, 0.62, 0.65), 0.12 * (1 - ph))
        self.snow.draw(out, t)
        return zoom(out, 1.03 + 0.04 * min(1.0, u / 2.2), 540, 900)


# ----------------------------------------------------------------------------- F4: the Villa Diodati in a storm

class Villa:
    def __init__(self):
        sky = vgrad([(0, (0.015, 0.02, 0.035)), (0.5, (0.05, 0.06, 0.085)), (1, (0.09, 0.10, 0.12))])
        self.clouds = cloud_tex(H, W + 400, 260, 41)
        self.sky = sky
        yy = np.arange(H, dtype=np.float32)[:, None]
        alps1 = art.ridge(W, 990, 230, 300, seed=12, octaves=6)
        alps2 = art.ridge(W, 1010, 120, 200, seed=13, octaves=6)
        self.m1 = np.clip((yy - alps1[None, :]) / 2.0, 0, 1)
        self.m2 = np.clip((yy - alps2[None, :]) / 2.0, 0, 1)
        self.snowcap = (np.clip(1 - (yy - alps1[None, :]) / 60.0, 0, 1) * self.m1)
        lake = np.zeros((H, W), np.float32)
        lake[1040:] = 1
        self.lake = lake
        ripple = cv2.resize(fbm(H // 10, W // 2, scale=5, octaves=3, seed=14), (W, H), interpolation=cv2.INTER_CUBIC)
        self.ripple = ripple
        # the shore and the villa on it
        fg = Canvas(W, H)
        shore = [(-20, 1330), (200, 1290), (420, 1250), (560, 1215), (760, 1205), (940, 1190), (1100, 1180),
                 (1100, 1920), (-20, 1920)]
        fg.poly(shore, "#07080b", smooth=False)
        vx, vy, vw, vh = 640, 1208, 340, 236
        fg.rect(vx - vw / 2, vy - vh, vx + vw / 2, vy, "#0d0f13")
        fg.poly([(vx - vw / 2 - 18, vy - vh), (vx - vw / 2 + 60, vy - vh - 74), (vx + vw / 2 - 60, vy - vh - 74),
                 (vx + vw / 2 + 18, vy - vh)], "#0a0b0e")
        self.windows = []
        r = np.random.default_rng(5)
        for row in range(3):
            for colm in range(5):
                wx = vx - vw / 2 + 40 + colm * (vw - 80) / 4
                wy = vy - vh + 30 + row * 70
                lit = r.random() < 0.55
                fg.rect(wx - 14, wy, wx + 14, wy + 44, "#ffb45c" if lit else "#1a1c22")
                if lit:
                    self.windows.append((wx, wy + 22))
        for k in range(5):                                        # the ground-floor arcade
            ax = vx - vw / 2 + 36 + k * (vw - 72) / 4
            fg.rect(ax - 18, vy - 50, ax + 18, vy, "#050608", r=14)
        for tx, th in ((430, 330), (470, 270), (905, 360), (960, 300), (1015, 250)):
            fg.c.drawPath(smooth_path([(tx - 26, 1260), (tx - 20, 1260 - th * 0.6), (tx, 1260 - th),
                                       (tx + 20, 1260 - th * 0.6), (tx + 26, 1260)], True), paint("#040506"))
        self.fg = fg.rgba()
        self.win_glow = np.zeros((H, W, 3), np.float32)
        for wx, wy in self.windows:
            add_spot(self.win_glow, wx, wy, 26, (1.0, 0.65, 0.3), 0.5)
        # their reflections in the lake
        refl = np.zeros((H, W), np.float32)
        for wx, wy in self.windows:
            ry = 1040 + (1208 - wy) * 0.4
            cv2.line(refl, (int(wx), int(ry)), (int(wx), int(ry + 160)), 0.6, 10, cv2.LINE_AA)
        self.refl = cv2.GaussianBlur(refl, (0, 0), 5) * lake
        self.rain = Rain(420, (0, 0, W, H), seed=7, a=(0.06, 0.2))
        self.bolts = {11.25: bolt_pts(260, 280, 330, 960, 41, jag=50), 12.55: bolt_pts(840, 300, 760, 900, 43)}

    def render(self, t, u):
        L = max([bs.lightning(t, at, 0.35) for at in self.bolts] + [0.0])
        off = int(t * 18) % 400
        cl = self.clouds[:, off:off + W]
        out = self.sky * (0.7 + 0.6 * cl[..., None]) + (L * 0.9 * cl)[..., None] * np.array([0.65, 0.7, 0.85])
        for at, pts in self.bolts.items():
            draw_bolt(out, pts, max(0.0, 1 - (t - at) / 0.22) if t >= at else 0.0)
        far = np.array([0.06, 0.07, 0.09]) + L * np.array([0.25, 0.27, 0.32])
        out = out * (1 - self.m1[..., None]) + (far + self.snowcap[..., None] * (0.03 + 0.4 * L)) * self.m1[..., None]
        near = np.array([0.035, 0.04, 0.05]) + L * np.array([0.12, 0.13, 0.16])
        out = out * (1 - self.m2[..., None]) + near * self.m2[..., None]
        lk = self.lake[..., None]
        water = np.array([0.012, 0.016, 0.026]) * (0.7 + 0.6 * self.ripple[..., None]) + \
            (self.refl * (0.6 + 0.4 * self.ripple))[..., None] * np.array([1.0, 0.62, 0.3]) + \
            (L * 0.35 * self.ripple)[..., None] * np.array([0.6, 0.65, 0.8])
        out = out * (1 - lk) + water * lk
        a = self.fg[..., 3:4]
        out = out * (1 - a) + self.fg[..., :3]
        out += self.win_glow * flick(t, 2)
        self.rain.draw(out, t, k=1.0)
        return zoom(out, 1.0 + 0.05 * min(1.0, u / 2.0), 640, 1100)


# ----------------------------------------------------------------------------- F5: three of them by candlelight

def bust_path(cv, x, y, s, bun=False, hair=0.0):
    p = smooth_path([(x - 150 * s, y + 10), (x - 140 * s, y - 120 * s), (x - 80 * s, y - 175 * s),
                     (x + 80 * s, y - 175 * s), (x + 140 * s, y - 120 * s), (x + 150 * s, y + 10)], True)
    cv.c.drawPath(p, paint("#ffffff"))
    cv.rect(x - 28 * s, y - 230 * s, x + 28 * s, y - 160 * s, "#ffffff")
    cv.ellipse(x, y - 265 * s, 58 * s, 70 * s, "#ffffff")
    if bun:
        cv.circle(x + 32 * s, y - 318 * s, 30 * s, "#ffffff")
        cv.ellipse(x, y - 300 * s, 62 * s, 44 * s, "#ffffff")
    if hair:
        cv.ellipse(x - 6 * s, y - 300 * s, 64 * s, 42 * s, "#ffffff")
        cv.ellipse(x + 30 * s, y - 296 * s, 40 * s, 30 * s, "#ffffff")


class Parlor:
    FIG = [("byron", 220, 1215, 1.2, False, 1.0), ("mary", 540, 1150, 0.98, True, 0.0),
           ("polidori", 860, 1215, 1.15, False, 0.6)]

    def __init__(self):
        wall = vgrad([(0, (0.05, 0.04, 0.035)), (1, (0.09, 0.066, 0.05))])
        wall *= (0.85 + 0.3 * fbm(H, W, scale=40, octaves=4, seed=22))[..., None]
        # a tall window at the back
        self.wm = mask_from(lambda cv: cv.rect(410, 380, 670, 900, "#ffffff", r=10))
        self.sky = vgrad([(0, (0.05, 0.06, 0.09)), (1, (0.12, 0.13, 0.16))])
        self.clouds = cloud_tex(H, W + 300, 200, 51)
        bars = Canvas(W, H)
        bars.rect(532, 380, 548, 900, "#120d0a")
        bars.rect(410, 630, 670, 644, "#120d0a")
        bars.rect(392, 900, 688, 922, "#1c140e")
        br = bars.rgba()
        room = wall * (1 - self.wm[..., None])
        room = room * (1 - br[..., 3:4]) + br[..., :3]
        self.room_a = np.clip(1 - self.wm + br[..., 3], 0, 1)
        # the figures, black, with candlelight catching their edges
        self.cx, self.cy = 540, 1000
        figs = np.zeros((H, W), np.float32)
        rim = np.zeros((H, W), np.float32)
        for name, x, y, s, bun, hair in self.FIG:
            m = mask_from(lambda cv: bust_path(cv, x, y, s, bun, hair))
            d = np.array([x - self.cx, y - 260 * s - self.cy], np.float32)
            d = d / (np.linalg.norm(d) + 1e-6) * 7
            away = cv2.warpAffine(m, np.array([[1, 0, d[0]], [0, 1, d[1]]], np.float32), (W, H))
            rim = np.maximum(rim, np.clip(m - away, 0, 1))
            figs = np.maximum(figs, m)
        self.figs, self.rim = figs, cv2.GaussianBlur(rim, (0, 0), 1.2)
        # the table and two candles
        table = np.ones((H - 1150, W, 3), np.float32) * np.array([0.13, 0.08, 0.05], np.float32)
        table *= (0.75 + 0.4 * cv2.resize(fbm(40, W // 4, scale=4, octaves=3, seed=23), (W, H - 1150)))[..., None]
        room[1150:] = table
        self.room_a[1150:] = 1
        cand = Canvas(W, H)
        self.wicks = [art.candle(cand, 512, 1172, 210, 46), art.candle(cand, 572, 1176, 170, 44)]
        cr = cand.rgba()
        self.room = room
        self.cand = cr
        self.light = light_map(H, W, 540, 960, 760, power=1.25)[..., None]
        self.bolts = [15.35, 17.75]

    def render(self, t, u):
        L = max([bs.lightning(t, at, 0.35) for at in self.bolts] + [0.0])
        off = int(t * 12) % 300
        sky = self.sky * (0.7 + 0.6 * self.clouds[:, off:off + W][..., None]) + L * 0.7
        f = flick(t, 5)
        warm = np.array([1.0, 0.72, 0.44], np.float32)
        lit = self.room * (0.28 + 1.9 * self.light * f * warm + 0.6 * L)
        out = sky * (1 - self.room_a[..., None]) + lit * self.room_a[..., None]
        fm = self.figs[..., None]
        out = out * (1 - fm) + np.array([0.012, 0.01, 0.01]) * fm
        out += (self.rim * 1.1 * f)[..., None] * warm * np.clip(self.light * 1.6, 0, 1)
        a = self.cand[..., 3:4]
        out = out * (1 - a) + self.cand[..., :3] * (0.42 + 0.38 * f) * np.array([1.0, 0.9, 0.8])
        for i, (wx, wy) in enumerate(self.wicks):
            add_spot(out, wx, wy - 28, 60, (1.0, 0.62, 0.28), 0.18 * f)
            art.candle_flame(out, wx, wy, 26, t + i * 1.7, seed=7 + i, k=1.15)
        return zoom(out, 1.0 + 0.05 * min(1.0, u / 5.7), 540, 1000)


# ----------------------------------------------------------------------------- F6/F7: the two title pages

def title_page(lines, w, h, seed):
    page = bs.aged_paper(w, h, seed=seed)
    d = ImageDraw.Draw(page)
    for kind, text, size, y in lines:
        if kind == "rule":
            d.line((w * 0.3, y, w * 0.7, y), fill=INKC + (200,), width=2)
            continue
        img = T(text, kind, size, INKC + (235,))
        if img.width > w - 80:
            img = fitT(text, kind, size, INKC + (235,), max_w=w - 80, min_size=14)
        page.alpha_composite(img, ((w - img.width) // 2, int(y)))
    return page


FRANK_PAGE = [("oldst_b", "FRANKENSTEIN;", 92, 80), ("oldst", "OR,", 38, 196), ("oldst", "THE MODERN PROMETHEUS.", 46, 250),
              ("rule", "", 0, 330), ("oldst", "IN THREE VOLUMES.", 32, 356), ("oldst", "VOL. I.", 30, 404),
              ("rule", "", 0, 462),
              ("fell_it", "Did I request thee, Maker, from my clay", 31, 492),
              ("fell_it", "To mould me man? Did I solicit thee", 31, 534),
              ("fell_it", "From darkness to promote me?—", 31, 576),
              ("oldst", "PARADISE LOST.", 24, 626), ("rule", "", 0, 686),
              ("fell_it", "London:", 40, 722), ("oldst", "PRINTED FOR", 24, 786),
              ("oldst", "LACKINGTON, HUGHES, HARDING, MAVOR, & JONES,", 22, 826),
              ("oldst", "FINSBURY-SQUARE.", 22, 862), ("rule", "", 0, 916), ("oldst", "1818.", 42, 940)]
VAMP_PAGE = [("oldst_b", "THE VAMPYRE;", 88, 120), ("oldst", "A TALE.", 46, 250), ("rule", "", 0, 340),
             ("fell_it", "London:", 44, 560), ("rule", "", 0, 650), ("oldst", "1819.", 46, 690)]


def desk_glow():
    base = vgrad([(0, (0.03, 0.025, 0.02)), (1, (0.06, 0.04, 0.03))])
    base += light_map(H, W, 300, 1500, 1200, power=1.2)[..., None] * np.array([0.45, 0.28, 0.14])
    return base


# ----------------------------------------------------------------------------- the reel

def build(R):
    t_same, t_volc = R.at("same rainy"), R.at("volcano.")
    t_in, t_mount, t_erupt = R.at("In 1815,"), R.at("Mount"), R.at("erupted.")
    t_next = R.at("The next")
    t_stuck = R.at("Stuck")
    t_lord, t_mary, t_john = R.at("Lord"), R.at("Mary Shelley"), R.at("John")
    t_scary = R.at("scariest")
    t_mary2 = R.at("Mary wrote")
    t_frank2 = R.at("Frankenstein.", t_mary2)
    t_pol2 = R.at("Polidori wrote")
    t_craze, t_drac = R.at("craze"), R.at("Dracula.", t_pol2)
    t_dbl = R.at("Double-tap")
    c1 = (R.end("volcano.") + t_in) / 2
    c2 = (R.end("erupted.") + t_next) / 2
    c3 = (R.end("dark.") + t_stuck) / 2
    c4 = t_lord - 0.12
    c5 = (R.end("story.") + t_mary2) / 2
    c6 = (R.end("Frankenstein.", t_mary2) + t_pol2) / 2
    c7 = t_dbl - 0.14

    def np_scene(cls, extra=None):
        def prep(ctx):
            ctx["s"] = cls()
            if extra:
                extra(ctx)
        return prep

    def lab(text, size=34, color=BONE):
        return glow(T(text, "bold", size, color, tracking=4), (0, 0, 0), radius=14, strength=0.9)

    def ttl(text, size=74, color=BONE):
        return glow(fitT(text, "bask", size, color, max_w=C.CW, min_size=40), (0, 0, 0), radius=24, strength=0.95)

    def d_study(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "t1" not in ctx:
            ctx["t1"] = ttl("ONE RAINY SUMMER · 1816")
        paste(f, ctx["t1"], W / 2, 1205, appear(t, t_same - 0.05, 0.3))

    def d_volcano(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u, t_erupt)))
        bs.shade(f)
        from reel_belle import typed
        typed(f, "1815", t, t_in, 340, size=110, rate=0.07)
        typed(f, "MOUNT TAMBORA, INDONESIA", t, t_mount, 450, size=44, rate=0.03)

    def d_cold(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "y" not in ctx:
            ctx["y"] = glow(T("1816", "bask", 230, ICE), (90, 140, 220), radius=40, strength=0.7)
            ctx["l"] = lab("THE YEAR WITHOUT A SUMMER", 40)
        a = appear(t, c2 + 0.05, 0.4)
        paste(f, scaled(ctx["y"], 1.08 - 0.08 * a), W / 2, 560, a)
        paste(f, ctx["l"], W / 2, 735, appear(t, c2 + 0.35, 0.35))

    def d_villa(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("THE VILLA DIODATI")
            ctx["t"] = ttl("LAKE GENEVA · JUNE 1816")
        paste(f, ctx["l"], W / 2, 300, appear(t, c3 + 0.1, 0.3))
        paste(f, ctx["t"], W / 2, 1205, appear(t, R.at("Lake Geneva,") - 0.05, 0.3))

    def d_parlor(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "n" not in ctx:
            ctx["n"] = [(lab(n, 32), lab(a, 28, SEPIA), x, y) for n, a, x, y in
                        (("LORD BYRON", "AGE 28", 225, 720), ("MARY SHELLEY", "AGE 18", 540, 680),
                         ("JOHN POLIDORI", "AGE 20", 850, 740))]
            ctx["t"] = ttl("A GHOST-STORY CONTEST")
        for (nm, ag, x, y), at in zip(ctx["n"], (t_lord, t_mary, t_john)):
            a = appear(t, at - 0.05, 0.3)
            paste(f, nm, x, y + 16 * (1 - a), a)
            paste(f, ag, x, y + 44 + 16 * (1 - a), a)
        paste(f, ctx["t"], W / 2, 1205, appear(t, t_scary - 0.1, 0.3))

    def prep_pages(ctx):
        ctx["bg"] = desk_glow()
        ctx["fp"] = title_page(FRANK_PAGE, 760, 1010, 61)
        ctx["vp"] = title_page(VAMP_PAGE, 700, 820, 62)
        ctx["dr"] = glow(T("DRACULA", "bask", 170, (232, 40, 34)), (130, 0, 0), radius=36, strength=0.9)
        ctx["dr2"] = lab("BRAM STOKER · 1897", 38)
        ctx["bats"] = {(s, up): hw.bat(s, up) for s in (70, 96, 120) for up in (True, False)}

    def lit_page(page, t, seed):
        f = 0.9 + 0.1 * flick(t, seed)
        arr = np.asarray(page, np.float32) / 255.0
        yy, xx = np.mgrid[0:page.height, 0:page.width].astype(np.float32)
        lm = np.clip(1.15 - np.sqrt((xx - page.width * 0.2) ** 2 + (yy - page.height * 0.95) ** 2) / (page.width * 1.6),
                     0.35, 1)
        arr[..., :3] *= (lm * f)[..., None]
        return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGBA")

    def d_frank(f, u, t, ctx):
        f.alpha_composite(to_pil(zoom(ctx["bg"], 1.0 + 0.04 * u / 1.8)))
        if "fpl" not in ctx:
            ctx["fpl"] = lit_page(ctx["fp"], 0, 1).rotate(-1.5, expand=True, resample=Image.BICUBIC)
        z = 0.98 + 0.04 * min(1.0, u / (c6 - c5))
        paste(f, scaled(ctx["fpl"], z), W / 2, 760, appear(u, 0.0, 0.2))
        bs.shade(f)
        bs.credit_line(f, "Title page re-set from the first edition, 1818")

    def d_vamp(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["bg"]))
        if "vpl" not in ctx:
            ctx["vpl"] = lit_page(ctx["vp"], 0, 2).rotate(1.2, expand=True, resample=Image.BICUBIC)
        k = ease((t - t_craze + 0.1) / 0.6) if t >= t_craze - 0.1 else 0.0
        z = (0.98 + 0.03 * min(1.0, u / 3.0)) * (1 - 0.3 * k)
        paste(f, scaled(ctx["vpl"], z), W / 2, 740 - 200 * k, appear(u, 0.0, 0.2) * (1 - 0.35 * k))
        if t >= t_craze:
            for i, (y0, sp, size) in enumerate(((560, 900, 96), (820, 760, 70), (420, 1050, 120), (980, 840, 96),
                                                (660, 980, 70))):
                x = -150 + (t - t_craze) * sp + i * 70
                y = y0 + 30 * math.sin((t - t_craze) * 6 + i)
                up = int((t + i * 0.07) / 0.09) % 2 == 0
                paste(f, ctx["bats"][(size, up)], x, y)
        if t >= t_drac - 0.05:
            a = appear(t, t_drac - 0.05, 0.12)
            paste(f, scaled(ctx["dr"], 1.6 - 0.6 * a), W / 2, 980, a)
            paste(f, ctx["dr2"], W / 2, 1110, appear(t, t_drac + 0.15, 0.25))
        bs.shade(f)
        bs.credit_line(f, "Title page re-set from the 1819 edition")

    def prep_end(ctx):
        hw.FACES[:] = [hw.face_layer(s) for _, _, s, _ in hw.PUMPKINS]
        ctx["bg"] = hw.night_base()
        ctx["cta"] = C.DoubleTap("LA PORTE'S OWN", "Halloween stories, just as strange", color1=hw.GOLDEN,
                                 glow1=(255, 120, 0), kind1="black", size1=100, y=520)

    def d_end(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        hw.animate(f, t)
        ctx["cta"].draw(f, u)

    scenes = [C.Scene(0.0, c1, d_study, np_scene(Study)), C.Scene(c1, c2, d_volcano, np_scene(Volcano)),
              C.Scene(c2, c3, d_cold, np_scene(ColdSummer)), C.Scene(c3, c4, d_villa, np_scene(Villa)),
              C.Scene(c4, c5, d_parlor, np_scene(Parlor)), C.Scene(c5, c6, d_frank, prep_pages),
              C.Scene(c6, c7, d_vamp, None), C.Scene(c7, R.dur + 1, d_end, prep_end, flicker=0.0)]
    scenes[6].prep = lambda ctx: ctx.update(scenes[5].ctx) if scenes[5].ready else prep_pages(ctx)
    atm = bs.Atmos(tint=(196, 196, 204), fog=0.1, vignette=0.7, grain=12, seed=5)
    flashes = [(1.25, 0.3), (5.2, 0.3), (11.25, 0.3), (12.55, 0.3), (15.35, 0.28), (17.75, 0.28), (t_frank2, 0.3)]
    film = C.Film(R, scenes, flashes=flashes, flicker=0.3, atmos=atm)

    import sfx as X
    import audio as AU
    n = int((R.dur + 0.5) * SR)
    rain = np.zeros(n, np.float32)
    r1 = X.rain(R.dur + 0.5, seed=34).mean(1)[:n]
    env = np.zeros(n, np.float32)
    for a, b, g in ((0.0, c1, 1.0), (c3, c4, 1.0), (c4, c5, 0.45), (c5, c7, 0.3)):
        env[int(a * SR):int(b * SR)] = g
    env = bs.lowpass(env, int(0.25 * SR))
    rain[:len(r1)] = r1 * env[:len(r1)]
    wind = X.wind(c3 - c2 + 1.0, seed=30).mean(1)
    rumble = X.lp(np.random.default_rng(3).normal(0, 1, int((c2 - c1) * SR)).astype(np.float32), 90) * 3.0
    rumble *= bs.env_ar(len(rumble), 0.6, 0.4)
    lava = X.fire_bed(c2 - c1, seed=31).mean(1)
    lava = lava * bs.env_ar(len(lava), 0.5, 0.3)
    th = lambda sd, d=5.0: X.thunder(d, seed=sd).mean(1)
    ev = [(rain, 0.0, 0.9, "bed"), (th(9), 1.22, 0.8, "bed"), (th(10), 5.17, 0.8, "bed"),
          (rumble, c1, 0.9, "bed"), (lava, c1, 0.4, "bed"), (X.boom(seed=22).mean(1), t_erupt, 1.0),
          ("type", t_in, 0.9), ("type", t_mount, 0.9),
          (wind, c2 - 0.2, 0.9, "bed"), (th(11), 11.22, 0.9, "bed"), (th(12, 4.0), 12.52, 0.8, "bed"),
          (th(13, 4.0), 15.32, 0.6, "bed"), (th(14, 4.0), 17.72, 0.6, "bed"), ("hit", t_scary, 0.6),
          ("whoosh", c5, 0.6), (th(15), t_frank2, 0.8, "bed"), ("whoosh", c6, 0.6),
          (X.whoosh(dur=0.9, seed=27).mean(1), t_craze, 0.6), ("hit", t_drac, 0.9),
          ("pop", c7 + 0.12, 0.9), ("pop", c7 + 0.42, 0.9), ("hit", c7 + 0.5, 0.6)]
    music = X.drone(R.dur + 1, seed=181).mean(1) * 0.9
    prog = AU.PROG[3]
    d = (R.dur - 0.5) / len(prog)
    pads = np.zeros(int((R.dur + 1) * SR), np.float32)
    for k, chord in enumerate(prog):
        p = X.pad(d + 3.0, [AU.N[cn] for cn in chord], seed=400 + k, attack=2.0, release=2.5).mean(1)
        i = int(max(0.0, k * d - 0.8) * SR)
        m = min(len(pads) - i, len(p))
        pads[i:i + m] += p[:m]
    music = music + pads * 0.8
    mot = AU.motif(6, 0.42).mean(1) if AU.motif(6, 0.42).ndim > 1 else AU.motif(6, 0.42)
    i = int((c7 + 0.7) * SR)
    m = min(len(music) - i, len(mot))
    music[i:i + m] += mot[:m] * 0.8
    return film, ev, music, "Frankenstein, Dracula and the Year Without a Summer"


OUTFILE = "frankenstein-dracula-and-the-year-without-a-summer.mp4"


def main(mode, times=None):
    R = C.Reel("frank")
    film, ev, music, title = build(R)
    if mode == "stills":
        ts = times or [0.4, 1.3, 3.2, 5.3, 6.6, 7.8, 8.3, 9.6, 11.3, 12.4, 13.8, 15.6, 17.9, 19.4, 21.5, 23.6, 24.6,
                       26.5]
        print(film.stills([t for t in ts if t < R.dur], "frank"))
        return
    vid = os.path.join(C.OUT, "_frank_video.mp4")
    film.video(vid, cover_t=0.8)
    mix = C.soundtrack(R, music, ev, music_gain=0.5)
    out = os.path.join(C.OUT, OUTFILE)
    C.finish(R, vid, mix, out, title)
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    main(sys.argv[1], [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None)
