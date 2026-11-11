#!/usr/bin/env python3
"""Snow Help for laporteweathernow.com/snow-help (added Nov. 10, 2026). Runs itself: nobody has to approve,
label or text anything.

Neighbors ask for help clearing snow; other neighbors and plow services offer it. Every 15-minute tick
(inside the "Readers' reports" workflow) this job:

  1. Puts each new request (Netlify form "snow-help") on the board by itself. The board is snow-help.json on
     the public "reports" branch (written into REPORTS_DIR, which the workflow saves): the town and what's
     needed, all picked from fixed lists, so nothing anyone typed is ever public. No street address is
     collected at all. Limits: 2 open requests per phone number, no repeats within a day, 20 new per run.
  2. Emails the helpers on the helper list who cover that town (through Brevo, free plan, keeping the
     morning emails' share of the day's sends), with a link to offer help.
  3. Connects them when a helper offers (Netlify form "snow-helper", from a request's "I can help" button):
     the helper is emailed the asker's first name and phone number, and the asker (if they gave an email)
     is emailed the helper's name and phone. Up to 3 helpers per request; 5 offers a day per helper.
     If the email can't go out, it is tried again every run for two days.
  4. Takes a request off the board a day after it's marked cleared (the "Mark it cleared" link in those
     emails, form "snow-update"), right away when the asker cancels, or after three days.
  5. Erases private details 60 days after a request (180 days after a helper signs up), or right away when
     someone cancels or leaves the helper list.

The record of all this is one issue per request or helper in the PRIVATE repository
ScoopAndDude/laporteweathernow-reports. Names, phones and emails are only in each issue's first comment,
so they can be deleted for good (a deleted comment keeps no history). Scoop doesn't have to do anything
there, but he can: `unpublish` or `reject` takes a request off the board, `done` marks it cleared,
`approve` puts an expired one back up, and closing a helper's issue takes them off the helper list.

Secrets: NETLIFY_FORMS_TOKEN and REPORTS_QUEUE_TOKEN (the same two as reports_queue.py; nothing happens
without them) and BREVO_API_KEY (without it requests still post, but nobody is emailed).
It prints counts only, never anything a person typed: this repository's job logs are public.

  python3 scripts/snow_help.py      (REPORTS_DIR = the reports branch's files, default ./reports-out)
"""
import datetime
import hashlib
import hmac
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
SITE_ID = "18c15497-9910-4f84-abe4-aab2675f9a9d"      # laporteweathernow.com on Netlify
FORM_ASK, FORM_HELP, FORM_UPDATE = "snow-help", "snow-helper", "snow-update"
QUEUE = os.environ.get("REPORTS_QUEUE_REPO", "ScoopAndDude/laporteweathernow-reports")
OUT = os.environ.get("REPORTS_DIR", "reports-out")
NETLIFY = os.environ.get("NETLIFY_FORMS_TOKEN", "").strip()
GH = os.environ.get("REPORTS_QUEUE_TOKEN", "").strip()
BREVO_KEY = os.environ.get("BREVO_API_KEY", "").strip()
NETLIFY_API = os.environ.get("NETLIFY_API", "https://api.netlify.com/api/v1")
GITHUB_API = os.environ.get("GITHUB_API", "https://api.github.com")
BREVO_API = os.environ.get("BREVO_API", "https://api.brevo.com/v3")
CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "morning-email.json")
PAGE = "https://laporteweathernow.com/snow-help"
BOARD_DAYS, DONE_HOURS = 3, 24
ERASE_ASK_DAYS, ERASE_HELP_DAYS = 60, 180
MAX_NEW, MAX_ERASE = 20, 30
MAX_HELPERS = 3                 # helpers connected to one request
MAX_OPEN_PER_PHONE = 2          # open requests from one phone number
MAX_OFFERS_PER_DAY = 5          # offers from one helper in 24 hours
MAX_LIST_MAIL = 25              # helper-list emails for one new request
MAX_MAIL = 60                   # emails in one run
MAIL_RESERVE = 20               # sends always left for the site's other emails
RETRY_HOURS = 48

# The same towns, spelled the same way, as the forms on /snow-help.
TOWNS = ["LaPorte", "Michigan City", "Westville", "Wanatah", "Union Mills", "Kingsford Heights", "Hanna", "La Crosse",
         "Rolling Prairie", "New Carlisle", "Trail Creek", "Long Beach", "Michiana Shores", "Kingsbury", "Mill Creek",
         "Hudson Lake", "Rural LaPorte County"]
CLEAR = {"driveway": "Driveway", "driveway-walk": "Driveway and sidewalk", "walk": "Sidewalk or walkway",
         "steps": "Steps and path to the door", "other": "Something else"}
