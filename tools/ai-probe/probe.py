#!/usr/bin/env python3
"""Probe 2 (Oct. 6, 2026): NWS archive routes, and reading one point from each model's GRIB."""
import json, re, urllib.request, datetime

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

LAT, LON = 41.5725, -86.7347   # KPPO
D = "20261005"
# (a) IEM text archive: PFMIWX
def pfm():
    t = get("https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil=PFMIWX&fmt=text&limit=1").decode("latin-1")
    say("PFMIWX latest length", len(t))
    names = re.findall(r"\n([A-Z][A-Za-z .'-]+)-\n?", t)
    say("first lines:\n" + t[:1200])
    for m in re.finditer(r"(?im)^(.*(?:PORTE|MICHIGAN CITY|VALPARAISO|SOUTH BEND).*)$", t):
        say("POINT LINE:", m.group(1))
    i = t.upper().find("LA PORTE")
    if i < 0: i = t.upper().find("LAPORTE")
    if i >= 0: say("LA PORTE block:\n" + t[i-200:i+2200])
    t2 = get("https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil=PFMIWX&fmt=text&sdate=2026-09-27T09:00Z&edate=2026-09-27T12:00Z&limit=5").decode("latin-1")
    say("archive Sept 27 09-12Z length", len(t2), "issued lines:", re.findall(r"\d{3,4} [AP]M E[DS]T \w{3} \w{3} \d+ \d{4}", t2)[:5])
tryit("pfm", pfm)
# (b) NDFD on AWS
def ndfd():
    x = get("https://noaa-ndfd-pds.s3.amazonaws.com/?list-type=2&max-keys=40&prefix=wmo/temp/2026/10/05/").decode()
    keys = re.findall(r"<Key>([^<]+)</Key><LastModified>([^<]+)</LastModified><ETag>[^<]*</ETag><Size>(\d+)</Size>", x)
    say("NDFD temp keys Oct 5:", len(keys)); [say("  ", k) for k in keys[:40]]
tryit("ndfd", ndfd)

import pygrib, numpy as np
def point_from_grib(path, lat=LAT, lon=LON):
    g = pygrib.open(path); out = []
    for m in g:
        v, lats, lons = m.data()
        lo = lon % 360 if lons.max() > 180 else lon
        d = (lats - lat) ** 2 + (lons - lo) ** 2
        j = np.unravel_index(np.argmin(d), d.shape)
        out.append((m.shortName, m.name, str(m.validDate), float(v[j]), float(lats[j]), float(lons[j])))
    return out
def ranged(base, idxlines, want):
    # NCEP .idx: n:offset:...  -> range to next offset
    rows = [l.split(":") for l in idxlines if l.strip()]
    for i, r in enumerate(rows):
        if want in ":".join(r):
            start = int(r[1]); end = int(rows[i+1][1]) - 1 if i + 1 < len(rows) else ""
            return get(base, rng=f"bytes={start}-{end}")
# (c) AIGFS TMP + APCP at f036
def aigfs():
    base = f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/aigfs/prod/aigfs.{D}/00/model/atmos/grib2/aigfs.t00z.sfc.f036.grib2"
    idx = get(base + ".idx").decode().splitlines()
    for want in (":TMP:2 m above ground:", ":APCP:surface:30-36 hour acc"):
        b = ranged(base, idx, want); open("/tmp/a.grb2", "wb").write(b)
        say("AIGFS", want, point_from_grib("/tmp/a.grb2"))
tryit("aigfs", aigfs)
# (d) GFS via filter, TMP and APCP f036
def gfs():
    u = ("https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?dir=%2Fgfs." + D + "%2F00%2Fatmos&file=gfs.t00z.pgrb2.0p25.f036"
         "&var_TMP=on&lev_2_m_above_ground=on&var_APCP=on&lev_surface=on&subregion=&toplat=42&leftlon=273&rightlon=274&bottomlat=41")
    open("/tmp/g.grb2", "wb").write(get(u)); say("GFS", point_from_grib("/tmp/g.grb2"))
tryit("gfs", gfs)
# (e) ECMWF AIFS and IFS: index ranges for 2t and tp at 36h
def ecmwf(model):
    base = f"https://data.ecmwf.int/forecasts/{D}/00z/{model}/0p25/oper/{D}000000-36h-oper-fc"
    lines = [json.loads(l) for l in get(base + ".index").decode().splitlines() if l.strip()]
    for p in ("2t", "tp"):
        r = [x for x in lines if x.get("param") == p]
        if not r: say(model, p, "not in index"); continue
        r = r[0]; b = get(base + ".grib2", rng=f"bytes={r['_offset']}-{r['_offset'] + r['_length'] - 1}")
        open("/tmp/e.grb2", "wb").write(b); say(model, p, point_from_grib("/tmp/e.grb2"))
for m in ("aifs-single", "ifs"): tryit(m, lambda m=m: ecmwf(m))
# (f) KPPO obs near 12Z Oct 6
def obs():
    j = json.loads(get("https://mesonet.agron.iastate.edu/api/1/obhistory.json?station=PPO&network=IN_ASOS&date=2026-10-06&full=1"))
    for r in j["data"]:
        if r["utc_valid"][11:13] in ("11", "12", "17", "18"): say("obs", r["utc_valid"], r["tmpf"], r.get("p01i"), r["raw"])
tryit("obs", obs)
open("probe/out.txt", "w").write("\n".join(OUT) + "\n")
