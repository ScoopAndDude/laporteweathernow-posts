#!/usr/bin/env python3
"""Second opinions for the Daily Scoop and Hard Hat Weather (added Oct. 2, 2026).

Used by nws_snapshot.py. Three things, all from free public data:

1. consensus(): the NWS forecast for La Porte next to four computer models from
   Open-Meteo (free, no key; open-meteo.com, CC BY 4.0): the National Blend of Models
   (NBM), the short-range HRRR (first ~2 days only), the American GFS and the European
   ECMWF. For each day the "blend" is the MIDDLE value (median) of NWS and the models,
   so one wild model can't drag it. When the scorecard has 14+ graded days, the blend
   is also nudged by our own past average error at the La Porte airport ("adjusted"),
   capped at 3 degrees. "suggested" is what the Daily Scoop's forecasts should use.
   Rain chances stay NWS's own: model rain chances are rougher than NWS's.

2. workday_rain(): the NWS hour-by-hour rain chances for today's and tomorrow's work
   hours (6 a.m. to 6 p.m. Central), summed up in plain words, e.g.
   "dry until 1 p.m.; rain likely 1-5 p.m. (up to 70%)".

3. morning_record(): what NWS and the blend said for TODAY at about 5 a.m., the time
   Hard Hat Weather makes its calls. Saved once per day to morning-log.json and never
   changed afterward, so scorecard.py can grade the same-morning forecast honestly.
"""
import datetime
import json
import os
import statistics
import urllib.parse
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
HERE = os.path.dirname(os.path.abspath(__file__))
SCORECARD = os.path.join(HERE, "..", "scorecard.json")
MORNING_LOG = os.path.join(HERE, "..", "morning-log.json")

MODELS = [  # Open-Meteo model id, plain name
    ("ncep_nbm_conus", "National Blend of Models (NBM)"),
    ("ncep_hrrr_conus", "HRRR (short range)"),
    ("gfs_seamless", "American GFS"),
    ("ecmwf_ifs025", "European ECMWF"),
]
BIAS_MIN_DAYS = 14
BIAS_CAP = 3.0
WORK_START, WORK_END = 6, 18          # 6 a.m. to 6 p.m. Central
MORNING_FROM, MORNING_TO = 4, 7       # the morning record is the first snapshot between 4 and 7 a.m.


def _local_date(iso):
    return datetime.datetime.fromisoformat(iso).astimezone(CENTRAL).date().isoformat()


def nws_days(periods):
    """{date: {high, low, rain}} using the Daily Scoop's rules: high = that day's daytime
    high; low = the overnight low ending that morning; rain = the higher chance of that
    day and the night after it."""
    out = {}
    for p in periods or []:
        if not p.get("start"):
            continue
        d = _local_date(p["start"])
        if p.get("isDaytime"):
            row = out.setdefault(d, {})
            row["high"] = p.get("temperatureF")
            row["rainDay"] = p.get("rainChancePercent") or 0
        else:
            nxt = (datetime.date.fromisoformat(d) + datetime.timedelta(days=1)).isoformat()
            out.setdefault(nxt, {})["low"] = p.get("temperatureF")
            out.setdefault(d, {})["rainNight"] = p.get("rainChancePercent") or 0
    for d, row in out.items():
        if "rainDay" in row or "rainNight" in row:
            row["rain"] = max(row.pop("rainDay", 0), row.pop("rainNight", 0))
    return out


def fetch_models(get_json):
    q = urllib.parse.urlencode({
        "latitude": 41.6081, "longitude": -86.7189,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "models": ",".join(m for m, _ in MODELS),
        "temperature_unit": "fahrenheit", "timezone": "America/Chicago", "forecast_days": 4,
    })
    d = get_json(f"https://api.open-meteo.com/v1/forecast?{q}", accept="application/json")
    daily = d.get("daily") or {}
    dates = daily.get("time") or []
    out = {}
    for mid, _ in MODELS:
        def col(var):
            return daily.get(f"{var}_{mid}") or (daily.get(var) if len(MODELS) == 1 else None) or []
        hi, lo, pr = col("temperature_2m_max"), col("temperature_2m_min"), col("precipitation_probability_max")
        for i, date in enumerate(dates):
            row = {}
            if i < len(hi) and hi[i] is not None:
                row["high"] = round(hi[i])
            if i < len(lo) and lo[i] is not None:
                row["low"] = round(lo[i])
            if i < len(pr) and pr[i] is not None:
                row["rain"] = round(pr[i])
            if row:
                out.setdefault(date, {})[mid] = row
    if not out:
        raise RuntimeError("Open-Meteo answered with no model data")
    return out


def load_bias():
    try:
        b = (json.load(open(SCORECARD, encoding="utf-8")) or {}).get("bias") or {}
    except Exception:
        return {"ready": False, "note": "no scorecard yet"}
    return b


def _adjust(value, bias_value, ready):
    if value is None or not ready or bias_value is None:
        return value
    nudge = max(-BIAS_CAP, min(BIAS_CAP, bias_value))
    return round(value - nudge)


