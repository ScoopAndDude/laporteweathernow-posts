#!/usr/bin/env python3
"""The Belle Gunness documentary for YouTube (Oct. 2026; Scoop: "lets make a whole documentary on belle",
"make it for youtube", 15 to 20 minutes, the same narrator as the shorts).

    python3 tools/video/belle-doc/doc.py stills OUTDIR [chapter ...]     one frame from each shot, as contact sheets
    python3 tools/video/belle-doc/doc.py render OUTDIR [chapter ...]     video segments (one per chapter), cached
    python3 tools/video/belle-doc/doc.py final OUTDIR                    soundtrack + segments -> the finished mp4
    python3 tools/video/belle-doc/doc.py srt OUTDIR                      captions file for YouTube
    python3 tools/video/belle-doc/doc.py lines                           writes lines.json for the voice job

1920x1080, 24 fps. The story is script.json: chapters of narration lines, each with the pictures to show.
The narrator (Kokoro-82M af_heart, like the shorts) is recorded by voice.py in GitHub Actions; each line's
length and word timings set the timing of everything else. The pictures are real: 1908 photos, postcards
and newspaper pages (public domain or CC BY, credited on screen), plus maps and title cards drawn here.
Music and sounds are written in code (music.py), so there's nothing for YouTube's Content ID to match.
"""
import functools
import hashlib
import json
import math
import os
import subprocess
import sys
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "images")
SHORT_IMG = os.path.normpath(os.path.join(HERE, "..", "belle-2026", "images"))
VOICE = os.path.join(HERE, "voice")
W, H, FPS = 1920, 1080, 24
SR = 48000
XFADE = 0.6          # seconds two shots overlap (dissolve)

INK = (34, 25, 18)
BONE = (240, 230, 212)
PAPER = (228, 211, 176)
BLOOD = (178, 30, 26)
NIGHT = (10, 9, 8)

# ------------------------------------------------------------------------------------------------ fonts
FONTS = {
    "fell": "fonts/IMFeENrm28P.ttf", "fell-it": "fonts/IMFeENit28P.ttf", "fell-sc": "fonts/IMFeENsc28P.ttf",
    "old": "fonts/OldStandard-Regular.ttf", "old-b": "fonts/OldStandard-Bold.ttf", "old-it": "fonts/OldStandard-Italic.ttf",
    "type": "fonts/SpecialElite-Regular.ttf",
    "lora": "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf",
    "lora-b": "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf",
    "lora-it": "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf",
    "inter": "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
    "inter-m": "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
    "inter-sb": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "inter-b": "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
}


@functools.lru_cache(maxsize=None)
def font(kind, size):
    path = FONTS[kind]
    f = ImageFont.truetype(path if path.startswith("/") else os.path.join(HERE, path), int(size))
    if kind == "lora-b":
        f.set_variation_by_name(b"Bold")
    elif kind in ("lora", "lora-it"):
        try:
            f.set_variation_by_name(b"Regular" if kind == "lora" else b"Italic")
        except Exception:
            pass
    return f


