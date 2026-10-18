#!/usr/bin/env python3
"""The 6 AM morning forecast email from La Porte Weather Now, sent with Brevo (added Oct. 17, 2026; nationwide
the same night).

People sign up at laporteweathernow.com/morning-email with any U.S. ZIP code or town (La Porte County towns are
quick picks). The site's sign-up function (Netlify function morning-signup) finds the place in its bundled ZIP
list (GeoNames, CC BY 4.0), asks the National Weather Service for that spot's forecast grid point and time zone,
and asks Brevo to send a confirmation email (double opt-in). Only people who click it join the Brevo list
"Morning Forecast". Their place is kept as Brevo contact attributes: ZIP, LAT, LON, GRIDPOINT, TOWN (the label,
e.g. "Michigan City, IN") and TZ (e.g. "America/Chicago").

The Timer starts this job every tick (15 minutes). Each run looks at every confirmed subscriber whose own local
time is 5:30-6:59 AM and who hasn't had today's email: before 5:58 local the email is scheduled in Brevo for
6:00 local, later it goes right away. Each person gets the Weather Service forecast for their own grid point and
the alerts in force at their spot (fetched once per grid point per run). La Porte County subscribers also get
the school delays and closings posted on /closings.

Each email is sent one by one through Brevo's email API, so every one carries its own one-click unsubscribe
link (and List-Unsubscribe headers). The link is signed, so it only works for that address; the site's function
takes the person off the list. Who already got today's email is kept as keyed hashes (no addresses) on the
"morning-email-state" branch, so a person never gets two in a day.

Brevo's free plan sends 300 emails a day in all (this email, the Thursday weekend email, confirmation emails
together). When a run's sends get near what's left today, the run still sends but fails on purpose so GitHub
emails Scoop (time for a paid Brevo plan). Every email carries the mailing address from morning-email.json.

  python3 scripts/morning_email.py send      (the Timer) send to whoever's 6 AM it is
  python3 scripts/morning_email.py preview   build sample emails into previews/ (and morning-email-preview.html,
                                             La Porte); with TEST_TO_OWNER=1 also send ONE test to
                                             laporteweathernow@gmail.com, for that address's own place
  python3 scripts/morning_email.py warn      (the "Warning email" job, every tick) email each subscriber once when a
                                             NEW Weather Service warning is issued for their own spot
  python3 scripts/morning_email.py setup     find or make the Brevo list, contact attributes and confirmation
                                             email; saves the ids in morning-email.json
Needs the repository secret BREVO_API_KEY (preview without TEST_TO_OWNER doesn't).

Added Oct. 17, 2026 (late), all approved by Scoop:
- A note from Scoop at the top: morning-note.json (see its "about"). Shown only on the date it's dated, in the
  subscriber's own time zone, to "all" subscribers or only "laporte" (La Porte County ZIPs). Nothing is ever
  written in Scoop's name by this script; with no note for today, nothing is shown.
- A sponsor line: sponsor.json "morningEmail". A sponsor shows to La Porte County subscribers (to everyone
  if "everywhere": true), labeled as a sponsor; while it's empty, a small house ad for the $75/month
  sponsor spot. Neither shows while a Warning is in effect at the subscriber's spot.
- A share line (forward, or /morning-email?ref=email) in every email.
- Warning emails (mode warn): a NEW National Weather Service Warning (only events named "... Warning",
  status Actual; watches and advisories don't count) at a subscriber's spot gets them one email right away,
  any hour. One per warning per person (the warning's VTEC event, so updates and extensions aren't resent),
  kept as keyed hashes on the "warning-email-state" branch. On by default; each email has its own "stop
  warning emails" link (Brevo attribute WARN = "no"), separate from the morning email's unsubscribe.
  Budget guard: warnings never use the sends kept back for the next morning emails (one per subscriber plus
  25); when they'd have to, the rest wait and the run fails so GitHub emails Scoop.
"""
import base64
import concurrent.futures
import datetime
import hashlib
import hmac
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(os.path.dirname(HERE), "morning-email.json")
KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO = os.environ.get("BREVO_API", "https://api.brevo.com/v3")
NWS = os.environ.get("NWS_API", "https://api.weather.gov")
HOME_JSON = os.environ.get("HOME_JSON", "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/live/home.json")
CLOSINGS_JSON = os.environ.get("CLOSINGS_JSON", "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/closings/closings.json")
STATE = os.environ.get("MORNING_STATE", "morning-email-state.json")
OWNER = "laporteweathernow@gmail.com"
SITE = "https://laporteweathernow.com"
SIGNUP_API = SITE + "/api/morning-signup"
DAILY_LIMIT = 300
UA = "LaPorteWeatherNow-morning-email/1.0 (+https://laporteweathernow.com/morning-email; laporteweathernow@gmail.com)"
ATTRS = ("ZIP", "LAT", "LON", "GRIDPOINT", "TOWN", "TZ")
LA_PORTE = {"ZIP": "46350", "LAT": "41.6081", "LON": "-86.7189", "TOWN": "La Porte, IN", "TZ": "America/Chicago"}
# La Porte County ZIP codes: these subscribers also get the county's school closings and the /emergency link.
LPC_ZIPS = {"46340", "46345", "46346", "46348", "46350", "46352", "46360", "46361", "46365", "46371", "46382",
            "46390", "46391", "46552"}
