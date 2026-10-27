"""Mix the soundtrack: narration, score, ambience and effects, timed to the shot list.

python3 audio.py OUT.wav
"""
import math
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

import sfx as X
from sfx import SR, n_of
from core import ROOT, sstep

import shots as S


def db(g):
    return 10 ** (g / 20.0)


class Bus:
    def __init__(self, n, ch=2):
        self.a = np.zeros((n, ch), np.float32)
        self.n = n

    def add(self, x, t, gain_db=0.0):
        if x.ndim == 1:
            x = np.stack([x, x], axis=1)
        o = int(round(t * SR))
        if o < 0:
            x = x[-o:]
            o = 0
        m = min(len(x), self.n - o)
        if m > 0:
            self.a[o:o + m] += x[:m] * db(gain_db)


AMB = {
    "match": [("room", -34), ("wind", -36)], "hearth": [("fire", -27), ("wind", -26)], "road": [("wind", -22)],
    "graveyard": [("wind", -23)], "carving": [("room", -31), ("wind", -38)], "carried": [("wind", -23)],
    "lanterns": [("wind", -24)], "dolmen": [("wind", -23), ("hum", -33)], "map_irl": [("wind", -33)],
    "harvest": [("wind", -26)], "twilight": [("wind", -26)], "mound": [("wind", -25), ("hum", -34)],
    "hawthorn": [("wind", -23)], "offering": [("wind", -25)], "chair": [("fire", -31), ("room", -32)],
    "guisers_fire": [("fire", -22), ("wind", -30)], "bonfire": [("fire", -22), ("wind", -28)], "relight": [("fire", -24)],
    "manuscript": [("room", -32)], "triptych": [("fire", -31), ("wind", -31)], "church": [("wind", -24)],
    "chapel": [("church", -26)], "votive": [("church", -28)], "three_candles": [("church", -30)],
    "blend": [("wind", -28), ("fire", -30)], "soul_cakes": [("room", -30)], "guisers_lane": [("wind", -24)],
    "door": [("room", -30)], "ghost_kid": [("wind", -32)], "mangels": [("wind", -24)], "crossroads": [("wind", -22)],
    "gate": [("wind", -22)], "coal": [("fire", -30)], "wanders": [("wind", -23)], "bog": [("wind", -23), ("hum", -36)],
    "parlor": [("fire", -27), ("clock", -30)], "kale": [("wind", -26)], "nuts": [("fire", -22)],
    "gutter": [("room", -30), ("wind", -30)], "saucers": [("room", -30), ("clock", -33)],
    "stones": [("wind", -26), ("fire", -36)], "mirror": [("room", -30), ("clock", -31)], "skulls": [("wind", -24)],
    "ship": [("waves", -19), ("rain", -26), ("wind", -24)], "atlantic": [("waves", -34)], "vs": [("room", -32)],
    "patch": [("wind", -26)], "jack1": [("wind", -32)], "jack2": [("wind", -32)],
    "victorian": [("room", -30), ("clock", -34)], "town1900": [("wind", -26), ("leaves", -32)],
    "rope": [("wind", -26), ("leaves", -34)], "soap": [("wind", -30)], "streetcar": [("wind", -28)],
    "town_ugly": [("wind", -26)], "alarm": [("wind", -28)], "window": [("wind", -30)], "porch_dark": [("wind", -26)],
    "party": [("wind", -32)], "radio_room": [("static", -36), ("clock", -34)], "radio": [("static", -31)],
    "bulletin": [("static", -27)], "tripod": [("wind", -24), ("hum", -26)], "dial": [("static", -28)],
    "tripod2": [("wind", -24), ("hum", -27)], "search": [("wind", -28)], "ration": [("room", -32), ("clock", -34)],
    "50s": [("wind", -32), ("leaves", -36)], "candy_table": [("room", -32)], "apple": [("room", -32)],
    "candy_table2": [("room", -32)], "candy_table3": [("room", -32)], "xray": [("hum", -34), ("room", -34)],
    "texas": [("wind", -30)], "town9": [("wind", -28)], "texas2": [("wind", -30)], "door_shadow": [("room", -30)],
    "porch_now": [("wind", -32)], "m_bonfire": [("fire", -28)], "m_turnips": [("wind", -30)], "m_dog": [("wind", -32)],
    "m_road": [("wind", -26)], "laporte": [("wind", -28), ("leaves", -34)], "fire1908": [("fire", -17)],
    "portrait": [("room", -32)], "town_night": [("wind", -26)], "belles": [("wind", -30), ("leaves", -36)],
    "party_porch": [("wind", -32)], "sky": [("wind", -32)], "outro": [("wind", -26)],
}

