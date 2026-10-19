#!/usr/bin/env python3
"""First snow check (added Oct. 19, 2026; .github/workflows/first-snow.yml). No AI.

Scoop asked on Oct. 19, 2026 to hear as soon as snow first shows up in the forecast for La Porte County,
so Hard Hat Weather's storm records get switched on before the first snowfall.

The Timer starts it at 7:00 AM and 5:00 PM Central, after the National Weather Service's overnight and
afternoon forecasts. Each run reads the NWS 7-day forecast for Michigan City, La Porte and Wanatah, and the
alerts in effect at those three spots. The first time this winter (July-June) that a forecast period mentions
snow, flurries, sleet, freezing rain, freezing drizzle or a wintry mix, or a winter alert is in effect (Winter
Storm, Winter Weather, Lake Effect Snow, Blizzard, Ice Storm ...; not Frost or Freeze), it emails
laporteweathernow@gmail.com once through Brevo, with the NWS's own words. That it went out is kept on the
"first-snow-state" branch, so there's one email per winter.

If Brevo can't send it (no key, an error, or too few free sends left after keeping the morning emails' share),
it opens a GitHub issue instead, which GitHub emails to Scoop. If neither works, the run fails (so GitHub emails
Scoop) and the next run tries again. If the NWS doesn't answer, it waits quietly for the next run; after 4 runs
in a row (2 days) without an answer, the run fails on purpose so GitHub emails Scoop.

    python3 scripts/first_snow.py check     what the Timer does
    python3 scripts/first_snow.py preview   prints what it finds and the email it would send; sends and saves nothing
    python3 scripts/first_snow.py test      emails one "[TEST]" copy to laporteweathernow@gmail.com; saves nothing
"""
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
NWS = os.environ.get("NWS_API", "https://api.weather.gov")
BREVO = os.environ.get("BREVO_API", "https://api.brevo.com/v3")
KEY = os.environ.get("BREVO_API_KEY", "").strip()
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
REPO = os.environ.get("GITHUB_REPOSITORY", "ScoopAndDude/laporteweathernow-posts")
STATE = os.environ.get("FIRST_SNOW_STATE", "first-snow-state.json")
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(os.path.dirname(HERE), "morning-email.json")   # sender name and address, morning list id
OWNER = "laporteweathernow@gmail.com"
UA = "LaPorteWeatherNow-first-snow/1.0 (+https://laporteweathernow.com; laporteweathernow@gmail.com)"
RESERVE_EXTRA = 25          # the same share the warning emails keep back for the morning emails and sign-ups
FAILS_BEFORE_ALARM = 4      # runs in a row with no NWS answer (2 days) before a run fails on purpose
TOWNS = [("Michigan City", 41.7100, -86.8950), ("La Porte", 41.6081, -86.7189), ("Wanatah", 41.4306, -86.8983)]
WINTRY = re.compile(r"\b(snow\w*|flurr\w*|sleet|freezing rain|freezing drizzle|wintry mix|ice pellets)\b", re.I)
WINTER_ALERT = re.compile(r"winter|snow|blizzard|ice storm|freezing rain|freezing drizzle|sleet", re.I)
AP_MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
NEXT_STEP = ("Next step: switch on Hard Hat Weather's storm records before the snow. "
             "Tell Claude \"turn on storm records\" (each live step still needs your OK).")
FACEBOOK = "Also a good one for the Facebook page: the first snow of the season is in the forecast."
FOOTER = ("This comes once per winter from the \"First snow check\" job in the laporteweathernow-posts "
          "repository (scripts/first_snow.py).")


# ---------- reading the NWS ----------
def nws(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/geo+json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read())
        except Exception as e:      # the NWS often answers 500/503 for a moment; try again
            last = e
            if i < tries - 1:
                time.sleep(4 * (i + 1))
    raise RuntimeError(f"{url.split('?')[0]}: {last}")


def read_town(name, lat, lon):
    """The town's forecast periods (7 days) and the alerts in effect there (None if the alerts didn't answer)."""
    pt = nws(f"{NWS}/points/{lat:.4f},{lon:.4f}")["properties"]
    periods = nws(pt["forecast"])["properties"]["periods"]
    try:
        alerts = [a.get("properties") or {} for a in
                  nws(f"{NWS}/alerts/active?point={lat:.4f},{lon:.4f}").get("features") or []]
    except Exception as e:
        print(f"{name}: no answer about alerts ({str(e)[:120]}); going by the forecast alone.")
        alerts = None
    return {"town": name, "lat": lat, "lon": lon, "periods": periods[:14], "alerts": alerts}


