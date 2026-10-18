#!/usr/bin/env python3
"""School delays and closings for laporteweathernow.com/closings (added Oct. 17, 2026).

Checks the official websites of La Porte County's school districts (and Marquette Catholic and Purdue
Northwest) every 5 minutes from 4:30 to 8:30 AM Central on winter weekday mornings (Nov. 1 - Mar. 31),
and posts a delay or closing ONLY when the school's own page says it in so many words:

  - an exact phrase: "2-hour delay" (two/three hour, delayed start), "schools are closed",
    "closed today", "no school", "classes canceled", "e-learning day", "virtual learning day",
    "campus is closed";
  - in text that's new since the afternoon before, or in the district's own status box
    (La Porte's alert banner, New Prairie's "School weather info", South Central's status light);
  - and about today: it names today ("today", "this morning", today's weekday or date), never a different day.

Anything else that looks like a delay or closing (no date, "tomorrow", two different answers, a status
box we don't recognize) is NOT posted: it's flagged for Scoop. A flag makes the run end with an error
on purpose, which is what makes GitHub email Scoop (same as the daily site check), with the school's
words and how to confirm it.

Scoop's own entries come from closings-manual.txt (Actions > School closings > Run workflow > "entry",
or edit the file): they win over anything found automatically, for that school and that day only.

Every entry is for one day: the page shows only today's entries (Central time), and the evening run
(8 PM Sunday-Thursday, also the "baseline" that learns what each page normally says) starts the next
day empty. The page always says to confirm with the school.

Saved on the "closings" branch, which only this job writes: closings.json (public, what the page shows)
and closings-state.json (what each page normally says, and which flags were already sent).

  python3 scripts/closings_check.py check      the morning job: 3 checks, 5 minutes apart (one 15-minute tick)
  python3 scripts/closings_check.py once       one check now (any time; used for testing)
  python3 scripts/closings_check.py baseline   learn each page as it is now (no posts, no flags), clear yesterday
  python3 scripts/closings_check.py seed       same as baseline (the first run ever)
  python3 scripts/closings_check.py rebuild    no checking: redo closings.json from the state and the manual file
  python3 scripts/closings_check.py entry SCHOOL STATUS [NOTE]   add Scoop's entry for today, then rebuild
Options (environment): CLOSINGS_DIR (where closings.json/closings-state.json are read and written,
default "."), CLOSINGS_PUBLISH=1 (push the closings branch after each check; needs TOKEN and
GITHUB_REPOSITORY), CLOSINGS_NOW (an ISO time to pretend it is, for tests), CLOSINGS_FIXTURES (a folder of
saved pages, <id>.html, instead of the live sites, for tests).
"""
import concurrent.futures
import datetime
import hashlib
import html
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
OUT_DIR = os.environ.get("CLOSINGS_DIR", ".")
MANUAL = os.path.join(REPO_ROOT, "closings-manual.txt")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 "
      "LaPorteWeatherNow-closings-check/1.0 (+https://laporteweathernow.com/closings)")

SEASON = ((11, 1), (3, 31))          # Nov. 1 through Mar. 31
WINDOW = ("04:30", "08:30")           # Central time, Monday-Friday
ROUNDS, GAP = 3, 300                  # one 15-minute tick = 3 checks, 5 minutes apart

