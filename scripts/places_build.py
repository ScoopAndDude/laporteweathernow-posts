#!/usr/bin/env python3
"""Builds the map squares behind laporteweathernow.com/camp-map (The Chase), so the map loads fast.

Instead of every visitor asking a volunteer Overpass server (slow or down on busy days), a weekly job
downloads OpenStreetMap's U.S. data from Geofabrik, keeps only what travelers need, and saves it as small
files, one per 1-degree square and layer, in the tiles/ folder on the main branch. GitHub Pages serves
them to the site from scoopanddude.github.io/laporteweathernow-posts/tiles/ (raw.githubusercontent.com
is the backup):

  tiles/main/<lat>_<lon>.json    campsites, RV parks, rest areas, service plazas, dog parks
  tiles/spring/<lat>_<lon>.json  named springs, springs with a drinking-water tag, hot springs, water fill stations
  tiles/stops/<lat>_<lon>.json   dump stations, showers, laundromats, libraries
  tiles/fuel/<lat>_<lon>.json    propane refills, truck stops, fuel stations with propane
  tiles/index.json               when the data is from, which squares have places, and which squares it covers

Each file is {"e": [[type, id, lat, lon, {tags}], ...]} with type "n", "w" or "r". The page reads only the
squares around the town on screen. Map data (c) OpenStreetMap contributors, under the Open Database
License (ODbL 1.0); these files are offered under the same license.

The job runs in steps so it's fast and one bad download can't break the map:
  1. One runner per state downloads that state's file (checked against Geofabrik's checksum) and keeps
     the places travelers need. The states run at the same time.
  2. One runner merges the states into map squares. A state that couldn't be downloaded this week, or
     whose count fell by more than half (a bad download or vandalism), keeps last week's copy, saved on
     the "places-parts" branch. Nothing is published unless every state is there.

  python3 scripts/places_build.py states                         (the list of states, for the workflow)
  python3 scripts/places_build.py extract STATE OUT.json         (needs osmium-tool and curl)
  python3 scripts/places_build.py tiles NEW_DIR OLD_DIR WORK_DIR (writes WORK_DIR/out/tiles and WORK_DIR/out/parts)
  python3 scripts/places_build.py check INDEX.json               (fails if any state's data is over 4 weeks old)
"""
import datetime
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.request

GEOFABRIK = "https://download.geofabrik.de/north-america/us/{}-latest.osm.pbf"
UA = "laporteweathernow.com camp map (weekly; contact laporteweathernow@gmail.com)"

# Geofabrik's names for every U.S. state, D.C., Puerto Rico and the U.S. Virgin Islands.
STATES = ["alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
          "district-of-columbia", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas",
          "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
          "missouri", "montana", "nebraska", "nevada", "new-hampshire", "new-jersey", "new-mexico", "new-york",
          "north-carolina", "north-dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "puerto-rico",
          "rhode-island", "south-carolina", "south-dakota", "tennessee", "texas", "us-virgin-islands", "utah",
          "vermont", "virginia", "washington", "west-virginia", "wisconsin", "wyoming"]

KEEP_OLD_DAYS = 21   # a state's count may fall by half only if last week's copy is this old (then it's real)
STALE_DAYS = 28      # after this long without a fresh download, the weekly job reports a real problem
MIN_COUNTS = {"main": 20000, "spring": 1000, "stops": 3000, "fuel": 500}   # far below a normal week, for the whole U.S.

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
LAYERS = ("main", "spring", "stops", "fuel")


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


