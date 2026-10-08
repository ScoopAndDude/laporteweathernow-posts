#!/usr/bin/env python3
"""Posts the Daily Video (scripts/daily_video.py) as a Reel on the La Porte Weather Now Facebook Page
and its Instagram account, through Meta's own free Graph API (the Reels Publishing API for the Page,
the Instagram API with Facebook Login's resumable Reels upload for Instagram). Added Oct. 8, 2026.

It needs one repository secret, META_TOKEN: an access token for Scoop's Meta app with the permissions
pages_show_list, pages_read_engagement, pages_manage_posts, instagram_basic and instagram_content_publish.
Either a Page token or a user/system-user token works; with a user token, the Page is found by name
("La Porte Weather Now"), or set the META_PAGE_ID secret. Without META_TOKEN nothing is posted and the
video still goes to the "video" branch. Setup steps: video/README.md.

Safety, every morning:
- Posts only today's video, made in the last 2 hours, and once per platform per day.
- Checks NWS alerts for La Porte County again right before posting: if a short-fused warning is in effect,
  or an alert came or went since the video was made, it doesn't post (the video would be out of date).
- video/config.json turns Facebook or Instagram off without touching the code.
- The token is only ever sent to graph.facebook.com and rupload.facebook.com, in headers, never printed.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily_video as dv  # noqa: E402
import nws_snapshot as ns  # noqa: E402

GRAPH = "https://graph.facebook.com"
PAGE_NAME = "la porte weather now"
MAX_AGE = datetime.timedelta(hours=2)


class MetaError(RuntimeError):
    pass


def call(method, url, token, params=None, body=None, headers=None, timeout=180):
    """One request to Meta. The token goes in the Authorization header, never in the URL."""
    h = {"Authorization": f"OAuth {token}", "User-Agent": ns.UA}
    h.update(headers or {})
    data = None
    if params and method == "GET":
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    elif params:
        data = urllib.parse.urlencode(params).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    if body is not None:
        data = body
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(raw).get("error") or {}
            msg = f"{err.get('message')} (code {err.get('code')}{', ' + str(err.get('error_subcode')) if err.get('error_subcode') else ''})"
        except Exception:
            msg = raw[:300]
        raise MetaError(f"Meta answered {e.code}: {msg}") from None
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": raw[:300]}


def accounts(token, v):
    """The Page (id, name, its token) and the Instagram account connected to it."""
    me = call("GET", f"{GRAPH}/{v}/me", token, {"fields": "id,name"})
    want = os.environ.get("META_PAGE_ID", "").strip()
    try:
        page = call("GET", f"{GRAPH}/{v}/{me['id']}", token, {"fields": "id,name,category,instagram_business_account"})
    except MetaError:
        page = {}
    if page.get("category"):                         # the token is a Page token
        return page["id"], page.get("name"), token, (page.get("instagram_business_account") or {}).get("id"), token
    pages = call("GET", f"{GRAPH}/{v}/me/accounts", token,
                 {"fields": "id,name,access_token,instagram_business_account", "limit": 100}).get("data") or []
    pick = next((p for p in pages if want and p.get("id") == want), None) or \
        next((p for p in pages if (p.get("name") or "").strip().lower() == PAGE_NAME), None)
    if not pick:
        raise MetaError(f"the token can't see the La Porte Weather Now Page (it sees {len(pages)} Page(s)); set META_PAGE_ID")
    return pick["id"], pick.get("name"), pick["access_token"], (pick.get("instagram_business_account") or {}).get("id"), token


def post_instagram(path, caption, ig_id, token, v, cover_ms=1000):
    size = os.path.getsize(path)
    box = call("POST", f"{GRAPH}/{v}/{ig_id}/media", token,
               {"media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": "true",
                "thumb_offset": str(cover_ms)})
    cid = box.get("id")
    uri = box.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{v}/{cid}"
    if not cid:
        raise MetaError(f"Instagram didn't make an upload box: {box}")
    with open(path, "rb") as fh:
        res = call("POST", uri, token, body=fh.read(), headers={"offset": "0", "file_size": str(size),
                                                                  "Content-Type": "application/octet-stream"}, timeout=600)
    if not res.get("success", True) and "debug_info" in res:
        raise MetaError(f"Instagram upload failed: {res.get('debug_info')}")
    status = ""
    for _ in range(72):                                # up to 6 minutes for Instagram to process it
        st = call("GET", f"{GRAPH}/{v}/{cid}", token, {"fields": "status_code,status"})
        status = st.get("status_code") or ""
        if status in ("FINISHED", "PUBLISHED"):
            break
        if status in ("ERROR", "EXPIRED"):
            raise MetaError(f"Instagram couldn't process the video: {st.get('status')}")
        time.sleep(5)
    else:
        raise MetaError(f"Instagram was still processing after 6 minutes ({status})")
    pub = call("POST", f"{GRAPH}/{v}/{ig_id}/media_publish", token, {"creation_id": cid})
    mid = pub.get("id")
    link = None
    try:
        link = call("GET", f"{GRAPH}/{v}/{mid}", token, {"fields": "permalink"}).get("permalink")
    except MetaError:
        pass
    return {"id": mid, "permalink": link}


def post_facebook(path, caption, page_id, page_token, v):
    size = os.path.getsize(path)
    start = call("POST", f"{GRAPH}/{v}/{page_id}/video_reels", page_token, {"upload_phase": "start"})
    vid = start.get("video_id")
    if not vid:
        raise MetaError(f"Facebook didn't start the upload: {start}")
    url = start.get("upload_url") or f"https://rupload.facebook.com/video-upload/{v}/{vid}"
    with open(path, "rb") as fh:
        res = call("POST", url, page_token, body=fh.read(), headers={"offset": "0", "file_size": str(size),
                                                                       "Content-Type": "application/octet-stream"}, timeout=600)
    if res.get("success") is False:
        raise MetaError(f"Facebook upload failed: {res}")
    fin = call("POST", f"{GRAPH}/{v}/{page_id}/video_reels", page_token,
               {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": caption})
    if not fin.get("success", True):
        raise MetaError(f"Facebook didn't publish it: {fin}")
    link = None
    for _ in range(24):                                # up to 2 minutes for the link
        try:
            st = call("GET", f"{GRAPH}/{v}/{vid}", page_token, {"fields": "status,permalink_url"})
            phase = ((st.get("status") or {}).get("publishing_phase") or {}).get("status")
            link = st.get("permalink_url")
            if phase in ("complete", None) and link:
                break
            if ((st.get("status") or {}).get("video_status")) == "error":
                raise MetaError(f"Facebook couldn't process the video: {st.get('status')}")
        except MetaError:
            raise
        except Exception:
            pass
        time.sleep(5)
    if link and link.startswith("/"):
        link = "https://www.facebook.com" + link
    return {"id": vid, "permalink": link}


def still_true(record, now):
    """Is the video still right? Today's, recent, and no alert has come or gone since it was made."""
    if record.get("date") != now.date().isoformat():
        return False, "the video isn't today's"
    try:
        made = datetime.datetime.fromisoformat(record.get("planned"))
        if now - made > MAX_AGE:
            return False, f"the video is {int((now - made).total_seconds() // 60)} minutes old"
    except Exception:
        return False, "the video has no time on it"
    try:
        alerts = dv.active_alerts(ns.county_alerts(), now)
    except Exception as e:
        return False, f"NWS alerts couldn't be checked ({str(e)[:120]})"
    short = [a["event"] for a in alerts if any(k in a["event"] for k in dv.SHORT_FUSED)]
    if short:
        return False, f"{', '.join(short)} in effect for La Porte County"
    if sorted(a["event"] for a in alerts) != sorted(a["event"] for a in record.get("alerts") or []):
        return False, "NWS alerts for La Porte County changed since the video was made"
    return True, ""