# One zone per U.S. offset, only to skip runs when it isn't 5:30-6:59 AM anywhere.
US_ZONES = ("America/New_York", "America/Chicago", "America/Denver", "America/Phoenix", "America/Los_Angeles",
            "America/Anchorage", "America/Adak", "Pacific/Honolulu")
WINDOW = ("05:30", "06:59")
NOTE = os.path.join(os.path.dirname(HERE), "morning-note.json")
SPONSOR = os.path.join(os.path.dirname(HERE), "sponsor.json")
WARN_STATE = os.environ.get("WARN_STATE", "warning-email-state.json")
SHARE_URL = SITE + "/morning-email?ref=email"
RESERVE_EXTRA = 25


def now_central():
    if os.environ.get("MORNING_NOW"):
        t = datetime.datetime.fromisoformat(os.environ["MORNING_NOW"])
        return t.astimezone(CENTRAL) if t.tzinfo else t.replace(tzinfo=CENTRAL)
    return datetime.datetime.now(CENTRAL)


def brevo(path, method="GET", body=None):
    req = urllib.request.Request(f"{BREVO}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"api-key": KEY, "accept": "application/json", "content-type": "application/json",
                                          "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read()
            return json.loads(b) if b.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Brevo {method} {path.split('?')[0]}: {e.code} {detail}") from None


def get_json(url):
    if url.startswith("file://"):
        return json.load(open(url[7:], encoding="utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def nws(url, tries=3):
    if url.startswith("file://"):
        return json.load(open(url[7:], encoding="utf-8"))
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/geo+json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                break
        except Exception as e:      # the Weather Service API has bad minutes; try again
            last = e
        if i + 1 < tries:
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"NWS {url}: {last}")


def esc(t):
    return html.escape(str(t or ""), quote=True)


def load_config():
    return json.load(open(CONFIG, encoding="utf-8"))


def ready(cfg):
    missing = []
    if not cfg.get("enabled"):
        missing.append('"enabled" is false in morning-email.json')
    if not (cfg.get("mailingAddress") or "").strip():
        missing.append("no mailingAddress in morning-email.json")
    if not cfg.get("listId") or not cfg.get("doiTemplateId"):
        missing.append("listId/doiTemplateId not set (run the workflow with mode setup)")
    return missing


# ---------- signed links (the site's function checks the same signatures) ----------
def secret():
    return hashlib.sha256(("lpwn-morning-v1|" + KEY).encode()).digest()


def sign(msg):
    return hmac.new(secret(), msg.encode(), hashlib.sha256).hexdigest()[:32]


def b64(s):
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def unsub_token(email):
    email = email.strip().lower()
    return f"{b64(email)}.{sign('unsub|' + email)}"


def nowarn_token(email):
    email = email.strip().lower()
    return f"{b64(email)}.{sign('nowarn|' + email)}"


def warns_on(contact):
    return str((contact.get("attributes") or {}).get("WARN") or "").strip().lower() != "no"


def sent_key(day, email):
    return sign(f"sent|{day}|{email.strip().lower()}")[:20]


# ---------- places and forecasts ----------
def place_of(contact):
    """The subscriber's place from their Brevo attributes; anyone without one (signed up before Oct. 17's
    nationwide change) is La Porte."""
    a = {k: str((contact.get("attributes") or {}).get(k) or "").strip() for k in ATTRS}
    if not (a["LAT"] and a["LON"]):
        a = dict(LA_PORTE, GRIDPOINT=a.get("GRIDPOINT") or "")
    return a


_TF = None


def tz_at(lat, lon):
    """The time zone at a spot, from the map (timezonefinder, offline). Not the Weather Service's: it gives
    La Porte County, which is on Central time, as America/Indiana/Indianapolis."""
    global _TF
    try:
        if _TF is None:
            from timezonefinder import TimezoneFinder
            _TF = TimezoneFinder()
        return _TF.timezone_at(lat=float(lat), lng=float(lon))
    except Exception:
        return None


def fill_point(a):
    """Add the grid point (the sign-up function asks the Weather Service; if it was down, ask now) and the
    time zone (always from the map here). Returns (place, changed)."""
    if a.get("GRIDPOINT") and a.get("TZ"):
        return a, False
    a = dict(a)
    if not a.get("GRIDPOINT"):
        p = nws(f"{NWS}/points/{float(a['LAT']):.4f},{float(a['LON']):.4f}")["properties"]
        a["GRIDPOINT"] = f"{p['gridId']}/{p['gridX']},{p['gridY']}"
        a["_nwstz"] = p.get("timeZone")
    if not a.get("TZ"):
        a["TZ"] = tz_at(a["LAT"], a["LON"]) or a.get("_nwstz") or "America/Chicago"
    a.pop("_nwstz", None)
    return a, True


def forecast(a, now):
    """{"daily", "alerts", "fetched"} for one grid point; raises if the forecast is missing or out of date."""
    fc = nws(f"{NWS}/gridpoints/{a['GRIDPOINT']}/forecast")["properties"]
    periods = [q for q in fc.get("periods") or [] if datetime.datetime.fromisoformat(q["endTime"]) > now]
    if len(periods) < 4:
        raise RuntimeError("forecast out of date")
    alerts, seen = [], set()
    for f in nws(f"{NWS}/alerts/active?point={float(a['LAT']):.4f},{float(a['LON']):.4f}").get("features") or []:
        p = f.get("properties") or {}
        if p.get("status") != "Actual" or p.get("event") in seen:
            continue
        seen.add(p.get("event"))
        alerts.append({"event": p.get("event"), "ends": p.get("ends"), "expires": p.get("expires")})
    return {"daily": periods, "alerts": alerts, "fetched": fc.get("updateTime") or fc.get("generatedAt")}


def local_county(a):
    return a.get("ZIP") in LPC_ZIPS


# ---------- the email ----------
def pick_periods(daily, today, tz):
    """Today's daytime period and the night after it, from the NWS 12-hour periods."""
    day = night = None
    for i, p in enumerate(daily or []):
        try:
            start = datetime.datetime.fromisoformat(p["startTime"]).astimezone(tz)
        except Exception:
            continue
        if p.get("isDaytime") and start.date() == today:
            day = p
            night = daily[i + 1] if i + 1 < len(daily) else None
            break
    if day is None and daily:
        day = daily[0]
        night = daily[1] if len(daily) > 1 else None
    return day, night


def _local_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def note_html(a, today, note=None):
    """Scoop's own note for today, exactly as he wrote it, or "" (never made up)."""
    try:
        n = note if note is not None else _local_json(NOTE)
        text = str(n.get("text") or "").strip()
        if not text or str(n.get("date") or "").strip() != today.isoformat():
            return ""
        who = str(n.get("for") or "all").strip().lower()
        if who == "laporte" and not local_county(a):
            return ""
        body = "<br>".join(esc(line) for line in text[:1200].splitlines())
        return ('<div style="background:#fff7e6;border-left:4px solid #ff8a00;padding:10px 14px;margin:0 0 16px;font-size:15px;line-height:1.55;color:#1f2a1f;">'
                f'<strong style="display:block;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#a35600;margin-bottom:4px;">A note from Scoop</strong>{body}</div>')
    except Exception:
        return ""


def sponsor_html(a, today, warned, sp=None):
    """Labeled sponsor line, or the house ad for the spot; nothing while a Warning is in effect."""
    try:
        if warned:
            return ""
        sp = sp if sp is not None else _local_json(SPONSOR)
        s = sp.get("morningEmail") if isinstance(sp, dict) else None
        box = 'margin:18px 0 0;padding:10px 14px;border:1px solid #e5e1d5;border-radius:8px;font-size:13px;line-height:1.5;color:#5b665b;'
        if isinstance(s, dict) and s.get("name") and str(s.get("until") or "9999") >= today.isoformat():
            if not (local_county(a) or s.get("everywhere")):
                return ""
            name = esc(s["name"])
            if str(s.get("url") or "").startswith("https://"):
                name = f'<a href="{esc(s["url"])}" style="color:#1a1a1a;font-weight:700;">{name}</a>'
            line = f" &middot; {esc(s['line'])}" if s.get("line") else ""
            return (f'<p style="{box}"><span style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;">Sponsor</span><br>'
                    f'This morning forecast is presented by {name}{line}. Sponsors never see or shape the forecast.</p>')
        return (f'<p style="{box}">Sponsor this morning forecast: $75/month (founding price). '
                f'<a href="{SITE}/media-kit" style="color:#1a1a1a;font-weight:700;">See the sponsor spots</a></p>')
    except Exception:
        return ""


def share_html(kind="morning"):
    what = "the free 6 AM forecast email" if kind == "morning" else "free Weather Service warning emails"
    subj = urllib.parse.quote("A free morning weather email")
    text = urllib.parse.quote("I get a free email with the National Weather Service forecast for my ZIP code every "
                              f"morning at 6, plus warnings. Sign up here: {SHARE_URL}")
    return ('<p style="margin:16px 0 0;font-size:14px;line-height:1.5;color:#1f2a1f;">Know someone who\'d like '
            f'{what}? Forward this email, or <a href="mailto:?subject={subj}&amp;body={text}" style="color:#1a1a1a;font-weight:700;">'
            f'email them the link</a>: <a href="{SHARE_URL}" style="color:#1a1a1a;">laporteweathernow.com/morning-email</a></p>')


def build(wx, closings, cfg, now, a, unsub_url, warn_on=True, note=None, sp=None):
    """Subject, HTML and preview text for one place. now is the subscriber's local time."""
    tz = now.tzinfo
    town = a.get("TOWN") or "La Porte, IN"
    short = town.split(",")[0]
    local = local_county(a)
    today = now.date()
    daily = wx.get("daily") or []
    day, night = pick_periods(daily, today, tz)
    alerts = wx.get("alerts") or []
    headline = ""
    if day:
        headline = f"{day.get('shortForecast', '')}, {'high' if day.get('isDaytime', True) else 'low'} {day.get('temperature')}°"
    names = []
    for al in alerts:
        if al.get("event") and al["event"] not in names:
            names.append(al["event"])
    mon = {5: "May", 6: "June", 7: "July", 9: "Sept."}.get(now.month, now.strftime("%b") + ".")
    subject = (f"{names[0]}: " if names else "") + (headline or "Today's forecast") + f" · {short}, {now:%a}., {mon} {now.day}"
    preview_text = (day or {}).get("detailedForecast", "")[:140]
    nws_page = f"https://forecast.weather.gov/MapClick.php?lat={float(a['LAT']):.4f}&lon={float(a['LON']):.4f}"

    posted = []
    if local and closings and closings.get("date") == today.isoformat():
        for s in closings.get("schools", []):
            t = s.get("today")
            if t and t.get("kind") in ("delay", "closed", "elearning"):
                posted.append((s["name"], t["words"]))

    p = lambda s: f'<p style="margin:0 0 12px;font-size:16px;line-height:1.5;color:#1f2a1f;">{s}</p>'
    h2 = lambda s: f'<h2 style="margin:22px 0 8px;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#a35600;">{s}</h2>'
    parts = [f'<h1 style="margin:0 0 4px;font-family:Georgia,serif;font-size:26px;color:#1a1a1a;">Good morning, {esc(short)}</h1>',
             f'<p style="margin:0 0 18px;font-size:14px;color:#5b665b;">{esc(now.strftime("%A, %B %-d, %Y"))} · {esc(town)}</p>']
    nh = note_html(a, today, note)
    if nh:
        parts.append(nh)
    if alerts:
        rows = []
        for al in alerts:
            until = ""
            try:
                until = " until " + datetime.datetime.fromisoformat(al.get("ends") or al.get("expires")).astimezone(tz).strftime("%a. %-I:%M %p")
            except Exception:
                pass
            rows.append(f"<strong>{esc(al.get('event'))}</strong>{esc(until)}")
        more = (f'<a href="{SITE}/emergency" style="color:#1a1a1a;">What it means and what to do</a>' if local
                else f'<a href="{nws_page}" style="color:#1a1a1a;">The details from the National Weather Service</a>')
        parts.append('<div style="border-left:4px solid #b3261e;background:#fdf1ef;padding:10px 14px;margin:0 0 16px;font-size:15px;line-height:1.5;">'
                     + "<br>".join(rows) + f"<br>{more}</div>")
    if posted:
        parts.append(h2("School delays and closings posted this morning"))
        parts.append(p("<br>".join(f"<strong>{esc(n)}</strong>: {esc(w)}" for n, w in posted)
                       + f'<br><span style="font-size:13px;color:#5b665b;">Always confirm with your school. <a href="{SITE}/closings" style="color:#1a1a1a;">All schools</a></span>'))
    if day:
        parts.append(h2(esc(day.get("name") or "Today")))
        parts.append(p(esc(day.get("detailedForecast") or day.get("shortForecast"))))
    if night:
        parts.append(h2(esc(night.get("name") or "Tonight")))
        parts.append(p(esc(night.get("detailedForecast") or night.get("shortForecast"))))
    ahead, started = [], False
    for q in daily:
        if q is night:
            started = True
            continue
        if started and q.get("isDaytime"):
            ahead.append(f"<strong>{esc(q.get('name'))}</strong>: {esc(q.get('shortForecast'))}, high {esc(q.get('temperature'))}°")
        if len(ahead) == 3:
            break
    if ahead:
        parts.append(h2("The next few days"))
        parts.append(p("<br>".join(ahead)))
    try:
        saved = datetime.datetime.fromisoformat(wx["fetched"]).astimezone(tz).strftime("%-I:%M %p %Z")
    except Exception:
        saved = "this morning"
    btn = "display:inline-block;font-weight:700;text-decoration:none;padding:12px 18px;border-radius:8px;margin:0 8px 8px 0;"
    if local:
        parts.append(f'<p style="margin:18px 0 0;"><a href="{SITE}/" style="{btn}background:#ff8a00;color:#1a1a1a;">Live weather and radar</a></p>')
    else:
        parts.append(f'<p style="margin:18px 0 0;"><a href="{nws_page}" style="{btn}background:#ff8a00;color:#1a1a1a;">Your full forecast</a>'
                     f'<a href="{SITE}/" style="{btn}background:#1a1a1a;color:#ffffff;">La Porte Weather Now</a></p>')
    parts.append(sponsor_html(a, today, any(str(n).endswith("Warning") for n in names), sp))
    parts.append(share_html())
    foot = (f"From the National Weather Service forecast for {esc(town)}, as of {esc(saved)}. Forecasts change; for warnings, "
            f"trust the National Weather Service and local officials. La Porte Weather Now is free, made in La Porte, Indiana, "
            f'and run by Scoop. <a href="{SITE}/" style="color:#5b665b;">laporteweathernow.com</a><br><br>'
            f"You're getting this because you signed up for the morning forecast for {esc(town)} at laporteweathernow.com and "
            f'confirmed your email. <a href="{SITE}/morning-email#change" style="color:#5b665b;">Change your place</a> · '
            f'<a href="{esc(unsub_url)}" style="color:#5b665b;">Unsubscribe</a> anytime, in one click.'
            + (" You also get an email right away when the Weather Service issues a warning for your spot: "
               '<a href="__NOWARN__" style="color:#5b665b;">Stop warning emails</a> (keeps the morning email).' if warn_on else
               f' Warning emails are off; <a href="{SITE}/morning-email#warnings" style="color:#5b665b;">turn them back on</a>.')
            + '<br><br>'
            f"La Porte Weather Now · {esc(cfg.get('mailingAddress') or '[MAILING ADDRESS GOES HERE]')}")
    body = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(subject)}</title></head><body style="margin:0;background:#f4f1e8;">'
            f'<div style="display:none;max-height:0;overflow:hidden;">{esc(preview_text)}</div>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1e8;"><tr><td align="center" style="padding:20px 12px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:12px;">'
            '<tr><td style="background:#1a1a1a;color:#ffffff;padding:14px 22px;border-radius:12px 12px 0 0;font-family:Arial,sans-serif;font-weight:800;letter-spacing:.06em;font-size:13px;">'
            f'<a href="{SITE}/" style="color:#ffffff;text-decoration:none;">LA PORTE WEATHER NOW</a> · MORNING FORECAST</td></tr>'
            '<tr><td style="padding:22px;font-family:Arial,Helvetica,sans-serif;">' + "".join(parts) + '</td></tr>'
            f'<tr><td style="padding:16px 22px 22px;font-family:Arial,sans-serif;font-size:12px;line-height:1.5;color:#5b665b;border-top:1px solid #e5e1d5;">{foot}</td></tr>'
            '</table></td></tr></table></body></html>')
    return subject, body, preview_text


