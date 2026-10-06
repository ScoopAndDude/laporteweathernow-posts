#!/usr/bin/env python3
"""Builds devotion/library.json for the Sky Devotion from entries.py.

Every verse's text is taken from the King James Version (public domain) and checked against two
independent digital copies of the KJV; the build stops if they disagree (after ignoring spacing and
the "LORD"/"Lord" small-caps difference). Sources (downloaded into KJV_DIR before running):
  A: https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_kjv.json
  B: https://raw.githubusercontent.com/aruljohn/Bible-kjv/master/<Book>.json (one file per book)
Run: python3 tools/devotion/build_library.py <KJV_DIR>   (from the posts repo root)
"""
import json, os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from entries import ENTRIES

KJV_DIR = sys.argv[1]
A = json.load(open(os.path.join(KJV_DIR, "en_kjv.json"), encoding="utf-8-sig"))
BOOKS = json.load(open(os.path.join(KJV_DIR, "Books.json")))   # 66 English names, in order
ALIAS = {"Psalm": "Psalms"}

def parse(ref):
    m = re.match(r"^(.+?) (\d+):(\d+)(?:-(\d+))?$", ref)
    book = ALIAS.get(m.group(1), m.group(1))
    return BOOKS.index(book), book, int(m.group(2)), int(m.group(3)), int(m.group(4) or m.group(3))

_b_cache = {}
def b_book(book):
    if book not in _b_cache:
        path = os.path.join(KJV_DIR, "b_" + book.replace(" ", "") + ".json")
        if not os.path.exists(path):
            url = "https://raw.githubusercontent.com/aruljohn/Bible-kjv/master/" + book.replace(" ", "") + ".json"
            with urllib.request.urlopen(url, timeout=60) as r: open(path, "wb").write(r.read())
        _b_cache[book] = json.load(open(path, encoding="utf-8-sig"))
    return _b_cache[book]

def clean(s):
    s = re.sub(r"[{}\[\]]", "", s)
    s = re.sub(r"\s+([,.;:?!])", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()

def text_a(bi, c, v1, v2):
    return clean(" ".join(A[bi]["chapters"][c - 1][v - 1] for v in range(v1, v2 + 1)))

def text_b(book, c, v1, v2):
    ch = [x for x in b_book(book)["chapters"] if int(x["chapter"]) == c][0]
    vs = {int(x["verse"]): x["text"] for x in ch["verses"]}
    return clean(" ".join(vs[v] for v in range(v1, v2 + 1)))

def same(a, b):
    k = lambda s: re.sub(r"[^a-z]", "", s.lower())
    return k(a) == k(b)

problems, out, verses = [], [], {}
for i, (sky, ref, text) in enumerate(ENTRIES):
    bi, book, c, v1, v2 = parse(ref)
    a, b = text_a(bi, c, v1, v2), text_b(book, c, v1, v2)
    if not same(a, b):
        problems.append(f"{ref}:\n  A: {a}\n  B: {b}")
    # Prefer B's spelling of LORD (small caps in print) when the words agree.
    verses[ref] = b if "LORD" in b else a
    out.append({"id": f"{sky}-{sum(1 for e in ENTRIES[:i] if e[0] == sky) + 1}", "sky": sky,
                "ref": ref.replace("Psalm ", "Psalm ") , "kjv": verses[ref], "text": text})
if problems:
    print("VERSE MISMATCHES, not building:\n" + "\n".join(problems)); sys.exit(1)
skies = {}
for e in out: skies.setdefault(e["sky"], []).append(e["id"])
lib = {
    "about": ("The Sky Devotion: a short devotion chosen each day by what the sky is doing. Written by "
              "La Porte Weather Now (laporteweathernow.com). Scripture: King James Version (public domain), "
              "each verse checked against two independent KJV texts. Free to share with credit."),
    "version": "2026-10-06",
    "skies": skies,
    "entries": out,
}
os.makedirs("devotion", exist_ok=True)
json.dump(lib, open("devotion/library.json", "w"), ensure_ascii=False, indent=1)
print(f"Wrote devotion/library.json: {len(out)} devotions, {len(set(verses))} verses, skies: {', '.join(f'{k} {len(v)}' for k, v in skies.items())}")
