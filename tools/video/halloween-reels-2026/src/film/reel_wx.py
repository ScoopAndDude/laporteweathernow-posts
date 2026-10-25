"""Weather + La Porte history: a Facebook reel (Oct. 22, 2026) in the Daily Video's look.

    python3 reel_wx.py stills|video

This week's forecast is the National Weather Service's for La Porte (point forecast as of 9:17 AM CDT Sunday,
Oct. 25, 2026, from the site's nws-snapshot.json; first cut used Thursday, Oct. 22's). The history is the "La Porte weather
anomaly": Stanley Changnon (Illinois State Water Survey, 1968) found La Porte had more rain, thunderstorms and hail
than the towns around it for decades in the mid-1900s and blamed the steel mills upwind in Chicago and Gary.
Later studies doubted it. Maps: U.S. Census Bureau county lines (via plotly/datasets) and Natural Earth's lakes.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import reels_common as C
from reels_common import bs, vr, W, H, SR, T, glow, paste, scaled, appear, ease, ease_out, dim, BONE

AMBER, GOLD, INK, SOFT, FAINT, BLUE, ICE = vr.AMBER, vr.GOLD, vr.INK, vr.SOFT, vr.FAINT, vr.BLUE, vr.ICE
X0, CW = vr.X0, vr.CW
GEO10 = os.path.join(C.ROOT, "dl", "geo10")

# NWS forecast for La Porte as of 9:17 AM CDT Sunday, Oct. 25, 2026 (point forecast via the site's nws-snapshot.json)
DAYS = [("MON", "sun-small-cloud", 69, "Mostly sunny", None), ("TUE", "sun-cloud", 68, "Partly sunny", None),
        ("WED", "sun-small-cloud", 73, "Mostly sunny", None), ("THU", "sun-small-cloud", 72, "Mostly sunny", 20)]

# the map: lon -88.30 .. -85.90, lat 40.55 .. 42.45, 900 px per degree of longitude
LON0, LAT1, KX, KY = -88.30, 42.45, 900.0, 900.0 / math.cos(math.radians(41.6))
MW, MH = int(2.4 * KX), int(1.9 * KY)
PANEL = (60, 360, 1020, 1262)          # x0, y0, x1, y1 on screen
CITIES = [("La Porte", 41.6106, -86.7225, "s"), ("Michigan City", 41.7075, -86.8950, "n"),
          ("Valparaiso", 41.4731, -87.0611, "s"), ("South Bend", 41.6764, -86.2520, "s"),
          ("Chicago", 41.8781, -87.6298, "w"), ("Gary", 41.5934, -87.3464, "s")]
MILLS = [("South Chicago", 41.735, -87.545), ("Gary", 41.612, -87.330)]


def mxy(lon, lat):
    return ((lon - LON0) * KX, (LAT1 - lat) * KY)


def build_map():
    S = 2
    img = Image.new("RGBA", (MW * S, MH * S), (13, 33, 54, 255))
    d = ImageDraw.Draw(img)
    cj = json.load(open(os.path.join(GEO10, "counties.json")))
    polys, lp = [], []
    for ft in cj["features"]:
        g = ft["geometry"]
        rings = [r for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]) for r in p]
        pts = [p for r in rings for p in r]
        if max(p[0] for p in pts) < LON0 - 0.1 or min(p[0] for p in pts) > LON0 + 2.5:
            continue
        if max(p[1] for p in pts) < LAT1 - 2.0 or min(p[1] for p in pts) > LAT1 + 0.1:
            continue
        for r in rings:
            sp = [(mxy(x, y)[0] * S, mxy(x, y)[1] * S) for x, y in r]
            polys.append(sp)
            if ft["properties"].get("NAME") == "LaPorte" and ft["properties"].get("STATE") == "18":
                lp.append(sp)
    for sp in polys:
        d.polygon(sp, fill=(30, 30, 35, 255))
    lakes = json.load(open(os.path.join(GEO10, "ne_10m_lakes.geojson")))
    for ft in lakes["features"]:
        if ft["properties"].get("name") == "Lake Michigan":
            g = ft["geometry"]
            for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
                d.polygon([(mxy(x, y)[0] * S, mxy(x, y)[1] * S) for x, y in p[0]], fill=(13, 33, 54, 255))
    for sp in polys:
        d.line(sp + sp[:1], fill=(70, 70, 82, 255), width=2 * S)
    for sp in lp:
        d.line(sp + sp[:1], fill=AMBER + (255,), width=5 * S, joint="curve")
    img = img.resize((MW, MH), Image.LANCZOS)
    lake = vr.text_img("Lake Michigan", "semi", 40, (92, 150, 205, 255))
    x, y = mxy(-87.05, 42.08)
    img.alpha_composite(lake, (int(x - lake.width / 2), int(y)))
    return img


class MapCam:
    def __init__(self, keys):
        self.keys = keys                # (t, s, lon, lat): screen px per map px, centre of the panel

    def at(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1:]
        for a, b in zip(ks, ks[1:]):
            if t <= b[0]:
                u = ease((t - a[0]) / max(1e-6, b[0] - a[0]))
                return tuple(a[i] + (b[i] - a[i]) * u for i in (1, 2, 3))
        return ks[-1][1:]

    def view(self, m, t):
        s, lon, lat = self.at(t)
        cx, cy = mxy(lon, lat)
        pw, ph = PANEL[2] - PANEL[0], PANEL[3] - PANEL[1]
        bw, bh = pw / s, ph / s
        x0, y0 = cx - bw / 2, cy - bh / 2
        crop = m.resize((pw, ph), Image.BICUBIC, box=(x0, y0, x0 + bw, y0 + bh))
        mask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=30, fill=255)
        crop.putalpha(mask)

        def to(lon2, lat2):
            px, py = mxy(lon2, lat2)
            return PANEL[0] + (px - x0) * s, PANEL[1] + (py - y0) * s
        return crop, to, s


def city_label(name, home=False):
    col = GOLD if home else INK
    lab = vr.text_img(name, "bold" if home else "semi", 34 if home else 28, col + (255,))
    return vr.glow(lab, (0, 0, 0), radius=8, strength=0.95)


def dotimg(r, col):
    S = 4
    img = Image.new("RGBA", ((r + 4) * 2 * S,) * 2, (0, 0, 0, 0))
    c = img.width / 2
    ImageDraw.Draw(img).ellipse((c - (r + 3) * S, c - (r + 3) * S, c + (r + 3) * S, c + (r + 3) * S), fill=(10, 10, 12, 255))
    ImageDraw.Draw(img).ellipse((c - r * S, c - r * S, c + r * S, c + r * S), fill=tuple(col) + (255,))
    return img.resize((img.width // S, img.height // S), Image.LANCZOS)


def hail_icon(size):
    img = vr.icon("cloud", size)
    d = ImageDraw.Draw(img)
    for (x, y, r) in ((0.32, 0.80, 0.07), (0.52, 0.86, 0.075), (0.70, 0.78, 0.065)):
        d.ellipse(((x - r) * size, (y - r) * size, (x + r) * size, (y + r) * size), fill=(232, 244, 255, 255),
                  outline=(150, 190, 230, 255), width=max(1, size // 40))
    return img


def factory(w=150):
    S = 3
    h = int(w * 1.05)
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = (186, 186, 196, 255)
    d.polygon([(0.05 * w * S, h * S), (0.05 * w * S, 0.62 * h * S), (0.30 * w * S, 0.50 * h * S), (0.30 * w * S, 0.62 * h * S),
               (0.55 * w * S, 0.50 * h * S), (0.55 * w * S, 0.62 * h * S), (0.95 * w * S, 0.62 * h * S),
               (0.95 * w * S, h * S)], fill=col)
    for x in (0.64, 0.76, 0.88):
        d.rectangle(((x - 0.04) * w * S, 0.12 * h * S, (x + 0.04) * w * S, 0.62 * h * S), fill=col)
    return img.resize((w, h), Image.LANCZOS)


def pill_chip(text, kind):
    ic = {"rain": vr.icon("rain", 64), "storm": vr.icon("storm", 64), "hail": hail_icon(64)}[kind]
    bg, border = {"rain": ((20, 50, 96, 240), BLUE), "storm": ((58, 38, 6, 240), AMBER),
                  "hail": ((28, 52, 74, 240), ICE)}[kind]
    return vr.pill(text, "black", 46, INK, bg, border=border, icon=ic, padx=28, pady=14)


def day_cards():
    n, gap = len(DAYS), 20
    cw = int((CW + 20 - gap * (n - 1)) / n)
    contents = []
    for name, ic, hi, text, pop in DAYS:
        parts = [(vr.text_img(name, "black", 58, INK), 26), (vr.icon(ic, min(190, cw - 40)), 18),
                 (vr.text_img(vr.deg(hi), "black", 104, INK), 22)]
        txt = vr.fit_para(text, "semi", 33, SOFT, cw - 36, max_lines=3, min_size=26, align="center")
        parts.append((txt, 22))
        if pop:
            parts.append((vr.pill(f"{pop}%", "bold", 34, INK, (20, 50, 96, 255), border=BLUE,
                                  icon=vr.icon("drop", 32), padx=20, pady=12), 0))
        contents.append(parts)
    ch = 40 + max(sum(img.height + g for img, g in parts) for parts in contents) + 40
    cards = []
    for parts in contents:
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=30, fill=(255, 255, 255, 18))
        yy = 40
        for img, g in parts:
            card.alpha_composite(img, ((cw - img.width) // 2, yy))
            yy += img.height + g
        cards.append(card)
    return cards, cw, gap


def rain_layer(t, n=380, seed=4, a=95, length=46, slant=0.22, speed=2300):
    rng = np.random.default_rng(seed)
    xs, ys0 = rng.uniform(-200, W + 100, n), rng.uniform(0, H, n)
    sp = rng.uniform(0.75, 1.25, n) * speed
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(n):
        y = (ys0[i] + sp[i] * t) % (H + 200) - 100
        x = xs[i] + slant * (y - ys0[i] % H) * 0.0 + slant * y * 0.25
        L = length * sp[i] / speed
        d.line((x, y, x - slant * L, y - L), fill=(205, 215, 230, int(a * rng.uniform(0.5, 1.0))), width=2)
    return lay


def build(R):
    t_this = R.at("This week?")
    t_but = R.at("But for")
    t_mid = R.at("mid-1900s,")
    t_la2 = R.at("La Porte got")
    t_rain, t_thun, t_hail = R.at("rain,"), R.at("thunderstorms"), R.at("hail")
    t_towns = R.at("towns around")
    t_one = R.at("One scientist")
    t_poll, t_steel = R.at("pollution"), R.at("steel mills")
    t_chi, t_gary = R.at("Chicago"), R.at("Gary.")
    t_others = R.at("Others")
    t_dbl = R.at("Double-tap")
    c1 = (R.end("it.") + t_this) / 2
    c2 = (R.end("Halloween.") + t_but) / 2
    c3 = t_la2 - 0.25
    c4 = (R.end("it.", t_towns) + t_one) / 2
    c5 = (R.end("Gary.") + t_others) / 2
    c6 = (R.end("it.", t_others) + t_dbl) / 2
    shared = {}

    def prep_hook(ctx):
        ctx["im"] = bs.photo("laporte-11.jpg", "night", inset=0.03)
        ctx["l1"] = vr.glow(vr.text_img("LA PORTE'S", "black", 92, INK), (0, 0, 0), radius=20, strength=0.9)
        big = vr.fit_line("WEATHER ANOMALY", "black", 120, GOLD, CW + 40, min_size=80)
        ctx["l2"] = vr.glow(big, AMBER, radius=30, strength=0.6)
        ctx["lab"] = vr.glow(vr.label_img("La Porte weather history"), (0, 0, 0), radius=12, strength=0.9)

    def draw_hook(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c1, z=(1.08, 1.18), f0=(0.5, 0.5), f1=(0.55, 0.48))
        f.alpha_composite(rain_layer(t))
        bs.shade(f)
        paste(f, ctx["lab"], W / 2, 300)
        paste(f, ctx["l1"], W / 2, 1060)
        k = ease_out(t / 0.6)
        paste(f, scaled(ctx["l2"], 1.06 - 0.06 * k), W / 2, 1185)
        bs.credit_line(f, C.bs.credit("laporte-11.jpg") + " · La Porte, about 1912")

    def prep_fc(ctx):
        ctx["bg"] = vr.background("warm")
        ctx["lab"] = vr.label_img("This week in La Porte")
        ctx["cards"], ctx["cw"], ctx["gap"] = day_cards()
        ctx["night"] = vr.pill("Nights around 50", "bold", 44, INK, (34, 30, 60, 255), border=(150, 140, 220),
                               icon=vr.icon("moon", 50), padx=30, pady=16)
        ctx["src"] = vr.text_img("Source: National Weather Service", "semi", 28, FAINT)

    def draw_fc(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        f.alpha_composite(C.alpha(ctx["lab"], appear(u, 0.0, 0.3)), (X0, 330))
        for i, card in enumerate(ctx["cards"]):
            a = appear(t, t_this - 0.05 + 0.08 * i, 0.32)
            f.alpha_composite(C.alpha(card, a), (X0 - 10 + i * (ctx["cw"] + ctx["gap"]), int(410 + 34 * (1 - a))))
        ch = ctx["cards"][0].height
        a = appear(t, R.at("near seventy,") - 0.1, 0.32)
        f.alpha_composite(C.alpha(ctx["night"], a), ((W - ctx["night"].width) // 2, int(410 + ch + 50 + 30 * (1 - a))))
        f.alpha_composite(ctx["src"], (X0, 1470))

    def prep_old(ctx):
        from PIL import ImageEnhance
        im = Image.open(os.path.join(C.BSRC, "images", "laporte-09.jpg")).convert("RGB")
        im = ImageEnhance.Color(im).enhance(0.8).convert("RGBA")
        wpc = 880
        pc = im.resize((wpc, int(im.height * wpc / im.width)), Image.LANCZOS)
        fr = Image.new("RGBA", (pc.width + 28, pc.height + 28), (240, 234, 220, 255))
        fr.alpha_composite(pc, (14, 14))
        sh = Image.new("RGBA", (fr.width + 90, fr.height + 90), (0, 0, 0, 0))
        m = Image.new("L", sh.size, 0)
        ImageDraw.Draw(m).rectangle((45, 58, 45 + fr.width, 58 + fr.height), fill=180)
        sh.putalpha(m.filter(ImageFilter.GaussianBlur(20)))
        sh.alpha_composite(fr, (45, 45))
        ctx["pc"] = sh.rotate(2.0, expand=True, resample=Image.BICUBIC)
        ctx["bg"] = bs.photo("laporte-09.jpg", "sepia", inset=0.03).filter(ImageFilter.GaussianBlur(9))

    def draw_old(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c3 - c2, z=(1.1, 1.16))
        dim(f, 0.5)
        z = 0.95 + 0.06 * min(1.0, u / (c3 - c2))
        paste(f, scaled(ctx["pc"], z), W / 2, 770, appear(u, 0.0, 0.2))
        f.alpha_composite(rain_layer(t, n=220, a=60, seed=6))
        bs.shade(f)
        from reel_belle import typed
        typed(f, "MID-1900s", t, t_mid, 330)
        bs.credit_line(f, "Hotel Rumely, La Porte (Tichnor Bros. postcard, public domain)")

    def prep_map(ctx):
        if "map" not in shared:
            shared["map"] = build_map()
            shared["bg"] = vr.background("storm")
            shared["labels"] = {c[0]: city_label(c[0], c[0] == "La Porte") for c in CITIES}
            shared["dots"] = {"home": dotimg(10, GOLD), "town": dotimg(7, INK), "dim": dotimg(7, (110, 110, 120))}
            shared["chips"] = [pill_chip("MORE RAIN", "rain"), pill_chip("MORE THUNDERSTORMS", "storm"),
                               pill_chip("MORE HAIL", "hail")]
            shared["storm"] = vr.icon("storm", 170)
            shared["fac"] = factory(120)
            shared["lab1"] = vr.label_img("What the weather records showed")
            shared["lab2"] = vr.label_img("Stanley Changnon, 1968 study")
            shared["stamp"] = bs.stamp([("STILL", 96), ("DEBATED", 104)], color=(240, 84, 64))
            shared["arrow"] = arrow_img()
            shared["wind"] = vr.glow(vr.text_img("WIND", "bold", 30, SOFT, tracking=4), (0, 0, 0), radius=8,
                                     strength=0.9)
            shared["cam"] = MapCam([(c3, 1.02, -86.80, 41.66), (t_one - 0.1, 1.06, -86.80, 41.66),
                                    (t_poll + 0.2, 0.60, -87.05, 41.72), (c6, 0.62, -87.05, 41.72)])
        ctx.update(shared)

    def draw_map(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        crop, to, s = ctx["cam"].view(ctx["map"], t)
        f.alpha_composite(crop, (PANEL[0], PANEL[1]))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # the mills' smoke, blowing east toward La Porte
        if t >= t_poll - 0.2:
            k = appear(t, t_poll - 0.2, 0.6)
            rng = np.random.default_rng(3)
            for name, lat, lon in MILLS:
                x, y = to(lon, lat)
                for i in range(26):
                    ph = (t * 0.22 + i / 26 + rng.uniform(0, 0.03)) % 1.0
                    px = x + ph * 520 * s / 0.6 + 14 * math.sin(i * 1.7 + t)
                    py = y - 40 - ph * 70 + 10 * math.sin(i * 2.3)
                    r = int(10 + 46 * ph)
                    lay.alpha_composite(bs.soft_dot(r, (150, 146, 140), int(120 * (1 - ph) * k)),
                                        (int(px - 2 * r), int(py - 2 * r)))
        f.alpha_composite(lay)
        for name, lat, lon in MILLS:
            if t >= t_steel - 0.1:
                x, y = to(lon, lat)
                k = appear(t, t_steel - 0.1 + (0.15 if name == "Gary" else 0), 0.25)
                paste(f, scaled(ctx["fac"], 0.6 + 0.4 * k), x, y - 30, k)
        if t >= t_poll:
            k = appear(t, t_poll, 0.4)
            for i, (lon, lat) in enumerate(((-87.35, 41.86), (-87.05, 41.52), (-86.95, 41.95))):
                x, y = to(lon, lat)
                drift = 26 * ((t * 0.8 + i * 0.33) % 1.0)
                paste(f, ctx["arrow"], x + drift, y, k * 0.85)
            x, y = to(-87.35, 41.86)
            paste(f, ctx["wind"], x, y - 44, k)
        # the towns
        home = to(-86.7225, 41.6106)
        for name, lat, lon, side in CITIES:
            if name in ("Chicago", "Gary") and t < t_poll:
                continue
            x, y = to(lon, lat)
            if not (PANEL[0] + 10 < x < PANEL[2] - 10 and PANEL[1] + 10 < y < PANEL[3] - 10):
                continue
            homey = name == "La Porte"
            dimmed = (not homey) and t_towns <= t < c4 + 0.2 and name not in ("Chicago", "Gary")
            dt = ctx["dots"]["home" if homey else ("dim" if dimmed else "town")]
            paste(f, dt, x, y)
            lab = ctx["labels"][name]
            pulse = 0.0
            for at, nm in ((t_chi, "Chicago"), (t_gary, "Gary")):
                if nm == name and 0 <= t - at < 0.5:
                    pulse = math.sin(math.pi * (t - at) / 0.5)
            lab2 = scaled(lab, 1 + 0.18 * pulse)
            if side == "s":
                paste(f, lab2, x, y + 30, 0.55 if dimmed else 1.0)
            elif side == "n":
                paste(f, lab2, x, y - 30, 0.55 if dimmed else 1.0)
            elif side == "w":
                paste(f, lab2, x - 14 - lab2.width / 2, y, 1.0)
            else:
                paste(f, lab2, x + 14 + lab2.width / 2, y, 1.0)
        # La Porte: a glow, and the storm over it while the records are read out
        k = 0.5 + 0.5 * math.sin(t * 4.0)
        paste(f, C.ring(16 + 10 * k, 4, GOLD, 0.6), home[0], home[1])
        if c3 <= t < c4 + 0.3:
            a = appear(t, t_rain - 0.1, 0.3) * (1 - ease((t - c4) / 0.3))
            paste(f, ctx["storm"], home[0] + 10, home[1] - 120 + 6 * math.sin(t * 2.2), a)
        # labels and chips
        if t < c4:
            f.alpha_composite(C.alpha(ctx["lab1"], appear(t, c3, 0.3)), (X0, 290))
            for i, (chip, at) in enumerate(zip(ctx["chips"], (t_rain, t_thun, t_hail))):
                a = appear(t, at - 0.08, 0.25)
                if a > 0:
                    f.alpha_composite(C.alpha(chip, a), (int(PANEL[0] + 24 - 30 * (1 - a)), PANEL[1] + 24 + i * 104))
        else:
            f.alpha_composite(C.alpha(ctx["lab2"], appear(t, c4, 0.3)), (X0, 290))
        if t >= t_others - 0.05:
            k = appear(t, t_others - 0.05, 0.12)
            sz = 1.0 + 1.0 * (1 - k)
            paste(f, scaled(ctx["stamp"], sz), W / 2, 820, min(1.0, k * 1.2))
        bs.credit_line(f, "Map: U.S. Census Bureau, Natural Earth")

    def prep_end(ctx):
        ctx["bg"] = vr.background("warm")
        ctx["cta"] = C.DoubleTap("FOR THE FULL FORECAST", "+ more La Porte weather history", color1=GOLD,
                                 glow1=AMBER, kind1="black", size1=84, y=520)
        ctx["url"] = vr.pill("laporteweathernow.com", "xbold", 50, (10, 10, 12), GOLD + (255,), padx=36, pady=20)

    def draw_end(f, u, t, ctx):
        f.alpha_composite(ctx["bg"])
        ctx["cta"].draw(f, u)
        paste(f, ctx["url"], W / 2, 1185, appear(u, 0.9, 0.3))

    scenes = [C.Scene(0.0, c1, draw_hook, prep_hook), C.Scene(c1, c2, draw_fc, prep_fc),
              C.Scene(c2, c3, draw_old, prep_old), C.Scene(c3, c6, draw_map, prep_map),
              C.Scene(c6, R.dur + 1, draw_end, prep_end, flicker=0.0)]
    for sc in scenes[1:]:
        if sc.flicker is None:
            sc.flicker = 0.0
    atm = bs.Atmos(tint=(196, 196, 204), fog=0.1, vignette=0.55, grain=10, seed=3)
    film = C.Film(R, scenes, flashes=[(0.45, 0.32), (2.35, 0.32)], flicker=0.25, atmos=atm)
    import sfx as X
    rain = X.rain(c3 + 1.0, seed=34).mean(1)
    rain[-int(1.0 * SR):] *= np.linspace(1, 0, int(1.0 * SR))
    fade_mid = np.ones(len(rain), np.float32)
    fade_mid[int(c1 * SR):int(c2 * SR)] = 0.25                     # quieter under the forecast
    ev = [(rain * fade_mid * 0.9, 0.0, 1.0, "bed"), (X.thunder(5.0, seed=9).mean(1), 0.42, 0.9, "bed"),
          (X.thunder(4.0, seed=12, crack=False).mean(1), 2.33, 0.7, "bed"),
          ("whoosh", c1, 0.6), ("pop", t_this, 0.5), ("whoosh", c2, 0.6), ("type", t_mid, 1.0),
          ("whoosh", c3, 0.6), ("pop", t_rain - 0.08, 0.7), ("pop", t_thun - 0.08, 0.7), ("pop", t_hail - 0.08, 0.7),
          (X.thunder(4.0, seed=15, crack=False).mean(1), t_thun, 0.5, "bed"), ("whoosh", t_poll - 0.1, 0.5),
          ("hit", t_others - 0.02, 0.9), ("pop", c6 + 0.12, 0.9), ("pop", c6 + 0.42, 0.9), ("hit", c6 + 0.5, 0.6)]
    music = X.pad(R.dur + 1, [110.0, 164.81, 220.0, 261.63], seed=44, attack=2.5, release=2.0).mean(1) * 0.9 \
        + X.drone(R.dur + 1, seed=45).mean(1) * 0.5
    return film, ev, music, "La Porte's Weather Anomaly"


def arrow_img(w=120):
    S = 3
    h = 40
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(4 * S, h * S / 2), ((w - 26) * S, h * S / 2)], fill=(236, 236, 242, 230), width=7 * S)
    d.polygon([((w - 36) * S, 4 * S), (w * S - 2, h * S / 2), ((w - 36) * S, (h - 4) * S)], fill=(236, 236, 242, 230))
    return img.resize((w, h), Image.LANCZOS)


OUTFILE = "la-porte-weather-anomaly.mp4"


def main(mode, times=None):
    R = C.Reel("wx")
    film, ev, music, title = build(R)
    if mode == "stills":
        ts = times or [0.4, 1.8, 3.2, 4.4, 6.5, 8.5, 9.8, 11.4, 12.3, 13.6, 15.5, 17.4, 18.8, 20.3, 22.4, 24.8]
        print(film.stills([t for t in ts if t < R.dur], "wx"))
        return
    vid = os.path.join(C.OUT, "_wx_video.mp4")
    film.video(vid, cover_t=0.8)
    mix = C.soundtrack(R, music, ev, music_gain=0.35)
    out = os.path.join(C.OUT, OUTFILE)
    C.finish(R, vid, mix, out, title)
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    main(sys.argv[1], [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None)
