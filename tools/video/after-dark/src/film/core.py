"""Drawing and compositing toolkit for the Halloween documentary.

Everything is drawn from scratch: Skia for anti-aliased vector shapes, PIL (with
RAQM shaping) for type, numpy/OpenCV for per-frame light, fire, fog and camera.
Frames are float32 RGB in [0, 1] (display-referred), H x W x 3.
"""
import math
import os
from functools import lru_cache

import cv2
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFont

cv2.setNumThreads(1)          # each render worker is single-threaded; we run one worker per core

W, H = 1920, 1080
OS = 1.15                     # backgrounds are painted larger than the frame so the camera can move
OW, OH = 2208, 1242
FPS = 24

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONT_DIR = os.path.join(ROOT, "doc", "fonts")
FONTS = {
    "black": "UnifrakturMaguntia.ttf",
    "type": "SpecialElite.ttf",
    "fell": "IMFeENrm28P.ttf",
    "fell_it": "IMFeENit28P.ttf",
    "fell_sc": "IMFeENsc28P.ttf",
    "old": "OldStandard-Regular.ttf",
    "old_b": "OldStandard-Bold.ttf",
    "sans": "Inter-SemiBold.otf",
    "sans_r": "Inter-Regular.otf",
    "sans_b": "Inter-Bold.otf",
    "sans_x": "Inter-ExtraBold.otf",
    "sans_k": "Inter-Black.otf",
}

# palette
NIGHT = "#0b1519"
GHOST = "#8fffc4"
AMBER = "#ffb45c"
EMBER = "#ff6a1a"
PAPER = "#ece2cb"
INK = "#2a2017"
BLOOD = "#9a1d12"
MOON = "#d8ece6"


# ----------------------------------------------------------------------------- colour / math

def rgb(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    return np.asarray(c, np.float32)


def mix(a, b, t):
    return rgb(a) * (1 - t) + rgb(b) * t


def c4(c, a=1.0):
    r, g, b = [float(x) for x in rgb(c)]
    return skia.Color4f(r, g, b, float(a))


def clamp01(x):
    return np.clip(x, 0.0, 1.0)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, np.float32) - e0) / (e1 - e0 + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def sstep(e0, e1, x):
    """scalar smoothstep"""
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0 + 1e-9)))
    return t * t * (3 - 2 * t)


