#!/usr/bin/env python3
"""Storm grid for Hard Hat Weather's storm records (built Oct. 19, 2026; TEST on the storm-records branch).

Free public NOAA data for NW Indiana and SW Michigan on one fixed regional grid. It knows nothing about any
customer: the Hard Hat sender (private, Google Apps Script) reads these files at each customer's own lots.

  radar/TR-TC.json      the last 48 hours of NOAA MRMS MultiSensor QPE (radar plus rain gauges, 1 hour, 1 km),
                        averaged over each grid cell, one file per tile of 10 x 10 cells: rain at a job site during
                        work hours, for delay records and the rain-out guarantee. (radar.json has all of it, for
                        this job's next run.)
  snow/YYYY-MM-DD/      meta.json and one file per tile that had anything (TR-TC.json, listed in meta.json's
                        "tiles"): the 24 hours ending 12 UTC that morning (6 AM CST, 7 AM CDT): estimated snow by hour in each
                        cell (the NOAA National Snowfall Analysis 24-hour total, split by its 6-hour analyses, spread
                        over each quarter-day by radar or by the nearest airport's reported snow rate, whichever is
                        larger: the method tested on last winter's storms in scripts/storm_records/build.py), the type
                        of precipitation by hour, freezing-rain ice, the airports' hourly temperature and weather (and
                        the hours after, for melting and refreezing), and the measured reports to compare with (NWS
                        storm reports and CoCoRaHS observers).
  index.json            what's there and when it was made.

The grid: 41.00-42.12 N, 87.56-86.04 W, 0.02 degrees (about 2 km); row 0 is the north edge and a cell's index is
row * cols + col, and its tile is "TR-TC" with TR = row // 10 and TC = col // 10. Radar values are thousandths of an
inch in a flat [index, value, index, value, ...] list per hour (cells with none are left out; -1 means no radar data);
snow is hundredths of an inch.

  python3 scripts/storm_grid.py update DIR            the hourly run: new radar hours, and the snow day once NOAA's
                                                      24-hour analysis is out (or from the 6-hour ones after 18 UTC)
  python3 scripts/storm_grid.py backfill DIR DAY...   snow days (and that day's radar, as radar-DAY/TR-TC.json) for
                                                      past dates, for tests
  python3 scripts/storm_grid.py latency DIR           when NOAA's latest files appeared (Last-Modified), for timing
"""
import datetime as dt
import gzip
import json
import math
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings

import numpy as np

UTC = dt.timezone.utc
H1, H6, H24 = dt.timedelta(hours=1), dt.timedelta(hours=6), dt.timedelta(hours=24)
UA = {"User-Agent": "laporteweathernow.com storm grid (GitHub Actions; laporteweathernow@gmail.com)"}
CACHE = os.environ.get("STORM_CACHE", "/tmp/storm-grid-cache")

