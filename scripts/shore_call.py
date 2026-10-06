#!/usr/bin/env python3
"""The Shore Call (Oct. 6, 2026): La Porte Weather Now's morning call for the La Porte County shore,
saved in shore.json for laporteweathernow.com/lake-michigan.

One call each morning for Washington Park, Long Beach, Mount Baldy and the Michigan City harbor, made
around 5:30 a.m. Central by fixed rules from the National Weather Service's own forecasts and alerts.
It is our call, not a warning: NWS alerts are listed word for word next to it, and they always win.

  Swim    Beach season only (late May through September), from the NWS beach (surf zone) forecast's
          swim risk for the La Porte County shore (zone INZ103): High = STAY OUT, Moderate = CAUTION,
          Low = OK. A Beach Hazards or Rip Current Statement makes it STAY OUT.
  Piers   From the waves in the NWS nearshore forecast for Michigan City to New Buffalo (LMZ046):
          waves to 5 feet or more, a Beach Hazards, Rip Current, High Surf or Lakeshore Flood alert, or
          a Gale or Storm Warning = STAY OFF; waves to 3 or 4 feet, a Small Craft Advisory or a
          Lakeshore Flood Watch = CAUTION; 2 feet or less = OK.
  Boats   Small boats: waves to 4 feet or more, winds to 22 knots or more, or a Small Craft Advisory,
          Gale, Storm or Special Marine Warning = STAY IN; 3-foot waves, 15 to 21 knots or gusts to
          25 = CAUTION; 2 feet or less and under 15 knots = GO. The best hours come from the Weather
          Service's hour-by-hour forecast grid for the lake off Michigan City (6 a.m. to 8 p.m.).
  Band    Mid-October through April, when an inch of snow or more is forecast anywhere in the county
          in the next 24 hours (6 a.m. to 6 a.m.), or a winter alert is out: the NWS grid's snow for
          9 towns, and the towns, school districts and main roads in the heaviest snow.

The next morning, each call is graded against what was measured from 7 a.m. to 7 p.m.:
  Waves  Highest wave height at the Michigan City buoy (NDBC 45170): calm under 2.5 feet, choppy
         2.5 to 4.5, rough over 4.5. The call's forecast waves sort the same way: 2 feet or less
         calm, 3 or 4 choppy, 5 and up rough.
  Wind   Strongest hourly wind at the buoy, or at the Michigan City lighthouse station (MCYI3) when
         the buoy is out: light under 15 knots, breezy 15 to 21, strong 22 and up.
  Snow   The NWS snow reports in snow.json within 7 miles of each town: under an inch, 1 to 3
         inches, 3 and up.
  The same group is a hit, the next group over is close, two groups off is a miss. A day is a hit
  when everything graded hit, a miss when anything missed, close otherwise. When nothing was
  measured (the buoy is out for the winter, say) the day isn't graded, and the page says why.
  Calls made after 9 a.m. (a late start) are shown but not counted in the score.

  python3 scripts/shore_call.py          make today's call if it isn't made yet; grade past calls
  python3 scripts/shore_call.py force    the same, at any hour (used when the job itself changes)

Never fails the job over a slow or missing answer: whatever can't be read is left for the next run.
"""
import datetime
import json
import math
import os
import re
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "shore.json")
SNOW = os.path.join(HERE, "..", "snow.json")
CENTRAL = ZoneInfo("America/Chicago")
EASTERN = ZoneInfo("America/Indiana/Indianapolis")   # NWS Northern Indiana dates its products in Eastern time
UTC = datetime.timezone.utc
API = "https://api.weather.gov"
NDBC = "https://www.ndbc.noaa.gov/data/realtime2"
UA = "LaPorteWeatherNow/1.0 (+https://laporteweathernow.com)"
SHORE_ZONE, LAKE_ZONE = "INZ103", "LMZ046"
ALERT_ZONES = ["INZ103", "INZ203", "LMZ046", "LMZ043", "LMZ745"]
ZONE_NAMES = {"INZ103": "La Porte County shore", "INZ203": "southern La Porte County",
              "LMZ046": "Michigan City to New Buffalo", "LMZ043": "New Buffalo to St. Joseph",
              "LMZ745": "Burns Harbor to Michigan City"}
# NWS Northern Indiana forecast grid cells on the lake off Michigan City and Long Beach, tried in order
# until one has wave heights (the town cells on the shore below are land).
MARINE_CELLS = [(8, 65), (7, 65), (8, 66), (9, 66), (7, 64)]
# name, NWS Northern Indiana grid cell (same as the home page's town forecasts), and the town's middle
TOWNS = [
    ("Long Beach", 8, 64, 41.7456, -86.8514), ("Michigan City", 7, 63, 41.7344, -86.8731),
    ("Rolling Prairie", 17, 62, 41.6731, -86.6239), ("La Porte", 13, 58, 41.6081, -86.7189),
    ("Westville", 7, 55, 41.5375, -86.9050), ("Union Mills", 11, 53, 41.4942, -86.7786),
    ("Kingsford Heights", 15, 53, 41.4783, -86.6931), ("Wanatah", 8, 50, 41.4303, -86.8819),
    ("La Crosse", 8, 45, 41.3178, -86.8897),
]
DISTRICTS = [
    ("Michigan City Area Schools", ["Michigan City"]),
    ("La Porte Community Schools", ["La Porte", "Kingsford Heights"]),
    ("New Prairie United Schools", ["Rolling Prairie"]),
    ("MSD of New Durham Township (Westville)", ["Westville"]),
    ("South Central Community Schools (Union Mills)", ["Union Mills"]),
    ("Tri-Township Consolidated Schools (Wanatah)", ["Wanatah"]),
]
ROADS = {"Michigan City": ["I-94", "US 12", "US 421"], "La Porte": ["US 35", "SR 2", "SR 39"],
         "Westville": ["US 421", "SR 2"], "Wanatah": ["US 30", "US 421"], "Rolling Prairie": ["US 20"]}

