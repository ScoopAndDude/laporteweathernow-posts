#!/usr/bin/env python3
"""The Daily Video: a short La Porte forecast video (about 20 seconds, 1080x1920) for Facebook and
Instagram Reels, made every morning from the National Weather Service and read by the weather radio's
voice. Added Oct. 8, 2026 (Scoop: "Make it automatic").

  python3 scripts/daily_video.py plan OUTDIR [--last DIR] [--mode auto|preview|force] [--now ISO] [--test FILE]
      Gather the official weather and write OUTDIR/plan.json: the opening line (the "hook"), the
      scenes, the words the voice reads and the post's caption. Sets the GitHub output build=true|false.
      --last DIR is the "video" branch as it stands (yesterday's or today's record, normals, map).
      auto makes one video a day, only between 5:45 and 9:30 AM Central; preview and force always make one.
      --test FILE plans from a saved data file instead of asking NWS (tools/video/test_plan.py).
  python3 scripts/daily_video.py voice OUTDIR     Record the words (Kokoro-82M, voice af_heart, like the radio).
  python3 scripts/daily_video.py silent OUTDIR    No voice: times each scene from its word count (for testing).
  python3 scripts/daily_video.py render OUTDIR    Draw it and save OUTDIR/laporte-<date>.mp4 (scripts/video_render.py).
  python3 scripts/daily_video.py post OUTDIR      Post it (scripts/video_post.py; needs the META_TOKEN secret).

Rules, the same as the radio and the Daily Scoop:
- Every number comes from the NWS forecast and hour-by-hour forecast, NWS alerts for La Porte County,
  NOAA's Storm Prediction Center, the La Porte airport, or NOAA's 1991-2020 normals. Nothing is made up,
  and the pictures are drawn from the data (no AI pictures). The radar is NOAA's own.
- The opening line is the most useful true thing about the next day and a half, picked by fixed rules
  (HOOKS below): an NWS alert first, then freeze or frost, snow, the Storm Prediction Center's risk,
  heat, wind, likely rain, then a big change, an unusual temperature, the weekend's best day, a nice day.
  No fear words and never a warning of our own: when there's an alert, the alert is the news, in NWS's words.
- No video while a short-fused warning (tornado, severe thunderstorm, flash flood, snow squall, extreme
  wind) is in effect for La Porte County: a recorded video would be out of date within minutes, and
  people need the warning itself (phone alerts, NOAA Weather Radio, the Alerts page).
- If NWS can't give both the forecast and the alerts, there's no video that morning.
"""
import datetime
import json
import os
import re
import shutil
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backup_scoop as bs  # noqa: E402
import nws_snapshot as ns  # noqa: E402
import radio_broadcast as rb  # noqa: E402

TZ = bs.TZ
REPO = os.path.normpath(os.path.join(HERE, ".."))
CONFIG_PATH = os.path.join(REPO, "video", "config.json")
SNAPSHOT = os.path.join(REPO, "nws-snapshot.json")
SCORECARD = os.path.join(REPO, "scorecard.json")
AUTO_WINDOW = ("05:45", "09:30")            # auto mode makes the day's video only in this window (Central)
SHORT_FUSED = ("Tornado Warning", "Severe Thunderstorm Warning", "Flash Flood Warning", "Extreme Wind Warning",
               "Snow Squall Warning", "Dust Storm Warning", "Tornado Emergency", "Flash Flood Emergency")
WEEKDAYS = bs.WEEKDAYS
SHORT_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
AP_MONTHS = bs.AP_MONTHS
NCEI = "https://www.ncei.noaa.gov/access/services"
HASHTAGS = "#LaPorte #LaPorteIndiana #LaPorteCounty #IndianaWeather #NWIndiana"
CUTOFFS = {"hook": 2.4, "period": 3.2, "radar": 3.8, "days": 3.6, "end": 2.6}   # shortest each scene can be (s)
LEAD, TAIL = 0.10, 0.30                     # voice starts this far into a scene; the scene runs this long after it


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def dt(s):
    return datetime.datetime.fromisoformat(s)


def local(s):
    return dt(s).astimezone(TZ) if isinstance(s, str) else s.astimezone(TZ)


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def config():
    c = load_json(CONFIG_PATH, {}) or {}
    c.setdefault("post", {"facebook": True, "instagram": True})
    c.setdefault("graphVersion", "v25.0")
    return c


def set_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def ap_day(d):
    """Friday, Oct. 9"""
    return f"{WEEKDAYS[d.weekday()]}, {AP_MONTHS[d.month - 1]} {d.day}"


def deg(t):
    return f"{int(t)}°" if t is not None else "--"


def upper_first(s):
    s = (s or "").strip()
    return s[:1].upper() + s[1:] if s else s


def lower_first(s):
    s = (s or "").strip()
    return s[:1].lower() + s[1:] if s and not s.startswith("I ") else s