def ease(t):
    t = min(1.0, max(0.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


class Noise1:
    """Smooth deterministic 1-D noise in [-1, 1] for flicker, sway and wobble."""

    def __init__(self, seed=0, octaves=4):
        r = np.random.default_rng(seed)
        self.v = [r.uniform(-1, 1, 4096).astype(np.float32) for _ in range(octaves)]
        self.oct = octaves

    def __call__(self, t, freq=1.0):
        s, amp, tot = 0.0, 1.0, 0.0
        f = freq
        for o in range(self.oct):
            x = t * f
            i = math.floor(x)
            fr = x - i
            fr = fr * fr * (3 - 2 * fr)
            v = self.v[o]
            a, b = v[i % 4096], v[(i + 1) % 4096]
            s += (a + (b - a) * fr) * amp
            tot += amp
            amp *= 0.5
            f *= 2.03
        return s / tot


def flicker(t, seed=0, amt=0.15, speed=1.0):
    n = _noise_for(seed)
    v = n(t, 3.1 * speed) * 0.75 + n(t + 11.0, 9.7 * speed) * 0.25
    return 1.0 + amt * v


@lru_cache(maxsize=64)
def _noise_for(seed):
    return Noise1(seed)


# ----------------------------------------------------------------------------- noise fields

def fbm(h, w, scale=200.0, octaves=5, persist=0.5, seed=0):
    """Value-noise fBm in [0,1]. scale = feature size of the first octave in pixels."""
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot, s = 1.0, 0.0, float(scale)
    for _ in range(octaves):
        gh, gw = max(2, int(h / s) + 3), max(2, int(w / s) + 3)
        g = r.random((gh, gw)).astype(np.float32)
        up = cv2.resize(g, (int(gw * s), int(gh * s)), interpolation=cv2.INTER_CUBIC)
        oy, ox = r.integers(0, max(1, up.shape[0] - h)), r.integers(0, max(1, up.shape[1] - w))
        out += up[oy:oy + h, ox:ox + w] * amp
        tot += amp
        amp *= persist
        s /= 2.0
        if s < 1.5:
            break
    out /= tot
    lo, hi = np.percentile(out, 0.5), np.percentile(out, 99.5)
    return clamp01((out - lo) / (hi - lo + 1e-6))


def tileable_x(n, overlap):
    """Make a noise field wrap horizontally by cross-fading its ends."""
    h, w = n.shape[:2]
    o = overlap
    a = np.linspace(0, 1, o, dtype=np.float32)
    if n.ndim == 3:
        a = a[None, :, None]
    else:
        a = a[None, :]
    out = n[:, : w - o].copy()
    out[:, :o] = n[:, w - o:] * (1 - a) + n[:, :o] * a
    return out


def noise1d(n, scale, octaves=4, seed=0, persist=0.5):
    r = np.random.default_rng(seed)
    out = np.zeros(n, np.float32)
    amp, tot, s = 1.0, 0.0, float(scale)
    x = np.arange(n, dtype=np.float32)
    for _ in range(octaves):
        k = int(n / s) + 4
        g = r.uniform(-1, 1, k).astype(np.float32)
        xs = np.arange(k, dtype=np.float32) * s
        # cubic-ish interpolation via smooth weights
        i = np.floor(x / s).astype(int)
        f = x / s - i
        f = f * f * (3 - 2 * f)
        out += (g[i] * (1 - f) + g[np.minimum(i + 1, k - 1)] * f) * amp
        tot += amp
        amp *= persist
        s /= 2.0
        if s < 1:
            break
    return out / tot


# ----------------------------------------------------------------------------- skia canvas

class Canvas:
    """A Skia raster canvas; .rgba() returns premultiplied float32 RGBA."""

    def __init__(self, w=OW, h=OH, bg=None):
        info = skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType)
        self.surface = skia.Surface.MakeRaster(info)
        self.c = self.surface.getCanvas()
        self.w, self.h = w, h
        if bg is not None:
            self.c.clear(c4(bg))
        else:
            self.c.clear(skia.Color4f(0, 0, 0, 0))

    def rgba(self):
        a = self.surface.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType,
                                                     alphaType=skia.AlphaType.kPremul_AlphaType)
        return a.astype(np.float32) * (1.0 / 255.0)

    def rgb(self):
        return self.rgba()[..., :3].copy()

    def alpha(self):
        return self.rgba()[..., 3].copy()

    # shapes -------------------------------------------------------------
    def path(self, path, paint):
        self.c.drawPath(path, paint)

    def poly(self, pts, color, a=1.0, blur=0, mode=None, closed=True, smooth=False, shader=None):
        p = smooth_path(pts, closed) if smooth else poly_path(pts, closed)
        self.c.drawPath(p, paint(color, a, blur=blur, mode=mode, shader=shader))
        return p

    def circle(self, x, y, r, color, a=1.0, blur=0, mode=None, shader=None):
        self.c.drawCircle(x, y, r, paint(color, a, blur=blur, mode=mode, shader=shader))

    def ellipse(self, x, y, rx, ry, color, a=1.0, blur=0, mode=None, shader=None):
        self.c.drawOval(skia.Rect(x - rx, y - ry, x + rx, y + ry), paint(color, a, blur=blur, mode=mode, shader=shader))

    def rect(self, x0, y0, x1, y1, color, a=1.0, blur=0, mode=None, shader=None, r=0):
        p = paint(color, a, blur=blur, mode=mode, shader=shader)
        if r:
            self.c.drawRoundRect(skia.Rect(x0, y0, x1, y1), r, r, p)
        else:
            self.c.drawRect(skia.Rect(x0, y0, x1, y1), p)

    def line(self, pts, color, width, a=1.0, blur=0, mode=None, cap=skia.Paint.kRound_Cap):
        p = paint(color, a, blur=blur, mode=mode, stroke=width, cap=cap)
        self.c.drawPath(poly_path(pts, False), p)

    def glow(self, x, y, r, color, a=1.0, mode=skia.BlendMode.kPlus, falloff=(1.0, 0.45, 0.14, 0.0)):
        cols = [c4(color, a * f) for f in falloff]
        pos = list(np.linspace(0, 1, len(falloff)))
        sh = skia.GradientShader.MakeRadial(skia.Point(x, y), r, cols, pos)
        self.c.drawCircle(x, y, r, paint(None, shader=sh, mode=mode))

    def image(self, arr_rgba_premul, x=0, y=0, mode=None, a=1.0):
        img = np_to_skimage(arr_rgba_premul)
        p = skia.Paint(AntiAlias=True)
        if mode is not None:
            p.setBlendMode(mode)
        if a < 1.0:
            p.setAlphaf(a)
        self.c.drawImage(img, x, y, skia.SamplingOptions(skia.FilterMode.kLinear), p)


