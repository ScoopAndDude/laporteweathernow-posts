#!/usr/bin/env python3
"""Music and sounds for the La Porte County hauntings documentary, written in code (original, so there's
nothing for YouTube's Content ID to match). Everything is 48 kHz stereo float32.

    cue(name, seconds, seed) -> np.ndarray (n, 2)       the music for one chapter
    sfx(name, seed) -> np.ndarray (n, 2)                one sound effect

The theme is an original ballad in A minor (6/8), heard on a glass harmonica (the parlor instrument of the
seance years), a music box, a piano, a small organ and a low pad, over lake waves, wind and rails. The
synthesizers are the Belle Gunness film's; the tunes and the sounds of the lake, the seance and the trains
are new.
"""
import math

import numpy as np
from scipy import signal

SR = 48000
A4 = 440.0
NOTE = {"C": -9, "C#": -8, "Db": -8, "D": -7, "D#": -6, "Eb": -6, "E": -5, "F": -4, "F#": -3, "Gb": -3, "G": -2,
        "G#": -1, "Ab": -1, "A": 0, "A#": 1, "Bb": 1, "B": 2}


def hz(n):
    """'D4' -> frequency."""
    name, octv = n[:-1], int(n[-1])
    return A4 * 2 ** ((NOTE[name] + 12 * (octv - 4)) / 12)


def t_axis(sec):
    return np.arange(int(sec * SR), dtype=np.float32) / SR


def env(n, a=0.01, r=0.2, sustain=1.0):
    e = np.full(n, sustain, np.float32)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    na, nr = min(na, n), min(nr, n)
    e[:na] = np.linspace(0, sustain, na, dtype=np.float32)
    e[n - nr:] *= np.linspace(1, 0, nr, dtype=np.float32)
    return e


def lowpass(x, cutoff, order=2):
    b, a = signal.butter(order, min(0.99, cutoff / (SR / 2)), "low")
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


def highpass(x, cutoff, order=2):
    b, a = signal.butter(order, min(0.99, cutoff / (SR / 2)), "high")
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(0.99, hi / (SR / 2))], "band")
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


_IR = {}


def reverb(x, seconds=2.8, wet=0.3, seed=1, damp=4500):
    """Stereo convolution reverb with a made-up hall (decaying filtered noise)."""
    key = (seconds, seed, damp)
    if key not in _IR:
        rng = np.random.default_rng(seed)
        n = int(seconds * SR)
        tt = np.arange(n) / SR
        decay = np.exp(-6.9 * tt / seconds).astype(np.float32)
        ir = rng.normal(0, 1, (n, 2)).astype(np.float32) * decay[:, None]
        ir = lowpass(ir, damp)
        ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))[:, None]
        ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))
        _IR[key] = ir
    ir = _IR[key]
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    out = np.zeros((len(x) + len(ir) - 1, 2), np.float32)
    for ch in range(2):
        out[:, ch] = signal.fftconvolve(x[:, ch], ir[:, ch], mode="full")
    out = out[: len(x)]
    return (x * (1 - wet) + out * wet * 2.2).astype(np.float32)


def place(buf, snd, at, gain=1.0, pan=0.0):
    """Mix a (mono or stereo) sound into buf (n, 2) at time `at` seconds."""
    i = int(at * SR)
    if i >= len(buf) or i + len(snd) <= 0:
        return
    if snd.ndim == 1:
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        snd = np.stack([snd * l * 1.414, snd * r * 1.414], axis=1)
    j0 = max(0, -i)
    j1 = min(len(snd), len(buf) - i)
    buf[i + j0: i + j1] += snd[j0:j1] * gain


# ------------------------------------------------------------------------------------------ instruments
def music_box(freq, dur=2.4, seed=0):
    tt = t_axis(dur)
    rng = np.random.default_rng(seed)
    out = np.zeros_like(tt)
    for k, (ratio, amp, dec) in enumerate(((1.0, 1.0, 1.6), (2.0, 0.28, 0.9), (2.76, 0.16, 0.55), (5.40, 0.07, 0.3), (8.93, 0.035, 0.18))):
        f = freq * ratio * (1 + rng.normal(0, 0.0007))
        out += amp * np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) * np.exp(-tt * (1 / dec) * (1 + k * 0.15))
    click = np.exp(-tt * 900) * rng.normal(0, 0.05, len(tt))
    out = (out + click) * env(len(tt), 0.002, 0.08)
    return out.astype(np.float32)