GEN = {"wind": lambda d, s: X.wind(d, s), "fire": lambda d, s: X.fire_bed(d, s), "room": lambda d, s: X.room_tone(d, s),
       "clock": lambda d, s: X.clock_ticks(d, s), "waves": lambda d, s: X.waves(d, s), "rain": lambda d, s: X.rain(d, s),
       "leaves": lambda d, s: X.leaves_bed(d, s), "church": lambda d, s: X.church_room(d, s),
       "hum": lambda d, s: X.eerie_hum(d, s), "static": lambda d, s: X.radio_static(d, s)}

N = X.NOTE
PROG = {
    0: [("D2", "A3", "D4", "F4"), ("Bb1", "F3", "Bb3", "D4"), ("G1", "G3", "Bb3", "D4"), ("A1", "A3", "C#4", "E4")],
    1: [("D2", "A3", "E4", "F4"), ("G1", "G3", "Bb3", "D4"), ("Bb1", "F3", "Bb3", "D4"), ("A1", "E3", "A3", "C#4")],
    2: [("D2", "A3", "D4", "F4"), ("F1", "F3", "A3", "C4"), ("C2", "G3", "C4", "E4"), ("D2", "A3", "D4", "F4")],
    3: [("D2", "A3", "D4", "F4"), ("Bb1", "F3", "Bb3", "D4"), ("F1", "F3", "A3", "C4"), ("A1", "A3", "C#4", "E4")],
    4: [("G1", "G3", "Bb3", "D4"), ("D2", "A3", "D4", "F4"), ("Eb2", "G3", "Bb3", "Eb4"), ("A1", "A3", "C#4", "E4")],
    5: [("D2", "A3", "D4", "F4"), ("C2", "G3", "C4", "E4"), ("Bb1", "F3", "Bb3", "D4"), ("A1", "A3", "C#4", "E4")],
    6: [("D2", "A3", "D4", "F4"), ("G1", "G3", "Bb3", "D4"), ("C2", "G3", "C4", "E4"), ("F1", "F3", "A3", "C4")],
    7: [("D2", "A3", "D4", "F4"), ("Eb2", "G3", "Bb3", "Eb4"), ("D2", "A3", "D4", "F4"), ("A1", "A3", "C#4", "E4")],
    8: [("D2", "A3", "D4", "F4"), ("F1", "F3", "A3", "C4"), ("Bb1", "F3", "Bb3", "D4"), ("A1", "A3", "C#4", "E4")],
    9: [("G1", "G3", "Bb3", "D4"), ("Eb2", "G3", "Bb3", "Eb4"), ("C2", "G3", "C4", "Eb4"), ("D2", "A3", "D4", "F#4")],
    10: [("D2", "A3", "D4", "F4"), ("Bb1", "F3", "Bb3", "D4"), ("F1", "F3", "A3", "C4"), ("C2", "G3", "C4", "E4")],
    11: [("D2", "A3", "D4", "F4"), ("Bb1", "F3", "Bb3", "D4"), ("G1", "G3", "Bb3", "D4"), ("A1", "A3", "C#4", "E4")],
    12: [("D2", "A3", "D4", "F4"), ("Bb1", "F3", "Bb3", "D4"), ("F1", "F3", "A3", "C4"), ("D2", "A3", "D4", "F4")],
}
MOTIF = [("A4", 1), ("D5", 1), ("F5", 1), ("E5", 1), ("D5", 1), ("C#5", 1), ("D5", 2), ("A4", 1), ("Bb4", 1), ("G4", 1),
         ("E4", 1), ("F4", 1), ("E4", 1), ("D4", 3)]


def motif(k=None, gap=0.42):
    notes = MOTIF if k is None else MOTIF[:k]
    return X.music_box([(N[nm], b) for nm, b in notes], start_gap=gap)


