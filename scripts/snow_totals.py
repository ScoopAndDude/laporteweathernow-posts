#!/usr/bin/env python3
"""La Porte County snow totals for laporteweathernow.com/snow-totals (Oct. 6, 2026).

Saves snow.json from the National Weather Service's local storm reports (LSRs) of snow in La Porte
County, as kept by the Iowa Environmental Mesonet at Iowa State University, which archives every
storm report the Weather Service issues. Only reports from NWS Northern Indiana (IWX), the office
that covers La Porte County. Reports are grouped into storms: a new storm starts after 36 hours
without a report.

  python3 scripts/snow_totals.py          update snow.json when it's due
  python3 scripts/snow_totals.py force    update now

Started by the Timer every tick, but it only asks the Mesonet once an hour from October through May
(the first tick of each hour) and once a day in summer (around 6 a.m.), so it's light on the archive.
Each run asks for the last 5 days and merges them in; last winter's storms are downloaded once and
kept. snow.json is only saved when the reports change, or every 6 hours so the page can say when they
were last checked. Never fails the job over a slow or missing answer: it prints a warning and keeps
the old file.
"""
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "snow.json")
CENTRAL = ZoneInfo("America/Chicago")
UTC = datetime.timezone.utc
API = "https://mesonet.agron.iastate.edu/geojson/lsr.geojson"
COUNTY_NAMES = {"laporte", "la porte"}
STORM_GAP_HOURS = 36
MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
SOURCE = {"label": "NWS local storm reports (Iowa Environmental Mesonet archive)",
          "url": "https://mesonet.agron.iastate.edu/lsr/"}
ABOUT = ("La Porte County, Indiana snow reports for laporteweathernow.com/snow-totals: every snow report in the "
         "National Weather Service's local storm reports from NWS Northern Indiana (IWX), from the Iowa Environmental "
         "Mesonet's archive, grouped into storms (a new storm starts after 36 hours without a report). Reports are "
         "from trained spotters, volunteer CoCoRaHS observers, NWS observers and the public, as the Weather Service "
         "logged them. Saved by the 'Snow totals' job (scripts/snow_totals.py).")


def now_utc():
    return datetime.datetime.now(UTC)


def season_of(d):
    """Snow season label and start for a date: Oct. 1 through Sept. 30, named like '2026-27'."""
    y = d.year if d.month >= 10 else d.year - 1
    return f"{y}-{(y + 1) % 100:02d}", datetime.datetime(y, 10, 1, tzinfo=CENTRAL)