def message(cfg, email, subject, body, preview_text, send_at=None, test=False, kind="morning"):
    unsub = f"{SIGNUP_API}?unsub={unsub_token(email)}"
    nowarn = f"{SIGNUP_API}?nowarn={nowarn_token(email)}"
    # A warning email's one-click unsubscribe stops warning emails only; the morning email's stops the morning email.
    one = nowarn if kind == "warning" else unsub
    m = {"sender": {"name": cfg["senderName"], "email": cfg["senderEmail"]}, "to": [{"email": email}],
         "subject": ("[TEST] " if test else "") + subject,
         "htmlContent": body.replace("__UNSUB__", esc(unsub)).replace("__NOWARN__", esc(nowarn)),
         "headers": {"List-Unsubscribe": f"<{one}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
         "tags": ["warning-email" if kind == "warning" else "morning-forecast"]}
    if send_at:
        m["scheduledAt"] = send_at.isoformat()
    return m


# ---------- Brevo ----------
def sends_left():
    acct = brevo("/account")
    for p in acct.get("plan", []) or []:
        if p.get("creditsType") == "sendLimit":
            return p.get("credits"), p.get("type")
    return None, None


def list_members(list_id):
    got, off = [], 0
    while True:
        page = brevo(f"/contacts/lists/{list_id}/contacts?limit=500&offset={off}").get("contacts", []) or []
        got += page
        if len(page) < 500:
            return got
        off += 500


def save_place(email, a):
    brevo(f"/contacts/{urllib.parse.quote(email)}", "PUT", {"attributes": {k: a.get(k, "") for k in ATTRS}})


def setup(cfg):
    if not KEY:
        print("No BREVO_API_KEY secret yet.")
        return 1
    acct = brevo("/account")
    print("Brevo account OK: " + ", ".join(f"{p.get('type')} ({p.get('credits')} {p.get('creditsType')})" for p in acct.get("plan", [])))
    lists = brevo("/contacts/lists?limit=50&offset=0").get("lists", []) or []
    lst = next((l for l in lists if l.get("name") == cfg["listName"]), None)
    if not lst:
        folders = brevo("/contacts/folders?limit=50&offset=0").get("folders", []) or []
        folder = folders[0]["id"] if folders else brevo("/contacts/folders", "POST", {"name": "La Porte Weather Now"})["id"]
        lst = brevo("/contacts/lists", "POST", {"name": cfg["listName"], "folderId": folder})
        print(f"Made the Brevo list \"{cfg['listName']}\" (id {lst['id']}).")
    else:
        print(f"Found the Brevo list \"{cfg['listName']}\" (id {lst['id']}).")
    cfg["listId"] = lst["id"]
    have = {a.get("name") for a in brevo("/contacts/attributes").get("attributes", []) or [] if a.get("category") == "normal"}
    for name in ATTRS + ("WARN",):
        if name not in have:
            brevo(f"/contacts/attributes/normal/{name}", "POST", {"type": "text"})
            print(f"Made the contact attribute {name}.")
    name = "Morning Forecast: confirm your email"
    temps = brevo("/smtp/templates?templateStatus=true&limit=100&offset=0").get("templates", []) or []
    t = next((x for x in temps if x.get("name") == name), None)
    if not t:
        doi = ('<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:20px;color:#1f2a1f;">'
               '<h1 style="font-family:Georgia,serif;color:#1a1a1a;font-size:24px;">One tap to start your morning forecast</h1>'
               '<p style="font-size:16px;line-height:1.5;">Someone (we hope you!) asked for La Porte Weather Now\'s free 6 AM forecast email '
               'at laporteweathernow.com. Tap the button to confirm. If it wasn\'t you, ignore this email and you won\'t hear from us.</p>'
               '<p><a href="{{ doubleoptin }}" style="display:inline-block;background:#ff8a00;color:#1a1a1a;font-weight:700;'
               'text-decoration:none;padding:12px 18px;border-radius:8px;">Yes, send me the morning forecast</a></p>'
               f'<p style="font-size:12px;color:#5b665b;">La Porte Weather Now · {esc(cfg.get("mailingAddress") or "")}</p></div>')
        t = brevo("/smtp/templates", "POST", {"templateName": name, "subject": "Confirm your La Porte morning forecast email",
                                               "sender": {"name": cfg["senderName"], "email": cfg["senderEmail"]},
                                               "htmlContent": doi, "tag": "optin", "isActive": True})
        print(f"Made the confirmation template (id {t['id']}).")
    else:
        print(f"Found the confirmation template (id {t['id']}).")
    cfg["doiTemplateId"] = t["id"]
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=1, ensure_ascii=False)
        f.write("\n")
    miss = ready(cfg)
    print("Ready to send." if not miss else "Saved. Still needed before anything is sent: " + "; ".join(miss))
    return 0