def friendly(short):
    """NWS's short forecast in plain words: 'Chance Rain Showers then Partly Cloudy' ->
    'A chance of rain showers, then partly cloudy'. Same facts, NWS's own words, sentence case."""
    s = bs.house_style(short or "").strip()
    if not s:
        return ""
    parts = []
    for part in re.split(r"\s+then\s+", s, flags=re.I):
        p = part.strip().lower()
        p = re.sub(r"^slight chance (of )?", "a slight chance of ", p)
        p = re.sub(r"^chance (of )?", "a chance of ", p)
        p = re.sub(r"\bt-?storms\b", "thunderstorms", p)
        if not re.search(r"snow|sleet|freezing", p):
            p = p.replace("rain showers", "showers")      # NWS's "Rain Showers" (it says "Snow Showers" for snow)
        parts.append(p)
    return upper_first(", then ".join(parts))


def card_words(short):
    """A few words for the small day cards: the friendly forecast, or its first part if it's long."""
    f = friendly(short)
    if len(f) > 34 and ", then " in f:
        a, b = f.split(", then ", 1)
        f = upper_first(b) if re.search(r"rain|shower|snow|storm|thunder|drizzle|sleet|ice|freez", b, re.I) and not \
            re.search(r"rain|shower|snow|storm|thunder|drizzle|sleet|ice|freez", a, re.I) else a
    return f


def icon_for(short, daytime, pop=None):
    """Which drawn icon fits NWS's words (video_render.py draws them)."""
    s = (short or "").lower()
    if "thunder" in s or "t-storm" in s:
        return "storm"
    if re.search(r"snow|flurr|blizzard", s):
        return "snow" if not re.search(r"rain|sleet|freezing", s) else "mix"
    if re.search(r"sleet|freezing|ice", s):
        return "mix"
    if re.search(r"rain|shower|drizzle", s):
        if re.search(r"slight chance|chance", s) and not re.search(r"likely", s):
            return "sun-rain" if daytime else "moon-rain"
        return "rain"
    if re.search(r"fog|haze|smoke|mist", s):
        return "fog"
    if re.search(r"mostly cloudy|\bcloudy\b|overcast", s) and "partly cloudy" not in s:
        return "cloud"
    if "partly" in s:
        return "sun-cloud" if daytime else "moon-cloud"
    if re.search(r"mostly sunny|mostly clear", s):
        return "sun-small-cloud" if daytime else "moon-small-cloud"
    if re.search(r"windy|breezy|blustery", s):
        return "wind"
    return "sun" if daytime else "moon"


def first_number(text):
    m = re.findall(r"\d+", text or "")
    return max(int(x) for x in m) if m else None


def sun_times(day, lat=ns.LAT, lon=ns.LON):
    """Sunrise and sunset in La Porte, by NOAA's Solar Calculator method (within a minute; checked
    against Chicago's published times for June 21 and Dec. 21)."""
    import math

    def event(rising):
        jd0 = (datetime.datetime(day.year, day.month, day.day) - datetime.datetime(2000, 1, 1, 12)).total_seconds() / 86400 + 2451545.0
        minutes = 720.0
        for _ in range(3):
            T = (jd0 + minutes / 1440.0 - 2451545.0) / 36525.0
            L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360
            M = math.radians(357.52911 + T * (35999.05029 - 0.0001537 * T))
            e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
            C = math.sin(M) * (1.914602 - T * (0.004817 + 0.000014 * T)) + math.sin(2 * M) * (0.019993 - 0.000101 * T) + math.sin(3 * M) * 0.000289
            om = math.radians(125.04 - 1934.136 * T)
            lam = math.radians(L0 + C - 0.00569 - 0.00478 * math.sin(om))
            eps = math.radians(23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60 + 0.00256 * math.cos(om))
            dec = math.asin(math.sin(eps) * math.sin(lam))
            y = math.tan(eps / 2) ** 2
            L = math.radians(L0)
            eqt = 4 * math.degrees(y * math.sin(2 * L) - 2 * e * math.sin(M) + 4 * e * y * math.sin(M) * math.cos(2 * L)
                                   - 0.5 * y * y * math.sin(4 * L) - 1.25 * e * e * math.sin(2 * M))
            la = math.radians(lat)
            ha = math.degrees(math.acos(math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(dec)) - math.tan(la) * math.tan(dec)))
            minutes = 720 - 4 * lon - eqt + (-4 * ha if rising else 4 * ha)
        return (datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.timezone.utc)
                + datetime.timedelta(minutes=round(minutes))).astimezone(TZ)
    return event(True), event(False)


# ---------------------------------------------------------------------------------------------
# The weather
# ---------------------------------------------------------------------------------------------
def hourly_forecast(pt):
    url = (pt.get("forecast") or "").rstrip("/") + "/hourly"
    d = ns.get_json(url)["properties"]
    out = []
    for x in d.get("periods") or []:
        out.append({"start": x.get("startTime"), "end": x.get("endTime"), "temp": x.get("temperature"),
                    "pop": (x.get("probabilityOfPrecipitation") or {}).get("value") or 0,
                    "short": x.get("shortForecast") or "", "wind": x.get("windSpeed") or "",
                    "isDaytime": x.get("isDaytime")})
    return out


def snapshot_today(now):
    s = load_json(SNAPSHOT, {}) or {}
    try:
        if local(s["fetched"]).date() == now.date():
            return s
    except Exception:
        pass
    return {}


