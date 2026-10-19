#!/usr/bin/env python3
"""Oct. 19, 2026 batch for Buffer (TikTok, YouTube Shorts, X): the four Myth-Busters from the Reel Kit
plus four new short videos about the site, in the same look (render_reels.py, the Reel Kit renderer).

  python3 batch_oct19.py [name ...]     (no args = all eight)
"""
import os
import re
import sys

import render_reels as R

HERE = os.path.dirname(os.path.abspath(__file__))
R.OUT = os.path.join(HERE, "out")
R.CHECK = os.path.join(HERE, "check")

# Green for GO (Hard Hat Weather's GO / DELAY / STOP)
GREEN = (52, 199, 106)
R.TAG_COLORS["n"] = GREEN
R.TAG = re.compile(r"\[(/?)([oawgrn])\]")

ORANGE, AMBER, RED, WHITE, GRAY, BLACK = R.ORANGE, R.AMBER, R.RED, R.WHITE, R.GRAY, R.BLACK
NO_HYPE = dict(t="text", text="No hype. Just the forecast.", size=48, color=GRAY, font="semi")

NEW = [
    # Is that warning for your town? (the home page's nearest storm warning line, live Oct. 18)
    dict(file="lpwn-reel-6-is-it-for-you", pill="NEW ON THE SITE", particles="rain",
         source="Warnings from the National Weather Service",
         glow=[(0.0, ORANGE), (2.9, AMBER), (5.8, ORANGE)], beats=[
        dict(dur=2.9, rows=[
            dict(t="label", text="YOUR PHONE BUZZED.", size=46, color=GRAY, track=8),
            dict(t="gap", h=44),
            dict(t="big", text="IS THAT WARNING", size=124, fit="q"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]FOR YOUR TOWN?[/o]", size=124, fit="q"),
        ]),
        dict(dur=2.9, rows=[
            dict(t="text", text="Storm warnings are drawn around the storm,", size=72),
            dict(t="gap", h=40),
            dict(t="big", text="[o]NOT WHOLE[/o]", size=170, fit="c"),
            dict(t="gap", h=26),
            dict(t="big", text="[o]COUNTIES.[/o]", size=170, fit="c"),
        ]),
        dict(dur=3.0, rows=[
            dict(t="text", text="Our home page now shows the nearest one:", size=68),
            dict(t="gap", h=40),
            dict(t="big", text="[o]HOW FAR.[/o]", size=190, fit="h"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]WHICH WAY.[/o]", size=190, fit="h"),
            dict(t="gap", h=40),
            dict(t="text", text="And whether it covers your town.", size=62),
        ]),
        dict(dur=2.7, rows=[
            dict(t="text", text="Nothing within 100 miles? It says that too.", size=60),
            dict(t="gap", h=44),
            dict(t="big", text="CHECK YOUR", size=160, fit="t"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]TOWN, FREE.[/o]", size=160, fit="t"),
            dict(t="gap", h=48),
            NO_HYPE,
        ]),
    ]),
    # The 6 AM morning forecast email
    dict(file="lpwn-reel-7-morning-email", pill="FREE EVERY MORNING", particles="sparkle",
         source="Forecast from the National Weather Service", beats=[
        dict(dur=2.8, rows=[
            dict(t="big", text="[o]6 AM.[/o]", size=330),
            dict(t="gap", h=44),
            dict(t="text", text="Your forecast, in your inbox.", size=84),
        ]),
        dict(dur=2.9, rows=[
            dict(t="text", text="Today, tonight and the next 3 days", size=72),
            dict(t="gap", h=40),
            dict(t="big", text="[o]FOR YOUR[/o]", size=180, fit="s"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]OWN SPOT.[/o]", size=180, fit="s"),
        ]),
        dict(dur=2.9, rows=[
            dict(t="text", text="A new warning for your spot?", size=76),
            dict(t="gap", h=40),
            dict(t="big", text="[o]AN EMAIL[/o]", size=180, fit="e"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]RIGHT AWAY.[/o]", size=180, fit="e"),
        ]),
        dict(dur=2.8, rows=[
            dict(t="big", text="FREE.", size=250),
            dict(t="gap", h=36),
            dict(t="text", text="Anywhere in the U.S. Made in La Porte.", size=62),
            dict(t="gap", h=44),
            dict(t="text", text="laporteweathernow.com/morning-email", size=46, color=GRAY, font="semi"),
        ]),
    ]),
    # Hard Hat Weather (job-site calls by 5 AM)
    dict(file="lpwn-reel-8-hard-hat", pill="HARD HAT WEATHER", particles="snow",
         source="Built on National Weather Service forecasts", beats=[
        dict(dur=2.8, rows=[
            dict(t="text", text="Can your crew work today?", size=80),
            dict(t="gap", h=44),
            dict(t="big", text="KNOW BY", size=210, fit="k"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]5 AM.[/o]", size=210, fit="k"),
        ]),
        dict(dur=2.9, rows=[
            dict(t="text", text="Every job site gets a call:", size=76),
            dict(t="gap", h=48),
            dict(t="big", text="[n]GO[/n] [g]·[/g] [a]DELAY[/a] [g]·[/g] [r]STOP[/r]", size=124),
            dict(t="gap", h=48),
            dict(t="text", text="with the workable hours and the reason.", size=64),
        ]),
        dict(dur=2.9, rows=[
            dict(t="text", text="Rain, wind, cold or snow:", size=78),
            dict(t="gap", h=40),
            dict(t="big", text="[o]YOUR TRADE’S[/o]", size=160, fit="l"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]OWN LIMITS.[/o]", size=160, fit="l"),
            dict(t="gap", h=40),
            dict(t="text", text="By text or email, before you roll out.", size=60),
        ]),
        dict(dur=2.8, rows=[
            dict(t="big", text="FREE", size=230),
            dict(t="gap", h=30),
            dict(t="text", text="for one job site.", size=80),
            dict(t="gap", h=44),
            dict(t="text", text="Crew plan $19 a month, with a 7-day free trial.", size=52, color=GRAY, font="semi"),
            dict(t="gap", h=30),
            dict(t="text", text="laporteweathernow.com/hardhat", size=50, color=GRAY, font="semi"),
        ]),
    ]),
    # Free watch & warning alerts on your phone
    dict(file="lpwn-reel-9-free-alerts", pill="FREE ALERTS", particles="rain",
         source="Alerts from the National Weather Service",
         glow=[(0.0, ORANGE), (2.8, RED), (5.7, ORANGE)], beats=[
        dict(dur=2.8, rows=[
            dict(t="text", text="Get the warning", size=84),
            dict(t="gap", h=30),
            dict(t="big", text="[o]ON YOUR[/o]", size=220, fit="p"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]PHONE.[/o]", size=220, fit="p"),
            dict(t="gap", h=44),
            dict(t="text", text="Free. No account. No email address.", size=58, color=GRAY, font="semi"),
        ]),
        dict(dur=2.9, rows=[
            dict(t="text", text="When the Weather Service issues a", size=72),
            dict(t="gap", h=44),
            dict(t="big", text="[a]WATCH[/a] OR [r]WARNING[/r]", size=124),
            dict(t="gap", h=44),
            dict(t="text", text="for your county, it shows up on your phone.", size=64),
        ]),
        dict(dur=2.9, rows=[
            dict(t="text", text="Follow up to", size=80),
            dict(t="gap", h=34),
            dict(t="big", text="[o]5 COUNTIES.[/o]", size=170),
            dict(t="gap", h=44),
            dict(t="text", text="Home, work, family.", size=74),
        ]),
        dict(dur=2.8, rows=[
            dict(t="text", text="On our home page, tap", size=74),
            dict(t="gap", h=34),
            dict(t="big", text="[o]GET FREE[/o]", size=180, fit="g"),
            dict(t="gap", h=24),
            dict(t="big", text="[o]ALERTS.[/o]", size=180, fit="g"),
            dict(t="gap", h=44),
            dict(t="text", text="iPhone: add the site to your Home Screen first.", size=46, color=GRAY, font="semi"),
        ]),
    ]),
]

MYTH = [r for r in R.REELS if r["file"].startswith(("lpwn-reel-1", "lpwn-reel-2", "lpwn-reel-3", "lpwn-reel-4"))]
ALL = MYTH + NEW

if __name__ == "__main__":
    want = sys.argv[1:]
    for reel in ALL:
        if not want or any(w in reel["file"] for w in want):
            R.render_reel(reel)
