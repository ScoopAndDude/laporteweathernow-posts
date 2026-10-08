#!/usr/bin/env python3
"""Tests for the Daily Video's words (scripts/daily_video.py): made-up forecasts, checked rules.

  python3 tools/video/test_plan.py

Checks that the opening line follows the rules (an alert first, then freeze/frost, rain, unusual
temperature, a nice day...), that a short-fused warning stops the video, and that every number the
voice says comes from the data. Needs no network.
"""
import datetime
import json
import os
import re
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import daily_video as dv  # noqa: E402

NOW = datetime.datetime(2026, 10, 9, 6, 5, tzinfo=dv.TZ)          # a Friday morning
NORMALS = {"station": {"id": "TEST", "name": "test", "km": 0},
           "days": {"10-09": [65.0, 44.5], "10-10": [64.6, 44.2], "10-11": [64.2, 43.9], "10-12": [63.8, 43.6]}}
FAILS = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


def periods(today=("Sunny", 70, 0, ""), tonight=("Mostly Clear", 48, 0, ""), sat=("Mostly Sunny", 72, 0),
            sun=("Partly Sunny", 70, 10), mon=("Sunny", 68, 0)):
    # NWS files La Porte as Eastern: 6 a.m./6 p.m. Eastern = 5 a.m./5 p.m. Central.
    out = []
    day0 = datetime.date(2026, 10, 9)
    rows = [("Today", True, today), ("Tonight", False, tonight), ("Saturday", True, sat), ("Saturday Night", False, ("Partly Cloudy", 55, 0)),
            ("Sunday", True, sun), ("Sunday Night", False, ("Mostly Clear", 50, 0)), ("Monday", True, mon), ("Monday Night", False, ("Clear", 45, 0))]
    for i, (name, isday, v) in enumerate(rows):
        start = datetime.datetime.combine(day0 + datetime.timedelta(days=i // 2), datetime.time(6 if isday else 18),
                                          tzinfo=datetime.timezone(datetime.timedelta(hours=-4)))
        end = start + datetime.timedelta(hours=12)
        out.append({"name": name, "start": start.isoformat(), "end": end.isoformat(), "isDaytime": isday,
                    "temperatureF": v[1], "rainChancePercent": v[2], "wind": "SW 5 to 10 mph", "short": v[0],
                    "detailed": v[3] if len(v) > 3 else ""})
    return out


def hours(pops):
    """Hour-by-hour from 6 a.m. Central; pops is a list of chances."""
    out = []
    t0 = datetime.datetime(2026, 10, 9, 6, 0, tzinfo=dv.TZ)
    for i, p in enumerate(pops):
        s = t0 + datetime.timedelta(hours=i)
        out.append({"start": s.isoformat(), "end": (s + datetime.timedelta(hours=1)).isoformat(), "temp": 50 + i,
                    "pop": p, "short": "Showers" if p >= 20 else "Sunny", "isDaytime": 6 <= s.hour < 18})
    return out


def data(ps, hs=None, alerts=None, yesterday_high=None, snapshot=None):
    sc = {"latest": {"date": "2026-10-08", "observed": {"high": yesterday_high}}} if yesterday_high is not None else {}
    return {"source": "test", "forecast": {"updated": NOW.isoformat(), "periods": ps}, "hours": hs or hours([0] * 24),
            "alerts": alerts or [], "observation": None, "snapshot": snapshot or {}, "scorecard": sc, "posts": {"posts": []}}


def numbers_ok(plan, d, normals):
    """Every number the voice says is in the data (or simple arithmetic on it, like a difference)."""
    allowed = set()
    for p in d["forecast"]["periods"]:
        allowed.add(p["temperatureF"])
        c = dv.bs.nws_chance(p["rainChancePercent"])
        if c:
            allowed.add(c)
        allowed.update(int(x) for x in re.findall(r"\d+", p.get("detailed") or ""))
    for h in d["hours"]:
        allowed.add(int(h["pop"]))
        t = dv.local(h["start"])
        allowed.update({t.hour % 12 or 12, (t.hour + 1) % 12 or 12})
    for v in (normals or {}).get("days", {}).values():
        allowed.update({int(round(v[0])), int(round(v[1]))})
    for p in d["forecast"]["periods"]:
        nhi, _ = dv.normals_for(dv.local(p["start"]).date(), normals)
        if nhi is not None:
            allowed.add(abs(int(round(p["temperatureF"] - nhi))))
    y = (d.get("scorecard") or {}).get("latest", {}).get("observed", {}).get("high")
    if y is not None:
        allowed.update(abs(p["temperatureF"] - y) for p in d["forecast"]["periods"])
    for a in d.get("alerts") or []:
        for k in ("ends", "expires", "onset"):
            if a.get(k):
                t = dv.local(a[k])
                allowed.update({t.hour % 12 or 12, t.minute})
    allowed.update({5, 1, 2, 3, 4, 9, 10, 11, 12, 2026})     # dates and "level N of 5"
    said = " ".join(s["say"] for s in plan["scenes"])
    found = [int(x) for x in re.findall(r"\d+", said)]
    bad = [n for n in found if n not in allowed]
    return not bad, bad


def plan_for(d, normals=NORMALS, now=NOW):
    return dv.build_plan(d, now, normals)


def spoken_clean(plan):
    return all(not re.search(r"[0-9°%]", s["spoken"]) for s in plan["scenes"])


def run():
    # 1. A nice day.
    d = data(periods())
    p = plan_for(d)
    check(p["hook"]["kind"] == "nice", f"nice day -> hook 'nice' (got {p['hook']['kind']}: {p['hook']['say']})")
    check(numbers_ok(p, d, NORMALS)[0], "nice day: every number is from the data")
    check(spoken_clean(p), "nice day: the voice gets words, not digits or symbols")

    # 2. Rain likely, mostly in the afternoon (hours from 6 a.m.: dry until 1 p.m., then 60-70%).
    d = data(periods(today=("Rain Showers Likely", 62, 70, "Rain showers likely, mainly after 1pm. High near 62.")),
             hs=hours([0, 0, 5, 10, 10, 15, 20, 60, 70, 70, 70, 65, 60]))
    p = plan_for(d)
    check(p["hook"]["kind"] == "rain", f"rain likely -> hook 'rain' (got {p['hook']['kind']})")
    check("after 1 p.m." in p["hook"]["small"], f"rain timing from the hour-by-hour forecast: {p['hook']['small']}")
    check(numbers_ok(p, d, NORMALS)[0], f"rain: every number is from the data {numbers_ok(p, d, NORMALS)[1]}")

    # 3. A freeze tonight beats a nice day.
    d = data(periods(tonight=("Clear", 30, 0)))
    p = plan_for(d)
    check(p["hook"]["kind"] == "freeze" and p["hook"]["big"] == "30°", f"freeze tonight -> hook 'freeze' (got {p['hook']})")

    # 4. Frost in NWS's words.
    d = data(periods(tonight=("Patchy Frost", 35, 0, "Patchy frost after 2am. Otherwise, clear, with a low around 35.")))
    p = plan_for(d)
    check(p["hook"]["kind"] == "frost" and p["hook"]["big"] == "Patchy frost", f"frost -> NWS's words (got {p['hook']['big']})")

    # 5. An alert comes first, in NWS's words, with its end time in Central.
    alert = {"id": "x1", "event": "Freeze Warning", "area": "Northern La Porte; Southern La Porte", "messageType": "Alert",
             "severity": "Moderate", "onset": "2026-10-09T23:00:00-05:00", "ends": "2026-10-10T09:00:00-05:00",
             "expires": "2026-10-09T15:00:00-05:00"}
    d = data(periods(tonight=("Clear", 28, 0)), alerts=[alert])
    p = plan_for(d)
    check(p["hook"]["kind"] == "alert" and p["hook"]["big"] == "Freeze Warning", f"alert first (got {p['hook']['kind']})")
    check("until 9 a.m. Saturday" in p["hook"]["say"], f"alert end time in Central: {p['hook']['say']}")
    check("Freeze Warning" in p["caption"], "the caption lists the alert")

    # 6. A short-fused warning: no video.
    tor = dict(alert, id="x2", event="Severe Thunderstorm Warning", onset=None, ends=None, expires="2026-10-09T06:45:00-05:00")
    d = data(periods(), alerts=[tor])
    with tempfile.TemporaryDirectory() as tmp:
        test = os.path.join(tmp, "test.json")
        out = os.path.join(tmp, "out")
        json.dump(dict(d, normals=NORMALS), open(test, "w"))
        gh = os.path.join(tmp, "gh.txt")
        os.environ["GITHUB_OUTPUT"] = gh
        dv.cmd_plan(out, ["--mode", "force", "--now", NOW.isoformat(), "--test", test])
        flags = open(gh).read()
        check("build=true" not in flags and not os.path.exists(os.path.join(out, "plan.json")),
              "Severe Thunderstorm Warning in effect -> no video")
        del os.environ["GITHUB_OUTPUT"]

    # 7. Unusually warm tomorrow (NOAA normals).
    d = data(periods(sat=("Mostly Sunny", 80, 0)))
    p = plan_for(d)
    check(p["hook"]["kind"] in ("normal", "nice"), f"warm Saturday considered (got {p['hook']['kind']})")
    opts = [h["kind"] for h in p["hookOptions"]]
    check("normal" in opts, f"'15° above normal' is among the options: {opts}")
    sat_hook = next(h for h in p["hookOptions"] if h["kind"] == "normal")
    check("15° above normal" in sat_hook["say"], f"normal hook says the right difference: {sat_hook['say']}")

    # 8. A big change from yesterday (airport reading via the scorecard).
    d = data(periods(today=("Mostly Sunny", 55, 0)), yesterday_high=72)
    p = plan_for(d)
    check(any(h["kind"] == "change" for h in p["hookOptions"]), "17° cooler than yesterday is among the options")

    # 9. Snow with NWS's amount.
    d = data(periods(today=("Snow Likely", 30, 70, "Snow likely. New snow accumulation of 1 to 3 inches possible."),
                     tonight=("Snow Likely", 25, 60)))
    p = plan_for(d)
    check(p["hook"]["kind"] == "snow", f"snow (with an amount) leads over a freezing night (got {p['hook']['kind']})")
    check(any(h["kind"] == "snow" and "1 to 3 inches" in h["say"] for h in p["hookOptions"]), "snow amount in NWS's words")

    # 10. Small helpers.
    check(dv.with_chance("A chance of rain showers, then partly cloudy", 30, "after 10 a.m.") ==
          "A 30% chance of rain showers after 10 a.m., then partly cloudy", "with_chance puts the chance and timing in place")
    check(dv.icon_for("Partly Sunny then Chance Rain Showers", True) == "sun-rain", "icon: partly sunny then showers")
    check(dv.icon_for("Mostly Cloudy", True) == "cloud", "icon: mostly cloudy")
    check(dv.icon_for("Mostly Clear", False) == "moon-small-cloud", "icon: mostly clear night")
    check(dv.icon_for("Slight Chance Showers And Thunderstorms", True) == "storm", "icon: storms")
    rise, sets = dv.sun_times(datetime.date(2026, 12, 21))
    check(rise.strftime("%H:%M") in ("07:10", "07:11") and sets.strftime("%H:%M") in ("16:19", "16:20"),
          f"sunrise/sunset Dec. 21 in La Porte ({rise:%H:%M}, {sets:%H:%M})")

    print(f"\n{len(FAILS)} failed." if FAILS else "\nALL PASSED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(run())
