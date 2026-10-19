#!/usr/bin/env python3
"""Storm grid TEST check (Oct. 19, 2026): the grid's snow days at the 5 test lots next to the per-lot engine's
results (storm-records/out/records/) and the 24-hour analysis at the exact lot. Writes OUT/compare.txt.

    python3 scripts/storm_records/grid_compare.py storm-records/out/grid
"""
import datetime as dt
import glob
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
CONF = json.load(open(os.path.join(ROOT, "storm-records", "config.json")))
RECORDS = os.path.join(ROOT, "storm-records", "out", "records")
UTC = dt.timezone.utc


def cell_of(g, lat, lon):
    r = int((g["north"] - lat) // g["step"])
    c = int((lon - g["west"]) // g["step"])
    if not (0 <= r < g["rows"] and 0 <= c < g["cols"]):
        return -1
    return r * g["cols"] + c


def parse(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def main():
    out = sys.argv[1]
    lines = []
    for path in sorted(glob.glob(os.path.join(out, "snow", "*", "meta.json"))):
        day = json.load(open(path))
        g = day["grid"]
        # the tiles hold the cells; put them back together
        day.update(cells=[], snow=[], type=[], ice=[])
        for name in day["tiles"]:
            t = json.load(open(os.path.join(os.path.dirname(path), f"{name}.json")))
            for k in ("cells", "snow", "type", "ice"):
                day[k] += t[k]
        idx = {c: i for i, c in enumerate(day["cells"])}
        end = parse(day["end"])
        hours = [parse(h) for h in day["hours"]]
        lines.append(f"== {day['day']} (24 hours ending {day['end']}): max {day['maxSnow']} in., "
                     f"{len(day['cells'])} cells with something, source {day['source']}, {len(day['reports'])} reports")
        for lot in CONF["lots"]:
            c = cell_of(g, lot["lat"], lot["lon"])
            i = idx.get(c)
            snow = [x / 100 for x in day["snow"][i]] if i is not None else [0.0] * 24
            types = day["type"][i] if i is not None else "." * 24
            total = sum(snow)
            cum, plow = 0.0, None
            for h, s in zip(hours, snow):
                cum += s
                if plow is None and cum >= lot["plow_at"] - 1e-9 and cum > 0:
                    plow = h
            # the per-lot engine's hours in the same 24 hours, from whichever storm record covers them
            eng, eng_plow = None, None
            for rp in glob.glob(os.path.join(RECORDS, "*", f"{lot['id']}.json")):
                rec = json.load(open(rp))
                hrs = [(parse(x["t"]), x["snow_in"]) for x in rec.get("hours", [])]
                inside = [(t, s) for t, s in hrs if end - dt.timedelta(hours=24) < t <= end]
                if inside:
                    eng = (eng or 0.0) + sum(s for _, s in inside)
                    cum2 = 0.0
                    for t, s in inside:
                        cum2 += s
                        if eng_plow is None and cum2 >= lot["plow_at"] - 1e-9 and cum2 > 0:
                            eng_plow = t
            lines.append(f"  {lot['id']:16s} grid {total:5.1f} in.  engine {('-' if eng is None else f'{eng:5.1f}')} in.  "
                         f"plow at {lot['plow_at']} in.: grid {plow.strftime('%m-%d %H') + 'Z' if plow else '-'}, "
                         f"engine {eng_plow.strftime('%m-%d %H') + 'Z' if eng_plow else '-'}  types {types}  "
                         f"ice {(day['ice'][i] / 100) if i is not None else 0:.2f}")
    with open(os.path.join(out, "compare.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
