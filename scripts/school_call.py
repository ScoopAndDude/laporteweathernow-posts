#!/usr/bin/env python3
"""The School Delay Watch's record (Oct. 6, 2026): saves the watch's call for each school morning in
school.json and grades it against what La Porte County's school districts actually did.

The watch on laporteweathernow.com's home page estimates, from the National Weather Service forecast for
La Porte, whether the next school morning brings "delays unlikely", "delay possible" or "closing
possible". It never says a school is closed: only the districts decide. This job saves the call as it
stood at 8 p.m. the night before each school day (same rules as the home page; see LEVEL RULES below),
once, and never changes it.

What the districts did comes from school-outcomes.txt, kept by hand from the districts' own
announcements: one line per morning, e.g.

    2026-12-10  LPCSC delay, MCAS closed, NPUSC delay, Westville delay, South Central open, Tri-Township delay
    2026-12-11  all open

Grading: a morning's outcome is the biggest step any of the six districts took (open, delay, or closed /
e-learning day). The call's level is 0 (delays unlikely), 1 (delay possible) or 2 (closing possible).
Same step = held up; one step off = partly; two steps off = missed. Mornings we flagged (delay or
closing possible) wait for an outcome line; quiet mornings are scored only when a line was logged (so a
delay we didn't see coming counts once it's logged). A line saying "no school" means it isn't scored.

  python3 scripts/school_call.py          save the call when it's due (8 p.m. before a school day) and grade
  python3 scripts/school_call.py force    save the call for the next school morning now, if it isn't saved yet

LEVEL RULES (from the home page's School Delay Watch, Oct. 1, 2026), for 6 to 8 a.m.:
  closing possible: a Blizzard, Winter Storm, Ice Storm, Lake Effect Snow, Extreme Cold or Wind Chill
      Warning; 4+ inches of snow from 6 p.m. the night before to 8 a.m.; 0.1+ inch of ice; wind chill -20 or lower
  delay possible: a winter watch or advisory, a cold or wind chill advisory or watch, a dense or freezing
      fog advisory; 1.5+ inches of snow; any ice; wind chill -10 or lower; visibility a quarter mile or less
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "school.json")
OUTCOMES = os.path.join(HERE, "..", "school-outcomes.txt")
CENTRAL = ZoneInfo("America/Chicago")
UTC = datetime.timezone.utc
API = "https://api.weather.gov"
UA = "LaPorteWeatherNow/1.0 (+https://laporteweathernow.com)"
GRID = "IWX/13,58"                    # La Porte (same as the home page)
POINT = "41.6081,-86.7189"
WORDS = ["Delays unlikely", "Delay possible", "Closing possible"]
WARNINGS = re.compile(r"Blizzard Warning|Winter Storm Warning|Ice Storm Warning|Lake Effect Snow Warning|Extreme Cold Warning|Wind Chill Warning", re.I)
ADVISORIES = re.compile(r"Winter Storm Watch|Winter Weather Advisory|Lake Effect Snow (?:Advisory|Watch)|Freezing Rain Advisory|Cold Weather Advisory|Wind Chill Advisory|Wind Chill Watch|Extreme Cold Watch|Dense Fog Advisory|Freezing Fog Advisory", re.I)
DISTRICTS = {  # short names people use -> the district
    "lpcsc": "La Porte Community Schools", "la porte": "La Porte Community Schools",
    "mcas": "Michigan City Area Schools", "michigan city": "Michigan City Area Schools",
    "npusc": "New Prairie United Schools", "new prairie": "New Prairie United Schools",
    "westville": "MSD of New Durham Township", "new durham": "MSD of New Durham Township",
    "south central": "South Central Community Schools", "union mills": "South Central Community Schools",
    "tri-township": "Tri-Township Consolidated Schools", "tri township": "Tri-Township Consolidated Schools",
    "wanatah": "Tri-Township Consolidated Schools",
}
STEP = {"open": 0, "delay": 1, "closed": 2, "e-learning": 2}
CALL_HOUR = 20          # the call is saved at 8 p.m. the night before
KEEP = 220
ABOUT = ("The School Delay Watch's record for laporteweathernow.com: the watch's call for each La Porte County school "
         "morning as it stood at 8 p.m. the night before (from the National Weather Service forecast for La Porte), and "
         "what the districts did, from school-outcomes.txt. Our estimate, never an announcement: only the districts decide. "
         "Saved by the 'School Delay Watch record' job (scripts/school_call.py).")

errors = []


def get_json(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/geo+json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"{url} -> {last}")


def now_utc():
    return datetime.datetime.now(UTC).replace(microsecond=0)


def parse_time(s):
    return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def at(day, hour):
    return datetime.datetime(day.year, day.month, day.day, hour, tzinfo=CENTRAL)


def school_season(day):
    return not ((day.month == 6 and day.day > 10) or day.month == 7 or (day.month == 8 and day.day < 10))


def span(valid_time):
    a, _, dur = str(valid_time).partition("/")
    start = parse_time(a)
    m = re.match(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$", dur or "")
    secs = ((int(m.group(1) or 0) * 24 + int(m.group(2) or 0)) * 60 + int(m.group(3) or 0)) * 60 if m else 0
    return start, start + datetime.timedelta(seconds=secs or 3600)


def ours(field, v):
    if v is None:
        return None
    u = str((field or {}).get("uom", ""))
    if u.endswith("degC"):
        return v * 9 / 5 + 32
    if u.endswith(":mm"):
        return v / 25.4
    if u.endswith(":m"):
        return v / 1609.34
    return v


def total_between(field, a, b):
    s = 0.0
    for v in (field or {}).get("values") or []:
        st, en = span(v.get("validTime"))
        lo, hi = max(st, a), min(en, b)
        val = ours(field, v.get("value"))
        if hi > lo and val:
            s += val * (hi - lo).total_seconds() / (en - st).total_seconds()
    return s


def lowest_between(field, a, b):
    low = None
    for v in (field or {}).get("values") or []:
        st, en = span(v.get("validTime"))
        val = ours(field, v.get("value"))
        if en > a and st < b and val is not None and (low is None or val < low):
            low = val
    return low


def inches_text(x):
    r = round(x * 2) / 2
    return "about an inch" if r <= 1 else f"about {r:g} inches"


def make_call(morning, now):
    """The watch's level for a school morning, by the home page's rules."""
    bus0, bus1 = at(morning, 6), at(morning, 8)
    start = max(now, at(morning - datetime.timedelta(days=1), 18))
    p = get_json(f"{API}/gridpoints/{GRID}").get("properties") or {}
    feats = get_json(f"{API}/alerts/active?point={POINT}").get("features") or []
    snow = total_between(p.get("snowfallAmount"), start, bus1)
    ice = total_between(p.get("iceAccumulation"), start, bus1)
    chill = lowest_between(p.get("windChill"), bus0, bus1)
    vis = lowest_between(p.get("visibility"), bus0, bus1)
    level, why, seen = 0, [], set()

    def add(n, text):
        nonlocal level
        level = max(level, n)
        why.append(text)
    for f in feats:
        q = f.get("properties") or {}
        if q.get("status") not in (None, "Actual") or q.get("messageType") == "Cancel" or q.get("event") in seen:
            continue
        try:
            starts = parse_time(q.get("onset") or q.get("effective"))
            ends = parse_time(q["ends"]) if q.get("ends") else parse_time(q["expires"]) if q.get("expires") else None
        except (KeyError, ValueError, TypeError):
            continue
        if not (starts < bus1 and (ends is None or ends > bus0)):
            continue
        if WARNINGS.search(q["event"]):
            seen.add(q["event"])
            add(2, f"The Weather Service has a {q['event']} in effect for the morning.")
        elif ADVISORIES.search(q["event"]):
            seen.add(q["event"])
            add(1, f"The Weather Service has a {q['event']} in effect for the morning.")
    if snow >= 4:
        add(2, f"{inches_text(snow).capitalize()} of snow is forecast before 8 AM.")
    elif snow >= 1.5:
        add(1, f"{inches_text(snow).capitalize()} of snow is forecast before 8 AM.")
    elif snow >= 0.3:
        why.append("A little snow, under an inch and a half, is forecast before 8 AM.")
    if ice >= 0.1:
        add(2, f"Freezing rain could coat roads with about {ice:.2f} inch of ice.")
    elif ice > 0.005:
        add(1, "Freezing rain could leave a glaze of ice on roads and sidewalks.")
    if chill is not None and chill <= -20:
        add(2, f"Wind chills near {round(chill)}°F at bus time.")
    elif chill is not None and chill <= -10:
        add(1, f"Wind chills near {round(chill)}°F at bus time.")
    if vis is not None and vis <= 0.25:
        add(1, "Dense fog could cut visibility to a quarter mile or less at bus time.")
    if not why:
        why.append("No snow, ice, dense fog or dangerous cold in the forecast.")
    return {"morning": morning.isoformat(), "made": now.isoformat(timespec="seconds"), "level": level,
            "words": WORDS[level], "why": why,
            "forecast": {"snowIn": round(snow, 1), "iceIn": round(ice, 2),
                         "windChillF": None if chill is None else round(chill),
                         "visibilityMi": None if vis is None else round(vis, 2)},
            "grade": None}


def read_outcomes():
    """school-outcomes.txt -> {date: {"districts": {name: step word}, "noSchool": bool, "line": text}}."""
    out = {}
    if not os.path.exists(OUTCOMES):
        return out
    for raw in open(OUTCOMES, encoding="utf-8"):
        line = raw.split("#", 1)[0].strip()
        m = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(.+)$", line)
        if not m:
            continue
        date, rest = m.group(1), m.group(2).strip()
        entry = {"districts": {}, "noSchool": False, "line": rest}
        low = rest.lower()
        if re.search(r"\bno school\b", low):
            entry["noSchool"] = True
        elif re.fullmatch(r"all (?:open|on time|normal)", low):
            entry["allOpen"] = True
        else:
            for part in re.split(r"[,;]", rest):
                part = part.strip().lower()
                w = re.search(r"\b(open|on time|delay(?:ed)?|\d-hour delay|two-hour delay|closed|e-?learning)\s*$", part)
                if not w:
                    continue
                name = part[:w.start()].strip()
                word = w.group(1)
                step = ("open" if word in ("open", "on time") else "closed" if word == "closed"
                        else "e-learning" if "learning" in word else "delay")
                d = DISTRICTS.get(name)
                if d:
                    entry["districts"][d] = step
        out[date] = entry
    return out


def grade(call, outcome):
    if outcome.get("noSchool"):
        return {"result": None, "note": "No school that day.", "did": "No school"}
    if outcome.get("allOpen"):
        step, did = 0, "All six districts opened on time."
    elif outcome["districts"]:
        step = max(STEP[s] for s in outcome["districts"].values())
        did = "; ".join(f"{d}: {s}" for d, s in sorted(outcome["districts"].items()))
    else:
        return None
    gap = abs(call["level"] - step)
    return {"result": "hit" if gap == 0 else "close" if gap == 1 else "miss", "did": did,
            "outcome": ["open", "delay", "closing"][step]}


def main():
    force = len(sys.argv) > 1 and sys.argv[1] == "force"
    now = now_utc().astimezone(CENTRAL)
    today = now.date()
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    calls = list(old.get("calls") or [])
    changed = False

    tomorrow = today + datetime.timedelta(days=1)
    due = school_season(tomorrow) and tomorrow.weekday() < 5 and (force or now.hour >= CALL_HOUR)
    if due and not any(c["morning"] == tomorrow.isoformat() for c in calls):
        try:
            c = make_call(tomorrow, now)
            calls.insert(0, c)
            changed = True
            print(f"School Delay Watch for {tomorrow}: {c['words']} ({'; '.join(c['why'])})")
        except Exception as e:
            print(f"::warning title=School Delay Watch record::Couldn't read the forecast ({str(e)[:200]}); the next run will try again.")
    else:
        print("No call due (it's saved at 8 p.m. before a school day).")

    outcomes = read_outcomes()
    for c in calls:
        o = outcomes.get(c["morning"])
        g = grade(c, o) if o else None
        if g is None and c["level"] >= 1 and c["morning"] <= today.isoformat():
            g = {"result": None, "waiting": True, "note": "Waiting for what the districts did."}
        if g != c.get("grade"):
            c["grade"] = g
            changed = True
    if not changed:
        print("school.json unchanged.")
        return 0
    calls.sort(key=lambda c: c["morning"], reverse=True)
    scored = [c for c in calls if c.get("grade") and c["grade"].get("result")]
    score = {"scored": len(scored), "hit": sum(c["grade"]["result"] == "hit" for c in scored),
             "close": sum(c["grade"]["result"] == "close" for c in scored),
             "miss": sum(c["grade"]["result"] == "miss" for c in scored),
             "since": min((c["morning"] for c in scored), default=None)}
    data = {"about": ABOUT, "updated": now.isoformat(timespec="seconds"), "score": score, "calls": calls[:KEEP]}
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"school.json saved: {len(data['calls'])} call(s); {score}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
