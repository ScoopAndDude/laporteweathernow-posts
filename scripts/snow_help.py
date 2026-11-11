#!/usr/bin/env python3
"""Snow Help for laporteweathernow.com/snow-help (added Nov. 10, 2026).

Neighbors ask for help clearing snow; other neighbors and plow services offer it. Nothing anyone sends is
public until Scoop approves it, and names, addresses and phone numbers are never public at all.

  1. Someone fills in "Ask for help" on /snow-help (Netlify Forms "snow-help": what needs clearing, how big,
     shovel or plow, free or paid, when, town, street address, first name, phone, a private note and the
     consent boxes). Each run of this job (every 15-minute tick, inside the "Readers' reports" workflow)
     opens one issue per request in the PRIVATE repository ScoopAndDude/laporteweathernow-reports, labeled
     "snow help". Only Scoop can see it. The name, phone, address and note go in the issue's first comment,
     never its title or text, so they can be deleted for good later (an issue's edits keep a history;
     a deleted comment doesn't).
  2. Scoop reads it in the GitHub app and adds a label:
       approve        put it on the board (after editing the "Shown publicly" lines, if he wants)
       helper found   the board says "A helper is on the way"
       done           the board says "Cleared" for a day, then it comes off (closing the issue does the same)
       unpublish      take it off the board
       reject         never post it (also closes the issue)
  3. Helper sign-ups (Netlify Forms "snow-helper") become their own private issues, labeled "snow helper".
     One sent from a request's "I can help" button names that request (#57), so it also shows on #57.
     Scoop texts the person who asked and the helper he picks, so they can connect.
  4. The board is snow-help.json on the public "reports" branch of this repository (written into REPORTS_DIR,
     which the workflow saves): the town and what's needed, never a name, address or phone number.
     A request comes off three days after it went up, or a day after it was cleared.
  5. Private details are erased 60 days after a request was sent (180 days after a helper signed up):
     the private comment and the Netlify submission are deleted.

Uses the same two secrets as reports_queue.py (NETLIFY_FORMS_TOKEN, REPORTS_QUEUE_TOKEN) and does nothing
without them. It prints counts only, never anything a person typed: this repository's job logs are public.

  python3 scripts/snow_help.py      (REPORTS_DIR = the reports branch's files, default ./reports-out)
"""
import datetime
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
FORM_ASK, FORM_HELP = "snow-help", "snow-helper"
QUEUE = os.environ.get("REPORTS_QUEUE_REPO", "ScoopAndDude/laporteweathernow-reports")
OUT = os.environ.get("REPORTS_DIR", "reports-out")
NETLIFY = os.environ.get("NETLIFY_FORMS_TOKEN", "").strip()
GH = os.environ.get("REPORTS_QUEUE_TOKEN", "").strip()
NETLIFY_API = os.environ.get("NETLIFY_API", "https://api.netlify.com/api/v1")
GITHUB_API = os.environ.get("GITHUB_API", "https://api.github.com")
PAGE = "https://laporteweathernow.com/snow-help"
BOARD_DAYS, DONE_HOURS = 3, 24
ERASE_ASK_DAYS, ERASE_HELP_DAYS = 60, 180
MAX_NEW, MAX_ERASE = 20, 30

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
          "helper found": ("2da44e", "Snow Help: a helper is on the way (shown on the board)"),
          "done": ("8250df", "Snow Help: cleared (shown on the board for a day)"),
          "approve": ("0e8a16", "Publish this on laporteweathernow.com"),
          "reject": ("b60205", "Never publish this"),
          "published": ("1d76db", "This is on the site"),
          "unpublish": ("5319e7", "Take this back off the site")}
ASK_MARK = re.compile(r"<!-- lpwn-snow:([\w-]+) -->")
HELP_MARK = re.compile(r"<!-- lpwn-snow-helper:([\w-]+) -->")
PRIVATE_MARK = "<!-- lpwn-snow-private -->"


def api(url, token, method="GET", body=None, auth="Bearer", accept="application/json"):
    data = json.dumps(body).encode() if body is not None else None
    hdr = {"Accept": accept, "User-Agent": "laporteweathernow-snow-help"}
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


def clean(t, n=300):
    """Text someone typed, made safe for an issue and the site: one line, no markup, no @-mentions or links."""
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
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else ""


def town_of(s):
    return next((t for t in TOWNS if t.lower() == str(s or "").strip().lower()), None)


def when_sent(sub):
    return datetime.datetime.fromisoformat(sub["created_at"].replace("Z", "+00:00"))


def fmt(t):
    return t.astimezone(CENTRAL).strftime("%b %-d, %Y, %-I:%M %p %Z")


def day(t):
    return t.astimezone(CENTRAL).strftime("%b %-d, %Y")


