#!/usr/bin/env python3
"""Backup Daily Scoop for laporteweathernow.com.

If there's no Daily Scoop for today by 6:30 AM Central, this posts a short automatic update
with the official NWS forecast for La Porte, clearly marked as automatic, so the homepage and
the Scoop page never show yesterday's post as the newest. The morning Scoop task replaces it
when its write-up comes in later.

  python3 scripts/backup_scoop.py build OUT.json    fetch NWS and write the post to OUT.json
                                                    (and its commit message to OUT.json.msg);
                                                    writes nothing when no backup is needed
  python3 scripts/backup_scoop.py insert OUT.json   add that post to scoop-posts.json, unless
                                                    today's Scoop showed up in the meantime
  python3 scripts/backup_scoop.py preview           print the post it would write right now
                                                    ({"source", "post"}), ignoring the clock and
                                                    today's post; posts nothing

Rules:
- It only posts between 6:30 AM and 2 PM Central. The job starts several times each morning,
  because GitHub's clock is loose and Central time shifts an hour in November.
- Fresh NWS data first; if NWS doesn't answer, nws-snapshot.json when it's under 6 hours old.
  With neither, nothing is posted, and the daily site check emails Scoop that today's Scoop
  is missing.
- Clock times in the NWS wording are already in Central time (see nws_snapshot.text_in_zone).
- "forecasts" stays empty, so the Track Record never grades NWS's numbers as ours.
- "auto": true marks the post for the morning Scoop task (which replaces it) and the site check.
"""
import datetime
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nws_snapshot as ns  # noqa: E402

REPO = os.path.join(HERE, "..")
POSTS = os.path.join(REPO, "scoop-posts.json")
SNAPSHOT = os.path.join(REPO, "nws-snapshot.json")
TZ = ZoneInfo("America/Chicago")
START = (6, 30)    # the Scoop is on time until 6:30 AM Central
STOP = (14, 0)     # after 2 PM a backup isn't worth posting
SNAPSHOT_MAX_HOURS = 6
FORECAST_URL = "https://forecast.weather.gov/MapClick.php?lat=41.6081&lon=-86.7189"
HAZARDS_URL = "https://www.weather.gov/iwx/"
AP_MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
NWS_TIME = re.compile(r"\b(1[0-2]|[1-9])(?::([0-5]\d))?\s?(am|pm)\b(\.?)", re.I)


def now_local():
    return datetime.datetime.now(TZ).replace(second=0, microsecond=0)


def load_posts():
    with open(POSTS, encoding="utf-8") as fh:
        return json.load(fh)


