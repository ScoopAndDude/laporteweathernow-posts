#!/usr/bin/env python3
"""Saves a small copy of La Porte's latest official weather as home.json for the
laporteweathernow.com homepage, so the page always has numbers to show: when the
Weather Service is slow or down, the homepage shows this copy with its time
("as of 7:41 a.m.") instead of dashes, then switches to live data when NWS answers.

Runs every hour on GitHub Actions and keeps only the newest copy, on the repo's
"live" branch (read at raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/live/home.json).
Same shapes the homepage's own code saves on each visitor's device (index.html).
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nws_snapshot import API, CENTRAL, LAT, LON, STATION, attempt, errors, get_json, text_in_zone, now_utc, central  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "home.json")
GRID = f"{API}/gridpoints/IWX/13,58"
NWS_TZ, REAL_TZ = "America/Indiana/Indianapolis", "America/Chicago"   # NWS files La Porte as Eastern; it's Central


def slim(p):
    start = p.get("startTime")
    return {
        "number": p.get("number"), "name": p.get("name"),
        "startTime": start, "endTime": p.get("endTime"), "isDaytime": p.get("isDaytime"),
        "temperature": p.get("temperature"), "windSpeed": p.get("windSpeed"),
        "shortForecast": text_in_zone(p.get("shortForecast"), start, NWS_TZ, REAL_TZ),
        "probabilityOfPrecipitation": {"value": (p.get("probabilityOfPrecipitation") or {}).get("value") or 0},
    }


def current():
    p = get_json(f"{API}/stations/{STATION}/observations/latest")["properties"]
    t = (p.get("temperature") or {}).get("value")
    if t is None:
        raise RuntimeError("KPPO has no temperature in its latest reading")

    def mph(q):
        q = q or {}
        v, unit = q.get("value"), q.get("unitCode", "")
        if v is None:
            return None
        return round(v * 0.621371) if "km_h" in unit else round(v * 2.237) if "m_s" in unit else round(v)
    rh = (p.get("relativeHumidity") or {}).get("value")
    return {
        "stationId": STATION, "stationName": "La Porte Municipal Airport",
        "tempF": round(t * 9 / 5 + 32), "text": p.get("textDescription"),
        "windMph": mph(p.get("windSpeed")), "gustMph": mph(p.get("windGust")),
        "humidity": round(rh) if rh else None, "timestamp": p.get("timestamp"),
    }


def daily():
    return [slim(p) for p in (get_json(f"{GRID}/forecast")["properties"].get("periods") or [])[:14]]


def hourly():
    now = now_utc()
    periods = get_json(f"{GRID}/forecast/hourly")["properties"].get("periods") or []
    return [slim(p) for p in periods if datetime.datetime.fromisoformat(p["endTime"]) > now][:24]


def alerts():
    feats = get_json(f"{API}/alerts/active?point={LAT},{LON}").get("features") or []
    out = []
    for f in feats:
        p = f.get("properties") or {}
        if p.get("status") not in (None, "Actual") or p.get("messageType") == "Cancel":
            continue
        out.append({k: p.get(k) for k in ("event", "headline", "severity", "sent", "onset", "ends", "expires")})
    return out


def main():
    started = now_utc()
    home = {
        "about": "Latest official NWS weather for La Porte, IN, saved hourly for laporteweathernow.com's homepage (scripts/home_cache.py).",
        "fetched": central(started),
        "place": "La Porte, IN",
        "timeZone": REAL_TZ,
        "current": attempt("KPPO observation", current),
        "daily": attempt("NWS forecast", daily) or [],
        "hourly": attempt("NWS hourly forecast", hourly) or [],
        "alerts": attempt("NWS alerts", alerts),
        "alertsChecked": central(started),
        "errors": errors,
    }
    if not home["current"] and not home["daily"]:
        print("Nothing came back from NWS; keeping the last copy.", file=sys.stderr)
        sys.exit(1)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(home, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"Saved home.json at {home['fetched']} ({len(home['daily'])} periods, {len(home['hourly'])} hours, {len(errors)} errors).")


if __name__ == "__main__":
    main()
