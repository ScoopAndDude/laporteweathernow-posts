#!/usr/bin/env python3
"""The Daily Scoop, written by fixed rules, with no AI (added Oct. 18, 2026).

Scoop: "the daily scoop cant rely on ai usage how can i automate it without ai?", then "yes build it".
The morning Scoop had been written by an AI task that sometimes ran out of usage, which left the automatic
NWS backup up instead. This writes the same kind of post every morning from the same official data, in
fixed sentences, the way the Daily Video and the automatic updates already do. It runs free on GitHub,
so there's nothing to run out of.

  python3 scripts/scoop_writer.py build OUT.json     write today's post to OUT.json (and its commit message
                                                     to OUT.json.msg) when one is due; writes nothing otherwise
  python3 scripts/scoop_writer.py insert OUT.json    add it to scoop-posts.json, in place of today's automatic
                                                     backup if that's up, unless a written Scoop got there first
  python3 scripts/scoop_writer.py preview [--now ISO] [--snapshot F] [--posts F] [--scorecard F] [--updates F]
                                                     print the post it would write ({"post", "words", "notes"}),
                                                     ignoring the clock and today's post; posts nothing

Where everything comes from (all official and public):
- nws-snapshot.json (scripts/nws_snapshot.py, saved by the "NWS weather snapshot" job at about 5 a.m.):
  - the NWS forecast for La Porte;
  - NWS alerts for La Porte County and next door;
  - the La Porte airport (KPPO);
  - the KEY MESSAGES of the NWS Northern Indiana forecast discussion;
  - SPC's storm outlooks and WPC's flooding-rain outlooks;
  - NWS's hour-by-hour rain chances for work hours, and NWS's rain amounts;
  - our blend of NWS and four computer models (scripts/consensus.py).
- scorecard.json: how yesterday's forecast did at the La Porte airport.
- scoop-updates.json: the forecast yesterday's Scoop was written from (scripts/scoop_update.py keeps it).
  This is for "What changed since yesterday's Scoop".

The post has the same shape as every Daily Scoop: title, summary, four paragraphs, sources, and the two
forecasts the Track Record grades. The paragraphs are: today; the next few days; what changed and what NWS
forecasters say; and right now (alerts and risks).

The rules are the same as the morning task's:
- Only numbers the sources state. Our own numbers are the blend's, and the post says so.
- Calm and factual. We pass along official alerts; we never issue our own warnings.
- All times are Central. NWS's forecast wording already is (nws_snapshot.text_in_zone); the times in the
  discussion are Eastern and are converted.
- About 250 words, never more than 320. Extras are dropped first, in a fixed order; alert information
  is never cut.
- It never posts twice and never changes a written Scoop that's already up (scoop_update.py adds the
  day's updates).
- No post without the NWS forecast and NWS alerts, from a snapshot fetched today in the last 3 hours.
"""
import argparse
import datetime
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backup_scoop as bs  # noqa: E402
import daily_video as dv  # noqa: E402
import radio_broadcast as rb  # noqa: E402
import scoop_update as su  # noqa: E402

REPO = os.path.normpath(os.path.join(HERE, ".."))
SNAPSHOT = os.path.join(REPO, "nws-snapshot.json")
SCORECARD = os.path.join(REPO, "scorecard.json")
UPDATES = os.path.join(REPO, "scoop-updates.json")
TZ = bs.TZ
EASTERN = ZoneInfo("America/New_York")
WEEKDAYS = bs.WEEKDAYS
START = (5, 25)                          # the snapshot job runs at about 5:00 a.m.
STOP = (14, 0)                           # after 2 p.m. a morning Scoop isn't worth posting
SNAPSHOT_MAX = datetime.timedelta(hours=3)
OBS_MAX = datetime.timedelta(hours=2)
AFD_MAX = datetime.timedelta(hours=18)
WORD_MAX = 320
HORIZON = 5                              # days ahead in paragraph 2
TEMP_STEP, RAIN_STEP = 4, 20             # "what changed": 4 degrees, 20 points of rain chance
FORECAST_URL = bs.FORECAST_URL
AFD_URL = "https://forecast.weather.gov/product.php?site=IWX&issuedby=IWX&product=AFD"
SPC_URL = "https://www.spc.noaa.gov/products/outlook/"
WPC_URL = "https://www.wpc.ncep.noaa.gov/qpf/excessive_rainfall_outlook_ero.php"
OPEN_METEO = {"label": "Computer model forecasts from Open-Meteo (CC BY 4.0)", "url": "https://open-meteo.com/"}
SHORT_FUSED = dv.SHORT_FUSED
WET = r"rain|shower|drizzle|thunder|storm|snow|sleet|flurr|ice|freezing"
# One short tip for the alert that leads the post, in plain words.
ALERT_TIPS = [
    (r"Frost|Freeze", "Cover or bring in tender plants."),
    (r"Wind Advisory|High Wind|Extreme Wind", "Secure anything loose outside, and expect gusty crosswinds on the roads."),
    (r"Dense Fog", "Slow down, use low beams and leave extra room on the road."),
    (r"Winter|Snow|Blizzard|Ice Storm|Freezing", "Allow extra time on the roads."),
    (r"Heat", "Drink water and take breaks in the shade."),
    (r"Flood", "Never drive through flooded roads."),
    (r"Wind Chill|Cold", "Bundle up and limit time outside."),
    (r"Beach Hazards|Rip Current", "Stay out of the water and off the piers."),
    (r"Air Quality", "Take it easy outdoors if you're sensitive to bad air."),
]


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def parse(s):
    return datetime.datetime.fromisoformat(s) if s else None


def local(s):
    return parse(s).astimezone(TZ)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def upper_first(s):
    return s[:1].upper() + s[1:] if s else s


def lower_first(s):
    return dv.lower_first(s) if s else s


def join_and(parts):
    parts = [p for p in parts if p]
    if not parts:
        return ""
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def words(text):
    return len(re.findall(r"\S+", text or ""))


def a_or_an(word):
    """'a 70%', 'an 80%', 'an 11%', 'a Wind Advisory', 'an Air Quality Alert'."""
    w = str(word).strip()
    if re.match(r"(8|11\b|18\b)", w) or w[:1].upper() in "AEIOU":
        return "an"
    return "a"


def names_run(names):
    """'Monday', 'Monday and Tuesday', 'Monday through Thursday'."""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{names[0]} through {names[-1]}"


