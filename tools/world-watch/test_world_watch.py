#!/usr/bin/env python3
"""Tests for scripts/world_watch.py (no network, no API key): the checks, the saving rules, and the
conversation with Claude (pause_turn, a proposal that fails the checks, a nudge), using a fake client.

  python3 tools/world-watch/test_world_watch.py
"""
import copy
import datetime
import json
import os
import shutil
import sys
import tempfile
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import world_watch as ww  # noqa: E402

TODAY = datetime.date(2026, 10, 19)   # a Monday
FAILED = []


def ok(cond, what):
    if not cond:
        FAILED.append(what)
        print("FAIL:", what)


def good_proposal():
    world = ww.load(ww.WORLD)
    amazon = ww.load(ww.AMAZON)
    enso = dict(copy.deepcopy(world["enso"]), changed=True)
    enso["reading"] = "+2.6°C"
    enso["readingNote"] = "above normal in the key Nino-3.4 zone of the Pacific, week of October 12"
    am = {k: copy.deepcopy(amazon[k]) for k in ("headline", "stats", "now", "species")}
    for s in am["species"]:
        s.setdefault("more", [])
    return {"enso": enso, "amazon": am, "summary": "El Nino Advisory, +2.6°C. Amazon: steady week."}


# ---------------------------------------------------------------- checks
p = good_proposal()
ok(ww.check(copy.deepcopy(p), TODAY) == [], "a proposal built from today's files passes: " + str(ww.check(copy.deepcopy(p), TODAY)))

bad = copy.deepcopy(p); bad["amazon"]["stats"] = bad["amazon"]["stats"][:3]
ok(any("exactly 4 tiles" in x for x in ww.check(bad, TODAY)), "3 stats tiles fail")
bad = copy.deepcopy(p); bad["enso"]["points"] = bad["enso"]["points"][:3]
ok(any("exactly 4 sentences" in x for x in ww.check(bad, TODAY)), "3 El Nino points fail")
bad = copy.deepcopy(p); bad["amazon"]["now"][0]["source"]["url"] = "http://example.com/x"
ok(any("https" in x for x in ww.check(bad, TODAY)), "an http link fails")
bad = copy.deepcopy(p); bad["amazon"]["now"][0]["date"] = "2026-10-25"
ok(any("future" in x for x in ww.check(bad, TODAY)), "a news date in the future fails")
bad = copy.deepcopy(p); bad["amazon"]["species"][0]["photo"] = {"url": "https://upload.wikimedia.org/a.jpg", "alt": "a fly",
    "credit": "Someone", "license": "All rights reserved", "licenseUrl": "https://example.com/l", "page": "https://commons.wikimedia.org/x"}
ok(any("license" in x for x in ww.check(bad, TODAY)), "a photo without a free license fails")
good = copy.deepcopy(p); good["amazon"]["species"][0]["photo"] = {"url": "https://upload.wikimedia.org/a.jpg", "alt": "a fly",
    "credit": "Someone", "license": "CC BY-SA 4.0", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
    "page": "https://commons.wikimedia.org/wiki/File:A.jpg"}
ok(ww.check(good, TODAY) == [], "a CC BY-SA photo passes")
bad = copy.deepcopy(p); bad["enso"]["reading"] = "2.6 degrees"
ok(any("reading" in x for x in ww.check(bad, TODAY)), "a reading without degrees C fails")
bad = copy.deepcopy(p); bad["enso"]["nextUpdate"] = "2026-10-01"
ok(any("passed" in x for x in ww.check(bad, TODAY)), "a nextUpdate that has passed fails")
bad = copy.deepcopy(p); bad["amazon"]["species"].append(copy.deepcopy(bad["amazon"]["species"][0])); bad["amazon"]["species"].append(copy.deepcopy(bad["amazon"]["species"][0]))
ok(any("3 to 6" in x for x in ww.check(bad, TODAY)), "7 species fail")
bad = copy.deepcopy(p); bad["amazon"]["now"][1]["text"] = "Fires fell. <img src=x onerror=alert(1)>"
ok(any("no '<'" in x for x in ww.check(bad, TODAY)), "HTML in a text is refused")
bad = copy.deepcopy(p); bad["amazon"]["stats"][2]["source"]["url"] = "javascript:alert(1)"
ok(len(ww.check(bad, TODAY)) >= 1, "a javascript: link is refused")
mixed = copy.deepcopy(p); mixed["amazon"]["now"].reverse()
ok(ww.check(mixed, TODAY) == [] and mixed["amazon"]["now"][0]["date"] == "2026-10-16", "news comes out newest first")

