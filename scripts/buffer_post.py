#!/usr/bin/env python3
"""Sends the Daily Video (scripts/daily_video.py) to TikTok and X through Buffer, the same morning it goes to
the Facebook Page and Instagram (scripts/video_post.py) and to YouTube (tools/video/youtube-upload.gs).
Added Oct. 12, 2026 (Scoop: "LPWN on autopilot").

It needs one repository secret, BUFFER_API_KEY: an API key from Buffer (publish.buffer.com/settings/api;
Buffer's Free plan includes one, good for 3,000 requests a month, and this uses about 30 a day at most). Without it
nothing is posted here and the video still goes everywhere else. The TikTok account (@laporteweathernow) and
the X account (@ScoopAndDude) are already connected in Buffer; video/config.json names them ("buffer") and
turns either one off ("post": "tiktok", "x"). Setup steps: video/README.md.

  python3 scripts/buffer_post.py DIR --sha SHA [--dry-run]
      DIR is the "video" branch as it stands (video.json, plan.json and the MP4), SHA its commit: Buffer
      fetches exactly that video from raw.githubusercontent.com. What it posted goes into DIR/video.json
      ("posted": "tiktok", "x"; "bufferNote"). DIR/video.json is only rewritten when something changed.
  python3 scripts/buffer_post.py --check
      Tests the key: which TikTok and X accounts it reaches. Posts nothing.

Same safety rules as Facebook and Instagram:
- Only today's video, made in the last 2 hours, and once per platform per day. Before posting it also asks
  Buffer whether today's video is already on that account, so a re-run (or a "force" run) never posts twice.
- Checks NWS alerts for La Porte County again right before posting: no post if a short-fused warning is in
  effect, or if an alert came or went since the video was made.
- At most two tries per platform per day.
- The key is only ever sent to api.buffer.com, in a header, and never printed.
"""
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily_video as dv  # noqa: E402
import video_post as vp  # noqa: E402

API = "https://api.buffer.com"
RAW = "https://raw.githubusercontent.com/{repo}/{sha}/{name}"
REPO = os.environ.get("GITHUB_REPOSITORY") or "ScoopAndDude/laporteweathernow-posts"
UA = "LaPorteWeatherNow/1.0 (+https://laporteweathernow.com)"
SERVICE = {"tiktok": "tiktok", "x": "twitter"}         # our name -> Buffer's name for the service
NAMES = {"tiktok": "TikTok", "x": "X"}
DEFAULT_ACCOUNTS = {"tiktok": "laporteweathernow", "x": "ScoopAndDude"}
TIKTOK_LIMIT = 2200                                     # TikTok caption with a video (Buffer's limit)
X_LIMIT = 280                                           # X's weighted count (Premium allows more; 280 reads best)
X_TAGS = "#LaPorte #INwx"
ALERT_PREFIX = "Official alerts for La Porte County:"
MAX_TRIES = 2
WAIT_SECONDS = 300                                      # how long to watch for "sent" after posting
POLL_SECONDS = 30
THUMB_MS = 1000                                         # cover frame, same as Instagram's

Q_ORGS = "query Orgs { account { organizations { id name } } }"
Q_CHANNELS = """query Channels($org: OrganizationId!) {
  channels(input: {organizationId: $org}) { id service name displayName isDisconnected isLocked }
}"""
Q_TODAY = """query Today($input: PostsInput!) {
  posts(first: 20, input: $input) { edges { node { id status text externalLink createdAt } } }
}"""
Q_POST = """query OnePost($id: PostId!) {
  post(input: {id: $id}) { id status sentAt externalLink error { message } }
}"""
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


# ---------- Buffer's API ----------

