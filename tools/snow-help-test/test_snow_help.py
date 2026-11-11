"""End-to-end test of scripts/snow_help.py against fake GitHub, Netlify and Brevo APIs (Nov. 10, 2026).
Nothing real is touched and no email is sent.

  python3 tools/snow-help-test/test_snow_help.py
"""
import datetime, hashlib, hmac, json, os, re, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

POSTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
Q = "ScoopAndDude/laporteweathernow-reports"
SITE = "18c15497-9910-4f84-abe4-aab2675f9a9d"
now = datetime.datetime.now(datetime.timezone.utc)
iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
S = {"labels": set(), "issues": {}, "comments": {}, "next_issue": 1, "next_comment": 100,
     "subs": {"f-ask": [], "f-help": [], "f-up": []}, "deleted_subs": [], "mail": [], "credits": 300, "brevo_down": False}
SECRET = hashlib.sha256(b"lpwn-snow-help:y").digest()
tok = lambda kind, n: hmac.new(SECRET, f"{kind}:{n}".encode(), hashlib.sha256).hexdigest()[:20]
seq = [0]

def sub(form, data, mins_ago=5):
    seq[0] += 1
    s = {"id": f"s{seq[0]}", "created_at": iso(now - datetime.timedelta(minutes=mins_ago)), "data": data}
    S["subs"][form].append(s)
    return s

ASK = dict(clear="driveway-walk", size="2car", tools="shovel", pay="free", when="asap", priority="yes", town="LaPorte",
           name="Mary", phone="219-555-0123", email="mary@example.com", details="Ramp by the side door", consent_age="yes", consent_share="yes")
HELP = dict(request="", name="Mike R.", phone="2195550199", email="mike@example.com", town="LaPorte", tools="blower", kind="free",
            business="", availability="Mornings", list="yes", consent_age="yes", consent_pledge="yes")

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, obj=None):
        b = json.dumps(obj).encode() if obj is not None else b""
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"null")
    def out(self, i):
        return dict(i, labels=[{"name": l} for l in sorted(i["labels"])])
    def route(self, method):
        p = urllib.parse.urlparse(self.path); path = p.path; qs = urllib.parse.parse_qs(p.query)
        if path.startswith("/br"):
            path = path[3:]
            if S["brevo_down"]: return self.send(500, {})
            if path == "/account": return self.send(200, {"plan": [{"type": "free", "creditsType": "sendLimit", "credits": S["credits"]}]})
            if path.startswith("/contacts/lists/"): return self.send(200, {"totalSubscribers": 40})
            if path == "/smtp/email" and method == "POST":
                b = self.body(); S["mail"].append({"to": b["to"][0]["email"], "subject": b["subject"], "text": b["textContent"]})
                return self.send(201, {"messageId": "m"})
            return self.send(404, {})
        if path.startswith("/nf"):
            path = path[3:]
            if method == "GET" and path == f"/sites/{SITE}/forms":
                return self.send(200, [{"name": "snow-help", "id": "f-ask"}, {"name": "snow-helper", "id": "f-help"}, {"name": "snow-update", "id": "f-up"}])
            m = re.match(r"^/forms/([\w-]+)/submissions$", path)
            if method == "GET" and m: return self.send(200, list(reversed(S["subs"].get(m.group(1), []))))
            m = re.match(r"^/submissions/(\w+)$", path)
            if method == "DELETE" and m:
                S["deleted_subs"].append(m.group(1))
                for k in S["subs"]: S["subs"][k] = [s for s in S["subs"][k] if s["id"] != m.group(1)]
                return self.send(204)
            return self.send(404, {})
        path = path[3:]; base = f"/repos/{Q}"
        if path == base and method == "GET": return self.send(200, {"private": True})
        if path == base + "/labels" and method == "POST":
            n = self.body()["name"]
            if n in S["labels"]: return self.send(422, {})
            S["labels"].add(n); return self.send(201, {})
        if path == base + "/issues" and method == "GET":
            page = int(qs.get("page", ["1"])[0]); items = sorted(S["issues"].values(), key=lambda i: -i["number"])
            return self.send(200, [self.out(i) for i in items[(page - 1) * 100: page * 100]])
        if path == base + "/issues" and method == "POST":
            b = self.body(); n = S["next_issue"]; S["next_issue"] += 1
            i = {"number": n, "title": b["title"], "body": b["body"], "labels": set(b.get("labels", [])), "state": "open", "created_at": iso(now)}
            S["issues"][n] = i; S["comments"][n] = []; return self.send(201, self.out(i))
        m = re.match(rf"^{re.escape(base)}/issues/(\d+)$", path)
        if m and method == "PATCH":
            i = S["issues"][int(m.group(1))]; b = self.body()
            for k in ("title", "body", "state"):
                if k in b: i[k] = b[k]
            return self.send(200, self.out(i))
        m = re.match(rf"^{re.escape(base)}/issues/(\d+)/comments$", path)
        if m and method == "POST":
            c = {"id": S["next_comment"], "body": self.body()["body"]}; S["next_comment"] += 1
            S["comments"][int(m.group(1))].append(c); return self.send(201, c)
        if m and method == "GET": return self.send(200, S["comments"][int(m.group(1))])
        m = re.match(rf"^{re.escape(base)}/issues/comments/(\d+)$", path)
        if m and method == "DELETE":
            for n in S["comments"]: S["comments"][n] = [c for c in S["comments"][n] if c["id"] != int(m.group(1))]
            return self.send(204)
        m = re.match(rf"^{re.escape(base)}/issues/(\d+)/labels$", path)
        if m and method == "POST":
            S["issues"][int(m.group(1))]["labels"] |= set(self.body()["labels"]); return self.send(200, [])
        m = re.match(rf"^{re.escape(base)}/issues/(\d+)/labels/(.+)$", path)
        if m and method == "DELETE":
            i = S["issues"][int(m.group(1))]; name = urllib.parse.unquote(m.group(2))
            if name not in i["labels"]: return self.send(404, {})
            i["labels"].discard(name); return self.send(200, [])
        return self.send(404, {})
    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_PATCH(self): self.route("PATCH")
    def do_DELETE(self): self.route("DELETE")

