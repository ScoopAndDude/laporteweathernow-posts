"""La Porte's own legends: three drawn reels (Oct. 25, 2026), the follow-up the Frankenstein reel promised.

    python3 reel_haunts.py posey|patton|orr stills|video [times]

Facts and legends are the hauntings page's (laporteweathernow.com/hauntings, "The case files"):
- Posey Chapel Cemetery, 3789 E 1000 N, Galena Township near Hesston: began in 1833 as a family plot for the children
  of Wightman Goit; a Methodist chapel in 1841, a new chapel in 1855, destroyed by an arson fire in 1972. Legends:
  the 1855 chapel was built after a fire set by a deranged preacher killed members of his congregation; a woman in
  white singing to a guitar; Mary Goit's spirit; bouncing lights; bells. (Ashley Hood, Haunted Cemeteries of Indiana,
  2020, via the La Porte County Herald-Dispatch.)
- Patton Cemetery, 1401 Rumely St: laid out by John Walker in 1841; holds Jennie Olson, Andrew Helgelien and Peter
  Gunness. Legends: shadows, voices, orbs, a heavy sadness near the victims' graves.
- Orr Lake Road ("Hangman's Road"): no record of a hanging; the story is the legend folklorists call "The Boyfriend's
  Death" (Indiana State University Folklore Archives, Lake County, 1970).
Everything is drawn except Belle Gunness's portrait in the Patton reel (public domain).
"""
import math
import os
import sys

import cv2
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFilter

import reels_common as C
from reels_common import bs, vr, W, H, SR, T, fitT, glow, paste, scaled, appear, ease, ease_out, dim, BONE, SEPIA
from core import fbm, add_spot, Canvas, smooth_path, poly_path, paint, light_map, Fog, Flame, Embers, smoothstep, \
    clamp01
import art
from reel_frank import to_pil, zoom, Rain, flick
from reel_belle import typed, red_title, label_fn

C.WEIGHT.update({"1833": 4.7, "1972": 5.0, "1841": 4.7, "1908": 4.35})
GHOSTC = (0.56, 1.0, 0.77)
LANT = (1.0, 0.66, 0.3)
FIRE = (1.0, 0.5, 0.16)
OUTFILES = {"posey": "posey-chapel-cemetery-the-bells.mp4", "patton": "patton-cemetery-belle-gunness-victims.mp4",
            "orr": "orr-lake-road-hangmans-road.mp4"}
TITLES = {"posey": "Posey Chapel Cemetery", "patton": "Patton Cemetery", "orr": "Orr Lake Road"}

# --------------------------------------------------------------------------------------------- the kit

SKY_NIGHT = [(0.0, "#020507"), (0.28, "#07131a"), (0.48, "#11252c"), (0.58, "#1d363b"), (1.0, "#22393d")]


def cv():
    return Canvas(W, H)


def night_sky(seed, moon=(790, 400, 58), stars=520, clouds=0.32, stops=None):
    return art.sky(W, H, stops=stops or SKY_NIGHT, moon=moon, stars=stars, clouds=clouds, seed=seed,
                   cloud_band=(0.0, 0.5), star_max_y=0.55, moon_glow=0.6)


def land(img, horizon, seed, far="#0a1519", near="#05090b", fog="#6f938e", fog_a=0.32):
    art.hills(img, horizon - 24, 34, 420, far, seed + 1, rim="#36514f", rim_w=3, rim_a=0.35)
    art.fog_band(img, horizon - 6, 46, fog, fog_a, seed=seed + 2)
    return art.hills(img, horizon + 30, 18, 640, near, seed + 3, rim="#2c4442", rim_w=3, rim_a=0.25)


def comp(img, layer, a=1.0):
    return art.comp(img, layer, a)


def layer_from_pil(im, x, y):
    """A PIL RGBA image placed at (x, y) as a full-frame premultiplied float layer."""
    lay = np.zeros((H, W, 4), np.float32)
    a = np.asarray(im.convert("RGBA"), np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + im.width), min(H, y + im.height)
    lay[y0:y1, x0:x1] = a[y0 - y:y1 - y, x0 - x:x1 - x]
    return lay


def sprite(draw_fn, w, h, blur=0.0):
    """Draw a shape on a small canvas; returns its alpha (h, w)."""
    c = Canvas(w, h)
    draw_fn(c)
    m = c.rgba()[..., 3]
    return cv2.GaussianBlur(m, (0, 0), blur) if blur else m


def put(frame, m, x, y, color, a, mode="add"):
    """Composite an alpha sprite with its bottom-centre at (x, y): add light, or darken (mode='dark')."""
    hh, ww = m.shape
    x0, y0 = int(x - ww / 2), int(y - hh)
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + ww), min(H, y0 + hh)
    if X1 <= X0 or Y1 <= Y0 or a <= 0.002:
        return
    mm = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None] * a
    if mode == "add":
        frame[Y0:Y1, X0:X1] += mm * np.array(color, np.float32)
    else:
        frame[Y0:Y1, X0:X1] = frame[Y0:Y1, X0:X1] * (1 - mm) + mm * np.array(color, np.float32)


class Bouncers:
    """The 'bouncing lights': small glowing orbs hopping between the graves."""

    def __init__(self, n, x0, x1, y0, y1, seed=4, color=GHOSTC):
        r = np.random.default_rng(seed)
        self.x = r.uniform(x0, x1, n)
        self.y = r.uniform(y0, y1, n)
        self.f = r.uniform(0.6, 1.1, n)
        self.amp = r.uniform(30, 80, n)
        self.ph = r.uniform(0, 6.28, n)
        self.dx = r.uniform(-25, 25, n)
        self.s = r.uniform(4, 7, n)
        self.color = color

    def draw(self, frame, t, k=1.0):
        for i in range(len(self.x)):
            hop = abs(math.sin(math.pi * self.f[i] * t + self.ph[i]))
            x = self.x[i] + self.dx[i] * t
            y = self.y[i] - hop * self.amp[i]
            b = (0.55 + 0.45 * math.sin(t * 3.1 + self.ph[i] * 2)) * k
            add_spot(frame, x, y, self.s[i] * 5, self.color, 0.10 * b)
            add_spot(frame, x, y, self.s[i], self.color, 0.85 * b)
            add_spot(frame, x, y, self.s[i] * 0.4, (1, 1, 1), 0.6 * b)
            add_spot(frame, x, y + hop * self.amp[i] + 8, self.s[i] * 3, self.color, 0.05 * b)   # glow on the grass


def grade(img, tint, k):
    """Push the picture toward a colour (k 0..1)."""
    if k <= 0:
        return img
    lum = img.mean(axis=2, keepdims=True)
    return img * (1 - k) + (lum * 1.6) * np.array(tint, np.float32) * k


def finish(img, t, u, z0=1.0, z1=1.06, dur=4.0, cx=W / 2, cy=1000):
    return zoom(img, z0 + (z1 - z0) * min(1.0, u / dur), cx, cy)


# --------------------------------------------------------------------------------------------- props

