"""Typographic scenes: title and chapter cards, paper date cards, numbers, maps,
manuscripts and lower-third overlays."""
import json
import math
import os
from functools import lru_cache

import cv2
import numpy as np
import skia

from core import (W, H, OW, OH, Canvas, Camera, Fog, rgb, mix, clamp01, smoothstep, sstep, ease, ease_out, fbm,
                  noise1d, add_spot, poly_path, smooth_path, paint, lin, rad, ADD, blur, flicker, text_mask, text_layer,
                  paste, font, measure, Embers, vignette, ROOT, PAPER, INK, AMBER, GHOST, BLOOD, warp, lerp)
from art import comp, vgrad
from scene import Scene, Painted, Ctx

PARCH = "#e8dcc0"


# ----------------------------------------------------------------------------- textures

@lru_cache(maxsize=4)
def paper_texture(seed=0, color=PARCH, burn=0.55, w=OW, h=OH):
    base = fbm(h // 2, w // 2, scale=220, octaves=6, seed=seed)
    base = cv2.resize(base, (w, h))
    fib = fbm(h // 2, w // 2, scale=3, octaves=2, seed=seed + 1)
    fib = cv2.resize(fib, (w, h))
    img = rgb(color)[None, None, :] * (0.9 + 0.12 * base[..., None] + 0.05 * (fib[..., None] - 0.5))
    st = fbm(h // 4, w // 4, scale=70, octaves=5, seed=seed + 2)
    st = cv2.resize(st, (w, h))
    ring = smoothstep(0.66, 0.70, st) * smoothstep(0.76, 0.70, st)
    blot = smoothstep(0.72, 0.95, st)
    img *= (1 - 0.10 * blot[..., None] * np.array([0.6, 0.9, 1.4], np.float32))
    img *= (1 - 0.08 * ring[..., None] * np.array([0.5, 0.9, 1.5], np.float32))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ex = np.minimum(xx, w - xx) / (w * 0.5)
    ey = np.minimum(yy, h - yy) / (h * 0.5)
    e = np.minimum(ex, ey * (h / w) * 1.6)
    edge = smoothstep(0.32, 0.0, e) * burn
    img *= (1 - edge[..., None] * np.array([0.45, 0.62, 0.85], np.float32))
    return img.astype(np.float32)


@lru_cache(maxsize=2)
def newsprint_texture(seed=0):
    img = paper_texture(seed, "#d8d0bc", 0.35)
    return img


@lru_cache(maxsize=2)
def dark_bg(seed=0, top="#05090b", bottom="#0c171b"):
    img = vgrad(H, W, [(0, top), (1, bottom)])
    n = cv2.resize(fbm(H // 4, W // 4, scale=80, octaves=5, seed=seed), (W, H))
    img *= (0.8 + 0.4 * n[..., None])
    return img.astype(np.float32)


# ----------------------------------------------------------------------------- text blocks

class Block:
    """A piece of text that fades (or types) in at t_in and optionally out at t_out."""

    def __init__(self, text, fname="fell", size=60, color=PAPER, x=W / 2, y=H / 2, anchor="mm", t_in=0.0, fade=0.7,
                 t_out=None, fade_out=0.6, type_cps=None, glow=None, glow_a=0.55, glow_sigma=None, tracking=0.0,
                 max_w=None, align="center", rise=12, shadow=0.0, line_gap=1.18, alpha=1.0, scale_in=0.0):
        self.text = text
        self.x, self.y, self.anchor = x, y, anchor
        self.t_in, self.fade, self.t_out, self.fade_out = t_in, fade, t_out, fade_out
        self.type_cps = type_cps
        self.rise = rise
        self.alpha = alpha
        self.scale_in = scale_in
        self.fname, self.size, self.tracking = fname, size, tracking
        if type_cps:
            f = font(fname, size)
            lines = text.split("\n")
            if max_w:
                from core import wrap_lines
                lines = wrap_lines(lines, f, max_w, tracking, size)
            self.lines = []
            lh = int(size * line_gap)
            for i, l in enumerate(lines):
                lay = text_layer(l if l else " ", fname, size, color, tracking=tracking, glow=glow, glow_a=glow_a,
                                 glow_sigma=glow_sigma, shadow=shadow)
                cum = [measure(l[:k], f, tracking, size) for k in range(len(l) + 1)]
                self.lines.append((lay, cum, i * lh, measure(l, f, tracking, size)))
            self.total = sum(len(l) for l in lines)
            self.height = lh * len(lines)
            self.width = max(c[3] for c in self.lines)
            self.layer = None
        else:
            self.layer = text_layer(text, fname, size, color, tracking=tracking, glow=glow, glow_a=glow_a,
                                    glow_sigma=glow_sigma, max_w=max_w, align=align, shadow=shadow, line_gap=line_gap)

    def alpha_at(self, t):
        a = sstep(self.t_in, self.t_in + self.fade, t) if self.fade > 0 else (1.0 if t >= self.t_in else 0.0)
        if self.t_out is not None:
            a *= 1 - sstep(self.t_out, self.t_out + self.fade_out, t)
        return a * self.alpha

    def draw(self, frame, t, dx=0.0, dy=0.0, k=1.0):
        a = self.alpha_at(t) * k
        if a <= 0.002:
            return
        if self.layer is not None:
            lay = self.layer
            off = (1 - ease_out(min(1.0, (t - self.t_in) / max(0.01, self.fade * 1.6)))) * self.rise
            if self.scale_in:
                s = 1 + self.scale_in * (1 - ease_out(min(1.0, (t - self.t_in) / max(0.01, self.fade * 2.5))))
                if abs(s - 1) > 0.002:
                    lay = cv2.resize(lay, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
            paste(frame, lay, self.x + dx, self.y + dy + off, a=a, anchor=self.anchor)
        else:
            n = (t - self.t_in) * self.type_cps
            if n <= 0:
                return
            # block origin from anchor
            bw, bh = self.width, self.height
            x0 = self.x - (bw / 2 if self.anchor[0] == "m" else (bw if self.anchor[0] == "r" else 0))
            y0 = self.y - (bh / 2 if self.anchor[1] == "m" else (bh if self.anchor[1] == "b" else 0))
            left = n
            for lay, cum, ly, lw in self.lines:
                if left <= 0:
                    break
                k_ = int(min(left, len(cum) - 1))
                vis = cum[k_]
                left -= len(cum) - 1
                pad = (lay.shape[1] - lw) / 2
                cut = int(pad + vis + 2) if k_ < len(cum) - 1 else lay.shape[1]
                part = lay[:, :max(1, cut)]
                paste(frame, part, x0 - pad + dx, y0 + ly + dy - lay.shape[0] / 2 + self.size * 0.55, a=a, anchor="lt")


# ----------------------------------------------------------------------------- base scenes

class TextScene(Scene):
    """Text blocks over a background; background is 'dark', 'paper', 'news' or an RGB array."""

    def __init__(self, blocks, dur, bg="dark", fog=True, embers=False, drift=0.03, seed=0, extra=None, tint=None,
                 vig=True, painting_text=False):
        super().__init__()
        self.blocks = blocks
        self.dur = dur
        self.bg_kind = bg
        self.use_fog = fog
        self.use_embers = embers
        self.drift = drift
        self.seed = seed
        self.extra = extra or []
        self.tint = tint

    def build(self):
        if isinstance(self.bg_kind, np.ndarray):
            self.bg = self.bg_kind
        elif self.bg_kind == "paper":
            self.bg = cv2.resize(paper_texture(self.seed % 3), (int(W * 1.06), int(H * 1.06)))
        elif self.bg_kind == "news":
            self.bg = cv2.resize(newsprint_texture(0), (int(W * 1.06), int(H * 1.06)))
        else:
            self.bg = cv2.resize(dark_bg(self.seed % 2), (int(W * 1.06), int(H * 1.06)))
        if self.tint is not None:
            self.bg = self.bg * rgb(self.tint)[None, None, :]
        self.fog = Fog(seed=self.seed + 3, density=0.20, top=0.0, bottom=1.0, color="#6f9690", speed=14) \
            if (self.use_fog and self.bg_kind == "dark") else None
        self.em = Embers(26, 200, W - 200, H + 30, rise=110, spread=80, life=(5, 9), size=(1.0, 2.0),
                         seed=self.seed + 7) if self.use_embers else None

    def render(self, t, u):
        self.ensure()
        z = 1.0 + self.drift * ease(u)
        bh, bw = self.bg.shape[:2]
        # the background is 6% larger than the frame; zoom slowly into its centre
        m = np.array([[bw / W / z, 0, (bw - bw / z) / 2], [0, bh / H / z, (bh - bh / z) / 2]], np.float32)
        frame = cv2.warpAffine(self.bg, m, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                               borderMode=cv2.BORDER_REFLECT)
        if self.fog is not None:
            self.fog.apply(frame, t)
        if self.em is not None:
            self.em.draw(frame, t, k=0.6)
        for f in self.extra:
            f(frame, t, u)
        for b in self.blocks:
            b.draw(frame, t)
        return frame


def title_card(dur):
    blocks = [
        Block("LAPORTE WEATHER NOW PRESENTS", "sans", 26, GHOST, W / 2, 330, t_in=0.3, fade=1.0, tracking=0.32,
              alpha=0.75),
        Block("Before", "black", 170, "#f3e6c8", W / 2, 478, t_in=0.8, fade=1.6, glow="#ff7a1a",
              glow_a=0.55, rise=0, scale_in=0.05),
        Block("Pumpkins", "black", 215, "#f3e6c8", W / 2, 668, t_in=1.3, fade=1.6, glow="#ff7a1a", glow_a=0.55,
              rise=0, scale_in=0.05),
        Block("The Real History of Halloween", "fell_it", 62, "#e2d2ae", W / 2, 838, t_in=2.0, fade=1.2,
              glow="#ff7a1a", glow_a=0.25, rise=6, alpha=0.92),
    ]
    return TextScene(blocks, dur, bg="dark", embers=True, drift=0.05, seed=1)


NUMWORDS = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"]


def chapter_card(n, title, dur):
    def line(frame, t, u):
        a = sstep(0.5, 1.4, t)
        w = 140 * ease_out(sstep(0.4, 1.4, t))
        if w > 1:
            cv2.line(frame, (int(W / 2 - w), 512), (int(W / 2 + w), 512),
                     tuple(float(c) * 0.85 * a for c in rgb(AMBER)), 2, cv2.LINE_AA)
    blocks = [Block("CHAPTER %s" % NUMWORDS[n].upper(), "sans", 30, GHOST, W / 2, 452, t_in=0.15, fade=0.8,
                    tracking=0.42, alpha=0.8),
              Block(title, "fell", 104, "#f1e4c6", W / 2, 600, t_in=0.45, fade=1.0, glow="#ff7a1a", glow_a=0.35,
                    rise=8)]
    return TextScene(blocks, dur, bg="dark", embers=True, drift=0.04, seed=n, extra=[line])


def paper_card(blocks, dur, seed=0, stamp=None, extra=None):
    ex = list(extra or [])
    if stamp:
        ex.append(stamp)
    return TextScene(blocks, dur, bg="paper", fog=False, drift=0.035, seed=seed, extra=ex)


def stamp(text, x, y, t_in, size=58, color=BLOOD, rot=-12, box=True):
    lay = text_layer(text, "type", size, color, tracking=0.08)
    hh, ww = lay.shape[:2]
    if box:
        c = Canvas(ww + 40, hh + 20)
        c.rect(14, 10 + hh * 0.18, ww + 26, hh * 0.82 + 10, color, 1.0)
        c.rect(20, 16 + hh * 0.18, ww + 20, hh * 0.82 + 4, "#000000", 1.0, mode=skia.BlendMode.kDstOut)
        bl = c.rgba()
        big = np.zeros_like(bl)
        oy, ox = (bl.shape[0] - hh) // 2, (bl.shape[1] - ww) // 2
        big[oy:oy + hh, ox:ox + ww] = lay
        from core import over
        lay = over(big, bl)
    m = cv2.getRotationMatrix2D((lay.shape[1] / 2, lay.shape[0] / 2), rot, 1.0)
    lay = cv2.warpAffine(lay, m, (lay.shape[1], lay.shape[0]), flags=cv2.INTER_LINEAR)
    # distress
    n = cv2.resize(fbm(lay.shape[0] // 2 + 2, lay.shape[1] // 2 + 2, scale=6, octaves=3, seed=3), (lay.shape[1], lay.shape[0]))
    lay = lay * (0.55 + 0.6 * smoothstep(0.25, 0.6, n))[..., None]

    def draw(frame, t, u):
        if t < t_in:
            return
        k = sstep(t_in, t_in + 0.12, t)
        s = 1.0 + 0.35 * (1 - ease_out(sstep(t_in, t_in + 0.2, t)))
        L = cv2.resize(lay, None, fx=s, fy=s) if s > 1.001 else lay
        paste(frame, L, x, y, a=0.85 * k)
    return draw


def big_number(dur, value, prefix="$", suffix="", decimals=1, label="", sub="", t0=0.4, t1=2.6, fname="sans_k",
               color="#ffb45c", label_color=PAPER, unit_text="", bg="dark", size=230, label_y=720, extra=None):
    blocks = []
    if label:
        blocks.append(Block(label, "sans", 44, label_color, W / 2, label_y, t_in=t1 - 0.4, fade=0.8, tracking=0.06))
    if sub:
        blocks.append(Block(sub, "sans_r", 30, "#c0d0cc", W / 2, 960, t_in=t1, fade=0.8, tracking=0.04))
    cache = {}

    def num(frame, t, u):
        p = ease_out(sstep(t0, t1, t))
        v = value * p
        txt = prefix + (("{:,.%df}" % decimals).format(v)) + suffix
        a = sstep(t0 - 0.2, t0 + 0.4, t)
        lay = cache.get(txt)
        if lay is None:
            lay = text_layer(txt, fname, size, color, glow="#ff6a00", glow_a=0.35)
            if len(cache) > 400:
                cache.clear()
            cache[txt] = lay
        paste(frame, lay, W / 2, 470, a=a)
        if unit_text:
            ul = cache.get("__u")
            if ul is None:
                ul = text_layer(unit_text, fname, int(size * 0.42), color)
                cache["__u"] = ul
            paste(frame, ul, W / 2, 470 + size * 0.72, a=sstep(t1 - 0.3, t1 + 0.3, t))
    return TextScene(blocks, dur, bg=bg, embers=False, drift=0.03, extra=[num] + list(extra or []))


# ----------------------------------------------------------------------------- maps

@lru_cache(maxsize=1)
def land_polys():
    p = os.path.join(ROOT, "dl", "geo", "ne_50m_land.geojson")
    d = json.load(open(p))
    polys = []
    for f in d["features"]:
        g = f["geometry"]
        if g["type"] == "Polygon":
            polys.append(g["coordinates"])
        else:
            polys.extend(g["coordinates"])
    return polys


def map_scene(dur, lon0, lon1, lat0, lat1, labels=(), route=None, route_t=(1.0, 5.0), cam=None, seed=0, title=None,
              ship=False, pins=()):
    """Antique parchment map. labels: (text, lon, lat, size, kind)."""
    def proj(lon, lat):
        x = (lon - lon0) / (lon1 - lon0) * OW
        # mercator y
        def my(la):
            return math.log(math.tan(math.pi / 4 + math.radians(la) / 2))
        y = (my(lat1) - my(lat)) / (my(lat1) - my(lat0)) * OH
        return x, y

    def build(ctx):
        sea = paper_texture(seed, "#d6c7a2", 0.6).copy()
        ctx.bg = sea
        land = Canvas()
        coast = Canvas()
        for poly in land_polys():
            ring = poly[0]
            lons = [p[0] for p in ring]
            lats = [p[1] for p in ring]
            if max(lons) < lon0 - 5 or min(lons) > lon1 + 5 or max(lats) < lat0 - 5 or min(lats) > lat1 + 5:
                continue
            pts = [proj(lo, la) for lo, la in ring]
            path = poly_path(pts)
            land.c.drawPath(path, paint("#efe4c8"))
            for k, (wd, a) in enumerate(((22, 0.10), (12, 0.14), (5, 0.25))):
                coast.c.drawPath(path, paint("#6a5a3a", a, stroke=wd, blur=2 if k < 2 else 0))
            coast.c.drawPath(path, paint("#3a2a14", 0.9, stroke=2.2))
        ctx.flush()
        cl = coast.rgba()
        comp(ctx.bg, cl)
        ll = land.rgba()
        tex = paper_texture(seed + 1, "#efe2c2", 0.0)
        a = ll[..., 3:4]
        ctx.bg[:] = ctx.bg * (1 - a) + tex * a
        line = Canvas()
        line.c.drawPath(poly_path([(0, 0)]), paint("#000"))
        for lo in range(int(lon0) // 5 * 5, int(lon1) + 5, 5):
            pts = [proj(lo, la) for la in np.linspace(lat0 - 2, lat1 + 2, 30)]
            line.line(pts, "#6a5a3a", 1.2, a=0.35)
        for la in range(int(lat0) // 5 * 5, int(lat1) + 5, 5):
            pts = [proj(lo, la) for lo in np.linspace(lon0 - 2, lon1 + 2, 60)]
            line.line(pts, "#6a5a3a", 1.2, a=0.35)
        comp(ctx.bg, line.rgba())
        # outline coast once more over the land fill
        comp(ctx.bg, coast.rgba() * np.array([1, 1, 1, 1], np.float32) * 0.6)
        # labels
        for (txt, lo, la, size, kind) in labels:
            x, y = proj(lo, la)
            fname = {"sc": "fell_sc", "it": "fell_it", "rm": "fell"}.get(kind, "fell_sc")
            lay = text_layer(txt, fname, size, "#3a2a14", tracking=0.25 if kind == "sc" else 0.02)
            paste(ctx.bg, lay, x, y)
        for (lo, la) in pins:
            x, y = proj(lo, la)
            pc = Canvas(60, 60)
            pc.circle(30, 30, 9, BLOOD)
            pc.circle(30, 30, 4, "#f0e0c0")
            paste(ctx.bg, pc.rgba(), x, y)
        compass(ctx.bg, OW - 330, OH - 300, 120)
        if route:
            pts = [proj(lo, la) for lo, la in route]
            # densify along a gentle arc
            P = np.array(pts, np.float64)
            seg = np.cumsum(np.r_[0, np.sqrt(((P[1:] - P[:-1]) ** 2).sum(1))])
            L = seg[-1]
            dense = np.array([np.interp(np.linspace(0, L, 400), seg, P[:, k]) for k in range(2)]).T

            def draw_route(buf, t):
                p = ease(sstep(route_t[0], route_t[1], t))
                n = int(len(dense) * p)
                for i in range(0, n - 1, 1):
                    if (i // 6) % 2 == 0:
                        x0, y0 = dense[i]
                        x1, y1 = dense[i + 1]
                        cv2.line(buf, (int(x0 * 4), int(y0 * 4)), (int(x1 * 4), int(y1 * 4)),
                                 tuple(float(c) for c in rgb(BLOOD)), 4, cv2.LINE_AA, shift=2)
                if ship and n > 2:
                    x, y = dense[min(n, len(dense) - 1)]
                    add_spot(buf, x, y, 7, (0.3, 0.05, 0.02), -0.0)
                    pts_ = np.array([(x - 18, y), (x + 18, y), (x + 12, y + 8), (x - 12, y + 8)], np.float32)
                    from items import silhouette
                    silhouette(buf, pts_, rgb("#2a1a0a"))
                    silhouette(buf, np.array([(x - 2, y - 26), (x + 2, y - 26), (x + 2, y), (x - 2, y)], np.float32), rgb("#2a1a0a"))
                    silhouette(buf, np.array([(x + 2, y - 24), (x + 16, y - 6), (x + 2, y - 4)], np.float32), rgb("#5a4a2a"))
            ctx.dyn.append(draw_route)
        if title:
            lay = text_layer(title, "fell_it", 54, "#3a2a14")
            paste(ctx.bg, lay, 330, 150)
    return Painted(build, dur=dur, cam=cam or Camera(1.0, 1.1, (0.5, 0.5), (0.5, 0.5)))


def compass(buf, x, y, r):
    c = Canvas(int(r * 2.6), int(r * 2.6))
    cx = cy = r * 1.3
    for k in range(16):
        a = k / 16 * 2 * math.pi
        L = r if k % 4 == 0 else (r * 0.6 if k % 2 == 0 else r * 0.38)
        w = r * (0.13 if k % 4 == 0 else 0.09)
        tip = (cx + math.sin(a) * L, cy - math.cos(a) * L)
        l = (cx + math.sin(a - math.pi / 2) * w, cy - math.cos(a - math.pi / 2) * w)
        rr = (cx + math.sin(a + math.pi / 2) * w, cy - math.cos(a + math.pi / 2) * w)
        c.poly([tip, l, (cx, cy)], "#3a2a14", 0.85)
        c.poly([tip, rr, (cx, cy)], "#8a7a5a", 0.85)
    c.c.drawCircle(cx, cy, r * 0.72, paint("#3a2a14", 0.6, stroke=1.5))
    c.c.drawCircle(cx, cy, r * 0.78, paint("#3a2a14", 0.4, stroke=1))
    lay = c.rgba()
    nl = text_layer("N", "fell", int(r * 0.4), "#3a2a14")
    comp_layer = lay
    paste(buf, comp_layer, x, y)
    paste(buf, nl, x, y - r * 1.25)


# ----------------------------------------------------------------------------- manuscript

LATIN = ("et lux in tenebris lucet et tenebrae eam non conprehenderunt fuit homo missus a Deo cui nomen erat "
         "Iohannes hic venit in testimonium ut testimonium perhiberet de lumine ut omnes crederent per illum "
         "non erat ille lux sed ut testimonium perhiberet de lumine erat lux vera quae inluminat omnem hominem "
         "venientem in mundum in mundo erat et mundus per ipsum factus est et mundus eum non cognovit")


def manuscript(dur, seed=0):
    def build(ctx):
        ctx.bg = paper_texture(seed + 2, "#e2d2a8", 0.75).copy()
        cv = ctx.cv
        x0, x1 = 420, OW - 380
        y = 210
        words = LATIN.split()
        f = font("black", 50)
        line, li = "", 0
        lines = []
        wi = 0
        while wi < len(words) * 3 and len(lines) < 17:
            w_ = words[wi % len(words)]
            t = (line + " " + w_).strip()
            limit = (x1 - x0) - (330 if len(lines) < 6 else 0)
            if f.getlength(t) > limit:
                lines.append(line)
                line = w_
            else:
                line = t
            wi += 1
        ctx.flush()
        for i, l in enumerate(lines):
            lx = x0 + (330 if i < 6 else 0)
            ly = y + i * 58
            cv2.line(ctx.bg, (x0 - 10, int(ly + 34)), (x1 + 10, int(ly + 34)), tuple(float(c) * 0.86 for c in rgb("#e2d2a8")), 1)
            lay = text_layer(l, "black", 50, "#2a1a10")
            paste(ctx.bg, lay, lx - 40, ly - 6, anchor="lt")
        # illuminated initial
        box = Canvas(320, 340)
        box.rect(10, 10, 310, 330, "#7a1a10", r=6)
        box.rect(24, 24, 296, 316, "#1c3a6a", r=4)
        for k in range(10):
            a = k / 10 * 2 * math.pi
            box.circle(160 + math.cos(a) * 110, 170 + math.sin(a) * 120, 10, "#d4a237")
        paste(ctx.bg, box.rgba(), x0 - 20, y - 40, anchor="lt")
        init = text_layer("E", "black", 270, "#e9c25a", glow=None)
        paste(ctx.bg, init, x0 + 140, y + 130)
        # margin note
        note = text_layer("Samain", "fell_it", 44, "#7a1a10")
        paste(ctx.bg, note, OW - 250, 470)
        ctx.light("candle", lambda t: flicker(t, 4, 0.12, 0.9)).glow(OW * 0.75, OH * 0.95, 1200, "#ff9a3a", 0.30)
    return Painted(build, dur=dur, cam=Camera(1.12, 1.02, (0.35, 0.35), (0.55, 0.5)))

