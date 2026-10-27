"""Scene builders, part 2: All Hallows' Eve, souls and guisers, Stingy Jack."""
import math

import cv2
import numpy as np
import skia

from core import (OW, OH, W, H, Canvas, Camera, rgb, mix, clamp01, smoothstep, sstep, ease, ease_out, fbm, add_spot,
                  poly_path, smooth_path, paint, lin, rad, ADD, blur, flicker, Noise1, Flame, Embers, Motes, Fog, AMBER,
                  GHOST, MOON, PAPER, INK, BLOOD, text_layer, paste)
from art import (figure, hooded, comp, sky, hills, tree, grass, reeds, farmhouse, church, gravestones, fence, pumpkin,
                 carve, turnip, candle, candle_flame, rim_shape, jack_face, sheet_ghost, lancet, vgrad)
from items import (EmberBed, night, dusk, hill, mist, ground, fog, bonfire, distant_fires, flock, wisps, ghosts, leaves,
                   cottage, gate, signpost, red_eyes, stone_wall, silhouette, porch, string_lights, DARK, RIM)
from interior import (Light, light_scene, plaster, wood, stone_blocks, table_top, fireplace, chair, plate, cup, jug, bowl,
                      soul_cake, falloff)
from scene import Scene, Painted, Blend, Seq, flick, ramp, times, const
from cards import Block, TextScene, paper_card, PARCH
from lib1 import FOG, pulse, graveyard, guisers_fire, hilltop_bonfire, church_night


# ----------------------------------------------------------------------------- panels

class Triptych(Scene):
    """Three scenes side by side as tall panels revealed at given times, with a word under each."""

    def __init__(self, scenes, times_, words, dur):
        super().__init__()
        self.scenes, self.times, self.words, self.dur = scenes, times_, words, dur

    def build(self):
        self.blocks = [Block(w_, "fell", 64, PAPER, W * (i + 0.5) / 3, H * 0.86, t_in=t_ + 0.15, fade=0.5,
                             glow="#ff7a1a", glow_a=0.35) for i, (w_, t_) in enumerate(zip(self.words, self.times))]

    def render(self, t, u):
        self.ensure()
        out = np.zeros((H, W, 3), np.float32)
        pw = W // 3
        for i, (sc, t0) in enumerate(zip(self.scenes, self.times)):
            k = sstep(t0, t0 + 0.5, t)
            if k <= 0:
                continue
            f = sc.render(t, u)
            x0 = (W - pw) // 2
            panel = f[:, x0:x0 + pw]
            out[:, i * pw:(i + 1) * pw] = panel * k
        for i in (1, 2):
            out[:, i * pw - 2:i * pw + 2] = 0
        out[int(H * 0.78):] *= np.linspace(1, 0.25, H - int(H * 0.78), dtype=np.float32)[:, None, None]
        for b in self.blocks:
            b.draw(out, t)
        return out

    def free(self):
        for s in self.scenes:
            s.free()
        self._built = False


def mask_closeup(dur):
    def build(ctx):
        night(ctx, moon=None, seed=5, clouds=0.5, stops=[(0, "#040506"), (0.7, "#160c08"), (1, "#3a1a0c")])
        ctx.light("back", flick(4, 0.15, 1.2)).glow(OW * 0.5, OH * 1.0, 1500, "#ff6a1a", 0.6)
        path = hooded(ctx.cv, OW * 0.5, OH * 1.55, 1500, color="#050302", seed=2)
        ctx.cv.c.drawPath(path, paint("#ff8a3a", 0.6, stroke=6, blur=4))
        hooded(ctx.cv, OW * 0.5, OH * 1.55, 1500, color="#050302", mask="#cbbfa4", seed=2)
        ctx.occlude(path)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06), name="mask_closeup")


# ----------------------------------------------------------------------------- the church