def chapel(c, lights, x, y, s=1.0, dark="#06090b", rim="#3b5654", lit=0.0, logs=False):
    """A plain country chapel seen from the front corner, with a belfry. (x, y) = bottom-left of the front wall."""
    fw, fh, roof = 300 * s, 250 * s, 150 * s
    sd, sk = 250 * s, 34 * s
    c.c.drawPath(poly_path([(x + fw, y), (x + fw, y - fh), (x + fw + sd, y - fh - sk), (x + fw + sd, y - sk)]),
                 paint("#040607"))
    c.c.drawPath(poly_path([(x + fw * 0.5, y - fh - roof), (x + fw + 6 * s, y - fh + 4 * s),
                            (x + fw + sd + 6 * s, y - fh - sk + 4 * s), (x + fw * 0.5 + sd, y - fh - roof - sk)]),
                 paint("#030405"))
    front = poly_path([(x, y), (x, y - fh), (x + fw * 0.5, y - fh - roof), (x + fw, y - fh), (x + fw, y)])
    art.rim_shape(c, front, dark, rim, (3 * s, 3 * s))
    if logs:
        for k in range(1, 9):
            yy = y - k * fh / 9
            c.line([(x + 4, yy), (x + fw - 4, yy)], "#0d1214", 2.0 * s, 0.8)
    if not logs:
        bx, bw = x + fw * 0.5, 74 * s
        by = y - fh - roof + 34 * s
        bel = poly_path([(bx - bw / 2, by), (bx - bw / 2, by - 92 * s), (bx, by - 158 * s), (bx + bw / 2, by - 92 * s),
                         (bx + bw / 2, by)])
        art.rim_shape(c, bel, dark, rim, (3 * s, 3 * s))
        c.rect(bx - 20 * s, by - 82 * s, bx + 20 * s, by - 38 * s, "#10171a")
        c.ellipse(bx, by - 54 * s, 12 * s, 14 * s, "#262a24")
    art.lancet(c, lights, x + fw * 0.5 - 32 * s, y, 64 * s, 126 * s, "#0d0a07", 0.0)
    for wx in (x + 46 * s, x + fw - 86 * s):
        art.lancet(c, lights, wx, y - 86 * s, 40 * s, 104 * s, "#ffb45c" if lit else "#0c1012", lit)
    for k in range(2):
        wx = x + fw + 60 * s + k * 100 * s
        wy = y - 80 * s - sk * (60 + k * 100) / 250
        c.c.drawPath(poly_path([(wx, wy), (wx, wy - 96 * s), (wx + 34 * s, wy - 101 * s), (wx + 34 * s, wy - 5 * s)]),
                     paint("#0b0f11"))
    return dict(windows=[(x + 66 * s, y - 140 * s), (x + fw - 66 * s, y - 140 * s)],
                door=(x + fw * 0.5, y - 60 * s), roof=(x + fw * 0.5 + sd * 0.45, y - fh - roof * 0.5 - sk * 0.5),
                belfry=(x + fw * 0.5, y - fh - roof - 20 * s))


def car(c, x, y, s=1.0, body="#090c0f", glass="#111a20", rim="#46646a"):
    """A 1960s sedan from the side, facing left. (x, y) = ground under its middle. Returns light positions."""
    L = 620 * s
    x0, x1 = x - L / 2, x + L / 2
    yb = y - 34 * s
    top = yb - 118 * s
    bodyp = smooth_path([(x0 + 4 * s, yb), (x0, yb - 46 * s), (x0 + 12 * s, top + 26 * s), (x0 + 120 * s, top + 8 * s),
                         (x0 + 200 * s, top), (x1 - 150 * s, top - 2 * s), (x1 - 40 * s, top + 10 * s),
                         (x1 + 6 * s, top + 30 * s), (x1 + 8 * s, yb - 40 * s), (x1, yb)], True, k=0.12)
    art.rim_shape(c, bodyp, body, rim, (2 * s, 3 * s), rim_a=0.65)
    cab = smooth_path([(x0 + 200 * s, top + 4 * s), (x0 + 262 * s, top - 82 * s), (x1 - 196 * s, top - 86 * s),
                       (x1 - 140 * s, top + 2 * s)], True, k=0.1)
    art.rim_shape(c, cab, body, rim, (2 * s, 3 * s), rim_a=0.65)
    c.c.drawPath(poly_path([(x0 + 222 * s, top), (x0 + 270 * s, top - 70 * s), (x0 + 372 * s, top - 72 * s),
                            (x0 + 372 * s, top)]), paint(glass))
    c.c.drawPath(poly_path([(x0 + 386 * s, top), (x0 + 386 * s, top - 72 * s), (x1 - 205 * s, top - 74 * s),
                            (x1 - 160 * s, top)]), paint(glass))
    c.line([(x0 + 30 * s, yb - 58 * s), (x1 - 20 * s, yb - 58 * s)], "#2c3c40", 2.5 * s, 0.7)   # chrome strip
    for wx in (x0 + 120 * s, x1 - 120 * s):
        c.circle(wx, yb, 52 * s, "#020304")
        c.circle(wx, yb, 40 * s, "#07090b")
        c.circle(wx, yb, 18 * s, "#1b2427")
    return dict(head=(x0 + 8 * s, yb - 48 * s), tail=(x1 + 4 * s, yb - 46 * s), roof=(x - 20 * s, top - 86 * s),
                cabin=(x - 30 * s, top - 40 * s))


def street_sign(text, w=560, h=128):
    S = 3
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * S - 1, h * S - 1), radius=18 * S, fill=(20, 92, 58, 255))
    d.rounded_rectangle((7 * S, 7 * S, w * S - 8 * S, h * S - 8 * S), radius=13 * S, outline=(236, 240, 232, 255),
                        width=4 * S)
    f = C.font("xbold", 76 * S)
    tw = f.getlength(text)
    d.text(((w * S - tw) / 2, (h * S - 76 * S * 1.2) / 2), text, font=f, fill=(240, 244, 236, 255))
    im = im.resize((w, h), Image.LANCZOS)
    # moonlight falls off toward the bottom
    a = np.asarray(im, np.float32)
    k = np.linspace(0.62, 0.34, h, dtype=np.float32)[:, None, None]
    a[..., :3] *= k
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def road(c, vx, vy, bottom=(420, 1180), y_bottom=H, color="#0c1416", edge="#22383a", curve=0.0):
    xl, xr = bottom
    pts_l = [(vx + (xl - vx) * k + curve * math.sin(k * math.pi) * 60, vy + (y_bottom - vy) * k) for k in np.linspace(0, 1, 24)]
    pts_r = [(vx + (xr - vx) * k + curve * math.sin(k * math.pi) * 60, vy + (y_bottom - vy) * k) for k in np.linspace(0, 1, 24)]
    c.poly(pts_l + pts_r[::-1], color)
    c.line(pts_l, edge, 3, 0.5)
    c.line(pts_r, edge, 3, 0.5)


# --------------------------------------------------------------------------------------------- shared text

def lab(text, size=34, color=BONE):
    return glow(T(text, "bold", size, color, tracking=4), (0, 0, 0), radius=14, strength=0.9)


def ttl(text, size=74, color=BONE):
    return glow(fitT(text, "bask", size, color, max_w=C.CW, min_size=40), (0, 0, 0), radius=24, strength=0.95)


def scene(cls, *args, **kw):
    def prep(ctx):
        ctx["s"] = cls(*args, **kw)
    return prep


# =============================================================================================== POSEY CHAPEL

class PoseyWide:
    """Farm country at night; a little cemetery on a rise at the end of a gravel road."""

    def __init__(self):
        img = night_sky(3, moon=(800, 380, 60))
        land(img, 1000, 30, near="#0a1416")
        yy = np.arange(H, dtype=np.float32)[:, None]
        img += (np.clip((yy - 1000) / 900.0, 0, 1) * 0.035)[..., None] * np.array([0.6, 0.9, 0.9], np.float32)
        c = cv()
        road(c, 600, 1000, bottom=(170, 1060), color="#18252a", edge="#3c5658")
        for k in range(16):                                 # stubble rows, converging
            xb = -500 + k * 140
            c.line([(600 + (xb - 600) * 0.02, 1004), (xb, H)], "#142226", 3.0, 0.7)
        c.poly([(330, 1012), (440, 960), (600, 942), (780, 948), (920, 972), (1010, 1012)], "#070c0e", smooth=True)
        art.gravestones(c, 985, 400, 940, 18, seed=7, hmin=30, hmax=74, rim="#5a7c76")
        art.fence(c, 1004, 360, 990, spacing=26, h=52, seed=5, broken=0.2)
        art.tree(c, 420, 1000, 640, seed=11, depth=7, spread=0.55, lean=0.08)
        art.tree(c, 930, 996, 560, seed=12, depth=7, spread=0.6, lean=-0.06)
        art.tree(c, 70, 1040, 820, seed=13, depth=7, spread=0.5, lean=0.12)
        art.grass(c, 1060, 0, W, "#060b0c", n=300, hmin=8, hmax=28, seed=3)
        comp(img, c.rgba())
        self.img = img
        self.fog = Fog(seed=3, scale=300, color="#7fa39e", density=0.22, top=0.5, bottom=0.72, speed=24, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.08, 4.5, 640, 940)


