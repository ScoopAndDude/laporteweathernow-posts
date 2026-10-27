"""The film's timeline: narration re-timed with breathing room, and every shot and
on-screen caption placed against it."""
import json
import math
import os
import re

import cv2
import numpy as np
import soundfile as sf

from core import W, H, ROOT, PAPER, AMBER, GHOST, INK, BLOOD, rgb, sstep, ease_out, text_layer, paste
from cards import Block, title_card, chapter_card, paper_card, big_number, map_scene, manuscript, stamp, TextScene
from scene import Black
import lib1
import lib2
import lib3
import lib4
import lib5

LEAD = 3.4
GAP = 0.75
GAP_LONG = 1.15
TITLE_GAP = 8.0
CH_GAP = 4.2
OUTRO_GAP = 2.6
SPECIAL = {(0, 0): 0.9, (3, 3): 1.3, (3, 4): 1.0, (4, 4): 1.0, (9, 3): 1.4, (11, 1): 1.2, (4, 7): 1.2,
           (7, 3): 0.9, (9, 5): 1.0}
TITLES = ["", "Samhain", "All Hallows' Eve", "Souls, Guisers and Stingy Jack", "Fortunes and Omens",
          "Crossing the Ocean", "The Prank Years", "The Night the Martians Came", "War, Sugar and the Candy Boom",
          "Poison in the Candy Bag", "Halloween Today", "La Porte's Halloween"]


class Timeline:
    def __init__(self):
        d = json.load(open(os.path.join(ROOT, "doc", "timings.json")))
        self.rate = d["rate"]
        self.paras = d["paras"]
        t = LEAD
        out = []
        for i, p in enumerate(self.paras):
            if i > 0:
                prev = self.paras[i - 1]
                if p["section"] != prev["section"]:
                    gap = TITLE_GAP if prev["section"] == 0 else (OUTRO_GAP if p["section"] == 12 else CH_GAP)
                else:
                    key = (prev["section"], prev["para"])
                    gap = SPECIAL.get(key, GAP_LONG if re.search(r"(\.\.\.|\?)\"?$", prev["text"]) else GAP)
                t += gap
            dur = p["end"] - p["start"]
            q = dict(p)
            q.update(s=t, e=t + dur, dur=dur)
            out.append(q)
            t += dur
        self.P = {(q["section"], q["para"]): q for q in out}
        self.list = out
        self.speech_end = t
        self._pauses()

    def _pauses(self):
        a, sr = sf.read(os.path.join(ROOT, "doc", "narration.wav"), dtype="float32")
        win = int(sr * 0.01)
        for q in self.list:
            seg = a[int(q["start"] * sr):int(q["end"] * sr)]
            n = len(seg) // win
            if n < 5:
                q["pauses"] = []
                continue
            rms = np.sqrt((seg[:n * win].reshape(n, win) ** 2).mean(1) + 1e-12)
            db = 20 * np.log10(rms)
            thr = np.median(db) - 22
            quiet = db < thr
            pauses = []
            i = 0
            while i < n:
                if quiet[i]:
                    j = i
                    while j < n and quiet[j]:
                        j += 1
                    if (j - i) >= 9 and i > 3 and j < n - 3:
                        pauses.append((i * 0.01, j * 0.01))
                    i = j
                else:
                    i += 1
            q["pauses"] = pauses

    def __call__(self, sec, para):
        return self.P[(sec, para)]

    def w(self, sec, para, phrase, nth=0, snap=True):
        """Estimated time the phrase starts being spoken."""
        q = self.P[(sec, para)]
        text = q["text"]
        idx = -1
        for _ in range(nth + 1):
            idx = text.find(phrase, idx + 1)
        if idx < 0:
            raise ValueError("phrase %r not in %d.%d" % (phrase, sec, para))
        wts = []
        for i, ch in enumerate(text):
            wgt = 1.0
            if ch in ".?!":
                wgt += 6.0
            elif ch in ",;:":
                wgt += 3.5
            wts.append(wgt)
        cum = np.cumsum([0.0] + wts)
        frac = cum[idx] / cum[-1]
        est = q["dur"] * frac
        before = text[:idx].rstrip()
        if snap and before and before[-1] in ".?!,;:" and q["pauses"]:
            ends = [p[1] for p in q["pauses"]]
            best = min(ends, key=lambda e: abs(e - est))
            if abs(best - est) < 0.8:
                est = best
        return q["s"] + est


