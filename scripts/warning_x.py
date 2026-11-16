#!/usr/bin/env python3
"""Posts new National Weather Service Warnings for La Porte County to X through Buffer.

Added Nov. 16, 2026. Moved here from a Grok Bot routine so the check can run on free
GitHub Actions every 15 minutes. The Timer starts it every tick (GitHub's own schedules
for this repository have been late); the workflow's cron is a backup. Safe to run twice:
each warning is posted once, by its NWS alert id.

Only events whose name contains "Warning", and only when the alert is for La Porte County
(zones INZ103, INZ203 or county INC091). Warnings for other counties are never posted.
The town is written LaPorte (one word) in the post. When there's nothing new, the job
prints that and posts nothing.

Needs the BUFFER_API_KEY repository secret (the same key as the Daily Video). Posts go
to the ScoopAndDude X channel already connected in Buffer. Posted ids are kept on the
"warning-x-state" branch so a warning is never posted twice.

  python3 scripts/warning_x.py
  python3 scripts/warning_x.py --dry-run   # fetch and print, post nothing, don't save

The key is only ever sent to api.buffer.com, in a header, and never printed.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

NWS = "https://api.weather.gov"
ZONES = ["INZ103", "INZ203", "INC091"]  # northern La Porte, southern La Porte, La Porte County
POINT = "41.6081,-86.7189"
LAPORTE_UGC = set(ZONES)
LAPORTE_SAME = {"018091"}
UA = "LaPorteWeatherNow/1.0 (+https://laporteweathernow.com)"
CENTRAL = ZoneInfo("America/Chicago")
BUFFER_API = "https://api.buffer.com"
# Scoop's Buffer org and the X (@ScoopAndDude) channel already used by scripts/buffer_post.py.
BUFFER_ORG = "6abd7addf66b764edacca840"
BUFFER_X_CHANNEL = "6abd7b5bea19ca0bde39378f"
LINK = "https://laporteweathernow.com/emergency"
TAGS = "#LaPorte #INwx"
STATE_NAME = "posted-alerts.txt"
X_LIMIT = 280

M_CREATE = """mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    __typename
    ... on PostActionSuccess { post { id status externalLink error { message } } }
    ... on NotFoundError { message }
    ... on UnauthorizedError { message }
    ... on UnexpectedError { message }
    ... on LimitReachedError { message }
    ... on InvalidInputError { message }
  }
}"""


class BufferError(RuntimeError):
    pass


def state_path():
    return os.environ.get("WARNING_X_STATE") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", STATE_NAME)


def load_posted(path):
    """NWS alert ids already posted, one per line. Lines starting with # are ignored."""
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line.split()[0])
    return out


def save_posted(path, ids):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    lines = [
        "# NWS alert ids already posted to X for La Porte County. One per line.",
        "# Do not delete a line, or that warning can go out again.",
    ]
    lines.extend(ids)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def alert_id(feat):
    p = (feat or {}).get("properties") or {}
    return p.get("id") or (feat or {}).get("id") or ""


def is_warning(props):
    return "Warning" in str((props or {}).get("event") or "")


def is_laporte_county(props):
    """True only when the alert itself is for La Porte County, IN (never a neighbor only)."""
    geo = (props or {}).get("geocode") or {}
    ugc = set(geo.get("UGC") or [])
    same = {str(x) for x in (geo.get("SAME") or [])}
    if ugc & LAPORTE_UGC or same & LAPORTE_SAME:
        return True
    for z in (props or {}).get("affectedZones") or []:
        if str(z).rstrip("/").split("/")[-1] in LAPORTE_UGC:
            return True
    return False


def still_in_effect(props, now):
    if (props or {}).get("status") and props.get("status") != "Actual":
        return False
    if str((props or {}).get("messageType") or "").lower() == "cancel":
        return False
    end_s = (props or {}).get("ends") or (props or {}).get("expires")
    if not end_s:
        return True
    try:
        end = datetime.datetime.fromisoformat(end_s)
        if end.tzinfo is None:
            end = end.replace(tzinfo=datetime.timezone.utc)
        return end > now
    except Exception:
        return True


def where_words(props):
    ugc = set(((props or {}).get("geocode") or {}).get("UGC") or [])
    area = (props or {}).get("areaDesc") or ""
    north = "INZ103" in ugc or "Northern La Porte" in area
    south = "INZ203" in ugc or "Southern La Porte" in area
    if "INC091" in ugc or (north and south) or not (north or south):
        return "LaPorte County"
    if north:
        return "northern LaPorte County"
    return "southern LaPorte County"


def clock(dt):
    dt = dt.astimezone(CENTRAL)
    mins = f":{dt.minute:02d}" if dt.minute else ""
    return f"{dt.hour % 12 or 12}{mins} {'a.m.' if dt.hour < 12 else 'p.m.'} CT"


def until_words(props):
    end_s = (props or {}).get("ends") or (props or {}).get("expires")
    if not end_s:
        return ""
    try:
        end = datetime.datetime.fromisoformat(end_s)
        if end.tzinfo is None:
            end = end.replace(tzinfo=datetime.timezone.utc)
        return f" until {clock(end)}"
    except Exception:
        return ""


