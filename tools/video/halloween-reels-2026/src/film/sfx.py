"""Procedural sound: every effect, ambience and musical instrument is synthesised here."""
import math

import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly

SR = 48000
_rng = np.random.default_rng(1234)


def rng(seed=None):
    return np.random.default_rng(seed) if seed is not None else _rng


def tt(dur):
    return np.arange(int(dur * SR), dtype=np.float32) / SR


def n_of(dur):
    return int(dur * SR)


def _sos(kind, f, order=2):
    if kind == "band":
        lo, hi = f
        hi = min(hi, SR / 2 * 0.95)
        return butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return butter(order, min(f, SR / 2 * 0.95), btype=kind, fs=SR, output="sos")


def bp(x, lo, hi, order=2):
    return sosfilt(_sos("band", (lo, hi), order), x, axis=0).astype(np.float32)


def lp(x, f, order=2):
    return sosfilt(_sos("low", f, order), x, axis=0).astype(np.float32)


def hp(x, f, order=2):
    return sosfilt(_sos("high", f, order), x, axis=0).astype(np.float32)


def reson(x, f, q=20):
    bw = f / q
    return bp(x, max(20, f - bw / 2), f + bw / 2, 1)


def white(n, seed=None):
    return rng(seed).standard_normal(n).astype(np.float32)


def pink(n, seed=None):
    w = rng(seed).standard_normal(n)
    X = np.fft.rfft(w)
    f = np.arange(len(X))
    f[0] = 1
    X /= np.sqrt(f)
    y = np.fft.irfft(X, n)
    return (y / (np.std(y) + 1e-9)).astype(np.float32)


def brown(n, seed=None, f=25.0):
    w = rng(seed).standard_normal(n).astype(np.float32)
    y = lp(w, f, 1)
    return y / (np.std(y) + 1e-9)


def smooth_rand(n, rate, seed=None, lo=0.0, hi=1.0):
    """Slowly varying random curve with about `rate` changes per second."""
    r = rng(seed)
    k = max(4, int(n / SR * rate) + 4)
    pts = r.uniform(lo, hi, k)
    x = np.linspace(0, k - 3, n)
    i = np.floor(x).astype(int)
    fr = x - i
    fr = fr * fr * (3 - 2 * fr)
    return (pts[i] * (1 - fr) + pts[i + 1] * fr).astype(np.float32)


def env_ad(n, a, d, curve=4.0):
    t = np.arange(n, dtype=np.float32) / SR
    e = np.where(t < a, t / max(a, 1e-4), np.exp(-(t - a) / max(d, 1e-4) * 1.0))
    return e.astype(np.float32)


def fade(x, fin=0.01, fout=0.05):
    n = len(x)
    a, b = min(n, n_of(fin)), min(n, n_of(fout))
    if a > 0:
        x[:a] *= np.linspace(0, 1, a, dtype=np.float32)[:, None] if x.ndim == 2 else np.linspace(0, 1, a, dtype=np.float32)
    if b > 0:
        x[n - b:] *= np.linspace(1, 0, b, dtype=np.float32)[:, None] if x.ndim == 2 else np.linspace(1, 0, b, dtype=np.float32)
    return x


def stereo(x, pan=0.0, width=0.0, seed=None):
    """Mono -> stereo with constant-power pan; width adds a tiny decorrelated delay."""
    l = math.cos((pan + 1) * math.pi / 4)
    r = math.sin((pan + 1) * math.pi / 4)
    out = np.stack([x * l, x * r], axis=1).astype(np.float32)
    if width > 0:
        d = int(SR * 0.012 * width)
        out[d:, 1] = out[d:, 1] * 0.7 + out[:-d, 1] * 0.3 if d > 0 else out[:, 1]
    return out


_IR = {}


