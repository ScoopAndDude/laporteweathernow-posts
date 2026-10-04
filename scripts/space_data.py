#!/usr/bin/env python3
"""Fires and weather satellites for "Earth from space" on laporteweathernow.com/disasters (added Oct. 4, 2026).

  python3 scripts/space_data.py FOLDER

Writes two files into FOLDER, which the "Earth from space data" job publishes as branch `space`
(only the newest copy is kept, like the `live` branch):

  fires.json       Every fire NASA's VIIRS cameras spotted in the last 24 hours (on the NOAA-20,
                   NOAA-21 and Suomi NPP satellites), from NASA FIRMS' free global files (no key).
                   Low-confidence detections are left out, and detections are merged into squares of
                   0.1 degree (about 7 miles), so the map stays quick: [lat, lon, power, count, time]
                   for each square, power = fire radiative power in megawatts (summed), time = newest
                   detection (Unix seconds). NASA data is free to use, with credit to NASA FIRMS.
  satellites.json  Orbits (two-line elements) of the weather satellites CelesTrak lists, plus the
                   International Space Station, for the page to work out where each one is right now.
                   CelesTrak asks for no more than one download of the same data every 2 hours; this
                   job runs every 3 hours.

If a source doesn't answer or sends something that doesn't look right, that file is left as it was,
so the page keeps showing the last good copy (with its time).
"""
import csv
import datetime
import io
import json
import os
import sys
import urllib.request

UA = "laporteweathernow.com Earth-from-space data (laporteweathernow@gmail.com)"
FIRMS = {
    "NOAA-20": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv",
    "NOAA-21": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_Global_24h.csv",
    "Suomi NPP": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv",
}
CELESTRAK = [
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
    "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle",   # the space station
]
CELL = 0.1          # degrees
MAX_SQUARES = 30000  # the strongest ones, if a huge fire season ever goes past this


def get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write(folder, name, data):
    tmp = os.path.join(folder, name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    os.replace(tmp, os.path.join(folder, name))


def fires(folder):
    squares, used, raw = {}, [], 0
    for sat, url in FIRMS.items():
        try:
            text = get(url)
        except Exception as e:
            print(f"Fires: {sat} didn't answer ({e}).")
            continue
        rows = list(csv.DictReader(io.StringIO(text)))
        if not rows or "latitude" not in rows[0] or "frp" not in rows[0]:
            print(f"Fires: {sat}'s file doesn't look right; skipped.")
            continue
        used.append(sat)
        for r in rows:
            if str(r.get("confidence", "")).strip().lower() in ("l", "low"):
                continue
            try:
                lat, lon, frp = float(r["latitude"]), float(r["longitude"]), max(float(r["frp"] or 0), 0.0)
                hhmm = str(r["acq_time"]).zfill(4)
                t = datetime.datetime.strptime(r["acq_date"] + hhmm, "%Y-%m-%d%H%M").replace(tzinfo=datetime.timezone.utc)
            except (KeyError, ValueError):
                continue
            raw += 1
            key = (round(lat / CELL), round(lon / CELL))
            s = squares.get(key)
            ts = int(t.timestamp())
            if s:
                s[2] += frp
                s[3] += 1
                s[4] = max(s[4], ts)
            else:
                squares[key] = [round(key[0] * CELL, 2), round(key[1] * CELL, 2), frp, 1, ts]
    if not used:
        print("Fires: no NASA FIRMS file came through; keeping the last copy.")
        return False
    out = sorted(squares.values(), key=lambda s: -s[2])[:MAX_SQUARES]
    for s in out:
        s[2] = round(s[2], 1)
    write(folder, "fires.json", {
        "about": "Fires spotted by NASA's VIIRS satellite cameras in the last 24 hours, merged into 0.1-degree squares: "
                 "[latitude, longitude, fire radiative power in megawatts (summed), detections, newest detection in Unix seconds]. "
                 "Low-confidence detections left out. Source: NASA FIRMS (https://firms.modaps.eosdis.nasa.gov).",
        "updated": now_iso(),
        "satellites": used,
        "detections": raw,
        "fires": out,
    })
    print(f"Fires: {raw} detections from {', '.join(used)} in {len(out)} squares.")
    return True


def satellites(folder):
    sats, seen = [], set()
    for url in CELESTRAK:
        try:
            lines = [l.rstrip() for l in get(url, 60).splitlines() if l.strip()]
        except Exception as e:
            print(f"Satellites: CelesTrak didn't answer ({e}).")
            continue
        for i in range(0, len(lines) - 2, 3):
            name, l1, l2 = lines[i].strip(), lines[i + 1], lines[i + 2]
            if not (l1.startswith("1 ") and l2.startswith("2 ")) or len(l1) < 69 or len(l2) < 69:
                continue
            sid = int(l1[2:7])
            if sid in seen:
                continue
            seen.add(sid)
            sats.append({"name": name, "id": sid, "l1": l1, "l2": l2})
    if len(sats) < 10:
        print(f"Satellites: only {len(sats)} orbits came through; keeping the last copy.")
        return False
    write(folder, "satellites.json", {
        "about": "Orbits (two-line elements) of CelesTrak's weather satellites and the International Space Station, "
                 "for working out where each one is now. Source: CelesTrak (https://celestrak.org).",
        "updated": now_iso(),
        "sats": sats,
    })
    print(f"Satellites: {len(sats)} orbits.")
    return True


def main(argv):
    folder = argv[1] if len(argv) > 1 else "."
    os.makedirs(folder, exist_ok=True)
    ok_f = fires(folder)
    ok_s = satellites(folder)
    # Fail only when nothing at all came through, so a one-off outage doesn't count as a broken job.
    return 0 if (ok_f or ok_s) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