def square(lat, lon):
    """The name of the 1-degree square a point is in, by its southwest corner (the page uses the same)."""
    return f"{math.floor(lat)}_{math.floor(lon)}"


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def age_days(iso):
    try:
        then = datetime.datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return 9999
    return (datetime.datetime.now(datetime.timezone.utc) - then).total_seconds() / 86400


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def download(state, path, tries=6):
    """Download a state's file and check it against Geofabrik's checksum.

    curl gives up on a stalled connection (under 100 KB/s for 2 minutes); the next try picks up where the
    last one stopped. If the file changed on the server in between, the checksum catches it and we start over.
    """
    url = GEOFABRIK.format(state)
    for attempt in range(1, tries + 1):
        try:
            want = fetch_text(url + ".md5").split()[0].lower()
        except Exception as e:  # no checksum this time; curl's own result decides
            print(f"  couldn't read the checksum (try {attempt}): {e}", flush=True)
            want = None
        t0 = time.time()
        r = subprocess.run(["curl", "-fsSL", "-A", UA, "--connect-timeout", "30", "--speed-limit", "100000",
                            "--speed-time", "120", "--max-time", "2400", "-C", "-", "-o", path, url])
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  try {attempt}: {size / 1e6:.0f} MB in {time.time() - t0:.0f} s (curl {r.returncode})", flush=True)
        if size and want:
            if md5_of(path) == want:
                return
            if r.returncode == 0:   # finished but doesn't match: the file changed on the server; start over
                print("  checksum didn't match; starting over", flush=True)
                os.remove(path)
        elif size and r.returncode == 0:
            return
        if attempt < tries:
            time.sleep(min(30 * attempt, 120))
    raise RuntimeError(f"couldn't download {state} after {tries} tries")


def run(*args):
    subprocess.run(args, check=True)


