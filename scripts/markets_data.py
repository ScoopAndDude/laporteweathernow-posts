#!/usr/bin/env python3
"""Saves the Markets & Economy numbers for laporteweathernow.com/markets.

Asks the U.S. Bureau of Labor Statistics (BLS) public API for every series in one
request and writes markets-data.json, which the Markets page and the Our Sources page
read. Visitors no longer each ask BLS, so nobody runs into BLS's daily limit
(about 25 requests a day per internet address without a key).

The file is only rewritten when BLS has new or revised numbers, so its history
(github.com/ScoopAndDude/laporteweathernow-posts/commits/main/markets-data.json) shows
every change. If BLS doesn't answer, the file is left alone and the page keeps showing
the last saved numbers.

Optional: a free BLS registration key saved as the repository secret BLS_API_KEY
switches to BLS's v2 API (500 requests a day for the key).
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "markets-data.json")

# Same keys and series as markets.js on the site.
SERIES = {
    "us": "LNS14000000",            # U.S. unemployment rate, seasonally adjusted
    "in": "LASST180000000000003",   # Indiana unemployment rate, seasonally adjusted
    "lp": "LAUCN180910000000003",   # La Porte County unemployment rate, not seasonally adjusted
    "cpi": "CUUR0000SA0",           # Consumer prices, all items (CPI-U)
    "gas": "CUUR0000SETB01",        # Consumer prices, gasoline (all types)
    "food": "CUUR0000SAF11",        # Consumer prices, food at home (groceries)
    "power": "CUUR0000SEHF",        # Consumer prices, household energy
}
KEEP = 25          # months kept per series: this month, last month and a year ago, with room to spare
MIN_SERIES = 4     # the page needs at least this many to be worth showing
STALE_DAYS = 45    # BLS puts out new numbers every month; this long without any means something's wrong


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def fetch_bls():
    year = now_utc().year
    body = {"seriesid": list(SERIES.values()), "startyear": str(year - 2), "endyear": str(year)}
    url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    key = os.environ.get("BLS_API_KEY", "").strip()
    if key:
        url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        body["registrationkey"] = key
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "laporteweathernow.com Markets page"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def clean(series):
    """Monthly values only (no annual averages or blanks), newest first, in BLS's own format."""
    rows = []
    for d in series.get("data") or []:
        period = str(d.get("period", ""))
        if not (len(period) == 3 and period[0] == "M" and period[1:].isdigit() and 1 <= int(period[1:]) <= 12):
            continue
        value = str(d.get("value", "")).strip()
        try:
            float(value)
        except ValueError:
            continue
        rows.append({"year": str(d.get("year", "")), "period": period,
                     "periodName": str(d.get("periodName", "")), "value": value})
    rows = [r for r in rows if r["year"].isdigit()]
    rows.sort(key=lambda r: (int(r["year"]), int(r["period"][1:])), reverse=True)
    return rows[:KEEP]


def load_old():
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
        return old if isinstance(old, dict) and isinstance(old.get("series"), dict) else None
    except (OSError, ValueError):
        return None


def is_stale(old):
    try:
        t = datetime.datetime.fromisoformat(str(old["updated"]).replace("Z", "+00:00"))
        return (now_utc() - t).days > STALE_DAYS
    except (KeyError, TypeError, ValueError):
        return True


def give_up(old, why):
    print(f"::warning::{why}")
    if old is None or is_stale(old):
        print(f"::error::No new Markets numbers saved in over {STALE_DAYS} days (or none yet). "
              "The page is showing old numbers or none.")
        return 1
    print("Keeping the last saved numbers.")
    return 0


def main():
    old = load_old()
    try:
        answer = fetch_bls()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return give_up(old, f"BLS didn't answer: {e}")

    found = {}
    for s in (answer.get("Results") or {}).get("series") or []:
        rows = clean(s)
        if rows:
            found[s.get("seriesID")] = rows
    got = [k for k, sid in SERIES.items() if sid in found]
    if len(got) < MIN_SERIES:
        msg = "; ".join(str(m) for m in (answer.get("message") or []))
        return give_up(old, f"BLS answered {answer.get('status')} with {len(got)} of {len(SERIES)} series. {msg}".strip())

    old_series = (old or {}).get("series") or {}
    series = {}
    for k, sid in SERIES.items():
        if sid in found:
            series[k] = {"seriesID": sid, "data": found[sid]}
        elif k in old_series:
            series[k] = old_series[k]   # BLS left this one out today: keep the last saved numbers
            print(f"::warning::BLS didn't send {sid} ({k}); keeping the last saved numbers for it.")

    latest = {k: f"{v['data'][0]['periodName']} {v['data'][0]['year']}: {v['data'][0]['value']}" for k, v in series.items()}
    if old and old_series == series:
        print("No new numbers. Latest:", json.dumps(latest))
        return 0

    out = {
        "updated": now_utc().isoformat().replace("+00:00", "Z"),
        "source": "U.S. Bureau of Labor Statistics public data API (api.bls.gov)",
        "about": "Saved for laporteweathernow.com/markets. Each series keeps its latest monthly values, "
                 "newest first, in BLS's own format.",
        "series": series,
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, OUT)
    print("Saved new numbers. Latest:", json.dumps(latest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
