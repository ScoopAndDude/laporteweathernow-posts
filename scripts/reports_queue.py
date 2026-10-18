#!/usr/bin/env python3
"""Readers' weather reports for laporteweathernow.com/reports (added Oct. 17, 2026).

Nothing a reader sends is public until Scoop approves it:

  1. A reader fills in the form on /reports (Netlify Forms "reader-report": what they saw, how much,
     town, when, an optional photo and first name, and the consent boxes). The page shrinks the photo
     in the phone and drops its hidden data (GPS location, camera details) before it's sent.
  2. Each run of this job (every 15-minute tick) takes new reports from Netlify and opens one issue per
     report in the PRIVATE repository ScoopAndDude/laporteweathernow-reports, with the photo (shrunk
     again here and stripped of all hidden data) saved there under pending/. Only Scoop can see it.
  3. Scoop reads it in the GitHub app and adds a label:
       approve    publish it (after editing the "Shown publicly" lines, if he wants)
       reject     never publish it (closing the issue does the same); its photo is deleted from the queue
       unpublish  take an approved report back off the site
  4. Approved reports go on the public "reports" branch of this repository (reports.json and photos/),
     which the map on /reports reads. Reports older than 45 days drop off, with their photos.

Needs two repository secrets (Settings > Secrets and variables > Actions):
  NETLIFY_FORMS_TOKEN    a Netlify personal access token (to read the form's submissions)
  REPORTS_QUEUE_TOKEN    a GitHub fine-grained token for ScoopAndDude/laporteweathernow-reports only,
                         with Contents: Read and write and Issues: Read and write
Until both are there, it does nothing (and the form on /reports stays hidden). It refuses to work if
the queue repository is public.

  python3 scripts/reports_queue.py      (REPORTS_DIR = the reports branch's files, default ./reports-out)
"""
import base64
import datetime
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
SITE_ID = "18c15497-9910-4f84-abe4-aab2675f9a9d"      # laporteweathernow.com on Netlify
FORM = "reader-report"
QUEUE = os.environ.get("REPORTS_QUEUE_REPO", "ScoopAndDude/laporteweathernow-reports")
OUT = os.environ.get("REPORTS_DIR", "reports-out")
NETLIFY = os.environ.get("NETLIFY_FORMS_TOKEN", "").strip()
GH = os.environ.get("REPORTS_QUEUE_TOKEN", "").strip()
NETLIFY_API = os.environ.get("NETLIFY_API", "https://api.netlify.com/api/v1")
GITHUB_API = os.environ.get("GITHUB_API", "https://api.github.com")
KEEP_DAYS = 45
MAX_NEW = 15

TYPES = {"snow": "Snow", "rain": "Rain", "hail": "Hail", "wind": "Wind damage", "flood": "Flooding"}
HAIL = {"pea": "Pea-size hail (1/4 in)", "dime": "Dime-size hail (3/4 in)", "quarter": "Quarter-size hail (1 in)",
        "golf": "Golf-ball-size hail (1 3/4 in)", "bigger": "Hail bigger than a golf ball"}
DAMAGE = {"limbs": "Large limbs down", "trees": "Trees down", "lines": "Power lines down",
          "building": "Damage to a building", "other": "Other damage"}
FLOOD = {"street": "Water over a street", "road": "Road closed by water", "yard": "Yards or fields flooded",
         "basement": "Basement flooding", "creek": "Creek or river out of its banks"}
WHEN = {"now": "Happening now", "hour": "In the last hour", "today": "Earlier today", "yesterday": "Yesterday"}
# Town centers (from the site's town pages); reports are pinned at the town, never an address.
TOWNS = {
    "La Porte": (41.6081, -86.7189), "Michigan City": (41.7075, -86.8950), "Westville": (41.5375, -86.9050),
    "Wanatah": (41.4303, -86.8819), "Union Mills": (41.4942, -86.7786), "Kingsford Heights": (41.4783, -86.6931),
    "Hanna": (41.4119, -86.7794), "La Crosse": (41.3178, -86.8897), "Rolling Prairie": (41.6731, -86.6239),
    "New Carlisle": (41.7031, -86.5089), "Trail Creek": (41.6972, -86.8572), "Long Beach": (41.7456, -86.8514),
    "Michiana Shores": (41.7570, -86.8167), "Kingsbury": (41.5278, -86.6975), "Mill Creek": (41.5758, -86.5464),
    "Hudson Lake": (41.7120, -86.5370),
}
LABELS = {"new report": ("fbca04", "A reader's report waiting for Scoop"),
          "approve": ("0e8a16", "Publish this report on laporteweathernow.com/reports"),
          "reject": ("b60205", "Never publish this report"),
          "published": ("1d76db", "This report is on the site"),
          "unpublish": ("5319e7", "Take this report back off the site")}


