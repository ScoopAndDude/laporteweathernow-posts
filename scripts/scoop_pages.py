#!/usr/bin/env python3
"""Daily Scoop pages: one plain web page per Scoop, so search engines can find them (Oct. 6, 2026).

The Daily Scoop page on the site draws today's post with JavaScript, and an archive that only
lives in scoop-posts.json is invisible to search. This builds, from scoop-posts.json:

  scoop/<date>.html          one page per written daily Scoop (weekly outlooks: week-of-<date>.html),
                             with the whole written forecast, its date, its author and Article data
  scoop/latest.html          a copy of the newest written daily Scoop (its canonical is the dated page)
  scoop/index.html           every Scoop by date, newest first
  scoop/sitemap.xml          the written Scoops, for search engines

laporteweathernow.com shows them at /scoop/<date>, /scoop/latest, /scoop and /scoop-sitemap.xml
through proxy rules in the site's _redirects, so a new Scoop never needs a site publish.
scoop/template.html (the site's header, menu and footer) comes from the site's builder; update it
when the site's menu changes.

Automatic NWS backup posts ("auto": true) get a page too, marked noindex and left out of the
sitemap: they're the Weather Service's words, not ours. New written Scoops are announced to Bing
and other IndexNow search engines (Google reads the sitemap instead) when this runs on GitHub.

  python3 scripts/scoop_pages.py          build (prints what changed)
Safe to run again: files are only rewritten when they change. Started by the Timer every tick and
whenever scoop-posts.json changes.
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "scoop")
SITE = "https://laporteweathernow.com"
CENTRAL = ZoneInfo("America/Chicago")
INDEXNOW_KEY = "6f3c2b9e4a1d48c7b05e9d2a7c13f846"   # also at https://laporteweathernow.com/<key>.txt
MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
MONTHS_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

STYLE = """<style>
.sp-wrap { max-width: 780px; }
.sp-byline { margin: 0 0 18px; font-size: 14px; color: var(--ink-soft); }
.sp-byline a { color: var(--forest); font-weight: 700; }
.sp-note, .sp-correction { margin: 0 0 16px; padding: 12px 16px; border-radius: 10px; background: var(--cream-2, #f1efe6); font-size: 15px; }
.sp-correction { border-left: 4px solid var(--amber); }
.sp-body p { font-size: 17px; line-height: 1.7; margin: 0 0 16px; }
.sp-box { background: var(--card); border-radius: var(--radius); box-shadow: var(--shadow); padding: 16px 20px; margin: 22px 0; }
.sp-box h2 { font-size: 16px; margin: 0 0 8px; font-family: inherit; letter-spacing: 0.02em; }
.sp-box ul { margin: 0; padding-inline-start: 20px; }
.sp-box li { margin: 0 0 6px; font-size: 15px; }
.sp-box a, .sp-pager a, .sp-links a { color: var(--forest); font-weight: 700; }
.sp-disclaimer { font-size: 14px; color: var(--ink-soft); margin: 18px 0; }
.sp-pager { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin: 26px 0 8px; }
.sp-pager a { display: block; background: var(--card); border-radius: 12px; box-shadow: var(--shadow); padding: 12px 16px; text-decoration: none; }
.sp-pager small { display: block; color: var(--ink-faint); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
.sp-links { display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 18px 0 0; font-size: 15px; }
.sp-month { margin: 28px 0 10px; font-size: 22px; }
.sp-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.sp-list li { background: var(--card); border-radius: 12px; box-shadow: var(--shadow); padding: 12px 16px; }
.sp-list a { color: var(--ink); font-weight: 700; text-decoration: none; }
.sp-list a:hover { text-decoration: underline; }
.sp-list .sp-when { display: block; font-size: 13px; color: var(--ink-faint); font-weight: 600; }
</style>"""


def esc(s):
    return html.escape(str(s or ""), quote=True)


def ymd(s):
    return datetime.date.fromisoformat(s[:10])


def long_date(s):
    d = ymd(s)
    return f"{DAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}"


def short_date(s):
    d = ymd(s)
    return f"{MONTHS[d.month - 1]} {d.day}"


def when(iso):
    """'Oct. 6, 2026, 5:42 a.m. CDT' in La Porte time."""
    if not iso:
        return ""
    try:
        t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if t.tzinfo is None:
        t = t.replace(tzinfo=CENTRAL)
    t = t.astimezone(CENTRAL)
    hour = t.hour % 12 or 12
    ampm = "a.m." if t.hour < 12 else "p.m."
    clock = f"{hour}:{t.minute:02d} {ampm}" if t.minute else f"{hour} {ampm}"
    return f"{MONTHS[t.month - 1]} {t.day}, {t.year}, {clock} {t.tzname()}"


def slug(p):
    return ("week-of-" if p.get("type") == "weekly" else "") + p["date"]


def url_of(p):
    return f"{SITE}/scoop/{slug(p)}"


def is_written(p):
    return not p.get("auto")


def paragraphs(p):
    body = p.get("body") or []
    if isinstance(body, str):
        body = [body]
    return [b for b in body if isinstance(b, str) and b.strip()]


def jsonld(graph):
    data = {"@context": "https://schema.org", "@graph": graph}
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"


def crumbs(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": name, "item": SITE + path} for i, (name, path) in enumerate(items, 1)]}


AUTHOR = {"@type": "Person", "@id": f"{SITE}/about#scoop", "name": "Daniel Schlief", "alternateName": "Scoop", "url": f"{SITE}/about#who"}


def fill(template, title, desc, canonical, head, main, og_title=None):
    t = template
    for key, val in (("{{TITLE}}", esc(title)), ("{{DESC}}", esc(desc)), ("{{CANONICAL}}", esc(canonical)),
                     ("{{OG_TITLE}}", esc(og_title or title)), ("{{HEAD}}", head), ("{{MAIN}}", main)):
        t = t.replace(key, val)
    return t


def post_page(p, older, newer, template, latest=False):
    url = url_of(p)
    weekly = p.get("type") == "weekly"
    auto = bool(p.get("auto"))
    title = p.get("title") or "Daily Scoop"
    summary = p.get("summary") or ""
    label = f"Week of {long_date(p['date'])}" if weekly else long_date(p["date"])
    page_title = (f"La Porte, IN Weather Week Ahead, {short_date(p['date'])}, {p['date'][:4]}: Daily Scoop" if weekly
                  else f"La Porte, IN Weather, {short_date(p['date'])}, {p['date'][:4]}: Daily Scoop")
    desc = summary or title
    if len(desc) > 300:
        desc = desc[:297].rsplit(" ", 1)[0] + "..."

    bits = []
    by = ('By <a href="/about#who">Scoop</a>, La Porte Weather Now' if not auto
          else "Automatic update from La Porte Weather Now, in the National Weather Service's words")
    posted, updated = when(p.get("posted")), when(p.get("updated"))
    line = by + (f" &middot; Posted {esc(posted)}" if posted else "")
    if updated and updated != posted:
        line += f" &middot; Updated {esc(updated)}"
    bits.append(f'<p class="sp-byline">{line}</p>')
    if auto:
        bits.append('<p class="sp-note">The written Scoop wasn\'t up yet when this was posted, so it carries the '
                    "National Weather Service's own forecast for La Porte instead.</p>")
    for c in p.get("corrections") or []:
        if isinstance(c, dict) and c.get("text"):
            bits.append(f'<p class="sp-correction"><strong>Correction{", " + esc(short_date(c["date"])) if c.get("date") else ""}:</strong> {esc(c["text"])}</p>')
    bits.append('<div class="sp-body">' + "".join(f"<p>{esc(x)}</p>" for x in paragraphs(p)) + "</div>")

    fc = [f for f in (p.get("forecasts") or []) if isinstance(f, dict) and re.match(r"^\d{4}-\d{2}-\d{2}$", str(f.get("date", "")))]
    if fc:
        items = []
        for f in fc:
            parts = []
            if f.get("high") not in (None, ""):
                parts.append(f"high {esc(f['high'])}")
            if f.get("low") not in (None, ""):
                parts.append(f"low {esc(f['low'])}")
            if f.get("rain") not in (None, ""):
                parts.append(f"{esc(f['rain'])}% chance of rain")
            if parts:
                items.append(f'<li><a href="/track-record#d-{esc(f["date"])}">{DAYS[ymd(f["date"]).weekday()]}, {short_date(f["date"])}</a>: {", ".join(parts)}</li>')
        if items:
            bits.append('<div class="sp-box"><h2>Our forecast on record</h2><ul>' + "".join(items) +
                        '</ul><p class="sp-disclaimer" style="margin:8px 0 0;">We check these against the La Porte airport weather station (KPPO) '
                        'after each day, and never change them. <a href="/track-record">See how they held up</a>.</p></div>')
    src = [s for s in (p.get("sources") or []) if isinstance(s, dict) and str(s.get("url", "")).startswith("https://")]
    if src:
        bits.append('<div class="sp-box"><h2>Sources</h2><ul>' + "".join(
            f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s.get("label") or s["url"])}</a></li>' for s in src) + "</ul></div>")
    bits.append('<p class="sp-disclaimer">Forecasts and warnings come from the National Weather Service office for Northern Indiana; '
                'La Porte Weather Now explains them and never issues its own warnings. For what\'s happening now, see '
                '<a href="/">today\'s La Porte forecast</a> and the <a href="/emergency">Emergency view</a>.</p>')
    pager = []
    if newer:
        pager.append(f'<a href="/scoop/{esc(slug(newer))}"><small>Newer Scoop</small>{esc(short_date(newer["date"]))}: {esc(newer.get("title"))}</a>')
    if older:
        pager.append(f'<a href="/scoop/{esc(slug(older))}"><small>Older Scoop</small>{esc(short_date(older["date"]))}: {esc(older.get("title"))}</a>')
    if pager:
        bits.append('<nav class="sp-pager" aria-label="More Daily Scoops">' + "".join(pager) + "</nav>")
    bits.append('<p class="sp-links"><a href="/scoop">Every Scoop by date</a><a href="/daily-scoop">Today\'s Daily Scoop</a>'
                '<a href="/track-record">Forecast Track Record</a><a href="/weather-questions">Weather questions</a></p>')

    eyebrow = "THE DAILY SCOOP &middot; WEEK AHEAD" if weekly else "THE DAILY SCOOP &middot; LA PORTE, IN"
    main = (f'\n<header class="hero" style="padding-bottom:44px;">\n  <div class="wrap">\n'
            f'    <div class="hero-eyebrow">{eyebrow} &middot; {esc(label.upper())}</div>\n'
            f'    <h1>{esc(title)}</h1>\n' + (f'    <p class="lede">{esc(summary)}</p>\n' if summary else "") +
            '  </div>\n</header>\n\n<section class="section">\n  <div class="wrap sp-wrap">\n    ' + "\n    ".join(bits) +
            "\n  </div>\n</section>\n")

    article = {"@type": "Article", "@id": url + "#article", "headline": title[:110], "description": desc,
               "datePublished": p.get("posted") or p["date"], "dateModified": p.get("updated") or p.get("posted") or p["date"],
               "author": AUTHOR if not auto else {"@id": f"{SITE}/#org"}, "publisher": {"@id": f"{SITE}/#org"},
               "mainEntityOfPage": url, "isPartOf": {"@id": f"{SITE}/#website"}, "inLanguage": "en-US",
               "image": f"{SITE}/og-image.png?v=3", "contentLocation": {"@type": "Place", "name": "La Porte, Indiana"}}
    head = STYLE + "\n" + jsonld([article, crumbs([("Home", "/"), ("Daily Scoop", "/daily-scoop"), (label, f"/scoop/{slug(p)}")])])
    if auto or latest:
        # Backups are NWS's words; "latest" is a copy of a dated page.
        head = ('<meta name="robots" content="noindex, follow" />\n' if auto else "") + head
    return fill(template, page_title, desc, url, head, main, og_title=f"Daily Scoop, {label}: {title}")


def archive_page(posts, template):
    by_month = {}
    for p in posts:
        d = ymd(p["date"])
        by_month.setdefault((d.year, d.month), []).append(p)
    parts = []
    for (y, m) in sorted(by_month, reverse=True):
        parts.append(f'<h2 class="sp-month">{MONTHS_FULL[m - 1]} {y}</h2>\n<ul class="sp-list">')
        for p in by_month[(y, m)]:
            kind = "Week ahead" if p.get("type") == "weekly" else long_date(p["date"])
            note = " &middot; automatic NWS update" if p.get("auto") else ""
            parts.append(f'<li><a href="/scoop/{esc(slug(p))}"><span class="sp-when">{esc(kind)}{note}</span>{esc(p.get("title"))}</a></li>')
        parts.append("</ul>")
    main = ('\n<header class="hero" style="padding-bottom:44px;">\n  <div class="wrap">\n'
            '    <div class="hero-eyebrow">THE DAILY SCOOP &middot; ARCHIVE</div>\n'
            '    <h1>Every Daily Scoop for La Porte, Indiana.</h1>\n'
            '    <p class="lede">The plain-English La Porte County forecast, written every morning from the National Weather Service '
            'forecast and the La Porte airport weather station (KPPO), newest first. Every forecast in them is graded on our '
            '<a href="/track-record" style="color:inherit; text-decoration:underline;">Track Record</a>.</p>\n'
            '  </div>\n</header>\n\n<section class="section">\n  <div class="wrap sp-wrap">\n'
            '    <p class="sp-links" style="margin-top:0;"><a href="/daily-scoop">Today\'s Daily Scoop</a><a href="/">La Porte forecast right now</a></p>\n    '
            + "\n    ".join(parts) + "\n  </div>\n</section>\n")
    url = f"{SITE}/scoop"
    head = STYLE + "\n" + jsonld([
        {"@type": "CollectionPage", "@id": url + "#page", "url": url, "name": "Daily Scoop archive", "inLanguage": "en-US",
         "isPartOf": {"@id": f"{SITE}/#website"}, "about": {"@type": "Place", "name": "La Porte, Indiana"}},
        crumbs([("Home", "/"), ("Daily Scoop", "/daily-scoop"), ("Archive", "/scoop")])])
    return fill(template, "La Porte, IN Daily Weather Briefings: Daily Scoop Archive",
                "Every Daily Scoop: the plain-English La Porte County, Indiana weather briefing written each morning from "
                "the National Weather Service forecast, newest first.", url, head, main, og_title="Daily Scoop archive: La Porte, IN")


def sitemap(posts):
    rows = []
    newest = max((p.get("updated") or p.get("posted") or p["date"])[:10] for p in posts) if posts else None
    if newest:
        rows.append(f"  <url><loc>{SITE}/scoop</loc><lastmod>{newest}</lastmod><changefreq>daily</changefreq></url>")
    for p in posts:
        if not is_written(p):
            continue
        rows.append(f"  <url><loc>{url_of(p)}</loc><lastmod>{(p.get('updated') or p.get('posted') or p['date'])[:10]}</lastmod></url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def write(rel, text, changed):
    path = os.path.join(OUT, rel)
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    if old != text:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        changed.append((rel, old is None))


def ping(urls):
    """Tell IndexNow search engines (Bing and others) about new pages. Only on GitHub."""
    if not urls or not os.environ.get("GITHUB_ACTIONS"):
        return
    body = json.dumps({"host": "laporteweathernow.com", "key": INDEXNOW_KEY,
                       "keyLocation": f"{SITE}/{INDEXNOW_KEY}.txt", "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"IndexNow: {r.status} for {len(urls)} address(es)")
    except Exception as e:   # never fail the job over a ping
        print(f"IndexNow didn't answer: {e}")


def main():
    template = open(os.path.join(OUT, "template.html"), encoding="utf-8").read()
    for key in ("{{TITLE}}", "{{DESC}}", "{{CANONICAL}}", "{{HEAD}}", "{{MAIN}}"):
        if key not in template:
            sys.exit(f"scoop/template.html is missing {key}")
    data = json.load(open(os.path.join(ROOT, "scoop-posts.json"), encoding="utf-8"))
    posts = [p for p in data.get("posts", []) if isinstance(p, dict) and p.get("date") and p.get("title")
             and re.match(r"^\d{4}-\d{2}-\d{2}$", p["date"])]
    # One page per address: if a day somehow has two posts of a kind, the first (newest) wins.
    seen, uniq = set(), []
    for p in posts:
        if slug(p) not in seen:
            seen.add(slug(p))
            uniq.append(p)
    posts = sorted(uniq, key=lambda p: (p["date"], p.get("type") == "weekly"), reverse=True)

    changed = []
    daily = [p for p in posts if p.get("type") != "weekly"]
    for i, p in enumerate(posts):
        line = daily if p.get("type") != "weekly" else [q for q in posts if q.get("type") == "weekly"]
        j = line.index(p)
        newer = line[j - 1] if j > 0 else None
        older = line[j + 1] if j + 1 < len(line) else None
        write(f"{slug(p)}.html", post_page(p, older, newer, template), changed)
    written_daily = [p for p in daily if is_written(p)]
    if written_daily:
        p = written_daily[0]
        j = daily.index(p)
        write("latest.html", post_page(p, daily[j + 1] if j + 1 < len(daily) else None, daily[j - 1] if j > 0 else None,
                                       template, latest=True), changed)
    write("index.html", archive_page(posts, template), changed)
    write("sitemap.xml", sitemap(posts), changed)

    # Pages for posts that no longer exist (a backup replaced by the written Scoop keeps its date, so
    # this only happens if a post is deleted by hand): leave them; the archive just stops listing them.
    for rel, new in changed:
        print(("new " if new else "updated ") + "scoop/" + rel)
    if not changed:
        print("Daily Scoop pages are up to date.")
    fresh = [f"{SITE}/scoop/{rel[:-5]}" for rel, new in changed
             if new and rel.endswith(".html") and rel not in ("latest.html", "index.html")
             and any(slug(p) == rel[:-5] and is_written(p) for p in posts)]
    if fresh:
        ping(fresh + [f"{SITE}/scoop"])


if __name__ == "__main__":
    main()
