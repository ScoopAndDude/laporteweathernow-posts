#!/usr/bin/env python3
"""The watchdog outside Google for the Hard Hat Weather sender (Oct. 11, 2026).

The sender (Google Apps Script, "Hard Hat Weather sender") runs its check every 5 minutes and
sends the 5 AM calls. Inside, it now emails Scoop when a morning call is late or the check keeps
stopping. This covers what it can't see itself: the check not running at all.

It asks the sender's web app (?health: times and counts only, never names) and opens a GitHub
issue here, which GitHub emails to Scoop, when:
  - the check hasn't finished a run in more than 25 minutes (it runs every 5), unless it's paused
    on purpose ("Pause everything" in its Settings tab), or
  - a morning call is late (15 minutes past its send time and not out, and not just waiting on
    the Weather Service), or
  - the web app doesn't answer at all (that also stops sign-ups from reaching the sheet).
It asks 3 times, a minute apart, before deciding, so a hiccup stays quiet. One open issue at a
time; while it stays open it's updated at most every 3 hours; when all is well again, it's closed
with a note (one more email, the good kind).

Started by the Timer at 4:45, 5:15, 5:45, 6:15 and 6:45 AM Central (scripts/timer.py), and by
GitHub's own clock every hour as a backup (sender-watch.yml). Run it by hand with "test_alert" to
get a test email.
"""
import datetime
import json
import os
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

HEALTH = ("https://script.google.com/macros/s/AKfycbyHS9v_eeJ1iZD-taPUmfVHwVmogT1wyP0eUO-pykwJk8pNFngTtuXBgeb6b_TzJ-f2"
          "/exec?health=1")
REPO = os.environ.get("GITHUB_REPOSITORY", "ScoopAndDude/laporteweathernow-posts")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
CENTRAL = ZoneInfo("America/Chicago")
TITLE = "The Hard Hat Weather sender needs a look"
STALE_MINUTES = 25
TRIES, PAUSE = 3, 60
REMIND_HOURS = 3
UA = "LaPorteWeatherNow-senderwatch/1.0 (+https://laporteweathernow.com)"


def fetch_health():
    req = urllib.request.Request(HEALTH, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def problems_in(h):
    """What's wrong, in plain words, from the sender's ?health answer ([] when all is well)."""
    if h.get("paused"):
        return []
    out = []
    mins = h.get("minutesSinceFinished")
    if mins is None:
        out.append("The sender's 5-minute check has no finished run on record.")
    elif mins > STALE_MINUTES:
        hours = f"{mins / 60:.1f} hours" if mins >= 120 else f"{mins} minutes"
        out.append(f"The sender's 5-minute check hasn't finished a run in {hours}, so calls, heads-ups, and warnings "
                   "aren't going out. In the Apps Script editor, check Triggers (the tick trigger every 5 minutes) "
                   "and Executions (errors).")
    m = h.get("morning") or {}
    if m.get("late"):
        out.append(f"{m['late']} of today's {m.get('due', m['late'])} morning calls haven't gone out yet. The sender emailed "
                   "you which ones; the Log tab in the Hard Hat Weather sheet may say why.")
    return out


def gh(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def open_issue():
    for issue in gh("GET", "/issues?state=open&per_page=100") or []:
        if issue.get("title") == TITLE and "pull_request" not in issue:
            return issue
    return None


def last_note_at(issue):
    """When the issue was last told something (created, or its latest comment)."""
    t = issue.get("created_at")
    if issue.get("comments"):
        comments = gh("GET", f"/issues/{issue['number']}/comments?per_page=100") or []
        if comments:
            t = comments[-1].get("created_at") or t
    return datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))


def main():
    now = datetime.datetime.now(CENTRAL)
    stamp = f"{now:%a %b} {now.day}, {now:%I:%M %p} Central".replace(" 0", " ")
    test = os.environ.get("TEST_ALERT") == "true"
    health, problems, error = None, [], None
    for i in range(TRIES):
        try:
            health, error = fetch_health(), None
            problems = problems_in(health)
        except Exception as e:   # no answer, or not JSON
            health, error = None, e
            problems = [f"The sender's web app didn't answer ({e}). That also stops sign-ups from reaching the sheet. "
                        "In the Apps Script editor, check Deploy > Manage deployments and Executions."]
        if not problems:
            break
        if i < TRIES - 1:
            time.sleep(PAUSE)
    print(f"Checked {stamp}: " + (json.dumps(health) if health is not None else f"no answer ({error})"))
    if test:
        problems = ["TEST ONLY, nothing is wrong: this is what an email from the Hard Hat sender watchdog looks like. "
                    "It closes itself."]

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## Hard Hat Weather sender\n\n" + ("\n".join(f"- {p}" for p in problems) if problems else "All well.") + "\n")
    if not TOKEN:
        print("No GitHub token, so no issue: " + (" ".join(problems) or "all well"))
        return 1 if problems else 0

    issue = open_issue()
    if problems:
        for p in problems:
            print(f"::error title=Hard Hat sender::{p}")
        text = f"**{stamp}**\n\n" + "\n".join(f"- {p}" for p in problems)
        if issue is None:
            made = gh("POST", "/issues", {"title": TITLE, "body": "@ScoopAndDude " + text +
                      "\n\nThis closes by itself once the sender is fine again. Opened by the sender watchdog "
                      "(scripts/sender_watch.py)."})
            print(f"Opened issue #{made['number']}.")
            issue = made
        elif datetime.datetime.now(datetime.timezone.utc) - last_note_at(issue) >= datetime.timedelta(hours=REMIND_HOURS):
            gh("POST", f"/issues/{issue['number']}/comments", {"body": "Still the case. " + text})
            print(f"Updated issue #{issue['number']}.")
        else:
            print(f"Issue #{issue['number']} is open and was updated in the last {REMIND_HOURS} hours.")
        if test:
            gh("POST", f"/issues/{issue['number']}/comments", {"body": "Test only: closing."})
            gh("PATCH", f"/issues/{issue['number']}", {"state": "closed"})
            print("Test issue closed.")
            return 0
        return 1
    if issue is not None:
        gh("POST", f"/issues/{issue['number']}/comments", {"body": f"Fine again as of {stamp}: the 5-minute check is running and no morning call is late."})
        gh("PATCH", f"/issues/{issue['number']}", {"state": "closed"})
        print(f"Closed issue #{issue['number']}: fine again.")
    else:
        print("All well.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
