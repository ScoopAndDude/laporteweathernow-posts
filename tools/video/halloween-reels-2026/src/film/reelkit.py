"""Shared pieces for the 9:16 Facebook reels: text, photos with slow zooms, the LPWN header,
Belle-series captions (word-by-word yellow), the double-tap end card, and the sound mix."""
import json
import math
import os
import re
import subprocess
import sys

import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from scipy.signal import resample_poly

FILM = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FILM)
sys.path.insert(0, FILM)

import shorts as SH  # noqa: E402
from core import paste, sstep, ease_out, clamp01  # noqa: E402

VW, VH, FPS, SR = 1080, 1920, 30, 48000
FONT_DIR = os.path.join(ROOT, "doc", "fonts")
IMG_DIR = os.path.join(ROOT, "belle_src", "images")
OUT = os.path.join(ROOT, "shorts", "out")

BONE = (243, 234, 219)
SEPIA = (226, 206, 168)
YELLOW = (255, 214, 72)
BLOOD = (206, 38, 32)
ORANGE = (255, 138, 28)
GHOST = (143, 255, 196)

_fonts = {}


def font(kind, size):
    """lora / lora_sb / inter_k (Black) / inter_x (ExtraBold) / inter_b / inter / fell_it / old / type."""
    key = (kind, int(size))
    if key in _fonts:
        return _fonts[key]
    files = {"inter_k": "Inter-Black.otf", "inter_x": "Inter-ExtraBold.otf", "inter_b": "Inter-Bold.otf",
             "inter_sb": "Inter-SemiBold.otf", "inter": "Inter-Regular.otf", "fell_it": "IMFeENit28P.ttf",
             "fell": "IMFeENrm28P.ttf", "old": "OldStandard-Regular.ttf", "old_b": "OldStandard-Bold.ttf",
             "type": "SpecialElite.ttf", "black": "UnifrakturMaguntia.ttf"}
    if kind.startswith("lora"):
        f = ImageFont.truetype(os.path.join(FONT_DIR, "Lora-Variable.ttf"), int(size),
                               layout_engine=ImageFont.Layout.RAQM)
        f.set_variation_by_name({"lora": b"Bold", "lora_sb": b"SemiBold", "lora_r": b"Regular"}[kind])
    else:
        f = ImageFont.truetype(os.path.join(FONT_DIR, files[kind]), int(size), layout_engine=ImageFont.Layout.RAQM)
    _fonts[key] = f
    return f


def txt(text, kind, size, fill=BONE, stroke=0, stroke_fill=(0, 0, 0), tracking=0.0, shadow=0.0, glow=None,
        glow_r=18, glow_a=0.6, max_w=None):
    """Text as a premultiplied float RGBA layer cropped to its ink (plus a margin for shadow and glow)."""
    f = font(kind, size)
    if max_w:
        while size > 18 and _width(text, f, tracking * size) > max_w:
            size -= 2
            f = font(kind, size)
    tr = tracking * size
    w = int(_width(text, f, tr)) + 4 * stroke + 40
    asc, desc = f.getmetrics()
    h = asc + desc + 4 * stroke + 40
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 20 + 2 * stroke
    if tr:
        for ch in text:
            d.text((x, 20 + 2 * stroke), ch, font=f, fill=tuple(fill) + (255,), stroke_width=stroke,
                   stroke_fill=tuple(stroke_fill) + (255,))
            x += f.getlength(ch) + tr
    else:
        d.text((x, 20 + 2 * stroke), text, font=f, fill=tuple(fill) + (255,), stroke_width=stroke,
               stroke_fill=tuple(stroke_fill) + (255,))
    box = img.getbbox()
    if box:
        img = img.crop(box)
    a = np.asarray(img, np.float32) / 255.0
    lay = a.copy()
    lay[..., :3] *= lay[..., 3:4]
    pad = int(max(glow_r * 2 if glow else 0, size * 0.25 if shadow else 0)) + 2
    lay = np.pad(lay, ((pad, pad), (pad, pad), (0, 0)))
    if shadow or glow:
        m = lay[..., 3]
        under = np.zeros_like(lay)
        if shadow:
            s = cv2.GaussianBlur(m, (0, 0), size * 0.08) * shadow
            under[..., 3] = np.clip(s, 0, 1)
        if glow:
            g = np.clip(cv2.GaussianBlur(m, (0, 0), glow_r) * 1.6, 0, 1) * glow_a
            gc = np.array(glow, np.float32) / 255.0
            under[..., :3] += g[..., None] * gc
            under[..., 3] = np.clip(under[..., 3] + g * 0.5, 0, 1)
        out = lay.copy()
        out[..., :3] = lay[..., :3] + under[..., :3] * (1 - lay[..., 3:4])
        out[..., 3] = lay[..., 3] + under[..., 3] * (1 - lay[..., 3])
        lay = out
    return lay