def ask_body(sub, d, form_id):
    sent = when_sent(sub)
    lines = [f"<!-- lpwn-snow:{sub['id']} -->",
             "Someone asked for help clearing snow. **Nothing is public until you add the `approve` label,** and even "
             "then only the \"Shown publicly\" lines go on the board. Their name, phone and address are in the first "
             "comment below.", "",
             "### Shown publicly (edit these lines before approving, if you want)",
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
             "**Post it on the board:** add `approve`. **Helper on the way:** add `helper found`. **Cleared:** add `done` "
             "(or close the issue). **Never post it:** add `reject`. **Take it down:** add `unpublish`.",
             "",
             "To connect them, text this person and the helper you pick. Helper sign-ups are issues labeled `snow helper`; "
             "the ones sent for this request show up below.",
             "",
             f"_Their private details are erased on {day(sent + datetime.timedelta(days=ERASE_ASK_DAYS))}._"]
    return "\n".join(lines)


def ask_private(sub, d):
    town = town_of(d.get("town"))
    addr = clean(d.get("address"), 120)
    maps = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{addr}, {town}, IN")
    return "\n".join([PRIVATE_MARK, "### Private: only you can see this",
                      f"- Name: {clean(d.get('name'), 40)}",
                      f"- Phone: {phone(d.get('phone'))}",
                      f"- Address: {addr}, {town}",
                      f"- Map: {maps}",
                      f"- Their note: {clean(d.get('details'), 300) or '(none)'}",
                      f"- Can't safely shovel (age, health or disability): {'yes' if d.get('priority') else 'not checked'}",
                      "- 18 or older: yes. OK to share their first name, address and phone with one helper you pick: yes.",
                      "", "_This comment is deleted automatically when the private details are erased._"])


def helper_body(sub, d, form_id, req_num):
    sent = when_sent(sub)
    lines = [f"<!-- lpwn-snow-helper:{sub['id']} -->",
             "Someone signed up to help clear snow. Private: helper sign-ups are never shown on the site. "
             "Their name and phone are in the first comment below.", "",
             (f"Offering to help with #{req_num}." if req_num else "Signed up for the helper list (any request near them)."),
             "",
             f"- Sent {fmt(sent)} (Netlify submission {sub['id']}: https://app.netlify.com/sites/scoopanddude/forms/{form_id})",
             "",
             "If you pick them, text them and the person who asked. Close this issue when they no longer want to help.",
             "",
             f"_Their private details are erased on {day(sent + datetime.timedelta(days=ERASE_HELP_DAYS))}._"]
    return "\n".join(lines)


def helper_private(sub, d):
    where = "Anywhere in LaPorte County" if str(d.get("town")) == "Anywhere" else town_of(d.get("town"))
    return "\n".join([PRIVATE_MARK, "### Private: only you can see this",
                      f"- Name: {clean(d.get('name'), 60)}",
                      f"- Phone: {phone(d.get('phone'))}",
                      f"- Where they can help: {where}",
                      f"- Has: {HTOOLS[d['tools']]}",
                      f"- Free or paid: {HKIND[d['kind']]}",
                      f"- Business: {clean(d.get('business'), 80) or '(none)'}",
                      f"- Usually free: {clean(d.get('availability'), 120) or '(not given)'}",
                      "- 18 or older: yes. Took the helper pledge and OK'd sharing their name and phone with the person they help: yes.",
                      "", "_This comment is deleted automatically when the private details are erased._"])


def parse_public(body):
    sec = (body or "").split("### Shown publicly", 1)[-1].split("### Not shown", 1)[0]
    out = {}
    for m in re.finditer(r"^- (Town|Clearing|Size|Tools|Pay|When|Priority|Note):[ \t]*(.*)$", sec, re.M):
        v = m.group(2).strip()
        out[m.group(1).lower()] = "" if v.lower() in ("(none)", "(not sure)", "(not given)") else v
    return out


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
    return rec, None