def gql(key, query, variables=None, retry=True, timeout=60):
    """One GraphQL call. Read-only calls are retried on network trouble; posting is never retried here.
    Any trouble comes back as BufferError. The key goes in a header that's never passed on to a redirect."""
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    tries = 3 if retry else 1
    for i in range(tries):
        req = urllib.request.Request(API, data=body, method="POST", headers={
            "Content-Type": "application/json", "User-Agent": UA})
        req.add_unredirected_header("Authorization", f"Bearer {key}")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("the answer wasn't a JSON object")
            break
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:300]
            if e.code == 401:
                raise BufferError("Buffer didn't accept the key (401); make a new one and replace the BUFFER_API_KEY secret")
            if e.code == 429:
                raise BufferError("Buffer's API limit was reached (429); it resets on its own")
            if e.code < 500 or i == tries - 1:
                raise BufferError(f"HTTP {e.code}: {text}")
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, ValueError) as e:
            if i == tries - 1:
                raise BufferError(f"couldn't get an answer from Buffer ({str(e)[:150]})")
        time.sleep(5 * (i + 1))
    if data.get("errors"):
        raise BufferError("; ".join(str((e or {}).get("message", "?")) for e in data["errors"])[:300])
    return data.get("data") or {}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def account_names(cfg):
    names = dict(DEFAULT_ACCOUNTS)
    names.update((cfg.get("buffer") or {}).get("accounts") or {})
    return names


def find_accounts(key, cfg):
    """The Buffer channel to use for each platform: by service, and by the account name in video/config.json."""
    names = account_names(cfg)
    found = []
    for org in ((gql(key, Q_ORGS).get("account") or {}).get("organizations") or []):
        for c in (gql(key, Q_CHANNELS, {"org": org["id"]}).get("channels") or []):
            c["organizationId"] = org["id"]
            found.append(c)
    out = {}
    for k, service in SERVICE.items():
        # Only the account named in video/config.json: never some other account that happens to be connected.
        want = norm(names.get(k))
        named = [c for c in found if c.get("service") == service and want
                 and want in (norm(c.get("name")), norm(c.get("displayName")))]
        out[k] = named[0] if named else None
    return out


def already_there(key, channel, header, now):
    """Today's video already on this account (sent, sending or waiting)? Then don't post it again."""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    data = gql(key, Q_TODAY, {"input": {"organizationId": channel["organizationId"], "filter": {
        "channelIds": [channel["id"]], "status": ["sent", "sending", "scheduled"],
        "createdAt": {"start": start.isoformat()}}}})
    for edge in ((data.get("posts") or {}).get("edges") or []):
        p = (edge or {}).get("node") or {}
        if (p.get("text") or "").startswith(header) and p.get("status") in ("sent", "sending", "scheduled"):
            return p
    return None


def create(key, channel, text, video_url):
    res = gql(key, M_CREATE, {"input": {
        "channelId": channel["id"], "text": text, "schedulingType": "automatic", "mode": "shareNow",
        "assets": [{"video": {"url": video_url, "metadata": {"thumbnailOffset": THUMB_MS}}}],
    }}, retry=False)["createPost"]
    kind = res.get("__typename")
    if kind != "PostActionSuccess":
        raise BufferError(f"{kind}: {res.get('message') or 'no reason given'}")
    return res["post"]


def watch(key, posts):
    """Waits (a few minutes at most) until Buffer says each new post went out or failed."""
    deadline = time.time() + WAIT_SECONDS
    while True:
        open_ = [k for k, p in posts.items() if p.get("status") not in ("sent", "error")]
        if not open_ or time.time() > deadline:
            return posts
        time.sleep(POLL_SECONDS)
        for k in open_:
            try:
                posts[k] = gql(key, Q_POST, {"id": posts[k]["id"]})["post"] or posts[k]
            except Exception as e:
                print(f"(Couldn't check the {NAMES[k]} post yet: {str(e)[:200]})", file=sys.stderr)


# ---------- The words ----------

def x_weight(text):
    """X's weighted length: a link (or a bare domain like laporteweathernow.com) counts 23, most characters 1,
    emoji and other wide characters 2."""
    t = re.sub(r"https?://\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:com|org|net|gov|us|io|edu)\b(?:/\S*)?", "\x00", text)
    n = 0
    for ch in t:
        o = ord(ch)
        if ch == "\x00":
            n += 23
        elif o <= 4351 or 8192 <= o <= 8205 or 8208 <= o <= 8223 or 8242 <= o <= 8247:
            n += 1
        else:
            n += 2
    return n


