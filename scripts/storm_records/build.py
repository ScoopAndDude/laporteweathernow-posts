#!/usr/bin/env python3
"""Storm records TEST (Oct. 19, 2026): per-lot snow, ice and rain records from free NOAA data.

For each storm in storm-records/config.json and each test lot:
  - snow total: NOAA's National Snowfall Analysis (NOHRSC sfav2, ~4 km). The 24-hour analyses (ending 6 AM CST)
    set each day's total (they take in the morning's observer reports); the 6-hour analyses split each day into
    quarters; NOAA MRMS radar + gauge precipitation (1-hour, 1 km) at the lot spreads each quarter over its hours;
  - snow, sleet, freezing rain or rain, and the temperature: the nearest airport's hourly reports (IEM ASOS
    archive); when radar shows precipitation at the lot but the airport reports none (lake-effect bands), the
    type comes from the temperature;
  - plow amount reached, heaviest hour, ice, low, refreeze after the snow, and the measured reports nearby
    (NWS storm reports and CoCoRaHS observers within 6 miles), shown next to the estimate.
Checks: the same estimate at every NWS storm report and CoCoRaHS observer in the region (they feed the analysis,
so this check is generous), and radar rain against CoCoRaHS rain gauges (not part of the radar estimate).
Rain records: rain at a job site during work hours from radar, next to the nearest airport with a rain gauge.

Writes storm-records/out/: records/<storm>/<lot>.json and .html, rain/<site>-<day>.json, index.html,
summary.json, summary.txt. Downloads go to a cache folder outside the repository.
"""
import datetime as dt
import gzip
import html
import json
import math
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
CONF = json.load(open(os.path.join(ROOT, "storm-records", "config.json")))
OUT = os.path.join(ROOT, "storm-records", "out")
CACHE = os.environ.get("STORM_CACHE", "/tmp/storm-cache")
CT = ZoneInfo("America/Chicago")
UTC = dt.timezone.utc
UA = {"User-Agent": "laporteweathernow.com storm records test (GitHub Actions; scoop090129@gmail.com)"}
REGION = CONF["region"]
NEARBY_MILES = 6.0
LOG = []
H1 = dt.timedelta(hours=1)
H6 = dt.timedelta(hours=6)
H24 = dt.timedelta(hours=24)


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


# ---------------------------------------------------------------- downloads and time helpers

def get(url, dest=None, tries=3, timeout=90):
    """Bytes of url, or the cached path when dest is given."""
    if dest and os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            if dest:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest + ".part", "wb") as f:
                    f.write(body)
                os.replace(dest + ".part", dest)
                return dest
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                break
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(2 * (i + 1))
    log(f"  ! could not get {url}: {last}")
    return None


def parse_local(s):
    return dt.datetime.fromisoformat(s).replace(tzinfo=CT)


def hours_between(a_utc, b_utc):
    """UTC hour marks h with a < h <= b (each is the END of a one-hour accumulation)."""
    h = a_utc.replace(minute=0, second=0, microsecond=0) + H1
    out = []
    while h <= b_utc:
        out.append(h)
        h += H1
    return out


def twelve_z_ends(a_utc, b_utc):
    """Ends (12 UTC) of the 24-hour periods that overlap (a, b]."""
    e = a_utc.replace(hour=12, minute=0, second=0, microsecond=0)
    if e <= a_utc:
        e += H24
    out = [e]
    while e < b_utc:
        e += H24
        out.append(e)
    return out


def fmt_local(t_utc, with_day=True):
    t = t_utc.astimezone(CT)
    if t.hour == 0:
        hr = "midnight"
    elif t.hour == 12:
        hr = "noon"
    else:
        hr = str(t.hour % 12) + (" AM" if t.hour < 12 else " PM")
    return (t.strftime("%a %b ") + str(t.day) + ", " + hr) if with_day else hr


def miles(a, b, c, d):
    r = 3958.8
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def in_region(lat, lon):
    return REGION["south"] <= lat <= REGION["north"] and REGION["west"] <= lon <= REGION["east"]


# ---------------------------------------------------------------- NOHRSC snowfall analysis (GeoTIFF, inches)

NOHRSC_UNITS = {"factor": 1.0, "checked": False}


def nohrsc_file(kind, end_utc):
    name = f"sfav2_CONUS_{kind}_{end_utc:%Y%m%d%H}.tif"
    return get(f"https://www.nohrsc.noaa.gov/snowfall_v2/data/{end_utc:%Y%m}/{name}", os.path.join(CACHE, "nohrsc", name))


def sample_tif(path, pts, raw=False):
    import rasterio
    out = []
    with rasterio.open(path) as ds:
        band = ds.read(1, masked=True)
        for lat, lon in pts:
            try:
                r, c = ds.index(lon, lat)
                v = band[r, c]
                v = None if np.ma.is_masked(v) else float(v)
            except Exception:  # noqa: BLE001
                v = None
            if v is not None and (math.isnan(v) or v < 0):
                v = None
            out.append(v if raw or v is None else v * NOHRSC_UNITS["factor"])
    return out