def temps_run(values, word):
    lo, hi = min(values), max(values)
    return f"{word} near {lo}" if lo == hi else f"{word}s {lo} to {hi}"


def chance(p):
    return bs.nws_chance((p or {}).get("rainChancePercent")) or 0


def night_of(p):
    """The date a night period belongs to: the evening it starts (an early-morning "Overnight" is last night)."""
    return (local(p["end"]) - datetime.timedelta(days=1)).date()


def friendly(short):
    return dv.friendly(short)


def with_chance(short, c):
    """NWS's short forecast in plain words with its chance after the wet part:
    'Mostly cloudy, then a chance of showers (30%)', 'Showers likely (70%), then partly cloudy'."""
    text = lower_first(friendly(short))
    if not c:
        return text
    parts = text.split(", then ")
    i = next((k for k, p in enumerate(parts) if re.search(WET, p, re.I)), 0)
    parts[i] = f"{parts[i]} ({c}%)"
    return ", then ".join(parts)


def sky(short, c):
    """A short sky phrase for titles: the dry part when rain is unlikely, the wet part when it's likely."""
    parts = lower_first(friendly(short)).split(", then ")
    wet = [p for p in parts if re.search(WET, p, re.I)]
    if c >= 30 and wet:
        return wet[0]
    main = [p for p in parts if not re.search(WET + r"|frost|fog", p, re.I)]
    return (main or parts)[0]


def temp_word(hi):
    if hi is None:
        return ""
    return ("hot" if hi >= 88 else "warm" if hi >= 75 else "mild" if hi >= 60 else "cool" if hi >= 45
            else "chilly" if hi >= 33 else "cold")


def max_wind(p):
    nums = [int(x) for x in re.findall(r"\d+", (p or {}).get("wind") or "")]
    return max(nums) if nums else 0


SENTENCE = re.compile(r"(?<=\.)\s+(?=[A-Z])")
WIND_SENTENCE = re.compile(r"\b(wind|winds)\b", re.I)
CHANCE_SENTENCE = re.compile(r"^Chance of precipitation is \d+%\.?$", re.I)


def nws_words(p, keep_wind, keep_chance=True):
    """NWS's own forecast wording for a period, in the site's style, with or without its wind and its
    "Chance of precipitation" sentences."""
    raw = re.sub(r"\s+", " ", (p or {}).get("detailed") or "").strip()
    out = []
    for s in SENTENCE.split(raw):
        s = s.strip()
        if not s:
            continue
        if WIND_SENTENCE.search(s) and "mph" in s and not keep_wind:
            continue
        if CHANCE_SENTENCE.match(s) and not keep_chance:
            continue
        out.append(s)
    return bs.house_style(" ".join(out))


def eastern_times_to_central(text):
    """Clock times in the NWS Northern Indiana discussion are the office's (Eastern) time."""
    def fix(m):
        h, mm, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
        h24 = (h % 12) + (12 if ap == "pm" else 0)
        t = datetime.datetime(2000, 1, 1, h24, mm, tzinfo=TZ) - datetime.timedelta(hours=1)
        return f"{bs.clock(t)} Central"
    return re.sub(r"\b(1[0-2]|[1-9])(?::?([0-5]\d))?\s*(AM|PM)(?:\s*(?:EDT|EST|ET))?\b", fix, text)


class Piece:
    """A sentence of the post. rank 0 is never dropped; higher ranks go first when the post runs long.
    alt is a shorter version used instead of dropping it (None: drop it)."""

    def __init__(self, text, rank=0, alt=None):
        self.text, self.rank, self.alt = text, rank, alt


def para(pieces):
    return " ".join(p.text for p in pieces if p.text)


# ---------------------------------------------------------------------------------------------
# Reading the snapshot
# ---------------------------------------------------------------------------------------------
class Day:
    """One day ahead: its daytime period and the night after it."""

    def __init__(self, date, day, night):
        self.date, self.day, self.night = date, day, night
        self.name = WEEKDAYS[date.weekday()]

    @property
    def high(self):
        return (self.day or {}).get("temperatureF")

    @property
    def rain(self):
        return max(chance(self.day), chance(self.night))

    def shorts(self):
        return f"{(self.day or {}).get('short') or ''} {(self.night or {}).get('short') or ''}"

    def kind(self):
        """quiet (no rain chance), chance (20-50%), or big (likely rain, snow, or strong gusts)."""
        g = max(dv.gust_of(self.day or {}) or 0, dv.gust_of(self.night or {}) or 0)
        if self.rain == 0 and not re.search(WET, self.shorts(), re.I) and g < 30:
            return "quiet"
        if self.rain >= 60 or re.search(r"likely|snow|sleet|freezing|flurr", self.shorts(), re.I) or g >= 30:
            return "big"
        return "chance"


class Weather:
    def __init__(self, snap, now):
        self.snap, self.now = snap, now
        self.today = now.date()
        self.periods = [p for p in (snap.get("forecast") or {}).get("periods") or [] if local(p["end"]) > now]
        self.day = next((p for p in self.periods[:2] if p.get("isDaytime") and local(p["start"]).date() <= self.today), None)
        self.night = next((p for p in self.periods[:3] if not p.get("isDaytime") and night_of(p) == self.today), None)
        self.ahead = []
        for p in self.periods:
            d = local(p["start"]).date()
            if p.get("isDaytime") and d > self.today:
                n = next((q for q in self.periods if not q.get("isDaytime") and night_of(q) == d), None)
                self.ahead.append(Day(d, p, n))
        self.alerts = dv.active_alerts(snap.get("alertsLaPorteCounty"), now)
        self.obs = snap.get("observation") or {}
        self.errors = {e.get("source") for e in snap.get("errors") or []}

    def label(self, p):
        if p is None:
            return ""
        if p.get("isDaytime"):
            d = local(p["start"]).date()
            return "today" if d <= self.today else WEEKDAYS[d.weekday()]
        d = night_of(p)
        return "tonight" if d == self.today else f"{WEEKDAYS[d.weekday()]} night"

    def workday(self, date):
        """[(hour, chance)] for NWS's work-hours rain chances (6 a.m. to 6 p.m.) on that date, from now on."""
        for d in (self.snap.get("workdayRain") or {}).get("days") or []:
            if d.get("date") == date.isoformat():
                return [(int(h["hour"]), int(h.get("rainChancePercent") or 0)) for h in d.get("hours") or []
                        if date > self.today or int(h["hour"]) >= self.now.hour]
        return []


def hour_clock(h):
    return bs.clock(datetime.datetime(2000, 1, 1, h % 24, 0, tzinfo=TZ))