# kind: "lpcsc" (SchoolBlocks alert banner data + page text), "npusc" (School weather info box + page text),
# "scentral" (status light + page text), "page" (page text as a browser shows it).
SCHOOLS = [
    {"id": "lpcsc", "name": "La Porte Community Schools", "area": "La Porte and Kingsford Heights",
     "url": "https://www.lpcsc.k12.in.us/", "info": "https://www.lpcsc.k12.in.us/en-US/closings-delays-7c720972",
     "kind": "lpcsc", "decides": "by 5:15 AM"},
    {"id": "mcas", "name": "Michigan City Area Schools", "area": "Michigan City",
     "url": "https://www.educatemc.net/", "info": "https://www.educatemc.net/welcome-to-city/about-us/our-schools/school-closings-delays",
     "kind": "page", "decides": "by 5:30 AM"},
    {"id": "npusc", "name": "New Prairie United Schools", "area": "Rolling Prairie and New Carlisle",
     "url": "https://www.npusc.k12.in.us/", "info": "https://www.npusc.k12.in.us/weather-decision-guidelines/",
     "kind": "npusc", "decides": "by 5:15 AM, shared by 5:30"},
    {"id": "scentral", "name": "South Central Community Schools", "area": "Union Mills",
     "url": "https://www.scentral.k12.in.us/", "info": "https://www.scentral.k12.in.us/", "kind": "scentral"},
    {"id": "tritownship", "name": "Tri-Township Consolidated Schools", "area": "Wanatah",
     "url": "https://district.tritownship.k12.in.us/", "info": "https://district.tritownship.k12.in.us/", "kind": "page"},
    {"id": "westville", "name": "MSD of New Durham Township", "area": "Westville",
     "url": "https://www.westville.k12.in.us/", "info": "https://www.westville.k12.in.us/", "kind": "page"},
    {"id": "marquette", "name": "Marquette Catholic High School", "area": "Michigan City",
     "url": "https://www.marquette-hs.org/", "info": "https://www.marquette-hs.org/", "kind": "page", "private": True},
    {"id": "pnw", "name": "Purdue University Northwest", "area": "Westville campus",
     "url": "https://www.pnw.edu/alerts/", "info": "https://www.pnw.edu/alerts/", "kind": "page", "college": True},
]
# Schools we can't check automatically: they tell families directly. Scoop can still add an entry for them.
NOT_CHECKED = [
    {"id": "lalumiere", "name": "La Lumiere School", "area": "La Porte", "url": "https://www.lalumiere.org/",
     "how": "Emails and texts its families; its website blocks automated checks.", "phone": "(219) 326-7450", "private": True},
    {"id": "queenofallsaints", "name": "Queen of All Saints School", "area": "Michigan City",
     "how": "Catholic school (Diocese of Gary); tells its families directly.", "phone": "(219) 872-4420", "private": True},
    {"id": "ststanislaus", "name": "St. Stanislaus Kostka Catholic School", "area": "Michigan City",
     "how": "Catholic school (Diocese of Gary); tells its families directly.", "phone": "(219) 872-2258", "private": True},
    {"id": "notredame", "name": "Notre Dame Catholic School", "area": "Michigan City",
     "how": "Catholic school (Diocese of Gary); tells its families directly.", "phone": "(219) 872-6216", "private": True},
    {"id": "stjohnslutheran", "name": "St. John's Lutheran School", "area": "La Porte",
     "how": "Tells its families directly.", "phone": "(219) 362-6692", "private": True},
]
ALL_IDS = {s["id"]: s for s in SCHOOLS + NOT_CHECKED}

# ---------- the exact phrases ----------
NUM = r"(?:one|two|three|1|2|3)"
DELAY_RX = re.compile(rf"\b({NUM})[\s-]*(?:hour|hr)s?[\s-]*(?:delay(?:ed)?(?:\s+start)?|late\s+start)\b|\bdelayed\s+start\b", re.I)
CLOSED_RX = re.compile(
    r"\b(?:schools?\s+(?:is|are|will\s+be)\s+closed|(?:is|are)\s+closed\s+(?:today|this\s+morning)|closed\s+today"
    r"|no\s+school|(?:school|classes)\s+(?:is\s+|are\s+|have\s+been\s+|has\s+been\s+)?cancel+ed|campus(?:es)?\s+(?:is|are|will\s+be)\s+closed"
    r"|school\s+closing\s+today)\b", re.I)
