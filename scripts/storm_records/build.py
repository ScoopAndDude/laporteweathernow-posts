#!/usr/bin/env python3
"""Storm records TEST (Oct. 19, 2026): per-lot snow, ice and rain records from free NOAA data.

For each storm in storm-records/config.json and each test lot:
  - snow total: NOAA's National Snowfall Analysis (NOHRSC sfav2, 6-hour grids, ~4 km), summed over the storm;
  - when it fell: NOAA MRMS radar + gauge precipitation (MultiSensor QPE 1-hour, 1 km) at the lot, hour by hour;
    the 6-hour snow totals are spread over the hours in proportion to the radar precipitation;
  - snow, sleet, freezing rain or rain, and the temperature: the nearest airport's hourly reports (IEM ASOS archive);
  - plow amount reached, heaviest hour, ice, low, and whether it refroze afterward.
Checks: the snow analysis at every NWS storm report and CoCoRaHS observer in the region (they feed the analysis,
so this check is generous), and radar rain against CoCoRaHS rain gauges (not part of the radar estimate).
Rain records: rain at a job site during work hours from radar, next to the nearest airport.

Writes storm-records/out/: records/<storm>/<lot>.json and .html, rain/<site>-<day>.json, index.html, summary.json,
summary.txt. Downloads go to a cache folder outside the repository.
"""
import datetime as dt
import gzip
import html
import json
import math
import os
import shutil
import sys
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
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


# ---------------------------------------------------------------- downloads

def get(url, dest=None, tries=3, timeout=90):
    """Bytes of url (or the path it was saved to). Cached in CACHE when dest is given."""
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
    h = a_utc.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
    out = []
    while h <= b_utc:
        out.append(h)
        h += dt.timedelta(hours=1)
    return out


def six_hour_ends(a_utc, b_utc):
    """6-hour period ends (00, 06, 12, 18 UTC) covering (a, b]."""
    h = a_utc.replace(minute=0, second=0, microsecond=0)
    h -= dt.timedelta(hours=h.hour % 6)
    out = []
    while h < b_utc:
        h += dt.timedelta(hours=6)
        out.append(h)
    return out


def fmt_local(t_utc, with_day=True):
    t = t_utc.astimezone(CT)
    hr = t.strftime("%I").lstrip("0") + (" AM" if t.hour < 12 else " PM")
    if t.hour == 0 and t.minute == 0:
        hr = "midnight"
    elif t.hour == 12 and t.minute == 0:
        hr = "noon"
    return (t.strftime("%a %b ") + str(t.day) + ", " + hr) if with_day else hr


# ---------------------------------------------------------------- NOHRSC snowfall analysis (GeoTIFF)

NOHRSC_UNITS = {"factor": None}


def nohrsc_file(kind, end_utc):
    name = f"sfav2_CONUS_{kind}_{end_utc:%Y%m%d%H}.tif"
    url = f"https://www.nohrsc.noaa.gov/snowfall_v2/data/{end_utc:%Y%m}/{name}"
    return get(url, os.path.join(CACHE, "nohrsc", name))


def sample_tif(path, pts):
    """Nearest-pixel values (in inches) at [(lat, lon)], plus the file's own unit note."""
    import rasterio
    out = []
    with rasterio.open(path) as ds:
        if NOHRSC_UNITS["factor"] is None:
            tags = {**ds.tags(), **ds.tags(1)}
            units = " ".join([str(ds.units[0] if ds.units else "")] + [f"{k}={v}" for k, v in tags.items()]).lower()
            log(f"  NOHRSC file {os.path.basename(path)}: crs={ds.crs} res={ds.res} nodata={ds.nodata} units/tags: {units[:300]}")
            if "meter" in units or " m " in f" {units} " or "units=m" in units:
                NOHRSC_UNITS["factor"] = 39.3701
            elif "inch" in units or "units=in" in units:
                NOHRSC_UNITS["factor"] = 1.0
        band = ds.read(1, masked=True)
        for lat, lon in pts:
            try:
                r, c = ds.index(lon, lat)
                v = band[r, c]
                out.append(None if np.ma.is_masked(v) else float(v))
            except Exception:  # noqa: BLE001
                out.append(None)
    return out


def snow_in(v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or v < 0)):
        return None
    f = NOHRSC_UNITS["factor"] or 1.0
    return v * f