def _width(text, f, tr):
    if tr:
        return sum(f.getlength(c) + tr for c in text) - tr
    return f.getlength(text)


def rect_layer(w, h, color, a=1.0, r=0, edge=None, edge_a=0.6, edge_w=3):
    m = np.zeros((h * 2, w * 2), np.uint8)
    if r:
        cv2.rectangle(m, (r * 2, 0), (w * 2 - r * 2, h * 2), 255, -1)
        cv2.rectangle(m, (0, r * 2), (w * 2, h * 2 - r * 2), 255, -1)
        for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
            cv2.circle(m, (cx * 2, cy * 2), r * 2, 255, -1)
    else:
        m[:] = 255
    al = cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    out = np.zeros((h, w, 4), np.float32)
    out[..., :3] = np.array(color, np.float32)[None, None, :] / 255 * al[..., None] * a
    out[..., 3] = al * a
    if edge is not None:
        k = cv2.morphologyEx((al > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT,
                             np.ones((edge_w, edge_w), np.uint8)).astype(np.float32) * edge_a
        ec = np.array(edge, np.float32) / 255
        out[..., :3] = ec[None, None, :] * k[..., None] + out[..., :3] * (1 - k[..., None])
        out[..., 3] = k + out[..., 3] * (1 - k)
    return out


def heart(size, color=(232, 40, 60)):
    S = size * 4
    m = np.zeros((S, S), np.uint8)
    t = np.linspace(0, 2 * math.pi, 400)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    pts = np.stack([S / 2 + x * S / 36, S / 2 - y * S / 36 - S * 0.03], 1).astype(np.int32)
    cv2.fillPoly(m, [pts], 255, cv2.LINE_AA)
    a = cv2.resize(m, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    out = np.zeros((size, size, 4), np.float32)
    out[..., :3] = np.array(color, np.float32)[None, None, :] / 255 * a[..., None]
    out[..., 3] = a
    return out


# ----------------------------------------------------------------------------- pictures

def sepia(img, strength=1.0):
    """img float RGB 0..1 -> sepia-toned."""
    g = img @ np.array([0.299, 0.587, 0.114], np.float32)
    g = np.clip((g - 0.04) / 0.92, 0, 1)
    lo = np.array([22, 15, 10], np.float32) / 255
    hi = np.array(BONE, np.float32) / 255
    mid = np.array([150, 112, 72], np.float32) / 255
    a = g[..., None]
    out = np.where(a < 0.5, lo + (mid - lo) * (a / 0.5), mid + (hi - mid) * ((a - 0.5) / 0.5))
    return img * (1 - strength) + out * strength


class Photo:
    """A still that fills the 9:16 frame with a slow zoom and drift (or sits inside it with a blurred backdrop)."""

    def __init__(self, path, z=(1.0, 1.12), c0=(0.5, 0.5), c1=(0.5, 0.5), tone="sepia", fit="cover", dim=1.0,
                 crop=None):
        im = cv2.imread(path, cv2.IMREAD_COLOR)[:, :, ::-1].astype(np.float32) / 255
        if crop:
            h, w = im.shape[:2]
            x0, y0, x1, y1 = crop
            im = im[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
        if tone == "sepia":
            im = sepia(im)
        self.im = np.ascontiguousarray(im)
        self.z, self.c0, self.c1, self.fit, self.dim = z, c0, c1, fit, dim
        h, w = self.im.shape[:2]
        self.cover = max(VW / w, VH / h)
        self.contain = min(VW / w, (VH * 0.56) / h)
        if fit == "contain":
            small = cv2.resize(self.im, (max(8, w // 12), max(8, h // 12)), interpolation=cv2.INTER_AREA)
            small = cv2.GaussianBlur(small, (0, 0), 2.5)
            sc = max(VW / small.shape[1], VH / small.shape[0])
            bg = cv2.resize(small, (int(small.shape[1] * sc) + 2, int(small.shape[0] * sc) + 2),
                            interpolation=cv2.INTER_CUBIC)
            y0 = (bg.shape[0] - VH) // 2
            x0 = (bg.shape[1] - VW) // 2
            self.bg = np.ascontiguousarray(bg[y0:y0 + VH, x0:x0 + VW]) * 0.35

    def render(self, u):
        e = u * u * (3 - 2 * u)
        z = self.z[0] + (self.z[1] - self.z[0]) * e
        cx = self.c0[0] + (self.c1[0] - self.c0[0]) * e
        cy = self.c0[1] + (self.c1[1] - self.c0[1]) * e
        h, w = self.im.shape[:2]
        if self.fit == "cover":
            s = self.cover * z
            # keep the view inside the picture
            half_w, half_h = VW / s / 2, VH / s / 2
            px = min(max(cx * w, half_w), w - half_w)
            py = min(max(cy * h, half_h), h - half_h)
            M = np.array([[1 / s, 0, px - VW / (2 * s)], [0, 1 / s, py - VH / (2 * s)]], np.float32)
            out = cv2.warpAffine(self.im, M, (VW, VH), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_REFLECT)
        else:
            s = self.contain * z
            out = self.bg.copy()
            pw, ph = int(w * s), int(h * s)
            pic = cv2.resize(self.im, (pw, ph), interpolation=cv2.INTER_AREA)
            x0 = (VW - pw) // 2 + int((cx - 0.5) * 40)
            y0 = int(VH * 0.43 - ph / 2)
            ys0, xs0 = max(0, y0), max(0, x0)
            ys1, xs1 = min(VH, y0 + ph), min(VW, x0 + pw)
            out[ys0:ys1, xs0:xs1] = pic[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
        return out * self.dim


VIG = None


def vignette():
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
        d = np.sqrt(((xx - VW / 2) / (VW / 2)) ** 2 * 0.7 + ((yy - VH * 0.5) / (VH / 2)) ** 2)
        v = 1 - 0.42 * np.clip(d, 0, 1.4) ** 2.0
        # darker bands behind the header and the captions
        top = np.clip((yy - 0) / 520, 0, 1) * 0.45 + 0.55
        bot = 1 - 0.45 * np.clip((yy - 1150) / 400, 0, 1)
        VIG = (v * top * bot)[..., None].astype(np.float32)
    return VIG


GRAIN = None


def grain(frame, t, k=0.035):
    global GRAIN
    if GRAIN is None:
        rng = np.random.default_rng(7)
        GRAIN = [(rng.random((VH // 2, VW // 2), dtype=np.float32) - 0.5) for _ in range(6)]
    g = GRAIN[int(t * 12) % 6]
    g = cv2.resize(g, (VW, VH), interpolation=cv2.INTER_NEAREST)
    frame += g[..., None] * k
    return frame


# ----------------------------------------------------------------------------- header, headings, credits

_logo = None


def header(frame, t, dur, n_seg, line2=None, a=1.0):
    global _logo
    if _logo is None:
        _logo = (SH.rounded_logo(), txt("LA PORTE WEATHER NOW", "inter_b", 30, (233, 227, 214), tracking=0.03,
                                        shadow=0.6))
    SH.progress_bar(frame, min(1.0, t / dur), n_seg, a)
    paste(frame, _logo[0], 80, 206, a=a, anchor="lt")
    paste(frame, _logo[1], 228, 236, a=a, anchor="lm")
    if line2 is not None:
        paste(frame, line2, VW / 2, 300, a=a)


class Heading:
    def __init__(self, text, t0, t1, y=1190, size=62, kind="lora", color=BONE, tracking=0.04, glow=None):
        self.lay = txt(text, kind, size, color, tracking=tracking, shadow=0.9, glow=glow, glow_a=0.45,
                       max_w=VW - 120)
        self.t0, self.t1, self.y = t0, t1, y

    def draw(self, frame, t):
        a = sstep(self.t0, self.t0 + 0.3, t) * (1 - sstep(self.t1 - 0.25, self.t1, t))
        if a > 0.003:
            paste(frame, self.lay, VW / 2, self.y + 10 * (1 - ease_out(sstep(self.t0, self.t0 + 0.4, t))), a=a)


class Credit:
    def __init__(self, text, t0, t1):
        self.lay = txt(text, "inter", 23, (214, 204, 186), shadow=0.8)
        self.t0, self.t1 = t0, t1

    def draw(self, frame, t):
        a = 0.85 * sstep(self.t0, self.t0 + 0.3, t) * (1 - sstep(self.t1 - 0.3, self.t1, t))
        if a > 0.003:
            paste(frame, self.lay, 62, 1492, a=a, anchor="lm")


# ----------------------------------------------------------------------------- captions (the Belle series look)

def load_words(vo_dir, off=0.0):
    vo = json.load(open(os.path.join(vo_dir, "vo.json")))
    audio, vsr = sf.read(os.path.join(vo_dir, "vo.wav"), dtype="float32")
    sents = []
    for it in vo["items"]:
        seg = audio[int(it["s"] * vsr):int(it["e"] * vsr)]
        pz = SH.detect_pauses(seg, vsr, it["s"])
        wt = SH.word_times(it["text"], it["s"], it["e"], pz)
        words = []
        for k, (w, t0) in enumerate(wt):
            t1 = wt[k + 1][1] if k + 1 < len(wt) else it["e"]
            words.append([w, t0 + off, t1 + off])
        sents.append(dict(it, words=words, s=it["s"] + off, e=it["e"] + off))
    return vo, sents


def word_time(sents, phrase, para=None, which=0):
    ph = [re.sub(r"[^\w'-]", "", x).lower() for x in phrase.split()]
    hits = []
    for s in sents:
        if para is not None and s["para"] != para:
            continue
        norm = [re.sub(r"[^\w'-]", "", w).lower() for w, _, _ in s["words"]]
        for i in range(len(norm) - len(ph) + 1):
            if norm[i:i + len(ph)] == ph:
                hits.append(s["words"][i][1])
    if not hits:
        raise KeyError(phrase)
    return hits[which]


class Captions:
    """Chunks of up to 16 characters; the word being spoken turns yellow and grows a little."""

    def __init__(self, sents, repl=(), y=1340, size=82, hide=()):
        words = []
        for s in sents:
            ws = [(w, a, b) for w, a, b in s["words"]]
            ws = self._repl(ws, repl)
            words += [list(w) + [s["e"]] for w in ws]
        self.chunks = []
        cur = []
        for w in words:
            cand = " ".join(x[0] for x in cur + [w])
            if cur and (len(cand) > 16 or re.search(r"[.?!:]$", cur[-1][0])):
                self.chunks.append(cur)
                cur = []
            cur.append(w)
        if cur:
            self.chunks.append(cur)
        self.y, self.size, self.hide = y, size, hide
        self.cache = {}

    @staticmethod
    def _repl(ws, repl):
        out, i = [], 0
        norm = [re.sub(r"[^\w'-]", "", w).lower() for w, _, _ in ws]
        while i < len(ws):
            for sp, disp in repl:
                k = len(sp.split())
                if norm[i:i + k] == [x.lower() for x in sp.split()]:
                    trail = re.findall(r"[^\w'-]+$", ws[i + k - 1][0])
                    out.append((disp + (trail[0] if trail else ""), ws[i][1], ws[i + k - 1][2]))
                    i += k
                    break
            else:
                out.append(ws[i])
                i += 1
        return out

    def img(self, word, active):
        key = (word, active)
        if key not in self.cache:
            col = YELLOW if active else (255, 255, 255)
            lay = txt(word, "inter_k", self.size, col, stroke=8)
            if active:
                lay = cv2.resize(lay, (int(lay.shape[1] * 1.08), int(lay.shape[0] * 1.08)),
                                 interpolation=cv2.INTER_LINEAR)
            self.cache[key] = lay
        return self.cache[key]

    def draw(self, frame, t):
        for t0, t1 in self.hide:
            if t0 <= t < t1:
                return
        cur = None
        for c in self.chunks:
            if c[0][1] - 0.05 <= t:
                cur = c
        if cur is None or t > cur[-1][2] + 0.5 or t > cur[-1][3] + 0.35:
            return
        parts = []
        for w, a, b, _ in cur:
            parts.append(self.img(w, a - 0.02 <= t < b + 0.02))
        space = int(self.size * 0.22)
        total = sum(p.shape[1] for p in parts) + space * (len(parts) - 1) - 16 * len(parts)
        scale = min(1.0, (VW - 100) / max(1, total))
        x = (VW - total * scale) / 2
        pop = min(1.0, (t - cur[0][1] + 0.05) / 0.12)
        a = max(0.2, pop)
        for p in parts:
            if scale < 1:
                p = cv2.resize(p, (int(p.shape[1] * scale), int(p.shape[0] * scale)), interpolation=cv2.INTER_AREA)
            paste(frame, p, x - 8 * scale, self.y, a=a, anchor="lm")
            x += p.shape[1] + space * scale - 16 * scale


# ----------------------------------------------------------------------------- the double-tap card

class DoubleTap:
    def __init__(self, t0, line1, line2=None, t1=None, y=820):
        self.t0, self.t1, self.y = t0, t1, y
        self.big = txt("DOUBLE-TAP", "inter_k", 132, (255, 255, 255), shadow=1.0)
        self.l1 = txt(line1, "lora", 70, BONE, shadow=1.0, max_w=VW - 120)
        self.l2 = txt(line2, "inter_sb", 44, YELLOW, shadow=1.0, max_w=VW - 120) if line2 else None
        self.heart = heart(190)

    def draw(self, frame, t):
        if t < self.t0 - 0.05:
            return
        a = sstep(self.t0, self.t0 + 0.35, t)
        if self.t1 is not None:
            a *= 1 - sstep(self.t1 - 0.3, self.t1, t)
        if a <= 0.003:
            return
        # darken behind the card
        frame *= 1 - 0.45 * a
        u = t - self.t0
        beat = 1 + 0.10 * max(0.0, math.sin(u * 2 * math.pi * 1.25)) ** 6
        pop = ease_out(sstep(0, 0.35, u))
        hs = 0.6 + 0.4 * pop
        hz = cv2.resize(self.heart, (int(190 * hs * beat), int(190 * hs * beat)), interpolation=cv2.INTER_LINEAR)
        paste(frame, hz, VW / 2, self.y - 210, a=a)
        paste(frame, self.big, VW / 2, self.y, a=a)
        paste(frame, self.l1, VW / 2, self.y + 120, a=a * sstep(self.t0 + 0.2, self.t0 + 0.5, t))
        if self.l2 is not None:
            paste(frame, self.l2, VW / 2, self.y + 205, a=a * sstep(self.t0 + 0.4, self.t0 + 0.7, t))


# ----------------------------------------------------------------------------- render + sound

def encode(path, n, make):
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                            "%dx%d" % (VW, VH), "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast",
                            "-crf", "19", "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", "60", path],
                           stdin=subprocess.PIPE)
    for f in range(n):
        fr = make(f / FPS)
        np.clip(fr, 0, 1, out=fr)
        enc.stdin.write((fr * 255 + 0.5).astype(np.uint8).tobytes())
        if f % 300 == 0:
            print("  frame %d/%d" % (f, n), flush=True)
    enc.stdin.close()
    enc.wait()


def preview(make, times, name):
    outs = []
    for t in times:
        fr = make(t)
        np.clip(fr, 0, 1, out=fr)
        outs.append((fr * 255 + 0.5).astype(np.uint8))
    small = [cv2.resize(o, (360, 640), interpolation=cv2.INTER_AREA) for o in outs]
    rows = [np.concatenate(small[i:i + 6] + [np.zeros_like(small[0])] * (6 - len(small[i:i + 6])), 1)
            for i in range(0, len(small), 6)]
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + "_preview.jpg")
    cv2.imwrite(p, cv2.cvtColor(np.concatenate(rows, 0), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 86])
    for i, o in enumerate(outs):
        cv2.imwrite(os.path.join(OUT, "%s_pf_%d.jpg" % (name, i)), cv2.cvtColor(o, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 90])
    return p


class Mix:
    def __init__(self, dur):
        self.n = int(dur * SR)
        self.voice = np.zeros((self.n, 2), np.float32)
        self.music = np.zeros((self.n, 2), np.float32)
        self.amb = np.zeros((self.n, 2), np.float32)
        self.fx = np.zeros((self.n, 2), np.float32)

    def add(self, bus, sig, t, g=0.0):
        if sig.ndim == 1:
            sig = np.stack([sig, sig], 1)
        i = int(t * SR)
        if i < 0:
            sig = sig[-i:]
            i = 0
        m = min(len(sig), self.n - i)
        if m > 0:
            getattr(self, bus)[i:i + m] += sig[:m] * SH.db(g)

    def voiceover(self, vo_dir, off=0.0):
        import sfx as X
        vo, vsr = sf.read(os.path.join(vo_dir, "vo.wav"), dtype="float32")
        vo = X.hp(resample_poly(vo, SR // vsr, 1).astype(np.float32), 70)
        vo *= SH.db(-3.0) / np.abs(vo).max()
        self.add("voice", vo, off)

    def score(self, prog_key=11, seed=0, motif_at=None, drone_g=-27, pad_g=-25):
        import sfx as X
        import audio as AU
        dur = self.n / SR
        dr = X.drone(dur + 2, seed=180 + seed)
        e = np.ones(len(dr), np.float32)
        e[:int(1.5 * SR)] = np.linspace(0, 1, int(1.5 * SR))
        self.add("music", dr * e[:, None], 0.0, drone_g)
        prog = AU.PROG[prog_key]
        d = (dur - 0.5) / len(prog)
        for k, chord in enumerate(prog):
            p = X.pad(d + 3.0, [AU.N[c] for c in chord], seed=400 + seed * 7 + k, attack=2.0, release=2.5)
            self.add("music", p, max(0.0, k * d - 0.8), pad_g)
        if motif_at is not None:
            self.add("music", AU.motif(6, 0.42), motif_at, -19)

    def finish(self, spans, path, target=-14.0):
        env = SH.duck_env(spans, self.n)
        x = self.voice + self.music * SH.db(2.0) * (1 - 0.55 * env) + self.amb * SH.db(5.0) * (1 - 0.40 * env) \
            + self.fx * (1 - 0.15 * env)
        fl = int(0.8 * SR)
        x[-fl:] *= np.linspace(1, 0, fl)[:, None]
        x[:int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
        return SH.loudnorm_write(x, path, target)


def mux(video, audio, out, title):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    "-metadata", "title=%s" % title, "-metadata", "artist=La Porte Weather Now", out], check=True)
