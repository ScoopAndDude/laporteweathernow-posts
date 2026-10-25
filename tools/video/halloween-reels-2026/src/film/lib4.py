"""Scene builders, part 4: the Martians, war and sugar, poison in the candy bag."""
import math

import cv2
import numpy as np
import skia

from core import (OW, OH, W, H, Canvas, Camera, rgb, mix, clamp01, smoothstep, sstep, ease, ease_out, fbm, add_spot,
                  poly_path, smooth_path, paint, lin, rad, ADD, blur, flicker, Noise1, Flame, Embers, Motes, Fog, AMBER,
                  GHOST, MOON, PAPER, INK, BLOOD, text_layer, paste, font)
from art import (figure, hooded, comp, sky, hills, tree, grass, farmhouse, gravestones, fence, pumpkin, carve, candle,
                 candle_flame, rim_shape, sheet_ghost, vgrad)
from items import (night, dusk, hill, mist, ground, fog, flock, leaves, silhouette, porch, string_lights, town_row,
                   gas_lamp, street_lamp_modern, kids_walking, DARK, RIM)
from interior import (Light, light_scene, plaster, wood, stone_blocks, table_top, chair, plate, cup, bowl, falloff,
                      radio_cathedral, ration_book, candy_pile, apple_on_stick, lightbox)
from scene import Scene, Painted, Blend, Seq, flick, ramp, times, const, cropped
from cards import Block, TextScene, paper_card, PARCH, stamp, newsprint_texture, paper_texture, big_number, dark_bg
from lib1 import FOG, pulse
from lib2 import Overlaid


# ----------------------------------------------------------------------------- the Martians

def radio_room(dur):
    def build(ctx):
        alb = np.zeros((OH, OW, 3), np.float32)
        wall = plaster(OH, OW, "#5a5040", seed=41)
        stripes = ((np.arange(OW) // 90) % 2).astype(np.float32)
        alb[:] = wall * (0.9 + 0.1 * stripes)[None, :, None]
        alb[int(OH * 0.78):] = wood(OH - int(OH * 0.78), OW, "#3a2a1c", seed=42, along="x", boards=5)
        cv = Canvas()
        rx, ry = OW * 0.62, OH * 0.66
        cv.rect(rx - 260, ry, rx + 260, ry + 30, "#3a2414", r=6)
        for lx in (rx - 230, rx + 210):
            cv.rect(lx, ry + 30, lx + 20, OH * 0.84, "#2a1a10")
        dial = radio_cathedral(cv, rx, ry, s=1.1)
        # an armchair seen from behind, someone listening in it, and a child on the rug
        cv.c.drawPath(smooth_path([(OW * 0.10, OH * 0.86), (OW * 0.09, OH * 0.50), (OW * 0.14, OH * 0.44), (OW * 0.28, OH * 0.44),
                                   (OW * 0.33, OH * 0.50), (OW * 0.32, OH * 0.86)], True), paint("#3a2418"))
        cv.ellipse(OW * 0.215, OH * 0.405, 62, 74, "#120c08")
        cv.c.drawPath(smooth_path([(OW * 0.17, OH * 0.47), (OW * 0.215, OH * 0.44), (OW * 0.26, OH * 0.47)], False),
                      paint("#120c08", stroke=40))
        cv.ellipse(OW * 0.44, OH * 0.70, 48, 56, "#120c08")
        cv.c.drawPath(smooth_path([(OW * 0.38, OH * 0.82), (OW * 0.39, OH * 0.74), (OW * 0.44, OH * 0.72), (OW * 0.49, OH * 0.74),
                                   (OW * 0.50, OH * 0.82)], True), paint("#120c08"))
        comp(alb, cv.rgba())
        glow = lambda t: 0.85 + 0.15 * flicker(t, 44, 0.6, 2.5)
        light_scene(ctx, alb, [Light("radio", dial[0], dial[1], 380, 2400, "#ffb066", 1.5, glow),
                               Light("lamp", OW * 0.05, OH * 0.2, 500, 2400, "#ffd8a0", 0.35, const(1))],
                    ambient=("#1d2c33", 0.10))
        lc = ctx.light("dial", glow)
        lc.circle(dial[0], dial[1], 30, "#ffcf7a", 1.0)
        lc.glow(dial[0], dial[1], 140, "#ffb066", 0.6)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.48, 0.55), (0.55, 0.55)), name="radio_room")