def rain_timing(hours, what):
    """(words, shape) for work-hours rain, e.g. ('mostly dry until about 1 p.m., then rain likely (up to 64%)',
    'late'). shape is '', 'all', 'early', 'late' or 'middle'."""
    wet = [(h, c) for h, c in hours if c >= 30]
    if not wet:
        return "", ""
    peak = max(c for _, c in wet)
    kind = "likely" if peak >= 50 else "possible"
    first, last = wet[0][0], wet[-1][0] + 1
    start, end = hours[0][0], hours[-1][0] + 1
    tail = f" (up to {peak}%)"
    if first <= start and last >= end:
        return f"{what} {kind} through the workday{tail}", "all"
    if first <= start:
        return f"{what} {kind} until about {hour_clock(last)}{tail}, then drier", "early"
    if last >= end:
        return f"mostly dry until about {hour_clock(first)}, then {what} {kind}{tail}", "late"
    return f"{what} {kind} from about {hour_clock(first)} to {hour_clock(last)}{tail}", "middle"


# ---------------------------------------------------------------------------------------------
# Alerts, in the same words everywhere in the post
# ---------------------------------------------------------------------------------------------
def alert_span(a, now):
    """' until 8 a.m. today', ' from 1 to 10 p.m. today', ' from 2 to 8 a.m. Sunday', ' from 7 p.m. Friday until 4 a.m. Saturday'."""
    try:
        onset, end = parse(a.get("onset")), parse(a.get("ends") or a.get("expires"))
    except Exception:
        return ""
    later = onset and onset > now + datetime.timedelta(minutes=30)
    if later and end:
        o, e = onset.astimezone(TZ), end.astimezone(TZ)
        ow, ew = dv.when_word(o, now), dv.when_word(e, now)
        if o.date() == e.date() and (o.hour < 12) == (e.hour < 12):
            oc = bs.clock(o).replace(" a.m.", "").replace(" p.m.", "")
            return f" from {oc} to {bs.clock(e)} {ow}"
        if ow == ew or (ow == "today" and ew == "tonight"):
            return f" from {bs.clock(o)} to {bs.clock(e)} {ow}"
        return f" from {bs.clock(o)} {ow} until {bs.clock(e)} {ew}"
    if later:
        return f" starting at {bs.clock(onset)} {dv.when_word(onset, now)}"
    if end:
        return f" until {bs.clock(end)} {dv.when_word(end, now)}"
    return ""


def alert_sentence(a, now):
    event = a["event"]
    return f"NWS has {a_or_an(event)} {event} for {rb.where_words(a.get('area'))}{alert_span(a, now)}."


def alert_tip(event):
    return next((tip for pat, tip in ALERT_TIPS if re.search(pat, event, re.I)), "")


# ---------------------------------------------------------------------------------------------
# Paragraph 1: today
# ---------------------------------------------------------------------------------------------
def bottom_line(w):
    """(opening sentence, kind). The kind tells the rest of the post what the opener already covered."""
    now, day, night = w.now, w.day, w.night
    hi = (day or {}).get("temperatureF")
    short = (day or {}).get("short") or ""
    c = chance(day)

    if w.alerts:
        a = w.alerts[0]
        if a["event"] in SHORT_FUSED:
            return alert_sentence(a, now) + " If you're in the warned area, follow NWS's instructions now.", "alert"
        tip = alert_tip(a["event"])
        return alert_sentence(a, now) + (f" {tip}" if tip else ""), "alert"

    lvl, _ = dv.spc_level(w.snap)
    stormy = re.search(r"thunder|storm", f"{short} {(night or {}).get('short')}", re.I)
    if lvl and stormy:
        when = "today" if re.search(r"thunder|storm", short, re.I) else "tonight"
        return (f"Storms are possible {when}, and NOAA's Storm Prediction Center has La Porte at level {lvl} of 5 "
                f"for severe storms. Keep a way to get warnings handy.", "storms")

    for q in (day, night):
        if q and re.search(r"snow|flurr", q.get("short") or "", re.I) and chance(q) >= 30:
            amt = dv.snow_words(q)
            return (f"Snow {w.label(q)}" + (f", {amt} possible, says NWS" if amt else "") +
                    ". Allow extra time on the roads.", "snow")

    if day and c >= 30 and re.search(r"rain|shower|drizzle|thunder", short, re.I):
        timing, shape = rain_timing(w.workday(w.today), su.precip(short))
        what = su.precip(short)
        if shape == "late":
            hour = timing.split("until about ")[1].split(",")[0]
            return (bs.end_sentence(f"Dry this morning, but take an umbrella after about {hour}"), "rain-timed")
        if shape == "early":
            return (f"An early {what if what != 'rain' else 'shower'} is possible, then it's mostly dry.", "rain-timed")
        if c >= 50:
            return ("A wet day: take an umbrella.", "rain")
        return (f"Keep an umbrella handy: NWS gives today {a_or_an(c)} {c}% chance of {what}.", "rain")

    if night:
        lo = night.get("temperatureF")
        fw = dv.frost_words(night)
        edge = now.month in (4, 5, 9, 10, 11)
        if lo is not None and lo <= 32 and edge:
            return (f"Below freezing tonight, with a low around {lo}: cover or bring in tender plants.", "frost")
        if fw and edge:
            return (f"{fw} is possible tonight: keep the plant covers handy.", "frost")
        if chance(night) >= 50 and re.search(WET, night.get("short") or "", re.I):
            what = "storms move" if re.search(r"thunder", night.get("short") or "", re.I) else f"{su.precip(night.get('short'))} moves"
            return (f"Dry by day, but {what} in tonight.", "rain-night")

    if hi is not None and hi >= 90:
        return ("A hot one: drink water and take breaks in the shade.", "heat")
    g = max(dv.gust_of(day or {}) or 0, dv.gust_of(night or {}) or 0)
    if g >= 35:
        return ("A windy day: secure anything loose outside.", "wind")
    if re.search(r"\bfog\b", short, re.I):
        return ("Watch for fog on the morning drive.", "fog")
    if hi is not None and hi <= 25:
        return ("A cold one: bundle up.", "cold")
    if c and re.search(WET, short, re.I):
        return (f"Mostly dry today, with {a_or_an(c)} {c}% chance of a passing {su.precip(short) if su.precip(short) != 'rain' else 'shower'}.", "slight")
    if hi is not None and 60 <= hi <= 84 and c == 0 and re.search(r"sunny|clear", short, re.I) \
            and not re.search(WET + r"|fog", short, re.I):
        return ("A great day to be outside.", "nice")
    if day:
        return (f"{upper_first(sky(short, c))} and {temp_word(hi)} today.", "plain")
    return ("", "plain")


