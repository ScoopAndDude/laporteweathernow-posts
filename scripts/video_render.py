#!/usr/bin/env python3
"""Draws the Daily Video from OUTDIR/plan.json (scripts/daily_video.py writes the plan and records the
voice) and saves OUTDIR/laporte-<date>.mp4 (1080x1920, 30 fps, H.264 + AAC 48 kHz, the Reels format)
and OUTDIR/cover.jpg.

Everything on screen is drawn from the plan's numbers: Inter type (video/fonts, SIL Open Font License),
the LPWN logo, weather icons drawn here, and, on wet mornings, NOAA's MRMS radar (the same radar as the
site's /radar page) over a county map from the U.S. Census Bureau. No stock footage, no AI pictures.

fetch_radar(OUTDIR, LAST) is called while planning: it saves the last hour of radar pictures near
La Porte and says whether there's rain or snow on them (the radar scene is left out when there isn't).
"""
import datetime
import io
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.request
import zipfile
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
ASSETS = os.path.join(REPO, "video")
TZ = ZoneInfo("America/Chicago")
UA = "LaPorteWeatherNow/1.0 (+https://laporteweathernow.com)"

W, H, FPS = 1080, 1920, 30
X0, XR = 80, 980                     # content edges (the right side stays clear of the apps' buttons)
CW = XR - X0
EXIT = 0.16                          # each scene fades out this long before the next one
ENTER = 0.32

INK = (250, 250, 250)
SOFT = (208, 208, 214)
FAINT = (146, 146, 156)
AMBER = (255, 138, 0)
GOLD = (255, 180, 0)
BLUE = (92, 170, 255)
ICE = (168, 216, 255)
RED = (240, 84, 64)
TONE = {"warm": GOLD, "cold": ICE, "rain": BLUE, "storm": (255, 176, 64), "alert": (255, 110, 80), "plain": INK}
GLOW = {"warm": (255, 138, 0), "cold": (70, 140, 255), "rain": (50, 120, 255), "storm": (255, 110, 30),
        "alert": (235, 50, 40), "plain": (255, 138, 0)}

FONT_FILES = {"black": "Inter-Black.otf", "xbold": "Inter-ExtraBold.otf", "bold": "Inter-Bold.otf",
              "semi": "Inter-SemiBold.otf", "reg": "Inter-Regular.otf"}
_fonts = {}


def font(weight, size):
    key = (weight, int(size))
    if key not in _fonts:
        try:
            _fonts[key] = ImageFont.truetype(os.path.join(ASSETS, "fonts", FONT_FILES[weight]), int(size))
        except OSError:
            _fonts[key] = ImageFont.truetype("DejaVuSans-Bold.ttf" if weight != "reg" else "DejaVuSans.ttf", int(size))
    return _fonts[key]