def radio_closeup(dur, needle=None):
    """Close on the radio's dial. needle = (t0, t1, f0, f1) moves the pointer between dial fractions."""
    def build(ctx):
        alb = wood(OH, OW, "#6a3a1a", seed=45, along="x") * 0.9
        cv = Canvas()
        dx, dy = OW * 0.5, OH * 0.50
        cv.circle(dx, dy, 330, "#2a1408")
        cv.circle(dx, dy, 300, "#c8a868")
        cv.circle(dx, dy, 280, "#e8d4a0")
        for i in range(11):
            a = math.radians(-150 + i * 30)
            cv.line([(dx + math.cos(a) * 230, dy + math.sin(a) * 230), (dx + math.cos(a) * 262, dy + math.sin(a) * 262)],
                    "#3a2a14", 4)
        comp(alb, cv.rgba())
        ctx.flush()
        for i, lab in enumerate(["55", "60", "70", "80", "100", "120", "140", "160"]):
            a = math.radians(-150 + i * 300 / 7)
            lay = text_layer(lab, "old_b", 40, "#3a2a14")
            paste(alb, lay, dx + math.cos(a) * 195, dy + math.sin(a) * 195)
        glow = lambda t: 0.85 + 0.15 * flicker(t, 44, 0.6, 2.5)
        light_scene(ctx, alb, [Light("dial", dx, dy, 420, 1800, "#ffb066", 1.3, glow)], ambient=("#1d2c33", 0.12))
        lc = ctx.light("face", glow)
        lc.circle(dx, dy, 280, "#ff9a3a", 0.35)

        def draw(buf, t):
            f = 0.62
            if needle:
                t0, t1, f0, f1 = needle
                f = f0 + (f1 - f0) * ease(sstep(t0, t1, t))
            a = math.radians(-150 + f * 300)
            p0 = (dx - math.cos(a) * 40, dy - math.sin(a) * 40)
            p1 = (dx + math.cos(a) * 250, dy + math.sin(a) * 250)
            cv2.line(buf, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), (0.55, 0.06, 0.03), 22,
                     cv2.LINE_AA, shift=2)
            add_spot(buf, dx, dy, 14, (0.2, 0.1, 0.05), 0.5)
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.05, 1.18, (0.5, 0.5), (0.5, 0.5)), name="radio_closeup")