class LowerThird:
    def __init__(self, text, t0, t1, sub=None):
        self.t0, self.t1 = t0, t1
        self.blocks = [Block(text.upper(), "sans", 32, PAPER, 150, H - 150, anchor="lm", t_in=t0 + 0.2, fade=0.6,
                             t_out=t1 - 0.5, fade_out=0.5, tracking=0.22, rise=6)]
        if sub:
            self.blocks.append(Block(sub, "fell_it", 40, "#c8bba0", 150, H - 100, anchor="lm", t_in=t0 + 0.45, fade=0.6,
                                     t_out=t1 - 0.5, fade_out=0.5, rise=6))
        self.grad = np.linspace(0, 1, 300, dtype=np.float32)[:, None, None] ** 1.5

    def draw(self, frame, t):
        if t < self.t0 or t > self.t1 + 0.1:
            return
        a = sstep(self.t0, self.t0 + 0.6, t) * (1 - sstep(self.t1 - 0.5, self.t1, t))
        frame[H - 300:, :1100] *= (1 - 0.55 * a * self.grad * np.linspace(1, 0, 1100, dtype=np.float32)[None, :, None] ** 0.7)
        p = ease_out(sstep(self.t0, self.t0 + 0.9, t))
        cv2.line(frame, (150, H - 196), (int(150 + 110 * p), H - 196), tuple(float(c) * a for c in rgb(AMBER)), 3, cv2.LINE_AA)
        for b in self.blocks:
            b.draw(frame, t)


class Callout:
    """A word or two said on screen, centred low, e.g. 'Samhain'."""

    def __init__(self, text, t0, t1, sub=None, fname="fell", size=110, y=H * 0.77, color=PAPER):
        self.t0, self.t1 = t0, t1
        self.blocks = [Block(text, fname, size, color, W / 2, y, t_in=t0, fade=0.5, t_out=t1 - 0.5, fade_out=0.5,
                             glow="#ff7a1a", glow_a=0.45, shadow=0.8)]
        if sub:
            self.blocks.append(Block(sub, "sans", 30, AMBER, W / 2, y + size * 0.72, t_in=t0 + 0.25, fade=0.5,
                                     t_out=t1 - 0.5, fade_out=0.5, tracking=0.22, shadow=0.8))

    def draw(self, frame, t):
        if t < self.t0 - 0.05 or t > self.t1 + 0.1:
            return
        a = sstep(self.t0, self.t0 + 0.5, t) * (1 - sstep(self.t1 - 0.5, self.t1, t))
        y0 = int(H * 0.62)
        frame[y0:] *= (1 - 0.45 * a * np.linspace(0, 1, H - y0, dtype=np.float32)[:, None, None])
        for b in self.blocks:
            b.draw(frame, t)


class Shot:
    def __init__(self, t, factory, fade=0.8, name=""):
        self.t, self.factory, self.fade, self.name = t, factory, fade, name
        self.end = None


