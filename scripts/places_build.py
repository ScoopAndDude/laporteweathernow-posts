#!/usr/bin/env python3
"""Builds the map squares behind laporteweathernow.com/camp-map (The Chase), so the map loads fast.

Instead of every visitor asking a volunteer Overpass server (slow or down on busy days), this job
downloads OpenStreetMap's U.S. data from Geofabrik once a week, keeps only what travelers need, and
saves it as small files, one per 1-degree square and layer, on the "places" branch:

  tiles/main/<lat>_<lon>.json    campsites, RV parks, rest areas, service plazas, dog parks
  tiles/spring/<lat>_<lon>.json  named springs, springs with a drinking-water tag, hot springs, water fill stations
  tiles/stops/<lat>_<lon>.json   dump stations, showers, laundromats, libraries
  tiles/fuel/<lat>_<lon>.json    propane refills, truck stops, fuel stations with propane
  tiles/index.json               when it was built, and which squares have data

Each file is {"e": [[type, id, lat, lon, {tags}], ...]} with type "n", "w" or "r". The page reads only
the squares around the town on screen. Map data (c) OpenStreetMap contributors, under the Open
Database License (ODbL 1.0); these files are offered under the same license.

  python3 scripts/places_build.py WORK_DIR      (needs osmium-tool; writes WORK_DIR/out)
"""
import datetime
import json
import math
import os
import shutil
import subprocess
import sys
import urllib.request

REGIONS = ["north-america/us-midwest", "north-america/us-northeast", "north-america/us-south",
           "north-america/us-west", "north-america/us-pacific", "north-america/us/puerto-rico"]
GEOFABRIK = "https://download.geofabrik.de/{}-latest.osm.pbf"
UA = "laporteweathernow.com camp map (weekly; contact laporteweathernow@gmail.com)"

# What osmium keeps from the full download (the finer choices are made in layer_of below).
FILTERS = ["nwr/tourism=camp_site,caravan_site", "nwr/highway=rest_area,services", "nwr/leisure=dog_park",
           "n/natural=spring", "nwr/natural=hot_spring",
           "nwr/amenity=water_point,sanitary_dump_station,shower,library,fuel,public_bath", "nwr/shop=laundry,gas"]

# Only the tags the page uses.
KEEP = {"name", "tourism", "highway", "leisure", "natural", "amenity", "shop", "bath:type", "access", "group_only",
        "camp_site", "fee", "charge", "dog", "website", "contact:website", "url", "phone", "contact:phone", "operator",
        "brand", "tents", "caravans", "motorhome", "toilets", "drinking_water", "water_point", "addr:city", "addr:state",
        "internet_access", "hot_water", "opening_hours", "hgv", "fuel:diesel", "fuel:HGV_diesel", "fuel:adblue",
        "fuel:lpg", "fuel:propane", "shower", "showers", "seasonal", "description", "note"}
LONG = {"description", "note"}


def layer_of(t):
    """Which layer a place belongs to, matching classify() in camp-map.js; None to skip it."""
    if t.get("leisure") == "dog_park":
        return "main"
    if t.get("natural") == "hot_spring" or t.get("bath:type") == "hot_spring":
        return "spring"
    if t.get("natural") == "spring":
        return "spring" if (t.get("name") or t.get("drinking_water")) else None
    if t.get("amenity") == "water_point":
        return "spring"
    if t.get("highway") in ("rest_area", "services") or t.get("tourism") in ("camp_site", "caravan_site"):
        return "main"
    if t.get("amenity") in ("sanitary_dump_station", "shower", "library") or t.get("shop") == "laundry":
        return "stops"
    if t.get("shop") == "gas":
        return "fuel"
    if t.get("amenity") == "fuel" and ("yes" in (t.get("hgv"), t.get("fuel:lpg"), t.get("fuel:propane"))):
        return "fuel"
    return None