SIZE = {"1car": "1-car driveway", "2car": "2-car driveway", "long": "Long or country driveway", "small": "Just a walk or steps"}
TOOLS = {"shovel": "Shovel is fine", "blower": "Needs a snowblower", "plow": "Needs a plow"}
PAY = {"free": "Free help", "either": "Free or small pay", "pay": "Will pay"}
WHEN = {"asap": "As soon as possible", "today": "Sometime today", "morning": "By tomorrow morning", "days": "In the next day or two"}
HTOOLS = {"shovel": "Shovel", "blower": "Snowblower", "plow": "Truck with a plow", "tractor": "Tractor or skid steer"}
HKIND = {"free": "Volunteer (always free)", "mixed": "Free for seniors and people with disabilities, paid otherwise",
         "paid": "Paid (agrees on a price before starting)"}
LABELS = {"snow help": ("bfdadc", "A Snow Help request (laporteweathernow.com/snow-help)"),
          "snow helper": ("c5def5", "Someone offering to help clear snow (private, never published)"),
          "on list": ("fef2c0", "Snow Help: gets an email when someone in their area asks for help"),
          "helper found": ("2da44e", "Snow Help: a helper has offered (shown on the board)"),
          "mail pending": ("d93f0b", "Snow Help: the connecting email hasn't gone out yet (retried every run)"),
          "done": ("8250df", "Snow Help: cleared (shown on the board for a day)"),
          "approve": ("0e8a16", "Publish this on laporteweathernow.com"),
          "reject": ("b60205", "Never publish this"),
          "published": ("1d76db", "This is on the site"),
          "unpublish": ("5319e7", "Take this back off the site")}
ASK_MARK = re.compile(r"<!-- lpwn-snow:([\w-]+) -->")
HELP_MARK = re.compile(r"<!-- lpwn-snow-helper:([\w-]+) -->")
WHO_MARK = re.compile(r"<!-- lpwn-snow-who:([0-9a-f]+) -->")
FOR_MARK = re.compile(r"<!-- lpwn-snow-for:(\d+) -->")
PRIVATE_MARK = "<!-- lpwn-snow-private -->"
SECRET = hashlib.sha256(("lpwn-snow-help:" + GH).encode()).digest()
mail = {"room": None, "sent": 0, "failed": 0}


def api(url, token, method="GET", body=None, auth="Bearer"):
    data = json.dumps(body).encode() if body is not None else None
    hdr = {"Accept": "application/json", "User-Agent": "laporteweathernow-snow-help"}
    if token:
        hdr["Authorization"] = f"{auth} {token}"
    if data is not None:
        hdr["Content-Type"] = "application/json"
    if url.startswith(GITHUB_API):
        hdr["X-GitHub-Api-Version"] = "2022-11-28"
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    with urllib.request.urlopen(req, timeout=40) as r:
        b = r.read()
        return json.loads(b) if b.strip() else {}


def gh(path, method="GET", body=None):
    return api(f"{GITHUB_API}{path}", GH, method, body)


def brevo(path, method="GET", body=None):
    req = urllib.request.Request(f"{BREVO_API}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"api-key": BREVO_KEY, "accept": "application/json",
                                          "content-type": "application/json", "User-Agent": "laporteweathernow-snow-help"})
    with urllib.request.urlopen(req, timeout=40) as r:
        b = r.read()
        return json.loads(b) if b.strip() else {}