def ir(rt=2.5, seed=7, pre=0.02, bright=6000):
    key = (rt, seed, pre, bright)
    if key in _IR:
        return _IR[key]
    n = n_of(rt * 1.2)
    r = rng(seed)
    t = np.arange(n) / SR
    decay = np.exp(-6.9 * t / rt)
    L = r.standard_normal(n) * decay
    R = r.standard_normal(n) * decay
    L, R = lp(L.astype(np.float32), bright), lp(R.astype(np.float32), bright)
    p = n_of(pre)
    out = np.zeros((n + p, 2), np.float32)
    out[p:, 0], out[p:, 1] = L, R
    # a few early reflections
    for k in range(6):
        dt = n_of(r.uniform(0.008, 0.06))
        g = r.uniform(0.2, 0.5)
        out[dt, 0] += g
        out[n_of(r.uniform(0.008, 0.06)), 1] += g
    out /= np.sqrt((out ** 2).sum() / 2) + 1e-9
    _IR[key] = out
    return out


def reverb(x, rt=2.5, wet=0.3, seed=7, bright=6000):
    """x: (n, 2). Returns dry+wet, lengthened by the tail."""
    h = ir(rt, seed, bright=bright)
    n = len(x) + len(h) - 1
    out = np.zeros((n, 2), np.float32)
    out[:len(x)] += x * (1 - wet * 0.5)
    for c in range(2):
        out[:, c] += fftconvolve(x[:, c], h[:, c]).astype(np.float32) * wet * 0.25
    return out


def norm(x, peak=1.0):
    m = np.abs(x).max() + 1e-9
    return (x / m * peak).astype(np.float32)


# ----------------------------------------------------------------------------- one-shot effects

def match_strike(seed=1):
    r = rng(seed)
    n = n_of(1.8)
    t = tt(1.8)
    scratch = bp(white(n, seed), 1800, 9000) * (env_ad(n, 0.005, 0.05)) * 0.9
    ign = np.zeros(n, np.float32)
    o = n_of(0.07)
    ign[o:] = bp(white(n - o, seed + 1), 400, 5000) * env_ad(n - o, 0.01, 0.30) * 0.7
    whump = np.zeros(n, np.float32)
    whump[o:] = np.sin(2 * np.pi * 85 * t[:n - o]) * np.exp(-t[:n - o] / 0.12) * 0.6
    fizz = bp(white(n, seed + 2), 2500, 10000) * np.exp(-t / 0.9) * 0.10
    x = scratch + ign + whump + fizz
    return reverb(stereo(norm(x, 0.9), 0.1), rt=0.9, wet=0.25)


def crow(n_caws=3, seed=2, f0=560):
    r = rng(seed)
    out = np.zeros(n_of(0.5 * n_caws + 0.6), np.float32)
    for k in range(n_caws):
        d = r.uniform(0.28, 0.38)
        n = n_of(d)
        t = tt(d)
        f = f0 * r.uniform(0.9, 1.1) * (1 - 0.18 * t / d)
        ph = 2 * np.pi * np.cumsum(f) / SR
        tone = sum((1.0 / h) * np.sin(h * ph) for h in range(1, 14))
        rasp = 1 + 0.9 * lp(white(n, seed + k), 180)
        x = tone * rasp
        x = bp(x, 700, 3200) * 1.3 + bp(x, 300, 700) * 0.4
        x *= env_ad(n, 0.02, d * 0.45)
        o = n_of(k * r.uniform(0.42, 0.55))
        out[o:o + n] += x
    return reverb(stereo(norm(out, 0.8), r.uniform(-0.6, 0.6)), rt=2.0, wet=0.45)


def creak(dur=1.6, rate=(25, 70), seed=3, freqs=(380, 820, 1500, 2600), q=18):
    """Wooden door or gate creak: a stick-slip impulse train ringing wooden resonances."""
    r = rng(seed)
    n = n_of(dur)
    t = tt(dur)
    rate_t = rate[0] + (rate[1] - rate[0]) * (0.5 - 0.5 * np.cos(np.pi * t / dur)) * (1 + 0.15 * smooth_rand(n, 8, seed))
    ph = np.cumsum(rate_t) / SR
    idx = np.nonzero(np.diff(np.floor(ph)) > 0)[0]
    imp = np.zeros(n, np.float32)
    imp[idx] = r.uniform(0.4, 1.0, len(idx))
    x = sum(reson(imp, f * r.uniform(0.95, 1.05), q) * g for f, g in zip(freqs, (1.0, 0.8, 0.5, 0.25)))
    x *= np.maximum(np.sin(np.pi * np.clip(t / dur, 0, 1)), 0) ** 0.5
    return reverb(stereo(norm(x, 0.8), 0.0), rt=1.2, wet=0.3)