def center(geom):
    """A point for any geometry: the point itself, or the average of a line's or outer ring's points."""
    kind, c = geom.get("type"), geom.get("coordinates")
    if kind == "Point":
        return c[1], c[0]
    if kind == "LineString":
        pts = c
    elif kind == "Polygon":
        pts = c[0]
    elif kind == "MultiPolygon":
        pts = c[0][0]
    else:
        return None
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]   # a closed ring repeats its first point
    if not pts:
        return None
    return sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
        shutil.copyfileobj(r, f, 16 * 1024 * 1024)


def run(*args):
    subprocess.run(args, check=True)


def main(work):
    os.makedirs(work, exist_ok=True)
    places = {}
    for region in REGIONS:
        name = region.rsplit("/", 1)[-1]
        src, flt, geo = (os.path.join(work, f"{name}.{x}") for x in ("osm.pbf", "filtered.osm.pbf", "geojsonseq"))
        print("Downloading", region, flush=True)
        download(GEOFABRIK.format(region), src)
        print(f"  {os.path.getsize(src) / 1e9:.2f} GB; filtering", flush=True)
        run("osmium", "tags-filter", src, *FILTERS, "-o", flt, "--overwrite")
        os.remove(src)
        run("osmium", "export", flt, "-f", "geojsonseq", "-x", "print_record_separator=false", "-a", "type,id", "-o", geo, "--overwrite")
        os.remove(flt)
        kept = 0
        with open(geo, encoding="utf-8") as f:
            for line in f:
                line = line.strip().lstrip("\x1e")
                if not line:
                    continue
                feat = json.loads(line)
                props = feat.get("properties") or {}
                t = {k: v for k, v in props.items() if not k.startswith("@")}
                layer = layer_of(t)
                if not layer:
                    continue
                pt = center(feat.get("geometry") or {})
                if not pt:
                    continue
                kind = {"node": "n", "way": "w", "relation": "r"}.get(props.get("@type"), "n")
                key = f"{kind}{props.get('@id')}"
                tags = {}
                for k, v in t.items():
                    if k in KEEP:
                        v = str(v)
                        tags[k] = v[:200] if k in LONG else v[:300]
                places[key] = (layer, [kind, int(props.get("@id") or 0), round(pt[0], 5), round(pt[1], 5), tags])
                kept += 1
        os.remove(geo)
        print(f"  kept {kept} places ({len(places)} total so far)", flush=True)

    counts = {}
    tiles = {}
    for layer, el in places.values():
        lat, lon = el[2], el[3]
        tkey = f"{math.floor(lat)}_{math.floor(lon)}"
        tiles.setdefault((layer, tkey), []).append(el)
        counts[layer] = counts.get(layer, 0) + 1
    print("By layer:", counts, flush=True)
    if counts.get("main", 0) < 20000 or counts.get("spring", 0) < 1000:
        print("Too few places; something went wrong. Not saving.")
        return 1

    out = os.path.join(work, "out")
    shutil.rmtree(out, ignore_errors=True)
    index = {"built": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
             "source": "OpenStreetMap contributors, via Geofabrik (data under the Open Database License, ODbL 1.0)",
             "format": "Each tile is {\"e\": [[type, id, lat, lon, tags], ...]}; type n/w/r; tiles are 1-degree squares named by their southwest corner.",
             "counts": counts, "tiles": {}}
    for (layer, tkey), els in sorted(tiles.items()):
        d = os.path.join(out, "tiles", layer)
        os.makedirs(d, exist_ok=True)
        els.sort(key=lambda e: (e[2], e[3]))
        with open(os.path.join(d, f"{tkey}.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"e": els}, ensure_ascii=False, separators=(",", ":")))
        index["tiles"].setdefault(layer, []).append(tkey)
    with open(os.path.join(out, "tiles", "index.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Camp map places\n\nBuilt weekly by `scripts/places_build.py` on the main branch for laporteweathernow.com/camp-map (The Chase).\n\n"
                "Map data (c) OpenStreetMap contributors, https://www.openstreetmap.org/copyright, available under the Open Database License "
                "(ODbL 1.0). These derived files are offered under the same license.\n")
    total = sum(len(v) for v in tiles.values())
    print(f"Saved {total} places in {len(tiles)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "places-work"))
