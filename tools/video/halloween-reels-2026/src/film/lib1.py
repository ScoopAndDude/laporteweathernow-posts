"""Scene builders, part 1: cold open, Samhain, the church."""
import math

import cv2
import numpy as np
import skia

from core import (OW, OH, W, H, Canvas, Camera, rgb, mix, clamp01, smoothstep, sstep, ease, fbm, add_spot, poly_path,
                  smooth_path, paint, lin, rad, ADD, blur, flicker, Noise1, Flame, Embers, Motes, Fog, AMBER, GHOST, MOON,
                  text_layer, paste)
from art import (figure, hooded, comp, sky, hills, tree, grass, reeds, farmhouse, church, gravestones, fence, hooded_figure, person,
                 pumpkin, carve, turnip, candle, candle_flame, skull, rim_shape, jack_face)
from items import (EmberBed, embers_glow, night, dusk, hill, mist, ground, fog, bonfire, distant_fires, flock, wisps, ghosts, leaves, stooks,
                   dolmen, mound, road, roadside_posts, approaching_light, cottage, gate, signpost, red_eyes,
                   turnip_lantern, jack, stone_wall, silhouette, DARK, RIM)
from interior import (Light, light_scene, plaster, wood, stone_blocks, table_top, fireplace, embers_bed, logs, chair,
                      plate, cup, jug, bowl)
from scene import Painted, Blend, Seq, flick, ramp, times, const

FOG = dict(seed=3, density=0.28, color="#7fa39e", top=0.45, bottom=1.0, speed=16)


def pulse(t0, t1, t2, t3):
    return lambda t: sstep(t0, t1, t) * (1 - sstep(t2, t3, t))


# ----------------------------------------------------------------------------- cold open

def match_turnip(dur):
    lx, ly = OW * 0.5, OH * 0.56

    def build(ctx):
        alb = stone_blocks(OH, OW, "#5c564e", seed=4)
        alb[int(ly + 150):] = wood(OH - int(ly + 150), OW, "#4a3424", seed=2, along="x") * 0.9
        alb[int(ly + 150):int(ly + 162)] *= 0.3
        lit = times(ramp(1.5, 2.6), flick(11, 0.16, 1.4))
        light_scene(ctx, alb, [Light("wall", lx, ly + 20, 260, 1700, "#ff9a4a", 1.5, lit),
                               Light("match", lx + 230, ly - 150, 120, 900, "#ffc070", 1.4, pulse(0.85, 1.0, 1.9, 2.5))],
                    ambient=("#22323a", 0.07))
        sh = Canvas()
        sh.ellipse(lx, ly + 152, 170, 24, "#000000", 0.7, blur=10)
        ctx.cv = sh
        ctx.lantern("turnip", lx, ly, 140, face=1, seed=1, fn=lit, dim=0.03, skin_k=0.85, halo=0.25)

        def match(buf, t):
            if 0.8 < t < 2.4:
                f = sstep(0.85, 1.6, t)
                x = lx + 230 - 230 * f
                y = ly - 150 + 60 * f
                k = sstep(0.8, 0.9, t) * (1 - sstep(2.0, 2.4, t))
                flash = math.exp(-max(0, t - 0.88) * 8) if t > 0.85 else 0
                add_spot(buf, x, y, 60, (1, 0.6, 0.25), 0.5 * flash)
                cv2.line(buf, (int(x + 6), int(y + 4)), (int(x + 110), int(y + 30)), (0.25, 0.17, 0.1), 5, cv2.LINE_AA)
                candle_flame(buf, x, y, 9, t, seed=3, k=k * 1.2)
        ctx.dyn.append(match)
    return Painted(build, dur=dur, cam=Camera(1.04, 1.16, (0.5, 0.52), (0.5, 0.53)), name="match_turnip")