def gather(now):
    """Live from NWS. Raises if the forecast or the alerts don't come back."""
    pt = ns.point()
    fc = ns.forecast(pt)
    alerts = ns.county_alerts()             # raises when no alert request answered
    try:
        hours = hourly_forecast(pt)
    except Exception as e:
        print(f"No hour-by-hour forecast this time ({str(e)[:160]}).", file=sys.stderr)
        hours = []
    try:
        obs = ns.observation()
    except Exception:
        obs = None
    return {"source": "nws", "fetched": now.isoformat(), "forecast": fc, "hours": hours, "alerts": alerts,
            "observation": obs, "snapshot": snapshot_today(now), "scorecard": load_json(SCORECARD, {}) or {},
            "posts": bs.load_posts()}


def active_alerts(alerts, now):
    out = []
    for a in alerts or []:
        if not a or not a.get("event") or (a.get("messageType") or "").lower() == "cancel":
            continue
        end_s = a.get("ends") or a.get("expires")
        try:
            if end_s and dt(end_s) < now:
                continue
        except Exception:
            pass
        out.append(a)
    out.sort(key=rb.alert_rank)
    return out


def normals_for(day, normals):
    try:
        v = (normals or {}).get("days", {}).get(day.strftime("%m-%d"))
        return (float(v[0]), float(v[1])) if v and v[0] is not None else (None, None)
    except Exception:
        return None, None


def fetch_normals():
    """NOAA's 1991-2020 daily normal highs and lows at the nearest station with them (La Porte's own
    cooperative station when it has them). Saved on the video branch, so this runs once."""
    lat, lon = ns.LAT, ns.LON
    bbox = ",".join(f"{v:.3f}" for v in (lat + 0.35, lon - 0.45, lat - 0.35, lon + 0.45))
    found = ns.get_json(f"{NCEI}/search/v1/data?dataset=normals-daily-1991-2020&bbox={bbox}&limit=200",
                        accept="application/json")
    cands = []
    for x in (found or {}).get("results") or []:
        st = ((x.get("stations") or [{}])[0]) or {}
        types = {d.get("id") for d in st.get("dataTypes") or []}
        c = (x.get("location") or {}).get("coordinates") or []
        if st.get("id") and "DLY-TMAX-NORMAL" in types and len(c) == 2:
            km = 111.2 * ((c[1] - lat) ** 2 + ((c[0] - lon) * 0.747) ** 2) ** 0.5
            cands.append((km, st["id"], st.get("name")))
    cands.sort()
    for km, sid, name in cands[:4]:
        for extra in ("", "&startDate=2010-01-01&endDate=2010-12-31"):
            try:
                rows = ns.get_json(f"{NCEI}/data/v1?dataset=normals-daily-1991-2020&stations={sid}&format=json"
                                   f"&dataTypes=DLY-TMAX-NORMAL,DLY-TMIN-NORMAL{extra}", accept="application/json") or []
            except Exception:
                rows = []
            days = {}
            for r in rows:
                d = str(r.get("DATE") or "")[-5:]
                try:
                    hi, lo = float(str(r.get("DLY-TMAX-NORMAL")).strip()), float(str(r.get("DLY-TMIN-NORMAL")).strip())
                except Exception:
                    continue
                if re.fullmatch(r"\d\d-\d\d", d) and -60 < hi < 130 and -60 < lo < 130:
                    days[d] = [round(hi, 1), round(lo, 1)]
            if len(days) >= 360:
                return {"about": "NOAA NCEI 1991-2020 daily normals (high, low in F) for the Daily Video.",
                        "station": {"id": sid, "name": name, "km": round(km, 1)}, "days": days}
    raise RuntimeError("no station with daily normals answered")


# ---------------------------------------------------------------------------------------------
# What the video says
# ---------------------------------------------------------------------------------------------
def rain_window(hours, start, end):
    """(peak chance, words) for the hours of a period, from the NWS hour-by-hour forecast (Central)."""
    hs = [h for h in hours if h.get("start") and start <= local(h["start"]) < end]
    if not hs:
        return None, None
    peak = max(int(h.get("pop") or 0) for h in hs)
    if peak < 20:
        return peak, None
    thr = max(20, peak - 10)
    wet = [h for h in hs if int(h.get("pop") or 0) >= thr]
    one = datetime.timedelta(hours=1)
    first, last = local(wet[0]["start"]), local(wet[-1]["start"]) + one
    s0, e0 = local(hs[0]["start"]), local(hs[-1]["start"]) + one
    if first <= s0 + one and last >= e0 - one:
        return peak, None                           # the whole stretch: the chance says it
    if first > s0 + one and last >= e0 - one:
        return peak, f"after {bs.clock(first)}"
    if first <= s0 + one:
        return peak, f"until {bs.clock(last)}"
    return peak, f"from {bs.clock(first)} to {bs.clock(last)}"


def gust_of(p):
    m = re.search(r"gusts? as high as (\d+) mph", p.get("detailed") or "", re.I)
    return int(m.group(1)) if m else None


def frost_words(p):
    m = re.search(r"\b((?:patchy|areas of|widespread)\s+)?frost\b", f"{p.get('short') or ''} {p.get('detailed') or ''}", re.I)
    return upper_first(m.group(0).lower()) if m else None