ELEARN_RX = re.compile(r"\b(?:e-?\s?learning|virtual\s+learning|remote\s+learning)\s+day\b", re.I)
KEYWORD_RX = re.compile(r"\b(?:delay(?:s|ed)?|closed|closing|closure|cancel+(?:ed|ation)?|e-?learning\s+day|virtual\s+learning|no\s+school|late\s+start)\b", re.I)
WORDS = {"1": "1-hour delay", "one": "1-hour delay", "2": "2-hour delay", "two": "2-hour delay",
         "3": "3-hour delay", "three": "3-hour delay"}
# Everyday page text that uses the words but never announces anything (menus, sign-up blurbs, policy pages).
BORING_RX = re.compile(r"^(?:school\s+)?(?:closings?|delays?)(?:\s*(?:&|and|/)\s*(?:closings?|delays?|cancell?ations?))*$"
                       r"|sign\s*up|text\s+alerts|how\s+(?:we|the\s+district)\s+decide|determin|guidelines|policy|procedure", re.I)
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def norm(t):
    return re.sub(r"\s+", " ", html.unescape(t or "")).strip()


def which_day(text, today):
    """'today', 'other' (names another day), 'tomorrow' or None (no day at all)."""
    t = text.lower()
    named_today = bool(re.search(r"\btoday\b|\bthis\s+morning\b", t))
    wd = WEEKDAYS[today.weekday()]
    other_day = False
    for i, name in enumerate(WEEKDAYS):
        if re.search(rf"\b(?:{name}\b|{name[:3]}\.)", t):
            if i == today.weekday():
                named_today = True
            else:
                other_day = True
    for m in re.finditer(r"\b(" + "|".join(m[:3] for m in MONTHS) + r")[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", t):
        if MONTHS.index(next(x for x in MONTHS if x.startswith(m.group(1)))) + 1 == today.month and int(m.group(2)) == today.day:
            named_today = True
        else:
            other_day = True
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t):
        if int(m.group(1)) == today.month and int(m.group(2)) == today.day:
            named_today = True
        elif 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
            other_day = True
    tomorrow = bool(re.search(r"\btomorrow\b|\btonight\b", t))
    if other_day:
        return "other"
    if named_today:
        return "today"
    if tomorrow:
        return "tomorrow"
    return None


def read_announcement(text):
    """What a piece of text announces, by exact phrase: a list of (kind, words)."""
    found = []
    for m in DELAY_RX.finditer(text):
        found.append(("delay", WORDS.get((m.group(1) or "").lower(), "Delayed start")))
    if CLOSED_RX.search(text):
        found.append(("closed", "Closed"))
    if ELEARN_RX.search(text):
        found.append(("elearning", "E-learning day"))
    kinds = {k for k, _ in found}
    return found, kinds


# ---------- reading the pages ----------
BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "td", "th", "tr",
              "header", "footer", "aside", "main", "nav", "dd", "dt", "blockquote", "figcaption", "br", "hr",
              "table", "ul", "ol", "form", "label", "button", "option", "a"}
SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "head", "iframe", "select"}


class Blocks(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.cur, self.skip = [], [], 0

    def flush(self):
        t = norm("".join(self.cur))
        if t:
            self.out.append(t)
        self.cur = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
        elif tag in BLOCK_TAGS:
            self.flush()

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK_TAGS:
            self.flush()

    def handle_data(self, d):
        if not self.skip:
            self.cur.append(d)


def blocks_of(page_html):
    p = Blocks()
    try:
        p.feed(page_html)
        p.close()
    except Exception:
        pass
    p.flush()
    seen, out = set(), []
    for b in p.out:
        if 4 <= len(b) <= 800 and b not in seen:
            seen.add(b)
            out.append(b)
    return out


def fetch_raw(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


CHROME = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")


def fetch_rendered(url):
    """The page as a browser shows it (many school sites fill in their alert banner with JavaScript)."""
    if not CHROME:
        return None
    prof = tempfile.mkdtemp(prefix="lpwn-chrome-")
    try:
        r = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                            "--no-first-run", "--mute-audio", f"--user-data-dir={prof}", f"--user-agent={UA}",
                            "--virtual-time-budget=9000", "--dump-dom", url],
                           capture_output=True, timeout=75)
        out = r.stdout.decode("utf-8", "replace")
        return out if len(out) > 500 else None
    except Exception:
        return None
    finally:
        shutil.rmtree(prof, ignore_errors=True)


