#!/usr/bin/env python3
"""Probe 3 (Oct. 6, 2026): Michigan City airport obs, NDFD archive layout, PFM parsing."""
import json, re, urllib.request

OUT = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.append(s)
def get(url, rng=None, timeout=60):
    h = {"User-Agent": "LaPorteWeatherNow/1.0 (laporteweathernow@gmail.com)"}
    if rng: h["Range"] = rng
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.read()
def tryit(label, fn):
    try: return fn()
    except Exception as e: say(f"!! {label}: {e}")

def obs(st):
    j = json.loads(get(f"https://mesonet.agron.iastate.edu/api/1/obhistory.json?station={st}&network=IN_ASOS&date=2026-09-30&full=1"))
    rows = j["data"]; say(st, "rows", len(rows))
    for r in rows[:3] + [x for x in rows if (x.get("p01i") or 0) > 0][:6]:
        say("  ", r["utc_valid"], r["tmpf"], "p01i", r.get("p01i"), r["raw"])
    m = json.loads(get(f"https://mesonet.agron.iastate.edu/api/1/daily.json?station={st}&network=IN_ASOS&year=2026&month=9"))
    for d in m["data"][-4:]: say("  daily", d.get("date"), d.get("max_tmpf"), d.get("min_tmpf"), d.get("precip"))
for st in ("MGC", "PPO"): tryit("obs " + st, lambda st=st: obs(st))
def meta():
    j = json.loads(get("https://mesonet.agron.iastate.edu/geojson/network/IN_ASOS.geojson"))
    for f in j["features"]:
        p = f["properties"]
        if p.get("sid") in ("MGC", "PPO", "SBN", "VPZ"): say("meta", p.get("sid"), p.get("sname"), f["geometry"]["coordinates"], p.get("archive_begin"))
tryit("meta", meta)
def ndfd():
    for pre in ("wmo/temp/", "wmo/temp/2026/", "wmo/temp/2026/10/", "opnl/"):
        x = get(f"https://noaa-ndfd-pds.s3.amazonaws.com/?list-type=2&max-keys=15&delimiter=/&prefix={pre}").decode()
        say("NDFD", pre, re.findall(r"<Prefix>([^<]+)</Prefix>", x)[:15], re.findall(r"<Key>([^<]+)</Key>", x)[:8])
tryit("ndfd", ndfd)
def pfm(sdate, edate):
    t = get(f"https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil=PFMIWX&fmt=text&sdate={sdate}&edate={edate}&limit=3").decode("latin-1")
    issues = re.findall(r"\n(\d{3,4} [AP]M E[DS]T \w{3} \w{3} +\d+ \d{4})\n", t)
    say("PFM", sdate, "issuances", issues[:3])
    i = t.find("Michigan City Municipal Airport")
    blk = t[i:t.find("$$", i)]
    say(blk[:1400])
tryit("pfm", lambda: pfm("2026-09-30T08:00Z", "2026-09-30T11:30Z"))
open("probe/out.txt", "w").write("\n".join(OUT) + "\n")
