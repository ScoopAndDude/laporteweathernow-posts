#!/usr/bin/env python3
"""Weather radio for laporteweathernow.com: the La Porte County broadcast, written for the ear
and recorded in a natural human voice.

  python3 scripts/radio_broadcast.py script OUT.json [--force] [--snapshot]
      Gather the newest official weather and write the broadcast to OUT.json: segments (alerts,
      right now, forecast, Daily Scoop) with the words shown on the page and the words the voice
      reads. Sets the GitHub output changed=true|false: false when the broadcast on the "radio"
      branch already says the same thing (only the clock moved), unless --force.
      --snapshot uses nws-snapshot.json instead of asking NWS (for trying it out).
  python3 scripts/radio_broadcast.py record SCRIPT.json OUTDIR
      Record it with Kokoro-82M (open-source voice, Apache 2.0, voice "af_heart") into
      OUTDIR/laporte-<hash>.mp3 and OUTDIR/radio.json (what the page's player reads).
  python3 scripts/radio_broadcast.py check OUTDIR
      Transcribe the recording with faster-whisper and compare it with the script, to check that
      every word comes out clearly.
  python3 scripts/radio_broadcast.py say "text"
      Print how a line will be read (the words the voice gets).

Rules:
- Official information only: NWS alerts for La Porte County (their own wording, read in full),
  the La Porte airport reading, the NWS forecast (clock times already moved to Central time),
  and today's Daily Scoop (title and summary, plus any correction). Nothing is made up.
- If NWS can't give both the forecast and the alerts, nothing new is recorded; the page shows how
  old the last recording is and reads any newer warning itself.
- Written the way a person talks on the radio: times as "four in the afternoon", "miles an hour",
  numbers in words, La Porte said the local way ("La Port").
"""
import datetime
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backup_scoop as bs  # noqa: E402
import nws_snapshot as ns  # noqa: E402

TZ = bs.TZ
RADIO_JSON_URL = "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/radio/radio.json"
VOICE = "af_heart"
SPEED = 0.97
RATE = 24000
PAUSE_PARAGRAPH = 0.55
PAUSE_SEGMENT = 1.0
OBS_MAX_HOURS = 2
# How the voice says local names (Kokoro/misaki sound symbols): La Porte is "luh-PORT".
PRONOUNCE = {"La Port": "ləpˈɔɹt"}
WEEKDAYS = bs.WEEKDAYS
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]

# ---------------------------------------------------------------------------------------------
# Numbers and times in words
# ---------------------------------------------------------------------------------------------
ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
        "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
ORDINAL_WORDS = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth",
                 "nine": "ninth", "twelve": "twelfth"}


def words(n):
    n = int(n)
    if n < 0:
        return "minus " + words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return ONES[n // 100] + " hundred" + (" " + words(n % 100) if n % 100 else "")
    if n < 1_000_000:
        return words(n // 1000) + " thousand" + (" " + words(n % 1000) if n % 1000 else "")
    if n < 1_000_000_000:
        return words(n // 1_000_000) + " million" + (" " + words(n % 1_000_000) if n % 1_000_000 else "")
    return str(n)


def ordinal(n):
    w = words(n)
    head, sep, last = re.match(r"^(.*?)([ -]?)([a-z]+)$", w).groups()
    if last in ORDINAL_WORDS:
        last = ORDINAL_WORDS[last]
    elif last.endswith("y"):
        last = last[:-1] + "ieth"
    else:
        last += "th"
    return head + sep + last


def year_words(y):
    y = int(y)
    if 2000 <= y <= 2009:
        return "two thousand" + (" " + words(y % 100) if y % 100 else "")
    hi, lo = divmod(y, 100)
    return words(hi) + " " + ("hundred" if lo == 0 else ("oh " + words(lo) if lo < 10 else words(lo)))


def part_of_day(h24):
    if h24 < 12:
        return "morning"
    if h24 < 17:
        return "afternoon"
    if h24 < 21:
        return "evening"
    return "night"


def clock_words(hour, minute, ampm):
    """(4, 0, 'pm') -> 'four'; (7, 5, 'am') -> 'seven oh five'. Noon and midnight by name."""
    h24 = hour % 12 + (12 if ampm == "pm" else 0)
    if minute == 0 and h24 == 12:
        return "noon", h24
    if minute == 0 and h24 == 0:
        return "midnight", h24
    base = words(hour)
    if minute:
        base += (" oh " + words(minute)) if minute < 10 else (" " + words(minute))
    return base, h24


DAY_AFTER = r"(?P<after>\s+(?:this (?:morning|afternoon|evening)|tonight|today|tomorrow(?: (?:morning|afternoon|evening|night))?|" \
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?: (?:morning|afternoon|evening|night))?))?"
TIME_RE = re.compile(r"\b(?P<h>1[0-2]|0?[1-9])(?::(?P<m>[0-5]\d))?\s?(?P<ap>a\.m\.|p\.m\.|am|pm|AM|PM|A\.M\.|P\.M\.)"
                     r"(?:\s+(?P<tz>CDT|CST|EDT|EST|CT|ET)\b)?" + DAY_AFTER + r"(?![\w])")