def chapel_interior(dur):
    def build(ctx):
        alb = stone_blocks(OH, OW, "#6a6458", seed=9, bh=64)
        alb[int(OH * 0.80):] = stone_blocks(OH - int(OH * 0.80), OW, "#4a463e", seed=10, bh=50, bw=(150, 260)) * 0.8
        cv = Canvas()
        wins = [OW * 0.22, OW * 0.50, OW * 0.78]
        for wx in wins:
            p = lancet(cv, Canvas(), wx - 85, OH * 0.66, 170, OH * 0.52, "#0d1620", 0.0)
        for px in (OW * 0.36, OW * 0.64):
            cv.rect(px - 50, 0, px + 50, OH * 0.8, "#3e3a34")
            cv.rect(px - 62, OH * 0.76, px + 62, OH * 0.8, "#2e2a26")
        # candle stand
        sx0, sx1 = OW * 0.33, OW * 0.67
        for k, yy in enumerate((OH * 0.74, OH * 0.80, OH * 0.86)):
            cv.rect(sx0 + k * 30, yy, sx1 - k * 30, yy + 10, "#1a1612")
        cv.rect(OW * 0.49, OH * 0.86, OW * 0.51, OH * 1.0, "#1a1612")
        tips = []
        r = np.random.default_rng(4)
        for k, yy in enumerate((OH * 0.74, OH * 0.80, OH * 0.86)):
            n = 9 - k
            for i in range(n):
                x = sx0 + 60 + k * 30 + (sx1 - sx0 - 120 - 60 * k) * i / (n - 1)
                hh = r.uniform(40, 80)
                tip = candle(cv, x, yy, hh, 18, color="#c8bba0")
                tips.append((tip, r.integers(0, 999)))
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("candles", OW * 0.5, OH * 0.72, 300, 2000, "#ffb066", 1.6, flick(5, 0.06, 0.8)),
                               Light("moon", OW * 0.5, OH * 0.3, 600, 2400, "#8fb0c8", 0.35, const(1))],
                    ambient=("#1d2c33", 0.12))
        mc = ctx.light("moon")
        for wx in wins:
            lancet(Canvas(), mc, wx - 85, OH * 0.66, 170, OH * 0.52, "#6d8ea8", 0.8)
            beam = poly_path([(wx - 85, OH * 0.2), (wx + 85, OH * 0.2), (wx + 520, OH * 1.0), (wx + 160, OH * 1.0)])
            mc.c.drawPath(beam, paint("#9fc0d8", 0.10, blur=26))
        mo = Motes(70, OW * 0.15, OW * 0.95, OH * 0.2, OH * 0.95, seed=3, color=(0.8, 0.9, 1.0))

        def draw(buf, t):
            for (tip, sd) in tips:
                candle_flame(buf, tip[0], tip[1], 6, t, seed=int(sd), k=0.9, glow=True)
            mo.draw(buf, t, 0.5)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.45), (0.5, 0.55)), name="chapel")


def votive_candles(dur):
    def build(ctx):
        alb = np.zeros((OH, OW, 3), np.float32)
        alb[:] = rgb("#1a1614")
        cv = Canvas()
        cups = []
        r = np.random.default_rng(6)
        for row, yy in enumerate((OH * 0.38, OH * 0.56, OH * 0.74, OH * 0.92)):
            cv.rect(0, yy + 6, OW, yy + 26, "#120e0c")
            n = 10 + row * 2
            for i in range(n):
                x = (i + 0.5 + (0.5 if row % 2 else 0)) * OW / n
                s = 0.7 + row * 0.18
                cups.append((x, yy, s, r.integers(0, 999), r.random() < 0.85))
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("all", OW * 0.5, OH * 0.65, 600, 2600, "#ff9a4a", 0.9, flick(7, 0.05, 0.6))],
                    ambient=("#1d2c33", 0.06))
        groups = [ctx.light("g%d" % k, flick(20 + k, 0.12, 1.1)) for k in range(3)]
        for i, (x, yy, s, sd, lit) in enumerate(cups):
            col = ["#8a1a12", "#9a5a12", "#7a1a2a"][i % 3]
            ctx.cv.rect(x - 26 * s, yy - 48 * s, x + 26 * s, yy + 6, col, 0.9, r=6 * s)
            ctx.cv.rect(x - 26 * s, yy - 48 * s, x - 18 * s, yy + 6, "#ffffff", 0.08)
            if lit:
                g = groups[i % 3]
                g.rect(x - 24 * s, yy - 44 * s, x + 24 * s, yy + 4, "#ff6a2a", 0.45)
                g.glow(x, yy - 30 * s, 110 * s, "#ffaa55", 0.35)

        def draw(buf, t):
            for (x, yy, s, sd, lit) in cups:
                if lit:
                    candle_flame(buf, x, yy - 40 * s, 8 * s, t, seed=int(sd), k=0.9, glow=False)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.05, 1.15, (0.5, 0.55), (0.5, 0.6)), name="votive")