def snow_words(p):
    m = re.search(r"(new )?snow accumulation of ([^.]*?)(?: possible)?\.", p.get("detailed") or "", re.I)
    return m.group(2).strip() if m else None


def spc_level(snap):
    try:
        day1 = next(d for d in snap.get("spc") or [] if d.get("day") == 1)
        risk = day1.get("riskAtLaPorte") or ""
    except Exception:
        return None, None
    for word, lvl in (("High", 5), ("Moderate", 4), ("Enhanced", 3), ("Slight", 2), ("Marginal", 1)):
        if word.lower() in risk.lower():
            return lvl, word
    return None, None


def periods_ahead(data, now):
    return [p for p in (data["forecast"].get("periods") or []) if dt(p["end"]) > now]


def when_word(t, now):
    """'today', 'tonight' (6 p.m. or later today), or the weekday."""
    w = bs.day_word(t, now)
    return "tonight" if w == "today" and local(t).hour >= 18 else w


def day_name(p, now):
    d = local(p["start"]).date()
    if d == now.date():
        return "today" if p.get("isDaytime") else "tonight"
    return WEEKDAYS[d.weekday()] + ("" if p.get("isDaytime") else " night")


def hooks(data, now, normals):
    """Every opening line that's true right now, with how much it matters. The highest wins."""
    ps = periods_ahead(data, now)
    first = ps[0]
    day = next((p for p in ps[:2] if p.get("isDaytime")), None)            # today (if it's still day)
    night = next((p for p in ps[:3] if not p.get("isDaytime")), None)     # tonight
    days_after = [p for p in ps if p.get("isDaytime") and local(p["start"]).date() > now.date()]
    tomorrow = days_after[0] if days_after else None
    out = []

    def add(score, kind, big, small, say, icon, tone, label=None, when=None):
        out.append({"score": score, "kind": kind, "big": big, "small": small, "say": say, "icon": icon,
                    "tone": tone, "label": label, "when": when})

    # 1. An official alert for La Porte County, in NWS's words.
    for a in active_alerts(data.get("alerts"), now):
        event = a["event"]
        kind = 0 if "Warning" in event else 1 if "Watch" in event else 2 if "Advisory" in event else 3
        span = ""
        try:
            onset = dt(a["onset"]) if a.get("onset") else None
            end_s = a.get("ends") or a.get("expires")
            if onset and onset > now + datetime.timedelta(minutes=30):
                span += f" from {bs.clock(onset)} {when_word(onset, now)}"
            if end_s:
                span += f" until {bs.clock(dt(end_s))} {when_word(dt(end_s), now)}"
        except Exception:
            pass
        where = rb.where_words(a.get("area"))
        article = "an" if event[:1].upper() in "AEIOU" else "a"
        add(130 - 10 * kind, "alert", event, f"for {where}{span}",
            f"The National Weather Service has {article} {event} for {where}{span}.",
            "alert", "alert", label="NATIONAL WEATHER SERVICE", when="now")
        break                                                             # the top one leads; the rest are listed

    # 2. Freeze or frost tonight (NWS's own words for frost), in the months when it's news: the
    #    growing season's ends. In winter a freezing night is normal; only a very cold one leads.
    if night and night.get("temperatureF") is not None:
        lo = night["temperatureF"]
        fw = frost_words(night)
        tn = day_name(night, now)
        edge = now.month in (4, 5, 9, 10, 11)
        if lo <= 32 and edge:
            add(92, "freeze", deg(lo), f"Below freezing {tn}",
                f"Below freezing {tn} in La Porte, with a low around {lo}°.", icon_for(night["short"], False), "cold", when=tn)
        elif fw and edge:
            add(90, "frost", f"{fw}", f"possible {tn} · low {lo}°",
                f"{fw} is possible {tn}, with a low around {lo}°.", "frost", "cold", when=tn)
        elif lo <= 0:
            add(84, "cold", deg(lo), f"Low {tn}", f"A bitter cold night: a low around {lo}°.", icon_for(night["short"], False),
                "cold", when=tn)

    # 3. Snow today or tonight.
    for p in [x for x in (day, night) if x]:
        if re.search(r"snow|flurr|blizzard", p.get("short") or "", re.I) and (p.get("rainChancePercent") or 0) >= 30:
            amt = snow_words(p)
            when = day_name(p, now)
            if amt:
                add(93, "snow", amt, f"of snow {when}", f"Snow {when}: {amt} possible, says the Weather Service.", "snow", "cold", when=when)
            else:
                add(86, "snow", "Snow", f"in the forecast {when}", f"{friendly(p['short'])} {when}.", "snow", "cold", when=when)
            break

    # 4. NOAA's Storm Prediction Center risk for today.
    lvl, word = spc_level(data.get("snapshot") or {})
    if lvl and lvl >= 2:
        add(88, "spc", f"Level {lvl} of 5", f"{word} risk of severe storms today",
            f"NOAA's Storm Prediction Center has La Porte at level {lvl} of 5 for severe storms today. "
            f"Keep a way to get warnings handy.", "storm", "storm", label="STORM PREDICTION CENTER", when="today")

    # 5. Thunderstorms in the forecast today or tonight.
    hours = data.get("hours") or []
    for p in [x for x in (day, night) if x]:
        if re.search(r"thunder|t-storm", p.get("short") or "", re.I):
            peak, window = rain_window(hours, local(p["start"]), local(p["end"]))
            chance = bs.nws_chance(p.get("rainChancePercent"))
            when = window or day_name(p, now)
            add(74 if lvl == 1 else 70, "storms", "Storms", f"possible {when}" + (f" · {chance}%" if chance else ""),
                f"Thunderstorms are possible {when}" + (f", a {chance}% chance." if chance else "."), "storm", "storm", when=day_name(p, now))
            break

    # 6. Heat and wind.
    if day and day.get("temperatureF") is not None and day["temperatureF"] >= 90:
        hi = day["temperatureF"]
        add(80 if hi >= 95 else 76, "heat", deg(hi), f"High {day_name(day, now)}",
            f"A hot one {day_name(day, now)}: a high near {hi}°. Drink water and take breaks in the shade.", "sun", "warm", when=day_name(day, now))
    for p in [x for x in (day, night) if x]:
        g = gust_of(p)
        if g and g >= 35:
            add(78 if g < 45 else 84, "wind", f"Gusts to {g}", f"mph {day_name(p, now)}",
                f"Gusts could reach {g} mph {day_name(p, now)}, says the Weather Service.", "wind", "storm", when=day_name(p, now))
            break

    # 7. Rain likely today.
    if day:
        chance = bs.nws_chance(day.get("rainChancePercent"))
        if chance and chance >= 50 and re.search(r"rain|shower|drizzle", day.get("short") or "", re.I):
            peak, window = rain_window(hours, local(day["start"]), local(day["end"]))
            add(66 if chance >= 60 else 60, "rain", f"{chance}%", "chance of rain today" + (f" · {window}" if window else ""),
                f"Rain likely today: a {chance}% chance" + (f", mostly {window}." if window else "."), "rain", "rain", when="today")

    # 8. A big change from yesterday at the La Porte airport.
    sc = (data.get("scorecard") or {}).get("latest") or {}
    y_high = (sc.get("observed") or {}).get("high")
    if day and day.get("temperatureF") is not None and y_high is not None and sc.get("date") == (now.date() - datetime.timedelta(days=1)).isoformat():
        diff = day["temperatureF"] - int(y_high)
        if abs(diff) >= 12:
            word = "warmer" if diff > 0 else "cooler"
            add(56 + min(abs(diff), 25) // 3, "change", f"{abs(diff)}° {word}", "than yesterday",
                f"About {abs(diff)}° {word} than yesterday, with a high near {day['temperatureF']}°.",
                icon_for(day["short"], True), "warm" if diff > 0 else "cold", when="today")

    # 9. Unusually warm or cool for the date (NOAA 1991-2020 normals), today or tomorrow.
    for p, base in ((day, 58), (tomorrow, 50)):
        if not p or p.get("temperatureF") is None:
            continue
        d = local(p["start"]).date()
        nhi, _ = normals_for(d, normals)
        if nhi is None:
            continue
        diff = int(round(p["temperatureF"] - nhi))
        if abs(diff) >= 10:
            word = "above" if diff > 0 else "below"
            when = day_name(p, now)
            date_words = f"{AP_MONTHS[d.month - 1]} {d.day}"
            add(base + min(abs(diff), 24) // 3, "normal", deg(p["temperatureF"]), f"{upper_first(when)}. {abs(diff)}° {word} normal.",
                f"{upper_first(when)}: {p['temperatureF']}°, about {abs(diff)}° {word} normal for {date_words}.",
                icon_for(p["short"], True), "warm" if diff > 0 else "cold", when=when)

    # 10. The weekend's best day (Thursday and Friday videos).
    if now.weekday() in (3, 4):
        wk = [p for p in days_after if local(p["start"]).weekday() in (5, 6)][:2]
        good = [p for p in wk if (bs.nws_chance(p.get("rainChancePercent")) or 0) < 20
                and re.search(r"sunny|clear", p.get("short") or "", re.I) and not re.search(r"rain|shower|snow|storm", p.get("short") or "", re.I)]
        if len(wk) == 2 and len(good) == 1:
            p = good[0]
            name = WEEKDAYS[local(p["start"]).weekday()]
            add(46, "weekend", name, "is the pick of the weekend",
                f"{name} is the pick of the weekend: {lower_first(friendly(p['short']))}, with a high near {p['temperatureF']}°.",
                icon_for(p["short"], True), "warm", when=name)

    # 11. A nice day.
    if day and day.get("temperatureF") is not None:
        hi = day["temperatureF"]
        chance = bs.nws_chance(day.get("rainChancePercent"))
        if not chance and 62 <= hi <= 84 and re.search(r"sunny|clear", day.get("short") or "", re.I) \
                and not re.search(r"rain|shower|snow|storm|fog", day.get("short") or "", re.I):
            add(40, "nice", deg(hi), f"and {lower_first(friendly(day['short']))} today",
                f"{friendly(day['short'])} and {hi}° today in La Porte.", icon_for(day["short"], True), "warm", when="today")

    # 12. Otherwise, just the forecast.
    p = day or first
    t = p.get("temperatureF")
    add(10, "plain", deg(t), f"{friendly(p['short'])}",
        f"{upper_first(day_name(p, now))} in La Porte: {lower_first(friendly(p['short']))}, "
        f"{'high near' if p.get('isDaytime') else 'low around'} {t}°.", icon_for(p["short"], p.get("isDaytime")), "plain",
        when=day_name(p, now))
    out.sort(key=lambda h: -h["score"])
    return out