def bulletin(dur):
    def static(frame, t, u):
        r = np.random.default_rng(int(t * 24) + 100000)
        n = r.normal(0, 1, (H // 6, W // 6)).astype(np.float32)
        n = cv2.resize(n, (W, H), interpolation=cv2.INTER_NEAREST)
        frame += n[..., None] * 0.03
        for _ in range(4):
            y = r.integers(0, H)
            frame[y:y + r.integers(2, 6)] += 0.08
    blocks = [Block("BULLETIN", "old_b", 210, "#e8d8b0", W / 2, H * 0.44, t_in=0.15, fade=0.12, rise=0, glow="#ff3a1a",
                    glow_a=0.45),
              Block("“We interrupt this program…”", "type", 54, "#c8b890", W / 2, H * 0.64, t_in=0.6, type_cps=24)]
    return TextScene(blocks, dur, bg="dark", fog=False, drift=0.06, seed=9, extra=[static])


def tripod(dur, beam_t=1.0):
    def build(ctx):
        night(ctx, moon=None, seed=331, clouds=0.7, stops=[(0, "#030405"), (0.6, "#0a1210"), (1, "#1a2a24")])
        hill(ctx, OH * 0.62, 20, 700, "#0c1614", 41, haze=("#2a3a34", 0.6, 100))
        farmhouse(ctx.cv, ctx.light("farm", flick(6, 0.05)), OW * 0.10, OH * 0.66, s=0.45)
        ctx.flush()
        ground(ctx, OH * 0.66, "#0c1410", "#030504")
        cv = ctx.cv
        for k in range(18):
            x0 = OW * (k / 17)
            cv.line([(OW * 0.5 + (x0 - OW * 0.5) * 0.05, OH * 0.66), (x0 * 3 - OW, OH)], "#050806", 6, a=0.8)
        # the machine
        tx, ty = OW * 0.62, OH * 0.30
        legs = [((tx - 40, ty + 40), (tx - 330, ty + 350), (tx - 420, OH * 0.70)),
                ((tx + 40, ty + 40), (tx + 280, ty + 330), (tx + 360, OH * 0.69)),
                ((tx, ty + 50), (tx + 30, ty + 380), (tx - 40, OH * 0.73))]
        for a, b, c in legs:
            cv.line([a, b], "#020303", 16)
            cv.line([b, c], "#020303", 11)
            cv.circle(b[0], b[1], 14, "#020303")
        body = smooth_path([(tx - 170, ty + 30), (tx - 120, ty - 70), (tx, ty - 110), (tx + 140, ty - 60), (tx + 180, ty + 30),
                            (tx + 60, ty + 70), (tx - 80, ty + 70)], True)
        rim_shape(cv, body, "#020303", "#5a6a60", (-3, -3), rim_a=0.5)
        cv.line([(tx + 150, ty + 10), (tx + 260, ty + 60)], "#020303", 10)
        lc = ctx.light("eye", flick(7, 0.2, 2.0))
        lc.circle(tx + 60, ty - 10, 12, "#ff3a1a", 1.0)
        lc.glow(tx + 60, ty - 10, 90, "#ff3a1a", 0.6)
        ctx.flush()
        beam = Canvas()
        beam.c.drawPath(poly_path([(tx + 260, ty + 60), (tx + 270, ty + 50), (OW * 0.35, OH * 0.98), (OW * 0.10, OH * 0.98)]),
                        paint("#c8ffe0", 0.16, blur=18))
        beam.glow(tx + 262, ty + 56, 70, "#e0fff0", 0.9)
        beam.ellipse(OW * 0.22, OH * 0.95, 260, 60, "#c8ffe0", 0.25, blur=30)
        ctx.light_np("beam", beam.rgb(), times(ramp(beam_t, beam_t + 0.6), lambda t: 0.85 + 0.15 * math.sin(t * 13)))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.1, (0.55, 0.45), (0.58, 0.5)),
                   fog=dict(FOG, density=0.34, color="#8fb0a0"), name="tripod")