def three_candles(dur, times_=(1.0, 2.2, 3.4), labels=(("31 October", "the Eve"), ("1 November", "All Saints"),
                                                     ("2 November", "All Souls"))):
    xs = [OW * 0.30, OW * 0.50, OW * 0.70]

    def build(ctx):
        alb = np.zeros((OH, OW, 3), np.float32)
        alb[:] = rgb("#2a2420")
        cv = Canvas()
        cv.rect(0, OH * 0.66, OW, OH, "#3a2a1e")
        tips = []
        for i, x in enumerate(xs):
            cv.ellipse(x, OH * 0.66, 90, 18, "#1a120c")
            tips.append(candle(cv, x, OH * 0.66, 330 - i * 20, 66, color="#d8ccb0"))
        comp(alb, cv.rgba())
        lights = [Light("c%d" % i, tips[i][0], tips[i][1], 260, 1500, "#ffb066", 1.3,
                        times(ramp(times_[i], times_[i] + 0.4), flick(30 + i, 0.08))) for i in range(3)]
        light_scene(ctx, alb, lights, ambient=("#1d2c33", 0.05))

        def draw(buf, t):
            for i, tip in enumerate(tips):
                k = sstep(times_[i], times_[i] + 0.25, t)
                if k > 0:
                    flare = math.exp(-max(0, t - times_[i]) * 6) * 0.6
                    candle_flame(buf, tip[0], tip[1], 15, t, seed=40 + i, k=k)
                    if flare > 0.01:
                        add_spot(buf, tip[0], tip[1] - 20, 40, (1, 0.7, 0.3), flare)
        ctx.dyn.append(draw)
    sc = Painted(build, dur=dur, cam=Camera(1.0, 1.04, (0.5, 0.5), (0.5, 0.5)), name="three_candles")
    blocks = []
    for i, (a, b) in enumerate(labels):
        x = W / 2 + (xs[i] - OW / 2) / 1.15
        blocks.append(Block(a, "sans", 30, AMBER, x, H * 0.80, t_in=times_[i] + 0.2, fade=0.6, tracking=0.12))
        blocks.append(Block(b, "fell", 52, PAPER, x, H * 0.87, t_in=times_[i] + 0.35, fade=0.6))
    return Overlaid(sc, blocks)


class Overlaid(Scene):
    """A scene with text blocks drawn over it in frame space."""

    def __init__(self, scene, blocks):
        super().__init__()
        self.scene, self.blocks = scene, blocks
        self.dur = scene.dur

    def render(self, t, u):
        f = self.scene.render(t, u)
        for b in self.blocks:
            b.draw(f, t)
        return f

    def free(self):
        self.scene.free()


def hallow_card(dur, t_eve=3.0):
    blocks = [Block("hal·low", "fell", 170, INK, W / 2, 330, t_in=0.2, fade=0.8),
              Block("(noun, Old English hālga)", "fell_it", 48, "#5a4a32", W / 2, 465, t_in=0.6, fade=0.8),
              Block("a holy person; a saint", "type", 54, INK, W / 2, 570, t_in=1.0, type_cps=26),
              Block("All Hallows' Eve", "fell", 96, BLOOD, W / 2, 790, t_in=t_eve, fade=0.9)]
    return paper_card(blocks, dur, seed=1)


def word_morph(dur, steps=(0.2, 1.3, 2.3, 3.2)):
    words = ["All Hallows' Eve", "All Hallows' Even", "Hallowe'en", "Halloween"]
    blocks = []
    for i, w_ in enumerate(words):
        last = i == len(words) - 1
        t_out = None if last else steps[i + 1] - 0.15
        blocks.append(Block(w_, "black" if last else "fell", 190 if last else 120, "#f3e6c8", W / 2, H / 2,
                            t_in=steps[i], fade=0.45, t_out=t_out, fade_out=0.35, rise=0,
                            glow="#ff7a1a" if last else None, glow_a=0.7, scale_in=0.04 if last else 0.0))
    return TextScene(blocks, dur, bg="dark", embers=True, drift=0.03, seed=4)