PRECIP = r"rain|shower|drizzle|thunder|storm|snow|sleet|flurr|ice"


def with_chance(text, chance, window):
    """'A chance of rain showers, then partly cloudy' + 30% + 'after 10 a.m.' ->
    'A 30% chance of rain showers after 10 a.m., then partly cloudy' (NWS's words, NWS's numbers)."""
    m = re.search(r"\ba (?:slight )?chance of ", text, re.I)
    if m:
        out = text[:m.start()] + f"a {chance}% chance of " + text[m.end():]
        if window:
            cut = out.find(", then", m.start())
            out = out[:cut] + f" {window}" + out[cut:] if cut >= 0 else out + f" {window}"
        return upper_first(out)
    cut = text.find(", then")
    head, tail = (text[:cut], text[cut:]) if cut >= 0 else (text, "")
    return upper_first(f"{head}, a {chance}% chance" + (f" {window}" if window else "") + tail)


def period_scene(p, now, hours, hook, with_hours):
    name = day_name(p, now)
    title = name.upper()
    temp = p.get("temperatureF")
    chance = bs.nws_chance(p.get("rainChancePercent"))
    peak, window = rain_window(hours, local(p["start"]), local(p["end"]))
    text = friendly(p.get("short"))
    sentence = text
    rain = None
    if chance and re.search(PRECIP, p.get("short") or "", re.I):
        what = bs.precip_word(p.get("short"))
        rain = {"pct": chance, "what": what, "window": window}
        sentence = with_chance(text, chance, window)
    spoken = sentence if not (rain and hook["kind"] in ("rain", "storms") and name == "today") else text
    say = bs.end_sentence(f"{upper_first(name)}: {lower_first(spoken)}") + f" {'High' if p.get('isDaytime') else 'Low'} {temp}."
    note = None
    g = gust_of(p)
    wind_mph = first_number(p.get("wind"))
    if g and g >= 25:
        note = f"Gusts to {g} mph"
        if hook["kind"] != "wind":
            say += f" Gusts to {g} mph."
    elif wind_mph and wind_mph >= 15:
        note = f"Wind {p.get('wind')}"
    fw = frost_words(p)
    if fw and hook["kind"] not in ("frost", "freeze"):
        note = f"{fw} possible"
        say += f" {fw} is possible."
    strip = []
    if with_hours:
        start = max(local(p["start"]), now.replace(minute=0, second=0, microsecond=0))
        stop = local(p["end"])
        for h in hours:
            t = local(h["start"])
            if start <= t < stop and (t.hour - start.hour) % 2 == 0 and len(strip) < 8:
                strip.append({"label": f"{t.hour % 12 or 12} {'AM' if t.hour < 12 else 'PM'}", "temp": h.get("temp"),
                              "pop": int(h.get("pop") or 0)})
        if len(strip) < 5:
            strip = []
    sun = None
    if not p.get("isDaytime"):
        d0 = local(p["start"]).date()
        sun = {"set": bs.clock(sun_times(d0)[1]), "rise": bs.clock(sun_times(d0 + datetime.timedelta(days=1))[0])}
    return {"id": "today" if name == "today" else "tonight" if name == "tonight" else re.sub(r"\W+", "-", name.lower()),
            "sun": sun,
            "kind": "period", "title": title, "date": ap_day(local(p["start"]).date()),
            "temp": temp, "tempLabel": "HIGH" if p.get("isDaytime") else "LOW",
            "icon": icon_for(p.get("short"), p.get("isDaytime"), chance), "text": text, "sentence": sentence,
            "rain": rain, "note": note, "hours": strip, "say": say}


