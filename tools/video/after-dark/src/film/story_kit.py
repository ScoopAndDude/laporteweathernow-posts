"""The drawn scenes for La Porte After Dark shorts, picked by name from a storyboard (see reel_story.py).

Every scene is a class taking one dict of options and returning a float RGB frame (H x W x 3, 0..1) from
render(t, u): t is the reel's clock (fog, flicker and lights move with it), u the time since the scene started.

Options every scene understands:
    seed     int     a different arrangement of the same place
    move     str     camera: "in" (default), "out", "left", "right", "up", "still"
    amount   float   how far the camera moves (default 0.07 = 7% zoom; pans use it too)
    focus    [x, y]  the point the camera moves toward (pixels in the 1080 x 1920 frame)
    fog      float   fog density (0 = none; each scene has its own default)
    rain     bool    rain falling in front of everything
    snow     bool    snow
    orbs     int     small glowing orbs drifting near the ground ("the lights people report")
    ghost    str     a faint figure for a legend: "woman", "man", "child", "shadow" (legends only, never a real person)
    ghost_x  float   where it stands (default per scene)
    dur      float   set by the engine: how long the scene is on screen

Kinds (KINDS at the bottom): cemetery, plot, chapel, house, road, woods, room, cellar, jail, cell, prison, dunes,
lake, lighthouse, town, train, courthouse, card (a plain dark backdrop for a text card), map.
Nothing here shows a body, a hanging, a real person's likeness or a brand.
"""
import math

import cv2
import numpy as np
import skia

import reels_common as C
from reels_common import W, H
from core import fbm, add_spot, Canvas, poly_path, smooth_path, paint, light_map, Fog, Motes, smoothstep
import art
from reel_frank import zoom, Rain, Snow, flick
from reel_haunts import (cv, night_sky, land, comp, sprite, put, layer_from_pil, street_sign, road, chapel, car,
                         Bouncers, grade, TownCemetery, Shadows, GHOSTC, LANT)
from reel_haunts2 import night_lake_sky, pine, lantern
from reel_canton import (Riverview, FamilyPlot, ChastainHouse, ViewingRoom, double_porch_house, boxwood, mountains,
                         obelisk, lamb_stone)

WARM = "#ffb45c"
MOONLIT = (0.62, 0.78, 0.86)


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def frac(x):
    return x - np.floor(x)


def hash2(a, b, seed=0):
    return frac(np.sin(a * 12.9898 + b * 78.233 + seed * 37.719) * 43758.5453)