# ---------- modes ----------
def in_window(local):
    return WINDOW[0] <= local.strftime("%H:%M") <= WINDOW[1]


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"about": "Who already got the morning email, as keyed hashes of day + address (no addresses).", "sent": {}}


def save_state(st, now):
    cut = (now.date() - datetime.timedelta(days=3)).isoformat()
    st["sent"] = {k: d for k, d in st.get("sent", {}).items() if d >= cut}
    st["updated"] = now.isoformat(timespec="seconds")
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=0, sort_keys=True)
        f.write("\n")


def preview(cfg, closings, now):
    os.makedirs("previews", exist_ok=True)
    samples = [dict(LA_PORTE),
               {"ZIP": "60601", "LAT": "41.8858", "LON": "-87.6181", "TOWN": "Chicago, IL", "TZ": ""},
               {"ZIP": "80202", "LAT": "39.7491", "LON": "-104.9946", "TOWN": "Denver, CO", "TZ": ""},
               {"ZIP": "85004", "LAT": "33.4515", "LON": "-112.0686", "TOWN": "Phoenix, AZ", "TZ": ""},
               {"ZIP": "98101", "LAT": "47.6114", "LON": "-122.3305", "TOWN": "Seattle, WA", "TZ": ""}]
    test = os.environ.get("TEST_TO_OWNER") == "1"
    own = None
    if test:
        if not KEY:
            print("No BREVO_API_KEY secret, so no test email.")
            return 1
        try:
            own = place_of(brevo(f"/contacts/{urllib.parse.quote(OWNER)}"))
        except Exception:
            own = dict(LA_PORTE)
        samples = [own] + [s for s in samples if s["ZIP"] != own.get("ZIP")]
    first = None
    for a in samples:
        a, _ = fill_point(a)
        local = now.astimezone(ZoneInfo(a["TZ"]))
        wx = forecast(a, local)
        subject, body, pv = build(wx, closings, cfg, local, a, "__UNSUB__")
        fn = a["TOWN"].split(",")[0].replace(" ", "-").lower()
        open(f"previews/{fn}.html", "w", encoding="utf-8").write(body)
        if a["ZIP"] == "46350":
            open("morning-email-preview.html", "w", encoding="utf-8").write(body)
        print(f"{a['TOWN']} ({a['GRIDPOINT']}, {a['TZ']}, local {local:%-I:%M %p}): {subject}")
        if first is None:
            first = (subject, body, pv, a)
    print("Saved previews/*.html and morning-email-preview.html")
    if test:
        subject, body, pv, a = first
        brevo("/smtp/email", "POST", message(cfg, OWNER, subject, body, pv, test=True))
        print(f"Sent ONE test ({a['TOWN']}) to {OWNER} only.")
    return 0