def lpcsc_alerts(raw):
    """La Porte's site (SchoolBlocks) carries its alert banner as data in the page: "alerts":[...]."""
    out = []
    for m in re.finditer(r'\\?"alerts\\?"\s*:\s*\[', raw):
        i, depth, j = m.end() - 1, 0, m.end() - 1
        while j < len(raw) and j - i < 60000:
            c = raw[j]
            depth += c == "["
            depth -= c == "]"
            if depth == 0:
                break
            j += 1
        chunk = raw[i:j + 1]
        if chunk.strip() in ("[]",):
            continue
        txt = chunk.replace('\\"', '"').replace("\\n", " ").replace("\\u003c", "<").replace("\\u003e", ">")
        for k in re.finditer(r'"(?:title|name|message|description|body|text|content)"\s*:\s*"((?:[^"\\]|\\.)*)"', txt):
            v = norm(re.sub(r"<[^>]+>", " ", k.group(1)))
            if v:
                out.append(v)
    return out


def npusc_status(raw):
    m = re.search(r"SCHOOL WEATHER INFO:(.{0,6000}?)ADDITIONAL QUICKLINKS", raw, re.S | re.I)
    if not m:
        return None
    t = norm(re.sub(r"<[^>]+>", " ", m.group(1)))
    light = re.search(r"/(\w*light)\.(?:jpe?g|png)", m.group(1), re.I)
    return {"text": t, "light": light.group(1).lower() if light else None}


def scentral_status(raw):
    m = re.search(r"class='ss_status'[^>]*>(.*?)</div>", raw, re.S)
    c = re.search(r"id='ss_comment_div'[^>]*>(.*?)</div>", raw, re.S)
    if not m:
        return None
    return {"text": norm(re.sub(r"<[^>]+>", " ", m.group(1))),
            "comment": norm(re.sub(r"<[^>]+>", " ", c.group(1))) if c else ""}


def read_school(s, fixtures=None):
    """Returns {"ok", "blocks": [...], "status": [(text, trusted)]} for one school."""
    raw = rendered = None
    try:
        if fixtures:
            p = os.path.join(fixtures, s["id"] + ".html")
            raw = rendered = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
        else:
            if s["kind"] in ("lpcsc", "npusc", "scentral"):
                try:
                    raw = fetch_raw(s["url"])
                except Exception:
                    raw = None
            rendered = fetch_rendered(s["url"])
            if rendered is None and raw is None:
                raw = fetch_raw(s["url"])
    except Exception as e:
        return {"ok": False, "error": str(e)[:120], "blocks": [], "status": []}
    page = rendered or raw
    if not page:
        return {"ok": False, "error": "no page", "blocks": [], "status": []}
    status = []
    src = raw or page
    if s["kind"] == "lpcsc":
        for a in lpcsc_alerts(src):
            status.append((a, True))
    elif s["kind"] == "npusc":
        st = npusc_status(src)
        if st and st["text"] and not re.fullmatch(r"(?i)school\s+is\s+in\s+session\.?", st["text"]):
            status.append((st["text"], True))
    elif s["kind"] == "scentral":
        st = scentral_status(src)
        if st:
            # Its light says "School is Closed" outside school hours and on weekends, so a plain
            # Open/Closed is never posted; anything else it says (or its comment line) is read like an alert.
            if st["text"] and not re.fullmatch(r"(?i)school\s+is\s+(?:open|closed)\.?", st["text"]):
                status.append((st["text"], True))
            if st["comment"] and len(st["comment"]) > 3:
                status.append((st["comment"], True))
    return {"ok": True, "blocks": blocks_of(page), "status": status}


