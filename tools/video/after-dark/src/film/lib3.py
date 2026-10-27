"""Scene builders, part 3: fortunes and omens, crossing the ocean, the prank years."""
import math

import cv2
import numpy as np
import skia

from core import (OW, OH, W, H, Canvas, Camera, rgb, mix, clamp01, smoothstep, sstep, ease, ease_out, fbm, add_spot,
                  poly_path, smooth_path, paint, lin, rad, ADD, blur, flicker, Noise1, Flame, Embers, Motes, Fog, AMBER,
                  GHOST, MOON, PAPER, INK, BLOOD, text_layer, paste, font)
from art import (figure, hooded, comp, sky, hills, tree, grass, reeds, farmhouse, church, gravestones, fence, pumpkin,
                 carve, turnip, candle, candle_flame, rim_shape, jack_face, sheet_ghost, lancet, vgrad, skull,
                 lantern_parts)
from items import (EmberBed, night, dusk, hill, mist, ground, fog, bonfire, distant_fires, flock, wisps, ghosts, leaves,
                   cottage, gate, signpost, red_eyes, stone_wall, silhouette, porch, string_lights, town_row, gas_lamp,
                   sea, tall_ship, rain, lightning, pumpkin_field, DARK, RIM)
from interior import (Light, light_scene, plaster, wood, stone_blocks, table_top, fireplace, chair, plate, cup, jug, bowl,
                      soul_cake, falloff, hazelnut, saucer, mirror, clock, logs)
from scene import Scene, Painted, Blend, Seq, flick, ramp, times, const, cropped
from cards import Block, TextScene, paper_card, PARCH, map_scene, stamp, newsprint_texture, paper_texture
from lib1 import FOG, pulse
from lib2 import Overlaid


# ----------------------------------------------------------------------------- fortunes

def parlor(dur):
    def build(ctx):
        alb = plaster(OH, OW, "#5e4c3a", seed=11)
        alb[int(OH * 0.84):] = wood(OH - int(OH * 0.84), OW, "#3a2a1c", seed=12, along="x", boards=4)
        cv = Canvas()
        fx, fy = OW * 0.42, OH * 0.84
        fireplace(cv, fx, fy, 760, 560, seed=7, stone="#7a7064")
        logs(cv, fx, fy - 6, 260)
        cpos = clock(cv, OW * 0.42, OH * 0.84 - 560 - 40, s=1.0)
        cv.rect(OW * 0.78, OH * 0.20, OW * 0.92, OH * 0.56, "#2e1e12")
        cv.rect(OW * 0.79, OH * 0.22, OW * 0.91, OH * 0.54, "#0b1418")
        # apples and nuts on the hearth
        r = np.random.default_rng(4)
        for i in range(5):
            ax = fx - 330 + i * 34 + r.uniform(-6, 6)
            cv.circle(ax, fy + 4, 26, "#8a1a12")
            cv.circle(ax - 8, fy - 6, 7, "#ff9a8a", 0.4)
        for i in range(9):
            hazelnut(cv, fx + 250 + r.uniform(-60, 60), fy + 10 + r.uniform(-8, 8), 13, rot=r.uniform(-40, 40))
        # armchair silhouette
        cv.c.drawPath(smooth_path([(OW * 0.06, OH), (OW * 0.05, OH * 0.55), (OW * 0.12, OH * 0.48), (OW * 0.20, OH * 0.55),
                                   (OW * 0.21, OH * 0.70), (OW * 0.25, OH * 0.72), (OW * 0.26, OH)], True), paint("#2a1a12"))
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("fire", fx, fy - 120, 360, 2400, "#ff8a3a", 1.9, flick(15, 0.2, 1.0)),
                               Light("moon", OW * 0.85, OH * 0.38, 300, 1600, "#9fc4d0", 0.45, const(1))],
                    ambient=("#1d2c33", 0.13))
        mc = ctx.light("moon")
        mc.rect(OW * 0.79, OH * 0.22, OW * 0.91, OH * 0.54, "#2e4650", 0.9)
        mc.rect(OW * 0.849, OH * 0.22, OW * 0.851 + 4, OH * 0.54, "#000000")
        fl = Flame(280, 340, seed=21, speed=0.9, width=0.62)
        bed = EmberBed(fx, fy - 16, 300, 44, seed=8)

        def draw(buf, t):
            bed.draw(buf, t, 0.8)
            f = fl.render(t, intensity=0.85)
            x0, y0 = int(fx - 140), int(fy - 340 + 4)
            buf[y0:y0 + 340, x0:x0 + 280] += f
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.48, 0.55), (0.45, 0.6)), name="parlor")


def burns_card(dur, t_quote=3.6):
    blocks = [Block("ROBERT BURNS · 1785", "sans", 30, "#5a4a32", W / 2, 250, t_in=0.3, fade=0.8, tracking=0.3),
              Block("Halloween", "fell", 170, INK, W / 2, 390, t_in=0.6, fade=1.0),
              Block("“Upon that night, when fairies light…”", "fell_it", 74, BLOOD, W / 2, 660,
                    t_in=t_quote, type_cps=14)]

    def rule(frame, t, u):
        a = sstep(0.8, 1.6, t)
        if a > 0:
            cv2.line(frame, (int(W / 2 - 160), 500), (int(W / 2 + 160), 500), tuple(float(c) * a for c in rgb("#8a7a5a")), 2,
                     cv2.LINE_AA)
    return paper_card(blocks, dur, seed=2, extra=[rule])