def knock(n=3, seed=4, spacing=0.32):
    r = rng(seed)
    out = np.zeros(n_of(spacing * n + 0.6), np.float32)
    for k in range(n):
        m = n_of(0.25)
        t = tt(0.25)
        x = lp(white(m, seed + k), 1400) * np.exp(-t / 0.012) * 0.8
        x += np.sin(2 * np.pi * 135 * t) * np.exp(-t / 0.06) * 0.9
        x += np.sin(2 * np.pi * 310 * t) * np.exp(-t / 0.035) * 0.4
        o = n_of(k * spacing * r.uniform(0.9, 1.1))
        out[o:o + m] += x * r.uniform(0.8, 1.0)
    return reverb(stereo(norm(out, 0.9), -0.1), rt=0.8, wet=0.3)


def thud(f=60, dur=1.2, seed=5, noise=0.6):
    t = tt(dur)
    n = len(t)
    x = np.sin(2 * np.pi * f * t * (1 - 0.2 * t)) * np.exp(-t / 0.25)
    x += lp(white(n, seed), 600) * np.exp(-t / 0.05) * noise
    return norm(x.astype(np.float32), 0.95)


def church_door(seed=6):
    c = creak(1.4, (18, 45), seed=seed, freqs=(220, 520, 1100, 2100))
    th = thud(55, 1.5, seed)
    th = reverb(stereo(th, 0.0), rt=3.0, wet=0.6)
    out = np.zeros((max(len(c), n_of(1.25) + len(th)), 2), np.float32)
    out[:len(c)] += c * 0.7
    o = n_of(1.25)
    out[o:o + len(th)] += th
    return out


def bell(f=150, dur=9.0, seed=7, strike=0.4):
    t = tt(dur)
    n = len(t)
    parts = [(0.5, 1.0, 5.5), (1.0, 0.8, 4.0), (1.19, 0.55, 3.0), (1.5, 0.35, 2.5), (2.0, 0.55, 2.2), (2.51, 0.25, 1.4),
             (2.98, 0.18, 1.1), (4.07, 0.12, 0.7), (5.2, 0.06, 0.4)]
    x = np.zeros(n, np.float32)
    for ratio, amp, tau in parts:
        for det in (-0.6, 0.6):
            x += amp * 0.5 * np.sin(2 * np.pi * (f * ratio + det) * t) * np.exp(-t / tau)
    x += hp(white(n, seed), 1500) * np.exp(-t / 0.015) * strike
    return reverb(stereo(norm(x, 0.9), 0.0), rt=4.0, wet=0.5)


def clock_ticks(dur, seed=8, rate=1.0):
    r = rng(seed)
    n = n_of(dur)
    out = np.zeros(n, np.float32)
    k = 0
    tk = 0.1
    while tk < dur - 0.1:
        m = n_of(0.08)
        t = tt(0.08)
        f = 1650 if k % 2 == 0 else 1320
        x = reson(white(m, seed + k) * np.exp(-t / 0.003), f, 12) * 3 + bp(white(m, seed + k + 1), 3000, 9000) * np.exp(-t / 0.002)
        o = n_of(tk)
        out[o:o + m] += x[: n - o] * r.uniform(0.8, 1.0)
        tk += 1.0 / rate
        k += 1
    return stereo(norm(out, 0.5), 0.3)


def thunder(dur=7.0, seed=9, crack=True):
    r = rng(seed)
    n = n_of(dur)
    t = tt(dur)
    rum = lp(brown(n, seed, 60), 220)
    bumps = smooth_rand(n, 3.5, seed, 0.1, 1.0) ** 2
    e = np.exp(-t / (dur * 0.35)) * np.clip(t / 0.08, 0, 1)
    x = rum * bumps * e
    if crack:
        x += hp(white(n, seed + 1), 300) * np.exp(-t / 0.08) * 0.5
    return reverb(stereo(norm(x, 0.95), r.uniform(-0.3, 0.3), 1.0), rt=3.5, wet=0.5, bright=3000)