def masonry(h, w, bw=44, bh=16, seed=0, color=(0.2, 0.1, 0.07), mortar=(0.1, 0.09, 0.08), var=0.35, stone=False):
    """A brick (or cut-stone) wall texture, float RGB h x w."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    row = np.floor(yy / bh)
    off = (row % 2) * bw / 2
    col = np.floor((xx + off) / bw)
    bx = (xx + off) - col * bw
    by = yy - row * bh
    m = 2.2 if not stone else 3.0
    mort = ((bx < m) | (by < m)).astype(np.float32)
    rnd = hash2(col, row, seed)
    n = cv2.resize(fbm(max(8, h // 6), max(8, w // 6), scale=10, octaves=3, seed=seed + 5), (w, h),
                   interpolation=cv2.INTER_CUBIC)
    base = np.array(color, np.float32)[None, None, :] * (1 - var / 2 + var * rnd)[..., None] * (0.8 + 0.4 * n)[..., None]
    out = base * (1 - mort[..., None]) + np.array(mortar, np.float32)[None, None, :] * mort[..., None]
    return out.astype(np.float32)


def put_tex(img, tex, mask, x0, y0, k=1.0):
    """Lay a texture (h, w, 3) into img at (x0, y0) through a 0..1 mask of the same size."""
    h, w = mask.shape
    X0, Y0 = max(0, x0), max(0, y0)
    X1, Y1 = min(W, x0 + w), min(H, y0 + h)
    if X1 <= X0 or Y1 <= Y0:
        return
    m = mask[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None] * k
    img[Y0:Y1, X0:X1] = img[Y0:Y1, X0:X1] * (1 - m) + tex[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * m


def poly_mask(pts, w=W, h=H, blur=0.0):
    c = Canvas(w, h)
    c.poly(pts, "#ffffff")
    m = c.rgba()[..., 3]
    return cv2.GaussianBlur(m, (0, 0), blur) if blur else m


def beam_mask(x, y, ang, length, spread, w=W, h=H, blur=18):
    """A cone of light from (x, y) pointing at angle ang (radians, 0 = right), as a 0..1 mask fading out."""
    a0, a1 = ang - spread, ang + spread
    pts = [(x, y), (x + math.cos(a0) * length, y + math.sin(a0) * length),
           (x + math.cos(ang) * length * 1.04, y + math.sin(ang) * length * 1.04),
           (x + math.cos(a1) * length, y + math.sin(a1) * length)]
    c = Canvas(w, h)
    c.poly(pts, "#ffffff")
    m = c.rgba()[..., 3]
    m = cv2.GaussianBlur(m, (0, 0), blur)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - x) ** 2 + (yy - y) ** 2) / length
    return (m * np.clip(1.15 - d, 0, 1) ** 1.6).astype(np.float32)


GHOSTS = {
    "woman": dict(dress=True, arms=((8, 2), (-8, -2)), legs=(2, -2)),
    "man": dict(coat=True, hat="brim", arms=((6, 2), (-6, -2)), legs=(3, -3)),
    "child": dict(child=True, dress=True, arms=((8, 2), (-8, -2)), legs=(3, -3)),
    "shadow": dict(coat=True, arms=((5, 2), (-5, -2)), legs=(3, -3)),
}


# --------------------------------------------------------------------------------------------- the base

class Shot:
    """What every scene shares: options, extras (fog, rain, snow, orbs, a faint figure) and the camera."""
    focus = (540, 1000)
    fog_d = 0.2
    fog_color = "#86aaa4"
    fog_band = (0.5, 0.85)
    ghost_xy = (540, 1200)
    ghost_h = 330
    ground = (1100, 1300)          # where orbs drift (y range)

    def __init__(self, p=None):
        p = dict(p or {})
        self.p = p
        self.seed = int(p.get("seed", 0))
        self.dur = float(p.get("dur", 6.0))
        self.img = None
        self.lights = None
        fd = float(p.get("fog", self.fog_d))
        self.fog = Fog(seed=11 + self.seed * 7 + hash(type(self).__name__) % 97, scale=300, color=self.fog_color,
                       density=fd, top=self.fog_band[0], bottom=self.fog_band[1], speed=18, w=W, h=H) if fd > 0 else None
        self.rain = Rain(260, (0, 0, W, H), seed=5 + self.seed, speed=2100, length=52, slant=0.16) if p.get("rain") else None
        self.snow = Snow(240, seed=3 + self.seed) if p.get("snow") else None
        n = int(p.get("orbs", 0))
        self.orbs = Bouncers(n, 120, W - 120, self.ground[0], self.ground[1], seed=4 + self.seed) if n else None
        g = p.get("ghost")
        self.ghost = None
        if g:
            kw = GHOSTS.get(g, GHOSTS["woman"])
            hh = int(p.get("ghost_h", self.ghost_h))
            self.ghost = sprite(lambda k: art.figure(k, 110, hh + 10, hh, color="#ffffff", **kw), 220, hh + 20, blur=4.5)
            self.ghost_kind = g

    def extras(self, out, t, u):
        if self.orbs is not None:
            self.orbs.draw(out, t, k=min(1.0, u / 0.8))
        if self.ghost is not None:
            x = float(self.p.get("ghost_x", self.ghost_xy[0])) + 14 * math.sin(t * 0.5)
            y = float(self.p.get("ghost_y", self.ghost_xy[1]))
            a = (0.28 + 0.16 * math.sin(t * 1.3)) * min(1.0, u / 1.2)
            if self.ghost_kind == "shadow":
                put(out, self.ghost, x, y, (0.01, 0.015, 0.02), a * 2.0, mode="dark")
            else:
                put(out, self.ghost, x, y, MOONLIT, a)
        if self.fog is not None:
            self.fog.apply(out, t)
        if self.rain is not None:
            self.rain.draw(out, t, k=1.0)
        if self.snow is not None:
            self.snow.draw(out, t, k=1.0)
        return out

    def camera(self, out, u):
        move = self.p.get("move", "in")
        amt = float(self.p.get("amount", 0.07))
        fx, fy = self.p.get("focus", self.focus)
        k = ease(u / max(1.0, self.dur))
        if move == "in":
            return zoom(out, 1.0 + amt * k, fx, fy)
        if move == "out":
            return zoom(out, 1.0 + amt * (1 - k), fx, fy)
        if move in ("left", "right"):
            z = 1.0 + max(0.06, amt)
            sweep = (W * 0.5) * (z - 1) / z * 1.6
            d = -1 if move == "left" else 1
            return zoom(out, z, min(W, max(0, fx - d * sweep / 2 + d * sweep * k)), fy)
        if move == "up":
            z = 1.0 + max(0.06, amt)
            return zoom(out, z, fx, min(H, max(0, fy + 260 - 520 * k)))
        return out

    def base(self, t, u):
        out = self.img.copy()
        if self.lights is not None:
            out += self.lights * (0.82 + 0.18 * flick(t, 4 + self.seed))
        return out

    def render(self, t, u):
        out = self.base(t, u)
        self.animate(out, t, u)
        self.extras(out, t, u)
        return self.camera(out, u)

    def animate(self, out, t, u):
        pass


# --------------------------------------------------------------------------------------------- jail

def jail_front(c, lights, x, y, s=1.0, lit=(0, 1, 0, 0, 1, 0), plaque=None, brick=None):
    """An 1880s brick sheriff's residence with a mansard roof and dormers, and the jail block beside it with tall
    barred windows. (x, y) = bottom-left. Returns the door lamp and plaque positions."""
    hw, hh = 560 * s, 330 * s                     # the house
    jx, jw, jh = x + hw, 380 * s, 360 * s          # the jail block, to the right
    dark = "#140b08"
    # mansard roof with dormers
    roof = poly_path([(x - 14 * s, y - hh), (x + hw + 14 * s, y - hh), (x + hw - 26 * s, y - hh - 150 * s),
                      (x + 26 * s, y - hh - 150 * s)])
    art.rim_shape(c, roof, "#06090b", "#4a6662", (3, 3))
    for k in range(int(hw // (90 * s))):                                            # slate courses
        yy = y - hh - (k + 1) * 150 * s / 6
        c.line([(x + 26 * s * (k + 1) / 6, yy), (x + hw - 26 * s * (k + 1) / 6, yy)], "#0d1416", 1.4, 0.7)
    c.rect(x - 22 * s, y - hh - 160 * s, x + hw + 22 * s, y - hh - 146 * s, "#0b1012")  # roof cresting
    dormers = []
    for dxk in (0.22, 0.5, 0.78):
        dx = x + hw * dxk
        c.poly([(dx - 40 * s, y - hh - 24 * s), (dx - 40 * s, y - hh - 112 * s), (dx, y - hh - 150 * s),
                (dx + 40 * s, y - hh - 112 * s), (dx + 40 * s, y - hh - 24 * s)], "#090d0f")
        dormers.append((dx - 22 * s, y - hh - 104 * s, 44 * s, 70 * s))
    for cx_ in (x + 60 * s, x + hw - 60 * s):                                        # chimneys
        c.rect(cx_ - 22 * s, y - hh - 230 * s, cx_ + 22 * s, y - hh - 100 * s, "#120a08")
        c.rect(cx_ - 28 * s, y - hh - 238 * s, cx_ + 28 * s, y - hh - 224 * s, "#120a08")
    # jail block: flat roof, heavy cornice
    c.rect(jx - 6 * s, y - jh - 30 * s, jx + jw + 14 * s, y - jh, "#0b0d0e")
    c.line([(jx - 6 * s, y - jh - 30 * s), (jx + jw + 14 * s, y - jh - 30 * s)], "#4a6662", 2, 0.5)
    # window lists for the brick pass: (x, y, w, h, kind)
    wins = []
    for fl in range(2):
        wy = y - hh + 46 * s + fl * 165 * s
        for k, wx in enumerate((x + 70 * s, x + 190 * s, x + 370 * s, x + 470 * s)):
            if fl == 1 and k in (1, 2):
                continue
            wins.append((wx, wy, 58 * s, 104 * s, "house"))
    for k in range(4):
        wins.append((jx + 50 * s + k * 84 * s, y - jh + 70 * s, 34 * s, 200 * s, "jail"))
    door = (x + hw * 0.5 - 44 * s, y - 150 * s, 88 * s, 150 * s)
    return dict(house=(x, y - hh, x + hw, y), jail=(jx, y - jh, jx + jw + 8 * s, y), wins=wins, door=door,
                dormers=dormers, lamp=(x + hw * 0.5, y - 176 * s), plaque=(x + hw * 0.5, y - 200 * s), s=s)


class Jail(Shot):
    """A county jail and sheriff's house at night: brick, mansard roof, the jail block's barred windows, a lamp
    over the door, an iron fence and a streetlamp. sign: a plaque over the door (keep it to what's really there,
    e.g. "SHERIFF'S HOUSE" or leave it out). lit: which of the house's windows glow (list of 0/1)."""
    focus = (560, 1080)
    ghost_xy = (880, 1310)
    ground = (1240, 1310)

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = night_sky(401 + self.seed, moon=(880, 360, 52), clouds=0.4)
        by = 1320                                                                            # the buildings' base
        land(img, by - 60, 410 + self.seed, far="#0a1418")
        c = cv()
        lights = cv()
        art.tree(c, 40, by, 980, seed=421 + self.seed, depth=8, spread=0.7, lean=0.1)
        art.tree(c, 1070, by - 10, 820, seed=422 + self.seed, depth=8, spread=0.6, lean=-0.12)
        J = jail_front(c, lights, 34, by, s=1.1, plaque=p.get("sign"))
        comp(img, c.rgba())
        # brick walls
        x0, y0, x1, y1 = [int(v) for v in J["house"]]
        tex = masonry(y1 - y0, x1 - x0, bw=34, bh=13, seed=431 + self.seed, color=(0.085, 0.045, 0.032),
                      mortar=(0.034, 0.03, 0.027))
        m = np.ones((y1 - y0, x1 - x0), np.float32)
        put_tex(img, tex, m, x0, y0)
        jx0, jy0, jx1, jy1 = [int(v) for v in J["jail"]]
        tex2 = masonry(jy1 - jy0, jx1 - jx0, bw=38, bh=14, seed=432 + self.seed, color=(0.075, 0.042, 0.03),
                       mortar=(0.03, 0.027, 0.024))
        put_tex(img, tex2, np.ones((jy1 - jy0, jx1 - jx0), np.float32), jx0, jy0)
        img[y0:y0 + 3, x0:x1] += 0.05                                                       # moonlit cornice
        img[jy0:jy0 + 3, jx0:jx1] += 0.05
        d = cv()
        lit = list(p.get("lit", (0, 1, 0, 0, 1, 0)))
        hi = 0
        for (wx, wy, ww, wh, kind) in J["wins"]:
            if kind == "house":
                on = lit[hi] if hi < len(lit) else 0
                hi += 1
                d.rect(wx - 8, wy - 14, wx + ww + 8, wy - 4, "#2a2622")                     # stone lintel
                d.rect(wx - 4, wy + wh, wx + ww + 4, wy + wh + 8, "#2a2622")                # sill
                if on:
                    d.rect(wx, wy, wx + ww, wy + wh, "#3a210c")
                    lights.rect(wx, wy, wx + ww, wy + wh, WARM, 0.85)
                    lights.glow(wx + ww / 2, wy + wh / 2, 130, WARM, 0.28)
                    for k in (1, 2):
                        lights.rect(wx, wy + wh * k / 3 - 2, wx + ww, wy + wh * k / 3 + 2, "#000000", 1.0)
                    lights.rect(wx + ww / 2 - 2, wy, wx + ww / 2 + 2, wy + wh, "#000000", 1.0)
                else:
                    d.rect(wx, wy, wx + ww, wy + wh, "#0a0f11")
                    d.line([(wx + ww / 2, wy), (wx + ww / 2, wy + wh)], "#1d1a17", 3)
            else:
                d.rect(wx - 8, wy - 16, wx + ww + 8, wy - 4, "#2a2622")
                d.rect(wx, wy, wx + ww, wy + wh, "#05080a")
                for k in range(4):                                                          # the bars
                    bx = wx + ww * (k + 0.5) / 4
                    d.line([(bx, wy), (bx, wy + wh)], "#2b3436", 3.2)
                for k in (0.33, 0.66):
                    d.line([(wx, wy + wh * k), (wx + ww, wy + wh * k)], "#2b3436", 3.0)
        for (wx, wy, ww, wh) in J["dormers"]:
            d.rect(wx, wy, wx + ww, wy + wh, "#0a0f11")
        dx, dy, dw, dh = J["door"]
        d.rect(dx - 14, dy - 26, dx + dw + 14, dy + dh, "#2a2622")
        d.rect(dx, dy, dx + dw, dy + dh, "#140c07")
        d.line([(dx + dw / 2, dy), (dx + dw / 2, dy + dh)], "#060403", 3)
        for k in range(4):                                                                  # front steps
            d.rect(dx - 30 - k * 12, dy + dh + k * 12, dx + dw + 30 + k * 12, dy + dh + 12 + k * 12, "#1a1816")
        # the lawn, an iron fence, the sidewalk, the curb and a wet street
        d.poly([(-20, by + 2), (W + 20, by - 4), (W + 20, H), (-20, H)], "#06090a")
        d.poly([(-20, by + 96), (W + 20, by + 92), (W + 20, by + 170), (-20, by + 176)], "#141819")   # sidewalk
        for k in range(0, W + 60, 64):
            d.line([(k, by + 94), (k - 12, by + 174)], "#0b0e0f", 2)
        d.poly([(-20, by + 174), (W + 20, by + 168), (W + 20, by + 184), (-20, by + 190)], "#22282a")  # curb
        d.poly([(-20, by + 190), (W + 20, by + 184), (W + 20, H), (-20, H)], "#0a0e10")             # street
        for k in range(-1, 46):
            xk = k * 24
            d.line([(xk, by + 92), (xk, by - 2)], "#030405", 4)
            d.poly([(xk - 6, by), (xk, by - 18), (xk + 6, by)], "#030405")
        d.line([(-10, by + 12), (W + 10, by + 12)], "#030405", 5)
        d.line([(-10, by + 80), (W + 10, by + 80)], "#030405", 5)
        d.rect(40, by - 420, 52, by + 120, "#030405")                                         # a streetlamp
        d.rect(26, by - 440, 66, by - 414, "#030405")
        comp(img, d.rgba())
        d = cv()
        comp(img, d.rgba())
        lx, ly = J["lamp"]
        lights.glow(lx, ly, 160, WARM, 0.35)
        lights.glow(46, by - 426, 220, WARM, 0.3)
        if p.get("sign"):
            comp(img, layer_from_pil(plaque(p["sign"]), int(lx - 210), int(J["plaque"][1] - 46)))
        self.door_light = light_map(H, W, lx, ly + 90, 440, power=1.4)
        self.street_light = light_map(H, W, 46, by - 360, 560, power=1.3)
        self.lamp = (lx, ly)
        self.street_lamp = (46, by - 426)
        refl = np.zeros((H, W, 3), np.float32)                                              # lamps on the wet street
        for (rx, ry) in ((lx, by + 300), (46, by + 330)):
            add_spot(refl, rx, ry, 26, (1.0, 0.75, 0.45), 0.6)
        self.refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=5, sigmaY=50)
        self.img = img
        self.lights = lights.rgba()[..., :3]

    def animate(self, out, t, u):
        fl = flick(t, 3)
        out *= (1.0 + 1.4 * self.door_light[..., None] * fl + 0.9 * self.street_light[..., None])
        add_spot(out, self.lamp[0], self.lamp[1], 12, (1.0, 0.85, 0.6), 1.2)
        add_spot(out, self.street_lamp[0], self.street_lamp[1], 12, (1.0, 0.85, 0.6), 1.2)
        out += self.refl * fl