def newspapers(dur, n=2):
    def make_paper(seed, w=900, h=1180):
        tex = cv2.resize(newsprint_texture(seed), (w, h))
        img = tex.copy()
        r = np.random.default_rng(seed)
        cv2.rectangle(img, (40, 40), (w - 40, 160), (0.12, 0.11, 0.1), -1)
        cv2.rectangle(img, (40, 175), (w - 40, 180), (0.2, 0.2, 0.2), -1)
        lay = text_layer("OCT. 31, 1938", "type", 34, "#2a2622")
        paste(img, lay, w / 2, 205)
        cv2.rectangle(img, (60, 250), (w - 60, 330), (0.1, 0.1, 0.1), -1)
        cv2.rectangle(img, (110, 350), (w - 110, 395), (0.18, 0.18, 0.18), -1)
        for col in range(3):
            x0 = 50 + col * (w - 100) // 3
            for y in range(430, h - 50, 22):
                x = x0
                while x < x0 + (w - 100) // 3 - 30:
                    wl = r.uniform(18, 70)
                    cv2.rectangle(img, (int(x), y), (int(min(x + wl, x0 + (w - 100) // 3 - 30)), y + 8), (0.42, 0.4, 0.38), -1)
                    x += wl + 10
        img = cv2.GaussianBlur(img, (0, 0), 0.8)
        return img
    papers = [make_paper(i) for i in range(n)]

    def draw(frame, t, u):
        for i, pimg in enumerate(papers):
            t0 = i * 1.4
            p = ease_out(sstep(t0, t0 + 1.0, t))
            if p <= 0:
                continue
            ang = (1 - p) * 720 + (i * 9 - 4)
            sc = 0.05 + 0.75 * p
            h_, w_ = pimg.shape[:2]
            m = cv2.getRotationMatrix2D((w_ / 2, h_ / 2), ang, sc)
            m[0, 2] += W / 2 - w_ / 2 + (i - 0.5) * 220
            m[1, 2] += H / 2 - h_ / 2 + i * 30
            warped = cv2.warpAffine(pimg, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
            mask = cv2.warpAffine(np.ones((h_, w_), np.float32), m, (W, H), flags=cv2.INTER_LINEAR)
            sh = cv2.GaussianBlur(mask, (0, 0), 18)
            frame *= (1 - 0.6 * sh[..., None])
            frame *= (1 - mask[..., None])
            frame += warped * 0.9
    return TextScene([], dur, bg="dark", fog=False, drift=0.03, seed=10, extra=[draw])


# ----------------------------------------------------------------------------- war and sugar

def searchlights(dur):
    def build(ctx):
        night(ctx, moon=None, seed=341, clouds=0.75, stops=[(0, "#020304"), (0.7, "#0a1216"), (1, "#16242a")])
        town_row(ctx, OH * 0.86, -40, OW + 40, seed=21, hmin=200, hmax=480, lit_p=0.0, color="#020304", rim="#1a2628")
        ctx.flush()
        beams = []
        for k, (bx, a0, sp) in enumerate(((0.15, -60, 0.35), (0.42, -100, -0.25), (0.70, -80, 0.3), (0.90, -120, -0.4))):
            beams.append((OW * bx, OH * 0.86, a0, sp, k))
        sprite = np.zeros((60, 1800, 3), np.float32)
        xs = np.linspace(0, 1, 1800, dtype=np.float32)[None, :]
        ys = np.linspace(-1, 1, 60, dtype=np.float32)[:, None]
        prof = np.exp(-(ys / (0.25 + 0.75 * xs)) ** 2) * (1 - xs) ** 0.6
        sprite[:] = (prof * 0.35)[..., None] * rgb("#d8e8f0")

        def draw(buf, t):
            for (bx, by, a0, sp, k) in beams:
                a = math.radians(a0 + 25 * math.sin(t * sp + k))
                ca, sa = math.cos(a), math.sin(a)
                m = np.array([[ca, -sa, bx], [sa, ca, by]], np.float32)
                # scale the sprite's height with distance (fan out)
                m[:, 1] *= 6.0
                m[0, 2] = bx - m[0, 1] * 30
                m[1, 2] = by - m[1, 1] * 30
                w = cv2.warpAffine(sprite, m, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                buf += w
        ctx.dyn.append(draw)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.5, 0.5), (0.5, 0.52)), name="searchlights")


def ration_scene(dur):
    def build(ctx):
        alb = np.zeros((OH, OW, 3), np.float32)
        table_top(alb, 0, OH, "#7a5a3a", seed=51)
        cv = Canvas()
        ration_book(cv, OW * 0.40, OH * 0.52, s=1.2, rot=-7)
        bowl(cv, OW * 0.76, OH * 0.70, s=1.5, color="#e8e2d6", fill="#f6f2ea")
        cv.line([(OW * 0.70, OH * 0.62), (OW * 0.86, OH * 0.48)], "#b8bcc0", 12)
        cv.ellipse(OW * 0.70, OH * 0.63, 30, 16, "#c8ccd0")
        comp(alb, cv.rgba())
        ctx.flush()
        tl = text_layer("UNITED STATES OF AMERICA", "old_b", 27, "#2a3a5a", tracking=0.1)
        tl2 = text_layer("WAR RATION BOOK ONE", "old_b", 39, "#2a3a5a", tracking=0.04)
        tl3 = text_layer("OFFICE OF PRICE ADMINISTRATION", "old", 21, "#2a3a5a", tracking=0.08)
        for L_, yy in ((tl, -250), (tl2, -180), (tl3, -110)):
            Lr = cv2.warpAffine(L_, cv2.getRotationMatrix2D((L_.shape[1] / 2, L_.shape[0] / 2), 7, 1.0),
                                (L_.shape[1], L_.shape[0]))
            dx_ = math.sin(math.radians(7)) * yy
            paste(alb, Lr, OW * 0.40 + dx_, OH * 0.52 + yy * math.cos(math.radians(7)))
        light_scene(ctx, alb, [Light("lamp", OW * 0.5, OH * 0.2, 700, 2600, "#ffe0b0", 1.4, const(1))],
                    ambient=("#26363e", 0.18))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.12, (0.45, 0.5), (0.42, 0.48)), name="ration")


def street_1950s(dur, kids_speed=70):
    def build(ctx):
        dusk(ctx, sun=None, seed=351, dark=0.55, clouds=0.3)
        cv = ctx.cv
        for k, (x0, w_, h_) in enumerate(((-60, 760, 300), (760, 700, 280), (1520, 760, 300))):
            y = OH * 0.70
            body = poly_path([(x0, y), (x0, y - h_ * 0.62), (x0 + w_ * 0.5, y - h_), (x0 + w_, y - h_ * 0.62), (x0 + w_, y)])
            rim_shape(cv, body, "#0a0c10", "#5a4a5a", (3, 3), rim_a=0.5)
            lc = ctx.light("h%d" % k, flick(70 + k, 0.03, 0.4))
            for wx in (x0 + w_ * 0.18, x0 + w_ * 0.68):
                cv.rect(wx, y - h_ * 0.45, wx + 120, y - h_ * 0.18, "#2a1a0a")
                lc.rect(wx, y - h_ * 0.45, wx + 120, y - h_ * 0.18, "#ffcf8a", 0.8)
                lc.glow(wx + 60, y - h_ * 0.3, 200, "#ffcf8a", 0.2)
            px, py = x0 + w_ * 0.45, y - h_ * 0.30
            lc.glow(px, py, 260, "#ffe2a8", 0.4)
            lc.circle(px, py, 12, "#fff2d0", 1.0)
        ctx.flush()
        ground(ctx, OH * 0.70, "#14121a", "#050508")
        cv = ctx.cv
        cv.rect(0, OH * 0.80, OW, OH * 0.84, "#2a2830")
        street_lamp_modern(ctx, OW * 0.86, OH * 0.82, s=1.2)
        for i, fx in enumerate((0.12, 0.40, 0.64)):
            ctx.lantern("pumpkin", OW * fx, OH * 0.72, 34, face=i % 3, seed=80 + i)
        tree(ctx.cv, OW * 0.30, OH * 0.80, 600, seed=91, color="#050508", spread=0.6)
        kids_walking(ctx, [dict(x=OW * 0.10, y=OH * 0.95, h=300, kind="ghost", bucket=True),
                           dict(x=OW * 0.20, y=OH * 0.96, h=330, kind="witch", bucket=True),
                           dict(x=OW * 0.29, y=OH * 0.95, h=280, kind="cape"),
                           dict(x=OW * 0.40, y=OH * 0.97, h=520, kind="adult")], speed=kids_speed)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.06, (0.45, 0.55), (0.5, 0.55)), name="street_50s")


