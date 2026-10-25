"""Halloween (trick-or-treat) forecast reel: the Daily Video's cards on the Halloween night background.

    python3 reel_hwfc.py stills|video [times]

Forecast: the NWS point forecast for La Porte (the posts repo's nws-snapshot.json), as of FC["asof"]; the
"best chance later Saturday night into Sunday" line is the NWS Northern Indiana forecast discussion's.
Sunset and dark (civil dusk): NOAA's solar calculation for La Porte (41.61 N, 86.72 W), Sat. Oct. 31, 2026, CDT.
Hours: trick-or-treat.json (La Porte and Michigan City official, 5 to 7 PM; most other towns reported the same).
To refresh before posting: update FC from the newest snapshot, the "hwfc" lines in reels_vo.py, re-record, re-render.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import reels_common as C
from reels_common import bs, vr, hw, W, H, SR, glow, paste, scaled, appear, ease, ease_out

ORANGE, GOLDEN, CREAM, LAV, FAINT, PURPLE = hw.ORANGE, hw.GOLDEN, hw.CREAM, hw.LAV, hw.FAINT, hw.PURPLE
BLUE, INK = vr.BLUE, vr.INK
X0, CW = vr.X0, vr.CW
CARD = (40, 17, 64, 236)
SKYBLUE = (150, 196, 255)

FC = {
    "asof": "Sun., Oct. 25",
    "day": {"icon": "cloud", "hi": 71, "sky": "Mostly cloudy and mild", "pop": 22,
            "pop_text": "Slight chance of a shower"},
    "night": {"icon": "rain", "lo": 54, "pop": 57, "sky": "Showers likely",
              "note": "Best chance: later Saturday night into Sunday"},
    "hours": "5 to 7 PM", "where": "La Porte, Michigan City and most towns",
    "sunset": "5:43 PM", "dark": "about 6:10",
}
C.WEIGHT.update({"71": 4.0, "543": 4.3, "610": 2.4, "5": 1.2, "7": 2.0})
OUTFILE = "halloween-trick-or-treat-forecast.mp4"


def label(text):
    return vr.text_img(text.upper(), "bold", 36, GOLDEN, tracking=4)


def panel(w, h, accent=ORANGE, fill=CARD):
    p = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=fill, outline=accent + (160,), width=3)
    return p


def night_layers(frame, t, bats=True):
    """hw.animate without the bats (they'd fly through the cards)."""
    if bats:
        hw.animate(frame, t)
        return
    for x, y, r, ph, f in hw.STARS:
        a = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * f * t + ph))
        frame.alpha_composite(vr.with_alpha(hw.star_sprite(r), a), (x - r * 3, y - r * 3))
    for i, (x, y, s, ph) in enumerate(hw.PUMPKINS):
        a = 0.80 + 0.20 * math.sin(2 * math.pi * 1.7 * t + ph) * math.sin(2 * math.pi * 0.53 * t + 2 * ph)
        fc = hw.FACES[i]
        frame.alpha_composite(vr.with_alpha(fc, max(0.55, min(1.0, a))), (x - fc.info["pad"], y - fc.info["pad"]))


def rain_layer(t, n=260, seed=6, a=70, length=40, slant=0.18, speed=2100):
    rng = np.random.default_rng(seed)
    xs, ys0 = rng.uniform(-200, W + 100, n), rng.uniform(0, H, n)
    sp = rng.uniform(0.75, 1.25, n) * speed
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(n):
        y = (ys0[i] + sp[i] * t) % (H + 200) - 100
        x = xs[i] + slant * y * 0.25
        L = length * sp[i] / speed
        d.line((x, y, x - slant * L, y - L), fill=(200, 210, 240, int(a * rng.uniform(0.5, 1.0))), width=2)
    return lay


