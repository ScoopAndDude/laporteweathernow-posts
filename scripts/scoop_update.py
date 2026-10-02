#!/usr/bin/env python3
"""Automatic updates for today's Daily Scoop (added Oct. 2, 2026).

The Daily Scoop is written once each morning. This job, started every 15 minutes by the
Timer, checks the official weather and changes today's post only when something real changes.

A written Scoop gets one short paragraph at the top of its body, starting
"Automatic update, 3:45 p.m.:" (replaced each time, so there's only ever one), when:
  - a watch, warning or advisory for La Porte County starts, changes or ends (right away);
  - NWS changes its forecast for today, tonight or tomorrow by 3 or more degrees, or by 20 or
    more points of rain chance, compared with the forecast the Scoop was written from;
  - the La Porte airport reads 5 or more degrees off NWS's earlier hour-by-hour forecast, or
    reports rain or snow in an hour that forecast gave 20% or less.
Except for alert changes, a written Scoop is updated at most once every 55 minutes. The paragraph
always says what's different from the Scoop below it, so an older update never lingers.

The automatic backup post ("auto": true, NWS's own words, see backup_scoop.py) is rebuilt with
the newest NWS forecast, airport reading and alerts: right away when alerts change, otherwise
at most hourly, when NWS has something newer.

Accuracy rules:
- Only official data, in fixed sentences (no AI): the NWS forecast for La Porte, NWS alerts for
  La Porte County and the La Porte airport (KPPO).
- "posted" and "forecasts" (what the Track Record grades) never change; "updated" shows the time
  of the newest change. Corrections stay as they are.
- If NWS's forecast or any of its alert lists don't answer, nothing changes this round. Airport
  readings more than 2 hours old are left out.
- An alert's end time is NWS's own "ends" (when the hazard ends; a message's "expires" isn't one).
  An alert that drops off NWS's list before its end time is kept for one more check, because
  NWS's list sometimes skips an alert while it's being updated; still gone 15 minutes later (or
  canceled), it has ended.
- "The forecast the Scoop was written from" is nws-snapshot.json when it's from today and older
  than the post; otherwise NWS's forecast at this job's first check after the post went up.
  It's kept in scoop-updates.json, with what was last published and today's list of updates.

  python3 scripts/scoop_update.py fetch DATA.json     save the newest NWS data (nothing if NWS fails)
  python3 scripts/scoop_update.py apply DATA.json     update scoop-posts.json and scoop-updates.json;
                                                      the commit message goes in DATA.json.msg
  python3 scripts/scoop_update.py preview DATA.json   print what apply would do; changes nothing
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backup_scoop as bs  # noqa: E402  (post helpers, house style, the backup post itself)
import nws_snapshot as ns  # noqa: E402  (NWS requests)

REPO = os.path.join(HERE, "..")
STATE = os.path.join(REPO, "scoop-updates.json")
SNAPSHOT = os.path.join(REPO, "nws-snapshot.json")
TZ = bs.TZ
PREFIX = "Automatic update, "
TEMP_STEP, RAIN_STEP = 3, 20                  # what counts as a forecast change
OFF_BY = 5                                    # airport vs. the earlier hour-by-hour forecast, degrees
QUIET = datetime.timedelta(minutes=55)        # least time between updates, except alert changes
OBS_MAX_AGE = datetime.timedelta(hours=2)
DATA_MAX_AGE = datetime.timedelta(minutes=20)
AHEAD = datetime.timedelta(hours=12)          # the rain-timing sentence looks this far ahead
ENDS_SLACK = datetime.timedelta(minutes=5)    # leaving NWS's list this close to its end time = it ran out
WET = re.compile(r"rain|shower|drizzle|thunder|snow|sleet|ice pellets|freezing", re.I)
ALERT_FIELDS = ("id", "event", "area", "onset", "ends", "expires", "sent", "messageType")
LOG_KEEP = 40
ABOUT = ("State for scripts/scoop_update.py, the automatic updates to today's Daily Scoop: the forecast "
         "the Scoop was written from (baseline), what was last published, the alerts last seen, and "
         "today's updates. Replaced each day. Safe to delete: the job starts over from the current post.")


# ---------- Small helpers ----------

def parse(s):
    return datetime.datetime.fromisoformat(s) if s else None


def wall_clock():
    return bs.now_local()


def chance(pct):
    """Rain chances as NWS words them: rounded to the nearest 10%, under 20% counts as none."""
    return bs.nws_chance(pct) or 0


def precip(*shorts):
    text = " ".join(s or "" for s in shorts)
    wet = re.search(r"rain|shower|drizzle|thunder|storm", text, re.I)
    white = re.search(r"snow|flurr|sleet|freezing|ice", text, re.I)
    return "rain or snow" if wet and white else "snow" if white else "rain"


def join_and(parts):
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


# ---------- NWS data ----------

def hourly(pt):
    d = ns.get_json(pt["forecast"] + "/hourly")["properties"]
    return [{"start": x.get("startTime"), "temperatureF": x.get("temperature"),
             "rainChancePercent": (x.get("probabilityOfPrecipitation") or {}).get("value") or 0,
             "short": x.get("shortForecast")} for x in (d.get("periods") or [])[:36]]


def cmd_fetch(out_path):
    now = wall_clock()
    try:
        pt = ns.point()
        fc = ns.forecast(pt)
        if len(fc.get("periods") or []) < 2:
            raise RuntimeError("no forecast periods")
    except Exception as e:
        print(f"NWS's forecast didn't answer ({str(e)[:200]}), so nothing changes this round.")
        return 0
    notes = []
    try:
        before = len(ns.errors)
        alerts = ns.county_alerts()
        failed = [x for x in ns.errors[before:] if str(x.get("source", "")).startswith("alerts ")]
        if failed:   # a list that didn't answer could make a live alert look ended
            raise RuntimeError("; ".join(x["error"][:120] for x in failed))
    except Exception as e:
        alerts = None
        notes.append(f"alerts didn't all answer ({str(e)[:200]})")
    try:
        obs = ns.observation()
    except Exception as e:
        obs = None
        notes.append(f"no airport reading ({str(e)[:150]})")
    try:
        hours = hourly(pt)
    except Exception as e:
        hours = None
        notes.append(f"no hour-by-hour forecast ({str(e)[:150]})")
    data = {"fetched": now.isoformat(), "forecast": fc, "alerts": alerts, "observation": obs, "hourly": hours}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print(f"NWS data saved at {bs.clock(now)}: {len(fc['periods'])} forecast periods, "
          f"{'alerts unknown' if alerts is None else str(len(alerts)) + ' alert(s)'}"
          f"{'; ' + '; '.join(notes) if notes else ''}.")
    return 0


# ---------- Alerts ----------

def alert_where(a):
    area = a.get("area") or ""
    north, south = "Northern La Porte" in area, "Southern La Porte" in area
    return ("northern La Porte County" if north and not south
            else "southern La Porte County" if south and not north else "La Porte County")


def alert_sent(a):
    try:
        return parse(a.get("sent")).timestamp()
    except Exception:
        return 0.0


def is_cancel(a):
    return (a.get("messageType") or "").lower() == "cancel"


def live_alerts(alerts):
    """Active alerts, one per kind and area: when NWS has updated an alert, the newest message wins."""
    best = {}
    for a in alerts or []:
        if not a or not a.get("event") or is_cancel(a):
            continue
        pair = (a["event"], alert_where(a))
        if pair not in best or alert_sent(a) >= alert_sent(best[pair]):
            best[pair] = a
    return [best[k] for k in sorted(best)]


def slim_alerts(alerts):
    return [{k: a.get(k) for k in ALERT_FIELDS} for a in live_alerts(alerts)]


def alert_key(a):
    try:
        end = parse(a["ends"]).astimezone(TZ).strftime("%Y-%m-%d %H:%M") if a.get("ends") else "no set end"
    except Exception:
        end = str(a.get("ends"))
    return f"{a['event']} | {alert_where(a)} | {end}"


def alert_list(alerts):
    """[{key, event, where}], one per alert, for comparing and for "has ended" sentences."""
    return [{"key": alert_key(a), "event": a["event"], "where": alert_where(a)} for a in live_alerts(alerts)]


def steady_alerts(now_rows, known_rows, missing_before, now):
    """NWS's alert list sometimes skips an alert for a few minutes while it's being updated. An alert
    we knew about that's missing before its end time is kept for one more check; missing again (or
    canceled, or past its end time), it has ended. Returns (alerts to use, [event, where] kept once)."""
    now_rows = list(now_rows or [])
    present = {(a["event"], alert_where(a)) for a in live_alerts(now_rows)}
    canceled = {(a.get("event"), alert_where(a)) for a in now_rows if a and is_cancel(a)}
    held, missing = [], []
    for a in live_alerts(known_rows):
        pair = (a["event"], alert_where(a))
        if pair in present or pair in canceled:
            continue
        try:
            end = parse(a.get("ends"))
        except Exception:
            end = None
        if end and now >= end - ENDS_SLACK:
            continue                          # it ran out on time
        if list(pair) in missing_before:
            continue                          # still gone 15 minutes later: NWS ended it early
        held.append(a)
        missing.append(list(pair))
    return now_rows + held, missing


def alert_sentence(a, now):
    event = a["event"]
    article = "an" if event[:1].upper() in "AEIOU" else "a"
    span = ""
    try:
        onset, end = parse(a.get("onset")), parse(a.get("ends"))
        if onset and onset > now + datetime.timedelta(minutes=30):
            span += f" from {bs.clock(onset)} {bs.day_word(onset, now)}"
        if end:
            span += f" until {bs.clock(end)} {bs.day_word(end, now)}"
    except Exception:
        pass
    return f"NWS has {article} {event} for {alert_where(a)}{span}."


# ---------- Forecast comparison ----------

def period_key(p):
    """"day 2026-10-02", or "night 2026-10-02" for the night that starts that evening. NWS's periods
    run 6 to 6 Eastern (5 to 5 Central), so a night is filed under the day before the morning it
    ends: an early-morning "Overnight" is last night, not tonight."""
    if p.get("isDaytime"):
        return f"day {parse(p['start']).astimezone(TZ).date().isoformat()}"
    end = parse(p["end"]).astimezone(TZ)
    return f"night {(end.date() - datetime.timedelta(days=1)).isoformat()}"


def period_values(periods):
    """{"day 2026-10-02" / "night 2026-10-02": {name, temp, rain, short}} from NWS forecast periods."""
    out = {}
    for p in periods or []:
        try:
            k = period_key(p)
        except Exception:
            continue
        if k not in out:
            out[k] = {"name": p.get("name"), "temp": p.get("temperatureF"),
                      "rain": chance(p.get("rainChancePercent")), "short": p.get("short")}
    return out


def hourly_values(hours):
    out = {}
    for h in hours or []:
        try:
            t = parse(h["start"]).astimezone(TZ)
        except Exception:
            continue
        out[t.strftime("%Y-%m-%dT%H")] = {"temp": h.get("temperatureF"), "rain": h.get("rainChancePercent") or 0}
    return out


def forecast_changes(base, cur, today):
    tomorrow = (datetime.date.fromisoformat(today) + datetime.timedelta(days=1)).isoformat()
    out = []
    for k in (f"day {today}", f"night {today}", f"day {tomorrow}"):
        b, c = base.get(k), cur.get(k)
        if not b or not c:
            continue
        common = {"k": k, "was": b.get("name"), "now": c.get("name"), "shortWas": b.get("short"), "shortNow": c.get("short")}
        if b.get("temp") is not None and c.get("temp") is not None and abs(c["temp"] - b["temp"]) >= TEMP_STEP:
            out.append(dict(common, field="temp", **{"from": b["temp"], "to": c["temp"]}))
        if abs((c.get("rain") or 0) - (b.get("rain") or 0)) >= RAIN_STEP:
            out.append(dict(common, field="rain", **{"from": b.get("rain") or 0, "to": c.get("rain") or 0}))
    return out


def changes_differ(new, old, live):
    """True when the forecast differences changed since the last update. Differences for periods
    that are over (today, after 5 p.m.) are dropped first: a day ending isn't a forecast change."""
    a = {(c["k"], c["field"]): c["to"] for c in new}
    b = {(c["k"], c["field"]): c["to"] for c in old or [] if c["k"] in live}
    if set(a) != set(b):
        return True
    return any(abs(v - b[key]) >= (TEMP_STEP if key[1] == "temp" else RAIN_STEP) for key, v in a.items())