def kale_plant(cv, x, y, h, color="#060a08", seed=0):
    r = np.random.default_rng(seed)
    cv.line([(x, y), (x + r.normal(0, 6), y - h)], color, max(3, h * 0.04))
    for k in range(7):
        f = 0.35 + 0.65 * k / 6
        side = 1 if k % 2 else -1
        ly = y - h * f
        lw = h * (0.32 - 0.2 * f)
        cv.c.drawPath(smooth_path([(x, ly), (x + side * lw * 0.5, ly - lw * 0.45), (x + side * lw, ly - lw * 0.2),
                                   (x + side * lw * 0.85, ly + lw * 0.1), (x + side * lw * 0.4, ly + lw * 0.12)], True),
                      paint(color))
    cv.circle(x, y - h * 1.02, h * 0.12, color)


def kale_garden(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.72, OH * 0.18, 52), seed=211, clouds=0.45)
        hill(ctx, OH * 0.58, 30, 600, "#0e1c20", 30, haze=("#2a4448", 0.6, 100))
        cottage(ctx, OW * 0.08, OH * 0.64, s=0.7, name="cot")
        mist(ctx, OH * 0.63, 40, "#7fa39e", 0.32, seed=25)
        ground(ctx, OH * 0.64, "#0a1416", "#030607")
        for row in range(4):
            y = OH * (0.68 + row * 0.08)
            hh = 70 + row * 40
            for i in range(14 - row * 2):
                x = (i + 0.5 + 0.3 * (row % 2)) * OW / (14 - row * 2)
                if abs(x - OW * 0.55) < 200 and row == 2:
                    continue
                kale_plant(ctx.cv, x, y, hh, seed=row * 50 + i)
        # two young people pulling a stalk together
        figure(ctx.cv, OW * 0.50, OH * 0.86, 330, "#030405", dress=True, arms=((60, 20), (40, 30)), lean=0.15, bonnet=True)
        figure(ctx.cv, OW * 0.60, OH * 0.87, 350, "#030405", coat=True, hat="cap", arms=((50, 20), (20, 10)), lean=0.1)
        kale_plant(ctx.cv, OW * 0.555, OH * 0.80, 130, seed=99)
        grass(ctx.cv, OH, 0, OW, "#020405", n=300, hmin=15, hmax=40, seed=25)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.55), (0.53, 0.58)), fog=dict(FOG, density=0.22),
                   name="kale_garden")


def nuts_fire(dur, jump_t=6.0):
    def build(ctx):
        alb = stone_blocks(OH, OW, "#6a5e52", seed=13, bh=90, bw=(160, 260))
        alb[int(OH * 0.70):] = stone_blocks(OH - int(OH * 0.70), OW, "#7a6e60", seed=14, bh=110, bw=(240, 380))
        alb[int(OH * 0.70):int(OH * 0.71)] *= 0.4
        cv = Canvas()
        cv.rect(OW * 0.15, OH * 0.12, OW * 0.85, OH * 0.70, "#0e0a08")
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("fire", OW * 0.5, OH * 0.55, 420, 2400, "#ff8a3a", 2.0, flick(16, 0.2, 1.1))],
                    ambient=("#1d2c33", 0.08))
        flames = [Flame(520, 720, seed=31, speed=0.85, width=0.6), Flame(360, 520, seed=32, speed=1.0, width=0.55)]
        bed = EmberBed(OW * 0.5, OH * 0.66, 900, 90, seed=11)
        # the two nuts are sprites so one can jump
        sprite = Canvas(180, 180)
        hazelnut(sprite, 90, 90, 62)
        nut = sprite.rgba()
        nut[..., :3] *= rgb("#ffcf9a")[None, None, :] * 1.15
        n1 = (OW * 0.45, OH * 0.765)
        n2 = (OW * 0.55, OH * 0.765)

        def draw(buf, t):
            bed.draw(buf, t, 1.0)
            for k, fl in enumerate(flames):
                f = fl.render(t + k * 3, intensity=0.95)
                fh, fw = f.shape[:2]
                x0 = int(OW * (0.5 + (k - 0.5) * 0.18) - fw / 2)
                y0 = int(OH * 0.68 - fh)
                buf[y0:y0 + fh, x0:x0 + fw] += f
            k_ = flicker(t, 16, 0.2, 1.1)
            for i, (x, y) in enumerate((n1, n2)):
                if i == 1 and t > jump_t:
                    d = t - jump_t
                    p = min(1.0, d / 0.55)
                    x = x + 260 * p
                    y = y - 140 * math.sin(math.pi * p) + (40 * p)
                    if d < 0.3:
                        add_spot(buf, n2[0], n2[1] - 10, 30, (1, 0.7, 0.3), 1.2 * (0.3 - d))
                lay = nut.copy()
                lay[..., :3] *= (0.55 + 0.45 * k_)
                paste(buf, lay, x, y)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.04, 1.14, (0.5, 0.62), (0.5, 0.66)), name="nuts_fire")


def candle_gutter(dur):
    def build(ctx):
        alb = plaster(OH, OW, "#4a3c30", seed=17)
        cv = Canvas()
        cv.rect(OW * 0.36, OH * 0.78, OW * 0.64, OH * 0.80, "#2a1a10")
        tip = candle(cv, OW * 0.5, OH * 0.78, 300, 74, color="#c8bba0")
        comp(alb, cv.rgba())
        fade = ramp(dur * 0.35, dur * 0.95, 1.0, 0.25)
        light_scene(ctx, alb, [Light("c", tip[0], tip[1], 360, 2200, "#ffb066", 1.6, times(fade, flick(18, 0.25, 2.2)))],
                    ambient=("#1d2c33", 0.06))
        nz = Noise1(19)

        def draw(buf, t):
            g = 1.0 + 2.5 * sstep(dur * 0.3, dur * 0.7, t)
            k = fade(t) * (0.8 + 0.2 * nz(t, 6))
            candle_flame(buf, tip[0], tip[1], 16 * (0.7 + 0.3 * k), t * g, seed=5, k=k)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.05, 1.15), name="candle_gutter")


