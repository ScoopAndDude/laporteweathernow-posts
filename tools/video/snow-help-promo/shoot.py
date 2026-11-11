import json, threading, http.server, socketserver, functools, datetime, urllib.parse
from playwright.sync_api import sync_playwright
SITE = "/home/claude/laporteweathernow-site/site"
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); p = u.path
        if "." not in p.rsplit("/", 1)[-1] and p != "/": self.path = p + ".html" + ("?" + u.query if u.query else "")
        return super().do_GET()
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Q, directory=SITE)); threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6)))
ago = lambda **k: (now - datetime.timedelta(**k)).isoformat(timespec="seconds")
R = lambda i, town, clear, size, tools, pay, kind, when, pri, helpers, **k: dict(id=i, town=town, clear=clear, size=size, tools=tools, pay=pay, payKind=kind, when=when, priority=pri, note="", helpers=helpers, status="matched" if helpers else "open", **k)
BOARD = {"ready": True, "helped": 0, "maxHelpers": 3, "requests": [
    R(12, "LaPorte", "Driveway and sidewalk", "2-car driveway", "Shovel is fine", "Free help", "free", "As soon as possible", True, 0, posted=ago(minutes=20)),
    R(13, "Westville", "Driveway", "Long or country driveway", "Needs a plow", "Will pay", "pay", "By tomorrow morning", False, 0, posted=ago(minutes=45)),
    R(11, "Michigan City", "Steps and path to the door", "Just a walk or steps", "Shovel is fine", "Free or small pay", "either", "Sometime today", True, 1, posted=ago(hours=2))]}
def route(r):
    u = r.request.url
    if u.startswith(base): return r.continue_()
    if u.endswith("/reports/snow-help.json"): return r.fulfill(status=200, content_type="application/json", body=json.dumps(BOARD))
    return r.abort()
HIDE = "for (const e of document.querySelectorAll('body *')) { const p = getComputedStyle(e).position; if (p === 'fixed' || p === 'sticky') e.style.display = 'none'; }"
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    pg = ctx.new_page(); pg.route("**/*", route)
    pg.goto(base + "/snow-help", wait_until="networkidle"); pg.wait_for_timeout(800); pg.evaluate(HIDE)
    pg.screenshot(path="shots/sh_hero.jpg", type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": 390, "height": 1250}, full_page=True)
    for name in ("ask", "board", "offer"):
        pg.locator("#" + name).screenshot(path=f"shots/sh_{name}.jpg", type="jpeg", quality=92)
    ctx.close()
    # the real homepage, live
    try:
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg = ctx.new_page()
        pg.goto("https://laporteweathernow.com/", wait_until="load", timeout=45000); pg.wait_for_timeout(6000); pg.evaluate(HIDE)
        pg.screenshot(path="shots/home.jpg", type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": 390, "height": 1700}, full_page=True)
        print("home: live")
    except Exception as e:
        print("home live failed:", str(e)[:120])
    b.close()