def glass_break(seed=10):
    r = rng(seed)
    n = n_of(2.2)
    t = tt(2.2)
    x = bp(white(n, seed), 1800, 12000) * np.exp(-t / 0.18) * 0.8
    x += thud(90, 2.2, seed) * 0.5
    for k in range(55):
        o = n_of(r.uniform(0.0, 0.9) ** 1.6)
        f = r.uniform(2400, 9000)
        d = r.uniform(0.04, 0.22)
        m = n_of(d * 4)
        tk = tt(d * 4)
        ping = np.sin(2 * np.pi * f * tk) * np.exp(-tk / d) * r.uniform(0.1, 0.35)
        x[o:o + m] += ping[: n - o]
    return reverb(stereo(norm(x, 0.95), 0.1, 1.0), rt=1.4, wet=0.3)


def alarm_bell(dur=3.0, seed=11, f=1350):
    n = n_of(dur)
    t = tt(dur)
    x = np.zeros(n, np.float32)
    for ratio, amp in ((1, 1.0), (2.71, 0.4), (5.1, 0.2)):
        x += amp * np.sin(2 * np.pi * f * ratio * t)
    hammer = 0.55 + 0.45 * np.abs(np.sin(np.pi * 16 * t))
    x *= hammer * np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.2, 0, 1)
    return reverb(stereo(norm(x, 0.7), 0.4), rt=1.5, wet=0.35)


def siren(dur=8.0, seed=12, f0=180, f1=620):
    t = tt(dur)
    rise = np.clip(t / (dur * 0.35), 0, 1)
    fall = np.clip((dur - t) / (dur * 0.35), 0, 1)
    f = f0 + (f1 - f0) * np.minimum(rise, fall) ** 0.7
    f *= 1 + 0.004 * np.sin(2 * np.pi * 5 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)
    x *= np.minimum(rise, fall) ** 0.5
    x = lp(x, 1800)
    return reverb(stereo(norm(x, 0.6), -0.2, 1.0), rt=4.5, wet=0.75, bright=3000)


def doorbell(seed=13):
    out = np.zeros(n_of(3.0), np.float32)
    for k, f in enumerate((659.25, 523.25)):
        t = tt(2.2)
        x = sum(a * np.sin(2 * np.pi * f * r_ * t) * np.exp(-t / tau)
                for r_, a, tau in ((1, 1.0, 1.4), (2.76, 0.3, 0.5), (5.4, 0.12, 0.2)))
        o = n_of(0.55 * k)
        out[o:o + len(t)] += x
    return reverb(stereo(norm(out, 0.7), 0.2), rt=1.0, wet=0.3)


def heartbeat(dur=6.0, bpm=68, seed=14):
    n = n_of(dur)
    out = np.zeros(n, np.float32)
    per = 60.0 / bpm
    tk = 0.05
    while tk < dur - 0.4:
        for off, f, amp, tau in ((0.0, 58, 1.0, 0.07), (0.26, 48, 0.75, 0.06)):
            m = n_of(0.3)
            t = tt(0.3)
            x = np.sin(2 * np.pi * f * t * (1 - 0.3 * t)) * np.exp(-t / tau) * amp
            x += lp(white(m, seed), 300) * np.exp(-t / 0.01) * 0.3 * amp
            o = n_of(tk + off)
            out[o:o + m] += x[: n - o]
        tk += per
    return stereo(norm(out, 0.95), 0.0)


def radio_static(dur=6.0, seed=15, crackle=1.0):
    r = rng(seed)
    n = n_of(dur)
    x = bp(white(n, seed), 700, 4500) * 0.25
    x *= 0.7 + 0.3 * smooth_rand(n, 4, seed)
    k = int(dur * 30 * crackle)
    for _ in range(k):
        o = r.integers(0, n - 200)
        x[o:o + r.integers(20, 200)] += r.uniform(-1, 1) * r.uniform(0.2, 0.8)
    t = tt(dur)
    x += 0.05 * np.sin(2 * np.pi * 60 * t) + 0.03 * np.sin(2 * np.pi * 120 * t)
    return stereo(norm(x, 0.6), 0.0)