class PoseyStones:
    """Down among the oldest stones."""

    def __init__(self):
        img = night_sky(5, moon=(240, 430, 50), clouds=0.4)
        land(img, 1150, 40)
        c = cv()
        art.gravestones(c, 1158, 40, 1040, 22, seed=21, hmin=40, hmax=110, rim="#45625f")
        art.tree(c, 860, 1160, 760, seed=22, depth=7, spread=0.6, lean=-0.1)
        art.fence(c, 1176, -20, 1100, spacing=30, h=50, seed=6, broken=0.25)
        comp(img, c.rgba())
        art.fog_band(img, 1180, 80, "#6f938e", 0.4, seed=8)
        c2 = cv()
        art.gravestones(c2, 1470, 120, 980, 3, seed=29, hmin=380, hmax=520, tilt=0.08, dark="#080d0f",
                        rim="#5e807b", kinds=("round", "slab", "round"))
        art.grass(c2, 1480, 0, W, "#040708", n=520, hmin=20, hmax=80, seed=4)
        comp(img, c2.rgba())
        self.img = img
        self.fog = Fog(seed=5, scale=280, color="#86aaa4", density=0.26, top=0.52, bottom=0.9, speed=20, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        self.fog.apply(out, t)
        return finish(out, t, u, 1.04, 1.0, 3.2, 540, 1100)


class PoseyChapel:
    """The last chapel, dark and long out of use, until the arson fire."""

    def __init__(self, t_fire):
        self.t_fire = t_fire
        img = night_sky(9, moon=(860, 360, 50), clouds=0.35)
        land(img, 1120, 50)
        c = cv()
        lights = cv()
        self.pts = chapel(c, lights, 300, 1126, s=1.0, lit=0.0)
        art.tree(c, 150, 1130, 700, seed=31, depth=7, spread=0.55, lean=0.1)
        art.tree(c, 960, 1128, 560, seed=32, depth=7, spread=0.6, lean=-0.12)
        art.gravestones(c, 1150, 40, 280, 6, seed=33, hmin=30, hmax=70)
        art.gravestones(c, 1150, 870, 1060, 5, seed=34, hmin=30, hmax=70)
        art.grass(c, 1170, 0, W, "#05090a", n=380, hmin=10, hmax=40, seed=6)
        comp(img, c.rgba())
        self.img = img
        w0, w1 = self.pts["windows"]
        self.flames = [(Flame(150, 260, seed=3, speed=1.2), w0, 0.0), (Flame(150, 260, seed=4, speed=1.1), w1, 0.25),
                       (Flame(360, 540, seed=5, speed=0.9, width=0.7), self.pts["roof"], 0.55),
                       (Flame(220, 380, seed=6, speed=1.0), self.pts["door"], 0.4)]
        self.light = light_map(H, W, 520, 960, 820, power=1.2)
        self.embers = Embers(70, 330, 900, 900, rise=300, spread=80, seed=8)
        self.fog = Fog(seed=9, scale=300, color="#7fa39e", density=0.16, top=0.55, bottom=0.8, speed=18, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        self.fog.apply(out, t)
        if t >= self.t_fire - 0.2:
            k_all = ease((t - self.t_fire + 0.2) / 1.2)
            fl = flick(t, 4)
            out += self.light[..., None] * np.array(FIRE, np.float32) * (0.55 * k_all * fl)
            for fm, (fx, fy), delay in self.flames:
                k = ease((t - self.t_fire - delay) / 0.8)
                if k <= 0:
                    continue
                spr = fm.render(t, intensity=0.6 + 0.6 * k)
                hh, ww = spr.shape[:2]
                x0, y0 = int(fx - ww / 2), int(fy - hh * 0.82)
                X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + ww), min(H, y0 + hh)
                out[Y0:Y1, X0:X1] += spr[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * k
            self.embers.draw(out, t, k=k_all)
        return finish(out, t, u, 1.0, 1.05, 4.0, 540, 980)


class PoseyLegend:
    """The legend's older fire: a plain log chapel burning, a hooded preacher watching."""

    def __init__(self):
        img = night_sky(13, moon=None, clouds=0.5, stars=200,
                        stops=[(0, "#050203"), (0.5, "#140806"), (0.62, "#2a120a"), (1.0, "#160805")])
        art.hills(img, 1160, 20, 500, "#070403", 41, rim="#5a2a12", rim_w=4, rim_a=0.5)
        c = cv()
        lights = cv()
        chapel(c, lights, 260, 1166, s=1.05, dark="#050302", rim="#6a3416", logs=True)
        art.tree(c, 980, 1170, 640, seed=42, depth=7, spread=0.6, lean=-0.1, color="#030101")
        art.grass(c, 1180, 0, W, "#040201", n=360, hmin=10, hmax=40, seed=7)
        self.fg = c.rgba()
        p = cv()
        art.hooded(p, 860, 1560, 820, color="#020101", rim="#ff8a3a", seed=4)
        self.preacher = p.rgba()
        self.img = img
        self.flame = Flame(760, 980, seed=12, speed=0.85, width=0.8, tongues=1.3)
        self.flame2 = Flame(420, 620, seed=13, speed=1.1, width=0.7)
        self.light = light_map(H, W, 440, 1000, 1000, power=1.1)
        self.embers = Embers(120, 180, 820, 1000, rise=340, spread=110, seed=14)
        self.smoke = Fog(seed=15, scale=240, color="#3a2a22", density=0.35, top=0.0, bottom=0.6, speed=40, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        fl = flick(t, 7)
        spr = self.flame.render(t, intensity=1.2)
        x0, y0 = 70, 300
        out[y0:y0 + spr.shape[0], x0:x0 + spr.shape[1]] += spr * 0.95
        comp(out, self.fg)
        spr2 = self.flame2.render(t + 3.0, intensity=1.0)
        out[640:640 + spr2.shape[0], 230:230 + spr2.shape[1]] += spr2 * 0.6
        out += self.light[..., None] * np.array(FIRE, np.float32) * 0.5 * fl
        self.embers.draw(out, t, k=1.0)
        self.smoke.apply(out, t, mode="screen")
        comp(out, self.preacher)
        return finish(out, t, u, 1.06, 1.0, 5.0, 560, 1000)


class PoseyWhite:
    """Fog among the graves: a pale woman in white, and lights that bounce between the stones."""

    def __init__(self):
        img = night_sky(17, moon=(170, 380, 52), clouds=0.45)
        land(img, 1070, 60)
        c = cv()
        art.tree(c, 120, 1090, 760, seed=51, depth=7, spread=0.6, lean=0.12)
        art.tree(c, 990, 1086, 680, seed=52, depth=7, spread=0.55, lean=-0.1)
        art.gravestones(c, 1090, 30, 1060, 20, seed=53, hmin=26, hmax=70)
        art.gravestones(c, 1180, -20, 1100, 12, seed=54, hmin=70, hmax=150)
        art.gravestones(c, 1330, -40, 1120, 7, seed=55, hmin=150, hmax=260, rim="#55776f")
        art.grass(c, 1340, 0, W, "#040708", n=500, hmin=14, hmax=60, seed=8)
        comp(img, c.rgba())
        self.img = img
        self.woman = sprite(lambda k: art.figure(k, 160, 548, 520, color="#ffffff", dress=True,
                                                 arms=((10, 40), (-8, -30)), legs=(2, -2)), 320, 560, blur=3.0)
        self.halo = sprite(lambda k: art.figure(k, 160, 548, 520, color="#ffffff", dress=True,
                                                arms=((10, 40), (-8, -30)), legs=(2, -2)), 320, 560, blur=22.0)
        self.lights = Bouncers(8, 120, 980, 1080, 1250, seed=6)
        self.fog = Fog(seed=17, scale=320, color="#8fb3ad", density=0.32, top=0.48, bottom=0.85, speed=26, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        a = 0.16 + 0.08 * math.sin(t * 1.3) + 0.04 * math.sin(t * 5.1)
        x = 640 + 16 * math.sin(t * 0.35)
        put(out, self.halo, x, 1180, (0.6, 0.9, 0.8), a * 0.6)
        put(out, self.woman, x, 1180, (0.86, 0.98, 0.94), a)
        self.fog.apply(out, t)
        self.lights.draw(out, t, k=min(1.0, u / 0.8))
        return finish(out, t, u, 1.0, 1.06, 5.0, 620, 1060)


def build_posey(R):
    t_near = R.at("Near Hesston,")
    t_bells = R.at("bells.")
    t_posey = R.at("Posey Chapel")
    t_1833 = R.at("1833.")
    t_its = R.at("Its last")
    t_arson = R.at("arson")
    t_1972 = R.at("1972.")
    t_but = R.at("But legend")
    t_older = R.at("older fire,")
    t_preach = R.at("deranged preacher,")
    t_vis = R.at("Visitors report")
    t_white = R.at("woman in white,")
    t_lights = R.at("lights")
    t_visit = R.at("Visit in")
    t_dbl = R.at("double-tap")
    c1 = (R.end("bells.") + t_posey) / 2
    c2 = (R.end("1833.") + t_its) / 2
    c3 = (R.end("1972.") + t_but) / 2
    c4 = (R.end("congregation.") + t_vis) / 2
    c5 = (R.end("graves.") + t_visit) / 2
    bells = (0.5, 2.7)

    def d_wide(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("GALENA TOWNSHIP · NEAR HESSTON")
            ctx["t"] = ttl("POSEY CHAPEL CEMETERY", 78)
        for b in bells:                                   # the bells nobody rings: faint rings from the cemetery
            k = (t - b) / 1.6
            if 0 <= k <= 1:
                paste(f, C.ring(30 + 300 * k, 4, (190, 255, 220), 0.6 * (1 - k)), 660, 900)
        paste(f, ctx["l"], W / 2, 300)
        paste(f, ctx["t"], W / 2, 1205)

    def d_stones(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("IT BEGAN AS A FAMILY PLOT")
        typed(f, "1833", t, t_1833 - 0.1, 380, size=120, rate=0.07)
        paste(f, ctx["l"], W / 2, 490, appear(t, t_1833 + 0.25, 0.3))

    def d_chapel(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("DESTROYED BY ARSON")
            ctx["l0"] = lab("THE LAST CHAPEL, BUILT 1855")
        a0 = appear(t, c2 + 0.1, 0.3) * (1 - ease((t - t_arson + 0.3) / 0.3))
        paste(f, ctx["l0"], W / 2, 300, a0)
        typed(f, "1972", t, t_1972 - 0.15, 380, size=120, rate=0.07)
        paste(f, ctx["l"], W / 2, 490, appear(t, t_arson + 0.2, 0.3))

    def d_legend(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("THE LEGEND", 36, (255, 190, 140))
            ctx["t"] = ttl("AN OLDER FIRE", 84, (255, 214, 170))
        paste(f, ctx["l"], W / 2, 300, appear(t, c3 + 0.05, 0.3))
        paste(f, ctx["t"], W / 2, 1205, appear(t, t_older - 0.05, 0.3))

    def d_white(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("WHAT PEOPLE SAY")
        paste(f, ctx["l"], W / 2, 300, appear(t, c4 + 0.05, 0.3))

    def p_end(ctx):
        ctx["s"] = PoseyWhite()
        ctx["cta"] = C.DoubleTap("FOR THE NEXT LEGEND", "Visit in daylight · obey posted hours", color1=(170, 255, 214),
                                 glow1=(20, 120, 80), kind1="bask", size1=96, y=520)

    def d_end(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u + 5.0)))
        bs.shade(f)
        ctx["cta"].draw(f, u)

    scenes = [C.Scene(0.0, c1, d_wide, scene(PoseyWide)), C.Scene(c1, c2, d_stones, scene(PoseyStones)),
              C.Scene(c2, c3, d_chapel, scene(PoseyChapel, t_arson)), C.Scene(c3, c4, d_legend, scene(PoseyLegend)),
              C.Scene(c4, c5, d_white, scene(PoseyWhite)), C.Scene(c5, R.dur + 1, d_end, p_end, flicker=0.0)]
    scenes[3].flicker = 0.55
    atm = bs.Atmos(tint=(196, 204, 200), fog=0.08, vignette=0.58, grain=12, seed=5)
    film = C.Film(R, scenes, flashes=[], flicker=0.2, atmos=atm)

    import sfx as X
    n = int((R.dur + 0.5) * SR)
    wind = X.wind(R.dur + 0.5, seed=30, strength=0.8).mean(1)[:n]
    bell = lambda sd, f0: X.lp(X.bell(f=f0, dur=6.0, seed=sd).mean(1), 2400)
    fire = X.fire_bed(c4 - c2 + 0.6, seed=31).mean(1)
    fire *= np.concatenate([np.zeros(int(max(0, t_arson - c2 - 0.2) * SR), np.float32),
                            np.ones(len(fire), np.float32)])[:len(fire)]
    hum = X.eerie_hum(c5 - c4 + 1.0, seed=37).mean(1)
    ev = [(wind, 0.0, 0.55, "bed"), (bell(7, 196.0), bells[0], 0.55, "bed"), (bell(8, 175.0), bells[1], 0.5, "bed"),
          (X.owl(seed=24).mean(1), 3.3, 0.35), ("whoosh", c1, 0.5), ("type", t_1833 - 0.1, 0.9), ("whoosh", c2, 0.5),
          ("type", t_1972 - 0.15, 0.9), (fire, c2, 0.8, "bed"), ("hit", t_arson, 0.6), ("whoosh", c3, 0.6),
          ("hit", t_older, 0.7), ("whoosh", c4, 0.5), (hum, c4, 0.7, "bed"), (bell(9, 210.0), t_white, 0.35, "bed"),
          ("pop", c5 + 0.12, 0.9), ("pop", c5 + 0.42, 0.9), ("hit", c5 + 0.5, 0.6)]
    return film, ev, haunt_music(R, seed=60, prog=4), TITLES["posey"]


# =============================================================================================== PATTON CEMETERY

class TownCemetery:
    """An old town cemetery at night: stone gateposts, iron fence, big trees, a streetlamp and houses beyond."""

    def __init__(self, seed=0, close=False, fog_d=0.2, candles=False, dawn=False):
        if dawn:
            img = art.vgrad(H, W, [(0, "#1c2236"), (0.25, "#3c3a56"), (0.45, "#9a7478"), (0.56, "#e8a882"),
                                   (0.58, "#6a5a60"), (1.0, "#181a1e")])
            art.stars_only(img, 40, 7, 420, k=0.3)
            art.hills(img, 1086, 34, 420, "#4a4450", 70 + seed, rim="#f0b090", rim_w=3, rim_a=0.4)
            art.fog_band(img, 1104, 46, "#e0b0a0", 0.4, seed=72 + seed)
            art.hills(img, 1140, 18, 640, "#1a1a1f", 73 + seed)
        else:
            img = night_sky(21 + seed, moon=(830, 380, 54), clouds=0.38)
            land(img, 1110, 70 + seed, far="#0b1418")
        c = cv()
        lights = cv()
        for hx, hw_, hh in ((560, 150, 90), (760, 190, 110), (960, 140, 80)):      # houses on the far side
            c.rect(hx - hw_ / 2, 1106 - hh, hx + hw_ / 2, 1106, "#070b0d")
            c.poly([(hx - hw_ / 2 - 10, 1106 - hh), (hx, 1106 - hh - 54), (hx + hw_ / 2 + 10, 1106 - hh)], "#060a0c")
            lights.rect(hx - 20, 1106 - hh + 30, hx + 4, 1106 - hh + 58, "#ffb45c", 0.85)
            lights.glow(hx - 8, 1106 - hh + 44, 60, "#ffb45c", 0.25)
        art.tree(c, 130, 1140, 940, seed=61 + seed, depth=8, spread=0.7, lean=0.08)
        art.tree(c, 990, 1136, 860, seed=62 + seed, depth=8, spread=0.66, lean=-0.1)
        art.gravestones(c, 1120, 40, 1050, 26, seed=63 + seed, hmin=24, hmax=66)
        art.gravestones(c, 1200, -20, 1100, 14, seed=64 + seed, hmin=70, hmax=150)
        if not close:
            for gx in (250, 830):                                                   # the gateposts and fence
                art.rim_shape(c, poly_path([(gx - 36, 1290), (gx - 36, 900), (gx + 36, 900), (gx + 36, 1290)]),
                              "#080c0e", "#4a6662", (3, 3))
                c.rect(gx - 46, 880, gx + 46, 906, "#0a0f11")
            for k in range(-14, 44):
                xk = k * 26
                if 220 < xk < 860:
                    continue
                c.line([(xk, 1296), (xk, 1150)], "#050809", 5)
                c.poly([(xk - 7, 1152), (xk, 1132), (xk + 7, 1152)], "#050809")
            c.line([(-10, 1170), (220, 1170)], "#050809", 6)
            c.line([(860, 1170), (1100, 1170)], "#050809", 6)
            c.line([(286, 918), (540, 870), (794, 918)], "#050809", 6)
        else:
            art.gravestones(c, 1262, 300, 301, 1, seed=69, hmin=390, hmax=391, tilt=0.0, dark="#0a1012",
                            rim="#7a9e96", kinds=("round",))
            art.gravestones(c, 1250, 770, 771, 1, seed=70, hmin=340, hmax=341, tilt=0.0, dark="#0a1012",
                            rim="#7a9e96", kinds=("slab",))
            self.wick = art.candle(c, 420, 1280, 66, 24)
        art.grass(c, 1440, 0, W, "#040708", n=480, hmin=14, hmax=70, seed=9 + seed)
        comp(img, c.rgba())
        img += lights.rgba()[..., :3]
        add_spot(img, 1040, 980, 70, (1.0, 0.8, 0.5), 0.35)                          # a streetlamp, off to the right
        add_spot(img, 1040, 980, 12, (1.0, 0.9, 0.7), 1.2)
        self.img = img
        self.candles = candles
        self.fog = Fog(seed=21 + seed, scale=300, color="#86aaa4" if not dawn else "#e6c0b0", density=fog_d, top=0.5,
                       bottom=0.85, speed=20, w=W, h=H)

    def render(self, t, u, z=(1.0, 1.05)):
        out = self.img.copy()
        self.fog.apply(out, t)
        if self.candles:
            wx, wy = self.wick
            art.candle_flame(out, wx, wy, 10, t, seed=3, k=1.0)
            add_spot(out, wx, wy - 10, 110, LANT, 0.16 * flick(t, 3))
        return finish(out, t, u, z[0], z[1], 4.0, 540, 1050)


class Shadows(TownCemetery):
    """The same ground in heavier fog, with dark shapes drifting between the stones."""

    def __init__(self):
        super().__init__(seed=0, fog_d=0.36)
        self.img = grade(self.img, (0.62, 0.78, 1.0), 0.35)
        yy = np.arange(H, dtype=np.float32)[:, None, None]
        self.img += np.exp(-((yy - 1080) / 150.0) ** 2) * np.array([0.05, 0.07, 0.08], np.float32)
        self.fog2 = Fog(seed=44, scale=260, color="#86aaa4", density=0.1, top=0.45, bottom=0.8, speed=30, w=W, h=H)
        r = np.random.default_rng(5)
        self.figs = []
        for i in range(4):
            h = r.uniform(240, 340)
            m = sprite(lambda k, h=h: art.figure(k, 110, h + 10, h, color="#ffffff", coat=r.random() < 0.5,
                                                 dress=r.random() < 0.4), 220, int(h + 20), blur=4.0)
            self.figs.append(dict(m=m, x=150 + i * 250 + r.uniform(-40, 40), y=r.uniform(1150, 1200),
                                  v=r.uniform(-20, 20), ph=r.uniform(0, 6.28)))

    def render(self, t, u, z=(1.0, 1.06)):
        out = self.img.copy()
        self.fog.apply(out, t)
        for g in self.figs:
            a = (0.45 + 0.35 * math.sin(t * 0.8 + g["ph"])) * min(1.0, u / 0.8)
            put(out, g["m"], g["x"] + g["v"] * t, g["y"], (0.01, 0.015, 0.02), a, mode="dark")
        self.fog2.apply(out, t)
        return finish(out, t, u, z[0], z[1], 5.0, 540, 1080)


def build_patton(R):
    t_some = R.at("Some of")
    t_here = R.at("right here")
    t_patton = R.at("Patton Cemetery")
    t_1841 = R.at("1841,")
    t_oldest = R.at("oldest graves")
    t_her = R.at("Her teenage")
    t_jennie = R.at("Jennie Olson,")
    t_so = R.at("So does")
    t_andrew = R.at("Andrew Helgelien,")
    t_farmer = R.at("the farmer")
    t_vis = R.at("Visitors describe")
    t_please = R.at("Please visit")
    c1 = (R.end("Porte.") + t_patton) / 2
    c2 = (R.end("area.") + t_her) / 2
    c3 = (R.end("ad.") + t_vis) / 2
    c4 = (R.end("victims.", t_vis) + t_please) / 2
    shared = {}

    def p_face(ctx):
        ctx["face"] = bs.emerging("belle-08.jpg", "sepia", scale=3.0, blur=0.5)
        ctx["l"] = label_fn("PATTON CEMETERY · LA PORTE", c1, y=300)

    def d_face(f, u, t, ctx):
        bs.float_in(f, ctx["face"], u, c1, w=(1420, 1280), focus=((0.41, 0.40), (0.42, 0.42)), at=(540, 640))
        bs.shade(f)
        ctx["l"](f, t)
        red_title(f, "BELLE'S VICTIMS", 116, t, -0.2)
        bs.credit_line(f, "Belle Gunness, public domain")

    def d_gate(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("ONE OF LA PORTE'S OLDEST")
            ctx["l0"] = lab("1401 RUMELY STREET")
        paste(f, ctx["l0"], W / 2, 300, appear(t, c1 + 0.05, 0.3))
        typed(f, "1841", t, t_1841 - 0.1, 400, size=120, rate=0.07)
        paste(f, ctx["l"], W / 2, 510, appear(t, t_oldest - 0.1, 0.3))

    def p_graves(ctx):
        ctx["s"] = TownCemetery(seed=3, close=True, fog_d=0.22, candles=True)
        ctx["n1"] = ttl("JENNIE OLSON", 78)
        ctx["s1"] = glow(T("her teenage foster daughter", "fell_it", 48, (226, 214, 190)), (0, 0, 0), radius=14,
                         strength=0.9)
        ctx["n2"] = ttl("ANDREW HELGELIEN", 78)
        ctx["s2"] = glow(T("the farmer who answered her ad", "fell_it", 48, (226, 214, 190)), (0, 0, 0), radius=14,
                         strength=0.9)

    def d_graves(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u, z=(1.06, 1.0))))
        bs.shade(f)
        a1 = appear(t, t_jennie - 0.1, 0.3)
        paste(f, ctx["n1"], W / 2, 400 + 14 * (1 - a1), a1)
        paste(f, ctx["s1"], W / 2, 486, appear(t, t_jennie + 0.3, 0.3))
        a2 = appear(t, t_andrew - 0.1, 0.3)
        paste(f, ctx["n2"], W / 2, 640 + 14 * (1 - a2), a2)
        paste(f, ctx["s2"], W / 2, 726, appear(t, t_farmer, 0.3))

    def d_shadows(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("WHAT PEOPLE SAY")
        paste(f, ctx["l"], W / 2, 300, appear(t, c3 + 0.05, 0.3))

    def p_end(ctx):
        ctx["s"] = Shadows()
        ctx["cta"] = C.DoubleTap("FOR THE NEXT LEGEND", "Please visit in daylight", color1=(170, 255, 214),
                                 glow1=(20, 120, 80), kind1="bask", size1=96, y=520)

    def d_end(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u + 5.0)))
        bs.shade(f)
        ctx["cta"].draw(f, u)

    scenes = [C.Scene(0.0, c1, d_face, p_face), C.Scene(c1, c2, d_gate, scene(TownCemetery)),
              C.Scene(c2, c3, d_graves, p_graves), C.Scene(c3, c4, d_shadows, scene(Shadows)),
              C.Scene(c4, R.dur + 1, d_end, p_end, flicker=0.0)]
    scenes[0].flicker = 0.6
    atm = bs.Atmos(tint=(196, 204, 206), fog=0.1, vignette=0.58, grain=12, seed=6)
    film = C.Film(R, scenes, flashes=[(0.35, 0.3)], flicker=0.2, atmos=atm)

    import sfx as X
    n = int((R.dur + 0.5) * SR)
    wind = X.wind(R.dur + 0.5, seed=33, strength=0.9).mean(1)[:n]
    hum = X.eerie_hum(c4 - c3 + 1.0, seed=38, f=49.0).mean(1)
    ev = [(wind, 0.0, 0.5, "bed"), (X.thunder(5.0, seed=9).mean(1), 0.37, 0.7, "bed"), ("hit", 0.05, 0.6),
          (X.crow(n_caws=2, seed=2).mean(1), 2.2, 0.35), ("whoosh", c1, 0.5), ("type", t_1841 - 0.1, 0.9),
          ("whoosh", c2, 0.5), ("pop", t_jennie - 0.1, 0.5), ("pop", t_andrew - 0.1, 0.5), ("whoosh", c3, 0.5),
          (hum, c3, 0.8, "bed"), (whispers(c4 - c3, seed=4), c3 + 0.4, 0.5, "bed"),
          (X.heartbeat(c4 - c3, bpm=58).mean(1), c3 + 0.6, 0.45, "bed"),
          ("pop", c4 + 0.12, 0.9), ("pop", c4 + 0.42, 0.9), ("hit", c4 + 0.5, 0.6)]
    return film, ev, haunt_music(R, seed=70, prog=11), TITLES["patton"]


# =============================================================================================== ORR LAKE ROAD

class LakeRoad:
    """A dark road along Orr Lake, bare trees overhead; a green street sign in the foreground."""

    def __init__(self, sign=True):
        img = night_sky(31, moon=(300, 400, 54), clouds=0.3)
        hz = 1010
        art.hills(img, hz - 20, 26, 460, "#0a1519", 81, rim="#36514f", rim_w=3, rim_a=0.3)
        yy = np.arange(H, dtype=np.float32)[:, None]
        lake = ((yy >= hz) & (yy < 1300)).astype(np.float32) * np.ones((1, W), np.float32)
        xx = np.arange(W, dtype=np.float32)[None, :]
        lake *= np.clip((700 - xx - (yy - hz) * 0.9) / 30.0, 0, 1)
        ripple = cv2.resize(fbm(H // 8, W // 2, scale=6, octaves=3, seed=82), (W, H), interpolation=cv2.INTER_CUBIC)
        water = np.array([0.022, 0.042, 0.052], np.float32) * (0.7 + 0.6 * ripple[..., None])
        glint = np.exp(-((xx - 300) / (18 + (yy - hz) * 0.22)) ** 2) * (yy > hz) * (0.25 + 0.75 * ripple)
        water = water + (glint * 0.75)[..., None] * np.array([0.7, 0.85, 0.82], np.float32)
        img = img * (1 - lake[..., None]) + water * lake[..., None]
        ground = ((yy >= hz) * (1 - lake)).astype(np.float32)
        img = img * (1 - ground[..., None]) + np.array([0.016, 0.026, 0.03], np.float32) * ground[..., None]
        c = cv()
        road(c, 760, hz + 4, bottom=(520, 1300), color="#152126", edge="#33504f", curve=0.3)
        for k, (tx, th) in enumerate(((920, 860), (1040, 1040), (700, 300), (820, 420), (640, 220))):
            art.tree(c, tx, hz + 10 + (th > 500) * (th * 0.28), th, seed=90 + k, depth=7, spread=0.6, lean=-0.18)
        for k in range(9):                                             # the far shore's trees
            art.tree(c, 40 + k * 70, hz - 8, 70 + 40 * (k % 3), seed=100 + k, depth=5, spread=0.6)
        art.grass(c, 1500, 0, W, "#030506", n=420, hmin=20, hmax=90, seed=11)
        if sign:
            c.rect(786, 760, 802, 1640, "#0b0f10")
            c.line([(788, 760), (788, 1640)], "#44585a", 2, 0.6)
        comp(img, c.rgba())
        if sign:
            comp(img, layer_from_pil(street_sign("ORR LAKE RD"), 794 - 280, 640))
        self.img = img
        self.fog = Fog(seed=31, scale=320, color="#7fa39e", density=0.2, top=0.5, bottom=0.66, speed=22, w=W, h=H)

    def render(self, t, u):
        out = self.img.copy()
        self.fog.apply(out, t)
        return finish(out, t, u, 1.0, 1.07, 4.0, 700, 1000)


class CarScene:
    """The car on the shoulder under a huge bare tree; night, or dawn with police lights."""

    def __init__(self, t_died=None, t_walk=None, dawn=False, t_look=None, t_shoes=None):
        self.t_died, self.t_walk, self.dawn, self.t_look, self.t_shoes = t_died, t_walk, dawn, t_look, t_shoes
        hz = 1040
        if dawn:
            img = art.vgrad(H, W, [(0, "#1a2033"), (0.3, "#3a3550"), (0.48, "#8a6670"), (0.54, "#d8977a"),
                                   (0.56, "#5a5058"), (1.0, "#14181c")])
            art.stars_only(img, 60, 5, 500, k=0.4)
        else:
            img = night_sky(41, moon=(860, 360, 50), clouds=0.36)
        art.hills(img, hz - 20, 24, 520, "#0b1519" if not dawn else "#3c3a44", 111, rim="#36514f", rim_w=3,
                  rim_a=0.3)
        art.fog_band(img, hz, 50, "#6f938e" if not dawn else "#c9a39a", 0.35, seed=112)
        art.hills(img, hz + 22, 10, 700, "#05090b" if not dawn else "#14161a", 113)
        c = cv()
        xs = np.linspace(W + 20, -20, 40)
        top = [(x, 1226 - 46 * ((W - x) / W) ** 2) for x in xs]
        bot = [(x, 1334 - 96 * ((W - x) / W) ** 2) for x in xs]
        c.poly(top + bot[::-1], "#121c20" if not dawn else "#23262b")
        c.line(top, "#2e4446", 3, 0.5)
        art.tree(c, 880, 1250, 1250, seed=121, depth=8, spread=0.72, lean=-0.42, gnarl=0.36, width=70,
                 color="#020304")
        art.tree(c, 120, hz + 30, 380, seed=122, depth=7, spread=0.6, lean=0.1)
        art.grass(c, 1300, 0, W, "#030506", n=380, hmin=16, hmax=60, seed=12)
        self.carpts = car(c, 560, 1262, s=1.0)
        if dawn:
            pc = cv()
            car(pc, 1010, 1240, s=0.82, body="#0c0f12")
            pc.rect(960, 1060, 1060, 1074, "#1a1a1a")
            comp(img, pc.rgba())
        comp(img, c.rgba())
        self.img = img
        hx, hy = self.carpts["head"]
        beam = cv()
        beam.poly([(hx, hy - 10), (hx, hy + 12), (-200, hy + 150), (-200, hy - 70)], "#ffe8b0", 0.18, blur=18)
        self.beam = beam.rgba()[..., :3]
        self.walker = [sprite(lambda k, lg=lg: art.figure(k, 90, 330, 320, color="#ffffff", coat=True,
                                                          arms=((14, 10), (-14, -10)), legs=(lg, -lg)), 180, 340)
                       for lg in (14, 4, -14, 4)]
        self.shadow = sprite(lambda k: k.ellipse(60, 30, 50, 16, "#ffffff"), 120, 60, blur=8)
        self.red = light_map(H, W, 1000, 1066, 900, power=1.1)
        self.fog = Fog(seed=41, scale=320, color="#7fa39e" if not dawn else "#d8b0a4", density=0.2 if not dawn else 0.3,
                       top=0.5, bottom=0.72, speed=20, w=W, h=H)

    def headlights(self, t):
        if self.t_died is None:
            return 0.0
        if t < self.t_died:
            return 1.0
        d = t - self.t_died
        if d < 0.7:
            return 0.5 + 0.5 * math.sin(d * 60) * (1 - d / 0.7)
        return 0.0

    def render(self, t, u, z=None):
        out = self.img.copy()
        k = self.headlights(t)
        if k > 0:
            out += self.beam * k
            hx, hy = self.carpts["head"]
            add_spot(out, hx, hy, 26, (1.0, 0.92, 0.7), 0.9 * k)
            add_spot(out, hx, hy, 6, (1, 1, 1), 1.5 * k)
        if self.t_walk is not None and t >= self.t_walk:
            p = min(1.0, (t - self.t_walk) / 3.0)
            x = 222 - 190 * p
            y = 1292 - 74 * p
            s = 1.0 - 0.45 * p
            m = self.walker[int((t - self.t_walk) * 5) % 4]
            mm = cv2.resize(m, (max(2, int(m.shape[1] * s)), max(2, int(m.shape[0] * s))))
            put(out, mm, x, y, (0.008, 0.01, 0.012), 0.95 * (1 - ease((p - 0.75) / 0.25)), mode="dark")
        if self.dawn:
            ph = int(t * 6) % 2
            col = (1.0, 0.08, 0.06) if ph == 0 else (0.12, 0.3, 1.0)
            out += self.red[..., None] * np.array(col, np.float32) * 0.55
            add_spot(out, 985 if ph == 0 else 1035, 1066, 16, col, 2.0)
            add_spot(out, 985 if ph == 0 else 1035, 1066, 60, col, 0.5)
        if self.t_shoes is None or t < self.t_shoes:
            rx, ry = self.carpts["roof"]
            sx = rx + 60 * math.sin(t * 1.6)
            put(out, self.shadow, sx, ry + 40, (0.0, 0.0, 0.0), 0.0 if not self.t_walk else 0.0, mode="dark")
        self.fog.apply(out, t)
        if z is not None:
            return zoom(out, z[0], z[1], z[2])
        return finish(out, t, u, 1.0, 1.05, 5.0, 560, 1100)


class RoofScrape(CarScene):
    """Closer on the roof: a shadow sways across it, back and forth."""

    def __init__(self):
        super().__init__()
        rx, ry = self.carpts["roof"]
        sh = cv()
        sh.line([(rx - 150, ry + 8), (rx - 60, ry + 2), (rx + 60, ry + 1), (rx + 130, ry + 6)], "#ffffff", 9, blur=3)
        self.sheen = sh.rgba()[..., 3]

    def render(self, t, u, z=None):
        out = self.img.copy()
        rx, ry = self.carpts["roof"]
        out += self.sheen[..., None] * np.array([0.30, 0.38, 0.40], np.float32)
        sx = rx + 85 * math.sin(t * 1.4)
        put(out, cv2.resize(self.shadow, (170, 64)), sx, ry + 40, (0.0, 0.0, 0.0), 0.9, mode="dark")
        self.fog.apply(out, t, density=0.12)
        jit = 3.0 * math.sin(t * 40) * max(0.0, math.sin(t * 1.4 * 2)) ** 8
        return zoom(out, 1.55 + 0.05 * min(1.0, u / 3.0), rx, ry + 60 + jit)


class Folklore:
    """Paper card on black: the legend's name and where folklorists found it."""

    def __init__(self):
        self.bg = np.zeros((H, W, 3), np.float32) + np.array([0.02, 0.025, 0.028], np.float32)
        self.bg += light_map(H, W, 540, 820, 900, power=1.4)[..., None] * np.array([0.10, 0.09, 0.07], np.float32)

    def render(self, t, u):
        return self.bg.copy()


def build_orr(R):
    t_some = R.at("Some people")
    t_hang = R.at("Hangman's Road.")
    t_story = R.at("The story")
    t_died = R.at("died")
    t_he = R.at("He went")
    t_lock = R.at("lock the")
    t_all = R.at("All night,")
    t_scr = R.at("scraping across")
    t_dawn = R.at("At dawn,")
    t_look = R.at("look back.")
    t_shoes = R.at("It was")
    t_no = R.at("There's no")
    t_old = R.at("It's an")
    t_dbl = R.at("Double-tap")
    c1 = (R.end("Hangman's Road.") + t_story) / 2
    c2 = (R.end("doors.") + t_all) / 2
    c3 = (R.end("roof.") + t_dawn) / 2
    c4 = (R.end("night.", t_shoes) + t_no) / 2
    c5 = t_dbl - 0.12

    def d_road(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        if "l" not in ctx:
            ctx["l"] = lab("LA PORTE · WEST OF PINE LAKE")
        paste(f, ctx["l"], W / 2, 300)
        red_title(f, "HANGMAN'S ROAD", 120, t, -0.2)

    def d_car(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)
        typed(f, "LOCK THE DOORS.", t, t_lock - 0.05, 380, size=84, rate=0.045)

    def d_roof(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        bs.shade(f)

    def p_dawn(ctx):
        ctx["s"] = CarScene(dawn=True, t_look=t_look, t_shoes=t_shoes)
        ctx["l"] = lab("DAWN")

    def d_dawn(f, u, t, ctx):
        if t < t_shoes - 0.1:
            img = ctx["s"].render(t, u, z=(1.0 + 0.03 * min(1.0, u / 2.0), 560, 1100))
        else:
            k = ease((t - t_shoes + 0.1) / 1.4)
            img = ctx["s"].render(t, u, z=(1.03 + 0.25 * k, 640, 1100 - 420 * k))
            img *= 1 - 0.45 * k
        f.alpha_composite(to_pil(img))
        bs.shade(f)
        paste(f, ctx["l"], W / 2, 300, appear(t, c3 + 0.05, 0.3) * (1 - ease((t - t_look + 0.3) / 0.3)))
        if t >= t_look - 0.2:
            red_title(f, "DON'T LOOK BACK", 120, t, t_look - 0.05)

    def p_folk(ctx):
        ctx["s"] = Folklore()
        card = bs.aged_paper(900, 640, seed=23)
        d = ImageDraw.Draw(card)
        f1 = C.font("fell_sc", 64)
        f2 = C.font("typew", 40)
        tx = "The Boyfriend's Death"
        d.text(((900 - f1.getlength(tx)) / 2, 70), tx, font=f1, fill=(42, 30, 20, 255))
        d.line([(120, 168), (780, 168)], fill=(90, 70, 50, 200), width=3)
        lines = ["A legend told across Indiana", "for generations.", "", "Indiana State University",
                 "Folklore Archives:", "Lake County, 1970"]
        for i, ln in enumerate(lines):
            d.text(((900 - f2.getlength(ln)) / 2, 214 + i * 58), ln, font=f2, fill=(52, 40, 28, 255))
        ctx["card"] = card.rotate(-2.0, resample=Image.BICUBIC, expand=True)
        ctx["stamp"] = bs.stamp([("NO", 96), ("RECORD", 104)], color=(220, 58, 44))

    def d_folk(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u)))
        a = appear(t, c4 + 0.05, 0.35)
        paste(f, ctx["card"], W / 2, 760 + 30 * (1 - a), a)
        if t >= t_no + 0.3:
            k = appear(t, t_no + 0.3, 0.12)
            paste(f, scaled(ctx["stamp"], 1.0 + 1.0 * (1 - k)), W / 2 + 180, 1135, min(1.0, k * 1.2))
        bs.shade(f)
        bs.credit_line(f, "Source: Indiana State University Folklore Archives")

    def p_end(ctx):
        ctx["s"] = LakeRoad(sign=False)
        ctx["cta"] = C.DoubleTap("IF YOU HEARD IT", "growing up around La Porte", color1=(255, 120, 100),
                                 glow1=(140, 0, 0), kind1="bask", size1=110, y=520)

    def d_end(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u + 4.0)))
        bs.shade(f)
        ctx["cta"].draw(f, u)

    scenes = [C.Scene(0.0, c1, d_road, scene(LakeRoad)),
              C.Scene(c1, c2, d_car, scene(CarScene, t_died=t_died, t_walk=t_he)),
              C.Scene(c2, c3, d_roof, scene(RoofScrape)), C.Scene(c3, c4, d_dawn, p_dawn),
              C.Scene(c4, c5, d_folk, p_folk, flicker=0.0), C.Scene(c5, R.dur + 1, d_end, p_end, flicker=0.0)]
    atm = bs.Atmos(tint=(196, 204, 206), fog=0.08, vignette=0.58, grain=12, seed=7)
    film = C.Film(R, scenes, flashes=[], flicker=0.2, atmos=atm)

    import sfx as X
    n = int((R.dur + 0.5) * SR)
    wind = X.wind(R.dur + 0.5, seed=35, strength=0.7).mean(1)[:n]
    ev = [(wind, 0.0, 0.5, "bed"), (X.owl(seed=24).mean(1), 1.2, 0.35), ("hit", t_hang, 0.6), ("whoosh", c1, 0.5),
          (sputter(seed=3), t_died - 0.1, 0.8), (steps(2.6, seed=5), t_he, 0.45, "bed"), ("type", t_lock - 0.05, 0.8),
          (lock_click(), R.at("doors.") + 0.05, 0.9), ("whoosh", c2, 0.5), (scrape(c3 - c2 + 0.3, seed=7), c2 + 0.2, 0.9, "bed"),
          ("whoosh", c3, 0.5), (X.lp(X.siren(4.0, seed=12).mean(1), 1500), c3 + 0.1, 0.25, "bed"),
          ("hit", t_look - 0.05, 0.8), (X.heartbeat(3.0, bpm=72).mean(1), t_shoes, 0.6, "bed"),
          ("whoosh", c4, 0.5), ("hit", t_no + 0.3, 0.8), ("type", t_old, 0.5),
          ("pop", c5 + 0.12, 0.9), ("pop", c5 + 0.42, 0.9), ("hit", c5 + 0.5, 0.6)]
    return film, ev, haunt_music(R, seed=80, prog=9), TITLES["orr"]


# =============================================================================================== sound

def haunt_music(R, seed=60, prog=4):
    import sfx as X
    import audio as AU
    music = X.drone(R.dur + 1, seed=seed).mean(1) * 0.85
    chords = AU.PROG[prog]
    d = (R.dur - 0.5) / len(chords)
    pads = np.zeros(int((R.dur + 1) * SR), np.float32)
    for k, chord in enumerate(chords):
        p = X.pad(d + 3.0, [AU.N[cn] for cn in chord], seed=seed + 10 + k, attack=2.0, release=2.5).mean(1)
        i = int(max(0.0, k * d - 0.8) * SR)
        m = min(len(pads) - i, len(p))
        pads[i:i + m] += p[:m]
    music = music + pads * 0.8
    mot = AU.motif(6, 0.42)
    mot = mot.mean(1) if mot.ndim > 1 else mot
    i = int((R.dur - 3.6) * SR)
    m = min(len(music) - i, len(mot))
    music[i:i + m] += mot[:m] * 0.7
    return music


def whispers(dur, seed=4):
    import sfx as X
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    t = 0.2
    while t < dur - 0.8:
        m = int(r.uniform(0.35, 0.8) * SR)
        x = X.bp(r.normal(0, 1, m).astype(np.float32), r.uniform(1500, 2600), r.uniform(3400, 5200))
        e = np.sin(np.linspace(0, math.pi, m)) ** 1.5 * (0.6 + 0.4 * np.sin(np.linspace(0, r.uniform(8, 18), m)) ** 2)
        i = int(t * SR)
        out[i:i + m] += (x * e)[: n - i] * r.uniform(0.4, 1.0)
        t += r.uniform(0.5, 1.4)
    out = X.reverb(X.stereo(out / max(1e-6, np.abs(out).max()) * 0.5, 0.0, 1.0), rt=2.5, wet=0.6).mean(1)
    return out.astype(np.float32)


def sputter(seed=3):
    import sfx as X
    r = np.random.default_rng(seed)
    n = int(1.4 * SR)
    out = np.zeros(n, np.float32)
    t = 0.0
    gap = 0.07
    while t < 1.0:
        m = int(0.05 * SR)
        x = X.lp(r.normal(0, 1, m).astype(np.float32), 300) * np.exp(-np.linspace(0, 6, m))
        i = int(t * SR)
        out[i:i + m] += x * (1 - t)
        t += gap
        gap *= 1.18
    return (out / max(1e-6, np.abs(out).max()) * 0.8).astype(np.float32)


def steps(dur, seed=5):
    import sfx as X
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    t = 0.05
    k = 0
    while t < dur - 0.2:
        m = int(0.09 * SR)
        x = X.bp(r.normal(0, 1, m).astype(np.float32), 200, 1800) * np.exp(-np.linspace(0, 7, m))
        i = int(t * SR)
        out[i:i + m] += x * (1 - 0.8 * t / dur)
        t += 0.42
        k += 1
    return (out / max(1e-6, np.abs(out).max()) * 0.7).astype(np.float32)


def lock_click():
    import sfx as X
    r = np.random.default_rng(9)
    m = int(0.12 * SR)
    x = X.bp(r.normal(0, 1, m).astype(np.float32), 1800, 6000) * np.exp(-np.linspace(0, 12, m))
    x2 = np.sin(2 * np.pi * 900 * np.arange(m) / SR) * np.exp(-np.linspace(0, 20, m)) * 0.4
    return ((x + x2) / max(1e-6, np.abs(x + x2).max()) * 0.8).astype(np.float32)


def scrape(dur, seed=7):
    """Something slowly dragging across a car roof: a few long, rasping strokes."""
    import sfx as X
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    t = 0.1
    while t < dur - 0.6:
        L = r.uniform(0.7, 1.1)
        m = int(L * SR)
        tt = np.arange(m) / SR
        rate = 60 + 30 * np.sin(np.pi * tt / L)
        ph = np.cumsum(rate) / SR
        imp = (np.diff(np.floor(ph), prepend=0) > 0).astype(np.float32) * r.uniform(0.5, 1.0, m)
        x = X.bp(imp + 0.15 * r.normal(0, 1, m).astype(np.float32), 500, 3200)
        x *= np.sin(np.pi * tt / L) ** 0.7
        i = int(t * SR)
        out[i:i + m] += x[: n - i]
        t += L + r.uniform(0.15, 0.4)
    out = X.reverb(X.stereo(out / max(1e-6, np.abs(out).max()) * 0.7, 0.1), rt=0.7, wet=0.25).mean(1)
    return out.astype(np.float32)


# =============================================================================================== main

BUILD = {"posey": build_posey, "patton": build_patton, "orr": build_orr}


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