def day_card():
    d = FC["day"]
    w, h = CW + 20, 540
    p = panel(w, h)
    ic = vr.icon(d["icon"], 300)
    tp = vr.text_img(vr.deg(d["hi"]), "black", 240, CREAM)
    hl = vr.text_img("HIGH", "bold", 40, FAINT, tracking=6)
    p.alpha_composite(ic, (50, 40))
    rx = w - 70 - tp.width
    top = 40 + (300 - tp.height - 12 - hl.height) // 2
    p.alpha_composite(tp, (rx, top))
    p.alpha_composite(hl, (rx + (tp.width - hl.width) // 2, top + tp.height + 12))
    sky = vr.fit_line(d["sky"], "xbold", 70, CREAM, w - 80, min_size=44)
    p.alpha_composite(sky, ((w - sky.width) // 2, 395))
    pill = vr.pill(f"{d['pop']}% · {d['pop_text']}", "bold", 40, INK, (20, 50, 96, 255), border=BLUE,
                   icon=vr.icon("drop", 40), padx=26, pady=14)
    return p, pill


def tot_cards():
    pk = hw.pumpkin(118, glow_face=True)
    sun = vr.icon("sun", 124)
    moon = vr.icon("moon", 112)
    return [hw.card(FC["hours"], FC["where"], ORANGE, pk),
            hw.card("Sunset " + FC["sunset"], "Saturday, Oct. 31", GOLDEN, sun),
            hw.card("Dark by " + FC["dark"], "Bring a flashlight", (170, 140, 255), moon)]


def night_card():
    d = FC["night"]
    w, h = CW + 20, 500
    p = panel(w, h, accent=(110, 160, 255))
    ic = vr.icon(d["icon"], 290)
    pc = vr.text_img(f"{d['pop']}%", "black", 200, SKYBLUE)
    cl = vr.text_img("CHANCE OF SHOWERS", "bold", 34, FAINT, tracking=4)
    p.alpha_composite(ic, (50, 40))
    cwid = max(pc.width, cl.width)
    rx = w - 60 - cwid
    top = 40 + (290 - pc.height - 8 - cl.height) // 2
    p.alpha_composite(pc, (rx + (cwid - pc.width) // 2, top))
    p.alpha_composite(cl, (rx + (cwid - cl.width) // 2, top + pc.height + 8))
    sky = vr.fit_line(f"{d['sky']} · Low {vr.deg(d['lo'])}", "xbold", 66, CREAM, w - 80, min_size=44)
    p.alpha_composite(sky, ((w - sky.width) // 2, 370))
    nw, nh = CW + 20, 230
    note = panel(nw, nh, accent=(110, 160, 255), fill=(22, 26, 58, 236))
    a = vr.fit_para(d["note"], "xbold", 52, CREAM, nw - 80, max_lines=2, min_size=38, align="center")
    b = vr.text_img("National Weather Service", "semi", 32, FAINT)
    y = (nh - a.height - 14 - b.height) // 2
    note.alpha_composite(a, ((nw - a.width) // 2, y))
    note.alpha_composite(b, ((nw - b.width) // 2, y + a.height + 14))
    return p, note


def build(R):
    t_sat = R.at("Saturday looks")
    t_slight = R.at("slight chance")
    t_tot = R.at("Trick-or-treat is")
    t_sun = R.at("The sun")
    t_dark = R.at("dark by")
    t_show = R.at("Showers are")
    t_best = R.at("the best")
    t_dbl = R.at("double-tap")
    c1 = (R.end("Porte.") + t_sat) / 2
    c2 = (R.end("shower.") + t_tot) / 2
    c3 = (R.end("6:10.") + t_show) / 2
    c4 = (R.end("Sunday.") + R.at("It can")) / 2
    src = "Forecast: National Weather Service, " + FC["asof"]

    def prep_base(ctx):
        if not hw.FACES:
            hw.FACES[:] = [hw.face_layer(s) for _, _, s, _ in hw.PUMPKINS]
        ctx["bg"] = hw.night_base()

    def prep_hook(ctx):
        prep_base(ctx)
        ctx["lab"] = label("La Porte · Sat., Oct. 31")
        big = vr.fit_line("TRICK-OR-TREAT", "black", 150, ORANGE, CW + 40, min_size=90)
        ctx["t1"] = vr.glow(big, (255, 110, 0), radius=30, strength=0.65)
        ctx["t2"] = vr.glow(vr.fit_line("FORECAST", "black", 150, CREAM, CW, min_size=90), (0, 0, 0), radius=20,
                            strength=0.8)
        ctx["cloud"] = vr.icon("rain", 290)
        ctx["q"] = vr.glow(vr.text_img("?", "black", 190, GOLDEN), (255, 120, 0), radius=24, strength=0.6)

    def draw_hook(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_layers(f, t, bats=True)
        f.alpha_composite(ctx["lab"], (X0, 330))
        k = ease_out(t / 0.6)
        paste(f, scaled(ctx["t1"], 1.06 - 0.06 * k), W / 2, 560)
        paste(f, ctx["t2"], W / 2, 715)
        bob = 10 * math.sin(t * 2.2)
        paste(f, ctx["cloud"], W / 2 - 40, 1010 + bob)
        paste(f, ctx["q"], W / 2 + 165, 930 - bob * 0.6, appear(t, 0.35, 0.25))

    def prep_day(ctx):
        prep_base(ctx)
        ctx["lab"] = label("Halloween · Saturday")
        ctx["card"], ctx["pill"] = day_card()

    def draw_day(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_layers(f, t, bats=False)
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        a = appear(t, t_sat - 0.15, 0.35)
        f.alpha_composite(C.alpha(ctx["card"], a), (X0 - 10, int(410 + 40 * (1 - a))))
        a2 = appear(t, t_slight - 0.1, 0.3)
        if a2 > 0:
            paste(f, scaled(ctx["pill"], 1.12 - 0.12 * a2), W / 2, 1040, a2)
        bs.credit_line(f, src)

    def prep_tot(ctx):
        prep_base(ctx)
        ctx["lab"] = label("Trick-or-treat")
        ctx["cards"] = tot_cards()
        ctx["more"] = vr.fit_line("Every town's hours: laporteweathernow.com", "semi", 36, LAV, CW, min_size=28)

    def draw_tot(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_layers(f, t, bats=False)
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        for i, (card, at) in enumerate(zip(ctx["cards"], (t_tot - 0.1, t_sun - 0.05, t_dark - 0.05))):
            a = appear(t, at, 0.3)
            if a > 0:
                f.alpha_composite(C.alpha(card, a), (int(X0 - 10 - 40 * (1 - a)), 420 + i * 208))
        paste(f, ctx["more"], W / 2, 1085 + ctx["more"].height / 2, appear(t, t_dark + 0.3, 0.3))
        bs.credit_line(f, "Hours: City of La Porte, City of Michigan City · Sunset: NOAA")

    def prep_night(ctx):
        prep_base(ctx)
        ctx["lab"] = label("Saturday night")
        ctx["card"], ctx["note"] = night_card()

    def draw_night(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_layers(f, t, bats=False)
        f.alpha_composite(C.alpha(rain_layer(t), appear(u, 0.0, 0.6)))
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        a = appear(t, t_show - 0.15, 0.35)
        f.alpha_composite(C.alpha(ctx["card"], a), (X0 - 10, int(410 + 40 * (1 - a))))
        a2 = appear(t, t_best - 0.1, 0.3)
        f.alpha_composite(C.alpha(ctx["note"], a2), (X0 - 10, int(940 + 30 * (1 - a2))))
        bs.credit_line(f, src)

    def prep_end(ctx):
        prep_base(ctx)
        ctx["cta"] = C.DoubleTap("FOR THE UPDATE", "and every town's trick-or-treat hours", color1=GOLDEN,
                                 glow1=(255, 120, 0), kind1="black", size1=100, y=520)
        ctx["url"] = vr.pill("laporteweathernow.com", "xbold", 52, (16, 8, 26), GOLDEN + (255,), padx=38, pady=22)

    def draw_end(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        night_layers(f, t, bats=True)
        ctx["cta"].draw(f, u)
        paste(f, ctx["url"], W / 2, 1190, appear(u, 0.9, 0.3))

    scenes = [C.Scene(0.0, c1, draw_hook, prep_hook), C.Scene(c1, c2, draw_day, prep_day),
              C.Scene(c2, c3, draw_tot, prep_tot), C.Scene(c3, c4, draw_night, prep_night),
              C.Scene(c4, R.dur + 1, draw_end, prep_end)]
    for sc in scenes:
        sc.flicker = 0.0
    atm = bs.Atmos(tint=(204, 198, 214), fog=0.05, vignette=0.45, grain=7, seed=8)
    film = C.Film(R, scenes, flashes=[], flicker=0.0, atmos=atm)

    import sfx as X
    rain = X.rain(c4 - c3 + 1.2, seed=36).mean(1)
    k = int(0.5 * SR)
    rain[:k] *= np.linspace(0, 1, k)
    rain[-int(0.9 * SR):] *= np.linspace(1, 0, int(0.9 * SR))
    ev = [("pop", 0.35, 0.6), ("whoosh", c1, 0.6), ("pop", t_sat - 0.1, 0.5), ("pop", t_slight - 0.08, 0.6),
          ("whoosh", c2, 0.6), ("pop", t_tot - 0.08, 0.6), ("pop", t_sun - 0.05, 0.6), ("pop", t_dark - 0.05, 0.6),
          ("whoosh", c3, 0.6), (rain * 0.8, c3, 1.0, "bed"), ("pop", t_show - 0.1, 0.5), ("pop", t_best - 0.08, 0.5),
          ("pop", c4 + 0.12, 0.9), ("pop", c4 + 0.42, 0.9), ("hit", c4 + 0.5, 0.5)]
    music = spooky_music(R.dur + 1, theremin=((0.0, 2.6, (69, 74, 72, 69)), (c4 + 0.2, 2.4, (74, 77, 74))))
    return film, ev, music, "Halloween Trick-or-Treat Forecast"


def spooky_music(seconds, theremin=()):
    """The fall-fun video's music box (hw.music), with the theremin where this reel wants it and no whooshes."""
    n = int(seconds * SR)
    out = np.zeros(n, np.float32)
    beat = 60 / 96
    bar = 4 * beat
    chords = [(50, "m"), (46, "M"), (43, "m"), (45, "M"), (50, "m"), (46, "M"), (43, "m"), (45, "M"), (50, "m")]

    def add(sig, start):
        i = int(start * SR)
        if i >= n:
            return
        j = min(n, i + len(sig))
        out[i:j] += sig[:j - i]

    def env(length, attack, release):
        m = int(length * SR)
        e = np.ones(m, np.float32)
        a, r = max(1, int(attack * SR)), max(1, int(release * SR))
        e[:a] = np.linspace(0, 1, a)
        e[-r:] *= np.linspace(1, 0, r)
        return e

    for b, (root, kind) in enumerate(chords):
        start = b * bar
        if start >= seconds:
            break
        length = min(bar + 0.45, seconds - start)
        tt = np.arange(int(length * SR)) / SR
        third = 3 if kind == "m" else 4
        pad = np.zeros_like(tt, dtype=np.float32)
        for semis in (0, third, 7, 12):
            f = hw.hz(root + semis)
            for det in (-0.0018, 0.0018):
                vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * tt)
                ph = 2 * np.pi * f * (1 + det) * np.cumsum(vib) / SR
                pad += (np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.22 * np.sin(3 * ph) + 0.1 * np.sin(4 * ph)).astype(np.float32)
        add(pad * env(length, 0.18, 0.5) * 0.028, start)
        up = [0, third, 7, 12, 7, third, 7, 12] if b % 2 == 0 else [12, 7, third, 7, 0, third, 7, third]
        for k, semis in enumerate(up):
            ts = start + k * beat / 2
            if ts >= seconds:
                break
            tt2 = np.arange(int(0.9 * SR)) / SR
            f = hw.hz(root + 24 + semis)
            tone = np.sin(2 * np.pi * f * tt2) + 0.25 * np.sin(2 * np.pi * 2 * f * tt2) + 0.12 * np.sin(2 * np.pi * 2.76 * f * tt2)
            add((tone * np.exp(-tt2 / 0.32) * np.minimum(1, tt2 / 0.004) * 0.11).astype(np.float32), ts)
        for k in (0, 2):
            ts = start + k * beat
            tt3 = np.arange(int(0.5 * SR)) / SR
            f = hw.hz(root - 12) * (1 + 0.5 * np.exp(-tt3 / 0.03))
            ph = 2 * np.pi * np.cumsum(f) / SR
            add((np.sin(ph) * np.exp(-tt3 / 0.16) * np.minimum(1, tt3 / 0.004) * 0.34).astype(np.float32), ts)
    for start, length, path in theremin:
        tt4 = np.arange(int(length * SR)) / SR
        midi = np.interp(tt4, np.linspace(0, length, len(path)), np.array(path, np.float32))
        f = 440.0 * 2 ** ((midi - 69) / 12) * (1 + 0.016 * np.sin(2 * np.pi * 6.3 * tt4))
        ph = 2 * np.pi * np.cumsum(f) / SR
        add((np.sin(ph) * env(length, 0.35, 0.8) * 0.12).astype(np.float32), start)
    fade = int(0.8 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(out * 1.4) / np.tanh(1.4)
    return out / max(1e-6, float(np.max(np.abs(out)))) * 0.89


def main(mode, times=None):
    R = C.Reel("hwfc")
    film, ev, music, title = build(R)
    if mode == "stills":
        ts = times or [0.0, 1.0, 3.0, 5.5, 8.0, 10.5, 12.3, 14.5, 16.8, 18.5, 20.8, 23.6]
        print(film.stills([t for t in ts if t < R.dur], "hwfc"))
        return
    vid = os.path.join(C.OUT, "_hwfc_video.mp4")
    film.video(vid, cover_t=0.8)
    mix = C.soundtrack(R, music, ev, music_gain=0.45)
    out = os.path.join(C.OUT, OUTFILE)
    C.finish(R, vid, mix, out, title)
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    main(sys.argv[1], [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None)