class TimelineScene(Scene):
    def __init__(self, dur, events, y0=1947, y1=1953, t_line=0.3):
        super().__init__()
        self.dur, self.events, self.y0, self.y1, self.t_line = dur, events, y0, y1, t_line

    def build(self):
        self.bg = dark_bg(1)
        self.ticks = {}
        for y in range(self.y0, self.y1 + 1):
            self.ticks[y] = text_layer(str(y), "sans", 30, "#9fb8b2")
        self.blocks = []
        for i, (yr, title, t0) in enumerate(self.events):
            x = self.xof(yr)
            up = i % 2 == 0
            self.blocks.append(Block(str(yr), "fell", 64, AMBER, x, H * (0.33 if up else 0.71), t_in=t0, fade=0.5))
            self.blocks.append(Block(title, "fell_it", 46, PAPER, x, H * (0.40 if up else 0.78), t_in=t0 + 0.15, fade=0.6,
                                     max_w=520))
        from core import Fog
        self.fog = Fog(seed=4, density=0.18, top=0.0, bottom=1.0, color="#6f9690", speed=12)

    def xof(self, yr):
        return W * 0.12 + (yr - self.y0) / (self.y1 - self.y0) * W * 0.76

    def render(self, t, u):
        self.ensure()
        f = self.bg.copy()
        self.fog.apply(f, t)
        p = ease(sstep(self.t_line, self.t_line + 1.2, t))
        x1 = W * 0.08 + p * W * 0.84
        cv2.line(f, (int(W * 0.08), int(H * 0.55)), (int(x1), int(H * 0.55)), tuple(float(c) for c in rgb("#8a7a5a")), 3,
                 cv2.LINE_AA)
        for y, lay in self.ticks.items():
            x = self.xof(y)
            if x <= x1:
                cv2.line(f, (int(x), int(H * 0.55) - 10), (int(x), int(H * 0.55) + 10), (0.6, 0.55, 0.45), 2, cv2.LINE_AA)
                paste(f, lay, x, H * 0.55 + 36, a=0.7)
        for yr, title, t0 in self.events:
            if t >= t0:
                k = sstep(t0, t0 + 0.3, t)
                add_spot(f, self.xof(yr), H * 0.55, 10, (1.0, 0.6, 0.2), 1.2 * k)
        for b in self.blocks:
            b.draw(f, t)
        return f


