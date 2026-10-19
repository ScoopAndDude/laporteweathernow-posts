#!/usr/bin/env python3
"""Storm records test (Oct. 19, 2026): which free archives answer from GitHub Actions.

Writes storm-records/out/probe.json and probe.txt. Read-only: only asks public NOAA / IEM / OSM
servers for a handful of files from last winter's Jan. 25-26, 2026 La Porte County storm.
"""
import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "storm-records", "out")
UA = {"User-Agent": "laporteweathernow.com storm records test (GitHub Actions; laporteweathernow@gmail.com)"}
results = []


def ask(label, url, method="GET", limit=4000, binary=False):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA, method=method)
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read() if method == "GET" else b""
            info = {"label": label, "url": url, "status": r.status, "bytes": len(body),
                    "type": r.headers.get("Content-Type"), "len_header": r.headers.get("Content-Length"),
                    "seconds": round(time.time() - t0, 1)}
            if not binary and body:
                info["head"] = body[:limit].decode("utf-8", "replace")
            results.append(info)
            return body
    except Exception as e:  # noqa: BLE001
        results.append({"label": label, "url": url, "error": f"{type(e).__name__}: {e}"[:300],
                        "seconds": round(time.time() - t0, 1)})
        return None


def s3_list(bucket, prefix, label, max_keys=50):
    url = f"https://{bucket}.s3.amazonaws.com/?list-type=2&max-keys={max_keys}&prefix={urllib.parse.quote(prefix)}"
    body = ask(label, url, limit=0)
    if not body:
        return []
    ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
    root = ET.fromstring(body)
    keys = [(c.find("s:Key", ns).text, int(c.find("s:Size", ns).text)) for c in root.findall("s:Contents", ns)]
    results[-1]["keys"] = keys[:8]
    results[-1]["key_count"] = len(keys)
    return keys


def main():
    os.makedirs(OUT, exist_ok=True)
    # 1. NOHRSC National Snowfall Analysis v2 archive (GeoTIFF / NetCDF), storm of Jan. 25-26, 2026.
    for name in ["sfav2_CONUS_24h_2026012612.tif", "sfav2_CONUS_6h_2026012612.tif",
                 "sfav2_CONUS_24h_2026012612.nc", "sfav2_CONUS_6h_2026012606.tif"]:
        ask(f"NOHRSC {name}", f"https://www.nohrsc.noaa.gov/snowfall_v2/data/202601/{name}", method="HEAD")
    ask("NOHRSC data dir 202601", "https://www.nohrsc.noaa.gov/snowfall_v2/data/202601/", limit=3000)
    ask("NOHRSC data dir 202511", "https://www.nohrsc.noaa.gov/snowfall_v2/data/202511/", limit=1500)

    # 2. MRMS on AWS (radar + gauge rain, hourly), same storm.
    s3_list("noaa-mrms-pds", "CONUS/MultiSensor_QPE_01H_Pass2_00.00/20260126/", "MRMS QPE 01H Pass2 2026-01-26")
    s3_list("noaa-mrms-pds", "CONUS/MultiSensor_QPE_01H_Pass1_00.00/20260126/", "MRMS QPE 01H Pass1 2026-01-26")
    s3_list("noaa-mrms-pds", "CONUS/PrecipFlag_00.00/20260126/", "MRMS PrecipFlag 2026-01-26", max_keys=5)
    s3_list("noaa-mrms-pds", "CONUS/MultiSensor_QPE_01H_Pass2_00.00/20251110/", "MRMS QPE 01H Pass2 2025-11-10")
    s3_list("noaa-mrms-pds", "CONUS/", "MRMS product folders", max_keys=1000)

    # 3. RTMA 2.5 km hourly analysis on AWS (temperature at a spot).
    s3_list("noaa-rtma-pds", "rtma2p5.20260126/", "RTMA 2.5km 2026-01-26", max_keys=20)

    # 4. IEM: airport hourly reports, storm reports, CoCoRaHS daily.
    q = urllib.parse.urlencode([("station", "MGC"), ("station", "PPO"), ("station", "SBN"), ("station", "VPZ"),
                                ("data", "tmpf"), ("data", "wxcodes"), ("data", "p01i"), ("data", "vsby"),
                                ("year1", "2026"), ("month1", "1"), ("day1", "25"),
                                ("year2", "2026"), ("month2", "1"), ("day2", "26"),
                                ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "yes"),
                                ("missing", "M"), ("trace", "T"), ("report_type", "3")])
    ask("IEM ASOS hourly", f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?{q}", limit=1500)
    ask("IEM LSR geojson", "https://mesonet.agron.iastate.edu/geojson/lsr.geojson?wfos=IWX&sts=2026-01-25T12:00Z&ets=2026-01-27T00:00Z", limit=800)
    ask("IEM CoCoRaHS IN daily", "https://mesonet.agron.iastate.edu/api/1/daily.geojson?network=IN_COCORAHS&date=2026-01-26", limit=1500)
    ask("IEM CoCoRaHS MI daily", "https://mesonet.agron.iastate.edu/api/1/daily.geojson?network=MI_COCORAHS&date=2026-01-26", limit=300)
    ask("IEM IEMRE hourly point", "https://mesonet.agron.iastate.edu/iemre/hourly/2026-01-26/41.61/-86.72/json", limit=1500)
    ask("IEM IEMRE daily point", "https://mesonet.agron.iastate.edu/iemre/daily/2026-01-26/41.61/-86.72/json", limit=1500)

    # 5. OpenStreetMap geocoding (test lots are public places).
    ask("Nominatim", "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": "Meijer, Michigan City, Indiana", "format": "jsonv2", "limit": 3}), limit=1500)

    json.dump(results, open(os.path.join(OUT, "probe.json"), "w"), indent=1)
    with open(os.path.join(OUT, "probe.txt"), "w") as f:
        for r in results:
            f.write(f"{r['label']}: {r.get('status', r.get('error'))} bytes={r.get('bytes')} len={r.get('len_header')} {r.get('seconds')}s\n")
            if r.get("keys"):
                f.write(f"   keys({r.get('key_count')}): {r['keys'][:4]}\n")
    print(open(os.path.join(OUT, "probe.txt")).read())


if __name__ == "__main__":
    main()