def np_to_skimage(arr):
    a = np.ascontiguousarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))
    return skia.Image.fromarray(a, colorType=skia.ColorType.kRGBA_8888_ColorType,
                                alphaType=skia.AlphaType.kPremul_AlphaType)


def paint(color=None, a=1.0, blur=0, mode=None, stroke=0, shader=None, cap=skia.Paint.kRound_Cap,
          join=skia.Paint.kRound_Join):
    p = skia.Paint(AntiAlias=True)
    if color is not None:
        p.setColor4f(c4(color, a))
    elif shader is not None and a < 1.0:
        p.setAlphaf(a)
    if shader is not None:
        p.setShader(shader)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if mode is not None:
        p.setBlendMode(mode)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(cap)
        p.setStrokeJoin(join)
    return p


def poly_path(pts, closed=True):
    p = skia.Path()
    pts = [(float(x), float(y)) for x, y in pts]
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if closed:
        p.close()
    return p


def smooth_path(pts, closed=True, k=1.0 / 6.0):
    """Catmull-Rom through the points, as cubic Beziers."""
    pts = [np.array(q, np.float64) for q in pts]
    n = len(pts)
    p = skia.Path()
    p.moveTo(*pts[0])
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else pts[(i + 1) % n]
        c1 = p1 + (p2 - p0) * k
        c2 = p2 - (p3 - p1) * k
        p.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if closed:
        p.close()
    return p


def lin(p0, p1, colors, pos=None):
    cols = [c4(c[0], c[1]) if isinstance(c, tuple) else c4(c) for c in colors]
    return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], cols, pos)


def rad(center, r, colors, pos=None):
    cols = [c4(c[0], c[1]) if isinstance(c, tuple) else c4(c) for c in colors]
    return skia.GradientShader.MakeRadial(skia.Point(*center), r, cols, pos)


ADD = skia.BlendMode.kPlus
SCREEN = skia.BlendMode.kScreen
MULT = skia.BlendMode.kMultiply
ERASE = skia.BlendMode.kDstOut
SRCATOP = skia.BlendMode.kSrcATop


# ----------------------------------------------------------------------------- type (PIL + RAQM)

@lru_cache(maxsize=128)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS[name]), int(size), layout_engine=ImageFont.Layout.RAQM)


