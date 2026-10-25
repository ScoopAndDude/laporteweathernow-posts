"""Scene builders, part 5: Halloween today, La Porte, the ending."""
import math
import os

import cv2
import numpy as np
import skia

from core import (OW, OH, W, H, Canvas, Camera, rgb, mix, clamp01, smoothstep, sstep, ease, ease_out, fbm, add_spot,
                  poly_path, smooth_path, paint, lin, rad, ADD, blur, flicker, Noise1, Flame, Embers, Motes, Fog, AMBER,
                  GHOST, MOON, PAPER, INK, BLOOD, text_layer, paste, font, ROOT)
from art import (figure, hooded, comp, sky, hills, tree, grass, farmhouse, gravestones, fence, pumpkin, carve, candle,
                 candle_flame, rim_shape, sheet_ghost, vgrad)
from items import (night, dusk, hill, mist, ground, fog, flock, leaves, silhouette, porch, string_lights, town_row,
                   gas_lamp, street_lamp_modern, kids_walking, courthouse, EmberBed, DARK, RIM)
from interior import Light, light_scene, plaster, wood, falloff
from scene import Scene, Painted, Blend, Seq, flick, ramp, times, const, cropped
from cards import Block, TextScene, paper_card, PARCH, dark_bg, big_number
from lib1 import FOG
from lib2 import Overlaid


# ----------------------------------------------------------------------------- Halloween today

def modern_porch(dur, kids_speed=55):
    def build(ctx):
        ctx.bg = np.zeros((OH, OW, 3), np.float32)
        ctx.bg[:] = rgb("#05080a")
        lx, ly = porch(ctx, OW * 0.58, OH * 0.70, s=1.05, light_k=1.0)
        string_lights(ctx, ((OW * 0.02, OH * 0.12), (OW * 0.98, OH * 0.12)), n=26, sag=60, name="string")
        ctx.flush()
        for i, (fx, r) in enumerate(((0.44, 70), (0.50, 56), (0.76, 82), (0.84, 60))):
            ctx.lantern("pumpkin", OW * fx, OH * (0.70 + 0.04 * (i % 2)) - r * 0.7, r, face=i % 3, seed=90 + i)
        kids_walking(ctx, [dict(x=OW * 0.04, y=OH * 0.99, h=360, kind="ghost", bucket=True),
                           dict(x=OW * 0.13, y=OH * 1.0, h=400, kind="witch", bucket=True),
                           dict(x=OW * 0.21, y=OH * 0.99, h=330, kind="cape", bucket=True)], speed=kids_speed)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.5), (0.52, 0.52)), name="modern_porch")


class PeopleScene(Scene):
    """n figures; the first k light up one after another."""

    def __init__(self, dur, n=4, k=3, t0=0.6, label="About 3 in 4 Americans plan to celebrate"):
        super().__init__()
        self.dur, self.n, self.k, self.t0, self.label = dur, n, k, t0, label

    def build(self):
        self.bg = dark_bg(0)
        self.fog = Fog(seed=5, density=0.16, top=0.0, bottom=1.0, color="#6f9690", speed=12)
        self.icons = []
        for i in range(self.n):
            c = Canvas(300, 520)
            figure(c, 150, 500, 470, "#ffffff", arms=((10, 5), (10, 5)), dress=i % 2 == 1)
            self.icons.append(c.rgba()[..., 3])
        self.block = Block(self.label, "sans", 48, PAPER, W / 2, H * 0.86, t_in=self.t0 + 0.4 * self.k, fade=0.7)

    def render(self, t, u):
        self.ensure()
        f = self.bg.copy()
        self.fog.apply(f, t)
        for i, m in enumerate(self.icons):
            x = W / 2 + (i - (self.n - 1) / 2) * 300
            lit = sstep(self.t0 + 0.4 * i, self.t0 + 0.4 * i + 0.35, t) if i < self.k else 0.0
            col = rgb("#3a4a4c") * (1 - lit) + rgb(AMBER) * lit
            lay = np.zeros(m.shape + (4,), np.float32)
            lay[..., 3] = m
            lay[..., :3] = m[..., None] * col
            paste(f, lay, x, H * 0.45)
            if lit > 0:
                add_spot(f, x, H * 0.45, 110, rgb(AMBER), 0.10 * lit)
        self.block.draw(f, t)
        return f