def hearth(dur, fire=None, shutters=True, embers_k=1.0):
    fx, fy = OW * 0.40, OH * 0.80
    wx0, wy0, wx1, wy1 = OW * 0.70, OH * 0.22, OW * 0.86, OH * 0.56
    fire_fn = fire or const(0.0)

    def build(ctx):
        alb = wood(OH, OW, "#4e3826", seed=7, along="y", boards=14) * 0.9
        alb[int(fy + 30):] = wood(OH - int(fy + 30), OW, "#3a2a1c", seed=8, along="x", boards=5)
        cv = Canvas()
        box = fireplace(cv, fx, fy, 820, 640, seed=3, stone="#8a8070")
        logs(cv, fx, fy - 6, 300)
        cv.rect(wx0 - 26, wy0 - 26, wx1 + 26, wy1 + 26, "#3a2616")
        cv.rect(wx0, wy0, wx1, wy1, "#0b1418")
        comp(alb, cv.rgba())
        ember_fn = times(flick(21, 0.22, 0.6), const(embers_k))
        light_scene(ctx, alb, [Light("embers", fx, fy - 40, 300, 1600, "#ff6a2a", 1.6, ember_fn),
                               Light("fire", fx, fy - 160, 380, 2400, "#ff9a4a", 2.2, times(fire_fn, flick(22, 0.18, 1.2))),
                               Light("moon", (wx0 + wx1) / 2, (wy0 + wy1) / 2, 300, 1600, "#9fc4d0", 0.5, const(1))],
                    ambient=("#1a262c", 0.16))
        bed = EmberBed(fx, fy - 18, 330, 56, seed=4)
        mc = ctx.light("moon")
        mc.rect(wx0, wy0, wx1, wy1, "#2e4650", 0.9)
        mc.glow(wx0 + (wx1 - wx0) * 0.7, wy0 + 40, 160, "#cfe6e0", 0.6)
        mc.rect(wx0 + (wx1 - wx0) / 2 - 5, wy0, wx0 + (wx1 - wx0) / 2 + 5, wy1, "#000000")
        mc.rect(wx0, wy0 + (wy1 - wy0) / 2 - 5, wx1, wy0 + (wy1 - wy0) / 2 + 5, "#000000")
        fl = Flame(300, 380, seed=6, speed=0.8, width=0.6)
        small = Flame(120, 150, seed=9, speed=1.0, width=0.5)

        def draw(buf, t):
            bed.draw(buf, t, 0.9 * ember_fn(t))
            k = fire_fn(t)
            if k > 0.01:
                f = fl.render(t, intensity=k)
                x0, y0 = int(fx - 150), int(fy - 380 + 10)
                buf[y0:y0 + 380, x0:x0 + 300] += f
            else:
                f = small.render(t, intensity=0.55 + 0.25 * math.sin(t * 1.3))
                x0, y0 = int(fx - 20), int(fy - 150 - 8)
                buf[y0:y0 + 150, x0:x0 + 120] += f * 0.8
        ctx.dyn.append(draw)
        if shutters:
            nz = Noise1(8)
            ww = (wx1 - wx0) / 2

            def shut(buf, t):
                for side in (-1, 1):
                    a = 0.55 + 0.35 * nz(t * 0.8 + (0 if side < 0 else 7), 1.0) + 0.15 * math.sin(t * 2.3 + side)
                    a = min(1.45, max(0.15, a))
                    wv = ww * math.cos(a)
                    hinge = wx0 if side < 0 else wx1
                    tip = hinge - side * wv
                    sk = 18 * math.sin(a)
                    pts = np.array([(hinge, wy0 + 6), (tip, wy0 + 6 - sk), (tip, wy1 - 6 + sk), (hinge, wy1 - 6)], np.float32)
                    silhouette(buf, pts, (0.02, 0.025, 0.03), 0.92)
            ctx.dyn.append(shut)
    return Painted(build, dur=dur, cam=Camera(1.02, 1.10, (0.45, 0.55), (0.42, 0.6)), name="hearth")