def airport_piece(w, notes):
    obs, t = w.obs, None
    try:
        t = local(obs["time"]) if obs.get("time") else None
    except Exception:
        t = None
    if not (t and obs.get("temperatureF") is not None and w.now - t <= OBS_MAX):
        notes.append("airport reading left out (missing or over 2 hours old)")
        return None
    weather = (obs.get("weather") or "").strip().lower().replace("fog/mist", "fog")
    return Piece(f"The La Porte airport at {bs.clock(t)}: {weather + ' and ' if weather else ''}{obs['temperatureF']}.", 3)


def today_pieces(w, notes):
    line, kind = bottom_line(w)
    out = [Piece(line)] if line else []
    if len(w.alerts) > 1:
        others = [f"{a_or_an(a['event'])} {a['event']}" for a in w.alerts[1:]]
        out.append(Piece(f"NWS also has {join_and(others)} for La Porte County (details below)."))
    if w.day:
        g = dv.gust_of(w.day) or 0
        keep_wind = g >= 25 or max_wind(w.day) >= 20
        lab = upper_first(w.label(w.day))
        out.append(Piece(bs.end_sentence(f"{lab}, NWS says: {nws_words(w.day, keep_wind, chance(w.day) >= 30)}"), 2,
                         bs.end_sentence(f"{lab}, NWS says: {nws_words(w.day, keep_wind and g >= 35, False)}")))
        timing, _ = rain_timing(w.workday(w.today), su.precip(w.day.get("short")))
        if timing and kind != "rain-timed":
            out.append(Piece(bs.end_sentence(f"Its hour-by-hour forecast for work hours: {timing}"), 4))
    if w.night:
        g = dv.gust_of(w.night) or 0
        lab = upper_first(w.label(w.night))
        out.append(Piece(bs.end_sentence(f"{lab}: {nws_words(w.night, g >= 35, chance(w.night) >= 30)}"), 2,
                         bs.end_sentence(f"{lab}: {nws_words(w.night, g >= 45, False)}")))
    a = airport_piece(w, notes)
    if a:
        out.append(a)
    if kind not in ("alert", "fog"):
        text = f"{(w.day or {}).get('detailed')} {(w.night or {}).get('detailed')}"
        if re.search(r"\b(dense|patchy|areas of) fog\b", text, re.I):
            out.append(Piece("Leave extra room on the road if you hit fog.", 5))
    return out, kind


# ---------------------------------------------------------------------------------------------
# Paragraph 2: the next few days
# ---------------------------------------------------------------------------------------------
def frost_note(days):
    nights = [d for d in days if d.night and dv.frost_words(d.night)]
    if not nights:
        return ""
    fw = lower_first(dv.frost_words(nights[0].night))
    return f", with {fw} possible {join_and([d.name + ' night' for d in nights])}"


def sky_words(days):
    shorts = [((d.day or {}).get("short") or "").lower() for d in days]
    if all(s == "sunny" for s in shorts):
        return "sunny and dry"
    if all(s in ("sunny", "mostly sunny", "clear", "mostly clear") for s in shorts):
        return "mostly sunny and dry"
    return "dry"


def big_clause(d):
    bits = []
    if d.day:
        bits.append(f"{with_chance(d.day.get('short'), chance(d.day))}, high near {d.high}")
    if d.night and chance(d.night):
        bits.append(f"{d.name} night {with_chance(d.night.get('short'), chance(d.night))}")
    g = max(dv.gust_of(d.day or {}) or 0, dv.gust_of(d.night or {}) or 0)
    if g >= 30:
        bits.append(f"gusts as high as {g} mph")
    snow = dv.snow_words(d.day or {}) or dv.snow_words(d.night or {})
    if snow:
        bits.append(f"{snow} of snow possible")
    return f"{d.name}: " + "; ".join(bits) + frost_note([d])


def chance_clause(group):
    what = "showers and thunderstorms" if re.search(r"thunder", " ".join(d.shorts() for d in group), re.I) else \
        su.precip(*[d.shorts() for d in group]).replace("rain", "showers")
    rains = [d.rain for d in group]
    lo, hi = min(rains), max(rains)
    pct = f"{lo}%" if lo == hi else f"{lo} to {hi}%"
    when = names_run([d.name for d in group])
    at_times = " at times" if len(group) > 1 else ""
    return f"{when}: a chance of {what}{at_times} ({pct}), {temps_run([d.high for d in group], 'high')}" + frost_note(group)


def ahead_clauses(w):
    days = [d for d in w.ahead[:HORIZON] if d.high is not None]
    clauses, i = [], 0
    while i < len(days):
        k = days[i].kind()
        if k == "big":
            clauses.append(big_clause(days[i]))
            i += 1
            continue
        j = i
        while j + 1 < len(days) and days[j + 1].kind() == k:
            j += 1
        group = days[i:j + 1]
        if k == "quiet":
            clauses.append(f"{upper_first(sky_words(group))} {names_run([d.name for d in group])}, "
                           f"{temps_run([d.high for d in group], 'high')}{frost_note(group)}")
        else:
            clauses.append(chance_clause(group))
        i = j + 1
    return clauses, days


def rain_total_sentence(w):
    r = w.snap.get("rain") or {}
    total = r.get("next72hInches")
    if total is None or total < 0.25:
        return ""
    snowy = any(re.search(r"snow|sleet|freezing", (p.get("short") or ""), re.I) for p in w.periods[:6])
    what = "precipitation (rain and melted snow)" if snowy else "rain"
    amount = f"{total:.1f}"
    return f"NWS's forecast {what} adds up to about {amount} {'inch' if total < 1.05 else 'inches'} over the next three days."


