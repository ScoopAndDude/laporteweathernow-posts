#!/usr/bin/env python3
"""Checks a laporteweathernow.com site package before it's published (guard rail, Sept. 30, 2026).

  python3 tools/check_site.py SITE.zip            (or a folder of site files)

Nothing goes live unless this says PASS. It checks:
  - every page's links to the site's own pages and files point at something that exists
    (Netlify matches file names without regard to capital letters, and so does this check)
  - every versioned script and style (name.js?v=xxxxxxxxxx) has the stamp of its actual file,
    so visitors never keep an old copy
  - every page has the site menu (except the few that have their own, like Hard Hat)
  - the pages in sitemap.xml exist
  - no redirect rule is one Netlify silently ignores ("/radar/*  /radar  301"; added Oct. 5, 2026)
  - with Playwright installed: every page opens in English and in Darja on a phone-sized screen
    with no script errors from the site's own code and no sideways scrolling
    (outside services are blocked during the test, so a missing map library is not an error)
Exit code 0 means PASS.
"""
import hashlib
import http.server
import json
import os
import re
import shutil
import socketserver
import sys
import tempfile
import threading
import zipfile

OWN_MENU_OK = ("hardhat/", "scoop-draft.html")      # pages with their own header
NOT_PAGES = re.compile(r"^google[0-9a-f]+\.html$")  # search-engine ownership files, not pages
IGNORED_ERRORS = ("L is not defined", "google is not defined", "OneSignal")   # outside libraries blocked in the test


def unpack(src):
    if os.path.isdir(src):
        return src, None
    tmp = tempfile.mkdtemp(prefix="lpwn-check-")
    with zipfile.ZipFile(src) as z:
        z.extractall(tmp)
    return tmp, tmp


def all_files(root):
    out = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/")
            out[rel.lower()] = rel
    return out


def static_checks(root):
    files = all_files(root)
    problems = []

    def exists(url):
        p = url.split("#")[0].split("?")[0].lstrip("/")
        if not p:
            return True
        return any(c.lower() in files for c in (p, p + ".html", p.rstrip("/") + "/index.html"))

    pages = [files[k] for k in files if k.endswith(".html") and not NOT_PAGES.match(os.path.basename(k))]
    for rel in sorted(pages):
        text = open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'\b(?:href|src)="(/[^"/][^"]*|/)"', text):
            if not exists(m.group(1)):
                problems.append(f"{rel}: link to {m.group(1)} goes nowhere")
        for m in re.finditer(r'(?:href|src)="/?([\w./-]+\.(?:js|css))\?v=([0-9a-f]{10})"', text):
            path, stamp = m.groups()
            real = files.get(path.lower())
            if not real:
                problems.append(f"{rel}: {path} is missing")
                continue
            actual = hashlib.sha256(open(os.path.join(root, real), "rb").read()).hexdigest()[:10]
            if actual != stamp:
                problems.append(f"{rel}: {path}?v={stamp} doesn't match the file (should be {actual})")
        if 'class="nav"' not in text and not rel.startswith(OWN_MENU_OK) and "<nav" not in text:
            problems.append(f"{rel}: no site menu")
    sm = files.get("sitemap.xml")
    if sm:
        for loc in re.findall(r"<loc>https://laporteweathernow\.com(/[^<]*)</loc>", open(os.path.join(root, sm), encoding="utf-8").read()):
            if not exists(loc):
                problems.append(f"sitemap.xml lists {loc}, which doesn't exist")
    # Netlify silently ignores a redirect like "/radar/*  /radar  301" (the * also matches /radar
    # itself, so Netlify treats it as a loop), and the ignored rule also stops every later rule for
    # those addresses. Found live on Oct. 5, 2026; checked against Netlify's own redirect engine.
    rd = files.get("_redirects")
    if rd:
        for n, line in enumerate(open(os.path.join(root, rd), encoding="utf-8").read().splitlines(), 1):
            parts = line.split()
            if len(parts) < 2 or parts[0].startswith("#"):
                continue
            frm, to = parts[0], parts[1]
            status = parts[2] if len(parts) > 2 else "301"
            if frm.endswith("/*") and status.startswith("3") and not re.search(r"[#?]", to) and to.rstrip("/") == frm[:-2]:
                base = frm[:-2]
                problems.append(f"_redirects line {n}: Netlify ignores \"{frm}  {to}\" and every later rule for those addresses; "
                                f"use \"{base}/:slug  {to}\" and \"{base}/:slug/*  {to}\" instead")
    return pages, problems


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass   # the browser often hangs up early on purpose (blocked outside files); that's fine


def browser_checks(root, pages):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, ["(Playwright isn't installed here, so the pages weren't opened in a browser.)"]
    handler = lambda *a, **k: Quiet(*a, directory=root, **k)
    httpd = Server(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    problems, opened = [], 0
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for lang in ("en", "ar-DZ"):
                for rel in sorted(pages):
                    ctx = b.new_context(viewport={"width": 390, "height": 844})
                    page = ctx.new_page()
                    errs = []
                    page.on("pageerror", lambda e: errs.append(str(e)))
                    page.route(lambda u: not u.startswith(base), lambda r: r.abort())
                    try:
                        page.goto(f"{base}/{rel}?lang={lang}", wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(600)
                        over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                        opened += 1
                    except Exception as e:
                        problems.append(f"{lang} {rel}: didn't open ({str(e)[:80]})")
                        ctx.close()
                        continue
                    for e in errs:
                        if not any(x in e for x in IGNORED_ERRORS):
                            problems.append(f"{lang} {rel}: script error: {e[:140]}")
                    if over > 2:
                        problems.append(f"{lang} {rel}: scrolls sideways by {over}px on a phone")
                    ctx.close()
            b.close()
    finally:
        httpd.shutdown()
    return opened, problems


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    root, tmp = unpack(argv[1])
    try:
        pages, problems = static_checks(root)
        opened, more = browser_checks(root, pages)
        problems += more
        real = [p for p in problems if not p.startswith("(")]
        print(f"{len(pages)} pages checked" + (f", {opened} page views opened in a browser (English and Darja)" if opened else "") + ".")
        for p in problems:
            print("  - " + p)
        print("PASS" if not real else f"FAIL: {len(real)} problem(s). Don't publish until they're fixed.")
        return 0 if not real else 1
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