# ----------------------------------------------------------------------------- souls and guisers

def soul_cakes(dur):
    def build(ctx):
        alb = plaster(OH, OW, "#6a5a48", seed=8)
        table_top(alb, OH * 0.62, OH, "#6a4428", seed=5)
        cv = Canvas()
        cx_, cy_ = OW * 0.52, OH * 0.78
        cv.ellipse(cx_, cy_ + 20, 420, 120, "#000000", 0.5, blur=18)
        plate(cv, cx_, cy_, 400, color="#cfc6b0", sy=0.3)
        r = np.random.default_rng(2)
        pos = [(-170, -10), (0, -30), (170, -10), (-90, 40), (90, 40), (0, 10), (-40, -60), (60, -55)]
        for i, (dx, dy) in enumerate(sorted(pos, key=lambda p: p[1])):
            soul_cake(cv, cx_ + dx, cy_ + dy - 10, 95, seed=i)
        tip = candle(cv, OW * 0.27, OH * 0.70, 300, 70, color="#c8bba0")
        jug(cv, OW * 0.80, OH * 0.72, s=1.1, color="#7a5a3a")
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("c", tip[0], tip[1], 480, 2600, "#ffb066", 1.7, flick(12, 0.09))],
                    ambient=("#26363e", 0.17))
        ctx.dyn.append(lambda buf, t: candle_flame(buf, tip[0], tip[1], 15, t, seed=8))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.14, (0.5, 0.6), (0.52, 0.62)), name="soul_cakes")


def guisers_lane(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.5, OH * 0.15, 48), seed=151, clouds=0.5)
        hill(ctx, OH * 0.55, 30, 500, "#0e1c20", 23, haze=("#2a4448", 0.6, 100))
        mist(ctx, OH * 0.57, 40, "#7fa39e", 0.35, seed=18)
        cottage(ctx, OW * 0.02, OH * 0.70, s=1.0, name="cl")
        cottage(ctx, OW * 0.70, OH * 0.66, s=0.8, name="cr")
        ground(ctx, OH * 0.66, "#0a1316", "#030607")
        ctx.cv.c.drawPath(poly_path([(OW * 0.47, OH * 0.62), (OW * 0.53, OH * 0.62), (OW * 0.80, OH), (OW * 0.20, OH)]),
                          paint(None, shader=lin((0, OH * 0.62), (0, OH), [("#2a3c3e", 1), ("#0a1012", 1)])))
        stone_wall(ctx, OH * 0.84, OH, 0, OW * 0.22, seed=5)
        stone_wall(ctx, OH * 0.84, OH, OW * 0.78, OW, seed=6)
        ctx.flush()
        pl = ctx.plane(1.08)
        specs = [(0.40, 330, 0.88, "#cbbfa4"), (0.50, 380, 0.92, "#d6cbb2"), (0.60, 340, 0.89, "#b9ae96")]
        for i, (fx, h, fy, mk) in enumerate(specs):
            path = hooded(pl.cv, OW * fx, OH * fy, h, color="#040506", seed=10 + i)
            pl.cv.c.drawPath(path, paint("#5a7a78", 0.5, stroke=3, blur=2))
            hooded(pl.cv, OW * fx, OH * fy, h, color="#040506", mask=mk, seed=10 + i)
        lx, ly = OW * 0.555, OH * 0.80
        pl.cv.line([(lx, ly - 60), (lx - 10, ly - 120)], "#100a06", 3)
        turnip(pl.cv, lx, ly, 40, seed=5)
        g = Canvas()
        carve(pl.cv, g, lx, ly + 2, 34, 32, kind=1, glow="#ffd27a", inner="#ff9a2a")
        g.glow(lx, ly, 260, "#ff8a2a", 0.3)
        G = g.rgb()
        pl.add_glow(G, lambda t: flicker(t, 3, 0.18, 1.3))
        pl.offset = lambda t: (0, -6 * t + math.sin(t * 6) * 2)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.16, (0.5, 0.6), (0.5, 0.62)), fog=FOG, name="guisers_lane")