def piano(freq, dur=3.5, vel=0.8, seed=0):
    tt = t_axis(dur)
    rng = np.random.default_rng(seed)
    out = np.zeros_like(tt)
    for k in range(1, 9):
        inh = 1 + 0.0004 * k * k
        amp = vel * (0.9 ** k) / k ** 0.6
        dec = 2.6 / (1 + 0.45 * k) * (220 / max(110.0, freq)) ** 0.35
        out += amp * np.sin(2 * np.pi * freq * k * inh * tt + rng.uniform(0, 6.28)) * np.exp(-tt / dec)
    out += 0.4 * vel * np.sin(2 * np.pi * freq * 1.0015 * tt) * np.exp(-tt / 3.2)      # a second string, a little out
    hammer = lowpass(rng.normal(0, 1, len(tt)).astype(np.float32), 2500) * np.exp(-tt * 120) * 0.12 * vel
    out = (out + hammer) * env(len(tt), 0.003, 0.25)
    return (out / 2.4).astype(np.float32)


def bell(freq, dur=7.0, seed=0):
    tt = t_axis(dur)
    rng = np.random.default_rng(seed)
    out = np.zeros_like(tt)
    for ratio, amp, dec in ((0.5, 0.5, 5.5), (1.0, 1.0, 4.2), (1.19, 0.4, 3.0), (1.5, 0.35, 2.6), (2.0, 0.3, 2.2), (2.74, 0.18, 1.4), (3.76, 0.1, 0.9)):
        out += amp * np.sin(2 * np.pi * freq * ratio * tt + rng.uniform(0, 6.28)) * np.exp(-tt / dec)
    out *= env(len(tt), 0.004, 0.5)
    return (out / 2.2).astype(np.float32)


def saw(freq, tt, detune=0.0, phase=0.0):
    f = freq * (1 + detune)
    ph = (f * tt + phase) % 1.0
    return (2 * ph - 1).astype(np.float32)


def pad(notes, dur, cutoff=1100, attack=1.6, release=2.2, seed=0, bright=0.0):
    """A soft string-like chord (several detuned saws, filtered)."""
    tt = t_axis(dur)
    rng = np.random.default_rng(seed)
    out = np.zeros((len(tt), 2), np.float32)
    for n in notes:
        f = hz(n)
        for v in range(3):
            d = (v - 1) * 0.0035 + rng.normal(0, 0.0007)
            s = saw(f, tt, d, rng.uniform(0, 1))
            pan = (v - 1) * 0.6
            out[:, 0] += s * (1 - pan) * 0.5
            out[:, 1] += s * (1 + pan) * 0.5
    lfo = 1 + 0.25 * np.sin(2 * np.pi * 0.11 * tt + rng.uniform(0, 6.28))
    out = lowpass(out, cutoff * (1 + bright), order=2)
    out = lowpass(out, cutoff * 1.6 * (1 + bright), order=1)
    out *= (env(len(tt), attack, release) * lfo.astype(np.float32))[:, None]
    return out / (len(notes) * 3) * 1.6


def drone(note, dur, seed=0, level=1.0):
    tt = t_axis(dur)
    f = hz(note)
    rng = np.random.default_rng(seed)
    s = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2 * tt + 1) + 0.12 * np.sin(2 * np.pi * f * 3.01 * tt)
    trem = 1 + 0.18 * np.sin(2 * np.pi * 0.07 * tt + rng.uniform(0, 6.28))
    return (s * trem * env(len(tt), 3.0, 3.0) * 0.35 * level).astype(np.float32)


def noise(dur, seed=0):
    return np.random.default_rng(seed).normal(0, 1, int(dur * SR)).astype(np.float32)


def wind(dur, seed=0, level=1.0):
    n = noise(dur, seed)
    tt = t_axis(dur)
    out = np.zeros((len(n), 2), np.float32)
    for ch, (lo, hi, rate) in enumerate(((180, 900, 0.09), (220, 1100, 0.07))):
        b = bandpass(n if ch == 0 else np.roll(n, 9000), lo, hi)
        m = 0.5 + 0.5 * np.sin(2 * np.pi * rate * tt + ch * 2) * np.sin(2 * np.pi * rate * 0.37 * tt + 1)
        out[:, ch] = b * (0.25 + 0.75 * m ** 2)
    return out * 0.12 * level * env(len(n), 2.0, 2.0)[:, None]


