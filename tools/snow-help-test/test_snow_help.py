"""End-to-end test of scripts/snow_help.py against fake GitHub and Netlify APIs (Nov. 10, 2026). Nothing real is touched.

  python3 tools/snow-help-test/test_snow_help.py
"""
import json, os, re, subprocess, sys, tempfile, threading, datetime, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

POSTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
Q = "ScoopAndDude/laporteweathernow-reports"
SITE = "18c15497-9910-4f84-abe4-aab2675f9a9d"
now = datetime.datetime.now(datetime.timezone.utc)
iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
S = {"labels": set(), "issues": {}, "comments": {}, "next_issue": 1, "next_comment": 100, "subs": {"f-ask": [], "f-help": []}, "deleted_subs": []}

def sub(sid, data, mins_ago=5):
    return {"id": sid, "created_at": iso(now - datetime.timedelta(minutes=mins_ago)), "data": data}

ASK_OK = dict(clear="driveway-walk", size="2car", tools="shovel", pay="free", when="asap", priority="yes", town="LaPorte",
              address="1234 Main St", name="Mary", phone="219-555-0123", details="Ramp by the side door", consent_age="yes", consent_share="yes")
S["subs"]["f-ask"] = [
    sub("a1", ASK_OK, 30),
    sub("a2", dict(ASK_OK, priority="", pay="pay", town="Michigan City", name="Bob", phone="(219) 555-0177", address="9 Elm Rd"), 20),
    sub("a3", dict(ASK_OK, consent_share=""), 10),                       # no consent: skipped
    sub("a4", dict(ASK_OK, **{"bot-field": "spam"}), 9),                 # bot: skipped
    sub("a5", dict(ASK_OK, phone="555-12"), 8),                          # bad phone: skipped
]
HELP_OK = dict(request="1", name="Mike R.", phone="2195550199", town="LaPorte", tools="blower", kind="free",
               business="", availability="Mornings", consent_age="yes", consent_pledge="yes")
S["subs"]["f-help"] = [sub("h1", HELP_OK, 7), sub("h2", dict(HELP_OK, request="", town="Anywhere", tools="plow", kind="paid", business="Joe's Plowing"), 6)]

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, obj=None):
        b = json.dumps(obj).encode() if obj is not None else b""
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"null")
    def issue_out(self, i):
        return dict(i, labels=[{"name": l} for l in sorted(i["labels"])])
    def route(self, method):
        p = urllib.parse.urlparse(self.path); path = p.path; qs = urllib.parse.parse_qs(p.query)
        if path.startswith("/nf"):
            path = path[3:]
            if method == "GET" and path == f"/sites/{SITE}/forms":
                return self.send(200, [{"name": "snow-help", "id": "f-ask"}, {"name": "snow-helper", "id": "f-help"}, {"name": "reader-report", "id": "f-rr"}])
            m = re.match(r"^/forms/([\w-]+)/submissions$", path)
            if method == "GET" and m: return self.send(200, list(reversed(S["subs"].get(m.group(1), []))))
            m = re.match(r"^/submissions/(\w+)$", path)
            if method == "DELETE" and m:
                S["deleted_subs"].append(m.group(1))
                for k in S["subs"]: S["subs"][k] = [s for s in S["subs"][k] if s["id"] != m.group(1)]
                return self.send(204)
            return self.send(404, {"path": path})
        path = path[3:]
        base = f"/repos/{Q}"
        if path == base and method == "GET": return self.send(200, {"private": True})
        if path == base + "/labels" and method == "POST":
            n = self.body()["name"]
            if n in S["labels"]: return self.send(422, {"message": "exists"})
            S["labels"].add(n); return self.send(201, {})
        if path == base + "/issues" and method == "GET":
            page = int(qs.get("page", ["1"])[0])
            items = sorted(S["issues"].values(), key=lambda i: -i["number"])
            return self.send(200, [self.issue_out(i) for i in items[(page - 1) * 100: page * 100]])
        if path == base + "/issues" and method == "POST":
            b = self.body(); n = S["next_issue"]; S["next_issue"] += 1
            i = {"number": n, "title": b["title"], "body": b["body"], "labels": set(b.get("labels", [])), "state": "open", "created_at": iso(now)}
            S["issues"][n] = i; S["comments"][n] = []
            return self.send(201, self.issue_out(i))
        m = re.match(rf"^{re.escape(base)}/issues/(\d+)$", path)
        if m and method == "PATCH":
            i = S["issues"][int(m.group(1))]; b = self.body()
            for k in ("title", "body", "state"):
                if k in b: i[k] = b[k]
            return self.send(200, self.issue_out(i))
        m = re.match(rf"^{re.escape(base)}/issues/(\d+)/comments$", path)
        if m and method == "POST":
            c = {"id": S["next_comment"], "body": self.body()["body"]}; S["next_comment"] += 1
            S["comments"][int(m.group(1))].append(c); return self.send(201, c)
        if m and method == "GET": return self.send(200, S["comments"][int(m.group(1))])
        m = re.match(rf"^{re.escape(base)}/issues/comments/(\d+)$", path)
        if m and method == "DELETE":
            cid = int(m.group(1))
            for n in S["comments"]: S["comments"][n] = [c for c in S["comments"][n] if c["id"] != cid]
            return self.send(204)
        m = re.match(rf"^{re.escape(base)}/issues/(\d+)/labels$", path)
        if m and method == "POST":
            S["issues"][int(m.group(1))]["labels"] |= set(self.body()["labels"]); return self.send(200, [])
        m = re.match(rf"^{re.escape(base)}/issues/(\d+)/labels/(.+)$", path)
        if m and method == "DELETE":
            i = S["issues"][int(m.group(1))]; name = urllib.parse.unquote(m.group(2))
            if name not in i["labels"]: return self.send(404, {})
            i["labels"].discard(name); return self.send(200, [])
        return self.send(404, {"path": path, "method": method})
    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_PATCH(self): self.route("PATCH")
    def do_DELETE(self): self.route("DELETE")