# ----------------------------------------------------------------------------- poison in the candy bag

def candy_table(dur, heartbeat=True):
    def build(ctx):
        alb = np.zeros((OH, OW, 3), np.float32)
        alb[:] = rgb("#2a2622")
        table_top(alb, OH * 0.38, OH, "#8a7a62", seed=61)
        cv = Canvas()
        candy_pile(cv, OW * 0.18, OH * 0.55, OW * 0.82, OH * 0.95, n=90, seed=3)
        bx, by = OW * 0.50, OH * 0.52
        cv.c.drawPath(poly_path([(bx - 170, by + 190), (bx - 150, by - 180), (bx + 150, by - 180), (bx + 170, by + 190)]),
                      paint(None, shader=lin((bx - 170, 0), (bx + 170, 0), [("#6a4a2a", 1), ("#a8845a", 1), ("#7a5a36", 1)])))
        cv.c.drawPath(poly_path([(bx - 150, by - 180), (bx - 120, by - 230), (bx + 120, by - 230), (bx + 150, by - 180)]),
                      paint("#8a6a44"))
        comp(alb, cv.rgba())
        face = Canvas()
        from art import jack_face
        for shp in jack_face(0):
            face.poly([(bx + px * 95, by + 10 + py * 90) for px, py in shp], "#2a1a0a")
        comp(alb, face.rgba())
        beat = (lambda t: 1.0 + 0.10 * (math.exp(-((t % 1.1) / 0.08) ** 2) + 0.6 * math.exp(-(((t % 1.1) - 0.25) / 0.08) ** 2))) \
            if heartbeat else const(1)
        light_scene(ctx, alb, [Light("lamp", OW * 0.5, OH * 0.30, 520, 1500, "#ffe8c0", 1.7, beat)],
                    ambient=("#1d2c33", 0.05))
        ctx.light("cone", const(1)).c.drawPath(poly_path([(OW * 0.47, 0), (OW * 0.53, 0), (OW * 0.80, OH), (OW * 0.20, OH)]),
                                               paint("#ffe8c0", 0.035, blur=40))
        lc = ctx.light("bulb", const(1))
        ctx.cv.rect(OW * 0.497, 0, OW * 0.503, OH * 0.06, "#050505")
        ctx.cv.c.drawPath(poly_path([(OW * 0.44, OH * 0.12), (OW * 0.56, OH * 0.12), (OW * 0.52, OH * 0.06), (OW * 0.48, OH * 0.06)]),
                          paint("#101010"))
        lc.ellipse(OW * 0.5, OH * 0.12, 60, 12, "#fff6e0", 1.0)
        lc.glow(OW * 0.5, OH * 0.13, 200, "#ffe8c0", 0.5)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.14, (0.5, 0.5), (0.5, 0.58)), name="candy_table")