def fetch(sts, ets):
    q = urllib.parse.urlencode({"wfos": "IWX", "sts": sts.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ"),
                                "ets": ets.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "laporteweathernow.com snow totals (GitHub Actions)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x > 0 else None


def snow_reports(geo):
    out = []
    for f in (geo or {}).get("features", []):
        p = f.get("properties") or {}
        county = re.sub(r"\s+", " ", str(p.get("county") or "")).strip().lower()
        if county not in COUNTY_NAMES or str(p.get("state") or p.get("st") or "").upper() != "IN":
            continue
        kind = str(p.get("typetext") or "").upper()
        if p.get("type") != "S" and "SNOW" not in kind:
            continue
        if "SQUALL" in kind:
            continue
        inches = num(p.get("magf") if p.get("magf") is not None else p.get("magnitude"))
        if inches is None or str(p.get("unit") or "inch").lower() not in ("inch", "inches", "in"):
            continue
        try:
            valid = datetime.datetime.fromisoformat(str(p["valid"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        out.append({
            "place": str(p.get("city") or "La Porte County").strip(),
            "inches": round(inches, 1),
            "time": valid.astimezone(CENTRAL).isoformat(timespec="minutes"),
            "source": str(p.get("source") or "").strip(),
            "remark": str(p.get("remark") or "").strip()[:200],
            "lat": p.get("lat"), "lon": p.get("lon"),
        })
    return out


def key(r):
    return (r["time"], r["place"].lower(), r["inches"])


def merge(old, new):
    seen = {key(r): r for r in old}
    for r in new:
        seen[key(r)] = r
    return sorted(seen.values(), key=lambda r: r["time"])


def date_label(a, b):
    a, b = datetime.datetime.fromisoformat(a), datetime.datetime.fromisoformat(b)
    if a.date() == b.date():
        return f"{MONTHS[a.month - 1]} {a.day}, {a.year}"
    if (a.year, a.month) == (b.year, b.month):
        return f"{MONTHS[a.month - 1]} {a.day}-{b.day}, {a.year}"
    if a.year == b.year:
        return f"{MONTHS[a.month - 1]} {a.day} - {MONTHS[b.month - 1]} {b.day}, {a.year}"
    return f"{MONTHS[a.month - 1]} {a.day}, {a.year} - {MONTHS[b.month - 1]} {b.day}, {b.year}"


def storms(reports):
    groups, cur, last = [], [], None
    for r in sorted(reports, key=lambda r: r["time"]):
        t = datetime.datetime.fromisoformat(r["time"])
        if cur and (t - last).total_seconds() > STORM_GAP_HOURS * 3600:
            groups.append(cur)
            cur = []
        cur.append(r)
        last = t
    if cur:
        groups.append(cur)
    out = []
    for g in groups:
        top = max(g, key=lambda r: r["inches"])
        out.append({"id": g[0]["time"][:10], "start": g[0]["time"], "end": g[-1]["time"],
                    "label": date_label(g[0]["time"], g[-1]["time"]),
                    "max": {"place": top["place"], "inches": top["inches"]},
                    "count": len(g), "reports": sorted(g, key=lambda r: -r["inches"])})
    return sorted(out, key=lambda s: s["start"], reverse=True)


def all_reports(data):
    return [r for s in (data.get("storms") or []) for r in s.get("reports", [])]


def main():
    force = len(sys.argv) > 1 and sys.argv[1] == "force"
    now = now_utc()
    local = now.astimezone(CENTRAL)
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    season, start = season_of(local)

    if not force and old.get("season") == season:
        winter = local.month in (10, 11, 12, 1, 2, 3, 4, 5)
        if not (local.minute < 15 if winter else (local.hour == 6 and local.minute < 15)):
            print("Snow totals aren't due this tick (hourly October-May, daily in summer).")
            return 0

    data = {"about": ABOUT, "updated": None, "source": SOURCE, "season": season,
            "seasonStart": start.date().isoformat(), "storms": [], "lastSeason": old.get("lastSeason")}
    keep = all_reports(old) if old.get("season") == season else []
    try:
        if old.get("season") == season and keep:
            since = max(start, datetime.datetime.fromisoformat(keep[-1]["time"]) - datetime.timedelta(days=5))
            since = min(since, now - datetime.timedelta(days=5))
        else:
            since = start
        fresh = snow_reports(fetch(max(since, start), now))
        # Last winter, once: kept so the page has something to show before this winter's first snow.
        prev_label, prev_start = season_of(start - datetime.timedelta(days=1))
        if not (data["lastSeason"] or {}).get("season") == prev_label:
            prev = snow_reports(fetch(prev_start, start))
            data["lastSeason"] = {"season": prev_label, "storms": storms(prev)}
    except Exception as e:   # the Mesonet is slow or down: keep what we have
        print(f"::warning title=Snow totals::Couldn't reach the storm-report archive ({e}); snow.json unchanged.")
        return 0

    data["storms"] = storms(merge(keep, [r for r in fresh if r["time"] >= start.isoformat(timespec="minutes")]))
    same = dict(old, updated=None) == dict(data, updated=None)
    if same and old.get("updated") and not force:
        age = (now - datetime.datetime.fromisoformat(old["updated"])).total_seconds()
        if age < 6 * 3600:
            print("No new snow reports; snow.json unchanged.")
            return 0
    data["updated"] = now.astimezone(CENTRAL).isoformat(timespec="seconds")
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    n = sum(s["count"] for s in data["storms"])
    print(f"snow.json: {len(data['storms'])} storm(s) and {n} report(s) this season ({season}); "
          f"last season {data['lastSeason']['season'] if data['lastSeason'] else 'none'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