WARN_TIME = re.compile(r"\b(\d{1,2})(\d{2})\s(AM|PM)\b")       # NWS warnings write 312 PM
WORD_TIME = re.compile(r"\b(noon|midnight)\s+(CDT|CST|EDT|EST)\b", re.I)


def say_time(m):
    hour, minute = int(m.group("h")), int(m.group("m") or 0)
    ampm = "am" if m.group("ap").lower().startswith("a") else "pm"
    base, h24 = clock_words(hour, minute, ampm)
    eastern = " eastern time" if (m.group("tz") or "").upper().startswith("E") else ""
    after = m.group("after") or ""
    if base in ("noon", "midnight"):
        return base + eastern + after
    day = re.match(r"\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|tomorrow)(?: (morning|afternoon|evening|night))?$", after)
    if after.strip() == "today":                           # "four this afternoon", "ten tonight"
        part = part_of_day(h24)
        return f"{base}{eastern} " + ("tonight" if part == "night" else "this " + part)
    if after.strip().startswith(("this", "tonight")):
        return base + eastern + after                      # "seven this evening"
    if day:
        return f"{base}{eastern} {day.group(1)} {day.group(2) or part_of_day(h24)}"   # "ten Friday morning"
    part = {"morning": "in the morning", "afternoon": "in the afternoon", "evening": "in the evening",
            "night": "at night"}[part_of_day(h24)]
    return f"{base} {part}{eastern}"


# ---------------------------------------------------------------------------------------------
# Written text -> spoken text
# ---------------------------------------------------------------------------------------------
SAY_AS = [
    (r"\bLa ?Porte\b", "La Port"),
    (r"\bLAPORTE\b|\bLA PORTE\b", "La Port"),
    (r"\bKPPO\b", "the La Port airport"),
    (r"\bthe NWS\b|\bNWS\b", "the Weather Service"),
    (r"\bthe Weather Service (Chicago|Northern Indiana|Grand Rapids)\b", r"the Weather Service in \1"),
    (r"\bSPC\b", "the Storm Prediction Center"),
    (r"\bWPC\b", "the Weather Prediction Center"),
    (r"\bthe the\b", "the"),
    (r"\bI-(\d+)\b", r"Interstate \1"),
    (r"\bUS[- ](\d+)\b", r"U.S. \1"),
    (r"\bSR[- ](\d+)\b", r"State Road \1"),
    (r"\bSt\.\s(?=[A-Z])", "Saint "),
    (r"\bMt\.\s(?=[A-Z])", "Mount "),
    (r"\be\.g\.", "for example"),
    (r"\bi\.e\.", "that is"),
    (r"\bapprox\.", "about"),
    (r"\bvs\.", "versus"),
    (r"\blaporteweathernow\.com\b", "La Port Weather Now dot com"),
    (r"\bweather\.gov(?:/\w+)*", "weather dot gov"),
    (r"\bhttps?://\S+", ""),
    (r"&", " and "),
]
HEADERS = [("PRECAUTIONARY/PREPAREDNESS ACTIONS", ""), ("ADDITIONAL DETAILS", "More details:"),
           ("HAZARD", "Hazard:"), ("SOURCE", "Source:"), ("IMPACTS", "Impacts:"), ("IMPACT", "Impact:"),
           ("WHAT", "What:"), ("WHERE", "Where:"), ("WHEN", "When:")]