def post_text(props):
    event = str((props or {}).get("event") or "Warning")
    text = f"NWS {event} for {where_words(props)}{until_words(props)}.\n\n{LINK}\n\n{TAGS}"
    if len(text) <= X_LIMIT:
        return text
    return f"NWS {event} for {where_words(props)}{until_words(props)}.\n\n{LINK}"


def nws_urls():
    return [f"{NWS}/alerts/active/zone/{z}" for z in ZONES] + [
        f"{NWS}/alerts/active?point={POINT}"
    ]


def get_json(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/geo+json", "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                break
            if i + 1 < tries:
                time.sleep(3 * (i + 1))
    raise RuntimeError(f"NWS {url}: {last}")


def fetch_alerts():
    """Active alerts from the county, its forecast zones, and the La Porte point, de-duplicated by id."""
    found, errors, seen = [], [], set()
    for url in nws_urls():
        try:
            feats = get_json(url).get("features") or []
        except Exception as e:
            errors.append(str(e)[:300])
            continue
        for f in feats:
            i = alert_id(f)
            if not i or i in seen:
                continue
            seen.add(i)
            found.append(f)
    if errors and not found and not seen:
        raise RuntimeError("NWS didn't answer: " + "; ".join(errors))
    if errors:
        print("NWS warning: " + "; ".join(errors), file=sys.stderr)
    return found


def new_warnings(features, posted, now):
    out = []
    for f in features:
        p = f.get("properties") or {}
        i = alert_id(f)
        if not i or i in posted:
            continue
        if not is_warning(p) or not is_laporte_county(p) or not still_in_effect(p, now):
            continue
        out.append(f)
    # Most urgent first, then by onset, so a tornado goes out before a lesser warning.
    order = ("Tornado Warning", "Extreme Wind Warning", "Flash Flood Warning",
             "Severe Thunderstorm Warning", "Snow Squall Warning")

    def sort_key(f):
        p = f.get("properties") or {}
        ev = p.get("event") or ""
        rank = order.index(ev) if ev in order else len(order)
        return (rank, p.get("onset") or p.get("effective") or "", alert_id(f))

    out.sort(key=sort_key)
    return out


def redacted(msg, key):
    s = str(msg)
    if key:
        s = s.replace(key, "***")
    return s


def gql(key, query, variables=None, retry=True, timeout=60):
    """One GraphQL call. The key goes in a header that's never passed on to a redirect, and never printed."""
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    tries = 3 if retry else 1
    data = None
    for i in range(tries):
        req = urllib.request.Request(BUFFER_API, data=body, method="POST", headers={
            "Content-Type": "application/json", "User-Agent": UA})
        req.add_unredirected_header("Authorization", f"Bearer {key}")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("the answer wasn't a JSON object")
            break
        except urllib.error.HTTPError as e:
            text = redacted(e.read().decode("utf-8", "replace")[:300], key)
            if e.code == 401:
                raise BufferError("Buffer didn't accept the key (401); make a new one and replace the BUFFER_API_KEY secret")
            if e.code == 429:
                raise BufferError("Buffer's API limit was reached (429); it resets on its own")
            if e.code < 500 or i == tries - 1:
                raise BufferError(f"HTTP {e.code}: {text}")
        except Exception as e:
            if i == tries - 1:
                raise BufferError(f"couldn't get an answer from Buffer ({redacted(e, key)[:150]})")
        time.sleep(5 * (i + 1))
    if data.get("errors"):
        raise BufferError("; ".join(redacted((e or {}).get("message", "?"), key) for e in data["errors"])[:300])
    return data.get("data") or {}


def create_x_post(key, text):
    res = gql(key, M_CREATE, {"input": {
        "channelId": BUFFER_X_CHANNEL, "text": text,
        "schedulingType": "automatic", "mode": "shareNow", "assets": [],
    }}, retry=False)["createPost"]
    kind = res.get("__typename")
    if kind != "PostActionSuccess":
        raise BufferError(f"{kind}: {res.get('message') or 'no reason given'}")
    return res["post"]


def run(dry_run=False):
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    if not dry_run and not key:
        print("Not posted: the BUFFER_API_KEY secret isn't set yet (video/README.md has the steps).",
              file=sys.stderr)
        return 2

    now = datetime.datetime.now(CENTRAL)
    path = state_path()
    posted = load_posted(path)
    due = new_warnings(fetch_alerts(), set(posted), now)
    if not due:
        print("No new La Porte County warnings.")
        return 0

    failed = []
    changed = False
    for f in due:
        p = f.get("properties") or {}
        i = alert_id(f)
        text = post_text(p)
        event = p.get("event") or "Warning"
        if dry_run:
            print(f"Would post to X ({i}):\n{text}\n")
            continue
        try:
            post = create_x_post(key, text)
            posted.append(i)
            changed = True
            print(f"Posted to X: {event} (Buffer post {post.get('id')}, {post.get('status')}).")
        except Exception as e:
            failed.append(f"{event}: {redacted(e, key)[:300]}")
            print(f"Couldn't post {event}: {redacted(e, key)[:300]}", file=sys.stderr)

    if changed:
        save_posted(path, posted)
    if dry_run:
        print(f"{len(due)} La Porte County warning(s) would be posted (dry run; nothing sent).")
        return 0
    if failed:
        print(f"{len(failed)} warning(s) did not post.", file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Post new La Porte County NWS Warnings to X through Buffer.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and print what would be posted; send nothing and don't save.")
    args = parser.parse_args(argv)
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