def change_phrase(ch, today):
    kind, date = ch["k"].split(" ")
    label = ("tonight" if kind == "night" else "today" if date == today
             else bs.WEEKDAYS[datetime.date.fromisoformat(date).weekday()])
    up = ch["to"] > ch["from"]
    if ch["field"] == "temp":
        word = "high" if kind == "day" else "low"
        return f"{'raised' if up else 'lowered'} its {word} for {label} to {ch['to']} (from {ch['from']})"
    scope = ""
    now_name = (ch.get("now") or "").lower()
    if (kind == "day" and date == today and now_name != (ch.get("was") or "").lower()
            and now_name.startswith(("this ", "late ", "rest of"))):
        label, scope = now_name, " for the whole day"          # e.g. "this afternoon"
    if ch["from"] == 0:
        return f"added a {ch['to']}% chance of {precip(ch.get('shortNow'))} for {label}"
    if ch["to"] == 0:
        return f"taken the {precip(ch.get('shortWas'))} out of its forecast for {label} (it had {ch['from']}%{scope})"
    return (f"{'raised' if up else 'lowered'} its chance of {precip(ch.get('shortNow'), ch.get('shortWas'))} "
            f"for {label} to {ch['to']}% (from {ch['from']}%{scope})")


# ---------- Airport and the hours ahead ----------