def road_scene(dur):
    vx, vy = OW * 0.52, OH * 0.60

    def build(ctx):
        night(ctx, moon=(OW * 0.30, OH * 0.20, 52), seed=12, clouds=0.55)
        hill(ctx, vy - 5, 40, 500, "#0e1c20", 3, haze=("#2a4448", 0.6, 100))
        mist(ctx, vy + 6, 30, "#7fa39e", 0.4, seed=1)
        hill(ctx, vy + 26, 14, 300, "#091417", 4)
        ctx.flush()
        # moonlit dirt road narrowing to the horizon
        yb = OH
        p = poly_path([(vx - 10, vy + 24), (vx + 10, vy + 24), (vx + 700, yb), (vx - 700, yb)])
        ctx.cv.c.drawPath(p, paint(None, shader=lin((0, vy), (0, yb), [("#3a5052", 1), ("#1d2a2c", 1), ("#0a1012", 1)], [0, 0.35, 1])))
        for off in (-0.18, 0.18):
            ctx.cv.line([(vx + off * 30, vy + 26), (vx + off * 1100, yb)], "#081012", 14, a=0.7)
        ctx.cv.line([(vx, vy + 26), (vx, yb)], "#4a6264", 30, a=0.18, blur=10)
        for side in (-1, 1):
            for i in range(14):
                f = ((i + 1) / 14) ** 1.8
                x = vx + side * (30 + 900 * f)
                y = vy + 24 + (yb - vy) * f
                h = 6 + 260 * f
                w = 2 + 18 * f
                pp = poly_path([(x - w / 2, y), (x - w / 2, y - h), (x + w / 2, y - h), (x + w / 2, y)])
                rim_shape(ctx.cv, pp, "#030607", "#4a6866", (2 + 2 * f, 2 + 2 * f), rim_a=0.6)
                if i > 0:
                    fp = ((i) / 14) ** 1.8
                    xp = vx + side * (30 + 900 * fp)
                    yp = vy + 24 + (yb - vy) * fp
                    hp = 6 + 260 * fp
                    ctx.cv.line([(xp, yp - hp * 0.7), (x, y - h * 0.7)], "#030607", 1 + 5 * f)
        tree(ctx.cv, OW * 0.12, OH * 0.98, 800, seed=21, spread=0.62, lean=0.12)
        tree(ctx.cv, OW * 0.90, OH * 0.95, 700, seed=22, spread=0.58, lean=-0.1)
        tree(ctx.cv, OW * 0.68, vy + 40, 200, seed=23, spread=0.6)
        tree(ctx.cv, OW * 0.37, vy + 36, 160, seed=24, spread=0.6)
        grass(ctx.cv, OH, 0, vx - 640, "#020405", n=300, hmin=20, hmax=90, seed=5)
        grass(ctx.cv, OH, vx + 640, OW, "#020405", n=300, hmin=20, hmax=90, seed=6)
        approaching_light(ctx, vx, vy + 14, t_total=dur * 2)
        flock(ctx, "crow", 1, (500, 250, 900, 350), seed=3, speed=90, size=(26, 30))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.14, (0.5, 0.55), (0.52, 0.52)), fog=FOG, name="road")


def graveyard(dur, crows=True, church_far=True, seed=0):
    def build(ctx):
        night(ctx, moon=(OW * 0.72, OH * 0.18, 60), seed=31 + seed, clouds=0.5)
        hill(ctx, OH * 0.66, 50, 600, "#0e1c20", 5, haze=("#2a4448", 0.6, 110))
        if church_far:
            lc = Canvas()
            church(ctx.cv, ctx.light("church", flick(4, 0.06)), OW * 0.18, OH * 0.66, s=0.45)
        mist(ctx, OH * 0.68, 50, "#7fa39e", 0.38, seed=3)
        hill(ctx, OH * 0.74, 30, 400, "#081316", 6, rim=RIM, rim_a=0.25)
        gravestones(ctx.cv, OH * 0.76, OW * 0.25, OW * 0.95, 14, seed=4, hmin=40, hmax=90)
        ctx.flush()
        mist(ctx, OH * 0.80, 50, "#7fa39e", 0.3, seed=4)
        ground(ctx, OH * 0.86, "#060d10", "#020405")
        gravestones(ctx.cv, OH * 0.90, OW * 0.05, OW * 0.95, 9, seed=7, hmin=120, hmax=240)
        tree(ctx.cv, OW * 0.88, OH * 0.92, 900, seed=41, spread=0.62, lean=-0.15)
        grass(ctx.cv, OH, 0, OW, "#020405", n=600, hmin=20, hmax=80, seed=6)
        ghosts(ctx, 3, (OW * 0.3, OH * 0.78, OW * 0.8, OH * 0.86), seed=2, a=0.08)
        if crows:
            flock(ctx, "crow", 3, (200, 200, 1200, 420), seed=5, speed=110, size=(22, 30))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.55), (0.55, 0.55)), fog=FOG, name="graveyard")


# ----------------------------------------------------------------------------- the turnip