def candy_apple(dur, glint_t=3.0):
    def build(ctx):
        alb = np.zeros((OH, OW, 3), np.float32)
        alb[:] = rgb("#241e1a")
        table_top(alb, OH * 0.62, OH, "#6a5a48", seed=62)
        cv = Canvas()
        plate(cv, OW * 0.5, OH * 0.80, 330, sy=0.3)
        apple_on_stick(cv, OW * 0.5, OH * 0.64, 190)
        comp(alb, cv.rgba())
        light_scene(ctx, alb, [Light("key", OW * 0.3, OH * 0.2, 600, 2400, "#ffe0c0", 1.4, const(1))],
                    ambient=("#26363e", 0.10))

        def glint(buf, t):
            d = t - glint_t
            if -0.1 < d < 1.2:
                k = math.exp(-abs(d - 0.25) * 5)
                x, y = OW * 0.555, OH * 0.60
                cv2.line(buf, (int(x * 4), int(y * 4)), (int((x + 60) * 4), int((y - 40) * 4)), (0.85, 0.85, 0.9), 5, cv2.LINE_AA, shift=2)
                add_spot(buf, x + 60, y - 40, 10, (1, 1, 1), 1.5 * k)
                for a in (0, 1.57):
                    cv2.line(buf, (int((x + 60 - 30 * math.cos(a)) * 4), int((y - 40 - 30 * math.sin(a)) * 4)),
                             (int((x + 60 + 30 * math.cos(a)) * 4), int((y - 40 + 30 * math.sin(a)) * 4)),
                             (k, k, k), 3, cv2.LINE_AA, shift=2)
        ctx.dyn.append(glint)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.16, (0.5, 0.55), (0.53, 0.52)), name="candy_apple")


def xray_scene(dur):
    def build(ctx):
        alb = plaster(OH, OW, "#3a4448", seed=63) * 0.6
        ctx.bg = alb * 0.08
        cv = Canvas()
        x0, y0, x1, y1 = OW * 0.18, OH * 0.14, OW * 0.82, OH * 0.84
        lightbox(cv, x0, y0, x1 - x0, y1 - y0)
        ctx.flush()
        comp(ctx.bg, cv.rgba() * np.array([0.25, 0.25, 0.25, 1], np.float32))
        film = Canvas()
        film.rect(x0 + 40, y0 + 40, x1 - 40, y1 - 40, "#0a1622")
        r = np.random.default_rng(7)
        for i in range(16):
            cx_, cy_ = r.uniform(x0 + 140, x1 - 140), r.uniform(y0 + 120, y1 - 120)
            film.c.save()
            film.c.translate(cx_, cy_)
            film.c.rotate(r.uniform(-60, 60))
            kind = i % 3
            if kind == 0:
                film.rect(-70, -22, 70, 22, "#7a9ab0", 0.55, r=6)
            elif kind == 1:
                film.ellipse(0, 0, 40, 26, "#8aaabe", 0.5)
                film.poly([(-38, 0), (-62, -16), (-62, 16)], "#8aaabe", 0.4)
                film.poly([(38, 0), (62, -16), (62, 16)], "#8aaabe", 0.4)
            else:
                film.circle(0, 0, 28, "#9ab8cc", 0.5)
            film.c.restore()
        film.line([(OW * 0.58, OH * 0.40), (OW * 0.66, OH * 0.52)], "#f2fbff", 4)
        film.circle(OW * 0.58, OH * 0.40, 6, "#f2fbff")
        ctx.light_np("box", film.rgb() * 1.0 + cv2.GaussianBlur(film.rgb(), (0, 0), 30) * 0.6,
                     lambda t: 0.92 + 0.08 * (math.sin(t * 50) > 0.97))
    return Painted(build, dur=dur, cam=Camera(1.0, 1.12, (0.5, 0.5), (0.58, 0.45)), name="xray")


def texas_house(dur, light_off=None):
    def build(ctx):
        night(ctx, moon=(OW * 0.15, OH * 0.15, 36), seed=361, clouds=0.4)
        ctx.flush()
        cv = ctx.cv
        y = OH * 0.74
        body = poly_path([(OW * 0.18, y), (OW * 0.18, y - 260), (OW * 0.50, y - 420), (OW * 0.82, y - 260), (OW * 0.82, y)])
        rim_shape(cv, body, "#080a0c", "#3a4a50", (3, 3), rim_a=0.5)
        lit = const(1) if light_off is None else (lambda t: 1 - sstep(light_off, light_off + 0.08, t))
        lc = ctx.light("porch", lit)
        lc.glow(OW * 0.46, y - 210, 500, "#ffe2a8", 0.35)
        lc.circle(OW * 0.46, y - 210, 14, "#fff2d0", 1.0)
        lc.ellipse(OW * 0.46, y + 20, 520, 70, "#ffe2a8", 0.12, blur=30)
        win = ctx.light("win", flick(80, 0.03, 0.4))
        for wx in (OW * 0.25, OW * 0.66):
            cv.rect(wx, y - 190, wx + 160, y - 90, "#1a120a")
            win.rect(wx, y - 190, wx + 160, y - 90, "#8aa0ff", 0.25)
        cv.rect(OW * 0.40, y - 200, OW * 0.44, y, "#1a120a")
        ctx.flush()
        ground(ctx, y, "#0c1410", "#030504")
        tree(ctx.cv, OW * 0.90, OH * 0.82, 640, seed=93, spread=0.65)
        grass(ctx.cv, OH, 0, OW, "#020405", n=300, hmin=10, hmax=30, seed=36)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.5, 0.55), (0.48, 0.55)), fog=dict(FOG, density=0.15),
                   name="texas_house")