# ---------- state ----------
def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def h(text):
    return hashlib.sha1(text.lower().encode()).hexdigest()[:16]


def now_central():
    if os.environ.get("CLOSINGS_NOW"):
        t = datetime.datetime.fromisoformat(os.environ["CLOSINGS_NOW"])
        return t.astimezone(CENTRAL) if t.tzinfo else t.replace(tzinfo=CENTRAL)
    return datetime.datetime.now(CENTRAL)


def in_season(d):
    (m1, d1), (m2, d2) = SEASON
    return (d.month, d.day) >= (m1, d1) or (d.month, d.day) <= (m2, d2)


def in_window(now):
    hm = now.strftime("%H:%M")
    return now.weekday() < 5 and in_season(now.date()) and WINDOW[0] <= hm <= WINDOW[1]


def next_check(now):
    d = now
    for _ in range(400):
        start = datetime.datetime.combine(d.date(), datetime.time(4, 30), CENTRAL)
        if d.weekday() < 5 and in_season(d.date()) and now < datetime.datetime.combine(d.date(), datetime.time(8, 30), CENTRAL):
            return max(start, now) if start <= now else start
        d = datetime.datetime.combine(d.date() + datetime.timedelta(days=1), datetime.time(0, 0), CENTRAL)
    return None


def fresh_cutoff(now):
    """Text first seen after noon yesterday counts as new (the evening run learns the page at 8 PM)."""
    return datetime.datetime.combine(now.date() - datetime.timedelta(days=1), datetime.time(12, 0), CENTRAL)