class BarsScene(Scene):
    def __init__(self, dur, items, t0=0.4, unit="$", suffix=" billion", maxv=5.0):
        super().__init__()
        self.dur, self.items, self.t0, self.unit, self.suffix, self.maxv = dur, items, t0, unit, suffix, maxv

    def build(self):
        self.bg = dark_bg(1)
        self.fog = Fog(seed=6, density=0.16, top=0.0, bottom=1.0, color="#6f9690", speed=12)
        self.labels = [text_layer(name, "sans", 54, PAPER) for name, v, c, ts in self.items]
        self.cache = {}

    def render(self, t, u):
        self.ensure()
        f = self.bg.copy()
        self.fog.apply(f, t)
        for i, (name, v, c, ts) in enumerate(self.items):
            y = H * (0.36 + 0.26 * i)
            a = sstep(ts, ts + 0.4, t)
            paste(f, self.labels[i], W * 0.12, y - 70, a=a, anchor="lm")
            p = ease_out(sstep(ts + 0.2, ts + 1.6, t))
            x0, x1 = W * 0.12, W * 0.12 + p * (v / self.maxv) * W * 0.62
            if x1 > x0 + 2:
                cv2.rectangle(f, (int(x0), int(y - 26)), (int(x1), int(y + 26)), tuple(float(q) for q in rgb(c)), -1)
                add_spot(f, x1, y, 40, rgb(c), 0.25)
            txt = "%s%.1f%s" % (self.unit, v * p, self.suffix)
            lay = self.cache.get(txt)
            if lay is None:
                lay = text_layer(txt, "sans_x", 60, c)
                self.cache[txt] = lay
            paste(f, lay, x1 + 30, y, a=a, anchor="lm")
        return f


def witch_hat(cv, x, y, s, color):
    cv.ellipse(x, y, 230 * s, 44 * s, color)
    cv.c.drawPath(smooth_path([(x - 120 * s, y - 10 * s), (x - 60 * s, y - 200 * s), (x + 30 * s, y - 330 * s),
                               (x + 170 * s, y - 380 * s), (x + 80 * s, y - 300 * s), (x + 60 * s, y - 150 * s),
                               (x + 120 * s, y - 10 * s)], True), paint(color))
    cv.rect(x - 110 * s, y - 60 * s, x + 115 * s, y - 25 * s, "#8a3a1a")


def web(cv, x, y, r, color, width=3):
    spokes = 12
    for k in range(spokes):
        a = k / spokes * 2 * math.pi
        cv.line([(x, y), (x + math.cos(a) * r, y + math.sin(a) * r)], color, width)
    for ring in range(1, 8):
        rr = r * ring / 8
        pts = []
        for k in range(spokes + 1):
            a = k / spokes * 2 * math.pi
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
        for k in range(spokes):
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            mx += (x - mx) * 0.12
            my += (y - my) * 0.12
            p = skia.Path()
            p.moveTo(x0, y0)
            p.quadTo(mx, my, x1, y1)
            cv.c.drawPath(p, paint(color, stroke=width * 0.7))