def heartbeat(dur, bpm=58, seed=0, level=1.0):
    out = np.zeros(int(dur * SR), np.float32)
    beat = 60.0 / bpm
    tt = t_axis(0.35)
    def thump(f, a):
        return (np.sin(2 * np.pi * f * tt * (1 - 0.4 * tt)) * np.exp(-tt * 18) * a).astype(np.float32)
    lub, dub = thump(55, 1.0), thump(48, 0.7)
    t = 0.3
    while t < dur - 0.4:
        i = int(t * SR)
        out[i:i + len(lub)] += lub[: len(out) - i]
        j = int((t + 0.28) * SR)
        if j < len(out):
            out[j:j + len(dub)] += dub[: len(out) - j]
        t += beat
    return lowpass(out, 160) * 0.6 * level


def tick(dur, rate=1.0, seed=0, level=1.0):
    out = np.zeros(int(dur * SR), np.float32)
    rng = np.random.default_rng(seed)
    tt = t_axis(0.03)
    for k in range(int(dur * rate)):
        f = 3000 if k % 2 else 2400
        c = (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 300) + rng.normal(0, 0.3, len(tt)) * np.exp(-tt * 500)).astype(np.float32)
        i = int((k / rate + 0.1) * SR)
        if i + len(c) < len(out):
            out[i:i + len(c)] += c * 0.35
    return highpass(out, 900) * level


def rumble(dur, seed=0, level=1.0):
    n = noise(dur, seed)
    r = lowpass(lowpass(n, 90), 120) * 2.2
    tt = t_axis(dur)
    m = 0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * tt) * np.sin(2 * np.pi * 0.051 * tt + 2)
    return (r * m * env(len(n), 2.5, 2.5) * level).astype(np.float32)