def check_once(state, now, learn_only=False, fixtures=None, ancient=False):
    """One check of every school. Returns the list of new flags."""
    today = now.date()
    day = today.isoformat()
    auto = state.setdefault("auto", {})
    if auto.get("date") != day:
        state["auto"] = auto = {"date": day, "found": {}}
    flags_sent = state.setdefault("flagsSent", {})
    for k in list(flags_sent):
        if k != day:
            del flags_sent[k]
    sent_today = set(flags_sent.setdefault(day, []))
    pages = state.setdefault("pages", {})
    checks = state.setdefault("checks", {})
    new_flags = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        results = dict(zip([s["id"] for s in SCHOOLS], ex.map(lambda s: read_school(s, fixtures), SCHOOLS)))
    stamp = now.isoformat(timespec="seconds")
    cutoff = fresh_cutoff(now).isoformat(timespec="seconds")
    for s in SCHOOLS:
        r = results[s["id"]]
        checks[s["id"]] = {"checked": stamp, "ok": r["ok"], **({"error": r["error"]} if not r["ok"] else {})}
        if not r["ok"]:
            continue
        known = pages.setdefault(s["id"], {})
        seeded = bool(known)
        if not seeded:
            known["_seeded"] = {"first": stamp, "last": "9999"}
        # 1) Learn every block (first and last time seen). Text that names a delay or closing is
        #    kept too, so the same old banner is recognized tomorrow.
        fresh = []
        for b in r["blocks"]:
            k = h(b)
            rec = known.get(k)
            if rec is None:
                # The very first learning run marks what's there as old, so nothing on a page counts as new
                # the next morning just because we'd never looked before.
                known[k] = rec = {"first": "2000-01-01T00:00:00-06:00" if (ancient or not seeded) else stamp, "last": stamp}
                if KEYWORD_RX.search(b):
                    rec["text"] = b[:300]
            else:
                rec["last"] = stamp
            if rec["first"] >= cutoff:
                fresh.append(b)
        if learn_only or not seeded:
            continue
        # 2) What the school says right now.
        # A status box's words are trusted only if they changed since noon yesterday: a box still
        # saying "2 HOUR DELAY" from yesterday is flagged, never posted again.
        seen_status = state.setdefault("statusSeen", {}).setdefault(s["id"], {})
        candidates = []
        for t, _ in r["status"]:
            k = h(t)
            rec = seen_status.setdefault(k, {"first": stamp})
            rec["last"] = stamp
            first = rec["first"]
            candidates.append((t, first >= cutoff))
            if first < cutoff and (KEYWORD_RX.search(t) or read_announcement(t)[0]) and which_day(t, today) != "other":
                candidates[-1] = (t, None)   # stale status: flag only
        st_texts = [t.lower() for t, _ in r["status"]]
        candidates += [(b, False) for b in fresh if not any(b.lower() in t or t in b.lower() for t in st_texts)]
        found, flagged = [], []
        for text, trusted in candidates:
            if trusted is None:
                flagged.append({"quote": text[:400], "why": "its status box has said this since before yesterday afternoon"})
                continue
            if BORING_RX.search(text) and len(text) < 60 and not trusted:
                continue
            ann, kinds = read_announcement(text)
            day_ref = which_day(text, today)
            if ann and len(kinds) == 1 and day_ref != "other":
                if day_ref == "today" or (trusted and day_ref is None):
                    found.append({"kind": ann[0][0], "words": ann[0][1], "quote": text[:280], "trusted": trusted})
                    continue
            if ann and day_ref == "other":
                continue      # about another day (yesterday's banner, or a date coming up)
            if ann or (KEYWORD_RX.search(text) and (trusted or len(text) <= 400)):
                why = ("two different answers" if len(kinds) > 1 else
                       "it says tomorrow or tonight" if day_ref == "tomorrow" else
                       "it doesn't say which day" if ann else "it mentions a delay or closing but not in our exact words")
                flagged.append({"quote": text[:400], "why": why})
        prev = auto["found"].get(s["id"])
        if found:
            kinds = {f["kind"] for f in found}
            if len(kinds) == 1:
                f = sorted(found, key=lambda x: (not x["trusted"], len(x["quote"])))[0]
                if not prev or prev["kind"] != f["kind"] or prev["words"] != f["words"]:
                    auto["found"][s["id"]] = {"kind": f["kind"], "words": f["words"], "quote": f["quote"],
                                              "seen": stamp, "pending": False}
                else:
                    prev["pending"] = False
            else:
                flagged.append({"quote": " / ".join(x["quote"] for x in found)[:400], "why": "two different answers"})
        for fl in flagged:
            key = h(s["id"] + fl["quote"])
            if prev and s["id"] in auto["found"]:
                auto["found"][s["id"]]["pending"] = True    # the page changed after we posted: say so on the site
            if key not in sent_today:
                sent_today.add(key)
                new_flags.append({"school": s["name"], "id": s["id"], "url": s["url"], **fl})
    flags_sent[day] = sorted(sent_today)
    # Forget page text not seen for 21 days.
    old = (now - datetime.timedelta(days=21)).isoformat(timespec="seconds")
    for sid, known in pages.items():
        for k in [k for k, v in known.items() if v.get("last", "") < old]:
            del known[k]
    for sid, seen in state.get("statusSeen", {}).items():
        for k in [k for k, v in seen.items() if v.get("last", "") < old]:
            del seen[k]
    state["lastCheck"] = stamp
    return new_flags


# ---------- Scoop's entries ----------
MANUAL_STATUS = {"2-hour delay": ("delay", "2-hour delay"), "3-hour delay": ("delay", "3-hour delay"),
                 "1-hour delay": ("delay", "1-hour delay"), "delay": ("delay", "Delayed start"),
                 "closed": ("closed", "Closed"), "e-learning day": ("elearning", "E-learning day"),
                 "elearning": ("elearning", "E-learning day"), "open": ("open", "Open, on time"),
                 "remove": ("remove", "")}