def pumpkin_dog(cv, x, y, s=1.0, costume="#e0701e", fur="#1a1410"):
    """A dog sitting in a pumpkin costume, side view; (x, y) = floor under the dog."""
    for lx in (x - 110 * s, x - 60 * s, x + 60 * s, x + 110 * s):
        cv.rect(lx - 14 * s, y - 120 * s, lx + 14 * s, y, fur, r=10 * s)
    cv.c.drawPath(smooth_path([(x - 170 * s, y - 170 * s), (x - 250 * s, y - 230 * s), (x - 270 * s, y - 210 * s),
                               (x - 190 * s, y - 150 * s)], True), paint(fur))
    pumpkin(cv, x, y - 190 * s, 190 * s, seed=3, base=costume, squash=0.72)
    hx, hy = x + 190 * s, y - 330 * s
    cv.ellipse(hx, hy, 80 * s, 70 * s, fur)
    cv.c.drawPath(smooth_path([(hx + 40 * s, hy - 10 * s), (hx + 150 * s, hy + 10 * s), (hx + 150 * s, hy + 45 * s),
                               (hx + 40 * s, hy + 50 * s)], True), paint(fur))
    cv.circle(hx + 150 * s, hy + 18 * s, 14 * s, "#050505")
    cv.c.drawPath(smooth_path([(hx - 50 * s, hy - 40 * s), (hx - 70 * s, hy + 60 * s), (hx - 20 * s, hy + 10 * s)], True),
                  paint(mix(fur, "#000", 0.4)))
    cv.circle(hx + 30 * s, hy - 15 * s, 9 * s, "#f0e8d8")
    cv.circle(hx + 32 * s, hy - 15 * s, 5 * s, "#050505")
    # stem hat
    cv.rect(hx - 20 * s, hy - 110 * s, hx + 10 * s, hy - 60 * s, "#3d5a1c", r=6 * s)
    cv.ellipse(hx - 5 * s, hy - 62 * s, 60 * s, 14 * s, "#4a6a24")


class PanelsScene(Scene):
    def __init__(self, dur, times_=(0.6, 2.2, 3.6)):
        super().__init__()
        self.dur, self.times = dur, times_

    def build(self):
        self.bg = dark_bg(0)
        self.fog = Fog(seed=7, density=0.16, top=0.0, bottom=1.0, color="#6f9690", speed=12)
        icons = []
        c = Canvas(560, 560)
        witch_hat(c, 280, 430, 1.0, "#1e1428")
        icons.append(c.rgba())
        c = Canvas(560, 560)
        web(c, 280, 280, 240, "#d8dcda", 3)
        c.line([(280, 0), (280, 230)], "#d8dcda", 2)
        c.ellipse(280, 250, 26, 32, "#1a1a1a")
        icons.append(c.rgba())
        c = Canvas(560, 560)
        pumpkin_dog(c, 260, 520, 0.95, fur="#3a2e24")
        icons.append(c.rgba())
        self.icons = icons
        self.blocks = []
        for i, (top, bot) in enumerate((("ADULTS", "a witch"), ("KIDS", "Spider-Man"), ("PETS", "a pumpkin"))):
            x = W * (0.2 + 0.3 * i)
            self.blocks.append(Block(top, "sans", 34, AMBER, x, H * 0.76, t_in=self.times[i] + 0.2, fade=0.5, tracking=0.3))
            self.blocks.append(Block(bot, "fell", 70, PAPER, x, H * 0.85, t_in=self.times[i] + 0.35, fade=0.5))

    def render(self, t, u):
        self.ensure()
        f = self.bg.copy()
        self.fog.apply(f, t)
        for i, lay in enumerate(self.icons):
            a = sstep(self.times[i], self.times[i] + 0.5, t)
            if a > 0:
                x = W * (0.2 + 0.3 * i)
                add_spot(f, x, H * 0.40, 200, rgb("#ff9a4a"), 0.10 * a)
                L = lay
                if i == 0:
                    L = lay.copy()
                    L[..., :3] = L[..., 3:4] * rgb("#2a1e36") + L[..., :3] * 0.6
                paste(f, cv2.resize(L, (430, 430)), x, H * 0.40, a=a)
        for b in self.blocks:
            b.draw(f, t)
        return f


def dog_porch(dur):
    def build(ctx):
        ctx.bg = np.zeros((OH, OW, 3), np.float32)
        ctx.bg[:] = rgb("#05080a")
        lx, ly = porch(ctx, OW * 0.30, OH * 0.80, s=1.1, light_k=1.0)
        ctx.flush()
        dog = Canvas()
        pumpkin_dog(dog, OW * 0.62, OH * 0.97, 1.3, fur="#2a2018")
        lay = dog.rgba()
        lm = falloff(lx, ly, 600, 2800)[..., None]
        lay[..., :3] *= (0.12 + 1.3 * lm) * rgb("#ffe0b0")[None, None, :]
        comp(ctx.bg, lay)
        ctx.lantern("pumpkin", OW * 0.86, OH * 0.90, 90, face=2, seed=99)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.55, 0.6), (0.6, 0.62)), name="dog_porch")