def turnip_carving(dur, reveal=(2.0, 2.6, 3.2)):
    tx, ty = OW * 0.55, OH * 0.55
    cx_, cy_ = OW * 0.30, OH * 0.70

    def build(ctx):
        alb = plaster(OH, OW, "#6a5a48", seed=3)
        table_top(alb, OH * 0.68, OH, "#6a4428", seed=2)
        cv = Canvas()
        cv.ellipse(tx, ty + 150, 210, 40, "#000000", 0.5, blur=14)
        turnip(cv, tx, ty, 160, seed=2)
        cv.poly([(OW * 0.68, OH * 0.84), (OW * 0.80, OH * 0.81), (OW * 0.81, OH * 0.825), (OW * 0.69, OH * 0.855)], "#c8ccd0")
        cv.rect(OW * 0.80, OH * 0.805, OW * 0.88, OH * 0.83, "#4a2a14", r=8)
        r = np.random.default_rng(3)
        for _ in range(9):
            sx, sy = tx + r.uniform(-320, 320), OH * r.uniform(0.76, 0.88)
            cv.ellipse(sx, sy, r.uniform(14, 30), r.uniform(6, 12), "#e8dcc0")
        tip = candle(cv, cx_, cy_ + 40, 240, 64, color="#b8ab90")
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("candle", tip[0], tip[1] - 10, 330, 2200, "#ffb066", 1.7, flick(9, 0.10, 1.0))],
                    ambient=("#26363e", 0.16))

        def draw(buf, t):
            candle_flame(buf, tip[0], tip[1], 14, t, seed=4)
            shapes = jack_face(1)
            for i in range(4):
                ts = reveal[min(i, len(reveal) - 1)] + (0.25 if i == 1 else 0)
                if t >= ts:
                    k = sstep(ts, ts + 0.35, t)
                    P = np.array([(tx + px * 128, ty + 8 + py * 122) for px, py in shapes[i]], np.float32)
                    silhouette(buf, P, (0.03, 0.015, 0.008), 0.95 * k)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.02, 1.14, (0.5, 0.55), (0.54, 0.52)), name="turnip_carving")


def turnip_carried(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.8, OH * 0.16, 46), seed=51, clouds=0.5)
        hill(ctx, OH * 0.62, 40, 500, "#0e1c20", 8, haze=("#2a4448", 0.6, 100))
        farmhouse(ctx.cv, ctx.light("house", flick(3, 0.06)), OW * 0.62, OH * 0.63, s=0.42)
        mist(ctx, OH * 0.64, 40, "#7fa39e", 0.4, seed=8)
        ground(ctx, OH * 0.66, "#081114", "#020405")
        fence(ctx.cv, OH * 0.76, 0, OW, seed=9, spacing=60, h=110)
        tree(ctx.cv, OW * 0.12, OH * 0.95, 700, seed=52, spread=0.6)
        grass(ctx.cv, OH, 0, OW, "#020405", n=500, hmin=20, hmax=70, seed=9)
        pl = ctx.plane(1.25)
        lx, ly = OW * 0.44, OH * 0.52
        pl.cv.line([(lx, ly - 125), (lx + 30, -50)], "#100a06", 4)
        turnip(pl.cv, lx, ly, 120, seed=3)
        gcv = Canvas()
        carve(pl.cv, gcv, lx, ly + 6, 102, 96, kind=1, glow="#ffd27a", inner="#ff9a2a")
        gcv.glow(lx, ly, 420, "#ff8a2a", 0.22)
        G = gcv.rgb()
        pl.offset = lambda t: (40 * math.sin(t * 1.6) + 20 * t, 10 * math.sin(t * 3.2) - 5)

        pl.add_glow(G, lambda t: flicker(t, 13, 0.18, 1.4))
        # ground light near the lantern
        ctx.light("ground", flick(13, 0.18, 1.4)).ellipse(lx + 60, OH * 0.95, 600, 120, "#ff8a2a", 0.10, blur=40)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.5), (0.52, 0.5)), fog=FOG, name="turnip_carried")


def mangel(cv, x, y, r, seed=0):
    sh = rad((x - r * 0.3, y - r * 0.4), r * 1.8, [("#ffe0a0", 1), ("#d89a50", 1), ("#6a3a1a", 1)], [0, 0.5, 1])
    p = smooth_path([(x, y - r * 1.25), (x + r * 0.7, y - r * 0.95), (x + r * 0.85, y - r * 0.1), (x + r * 0.55, y + r * 0.8),
                     (x + r * 0.1, y + r * 1.5), (x - r * 0.05, y + r * 1.5), (x - r * 0.55, y + r * 0.8), (x - r * 0.85, y - r * 0.1),
                     (x - r * 0.7, y - r * 0.95)], True)
    cv.c.drawPath(p, paint(None, shader=sh))
    cv.c.save()
    cv.c.clipPath(p, doAntiAlias=True)
    cv.rect(x - r, y - r * 1.4, x + r, y - r * 0.6, "#8a3a2a", 0.6, blur=r * 0.25)
    cv.c.restore()
    cv.ellipse(x, y - r * 1.12, r * 0.42, r * 0.11, "#1a0c04")