def read_manual(day):
    out = {}
    try:
        lines = open(MANUAL, encoding="utf-8").read().splitlines()
    except FileNotFoundError:
        return out
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\S+)\s+([^|]+?)\s*(?:\|\s*(.*?))?\s*(?:@\s*(\S+))?$", line)
        if not m or m.group(1) != day:
            continue
        sid, st = m.group(2).lower(), m.group(3).strip().lower()
        if sid not in ALL_IDS or st not in MANUAL_STATUS:
            continue
        kind, words = MANUAL_STATUS[st]
        out[sid] = {"kind": kind, "words": words, "note": (m.group(4) or "").strip()[:200],
                    "seen": m.group(5) or None, "how": "scoop"}
    return out


def build(state, now):
    day = now.date().isoformat()
    auto = state.get("auto", {})
    found = auto.get("found", {}) if auto.get("date") == day else {}
    manual = read_manual(day)
    checks = state.get("checks", {})
    schools = []
    for s in SCHOOLS + NOT_CHECKED:
        sid = s["id"]
        entry = None
        if sid in manual:
            entry = None if manual[sid]["kind"] == "remove" else manual[sid]
        elif sid in found:
            f = found[sid]
            entry = {"kind": f["kind"], "words": f["words"], "quote": f["quote"], "seen": f["seen"],
                     "how": "auto", "pending": f.get("pending", False)}
        c = checks.get(sid, {})
        row = {k: s[k] for k in ("id", "name", "area", "url") if k in s}
        row["info"] = s.get("info", s.get("url"))
        row["checked"] = sid in ALL_IDS and any(x["id"] == sid for x in SCHOOLS)
        if row["checked"]:
            row["lastCheck"] = c.get("checked")
            row["reached"] = c.get("ok")
        else:
            row["how"] = s.get("how")
            row["phone"] = s.get("phone")
        if s.get("private"):
            row["private"] = True
        if s.get("college"):
            row["college"] = True
        if s.get("decides"):
            row["decides"] = s["decides"]
        row["today"] = entry
        schools.append(row)
    nxt = next_check(now)
    return {
        "about": ("School delays and closings for La Porte County, for laporteweathernow.com/closings. Posted only "
                  "when a school's own website says it in exact words about today, or when Scoop adds it from the "
                  "school's announcement. Every entry is for one day only. Always confirm with your school."),
        "updated": now.isoformat(timespec="seconds"),
        "date": day,
        "checking": in_window(now),
        "lastCheck": state.get("lastCheck"),
        "nextCheck": nxt.isoformat(timespec="seconds") if nxt else None,
        "season": "Nov. 1 - Mar. 31, Monday-Friday, 4:30-8:30 AM Central, every 5 minutes",
        "schools": schools,
    }


# ---------- saving ----------
def save(state, now):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "closings-state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=0, sort_keys=True)
    with open(os.path.join(OUT_DIR, "closings.json"), "w", encoding="utf-8") as f:
        json.dump(build(state, now), f, indent=1)
    if os.environ.get("CLOSINGS_PUBLISH") == "1":
        publish(now)