MONTH_SAY = {"Jan.": "January", "Feb.": "February", "Aug.": "August", "Sept.": "September", "Oct.": "October",
             "Nov.": "November", "Dec.": "December", "January": "January", "February": "February", "March": "March",
             "April": "April", "May": "May", "June": "June", "July": "July", "August": "August",
             "September": "September", "October": "October", "November": "November", "December": "December"}
MONTH_RE = "|".join(re.escape(k) for k in sorted(MONTH_SAY, key=len, reverse=True))
FRACTIONS = {"½": "a half", "¼": "a quarter", "¾": "three quarters", "1/2": "a half", "1/4": "a quarter",
             "3/4": "three quarters", "1/3": "a third", "2/3": "two thirds"}


def clean_nws(text):
    """NWS product text: drop the machine lines and turn the section markers into speech."""
    t = text or ""
    t = re.split(r"\n\s*&&", t)[0]
    t = re.sub(r"(?m)^\s*(LAT\.\.\.LON|TIME\.\.\.MOT\.\.\.LOC|MAX HAIL SIZE|MAX WIND GUST|TORNADO\.\.\.|HAIL\.\.\.|WIND\.\.\.)[^\n]*$", "", t)
    for head, spoken in HEADERS:
        t = re.sub(r"(?m)(^|\s)\*?\s*" + re.escape(head) + r"\.\.\.", r"\1" + ((spoken + " ") if spoken else ""), t)
    t = re.sub(r"(?m)^\s*\*\s*", "", t)
    t = t.replace("$$", " ")
    return t


def sentence_case_if_shouting(t):
    letters = [c for c in t if c.isalpha()]
    if len(letters) > 20 and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        t = t.lower()
        t = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)
        t = re.sub(r"\bla porte\b", "La Porte", t)
    return t


def for_ear(text):
    t = clean_nws(text)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace("...", ", ").replace("…", ", ")
    t = WARN_TIME.sub(lambda m: f"{int(m.group(1))}:{m.group(2)} {m.group(3)}", t)
    t = WORD_TIME.sub(lambda m: m.group(1) + (" eastern time" if m.group(2).upper().startswith("E") else ""), t)
    t = TIME_RE.sub(say_time, t)
    t = re.sub(r"\b(CDT|CST)\b", "", t)
    t = re.sub(r"\b(EDT|EST)\b", "eastern time", t)
    t = sentence_case_if_shouting(t)          # after the times, which are matched in capitals
    for pat, rep in SAY_AS:
        t = re.sub(pat, rep, t)
    # Units and symbols
    t = re.sub(r"\bmph\b", "miles an hour", t)
    t = re.sub(r"\bkts?\b", "knots", t)
    t = re.sub(r"(\d)\s?ft\b", r"\1 feet", t)
    t = re.sub(r"(\d)\s?in\.(?=\s|$)", r"\1 inches", t)
    for frac, spoken in FRACTIONS.items():
        t = re.sub(r"(\d)" + re.escape(frac), lambda m: words(m.group(1)) + " and " + spoken, t)
        t = t.replace(frac, spoken)
    t = re.sub(r"(around|near|of|to|as low as|as high as|between|and|about) -(\d+)\b",
               lambda m: f"{m.group(1)} {words(m.group(2))} below zero", t)
    t = re.sub(r"(-?\d+)\s?°(?:F\b)?", lambda m: (words(m.group(1)[1:]) + " below zero") if m.group(1).startswith("-")
               else words(m.group(1)) + " degrees", t)
    t = re.sub(r"(\d+)\s?%", lambda m: words(m.group(1)) + " percent", t)
    t = re.sub(r"(\d+)\s?(?:-|–|to)\s?(\d+)(?=\s|$|[,.;])", r"\1 to \2", t)
    t = re.sub(r"\b(\d+)(st|nd|rd|th)\b", lambda m: ordinal(m.group(1)), t)
    t = re.sub(r"\b(" + MONTH_RE + r")\s(\d{1,2})\b(?![:\d])",
               lambda m: MONTH_SAY[m.group(1)] + " " + ordinal(m.group(2)), t)
    t = re.sub(r"\b(19\d\d|20\d\d)\b", lambda m: year_words(m.group(1)), t)
    t = re.sub(r"\$(\d+)", lambda m: words(m.group(1)) + " dollars", t)
    t = re.sub(r"\b(\d{1,3}(?:,\d{3})+)\b", lambda m: words(m.group(1).replace(",", "")), t)
    t = re.sub(r"\b(\d+)\.(\d+)\b", lambda m: words(m.group(1)) + " point " + " ".join(ONES[int(c)] for c in m.group(2)), t)
    t = re.sub(r"\b\d+\b", lambda m: words(m.group(0)), t)
    # Punctuation the voice reads better as pauses
    t = re.sub(r"\s*[·•|]\s*", ", ", t)
    t = re.sub(r"\s*[—–]\s*", ", ", t)
    t = re.sub(r"[()\[\]]", ", ", t)
    t = re.sub(r"(?<=[A-Za-z])/(?=[A-Za-z])", " or ", t)
    t = t.replace("*", "")
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r",\s*([,.;:!?])", r"\1", t)
    t = re.sub(r"([.!?])\s*[,;]", r"\1", t)
    t = re.sub(r"^\s*[,;:]\s*", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    if t and t[-1] not in ".!?":
        t += "."
    return t


# ---------------------------------------------------------------------------------------------
# Writing the broadcast
# ---------------------------------------------------------------------------------------------
def greeting(now):
    h = now.hour
    return "Good morning" if 4 <= h < 12 else "Good afternoon" if 12 <= h < 17 else "Good evening" if 17 <= h < 22 else "Hello"


def long_date(now):
    return f"{WEEKDAYS[now.weekday()]}, {MONTHS[now.month - 1]} {now.day}"


SEVERITY = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3}