def bulletin_tone(seed=16):
    out = np.zeros(n_of(1.2), np.float32)
    for k in range(3):
        t = tt(0.16)
        x = np.sin(2 * np.pi * 1000 * t) * np.clip(t / 0.005, 0, 1) * np.clip((0.16 - t) / 0.005, 0, 1)
        o = n_of(0.27 * k)
        out[o:o + len(t)] += x
    return stereo(norm(bp(out, 300, 3000), 0.6))


def piano_note(f, dur=1.2, amp=1.0):
    t = tt(dur)
    x = sum((1.0 / h ** 1.3) * np.sin(2 * np.pi * f * h * (1 + 0.0004 * h * h) * t) * np.exp(-t * (1.5 + 0.6 * h))
            for h in range(1, 9))
    return (x * amp * np.clip(t / 0.004, 0, 1)).astype(np.float32)


def dance_music(dur=6.0, seed=17):
    """A little swing tune, as heard through a 1930s radio."""
    bpm = 132
    beat = 60 / bpm
    n = n_of(dur)
    out = np.zeros(n, np.float32)
    chords = [(130.81, 164.81, 196.0, 233.08), (174.61, 220.0, 261.63, 311.13), (130.81, 164.81, 196.0, 233.08),
              (196.0, 246.94, 293.66, 349.23)]
    bass = [65.41, 82.41, 98.0, 110.0, 87.31, 110.0, 130.81, 146.83, 65.41, 82.41, 98.0, 110.0, 98.0, 123.47, 146.83, 164.81]
    tk = 0.0
    i = 0
    while tk < dur - 0.3:
        o = n_of(tk)
        b = piano_note(bass[i % len(bass)], 0.5, 0.9)
        out[o:o + len(b)] += b[: n - o]
        if i % 2 == 1:
            for f in chords[(i // 4) % 4]:
                c = piano_note(f * 2, 0.35, 0.35)
                oc = o + n_of(beat * 0.33)
                out[oc:oc + len(c)] += c[: max(0, n - oc)]
        tk += beat
        i += 1
    x = np.tanh(bp(out, 280, 3200) * 2.5) * 0.6
    x += bp(white(n, seed), 1000, 4000) * 0.03
    return stereo(norm(x, 0.6), 0.0)


def screen_door(seed=18):
    c = creak(0.5, (60, 120), seed=seed, freqs=(900, 1800, 3200), q=25) * 0.5
    th = stereo(thud(110, 0.9, seed, noise=0.9), 0.2)
    r = rng(seed)
    out = np.zeros((n_of(1.8), 2), np.float32)
    out[:len(c)] += c[:len(out)]
    o = n_of(0.45)
    out[o:o + len(th)] += th[: len(out) - o]
    for k in range(5):
        m = n_of(0.03)
        oo = o + n_of(0.06 + 0.07 * k)
        out[oo:oo + m] += stereo(bp(white(m, seed + k), 800, 3000) * np.exp(-tt(0.03) / 0.008) * 0.4 * (0.7 ** k))
    return reverb(out, rt=0.9, wet=0.25)


def blow_out(seed=19):
    n = n_of(1.0)
    t = tt(1.0)
    x = bp(white(n, seed), 250, 3500) * np.maximum(np.sin(np.pi * np.clip(t / 0.45, 0, 1)), 0) ** 1.5 * 0.8
    x += bp(white(n, seed + 1), 80, 300) * np.exp(-((t - 0.25) / 0.12) ** 2) * 0.5
    return stereo(norm(x, 0.7), 0.0)


def type_click(seed=20):
    r = rng(seed)
    m = n_of(0.07)
    t = tt(0.07)
    x = bp(white(m, seed), 1500, 7000) * np.exp(-t / 0.004) * r.uniform(0.6, 1.0)
    x += reson(white(m, seed + 1), r.uniform(2100, 2700), 10) * np.exp(-t / 0.012) * 2.0
    x += np.sin(2 * np.pi * r.uniform(160, 220) * t) * np.exp(-t / 0.012) * 0.4
    return x.astype(np.float32)


def whoosh(dur=1.2, seed=21, up=True):
    n = n_of(dur)
    t = tt(dur)
    w_ = white(n, seed)
    lo = bp(w_, 200, 900)
    mid = bp(w_, 900, 3000)
    hi = bp(w_, 3000, 9000)
    p = t / dur if up else 1 - t / dur
    x = lo * (1 - p) + mid * np.sin(np.pi * p) + hi * p
    x *= np.maximum(np.sin(np.pi * np.clip(t / dur, 0, 1)), 0) ** 1.5
    return stereo(norm(x, 0.7), 0.0, 1.0)


def boom(seed=22, f0=85, f1=32, dur=3.0):
    t = tt(dur)
    n = len(t)
    f = f1 + (f0 - f1) * np.exp(-t / 0.4)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / 1.0)
    x += lp(white(n, seed), 500) * np.exp(-t / 0.06) * 0.5
    x = np.tanh(x * 1.4)
    return reverb(stereo(norm(x, 0.95), 0.0), rt=3.5, wet=0.5, bright=2500)


def swell(dur=2.5, seed=23):
    """Reverse-cymbal style rise into a hit."""
    n = n_of(dur)
    t = tt(dur)
    x = bp(white(n, seed), 2000, 12000) * (t / dur) ** 3
    x += bp(white(n, seed + 1), 300, 2000) * (t / dur) ** 4 * 0.5
    x[-n_of(0.02):] *= np.linspace(1, 0, n_of(0.02))
    return stereo(norm(x, 0.6), 0.0, 1.0)


def owl(seed=24):
    out = np.zeros(n_of(2.2), np.float32)
    for k, (o, d, f) in enumerate(((0.0, 0.32, 390), (0.55, 0.18, 370), (0.8, 0.5, 360))):
        t = tt(d)
        fr = f * (1 - 0.06 * t / d)
        ph = 2 * np.pi * np.cumsum(fr) / SR
        x = (np.sin(ph) + 0.15 * np.sin(2 * ph)) * np.maximum(np.sin(np.pi * t / d), 0) ** 1.2
        x += lp(white(len(t), seed + k), 600) * 0.05
        oo = n_of(o)
        out[oo:oo + len(t)] += x
    return reverb(stereo(norm(out, 0.6), rng(seed).uniform(-0.7, 0.7)), rt=2.5, wet=0.55)


def sting(dur=5.0, seed=25, notes=(587.33, 622.25, 880.0, 932.33)):
    """Dissonant string-like cluster swell."""
    t = tt(dur)
    n = len(t)
    x = np.zeros(n, np.float32)
    r = rng(seed)
    for f in notes:
        for v in range(3):
            fv = f * (1 + r.uniform(-0.003, 0.003))
            vib = 1 + 0.003 * np.sin(2 * np.pi * r.uniform(4.5, 6) * t + r.uniform(0, 6))
            ph = 2 * np.pi * np.cumsum(fv * vib) / SR
            x += sum((1 / h) * np.sin(h * ph) for h in range(1, 6)) * 0.2
    trem = 1 + 0.25 * np.sin(2 * np.pi * 7 * t)
    e = np.clip(t / (dur * 0.35), 0, 1) ** 2 * np.clip((dur - t) / (dur * 0.5), 0, 1)
    x = lp(x * trem * e, 4000)
    return reverb(stereo(norm(x, 0.6), 0.0, 1.0), rt=3.0, wet=0.5)


def music_box(notes, start_gap=0.42, seed=26, octave=1.0):
    """notes: list of (freq or None, beats)."""
    total = sum(b for _, b in notes) * start_gap + 3.0
    out = np.zeros(n_of(total), np.float32)
    tk = 0.0
    for f, b in notes:
        if f:
            d = 2.4
            t = tt(d)
            ff = f * octave
            x = (np.sin(2 * np.pi * ff * t) * np.exp(-t / 1.1) + 0.25 * np.sin(2 * np.pi * ff * 3 * t) * np.exp(-t / 0.3) +
                 0.12 * np.sin(2 * np.pi * ff * 4.2 * t) * np.exp(-t / 0.12))
            x *= np.clip(t / 0.002, 0, 1)
            o = n_of(tk)
            out[o:o + len(x)] += x[: len(out) - o]
        tk += b * start_gap
    return reverb(stereo(norm(out, 0.6), 0.15, 0.5), rt=3.0, wet=0.55)


# ----------------------------------------------------------------------------- beds (continuous)

def wind(dur, seed=30, strength=1.0, gusty=1.0):
    n = n_of(dur)
    out = np.zeros((n, 2), np.float32)
    for c in range(2):
        pn = pink(n, seed + c * 7)
        bands = [bp(pn, 180, 420), bp(pn, 420, 900), bp(pn, 900, 2000)]
        mods = [smooth_rand(n, 0.25 * gusty, seed + 10 + c * 3 + k, 0.15, 1.0) ** 2 for k in range(3)]
        x = bands[0] * mods[0] * 1.0 + bands[1] * mods[1] * 0.7 + bands[2] * mods[2] * 0.35
        # a faint whistle that drifts in pitch
        ft = 600 + 250 * smooth_rand(n, 0.15, seed + 20 + c)
        ph = 2 * np.pi * np.cumsum(ft) / SR
        x += np.sin(ph) * 0.03 * smooth_rand(n, 0.2, seed + 30 + c) ** 3
        out[:, c] = x
    return out / (np.abs(out).max() + 1e-9) * 0.5 * strength


def fire_bed(dur, seed=31, intensity=1.0):
    r = rng(seed)
    n = n_of(dur)
    roar = lp(brown(n, seed, 80), 500) * (0.6 + 0.4 * smooth_rand(n, 1.5, seed)) * 0.5
    x = roar
    k = int(dur * 22 * intensity)
    for _ in range(k):
        o = r.integers(0, max(1, n - 600))
        m = r.integers(40, 400)
        a = r.pareto(2.5) * 0.15
        c = hp(white(m, r.integers(1 << 30)), 1500) * np.exp(-np.arange(m) / (m / 4)) * a
        x[o:o + m] += c
    for _ in range(int(dur * 1.2 * intensity)):
        o = r.integers(0, max(1, n - 3000))
        m = 2400
        tk = np.arange(m) / SR
        pop = bp(white(m, r.integers(1 << 30)), 300, 2000) * np.exp(-tk / 0.01) * r.uniform(0.3, 0.8)
        x[o:o + m] += pop
    out = np.stack([x, np.roll(x, 37)], axis=1)
    return out / (np.abs(out).max() + 1e-9) * 0.5


def room_tone(dur, seed=32):
    n = n_of(dur)
    x = lp(brown(n, seed, 40), 300) * 0.3 + lp(white(n, seed + 1), 2000) * 0.02
    return stereo(x.astype(np.float32), 0.0, 1.0) * 0.4


def waves(dur, seed=33):
    r = rng(seed)
    n = n_of(dur)
    out = np.zeros((n, 2), np.float32)
    base = lp(brown(n, seed, 120), 700)
    sw = np.zeros(n, np.float32)
    tk = 0.0
    while tk < dur:
        d = r.uniform(3.5, 6.5)
        o, m = n_of(tk), n_of(d)
        e = np.maximum(np.sin(np.pi * np.linspace(0, 1, m)), 0) ** 2
        sw[o:o + m] += e[: n - o]
        tk += d * r.uniform(0.6, 0.9)
    splash = bp(white(n, seed + 1), 800, 5000) * sw ** 3 * 0.35
    x = base * (0.35 + 0.65 * sw) + splash
    out[:, 0], out[:, 1] = x, np.roll(x, 211)
    return out / (np.abs(out).max() + 1e-9) * 0.5


def rain(dur, seed=34):
    r = rng(seed)
    n = n_of(dur)
    x = hp(white(n, seed), 1200) * 0.15 + lp(hp(white(n, seed + 1), 300), 3000) * 0.1
    for _ in range(int(dur * 60)):
        o = r.integers(0, n - 300)
        m = r.integers(60, 300)
        x[o:o + m] += bp(white(m, r.integers(1 << 30)), 2000, 8000) * np.exp(-np.arange(m) / (m / 5)) * r.uniform(0.05, 0.3)
    out = np.stack([x, np.roll(x, 97)], axis=1)
    return out / (np.abs(out).max() + 1e-9) * 0.5


def leaves_bed(dur, seed=35):
    n = n_of(dur)
    x = bp(white(n, seed), 2500, 9000) * smooth_rand(n, 3, seed, 0, 1) ** 4
    return stereo(norm(x, 0.4), 0.0, 1.0)


def church_room(dur, seed=36):
    return reverb(room_tone(dur, seed) * 0.6, rt=3.0, wet=0.6)[:n_of(dur)]


def eerie_hum(dur, seed=37, f=55.0):
    t = tt(dur)
    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t + 1) + 0.3 * np.sin(2 * np.pi * (f * 2.01) * t)
    x *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t)
    return stereo((x * 0.3).astype(np.float32), 0.0, 1.0)


