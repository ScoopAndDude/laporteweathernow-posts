#!/usr/bin/env python3
"""Grades every Daily Scoop forecast against what the La Porte airport (KPPO) recorded
and saves scorecard.json, which the homepage's "how we've done" line and the morning
Scoop's "Yesterday we said..." line read.

Same rules as the Track Record page (scorecard.js on the site), in plain words:
- A day is scored against the most recent Scoop that went live (its "posted" time)
  BEFORE that day began in La Porte. Posts from the day itself don't count.
- High = the highest temperature of that calendar day, low = the lowest.
- A temperature forecast held up if the reading was within 3 degrees F of it. A range
  like [47, 49] is scored from its middle.
- Rain: at 50% or higher it should have rained (0.01 in or more); at 20% or lower it
  should have stayed dry. 21-49% isn't scored.
- Days the station has no data for aren't scored.
- Days the station barely reported aren't scored either (added Oct. 11, 2026): a day counts
  only if the airport sent temperatures in at least MIN_HOURS of its 24 hours. On Oct. 10,
  2026 it sent 4 readings, all after 11 PM, and the archive's daily summary made that last
  hour look like the whole day. Those days are listed in scorecard.json's "thinDays" so the
  Track Record page skips them too.
Also (added Oct. 2, 2026):
- "bias": our average error (forecast minus what the airport recorded) for highs and lows
  over the last 30 graded days. consensus.py nudges the model blend by it once there are
  14+ days. Positive = we ran too warm.
- "morning": the SAME-DAY forecast saved at about 5 a.m. in morning-log.json (what
  Hard Hat Weather's calls are made from), graded the same way: the high within 3 degrees,
  and the rain call (the higher chance of the day and the night after it).
Observations come from the Iowa Environmental Mesonet's archive of airport reports.
"""
import datetime
import json
import math
import os
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
POSTS = os.path.join(HERE, "..", "scoop-posts.json")
MORNING_LOG = os.path.join(HERE, "..", "morning-log.json")
BIAS_MIN_DAYS = 14   # same as consensus.py: the blend is nudged only after this many graded days
OUT = os.path.join(HERE, "..", "scorecard.json")
TZ = ZoneInfo("America/Chicago")
MAIN = ("PPO", "IN_ASOS", "La Porte Municipal Airport (KPPO)")
NEIGHBORS = [("SBN", "IN_ASOS", "South Bend airport"), ("VPZ", "IN_ASOS", "Valparaiso airport")]
TOLERANCE = 3
MIN_HOURS = 18      # hours of the day (of 24) with at least one temperature report, or the day isn't graded
WINDOW = 30
UA = "LaPorteWeatherNow/1.0 (+https://laporteweathernow.com)"


def jround(x):
    """Rounds like JavaScript's Math.round (72.5 -> 73), so numbers match the Track Record page."""
    return math.floor(x + 0.5)


def get_json(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"{url} -> {last}")


def start_of_day(ymd):
    y, m, d = map(int, ymd.split("-"))
    return datetime.datetime(y, m, d, tzinfo=TZ)


def fc_range(v):
    if isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
        return (min(v), max(v))
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return (v, v)
    return None


def collect_forecasts(posts):
    best = {}
    for p in posts:
        if not p or p.get("type") == "weekly" or not isinstance(p.get("forecasts"), list):
            continue
        try:
            posted = datetime.datetime.fromisoformat(p["posted"])
        except Exception:
            continue
        for f in p["forecasts"]:
            date = (f or {}).get("date", "")
            if len(date) != 10:
                continue
            if not posted < start_of_day(date):
                continue            # must be public before the day starts
            cur = best.get(date)
            if not cur or posted > cur["posted"]:
                best[date] = {"date": date, "high": f.get("high"), "low": f.get("low"), "rain": f.get("rain"),
                              "posted": posted, "post": p.get("date"),
                              "leadDays": (datetime.date.fromisoformat(date) - posted.astimezone(TZ).date()).days}
    return sorted(best.values(), key=lambda r: r["date"], reverse=True)