def alert_rank(a):
    event = a.get("event") or ""
    kind = 0 if "Warning" in event else 1 if "Watch" in event else 2 if "Advisory" in event else 3
    return (kind, SEVERITY.get(a.get("severity"), 4), a.get("sent") or "")


def where_words(area):
    area = area or ""
    north, south = "Northern La Porte" in area, "Southern La Porte" in area
    return ("northern La Porte County" if north and not south
            else "southern La Porte County" if south and not north else "La Porte County")


def alert_paragraphs(alerts, now):
    rows = [a for a in alerts if a and a.get("event") and (a.get("messageType") or "").lower() != "cancel"]
    if not rows:
        return ["Good news first: there are no watches, warnings or advisories for La Porte County right now."], []
    rows.sort(key=alert_rank)
    n = len(rows)
    out = [f"First, the alerts. The National Weather Service has {'one alert' if n == 1 else str(n) + ' alerts'} "
           f"in effect for La Porte County."]
    for a in rows:
        event = a["event"]
        article = "an" if event[:1].upper() in "AEIOU" else "a"
        span = ""
        try:
            onset = datetime.datetime.fromisoformat(a["onset"]) if a.get("onset") else None
            end_s = a.get("ends") or a.get("expires")
            end = datetime.datetime.fromisoformat(end_s) if end_s else None
            if onset and onset > now + datetime.timedelta(minutes=30):
                span += f" from {bs.clock(onset)} {bs.day_word(onset, now)}"
            if end:
                span += f" until {bs.clock(end)} {bs.day_word(end, now)}"
        except Exception:
            pass
        out.append(f"There is {article} {event} for {where_words(a.get('area'))}{span}.")
        for part in (a.get("description"), a.get("instruction")):
            text = re.sub(r"\s*\n\s*\n\s*", "\n\n", (part or "").strip())
            for para in [p for p in re.split(r"\n\s*\n", text) if p.strip()]:
                out.append(re.sub(r"\s*\n\s*", " ", para.strip()))
    return out, [a.get("id") for a in rows if a.get("id")]


def sky_phrase(weather):
    """The airport's sky and weather words, the way you'd say them: "under mostly cloudy skies"."""
    low = (weather or "").strip().lower().replace("fog/mist", "fog and mist").replace("/", " and ")
    if not low:
        return ""
    if low in ("clear", "fair"):
        return "under clear skies"
    if low == "a few clouds":
        return "with a few clouds"
    if low in ("mostly cloudy", "partly cloudy", "cloudy", "overcast", "mostly clear"):
        return f"under {low} skies"
    return "with " + low


