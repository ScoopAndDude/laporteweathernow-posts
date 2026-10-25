#!/usr/bin/env python3
"""Finds and downloads real pictures for the Stanley Hotel documentary (runs in GitHub Actions,
.github/workflows/stanley-doc-images.yml, because the cloud workspace can't reach these sites).
Copied from tools/video/belle-doc/fetch.py on the belle-doc branch; only the newspaper search's fallback changed.

- Wikimedia Commons: only public domain, CC0 and CC BY files (no share-alike, non-commercial or
  no-derivatives), each with its author and license for the credit.
- Library of Congress photos and maps: only items the Library marks "no known restrictions" (or public domain).
- Library of Congress Chronicling America: 1908-1909 newspaper pages that mention Gunness (public domain).
  The OCR word positions find the "Gunness" headlines, and each headline block is also saved as a crop.

Saves images/<name>-NN.jpg, images/manifest.json (title, page, url, license, artist, credit, date, desc)
and images/fetch-log.txt (everything it tried, since the job's own log can't be read from the workspace).

    fetch.py --extra     a second, smaller pass (sources-extra.json): adds pictures to the list without touching
                         the ones already there (their numbers stay the same): sharper copies of chosen pictures,
                         full-resolution clippings of chosen newspaper headlines, and a few new searches.
                         New files are listed in images/extra-files.txt; the log is images/fetch-log-extra.txt.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "images")
os.makedirs(OUT, exist_ok=True)
LOGF = None                    # opened in main (fetch-log.txt, or fetch-log-extra.txt for --extra)
UA = "LaPorteWeatherNow/1.0 (https://laporteweathernow.com; laporteweathernow@gmail.com) documentary picture search"
MAX_SIDE = 2000


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    if LOGF:
        print(s, file=LOGF)
        LOGF.flush()


_last = {"loc": 0.0}


def get(url, tries=4, loc=False):
    for k in range(tries):
        if loc:                                   # the Library asks for no more than ~20 requests per 10 s
            wait = 1.2 - (time.time() - _last["loc"])
            if wait > 0:
                time.sleep(wait)
            _last["loc"] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                log("  429 (too many requests), waiting 90 s:", url[:120])
                time.sleep(90)
            elif e.code in (404, 403, 400) or k == tries - 1:
                raise
            else:
                time.sleep(3 + 4 * k)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(3 + 4 * k)


def getjson(url, loc=False):
    return json.loads(get(url, loc=loc))


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def license_ok(s):
    s = (s or "").strip().lower()
    if not s:
        return False
    if any(w in s for w in ("-sa", " sa ", "sharealike", "share alike", "-nc", " nc", "noncommercial", "-nd", " nd ",
                            "fair use", "non-free", "copyrighted")):
        return False
    return s.startswith(("public domain", "pd", "cc0", "no restrictions", "cc by", "cc-by", "attribution"))


def save_image(raw, path, max_side=MAX_SIDE):
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    img.save(path, quality=88)
    return img.size


manifest, seen = [], set()
NEW_FILES = []                 # files saved in this run (for the --extra zip)


def add(entry, raw, name, k, max_side=MAX_SIDE, filename=None):
    path = os.path.join(OUT, filename or f"{name}-{k:02d}.jpg")
    size = save_image(raw, path, max_side)
    entry.update({"file": os.path.basename(path), "saved": list(size)})
    manifest.append(entry)
    NEW_FILES.append(entry["file"])
    log("  saved", entry["file"], size, "|", entry.get("license", ""), "|", (entry.get("artist") or "")[:50], "|", (entry.get("title") or "")[:90])


# ------------------------------------------------------------------ Wikimedia Commons
API = "https://commons.wikimedia.org/w/api.php?"


def commons_pages(params, limit):
    out, cont = [], {}
    while len(out) < limit:
        p = dict(params, **cont)
        data = getjson(API + urllib.parse.urlencode(p))
        out.extend((data.get("query", {}).get("pages", {}) or {}).values())
        if "continue" not in data:
            break
        cont = data["continue"]
    return out[:limit]


def subcats(cat, depth):
    cats, frontier = [cat], [cat]
    for _ in range(depth):
        nxt = []
        for c in frontier:
            try:
                data = getjson(API + urllib.parse.urlencode({"action": "query", "format": "json", "list": "categorymembers",
                                                             "cmtitle": c, "cmtype": "subcat", "cmlimit": "100"}))
                nxt += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
            except Exception as e:
                log("  subcats failed", c, e)
        cats += nxt
        frontier = nxt
    return cats


def commons(q):
    base = {"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime",
            "iiurlwidth": str(MAX_SIDE)}
    pages = []
    if q.get("category"):
        for c in subcats(q["category"], q.get("depth", 0)):
            pages += commons_pages(dict(base, generator="categorymembers", gcmtitle=c, gcmtype="file", gcmlimit="50"), q.get("max", 50))
            if len(pages) >= q.get("max", 50) * 2:
                break
    else:
        pages = commons_pages(dict(base, generator="search", gsrsearch=q["search"], gsrnamespace="6", gsrlimit="50"), q.get("max", 50))
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {}) or {}
        val = lambda k: clean((md.get(k) or {}).get("value", ""))
        out.append({"title": p.get("title"), "page": ii.get("descriptionurl"), "url": ii.get("thumburl") or ii.get("url"),
                    "mime": ii.get("mime") or "", "width": ii.get("width"), "height": ii.get("height"),
                    "license": val("LicenseShortName"), "usage": val("UsageTerms"), "artist": val("Artist")[:160],
                    "credit": val("Credit")[:200], "date": val("DateTimeOriginal")[:60], "desc": val("ImageDescription")[:500],
                    "source": "Wikimedia Commons"})
    return out


# ------------------------------------------------------------------ Library of Congress
def iiif_base(u):
    m = re.match(r"(https://tile\.loc\.gov/image-services/iiif/[^/]+)/", u or "")
    return m.group(1) if m else None


def loc_items(endpoint, q, dates=None, limit=30):
    params = {"q": q, "fo": "json", "c": str(min(100, max(limit, 25)))}
    if dates:
        params["dates"] = dates
    url = f"https://www.loc.gov/{endpoint}/?" + urllib.parse.urlencode(params)
    data = getjson(url, loc=True)
    res = data.get("results", [])
    log(f"  {endpoint} '{q}' {dates or ''}: {len(res)} results")
    return res[:limit]


def loc_rights(item_json):
    it = item_json.get("item", {}) or {}
    texts = []
    for key in ("rights_advisory", "rights", "rights_information"):
        v = it.get(key) or item_json.get(key)
        if isinstance(v, list):
            texts += [str(x) for x in v]
        elif v:
            texts.append(str(v))
    return " ".join(texts)


def loc_fetch(spec, endpoint, max_side):
    k = 0
    try:
        results = loc_items(endpoint, spec["q"], spec.get("dates"), spec.get("max", 30))
    except Exception as e:
        log("  search failed:", e)
        return
    for r in results:
        rid = r.get("id") or r.get("url")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        base = next((iiif_base(u) for u in (r.get("image_url") or []) if iiif_base(u)), None)
        if not base:
            log("  no picture:", r.get("title", "")[:80])
            continue
        try:
            ij = getjson(rid.split("?")[0].rstrip("/") + "/?fo=json", loc=True)
        except Exception as e:
            log("  item failed:", rid, e)
            continue
        rights = loc_rights(ij)
        if not re.search(r"no known (copyright )?restrictions|public domain|no known restriction", rights, re.I):
            log("  skip (rights):", r.get("title", "")[:70], "|", rights[:120])
            continue
        it = ij.get("item", {}) or {}
        try:
            raw = get(f"{base}/full/!{max_side},{max_side}/0/default.jpg", loc=True)
        except Exception as e:
            try:
                raw = get(f"{base}/full/pct:50/0/default.jpg", loc=True)
            except Exception as e2:
                log("  download failed:", base, e, e2)
                continue
        k += 1
        creators = it.get("contributor_names") or it.get("creators") or r.get("contributor") or []
        add({"title": clean(r.get("title") or it.get("title") or ""), "page": rid, "url": base,
             "license": "No known restrictions (Library of Congress)", "rights": rights[:300],
             "artist": clean("; ".join(c if isinstance(c, str) else c.get("title", "") for c in creators))[:160],
             "credit": "Library of Congress", "date": str(r.get("date") or it.get("date") or "")[:40],
             "desc": clean(" ".join(it.get("summary", []) if isinstance(it.get("summary"), list) else [str(it.get("summary") or "")]))[:500],
             "source": "Library of Congress"}, raw, spec["name"], k, max_side)


# ------------------------------------------------------------------ Chronicling America (1908 newspapers)
def alto_blocks(xml_bytes, pattern):
    """(page_w, page_h, [(score, x, y, w, h, text)]) for text blocks containing the pattern."""
    root = ET.fromstring(xml_bytes)
    strip = lambda t: t.split("}")[-1]
    page = next((e for e in root.iter() if strip(e.tag) == "Page"), None)
    pw, ph = float(page.get("WIDTH")), float(page.get("HEIGHT"))
    blocks = []
    for tb in (e for e in root.iter() if strip(e.tag) == "TextBlock"):
        words = [s for s in tb.iter() if strip(s.tag) == "String"]
        text = " ".join(s.get("CONTENT", "") for s in words)
        hits = [s for s in words if re.search(pattern, s.get("CONTENT", ""), re.I)]
        if not hits:
            continue
        score = max(float(s.get("HEIGHT", 0)) for s in hits)
        blocks.append((score, float(tb.get("HPOS")), float(tb.get("VPOS")), float(tb.get("WIDTH")), float(tb.get("HEIGHT")), text[:400]))
    blocks.sort(reverse=True)
    return pw, ph, blocks


def find_alto_url(obj):
    s = json.dumps(obj)
    m = re.search(r'https?://tile\.loc\.gov/text-services/word-coordinates-service\?[^"\s]+', s)
    if m:
        u = m.group(0).replace("\\u0026", "&")
        return u if "format=alto_xml" in u else u + "&format=alto_xml"
    return None


def newspapers(spec):
    d0, d1 = spec["dates"].split("/")
    tries = [                     # the first form that gives pages inside the dates wins (some forms ignore the dates)
        ("collections/chronicling-america", {"qs": spec["q"], "ops": "AND", "searchType": "advanced", "start_date": d0, "end_date": d1, "dl": "page"}),
        ("collections/chronicling-america", {"q": spec["q"], "start_date": d0, "end_date": d1, "dl": "page"}),
        ("collections/chronicling-america", {"q": spec["q"], "dates": d0 + "/" + d1}),
        ("collections/chronicling-america", {"q": spec["q"], "dates": d0[:4] + "/" + d1[:4]}),
        ("search", {"q": (spec["q"] + " " + spec.get("place", "")).strip(), "fa": "original-format:newspaper", "dates": d0[:4] + "/" + d1[:4]}),
    ]
    results = []
    for ep, params in tries:
        params = dict(params, fo="json", c="100")
        url = f"https://www.loc.gov/{ep}/?" + urllib.parse.urlencode(params)
        try:
            data = getjson(url, loc=True)
            res = [r for r in data.get("results", []) if any(iiif_base(u) for u in (r.get("image_url") or []))
                   and d0 <= str(r.get("date", ""))[:10] <= d1]
            log(f"  newspaper search {url[:180]} -> {len(data.get('results', []))} results, {len(res)} inside the dates with pictures")
            if res:
                log("  first result keys:", sorted(res[0].keys())[:40])
                results = res
                break
        except Exception as e:
            log("  newspaper search failed:", url[:160], e)
    if not results:
        return
    # earliest pages first (the first weeks of May 1908 had the biggest headlines), one page per paper per day
    results.sort(key=lambda r: (str(r.get("date", "")), str(r.get("id", ""))))
    name = spec.get("name", "news")
    k, per_day = 0, set()
    for r in results:
        if k >= spec.get("max", 60):
            break
        title = clean(r.get("title", ""))
        paper = clean((r.get("partof_title") or [title])[0] if isinstance(r.get("partof_title"), list) else (r.get("partof_title") or title))
        day_key = (paper, str(r.get("date", "")))
        if day_key in per_day:
            continue
        rid = r.get("id") or ""
        if rid.split("&q=")[0] in seen:
            continue
        base = next((iiif_base(u) for u in r.get("image_url") or [] if iiif_base(u)), None)
        try:
            info = getjson(base + "/info.json", loc=True)
            iw, ih = int(info["width"]), int(info["height"])
        except Exception as e:
            log("  info.json failed:", base, e)
            continue
        crops = []
        try:
            if not spec.get("crops_per_page", 3):
                raise StopIteration
            res_json = getjson(rid.split("#")[0] + ("&" if "?" in rid else "?") + "fo=json", loc=True)
            alto_url = find_alto_url(res_json)
            if alto_url:
                pw, ph, blocks = alto_blocks(get(alto_url, loc=True), spec["q"])
                sx, sy = iw / pw, ih / ph
                for score, x, y, w, h, text in blocks[: spec.get("crops_per_page", 3)]:
                    pad = 0.15
                    X0, Y0 = max(0, int((x - w * pad) * sx)), max(0, int((y - h * pad - 40) * sy))
                    X1, Y1 = min(iw, int((x + w * (1 + pad)) * sx)), min(ih, int((y + h * (1 + pad) + 40) * sy))
                    crops.append({"box": [X0, Y0, X1 - X0, Y1 - Y0], "score": score, "text": text})
            else:
                log("  no word positions for", rid[:100])
        except StopIteration:
            pass
        except Exception as e:
            log("  word positions failed:", rid[:100], e)
        try:
            raw = get(f"{base}/full/!2600,2600/0/default.jpg", loc=True)
        except Exception as e:
            log("  page download failed:", base, e)
            continue
        per_day.add(day_key)
        seen.add(rid.split("&q=")[0])
        k += 1
        entry = {"title": f"{paper}, {r.get('date', '')}", "page": rid.split("&q=")[0], "url": base,
                 "license": spec.get("license", "Public domain (1908 newspaper)"),
                 "artist": paper, "credit": "Library of Congress, Chronicling America", "date": str(r.get("date", "")),
                 "desc": clean(" ".join(r.get("description", []) if isinstance(r.get("description"), list) else [str(r.get("description") or "")]))[:300],
                 "source": "Library of Congress", "kind": "newspaper-page", "page_size": [iw, ih], "crops": []}
        add(entry, raw, name, k, max_side=2600)
        for j, c in enumerate(crops, 1):
            x, y, w, h = c["box"]
            if w < 50 or h < 30:
                continue
            try:
                raw_c = get(f"{base}/{x},{y},{w},{h}/!2000,2000/0/default.jpg", loc=True)
            except Exception as e:
                log("  crop failed:", e)
                continue
            path = os.path.join(OUT, f"{name}-{k:02d}-crop{j}.jpg")
            size = save_image(raw_c, path, 2000)
            entry["crops"].append({"file": os.path.basename(path), "box": c["box"], "score": c["score"], "text": c["text"], "saved": list(size)})
            log("    crop", os.path.basename(path), size, "|", c["text"][:100])


def write_manifest():
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ the second pass (--extra)
def commons_original(title):
    """The full-size file URL for a Commons file title."""
    data = getjson(API + urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|size",
                                                "titles": title}))
    page = next(iter((data.get("query", {}).get("pages", {}) or {}).values()), {})
    ii = (page.get("imageinfo") or [{}])[0]
    return ii.get("url"), ii.get("width"), ii.get("height")


def hires_copies(items, old):
    """Sharper copies of Commons pictures already on the list: {"file": "gunness-45.jpg", "out": "gunness-45-hi", "max_side": 4600}."""
    by_file = {x["file"]: x for x in old}
    for h in items:
        if h["out"] + ".jpg" in by_file:
            continue                                  # made by an earlier run
        src = by_file.get(h["file"])
        if not src:
            log("  not on the list:", h["file"])
            continue
        try:
            url, w, hh = commons_original(src["title"])
            raw = get(url)
        except Exception as e:
            log("  original failed:", src["title"], e)
            continue
        entry = {k: v for k, v in src.items() if k not in ("file", "saved")}
        entry.update({"url": url, "hires_of": h["file"]})
        add(entry, raw, "", 0, max_side=int(h.get("max_side", 5000)), filename=h["out"] + ".jpg")


def news_clips(items, old):
    """Full-resolution cut-outs of newspaper pages already on the list: {"file": "news-02.jpg", "box": [x0, y0, x1, y1]
    (fractions of the page), "out": "news-02-a"}. Each page is downloaded once at full size and cut here (asking the
    Library's server for a region gave back a blurred, enlarged copy)."""
    by_file = {x["file"]: x for x in old}
    pages = {}
    for c in items:
        if c["out"] + ".jpg" in by_file:
            continue                                  # made by an earlier run
        pages.setdefault(c["file"], []).append(c)
    for pfile, clips in pages.items():
        src = by_file.get(pfile)
        if not src or not src.get("url"):
            log("  page not on the list:", pfile)
            continue
        base = src["url"]
        iw, ih = src.get("page_size") or (None, None)
        if not iw:
            try:
                info = getjson(base + "/info.json", loc=True)
                iw, ih = int(info["width"]), int(info["height"])
            except Exception as e:
                log("  info.json failed:", pfile, e)
                continue
        big = None
        for size in (f"!{max(iw, ih)},{max(iw, ih)}", "full", "pct:75", "!5200,5200"):
            try:
                big = Image.open(io.BytesIO(get(f"{base}/full/{size}/0/default.jpg", loc=True))).convert("RGB")
                log(f"  page {pfile} at {size}: {big.size}")
                break
            except Exception as e:
                log(f"  page {pfile} at {size} failed:", e)
        if big is None:
            continue
        bw, bh = big.size
        for c in clips:
            x0, y0, x1, y1 = c["box"]
            box = (int(max(0, x0) * bw), int(max(0, y0) * bh), int(min(1, x1) * bw), int(min(1, y1) * bh))
            crop = big.crop(box)
            m = int(c.get("max_side", 3600))
            crop.thumbnail((m, m), Image.LANCZOS)
            path = os.path.join(OUT, c["out"] + ".jpg")
            crop.save(path, quality=90)
            entry = {k: v for k, v in src.items() if k not in ("file", "saved", "crops")}
            entry.update({"clip_of": pfile, "box": c["box"], "clip_px": [box[0], box[1], box[2] - box[0], box[3] - box[1]],
                          "note": c.get("note", ""), "file": c["out"] + ".jpg", "saved": list(crop.size)})
            manifest.append(entry)
            NEW_FILES.append(entry["file"])
            log("  saved", entry["file"], crop.size, "|", c.get("note", ""))
        del big


def resource_pages(items, old):
    """Whole newspaper pages named by their Library of Congress address, saved at full size (for headlines the
    film zooms into): {"name": "bee-0429", "url": "https://www.loc.gov/resource/.../?sp=1", "paper": ..., "date": ...}."""
    have = {x["file"] for x in old}
    for r in items:
        out = r["name"] + ".jpg"
        if out in have:
            continue
        try:
            js = getjson(r["url"].split("#")[0] + ("&" if "?" in r["url"] else "?") + "fo=json", loc=True)
        except Exception as e:
            log("  page lookup failed:", r["url"], e)
            continue
        urls = re.findall(r'https://tile\.loc\.gov/image-services/iiif/[^"\s]+', json.dumps(js))
        base = next((iiif_base(u) for u in urls if iiif_base(u)), None)
        if not base:
            log("  no picture service for", r["url"])
            continue
        try:
            info = getjson(base + "/info.json", loc=True)
            iw, ih = int(info["width"]), int(info["height"])
        except Exception as e:
            log("  info.json failed:", base, e)
            iw, ih = None, None
        raw = None
        m = int(r.get("max_side", 9000))
        for size in ([f"!{max(iw, ih)},{max(iw, ih)}"] if iw else []) + [f"!{m},{m}", "full", "pct:50"]:
            try:
                raw = get(f"{base}/full/{size}/0/default.jpg", loc=True)
                break
            except Exception as e:
                log(f"  {r['name']} at {size} failed:", e)
        if raw is None:
            continue
        entry = {"title": f"{r.get('paper', '')}, {r.get('date', '')}", "page": r["url"], "url": base,
                 "license": r.get("license", "Public domain (1908 newspaper)"), "artist": r.get("paper", ""),
                 "credit": "Library of Congress, Chronicling America", "date": r.get("date", ""), "desc": r.get("note", ""),
                 "source": "Library of Congress", "kind": "newspaper-page", "page_size": [iw, ih], "note": r.get("note", "")}
        add(entry, raw, "", 0, max_side=m, filename=out)


def main_extra():
    global LOGF
    LOGF = open(os.path.join(OUT, "fetch-log-extra.txt"), "w", encoding="utf-8")
    spec = json.load(open(os.path.join(HERE, "sources-extra.json"), encoding="utf-8"))
    old = json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))
    manifest.extend(old)
    for x in old:
        seen.add(x.get("title"))
        seen.add(x.get("page"))
    log(len(old), "pictures already on the list")
    if spec.get("commons_hires"):
        log("Sharper copies:", len(spec["commons_hires"]))
        hires_copies(spec["commons_hires"], old)
        write_manifest()
    if spec.get("news_clips"):
        log("Newspaper clippings at full resolution:", len(spec["news_clips"]))
        news_clips(spec["news_clips"], old)
        write_manifest()
    if spec.get("resource_pages"):
        log("Whole pages at full size:", len(spec["resource_pages"]))
        resource_pages(spec["resource_pages"], old)
        write_manifest()
    taken = {re.sub(r"-\d+\.jpg$", "", x["file"]) for x in old}
    for q in spec.get("commons", []):
        if q["name"] in taken:
            log("  name already used, skipped:", q["name"])
            continue
        log("Commons:", q["name"], q.get("category") or q.get("search"))
        try:
            found = commons(q)
        except Exception as e:
            log("  didn't answer:", e)
            continue
        k = 0
        for it in sorted(found, key=lambda x: x["title"] or ""):
            if k >= q.get("max", 50):
                break
            if it["title"] in seen or not it["url"] or not it["mime"].startswith("image/") or "svg" in it["mime"]:
                continue
            if not license_ok(it["license"]):
                log("  skip (license):", it["title"][:90], "|", it["license"])
                continue
            seen.add(it["title"])
            try:
                raw = get(it["url"])
            except Exception as e:
                log("  couldn't download", it["title"], e)
                continue
            k += 1
            add(it, raw, q["name"], k)
            time.sleep(0.3)
        write_manifest()
    for q in spec.get("newspapers", []):
        if q["name"] in taken:
            log("  name already used, skipped:", q["name"])
            continue
        log("Chronicling America:", q)
        try:
            newspapers(dict(q, crops_per_page=0))
        except Exception as e:
            log("  stopped:", e)
        write_manifest()
    write_manifest()
    with open(os.path.join(OUT, "extra-files.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(NEW_FILES) + "\n")
    log(len(NEW_FILES), "new pictures saved;", len(manifest), "on the list")


def main():
    global LOGF
    if "--extra" in sys.argv:
        return main_extra()
    LOGF = open(os.path.join(OUT, "fetch-log.txt"), "w", encoding="utf-8")
    spec = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))
    only = set(sys.argv[1:])
    for q in spec.get("commons", []):
        if only and q["name"] not in only:
            continue
        log("Commons:", q["name"], q.get("category") or q.get("search"))
        try:
            found = commons(q)
        except Exception as e:
            log("  didn't answer:", e)
            continue
        k = 0
        for it in sorted(found, key=lambda x: x["title"] or ""):
            if k >= q.get("max", 50):
                break
            if it["title"] in seen or not it["url"] or not it["mime"].startswith("image/") or "svg" in it["mime"]:
                continue
            if not license_ok(it["license"]):
                log("  skip (license):", it["title"][:90], "|", it["license"])
                continue
            seen.add(it["title"])
            try:
                raw = get(it["url"])
            except Exception as e:
                log("  couldn't download", it["title"], e)
                continue
            k += 1
            add(it, raw, q["name"], k)
            time.sleep(0.3)
        write_manifest()
    for q in spec.get("loc_photos", []):
        if only and q["name"] not in only:
            continue
        log("Library of Congress photos:", q["name"], q["q"])
        loc_fetch(q, "photos", MAX_SIDE)
        write_manifest()
    for q in spec.get("loc_maps", []):
        if only and q["name"] not in only:
            continue
        log("Library of Congress maps:", q["name"], q["q"])
        loc_fetch(q, "maps", 3200)
        write_manifest()
    if spec.get("newspapers") and (not only or "news" in only):
        log("Chronicling America:", spec["newspapers"])
        newspapers(spec["newspapers"])
    write_manifest()
    log(len(manifest), "pictures saved")


if __name__ == "__main__":
    main()