def calibrate_units():
    """Inches or meters? La Porte's season total through Jan. 26, 2026 was several feet, so a value under 5
    at La Porte would mean meters. (The Oct. 19 run found 56.8: inches.)"""
    name = "sfav2_CONUS_2025093012_to_2026012612.tif"
    path = get(f"https://www.nohrsc.noaa.gov/snowfall_v2/data/202601/{name}", os.path.join(CACHE, "nohrsc", name))
    if not path:
        log("  ! no season file to check NOHRSC units; assuming inches")
        return
    raw = sample_tif(path, [(41.61, -86.72)], raw=True)[0]
    if raw is not None:
        NOHRSC_UNITS["factor"] = 39.3701 if raw < 5 else 1.0
        log(f"  NOHRSC season total at La Porte through Jan 26: raw {raw:.2f} -> factor {NOHRSC_UNITS['factor']}")


# ---------------------------------------------------------------- MRMS hourly precipitation (GRIB2, cached crops)

MRMS_GRID = {}
MARGIN = 0.15


def mrms_file(end_utc):
    for p in ("Pass2", "Pass1"):
        key = (f"CONUS/MultiSensor_QPE_01H_{p}_00.00/{end_utc:%Y%m%d}/"
               f"MRMS_MultiSensor_QPE_01H_{p}_00.00_{end_utc:%Y%m%d-%H}0000.grib2.gz")
        path = get(f"https://noaa-mrms-pds.s3.amazonaws.com/{key}", os.path.join(CACHE, "mrms", os.path.basename(key)))
        if path:
            return path
    return None


def mrms_crop(path):
    crop_path = path[:-len(".grib2.gz")] + ".crop.npy"
    if os.path.exists(crop_path) and MRMS_GRID:
        return np.load(crop_path)
    import pygrib
    raw = path[:-3]
    if not os.path.exists(raw):
        with gzip.open(path, "rb") as fi, open(raw + ".part", "wb") as fo:
            shutil.copyfileobj(fi, fo)
        os.replace(raw + ".part", raw)
    grbs = pygrib.open(raw)
    g = grbs.message(1)
    if not MRMS_GRID:
        MRMS_GRID.update(lat1=g["latitudeOfFirstGridPointInDegrees"], lon1=g["longitudeOfFirstGridPointInDegrees"],
                         dlat=g["jDirectionIncrementInDegrees"], dlon=g["iDirectionIncrementInDegrees"],
                         jpos=g["jScansPositively"], ni=g["Ni"], nj=g["Nj"])
        G = MRMS_GRID
        north, south = REGION["north"] + MARGIN, REGION["south"] - MARGIN
        west, east = (REGION["west"] - MARGIN) % 360, (REGION["east"] + MARGIN) % 360
        if G["jpos"]:
            r0, r1 = int((south - G["lat1"]) / G["dlat"]), int((north - G["lat1"]) / G["dlat"]) + 1
        else:
            r0, r1 = int((G["lat1"] - north) / G["dlat"]), int((G["lat1"] - south) / G["dlat"]) + 1
        c0, c1 = int((west - G["lon1"]) / G["dlon"]), int((east - G["lon1"]) / G["dlon"]) + 1
        G.update(r0=r0, r1=r1, c0=c0, c1=c1)
        log(f"  MRMS grid: {MRMS_GRID}")
    G = MRMS_GRID
    v = np.ma.filled(np.ma.asarray(g.values, dtype=float), np.nan)[G["r0"]:G["r1"], G["c0"]:G["c1"]]
    grbs.close()
    v[v < 0] = np.nan
    np.save(crop_path, v)
    os.remove(raw)
    return v


def sample_mrms(path, pts):
    """Liquid precipitation (inches) at each point: the nearest 1 km cell (or the 3x3 mean when it's missing)."""
    v = mrms_crop(path)
    G = MRMS_GRID
    out = []
    for lat, lon in pts:
        r = int(round((lat - G["lat1"]) / G["dlat"])) if G["jpos"] else int(round((G["lat1"] - lat) / G["dlat"]))
        c = int(round(((lon % 360) - G["lon1"]) / G["dlon"]))
        r -= G["r0"]
        c -= G["c0"]
        if not (1 <= r < v.shape[0] - 1 and 1 <= c < v.shape[1] - 1):
            out.append(None)
            continue
        cell = v[r, c]
        if np.isnan(cell):
            win = v[r - 1:r + 2, c - 1:c + 2]
            cell = np.nan if np.all(np.isnan(win)) else np.nanmean(win)
        out.append(None if np.isnan(cell) else float(cell) / 25.4)
    return out


# ---------------------------------------------------------------- airport reports (IEM ASOS archive)

