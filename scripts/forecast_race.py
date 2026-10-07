#!/usr/bin/env python3
"""The Forecast Race: NOAA's new AI weather model against the National Weather Service's own
forecasters (and three other computer models), graded every day at the La Porte airport (KPPO).

Each morning (about 5:30 AM Central) this saves what each racer says about TOMORROW in La Porte:
  - the temperature at four checkpoints: 06, 12, 18 and 00 UTC (1 AM, 7 AM, 1 PM and 7 PM in summer
    time; midnight, 6 AM, noon and 6 PM in winter time), the times every model reports;
  - the rain total for the 24 hours from 06 UTC to 06 UTC (1 AM to 1 AM in summer time).
The next morning it grades each racer against what KPPO recorded, and keeps a leaderboard.

Racers (all free, public data; nothing here is our own forecast):
  nws    The National Weather Service's official forecast: the forecast grids its forecasters
         publish (National Digital Forecast Database), as they stood at 5:30 AM Central.
         Source: NOAA Open Data on AWS (noaa-ndfd-pds).
  aigfs  NOAA's AI Global Forecast System (AIGFS), its AI model, operational since Dec. 17, 2025.
         The 00 UTC run, from NOAA's NOMADS server.
  gfs    NOAA's regular Global Forecast System (GFS), 00 UTC run, from NOMADS.
  aifs   ECMWF's AI model (AIFS Single), 00 UTC run, from ECMWF open data (CC BY 4.0).
  ifs    ECMWF's regular model (IFS), 00 UTC run, from ECMWF open data (CC BY 4.0).

Rules: forecasts are saved once and never changed. A racer that's missing a forecast on a day just
isn't scored that day. Model values are interpolated to the airport's spot; the Weather Service grid
point nearest the airport is used. Observations: KPPO via the Iowa Environmental Mesonet.

Usage:
  python3 scripts/forecast_race.py              # morning run: save today's forecasts if due, grade, rebuild
  python3 scripts/forecast_race.py force        # save today's forecasts now, whatever the hour
  python3 scripts/forecast_race.py backfill 2026-09-27 2026-10-05
        # fill in forecasts made on those mornings from the public archives (marked "backfilled")
"""
import datetime as dt
import json
import math
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
UTC = dt.timezone.utc
OUT = "race.json"
STATION = {"id": "KPPO", "iem": "PPO", "network": "IN_ASOS", "name": "La Porte Municipal Airport",
           "lat": 41.5725, "lon": -86.7345}
UA = {"User-Agent": "LaPorteWeatherNow/1.0 (laporteweathernow.com; laporteweathernow@gmail.com)"}
CHECK_HOURS = [6, 12, 18, 24]            # UTC hours after the target date's 00 UTC (24 = next 00 UTC)
LEADS = [30, 36, 42, 48]                 # from the 00 UTC run the morning before
RAIN_LEADS = (30, 54)                    # 06 UTC tomorrow to 06 UTC the day after
SAVE_FROM = dt.time(5, 30)               # local time the morning save may start
NDFD_CUTOFF = dt.time(5, 30)             # the Weather Service forecast "as it stood" at this local time
HIT_DEGREES = 3