# ----------------------------------------------------------------------------- La Porte

def laporte_dusk(dur, dark=0.45, lamps_t=None):
    def build(ctx):
        dusk(ctx, sun=None, seed=371, dark=dark, clouds=0.3)
        town_row(ctx, OH * 0.80, -40, OW * 0.36, seed=31, hmin=200, hmax=360, lit_p=0.45, color="#08080c", rim="#4a3a4a")
        town_row(ctx, OH * 0.80, OW * 0.66, OW + 40, seed=32, hmin=200, hmax=380, lit_p=0.45, color="#08080c", rim="#4a3a4a")
        courthouse(ctx, OW * 0.35, OH * 0.80, s=1.0)
        ctx.flush()
        ground(ctx, OH * 0.80, "#0c0c10", "#040406")
        on = ramp(lamps_t, lamps_t + 0.4) if lamps_t is not None else const(1)
        for fx in (0.10, 0.30, 0.70, 0.90):
            street_lamp_modern(ctx, OW * fx, OH * 0.97, s=1.1, k=1.0, name="sl%d" % int(fx * 100))
            ctx.lights["sl%d" % int(fx * 100)][1] = on
        for fx in (0.04, 0.96):
            tree(ctx.cv, OW * fx, OH * 0.95, 700, seed=int(fx * 100) + 7, color="#050508", spread=0.6)
        leaves(ctx, 20, seed=9, wind=140)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.5, 0.5), (0.5, 0.45)), name="laporte_dusk")


def farmhouse_fire(dur):
    def build(ctx):
        night(ctx, moon=None, seed=381, clouds=0.6, stops=[(0, "#040303"), (0.6, "#160c08"), (1, "#3a180c")])
        hill(ctx, OH * 0.66, 30, 600, "#120a08", 51, haze=("#5a2a18", 0.5, 120))
        ground(ctx, OH * 0.74, "#140a06", "#030202")
        cv = ctx.cv
        x, y = OW * 0.36, OH * 0.80
        farmhouse(cv, ctx.light("win", flick(5, 0.25, 2.0)), x, y, s=1.35, lit=(1, 1, 1, 1, 1), window="#ff6a1a",
                  porch=False)
        tree(cv, OW * 0.10, OH * 0.92, 760, seed=111, spread=0.6, color="#030202")
        tree(cv, OW * 0.92, OH * 0.90, 680, seed=112, spread=0.6, color="#030202")
        ctx.flush()
        fl = [Flame(420, 620, seed=61 + k, speed=0.9, width=0.6, wobble=0.5) for k in range(4)]
        spots = [(x + 120, y - 330), (x + 300, y - 420), (x + 480, y - 360), (x + 620, y - 260)]
        lc = ctx.light("blaze", flick(62, 0.18, 1.3))
        lc.glow(x + 340, y - 350, 1100, "#ff6a1a", 0.6)
        lc.ellipse(x + 340, y + 40, 900, 120, "#ff6a1a", 0.15, blur=40)
        em = Embers(80, x + 50, x + 700, y - 450, rise=420, spread=120, seed=63)
        smoke = cv2.resize(fbm(OH // 4, OW // 4, scale=40, octaves=5, seed=64), (OW, OH))
        smoke = smoothstep(0.45, 0.85, smoke)
        cone = np.zeros((OH, OW), np.float32)
        yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
        cone = clamp01(1 - np.abs(xx - (x + 360 + (y - 400 - yy) * 0.25)) / (200 + (y - 400 - yy).clip(0) * 0.8)) * \
            smoothstep(y - 300, y - 700, yy)

        def draw(buf, t):
            for k, (f, (sx, sy)) in enumerate(zip(fl, spots)):
                img = f.render(t + k, intensity=1.0)
                hh, ww = img.shape[:2]
                y0, x0 = int(sy - hh * 0.75), int(sx - ww / 2)
                buf[y0:y0 + hh, x0:x0 + ww] += img
            em.draw(buf, t, 1.0)
            sh = np.roll(smoke, -int(t * 40), axis=0)
            dark = (sh * cone * 0.6)[..., None]
            buf *= (1 - dark)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.5), (0.52, 0.48)), name="farmhouse_fire")