def wintry_periods(town):
    hits = []
    for p in town["periods"]:
        short, text = p.get("shortForecast") or "", p.get("detailedForecast") or ""
        if WINTRY.search(short) or WINTRY.search(text):
            hits.append({"town": town["town"], "name": p.get("name") or "", "start": p.get("startTime") or "",
                         "short": short, "text": text,
                         "pop": (p.get("probabilityOfPrecipitation") or {}).get("value")})
    return hits


def winter_alerts(town):
    return [{"town": town["town"], "event": a.get("event") or "", "headline": a.get("headline") or ""}
            for a in town.get("alerts") or [] if WINTER_ALERT.search(a.get("event") or "")]


# ---------- the email ----------
def when(start):
    try:
        return datetime.datetime.fromisoformat(start).astimezone(CENTRAL)
    except (TypeError, ValueError):
        return None


def label(name, start):
    d = when(start)
    return f"{name}, {AP_MONTHS[d.month - 1]} {d.day}" if d else name


def amount(text):
    m = re.search(r"[^.]*\b(?:snow|ice|sleet) accumulation[^.]*\.", text, re.I)
    return m.group(0).strip() if m else ""


def towns_list(names):
    names = list(dict.fromkeys(names))
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def by_period(hits):
    groups = {}
    for h in hits:
        g = groups.setdefault(h["start"], {"start": h["start"], "name": h["name"], "hits": []})
        g["hits"].append(h)
    far = datetime.datetime.max.replace(tzinfo=CENTRAL)
    return sorted(groups.values(), key=lambda g: when(g["start"]) or far)


def period_line(g):
    def words(h):
        pop = f", {h['pop']}%" if h["pop"] is not None else ""
        amt = amount(h["text"])
        return f"{h['short']}{pop}." + (f" {amt}" if amt else "")
    said = {}
    for h in g["hits"]:
        said.setdefault(words(h), []).append(h["town"])
    if len(said) == 1:
        (w, towns), = said.items()
        return f"{label(g['name'], g['start'])}, {towns_list(towns)}: {w}"
    return f"{label(g['name'], g['start'])}: " + " ".join(f"{towns_list(t)}: {w}" for w, t in said.items())


def forecast_links(towns):
    return [(t["town"], f"https://forecast.weather.gov/MapClick.php?lat={t['lat']:.4f}&lon={t['lon']:.4f}")
            for t in towns]