# ---------------------------------------------------------------- due
ok(ww.due(datetime.datetime(2026, 10, 20, 9, 0, tzinfo=ww.CENTRAL)) == "no", "not due on a Tuesday")
ok(ww.due(datetime.datetime(2026, 10, 20, 9, 0, tzinfo=ww.CENTRAL), force=True) == "yes", "force runs any day")
ok(ww.due(datetime.datetime(2026, 10, 26, 8, 45, tzinfo=ww.CENTRAL)) == "yes", "due on the next Monday")
ok(ww.next_monday(TODAY) == datetime.date(2026, 10, 26), "next Monday from a Monday is a week out")
ok(ww.next_monday(datetime.date(2026, 10, 21)) == datetime.date(2026, 10, 26), "next Monday from a Wednesday")

# ---------------------------------------------------------------- saving
tmp = tempfile.mkdtemp()
try:
    wpath, apath = os.path.join(tmp, "world-watch.json"), os.path.join(tmp, "amazon-watch.json")
    shutil.copy(ww.WORLD, wpath); shutil.copy(ww.AMAZON, apath)
    before_world, before_amazon = ww.load(wpath), ww.load(apath)
    prop_path = os.path.join(tmp, "p.json")
    q = good_proposal(); q["_meta"] = {"date": "2026-10-26"}
    ww.save(prop_path, q)
    changed = ww.apply(prop_path, today=datetime.date(2026, 10, 26), world_path=wpath, amazon_path=apath)
    w2, a2 = ww.load(wpath), ww.load(apath)
    ok(changed and os.path.exists(prop_path + ".msg"), "a real change writes the commit message")
    ok(w2["enso"]["reading"] == "+2.6°C" and w2["updated"] == "2026-10-26", "El Nino and its date saved")
    ok(w2["climate"] == before_world["climate"], "climate kept as it was")
    ok(list(w2.keys()) == list(before_world.keys()), "world-watch.json keeps its key order")
    ok(a2["about"] == before_amazon["about"], "about kept as it was")
    ok(a2["updated"] == "2026-10-26" and a2["nextUpdate"] == "2026-11-02", "Amazon dates set by the script")
    ok(list(a2.keys()) == list(before_amazon.keys()), "amazon-watch.json keeps its key order")
    ok(open(wpath, encoding="utf-8").read().endswith("}\n") and "Niño" in open(wpath, encoding="utf-8").read(),
       "files stay plain UTF-8 with a newline at the end")

    # changed=false: world-watch.json isn't touched at all
    shutil.copy(ww.WORLD, wpath)
    raw_before = open(wpath, encoding="utf-8").read()
    q = good_proposal(); q["enso"]["changed"] = False; q["enso"]["reading"] = "+9.9°C"
    ww.save(prop_path, q)
    ww.apply(prop_path, today=datetime.date(2026, 10, 26), world_path=wpath, amazon_path=apath)
    ok(open(wpath, encoding="utf-8").read() == raw_before, "no El Nino change leaves world-watch.json byte for byte")

    # a bad proposal is refused by apply too
    q = good_proposal(); q["amazon"]["stats"] = []
    ww.save(prop_path, q)
    try:
        ww.apply(prop_path, today=TODAY, world_path=wpath, amazon_path=apath)
        ok(False, "apply refuses a proposal that fails the checks")
    except SystemExit:
        pass
finally:
    shutil.rmtree(tmp)


# ---------------------------------------------------------------- the conversation, with a fake Claude
class FakeStream:
    def __init__(self, msg): self.msg = msg
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self): return self.msg


class FakeClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.messages = self

    def stream(self, **kw):
        self.calls.append(copy.deepcopy({k: v for k, v in kw.items() if k != "tools"}) | {"tools": kw["tools"]})
        return FakeStream(self.replies.pop(0))


def usage(i=1000, o=200, s=0, f=0):
    return NS(input_tokens=i, output_tokens=o, cache_creation_input_tokens=0, cache_read_input_tokens=0,
              server_tool_use=NS(web_search_requests=s, web_fetch_requests=f))


def save_block(inp, bid="toolu_1"):
    return NS(type="tool_use", id=bid, name="save_world_watch", input=inp)