def api(url, token, method="GET", body=None, auth="Bearer", accept="application/json", raw=False):
    data = json.dumps(body).encode() if body is not None else None
    hdr = {"Accept": accept, "User-Agent": "laporteweathernow-reports"}
    if token:
        hdr["Authorization"] = f"{auth} {token}"
    if data is not None:
        hdr["Content-Type"] = "application/json"
    if "api.github.com" in url or url.startswith(GITHUB_API):
        hdr["X-GitHub-Api-Version"] = "2022-11-28"
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    with urllib.request.urlopen(req, timeout=40) as r:
        b = r.read()
        if raw:
            return b
        return json.loads(b) if b.strip() else {}


def gh(path, method="GET", body=None, **kw):
    return api(f"{GITHUB_API}{path}", GH, method, body, **kw)


def clean(t, n=300):
    """Reader text, made safe for an issue and the site: one paragraph, no markup, no @-mentions or links."""
    t = re.sub(r"<[^>]*>", " ", str(t or ""))
    t = re.sub(r"[\x00-\x1f\x7f]+", " ", t)
    t = re.sub(r"https?://\S+|www\.\S+", "[link removed]", t)
    t = re.sub("@(?!\u200b)", "@\u200b", t).replace("`", "'")
    t = re.sub(r"[*_#\[\]|>~]", "", t)
    return re.sub(r"\s+", " ", t).strip()[:n]


def amount_of(d):
    kind = d.get("type")
    if kind in ("snow", "rain"):
        try:
            v = float(str(d.get("inches", "")).strip())
        except ValueError:
            return ""
        if not (0 < v <= (60 if kind == "snow" else 15)):
            return ""
        v = round(v * 10) / 10
        return f"{v:g} in"
    if kind == "hail":
        return HAIL.get(d.get("hail_size"), "")
    if kind == "wind":
        return DAMAGE.get(d.get("damage"), "")
    if kind == "flood":
        return FLOOD.get(d.get("flood_kind"), "")
    return ""


def strip_photo(raw):
    """Re-draws the photo as a plain JPEG, at most 1600 px, with no hidden data at all (no GPS, no EXIF)."""
    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(raw))
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")
    im.thumbnail((1600, 1600))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=82, optimize=True, progressive=True)   # no exif=, no icc_profile=: nothing kept
    return out.getvalue(), im.size


def photo_url(v):
    if isinstance(v, dict):
        return v.get("url")
    if isinstance(v, str) and v.startswith("http"):
        return v
    return None


def fmt(t):
    return t.astimezone(CENTRAL).strftime("%b %-d, %Y, %-I:%M %p %Z")


def issue_body(sub, d, photo_path, form_id):
    when = WHEN.get(d.get("when"), "")
    sent = datetime.datetime.fromisoformat(sub["created_at"].replace("Z", "+00:00"))
    lines = [f"<!-- lpwn-report:{sub['id']} -->",
             "A reader sent a weather report. **Nothing is public until you add the `approve` label.**", ""]
    if photo_path:
        lines += [f"![The reader's photo](https://github.com/{QUEUE}/blob/main/{photo_path}?raw=true)", "",
                  f"(If the photo doesn't show: [open it](https://github.com/{QUEUE}/blob/main/{photo_path}).)", ""]
    lines += ["### Shown publicly (edit these lines before approving, if you want)",
              f"- Type: {TYPES.get(d.get('type'), 'Other')}",
              f"- Amount: {amount_of(d) or '(none)'}",
              f"- Town: {clean(d.get('town'), 40) or '(none)'}",
              f"- When: {when or '(not given)'}",
              f"- Note: {clean(d.get('details'), 300) or '(none)'}",
              f"- Name: {clean(d.get('name'), 40) or '(none)'}",
              f"- Photo: {'yes' if photo_path else 'no'}",
              "",
              "### Not shown",
              f"- Sent {fmt(sent)} (Netlify submission {sub['id']})",
              f"- Photo consent: {'yes' if d.get('consent_photo') else 'no'}; 13 or older: {'yes' if d.get('consent_age') else 'no'}",
              f"- On Netlify: https://app.netlify.com/sites/scoopanddude/forms/{form_id}",
              "",
              "**Approve:** add the label `approve`. **Reject:** add `reject` (or close the issue). "
              "**Later, to take it down:** add `unpublish`."]
    return "\n".join(lines)