def send(cfg, closings, now):
    miss = ready(cfg) + ([] if KEY else ["no BREVO_API_KEY secret"])
    if miss:
        print("Morning email isn't set up yet, so nothing was sent: " + "; ".join(miss))
        return 0
    if not any(in_window(now.astimezone(ZoneInfo(z))) for z in US_ZONES):
        print(f"It isn't 5:30-6:59 AM in any U.S. time zone ({now:%-I:%M %p %Z}).")
        return 0
    st = load_state()
    due, c_warn = [], {}
    for c in list_members(cfg["listId"]):
        if c.get("emailBlacklisted"):
            continue
        email = c["email"].strip().lower()
        c_warn[email] = warns_on(c)
        a = place_of(c)
        try:
            a, changed = fill_point(a)
            if changed:
                save_place(email, a)
        except Exception as e:
            print(f"A subscriber's place has no Weather Service grid point ({str(e)[:120]}); skipped.")
            continue
        try:
            local = now.astimezone(ZoneInfo(a["TZ"]))
        except Exception:
            local = now
        if not in_window(local):
            continue
        day = local.date().isoformat()
        if sent_key(day, email) in st["sent"]:
            continue
        due.append((email, a, local, day))
    if not due:
        print(f"Nobody's 6 AM email is due ({now:%-I:%M %p %Z}).")
        save_state(st, now)
        return 0
    left, plan = sends_left()
    rc = 0
    if left is not None and plan == "free" and len(due) > left - 25:
        print(f"WARNING: {len(due)} emails to send now and {left} of Brevo's {DAILY_LIMIT} free daily sends left. "
              "Sending anyway; past the limit Brevo holds or refuses the rest. Time for a paid Brevo plan.")
        rc = 3
    # one forecast per grid point (and spot for alerts) per run
    cache = {}
    def wx_for(a, local):
        k = a["GRIDPOINT"]
        if k not in cache:
            try:
                cache[k] = forecast(a, local)
            except Exception as e:
                cache[k] = e
        return cache[k]
    jobs = []
    for email, a, local, day in due:
        wx = wx_for(a, local)
        if isinstance(wx, Exception):
            print(f"{a['TOWN']}: no fresh forecast ({str(wx)[:120]}); will try again next run.")
            rc = 3 if local.strftime("%H:%M") <= "05:44" else rc
            continue
        send_at = datetime.datetime.combine(local.date(), datetime.time(6, 0), local.tzinfo)
        when = send_at if local < send_at - datetime.timedelta(minutes=2) else None
        subject, body, pv = build(wx, closings, cfg, local, a, "__UNSUB__", warn_on=c_warn.get(email, True))
        jobs.append((email, day, message(cfg, email, subject, body, pv, when), a))

    def go(job):
        email, day, msg, a = job
        try:
            brevo("/smtp/email", "POST", msg)
            return job, None
        except Exception as e:
            return job, e
    ok = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for (email, day, msg, a), err in ex.map(go, jobs):
            if err:
                print(f"{a['TOWN']}: Brevo refused one email ({str(err)[:160]}).")
                rc = 3
                continue
            st["sent"][sent_key(day, email)] = day
            ok += 1
    save_state(st, now)
    places = len({j[3]["GRIDPOINT"] for j in jobs})
    print(f"{ok} of {len(due)} due emails sent or scheduled ({places} forecast areas; {len(cache)} forecasts fetched).")
    return rc