# ---------------------------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------------------------
def text_img(text, weight, size, color, tracking=0):
    """One line of text, cropped to the ink."""
    f = font(weight, size)
    asc, desc = f.getmetrics()
    if tracking:
        widths = [f.getlength(ch) for ch in text]
        width = int(sum(widths) + tracking * max(0, len(text) - 1)) + 8
    else:
        width = int(math.ceil(f.getlength(text))) + 8
    img = Image.new("RGBA", (max(width, 1), asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tracking:
        x = 2
        for ch, w in zip(text, widths):
            d.text((x, 2), ch, font=f, fill=color)
            x += w + tracking
    else:
        d.text((2, 2), text, font=f, fill=color)
    box = img.getbbox()
    return img.crop(box) if box else img


def wrap(text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if f.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def para_img(text, weight, size, color, max_w, max_lines=3, align="left", gap=1.17):
    f = font(weight, size)
    lines = wrap(text, f, max_w)
    if len(lines) > max_lines or any(f.getlength(ln) > max_w for ln in lines):
        return None
    lh = int(size * gap)
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (max_w + 8, lh * (len(lines) - 1) + asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        w = f.getlength(ln)
        x = 2 if align == "left" else (max_w - w) / 2 + 2 if align == "center" else max_w - w + 2
        d.text((x, 2 + i * lh), ln, font=f, fill=color)
    box = img.getbbox()
    if not box:
        return img
    return img.crop((0, box[1], img.width, box[3])) if align != "left" else img.crop((box[0], box[1], box[2], box[3]))


def fit_para(text, weight, size, color, max_w, max_lines=2, min_size=34, align="left"):
    s = size
    while s >= min_size:
        im = para_img(text, weight, s, color, max_w, max_lines, align)
        if im is not None:
            return im
        s -= 4
    return para_img(text, weight, min_size, color, max_w, 99, align)


def fit_line(text, weight, size, color, max_w, min_size=40, tracking=0):
    s = size
    while s > min_size and font(weight, s).getlength(text) + tracking * len(text) > max_w:
        s -= 4
    return text_img(text, weight, s, color, tracking)


def glow(img, color, radius=26, strength=0.55):
    """The LPWN look: a soft colored glow behind big type."""
    pad = radius * 2
    big = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    a = img.getchannel("A")
    halo = Image.new("RGBA", big.size, color + (0,))
    mask = Image.new("L", big.size, 0)
    mask.paste(a, (pad, pad))
    mask = mask.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: int(v * strength))
    halo.putalpha(mask)
    big.alpha_composite(halo)
    big.alpha_composite(img, (pad, pad))
    big.info["pad"] = pad
    return big


def rounded(img, radius):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(ImageChops.multiply(out.getchannel("A"), mask))
    return out


def pill(text, weight, size, fg, bg, border=None, icon=None, padx=30, pady=18):
    t = text_img(text, weight, size, fg)
    iw = icon.width + 16 if icon else 0
    h = max(t.height, icon.height if icon else 0) + 2 * pady
    img = Image.new("RGBA", (t.width + iw + 2 * padx, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, img.width - 1, h - 1), radius=h // 2, fill=bg, outline=border, width=3 if border else 0)
    x = padx
    if icon:
        img.alpha_composite(icon, (x, (h - icon.height) // 2))
        x += iw
    img.alpha_composite(t, (x, (h - t.height) // 2))
    return img


# ---------------------------------------------------------------------------------------------
# Weather icons, drawn (4x, then scaled down so the edges are smooth)
# ---------------------------------------------------------------------------------------------
def _cap_line(d, a, b, w, fill):
    d.line([a, b], fill=fill, width=int(w))
    r = w / 2
    for (x, y) in (a, b):
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def _sun(img, cx, cy, r, S):
    d = ImageDraw.Draw(img)
    for i in range(8):
        ang = math.pi / 4 * i
        a = (cx * S + math.cos(ang) * r * 1.42 * S, cy * S + math.sin(ang) * r * 1.42 * S)
        b = (cx * S + math.cos(ang) * r * 1.86 * S, cy * S + math.sin(ang) * r * 1.86 * S)
        _cap_line(d, a, b, r * 0.24 * S, GOLD)
    d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), fill=GOLD)
    d.ellipse(((cx - r * 0.78) * S, (cy - r * 0.78) * S, (cx + r * 0.62) * S, (cy + r * 0.62) * S), fill=(255, 198, 40))


def _moon(img, cx, cy, r, S):
    m = Image.new("L", img.size, 0)
    dm = ImageDraw.Draw(m)
    dm.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), fill=255)
    dm.ellipse(((cx - r + r * 0.62) * S, (cy - r - r * 0.28) * S, (cx + r + r * 0.62) * S, (cy + r - r * 0.28) * S), fill=0)
    col = Image.new("RGBA", img.size, (246, 232, 186, 255))
    col.putalpha(m)
    img.alpha_composite(col)


def _cloud(img, cx, cy, w, S, fill):
    m = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(m)
    for (dx, dy, r) in ((-0.27, 0.05, 0.19), (-0.02, -0.10, 0.27), (0.25, 0.03, 0.20)):
        d.ellipse(((cx + dx * w - r * w) * S, (cy + dy * w - r * w) * S, (cx + dx * w + r * w) * S, (cy + dy * w + r * w) * S), fill=255)
    d.rounded_rectangle(((cx - 0.46 * w) * S, (cy + 0.02 * w) * S, (cx + 0.45 * w) * S, (cy + 0.24 * w) * S), radius=0.11 * w * S, fill=255)
    shade = Image.new("RGBA", img.size, tuple(max(0, c - 34) for c in fill) + (255,))
    shade.putalpha(m)
    img.alpha_composite(shade, (0, int(0.025 * w * S)))
    col = Image.new("RGBA", img.size, fill + (255,))
    col.putalpha(m)
    img.alpha_composite(col)


def _drops(img, xs, y, S, color=BLUE, length=0.11):
    d = ImageDraw.Draw(img)
    for i, x in enumerate(xs):
        yy = y + (0.04 if i % 2 else 0)
        _cap_line(d, (x * S, yy * S), ((x - 0.035) * S, (yy + length) * S), 0.04 * S, color)


def _flake(img, cx, cy, r, S, color=INK, width=0.16):
    d = ImageDraw.Draw(img)
    for k in range(3):
        ang = math.pi / 3 * k + math.pi / 2
        a = (cx * S + math.cos(ang) * r * S, cy * S + math.sin(ang) * r * S)
        b = (cx * S - math.cos(ang) * r * S, cy * S - math.sin(ang) * r * S)
        _cap_line(d, a, b, r * width * S, color)
    if r > 0.12:
        for k in range(6):
            ang = math.pi / 3 * k + math.pi / 2
            px, py = cx + math.cos(ang) * r * 0.6, cy + math.sin(ang) * r * 0.6
            for sgn in (-1, 1):
                ang2 = ang + sgn * math.pi / 4
                _cap_line(d, (px * S, py * S), ((px + math.cos(ang2) * r * 0.32) * S, (py + math.sin(ang2) * r * 0.32) * S), r * width * 0.8 * S, color)


def _bolt(img, S, ox=0.0, oy=0.0, k=1.0):
    pts = [(0.53, 0.52), (0.40, 0.76), (0.51, 0.76), (0.44, 0.96), (0.66, 0.66), (0.54, 0.66), (0.62, 0.52)]
    ImageDraw.Draw(img).polygon([((ox + x * k) * S, (oy + y * k) * S) for x, y in pts], fill=GOLD)


def _bars(img, ys, S, x0=0.16, x1=0.84, color=SOFT):
    d = ImageDraw.Draw(img)
    for i, y in enumerate(ys):
        off = 0.06 if i % 2 else 0
        _cap_line(d, ((x0 + off) * S, y * S), ((x1 - off * 0.5) * S, y * S), 0.05 * S, color)


def _wind(img, S):
    d = ImageDraw.Draw(img)
    for (y, x1, r) in ((0.34, 0.66, 0.09), (0.50, 0.80, 0.11), (0.66, 0.58, 0.08)):
        _cap_line(d, (0.16 * S, y * S), (x1 * S, y * S), 0.05 * S, SOFT)
        d.arc(((x1 - r) * S, (y - 2 * r) * S, (x1 + r) * S, y * S), start=-90 - 180, end=90, fill=SOFT, width=int(0.05 * S))


def _alert(img, S, color=GOLD):
    d = ImageDraw.Draw(img)
    pts = [(0.5 * S, 0.12 * S), (0.92 * S, 0.86 * S), (0.08 * S, 0.86 * S)]
    d.polygon(pts, fill=color)
    d.line(pts + [pts[0]], fill=color, width=int(0.07 * S), joint="curve")
    d.rounded_rectangle((0.455 * S, 0.36 * S, 0.545 * S, 0.64 * S), radius=0.04 * S, fill=(18, 18, 20))
    d.ellipse((0.452 * S, 0.70 * S, 0.548 * S, 0.796 * S), fill=(18, 18, 20))


WHITE_CLOUD, GRAY_CLOUD, DARK_CLOUD = (236, 240, 246), (166, 174, 188), (104, 112, 128)


def icon(kind, size):
    S = size * 3
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    k = kind or "sun"
    if k == "sun":
        _sun(img, 0.5, 0.5, 0.25, S)
    elif k == "moon":
        _moon(img, 0.5, 0.5, 0.30, S)
    elif k in ("sun-small-cloud", "moon-small-cloud"):
        (_sun if k.startswith("sun") else _moon)(img, 0.43, 0.40, 0.22 if k.startswith("sun") else 0.27, S)
        _cloud(img, 0.62, 0.70, 0.54, S, WHITE_CLOUD)
    elif k in ("sun-cloud", "moon-cloud"):
        (_sun if k.startswith("sun") else _moon)(img, 0.36, 0.36, 0.19 if k.startswith("sun") else 0.23, S)
        _cloud(img, 0.56, 0.60, 0.74, S, WHITE_CLOUD)
    elif k == "cloud":
        _cloud(img, 0.40, 0.42, 0.56, S, GRAY_CLOUD)
        _cloud(img, 0.56, 0.60, 0.80, S, WHITE_CLOUD)
    elif k in ("sun-rain", "moon-rain"):
        (_sun if k.startswith("sun") else _moon)(img, 0.33, 0.30, 0.17 if k.startswith("sun") else 0.21, S)
        _cloud(img, 0.55, 0.48, 0.74, S, WHITE_CLOUD)
        _drops(img, [0.42, 0.57, 0.72], 0.72, S)
    elif k == "rain":
        _cloud(img, 0.50, 0.40, 0.84, S, GRAY_CLOUD)
        _drops(img, [0.33, 0.47, 0.61, 0.75], 0.66, S, length=0.14)
    elif k == "storm":
        _cloud(img, 0.50, 0.38, 0.84, S, DARK_CLOUD)
        _bolt(img, S, ox=-0.02, oy=0.0, k=0.95)
        _drops(img, [0.30, 0.78], 0.66, S)
    elif k == "snow":
        _cloud(img, 0.50, 0.40, 0.84, S, GRAY_CLOUD)
        for (x, y) in ((0.34, 0.74), (0.52, 0.82), (0.70, 0.74)):
            _flake(img, x, y, 0.07, S)
    elif k == "mix":
        _cloud(img, 0.50, 0.40, 0.84, S, GRAY_CLOUD)
        _drops(img, [0.36, 0.64], 0.66, S)
        for (x, y) in ((0.50, 0.80), (0.78, 0.76)):
            _flake(img, x, y, 0.06, S)
    elif k == "fog":
        _cloud(img, 0.50, 0.34, 0.70, S, GRAY_CLOUD)
        _bars(img, [0.62, 0.73, 0.84], S)
    elif k == "wind":
        _wind(img, S)
    elif k == "frost":
        _flake(img, 0.5, 0.5, 0.36, S, ICE, width=0.10)
        _flake(img, 0.82, 0.22, 0.06, S, ICE)
        _flake(img, 0.18, 0.80, 0.05, S, ICE)
    elif k == "alert":
        _alert(img, S)
    elif k == "drop":
        d = ImageDraw.Draw(img)
        d.ellipse((0.24 * S, 0.40 * S, 0.76 * S, 0.92 * S), fill=BLUE)
        d.polygon([(0.5 * S, 0.06 * S), (0.27 * S, 0.56 * S), (0.73 * S, 0.56 * S)], fill=BLUE)
    else:
        _sun(img, 0.5, 0.5, 0.25, S)
    return img.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------------------------
# The radar (NOAA MRMS, the same service as laporteweathernow.com/radar)
# ---------------------------------------------------------------------------------------------
BOX = (-87.55, 41.00, -85.90, 42.23)            # west, south, east, north: La Porte County and around it
MAP = 920
WMS = "https://opengeo.ncep.noaa.gov/geoserver/conus/conus_bref_qcd/ows"
CENSUS_ZIP = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"
BASEMAP_VERSION = 2
CITIES = [  # name, lat, lon, label side
    ("La Porte", 41.6106, -86.7225, "e"), ("Michigan City", 41.7075, -86.8950, "w"), ("Valparaiso", 41.4731, -87.0611, "w"),
    ("South Bend", 41.6764, -86.2520, "e"), ("Gary", 41.5934, -87.3464, "s"), ("Knox", 41.2959, -86.6250, "e"),
    ("Plymouth", 41.3436, -86.3097, "e"), ("Benton Harbor", 42.1167, -86.4542, "e"), ("Niles", 41.8297, -86.2542, "e"),
]


def http_get(url, timeout=60, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except Exception as e:
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"{url[:120]} -> {last}")


def xy(lon, lat):
    w, s, e, n = BOX
    return ((lon - w) / (e - w) * MAP, (n - lat) / (n - s) * MAP)


def census_counties():
    """Detailed county outlines (U.S. Census Bureau cartographic boundaries, clipped to the shore)."""
    import shapefile  # pyshp
    raw, _ = http_get(CENSUS_ZIP, timeout=120)
    z = zipfile.ZipFile(io.BytesIO(raw))
    base = "cb_2023_us_county_500k"
    sf = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), shx=io.BytesIO(z.read(base + ".shx")),
                          dbf=io.BytesIO(z.read(base + ".dbf")))
    fields = [f[0] for f in sf.fields[1:]]
    w, s, e, n = BOX
    out = []
    for sr in sf.iterShapeRecords():
        x0, y0, x1, y1 = sr.shape.bbox
        if x1 < w - 0.05 or x0 > e + 0.05 or y1 < s - 0.05 or y0 > n + 0.05:
            continue
        rec = dict(zip(fields, sr.record))
        pts, parts = sr.shape.points, list(sr.shape.parts) + [len(sr.shape.points)]
        polys = [pts[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
        out.append({"state": rec.get("STATEFP"), "name": rec.get("NAME"), "polygons": polys})
    if len(out) < 15:
        raise RuntimeError(f"only {len(out)} counties")
    return out, "U.S. Census Bureau (cb_2023_us_county_500k)"


def fallback_counties():
    with open(os.path.join(ASSETS, "basemap-fallback.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc["counties"], "U.S. Census Bureau (2010, simplified)"


def draw_basemap(counties):
    S = 2
    under = Image.new("RGBA", (MAP * S, MAP * S), (13, 33, 54, 255))
    d = ImageDraw.Draw(under)
    lp = []
    for c in counties:
        for poly in c["polygons"]:
            pts = [(x * S, y * S) for x, y in (xy(lon, lat) for lon, lat in poly)]
            if len(pts) > 2:
                d.polygon(pts, fill=(30, 30, 35, 255))
    for c in counties:
        for poly in c["polygons"]:
            pts = [(x * S, y * S) for x, y in (xy(lon, lat) for lon, lat in poly)]
            if len(pts) > 2:
                d.line(pts + [pts[0]], fill=(70, 70, 82, 255), width=2 * S // 2 + 1)
            if c["name"] in ("LaPorte", "La Porte") and str(c["state"]) in ("18", 18):
                lp.append(pts)
    over = Image.new("RGBA", under.size, (0, 0, 0, 0))
    do = ImageDraw.Draw(over)
    for pts in lp:
        do.line(pts + [pts[0]], fill=AMBER + (255,), width=5 * S, joint="curve")
    f = font("semi", 26 * S)
    lake = text_img("Lake Michigan", "semi", 30 * S, (92, 150, 205, 255))
    lx, ly = xy(-87.22, 42.02)
    under.alpha_composite(lake, (int(lx * S - lake.width / 2), int(ly * S)))
    for name, lat, lon, side in CITIES:
        x, y = xy(lon, lat)
        x, y = x * S, y * S
        home = name == "La Porte"
        r = (9 if home else 6) * S
        do.ellipse((x - r - 3 * S, y - r - 3 * S, x + r + 3 * S, y + r + 3 * S), fill=(10, 10, 12, 255))
        do.ellipse((x - r, y - r, x + r, y + r), fill=(GOLD if home else INK) + (255,))
        label = text_img(name, "bold" if home else "semi", (30 if home else 25) * S, (GOLD if home else INK) + (255,))
        halo = glow(label, (0, 0, 0), radius=6 * S, strength=0.95)
        pad = halo.info["pad"]
        gapx = 14 * S
        if side == "e":
            pos = (x + gapx - pad, y - label.height / 2 - pad)
        elif side == "w":
            pos = (x - gapx - label.width - pad, y - label.height / 2 - pad)
        else:
            pos = (x - label.width / 2 - pad, y + 12 * S - pad)
        over.alpha_composite(halo, (int(pos[0]), int(pos[1])))
    del f
    return under.resize((MAP, MAP), Image.LANCZOS), over.resize((MAP, MAP), Image.LANCZOS)


def basemap(outdir, last_dir):
    """The map under the radar, kept on the video branch once it's drawn."""
    meta_last = os.path.join(last_dir, "basemap.json") if last_dir else None
    try:
        meta = json.load(open(meta_last, encoding="utf-8")) if meta_last and os.path.exists(meta_last) else {}
    except Exception:
        meta = {}
    if meta.get("version") == BASEMAP_VERSION and meta.get("detailed"):
        under = Image.open(os.path.join(last_dir, "basemap-under.png")).convert("RGBA")
        over = Image.open(os.path.join(last_dir, "basemap-over.png")).convert("RGBA")
        source = meta.get("source")
        detailed = True
    else:
        try:
            counties, source = census_counties()
            detailed = True
        except Exception as e:
            print(f"Detailed county map not available ({str(e)[:160]}); using the simple one.", file=sys.stderr)
            counties, source = fallback_counties()
            detailed = False
        under, over = draw_basemap(counties)
    under.save(os.path.join(outdir, "basemap-under.png"))
    over.save(os.path.join(outdir, "basemap-over.png"))
    with open(os.path.join(outdir, "basemap.json"), "w", encoding="utf-8") as fh:
        json.dump({"version": BASEMAP_VERSION, "detailed": detailed, "source": source, "box": BOX}, fh)
    return under, over, source


def parse_iso(s):
    return datetime.datetime.fromisoformat(s.strip().replace("Z", "+00:00"))


def radar_times():
    raw, _ = http_get(f"{WMS}?service=WMS&version=1.3.0&request=GetCapabilities&t={int(time.time() // 120)}")
    caps = raw.decode("utf-8", "replace")
    m = re.search(r'<Dimension([^>]*name="time"[^>]*)>([^<]*)</Dimension>', caps)
    if not m:
        raise RuntimeError("the radar service didn't list its times")
    attrs, body = m.group(1), m.group(2).strip()
    dm = re.search(r'default="([^"]+)"', attrs)
    times = []
    if "/" in body and "," not in body:
        a, b, step = body.split("/")
        mins = re.fullmatch(r"PT(\d+)M", step)
        start, end = parse_iso(a), parse_iso(b)
        k = int(mins.group(1)) if mins else 2
        t = end
        while t >= start and len(times) < 60:
            times.append(t)
            t -= datetime.timedelta(minutes=k)
    else:
        times = [parse_iso(x) for x in body.split(",") if x.strip()]
    newest = parse_iso(dm.group(1)) if dm else max(times)
    times = sorted(t for t in times if t <= newest)
    return newest, times


def fetch_radar(outdir, last_dir=None, force=False):
    """Saves the last hour of radar pictures. True when there's rain or snow on them (or force=True,
    for testing the radar scene on a dry day)."""
    newest, times = radar_times()
    now = datetime.datetime.now(datetime.timezone.utc)
    if now - newest > datetime.timedelta(minutes=30):
        print(f"The radar's newest picture is {int((now - newest).total_seconds() // 60)} minutes old; leaving radar out.")
        return False
    picks = []
    for back in (50, 40, 30, 20, 10, 0):
        target = newest - datetime.timedelta(minutes=back)
        best = min(times, key=lambda t: abs((t - target).total_seconds())) if times else newest
        if abs((best - target).total_seconds()) <= 300 and best not in picks:
            picks.append(best)
    if newest not in picks:
        picks.append(newest)
    rdir = os.path.join(outdir, "radar")
    os.makedirs(rdir, exist_ok=True)
    w, s, e, n = BOX
    frames = []
    for t in picks:
        iso = t.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        url = (f"{WMS}?service=WMS&version=1.1.1&request=GetMap&layers=conus_bref_qcd&styles=&format=image/png"
               f"&transparent=true&srs=EPSG:4326&bbox={w},{s},{e},{n}&width={MAP}&height={MAP}&time={iso}")
        try:
            raw, ctype = http_get(url, timeout=40, tries=2)
            if "image" not in ctype:
                continue
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception as ex:
            print(f"Radar picture {iso} didn't come back ({str(ex)[:120]}).", file=sys.stderr)
            continue
        name = f"frame-{len(frames):02d}.png"
        img.save(os.path.join(rdir, name))
        frames.append({"file": name, "time": t.isoformat()})
    if not frames:
        raise RuntimeError("no radar pictures came back")
    last = Image.open(os.path.join(rdir, frames[-1]["file"])).getchannel("A")
    hist = last.histogram()
    wet = sum(hist[16:]) / float(MAP * MAP)
    when = parse_iso(frames[-1]["time"]).astimezone(TZ)
    meta = {"frames": frames, "newest": frames[-1]["time"], "clock": clock_words(when), "coverage": round(wet, 4)}
    with open(os.path.join(rdir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    print(f"Radar: {len(frames)} pictures, newest {meta['clock']}, {wet:.1%} of the map has rain or snow.")
    if wet < 0.004 and not force:
        return False
    basemap(outdir, last_dir)
    return True


def clock_words(dt_local):
    h, m = dt_local.hour, dt_local.minute
    return f"{h % 12 or 12}:{m:02d} {'a.m.' if h < 12 else 'p.m.'}"


# ---------------------------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------------------------
class Layer:
    def __init__(self, img, x, y, delay=0.0, fixed=False, zoom=0.0, frames=None, frame_every=0.5, rise=34):
        self.img, self.x, self.y = img, int(x), int(y)
        self.delay, self.fixed, self.zoom, self.rise = delay, fixed, zoom, rise
        self.frames, self.frame_every = frames, frame_every


def centered(img):
    return (W - img.width) // 2


def deg(t):
    return f"{int(t)}°" if t is not None else "--"


def label_img(text, color=AMBER):
    return text_img(text.upper(), "bold", 34, color, tracking=3)


def footer_layer():
    t = text_img("Source: National Weather Service", "semi", 28, FAINT)
    return Layer(t, X0, 1470, fixed=True)


def stack_center(items, top=330, bottom=1440, gap=36):
    """Center a column of (img, gap_after) between top and bottom; returns y positions."""
    total = sum(img.height for img, _ in items) + sum(g for _, g in items[:-1])
    y = top + max(0, (bottom - top - total) // 2)
    ys = []
    for img, g in items:
        ys.append(y)
        y += img.height + g
    return ys


def hook_scene(s, plan):
    tone = s.get("tone") or "plain"
    color = TONE.get(tone, INK)
    label = label_img(s.get("label") or "La Porte")
    ic = icon(s.get("icon"), 360)
    big_text = s.get("big") or ""
    big = fit_line(big_text, "black", 300, color, CW, min_size=150)
    if big.width > CW or (" " in big_text and font("black", 300).getlength(big_text) > CW * 1.25):
        alt = fit_para(big_text, "black", 200, color, CW, max_lines=2, min_size=110, align="center")
        if alt is not None:
            big = alt
    bigg = glow(big, GLOW.get(tone, AMBER), radius=30, strength=0.5)
    pad = bigg.info["pad"]
    small = fit_para(s.get("small") or "", "bold", 72, INK, CW, max_lines=1, min_size=56, align="center")
    if small is None or small.width > CW + 8 or font("bold", 56).getlength(s.get("small") or "") > CW:
        small = fit_para(s.get("small") or "", "bold", 72, INK, CW, max_lines=2, min_size=44, align="center")
    items = [(label, 56), (ic, 40), (big, 44), (small, 30)]
    more = None
    if s.get("more"):
        more = fit_para("Also in effect: " + ", ".join(s["more"]), "semi", 40, SOFT, CW, max_lines=2, min_size=30, align="center")
        items.append((more, 0))
    ys = stack_center(items, top=300, bottom=1440)
    layers = [Layer(label, centered(label), ys[0], fixed=True),
              Layer(ic, centered(ic), ys[1], fixed=True, zoom=0.035),
              Layer(bigg, centered(big) - pad, ys[2] - pad, fixed=True, zoom=0.03),
              Layer(small, centered(small), ys[3], fixed=True)]
    if more is not None:
        layers.append(Layer(more, centered(more), ys[4], fixed=True))
    return layers


def hours_strip(hours, width=CW + 20, height=270):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, width - 1, height - 1), radius=30, fill=(255, 255, 255, 16))
    n = len(hours)
    colw = width / n
    base, maxh = height - 28, 92
    for i, h in enumerate(hours):
        cx = colw * (i + 0.5)
        t = text_img(h["label"], "semi", 27, FAINT)
        img.alpha_composite(t, (int(cx - t.width / 2), 26))
        temp = text_img(deg(h.get("temp")), "bold", 44, INK)
        img.alpha_composite(temp, (int(cx - temp.width / 2), 70))
        pop = int(h.get("pop") or 0)
        bh = max(6, maxh * pop / 100)
        col = BLUE if pop >= 20 else (78, 78, 90)
        d.rounded_rectangle((cx - 20, base - bh, cx + 20, base), radius=8, fill=col + (255,))
        if pop >= 20:
            p = text_img(f"{pop}%", "bold", 26, BLUE)
            img.alpha_composite(p, (int(cx - p.width / 2), int(base - bh - p.height - 10)))
    return img


def period_scene(s, plan):
    title = s["title"] + (f" · {s['date'].upper()}" if s["title"] == "TODAY" else "")
    label = label_img(title)
    ic = icon(s.get("icon"), 330)
    temp = fit_line(deg(s.get("temp")), "black", 250, INK, 540, min_size=150)
    tl = text_img(s.get("tempLabel", ""), "bold", 34, FAINT, tracking=4)
    text = fit_para(s.get("text") or "", "bold", 68, INK, CW, max_lines=2, min_size=46)
    layers = [Layer(label, X0, 330, delay=0.0), Layer(ic, X0 - 14, 400, delay=0.05),
              Layer(temp, XR - temp.width, 420, delay=0.10), Layer(tl, XR - tl.width, 420 + temp.height + 22, delay=0.14)]
    y = 790
    layers.append(Layer(text, X0, y, delay=0.18))
    y += text.height + 40
    r = s.get("rain")
    if r:
        words = f"{r['pct']}% chance of {r['what']}" + (f" · {r['window']}" if r.get("window") else "")
        p = pill(words, "bold", 40, INK, (20, 50, 96, 255), border=BLUE, icon=icon("drop", 40))
        if p.width > CW + 20:
            p = pill(words, "bold", 32, INK, (20, 50, 96, 255), border=BLUE, icon=icon("drop", 34))
        layers.append(Layer(p, X0, y, delay=0.26))
        y += p.height + 22
    if s.get("note"):
        p = pill(s["note"], "bold", 40, GOLD, (58, 38, 6, 255), border=AMBER)
        layers.append(Layer(p, X0, y, delay=0.30))
        y += p.height + 22
    if s.get("hours"):
        strip = hours_strip(s["hours"])
        sy = max(y + 30, 1090)
        if sy + strip.height <= 1450:
            layers.append(Layer(strip, X0 - 10, sy, delay=0.36))
    elif s.get("sun"):
        row = sun_row(s["sun"])
        sy = max(y + 30, 1150)
        if sy + row.height <= 1450:
            layers.append(Layer(row, X0 - 10, sy, delay=0.36))
    layers.append(footer_layer())
    return layers


def sun_row(sun, width=CW + 20, height=170):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, width - 1, height - 1), radius=30, fill=(255, 255, 255, 16))
    for i, (word, when) in enumerate((("SUNSET", sun.get("set")), ("SUNRISE", sun.get("rise")))):
        x0 = i * width // 2
        ic = icon("sun", 84)
        lab = text_img(word, "bold", 28, FAINT, tracking=3)
        tm = text_img(when or "", "bold", 54, INK)
        block_w = ic.width + 22 + max(lab.width, tm.width)
        bx = x0 + (width // 2 - block_w) // 2
        img.alpha_composite(ic, (bx, (height - ic.height) // 2))
        ty = (height - (lab.height + 14 + tm.height)) // 2
        img.alpha_composite(lab, (bx + ic.width + 22, ty))
        img.alpha_composite(tm, (bx + ic.width + 22, ty + lab.height + 14))
    return img


def radar_scene(s, plan, outdir):
    rdir = os.path.join(outdir, "radar")
    meta = json.load(open(os.path.join(rdir, "meta.json"), encoding="utf-8"))
    under = Image.open(os.path.join(outdir, "basemap-under.png")).convert("RGBA")
    over = Image.open(os.path.join(outdir, "basemap-over.png")).convert("RGBA")
    frames = []
    for f in meta["frames"]:
        img = under.copy()
        rad = Image.open(os.path.join(rdir, f["file"])).convert("RGBA")
        a = rad.getchannel("A").point(lambda v: int(v * 0.9))
        rad.putalpha(a)
        img.alpha_composite(rad)
        img.alpha_composite(over)
        t = parse_iso(f["time"]).astimezone(TZ)
        stamp = pill(clock_words(t), "bold", 30, INK, (0, 0, 0, 190))
        img.alpha_composite(stamp, (MAP - stamp.width - 18, MAP - stamp.height - 18))
        card = rounded(img, 30)
        ImageDraw.Draw(card).rounded_rectangle((0, 0, MAP - 1, MAP - 1), radius=30, outline=(72, 72, 84, 255), width=3)
        frames.append(card)
    # hold the newest picture a little longer
    frames = frames + [frames[-1]] * 2
    label = label_img(f"Radar · {meta['clock']}")
    legend = Image.new("RGBA", (CW, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(legend)
    stops = [(0.0, (4, 233, 231)), (0.2, (1, 159, 244)), (0.35, (2, 253, 2)), (0.5, (0, 187, 0)), (0.62, (253, 248, 2)),
             (0.74, (253, 149, 0)), (0.86, (253, 0, 0)), (1.0, (248, 0, 253))]
    bw, bx = 360, 0
    for i in range(bw):
        u = i / (bw - 1)
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if a <= u <= b:
                k = (u - a) / (b - a)
                col = tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(3))
                d.line([(bx + i, 10), (bx + i, 30)], fill=col + (255,))
                break
    light = text_img("Light", "semi", 24, FAINT)
    heavy = text_img("Heavy", "semi", 24, FAINT)
    legend.alpha_composite(light, (0, 40))
    legend.alpha_composite(heavy, (bw - heavy.width, 40))
    credit = text_img("Radar: NOAA/NWS MRMS", "semi", 26, FAINT)
    legend.alpha_composite(credit, (CW - credit.width, 14))
    every = max(0.3, min(0.6, (s["duration"] - 0.6) / max(1, len(frames))))
    return [Layer(label, X0, 330), Layer(frames[-1], X0, 400, delay=0.06, frames=frames, frame_every=every),
            Layer(legend, X0, 400 + MAP + 24, delay=0.12), footer_layer()]


def days_scene(s, plan):
    label = label_img(s["title"])
    days = s["days"]
    n = len(days)
    gap = 20
    cw = int((CW + 20 - gap * (n - 1)) / n)
    contents = []
    for x in days:
        parts = [(text_img(x["name"], "black", 58, GOLD if x.get("star") else INK), 26),
                 (icon(x["icon"], min(210, cw - 40)), 18),
                 (text_img(deg(x["hi"]), "black", 104, INK), 20)]
        if x.get("lo") is not None:
            parts.append((text_img(f"Low {deg(x['lo'])}", "semi", 38, FAINT), 24))
        if x.get("pop"):
            parts.append((pill(f"{x['pop']}%", "bold", 34, INK, (20, 50, 96, 255), border=BLUE, icon=icon("drop", 32),
                               padx=20, pady=12), 22))
        txt = fit_para(x.get("text") or "", "semi", 33, SOFT, cw - 36, max_lines=3, min_size=26, align="center")
        if txt is not None:
            parts.append((txt, 0))
        contents.append(parts)
    ch = 40 + max(sum(img.height + g for img, g in parts) for parts in contents) + 40
    layers = [Layer(label, X0, 330)]
    for i, (x, parts) in enumerate(zip(days, contents)):
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=30, fill=(255, 255, 255, 18),
                                               outline=AMBER + (255,) if x.get("star") else None, width=4 if x.get("star") else 0)
        yy = 40
        for img, g in parts:
            card.alpha_composite(img, ((cw - img.width) // 2, yy))
            yy += img.height + g
        layers.append(Layer(card, X0 - 10 + i * (cw + gap), 410, delay=0.08 + 0.08 * i))
    layers.append(footer_layer())
    return layers


def end_scene(s, plan):
    logo = rounded(Image.open(os.path.join(ASSETS, "logo-512.png")).convert("RGBA").resize((320, 320), Image.LANCZOS), 48)
    a = text_img("LA PORTE", "black", 118, INK)
    b = text_img("WEATHER NOW", "black", 118, GOLD)
    b = fit_line("WEATHER NOW", "black", 118, GOLD, CW)
    c = text_img("Free forecast every morning", "semi", 52, SOFT)
    url = pill("laporteweathernow.com", "xbold", 54, (10, 10, 12), GOLD + (255,), padx=40, pady=24)
    tag = text_img("No hype. Just the forecast.", "bold", 40, FAINT)
    src = text_img("Source: National Weather Service", "semi", 28, FAINT)
    items = [(logo, 50), (a, 18), (b, 50), (c, 44), (url, 48), (tag, 30), (src, 0)]
    ys = stack_center(items, top=300, bottom=1460)
    return [Layer(img, centered(img), y, delay=0.05 * i) for i, ((img, _), y) in enumerate(zip(items, ys))]


# ---------------------------------------------------------------------------------------------
# Frames
# ---------------------------------------------------------------------------------------------
def background(tone):
    import numpy as np
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    top, bottom = np.array([16, 16, 19], np.float32), np.array([5, 5, 7], np.float32)
    k = (yy / H)[..., None]
    img = top * (1 - k) + bottom * k
    g = np.array(GLOW.get(tone, AMBER), np.float32)
    dist = np.sqrt((xx - W * 0.5) ** 2 + ((yy - H * 0.36) * 0.9) ** 2) / 820.0
    glow_k = np.clip(1 - dist, 0, 1) ** 2 * 0.22
    img = img * (1 - glow_k[..., None]) + g * glow_k[..., None]
    grain = np.random.default_rng(7).normal(0, 2.2, (H, W, 1)).astype(np.float32)   # fine grain, no color banding
    img = img + grain
    rgba = np.dstack([np.clip(img, 0, 255).astype(np.uint8), np.full((H, W), 255, np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def brand_row():
    img = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
    mark = Image.open(os.path.join(ASSETS, "logo-mark.png")).convert("RGBA")
    mark = rounded(mark.resize((int(mark.width * 60 / mark.height), 60), Image.LANCZOS), 10)
    img.alpha_composite(mark, (X0, 30))
    t = text_img("LA PORTE WEATHER NOW", "xbold", 30, INK, tracking=2)
    img.alpha_composite(t, (X0 + mark.width + 22, 30 + (60 - t.height) // 2))
    return img


def ease(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def with_alpha(img, a):
    if a >= 0.999:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


def progress(frame, scenes, t, total):
    bar = Image.new("RGBA", (W, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(bar)
    n = len(scenes)
    gap = 8
    segw = (CW + 20 - gap * (n - 1)) / n
    for i, sc in enumerate(scenes):
        x = X0 - 10 + i * (segw + gap)
        d.rounded_rectangle((x, 5, x + segw, 11), radius=3, fill=(255, 255, 255, 56))
        u = (t - sc["start"]) / sc["dur"]
        if u > 0:
            d.rounded_rectangle((x, 5, x + segw * min(1.0, u), 11), radius=3,
                                fill=(255, 255, 255, 220) if u >= 1 else GOLD + (255,))
    frame.alpha_composite(bar, (0, 163))


def build(plan, outdir):
    tone = plan["scenes"][0].get("tone") or "plain"
    scenes = []
    for s in plan["scenes"]:
        if s["kind"] == "hook":
            layers = hook_scene(s, plan)
        elif s["kind"] == "period":
            layers = period_scene(s, plan)
        elif s["kind"] == "radar":
            layers = radar_scene(s, plan, outdir)
        elif s["kind"] == "days":
            layers = days_scene(s, plan)
        else:
            layers = end_scene(s, plan)
        scenes.append({"id": s["id"], "kind": s["kind"], "start": s["start"], "dur": s["duration"], "layers": layers})
    base = background(tone)
    base.alpha_composite(brand_row(), (0, 175))
    return scenes, base


def frame_at(t, scenes, base, cache):
    idx = 0
    for i, sc in enumerate(scenes):
        if t >= sc["start"]:
            idx = i
    sc = scenes[idx]
    u = t - sc["start"]
    last = idx == len(scenes) - 1
    exit_a = 1.0 if last else max(0.0, min(1.0, (sc["start"] + sc["dur"] - t) / EXIT))
    settled = exit_a >= 0.999 and all(L.fixed or u - L.delay >= ENTER for L in sc["layers"])
    key = sc["id"]
    if settled and key in cache:
        frame = cache[key].copy()
    else:
        frame = base.copy()
        for L in sc["layers"]:
            if L.frames or L.zoom:
                continue
            a = 1.0 if L.fixed else ease((u - L.delay) / ENTER)
            if a <= 0:
                continue
            dy = 0 if L.fixed else int(L.rise * (1 - a))
            frame.alpha_composite(with_alpha(L.img, a * exit_a), (L.x, L.y + dy))
        if settled:
            cache[key] = frame.copy()
    for L in sc["layers"]:
        if not (L.frames or L.zoom):
            continue
        a = (1.0 if L.fixed else ease((u - L.delay) / ENTER)) * exit_a
        if a <= 0:
            continue
        img = L.img
        x, y = L.x, L.y
        if L.frames:
            k = min(len(L.frames) - 1, int(max(0.0, u - L.delay) / L.frame_every))
            img = L.frames[k]
        if L.zoom:
            z = 1 + L.zoom * min(1.0, u / max(0.1, sc["dur"]))
            nw, nh = int(img.width * z), int(img.height * z)
            img = img.resize((nw, nh), Image.BILINEAR)
            x -= (nw - L.img.width) // 2
            y -= (nh - L.img.height) // 2
        dy = 0 if L.fixed else int(L.rise * (1 - min(1.0, a / max(exit_a, 1e-6))))
        frame.alpha_composite(with_alpha(img, a), (x, y + dy))
    return frame


def audio_track(plan, outdir, total):
    import numpy as np
    import soundfile as sf
    rate = 24000
    track = np.zeros(int((total + 0.5) * rate), dtype=np.float32)
    for s in plan["scenes"]:
        if not s.get("voiceFile"):
            continue
        a, r = sf.read(os.path.join(outdir, s["voiceFile"]), dtype="float32")
        if a.ndim > 1:
            a = a.mean(axis=1)
        if r != rate:
            raise RuntimeError(f"voice at {r} Hz, expected {rate}")
        i = int(s["voiceAt"] * rate)
        track[i:i + len(a)] += a[:max(0, len(track) - i)]
    path = os.path.join(outdir, "track.wav")
    sf.write(path, track, rate)
    return path


def render(outdir):
    with open(os.path.join(outdir, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    scenes, base = build(plan, outdir)
    total = plan["seconds"]
    n = int(math.ceil(total * FPS))
    track = audio_track(plan, outdir, total)
    name = f"laporte-{plan['date']}.mp4"
    out = os.path.join(outdir, name)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", track,
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-g", str(FPS * 2), "-keyint_min", str(FPS * 2), "-sc_threshold", "0", "-r", str(FPS),
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-ar", "48000", "-ac", "2",
           "-c:a", "aac", "-b:a", "160k", "-t", f"{n / FPS:.3f}", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cache = {}
    cover_at = min(1.0, scenes[0]["dur"] * 0.5)
    t0 = time.time()
    for i in range(n):
        t = i / FPS
        frame = frame_at(t, scenes, base, cache)
        progress(frame, scenes, t, total)
        if abs(t - cover_at) < 0.5 / FPS:
            frame.convert("RGB").save(os.path.join(outdir, "cover.jpg"), quality=90)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg couldn't make the video")
    plan["video"] = name
    plan["cover"] = "cover.jpg"
    plan["bytes"] = os.path.getsize(out)
    plan["rendered"] = datetime.datetime.now(TZ).isoformat(timespec="seconds")
    with open(os.path.join(outdir, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
    # video.json: what this morning's video says and (after scripts/video_post.py) where it was posted.
    record = {
        "about": "The newest Daily Video for La Porte Weather Now (scripts/daily_video.py). Official NWS weather, "
                 "read by an open-source voice (Kokoro-82M). Replaced every morning; only the newest is kept.",
        "date": plan["date"], "planned": plan["planned"], "made": plan["rendered"], "mode": plan.get("mode"),
        "video": name, "cover": "cover.jpg", "seconds": total, "megabytes": round(plan["bytes"] / 1e6, 1),
        "voice": plan.get("voice"), "hook": plan.get("hook"), "alerts": plan.get("alerts"),
        "forecastUpdated": plan.get("forecastUpdated"), "normalsStation": plan.get("normalsStation"),
        "words": [s.get("say") for s in plan["scenes"]], "caption": plan.get("caption"),
        "posted": {}, "errors": [],
    }
    with open(os.path.join(outdir, "video.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2)
    print(f"Made {name}: {total:.1f} seconds, {n} frames, {plan['bytes'] / 1e6:.1f} MB in {time.time() - t0:.0f} s.")
    return 0


def stills(outdir, times=None):
    """Save a few frames as PNGs (for checking the look without making the video)."""
    with open(os.path.join(outdir, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    scenes, base = build(plan, outdir)
    cache = {}
    out = []
    for sc in scenes:
        t = sc["start"] + min(sc["dur"] - EXIT - 0.05, 1.2)
        f = frame_at(t, scenes, base, cache)
        progress(f, scenes, t, plan["seconds"])
        p = os.path.join(outdir, f"still-{sc['id']}.png")
        f.convert("RGB").save(p)
        out.append(p)
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "stills":
        print("\n".join(stills(sys.argv[2])))
    elif len(sys.argv) >= 3 and sys.argv[1] == "render":
        sys.exit(render(sys.argv[2]))
    else:
        print(__doc__)