def saucers(dur, times_=(2.0, 4.0, 7.0), hand_t=7.2):
    xs = [OW * 0.27, OW * 0.50, OW * 0.73]
    contents = ["ring", "coin", "clay"]

    def build(ctx):
        alb = plaster(OH, OW, "#4a3c30", seed=22) * 0.6
        table_top(alb, OH * 0.30, OH, "#5a3a22", seed=21)
        cv = Canvas()
        for x, c in zip(xs, contents):
            saucer(cv, x, OH * 0.66, 190, content=c)
        comp(alb, cv.rgba())
        lights = [Light("s%d" % i, x, OH * 0.55, 260, 900, "#ffd8a0", 1.8, times(ramp(times_[i], times_[i] + 0.6), const(1)))
                  for i, x in enumerate(xs)]
        light_scene(ctx, alb, lights, ambient=("#24343c", 0.12))
        # a hand reaching down toward the last saucer
        pl = ctx.plane(1.0)
        hx, hy = xs[2] + 40, OH * 0.40
        pl.cv.c.drawPath(smooth_path([(hx - 70, -40), (hx + 70, -40), (hx + 60, hy - 60), (hx - 50, hy - 50)], True),
                         paint("#120c0a"))
        pl.cv.c.drawPath(smooth_path([(hx - 55, hy - 70), (hx + 55, hy - 70), (hx + 60, hy + 10), (hx + 20, hy + 40),
                                      (hx - 30, hy + 30), (hx - 60, hy - 10)], True), paint("#7a5a48"))
        for k in range(4):
            fxp = hx - 40 + k * 26
            pl.cv.line([(fxp, hy + 10), (fxp + 4, hy + 90 - abs(k - 1.5) * 14)], "#7a5a48", 22)
        pl.offset = lambda t: (0, -760 + 740 * ease(sstep(hand_t, hand_t + 2.2, t)))
    sc = Painted(build, dur=dur, cam=Camera(1.0, 1.05, (0.5, 0.55), (0.55, 0.55)), name="saucers")
    labels = ["marriage", "wealth", "death"]
    blocks = [Block(l, "type", 50, BLOOD if l == "death" else PAPER, W / 2 + (x - OW / 2) / 1.12, H * 0.83,
                    t_in=times_[i] + 0.4, type_cps=18) for i, (l, x) in enumerate(zip(labels, xs))]
    return Overlaid(sc, blocks)


def stones_ashes(dur, gone_t=7.0, dawn=(3.0, 6.0)):
    def build(ctx):
        night(ctx, moon=None, seed=221, clouds=0.5)
        prof = hill(ctx, OH * 0.62, 40, 700, "#0e1c20", 31, haze=("#2a4448", 0.5, 100))
        yy = np.arange(OH, dtype=np.float32)[:, None]
        skym = clamp01(prof[None, :] - yy + 0.5)
        dawn_sky = vgrad(OH, OW, [(0, "#1a2a3a"), (0.35, "#5a4a5a"), (0.6, "#d8906a"), (1.0, "#e8a070")]) * 0.6
        ctx.light_np("dawnsky", dawn_sky * skym[..., None], ramp(*dawn))
        hl = np.zeros((OH, OW, 3), np.float32)
        hl[:] = rgb("#3a2a24") * 0.35
        ctx.light_np("dawnland", hl * (1 - skym[..., None]), ramp(*dawn))
        ground(ctx, OH * 0.64, "#14100e", "#050404")
        cx_, cy_ = OW * 0.5, OH * 0.80
        ctx.cv.ellipse(cx_, cy_, 420, 120, "#2a2420")
        ctx.cv.ellipse(cx_, cy_, 360, 95, "#3a3430", blur=10)
        ctx.flush()
        embers = EmberBed(cx_, cy_, 380, 70, seed=5)
        ctx.dyn.append(lambda buf, t: embers.draw(buf, t, 0.5 * (1 - sstep(dawn[0], dawn[1], t)) + 0.15))
        ctx.light("glow", lambda t: 1 - 0.7 * sstep(dawn[0], dawn[1], t)).ellipse(cx_, cy_, 700, 220, "#ff6a2a", 0.12, blur=50)
        r = np.random.default_rng(8)
        for k in range(8):
            a = k / 8 * 2 * math.pi + 0.2
            sx, sy, sr = cx_ + math.cos(a) * 470, cy_ + math.sin(a) * 140, r.uniform(30, 44)
            target = ctx.plane(1.0) if k == 2 else None
            c = target.cv if target else ctx.cv
            c.ellipse(sx, sy + sr * 0.3, sr * 1.2, sr * 0.45, "#000000", 0.5, blur=4)
            c.ellipse(sx, sy, sr, sr * 0.7, None,
                      shader=rad((sx - sr * 0.3, sy - sr * 0.3), sr * 1.4, [("#6a645a", 1), ("#3a362e", 1), ("#141210", 1)], [0, 0.5, 1]))
            if target:
                target.dyn.append(lambda src, t: src.__imul__(1 - sstep(gone_t, gone_t + 0.8, t)))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.5, 0.6), (0.5, 0.62)), name="stones_ashes")