# ---------- warning emails (mode warn) ----------
def warning_key(p):
    """One warning = one VTEC event (office, phenomenon, significance, number, year), so NWS's updates and
    extensions of it aren't new. None for a cancel/expire/upgrade-away message. Falls back to the alert id."""
    for v in (p.get("parameters") or {}).get("VTEC") or []:
        parts = v.strip("/").split(".")
        if len(parts) >= 7:
            action, office, phen, sig, etn = parts[1], parts[2], parts[3], parts[4], parts[5]
            if action in ("CAN", "EXP", "UPG"):
                return None
            year = (p.get("sent") or "")[:4]
            return f"{office}.{phen}.{sig}.{etn}.{year}"
    return p.get("id") or p.get("@id")


def active_warnings(lat, lon, now):
    got = []
    for f in nws(f"{NWS}/alerts/active?point={float(lat):.4f},{float(lon):.4f}").get("features") or []:
        p = f.get("properties") or {}
        if p.get("status") != "Actual" or p.get("messageType") not in ("Alert", "Update"):
            continue
        if not str(p.get("event") or "").endswith("Warning"):
            continue
        try:
            end = datetime.datetime.fromisoformat(p.get("ends") or p.get("expires"))
            if end <= now + datetime.timedelta(minutes=5):
                continue
        except Exception:
            pass
        k = warning_key(p)
        if k:
            got.append((k, p))
    return got


