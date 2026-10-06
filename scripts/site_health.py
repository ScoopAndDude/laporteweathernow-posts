#!/usr/bin/env python3
"""Daily health check for laporteweathernow.com, saved as health.json.

Checks, in plain words:
- every page in the sitemap (plus the Hard Hat pages) loads, has the site menu, and
  every script/style it loads answers with a version stamp that matches the file;
- the data files the site reads are fresh (today's Daily Scoop, the NWS snapshot, the
  hourly homepage copy, the forecast scorecard, the El Nino file);
- the Daily Scoop's on-time record for the last 14 days (posted by 6:30 AM Central);
- which GitHub jobs failed in the last 7 days.
Anything wrong goes into "problems" in plain English. The weekly check-up reads this.
The ones readers would notice (a page or file down, no Scoop today or only the automatic
backup, a stuck homepage copy, a posts file that won't read) also go into "urgent"; the
workflow then fails on purpose, and GitHub emails Scoop.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..")
OUT = os.path.join(REPO, "health.json")
SITE = "https://laporteweathernow.com"
TZ = ZoneInfo("America/Chicago")
UA = "LaPorteWeatherNow-healthcheck/1.0 (+https://laporteweathernow.com)"
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "ScoopAndDude/laporteweathernow-posts")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
EXTRA_PAGES = ["/", "/hardhat/", "/hardhat/pay", "/hardhat/terms", "/hardhat/privacy", "/hardhat/thanks"]
ASSET_RE = re.compile(r'(?:src|href)="((?:/|\.\./)?[A-Za-z0-9_\-./]+\.(?:js|css|png|svg|ico|json)\?v=([0-9a-f]{10}))"')

problems = []
urgent = []     # readers would notice (a page or file down, no Scoop today)
stuck = []      # a job that keeps the site fresh has stopped (readers may not notice yet)


def problem(text, is_urgent=False):
    problems.append(text)
    if is_urgent:
        urgent.append(text)


def stuck_job(text):
    problems.append(text)
    stuck.append(text)


def fetch(url, tries=2, headers=None):
    last = None
    for i in range(tries):
        try:
            h = {"User-Agent": UA}
            h.update(headers or {})
            t0 = time.time()
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
                return r.status, r.read(), round((time.time() - t0) * 1000)
        except urllib.error.HTTPError as e:
            return e.code, b"", 0
        except Exception as e:
            last = e
            time.sleep(3)
    return 0, str(last).encode(), 0


def now():
    return datetime.datetime.now(TZ).replace(microsecond=0)


def age_hours(iso):
    try:
        return round((now() - datetime.datetime.fromisoformat(iso)).total_seconds() / 3600, 1)
    except Exception:
        return None


def check_pages():
    status, body, _ = fetch(f"{SITE}/sitemap.xml")
    paths = []
    if status == 200:
        paths = [re.sub(r"^https?://[^/]+", "", u) or "/" for u in re.findall(r"<loc>([^<]+)</loc>", body.decode("utf-8", "replace"))]
    else:
        problem(f"The sitemap didn't load (status {status}).")
    for p in EXTRA_PAGES:
        if p not in paths:
            paths.append(p)
    pages, assets = [], {}
    for p in paths:
        status, body, ms = fetch(SITE + p)
        text = body.decode("utf-8", "replace")
        row = {"path": p, "status": status, "ms": ms,
               "fingerprint": hashlib.sha256(body).hexdigest()[:10] if status == 200 else None,
               "groupedMenu": 'class="nav-group"' in text}
        if status != 200:
            problem(f"Page {p} didn't load (status {status}).", True)
        elif not p.startswith(("/hardhat", "/farm")) and '<nav class="nav"' not in text:   # Hard Hat and Field Day pages have their own header
            problem(f"Page {p} is missing the site menu.", True)
        for ref, stamp in ASSET_RE.findall(text):
            base = p if p.endswith("/") else p.rsplit("/", 1)[0] + "/"
            url = SITE + (ref if ref.startswith("/") else base + ref)
            url = re.sub(r"/[^/]+/\.\./", "/", url)
            assets.setdefault(url, {"stamp": stamp, "pages": []})["pages"].append(p)
        pages.append(row)
    checked = []
    for url, info in sorted(assets.items()):
        status, body, _ = fetch(url)
        real = hashlib.sha256(body).hexdigest()[:10] if status == 200 else None
        ok = status == 200 and real == info["stamp"]
        checked.append({"url": url.replace(SITE, ""), "status": status, "stampOk": ok})
        if status != 200:
            problem(f"{url.replace(SITE, '')} didn't load (status {status}), used by {', '.join(info['pages'][:3])}.", True)
        elif not ok:
            problem(f"{url.replace(SITE, '').split('?')[0]} has a version stamp that doesn't match the file (visitors may get an old copy).", True)
    return pages, checked


def check_data():
    out = {}
    today = now().date().isoformat()
    try:
        posts = json.load(open(os.path.join(REPO, "scoop-posts.json"), encoding="utf-8")).get("posts") or []
        daily = [p for p in posts if p.get("type") == "daily"]
        latest = daily[0] if daily else {}
        out["latestScoop"] = {"date": latest.get("date"), "posted": latest.get("posted"), "automatic": bool(latest.get("auto"))}
        if latest.get("date") != today and now().hour >= 7:
            problem(f"There's no Daily Scoop for today ({today}); the newest is {latest.get('date')}.", True)
        elif latest.get("date") == today and latest.get("auto"):
            problem("Today's Daily Scoop is the automatic NWS backup: the morning Scoop task didn't post by 6:30 AM.", True)
        record = []
        for i in range(14):
            d = (now().date() - datetime.timedelta(days=i)).isoformat()
            p = next((x for x in daily if x.get("date") == d), None)
            if not p:
                record.append({"date": d, "result": "missing"})
                continue
            stamp = p.get("posted") or p.get("updated")
            if not stamp:
                record.append({"date": d, "result": "unknown"})
                continue
            posted = datetime.datetime.fromisoformat(stamp).astimezone(TZ)
            result = "backup" if p.get("auto") else "on time" if (posted.hour, posted.minute) <= (6, 30) else "late"
            record.append({"date": d, "result": result, "posted": posted.strftime("%H:%M")})
        out["scoopLast14"] = {"onTime": sum(r["result"] == "on time" for r in record),
                              "late": sum(r["result"] == "late" for r in record),
                              "backup": sum(r["result"] == "backup" for r in record),
                              "missing": sum(r["result"] == "missing" for r in record), "days": record}
    except Exception as e:
        problem(f"Couldn't read scoop-posts.json: {e}", True)
    for name, key, limit in (("nws-snapshot.json", "fetched", 26), ("scorecard.json", "generated", 26)):
        try:
            h = age_hours(json.load(open(os.path.join(REPO, name), encoding="utf-8")).get(key))
            out[name] = {"ageHours": h}
            if h is None or h > limit:
                problem(f"{name} is {h} hours old (should be under {limit}).")
        except Exception as e:
            problem(f"Couldn't read {name}: {e}")
    try:
        ww = json.load(open(os.path.join(REPO, "world-watch.json"), encoding="utf-8"))
        days = (now().date() - datetime.date.fromisoformat(ww.get("updated"))).days
        out["world-watch.json"] = {"updated": ww.get("updated"), "ageDays": days}
        if days > 8:
            problem(f"The El Nino numbers (world-watch.json) are {days} days old; the weekly update may have stopped.")
    except Exception as e:
        problem(f"Couldn't read world-watch.json: {e}")
    status, body, _ = fetch(f"https://raw.githubusercontent.com/{REPO_NAME}/live/home.json")
    try:
        h = age_hours(json.loads(body).get("fetched")) if status == 200 else None
        out["home.json"] = {"status": status, "ageHours": h}
        if h is None or h > 3:
            # Readers only see this copy when NWS is down, so it's a stuck job, not a page problem.
            stuck_job(f"The homepage's backup weather copy is {h} hours old (status {status}); the 'Homepage weather copy' job may be stuck.")
    except Exception as e:
        problem(f"Couldn't read the homepage weather copy: {e}", True)
    # Weather radio: re-recorded whenever the broadcast changes (the airport reading alone changes it
    # every hour). Not urgent: the Alerts page's player uses the device's own voice when it's old.
    status, body, _ = fetch(f"https://raw.githubusercontent.com/{REPO_NAME}/radio/radio.json")
    try:
        h = age_hours(json.loads(body).get("recorded")) if status == 200 else None
        out["radio.json"] = {"status": status, "ageHours": h}
        if h is None or h > 4:
            stuck_job(f"The weather radio recording is {h} hours old (status {status}); the 'Weather radio' job may be stuck. "
                      "(The Alerts page reads the latest in the phone's own voice meanwhile.)")
    except Exception as e:
        problem(f"Couldn't read the weather radio recording: {e}")
    # The Chase (camp map): weekly fuel prices and map squares. Readers still get the older copy
    # (each shows its date), so a late update is a stuck job, not a page problem.
    try:
        fp = json.load(open(os.path.join(REPO, "fuel-prices.json"), encoding="utf-8"))
        days = (now().date() - datetime.date.fromisoformat(fp.get("week"))).days
        out["fuel-prices.json"] = {"week": fp.get("week"), "ageDays": days}
        if days > 13:   # EIA's week starts Monday; it's normally saved by Tuesday night, holidays add a day or two
            stuck_job(f"The Chase's fuel prices are for the week of {fp.get('week')} ({days} days ago); the weekly 'Fuel prices' job may be stuck.")
    except Exception as e:
        problem(f"Couldn't read fuel-prices.json: {e}")
    try:
        idx = json.load(open(os.path.join(REPO, "tiles", "index.json"), encoding="utf-8"))
        h = age_hours(idx.get("made"))
        out["tiles/index.json"] = {"made": idx.get("made"), "dataFrom": idx.get("built"), "ageDays": round(h / 24, 1) if h is not None else None}
        if h is None or h > 10 * 24:
            stuck_job(f"The Chase's map squares were last built {round(h / 24) if h is not None else '?'} days ago; the weekly "
                      "'Camp map places from OpenStreetMap' job may be stuck. (The map still works from the older copy.)")
    except Exception as e:
        problem(f"Couldn't read The Chase's map squares (tiles/index.json): {e}")
    status, body, _ = fetch(f"https://scoopanddude.github.io/{REPO_NAME.split('/')[1]}/tiles/index.json")
    out["tiles on GitHub Pages"] = {"status": status}
    if status != 200:
        problem(f"GitHub Pages didn't serve The Chase's map squares (status {status}); the map is using the backup copy or Overpass.")
    return out


def check_actions():
    """Failed GitHub jobs in the last 7 days, and when the outside clock last ticked."""
    if not TOKEN:
        return None
    auth = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    # The timer starts runs all day long, so ask GitHub for the failures only (the full list is too long).
    status, body, _ = fetch(f"https://api.github.com/repos/{REPO_NAME}/actions/runs?status=failure&per_page=100&created=>={since}", headers=auth)
    if status != 200:
        return {"error": f"status {status}"}
    # This check's own runs fail on purpose when something needs a look (that's the email), so they don't count.
    runs = [r for r in json.loads(body).get("workflow_runs") or [] if r.get("name") != "Site health check"]
    by_name = {}
    for r in runs:
        by_name[r["name"]] = by_name.get(r["name"], 0) + 1
    for name, n in by_name.items():
        problem(f"GitHub job '{name}' failed {n} time{'s' if n != 1 else ''} in the last 7 days.")
    # The outside clock (Apps Script "LPWN timer") sends a tick every 15 minutes. Once it has
    # started, a long silence means it stopped (usually an expired GitHub key).
    status, body, _ = fetch(f"https://api.github.com/repos/{REPO_NAME}/actions/workflows/timer.yml/runs?event=repository_dispatch&per_page=1", headers=auth)
    last_tick = None
    try:
        tick_runs = json.loads(body).get("workflow_runs") or [] if status == 200 else []
        if tick_runs:
            last_tick = tick_runs[0]["created_at"]
            h = round((datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(last_tick.replace("Z", "+00:00"))).total_seconds() / 3600, 1)
            if h > 2:
                stuck_job(f"The outside clock (Apps Script 'LPWN timer') last ticked {h} hours ago; its GitHub key may have expired.")
    except Exception as e:
        problem(f"Couldn't read the timer's runs: {e}")
    return {"failedLast7days": by_name, "failures": [{"name": r["name"], "when": r["created_at"], "url": r["html_url"]} for r in runs[:20]],
            "lastTick": last_tick}


def main():
    pages, assets = check_pages()
    data = check_data()
    actions = check_actions()
    report = {
        "about": "Daily health check for laporteweathernow.com (scripts/site_health.py). 'problems' lists anything to fix, in plain English.",
        "checked": now().isoformat(),
        "ok": not problems,
        "problems": problems,
        "urgent": urgent,
        "stuck": stuck,
        "pages": pages,
        "assets": {"checked": len(assets), "notOk": [a for a in assets if a["status"] != 200 or not a["stampOk"]]},
        "data": data,
        "githubJobs": actions,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"{len(pages)} pages, {len(assets)} files checked; {len(problems)} problem(s), {len(urgent)} urgent, {len(stuck)} stuck job(s).")
    for p in problems:
        print("  -", p)


if __name__ == "__main__":
    main()