def months_between(first, last):
    y, m = map(int, first.split("-")[:2])
    ly, lm = map(int, last.split("-")[:2])
    out = []
    while (y, m) <= (ly, lm):
        out.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def station_days(station, months):
    sid, net, _ = station
    days = {}
    for y, m in months:
        data = get_json(f"https://mesonet.agron.iastate.edu/api/1/daily.json?station={sid}&network={net}&year={y}&month={m}")
        for row in data.get("data") or []:
            if row and row.get("date"):
                days[row["date"]] = row
    return days


def hours_reported(date):
    """How many of the date's 24 local hours have at least one temperature report from the airport."""
    sid, net, _ = MAIN
    data = get_json(f"https://mesonet.agron.iastate.edu/api/1/obhistory.json?station={sid}&network={net}&date={date}&full=1")
    hours = set()
    for r in data.get("data") or []:
        lv = (r or {}).get("local_valid") or ""
        if r.get("tmpf") is not None and lv[:10] == date:
            hours.add(lv[11:13])
    return len(hours)


def check_coverage(dates, today):
    """{date: hours reported} for each date. Days at least 3 days old come from the last
    scorecard.json when it has them (the archive rarely changes after that)."""
    try:
        cache = json.load(open(OUT, encoding="utf-8")).get("coverage") or {}
    except Exception:
        cache = {}
    settled = (datetime.date.fromisoformat(today) - datetime.timedelta(days=3)).isoformat()
    out = {}
    for d in sorted(set(dates)):
        if d <= settled and isinstance(cache.get(d), int):
            out[d] = cache[d]
            continue
        try:
            out[d] = hours_reported(d)
        except Exception as e:
            print(f"!! hours reported on {d}: {e}", file=sys.stderr)   # unknown: graded as before
    for d, h in cache.items():
        out.setdefault(d, h)
    return out


def observed_on(date, main, neighbors):
    row = main.get(date)
    if not row or row.get("max_tmpf") is None or row.get("min_tmpf") is None:
        return {"missing": True}
    hours = row.get("_hours")
    if isinstance(hours, int) and hours < MIN_HOURS:
        return {"missing": True, "readingHours": hours}
    out = {"missing": False, "high": jround(row["max_tmpf"]), "low": jround(row["min_tmpf"])}
    precip = row.get("precip")
    if precip is not None and precip >= 0.01:
        out.update(rained=True, rainText=f"{precip:.2f} in of rain")
    elif precip is not None:
        out.update(rained=False, rainText="no measurable rain")
    else:
        amounts = [(n.get(date) or {}).get("precip") if n is not None else None for n in neighbors]
        if len(amounts) < len(NEIGHBORS) or any(a is None for a in amounts):
            out.update(rained=None, rainText="no rain report, couldn't double-check (not scored)")
        elif all(a >= 0.10 for a in amounts):
            out.update(rained=None, rainText="rain nearby, none reported at La Porte (not scored)")
        else:
            out.update(rained=False, rainText="no rain recorded")
    return out


def temp_check(forecast, observed):
    r = fc_range(forecast)
    if not r or observed is None:
        return None
    off = jround(abs(observed - (r[0] + r[1]) / 2) * 10) / 10
    return {"off": off, "hit": off <= TOLERANCE}


def rain_check(chance, rained):
    if not isinstance(chance, (int, float)) or isinstance(chance, bool) or rained is None:
        return None
    if chance >= 50:
        return {"hit": rained is True, "kind": "likely"}
    if chance <= 20:
        return {"hit": rained is False, "kind": "dry"}
    return {"hit": None, "kind": "tossup"}


def score(f, main, neighbors, today):
    if f["date"] >= today:
        return {"status": "pending"}
    o = observed_on(f["date"], main, neighbors)
    if o["missing"]:
        return {"status": "nodata", **({"readingHours": o["readingHours"]} if "readingHours" in o else {})}
    high, low, rain = temp_check(f["high"], o["high"]), temp_check(f["low"], o["low"]), rain_check(f["rain"], o["rained"])
    parts = [x for x in (high, low, rain if rain and rain["hit"] is not None else None) if x]
    misses = sum(1 for x in parts if not x["hit"])
    verdict = "none" if not parts else "hit" if misses == 0 else "miss" if misses == len(parts) else "close"
    return {"status": "scored", "observed": o, "high": high, "low": low, "rain": rain, "verdict": verdict, "anyScored": bool(parts)}