def portrait_frame(dur):
    def build(ctx):
        alb = plaster(OH, OW, "#4a3a30", seed=81)
        cv = Canvas()
        mx, my = OW * 0.5, OH * 0.45
        cv.ellipse(mx, my, 330, 410, None, shader=rad((mx - 100, my - 130), 520, [("#f2d98a", 1), ("#8a6a2a", 1), ("#3a2a0a", 1)], [0, 0.5, 1]))
        cv.ellipse(mx, my, 290, 370, "#1a120c")
        cv.ellipse(mx, my, 270, 350, "#3a3028")
        bust = smooth_path([(mx - 240, my + 350), (mx - 220, my + 200), (mx - 110, my + 140), (mx + 110, my + 140), (mx + 220, my + 200),
                            (mx + 240, my + 350)], True)
        cv.c.save()
        cv.c.clipPath(skia.Path.Oval(skia.Rect(mx - 270, my - 350, mx + 270, my + 350)), doAntiAlias=True)
        cv.c.drawPath(bust, paint("#0c0806"))
        cv.rect(mx - 40, my + 70, mx + 40, my + 150, "#0c0806")
        cv.ellipse(mx, my - 10, 105, 135, "#0c0806")
        cv.ellipse(mx + 10, my - 150, 70, 50, "#0c0806")
        cv.c.restore()
        cv.rect(mx - 270, my + 430, mx + 270, my + 500, "#8a6a2a", r=8)
        comp(alb, cv.rgba())
        ctx.flush()
        lay = text_layer("BELLE GUNNESS", "old_b", 36, "#2a1a08", tracking=0.18)
        paste(alb, lay, mx, my + 466)
        light_scene(ctx, alb, [Light("c", OW * 0.5, OH * 0.95, 520, 2600, "#ffb066", 1.5, flick(82, 0.1, 0.9))],
                    ambient=("#1d2c33", 0.08))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.12, (0.5, 0.5), (0.5, 0.45)), name="portrait")


def town_night(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.80, OH * 0.15, 40), seed=391, clouds=0.5)
        town_row(ctx, OH * 0.72, -40, OW + 40, seed=41, hmin=240, hmax=460, lit_p=0.2, color="#05080a")
        ctx.flush()
        ground(ctx, OH * 0.72, "#10181a", "#040607")
        for fx in (0.2, 0.55, 0.85):
            street_lamp_modern(ctx, OW * fx, OH * 0.95, s=1.1)
        leaves(ctx, 18, seed=12, wind=120)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.55), (0.5, 0.52)), fog=dict(FOG, density=0.3),
                   name="town_night")


def little_belles(dur, speed=60):
    def build(ctx):
        night(ctx, moon=(OW * 0.15, OH * 0.15, 40), seed=401, clouds=0.4)
        town_row(ctx, OH * 0.70, -40, OW + 40, seed=42, hmin=240, hmax=420, lit_p=0.35, color="#06080a")
        ctx.flush()
        ground(ctx, OH * 0.70, "#12181a", "#040607")
        street_lamp_modern(ctx, OW * 0.55, OH * 0.92, s=1.2)
        kids_walking(ctx, [dict(x=OW * 0.05, y=OH * 0.98, h=330, kind="belle", bucket=True),
                           dict(x=OW * 0.16, y=OH * 0.99, h=360, kind="belle", bucket=True),
                           dict(x=OW * 0.26, y=OH * 0.98, h=310, kind="belle", bucket=True),
                           dict(x=OW * 0.36, y=OH * 1.0, h=520, kind="adult", hat="brim")], speed=speed)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.05, (0.5, 0.55), (0.52, 0.55)), fog=dict(FOG, density=0.18),
                   name="little_belles")


