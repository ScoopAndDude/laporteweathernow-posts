#!/usr/bin/env python3
"""Tests for sending the Daily Video to TikTok and X through Buffer (scripts/buffer_post.py).

  python3 tools/video/test_buffer.py

Checks the X version stays under 280 (X's weighted count) and keeps official alerts whole, that TikTok gets
the same caption as Facebook and Instagram, and the morning run's rules: nothing without today's video,
nothing without the key, nothing twice. Needs no network.
"""
import copy
import datetime
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)
import buffer_post as bp  # noqa: E402
import daily_video as dv  # noqa: E402
import test_plan as tp  # noqa: E402

FAILS = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


class FakeBuffer:
    """Answers the few calls buffer_post.py makes, like Buffer's API would."""

    def __init__(self, fail=None, existing=None, slow=False, rename=None, broken=False):
        self.fail = dict(fail or {})        # channel id -> how many times it reports an error
        self.existing = existing            # a post already there today, starting with this text
        self.slow = slow                    # posts stay "sending" until finish()
        self.rename = rename or {}          # channel id -> another account name
        self.broken = broken                # answers with nulls where data should be
        self.created = []
        self.posts = {}

    def finish(self, fail=None):
        self.slow = False
        for p in self.posts.values():
            failing = fail and p["channel"] == fail
            p.update(status="error" if failing else "sent", externalLink=None if failing else "https://example/" + p["id"],
                     error={"message": "TikTok couldn't process the video"} if failing else None)

    def gql(self, key, query, variables=None, retry=True, timeout=60):
        v = variables or {}
        if self.broken:
            return {"account": None, "channels": None, "posts": None, "createPost": None, "post": None}
        if query == bp.Q_ORGS:
            return {"account": {"organizations": [{"id": "org1", "name": "My organization"}]}}
        if query == bp.Q_CHANNELS:
            chans = [
                {"id": "ch-tt", "service": "tiktok", "name": "laporteweathernow", "displayName": "laporteweathernow", "isDisconnected": False, "isLocked": False},
                {"id": "ch-yt", "service": "youtube", "name": "LaPorteWeatherNow ", "displayName": "LaPorteWeatherNow ", "isDisconnected": False, "isLocked": False},
                {"id": "ch-x", "service": "twitter", "name": "ScoopAndDude", "displayName": "ScoopAndDude", "isDisconnected": False, "isLocked": False}]
            for c in chans:
                if c["id"] in self.rename:
                    c["name"] = c["displayName"] = self.rename[c["id"]]
            return {"channels": chans}
        if query == bp.Q_TODAY:
            ch = v["input"]["filter"]["channelIds"][0]
            edges = [{"node": {"id": "old-" + ch, "status": "sent", "text": self.existing + "\nmore", "externalLink": None,
                               "createdAt": "2026-10-09T11:05:00Z"}}] if self.existing else []
            return {"posts": {"edges": edges}}
        if query == bp.M_CREATE:
            inp = v["input"]
            self.created.append(inp)
            pid = "p-" + ("x" if inp["channelId"] == "ch-x" else "tt") + str(len(self.created))
            failing = self.fail.get(inp["channelId"], 0) > 0
            if failing:
                self.fail[inp["channelId"]] -= 1
            self.posts[pid] = {"id": pid, "channel": inp["channelId"], "status": "error" if failing else "sent", "sentAt": None,
                               "externalLink": None if failing else ("https://x.example/p-x" if inp["channelId"] == "ch-x" else "https://tiktok.example/" + pid),
                               "error": {"message": "TikTok couldn't process the video"} if failing else None}
            if self.slow:
                self.posts[pid].update(status="sending", externalLink=None, error=None)
            return {"createPost": {"__typename": "PostActionSuccess", "post": {"id": pid, "status": "sending", "externalLink": None, "error": None}}}
        if query == bp.Q_POST:
            return {"post": self.posts[v["id"]]}
        raise AssertionError("unexpected call")