def consensus(periods, get_json):
    nws = nws_days(periods)
    models = fetch_models(get_json)
    bias = load_bias()
    ready = bool(bias.get("ready"))
    days, suggested = [], []
    today = datetime.datetime.now(CENTRAL).date()
    for i in range(0, 4):
        date = (today + datetime.timedelta(days=i)).isoformat()
        n, m = nws.get(date, {}), models.get(date, {})
        if not n and not m:
            continue
        row = {"date": date, "nws": {k: n.get(k) for k in ("high", "low", "rain")},
               "models": {mid: m[mid] for mid, _ in MODELS if mid in m}}
        blend, adjusted, spread = {}, {}, {}
        for k in ("high", "low"):
            vals = [v for v in [n.get(k)] + [x.get(k) for x in row["models"].values()] if v is not None]
            if vals:
                blend[k] = round(statistics.median(vals))
                spread[k] = max(vals) - min(vals)
                adjusted[k] = _adjust(blend[k], bias.get(k), ready)
        row.update(blend=blend, adjusted=adjusted, spread=spread)
        notes = []
        for k, word in (("high", "high"), ("low", "low")):
            if n.get(k) is not None and adjusted.get(k) is not None and abs(adjusted[k] - n[k]) >= 3:
                notes.append(f"our blend's {word} ({adjusted[k]}) differs from NWS ({n[k]}) by {abs(adjusted[k] - n[k])} degrees")
            if spread.get(k, 0) >= 6:
                notes.append(f"the models disagree on the {word} by {spread[k]} degrees (less certain)")
        row["note"] = "; ".join(notes) or "NWS and the models agree within a few degrees"
        days.append(row)
        if i in (1, 2):
            suggested.append({"date": date, "high": adjusted.get("high", n.get("high")),
                              "low": adjusted.get("low", n.get("low")), "rain": n.get("rain")})
    return {
        "about": ("NWS next to four computer models (Open-Meteo, CC BY 4.0). blend = the middle value of NWS and "
                  "the models; adjusted = blend corrected by our own average past error at the La Porte airport "
                  f"once {BIAS_MIN_DAYS}+ days are graded (capped at {BIAS_CAP:g} degrees). Rain chances are NWS's. "
                  "suggested = what the Daily Scoop's forecasts use (tomorrow and the day after)."),
        "models": {mid: name for mid, name in MODELS},
        "bias": bias,
        "days": days,
        "suggested": suggested,
    }


def _hour_label(h):
    return f"{(h % 12) or 12} {'a.m.' if h < 12 else 'p.m.'}"


def _summarize_hours(hours):
    """hours: [(hour, pop)] for one day's work hours -> plain-words summary."""
    def kind(p):
        return "likely" if p >= 50 else "possible" if p >= 30 else "dry"
    blocks = []
    for h, p in hours:
        k = kind(p)
        if blocks and blocks[-1]["kind"] == k and blocks[-1]["end"] == h:
            blocks[-1]["end"] = h + 1
            blocks[-1]["max"] = max(blocks[-1]["max"], p)
        else:
            blocks.append({"kind": k, "start": h, "end": h + 1, "max": p})
    if all(b["kind"] == "dry" for b in blocks):
        return "dry through work hours (6 a.m. to 6 p.m.)"
    parts = []
    for b in blocks:
        span = f"{_hour_label(b['start'])}-{_hour_label(b['end'])}"
        if b["kind"] == "dry":
            parts.append(f"mostly dry {span}")
        else:
            parts.append(f"rain {b['kind']} {span} (up to {b['max']}%)")
    return "; ".join(parts)


def workday_rain(pt, get_json):
    url = (pt or {}).get("forecast")
    if not url:
        raise RuntimeError("no NWS forecast link")
    d = get_json(url + "/hourly")["properties"]
    today = datetime.datetime.now(CENTRAL).date()
    by_day = {}
    for x in d.get("periods") or []:
        t = datetime.datetime.fromisoformat(x["startTime"]).astimezone(CENTRAL)
        if WORK_START <= t.hour < WORK_END and (t.date() - today).days in (0, 1):
            pop = (x.get("probabilityOfPrecipitation") or {}).get("value") or 0
            by_day.setdefault(t.date().isoformat(), []).append((t.hour, int(pop)))
    out = []
    for date in sorted(by_day):
        hours = sorted(by_day[date])
        out.append({"date": date, "summary": _summarize_hours(hours),
                    "hours": [{"hour": h, "rainChancePercent": p} for h, p in hours]})
    return {"about": "NWS hour-by-hour rain chances for work hours, 6 a.m. to 6 p.m. Central (30-49% = possible, 50%+ = likely).",
            "days": out}


def morning_record(started_utc, periods, cons):
    """Adds today's ~5 a.m. forecast to morning-log.json once (never rewrites a day)."""
    now = started_utc.astimezone(CENTRAL)
    if not (MORNING_FROM <= now.hour < MORNING_TO):
        return None
    today = now.date().isoformat()
    try:
        log = json.load(open(MORNING_LOG, encoding="utf-8"))
    except Exception:
        log = {"about": "", "days": []}
    if any(r.get("date") == today for r in log.get("days", [])):
        return None
    n = nws_days(periods).get(today, {})
    if n.get("high") is None:
        return None
    blend = next((r for r in (cons or {}).get("days", []) if r["date"] == today), None)
    row = {"date": today, "saved": now.replace(microsecond=0).isoformat(),
           "nws": {"high": n.get("high"), "rain": n.get("rain")},
           "blend": {"high": (blend or {}).get("adjusted", {}).get("high")} if blend else None}
    log["about"] = ("What NWS (and, from Oct. 2, 2026, our model blend) said for the SAME day at about 5 a.m., "
                    "when Hard Hat Weather makes its calls. One entry per day, saved once and never changed. "
                    "Graded in scorecard.json under \"morning\". Made by scripts/consensus.py.")
    log["days"] = ([row] + log.get("days", []))[:400]
    with open(MORNING_LOG, "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return row
