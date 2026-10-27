"""Sounds the older reels didn't need: an iron cell door, keys, water dripping in a cell block, a foghorn, a steam
whistle and a freight train's rumble. All synthesized (mono, 48 kHz), so nothing has to be licensed."""
import math

import numpy as np

import sfx as X
from reels_common import SR


def _norm(x, peak=0.8):
    return (x / max(1e-6, float(np.abs(x).max())) * peak).astype(np.float32)


def clang(seed=1, dur=2.6):
    """A heavy iron door slamming shut and ringing in a stone room."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for f, a, d in ((112, 1.0, 1.4), (237, 0.7, 1.0), (391, 0.5, 0.8), (583, 0.35, 0.6), (847, 0.25, 0.45),
                    (1290, 0.18, 0.3), (1911, 0.1, 0.2)):
        f *= r.uniform(0.97, 1.03)
        out += a * np.sin(2 * np.pi * f * t + r.uniform(0, 6.28)) * np.exp(-t / d)
    hit = X.bp(r.normal(0, 1, int(0.05 * SR)).astype(np.float32), 300, 5000) * np.exp(-np.linspace(0, 8, int(0.05 * SR)))
    out[:len(hit)] += hit * 1.6
    thump = np.sin(2 * np.pi * 55 * t) * np.exp(-t / 0.12)
    out += thump * 0.9
    out = X.reverb(X.stereo(_norm(out), 0.0), rt=2.2, wet=0.45).mean(1)
    return _norm(out)


def keys(seed=2, dur=1.2):
    """A ring of keys jingling."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    t = 0.02
    while t < dur - 0.15:
        m = int(0.06 * SR)
        tt = np.arange(m) / SR
        f = r.uniform(3200, 7400)
        x = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.02) + 0.3 * r.normal(0, 1, m) * np.exp(-tt / 0.005)
        i = int(t * SR)
        out[i:i + m] += x[: n - i] * r.uniform(0.3, 1.0)
        t += r.uniform(0.02, 0.09)
    return _norm(X.reverb(X.stereo(out, 0.1), rt=0.8, wet=0.25).mean(1), 0.6)


def drips(dur, seed=3):
    """Slow drops of water in a stone cell block."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    t = 0.4
    while t < dur - 0.3:
        m = int(0.09 * SR)
        tt = np.arange(m) / SR
        f0 = r.uniform(900, 1500)
        x = np.sin(2 * np.pi * (f0 + 2200 * tt) * tt) * np.exp(-tt / 0.018)
        i = int(t * SR)
        out[i:i + m] += x[: n - i] * r.uniform(0.4, 1.0)
        t += r.uniform(0.9, 2.2)
    return _norm(X.reverb(X.stereo(out, 0.0), rt=2.6, wet=0.55).mean(1), 0.5)


def foghorn(seed=4, dur=3.5):
    """A distant diaphone foghorn: a low two-tone groan."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.clip(t / 0.25, 0, 1) * np.clip((dur - 0.6 - t) / 0.6, 0, 1)
    f = np.where(t < dur * 0.55, 150.0, 128.0)
    ph = np.cumsum(f) / SR
    x = sum(a * np.sin(2 * np.pi * k * ph) for k, a in ((1, 1.0), (2, 0.5), (3, 0.3), (4, 0.15)))
    x = X.lp(x.astype(np.float32), 900) * env
    return _norm(X.reverb(X.stereo(x, 0.0), rt=3.0, wet=0.6).mean(1), 0.7)


def whistle(seed=5, dur=2.4):
    """A steam locomotive's chime whistle, a long way off."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.clip(t / 0.15, 0, 1) * np.clip((dur - 0.4 - t) / 0.4, 0, 1)
    x = sum(np.sin(2 * np.pi * f * t + k) for k, f in enumerate((370.0, 466.0, 554.0)))
    x = x + 0.4 * np.random.default_rng(seed).normal(0, 1, n)
    x = X.bp(x.astype(np.float32), 300, 2500) * env
    return _norm(X.reverb(X.stereo(x, 0.2), rt=2.4, wet=0.55).mean(1), 0.5)


def rumble(dur, seed=6, clack=True):
    """A freight train rolling past: low rumble with the clack of wheels over rail joints."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    x = X.lp(X.brown(n, seed, 30), 220) * 0.8
    if clack:
        t = 0.1
        while t < dur - 0.1:
            for dt in (0.0, 0.12):
                m = int(0.04 * SR)
                c = X.bp(r.normal(0, 1, m).astype(np.float32), 200, 1500) * np.exp(-np.linspace(0, 9, m))
                i = int((t + dt) * SR)
                if i + m < n:
                    x[i:i + m] += c * 0.5
            t += 0.62
    swell = np.sin(np.linspace(0, math.pi, n)) ** 0.6
    return _norm(x * swell, 0.7)


def bed(kind, dur, seed=1):
    """A long ambience under a scene, mono."""
    if kind == "wind":
        return X.wind(dur, seed=40 + seed, strength=0.75).mean(1)
    if kind == "rain":
        return X.rain(dur, seed=44 + seed).mean(1)
    if kind == "waves":
        return X.waves(dur, seed=33 + seed).mean(1)
    if kind == "room":
        return X.room_tone(dur, seed=32 + seed).mean(1)
    if kind == "rumble":
        return rumble(dur, seed=6 + seed)
    return None


def accent(kind, seed=1):
    """A one-off sound placed early in a scene, mono (or None)."""
    if kind == "owl":
        return X.owl(seed=24 + seed).mean(1)
    if kind == "creak":
        return X.creak(1.8, seed=23 + seed).mean(1)
    if kind == "bell":
        return X.bell(f=150, dur=6.0, seed=7 + seed).mean(1) * 0.6
    if kind == "clang":
        return clang(seed)
    if kind == "drip":
        return drips(6.0, seed)
    if kind == "foghorn":
        return foghorn(seed)
    if kind == "whistle":
        return whistle(seed)
    if kind == "keys":
        return keys(seed)
    if kind == "thunder":
        return X.thunder(5.0, seed=12 + seed).mean(1)
    if kind == "knock":
        return X.knock(3, seed=4 + seed).mean(1)
    if kind == "heartbeat":
        return X.heartbeat(3.0, bpm=70, seed=14 + seed).mean(1)
    if kind == "music_box":
        import audio as AU
        N = AU.N
        return X.music_box([(N["E5"], 1), (N["G5"], 1), (N["E5"], 1), (N["D5"], 1), (N["C5"], 2), (None, 1),
                            (N["E5"], 1), (N["D5"], 1), (N["C5"], 1), (N["A4"], 2)], start_gap=0.5, seed=27).mean(1)
    if kind == "siren_far":
        return None                     # left out on purpose: an active prison's siren isn't a sound effect
    return None
