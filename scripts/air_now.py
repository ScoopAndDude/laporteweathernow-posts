#!/usr/bin/env python3
"""Saves La Porte's official air quality as air.json (Oct. 17, 2026), for laporteweathernow.com/air-quality
and the homepage card. Runs with the homepage copy every 15 minutes (home-cache.yml) and goes on the
"live" branch next to home.json: raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/live/air.json

Source: EPA AirNow's current observations near ZIP 46350 (the 2026 "ziplatlong" web service; the old
zipCode/latLong services were retired Sept. 30, 2026). AirNow picks the closest monitor for each
pollutant within 50 miles; the AQI is the NowCast AQI, the same number AirNow.gov shows.
The key is the AIRNOW_API_KEY secret. It never goes into air.json, the log or the site.

If AirNow doesn't answer, the last saved air.json is kept as it was (its observed time shows its age,
and the site falls back to its model estimate when the copy is more than 3 hours old)."""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "air.json")
LAST = "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/live/air.json"
URL = "https://www.airnowapi.org/aq/observation/current/ziplatlong/"
ZIP = "46350"
OFFSETS = {"CDT": -5, "CST": -6, "EDT": -4, "EST": -5}
NAMES = {"OZONE": "ozone", "O3": "ozone", "PM2.5": "fine particles (PM2.5, which includes smoke)", "PM10": "coarse particles (PM10, dust)"}


def say(msg, key):
    print(str(msg).replace(key, "***") if key else msg)


def observed(r):
    """'2026-10-17' + '17:00' + 'CDT' -> '2026-10-17T17:00:00-05:00'."""
    off = OFFSETS.get((r.get("localTimeZone") or "").upper())
    d, h = r.get("dateObserved"), r.get("hourObserved")
    if off is None or not d or h is None:
        return None
    hh = int(str(h).split(":")[0])
    tz = datetime.timezone(datetime.timedelta(hours=off))
    return datetime.datetime.fromisoformat(d).replace(hour=hh, tzinfo=tz).isoformat()


def keep_last(reason, key):
    say(f"AirNow: {reason}; keeping the last air.json", key)
    try:
        with urllib.request.urlopen(LAST, timeout=20) as r:
            last = json.load(r)
        last["lastError"] = reason
        last["lastTry"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(last, fh, indent=1)
    except Exception as e:  # nothing saved yet: no file, the site uses its estimate
        say(f"no earlier air.json either ({type(e).__name__})", key)


def main():
    key = os.environ.get("AIRNOW_API_KEY", "").strip()
    if not key:
        keep_last("no AIRNOW_API_KEY secret", key)
        return
    q = urllib.parse.urlencode({"zipCode": ZIP, "format": "application/json", "API_KEY": key})
    try:
        req = urllib.request.Request(URL + "?" + q, headers={"User-Agent": "laporteweathernow.com (air quality)"})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        keep_last(f"HTTP {e.code}", key)
        return
    except Exception as e:
        keep_last(type(e).__name__, key)
        return
    if not isinstance(data, list):
        msg = ((data or {}).get("WebServiceError") or [{}])[0].get("Message", "unexpected answer")
        keep_last(msg[:120], key)
        return
    readings = []
    for r in data:
        aqi = r.get("nowcastAQI")
        if not isinstance(aqi, (int, float)) or aqi < 0:
            continue
        p = (r.get("parameterName") or "").upper()
        readings.append({
            "pollutant": p, "about": NAMES.get(p, p.lower()), "aqi": int(aqi), "category": r.get("aqiCategoryName"),
            "site": r.get("siteName"), "siteId": r.get("siteID"), "reportingArea": r.get("reportingAreaName"),
            "agency": r.get("reportingAgency"), "observed": observed(r),
        })
    if not readings:
        keep_last("no readings within 50 miles", key)
        return
    top = max(readings, key=lambda x: x["aqi"])
    times = sorted(x["observed"] for x in readings if x["observed"])
    out = {
        "about": "Official air quality for La Porte, Indiana: EPA AirNow's current NowCast AQI from the closest monitor for each pollutant within 50 miles of ZIP 46350 (scripts/air_now.py).",
        "source": "EPA AirNow", "zip": ZIP,
        "checked": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "observed": times[-1] if times else None,
        "aqi": top["aqi"], "category": top["category"], "main": top["pollutant"], "mainAbout": top["about"], "site": top["site"],
        "readings": sorted(readings, key=lambda x: -x["aqi"]),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    say(f"AirNow: AQI {top['aqi']} {top['category']} ({top['pollutant']} at {top['site']}), {len(readings)} readings, observed {out['observed']}", key)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never fail the homepage copy over air quality
        print("air_now:", type(e).__name__)
    sys.exit(0)
