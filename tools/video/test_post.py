#!/usr/bin/env python3
"""Tests for posting the Daily Video (scripts/video_post.py) with a stand-in for Meta: the La Porte
location tag goes on the Reel, and if Facebook or Instagram turns the tag down, the Reel still posts
without it. Needs no network and no key.

  python3 tools/video/test_post.py
"""
import os
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import video_post as vp  # noqa: E402

FAILS = []
PLACE = {"id": "112342342114259", "name": "La Porte, Indiana"}


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


def fake_meta(refuse_place):
    calls = []

    def call(method, url, token, params=None, body=None, headers=None, timeout=180):
        p = dict(params or {})
        calls.append((method, url, p))
        if url.endswith("/video_reels") and p.get("upload_phase") == "start":
            return {"video_id": "v1", "upload_url": "https://rupload.facebook.com/video-upload/v25.0/v1"}
        if "rupload.facebook.com" in url:
            return {"success": True}
        if url.endswith("/video_reels") and p.get("upload_phase") == "finish":
            if "place" in p and refuse_place:
                raise vp.MetaError("Meta answered 400: Invalid parameter (code 100)")
            return {"success": True}
        if url.endswith("/v1"):
            return {"status": {"publishing_phase": {"status": "complete"}}, "permalink_url": "/reel/1/"}
        if url.endswith("/media"):
            if "location_id" in p and refuse_place:
                raise vp.MetaError("Meta answered 400: INSTAGRAM_PLATFORM_API__INVALID_LOCATION_ID (code 100)")
            return {"id": "c1", "uri": "https://rupload.facebook.com/ig-api-upload/v25.0/c1"}
        if url.endswith("/c1"):
            return {"status_code": "FINISHED"}
        if url.endswith("/media_publish"):
            return {"id": "m1"}
        if url.endswith("/m1"):
            return {"permalink": "https://www.instagram.com/reel/x/"}
        raise AssertionError(f"unexpected call {method} {url}")

    return call, calls


def run():
    real_call = vp.call
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "laporte-test.mp4")
        with open(path, "wb") as fh:
            fh.write(b"\0" * 2048)
        try:
            check(vp.place_tag() == PLACE, f"config names La Porte, Indiana as the place ({vp.place_tag()})")

            vp.call, calls = fake_meta(refuse_place=False)
            res = vp.post_facebook(path, "caption", "123", "tok", "v25.0", place=PLACE)
            fins = [p for _, u, p in calls if p.get("upload_phase") == "finish"]
            check(res["place"] == "La Porte, Indiana" and len(fins) == 1 and fins[0].get("place") == PLACE["id"],
                  "Facebook: the Reel is tagged with La Porte")
            check(res["permalink"] == "https://www.facebook.com/reel/1/", "Facebook: the link comes back")

            vp.call, calls = fake_meta(refuse_place=True)
            res = vp.post_facebook(path, "caption", "123", "tok", "v25.0", place=PLACE)
            fins = [p for _, u, p in calls if p.get("upload_phase") == "finish"]
            check(res["place"] is None and len(fins) == 2 and "place" not in fins[1] and res["id"] == "v1",
                  "Facebook: tag turned down -> posts without it")

            vp.call, calls = fake_meta(refuse_place=False)
            res = vp.post_instagram(path, "caption", "ig1", "tok", "v25.0", place=PLACE)
            boxes = [p for _, u, p in calls if u.endswith("/media")]
            check(res["place"] == "La Porte, Indiana" and boxes[0].get("location_id") == PLACE["id"] and res["id"] == "m1",
                  "Instagram: the Reel is tagged with La Porte")

            vp.call, calls = fake_meta(refuse_place=True)
            res = vp.post_instagram(path, "caption", "ig1", "tok", "v25.0", place=PLACE)
            boxes = [p for _, u, p in calls if u.endswith("/media")]
            check(res["place"] is None and len(boxes) == 2 and "location_id" not in boxes[1] and res["id"] == "m1",
                  "Instagram: tag turned down -> posts without it")

            vp.call, calls = fake_meta(refuse_place=False)
            res = vp.post_facebook(path, "caption", "123", "tok", "v25.0", place=None)
            fins = [p for _, u, p in calls if p.get("upload_phase") == "finish"]
            check(res["place"] is None and "place" not in fins[0], "no place in the config -> no tag")
        finally:
            vp.call = real_call

    print(f"\n{len(FAILS)} failed." if FAILS else "\nALL PASSED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(run())