def blend(w):
    """(sentence, uncertain sentence, used): where our blend differs from NWS by 3+ degrees, for the
    two days the Track Record grades, and which of those days the models disagree on."""
    c = w.snap.get("consensus") or {}
    if not c or "Computer models (Open-Meteo)" in w.errors:
        return "", "", False
    rows = {x.get("date"): x for x in c.get("days") or []}
    nws_bits, our_bits, unsure = [], [], []
    for s in (c.get("suggested") or [])[:2]:
        date = datetime.date.fromisoformat(s["date"])
        nws = ((rows.get(s["date"]) or {}).get("nws")) or {}
        eve = date - datetime.timedelta(days=1)
        night_label = "tonight" if eve == w.today else f"{WEEKDAYS[eve.weekday()]} night"
        for kind, label in (("low", night_label), ("high", WEEKDAYS[date.weekday()])):
            ours, theirs = s.get(kind), nws.get(kind)
            if ours is None or theirs is None or abs(ours - theirs) < 3:
                continue
            nws_bits.append(f"{'a low around' if kind == 'low' else 'a high near'} {theirs} {label}")
            our_bits.append(str(ours))
        note = (rows.get(s["date"]) or {}).get("note") or ""
        for kind in re.findall(r"the models disagree on the (high|low)", note):
            unsure.append(f"{WEEKDAYS[date.weekday()]}'s high" if kind == "high" else f"{night_label}'s low")
    sentence = ""
    if nws_bits:
        sentence = (f"NWS says {join_and(nws_bits)}; our blend of NWS and four computer models says "
                    f"{join_and(our_bits)}, so that's our forecast.")
    unsure_s = ""
    if unsure:
        unsure_s = (f"The models disagree on {join_and(unsure)}, so "
                    f"{'that is' if len(unsure) == 1 else 'those are'} less certain.")
    return sentence, unsure_s, bool(nws_bits or unsure)


def ahead_pieces(w, notes):
    clauses, days = ahead_clauses(w)
    if not clauses:
        notes.append("no days ahead in the forecast")
        return [], days, False
    out = [Piece(bs.end_sentence(c)) for c in clauses]
    total = rain_total_sentence(w)
    if total:
        out.append(Piece(total, 5))
    blend_s, unsure_s, used = blend(w)
    if blend_s:
        out.append(Piece(blend_s))
    if unsure_s:
        out.append(Piece(unsure_s, 5))
    return out, days, used


# ---------------------------------------------------------------------------------------------
# Paragraph 3: what changed, what NWS forecasters say, how yesterday's forecast did
# ---------------------------------------------------------------------------------------------
def changes_sentence(w, updates, notes):
    if not updates or updates.get("kind") != "written" or not updates.get("date"):
        notes.append("no written Scoop baseline in scoop-updates.json; 'what changed' left out")
        return ""
    base_date = datetime.date.fromisoformat(updates["date"])
    if base_date >= w.today or (w.today - base_date).days > 3:
        notes.append(f"baseline is from {base_date}; 'what changed' left out")
        return ""
    base = ((updates.get("baseline") or {}).get("periods")) or {}
    cur = su.period_values(w.periods)
    t0, t1, t2 = w.today, w.today + datetime.timedelta(days=1), w.today + datetime.timedelta(days=2)
    keys = [(f"day {t0}", "today's", "high"), (f"night {t0}", "tonight's", "low"),
            (f"day {t1}", f"{WEEKDAYS[t1.weekday()]}'s", "high"), (f"night {t1}", f"{WEEKDAYS[t1.weekday()]} night's", "low"),
            (f"day {t2}", f"{WEEKDAYS[t2.weekday()]}'s", "high")]
    found = []
    for k, when, word in keys:
        b, c = base.get(k), cur.get(k)
        if not b or not c:
            continue
        frm, to = b.get("rain") or 0, c.get("rain") or 0
        if abs(to - frm) >= RAIN_STEP:
            what = su.precip(c.get("short"), b.get("short"))
            if to == 0:
                phrase = f"the {what} is out of {when} forecast (it was {frm}%)"
            elif frm == 0:
                phrase = f"{when[:-2]} now has {a_or_an(to)} {to}% chance of {what}"
            else:
                phrase = f"{when} chance of {what} is now {to}% (from {frm}%)"
            found.append((2, abs(to - frm), phrase))
        if b.get("temp") is not None and c.get("temp") is not None and abs(c["temp"] - b["temp"]) >= TEMP_STEP:
            found.append((1, abs(c["temp"] - b["temp"]), f"{when} {word} is now {c['temp']} (from {b['temp']})"))
    old = {a.get("event") for a in (updates.get("baseline") or {}).get("alerts") or []}
    for a in w.alerts:
        if a["event"] not in old:
            found.append((3, 0, f"NWS has since issued {a_or_an(a['event'])} {a['event']}"))
    found.sort(key=lambda x: (-x[0], -x[1]))
    since = "yesterday's" if base_date == w.today - datetime.timedelta(days=1) else f"{WEEKDAYS[base_date.weekday()]}'s"
    if not found:
        return (f"What changed since {since} Scoop: not much. NWS's highs and lows through {WEEKDAYS[t2.weekday()]} "
                f"moved less than {TEMP_STEP} degrees, and its rain chances less than {RAIN_STEP} points.")
    if found[0][0] < 3:
        return f"What changed in NWS's forecast since {since} Scoop: {join_and([f[2] for f in found[:3]])}."
    return f"What changed since {since} Scoop: {join_and([f[2] for f in found[:3]])}."


def key_messages(w, notes):
    """([quoted key messages], issue time) from the NWS Northern Indiana forecast discussion."""
    d = w.snap.get("discussion") or {}
    text, issued = d.get("text") or "", parse(d.get("issued"))
    if not text or not issued:
        notes.append("no forecast discussion in the snapshot")
        return [], None
    if w.now - issued > AFD_MAX:
        notes.append("forecast discussion over 18 hours old; left out")
        return [], None
    m = re.search(r"KEY MESSAGES\.{0,3}\s*(.*?)(?:\n\s*&&|\n\s*\.[A-Z][A-Z ]+\.{3})", text, re.S)
    if not m:
        notes.append("the discussion has no KEY MESSAGES section")
        return [], issued
    bullets = [re.sub(r"\s+", " ", b).strip(" -") for b in re.split(r"\n\s*-\s+", "\n" + m.group(1).strip())]
    bullets = [bs.end_sentence(eastern_times_to_central(b)) for b in bullets if len(b) > 10]
    return bullets[:2], issued


def fmt_temp(v):
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return f"{v[0]} to {v[1]}"
    return str(v)


