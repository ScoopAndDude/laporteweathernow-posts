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
        problems.append(f"The sitemap didn't load (status {status}).")
    for p in EXTRA_PAGES:
        if p not in paths:
            paths.append(p)
    pages, assets = [], {}
    for p in paths:
        status, body, ms = fetch(SITE + p)
        text = body.decode("utf-8", "replace")
        row = {"path": p, "status": status, "ms": ms}
        if status != 200:
            problems.append(f"Page {p} didn't load (status {status}).")
        elif not p.startswith("/hardhat") and '<nav class="nav"' not in text:
            problems.append(f"Page {p} is missing the site menu.")
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
            problems.append(f"{url.replace(SITE, '')} didn't load (status {status}), used by {', '.join(info['pages'][:3])}.")
        elif not ok:
            problems.append(f"{url.replace(SITE, '').split('?')[0]} has a version stamp that doesn't match the file (visitors may get an old copy).")
    return pages, checked


def check_data():
    out = {}
    today = now().date().isoformat()
    try:
        posts = json.load(open(os.path.join(REPO, "scoop-posts.json"), encoding="utf-8")).get("posts") or []
        daily = [p for p in posts if p.get("type") == "daily"]
        latest = daily[0] if daily else {}
        out["latestScoop"] = {"date": latest.get("date"), "posted": latest.get("posted")}
        if latest.get("date") != today and now().hour >= 7:
            problems.append(f"There's no Daily Scoop for today ({today}); the newest is {latest.get('date')}.")
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
            record.append({"date": d, "result": "on time" if (posted.hour, posted.minute) <= (6, 30) else "late",
                           "posted": posted.strftime("%H:%M")})
        out["scoopLast14"] = {"onTime": sum(r["result"] == "on time" for r in record),
                              "late": sum(r["result"] == "late" for r in record),
                              "missing": sum(r["result"] == "missing" for r in record), "days": record}
    except Exception as e:
        problems.append(f"Couldn't read scoop-posts.json: {e}")
    for name, key, limit in (("nws-snapshot.json", "fetched", 26), ("scorecard.json", "generated", 26)):
        try:
            h = age_hours(json.load(open(os.path.join(REPO, name), encoding="utf-8")).get(key))
            out[name] = {"ageHours": h}
            if h is None or h > limit:
                problems.append(f"{name} is {h} hours old (should be under {limit}).")
        except Exception as e:
            problems.append(f"Couldn't read {name}: {e}")
    try:
        ww = json.load(open(os.path.join(REPO, "world-watch.json"), encoding="utf-8"))
        days = (now().date() - datetime.date.fromisoformat(ww.get("updated"))).days
        out["world-watch.json"] = {"updated": ww.get("updated"), "ageDays": days}
        if days > 8:
            problems.append(f"The El Nino numbers (world-watch.json) are {days} days old; the weekly update may have stopped.")
    except Exception as e:
        problems.append(f"Couldn't read world-watch.json: {e}")
    status, body, _ = fetch(f"https://raw.githubusercontent.com/{REPO_NAME}/live/home.json")
    try:
        h = age_hours(json.loads(body).get("fetched")) if status == 200 else None
        out["home.json"] = {"status": status, "ageHours": h}
        if h is None or h > 3:
            problems.append(f"The homepage's hourly weather copy is {h} hours old (status {status}); the 'Homepage weather copy' job may be stuck.")
    except Exception as e:
        problems.append(f"Couldn't read the homepage weather copy: {e}")
    return out


def check_actions():
    if not TOKEN:
        return None
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    status, body, _ = fetch(f"https://api.github.com/repos/{REPO_NAME}/actions/runs?per_page=100&created=>={since}",
                            headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})
    if status != 200:
        return {"error": f"status {status}"}
    runs = json.loads(body).get("workflow_runs") or []
    failed = [{"name": r["name"], "when": r["created_at"], "url": r["html_url"]} for r in runs if r.get("conclusion") == "failure"]
    by_name = {}
    for r in runs:
        by_name.setdefault(r["name"], {"runs": 0, "failed": 0})
        by_name[r["name"]]["runs"] += 1
        by_name[r["name"]]["failed"] += 1 if r.get("conclusion") == "failure" else 0
    for name, c in by_name.items():
        if c["failed"]:
            problems.append(f"GitHub job '{name}' failed {c['failed']} of {c['runs']} times in the last 7 days.")
    return {"last7days": by_name, "failures": failed[:20]}


def main():
    pages, assets = check_pages()
    data = check_data()
    actions = check_actions()
    report = {
        "about": "Daily health check for laporteweathernow.com (scripts/site_health.py). 'problems' lists anything to fix, in plain English.",
        "checked": now().isoformat(),
        "ok": not problems,
        "problems": problems,
        "pages": pages,
        "assets": {"checked": len(assets), "notOk": [a for a in assets if a["status"] != 200 or not a["stampOk"]]},
        "data": data,
        "githubJobs": actions,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"{len(pages)} pages, {len(assets)} files checked; {len(problems)} problem(s).")
    for p in problems:
        print("  -", p)


if __name__ == "__main__":
    main()