GRID = {"north": 42.12, "south": 41.00, "west": -87.56, "east": -86.04, "step": 0.02}
ROWS = int(round((GRID["north"] - GRID["south"]) / GRID["step"]))
COLS = int(round((GRID["east"] - GRID["west"]) / GRID["step"]))
GRID.update(rows=ROWS, cols=COLS)
LAT = GRID["north"] - (np.arange(ROWS) + 0.5) * GRID["step"]
LON = GRID["west"] + (np.arange(COLS) + 0.5) * GRID["step"]
NCELL = ROWS * COLS
TILE = 10
TROWS, TCOLS = -(-ROWS // TILE), -(-COLS // TILE)
GRID.update(tile=TILE, tileRows=TROWS, tileCols=TCOLS)
TILES = [f"{tr}-{tc}" for tr in range(TROWS) for tc in range(TCOLS)]

# Airports with hourly reports (IEM's ASOS archive). Michigan City's rain gauge read 0.00 on every rainy day
# checked in Sept.-Oct. 2026, so it's marked as not measuring rain (its weather and temperature are fine).
STATIONS = {
    "MGC": {"name": "Michigan City airport", "lat": 41.7033, "lon": -86.8212, "precip": False},
    "PPO": {"name": "La Porte airport", "lat": 41.5725, "lon": -86.7345, "precip": True},
    "VPZ": {"name": "Valparaiso airport", "lat": 41.4540, "lon": -87.0071, "precip": True},
    "SBN": {"name": "South Bend airport", "lat": 41.7072, "lon": -86.3164, "precip": True},
    "GYY": {"name": "Gary airport", "lat": 41.6163, "lon": -87.4128, "precip": True},
    "OXI": {"name": "Starke County airport (Knox)", "lat": 41.3301, "lon": -86.6647, "precip": True},
    "BEH": {"name": "Benton Harbor airport", "lat": 42.1286, "lon": -86.4285, "precip": True},
}
RADAR_HOURS = 48          # radar.json keeps this many hours
KEEP_SNOW_DAYS = 14       # snow days kept on the data branch
FETCH_PER_RUN = 50        # radar files per hourly run (the first run fills 48)
SNOW_WAIT = 6             # hours after 12 UTC to wait for the 24-hour analysis before using the 6-hour ones
TYPE_CODE = {"snow": "S", "snow?": "s", "sleet": "P", "freezing rain": "Z", "rain": "R", "": "."}
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def iso(t):
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


def parse_iso(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)


def floor_hour(t):
    return t.replace(minute=0, second=0, microsecond=0)


def get(url, dest=None, tries=3, timeout=90, quiet404=False):
    """Bytes of url, or the cached path when dest is given; None when it isn't there."""
    if dest and os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
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
            if e.code in (403, 404):    # not there (S3 answers 403 or 404 for a missing file)
                if not quiet404:
                    log(f"  - not there yet: {url.rsplit('/', 1)[-1]}")
                return None
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(2 * (i + 1))
    log(f"  ! could not get {url}: {last}")
    return None


def miles(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    x = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(x))


def in_grid(lat, lon):
    return GRID["south"] <= lat < GRID["north"] and GRID["west"] <= lon < GRID["east"]


# ---------------------------------------------------------------- NOAA National Snowfall Analysis (GeoTIFF, inches)

def nohrsc_path(kind, end, quiet=False):
    name = f"sfav2_CONUS_{kind}_{end:%Y%m%d%H}.tif"
    return get(f"https://www.nohrsc.noaa.gov/snowfall_v2/data/{end:%Y%m}/{name}", os.path.join(CACHE, "nohrsc", name),
               quiet404=quiet)


def nohrsc_cells(path):
    """The analysis at each cell center (nearest analysis pixel), inches; NaN where it has no value."""
    import rasterio
    with rasterio.open(path) as ds:
        band = ds.read(1, masked=True)
        lon2, lat2 = np.meshgrid(LON, LAT)
        cf, rf = (~ds.transform) * (lon2, lat2)
        r, c = np.floor(rf).astype(int), np.floor(cf).astype(int)
        ok = (r >= 0) & (r < band.shape[0]) & (c >= 0) & (c < band.shape[1])
        out = np.full((ROWS, COLS), np.nan)
        vals = np.ma.filled(band[np.clip(r, 0, band.shape[0] - 1), np.clip(c, 0, band.shape[1] - 1)].astype(float), np.nan)
        out[ok] = vals[ok]
        out[(out < 0) | (out > 200)] = np.nan
        if "crs" not in GRID_INFO:
            GRID_INFO["nohrsc"] = {"crs": str(ds.crs), "res": [abs(ds.transform.a), abs(ds.transform.e)]}
            GRID_INFO["crs"] = True
    return out


GRID_INFO = {}


# ---------------------------------------------------------------- NOAA MRMS radar + gauge precipitation (GRIB2)

def mrms_path(end, passes=(2, 1)):
    for p in passes:
        key = (f"CONUS/MultiSensor_QPE_01H_Pass{p}_00.00/{end:%Y%m%d}/"
               f"MRMS_MultiSensor_QPE_01H_Pass{p}_00.00_{end:%Y%m%d-%H}0000.grib2.gz")
        path = get(f"https://noaa-mrms-pds.s3.amazonaws.com/{key}", os.path.join(CACHE, "mrms", os.path.basename(key)),
                   tries=2, quiet404=True)
        if path:
            return path, p
    return None, 0


def mrms_cells(path):
    """Precipitation (inches) in each cell: the mean of the 1 km MRMS pixels inside it (NaN where MRMS has none)."""
    import pygrib
    raw = path[:-3] + ".tmp"
    with gzip.open(path, "rb") as fi, open(raw, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    grbs = pygrib.open(raw)
    g = grbs.message(1)
    lat1, lon1 = g["latitudeOfFirstGridPointInDegrees"], g["longitudeOfFirstGridPointInDegrees"]
    d, jpos = g["iDirectionIncrementInDegrees"], g["jScansPositively"]
    vals = g.values
    grbs.close()
    os.remove(raw)
    k = int(round(GRID["step"] / d))
    if abs(k * d - GRID["step"]) > 1e-6:
        raise RuntimeError(f"MRMS spacing {d} doesn't divide the grid step")
    north_c, south_c = GRID["north"] - d / 2, GRID["south"] + d / 2
    if jpos:
        r0, r1 = int(round((south_c - lat1) / d)), int(round((north_c - lat1) / d)) + 1
    else:
        r0, r1 = int(round((lat1 - north_c) / d)), int(round((lat1 - south_c) / d)) + 1
    c0 = int(round((((GRID["west"] + d / 2) % 360) - lon1) / d))
    sub = np.ma.filled(np.ma.asarray(vals[r0:r1, c0:c0 + COLS * k], dtype=float), np.nan)
    if jpos:
        sub = sub[::-1]
    if sub.shape != (ROWS * k, COLS * k):
        raise RuntimeError(f"MRMS crop {sub.shape} isn't {(ROWS * k, COLS * k)}")
    sub[sub < 0] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        cells = np.nanmean(sub.reshape(ROWS, k, COLS, k), axis=(1, 3)) / 25.4
    if "mrms" not in GRID_INFO:
        GRID_INFO["mrms"] = {"lat1": lat1, "lon1": lon1, "d": d, "jpos": jpos, "rows": [r0, r1], "col0": c0}
    return cells


def encode_hour(cells):
    """Flat [index, thousandths, ...] for cells with 0.001 in. or more; -1 for cells with no radar data."""
    flat = cells.reshape(-1)
    v = np.where(np.isnan(flat), -1, np.rint(flat * 1000)).astype(np.int64)
    idx = np.nonzero(v != 0)[0]
    out = np.empty(idx.size * 2, dtype=np.int64)
    out[0::2], out[1::2] = idx, v[idx]
    return out.tolist()


def decode_hour(flat):
    """Back to inches by cell (NaN for no data)."""
    a = np.zeros(NCELL)
    f = np.asarray(flat, dtype=np.int64).reshape(-1, 2) if flat else np.zeros((0, 2), dtype=np.int64)
    if f.size:
        a[f[:, 0]] = np.where(f[:, 1] < 0, np.nan, f[:, 1] / 1000.0)
    return a.reshape(ROWS, COLS)


def load_radar(path):
    try:
        with open(path, encoding="utf-8") as f:
            o = json.load(f)
        if o.get("grid", {}).get("rows") != ROWS or o.get("grid", {}).get("cols") != COLS:
            log("  radar.json is on another grid; starting over")
            return {}
        return {k: {"p": v["p"], "v": v["v"]} for k, v in o.get("hours", {}).items()}
    except (OSError, ValueError):
        return {}


def save_radar(path, store):
    hours = {k: store[k] for k in sorted(store)}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"about": "NOAA MRMS MultiSensor QPE, 1-hour (Pass 2, or Pass 1 until Pass 2 is out), mean over each "
                            "cell; keys are each hour's END (UTC); v = [cell, thousandths of an inch, ...]; -1 = no data",
                   "grid": GRID, "hours": hours}, f, separators=(",", ":"))


