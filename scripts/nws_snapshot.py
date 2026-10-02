#!/usr/bin/env python3
"""Saves the newest official weather for La Porte, Indiana into nws-snapshot.json.

The Daily Scoop is written every morning from this file, so each post starts from the
newest National Weather Service forecast, alerts and forecaster discussion. GitHub's
computers can reach weather.gov directly, and the file keeps a dated copy of exactly
what NWS, the Storm Prediction Center (SPC) and the Weather Prediction Center (WPC)
said at that moment (github.com/ScoopAndDude/laporteweathernow-posts/commits/main/nws-snapshot.json).

Every source is asked on its own. If one doesn't answer, its error goes into the
file's "errors" list and the rest still save, so the post writer knows what's missing.
If neither the forecast nor the alerts can be read, the old file is left alone and
the job fails (GitHub emails the owner).

Sources (all free, public, U.S. government):
  api.weather.gov    forecast, active alerts, La Porte airport observation (KPPO),
                     Northern Indiana forecast discussion (AFD), hazardous weather
                     outlook (HWO), hydrologic outlook (ESF), forecast rain amounts
  spc.noaa.gov       severe storm outlooks for today, tomorrow and the day after
  mapservices.weather.noaa.gov   WPC excessive rainfall (flooding rain) outlooks
"""
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import consensus as second_opinion   # model blend, work-hour rain timing, morning log (scripts/consensus.py)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nws-snapshot.json")

LAT, LON = 41.6081, -86.7189        # La Porte, Indiana (same point as the site's NWS forecast link)
PLACE = "La Porte, IN"
STATION = "KPPO"                    # La Porte Municipal Airport
OFFICE = "IWX"                      # NWS Northern Indiana (Syracuse, IN)
COUNTY_ZONES = ["INZ103", "INZ203", "INC091"]   # northern La Porte, southern La Porte, La Porte County
API = "https://api.weather.gov"
# Indiana's Central-time counties (same list as the website's timeutil.js).
CENTRAL_TIME_COUNTIES = {"INC051", "INC073", "INC089", "INC091", "INC111", "INC123", "INC127",
                         "INC129", "INC147", "INC149", "INC163", "INC173"}
UA = "LaPorteWeatherNow/1.0 (+https://laporteweathernow.com)"
CENTRAL = ZoneInfo("America/Chicago")

LINKS = {
    "forecast": "https://forecast.weather.gov/MapClick.php?lat=41.6081&lon=-86.7189",
    "discussion": "https://forecast.weather.gov/product.php?site=IWX&issuedby=IWX&product=AFD",
    "hazardousWeatherOutlook": "https://forecast.weather.gov/product.php?site=IWX&issuedby=IWX&product=HWO",
    "hydrologicOutlook": "https://forecast.weather.gov/product.php?site=IWX&issuedby=IWX&product=ESF",
    "currentHazards": "https://www.weather.gov/iwx/",
    "spcOutlooks": "https://www.spc.noaa.gov/products/outlook/",
    "wpcExcessiveRain": "https://www.wpc.ncep.noaa.gov/qpf/excessive_rainfall_outlook_ero.php",
    "observation": "https://forecast.weather.gov/data/obhistory/KPPO.html",
}

errors = []


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def central(dt):
    return dt.astimezone(CENTRAL).isoformat()


def get(url, accept="application/geo+json", tries=3, timeout=30):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": accept, "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # network errors, 5xx, timeouts: wait and try again
            last = e
            time.sleep(2 + 3 * attempt)
    raise RuntimeError(f"{url} -> {last}")


def get_json(url, accept="application/geo+json"):
    return json.loads(get(url, accept=accept))