def airport(obs, base_hours, now):
    """(sentence, kinds) for the newest airport reading; kinds can hold "warm", "cool", "wet"."""
    if not obs or obs.get("temperatureF") is None:
        return "", []
    try:
        t = parse(obs.get("time")).astimezone(TZ)
    except Exception:
        return "", []
    if now - t > OBS_MAX_AGE:
        return "", []
    weather = (obs.get("weather") or "").strip().lower()
    temp = obs["temperatureF"]
    reading = f"at {bs.clock(t)} the La Porte airport reported {weather + ' and ' if weather else ''}{temp} degrees"
    nearest = (t + datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H")
    f = (base_hours or {}).get(nearest)
    kinds = []
    if f and f.get("temp") is not None:
        if temp - f["temp"] >= OFF_BY:
            kinds.append("warm")
        elif f["temp"] - temp >= OFF_BY:
            kinds.append("cool")
    if f and WET.search(weather) and "vicinity" not in weather and (f.get("rain") or 0) <= 20:
        kinds.append("wet")
    if "warm" in kinds or "cool" in kinds:
        s = (f"It's running {'warmer' if 'warm' in kinds else 'cooler'} than NWS's earlier hour-by-hour forecast: "
             f"{reading}, where that forecast had about {f['temp']}.")
    else:
        s = bs.end_sentence(reading[0].upper() + reading[1:])
    if "wet" in kinds:
        p = f.get("rain") or 0
        s += (f" NWS's earlier hour-by-hour forecast gave that hour {'no' if p == 0 else f'only a {p}%'} "
              f"chance of {precip(weather)}.")
    return s, kinds


def rain_ahead(hours, now):
    rows = []
    for h in hours or []:
        try:
            t = parse(h["start"]).astimezone(TZ)
        except Exception:
            continue
        if now - datetime.timedelta(hours=1) < t < now + AHEAD:
            rows.append((t, h.get("rainChancePercent") or 0, h.get("short")))
    blocks = []
    for t, p, short in rows:
        kind = "likely" if p >= 50 else "possible" if p >= 30 else None
        if not kind:
            continue
        if blocks and blocks[-1]["kind"] == kind and blocks[-1]["end"] == t:
            b = blocks[-1]
            b["end"], b["max"] = t + datetime.timedelta(hours=1), max(b["max"], p)
            b["shorts"].append(short)
        else:
            blocks.append({"kind": kind, "start": t, "end": t + datetime.timedelta(hours=1), "max": p, "shorts": [short]})
    if not blocks:
        return ""
    parts = [f"{precip(*b['shorts'])} {b['kind']} from {bs.clock(b['start'])} to {bs.clock(b['end'])} (up to {b['max']}%)"
             for b in blocks]
    return f"Over the next 12 hours, NWS's hour-by-hour forecast has {join_and(parts)}."


def held_note(missing):
    return (" Kept for one more check (it left NWS's list before its end time): "
            + "; ".join(f"{e} for {w}" for e, w in missing) + ".") if missing else ""


def logged(state, now, why):
    state["updates"] = ((state.get("updates") or []) + [{"time": now.isoformat(), "why": why}])[-LOG_KEEP:]


# ---------- Written Scoop ----------

def baseline(post, data, now):
    """The forecast the Scoop was written from: the morning snapshot when it fits, else NWS now."""
    snap = load_json(SNAPSHOT, {})
    try:
        fetched, posted = parse(snap.get("fetched")), parse(post.get("posted"))
        fits = (fetched.astimezone(TZ).date().isoformat() == post["date"] and posted is not None and fetched <= posted
                and len((snap.get("forecast") or {}).get("periods") or []) >= 2)
    except Exception:
        fits = False
    hours = hourly_values(data.get("hourly"))
    hours_from = data["fetched"] if data.get("hourly") else None
    if fits:
        alerts = snap.get("alertsLaPorteCounty")
        rows = slim_alerts(alerts if alerts is not None else data["alerts"])
        return {"from": snap["fetched"], "source": "nws-snapshot.json (what the Scoop was written from)",
                "periods": period_values(snap["forecast"]["periods"]), "alerts": alert_list(rows),
                "alertRows": rows, "hourly": hours, "hourlyFrom": hours_from}
    rows = slim_alerts(data["alerts"])
    return {"from": data["fetched"], "source": "NWS at this job's first check after the Scoop went up",
            "periods": period_values(data["forecast"]["periods"]), "alerts": alert_list(rows),
            "alertRows": rows, "hourly": hours, "hourlyFrom": hours_from}


def plan_written(post, data, state, now):
    today = post["date"]
    started = not (state.get("date") == today and state.get("post") == post.get("posted") and state.get("kind") == "written")
    if started:
        base = baseline(post, data, now)
        state = {"about": ABOUT, "date": today, "post": post.get("posted"), "kind": "written",
                 "baseline": base, "published": None, "alertRows": base["alertRows"], "missing": [], "updates": []}
    base = state["baseline"]
    if not base.get("hourly") and data.get("hourly"):          # the first check had no hour-by-hour forecast
        base["hourly"], base["hourlyFrom"] = hourly_values(data["hourly"]), data["fetched"]
        started = True
    missing_before = state.get("missing") or []
    rows, missing = steady_alerts(data["alerts"], state.get("alertRows") or [], missing_before, now)
    keep_notes = started or missing != missing_before
    pub = state.get("published") or {}

    cur = alert_list(rows)
    cur_keys = [a["key"] for a in cur]
    prev_keys = pub.get("alertKeys") if pub else [a["key"] for a in base["alerts"]]
    alerts_changed = cur_keys != prev_keys
    cur_pairs = {(a["event"], a["where"]) for a in cur}
    ended, seen = [], set()
    for a in base["alerts"] + (pub.get("alerts") or []):     # in the Scoop or an earlier update, gone now
        pair = (a["event"], a["where"])
        if pair not in cur_pairs and pair not in seen:
            seen.add(pair)
            ended.append(a)

    cur_periods = period_values(data["forecast"]["periods"])
    changes = forecast_changes(base["periods"], cur_periods, today)
    forecast_changed = changes_differ(changes, pub.get("changes"), set(cur_periods))
    reading, kinds = airport(data.get("observation"), base.get("hourly"), now)
    new_kinds = sorted(set(kinds) - set(pub.get("off") or []))

    why = []
    if alerts_changed:
        why.append("alerts changed (" + ("; ".join(cur_keys) or "none now") + ")")
    if forecast_changed:
        why.append("NWS forecast " + ("; ".join(f"{c['k']} {c['field']} {c['from']}->{c['to']}" for c in changes)
                                       or "back in line with the Scoop"))
    if new_kinds:
        why.append("airport running " + " and ".join(new_kinds))
    waiting = None
    if not why:
        waiting = "Nothing new for today's Scoop."
    elif not alerts_changed and pub.get("time") and now - parse(pub["time"]) < QUIET:
        waiting = f"Waiting: {'; '.join(why)}, but the last update was at {bs.clock(parse(pub['time']))}."
    if waiting:
        if not keep_notes:
            return None, None, waiting + held_note(missing)
        state["alertRows"], state["missing"] = slim_alerts(rows), missing
        return state, None, waiting + held_note(missing) + (" Saved the forecast the Scoop was written from." if started else "")

    s = [alert_sentence(a, now) for a in live_alerts(rows)]
    if s:
        s.append("We pass these along as NWS issues them; details are at weather.gov/iwx.")
    s += [f"The {a['event']} for {a['where']} has ended." for a in ended]
    if changes:
        s.append("Since the Scoop below was written, NWS has " + join_and([change_phrase(c, today) for c in changes]) + ".")
    elif any(c["k"] in cur_periods for c in pub.get("changes") or []):
        s.append("NWS's forecast is back in line with the Scoop below.")
    if reading:
        s.append(reading)
    ahead = rain_ahead(data.get("hourly"), now)
    if ahead:
        s.append(ahead)
    if not cur:
        s.append("There are no watches, warnings, or advisories for La Porte County right now.")
    paragraph = f"{PREFIX}{bs.clock(now)}: " + " ".join(s)

    new_post = dict(post)
    new_post["body"] = [paragraph] + [p for p in post.get("body") or [] if not str(p).startswith(PREFIX)]
    new_post["updated"] = now.isoformat()
    state["published"] = {"time": now.isoformat(), "alertKeys": cur_keys, "alerts": cur, "changes": changes,
                          "off": sorted(kinds), "paragraph": paragraph}
    state["alertRows"], state["missing"] = slim_alerts(rows), missing
    logged(state, now, "; ".join(why))
    return state, new_post, "Updated today's Scoop: " + "; ".join(why) + "." + held_note(missing)


# ---------- Automatic backup ----------

def plan_backup(post, data, state, now):
    today = post["date"]
    if not (state.get("date") == today and state.get("post") == post.get("posted") and state.get("kind") == "backup"):
        state = {"about": ABOUT, "date": today, "post": post.get("posted"), "kind": "backup",
                 "published": {"time": post.get("updated") or post.get("posted"), "alertKeys": None,
                               "obsTime": None, "forecastUpdated": None},
                 "alertRows": [], "missing": [], "updates": []}
    missing_before = state.get("missing") or []
    rows, missing = steady_alerts(data["alerts"], state.get("alertRows") or [], missing_before, now)
    pub = state["published"]
    cur_keys = [a["key"] for a in alert_list(rows)]
    alerts_changed = bool(cur_keys) if pub.get("alertKeys") is None else cur_keys != pub["alertKeys"]
    obs = data.get("observation") or {}
    obs_time, fc_updated = obs.get("time"), (data.get("forecast") or {}).get("updated")
    newer = bool((obs_time and obs_time != pub.get("obsTime")) or (fc_updated and fc_updated != pub.get("forecastUpdated")))
    due = now - parse(pub["time"]) >= QUIET
    if not (alerts_changed or (due and newer)):
        msg = ("Backup is current." if not newer else
               f"Backup waits for its hourly refresh (last at {bs.clock(parse(pub['time']))}).") + held_note(missing)
        if missing == missing_before:
            return None, None, msg
        state["alertRows"], state["missing"] = slim_alerts(rows), missing
        return state, None, msg

    bdata = {"source": "nws", "fetched": now, "forecast": data["forecast"], "alerts": rows, "observation": obs}
    if len(bs.current_periods(bdata, now)) < 2:
        return None, None, "NWS's forecast had too few current periods; backup left as it is."
    built = bs.build_post(bdata, now)
    posted = parse(post.get("posted")) or now
    built["posted"] = post.get("posted") or now.isoformat()
    built["updated"] = now.isoformat()
    built["summary"] = bs.end_sentence(f"The Daily Scoop is running late, so here is the official NWS forecast for La Porte, "
                                       f"posted automatically at {bs.clock(posted)} and refreshed at {bs.clock(now)}")
    built["body"][0] = built["body"][0].replace(
        "This is an automatic update.", f"This is an automatic update, refreshed through the day (latest at {bs.clock(now)}).", 1)
    built["corrections"] = post.get("corrections") or []
    new_post = {k: built.get(k, post.get(k)) for k in post}
    new_post.update({k: v for k, v in built.items() if k not in new_post})
    why = "alerts changed" if alerts_changed else "hourly refresh"
    state["published"] = {"time": now.isoformat(), "alertKeys": cur_keys, "obsTime": obs_time, "forecastUpdated": fc_updated}
    state["alertRows"], state["missing"] = slim_alerts(rows), missing
    logged(state, now, why)
    return state, new_post, f"Refreshed the automatic backup ({why})." + held_note(missing)


# ---------- Commands ----------

def plan(data):
    """(posts file or None, state or None, message, commit message or None)."""
    now = parse(data["fetched"]).astimezone(TZ)
    if wall_clock() - now > DATA_MAX_AGE:
        return None, None, f"The NWS data is from {bs.clock(now)}, too old to use.", None
    if data.get("alerts") is None:
        return None, None, "NWS alerts couldn't all be checked, so nothing changes this round.", None
    if len((data.get("forecast") or {}).get("periods") or []) < 2:
        return None, None, "NWS's forecast had no periods, so nothing changes this round.", None
    today = now.date().isoformat()
    posts = bs.load_posts()
    post = bs.todays_post(posts, today)
    if not post:
        return None, None, "No Daily Scoop for today yet; nothing to update.", None
    state = load_json(STATE, {})
    planner = plan_backup if post.get("auto") else plan_written
    new_state, new_post, message = planner(post, data, state, now)
    if new_post is None and new_state is None:
        return None, None, message, None
    if new_post is not None:
        i = posts["posts"].index(post)
        posts["posts"][i] = new_post
        commit = (f"Automatic Scoop update ({bs.ap_date(today)}, {bs.clock(now)})\n\n{message}\n"
                  f"Written by scripts/scoop_update.py from NWS data fetched at {bs.clock(now)}.\n")
    else:
        posts = None
        commit = f"Automatic Scoop updates: notes ({bs.ap_date(today)}, {bs.clock(now)})\n\n{message}\n"
    return posts, new_state, message, commit


def cmd_apply(data_path, write=True):
    data = load_json(data_path, None)
    if not data:
        print("No NWS data this round (NWS didn't answer), so nothing changes.")
        return 0
    posts, state, message, commit = plan(data)
    print(message)
    if not write:
        if posts:
            post = bs.todays_post(posts, parse(data["fetched"]).astimezone(TZ).date().isoformat())
            print(json.dumps({"title": post["title"], "summary": post["summary"], "updated": post["updated"],
                              "body": post["body"]}, ensure_ascii=False, indent=2))
        if state:
            print(json.dumps(state, ensure_ascii=False, indent=1)[:4000])
        return 0
    if posts:
        bs.save_posts(posts)
    if state:
        with open(STATE, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    if commit:
        with open(data_path + ".msg", "w", encoding="utf-8") as fh:
            fh.write(commit)
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "fetch":
        return cmd_fetch(argv[2])
    if len(argv) >= 3 and argv[1] == "apply":
        return cmd_apply(argv[2])
    if len(argv) >= 3 and argv[1] == "preview":
        return cmd_apply(argv[2], write=False)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