SHORE_STAY_OFF = {"Beach Hazards Statement", "Rip Current Statement", "High Surf Advisory", "High Surf Warning",
                  "Lakeshore Flood Advisory", "Lakeshore Flood Warning"}
SHORE_CAUTION = {"Lakeshore Flood Watch", "Lakeshore Flood Statement"}
WIND_STAY_OFF = {"Gale Warning", "Storm Warning", "Hurricane Force Wind Warning"}
BOATS_STAY_IN = {"Small Craft Advisory", "Gale Warning", "Storm Warning", "Hurricane Force Wind Warning",
                 "Special Marine Warning", "Heavy Freezing Spray Warning", "Freezing Spray Advisory",
                 "Hazardous Seas Warning"}
BOATS_CAUTION = {"Gale Watch", "Storm Watch", "Hurricane Force Wind Watch", "Heavy Freezing Spray Watch",
                 "Dense Fog Advisory", "Marine Weather Statement", "Low Water Advisory"}
SWIM_STAY_OUT = {"Beach Hazards Statement", "Rip Current Statement", "High Surf Advisory", "High Surf Warning"}
WINTER = re.compile(r"Lake Effect Snow|Winter Storm|Winter Weather|Blizzard|Snow Squall|Ice Storm", re.I)

KEEP_CALLS = 120          # days of calls kept in shore.json (the score keeps counting past that)
DAY_HOURS = (6, 20)       # the call covers 6 a.m. to 8 p.m.
GRADE_HOURS = (7, 19)     # and is graded on 7 a.m. to 7 p.m.
COUNTS_BEFORE = 9         # calls made after 9 a.m. aren't scored
NEAR_MILES = 7
ABOUT = ("The Shore Call: La Porte Weather Now's morning call for the La Porte County shore (Washington Park, "
         "Long Beach, Mount Baldy, the Michigan City harbor), made by fixed rules from National Weather Service "
         "forecasts and graded the next day against the Michigan City buoy (NDBC 45170), the Michigan City "
         "lighthouse station (MCYI3) and NWS snow reports. Our call, not a warning: NWS alerts always win. "
         "Rules: laporteweathernow.com/lake-michigan#shore-rules. Saved by the 'Shore Call' job "
         "(scripts/shore_call.py).")

errors = []


# ---------- fetching ----------

def get(url, accept="application/geo+json", tries=3, timeout=30):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept, "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:   # network errors, 5xx, timeouts: wait and try again
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"{url} -> {last}")


def get_json(url, accept="application/geo+json"):
    return json.loads(get(url, accept=accept))