RACERS = [
    {"id": "nws", "name": "Weather Service forecasters", "short": "Weather Service", "kind": "people",
     "about": "The National Weather Service's official forecast for the spot, made by its forecasters (Northern Indiana office), as it stood at 5:30 AM.",
     "source": "NWS National Digital Forecast Database, NOAA Open Data on AWS", "link": "https://registry.opendata.aws/noaa-ndfd/"},
    {"id": "aigfs", "name": "NOAA's AI model (AIGFS)", "short": "NOAA AI", "kind": "ai",
     "about": "NOAA's Artificial Intelligence Global Forecast System, in use since Dec. 17, 2025. The run that starts at 7 PM Central the evening before (6 PM in winter).",
     "source": "NOAA NOMADS", "link": "https://nomads.ncep.noaa.gov/"},
    {"id": "gfs", "name": "NOAA's regular model (GFS)", "short": "NOAA GFS", "kind": "physics",
     "about": "The Global Forecast System, NOAA's main physics-based computer model. Same run time as the AI.",
     "source": "NOAA NOMADS", "link": "https://nomads.ncep.noaa.gov/"},
    {"id": "aifs", "name": "Europe's AI model (AIFS)", "short": "Europe AI", "kind": "ai",
     "about": "The European Centre for Medium-Range Weather Forecasts' AI model (AIFS Single). Same run time.",
     "source": "ECMWF open data (CC BY 4.0)", "link": "https://www.ecmwf.int/en/forecasts/datasets/open-data"},
    {"id": "ifs", "name": "Europe's regular model (ECMWF)", "short": "Europe ECMWF", "kind": "physics",
     "about": "ECMWF's physics-based model (IFS), long rated one of the world's best. Same run time.",
     "source": "ECMWF open data (CC BY 4.0)", "link": "https://www.ecmwf.int/en/forecasts/datasets/open-data"},
]
RACER_IDS = [r["id"] for r in RACERS]


# ---------------------------------------------------------------- helpers
def get(url, rng=None, timeout=90, tries=3):
    headers = dict(UA)
    if rng:
        headers["Range"] = rng
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(4 * (i + 1))
    raise last


def k_to_f(k):
    return (k - 273.15) * 9 / 5 + 32


def r1(x):
    return None if x is None else math.floor(x * 10 + 0.5) / 10


def r2(x):
    return None if x is None else math.floor(x * 100 + 0.5) / 100


def iso(t):
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


def local_label(t):
    lt = t.astimezone(CENTRAL)
    h = lt.hour % 12 or 12
    if lt.hour == 0:
        return "midnight"
    if lt.hour == 12:
        return "noon"
    return f"{h} {'AM' if lt.hour < 12 else 'PM'}"


def checkpoints(target):
    base = dt.datetime(target.year, target.month, target.day, tzinfo=UTC)
    return [base + dt.timedelta(hours=h) for h in CHECK_HOURS]


def rain_window(target):
    base = dt.datetime(target.year, target.month, target.day, tzinfo=UTC)
    return base + dt.timedelta(hours=6), base + dt.timedelta(hours=30)


def bilinear(lats, lons, vals, lat, lon):
    """Interpolate a regular lat/lon grid (1-D axes, any order) to one point."""
    import numpy as np
    lats = np.asarray(lats); lons = np.asarray(lons)
    if lons.max() > 180 and lon < 0:
        lon += 360
    def bracket(axis, x):
        order = np.argsort(axis)
        a = axis[order]
        i = int(np.searchsorted(a, x))
        i = min(max(i, 1), len(a) - 1)
        x0, x1 = a[i - 1], a[i]
        w = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        return order[i - 1], order[i], w
    i0, i1, wy = bracket(lats, lat)
    j0, j1, wx = bracket(lons, lon)
    v = vals
    top = v[i0, j0] * (1 - wx) + v[i0, j1] * wx
    bot = v[i1, j0] * (1 - wx) + v[i1, j1] * wx
    return float(top * (1 - wy) + bot * wy)


def grib_messages(blob):
    import pygrib
    with tempfile.NamedTemporaryFile(suffix=".grb2", delete=False) as f:
        f.write(blob)
        path = f.name
    try:
        g = pygrib.open(path)
        msgs = list(g)
        out = []
        for m in msgs:
            out.append(m)
        return out, g, path
    except Exception:
        os.unlink(path)
        raise