def lantern_wall(dur, mangels=False, seed=0):
    def build(ctx):
        night(ctx, moon=(OW * 0.22, OH * 0.17, 50), seed=61 + seed, clouds=0.5)
        hill(ctx, OH * 0.58, 50, 600, "#0e1c20", 9, haze=("#2a4448", 0.6, 120))
        mist(ctx, OH * 0.60, 50, "#7fa39e", 0.4, seed=10)
        hill(ctx, OH * 0.66, 30, 400, "#081316", 10)
        tree(ctx.cv, OW * 0.85, OH * 0.72, 520, seed=62, spread=0.6)
        ground(ctx, OH * 0.70, "#0a1215", "#040809")
        stone_wall(ctx, OH * 0.70, OH * 1.0, seed=3)
        ctx.flush()
        xs = [0.17, 0.33, 0.50, 0.67, 0.83]
        faces = [1, 0, 1, 2, 0]
        for i, fx in enumerate(xs):
            x = OW * fx
            if mangels and i % 2 == 1:
                ctx.lantern("mangel", x, OH * 0.60, 92, face=faces[i], seed=i, fn=flick(30 + i, 0.18, 1.3))
            else:
                r = 115 if i == 2 else 95
                ctx.lantern("turnip", x, OH * 0.70 - r * 0.95, r, face=faces[i], seed=40 + i, fn=flick(40 + i, 0.16, 1.3))
            ctx.light("wallglow%d" % i, flick(30 + i, 0.18, 1.3)).ellipse(x, OH * 0.74, 260, 60, "#ff8a2a", 0.10, blur=30)
        flock(ctx, "bat", 4, (300, 120, 1500, 420), seed=7, speed=170, size=(20, 34))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.5, 0.5), (0.5, 0.52)),
                   fog=dict(FOG, density=0.22), name="lantern_wall")


def dolmen_scene(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.78, OH * 0.20, 56), seed=71, clouds=0.6)
        hill(ctx, OH * 0.62, 60, 700, "#0e1c20", 11, haze=("#2a4448", 0.6, 120))
        mist(ctx, OH * 0.66, 50, "#7fa39e", 0.42, seed=11)
        prof = hill(ctx, OH * 0.78, 50, 900, "#071013", 12, rim=RIM, rim_a=0.3)
        x = OW * 0.48
        y = float(prof[int(x)]) + 30
        dolmen(ctx, x, y, s=1.15, glow_fn=times(ramp(0.5, dur * 0.8, 0.2, 0.62), flick(3, 0.08, 0.5)))
        grass(ctx.cv, OH, 0, OW, "#020405", n=600, hmin=20, hmax=70, seed=12)
        wisps(ctx, 7, (OW * 0.3, OH * 0.45, OW * 0.7, OH * 0.75), seed=4, fade_in=ramp(1.0, dur * 0.7))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.12, (0.5, 0.56), (0.49, 0.55)),
                   fog=dict(FOG, density=0.32, color="#86b8a8"), name="dolmen")


# ----------------------------------------------------------------------------- Samhain

def harvest_dusk(dur):
    def build(ctx):
        dusk(ctx, sun=(OW * 0.70, OH * 0.66, 36), seed=81, dark=0.15)
        hill(ctx, OH * 0.64, 60, 700, "#2a2230", 13, haze=("#a0605a", 0.4, 80))
        mist(ctx, OH * 0.66, 40, "#e0a080", 0.25, seed=12)
        hill(ctx, OH * 0.72, 40, 500, "#140f18", 14)
        ground(ctx, OH * 0.74, "#120d12", "#040306")
        stooks(ctx, OH * 0.80, OW * 0.05, OW * 0.95, 9, seed=3, s=(80, 120), color="#07050a")
        stooks(ctx, OH * 0.96, OW * 0.0, OW * 1.0, 5, seed=5, s=(160, 220), color="#030205")
        tree(ctx.cv, OW * 0.10, OH * 0.82, 520, seed=82, color="#05040a", spread=0.6)
        ctx.light("warm", ramp(0, dur, 1.0, 0.35)).rect(0, 0, OW, OH, "#ff8a3a", 0.10)
        flock(ctx, "crow", 6, (100, 260, 1200, 520), seed=8, speed=120, size=(16, 26))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.5, 0.52), (0.55, 0.5)), name="harvest_dusk")


