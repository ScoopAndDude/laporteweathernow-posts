#!/usr/bin/env python3
"""Probe 4 (Oct. 6, 2026): NDFD (the Weather Service's official forecast grids) archive on AWS."""
import json, re, urllib.request, os

OUT = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.append(s)
def get(url, rng=None, timeout=120):
    h = {"User-Agent": "LaPorteWeatherNow/1.0 (laporteweathernow@gmail.com)"}
    if rng: h["Range"] = rng
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.read()
def lst(prefix, delim=True, n=200):
    x = get(f"https://noaa-ndfd-pds.s3.amazonaws.com/?list-type=2&max-keys={n}{'&delimiter=/' if delim else ''}&prefix={prefix}").decode()
    return re.findall(r"<Prefix>([^<]+)</Prefix>", x), re.findall(r"<Key>([^<]+)</Key><LastModified>([^<]+)</LastModified><ETag>[^<]*</ETag><Size>(\d+)</Size>", x)
for el in ("temp", "qpf", "pop12", "maxt", "mint"):
    try:
        p, k = lst(f"wmo/{el}/2026/10/05/")
        say(el, "prefixes", p[:30]); say(el, "keys", len(k), k[:30])
    except Exception as e: say("!!", el, e)
try:
    p, k = lst("wmo/temp/2026/10/05/", delim=False, n=300)
    say("temp all keys", len(k))
    for x in k: say("  ", x)
except Exception as e: say("!! all", e)
import pygrib, numpy as np
LAT, LON = 41.5725, -86.7345
def inspect(key):
    b = get("https://noaa-ndfd-pds.s3.amazonaws.com/" + key)
    open("/tmp/n.bin", "wb").write(b); say("FILE", key, len(b), "bytes")
    g = pygrib.open("/tmp/n.bin"); n = 0
    for m in g:
        n += 1
        if n <= 40:
            try:
                lats, lons = m.latlons()
                d = (lats - LAT) ** 2 + (lons - LON) ** 2; j = np.unravel_index(np.argmin(d), d.shape)
                v = m.values[j]
                say("  msg", n, m.shortName, m.name, "analDate", m.analDate, "valid", m.validDate, "ft", m.forecastTime, m.stepRange if hasattr(m, 'stepRange') else '', "grid", m.Ni, m.Nj, "pt", round(float(lats[j]), 3), round(float(lons[j]), 3), "val", float(v))
            except Exception as e:
                say("  msg", n, "err", e)
    say("  total msgs", n)
try:
    _, k = lst("wmo/temp/2026/10/05/", delim=False, n=300)
    ks = [x for x in k if x[0]]
    # pick a file written between 09:00 and 11:30 UTC, smallest first
    cand = [x for x in ks if "T09" in x[1] or "T10" in x[1] or "T11" in x[1]]
    say("candidates", cand[:10])
    for key, lm, size in sorted(cand, key=lambda x: int(x[2]))[:3]:
        inspect(key)
except Exception as e: say("!! inspect", e)
open("probe/out.txt", "w").write("\n".join(OUT) + "\n")