def calibrate_units():
    """Inches or meters? La Porte's season total through Jan. 26, 2026 was several feet (storm reports:
    20+ inches in November alone), so a value under 5 at La Porte means the grid is in meters."""
    name = "sfav2_CONUS_2025093012_to_2026012612.tif"
    path = get(f"https://www.nohrsc.noaa.gov/snowfall_v2/data/202601/{name}", os.path.join(CACHE, "nohrsc", name))
    if not path:
        log("  ! no season file to check NOHRSC units; assuming the file's tags")
        return
    keep = NOHRSC_UNITS["factor"]
    NOHRSC_UNITS["factor"] = 1.0
    raw = sample_tif(path, [(41.61, -86.72)])[0]
    NOHRSC_UNITS["factor"] = keep
    if raw is None:
        log("  ! season file had no value at La Porte")
        return
    factor = 39.3701 if raw < 5 else 1.0
    if keep and abs(keep - factor) > 0.01:
        log(f"  ! file tags said factor {keep}, season check says {factor}; using the season check")
    NOHRSC_UNITS["factor"] = factor
    log(f"  NOHRSC season total at La Porte through Jan 26: raw {raw:.3f} -> unit factor {factor} ({raw * factor:.1f} in.)")


# ---------------------------------------------------------------- MRMS hourly precipitation (GRIB2)

MRMS_GRID = {}


def mrms_file(end_utc):
    for p in ("Pass2", "Pass1"):
        key = (f"CONUS/MultiSensor_QPE_01H_{p}_00.00/{end_utc:%Y%m%d}/"
               f"MRMS_MultiSensor_QPE_01H_{p}_00.00_{end_utc:%Y%m%d-%H}0000.grib2.gz")
        path = get(f"https://noaa-mrms-pds.s3.amazonaws.com/{key}", os.path.join(CACHE, "mrms", os.path.basename(key)))
        if path:
            return path
    return None


MARGIN = 0.15  # degrees around the region kept from each MRMS file


def mrms_crop(path):
    """The region's piece of an MRMS file (mm, NaN where missing), decoded once and cached as .npy."""
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
                         jpos=g["jScansPositively"], ni=g["Ni"], nj=g["Nj"], name=g.name, units=g.units)
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
    """Liquid precipitation (inches) at [(lat, lon)]: the nearest 1 km cell, and the mean of the 3x3 around it."""
    v = mrms_crop(path)
    G = MRMS_GRID
    out = []
    for lat, lon in pts:
        lon360 = lon % 360
        r = int(round((lat - G["lat1"]) / G["dlat"])) if G["jpos"] else int(round((G["lat1"] - lat) / G["dlat"]))
        c = int(round((lon360 - G["lon1"]) / G["dlon"]))
        r -= G["r0"]
        c -= G["c0"]
        if not (1 <= r < v.shape[0] - 1 and 1 <= c < v.shape[1] - 1):
            out.append((None, None))
            continue
        win = v[r - 1:r + 2, c - 1:c + 2]
        cell = v[r, c]
        cell = None if np.isnan(cell) else float(cell) / 25.4
        mean = None if np.all(np.isnan(win)) else float(np.nanmean(win)) / 25.4
        out.append((cell, mean))
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
    """Reports in the hour ending end_utc: weather codes seen, last temperature, the hour's gauge amount."""
    rows = [o for o in obs if end_utc - dt.timedelta(hours=1) < o["t"] <= end_utc + dt.timedelta(minutes=5)]
    wx = " ".join(o["wx"] for o in rows if o["wx"])
    temps = [o["tmpf"] for o in rows if o["tmpf"] is not None]
    # the routine report near :53-:56 carries the hour's precipitation (p01i resets each hour)
    routine = [o for o in rows if 50 <= o["t"].minute <= 59 and o["p01i"] is not None]
    p01 = routine[-1]["p01i"] if routine else None
    return wx, (temps[-1] if temps else None), p01