def attempt(name, fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        errors.append({"source": name, "error": str(e)[:300]})
        print(f"::warning title=Shore Call::{name}: {str(e)[:300]}")
        return None


# ---------- times ----------

def now_utc():
    return datetime.datetime.now(UTC).replace(microsecond=0)


def parse_time(s):
    return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def at(day, hour):
    """A Central time on a date."""
    return datetime.datetime(day.year, day.month, day.day, hour, tzinfo=CENTRAL)


def clock(t):
    """'6 a.m.', '2:30 p.m.', 'noon' in Central time."""
    t = t.astimezone(CENTRAL)
    if t.hour == 12 and t.minute == 0:
        return "noon"
    if t.hour == 0 and t.minute == 0:
        return "midnight"
    h = t.hour % 12 or 12
    return f"{h}{':%02d' % t.minute if t.minute else ''} {'a.m.' if t.hour < 12 else 'p.m.'}"


def when_text(t, today):
    """'4 p.m.', 'Wed. 4 p.m.' for another day, in Central time."""
    t = t.astimezone(CENTRAL)
    if t.date() == today:
        return clock(t)
    return f"{['Mon.', 'Tue.', 'Wed.', 'Thu.', 'Fri.', 'Sat.', 'Sun.'][t.weekday()]} {clock(t)}"


def span(valid_time):
    """NWS grid times like '2026-10-06T10:00:00+00:00/PT3H' -> (start, end)."""
    a, _, dur = str(valid_time).partition("/")
    start = parse_time(a)
    m = re.match(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$", dur or "") or None
    secs = 0
    if m:
        secs = ((int(m.group(1) or 0) * 24 + int(m.group(2) or 0)) * 60 + int(m.group(3) or 0)) * 60
    return start, start + datetime.timedelta(seconds=secs or 3600)


# ---------- NWS text products ----------

def latest_product(kind, max_age_hours):
    items = get_json(f"{API}/products/types/{kind}/locations/IWX", accept="application/ld+json").get("@graph") or []
    items.sort(key=lambda x: x.get("issuanceTime", ""), reverse=True)
    if not items:
        return None
    issued = parse_time(items[0]["issuanceTime"])
    if (now_utc() - issued).total_seconds() > max_age_hours * 3600:
        return None
    prod = get_json(f"{API}/products/{items[0]['id']}", accept="application/ld+json")
    return {"issued": issued, "text": prod.get("productText") or ""}


def ugc_codes(ugc):
    """'LMZ043-046-061415-' -> ['LMZ043', 'LMZ046']."""
    out, prefix = [], ""
    for tok in re.sub(r"\s+", "", ugc).split("-"):
        m = re.match(r"^([A-Z]{2}[CZ])?(\d{3})(?:>(\d{3}))?$", tok)
        if not m or (not m.group(1) and not prefix):
            continue
        if m.group(1):
            prefix = m.group(1)
        for n in range(int(m.group(2)), int(m.group(3) or m.group(2)) + 1):
            out.append(f"{prefix}{n:03d}")
    return out


def segment_for(text, zone):
    for seg in (text or "").split("$$"):
        m = re.search(r"(?:^|\n)([A-Z]{2}[CZ]\d{3}[\s\S]*?\d{6}-)", seg)
        if m and zone in ugc_codes(m.group(1)):
            return seg[m.end():]
    return None


PERIOD_RE = re.compile(r"\n\.([A-Z][A-Z ]*?)\.\.\.([\s\S]*?)(?=\n\.[A-Z][A-Z ]*?\.\.\.|\n[ \t]*\n|$)")
WEEKDAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


def periods_of(seg):
    return [(m.group(1).strip(), m.group(2)) for m in PERIOD_RE.finditer("\n" + (seg or ""))]


def period_date(name, issued_date):
    if re.search(r"TODAY|THIS (?:MORNING|AFTERNOON|EVENING)|TONIGHT|REST OF", name):
        return issued_date
    for i, d in enumerate(WEEKDAYS):
        if name.startswith(d):
            return issued_date + datetime.timedelta(days=(i - issued_date.weekday()) % 7)
    return None


def day_periods(seg, issued, day):
    """The daytime period for `day` and the night after it, as (name, text)."""
    issued_date = issued.astimezone(EASTERN).date()
    daytime = night = None
    for name, body in periods_of(seg):
        d = period_date(name, issued_date)
        text = re.sub(r"\s+", " ", body).strip()
        if d == day and "NIGHT" not in name and daytime is None:
            daytime = (name, text)
        elif d == day and "NIGHT" in name and night is None:
            night = (name, text)
    return daytime, night


def wind_numbers(text):
    """Highest sustained wind and gust (knots) named in a marine forecast period."""
    t = re.sub(r"\s+", " ", text or "")
    gust = 0
    for m in re.finditer(r"gusts?(?: up)? to (\d+) knots", t, re.I):
        gust = max(gust, int(m.group(1)))
    rest = re.sub(r"gusts?(?: up)? to \d+ knots", " ", t, flags=re.I)
    wind = 0
    for m in re.finditer(r"(\d+)(?: to (\d+))? knots", rest):
        wind = max(wind, int(m.group(2) or m.group(1)))
    return (wind or None), (gust or None)


def wave_number(text):
    """Highest wave height (feet) named in a forecast period: 'Waves 1 to 3 feet building to 2 to 4 feet' -> 4."""
    t = re.sub(r"\s+", " ", text or "")
    best = None
    for m in re.finditer(r"(\d+)(?: to (\d+))? (?:feet|foot)", t):
        v = int(m.group(2) or m.group(1))
        best = v if best is None else max(best, v)
    return best


def water_temp(seg):
    m = re.search(r"Michigan\s+City\s+is\s+(\d+)\s+degrees", seg or "", re.I)
    return int(m.group(1)) if m else None


def swim_facts(body):
    facts = {}
    for line in (body or "").split("\n"):
        m = re.match(r"^\s*([A-Za-z][A-Za-z ]*?)\*{0,2}\.{3,}\s*(.+?)\s*$", line)
        if m:
            facts[m.group(1).strip().lower()] = re.sub(r"\.$", "", m.group(2))
    if facts:
        return facts
    text = re.sub(r"\s+", " ", body or "").replace("*", "").strip()
    r = re.search(r"\b(Low|Moderate|High) swim risk\.?\s*", text, re.I)
    if r:
        facts["swim risk"] = r.group(1)
        text = text.replace(r.group(0), "")
    w = re.search(r"\bWave height ([^.]+)\.\s*", text, re.I)
    if w:
        facts["wave height"] = w.group(1)[0].upper() + w.group(1)[1:]
        text = text.replace(w.group(0), "")
    facts["text"] = text.strip()
    return facts


def beach_forecast(day):
    """Today's swim risk from the NWS beach (surf zone) forecast, or None out of season."""
    prod = latest_product("SRF", 30)
    if not prod:
        return None
    seg = segment_for(prod["text"], SHORE_ZONE)
    if not seg:
        return None
    issued_date = prod["issued"].astimezone(EASTERN).date()
    for name, body in periods_of(seg):
        if period_date(name, issued_date) == day and "NIGHT" not in name:
            f = swim_facts(body)
            risk = str(f.get("swim risk") or "").strip().lower()
            if risk not in ("low", "moderate", "high"):
                return None
            return {"issued": prod["issued"].astimezone(CENTRAL).isoformat(timespec="minutes"), "risk": risk.title(),
                    "waves": f.get("wave height"), "text": f.get("text") or f.get("weather")}
    return None


def lake_forecast(day):
    prod = latest_product("NSH", 20)
    if not prod:
        raise RuntimeError("no nearshore marine forecast from NWS Northern Indiana in the last 20 hours")
    seg = segment_for(prod["text"], LAKE_ZONE)
    if not seg:
        raise RuntimeError(f"the nearshore forecast has no {LAKE_ZONE} section")
    daytime, night = day_periods(seg, prod["issued"], day)
    if not daytime:
        raise RuntimeError("the nearshore forecast has no period for today")
    wind, gust = wind_numbers(daytime[1])
    return {"issued": prod["issued"].astimezone(CENTRAL).isoformat(timespec="minutes"),
            "period": daytime[0].title(), "today": daytime[1], "tonight": night[1] if night else None,
            "waveMaxFt": wave_number(daytime[1]), "windMaxKt": wind, "gustKt": gust,
            "ice": bool(re.search(r"\bice\b", daytime[1], re.I)), "waterF": water_temp(seg)}


# ---------- alerts ----------

def alerts():
    d = get_json(f"{API}/alerts/active?zone={','.join(ALERT_ZONES)}")
    seen, rows = set(), []
    for f in d.get("features") or []:
        p = f.get("properties") or {}
        if p.get("status") != "Actual" or p.get("messageType") == "Cancel":
            continue
        zones = [z for z in ((p.get("geocode") or {}).get("UGC") or []) if z in ALERT_ZONES]
        start = p.get("onset") or p.get("effective")
        end = p.get("ends") or p.get("expires")
        key = (p.get("event"), end)
        if key in seen:
            for r in rows:
                if (r["event"], r["ends"]) == key:
                    r["zones"] = sorted(set(r["zones"]) | set(zones))
            continue
        seen.add(key)
        rows.append({"event": p.get("event"), "headline": p.get("headline"), "sender": p.get("senderName"),
                     "onset": start, "ends": end, "zones": zones})
    return rows


def on_lake(a):
    return any(z.startswith("LMZ") for z in a["zones"])


def during(a, start, end):
    """Is alert `a` in effect at any time between start and end?"""
    try:
        s = parse_time(a["onset"]) if a.get("onset") else start
        e = parse_time(a["ends"]) if a.get("ends") else end
    except ValueError:
        return True
    return s < end and e > start


def alert_out(a, today):
    zones = [ZONE_NAMES[z] for z in a["zones"] if z in ZONE_NAMES]
    until = ""
    if a.get("ends"):
        try:
            until = "until " + when_text(parse_time(a["ends"]), today)
        except ValueError:
            pass
    starts = ""
    if a.get("onset"):
        try:
            s = parse_time(a["onset"])
            if s > now_utc():
                starts = "from " + when_text(s, today)
        except ValueError:
            pass
    return {"event": a["event"], "when": " ".join(x for x in (starts, until) if x), "zones": zones,
            "sender": a.get("sender") or "National Weather Service"}


# ---------- hour by hour on the lake ----------

def to_ft(v, uom):
    return None if v is None else v * 3.28084 if str(uom).endswith(":m") else v


def to_kt(v, uom):
    if v is None:
        return None
    u = str(uom)
    if u.endswith("km_h-1"):
        return v / 1.852
    if u.endswith("m_s-1"):
        return v * 1.943844
    return v


def hourly(field, conv):
    out = {}
    uom = (field or {}).get("uom", "")
    for v in (field or {}).get("values") or []:
        if v.get("value") is None:
            continue
        s, e = span(v.get("validTime"))
        t = s.replace(minute=0, second=0)
        while t < e:
            out[t.astimezone(UTC)] = conv(v["value"], uom)
            t += datetime.timedelta(hours=1)
    return out


def marine_grid(cache):
    cells = [tuple(cache)] if cache else []
    cells += [c for c in MARINE_CELLS if c not in cells]
    for x, y in cells:
        try:
            p = get_json(f"{API}/gridpoints/IWX/{x},{y}").get("properties") or {}
        except Exception as e:
            errors.append({"source": f"lake grid IWX/{x},{y}", "error": str(e)[:200]})
            continue
        waves = hourly(p.get("waveHeight"), to_ft)
        if waves:
            return [x, y], {"waves": waves, "wind": hourly(p.get("windSpeed"), to_kt),
                            "gust": hourly(p.get("windGust"), to_kt)}
    return None, None


def hour_status(ft, kt, gust):
    if ft is None and kt is None:
        return None
    if (ft or 0) >= 3.5 or (kt or 0) >= 21.5:
        return "stay"
    if (ft or 0) >= 2.5 or (kt or 0) >= 14.5 or (gust or 0) >= 24.5:
        return "caution"
    return "go"


def boat_hours(grid, day, lake_alerts):
    rows = []
    for h in range(*DAY_HOURS):
        t = at(day, h).astimezone(UTC)
        ft, kt, gust = grid["waves"].get(t), grid["wind"].get(t), grid["gust"].get(t)
        st = hour_status(ft, kt, gust)
        if any(a["event"] in BOATS_STAY_IN and on_lake(a) and during(a, t, t + datetime.timedelta(hours=1)) for a in lake_alerts):
            st = "stay"
        rows.append({"hour": h, "status": st, "waveFt": None if ft is None else round(ft, 1),
                     "windKt": None if kt is None else round(kt), "gustKt": None if gust is None else round(gust)})
    return rows


def best_window(rows):
    best, cur = None, None
    for r in rows:
        if r["status"] == "go":
            cur = [r["hour"], r["hour"] + 1] if cur is None else [cur[0], r["hour"] + 1]
            if best is None or cur[1] - cur[0] > best[1] - best[0]:
                best = list(cur)
        else:
            cur = None
    return best


# ---------- the call ----------

def lake_word(ft):
    if ft is None:
        return None
    return "calm" if ft <= 2 else "choppy" if ft <= 4 else "rough"


def wind_word(kt):
    if kt is None:
        return None
    return "light" if kt < 15 else "breezy" if kt < 22 else "strong"


def window_text(w, day):
    return f"{clock(at(day, w[0]))} to {clock(at(day, w[1]))}"


def swim_call(beach, today_alerts):
    if not beach:
        return {"call": None, "why": "No swim forecast: the Weather Service's beach forecast runs from just before "
                                     "Memorial Day weekend through September, and there are no lifeguards out of season."}
    stay = [a["event"] for a in today_alerts if a["event"] in SWIM_STAY_OUT]
    risk = beach["risk"]
    call = "STAY OUT" if stay or risk == "High" else "CAUTION" if risk == "Moderate" else "OK"
    why = f"The Weather Service's beach forecast has a {risk.lower()} swim risk"
    why += f", and a {stay[0]} is out." if stay else "."
    if call == "OK":
        why += " Low risk isn't no risk: swim near a lifeguard and away from the piers and breakwalls."
    return {"call": call, "risk": risk, "why": why}


def pier_call(lake, today_alerts, beach):
    ft = lake.get("waveMaxFt") if lake else None
    stay = [a["event"] for a in today_alerts if a["event"] in SHORE_STAY_OFF or (a["event"] in WIND_STAY_OFF and on_lake(a))]
    caution = [a["event"] for a in today_alerts if a["event"] in SHORE_CAUTION or (a["event"] == "Small Craft Advisory" and on_lake(a))]
    if stay or (ft is not None and ft >= 5):
        call = "STAY OFF"
    elif caution or (ft is not None and ft >= 3) or (beach and beach["risk"] == "Moderate"):
        call = "CAUTION"
    elif ft is not None:
        call = "OK"
    else:
        return {"call": None, "why": "The Weather Service's lake forecast has no wave heights today"
                                     + (" (ice on the lake)." if lake and lake.get("ice") else ".")}
    parts = []
    if ft is not None:
        parts.append(f"Waves up to {ft} {'foot' if ft == 1 else 'feet'} in the Weather Service's lake forecast")
    if stay or caution:
        names = stay + caution
        parts.append("a " + " and a ".join(names) + (" are out" if len(names) > 1 else " is out"))
    why = (", and ".join(parts) + ".") if parts else ""
    if call == "OK":
        why += " Piers are slick and the water is cold: stay back from the edge."
    return {"call": call, "why": why.strip()}


def boat_call(lake, today_alerts, rows, day):
    stay = [a["event"] for a in today_alerts if a["event"] in BOATS_STAY_IN and on_lake(a)]
    caution = [a["event"] for a in today_alerts if a["event"] in BOATS_CAUTION and on_lake(a)]
    ft = lake.get("waveMaxFt") if lake else None
    kt = lake.get("windMaxKt") if lake else None
    gust = lake.get("gustKt") if lake else None
    out = {"window": None, "windowText": None, "after": None}
    known = [r for r in (rows or []) if r["status"]]
    if len(known) >= 8:
        w = best_window(known)
        if w and w[1] - w[0] >= 3:
            later = [r["status"] for r in known if r["hour"] >= w[1]]
            out.update(call="GO", window=[f"{w[0]:02d}:00", f"{w[1]:02d}:00"], windowText=window_text(w, day),
                       after=("stay" if "stay" in later else "caution" if "caution" in later else None))
        else:
            n_stay = sum(1 for r in known if r["status"] == "stay")
            out["call"] = "STAY IN" if n_stay * 2 >= len(known) or stay else "CAUTION"
    elif lake:
        if stay or (ft or 0) >= 4 or (kt or 0) >= 22:
            out["call"] = "STAY IN"
        elif caution or (ft or 0) >= 3 or (kt or 0) >= 15 or (gust or 0) >= 25:
            out["call"] = "CAUTION"
        elif ft is not None or kt is not None:
            out["call"] = "GO"
        else:
            out["call"] = None
    else:
        out["call"] = None
    if lake and lake.get("today"):
        out["why"] = f"Weather Service lake forecast for {lake['period'].lower()}: {lake['today']}"
    else:
        out["why"] = "The Weather Service's lake forecast wasn't available this morning."
    if stay or caution:
        out["why"] += " " + " ".join(f"{e} out." for e in stay + caution)
    return out


def headline(c):
    parts = []
    lw = c.get("lake")
    sw, pi, bo = (c.get("swim") or {}).get("call"), (c.get("piers") or {}).get("call"), (c.get("boats") or {}).get("call")
    if sw:
        parts.append({"STAY OUT": "stay out of the water", "CAUTION": "swim with caution",
                      "OK": "OK to swim near a lifeguard"}[sw])
    if pi:
        parts.append({"STAY OFF": "stay off the piers", "CAUTION": "careful on the piers", "OK": "piers OK"}[pi])
    if bo == "GO" and c["boats"].get("windowText"):
        parts.append(f"small boats GO {c['boats']['windowText']}")
    elif bo:
        parts.append({"STAY IN": "small boats stay in", "CAUTION": "small boats use caution", "GO": "small boats GO"}[bo])
    lead = f"{lw.capitalize()} lake" if lw else "Lake forecast not out yet"
    text = f"{lead}: {', '.join(parts)}" if parts else lead
    text = text if text.endswith(".") else text + "."
    b = c.get("band")
    if b and b.get("headline"):
        text = b["headline"] + " " + text
    return text


# ---------- the snow band ----------

def band_season(day):
    return (day.month == 10 and day.day >= 15) or day.month in (11, 12, 1, 2, 3, 4)


def snow_between(field, a, b):
    total = 0.0
    uom = (field or {}).get("uom", "")
    for v in (field or {}).get("values") or []:
        if not v.get("value"):
            continue
        s, e = span(v.get("validTime"))
        lo, hi = max(s, a), min(e, b)
        if hi > lo:
            val = v["value"] / 25.4 if str(uom).endswith(":mm") else v["value"]
            total += val * (hi - lo).total_seconds() / (e - s).total_seconds()
    return total


def inches_text(x):
    if x < 0.5:
        return "under half an inch"
    if x < 1:
        return "under an inch"
    r = round(x * 2) / 2
    return "about 1 inch" if r == 1 else f"about {r:g} inches"


def snow_group(x):
    return "under 1 inch" if x < 1 else "1 to 3 inches" if x < 3 else "3 inches or more"


def band_call(day, today_alerts):
    if not band_season(day):
        return None
    a, b = at(day, 6), at(day, 6) + datetime.timedelta(days=1)
    towns = []
    for name, x, y, lat, lon in TOWNS:
        try:
            p = get_json(f"{API}/gridpoints/IWX/{x},{y}").get("properties") or {}
        except Exception as e:
            errors.append({"source": f"snow grid {name}", "error": str(e)[:200]})
            continue
        towns.append({"town": name, "inches": round(snow_between(p.get("snowfallAmount"), a, b), 1)})
    if len(towns) < 5:
        raise RuntimeError("couldn't read the snow forecast for most towns")
    winter = [x for x in today_alerts if WINTER.search(x["event"] or "") and
              set(x["zones"]) & {"INZ103", "INZ203"}]
    top = max(t["inches"] for t in towns)
    if top < 1 and not winter:
        return None
    cut = max(2.0, top / 2) if top >= 2 else 1.0
    for t in towns:
        t["group"] = "band" if t["inches"] >= cut else "edge" if t["inches"] >= 1 else "outside"
        t["text"] = inches_text(t["inches"])
    inside = [t["town"] for t in sorted(towns, key=lambda t: -t["inches"]) if t["group"] == "band"]
    districts = []
    for d, ts in DISTRICTS:
        amt = max((t["inches"] for t in towns if t["town"] in ts), default=None)
        if amt is not None:
            districts.append({"district": d, "inches": amt, "text": inches_text(amt),
                              "inBand": any(t["town"] in ts and t["group"] == "band" for t in towns)})
    roads = []
    for t in inside:
        for r in ROADS.get(t, []):
            if r not in roads:
                roads.append(r)
    lake_effect = any(re.search("Lake Effect", x["event"], re.I) for x in winter)
    if inside:
        names = inside[0] if len(inside) == 1 else ", ".join(inside[:-1]) + " and " + inside[-1]
        word = "Lake-effect band" if lake_effect else "Heaviest snow"
        hl = f"{word} today: {names}, {inches_text(max(t['inches'] for t in towns if t['group'] == 'band'))}."
    elif top >= 1:
        hl = f"Snow today: up to {inches_text(top)} in the county."
    else:
        hl = f"{winter[0]['event']} out; little snow in the forecast grid for our towns."
    return {"from": a.isoformat(timespec="minutes"), "to": b.isoformat(timespec="minutes"), "headline": hl,
            "towns": towns, "inBand": inside, "districts": districts, "roads": roads,
            "alerts": [x["event"] for x in winter]}


# ---------- grading ----------

def ndbc(station):
    text = get(f"{NDBC}/{station}.txt", accept="text/plain")
    lines = text.splitlines()
    if not lines:
        return []
    head = lines[0].lstrip("#").split()
    rows = []
    for line in lines[1:]:
        if line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < len(head):
            continue
        d = dict(zip(head, parts))
        try:
            t = datetime.datetime(int(d["YY"]), int(d["MM"]), int(d["DD"]), int(d["hh"]), int(d["mm"]), tzinfo=UTC)
        except (KeyError, ValueError):
            continue

        def val(k):
            v = d.get(k)
            try:
                return None if v in (None, "MM") else float(v)
            except ValueError:
                return None
        rows.append({"t": t, "wspd": val("WSPD"), "wvht": val("WVHT")})
    return rows


def measured(rows, day):
    a, b = at(day, GRADE_HOURS[0]).astimezone(UTC), at(day, GRADE_HOURS[1]).astimezone(UTC)
    inside = [r for r in rows if a <= r["t"] < b]
    waves = [r["wvht"] * 3.28084 for r in inside if r["wvht"] is not None]
    wave_hours = {r["t"].replace(minute=0) for r in inside if r["wvht"] is not None}
    by_hour = {}
    for r in inside:
        if r["wspd"] is not None:
            by_hour.setdefault(r["t"].replace(minute=0), []).append(r["wspd"] * 1.943844)
    wind = max((sum(v) / len(v) for v in by_hour.values()), default=None)
    return {"waveFt": round(max(waves), 1) if len(wave_hours) >= 6 else None,
            "windKt": round(wind) if len(by_hour) >= 6 else None}


def compare(called, seen, order):
    gap = abs(order.index(called) - order.index(seen))
    return "hit" if gap == 0 else "close" if gap == 1 else "miss"


def miles(lat1, lon1, lat2, lon2):
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def snow_reports():
    try:
        data = json.load(open(SNOW, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return [r for s in (data.get("storms") or []) for r in s.get("reports", [])]


def grade_band(band, reports):
    if reports is None:
        return None
    a = parse_time(band["from"])
    b = parse_time(band["to"]) + datetime.timedelta(hours=6)
    near = [r for r in reports if r.get("lat") is not None and a <= parse_time(r["time"]) <= b]
    order = ["under 1 inch", "1 to 3 inches", "3 inches or more"]
    by_town = {}
    for r in near:
        d, name = min((miles(x[3], x[4], float(r["lat"]), float(r["lon"])), x[0]) for x in TOWNS)
        if d <= NEAR_MILES:
            by_town.setdefault(name, []).append(r["inches"])
    towns = []
    for t in band["towns"]:
        got = by_town.get(t["town"])
        if not got:
            continue
        seen = max(got)
        towns.append({"town": t["town"], "called": snow_group(t["inches"]), "measuredIn": seen,
                      "measured": snow_group(seen), "result": compare(snow_group(t["inches"]), snow_group(seen), order)})
    if not towns:
        return {"result": None, "note": "No snow reports near our towns for this day."}
    res = [t["result"] for t in towns]
    return {"result": "miss" if "miss" in res else "hit" if all(r == "hit" for r in res) else "close", "towns": towns}


def grade(call, buoy, light, reports):
    day = datetime.date.fromisoformat(call["date"])
    f = call.get("forecast") or {}
    out, results, notes = {}, [], []
    b = measured(buoy, day) if buoy is not None else {"waveFt": None, "windKt": None}
    l = measured(light, day) if light is not None else {"waveFt": None, "windKt": None}
    if f.get("waveMaxFt") is not None and b["waveFt"] is not None:
        seen = "calm" if b["waveFt"] < 2.5 else "choppy" if b["waveFt"] < 4.5 else "rough"
        r = compare(lake_word(f["waveMaxFt"]), seen, ["calm", "choppy", "rough"])
        out["waves"] = {"called": lake_word(f["waveMaxFt"]), "calledFt": f["waveMaxFt"], "measuredFt": b["waveFt"],
                        "measured": seen, "where": "Michigan City buoy", "result": r}
        results.append(r)
    elif f.get("waveMaxFt") is not None:
        notes.append("Waves not graded: the Michigan City buoy didn't report (it's out of the water from late fall to spring).")
    wind_kt, where = (b["windKt"], "Michigan City buoy") if b["windKt"] is not None else (l["windKt"], "Michigan City lighthouse")
    if f.get("windMaxKt") is not None and wind_kt is not None:
        seen = wind_word(wind_kt)
        r = compare(wind_word(f["windMaxKt"]), seen, ["light", "breezy", "strong"])
        out["wind"] = {"called": wind_word(f["windMaxKt"]), "calledKt": f["windMaxKt"], "measuredKt": wind_kt,
                       "measured": seen, "where": where, "result": r}
        results.append(r)
    elif f.get("windMaxKt") is not None:
        notes.append("Wind not graded: no wind readings from the buoy or the lighthouse.")
    if call.get("band"):
        g = grade_band(call["band"], reports)
        if g:
            out["band"] = g
            if g.get("result"):
                results.append(g["result"])
            elif g.get("note"):
                notes.append(g["note"])
    out["result"] = (None if not results else "miss" if "miss" in results
                     else "hit" if all(r == "hit" for r in results) else "close")
    if notes:
        out["note"] = " ".join(notes)
    out["graded"] = now_utc().astimezone(CENTRAL).isoformat(timespec="minutes")
    return out


# ---------- main ----------

def make_call(now, old):
    day = now.date()
    lake = attempt("NWS nearshore marine forecast", lake_forecast, day)
    beach = attempt("NWS beach forecast", beach_forecast, day) if 5 <= day.month <= 9 else None
    al = attempt("NWS alerts", alerts)
    if lake is None and al is None:
        return None, old.get("marineCell")
    al = al or []
    day_a, day_b = at(day, DAY_HOURS[0]), at(day, DAY_HOURS[1])
    today_alerts = [a for a in al if during(a, day_a, day_b)]
    cell, grid = attempt("NWS lake forecast grid", marine_grid, old.get("marineCell")) or (None, None)
    rows = boat_hours(grid, day, today_alerts) if grid else None
    band = attempt("NWS snow forecast grid", band_call, day, al) if band_season(day) else None
    c = {
        "date": day.isoformat(),
        "made": now.isoformat(timespec="seconds"),
        "counts": now.hour < COUNTS_BEFORE,
        "lake": lake_word(lake["waveMaxFt"]) if lake else None,
        "swim": swim_call(beach, today_alerts),
        "piers": pier_call(lake, today_alerts, beach),
        "boats": boat_call(lake, today_alerts, rows, day),
        "band": band,
        "alerts": [alert_out(a, day) for a in al if a["event"] in (SHORE_STAY_OFF | SHORE_CAUTION)
                   or (a["event"] in (BOATS_STAY_IN | BOATS_CAUTION) and on_lake(a)) or WINTER.search(a["event"] or "")],
        "forecast": {"waveMaxFt": lake.get("waveMaxFt") if lake else None, "windMaxKt": lake.get("windMaxKt") if lake else None,
                     "gustKt": lake.get("gustKt") if lake else None, "waterF": lake.get("waterF") if lake else None},
        "nws": {"lake": {k: lake[k] for k in ("issued", "period", "today", "tonight")} if lake else None,
                "beach": beach},
        "hours": rows,
        "grade": None,
    }
    c["headline"] = headline(c)
    return c, cell or old.get("marineCell")


def slim(c):
    out = {k: c.get(k) for k in ("date", "made", "counts", "lake", "headline", "forecast", "grade")}
    for k in ("swim", "piers", "boats"):
        out[k] = {"call": (c.get(k) or {}).get("call")}
        if k == "boats" and (c.get(k) or {}).get("windowText"):
            out[k]["windowText"] = c[k]["windowText"]
    if c.get("band"):
        out["band"] = {k: c["band"].get(k) for k in ("from", "to", "headline", "inBand", "towns")}
    return out


def main():
    force = len(sys.argv) > 1 and sys.argv[1] == "force"
    now = now_utc().astimezone(CENTRAL)
    today = now.date()
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    calls = list(old.get("calls") or [])
    score = dict(old.get("score") or {"since": None, "graded": 0, "hit": 0, "close": 0, "miss": 0})
    changed = False

    # Grade calls from earlier days once their day is over (needs the buoy's readings).
    pending = [c for c in calls if c.get("grade") is None and
               (today - datetime.date.fromisoformat(c["date"])).days >= (2 if c.get("band") else 1)]
    if pending:
        buoy = attempt("Michigan City buoy (NDBC 45170)", ndbc, "45170")
        light = attempt("Michigan City lighthouse (NDBC MCYI3)", ndbc, "MCYI3")
        reports = snow_reports()
        for c in pending:
            age = (today - datetime.date.fromisoformat(c["date"])).days
            if buoy is None and light is None and age < 4:
                continue   # the readings didn't load; try again next run
            g = grade(c, buoy if buoy is not None else [], light if light is not None else [], reports)
            c["grade"] = g
            changed = True
            if c.get("counts") and g.get("result"):
                score["graded"] += 1
                score[g["result"]] += 1
                score["since"] = score.get("since") or c["date"]

    # Make today's call, once, in the morning (or at any hour when the job itself changed).
    have_today = any(c["date"] == today.isoformat() for c in calls)
    if not have_today and (force or 5 <= now.hour < 12):
        call, cell = make_call(now, old)
        if call:
            calls.insert(0, call)
            old["marineCell"] = cell
            changed = True
            print(f"Today's Shore Call: {call['headline']}")
        else:
            print("::warning title=Shore Call::Couldn't read the lake forecast or the alerts; no call yet. The next run will try again.")
    elif have_today:
        print("Today's call is already made.")
    else:
        print("No call due (the call is made between 5 a.m. and noon).")

    if not changed:
        print("shore.json unchanged.")
        return 0
    calls.sort(key=lambda c: c["date"], reverse=True)
    calls = [c if i < 14 else slim(c) for i, c in enumerate(calls)]
    for c in calls[1:]:
        c.pop("hours", None)
    data = {"about": ABOUT, "updated": now.isoformat(timespec="seconds"), "score": score,
            "marineCell": old.get("marineCell"), "calls": calls[:KEEP_CALLS], "errors": errors}
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"shore.json saved: {len(data['calls'])} call(s); score {score}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