def door_shadow(dur, change_t=3.0):
    def build(ctx):
        alb = plaster(OH, OW, "#4a4038", seed=71) * 0.5
        ctx.bg = alb * 0.25
        cv = Canvas()
        dx0, dy0, dx1, dy1 = OW * 0.32, OH * 0.06, OW * 0.68, OH * 1.0
        cv.rect(dx0 - 30, dy0 - 30, dx1 + 30, dy1, "#1a120c")
        cv.rect(dx0, dy0, dx1, dy1, "#2a1c12")
        gx0, gy0, gx1, gy1 = dx0 + 70, dy0 + 70, dx1 - 70, OH * 0.62
        cv.rect(gx0, gy0, gx1, gy1, "#000000")
        ctx.flush()
        comp(ctx.bg, cv.rgba())
        glass = np.zeros((OH, OW, 3), np.float32)
        frost = cv2.resize(fbm(OH // 4, OW // 4, scale=8, octaves=3, seed=5), (OW, OH))
        glass[int(gy0):int(gy1), int(gx0):int(gx1)] = (rgb("#ffd8a0") * 0.55)[None, None, :] * \
            (0.8 + 0.4 * frost[int(gy0):int(gy1), int(gx0):int(gx1), None])
        ctx.light_np("glass", glass, const(1))
        # shadows cast on the glass: a monster, then a child with a bucket
        mon = Canvas()
        mx, my = OW * 0.5, OH * 0.66
        mon.c.drawPath(smooth_path([(mx - 260, my), (mx - 230, my - 260), (mx - 150, my - 420), (mx - 160, my - 560),
                                    (mx - 90, my - 470), (mx, my - 480), (mx + 90, my - 470), (mx + 160, my - 560),
                                    (mx + 150, my - 420), (mx + 230, my - 260), (mx + 260, my)], True), paint("#ffffff"))
        for side in (-1, 1):
            mon.line([(mx + side * 220, my - 300), (mx + side * 330, my - 380), (mx + side * 360, my - 330)], "#ffffff", 30)
            for k in range(3):
                mon.line([(mx + side * 360, my - 330), (mx + side * (400 + k * 10), my - 300 + k * 30)], "#ffffff", 9)
        kid = Canvas()
        figure(kid, mx, my + 10, 300, "#ffffff", child=True, hat="witch", dress=True, arms=((10, 5), (30, 40)))
        kid.circle(mx + 70, my - 110, 32, "#ffffff")
        gm = np.zeros((OH, OW), np.float32)
        gm[int(gy0):int(gy1), int(gx0):int(gx1)] = 1
        M = cv2.GaussianBlur(mon.rgba()[..., 3], (0, 0), 7) * gm
        K = cv2.GaussianBlur(kid.rgba()[..., 3], (0, 0), 5) * gm
        G = glass

        def shadow(buf, t):
            k = sstep(change_t, change_t + 1.4, t)
            S = M * (1 - k) + K * k
            y0, y1, x0, x1 = int(gy0), int(gy1), int(gx0), int(gx1)
            buf[y0:y1, x0:x1] -= G[y0:y1, x0:x1] * S[y0:y1, x0:x1, None] * 0.92
        ctx.dyn.append(shadow)
    return Painted(build, dur=dur, cam=Camera(1.0, 1.08, (0.5, 0.45), (0.5, 0.45)), name="door_shadow")
