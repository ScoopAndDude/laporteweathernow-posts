#!/usr/bin/env python3
"""Starts the jobs that are due, for the "Timer" workflow.

GitHub's own schedules (cron) for this repository have been hours late or missing since
Sept. 29-30, 2026, a GitHub problem others report too. So a clock outside GitHub (a Google Apps
Script trigger in the business Google account) sends a "tick" every 15 minutes, and this script
starts whichever jobs are due at that moment, in La Porte (Central) time:

  every tick           Homepage weather copy, Weather radio
  5:00-5:14 AM         NWS weather snapshot (backup; the morning Scoop task starts its own)
  6:30-8:14 AM         Backup Daily Scoop (it posts only if today's Scoop isn't up)
  8:10-8:24 AM         Site health check
  9:15-9:29 AM, 4:45-4:59 PM   Markets numbers from BLS

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

EVERY_TICK = ["home-cache.yml", "radio.yml"]
WINDOWS = [
    ("nws-snapshot.yml", [("05:00", "05:14")]),
    ("backup-scoop.yml", [("06:30", "08:14")]),
    ("site-health.yml", [("08:10", "08:24")]),
    ("markets-data.yml", [("09:15", "09:29"), ("16:45", "16:59")]),
]


def due(now):
    hm = now.strftime("%H:%M")
    jobs = list(EVERY_TICK)
    for wf, spans in WINDOWS:
        if any(a <= hm <= b for a, b in spans):
            jobs.append(wf)
    return jobs


def dispatch(workflow):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow}/dispatches",
        data=json.dumps({"ref": "main"}).encode(),
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
