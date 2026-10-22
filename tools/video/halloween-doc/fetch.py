#!/usr/bin/env python3
"""Finds and downloads real pictures for the History of Halloween documentary (runs in GitHub Actions,
.github/workflows/halloween-doc-images.yml, because the cloud workspace can't reach these sites). Same rules and
code as the Belle Gunness film's fetch.py.

- Wikimedia Commons: only public domain, CC0 and CC BY files (no share-alike, non-commercial or
  no-derivatives), each with its author and license for the credit.
- Library of Congress photos and maps: only items the Library marks "no known restrictions" (or public domain).
- Library of Congress Chronicling America: old newspaper pages for each search (public domain, or no known
  restrictions). The OCR word positions find the headline blocks with the search's "pattern", saved as crops too.
- Every picture in one Library of Congress item (loc_items, e.g. the HABS survey of the lighthouse).
- Pages of public-domain books on the Internet Archive that mention a name (archive_books).

Saves images/<name>-NN.jpg, images/manifest.json (title, page, url, license, artist, credit, date, desc)
and images/fetch-log.txt (everything it tried, since the job's own log can't be read from the workspace).

    fetch.py --extra     a second, smaller pass (sources-extra.json): adds pictures to the list without touching
                         the ones already there (their numbers stay the same): sharper copies of chosen pictures,
                         full-resolution clippings of chosen newspaper headlines, and a few new searches.
                         New files are listed in images/extra-files.txt; the log is images/fetch-log-extra.txt.
"""
import io
import glob
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


_last = {"loc": 0.0, "429": 0}
DEADLINE = [None]              # time.time() after which every loop stops, so the zip step still runs


def out_of_time():
    return DEADLINE[0] is not None and time.time() > DEADLINE[0]


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
                _last["429"] += 1
                if _last["429"] > 25 or out_of_time():
                    raise                                # the Library is refusing: give up on it for this run
                log("  429 (too many requests), waiting 40 s:", url[:120])
                time.sleep(40)
            elif e.code in (404, 403, 400) or k == tries - 1:
                raise
            else:
                time.sleep(8 + 10 * k)                 # 520s from the Library's front door: back off
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
    elif q.get("titles"):                     # exact file names, 40 at a time
        for i in range(0, len(q["titles"]), 40):
            pages += commons_pages(dict(base, titles="|".join(q["titles"][i:i + 40])), 40)
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
    max_side = int(spec.get("max_side", max_side))
    k = 0
    try:
        results = loc_items(endpoint, spec["q"], spec.get("dates"), spec.get("max", 30))
    except Exception as e:
        log("  search failed:", e)
        return
    for r in results:
        if out_of_time() or _last["429"] > 25:
            break
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
        if not re.search(r"no known (copyright )?restrictions|public domain|no known restriction|free to use and reuse|not aware of any u\.?s\.? copyright", rights, re.I):
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