def entrepreneur_card(dur):
    blocks = [Block("“our entrepreneur”", "fell_it", 150, INK, W / 2, H * 0.42, t_in=0.3, fade=0.9),
              Block("— a La Porte County Historical Society Museum curator,\non Belle Gunness (as quoted by Crime Library)",
                    "type", 38, "#5a4a32", W / 2, H * 0.68, t_in=1.2, fade=0.9, line_gap=1.5)]
    return paper_card(blocks, dur, seed=4)


def porch_party(dur):
    def build(ctx):
        ctx.bg = np.zeros((OH, OW, 3), np.float32)
        ctx.bg[:] = rgb("#05080a")
        lx, ly = porch(ctx, OW * 0.5, OH * 0.72, s=1.0, light_k=0.9)
        string_lights(ctx, ((OW * 0.0, OH * 0.10), (OW * 1.0, OH * 0.14)), n=28, sag=70, name="s1")
        ctx.flush()
        cv = ctx.cv
        # paper skeleton on the wall
        sx, sy = OW * 0.20, OH * 0.22
        bone = "#d8d4c8"
        cv.ellipse(sx, sy, 34, 40, bone)
        cv.ellipse(sx - 12, sy - 2, 9, 10, "#05080a")
        cv.ellipse(sx + 12, sy - 2, 9, 10, "#05080a")
        cv.line([(sx, sy + 40), (sx, sy + 210)], bone, 10)
        for k in range(5):
            cv.line([(sx - 50 + k * 4, sy + 70 + k * 24), (sx + 50 - k * 4, sy + 70 + k * 24)], bone, 6)
        cv.line([(sx, sy + 60), (sx - 80, sy + 150), (sx - 60, sy + 240)], bone, 8)
        cv.line([(sx, sy + 60), (sx + 80, sy + 150), (sx + 90, sy + 230)], bone, 8)
        cv.line([(sx, sy + 210), (sx - 40, sy + 340), (sx - 50, sy + 450)], bone, 9)
        cv.line([(sx, sy + 210), (sx + 40, sy + 340), (sx + 45, sy + 450)], bone, 9)
        web(cv, OW * 0.86, OH * 0.06, 180, "#c8ccc8", 2)
        ctx.flush()
        for i, (fx, r) in enumerate(((0.33, 80), (0.40, 62), (0.62, 90), (0.70, 64), (0.30, 54))):
            ctx.lantern("pumpkin", OW * fx, OH * (0.72 + 0.06 * (i // 4)) - r * 0.7, r, face=i % 3, seed=100 + i)
        pl = ctx.plane(1.0)
        for i, (fx, h, kind) in enumerate(((0.80, 560, "witch"), (0.88, 380, "cape"), (0.12, 600, "adult"))):
            figure(pl.cv, OW * fx, OH * 1.02, h, "#030405", child=kind == "cape", hat="witch" if kind == "witch" else "top",
                   dress=kind == "witch", cape=kind == "cape", arms=((20, 30), (150, 20)) if kind == "adult" else ((10, 5), (40, 60)))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.5), (0.5, 0.52)), name="porch_party")