def days_scene(data, now, start_after, hook):
    ps = periods_ahead(data, now)
    days = []
    for i, p in enumerate(ps):
        if not p.get("isDaytime") or local(p["start"]) < start_after:
            continue
        lo = next((q.get("temperatureF") for q in ps[i + 1:i + 2] if not q.get("isDaytime")), None)
        d = local(p["start"]).date()
        days.append({"name": SHORT_DAYS[d.weekday()], "day": WEEKDAYS[d.weekday()], "hi": p.get("temperatureF"), "lo": lo,
                     "pop": bs.nws_chance(p.get("rainChancePercent")), "icon": icon_for(p.get("short"), True),
                     "text": card_words(p.get("short")), "short": p.get("short"),
                     "star": hook.get("when") in (WEEKDAYS[d.weekday()], WEEKDAYS[d.weekday()] + " night")})
        if len(days) == 3:
            break
    if len(days) < 2:
        return None
    # The voice reads two days, skipping the one the opening line was about.
    told = [x for x in days if not x["star"]][:2]
    say = " ".join(bs.end_sentence(f"{x['day']}: {lower_first(friendly(x['short']))}, {x['hi']}") for x in told)
    return {"id": "days", "kind": "days", "title": f"NEXT {len(days)} DAYS", "days": days, "say": say}