def build_warning(p, cfg, a, now, warn_on=True):
    tz = now.tzinfo
    town = a.get("TOWN") or "La Porte, IN"
    short = town.split(",")[0]
    until = ""
    try:
        until = datetime.datetime.fromisoformat(p.get("ends") or p.get("expires")).astimezone(tz).strftime("%a. %-I:%M %p %Z")
    except Exception:
        pass
    event = str(p.get("event") or "Warning")
    subject = f"{event} for {short}" + (f" until {until}" if until else "")
    nws_page = f"https://forecast.weather.gov/MapClick.php?lat={float(a['LAT']):.4f}&lon={float(a['LON']):.4f}"
    para = lambda t: "".join(f'<p style="margin:0 0 10px;font-size:15px;line-height:1.5;color:#1f2a1f;">{esc(x.strip())}</p>'
                             for x in str(t or "").replace("\r", "").split("\n\n") if x.strip())
    desc = str(p.get("description") or "")
    if len(desc) > 2500:
        desc = desc[:2500].rsplit(" ", 1)[0] + " ..."
    local = local_county(a)
    more = (f'<a href="{SITE}/emergency" style="display:inline-block;font-weight:700;text-decoration:none;padding:12px 18px;border-radius:8px;background:#b3261e;color:#ffffff;margin:0 8px 8px 0;">Live alerts and radar</a>' if local else "") + \
           f'<a href="{nws_page}" style="display:inline-block;font-weight:700;text-decoration:none;padding:12px 18px;border-radius:8px;background:#1a1a1a;color:#ffffff;margin:0 8px 8px 0;">National Weather Service</a>'
    parts = [f'<h1 style="margin:0 0 6px;font-family:Georgia,serif;font-size:24px;color:#b3261e;">{esc(event)}</h1>',
             f'<p style="margin:0 0 14px;font-size:15px;color:#1f2a1f;"><strong>For your spot, {esc(town)}</strong>' + (f", until {esc(until)}" if until else "") + '.</p>',
             f'<div style="border-left:4px solid #b3261e;background:#fdf1ef;padding:10px 14px;margin:0 0 14px;">{para(p.get("headline"))}{para(p.get("instruction"))}</div>',
             para(desc), f'<p style="margin:14px 0 0;">{more}</p>', share_html("warning")]
    foot = (f"Official National Weather Service warning ({esc(p.get('senderName') or 'NWS')}), passed along as issued. Emails can be late; "
            "keep your phone's emergency alerts on and follow local officials. "
            f'<a href="{SITE}/" style="color:#5b665b;">La Porte Weather Now</a> is free, made in La Porte, Indiana, and run by Scoop.<br><br>'
            f"You're getting this because you signed up for the morning forecast for {esc(town)}, which includes warning emails. "
            '<a href="__NOWARN__" style="color:#5b665b;">Stop warning emails</a> (keeps the morning email) · '
            '<a href="__UNSUB__" style="color:#5b665b;">Unsubscribe from everything</a><br><br>'
            f"La Porte Weather Now · {esc(cfg.get('mailingAddress') or '')}")
    body = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(subject)}</title></head><body style="margin:0;background:#f4f1e8;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1e8;"><tr><td align="center" style="padding:20px 12px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:12px;">'
            '<tr><td style="background:#b3261e;color:#ffffff;padding:14px 22px;border-radius:12px 12px 0 0;font-family:Arial,sans-serif;font-weight:800;letter-spacing:.06em;font-size:13px;">'
            'WEATHER SERVICE WARNING · LA PORTE WEATHER NOW</td></tr>'
            '<tr><td style="padding:22px;font-family:Arial,Helvetica,sans-serif;">' + "".join(parts) + '</td></tr>'
            f'<tr><td style="padding:16px 22px 22px;font-family:Arial,sans-serif;font-size:12px;line-height:1.5;color:#5b665b;border-top:1px solid #e5e1d5;">{foot}</td></tr>'
            '</table></td></tr></table></body></html>')
    return subject, body, str(p.get("headline") or "")[:140]