class SkyClock(Scene):
    """Halloween night in La Porte: sunset 5:44 PM, dark by 6:46, moonrise about 10:40."""

    def __init__(self, dur, t_sun=1.0, t_dark=3.2, t_moon=5.0):
        super().__init__()
        self.dur, self.t_sun, self.t_dark, self.t_moon = dur, t_sun, t_dark, t_moon

    def build(self):
        self.day = vgrad(H, W, [(0, "#1a2a4a"), (0.6, "#7a5a6a"), (0.72, "#e09a6a"), (1, "#e8a070")])
        self.nite = vgrad(H, W, [(0, "#03060a"), (0.72, "#0b1519"), (1, "#0e1a1e")])
        from art import stars_only
        self.stars = np.zeros((H, W, 3), np.float32)
        stars_only(self.stars, 300, 4, H * 0.68)
        self.ground = vgrad(H - int(H * 0.72), W, [(0, "#0a0c10"), (1, "#020304")])
        c = Canvas(W, H)
        r = np.random.default_rng(3)
        x = 0
        while x < W:
            w_ = r.uniform(60, 160)
            h_ = r.uniform(30, 120)
            c.rect(x, H * 0.72 - h_, x + w_, H * 0.72 + 2, "#05070a")
            x += w_
        tree(c, W * 0.12, H * 0.73, 260, seed=5, color="#05070a")
        tree(c, W * 0.86, H * 0.73, 220, seed=6, color="#05070a")
        self.skyline = c.rgba()
        self.blocks = [Block("SATURDAY, OCT. 31  ·  LA PORTE, INDIANA", "sans", 30, GHOST, W / 2, H * 0.10, t_in=0.2, fade=0.7,
                             tracking=0.25, alpha=0.9),
                       Block("Sunset\n5:44 PM", "fell", 60, PAPER, W * 0.22, H * 0.86, t_in=self.t_sun + 0.4, fade=0.6),
                       Block("Dark by\n6:46 PM", "fell", 60, PAPER, W * 0.50, H * 0.86, t_in=self.t_dark + 0.2, fade=0.6),
                       Block("Moonrise\nabout 10:40 PM", "fell", 60, PAPER, W * 0.78, H * 0.86, t_in=self.t_moon + 0.6,
                             fade=0.6)]

    def render(self, t, u):
        self.ensure()
        d = sstep(self.t_sun, self.t_dark + 0.6, t)
        f = self.day * (1 - d) + self.nite * d
        f += self.stars * sstep(self.t_dark - 0.6, self.t_dark + 0.8, t)
        hz = H * 0.72
        # sun sinking
        sp = ease(sstep(0, self.t_sun + 0.8, t))
        sx, sy = W * 0.24, hz - 110 + sp * 160
        if sy < hz + 60:
            add_spot(f, sx, sy, 160, (1.0, 0.6, 0.3), 0.35 * (1 - d))
            cv2.circle(f, (int(sx), int(sy)), 46, (1.0, 0.82, 0.55), -1, cv2.LINE_AA)
        # moon rising (waning gibbous, lit on the left)
        mp = ease(sstep(self.t_moon, self.t_moon + 1.6, t))
        if mp > 0:
            mx, my = W * 0.78, hz + 60 - mp * 260
            moon = np.zeros((140, 140, 4), np.float32)
            yy, xx = np.mgrid[0:140, 0:140].astype(np.float32)
            dd = np.sqrt((xx - 70) ** 2 + (yy - 70) ** 2)
            disc = smoothstep(46, 44, dd)
            lit = disc * np.where((xx - 70) < 45 * 0.45 * np.sqrt(np.clip(1 - ((yy - 70) / 45) ** 2, 0, 1)), 1.0, 0.18)
            moon[..., :3] = lit[..., None] * rgb(MOON)
            moon[..., 3] = disc
            add_spot(f, mx, my, 120, rgb("#8fb0b0"), 0.25 * mp)
            paste(f, moon, mx, my, a=mp)
        lay = self.skyline
        f *= (1 - lay[..., 3:4])
        f += lay[..., :3]
        f[int(hz):] = self.ground
        for b in self.blocks:
            b.draw(f, t)
        return f


# ----------------------------------------------------------------------------- the ending

