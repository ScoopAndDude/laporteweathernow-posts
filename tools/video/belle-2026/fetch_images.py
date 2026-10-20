#!/usr/bin/env python3
"""Finds and downloads real pictures for the Halloween shorts (runs in GitHub Actions, belle-images.yml).

Wikimedia Commons: only public domain, CC0, CC BY and CC BY-SA files are kept, each with its author and
license for the credit. Library of Congress (Chronicling America): front pages of 1908 newspapers, which
are public domain. Saves images/<name>-NN.jpg (at most 1600 px) and images/manifest.json."""
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "images")
UA = "LaPorteWeatherNow/1.0 (https://laporteweathernow.com; laporteweathernow@gmail.com) Halloween video picture search"
OK_LICENSE = re.compile(r"^(public domain|pd|cc0|cc[- ]by(-sa)?([- ][0-9.]+)?|cc[- ]by[- ]sa[- ][0-9.]+)", re.I)


def get(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(2 + 3 * k)


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def commons(q):
    params = {"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": "1600"}
    if q.get("category"):
        params.update({"generator": "categorymembers", "gcmtitle": q["category"], "gcmtype": "file", "gcmlimit": str(q.get("max", 20))})
    else:
        params.update({"generator": "search", "gsrsearch": q["search"], "gsrnamespace": "6", "gsrlimit": str(q.get("max", 20))})
    data = json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)))
    out = []
    for p in (data.get("query", {}).get("pages", {}) or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {}) or {}
        val = lambda k: clean((md.get(k) or {}).get("value", ""))
        out.append({"title": p.get("title"), "page": ii.get("descriptionurl"), "url": ii.get("thumburl") or ii.get("url"),
                    "mime": ii.get("mime"), "width": ii.get("width"), "height": ii.get("height"),
                    "license": val("LicenseShortName"), "usage": val("UsageTerms"), "artist": val("Artist")[:160],
                    "credit": val("Credit")[:200], "date": val("DateTimeOriginal")[:60], "desc": val("ImageDescription")[:400]})
    return out


def loc_pages(q):
    params = {"andtext": q["text"], "date1": q["from"], "date2": q["to"], "dateFilterType": "range", "searchType": "advanced",
              "rows": str(q.get("max", 10)), "format": "json"}
    out = []
    try:
        data = json.loads(get("https://chroniclingamerica.loc.gov/search/pages/results/?" + urllib.parse.urlencode(params)))
        for it in data.get("items", []):
            pid = it.get("id", "")          # like /lccn/sn84026749/1908-05-06/ed-1/seq-1/
            out.append({"title": f"{it.get('title', '').strip()} ({it.get('date', '')}), page {it.get('sequence', '')}",
                        "page": "https://chroniclingamerica.loc.gov" + pid, "url": "https://chroniclingamerica.loc.gov" + pid.rstrip("/") + ".jp2",
                        "thumb": "https://chroniclingamerica.loc.gov" + pid + "thumbnail.jpg",
                        "license": "Public domain (1908)", "artist": it.get("title", "").strip(), "date": it.get("date", ""),
                        "credit": "Library of Congress, Chronicling America", "desc": (it.get("ocr_eng") or "")[:300]})
    except Exception as e:
        print("Library of Congress search didn't answer:", e)
    return out


def save(item, path):
    raw = get(item["url"])
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    img.thumbnail((1600, 1600))
    img.save(path, quality=90)
    return img.size


def main():
    spec = json.load(open(os.path.join(HERE, "images.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    manifest, seen = [], set()
    for q in spec["commons"]:
        try:
            found = commons(q)
        except Exception as e:
            print(q["name"], "didn't answer:", e)
            continue
        k = 0
        for it in sorted(found, key=lambda x: x["title"] or ""):
            if it["title"] in seen or not it["url"] or not (it["mime"] or "").startswith("image/") or "svg" in (it["mime"] or ""):
                continue
            if not OK_LICENSE.match(it["license"] or ""):
                print("skip (license):", it["title"], "|", it["license"])
                continue
            seen.add(it["title"])
            k += 1
            path = os.path.join(OUT, f"{q['name']}-{k:02d}.jpg")
            try:
                size = save(it, path)
            except Exception as e:
                print("couldn't download", it["title"], e)
                continue
            it.update({"file": os.path.basename(path), "saved": size, "source": "Wikimedia Commons"})
            manifest.append(it)
            print("saved", it["file"], it["title"], "|", it["license"], "|", it["artist"][:60])
            time.sleep(0.4)
    lq = spec.get("loc_newspapers")
    if lq:
        for k, it in enumerate(loc_pages(lq), 1):
            path = os.path.join(OUT, f"newspaper-{k:02d}.jpg")
            try:
                size = save(it, path)
            except Exception as e:
                try:
                    it["url"] = it["thumb"]
                    size = save(it, path)
                except Exception as e2:
                    print("couldn't download", it["title"], e, e2)
                    continue
            it.update({"file": os.path.basename(path), "saved": size, "source": "Library of Congress"})
            manifest.append(it)
            print("saved", it["file"], it["title"])
            time.sleep(0.5)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    print(len(manifest), "pictures saved")


if __name__ == "__main__":
    main()