def tile_name(idx):
    r, c = divmod(int(idx), COLS)
    return f"{r // TILE}-{c // TILE}"


def write_radar_tiles(tdir, store):
    """One file per tile, every tile, with every hour (an hour with nothing in that tile has an empty list)."""
    keys = sorted(store)
    per = {k: {} for k in keys}
    for k in keys:
        flat = store[k]["v"]
        for i in range(0, len(flat), 2):
            per[k].setdefault(tile_name(flat[i]), []).extend(flat[i:i + 2])
    for name in TILES:
        write_json(os.path.join(tdir, f"{name}.json"), {
            "grid": GRID, "tile": name, "from": keys[0] if keys else None, "to": keys[-1] if keys else None,
            "hours": {k: {"p": store[k]["p"], "v": per[k].get(name, [])} for k in keys}})


def write_snow_day(sdir, obj):
    """snow/DAY/: one file per tile with anything in it, then meta.json (listing them) last."""
    d = os.path.join(sdir, obj["day"])
    if os.path.isdir(d):
        shutil.rmtree(d)
    tiles = {}
    for i, idx in enumerate(obj["cells"]):
        t = tiles.setdefault(tile_name(idx), {"cells": [], "snow": [], "type": [], "ice": []})
        t["cells"].append(idx)
        t["snow"].append(obj["snow"][i])
        t["type"].append(obj["type"][i])
        t["ice"].append(obj["ice"][i])
    for name, t in tiles.items():
        write_json(os.path.join(d, f"{name}.json"), dict(t, day=obj["day"], tile=name))
    meta = {k: v for k, v in obj.items() if k not in ("cells", "snow", "type", "ice")}
    meta["tiles"] = sorted(tiles)
    write_json(os.path.join(d, "meta.json"), meta)