def summarize(rows):
    s = {"days": 0, "highs": [0, 0], "lows": [0, 0], "rainLikely": [0, 0], "rainDry": [0, 0]}
    he, le = [], []
    for r in rows:
        sc = r["score"]
        if sc.get("status") != "scored" or not sc.get("anyScored"):
            continue
        s["days"] += 1
        for key, part, errs in (("highs", sc["high"], he), ("lows", sc["low"], le)):
            if part:
                s[key][1] += 1
                s[key][0] += 1 if part["hit"] else 0
                errs.append(part["off"])
        rain = sc.get("rain")
        if rain and rain["kind"] in ("likely", "dry") and rain["hit"] is not None:
            k = "rainLikely" if rain["kind"] == "likely" else "rainDry"
            s[k][1] += 1
            s[k][0] += 1 if rain["hit"] else 0
    s["rain"] = [s["rainLikely"][0] + s["rainDry"][0], s["rainLikely"][1] + s["rainDry"][1]]
    s["highAvgOff"] = round(sum(he) / len(he), 1) if he else None
    s["lowAvgOff"] = round(sum(le) / len(le), 1) if le else None
    return s


def bias_of(rows):
    out = {"days": 0, "ready": False}
    for key in ("high", "low"):
        errs = []
        for r in rows:
            sc = r["score"]
            fr = fc_range(r.get(key))
            if sc.get("status") == "scored" and fr and sc["observed"].get(key) is not None:
                errs.append((fr[0] + fr[1]) / 2 - sc["observed"][key])
        out[key] = round(sum(errs) / len(errs), 1) if errs else None
        out[key + "Days"] = len(errs)
    out["days"] = min(out["highDays"], out["lowDays"])
    out["ready"] = out["days"] >= BIAS_MIN_DAYS
    out["note"] = ("Average of (forecast minus airport reading) over the last 30 graded days; positive means we ran warm. "
                   f"Used to nudge the model blend once {BIAS_MIN_DAYS}+ days are graded.")
    return out


def morning_grades(main_days, neighbors, today, start):
    try:
        log = json.load(open(MORNING_LOG, encoding="utf-8")).get("days") or []
    except Exception:
        return None
    days = []
    s = {"days": 0, "nwsHighs": [0, 0], "blendHighs": [0, 0], "rain": [0, 0]}
    ne, be = [], []
    for e in log:
        date = e.get("date") or ""
        if not date or date >= today:
            continue
        o = observed_on(date, main_days, neighbors)
        row = {"date": date, "said": {"nwsHigh": (e.get("nws") or {}).get("high"),
                                      "blendHigh": (e.get("blend") or {}).get("high"),
                                      "rain": (e.get("nws") or {}).get("rain")}}
        if o["missing"]:
            row["status"] = "nodata"
            if "readingHours" in o:
                row["readingHours"] = o["readingHours"]
            days.append(row)
            continue
        nh = temp_check(row["said"]["nwsHigh"], o["high"])
        bh = temp_check(row["said"]["blendHigh"], o["high"])
        rc = rain_check(row["said"]["rain"], o["rained"])
        row.update(status="scored", observed={"high": o["high"], "rained": o["rained"], "rainText": o["rainText"]},
                   nwsHigh=nh, blendHigh=bh, rain=rc)
        days.append(row)
        if date < start:
            continue
        s["days"] += 1
        for key, part, errs in (("nwsHighs", nh, ne), ("blendHighs", bh, be)):
            if part:
                s[key][1] += 1
                s[key][0] += 1 if part["hit"] else 0
                errs.append(part["off"])
        if rc and rc["hit"] is not None:
            s["rain"][1] += 1
            s["rain"][0] += 1 if rc["hit"] else 0
    s["nwsHighAvgOff"] = round(sum(ne) / len(ne), 1) if ne else None
    s["blendHighAvgOff"] = round(sum(be) / len(be), 1) if be else None
    return {"about": ("Same-morning forecasts (saved about 5 a.m., when Hard Hat Weather makes its calls), graded "
                      "against the La Porte airport: today's high within 3 degrees, and the rain call (50%+ should "
                      "rain, 20% or less should stay dry). nws = the NWS forecast; blend = our model blend (from Oct. 2, 2026)."),
            "last30": s, "days": days[:60]}