srv = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
out_dir = tempfile.mkdtemp()
env = dict(os.environ, NETLIFY_FORMS_TOKEN="x", REPORTS_QUEUE_TOKEN="y", REPORTS_DIR=out_dir,
           NETLIFY_API=f"http://127.0.0.1:{port}/nf", GITHUB_API=f"http://127.0.0.1:{port}/gh")
PERSONAL = ["Mary", "Bob", "Mike", "1234 Main", "9 Elm", "555-0123", "555-0177", "555-0199", "Ramp", "Joe"]

def run(label):
    r = subprocess.run([sys.executable, "scripts/snow_help.py"], cwd=POSTS, env=env, capture_output=True, text=True)
    log = r.stdout + r.stderr
    leaks = [w for w in PERSONAL if w in log]
    print(f"[{label}] exit={r.returncode} :: {log.strip()}")
    assert r.returncode == 0, "script failed"
    assert not leaks, f"personal data in the log: {leaks}"
    try: return json.load(open(os.path.join(out_dir, "snow-help.json")))
    except FileNotFoundError: return None

def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    assert cond, msg

# 1) new requests and helpers
b = run("first run")
asks = [i for i in S["issues"].values() if "snow help" in i["labels"]]
helps = [i for i in S["issues"].values() if "snow helper" in i["labels"]]
check(len(asks) == 2 and len(helps) == 2, "2 requests and 2 helper sign-ups queued; 3 bad ones skipped")
check(all(not re.search("Mary|Bob|Main St|Elm|555-", i["title"] + i["body"]) for i in asks + helps), "no personal data in any title or issue text")
check(all(any("lpwn-snow-private" in c["body"] for c in S["comments"][i["number"]]) for i in asks + helps), "each has a private comment")
c1 = S["comments"][1][0]["body"]
check("(219) 555-0123" in c1 and "1234 Main St, LaPorte" in c1 and "google.com/maps" in c1, "request #1's private comment has phone, address and map")
h_for_1 = next(i for i in helps if "Offering to help with #1." in i["body"])
check(h_for_1["title"].startswith("Snow helper for #1: LaPorte"), "helper sign-up names request #1: " + h_for_1["title"])
check(b and b["ready"] is True and b["requests"] == [], "board is ready and empty (nothing approved yet)")
b = run("second run, nothing new")
check(len(S["issues"]) == 4, "nothing queued twice")