def now_paragraphs(obs, now):
    if not obs or obs.get("temperatureF") is None or not obs.get("time"):
        return []
    try:
        t = datetime.datetime.fromisoformat(obs["time"])
    except Exception:
        return []
    if now - t > datetime.timedelta(hours=OBS_MAX_HOURS):
        return []
    temp = obs["temperatureF"]
    temp_words = f"{temp} degrees" if temp >= 0 else f"{-temp} below zero"
    sky = sky_phrase(obs.get("weather"))
    when = "Right now at the La Porte airport" if now - t <= datetime.timedelta(minutes=45) else f"At {bs.clock(t)}, at the La Porte airport"
    first = f"{when}, it's {temp_words}{' ' + sky if sky else ''}."
    wind = obs.get("wind") or {}
    mph, gust, frm = wind.get("mph"), wind.get("gustMph"), wind.get("from")
    if mph is None:
        second = ""
    elif not mph:
        second = "The wind is calm."
    else:
        direction = COMPASS_WORDS.get(frm or "", "")
        second = f"The wind is {'from the ' + direction + ' ' if direction else ''}at {mph} mph" + (f", gusting to {gust}." if gust else ".")
    return [" ".join(x for x in (first, second) if x)]


COMPASS_WORDS = {"N": "north", "NNE": "north-northeast", "NE": "northeast", "ENE": "east-northeast", "E": "east",
                 "ESE": "east-southeast", "SE": "southeast", "SSE": "south-southeast", "S": "south",
                 "SSW": "south-southwest", "SW": "southwest", "WSW": "west-southwest", "W": "west",
                 "WNW": "west-northwest", "NW": "northwest", "NNW": "north-northwest"}


def period_name(p):
    name = (p.get("name") or "").strip()
    return name[:1].upper() + name[1:].lower() if name else ""


def forecast_paragraphs(periods):
    out = ["Now, the forecast from the National Weather Service."]
    for p in periods[:3]:
        detail = bs.house_style(p.get("detailed") or p.get("short") or "")
        out.append(f"{period_name(p)}: {detail}")
    later = []
    for p in periods[3:7]:
        line = f"{period_name(p)}: {bs.sentence_case(bs.house_style(p.get('short')))}"
        if bs.temp_words(p):
            line += f", {bs.temp_words(p)}"
        chance = bs.nws_chance(p.get("rainChancePercent"))
        if chance:
            line += f", with a {chance}% chance of {bs.precip_word(p.get('short'))}"
        later.append(bs.end_sentence(line))
    if later:
        out.append("Looking further ahead. " + " ".join(later))
    return out


def scoop_paragraphs(posts, today):
    post = bs.todays_post(posts, today)
    if not post or post.get("auto"):
        return [], None
    out = [f"And here's today's Daily Scoop: {bs.end_sentence(post.get('title') or '')}"]
    if post.get("summary"):
        out.append(post["summary"])
    for c in post.get("corrections") or []:
        if c.get("text"):
            out.append("A correction to today's Scoop: " + c["text"])
    out.append("You can read the whole Scoop on our website.")
    return out, post.get("date")


def build_script(data, now):
    segs = []
    intro = (f"{greeting(now)}. This is the La Porte Weather Now weather radio for La Porte County, Indiana, "
             f"with the latest as of {bs.clock(now)}, {long_date(now)}.")
    segs.append({"id": "intro", "title": "Welcome", "paragraphs": [intro]})
    alert_text, alert_ids = alert_paragraphs(data["alerts"], now)
    segs.append({"id": "alerts", "title": "Alerts", "paragraphs": alert_text})
    right_now = now_paragraphs(data.get("observation"), now)
    if right_now:
        segs.append({"id": "now", "title": "Right now", "paragraphs": right_now})
    segs.append({"id": "forecast", "title": "Forecast", "paragraphs": forecast_paragraphs(bs.current_periods(data, now))})
    scoop, scoop_date = scoop_paragraphs(data["posts"], now.date().isoformat())
    if scoop:
        segs.append({"id": "scoop", "title": "Daily Scoop", "paragraphs": scoop})
    outro = ("That's the latest from La Porte Weather Now. If a warning is issued, act on it right away, "
             "and keep your phone's emergency alerts turned on. Stay safe, La Porte County.")
    segs.append({"id": "outro", "title": "Sign-off", "paragraphs": [outro]})
    for s in segs:
        s["spoken"] = [for_ear(p) for p in s["paragraphs"]]
    # What the broadcast says, apart from the clock: a new recording only when this changes.
    basis = json.dumps([greeting(now), now.date().isoformat()] +
                       [s["spoken"] for s in segs if s["id"] not in ("intro", "outro")], ensure_ascii=False)
    return {
        "place": "La Porte County, Indiana",
        "written": now.isoformat(),
        "hash": hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16],
        "alertIds": alert_ids,
        "scoopDate": scoop_date,
        "observationTime": (data.get("observation") or {}).get("time"),
        "forecastUpdated": (data.get("forecast") or {}).get("updated"),
        "source": data["source"],
        "segments": segs,
    }