def loc_item_pages(spec):
    """Every picture in one Library of Congress item (a HABS survey has photos, data pages and drawings):
    {"name": "habs-lh", "item": "https://www.loc.gov/item/in0149/", "max": 40}."""
    try:
        ij = getjson(spec["item"].split("?")[0].rstrip("/") + "/?fo=json", loc=True)
    except Exception as e:
        log("  item failed:", spec["item"], e)
        return
    rights = loc_rights(ij)
    log("  rights:", rights[:200])
    if not re.search(r"no known (copyright )?restrictions|public domain|no known restriction|free to use and reuse|not aware of any u\.?s\.? copyright", rights, re.I):
        log("  skip (rights)")
        return
    it = ij.get("item", {}) or {}
    res = ij.get("resources") or []
    log("  resources:", len(res), [(r.get("url"), r.get("files") if isinstance(r.get("files"), int) else len(r.get("files") or [])) for r in res][:60])
    bases = []
    # the item's file list names each page's master file; its IIIF id is the storage path with ":" for "/"
    for r in res:
        for page in (r.get("files") if isinstance(r.get("files"), list) else []):
            for f in (page if isinstance(page, list) else [page]):
                u = (f or {}).get("url", "") if isinstance(f, dict) else ""
                mm = re.search(r"tile\.loc\.gov/storage-services/(?:master|service)/(pnp/.+?)\.(?:tif|jpg|jp2)$", u)
                if mm:
                    b = "https://tile.loc.gov/image-services/iiif/service:" + mm.group(1).replace("/", ":")
                    if b not in [x[0] for x in bases]:
                        bases.append((b, r.get("url", ""), ""))
                    break
            if len(bases) >= spec.get("max", 40):
                break
    if bases:
        log("  pages from the file list:", len(bases))
        res = []                                     # skip the page-by-page lookup below
    for r in res:
        u = r.get("url")
        if not u:
            continue
        n = r.get("files") if isinstance(r.get("files"), int) else 1
        for sp in range(1, max(1, min(n, spec.get("max", 40))) + 1):
            pu = re.sub(r"([?&])sp=\d+", r"\1sp=%d" % sp, u) if "sp=" in u else u + ("&" if "?" in u else "?") + f"sp={sp}"
            try:
                js = getjson(pu.split("#")[0] + "&fo=json", loc=True)
            except Exception as e:
                log("  page failed:", pu, e)
                continue
            found = [iiif_base(x) for x in re.findall(r'https://tile\.loc\.gov/image-services/iiif/[^"\s]+', json.dumps(js))]
            found = [b for b in found if b]
            pg = js.get("page")
            cap = clean(str((pg.get("title") if isinstance(pg, dict) else "") or r.get("caption") or ""))
            # the page's own picture is the one named most often in its record
            if found:
                b = max(set(found), key=found.count)
                if b not in [x[0] for x in bases]:
                    bases.append((b, pu, cap))
            if len(bases) >= spec.get("max", 40):
                break
        if len(bases) >= spec.get("max", 40):
            break
    k = 0
    for b, pu, cap in bases:
        try:
            raw = get(f"{b}/full/!{spec.get('max_side', 3000)},{spec.get('max_side', 3000)}/0/default.jpg", loc=True)
        except Exception as e:
            try:
                raw = get(f"{b}/full/pct:50/0/default.jpg", loc=True)
            except Exception as e2:
                log("  download failed:", b, e, e2)
                continue
        k += 1
        add({"title": clean(it.get("title") or ij.get("title") or ""), "page": pu, "url": b, "caption": cap[:200],
             "license": "No known restrictions (Library of Congress)", "rights": rights[:300],
             "artist": clean("; ".join(c if isinstance(c, str) else c.get("title", "") for c in (it.get("contributor_names") or [])))[:160],
             "credit": "Library of Congress", "date": str(it.get("date") or "")[:40], "source": "Library of Congress"},
            raw, spec["name"], k, spec.get("max_side", 3000))


def archive_books(spec):
    """Pages of an old book on the Internet Archive that mention a name: {"name": "hardinge", "id": "modernamericansp00brit",
    "find": ["Cathcart"], "max": 6, "license": "Public domain (1870 book)", "title": ..., "author": ...}. The book's PDF
    (with its text layer) is downloaded, searched page by page and the matching pages are drawn at about 200 dpi."""
    ids = [spec["id"]] if spec.get("id") else []
    if spec.get("search"):                           # or find the book first
        try:
            js = getjson("https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
                {"q": spec["search"], "fl[]": "identifier", "rows": "8", "output": "json"}))
            ids += [d["identifier"] for d in js.get("response", {}).get("docs", []) if d.get("identifier") not in ids]
            log("  books found:", ids)
        except Exception as e:
            log("  book search failed:", e)
    k = 0
    for ident in ids[: spec.get("tries", 4)]:
        k += one_book(ident, spec, k)
        if k:
            break