def post(outdir, dry_run=False):
    rec_path = os.path.join(outdir, "video.json")
    record = dv.load_json(rec_path, {}) or {}
    plan = dv.load_json(os.path.join(outdir, "plan.json"), {}) or {}
    record.setdefault("posted", {})
    record.setdefault("errors", [])
    cfg = dv.config()
    v = cfg.get("graphVersion", "v25.0")
    want = [k for k in ("facebook", "instagram") if (cfg.get("post") or {}).get(k)]
    token = os.environ.get("META_TOKEN", "").strip()
    now = dv.bs.now_local()
    todo = [k for k in want if not (record["posted"].get(k) or {}).get("id")]
    if not token:
        record["postNote"] = "Not posted: the META_TOKEN secret isn't set yet (video/README.md has the steps)."
        print(record["postNote"])
        dv.save_json(rec_path, record)
        return 0
    if not todo:
        print("Already posted today on " + ", ".join(want) + ".")
        return 0
    ok, why = still_true(plan, now)
    if not ok:
        record["postNote"] = f"Not posted: {why}."
        print(record["postNote"])
        dv.save_json(rec_path, record)
        return 0
    path = os.path.join(outdir, plan["video"])
    caption = plan["caption"]
    page_id, page_name, page_token, ig_id, user_token = accounts(token, v)
    print(f"Posting to {page_name} (Facebook){' and its Instagram' if ig_id else ''}.")
    if dry_run:
        print("Dry run: nothing posted.")
        return 0
    failed = []
    for k in todo:
        try:
            if k == "instagram":
                if not ig_id:
                    raise MetaError("no Instagram account is connected to the Page")
                res = post_instagram(path, caption, ig_id, user_token, v)
            else:
                res = post_facebook(path, caption, page_id, page_token, v)
            res["at"] = dv.bs.now_local().isoformat()
            record["posted"][k] = res
            print(f"Posted on {k}: {res.get('permalink') or res.get('id')}")
        except Exception as e:
            msg = f"{k}: {str(e)[:300]}"
            record["errors"].append({"at": dv.bs.now_local().isoformat(), "error": msg})
            print(f"!! Couldn't post on {msg}", file=sys.stderr)
            failed.append(k)
        dv.save_json(rec_path, record)
    record["postNote"] = "Posted." if not failed else f"Not posted on {', '.join(failed)} (see errors)."
    dv.save_json(rec_path, record)
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        sys.exit(post(sys.argv[1], dry_run="--dry-run" in sys.argv))
    print(__doc__)