def extract(state, out_json):
    """One state: download, keep the places travelers need, save them as [[layer, element], ...]."""
    if state not in STATES:
        print(f"Unknown state {state!r}; expected one of: {', '.join(STATES)}")
        return 2
    work = os.path.dirname(os.path.abspath(out_json))
    src, flt, geo = (os.path.join(work, f"{state}.{x}") for x in ("osm.pbf", "filtered.osm.pbf", "geojsonseq"))
    t0 = time.time()
    print("Downloading", state, flush=True)
    download(state, src)
    print(f"  downloaded in {time.time() - t0:.0f} s; keeping the places travelers need", flush=True)
    run("osmium", "tags-filter", src, *FILTERS, "-o", flt, "--overwrite")
    os.remove(src)
    run("osmium", "export", flt, "-f", "geojsonseq", "-x", "print_record_separator=false", "-a", "type,id",
        "-o", geo, "--overwrite")
    os.remove(flt)
    places, cover, counts = {}, set(), {}
    with open(geo, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            feat = json.loads(line)
            pt = center(feat.get("geometry") or {})
            if not pt:
                continue
            cover.add(square(*pt))   # every square with any U.S. data in it, even places we don't keep
            props = feat.get("properties") or {}
            t = {k: v for k, v in props.items() if not k.startswith("@")}
            layer = layer_of(t)
            if not layer:
                continue
            kind = {"node": "n", "way": "w", "relation": "r"}.get(props.get("@type"), "n")
            tags = {}
            for k, v in t.items():
                if k in KEEP:
                    v = str(v)
                    tags[k] = v[:200] if k in LONG else v[:300]
            key = f"{kind}{props.get('@id')}"
            if key not in places:
                counts[layer] = counts.get(layer, 0) + 1
            places[key] = [layer, [kind, int(props.get("@id") or 0), round(pt[0], 5), round(pt[1], 5), tags]]
    os.remove(geo)
    if not places:
        print("  no places found; the download must be broken")
        return 1
    part = {"state": state, "built": now_iso(), "counts": counts, "cover": sorted(cover), "places": list(places.values())}
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(part, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  kept {len(places)} places {counts} in {time.time() - t0:.0f} s", flush=True)
    return 0


def load_parts(folder):
    """Every state file in a folder, by state; unreadable or empty ones are skipped."""
    parts = {}
    if not folder or not os.path.isdir(folder):
        return parts
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                part = json.load(f)
        except (OSError, ValueError) as e:
            print(f"  skipping {name}: {e}")
            continue
        if part.get("state") in STATES and part.get("places"):
            parts[part["state"]] = part
    return parts


def tiles(new_dir, old_dir, work):
    """Merge every state's places into the map squares, using last week's copy for any state that failed."""
    new, old = load_parts(new_dir), load_parts(old_dir)
    print(f"{len(new)} states downloaded this week; {len(old)} copies from earlier weeks", flush=True)
    use, notes = {}, []
    for s in STATES:
        n, o = new.get(s), old.get(s)
        if n and o and len(n["places"]) < 0.5 * len(o["places"]) and age_days(o.get("built")) < KEEP_OLD_DAYS:
            notes.append(f"{s}: only {len(n['places'])} places this week, {len(o['places'])} before; keeping the earlier copy")
            use[s] = o
        elif n:
            use[s] = n
        elif o:
            notes.append(f"{s}: not downloaded this week; using the copy from {str(o.get('built'))[:10]}")
            use[s] = o
    for line in notes:
        print(" ", line)
    missing = [s for s in STATES if s not in use]
    if missing:
        print("Missing states, so nothing was saved:", ", ".join(missing))
        return 1
    places, cover, dates = {}, set(), {}
    for s in STATES:
        part = use[s]
        dates[s] = str(part.get("built"))
        cover.update(part.get("cover") or [])
        for layer, el in part["places"]:
            if layer in LAYERS:
                places[f"{el[0]}{el[1]}"] = (layer, el)   # places on a state line are in both states' files
    counts, squares = {}, {}
    for layer, el in places.values():
        squares.setdefault((layer, square(el[2], el[3])), []).append(el)
        counts[layer] = counts.get(layer, 0) + 1
        cover.add(square(el[2], el[3]))
    print(f"{len(places)} places in {len(squares)} squares:", counts, flush=True)
    low = {k: counts.get(k, 0) for k, least in MIN_COUNTS.items() if counts.get(k, 0) < least}
    if low:
        print("Too few places, so something went wrong; nothing was saved:", low)
        return 1
    out = os.path.join(work, "out")
    shutil.rmtree(out, ignore_errors=True)
    index = {"built": min(dates.values()),   # the oldest state's data, so the page never claims newer than it is
             "made": now_iso(),
             "source": "OpenStreetMap contributors, via Geofabrik",
             "license": "Open Database License (ODbL 1.0), https://www.openstreetmap.org/copyright",
             "format": "Each tile is {\"e\": [[type, id, lat, lon, tags], ...]} with type n/w/r. Tiles are 1-degree squares "
                       "named by their southwest corner; cover lists every square the data covers.",
             "states": dates, "counts": counts, "cover": sorted(cover), "tiles": {}}
    for (layer, key), els in sorted(squares.items()):
        d = os.path.join(out, "tiles", layer)
        os.makedirs(d, exist_ok=True)
        els.sort(key=lambda e: (e[2], e[3], e[0], e[1]))   # same data, same file: small weekly changes
        with open(os.path.join(d, f"{key}.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"e": els}, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
        index["tiles"].setdefault(layer, []).append(key)
    with open(os.path.join(out, "tiles", "index.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
    with open(os.path.join(out, "tiles", "README.md"), "w", encoding="utf-8") as f:
        f.write("# Camp map places\n\nMap squares for laporteweathernow.com/camp-map (The Chase), rebuilt weekly by "
                "`scripts/places_build.py` and `.github/workflows/places.yml`. Don't edit these by hand.\n\n"
                "Map data (c) OpenStreetMap contributors, https://www.openstreetmap.org/copyright, available under the "
                "Open Database License (ODbL 1.0). These derived files are offered under the same license.\n")
    os.makedirs(os.path.join(out, "parts"))
    for s in STATES:
        with open(os.path.join(out, "parts", f"{s}.json"), "w", encoding="utf-8") as f:
            json.dump(use[s], f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out, "parts", "README.md"), "w", encoding="utf-8") as f:
        f.write("# Last week's states\n\nEach state's places from the latest weekly build of the camp map squares, kept so "
                "a state that fails to download keeps its earlier copy. Replaced every week.\n\n"
                "Map data (c) OpenStreetMap contributors, ODbL 1.0.\n")
    print(f"Saved {len(places)} places in {len(squares)} files; data from {index['built'][:10]} or newer.")
    return 0


def check(index_json):
    """A real problem worth an alarm: a state that hasn't had a fresh download in four weeks."""
    with open(index_json, encoding="utf-8") as f:
        index = json.load(f)
    old = {s: d[:10] for s, d in index.get("states", {}).items() if age_days(d) > STALE_DAYS}
    if old:
        print("These states haven't downloaded in over four weeks (the map still shows their older copy):", old)
        return 1
    print("Every state's data is under four weeks old.")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["states"]:
        print(json.dumps(STATES, separators=(",", ":")))
        sys.exit(0)
    if len(args) == 3 and args[0] == "extract":
        sys.exit(extract(args[1], args[2]))
    if len(args) == 4 and args[0] == "tiles":
        sys.exit(tiles(args[1], args[2], args[3]))
    if len(args) == 2 and args[0] == "check":
        sys.exit(check(args[1]))
    print(__doc__)
    sys.exit(2)