def publish(now):
    token, repo = os.environ.get("TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("  (not published: no TOKEN / GITHUB_REPOSITORY)")
        return
    d = tempfile.mkdtemp(prefix="closings-")
    try:
        for n in ("closings.json", "closings-state.json"):
            shutil.copy(os.path.join(OUT_DIR, n), d)
        env = dict(os.environ, GIT_AUTHOR_NAME="github-actions[bot]", GIT_COMMITTER_NAME="github-actions[bot]",
                   GIT_AUTHOR_EMAIL="41898282+github-actions[bot]@users.noreply.github.com",
                   GIT_COMMITTER_EMAIL="41898282+github-actions[bot]@users.noreply.github.com")
        run = lambda *a: subprocess.run(["git", *a], cwd=d, env=env, check=True, capture_output=True)
        run("init", "-q", "-b", "closings")
        run("add", "closings.json", "closings-state.json")
        run("commit", "-q", "-m", f"School closings ({now:%Y-%m-%d %H:%M %Z})")
        for i in range(3):
            try:
                run("push", "-q", "-f", f"https://x-access-token:{token}@github.com/{repo}.git", "closings:closings")
                return
            except subprocess.CalledProcessError:
                time.sleep(4)
        print("  couldn't push the closings branch")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def report_flags(flags):
    if not flags:
        return
    lines = ["## A school page needs a look", ""]
    for fl in flags:
        lines += [f"**{fl['school']}** ({fl['url']}): not posted, because {fl['why']}.", "",
                  f"> {fl['quote']}", ""]
    lines += ["If it's a real delay or closing for today, add it: Actions > School closings > Run workflow >",
              "mode \"entry\", pick the school and what it said. If not, there's nothing to do."]
    text = "\n".join(lines)
    print(text)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def main(argv):
    mode = argv[1] if len(argv) > 1 else "check"
    fixtures = os.environ.get("CLOSINGS_FIXTURES")
    state = load(os.path.join(OUT_DIR, "closings-state.json"), {})
    now = now_central()
    flags = []
    if mode == "entry":
        if len(argv) < 4:
            print("entry SCHOOL STATUS [NOTE]")
            return 2
        sid, st = argv[2].lower(), argv[3].strip().lower()
        if sid not in ALL_IDS or st not in MANUAL_STATUS:
            print(f"Unknown school or status: {sid} / {st}")
            return 2
        note = " ".join(argv[4:]).replace("|", "/").replace("@", "at").strip()[:200]
        line = f"{now.date().isoformat()}  {sid}  {st}" + (f"  | {note}" if note else "") + f"  @ {now.isoformat(timespec='seconds')}"
        with open(MANUAL, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print("Added: " + line)
        save(state, now)
        return 0
    if mode == "rebuild":
        save(state, now)
        print("Rebuilt closings.json.")
        return 0
    if mode == "check" and not in_window(now) and 19 <= now.hour <= 21:
        tomorrow = now.date() + datetime.timedelta(days=1)
        if in_season(tomorrow) or in_season(now.date()):
            mode = "baseline"   # the 8 PM run: learn the pages and start tomorrow empty
    if mode in ("baseline", "seed"):
        check_once(state, now, learn_only=True, fixtures=fixtures, ancient=(mode == "seed"))
        if mode == "baseline":
            state["auto"] = {"date": (now.date() + datetime.timedelta(days=1)).isoformat() if now.hour >= 12 else now.date().isoformat(), "found": {}}
        save(state, now)
        print(f"Learned {sum(len(v) for v in state.get('pages', {}).values())} pieces of page text.")
        return 0
    if mode == "check" and not in_window(now):
        print(f"Not a checking time ({now:%a %b %-d, %-I:%M %p %Z}); next: {next_check(now)}. Rebuilding only.")
        save(state, now)
        return 0
    rounds = ROUNDS if mode == "check" else 1
    for i in range(rounds):
        t0 = time.time()
        now = now_central()
        if mode == "check" and i and not in_window(now):
            break
        new = check_once(state, now, fixtures=fixtures)
        flags += new
        save(state, now)
        posted = {k: v["words"] for k, v in state.get("auto", {}).get("found", {}).items()}
        bad = [k for k, v in state.get("checks", {}).items() if not v.get("ok")]
        print(f"{now:%-I:%M %p}: checked {len(SCHOOLS)} schools; posted {posted or 'nothing'}; "
              f"{len(new)} new flag(s)" + (f"; couldn't reach {', '.join(bad)}" if bad else ""))
        if i < rounds - 1:
            time.sleep(max(0, GAP - (time.time() - t0)))
    report_flags(flags)
    return 3 if flags else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