def outro_porch(dur, porch_off=None, blow_t=None):
    def build(ctx):
        night(ctx, moon=(OW * 0.80, OH * 0.16, 44), seed=411, clouds=0.5)
        hill(ctx, OH * 0.62, 30, 600, "#0e1c20", 61, haze=("#2a4448", 0.6, 100))
        town_row(ctx, OH * 0.66, OW * 0.55, OW + 40, seed=51, hmin=120, hmax=240, lit_p=0.3, color="#05080a",
                 name="houses")
        ctx.flush()
        ground(ctx, OH * 0.66, "#0a1316", "#030607")
        tree(ctx.cv, OW * 0.25, OH * 0.70, 600, seed=121, spread=0.6)
        # porch rail across the foreground
        cv = ctx.cv
        cv.rect(0, OH * 0.70, OW, OH * 0.74, "#120e0c")
        for k in range(14):
            x = k * OW / 13
            cv.rect(x - 14, OH * 0.74, x + 14, OH, "#0e0a08")
        cv.rect(0, OH * 0.66, OW * 0.12, OH, "#100c0a")
        ctx.flush()
        off = (lambda t: 1 - sstep(porch_off, porch_off + 0.15, t)) if porch_off is not None else const(1)
        lc = ctx.light("porchlight", off)
        lc.glow(OW * 0.06, OH * 0.30, 900, "#ffe2a8", 0.30)
        lc.rect(0, OH * 0.70, OW * 0.6, OH * 0.74, "#ffe2a8", 0.06)
        lc.glow(OW * 0.06, OH * 0.28, 120, "#fff2d0", 0.6)
        ctx.lights["houses"][1] = off
        nz = Noise1(131)

        def jack_fn(t):
            k = flicker(t, 132, 0.14, 1.2)
            if blow_t is not None and t > blow_t:
                d = t - blow_t
                k *= max(0.0, 1 - d / 0.7) * (0.6 + 0.4 * abs(math.sin(d * 25)))
            return k
        ctx.lantern("pumpkin", OW * 0.58, OH * 0.70 - 190 * 0.72, 190, face=0, seed=133, fn=jack_fn, skin_k=0.7)
        if blow_t is not None:
            def smoke(buf, t):
                d = t - blow_t
                if 0.3 < d < 6:
                    for k in range(14):
                        tt = d - k * 0.12
                        if tt <= 0:
                            continue
                        x = OW * 0.58 + math.sin(tt * 2.2 + k) * 20 * tt
                        y = OH * 0.70 - 300 - tt * 70
                        add_spot(buf, x, y, 12 + tt * 12, (0.6, 0.62, 0.62), 0.05 * math.exp(-tt * 0.5))
            ctx.dyn.append(smoke)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.12, (0.55, 0.55), (0.58, 0.56)), fog=dict(FOG, density=0.22),
                   name="outro_porch")


class EndCard(Scene):
    def __init__(self, dur, t0=0.3):
        super().__init__()
        self.dur, self.t0 = dur, t0

    def build(self):
        self.bg = dark_bg(0)
        self.fog = Fog(seed=9, density=0.22, top=0.0, bottom=1.0, color="#6f9690", speed=14)
        self.em = Embers(24, 100, W - 100, H + 30, rise=110, spread=80, life=(5, 9), size=(1.0, 2.0), seed=12)
        logo = cv2.imread(os.path.join(ROOT, "doc", "logo-512.png"))[..., ::-1].astype(np.float32) / 255
        s = 360
        logo = cv2.resize(logo, (s, s), interpolation=cv2.INTER_AREA)
        c = Canvas(s, s)
        c.rect(0, 0, s, s, "#ffffff", r=40)
        m = c.rgba()[..., 3:4]
        self.logo = np.concatenate([logo * m, m], axis=2)
        self.blocks = [Block("Happy Halloween", "black", 120, "#f3e6c8", W * 0.30, H * 0.70, t_in=self.t0 + 0.6, fade=1.0,
                             glow="#ff7a1a", glow_a=0.5),
                       Block("laporteweathernow.com", "sans", 44, GHOST, W * 0.30, H * 0.82, t_in=self.t0 + 1.2, fade=0.8,
                             tracking=0.04),
                       Block("Watch next", "sans", 30, "#9fb8b2", W * 0.74, H * 0.18, t_in=self.t0 + 1.6, fade=0.8,
                             tracking=0.3)]

    def render(self, t, u):
        self.ensure()
        f = self.bg.copy()
        self.fog.apply(f, t)
        self.em.draw(f, t, 0.6)
        a = sstep(self.t0, self.t0 + 0.8, t)
        add_spot(f, W * 0.30, H * 0.36, 260, rgb("#ff7a1a"), 0.10 * a)
        paste(f, self.logo, W * 0.30, H * 0.36, a=a)
        for b in self.blocks:
            b.draw(f, t)
        return f
