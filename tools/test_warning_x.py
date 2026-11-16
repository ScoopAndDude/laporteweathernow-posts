#!/usr/bin/env python3
"""Tests for posting La Porte County NWS Warnings to X (scripts/warning_x.py).

  python3 tools/test_warning_x.py

No network: filtering, post wording, and the posted-ids file. Nothing is sent to Buffer or NWS.
"""
import datetime
import os
import sys
import tempfile
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import warning_x as wx  # noqa: E402

CENTRAL = ZoneInfo("America/Chicago")
now = datetime.datetime(2026, 11, 16, 12, 0, tzinfo=CENTRAL)
later = (now + datetime.timedelta(hours=2)).isoformat()
past = (now - datetime.timedelta(hours=1)).isoformat()
failed = 0


def check(ok, msg):
    global failed
    if ok:
        print(f"  ok  {msg}")
    else:
        failed += 1
        print(f"  FAIL  {msg}")


def feat(event, ugc=None, same=None, area="", status="Actual", message="Alert",
         ends=None, ident="id-1", affected=None):
    props = {
        "id": ident,
        "event": event,
        "status": status,
        "messageType": message,
        "areaDesc": area,
        "ends": ends if ends is not None else later,
        "geocode": {"UGC": ugc or [], "SAME": same or []},
    }
    if affected:
        props["affectedZones"] = affected
    return {"id": ident, "properties": props}


print("warning_x (no network)")

check(wx.is_warning({"event": "Tornado Warning"}), "Tornado Warning counts")
check(wx.is_warning({"event": "Severe Thunderstorm Warning"}), "Severe Thunderstorm Warning counts")
check(not wx.is_warning({"event": "Tornado Watch"}), "Tornado Watch does not count")
check(not wx.is_warning({"event": "Special Weather Statement"}), "Special Weather Statement does not count")
check(not wx.is_warning({"event": "Winter Weather Advisory"}), "advisory does not count")

check(wx.is_laporte_county({"geocode": {"UGC": ["INC091"], "SAME": []}}), "INC091 is La Porte County")
check(wx.is_laporte_county({"geocode": {"UGC": ["INZ103"], "SAME": []}}), "INZ103 is La Porte County")
check(wx.is_laporte_county({"geocode": {"UGC": ["INZ203"], "SAME": []}}), "INZ203 is La Porte County")
check(wx.is_laporte_county({"geocode": {"UGC": [], "SAME": ["018091"]}}), "SAME 018091 is La Porte County")
check(wx.is_laporte_county({"affectedZones": ["https://api.weather.gov/zones/forecast/INZ103"],
                            "geocode": {"UGC": [], "SAME": []}}),
      "affectedZones INZ103 is La Porte County")
check(not wx.is_laporte_county({"geocode": {"UGC": ["INC127"], "SAME": ["018127"]},
                                "areaDesc": "Porter, IN"}),
      "Porter County only is not posted")
check(not wx.is_laporte_county({"geocode": {"UGC": ["LMZ046"], "SAME": []},
                                "areaDesc": "Lake Michigan"}),
      "a lake-only warning is not posted")
check(wx.is_laporte_county({"geocode": {"UGC": ["INC091", "INC127"], "SAME": ["018091", "018127"]}}),
      "a warning that includes La Porte and a neighbor is posted")

check(wx.still_in_effect({"status": "Actual", "ends": later}, now), "still in effect")
check(not wx.still_in_effect({"status": "Actual", "ends": past}, now), "already ended is skipped")
check(not wx.still_in_effect({"status": "Test", "ends": later}, now), "Test status is skipped")
check(not wx.still_in_effect({"status": "Actual", "messageType": "Cancel", "ends": later}, now),
      "Cancel is skipped")

check(wx.where_words({"geocode": {"UGC": ["INC091"]}, "areaDesc": "La Porte, IN"}) == "LaPorte County",
      "county warning says LaPorte County")
check(wx.where_words({"geocode": {"UGC": ["INZ103"]}, "areaDesc": "Northern La Porte, IN"})
      == "northern LaPorte County",
      "north zone says northern LaPorte County")
check(wx.where_words({"geocode": {"UGC": ["INZ203"]}, "areaDesc": "Southern La Porte, IN"})
      == "southern LaPorte County",
      "south zone says southern LaPorte County")
check("La Porte" not in wx.where_words({"geocode": {"UGC": ["INC091"]}, "areaDesc": "La Porte, IN"}),
      "the two-word town name is not used")

text = wx.post_text({"event": "Tornado Warning", "geocode": {"UGC": ["INC091"]},
                     "areaDesc": "La Porte, IN", "ends": "2026-11-16T20:15:00-06:00"})
check("Tornado Warning" in text, "post names the warning")
check("LaPorte County" in text, "post writes LaPorte as one word")
check("La Porte" not in text, "post does not use the two-word town name")
check("https://laporteweathernow.com/emergency" in text, "post links to the alerts page")
check("#LaPorte" in text and "#INwx" in text, "post has the usual X hashtags")
check("8:15 p.m. CT" in text, f"post has the until time in Central ({text!r})")
check(len(text) <= 280, "post fits in 280 characters")

posted = {"already"}
rows = wx.new_warnings([
    feat("Tornado Watch", ugc=["INC091"], ident="watch"),
    feat("Special Weather Statement", ugc=["INC091"], ident="sps"),
    feat("Tornado Warning", ugc=["INC127"], same=["018127"], area="Porter, IN", ident="porter"),
    feat("Tornado Warning", ugc=["INC091"], ident="already"),
    feat("Tornado Warning", ugc=["INC091"], ident="old", ends=past),
    feat("Severe Thunderstorm Warning", ugc=["INC091"], ident="svr"),
    feat("Tornado Warning", ugc=["INC091"], ident="tor"),
], posted, now)
ids = [wx.alert_id(f) for f in rows]
check(ids == ["tor", "svr"], f"only new in-effect La Porte County warnings, tornado first ({ids})")

with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "posted-alerts.txt")
    check(wx.load_posted(path) == [], "missing file is empty")
    wx.save_posted(path, ["urn:oid:one", "urn:oid:two"])
    check(wx.load_posted(path) == ["urn:oid:one", "urn:oid:two"], "ids round-trip")
    # A comment and a leftover note on the same line are ignored / trimmed.
    with open(path, "a", encoding="utf-8") as f:
        f.write("# ignore me\nurn:oid:three  Tornado Warning\n")
    check(wx.load_posted(path) == ["urn:oid:one", "urn:oid:two", "urn:oid:three"],
          "comments skipped, first token is the id")

print()
if failed:
    print(f"{failed} test(s) failed.")
    sys.exit(1)
print("All tests passed.")