def compose(towns, hits, alerts, test=False):
    """Subject, HTML, plain text and Markdown (for the GitHub issue) of the email."""
    groups = by_period(hits)
    links = forecast_links(towns)
    if groups:
        first = groups[0]
        lead = max(first["hits"], key=lambda h: h["pop"] or 0)
        subject = f"First snow in the forecast for La Porte County: {label(first['name'], first['start'])}"
        opening = ("Snow just showed up in the National Weather Service forecast for La Porte County, "
                   "the first time this winter.")
        first_line = f"First: {label(first['name'], first['start'])} ({towns_list(h['town'] for h in first['hits'])})"
        quote = f"NWS for {lead['town']}: \"{lead['text']}\""
        lines = [period_line(g) for g in groups]
    elif alerts:
        subject = f"Winter alert for La Porte County: {alerts[0]['event']}"
        opening = "The National Weather Service has a winter alert out for La Porte County, the first this winter."
        first_line, quote, lines = "", "", []
    else:   # a test with no snow in the forecast: show the layout with today's first periods
        subject = "First snow in the forecast for La Porte County"
        opening = ("No snow is in the forecast for La Porte County right now. When snow first shows up, an email "
                   "like this one comes once, with the NWS's own words for each snowy period. Today's first "
                   "periods, to show the layout:")
        first_line, quote = "", ""
        sample = [p for t in towns if t["town"] == "La Porte" for p in t["periods"][:3]] or towns[0]["periods"][:3]
        lines = [f"{label(p.get('name') or '', p.get('startTime') or '')}, La Porte: {p.get('shortForecast') or ''}."
                 for p in sample]
    seen = set()
    alert_lines = []
    for a in alerts:
        if a["event"] in seen:
            continue
        seen.add(a["event"])
        alert_lines.append(f"{a['event']} ({towns_list(b['town'] for b in alerts if b['event'] == a['event'])})"
                           + (f": {a['headline']}" if a["headline"] else ""))
    if test:
        subject = "[TEST] " + subject
        banner = ("TEST ONLY, nothing to do: this is what the first-snow email looks like. "
                  + ("Snow IS in the forecast right now, so the real one goes out at the next check."
                     if groups or alerts else "")).strip()
    else:
        banner = ""
    list_title = "Snowy periods in the 7-day forecast:" if groups else ""
    alerts_text = "Winter alerts in effect: " + ("; ".join(alert_lines) if alert_lines else "none") + "."

    # plain text
    t = [banner, "", opening, ""] if banner else [opening, ""]
    if first_line:
        t += [first_line, quote, ""]
    if lines:
        t += ([list_title] if list_title else []) + [f"- {x}" for x in lines] + [""]
    t += [alerts_text, "", NEXT_STEP, "", "Full forecasts: " + "; ".join(f"{n} {u}" for n, u in links), ""]
    if groups or alerts:
        t += [FACEBOOK, ""]
    t += [FOOTER]
    text = "\n".join(t).strip() + "\n"

    # HTML
    e = html.escape
    h = ['<div style="font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.5;color:#1d2433;max-width:620px">']
    if banner:
        h.append(f'<p style="background:#fff4d6;padding:8px 12px;border-radius:6px"><b>{e(banner)}</b></p>')
    h.append(f"<p><b>{e(opening)}</b></p>")
    if first_line:
        h.append(f"<p><b>{e(first_line)}</b><br>{e(quote)}</p>")
    if lines:
        h.append((f"<p style=\"margin-bottom:4px\"><b>{e(list_title)}</b></p>" if list_title else "")
                 + "<ul style=\"margin-top:0\">" + "".join(f"<li>{e(x)}</li>" for x in lines) + "</ul>")
    h.append(f"<p>{e(alerts_text)}</p>")
    h.append(f"<p><b>{e(NEXT_STEP)}</b></p>")
    h.append("<p>Full forecasts: " + " &middot; ".join(f'<a href="{e(u)}">{e(n)}</a>' for n, u in links) + "</p>")
    if groups or alerts:
        h.append(f"<p>{e(FACEBOOK)}</p>")
    h.append(f'<p style="color:#667085;font-size:13px">{e(FOOTER)}</p></div>')
    body_html = "\n".join(h)

    # Markdown for the GitHub issue (the @-mention is what makes GitHub email Scoop)
    m = ["@ScoopAndDude " + opening, ""]
    if first_line:
        m += [f"**{first_line}**", "", "> " + quote, ""]
    if lines:
        m += ([f"**{list_title}**"] if list_title else []) + [f"- {x}" for x in lines] + [""]
    m += [alerts_text, "", f"**{NEXT_STEP}**", "", "Full forecasts: " + " · ".join(f"[{n}]({u})" for n, u in links)]
    return subject, body_html, text, "\n".join(m)


# ---------- sending ----------
def brevo(path, method="GET", body=None):
    req = urllib.request.Request(f"{BREVO}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"api-key": KEY, "accept": "application/json",
                                          "content-type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read()
            return json.loads(b) if b.strip() else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Brevo {method} {path.split('?')[0]}: {e.code} "
                           f"{e.read().decode('utf-8', 'replace')[:200]}") from None


def config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def brevo_room(cfg):
    """Free sends left today after the morning emails' share; None when Brevo doesn't say or it isn't the free plan."""
    left = plan = None
    for p in brevo("/account").get("plan") or []:
        if p.get("creditsType") == "sendLimit":
            left, plan = p.get("credits"), p.get("type")
    if left is None or plan != "free":
        return None
    members = 0
    if cfg.get("listId"):
        try:
            members = int(brevo(f"/contacts/lists/{cfg['listId']}").get("totalSubscribers") or 0)
        except Exception as e:
            print(f"Couldn't read the morning list's size ({str(e)[:100]}).")
    return int(left) - members - RESERVE_EXTRA