def plaque(text, w=420, h=70):
    """A cut-stone name plaque, lit from below by the door lamp."""
    S = 3
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w * S - 1, h * S - 1), fill=(58, 52, 44, 255))
    d.rectangle((5 * S, 5 * S, w * S - 6 * S, h * S - 6 * S), outline=(30, 26, 22, 255), width=3 * S)
    f = C.font("oldst_b", 40 * S)
    while f.getlength(text) > (w - 40) * S and f.size > 20 * S:
        f = C.font("oldst_b", f.size / S - 2)
        f = C.font("oldst_b", int(f.size))
    tw = f.getlength(text)
    d.text(((w * S - tw) / 2, (h * S - f.size * 1.18) / 2), text, font=f, fill=(196, 178, 150, 255))
    im = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    a[..., :3] *= np.linspace(0.45, 0.85, h, dtype=np.float32)[:, None, None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


class Cell(Shot):
    """Inside an old jail cell, looking in through the bars: a cot, a high barred window and a shaft of moonlight
    with dust in it. door_open=True swings the cell door out."""
    focus = (560, 980)
    fog_d = 0.06
    fog_color = "#6a7a80"
    fog_band = (0.0, 0.9)
    ghost_xy = (600, 1200)
    ghost_h = 420
    ground = (1050, 1200)

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = np.zeros((H, W, 3), np.float32)
        wall = masonry(1180, W, bw=64, bh=24, seed=451 + self.seed, color=(0.07, 0.068, 0.064),
                       mortar=(0.035, 0.034, 0.032), var=0.25, stone=True)
        img[:1180] = wall
        yy = np.arange(H, dtype=np.float32)[:, None]
        floor = cv2.resize(fbm(H // 4, W // 4, scale=16, octaves=5, seed=452 + self.seed), (W, H),
                           interpolation=cv2.INTER_CUBIC)
        img[1180:] = ((0.035 + 0.025 * floor[1180:]) * np.ones((1, 1), np.float32))[..., None] * \
            np.array([0.9, 0.92, 0.95], np.float32)
        c = cv()
        c.rect(0, 1172, W, 1188, "#050505", 0.9, blur=3)
        self.win = (230, 470, 430, 650)
        x0, y0, x1, y1 = self.win
        c.rect(x0 - 14, y0 - 14, x1 + 14, y1 + 14, "#141414")
        c.rect(x0, y0, x1, y1, "#0b1418")
        for k in range(1, 5):
            c.line([(x0 + (x1 - x0) * k / 5, y0), (x0 + (x1 - x0) * k / 5, y1)], "#020202", 6)
        c.line([(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)], "#020202", 5)
        # the cot: iron frame, thin mattress, a folded blanket
        c.rect(560, 1080, 1040, 1104, "#2a2e30")
        c.rect(560, 1060, 1040, 1082, "#3e3a34")
        c.rect(570, 1104, 584, 1250, "#1c2022")
        c.rect(1016, 1104, 1030, 1250, "#1c2022")
        c.rect(860, 1040, 1000, 1062, "#4a3a30")
        c.rect(180, 1200, 240, 1260, "#2a2c2e")                                           # a bucket
        c.ellipse(210, 1200, 30, 8, "#111314")
        comp(img, c.rgba())
        self.img = img
        # moonlight: the shaft from the window to the floor, and the window's barred patch on the floor
        self.shaft = cv2.GaussianBlur(poly_mask([(x0, y0), (x1, y0), (x1 + 520, 1500), (x0 + 340, 1560)]), (0, 0), 24)
        self.shaft *= np.clip((yy - y0) / 300.0, 0.3, 1.0)
        patch = poly_mask([(x0 + 300, 1360), (x1 + 470, 1330), (x1 + 560, 1520), (x0 + 360, 1560)], blur=6)
        bars = np.ones((H, W), np.float32)
        for k in range(1, 5):
            px = (x0 + 300) + (x1 + 470 - x0 - 300) * k / 5
            cv2.line(bars, (int(px), 1330), (int(px + 70), 1560), 0.0, 14, cv2.LINE_AA)
        self.patch = patch * cv2.GaussianBlur(bars, (0, 0), 3)
        self.motes = Motes(120, x0, x1 + 480, y0, 1500, seed=453 + self.seed, color=(0.8, 0.9, 1.0), size=(0.8, 1.8))
        self.room_light = light_map(H, W, 760, 1150, 700, power=1.2) * 1.1
        # the bars in front of us
        self.door_open = bool(p.get("door_open"))
        b = Canvas(W, H)
        spacing = 92
        for k in range(-1, 13):
            bx = 30 + k * spacing
            if self.door_open and 300 < bx < 780:
                continue
            b.rect(bx - 9, 0, bx + 9, H, "#0c0d0e")
            b.line([(bx - 5, 0), (bx - 5, H)], "#5b6a6e", 2.0, 0.5)
        for yb in (330, 1640):
            b.rect(-10, yb, W + 10, yb + 30, "#0e1011")
            b.line([(-10, yb + 2), (W + 10, yb + 2)], "#5b6a6e", 2, 0.4)
        if self.door_open:                                                                  # the open door, swung out
            for k in range(6):
                bx = 330 + k * 34
                b.line([(bx, 260 - k * 26), (bx, 1720 + k * 26)], "#0c0d0e", 18)
                b.line([(bx - 5, 260 - k * 26), (bx - 5, 1720 + k * 26)], "#5b6a6e", 2.0, 0.4)
            b.line([(320, 380), (520, 230)], "#0e1011", 26)
            b.line([(320, 1600), (520, 1760)], "#0e1011", 26)
        self.bars = b.rgba()

    def animate(self, out, t, u):
        cool = np.array([0.55, 0.68, 0.8], np.float32)
        out += self.shaft[..., None] * cool * 0.2
        out += self.patch[..., None] * cool * 0.22
        out *= (1.0 + 0.9 * self.room_light[..., None])
        self.motes.draw(out, t, k=1.0, mask=self.shaft)
        comp(out, self.bars)


# --------------------------------------------------------------------------------------------- prison

class Prison(Shot):
    """A state prison at night: a long stone wall, a guard tower whose searchlight sweeps the fog, cell houses
    with rows of small windows behind the wall. Told as history: no prisoners or guards are shown."""
    focus = (600, 1060)
    fog_d = 0.22
    ground = (1420, 1500)
    ghost_xy = (300, 1450)

    def __init__(self, p=None):
        super().__init__(p)
        img = night_sky(501 + self.seed, moon=(250, 340, 44), clouds=0.5)
        land(img, 1120, 510 + self.seed, far="#0a1418")
        c = cv()
        lights = cv()
        # the cell houses behind the wall
        for (bx0, bx1, top) in ((40, 520, 900), (560, 1000, 930)):
            c.rect(bx0, top, bx1, 1160, "#0b0f11")
            c.poly([(bx0 - 10, top), (bx0 + 30, top - 70), (bx1 - 30, top - 70), (bx1 + 10, top)], "#080b0c")
            for r in range(3):
                for k in range(int((bx1 - bx0 - 40) / 34)):
                    wx = bx0 + 24 + k * 34
                    wy = top + 30 + r * 60
                    c.rect(wx, wy, wx + 12, wy + 30, "#040607")
                    if hash2(k, r, self.seed + bx0) > 0.8:
                        lights.rect(wx, wy, wx + 12, wy + 30, "#ffcf8a", 0.6)
        c.rect(940, 640, 980, 980, "#090c0d")                                              # the smokestack
        c.rect(930, 628, 990, 646, "#090c0d")
        comp(img, c.rgba())
        # the wall: big cut-stone blocks
        wall_top, wall_bot = 1080, 1400
        tex = masonry(wall_bot - wall_top, W, bw=120, bh=52, seed=511 + self.seed, color=(0.075, 0.08, 0.08),
                      mortar=(0.03, 0.033, 0.034), var=0.3, stone=True)
        yy = np.arange(wall_bot - wall_top, dtype=np.float32)[:, None, None]
        tex *= (0.7 + 0.5 * (yy / (wall_bot - wall_top)))
        put_tex(img, tex, np.ones((wall_bot - wall_top, W), np.float32), 0, wall_top)
        img[wall_top:wall_top + 20] = np.array([0.09, 0.1, 0.1], np.float32)                 # coping
        img[wall_top:wall_top + 3] += 0.06
        d = cv()
        # the guard tower: a stone shaft through the wall, a glassed cab and a hipped roof
        tx = 800
        d.rect(tx - 76, 700, tx + 76, 1410, "#0a0d0e")
        d.line([(tx - 76, 700), (tx - 76, 1410)], "#46605e", 2.5, 0.5)
        d.rect(tx - 108, 610, tx + 108, 710, "#0b0e0f")
        for k in range(4):
            d.rect(tx - 96 + k * 50, 626, tx - 62 + k * 50, 694, "#16202a")
        d.poly([(tx - 130, 612), (tx, 510), (tx + 130, 612)], "#07090a")
        d.rect(tx - 120, 706, tx + 120, 720, "#0b0e0f")                                     # catwalk
        for k in range(9):
            d.line([(tx - 116 + k * 29, 706), (tx - 116 + k * 29, 752)], "#0b0e0f", 3)
        self.light_pt = (tx + 104, 664)
        # a far tower on the left
        d.rect(150, 960, 210, 1100, "#090c0d")
        d.rect(136, 926, 224, 966, "#0a0d0e")
        d.poly([(128, 928), (180, 886), (232, 928)], "#07090a")
        lights.rect(150, 936, 210, 958, "#ffcf8a", 0.4)
        # the road along the wall
        d.poly([(-20, 1400), (W + 20, 1400), (W + 20, H), (-20, H)], "#07090a")
        d.poly([(-20, 1440), (W + 20, 1430), (W + 20, 1540), (-20, 1560)], "#0c1113")
        for k in range(14):                                                                 # an outer fence
            d.line([(k * 84, 1600), (k * 84, 1470)], "#030405", 5)
        d.line([(-10, 1490), (W + 10, 1490)], "#030405", 2.5)
        d.line([(-10, 1530), (W + 10, 1530)], "#030405", 2.5)
        d.line([(-10, 1570), (W + 10, 1570)], "#030405", 2.5)
        art.grass(d, 1640, 0, W, "#030506", n=420, hmin=12, hmax=50, seed=19 + self.seed)
        comp(img, d.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]
        self.beams = {}

    def beam(self, ang):
        key = round(ang, 2)
        if key not in self.beams:
            x, y = self.light_pt
            self.beams[key] = beam_mask(x, y, ang, 1300, 0.075)
            if len(self.beams) > 80:
                self.beams.pop(next(iter(self.beams)))
        return self.beams[key]

    def animate(self, out, t, u):
        ang = math.pi * (0.62 + 0.2 * math.sin(t * 0.55 + self.seed))
        m = self.beam(ang)
        fogl = self.fog.layer(t, 1.0) if self.fog is not None else 0.5
        out += m[..., None] * (0.26 + 0.8 * fogl[..., None]) * np.array([0.85, 0.9, 0.95], np.float32)
        add_spot(out, self.light_pt[0], self.light_pt[1], 34, (1.0, 0.96, 0.85), 0.8)
        add_spot(out, self.light_pt[0], self.light_pt[1], 8, (1.0, 1.0, 1.0), 1.6)


# --------------------------------------------------------------------------------------------- dunes, lake, lighthouse

def lake_water(img, hz, y1, x_from, moon_x, seed, k_glint=0.9, right=True):
    """Fill [hz, y1) with dark rippling water on one side of x_from (right=True: x > x_from), moon path at moon_x."""
    yy = np.arange(H, dtype=np.float32)[:, None]
    xx = np.arange(W, dtype=np.float32)[None, :]
    band = ((yy >= hz) & (yy < y1)).astype(np.float32)
    side = np.clip((xx - x_from) / 30.0, 0, 1) if right else np.clip((x_from - xx) / 30.0, 0, 1)
    m = band * side
    ripple = cv2.resize(fbm(H // 8, W // 2, scale=5, octaves=3, seed=seed), (W, H), interpolation=cv2.INTER_CUBIC)
    water = np.array([0.02, 0.04, 0.05], np.float32) * (0.7 + 0.6 * ripple[..., None])
    glint = np.exp(-((xx - moon_x) / (26 + (yy - hz) * 0.3)) ** 2) * (yy > hz) * (0.2 + 0.8 * ripple ** 2)
    water = water + (glint * k_glint)[..., None] * np.array([0.72, 0.86, 0.84], np.float32)
    img[:] = img * (1 - m[..., None]) + water * m[..., None]
    return m


class Waves:
    """Foam lines rolling up a beach: a few bright, soft streaks that move toward the viewer and fade."""

    def __init__(self, y0, y1, x0=0, x1=W, n=5, seed=0):
        self.y0, self.y1, self.x0, self.x1, self.n = y0, y1, x0, x1, n
        self.noise = cv2.resize(fbm(64, 256, scale=12, octaves=3, seed=seed), (W, 64), interpolation=cv2.INTER_CUBIC)
        self.lay = np.zeros((H, W), np.float32)

    def draw(self, out, t, k=1.0):
        lay = self.lay
        lay[:] = 0
        for i in range(self.n):
            ph = (t * 0.12 + i / self.n) % 1.0
            y = self.y0 + (self.y1 - self.y0) * ph ** 1.4
            a = math.sin(math.pi * ph) * 0.9
            row = self.noise[(i * 11) % 64]
            ys = (y + 14 * row).astype(np.int32)
            for x in range(self.x0, self.x1, 3):
                yv = int(ys[min(W - 1, x)])
                if 0 <= yv < H - 3:
                    lay[yv:yv + 3, x:x + 3] = max(lay[yv, x], a * (0.4 + 0.6 * row[min(W - 1, x)]))
        lay = cv2.GaussianBlur(lay, (0, 0), 2.2)
        out += lay[..., None] * np.array([0.5, 0.6, 0.62], np.float32) * k


def sand_tex(h, w, seed, base=(0.27, 0.29, 0.31)):
    """Moonlit sand: soft wind ripples (low contrast) over gentle noise."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    n = cv2.resize(fbm(max(8, h // 6), max(8, w // 6), scale=30, octaves=4, seed=seed), (w, h),
                   interpolation=cv2.INTER_CUBIC)
    warp = cv2.resize(fbm(max(8, h // 10), max(8, w // 10), scale=12, octaves=3, seed=seed + 1), (w, h),
                      interpolation=cv2.INTER_CUBIC)
    rip = np.sin((xx * 0.28 + yy * 0.95) / 5.5 + warp * 9.0)
    k = 0.92 + 0.08 * n + 0.025 * rip
    return (np.array(base, np.float32)[None, None, :] * k[..., None]).astype(np.float32)


def grass_tuft(c, x, y, s, rr, color="#0b140f"):
    """A clump of marram grass: long curved blades leaning with the wind."""
    for j in range(int(7 + 6 * s)):
        a = rr.uniform(-0.75, 0.55)
        L = rr.uniform(30, 78) * s
        bend = rr.uniform(0.15, 0.5)
        x1, y1 = x + math.sin(a) * L * 0.5, y - math.cos(a) * L * 0.55
        x2, y2 = x + math.sin(a + bend) * L, y - math.cos(a + bend) * L * 0.92
        c.c.drawPath(smooth_path([(x, y), (x1, y1), (x2, y2)], False), paint(color, 0.95, stroke=max(1.2, 2.4 * s)))


class Dunes(Shot):
    """A tall dune by Lake Michigan at night: a curving moonlit slope with beach grass on the left, the lake with the
    moon's path on it, foam running up the beach. trees=True adds dead trunks sticking out of the sand (the "tree
    graveyards" the dunes uncover); steps=True a line of footprints up the slope."""
    focus = (460, 1000)
    fog_d = 0.12
    fog_band = (0.55, 0.95)
    ghost_xy = (860, 1290)
    ghost_h = 250
    ground = (1150, 1290)

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        mx = 760
        img = night_lake_sky(521 + self.seed, moon=(mx, 400, 66), clouds=0.26, glow_k=0.85)
        hz, shore = 1000, 1262
        lake_water(img, hz, shore + 10, -40, mx, 522 + self.seed)
        # far shore: a low dark line of dunes across the lake
        art.hills(img, hz + 2, 10, 300, "#0a1316", 523 + self.seed, rim="#3e5c5a", rim_w=2, rim_a=0.25)
        img[hz + 2:hz + 6] *= 0.9
        lake_water(img, hz + 8, shore + 10, -40, mx, 522 + self.seed)
        xx = np.arange(W, dtype=np.float32)
        u = np.clip(xx / 780.0, 0, 1)
        prof = 600 + (shore - 600) * (u ** 1.7) + 26 * np.sin(xx / 95.0 + self.seed) * (1 - u) * u * 2.2
        prof = np.where(xx > 780, shore + 4, prof)
        yy = np.arange(H, dtype=np.float32)[:, None]
        cov = np.clip(yy - prof[None, :] + 0.5, 0, 1)
        cov = cv2.GaussianBlur(cov, (0, 0), 1.2)
        tex = sand_tex(H, W, 524 + self.seed, base=(0.22, 0.235, 0.25))
        depth = np.clip((yy - prof[None, :]) / 520.0, 0, 1)
        lit = (0.62 + 0.38 * (1 - depth)) * (0.75 + 0.25 * u[None, :])
        sand = tex * lit[..., None]
        img[:] = img * (1 - cov[..., None]) + sand * cov[..., None]
        rimm = np.exp(-np.maximum(yy - prof[None, :], 0) / 5.0) * (yy > prof[None, :] - 1) * (xx[None, :] < 790)
        img += (rimm * 0.16)[..., None] * np.array([0.8, 0.92, 0.92], np.float32)
        # the beach: a wet band at the water's edge, drier sand toward us
        beach = np.clip((yy - shore) / 3.0, 0, 1) * np.ones((1, W), np.float32)
        wet = np.exp(-np.maximum(yy - shore, 0) / 40.0)
        btex = sand_tex(H, W, 525 + self.seed, base=(0.105, 0.11, 0.115)) * (0.7 + 0.3 * (1 - wet))[..., None]
        btex *= np.clip(1.0 - (yy - shore) / 1400.0, 0.55, 1.0)[..., None]
        img[:] = img * (1 - beach[..., None]) + btex * beach[..., None]
        glint = np.exp(-((xx[None, :] - mx) / 60.0) ** 2) * wet * (yy > shore)
        img += (glint * 0.22)[..., None] * np.array([0.7, 0.85, 0.85], np.float32)
        c = cv()
        rr = np.random.default_rng(530 + self.seed)
        for k in range(46):                                                                # grass on the slope
            gx = rr.uniform(-20, 720)
            py = float(np.interp(gx, xx, prof))
            gy = py + rr.uniform(4, 260) ** 1.1
            grass_tuft(c, gx, gy, rr.uniform(0.6, 1.25), rr)
        for k in range(10):                                                                # and along the crest
            gx = rr.uniform(-20, 500)
            grass_tuft(c, gx, float(np.interp(gx, xx, prof)) + 6, rr.uniform(0.9, 1.4), rr)
        if p.get("trees"):
            for k, (tx, th) in enumerate(((180, 230), (360, 180), (90, 160))):
                ty = float(np.interp(tx, xx, prof)) + 90 + k * 40
                art.tree(c, tx, ty, th, seed=540 + k, depth=5, spread=0.75, color="#120e0b", lean=0.12, gnarl=0.5)
        if p.get("steps"):
            for k in range(16):
                sx = 640 - k * 30 + (k % 2) * 12
                sy = float(np.interp(sx, xx, prof)) + 26 + k * 2
                c.ellipse(sx, sy, 8, 4, "#15181a", 0.85)
        for k in range(26):                                                                # driftwood and grass on the beach
            gx = rr.uniform(0, W)
            gy = rr.uniform(1420, 1880)
            if rr.random() < 0.25:
                c.line([(gx, gy), (gx + rr.uniform(40, 120), gy - rr.uniform(-6, 6))], "#0d0d0c", rr.uniform(4, 9))
            else:
                grass_tuft(c, gx, gy, rr.uniform(0.4, 0.8), rr, color="#0a110d")
        comp(img, c.rgba())
        self.img = img
        self.waves = Waves(shore - 70, shore + 6, 0, W, n=5, seed=531 + self.seed)

    def animate(self, out, t, u):
        self.waves.draw(out, t, k=0.9)


class Lake(Shot):
    """Lake Michigan at night from the beach: waves rolling in, the moon's path, a pier on the left.
    city=True adds the glow of a city on the far horizon (Chicago, from the Indiana shore)."""
    focus = (540, 1060)
    fog_d = 0.14
    ghost_xy = (560, 1320)
    ghost_h = 260
    ground = (1200, 1320)

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        mx = 640
        img = night_lake_sky(551 + self.seed, moon=(mx, 430, 64), clouds=0.32, glow_k=0.8)
        hz = 1020
        if p.get("city"):
            xx = np.arange(W, dtype=np.float32)[None, :]
            yy = np.arange(H, dtype=np.float32)[:, None]
            glow_ = np.exp(-((yy - hz) / 60.0) ** 2) * np.exp(-((xx - 240) / 260.0) ** 2) * (yy < hz)
            img += glow_[..., None] * np.array([0.25, 0.18, 0.1], np.float32)
            r = np.random.default_rng(5)
            for k in range(70):
                add_spot(img, r.uniform(80, 420), hz - r.uniform(1, 9), 1.0, (1.0, 0.85, 0.6), r.uniform(0.3, 0.9))
        shore = 1330
        lake_water(img, hz, shore + 10, -40, mx, 552 + self.seed)
        yy = np.arange(H, dtype=np.float32)[:, None]
        xx = np.arange(W, dtype=np.float32)[None, :]
        beach = np.clip((yy - shore) / 3.0, 0, 1) * np.ones((1, W), np.float32)
        wet = np.exp(-np.maximum(yy - shore, 0) / 50.0)
        btex = sand_tex(H, W, 554 + self.seed, base=(0.1, 0.105, 0.11)) * (0.7 + 0.3 * (1 - wet))[..., None]
        btex *= np.clip(1.0 - (yy - shore) / 1400.0, 0.55, 1.0)[..., None]
        img[:] = img * (1 - beach[..., None]) + btex * beach[..., None]
        img += (np.exp(-((xx - mx) / 70.0) ** 2) * wet * (yy > shore) * 0.2)[..., None] * \
            np.array([0.7, 0.85, 0.85], np.float32)
        c = cv()
        if p.get("pier", True):                                                           # a breakwater pier, left
            c.poly([(-20, 1250), (420, 1062), (436, 1068), (-20, 1290)], "#11171a")
            c.line([(-20, 1250), (420, 1062)], "#4e6a68", 2.5, 0.6)
            for k in range(12):
                px = 410 - k * 38
                py = 1066 + k * 16
                c.rect(px - 3, py, px + 3, py + 40 + k * 4, "#070a0b")
            c.rect(424, 990, 436, 1064, "#0d1214")                                            # a light at the end
            c.rect(418, 980, 442, 996, "#0d1214")
            self.pier_light = (430, 986)
        else:
            self.pier_light = None
        rr = np.random.default_rng(556 + self.seed)
        for k in range(18):
            grass_tuft(c, rr.uniform(0, W), rr.uniform(1560, 1900), rr.uniform(0.4, 0.9), rr, color="#0a110d")
        comp(img, c.rgba())
        self.img = img
        self.waves = Waves(1220, shore + 6, 0, W, n=6, seed=553 + self.seed)

    def animate(self, out, t, u):
        self.waves.draw(out, t)
        if self.pier_light is not None:
            on = 0.6 + 0.4 * (math.sin(t * 2.4) > 0)
            add_spot(out, *self.pier_light, 26, (1.0, 0.45, 0.35), 0.35 * on)
            add_spot(out, *self.pier_light, 5, (1.0, 0.7, 0.6), 1.2 * on)


class Lighthouse(Shot):
    """A pierhead lighthouse at night: a tapered tower on a breakwater with an elevated catwalk running back to
    shore, its light turning; waves breaking on the pier. style="house" draws an old brick keeper's house with the
    lantern on its roof instead."""
    focus = (640, 900)
    fog_d = 0.2

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        self.style = p.get("style", "pier")
        img = night_lake_sky(571 + self.seed, moon=(200, 380, 50), clouds=0.4, glow_k=0.7)
        hz = 1060
        lake_water(img, hz, H, -40, 200, 572 + self.seed, k_glint=0.6)
        c = cv()
        lights = cv()
        if self.style == "pier":
            c.poly([(-20, 1380), (640, 1090), (720, 1094), (720, 1120), (-20, 1460)], "#0c1012")   # breakwater
            for k in range(16):                                                                 # catwalk
                px = 20 + k * 40
                py = 1300 - k * 13
                c.line([(px, py), (px, py - 70)], "#070909", 4)
            c.line([(0, 1240), (640, 1010)], "#070909", 6)
            c.line([(0, 1262), (640, 1032)], "#070909", 4)
            tx, base, top = 680, 1096, 640
            c.poly([(tx - 60, base), (tx - 38, top), (tx + 38, top), (tx + 60, base)], "#c8ccca")
            c.poly([(tx + 6, base), (tx + 2, top), (tx + 38, top), (tx + 60, base)], "#8f9694")
            c.rect(tx - 66, base - 40, tx + 66, base, "#a8aeac")
            c.rect(tx - 56, top - 14, tx + 56, top, "#2a2e2e")                                    # gallery
            for k in range(8):
                c.line([(tx - 52 + k * 15, top - 14), (tx - 52 + k * 15, top - 40)], "#1a1c1c", 2)
            c.rect(tx - 30, top - 86, tx + 30, top - 14, "#1a1e1e")                               # lantern room
            c.poly([(tx - 36, top - 86), (tx, top - 120), (tx + 36, top - 86)], "#101212")
            lights.rect(tx - 24, top - 80, tx + 24, top - 20, "#fff2c8", 0.9)
            self.lamp = (tx, top - 52)
            for k in range(3):
                c.rect(tx - 10, base - 120 - k * 120, tx + 10, base - 92 - k * 120, "#1a1e1e")
        else:
            land(img, 1150, 573 + self.seed, far="#0a1418")
            hx, hy = 300, 1190
            c.rect(hx, hy - 220, hx + 420, hy, "#0d0807")
            c.poly([(hx - 20, hy - 220), (hx + 210, hy - 330), (hx + 440, hy - 220)], "#080605")
            c.rect(hx + 180, hy - 420, hx + 240, hy - 300, "#141414")
            c.rect(hx + 170, hy - 430, hx + 250, hy - 416, "#0e0e0e")
            c.poly([(hx + 176, hy - 430), (hx + 210, hy - 470), (hx + 244, hy - 430)], "#0a0a0a")
            lights.rect(hx + 186, hy - 412, hx + 234, hy - 306, "#fff2c8", 0.85)
            for wx in (hx + 50, hx + 150, hx + 270, hx + 350):
                c.rect(wx, hy - 170, wx + 40, hy - 90, "#0b1012")
            c.poly([(-20, hy), (W + 20, hy - 10), (W + 20, H), (-20, H)], "#050809")
            self.lamp = (hx + 210, hy - 360)
        comp(img, c.rgba())
        if self.style == "house":
            put_tex(img, masonry(220, 420, seed=574, color=(0.11, 0.06, 0.045), mortar=(0.045, 0.04, 0.035)),
                    np.ones((220, 420), np.float32), 300, 970)
        self.img = img
        self.lights = lights.rgba()[..., :3]
        self.waves = Waves(1150, 1500, 0, W, n=6, seed=575 + self.seed)
        self.beams = {}

    def animate(self, out, t, u):
        x, y = self.lamp
        ang = (t * 0.9) % (2 * math.pi)
        for a in (ang, ang + math.pi):
            vis = abs(math.cos(a))                             # a beam pointing at us (sideways) shows longest
            key = round(math.atan2(0.18 * math.sin(a), math.cos(a)), 2)
            if key not in self.beams:
                self.beams[key] = beam_mask(x, y, key, 1150, 0.05, blur=14)
                if len(self.beams) > 100:
                    self.beams.pop(next(iter(self.beams)))
            out += self.beams[key][..., None] * (0.2 + 0.25 * vis) * np.array([1.0, 0.95, 0.8], np.float32)
        add_spot(out, x, y, 40, (1.0, 0.95, 0.8), 0.6)
        add_spot(out, x, y, 9, (1.0, 1.0, 1.0), 1.6)
        self.waves.draw(out, t, k=0.8)


# --------------------------------------------------------------------------------------------- town, courthouse, train

def storefront_quads(vx, vy, side, n, x_edge, y_base, depth=0.9):
    """Façade quads for a street in one-point perspective. side=-1 left, +1 right. Returns [(near_x, far_x,
    top_near, top_far, bottom_near, bottom_far)] from near to far."""
    out = []
    xs = np.geomspace(1.0, 0.18, n + 1)
    for k in range(n):
        a, b = xs[k], xs[k + 1]
        xn = vx + (x_edge - vx) * a
        xf = vx + (x_edge - vx) * b
        hgt = (1 if k % 3 else 1.35) * (420 + 140 * ((k * 7) % 3))
        tn = vy - (vy - (y_base - hgt)) * a
        tf = vy - (vy - (y_base - hgt)) * b
        bn = vy + (y_base - vy) * a
        bf = vy + (y_base - vy) * b
        out.append((xn, xf, tn, tf, bn, bf))
    return out


class Town(Shot):
    """A small-town main street at night after rain: brick storefronts on both sides, streetlights, lit windows, wet
    pavement with reflections, and the courthouse at the end of the street. tower: "dome", "clock" or "none".
    sign: a vertical blade sign on the right ("HOTEL", "THEATER"...) - only if the story needs it."""
    focus = (540, 980)
    fog_d = 0.12
    ghost_xy = (640, 1300)
    ghost_h = 300

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = night_sky(601 + self.seed, moon=(860, 330, 40), clouds=0.45)
        vx, vy = 540, 1020
        c = cv()
        lights = cv()
        tower = p.get("tower", "dome")
        if tower != "none":                                                                 # the courthouse
            c.rect(380, 860, 700, 1030, "#080b0c")
            c.poly([(360, 862), (540, 800), (720, 862)], "#070a0b")
            if tower == "dome":
                c.rect(480, 700, 600, 810, "#090c0d")
                c.c.drawPath(smooth_path([(470, 712), (480, 640), (540, 600), (600, 640), (610, 712)], True),
                             paint("#090c0d"))
                c.rect(534, 560, 546, 604, "#090c0d")
                lights.circle(540, 750, 18, "#ffe6b0", 0.7)
            else:
                c.rect(500, 600, 580, 830, "#090c0d")
                c.poly([(494, 604), (540, 520), (586, 604)], "#07090a")
                lights.circle(540, 660, 26, "#ffe6b0", 0.75)
                lights.circle(540, 660, 22, "#000000", 0.0)
            for k in range(5):
                lights.rect(400 + k * 60, 900, 424 + k * 60, 950, WARM, 0.5 * (k % 2))
        for side, edge in ((-1, -60), (1, W + 60)):
            for k, (xn, xf, tn, tf, bn, bf) in enumerate(storefront_quads(vx, vy, side, 6, edge, 1420)):
                shade = "#0d0806" if k % 2 else "#110a07"
                c.poly([(xn, tn), (xf, tf), (xf, bf), (xn, bn)], shade)
                c.line([(xn, tn), (xf, tf)], "#3a4a48", 2, 0.5)
                c.line([(xf, tf), (xf, bf)], "#050303", 3, 0.8)
                for r in range(3):                                                         # upper windows
                    for j in range(3):
                        u0, u1 = (j + 0.2) / 3, (j + 0.65) / 3
                        v0 = 0.12 + r * 0.17
                        pts = []
                        for (uu, vv) in ((u0, v0), (u1, v0), (u1, v0 + 0.11), (u0, v0 + 0.11)):
                            xq = xn + (xf - xn) * uu
                            yq = (tn + (tf - tn) * uu) + ((bn + (bf - bn) * uu) - (tn + (tf - tn) * uu)) * vv
                            pts.append((xq, yq))
                        on = hash2(k * 3 + j, r + side * 5, self.seed) > 0.72
                        c.poly(pts, "#06090a")
                        if on:
                            lights.poly(pts, WARM, 0.75)
                pts = []                                                                   # a lit shop window
                for (uu, vv) in ((0.1, 0.72), (0.85, 0.72), (0.85, 0.93), (0.1, 0.93)):
                    xq = xn + (xf - xn) * uu
                    yq = (tn + (tf - tn) * uu) + ((bn + (bf - bn) * uu) - (tn + (tf - tn) * uu)) * vv
                    pts.append((xq, yq))
                if hash2(k, side, self.seed + 9) > 0.45:
                    lights.poly(pts, "#ffc47a", 0.55)
                else:
                    c.poly(pts, "#070a0b")
        c.poly([(-60, 1420), (vx - 6, vy), (vx + 6, vy), (W + 60, 1420), (W + 60, H), (-60, H)], "#0a0e10")
        for k in range(8):                                                                 # centre line dashes
            a, b = 0.18 + k * 0.1, 0.18 + k * 0.1 + 0.05
            y0, y1 = vy + (H - vy) * a ** 1.6, vy + (H - vy) * b ** 1.6
            c.line([(vx, y0), (vx, y1)], "#3a3a2a", 2 + 10 * a, 0.5)
        self.lamps = []
        for side in (-1, 1):                                                               # streetlights
            for k, a in enumerate((1.0, 0.62, 0.4, 0.27)):
                lx = vx + side * (470 * a)
                base = vy + (1500 - vy) * a
                top = base - 620 * a
                c.line([(lx, base), (lx, top)], "#030405", max(2, 9 * a))
                c.line([(lx, top), (lx - side * 50 * a, top)], "#030405", max(2, 7 * a))
                self.lamps.append((lx - side * 50 * a, top + 8 * a, a))
        if p.get("sign"):
            sx, sy = 930, 700
            c.rect(sx - 4, sy - 10, sx + 4, sy + 420, "#030405")
            sign = vertical_sign(p["sign"])
            comp(img, c.rgba())
            c = cv()
            comp(img, layer_from_pil(sign, sx - sign.width // 2 - 40, sy))
        comp(img, c.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]
        # reflections of the lights on the wet street: long vertical smears below each lamp
        refl = np.zeros((H, W, 3), np.float32)
        for (lx, ly, a) in self.lamps:
            add_spot(refl, lx, vy + (vy - ly) * 0.55 + 40 * a, 30 * a + 6, (1.0, 0.75, 0.45), 0.5)
        refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=4, sigmaY=40)
        self.refl = refl

    def animate(self, out, t, u):
        out += self.refl * (0.9 + 0.1 * flick(t, 8))
        for (lx, ly, a) in self.lamps:
            add_spot(out, lx, ly, 70 * a + 10, (1.0, 0.8, 0.5), 0.35)
            add_spot(out, lx, ly, 9 * a + 2, (1.0, 0.92, 0.75), 1.3)


def vertical_sign(text, w=110):
    from PIL import Image, ImageDraw
    S = 3
    f = C.font("xbold", 64 * S)
    h = int(len(text) * 74 + 50)
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * S - 1, h * S - 1), radius=14 * S, fill=(26, 12, 10, 255),
                        outline=(255, 120, 80, 255), width=4 * S)
    for i, ch in enumerate(text):
        tw = f.getlength(ch)
        d.text(((w * S - tw) / 2, (24 + i * 74) * S), ch, font=f, fill=(255, 170, 120, 255))
    return im.resize((w, h), Image.LANCZOS)


class Courthouse(Shot):
    """A county courthouse square at night: a big stone courthouse with a clock tower (tower="clock") or a dome
    (tower="dome"), or no tower (tower="none", an old hall), lit windows, lamps along the walk and bare trees."""
    focus = (540, 900)
    fog_d = 0.14
    ghost_xy = (760, 1250)
    ghost_h = 300

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = night_sky(621 + self.seed, moon=(880, 330, 46), clouds=0.4)
        land(img, 1180, 622 + self.seed, far="#0a1418")
        c = cv()
        lights = cv()
        x0, x1, base, top = 140, 940, 1230, 860
        c.rect(x0, top, x1, base, "#0d0c0b")
        c.poly([(x0 - 20, top + 4), (540, top - 120), (x1 + 20, top + 4)], "#0a0909")
        for wx in np.linspace(x0 + 40, x1 - 90, 9):
            for wy in (top + 50, top + 200):
                on = hash2(wx, wy, self.seed) > 0.6
                c.rect(wx, wy, wx + 46, wy + 110, "#070809")
                c.c.drawPath(smooth_path([(wx, wy + 10), (wx + 23, wy - 16), (wx + 46, wy + 10)], False),
                             paint("#2a2826", stroke=4))
                if on:
                    lights.rect(wx, wy, wx + 46, wy + 110, WARM, 0.65)
        if p.get("tower", "clock") == "dome":
            c.rect(460, 640, 620, 760, "#0c0b0a")
            c.c.drawPath(smooth_path([(448, 650), (460, 560), (540, 510), (620, 560), (632, 650)], True),
                         paint("#0c0b0a"))
            c.rect(530, 450, 550, 520, "#0c0b0a")
        elif p.get("tower", "clock") == "none":
            pass
        else:
            c.rect(470, 520, 610, 760, "#0c0b0a")
            c.poly([(460, 524), (540, 400), (620, 524)], "#090808")
            lights.circle(540, 590, 40, "#ffe6b0", 0.6)
            c.line([(540, 590), (540, 562)], "#0c0b0a", 4)
            c.line([(540, 590), (560, 598)], "#0c0b0a", 4)
        comp(img, c.rgba())
        tex = masonry(base - top, x1 - x0, bw=70, bh=30, seed=623 + self.seed, color=(0.12, 0.08, 0.06),
                      mortar=(0.05, 0.04, 0.035), var=0.25, stone=True)
        m = np.ones((base - top, x1 - x0), np.float32)
        put_tex(img, tex, m * 0.55, x0, top)
        d = cv()
        art.tree(d, 60, 1290, 860, seed=631 + self.seed, depth=8, spread=0.7, lean=0.08)
        art.tree(d, 1030, 1290, 820, seed=632 + self.seed, depth=8, spread=0.66, lean=-0.1)
        for k in range(10):
            d.rect(380 + k * 34, 1230 + k * 10, 700 - k * 34 + 2 * k, 1240 + k * 10, "#141312")
        d.poly([(-20, 1300), (W + 20, 1300), (W + 20, H), (-20, H)], "#06090a")
        d.poly([(470, 1300), (610, 1300), (760, H), (320, H)], "#0f1314")
        self.lamps = [(300, 1120), (780, 1120)]
        for lx, ly in self.lamps:
            d.rect(lx - 5, ly, lx + 5, 1320, "#030405")
            d.rect(lx - 18, ly - 30, lx + 18, ly + 4, "#030405")
        art.grass(d, 1560, 0, W, "#030506", n=300, hmin=10, hmax=40, seed=23 + self.seed)
        comp(img, d.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]

    def animate(self, out, t, u):
        for lx, ly in self.lamps:
            add_spot(out, lx, ly - 14, 90, (1.0, 0.8, 0.5), 0.3)
            add_spot(out, lx, ly - 14, 10, (1.0, 0.92, 0.75), 1.3)


class Train(Shot):
    """A freight train at night, side on, rolling past below a huge sand dune; the engine's smoke trails back.
    dune=False leaves the dune out. moving=False parks it."""
    focus = (540, 1000)
    fog_d = 0.16

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = night_sky(641 + self.seed, moon=(220, 360, 50), clouds=0.3)
        if p.get("dune", True):
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            prof = 1190 - 560 * np.exp(-((xx - 620) / 360.0) ** 2) - 40 * np.exp(-((xx - 260) / 130.0) ** 2)
            dune = cv2.GaussianBlur((yy > prof).astype(np.float32), (0, 0), 1.5)
            shade = np.clip(0.45 + 0.55 * (1 - (xx - 400) / 900.0), 0.3, 1.0)
            col = np.array([0.2, 0.22, 0.25], np.float32) * shade[..., None]
            img[:] = img * (1 - dune[..., None]) + col * dune[..., None]
            rim = np.exp(-np.maximum(yy - prof, 0) / 5.0) * (yy > prof)
            img += (rim * 0.1)[..., None]
        c = cv()
        c.poly([(-20, 1196), (W + 20, 1196), (W + 20, H), (-20, H)], "#060809")
        c.rect(-20, 1300, W + 20, 1310, "#2a2e30")                                         # the rails
        for k in range(0, W + 40, 34):
            c.rect(k, 1310, k + 18, 1322, "#141618")
        art.grass(c, 1500, 0, W, "#030506", n=380, hmin=12, hmax=50, seed=25 + self.seed)
        comp(img, c.rgba())
        self.img = img
        self.moving = p.get("moving", True)
        # one long strip of cars, drawn once, scrolled at render time
        k_ = 1.4
        L = int(3400 * k_)
        s = Canvas(L, int(300 * k_))
        x = 40 * k_

        def R(a, b, c_, d_, col):
            s.rect(a * k_, b * k_, c_ * k_, d_ * k_, col)
        x0_ = 40
        R(x0_, 90, x0_ + 300, 230, "#050607")                                               # the locomotive
        R(x0_ + 210, 30, x0_ + 300, 230, "#050607")
        R(x0_ + 40, 40, x0_ + 70, 90, "#050607")
        R(x0_ + 30, 30, x0_ + 80, 44, "#050607")
        s.line([(x0_ * k_, 90 * k_), ((x0_ + 210) * k_, 90 * k_)], "#3c4a4c", 2, 0.6)
        for wx in (x0_ + 40, x0_ + 110, x0_ + 180, x0_ + 250):
            s.circle(wx * k_, 246 * k_, 26 * k_, "#050607")
        self.engine_stack = ((x0_ + 55) * k_, 30 * k_)
        self.engine_lamp = ((x0_ + 6) * k_, 120 * k_)
        xc = x0_ + 330
        while xc < 3400 - 260:
            s.poly([(xc * k_, 80 * k_), ((xc + 250) * k_, 80 * k_), ((xc + 232) * k_, 210 * k_),
                    ((xc + 18) * k_, 210 * k_)], "#08090a")                                  # an open hopper car
            s.line([(xc * k_, 80 * k_), ((xc + 250) * k_, 80 * k_)], "#3c4a4c", 2, 0.6)
            s.poly([((xc + 12) * k_, 80 * k_), ((xc + 238) * k_, 80 * k_), ((xc + 225) * k_, 60 * k_),
                    ((xc + 25) * k_, 60 * k_)], "#2a2a26")                                 # sand heaped on top
            for wx in (xc + 40, xc + 90, xc + 160, xc + 210):
                s.circle(wx * k_, 240 * k_, 20 * k_, "#050607")
            R(xc + 250, 190, xc + 270, 200, "#050607")
            xc += 270
        self.strip = s.rgba()
        self.L = L
        self.k = k_
        self.smoke = Fog(seed=643, scale=120, color="#5a6a6a", density=0.5, top=0.0, bottom=1.0, speed=60, w=720, h=280)

    def animate(self, out, t, u):
        off = (500 + u * 150.0) % (self.L + W) if self.moving else 700
        x0 = int(W - off)
        y0 = int(1300 - 262 * self.k)
        strip = self.strip
        X0, X1 = max(0, x0), min(W, x0 + self.L)
        if X1 > X0:
            seg = strip[:, X0 - x0:X1 - x0]
            sub = out[y0:y0 + seg.shape[0], X0:X1]
            sub *= (1 - seg[..., 3:4])
            sub += seg[..., :3]
            ex = x0 + self.engine_lamp[0]
            if -50 < ex < W + 50:
                add_spot(out, ex, y0 + self.engine_lamp[1], 50, (1.0, 0.9, 0.7), 0.6)
                add_spot(out, ex, y0 + self.engine_lamp[1], 8, (1.0, 1.0, 0.9), 1.5)
            sx = x0 + self.engine_stack[0]
            if -300 < sx < W + 200:
                sm = self.smoke.layer(t, 0.7)
                yy = np.linspace(1, 0, sm.shape[0])[:, None]
                sm = sm * yy
                X = int(sx)
                Y = int(y0 + self.engine_stack[1] - sm.shape[0])
                a0, a1 = max(0, X), min(W, X + sm.shape[1])
                if a1 > a0 and Y >= 0:
                    out[Y:Y + sm.shape[0], a0:a1] = 1 - (1 - out[Y:Y + sm.shape[0], a0:a1]) * \
                        (1 - sm[:, a0 - X:a1 - X, None] * np.array([0.32, 0.36, 0.38], np.float32))


# --------------------------------------------------------------------------------------------- the older scenes

class Cemetery(Shot):
    """An old cemetery at night. style="gate" (stone gateposts and an iron fence, town houses beyond),
    "rows" (two big oaks over rows of old stones), "country" (a little cemetery on a rise in farm country),
    "plot" (a family plot up close: an obelisk and old headstones). shadows=True adds dark shapes drifting
    between the stones."""
    focus = (540, 1050)

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        style = p.get("style", "gate")
        if style == "gate":
            self.s = Shadows() if p.get("shadows") else TownCemetery(seed=self.seed, fog_d=0.0)
        elif style == "rows":
            self.s = Riverview(seed=self.seed, group=False)
        elif style == "plot":
            self.s = FamilyPlot(dur=self.dur)
        else:
            self.s = CountryCemetery(seed=self.seed)
        self.s.fog = None if style != "rows" else self.s.fog
        self.img = self.s.img

    def render(self, t, u):
        if isinstance(self.s, (Shadows,)):
            out = self.s.img.copy()
            for g in self.s.figs:
                a = (0.45 + 0.35 * math.sin(t * 0.8 + g["ph"])) * min(1.0, u / 0.8)
                put(out, g["m"], g["x"] + g["v"] * t, g["y"], (0.01, 0.015, 0.02), a, mode="dark")
        else:
            out = self.s.img.copy()
        self.extras(out, t, u)
        return self.camera(out, u)


class CountryCemetery:
    def __init__(self, seed=0):
        img = night_sky(661 + seed, moon=(800, 380, 60))
        land(img, 1080, 662 + seed, far="#0a1418")
        c = cv()
        art.hills(img, 1120, 40, 500, "#071012", 663 + seed, rim="#2c4442", rim_w=3, rim_a=0.3)
        art.tree(c, 760, 1110, 820, seed=664 + seed, depth=8, spread=0.7, lean=-0.06)
        art.gravestones(c, 1110, 300, 900, 16, seed=665 + seed, hmin=30, hmax=80)
        art.fence(c, 1140, 260, 960, spacing=34, h=56, seed=6, broken=0.2)
        road(c, 560, 1120, bottom=(300, 860), color="#10181a", edge="#2a4040")
        art.grass(c, 1500, 0, W, "#030506", n=420, hmin=14, hmax=60, seed=27 + seed)
        comp(img, c.rgba())
        self.img = img
        self.fog = None


class Plot(Cemetery):
    def __init__(self, p=None):
        p = dict(p or {})
        p.setdefault("style", "plot")
        super().__init__(p)


class ChapelScene(Shot):
    """A plain country chapel with a belfry among old stones. lit=True lights its windows."""
    focus = (520, 1000)

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = night_sky(681 + self.seed, moon=(830, 360, 54))
        land(img, 1120, 682 + self.seed, far="#0a1418")
        c = cv()
        lights = cv()
        art.tree(c, 980, 1150, 880, seed=683 + self.seed, depth=8, spread=0.66, lean=-0.1)
        chapel(c, lights, 230, 1140, s=1.25, lit=0.9 if p.get("lit") else 0.0)
        art.gravestones(c, 1220, 20, 1060, 14, seed=684 + self.seed, hmin=50, hmax=120)
        art.grass(c, 1400, 0, W, "#030506", n=420, hmin=14, hmax=60, seed=29 + self.seed)
        comp(img, c.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]


class House(Shot):
    """An old house at night. style="farmhouse" (a two-storey gable farmhouse with a porch, by a lake),
    "porch" (an 1850s house with a two-level front porch below mountain ridges), "victorian" (a tall Queen Anne
    house with a turret). lit: which windows glow (list of 0/1). window_ghost=True puts a faint figure in one."""
    focus = (520, 950)

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        style = p.get("style", "farmhouse")
        if style == "porch":
            s = ChastainHouse(seed=self.seed, lit=bool(p.get("lit", True)), kids=bool(p.get("kids")),
                              close=bool(p.get("close")))
            self.img, self.lights = s.img, s.lights
            self.s = s
        else:
            img = night_lake_sky(701 + self.seed, moon=(880, 380, 60), clouds=0.32)
            land(img, 1140, 702 + self.seed, far="#0a1418")
            c = cv()
            lights = cv()
            lit = tuple(p.get("lit", (0, 1, 0, 0, 0)))
            if style == "victorian":
                self.win = victorian(c, lights, 230, 1180, s=1.0, lit=lit)
            else:
                art.farmhouse(c, lights, 240, 1170, s=1.05, lit=lit)
                self.win = (240 + 420 * 1.05 * 0.62, 1170 - 300 * 1.05 * 0.83)
            art.tree(c, 110, 1180, 980, seed=711 + self.seed, depth=8, spread=0.7, lean=0.1)
            art.tree(c, 990, 1170, 800, seed=712 + self.seed, depth=8, spread=0.62, lean=-0.14)
            art.fence(c, 1250, -20, 1100, spacing=40, h=70, seed=8, broken=0.3)
            art.grass(c, 1320, 0, W, "#030506", n=420, hmin=14, hmax=60, seed=31 + self.seed)
            comp(img, c.rgba())
            self.img = img
            self.lights = lights.rgba()[..., :3]
            self.s = None
        if p.get("window_ghost") and self.s is None:
            self.wg = sprite(lambda k: art.figure(k, 40, 130, 120, color="#ffffff", dress=True), 80, 140, blur=2.5)
        else:
            self.wg = None

    def animate(self, out, t, u):
        if self.wg is not None:
            wx, wy = self.win
            a = (0.35 + 0.2 * math.sin(t * 1.1)) * min(1.0, u / 1.5)
            put(out, self.wg, wx + 30, wy + 92, (0.05, 0.03, 0.02), a, mode="dark")


def victorian(c, lights, x, y, s=1.0, lit=(0, 1, 0, 1, 0, 0), dark="#05090b", rim="#3b5654"):
    """A tall Queen Anne house: front gable, a round corner turret with a conical roof, wraparound porch."""
    w, h = 470 * s, 360 * s
    art.rim_shape(c, poly_path([(x, y), (x, y - h), (x + w * 0.62, y - h), (x + w * 0.62, y)]), dark, rim, (3, 3))
    art.rim_shape(c, poly_path([(x - 16 * s, y - h), (x + w * 0.31, y - h - 230 * s), (x + w * 0.62 + 16 * s, y - h)]),
                  dark, rim, (3, 3))
    tx = x + w * 0.62
    art.rim_shape(c, poly_path([(tx, y), (tx, y - h - 60 * s), (tx + 150 * s, y - h - 60 * s), (tx + 150 * s, y)]),
                  dark, rim, (3, 3))
    art.rim_shape(c, poly_path([(tx - 12 * s, y - h - 60 * s), (tx + 75 * s, y - h - 300 * s),
                                (tx + 162 * s, y - h - 60 * s)]), dark, rim, (3, 3))
    c.rect(x - 30 * s, y - 150 * s, tx + 190 * s, y - 132 * s, dark)                       # porch roof
    for px in np.linspace(x - 20 * s, tx + 170 * s, 8):
        c.rect(px, y - 134 * s, px + 8 * s, y, dark)
    wins = [(x + 50 * s, y - h + 50 * s), (x + 180 * s, y - h + 50 * s), (x + w * 0.31 - 26 * s, y - h - 130 * s),
            (tx + 50 * s, y - h + 20 * s), (tx + 50 * s, y - h + 170 * s), (x + 120 * s, y - 120 * s)]
    for i, (wx, wy) in enumerate(wins):
        on = lit[i] if i < len(lit) else 0
        ww, wh = 52 * s, 96 * s
        if on:
            c.rect(wx, wy, wx + ww, wy + wh, "#4a2a10")
            lights.rect(wx, wy, wx + ww, wy + wh, WARM, 0.9 * on)
            lights.glow(wx + ww / 2, wy + wh / 2, 130 * s, WARM, 0.3 * on)
            lights.rect(wx + ww / 2 - 2, wy, wx + ww / 2 + 2, wy + wh, "#000000", 1.0)
        else:
            c.rect(wx, wy, wx + ww, wy + wh, "#0d1619")
    return wins[3]


class RoadScene(Shot):
    """A dark country road at night under bare trees, a green street sign in front (sign: its text, or leave it
    out), lake=True puts a lake beside the road, car=True parks a 1960s sedan on the shoulder (wrong for older
    stories), tail_lights=True shows a car's red tail lights pulling away down the road (no car drawn, any era)."""
    focus = (700, 1000)

    def animate(self, out, t, u):
        if self.p.get("tail_lights"):
            k = min(1.0, u / max(1.5, self.dur))
            e = 1 - (1 - k) ** 2
            vx, vy = 760, 1014                                     # the road's far end
            kk = (1 - e) ** 1.3 * 0.55
            y = vy + (H - vy) * kk
            x = vx + (900 - vx) * kk + 0.3 * math.sin(kk * math.pi) * 60
            gap = 70 * (1 - e) ** 1.3 + 6
            a = 1.0 - 0.6 * e
            for dx in (-gap / 2, gap / 2):
                add_spot(out, x + dx, y, 22 * (1 - e) + 4, (1.0, 0.1, 0.05), 0.5 * a)
                add_spot(out, x + dx, y, 5 * (1 - e) + 1.5, (1.0, 0.5, 0.4), 1.3 * a)
            add_spot(out, x, y + 30 * (1 - e), 120 * (1 - e) + 20, (0.6, 0.05, 0.02), 0.12 * a)

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = night_lake_sky(721 + self.seed, moon=(300, 420, 60 if not p.get("full_moon") else 100), clouds=0.28)
        hz = 1010
        art.hills(img, hz - 20, 26, 460, "#0a1519", 722 + self.seed, rim="#36514f", rim_w=3, rim_a=0.3)
        yy = np.arange(H, dtype=np.float32)[:, None]
        xx = np.arange(W, dtype=np.float32)[None, :]
        if p.get("lake", False):
            lake = ((yy >= hz) & (yy < 1300)).astype(np.float32) * np.clip((700 - xx - (yy - hz) * 0.9) / 30.0, 0, 1)
            ripple = cv2.resize(fbm(H // 8, W // 2, scale=6, octaves=3, seed=723), (W, H), interpolation=cv2.INTER_CUBIC)
            water = np.array([0.022, 0.042, 0.052], np.float32) * (0.7 + 0.6 * ripple[..., None])
            glint = np.exp(-((xx - 300) / (18 + (yy - hz) * 0.22)) ** 2) * (yy > hz) * (0.25 + 0.75 * ripple)
            water = water + (glint * 0.75)[..., None] * np.array([0.7, 0.85, 0.82], np.float32)
            img = img * (1 - lake[..., None]) + water * lake[..., None]
        else:
            lake = np.zeros((H, W), np.float32)
        ground = ((yy >= hz) * (1 - lake)).astype(np.float32)
        img = img * (1 - ground[..., None]) + np.array([0.022, 0.034, 0.038], np.float32) * ground[..., None]
        c = cv()
        from core import lin
        vx, vy, xl, xr = 760, hz + 4, 430, 1170

        def edge_x(y, x_bottom):
            k = (y - vy) / (H - vy)
            return vx + (x_bottom - vx) * k + 0.3 * math.sin(k * math.pi) * 60
        ys = np.linspace(vy, H, 30)
        left = [(edge_x(y, xl), y) for y in ys]
        right = [(edge_x(y, xr), y) for y in ys]
        c.poly(left + right[::-1], "#1a2a2e", shader=lin((0, vy), (0, H), ["#2c3d42", "#121c1f"]))
        c.line(left, "#5a7c7c", 3, 0.55)
        c.line(right, "#5a7c7c", 3, 0.55)
        for k in range(9):                                                     # the centre line, fading off
            a, b = 0.1 + k * 0.1, 0.1 + k * 0.1 + 0.045
            ya, yb = vy + (H - vy) * a, vy + (H - vy) * b
            c.line([(edge_x(ya, 800), ya), (edge_x(yb, 800), yb)], "#9a9468", 2 + 9 * a, 0.45)
        for k, (tx, th) in enumerate(((990, 860), (1080, 1040), (700, 300), (880, 420), (640, 220))):
            art.tree(c, tx, hz + 10 + (th > 500) * (th * 0.28), th, seed=730 + k + self.seed, depth=7, spread=0.6,
                     lean=-0.18)
        for k in range(9):
            art.tree(c, 40 + k * 70, hz - 8, 70 + 40 * (k % 3), seed=740 + k, depth=5, spread=0.6)
        for gy in (1160, 1330, 1520, 1760):                                    # grass on the verges, not the road
            for g0, g1, n_ in ((-10, edge_x(gy, xl) - 14, 110), (edge_x(gy, xr) + 14, W + 10, 60)):
                if g1 - g0 > 20:
                    art.grass(c, gy, g0, g1, "#030506", n=n_, hmin=14, hmax=60, seed=33 + int(gy) + self.seed)
        if p.get("car"):
            car(c, 250, 1330, s=0.8)
        if p.get("sign"):
            c.rect(786, 760, 802, 1640, "#0b0f10")
            c.line([(788, 760), (788, 1640)], "#44585a", 2, 0.6)
        comp(img, c.rgba())
        if p.get("sign"):
            comp(img, layer_from_pil(street_sign(p["sign"]), 794 - 280, 640))
        self.img = img


class Woods(Shot):
    """Bare woods under the moon with a path; lantern=True: a lantern glow moving away between the trees (no one
    shown)."""
    focus = (560, 1100)
    fog_d = 0.26

    def __init__(self, p=None):
        super().__init__(p)
        img = night_lake_sky(751 + self.seed, moon=(760, 420, 80), clouds=0.25, glow_k=0.85)
        land(img, 1080, 752 + self.seed, far="#0a1418")
        c = cv()
        for k in range(14):
            tx = -40 + k * 86 + (k % 3) * 18
            th = 700 + (k * 137 + self.seed * 53) % 500
            art.tree(c, tx, 1100 + (k % 4) * 30, th, seed=760 + k + self.seed, depth=7, spread=0.55,
                     lean=((k % 5) - 2) * 0.05)
        c.poly([(-20, 1180), (W + 20, 1170), (W + 20, H), (-20, H)], "#040708")
        c.poly([(500, 1180), (580, 1180), (820, H), (300, H)], "#0b1012", 0.9)
        art.grass(c, 1400, 0, W, "#030405", n=460, hmin=14, hmax=70, seed=35 + self.seed)
        comp(img, c.rgba())
        self.img = img
        self.lantern = bool(self.p.get("lantern"))

    def animate(self, out, t, u):
        if self.lantern:
            p = min(1.0, u / max(1.0, self.dur))
            x = 600 + 120 * p + 10 * math.sin(t * 3.0)
            y = 1180 - 60 * p + 6 * abs(math.sin(t * 2.2))
            fl = flick(t, 13)
            lm = light_map(H, W, x, y, 380 * (1.2 - 0.6 * p), power=1.3)
            out += lm[..., None] * np.array(LANT, np.float32) * 0.45 * fl
            add_spot(out, x, y, 30 * (1.2 - 0.6 * p), (1.0, 0.75, 0.4), 0.9 * fl)
            add_spot(out, x, y, 6, (1.0, 0.95, 0.8), 1.5)


class Room(Shot):
    """Inside an old house on a stormy night: plank walls, rain on the window, a candle on a little table, empty
    chairs along the wall. No one is shown."""
    focus = (540, 950)
    fog_d = 0.0

    def __init__(self, p=None):
        super().__init__(p)
        self.s = ViewingRoom()
        self.img = self.s.img

    def render(self, t, u):
        out = self.s.render(t, u)               # the room's own candlelight, rain and slow push-in
        self.extras(out, t, u)
        return out


class CellarScene(Shot):
    focus = (540, 1050)
    fog_d = 0.0

    def __init__(self, p=None):
        super().__init__(p)
        from reel_haunts2 import Cellar
        self.s = Cellar()
        self.img = self.s.img

    def render(self, t, u):
        out = self.s.render(t, u)
        self.extras(out, t, u)
        return out


class Backdrop(Shot):
    """A dark, softly lit backdrop for a text card (a year, a quote, a headline)."""
    focus = (540, 960)
    fog_d = 0.12
    fog_band = (0.2, 1.0)

    def __init__(self, p=None):
        super().__init__(p)
        img = art.vgrad(H, W, [(0, "#020304"), (0.5, "#0a1114"), (1.0, "#030405")])
        n = cv2.resize(fbm(H // 8, W // 8, scale=20, octaves=4, seed=771 + self.seed), (W, H),
                       interpolation=cv2.INTER_CUBIC)
        img += (n * 0.03)[..., None]
        self.img = img.astype(np.float32)


KINDS = {
    "cemetery": Cemetery, "plot": Plot, "chapel": ChapelScene, "house": House, "road": RoadScene, "woods": Woods,
    "room": Room, "cellar": CellarScene, "jail": Jail, "cell": Cell, "prison": Prison, "dunes": Dunes, "lake": Lake,
    "lighthouse": Lighthouse, "town": Town, "courthouse": Courthouse, "train": Train, "card": Backdrop,
}

# what each kind sounds like underneath the narrator (reel_story.py mixes these in)
AMBIENCE = {
    "cemetery": ("wind", "owl"), "plot": ("wind", "owl"), "chapel": ("wind", "bell"), "house": ("wind", "creak"),
    "road": ("wind", "owl"), "woods": ("wind", "owl"), "room": ("rain", "creak"), "cellar": ("room", "creak"),
    "jail": ("wind", "clang"), "cell": ("room", "drip"), "prison": ("wind", "siren_far"), "dunes": ("waves", "wind"),
    "lake": ("waves", None), "lighthouse": ("waves", "foghorn"), "town": ("rain", None), "courthouse": ("wind", "bell"),
    "train": ("rumble", "whistle"), "card": ("room", None),
}


def make(spec, dur):
    spec = dict(spec or {})
    kind = spec.pop("kind", "card")
    spec["dur"] = dur
    if kind not in KINDS:
        raise KeyError("unknown scene kind %r (have: %s)" % (kind, ", ".join(sorted(KINDS))))
    return KINDS[kind](spec)