def video_dir(plan, posted=None):
    d = tempfile.mkdtemp()
    plan = dict(plan, video="laporte-2026-10-09.mp4")
    record = {"date": plan["date"], "planned": plan["planned"], "video": plan["video"], "caption": plan["caption"],
              "alerts": plan.get("alerts"), "posted": posted or {}, "errors": []}
    with open(os.path.join(d, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(d, "video.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2)
    return d


def read(d):
    with open(os.path.join(d, "video.json"), encoding="utf-8") as fh:
        return json.load(fh)


def run():
    # X's weighted count.
    check(bp.x_weight("abc") == 3, "x_weight: plain letters count 1")
    check(bp.x_weight("See laporteweathernow.com") == 4 + 23, "x_weight: a bare domain counts 23, like X's links")
    check(bp.x_weight("Read https://laporteweathernow.com/daily-scoop now") == 5 + 23 + 4, "x_weight: a full link counts 23")
    check(bp.x_weight("84° — a.m.") == len("84° — a.m."), "x_weight: degree sign, dash and a.m. count 1 each")
    check(bp.x_weight("⛈") == 2, "x_weight: emoji count 2")

    # A nice day.
    nice = tp.plan_for(tp.data(tp.periods()))
    x = bp.x_text(nice)
    lines = nice["caption"].split("\n")
    check(bp.x_weight(x) <= 280, f"nice day: X version is {bp.x_weight(x)} (280 or less)")
    check(x.startswith(lines[0]), "nice day: X version starts with the same line as the caption (finds re-posts)")
    check(all(p in x for p in bp.period_lines(nice)[:2]), "nice day: X version has today and tonight, word for word")
    check("laporteweathernow.com" in x, "nice day: X version has the link")
    check(bp.tiktok_text(nice) == nice["caption"], "nice day: TikTok gets the same caption as Facebook and Instagram")

    # Alerts: kept whole, and first.
    alert = {"id": "x1", "event": "Freeze Warning", "area": "Northern La Porte; Southern La Porte", "messageType": "Alert",
             "severity": "Moderate", "onset": "2026-10-09T23:00:00-05:00", "ends": "2026-10-10T09:00:00-05:00",
             "expires": "2026-10-09T15:00:00-05:00"}
    wind = dict(alert, id="x2", event="Wind Advisory", onset="2026-10-09T10:00:00-05:00", ends="2026-10-09T19:00:00-05:00")
    cold = tp.plan_for(tp.data(tp.periods(tonight=("Clear", 28, 0)), alerts=[alert, wind]))
    x = bp.x_text(cold)
    alert_line = next(l for l in cold["caption"].split("\n") if l.startswith(bp.ALERT_PREFIX))
    check(bp.x_weight(x) <= 280, f"alerts: X version is {bp.x_weight(x)} (280 or less)")
    check(alert_line in x, f"alerts: the official alert line is there, whole ({alert_line})")
    check(x.index(alert_line) < x.index("laporteweathernow.com"), "alerts: the alert comes before the link")

    # A very long alert day: never cut mid-alert; falls back to a plain line.
    many = [dict(alert, id=f"m{i}", event=e) for i, e in enumerate(
        ["Winter Storm Warning", "Wind Chill Advisory", "Lakeshore Flood Warning", "Special Weather Statement",
         "Hazardous Weather Outlook", "Gale Warning", "Freezing Fog Advisory", "Winter Weather Advisory"])]
    long_plan = tp.plan_for(tp.data(tp.periods(tonight=("Snow", 25, 90)), alerts=many))
    x = bp.x_text(long_plan)
    check(bp.x_weight(x) <= 280, f"long alerts: X version is {bp.x_weight(x)} (280 or less)")
    long_line = next((l for l in long_plan["caption"].split("\n") if l.startswith(bp.ALERT_PREFIX)), "")
    check((long_line in x) or ("Official alerts are in effect for La Porte County." in x),
          "long alerts: the alert line is whole, or replaced by a plain 'alerts are in effect' line")

    # TikTok's 2,200 limit.
    big = copy.deepcopy(nice)
    big["caption"] = big["caption"].replace("No hype. Just the forecast.", "No hype. " + "x" * 2300)
    check(len(bp.tiktok_text(big)) <= bp.TIKTOK_LIMIT, "TikTok: a too-long caption is trimmed under 2,200")

    # The morning run's rules (no network: each case stops before Buffer or NWS would be asked).
    now = dv.dt(nice["planned"]).astimezone(dv.TZ) + datetime.timedelta(minutes=5)
    d = video_dir(nice)
    yesterday = now - datetime.timedelta(days=1)
    before = open(os.path.join(d, "video.json"), encoding="utf-8").read()
    check(bp.run(d, "abc123", now=yesterday, key="k") == 0, "run: not today's video -> nothing to do")
    check(open(os.path.join(d, "video.json"), encoding="utf-8").read() == before, "run: and video.json is untouched")

    d = video_dir(nice)
    check(bp.run(d, "abc123", now=now, key="") == 0, "run: no key -> no post, and the job doesn't fail")
    check("BUFFER_API_KEY" in (read(d).get("bufferNote") or ""), f"run: no key -> says so in video.json ({read(d).get('bufferNote')})")
    snap = open(os.path.join(d, "video.json"), encoding="utf-8").read()
    bp.run(d, "abc123", now=now, key="")
    check(open(os.path.join(d, "video.json"), encoding="utf-8").read() == snap, "run: same note again -> file not rewritten (no extra commit)")

    d = video_dir(nice, posted={"tiktok": {"id": "t1", "via": "buffer", "status": "sent"},
                                "x": {"id": "x1", "via": "buffer", "status": "sent"}})
    check(bp.run(d, "abc123", now=now, key="k") == 0, "run: TikTok and X already posted today -> nothing to do")
    check(read(d)["posted"]["tiktok"]["id"] == "t1", "run: and the record stays as it was")

    d = video_dir(nice)
    rec = read(d)
    rec["bufferTries"] = {"tiktok": 2, "x": 2}
    with open(os.path.join(d, "video.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    check(bp.run(d, "abc123", now=now, key="k") == 0, "run: two tries already today -> stops trying")

    cfg = dv.config()
    check(all((cfg.get("post") or {}).get(k) is not None for k in ("tiktok", "x")), "video/config.json has TikTok and X switches")

    # The posting itself, with a stand-in for Buffer (no network).
    fake = FakeBuffer()
    real = (bp.gql, bp.reachable, bp.vp.still_true, bp.POLL_SECONDS)
    bp.gql, bp.reachable, bp.vp.still_true, bp.POLL_SECONDS = fake.gql, (lambda url, size: True), (lambda p, n: (True, "")), 0
    try:
        d = video_dir(nice)
        open(os.path.join(d, "laporte-2026-10-09.mp4"), "wb").write(b"0" * 10)
        check(bp.run(d, "abc123", now=now, key="k") == 0, "post: TikTok and X both go out")
        r = read(d)
        check(r["posted"]["tiktok"]["status"] == "sent" and r["posted"]["x"]["status"] == "sent", "post: Buffer says both were sent")
        check(r["posted"]["x"]["permalink"] == "https://x.example/p-x", "post: the link to each post is kept")
        check(r.get("bufferNote") == "Posted on TikTok and X.", f"post: note says so ({r.get('bufferNote')})")
        made = {c["channelId"]: c for c in fake.created}
        check(made["ch-tt"]["text"] == nice["caption"], "post: TikTok got the full caption")
        check(bp.x_weight(made["ch-x"]["text"]) <= 280, "post: X got the short version")
        check(made["ch-x"]["mode"] == "shareNow" and made["ch-x"]["schedulingType"] == "automatic", "post: posted now, automatically")
        check(made["ch-tt"]["assets"][0]["video"]["url"].endswith("/abc123/laporte-2026-10-09.mp4"),
              "post: Buffer fetches the video from this exact commit")
        n = len(fake.created)
        bp.run(d, "abc123", now=now, key="k")
        check(len(fake.created) == n, "post: a second run the same morning posts nothing")

        # TikTok turns it down once: the next run tries once more, then stops.
        fake = FakeBuffer(fail={"ch-tt": 1})
        bp.gql = fake.gql
        d = video_dir(nice)
        open(os.path.join(d, "laporte-2026-10-09.mp4"), "wb").write(b"0" * 10)
        check(bp.run(d, "abc123", now=now, key="k") == 1, "error: TikTok fails -> the run says so (exit 1)")
        r = read(d)
        check("tiktok" not in r["posted"] and r["posted"]["x"]["status"] == "sent", "error: X still posted, TikTok not marked posted")
        check(any("TikTok (Buffer)" in e["error"] for e in r["errors"]), "error: the reason is in video.json")
        check(bp.run(d, "abc123", now=now, key="k") == 0 and read(d)["posted"]["tiktok"]["status"] == "sent",
              "error: the 6:45 run tries TikTok once more and it goes out")
        check(sum(1 for c in fake.created if c["channelId"] == "ch-x") == 1, "error: X wasn't posted twice")

        # Already on Buffer today (say a 'force' run made a new video): don't post again.
        fake = FakeBuffer(existing=nice["caption"].split("\n")[0])
        bp.gql = fake.gql
        d = video_dir(nice)
        open(os.path.join(d, "laporte-2026-10-09.mp4"), "wb").write(b"0" * 10)
        bp.run(d, "abc123", now=now, key="k")
        check(not fake.created and read(d)["posted"]["tiktok"]["id"] == "old-ch-tt", "re-run: today's video already on Buffer -> not posted again")

        # Buffer still busy when the watch ends: not called posted yet; the next run checks and finds it went out.
        fake = FakeBuffer(slow=True)
        bp.gql = fake.gql
        d = video_dir(nice)
        open(os.path.join(d, "laporte-2026-10-09.mp4"), "wb").write(b"0" * 10)
        real_wait, bp.WAIT_SECONDS = bp.WAIT_SECONDS, 0
        bp.run(d, "abc123", now=now, key="k")
        bp.WAIT_SECONDS = real_wait
        check("not confirmed yet" in (read(d).get("bufferNote") or ""), f"slow: says not confirmed yet ({read(d).get('bufferNote')})")
        fake.finish()
        n = len(fake.created)
        check(bp.run(d, "abc123", now=now, key="k") == 0 and read(d)["posted"]["tiktok"]["status"] == "sent"
              and read(d).get("bufferNote") == "Posted on TikTok and X.", "slow: the next run confirms both went out")
        check(len(fake.created) == n, "slow: and posts nothing new")

        # Buffer still busy, then it fails: the next run sees that and gives TikTok its second try.
        fake = FakeBuffer(slow=True)
        bp.gql = fake.gql
        d = video_dir(nice)
        open(os.path.join(d, "laporte-2026-10-09.mp4"), "wb").write(b"0" * 10)
        bp.WAIT_SECONDS = 0
        bp.run(d, "abc123", now=now, key="k")
        bp.WAIT_SECONDS = real_wait
        fake.finish(fail="ch-tt")
        check(bp.run(d, "abc123", now=now, key="k") == 0 and read(d)["posted"]["tiktok"]["status"] == "sent",
              "slow then failed: the next run notices and TikTok gets its second try")
        check(sum(1 for c in fake.created if c["channelId"] == "ch-tt") == 2 and
              sum(1 for c in fake.created if c["channelId"] == "ch-x") == 1, "slow then failed: X still posted only once")

        # Too late in the day: no try, no note, no commit.
        d = video_dir(nice)
        before = open(os.path.join(d, "video.json"), encoding="utf-8").read()
        fake = FakeBuffer()
        bp.gql = fake.gql
        check(bp.run(d, "abc123", now=now + datetime.timedelta(hours=5), key="k") == 0 and not fake.created,
              "late: 5 hours after the video, nothing is posted")
        check(open(os.path.join(d, "video.json"), encoding="utf-8").read() == before, "late: and video.json is untouched (no commit)")

        # The account named in config isn't there: never post to some other account instead.
        fake = FakeBuffer(rename={"ch-x": "SomeoneElse"})
        bp.gql = fake.gql
        d = video_dir(nice)
        open(os.path.join(d, "laporte-2026-10-09.mp4"), "wb").write(b"0" * 10)
        check(bp.run(d, "abc123", now=now, key="k") == 1, "wrong account: the run says so")
        check(all(c["channelId"] != "ch-x" for c in fake.created) and "x" not in read(d)["posted"],
              "wrong account: nothing went to the other X account")

        # A strange answer from Buffer: logged, counted as a try, no crash.
        fake = FakeBuffer(broken=True)
        bp.gql = fake.gql
        d = video_dir(nice)
        open(os.path.join(d, "laporte-2026-10-09.mp4"), "wb").write(b"0" * 10)
        check(bp.run(d, "abc123", now=now, key="k") == 1, "strange answer: the run says so instead of crashing")
        check(read(d).get("bufferTries") == {"tiktok": 1, "x": 1}, "strange answer: counted as a try")
    finally:
        bp.gql, bp.reachable, bp.vp.still_true, bp.POLL_SECONDS = real

    print(f"\n{len(FAILS)} failed." if FAILS else "\nALL PASSED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(run())