def attempt(name, fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        errors.append({"source": name, "error": str(e)[:400]})
        print(f"!! {name}: {e}", file=sys.stderr)
        return None


# ---------- helpers ----------

def num(v, nd=0):
    if v is None:
        return None
    r = round(float(v), nd)
    return int(r) if nd == 0 else r


def qv(props, key):
    """Value and unit of an api.weather.gov quantity like {"unitCode": "wmoUnit:degC", "value": 12.2}."""
    q = props.get(key) or {}
    return q.get("value"), q.get("unitCode", "")


def to_f(v, unit):
    if v is None:
        return None
    return num(v * 9 / 5 + 32) if unit.endswith("degC") else num(v)


def to_mph(v, unit):
    if v is None:
        return None
    if unit.endswith("km_h-1"):
        return num(v * 0.621371)
    if unit.endswith("m_s-1"):
        return num(v * 2.236936)
    return num(v)


def compass(deg):
    if deg is None:
        return None
    pts = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return pts[int((float(deg) % 360) / 22.5 + 0.5) % 16]


def iso_hours(duration):
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?", duration or "")
    if not m:
        return 0
    d, h, mi = (int(x or 0) for x in m.groups())
    return d * 24 + h + (1 if mi else 0)


# ---------- NWS ----------

def point():
    p = get_json(f"{API}/points/{LAT},{LON}")["properties"]
    rel = (p.get("relativeLocation") or {}).get("properties") or {}
    county = (p.get("county") or "").rsplit("/", 1)[-1]
    return {
        "office": p.get("gridId"), "gridX": p.get("gridX"), "gridY": p.get("gridY"),
        "forecast": p.get("forecast"), "forecastGridData": p.get("forecastGridData"),
        "forecastZone": (p.get("forecastZone") or "").rsplit("/", 1)[-1],
        "county": county,
        "nwsTimeZone": p.get("timeZone"),
        # Indiana's Central-time counties are on file with NWS as Eastern; La Porte (INC091) keeps Central.
        "timeZone": "America/Chicago" if county in CENTRAL_TIME_COUNTIES else p.get("timeZone"),
        "nearestPlace": ", ".join(x for x in (rel.get("city"), rel.get("state")) if x),
    }


def zone_names(ids):
    names = {}
    for z in ids:
        kind = "county" if z[2] == "C" else "forecast"
        p = get_json(f"{API}/zones/{kind}/{z}")["properties"]
        names[z] = p.get("name")
    return names


def observation():
    p = get_json(f"{API}/stations/{STATION}/observations/latest")["properties"]
    t, tu = qv(p, "temperature")
    d, du = qv(p, "dewpoint")
    ws, wsu = qv(p, "windSpeed")
    wg, wgu = qv(p, "windGust")
    wd, _ = qv(p, "windDirection")
    vis, visu = qv(p, "visibility")
    rh, _ = qv(p, "relativeHumidity")
    pr, pru = qv(p, "barometricPressure")
    obs_time = p.get("timestamp")
    return {
        "station": f"{STATION} (La Porte Municipal Airport)",
        "time": central(datetime.datetime.fromisoformat(obs_time)) if obs_time else None,
        "weather": p.get("textDescription"),
        "temperatureF": to_f(t, tu),
        "dewpointF": to_f(d, du),
        "humidityPercent": num(rh),
        "wind": {"from": compass(wd), "degrees": num(wd), "mph": to_mph(ws, wsu), "gustMph": to_mph(wg, wgu)},
        "visibilityMiles": num(vis / 1609.344, 1) if vis is not None and visu.endswith(":m") else None,
        "pressureInHg": num(pr / 3386.389, 2) if pr is not None and pru.endswith("Pa") else None,
        "metar": p.get("rawMessage"),
    }


TIME_WORD = re.compile(r"\b(?:(1[0-2]|[1-9])(?::([0-5]\d))?\s?(am|pm)|(noon|midnight))\b", re.I)


def text_in_zone(text, when, nws_tz, real_tz):
    """NWS writes clock times ("before 5pm") in the zone it has on file for the point. For
    La Porte that's Eastern, but La Porte keeps Central time, so every time reads an hour
    late. Same fix as the website's nwsTextInZone (timeutil.js)."""
    if not text or not nws_tz or not real_tz or nws_tz == real_tz:
        return text
    d = datetime.datetime.fromisoformat(when)
    shift = int((d.astimezone(ZoneInfo(real_tz)).utcoffset() - d.astimezone(ZoneInfo(nws_tz)).utcoffset()).total_seconds() // 60)
    if not shift:
        return text

    def fix(m):
        h, mm, ap, word = m.groups()
        if word:
            mins = 720 if word.lower() == "noon" else 0
        else:
            mins = (int(h) % 12 + (12 if ap.lower() == "pm" else 0)) * 60 + int(mm or 0)
        mins = (mins + shift) % 1440
        hh, mn = divmod(mins, 60)
        out = "midnight" if mins == 0 else "noon" if mins == 720 else \
            f"{hh % 12 or 12}{':%02d' % mn if mn else ''}{'am' if hh < 12 else 'pm'}"
        return out[0].upper() + out[1:] if m.group(0)[0].isupper() else out
    return TIME_WORD.sub(fix, text)


def forecast(pt):
    d = get_json(pt["forecast"])["properties"]
    nws_tz, real_tz = pt.get("nwsTimeZone"), pt.get("timeZone")
    periods = []
    for x in d.get("periods") or []:
        start = x.get("startTime")
        periods.append({
            "name": x.get("name"),
            "start": start, "end": x.get("endTime"),
            "isDaytime": x.get("isDaytime"),
            "temperatureF": x.get("temperature"),
            "rainChancePercent": (x.get("probabilityOfPrecipitation") or {}).get("value"),
            "wind": " ".join(v for v in (x.get("windDirection"), x.get("windSpeed")) if v),
            "short": text_in_zone(x.get("shortForecast"), start, nws_tz, real_tz),
            "detailed": text_in_zone(x.get("detailedForecast"), start, nws_tz, real_tz),
        })
    note = None
    if nws_tz and real_tz and nws_tz != real_tz:
        note = (f"Clock times in the forecast wording are already in {real_tz} (La Porte's real time). "
                f"NWS writes them in {nws_tz}, which it has on file for La Porte by mistake.")
    return {"updated": d.get("updateTime") or d.get("updated"), "generated": d.get("generatedAt"),
            "timesNote": note, "periods": periods}


def rain_amounts(pt, periods):
    """Forecast rain (NWS grid QPF) in inches for each forecast period and the next 3 days."""
    q = get_json(pt["forecastGridData"])["properties"].get("quantitativePrecipitation") or {}
    unit = q.get("uom", "")
    hours = []
    for v in q.get("values") or []:
        start_s, dur = v["validTime"].split("/")
        start = datetime.datetime.fromisoformat(start_s)
        n = iso_hours(dur)
        amount = float(v.get("value") or 0)
        if unit.endswith("mm"):
            amount /= 25.4
        for h in range(n):
            hours.append((start + datetime.timedelta(hours=h), amount / n))
    now = now_utc().replace(minute=0, second=0)   # count the hour that's under way
    by_period = []
    for p in periods or []:
        s = datetime.datetime.fromisoformat(p["start"])
        e = datetime.datetime.fromisoformat(p["end"])
        by_period.append({"name": p["name"], "inches": round(sum(a for t, a in hours if s <= t < e), 2)})
    return {
        "note": "NWS forecast grid rain totals (QPF) for the La Porte grid point; the forecast text's own wording comes first.",
        "next24hInches": round(sum(a for t, a in hours if now <= t < now + datetime.timedelta(hours=24)), 2),
        "next72hInches": round(sum(a for t, a in hours if now <= t < now + datetime.timedelta(hours=72)), 2),
        "byPeriod": by_period,
    }


def alert_row(f, full=True):
    p = f.get("properties") or {}
    row = {
        "id": p.get("id"),
        "event": p.get("event"),
        "headline": p.get("headline"),
        "nwsHeadline": ((p.get("parameters") or {}).get("NWSheadline") or [None])[0],
        "area": p.get("areaDesc"),
        "sender": p.get("senderName"),
        "sent": p.get("sent"), "onset": p.get("onset"), "ends": p.get("ends"), "expires": p.get("expires"),
        "messageType": p.get("messageType"),
        "severity": p.get("severity"), "certainty": p.get("certainty"), "urgency": p.get("urgency"),
    }
    if full:
        row["description"] = p.get("description")
        row["instruction"] = p.get("instruction")
    return row


def county_alerts():
    seen, rows, answered = set(), [], 0
    urls = [f"{API}/alerts/active?point={LAT},{LON}"] + [f"{API}/alerts/active/zone/{z}" for z in COUNTY_ZONES]
    for url in urls:
        try:
            feats = get_json(url).get("features") or []
            answered += 1
        except Exception as e:
            errors.append({"source": "alerts " + url, "error": str(e)[:400]})
            continue
        for f in feats:
            key = (f.get("properties") or {}).get("id")
            if key not in seen:
                seen.add(key)
                rows.append(alert_row(f))
    if not answered:
        raise RuntimeError("no alert request answered")
    return rows


# Counties next to or near La Porte County (SAME codes), so their alerts come with full text:
# Lake, Porter, Starke, St. Joseph, Jasper, Newton, Pulaski, Marshall, Elkhart (IN) and Berrien (MI).
NEARBY_SAME = {"018089", "018127", "018149", "018141", "018073", "018111", "018131", "018099", "018039", "026021"}


def area_alerts():
    """Every active alert in Indiana and Michigan (short form), plus full text for nearby counties."""
    short, nearby, seen = [], [], set()
    for area in ("IN", "MI"):
        for f in get_json(f"{API}/alerts/active?area={area}").get("features") or []:
            p = f.get("properties") or {}
            same = set(((p.get("geocode") or {}).get("SAME")) or [])
            if (area == "IN" or same & NEARBY_SAME) and p.get("id") not in seen:
                seen.add(p.get("id"))
                short.append(alert_row(f, full=False))
            if same & NEARBY_SAME and "018091" not in same:
                row = alert_row(f)
                if row["id"] not in {r["id"] for r in nearby}:
                    nearby.append(row)
    return {"indiana": short, "nearbyCountiesFullText": nearby}


def latest_product(kind, max_age_hours=None):
    items = get_json(f"{API}/products/types/{kind}/locations/{OFFICE}", accept="application/ld+json").get("@graph") or []
    items.sort(key=lambda x: x.get("issuanceTime", ""), reverse=True)
    if not items:
        return None
    issued = datetime.datetime.fromisoformat(items[0]["issuanceTime"])
    age = round((now_utc() - issued).total_seconds() / 3600, 1)
    if max_age_hours and age > max_age_hours:
        return {"issued": central(issued), "ageHours": age, "text": None,
                "note": f"Newest one is older than {max_age_hours} hours, so it isn't current."}
    prod = get_json(f"{API}/products/{items[0]['id']}", accept="application/ld+json")
    return {"issued": central(issued), "ageHours": age, "text": (prod.get("productText") or "").strip()}


# ---------- SPC and WPC ----------

SPC_ORDER = {"TSTM": 1, "MRGL": 2, "SLGT": 3, "ENH": 4, "MDT": 5, "HIGH": 6}


def in_ring(x, y, ring):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def in_geometry(x, y, geom):
    if not geom:
        return False
    coords = geom.get("coordinates") or []
    polys = [coords] if geom.get("type") == "Polygon" else coords if geom.get("type") == "MultiPolygon" else []
    return any(poly and in_ring(x, y, poly[0]) and not any(in_ring(x, y, h) for h in poly[1:]) for poly in polys)


def spc_day(day):
    g = get_json(f"https://www.spc.noaa.gov/products/outlook/day{day}otlk_cat.nolyr.geojson", accept="application/json")
    here, present, valid, expire = None, [], None, None
    for f in g.get("features") or []:
        p = f.get("properties") or {}
        label = p.get("LABEL")
        valid, expire = valid or p.get("VALID"), expire or p.get("EXPIRE")
        if label in SPC_ORDER and f.get("geometry"):
            present.append(p.get("LABEL2") or label)
            if in_geometry(LON, LAT, f["geometry"]) and (here is None or SPC_ORDER[label] > SPC_ORDER[here[0]]):
                here = (label, p.get("LABEL2") or label)
    out = {"day": day, "valid": valid, "expires": expire,
           "riskAtLaPorte": here[1] if here else "No thunderstorm or severe risk area",
           "riskAreasAnywhere": present}
    try:
        page = get(f"https://www.spc.noaa.gov/products/outlook/day{day}otlk.html", accept="text/html")
        m = re.search(r"<pre[^>]*>(.*?)</pre>", page, re.S | re.I)
        text = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
        s = re.search(r"\.\.\.SUMMARY\.\.\.\s*(.*?)(?:\n\s*\n|$)", text, re.S)
        out["summary"] = " ".join(s.group(1).split()) if s else None
        out["text"] = text[:5000]
    except Exception as e:
        errors.append({"source": f"SPC day {day} text", "error": str(e)[:400]})
    return out


def wpc_excessive_rain():
    base = "https://mapservices.weather.noaa.gov/vector/rest/services/hazards/wpc_precip_hazards/MapServer"
    info = get_json(base + "?f=json", accept="application/json")
    out = []
    for layer in info.get("layers") or []:
        name = layer.get("name") or ""
        if "excessive" not in name.lower() and "ero" not in name.lower().split():
            continue
        q = urllib.parse.urlencode({
            "geometry": f"{LON},{LAT}", "geometryType": "esriGeometryPoint", "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "false", "f": "json"})
        res = get_json(f"{base}/{layer.get('id')}/query?{q}", accept="application/json")
        out.append({"layer": name, "atLaPorte": [f.get("attributes") for f in res.get("features") or []]})
    return out


def main():
    started = now_utc()
    pt = attempt("NWS point", point) or {}
    fc = attempt("NWS forecast", forecast, pt) if pt.get("forecast") else None
    alerts = attempt("NWS alerts for La Porte County", county_alerts)
    if fc is None and alerts is None:
        print("Neither the forecast nor the alerts could be read; leaving the old file alone.", file=sys.stderr)
        sys.exit(1)
    snap = {
        "about": ("Official weather for La Porte, Indiana, saved by a GitHub job for the Daily Scoop "
                  "(laporteweathernow.com/daily-scoop). Copied from NWS, SPC and WPC as-is; see scripts/nws_snapshot.py."),
        "fetched": central(started),
        "place": PLACE, "lat": LAT, "lon": LON,
        "point": pt,
        "zones": attempt("NWS zone names", zone_names, COUNTY_ZONES),
        "observation": attempt("KPPO observation", observation),
        "forecast": fc,
        "rain": attempt("NWS forecast rain amounts", rain_amounts, pt, (fc or {}).get("periods")) if pt.get("forecastGridData") else None,
        "alertsLaPorteCounty": alerts,
        "alertsNearby": attempt("NWS alerts for Indiana and nearby Michigan", area_alerts),
        "discussion": attempt("NWS Northern Indiana discussion (AFD)", latest_product, "AFD"),
        "hazardousWeatherOutlook": attempt("NWS hazardous weather outlook (HWO)", latest_product, "HWO", 36),
        "hydrologicOutlook": attempt("NWS hydrologic outlook (ESF)", latest_product, "ESF", 96),
        "spc": [x for x in (attempt(f"SPC day {d} outlook", spc_day, d) for d in (1, 2, 3)) if x],
        "wpcExcessiveRain": attempt("WPC excessive rainfall outlook", wpc_excessive_rain),
        "workdayRain": attempt("NWS hourly rain chances", second_opinion.workday_rain, pt, get_json) if pt.get("forecast") else None,
        "consensus": attempt("Computer models (Open-Meteo)", second_opinion.consensus, (fc or {}).get("periods"), get_json) if fc else None,
        "links": LINKS,
        "errors": errors,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    if fc:
        row = attempt("Morning log", second_opinion.morning_record, started, fc.get("periods"), snap.get("consensus"))
        if row:
            print(f"Saved this morning's forecast to morning-log.json: {row}")
    print(f"Saved {os.path.basename(OUT)} at {snap['fetched']} with {len(errors)} source error(s).")
    for e in errors:
        print(f"   - {e['source']}: {e['error']}")


if __name__ == "__main__":
    main()