# 2) approve #1 (with a public note), reject #2
S["issues"][1]["body"] = S["issues"][1]["body"].replace("- Note: (none)", "- Note: Near the high school")
S["issues"][1]["labels"].add("approve"); S["issues"][2]["labels"].add("reject")
b = run("approve #1, reject #2")
r1 = next(r for r in b["requests"] if r["id"] == 1)
check(r1["status"] == "open" and r1["town"] == "LaPorte" and r1["note"] == "Near the high school" and r1["priority"] is True and r1["payKind"] == "free", "#1 on the board: " + json.dumps(r1))
check(not any(k in json.dumps(b) for k in ["Mary", "Main St", "555", "Ramp"]), "board has no private details")
check("published" in S["issues"][1]["labels"] and "approve" not in S["issues"][1]["labels"], "#1 labeled published")
check(S["issues"][2]["state"] == "closed" and "<!-- rejected -->" in S["issues"][2]["body"] and all(r["id"] != 2 for r in b["requests"]), "#2 rejected and closed")
n_comments_2 = len(S["comments"][2]); run("again"); check(len(S["comments"][2]) == n_comments_2, "reject isn't repeated")

# 3) helper found, then closed
S["issues"][1]["labels"].add("helper found")
b = run("helper found"); check(b["requests"][0]["status"] == "matched", "#1 shows a helper on the way")
S["issues"][1]["state"] = "closed"
b = run("closed"); r1 = b["requests"][0]
check(r1["status"] == "done" and r1.get("doneAt") and "done" in S["issues"][1]["labels"] and b["helped"] == 1, "#1 cleared, labeled done, helped = 1")

# 4) a day later it comes off the board
r1["doneAt"] = (datetime.datetime.fromisoformat(r1["doneAt"]) - datetime.timedelta(hours=25)).isoformat()
json.dump(b, open(os.path.join(out_dir, "snow-help.json"), "w"))
b = run("a day later"); check(b["requests"] == [] and b["helped"] == 1, "#1 off the board; still counted as helped")

# 5) a new request, approved, then left up more than three days
S["subs"]["f-ask"].append(sub("a6", dict(ASK_OK, town="Westville", name="Ann", phone="2195550111", address="5 Oak"), 1))
run("new request a6")
n6 = max(S["issues"]); S["issues"][n6]["labels"].add("approve")
b = run("approve a6"); r6 = next(r for r in b["requests"] if r["id"] == n6)
r6["posted"] = (datetime.datetime.fromisoformat(r6["posted"]) - datetime.timedelta(days=4)).isoformat()
json.dump(b, open(os.path.join(out_dir, "snow-help.json"), "w"))
b = run("four days later")
check(all(r["id"] != n6 for r in b["requests"]) and "published" not in S["issues"][n6]["labels"], "stale request came off the board and can be approved again")

# 6) a bad edit before approving
S["subs"]["f-ask"].append(sub("a7", dict(ASK_OK, name="Al", phone="2195550122", address="7 Pine"), 1))
run("new request a7"); n7 = max(S["issues"])
S["issues"][n7]["body"] = S["issues"][n7]["body"].replace("- Town: LaPorte", "- Town: Chicago"); S["issues"][n7]["labels"].add("approve")
b = run("bad town"); check(all(r["id"] != n7 for r in b["requests"]) and "Not posted" in S["comments"][n7][-1]["body"], "bad Town line is refused with a note")

# 7) unpublish
S["issues"][n7]["body"] = S["issues"][n7]["body"].replace("- Town: Chicago", "- Town: LaPorte"); S["issues"][n7]["labels"].add("approve")
b = run("fixed and approved"); check(any(r["id"] == n7 for r in b["requests"]), "fixed request goes up")
S["issues"][n7]["labels"].add("unpublish")
b = run("unpublish"); check(all(r["id"] != n7 for r in b["requests"]) and not ({"unpublish", "published"} & S["issues"][n7]["labels"]), "unpublished")

# 8) erase after 60 days
S["issues"][1]["created_at"] = iso(now - datetime.timedelta(days=61))
S["issues"][3]["created_at"] = iso(now - datetime.timedelta(days=61))   # a helper: kept until 180 days
for s_ in S["subs"]["f-ask"]:
    if s_["id"] == "a5": s_["created_at"] = iso(now - datetime.timedelta(days=61))   # never queued (bad phone)
run("61 days later")
check(not any("lpwn-snow-private" in c["body"] for c in S["comments"][1]) and "<!-- erased -->" in S["issues"][1]["body"] and "a1" in S["deleted_subs"], "request #1: private comment and Netlify copy deleted")
check(any("lpwn-snow-private" in c["body"] for c in S["comments"][3]), "helper sign-up kept (not 180 days yet)")
check("a5" in S["deleted_subs"] and "a3" not in S["deleted_subs"], "an old submission that never got queued is deleted too; newer ones stay")
n_patch = S["issues"][1]["body"]; run("again"); check(S["issues"][1]["body"] == n_patch, "erasing isn't repeated")
print("\nALL GOOD")