def twilight(dur):
    def build(ctx):
        dusk(ctx, sun=None, seed=82, dark=0.72)
        hill(ctx, OH * 0.64, 60, 700, "#141822", 13, haze=("#4a3a4a", 0.4, 80))
        mist(ctx, OH * 0.66, 40, "#9a8a9a", 0.18, seed=12)
        hill(ctx, OH * 0.72, 40, 500, "#090a10", 14)
        ground(ctx, OH * 0.74, "#08080c", "#020204")
        stooks(ctx, OH * 0.80, OW * 0.05, OW * 0.95, 9, seed=3, s=(80, 120), color="#030306")
        cottage(ctx, OW * 0.66, OH * 0.73, s=0.5, lit=1.0, name="cot")
        tree(ctx.cv, OW * 0.10, OH * 0.82, 520, seed=82, color="#030308", spread=0.6)
    return Painted(build, dur=dur, cam=Camera(1.02, 1.08, (0.5, 0.5), (0.5, 0.5)), name="twilight")


def fairy_mound(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.25, OH * 0.16, 50), seed=91, clouds=0.65)
        hill(ctx, OH * 0.60, 50, 700, "#0e1c20", 15, haze=("#2a4448", 0.6, 110))
        mist(ctx, OH * 0.63, 45, "#86b8a8", 0.4, seed=13)
        ground(ctx, OH * 0.70, "#081114", "#020405")
        mound(ctx, OW * 0.55, OH * 0.80, 1100, 330, door_fn=times(flick(5, 0.12, 0.6), ramp(0, 1.5, 0.4, 1)))
        tree(ctx.cv, OW * 0.15, OH * 0.86, 560, seed=92, spread=0.7)
        grass(ctx.cv, OH, 0, OW, "#020405", n=500, hmin=20, hmax=60, seed=13)
        wisps(ctx, 9, (OW * 0.30, OH * 0.40, OW * 0.80, OH * 0.80), seed=6)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.52, 0.56), (0.55, 0.6)),
                   fog=dict(FOG, color="#86b8a8", density=0.3), name="fairy_mound")


def hawthorn(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.58, OH * 0.30, 70), seed=101, clouds=0.45)
        hill(ctx, OH * 0.68, 40, 800, "#0e1c20", 16, haze=("#2a4448", 0.6, 110))
        mist(ctx, OH * 0.70, 40, "#7fa39e", 0.4, seed=14)
        prof = hill(ctx, OH * 0.80, 70, 900, "#061012", 17, rim=RIM, rim_a=0.35)
        x = OW * 0.56
        tree(ctx.cv, x, float(prof[int(x)]) + 8, 760, seed=103, spread=0.95, gnarl=0.55, droop=0.25, lean=-0.08,
             start_branch=0.22, depth=8)
        grass(ctx.cv, OH, 0, OW, "#020405", n=500, hmin=20, hmax=60, seed=14)
        wisps(ctx, 5, (OW * 0.3, OH * 0.45, OW * 0.8, OH * 0.80), seed=7, color=(0.75, 0.9, 1.0))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.55, 0.5), (0.55, 0.55)), fog=FOG, name="hawthorn")


def offering(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.82, OH * 0.15, 48), seed=111, clouds=0.5)
        hill(ctx, OH * 0.62, 40, 600, "#0e1c20", 18, haze=("#2a4448", 0.6, 100))
        mist(ctx, OH * 0.64, 40, "#7fa39e", 0.35, seed=15)
        ground(ctx, OH * 0.70, "#0a1215", "#030607")
        cottage(ctx, OW * 0.25, OH * 0.78, s=1.6, lit=1.0, name="cot", door_lit=True)
        # stone step with an offering of food and drink
        ctx.cv.rect(690, OH * 0.775, 1010, OH * 0.815, "#0c1113", r=6)
        from interior import bowl, jug
        pc = Canvas()
        bowl(pc, 770, OH * 0.78, s=0.75, color="#3a2a1a", fill="#6a5030")
        jug(pc, 925, OH * 0.78, s=0.62, color="#3a2a1c")
        lay = pc.rgba()
        lay[..., :3] *= 0.28
        ctx.flush()
        comp(ctx.bg, lay)
        ctx.light("cot").glow(840, OH * 0.77, 380, AMBER, 0.14)
        grass(ctx.cv, OH, 0, OW, "#020405", n=400, hmin=20, hmax=60, seed=15)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.12, (0.5, 0.6), (0.55, 0.64)), fog=dict(FOG, density=0.22),
                   name="offering")