def door_open(dur, t_open=1.0):
    dx0, dx1 = OW * 0.40, OW * 0.60
    dy0, dy1 = OH * 0.18, OH * 0.90

    def build(ctx):
        night(ctx, moon=(OW * 0.62, OH * 0.12, 40), seed=161, clouds=0.4)
        hill(ctx, OH * 0.62, 30, 500, "#0e1c20", 24, haze=("#2a4448", 0.6, 100))
        mist(ctx, OH * 0.65, 50, "#7fa39e", 0.45, seed=19)
        ground(ctx, OH * 0.70, "#0a1416", "#030607")
        fig = Canvas()
        path = hooded(fig, OW * 0.505, OH * 0.95, 780, color="#030405", seed=3)
        fig.c.drawPath(path, paint("#7fa39e", 0.6, stroke=4, blur=3))
        hooded(fig, OW * 0.505, OH * 0.95, 780, color="#030405", mask="#d0c4aa", seed=3)
        ctx.flush()
        comp(ctx.bg, fig.rgba())
        # interior wall with the doorway cut out, lit by a candle off to the left
        pl = ctx.plane(1.0)
        walb = plaster(OH, OW, "#5a4a38", seed=4)
        fc = Canvas()
        fc.rect(dx0 - 46, dy0 - 46, dx1 + 46, dy1 + 4, "#4a2e18")
        comp(walb, fc.rgba())
        lm = falloff(OW * 0.12, OH * 0.55, 520, 2600)
        lit = walb * (rgb("#1d2c33")[None, None, :] * 0.10 + lm[..., None] * 1.4 * rgb("#ffb066")[None, None, :])
        alpha = np.ones((OH, OW), np.float32)
        alpha[int(dy0):int(dy1), int(dx0):int(dx1)] = 0
        pl.cv = None
        pl.rgba = np.concatenate([lit * alpha[..., None], alpha[..., None]], axis=2).astype(np.float32)
        pl.finish = lambda: None
        def door(buf, t):
            o = ease(sstep(t_open, t_open + 1.6, t)) * 1.25
            w = (dx1 - dx0) * math.cos(o)
            sk = 40 * math.sin(o)
            pts = np.array([(dx0, dy0), (dx0 + w, dy0 + sk), (dx0 + w, dy1 - sk), (dx0, dy1)], np.float32)
            silhouette(buf, pts, rgb("#2a1a10") * 0.55, 1.0)
            if w > 30:
                for k in (0.33, 0.66):
                    silhouette(buf, np.array([(dx0, dy0 + (dy1 - dy0) * k), (dx0 + w, dy0 + sk + (dy1 - dy0 - 2 * sk) * k),
                                              (dx0 + w, dy0 + sk + (dy1 - dy0 - 2 * sk) * k + 10), (dx0, dy0 + (dy1 - dy0) * k + 10)],
                                             np.float32), (0.05, 0.03, 0.02), 1.0)
        ctx.dyn.append(door)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.12, (0.5, 0.5), (0.5, 0.48), ease_fn=ease), fog=dict(FOG, density=0.2),
                   name="door_open")


def ghost_kid(dur):
    def build(ctx):
        ctx.bg = np.zeros((OH, OW, 3), np.float32)
        ctx.bg[:] = rgb("#05080a")
        lx, ly = porch(ctx, OW * 0.36, OH * 0.80, s=1.2, light_k=1.0)
        ctx.flush()
        kid = Canvas()
        sheet_ghost(kid, OW * 0.62, OH * 0.98, 520, color="#e2e0da")
        kid.c.save()
        pumpkin(kid, OW * 0.70, OH * 0.80, 62, seed=3, base="#e0701e")
        kid.c.restore()
        lay = kid.rgba()
        lm = falloff(lx, ly, 500, 2600)[..., None]
        lay[..., :3] *= (0.10 + 1.4 * lm) * rgb("#ffe0b0")[None, None, :]
        comp(ctx.bg, lay)
        ctx.lantern("pumpkin", OW * 0.20, OH * 0.94, 95, face=0, seed=9)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.55), (0.52, 0.55)), name="ghost_kid")


# ----------------------------------------------------------------------------- Stingy Jack

def jack_figure(cv, x, y, h, color="#030405", lantern=False):
    return figure(cv, x, y, h, color, coat=True, hat="brim", arms=((10, 6), (25, 40) if lantern else (-4, -4)), lean=0.02)


