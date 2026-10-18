#!/usr/bin/env python3
"""La Porte County rain and snow totals by town, for laporteweathernow.com/rain-totals (Oct. 18, 2026).

Saves rain.json: every daily rain-gauge (and snowfall) report from La Porte County's volunteer
observers over the last 31 days, as kept by the Iowa Environmental Mesonet (IEM) at Iowa State
University:
  - CoCoRaHS (Community Collaborative Rain, Hail and Snow Network) volunteers, IEM network IN_COCORAHS,
    stations IN-LP-*: each report is the 24 hours ending at the observer's morning reading (usually
    about 7 a.m.) on that date.
  - National Weather Service cooperative (co-op) observers in the county, IEM network IN_COOP: the
    24 hours ending at that observer's reading time, which is saved with each station.
Nothing is estimated or filled in: a day with no report stays empty, and the page says so.
A trace (a little rain, too little to measure) is saved as "T".

  python3 scripts/rain_totals.py          update the last 5 days (the whole 31 the first time)
  python3 scripts/rain_totals.py force    download all 31 days again

Started by the Timer three times a morning (observers send their reports through the morning).
Never fails the job over a slow or missing answer: it prints a warning and keeps what it had.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "rain.json")
CENTRAL = ZoneInfo("America/Chicago")
API = "https://mesonet.agron.iastate.edu/api/1/daily.geojson?network={net}&date={date}"
DAYS = 31
REFRESH = 5
# La Porte County's co-op stations (IEM IDs). CoCoRaHS stations are found by their IN-LP- prefix.
COOP = {"LAPI3", "WANI3"}
ABOUT = ("Daily rain and snowfall reports from La Porte County, Indiana's CoCoRaHS volunteers and National Weather "
         "Service co-op observers, for laporteweathernow.com/rain-totals, from the Iowa Environmental Mesonet. "
         "Observed amounts only; a missing day means no report. 'T' is a trace. Made by scripts/rain_totals.py.")
SOURCES = [{"label": "CoCoRaHS volunteer observers", "url": "https://www.cocorahs.org/"},
           {"label": "NWS cooperative observers", "url": "https://www.weather.gov/coop/"},
           {"label": "Iowa Environmental Mesonet (Iowa State University) archive", "url": "https://mesonet.agron.iastate.edu/"}]


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "laporteweathernow.com rain totals (github.com/ScoopAndDude)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"warning: {url}: {e}", file=sys.stderr)
            time.sleep(3 * (i + 1))
    return None


def amount(v):
    """IEM gives a trace as 0.0001. Keep inches to 2 places; None stays None (not reported)."""
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if v < 0:
        return None
    if 0 < v < 0.005:
        return "T"
    return round(v, 2)


def place(name):
    """'(KD9LWR) Trail Creek 1.0 NNW' -> 'Trail Creek'; 'LAPORTE' -> 'La Porte'; 'WANATAH 2 WNW' -> 'Wanatah'."""
    n = re.sub(r"^\(.*?\)\s*", "", name or "").strip()
    n = re.sub(r"\s+\d+(\.\d+)?\s+[NSEW]{1,3}$", "", n).strip()
    if n.isupper():
        n = n.title()
    if n.replace(" ", "").lower() == "laporte":
        n = "La Porte"
    return n


def main():
    force = len(sys.argv) > 1 and sys.argv[1] == "force"
    old = {}
    if os.path.exists(OUT) and not force:
        try:
            old = json.load(open(OUT, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            old = {}
    today = datetime.datetime.now(CENTRAL).date()
    dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(DAYS)]
    have = set(old.get("checkedDates") or [])
    stations = {s["id"]: s for s in old.get("stations", [])}
    checked = set()
    for i, d in enumerate(dates):
        if i >= REFRESH and d in have:
            checked.add(d)
            continue
        ok = True
        for net in ("IN_COCORAHS", "IN_COOP"):
            g = get(API.format(net=net, date=d))
            if g is None:
                ok = False
                continue
            for f in g.get("features", []):
                p = f.get("properties") or {}
                sid = p.get("station") or ""
                if not (sid.startswith("IN-LP-") if net == "IN_COCORAHS" else sid in COOP):
                    continue
                pr, sn = amount(p.get("precip")), amount(p.get("snow"))
                s = stations.setdefault(sid, {"id": sid})
                lon, lat = (f.get("geometry") or {}).get("coordinates", [None, None])[:2]
                s.update({"name": p.get("name") or sid, "place": place(p.get("name")),
                          "network": "CoCoRaHS" if net == "IN_COCORAHS" else "NWS co-op",
                          "lat": round(lat, 4) if lat is not None else None, "lon": round(lon, 4) if lon is not None else None})
                if p.get("temp_hour") not in (None, ""):
                    try:
                        s["obsHour"] = int(float(p["temp_hour"]))
                    except (TypeError, ValueError):
                        pass
                s.setdefault("precip", {}).pop(d, None)
                s.setdefault("snow", {}).pop(d, None)
                if pr is not None:
                    s["precip"][d] = pr
                if sn is not None:
                    s["snow"][d] = sn
        if ok:
            checked.add(d)
    keep = set(dates)
    out_st = []
    for s in stations.values():
        s["precip"] = {k: v for k, v in sorted(s.get("precip", {}).items(), reverse=True) if k in keep}
        s["snow"] = {k: v for k, v in sorted(s.get("snow", {}).items(), reverse=True) if k in keep}
        if s["precip"] or s["snow"]:
            out_st.append(s)
    out_st.sort(key=lambda s: (s["place"], s["name"]))
    if not out_st and old.get("stations"):
        print("warning: no reports at all this time; keeping the old file", file=sys.stderr)
        return
    data = {"about": ABOUT, "updated": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "dates": dates, "checkedDates": sorted(checked & keep, reverse=True), "sources": SOURCES, "stations": out_st}
    old_cmp = dict(old); new_cmp = dict(data)
    for x in (old_cmp, new_cmp):
        x.pop("updated", None)
    if old_cmp == new_cmp and old.get("updated"):
        # Same reports: save at most every 6 hours so the page can say when they were last checked.
        last = datetime.datetime.fromisoformat(old["updated"].replace("Z", "+00:00"))
        if datetime.datetime.now(datetime.timezone.utc) - last < datetime.timedelta(hours=6):
            print("no change")
            return
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"saved {len(out_st)} stations, {len(checked)} days checked")


if __name__ == "__main__":
    main()
