#!/usr/bin/env python3
"""One-time probe (Oct. 6, 2026): what forecast data can a GitHub runner reach for the AI scoreboard?"""
import json, re, sys, time, urllib.request, datetime, traceback

OUT = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.append(s)

def get(url, rng=None, timeout=40):
    h = {"User-Agent": "LaPorteWeatherNow/1.0 (laporteweathernow@gmail.com)"}
    if rng: h["Range"] = rng
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()

def try_get(label, url, n=1500, rng=None):
    try:
        st, b = get(url, rng)
        say(f"== {label}: {st}, {len(b)} bytes  {url}")
        return b
    except Exception as e:
        say(f"== {label}: FAILED {e}  {url}")
        return None

def links(html):
    return re.findall(r'href="([^"]+)"', html.decode("utf-8", "replace"))

now = datetime.datetime.utcnow()
# 1. AIGFS on NOMADS
b = try_get("AIGFS root", "https://nomads.ncep.noaa.gov/pub/data/nccf/com/aigfs/prod/")
if b:
    ds = [l for l in links(b) if l.startswith("aigfs.")]
    say("AIGFS dates:", ds)
    if ds:
        d = ds[-2] if len(ds) > 1 else ds[-1]
        b2 = try_get("AIGFS day", f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/aigfs/prod/{d}")
        if b2: say("cycles:", links(b2))
        b3 = try_get("AIGFS 00z grib2 dir", f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/aigfs/prod/{d}00/model/atmos/grib2/")
        if b3:
            ls = links(b3); say("files:", len(ls), ls[:12], "...", ls[-12:])
        for f in ("aigfs.t00z.sfc.f036.grib2.idx", "aigfs.t00z.sfc.f042.grib2.idx", "aigfs.t00z.sfc.f039.grib2.idx"):
            b4 = try_get("idx " + f, f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/aigfs/prod/{d}00/model/atmos/grib2/{f}")
            if b4: say(b4.decode()[:1500])
# other products
for p in ("aigefs", "hgefs"):
    b = try_get(p + " root", f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/{p}/prod/")
    if b: say(p, [l for l in links(b) if p in l][:20])
# 2. GFS dates on NOMADS + grib filter test
b = try_get("GFS root", "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/")
if b: say("GFS dates:", [l for l in links(b) if l.startswith("gfs.")])
d = (now - datetime.timedelta(days=1)).strftime("%Y%m%d")
gf = try_get("GFS filter f036", "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?dir=%2Fgfs." + d + "%2F00%2Fatmos&file=gfs.t00z.pgrb2.0p25.f036&var_TMP=on&lev_2_m_above_ground=on&subregion=&toplat=42&leftlon=273&rightlon=274&bottomlat=41")
if gf: open("probe/gfs_f036.grb2", "wb").write(gf)
# 3. AWS buckets
for bk in ("noaa-gfs-bdp-pds", "noaa-nws-aigfs-pds", "noaa-aigfs-pds", "noaa-ndfd-pds", "noaa-nws-ndfd-pds"):
    b = try_get("bucket " + bk, f"https://{bk}.s3.amazonaws.com/?list-type=2&max-keys=8&delimiter=/")
    if b: say(b.decode()[:900])
b = try_get("NDFD prefixes", "https://noaa-ndfd-pds.s3.amazonaws.com/?list-type=2&max-keys=20&delimiter=/&prefix=wmo/")
if b: say(b.decode()[:1500])
# 4. ECMWF open data
b = try_get("ECMWF root", "https://data.ecmwf.int/forecasts/")
if b: say("ECMWF dates:", links(b)[-6:])
d = (now - datetime.timedelta(days=1)).strftime("%Y%m%d")
b = try_get("ECMWF day", f"https://data.ecmwf.int/forecasts/{d}/00z/")
if b: say("ECMWF 00z:", links(b))
b = try_get("ECMWF aifs-single", f"https://data.ecmwf.int/forecasts/{d}/00z/aifs-single/0p25/oper/")
if b:
    ls = links(b); say("aifs files:", len(ls), ls[:10])
    idx = [l for l in ls if l.endswith(".index") and "36h" in l]
    say("aifs 36h index:", idx)
    if idx:
        u = idx[0] if idx[0].startswith("http") else f"https://data.ecmwf.int{idx[0]}" if idx[0].startswith("/") else f"https://data.ecmwf.int/forecasts/{d}/00z/aifs-single/0p25/oper/{idx[0]}"
        bi = try_get("aifs index", u)
        if bi:
            lines = bi.decode().splitlines(); say(len(lines), "lines"); say("\n".join([l for l in lines if '"2t"' in l or '"tp"' in l][:6]))
b = try_get("ECMWF ifs", f"https://data.ecmwf.int/forecasts/{d}/00z/ifs/0p25/oper/")
if b: say("ifs files:", len(links(b)), links(b)[:6])
# 5. IEM observations for KPPO
b = try_get("IEM obhistory", f"https://mesonet.agron.iastate.edu/api/1/obhistory.json?station=PPO&network=IN_ASOS&date={(now - datetime.timedelta(days=1)).strftime('%Y-%m-%d')}")
if b:
    j = json.loads(b); rows = j.get("data", [])
    say("obs rows:", len(rows), json.dumps(rows[:2])[:700])
# 6. NWS gridpoint temps
try:
    st, b = get("https://api.weather.gov/points/41.6081,-86.7189")
    p = json.loads(b)["properties"]; say("point:", p.get("gridId"), p.get("gridX"), p.get("gridY"), p.get("forecastGridData"))
    st, b = get(p["forecastGridData"])
    g = json.loads(b)["properties"]; t = g["temperature"]
    say("grid updateTime:", g.get("updateTime"), "temp uom:", t.get("uom"), "first values:", json.dumps(t["values"][:4]))
except Exception as e:
    say("NWS grid FAILED", e)
open("probe/out.txt", "w").write("\n".join(OUT) + "\n")
