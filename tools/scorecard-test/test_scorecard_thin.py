"""Offline test of scripts/scorecard.py with the real IEM numbers for Sept. 20-Oct. 11, 2026
(fetched Oct. 11 through a browser). Usage: python3 -I test_scorecard_thin.py <posts repo> <fixture.json>"""
import datetime, importlib.util, json, os, re, shutil, sys, tempfile

repo, fixture = sys.argv[1], sys.argv[2]
fx = json.load(open(fixture))
tmp = tempfile.mkdtemp()
for f in ("scoop-posts.json", "morning-log.json"):
    shutil.copy(os.path.join(repo, f), tmp)
spec = importlib.util.spec_from_file_location("scorecard", os.path.join(repo, "scripts", "scorecard.py"))
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)
sc.POSTS, sc.MORNING_LOG, sc.OUT = (os.path.join(tmp, f) for f in ("scoop-posts.json", "morning-log.json", "scorecard.json"))

calls = {"obhistory": 0}
def fake_get_json(url, tries=3):
    m = re.search(r"daily\.json\?station=(\w+)&network=\w+&year=(\d+)&month=(\d+)", url)
    if m:
        rows = fx["daily"].get(f"{m.group(1)}-{int(m.group(3))}", [])
        return {"data": [{"date": d, "max_tmpf": hi, "min_tmpf": lo, "precip": p} for d, hi, lo, p in rows]}
    m = re.search(r"obhistory\.json\?station=PPO&network=IN_ASOS&date=([\d-]+)", url)
    if m:
        calls["obhistory"] += 1
        h = fx["hours"].get(m.group(1))
        if h is None:
            raise RuntimeError("no fixture")
        return {"data": [{"local_valid": f"{m.group(1)}T{i:02d}:55", "tmpf": 50.0} for i in range(h)]}
    raise RuntimeError("unexpected " + url)
sc.get_json = fake_get_json

class FixedDT(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2026, 10, 11, 12, 0, tzinfo=tz)
_dt = datetime
class Shim:
    datetime = FixedDT; date = _dt.date; timedelta = _dt.timedelta
sc.datetime = Shim

sc.main()
card = json.load(open(sc.OUT))
ok = True
def check(name, got, want):
    global ok
    good = got == want
    ok &= good
    print("PASS" if good else "FAIL", name, got, "" if good else f"(want {want})")
oct10 = next(d for d in card["days"] if d["date"] == "2026-10-10")
check("Oct. 10 not graded", (oct10["status"], oct10.get("readingHours")), ("nodata", 1))
check("thinDays", card["thinDays"], {"2026-10-10": 1})
l30 = card["last30"]
check("highs", l30["highs"], [6, 12]); check("lows", l30["lows"], [7, 12])
check("high average miss", l30["highAvgOff"], 4.3); check("low average miss", l30["lowAvgOff"], 3.0)
check("latest graded day", card["latest"]["date"], "2026-10-09")
m10 = next((d for d in card["morning"]["days"] if d["date"] == "2026-10-10"), None)
check("5 AM grade Oct. 10", (m10 or {}).get("status"), "nodata")
check("Oct. 9 still graded (21 hours)", next(d for d in card["days"] if d["date"] == "2026-10-09")["status"], "scored")
first_calls = calls["obhistory"]
sc.main()   # second run: settled days come from the saved coverage
check("second run re-asks only the last 3 days", calls["obhistory"] - first_calls <= 3, True)
print("ALL PASSED" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