def config():
    try:
        return json.load(open(CONFIG, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def mail_room():
    """Emails this run may still send: MAX_MAIL, and on Brevo's free plan no more than what's left today
    after the morning emails' share and a small reserve."""
    if mail["room"] is None:
        room = MAX_MAIL if BREVO_KEY else 0
        if BREVO_KEY:
            try:
                cfg = config()
                for p in brevo("/account").get("plan") or []:
                    if p.get("creditsType") == "sendLimit" and p.get("type") == "free":
                        members = int(brevo(f"/contacts/lists/{cfg['listId']}").get("totalSubscribers") or 0) if cfg.get("listId") else 0
                        room = min(room, int(p.get("credits") or 0) - members - MAIL_RESERVE)
            except Exception:
                pass                                   # Brevo didn't say; the per-run cap still applies
        mail["room"] = max(0, room)
    return mail["room"] - mail["sent"]


def send(to, subject, lines, stop_link=None):
    """One plain email. `lines` are paragraphs: text, or (label, link) for a link. True when Brevo took it."""
    if not to or mail_room() <= 0:
        mail["failed"] += 1
        return False
    cfg = config()
    foot = ["La Porte Weather Now runs Snow Help for free to connect neighbors. Helpers are volunteers or independent "
            "businesses, not our staff; we don't check backgrounds. Agree on what will be done, and any price, before work "
            "starts, and never pay up front. In an emergency call 911.",
            f"La Porte Weather Now LLC, {cfg.get('mailingAddress') or '703 A St., La Porte, IN 46350'}"]
    if stop_link:
        lines = list(lines) + [("Stop these emails and erase my sign-up", stop_link)]
    parts, text = [], []
    for ln in lines:
        if isinstance(ln, tuple):
            parts.append(f'<p><a href="{html.escape(ln[1], quote=True)}" style="font-weight:bold;">{html.escape(ln[0])}</a></p>')
            text.append(f"{ln[0]}: {ln[1]}")
        else:
            parts.append(f"<p>{html.escape(ln)}</p>")
            text.append(ln)
    parts += [f'<p style="font-size:12px;color:#666;">{html.escape(f)}</p>' for f in foot]
    try:
        brevo("/smtp/email", "POST", {
            "sender": {"name": cfg.get("senderName") or "La Porte Weather Now",
                       "email": cfg.get("senderEmail") or "alerts@laporteweathernow.com"},
            "to": [{"email": to}], "subject": subject,
            "htmlContent": '<div style="font-family:Arial,sans-serif;font-size:16px;line-height:1.5;color:#222;">' + "".join(parts) + "</div>",
            "textContent": "\n\n".join(text + foot)})
    except Exception:
        mail["failed"] += 1
        return False
    mail["sent"] += 1
    return True


def clean(t, n=300):
    """Text someone typed, made safe for an issue and an email: one line, no markup, no @-mentions or links."""
    t = re.sub(r"<[^>]*>", " ", str(t or ""))
    t = re.sub(r"[\x00-\x1f\x7f]+", " ", t)
    t = re.sub(r"https?://\S+|www\.\S+", "[link removed]", t)
    t = re.sub("@(?!​)", "@​", t).replace("`", "'")
    t = re.sub(r"[*_#\[\]|>~]", "", t)
    return re.sub(r"\s+", " ", t).strip()[:n]


def phone(s):
    """(219) 555-0123, or "" when it isn't a 10-digit U.S. number."""
    d = re.sub(r"\D", "", str(s or ""))
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 and d[0] not in "01" else ""


def email_of(s):
    s = str(s or "").strip()
    return s if len(s) <= 120 and re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", s) else ""


def who(s):
    """A short fingerprint of a phone number, to count requests and offers without storing the number again."""
    return hmac.new(SECRET, ("who:" + re.sub(r"\D", "", s)).encode(), hashlib.sha256).hexdigest()[:16]


def token(kind, n):
    return hmac.new(SECRET, f"{kind}:{n}".encode(), hashlib.sha256).hexdigest()[:20]


def link(kind, n):
    return f"{PAGE}?act={kind}&id={n}&t={token(kind, n)}#update"


def town_of(s):
    return next((t for t in TOWNS if t.lower() == str(s or "").strip().lower()), None)


def when_sent(sub):
    return datetime.datetime.fromisoformat(sub["created_at"].replace("Z", "+00:00"))


def made(issue):
    return datetime.datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))


def fmt(t):
    return t.astimezone(CENTRAL).strftime("%b %-d, %Y, %-I:%M %p %Z")


def day(t):
    return t.astimezone(CENTRAL).strftime("%b %-d, %Y")


def ask_body(sub, d, form_id):
    sent = when_sent(sub)
    return "\n".join([
        f"<!-- lpwn-snow:{sub['id']} -->", f"<!-- lpwn-snow-who:{who(phone(d.get('phone')))} -->",
        "Someone asked for help clearing snow. **It went on the board by itself; you don't have to do anything.** "
        "Only the \"Shown publicly\" lines are on the board. Their name and phone are in the first comment below.", "",
        "### Shown publicly (you can edit these lines; the board follows)",
        f"- Town: {town_of(d.get('town'))}",
        f"- Clearing: {CLEAR[d['clear']]}",
        f"- Size: {SIZE.get(d.get('size'), '(not sure)')}",
        f"- Tools: {TOOLS.get(d.get('tools'), '(not sure)')}",
        f"- Pay: {PAY[d['pay']]}",
        f"- When: {WHEN.get(d.get('when'), 'As soon as possible')}",
        f"- Priority: {'yes' if d.get('priority') else 'no'}",
        "- Note: (none)",
        "",
        "### Not shown",
        f"- Sent {fmt(sent)} (Netlify submission {sub['id']}: https://app.netlify.com/sites/scoopanddude/forms/{form_id})",
        "",
        "Helpers who offer are emailed this person's first name and phone automatically (up to 3). "
        "**Take it down:** add `unpublish` or `reject`. **Mark it cleared:** add `done`. **Put an expired one back up:** add `approve`.",
        "",
        f"_Their private details are erased on {day(sent + datetime.timedelta(days=ERASE_ASK_DAYS))}._"])


def ask_private(d):
    return "\n".join([PRIVATE_MARK, "### Private: only you can see this",
                      f"- Name: {clean(d.get('name'), 40)}",
                      f"- Phone: {phone(d.get('phone'))}",
                      f"- Email: {email_of(d.get('email')) or '(none)'}",
                      f"- Their note: {clean(d.get('details'), 300) or '(none)'}",
                      f"- Can't safely shovel (age, health or disability): {'yes' if d.get('priority') else 'not checked'}",
                      "- 18 or older: yes. OK to share their first name and phone with up to 3 helpers who offer: yes.",
                      "", "_This comment is deleted automatically when the private details are erased._"])