def crackle(dur, seed=0, level=1.0, rate=14.0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    k = int(dur * rate)
    for _ in range(k):
        i = int(rng.integers(0, max(1, n - 2000)))
        L = int(rng.integers(40, 900))
        a = rng.uniform(0.1, 1.0) ** 2
        out[i:i + L] += rng.normal(0, a, L).astype(np.float32) * np.exp(-np.arange(L) / (L / 4)).astype(np.float32)
    return highpass(out, 700) * 0.5 * level + lowpass(noise(dur, seed + 1), 300) * 0.05 * level


# ------------------------------------------------------------------------------------------ this film's instruments
def glass(freq, dur=4.0, seed=0):
    """A glass-harmonica-like tone: pure partials, a slow swell, a slight shimmer."""
    tt = t_axis(dur)
    rng = np.random.default_rng(seed)
    vib = 1 + 0.002 * np.sin(2 * np.pi * rng.uniform(4.6, 5.6) * tt + rng.uniform(0, 6.28))
    ph = 2 * np.pi * freq * np.cumsum(vib) / SR
    x = np.sin(ph) + 0.16 * np.sin(2 * ph + 0.4) + 0.05 * np.sin(3 * ph + 1.3)
    trem = 1 + 0.07 * np.sin(2 * np.pi * rng.uniform(2.6, 3.4) * tt + rng.uniform(0, 6.28))
    e = env(len(tt), a=min(0.35, dur * 0.2), r=min(1.8, dur * 0.55))
    return (x * trem * e * 0.42).astype(np.float32)


def organ(notes, dur, seed=0, cutoff=2400, attack=0.4, release=1.4):
    """A small church organ chord (a few drawbars), soft."""
    tt = t_axis(dur)
    rng = np.random.default_rng(seed)
    out = np.zeros(len(tt), np.float32)
    for n in notes:
        f = hz(n)
        for mult, amp in ((0.5, 0.3), (1.0, 1.0), (2.0, 0.45), (3.0, 0.18), (4.0, 0.14), (6.0, 0.05)):
            out += (amp * np.sin(2 * np.pi * f * mult * tt + rng.uniform(0, 6.28))).astype(np.float32)
    wob = (1 + 0.03 * np.sin(2 * np.pi * 5.5 * tt)).astype(np.float32)
    out = lowpass(out * wob, cutoff)
    return (out * env(len(tt), attack, release) / (len(notes) * 1.6)).astype(np.float32)


def waves(dur, seed=0, level=1.0, period=7.0):
    """Lake waves: swells of low noise, each with a wash of spray."""
    n = noise(dur + 1, seed)
    tt = t_axis(dur + 1)
    rng = np.random.default_rng(seed)
    out = np.zeros((len(n), 2), np.float32)
    for ch in range(2):
        nn = np.roll(n, ch * 7000)
        lo = lowpass(nn, 500)
        hi = bandpass(nn, 700, 4500)
        e = np.zeros(len(tt), np.float32)
        t = rng.uniform(0, 2)
        while t < dur + 1:
            per = period * rng.uniform(0.75, 1.25)
            k = (tt - t) / per
            m = (k >= 0) & (k < 1)
            e[m] += (np.sin(np.pi * k[m]) ** 2 * np.exp(-2.5 * k[m]) * rng.uniform(0.6, 1.0)).astype(np.float32)
            t += per * rng.uniform(0.55, 0.85)
        out[:, ch] = lo * (0.35 + 0.65 * e) * 0.8 + hi * e ** 1.5 * 0.35
    out = out[: int(dur * SR)]
    return out * 0.18 * level * env(len(out), 1.5, 1.5)[:, None]


def foghorn(dur=4.5, seed=0):
    """A fog signal far down the pier, very low."""
    tt = t_axis(dur)
    f = 110 * (1 - 0.06 * np.clip((tt - dur + 0.8) / 0.8, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph) + 0.12 * np.sin(4 * ph)
    e = np.clip(tt / 0.25, 0, 1) * np.clip((dur - tt) / 0.9, 0, 1)
    return lowpass((x * e).astype(np.float32), 700) * 0.4


def chug(dur, bpm=84, seed=0, level=1.0):
    """A steam train far off: steady puffs of filtered noise."""
    out = np.zeros(int(dur * SR), np.float32)
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm / 2
    L = int(0.22 * SR)
    shape = np.exp(-np.arange(L) / (L / 5)).astype(np.float32)
    t, k = 0.2, 0
    while t < dur - 0.3:
        i = int(t * SR)
        puff = bandpass(rng.normal(0, 1, L).astype(np.float32), 300, 2200) * shape * (1.0 if k % 2 == 0 else 0.6)
        out[i:i + L] += puff[: len(out) - i]
        t += beat
        k += 1
    sway = (0.7 + 0.3 * np.sin(2 * np.pi * 0.05 * t_axis(dur))).astype(np.float32)
    return out * sway * 0.25 * level * env(len(out), 2.5, 2.5)


def drum_hit(seed=0, size=1.0):
    """A bass drum struck once in a dark room."""
    tt = t_axis(1.6)
    rng = np.random.default_rng(seed)
    f = 62 * size ** -0.3 * (1 + 0.6 * np.exp(-tt * 30))
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-tt * 4.2)
    skin = lowpass(rng.normal(0, 1, len(tt)).astype(np.float32), 900) * np.exp(-tt * 40) * 0.5
    return (body + skin).astype(np.float32) * 0.9


# ------------------------------------------------------------------------------------------ the theme
# An original ballad in A minor, 6/8. Each entry: (note or None for a rest, eighth notes).
H_THEME = [("A4", 2), ("C5", 1), ("E5", 2), ("D5", 1), ("C5", 2), ("B4", 1), ("A4", 3),
           ("G4", 2), ("A4", 1), ("B4", 2), ("C5", 1), ("B4", 2), ("G#4", 1), ("E4", 3)]
H_THEME_B = [("A4", 2), ("C5", 1), ("E5", 2), ("A5", 1), ("G5", 2), ("F5", 1), ("E5", 3),
             ("D5", 2), ("C5", 1), ("B4", 2), ("G#4", 1), ("A4", 6)]
AM, F, G, E = ["A2", "E3", "A3", "C4"], ["F2", "C3", "F3", "A3"], ["G2", "D3", "G3", "B3"], ["E2", "B2", "E3", "G#3"]
C, DM = ["C3", "G3", "C4", "E4"], ["D3", "A3", "D4", "F4"]
H_PROG_A = [AM, F, G, E]                          # under H_THEME, one chord a bar
H_PROG_B = [AM, C, E, AM]                         # under H_THEME_B
H_PROG_SUS = [["A2", "E3", "B3", "C4"], ["F2", "C3", "E3", "B3"], ["D3", "A3", "C4", "E4"], ["E2", "B2", "D3", "A3"]]
HYMN = [AM, F, C, G, AM, DM, E, AM]
PENTA = ["A4", "C5", "D5", "E5", "G5", "A5", "E4", "G4"]


def melody(buf, start, notes, beat, inst="box", oct_shift=0, gain=1.0, seed=0, swing=0.0, pan=0.0):
    t = start
    rng = np.random.default_rng(seed)
    for i, (n, b) in enumerate(notes):
        if n:
            name, o = n[:-1], int(n[-1]) + oct_shift
            f = hz(f"{name}{o}")
            jitter = rng.normal(0, 0.008) + (swing * beat if i % 3 == 1 else 0)
            if inst == "box":
                place(buf, music_box(f, 2.6, seed + i), t + jitter, gain * 0.55, pan)
            elif inst == "piano":
                place(buf, piano(f, 4.0, 0.75, seed + i), t + jitter, gain * 0.9, pan)
            elif inst == "bell":
                place(buf, bell(f, 6.0, seed + i), t + jitter, gain * 0.5, pan)
            elif inst == "glass":
                place(buf, glass(f, max(1.2, b * beat * 1.6), seed + i), t + jitter, gain * 0.9, pan)
            elif inst == "organ":
                place(buf, organ([f"{name}{o}"], max(0.8, b * beat * 1.05), seed + i, attack=0.08, release=0.5), t, gain * 1.4, pan)
        t += b * beat
    return t


def chords(buf, start, prog, bar, bars, cutoff=1000, gain=1.0, seed=0, bright=0.0):
    t = start
    for k in range(bars):
        notes = prog[k % len(prog)]
        place(buf, pad(notes, bar + 2.0, cutoff, attack=min(1.6, bar * 0.4), release=2.0, seed=seed + k, bright=bright), t, gain)
        t += bar
    return t


def organ_chords(buf, start, prog, bar, bars, gain=1.0, seed=0):
    t = start
    for k in range(bars):
        place(buf, organ(prog[k % len(prog)], bar + 1.2, seed + k), t, gain, 0.0)
        t += bar
    return t


def piano_arps(buf, start, prog, bar, bars, beat_div=6, gain=1.0, seed=0, low=True):
    t = start
    for k in range(bars):
        notes = prog[k % len(prog)]
        pattern = [0, 1, 2, 3, 2, 1][:beat_div]
        for j, idx in enumerate(pattern):
            n = notes[idx % len(notes)]
            name, o = n[:-1], int(n[-1]) + (0 if low else 1)
            place(buf, piano(hz(f"{name}{o}"), 3.0, 0.5 + 0.2 * (j == 0), seed + k * 10 + j), t + j * bar / beat_div, gain * 0.55)
        t += bar
    return t


# ------------------------------------------------------------------------------------------ cues
def cue(name, seconds, seed=1):
    seconds = max(2.0, float(seconds))
    n = int(seconds * SR) + SR * 4
    buf = np.zeros((n, 2), np.float32)
    e8 = 0.36                      # an eighth note: a slow 6/8
    bar = e8 * 6                   # 2.16 s
    phrase = bar * 4               # one statement of a theme
    nb = int(seconds / bar) + 2
    rng = np.random.default_rng(seed)

    def loop(fn, every, first=0.0):
        t = first
        while t < seconds:
            fn(t)
            t += every

    if name == "open":
        place(buf, waves(seconds + 2, seed, 0.9), 0, 1.0)
        place(buf, wind(seconds + 2, seed + 1, 0.8), 0, 0.8)
        place(buf, drone("A1", seconds + 2, seed, 1.0), 0, 0.8)
        place(buf, drone("E2", seconds + 2, seed + 1, 0.5), 0, 0.5)
        loop(lambda t: place(buf, bell(hz("A2"), 7.0, seed + int(t)), t + 1.0, 0.3, -0.3), 13.0)
        loop(lambda t: melody(buf, t + 3.0, H_THEME[:7], e8 * 1.3, "glass", 0, 0.8, seed + int(t), pan=0.25), phrase * 2.2)
    elif name == "title":
        place(buf, drone("A1", seconds + 2, seed, 1.2), 0, 0.9)
        place(buf, pad(["A2", "E3", "A3", "C4", "E4"], seconds + 1, 1500, attack=0.6, release=3.0, seed=seed), 0, 1.0)
        place(buf, bell(hz("A2"), 8.0, seed), 0.05, 0.6)
        place(buf, rumble(seconds + 1, seed, 1.0), 0, 0.8)
        melody(buf, 1.4, H_THEME[:4], e8 * 1.4, "glass", 0, 0.7, seed, pan=0.15)
    elif name == "door":
        place(buf, wind(seconds + 2, seed, 0.7), 0, 0.7)
        piano_arps(buf, 0.3, H_PROG_A, bar, nb, 6, 0.7, seed)
        chords(buf, 0.0, H_PROG_A, bar, nb, 700, 0.4, seed + 5)
        loop(lambda t: melody(buf, t, H_THEME if int(t / phrase) % 4 == 0 else H_THEME_B, e8, "glass", 0, 0.6, seed + int(t), pan=0.2),
             phrase * 2, first=phrase)
    elif name == "keeper":
        place(buf, waves(seconds + 2, seed, 1.1, period=6.5), 0, 1.0)
        chords(buf, 0.0, H_PROG_A + H_PROG_B, bar, nb, 900, 0.6, seed)
        loop(lambda t: melody(buf, t, H_THEME, e8 * 1.05, "box", 0, 0.75, seed + int(t), pan=0.25), phrase * 2.0, first=bar)
        loop(lambda t: melody(buf, t, H_THEME_B, e8 * 1.05, "box", 0, 0.55, seed + 40 + int(t), pan=-0.25), phrase * 2.0, first=bar + phrase)
        loop(lambda t: place(buf, foghorn(4.5, seed + int(t)), t, 0.35, -0.5), 31.0, first=9.0)
    elif name == "parlor":                       # a slow parlor waltz under a clock
        beat = 0.62
        place(buf, tick(seconds + 2, 1.0, seed, 0.7), 0, 0.5)
        prog = [AM, DM, E, AM, F, DM, E, E]
        t, k = 0.3, 0
        while t < seconds:
            ch = prog[k % len(prog)]
            place(buf, piano(hz(ch[0]), 3.0, 0.7, seed + k), t, 0.55, -0.1)
            for j in (1, 2):
                for nn in ch[1:]:
                    place(buf, piano(hz(nn), 1.4, 0.35, seed + k * 7 + j), t + j * beat, 0.22, 0.1)
            t += beat * 3
            k += 1
        loop(lambda t: melody(buf, t, H_THEME, beat * 0.5 * 1.5, "box", 0, 0.6, seed + int(t), pan=0.3), beat * 3 * 8, first=beat * 3 * 2)
    elif name == "spirits":                      # the dark room: low drone, a slow pulse and the glass, almost nothing else
        place(buf, drone("A1", seconds + 2, seed, 1.0), 0, 0.9)
        place(buf, drone("D#2", seconds + 2, seed + 4, 0.25), 0, 0.3)
        place(buf, heartbeat(seconds + 2, 50, seed, 0.7), 0, 0.6)
        place(buf, wind(seconds + 2, seed, 0.4), 0, 0.5)
        def ghost(t):
            for j in range(3):
                nn = PENTA[int(rng.integers(0, len(PENTA)))]
                place(buf, glass(hz(nn), float(rng.uniform(3.0, 5.5)), seed + int(t) + j), t + j * float(rng.uniform(1.4, 2.6)), 0.5,
                      float(rng.uniform(-0.6, 0.6)))
        loop(ghost, 9.0, first=1.0)
        chords(buf, 0.0, H_PROG_SUS, bar * 3, int(seconds / (bar * 3)) + 1, 600, 0.35, seed)
    elif name == "graves":
        chords(buf, 0.0, H_PROG_B, bar * 2, int(seconds / (bar * 2)) + 1, 650, 0.7, seed)
        loop(lambda t: place(buf, bell(hz("A2"), 8.0, seed + int(t)), t + 1.5, 0.45, 0.0), 9.5)
        place(buf, drone("A1", seconds + 2, seed, 1.0), 0, 0.6)
        place(buf, wind(seconds + 2, seed, 0.7), 0, 0.7)
        loop(lambda t: melody(buf, t, H_THEME_B, e8 * 1.25, "glass", -1, 0.5, seed + int(t), pan=-0.2), phrase * 2.5, first=phrase)
    elif name == "chapel":
        place(buf, wind(seconds + 2, seed, 0.8), 0, 0.8)
        organ_chords(buf, 0.2, HYMN, bar * 1.5, int(seconds / (bar * 1.5)) + 1, 0.9, seed)
        loop(lambda t: melody(buf, t, H_THEME, e8 * 1.5, "organ", 0, 0.5, seed + int(t)), bar * 1.5 * 16, first=bar * 1.5 * 8)
        loop(lambda t: place(buf, bell(hz("E3"), 7.0, seed + int(t)), t, 0.2, 0.4), 17.0, first=4.0)
    elif name == "rails":
        place(buf, chug(seconds + 2, 84, seed, 1.0), 0, 0.7)
        chords(buf, 0.0, H_PROG_A, bar * 2, int(seconds / (bar * 2)) + 1, 650, 0.55, seed)
        def ost(t):
            for j, nn in enumerate(["A2", "A2", "E2", "G2"]):
                place(buf, piano(hz(nn), 2.5, 0.6, seed + int(t) + j), t + j * e8 * 2, 0.5)
        loop(ost, e8 * 8)
        loop(lambda t: melody(buf, t, H_THEME, e8, "glass", 0, 0.45, seed + int(t), pan=0.3), phrase * 3, first=phrase)
    elif name == "war":
        place(buf, tick(seconds + 2, 2.0, seed, 0.6), 0, 0.45)
        chords(buf, 0.0, [AM, AM, F, E], bar, nb, 650, 0.7, seed)
        def pulse(t):
            place(buf, drum_hit(seed + int(t * 10), 0.8), t, 0.35, 0.0)
            place(buf, piano(hz("A1"), 2.0, 0.7, seed + int(t)), t, 0.4, 0.0)
        loop(pulse, bar / 2)
        loop(lambda t: melody(buf, t, H_THEME_B, e8, "piano", -1, 0.45, seed + int(t), pan=-0.2), phrase * 2, first=phrase)
    elif name == "end":
        place(buf, waves(seconds + 2, seed, 0.6), 0, 0.7)
        chords(buf, 0.0, H_PROG_A + H_PROG_B, bar, nb, 800, 0.6, seed)
        tt = melody(buf, 1.0, H_THEME, e8 * 1.1, "piano", 0, 0.7, seed)
        tt = melody(buf, tt, H_THEME_B, e8 * 1.1, "glass", 0, 0.7, seed + 9)
        melody(buf, tt + bar, H_THEME, e8 * 1.25, "box", 0, 0.5, seed + 19)
    else:
        place(buf, drone("A1", seconds + 2, seed, 1.0), 0, 0.8)
    out = reverb(buf, 3.4, 0.34, seed=3)
    out = out[: int(seconds * SR)]
    e = env(len(out), 1.2, 2.0)                  # gentle fade at both ends
    out *= e[:, None]
    peak = float(np.abs(out).max()) or 1.0
    return (out / peak * 0.5).astype(np.float32)


# ------------------------------------------------------------------------------------------ sound effects
def sfx(name, seed=0):
    x = _sfx(name, seed)
    peak = float(np.abs(x).max()) or 1.0
    return (x * (0.7 / peak)).astype(np.float32)


def _sfx(name, seed=0):
    rng = np.random.default_rng(seed)
    if name == "page":                        # a newspaper page turned
        n = noise(0.7, seed)
        tt = t_axis(0.7)
        e = np.exp(-((tt - 0.25) / 0.12) ** 2) + 0.5 * np.exp(-((tt - 0.45) / 0.08) ** 2)
        return bandpass(n, 900, 7000) * e.astype(np.float32) * 0.5
    if name == "type":                        # a few typewriter keys
        out = np.zeros(int(1.6 * SR), np.float32)
        t = 0.0
        for k in range(10):
            tt = t_axis(0.05)
            c = (rng.normal(0, 1, len(tt)) * np.exp(-tt * 160) + np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt * 220) * 0.6).astype(np.float32)
            i = int(t * SR)
            out[i:i + len(c)] += c * rng.uniform(0.5, 1.0)
            t += rng.uniform(0.08, 0.16)
        return highpass(out, 600) * 0.35
    if name == "chapter":                     # a low hit with a long tail for chapter cards
        tt = t_axis(4.0)
        boom = np.sin(2 * np.pi * 45 * tt * (1 - 0.3 * tt / 4)) * np.exp(-tt * 1.4)
        hiss = lowpass(noise(4.0, seed), 1200) * np.exp(-tt * 2.0) * 0.15
        return reverb((boom + hiss).astype(np.float32) * 0.6, 3.0, 0.4, seed=5)
    if name == "bell":
        return reverb(bell(hz("A2"), 8.0, seed) * 0.7, 3.0, 0.4)
    if name == "train":                       # a steam whistle far off
        tt = t_axis(2.6)
        f0 = hz("A4")
        tone = sum(np.sin(2 * np.pi * f0 * r * tt + k) * a for k, (r, a) in enumerate(((1, 1), (1.26, 0.7), (1.5, 0.6))))
        e = np.clip(tt / 0.15, 0, 1) * np.clip((2.6 - tt) / 0.6, 0, 1)
        breath = bandpass(noise(2.6, seed), 500, 3000) * 0.25
        return reverb(((tone * 0.3 + breath) * e).astype(np.float32) * 0.5, 3.0, 0.55)
    if name == "waves":                       # one wave on the pier
        return waves(6.0, seed, 1.6, period=4.0)
    if name == "wind":                        # a gust
        return wind(5.0, seed, 2.0)
    if name == "drum":                        # Old King's bass drum, in the dark
        return reverb(drum_hit(seed) * 0.9, 2.6, 0.45, seed=7)
    if name == "flash":                       # Cathcart's flash: a flare of powder and a hiss
        tt = t_axis(1.4)
        pop = rng.normal(0, 1, len(tt)).astype(np.float32) * np.exp(-tt * 22)
        hiss = highpass(rng.normal(0, 1, len(tt)).astype(np.float32), 3000) * np.exp(-tt * 4) * 0.25
        thump = np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 20) * 0.6
        return reverb((lowpass(pop, 4500) * 0.6 + hiss + thump).astype(np.float32), 1.8, 0.35)
    if name == "triangle":                    # struck twice, somewhere in the dark
        tt = t_axis(3.5)
        def ring(f0):
            return sum(a * np.sin(2 * np.pi * f0 * r * tt) * np.exp(-tt / d) for r, a, d in ((1.0, 1.0, 1.6), (2.76, 0.5, 1.0), (5.40, 0.3, 0.6), (8.93, 0.15, 0.4)))
        out = np.zeros(int(4.2 * SR), np.float32)
        a = (ring(1320.0) * 0.4).astype(np.float32)
        out[: len(a)] += a
        out[int(0.55 * SR): int(0.55 * SR) + len(a)] += a[: len(out) - int(0.55 * SR)] * 0.7
        return reverb(out, 3.0, 0.5)
    if name == "foghorn":
        return reverb(foghorn(4.5, seed), 3.5, 0.5)
    if name == "crowd":
        n = noise(6.0, seed)
        tt = t_axis(6.0)
        m = 0.6 + 0.4 * np.sin(2 * np.pi * 0.9 * tt) * np.sin(2 * np.pi * 0.37 * tt + 1)
        v = bandpass(n, 250, 1800) * m.astype(np.float32)
        return np.stack([v, np.roll(v, 4000)], axis=1) * 0.25 * env(len(n), 1.0, 1.5)[:, None]
    if name == "camera":                      # an old camera's flash powder and shutter
        tt = t_axis(1.2)
        pop = rng.normal(0, 1, len(tt)).astype(np.float32) * np.exp(-tt * 18)
        return reverb(lowpass(pop, 3000) * 0.4, 2.0, 0.3)
    if name == "heart":
        return heartbeat(4.0, 60, seed, 1.2)
    if name == "thud":
        tt = t_axis(1.5)
        return (np.sin(2 * np.pi * 60 * tt) * np.exp(-tt * 7) + lowpass(noise(1.5, seed), 400) * np.exp(-tt * 12) * 0.4).astype(np.float32) * 0.8
    if name == "whoosh":
        n = noise(1.4, seed)
        tt = t_axis(1.4)
        e = np.sin(np.pi * np.clip(tt / 1.4, 0, 1)) ** 2
        return bandpass(n, 300, 2500) * e.astype(np.float32) * 0.3
    if name == "fire":
        return np.stack([crackle(6.0, seed, 1.0, 26) + rumble(6.0, seed, 0.7)] * 2, axis=1) * env(int(6.0 * SR), 0.8, 2.0)[:, None]
    return np.zeros(int(0.5 * SR), np.float32)