def mirror_scene(dur, face_t=6.0):
    def build(ctx):
        alb = plaster(OH, OW, "#5a4a3a", seed=23)
        cv = Canvas()
        mx, my = OW * 0.5, OH * 0.42
        mirror(cv, mx, my, 260, 330)
        cv.rect(OW * 0.30, OH * 0.84, OW * 0.70, OH * 0.87, "#3a2414")
        tip = candle(cv, OW * 0.5, OH * 0.84, 210, 60, color="#c8bba0")
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("c", tip[0], tip[1], 340, 2000, "#ffb066", 1.5, flick(24, 0.12, 1.0))],
                    ambient=("#1d2c33", 0.07))
        # reflection of the flame and the face in the glass
        refl = Canvas()
        refl.glow(mx, my + 260, 220, "#ffb066", 0.30)
        ctx.light("refl", flick(24, 0.12, 1.0)).glow(mx, my + 250, 120, "#ffb066", 0.25)
        face = Canvas()
        face.c.drawPath(smooth_path([(mx - 230, my + 330), (mx - 210, my + 180), (mx - 90, my + 120), (mx + 90, my + 120),
                                     (mx + 210, my + 180), (mx + 230, my + 330)], True), paint("#9ab0b0"))
        face.ellipse(mx, my - 20, 105, 130, "#9ab0b0")
        face.rect(mx - 40, my + 80, mx + 40, my + 140, "#9ab0b0")
        clip = Canvas()
        clip.ellipse(mx, my, 260, 330, "#ffffff")
        m = clip.rgba()[..., 3:4]
        F = face.rgba()[..., :3] * m
        F = cv2.GaussianBlur(F, (0, 0), 6)
        ctx.light_np("face", cv2.GaussianBlur(F, (0, 0), 10) * 0.15, times(ramp(face_t, face_t + 2.5), flick(25, 0.1, 0.4)))
        ctx.dyn.append(lambda buf, t: candle_flame(buf, tip[0], tip[1], 14, t, seed=6))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.14, (0.5, 0.55), (0.5, 0.45)), name="mirror")


def skulls_scene(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.15, OH * 0.15, 46), seed=231, clouds=0.5)
        hill(ctx, OH * 0.58, 30, 600, "#0e1c20", 32, haze=("#2a4448", 0.6, 100))
        church(ctx.cv, ctx.light("ch", flick(4, 0.06)), OW * 0.62, OH * 0.62, s=0.5)
        mist(ctx, OH * 0.62, 40, "#7fa39e", 0.38, seed=26)
        ground(ctx, OH * 0.66, "#0a1316", "#030607")
        gravestones(ctx.cv, OH * 0.72, OW * 0.0, OW * 1.0, 10, seed=13, hmin=60, hmax=120)
        stone_wall(ctx, OH * 0.80, OH, seed=9)
        ctx.flush()
        for i, (fx, s) in enumerate(((0.22, 70), (0.42, 84), (0.62, 76), (0.80, 66))):
            lc = ctx.light("sk%d" % i, flick(50 + i, 0.2, 1.4))
            sk = Canvas()
            skull(sk, lc, OW * fx, OH * 0.80 - s * 0.62, s, bone="#a89e88")
            lay = sk.rgba()
            lay[..., :3] *= 0.30
            comp(ctx.bg, lay)
            lc.glow(OW * fx, OH * 0.80 - s * 0.4, s * 1.4, "#ff8a3a", 0.18)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.6), (0.5, 0.62)), fog=dict(FOG, density=0.22),
                   name="skulls")


def three_words(dur, times_=(0.0, 0.7, 1.45)):
    words = [("Love.", PAPER), ("Money.", "#e9c25a"), ("Death.", "#d23a26")]
    blocks = [Block(w_, "fell", 130, c, W * (0.22 + 0.28 * i), H * 0.48, t_in=times_[i], fade=0.25, rise=0,
                    glow="#ff3a1a" if i == 2 else None, glow_a=0.5) for i, (w_, c) in enumerate(words)]
    return TextScene(blocks, dur, bg="dark", embers=False, drift=0.04, seed=6)


# ----------------------------------------------------------------------------- crossing the ocean

def famine_ship(dur, flashes=(1.5, 5.5)):
    def build(ctx):
        night(ctx, moon=(OW * 0.75, OH * 0.2, 44), seed=241, clouds=0.85,
              stops=[(0, "#020406"), (0.6, "#0a1418"), (1, "#14262a")])
        sea(ctx, int(OH * 0.62), seed=3, moon_x=OW * 0.75)
        lightning(ctx, flashes)
        pl = ctx.plane(1.0)
        lx, ly = tall_ship(pl.cv, OW * 0.42, OH * 0.70, s=0.95, color="#020405")
        g = Canvas()
        g.glow(lx, ly, 60, "#ffb066", 0.9)
        pl.add_glow(g.rgb(), lambda t: flicker(t, 3, 0.2, 1.0))
        nz = Noise1(33)
        pl.offset = lambda t: (12 * t, 14 * math.sin(t * 1.1) + 6 * nz(t, 0.7))
        rain(ctx, n=320, seed=2, a=0.22)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.55), (0.52, 0.55), shake=6), name="ship")


def atlantic_map(dur, route_t=(1.0, 6.0)):
    labels = [("IRELAND", -8.0, 53.2, 34, "sc"), ("SCOTLAND", -4.5, 56.8, 26, "sc"),
              ("ATLANTIC OCEAN", -40.0, 46.0, 54, "it"), ("North America", -72.0, 48.5, 46, "it"),
              ("New York", -74.0, 40.0, 30, "rm"), ("Boston", -70.0, 43.2, 28, "rm")]
    route = [(-8.3, 51.85), (-20, 50.5), (-35, 47.5), (-50, 44.5), (-62, 42.3), (-73.9, 40.6)]
    return map_scene(dur, -80, 2, 33, 61, labels=labels, route=route, route_t=route_t, ship=True, seed=5,
                     cam=Camera(1.12, 1.0, (0.85, 0.35), (0.5, 0.5)), pins=[(-8.3, 51.85), (-73.9, 40.6)])