def helper_body(sub, d, form_id, req_num):
    sent = when_sent(sub)
    where = "Anywhere" if str(d.get("town")) == "Anywhere" else town_of(d.get("town"))
    return "\n".join([
        f"<!-- lpwn-snow-helper:{sub['id']} -->", f"<!-- lpwn-snow-who:{who(phone(d.get('phone')))} -->",
        (f"<!-- lpwn-snow-for:{req_num} -->" if req_num else "<!-- list only -->"),
        "Someone signed up to help clear snow. Private: helper sign-ups are never shown on the site. "
        "Their name, phone and email are in the first comment below. Nothing for you to do.", "",
        (f"Offering to help with #{req_num}." if req_num else "Signed up for the helper list."),
        "",
        f"- Where: {where}",
        f"- Has: {HTOOLS[d['tools']]}",
        f"- Free or paid: {HKIND[d['kind']]}",
        f"- Sent {fmt(sent)} (Netlify submission {sub['id']}: https://app.netlify.com/sites/scoopanddude/forms/{form_id})",
        "",
        "Close this issue to take them off the helper list.",
        "",
        f"_Their private details are erased on {day(sent + datetime.timedelta(days=ERASE_HELP_DAYS))}._"])


def helper_private(d):
    return "\n".join([PRIVATE_MARK, "### Private: only you can see this",
                      f"- Name: {clean(d.get('name'), 60)}",
                      f"- Phone: {phone(d.get('phone'))}",
                      f"- Email: {email_of(d.get('email'))}",
                      f"- Business: {clean(d.get('business'), 80) or '(none)'}",
                      f"- Usually free: {clean(d.get('availability'), 120) or '(not given)'}",
                      "- 18 or older: yes. Took the helper pledge and OK'd sharing their name and phone with the person they help: yes.",
                      "", "_This comment is deleted automatically when the private details are erased._"])


def fields(text, names):
    out = {}
    for m in re.finditer(r"^- (" + "|".join(names) + r"):[ \t]*(.*)$", text or "", re.M):
        v = m.group(2).strip()
        out[m.group(1).lower()] = "" if v.lower() in ("(none)", "(not sure)", "(not given)") else v
    return out


def parse_public(body):
    sec = (body or "").split("### Shown publicly", 1)[-1].split("### Not shown", 1)[0]
    return fields(sec, ["Town", "Clearing", "Size", "Tools", "Pay", "When", "Priority", "Note"])


def private_of(n):
    """The private comment's lines for issue #n ({} once erased)."""
    for c in gh(f"/repos/{QUEUE}/issues/{n}/comments?per_page=100"):
        if PRIVATE_MARK in (c.get("body") or ""):
            return fields(c["body"], ["Name", "Phone", "Email", "Their note", "Business", "Usually free"])
    return {}


def record(num, f, old=None):
    """The board's entry for request #num from its "Shown publicly" lines, or an error message."""
    town = town_of(f.get("town"))
    pay = next((v for v in PAY.values() if v.lower() == f.get("pay", "").strip().lower()), None)
    what = clean(f.get("clearing"), 60)
    if not town or not pay or not what:
        return None, ("Not posted: the Town line has to be one of " + ", ".join(TOWNS) + "; the Pay line one of "
                      + ", ".join(PAY.values()) + "; and the Clearing line can't be empty. Fix the line and add `approve` again.")
    rec = dict(old or {})
    rec.update({"id": num, "town": town, "clear": what, "size": clean(f.get("size"), 60), "tools": clean(f.get("tools"), 60),
                "pay": pay, "payKind": next(k for k, v in PAY.items() if v == pay), "when": clean(f.get("when"), 60),
                "priority": f.get("priority", "").strip().lower() in ("yes", "y", "true"), "note": clean(f.get("note"), 200)})
    rec.setdefault("helpers", 0)
    return rec, None


def erase(issue, close=False):
    n = issue["number"]
    for c in gh(f"/repos/{QUEUE}/issues/{n}/comments?per_page=100"):
        if PRIVATE_MARK in (c.get("body") or ""):
            gh(f"/repos/{QUEUE}/issues/comments/{c['id']}", "DELETE")
    body = re.sub(r"_Their private details are erased on [^_]*\._", "", issue.get("body") or "").rstrip()
    patch = {"body": body + f"\n\n_Private details erased {day(datetime.datetime.now(CENTRAL))}._\n<!-- erased -->"}
    if close:
        patch.update({"state": "closed", "state_reason": "not_planned"})
        issue["state"] = "closed"
    issue["body"] = patch["body"]
    gh(f"/repos/{QUEUE}/issues/{n}", "PATCH", patch)