# ---------------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------------
def gather(now, use_snapshot):
    posts = bs.load_posts()
    if use_snapshot:
        with open(bs.SNAPSHOT, encoding="utf-8") as fh:
            s = json.load(fh)
        return {"source": "snapshot", "fetched": now, "forecast": s["forecast"],
                "alerts": s.get("alertsLaPorteCounty") or [], "observation": s.get("observation"), "posts": posts}
    pt = ns.point()
    fc = ns.forecast(pt)
    alerts = ns.county_alerts()            # raises when no alert request answered
    try:
        obs = ns.observation()
    except Exception as e:
        print(f"No airport reading this time ({str(e)[:120]}).", file=sys.stderr)
        obs = None
    return {"source": "nws", "fetched": now, "forecast": fc, "alerts": alerts, "observation": obs, "posts": posts}


def previous_hash():
    try:
        req = urllib.request.Request(RADIO_JSON_URL + "?t=" + str(int(datetime.datetime.now().timestamp())),
                                     headers={"User-Agent": ns.UA, "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8")).get("hash")
    except Exception:
        return None


def set_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def cmd_script(out_path, force=False, use_snapshot=False):
    now = bs.now_local()
    try:
        data = gather(now, use_snapshot)
    except Exception as e:
        print(f"NWS didn't give both the forecast and the alerts ({str(e)[:200]}); keeping the last recording.")
        set_output("changed", "false")
        return 0
    if len(bs.current_periods(data, now)) < 3:
        print("The NWS forecast came back without enough periods; keeping the last recording.")
        set_output("changed", "false")
        return 0
    script = build_script(data, now)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(script, fh, ensure_ascii=False, indent=2)
    before = None if force else previous_hash()
    changed = force or before != script["hash"]
    set_output("changed", "true" if changed else "false")
    words_count = sum(len(p.split()) for s in script["segments"] for p in s["spoken"])
    print(f"Broadcast {script['hash']} ({words_count} words, about {words_count / 150:.1f} minutes): "
          f"{'new, recording it' if changed else 'same as the current recording'}.")
    return 0


