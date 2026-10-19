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
  5:20 and 6:20 AM (each for 15 minutes)   The Sky Devotion for La Porte (added Oct. 6, 2026; the first start
                       picks today's devotion, the second does nothing once it's saved)
  5:30, 6:30 and 7:30 AM (each for 15 minutes)   The Forecast Race (added Oct. 6, 2026; saves this morning's
                       forecasts and grades yesterday's; later starts only fill in a racer that didn't answer)
  6:00 and 6:45 AM (each for 15 minutes)   The Daily Video (added Oct. 8, 2026; the first start makes and
                       posts the day's forecast video, the second does nothing once it's made)
  4:45, 5:15, 5:45, 6:15 and 6:45 AM (each for 15 minutes)   The Hard Hat sender watch (added Oct. 11,
                       2026; asks the 5 AM sender whether it's running and whether any morning call is late)
  5:30-6:14 AM (every tick), 7:00 and 9:00 AM (each for 15 minutes)   The Daily Scoop writer (added Oct. 18,
                       2026; no AI: it posts today's Scoop once, and does nothing after that)
  6:30-8:09 AM         Backup Daily Scoop (it posts only if today's Scoop isn't up)
  8:10-8:24 AM         Site health check
  9:15-9:29 AM, 4:45-4:59 PM   Markets numbers from BLS
  Monday 3:15-3:29 AM and 3:15-3:29 PM   The Chase's map squares (the second start only builds
                       if the first didn't; see places.yml)
  Tuesday 5:45-5:59 PM, Wednesday and Thursday 9:45-9:59 AM   The Chase's fuel prices from EIA
                       (saved only when EIA has a new week)
  4:30-8:30 AM weekdays, 8:00 PM Sunday-Thursday   School closings (added Oct. 17, 2026; checks the
                       school sites Nov.-Mar. only, 3 times per tick)
  every tick           Readers' reports queue (added Oct. 17, 2026; once it's set up)
  every tick           Morning forecast email (U.S.-wide, 6 AM each subscriber's time) and Warning emails
                       (a new NWS warning at a subscriber's spot), both added Oct. 17, 2026
  every 3 hours from 12:35 AM (12:35, 3:35, 6:35 ...)   Earth from space data (NASA FIRMS fires,
                       CelesTrak weather satellites) for the disasters page
  7:00 AM and 5:00 PM (each for 15 minutes)   First snow check (added Oct. 19, 2026; emails Scoop once a
                       winter when snow first shows up in the NWS forecast for La Porte County)
  every hour, :20-:34  Storm grid (Hard Hat storm records and job-site rain; NOAA radar and snowfall analysis
                       for NW Indiana and SW Michigan on the storm-grid branch; no customer locations)

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

EVERY_TICK = ["home-cache.yml", "radio.yml", "scoop-update.yml", "scoop-pages.yml", "snow-totals.yml",
              "reports.yml",   # reports.yml (Oct. 17, 2026): readers' reports queue; does nothing until set up
              "morning-email.yml",   # morning email (Oct. 17, 2026): sends to whoever's 6 AM it is, U.S.-wide
              "warning-email.yml"]   # warning emails (Oct. 17, 2026): a NEW NWS warning at a subscriber's spot
# (workflow, [(from, to), ...], days): days are Python weekdays (Monday is 0); None means every day.
WINDOWS = [
    ("nws-snapshot.yml", [("05:00", "05:14")], None),
    ("shore-call.yml", [("05:30", "05:44"), ("06:30", "06:44"), ("07:30", "07:44")], None),
    ("sky-devotion.yml", [("05:20", "05:34"), ("06:20", "06:34")], None),
    ("forecast-race.yml", [("05:30", "05:44"), ("06:30", "06:44"), ("07:30", "07:44")], None),
    ("school-call.yml", [("20:00", "20:14"), ("21:00", "21:14")], {6, 0, 1, 2, 3}),
    # School closings (Oct. 17, 2026): every tick 4:30-8:30 AM on weekdays (it checks 3 times per tick and
    # does nothing outside Nov.-Mar.), plus 8:00 PM Sunday-Thursday to learn the pages and start the day empty.
    ("closings.yml", [("04:30", "08:29")], {0, 1, 2, 3, 4}),
    ("closings.yml", [("20:00", "20:14")], {6, 0, 1, 2, 3}),
    ("daily-video.yml", [("06:00", "06:14"), ("06:45", "06:59")], None),
    ("sender-watch.yml", [("04:45", "04:59"), ("05:15", "05:29"), ("05:45", "05:59"), ("06:15", "06:29"), ("06:45", "06:59")], None),
    # The Daily Scoop writer (Oct. 18, 2026): no AI; posts once, after the 5 a.m. snapshot, and does nothing after that.
    ("scoop-writer.yml", [("05:30", "06:14"), ("07:00", "07:14"), ("09:00", "09:14")], None),
    ("backup-scoop.yml", [("06:30", "08:09")], None),
    ("site-health.yml", [("08:10", "08:24")], None),
    ("markets-data.yml", [("09:15", "09:29"), ("16:45", "16:59")], None),
    ("places.yml", [("03:15", "03:29"), ("15:15", "15:29")], {0}),
    ("fuel-prices.yml", [("17:45", "17:59")], {1}),
    ("fuel-prices.yml", [("09:45", "09:59")], {2, 3}),
    ("space-data.yml", [(f"{h:02d}:35", f"{h:02d}:49") for h in range(0, 24, 3)], None),
    # First snow check (Oct. 19, 2026): after the NWS's overnight and afternoon forecasts; emails once a winter.
    ("first-snow.yml", [("07:00", "07:14"), ("17:00", "17:14")], None),
    # Storm grid (Hard Hat storm records): every hour, after NOAA's Pass 1 radar (about 15 minutes after the hour).
    ("storm-grid.yml", [(f"{h:02d}:20", f"{h:02d}:34") for h in range(24)], None),
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