def main(out):
    tl, shots, ovs, total = S.build()
    n = n_of(total + 1.0)
    voice = Bus(n, 1)
    music = Bus(n)
    amb = Bus(n)
    fx = Bus(n)
    w = tl.w
    P = tl

    # ------------------------------------------------------------------ narration
    a, sr = sf.read(os.path.join(ROOT, "doc", "narration.wav"), dtype="float32")
    a48 = resample_poly(a, 2, 1).astype(np.float32)
    a48 = X.hp(a48, 70)
    pk = np.abs(a48).max()
    a48 *= db(-3.0) / pk
    for q in tl.list:
        i0, i1 = int(max(0, q["start"] - 0.04) * SR), int((q["end"] + 0.08) * SR)
        clip = a48[i0:i1]
        voice.add(clip[:, None], q["s"] - 0.04)

    # ------------------------------------------------------------------ ambience beds, crossfading with the shots
    for i, s in enumerate(shots):
        beds = AMB.get(s.name)
        if not beds:
            continue
        fi = max(0.6, s.fade)
        fn = max(0.6, shots[i + 1].fade if i + 1 < len(shots) else 0.6)
        t0 = s.t - fi / 2
        t1 = s.end + fn / 2
        d = t1 - t0
        for k, (kind, g) in enumerate(beds):
            x = GEN[kind](d, 1000 + i * 7 + k)
            x = x[:n_of(d)]
            m = len(x)
            e = np.ones(m, np.float32)
            a_, b_ = n_of(fi), n_of(fn)
            e[:a_] = np.linspace(0, 1, a_)
            e[m - b_:] = np.minimum(e[m - b_:], np.linspace(1, 0, b_))
            if s.name == "outro":
                # the wind dies away at the very end
                tt_ = np.arange(m) / SR + t0
                E = P(12, 4)["e"]
                e *= 1 - np.clip((tt_ - (E - 4.0)) / 5.0, 0, 1)
            amb.add(x * e[:, None], t0, g)

    # ------------------------------------------------------------------ effects
    def sh(name):
        return [s for s in shots if s.name == name][0]

    T6 = P(0, 6)["e"]
    fx.add(X.creak(1.8, (22, 50), seed=3), 0.05, -20)
    fx.add(X.match_strike(), 0.80, -12)
    fx.add(X.crow(2, seed=5), 3.4, -22)
    for k, tk in enumerate((0.9, 3.2)):
        fx.add(X.stereo(X.thud(140, 0.6, 40 + k, noise=1.0), 0.6), sh("hearth").t + tk, -24)
    fx.add(X.owl(seed=6), sh("road").t + 1.0, -24)
    fx.add(X.crow(3, seed=7), sh("graveyard").t + 1.2, -21)
    for k, tk in enumerate((w(0, 3, "You carve"), w(0, 3, "Something ugly"), w(0, 3, "Something meant"))):
        fx.add(X.stereo(X.bp(X.white(n_of(0.35), 50 + k), 800, 5000) * np.exp(-np.arange(n_of(0.35)) / SR / 0.08)
                        * 0.6, 0.1), tk + 0.3, -26)
    fx.add(X.owl(seed=8), sh("lanterns").t + 2.0, -25)
    fx.add(X.sting(6.0, seed=9), sh("dolmen").t + 1.0, -22)
    # title
    fx.add(X.swell(2.0), T6 + 0.5 - 2.0 + 0.6, -20)
    music.add(X.boom(), T6 + 0.6, -10)
    music.add(motif(), T6 + 1.0, -16)
    music.add(X.choir(7.5, [N["D3"], N["A3"], N["F4"]], seed=12), T6 + 0.4, -24)
    # chapter cards: soft hit + a phrase of the music box
    for s in shots:
        if s.name.startswith("ch") and s.name[2:].isdigit():
            music.add(X.boom(seed=30 + int(s.name[2:]), f0=70, f1=30, dur=2.5), s.t + 0.1, -16)
            music.add(motif(5, 0.45), s.t + 0.5, -20)
    # Samhain
    fx.add(X.crow(4, seed=11), sh("harvest").t + 1.0, -26)
    fx.add(X.owl(seed=12), sh("hawthorn").t + 1.5, -26)
    for k, nm in enumerate(("Fire.", "Disguises.", "And the dead")):
        music.add(X.boom(seed=40 + k, f0=60, f1=30, dur=1.8), w(1, 9, nm), -20)
    # the church
    fx.add(X.church_door(), sh("church").t + 0.2, -15)
    fx.add(X.bell(150, 9.0), sh("church").t + 0.8, -19)
    music.add(X.choir(sh("votive").end - sh("chapel").t + 2, [N["D3"], N["F3"], N["A3"], N["D4"]], seed=13),
              sh("chapel").t, -22)
    for k, nm in enumerate(("The eve", "All Saints", "All Souls")):
        fx.add(X.match_strike(seed=60 + k) * 0.5, w(2, 4, nm) - 0.05, -20)
    fx.add(X.whoosh(1.0, seed=14), w(2, 6, "for a few"), -24)
    music.add(X.boom(seed=15), w(2, 6, "Halloween"), -16)
    # souls, guisers, Jack
    fx.add(X.knock(3, seed=16), w(3, 2, "They knocked"), -16)
    fx.add(X.creak(2.2, (16, 40), seed=17, freqs=(260, 600, 1250, 2300)), sh("door").t + (w(3, 3, "Standing") - 1.6 - sh("door").t),
           -15)
    fx.add(X.wind(4.0, 70, 1.2), w(3, 3, "Standing") - 1.0, -24)
    fx.add(X.sting(4.0, seed=18), w(3, 3, "figure in a mask") - 0.5, -22)
    fx.add(X.doorbell(), sh("ghost_kid").t + 0.1, -18)
    fx.add(X.sting(4.0, seed=19, notes=(146.8, 155.6, 220.0)), w(3, 7, "fooled the Devil") + 0.2, -18)
    fx.add(X.creak(1.6, (30, 70), seed=20, freqs=(700, 1500, 2900, 4200), q=30), sh("gate").t + 0.6, -22)
    fx.add(X.owl(seed=21), sh("bog").t + 1.0, -27)
    # fortunes
    fx.add(X.stereo(X.bp(X.white(n_of(0.4), 80), 300, 3000) * np.exp(-np.arange(n_of(0.4)) / SR / 0.05), 0.2),
           sh("parlor").t + 2.5, -24)
    tj = w(4, 3, "jumped") - 0.1
    fx.add(X.stereo(X.thud(400, 0.3, 81, 1.0), 0.3), tj, -18)
    fx.add(X.wind(2.0, 82, 1.0, 2.0), sh("gutter").t + 0.2, -22)
    music.add(X.boom(seed=83, f0=55, f1=28, dur=3.0), w(4, 5, "clay"), -14)
    fx.add(X.crow(1, seed=84), w(4, 6, "In the morning") + 1.5, -28)
    fx.add(X.sting(6.0, seed=85, notes=(293.7, 311.1, 440.0, 466.2)), w(4, 7, "she would see") - 0.3, -19)
    for k, nm in enumerate(("Love.", "Money.", "Death.")):
        music.add(X.boom(seed=86 + k, f0=70 - 10 * k, f1=28, dur=2.5), w(4, 9, nm), -18 + 4 * (k == 2))
    # the ocean
    fx.add(X.thunder(7.0, seed=90), sh("ship").t + 1.6, -15)
    for k, nm in enumerate(("Bigger", "Brighter", "And grinning")):
        music.add(X.boom(seed=91 + k, f0=60, f1=30, dur=1.6), w(5, 3, nm), -22)
    # pranks
    for k in range(6):
        fx.add(X.stereo(X.thud(90, 0.25, 100 + k, 0.8), -0.5 + 0.2 * k), sh("town1900").t + 1.0 + 0.27 * k, -28)
    for k in range(10):
        f0 = 2400 + 400 * math.sin(k)
        tq = X.tt(0.12)
        sq = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.3 * tq / 0.12)) / SR) * np.sin(np.pi * tq / 0.12) * 0.3
        fx.add(X.stereo(sq.astype(np.float32), 0.0), w(6, 1, "soaped") - 0.5 + 0.35 * k, -30)
    st = sh("streetcar")
    fx.add(X.alarm_bell(0.5, 101, 2200), st.t + 0.3, -26)
    fx.add(X.alarm_bell(0.5, 102, 2200), st.t + 0.75, -26)
    for k in range(3):
        fx.add(X.stereo(X.thud(70, 0.6, 103 + k, 1.0), 0.0), w(6, 1, "pelted") + 0.9 * k, -22)
    fx.add(X.alarm_bell(2.5, 104), sh("alarm").t, -20)
    fx.add(X.glass_break(), w(6, 2, "bricks") + 0.2, -13)
    fx.add(X.thunder(1.5, seed=105, crack=True), w(6, 2, "A few homeowners") + 1.1, -17)
    # Martians
    fx.add(X.dance_music(sh("radio").t + (w(7, 1, "Bulletin after") - sh("radio").t) - sh("radio_room").t + 0.2, 110),
           sh("radio_room").t, -22)
    fx.add(X.bulletin_tone(), w(7, 1, "Bulletin after") - 0.1, -15)
    fx.add(X.sting(5.0, seed=111, notes=(220.0, 233.1, 330.0, 349.2)), w(7, 1, "Martians had landed"), -18)
    for k in range(2):
        fx.add(X.whoosh(0.9, seed=112 + k), sh("papers").t + 1.4 * k, -22)
    tn = w(7, 3, "Most people")
    fx.add(X.radio_static(1.8, 113, 2.0), tn, -22)
    # war and sugar
    fx.add(X.siren(9.0, 120), sh("search").t - 0.3, -16)
    stamp_t = sh("1947").t + 1.4
    fx.add(X.stereo(X.thud(120, 0.5, 121, 1.0), 0.1), stamp_t, -16)
    fx.add(X.doorbell(), sh("50s").t + 0.8, -22)
    for y, txt, tt_ in [(0, 0, w(8, 4, "In nineteen fifty,")), (0, 0, w(8, 4, "In nineteen fifty-one")),
                        (0, 0, w(8, 4, "And in nineteen fifty-two"))]:
        music.add(motif(1, 0.4), tt_, -22)
    # poison
    ct = sh("candy_table")
    fx.add(X.heartbeat(ct.end - ct.t + 1.0), ct.t, -16)
    fx.add(X.stereo(X.bp(X.white(n_of(1.4), 130), 1500, 7000) * X.smooth_rand(n_of(1.4), 12, 130) ** 3, 0.2),
           ct.t + 1.5, -24)
    fx.add(X.sting(4.0, seed=131), w(9, 1, "razor") + 0.3, -24)
    fx.add(X.stereo(X.thud(900, 0.08, 132, 1.0) * 0.5, 0.0), sh("xray").t + 0.15, -20)
    music.add(X.boom(seed=133), w(9, 2, "the nightmare"), -14)
    c3 = sh("candy_table3")
    fx.add(X.heartbeat(c3.end - c3.t + 0.5, bpm=60), c3.t, -18)
    fx.add(X.stereo(X.thud(1500, 0.06, 134, 1.0) * 0.4, 0.0), sh("texas2").t + (w(9, 3, "He was executed") + 1.6 - sh("texas2").t),
           -22)
    music.add(X.boom(seed=135, f0=50, f1=25), sh("zero").t + 0.1, -14)
    # today
    fx.add(X.doorbell(), sh("porch_now").t + 0.5, -20)
    fx.add(X.thunder(6.0, seed=140, crack=False), sh("people").t + 0.5, -26)
    fx.add(X.swell(1.5, 141), sh("13.5b").t - 0.2, -24)
    for k, nm in enumerate(("A witch", "For kids", "a pumpkin")):
        music.add(motif(1, 0.4), w(10, 3, nm), -22)
    for nm in ("m_turnips", "m_dog", "m_road"):
        fx.add(X.whoosh(0.8, seed=hash(nm) % 1000), sh(nm).t - 0.4, -26)
    # La Porte
    fx.add(X.screen_door(), sh("laporte").t + 1.6, -18)
    fx.add(X.sting(5.0, seed=150, notes=(146.8, 155.6, 220.0, 233.1)), sh("portrait").t + 0.2, -20)
    # the end
    E = P(12, 4)["e"]
    fx.add(X.blow_out(), E + 0.85, -14)
    fx.add(X.bell(110, 10.0, seed=151, strike=0.6), E + 2.7, -12)
    music.add(motif(gap=0.5), E + 4.2, -17)
    music.add(X.pad(16.0, [N["D3"], N["A3"], N["D4"], N["F4"]], seed=152), E + 3.9, -24)

    # typewriter clicks for typed text
    clicks = [X.type_click(500 + k) for k in range(12)]
    for s in shots:
        try:
            sc = s.factory(s.end - s.t, s.t)
        except Exception:
            continue
        blocks = getattr(sc, "blocks", [])
        for b in blocks:
            if getattr(b, "type_cps", None):
                k = 0
                for ch in b.text:
                    if ch == "\n":
                        continue
                    tk = s.t + b.t_in + k / b.type_cps
                    if ch != " " and tk < s.end + 0.3:
                        fx.add(X.stereo(clicks[k % len(clicks)], 0.1), tk, -24)
                    k += 1

    # ------------------------------------------------------------------ score: drone + chapter pads
    sec_bounds = []
    for sec in range(13):
        qs = [q for q in tl.list if q["section"] == sec]
        t0 = qs[0]["s"] - (3.0 if sec else 3.4)
        t1 = qs[-1]["e"] + 3.0
        sec_bounds.append((sec, t0, t1))
    for sec, t0, t1 in sec_bounds:
        d = t1 - t0 + 6.0
        dr = X.drone(d, seed=160 + sec)
        e = np.ones(len(dr), np.float32)
        e[:n_of(3)] = np.linspace(0, 1, n_of(3))
        e[-n_of(3):] = np.linspace(1, 0, n_of(3))
        music.add(dr * e[:, None], t0 - 3.0, -27)
    for sec, t0, t1 in sec_bounds:
        prog = PROG[sec]
        d = (t1 - t0) / len(prog)
        for k, chord in enumerate(prog):
            freqs = [N[c] for c in chord]
            p = X.pad(d + 4.0, freqs, seed=200 + sec * 5 + k, attack=3.0, release=3.5)
            music.add(p, t0 + k * d - 1.0, -25)

    # ------------------------------------------------------------------ mix
    # narration activity at a 100 Hz control rate -> smooth ducking envelope
    cr = 100
    nc = int(total * cr) + 200
    act = np.zeros(nc, np.float32)
    for q in tl.list:
        act[int(q["s"] * cr):int(q["e"] * cr)] = 1
    from scipy.signal import lfilter
    up = lfilter([1 - math.exp(-1 / (0.15 * cr))], [1, -math.exp(-1 / (0.15 * cr))], act)
    down = lfilter([1 - math.exp(-1 / (0.8 * cr))], [1, -math.exp(-1 / (0.8 * cr))], act)
    envc = np.maximum(up, down).astype(np.float32)
    mix = np.zeros((n, 2), np.float32)
    step = SR * 20
    for i0 in range(0, n, step):
        i1 = min(n, i0 + step)
        tc = np.arange(i0, i1, dtype=np.float64) / SR * cr
        env = np.interp(tc, np.arange(nc), envc).astype(np.float32)[:, None]
        mix[i0:i1] = (voice.a[i0:i1] + music.a[i0:i1] * (db(2.0) * (1 - 0.55 * env))
                      + amb.a[i0:i1] * (db(5.0) * (1 - 0.40 * env)) + fx.a[i0:i1] * (1 - 0.15 * env))
    pk = np.abs(mix).max()
    print("pre-limit peak %.2f" % pk)
    np.tanh(mix / 0.9, out=mix)
    mix *= 0.9
    sf.write(out, mix, SR, subtype="FLOAT")
    stems = os.environ.get("STEMS")
    if stems:
        os.makedirs(stems, exist_ok=True)
        sf.write(os.path.join(stems, "music.wav"), music.a * db(2.0), SR, subtype="FLOAT")
        sf.write(os.path.join(stems, "ambfx.wav"), amb.a * db(5.0) + fx.a, SR, subtype="FLOAT")
        sf.write(os.path.join(stems, "voice.wav"), voice.a, SR, subtype="FLOAT")
        print("stems in", stems)
    for nm, b in (("voice", voice), ("music", music), ("amb", amb), ("fx", fx)):
        rms = np.sqrt((b.a ** 2).mean())
        print("%-6s rms %.1f dBFS  peak %.2f" % (nm, 20 * np.log10(rms + 1e-9), np.abs(b.a).max()))
    print("wrote", out, total)


if __name__ == "__main__":
    main(sys.argv[1])
