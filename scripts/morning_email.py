#!/usr/bin/env python3
"""The 6 AM morning forecast email for La Porte, sent with Brevo (added Oct. 17, 2026).

People sign up at laporteweathernow.com/morning-email. The site's sign-up function (Netlify function
morning-signup) asks Brevo to send them a confirmation email first (double opt-in); only people who click
it join the Brevo list "Morning Forecast". This is a separate list from the Thursday "Weekend Outlook".

Every morning the Timer starts this job at 5:30-6:44 AM Central. At 5:30-5:59 it builds today's email
from the site's 15-minute copy of the National Weather Service forecast for La Porte (home.json on the
"live" branch), any alerts, and any school delays or closings posted on /closings, and schedules it in
Brevo for 6:00 AM. If the first start comes after 6:00 (GitHub ran late), it sends right away, until
6:44; after that it skips the day. It never sends twice in a day (it looks for today's campaign first).

Brevo adds the unsubscribe link ({{ unsubscribe }} below) and keeps unsubscribed people off every later
send. Every email carries the mailing address from morning-email.json; without one it doesn't send.

Brevo's free plan sends 300 emails a day in all (this email, the Thursday weekend email, welcome and
confirmation emails together). If the list gets close to that, the run fails on purpose so GitHub emails
Scoop.

  python3 scripts/morning_email.py send      (the Timer) schedule or send today's email if it's time
  python3 scripts/morning_email.py preview   build today's email into morning-email-preview.html; with
                                             TEST_TO_OWNER=1, also send it to laporteweathernow@gmail.com only
  python3 scripts/morning_email.py setup     find or create the Brevo list and confirmation template and
                                             save their ids in morning-email.json
Needs the repository secret BREVO_API_KEY (preview without TEST_TO_OWNER doesn't).
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(os.path.dirname(HERE), "morning-email.json")
KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO = os.environ.get("BREVO_API", "https://api.brevo.com/v3")
HOME_JSON = os.environ.get("HOME_JSON", "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/live/home.json")
CLOSINGS_JSON = os.environ.get("CLOSINGS_JSON", "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/closings/closings.json")
OWNER = "laporteweathernow@gmail.com"
SITE = "https://laporteweathernow.com"
DAILY_LIMIT = 300


def now_central():
    if os.environ.get("MORNING_NOW"):
        t = datetime.datetime.fromisoformat(os.environ["MORNING_NOW"])
        return t.astimezone(CENTRAL) if t.tzinfo else t.replace(tzinfo=CENTRAL)
    return datetime.datetime.now(CENTRAL)


def brevo(path, method="GET", body=None):
    req = urllib.request.Request(f"{BREVO}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"api-key": KEY, "accept": "application/json", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read()
            return json.loads(b) if b.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Brevo {method} {path}: {e.code} {detail}") from None


def get_json(url):
    if url.startswith("file://"):
        return json.load(open(url[7:], encoding="utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": "laporteweathernow-morning-email", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


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


# ---------- the email ----------
def pick_periods(daily, today):
    """Today's daytime period and the night after it, from the NWS 12-hour periods."""
    day = night = None
    for i, p in enumerate(daily or []):
        try:
            start = datetime.datetime.fromisoformat(p["startTime"]).astimezone(CENTRAL)
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


