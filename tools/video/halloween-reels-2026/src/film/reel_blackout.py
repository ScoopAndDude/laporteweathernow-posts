"""Power-outage prep shorts, parts 1-3 ("Could your house last 3 days?"), Oct. 2026.

    python3 reels_vo.py bo1 bo2 bo3          # record (once)
    python3 reel_blackout.py 1|2|3 stills|video [times]

Hooked to the Pentagon's FORTRESS America plan (bases able to run 90 days on their own, as Fox News reported on
Oct. 25, 2026), and plain that it isn't a blackout notice for homes. Every tip is from Ready.gov/FEMA, the CDC, the
CPSC, the National Weather Service, FoodSafety.gov, the FDA, the Red Cross, NIPSCO or Indiana FSSA, at least two each
(claims and links: posts-blackout.json). Pictures are drawn (blackout_art.py); no people, no logos.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import blackout_art as BA
import reels_common as C
from reels_common import bs, vr, W, H, SR, paste, scaled, appear, ease_out

X0, CW = vr.X0, vr.CW
GOLDEN, CREAM, INK = (255, 196, 84), (246, 238, 222), vr.INK
FAINT = (178, 186, 208)
NAVY_CARD = (22, 30, 56, 236)
AMBER, RED, GREEN, WATER = BA.AMBER, BA.RED, BA.GREEN, BA.WATER
OUTFILES = {1: "outage-part-1-fortress-90-days.mp4", 2: "outage-part-2-staying-warm.mp4",
            3: "outage-part-3-food-and-water.mp4"}
TITLES = {1: "Could your house last 3 days? Part 1", 2: "Could your house last 3 days? Part 2",
          3: "Could your house last 3 days? Part 3"}
C.WEIGHT.update({"444111": 6.5, "2-1-1": 3.6, "911": 3.2, "NIPSCO.com": 4.6, "NIPSCO": 2.2, "FORTRESS": 2.2})


# ----------------------------------------------------------------------------- drawing helpers
def base():
    """Night blue fading to black."""
    g = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([16, 22, 44]), np.array([4, 6, 12])
    arr = np.zeros((H, W, 3), np.float32)
    for c in range(3):
        arr[:, :, c] = top[c] * (1 - g[:, 0])[:, None] + bot[c] * g[:, 0][:, None]
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    return img


SNOW = np.random.default_rng(11).uniform(0, 1, (90, 4))


def snow_layer(t, a=110):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for x0, y0, sp, r in SNOW:
        y = (y0 * (H + 100) + (40 + 70 * sp) * t) % (H + 100) - 50
        x = x0 * W + 18 * math.sin(t * (0.6 + sp) + 6 * x0)
        rr = 2 + 3 * r
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(235, 240, 255, int(a * (0.4 + 0.6 * r))))
    return lay


def label(text):
    return vr.text_img(text.upper(), "bold", 36, GOLDEN, tracking=4)


def head(text, color=CREAM, size=104, glow=None):
    img = vr.fit_para(text, "black", size, color, CW, max_lines=2, min_size=60, align="center")
    return vr.glow(img, glow, radius=26, strength=0.6) if glow else img


def card(name, line, accent, art=None, h=176):
    w = CW + 20
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=30, fill=NAVY_CARD, outline=accent + (150,), width=3)
    d.rounded_rectangle((0, 0, 16, h - 1), radius=8, fill=accent + (255,))
    room = w - (210 if art is not None else 80)
    nm = vr.fit_line(name, "xbold", 58, CREAM, room, min_size=38)
    ln = vr.fit_line(line, "semi", 38, FAINT, room, min_size=28) if line else None
    hh = nm.height + (16 + ln.height if ln else 0)
    y = (h - hh) // 2
    img.alpha_composite(nm, (46, y))
    if ln:
        img.alpha_composite(ln, (46, y + nm.height + 16))
    if art is not None:
        img.alpha_composite(art, (w - art.width - 26, (h - art.height) // 2))
    return img


def pill(text, fill=AMBER, ink=(16, 16, 20), size=46):
    return vr.pill(text, "bold", size, ink, fill + (255,), padx=34, pady=18)


def pop(f, img, cx, cy, t, at, dur=0.35, grow=0.12):
    a = appear(t, at, dur)
    if a > 0:
        paste(f, scaled(img, 1 + grow * (1 - ease_out(min(1.0, (t - at) / dur)))), cx, cy, a)


def slide(f, img, x, y, t, at, dur=0.3):
    a = appear(t, at, dur)
    if a > 0:
        f.alpha_composite(C.alpha(img, a), (int(x - 40 * (1 - a)), int(y)))


def two(a, b, color=CREAM, size=96, glow=None):
    """A headline in two set lines (no orphan words)."""
    img = col([vr.fit_line(a, "black", size, color, CW, min_size=56), vr.fit_line(b, "black", size, color, CW, min_size=56)],
              gap=16)
    return vr.glow(img, glow, radius=26, strength=0.6) if glow else img


def follow(text, sub=None):
    """The closing call: 'FOLLOW FOR PART 2'."""
    big = vr.glow(vr.fit_line(text, "black", 96, GOLDEN, CW, min_size=60), (255, 140, 0), radius=24, strength=0.6)
    small = vr.fit_line(sub, "semi", 40, FAINT, CW, min_size=30) if sub else None
    return big, small


# ----------------------------------------------------------------------------- the three parts
TOP, BOTTOM = 400, 1235              # the content zone: under the label, above the captions (1290-1400)


def row(items, gap=50):
    """Side by side, centered on one baseline row: [(img, at)] -> a 'row' item."""
    return ("row", items, gap)


def col(imgs, gap=14):
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for i in imgs:
        out.alpha_composite(i, ((w - i.width) // 2, y))
        y += i.height + gap
    return out


def txt(text, kind="xbold", size=58, color=CREAM, max_w=None):
    return vr.fit_line(text, kind, size, color, max_w or CW, min_size=30)


def layout(items, gaps):
    """y (top) for each item, the stack centered in the content zone."""
    hs = []
    for it in items:
        if it[0] == "row":
            hs.append(max(img.height for img, _ in it[1]))
        else:
            hs.append(it[0].height)
    total = sum(hs) + sum(gaps[:len(items) - 1])
    y = TOP + max(0, (BOTTOM - TOP - total) // 2)
    ys = []
    for h, g in zip(hs, gaps + [0]):
        ys.append(y)
        y += h + g
    return ys, hs


def draw_items(f, t, items, ys, hs):
    for it, y, h in zip(items, ys, hs):
        if it[0] == "row":
            _, subs, gap = it
            total = sum(img.width for img, _ in subs) + gap * (len(subs) - 1)
            x = (W - total) // 2
            for img, at in subs:
                cy = y + h / 2
                if at is None:
                    paste(f, img, x + img.width / 2, cy)
                else:
                    pop(f, img, x + img.width / 2, cy, t, at)
                x += img.width + gap
            continue
        img, at, kind = it
        if at is None:
            paste(f, img, W / 2, y + h / 2)
        elif kind == "slide":
            slide(f, img, (W - img.width) // 2, y, t, at)
        else:
            pop(f, img, W / 2, y + h / 2, t, at, 0.32, 0.08 if img.width > 600 else 0.14)


def scenes_for(part, R):
    n = len(set(it["para"] for it in R.items))
    cuts = [0.0] + [R.para(p)[0] - 0.2 for p in range(1, n)] + [R.dur + 1.0]
    at = R.at
    S = lambda k, d=0.05: cuts[k] + d          # noqa: E731  (a time just after scene k starts)
    specs = []                                 # (label, [items], [gaps], credit)
    if part == 1:
        news = "90 days: Fox News (Oct. 25). Speech: DefenseScoop; Air & Space Forces Magazine"
        tips = "Ready.gov (FEMA); CDC; American Red Cross"
        specs.append(("A reported 90-day goal for bases", lambda: [
            row([(col([BA.calendar(330), txt("Major bases", size=62), txt("90 days on their own", "semi", 40, FAINT, 460)]),
                  None),
                 (col([BA.house(330, lit=False), txt("Your house", size=62),
                       vr.glow(txt("3 days?", "black", 92, GOLDEN), (255, 140, 0), radius=24, strength=0.6)]), None)],
                gap=40),
            (txt("As reported by Fox News", "semi", 38, FAINT), None, "pop")], [70], news))
        specs.append(("FORTRESS America", lambda: [
            (pill("Announced Sept. 30, 2026", AMBER), at("announced September"), "pop"),
            (BA.bulb(300, on=True), S(1), "pop"),
            (head("Bases that make their own power", CREAM, 88), at("One goal"), "pop"),
            (card('"...our bases stay lit."', "Pete Hegseth, Sept. 30, 2026", AMBER), at("His words"), "slide")],
            [26, 24, 34], news))
        specs.append(("What it isn't", lambda: [
            (BA.house(300, lit=True), S(2), "pop"),
            (head("Not a blackout notice", CREAM, 100), at("a blackout notice") - 0.2, "pop"),
            (card("No home power cuts", "in anything announced", GREEN), at("Nothing announced"), "slide"),
            (card("A long-term military plan", "starting with bases", GREEN), at("It's a long-term"), "slide")],
            [20, 30, 20], news))
        specs.append(("Your first hour", lambda: [
            (head("Power out?", CREAM, 120), S(3), "pop"),
            row([(BA.flashlight(280), at("Flashlights, not")), (BA.no(BA.candle(220)), at("not candles"))], gap=90),
            (txt("Flashlights, not candles (a fire risk)", "semi", 44, FAINT), at("not candles"), "pop"),
            (card("Unplug electronics", "Power can surge when it comes back", AMBER, BA.plug(140)),
             at("Unplug electronics"), "slide")], [20, 14, 40], tips))
        specs.append(("Your first hour", lambda: [
            (BA.fridge(300), S(4), "pop"),
            (head("Keep the fridge and freezer shut", CREAM, 84), S(4, 0.15), "pop"),
            (card("Report the outage", "to your power company", GREEN, BA.phone(140)), at("Report the outage"),
             "slide"),
            (pill("NIPSCO: text OUT to 444111", GREEN), at("For NIPSCO"), "pop")],
            [20, 34, 24], "Ready.gov (FEMA); American Red Cross; NIPSCO (nipsco.com/outages)"))
        specs.append(("If it's safe to go out", lambda: [
            row([(BA.house(250, lit=False), S(5)), (BA.flashlight(190), S(5, 0.25)), (BA.house(250, lit=False),
                                                                                        S(5, 0.15))], gap=20),
            (head("Check on neighbors", CREAM, 100), at("Check on neighbors"), "pop"),
            (col(list(follow("FOLLOW FOR PART 2", "Staying warm, safely"))), at("Follow for part"), "pop")],
            [30, 60], "Ready.gov (FEMA); National Weather Service"))
    elif part == 2:
        cpsc = "U.S. Consumer Product Safety Commission; CDC"
        specs.append(("Part 2 · Staying warm", lambda: [
            row([(BA.generator(260), None), (BA.distance(300, "20+ FT"), None), (BA.house(300, lit=False), None)],
                gap=10),
            (head("Generator? Outside only", CREAM, 100), None, "pop"),
            (card("At least 20 feet away", "from windows, doors and vents", AMBER), at("at least 20"), "slide")],
            [30, 36], cpsc))
        specs.append(("Never in the garage", lambda: [
            (BA.no(BA.garage(330, inside=BA.generator(160))), S(1), "pop"),
            (two("Not even with", "the door open", CREAM, 96), at("even with the"), "pop"),
            (card("Exhaust = carbon monoxide", "You can't see it or smell it", RED), at("The exhaust"), "slide")],
            [24, 36], cpsc))
        specs.append(("Carbon monoxide alarm", lambda: [
            (BA.co_alarm(240), S(2), "pop"),
            (head("Batteries or battery backup", CREAM, 84), at("needs batteries"), "pop"),
            (card("Never heat with a gas oven", "or stove", RED, BA.no(BA.oven(124)), h=158), at("Never heat"),
             "slide"),
            (card("No grills indoors", None, RED, BA.no(BA.grill(124)), h=150), at("No grills"), "slide")],
            [20, 30, 16], "CDC; Ready.gov (FEMA); U.S. Consumer Product Safety Commission"))
        def sym(nm):
            return vr.pill(nm, "bold", 52, CREAM, (64, 30, 40, 255), padx=34, pady=14)
        specs.append(("Carbon monoxide signs", lambda: [
            row([(sym("Headache"), at("headache") - 0.05), (sym("Dizziness"), at("dizziness") - 0.05)], gap=24),
            row([(sym("Weakness"), at("weakness") - 0.05), (sym("Upset stomach"), at("upset stomach") - 0.05)], gap=24),
            row([(sym("Vomiting"), at("vomiting") - 0.05), (sym("Chest pain"), at("chest pain") - 0.05)], gap=24),
            (sym("Confusion"), at("confusion") - 0.05, "pop"),
            (card("Get outside", "then call 911", RED, BA.phone(130)), at("Get outside"), "slide")],
            [18, 18, 18, 40], "CDC; Indiana Homeland Security; U.S. CPSC"))
        specs.append(("Stay warm", lambda: [
            (BA.thermometer(300, color=(120, 170, 255)), S(4), "pop"),
            (two("Loose layers,", "a hat, blankets", CREAM, 92), at("loose layers") - 0.1, "pop"),
            (card("Close off rooms", "you don't need", AMBER, BA.house(140, lit=False)), at("Close off"), "slide")],
            [24, 36], "National Weather Service; CDC"))
        specs.append(("Too cold? Go.", lambda: [
            (BA.house(230, lit=True), S(5), "pop"),
            (two("Go somewhere", "with heat", CREAM, 92), at("Go somewhere"), "pop"),
            (card("In Indiana, call 2-1-1", "to find a warming center", AMBER, BA.phone(130)), at("In Indiana"),
             "slide"),
            (col(list(follow("FOLLOW FOR PART 3", "Food and water"))), at("Follow for part"), "pop")],
            [16, 28, 36], "Ready.gov (FEMA); CDC; Indiana FSSA (Indiana 211)"))
    else:
        food = "FoodSafety.gov; FDA; CDC"
        specs.append(("Part 3 · Food and water", lambda: [
            row([(BA.house(240, lit=False), None), (BA.fridge(300, badge="4 HR"), None)], gap=70),
            (head("Could your house last 3 days?", CREAM, 84), None, "pop"),
            (pill("Keep the doors shut", AMBER), at("Keep the doors"), "pop"),
            (vr.glow(txt("Fridge: about 4 hours", "black", 86, GOLDEN), (255, 140, 0), radius=24, strength=0.6),
             at("Your fridge keeps"), "pop")],
            [24, 30, 24], food))
        specs.append(("Freezer", lambda: [
            row([(col([BA.fridge(300, badge="48 HR", badge_color=WATER), txt("Full freezer", size=58)]),
                  at("A full freezer")),
                 (col([BA.fridge(300, badge="24 HR", badge_color=WATER), txt("Half-full freezer", size=58)]),
                  at("Half full"))], gap=50),
            (pill("Doors shut", WATER), at("Half full") + 0.5, "pop")], [40], "CDC; FDA"))
        specs.append(("The 40° rule", lambda: [
            (BA.thermometer(300, color=WATER), S(2), "pop"),
            (card("Appliance thermometer", "in the fridge and freezer", GREEN), at("Put an appliance"), "slide"),
            (head("Fridge: 40°F or colder", CREAM, 96, (90, 160, 255)), at("In the fridge"), "pop"),
            (pill("Freezer: 0°F or colder", WATER), at("In the fridge") + 0.6, "pop")],
            [30, 30, 20], "FDA; CDC"))
        specs.append(("Fridge off more than 4 hours?", lambda: [
            (BA.trash(230), S(3), "pop"),
            (card("Toss perishables", "meat, milk, eggs, leftovers", RED), at("Toss perishables"), "slide"),
            (card("Don't taste-test", None, RED, h=140), at("Don't taste-test"), "slide"),
            (head("When in doubt, throw it out", GOLDEN, 84, (255, 140, 0)), at("When in doubt"), "pop")],
            [24, 16, 30], "FoodSafety.gov; CDC; Ready.gov (FEMA)"))

        def jugs():
            j = BA.jug(118)
            grid = Image.new("RGBA", (6 * 118 + 5 * 22, 2 * 118 + 22), (0, 0, 0, 0))
            for i in range(12):
                r, c = divmod(i, 6)
                grid.alpha_composite(j, (c * 140, r * 140))
            return grid
        specs.append(("Water", lambda: [
            (two("1 gallon per person,", "per day", CREAM, 96), S(4), "pop"),
            (card("At least 3 days", "A family of 4: at least 12 gallons", WATER), at("for at least"), "slide"),
            (jugs(), at("A family of"), "pop")], [30, 36], "CDC; American Red Cross; Ready.gov (FEMA)"))
        specs.append(("Medicine that needs the fridge?", lambda: [
            row([(BA.fridge(300), S(5)), (BA.bottle(170), S(5, 0.25))], gap=30),
            (head("Ask your pharmacist now", CREAM, 92), at("Ask your pharmacist"), "pop"),
            (txt("what to do in an outage", "semi", 50, FAINT), at("Ask your pharmacist") + 0.3, "pop")],
            [30, 10], "FDA; Ready.gov (FEMA)"))
        specs.append(("Save this", lambda: [
            (BA.house(280, lit=True), S(6), "pop"),
            (head("Send it to someone who lives alone", CREAM, 84), at("send it to") - 0.1, "pop"),
            (vr.pill("laporteweathernow.com", "xbold", 50, (16, 8, 26), GOLDEN + (255,), padx=38, pady=22),
             at("send it to") + 0.8, "pop")], [30, 40], None))

    scenes = []
    snow = part in (2, 3)
    for k, (lab_text, build_items, gaps, src) in enumerate(specs):
        def make(lab_text=lab_text, build_items=build_items, gaps=gaps, src=src, k=k):
            def p(ctx):
                ctx["bg"] = base()
                ctx["lab"] = label(lab_text)
                ctx["items"] = build_items()
                ctx["ys"], ctx["hs"] = layout(ctx["items"], gaps)

            def d(f, u, t, ctx):
                f.alpha_composite(ctx["bg"])
                if snow:
                    f.alpha_composite(snow_layer(t))
                f.alpha_composite(C.alpha(ctx["lab"], 1.0 if k == 0 else appear(u, 0, 0.3)), (X0, 330))
                draw_items(f, t, ctx["items"], ctx["ys"], ctx["hs"])
                if src:
                    bs.credit_line(f, src)
            return p, d
        p, d = make()
        sc = C.Scene(cuts[k], cuts[k + 1], d, p)
        sc.flicker = 0.0
        scenes.append(sc)
    return scenes, cuts


def calm_music(seconds, root=55):
    """A steady, warm pad (major key, slow), quiet under the narrator. No hits, nothing scary."""
    n = int(seconds * SR)
    out = np.zeros(n, np.float32)
    beat = 60 / 76
    bar = 4 * beat
    prog = [(0, "M"), (7, "M"), (9, "m"), (5, "M")]
    b = 0
    while b * bar < seconds:
        start = b * bar
        semis0, kind = prog[b % 4]
        length = min(bar + 0.6, seconds - start)
        tt = np.arange(int(length * SR)) / SR
        third = 4 if kind == "M" else 3
        pad = np.zeros_like(tt, dtype=np.float32)
        for s in (0, third, 7, 12):
            f = 440.0 * 2 ** ((root + semis0 + s - 69) / 12)
            for det in (-0.0015, 0.0015):
                ph = 2 * np.pi * f * (1 + det) * tt
                pad += (np.sin(ph) + 0.3 * np.sin(2 * ph)).astype(np.float32)
        e = np.ones_like(tt, dtype=np.float32)
        a, r = min(int(0.6 * SR), len(e) // 2), min(int(0.8 * SR), len(e) // 2)
        e[:a] = np.linspace(0, 1, a)
        e[-r:] *= np.linspace(1, 0, r)
        i = int(start * SR)
        j = min(n, i + len(tt))
        out[i:j] += (pad * e * 0.03)[:j - i]
        for k in range(8):                       # a soft, low pulse on the eighths
            ts = start + k * beat / 2
            if ts >= seconds:
                break
            t2 = np.arange(int(0.35 * SR)) / SR
            f = 440.0 * 2 ** ((root + semis0 - 12 - 69) / 12)
            blip = np.sin(2 * np.pi * f * t2) * np.exp(-t2 / 0.12) * np.minimum(1, t2 / 0.01) * 0.05
            i2 = int(ts * SR)
            j2 = min(n, i2 + len(blip))
            out[i2:j2] += blip[:j2 - i2].astype(np.float32)
        b += 1
    fade = int(1.0 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / max(1e-6, float(np.max(np.abs(out)))) * 0.85


def main(part, mode, times=None):
    R = C.Reel("bo%d" % part)
    scenes, cuts = scenes_for(part, R)
    atm = bs.Atmos(tint=(206, 212, 228), fog=0.03, vignette=0.4, grain=6, seed=4)
    film = C.Film(R, scenes, flashes=[], flicker=0.0, atmos=atm)
    name = "bo%d" % part
    if mode == "stills":
        ts = times or [0.05, 1.2] + [c + 1.6 for c in cuts[1:-1]] + [R.dur - 0.4]
        print(film.stills([t for t in ts if t < R.dur], name))
        return
    vid = os.path.join(C.OUT, "_%s_video.mp4" % name)
    film.video(vid, cover_t=1.0)
    ev = [("whoosh", c, 0.35) for c in cuts[1:-1]]
    mix = C.soundtrack(R, calm_music(R.dur + 1), ev, music_gain=0.40, hit_gain=0.35)
    out = os.path.join(C.OUT, OUTFILES[part])
    C.finish(R, vid, mix, out, TITLES[part])
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None)