def text(s, kind, size, fill, tracking=0, stroke=0, stroke_fill=(0, 0, 0)):
    """One line of text as a tight RGBA image."""
    f = font(kind, size)
    pad = 10 + 2 * stroke
    if tracking:
        widths = [f.getlength(c) for c in s]
        w = int(sum(widths) + tracking * max(0, len(s) - 1)) + 2 * pad
    else:
        w = int(f.getlength(s)) + 2 * pad
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (max(1, w), asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tracking:
        x = pad
        for c, cw in zip(s, widths):
            d.text((x, pad), c, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
            x += cw + tracking
    else:
        d.text((pad, pad), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    box = img.getbbox()
    return img.crop(box) if box else img


def wrap(s, f, max_w):
    lines, cur = [], ""
    for word in s.split():
        t = (cur + " " + word).strip()
        if f.getlength(t) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def para(s, kind, size, fill, max_w, gap=1.3, align="left", justify=False):
    """A paragraph as an RGBA image (keeps line height steady; optional justification)."""
    f = font(kind, size)
    lines = []
    for block in s.split("\n"):
        lines += wrap(block, f, max_w) if block.strip() else [""]
    asc, desc = f.getmetrics()
    lh = int(size * gap)
    img = Image.new("RGBA", (int(max_w) + 20, lh * len(lines) + desc + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        y = 10 + i * lh
        if justify and i < len(lines) - 1 and " " in ln and lines[i + 1] != "":
            words = ln.split()
            total = sum(f.getlength(wd) for wd in words)
            space = (max_w - total) / (len(words) - 1)
            x = 10
            for wd in words:
                d.text((x, y), wd, font=f, fill=fill)
                x += f.getlength(wd) + space
            continue
        lw = f.getlength(ln)
        x = 10 + (max_w - lw) / 2 if align == "center" else 10 + (max_w - lw if align == "right" else 0)
        d.text((x, y), ln, font=f, fill=fill)
    box = img.getbbox()
    return img.crop((0, 0, img.width, box[3] + 4)) if box else img


def shadow(img, radius=18, alpha=150, offset=(0, 10)):
    """img with a soft drop shadow (returns a bigger RGBA and the offset of img inside it)."""
    pad = radius * 3
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    a = img.getchannel("A").point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 255))
    sh.putalpha(a)
    out.alpha_composite(sh, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(radius))
    out.alpha_composite(img, (pad, pad))
    return out, pad


def glow(img, color, radius=22, strength=0.8):
    pad = radius * 3
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    a = img.getchannel("A").point(lambda v: int(v * strength))
    g = Image.new("RGBA", img.size, tuple(color) + (255,))
    g.putalpha(a)
    out.alpha_composite(g, (pad, pad))
    out = out.filter(ImageFilter.GaussianBlur(radius))
    out.alpha_composite(img, (pad, pad))
    return out


def with_alpha(img, a):
    if a >= 0.999:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return img


def put(frame, img, x, y, alpha=1.0):
    """Paste an RGBA image onto the RGB frame at (x, y) with its alpha."""
    if alpha <= 0.003:
        return
    if alpha < 0.999:
        img = with_alpha(img, alpha)
    frame.paste(img, (int(round(x)), int(round(y))), img)


def put_c(frame, img, cx, cy, alpha=1.0):
    put(frame, img, cx - img.width / 2, cy - img.height / 2, alpha)


# ------------------------------------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3


def fade(t, start, dur):
    return ease((t - start) / dur) if dur > 0 else float(t >= start)


def lerp(a, b, k):
    return a + (b - a) * k


# ------------------------------------------------------------------------------------------------ pictures
MANIFEST = {}


def load_manifests():
    for d in (IMG, SHORT_IMG):
        p = os.path.join(d, "manifest.json")
        if os.path.exists(p):
            for x in json.load(open(p, encoding="utf-8")):
                MANIFEST.setdefault(x["file"], dict(x, _dir=d))
                for c in x.get("crops", []):
                    MANIFEST.setdefault(c["file"], dict(x, file=c["file"], _dir=d, crop_of=x["file"], crop_text=c.get("text", "")))


def img_path(name):
    for d in (IMG, SHORT_IMG):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(name)


def credit_for(name):
    m = MANIFEST.get(name)
    if not m:
        return ""
    lic = (m.get("license") or "").strip()
    low = lic.lower()
    if low.startswith(("public domain", "pd", "cc0", "no known", "no restrictions")):
        return ""
    import re
    who = re.sub(r"\s+from\s.*$", "", re.sub(r"(Unknown author)+", "", m.get("artist") or "")).strip()
    return f"Photo: {who} / {lic}" if who else f"Photo: {lic}"


@functools.lru_cache(maxsize=64)
def picture(name, tone="sepia", crop=None, max_side=2600):
    """A picture, toned like an old print. crop = (x0, y0, x1, y1) as fractions."""
    im = Image.open(img_path(name)).convert("RGB")
    if crop:
        x0, y0, x1, y1 = crop
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    if tone in ("sepia", "sepia-soft", "bw", "paper"):
        g = ImageOps.autocontrast(im.convert("L"), cutoff=0.6)
        if tone == "sepia-soft":
            g = ImageEnhance.Contrast(g).enhance(0.92)
        if tone == "bw":
            im = ImageOps.colorize(g, black=(14, 13, 12), mid=(118, 112, 104), white=(238, 234, 226))
        elif tone == "paper":
            im = ImageOps.colorize(g, black=(30, 24, 18), mid=(140, 122, 96), white=(236, 222, 192))
        else:
            im = ImageOps.colorize(g, black=(16, 12, 9), mid=(124, 99, 72), white=(242, 226, 194))
    elif tone == "warm":
        im = ImageEnhance.Color(im).enhance(0.55)
        arr = np.asarray(im, np.float32) * np.array([1.04, 0.98, 0.88], np.float32)
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    elif tone == "night":
        im = ImageEnhance.Color(im).enhance(0.3)
        im = ImageEnhance.Brightness(im).enhance(0.6)
        arr = np.asarray(im, np.float32) * np.array([0.72, 0.86, 1.08], np.float32)
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return im


class Pyramid:
    """An image and smaller copies of it, so a camera move over it costs the same at any zoom.
    Views are cut with OpenCV (about three times faster than Pillow here)."""

    def __init__(self, im):
        a = np.asarray(im.convert("RGB")) if isinstance(im, Image.Image) else im
        self.levels = [np.ascontiguousarray(a)]
        while min(self.levels[-1].shape[:2]) > 700:
            l = self.levels[-1]
            self.levels.append(cv2.resize(l, (l.shape[1] // 2, l.shape[0] // 2), interpolation=cv2.INTER_AREA))

    @property
    def size(self):
        h, w = self.levels[0].shape[:2]
        return (w, h)

    def view_array(self, box, out=(W, H)):
        x0, y0, x1, y1 = box
        scale = (x1 - x0) / out[0]
        lvl = 0
        while lvl + 1 < len(self.levels) and scale > 1.45:
            scale /= 2
            lvl += 1
        return warp(self.levels[lvl], [c * 0.5 ** lvl for c in box], out)

    def view(self, box, out=(W, H)):
        """box = (x0, y0, x1, y1) in full-size pixels (may extend past the edges, which show as dark)."""
        return Image.fromarray(self.view_array(box, out))


def warp(arr, box, out=(W, H)):
    """The part of arr inside box (float pixels), scaled to out, with sub-pixel accuracy."""
    x0, y0, x1, y1 = box
    sx, sy = (x1 - x0) / out[0], (y1 - y0) / out[1]
    M = np.float32([[sx, 0, x0 + 0.5 * sx - 0.5], [0, sy, y0 + 0.5 * sy - 0.5]])
    return cv2.warpAffine(arr, M, out, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT, borderValue=NIGHT)


@functools.lru_cache(maxsize=48)
def pyramid(name, tone, crop):
    return Pyramid(picture(name, tone, crop))


def cover_box(iw, ih, z, fx, fy, aspect=W / H):
    """The camera rectangle (in picture pixels) for a cover-fill view at zoom z centred near (fx, fy)."""
    if iw / ih > aspect:
        ch = ih / z
        cw = ch * aspect
    else:
        cw = iw / z
        ch = cw / aspect
    cx = clamp(fx * iw, cw / 2, iw - cw / 2)
    cy = clamp(fy * ih, ch / 2, ih - ch / 2)
    return (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)


# ------------------------------------------------------------------------------------------------ backgrounds and textures
@functools.lru_cache(maxsize=16)
def noise_tex(w, h, scale, seed, blur=0):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8), "L").resize((w, h), Image.BICUBIC)
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im


@functools.lru_cache(maxsize=8)
def desk(seed=1, color=(30, 24, 19), w=W, h=H):
    """A dark, slightly mottled background (like an old leather desk) for prints and clippings."""
    n1 = np.asarray(noise_tex(w, h, 160, seed, 30), np.float32) / 255.0
    n2 = np.asarray(noise_tex(w, h, 24, seed + 1, 2), np.float32) / 255.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w * 0.65)) ** 2 + ((yy - h / 2) / (h * 0.7)) ** 2)
    v = np.clip(1.15 - d * 0.75, 0.25, 1.0)
    base = np.array(color, np.float32)[None, None, :] * (0.78 + 0.32 * n1[..., None] + 0.08 * n2[..., None]) * v[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")


SW, SH = 480, 270           # the smoky card background is worked out small and enlarged (it's all soft anyway)


@functools.lru_cache(maxsize=8)
def _smoke_parts(seed):
    base = np.asarray(desk(seed, (16, 13, 11), SW, SH), np.float32)
    layers = []
    for i, (sc, a) in enumerate(((55, 0.30), (30, 0.20))):
        n = np.asarray(noise_tex(SW * 2, SH, sc, seed + 10 + i, 8), np.float32) / 255.0
        layers.append(np.clip((n - 0.35) * 1.8, 0, 1) * a)
    return base, layers


def dark_bg(t, seed=1, strength=1.0):
    base, layers = _smoke_parts(seed)
    m = np.zeros((SH, SW), np.float32)
    for i, L in enumerate(layers):
        x = int((t * (4.5 + 2.5 * i)) % SW)
        m += L[:, x:x + SW]
    m *= strength
    col = np.array((150, 140, 128), np.float32)
    out = np.clip(base + (col - base) * m[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(cv2.resize(out, (W, H), interpolation=cv2.INTER_LINEAR))


@functools.lru_cache(maxsize=8)
def aged_paper(w, h, seed=3, color=PAPER, edge=70, ragged=True, blotch=0.10):
    rng = np.random.default_rng(seed)
    base = np.ones((h, w, 3), np.float32) * np.array(color, np.float32)
    blot = np.asarray(noise_tex(w, h, 90, seed, 30), np.float32)[..., None] / 255.0
    fine = np.asarray(noise_tex(w, h, 3, seed + 5, 0), np.float32)[..., None] / 255.0
    base *= (0.97 - blotch) + 2 * blotch * blot * 0.6 + 0.05 * fine
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    e = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]) / float(edge)
    base *= (0.62 + 0.38 * np.clip(e, 0, 1) ** 0.55)[..., None]
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    if ragged:
        mask = Image.new("L", (w, h), 0)
        pts = []
        step = 12
        for i in range(0, w, step):
            pts.append((i, rng.uniform(0, 6)))
        for i in range(0, h, step):
            pts.append((w - rng.uniform(0, 6), i))
        for i in range(w, 0, -step):
            pts.append((i, h - rng.uniform(0, 6)))
        for i in range(h, 0, -step):
            pts.append((rng.uniform(0, 6), i))
        ImageDraw.Draw(mask).polygon(pts, fill=255)
        im.putalpha(mask)
    return im


# ------------------------------------------------------------------------------------------------ film look (in Python: dust and scratches;
# grain and vignette are done by ffmpeg's filters, which is much faster)
def dust(frame, t, amount=1.0):
    n = int(t * FPS)
    rng = np.random.default_rng(n * 7919 + 13)
    d = ImageDraw.Draw(frame)
    for _ in range(int(rng.integers(0, 4) * amount)):
        x, y = rng.integers(0, W), rng.integers(0, H)
        r = rng.uniform(0.8, 2.6)
        c = int(rng.choice([18, 22, 210, 225]))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(c, c, c))
    if rng.random() < 0.05 * amount:           # a hair
        x, y = rng.integers(0, W), rng.integers(0, H)
        pts = [(x + 6 * k + rng.normal(0, 2), y + 4 * math.sin(k / 2.0) + rng.normal(0, 1)) for k in range(int(rng.integers(6, 16)))]
        d.line(pts, fill=(20, 20, 20), width=1)
    blk = n // 9                                # a scratch that lasts a few frames now and then
    r2 = np.random.default_rng(blk * 31 + 5)
    if r2.random() < 0.18 * amount:
        x = int(r2.integers(80, W - 80)) + int(rng.integers(-2, 3))
        c = int(r2.choice([30, 200]))
        d.line((x, 0, x + int(r2.integers(-6, 7)), H), fill=(c, c, c), width=1)


FFMPEG_LOOK = "vignette=angle=0.62:eval=init,noise=c0s=5:c0f=t+u"


# ------------------------------------------------------------------------------------------------ shots
SHOTS = {}


def shot(kind):
    def deco(cls):
        SHOTS[kind] = cls
        cls.kind = kind
        return cls
    return deco


class Shot:
    """One picture on screen from start to end (seconds). spec comes from script.json."""

    def __init__(self, spec, start, end, line=None):
        self.spec, self.start, self.end, self.line = spec, start, end, line
        self.ready = False

    @property
    def dur(self):
        return max(0.1, self.end - self.start)

    def u(self, t):
        return (t - self.start) / self.dur

    def prepare(self):
        pass

    def draw(self, t):
        if not self.ready:
            self.prepare()
            self.ready = True
        return self.frame(t)

    def frame(self, t):
        return Image.new("RGB", (W, H), NIGHT)

    def credit(self):
        f = self.spec.get("file")
        return self.spec.get("credit", credit_for(f) if f else "")


def drift(u):
    """Camera progress over a shot: steady, with soft ends (a little past 0..1 for the dissolves)."""
    u = clamp(u, -0.15, 1.15)
    return 0.5 - 0.5 * math.cos(math.pi * clamp((u + 0.15) / 1.3))


class Scene:
    """A still composition a bit bigger than the frame, for a slow camera push (prints, clippings)."""
    MARGIN = 1.16

    def __init__(self, bg_seed=1):
        self.w, self.h = int(W * self.MARGIN), int(H * self.MARGIN)
        self.img = desk(bg_seed, (30, 24, 19), self.w, self.h).copy()

    def place_c(self, rgba, cx=None, cy=None):
        cx = self.w / 2 if cx is None else cx
        cy = self.h / 2 if cy is None else cy
        self.img.paste(rgba, (int(cx - rgba.width / 2), int(cy - rgba.height / 2)), rgba)

    def done(self):
        self.pyr = Pyramid(self.img)
        return self

    def view(self, z, fx=0.5, fy=0.5):
        """z = 1: the whole scene; z = MARGIN: exactly frame-sized."""
        vw = self.w / z
        vh = vw * H / W
        cx = clamp(fx * self.w, vw / 2, self.w - vw / 2)
        cy = clamp(fy * self.h, vh / 2, self.h - vh / 2)
        return self.pyr.view((cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2))


@shot("photo")
class Photo(Shot):
    """A photo. fit: cover (fills the frame, slow push or pan), contain (whole picture over a blurred copy of
    itself), print (an old print with a border, lying on a dark desk)."""

    def prepare(self):
        s = self.spec
        self.tone = s.get("tone", "sepia")
        self.crop = tuple(s["crop"]) if s.get("crop") else None
        self.fit = s.get("fit", "cover")
        self.z = s.get("z", [1.0, 1.10] if self.fit == "cover" else [1.0, 1.10])
        self.f0, self.f1 = s.get("f0", [0.5, 0.5]), s.get("f1", s.get("f0", [0.5, 0.5]))
        if self.fit == "cover":
            self.pyr = pyramid(s["file"], self.tone, self.crop)
            return
        pic = picture(s["file"], self.tone, self.crop)
        sc = Scene(bg_seed=sum(map(ord, s["file"])) % 5 + 1)
        if self.fit == "contain":
            bg = pic.copy()
            bg.thumbnail((480, 480))
            bg = ImageOps.fit(bg, (480, 270)).filter(ImageFilter.GaussianBlur(12))
            bg = ImageEnhance.Brightness(bg).enhance(0.36)
            sc.img = bg.resize((sc.w, sc.h), Image.BICUBIC)
            box = s.get("box", [0.86, 0.86])
            k = min(W * box[0] / pic.width, H * box[1] / pic.height)
            fg = pic.resize((max(1, int(pic.width * k)), max(1, int(pic.height * k))), Image.LANCZOS).convert("RGBA")
            img, _ = shadow(fg, radius=22, alpha=170, offset=(0, 12))
            sc.place_c(img)
        else:                                   # print: a cream border, a slight tilt, on the desk
            box = s.get("box", [0.74, 0.82])
            k = min(W * box[0] / pic.width, H * box[1] / pic.height)
            p = pic.resize((max(1, int(pic.width * k)), max(1, int(pic.height * k))), Image.LANCZOS)
            b = max(14, int(min(p.size) * 0.045))
            card = aged_paper(p.width + 2 * b, p.height + 2 * b + int(b * 0.8), seed=sum(map(ord, s["file"])) % 97, color=(222, 208, 178), edge=30, ragged=False).copy()
            card.paste(p, (b, b))
            ImageDraw.Draw(card).rectangle((b - 1, b - 1, b + p.width, b + p.height), outline=(120, 100, 76, 255), width=1)
            rot = s.get("rot", (sum(map(ord, s["file"])) % 5 - 2) * 0.7)
            card = card.rotate(rot, resample=Image.BICUBIC, expand=True)
            img, _ = shadow(card, radius=20, alpha=190, offset=(6, 14))
            sc.place_c(img)
        self.scene = sc.done()

    def frame(self, t):
        k = drift(self.u(t))
        z = lerp(self.z[0], self.z[1], k)
        fx, fy = lerp(self.f0[0], self.f1[0], k), lerp(self.f0[1], self.f1[1], k)
        if self.fit == "cover":
            iw, ih = self.pyr.size
            return self.pyr.view(cover_box(iw, ih, z, fx, fy))
        return self.scene.view(z, fx, fy)


@functools.lru_cache(maxsize=24)
def paper_page(name, tone="paper"):
    return Pyramid(picture(name, tone, None, max_side=4000))


def fit_aspect(box, iw, ih, aspect=W / H, margin=1.0):
    """Grow a box (pixels) to the frame's shape, centred, times margin."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * margin, (y1 - y0) * margin
    if w / h > aspect:
        h = w / aspect
    else:
        w = h * aspect
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


@shot("news")
class News(Shot):
    """A 1908 newspaper page. mode: zoom (from the whole page into box), pan (box -> box2), hold, or clip (a
    cut-out piece as a clipping on the desk). box/box2 are fractions of the page; "crop": n uses the n-th
    headline block found by fetch.py."""

    def box_from_spec(self, iw, ih):
        s = self.spec
        b = s.get("box")
        if b is None and s.get("crop") is not None:
            m = MANIFEST.get(s["file"], {})
            c = m.get("crops", [])[int(s["crop"]) - 1]
            pw, ph = m.get("page_size", [iw, ih])
            x, y, w, h = c["box"]
            b = [x / pw, y / ph, (x + w) / pw, (y + h) / ph]
        return b

    def prepare(self):
        s = self.spec
        self.mode = s.get("mode", "zoom")
        self.tone = s.get("tone", "paper")
        if self.mode == "clip":
            pic = picture(s["file"], self.tone, None, max_side=4000)
            b = self.box_from_spec(pic.width, pic.height)
            if b:
                pic = pic.crop((int(b[0] * pic.width), int(b[1] * pic.height), int(b[2] * pic.width), int(b[3] * pic.height)))
            size = s.get("size", [0.80, 0.72])
            k = min(W * size[0] / pic.width, H * size[1] / pic.height)
            p = pic.resize((max(1, int(pic.width * k)), max(1, int(pic.height * k))), Image.LANCZOS).convert("RGBA")
            mask = Image.new("L", p.size, 0)
            rng = np.random.default_rng(len(s["file"]))
            pts = [(i, rng.uniform(0, 7)) for i in range(0, p.width, 10)] + [(p.width - rng.uniform(0, 7), i) for i in range(0, p.height, 10)]
            pts += [(i, p.height - rng.uniform(0, 7)) for i in range(p.width, 0, -10)] + [(rng.uniform(0, 7), i) for i in range(p.height, 0, -10)]
            ImageDraw.Draw(mask).polygon(pts, fill=255)
            p.putalpha(mask)
            p = p.rotate(s.get("rot", -1.2), resample=Image.BICUBIC, expand=True)
            img, _ = shadow(p, radius=18, alpha=200, offset=(5, 12))
            sc = Scene(3)
            sc.place_c(img)
            self.scene = sc.done()
            self.z = s.get("z", [1.0, 1.10])
            return
        self.pyr = paper_page(s["file"], self.tone)
        iw, ih = self.pyr.size
        whole = fit_aspect((0, 0, iw, ih), iw, ih, margin=1.08)
        b = self.box_from_spec(iw, ih)
        tight = fit_aspect((b[0] * iw, b[1] * ih, b[2] * iw, b[3] * ih), iw, ih, margin=s.get("margin", 1.15)) if b else whole
        if self.mode == "pan":
            b2 = s["box2"]
            self.r0, self.r1 = tight, fit_aspect((b2[0] * iw, b2[1] * ih, b2[2] * iw, b2[3] * ih), iw, ih, margin=s.get("margin", 1.15))
        elif self.mode == "hold":
            self.r0 = self.r1 = tight
        else:
            self.r0, self.r1 = whole, tight
        self.hold = s.get("hold", 0.35)       # the last part of the shot stays on the headline

    def frame(self, t):
        u = self.u(t)
        if self.mode == "clip":
            return self.scene.view(lerp(self.z[0], self.z[1], drift(u)))
        k = ease(clamp(u / max(0.2, 1 - self.hold))) if self.mode != "hold" else 0
        r0, r1 = self.r0, self.r1
        w0, w1 = r0[2] - r0[0], r1[2] - r1[0]
        w = math.exp(lerp(math.log(w0), math.log(w1), k))           # zoom in log space so the move feels even
        kk = (w0 - w) / (w0 - w1) if abs(w0 - w1) > 1e-6 else k
        cx = lerp((r0[0] + r0[2]) / 2, (r1[0] + r1[2]) / 2, kk)
        cy = lerp((r0[1] + r0[3]) / 2, (r1[1] + r1[3]) / 2, kk)
        if self.mode == "hold":
            w *= lerp(1.0, 0.93, drift(u))
        h = w * H / W
        return self.pyr.view((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))

    def credit(self):
        m = MANIFEST.get(self.spec.get("file"), {})
        return self.spec.get("credit", f"{m.get('artist', 'Newspaper')}, {m.get('date', '')} · Library of Congress" if m else "")


def word_times(line):
    """[(word, start, end)] for a line, from the voice job (empty before it has run)."""
    v = VOICE_DATA.get(line["id"]) if line else None
    return v["words"] if v else []


def fine_print(d, x0, y, colw, rows, rng, size=5, gap=12):
    """Rows of tiny word-shaped marks: print too small to read."""
    for r in range(rows):
        x = x0
        end = x0 + (colw if r < rows - 1 else int(colw * rng.uniform(0.3, 0.8)))
        while x < end - 12:
            wl = int(rng.integers(8, 40))
            if x + wl > end:
                break
            d.rectangle((x, y + 2, x + wl, y + size), fill=(70, 56, 42, int(rng.integers(40, 70))))
            x += wl + int(rng.integers(7, 11))
        y += size + gap
    return y


class Reveal(Shot):
    """Words that darken (or appear) as the narrator reads them: two versions of the page are made once, and
    each frame pastes the read words from the finished one onto the unread one."""

    def build_pages(self):
        raise NotImplementedError

    def prepare(self):
        unread, done, boxes, focus = self.build_pages()      # RGBA pages, word boxes in page pixels
        sc = Scene(self.spec.get("desk", 2))
        cx, cy = sc.w / 2, sc.h / 2
        ox, oy = int(cx - unread.width / 2), int(cy - unread.height / 2)
        sh, pad = shadow(unread, radius=16, alpha=170, offset=(4, 12))
        sc.img.paste(sh, (ox - pad, oy - pad), sh)
        self.base = np.asarray(sc.img.convert("RGB")).copy()
        full = sc.img.copy()
        full.paste(done, (ox, oy), done)
        self.full = np.asarray(full.convert("RGB")).copy()
        self.boxes = [(x0 + ox, y0 + oy, x1 + ox, y1 + oy) for (x0, y0, x1, y1) in boxes]
        self.sw, self.sh = sc.w, sc.h
        self.focus = (0.5, (oy + focus * unread.height) / sc.h)
        self.z = self.spec.get("z", [1.0, 1.14])

    def words_read(self, t):
        spoken = word_times(self.line)
        tl = t - (self.line["_start"] if self.line else self.start)
        n = len(self.boxes)
        if spoken and self.spec.get("sync", True):
            k = sum(1 for (_, a, b) in spoken if a <= tl + 0.05)
            return min(n, int(round(k * n / max(1, len(spoken)))))
        return int(n * clamp(self.u(t) * 1.25))

    def frame(self, t):
        k = drift(self.u(t))
        z = lerp(self.z[0], self.z[1], k)
        vw = self.sw / z
        vh = vw * H / W
        cx = clamp(self.focus[0] * self.sw, vw / 2, self.sw - vw / 2)
        cy = clamp(self.focus[1] * self.sh, vh / 2, self.sh - vh / 2)
        x0, y0 = cx - vw / 2, cy - vh / 2
        comp = self.base.copy()
        for (bx0, by0, bx1, by1) in self.boxes[: self.words_read(t)]:
            comp[by0:by1, bx0:bx1] = self.full[by0:by1, bx0:bx1]
        return Image.fromarray(warp(comp, (x0, y0, x0 + vw, y0 + vh)))


@shot("ad")
class Ad(Reveal):
    """A newspaper classified ad set in old type; its words darken as the narrator reads them."""

    def build_pages(self):
        s = self.spec
        colw, pw, ph = 760, 1040, 1180
        page = aged_paper(pw, ph, seed=21, color=(220, 204, 170), edge=90).copy()
        d = ImageDraw.Draw(page)
        x0 = (pw - colw) // 2
        d.line((x0 - 30, 60, x0 - 30, ph - 60), fill=INK + (120,), width=2)
        d.line((x0 + colw + 30, 60, x0 + colw + 30, ph - 60), fill=INK + (120,), width=2)
        rng = np.random.default_rng(4)
        y = 90
        while y < 300:
            y = fine_print(d, x0, y, colw, int(rng.integers(3, 6)), rng) + 22
        d.line((x0, y, x0 + colw, y), fill=INK + (160,), width=2)
        hd = text(s.get("head", "PERSONAL."), "old-b", 44, INK + (255,), tracking=4)
        page.alpha_composite(hd, (x0 + (colw - hd.width) // 2, y + 26))
        y += 26 + hd.height + 30
        f = font("old", 40)
        words = s["text"].split()
        lines, cur = [], []
        for wd in words:
            if f.getlength(" ".join(cur + [wd])) > colw and cur:
                lines.append(cur)
                cur = [wd]
            else:
                cur.append(wd)
        if cur:
            lines.append(cur)
        lh = 54
        y_text = y
        unread, done = page.copy(), page.copy()
        du, dd = ImageDraw.Draw(unread), ImageDraw.Draw(done)
        boxes = []
        for li, ln in enumerate(lines):
            total = sum(f.getlength(w) for w in ln)
            last = li == len(lines) - 1
            space = (colw - total) / (len(ln) - 1) if len(ln) > 1 and not last else f.getlength(" ")
            x = x0
            for wd in ln:
                du.text((x, y), wd, font=f, fill=INK + (80,))
                dd.text((x, y), wd, font=f, fill=INK + (255,))
                wl = f.getlength(wd)
                boxes.append((int(x) - 2, int(y) - 4, int(x + wl) + 3, int(y + lh) - 4))
                x += wl + space
            y += lh
        yb = y + 30
        for im in (unread, done):
            dr = ImageDraw.Draw(im)
            dr.line((x0, yb, x0 + colw, yb), fill=INK + (160,), width=2)
            r2 = np.random.default_rng(5)
            yy = yb + 30
            while yy < ph - 80:
                yy = fine_print(dr, x0, yy, colw, int(r2.integers(3, 6)), r2) + 22
        return unread, done, boxes, (y_text + yb) / 2 / ph


@shot("letter")
class Letter(Reveal):
    """A letter in an old hand on lined paper; the words appear as they're read."""

    def build_pages(self):
        s = self.spec
        pw, ph = 1240, 920
        page = aged_paper(pw, ph, seed=11, color=(232, 220, 192), edge=110).copy()
        d = ImageDraw.Draw(page)
        for yy in range(150, ph - 60, 66):
            d.line((90, yy + 48, pw - 90, yy + 48), fill=(150, 160, 175, 70), width=1)
        ink = (40, 34, 64, 255)
        f = font("fell-it", 52)
        y = 150
        if s.get("greeting"):
            page.alpha_composite(text(s["greeting"], "fell-it", 56, ink), (110, y - 52))
            y += 66
        unread, done = page.copy(), page.copy()
        dd = ImageDraw.Draw(done)
        boxes = []
        x = 110
        for wd in s["text"].split():
            wl = f.getlength(wd + " ")
            if x + wl > pw - 100:
                x, y = 110, y + 66
            dd.text((x, y), wd, font=f, fill=ink)
            boxes.append((int(x) - 2, int(y) - 2, int(x + wl), int(y + 64)))
            x += wl
        if s.get("sign"):
            sg = text(s["sign"], "fell-it", 58, ink)
            sx, sy = pw - 120 - sg.width, y + 92
            done.alpha_composite(sg, (sx, sy))
            boxes.append((sx - 4, sy - 4, sx + sg.width + 4, sy + sg.height + 6))
        return unread, done, boxes, 0.5


# ---- cards
@shot("title")
class Title(Shot):
    def prepare(self):
        s = self.spec
        self.t1 = glow(text(s["title"], "fell", s.get("size", 150), BONE + (255,), tracking=6), (90, 20, 10), radius=30, strength=0.9)
        self.t2 = text(s.get("subtitle", ""), "fell-it", 60, (214, 196, 166, 255)) if s.get("subtitle") else None
        self.t0 = text(s.get("kicker", ""), "inter-sb", 28, (190, 172, 140, 255), tracking=10) if s.get("kicker") else None

    def frame(self, t):
        tl = t - self.start
        f = dark_bg(t, 2)
        if self.t0:
            put_c(f, self.t0, W / 2, H / 2 - 170, fade(tl, 0.3, 1.0))
        put_c(f, self.t1, W / 2, H / 2 - 20, fade(tl, 0.6, 1.4))
        if self.t2:
            put_c(f, self.t2, W / 2, H / 2 + 120, fade(tl, 1.6, 1.0))
        return f


NUMBERS = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen"]


@shot("chapter")
class Chapter(Shot):
    def prepare(self):
        s = self.spec
        n = s.get("n")
        self.k = text(f"CHAPTER {NUMBERS[n].upper()}" if n else s.get("kicker", ""), "inter-sb", 30, (196, 176, 140, 255), tracking=12)
        self.t = glow(text(s["title"], "fell", 140, BONE + (255,), tracking=3), (80, 18, 8), radius=26, strength=0.75)
        self.sub = text(s["sub"], "fell-it", 48, (200, 184, 156, 255)) if s.get("sub") else None
        self.rule = Image.new("RGBA", (360, 2), (196, 176, 140, 200))

    def frame(self, t):
        tl = t - self.start
        f = dark_bg(t, 3)
        a = fade(tl, 0.2, 0.8) * (1 - fade(t, self.end - 0.7, 0.6))
        put_c(f, self.k, W / 2, H / 2 - 130, a)
        put_c(f, self.rule, W / 2, H / 2 - 90, a)
        put_c(f, self.t, W / 2, H / 2 + 10, a)
        if self.sub:
            put_c(f, self.sub, W / 2, H / 2 + 120, a * fade(tl, 0.7, 0.8))
        return f


@shot("quote")
class Quote(Shot):
    """A short quote on the dark card, with who said it and when."""

    def prepare(self):
        s = self.spec
        self.q = para("“" + s["text"] + "”", s.get("font", "fell-it"), s.get("size", 76), BONE + (255,), s.get("width", 1450), gap=1.3, align="center")
        self.by = text(s["by"], "inter-m", 30, (196, 176, 140, 255), tracking=2) if s.get("by") else None

    def frame(self, t):
        tl = t - self.start
        f = dark_bg(t, 5)
        a = fade(tl, 0.15, 0.7)
        put_c(f, self.q, W / 2, H / 2 - 30, a)
        if self.by:
            put_c(f, self.by, W / 2, H / 2 + self.q.height / 2 + 40, a * fade(tl, 0.8, 0.8))
        return f


@shot("big")
class Big(Shot):
    """A big number, date or name with a line under it (over a darkened photo if `file` is given)."""

    def prepare(self):
        s = self.spec
        fk = s.get("font", "lora-b" if any(ch.isdigit() for ch in s["text"]) else "fell")
        self.top = glow(text(s["text"], fk, s.get("size", 170), tuple(s.get("color", BONE)) + (255,)), (60, 10, 6), radius=26, strength=0.8)
        self.cap = para(s["cap"], "inter-m", 40, (222, 208, 182, 255), 1300, align="center") if s.get("cap") else None
        self.under = None
        if s.get("file"):
            p = Photo(dict(file=s["file"], tone=s.get("tone", "sepia"), z=s.get("z", [1.05, 1.12]), f0=s.get("f0", [0.5, 0.5])), self.start, self.end)
            p.prepare()
            self.under = p

    def frame(self, t):
        tl = t - self.start
        if self.under:
            f = Image.blend(self.under.frame(t), Image.new("RGB", (W, H), (8, 6, 5)), 0.62)
        else:
            f = dark_bg(t, 6)
        put_c(f, self.top, W / 2, H / 2 - 40, fade(tl, 0.1, 0.6))
        if self.cap:
            put_c(f, self.cap, W / 2, H / 2 + 110, fade(tl, 0.5, 0.7))
        return f


@shot("names")
class Names(Shot):
    """Names that appear one at a time (for the people who died)."""

    def prepare(self):
        s = self.spec
        self.head = text(s.get("head", ""), "inter-sb", 30, (196, 176, 140, 255), tracking=8) if s.get("head") else None
        self.rows = []
        for n in s["names"]:
            name, sub = (n + [""])[:2] if isinstance(n, list) else (n, "")
            a = text(name, "fell", 64, BONE + (255,))
            b = text(sub, "fell-it", 40, (196, 180, 150, 255)) if sub else None
            self.rows.append((a, b))
        self.cols = s.get("cols", 2 if len(self.rows) > 6 else 1)

    def frame(self, t):
        tl = t - self.start
        f = dark_bg(t, 7)
        if self.head:
            put_c(f, self.head, W / 2, 130, fade(tl, 0.1, 0.6))
        per = max(1, math.ceil(len(self.rows) / self.cols))
        step = min(122, (H - 320) / per)
        span = self.dur * float(self.spec.get("span", 0.75))
        for i, (a, b) in enumerate(self.rows):
            col, row = i // per, i % per
            cx = W / 2 if self.cols == 1 else (W * (0.28 + 0.44 * col))
            y = 240 + row * step
            al = fade(tl, 0.4 + i * span / max(1, len(self.rows)), 0.6)
            put_c(f, a, cx, y, al)
            if b:
                put_c(f, b, cx, y + 46, al * 0.9)
        return f


@shot("dark")
class Dark(Shot):
    def frame(self, t):
        return dark_bg(t, 8)


# ------------------------------------------------------------------------------------------------ maps
MAPS = {
    # bbox: lon0, lat0, lon1, lat1 (Mercator); the picture is px wide
    "atlantic": {"bbox": [-96.0, 28.0, 26.0, 69.0], "px": 5200, "grid": 10,
                 "files": ["world-land", "world-lakes", "world-borders", "world-states"]},
    "midwest": {"bbox": [-89.4, 40.9, -85.4, 42.9], "px": 5200, "grid": 0.5,
                "files": ["mid-lakes", "mid-states", "mid-rail"]},
}
LAND, WATER, COAST = (228, 214, 180), (172, 180, 168), (64, 50, 36)


def merc_y(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


class MapBase:
    def __init__(self, name):
        m = MAPS[name]
        self.name = name
        lon0, lat0, lon1, lat1 = m["bbox"]
        self.lon0, self.lon1 = lon0, lon1
        self.y0, self.y1 = merc_y(lat1), merc_y(lat0)          # top, bottom
        self.wpx = m["px"]
        self.k = self.wpx / math.radians(lon1 - lon0)
        self.hpx = int((self.y0 - self.y1) * self.k)
        self.img = self.draw(m)
        self.pyr = Pyramid(self.img)

    def xy(self, lon, lat):
        return (math.radians(lon - self.lon0) * self.k, (self.y0 - merc_y(lat)) * self.k)

    def geo(self, fname):
        return json.load(open(os.path.join(HERE, "map", fname + ".geojson"), encoding="utf-8"))["features"]

    def draw(self, m):
        img = Image.new("RGB", (self.wpx, self.hpx), WATER if self.name == "atlantic" else LAND)
        d = ImageDraw.Draw(img)
        def rings(g):
            t, c = g["type"], g["coordinates"]
            if t == "Polygon":
                return [c]
            if t == "MultiPolygon":
                return c
            return []
        def lines(g):
            t, c = g["type"], g["coordinates"]
            if t == "LineString":
                return [c]
            if t == "MultiLineString":
                return c
            if t == "Polygon":
                return c
            if t == "MultiPolygon":
                return [r for p in c for r in p]
            return []
        P = lambda ring: [self.xy(x, y) for x, y in ring]
        files = m["files"]
        if "world-land" in files:
            for f in self.geo("world-land"):
                for poly in rings(f["geometry"]):
                    d.polygon(P(poly[0]), fill=LAND)
                    for hole in poly[1:]:
                        d.polygon(P(hole), fill=WATER)
        lakes = [x for x in files if x.endswith("lakes")]
        for lf in lakes:
            for f in self.geo(lf):
                for poly in rings(f["geometry"]):
                    d.polygon(P(poly[0]), fill=WATER)
        # coast lines with a soft "water lining" (old maps hatch the water along the shore)
        shore = []
        if "world-land" in files:
            for f in self.geo("world-land"):
                for poly in rings(f["geometry"]):
                    shore += [P(r) for r in poly]
        for lf in lakes:
            for f in self.geo(lf):
                for poly in rings(f["geometry"]):
                    shore += [P(r) for r in poly]
        lw = max(2, self.wpx // 1600)
        for k, a in ((5, 40), (3, 70)):
            for r in shore:
                if len(r) > 2:
                    d.line(r + [r[0]], fill=tuple(int(c * (1 - a / 255) + 120 * a / 255) for c in WATER), width=lw * k)
        for lf in lakes + (["world-land"] if "world-land" in files else []):
            for f in self.geo(lf):
                for poly in rings(f["geometry"]):
                    d.polygon(P(poly[0]), fill=WATER if lf != "world-land" else LAND)
        for r in shore:
            if len(r) > 2:
                d.line(r + [r[0]], fill=COAST, width=lw)
        for bf, col, dash in (("world-borders", (120, 92, 66), 18), ("world-states", (150, 124, 96), 12), ("mid-states", (120, 92, 66), 26)):
            if bf in files:
                for f in self.geo(bf):
                    for ln in lines(f["geometry"]):
                        dashed(d, P(ln), col, max(1, lw - 1), dash * lw / 2, dash * lw / 3)
        if "mid-rail" in files:
            for f in self.geo("mid-rail"):
                for ln in lines(f["geometry"]):
                    pts = P(ln)
                    d.line(pts, fill=(150, 128, 102), width=max(1, lw - 1))
        # graticule
        g = m["grid"]
        lon = math.ceil(self.lon0 / g) * g
        while lon < self.lon1:
            x = self.xy(lon, 0)[0]
            d.line([(x, 0), (x, self.hpx)], fill=(150, 130, 100), width=1)
            lon += g
        lat_lo, lat_hi = m["bbox"][1], m["bbox"][3]
        lat = math.ceil(lat_lo / g) * g
        while lat < lat_hi:
            y = self.xy(self.lon0, lat)[1]
            d.line([(0, y), (self.wpx, y)], fill=(150, 130, 100), width=1)
            lat += g
        # paper: blotches and darker edges
        arr = np.asarray(img, np.float32)
        n = np.asarray(noise_tex(self.wpx // 8, self.hpx // 8, 60, 3, 10).resize((self.wpx, self.hpx), Image.BICUBIC), np.float32)[..., None] / 255.0
        arr *= 0.93 + 0.09 * n
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def dashed(d, pts, fill, width, dash, gap):
    """A dashed line that keeps its rhythm along the whole path."""
    run = 0.0
    period = dash + gap
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.dist(a, b)
        pos = 0.0
        while pos < L - 1e-6:
            ph = run % period
            on = ph < dash
            step = min(L - pos, (dash - ph) if on else (period - ph))
            if on:
                d.line([(lerp(a[0], b[0], pos / L), lerp(a[1], b[1], pos / L)),
                        (lerp(a[0], b[0], (pos + step) / L), lerp(a[1], b[1], (pos + step) / L))], fill=fill, width=width)
            pos += step
            run += step


@functools.lru_cache(maxsize=4)
def map_base(name):
    return MapBase(name)


@shot("map")
class Map(Shot):
    """An old-style map. cam0/cam1: [lon, lat, width in degrees]. route: [[lon, lat], ...] drawn from
    route_from to route_to (fractions of the shot). places: [{"name", "at": [lon, lat], "show": fraction}]."""

    def prepare(self):
        self.mb = map_base(self.spec.get("map", "atlantic"))
        self.route = [self.mb.xy(*p) for p in self.spec.get("route", [])]
        self.places = []
        for p in self.spec.get("places", []):
            lab = text(p["name"], p.get("font", "fell-it"), p.get("size", 58), INK + (255,), tracking=p.get("tracking", 0))
            self.places.append((p, self.mb.xy(*p["at"]), glow(lab, (236, 224, 196), radius=8, strength=1.0)))
        self.title = glow(text(self.spec["title"], "fell-sc", 72, INK + (255,), tracking=6), (236, 224, 196), radius=10, strength=1.0) if self.spec.get("title") else None

    def cam(self, k):
        c0, c1 = self.spec["cam0"], self.spec.get("cam1", self.spec["cam0"])
        w = math.exp(lerp(math.log(c0[2]), math.log(c1[2]), k))
        kk = (c0[2] - w) / (c0[2] - c1[2]) if abs(c0[2] - c1[2]) > 1e-9 else k
        lon, lat = lerp(c0[0], c1[0], kk), lerp(c0[1], c1[1], kk)
        cx, cy = self.mb.xy(lon, lat)
        wpx = math.radians(w) * self.mb.k
        return (cx - wpx / 2, cy - wpx * H / W / 2, cx + wpx / 2, cy + wpx * H / W / 2)

    def frame(self, t):
        u = self.u(t)
        k = ease(clamp(u / self.spec.get("move_end", 0.8)))
        box = self.cam(k)
        f = self.mb.pyr.view(box)
        sx = W / (box[2] - box[0])
        S = lambda p: ((p[0] - box[0]) * sx, (p[1] - box[1]) * sx)
        d = ImageDraw.Draw(f)
        if self.route:
            r0, r1 = self.spec.get("route_from", 0.15), self.spec.get("route_to", 0.85)
            prog = ease(clamp((u - r0) / max(0.05, r1 - r0)))
            pts = [S(p) for p in self.route]
            seglen = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
            total = sum(seglen) or 1
            want = total * prog
            drawn, acc = [pts[0]], 0
            for i, L in enumerate(seglen):
                if acc + L >= want:
                    q = (want - acc) / L if L else 0
                    drawn.append((lerp(pts[i][0], pts[i + 1][0], q), lerp(pts[i][1], pts[i + 1][1], q)))
                    break
                drawn.append(pts[i + 1])
                acc += L
            # dashes
            dash, gap, run = 22, 14, 0.0
            for i in range(len(drawn) - 1):
                a, b = drawn[i], drawn[i + 1]
                L = math.dist(a, b)
                pos = 0.0
                while pos < L:
                    on = (run % (dash + gap)) < dash
                    step = min(L - pos, (dash - run % (dash + gap)) if on else (dash + gap - run % (dash + gap)))
                    if on:
                        p0 = (lerp(a[0], b[0], pos / L), lerp(a[1], b[1], pos / L))
                        p1 = (lerp(a[0], b[0], (pos + step) / L), lerp(a[1], b[1], (pos + step) / L))
                        d.line([p0, p1], fill=BLOOD, width=6)
                    pos += step
                    run += step
            if 0 < prog < 1:
                x, y = drawn[-1]
                d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=BLOOD, outline=(250, 236, 210), width=3)
        for p, xy, lab in self.places:
            a = fade(u, p.get("show", 0.0), 0.12)
            if a <= 0:
                continue
            x, y = S(xy)
            r = p.get("dot", 9)
            if r:
                d.ellipse((x - r, y - r, x + r, y + r), fill=INK, outline=(240, 228, 200), width=2)
            off = p.get("off", [18, -lab.height / 2 - 6])
            put(f, lab, x + off[0], y + off[1], a)
        if self.title:
            put(f, self.title, 70, 60, fade(u, 0.0, 0.1))
        return f


# ------------------------------------------------------------------------------------------------ timeline
VOICE_DATA = {}
WPS = 2.45            # words per second, for timing before the narration is recorded


def load_voice():
    p = os.path.join(VOICE, "voice.json")
    if os.path.exists(p):
        for ln in json.load(open(p, encoding="utf-8"))["lines"]:
            VOICE_DATA[ln["id"]] = {"dur": ln["seconds"], "words": ln["words"], "text": ln.get("text", ln["say"])}


def line_dur(ln):
    if ln.get("say"):
        v = VOICE_DATA.get(ln["id"])
        if v and v["text"] == (ln.get("tts") or ln["say"]):
            return v["dur"]
        return len(ln["say"].split()) / WPS + 0.4
    return float(ln.get("hold", 3.0))


def load_script():
    return json.load(open(os.environ.get("DOC_SCRIPT", os.path.join(HERE, "script.json")), encoding="utf-8"))


def build(script):
    """Times for every chapter, line and shot. Returns chapters: [{id, start, end, shots, lines, overlays, music}]."""
    t = 0.0
    chapters = []
    for ch in script["chapters"]:
        c = {"id": ch["id"], "start": t, "music": ch.get("music"), "shots": [], "lines": [], "overlays": [], "sfx": []}
        if ch.get("card"):
            dur = float(ch["card"].get("hold", 4.2))
            c["shots"].append(SHOTS[ch["card"]["type"]](ch["card"], t, t + dur))
            c["sfx"].append(("chapter", t + 0.15))
            t += dur
        prev = None
        for ln in ch["lines"]:
            t += float(ln.get("pre", 0.0))
            dur = line_dur(ln)
            gap = float(ln.get("gap", 0.45 if ln.get("say") else 0.0))
            ln = dict(ln, _start=t, _dur=dur)
            c["lines"].append(ln)
            vs = ln.get("v")
            vs = vs if isinstance(vs, list) else ([vs] if vs else [])
            span_end = t + dur + gap
            if not vs or (len(vs) == 1 and vs[0].get("same")):
                if prev is not None:
                    prev.end = span_end
                    if vs and vs[0].get("line_words"):
                        prev.line = ln
            else:
                weights = [float(v.get("w", 1.0)) for v in vs]
                total = sum(weights)
                s0 = t
                for v, wgt in zip(vs, weights):
                    s1 = s0 + (span_end - t) * wgt / total
                    if v.get("same") and prev is not None:
                        prev.end = s1
                    else:
                        prev = SHOTS[v["type"]](v, s0, s1, ln)
                        c["shots"].append(prev)
                        for name, at in v.get("sfx", []):
                            c["sfx"].append((name, s0 + float(at)))
                    s0 = s1
            if ln.get("lower"):
                c["overlays"].append({"kind": "lower", "text": ln["lower"], "start": t + 0.25, "end": t + max(3.8, min(6.0, dur))})
            if ln.get("on"):
                o = ln["on"] if isinstance(ln["on"], dict) else {"text": ln["on"]}
                c["overlays"].append(dict(o, kind="on", start=t + float(o.get("at", 0.2)), end=t + float(o.get("until", dur + gap * 0.5))))
            for name, at in ln.get("sfx", []):
                c["sfx"].append((name, t + (float(at) if not isinstance(at, str) else word_at(ln, at))))
            t = span_end
        t += float(ch.get("tail", 0.6))
        if c["shots"]:
            c["shots"][-1].end = t
        c["end"] = t
        chapters.append(c)
    return chapters


def word_at(ln, word):
    w = word.lower().strip(".,")
    for (wd, a, b) in VOICE_DATA.get(ln["id"], {}).get("words", []):
        if wd.lower().strip(".,!?;:“”\"'") == w:
            return ln["_start"] + a
    words = ln.get("say", "").split()
    for i, wd in enumerate(words):
        if wd.lower().strip(".,!?;:“”\"'") == w:
            return ln["_start"] + ln["_dur"] * i / max(1, len(words))
    return ln["_start"]


# ------------------------------------------------------------------------------------------------ overlays
@functools.lru_cache(maxsize=64)
def lower_img(s):
    parts = s.split("|")
    a = text(parts[0].strip(), "fell-sc", 46, BONE + (255,), tracking=2)
    b = text(parts[1].strip(), "inter-m", 28, (206, 190, 160, 255), tracking=3) if len(parts) > 1 else None
    w = max(a.width, b.width if b else 0) + 90
    h = a.height + (b.height + 16 if b else 0) + 50
    band = Image.new("RGBA", (w + 200, h), (0, 0, 0, 0))
    arr = np.zeros((h, w + 200, 4), np.uint8)
    xs = np.linspace(1, 0, w + 200) ** 1.6
    arr[..., 3] = (xs * 170).astype(np.uint8)[None, :]
    band = Image.fromarray(arr, "RGBA")
    rule = Image.new("RGBA", (6, h - 30), (178, 30, 26, 255))
    band.alpha_composite(rule, (40, 15))
    band.alpha_composite(a, (66, 24))
    if b:
        band.alpha_composite(b, (68, 24 + a.height + 14))
    return band


@functools.lru_cache(maxsize=128)
def credit_img(s):
    return text(s, "inter-m", 20, (230, 222, 206, 200), stroke=1, stroke_fill=(0, 0, 0))


@functools.lru_cache(maxsize=64)
def on_img(s, style):
    if style == "quote":
        return glow(para(s, "fell-it", 54, BONE + (255,), 1400, align="center"), (0, 0, 0), radius=14, strength=1.0)
    if style == "label":
        return glow(text(s, "fell-sc", 64, BONE + (255,), tracking=3), (0, 0, 0), radius=14, strength=1.0)
    return glow(para(s, "inter-sb", 44, BONE + (255,), 1500, align="center"), (0, 0, 0), radius=12, strength=1.0)


def draw_overlays(f, c, t, shot_now):
    for o in c["overlays"]:
        if not (o["start"] <= t <= o["end"] + 0.5):
            continue
        a = fade(t, o["start"], 0.45) * (1 - fade(t, o["end"], 0.45))
        if o["kind"] == "lower":
            img = lower_img(o["text"])
            slide = (1 - ease_out((t - o["start"]) / 0.6)) * 40
            put(f, img, 0 - slide, H - 120 - img.height, a)
        elif o["kind"] == "on":
            img = on_img(o["text"], o.get("style", "plain"))
            pos = o.get("pos", "bottom")
            y = {"bottom": H - 150 - img.height / 2, "center": H / 2, "top": 170}[pos]
            put_c(f, img, W / 2, y, a)
    if shot_now is not None:
        cr = shot_now.credit()
        if cr:
            img = credit_img(cr)
            a = fade(t, shot_now.start + 0.2, 0.5) * (1 - fade(t, shot_now.end - 0.6, 0.4))
            put(f, img, W - 40 - img.width, H - 34 - img.height, a)


# ------------------------------------------------------------------------------------------------ frames
def frame_at(c, t):
    act = [s for s in c["shots"] if s.start - XFADE / 2 <= t < s.end + XFADE / 2]
    if not act:
        f = Image.new("RGB", (W, H), NIGHT)
        main = None
    elif len(act) == 1:
        f = act[0].draw(t)
        main = act[0]
    else:
        a, b = act[0], act[-1]
        k = ease((t - (b.start - XFADE / 2)) / XFADE)
        fa, fb = a.draw(t), b.draw(t)
        f = Image.blend(fa, fb, k)
        main = b if k >= 0.5 else a
    if f.mode != "RGB":
        f = f.convert("RGB")
    draw_overlays(f, c, t, main)
    dust(f, t)
    # chapter edges fade through black
    a_in = fade(t, c["start"], 0.5)
    a_out = 1 - fade(t, c["end"] - 0.6, 0.6)
    a = min(a_in, a_out)
    if a < 0.999:
        f = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), f, max(0.0, a))
    return f


def release(c, t):
    """Forget the big pictures of shots that are over."""
    for s in c["shots"]:
        if s.ready and s.end + XFADE < t:
            for k in ("pyr", "scene", "base", "full", "mb", "under"):
                if hasattr(s, k):
                    setattr(s, k, None)
            s.ready = False


# ------------------------------------------------------------------------------------------------ stills, segments, final
def contact_sheet(items, path, cols=4, scale=0.25):
    tw, th = int(W * scale), int(H * scale)
    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols * (tw + 10) + 10, rows * (th + 46) + 10), (250, 250, 250))
    d = ImageDraw.Draw(sheet)
    f = font("inter-m", 15)
    for i, (label, im) in enumerate(items):
        x, y = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 46)
        sheet.paste(im.resize((tw, th), Image.BILINEAR), (x, y + 36))
        d.text((x, y + 2), label[:70], font=f, fill=(20, 20, 20))
        d.text((x, y + 19), label[70:140], font=f, fill=(90, 90, 90))
    sheet.save(path, quality=88)