def build(home, closings, cfg, now):
    today = now.date()
    daily = home.get("daily") or []
    day, night = pick_periods(daily, today)
    alerts = home.get("alerts") or []
    headline = ""
    if day:
        headline = f"{day.get('shortForecast', '')}, high {day.get('temperature')}°"
    alert_names = []
    for a in alerts:
        ev = a.get("event")
        if ev and ev not in alert_names:
            alert_names.append(ev)
    mon = {5: "May", 6: "June", 7: "July", 9: "Sept."}.get(now.month, now.strftime("%b") + ".")
    subject = (f"{alert_names[0]}: " if alert_names else "") + (headline or "Today's forecast") + f" · La Porte, {now:%a}., {mon} {now.day}"
    preview_text = (day or {}).get("detailedForecast", "")[:140]

    posted = []
    if closings and closings.get("date") == today.isoformat():
        for s in closings.get("schools", []):
            t = s.get("today")
            if t and t.get("kind") in ("delay", "closed", "elearning"):
                posted.append((s["name"], t["words"]))

    p = lambda s: f'<p style="margin:0 0 12px;font-size:16px;line-height:1.5;color:#1f2a1f;">{s}</p>'
    h2 = lambda s: f'<h2 style="margin:22px 0 8px;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#a35600;">{s}</h2>'
    parts = [f'<h1 style="margin:0 0 4px;font-family:Georgia,serif;font-size:26px;color:#1a1a1a;">Good morning, La Porte</h1>',
             f'<p style="margin:0 0 18px;font-size:14px;color:#5b665b;">{esc(now.strftime("%A, %B %-d, %Y"))}</p>']
    if alerts:
        rows = []
        for a in alerts:
            ends = a.get("ends") or a.get("expires")
            until = ""
            try:
                until = " until " + datetime.datetime.fromisoformat(ends).astimezone(CENTRAL).strftime("%a. %-I:%M %p")
            except Exception:
                pass
            rows.append(f"<strong>{esc(a.get('event'))}</strong>{esc(until)}")
        parts.append('<div style="border-left:4px solid #b3261e;background:#fdf1ef;padding:10px 14px;margin:0 0 16px;font-size:15px;line-height:1.5;">'
                     + "<br>".join(rows) + f'<br><a href="{SITE}/emergency" style="color:#1a1a1a;">What it means and what to do</a></div>')
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
    ahead = []
    started = False
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
        saved = datetime.datetime.fromisoformat(home["fetched"]).astimezone(CENTRAL).strftime("%-I:%M %p %Z")
    except Exception:
        saved = "this morning"
    parts.append(f'<p style="margin:18px 0 0;"><a href="{SITE}/" style="display:inline-block;background:#ff8a00;color:#1a1a1a;font-weight:700;text-decoration:none;padding:12px 18px;border-radius:8px;">Live weather and radar</a></p>')
    foot = (f"From the National Weather Service forecast for La Porte, as of {esc(saved)}. Forecasts change; for warnings, "
            f"trust the National Weather Service and local officials. La Porte Weather Now is free, local and run by Scoop.<br><br>"
            f"You're getting this because you signed up for the morning forecast at laporteweathernow.com and confirmed your email. "
            f'<a href="{{{{ unsubscribe }}}}" style="color:#5b665b;">Unsubscribe</a> anytime, in one click.<br><br>'
            f"La Porte Weather Now · {esc(cfg.get('mailingAddress') or '[MAILING ADDRESS GOES HERE]')}")
    body = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(subject)}</title></head><body style="margin:0;background:#f4f1e8;">'
            f'<div style="display:none;max-height:0;overflow:hidden;">{esc(preview_text)}</div>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1e8;"><tr><td align="center" style="padding:20px 12px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:12px;">'
            '<tr><td style="background:#1a1a1a;color:#ffffff;padding:14px 22px;border-radius:12px 12px 0 0;font-family:Arial,sans-serif;font-weight:800;letter-spacing:.06em;font-size:13px;">LA PORTE WEATHER NOW · MORNING FORECAST</td></tr>'
            '<tr><td style="padding:22px;font-family:Arial,Helvetica,sans-serif;">' + "".join(parts) + '</td></tr>'
            f'<tr><td style="padding:16px 22px 22px;font-family:Arial,sans-serif;font-size:12px;line-height:1.5;color:#5b665b;border-top:1px solid #e5e1d5;">{foot}</td></tr>'
            '</table></td></tr></table></body></html>')
    return subject, body, preview_text


# ---------- Brevo ----------
def campaign_name(now):
    return f"Morning forecast {now.date().isoformat()}"


def todays_campaign(now):
    out = brevo("/emailCampaigns?limit=50&offset=0&sort=desc")
    for c in out.get("campaigns", []) or []:
        if c.get("name") == campaign_name(now):
            return c
    return None


def sends_left():
    acct = brevo("/account")
    for p in acct.get("plan", []) or []:
        if p.get("creditsType") == "sendLimit":
            return p.get("credits"), p.get("type")
    return None, None


