"""La Porte County trick-or-treat hours reel (1080x1920), drawn in the "Before Pumpkins" style.

python3 tot_reel.py [PREVIEW times...]
Needs shorts/tot_vo (tot_vo.py) and the clean backgrounds t0..t4 in shorts/src (render_clips.py).
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
from scipy.signal import resample_poly

FILM = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FILM)
sys.path.insert(0, FILM)

import shorts as SH  # noqa: E402
from core import text_layer, paste, rgb, GHOST, sstep, ease_out  # noqa: E402

VW, VH, FPS, SR = 1080, 1920, 24, 48000
OFF = 0.9                      # the doorbell rings before the first words
DUR = 57.0
SRC = os.path.join(ROOT, "shorts", "src")
OUT = os.path.join(ROOT, "shorts", "out")
VO_DIR = os.path.join(ROOT, "shorts", "tot_vo")
AMBER = "#ffb45c"
ORANGE = "#ff8a1c"
CREAM = "#f6ead0"
MUTED = "#9fb7b2"

# sections: (start, end, background clip, its first output time, framing, dim)
SECTIONS = [
    (0.0, 5.9, "t0", 0.0, (1.0, 0.5, 0), 1.0),
    (5.9, 19.2, "t1", 5.65, (1.0, 0.62, 0), 0.5),
    (19.2, 33.1, "t2", 18.95, (1.0, 0.5, 0), 0.5),
    (33.1, 48.3, "t3", 32.85, (1.0, 0.5, 0), 0.5),
    (48.3, DUR, "t4", 48.05, (1.0, 0.42, 0), 1.0),
]
XF = 0.5


# ---------------------------------------------------------------------------- words

def load_words():
    vo = json.load(open(os.path.join(VO_DIR, "vo.json")))
    audio, vsr = sf.read(os.path.join(VO_DIR, "vo.wav"), dtype="float32")
    sents = []
    for it in vo["items"]:
        seg = audio[int(it["s"] * vsr):int(it["e"] * vsr)]
        pz = SH.detect_pauses(seg, vsr, it["s"])
        wt = [(w, t + OFF) for w, t in SH.word_times(it["text"], it["s"], it["e"], pz)]
        sents.append(dict(it, words=wt, s=it["s"] + OFF, e=it["e"] + OFF))
    return sents


def word_time(sents, para, phrase):
    ph = phrase.lower().split()
    for s in sents:
        if s["para"] != para:
            continue
        norm = [re.sub(r"[^\w'-]", "", w).lower() for w, _ in s["words"]]
        for i in range(len(norm) - len(ph) + 1):
            if norm[i:i + len(ph)] == ph:
                return s["words"][i][1]
    raise KeyError((para, phrase))


# ---------------------------------------------------------------------------- drawing

def tl(text, fname, size, color, **kw):
    kw.setdefault("shadow", 0.9)
    return text_layer(text, fname, size, color, **kw)


def pill(text, size=40, fg="#1a1206", bg=AMBER, padx=34, h=None):
    t = text_layer(text, "sans_x", size, fg, shadow=0.0)
    padn = int(size * 0.9)
    ink = t[padn:-padn, padn:-padn]
    ih, iw = ink.shape[:2]
    h = h or int(size * 1.55)
    w = iw + 2 * padx
    out = np.zeros((h, w, 4), np.float32)
    r = h // 2
    m = np.zeros((h * 4, w * 4), np.uint8)
    cv2.rectangle(m, (r * 4, 0), (w * 4 - r * 4, h * 4), 255, -1)
    cv2.circle(m, (r * 4, r * 4), r * 4, 255, -1)
    cv2.circle(m, (w * 4 - r * 4, r * 4), r * 4, 255, -1)
    a = cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    out[..., :3] = rgb(bg)[None, None, :] * a[..., None]
    out[..., 3] = a
    y0 = (h - ih) // 2
    x0 = padx
    region = out[y0:y0 + ih, x0:x0 + iw]
    region[..., :3] = ink[..., :3] + region[..., :3] * (1 - ink[..., 3:4])
    region[..., 3] = ink[..., 3] + region[..., 3] * (1 - ink[..., 3])
    return out


def panel_box(w, h, r=34, fill="#080c0e", fa=0.74, edge=AMBER, ea=0.55):
    m = np.zeros((h * 2, w * 2), np.uint8)
    cv2.rectangle(m, (r * 2, 0), (w * 2 - r * 2, h * 2), 255, -1)
    cv2.rectangle(m, (0, r * 2), (w * 2, h * 2 - r * 2), 255, -1)
    for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(m, (cx * 2, cy * 2), r * 2, 255, -1)
    a = cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    # rounded border: outline of the mask
    k = cv2.morphologyEx((a > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)
    out = np.zeros((h, w, 4), np.float32)
    out[..., :3] = rgb(fill)[None, None, :] * a[..., None] * fa
    out[..., 3] = a * fa
    border = np.clip(k, 0, 1) * ea
    out[..., :3] = rgb(edge)[None, None, :] * border[..., None] + out[..., :3] * (1 - border[..., None])
    out[..., 3] = border + out[..., 3] * (1 - border)
    return out


def jack_icon(s=40):
    """A tiny glowing jack-o'-lantern."""
    c = np.zeros((s * 4, s * 4, 4), np.float32)
    S = s * 4
    cv2.ellipse(c, (S // 2, S // 2 + S // 16), (S // 2 - 6, int(S * 0.40)), 0, 0, 360, (1.0, 0.50, 0.12, 1.0), -1, cv2.LINE_AA)
    cv2.rectangle(c, (S // 2 - S // 22, S // 14), (S // 2 + S // 22, S // 5), (0.35, 0.42, 0.15, 1.0), -1)
    face = [np.array([[S * 0.30, S * 0.48], [S * 0.40, S * 0.33], [S * 0.46, S * 0.48]]),
            np.array([[S * 0.54, S * 0.48], [S * 0.60, S * 0.33], [S * 0.70, S * 0.48]]),
            np.array([[S * 0.26, S * 0.60], [S * 0.36, S * 0.66], [S * 0.44, S * 0.60], [S * 0.50, S * 0.68],
                      [S * 0.56, S * 0.60], [S * 0.64, S * 0.66], [S * 0.74, S * 0.60], [S * 0.62, S * 0.78],
                      [S * 0.38, S * 0.78]])]
    for f in face:
        cv2.fillPoly(c, [f.astype(np.int32)], (1.0, 0.86, 0.35, 1.0), cv2.LINE_AA)
    c = cv2.resize(c, (s, s), interpolation=cv2.INTER_AREA)
    c[..., :3] *= c[..., 3:4]
    return c


class Item:
    """A layer that fades and slides in at t_in (and out at t_out)."""

    def __init__(self, layer, x, y, t_in, t_out=None, anchor="mm", rise=14, fade=0.25):
        self.layer, self.x, self.y, self.anchor = layer, x, y, anchor
        self.t_in, self.t_out, self.rise, self.fade = t_in, t_out, rise, fade

    def draw(self, frame, t, k=1.0):
        a = sstep(self.t_in, self.t_in + self.fade, t)
        if self.t_out is not None:
            a *= 1 - sstep(self.t_out, self.t_out + 0.25, t)
        a *= k
        if a <= 0.003:
            return
        dy = self.rise * (1 - ease_out(sstep(self.t_in, self.t_in + self.fade + 0.1, t)))
        paste(frame, self.layer, self.x, self.y + dy, a=a, anchor=self.anchor)


# ---------------------------------------------------------------------------- the reel

def build_items(sents):
    W = lambda p, ph: word_time(sents, p, ph)  # noqa: E731
    items = []
    # 1. hook
    glow = dict(glow=ORANGE, glow_a=0.55)
    yy = np.linspace(-1, 1, 600, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, VW, dtype=np.float32)[None, :]
    shade = np.zeros((600, VW, 4), np.float32)
    shade[..., 3] = 0.68 * np.exp(-(yy / 0.62) ** 2) * (1 - 0.35 * xx ** 2)
    items += [Item(shade, VW / 2, 1090, 0.0, 5.55, rise=0, fade=0.01)]
    items += [Item(tl("TRICK-OR-TREAT", "sans_k", 96, ORANGE), VW / 2, 905, 0.15, 5.55),
              Item(tl("HOURS", "sans_k", 200, CREAM, **glow), VW / 2, 1060, 0.35, 5.55),
              Item(tl("every La Porte County town · 2026", "sans_b", 42, CREAM), VW / 2, 1195, 0.7, 5.55),
              Item(pill("SAVE THIS"), VW / 2, 1300, W(0, "save") - 0.05, 5.55)]
    # 2. most towns: Saturday 5 to 7
    s1 = []
    s1.append(Item(tl("SATURDAY, OCT. 31", "sans_x", 56, AMBER, tracking=0.03), VW / 2, 612, W(1, "saturday") - 0.1))
    s1.append(Item(tl("5 TO 7 P.M.", "sans_k", 108, CREAM, **glow), VW / 2, 728, W(1, "from") - 0.05))
    towns = ["La Porte", "Michigan City", "Kingsford Heights", "Long Beach", "Rolling Prairie", "Trail Creek",
             "Union Mills", "Wanatah", "Westville"]
    spoken = {"La Porte": "la porte", "Michigan City": "michigan city", "Kingsford Heights": "kingsford heights",
              "Long Beach": "long beach", "Rolling Prairie": "rolling prairie", "Trail Creek": "trail creek",
              "Union Mills": "union mills", "Wanatah": "wanatah", "Westville": "westville"}
    icon = jack_icon(40)
    for k, name in enumerate(towns):
        col, row = k % 2, k // 2
        x = 150 if col == 0 else 650
        y = 885 + row * 92
        t = W(2, spoken[name]) - 0.05
        s1.append(Item(icon, x - 10, y, t, anchor="rm", rise=8))
        s1.append(Item(tl(name, "sans_b", 44, CREAM), x - 20, y, t, anchor="lm", rise=8))
    # 3. the exceptions
    s2 = []
    s2.append(Item(tl("LaCrosse", "sans_x", 62, CREAM), 110, 615, W(3, "lacrosse") - 0.05, anchor="lm"))
    s2.append(Item(tl("Sat., Oct. 31 · 5 to 7:30 p.m.", "sans", 42, AMBER), 110, 690, W(3, "lacrosse"), anchor="lm"))
    s2.append(Item(pill("LATER", 32), 950, 615, W(3, "later"), anchor="rm"))
    s2.append(Item(tl("Pottawattamie Park", "sans_x", 62, CREAM), 110, 835, W(4, "pottawattamie") - 0.05, anchor="lm"))
    s2.append(Item(tl("Sun., Oct. 25 · 3 to 5 p.m.", "sans", 42, AMBER), 110, 910, W(4, "this"), anchor="lm"))
    s2.append(Item(pill("EARLY · IN DAYLIGHT", 30), 110, 990, W(4, "daylight") - 0.1, anchor="lm"))
    s2.append(Item(tl("Hanna · Michiana Shores", "sans_x", 54, CREAM), 110, 1140, W(5, "hanna") - 0.05, anchor="lm"))
    s2.append(Item(tl("No hours announced yet", "sans", 42, MUTED), 110, 1210, W(5, "haven't"), anchor="lm"))
    # 4. this weekend, a day at a time
    s3 = []
    head = Item(tl("CAN'T WAIT? THIS WEEKEND", "sans_x", 40, AMBER, tracking=0.12), VW / 2, 590, W(6, "can't") - 0.05)
    s3.append(head)
    t_sat, t_sun = W(7, "saturday") - 0.15, W(8, "sunday") - 0.15
    days = [
        ("FRIDAY, OCT. 23", W(6, "trunk-or-treats") - 0.1, t_sat,
         [("Franciscan Health Trunk-or-Treat", "Michigan City · 4:30 to 6:30 p.m.", W(6, "franciscan"))]),
        ("SATURDAY, OCT. 24", t_sat, t_sun,
         [("Trick-or-Treat on Franklin Street", "Michigan City · 2 to 5 p.m.", W(7, "franklin")),
          ("YMCA Trunk-or-Treat", "Michigan City · 2 to 4 p.m.", W(7, "ymca")),
          ("Museum Trick or Treat", "County museum, La Porte · 2 to 4 p.m.", W(7, "county museum")),
          ("Trick or Treat in Pioneerland", "County fairgrounds · 5 to 7 p.m.", W(7, "pioneerland"))]),
        ("SUNDAY, OCT. 25", t_sun, 48.05,
         [("La Porte Police Trunk or Treat", "Civic Auditorium, La Porte · 1 to 3 p.m.", W(8, "la porte police")),
          ("Orak Shrine Trunk-or-Treat", "Michigan City · 4 to 6 p.m.", W(8, "orak"))]),
    ]
    for day, t0, t1, evs in days:
        s3.append(Item(tl(day, "sans_k", 58, CREAM, **glow), VW / 2, 680, t0, t1 - 0.25))
        for k, (name, detail, t) in enumerate(evs):
            y = 790 + k * 140
            s3.append(Item(tl(name, "sans_b", 44, CREAM), 110, y, max(t0 + 0.1, t - 0.05), t1 - 0.25, anchor="lm"))
            s3.append(Item(tl(detail, "sans", 36, AMBER), 110, y + 52, max(t0 + 0.15, t), t1 - 0.25, anchor="lm"))
    # 5. outro
    s4 = [Item(tl("Every time and place:", "sans_b", 48, CREAM), VW / 2, 600, W(9, "every") - 0.05, 55.6),
          Item(pill("laporteweathernow.com", 44), VW / 2, 690, W(9, "la porte") - 0.05, 55.6),
          Item(tl("Happy trick-or-treating!", "fell_it", 70, CREAM, **glow), VW / 2, 800, W(9, "happy") - 0.05, 55.6)]
    return items, s1, s2, s3, s4


class BG:
    """Reads the five background clips forward, two at once during a crossfade."""

    def __init__(self):
        self.readers = {}

    def frame(self, name, tau, first):
        if name not in self.readers:
            self.readers[name] = SH.Reader(os.path.join(SRC, name + ".mp4"))
        idx = int(round((tau - first) * FPS))
        return self.readers[name].get(max(0, idx))


def section_at(tau):
    out = []
    for k, (s0, s1, clip, first, fr, dim) in enumerate(SECTIONS):
        a0 = s0 - XF / 2 if k else -1
        a1 = s1 + XF / 2 if k < len(SECTIONS) - 1 else DUR + 1
        if a0 <= tau < a1:
            w = 1.0 if k == 0 else sstep(s0 - XF / 2, s0 + XF / 2, tau)
            out.append((k, w))
    return out


def render(preview=None):
    sents = load_words()
    hook, s1, s2, s3, s4 = build_items(sents)
    groups = [(hook, 0.0, 5.9), (s1, 5.9, 19.2), (s2, 19.2, 33.1), (s3, 33.1, 48.3), (s4, 48.3, DUR)]
    # captions under the panels
    SH.CAP_Y = 1452
    SH.CAP_SIZE = 60
    caps = []
    for s in sents:
        for c, show, hide in SH.make_chunks(s["words"], s["e"]):
            caps.append([c, show, hide])
    caps.sort(key=lambda c: c[1])
    for k in range(len(caps) - 1):
        caps[k][2] = min(caps[k][2], caps[k + 1][1] - 0.02)
    hl = ["la porte", "saturday", "five", "seven", "lacrosse", "seven-thirty", "pottawattamie", "sunday", "early",
          "daylight", "friday", "save", "happy"]
    captions = [SH.Caption(c, s, h, hl) for c, s, h in caps]
    logo = SH.rounded_logo()
    brand = text_layer("LA PORTE WEATHER NOW", "sans_b", 30, "#e9e3d6", tracking=0.04, shadow=0.6)
    title = text_layer("Trick-or-Treat Hours", "fell", 70, "#f1e4c6", glow=ORANGE, glow_a=0.45, shadow=0.8)
    tag = text_layer("LA PORTE COUNTY · HALLOWEEN 2026", "sans", 27, GHOST, tracking=0.2, shadow=0.8)
    boxes = {1: (panel_box(960, 800), 540, 520 + 400), 2: (panel_box(960, 730), 540, 520 + 365),
             3: (panel_box(960, 800), 540, 520 + 400)}
    vig = SH.vignette_v()
    bg = BG()

    def make(tau):
        parts = section_at(tau)
        base = None
        for k, w in parts:
            s0, s1_, clip, first, fr, dim = SECTIONS[k]
            src = bg.frame(clip, tau, first)
            b = SH.compose_base(src, *fr)
            # dim behind the lists, ease back up for the outro
            b *= dim
            base = b if base is None else base * (1 - w) + b * w
        # the very end: fade to dark after the candle goes out
        base *= 1 - 0.8 * sstep(55.8, 57.0, tau)
        frame = base * vig
        SH.progress_bar(frame, min(1.0, tau / DUR), 5)
        paste(frame, logo, 80, 206, anchor="lt")
        paste(frame, brand, 203, 236, anchor="lm")
        ta = sstep(5.6, 6.1, tau) * (1 - sstep(47.9, 48.4, tau))
        if ta > 0:
            paste(frame, title, VW / 2, 330, a=ta)
            paste(frame, tag, VW / 2, 398, a=ta)
        for gi, (items, g0, g1) in enumerate(groups):
            ga = sstep(g0 - 0.3, g0 + 0.2, tau) * (1 - sstep(g1 - 0.2, g1 + 0.3, tau)) if gi else \
                (1 - sstep(g1 - 0.2, g1 + 0.3, tau))
            if gi == 4:
                ga = sstep(g0 - 0.3, g0 + 0.2, tau)
            if ga <= 0.003:
                continue
            if gi in boxes:
                lay, x, y = boxes[gi]
                paste(frame, lay, x, y, a=ga)
            for it in items:
                it.draw(frame, tau, ga)
        for cp in captions:
            cp.draw(frame, tau)
        np.clip(frame, 0, 1, out=frame)
        return frame

    os.makedirs(OUT, exist_ok=True)
    if preview:
        outs = [make(t) for t in preview]
        small = [cv2.resize((o * 255 + 0.5).astype(np.uint8), (360, 640), interpolation=cv2.INTER_AREA) for o in outs]
        cv2.imwrite(os.path.join(OUT, "tot_preview.jpg"), cv2.cvtColor(np.concatenate(small, 1), cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
        for i, o in enumerate(outs):
            cv2.imwrite(os.path.join(OUT, "tot_pf_%d.jpg" % i),
                        cv2.cvtColor((o * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
        return
    vid = os.path.join(OUT, "tot_video.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                            "%dx%d" % (VW, VH), "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast",
                            "-crf", "19", "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", "48", vid],
                           stdin=subprocess.PIPE)
    n = int(round(DUR * FPS))
    for f in range(n):
        enc.stdin.write((make(f / FPS) * 255 + 0.5).astype(np.uint8).tobytes())
        if f % 240 == 0:
            print("frame %d/%d" % (f, n), flush=True)
    enc.stdin.close()
    enc.wait()
    # sound: doorbell, the narrator, a soft score, wind and leaves, and the candle at the end
    import sfx as X
    import audio as AU
    ns = int(DUR * SR)
    vo, vsr = sf.read(os.path.join(VO_DIR, "vo.wav"), dtype="float32")
    vo = X.hp(resample_poly(vo, SR // vsr, 1).astype(np.float32), 70)
    vo *= SH.db(-3.0) / np.abs(vo).max()
    voice = np.zeros((ns, 2), np.float32)
    o = int(OFF * SR)
    m = min(len(vo), ns - o)
    voice[o:o + m] = vo[:m, None]
    music = np.zeros((ns, 2), np.float32)

    def add(bus, sig, t, g):
        if sig.ndim == 1:
            sig = np.stack([sig, sig], 1)
        i = int(t * SR)
        mm = min(len(sig), ns - i)
        if mm > 0:
            bus[i:i + mm] += sig[:mm] * SH.db(g)
    dr = X.drone(DUR + 2, seed=171)
    e = np.ones(len(dr), np.float32)
    e[:int(2 * SR)] = np.linspace(0, 1, int(2 * SR))
    add(music, dr * e[:, None], 0.0, -27)
    prog = AU.PROG[11]
    d = (DUR - 1.0) / len(prog)
    for k, chord in enumerate(prog):
        p = X.pad(d + 4.0, [AU.N[c] for c in chord], seed=300 + k, attack=2.5, release=3.0)
        add(music, p, max(0.0, k * d - 1.0), -25)
    add(music, AU.motif(7, 0.45), W_happy(sents) + 0.6, -19)
    music *= SH.db(2.0)
    amb = np.zeros((ns, 2), np.float32)
    add(amb, X.wind(DUR, 501), 0.0, -27)
    add(amb, X.leaves_bed(DUR, 502), 0.0, -34)
    amb *= SH.db(5.0)
    fx = np.zeros((ns, 2), np.float32)
    add(fx, X.doorbell(), 0.0, -14)
    add(fx, X.blow_out(), 54.45, -12)
    add(fx, X.boom(seed=33, f0=70, f1=30, dur=2.5), 5.85, -18)
    env = SH.duck_env([(s["s"], s["e"]) for s in sents], ns)
    x = voice + music * (1 - 0.55 * env) + amb * (1 - 0.40 * env) + fx * (1 - 0.15 * env)
    x[-int(1.2 * SR):] *= np.linspace(1, 0, int(1.2 * SR))[:, None]
    wav = os.path.join(OUT, "tot_audio.wav")
    I, gain = SH.loudnorm_write(x, wav)
    final = os.path.join(OUT, "la-porte-county-trick-or-treat-hours-2026.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    "-metadata", "title=Trick-or-Treat Hours, La Porte County 2026",
                    "-metadata", "artist=La Porte Weather Now", final], check=True)
    print("done %.1f LUFS -> %+.1f dB -> %s" % (I, gain, final), flush=True)


def W_happy(sents):
    return word_time(sents, 9, "happy")


if __name__ == "__main__":
    pv = [float(v) for v in sys.argv[1:]] if len(sys.argv) > 1 else None
    render(pv)