def erase(issue):
    n = issue["number"]
    for c in gh(f"/repos/{QUEUE}/issues/{n}/comments?per_page=100"):
        if PRIVATE_MARK in (c.get("body") or ""):
            gh(f"/repos/{QUEUE}/issues/comments/{c['id']}", "DELETE")
    body = re.sub(r"_Their private details are erased on [^_]*\._", "", issue.get("body") or "").rstrip()
    gh(f"/repos/{QUEUE}/issues/{n}", "PATCH",
       {"body": body + f"\n\n_Private details erased {day(datetime.datetime.now(CENTRAL))}._\n<!-- erased -->"})


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
        m = ASK_MARK.search(i.get("body") or "")
        if m:
            asks[m.group(1)] = i
        m = HELP_MARK.search(i.get("body") or "")
        if m:
            helpers[m.group(1)] = i
    by_num = {i["number"]: i for i in asks.values()}
    forms = {f.get("name"): f for f in api(f"{NETLIFY_API}/sites/{SITE_ID}/forms", NETLIFY)}
    cutoff = now - datetime.timedelta(days=14)
    subs_of = {}

    def submissions(name):
        if name not in subs_of:
            f = forms.get(name)
            subs_of[name] = (f, api(f"{NETLIFY_API}/forms/{f['id']}/submissions?per_page=100", NETLIFY) if f else [])
        return subs_of[name]

    # 1) New requests into the private queue.
    form, subs = submissions(FORM_ASK)
    opened = skipped = 0
    for sub in sorted(subs, key=lambda s: s.get("created_at", "")):
        if sub["id"] in asks or opened >= MAX_NEW or when_sent(sub) < cutoff:
            continue
        d = sub.get("data") or {}
        if (d.get("bot-field") or not d.get("consent_age") or not d.get("consent_share") or not town_of(d.get("town"))
                or d.get("clear") not in CLEAR or d.get("pay") not in PAY or not phone(d.get("phone"))
                or not clean(d.get("address"), 120) or not clean(d.get("name"), 40)):
            skipped += 1
            continue
        title = f"Snow help: {CLEAR[d['clear']]} in {town_of(d.get('town'))} · {WHEN.get(d.get('when'), 'As soon as possible')} · {PAY[d['pay']]}"
        i = gh(f"/repos/{QUEUE}/issues", "POST", {"title": title[:120], "body": ask_body(sub, d, form["id"]), "labels": ["snow help"]})
        gh(f"/repos/{QUEUE}/issues/{i['number']}/comments", "POST", {"body": ask_private(sub, d)})
        asks[sub["id"]] = i
        by_num[i["number"]] = i
        opened += 1

    # 2) Helper sign-ups (private issues only).
    form, subs = submissions(FORM_HELP)
    signed = 0
    for sub in sorted(subs, key=lambda s: s.get("created_at", "")):
        if sub["id"] in helpers or signed >= MAX_NEW or when_sent(sub) < cutoff:
            continue
        d = sub.get("data") or {}
        if (d.get("bot-field") or not d.get("consent_age") or not d.get("consent_pledge") or not phone(d.get("phone"))
                or not clean(d.get("name"), 60) or not (d.get("town") == "Anywhere" or town_of(d.get("town")))
                or d.get("tools") not in HTOOLS or d.get("kind") not in HKIND):
            skipped += 1
            continue
        req = str(d.get("request") or "").strip().lstrip("#")
        req_num = int(req) if req.isdigit() and int(req) in by_num else None
        where = "anywhere" if d.get("town") == "Anywhere" else town_of(d.get("town"))
        title = f"Snow helper{f' for #{req_num}' if req_num else ''}: {where} · {HTOOLS[d['tools']]} · {HKIND[d['kind']].split(' (')[0]}"
        i = gh(f"/repos/{QUEUE}/issues", "POST", {"title": title[:120], "body": helper_body(sub, d, form["id"], req_num), "labels": ["snow helper"]})
        gh(f"/repos/{QUEUE}/issues/{i['number']}/comments", "POST", {"body": helper_private(sub, d)})
        helpers[sub["id"]] = i
        signed += 1

    # 3) Scoop's decisions, onto the board.
    try:
        board = json.load(open(os.path.join(OUT, "snow-help.json"), encoding="utf-8"))
    except Exception:
        board = {}
    live = {r["id"]: r for r in board.get("requests", []) if isinstance(r, dict) and r.get("id")}
    changed = not board.get("ready")

    def labels(i):
        return {l["name"] for l in i.get("labels", [])}

    def comment(n, text):
        gh(f"/repos/{QUEUE}/issues/{n}/comments", "POST", {"body": text})

    def unlabel(n, name):
        try:
            gh(f"/repos/{QUEUE}/issues/{n}/labels/{urllib.parse.quote(name)}", "DELETE")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise

    for i in asks.values():
        L, n, body = labels(i), i["number"], i.get("body") or ""
        if "unpublish" in L or ("reject" in L and "published" in L):
            if live.pop(n, None) is not None:
                changed = True
            unlabel(n, "unpublish")
            unlabel(n, "published")
            comment(n, f"Taken off the board {fmt(now)}.")
            L -= {"unpublish", "published"}
        if "reject" in L and "<!-- rejected -->" not in body:
            comment(n, "Rejected: it won't be posted.")
            gh(f"/repos/{QUEUE}/issues/{n}", "PATCH", {"state": "closed", "state_reason": "not_planned", "body": body + "\n<!-- rejected -->"})
            continue
        if "reject" in L:
            continue
        if "approve" in L and "published" not in L:
            rec, err = record(n, parse_public(body))
            unlabel(n, "approve")
            if err:
                comment(n, err)
                continue
            rec.update({"status": "open", "posted": now.isoformat(timespec="seconds")})
            rec.pop("doneAt", None)
            live[n] = rec
            changed = True
            gh(f"/repos/{QUEUE}/issues/{n}/labels", "POST", {"labels": ["published"]})
            comment(n, f"On the board {fmt(now)}: {PAGE}#req-{n} (add `helper found` when someone's on the way, "
                       "`done` when it's cleared, or `unpublish` to take it down).")
            L |= {"published"}
        if "published" in L and n in live:
            rec = live[n]
            fresh, err = record(n, parse_public(body), rec)       # Scoop may edit the public lines later
            if not err and any(fresh.get(k) != rec.get(k) for k in fresh):
                live[n] = rec = fresh
                changed = True
            status = "done" if ("done" in L or i.get("state") == "closed") else "matched" if "helper found" in L else "open"
            if status != rec.get("status"):
                rec["status"] = status
                if status == "done":
                    rec["doneAt"] = now.isoformat(timespec="seconds")
                    if "done" not in L:
                        gh(f"/repos/{QUEUE}/issues/{n}/labels", "POST", {"labels": ["done"]})
                else:
                    rec.pop("doneAt", None)
                changed = True

    # 4) Off the board: three days after going up, or a day after it was cleared.
    for n, rec in list(live.items()):
        posted = datetime.datetime.fromisoformat(rec.get("posted") or now.isoformat())
        done_at = datetime.datetime.fromisoformat(rec["doneAt"]) if rec.get("doneAt") else None
        if (done_at and now - done_at > datetime.timedelta(hours=DONE_HOURS)) or now - posted > datetime.timedelta(days=BOARD_DAYS):
            del live[n]
            changed = True
            i = by_num.get(n)
            if i and "done" not in labels(i) and i.get("state") != "closed":
                unlabel(n, "published")
                comment(n, "Came off the board after three days. Add `approve` again to put it back up.")

    # 5) Erase private details once they're old enough.
    erased = 0
    netlify_ids = {s["id"] for name in (FORM_ASK, FORM_HELP) for s in submissions(name)[1]}
    for kind, group, days in (("ask", asks, ERASE_ASK_DAYS), ("helper", helpers, ERASE_HELP_DAYS)):
        for sid, i in group.items():
            if erased >= MAX_ERASE:
                break
            made = datetime.datetime.fromisoformat(i["created_at"].replace("Z", "+00:00"))
            if now - made < datetime.timedelta(days=days) or "<!-- erased -->" in (i.get("body") or ""):
                continue
            erase(i)
            if sid in netlify_ids:
                try:
                    api(f"{NETLIFY_API}/submissions/{sid}", NETLIFY, "DELETE")
                except urllib.error.HTTPError as e:
                    if e.code != 404:
                        raise
            erased += 1
    for name, group, days in ((FORM_ASK, asks, ERASE_ASK_DAYS), (FORM_HELP, helpers, ERASE_HELP_DAYS)):
        for s in submissions(name)[1]:             # ones that never made it into the queue (spam, missing boxes)
            if erased < MAX_ERASE and s["id"] not in group and now - when_sent(s) > datetime.timedelta(days=days):
                try:
                    api(f"{NETLIFY_API}/submissions/{s['id']}", NETLIFY, "DELETE")
                except urllib.error.HTTPError as e:
                    if e.code != 404:
                        raise
                erased += 1

    # 6) The season's count of neighbors helped (since July 1).
    start = datetime.datetime(now.year if now.month >= 7 else now.year - 1, 7, 1, tzinfo=CENTRAL)
    helped = sum(1 for i in asks.values()
                 if "done" in labels(i) and datetime.datetime.fromisoformat(i["created_at"].replace("Z", "+00:00")) >= start)
    helped += sum(1 for r in live.values() if r.get("status") == "done" and r["id"] in by_num and "done" not in labels(by_num[r["id"]]))
    if helped != board.get("helped"):
        changed = True
    if changed:
        os.makedirs(OUT, exist_ok=True)
        json.dump({"about": "Snow Help requests approved by Scoop for laporteweathernow.com/snow-help. Town and what's "
                            "needed only: never a name, address or phone number.",
                   "ready": True, "updated": now.isoformat(timespec="seconds"), "helped": helped,
                   "requests": sorted(live.values(), key=lambda r: r.get("posted", ""), reverse=True)},
                  open(os.path.join(OUT, "snow-help.json"), "w", encoding="utf-8"), indent=1)
    print(f"Snow Help: {opened} new requests, {signed} new helpers, {skipped} skipped, {len(live)} on the board, "
          f"{erased} erased, {helped} helped this season.")
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
