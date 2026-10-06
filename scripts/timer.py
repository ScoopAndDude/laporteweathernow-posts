#!/usr/bin/env python3
"""Starts the jobs that are due, for the "Timer" workflow.

GitHub's own schedules (cron) for this repository have been hours late or missing since
Sept. 29-30, 2026, a GitHub problem others report too. So a clock outside GitHub (a Google Apps
Script trigger in the business Google account) sends a "tick" every 15 minutes, and this script
starts whichever jobs are due at that moment, in La Porte (Central) time:

  every tick           Homepage weather copy, Weather radio, Daily Scoop updates, Daily Scoop pages
                       (added Oct. 6, 2026; it only saves pages that changed), Snow totals (it only asks
                       for reports once an hour October-May and once a day in summer)
  5:00-5:14 AM         NWS weather snapshot (backup; the morning Scoop task starts its own)
  5:30, 6:30 and 7:30 AM (each for 15 minutes)   The Shore Call (added Oct. 6, 2026; the first start
                       makes the day's call, the later ones only try again if it couldn't)
  Sunday-Thursday 8:00 and 9:00 PM   The School Delay Watch's record (added Oct. 6, 2026; saves the call
                       for the next school morning; the 9:00 start only tries again if 8:00 couldn't)
  6:30-8:09 AM         Backup Daily Scoop (it posts only if today's Scoop isn't up)
  8:10-8:24 AM         Site health check
  9:15-9:29 AM, 4:45-4:59 PM   Markets numbers from BLS
  Monday 3:15-3:29 AM and 3:15-3:29 PM   The Chase's map squares (the second start only builds
                       if the first didn't; see places.yml)
  Tuesday 5:45-5:59 PM, Wednesday and Thursday 9:45-9:59 AM   The Chase's fuel prices from EIA
                       (saved only when EIA has a new week)
  every 3 hours from 12:35 AM (12:35, 3:35, 6:35 ...)   Earth from space data (NASA FIRMS fires,
                       CelesTrak weather satellites) for the disasters page

The jobs keep their GitHub schedules too, so if GitHub's clock recovers, a job may run twice;
each one is safe to run twice.
"""
import datetime
import json
import os
import sys
import urllib.request
from zoneinfo import ZoneInfo

REPO = os.environ.get("GITHUB_REPOSITORY", "ScoopAndDude/laporteweathernow-posts")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
CENTRAL = ZoneInfo("America/Chicago")

EVERY_TICK = ["home-cache.yml", "radio.yml", "scoop-update.yml", "scoop-pages.yml", "snow-totals.yml"]
# (workflow, [(from, to), ...], days): days are Python weekdays (Monday is 0); None means every day.
WINDOWS = [
    ("nws-snapshot.yml", [("05:00", "05:14")], None),
    ("shore-call.yml", [("05:30", "05:44"), ("06:30", "06:44"), ("07:30", "07:44")], None),
    ("school-call.yml", [("20:00", "20:14"), ("21:00", "21:14")], {6, 0, 1, 2, 3}),
    ("backup-scoop.yml", [("06:30", "08:09")], None),
    ("site-health.yml", [("08:10", "08:24")], None),
    ("markets-data.yml", [("09:15", "09:29"), ("16:45", "16:59")], None),
    ("places.yml", [("03:15", "03:29"), ("15:15", "15:29")], {0}),
    ("fuel-prices.yml", [("17:45", "17:59")], {1}),
    ("fuel-prices.yml", [("09:45", "09:59")], {2, 3}),
    ("space-data.yml", [(f"{h:02d}:35", f"{h:02d}:49") for h in range(0, 24, 3)], None),
]


def due(now):
    hm = now.strftime("%H:%M")
    jobs = list(EVERY_TICK)
    for wf, spans, days in WINDOWS:
        if (days is None or now.weekday() in days) and any(a <= hm <= b for a, b in spans) and wf not in jobs:
            jobs.append(wf)
    return jobs


# The daily site check started by the timer is the one that emails Scoop about problems.
INPUTS = {"site-health.yml": {"alert": "true"}}


def dispatch(workflow):
    body = {"ref": "main"}
    if workflow in INPUTS:
        body["inputs"] = INPUTS[workflow]
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow}/dispatches",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def main():
    now = datetime.datetime.now(CENTRAL)
    jobs = due(now)
    print(f"Tick at {now:%I:%M %p} Central: starting {', '.join(jobs)}.")
    failed = []
    for wf in jobs:
        try:
            status = dispatch(wf)
            print(f"  {wf}: started ({status})")
        except Exception as e:
            print(f"  {wf}: couldn't start ({e})")
            failed.append(wf)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
