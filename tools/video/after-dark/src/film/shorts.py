"""Vertical shorts (1080x1920) cut from "Before Pumpkins", for YouTube Shorts and Facebook Reels.

python3 shorts.py NAME [NAME ...]      names: a (60-second trailer), b (Martians), c (candy), d (La Porte)

Needs clean source footage from render_clips.py in shorts/src, the documentary mix in mix/,
and for "a" the new voice-over (short_vo.py) and the stems (STEMS=... audio.py).
"""
import json
import math
import os
import re
import subprocess
import sys

import cv2
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, lfilter

FILM = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FILM)
sys.path.insert(0, FILM)

from core import text_layer, text_mask, paste, rgb, GHOST, sstep, ease_out  # noqa: E402

VW, VH, FPS, SR = 1080, 1920, 24, 48000
WIN_Y0, WIN = 440, 1080
WIN_CY = WIN_Y0 + WIN // 2
CAP_Y = 1398
CAP_SIZE = 72
CAP_MAXW = 860
SRC = os.path.join(ROOT, "shorts", "src")
OUT = os.path.join(ROOT, "shorts", "out")
YELLOW = "#ffd34d"
CREAM = "#f1e4c6"
END_DUR = 3.0

FRAMING = {  # shot: (zoom, centre x as a fraction of the 16:9 frame)
    "radio_room": (1.0, 0.62), "bulletin": (0.75, 0.5), "papers": (0.85, 0.5), "xray": (0.8, 0.5),
    "zero": (0.62, 0.5), "papers2": (0.9, 0.47), "entrepreneur": (0.9, 0.5), "sky": (0.7, 0.5, -40),
    "belles": (1.0, 0.62), "outro": (1.0, 0.42), "ship": (1.0, 0.42), "fire1908": (1.0, 0.55),
    "tripod": (1.0, 0.55), "tripod2": (1.0, 0.55), "apple": (1.0, 0.48), "carving": (1.0, 0.45),
    "saucers": (0.80, 0.5, -40), "map_irl": (1.0, 0.45), "party_porch": (1.0, 0.5), "portrait": (0.85, 0.5, -60),
}

def fr3(name):
    f = FRAMING.get(name, (1.0, 0.5))
    return (f[0], f[1], f[2] if len(f) > 2 else 0.0)


# ---------------------------------------------------------------------------- the four shorts

A_EDL = [  # out0, out1, shot, src0, src1
    (0.00, 2.30, "match", 0.75, 3.05), (2.30, 4.20, "carving", 26.40, 28.30), (4.20, 6.95, "lanterns", 34.90, 37.65),
    (6.95, 11.50, "map_irl", 57.60, 62.15), (11.50, 16.70, "dolmen", 41.00, 46.20),
    (16.70, 20.25, "chair", 107.60, 111.15), (20.25, 23.85, "guisers_fire", 116.60, 120.20),
    (23.85, 26.95, "chapel", 160.60, 163.70), (26.95, 29.20, "morph", 207.90, 208.60),
    (29.20, 29.95, "morph", 208.60, 210.90), (29.95, 30.70, "morph", 210.90, 211.30),
    (30.70, 32.70, "mirror", 372.80, 374.80), (32.70, 37.60, "saucers", 354.70, 359.10),
    (37.60, 40.20, "ship", 402.00, 404.60), (40.20, 42.10, "patch", 421.00, 422.90),
    (42.10, 43.35, "jack1", 426.30, 427.55), (43.35, 46.80, "laporte", 760.00, 763.45),
    (46.80, 48.30, "portrait", 772.00, 773.50), (48.30, 51.30, "belles", 783.00, 786.00),
    (51.30, 55.00, "outro", 846.10, 849.80),
]