def turnip_vs_pumpkin(dur):
    def build(ctx):
        alb = plaster(OH, OW, "#6a5a48", seed=31)
        table_top(alb, OH * 0.70, OH, "#6a4428", seed=32)
        cv = Canvas()
        cv.ellipse(OW * 0.30, OH * 0.80, 140, 30, "#000000", 0.5, blur=12)
        turnip(cv, OW * 0.30, OH * 0.71, 90, seed=4)
        cv.ellipse(OW * 0.62, OH * 0.83, 420, 70, "#000000", 0.5, blur=16)
        pumpkin(cv, OW * 0.62, OH * 0.58, 380, seed=5)
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("c", OW * 0.40, OH * 0.30, 750, 3200, "#ffb066", 1.7, flick(30, 0.06, 0.8))],
                    ambient=("#26363e", 0.18))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.45, 0.55), (0.52, 0.55)), name="turnip_vs_pumpkin")


def pumpkin_patch(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.78, OH * 0.16, 58), seed=251, clouds=0.4)
        hill(ctx, OH * 0.50, 30, 600, "#0e1c20", 33, haze=("#2a4448", 0.6, 100))
        farmhouse(ctx.cv, ctx.light("fh", flick(5, 0.06)), OW * 0.08, OH * 0.52, s=0.35)
        mist(ctx, OH * 0.52, 40, "#7fa39e", 0.35, seed=27)
        ground(ctx, OH * 0.53, "#0c1610", "#030604")
        ctx.flush()
        pumpkin_field(ctx, OH * 0.55, n=46, seed=4)
        ctx.flush()
        ctx.bg[int(OH * 0.5):] *= 0.75
        fence(ctx.cv, OH * 0.58, OW * 0.55, OW, seed=12, spacing=50, h=70)
        flock(ctx, "crow", 2, (200, 220, 1000, 380), seed=12, speed=100, size=(20, 26))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.5), (0.55, 0.6)), fog=dict(FOG, density=0.2),
                   name="pumpkin_patch")


def jack_hero(dur, boosts=(), base=0.85, face=0):
    def build(ctx):
        night(ctx, moon=None, seed=261, clouds=0.3, stops=[(0, "#030405"), (1, "#0b1012")], stars=60)
        ground(ctx, OH * 0.80, "#0e0a08", "#030202")
        fn = lambda t: (base + sum(0.22 * sstep(b, b + 0.25, t) for b in boosts)) * flicker(t, 41, 0.12, 1.2)
        ctx.light("ground", fn).ellipse(OW * 0.5, OH * 0.86, 700, 90, "#ff7a2a", 0.22, blur=40)
        ctx.lantern("pumpkin", OW * 0.5, OH * 0.56, 330, face=face, seed=7, fn=fn, skin_k=0.6, halo=0.3)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.14, (0.5, 0.55), (0.5, 0.56)), name="jack_hero")