def build():
    tl = Timeline()
    P, w = tl, tl.w
    shots, ovs = [], []

    def add(t, factory, fade=0.8, name=""):
        shots.append(Shot(t, factory, fade, name))

    def lower(text, t0, t1, sub=None):
        ovs.append(LowerThird(text, t0, t1, sub))

    def call(text, t0, t1, sub=None, **kw):
        ovs.append(Callout(text, t0, t1, sub, **kw))

    # ------------------------------------------------------------------ cold open
    add(0.0, lambda d, s0: lib1.match_turnip(d), fade=0.0, name="match")
    add(w(0, 0, "The fire") - 0.25, lambda d, s0: lib1.hearth(d), name="hearth")
    add(P(0, 1)["s"] - 0.3, lambda d, s0: lib1.road_scene(d), name="road")
    add(P(0, 2)["s"] - 0.3, lambda d, s0: lib1.graveyard(d), name="graveyard")
    t_carve = w(0, 3, "You carve")
    add(P(0, 3)["s"] - 0.3, lambda d, s0: lib1.turnip_carving(d, (t_carve - s0 + 0.3, w(0, 3, "Something ugly") - s0,
                                                                  w(0, 3, "Something meant") - s0)), name="carving")
    add(P(0, 4)["s"] - 0.3, lambda d, s0: lib1.turnip_carried(d), name="carried")
    add(P(0, 5)["s"] - 0.3, lambda d, s0: lib1.lantern_wall(d), name="lanterns")
    add(P(0, 6)["s"] - 0.3, lambda d, s0: lib1.dolmen_scene(d), name="dolmen")
    T6 = P(0, 6)["e"]
    add(T6 + 0.5, lambda d, s0: title_card(d), fade=1.4, name="title")

    # ------------------------------------------------------------------ chapters
    def chapter(n):
        prev_end = tl.list[[i for i, q in enumerate(tl.list) if q["section"] == n][0] - 1]["e"]
        start = (T6 + 4.9) if n == 1 else prev_end + 0.35
        add(start, lambda d, s0, n=n: chapter_card(n, TITLES[n], d), fade=1.0 if n > 1 else 1.2, name="ch%d" % n)

    chapter(1)
    s1 = P(1, 0)["s"]
    add(s1 + 0.6, lambda d, s0: lib3.map_scene(d, -17.5, 7.0, 50.6, 59.4,
                                              labels=[("IRELAND", -8.0, 53.3, 46, "sc"), ("SCOTLAND", -4.3, 57.0, 40, "sc"),
                                                      ("Atlantic Ocean", -14.0, 55.5, 44, "it"), ("North Sea", 2.6, 56.6, 40, "it")],
                                              cam=lib1.Camera(1.0, 1.12, (0.45, 0.5), (0.42, 0.55)), seed=2), name="map_irl")
    tS = w(1, 0, "Samhain")
    call("Samhain", tS - 0.1, P(1, 0)["e"] + 0.9, sub="SAY IT “SOW-in”  ·  1 NOVEMBER")
    add(P(1, 1)["s"] - 0.3, lambda d, s0: lib1.harvest_dusk(d), name="harvest")
    add(P(1, 2)["s"] - 0.3, lambda d, s0: lib1.twilight(d), name="twilight")
    call("31 October", w(1, 2, "October thirty"), P(1, 2)["e"] + 0.6, sub="THE NIGHT BEFORE SAMHAIN")
    add(P(1, 3)["s"] - 0.3, lambda d, s0: lib1.fairy_mound(d), name="mound")
    add(w(1, 3, "They were feared") - 0.2, lambda d, s0: lib1.hawthorn(d), name="hawthorn")
    add(P(1, 4)["s"] - 0.3, lambda d, s0: lib1.offering(d), name="offering")
    add(P(1, 5)["s"] - 0.3, lambda d, s0: lib1.empty_chair(d), name="chair")
    add(P(1, 6)["s"] - 0.3, lambda d, s0: lib1.guisers_fire(d), name="guisers_fire")
    add(P(1, 7)["s"] - 0.3, lambda d, s0: lib1.hilltop_bonfire(d), name="bonfire")
    t_rel = w(1, 7, "and lit them")
    add(w(1, 7, "In some places") - 0.2, lambda d, s0: lib1.hearth(d, fire=lib1.ramp(t_rel - s0, t_rel - s0 + 1.2),
                                                                     shutters=False), name="relight")
    add(P(1, 8)["s"] - 0.3, lambda d, s0: manuscript(d), name="manuscript")
    lower("Samhain in Irish writing", P(1, 8)["s"] + 0.3, P(1, 8)["s"] + 6.0, sub="as early as the 800s")
    tf, tdz, tdd = w(1, 9, "Fire."), w(1, 9, "Disguises."), w(1, 9, "And the dead")
    add(P(1, 9)["s"] - 0.3, lambda d, s0: lib2.Triptych([lib1.hilltop_bonfire(d), lib2.mask_closeup(d), lib1.graveyard(d)],
                                                         (tf - s0, tdz - s0, tdd - s0),
                                                         ("Fire.", "Disguises.", "The dead."), d), name="triptych")

    chapter(2)
    add(P(2, 0)["s"] - 0.4, lambda d, s0: lib1.church_night(d), name="church")
    add(P(2, 1)["s"] - 0.3, lambda d, s0: lib2.chapel_interior(d), name="chapel")
    lower("Rome", P(2, 1)["s"] + 0.2, P(2, 1)["s"] + 6.0, sub="the 700s A.D.")
    call("All Saints' Day", w(2, 1, "All Saints"), P(2, 1)["e"] + 0.7, sub="1 NOVEMBER")
    add(P(2, 2)["s"] - 0.3, lambda d, s0: paper_card([
        Block("A.D.", "fell_sc", 60, "#5a4a32", W / 2, 230, t_in=0.2, fade=0.6, tracking=0.2),
        Block("835", "fell", 260, INK, W / 2, 400, t_in=0.3, fade=0.8),
        Block("Emperor Louis the Pious makes All Saints' Day\na holy day across his empire", "type", 50, INK, W / 2,
              720, t_in=1.4, type_cps=30)], d, seed=0), name="835")
    add(P(2, 3)["s"] - 0.3, lambda d, s0: lib2.votive_candles(d), name="votive")
    call("All Souls' Day", w(2, 3, "All Souls"), w(2, 3, "For every soul") + 0.5, sub="2 NOVEMBER")
    t3 = (w(2, 4, "The eve"), w(2, 4, "All Saints"), w(2, 4, "All Souls"))
    add(P(2, 4)["s"] - 0.3, lambda d, s0: lib2.three_candles(d, tuple(x - s0 for x in t3)), name="three_candles")
    t_eve = w(2, 5, "All Hallows' Eve")
    add(P(2, 5)["s"] - 0.3, lambda d, s0: lib2.hallow_card(d, t_eve - s0), name="hallow")
    tm = (0.15, w(2, 6, "for a few") - P(2, 6)["s"] + 0.6, w(2, 6, "and you get") - P(2, 6)["s"] + 0.3,
          w(2, 6, "Halloween") - P(2, 6)["s"] + 0.3)
    add(P(2, 6)["s"] - 0.3, lambda d, s0: lib2.word_morph(d, tuple(x + 0.3 for x in tm)), name="morph")

    chapter(3)
    add(P(3, 0)["s"] + 0.6, lambda d, s0: lib2.Blend(lib1.church_night(d), lib1.hilltop_bonfire(d), d * 0.25, d * 0.7, d),
        name="blend")
    add(P(3, 1)["s"] - 0.3, lambda d, s0: lib2.soul_cakes(d), name="soul_cakes")
    call("souling", w(3, 1, "souling"), P(3, 1)["e"] + 0.8, fname="fell_it")
    add(P(3, 2)["s"] - 0.3, lambda d, s0: lib2.guisers_lane(d), name="guisers_lane")
    call("guisers", w(3, 2, "guisers"), w(3, 2, "They knocked") + 0.4, fname="fell_it")
    lower("Scotland", w(3, 2, "The earliest record"), P(3, 2)["e"] + 0.6, sub="earliest record: the 1500s")
    t_open = w(3, 3, "Standing") - 1.6
    add(P(3, 3)["s"] - 0.3, lambda d, s0: lib2.door_open(d, t_open - s0), name="door")
    add(P(3, 4)["s"] - 0.15, lambda d, s0: lib2.ghost_kid(d), fade=0.05, name="ghost_kid")
    add(P(3, 5)["s"] - 0.3, lambda d, s0: lib1.lantern_wall(d, mangels=True, seed=3), name="mangels")
    call("mangel-wurzel", w(3, 5, "mangel"), w(3, 5, "They cut") + 0.3, sub="A BIG FODDER BEET", fname="fell_it")
    t_eyes = w(3, 7, "fooled the Devil")
    add(P(3, 6)["s"] - 0.3, lambda d, s0: lib2.crossroads(d, t_eyes - s0), name="crossroads")
    lower("Stingy Jack", P(3, 7)["s"] + 0.3, w(3, 7, "When Jack") - 0.2, sub="an Irish folk tale")
    add(w(3, 7, "When Jack finally") - 0.2, lambda d, s0: lib2.locked_gate(d), name="gate")
    add(P(3, 8)["s"] - 0.3, lambda d, s0: lib2.coal(d), name="coal")
    add(w(3, 8, "Jack put it") - 0.2, lambda d, s0: lib2.jack_wanders(d), name="wanders")
    add(P(3, 9)["s"] - 0.3, lambda d, s0: lib2.bog_wisps(d), name="bog")
    call("Jack of the Lantern", w(3, 9, "Jack of the Lantern"), P(3, 9)["e"] + 1.0, fname="fell_it")

    chapter(4)
    add(P(4, 0)["s"] + 0.6, lambda d, s0: lib3.parlor(d), name="parlor")
    tq = w(4, 1, "Upon")
    add(P(4, 1)["s"] - 0.3, lambda d, s0: lib3.burns_card(d, tq - s0), name="burns")
    add(P(4, 2)["s"] - 0.3, lambda d, s0: lib3.kale_garden(d), name="kale")
    tj = w(4, 3, "jumped") - 0.1
    add(P(4, 3)["s"] - 0.3, lambda d, s0: lib3.nuts_fire(d, tj - s0), name="nuts")
    add(P(4, 4)["s"] - 0.3, lambda d, s0: lib3.candle_gutter(d), name="gutter")
    ts = (w(4, 5, "ring"), w(4, 5, "coin"), w(4, 5, "clay"))
    th = w(4, 5, "But touch") - 0.6
    add(P(4, 5)["s"] - 0.3, lambda d, s0: lib3.saucers(d, tuple(x - s0 for x in ts), th - s0), name="saucers")
    tm_, tg = w(4, 6, "In the morning"), w(4, 6, "missing") + 0.2
    add(P(4, 6)["s"] - 0.3, lambda d, s0: lib3.stones_ashes(d, tg - s0, (tm_ - s0, tm_ - s0 + 2.5)), name="stones")
    tface = w(4, 7, "she would see")
    add(P(4, 7)["s"] - 0.3, lambda d, s0: lib3.mirror_scene(d, tface - s0), name="mirror")
    add(P(4, 8)["s"] - 0.3, lambda d, s0: lib3.skulls_scene(d), name="skulls")
    lower("Brittany, France", P(4, 8)["s"] + 0.3, P(4, 8)["e"] + 0.5)
    tw = (w(4, 9, "Love."), w(4, 9, "Money."), w(4, 9, "Death."))
    add(P(4, 9)["s"] - 0.3, lambda d, s0: lib3.three_words(d, tuple(x - s0 for x in tw)), fade=0.4, name="words")

    chapter(5)
    add(P(5, 0)["s"] + 0.6, lambda d, s0: lib3.famine_ship(d), name="ship")
    lower("The Great Famine", P(5, 0)["s"] + 0.6, w(5, 0, "Huge numbers") - 0.3, sub="Ireland, 1845–1852")
    t_map = w(5, 0, "Huge numbers") - 0.2
    add(t_map, lambda d, s0: lib3.atlantic_map(d, (w(5, 0, "crossed") - s0, w(5, 0, "Scottish") - s0 + 0.5)), name="atlantic")
    add(P(5, 1)["s"] - 0.3, lambda d, s0: lib3.turnip_vs_pumpkin(d), name="vs")
    add(w(5, 1, "Here, pumpkins") - 0.2, lambda d, s0: lib3.pumpkin_patch(d), name="patch")
    add(P(5, 2)["s"] - 0.3, lambda d, s0: lib3.jack_hero(d, face=2), name="jack1")
    add(w(5, 2, "In eighteen ninety-two") - 0.2, lambda d, s0: lib3.victorian_parlor(d), name="victorian")
    lower("Atlanta, Georgia", w(5, 2, "In eighteen ninety-two") + 0.3, P(5, 2)["e"] + 0.5, sub="1892")
    tb = (w(5, 3, "Bigger"), w(5, 3, "Brighter"), w(5, 3, "And grinning"))
    add(P(5, 3)["s"] - 0.3, lambda d, s0: lib3.jack_hero(d, boosts=tuple(x - s0 for x in tb), face=0), name="jack2")

    chapter(6)
    add(P(6, 0)["s"] + 0.6, lambda d, s0: lib3.town_1900(d), name="town1900")
    add(P(6, 1)["s"] - 0.3, lambda d, s0: lib3.rope_sidewalk(d), name="rope")
    t_soap = w(6, 1, "They tied")
    add(t_soap - 0.2, lambda d, s0: lib3.soaped_window(d, w(6, 1, "soaped") - s0 - 0.6, w(6, 1, "In eighteen") - s0),
        name="soap")
    t_car = w(6, 1, "In eighteen ninety-four")
    bursts = tuple(w(6, 1, "pelted") + k * 0.9 for k in range(3))
    add(t_car - 0.2, lambda d, s0: lib3.streetcar(d, tuple(b - s0 for b in bursts)), name="streetcar")
    lower("Washington, D.C.", t_car + 0.3, P(6, 1)["e"] + 0.5, sub="1894")
    add(P(6, 2)["s"] - 0.3, lambda d, s0: lib3.town_1900(d, leaves_on=False), name="town_ugly")
    add(w(6, 2, "Kids pulled") - 0.2, lambda d, s0: lib3.fire_alarm(d), name="alarm")
    tbr = w(6, 2, "bricks")
    add(w(6, 2, "and threw") - 0.2, lambda d, s0: lib3.broken_window(d, tbr - s0 + 0.2), name="window")
    tbs = w(6, 2, "A few homeowners")
    add(w(6, 2, "Some demanded") - 0.2, lambda d, s0: lib3.porch_dark(d, tbs - s0), name="porch_dark")
    add(P(6, 3)["s"] - 0.3, lambda d, s0: lib3.party_lanterns(d), name="party")
    add(w(6, 3, "Give us") - 0.25, lambda d, s0: lib3.treat_or_trick_card(d, 0.2), name="treat_card")
    tc = w(6, 4, "turned up")
    add(P(6, 4)["s"] - 0.3, lambda d, s0: lib3.newsprint_card(d, tc - s0), name="news")
    t1r, t2r = w(6, 5, "Kids should"), w(6, 5, "Grown-ups")
    add(P(6, 5)["s"] - 0.3, lambda d, s0: lib3.rules_card(d, t1r - s0, t2r - s0), name="rules")
    lower("Late 1930s", P(6, 5)["s"] + 0.3, w(6, 5, "Kids should") - 0.2, sub="magazines teach trick-or-treat manners")

    chapter(7)
    add(P(7, 0)["s"] + 0.6, lambda d, s0: lib4.radio_room(d), name="radio_room")
    lower("October 30, 1938", P(7, 0)["s"] + 0.8, P(7, 0)["e"] + 0.5, sub="the night before Halloween")
    add(P(7, 1)["s"] - 0.3, lambda d, s0: lib4.radio_closeup(d), name="radio")
    lower("CBS Radio", P(7, 1)["s"] + 0.3, w(7, 1, "Bulletin") - 0.3, sub="Orson Welles’s “The War of the Worlds”")
    add(w(7, 1, "Bulletin after") - 0.2, lambda d, s0: lib4.bulletin(d), fade=0.2, name="bulletin")
    add(w(7, 1, "reporting that") - 0.2, lambda d, s0: lib4.tripod(d, 1.0), name="tripod")
    lower("Grovers Mill, New Jersey", w(7, 1, "Grovers Mill") - 0.3, P(7, 1)["e"] + 1.0)
    add(P(7, 2)["s"] - 0.3, lambda d, s0: lib4.newspapers(d), name="papers")
    tn = w(7, 3, "Most people")
    add(P(7, 3)["s"] - 0.3, lambda d, s0: lib4.radio_closeup(d, (tn - s0, tn - s0 + 1.6, 0.62, 0.18)), name="dial")
    add(P(7, 4)["s"] - 0.3, lambda d, s0: lib4.tripod(d, 0.3), name="tripod2")

    chapter(8)
    add(P(8, 0)["s"] - 0.4, lambda d, s0: lib4.searchlights(d), name="search")
    add(P(8, 1)["s"] - 0.3, lambda d, s0: lib4.ration_scene(d), name="ration")
    lower("1942", P(8, 1)["s"] + 0.3, w(8, 1, "Families got") - 0.2, sub="sugar is rationed")
    call("½ pound of sugar a week", w(8, 1, "about half"), P(8, 1)["e"] + 0.6, size=90)
    add(P(8, 2)["s"] - 0.3, lambda d, s0: paper_card([
        Block("CHICAGO  ·  1942", "sans", 34, "#5a4a32", W / 2, 260, t_in=0.2, fade=0.6, tracking=0.3),
        Block("City council votes to replace\nHalloween with", "type", 60, INK, W / 2, 470, t_in=0.6, type_cps=30),
        Block("“Conservation Day”", "fell", 120, BLOOD, W / 2, 700, t_in=2.6, fade=0.6)], d, seed=1), name="chicago")
    add(w(8, 2, "In Rochester") - 0.2, lambda d, s0: paper_card([
        Block("ROCHESTER, NEW YORK", "sans", 34, "#5a4a32", W / 2, 260, t_in=0.2, fade=0.6, tracking=0.3),
        Block("A school superintendent calls\nHalloween pranks", "type", 60, INK, W / 2, 470, t_in=0.5, type_cps=30),
        Block("“wartime sabotage”", "fell", 120, BLOOD, W / 2, 700, t_in=2.6, fade=0.6)], d, seed=2), name="rochester")
    add(P(8, 3)["s"] - 0.3, lambda d, s0: paper_card([
        Block("JUNE 1947", "sans", 40, "#5a4a32", W / 2, 300, t_in=0.2, fade=0.6, tracking=0.3),
        Block("Sugar rationing ends", "fell", 130, INK, W / 2, 470, t_in=0.4, fade=0.7)], d, seed=0,
        stamp=stamp("RATIONING ENDED", W * 0.66, H * 0.74, 1.4, size=60)), name="1947")
    add(w(8, 3, "And Halloween") - 0.2, lambda d, s0: lib4.street_1950s(d), name="50s")
    ev = [(1950, "UNICEF coin boxes for trick-or-treaters", w(8, 4, "In nineteen fifty,")),
          (1951, "“Peanuts” goes trick-or-treating", w(8, 4, "In nineteen fifty-one")),
          (1952, "Donald Duck in “Trick or Treat”", w(8, 4, "And in nineteen fifty-two"))]
    add(ev[0][2] - 0.6, lambda d, s0: lib4.TimelineScene(d, [(y, txt, t - s0) for y, txt, t in ev]), name="timeline")
    add(P(8, 5)["s"] - 0.3, lambda d, s0: big_number(d, 300, prefix="$", suffix=" million", decimals=0,
                                                     label="Halloween candy and costumes, 1965", t0=0.3,
                                                     t1=w(8, 5, "three-hundred") - s0 + 1.0, fname="old_b",
                                                     color="#e9c25a"), name="300m")

    chapter(9)
    add(P(9, 0)["s"] + 0.6, lambda d, s0: lib4.candy_table(d), name="candy_table")
    tg = w(9, 1, "razor") + 0.3
    add(P(9, 1)["s"] - 0.3, lambda d, s0: lib4.candy_apple(d, tg - s0), name="apple")
    add(w(9, 1, "Parents searched") - 0.2, lambda d, s0: lib4.candy_table(d, heartbeat=False), name="candy_table2")
    add(w(9, 1, "Some hospitals") - 0.2, lambda d, s0: lib4.xray_scene(d), name="xray")
    add(P(9, 2)["s"] - 0.3, lambda d, s0: lib4.texas_house(d), name="texas")
    lower("Deer Park, Texas", P(9, 2)["s"] + 0.6, P(9, 2)["e"] + 0.3, sub="October 31, 1974")
    toff = w(9, 3, "He was executed")
    add(P(9, 3)["s"] - 0.3, lambda d, s0: lib5.town_night(d), name="town9")
    add(w(9, 3, "and he handed") - 0.2, lambda d, s0: lib4.candy_table(d, heartbeat=True), name="candy_table3")
    add(toff - 0.25, lambda d, s0: lib4.texas_house(d, toff - s0 + 1.6), name="texas2")
    add(P(9, 4)["s"] - 0.3, lambda d, s0: lib4.newspapers(d), name="papers2")
    lower("Joel Best", P(9, 4)["s"] + 0.5, w(9, 4, "Not one") - 0.3, sub="sociologist, University of Delaware")
    add(w(9, 4, "Not one case") - 0.25, lambda d, s0: big_number(d, 0, prefix="", decimals=0,
                                                                  label="cases of a stranger poisoning Halloween candy at random that held up",
                                                                  t0=0.1, t1=0.6, fname="old_b", color="#d23a26", size=340,
                                                                  label_y=780), name="zero")
    tchg = w(9, 5, "The real danger")
    add(P(9, 5)["s"] - 0.3, lambda d, s0: lib4.door_shadow(d, tchg - s0), name="door_shadow")

    chapter(10)
    add(P(10, 0)["s"] + 0.6, lambda d, s0: lib5.modern_porch(d), name="porch_now")
    t135 = w(10, 1, "thirteen")
    add(P(10, 1)["s"] - 0.3, lambda d, s0: big_number(d, 13.5, prefix="$", suffix=" billion", decimals=1,
                                                      label="expected Halloween spending this year, a record",
                                                      sub="Source: National Retail Federation, Sept. 2026",
                                                      t0=t135 - s0, t1=t135 - s0 + 2.0), name="13.5b")
    add(w(10, 1, "About three in four") - 0.2, lambda d, s0: lib5.PeopleScene(d, t0=0.5), name="people")
    tc4, tcd = w(10, 2, "Costumes"), w(10, 2, "Candy")
    add(P(10, 2)["s"] - 0.3, lambda d, s0: lib5.BarsScene(d, [("Costumes", 4.4, "#ff9a3a", tc4 - s0),
                                                               ("Candy", 4.1, "#b07aff", tcd - s0)]), name="bars")
    tp = (w(10, 3, "A witch"), w(10, 3, "For kids"), w(10, 3, "a pumpkin"))
    add(P(10, 3)["s"] - 0.3, lambda d, s0: lib5.PanelsScene(d, tuple(x - s0 for x in tp)), name="panels")
    add(P(10, 4)["s"] - 0.3, lambda d, s0: lib1.hilltop_bonfire(d), name="m_bonfire")
    add(w(10, 4, "turnip lanterns") - 0.2, lambda d, s0: lib1.lantern_wall(d), name="m_turnips")
    add(w(10, 4, "to a dog") - 0.2, lambda d, s0: lib5.dog_porch(d), name="m_dog")
    add(w(10, 4, "It's been") - 0.2, lambda d, s0: lib1.road_scene(d), name="m_road")

    chapter(11)
    add(P(11, 0)["s"] + 0.6, lambda d, s0: lib5.laporte_dusk(d), name="laporte")
    lower("La Porte, Indiana", P(11, 0)["s"] + 0.8, P(11, 0)["e"] + 1.0)
    add(P(11, 1)["s"] - 0.3, lambda d, s0: lib5.farmhouse_fire(d), name="fire1908")
    lower("McClung Road", P(11, 1)["s"] + 0.4, w(11, 1, "The digging") - 0.3, sub="April 28, 1908")
    add(w(11, 1, "The digging") - 0.2, lambda d, s0: lib5.portrait_frame(d), name="portrait")
    add(P(11, 2)["s"] - 0.3, lambda d, s0: lib5.town_night(d), name="town_night")
    add(P(11, 3)["s"] - 0.3, lambda d, s0: lib5.little_belles(d), name="belles")
    add(w(11, 3, "The county museum") - 0.2, lambda d, s0: lib5.entrepreneur_card(d), name="entrepreneur")
    add(P(11, 4)["s"] - 0.3, lambda d, s0: lib5.porch_party(d), name="party_porch")
    tsun, tmoon = w(11, 5, "the sun sets"), w(11, 5, "And the moon")
    add(P(11, 5)["s"] - 0.3, lambda d, s0: lib5.SkyClock(d, tsun - s0, (tsun + tmoon) / 2 - s0, tmoon - s0), name="sky")

    # ------------------------------------------------------------------ outro
    o0 = P(12, 0)["s"] - 1.2
    t_off = w(12, 3, "and the porch lights")
    E = P(12, 4)["e"]
    blow = E + 0.9
    add(o0, lambda d, s0: lib5.outro_porch(d, t_off - s0 + 1.0, blow - s0), fade=1.2, name="outro")
    ovs.append(Callout("Belle Gunness series", w(12, 0, "watch our"), w(12, 0, "and our") + 0.4, sub="WATCH NEXT",
                       size=86))
    ovs.append(Callout("La Porte County hauntings", w(12, 0, "and our"), P(12, 0)["e"] + 0.7, sub="AND", size=86))
    ovs.append(Callout("laporteweathernow.com", w(12, 1, "are on"), P(12, 1)["e"] + 0.9,
                       sub="TRICK-OR-TREAT HOURS FOR EVERY TOWN", fname="sans_b", size=84))
    ovs.append(Callout("Follow La Porte Weather Now", P(12, 2)["s"] + 0.2, P(12, 2)["e"] + 0.8, size=80))
    add(E + 2.6, lambda d, s0: Black(), fade=1.2, name="black")
    add(E + 3.9, lambda d, s0: lib5.EndCard(d), fade=1.0, name="endcard")
    total = E + 3.9 + 16.0
    for i, s in enumerate(shots):
        s.end = shots[i + 1].t if i + 1 < len(shots) else total
    # sanity: increasing
    for a, b in zip(shots, shots[1:]):
        assert b.t > a.t + 0.4, (a.name, b.name, a.t, b.t)
    return tl, shots, ovs, total


if __name__ == "__main__":
    tl, shots, ovs, total = build()
    print("total %.2f s = %d:%05.2f, %d shots, %d overlays" % (total, total // 60, total % 60, len(shots), len(ovs)))
    for s in shots:
        print("%7.2f  %5.2f  %s" % (s.t, s.end - s.t, s.name))