# ----------------------------------------------------------------------------- music

NOTE = {}
for i, nm in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]):
    for octv in range(0, 8):
        NOTE["%s%d" % (nm, octv)] = 440.0 * 2 ** ((i - 9) / 12 + (octv - 4))
for _sharp, _flat in (("C#", "Db"), ("D#", "Eb"), ("F#", "Gb"), ("G#", "Ab"), ("A#", "Bb")):
    for octv in range(0, 8):
        NOTE["%s%d" % (_flat, octv)] = NOTE["%s%d" % (_sharp, octv)]


def pad(dur, freqs, seed=40, bright=1400, attack=3.0, release=3.0):
    """Warm detuned pad (band-limited saw voices through a soft low-pass)."""
    t = tt(dur)
    n = len(t)
    x = np.zeros(n, np.float32)
    r = rng(seed)
    for f in freqs:
        for v in range(3):
            fv = f * (1 + (v - 1) * 0.004)
            ph0 = r.uniform(0, 6.28)
            hmax = max(1, int(bright * 2 / fv))
            for h in range(1, min(hmax, 12) + 1):
                x += (0.6 / h) * np.sin(2 * np.pi * fv * h * t + ph0 * h)
    x = lp(x, bright)
    e = np.minimum(np.clip(t / attack, 0, 1), np.clip((dur - t) / release, 0, 1))
    x *= e * (0.85 + 0.15 * np.sin(2 * np.pi * 0.11 * t))
    return stereo(norm(x, 0.5), 0.0, 1.0)