srv = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
out_dir = tempfile.mkdtemp()
env = dict(os.environ, NETLIFY_FORMS_TOKEN="x", REPORTS_QUEUE_TOKEN="y", BREVO_API_KEY="z", REPORTS_DIR=out_dir,
           NETLIFY_API=f"http://127.0.0.1:{port}/nf", GITHUB_API=f"http://127.0.0.1:{port}/gh", BREVO_API=f"http://127.0.0.1:{port}/br")
PERSONAL = ["Mary", "Bob", "Mike", "Joe", "Ann", "555-0", "5550", "Ramp", "@example"]
BOARD = os.path.join(out_dir, "snow-help.json")

def run(label):
    S["mail"].clear()
    r = subprocess.run([sys.executable, "scripts/snow_help.py"], cwd=POSTS, env=env, capture_output=True, text=True)
    log = r.stdout + r.stderr
    print(f"[{label}] exit={r.returncode} :: {log.strip()}")
    assert r.returncode == 0, "script failed"
    assert not [w for w in PERSONAL if w in log], "personal data in the log"
    b = json.load(open(BOARD))
    assert not [w for w in PERSONAL if w in json.dumps(b)], "personal data on the public board"
    return b

def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    assert cond, msg

def req(b, n): return next((r for r in b["requests"] if r["id"] == n), None)
def to(addr): return [m for m in S["mail"] if m["to"] == addr]