_nearest = {}
def point_value(m, lat=STATION["lat"], lon=STATION["lon"]):
    """Value at the station: bilinear on regular lat/lon grids, nearest grid point otherwise."""
    import numpy as np
    vals = m.values
    if m.gridType == "regular_ll":
        lats, lons = m.distinctLatitudes, m.distinctLongitudes
        return bilinear(lats, lons, np.asarray(vals), lat, lon)
    sig = (m.gridType, m.Ni, m.Nj, round(float(m.latitudeOfFirstGridPointInDegrees), 4),
           round(float(m.longitudeOfFirstGridPointInDegrees), 4))
    if sig not in _nearest:
        la, lo = m.latlons()
        d = (la - lat) ** 2 + (lo - (lon if lo.max() <= 180 else lon % 360)) ** 2
        j = np.unravel_index(np.argmin(d), d.shape)
        _nearest[sig] = (j, float(la[j]), float(lo[j]))
        print(f"    nearest {m.gridType} point to {STATION['id']}: {_nearest[sig][1]:.4f}, {_nearest[sig][2]:.4f}")
    return float(vals[_nearest[sig][0]])


def ncep_idx_ranges(base_url):
    lines = get(base_url + ".idx").decode().splitlines()
    rows = [l.split(":") for l in lines if l.strip()]
    out = []
    for i, r in enumerate(rows):
        start = int(r[1])
        end = int(rows[i + 1][1]) - 1 if i + 1 < len(rows) else None
        out.append((":" + ":".join(r[3:]), start, end))
    return out


def fetch_ncep_field(base_url, want):
    for desc, start, end in ncep_idx_ranges(base_url):
        if want in desc:
            return get(base_url, rng=f"bytes={start}-{'' if end is None else end}")
    raise KeyError(f"{want} not in {base_url}")


# ---------------------------------------------------------------- racers
def run_time(made):
    """The model run used for forecasts made on local date `made`: 00 UTC that day."""
    return dt.datetime(made.year, made.month, made.day, tzinfo=UTC)


def fc_aigfs(made, target):
    run = run_time(made)
    temps = []
    base = lambda f: (f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/aigfs/prod/aigfs.{run:%Y%m%d}/00/"
                      f"model/atmos/grib2/aigfs.t00z.sfc.f{f:03d}.grib2")
    for f in LEADS:
        msgs, g, p = grib_messages(fetch_ncep_field(base(f), ":TMP:2 m above ground:"))
        temps.append(r1(k_to_f(point_value(msgs[0])))); g.close(); os.unlink(p)
    acc = []
    for f in RAIN_LEADS:
        msgs, g, p = grib_messages(fetch_ncep_field(base(f), f":APCP:surface:0-{f} hour acc"))
        acc.append(point_value(msgs[0])); g.close(); os.unlink(p)
    return {"temps": temps, "rainIn": r2(max(0.0, acc[1] - acc[0]) / 25.4), "run": iso(run)}


def fc_gfs(made, target):
    run = run_time(made)
    temps, acc = [], {}
    for f in sorted(set(LEADS) | set(RAIN_LEADS)):
        url = ("https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?dir=%2Fgfs." + f"{run:%Y%m%d}" +
               "%2F00%2Fatmos&file=gfs.t00z.pgrb2.0p25.f" + f"{f:03d}" +
               "&var_TMP=on&lev_2_m_above_ground=on&var_APCP=on&lev_surface=on"
               "&subregion=&toplat=42.5&leftlon=272.5&rightlon=274&bottomlat=41")
        msgs, g, p = grib_messages(get(url))
        for m in msgs:
            if m.shortName in ("2t", "t") and m.typeOfLevel == "heightAboveGround" and f in LEADS:
                temps.append((f, r1(k_to_f(point_value(m)))))
            if m.shortName == "tp" and getattr(m, "startStep", None) == 0:
                acc[f] = point_value(m)
        g.close(); os.unlink(p)
        time.sleep(1)
    temps = [t for _, t in sorted(temps)]
    if len(temps) != len(LEADS) or any(f not in acc for f in RAIN_LEADS):
        raise ValueError(f"GFS incomplete: temps {temps}, acc {acc}")
    return {"temps": temps, "rainIn": r2(max(0.0, acc[RAIN_LEADS[1]] - acc[RAIN_LEADS[0]]) / 25.4), "run": iso(run)}