def period_lines(plan):
    """The caption's lines for each forecast period (Today, Tonight...), built exactly as daily_video.caption does."""
    out = []
    for s in plan.get("scenes") or []:
        if s.get("kind") != "period":
            continue
        bit = dv.bs.end_sentence(f"{dv.upper_first(s['title'].lower())}: {s['sentence']}") + \
            f" {dv.upper_first(s['tempLabel'].lower())} {s['temp']}."
        if s.get("note"):
            bit += f" {dv.bs.end_sentence(s['note'])}"
        out.append(bit)
    return out


def x_text(plan):
    """The X version: the header, any official alerts, today and tonight, the link. Under 280 (weighted),
    dropping the least important lines first and never cutting an alert line in the middle."""
    lines = (plan.get("caption") or "").split("\n")
    header = lines[0]
    alert = next((l for l in lines if l.startswith(ALERT_PREFIX)), None)
    periods = [p for p in period_lines(plan) if p in lines][:2]
    link = "Free forecast every morning: laporteweathernow.com"
    tries = [
        [header, alert, *periods, link, X_TAGS],
        [header, alert, *periods, link],
        [header, alert, *periods[:1], link],
        [header, alert, link],
        [header, alert and "Official alerts are in effect for La Porte County.", link],
    ]
    for t in tries:
        text = "\n".join(x for x in t if x)
        if x_weight(text) <= X_LIMIT:
            return text
    return "\n".join([header, link])


def tiktok_text(plan):
    """TikTok gets the same caption as Facebook and Instagram, trimmed (least important lines first) if it's
    ever over TikTok's 2,200 characters."""
    caption = plan.get("caption") or ""
    if len(caption) <= TIKTOK_LIMIT:
        return caption
    lines = caption.split("\n")
    for drop in ("No hype.", "Today's Daily Scoop:"):
        lines = [l for l in lines if not l.startswith(drop)]
        if len("\n".join(lines)) <= TIKTOK_LIMIT:
            return "\n".join(lines)
    return "\n".join(lines)[:TIKTOK_LIMIT - 1].rsplit(" ", 1)[0] + "…"


def text_for(k, plan):
    return tiktok_text(plan) if k == "tiktok" else x_text(plan)


# ---------- The morning run ----------

def reachable(url, size, tries=6):
    """Is the video on raw.githubusercontent.com yet, whole? (Buffer fetches it from there.)"""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status == 200 and int(r.headers.get("Content-Length") or -1) == size:
                    return True
        except Exception:
            pass
        time.sleep(10)
    return False


def save_if_changed(path, before, record):
    if json.dumps(record, sort_keys=True) != before:
        dv.save_json(path, record)


def note(record, text):
    record["bufferNote"] = text
    print(text)


def log_error(record, k, msg):
    who = NAMES.get(k, k)
    record["errors"].append({"at": dv.bs.now_local().isoformat(), "error": f"{who} (Buffer): {str(msg)[:300]}"})


def settle(record, k, p, failed):
    """Puts what Buffer now says about a post into the record. A post Buffer couldn't publish comes off the
    record (so a later run may try once more, two tries a day at most)."""
    rec = record["posted"][k]
    rec["status"] = p.get("status") or rec.get("status")
    rec["permalink"] = p.get("externalLink") or rec.get("permalink")
    if rec["status"] == "error":
        msg = (p.get("error") or {}).get("message") or "no reason given"
        log_error(record, k, msg)
        print(f"!! {NAMES[k]} didn't take it: {msg}", file=sys.stderr)
        del record["posted"][k]
        failed.append(k)
    else:
        print(f"{NAMES[k]}: {rec['status']}{(' ' + rec['permalink']) if rec.get('permalink') else ''}")