def text_mask(text, fname, size, tracking=0.0, pad=None, line_gap=1.18, align="center", max_w=None):
    """Render text (may contain \\n) into an alpha mask. Returns (mask float32, (w,h), baseline offsets)."""
    f = font(fname, size)
    lines = text.split("\n")
    if max_w:
        lines = wrap_lines(lines, f, max_w, tracking, size)
    asc, desc = f.getmetrics()
    lh = int(size * line_gap)
    widths = [measure(l, f, tracking, size) for l in lines]
    tw = int(max(widths) + size * 0.6)
    th = int(lh * (len(lines) - 1) + asc + desc + size * 0.4)
    pad = int(size * 0.3) if pad is None else pad
    im = Image.new("L", (tw + 2 * pad, th + 2 * pad), 0)
    d = ImageDraw.Draw(im)
    for i, (l, lw) in enumerate(zip(lines, widths)):
        if align == "center":
            x0 = pad + (tw - lw) / 2
        elif align == "right":
            x0 = pad + tw - lw
        else:
            x0 = pad
        y0 = pad + i * lh
        if tracking:
            x = x0
            for ch in l:
                d.text((x, y0), ch, font=f, fill=255)
                x += f.getlength(ch) + tracking * size
        else:
            d.text((x0, y0), l, font=f, fill=255)
    m = np.asarray(im, np.float32) / 255.0
    ys, xs = np.nonzero(m > 0.003)
    if len(ys):
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        m = m[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2]
    return m


def measure(line, f, tracking, size):
    if tracking:
        return sum(f.getlength(ch) + tracking * size for ch in line) - tracking * size
    return f.getlength(line)


def wrap_lines(lines, f, max_w, tracking, size):
    out = []
    for l in lines:
        words = l.split(" ")
        cur = ""
        for w_ in words:
            t = (cur + " " + w_).strip()
            if measure(t, f, tracking, size) > max_w and cur:
                out.append(cur)
                cur = w_
            else:
                cur = t
        out.append(cur)
    return out


def glyph_layer(mask, color, a=1.0):
    """Mask -> premultiplied RGBA layer."""
    col = rgb(color)
    out = np.zeros(mask.shape + (4,), np.float32)
    out[..., 3] = mask * a
    out[..., :3] = mask[..., None] * col[None, None, :] * a
    return out


def blur(img, sigma):
    if sigma <= 0:
        return img
    k = int(sigma * 3) * 2 + 1
    return cv2.GaussianBlur(img, (k, k), sigma, borderType=cv2.BORDER_CONSTANT)


def text_layer(text, fname, size, color, a=1.0, tracking=0.0, glow=None, glow_sigma=None, glow_a=0.6,
               shadow=0.0, max_w=None, align="center", line_gap=1.18):
    """Premultiplied RGBA layer with optional coloured glow and dark shadow behind the text."""
    m = text_mask(text, fname, size, tracking=tracking, max_w=max_w, align=align, line_gap=line_gap)
    padn = int(size * 0.9)
    m = np.pad(m, padn)
    lay = np.zeros(m.shape + (4,), np.float32)
    if shadow:
        sh = blur(m, size * 0.10) * shadow
        lay[..., 3] = sh
    if glow is not None:
        gs = glow_sigma or size * 0.18
        g = clamp01(blur(m, gs) * 1.6) * glow_a
        gc = rgb(glow)
        lay[..., :3] += g[..., None] * gc
        lay[..., 3] = clamp01(lay[..., 3] + g * 0.0)
    fg = glyph_layer(m, color, a)
    lay = over(fg, lay)
    return lay


def over(fg, bg):
    """Premultiplied 'over' of two RGBA layers of the same size."""
    out = fg.copy()
    out[..., :3] += bg[..., :3] * (1 - fg[..., 3:4])
    out[..., 3] = fg[..., 3] + bg[..., 3] * (1 - fg[..., 3])
    return out


def paste(frame, layer, x, y, a=1.0, anchor="mm", add=False):
    """Composite a premultiplied RGBA layer onto an RGB frame at (x, y) with anchor (mm, lt, lm, ...)."""
    lh, lw = layer.shape[:2]
    if anchor[0] == "m":
        x0 = x - lw / 2
    elif anchor[0] == "r":
        x0 = x - lw
    else:
        x0 = x
    if anchor[1] == "m":
        y0 = y - lh / 2
    elif anchor[1] == "b":
        y0 = y - lh
    else:
        y0 = y
    x0, y0 = int(round(x0)), int(round(y0))
    fh, fw = frame.shape[:2]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    dx1, dy1 = min(fw, x0 + lw), min(fh, y0 + lh)
    if dx1 <= dx0 or dy1 <= dy0 or a <= 0:
        return frame
    L = layer[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)]
    F = frame[dy0:dy1, dx0:dx1]
    if add:
        F += L[..., :3] * a
    else:
        F *= (1 - L[..., 3:4] * a)
        F += L[..., :3] * a
    return frame