def victorian_parlor(dur):
    def build(ctx):
        alb = np.zeros((OH, OW, 3), np.float32)
        stripes = ((np.arange(OW) // 60) % 2).astype(np.float32)
        alb[:] = (rgb("#5a3a3a") * (0.85 + 0.15 * stripes[:, None]))[None, :, :]
        n = cv2.resize(fbm(OH // 4, OW // 4, scale=60, octaves=4, seed=5), (OW, OH))
        alb *= (0.85 + 0.3 * n)[..., None]
        alb[int(OH * 0.62):int(OH * 0.64)] = rgb("#3a2414")
        alb[int(OH * 0.64):] = wood(OH - int(OH * 0.64), OW, "#4a2a1a", seed=6, along="y", boards=12) * 0.8
        alb[int(OH * 0.86):] = wood(OH - int(OH * 0.86), OW, "#3a2414", seed=7, along="x", boards=3)
        cv = Canvas()
        cv.rect(OW * 0.30, OH * 0.30, OW * 0.70, OH * 0.33, "#3a2414")
        for fx, h, dress, hat in ((0.12, 640, True, None), (0.20, 690, False, "top"), (0.80, 660, True, None),
                                  (0.88, 700, False, None)):
            figure(cv, OW * fx, OH * 1.0, h, "#140c0a", dress=dress, coat=not dress, hat=hat,
                   arms=((10, 10), (20, 50)))
        comp(alb, cv.rgba())
        spots = [(OW * 0.36, OH * 0.27, 70), (OW * 0.5, OH * 0.26, 80), (OW * 0.64, OH * 0.27, 70),
                 (OW * 0.30, OH * 0.80, 90), (OW * 0.70, OH * 0.80, 95)]
        light_scene(ctx, alb, [Light("p%d" % i, x, y, 260, 1800, "#ff9a4a", 0.9, flick(60 + i, 0.12, 1.1))
                               for i, (x, y, r) in enumerate(spots)], ambient=("#2a2a30", 0.10))
        for i, (x, y, r) in enumerate(spots):
            ctx.lantern("pumpkin", x, y, r, face=i % 3, seed=70 + i, fn=flick(60 + i, 0.12, 1.1), skin_k=0.7)
    return Painted(build, dur=dur, cam=Camera(1.02, 1.12, (0.5, 0.5), (0.5, 0.45)), name="victorian")


# ----------------------------------------------------------------------------- the prank years

def town_1900(dur, leaves_on=True):
    def build(ctx):
        night(ctx, moon=(OW * 0.86, OH * 0.12, 40), seed=271, clouds=0.5)
        town_row(ctx, OH * 0.70, -40, OW + 40, seed=5, hmin=260, hmax=520, lit_p=0.35, style="old")
        ground(ctx, OH * 0.70, "#141c1e", "#050708")
        ctx.cv.rect(0, OH * 0.70, OW, OH * 0.74, "#202a2c")
        for fx in (0.15, 0.45, 0.75):
            gas_lamp(ctx, OW * fx, OH * 0.78, s=1.1)
        if leaves_on:
            leaves(ctx, 40, seed=3, wind=260)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.5, 0.55), (0.55, 0.55)), fog=dict(FOG, density=0.18),
                   name="town_1900")


def rope_sidewalk(dur):
    def build(ctx):
        night(ctx, moon=None, seed=281, clouds=0.6)
        town_row(ctx, OH * 0.55, -40, OW + 40, seed=8, hmin=200, hmax=420, lit_p=0.25)
        ground(ctx, OH * 0.55, "#1a2224", "#06090a")
        cv = ctx.cv
        cv.c.drawPath(poly_path([(0, OH * 0.62), (OW, OH * 0.58), (OW, OH * 0.66), (0, OH * 0.74)]), paint("#2a3436"))
        for k in range(12):
            x = k * OW / 11
            cv.line([(x, OH * 0.62 - 0.04 * OH * k / 11), (x - 80, OH * 0.74 - 0.08 * OH * k / 11)], "#1a2224", 3)
        gas_lamp(ctx, OW * 0.80, OH * 0.70, s=1.4)
        tree(cv, OW * 0.12, OH * 0.80, 700, seed=31, spread=0.6)
        cv.c.drawPath(smooth_path([(OW * 0.13, OH * 0.765), (OW * 0.45, OH * 0.79), (OW * 0.80, OH * 0.685)], False),
                      paint("#b8a888", 0.9, stroke=6))
        leaves(ctx, 25, seed=5, wind=200)
    return Painted(build, dur=dur, cam=Camera(1.05, 1.14, (0.45, 0.65), (0.5, 0.68)), fog=dict(FOG, density=0.2),
                   name="rope")


SCRIBBLE = None


def soaped_window(dur, t0=0.8, t1=4.5):
    wx0, wy0, wx1, wy1 = OW * 0.25, OH * 0.12, OW * 0.75, OH * 0.86

    def build(ctx):
        alb = wood(OH, OW, "#4a5050", seed=41, along="x", boards=26) * 0.7
        cv = Canvas()
        cv.rect(wx0 - 50, wy0 - 50, wx1 + 50, wy1 + 50, "#d8d4c8")
        cv.rect(wx0, wy0, wx1, wy1, "#1a1410")
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("street", OW * 0.1, OH * 0.1, 900, 3000, "#ffd8a0", 0.9, flick(3, 0.05, 1.0))],
                    ambient=("#24343c", 0.10))
        inside = ctx.light("inside", flick(42, 0.08, 0.8))
        inside.rect(wx0, wy0, wx1, wy1, "#ff9a4a", 0.30)
        inside.glow(OW * 0.6, OH * 0.6, 600, "#ffb066", 0.35)
        for k in (0.5,):
            inside.rect(wx0 + (wx1 - wx0) * k - 10, wy0, wx0 + (wx1 - wx0) * k + 10, wy1, "#000000")
            inside.rect(wx0, wy0 + (wy1 - wy0) * k - 10, wx1, wy0 + (wy1 - wy0) * k + 10, "#000000")
        # soap scribbles: loops and zigzags, revealed along their length
        r = np.random.default_rng(5)
        strokes = []
        for k in range(5):
            cx_, cy_ = r.uniform(wx0 + 120, wx1 - 120), r.uniform(wy0 + 120, wy1 - 120)
            pts = []
            for i in range(140):
                a = i * 0.24
                rr = 40 + i * 1.6
                pts.append((cx_ + math.cos(a) * rr * 0.9 + r.normal(0, 3), cy_ + math.sin(a) * rr * 0.55 + r.normal(0, 3)))
            strokes.append(np.array(pts, np.float32))
        zz = []
        for i in range(30):
            zz.append((wx0 + 60 + i * (wx1 - wx0 - 120) / 29, wy0 + (wy1 - wy0) * (0.78 + 0.08 * (-1) ** i)))
        strokes.append(np.array(zz, np.float32))
        total = sum(len(s_) for s_ in strokes)

        def draw(buf, t):
            p = sstep(t0, t1, t) * total
            for s_ in strokes:
                n = int(min(len(s_), p))
                p -= len(s_)
                if n < 2:
                    break
                q = (s_[:n] * 4).astype(np.int32)
                cv2.polylines(buf, [q], False, (0.82, 0.84, 0.82), 9, cv2.LINE_AA, shift=2)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.5), (0.5, 0.5)), name="soaped")


def streetcar(dur, bursts=(2.0, 3.2, 4.4)):
    def build(ctx):
        night(ctx, moon=(OW * 0.15, OH * 0.12, 40), seed=291, clouds=0.5)
        town_row(ctx, OH * 0.66, -40, OW + 40, seed=11, hmin=300, hmax=560, lit_p=0.3)
        ground(ctx, OH * 0.66, "#141c1e", "#050708")
        for y in (OH * 0.80, OH * 0.84):
            ctx.cv.line([(0, y), (OW, y)], "#3a4446", 5)
        ctx.cv.line([(0, OH * 0.18), (OW, OH * 0.16)], "#050708", 3)
        gas_lamp(ctx, OW * 0.08, OH * 0.90, s=1.2)
        pl = ctx.plane(1.0)
        cx_, cy_ = OW * 0.30, OH * 0.82
        body = poly_path([(cx_, cy_), (cx_, cy_ - 300), (cx_ + 40, cy_ - 340), (cx_ + 860, cy_ - 340), (cx_ + 900, cy_ - 300),
                          (cx_ + 900, cy_)])
        pl.cv.c.drawPath(body, paint("#1a1210"))
        pl.cv.line([(cx_ + 450, cy_ - 340), (cx_ + 700, OH * 0.168)], "#050505", 4)
        g = Canvas()
        for i in range(8):
            x = cx_ + 60 + i * 100
            pl.cv.rect(x, cy_ - 270, x + 70, cy_ - 160, "#3a2412")
            g.rect(x, cy_ - 270, x + 70, cy_ - 160, "#ffcf7a", 0.9)
            g.glow(x + 35, cy_ - 215, 120, "#ffcf7a", 0.25)
        for wx in (cx_ + 150, cx_ + 750):
            pl.cv.circle(wx, cy_ + 10, 36, "#050505")
        pl.add_glow(g.rgb(), lambda t: flicker(t, 7, 0.05, 2.0))
        pl.offset = lambda t: (-90 * t, 0)
        for k in range(3):
            figure(ctx.cv, OW * (0.70 + k * 0.06), OH * 0.97, 300 - k * 20, "#030405", child=True, cape=False,
                   arms=((150, 30), (20, 10)) if k == 1 else ((20, 20), (60, 60)), hat="cap")
        ctx.flush()
        r = np.random.default_rng(4)
        puffs = [(b, OW * r.uniform(0.35, 0.65), OH * r.uniform(0.45, 0.62)) for b in bursts]

        def flour(buf, t):
            for (b, x, y) in puffs:
                d = t - b
                if 0 <= d < 2.2:
                    s = 30 + 220 * (1 - math.exp(-d * 2.5))
                    a = 0.55 * math.exp(-d * 1.4)
                    add_spot(buf, x - 90 * d, y + 25 * d, s, (0.85, 0.85, 0.82), a)
        ctx.dyn.append(flour)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.55), (0.48, 0.55)), fog=dict(FOG, density=0.15),
                   name="streetcar")