def ptype(wx, temp, liquid):
    """snow / sleet / freezing rain / rain from the airport's weather codes, else from the temperature
    when radar shows precipitation at the lot (lake-effect can miss the airport)."""
    codes = [c.strip() for c in (wx or "").split() if c.strip()]
    bare = [c.lstrip("+-") for c in codes]
    if any("FZRA" in c or "FZDZ" in c for c in bare):
        return "freezing rain"
    if any("PL" in c for c in bare):
        return "sleet"
    if any(("SN" in c or "SG" in c) and c not in ("BLSN", "DRSN") for c in bare):
        return "snow"
    if any("RA" in c or "DZ" in c for c in bare):
        return "freezing rain" if (temp is not None and temp <= 31.5) else "rain"
    if liquid and liquid >= 0.005:
        if temp is None:
            return "snow?"
        return "snow" if temp <= 33.5 else "rain"
    return ""


def nearest_station(lat, lon):
    best = None
    for sid, s in CONF["stations"].items():
        d = miles(lat, lon, s["lat"], s["lon"])
        if best is None or d < best[1]:
            best = (sid, d)
    return best


def miles(a, b, c, d):
    r = 3958.8
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


# ---------------------------------------------------------------- reports to check against

def in_region(lat, lon):
    return REGION["south"] <= lat <= REGION["north"] and REGION["west"] <= lon <= REGION["east"]


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


def cocorahs_day(date):
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
    return out


# ---------------------------------------------------------------- one lot, one storm

def build_record(lot, storm, hours, mrms, six, six_vals, obs):
    lat, lon = lot["lat"], lot["lon"]
    sid, sdist = nearest_station(lat, lon)
    rows = []
    for h in hours:
        cell, mean = mrms.get(h, {}).get(lot["id"], (None, None))
        liquid = cell if cell is not None else mean
        wx, temp, p01 = hour_obs(obs.get(sid, []), h)
        rows.append({"t": h, "liquid": liquid, "wx": wx, "temp": temp, "airport_p01": p01,
                     "type": ptype(wx, temp, liquid), "snow": 0.0})
    # spread each 6-hour snow total over its hours, weighted by radar precipitation in snow-like hours
    total = 0.0
    for end in six:
        s6 = six_vals.get(end, {}).get(lot["id"])
        if not s6:
            continue
        total += s6
        idx = [i for i, r in enumerate(rows) if end - dt.timedelta(hours=6) < r["t"] <= end]
        if not idx:
            continue
        snowy = [i for i in idx if rows[i]["type"] in ("snow", "snow?", "sleet")]
        pool = snowy or [i for i in idx if (rows[i]["liquid"] or 0) > 0] or idx
        w = [max(rows[i]["liquid"] or 0.0, 0.0) for i in pool]
        if sum(w) <= 0:
            w = [1.0] * len(pool)
        for i, wi in zip(pool, w):
            rows[i]["snow"] += s6 * wi / sum(w)
    cum = 0.0
    plow_t = None
    for r in rows:
        cum += r["snow"]
        r["cum"] = cum
        if plow_t is None and cum >= lot["plow_at"]:
            plow_t = r["t"]
    snow_hours = [r for r in rows if r["snow"] >= 0.05]
    start = snow_hours[0]["t"] - dt.timedelta(hours=1) if snow_hours else None
    end = snow_hours[-1]["t"] if snow_hours else None
    heavy = max(rows, key=lambda r: r["snow"]) if rows else None
    ice = sum((r["liquid"] or 0) for r in rows if r["type"] == "freezing rain")
    sleet_h = sum(1 for r in rows if r["type"] == "sleet")
    temps = [r["temp"] for r in rows if r["temp"] is not None]
    # refreeze: above freezing during or after the storm, then back to 32F or below
    refreeze = None
    above = False
    after_start = start or (rows[0]["t"] if rows else None)
    for r in rows:
        if after_start and r["t"] < after_start:
            continue
        if r["temp"] is None:
            continue
        if r["temp"] > 32.5:
            above = True
        elif above and r["temp"] <= 32:
            refreeze = r["t"]
            above = False
    return {
        "lot": lot, "storm": {k: storm[k] for k in ("id", "name")},
        "station": {"id": sid, "name": CONF["stations"][sid]["name"], "miles": round(sdist, 1)},
        "snow_total_in": round(total, 1), "plow_at": lot["plow_at"],
        "plow_reached": plow_t.isoformat() if plow_t else None,
        "start": start.isoformat() if start else None, "end": end.isoformat() if end else None,
        "heaviest": {"t": heavy["t"].isoformat(), "in": round(heavy["snow"], 2)} if heavy and heavy["snow"] > 0 else None,
        "ice_in": round(ice, 2), "sleet_hours": sleet_h,
        "low_f": min(temps) if temps else None, "high_f": max(temps) if temps else None,
        "refreeze": refreeze.isoformat() if refreeze else None,
        "radar_liquid_in": round(sum((r["liquid"] or 0) for r in rows), 2),
        "hours": [{"t": r["t"].isoformat(), "snow_in": round(r["snow"], 2), "cum_in": round(r["cum"], 1),
                   "liquid_in": None if r["liquid"] is None else round(r["liquid"], 3), "type": r["type"],
                   "temp_f": r["temp"], "wx": r["wx"]} for r in rows],
    }


