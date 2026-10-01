#!/usr/bin/env python3
"""Saves this week's official average gas and diesel prices for laporteweathernow.com/camp-map (The Chase).

Reads the U.S. Energy Information Administration's weekly "Gasoline and Diesel Fuel Update"
(www.eia.gov/petroleum/gasdiesel), the federal government's free, official survey of retail fuel
prices, and writes fuel-prices.json: regular gasoline and on-highway diesel for the U.S., the five
fuel regions (PADDs) and their East Coast subregions, the nine states EIA lists on its own
(CA, CO, FL, MA, MN, NY, OH, TX, WA), and ten cities. No key needed.

EIA publishes on Mondays' prices, usually on Tuesday afternoon. The file is only rewritten when the
numbers change, so its history shows every week. If EIA doesn't answer or the page looks wrong,
the file is left alone and the site keeps showing the last saved week (with its date).
"""
import datetime
import html.parser
import json
import os
import re
import sys
import urllib.request

URL = "https://www.eia.gov/petroleum/gasdiesel/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fuel-prices.json")

REGIONS = {
    "U.S.": "US", "East Coast (PADD1)": "PADD1", "New England (PADD1A)": "PADD1A",
    "Central Atlantic (PADD1B)": "PADD1B", "Lower Atlantic (PADD1C)": "PADD1C", "Midwest (PADD2)": "PADD2",
    "Gulf Coast (PADD3)": "PADD3", "Rocky Mountain (PADD4)": "PADD4", "West Coast (PADD5)": "PADD5",
    "West Coast less California": "PADD5XCA",
}
STATES = {"California": "CA", "Colorado": "CO", "Florida": "FL", "Massachusetts": "MA", "Minnesota": "MN",
          "New York": "NY", "Ohio": "OH", "Texas": "TX", "Washington": "WA"}


class Tables(html.parser.HTMLParser):
    """Every <table> on the page as {caption, rows: [[cell text, ...], ...]}."""

    def __init__(self):
        super().__init__()
        self.tables, self.stack, self.cell, self.in_caption = [], [], None, False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.stack.append({"caption": "", "rows": []})
        elif not self.stack:
            return
        elif tag == "caption":
            self.in_caption = True
        elif tag == "tr":
            self.stack[-1]["rows"].append([])
        elif tag in ("td", "th"):
            self.cell = []

    def handle_endtag(self, tag):
        if not self.stack:
            return
        if tag == "table":
            self.tables.append(self.stack.pop())
        elif tag == "caption":
            self.in_caption = False
        elif tag in ("td", "th") and self.cell is not None:
            if self.stack[-1]["rows"]:
                self.stack[-1]["rows"][-1].append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None

    def handle_data(self, data):
        if not self.stack:
            return
        if self.in_caption:
            self.stack[-1]["caption"] += data
        if self.cell is not None:
            self.cell.append(data)


def number(s):
    try:
        return round(float(s.replace(",", "")), 3)
    except (ValueError, AttributeError):
        return None


def read_table(t, names):
    """{key: {price, weekAgo}} plus the date of the newest week, from one EIA table."""
    out, cities, week, in_cities = {}, {}, None, False
    for row in t["rows"]:
        if not row:
            continue
        dates = [c for c in row if re.fullmatch(r"\d{2}/\d{2}/\d{2}", c)]
        if len(dates) >= 2:
            week = dates[-1]
            continue
        label = row[0]
        if label == "Cities":
            in_cities = True
            continue
        vals = [number(c) for c in row[1:4]]
        if len(vals) < 3 or vals[2] is None:
            continue
        item = {"price": vals[2], "weekAgo": vals[1]}
        if in_cities:
            cities[label] = item
        elif label in names:
            out[names[label]] = item
    return out, cities, week


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "laporteweathernow.com (The Chase fuel prices; contact laporteweathernow@gmail.com)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            page = r.read().decode("utf-8", "replace")
    except Exception as e:  # EIA down: keep the last saved week
        print("Couldn't reach EIA:", e)
        return 1
    p = Tables()
    p.feed(page)
    regular, diesel, cities, week = {}, {}, {}, None
    for t in p.tables:
        cap = t["caption"].lower()
        if "regular gasoline" in cap:
            got, _, w = read_table(t, REGIONS)
            regular.update(got)
            week = w or week
        elif cap.strip().startswith("states"):
            got, c, _ = read_table(t, STATES)
            regular.update(got)
            cities.update(c)
        elif "diesel" in cap:
            got, _, _ = read_table(t, dict(REGIONS, California="CA"))
            diesel.update(got)
    us = regular.get("US", {}).get("price")
    if not week or not us or not 1 < us < 15 or len(regular) < 12 or len(diesel) < 8:
        print("EIA's page didn't look right; leaving the file alone.", week, us, len(regular), len(diesel))
        return 1
    m, d, y = week.split("/")
    out = {
        "about": "Official weekly average retail fuel prices from the U.S. Energy Information Administration, saved for laporteweathernow.com/camp-map (scripts/fuel_prices.py).",
        "source": "U.S. Energy Information Administration (EIA), Gasoline and Diesel Fuel Update",
        "sourceUrl": URL,
        "week": f"20{y}-{m}-{d}",
        "regular": regular,
        "diesel": diesel,
        "regularCities": cities,
    }
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
        old.pop("fetched", None)
        if old == out:
            print("No new prices. Week of", out["week"])
            return 0
    except (OSError, ValueError):
        pass
    out["fetched"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, OUT)
    print("Saved prices for the week of", out["week"], "- U.S. regular", us)
    return 0


if __name__ == "__main__":
    sys.exit(main())