three_tiles = good_proposal(); three_tiles["amazon"]["stats"] = three_tiles["amazon"]["stats"][:3]
replies = [
    NS(stop_reason="pause_turn", content=[NS(type="text", text="Searching...")], usage=usage(s=4, f=2)),
    NS(stop_reason="tool_use", content=[save_block(three_tiles)], usage=usage(o=3000)),
    NS(stop_reason="tool_use", content=[save_block(good_proposal(), "toolu_2")], usage=usage(o=3000)),
]
fake = FakeClient(replies)
logs = []
prop, total, notes = ww.ask_claude(fake, TODAY, ww.load(ww.WORLD), ww.load(ww.AMAZON), log=logs.append)
ok(len(fake.calls) == 3, "three requests: paused, fixed, saved")
first = fake.calls[0]["messages"][0]["content"]
ok(ww.NOAA_ENSO in first and ww.IRI_ENSO in first, "the NOAA and IRI links are in the user message (so web_fetch may fetch them)")
ok(fake.calls[1]["messages"][-1]["role"] == "assistant", "after pause_turn the paused turn is sent back as-is")
last = fake.calls[2]["messages"][-1]
ok(last["role"] == "user" and all(c["type"] == "tool_result" and c["is_error"] for c in last["content"]),
   "a proposal that fails goes back as an error tool_result only")
ok("exactly 4 tiles" in last["content"][0]["content"], "Claude is told what to fix")
ok(prop["enso"]["reading"] == "+2.6°C", "the fixed proposal is the one returned")
ok(total["search"] == 4 and total["fetch"] == 2, "searches and fetches are counted")
names = [t.get("name") for t in fake.calls[0]["tools"]]
ok(names == ["web_search", "web_fetch", "save_world_watch"], "tools: web search, web fetch, save")
ok(fake.calls[0]["tools"][1]["blocked_domains"] == ["terrabrasilis.dpi.inpe.br"], "INPE's data service can't be fetched")
ok(fake.calls[0]["model"] == "claude-opus-5-5", "Claude Opus 5.5")

# ends its turn without saving: one nudge, then it saves
fake = FakeClient([NS(stop_reason="end_turn", content=[NS(type="text", text="Done.")], usage=usage()),
                   NS(stop_reason="tool_use", content=[save_block(good_proposal())], usage=usage())])
prop, total, notes = ww.ask_claude(fake, TODAY, ww.load(ww.WORLD), ww.load(ww.AMAZON), log=logs.append)
ok(fake.calls[1]["messages"][-1] == {"role": "user", "content": "Please call save_world_watch now with the full update."},
   "a turn that ends without saving gets one nudge")

# keeps failing: refused after MAX_FIXES
fake = FakeClient([NS(stop_reason="tool_use", content=[save_block(three_tiles, f"t{i}")], usage=usage()) for i in range(5)])
try:
    ww.ask_claude(fake, TODAY, ww.load(ww.WORLD), ww.load(ww.AMAZON), log=logs.append)
    ok(False, "a proposal that keeps failing is refused")
except RuntimeError as e:
    ok("didn't pass" in str(e) and len(fake.calls) == ww.MAX_FIXES + 1, "refused after the allowed fixes")

# runaway cost: stopped
fake = FakeClient([NS(stop_reason="pause_turn", content=[], usage=usage(i=3_000_000)) for _ in range(3)])
try:
    ww.ask_claude(fake, TODAY, ww.load(ww.WORLD), ww.load(ww.AMAZON), log=logs.append)
    ok(False, "a run that costs too much is stopped")
except RuntimeError as e:
    ok("Stopped" in str(e), "a run past the cost cap stops")

# the strict schema is valid as far as the API's rules go: no unsupported keywords
def walk(node, path="schema"):
    if isinstance(node, dict):
        for bad_kw in ("maxItems", "minLength", "maxLength", "minimum", "maximum", "pattern"):
            ok(bad_kw not in node, f"{path} has no {bad_kw}")
        if node.get("type") == "object":
            ok(node.get("additionalProperties") is False, f"{path} sets additionalProperties false")
        if "minItems" in node:
            ok(node["minItems"] in (0, 1), f"{path} minItems is 0 or 1")
        for k, v in node.items():
            walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]")
walk(ww.SAVE_TOOL["input_schema"])

print("ALL PASSED" if not FAILED else f"{len(FAILED)} FAILED")
sys.exit(1 if FAILED else 0)