def one_book(ident, spec, k0=0):
    import fitz                                      # pymupdf
    pdf_path = os.path.join(OUT, "_" + ident + ".pdf")
    try:
        meta = getjson(f"https://archive.org/metadata/{ident}")
        pdfs = [f["name"] for f in meta.get("files", []) if f.get("name", "").lower().endswith(".pdf")]
        log("  files:", pdfs[:6])
        name = next((f for f in pdfs if f == ident + ".pdf"), None) or next((f for f in pdfs if "text" in f.lower()), None) or (pdfs[0] if pdfs else ident + ".pdf")
        raw = get(f"https://archive.org/download/{ident}/{urllib.parse.quote(name)}", tries=3)
        open(pdf_path, "wb").write(raw)
        log("  pdf:", name, len(raw) // 1024, "KB")
    except Exception as e:
        log("  book download failed:", ident, e)
        return 0
    doc = fitz.open(pdf_path)
    words = [w.lower() for w in spec["find"]]
    hits = []
    for i in range(doc.page_count):
        t = doc[i].get_text() or ""
        low = t.lower()
        if any(w in low for w in words):
            hits.append((i, re.sub(r"[ \t]+", " ", t).strip()))      # the whole page's text, to read the facts
    log("  pages that match:", [h[0] + 1 for h in hits][:60])
    k = k0
    for i, snip in hits[: spec.get("max", 6)]:
        pix = doc[i].get_pixmap(dpi=spec.get("dpi", 200))
        k += 1
        add({"title": (spec.get("title") or ident) + f", page {i + 1} of the scan", "book_id": ident, "page": f"https://archive.org/details/{ident}/page/n{i}/mode/1up",
             "url": f"https://archive.org/details/{ident}", "license": spec.get("license", "Public domain (old book)"),
             "artist": spec.get("author", ""), "credit": "Internet Archive", "date": spec.get("date", ""), "desc": snip[:6000],
             "source": "Internet Archive", "kind": "book-page", "scan_page": i + 1,
             "found": [w for w in spec["find"] if w.lower() in snip.lower()]},
            pix.tobytes("jpeg"), spec["name"], k, max_side=3000)
    doc.close()
    os.remove(pdf_path)
    return k - k0


# ------------------------------------------------------------------ Chronicling America (1908 newspapers)
def alto_blocks(xml_bytes, pattern):
    """(page_w, page_h, [(score, x, y, w, h, text)]): a box around every word matching the pattern — the text
    block's (column's) width, from two lines above the word to about a dozen lines below it — biggest type first.
    (Whole text blocks are no use: on old papers a block is the whole column.)"""
    root = ET.fromstring(xml_bytes)
    strip = lambda t: t.split("}")[-1]
    page = next((e for e in root.iter() if strip(e.tag) == "Page"), None)
    pw, ph = float(page.get("WIDTH")), float(page.get("HEIGHT"))
    blocks = []
    for tb in (e for e in root.iter() if strip(e.tag) == "TextBlock"):
        words = [s for s in tb.iter() if strip(s.tag) == "String"]
        bx, bw = float(tb.get("HPOS", 0)), float(tb.get("WIDTH", pw * 0.15))
        for i, s in enumerate(words):
            if not re.search(pattern, s.get("CONTENT", ""), re.I):
                continue
            wy, wh = float(s.get("VPOS", 0)), float(s.get("HEIGHT", 20)) or 20.0
            y0 = max(0.0, wy - wh * 2.5)
            y1 = min(ph, wy + wh * 14)
            text = " ".join(w.get("CONTENT", "") for w in words[max(0, i - 6): i + 30])
            blocks.append((wh, bx, y0, bw, y1 - y0, text[:400]))
    blocks.sort(reverse=True)
    # drop boxes that sit inside an earlier (bigger-type) one
    keep = []
    for b in blocks:
        if not any(abs(b[1] - k[1]) < 5 and k[2] - 5 <= b[2] <= k[2] + k[4] * 0.5 for k in keep):
            keep.append(b)
    return pw, ph, keep


def ca_page(page_url):
    """(lccn, date, ed, seq) from a loc.gov resource page URL, or None."""
    m = re.search(r"resource/([a-z0-9]+)/(\d{4}-\d{2}-\d{2})/(ed-\d+)/\?sp=(\d+)", page_url)
    return m.groups() if m else None


def coords_blocks(raw, pattern):
    """The word-coordinates service answers JSON: {"width", "height", "coords": {word: [[x, y, w, h], ...]}}.
    Makes block-like boxes around each matching word (a column's width, a dozen lines tall)."""
    d = json.loads(raw)
    pw, ph = float(d["width"]), float(d["height"])
    blocks = []
    for word, boxes in (d.get("coords") or {}).items():
        if not re.search(pattern, word, re.I):
            continue
        for x, y, w, h in boxes:
            col = pw * 0.15
            X0, Y0 = max(0.0, x + w / 2 - col / 2), max(0.0, y - h * 2.5)
            blocks.append((float(h), X0, Y0, min(pw - X0, col), min(ph - Y0, h * 14), word))
    blocks.sort(reverse=True)
    return pw, ph, blocks


def word_blocks(page_url, pattern, page_json=None):
    """Where the words are on a Chronicling America page: the old site's ALTO (ocr.xml) first, then the
    word-coordinates service the new site links to. Returns (page_w, page_h, blocks) or raises."""
    cp = ca_page(page_url)
    if cp:
        lccn, date, ed, seq = cp
        try:
            return alto_blocks(get(f"https://chroniclingamerica.loc.gov/lccn/{lccn}/{date}/{ed}/seq-{seq}/ocr.xml", loc=True), pattern)
        except Exception as e:
            log("  ocr.xml failed:", lccn, date, seq, str(e)[:80])
    if page_json is None:
        page_json = getjson(page_url + ("&" if "?" in page_url else "?") + "fo=json", loc=True)
    u = find_alto_url(page_json)
    if not u:
        raise RuntimeError("no word coordinates")
    raw = get(u, loc=True)
    try:
        return alto_blocks(raw, pattern)
    except Exception:
        return coords_blocks(raw, pattern)


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
        ("search", {"q": spec["q"] + " la porte", "fa": "original-format:newspaper", "dates": d0[:4] + "/" + d1[:4]}),
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
        if k >= spec.get("max", 60) or out_of_time() or _last["429"] > 25:
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
                pw, ph, blocks = alto_blocks(get(alto_url, loc=True), spec.get("pattern") or spec["q"])
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
        for size in (f"!{max(iw, ih)},{max(iw, ih)}", "full", "pct:75", "!10000,10000", "!8000,8000", "!5200,5200"):
            try:
                big = Image.open(io.BytesIO(get(f"{base}/full/{size}/0/default.jpg", loc=True))).convert("RGB")
                log(f"  page {pfile} at {size}: {big.size}")
                break
            except Exception as e:
                log(f"  page {pfile} at {size} failed:", e)
        if big is None:
            continue
        bw, bh = big.size
        alto_cache = {}
        for c in clips:
            if "box" not in c and c.get("pattern"):
                # find the words on the page (ALTO word coordinates) and cut around the best block
                try:
                    if c["pattern"] not in alto_cache:
                        alto_cache[c["pattern"]] = word_blocks(src["page"], c["pattern"])
                    pw, ph, blocks = alto_cache[c["pattern"]]
                except Exception as e:
                    log("  word positions failed:", pfile, e)
                    continue
                blocks = [b for b in blocks if re.search(c["pattern"], b[5], re.I)]
                if not blocks:
                    log("  no block matches", c["pattern"], "on", pfile)
                    continue
                px, py = float(c.get("pad", 0.12)), float(c.get("pad_y", 0.1))
                if c.get("all"):
                    extra = []
                    for j, (score, x, y, w, h, text) in enumerate(blocks[: int(c.get("max", 4))], 1):
                        extra.append(dict(c, all=False, out=f"{c['out']}-{j}", note=(c.get("note", "") + " | " + text[:160]).strip(" |"),
                                          box=[max(0.0, (x - w * px) / pw), max(0.0, (y - h * py) / ph), min(1.0, (x + w * (1 + px)) / pw), min(1.0, (y + h * (1 + py)) / ph)]))
                    clips.extend(extra)
                    continue
                score, x, y, w, h, text = blocks[min(int(c.get("n", 0)), len(blocks) - 1)]
                c["box"] = [max(0.0, (x - w * px) / pw), max(0.0, (y - h * py) / ph), min(1.0, (x + w * (1 + px)) / pw), min(1.0, (y + h * (1 + py)) / ph)]
                c["note"] = (c.get("note", "") + " | " + text[:160]).strip(" |")
                log("  found", c["pattern"], "on", pfile, "box", [round(v, 3) for v in c["box"]], "|", text[:80])
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


def loc_issues(items, old):
    """Every page of named newspaper issues (Library of Congress Chronicling America), kept only when the page's
    words match the pattern: {"name": "sbnt-1913", "lccn": "sn87055779", "date": "1913-11-01", "pattern": "hallowe", "max": 3}.
    Saves the page and crops of the matching text blocks. For La Porte's neighbors (South Bend, Hammond, Indianapolis),
    whose pages the keyword search doesn't surface."""
    have = {x["file"] for x in old}
    for r in items:
        if out_of_time():
            log("  time's up, skipped:", r["name"])
            continue
        name, lccn, date = r["name"], r["lccn"], r["date"]
        if any(f.startswith(name + "-") for f in have):
            continue
        eds = r.get("editions", ["ed-1"])
        k = 0
        for ed in eds:
            base_url = f"https://www.loc.gov/resource/{lccn}/{date}/{ed}/"
            try:
                js = getjson(base_url + "?fo=json", loc=True)
            except Exception as e:
                log("  issue lookup failed:", base_url, e)
                continue
            n = 0
            try:
                n = int((js.get("resource") or {}).get("segment_count") or js.get("segments", {}).get("total") or 0)
            except Exception:
                n = 0
            if not n:
                n = len(re.findall(r'"sp=(\d+)"', json.dumps(js))) or int(r.get("pages", 12))
            log(f"  {name} {ed}: {n} pages")
            for sp in range(1, min(n, int(r.get("pages", 16))) + 1):
                if k >= r.get("max", 3) or out_of_time():
                    break
                url = f"{base_url}?sp={sp}"
                try:
                    pj = getjson(url + "&fo=json", loc=True)
                except Exception as e:
                    log("  page lookup failed:", url, e)
                    continue
                urls = re.findall(r'https://tile\.loc\.gov/image-services/iiif/[^"\s]+', json.dumps(pj))
                base = next((iiif_base(u) for u in urls if iiif_base(u)), None)
                if not base:
                    continue
                try:
                    pw, ph, blocks = word_blocks(url, r.get("pattern", "hallowe"), pj)
                except Exception as e:
                    log("  word positions failed:", url, str(e)[:100])
                    continue
                if not blocks:
                    continue
                try:
                    info = getjson(base + "/info.json", loc=True)
                    iw, ih = int(info["width"]), int(info["height"])
                    raw = get(f"{base}/full/!2600,2600/0/default.jpg", loc=True)
                except Exception as e:
                    log("  page download failed:", base, e)
                    continue
                k += 1
                paper = r.get("paper", lccn)
                entry = {"title": f"{paper}, {date}, page {sp}", "page": url, "url": base, "license": r.get("license", "Public domain (newspaper, before 1930)"),
                         "artist": paper, "credit": "Library of Congress, Chronicling America", "date": date, "desc": blocks[0][5][:300],
                         "source": "Library of Congress", "kind": "newspaper-page", "page_size": [iw, ih], "crops": []}
                add(entry, raw, name, k, max_side=2600)
                sx, sy = iw / pw, ih / ph
                for j, (score, x, y, w, h, text) in enumerate(blocks[: r.get("crops_per_page", 3)], 1):
                    pad = 0.15
                    X0, Y0 = max(0, int((x - w * pad) * sx)), max(0, int((y - h * pad - 40) * sy))
                    X1, Y1 = min(iw, int((x + w * (1 + pad)) * sx)), min(ih, int((y + h * (1 + pad) + 40) * sy))
                    if X1 - X0 < 50 or Y1 - Y0 < 30:
                        continue
                    try:
                        raw_c = get(f"{base}/{X0},{Y0},{X1 - X0},{Y1 - Y0}/!2000,2000/0/default.jpg", loc=True)
                    except Exception as e:
                        log("  crop failed:", e)
                        continue
                    path = os.path.join(OUT, f"{name}-{k:02d}-crop{j}.jpg")
                    size = save_image(raw_c, path, 2000)
                    entry["crops"].append({"file": os.path.basename(path), "box": [X0, Y0, X1 - X0, Y1 - Y0], "score": score, "text": text, "saved": list(size)})
                    log("    crop", os.path.basename(path), "|", text[:100])
                write_manifest()



def split_spec(spec, part):
    """The sections one parallel part runs: commons1/commons2 (the Commons searches in two halves), loc, maps, books, news."""
    if not part:
        return spec
    keep = {"commons1": ["commons", "commons_hires"], "commons2": ["commons"], "loc": ["loc_photos"],
            "maps": ["loc_maps", "loc_items", "resource_pages"], "books": ["archive_books"], "news": ["newspapers", "news_clips", "loc_issues"]}[part]
    out = {k: v for k, v in spec.items() if k in keep}
    c = spec.get("commons", [])
    half = (len(c) + 1) // 2
    if part == "commons1":
        out["commons"] = c[:half]
    elif part == "commons2":
        out["commons"] = c[half:]
    return out


def main_extra():
    """The second pass: adds pictures without touching the ones already on the list. With --part, each parallel job
    writes only its new pictures to images/manifest-extra-<part>.json (merged into manifest.json afterwards)."""
    global LOGF, write_manifest
    part = PART[0]
    sfx = f"-{part}" if part else ""
    LOGF = open(os.path.join(OUT, f"fetch-log-extra{sfx}.txt"), "w", encoding="utf-8")
    spec = split_spec(json.load(open(os.path.join(HERE, "sources-extra.json"), encoding="utf-8")), part)
    old = []
    for mp in sorted(glob.glob(os.path.join(OUT, "manifest*.json"))):           # every earlier part's list
        old.extend(json.load(open(mp, encoding="utf-8")))
    manifest.extend(old)
    for x in old:
        seen.add(x.get("title"))
        seen.add(x.get("page"))
    log(len(old), "pictures already on the list; part", part)

    def write_new():
        with open(os.path.join(OUT, f"manifest-extra{sfx}.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest[len(old):], fh, ensure_ascii=False, indent=1)
    write_manifest = write_new
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
    if spec.get("loc_issues"):
        log("Newspaper issues scanned for Halloween:", len(spec["loc_issues"]))
        loc_issues(spec["loc_issues"], old)
        write_manifest()
    taken = {re.sub(r"-\d+(-crop\d+)?\.jpg$", "", x["file"]) for x in old}
    for q in spec.get("commons", []):
        if q["name"] in taken:
            log("  name already used, skipped:", q["name"])
            continue
        if out_of_time():
            log("  time's up, skipped:", q["name"])
            continue
        log("Commons:", q["name"], q.get("category") or q.get("search") or q.get("titles"))
        try:
            found = commons(q)
        except Exception as e:
            log("  didn't answer:", e)
            continue
        log("  found", len(found))
        k = 0
        for it in sorted(found, key=lambda x: x["title"] or ""):
            if k >= q.get("max", 50) or out_of_time():
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
    for section, endpoint, side in (("loc_photos", "photos", MAX_SIDE), ("loc_maps", "maps", 3200)):
        for q in spec.get(section, []):
            if q["name"] in taken or out_of_time():
                log("  skipped:", q["name"])
                continue
            log("Library of Congress", endpoint + ":", q["name"], q["q"])
            loc_fetch(q, endpoint, side)
            write_manifest()
    for q in spec.get("loc_items", []):
        if q["name"] in taken or out_of_time():
            log("  skipped:", q["name"])
            continue
        log("Library of Congress item, every picture:", q["name"], q["item"])
        loc_item_pages(q)
        write_manifest()
    for q in spec.get("archive_books", []):
        if q["name"] in taken or out_of_time():
            log("  skipped:", q["name"])
            continue
        log("Internet Archive book:", q["name"], q.get("id") or q.get("search"), q["find"])
        try:
            archive_books(q)
        except Exception as e:
            log("  book stopped:", e)
        write_manifest()
    for q in spec.get("newspapers", []):
        if q["name"] in taken or out_of_time():
            log("  skipped:", q["name"])
            continue
        log("Chronicling America:", q)
        try:
            newspapers(dict(q, crops_per_page=q.get("crops_per_page", 0)))
        except Exception as e:
            log("  stopped:", e)
        write_manifest()
    write_manifest()
    with open(os.path.join(OUT, f"extra-files{sfx}.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(NEW_FILES) + "\n")
    log(len(NEW_FILES), "new pictures saved", "(stopped by the time limit)" if out_of_time() else "")


PART = [None]


def write_manifest_part():
    name = f"manifest-{PART[0]}.json" if PART[0] else "manifest.json"
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)


def main():
    global LOGF, write_manifest
    args = [a for a in sys.argv[1:] if a != "--extra"]
    if "--part" in args:                  # run one part of the list (parallel jobs): commons1, commons2, loc, maps, books, news
        i = args.index("--part")
        PART[0] = args[i + 1]
        del args[i:i + 2]
        write_manifest = write_manifest_part
    if "--minutes" in args:
        i = args.index("--minutes")
        DEADLINE[0] = time.time() + 60 * float(args[i + 1])
        del args[i:i + 2]
    if "--extra" in sys.argv:
        return main_extra()
    LOGF = open(os.path.join(OUT, f"fetch-log-{PART[0]}.txt" if PART[0] else "fetch-log.txt"), "w", encoding="utf-8")
    spec = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))
    if PART[0]:
        c = spec.get("commons", [])
        half = (len(c) + 1) // 2
        keep = {"commons1": ["commons"], "commons2": ["commons"], "loc": ["loc_photos"], "maps": ["loc_maps", "loc_items"],
                "books": ["archive_books"], "news": ["newspapers"]}[PART[0]]
        spec = {k: v for k, v in spec.items() if k in keep}
        if PART[0] == "commons1":
            spec["commons"] = c[:half]
        elif PART[0] == "commons2":
            spec["commons"] = c[half:]
    only = set(args)
    for q in spec.get("commons", []):
        if only and q["name"] not in only:
            continue
        if out_of_time():
            log("  time's up, skipped:", q["name"])
            continue
        log("Commons:", q["name"], q.get("category") or q.get("search"))
        try:
            found = commons(q)
        except Exception as e:
            log("  didn't answer:", e)
            continue
        k = 0
        for it in sorted(found, key=lambda x: x["title"] or ""):
            if k >= q.get("max", 50) or out_of_time():
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
        if out_of_time():
            log("  time's up, skipped:", q["name"])
            continue
        log("Library of Congress photos:", q["name"], q["q"])
        loc_fetch(q, "photos", MAX_SIDE)
        write_manifest()
    for q in spec.get("loc_maps", []):
        if only and q["name"] not in only:
            continue
        if out_of_time():
            log("  time's up, skipped:", q["name"])
            continue
        log("Library of Congress maps:", q["name"], q["q"])
        loc_fetch(q, "maps", 3200)
        write_manifest()
    for q in spec.get("loc_items", []):
        if only and q["name"] not in only:
            continue
        if out_of_time():
            log("  time's up, skipped:", q["name"])
            continue
        log("Library of Congress item, every picture:", q["name"], q["item"])
        loc_item_pages(q)
        write_manifest()
    for q in spec.get("archive_books", []):
        if only and q["name"] not in only:
            continue
        if out_of_time():
            log("  time's up, skipped:", q["name"])
            continue
        log("Internet Archive book:", q["name"], q.get("id") or q.get("search"), q["find"])
        try:
            archive_books(q)
        except Exception as e:
            log("  book stopped:", e)
        write_manifest()
    news = spec.get("newspapers")
    if news and (not only or "news" in only):
        for ns in (news if isinstance(news, list) else [news]):     # one search, or several (each with its own name)
            if out_of_time():
                log("  time's up, skipped:", ns.get("name"))
                continue
            log("Chronicling America:", ns)
            try:
                newspapers(ns)
            except Exception as e:
                log("  newspaper search stopped:", e)
            write_manifest()
    write_manifest()
    if PART[0]:
        with open(os.path.join(OUT, f"files-{PART[0]}.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(NEW_FILES) + "\n")
    log(len(manifest), "pictures saved", "(stopped by the time limit)" if out_of_time() else "")


if __name__ == "__main__":
    main()