def main():
    if not NETLIFY or not GH:
        print("Snow Help isn't set up yet (secrets NETLIFY_FORMS_TOKEN and REPORTS_QUEUE_TOKEN); nothing to do.")
        return 0
    if not gh(f"/repos/{QUEUE}").get("private"):
        print(f"{QUEUE} is public; requests would be visible to everyone. Make it private first.")
        return 1
    now = datetime.datetime.now(CENTRAL)
    for name, (color, desc) in LABELS.items():
        try:
            gh(f"/repos/{QUEUE}/labels", "POST", {"name": name, "color": color, "description": desc})
        except urllib.error.HTTPError as e:
            if e.code != 422:          # 422: the label is already there
                raise
    issues, page = [], 1
    while True:
        batch = gh(f"/repos/{QUEUE}/issues?state=all&per_page=100&page={page}")
        issues += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100 or page >= 20:
            break
        page += 1
    asks, helpers = {}, {}
    for i in issues:
        i["labels"] = [{"name": l["name"]} for l in i.get("labels", [])]
        m = ASK_MARK.search(i.get("body") or "")
        if m:
            asks[m.group(1)] = i
        m = HELP_MARK.search(i.get("body") or "")
        if m:
            helpers[m.group(1)] = i
    by_num = {i["number"]: i for i in asks.values()}
    helper_by_num = {i["number"]: i for i in helpers.values()}

    def labels(i):
        return {l["name"] for l in i.get("labels", [])}

    def label(i, name):
        if name not in labels(i):
            gh(f"/repos/{QUEUE}/issues/{i['number']}/labels", "POST", {"labels": [name]})
            i["labels"].append({"name": name})

    def unlabel(i, name):
        if name in labels(i):
            try:
                gh(f"/repos/{QUEUE}/issues/{i['number']}/labels/{urllib.parse.quote(name)}", "DELETE")
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
            i["labels"] = [l for l in i["labels"] if l["name"] != name]

    def comment(n, text):
        gh(f"/repos/{QUEUE}/issues/{n}/comments", "POST", {"body": text})

    def who_of(i):
        m = WHO_MARK.search(i.get("body") or "")
        return m.group(1) if m else ""

    forms = {f.get("name"): f for f in api(f"{NETLIFY_API}/sites/{SITE_ID}/forms", NETLIFY)}
    cutoff = now - datetime.timedelta(days=14)
    subs_of = {}

    def submissions(name):
        if name not in subs_of:
            f = forms.get(name)
            subs_of[name] = (f, api(f"{NETLIFY_API}/forms/{f['id']}/submissions?per_page=100", NETLIFY) if f else [])
        return subs_of[name]

    def drop(sid):
        try:
            api(f"{NETLIFY_API}/submissions/{sid}", NETLIFY, "DELETE")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise

    try:
        board = json.load(open(os.path.join(OUT, "snow-help.json"), encoding="utf-8"))
    except Exception:
        board = {}
    live = {r["id"]: r for r in board.get("requests", []) if isinstance(r, dict) and r.get("id")}
    before = json.dumps(live, sort_keys=True)
    changed = not board.get("ready")

    # 1) Links people tapped in their emails: mark it cleared, cancel my request, take me off the helper list.
    updates = 0
    for sub in submissions(FORM_UPDATE)[1]:
        d = sub.get("data") or {}
        act, num, tok = str(d.get("action") or ""), str(d.get("id") or ""), str(d.get("token") or "")
        if act in ("done", "cancel", "stop") and num.isdigit() and hmac.compare_digest(tok, token(act, int(num))):
            n = int(num)
            i = by_num.get(n) if act != "stop" else helper_by_num.get(n)
            if i and act == "done" and "reject" not in labels(i):
                label(i, "done")
                updates += 1
            elif i and act == "cancel":
                live.pop(n, None)
                unlabel(i, "published")
                if "<!-- erased -->" not in (i.get("body") or ""):
                    comment(n, f"Canceled by the person who asked, {fmt(now)}.")
                    erase(i, close=True)
                updates += 1
            elif i and act == "stop":
                unlabel(i, "on list")
                unlabel(i, "mail pending")
                if "<!-- erased -->" not in (i.get("body") or ""):
                    comment(n, f"They asked to be taken off the helper list, {fmt(now)}.")
                    erase(i, close=True)
                updates += 1
        drop(sub["id"])

    # 2) New requests: straight onto the board, and an email to the helpers who cover that town.
    form, subs = submissions(FORM_ASK)
    opened = skipped = 0
    for sub in sorted(subs, key=lambda s: s.get("created_at", "")):
        if sub["id"] in asks or opened >= MAX_NEW or now - when_sent(sub) > datetime.timedelta(days=2):
            continue                                       # a request this job didn't post within two days is stale
        d = sub.get("data") or {}
        town = town_of(d.get("town"))
        if (d.get("bot-field") or not d.get("consent_age") or not d.get("consent_share") or not town
                or d.get("clear") not in CLEAR or d.get("pay") not in PAY or not phone(d.get("phone"))
                or not clean(d.get("name"), 40)):
            skipped += 1
            continue
        me = who(phone(d.get("phone")))
        mine = [i for i in asks.values() if who_of(i) == me]
        if (sum(1 for i in mine if i["number"] in live and live[i["number"]].get("status") != "done") >= MAX_OPEN_PER_PHONE
                or any(now - made(i) < datetime.timedelta(hours=24) and f"- Clearing: {CLEAR[d['clear']]}\n" in (i.get("body") or "")
                       and f"- Town: {town}\n" in (i.get("body") or "") for i in mine)):
            skipped += 1                                   # too many open, or the same request again within a day
            continue
        title = f"Snow help: {CLEAR[d['clear']]} in {town} · {WHEN.get(d.get('when'), 'As soon as possible')} · {PAY[d['pay']]}"
        body = ask_body(sub, d, form["id"])
        i = gh(f"/repos/{QUEUE}/issues", "POST", {"title": title[:120], "body": body, "labels": ["snow help", "published"]})
        i["labels"] = [{"name": "snow help"}, {"name": "published"}]
        n = i["number"]
        comment(n, ask_private(d))
        asks[sub["id"]] = by_num[n] = i
        rec, _ = record(n, parse_public(body))
        rec.update({"status": "open", "posted": now.isoformat(timespec="seconds"), "helpers": 0})
        live[n] = rec
        opened += 1
        what = f"{rec['clear']} in {town}" + (f" ({rec['size']})" if rec["size"] else "")
        if email_of(d.get("email")):
            send(email_of(d.get("email")), f"Your snow help request is on the board (#{n})",
                 [f"Hi {clean(d.get('name'), 40)}, your request is on the Snow Help board: {what}. {rec['pay']}.",
                  "When a neighbor or plow service offers to help, we email you their name and phone number, and they get "
                  "your first name and phone number so they can call or text you. Up to 3 helpers can offer.",
                  "You decide who helps. Share your address only once you've talked with them. Never pay up front.",
                  ("Mark it cleared", link("done", n)), ("Cancel my request", link("cancel", n)),
                  "Help isn't guaranteed. Your request comes off the board after three days."])
        sent_list = 0
        for h in helpers.values():
            if sent_list >= MAX_LIST_MAIL:
                break
            if h.get("state") != "open" or "on list" not in labels(h) or who_of(h) == me:
                continue
            hf = fields(h.get("body"), ["Where", "Has", "Free or paid"])
            if hf.get("where") not in ("Anywhere", town):
                continue
            if rec["payKind"] == "free" and hf.get("free or paid") == HKIND["paid"]:
                continue                                   # paid-only services aren't emailed about free-help requests
            to = private_of(h["number"]).get("email")
            if to and send(email_of(to), f"Snow help needed in {town}: {rec['clear']}",
                           [f"A neighbor in {town} asked for help: {what}. {rec['tools'] or 'Shovel or plow: not sure'}. "
                            f"{rec['pay']}. Needed: {rec['when'].lower()}." + (" Someone at this home can't safely shovel." if rec["priority"] else ""),
                            ("I can help with this one", f"{PAGE}?help={n}#offer"),
                            "Tap the link and send the short form. We'll email you their first name and phone number."],
                           stop_link=link("stop", h["number"])):
                sent_list += 1

    # 3) Helper sign-ups and offers.
    def connect(h):
        """Email the helper the asker's first name and phone (and the asker the helper's). True when settled."""
        m = FOR_MARK.search(h.get("body") or "")
        n = int(m.group(1)) if m else 0
        req, rec = by_num.get(n), live.get(n)
        hp = private_of(h["number"])
        if not hp.get("email"):
            return True                                    # erased since; nothing to send
        stop = link("stop", h["number"])
        first = hp.get("name", "").split(" ")[0]
        if not req or not rec or rec.get("status") == "done" or rec.get("helpers", 0) >= MAX_HELPERS:
            send(email_of(hp["email"]), f"Snow help request #{n} is already covered",
                 [f"Thanks for offering, {first}. Request #{n} is already covered or has come off the board.",
                  ("See who else needs a hand", PAGE + "#board")], stop_link=stop)
            return True
        rp = private_of(n)
        if not rp.get("phone"):
            return True
        ok = send(email_of(hp["email"]), f"You're connected: snow help request #{n} in {rec['town']}",
                  [f"Thank you for stepping up, {first}. Here's who asked for help:",
                   f"{rp.get('name', 'Your neighbor')}, {rp['phone']} (call or text). {rec['town']}: {rec['clear']}"
                   + (f", {rec['size']}" if rec["size"] else "") + f". {rec['pay']}. Needed: {(rec['when'] or 'soon').lower()}.",
                   (f"Their note: {rp['their note']}" if rp.get("their note") else "Call or text them to get the address and set a time."),
                   "Please reach out soon, agree on any price before you start, take no money up front, and clear only what they ask for. "
                   "Use their number for this job only.",
                   ("Mark it cleared when you're done", link("done", n))], stop_link=stop)
        if not ok:
            return False
        rec["helpers"] = rec.get("helpers", 0) + 1
        if rec.get("status") == "open":
            rec["status"] = "matched"
        label(req, "helper found")
        hf = fields(h.get("body"), ["Has", "Free or paid"])
        comment(n, f"Helper #{h['number']} offered and was emailed this person's first name and phone ({rec['helpers']} of {MAX_HELPERS}).")
        if rp.get("email"):
            send(email_of(rp["email"]), f"A helper offered to clear your snow (request #{n})",
                 [f"Good news, {rp.get('name', 'neighbor')}: {hp.get('name', 'a helper')} offered to help.",
                  f"{hp.get('name', 'Your helper')}, {hp.get('phone', '')}" + (f", {hp['business']}" if hp.get("business") else "")
                  + f". Has: {hf.get('has', 'a shovel')}. {hf.get('free or paid', '')}.",
                  "They have your first name and phone number and should call or text you. You can also reach out first. "
                  "Agree on any price before work starts, never pay up front, and nobody needs to come inside your home.",
                  ("Mark it cleared", link("done", n)), ("Cancel my request", link("cancel", n))])
        return True

    form, subs = submissions(FORM_HELP)
    signed = 0
    for sub in sorted(subs, key=lambda s: s.get("created_at", "")):
        if sub["id"] in helpers or signed >= MAX_NEW or when_sent(sub) < cutoff:
            continue
        d = sub.get("data") or {}
        if (d.get("bot-field") or not d.get("consent_age") or not d.get("consent_pledge") or not phone(d.get("phone"))
                or not email_of(d.get("email")) or not clean(d.get("name"), 60)
                or not (d.get("town") == "Anywhere" or town_of(d.get("town")))
                or d.get("tools") not in HTOOLS or d.get("kind") not in HKIND):
            skipped += 1
            continue
        me = who(phone(d.get("phone")))
        req = str(d.get("request") or "").strip().lstrip("#")
        req_num = int(req) if req.isdigit() and int(req) in by_num else None
        theirs = [h for h in helpers.values() if who_of(h) == me]
        if req_num and (sum(1 for h in theirs if FOR_MARK.search(h.get("body") or "") and now - made(h) < datetime.timedelta(hours=24)) >= MAX_OFFERS_PER_DAY
                        or any(f"<!-- lpwn-snow-for:{req_num} -->" in (h.get("body") or "") for h in theirs)
                        or who_of(by_num[req_num]) == me):
            skipped += 1                                   # too many offers today, the same offer twice, or their own request
            continue
        on_list = (bool(d.get("list")) or not req_num) and not any("on list" in labels(h) and h.get("state") == "open" for h in theirs)
        where = "anywhere" if d.get("town") == "Anywhere" else town_of(d.get("town"))
        title = f"Snow helper{f' for #{req_num}' if req_num else ''}: {where} · {HTOOLS[d['tools']]} · {HKIND[d['kind']].split(' (')[0]}"
        names = ["snow helper"] + (["on list"] if on_list else []) + (["mail pending"] if req_num else [])
        i = gh(f"/repos/{QUEUE}/issues", "POST", {"title": title[:120], "body": helper_body(sub, d, form["id"], req_num), "labels": names})
        i["labels"] = [{"name": x} for x in names]
        comment(i["number"], helper_private(d))
        helpers[sub["id"]] = helper_by_num[i["number"]] = i
        signed += 1
        if not req_num:
            send(email_of(d.get("email")), "You're on the Snow Help helper list",
                 [f"Thank you, {clean(d.get('name'), 60).split(' ')[0]}! When someone "
                  + ("in LaPorte County" if d.get("town") == "Anywhere" else f"in {where}") + " asks for help clearing snow, we'll email you.",
                  "Tap \"I can help\" on a request and we'll email you that neighbor's first name and phone number.",
                  ("See the board", PAGE + "#board")], stop_link=link("stop", i["number"]))
    for h in helpers.values():                             # new offers, and ones whose email didn't go out earlier
        if "mail pending" in labels(h) and h.get("state") == "open":
            if now - made(h) > datetime.timedelta(hours=RETRY_HOURS) or connect(h):
                unlabel(h, "mail pending")

    # 4) Status, and anything Scoop changed by hand.
    for i in asks.values():
        L, n, body = labels(i), i["number"], i.get("body") or ""
        if "unpublish" in L or ("reject" in L and "published" in L):
            live.pop(n, None)
            unlabel(i, "unpublish")
            unlabel(i, "published")
            comment(n, f"Taken off the board {fmt(now)}.")
            L = labels(i)
        if "reject" in L:
            if "<!-- rejected -->" not in body and i.get("state") != "closed":
                comment(n, "Rejected: it won't be posted.")
                i["body"] = body + "\n<!-- rejected -->"
                gh(f"/repos/{QUEUE}/issues/{n}", "PATCH", {"state": "closed", "state_reason": "not_planned", "body": i["body"]})
            continue
        if "approve" in L and "published" not in L:
            rec, err = record(n, parse_public(body))
            unlabel(i, "approve")
            if err:
                comment(n, err)
                continue
            rec.update({"status": "open", "posted": now.isoformat(timespec="seconds"), "helpers": 0})
            rec.pop("doneAt", None)
            live[n] = rec
            label(i, "published")
            unlabel(i, "done")
            unlabel(i, "helper found")
            if i.get("state") == "closed":
                gh(f"/repos/{QUEUE}/issues/{n}", "PATCH", {"state": "open"})
                i["state"] = "open"
            comment(n, f"Back on the board {fmt(now)}: {PAGE}#req-{n}")
            L = labels(i)
        elif "approve" in L:
            unlabel(i, "approve")
        if "published" in L and n in live:
            rec = live[n]
            fresh, err = record(n, parse_public(body), rec)       # Scoop may edit the public lines
            if not err:
                live[n] = rec = fresh
            status = ("done" if ("done" in L or i.get("state") == "closed")
                      else "matched" if ("helper found" in L or rec.get("helpers", 0) > 0) else "open")
            if status != rec.get("status"):
                rec["status"] = status
                if status == "done":
                    rec["doneAt"] = now.isoformat(timespec="seconds")
                    label(i, "done")
                else:
                    rec.pop("doneAt", None)

    # 5) Off the board: a day after it was cleared, or three days after going up.
    for n, rec in list(live.items()):
        posted = datetime.datetime.fromisoformat(rec.get("posted") or now.isoformat())
        done_at = datetime.datetime.fromisoformat(rec["doneAt"]) if rec.get("doneAt") else None
        cleared = bool(done_at and now - done_at > datetime.timedelta(hours=DONE_HOURS))
        if cleared or (not done_at and now - posted > datetime.timedelta(days=BOARD_DAYS)):
            del live[n]
            i = by_num.get(n)
            if i:
                unlabel(i, "published")
                if not cleared:
                    comment(n, "Came off the board after three days. Add `approve` to put it back up.")
                if i.get("state") != "closed":
                    gh(f"/repos/{QUEUE}/issues/{n}", "PATCH", {"state": "closed", "state_reason": "completed" if cleared else "not_planned"})
                    i["state"] = "closed"

    # 6) Erase private details once they're old enough.
    erased = 0
    for name, group, days in ((FORM_ASK, asks, ERASE_ASK_DAYS), (FORM_HELP, helpers, ERASE_HELP_DAYS)):
        netlify_ids = {s["id"] for s in submissions(name)[1]}
        for sid, i in group.items():
            if erased >= MAX_ERASE:
                break
            if "<!-- erased -->" in (i.get("body") or ""):
                if sid in netlify_ids:                     # erased early (canceled, or left the list): the form copy goes too
                    drop(sid)
                continue
            if now - made(i) < datetime.timedelta(days=days):
                continue
            unlabel(i, "on list")
            erase(i, close=name == FORM_HELP)
            if sid in netlify_ids:
                drop(sid)
            erased += 1
        for s in submissions(name)[1]:                     # ones that never made it in (spam, missing boxes, over a limit)
            if erased < MAX_ERASE and s["id"] not in group and now - when_sent(s) > datetime.timedelta(days=days):
                drop(s["id"])
                erased += 1

    # 7) The season's count of neighbors helped (since July 1).
    start = datetime.datetime(now.year if now.month >= 7 else now.year - 1, 7, 1, tzinfo=CENTRAL)
    helped = sum(1 for i in asks.values() if "done" in labels(i) and made(i) >= start)
    if changed or helped != board.get("helped") or json.dumps(live, sort_keys=True) != before:
        os.makedirs(OUT, exist_ok=True)
        json.dump({"about": "Snow Help requests for laporteweathernow.com/snow-help. Town and what's needed only, all "
                            "picked from fixed lists: never a name, address, phone number or anything typed.",
                   "ready": True, "updated": now.isoformat(timespec="seconds"), "helped": helped, "maxHelpers": MAX_HELPERS,
                   "requests": sorted(live.values(), key=lambda r: r.get("posted", ""), reverse=True)},
                  open(os.path.join(OUT, "snow-help.json"), "w", encoding="utf-8"), indent=1)
    print(f"Snow Help: {opened} new requests, {signed} new helpers, {updates} updates, {skipped} skipped, {len(live)} on the board, "
          f"{mail['sent']} emails sent, {mail['failed']} not sent, {erased} erased, {helped} helped this season.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                      # never print what anyone typed: the log is public
        tb = e.__traceback__
        while tb.tb_next:
            tb = tb.tb_next
        print(f"Snow Help stopped: {type(e).__name__} at line {tb.tb_lineno}"
              + (f" (HTTP {e.code})" if isinstance(e, urllib.error.HTTPError) else ""))
        sys.exit(1)