def cmd_stills(outdir, only):
    script = load_script()
    chapters = build(script)
    os.makedirs(outdir, exist_ok=True)
    for c in chapters:
        if only and c["id"] not in only:
            continue
        items = []
        for s in c["shots"]:
            at = s.start + s.dur * float(s.spec.get("still", 0.7))
            ln = s.line or {}
            label = f"{c['id']} {fmt_t(s.start)} {s.kind} {s.spec.get('file', s.spec.get('title', s.spec.get('text', '')))} | {ln.get('say', '')}"
            items.append((label, frame_at(c, at)))
        contact_sheet(items, os.path.join(outdir, f"sheet-{c['id']}.jpg"))
        print("sheet", c["id"], len(items), "shots", f"{c['end'] - c['start']:.1f} s")
    total = chapters[-1]["end"]
    print(f"total {total / 60:.1f} min")


def fmt_t(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def seg_key(c):
    h = hashlib.sha1()
    h.update(open(__file__, "rb").read())
    h.update(json.dumps([(s.kind, s.spec, round(s.start, 3), round(s.end, 3)) for s in c["shots"]], sort_keys=True, default=str).encode())
    h.update(json.dumps(c["overlays"], sort_keys=True, default=str).encode())
    h.update(json.dumps([(ln["id"], ln.get("say"), round(ln["_start"], 3)) for ln in c["lines"]]).encode())
    return h.hexdigest()[:12]


def render_segment(c, outdir, preset="veryfast", crf=21):
    key = seg_key(c)
    path = os.path.join(outdir, f"seg-{c['id']}-{key}.mp4")
    if os.path.exists(path):
        return path
    n = int(round((c["end"] - c["start"]) * FPS))
    tmp = path + ".part.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", FFMPEG_LOOK, "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-g", str(FPS * 2), "-r", str(FPS), "-movflags", "+faststart", tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        t = c["start"] + i / FPS
        proc.stdin.write(frame_at(c, t).tobytes())
        if i % (FPS * 5) == 0:
            release(c, t)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed on " + c["id"])
    os.replace(tmp, path)
    return path


def cmd_render(outdir, only, workers=1):
    script = load_script()
    chapters = build(script)
    os.makedirs(outdir, exist_ok=True)
    todo = [c for c in chapters if not only or c["id"] in only]
    import multiprocessing as mp
    import time as _t
    t0 = _t.time()
    if workers > 1 and len(todo) > 1:
        # longest first, so the two workers finish at about the same time
        order = sorted(range(len(todo)), key=lambda i: -(todo[i]["end"] - todo[i]["start"]))
        with mp.get_context("fork").Pool(workers) as pool:
            res = pool.map(_render_one, [(chapters.index(todo[i]), outdir) for i in order], chunksize=1)
        paths = dict(res)
    else:
        paths = dict(_render_one((chapters.index(c), outdir)) for c in todo)
    print(f"rendered {len(todo)} chapters in {(_t.time() - t0) / 60:.1f} min")
    return paths


def _render_one(args):
    idx, outdir = args
    chapters = build(load_script())
    c = chapters[idx]
    import time as _t
    t0 = _t.time()
    p = render_segment(c, outdir)
    print(f"  {c['id']}: {c['end'] - c['start']:.1f} s in {_t.time() - t0:.0f} s -> {os.path.basename(p)}", flush=True)
    return c["id"], p


def cmd_lines():
    """lines.json for the voice job, from script.json."""
    script = load_script()
    out = []
    for ch in script["chapters"]:
        for ln in ch["lines"]:
            if ln.get("say"):
                out.append({"id": ln["id"], "say": ln["say"], **({"tts": ln["tts"]} if ln.get("tts") else {})})
    ids = [x["id"] for x in out]
    assert len(ids) == len(set(ids)), "duplicate line ids"
    json.dump({"about": "Narration for the Belle Gunness documentary, made from script.json by doc.py lines. Pushing a change records the changed lines again (.github/workflows/belle-doc-voice.yml).",
               "lines": out}, open(os.path.join(HERE, "lines.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    words = sum(len(x["say"].split()) for x in out)
    print(len(out), "lines,", words, "words, about", round(words / WPS / 60, 1), "min of narration")


def cmd_srt(outdir):
    """Captions: up to two lines of ~42 characters, following the narrator's words."""
    chapters = build(load_script())
    cues = []
    for c in chapters:
        for ln in c["lines"]:
            if not ln.get("say"):
                continue
            words = (VOICE_DATA.get(ln["id"], {}).get("words") or []) if not ln.get("tts") else []
            if not words:               # spoken words differ from the caption words (or no recording yet): spread evenly
                toks = ln["say"].split()
                step = ln["_dur"] / max(1, len(toks))
                words = [[w, i * step, (i + 1) * step] for i, w in enumerate(toks)]
            cur, cs = [], None
            for (w, a, b) in words:
                if cs is None:
                    cs = a
                cur.append(w)
                txt = " ".join(cur)
                end_sentence = w.endswith((".", "?", "!"))
                if len(txt) >= 70 or (end_sentence and len(txt) > 25) or (b - cs) > 5.5:
                    cues.append((ln["_start"] + cs, ln["_start"] + b + 0.15, txt))
                    cur, cs = [], None
            if cur:
                cues.append((ln["_start"] + cs, ln["_start"] + words[-1][2] + 0.25, " ".join(cur)))
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    out = []
    for i, (a, b, txt) in enumerate(cues, 1):
        if i < len(cues):
            b = min(b, cues[i][0] - 0.02)
        if len(txt) > 42:
            words = txt.split()
            best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(txt) / 2))
            txt = " ".join(words[:best]) + "\n" + " ".join(words[best:])
        out.append(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n")
    path = os.path.join(outdir, "belle-gunness-documentary.en.srt")
    open(path, "w", encoding="utf-8").write("\n".join(out))
    print("captions:", path, len(cues), "cues")
    return path


# ------------------------------------------------------------------------------------------------ sound
def read_voice(lid):
    import soundfile as sf
    from scipy.signal import resample_poly
    for ext in (".flac", ".wav"):
        p = os.path.join(VOICE, lid + ext)
        if os.path.exists(p):
            a, rate = sf.read(p, dtype="float32", always_2d=False)
            if a.ndim > 1:
                a = a.mean(axis=1)
            if rate != SR:
                g = math.gcd(SR, rate)
                a = resample_poly(a, SR // g, rate // g).astype(np.float32)
            return a
    return None


def soundtrack(chapters, path):
    import music
    from scipy import signal as sg
    total = chapters[-1]["end"]
    n = int(total * SR) + SR
    narr = np.zeros(n, np.float32)
    missing = 0
    for c in chapters:
        for ln in c["lines"]:
            if ln.get("say"):
                a = read_voice(ln["id"])
                if a is None:
                    missing += 1
                    continue
                i = int(ln["_start"] * SR)
                narr[i:i + len(a)] += a[: n - i]
    if missing:
        print(f"  ({missing} lines have no recording yet)")
    # how much the music steps back while the narrator talks
    rect = np.abs(narr)
    att = sg.lfilter([1 - math.exp(-1 / (0.03 * SR))], [1, -math.exp(-1 / (0.03 * SR))], rect)
    rel = sg.lfilter([1 - math.exp(-1 / (0.6 * SR))], [1, -math.exp(-1 / (0.6 * SR))], att)
    duck = np.clip(np.maximum(att, rel) / (np.percentile(rel[rel > 1e-4], 70) if (rel > 1e-4).any() else 1), 0, 1).astype(np.float32)
    mus = np.zeros((n, 2), np.float32)
    for k, c in enumerate(chapters):
        name = c.get("music") or "open"
        seg = music.cue(name, c["end"] - c["start"] + 2.5, seed=k + 3)
        music.place(mus, seg, max(0.0, c["start"] - 0.4), 1.0)
    fx = np.zeros((n, 2), np.float32)
    for k, c in enumerate(chapters):
        for name, at in c["sfx"]:
            music.place(fx, music.sfx(name, seed=int(at * 10)), at, 0.8)
    gain = (0.36 - 0.26 * duck)[:, None]
    mix = narr[:, None] * 1.0 + mus * gain + fx * 0.6
    mix /= max(1.0, float(np.abs(mix).max()) / 0.95)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def loudnorm(src, dst, target=-14.0):
    """Two-pass loudness normalisation to YouTube's level."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = r.stderr[r.stderr.rfind("{"): r.stderr.rfind("}") + 1]
    m = json.loads(js)
    af = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", af, "-ar", "48000", dst], check=True)
    return m


def cmd_final(outdir, name="belle-gunness-documentary.mp4"):
    chapters = build(load_script())
    paths = cmd_render(outdir, None)
    raw = os.path.join(outdir, "soundtrack-raw.wav")
    soundtrack(chapters, raw)
    norm = os.path.join(outdir, "soundtrack.wav")
    m = loudnorm(raw, norm)
    print("  loudness before:", m["input_i"], "LUFS")
    lst = os.path.join(outdir, "segments.txt")
    with open(lst, "w") as fh:
        for c in chapters:
            fh.write(f"file '{os.path.abspath(paths[c['id']])}'\n")
    out = os.path.join(outdir, name)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", norm,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    total = chapters[-1]["end"]
    print(f"made {out}: {total / 60:.2f} min, {os.path.getsize(out) / 1e6:.0f} MB")
    print("chapters:")
    for c in chapters:
        print(f"  {fmt_t(c['start'])} {c['id']}")
    return out


def main():
    load_manifests()
    load_voice()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    cmd = args[0]
    if cmd == "lines":
        cmd_lines()
    elif cmd == "stills":
        cmd_stills(args[1], set(args[2:]))
    elif cmd == "render":
        cmd_render(args[1], set(args[2:]))
    elif cmd == "final":
        cmd_final(args[1])
    elif cmd == "srt":
        cmd_srt(args[1])
    elif cmd == "sound":
        chapters = build(load_script())
        soundtrack(chapters, os.path.join(args[1], "soundtrack-raw.wav"))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main()