SHORTS = {
    "a": dict(
        title="Before Pumpkins", file="short-1-before-pumpkins.mp4", kind="vo",
        tags=[(0.0, 6.95, "THE REAL HISTORY OF HALLOWEEN"), (6.95, 10.3, "IRELAND & SCOTLAND"),
              (10.3, 16.7, "SAMHAIN \u00b7 SAY IT \u201cSOW-in\u201d"), (16.7, 23.85, "THE NIGHT THE DEAD CAME HOME"),
              (23.85, 30.7, "ALL HALLOWS\u2019 EVE"), (30.7, 37.6, "FORTUNES AND OMENS"),
              (37.6, 43.35, "THE 1840s \u00b7 IRELAND TO AMERICA"), (43.35, 51.3, "LA PORTE, INDIANA"),
              (51.3, 55.0, "FULL DOCUMENTARY ON OUR CHANNEL")],
        hl=["pumpkins", "turnips", "samhain", "dead", "halloween", "clay", "la porte", "belle gunness", "dare",
            "ugly", "ireland", "scotland", "october 31st", "all hallows\u2019 eve", "all saints\u2019 day"],
        repl=[("October thirty-first", "October 31st"), ("November first", "November 1st")],
    ),
    "b": dict(
        title="The Night the Martians Came", file="short-2-the-night-the-martians-came.mp4", kind="clip",
        t0=522.40, src_end=568.80, section=7, audio_end=571.80,
        tags=[(523.36, 529.18, "OCTOBER 30, 1938"), (529.73, 537.79, "CBS RADIO \u00b7 ORSON WELLES"),
              (544.82, 547.6, "GROVERS MILL, NEW JERSEY")],
        hl=["1938", "halloween", "radios", "martians", "new jersey", "grovers mill", "panicked", "twist", "invaded",
            "orson welles", "news", "legend"],
        repl=[("nineteen thirty-eight", "1938")],
    ),
    "c": dict(
        title="Poison in the Candy Bag", file="short-3-poison-in-the-candy-bag.mp4", kind="clip",
        t0=643.40, src_end=712.40, section=9, audio_end=715.20,
        tags=[(663.74, 673.66, "DEER PARK, TEXAS \u00b7 1974"), (691.26, 697.86, "JOEL BEST \u00b7 SOCIOLOGIST")],
        hl=["poison", "x-rays", "1974", "cyanide", "father", "executed", "not one", "stranger", "home",
            "razor blades", "nightmare", "story"],
        repl=[("nineteen-sixties", "1960s"), ("nineteen seventy-four", "1974"), ("eight-year-old", "8-year-old"),
              ("nineteen eighty-four", "1984")],
    ),
    "d": dict(
        title="La Porte\u2019s Halloween", file="short-4-la-portes-halloween.mp4", kind="clip",
        t0=758.75, src_end=819.40, section=11, audio_end=820.30, sting=True,
        tags=[(759.79, 763.9, "LA PORTE, INDIANA"), (764.05, 771.22, "McCLUNG ROAD \u00b7 APRIL 28, 1908"),
              (805.0, 818.6, "HALLOWEEN \u00b7 SATURDAY, OCT. 31")],
        hl=["la porte", "indiana", "1908", "belle gunness", "belles", "entrepreneur", "5:44", "10:40", "dark",
            "head", "party", "saturday"],
        repl=[("nineteen-oh-eight", "1908"), ("three-foot-tall", "3-foot-tall"), ("five forty-four", "5:44"),
              ("about ten forty", "about 10:40")],
    ),
}


# ---------------------------------------------------------------------------- word timing

def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    if not w:
        return 1
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ee", "ye")):
        n -= 1
    return max(1, n)


def word_weight(w):
    core = re.sub(r"[^\w'-]", "", w)
    if re.fullmatch(r"[A-Z]{2,}", core):          # initials, e.g. CBS
        return len(core) * 0.9 + 0.3
    return sum(syllables(p) for p in re.split(r"-", core) if p) + 0.35


def ends_phrase(w):
    return bool(re.search(r"(\.\.\.|[,;:.!?\u2026])[\"\u201d']?$", w))