# ---------------------------------------------------------------- pages

CSS = """body{margin:0;background:#f4f5f7;font:15px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#18212b}
.wrap{max-width:720px;margin:0 auto;padding:18px 16px 40px}.card{background:#fff;border:1px solid #d9dee4;border-radius:10px;padding:16px 18px;margin:0 0 14px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:0 0 8px}.muted{color:#5b6672;font-size:13px}.big{font-size:30px;font-weight:700}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:5px 6px;border-bottom:1px solid #e6e9ed;text-align:left;font-variant-numeric:tabular-nums}
th{color:#5b6672;font-weight:600}.tag{display:inline-block;padding:1px 7px;border-radius:9px;background:#fde9dd;color:#9a3412;font-size:12px;font-weight:600}
ul{margin:6px 0 0 18px;padding:0}li{margin:3px 0}.brand{color:#c2410c;font-weight:700;letter-spacing:.04em;font-size:12px;text-transform:uppercase}
a{color:#9a3412}.scroll{overflow-x:auto}"""


def page(title, body):
    return (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class=wrap>{body}</div></body></html>")


def record_html(rec):
    e = html.escape
    lot, st = rec["lot"], rec["storm"]
    T = lambda s: fmt_local(dt.datetime.fromisoformat(s)) if s else "not reached"  # noqa: E731
    bullets = []
    if rec["plow_reached"]:
        bullets.append(f"Plow amount ({rec['plow_at']:g} in.) reached around <b>{T(rec['plow_reached'])}</b>.")
    else:
        bullets.append(f"Plow amount ({rec['plow_at']:g} in.) not reached.")
    if rec["start"] and rec["end"]:
        bullets.append(f"Snow fell from about {T(rec['start'])} to {T(rec['end'])}.")
    if rec["heaviest"]:
        bullets.append(f"Heaviest: about {rec['heaviest']['in']:.1f} in. in the hour ending {T(rec['heaviest']['t'])}.")
    if rec["ice_in"] >= 0.01:
        bullets.append(f"Freezing rain: about {rec['ice_in']:.2f} in. (ice).")
    elif rec["sleet_hours"]:
        bullets.append(f"Sleet reported for {rec['sleet_hours']} hour(s).")
    else:
        bullets.append("No freezing rain or sleet reported.")
    if rec["low_f"] is not None:
        bullets.append(f"Temperature {rec['low_f']:.0f}&ndash;{rec['high_f']:.0f}&deg;F at the {e(rec['station']['name'])}.")
    if rec["refreeze"]:
        bullets.append(f"<b>Refreeze:</b> above freezing, then back to 32&deg;F or colder around {T(rec['refreeze'])}.")
    else:
        bullets.append("No thaw and refreeze during the storm window.")
    rows = []
    for h in rec["hours"]:
        if h["snow_in"] < 0.05 and not h["type"]:
            continue
        when = e(fmt_local(dt.datetime.fromisoformat(h["t"])))
        temp = "" if h["temp_f"] is None else "%.0f&deg;" % h["temp_f"]
        water = "" if h["liquid_in"] is None else "%.2f" % h["liquid_in"]
        rows.append(f"<tr><td>{when}</td><td>{h['snow_in']:.1f}</td><td>{h['cum_in']:.1f}</td>"
                    f"<td>{e(h['type'] or '-')}</td><td>{temp}</td><td>{water}</td></tr>")
    body = (f"<p class=brand>Hard Hat Weather &middot; storm record (test)</p>"
            f"<div class=card><h1>{e(lot['label'])}</h1><p class=muted>{e(st['name'])}</p>"
            f"<p class=big>{rec['snow_total_in']:.1f} in. of snow</p>"
            f"<ul>{''.join('<li>' + b + '</li>' for b in bullets)}</ul></div>"
            f"<div class=card><h2>Hour by hour</h2><div class=scroll><table><tr><th>Hour ending</th><th>Snow (in.)</th><th>Total</th>"
            f"<th>Type</th><th>Temp</th><th>Water (in.)</th></tr>{''.join(rows)}</table></div>"
            f"<p class=muted>Snow: NOAA National Snowfall Analysis (NOHRSC), 6-hour totals at this spot, spread over the hours by NOAA MRMS "
            f"radar and gauge precipitation measured at this spot. Type and temperature: {e(rec['station']['name'])} hourly reports "
            f"({rec['station']['miles']:.0f} miles away). Estimates from public NOAA data, not a certified report.</p></div>")
    return page(f"Storm record: {lot['label']}, {st['name']}", body)


# ---------------------------------------------------------------- main

def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    lots = {l["id"]: l for l in CONF["lots"]}
    pts = [(l["lat"], l["lon"]) for l in CONF["lots"]]
    summary = {"made": dt.datetime.now(CT).isoformat(timespec="minutes"), "storms": [], "checks": {}, "rain": []}
    snow_pairs_lsr, snow_pairs_coco = [], []
    calibrate_units()

    for storm in CONF["storms"]:
        a = parse_local(storm["start"]).astimezone(UTC)
        b = parse_local(storm["end"]).astimezone(UTC)
        log(f"Storm {storm['name']}: {a:%Y-%m-%d %H}Z to {b:%Y-%m-%d %H}Z")
        hours = hours_between(a, b)
        hours_ext = hours_between(a, b + dt.timedelta(hours=18))  # temperatures after the snow, for refreeze
        six = six_hour_ends(a, b)
        # snow analysis at the lots
        six_vals = {}
        for end in six:
            path = nohrsc_file("6h", end)
            if not path:
                continue
            vals = sample_tif(path, pts)
            six_vals[end] = {lid: snow_in(v) for lid, v in zip(lots, vals)}
        # radar precipitation at the lots
        mrms = {}
        for h in hours:
            path = mrms_file(h)
            if not path:
                continue
            mrms[h] = {lid: v for lid, v in zip(lots, sample_mrms(path, pts))}
        obs = asos(list(CONF["stations"]), a - dt.timedelta(hours=1), b + dt.timedelta(hours=19))
        recs = []
        for lid, lot in lots.items():
            rec = build_record(lot, storm, hours_ext, mrms, six, six_vals, obs)
            d = os.path.join(OUT, "records", storm["id"])
            os.makedirs(d, exist_ok=True)
            json.dump(rec, open(os.path.join(d, f"{lid}.json"), "w"), indent=1)
            open(os.path.join(d, f"{lid}.html"), "w").write(record_html(rec))
            recs.append({"lot": lid, "label": lot["label"], "snow": rec["snow_total_in"], "plow": rec["plow_reached"],
                         "ice": rec["ice_in"], "refreeze": rec["refreeze"], "start": rec["start"], "end": rec["end"],
                         "radar_liquid": rec["radar_liquid_in"]})
            log(f"  {lot['label']}: {rec['snow_total_in']} in.; plow at {rec['plow_reached']}; ice {rec['ice_in']}; "
                f"refreeze {rec['refreeze']}; radar water {rec['radar_liquid_in']} in.")
        # checks: storm reports (storm totals so far) against the analysis summed to the report time
        reports = lsr_snow(a, b + dt.timedelta(hours=12))
        if reports:
            rpts = [(r["lat"], r["lon"]) for r in reports]
            per_end = {}
            for end in six:
                path = nohrsc_file("6h", end)
                if path:
                    per_end[end] = [snow_in(v) for v in sample_tif(path, rpts)]
            for i, r in enumerate(reports):
                est = sum((per_end[e][i] or 0) for e in per_end if e <= r["t"] + dt.timedelta(hours=3))
                snow_pairs_lsr.append({"storm": storm["id"], "place": r["place"], "reported": r["inches"],
                                       "analysis": round(est, 1), "lat": r["lat"], "lon": r["lon"]})
        # checks: CoCoRaHS 24-hour snow (about 7 AM) against the 24-hour analysis ending 12 UTC that morning
        day = a.astimezone(CT).date() + dt.timedelta(days=1)
        while day <= b.astimezone(CT).date() + dt.timedelta(days=1):
            end12 = dt.datetime(day.year, day.month, day.day, 12, tzinfo=UTC)
            path = nohrsc_file("24h", end12)
            obsd = [o for o in cocorahs_day(day.isoformat()) if isinstance(o["snow"], (int, float))]
            if path and obsd:
                vals = sample_tif(path, [(o["lat"], o["lon"]) for o in obsd])
                for o, v in zip(obsd, vals):
                    est = snow_in(v)
                    if est is None:
                        continue
                    if o["snow"] == 0 and est < 0.1:
                        continue  # both dry: not a test
                    snow_pairs_coco.append({"storm": storm["id"], "date": day.isoformat(), "name": o["name"],
                                            "reported": o["snow"], "analysis": round(est, 1)})
            day += dt.timedelta(days=1)
        summary["storms"].append({"id": storm["id"], "name": storm["name"], "lots": recs})

    summary["checks"]["snow_vs_storm_reports"] = stats(snow_pairs_lsr)
    summary["checks"]["snow_vs_cocorahs"] = stats(snow_pairs_coco)
    summary["checks"]["pairs_storm_reports"] = snow_pairs_lsr
    summary["checks"]["pairs_cocorahs"] = snow_pairs_coco

    # ---------------- rain at a job site during work hours
    rain = CONF["rain"]
    rpts_ids = rain["sites"]
    rpts = [(lots[i]["lat"], lots[i]["lon"]) for i in rpts_ids]
    w0, w1 = rain["work_hours"]
    for day in rain["days"]:
        d0 = dt.datetime.fromisoformat(day).replace(tzinfo=CT)
        a = (d0 + dt.timedelta(hours=w0)).astimezone(UTC)
        b = (d0 + dt.timedelta(hours=w1)).astimezone(UTC)
        hours = hours_between(a, b)
        vals = {}
        for h in hours:
            path = mrms_file(h)
            if path:
                vals[h] = sample_mrms(path, rpts)
        obs = asos(list(CONF["stations"]), a - dt.timedelta(hours=1), b + dt.timedelta(hours=1))
        for k, lid in enumerate(rpts_ids):
            lot = lots[lid]
            sid, sd = nearest_station(lot["lat"], lot["lon"])
            per = []
            for h in hours:
                cell, mean = vals.get(h, [(None, None)] * len(rpts))[k]
                site = cell if cell is not None else mean
                _, temp, p01 = hour_obs(obs.get(sid, []), h)
                per.append({"t": h.isoformat(), "site_in": None if site is None else round(site, 3),
                            "airport_in": p01, "temp_f": temp})
            site_tot = sum(p["site_in"] or 0 for p in per)
            wet = sum(1 for p in per if (p["site_in"] or 0) >= 0.01)
            ap_tot = sum(p["airport_in"] or 0 for p in per if p["airport_in"] and p["airport_in"] > 0.001)
            ap_wet = sum(1 for p in per if (p["airport_in"] or 0) >= 0.01)
            item = {"day": day, "site": lid, "label": lot["label"], "station": sid, "station_miles": round(sd, 1),
                    "site_rain_in": round(site_tot, 2), "site_wet_hours": wet,
                    "airport_rain_in": round(ap_tot, 2), "airport_wet_hours": ap_wet, "hours": per}
            os.makedirs(os.path.join(OUT, "rain"), exist_ok=True)
            json.dump(item, open(os.path.join(OUT, "rain", f"{lid}-{day}.json"), "w"), indent=1)
            summary["rain"].append({k2: v for k2, v in item.items() if k2 != "hours"})
            log(f"Rain {day} {lot['label']}: site {site_tot:.2f} in. ({wet} wet hours) vs {sid} {ap_tot:.2f} in. ({ap_wet})")

    # radar rain against CoCoRaHS gauges (24 hours ending about 7 AM)
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
        for h in hours_between(end - dt.timedelta(hours=24), end):
            path = mrms_file(h)
            if not path:
                continue
            ok += 1
            for i, (cell, mean) in enumerate(sample_mrms(path, gp)):
                tot[i] += (cell if cell is not None else (mean or 0)) or 0
        if ok < 20:
            continue
        for o, est in zip(gauges, tot):
            if o["precip"] == 0 and est < 0.02:
                continue
            pairs.append({"date": day, "name": o["name"], "gauge": o["precip"], "radar": round(est, 2)})
    summary["checks"]["rain_vs_cocorahs"] = stats(pairs, a="gauge", b="radar")
    summary["checks"]["pairs_rain"] = pairs

    summary["nohrsc_unit_factor"] = NOHRSC_UNITS["factor"]
    summary["seconds"] = round(time.time() - t0)
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1, default=str)
    write_index(summary)
    open(os.path.join(OUT, "summary.txt"), "w").write("\n".join(LOG) + "\n")
    log(f"Done in {summary['seconds']} s")