def load_warn_state():
    try:
        st = json.load(open(WARN_STATE, encoding="utf-8"))
        st.setdefault("sent", {})
        return st
    except Exception:
        return None


def save_warn_state(st, now):
    cut = (now - datetime.timedelta(days=10)).isoformat()
    st["sent"] = {k: d for k, d in st.get("sent", {}).items() if d >= cut}
    st["about"] = "Who already got which warning email, as keyed hashes of warning + address (no addresses)."
    st["updated"] = now.isoformat(timespec="seconds")
    with open(WARN_STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=0, sort_keys=True)
        f.write("\n")


def warn_key(k, email):
    return sign(f"warn|{k}|{email.strip().lower()}")[:20]


def warn(cfg, now):
    miss = ready(cfg) + ([] if KEY else ["no BREVO_API_KEY secret"])
    if miss:
        print("Warning emails aren't set up yet: " + "; ".join(miss))
        return 0
    st = load_warn_state()
    boot = st is None
    if boot:
        st = {"sent": {}}
    members = [c for c in list_members(cfg["listId"]) if not c.get("emailBlacklisted")]
    groups = {}
    for c in members:
        if not warns_on(c):
            continue
        a = place_of(c)
        if not a.get("GRIDPOINT"):
            continue        # the morning run fills it in; warnings start once it's known
        groups.setdefault(a["GRIDPOINT"], []).append((c["email"].strip().lower(), a))
    def look(item):
        gp, people = item
        try:
            return gp, active_warnings(people[0][1]["LAT"], people[0][1]["LON"], now), None
        except Exception as e:
            return gp, [], e
    due, failed, queued = [], 0, set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for gp, ws, err in ex.map(look, groups.items()):
            if err:
                failed += 1
                print(f"{gp}: Weather Service alerts didn't answer ({str(err)[:100]}); will check again next run.")
                continue
            for k, p in ws:
                for email, a in groups[gp]:
                    h = warn_key(k, email)
                    if h in st["sent"] or h in queued:
                        continue
                    queued.add(h)
                    if boot:
                        st["sent"][h] = now.isoformat(timespec="seconds")
                        continue
                    due.append((h, email, a, p))
    if boot:
        save_warn_state(st, now)
        print(f"First run: noted {len(st['sent'])} warning(s) already in effect without emailing; new ones from now on.")
        return 0
    if not due:
        save_warn_state(st, now)
        print(f"No new warnings for {sum(len(v) for v in groups.values())} subscriber(s) in {len(groups)} forecast area(s)"
              f" ({now:%-I:%M %p %Z}).")
        return 0
    rc = 0
    try:
        left, plan = sends_left()
    except Exception as e:
        left, plan = None, None
        print(f"Couldn't read Brevo's sends left ({str(e)[:100]}).")
    reserve = len(members) + RESERVE_EXTRA     # kept for the next morning emails and sign-up confirmations
    if left is None:
        room = 20
    elif plan == "free":
        room = max(0, left - reserve)
    else:
        room = len(due)
    # Most dangerous first if not all fit
    order = ("Tornado Warning", "Extreme Wind Warning", "Flash Flood Warning", "Severe Thunderstorm Warning")
    due.sort(key=lambda d: order.index(d[3].get("event")) if d[3].get("event") in order else len(order))
    if len(due) > room:
        print(f"BUDGET: {len(due)} warning emails due but only {room} fit (Brevo: {left} left today, {reserve} kept for "
              "morning emails). The rest wait for the next run. Time for a paid Brevo plan.")
        rc = 3
    elif left is not None and plan == "free" and left - len(due) < reserve + 30:
        print(f"Brevo is getting low: {left} sends left today, {reserve} kept for morning emails.")
        rc = 3
    jobs = []
    for h, email, a, p in due[:room]:
        try:
            # TZ is blank for a moment after a confirmed place change (the morning run fills it in): look it up
            local = now.astimezone(ZoneInfo(a.get("TZ") or tz_at(a["LAT"], a["LON"]) or "America/Chicago"))
        except Exception:
            local = now
        subject, body, pv = build_warning(p, cfg, a, local)
        jobs.append((h, email, a, message(cfg, email, subject, body, pv, kind="warning")))
    def go(job):
        try:
            brevo("/smtp/email", "POST", job[3])
            return job, None
        except Exception as e:
            return job, e
    ok = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for (h, email, a, msg), err in ex.map(go, jobs):
            if err:
                print(f"{a.get('TOWN')}: Brevo refused a warning email ({str(err)[:160]}).")
                rc = 3
                continue
            st["sent"][h] = now.isoformat(timespec="seconds")
            ok += 1
    save_warn_state(st, now)
    print(f"{ok} of {len(due)} warning emails sent ({len({d[3].get('event') for d in due})} kind(s) of warning).")
    return rc


def main(argv):
    mode = argv[1] if len(argv) > 1 else "send"
    cfg = load_config()
    if mode == "setup":
        return setup(cfg)
    now = now_central()
    if mode == "warn":
        return warn(cfg, now)
    try:
        closings = get_json(CLOSINGS_JSON)
    except Exception:
        closings = None
    if mode == "preview":
        return preview(cfg, closings, now)
    return send(cfg, closings, now)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
