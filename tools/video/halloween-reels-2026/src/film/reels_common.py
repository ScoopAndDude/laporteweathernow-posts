"""Shared pieces for the four Facebook reels (Oct. 22, 2026).

The Belle reels reuse the Belle Gunness series' own drawing code (tools/video/belle-2026/shorts.py from the
posts repo) and the Daily Video's (scripts/video_render.py), so Parts 3 and 4 look and sound like Parts 1 and 2:
same sepia photos, shading, titles, word-by-word captions, header and progress bar, grain and flicker.
"""
import importlib.util
import json
import math
import os
import re
import subprocess
import sys

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import resample_poly

FILM = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FILM)
sys.path.insert(0, FILM)

import shorts as SH  # noqa: E402

BSRC = os.path.join(ROOT, "belle_src")
BREPO = os.path.join(ROOT, "belle_repo")
FONTS = os.path.join(ROOT, "doc", "fonts")
OUT = os.path.join(ROOT, "shorts", "out")
J = os.path.join


def _setup():
    def put(src, dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.lexists(dst):
            os.symlink(src, dst)
    put(J(BSRC, "video_render.py"), J(BREPO, "scripts", "video_render.py"))
    for f in ("Inter-Black.otf", "Inter-ExtraBold.otf", "Inter-Bold.otf", "Inter-SemiBold.otf", "Inter-Regular.otf"):
        put(J(FONTS, f), J(BREPO, "video", "fonts", f))
    put(J(ROOT, "doc", "logo-512.png"), J(BREPO, "video", "logo-512.png"))
    put(J(ROOT, "doc", "logo-mark.png"), J(BREPO, "video", "logo-mark.png"))
    put(J(BSRC, "halloween_make.py"), J(BREPO, "tools", "video", "halloween-2026", "make.py"))
    bdir = J(BREPO, "tools", "video", "belle-2026")
    put(J(BSRC, "shorts.py"), J(bdir, "shorts.py"))
    vj = J(bdir, "voice", "voice.json")
    if not os.path.exists(vj):
        os.makedirs(os.path.dirname(vj), exist_ok=True)
        json.dump({"lines": []}, open(vj, "w"))
    for f in os.listdir(J(BSRC, "images")):
        put(J(BSRC, "images", f), J(bdir, "images", f))
    put(J(BSRC, "manifest.json"), J(bdir, "images", "manifest.json"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_setup()
bs = _load("belle_shorts", J(BREPO, "tools", "video", "belle-2026", "shorts.py"))
bs.LORA = J(FONTS, "Lora-Variable.ttf")
vr = bs.vr
hw = bs.hw

W, H, FPS, SR = bs.W, bs.H, bs.FPS, 48000
X0, CW = bs.X0, bs.CW
BONE, SEPIA, INKC, BLOOD, EMBER = bs.BONE, bs.SEPIA, bs.INKC, bs.BLOOD, bs.EMBER
RED = (242, 64, 52)
GOLD = vr.GOLD
YELLOW = (255, 214, 72)

# ----------------------------------------------------------------------------- type

EXTRA = {"oldst": "OldStandard-Regular.ttf", "oldst_b": "OldStandard-Bold.ttf", "fell": "IMFeENrm28P.ttf",
         "fell_it": "IMFeENit28P.ttf", "fell_sc": "IMFeENsc28P.ttf", "typew": "SpecialElite.ttf"}


def font(kind, size):
    key = (kind, int(size))
    if key not in bs._fc:
        if kind == "lora_r":
            f = ImageFont.truetype(bs.LORA, int(size))
            f.set_variation_by_name(b"Regular")
        elif kind == "lora_sb":
            f = ImageFont.truetype(bs.LORA, int(size))
            f.set_variation_by_name(b"SemiBold")
        elif kind in EXTRA:
            f = ImageFont.truetype(J(FONTS, EXTRA[kind]), int(size))
        else:
            return bs.F(kind, size)
        bs._fc[key] = f
    return bs._fc[key]


def T(text, kind, size, fill, **kw):
    font(kind, size)
    fill = tuple(fill) if len(fill) == 4 else tuple(fill) + (255,)
    return bs.T(text, kind, int(size), fill, **kw)


def fitT(text, kind, size, fill, max_w=CW, min_size=30, **kw):
    s = int(size)
    tr = kw.get("tracking", 0)
    while s > min_size and font(kind, s).getlength(text) + tr * max(0, len(text) - 1) > max_w:
        s -= 2
    return T(text, kind, s, fill, **kw)


def glow(img, color, radius=26, strength=0.75):
    return bs.glowT(img, color, radius=radius, strength=strength)[0]


def alpha(img, a):
    return vr.with_alpha(img, max(0.0, min(1.0, a)))


def paste(frame, img, cx, cy, a=1.0):
    if a > 0.003:
        frame.alpha_composite(alpha(img, a) if a < 0.999 else img,
                              (int(round(cx - img.width / 2)), int(round(cy - img.height / 2))))


def paste_lt(frame, img, x, y, a=1.0):
    if a > 0.003:
        frame.alpha_composite(alpha(img, a) if a < 0.999 else img, (int(round(x)), int(round(y))))


def scaled(img, s):
    if abs(s - 1) < 1e-3:
        return img
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def appear(t, at, dur=0.28):
    return ease_out((t - at) / dur) if t >= at else 0.0


def window(t, t0, t1, fin=0.25, fout=0.25):
    return appear(t, t0, fin) * (1 - ease((t - (t1 - fout)) / fout)) if t1 is not None else appear(t, t0, fin)


def dim(frame, a):
    if a > 0.003:
        frame.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * min(1.0, a)))))