def crossroads(dur, eyes_t=2.5):
    def build(ctx):
        night(ctx, moon=(OW * 0.80, OH * 0.16, 44), seed=171, clouds=0.6)
        hill(ctx, OH * 0.55, 40, 600, "#0e1c20", 25, haze=("#2a4448", 0.6, 100))
        ctx.flush()
        for i in range(14):
            tree(ctx.cv, OW * (0.02 + i * 0.075), OH * 0.66, 300 + 80 * math.sin(i * 1.7), seed=200 + i, spread=0.6,
                 color="#030607")
        ctx.flush()
        mist(ctx, OH * 0.64, 40, "#7fa39e", 0.35, seed=20)
        ground(ctx, OH * 0.66, "#0a1316", "#030607")
        ctx.cv.c.drawPath(poly_path([(0, OH * 0.74), (OW, OH * 0.72), (OW, OH * 0.80), (0, OH * 0.83)]),
                          paint("#22343a", 0.9))
        ctx.cv.c.drawPath(poly_path([(OW * 0.48, OH * 0.66), (OW * 0.52, OH * 0.66), (OW * 0.75, OH), (OW * 0.30, OH)]),
                          paint(None, shader=lin((0, OH * 0.66), (0, OH), [("#2a3c3e", 1), ("#0a1012", 1)])))
        signpost(ctx, OW * 0.36, OH * 0.80, s=1.2)
        jack_figure(ctx.cv, OW * 0.58, OH * 0.86, 430)
        red_eyes(ctx, OW * 0.25, OH * 0.58, s=1.2, fn=times(ramp(eyes_t, eyes_t + 1.0), flick(9, 0.1, 0.4)))
        grass(ctx.cv, OH, 0, OW, "#020405", n=500, hmin=20, hmax=60, seed=21)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.55), (0.46, 0.55)), fog=FOG, name="crossroads")


def locked_gate(dur):
    def build(ctx):
        night(ctx, moon=None, seed=181, clouds=0.5)
        hill(ctx, OH * 0.60, 30, 600, "#0e1c20", 26, haze=("#2a4448", 0.6, 100))
        ground(ctx, OH * 0.70, "#0a1316", "#030607")
        gate(ctx, OW * 0.55, OH * 0.86, s=1.6)
        jack_figure(ctx.cv, OW * 0.22, OH * 0.95, 520)
        grass(ctx.cv, OH, 0, OW, "#020405", n=400, hmin=20, hmax=60, seed=22)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.48, 0.55), (0.52, 0.52)), fog=FOG, name="locked_gate")


def coal(dur):
    def build(ctx):
        ctx.bg = np.zeros((OH, OW, 3), np.float32)
        alb = stone_blocks(OH, OW, "#3a3632", seed=12, bh=120, bw=(200, 340)) * 0.5
        light_scene(ctx, alb, [Light("coal", OW * 0.5, OH * 0.62, 260, 1500, "#ff6a2a", 1.2, flick(14, 0.2, 0.8))],
                    ambient=("#1d2c33", 0.04))
        cx_, cy_ = OW * 0.5, OH * 0.62
        lump = Canvas()
        lump.c.drawPath(smooth_path([(cx_ - 150, cy_ + 30), (cx_ - 120, cy_ - 70), (cx_ - 20, cy_ - 105), (cx_ + 90, cy_ - 80),
                                     (cx_ + 160, cy_ - 10), (cx_ + 120, cy_ + 50), (cx_, cy_ + 70)], True), paint("#0a0605"))
        ctx.flush()
        la = lump.rgba()
        comp(ctx.bg, la)
        m = la[..., 3]
        y0, y1, x0, x1 = int(cy_ - 120), int(cy_ + 80), int(cx_ - 170), int(cx_ + 170)
        mask = m[y0:y1, x0:x1]
        n1 = fbm(y1 - y0, x1 - x0, scale=22, octaves=4, seed=3)
        n2 = fbm(y1 - y0, x1 - x0, scale=10, octaves=3, seed=4)
        from core import fire_lut
        lut = fire_lut()
        em = Embers(30, cx_ - 80, cx_ + 80, cy_ - 60, rise=220, spread=50, life=(1.5, 3.0), seed=9)

        inner = cv2.erode(mask, np.ones((9, 9), np.uint8))

        def draw(buf, t):
            a = 0.5 + 0.5 * math.sin(t * 1.3)
            crack = np.abs(n1 * (0.7 + 0.3 * a) + n2 * 0.3 - 0.5)
            heat = smoothstep(0.035, 0.0, crack) * inner * (0.75 + 0.25 * flicker(t, 3, 0.5, 1.5))
            heat = np.maximum(heat, inner * 0.12 * smoothstep(0.45, 0.8, n2))
            buf[y0:y1, x0:x1] += lut[(clamp01(heat) * 255).astype(np.uint8)] * 1.1
            em.draw(buf, t, 0.8)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.08, 1.2, (0.5, 0.52), (0.5, 0.5)), name="coal")