def detect_pauses(audio, sr, t_off, min_len=0.09):
    """Quiet stretches inside a stretch of speech; returns absolute (start, end) times."""
    win = int(sr * 0.01)
    n = len(audio) // win
    if n < 5:
        return []
    rms = np.sqrt((audio[:n * win].reshape(n, win) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    thr = np.median(db) - 22
    quiet = db < thr
    out = []
    i = 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= min_len and i > 3 and j < n - 3:
                out.append((t_off + i * 0.01, t_off + j * 0.01))
            i = j
        else:
            i += 1
    return out


def word_times(text, t0, t1, pauses):
    """Spread the words of one stretch of speech over [t0, t1], lining phrase breaks up with real pauses."""
    words = text.split()
    wts = [word_weight(w) for w in words]
    cum = np.cumsum([0.0] + wts)
    tot = cum[-1]
    brk = [i for i, w in enumerate(words[:-1]) if ends_phrase(w)]
    est = {i: t0 + (t1 - t0) * cum[i + 1] / tot for i in brk}
    assigned = {}
    for p in sorted(pauses, key=lambda p: -(p[1] - p[0])):
        mid = (p[0] + p[1]) / 2
        cands = [i for i in brk if i not in assigned]
        if not cands:
            break
        i = min(cands, key=lambda i: abs(est[i] - mid))
        if abs(est[i] - mid) < 0.9:
            assigned[i] = p
    # keep the assignment in order
    keep, last = {}, -1.0
    for i in sorted(assigned):
        if assigned[i][0] > last:
            keep[i] = assigned[i]
            last = assigned[i][1]
    # speech runs between the pauses
    starts = [0.0] * len(words)
    runs, a, ta = [], 0, t0
    for i in sorted(keep):
        runs.append((a, i + 1, ta, keep[i][0]))
        a, ta = i + 1, keep[i][1]
    runs.append((a, len(words), ta, t1))
    for a, b, ta, tb in runs:
        w = wts[a:b]
        tw = sum(w)
        c = ta
        for k in range(a, b):
            starts[k] = c
            c += (tb - ta) * wts[k] / tw
    return list(zip(words, starts))


def apply_repl(tokens, repl):
    out, i = [], 0
    norm = [re.sub(r"[^\w'-]", "", w).lower() for w, _ in tokens]
    while i < len(tokens):
        for sp, disp in repl:
            k = len(sp.split())
            if norm[i:i + k] == [x.lower() for x in sp.split()]:
                trail = re.findall(r"[^\w'-]+$", tokens[i + k - 1][0])
                out.append((disp + (trail[0] if trail else ""), tokens[i][1]))
                i += k
                break
        else:
            out.append(tokens[i])
            i += 1
    return out


def make_chunks(tokens, end_time, maxw=3, maxc=18):
    """Group words into caption chunks. Returns [(words [(w, t)], t_show, t_hide)]."""
    chunks, cur = [], []
    for w, t in tokens:
        if cur and len(" ".join(x for x, _ in cur + [(w, t)])) > maxc:
            chunks.append(cur)
            cur = []
        cur.append((w, t))
        if len(cur) >= maxw or ends_phrase(w):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    # fold a lone short word into the chunk before it
    merged = []
    for c in chunks:
        if merged and len(c) == 1 and len(c[0][0]) <= 4 and not ends_phrase(merged[-1][-1][0]) \
                and len(" ".join(x for x, _ in merged[-1] + c)) <= maxc + 5:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    out = []
    for k, c in enumerate(merged):
        show = c[0][1]
        hide = merged[k + 1][0][1] if k + 1 < len(merged) else end_time + 0.25
        out.append((c, show, hide))
    return out


# ---------------------------------------------------------------------------- drawing helpers

def is_hl(word_seq, i, hl):
    """True if the word at i starts or sits inside a highlighted phrase."""
    norm = [re.sub(r"[^\w'\u2019:-]", "", w).lower().replace("'", "\u2019") for w in word_seq]
    for ph in hl:
        p = ph.lower().replace("'", "\u2019").split()
        for s in range(max(0, i - len(p) + 1), i + 1):
            if norm[s:s + len(p)] == p:
                return True
    return False


class Caption:
    """One chunk of words, rendered once; words fade in as they are spoken."""

    def __init__(self, words, show, hide, hl):
        self.show, self.hide = show, hide
        self.times = [t for _, t in words]
        txt = [w for w, _ in words]
        line = " ".join(txt)
        white = text_layer(line, "sans_x", CAP_SIZE, "#ffffff", shadow=1.0)
        yel = text_layer(line, "sans_x", CAP_SIZE, YELLOW, shadow=1.0)
        padn = int(CAP_SIZE * 0.9)
        ink0 = padn + 2
        # right edge of each word's ink, measured on growing prefixes
        bounds = []
        for k in range(1, len(txt) + 1):
            m = text_mask(" ".join(txt[:k]), "sans_x", CAP_SIZE)
            bounds.append(ink0 + m.shape[1] - 4)
        h, w = white.shape[:2]
        from core import font
        space = font("sans_x", CAP_SIZE).getlength(" ")
        self.word_of_col = np.zeros(w, np.int32)
        cols = np.arange(w)
        for k in range(len(bounds) - 1):
            self.word_of_col[cols >= bounds[k] + space / 2] = k + 1
        use_y = np.array([is_hl(txt, k, hl) for k in range(len(txt))])
        pick = use_y[self.word_of_col][None, :, None]
        layer = np.where(pick, yel, white)
        scale = min(1.0, (CAP_MAXW + 2 * padn) / w)
        if scale < 1.0:
            layer = cv2.resize(layer, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            self.word_of_col = self.word_of_col[(np.arange(layer.shape[1]) / scale).astype(int).clip(0, w - 1)]
        self.layer = layer.astype(np.float32)

    def draw(self, frame, t):
        if t < self.show - 0.02 or t > self.hide:
            return
        a_out = 1.0 - sstep(self.hide - 0.08, self.hide, t)
        alphas = np.array([sstep(tw - 0.03, tw + 0.07, t) for tw in self.times], np.float32) * a_out
        if alphas.max() <= 0.001:
            return
        col_a = alphas[self.word_of_col][None, :, None]
        rise = 8 * (1 - ease_out(sstep(self.show - 0.03, self.show + 0.15, t)))
        paste(frame, self.layer * col_a, VW / 2, CAP_Y + rise)


def rounded_logo(h=60, r=10):
    im = cv2.imread(os.path.join(ROOT, "doc", "logo-mark.png"))[:, :, ::-1].astype(np.float32) / 255
    w = int(round(im.shape[1] * h / im.shape[0]))
    im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
    m = np.zeros((h * 4, w * 4), np.uint8)
    cv2.rectangle(m, (r * 4, 0), (w * 4 - r * 4, h * 4), 255, -1)
    cv2.rectangle(m, (0, r * 4), (w * 4, h * 4 - r * 4), 255, -1)
    for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(m, (cx * 4, cy * 4), r * 4, 255, -1)
    a = cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    out = np.zeros((h, w, 4), np.float32)
    out[..., :3] = im * a[..., None]
    out[..., 3] = a
    return out


def big_logo(h=300):
    from PIL import Image
    im = np.asarray(Image.open(os.path.join(ROOT, "doc", "logo-512.png")).convert("RGB"), np.float32) / 255
    im = cv2.resize(im, (h, h), interpolation=cv2.INTER_AREA)
    r = 28
    m = np.zeros((h * 4, h * 4), np.uint8)
    cv2.rectangle(m, (r * 4, 0), (h * 4 - r * 4, h * 4), 255, -1)
    cv2.rectangle(m, (0, r * 4), (h * 4, h * 4 - r * 4), 255, -1)
    for cx, cy in ((r, r), (h - r, r), (r, h - r), (h - r, h - r)):
        cv2.circle(m, (cx * 4, cy * 4), r * 4, 255, -1)
    a = cv2.resize(m, (h, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    out = np.zeros((h, h, 4), np.float32)
    out[..., :3] = im * a[..., None]
    out[..., 3] = a
    return out


def progress_bar(frame, p, n_seg, a=1.0):
    """Story-style bar: n segments, filled up to fraction p of the whole short."""
    x0, x1, y, gap = 70, 1010, 170, 10
    seg_w = (x1 - x0 - gap * (n_seg - 1)) / n_seg
    for k in range(n_seg):
        sx0 = x0 + k * (seg_w + gap)
        sx1 = sx0 + seg_w
        cv2.line(frame, (int(sx0), y), (int(sx1), y), tuple(float(c) * a for c in (0.33, 0.33, 0.33)), 5, cv2.LINE_AA)
        f = np.clip(p * n_seg - k, 0, 1)
        if f > 0:
            col = (0.83, 0.60, 0.12) if f < 1 else (0.86, 0.83, 0.77)
            cv2.line(frame, (int(sx0), y), (int(sx0 + seg_w * f), y), tuple(float(c) * a for c in col), 5,
                     cv2.LINE_AA)


class Reader:
    """Reads a clip's frames forward only."""

    def __init__(self, path):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                  stdout=subprocess.PIPE, bufsize=10 ** 8)
        self.i = -1
        self.cur = None

    def get(self, idx):
        while self.i < idx:
            buf = self.p.stdout.read(1920 * 1080 * 3)
            if len(buf) < 1920 * 1080 * 3:
                break
            self.cur = np.frombuffer(buf, np.uint8).reshape(1080, 1920, 3)
            self.i += 1
        return self.cur

    def close(self):
        self.p.stdout.close()
        self.p.terminate()


def compose_base(src, zoom, cx, dy=0.0):
    """Blurred backdrop plus the sharp picture window, as float RGB."""
    small = cv2.resize(src[:, 656:1264], (54, 96), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    small = cv2.GaussianBlur(small, (0, 0), 2.2)
    bg = cv2.resize(small, (VW, VH), interpolation=cv2.INTER_CUBIC) * 0.30
    zoom = max(0.5625, min(1.0, zoom))
    vis_w = VW / zoom
    x0 = cx * 1920 - vis_w / 2
    x0 = max(0.0, min(1920 - vis_w, x0))
    crop = src[:, int(round(x0)):int(round(x0 + vis_w))]
    h = int(round(1080 * zoom))
    sharp = cv2.resize(crop, (VW, h), interpolation=cv2.INTER_AREA if zoom < 1 else cv2.INTER_LINEAR)
    sharp = sharp.astype(np.float32) / 255
    y0 = int(round(WIN_CY - h // 2 + dy))
    y0 = max(0, min(VH - h, y0))
    fe = 80
    yy = np.arange(h, dtype=np.float32)
    a = np.clip(np.minimum(yy, h - 1 - yy) / fe, 0, 1)
    a = (a * a * (3 - 2 * a))[:, None, None]
    bg[y0:y0 + h] = bg[y0:y0 + h] * (1 - a) + sharp * a
    return bg


VIG = None


def vignette_v():
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
        d = np.sqrt(((xx - VW / 2) / (VW / 2)) ** 2 * 0.6 + ((yy - VH * 0.48) / (VH / 2)) ** 2)
        VIG = (1 - 0.35 * np.clip(d, 0, 1.4) ** 2.2)[..., None].astype(np.float32)
        VIG[:440] *= np.linspace(0.75, 1.0, 440, dtype=np.float32)[:, None, None]
    return VIG


# ---------------------------------------------------------------------------- audio

def db(g):
    return 10 ** (g / 20.0)


def duck_env(spans, n, attack=0.15, release=0.8):
    cr = 100
    nc = int(n / SR * cr) + 2
    act = np.zeros(nc, np.float32)
    for s, e in spans:
        act[int(max(0, s) * cr):int(max(0, e) * cr)] = 1
    up = lfilter([1 - math.exp(-1 / (attack * cr))], [1, -math.exp(-1 / (attack * cr))], act)
    down = lfilter([1 - math.exp(-1 / (release * cr))], [1, -math.exp(-1 / (release * cr))], act)
    env = np.maximum(up, down).astype(np.float32)
    return np.interp(np.arange(n) / SR * cr, np.arange(nc), env).astype(np.float32)[:, None]


def read_range(path, t0, t1):
    info = sf.info(path)
    i0, i1 = int(round(t0 * info.samplerate)), int(round(t1 * info.samplerate))
    x, _ = sf.read(path, start=max(0, i0), stop=i1, dtype="float32", always_2d=True)
    if i0 < 0:
        x = np.concatenate([np.zeros((-i0, x.shape[1]), np.float32), x])
    want = i1 - i0
    if len(x) < want:
        x = np.concatenate([x, np.zeros((want - len(x), x.shape[1]), np.float32)])
    return x


def fade(x, fin, fout):
    n = len(x)
    e = np.ones(n, np.float32)
    a, b = int(fin * SR), int(fout * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if b:
        e[n - b:] = np.minimum(e[n - b:], np.linspace(1, 0, b))
    return x * e[:, None]


def end_sting(n_total, at):
    import sfx as X
    import audio as AU
    out = np.zeros((n_total, 2), np.float32)

    def add(sig, t, g):
        if sig.ndim == 1:
            sig = np.stack([sig, sig], 1)
        o = int(t * SR)
        m = min(len(sig), n_total - o)
        if m > 0:
            out[o:o + m] += sig[:m] * db(g)
    add(X.boom(seed=31, f0=70, f1=30, dur=2.5), at + 0.05, -14)
    add(AU.motif(5, 0.45), at + 0.4, -18)
    return out


def build_audio(name, cfg, dur, vo_spans=None):
    n = int(round(dur * SR))
    if cfg["kind"] == "clip":
        t0 = cfg["t0"]
        x = read_range(os.path.join(ROOT, "mix", "mix.wav"), t0, t0 + dur)
        stop = cfg["audio_end"] - t0
        e = np.ones(n, np.float32)
        i_stop = min(n, int(stop * SR))
        f_len = int(0.9 * SR)
        e[max(0, i_stop - f_len):i_stop] = np.linspace(1, 0, i_stop - max(0, i_stop - f_len))
        e[i_stop:] = 0
        x = x * e[:, None]
        x = fade(x, 0.06, 0.0)
        if cfg.get("sting"):
            x += end_sting(n, dur - END_DUR)
        return x
    # "a": new voice-over over the documentary's music and ambience
    vo, vsr = sf.read(os.path.join(ROOT, "shorts", "a_vo", "vo.wav"), dtype="float32")
    vo = resample_poly(vo, SR // vsr, 1).astype(np.float32)
    import sfx as X
    vo = X.hp(vo, 70)
    vo *= db(-3.0) / np.abs(vo).max()
    voice = np.zeros((n, 2), np.float32)
    m = min(n, len(vo))
    voice[:m] = vo[:m, None]
    stems = os.path.join(ROOT, "mix", "stems")
    # music: the cold open's bed, with its last stretch reused to reach the end
    mus = np.zeros((n, 2), np.float32)
    cut = 47.2
    xf = 1.5
    a_ = read_range(os.path.join(stems, "music.wav"), 0.0, cut + xf)
    mus[:len(a_)] += fade(a_, 0.0, xf)[:n]
    b_ = read_range(os.path.join(stems, "music.wav"), 36.4, 36.4 + (dur - cut))
    b_ = fade(b_, xf, 1.5)
    o = int(cut * SR)
    mus[o:o + len(b_)] += b_[:n - o]
    # ambience and effects follow the pictures
    amb = np.zeros((n, 2), np.float32)
    xf2 = 0.12
    for out0, out1, shot, s0, s1 in A_EDL:
        if shot == "morph" and out0 > 27:
            continue
        o1 = out1
        if shot == "morph":
            o1 = 30.70
        seg = read_range(os.path.join(stems, "ambfx.wav"), s0 - xf2, s0 + (o1 - out0) + xf2)
        seg = fade(seg, xf2 * 2, xf2 * 2)
        oo = int((out0 - xf2) * SR)
        if oo < 0:
            seg = seg[-oo:]
            oo = 0
        mm = min(len(seg), n - oo)
        amb[oo:oo + mm] += seg[:mm]
    env = duck_env(vo_spans, n)
    x = voice + mus * (1 - 0.55 * env) + amb * (1 - 0.30 * env)
    # a hit on "Pumpkins." and a sting under the end card
    add = np.zeros((n, 2), np.float32)
    bm = X.boom(seed=91, f0=60, f1=30, dur=1.6)
    if bm.ndim == 1:
        bm = np.stack([bm, bm], 1)
    o = int(42.12 * SR)
    add[o:o + len(bm)] += bm[:n - o] * db(-16)
    x += add + end_sting(n, dur - END_DUR)
    return x


def loudnorm_write(x, path, target=-14.0):
    tmp = path + ".raw.wav"
    sf.write(tmp, x, SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    gain = target - I + 0.15
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    "volume=%.2fdB,alimiter=limit=0.79:attack=4:release=60:level=false:latency=true" % gain,
                    "-c:a", "pcm_f32le", path], check=True)
    os.remove(tmp)
    return I, gain


# ---------------------------------------------------------------------------- build one short

def build(name):
    import shots as S
    from render import active_weights
    cfg = SHORTS[name]
    os.makedirs(OUT, exist_ok=True)
    tl, shots, ovs, total = S.build()
    index = {s.name: i for i, s in enumerate(shots)}
    meta = json.load(open(os.path.join(SRC, name + ".json")))
    times, modes = meta["times"], meta["modes"]

    # --- words and captions, on the short's own clock
    caps, beats = [], []
    if cfg["kind"] == "vo":
        vo = json.load(open(os.path.join(ROOT, "shorts", "a_vo", "vo.json")))
        audio, vsr = sf.read(os.path.join(ROOT, "shorts", "a_vo", "vo.wav"), dtype="float32")
        spans = []
        paras = {}
        for it in vo["items"]:
            seg = audio[int(it["s"] * vsr):int(it["e"] * vsr)]
            pz = detect_pauses(seg, vsr, it["s"])
            toks = apply_repl(word_times(it["text"], it["s"], it["e"], pz), cfg["repl"])
            for c, show, hide in make_chunks(toks, it["e"]):
                caps.append([c, show, hide])
            spans.append((it["s"], it["e"]))
            paras.setdefault(it["para"], []).append(it)
        beats = [(v[0]["s"], v[-1]["e"]) for _, v in sorted(paras.items())]
        dur = A_EDL[-1][1] + END_DUR
        clock0 = 0.0
    else:
        clock0 = cfg["t0"]
        spans = []
        for q in tl.list:
            if q["section"] != cfg["section"]:
                continue
            pz = [(q["s"] + p0, q["s"] + p1) for p0, p1 in q["pauses"]]
            toks = word_times(q["text"], q["s"], q["e"], pz)
            toks = apply_repl([(w, t - clock0) for w, t in toks], cfg["repl"])
            for c, show, hide in make_chunks(toks, q["e"] - clock0):
                caps.append([c, show, hide])
            spans.append((q["s"] - clock0, q["e"] - clock0))
            beats.append((q["s"] - clock0, q["e"] - clock0))
        dur = (cfg["src_end"] - clock0) + END_DUR
    # a chunk never outlives the next one's arrival
    caps.sort(key=lambda c: c[1])
    for k in range(len(caps) - 1):
        caps[k][2] = min(caps[k][2], caps[k + 1][1] - 0.02)
    captions = [Caption(c, s, h, cfg["hl"]) for c, s, h in caps]
    n_frames = int(round(dur * FPS))
    end_t = dur - END_DUR

    # --- static overlays
    logo = rounded_logo()
    brand = text_layer("LAPORTE WEATHER NOW", "sans_b", 30, "#e9e3d6", tracking=0.04, shadow=0.6)
    title = text_layer(cfg["title"], "fell", 68, CREAM, glow="#ff7a1a", glow_a=0.45, shadow=0.8)
    tw = title.shape[1]
    if tw > VW - 40:
        s_ = (VW - 40) / tw
        title = cv2.resize(title, (int(tw * s_), int(title.shape[0] * s_)), interpolation=cv2.INTER_AREA)
    tag_layers = []
    for a0, a1, txt in cfg["tags"]:
        tag_layers.append(((a0 - clock0) if cfg["kind"] == "clip" else a0,
                           (a1 - clock0) if cfg["kind"] == "clip" else a1,
                           text_layer(txt, "sans", 27, GHOST, tracking=0.2, shadow=0.8)))
    e_logo = big_logo(280)
    e_title = text_layer("Before Pumpkins", "fell", 112, CREAM, glow="#ff7a1a", glow_a=0.55, shadow=0.8)
    e_sub = text_layer("The Real History of Halloween", "fell_it", 54, "#e2d2ae", shadow=0.8)
    e_cta = text_layer("FULL DOCUMENTARY ON OUR CHANNEL", "sans_b", 30, GHOST, tracking=0.2, shadow=0.8)
    e_url = text_layer("laporteweathernow.com", "sans", 32, "#c8bba0", shadow=0.8)
    vig = vignette_v()

    # --- source frame for each output frame
    cand_cache = {}

    def src_for(tau):
        """(index into the clip, shot name for framing) for short time tau."""
        if cfg["kind"] == "clip":
            idx = int(round(tau * FPS))
            idx = min(idx, len(times) - 1)
            return idx, None
        for out0, out1, shot, s0, s1 in A_EDL:
            if out0 - 1e-6 <= tau < out1 + 1e-6:
                s = s0 + (tau - out0) * (s1 - s0) / (out1 - out0)
                if shot not in cand_cache:
                    cand_cache[shot] = [i for i, m in enumerate(modes) if m == shot]
                cand = cand_cache[shot]
                ts = np.array([times[i] for i in cand])
                j = int(np.argmin(np.abs(ts - s)))
                return cand[j], shot
        return len(times) - 1, A_EDL[-1][2]

    def framing(idx, shot):
        if shot:
            return fr3(shot)
        t = times[idx]
        m = modes[idx]
        if m != "film":
            return fr3(m)
        zs, cs, ds, ws = 0.0, 0.0, 0.0, 0.0
        for i in range(len(shots)):
            wgt, a0, a1 = active_weights(shots, i, t)
            if wgt <= 0:
                continue
            # weight of this shot in the blend: later shot weight wgt, earlier gets the rest
            ws_i = wgt
            z, c, d = fr3(shots[i].name)
            zs = zs * (1 - ws_i) + z * ws_i if ws else z
            cs = cs * (1 - ws_i) + c * ws_i if ws else c
            ds = ds * (1 - ws_i) + d * ws_i if ws else d
            ws = 1.0
        return (zs, cs, ds) if ws else (1.0, 0.5, 0.0)

    # --- quick look at a few frames instead of the whole short
    prev_list = os.environ.get("PREVIEW")
    if prev_list:
        outs = []
        for tau in [float(v) for v in prev_list.split(",")]:
            if tau < end_t:
                idx, shot = src_for(tau)
                buf = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.4f" % (idx / FPS), "-i",
                                      os.path.join(SRC, name + ".mp4"), "-frames:v", "1", "-f", "rawvideo",
                                      "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
                src = np.frombuffer(buf, np.uint8).reshape(1080, 1920, 3)
                z, c, d = framing(idx, shot)
                base = compose_base(src, z, c, d)
                globals()["_LAST_BASE"] = base
            else:
                base = globals().get("_LAST_BASE", np.zeros((VH, VW, 3), np.float32)) * 0.3
            frame = base * vig
            progress_bar(frame, min(1.0, tau / end_t), len(beats))
            paste(frame, logo, 80, 206, anchor="lt")
            paste(frame, brand, 203, 236, anchor="lm")
            if tau < end_t:
                paste(frame, title, VW / 2, 330)
                for a0, a1, lay in tag_layers:
                    if a0 <= tau <= a1:
                        paste(frame, lay, VW / 2, 396)
                for cp in captions:
                    cp.draw(frame, tau)
            else:
                u = 3.0
                paste(frame, e_logo, VW / 2, 700)
                paste(frame, e_title, VW / 2, 965)
                paste(frame, e_sub, VW / 2, 1062)
                paste(frame, e_cta, VW / 2, 1170)
                paste(frame, e_url, VW / 2, 1228)
            np.clip(frame, 0, 1, out=frame)
            outs.append((frame * 255 + 0.5).astype(np.uint8))
        small = [cv2.resize(o, (360, 640), interpolation=cv2.INTER_AREA) for o in outs]
        sheet = np.concatenate(small, axis=1)
        cv2.imwrite(os.path.join(OUT, name + "_preview.jpg"), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
        cv2.imwrite(os.path.join(OUT, name + "_preview_full.png"), cv2.cvtColor(outs[0], cv2.COLOR_RGB2BGR))
        for w_, s_, h_ in caps[:12]:
            print("%6.2f-%6.2f  %s" % (s_, h_, " ".join(x for x, _ in w_)))
        return

    # --- video
    vid_path = os.path.join(OUT, name + "_video.mp4")
    audio_only = bool(os.environ.get("AUDIO_ONLY")) and os.path.exists(vid_path)
    enc = None if audio_only else subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                            "%dx%d" % (VW, VH), "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", os.environ.get("PRESET", "medium"),
                            "-crf", "19", "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", "48", vid_path],
                           stdin=subprocess.PIPE)
    rd = Reader(os.path.join(SRC, name + ".mp4"))
    prev_base, last_shot, xf_start = None, None, -1.0
    last_base = None
    if os.environ.get("AUDIO_ONLY") and os.path.exists(vid_path):
        n_frames_video = 0
    else:
        n_frames_video = n_frames
    for f in range(n_frames_video):
        tau = f / FPS
        if tau < end_t:
            idx, shot = src_for(tau)
            src = rd.get(idx)
            z, c, d = framing(idx, shot)
            base = compose_base(src, z, c, d)
            # quick dissolves between the trailer's pictures
            if cfg["kind"] == "vo":
                if shot != last_shot and last_shot is not None and not (shot == "morph" and last_shot == "morph"):
                    prev_base, xf_start = last_base, tau
                if prev_base is not None and tau - xf_start < 0.25:
                    k = sstep(0.0, 0.25, tau - xf_start)
                    base = prev_base * (1 - k) + base * k
                last_shot = shot
            last_base = base
        else:
            k = sstep(end_t, end_t + 0.6, tau)
            base = last_base * (1 - 0.85 * k)
        frame = base * vig
        # header
        progress_bar(frame, min(1.0, tau / end_t), len(beats))
        paste(frame, logo, 80, 206, anchor="lt")
        paste(frame, brand, 203, 236, anchor="lm")
        if tau < end_t + 0.3:
            ta = 1 - sstep(end_t, end_t + 0.3, tau)
            paste(frame, title, VW / 2, 330, a=ta * sstep(0.0, 0.25, tau + 0.25))
            for a0, a1, lay in tag_layers:
                if a0 - 0.1 <= tau <= a1 + 0.4:
                    a = sstep(a0, a0 + 0.35, tau) * (1 - sstep(a1, a1 + 0.35, tau)) * ta
                    paste(frame, lay, VW / 2, 396, a=a)
            for cp in captions:
                cp.draw(frame, tau)
        else:
            # end card
            u = tau - end_t
            paste(frame, e_logo, VW / 2, 700, a=sstep(0.2, 0.7, u))
            paste(frame, e_title, VW / 2, 965 + 10 * (1 - ease_out(sstep(0.4, 1.1, u))), a=sstep(0.4, 1.0, u))
            paste(frame, e_sub, VW / 2, 1062, a=sstep(0.7, 1.2, u))
            paste(frame, e_cta, VW / 2, 1170, a=sstep(1.0, 1.5, u))
            paste(frame, e_url, VW / 2, 1228, a=sstep(1.2, 1.7, u))
        np.clip(frame, 0, 1, out=frame)
        enc.stdin.write((frame * 255 + 0.5).astype(np.uint8).tobytes())
        if f % 240 == 0:
            print("%s frame %d/%d" % (name, f, n_frames), flush=True)
    rd.close()
    if enc is not None:
        enc.stdin.close()
        enc.wait()

    # --- audio and mux
    x = build_audio(name, cfg, dur, vo_spans=spans)
    wav = os.path.join(OUT, name + "_audio.wav")
    I, gain = loudnorm_write(x, wav)
    final = os.path.join(OUT, cfg["file"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid_path, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    "-metadata", "title=%s | Before Pumpkins" % cfg["title"], "-metadata", "artist=La Porte Weather Now",
                    final], check=True)
    print("%s: %.1f s, mix %.1f LUFS -> gain %.1f dB -> %s" % (name, dur, I, gain, final), flush=True)
    json.dump([[[w for w, _ in c], s, h] for c, s, h in caps], open(os.path.join(OUT, name + "_captions.json"), "w"),
              indent=0)


if __name__ == "__main__":
    for nm in sys.argv[1:]:
        build(nm)
