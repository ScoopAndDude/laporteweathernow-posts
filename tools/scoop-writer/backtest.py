#!/usr/bin/env python3
"""Run the no-AI Scoop writer (scripts/scoop_writer.py) on past mornings, from git history, posting nothing.

For each date it takes the files as they stood at 5:31 a.m. Central that morning: the 5 a.m. NWS snapshot,
scoop-posts.json, scorecard.json and scoop-updates.json. Then it writes what the robot would have posted,
next to the post that actually went out that day.

  python3 tools/scoop-writer/backtest.py 2026-10-09 2026-10-18 [--out FILE.json] [--at 05:31]

Needs history back to the first date (git fetch --shallow-since=<date> origin main).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import scoop_writer as sw  # noqa: E402

REF = "origin/main"


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, check=True).stdout


def at(rev, path, default):
    try:
        return json.loads(git("show", f"{rev}:{path}"))
    except Exception:
        return default


def morning(date, hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.datetime(date.year, date.month, date.day, h, m, tzinfo=sw.TZ)


def run(day, hhmm):
    now = morning(day, hhmm)
    rev = git("rev-list", "-1", f"--before={now.isoformat()}", REF).strip()
    if not rev:
        return {"date": day.isoformat(), "error": "no history this far back"}
    snap = at(rev, "nws-snapshot.json", {})
    out = {"date": day.isoformat(), "rev": rev[:8], "snapshot": snap.get("fetched")}
    snap_ok = False
    try:
        snap_ok = sw.parse(snap["fetched"]).astimezone(sw.TZ).date() == day
    except Exception:
        pass
    if not snap_ok:
        out["error"] = f"no snapshot from that morning by {hhmm} (newest: {snap.get('fetched')})"
        return out
    try:
        made = sw.build_post(snap, at(rev, "scoop-posts.json", {"posts": []}), at(rev, "scorecard.json", {}),
                             at(rev, "scoop-updates.json", {}), now)
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out
    out.update(made)
    actual = next((p for p in at(REF, "scoop-posts.json", {"posts": []})["posts"]
                   if p.get("type", "daily") == "daily" and p.get("date") == day.isoformat()), None)
    if actual:
        out["actual"] = {k: actual.get(k) for k in ("posted", "title", "summary", "body", "forecasts")}
        out["actual"]["auto"] = bool(actual.get("auto"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("first")
    ap.add_argument("last")
    ap.add_argument("--out")
    ap.add_argument("--at", default="05:31")
    a = ap.parse_args()
    d, last = datetime.date.fromisoformat(a.first), datetime.date.fromisoformat(a.last)
    results = []
    while d <= last:
        results.append(run(d, a.at))
        d += datetime.timedelta(days=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=1)
    for r in results:
        print("=" * 100)
        if r.get("error"):
            print(r["date"], "ERROR:", r["error"])
            continue
        p = r["post"]
        print(f"{r['date']}  ({r['words']} words, snapshot {r['snapshot']})")
        print("TITLE:", p["title"], f"[{len(p['title'])}]")
        print("SUMMARY:", p["summary"])
        for i, b in enumerate(p["body"], 1):
            print(f"P{i} ({sw.words(b)}w): {b}")
        print("FORECASTS:", json.dumps(p["forecasts"]), "| SOURCES:", len(p["sources"]))
        if r.get("notes"):
            print("NOTES:", "; ".join(r["notes"]))
        if r.get("actual"):
            act = r["actual"]
            print(f"-- ACTUAL ({'automatic NWS backup' if act['auto'] else 'AI-written'}, posted {act['posted']}): {act['title']}")
            print("   forecasts:", json.dumps(act["forecasts"]))


if __name__ == "__main__":
    main()