# ----------------------------------------------------------------------------- light, glow, particles

@lru_cache(maxsize=256)
def gauss_sprite(sigma):
    r = int(math.ceil(sigma * 3))
    x = np.arange(-r, r + 1, dtype=np.float32)
    g = np.exp(-(x * x) / (2 * sigma * sigma))
    return np.outer(g, g).astype(np.float32)


def add_spot(frame, x, y, sigma, color, k=1.0):
    """Additive gaussian splat (fast; for embers, stars, wisps)."""
    s = gauss_sprite(round(sigma * 4) / 4 if sigma > 1 else max(0.5, round(sigma * 8) / 8))
    r = s.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    fh, fw = frame.shape[:2]
    x0, y0, x1, y1 = xi - r, yi - r, xi + r + 1, yi + r + 1
    if x1 <= 0 or y1 <= 0 or x0 >= fw or y0 >= fh:
        return
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1, sy1 = s.shape[1] - max(0, x1 - fw), s.shape[0] - max(0, y1 - fh)
    frame[max(0, y0):min(fh, y1), max(0, x0):min(fw, x1)] += s[sy0:sy1, sx0:sx1, None] * (rgb(color) * k)[None, None, :]


def radial(h, w, cx, cy, r, power=2.0):
    """1 at centre falling to 0 at radius r (smooth)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    return clamp01(1 - d) ** power


def light_map(h, w, cx, cy, r, power=1.6, falloff="smooth"):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)
    return (1.0 / (1.0 + d2 * 6.0)) * clamp01(1 - np.sqrt(d2) * 0.35) ** power


@lru_cache(maxsize=4)
def vignette(strength=0.55, power=2.4):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    v = 1 - strength * d ** power
    return v[..., None].astype(np.float32)


class Grain:
    def __init__(self, n=12, seed=7):
        r = np.random.default_rng(seed)
        self.frames = []
        for _ in range(n):
            g = r.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
            g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
            self.frames.append((g * 40).clip(-127, 127).astype(np.int8))

    def apply(self, frame, i, amount=0.010):
        g = self.frames[i % len(self.frames)].astype(np.float32) * (amount / 40.0)
        frame += g[..., None]
        return frame


# ----------------------------------------------------------------------------- fog

class Fog:
    """Two scrolling fBm sheets, denser toward the ground."""

    def __init__(self, seed=1, scale=260, color="#8fb3ad", density=0.22, top=0.35, bottom=1.0, speed=18.0,
                 w=W, h=H):
        self.w, self.h = w, h
        hh = h // 2
        ww = w // 2
        self.sheets = []
        for k in range(2):
            n = fbm(hh, ww + 260, scale=scale / 2 * (1 + 0.6 * k), octaves=5, seed=seed + k * 17)
            n = tileable_x(n, 260)
            n = smoothstep(0.30, 0.95, n)
            self.sheets.append(n.astype(np.float32))
        prof = smoothstep(top, bottom, np.linspace(0, 1, h, dtype=np.float32))
        self.prof = prof[:, None]
        self.color = rgb(color)
        self.density = density
        self.speed = speed

    def layer(self, t, density=None):
        hh, ww = self.sheets[0].shape
        acc = np.zeros((hh, ww), np.float32)
        for k, s in enumerate(self.sheets):
            off = int(t * self.speed * (0.5 + 0.7 * k) / 2) % ww
            acc += np.roll(s, -off, axis=1) * (0.6 if k == 0 else 0.4)
        f = cv2.resize(acc, (self.w, self.h), interpolation=cv2.INTER_LINEAR)
        return f * self.prof * (self.density if density is None else density)

    def apply(self, frame, t, density=None, mode="screen"):
        f = self.layer(t, density)[..., None]
        if mode == "screen":
            frame[:] = 1 - (1 - frame) * (1 - f * self.color)
        else:
            frame += f * self.color
        return frame


# ----------------------------------------------------------------------------- fire

FIRE_LUT = None


def fire_lut():
    global FIRE_LUT
    if FIRE_LUT is None:
        stops = [(0.0, (0, 0, 0)), (0.18, (0.35, 0.02, 0.0)), (0.38, (0.85, 0.18, 0.02)), (0.58, (1.0, 0.45, 0.08)),
                 (0.78, (1.0, 0.75, 0.28)), (1.0, (1.0, 0.97, 0.85))]
        xs = np.linspace(0, 1, 256)
        lut = np.zeros((256, 3), np.float32)
        for c in range(3):
            lut[:, c] = np.interp(xs, [s[0] for s in stops], [s[1][c] for s in stops])
        FIRE_LUT = lut
    return FIRE_LUT


class Flame:
    """Noise-advected flame sprite. render(t) -> additive RGB array (h, w, 3)."""

    def __init__(self, w, h, seed=0, tongues=1.0, speed=1.0, width=0.62, power=1.35, wobble=0.35):
        self.w, self.h = w, h
        r = np.random.default_rng(seed)
        nh = 512
        self.n1 = tileable_y(fbm(nh + 128, 128, scale=26, octaves=4, seed=seed), 128)
        self.n2 = tileable_y(fbm(nh + 128, 128, scale=12, octaves=3, seed=seed + 5), 128)
        self.nh = nh
        v = np.linspace(1, 0, h, dtype=np.float32)[:, None]       # 0 at base, 1 at top
        u = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
        self.u, self.v = u, v
        self.speed = speed
        self.width = width
        self.power = power
        self.wobble = wobble
        self.tongues = tongues

    def render(self, t, intensity=1.0):
        h, w = self.h, self.w
        sp = self.speed
        o1 = int(t * 260 * sp) % self.nh
        o2 = int(t * 420 * sp) % self.nh
        a = np.roll(self.n1, o1, axis=0)[: self.nh]
        b = np.roll(self.n2, o2, axis=0)[: self.nh]
        a = cv2.resize(a[: int(self.nh * 0.55)], (w, h), interpolation=cv2.INTER_LINEAR)
        b = cv2.resize(b[: int(self.nh * 0.55)], (w, h), interpolation=cv2.INTER_LINEAR)
        u, v = self.u, self.v
        disp = (a - 0.5) * self.wobble * (0.25 + v * 1.4)
        width = self.width * (1 - v) ** 0.55 + 0.02
        d = np.abs(u + disp) / width
        core = clamp01(1 - d)
        heat = core ** 1.2 * (1 - v) ** self.power
        heat *= (0.55 + 0.9 * b * self.tongues)
        heat = clamp01(heat * 1.6 * intensity)
        idx = (heat * 255).astype(np.uint8)
        return fire_lut()[idx]


def tileable_y(n, overlap):
    return tileable_x(n.T, overlap).T.copy()


class Embers:
    def __init__(self, n, x0, x1, y0, rise=260.0, spread=60.0, life=(2.0, 4.5), size=(1.0, 2.2), seed=3,
                 color=(1.0, 0.55, 0.15)):
        r = np.random.default_rng(seed)
        self.n = n
        self.x = r.uniform(x0, x1, n)
        self.y0 = y0
        self.vy = r.uniform(0.6, 1.2, n) * rise
        self.life = r.uniform(*life, n)
        self.off = r.uniform(0, 10, n)
        self.size = r.uniform(*size, n)
        self.ph = r.uniform(0, 6.28, n)
        self.spread = spread
        self.color = np.array(color, np.float32)

    def draw(self, frame, t, k=1.0, dx=0.0, dy=0.0):
        age = (t + self.off) % self.life
        f = age / self.life
        ys = self.y0 - self.vy * age + dy
        xs = self.x + np.sin(age * 2.1 + self.ph) * self.spread * f + dx + age * 12
        br = np.sin(np.pi * f) * (0.6 + 0.4 * np.sin(t * 13 + self.ph)) * k
        for i in range(self.n):
            if br[i] > 0.02:
                add_spot(frame, xs[i], ys[i], self.size[i], self.color, br[i] * 1.4)


class Motes:
    """Dust drifting slowly in a light beam (or snow-like ash)."""

    def __init__(self, n, x0, x1, y0, y1, seed=5, color=(1, 0.9, 0.75), size=(0.7, 1.6), drift=(6, 12)):
        r = np.random.default_rng(seed)
        self.n = n
        self.x = r.uniform(x0, x1, n)
        self.y = r.uniform(y0, y1, n)
        self.vx = r.uniform(-drift[0], drift[0], n)
        self.vy = r.uniform(-drift[1], drift[1] * 0.5, n)
        self.size = r.uniform(*size, n)
        self.ph = r.uniform(0, 6.28, n)
        self.box = (x0, x1, y0, y1)
        self.color = np.array(color, np.float32)

    def draw(self, frame, t, k=1.0, mask=None):
        x0, x1, y0, y1 = self.box
        xs = x0 + (self.x - x0 + self.vx * t + 8 * np.sin(t * 0.4 + self.ph)) % (x1 - x0)
        ys = y0 + (self.y - y0 + self.vy * t) % (y1 - y0)
        br = (0.5 + 0.5 * np.sin(t * 1.3 + self.ph * 3)) * k
        for i in range(self.n):
            kk = br[i]
            if mask is not None:
                xi, yi = int(xs[i]), int(ys[i])
                if 0 <= yi < mask.shape[0] and 0 <= xi < mask.shape[1]:
                    kk *= mask[yi, xi]
                else:
                    kk = 0
            if kk > 0.02:
                add_spot(frame, xs[i], ys[i], self.size[i], self.color, kk * 0.5)


# ----------------------------------------------------------------------------- camera

class Camera:
    """Moves over an OW x OH painting. zoom 1.0 shows the whole painting; up to OS without upsampling."""

    def __init__(self, z0=1.0, z1=1.08, c0=(0.5, 0.5), c1=(0.5, 0.5), rot0=0.0, rot1=0.0, ease_fn=ease,
                 shake=0.0, seed=0):
        self.z0, self.z1, self.c0, self.c1 = z0, z1, c0, c1
        self.rot0, self.rot1 = rot0, rot1
        self.ease = ease_fn
        self.shake = shake
        self.n = Noise1(seed + 101)

    def matrix(self, u, t=0.0, depth=1.0, src_w=OW, src_h=OH):
        e = self.ease(u)
        z = lerp(self.z0, self.z1, e)
        z = 1 + (z - 1) * depth
        cx = lerp(self.c0[0], self.c1[0], e)
        cy = lerp(self.c0[1], self.c1[1], e)
        cx = 0.5 + (cx - 0.5) * depth
        cy = 0.5 + (cy - 0.5) * depth
        s = (src_w / W) / z
        # keep the view inside the painting
        half_w, half_h = W * s / 2, H * s / 2
        px = min(max(cx * src_w, half_w), src_w - half_w)
        py = min(max(cy * src_h, half_h), src_h - half_h)
        if self.shake:
            px += self.n(t, 0.6) * self.shake * depth
            py += self.n(t + 50, 0.5) * self.shake * depth
        rot = math.radians(lerp(self.rot0, self.rot1, e))
        cs, sn = math.cos(rot) * s, math.sin(rot) * s
        # dst (x,y) -> src
        m = np.array([[cs, -sn, px - cs * W / 2 + sn * H / 2],
                      [sn, cs, py - sn * W / 2 - cs * H / 2]], np.float32)
        return m


def warp(img, m, interp=cv2.INTER_LINEAR):
    return cv2.warpAffine(img, m, (W, H), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)


def warp_pts(m, pts):
    """Map painting coordinates to frame coordinates for the given (dst->src) matrix."""
    A = np.vstack([m, [0, 0, 1]])
    inv = np.linalg.inv(A)
    p = np.asarray(pts, np.float64)
    q = (inv[:2, :2] @ p.T).T + inv[:2, 2]
    return q
