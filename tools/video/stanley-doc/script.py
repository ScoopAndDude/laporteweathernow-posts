#!/usr/bin/env python3
"""The Stanley Hotel documentary's script: every narration line and the pictures shown with it.

    python3 tools/video/stanley-doc/script.py        writes script.json (what doc.py and the voice job read)

Facts (checked Oct. 25, 2026; sources in the YouTube description): Wikipedia's articles on the Stanley Hotel,
F.O. Stanley, Estes Park and The Shining (novel), with the 1911 newspaper accounts they cite (the AP story in
the York Dispatch, June 26, 1911; the Fort Collins Express, June 29, 1911); the Colorado Springs Gazette and
the Denver Gazette (ghost stories, and the hotel's own history); Far Out magazine (Room 237); KUNC (the film
center, Aug. 2026). Stephen King's stay is told the way he told it. The hotel's own stories are called the
hotel's stories, and ghost stories are called what guests say; none of them is presented as proven.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def two(n):
    if n < 20:
        return ONES[n]
    return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")


def year_words(y):
    if 2000 <= y < 2010:
        return "two thousand" + (" " + ONES[y % 10] if y % 10 else "")
    hi, lo = divmod(y, 100)
    if lo == 0:
        return two(hi) + " hundred"
    if lo < 10:
        return two(hi) + " oh " + ONES[lo]
    return two(hi) + " " + two(lo)


# words the narrator says differently from how the captions spell them
SAY_AS = [
    (r"\bRoom 217\b", "Room two-seventeen"), (r"\bRoom 237\b", "Room two-thirty-seven"), (r"\b217\b", "two-seventeen"),
    (r"\b237\b", "two-thirty-seven"), (r"\b127\b", "a hundred and twenty-seven"),
]


def spoken(s):
    """How the narrator should say it: years and decades in words (the captions keep the numerals)."""
    for pat, rep in SAY_AS:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\b(1[89])(\d)0s\b", lambda m: two(int(m.group(1))) + " " + TENS[int(m.group(2))][:-1] + "ies", s)
    return re.sub(r"\b(1[89]\d\d|20[0-2]\d)\b", lambda m: year_words(int(m.group(1))), s)


# ---------------------------------------------------------------------------------------------- picture helpers
def P(file, fit="cover", tone="sepia", z=None, f0=None, f1=None, crop=None, **kw):
    d = {"type": "photo", "file": file, "fit": fit, "tone": tone}
    if z:
        d["z"] = z
    if f0:
        d["f0"] = f0
    if f1:
        d["f1"] = f1
    if crop:
        d["crop"] = crop
    d.update(kw)
    return d


def NEWS(file, mode="zoom", **kw):
    return dict(type="news", file=file, mode=mode, **kw)


def MAP(**kw):
    return dict(type="map", **kw)


def BIG(text, cap=None, file=None, **kw):
    d = dict(type="big", text=text, **kw)
    if cap:
        d["cap"] = cap
    if file:
        d["file"] = file
    return d


def QUOTE(text, by=None, **kw):
    return dict(type="quote", text=text, **({"by": by} if by else {}), **kw)


def TYPED(head, rows, **kw):
    return dict(type="typed", head=head, rows=rows, **kw)


def L(lid, say=None, v=None, **kw):
    d = {"id": lid}
    if say:
        d["say"] = say
        sp = spoken(say)
        if sp != say:
            d["tts"] = sp
    if v is not None:
        d["v"] = v
    d.update(kw)
    return d


SAME = {"same": True}


def TODO(desc):
    """A stand-in until the right picture is chosen."""
    return QUOTE(desc, "picture to come", size=48)


# ---------------------------------------------------------------------------------------------- the chapters
CHAPTERS = [
    # ------------------------------------------------------------------ cold open
    dict(id="open", music="ballroom", tail=0.2, lines=[
        L("o01", "On October 30th, 1974, the night before Halloween, a young writer and his wife checked into an old hotel in the Colorado Rockies.",
          P("stanley-search-02.jpg", tone="night", z=[1.0, 1.16], f0=[0.55, 0.62], f1=[0.56, 0.56]), lower="Estes Park, Colorado | October 30, 1974",
          sfx=[["creak", 6.0]]),
        L("o02", "It was about to close for the winter. As he told it later, they were the only guests in the place.",
          dict(type="corridor", z=[1.0, 1.1], seed=1)),
        L("o03", "At dinner, theirs was the only table set. Every other chair was up on the tables, while recorded orchestra music played to the empty room.",
          dict(type="dining", z=[1.0, 1.14], f0=[0.5, 0.5], f1=[0.42, 0.55]), lower="Drawn for this film | the story as Stephen King told it"),
        L("o04", "That night, he dreamed that his three-year-old son was running down the hotel's hallways, looking back over his shoulder, screaming. He was being chased by a fire hose.",
          dict(type="corridor", z=[1.06, 1.34], f0=[0.5, 0.47], seed=1), gap=0.8, sfx=[["heart", 4.5]]),
        L("o05", "He woke up drenched in sweat, lit a cigarette, and sat looking out the window at the mountains. By the time he'd finished it, he had the bones of a novel.",
          dict(type="window", z=[1.0, 1.1])),
        L("o06", "The writer was Stephen King. The book became The Shining. And the hotel was the Stanley.",
          [P("king-15.jpg", fit="print", tone="bw", z=[1.0, 1.08], w=1.0, lower="Stephen King | 1974"),
           P("stanley-search-15.jpg", tone="warm", z=[1.0, 1.18], f0=[0.5, 0.55], f1=[0.5, 0.34], w=1.5, lower="The Stanley Hotel | Estes Park, Colorado")], gap=0.8),
        L("o07", "But the Stanley's story starts more than seventy years earlier, with a man from Maine who came to these mountains expecting to die.",
          P("fo-stanley-47.jpg", fit="print", tone="bw", z=[1.0, 1.1], f0=[0.5, 0.45]), gap=0.6),
    ]),
    dict(id="title", music="title", tail=0.3, lines=[
        L("t01", None, dict(type="title", title="THE STANLEY HOTEL", subtitle="The Real Story Behind The Shining",
                             kicker="A LA PORTE WEATHER NOW DOCUMENTARY"), hold=7.0),
    ]),

    # ------------------------------------------------------------------ 1. The twins
    dict(id="c1", music="steam", card=dict(type="chapter", n=1, title="The Twins", sub="Kingfield, Maine · 1849"), lines=[
        L("c1-01", "Freelan Oscar Stanley was born on June 1st, 1849, in Kingfield, Maine. He had an identical twin, Francis. People knew them as F.O. and F.E.",
          P("stanley-search-13.jpg", tone="sepia", z=[1.0, 1.16], f0=[0.45, 0.5], f1=[0.42, 0.32]), lower="The Stanley twins | a trial run in Newton, Massachusetts, 1897"),
        L("c1-02", "The twins were inventors. Their company made photographic dry plates, and in 1905, they sold it to Eastman Kodak.",
          TYPED("THE STANLEY TWINS", ["Born: Kingfield, Maine, 1849.", "Business: photographic dry plates.", "Sold to Eastman Kodak: 1905."])),
        L("c1-03", "By then, they had a new business: steam-powered automobiles. The Stanley Steamer.",
          [P("steamer-16.jpg", fit="print", tone="paper", z=[1.0, 1.08], lower="A Stanley steam car | in a German car magazine, 1900"),
           P("steamer-07.jpg", tone="warm", z=[1.0, 1.12], f0=[0.5, 0.55], f1=[0.42, 0.6], lower="A 1906 Stanley Steamer | Collings Foundation")]),
        L("c1-04", "In 1906, a Stanley steam racer set a world speed record on the sand at Ormond Beach, Florida: more than 127 miles an hour.",
          BIG("127 mph", cap="A world speed record, Ormond Beach, Florida, 1906", file="steamer-30.jpg", tone="bw")),
        L("c1-05", "But F.O. Stanley was sick. He had survived tuberculosis once, in 1881, the year the disease killed one of his brothers. In 1903, it came back, and this time it looked like it would kill him.",
          TYPED("TUBERCULOSIS", ["1881: F.O. Stanley survives it.", "That year, it kills his brother Solomon.", "1903: it comes back."]), gap=0.7),
        L("c1-06", "The treatment of the day was fresh, dry air, sunshine and rest. Stanley went west to Denver, where a tuberculosis doctor sent him higher, to a mountain valley he compared to the famous health resorts of Switzerland: Estes Park.",
          MAP(map="usa", cam0=[-88.0, 41.5, 44], cam1=[-100.0, 40.5, 26], move_end=0.9, title="1903",
              route=[[-70.15, 44.96], [-73.9, 42.7], [-79.0, 42.9], [-87.63, 41.88], [-95.9, 41.26], [-104.99, 39.74], [-105.52, 40.38]],
              route_from=0.08, route_to=0.88,
              places=[{"name": "Kingfield, Maine", "at": [-70.15, 44.96], "show": 0.0, "off": [-360, -80]},
                      {"name": "Denver", "at": [-104.99, 39.74], "show": 0.62, "off": [18, 8]},
                      {"name": "Estes Park", "at": [-105.52, 40.38], "show": 0.8, "off": [-250, -76]}])),
        L("c1-07", "Stanley arrived on June 30th, 1903, with his wife, Flora.",
          P("estes-park-cat-33.jpg", tone="sepia", crop=[0.02, 0.03, 0.98, 0.9], z=[1.0, 1.12], f0=[0.5, 0.55], f1=[0.55, 0.62]), lower="Estes Park | 1907"),
        L("c1-08", "The mountains worked, or something did. He got better. He would live another thirty-seven years.",
          P("longs-peak-14.jpg", tone="warm", crop=[0.01, 0.02, 0.99, 0.97], z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.55, 0.35]),
          lower="Longs Peak, from Estes Park | Detroit Publishing Co., about 1900", gap=0.8),
    ]),

    # ------------------------------------------------------------------ 2. The hotel
    dict(id="c2", music="hotel", card=dict(type="chapter", n=2, title="The Hotel", sub="Estes Park · 1907 – 1909"), lines=[
        L("c2-01", "Stanley fell in love with the valley. He and Flora built a summer house there, and he decided to build a grand hotel, for friends from back East who came out to visit.",
          [P("longs-peak-20.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.96], z=[1.0, 1.1], f0=[0.5, 0.5], f1=[0.45, 0.4], w=1.3),
           P("estes-park-old-07.jpg", fit="print", tone="warm", z=[1.0, 1.08], lower="Beautiful Estes Park | a 1912 booklet")]),
        L("c2-02", "He bought the land from the ranch of an Irish earl, Lord Dunraven, who back in the 1870s had tried to take over the whole valley as his private hunting preserve.",
          [P("dunraven-01.jpg", fit="print", tone="bw", z=[1.0, 1.06], w=0.85, lower="The 4th Earl of Dunraven | 1841 – 1926"),
           P("longs-peak-02.jpg", tone="warm", z=[1.0, 1.14], f0=[0.35, 0.55], f1=[0.62, 0.45], w=1.15, lower="Estes Park, by Albert Bierstadt | 1877")]),
        L("c2-03", "Construction began in 1907. Stanley helped design it himself, in the Colonial Revival style of the East: white walls, red roofs and a long porch facing the peaks.",
          P("stanley-search-16.jpg", tone="warm", z=[1.08, 1.2], f0=[0.25, 0.5], f1=[0.72, 0.5]), lower="The Stanley Hotel | today"),
        L("c2-04", "To light it, he built a hydroelectric plant on the Fall River, which brought electricity to Estes Park for the first time.",
          P("estes-park-cat-15.jpg", tone="sepia", crop=[0.0, 0.0, 1.0, 0.92], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.45, 0.6]), lower="The Fall River, Estes Park | 1921"),
        L("c2-05", "Getting there was half the adventure. Guests rode the train as far as Lyons, in the foothills. From there, Stanley's company carried them up the canyon in steam-powered Mountain Wagons.",
          [MAP(map="colorado", cam0=[-105.2, 40.0, 2.4], cam1=[-105.33, 40.16, 1.5], move_end=0.6, title="1909",
              route=[[-104.99, 39.74], [-105.08, 39.95], [-105.27, 40.22], [-105.33, 40.25], [-105.40, 40.30], [-105.47, 40.35], [-105.52, 40.38]],
              route_from=0.15, route_to=0.85,
              places=[{"name": "Denver", "at": [-104.99, 39.74], "show": 0.0}, {"name": "Boulder", "at": [-105.27, 40.01], "show": 0.0},
                      {"name": "Lyons", "at": [-105.27, 40.22], "show": 0.25, "off": [18, -10]},
                      {"name": "Estes Park", "at": [-105.52, 40.38], "show": 0.75, "off": [-262, -72]},
                      {"name": "ROCKY MOUNTAINS", "at": [-105.78, 40.05], "dot": 0, "font": "fell-sc", "size": 44, "tracking": 6}], w=1.25),
           P("mtwagon-01.jpg", tone="warm", crop=[0.10, 0.08, 0.94, 0.82], z=[1.0, 1.1], f0=[0.40, 0.5], f1=[0.56, 0.5], w=0.9,
             lower="A 1913 Stanley Mountain Wagon | at a steam rally in the Netherlands, 2015")],
          sfx=[["train", 1.5]]),
        L("c2-06", "The Stanley Hotel opened on July 4th, 1909.", BIG("July 4, 1909", cap="The Stanley Hotel opens", file="stanley-search-21.jpg", tone="sepia"), gap=0.8,
          sfx=[["bell", 0.2]]),
        L("c2-07", "That same year, he built a concert hall beside it, for Flora, who played the piano.",
          P("stanley-search-03.jpg", tone="warm", z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.4]), lower="The Concert Hall | today"),
        L("c2-07b", "He also helped bring elk back to the valley from Yellowstone, in 1913, and backed the campaign for Rocky Mountain National Park, which was created right next door in 1915.",
          [P("elk-estes-01.jpg", tone="warm", z=[1.0, 1.12], f0=[0.55, 0.6], f1=[0.6, 0.55], lower="Elk in Estes Park | today"),
           P("longs-peak-15.jpg", fit="print", tone="bw", z=[1.0, 1.08], lower="Enos Mills | who led the campaign for the park"),
           P("longs-peak-09.jpg", tone="bw", z=[1.0, 1.1], f0=[0.5, 0.45], f1=[0.5, 0.35], lower="Rocky Mountain National Park | Ansel Adams, 1930s")]),
        L("c2-08", "It was a summer resort, for wealthy travelers, and for people who came west for their health, the way Stanley had. For decades, the hotel had no heat. Every fall, it closed for the winter.",
          [P("estes-park-old-13.jpg", fit="print", tone="warm", z=[1.0, 1.08], w=1.4, lower="A summer resort | an Estes Park postcard, 1910s", credit="Postcard: UBC Library"),
           P("stanley-search-14.jpg", tone="bw", z=[1.0, 1.12], f0=[0.5, 0.55], f1=[0.6, 0.5])], gap=0.8),
    ]),

    # ------------------------------------------------------------------ 3. The explosion
    dict(id="c3", music="explosion", card=dict(type="chapter", n=3, title="The Explosion", sub="June 25, 1911"), lines=[
        L("c3-01", "On June 25th, 1911, in the hotel's third summer, a gas explosion went off inside the Stanley.",
          NEWS("news1911-05-hi.jpg", mode="zoom", box=[0.2597, 0.5462, 0.4038, 0.6308], margin=1.12, hold=0.32, max_side=8700,
               lower="The Salt Lake Tribune | front page, June 26, 1911"), sfx=[["boom", 0.6]]),
        L("c3-02", "As the hotel tells the story, the power was out, and a chambermaid named Elizabeth Wilson walked into Room 217 with a flame, not knowing the room was full of gas.",
          dict(type="door", number="217", z=[1.0, 1.18], f0=[0.5, 0.5], f1=[0.5, 0.42]), sfx=[["creak", 1.0]]),
        L("c3-03", "The newspapers reported eight people hurt, none of them guests. The worst hurt was the chambermaid. The Associated Press said she was hurled from the second floor to the first, and that both her ankles were broken.",
          [dict(type="pile", w=1.0, lower="Papers across the country | June 26 and 27, 1911", items=[
              {"file": "clip1911-sfcall.jpg", "width": 0.34, "at": [0.30, 0.31], "rot": -3.0},
              {"file": "clip1911-honolulu.jpg", "width": 0.30, "at": [0.72, 0.29], "rot": 2.8},
              {"file": "clip1911-saltlake.jpg", "width": 0.27, "max_h": 0.5, "at": [0.33, 0.68], "rot": 1.8},
              {"file": "clip1911-tonopah.jpg", "width": 0.26, "max_h": 0.5, "at": [0.67, 0.66], "rot": -1.6}]),
           NEWS("clip1911-topeka.jpg", mode="clip", size=[0.84, 0.76], z=[1.0, 1.09], f0=[0.5, 0.48], f1=[0.5, 0.58], w=1.04,
                lower="The Topeka State Journal | June 26, 1911")]),
        L("c3-04", "Not every paper agreed. Colorado papers gave her name as Elizabeth Lambert. And four days later, the Fort Collins Express printed a long, detailed account saying she had never fallen through the floor at all.",
          TYPED("NOT EVERY PAPER AGREED", ["Colorado papers named her", "Elizabeth Lambert.", "The Fort Collins Express, June 29:", "she never fell through the floor."])),
        L("c3-05", "She survived. In the hotel's telling, she healed, went back to work at the Stanley, and stayed for years.",
          P("stanley-search-12.jpg", tone="warm", z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.45, 0.55]), lower="A guest room at the Stanley | today"),
        L("c3-06", "Remember that room number: 217.", BIG("217", cap="Remember the number"), gap=1.2),
    ]),

    # ------------------------------------------------------------------ 4. The long winters
    dict(id="c4", music="winters", card=dict(type="chapter", n=4, title="The Long Winters", sub="1926 – 1974"), lines=[
        L("c4-01", "In 1926, Stanley sold the hotel. The company that bought it went broke, so he took it back, and in 1930, he sold it again.",
          TYPED("THE STANLEY HOTEL", ["1909: opened by F.O. Stanley.", "1926: sold. The buyer went broke.", "Stanley took it back.", "1930: sold again, to Roe Emery."])),
        L("c4-02", "Flora died in 1939. Freelan Oscar Stanley died the next year, on October 2nd, 1940. He was ninety-one.",
          P("fo-stanley-46.jpg", fit="print", tone="warm", z=[1.0, 1.1], lower="F.O. and Flora Stanley | driving up Mount Washington, 1899")),
        L("c4-03", "The hotel passed from owner to owner. With no heat, it still shut down every winter. By the 1970s, its glory days seemed long gone, and the hotel's own history admits it might have ended up under the wrecking ball.",
          P("stanley-search-17.jpg", tone="bw", z=[1.0, 1.16], f0=[0.5, 0.55], f1=[0.55, 0.45])),
        L("c4-04", "Then, in 1974, another man from Maine moved to Colorado.",
          MAP(map="usa", cam0=[-88.0, 41.5, 44], title="1974",
              route=[[-69.0, 44.6], [-73.9, 42.7], [-79.0, 42.9], [-87.63, 41.88], [-95.9, 41.26], [-104.99, 39.74], [-105.27, 40.01]],
              route_from=0.1, route_to=0.85,
              places=[{"name": "Maine", "at": [-69.0, 44.6], "show": 0.0, "dot": 0, "font": "fell-sc", "size": 46, "tracking": 4, "off": [-190, -96]},
                      {"name": "Boulder", "at": [-105.27, 40.01], "show": 0.8, "off": [18, 4]}]), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 5. Room 217
    dict(id="c5", music="king", card=dict(type="chapter", n=5, title="Room 217", sub="October 30, 1974"), lines=[
        L("c5-01", "Stephen King was twenty-seven. His first novel, Carrie, had come out that spring, and he and his wife, Tabitha, had moved their family to Boulder.",
          P("king-15.jpg", fit="print", tone="bw", z=[1.0, 1.1], f0=[0.5, 0.45]), lower="Stephen King | 1974 (photo: Alex Gotfryd)"),
        L("c5-02", "Two years earlier, he'd started a novel called Darkshine, about a psychic boy in a psychic amusement park. He had given up on it.",
          TYPED("DARKSHINE", ["A novel Stephen King started in 1972:", "a psychic boy", "in a psychic amusement park.", "He gave up on it."])),
        L("c5-03", "Then came that night at the Stanley. The empty halls. The music playing to no one. The dream.",
          [dict(type="corridor", z=[1.0, 1.08], seed=1), dict(type="dining", z=[1.08, 1.16], f0=[0.42, 0.55]), dict(type="window", z=[1.04, 1.1])], gap=0.8),
        L("c5-04", "The hotel says the Kings stayed in Room 217.",
          P("stanley-search-11.jpg", tone="warm", z=[1.1, 1.35], f0=[0.3, 0.8], f1=[0.78, 0.2]), lower="Room 217 | the Stanley Hotel, today"),
        L("c5-05", "In the book, a struggling writer named Jack Torrance takes a job as the winter caretaker of the Overlook, a mountain resort that's snowed in for months. He brings his wife, Wendy, and their son, Danny, who has a gift: the shining.",
          dict(type="snowhotel", z=[1.0, 1.12]), lower="The Overlook | a made-up hotel in the novel (drawn)"),
        L("c5-06", "The hotel's ghosts go to work on Jack. And the one room Danny is warned to stay out of is Room 217.",
          [dict(type="snowhotel", z=[1.12, 1.2], snow=1.3), dict(type="door", number="217", z=[1.12, 1.3], f0=[0.5, 0.42])], gap=0.8),
        L("c5-07", "The Shining came out in January 1977. It was King's third novel, and his first hardcover bestseller.",
          BIG("January 1977", cap="The Shining is published: Stephen King's third novel")),
        L("c5-08", "That May, the Stanley Hotel was added to the National Register of Historic Places.",
          P("stanley-search-21.jpg", tone="warm", z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.42]), lower="National Register of Historic Places | May 26, 1977", gap=0.8),
    ]),

    # ------------------------------------------------------------------ 6. The Overlook
    dict(id="c6", music="film", card=dict(type="chapter", n=6, title="The Overlook", sub="1980 – 2015"), lines=[
        L("c6-01", "In 1980, Stanley Kubrick turned the book into a movie, with Jack Nicholson as Jack Torrance.",
          BIG("1980", cap="Stanley Kubrick's The Shining, with Jack Nicholson")),
        L("c6-02", "Kubrick didn't film at the Stanley. The outside of his Overlook is Timberline Lodge, on Mount Hood in Oregon, and the inside was built on sound stages in England.",
          [MAP(map="north", cam0=[-60.0, 45.9, 135], title="THE SHINING, 1980", w=1.4,
              places=[{"name": "The Stanley (not used)", "at": [-105.52, 40.38], "show": 0.02, "off": [18, 4]},
                      {"name": "Timberline Lodge", "at": [-121.71, 45.33], "show": 0.3, "off": [18, -72]},
                      {"name": "Elstree Studios, England", "at": [-0.30, 51.65], "show": 0.62, "off": [-560, -72]}]),
           P("timberline-06.jpg", tone="bw", z=[1.0, 1.1], f0=[0.55, 0.5], f1=[0.6, 0.45], lower="Timberline Lodge, Mount Hood, Oregon | 1930s")]),
        L("c6-03", "Timberline asked for one change. Its managers were afraid guests would refuse to sleep in the lodge's real Room 217. So in the movie, it's Room 237, a number Timberline doesn't have.",
          [dict(type="door", number="217", z=[1.0, 1.06], light=False), dict(type="door", number="237", z=[1.06, 1.16])]),
        L("c6-04", "King never liked Kubrick's version. In 1997, he made his own, a TV miniseries, and this time it was filmed at the Stanley.",
          P("stanley-search-05.jpg", tone="warm", z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.5, 0.55]), lower="The Stanley's lobby | today"),
        L("c6-05", "Hollywood kept coming back. In Dumb and Dumber, the Stanley played a fancy hotel in Aspen.",
          P("stanley-search-07.jpg", tone="warm", z=[1.0, 1.12], f0=[0.4, 0.5], f1=[0.6, 0.5])),
        L("c6-06", "And in 2015, the hotel planted a hedge maze, a nod to Kubrick's film. There's no hedge maze in King's book. He wrote topiary animals instead, the kind that move when you aren't looking.",
          P("stanley-search-06.jpg", tone="warm", z=[1.0, 1.12], f0=[0.45, 0.5], f1=[0.7, 0.55]), lower="The hedge maze | planted in 2015", gap=0.8),
    ]),

    # ------------------------------------------------------------------ 7. The ghosts
    dict(id="c7", music="ghosts", card=dict(type="chapter", n=7, title="The Ghosts", sub="What guests say"), lines=[
        L("c7-01", "Ever since The Shining, people have come to the Stanley hoping to meet a ghost. Some say they have.",
          P("stanley-search-21.jpg", tone="night", z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.5, 0.4])),
        L("c7-02", "In Room 217, guests tell of a presence that tidies up: suitcases unpacked, clothes folded and put away, lights switched off. They say it's the chambermaid from 1911.",
          dict(type="door", number="217", z=[1.0, 1.2], f0=[0.5, 0.5], f1=[0.5, 0.6])),
        L("c7-03", "Some say she doesn't approve of unmarried couples sharing a bed.", SAME, gap=0.7),
        L("c7-04", "On the fourth floor, guests report hearing children laughing and running in the halls at night. When they look, no one's there. And there's no known record of a child ever dying there.",
          P("stanley-search-04.jpg", tone="night", z=[1.0, 1.3], f0=[0.5, 0.5], f1=[0.5, 0.48]), lower="A hallway at the Stanley | today", sfx=[["steps", 3.0]]),
        L("c7-05", "Some say they've seen F.O. Stanley himself, in the billiard room and the bar. And in the music room, people say Flora's piano sometimes plays by itself.",
          [P("stanley-search-09.jpg", tone="sepia-soft", z=[1.0, 1.1], f0=[0.4, 0.5], f1=[0.6, 0.45], lower="The music room | today"),
           P("stanley-search-01.jpg", tone="warm", z=[1.0, 1.16], f0=[0.5, 0.6], f1=[0.5, 0.45], w=1.3, lower="An antique piano at the Stanley")]),
        L("c7-06", "Ghost-hunting TV shows have investigated the hotel, and it runs ghost tours of its own.",
          P("stanley-search-23.jpg", tone="night", z=[1.0, 1.12], f0=[0.55, 0.5], f1=[0.4, 0.4])),
        L("c7-07", "None of it has ever been proven. And according to the Denver Gazette, an employee caught faking a haunting can be fired.",
          TYPED("NONE OF IT PROVEN", ["Ghost stories: what guests say.", "Faking a haunting:", "a firing offense for staff,", "the Denver Gazette reported."]), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 8. Today
    dict(id="c8", music="today", card=dict(type="chapter", n=8, title="The Stanley Today", sub="2026"), lines=[
        L("c8-01", "Since 1983, the Stanley has stayed open all year. In 2025, it was sold in a four-hundred-million-dollar deal, to a nonprofit created through a Colorado state authority.",
          P("stanley-search-16.jpg", tone="warm", z=[1.0, 1.1], f0=[0.4, 0.5], f1=[0.6, 0.5]), lower="The Stanley Hotel | today"),
        L("c8-02", "On the grounds, construction is under way on the Stanley Film Center, with a new theater and a museum of horror films. It's set to open in 2028.",
          TYPED("THE STANLEY FILM CENTER", ["Being built on the hotel grounds.", "A new theater,", "and a museum of horror films.", "Set to open: 2028."]), gap=0.8),
    ]),

    # ------------------------------------------------------------------ epilogue
    dict(id="end", music="finale", card=dict(type="chapter", kicker="EPILOGUE", title="The Stanley", sub="Estes Park, Colorado"), tail=1.0, lines=[
        L("e01", "F.O. Stanley came west expecting to die, and lived thirty-seven more years. The hotel he built nearly faded away, until a writer spent one night there, and had a nightmare.",
          P("stanley-search-19.jpg", tone="warm", z=[1.0, 1.14], f0=[0.5, 0.4], f1=[0.5, 0.3]), lower="F.O. Stanley in bronze | at the hotel today"),
        L("e02", "Is the Stanley haunted? You'll have to decide that for yourself. But few buildings owe as much to a ghost story.",
          [P("stanley-search-15.jpg", tone="night", z=[1.08, 1.24], f0=[0.5, 0.42], f1=[0.5, 0.3]), P("estes-park-cat-29.jpg", tone="night", z=[1.0, 1.1])], gap=1.2),
        L("e03", "Is there a haunted place where you live? Comment your city or town, and we'll make a video on its haunted history.",
          dict(type="cta"), gap=10.0),
    ]),
]


def build():
    script = {"title": "The Stanley Hotel: The Real Story Behind The Shining", "chapters": CHAPTERS}
    json.dump(script, open(os.path.join(HERE, "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    words = sum(len(ln.get("say", "").split()) for ch in CHAPTERS for ln in ch["lines"])
    print(len(CHAPTERS), "chapters,", sum(len(ch["lines"]) for ch in CHAPTERS), "lines,", words, "words")


if __name__ == "__main__":
    build()