def fc_ecmwf(model):
    def fn(made, target):
        run = run_time(made)
        def field(step, param):
            base = (f"https://data.ecmwf.int/forecasts/{run:%Y%m%d}/00z/{model}/0p25/oper/"
                    f"{run:%Y%m%d}000000-{step}h-oper-fc")
            rows = [json.loads(l) for l in get(base + ".index").decode().splitlines() if l.strip()]
            r = [x for x in rows if x.get("param") == param and x.get("levtype", "sfc") == "sfc"]
            if not r:
                raise KeyError(f"{param} at step {step} not in {model}")
            r = r[0]
            blob = get(base + ".grib2", rng=f"bytes={r['_offset']}-{r['_offset'] + r['_length'] - 1}")
            msgs, g, p = grib_messages(blob)
            v = point_value(msgs[0]); g.close(); os.unlink(p)
            return v
        temps = [r1(k_to_f(field(s, "2t"))) for s in LEADS]
        tp = [field(s, "tp") for s in RAIN_LEADS]          # meters, accumulated from the start
        return {"temps": temps, "rainIn": r2(max(0.0, tp[1] - tp[0]) * 1000 / 25.4), "run": iso(run)}
    return fn


def s3_keys(bucket, prefix):
    keys, token = [], None
    while True:
        url = f"https://{bucket}.s3.amazonaws.com/?list-type=2&max-keys=1000&prefix={prefix}"
        if token:
            url += "&continuation-token=" + urllib.parse.quote(token)
        x = get(url).decode()
        keys += re.findall(r"<Key>([^<]+)</Key>", x)
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", x)
        if not m:
            return keys
        token = m.group(1)


def ndfd_file(element, header, cutoff_utc):
    """Newest NDFD file of this WMO header issued at or before the cutoff (looks back 2 days)."""
    best = None
    for back in (0, 1, 2):
        day = (cutoff_utc - dt.timedelta(days=back))
        prefix = f"wmo/{element}/{day:%Y/%m/%d}/{header}_KWBN_"
        for k in s3_keys("noaa-ndfd-pds", prefix):
            stamp = dt.datetime.strptime(k.rsplit("_", 1)[1][:12], "%Y%m%d%H%M").replace(tzinfo=UTC)
            if stamp <= cutoff_utc and (best is None or stamp > best[0]):
                best = (stamp, k)
        if best:
            return best
    return None


def fc_nws(made, target):
    cutoff = dt.datetime.combine(made, NDFD_CUTOFF, tzinfo=CENTRAL).astimezone(UTC)
    found = ndfd_file("temp", "YEUZ98", cutoff)
    if not found:
        raise FileNotFoundError("no NDFD temperature file before the cutoff")
    issued, key = found
    msgs, g, p = grib_messages(get("https://noaa-ndfd-pds.s3.amazonaws.com/" + key, timeout=300))
    want = {c: None for c in checkpoints(target)}
    for m in msgs:
        vd = m.validDate.replace(tzinfo=UTC)
        if vd in want and want[vd] is None:
            want[vd] = r1(k_to_f(point_value(m)))
    g.close(); os.unlink(p)
    temps = [want[c] for c in checkpoints(target)]
    if any(t is None for t in temps):
        raise ValueError(f"NDFD file {key} lacks a checkpoint: {temps}")
    rain = None
    q = ndfd_file("qpf", "YIUZ98", cutoff) or ndfd_file("qpf", "YIUZ88", cutoff)
    if q:
        msgs, g, p = grib_messages(get("https://noaa-ndfd-pds.s3.amazonaws.com/" + q[1], timeout=300))
        start, end = rain_window(target)
        parts = {}
        for m in msgs:
            vd = m.validDate.replace(tzinfo=UTC)     # end of the 6-hour period
            if start < vd <= end:
                parts[vd] = point_value(m)
        g.close(); os.unlink(p)
        if len(parts) == 4:
            rain = r2(sum(parts.values()) / 25.4)
    return {"temps": temps, "rainIn": rain, "issued": iso(issued)}


