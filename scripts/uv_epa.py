"""EPA UV Index for La Porte (ZIP 46350): the daily peak and the hourly forecast, saved as uv.json
on the live branch by the every-15-minutes "Homepage weather copy" job (Oct. 17, 2026).

The site's /air-quality page and homepage card read the hourly hours ("sunscreen 11 a.m. to 3 p.m.")
from this copy instead of asking EPA from every visitor's browser: when EPA's hourly service has nothing
(it answered "not found" for every ZIP on Oct. 17, 2026), the browser would log an error on each page view.
Here a miss is just "hours": [] and the page leaves the hours out. No key needed.
Never fails the job: if EPA can't be reached at all, the last copy is kept.
"""
import datetime, json, sys, urllib.error, urllib.request
from zoneinfo import ZoneInfo

ZIP = "46350"
TZ = ZoneInfo("America/Chicago")
HOSTS = ["https://data.epa.gov/dmapservice", "https://data.epa.gov/efservice"]   # documented host first
LAST = "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/live/uv.json"
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()


def ask(kind):
    """(status, rows): status 'ok', 'none' (EPA answered but has no results) or 'down' (couldn't reach it)."""
    status = "down"
    for host in HOSTS:
        url = f"{host}/getEnvirofacts{kind}/ZIP/{ZIP}/JSON"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "laporteweathernow.com (UV copy)"})
            with urllib.request.urlopen(req, timeout=25) as r:
                rows = json.load(r)
            if isinstance(rows, list) and rows:
                return "ok", rows
            status = "none"
        except urllib.error.HTTPError as e:
            if e.code == 404:   # EPA's "The UV results could not be found for that location."
                status = "none"
        except Exception:
            pass
    return status, []


def hour_of(s):
    """EPA hourly times look like "OCT/17/2026 01 PM" (local time)."""
    try:
        d, hh, ap = str(s).upper().split()
        mon, day, year = d.split("/")
        h = int(hh) % 12 + (12 if ap == "PM" else 0)
        return f"{year}-{MONTHS.index(mon) + 1:02d}-{day}", h
    except Exception:
        return None


def main():
    now = datetime.datetime.now(TZ)
    out = {"zip": ZIP, "fetched": now.isoformat(timespec="minutes"), "date": now.strftime("%Y-%m-%d"),
           "daily": None, "hours": [], "hourly_status": None, "source": "EPA UV Index forecast (data.epa.gov Envirofacts)"}
    ds, drows = ask("UVDAILY")
    if ds == "ok":
        r = drows[0]
        try:
            out["daily"] = {"index": int(float(r.get("UV_INDEX"))), "alert": str(r.get("UV_ALERT")) == "1", "date": r.get("DATE")}
        except Exception:
            ds = "none"
    hs, hrows = ask("UVHOURLY")
    out["hourly_status"] = hs
    for r in hrows:
        t = hour_of(r.get("DATE_TIME"))
        try:
            v = int(float(r.get("UV_VALUE")))
        except Exception:
            continue
        if t and t[0] == out["date"]:
            out["hours"].append({"hour": t[1], "uv": v})
    out["hours"].sort(key=lambda x: x["hour"])
    if ds == "down" and hs == "down":
        # EPA unreachable: keep the last copy so the site still has today's hours if it had them.
        try:
            with urllib.request.urlopen(LAST, timeout=20) as r:
                last = json.load(r)
            with open("uv.json", "w") as fh:
                json.dump(last, fh, indent=1)
            print("EPA UV unreachable; kept the last copy from", last.get("fetched"))
        except Exception:
            print("EPA UV unreachable and no last copy; uv.json not written")
        return
    with open("uv.json", "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"UV daily: {out['daily']}; hourly: {hs}, {len(out['hours'])} hours for {out['date']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # never fail the homepage copy job over UV
        print("UV copy skipped:", e)
    sys.exit(0)