def bust(cv, x, y, s, color="#120c08", hat=None, bun=False):
    """Head and shoulders of someone seated behind a table; (x, y) = centre at table height."""
    cv.c.drawPath(smooth_path([(x - 150 * s, y + 10), (x - 140 * s, y - 120 * s), (x - 80 * s, y - 175 * s),
                               (x + 80 * s, y - 175 * s), (x + 140 * s, y - 120 * s), (x + 150 * s, y + 10)], True), paint(color))
    cv.rect(x - 28 * s, y - 230 * s, x + 28 * s, y - 160 * s, color)
    cv.ellipse(x, y - 265 * s, 58 * s, 70 * s, color)
    if bun:
        cv.circle(x + 30 * s, y - 315 * s, 30 * s, color)
    if hat:
        cv.ellipse(x, y - 318 * s, 110 * s, 18 * s, color)
        cv.ellipse(x, y - 345 * s, 62 * s, 40 * s, color)


def empty_chair(dur):
    def build(ctx):
        alb = plaster(OH, OW, "#5a4a3a", seed=5)
        cv = Canvas()
        fireplace(cv, OW * 0.86, OH * 0.70, 420, 400, seed=5)
        # the empty chair at the head of the table, facing us
        cx_, top = OW * 0.50, OH * 0.40
        for px in (cx_ - 115, cx_ + 95):
            cv.rect(px, top, px + 20, OH * 0.76, "#3a2414", r=8)
        cv.c.drawPath(smooth_path([(cx_ - 125, top + 10), (cx_, top - 30), (cx_ + 125, top + 10), (cx_ + 120, top + 40),
                                   (cx_, top + 8), (cx_ - 120, top + 40)], True), paint("#4a2e18"))
        for k in range(5):
            sx = cx_ - 70 + k * 35
            cv.rect(sx, top + 30, sx + 12, OH * 0.66, "#3a2414", r=5)
        cv.rect(cx_ - 135, OH * 0.66, cx_ + 135, OH * 0.69, "#5a3a20", r=6)
        comp(alb, cv.rgba())
        table_top(alb, OH * 0.74, OH, "#5a3a22", seed=4)
        cv = Canvas()
        bust(cv, OW * 0.22, OH * 0.75, 1.05, bun=True)
        bust(cv, OW * 0.78, OH * 0.75, 1.1)
        for px in (OW * 0.22, OW * 0.50, OW * 0.78):
            plate(cv, px, OH * 0.83, 125)
        cup(cv, OW * 0.58, OH * 0.81, 0.85)
        cup(cv, OW * 0.31, OH * 0.81, 0.85)
        tip1 = candle(cv, OW * 0.38, OH * 0.80, 230, 58, color="#c8bba0")
        tip2 = candle(cv, OW * 0.64, OH * 0.80, 200, 54, color="#c8bba0")
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("c1", tip1[0], tip1[1], 260, 2000, "#ffb066", 1.5, flick(1, 0.1)),
                               Light("c2", tip2[0], tip2[1], 250, 2000, "#ffb066", 1.4, flick(2, 0.1)),
                               Light("fire", OW * 0.86, OH * 0.64, 160, 1200, "#ff6a2a", 0.9, flick(3, 0.2, 0.7))],
                    ambient=("#1d2c33", 0.13))
        bed = EmberBed(OW * 0.86, OH * 0.685, 180, 34, seed=6)

        def draw(buf, t):
            bed.draw(buf, t, 0.8)
            g = 1.0 + 0.6 * max(0, math.sin(t * 0.9))
            candle_flame(buf, tip1[0], tip1[1], 13, t * g, seed=1)
            candle_flame(buf, tip2[0], tip2[1], 12, t * g, seed=2)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.16, (0.5, 0.6), (0.5, 0.52)), name="empty_chair")