def until_words(a, now):
    end_s = a.get("ends") or a.get("expires")
    return f" until {bs.clock(dt(end_s))} {when_word(dt(end_s), now)}" if end_s else ""


def caption(plan_scenes, hook, data, now, alerts):
    lines = [f"La Porte weather for {ap_day(now.date())}, from the National Weather Service:"]
    if alerts:
        lines.append(bs.end_sentence("Official alerts for La Porte County: " + "; ".join(
            f"{a['event']}{until_words(a, now)}" for a in alerts)))
    for s in plan_scenes:
        if s["kind"] == "period":
            bit = bs.end_sentence(f"{upper_first(s['title'].lower())}: {s['sentence']}") + f" {upper_first(s['tempLabel'].lower())} {s['temp']}."
            if s.get("note"):
                bit += f" {bs.end_sentence(s['note'])}"
            lines.append(bit)
        elif s["kind"] == "days":
            lines.append(" ".join(f"{x['day']}: {x['text']}, high {x['hi']}." for x in s["days"]))
    post = bs.todays_post(data.get("posts") or {}, now.date().isoformat())
    if post and not post.get("auto") and post.get("title"):
        lines.append(f"Today's Daily Scoop: {post['title']}")
    lines.append("Free forecast every morning: laporteweathernow.com")
    lines.append("No hype. Just the forecast.")
    lines.append(HASHTAGS)
    return "\n".join(lines)


def build_plan(data, now, normals, radar_ok=None):
    ps = periods_ahead(data, now)
    if len(ps) < 4:
        raise RuntimeError("the NWS forecast came back without enough periods")
    alerts = active_alerts(data.get("alerts"), now)
    short_fused = [a for a in alerts if any(k in a["event"] for k in SHORT_FUSED)]
    options = hooks(data, now, normals)
    hook = options[0]
    hours = data.get("hours") or []
    scenes = [{"id": "hook", "kind": "hook", "label": hook.get("label") or f"LA PORTE · {ap_day(now.date()).upper()}",
               "big": hook["big"], "small": hook["small"], "icon": hook["icon"], "tone": hook["tone"],
               "hookKind": hook["kind"], "say": hook["say"]}]
    if hook["kind"] == "alert" and len(alerts) > 1:
        scenes[0]["more"] = [a["event"] for a in alerts[1:4]]
    first, second = ps[0], ps[1]
    scenes.append(period_scene(first, now, hours, hook, with_hours=True))
    scenes.append(period_scene(second, now, hours, hook, with_hours=False))
    if radar_ok:
        scenes.append({"id": "radar", "kind": "radar", "title": "RADAR", "say": "Here's the radar right now."})
    nxt = days_scene(data, now, local(second["end"]), hook)
    if nxt:
        scenes.append(nxt)
    scenes.append({"id": "end", "kind": "end", "say": "Free forecast every morning at laporteweathernow.com."})
    for s in scenes:
        s["spoken"] = rb.for_ear(s["say"])
    obs = data.get("observation") or {}
    return {
        "about": "The Daily Video for La Porte Weather Now (scripts/daily_video.py): official NWS weather, read aloud.",
        "date": now.date().isoformat(),
        "planned": now.isoformat(),
        "source": data.get("source"),
        "forecastUpdated": (data["forecast"] or {}).get("updated"),
        "observationTime": obs.get("time"),
        "alerts": [{"event": a["event"], "ends": a.get("ends") or a.get("expires"), "id": a.get("id")} for a in alerts],
        "shortFused": [a["event"] for a in short_fused],
        "hook": {k: hook[k] for k in ("kind", "score", "big", "small", "say", "when")},
        "hookOptions": [{"kind": h["kind"], "score": h["score"], "say": h["say"]} for h in options[:6]],
        "scenes": scenes,
        "caption": caption(scenes, hook, data, now, alerts),
        "words": sum(len(s["spoken"].split()) for s in scenes),
    }