FETCH = {"nws": fc_nws, "aigfs": fc_aigfs, "gfs": fc_gfs, "aifs": fc_ecmwf("aifs-single"), "ifs": fc_ecmwf("ifs")}


# ---------------------------------------------------------------- observations
_obs_cache = {}
def obs_rows(local_date):
    key = local_date.isoformat()
    if key not in _obs_cache:
        url = (f"https://mesonet.agron.iastate.edu/api/1/obhistory.json?station={STATION['iem']}"
               f"&network={STATION['network']}&date={key}&full=1")
        _obs_cache[key] = json.loads(get(url)).get("data", [])
    return _obs_cache[key]


def parse_utc(s):
    return dt.datetime.strptime(s.replace("Z", ""), "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)


def observed(target):
    """KPPO's temperature nearest each checkpoint (within 20 minutes) and the 24-hour rain total."""
    rows = []
    for d in (target - dt.timedelta(days=1), target, target + dt.timedelta(days=1), target + dt.timedelta(days=2)):
        try:
            rows += obs_rows(d)
        except Exception:
            pass
    pts = []
    for r in rows:
        try:
            pts.append((parse_utc(r["utc_valid"]), r))
        except Exception:
            continue
    temps = []
    for c in checkpoints(target):
        near = [(abs((t - c).total_seconds()), r) for t, r in pts if r.get("tmpf") is not None]
        near = [x for x in near if x[0] <= 20 * 60]
        temps.append(r1(min(near, key=lambda x: x[0])[1]["tmpf"]) if near else None)
    start, end = rain_window(target)
    # Hourly reports (minute 55, or the routine one closest to it) carry the past hour's rain.
    hourly = {}
    for t, r in pts:
        if start < t <= end + dt.timedelta(minutes=5) and t.minute >= 50:
            hourly[t.replace(minute=0)] = r.get("p01i")
    total = r2(sum(v for v in hourly.values() if isinstance(v, (int, float))))
    out = {"temps": temps, "rainIn": None, "rainHours": len(hourly)}
    if len(hourly) >= 22:
        out["rainIn"] = total
    elif total and total >= 0.01:
        # Some hourly reports are missing, but rain was measured: it rained at least this much.
        out["rainIn"] = total; out["rainAtLeast"] = True
    return out


# ---------------------------------------------------------------- grading
def grade_day(day):
    obs = day.get("observed") or {}
    scores = {}
    for rid, fc in day["forecasts"].items():
        if not fc or not fc.get("temps"):
            continue
        misses = [abs(f - o) for f, o in zip(fc["temps"], obs.get("temps", [])) if f is not None and o is not None]
        if len(misses) < 3:
            continue
        s = {"avgMiss": r1(sum(misses) / len(misses)), "hits": sum(1 for m in misses if m <= HIT_DEGREES),
             "checks": len(misses), "worst": r1(max(misses))}
        if fc.get("rainIn") is not None and obs.get("rainIn") is not None:
            said, got = fc["rainIn"] >= 0.01, obs["rainIn"] >= 0.01
            s["rainRight"] = said == got
        scores[rid] = s
    day["scores"] = scores
    if len(scores) >= 2:
        best = min(s["avgMiss"] for s in scores.values())
        day["winners"] = [rid for rid in RACER_IDS if rid in scores and scores[rid]["avgMiss"] == best]
    else:
        day["winners"] = []
    day["status"] = "scored" if scores else "no-observations"


def board(days):
    rows = []
    for rid in RACER_IDS:
        sc = [d["scores"][rid] for d in days if rid in d.get("scores", {})]
        if not sc:
            rows.append({"id": rid, "days": 0})
            continue
        checks = sum(s["checks"] for s in sc)
        miss = sum(s["avgMiss"] * s["checks"] for s in sc) / checks
        rain = [s["rainRight"] for s in sc if "rainRight" in s]
        rows.append({
            "id": rid, "days": len(sc), "avgMiss": r1(miss),
            "hitPct": round(100 * sum(s["hits"] for s in sc) / checks),
            "rainRight": sum(rain), "rainCalls": len(rain),
            "wins": sum(1 for d in days if rid in d.get("winners", []) and len(d.get("winners", [])) == 1),
            "ties": sum(1 for d in days if rid in d.get("winners", []) and len(d.get("winners", [])) > 1),
        })
    # Only racers with enough graded days are ranked; one that joined later waits until it has
    # at least half as many days as the leader (and 3 or more).
    most = max([r["days"] for r in rows] or [0])
    enough = lambda r: r["days"] >= max(3, math.ceil(most / 2))
    ranked = sorted([r for r in rows if r["days"] and enough(r)], key=lambda r: (r["avgMiss"], -r["hitPct"]))
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    waiting = [r for r in rows if r["days"] and not enough(r)]
    for r in waiting:
        r["rank"] = None
    return ranked + waiting + [r for r in rows if not r["days"]]


def head_to_head(days, a="aigfs", b="nws"):
    both = [d for d in days if a in d.get("scores", {}) and b in d.get("scores", {})]
    out = {"a": a, "b": b, "days": len(both), "aBetter": 0, "bBetter": 0, "same": 0}
    for d in both:
        x, y = d["scores"][a]["avgMiss"], d["scores"][b]["avgMiss"]
        out["aBetter" if x < y else "bBetter" if y < x else "same"] += 1
    if both:
        out["aAvgMiss"] = r1(sum(d["scores"][a]["avgMiss"] for d in both) / len(both))
        out["bAvgMiss"] = r1(sum(d["scores"][b]["avgMiss"] for d in both) / len(both))
    return out


# ---------------------------------------------------------------- main
def load():
    try:
        return json.load(open(OUT))
    except Exception:
        return {"days": []}


def save_forecasts(data, made, backfilled=False):
    target = made + dt.timedelta(days=1)
    day = next((d for d in data["days"] if d["target"] == target.isoformat()), None)
    if day is None:
        day = {"target": target.isoformat(), "made": made.isoformat(),
               "checkpoints": [{"utc": iso(c), "local": local_label(c)} for c in checkpoints(target)],
               "forecasts": {}, "status": "waiting"}
        data["days"].append(day)
    errors = {}
    for rid in RACER_IDS:
        if day["forecasts"].get(rid):
            continue                                        # saved once, never changed
        try:
            fc = FETCH[rid](made, target)
            if backfilled:
                fc["backfilled"] = True
            fc["saved"] = iso(dt.datetime.now(UTC))
            day["forecasts"][rid] = fc
            print(f"  {made} -> {target} {rid}: {fc['temps']} rain {fc.get('rainIn')}")
        except Exception as e:
            errors[rid] = f"{type(e).__name__}: {e}"[:300]
            print(f"  {made} -> {target} {rid}: couldn't get it ({errors[rid]})")
    if errors:
        day.setdefault("missing", {}).update(errors)
    for rid in list(day.get("missing", {})):
        if day["forecasts"].get(rid):
            day["missing"].pop(rid)
    if not day.get("missing"):
        day.pop("missing", None)
    return day


def main(argv):
    data = load()
    now = dt.datetime.now(UTC)
    today = now.astimezone(CENTRAL).date()
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "backfill":
        a = dt.date.fromisoformat(argv[2]); b = dt.date.fromisoformat(argv[3])
        d = a
        while d <= b and d < today:
            print(f"Backfilling forecasts made {d}")
            save_forecasts(data, d, backfilled=True)
            d += dt.timedelta(days=1)
    elif mode == "force" or now.astimezone(CENTRAL).time() >= SAVE_FROM:
        print(f"Saving forecasts made {today}")
        save_forecasts(data, today)
    # Grade every day whose rain window ended at least an hour ago and isn't scored yet.
    for day in data["days"]:
        target = dt.date.fromisoformat(day["target"])
        _, rain_end = rain_window(target)
        if now >= rain_end + dt.timedelta(hours=1) and day.get("status") != "scored":
            try:
                day["observed"] = observed(target)
                grade_day(day)
                print(f"Graded {target}: winners {day.get('winners')}")
            except Exception as e:
                print(f"Couldn't grade {target}: {e}")
        elif day.get("status") == "scored" and day.get("observed", {}).get("rainIn") is None and now - rain_end < dt.timedelta(days=3):
            # rain reports sometimes arrive late: try once more for up to 3 days
            try:
                o = observed(target)
                if o.get("rainIn") is not None:
                    day["observed"] = o; grade_day(day)
            except Exception:
                pass
    data["days"].sort(key=lambda d: d["target"])
    data["days"] = data["days"][-400:]
    scored = [d for d in data["days"] if d.get("status") == "scored"]
    last30 = [d for d in scored if dt.date.fromisoformat(d["target"]) > today - dt.timedelta(days=30)]
    out = {
        "about": ("The Forecast Race: NOAA's new AI weather model, the National Weather Service's own forecasters "
                  "and three other computer models, graded every day against the La Porte airport (KPPO). "
                  "Each morning we save what each racer says about tomorrow (temperatures at four checkpoints and the "
                  "24-hour rain total) and grade it the next day. Saved forecasts are never changed. "
                  "Run by La Porte Weather Now (scripts/forecast_race.py)."),
        "generated": now.astimezone(CENTRAL).isoformat(timespec="seconds"),
        "started": "2026-10-06",
        "station": STATION,
        "rules": {"checkpointsUtc": ["06", "12", "18", "00"], "hitDegrees": HIT_DEGREES,
                  "rainWindow": "06 UTC to 06 UTC (1 AM to 1 AM Central summer time; midnight to midnight in winter)",
                  "rainCall": "a racer 'calls rain' when it forecasts 0.01 inch or more for the 24 hours",
                  "minDaysToCall": 14},
        "racers": RACERS,
        # ECMWF's terms ask for this exact attribution for a service built on its open data (checked Oct. 7, 2026,
        # apps.ecmwf.int/datasets/licences/general): the statement, the source, the licence, the disclaimer, the changes.
        "credits": ("NOAA/National Weather Service (NDFD, AIGFS, GFS: public domain). Observations: the La Porte "
                    "Municipal Airport's automated weather station (KPPO) via the Iowa Environmental Mesonet. "
                    "This service is based on data and products of the European Centre for Medium-Range Weather "
                    "Forecasts (ECMWF) (AIFS and IFS open data). Source: www.ecmwf.int. Licence: Creative Commons "
                    "Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/. "
                    "ECMWF does not accept any liability whatsoever for any error or omission in the data, their "
                    "availability, or for any loss or damage arising from their use. Changes: we read single "
                    "forecast values for one spot from ECMWF's files."),
        "leaderboard": {"last30": board(last30), "all": board(scored)},
        "headToHead": {"aiVsNws": head_to_head(scored, "aigfs", "nws"), "aiVsGfs": head_to_head(scored, "aigfs", "gfs"),
                       "europeAiVsNws": head_to_head(scored, "aifs", "nws")},
        "days": data["days"],
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"Wrote {OUT}: {len(scored)} graded days, {len(data['days'])} days on file.")


if __name__ == "__main__":
    main(sys.argv)