def fire_alarm(dur):
    def build(ctx):
        night(ctx, moon=None, seed=301, clouds=0.6)
        town_row(ctx, OH * 0.62, -40, OW + 40, seed=12, hmin=260, hmax=520, lit_p=0.2)
        ground(ctx, OH * 0.62, "#141c1e", "#050708")
        gas_lamp(ctx, OW * 0.25, OH * 0.95, s=1.6)
        cv = ctx.cv
        bx, by = OW * 0.58, OH * 0.42
        cv.rect(bx - 12, by, bx + 12, OH * 0.98, "#1a0806")
        cv.rect(bx - 90, by - 180, bx + 90, by + 40, "#7a1008", r=10)
        cv.c.drawPath(poly_path([(bx - 100, by - 180), (bx, by - 240), (bx + 100, by - 180)]), paint("#5a0c06"))
        cv.circle(bx, by - 70, 40, "#2a0402")
        lay = text_layer("FIRE", "sans_x", 40, "#f0e0c0")
        ctx.flush()
        paste(ctx.bg, lay, bx, by + 10)
        lc = ctx.light("alarm", lambda t: 0.6 + 0.4 * (math.sin(t * 9) > 0))
        lc.glow(bx, by - 260, 160, "#ff2a1a", 0.5)
        lc.circle(bx, by - 262, 16, "#ff6a4a", 0.9)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.5), (0.55, 0.45), shake=3), fog=dict(FOG, density=0.15),
                   name="fire_alarm")


def broken_window(dur, crack_t=1.5):
    wx0, wy0, wx1, wy1 = OW * 0.15, OH * 0.15, OW * 0.85, OH * 0.80

    def build(ctx):
        alb = stone_blocks(OH, OW, "#5a5048", seed=51, bh=60) * 0.8
        cv = Canvas()
        cv.rect(wx0 - 40, wy0 - 40, wx1 + 40, wy1 + 40, "#2a1a10")
        cv.rect(wx0, wy0, wx1, wy1, "#120e0a")
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("street", OW * 0.5, OH * 1.2, 700, 2400, "#ffd8a0", 0.8, flick(5, 0.05, 1.0))],
                    ambient=("#24343c", 0.10))
        shop = ctx.light("shop", flick(52, 0.04, 0.5))
        shop.rect(wx0, wy0, wx1, wy1, "#ffb066", 0.22)
        for k in range(5):
            shop.rect(wx0 + 80, wy0 + 160 + k * 120, wx1 - 80, wy0 + 170 + k * 120, "#000000", 0.6)
        lay = text_layer("BAKERY", "old_b", 110, "#d4a237", tracking=0.25)
        ctx.flush()
        paste(ctx.bg, lay, OW * 0.5, wy0 + 90, a=0.85)
        ix, iy = OW * 0.56, OH * 0.48
        r = np.random.default_rng(9)
        cracks = []
        for k in range(14):
            a = k / 14 * 2 * math.pi + r.normal(0, 0.15)
            pts = [(ix, iy)]
            x, y = ix, iy
            L = r.uniform(250, 700)
            for i in range(10):
                a += r.normal(0, 0.18)
                x += math.cos(a) * L / 10
                y += math.sin(a) * L / 10
                pts.append((x, y))
            cracks.append(np.array(pts, np.float32))
        rings = [np.array([(ix + math.cos(a) * rr * (1 + 0.1 * math.sin(a * 5)), iy + math.sin(a) * rr)
                           for a in np.linspace(0, 2 * math.pi, 60)], np.float32) for rr in (70, 160)]

        def draw(buf, t):
            if t < crack_t:
                return
            p = sstep(crack_t, crack_t + 0.25, t)
            for c in cracks:
                n = max(2, int(len(c) * p))
                cv2.polylines(buf, [(c[:n] * 4).astype(np.int32)], False, (0.85, 0.88, 0.9), 6, cv2.LINE_AA, shift=2)
            if p >= 1:
                for rg in rings:
                    cv2.polylines(buf, [(rg * 4).astype(np.int32)], True, (0.7, 0.72, 0.75), 4, cv2.LINE_AA, shift=2)
            if t - crack_t < 0.15:
                add_spot(buf, ix, iy, 80, (1, 1, 1), 0.6)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.05, (0.5, 0.5), (0.52, 0.5), shake=2), name="broken_window")


