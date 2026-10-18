#!/usr/bin/env python3
"""Tests for the no-AI Daily Scoop writer (scripts/scoop_writer.py). No network needed.

Three saved mornings (tools/scoop-writer/fixtures/, trimmed copies of what the 5 a.m. snapshot,
scoop-posts.json, scorecard.json and scoop-updates.json held at 5:31 a.m.):
  2026-10-14  a stormy week: rain early, storms Thursday, WPC's flooding-rain risk, a changed forecast
  2026-10-16  a Wind Advisory for La Porte County and next door, showers and storms, gusts to 40 mph
  2026-10-18  a Frost Advisory until 8 a.m., then a dry, sunny week

  python3 tools/scoop-writer/test_writer.py
"""
import copy
import datetime
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import backup_scoop as bs  # noqa: E402
import scoop_writer as sw  # noqa: E402

FAILED = []
KEYS = ["type", "date", "posted", "updated", "title", "summary", "body", "sources", "author", "forecasts", "corrections"]


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        FAILED.append(what)


def fixture(day):
    with open(os.path.join(HERE, "fixtures", f"{day}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def make(f, **changes):
    snap = copy.deepcopy(f["snapshot"])
    for k, v in changes.items():
        snap[k] = v
    now = sw.parse(f["now"]).astimezone(sw.TZ)
    return sw.build_post(snap, f["posts"], f["scorecard"], f["updates"], now)


def common(day, made, f):
    post = made["post"]
    text = " ".join([post["title"], post["summary"]] + post["body"])
    check(list(post.keys()) == KEYS, f"{day}: same keys, same order as every Daily Scoop")
    check("auto" not in post, f"{day}: never marked automatic (that's the NWS backup)")
    check(post["date"] == day and post["posted"] == post["updated"], f"{day}: dated today, posted = updated")
    check(len(post["body"]) == 4, f"{day}: four paragraphs ({len(post['body'])})")
    check(made["words"] <= sw.WORD_MAX, f"{day}: {made['words']} words, at most {sw.WORD_MAX}")
    check(len(post["title"]) <= 92, f"{day}: title fits ({len(post['title'])} characters): {post['title']}")
    check(post["summary"].endswith("."), f"{day}: the summary is one finished sentence")
    check(not re.search(r"\bNone\b|\bnull\b|\{|\}|  |\.\.(?!\.)| ,|\(\)", text), f"{day}: no leftovers (None, braces, double spaces or periods)")
    check(not re.search(r"\b(EDT|EST)\b", " ".join(post["body"])), f"{day}: no Eastern times in the text")
    check(not re.search(r"\b(AI|artificial)\b", text), f"{day}: says nothing about AI")
    check(post["body"][3].startswith("Right now"), f"{day}: paragraph 4 starts 'Right now'")
    check(post["sources"][0]["url"] == sw.FORECAST_URL and post["sources"][0]["label"] == "NWS forecast for La Porte, IN",
          f"{day}: the NWS forecast for La Porte is the first source")
    # The Track Record grades these: our blend's high and low, NWS's rain chance, for tomorrow and the day after.
    today = datetime.date.fromisoformat(day)
    sug = {s["date"]: s for s in f["snapshot"]["consensus"]["suggested"]}
    want = [(today + datetime.timedelta(days=i)).isoformat() for i in (1, 2)]
    check([x["date"] for x in post["forecasts"]] == want, f"{day}: forecasts for tomorrow and the day after")
    for x in post["forecasts"]:
        check(x["high"] == sug[x["date"]]["high"] and x["low"] == sug[x["date"]]["low"],
              f"{day}: {x['date']} high and low are the blend's ({x['high']}, {x['low']})")
    # Rain: NWS's, the higher of the day and the night after it, rounded the way NWS's wording rounds.
    periods = f["snapshot"]["forecast"]["periods"]
    for x in post["forecasts"]:
        d = datetime.date.fromisoformat(x["date"])
        day_p = [p for p in periods if p["isDaytime"] and sw.local(p["start"]).date() == d]
        night_p = [p for p in periods if not p["isDaytime"] and sw.night_of(p) == d]
        rain = max([bs.nws_chance(p.get("rainChancePercent")) or 0 for p in day_p + night_p] or [0])
        check(x["rain"] == rain, f"{day}: {x['date']} rain chance is NWS's ({x['rain']}%)")
    # Every temperature in paragraph 1 is one NWS or the La Porte airport gave.
    allowed = {str(p.get("temperatureF")) for p in periods} | {str((f["snapshot"].get("observation") or {}).get("temperatureF"))}
    temps = re.findall(r"(?:high near|low around|:\s[a-z ]*and)\s(\d+)", post["body"][0])
    check(all(t in allowed for t in temps), f"{day}: paragraph 1's temperatures come from NWS and the airport {temps}")
    return post


def run():
    # ---- Oct. 14: rain early, storms Thursday, WPC risk, what changed ----
    f = fixture("2026-10-14")
    made = make(f)
    post = common("2026-10-14", made, f)
    p1, p2, p3, p4 = post["body"]
    check(p1.startswith("An early shower is possible"), "Oct. 14: the bottom line says the rain is early")
    check("before 10 a.m." in p1, "Oct. 14: NWS's own timing, in the site's style")
    check("Thursday" in p2 and "80%" in p2, "Oct. 14: paragraph 2 has Thursday night's 80%")
    check("our blend of NWS and four computer models says 64, 46 and 63" in p2,
          "Oct. 14: says where our numbers differ from NWS's, and that they're the blend's")
    check(any(s["url"] == sw.OPEN_METEO["url"] for s in post["sources"]), "Oct. 14: credits Open-Meteo when the blend is mentioned")
    check(p3.startswith("What changed in NWS's forecast since yesterday's Scoop: Friday's chance of rain is now 80% (from 30%)"),
          "Oct. 14: the biggest change first, with the old number")
    check('key messages this morning: "A cold front' in p3, "Oct. 14: NWS forecasters' own key message, quoted")
    check("Yesterday we said a high of 82 and a 70% chance of rain; the La Porte airport got 84 and stayed dry." in p3,
          "Oct. 14: owns yesterday's missed rain call")
    check("marginal (at least 5%) risk of flooding rain from 7 a.m. Thursday to 7 a.m. Friday" in p4,
          "Oct. 14: WPC's flooding-rain risk, in Central time")
    check(any("discussion (we used the 3:29 AM EDT Oct. 14 issue" in s["label"] for s in post["sources"]),
          "Oct. 14: names the discussion issue it used")
    check(post["title"].startswith("Early storms, then mostly cloudy near 66; storms likely Thursday"), "Oct. 14: title")

    # ---- Oct. 16: Wind Advisory ----
    f = fixture("2026-10-16")
    made = make(f)
    post = common("2026-10-16", made, f)
    p1, p2, p3, p4 = post["body"]
    check(p1.startswith("NWS has a Wind Advisory for La Porte County from 1 to 10 p.m. today."), "Oct. 16: leads with the advisory, Central times")
    check("Secure anything loose outside" in p1, "Oct. 16: one practical tip for the advisory")
    check("gusts as high as 35 mph" in p1, "Oct. 16: keeps the wind when it matters")
    check(p4.startswith("Right now NWS has a Wind Advisory for La Porte County from 1 to 10 p.m. today."),
          "Oct. 16: paragraph 4 passes the advisory along")
    check("Next door, NWS Chicago has a Wind Advisory for Porter County" in p4, "Oct. 16: Porter County's advisory next door")
    check("NWS has since issued a Wind Advisory" in p3, "Oct. 16: what changed starts with the new advisory")
    check("Wind Advisory" in post["title"] and "Wind Advisory" in post["summary"], "Oct. 16: the advisory is in the title and summary")
    # The same morning without the advisory: no alert words anywhere.
    calm = make(f, alertsLaPorteCounty=[], alertsNearby={"indiana": [], "nearbyCountiesFullText": []})
    t = " ".join([calm["post"]["title"], calm["post"]["summary"]] + calm["post"]["body"])
    check("Advisory" not in t and "no watches, warnings or advisories for La Porte County or for Porter and Lake counties" in t,
          "Oct. 16 without alerts: says there are none, and names no advisory")
    # A tornado warning leads, with NWS's instructions.
    tw = copy.deepcopy(f["snapshot"]["alertsLaPorteCounty"][0])
    tw.update({"event": "Tornado Warning", "id": "tw-1", "onset": "2026-10-16T06:20:00-04:00", "ends": "2026-10-16T07:00:00-04:00",
               "expires": "2026-10-16T07:00:00-04:00"})
    warned = make(f, alertsLaPorteCounty=[tw] + f["snapshot"]["alertsLaPorteCounty"])
    check(warned["post"]["body"][0].startswith("NWS has a Tornado Warning for La Porte County until 6 a.m. today. "
                                               "If you're in the warned area, follow NWS's instructions now."),
          "a Tornado Warning leads paragraph 1, with NWS's instructions")
    check("NWS also has a Wind Advisory" in warned["post"]["body"][0], "a second alert is named in paragraph 1 too")

    # ---- Oct. 18: Frost Advisory, dry week ----
    f = fixture("2026-10-18")
    made = make(f)
    post = common("2026-10-18", made, f)
    p1, p2, p3, p4 = post["body"]
    check(post["title"] == "Frost Advisory until 8 a.m., then sunny near 62; dry all week, highs near 71 by Thursday", "Oct. 18: title")
    check(p1.startswith("NWS has a Frost Advisory for La Porte County until 8 a.m. today. Cover or bring in tender plants."),
          "Oct. 18: leads with the Frost Advisory")
    check(p2.startswith("Sunny and dry Monday through Friday, highs 66 to 71."), "Oct. 18: the dry stretch in one line")
    check("For yesterday, our Oct. 15 Scoop said a high of 56; the La Porte airport got 57." in p3,
          "Oct. 18: grades yesterday against the Scoop that made the forecast")
    check("What changed" not in p3 and any("baseline" in n for n in made["notes"]),
          "Oct. 18: no 'what changed' when yesterday's post was the automatic backup")
    check("SPC shows no thunderstorm or severe risk here through Tuesday" in p4, "Oct. 18: SPC through day 3")
    # Missing sources are left out, never guessed.
    no_models = make(f, consensus=None)
    check(not any(s["url"] == sw.OPEN_METEO["url"] for s in no_models["post"]["sources"]) and
          all(x["high"] is not None for x in no_models["post"]["forecasts"]),
          "without the models: NWS's own numbers, and no Open-Meteo credit")
    no_spc = make(f, spc=[])
    check("SPC" not in no_spc["post"]["body"][3], "without SPC's outlooks: says nothing about SPC")
    no_afd = make(f, discussion=None)
    check("key messages" not in no_afd["post"]["body"][2] and not any("discussion" in s["label"] for s in no_afd["post"]["sources"]),
          "without the discussion: no key messages and no discussion source")
    stale_afd = copy.deepcopy(f["snapshot"]["discussion"])
    stale_afd["issued"] = "2026-10-16T09:00:00-05:00"
    check("key messages" not in make(f, discussion=stale_afd)["post"]["body"][2], "a discussion over 18 hours old is left out")
    check(sw.eastern_times_to_central("Gusts to 45 mph after 2 PM EDT, ending by 11 PM.") ==
          "Gusts to 45 mph after 1 p.m. Central, ending by 10 p.m. Central.", "the discussion's Eastern times become Central")

    # ---- insert: never twice, and it replaces the automatic backup ----
    tmp = tempfile.mkdtemp()
    posts_path, post_path = os.path.join(tmp, "scoop-posts.json"), os.path.join(tmp, "post.json")
    real = bs.POSTS
    try:
        bs.POSTS = posts_path
        backup = {"type": "daily", "date": post["date"], "posted": "2026-10-18T06:32:00-05:00", "title": "Automatic NWS update: x",
                  "body": ["x"], "forecasts": [], "auto": True}
        older = {"type": "daily", "date": "2026-10-17", "posted": "2026-10-17T05:40:00-05:00", "title": "y", "body": ["y"], "forecasts": []}
        with open(posts_path, "w", encoding="utf-8") as fh:
            json.dump({"about": "test", "posts": [backup, older]}, fh)
        with open(post_path, "w", encoding="utf-8") as fh:
            json.dump(post, fh)
        check(sw.cmd_insert(post_path) == 0, "insert: runs")
        got = json.load(open(posts_path, encoding="utf-8"))["posts"]
        check(got[0]["title"] == post["title"] and not got[0].get("auto") and len(got) == 2 and got[1]["date"] == "2026-10-17",
              "insert: replaces today's automatic backup, keeps the rest")
        sw.cmd_insert(post_path)
        check(len(json.load(open(posts_path, encoding="utf-8"))["posts"]) == 2, "insert: never posts twice")
        with open(post_path, "w", encoding="utf-8") as fh:
            json.dump(dict(post, auto=True), fh)
        check(sw.cmd_insert(post_path) == 1, "insert: refuses a post marked automatic")
    finally:
        bs.POSTS = real

    print()
    print("ALL PASSED" if not FAILED else f"{len(FAILED)} FAILED")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(run())