def stats(pairs, a="reported", b="analysis"):
    if not pairs:
        return {"n": 0}
    d = [p[b] - p[a] for p in pairs]
    ad = [abs(x) for x in d]
    rel = [abs(p[b] - p[a]) / p[a] for p in pairs if p[a] >= 1]
    return {"n": len(d), "mean_diff": round(sum(d) / len(d), 2), "mean_abs_diff": round(sum(ad) / len(ad), 2),
            "median_abs_diff": round(sorted(ad)[len(ad) // 2], 2),
            "within_1": round(sum(1 for x in ad if x <= 1) / len(ad), 2),
            "within_2": round(sum(1 for x in ad if x <= 2) / len(ad), 2),
            "median_rel_err_ge1": round(sorted(rel)[len(rel) // 2], 2) if rel else None}


def write_index(s):
    e = html.escape
    parts = ["<p class=brand>Hard Hat Weather &middot; storm records test</p><div class=card><h1>Storm records: last winter, 5 test lots</h1>"
             f"<p class=muted>Made {e(s['made'])} from public NOAA data. Not live; no customers.</p></div>"]
    for st in s["storms"]:
        rows = "".join(
            f"<tr><td><a href='records/{st['id']}/{l['lot']}.html'>{e(l['label'])}</a></td><td>{l['snow']:.1f}</td>"
            f"<td>{e(fmt_local(dt.datetime.fromisoformat(l['plow'])) if l['plow'] else '-')}</td><td>{l['ice']:.2f}</td>"
            f"<td>{e(fmt_local(dt.datetime.fromisoformat(l['refreeze'])) if l['refreeze'] else '-')}</td></tr>" for l in st["lots"])
        parts.append(f"<div class=card><h2>{e(st['name'])}</h2><div class=scroll><table><tr><th>Lot</th><th>Snow (in.)</th>"
                     f"<th>Plow amount reached</th><th>Ice (in.)</th><th>Refreeze</th></tr>{rows}</table></div></div>")
    c = s["checks"]
    def line(k, label):
        x = c.get(k) or {}
        if not x.get("n"):
            return f"<li>{label}: no pairs</li>"
        return (f"<li>{label}: {x['n']} pairs, typical miss {x['median_abs_diff']} in. (average {x['mean_abs_diff']}), "
                f"within 1 in. {round(100 * x['within_1'])}%, within 2 in. {round(100 * x['within_2'])}%, average difference {x['mean_diff']:+}</li>")
    parts.append("<div class=card><h2>How close it is</h2><ul>"
                 + line("snow_vs_storm_reports", "Snow vs NWS storm reports (storm totals)")
                 + line("snow_vs_cocorahs", "Snow vs CoCoRaHS observers (24 hours)")
                 + line("rain_vs_cocorahs", "Radar rain vs CoCoRaHS rain gauges (24 hours)")
                 + "</ul><p class=muted>The snowfall analysis uses many of these same reports, so the snow check is generous. "
                 "The rain gauges are not part of the radar estimate.</p></div>")
    rr = "".join(f"<tr><td>{e(r['day'])}</td><td>{e(r['label'])}</td><td>{r['site_rain_in']:.2f} ({r['site_wet_hours']} h)</td>"
                 f"<td>{r['airport_rain_in']:.2f} ({r['airport_wet_hours']} h) {e(r['station'])}</td></tr>" for r in s["rain"])
    parts.append(f"<div class=card><h2>Rain during work hours (7 AM-5 PM): job site radar vs nearest airport</h2><div class=scroll><table>"
                 f"<tr><th>Day</th><th>Site</th><th>At the site (wet hours)</th><th>Nearest airport</th></tr>{rr}</table></div></div>")
    open(os.path.join(OUT, "index.html"), "w").write(page("Storm records test", "".join(parts)))


if __name__ == "__main__":
    main()