def finish(record, want, failed, rec_path, before):
    failed = [k for k in dict.fromkeys(failed) if not (record["posted"].get(k) or {}).get("id")]
    done = [k for k in want if (record["posted"].get(k) or {}).get("id")]
    sent = [NAMES[k] for k in done if record["posted"][k].get("status") == "sent"]
    waiting = [NAMES[k] for k in done if record["posted"][k].get("status") != "sent"]
    bits = []
    if failed:
        bits.append(f"Not posted on {' or '.join(NAMES[k] for k in failed)} (see errors).")
    if sent:
        bits.append(f"Posted on {' and '.join(sent)}.")
    if waiting:
        bits.append(f"Sent to Buffer for {' and '.join(waiting)}, not confirmed yet (the next run checks).")
    if bits:
        note(record, " ".join(bits))
    save_if_changed(rec_path, before, record)
    return 1 if failed else 0


def run(vdir, sha, dry_run=False, now=None, key=None):
    rec_path = os.path.join(vdir, "video.json")
    record = dv.load_json(rec_path, {}) or {}
    plan = dv.load_json(os.path.join(vdir, "plan.json"), {}) or {}
    before = json.dumps(record, sort_keys=True)
    fixed_now = now is not None
    now = now or dv.bs.now_local()
    today = now.date().isoformat()
    if record.get("date") != today or plan.get("date") != today or not plan.get("video"):
        print("No video from today on the video branch; nothing to send to TikTok or X.")
        return 0
    cfg = dv.config()
    want = [k for k in SERVICE if (cfg.get("post") or {}).get(k)]
    record.setdefault("posted", {})
    record.setdefault("errors", [])
    key = key if key is not None else os.environ.get("BUFFER_API_KEY", "").strip()
    failed = []

    # 1. Posts Buffer hadn't finished last run: did they go out? (A failed one may get its second try below.)
    unsure = [k for k in want if (record["posted"].get(k) or {}).get("via") == "buffer"
              and record["posted"][k].get("status") != "sent"]
    if unsure and key and not dry_run:
        for k in unsure:
            try:
                p = gql(key, Q_POST, {"id": record["posted"][k]["id"]}).get("post") or {}
            except Exception as e:
                print(f"(Couldn't check the {NAMES[k]} post: {str(e)[:200]})", file=sys.stderr)
                continue
            settle(record, k, p, failed)

    # 2. What's left to post today.
    tries = dict(record.get("bufferTries") or {})
    todo = [k for k in want if not (record["posted"].get(k) or {}).get("id") and tries.get(k, 0) < MAX_TRIES]
    if not todo:
        if not want:
            print("Nothing to do: TikTok and X are turned off in video/config.json.")
        elif not unsure:
            print("Nothing to do: " + "; ".join(
                f"{NAMES[k]} {'already posted' if (record['posted'].get(k) or {}).get('id') else 'tried twice'} today"
                for k in want) + ".")
        return finish(record, want, failed, rec_path, before) if unsure else 0
    if not key:
        note(record, "Not posted on TikTok or X: the BUFFER_API_KEY secret isn't set yet (video/README.md has the steps).")
        save_if_changed(rec_path, before, record)
        return 0
    try:
        age = now - dv.dt(plan["planned"])
    except Exception:
        age = None
    if age is None or age > vp.MAX_AGE:
        print("This morning's video is more than 2 hours old now, so TikTok and X wait for tomorrow's.")
        return finish(record, want, failed, rec_path, before) if unsure else 0
    ok, why = vp.still_true(plan, now)
    if not ok:
        note(record, f"Not posted on TikTok or X: {why}.")
        save_if_changed(rec_path, before, record)
        return 0

    # 3. Each run from here counts as a try (two a day at most), saved right away, so a problem that needs Scoop
    #    (a bad key, a disconnected account) fails the morning job at most twice a day, not on every run.
    if not dry_run:
        for k in todo:
            tries[k] = tries.get(k, 0) + 1
        record["bufferTries"] = tries
        save_if_changed(rec_path, before, record)
    video_path = os.path.join(vdir, plan["video"])
    url = RAW.format(repo=REPO, sha=sha, name=plan["video"])
    if not os.path.exists(video_path) or not reachable(url, os.path.getsize(video_path)):
        note(record, "Not posted on TikTok or X: the video isn't on raw.githubusercontent.com yet (a later run tries again).")
        save_if_changed(rec_path, before, record)
        return 1
    header = (plan.get("caption") or "").split("\n")[0]
    try:
        accounts = find_accounts(key, cfg)
    except Exception as e:
        for k in todo:
            log_error(record, k, e)
        note(record, f"Not posted on TikTok or X: {str(e)[:300]}.")
        save_if_changed(rec_path, before, record)
        return 1
    # The alerts once more, right before posting (the checks above can take a few minutes).
    ok, why = vp.still_true(plan, now if fixed_now else dv.bs.now_local())
    if not ok:
        note(record, f"Not posted on TikTok or X: {why}.")
        save_if_changed(rec_path, before, record)
        return 0

    # 4. Post.
    new = {}
    for k in todo:
        ch = accounts.get(k)
        try:
            if not ch:
                raise BufferError(f"no {NAMES[k]} account named {account_names(cfg).get(k)!r} is connected in Buffer "
                                  "(the name is in video/config.json, buffer.accounts)")
            if ch.get("isDisconnected") or ch.get("isLocked"):
                raise BufferError(f"Buffer says the {NAMES[k]} account needs reconnecting")
            there = already_there(key, ch, header, now)
            if there:
                record["posted"][k] = {"id": there["id"], "via": "buffer", "status": there.get("status"),
                                       "permalink": there.get("externalLink"), "at": there.get("createdAt")}
                print(f"Already on {NAMES[k]} today (Buffer post {there['id']}); not posting again.")
                continue
            text = text_for(k, plan)
            if dry_run:
                print(f"Dry run, {NAMES[k]} (@{ch['name'].strip()}), {len(text)} characters:\n{text}\n")
                continue
            post = create(key, ch, text, url)
            new[k] = post
            record["posted"][k] = {"id": post["id"], "via": "buffer", "status": post.get("status"),
                                   "permalink": post.get("externalLink"), "at": dv.bs.now_local().isoformat()}
            print(f"Sent to Buffer for {NAMES[k]}: post {post['id']} ({post.get('status')}).")
        except Exception as e:
            log_error(record, k, e)
            print(f"!! Couldn't post on {NAMES[k]}: {str(e)[:300]}", file=sys.stderr)
            failed.append(k)
        save_if_changed(rec_path, before, record)
    if dry_run:
        print("Dry run: nothing posted.")
        return 0
    for k, p in watch(key, new).items():
        settle(record, k, p, failed)
    return finish(record, want, failed, rec_path, before)


def check():
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    if not key:
        print("The BUFFER_API_KEY secret isn't set yet, so TikTok and X are off (video/README.md has the steps).")
        return 0
    cfg = dv.config()
    accounts = find_accounts(key, cfg)
    bad = 0
    for k in SERVICE:
        ch = accounts.get(k)
        on = (cfg.get("post") or {}).get(k)
        if not ch:
            print(f"{NAMES[k]}: no account connected in Buffer." + ("" if on else " (Turned off in video/config.json.)"))
            bad += 1 if on else 0
        else:
            state = "needs reconnecting in Buffer" if ch.get("isDisconnected") or ch.get("isLocked") else "connected"
            print(f"{NAMES[k]}: @{ch['name'].strip()} ({state}){'' if on else ', turned off in video/config.json'}.")
            bad += 1 if (on and state != "connected") else 0
    print("The key works. Nothing was posted." if not bad else "The key works, but fix the account(s) above.")
    return 1 if bad else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--check"]:
        sys.exit(check())
    if args and not args[0].startswith("--") and "--sha" in args:
        sha = args[args.index("--sha") + 1]
        sys.exit(run(args[0], sha, dry_run="--dry-run" in args))
    print(__doc__)
    sys.exit(2)