# 1) A helper joins the list; then a request posts by itself and that helper is emailed.
sub("f-help", HELP, 40)
sub("f-help", dict(HELP, name="Joe P.", phone="2195550144", email="joe@example.com", town="Michigan City", kind="paid", tools="plow", business="Joe's Plowing"), 39)
b = run("two helpers join the list")
check(len(to("mike@example.com")) == 1 and "helper list" in to("mike@example.com")[0]["subject"] and "act=stop" in to("mike@example.com")[0]["text"], "list helper gets a welcome email with a stop link")
check(b["ready"] and b["requests"] == [], "board ready and empty")
sub("f-ask", ASK, 10)
sub("f-ask", dict(ASK, consent_share=""), 9); sub("f-ask", dict(ASK, **{"bot-field": "x"}), 9); sub("f-ask", dict(ASK, phone="555-12"), 9)
b = run("a request comes in")
r3 = req(b, 3)
check(r3 and r3["status"] == "open" and r3["town"] == "LaPorte" and r3["priority"] and r3["helpers"] == 0, "request #3 is on the board by itself: " + json.dumps(r3))
check(all(not re.search("Mary|555|Ramp|example", i["title"] + i["body"]) for i in S["issues"].values()), "no personal data in any issue title or text")
check("(219) 555-0123" in S["comments"][3][0]["body"] and "mary@example.com" in S["comments"][3][0]["body"], "private comment holds name, phone, email")
check(len(to("mary@example.com")) == 1 and "act=cancel" in to("mary@example.com")[0]["text"], "asker gets a confirmation with cancel and cleared links")
m = to("mike@example.com")
check(len(m) == 1 and "?help=3" in m[0]["text"] and "Mary" not in m[0]["text"] and "555" not in m[0]["text"], "LaPorte list helper is emailed the request, without the asker's details")
check(not to("joe@example.com"), "Michigan City paid-only helper isn't emailed")
b = run("nothing new"); check(len(S["issues"]) == 3 and not S["mail"], "nothing posted or emailed twice")

# 2) Limits: same request again, and a third open request from one phone.
sub("f-ask", ASK, 1)
sub("f-ask", dict(ASK, clear="steps", email=""), 1)
sub("f-ask", dict(ASK, clear="walk", email=""), 0)
b = run("repeats and too many")
check(len(b["requests"]) == 2, "duplicate skipped; second request posted; third open one from the same phone skipped")

# 3) A helper offers: both sides are connected by email.
sub("f-help", dict(HELP, request="3", list=""), 1)
b = run("Mike offers on #3")
m = to("mike@example.com")
check(len(m) == 1 and "Mary" in m[0]["text"] and "(219) 555-0123" in m[0]["text"] and "Ramp" in m[0]["text"] and "act=done" in m[0]["text"], "helper is emailed the asker's first name, phone and note")
m = to("mary@example.com")
check(len(m) == 1 and "Mike R." in m[0]["text"] and "(219) 555-0199" in m[0]["text"], "asker is emailed the helper's name and phone")
check(req(b, 3)["status"] == "matched" and req(b, 3)["helpers"] == 1 and "helper found" in S["issues"][3]["labels"], "board shows 1 helper offered")
hi = max(S["issues"]); check("mail pending" not in S["issues"][hi]["labels"], "offer settled")
sub("f-help", dict(HELP, request="3", list=""), 0)
b = run("Mike offers on #3 again"); check(req(b, 3)["helpers"] == 1 and not S["mail"], "same offer twice is ignored")
sub("f-help", dict(HELP, request="3", name="Mary", phone="219-555-0123", email="mary@example.com", list=""), 0)
b = run("asker offers on own request"); check(req(b, 3)["helpers"] == 1, "can't offer on your own request")

# 4) Email down: the offer waits and is retried.
S["brevo_down"] = True
sub("f-help", dict(HELP, request="3", name="Ann K.", phone="2195550155", email="ann@example.com", list=""), 0)
b = run("Ann offers while email is down")
ai = max(S["issues"]); check("mail pending" in S["issues"][ai]["labels"] and req(b, 3)["helpers"] == 1, "offer waits when the email can't go out")
S["brevo_down"] = False
b = run("email is back")
check("mail pending" not in S["issues"][ai]["labels"] and req(b, 3)["helpers"] == 2 and any("Mary" in m["text"] for m in to("ann@example.com")), "retried and connected")