def scorecard_sentence(w, sc, notes):
    latest = (sc or {}).get("latest") or {}
    yesterday = (w.today - datetime.timedelta(days=1)).isoformat()
    if latest.get("date") != yesterday or latest.get("status") != "scored" or yesterday in ((sc or {}).get("thinDays") or {}):
        notes.append("scorecard has no graded day for yesterday")
        return ""
    fc, ob = latest.get("forecast") or {}, latest.get("observed") or {}
    said, got = [f"a high of {fmt_temp(fc.get('high'))}"], [str(ob.get("high"))]
    if (latest.get("low") or {}).get("hit") is False and fc.get("low") is not None:
        said.append(f"a low of {fmt_temp(fc.get('low'))}")
        got.append(str(ob.get("low")))
    tail = ""
    if (latest.get("rain") or {}).get("hit") is False and fc.get("rain") is not None:
        said.append(f"{a_or_an(fc['rain'])} {fc['rain']}% chance of rain")
        tail = " and got rain" if ob.get("rained") else " and stayed dry"
    lead = latest.get("leadDays")
    who = "Yesterday we said" if lead == 1 else f"For yesterday, our {bs.ap_date(latest.get('fromPost'))} Scoop said"
    return f"{who} {join_and(said)}; the La Porte airport got {join_and(got)}{tail}."


def third_pieces(w, updates, sc, notes):
    out = []
    changed = changes_sentence(w, updates, notes)
    if changed:
        out.append(Piece(changed))
    keys, issued = key_messages(w, notes)
    if keys:
        head = "NWS Northern Indiana forecasters' key messages this morning:"
        if len(keys) > 1:
            out.append(Piece(f'{head} "{keys[0]}" "{keys[1]}"', 6, f'{head} "{keys[0]}"'))
        else:
            out.append(Piece(f'{head} "{keys[0]}"'))
    score = scorecard_sentence(w, sc, notes)
    if score:
        out.append(Piece(score))
    return out, (issued if keys else None)


# ---------------------------------------------------------------------------------------------
# Paragraph 4: right now
# ---------------------------------------------------------------------------------------------
def nearby_alerts(w):
    out = []
    lp_ids = {a.get("id") for a in w.alerts}
    for a in dv.active_alerts(((w.snap.get("alertsNearby") or {}).get("nearbyCountiesFullText")) or [], w.now):
        if a.get("id") in lp_ids:
            continue
        area = [x.strip() for x in (a.get("area") or "").split(";")]
        counties = [c for c in ("Porter", "Lake") if c in area]
        if not counties:
            continue
        sender = re.sub(r"\s+[A-Z]{2}$", "", a.get("sender") or "NWS")
        where = "Porter and Lake counties" if len(counties) == 2 else f"{counties[0]} County"
        out.append(f"{sender} has {a_or_an(a['event'])} {a['event']} for {where}{alert_span(a, w.now)}")
    return out


SPC_WORDS = (("High", 5), ("Moderate", 4), ("Enhanced", 3), ("Slight", 2), ("Marginal", 1))


def spc_phrase(w):
    days = sorted(w.snap.get("spc") or [], key=lambda d: d.get("day") or 0)
    if not days:
        return ""
    names, severe, general, none_ = [], [], [], []
    for d in days:
        n = int(d.get("day") or 1)
        date = w.today + datetime.timedelta(days=n - 1)
        label = ("today" if w.now.hour < 17 else "tonight") if n == 1 else WEEKDAYS[date.weekday()]
        names.append(label)
        risk = d.get("riskAtLaPorte") or ""
        lvl = next((v for word, v in SPC_WORDS if word.lower() in risk.lower()), None)
        if lvl:
            word = next(word for word, v in SPC_WORDS if v == lvl)
            severe.append(f"{a_or_an(word)} {word.lower()} (level {lvl} of 5) risk of severe storms here {label}")
        elif "general" in risk.lower():
            general.append(label)
        else:
            none_.append(label)
    if severe:
        s = "SPC has " + join_and(severe)
        if general:
            s += f", and only general thunderstorms {join_and(general)}"
        return s
    if general:
        return f"SPC shows only general thunderstorms here {join_and(general)}" + (f", none {join_and(none_)}" if none_ else "")
    return f"SPC shows no thunderstorm or severe risk here through {names[-1]}"


def wpc_phrase(w):
    layers = w.snap.get("wpcExcessiveRain")
    if layers is None or "WPC excessive rainfall outlook" in w.errors:
        return ""
    risks = []
    for layer in layers:
        for r in layer.get("atLaPorte") or []:
            outlook = (r.get("outlook") or "").strip()
            if not outlook:
                continue
            try:
                start = datetime.datetime.fromisoformat(r["start_time"]).replace(tzinfo=datetime.timezone.utc).astimezone(TZ)
                end = datetime.datetime.fromisoformat(r["end_time"]).replace(tzinfo=datetime.timezone.utc).astimezone(TZ)
                span = f" from {bs.clock(start)} {bs.day_word(start, w.now)} to {bs.clock(end)} {bs.day_word(end, w.now)}"
            except Exception:
                span = ""
            m = re.match(r"(\w+)\s*\((.*)\)", outlook)
            label = f"{m.group(1).lower()} ({m.group(2).lower()})" if m else outlook.lower()
            risks.append(f"{a_or_an(label)} {label} risk of flooding rain{span}")
    if risks:
        return "WPC puts La Porte in " + join_and(risks[:2])
    last = w.today + datetime.timedelta(days=max(len(layers), 1) - 1)
    return f"WPC shows no flooding-rain risk at La Porte through {WEEKDAYS[last.weekday()]}"


def right_now_pieces(w):
    out = []
    near = nearby_alerts(w)
    if w.alerts:
        for i, a in enumerate(w.alerts):
            s = alert_sentence(a, w.now)
            out.append(Piece(("Right now " + s) if i == 0 else s))
        out.append(Piece("We pass these along as NWS issues them; details and updates are at weather.gov/iwx."))
        if near:
            out.append(Piece(bs.end_sentence("Next door, " + join_and(near))))
    else:
        base = "Right now there are no watches, warnings or advisories for La Porte County"
        if near:
            out.append(Piece(bs.end_sentence(base + "; next door, " + join_and(near))))
        else:
            out.append(Piece(base + " or for Porter and Lake counties next door."))
    risk = [x for x in (spc_phrase(w), wpc_phrase(w)) if x]
    if risk:
        out.append(Piece(bs.end_sentence(", and ".join(risk))))
    return out