# ---------------------------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------------------------
def parse_args(argv):
    args = {"last": None, "mode": "auto", "now": None, "test": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--") and a[2:] in args and i + 1 < len(argv):
            args[a[2:]] = argv[i + 1]
            i += 2
            continue
        i += 1
    return args


def cmd_plan(outdir, argv):
    args = parse_args(argv)
    os.makedirs(outdir, exist_ok=True)
    now = local(dt(args["now"])) if args["now"] else bs.now_local()
    mode = (args["mode"] or "auto").strip().lower()
    last_dir = args["last"]
    last = load_json(os.path.join(last_dir, "video.json"), {}) if last_dir else {}
    set_output("build", "false")
    hm = now.strftime("%H:%M")
    if mode == "auto":
        if not (AUTO_WINDOW[0] <= hm <= AUTO_WINDOW[1]):
            print(f"It's {bs.clock(now)}; the day's video is made between 5:45 and 9:30 AM. Nothing to do.")
            return 0
        if last.get("date") == now.date().isoformat():
            print(f"Today's video was already made at {last.get('made')}; nothing to do.")
            return 0
    # Normals: kept on the video branch; looked up once.
    normals = load_json(os.path.join(last_dir, "normals.json")) if last_dir else None
    if args["test"]:
        data = load_json(args["test"])
        normals = data.get("normals", normals)
    else:
        if not normals:
            try:
                normals = fetch_normals()
                print(f"Normals: {normals['station']['name']} ({normals['station']['id']}, {normals['station']['km']} km).")
            except Exception as e:
                print(f"No normals this time ({str(e)[:160]}); the unusual-temperature line is skipped.", file=sys.stderr)
                normals = None
        try:
            data = gather(now)
        except Exception as e:
            print(f"NWS didn't give both the forecast and the alerts ({str(e)[:200]}); no video this time.")
            return 0
    if normals:
        save_json(os.path.join(outdir, "normals.json"), normals)
    alerts = active_alerts(data.get("alerts"), now)
    short_fused = [a["event"] for a in alerts if any(k in a["event"] for k in SHORT_FUSED)]
    if short_fused and mode != "preview":
        print(f"{', '.join(short_fused)} in effect for La Porte County: no video now (it would be out of date "
              f"within minutes). The Timer tries again at 6:45.")
        return 0
    # The radar: only when there's rain or snow on it near La Porte.
    radar_ok = False
    if not args["test"]:
        try:
            import video_render
            radar_ok = video_render.fetch_radar(outdir, last_dir, force=os.environ.get("VIDEO_RADAR") == "always" and mode == "preview")
        except Exception as e:
            print(f"No radar this time ({str(e)[:200]}).", file=sys.stderr)
    plan = build_plan(data, now, normals, radar_ok=radar_ok)
    plan["mode"] = mode
    if normals:
        plan["normalsStation"] = normals.get("station")
    save_json(os.path.join(outdir, "plan.json"), plan)
    print(f"Hook ({plan['hook']['kind']}): {plan['hook']['say']}")
    for s in plan["scenes"]:
        print(f"  [{s['id']}] {s['say']}")
    print(f"{plan['words']} words. Caption:\n{plan['caption']}")
    set_output("build", "true")
    return 0


def speak_all(plan, outdir, speak, rate):
    import numpy as np
    import soundfile as sf
    vdir = os.path.join(outdir, "voice")
    os.makedirs(vdir, exist_ok=True)
    for s in plan["scenes"]:
        audio = speak(s["spoken"])
        audio = np.asarray(audio, dtype=np.float32)
        path = os.path.join(vdir, f"{s['id']}.wav")
        sf.write(path, audio, rate)
        s["voiceFile"] = os.path.relpath(path, outdir)
        s["voiceSeconds"] = round(len(audio) / rate, 2)


def timeline(plan):
    t = 0.0
    for s in plan["scenes"]:
        v = s.get("voiceSeconds") or 0.0
        dur = max(CUTOFFS.get(s["kind"], 3.0), LEAD + v + TAIL)
        s["start"], s["duration"], s["voiceAt"] = round(t, 2), round(dur, 2), round(t + (0.04 if s["kind"] == "hook" else LEAD), 2)
        t += dur
    plan["seconds"] = round(t, 2)


def cmd_voice(outdir):
    import numpy as np
    from kokoro import KPipeline
    plan = load_json(os.path.join(outdir, "plan.json"))
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    speed = float(config().get("voiceSpeed", 1.1))

    def speak(text):
        for word, sounds in rb.PRONOUNCE.items():
            text = text.replace(word, f"[{word}](/{sounds}/)")
        chunks = []
        for result in pipe(text, voice=rb.VOICE, speed=speed, split_pattern=r"\n+"):
            audio = result.audio if hasattr(result, "audio") else result[2]
            if audio is not None:
                chunks.append(audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio))
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)

    speak_all(plan, outdir, speak, rb.RATE)
    timeline(plan)
    plan["voice"] = f"Kokoro-82M {rb.VOICE}, speed {speed}"
    save_json(os.path.join(outdir, "plan.json"), plan)
    print(f"Voice recorded: {plan['seconds']} seconds in all.")
    return 0


def cmd_silent(outdir):
    """No voice (testing): each scene lasts as long as its words would take to read."""
    import numpy as np
    plan = load_json(os.path.join(outdir, "plan.json"))
    speak_all(plan, outdir, lambda text: np.zeros(int(rb.RATE * len(text.split()) / 2.75), dtype=np.float32), rb.RATE)
    timeline(plan)
    plan["voice"] = "silent (test)"
    save_json(os.path.join(outdir, "plan.json"), plan)
    print(f"Silent timing: {plan['seconds']} seconds in all.")
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "plan":
        return cmd_plan(argv[2], argv[3:])
    if len(argv) >= 3 and argv[1] == "voice":
        return cmd_voice(argv[2])
    if len(argv) >= 3 and argv[1] == "silent":
        return cmd_silent(argv[2])
    if len(argv) >= 3 and argv[1] == "render":
        import video_render
        return video_render.render(argv[2])
    if len(argv) >= 3 and argv[1] == "post":
        import video_post
        return video_post.post(argv[2], dry_run="--dry-run" in argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
