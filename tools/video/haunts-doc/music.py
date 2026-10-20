#!/usr/bin/env python3
"""Music and sounds for the Belle Gunness documentary, written in code (original, so there's nothing for
YouTube's Content ID to match). Everything is 48 kHz stereo float32.

    cue(name, seconds, seed) -> np.ndarray (n, 2)       the music for one chapter
    sfx(name, seed) -> np.ndarray (n, 2)                one sound effect

The theme is an original lullaby in D minor (3/4) heard on a music box, a piano and a low pad.
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


# ------------------------------------------------------------------------------------------ the theme
# Original lullaby in D minor, 3/4. Each entry: (note or None for a rest, beats).
THEME = [("A4", 1), ("D5", 1), ("F5", 1), ("E5", 2), ("D5", 1), ("C#5", 1), ("D5", 1), ("E5", 1), ("A4", 3),
         ("Bb4", 1), ("D5", 1), ("G5", 1), ("F5", 2), ("E5", 1), ("D5", 1), ("C#5", 1), ("E5", 1), ("D5", 3)]
THEME_B = [("F5", 1), ("E5", 1), ("D5", 1), ("C5", 2), ("Bb4", 1), ("A4", 1), ("Bb4", 1), ("G4", 1), ("A4", 3),
           ("D5", 1), ("C5", 1), ("Bb4", 1), ("A4", 2), ("G4", 1), ("F4", 1), ("E4", 1), ("C#5", 1), ("D5", 3)]
PROG_A = [["D3", "A3", "D4", "F4"], ["Bb2", "F3", "Bb3", "D4"], ["F2", "C3", "F3", "A3"], ["A2", "E3", "A3", "C#4"]]
PROG_B = [["G2", "D3", "G3", "Bb3"], ["D3", "A3", "D4", "F4"], ["Bb2", "F3", "Bb3", "D4"], ["A2", "E3", "G3", "C#4"]]
PROG_SUS = [["D3", "A3", "E4", "A4"], ["Bb2", "F3", "C4", "E4"], ["G2", "D3", "A3", "D4"], ["A2", "E3", "B3", "E4"]]


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
        t += b * beat
    return t


def chords(buf, start, prog, bar, bars, cutoff=1000, gain=1.0, seed=0, bright=0.0):
    t = start
    for k in range(bars):
        notes = prog[k % len(prog)]
        place(buf, pad(notes, bar + 2.0, cutoff, attack=min(1.6, bar * 0.4), release=2.0, seed=seed + k, bright=bright), t, gain)
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
    beat = 0.72                    # a slow 3/4
    bar = beat * 3
    rng = np.random.default_rng(seed)

    def loop(fn, every):
        t = 0.0
        while t < seconds:
            fn(t)
            t += every

    if name == "open":
        place(buf, wind(seconds + 2, seed, 1.2), 0, 1.0)
        place(buf, drone("D2", seconds + 2, seed, 1.0), 0, 0.8)
        loop(lambda t: place(buf, bell(hz("D3"), 7.0, seed + int(t)), t + 1.0, 0.35, -0.3), 11.0)
        loop(lambda t: melody(buf, t + 3.0, THEME[:9], beat * 1.25, "box", 0, 0.8, seed + int(t), pan=0.25), 22.0)
    elif name == "title":
        place(buf, drone("D2", seconds + 2, seed, 1.2), 0, 0.9)
        place(buf, pad(["D3", "A3", "D4", "F4", "A4"], seconds + 1, 1600, attack=0.6, release=3.0, seed=seed), 0, 1.0)
        place(buf, bell(hz("D3"), 8.0, seed), 0.05, 0.6)
        place(buf, rumble(seconds + 1, seed, 1.0), 0, 0.8)
    elif name == "norway":
        place(buf, drone("D2", seconds + 2, seed, 0.8), 0, 0.7)
        place(buf, drone("A2", seconds + 2, seed + 1, 0.5), 0, 0.5)
        chords(buf, 0.5, PROG_SUS, bar * 4, int(seconds / (bar * 4)) + 1, 900, 0.7, seed)
        loop(lambda t: melody(buf, t + 2.0, THEME, beat * 1.15, "box", 0, 0.7, seed + int(t), pan=0.2), bar * 4 * 4)
        place(buf, wind(seconds + 2, seed + 3, 0.6), 0, 0.8)
    elif name == "chicago":
        place(buf, tick(seconds + 2, 1.0, seed, 0.8), 0, 0.6)
        chords(buf, 0.0, PROG_A, bar * 2, int(seconds / (bar * 2)) + 1, 800, 0.8, seed)
        loop(lambda t: place(buf, piano(hz("D2"), 5.0, 0.8, seed + int(t)), t + 0.2, 0.7), bar * 2)
        loop(lambda t: melody(buf, t + bar * 4, THEME_B, beat, "piano", -1, 0.55, seed + int(t), pan=-0.2), bar * 2 * 8)
    elif name == "farm":
        piano_arps(buf, 0.3, PROG_A, bar * 2, int(seconds / (bar * 2)) + 1, 6, 0.75, seed)
        chords(buf, 0.0, PROG_A, bar * 2, int(seconds / (bar * 2)) + 1, 700, 0.45, seed + 5)
        loop(lambda t: melody(buf, t + bar * 4, THEME, beat * 1.1, "piano", 0, 0.5, seed + int(t)), bar * 2 * 8)
    elif name == "ads":
        chords(buf, 0.0, PROG_A, bar * 2, int(seconds / (bar * 2)) + 1, 650, 0.5, seed)
        loop(lambda t: melody(buf, t + 0.5, THEME, beat * 0.95, "box", 0, 0.75, seed + int(t), swing=0.05, pan=0.3), bar * 6)
        loop(lambda t: melody(buf, t + 0.5 + bar * 6 * 0.5, THEME_B, beat * 0.95, "box", 1, 0.35, seed + 50 + int(t), pan=-0.4), bar * 12)
    elif name == "suitors":
        place(buf, heartbeat(seconds + 2, 56, seed, 1.0), 0, 0.9)
        place(buf, drone("D2", seconds + 2, seed, 1.0), 0, 0.8)
        chords(buf, 0.0, [["D3", "Eb3", "A3"], ["D3", "E3", "Bb3"]], bar * 4, int(seconds / (bar * 4)) + 1, 600, 0.6, seed)
        loop(lambda t: place(buf, bell(hz("A2"), 7.0, seed + int(t)), t + 4.0, 0.25, 0.3), 16.0)
    elif name == "lamphere":
        place(buf, tick(seconds + 2, 1.25, seed, 0.7), 0, 0.6)
        def ost(t):
            for j, nn in enumerate(["D2", "D2", "Eb2", "D2"]):
                place(buf, piano(hz(nn), 3.0, 0.7, seed + int(t) + j), t + j * beat, 0.6)
        loop(ost, beat * 4)
        chords(buf, 0.0, [["D3", "F3", "A3"], ["D3", "F3", "Bb3"], ["C#3", "E3", "A3"]], bar * 3, int(seconds / (bar * 3)) + 1, 700, 0.6, seed)
    elif name == "fire":
        place(buf, rumble(seconds + 2, seed, 1.4), 0, 1.0)
        place(buf, crackle(seconds + 2, seed, 1.0, rate=20), 0, 0.7)
        sw = pad(["D3", "Eb3", "A3", "D4", "Eb4"], seconds + 1, 900, attack=seconds * 0.6, release=2.5, seed=seed)
        place(buf, sw, 0, 1.0)
        loop(lambda t: place(buf, bell(hz("D3"), 7.0, seed + int(t)), t + 2.0, 0.3, -0.2), 13.0)
    elif name == "digging":
        chords(buf, 0.0, PROG_B, bar * 3, int(seconds / (bar * 3)) + 1, 650, 0.8, seed)
        loop(lambda t: place(buf, bell(hz("D2"), 8.0, seed + int(t)), t + 1.5, 0.45, 0.0), 9.0)
        place(buf, drone("D1", seconds + 2, seed, 1.0), 0, 0.6)
        place(buf, wind(seconds + 2, seed, 0.5), 0, 0.6)
    elif name == "crowds":
        chords(buf, 0.0, PROG_A, bar * 2, int(seconds / (bar * 2)) + 1, 700, 0.6, seed)
        loop(lambda t: melody(buf, t + 0.4, THEME, beat * 0.8, "box", 1, 0.45, seed + int(t), swing=0.08, pan=0.4), bar * 6)
    elif name == "doubt":
        chords(buf, 0.0, PROG_SUS, bar * 3, int(seconds / (bar * 3)) + 1, 1300, 0.6, seed, bright=0.3)
        loop(lambda t: melody(buf, t + 2.5, [(n, b) for n, b in reversed(THEME)], beat * 1.3, "box", 0, 0.5, seed + int(t), pan=-0.3), bar * 12)
        place(buf, wind(seconds + 2, seed, 0.5), 0, 0.6)
    elif name == "trial":
        place(buf, tick(seconds + 2, 1.0, seed, 0.9), 0, 0.6)
        piano_arps(buf, 0.0, PROG_B, bar * 2, int(seconds / (bar * 2)) + 1, 3, 0.7, seed)
        chords(buf, 0.0, PROG_B, bar * 2, int(seconds / (bar * 2)) + 1, 650, 0.5, seed + 3)
    elif name == "sightings":
        place(buf, wind(seconds + 2, seed, 1.0), 0, 0.9)
        chords(buf, 0.0, PROG_SUS, bar * 4, int(seconds / (bar * 4)) + 1, 900, 0.5, seed)
        loop(lambda t: melody(buf, t + 1.5, THEME_B, beat * 1.2, "box", 0, 0.6, seed + int(t), pan=0.35), bar * 12)
    elif name == "dna":
        chords(buf, 0.0, PROG_SUS, bar * 2, int(seconds / (bar * 2)) + 1, 1500, 0.55, seed, bright=0.2)
        def pl(t):
            for j, nn in enumerate(["D4", "A4", "E5", "A4", "F5", "A4"]):
                place(buf, music_box(hz(nn), 1.2, seed + j), t + j * beat / 2, 0.22, 0.4 if j % 2 else -0.4)
        loop(pl, beat * 3)
    elif name == "end":
        chords(buf, 0.0, PROG_A, bar * 3, int(seconds / (bar * 3)) + 1, 750, 0.6, seed)
        tt = melody(buf, 1.0, THEME, beat * 1.2, "piano", 0, 0.7, seed)
        melody(buf, tt + bar, THEME_B, beat * 1.3, "box", 0, 0.6, seed + 9)
        place(buf, wind(seconds + 2, seed, 0.6), 0, 0.6)
    else:
        place(buf, drone("D2", seconds + 2, seed, 1.0), 0, 0.8)
    out = reverb(buf, 3.2, 0.32, seed=3)
    out = out[: int(seconds * SR)]
    # gentle fade at both ends
    e = env(len(out), 1.2, 2.0)
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
    if name == "fire":
        return np.stack([crackle(6.0, seed, 1.0, 26) + rumble(6.0, seed, 0.7)] * 2, axis=1) * env(int(6.0 * SR), 0.8, 2.0)[:, None]
    if name == "bell":
        return reverb(bell(hz("D3"), 8.0, seed) * 0.7, 3.0, 0.4)
    if name == "train":                       # a steam whistle far off
        tt = t_axis(2.6)
        f0 = hz("A4")
        tone = sum(np.sin(2 * np.pi * f0 * r * tt + k) * a for k, (r, a) in enumerate(((1, 1), (1.26, 0.7), (1.5, 0.6))))
        e = np.clip(tt / 0.15, 0, 1) * np.clip((2.6 - tt) / 0.6, 0, 1)
        breath = bandpass(noise(2.6, seed), 500, 3000) * 0.25
        return reverb(((tone * 0.3 + breath) * e).astype(np.float32) * 0.5, 3.0, 0.55)
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
    if name == "gavel":
        tt = t_axis(0.8)
        knock = (np.sin(2 * np.pi * 180 * tt) * np.exp(-tt * 40) + lowpass(noise(0.8, seed), 2000) * np.exp(-tt * 60)).astype(np.float32)
        out = np.zeros(int(1.6 * SR), np.float32)
        out[: len(knock)] += knock
        out[int(0.45 * SR): int(0.45 * SR) + len(knock)] += knock * 0.9
        return reverb(out * 0.6, 1.6, 0.3)
    return np.zeros(int(0.5 * SR), np.float32)