# ---------------------------------------------------------------------------------------------
# Title, summary and forecasts
# ---------------------------------------------------------------------------------------------
def today_phrase(w):
    """'sunny near 62', 'early showers, then mostly cloudy near 66', 'showers this afternoon and tonight' for the title."""
    if not w.day:
        return ""
    hi = w.day.get("temperatureF")
    near = f" near {hi}" if hi is not None else ""
    short, c = w.day.get("short"), chance(w.day)
    if c >= 30 and re.search(r"rain|shower|drizzle|thunder", short or "", re.I):
        what = "storms" if re.search(r"thunder", short, re.I) else "showers" if re.search(r"shower", short, re.I) else su.precip(short)
        _, shape = rain_timing(w.workday(w.today), what)
        dry = [p for p in lower_first(friendly(short)).split(", then ") if not re.search(WET, p, re.I)]
        if shape == "early":
            return f"early {what}, then {dry[0] if dry else 'drier'}{near}"
        if shape == "late":
            wet_night = w.night and chance(w.night) >= 50 and re.search(WET, w.night.get("short") or "", re.I)
            return f"{what} this afternoon{' and tonight' if wet_night else ''}{near}"
    return f"{sky(short, c)}{near}"


def next_phrase(w):
    """The next notable thing, for the title: an alert, tonight's rain or frost, or the days ahead."""
    days = [d for d in w.ahead[:HORIZON] if d.high is not None]
    if w.night and chance(w.night) >= 50 and re.search(WET, w.night.get("short") or "", re.I) \
            and "tonight" not in today_phrase(w):
        what = "storms" if re.search(r"thunder", w.night.get("short") or "", re.I) else su.precip(w.night.get("short"))
        return f"{what} likely tonight"
    wet = next((d for d in days[:4] if d.rain >= 30), None)
    if wet:
        what = "storms" if re.search(r"thunder", wet.shorts(), re.I) else su.precip(wet.shorts())
        when = wet.name if chance(wet.day) >= 30 else f"{wet.name} night"
        return f"{what} {'likely' if wet.rain >= 50 else 'possible'} {when}"
    if not days:
        return ""
    phrase = "dry all week" if len(days) >= 5 else f"dry through {days[-1].name}"
    hi_today = (w.day or {}).get("temperatureF")
    peak = max(days[:4], key=lambda d: d.high)
    low_day = min(days[:4], key=lambda d: d.high)
    if hi_today is not None and peak.high - hi_today >= 7:
        phrase += f", highs near {peak.high} by {peak.name}"
    elif hi_today is not None and hi_today - low_day.high >= 7:
        phrase += f", cooler {low_day.name}, near {low_day.high}"
    return phrase


def alert_title(a, now):
    """'Frost Advisory until 8 a.m.', 'Wind Advisory 1 to 10 p.m.', 'Frost Advisory early Sunday'."""
    event = a["event"]
    try:
        onset, end = parse(a.get("onset")), parse(a.get("ends") or a.get("expires"))
    except Exception:
        onset, end = None, None
    if onset and onset > now + datetime.timedelta(minutes=30) and end:
        o, e = onset.astimezone(TZ), end.astimezone(TZ)
        if o.date() > now.date() and e.hour <= 12:
            return f"{event} early {WEEKDAYS[e.weekday()]}"
        if o.date() == e.date() == now.date():
            return f"{event} {bs.clock(o).replace(' a.m.', '').replace(' p.m.', '') if (o.hour < 12) == (e.hour < 12) else bs.clock(o)} to {bs.clock(e)}"
        return f"{event} from {dv.when_word(o, now)}"
    if end and end.astimezone(TZ).date() == now.date():
        return f"{event} until {bs.clock(end)}"
    if end:
        return f"{event} until {WEEKDAYS[end.astimezone(TZ).weekday()]}"
    return event


def make_title(w):
    today = today_phrase(w)
    nxt = next_phrase(w)
    if w.alerts:
        a = w.alerts[0]
        at = alert_title(a, w.now)
        try:
            ends_this_morning = parse(a.get("ends")).astimezone(TZ) <= w.now.replace(hour=12, minute=0)
        except Exception:
            ends_this_morning = False
        if ends_this_morning and today:
            options = [f"{at}, then {today}; {nxt}", f"{at}, then {today}"]
        else:
            options = [f"{upper_first(today)}; {at}, {nxt}" if today else f"{at}; {nxt}", f"{upper_first(today)}; {at}" if today else at]
    else:
        options = [f"{upper_first(today)}; {nxt}" if today else upper_first(nxt), upper_first(today or nxt)]
    for t in options:
        t = upper_first(t.strip("; ,"))
        if len(t) <= 92:
            return t
    return upper_first(options[-1])[:92].rsplit(" ", 1)[0]


def make_summary(w):
    bits = []
    if w.day:
        hi = w.day.get("temperatureF")
        bits.append(f"{upper_first(with_chance(w.day.get('short'), chance(w.day)))} today" + (f", high near {hi}" if hi is not None else ""))
    if w.night:
        lo = w.night.get("temperatureF")
        bits.append(f"{with_chance(w.night.get('short'), chance(w.night))} tonight" + (f", low around {lo}" if lo is not None else ""))
    s = "; ".join(bits) if bits else "The La Porte forecast"
    nxt = next_phrase(w)
    if nxt and "tonight" not in nxt:
        s += f"; then {nxt}"
    if w.alerts:
        a = w.alerts[0]
        s += f". NWS has {a_or_an(a['event'])} {a['event']} for {rb.where_words(a.get('area'))}{alert_span(a, w.now)}"
    else:
        s += ", with no watches, warnings or advisories for La Porte County"
    return bs.end_sentence(s)


def our_forecasts(w):
    """Tomorrow and the day after, for the Track Record: our blend's high and low (NWS's when the blend
    is missing), and NWS's rain chance (the higher of the day and the night after it)."""
    c = w.snap.get("consensus") or {}
    suggested = {s.get("date"): s for s in c.get("suggested") or []}
    out = []
    for i in (1, 2):
        date = w.today + datetime.timedelta(days=i)
        d = next((x for x in w.ahead if x.date == date), None)
        prev = next((x for x in w.ahead if x.date == date - datetime.timedelta(days=1)), None)
        prev_night = w.night if i == 1 else (prev.night if prev else None)
        s = suggested.get(date.isoformat()) or {}
        high = s.get("high") if s.get("high") is not None else (d.high if d else None)
        low = s.get("low") if s.get("low") is not None else (prev_night or {}).get("temperatureF")
        if high is None or low is None:
            continue
        out.append({"date": date.isoformat(), "high": high, "low": low, "rain": d.rain if d else 0})
    return out


def afd_label(issued):
    t = issued.astimezone(EASTERN)
    return f"{t.strftime('%I:%M %p').lstrip('0')} {t.tzname()} {bs.ap_date(t.date().isoformat())}"