def main():
    posts = json.load(open(POSTS, encoding="utf-8")).get("posts") or []
    forecasts = collect_forecasts(posts)
    now = datetime.datetime.now(TZ)
    today = now.date().isoformat()
    past = [f for f in forecasts if f["date"] < today]
    try:
        for e in json.load(open(MORNING_LOG, encoding="utf-8")).get("days") or []:
            if e.get("date") and e["date"] < today:
                past.append({"date": e["date"]})      # so the airport data covers the morning log too
    except Exception:
        pass
    if not past:
        print("No forecasts to grade yet.")
        return
    months = months_between(min(f["date"] for f in past), max(f["date"] for f in past))
    main_days = station_days(MAIN, months)          # failure here = no scorecard; keep the old file
    coverage = check_coverage([f["date"] for f in past], today)
    for d, h in coverage.items():
        if d in main_days and isinstance(h, int):
            main_days[d]["_hours"] = h
    neighbors = []
    for n in NEIGHBORS:
        try:
            neighbors.append(station_days(n, months))
        except Exception as e:
            print(f"!! {n[2]}: {e}", file=sys.stderr)
            neighbors.append(None)                  # unknown, never mistaken for "dry"
    rows = [dict(f, score=score(f, main_days, neighbors, today)) for f in forecasts]
    start = (now.date() - datetime.timedelta(days=WINDOW)).isoformat()
    recent = [r for r in rows if start <= r["date"] < today]
    scored = [r for r in rows if r["score"].get("status") == "scored" and r["score"].get("anyScored")]

    def day_out(r):
        sc = r["score"]
        out = {"date": r["date"], "fromPost": r["post"], "leadDays": r["leadDays"],
               "forecast": {"high": r["high"], "low": r["low"], "rain": r["rain"]}, "status": sc["status"]}
        if "readingHours" in sc:
            out["readingHours"] = sc["readingHours"]
        if sc["status"] == "scored":
            o = sc["observed"]
            out.update(observed={"high": o["high"], "low": o["low"], "rained": o["rained"], "rainText": o["rainText"]},
                       high=sc["high"], low=sc["low"], rain=sc["rain"], verdict=sc["verdict"])
        return out

    card = {
        "about": ("Daily Scoop forecasts graded against the La Porte airport (KPPO), same rules as "
                  "laporteweathernow.com/track-record: temperatures count if within 3 degrees F; rain calls "
                  "count at 50%+ (should rain) and 20% or less (should stay dry). Made by scripts/scorecard.py."),
        "generated": now.replace(microsecond=0).isoformat(),
        "station": MAIN[2],
        "tolerance": TOLERANCE,
        "since": min(r["date"] for r in scored) if scored else None,
        "window": {"days": WINDOW, "from": start, "to": (now.date() - datetime.timedelta(days=1)).isoformat()},
        "last30": summarize(recent),
        "allTime": summarize(rows),
        "bias": bias_of(recent),
        "morning": morning_grades(main_days, neighbors, today, start),
        "latest": day_out(scored[0]) if scored else None,
        "days": [day_out(r) for r in rows[:60]],
        "readingRule": (f"A day is graded only if the airport reported temperatures in at least {MIN_HOURS} of its "
                        "24 hours. thinDays lists the days that fell short (date: hours reported); coverage keeps "
                        "every checked day's count."),
        "thinDays": {d: h for d, h in sorted(coverage.items()) if isinstance(h, int) and h < MIN_HOURS},
        "coverage": {d: h for d, h in sorted(coverage.items()) if isinstance(h, int)},
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(card, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    s = card["last30"]
    print(f"Saved scorecard.json: {s['days']} days scored; highs {s['highs']}, lows {s['lows']}, rain {s['rain']}.")


if __name__ == "__main__":
    main()