def porch_dark(dur, light_t=2.0):
    def build(ctx):
        night(ctx, moon=(OW * 0.85, OH * 0.15, 40), seed=311, clouds=0.5)
        hill(ctx, OH * 0.60, 30, 600, "#0e1c20", 34, haze=("#2a4448", 0.6, 100))
        ground(ctx, OH * 0.62, "#0a1316", "#030607")
        farmhouse(ctx.cv, ctx.light("win", times(ramp(light_t, light_t + 0.2), flick(9, 0.06))), OW * 0.25, OH * 0.82,
                  s=1.6, lit=(0, 0, 1, 1, 0))
        ctx.flush()
        door = ctx.light("door", ramp(light_t + 0.6, light_t + 1.2))
        door.rect(OW * 0.25 + 280 * 1.6, OH * 0.82 - 230, OW * 0.25 + 280 * 1.6 + 70, OH * 0.82, "#ffcf8a", 0.9)
        figure(ctx.cv, OW * 0.25 + 280 * 1.6 + 35, OH * 0.82, 200, "#020304", coat=True, hat="brim")
        grass(ctx.cv, OH, 0, OW, "#020405", n=400, hmin=20, hmax=60, seed=34)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.5, 0.55), (0.5, 0.55)), fog=FOG, name="porch_dark")


def party_lanterns(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.80, OH * 0.12, 40), seed=321, clouds=0.4)
        town_row(ctx, OH * 0.62, -40, OW + 40, seed=14, hmin=240, hmax=420, lit_p=0.5)
        ground(ctx, OH * 0.62, "#141412", "#050505")
        for k, (y0, y1) in enumerate(((OH * 0.20, OH * 0.26), (OH * 0.30, OH * 0.24))):
            string_lights(ctx, ((-20, y0), (OW + 20, y1)), n=18, colors=("#ff8a2a", "#ffcf6a", "#ff5a2a"), name="s%d" % k,
                          sag=90)
        ctx.flush()
        r = np.random.default_rng(6)
        pl = ctx.plane(1.0)
        for i in range(11):
            fx = 0.05 + i * 0.09 + r.uniform(-0.02, 0.02)
            child = r.random() < 0.4
            figure(pl.cv, OW * fx, OH * (0.98 + r.uniform(-0.02, 0.02)), (330 if child else 520) * r.uniform(0.9, 1.1),
                   "#050404", child=child, dress=r.random() < 0.5, hat=r.choice([None, "witch", "brim", "cap"]),
                   arms=((r.uniform(5, 160), 10), (r.uniform(5, 60), 20)))
        ctx.light("glow", flick(3, 0.05)).rect(0, OH * 0.3, OW, OH * 0.9, "#ff9a4a", 0.05)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.5), (0.5, 0.52)), name="party")


def treat_or_trick_card(dur, t_in=0.3):
    blocks = [Block("“Give us a treat…\nor we’ll play a trick.”", "type", 84, PAPER, W / 2, H / 2,
                    t_in=t_in, type_cps=17, glow="#ff7a1a", glow_a=0.3)]
    return TextScene(blocks, dur, bg="dark", embers=True, drift=0.04, seed=7)


def newsprint_card(dur, t_circle=2.5):
    blocks = [Block("“trick or treat”", "old_b", 120, "#1a1612", W / 2, H * 0.44, t_in=0.6, fade=0.6),
              Block("The Blackie Times  ·  Blackie, Alberta", "type", 44, INK, W / 2, H * 0.70, t_in=1.4, type_cps=30),
              Block("November 3, 1927", "type", 44, BLOOD, W / 2, H * 0.78, t_in=2.8, type_cps=20)]
    r = np.random.default_rng(11)
    bars = []
    for col in range(4):
        x0 = 120 + col * 430
        y = 70
        while y < H - 60:
            n = r.integers(3, 9)
            x = x0
            for k in range(n):
                wlen = r.uniform(20, 80)
                if x + wlen > x0 + 380:
                    break
                bars.append((x, y, wlen))
                x += wlen + 12
            y += 26
    base = cv2.resize(newsprint_texture(0), (int(W * 1.06), int(H * 1.06)))
    for (x, y, wl) in bars:
        cv2.rectangle(base, (int(x), int(y)), (int(x + wl), int(y + 9)), (0.45, 0.43, 0.40), -1)
    base = cv2.GaussianBlur(base, (0, 0), 0.8)
    # fade the columns out behind the phrase
    m = np.zeros(base.shape[:2], np.float32)
    cv2.rectangle(m, (int(W * 0.20), int(H * 0.32)), (int(W * 0.86), int(H * 0.86)), 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), 50)[..., None] * 0.92
    clean = cv2.resize(newsprint_texture(0), (base.shape[1], base.shape[0]))
    base = base * (1 - m) + clean * m

    def circle(frame, t, u):
        p = ease(sstep(t_circle, t_circle + 1.0, t))
        if p <= 0:
            return
        n = int(80 * p)
        pts = np.array([(W / 2 + math.cos(a) * 470 * (1 + 0.04 * math.sin(a * 3)), H * 0.44 + math.sin(a) * 120)
                        for a in np.linspace(-2.6, -2.6 + 2 * math.pi * 1.05 * p, max(2, n))], np.float32)
        cv2.polylines(frame, [(pts * 4).astype(np.int32)], False, tuple(float(c) for c in rgb(BLOOD)), 7, cv2.LINE_AA, shift=2)
    return TextScene(blocks, dur, bg=base, fog=False, drift=0.04, seed=3, extra=[circle])


def rules_card(dur, t1=1.0, t2=4.2):
    blocks = [Block("The new rules", "fell", 120, INK, W / 2, 260, t_in=0.2, fade=0.8),
              Block("Kids: ask politely.", "type", 64, INK, W / 2, 520, t_in=t1, type_cps=20),
              Block("Grown-ups: have treats ready at the door.", "type", 64, INK, W / 2, 660, t_in=t2, type_cps=22)]
    return paper_card(blocks, dur, seed=3)