def heart(size, color=(232, 40, 60)):
    S = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    t = np.linspace(0, 2 * math.pi, 400)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    pts = list(zip(S / 2 + x * S / 36, S / 2 - y * S / 36 - S * 0.02))
    ImageDraw.Draw(img).polygon(pts, fill=tuple(color) + (255,))
    return img.resize((size, size), Image.LANCZOS)


def ring(r, width, color, a):
    S = 4
    img = Image.new("RGBA", (int(2 * r + 2 * width + 4) * S,) * 2, (0, 0, 0, 0))
    c = img.width / 2
    ImageDraw.Draw(img).ellipse((c - r * S, c - r * S, c + r * S, c + r * S), outline=tuple(color) + (int(255 * a),),
                                width=int(width * S))
    return img.resize((img.width // S, img.height // S), Image.LANCZOS)


class DoubleTap:
    """The end card: two taps, a heart that pops on the second, DOUBLE-TAP and what's next."""

    def __init__(self, line1, line2=None, color1=RED, glow1=(140, 0, 0), y=560, size1=150, kind1="lora"):
        self.heart = heart(230)
        self.halo = glow(self.heart, (255, 40, 60), radius=34, strength=0.8)
        self.big = glow(T("DOUBLE-TAP", "black", 132, (255, 255, 255)), (0, 0, 0), radius=24, strength=0.9)
        self.l1 = glow(fitT(line1, kind1, size1, color1, max_w=CW + 40, min_size=60), glow1, radius=30, strength=0.85)
        self.l2 = glow(fitT(line2, "lora", 58, BONE, max_w=CW + 40, min_size=34), (0, 0, 0), radius=18,
                       strength=0.9) if line2 else None
        self.y = y
        self.taps = (0.12, 0.42)

    def draw(self, frame, u):
        dim(frame, 0.42 * appear(u, 0.0, 0.35))
        y = self.y
        for tap in self.taps:                       # the finger's two taps: rings spreading out
            k = (u - tap) / 0.45
            if 0 <= k <= 1:
                paste(frame, ring(60 + 120 * k, 6, (255, 255, 255), 0.75 * (1 - k)), W / 2, y)
        if u >= self.taps[1]:
            k = u - self.taps[1]
            pop = 1.25 - 0.25 * ease_out(k / 0.18) if k < 0.18 else 1.0
            beat = 1 + 0.07 * max(0.0, math.sin((k - 0.3) * 2 * math.pi * 1.1)) ** 8 if k > 0.3 else 1.0
            paste(frame, scaled(self.halo, pop * beat), W / 2, y, min(1.0, k / 0.08))
        paste(frame, self.big, W / 2, y + 230, appear(u, 0.25, 0.25))
        paste(frame, self.l1, W / 2, y + 390, appear(u, 0.5, 0.25))
        if self.l2 is not None:
            paste(frame, self.l2, W / 2, y + 525, appear(u, 0.75, 0.3))


# ----------------------------------------------------------------------------- the narration and its word times

# Some written words take longer to say than their letters suggest.
WEIGHT = {"1908": 4.35, "1815": 4.7, "1931": 5.0, "1897": 5.0, "1816": 4.7, "mid-1900s": 5.35, "Mrs": 2.35}
_ww = SH.word_weight


def _word_weight(w):
    core = re.sub(r"[^\w'-]", "", w)
    if core in WEIGHT:
        return WEIGHT[core]
    return _ww(w)


SH.word_weight = _word_weight


def norm(w):
    return re.sub(r"[^\w'-]", "", w).lower()


class Reel:
    def __init__(self, name, tail=0.6):
        self.name = name
        d = J(ROOT, "shorts", "r_" + name)
        vo = json.load(open(J(d, "vo.json")))
        self.vo, self.vsr = sf.read(J(d, "vo.wav"), dtype="float32")
        self.items = vo["items"]
        self.words = []
        for it in self.items:
            seg = self.vo[int(it["s"] * self.vsr):int(it["e"] * self.vsr)]
            pz = SH.detect_pauses(seg, self.vsr, it["s"])
            wt = SH.word_times(it["text"], it["s"], it["e"], pz)
            for k, (w, t0) in enumerate(wt):
                t1 = wt[k + 1][1] if k + 1 < len(wt) else it["e"]
                self.words.append([w, round(t0, 3), round(t1, 3)])
        self.dur = self.items[-1]["e"] + tail
        self.n = int(math.ceil(self.dur * FPS))

    def at(self, phrase, after=0.0):
        ph = [norm(x) for x in phrase.split()]
        for i in range(len(self.words)):
            if self.words[i][1] + 1e-6 < after:
                continue
            if [norm(w[0]) for w in self.words[i:i + len(ph)]] == ph:
                return self.words[i][1]
        raise KeyError(phrase)

    def end(self, phrase, after=0.0):
        ph = phrase.split()
        t = self.at(phrase, after)
        i = [k for k, w in enumerate(self.words) if abs(w[1] - t) < 1e-6][0]
        return self.words[i + len(ph) - 1][2]

    def para(self, p):
        its = [it for it in self.items if it["para"] == p]
        return its[0]["s"], its[-1]["e"]

    def bars(self):
        """Progress-bar segments: one per paragraph, each running to the next paragraph's start."""
        ps = sorted(set(it["para"] for it in self.items))
        starts = [0.0] + [self.para(p)[0] - 0.15 for p in ps[1:]]
        ends = starts[1:] + [self.dur]
        return [{"start": a, "dur": b - a} for a, b in zip(starts, ends)]


# ----------------------------------------------------------------------------- scenes and the frame loop

class Scene:
    def __init__(self, t0, t1, draw, prep=None, flicker=None):
        self.t0, self.t1, self.draw, self.prep = t0, t1, draw, prep
        self.flicker = flicker
        self.ctx = {}
        self.ready = False


class Film:
    def __init__(self, reel, scenes, theme="photo", flashes=(), flicker=0.6, captions=True, label=None,
                 base=(8, 8, 10), atmos=None):
        self.reel, self.scenes, self.flashes = reel, scenes, list(flashes)
        self.flicker, self.captions, self.label = flicker, captions, label
        self.atm = atmos or bs.Atmos(tint=(196, 196, 204), fog=0.16, vignette=0.75, grain=16, seed=2)
        self.brand = vr.brand_row()
        self.bars = reel.bars()
        self.base = Image.new("RGBA", (W, H), tuple(base) + (255,))

    def scene_at(self, t):
        idx = 0
        for i, sc in enumerate(self.scenes):
            if t >= sc.t0 - 1e-9:
                idx = i
        sc = self.scenes[idx]
        if not sc.ready:
            if sc.prep:
                sc.prep(sc.ctx)
            sc.ready = True
        return sc

    def frame(self, t):
        f = self.base.copy()
        sc = self.scene_at(t)
        sc.draw(f, t - sc.t0, t, sc.ctx)
        f.alpha_composite(self.brand, (0, 175))
        if self.label is not None:
            self.label(f, t)
        if self.captions:
            bs.caption(f, self.reel.words, t)
        vr.progress(f, self.bars, t, self.reel.dur)
        flash = max([bs.lightning(t, at, length) for at, length in self.flashes] + [0.0])
        fl = self.flicker if sc.flicker is None else sc.flicker
        self.atm.finish(f, t, flicker=fl, flash=flash)
        return f

    def stills(self, times, name):
        os.makedirs(OUT, exist_ok=True)
        imgs = []
        for t in times:
            imgs.append(self.frame(t).convert("RGB"))
        small = [im.resize((360, 640), Image.LANCZOS) for im in imgs]
        cols = 6
        rows = (len(small) + cols - 1) // cols
        sheet = Image.new("RGB", (360 * cols, 640 * rows), (0, 0, 0))
        for i, im in enumerate(small):
            sheet.paste(im, ((i % cols) * 360, (i // cols) * 640))
        p = J(OUT, "%s_preview.jpg" % name)
        sheet.save(p, quality=85)
        for i, im in enumerate(imgs):
            im.save(J(OUT, "%s_pf_%02d.jpg" % (name, i)), quality=90)
        return p

    def video(self, path, cover_t=0.5):
        n = self.reel.n
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
               "-profile:v", "high", "-g", str(FPS * 2), "-keyint_min", str(FPS * 2), "-sc_threshold", "0", path]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for i in range(n):
            t = i / FPS
            f = self.frame(t).convert("RGB")
            if abs(t - cover_t) < 0.5 / FPS:
                f.save(path.replace(".mp4", "-cover.jpg"), quality=92)
            proc.stdin.write(f.tobytes())
            if i % 150 == 0:
                print("  %s frame %d/%d" % (self.reel.name, i, n), flush=True)
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed")


# ----------------------------------------------------------------------------- sound

def voice48(reel):
    v = resample_poly(reel.vo, SR // reel.vsr, 1).astype(np.float32)
    return v


def soundtrack(reel, music, events, seed=5, music_gain=0.55, bed_gain=0.55, hit_gain=0.5, extra_bed=None):
    """The Belle series' mix: narrator first, the music and long sounds pulled down under her, short hits on top.
    music: a mono array (or a bs.music_bed kind); events: [(kind or array, time, gain)]"""
    rng = np.random.default_rng(seed)
    n = int((reel.dur + 0.3) * SR)
    if isinstance(music, str):
        music = bs.music_bed(music, reel.dur + 0.3, rng)
    music = np.pad(music, (0, max(0, n - len(music))))[:n]
    voice = np.zeros(n, np.float32)
    v = voice48(reel)
    voice[:min(n, len(v))] = v[:n]
    duck = np.ones(n, np.float32)
    for it in reel.items:
        duck[max(0, int((it["s"] - 0.12) * SR)):int(it["e"] * SR)] = 0.0
    bed = np.zeros(n, np.float32)
    hits = np.zeros(n, np.float32)
    if extra_bed is not None:
        bed[:min(n, len(extra_bed))] += extra_bed[:n]
    for ev in events:
        kind, at, g = ev[:3]
        snd = bs.sfx(kind, rng) if isinstance(kind, str) else kind
        snd = np.asarray(snd, np.float32)
        if snd.ndim > 1:
            snd = snd.mean(1)
        k = max(0, int((at - (0.22 if isinstance(kind, str) and kind == "whoosh" else 0.0)) * SR))
        m = min(n, k + len(snd))
        if m <= k:
            continue
        bus = ev[3] if len(ev) > 3 else ("bed" if (isinstance(kind, str) and kind in bs.BED_FX) else "hits")
        target = bed if bus == "bed" else hits
        target[k:m] += snd[:m - k] * g
    duck = bs.lowpass(duck, int(0.1 * SR))
    mix = (voice * 2.0 + music * (0.25 + 0.75 * duck) * music_gain + bed * (0.35 + 0.65 * duck) * bed_gain
           + hits * hit_gain)
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    fade = int(0.35 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / max(1e-6, float(np.max(np.abs(mix)))) * 0.92
    return mix.astype(np.float32)


def finish(reel, video_path, mix, out_path, title):
    wav = out_path.replace(".mp4", ".wav")
    I, gain = SH.loudnorm_write(np.stack([mix, mix], 1), wav, -14.0)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video_path, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", "%.3f" % (reel.n / FPS),
                    "-movflags", "+faststart", "-metadata", "title=%s" % title,
                    "-metadata", "artist=La Porte Weather Now", out_path], check=True)
    os.remove(wav)
    return I, gain


def measure(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null",
                        "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True).stdout.strip())
    return I, (float(tp[-1]) if tp else None), d


def patch_start(film, orig, path, n_new, cover_t=None):
    """Re-render the first n_new frames and keep the rest of an earlier render (decoded and re-encoded once)."""
    n = film.reel.n
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-g", str(FPS * 2), "-keyint_min", str(FPS * 2), "-sc_threshold", "0", path]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n_new):
        f = film.frame(i / FPS).convert("RGB")
        if cover_t is not None and abs(i / FPS - cover_t) < 0.5 / FPS:
            f.save(path.replace(".mp4", "-cover.jpg"), quality=92)
        enc.stdin.write(f.tobytes())
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", orig, "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-"], stdout=subprocess.PIPE)
    fs = W * H * 3
    i = 0
    while i < n:
        buf = dec.stdout.read(fs)
        if len(buf) < fs:
            break
        if i >= n_new:
            enc.stdin.write(buf)
        i += 1
    dec.stdout.close()
    dec.wait()
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return i