def list_size(list_id):
    l = brevo(f"/contacts/lists/{list_id}")
    return l.get("uniqueSubscribers", l.get("totalSubscribers", 0)) or 0


def setup(cfg):
    if not KEY:
        print("No BREVO_API_KEY secret yet.")
        return 1
    acct = brevo("/account")
    plans = ", ".join(f"{p.get('type')} ({p.get('credits')} {p.get('creditsType')})" for p in acct.get("plan", []))
    print(f"Brevo account OK: {plans}")
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
        json.dump(cfg, f, indent=1)
        f.write("\n")
    miss = ready(cfg)
    print("Ready to send." if not miss else "Saved. Still needed before anything is sent: " + "; ".join(miss))
    return 0


def main(argv):
    mode = argv[1] if len(argv) > 1 else "send"
    cfg = load_config()
    if mode == "setup":
        return setup(cfg)
    now = now_central()
    home = get_json(HOME_JSON)
    try:
        closings = get_json(CLOSINGS_JSON)
    except Exception:
        closings = None
    subject, body, preview_text = build(home, closings, cfg, now)
    if mode == "preview":
        with open("morning-email-preview.html", "w", encoding="utf-8") as f:
            f.write(body)
        print(f"Subject: {subject}\nSaved morning-email-preview.html")
        if os.environ.get("TEST_TO_OWNER") == "1":
            if not KEY:
                print("No BREVO_API_KEY secret, so no test email.")
                return 1
            brevo("/smtp/email", "POST", {"sender": {"name": cfg["senderName"], "email": cfg["senderEmail"]},
                                           "to": [{"email": OWNER}], "subject": "[TEST] " + subject,
                                           "htmlContent": body.replace("{{ unsubscribe }}", SITE + "/morning-email")})
            print(f"Sent a test to {OWNER} only.")
        return 0
    # send
    miss = ready(cfg) + ([] if KEY else ["no BREVO_API_KEY secret"])
    if miss:
        print("Morning email isn't set up yet, so nothing was sent: " + "; ".join(miss))
        return 0
    hm = now.strftime("%H:%M")
    if not ("05:30" <= hm <= "06:44"):
        print(f"Not sending time ({now:%-I:%M %p %Z}).")
        return 0
    try:
        fetched = datetime.datetime.fromisoformat(home["fetched"])
        age = (now - fetched).total_seconds() / 3600
    except Exception:
        age = 99
    if age > 3:
        print(f"The forecast copy is {age:.1f} hours old; not sending a stale forecast today.")
        return 3 if hm <= "05:44" else 0     # one failure email per morning is enough
    existing = todays_campaign(now)
    if existing:
        print(f"Today's email is already {existing.get('status')} ({existing.get('name')}).")
        return 0
    n = list_size(cfg["listId"])
    if n == 0:
        print("No confirmed subscribers yet; nothing to send.")
        return 0
    left, plan = sends_left()
    send_at = datetime.datetime.combine(now.date(), datetime.time(*map(int, cfg.get("sendAt", "06:00").split(":"))), CENTRAL)
    camp = {"name": campaign_name(now), "subject": subject, "previewText": preview_text or "",
            "sender": {"name": cfg["senderName"], "email": cfg["senderEmail"]},
            "htmlContent": body, "recipients": {"listIds": [int(cfg["listId"])]}}
    if now < send_at - datetime.timedelta(minutes=2):
        camp["scheduledAt"] = send_at.isoformat()
        c = brevo("/emailCampaigns", "POST", camp)
        print(f"Scheduled today's email (campaign {c.get('id')}) for {send_at:%-I:%M %p %Z} to {n} subscribers.")
    else:
        c = brevo("/emailCampaigns", "POST", camp)
        brevo(f"/emailCampaigns/{c['id']}/sendNow", "POST")
        print(f"Sent today's email (campaign {c.get('id')}) now ({now:%-I:%M %p %Z}; the start came late) to {n} subscribers.")
    if left is not None and plan == "free" and (n > left or n > DAILY_LIMIT - 40):
        print(f"WARNING: {n} subscribers and {left} of Brevo's {DAILY_LIMIT} free daily sends left. On the free plan only "
              f"{DAILY_LIMIT} emails go out a day in all; the rest wait. Time to look at a paid Brevo plan.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