# ---------------------------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------------------------
def cmd_record(script_path, out_dir):
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    with open(script_path, encoding="utf-8") as fh:
        script = json.load(fh)
    os.makedirs(out_dir, exist_ok=True)
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")

    def speak(text):
        # Kokoro takes a pronunciation in [word](/sounds/): La Porte is "luh-PORT" here.
        for word, sounds in PRONOUNCE.items():
            text = text.replace(word, f"[{word}](/{sounds}/)")
        chunks = []
        for result in pipe(text, voice=VOICE, speed=SPEED, split_pattern=r"\n+"):
            audio = result.audio if hasattr(result, "audio") else result[2]
            if audio is None:
                continue
            chunks.append(audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio))
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)

    def silence(seconds):
        return np.zeros(int(RATE * seconds), dtype=np.float32)

    pieces, pos, segments = [], 0, []
    for i, seg in enumerate(script["segments"]):
        start = pos
        for j, line in enumerate(seg["spoken"]):
            audio = speak(line).astype(np.float32)
            pieces.append(audio)
            pos += len(audio)
            gap = silence(PAUSE_PARAGRAPH if j < len(seg["spoken"]) - 1 else PAUSE_SEGMENT)
            pieces.append(gap)
            pos += len(gap)
        segments.append({"id": seg["id"], "title": seg["title"], "start": round(start / RATE, 2),
                         "end": round(pos / RATE, 2), "text": seg["paragraphs"]})
    wav = os.path.join(out_dir, "broadcast.wav")
    sf.write(wav, np.concatenate(pieces), RATE)
    name = f"laporte-{script['hash']}.mp3"
    # Even loudness (like radio), mono speech MP3.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", str(RATE), "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k", os.path.join(out_dir, name)], check=True)
    os.remove(wav)
    radio = {
        "about": "La Porte County weather radio for laporteweathernow.com (Alerts page). Official NWS information "
                 "read by an open-source voice (Kokoro-82M, af_heart). Replaced whenever the broadcast changes.",
        "place": script["place"],
        "recorded": bs.now_local().isoformat(),
        "written": script["written"],
        "hash": script["hash"],
        "audio": name,
        "duration": round(pos / RATE, 1),
        "voice": f"Kokoro-82M {VOICE}",
        "alertIds": script["alertIds"],
        "scoopDate": script["scoopDate"],
        "observationTime": script["observationTime"],
        "forecastUpdated": script["forecastUpdated"],
        "segments": segments,
    }
    with open(os.path.join(out_dir, "radio.json"), "w", encoding="utf-8") as fh:
        json.dump(radio, fh, ensure_ascii=False, indent=2)
    # Keep the script with the recording, for the word check.
    with open(os.path.join(out_dir, "script.json"), "w", encoding="utf-8") as fh:
        json.dump(script, fh, ensure_ascii=False, indent=2)
    print(f"Recorded {name}: {radio['duration']} seconds.")
    return 0


# ---------------------------------------------------------------------------------------------
# Word check
# ---------------------------------------------------------------------------------------------
def normalize_words(text):
    t = text.lower().replace("-", " ")
    t = re.sub(r"\b\d+\b", lambda m: words(m.group(0)).replace("-", " "), t)
    return re.findall(r"[a-z']+", t)


def cmd_check(out_dir):
    try:
        return word_check(out_dir)
    except Exception:
        import traceback
        report = "The word check couldn't run:\n" + traceback.format_exc()
        print(report)
        with open(os.path.join(out_dir, "check.txt"), "w", encoding="utf-8") as fh:
            fh.write(report)
        return 0


def word_check(out_dir):
    from faster_whisper import WhisperModel
    with open(os.path.join(out_dir, "radio.json"), encoding="utf-8") as fh:
        radio = json.load(fh)
    with open(os.path.join(out_dir, "script.json"), encoding="utf-8") as fh:
        script = json.load(fh)
    import numpy as np
    # ffmpeg decodes the MP3 (16 kHz mono), so the check doesn't depend on faster-whisper's own decoder.
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(out_dir, radio["audio"]),
                          "-ar", "16000", "-ac", "1", "-f", "f32le", "-"], check=True, capture_output=True).stdout
    samples = np.frombuffer(raw, dtype=np.float32)
    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(samples, beam_size=5, language="en")
    heard = " ".join(s.text.strip() for s in segs)
    said = " ".join(p for s in script["segments"] for p in s["spoken"])
    a, b = normalize_words(said), normalize_words(heard)
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    lines = [f"Word check of {radio['audio']} (recorded {radio['recorded']}): {ratio:.1%} of the words match "
             f"({len(a)} written, {len(b)} heard by speech-to-text).", "", "HEARD:", heard, "", "DIFFERENCES (written -> heard):"]
    sm = difflib.SequenceMatcher(None, a, b)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            lines.append(f"  {' '.join(a[i1:i2]) or '-'}  ->  {' '.join(b[j1:j2]) or '-'}")
    report = "\n".join(lines) + "\n"
    print(report)
    # Saved with the recording (the radio branch), so the check can be read without the job log.
    with open(os.path.join(out_dir, "check.txt"), "w", encoding="utf-8") as fh:
        fh.write(report)
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "script":
        return cmd_script(argv[2], force="--force" in argv, use_snapshot="--snapshot" in argv)
    if len(argv) >= 4 and argv[1] == "record":
        return cmd_record(argv[2], argv[3])
    if len(argv) >= 3 and argv[1] == "check":
        return cmd_check(argv[2])
    if len(argv) >= 3 and argv[1] == "say":
        print(for_ear(" ".join(argv[2:])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