def guisers_fire(dur):
    def build(ctx):
        night(ctx, moon=None, seed=121, clouds=0.6, stops=[(0, "#030507"), (0.6, "#120d0d"), (1, "#3a1a10")])
        hill(ctx, OH * 0.66, 50, 700, "#120b0a", 19, haze=("#5a2a18", 0.5, 120))
        bonfire(ctx, OW * 0.50, OH * 0.70, size=300, seed=4, embers=70, light_r=1300)
        ground(ctx, OH * 0.72, "#140a06", "#030202")
        pl = ctx.plane(1.15)
        specs = [(0.10, 560, 0.97), (0.24, 690, 1.02), (0.37, 610, 0.99), (0.55, 720, 1.03), (0.70, 600, 0.98),
                 (0.86, 670, 1.01)]
        r = np.random.default_rng(3)
        for i, (fx, h, fy) in enumerate(specs):
            x = OW * fx
            path = hooded(pl.cv, x, OH * fy, h, color="#040202", mask=None, lean=r.uniform(-0.05, 0.05), seed=i)
            pl.cv.c.drawPath(path, paint("#ff8a3a", 0.55, stroke=5, blur=3))
            hooded(pl.cv, x, OH * fy, h, color="#040202", mask=["#cbbfa4", "#b9ae96", "#d6cbb2"][i % 3],
                   lean=0, seed=i)
        pl.offset = lambda t: (28 * t, math.sin(t * 2.2) * 3)
    return Painted(build, dur=dur, cam=Camera(1.02, 1.08, (0.5, 0.55), (0.52, 0.55)), name="guisers_fire")


def hilltop_bonfire(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.18, OH * 0.15, 40), seed=131, clouds=0.5)
        hill(ctx, OH * 0.55, 70, 700, "#0d171b", 20, haze=("#2a3a3c", 0.6, 120))
        distant_fires(ctx, [(OW * 0.12, OH * 0.52), (OW * 0.86, OH * 0.50), (OW * 0.70, OH * 0.54)], seed=3, size=8)
        mist(ctx, OH * 0.57, 40, "#7f8a8a", 0.3, seed=16)
        prof = hill(ctx, OH * 0.70, 80, 1100, "#070b0d", 21, rim="#5a3a2a", rim_a=0.25)
        x = OW * 0.5
        y = float(prof[int(x)]) + 10
        bonfire(ctx, x, y, size=240, seed=8, embers=60, light_r=1100)
        pl = ctx.plane(1.0)
        poses = [dict(arms=((150, 20), (10, 5)), dress=True), dict(arms=((20, 30), (25, 20))),
                 dict(arms=((8, 4), (60, 70)), child=True), dict(arms=((165, 10), (165, 10))),
                 dict(arms=((10, 5), (15, 10)), dress=True), dict(arms=((40, 60), (8, 4)), hat="brim")]
        for fx, pz, hh in zip((-340, -235, -150, 170, 250, 345), poses, (205, 195, 130, 210, 190, 200)):
            figure(pl.cv, x + fx, y + 34, hh, "#040303", **pz)
        ctx.flush()
    return Painted(build, dur=dur, cam=Camera(1.0, 1.12, (0.5, 0.5), (0.5, 0.55)), fog=dict(FOG, density=0.2),
                   name="hilltop_bonfire")


# ----------------------------------------------------------------------------- the church

def church_night(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.75, OH * 0.16, 54), seed=141, clouds=0.45)
        hill(ctx, OH * 0.62, 40, 600, "#0e1c20", 22, haze=("#2a4448", 0.6, 100))
        mist(ctx, OH * 0.64, 40, "#7fa39e", 0.38, seed=17)
        church(ctx.cv, ctx.light("church", flick(6, 0.07, 0.8)), OW * 0.40, OH * 0.74, s=1.0)
        ground(ctx, OH * 0.74, "#0a1215", "#030607")
        gravestones(ctx.cv, OH * 0.84, OW * 0.02, OW * 0.98, 12, seed=9, hmin=80, hmax=170)
        tree(ctx.cv, OW * 0.08, OH * 0.94, 820, seed=142, spread=0.6, lean=0.1)
        grass(ctx.cv, OH, 0, OW, "#020405", n=500, hmin=20, hmax=60, seed=17)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.5), (0.48, 0.52)), fog=FOG, name="church_night")