def fetch_radar_hour(store, end, passes=(2, 1)):
    path, p = mrms_path(end, passes)
    if not path:
        return False
    try:
        store[iso(end)] = {"p": p, "v": encode_hour(mrms_cells(path))}
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    return True


# ---------------------------------------------------------------- airports (IEM ASOS archive)

def asos(a, b):
    q = [("station", s) for s in STATIONS] + [("data", x) for x in ("tmpf", "wxcodes", "p01i")] + [
        ("year1", a.year), ("month1", a.month), ("day1", a.day), ("hour1", a.hour), ("minute1", 0),
        ("year2", b.year), ("month2", b.month), ("day2", b.day), ("hour2", b.hour), ("minute2", 0),
        ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "no"), ("missing", "M"), ("trace", "T")]
    body = get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?" + urllib.parse.urlencode(q), timeout=120)
    obs = {s: [] for s in STATIONS}
    if not body:
        return obs
    lines = body.decode("utf-8", "replace").strip().splitlines()
    if not lines:
        return obs
    head = lines[0].split(",")
    for line in lines[1:]:
        row = dict(zip(head, line.split(",")))
        s = row.get("station")
        if s not in obs:
            continue
        try:
            t = dt.datetime.strptime(row["valid"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
        except (KeyError, ValueError):
            continue
        tmpf = None if row.get("tmpf") in ("M", "", None) else float(row["tmpf"])
        obs[s].append({"t": t, "tmpf": tmpf, "wx": "" if row.get("wxcodes") in ("M", None) else row["wxcodes"]})
    return obs


def hour_obs(rows, end):
    """Weather codes reported in the hour ending `end`, and its last temperature."""
    inside = [o for o in rows if end - H1 < o["t"] <= end + dt.timedelta(minutes=5)]
    wx = " ".join(dict.fromkeys(c for o in inside for c in o["wx"].split() if c))
    temps = [o["tmpf"] for o in inside if o["tmpf"] is not None]
    return wx, (temps[-1] if temps else None)


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
    """Typical water rate (in./hour) for the heaviest snow or sleet the airport reported that hour."""
    best = 0.0
    for c in (wx or "").split():
        bare = c.lstrip("+-")
        if ("SN" in bare or "PL" in bare or "SG" in bare) and bare not in ("BLSN", "DRSN"):
            best = max(best, 0.04 if c.startswith("+") else (0.01 if c.startswith("-") else 0.02))
    return best


# ---------------------------------------------------------------- measured reports to compare with

def lsr_snow(a, b):
    q = urllib.parse.urlencode({"wfos": "IWX,LOT", "sts": f"{a:%Y-%m-%dT%H:%MZ}", "ets": f"{b:%Y-%m-%dT%H:%MZ}"})
    body = get(f"https://mesonet.agron.iastate.edu/geojson/lsr.geojson?{q}")
    out = []
    for f in (json.loads(body).get("features", []) if body else []):
        p = f.get("properties") or {}
        if str(p.get("typetext") or "").upper() not in ("SNOW", "HEAVY SNOW") and p.get("type") != "S":
            continue
        try:
            inches = float(p.get("magnitude"))
            lon, lat = f["geometry"]["coordinates"][:2]
            t = dt.datetime.fromisoformat(str(p.get("valid")).replace("Z", "+00:00"))
        except (TypeError, ValueError, KeyError):
            continue
        if inches < 0 or not in_grid(lat, lon):
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
        out.append({"kind": "NWS storm report", "lat": round(lat, 4), "lon": round(lon, 4), "in": inches, "t": iso(t),
                    "place": str(p.get("city") or "").strip(), "source": str(p.get("source") or "").strip(),
                    "remark": str(p.get("remark") or "").strip()[:160]})
    return out


def cocorahs(date):
    out = []
    for net in ("IN_COCORAHS", "MI_COCORAHS"):
        body = get(f"https://mesonet.agron.iastate.edu/api/1/daily.geojson?network={net}&date={date}")
        for f in (json.loads(body).get("features", []) if body else []):
            p = f.get("properties") or {}
            try:
                lon, lat = f["geometry"]["coordinates"][:2]
            except (TypeError, KeyError, ValueError):
                continue
            snow = p.get("snow")
            if snow is None or not in_grid(lat, lon):
                continue
            try:
                snow = float(snow)
            except (TypeError, ValueError):
                continue
            if snow < 0:      # IEM marks a trace as a tiny value or a negative code; skip codes
                continue
            out.append({"kind": "CoCoRaHS", "lat": round(lat, 4), "lon": round(lon, 4), "in": snow,
                        "date": date, "name": str(p.get("name") or "").strip(), "id": str(p.get("station") or "")})
    return out


# ---------------------------------------------------------------- one snow day on the grid

def nearest_station_index(names):
    lat2, lon2 = np.meshgrid(LAT, LON, indexing="ij")
    best, which = np.full((ROWS, COLS), np.inf), np.zeros((ROWS, COLS), dtype=int)
    for i, s in enumerate(names):
        st = STATIONS[s]
        dy = (lat2 - st["lat"]) * 69.0
        dx = (lon2 - st["lon"]) * 69.0 * math.cos(math.radians(41.6))
        dist = np.hypot(dx, dy)
        closer = dist < best
        best[closer], which[closer] = dist[closer], i
    return which


def snow_day(day, store, now):
    """The snow file for the 24 hours ending 12 UTC on `day` (a date), from the radar hours in `store`."""
    e = dt.datetime(day.year, day.month, day.day, 12, tzinfo=UTC)
    hours = [e - H24 + H1 * (i + 1) for i in range(24)]
    subs = [e - H6 * k for k in (3, 2, 1, 0)]
    p24 = nohrsc_path("24h", e)
    v24 = nohrsc_cells(p24) if p24 else None
    v6 = []
    for x in subs:
        p6 = nohrsc_path("6h", x)
        v6.append(nohrsc_cells(p6) if p6 else None)
    have6 = [v is not None for v in v6]
    radar = np.stack([decode_hour(store[iso(h)]["v"]) if iso(h) in store else np.full((ROWS, COLS), np.nan) for h in hours])
    radar_ok = [iso(h) in store for h in hours]
    after_to = min(now, e + dt.timedelta(hours=18))
    obs = asos(e - H24 - H1, max(after_to, e + H1))
    names = list(STATIONS)
    st_hours = {}
    for s in names:
        rows = []
        h = e - H24 + H1
        while h <= after_to:
            wx, temp = hour_obs(obs[s], h)
            rows.append([iso(h), None if temp is None else round(temp), wx])
            h += H1
        st_hours[s] = rows
    near = nearest_station_index(names)
    wx_by = {s: [st_hours[s][i][2] for i in range(24)] for s in names}
    tp_by = {s: [st_hours[s][i][1] for i in range(24)] for s in names}
    # the day's total in each cell: the 24-hour analysis, or the four 6-hour ones added up
    six = np.stack([v if v is not None else np.zeros((ROWS, COLS)) for v in v6])
    six = np.nan_to_num(six, nan=0.0)
    if v24 is not None:
        total = np.where(np.isnan(v24), six.sum(axis=0), v24)
        snow_ok = True
    elif all(have6):
        total = six.sum(axis=0)
        snow_ok = True
    else:
        total = np.zeros((ROWS, COLS))
        snow_ok = False
    total = np.where(total < 0.05, 0.0, total)
    cells, snow_rows, type_rows, ice = [], [], [], []
    rad0 = np.nan_to_num(radar, nan=0.0)
    for r in range(ROWS):
        for c in range(COLS):
            liquid = rad0[:, r, c]
            day_total = float(total[r, c])
            if day_total <= 0 and liquid.max() < 0.005:
                continue
            s = names[near[r, c]]
            types = [ptype(wx_by[s][i], tp_by[s][i], liquid[i]) for i in range(24)]
            snow = np.zeros(24)
            if day_total > 0:
                s6 = six[:, r, c]
                if s6.sum() > 0:
                    shares = s6 / s6.sum()
                else:
                    w = np.array([liquid[q * 6:(q + 1) * 6].sum() for q in range(4)])
                    shares = w / w.sum() if w.sum() > 0 else np.full(4, 0.25)
                for q in range(4):
                    amt = day_total * shares[q]
                    if amt <= 0:
                        continue
                    hrs = list(range(q * 6, (q + 1) * 6))
                    pool = [i for i in hrs if types[i] in ("snow", "snow?", "sleet")] or \
                           [i for i in hrs if liquid[i] > 0] or hrs
                    w = np.array([max(liquid[i], airport_rate(wx_by[s][i])) for i in pool])
                    if w.sum() <= 0:
                        w = np.ones(len(pool))
                    for i, wi in zip(pool, w):
                        snow[i] += amt * wi / w.sum()
            code = "".join(TYPE_CODE.get(types[i], ".") if (snow[i] >= 0.005 or liquid[i] >= 0.005) else "."
                           for i in range(24))
            zr = sum(liquid[i] for i in range(24) if types[i] == "freezing rain" and liquid[i] >= 0.005)
            if day_total <= 0 and code.strip(".") == "":
                continue
            cells.append(r * COLS + c)
            snow_rows.append([int(round(x * 100)) for x in snow])
            type_rows.append(code)
            ice.append(int(round(zr * 100)))
    reports = lsr_snow(e - H24, e + dt.timedelta(hours=3)) + cocorahs(day.isoformat())
    return {
        "about": "Estimated snow by hour (hundredths of an inch) in each cell for the 24 hours ending 12 UTC; type by "
                 "hour: S snow, s snow (no airport report; from temperature), P sleet, Z freezing rain, R rain, . none; "
                 "ice = freezing-rain water (hundredths); cells with nothing are left out.",
        "day": day.isoformat(), "end": iso(e), "made": iso(now), "grid": GRID,
        "hours": [iso(h) for h in hours],
        "source": {"snowOk": snow_ok, "nohrsc24": v24 is not None, "nohrsc6": sum(have6),
                   "radarHours": sum(radar_ok), "radarPass2": sum(1 for h in hours if store.get(iso(h), {}).get("p") == 2)},
        "maxSnow": round(float(total.max()), 1),
        "cells": cells, "snow": snow_rows, "type": type_rows, "ice": ice,
        "stations": {s: dict(STATIONS[s], obs=st_hours[s]) for s in names},
        "reports": reports,
    }


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "w", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"))
    os.replace(path + ".part", path)


# ---------------------------------------------------------------- the hourly run

def update(outdir, now=None):
    now = now or dt.datetime.now(UTC)
    rpath = os.path.join(outdir, "radar.json")
    store = load_radar(rpath)
    oldest = floor_hour(now) - H1 * RADAR_HOURS
    store = {k: v for k, v in store.items() if parse_iso(k) > oldest}
    newest = floor_hour(now - dt.timedelta(minutes=65))
    want = []
    h = newest
    while h > oldest:
        want.append(h)
        h -= H1
    fetched = upgraded = 0
    for h in want:           # newest first: delay records need today's hours soonest
        if fetched >= FETCH_PER_RUN:
            break
        have = store.get(iso(h))
        if have and have["p"] == 2:
            continue
        if have and now - h < dt.timedelta(minutes=110):
            continue         # Pass 2 usually comes about two hours after the hour
        ok = fetch_radar_hour(store, h, passes=(2,) if have else (2, 1))
        if ok:
            fetched += 1
            upgraded += 1 if have else 0
    log(f"radar: {len(store)} hours kept, {fetched} fetched ({upgraded} upgraded to Pass 2)")
    save_radar(rpath, store)
    write_radar_tiles(os.path.join(outdir, "radar"), store)
    # snow days: the latest three 12 UTC ends
    last12 = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if last12 > now:
        last12 -= H24
    made = []
    for back in range(3):
        e = last12 - H24 * back
        day = e.date()
        if os.path.exists(os.path.join(outdir, "snow", day.isoformat(), "meta.json")):
            continue
        hours_in = all(iso(e - H24 + H1 * (i + 1)) in store for i in range(24))
        p24 = nohrsc_path("24h", e, quiet=True)
        late = now - e >= dt.timedelta(hours=SNOW_WAIT)
        if (p24 and hours_in) or late:
            obj = snow_day(day, store, now)
            write_snow_day(os.path.join(outdir, "snow"), obj)
            made.append(day.isoformat())
            log(f"snow day {day}: made (24-hour analysis {'yes' if obj['source']['nohrsc24'] else 'no'}, "
                f"{obj['source']['radarHours']} radar hours, max {obj['maxSnow']} in.)")
        else:
            log(f"snow day {day}: waiting ({'analysis out' if p24 else 'no 24-hour analysis yet'}, "
                f"{'radar complete' if hours_in else 'radar hours missing'})")
    sdir = os.path.join(outdir, "snow")
    days = sorted(f for f in os.listdir(sdir) if os.path.exists(os.path.join(sdir, f, "meta.json"))) if os.path.isdir(sdir) else []
    for d in days[:-KEEP_SNOW_DAYS]:
        shutil.rmtree(os.path.join(sdir, d))
    days = days[-KEEP_SNOW_DAYS:]
    keys = sorted(store)
    write_json(os.path.join(outdir, "index.json"), {
        "made": iso(now), "grid": GRID,
        "radar": {"from": keys[0] if keys else None, "to": keys[-1] if keys else None, "hours": len(keys),
                  "pass2": sum(1 for k in keys if store[k]["p"] == 2)},
        "snowDays": days, "madeThisRun": made})
    return made


# ---------------------------------------------------------------- tests and timing

def backfill(outdir, days):
    for d in days:
        day = dt.date.fromisoformat(d)
        e = dt.datetime(day.year, day.month, day.day, 12, tzinfo=UTC)
        store = {}
        for i in range(24):
            h = e - H24 + H1 * (i + 1)
            if not fetch_radar_hour(store, h, passes=(2, 1)):
                log(f"  ! no radar for {iso(h)}")
        write_radar_tiles(os.path.join(outdir, f"radar-{d}"), store)
        obj = snow_day(day, store, e + dt.timedelta(hours=18))
        write_snow_day(os.path.join(outdir, "snow"), obj)
        log(f"{d}: {len(obj['cells'])} cells with something, max {obj['maxSnow']} in., source {obj['source']}")
    with open(os.path.join(outdir, "grid-info.json"), "w", encoding="utf-8") as f:
        json.dump(GRID_INFO, f, indent=1, default=str)


def head_time(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.headers.get("Last-Modified")
    except Exception as e:  # noqa: BLE001
        return f"none ({str(e)[:60]})"


def latency(outdir):
    now = dt.datetime.now(UTC)
    lines = [f"Checked {iso(now)}"]
    last12 = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if last12 > now:
        last12 -= H24
    for back in range(3):
        e = last12 - H24 * back
        for kind, ends in (("24h", [e]), ("6h", [e - H6 * k for k in (3, 2, 1, 0)])):
            for x in ends:
                name = f"sfav2_CONUS_{kind}_{x:%Y%m%d%H}.tif"
                lines.append(f"NOHRSC {kind} ending {iso(x)}: {head_time(f'https://www.nohrsc.noaa.gov/snowfall_v2/data/{x:%Y%m}/{name}')}")
    h = floor_hour(now)
    for back in range(1, 7):
        x = h - H1 * back
        for p in (1, 2):
            key = (f"CONUS/MultiSensor_QPE_01H_Pass{p}_00.00/{x:%Y%m%d}/"
                   f"MRMS_MultiSensor_QPE_01H_Pass{p}_00.00_{x:%Y%m%d-%H}0000.grib2.gz")
            lines.append(f"MRMS Pass{p} ending {iso(x)}: {head_time('https://noaa-mrms-pds.s3.amazonaws.com/' + key)}")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "latency.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log("\n".join(lines))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    mode, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    try:
        if mode == "update":
            update(outdir)
        elif mode == "backfill":
            backfill(outdir, sys.argv[3:])
        elif mode == "latency":
            latency(outdir)
        else:
            print(__doc__)
            return 2
    finally:
        with open(os.path.join(outdir, "log.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(LOG) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