def jack_wanders(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.20, OH * 0.22, 40), seed=191, clouds=0.55)
        hill(ctx, OH * 0.58, 30, 700, "#0e1c20", 27, haze=("#2a4448", 0.6, 100))
        mist(ctx, OH * 0.60, 50, "#7fa39e", 0.4, seed=23)
        ground(ctx, OH * 0.62, "#0a1416", "#030607")
        reeds(ctx.cv, OH, 0, OW, "#020405", n=180, hmin=40, hmax=150, seed=4)
        pl = ctx.plane(1.0)
        x, y = OW * 0.60, OH * 0.74
        info = figure(pl.cv, x, y, 150, "#030405", coat=True, hat="brim", arms=((10, 6), (30, 30)))
        hx, hy = info["hands"][1]
        g = Canvas()
        turnip(pl.cv, hx + 4, hy + 30, 14, seed=3)
        g.glow(hx + 4, hy + 30, 160, "#ff8a2a", 0.45)
        g.glow(hx + 4, hy + 30, 22, "#ffd27a", 0.9)
        G = g.rgb()
        pl.add_glow(G, lambda t: flicker(t, 6, 0.2, 1.4))
        pl.offset = lambda t: (-22 * t, math.sin(t * 5) * 1.5)
        wisps(ctx, 5, (OW * 0.1, OH * 0.55, OW * 0.9, OH * 0.70), seed=8, color=(1.0, 0.75, 0.4), size=(3, 6))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.55), (0.5, 0.55)), fog=dict(FOG, density=0.32),
                   name="jack_wanders")


def bog_wisps(dur):
    def build(ctx):
        night(ctx, moon=(OW * 0.75, OH * 0.28, 50), seed=201, clouds=0.5)
        hill(ctx, OH * 0.56, 25, 700, "#0e1c20", 28, haze=("#2a4448", 0.6, 100))
        mist(ctx, OH * 0.58, 40, "#7fa39e", 0.4, seed=24)
        ground(ctx, OH * 0.60, "#0a1416", "#030607")
        ctx.flush()
        r = np.random.default_rng(3)
        pools = Canvas()
        for _ in range(9):
            px, py = r.uniform(0, OW), r.uniform(OH * 0.64, OH * 0.95)
            rx = r.uniform(120, 420) * (0.4 + (py - OH * 0.6) / OH)
            pools.c.drawPath(smooth_path([(px - rx, py), (px - rx * 0.5, py - rx * 0.09), (px + rx * 0.4, py - rx * 0.11),
                                          (px + rx, py - rx * 0.02), (px + rx * 0.6, py + rx * 0.08), (px - rx * 0.4, py + rx * 0.1)], True),
                             paint("#1c3034", 0.85, blur=3))
            pools.ellipse(px + rx * 0.1, py - rx * 0.03, rx * 0.55, rx * 0.025, "#8aa8a6", 0.18, blur=2)
        comp(ctx.bg, pools.rgba())
        reeds(ctx.cv, OH * 0.66, 0, OW, "#04080a", n=120, hmin=30, hmax=90, seed=5)
        reeds(ctx.cv, OH, 0, OW, "#020405", n=160, hmin=80, hmax=260, seed=6)
        wisps(ctx, 10, (OW * 0.1, OH * 0.50, OW * 0.9, OH * 0.80), seed=9, color=(0.75, 1.0, 0.55), size=(4, 8))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.5, 0.55), (0.55, 0.55)), fog=dict(FOG, density=0.3),
                   name="bog")