# 5) Up to 3 helpers; the 4th is told it's covered.
sub("f-help", dict(HELP, request="3", name="Bob T.", phone="2195550166", email="bob@example.com", list=""), 1)
sub("f-help", dict(HELP, request="3", name="Joe P.", phone="2195550144", email="joe@example.com", list=""), 0)
b = run("two more offers")
check(req(b, 3)["helpers"] == 3 and "already covered" in to("joe@example.com")[0]["subject"] and "555-0123" not in to("joe@example.com")[0]["text"], "3 helpers max; the 4th gets no phone number")

# 6) Daily send limit: nothing goes out when the morning emails need what's left.
S["credits"] = 50
sub("f-ask", dict(ASK, phone="2195550177", name="Bob", email="bob2@example.com", town="Westville"), 0)
b = run("almost out of sends"); check(not S["mail"] and any(r["town"] == "Westville" for r in b["requests"]), "request still posts; no email past the daily limit")
S["credits"] = 300

# 7) Links from the emails: cleared, cancel, stop; a bad token does nothing.
sub("f-up", {"action": "done", "id": "3", "token": "0" * 20}, 0)
b = run("bad token"); check(req(b, 3)["status"] == "matched" and not S["subs"]["f-up"], "bad token ignored and removed")
sub("f-up", {"action": "done", "id": "3", "token": tok("done", 3)}, 0)
b = run("marked cleared"); check(req(b, 3)["status"] == "done" and b["helped"] == 1, "cleared; 1 neighbor helped")
n2 = next(r["id"] for r in b["requests"] if r["clear"].startswith("Steps"))
sub("f-up", {"action": "cancel", "id": str(n2), "token": tok("cancel", n2)}, 0)
b = run("canceled")
check(not req(b, n2) and S["issues"][n2]["state"] == "closed" and not any("lpwn-snow-private" in c["body"] for c in S["comments"][n2]), "canceled: off the board, private details erased")
sub("f-up", {"action": "stop", "id": "1", "token": tok("stop", 1)}, 0)
b = run("helper leaves the list")
check("on list" not in S["issues"][1]["labels"] and S["issues"][1]["state"] == "closed" and not any("lpwn-snow-private" in c["body"] for c in S["comments"][1]), "helper off the list and erased")
sub("f-ask", dict(ASK, phone="2195550188", name="Ann", email="", clear="driveway"), 0)
b = run("new LaPorte request after Mike left"); check(not to("mike@example.com"), "no email to a helper who left")

# 8) Time: cleared ones leave after a day, open ones after three; Scoop can take one down or put one back.
r = req(b, 3); r["doneAt"] = (datetime.datetime.fromisoformat(r["doneAt"]) - datetime.timedelta(hours=25)).isoformat()
old = next(x for x in b["requests"] if x["town"] == "Westville"); old["posted"] = (datetime.datetime.fromisoformat(old["posted"]) - datetime.timedelta(days=4)).isoformat()
json.dump(b, open(BOARD, "w"))
b = run("days later")
check(not req(b, 3) and not req(b, old["id"]) and S["issues"][old["id"]]["state"] == "closed" and b["helped"] == 1, "cleared and stale requests came off the board")
S["issues"][old["id"]]["labels"].add("approve")
b = run("Scoop puts one back"); check(req(b, old["id"]) and req(b, old["id"])["status"] == "open", "approve puts an expired request back up")
S["issues"][old["id"]]["labels"].add("unpublish")
b = run("Scoop takes one down"); check(not req(b, old["id"]), "unpublish takes it down")

# 9) Erase after 60 days.
S["issues"][3]["created_at"] = iso(now - datetime.timedelta(days=61))
run("61 days later")
check(not any("lpwn-snow-private" in c["body"] for c in S["comments"][3]) and "<!-- erased -->" in S["issues"][3]["body"], "request #3's private details erased")
print("\nALL GOOD")