def save_posts(data):
    with open(POSTS, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def todays_post(data, today):
    return next((p for p in data.get("posts") or []
                 if p.get("type", "daily") == "daily" and p.get("date") == today), None)


def ap_date(ymd):
    d = datetime.date.fromisoformat(ymd)
    return f"{AP_MONTHS[d.month - 1]} {d.day}"


def clock(dt):
    """6:35 a.m., 2 p.m., noon, midnight (Central)."""
    dt = dt.astimezone(TZ)
    if dt.minute == 0 and dt.hour in (0, 12):
        return "midnight" if dt.hour == 0 else "noon"
    mins = f":{dt.minute:02d}" if dt.minute else ""
    return f"{dt.hour % 12 or 12}{mins} {'a.m.' if dt.hour < 12 else 'p.m.'}"


def day_word(dt, now):
    days = (dt.astimezone(TZ).date() - now.date()).days
    if days == 0:
        return "today"
    return WEEKDAYS[dt.astimezone(TZ).weekday()] if 0 < days < 7 else ap_date(dt.astimezone(TZ).date().isoformat())


def house_style(text):
    """NWS "before 4pm." becomes "before 4 p.m." (the site's style)."""
    def fix(m):
        h, mm, ap, dot = m.groups()
        return f"{h}{':' + mm if mm else ''} {'a.m.' if ap.lower() == 'am' else 'p.m.'}"
    return NWS_TIME.sub(fix, text or "").strip()


def end_sentence(s):
    """Adds the period, unless the sentence already ends in one (as "a.m." does)."""
    s = s.rstrip()
    return s if s.endswith(".") else s + "."


def nws_chance(pct):
    """NWS's wording rounds chances to the nearest 10% and leaves out anything under 20%."""
    if pct is None:
        return None
    r = int(float(pct) / 10 + 0.5) * 10
    return r if r >= 20 else None


def sentence_case(s):
    s = (s or "").strip()
    return s[:1].upper() + s[1:].lower() if s else s


def precip_word(short):
    wet = re.search(r"rain|shower|drizzle|thunder|storm", short or "", re.I)
    white = re.search(r"snow|flurr|sleet|freezing|ice", short or "", re.I)
    return "rain" if wet and not white else "snow" if white and not wet else "rain or snow"


def temp_words(p):
    t = p.get("temperatureF")
    if t is None:
        return ""
    return f"high near {t}" if p.get("isDaytime") else f"low around {t}"


# ---------- Weather ----------

def fresh_data(now):
    pt = ns.point()
    fc = ns.forecast(pt)
    try:
        alerts = ns.county_alerts()
    except Exception:
        alerts = None
    try:
        obs = ns.observation()
    except Exception:
        obs = None
    return {"source": "nws", "fetched": now, "forecast": fc, "alerts": alerts, "observation": obs}


def snapshot_data(now):
    try:
        with open(SNAPSHOT, encoding="utf-8") as fh:
            s = json.load(fh)
        fetched = datetime.datetime.fromisoformat(s["fetched"])
    except Exception:
        return None
    if now - fetched > datetime.timedelta(hours=SNAPSHOT_MAX_HOURS) or not (s.get("forecast") or {}).get("periods"):
        return None
    return {"source": "snapshot", "fetched": fetched, "forecast": s["forecast"],
            "alerts": s.get("alertsLaPorteCounty"), "observation": s.get("observation")}


def get_data(now):
    try:
        data = fresh_data(now)
        if len(current_periods(data, now)) >= 2:
            return data
        print("NWS answered without a usable forecast; trying the saved snapshot.", file=sys.stderr)
    except Exception as e:
        print(f"NWS didn't answer ({str(e)[:200]}); trying the saved snapshot.", file=sys.stderr)
    data = snapshot_data(now)
    if data and len(current_periods(data, now)) >= 2:
        return data
    return None


def current_periods(data, now):
    out = []
    for p in (data.get("forecast") or {}).get("periods") or []:
        try:
            if datetime.datetime.fromisoformat(p["end"]) > now:
                out.append(p)
        except Exception:
            continue
    return out


# ---------- The post ----------

def alert_sentences(data, now):
    alerts = data.get("alerts")
    as_of = clock(data["fetched"])
    if alerts is None:
        return ("We couldn't check NWS alerts just now; see NWS Northern Indiana at weather.gov/iwx "
                "for any watches, warnings, or advisories.")
    rows = [a for a in alerts if a and a.get("event") and (a.get("messageType") or "").lower() != "cancel"]
    if not rows:
        return f"Right now there are no watches, warnings, or advisories for La Porte County (checked at {as_of})."
    out = []
    for a in rows:
        event = a["event"]
        article = "an" if event[:1].upper() in "AEIOU" else "a"
        area = a.get("area") or ""
        north, south = "Northern La Porte" in area, "Southern La Porte" in area
        where = ("northern La Porte County" if north and not south
                 else "southern La Porte County" if south and not north else "La Porte County")
        span = ""
        try:
            onset = datetime.datetime.fromisoformat(a["onset"]) if a.get("onset") else None
            end_s = a.get("ends") or a.get("expires")
            end = datetime.datetime.fromisoformat(end_s) if end_s else None
            if onset and onset > now + datetime.timedelta(minutes=30):
                span += f" from {clock(onset)} {day_word(onset, now)}"
            if end:
                span += f" until {clock(end)} {day_word(end, now)}"
        except Exception:
            pass
        out.append(f"NWS has {article} {event} for {where}{span}.")
    return (f"Right now (checked at {as_of}): " + " ".join(out) +
            " We pass these along as NWS issues them; details and updates are at weather.gov/iwx.")


def build_post(data, now):
    periods = current_periods(data, now)
    first, second = periods[0], periods[1]
    later = periods[2:8]
    today = now.date().isoformat()
    first_short = sentence_case(house_style(first.get("short")))
    if len(first_short) > 60:
        first_short = first_short[:57].rsplit(" ", 1)[0] + "…"
    title = f"Automatic NWS update: {first_short}" + (f", {temp_words(first)}" if temp_words(first) else "")

    source_words = ("the official National Weather Service forecast for La Porte" if data["source"] == "nws"
                    else f"the official National Weather Service forecast for La Porte as of {clock(data['fetched'])}")
    intro = (f"This is an automatic update. The Daily Scoop didn't post by 6:30 a.m., so here is {source_words}, "
             "in NWS's own words. If Scoop's write-up comes in later today, it will replace this.")

    near = " ".join(end_sentence(f"{p['name']}: {house_style(p.get('detailed') or p.get('short'))}") for p in (first, second))
    obs = data.get("observation") or {}
    try:
        obs_time = datetime.datetime.fromisoformat(obs["time"]) if obs.get("time") else None
    except Exception:
        obs_time = None
    if obs_time and obs.get("temperatureF") is not None and now - obs_time < datetime.timedelta(hours=2):
        weather = (obs.get("weather") or "").strip().lower()
        near += end_sentence(f" At {clock(obs_time)} the La Porte airport reported "
                             f"{weather + ' and ' if weather else ''}{obs['temperatureF']} degrees")
    updated = (data.get("forecast") or {}).get("updated")
    try:
        if updated:
            near += end_sentence(f" NWS last updated this forecast at {clock(datetime.datetime.fromisoformat(updated))}")
    except Exception:
        pass

    bits = []
    for p in later:
        line = f"{p['name']}: {sentence_case(house_style(p.get('short')))}"
        if temp_words(p):
            line += f", {temp_words(p)}"
        chance = nws_chance(p.get("rainChancePercent"))
        if chance:
            line += f", {chance}% chance of {precip_word(p.get('short'))}"
        bits.append(end_sentence(line))
    ahead = "The next few days, from the same NWS forecast: " + " ".join(bits) if bits else ""

    summary = end_sentence(f"The Daily Scoop is running late, so here is the official NWS forecast for La Porte, "
                           f"posted automatically at {clock(now)}")
    stamp = now.isoformat()
    return {
        "type": "daily",
        "date": today,
        "posted": stamp,
        "updated": stamp,
        "title": title,
        "summary": summary,
        "body": [x for x in (intro, near, ahead, alert_sentences(data, now)) if x],
        "sources": [
            {"label": "NWS forecast for La Porte, IN", "url": FORECAST_URL},
            {"label": "NWS Northern Indiana current hazards", "url": HAZARDS_URL},
        ],
        "author": "La Porte Weather Now",
        "forecasts": [],
        "corrections": [],
        "auto": True,
    }


# ---------- Commands ----------

def cmd_build(out_path):
    now = now_local()
    today = now.date().isoformat()
    if not (START <= (now.hour, now.minute) < STOP):
        print(f"It's {clock(now)} in La Porte; the backup only posts between 6:30 a.m. and 2 p.m.")
        return 0
    if todays_post(load_posts(), today):
        print("Today's Daily Scoop is already up; nothing to do.")
        return 0
    data = get_data(now)
    if not data:
        # No email from this job: the daily site check reports the missing Scoop once.
        print("No fresh NWS forecast and no recent snapshot, so no backup post this time.")
        return 0
    post = build_post(data, now)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(post, fh, ensure_ascii=False, indent=2)
    with open(out_path + ".msg", "w", encoding="utf-8") as fh:
        fh.write(f"Automatic backup Scoop ({ap_date(today)})\n\nThe morning Scoop wasn't up by 6:30 a.m. Central, "
                 f"so this posts the NWS forecast ({'fresh from NWS' if data['source'] == 'nws' else 'from the saved snapshot'}).\n")
    print(f"Backup post ready ({data['source']}): {post['title']}")
    return 0


def cmd_insert(post_path):
    with open(post_path, encoding="utf-8") as fh:
        post = json.load(fh)
    for key in ("type", "date", "posted", "title", "body"):
        if not post.get(key):
            print(f"The backup post has no {key}; not posting it.", file=sys.stderr)
            return 1
    data = load_posts()
    if todays_post(data, post["date"]):
        print("Today's Daily Scoop showed up in the meantime; not posting the backup.")
        return 0
    data["posts"].insert(0, post)
    save_posts(data)
    print(f"Added the backup post for {post['date']}.")
    return 0


def cmd_preview():
    now = now_local()
    data = get_data(now)
    if not data:
        print("No fresh NWS forecast and no recent snapshot.", file=sys.stderr)
        return 1
    print(json.dumps({"source": data["source"], "post": build_post(data, now)}, ensure_ascii=False, indent=2))
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "build":
        return cmd_build(argv[2])
    if len(argv) >= 3 and argv[1] == "insert":
        return cmd_insert(argv[2])
    if len(argv) >= 2 and argv[1] == "preview":
        return cmd_preview()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