def parse_public(body):
    sec = body.split("### Shown publicly", 1)[-1].split("### Not shown", 1)[0]
    out = {}
    for m in re.finditer(r"^- (Type|Amount|Town|When|Note|Name|Photo):\s*(.*)$", sec, re.M):
        v = m.group(2).strip()
        out[m.group(1).lower()] = "" if v in ("(none)", "(not given)") else v
    return out


def load_public():
    try:
        return json.load(open(os.path.join(OUT, "reports.json"), encoding="utf-8"))
    except Exception:
        return {"reports": []}


def main():
    if not NETLIFY or not GH:
        print("Readers' reports aren't set up yet (secrets NETLIFY_FORMS_TOKEN and REPORTS_QUEUE_TOKEN); nothing to do.")
        return 0
    repo = gh(f"/repos/{QUEUE}")
    if not repo.get("private"):
        print(f"{QUEUE} is public; reports would be visible before approval. Make it private first.")
        return 1
    now = datetime.datetime.now(CENTRAL)
    for name, (color, desc) in LABELS.items():
        try:
            gh(f"/repos/{QUEUE}/labels", "POST", {"name": name, "color": color, "description": desc})
        except urllib.error.HTTPError as e:
            if e.code != 422:
                raise
    # Every issue this job ever opened, by report id.
    issues, page = [], 1
    while True:
        batch = gh(f"/repos/{QUEUE}/issues?state=all&per_page=100&page={page}")
        issues += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100 or page >= 20:
            break
        page += 1
    by_id = {}
    for i in issues:
        m = re.search(r"lpwn-report:([0-9a-f]+)", i.get("body") or "")
        if m:
            by_id[m.group(1)] = i
    # 1) New reports from Netlify into the private queue.
    forms = api(f"{NETLIFY_API}/sites/{SITE_ID}/forms", NETLIFY)
    form = next((f for f in forms if f.get("name") == FORM), None)
    opened = 0
    if form:
        subs = api(f"{NETLIFY_API}/forms/{form['id']}/submissions?per_page=100", NETLIFY)
        cutoff = now - datetime.timedelta(days=14)
        for sub in sorted(subs, key=lambda s: s.get("created_at", "")):
            if sub["id"] in by_id or opened >= MAX_NEW:
                continue
            created = datetime.datetime.fromisoformat(sub["created_at"].replace("Z", "+00:00"))
            if created < cutoff:
                continue
            d = sub.get("data") or {}
            if d.get("bot-field") or not d.get("consent_age") or d.get("type") not in TYPES:
                continue
            photo_path = None
            purl = photo_url(d.get("photo"))
            if purl and d.get("consent_photo"):
                try:
                    try:
                        raw = api(purl, None, raw=True, accept="*/*")
                    except urllib.error.HTTPError:
                        raw = api(purl, NETLIFY, raw=True, accept="*/*")
                    jpg, _ = strip_photo(raw)
                    photo_path = f"pending/{sub['id']}.jpg"
                    gh(f"/repos/{QUEUE}/contents/{photo_path}", "PUT",
                       {"message": f"Photo for report {sub['id']}", "content": base64.b64encode(jpg).decode()})
                except Exception as e:
                    print(f"  report {sub['id']}: photo skipped ({str(e)[:80]})")
                    photo_path = None
            title = f"{TYPES[d['type']]}{(' ' + amount_of(d)) if amount_of(d) else ''} in {clean(d.get('town'), 40) or 'a town not given'}"
            gh(f"/repos/{QUEUE}/issues", "POST",
               {"title": title[:120], "body": issue_body(sub, d, photo_path, form["id"]), "labels": ["new report"]})
            opened += 1
    # 2) Scoop's decisions.
    pub = load_public()
    reports = pub.get("reports", [])
    os.makedirs(os.path.join(OUT, "photos"), exist_ok=True)
    changed = False

    def labels(i):
        return {l["name"] for l in i.get("labels", [])}

    def drop_pending(rid):
        path = f"pending/{rid}.jpg"
        try:
            meta = gh(f"/repos/{QUEUE}/contents/{path}")
            gh(f"/repos/{QUEUE}/contents/{path}", "DELETE", {"message": f"Remove photo for report {rid}", "sha": meta["sha"]})
        except urllib.error.HTTPError:
            pass

    for rid, i in by_id.items():
        L = labels(i)
        n = i["number"]
        if "unpublish" in L and "published" in L:
            reports = [r for r in reports if r["id"] != rid]
            p = os.path.join(OUT, "photos", f"{rid}.jpg")
            if os.path.exists(p):
                os.remove(p)
            changed = True
            gh(f"/repos/{QUEUE}/issues/{n}/labels/published", "DELETE")
            gh(f"/repos/{QUEUE}/issues/{n}/labels/unpublish", "DELETE")
            gh(f"/repos/{QUEUE}/issues/{n}/comments", "POST", {"body": f"Taken off the site {fmt(now)}."})
            continue
        if "approve" in L and "published" not in L and "reject" not in L:
            f = parse_public(i.get("body") or "")
            town = next((t for t in TOWNS if t.lower() == f.get("town", "").lower()), None)
            kind = next((k for k, v in TYPES.items() if v.lower() == f.get("type", "").lower()), None)
            if not town or not kind:
                gh(f"/repos/{QUEUE}/issues/{n}/labels/approve", "DELETE")
                gh(f"/repos/{QUEUE}/issues/{n}/comments", "POST", {"body":
                   "Not published: the Town line has to be one of " + ", ".join(TOWNS) +
                   ", and the Type line one of " + ", ".join(TYPES.values()) + ". Fix the line and add `approve` again."})
                continue
            rec = {"id": rid, "type": kind, "typeName": TYPES[kind], "amount": clean(f.get("amount"), 80),
                   "town": town, "lat": TOWNS[town][0], "lon": TOWNS[town][1], "when": clean(f.get("when"), 40),
                   "note": clean(f.get("note"), 300), "name": clean(f.get("name"), 40),
                   "sent": i["created_at"], "approved": now.isoformat(timespec="seconds")}
            if f.get("photo", "").lower().startswith("y"):
                try:
                    raw = gh(f"/repos/{QUEUE}/contents/pending/{rid}.jpg", accept="application/vnd.github.raw", raw=True)
                    jpg, size = strip_photo(raw)
                    open(os.path.join(OUT, "photos", f"{rid}.jpg"), "wb").write(jpg)
                    rec["photo"] = f"photos/{rid}.jpg"
                    rec["photoSize"] = list(size)
                except Exception as e:
                    print(f"  report {rid}: photo not found ({str(e)[:60]}); published without it")
            reports = [r for r in reports if r["id"] != rid] + [rec]
            changed = True
            gh(f"/repos/{QUEUE}/issues/{n}/labels", "POST", {"labels": ["published"]})
            gh(f"/repos/{QUEUE}/issues/{n}/labels/approve", "DELETE")
            gh(f"/repos/{QUEUE}/issues/{n}/comments", "POST",
               {"body": f"Published {fmt(now)}: https://laporteweathernow.com/reports#r-{rid} (add `unpublish` to take it down)."})
            if i["state"] == "open":
                gh(f"/repos/{QUEUE}/issues/{n}", "PATCH", {"state": "closed", "state_reason": "completed"})
            continue
        if ("reject" in L or (i["state"] == "closed" and "published" not in L)) and "rejected" not in (i.get("body") or "")[-40:]:
            drop_pending(rid)
            if i["state"] == "open":
                gh(f"/repos/{QUEUE}/issues/{n}/comments", "POST", {"body": "Rejected: it won't be published, and its photo was deleted from this queue."})
                gh(f"/repos/{QUEUE}/issues/{n}", "PATCH", {"state": "closed", "state_reason": "not_planned"})
            gh(f"/repos/{QUEUE}/issues/{n}", "PATCH", {"body": (i.get("body") or "") + "\n\n<!-- rejected -->"})
    # 3) Old reports drop off.
    old = (now - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    keep = [r for r in reports if r.get("approved", "") >= old]
    if len(keep) != len(reports):
        changed = True
    ids = {r["id"] for r in keep}
    for fn in os.listdir(os.path.join(OUT, "photos")):
        if fn.endswith(".jpg") and fn[:-4] not in ids:
            os.remove(os.path.join(OUT, "photos", fn))
            changed = True
    keep.sort(key=lambda r: r.get("approved", ""), reverse=True)
    if changed or not pub.get("ready"):
        json.dump({"about": "Readers' weather reports approved by Scoop for laporteweathernow.com/reports. Pinned at the "
                            "town, never an address. Photos have no hidden data (no GPS).",
                   "ready": True, "updated": now.isoformat(timespec="seconds"), "reports": keep},
                  open(os.path.join(OUT, "reports.json"), "w", encoding="utf-8"), indent=1)
    print(f"Reports: {opened} new in the queue, {len(keep)} on the site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