# ---------------------------------------------------------------------------------------------
# The post
# ---------------------------------------------------------------------------------------------
def build_post(snap, posts, sc, updates, now):
    """{post, words, notes} for the Scoop this data makes at `now`."""
    notes = []
    w = Weather(snap, now)
    if not w.periods:
        raise ValueError("the NWS forecast has no periods left")
    p1, _ = today_pieces(w, notes)
    p2, _, used_blend = ahead_pieces(w, notes)
    p3, issued = third_pieces(w, updates, sc, notes)
    p4 = right_now_pieces(w)
    paras = [p1, p2, p3, p4]

    def total():
        return sum(words(para(p)) for p in paras)

    # Keep it short for phones: shorten or drop extras, highest rank first, until it fits.
    for rank in (6, 5, 4, 3, 2, 1):
        if total() <= WORD_MAX:
            break
        for pieces in paras:
            for p in pieces:
                if p.rank == rank and p.text:
                    p.text = p.alt or ""
                    notes.append(f"shortened to fit (rank {rank})")
    if total() > WORD_MAX:
        notes.append(f"still {total()} words after trimming (alert information is never cut)")

    body = [para(p) for p in paras if para(p)]
    stamp = now.isoformat()
    sources = [{"label": "NWS forecast for La Porte, IN", "url": FORECAST_URL}]
    if issued:
        sources.append({"label": f"NWS Northern Indiana forecast discussion (we used the {afd_label(issued)} issue; "
                                 f"the link opens the newest one)", "url": AFD_URL})
    if spc_phrase(w):
        sources.append({"label": "Storm Prediction Center convective outlooks", "url": SPC_URL})
    if wpc_phrase(w):
        sources.append({"label": "Weather Prediction Center excessive rainfall outlooks", "url": WPC_URL})
    sources.append({"label": "NWS Northern Indiana current hazards", "url": bs.HAZARDS_URL})
    if used_blend:
        sources.append(dict(OPEN_METEO))
    post = {
        "type": "daily",
        "date": w.today.isoformat(),
        "posted": stamp,
        "updated": stamp,
        "title": make_title(w),
        "summary": make_summary(w),
        "body": body,
        "sources": sources,
        "author": "La Porte Weather Now",
        "forecasts": our_forecasts(w),
        "corrections": [],
    }
    return {"post": post, "words": sum(words(b) for b in body), "notes": sorted(set(notes), key=notes.index)}


# ---------------------------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------------------------
def written_today(data, today):
    p = bs.todays_post(data, today)
    return p if p and not p.get("auto") else None


def fresh_snapshot(now):
    snap = load_json(SNAPSHOT, {})
    try:
        fetched = parse(snap["fetched"])
    except Exception:
        return None, "nws-snapshot.json has no fetch time"
    if fetched.astimezone(TZ).date() != now.date() or now - fetched > SNAPSHOT_MAX:
        return None, f"nws-snapshot.json is from {fetched.astimezone(TZ):%b %d %I:%M %p}, not this morning"
    if not (snap.get("forecast") or {}).get("periods"):
        return None, "the snapshot has no NWS forecast"
    if snap.get("alertsLaPorteCounty") is None:
        return None, "the snapshot couldn't read NWS alerts for La Porte County"
    return snap, ""


def cmd_build(out_path):
    now = bs.now_local()
    today = now.date().isoformat()
    if not (START <= (now.hour, now.minute) < STOP):
        print(f"It's {bs.clock(now)} in La Porte; the Scoop writer only posts between 5:25 a.m. and 2 p.m.")
        return 0
    data = bs.load_posts()
    if written_today(data, today):
        print("Today's Daily Scoop is already up; nothing to do.")
        return 0
    snap, why = fresh_snapshot(now)
    if not snap:
        print(f"No post this time: {why}.")
        return 0
    made = build_post(snap, data, load_json(SCORECARD, {}), load_json(UPDATES, {}), now)
    post = made["post"]
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(post, fh, ensure_ascii=False, indent=2)
    replaces = bool(bs.todays_post(data, today))
    with open(out_path + ".msg", "w", encoding="utf-8") as fh:
        fh.write(f"Add Daily Scoop post ({bs.ap_date(today)})\n\n"
                 f"Written by scripts/scoop_writer.py (fixed rules, no AI) from the NWS snapshot fetched at "
                 f"{bs.clock(parse(snap['fetched']))}.{' Replaces the automatic backup.' if replaces else ''}\n")
    print(f"Scoop ready ({made['words']} words): {post['title']}")
    for n in made["notes"]:
        print(f"  note: {n}")
    return 0


def cmd_insert(post_path):
    with open(post_path, encoding="utf-8") as fh:
        post = json.load(fh)
    for key in ("type", "date", "posted", "title", "body", "forecasts"):
        if not post.get(key):
            print(f"The post has no {key}; not posting it.", file=sys.stderr)
            return 1
    if post.get("auto"):
        print("Refusing to insert a post marked automatic.", file=sys.stderr)
        return 1
    data = bs.load_posts()
    if written_today(data, post["date"]):
        print("A written Daily Scoop for today showed up in the meantime; not posting.")
        return 0
    backup = bs.todays_post(data, post["date"])
    if backup:
        data["posts"].remove(backup)
    data["posts"].insert(0, post)
    bs.save_posts(data)
    print(f"Added the Daily Scoop for {post['date']}{' (replacing the automatic backup)' if backup else ''}.")
    return 0


def cmd_preview(argv):
    ap = argparse.ArgumentParser(prog="scoop_writer.py preview")
    ap.add_argument("--now")
    ap.add_argument("--snapshot", default=SNAPSHOT)
    ap.add_argument("--posts", default=bs.POSTS)
    ap.add_argument("--scorecard", default=SCORECARD)
    ap.add_argument("--updates", default=UPDATES)
    a = ap.parse_args(argv)
    snap = load_json(a.snapshot, {})
    now = parse(a.now).astimezone(TZ) if a.now else bs.now_local()
    made = build_post(snap, load_json(a.posts, {"posts": []}), load_json(a.scorecard, {}), load_json(a.updates, {}), now)
    print(json.dumps(made, ensure_ascii=False, indent=2))
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "build":
        return cmd_build(argv[2])
    if len(argv) >= 3 and argv[1] == "insert":
        return cmd_insert(argv[2])
    if len(argv) >= 2 and argv[1] == "preview":
        return cmd_preview(argv[2:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