def open_issue(title, body):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/issues", method="POST",
                                 data=json.dumps({"title": title, "body": body}).encode(),
                                 headers={"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28",
                                          "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("number")


def deliver(subject, body_html, text, md, issue_ok=True):
    """'email' or 'issue #n' when it went out, None when it couldn't."""
    cfg = config()
    why = ""
    if not KEY:
        why = "no BREVO_API_KEY"
    else:
        try:
            room = brevo_room(cfg)
            if room is not None and room < 1:
                why = "too few Brevo sends left today after keeping the morning emails' share"
            else:
                r = brevo("/smtp/email", "POST", {
                    "sender": {"name": cfg.get("senderName") or "La Porte Weather Now",
                               "email": cfg.get("senderEmail") or "alerts@laporteweathernow.com"},
                    "to": [{"email": OWNER}], "subject": subject, "htmlContent": body_html, "textContent": text,
                    "tags": ["first-snow"]})
                print(f"Emailed {OWNER} (Brevo message {r.get('messageId', '?')}).")
                return "email"
        except Exception as e:
            why = str(e)[:200]
    print(f"Couldn't email ({why}).")
    if not issue_ok:
        return None
    try:
        n = open_issue(subject, md + f"\n\n(This came as an issue because the email didn't go: {why}.)")
        print(f"Opened GitHub issue #{n} instead; GitHub emails it to Scoop.")
        return f"issue #{n}"
    except Exception as e:
        print(f"Couldn't open a GitHub issue either ({str(e)[:200]}).")
        return None


# ---------- state ----------
def notice(msg):
    """Also put the result on the run's page (a GitHub Actions note), so it shows without opening the log."""
    print(msg)
    if os.environ.get("GITHUB_ACTIONS"):
        print("::notice title=First snow check::" + msg.replace("%", "%25").replace("\r", "").replace("\n", "%0A"))


def season(now):
    y = now.year if now.month >= 7 else now.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(st):
    d = os.path.dirname(STATE)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, sort_keys=True)
        f.write("\n")


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "check").strip().lower()
    if mode not in ("check", "preview", "test"):
        print(__doc__)
        return 2
    now = datetime.datetime.now(CENTRAL)
    st = load_state()
    winter = season(now)
    if mode == "check" and st.get("season") == winter and st.get("notified"):
        notice(f"This winter's first-snow email already went out ({st['notified']}, {st.get('via', '?')}).")
        return 0

    towns = []
    for name, lat, lon in TOWNS:
        try:
            towns.append(read_town(name, lat, lon))
        except Exception as e:
            print(f"{name}: no answer from the NWS ({str(e)[:150]}).")
    if not towns:
        if mode != "check":
            return 1
        st["failsInARow"] = int(st.get("failsInARow") or 0) + 1
        save_state(st)
        if st["failsInARow"] >= FAILS_BEFORE_ALARM:
            notice(f"The NWS hasn't answered {st['failsInARow']} runs in a row; failing on purpose so GitHub emails Scoop.")
            return 1
        notice(f"The NWS didn't answer (run {st['failsInARow']} in a row); trying again at the next run.")
        return 0
    if mode == "check" and st.get("failsInARow"):
        st["failsInARow"] = 0
        save_state(st)

    seen = "\n".join(f"{t['town']}: " + " | ".join(f"{p.get('name')}: {p.get('shortForecast')}" for p in t["periods"])
                     for t in towns)
    hits = [h for t in towns for h in wintry_periods(t)]
    alerts = [a for t in towns for a in winter_alerts(t)]
    checked = (f"Checked {now:%b. %-d, %-I:%M %p %Z}: {len(hits)} snowy forecast period(s), "
               f"{len(alerts)} winter alert(s)" + (f"; no answer for {3 - len(towns)} town(s)" if len(towns) < 3 else ""))
    if not hits and not alerts and mode != "test":
        notice(f"No snow in the forecast for La Porte County yet. {checked}.\n{seen}")
        return 0

    subject, body_html, text, md = compose(towns, hits, alerts, test=(mode == "test"))
    if mode == "preview":
        notice(f"{checked}. Would email {OWNER}:\nSubject: {subject}\n\n{text}")
        return 0
    print(f"{checked}.\n{seen}")
    via = deliver(subject, body_html, text, md, issue_ok=(mode == "check"))
    if not via:
        notice(f"Couldn't send \"{subject}\" by email or GitHub issue; failing so GitHub emails Scoop, and the next run "
               "tries again." if mode == "check" else f"Couldn't send the test email \"{subject}\".")
        return 1
    notice(f"Sent \"{subject}\" ({'email to ' + OWNER if via == 'email' else via}).")
    if mode == "check":
        first = by_period(hits)[0] if hits else None
        st.update({"season": winter, "notified": now.isoformat(timespec="minutes"), "via": via, "failsInARow": 0,
                   "first": ({"period": label(first["name"], first["start"]),
                              "towns": [h["town"] for h in first["hits"]], "short": first["hits"][0]["short"]}
                             if first else {"alert": alerts[0]["event"]})})
        save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