def drone(dur, seed=41, root=36.71):
    t = tt(dur)
    x = (np.sin(2 * np.pi * root * t) * 0.8 + np.sin(2 * np.pi * root * 2 * t + 0.5) * 0.6 +
         np.sin(2 * np.pi * root * 3.0 * t + 1.1) * 0.25 + np.sin(2 * np.pi * (root * 2 + 0.15) * t) * 0.4)
    x += lp(pink(len(t), seed), 200) * 0.25
    x *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.05 * t)
    return stereo(norm(x.astype(np.float32), 0.5), 0.0, 1.0)


def choir(dur, freqs, seed=42, attack=2.5, release=2.5):
    t = tt(dur)
    n = len(t)
    x = np.zeros(n, np.float32)
    r = rng(seed)
    for f in freqs:
        for v in range(4):
            fv = f * (1 + r.uniform(-0.006, 0.006))
            vib = 1 + 0.004 * np.sin(2 * np.pi * r.uniform(4.6, 5.6) * t + r.uniform(0, 6))
            ph = 2 * np.pi * np.cumsum(fv * vib) / SR
            src = sum((1.0 / h) * np.sin(h * ph) for h in range(1, int(4000 / f)))
            x += src.astype(np.float32)
    y = bp(x, 550, 900) * 1.0 + bp(x, 1000, 1300) * 0.55 + bp(x, 2300, 2900) * 0.25
    e = np.minimum(np.clip(t / attack, 0, 1), np.clip((dur - t) / release, 0, 1))
    y = (y * e).astype(np.float32)
    return reverb(stereo(norm(y, 0.5), 0.0, 1.0), rt=3.5, wet=0.6)[:n]