def asos(stations, a_utc, b_utc):
    q = [("station", s) for s in stations] + [("data", x) for x in ("tmpf", "wxcodes", "p01i")] + [
        ("year1", a_utc.year), ("month1", a_utc.month), ("day1", a_utc.day), ("hour1", a_utc.hour),
        ("year2", b_utc.year), ("month2", b_utc.month), ("day2", b_utc.day), ("hour2", b_utc.hour),
        ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "no"), ("missing", "M"), ("trace", "T")]
    body = get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?" + urllib.parse.urlencode(q))
    obs = {s: [] for s in stations}
    if not body:
        return obs
    lines = body.decode("utf-8", "replace").strip().splitlines()
    head = lines[0].split(",")
    for line in lines[1:]:
        row = dict(zip(head, line.split(",")))
        s = row.get("station")
        if s not in obs:
            continue
        t = dt.datetime.strptime(row["valid"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
        tmpf = None if row.get("tmpf") in ("M", "", None) else float(row["tmpf"])
        p = row.get("p01i")
        p01 = 0.001 if p == "T" else (None if p in ("M", "", None) else float(p))
        obs[s].append({"t": t, "tmpf": tmpf, "wx": "" if row.get("wxcodes") in ("M", None) else row["wxcodes"], "p01i": p01})
    return obs


def hour_obs(obs, end_utc):
    """Reports in the hour ending end_utc: weather codes, last temperature, the routine report's gauge amount."""
    rows = [o for o in obs if end_utc - H1 < o["t"] <= end_utc + dt.timedelta(minutes=5)]
    wx = " ".join(o["wx"] for o in rows if o["wx"])
    temps = [o["tmpf"] for o in rows if o["tmpf"] is not None]
    routine = [o for o in rows if 50 <= o["t"].minute <= 59 and o["p01i"] is not None]
    return wx, (temps[-1] if temps else None), (routine[-1]["p01i"] if routine else None)


def ptype(wx, temp, liquid):
    codes = [c.strip().lstrip("+-") for c in (wx or "").split() if c.strip()]
    if any("FZRA" in c or "FZDZ" in c for c in codes):
        return "freezing rain"
    if any("PL" in c for c in codes):
        return "sleet"
    if any(("SN" in c or "SG" in c) and c not in ("BLSN", "DRSN") for c in codes):
        return "snow"
    if any("RA" in c or "DZ" in c for c in codes):
        return "freezing rain" if (temp is not None and temp <= 31.5) else "rain"
    if liquid and liquid >= 0.005:
        if temp is None:
            return "snow?"
        return "snow" if temp <= 33.5 else "rain"
    return ""


def airport_rate(wx):
    """Typical water-equivalent rate (in./hour) for the heaviest snow the airport reported that hour."""
    codes = [c.strip() for c in (wx or "").split() if c.strip()]
    best = 0.0
    for c in codes:
        bare = c.lstrip("+-")
        if not (("SN" in bare or "PL" in bare or "SG" in bare) and bare not in ("BLSN", "DRSN")):
            continue
        rate = 0.04 if c.startswith("+") else (0.01 if c.startswith("-") else 0.02)
        best = max(best, rate)
    return best


def nearest_station(lat, lon, need_precip=False):
    best = None
    for sid, s in CONF["stations"].items():
        if need_precip and not s.get("precip", True):
            continue
        d = miles(lat, lon, s["lat"], s["lon"])
        if best is None or d < best[1]:
            best = (sid, d)
    return best


# ---------------------------------------------------------------- reports to compare with

def lsr_snow(a_utc, b_utc):
    q = urllib.parse.urlencode({"wfos": "IWX,LOT", "sts": f"{a_utc:%Y-%m-%dT%H:%MZ}", "ets": f"{b_utc:%Y-%m-%dT%H:%MZ}"})
    body = get(f"https://mesonet.agron.iastate.edu/geojson/lsr.geojson?{q}")
    out = []
    if not body:
        return out
    for f in json.loads(body).get("features", []):
        p = f.get("properties") or {}
        kind = str(p.get("typetext") or "").upper()
        if kind not in ("SNOW", "HEAVY SNOW") and p.get("type") != "S":
            continue
        try:
            inches = float(p.get("magnitude"))
            lon, lat = f["geometry"]["coordinates"][:2]
        except (TypeError, ValueError, KeyError):
            continue
        if inches <= 0 or not in_region(lat, lon):
            continue
        t = dt.datetime.fromisoformat(str(p.get("valid")).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
        out.append({"lat": lat, "lon": lon, "inches": inches, "t": t,
                    "place": f"{p.get('city') or ''}".strip(), "source": p.get("source") or ""})
    return out


COCO = {}


def cocorahs_day(date):
    if date in COCO:
        return COCO[date]
    out = []
    for net in ("IN_COCORAHS", "MI_COCORAHS"):
        body = get(f"https://mesonet.agron.iastate.edu/api/1/daily.geojson?network={net}&date={date}")
        if not body:
            continue
        for f in json.loads(body).get("features", []):
            p = f.get("properties") or {}
            lon, lat = f["geometry"]["coordinates"][:2]
            if not in_region(lat, lon):
                continue
            out.append({"id": p.get("station"), "name": p.get("name"), "lat": lat, "lon": lon,
                        "snow": p.get("snow"), "precip": p.get("precip"), "hour": p.get("temp_hour")})
    COCO[date] = out
    return out


# ---------------------------------------------------------------- the estimate at any set of points

def storm_series(points, a, b, hours_ext):
    """For each (lat, lon): hourly rows (radar water, airport type/temp, estimated snow) over hours_ext, with snow
    only inside (a, b]. Daily totals from the 24-hour analysis, split by the 6-hour analyses, spread by radar."""
    storm_hours = [h for h in hours_ext if h <= b]
    days = twelve_z_ends(a, b)
    v24, v6 = {}, {}
    for e in days:
        p = nohrsc_file("24h", e)
        v24[e] = sample_tif(p, points) if p else [None] * len(points)
        for k in (3, 2, 1, 0):
            e6 = e - k * H6
            if e6 not in v6:
                p6 = nohrsc_file("6h", e6)
                v6[e6] = sample_tif(p6, points) if p6 else [None] * len(points)
    radar = {}
    for h in storm_hours:
        p = mrms_file(h)
        radar[h] = sample_mrms(p, points) if p else [None] * len(points)
    out = []
    for i, (lat, lon) in enumerate(points):
        sid, sdist = nearest_station(lat, lon)
        rows = []
        for h in hours_ext:
            liquid = radar[h][i] if h in radar else None
            wx, temp, _ = hour_obs(OBS.get(sid, []), h)
            rows.append({"t": h, "liquid": liquid, "wx": wx, "temp": temp, "type": ptype(wx, temp, liquid),
                         "snow": 0.0, "in_storm": h <= b})
        by_t = {r["t"]: r for r in rows}
        sources = []
        for e in days:
            subs = [e - k * H6 for k in (3, 2, 1, 0)]
            s6 = [v6[x][i] or 0.0 for x in subs]
            tot24 = v24[e][i]
            day_total = tot24 if tot24 is not None else sum(s6)
            if not day_total:
                continue
            if sum(s6) > 0:
                shares = [x / sum(s6) for x in s6]
            else:  # no 6-hour detail: lean on radar, else spread evenly
                w = [sum(max(by_t[h]["liquid"] or 0, 0) for h in storm_hours if x - H6 < h <= x) for x in subs]
                shares = [x / sum(w) for x in w] if sum(w) > 0 else [0.25] * 4
            for x, share in zip(subs, shares):
                amt = day_total * share
                if amt <= 0:
                    continue
                hrs = [h for h in storm_hours if x - H6 < h <= x and h > a]
                if not hrs:
                    continue  # this quarter-day is outside the storm window
                snowy = [h for h in hrs if by_t[h]["type"] in ("snow", "snow?", "sleet")]
                pool = snowy or [h for h in hrs if (by_t[h]["liquid"] or 0) > 0] or hrs
                # weight = the larger of radar water at the lot and a typical water rate for the snow the
                # airport reports (light 0.01, moderate 0.02, heavy 0.04 in./hour), so an hour the radar
                # undercounts (shallow snow clouds) still gets its share
                w = [max(max(by_t[h]["liquid"] or 0.0, 0.0), airport_rate(by_t[h]["wx"])) for h in pool]
                if sum(w) <= 0:
                    w = [1.0] * len(pool)
                for h, wi in zip(pool, w):
                    by_t[h]["snow"] += amt * wi / sum(w)
            sources.append({"end": e.isoformat(), "nohrsc_24h": None if tot24 is None else round(tot24, 1),
                            "nohrsc_6h_sum": round(sum(s6), 1)})
        cum = 0.0
        for r in rows:
            cum += r["snow"]
            r["cum"] = cum
        out.append({"rows": rows, "station": (sid, sdist), "sources": sources, "total": cum})
    return out


OBS = {}


def summarize(lot, series, storm, nearby):
    rows = series["rows"]
    sid, sdist = series["station"]
    plow_t = next((r["t"] for r in rows if r["cum"] >= lot["plow_at"] - 1e-9 and r["cum"] > 0), None)
    snowy = [r for r in rows if r["snow"] >= 0.05]
    start = snowy[0]["t"] - H1 if snowy else None
    end = snowy[-1]["t"] if snowy else None
    heavy = max(rows, key=lambda r: r["snow"]) if rows else None
    in_storm = [r for r in rows if r["in_storm"]]
    ice = sum((r["liquid"] or 0) for r in in_storm if r["type"] == "freezing rain")
    sleet_h = sum(1 for r in in_storm if r["type"] == "sleet")
    temps = [r["temp"] for r in in_storm if r["temp"] is not None]
    # refreeze: once the snow is done, above freezing (melting), then back to 32F or colder
    refreeze, melt = None, None
    if end:
        above = False
        for r in rows:
            if r["t"] < end - dt.timedelta(hours=2) or r["temp"] is None:
                continue
            if r["temp"] > 32.5:
                above = True
                melt = melt or r["t"]
            elif above and r["temp"] <= 32:
                refreeze = r["t"]
                break
    after = [r["temp"] for r in rows if end and r["t"] > end and r["temp"] is not None]
    return {
        "lot": lot, "storm": {k: storm[k] for k in ("id", "name")},
        "station": {"id": sid, "name": CONF["stations"][sid]["name"], "miles": round(sdist, 1)},
        "snow_total_in": round(series["total"], 1), "plow_at": lot["plow_at"],
        "plow_reached": plow_t.isoformat() if plow_t else None,
        "start": start.isoformat() if start else None, "end": end.isoformat() if end else None,
        "heaviest": {"t": heavy["t"].isoformat(), "in": round(heavy["snow"], 2)} if heavy and heavy["snow"] > 0 else None,
        "ice_in": round(ice, 2), "sleet_hours": sleet_h,
        "low_f": min(temps) if temps else None, "high_f": max(temps) if temps else None,
        "after_low_f": min(after) if after else None, "after_high_f": max(after) if after else None,
        "melt": melt.isoformat() if melt else None, "refreeze": refreeze.isoformat() if refreeze else None,
        "nearby": nearby, "analysis_days": series["sources"],
        "hours": [{"t": r["t"].isoformat(), "snow_in": round(r["snow"], 2), "cum_in": round(r["cum"], 1),
                   "radar_water_in": None if r["liquid"] is None else round(r["liquid"], 3), "type": r["type"],
                   "temp_f": r["temp"], "wx": r["wx"]} for r in rows],
    }


# ---------------------------------------------------------------- pages

CSS = """body{margin:0;background:#f4f5f7;font:15px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#18212b}
.wrap{max-width:720px;margin:0 auto;padding:18px 16px 40px}.card{background:#fff;border:1px solid #d9dee4;border-radius:10px;padding:16px 18px;margin:0 0 14px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:0 0 8px}.muted{color:#5b6672;font-size:13px}.big{font-size:30px;font-weight:700;margin:6px 0}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:5px 6px;border-bottom:1px solid #e6e9ed;text-align:left;font-variant-numeric:tabular-nums}
th{color:#5b6672;font-weight:600}ul{margin:6px 0 0 18px;padding:0}li{margin:3px 0}.brand{color:#c2410c;font-weight:700;letter-spacing:.04em;font-size:12px;text-transform:uppercase}
a{color:#9a3412}.scroll{overflow-x:auto}"""


def page(title, body):
    return (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class=wrap>{body}</div></body></html>")


def T(s):
    return fmt_local(dt.datetime.fromisoformat(s)) if s else ""


def record_html(rec):
    e = html.escape
    lot, st = rec["lot"], rec["storm"]
    b = []
    b.append(f"Plow amount ({rec['plow_at']:g} in.) reached around <b>{T(rec['plow_reached'])}</b>." if rec["plow_reached"]
             else f"Plow amount ({rec['plow_at']:g} in.) not reached.")
    if rec["start"] and rec["end"]:
        b.append(f"Snow fell from about {T(rec['start'])} to {T(rec['end'])}.")
    if rec["heaviest"]:
        b.append(f"Heaviest: about {rec['heaviest']['in']:.1f} in. in the hour ending {T(rec['heaviest']['t'])}.")
    if rec["ice_in"] >= 0.01:
        b.append(f"Freezing rain: about {rec['ice_in']:.2f} in. (ice).")
    elif rec["sleet_hours"]:
        b.append(f"Sleet at the airport for {rec['sleet_hours']} hour(s).")
    else:
        b.append("No freezing rain or sleet reported.")
    if rec["low_f"] is not None:
        b.append(f"Temperature during the storm: {rec['low_f']:.0f}&ndash;{rec['high_f']:.0f}&deg;F.")
    if rec["refreeze"]:
        b.append(f"<b>Refreeze:</b> above freezing from about {T(rec['melt'])}, back to 32&deg;F or colder around {T(rec['refreeze'])}.")
    elif rec["after_high_f"] is not None and rec["after_high_f"] <= 32:
        b.append(f"Stayed below freezing for the 18 hours after the snow (high {rec['after_high_f']:.0f}&deg;F): no melting.")
    elif rec["melt"]:
        b.append(f"Above freezing from about {T(rec['melt'])} after the snow.")
    near = ""
    if rec["nearby"]:
        items = "".join(f"<li>{n['inches']:.1f} in. at {e(n['place'])} ({n['miles']:.1f} mi), {e(n['what'])}</li>" for n in rec["nearby"][:4])
        near = f"<div class=card><h2>Measured nearby</h2><ul>{items}</ul><p class=muted>Reports from the National Weather Service and CoCoRaHS volunteer observers.</p></div>"
    rows = []
    for h in rec["hours"]:
        if h["snow_in"] < 0.05 and not h["type"]:
            continue
        temp = "" if h["temp_f"] is None else "%.0f&deg;" % h["temp_f"]
        rows.append(f"<tr><td>{e(T(h['t']))}</td><td>{h['snow_in']:.1f}</td><td>{h['cum_in']:.1f}</td>"
                    f"<td>{e(h['type'] or '-')}</td><td>{temp}</td></tr>")
    body = (f"<p class=brand>Hard Hat Weather &middot; storm record (test)</p>"
            f"<div class=card><h1>{e(lot['label'])}</h1><p class=muted>{e(st['name'])}</p>"
            f"<p class=big>{rec['snow_total_in']:.1f} in. of snow</p><ul>{''.join('<li>' + x + '</li>' for x in b)}</ul></div>"
            f"{near}"
            f"<div class=card><h2>Hour by hour</h2><div class=scroll><table><tr><th>Hour ending</th><th>Snow (in.)</th>"
            f"<th>Total</th><th>Type</th><th>Temp</th></tr>{''.join(rows)}</table></div>"
            f"<p class=muted>Snow: NOAA National Snowfall Analysis (NOHRSC) for this spot, split by hour with NOAA MRMS radar "
            f"at this spot. Type and temperature: {e(rec['station']['name'])} ({rec['station']['miles']:.0f} miles away). "
            f"Estimates from public NOAA data, not a certified report.</p></div>")
    return page(f"Storm record: {lot['label']}, {st['name']}", body)


def nearby_reports(lat, lon, lsrs, coco_days):
    out = []
    for r in lsrs:
        d = miles(lat, lon, r["lat"], r["lon"])
        if d <= NEARBY_MILES:
            out.append({"inches": r["inches"], "place": r["place"] or "storm report", "miles": round(d, 1),
                        "what": f"NWS storm report, {fmt_local(r['t'])}", "t": r["t"].isoformat()})
    for day, obs in coco_days:
        for o in obs:
            if not isinstance(o["snow"], (int, float)) or o["snow"] <= 0:
                continue
            d = miles(lat, lon, o["lat"], o["lon"])
            if d <= NEARBY_MILES:
                out.append({"inches": float(o["snow"]), "place": o["name"], "miles": round(d, 1),
                            "what": f"CoCoRaHS, 24 hours to about 7 AM {dt.date.fromisoformat(day):%a %b} {dt.date.fromisoformat(day).day}",
                            "t": day})
    out.sort(key=lambda x: (x["miles"], -x["inches"]))
    return out


# ---------------------------------------------------------------- main

def stats(pairs, a="reported", b="analysis"):
    if not pairs:
        return {"n": 0}
    d = [p[b] - p[a] for p in pairs]
    ad = sorted(abs(x) for x in d)
    return {"n": len(d), "mean_diff": round(sum(d) / len(d), 2), "mean_abs_diff": round(sum(ad) / len(ad), 2),
            "median_abs_diff": round(ad[len(ad) // 2], 2),
            "within_1": round(sum(1 for x in ad if x <= 1) / len(ad), 2),
            "within_2": round(sum(1 for x in ad if x <= 2) / len(ad), 2)}


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    lots = {l["id"]: l for l in CONF["lots"]}
    lot_pts = [(l["lat"], l["lon"]) for l in CONF["lots"]]
    summary = {"made": dt.datetime.now(CT).isoformat(timespec="minutes"), "storms": [], "checks": {}, "rain": []}
    pairs_lsr, pairs_coco, pairs_coco6 = [], [], []
    calibrate_units()

    for storm in CONF["storms"]:
        a = parse_local(storm["start"]).astimezone(UTC)
        b = parse_local(storm["end"]).astimezone(UTC)
        log(f"Storm {storm['name']}: {a:%Y-%m-%d %H}Z to {b:%Y-%m-%d %H}Z")
        hours_ext = hours_between(a, b + dt.timedelta(hours=18))
        OBS.clear()
        OBS.update(asos(list(CONF["stations"]), a - H1, b + dt.timedelta(hours=19)))
        lsrs = lsr_snow(a, b + dt.timedelta(hours=12))
        coco_days = []
        day = a.astimezone(CT).date() + dt.timedelta(days=1)
        while day <= b.astimezone(CT).date() + dt.timedelta(days=1):
            coco_days.append((day.isoformat(), cocorahs_day(day.isoformat())))
            day += dt.timedelta(days=1)

        series = storm_series(lot_pts, a, b, hours_ext)
        recs = []
        for (lid, lot), ser in zip(lots.items(), series):
            near = nearby_reports(lot["lat"], lot["lon"], lsrs, coco_days)
            rec = summarize(lot, ser, storm, near)
            d = os.path.join(OUT, "records", storm["id"])
            os.makedirs(d, exist_ok=True)
            json.dump(rec, open(os.path.join(d, f"{lid}.json"), "w"), indent=1)
            open(os.path.join(d, f"{lid}.html"), "w").write(record_html(rec))
            recs.append({"lot": lid, "label": lot["label"], "snow": rec["snow_total_in"], "plow": rec["plow_reached"],
                         "ice": rec["ice_in"], "refreeze": rec["refreeze"], "start": rec["start"], "end": rec["end"],
                         "nearby": near[:2]})
            log(f"  {lot['label']}: {rec['snow_total_in']} in.; plow {rec['plow_reached']}; {rec['start']} to {rec['end']}; "
                f"refreeze {rec['refreeze']}; nearby {[(n['inches'], n['place'], n['miles']) for n in near[:3]]}")

        # check 1: NWS storm reports (storm totals so far) vs the same estimate at the report, up to its time
        if lsrs:
            sers = storm_series([(r["lat"], r["lon"]) for r in lsrs], a, b, hours_between(a, b))
            for r, s in zip(lsrs, sers):
                est = sum(x["snow"] for x in s["rows"] if x["t"] <= r["t"] + H1)
                pairs_lsr.append({"storm": storm["id"], "place": r["place"], "reported": r["inches"], "analysis": round(est, 1)})
        # check 2: CoCoRaHS 24-hour snow vs the 24-hour analysis ending 12 UTC that morning (and the 6-hour sum)
        for day_s, obs in coco_days:
            d = dt.date.fromisoformat(day_s)
            e12 = dt.datetime(d.year, d.month, d.day, 12, tzinfo=UTC)
            pts = [o for o in obs if isinstance(o["snow"], (int, float))]
            p24 = nohrsc_file("24h", e12)
            if not p24 or not pts:
                continue
            xy = [(o["lat"], o["lon"]) for o in pts]
            v24 = sample_tif(p24, xy)
            v6 = [0.0] * len(pts)
            ok6 = True
            for k in range(4):
                p6 = nohrsc_file("6h", e12 - k * H6)
                if not p6:
                    ok6 = False
                    break
                for i, v in enumerate(sample_tif(p6, xy)):
                    v6[i] += v or 0.0
            for o, x24, x6 in zip(pts, v24, v6):
                if x24 is None or (o["snow"] == 0 and x24 < 0.1):
                    continue
                pairs_coco.append({"storm": storm["id"], "date": day_s, "name": o["name"], "reported": o["snow"], "analysis": round(x24, 1)})
                if ok6:
                    pairs_coco6.append({"storm": storm["id"], "date": day_s, "name": o["name"], "reported": o["snow"], "analysis": round(x6, 1)})
        summary["storms"].append({"id": storm["id"], "name": storm["name"], "lots": recs})

    summary["checks"]["snow_vs_storm_reports"] = stats(pairs_lsr)
    summary["checks"]["snow_vs_cocorahs_24h"] = stats(pairs_coco)
    summary["checks"]["snow_vs_cocorahs_6h_sums"] = stats(pairs_coco6)
    summary["checks"]["pairs_storm_reports"] = pairs_lsr
    summary["checks"]["pairs_cocorahs"] = pairs_coco
    for k in ("snow_vs_storm_reports", "snow_vs_cocorahs_24h", "snow_vs_cocorahs_6h_sums"):
        log(f"Check {k}: {summary['checks'][k]}")

    # ---------------- rain at a job site during work hours (radar) vs the nearest airport with a gauge
    rain = CONF["rain"]
    w0, w1 = rain["work_hours"]
    site_ids = rain["sites"]
    pts = [(lots[i]["lat"], lots[i]["lon"]) for i in site_ids]
    for day in rain["days"]:
        d0 = dt.datetime.fromisoformat(day).replace(tzinfo=CT)
        a = (d0 + dt.timedelta(hours=w0)).astimezone(UTC)
        b = (d0 + dt.timedelta(hours=w1)).astimezone(UTC)
        hours = hours_between(a, b)
        vals = {}
        for h in hours:
            p = mrms_file(h)
            vals[h] = sample_mrms(p, pts) if p else [None] * len(pts)
        obs = asos(list(CONF["stations"]), a - H1, b + H1)
        for k, lid in enumerate(site_ids):
            lot = lots[lid]
            sid, sd = nearest_station(lot["lat"], lot["lon"], need_precip=True)
            per = []
            for h in hours:
                _, temp, p01 = hour_obs(obs.get(sid, []), h)
                per.append({"t": h.isoformat(), "site_in": None if vals[h][k] is None else round(vals[h][k], 3),
                            "airport_in": p01, "temp_f": temp})
            site_tot = sum(p["site_in"] or 0 for p in per)
            wet = sum(1 for p in per if (p["site_in"] or 0) >= 0.01)
            ap = [p["airport_in"] for p in per if p["airport_in"] is not None]
            ap_tot = sum(x for x in ap if x > 0.001) if ap else None
            ap_wet = sum(1 for x in ap if x >= 0.01) if ap else None
            item = {"day": day, "site": lid, "label": lot["label"], "station": sid,
                    "station_name": CONF["stations"][sid]["name"], "station_miles": round(sd, 1),
                    "site_rain_in": round(site_tot, 2), "site_wet_hours": wet,
                    "airport_rain_in": None if ap_tot is None else round(ap_tot, 2), "airport_wet_hours": ap_wet, "hours": per}
            os.makedirs(os.path.join(OUT, "rain"), exist_ok=True)
            json.dump(item, open(os.path.join(OUT, "rain", f"{lid}-{day}.json"), "w"), indent=1)
            summary["rain"].append({k2: v for k2, v in item.items() if k2 != "hours"})
            log(f"Rain {day} {lot['label']}: site {site_tot:.2f} in. ({wet} wet hours) vs {sid} {ap_tot} in. ({ap_wet})")

    # radar rain vs CoCoRaHS gauges (24 hours ending about 7 AM)
    pairs = []
    for day in rain["gauge_dates"]:
        d = dt.date.fromisoformat(day)
        end = dt.datetime(d.year, d.month, d.day, 7, tzinfo=CT).astimezone(UTC)
        gauges = [o for o in cocorahs_day(day) if isinstance(o["precip"], (int, float))]
        if not gauges:
            continue
        gp = [(o["lat"], o["lon"]) for o in gauges]
        tot = [0.0] * len(gauges)
        ok = 0
        for h in hours_between(end - H24, end):
            p = mrms_file(h)
            if not p:
                continue
            ok += 1
            for i, v in enumerate(sample_mrms(p, gp)):
                tot[i] += v or 0.0
        if ok < 20:
            continue
        for o, est in zip(gauges, tot):
            if o["precip"] == 0 and est < 0.02:
                continue
            pairs.append({"date": day, "name": o["name"], "gauge": o["precip"], "radar": round(est, 2)})
    summary["checks"]["rain_vs_cocorahs"] = stats(pairs, a="gauge", b="radar")
    summary["checks"]["pairs_rain"] = pairs
    log(f"Check rain_vs_cocorahs: {summary['checks']['rain_vs_cocorahs']}")

    summary["seconds"] = round(time.time() - t0)
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1, default=str)
    write_index(summary)
    open(os.path.join(OUT, "summary.txt"), "w").write("\n".join(LOG) + "\n")
    log(f"Done in {summary['seconds']} s")


def write_index(s):
    e = html.escape
    parts = ["<p class=brand>Hard Hat Weather &middot; storm records test</p><div class=card><h1>Storm records: last winter, 5 test lots</h1>"
             f"<p class=muted>Made {e(s['made'])} from public NOAA data. Not live; no customers.</p></div>"]
    def near_text(lot_row):
        items = ["%.1f at %s" % (n["inches"], n["place"]) for n in lot_row["nearby"]]
        return "; ".join(items) or "-"

    for st in s["storms"]:
        rows = "".join(
            f"<tr><td><a href='records/{st['id']}/{l['lot']}.html'>{e(l['label'])}</a></td><td>{l['snow']:.1f}</td>"
            f"<td>{e(T(l['plow']) or '-')}</td><td>{e(T(l['refreeze']) or '-')}</td><td>{e(near_text(l))}</td></tr>"
            for l in st["lots"])
        parts.append(f"<div class=card><h2>{e(st['name'])}</h2><div class=scroll><table><tr><th>Lot</th><th>Snow (in.)</th>"
                     f"<th>Plow amount reached</th><th>Refreeze</th><th>Measured nearby</th></tr>{rows}</table></div></div>")
    c = s["checks"]

    def line(k, label):
        x = c.get(k) or {}
        if not x.get("n"):
            return f"<li>{label}: no pairs</li>"
        return (f"<li>{label}: {x['n']} pairs, typical miss {x['median_abs_diff']} in. (average {x['mean_abs_diff']}), "
                f"within 1 in. {round(100 * x['within_1'])}%, within 2 in. {round(100 * x['within_2'])}%, average difference {x['mean_diff']:+}</li>")
    parts.append("<div class=card><h2>How close it is</h2><ul>"
                 + line("snow_vs_storm_reports", "Snow vs NWS storm reports (storm totals)")
                 + line("snow_vs_cocorahs_24h", "Snow vs CoCoRaHS observers (24 hours)")
                 + line("snow_vs_cocorahs_6h_sums", "Same, using the 6-hour analyses added up")
                 + line("rain_vs_cocorahs", "Radar rain vs CoCoRaHS rain gauges (24 hours)")
                 + "</ul><p class=muted>The snowfall analysis uses many of these same reports, so the snow check is generous. "
                 "The rain gauges are not part of the radar estimate.</p></div>")
    rr = "".join(f"<tr><td>{e(r['day'])}</td><td>{e(r['label'])}</td><td>{r['site_rain_in']:.2f} ({r['site_wet_hours']} h)</td>"
                 f"<td>{'-' if r['airport_rain_in'] is None else '%.2f (%s h)' % (r['airport_rain_in'], r['airport_wet_hours'])} "
                 f"{e(r['station_name'])}, {r['station_miles']:.0f} mi</td></tr>" for r in s["rain"])
    parts.append(f"<div class=card><h2>Rain during work hours (7 AM-5 PM): radar at the job site vs the nearest airport gauge</h2>"
                 f"<div class=scroll><table><tr><th>Day</th><th>Site</th><th>At the site (wet hours)</th><th>Nearest airport</th></tr>{rr}</table></div></div>")
    open(os.path.join(OUT, "index.html"), "w").write(page("Storm records test", "".join(parts)))


if __name__ == "__main__":
    main()
