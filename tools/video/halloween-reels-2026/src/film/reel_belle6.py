"""Belle Gunness, Part 6: the grave near Chicago and the DNA test (Oct. 25, 2026), in the series' look.

    python3 reel_belle6.py stills|video [times]

Facts: on June 18, 1908, La Porte's Cutler Funeral Home shipped the caskets to Forest Home Cemetery, Forest Park, Ill.,
where they were buried in the lot of Belle's first husband, Mads Sorenson (the hauntings page; Forest Park Review,
Dec. 4, 2007). On Nov. 5, 2007, University of Indianapolis forensic anthropology students (Stephen Nawrocki directing,
Andrea Simmons heading the effort) exhumed the headless skeleton (Forest Park Review; Chicagoist, Feb. 12, 2008) to
compare its DNA with saliva on envelopes Belle mailed to a suitor; "due to its age the sample was not able to be
properly tested" (Wikipedia). On April 26, 2008, Simmons and descendants of the victims placed headstones on victims'
graves unmarked since 1908 (WBEZ, April 28, 2008).
Pictures: viewing the cellar, 1908 (Steve Shook, CC BY 2.0); the farm after the fire (same); the rest is drawn.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import reels_common as C
from reels_common import bs, vr, W, H, SR, T, fitT, glow, paste, scaled, appear, ease, ease_out, dim, BONE, SEPIA, \
    INKC, BLOOD
from reel_belle import label_fn, typed, red_title, credit, dot, scribble, PageCam
import reel_haunts as RH
from reel_frank import to_pil

C.WEIGHT.update({"2008": 4.4, "1908": 4.35, "DNA": 3.0})
GEO = os.path.join(C.ROOT, "dl", "geo")
GEO10 = os.path.join(C.ROOT, "dl", "geo10")
OUTFILE = "belle-gunness-part-6-the-dna-test.mp4"
TEAL = (120, 230, 210)


def build_chi_map():
    """La Porte to Forest Park on old paper: Lake Michigan's southern shore, the state line, county lines."""
    MW, MH = 1400, 2000
    m = bs.aged_paper(MW, MH, seed=19)
    k, lon0, lat0 = 520.0, -87.25, 41.75
    cl = math.cos(math.radians(41.7))

    def P(lon, lat):
        return (MW / 2 + (lon - lon0) * k * cl, MH / 2 - (lat - lat0) * k)

    S = 2

    def rings(geom):
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for ring in poly:
                yield [(P(x, y)[0] * S, P(x, y)[1] * S) for x, y in ring]

    lines = Image.new("RGBA", (MW * S, MH * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lines)
    cj = json.load(open(os.path.join(GEO10, "counties.json")))
    for ft in cj["features"]:
        if ft["properties"].get("STATE") not in ("17", "18", "26"):
            continue
        for r in rings(ft["geometry"]):
            if any(-200 < x < MW * S + 200 and -200 < y < MH * S + 200 for x, y in r[::20]):
                d.line(r + r[:1], fill=INKC + (60,), width=1 * S)
    st = json.load(open(os.path.join(GEO, "ne_50m_admin_1_states_provinces_lakes.geojson")))
    for ft in st["features"]:
        if ft["properties"].get("name") in ("Illinois", "Indiana", "Michigan"):
            for r in rings(ft["geometry"]):
                d.line(r + r[:1], fill=INKC + (170,), width=3 * S)
    water = Image.new("L", (MW * S, MH * S), 0)
    dw = ImageDraw.Draw(water)
    lakes = json.load(open(os.path.join(GEO10, "ne_10m_lakes.geojson")))
    for ft in lakes["features"]:
        if ft["properties"].get("name") == "Lake Michigan":
            for r in rings(ft["geometry"]):
                dw.polygon(r, fill=255)
    lines = lines.resize((MW, MH), Image.LANCZOS)
    water = water.resize((MW, MH), Image.LANCZOS)
    wa = np.asarray(water, np.float32) / 255.0
    hatch = ((np.arange(MH)[:, None] % 9) < 2).astype(np.float32) * 0.5 + 0.5
    tint = Image.new("RGBA", (MW, MH), (96, 84, 66, 0))
    tint.putalpha(Image.fromarray((wa * hatch * 110).astype(np.uint8), "L"))
    paper = Image.new("RGBA", (MW, MH), (0, 0, 0, 0))
    paper.alpha_composite(lines)
    m.alpha_composite(tint)
    edge = water.filter(ImageFilter.FIND_EDGES)
    shore = Image.new("RGBA", (MW, MH), INKC + (0,))
    shore.putalpha(edge.point(lambda v: min(255, v * 3)))
    m.alpha_composite(shore)
    m.alpha_composite(paper)
    for name, lon, lat in (("ILLINOIS", -88.05, 41.35), ("INDIANA", -86.55, 41.3)):
        img = T(name, "fell_sc", 44, INKC + (150,), tracking=8)
        x, y = P(lon, lat)
        m.alpha_composite(img, (int(x - img.width / 2), int(y - img.height / 2)))
    img = T("Lake Michigan", "fell_it", 46, INKC + (150,))
    x, y = P(-87.2, 42.15)
    m.alpha_composite(img, (int(x - img.width / 2), int(y - img.height / 2)))
    return m, P


def helix(w, h, phase, a=1.0, broken=0.0, seed=3):
    """A glowing DNA double helix, vertical. broken 0..1 drops rungs and fades strands."""
    S = 2
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = np.random.default_rng(seed)
    n = 90
    amp = w * 0.34
    for strand in (0, 1):
        pts = []
        for i in range(n + 1):
            y = h * i / n
            x = w / 2 + amp * math.sin(i / n * 4 * math.pi + phase + strand * math.pi)
            pts.append((x * S, y * S))
        for i in range(n):
            if broken and r.random() < broken * 0.6:
                continue
            z = math.cos(i / n * 4 * math.pi + phase + strand * math.pi)
            al = int(255 * a * (0.45 + 0.55 * (z + 1) / 2) * (1 - 0.6 * broken))
            d.line([pts[i], pts[i + 1]], fill=TEAL + (al,), width=int(6 * S))
    for i in range(0, n, 3):
        if broken and r.random() < broken:
            continue
        y = h * i / n
        x1 = w / 2 + amp * math.sin(i / n * 4 * math.pi + phase)
        x2 = w / 2 + amp * math.sin(i / n * 4 * math.pi + phase + math.pi)
        d.line([(x1 * S, y * S), (x2 * S, y * S)], fill=(230, 250, 245, int(170 * a * (1 - broken))), width=int(3 * S))
    img = img.resize((w, h), Image.LANCZOS)
    return glow(img, (40, 190, 170), radius=18, strength=0.7)


def letter_envelope():
    """An old envelope: an address in loose handwriting, a two-cent stamp, a postmark."""
    env = bs.aged_paper(820, 500, seed=31)
    d = ImageDraw.Draw(env)
    rng = np.random.default_rng(8)
    for y, x0, x1 in ((250, 250, 640), (306, 290, 700), (362, 330, 660)):
        scribble(d, x0, x1, y, rng, a=150)
    d.rectangle((660, 40, 770, 170), fill=(170, 70, 60, 255), outline=(110, 40, 30, 255), width=4)
    d.text((683, 70), "2¢", font=C.font("oldst_b", 56), fill=(240, 220, 200, 255))
    for k in range(3):
        d.ellipse((520 - k * 6, 60 - k * 6, 640 + k * 6, 180 + k * 6), outline=INKC + (120 - 30 * k,), width=3)
    d.text((540, 98), "LA PORTE", font=C.font("oldst", 22), fill=INKC + (140,))
    d.text((548, 128), "IND.", font=C.font("oldst", 22), fill=INKC + (140,))
    for k in range(4):
        d.line([(500, 210 + k * 14), (650, 210 + k * 14)], fill=INKC + (90,), width=3)
    return env.rotate(3, resample=Image.BICUBIC, expand=True)


def build(R):
    t_she = R.at("She'd been")
    t_chicago = R.at("near Chicago")
    t_1908 = R.at("1908,")
    t_plot = R.at("in the plot")
    t_res = R.at("Researchers")
    t_dna = R.at("DNA")
    t_env = R.at("an envelope")
    t_but = R.at("But the")
    t_tested = R.at("properly tested.")
    t_ans = R.at("The answer")
    t_buried = R.at("still buried.")
    t_2008 = R.at("In 2008,")
    t_head = R.at("headstones.")
    t_dbl = R.at("Double-tap")
    c1 = (R.end("woman.") + t_she) / 2
    c2 = (R.end("husband.") + t_res) / 2
    c4 = (R.end("still buried.") + t_2008) / 2
    c5 = (R.end("headstones.") + t_dbl) / 2
    shared = {}

    def p_hook(ctx):
        ctx["im"] = bs.photo("belle-farm-15.jpg", "sepia", inset=0.03)

    def d_hook(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c1, z=(1.12, 1.2), f0=(0.5, 0.55), f1=(0.52, 0.6))
        bs.shade(f)
        red_title(f, "THE HEADLESS WOMAN", 104, t, -0.2)
        bs.credit_line(f, credit("belle-farm-15.jpg", "viewing the cellar, 1908"))

    def p_map(ctx):
        ctx["map"], ctx["P"] = build_chi_map()
        ctx["dot"] = dot(13, BLOOD)
        ctx["lp"] = glow(T("LA PORTE", "oldst_b", 40, INKC), (244, 234, 214), radius=10, strength=0.9)
        ctx["fp"] = glow(T("FOREST PARK, ILL.", "oldst_b", 40, INKC), (244, 234, 214), radius=10, strength=0.9)
        ctx["chi"] = glow(T("CHICAGO", "oldst", 34, INKC), (244, 234, 214), radius=10, strength=0.9)

    cam = PageCam([(c1, 1.0, 700, 1000), (c2, 1.08, 690, 990)], ys=820)

    def d_map(f, u, t, ctx):
        to, s = cam.draw(f, ctx["map"], t)
        P = ctx["P"]
        A, B = to(*P(-86.72, 41.61)), to(*P(-87.81, 41.876))
        Cc = to(*P(-87.63, 41.88))
        ctrl = ((A[0] + B[0]) / 2, min(A[1], B[1]) - 120)
        r0, r1 = t_chicago - 0.2, t_1908 + 0.3
        prog = ease((t - r0) / (r1 - r0)) if t >= r0 else 0.0
        if prog > 0:
            S = 2
            lay = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
            dd = ImageDraw.Draw(lay)
            n = 60
            for i in range(n):
                q0, q1 = i / n, (i + 0.55) / n
                if q0 > prog:
                    break
                p0 = ((1 - q0) ** 2 * A[0] + 2 * (1 - q0) * q0 * ctrl[0] + q0 * q0 * B[0],
                      (1 - q0) ** 2 * A[1] + 2 * (1 - q0) * q0 * ctrl[1] + q0 * q0 * B[1])
                q1 = min(q1, prog)
                p1 = ((1 - q1) ** 2 * A[0] + 2 * (1 - q1) * q1 * ctrl[0] + q1 * q1 * B[0],
                      (1 - q1) ** 2 * A[1] + 2 * (1 - q1) * q1 * ctrl[1] + q1 * q1 * B[1])
                dd.line([(p0[0] * S, p0[1] * S), (p1[0] * S, p1[1] * S)], fill=BLOOD + (235,), width=7 * S)
            f.alpha_composite(lay.resize((W, H), Image.LANCZOS))
        paste(f, ctx["dot"], A[0], A[1])
        paste(f, ctx["lp"], A[0], A[1] + 48)
        paste(f, ctx["chi"], Cc[0] + 10, Cc[1] - 50, 0.85)
        if t >= r1:
            paste(f, ctx["dot"], B[0], B[1])
            paste(f, ctx["fp"], B[0] + 40, B[1] + 50)
            k = (t - r1) / 0.6
            if k < 1:
                paste(f, C.ring(16 + 50 * k, 5, BLOOD, 1 - k), B[0], B[1])
        bs.shade(f)
        typed(f, "JUNE 1908", t, c1 + 0.1, 330, size=72, rate=0.05)
        bs.title(f, "FOREST HOME CEMETERY", "bask", 84, BONE, 1205, glow=(0, 0, 0),
                 alpha=appear(t, t_plot - 0.1, 0.25))
        bs.credit_line(f, "Map: Natural Earth, U.S. Census Bureau")

    def p_dna(ctx):
        ctx["bg"] = bs.photo("belle-farm-13.jpg", "sepia", inset=0.05).filter(ImageFilter.GaussianBlur(9))
        ctx["env"] = letter_envelope()
        ctx["lab"] = glow(T("UNIVERSITY OF INDIANAPOLIS", "bold", 34, BONE, tracking=4), (0, 0, 0), radius=14,
                          strength=0.9)
        ctx["stamp"] = bs.stamp([("TOO OLD", 92), ("TO TEST", 100)])

    def d_dna(f, u, t, ctx):
        bs.kenburns(f, ctx["bg"], u, c4 - c2, z=(1.05, 1.1))
        dim(f, 0.55)
        a = appear(t, c2 + 0.05, 0.35)
        paste(f, ctx["env"], W / 2 - 40, 820 + 40 * (1 - a), a)
        if t >= t_dna - 0.2:
            broken = ease((t - t_tested) / 1.2) if t >= t_tested else 0.0
            ka = appear(t, t_dna - 0.2, 0.35) * (1 - 0.75 * broken)
            fl = 1.0 if broken == 0 else (0.6 + 0.4 * math.sin(t * 37))
            paste(f, helix(280, 640, t * 2.2, a=1.0, broken=broken), 850, 850, ka * fl)
        bs.shade(f)
        typed(f, "NOV. 2007", t, c2 + 0.1, 330, size=72, rate=0.05)
        paste(f, ctx["lab"], W / 2, 430, appear(t, t_res + 0.3, 0.3))
        if t >= t_tested - 0.1:
            k = appear(t, t_tested - 0.1, 0.12)
            sh = np.random.default_rng(int(t * 1000)).normal(0, 8, 2) if t - t_tested < 0.2 else (0, 0)
            paste(f, scaled(ctx["stamp"], 2.0 - 1.0 * k), W / 2 + sh[0], 860 + sh[1], min(1.0, k * 1.2))
        bs.title(f, "STILL BURIED", "bask", 96, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_buried - 0.1, 0.25))
        bs.credit_line(f, credit("belle-farm-13.jpg", "the farm after the fire, 1908"))

    def p_stones(ctx):
        sc = RH.TownCemetery(seed=5, close=True, fog_d=0.16, dawn=True)
        shared["stones"] = sc
        ctx["s"] = sc
        ctx["lab"] = glow(T("100 YEARS AFTER THE FIRE", "bold", 34, BONE, tracking=4), (0, 0, 0), radius=14,
                          strength=0.9)

    def d_stones(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u, z=(1.06, 1.0))))
        bs.shade(f)
        typed(f, "APRIL 2008", t, t_2008 - 0.05, 330, size=72, rate=0.05)
        paste(f, ctx["lab"], W / 2, 430, appear(t, t_2008 + 0.5, 0.3))
        bs.title(f, "HEADSTONES, AT LAST", "bask", 90, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_head - 0.6, 0.3))

    def p_end(ctx):
        if "stones" not in shared:
            p_stones({})
        ctx["s"] = shared["stones"]
        ctx["cta"] = C.DoubleTap("TO REMEMBER THEM", "Belle Gunness, Part 6", color1=BONE, glow1=(0, 0, 0))

    def d_end(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u + 5.0, z=(1.0, 1.0))))
        dim(f, 0.25)
        bs.shade(f)
        ctx["cta"].draw(f, u)

    scenes = [C.Scene(0.0, c1, d_hook, p_hook), C.Scene(c1, c2, d_map, p_map), C.Scene(c2, c4, d_dna, p_dna),
              C.Scene(c4, c5, d_stones, p_stones), C.Scene(c5, R.dur + 1, d_end, p_end)]
    film = C.Film(R, scenes, flashes=[(0.35, 0.32)], label=label_fn("BELLE GUNNESS · PART 6", c1))
    ev = [("thunder", 0.33, 0.9), ("whoosh", c1, 0.7), ("type", c1 + 0.1, 0.9), ("pop", t_1908 + 0.3, 0.8),
          ("whoosh", c2, 0.6), ("type", c2 + 0.1, 0.9), ("pop", t_dna - 0.2, 0.6), ("heartbeat", t_env, 0.7),
          ("hit", t_tested - 0.05, 1.0), ("thud", t_buried, 0.7), ("whoosh", c4, 0.6), ("type", t_2008 - 0.05, 0.9),
          ("pop", c5 + 0.12, 0.9), ("pop", c5 + 0.42, 0.9), ("hit", c5 + 0.5, 0.7)]
    return film, ev, "lullaby", "Belle Gunness, Part 6: The DNA Test"


def main(mode, times=None):
    R = C.Reel("belle6")
    film, ev, music, title = build(R)
    if mode == "stills":
        ts = times or [round(R.dur * k / 12, 2) for k in range(12)]
        print(film.stills([t for t in ts if t < R.dur], "belle6"))
        return
    vid = os.path.join(C.OUT, "_belle6_video.mp4")
    film.video(vid, cover_t=0.6)
    mix = C.soundtrack(R, music, ev)
    out = os.path.join(C.OUT, OUTFILE)
    C.finish(R, vid, mix, out, title)
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    main(sys.argv[1], [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None)
