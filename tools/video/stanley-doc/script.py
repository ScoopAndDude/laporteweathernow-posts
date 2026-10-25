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
    dict(id="open", music="open", tail=0.2, lines=[
        L("o01", "On October 30th, 1974, the night before Halloween, a young writer and his wife checked into an old hotel in the Colorado Rockies.",
          TODO("the hotel at night"), lower="Estes Park, Colorado | October 30, 1974"),
        L("o02", "It was about to close for the winter. As he told it later, they were the only guests in the place.", TODO("empty hallway")),
        L("o03", "At dinner, theirs was the only table set. Every other chair was up on the tables, while recorded orchestra music played to the empty room.",
          TODO("dining room")),
        L("o04", "That night, he dreamed that his three-year-old son was running down the hotel's hallways, looking back over his shoulder, screaming. He was being chased by a fire hose.",
          TODO("hallway at night"), gap=0.8),
        L("o05", "He woke up drenched in sweat, lit a cigarette, and sat looking out the window at the mountains. By the time he'd finished it, he had the bones of a novel.",
          TODO("mountains from a window")),
        L("o06", "The writer was Stephen King. The book became The Shining. And the hotel was the Stanley.", TODO("the Stanley"), gap=0.8),
        L("o07", "But the Stanley's story starts more than seventy years earlier, with another man from Maine, who came to these mountains expecting to die.",
          TODO("old photo of the hotel"), gap=0.6),
    ]),
    dict(id="title", music="title", tail=0.3, lines=[
        L("t01", None, dict(type="title", title="THE STANLEY HOTEL", subtitle="The Real Story Behind The Shining",
                             kicker="A LA PORTE WEATHER NOW DOCUMENTARY"), hold=7.0),
    ]),

    # ------------------------------------------------------------------ 1. The twins
    dict(id="c1", music="steam", card=dict(type="chapter", n=1, title="The Twins", sub="Kingfield, Maine · 1849"), lines=[
        L("c1-01", "Freelan Oscar Stanley was born on June 1st, 1849, in Kingfield, Maine. He had an identical twin, Francis. People knew them as F.O. and F.E.",
          TODO("F.O. Stanley")),
        L("c1-02", "The twins were inventors. Their company made photographic dry plates, and in 1905, they sold it to Eastman Kodak.", TODO("dry plates")),
        L("c1-03", "By then, they had a new business: steam-powered automobiles. The Stanley Steamer.", TODO("Stanley Steamer")),
        L("c1-04", "In 1906, a Stanley steam racer set a world speed record on the sand at Ormond Beach, Florida: more than 127 miles an hour.",
          TODO("Rocket racer")),
        L("c1-05", "But F.O. Stanley was sick. He had survived tuberculosis once, in 1881, the year the disease killed one of his brothers. In 1903, it came back, and this time it looked like it would kill him.",
          TODO("F.O. portrait"), gap=0.7),
        L("c1-06", "The treatment of the day was fresh, dry air, sunshine and rest. Stanley went west to Denver, where a tuberculosis doctor sent him higher, to a mountain valley he compared to the famous health resorts of Switzerland: Estes Park.",
          TODO("map Maine to Colorado")),
        L("c1-07", "Stanley arrived on June 30th, 1903, with his wife, Flora.", TODO("Estes Park 1900s")),
        L("c1-08", "The mountains worked, or something did. He got better. He would live another thirty-seven years.", TODO("valley"), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 2. The hotel
    dict(id="c2", music="hotel", card=dict(type="chapter", n=2, title="The Hotel", sub="Estes Park · 1907 – 1909"), lines=[
        L("c2-01", "Stanley fell in love with the valley. He and Flora built a summer house there, and he decided to build a grand hotel, for friends from back East who came out to visit.",
          TODO("Estes Park valley")),
        L("c2-02", "He bought the land from the ranch of an Irish earl, Lord Dunraven, who back in the 1870s had tried to take over the whole valley as his private hunting preserve.",
          TODO("Dunraven / map")),
        L("c2-03", "Construction began in 1907. Stanley helped design it himself, in the Colonial Revival style of the East: white walls, red roofs and a long porch facing the peaks.",
          TODO("hotel, early photo")),
        L("c2-04", "To light it, he built a hydroelectric plant on the Fall River, which brought electricity to Estes Park for the first time.", TODO("Fall River")),
        L("c2-05", "Getting there was half the adventure. Guests rode the train as far as Lyons, in the foothills. From there, Stanley's company carried them up the canyon in steam-powered Mountain Wagons.",
          TODO("Mountain Wagon / map")),
        L("c2-06", "The Stanley Hotel opened on July 4th, 1909.", TODO("opening"), gap=0.8),
        L("c2-07", "That same year, he built a concert hall beside it, for Flora, who played the piano.", TODO("concert hall")),
        L("c2-07b", "He also helped bring elk back to the valley from Yellowstone, in 1913, and backed the campaign for Rocky Mountain National Park, which was created right next door in 1915.",
          TODO("elk / park")),
        L("c2-08", "It was a summer resort, for wealthy travelers, and for people who came west for their health, the way Stanley had. For decades, the hotel had no heat. Every fall, it closed for the winter.",
          TODO("winter"), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 3. The explosion
    dict(id="c3", music="explosion", card=dict(type="chapter", n=3, title="The Explosion", sub="June 25, 1911"), lines=[
        L("c3-01", "On June 25th, 1911, two summers after the hotel opened, a gas explosion went off inside the Stanley.", TODO("1911 newspaper"), sfx=[["boom", 0.6]]),
        L("c3-02", "As the hotel tells the story, the power was out, and a chambermaid named Elizabeth Wilson walked into Room 217 with a flame, not knowing the room was full of gas.",
          TODO("room 217")),
        L("c3-03", "The newspapers reported eight workers hurt, and no guests. The worst hurt was the chambermaid. The Associated Press said she was hurled from the second floor to the first, and that both her ankles were broken.",
          TODO("AP story")),
        L("c3-04", "Not every paper agreed. Colorado papers gave her name as Elizabeth Lambert. And four days later, the Fort Collins Express printed a long, detailed account saying she had never fallen through the floor at all.",
          TODO("Fort Collins Express")),
        L("c3-05", "She survived. In the hotel's telling, she healed, went back to work at the Stanley, and stayed for years.", TODO("the hotel")),
        L("c3-06", "Remember that room number: 217.", BIG("217", cap="Remember the number"), gap=1.2),
    ]),

    # ------------------------------------------------------------------ 4. The long winters
    dict(id="c4", music="winters", card=dict(type="chapter", n=4, title="The Long Winters", sub="1926 – 1974"), lines=[
        L("c4-01", "In 1926, Stanley sold the hotel. The company that bought it went broke, so he took it back, and in 1930, he sold it again.", TODO("hotel 1920s")),
        L("c4-02", "Flora died in 1939. Freelan Oscar Stanley died the next year, on October 2nd, 1940. He was ninety-one.", TODO("Stanley")),
        L("c4-03", "The hotel passed from owner to owner. With no heat, it still shut down every winter. By the 1970s, its glory days seemed long gone, and the hotel's own history admits it might have ended up under the wrecking ball.",
          TODO("faded hotel")),
        L("c4-04", "Then, in 1974, another man from Maine moved to Colorado.", TODO("Boulder / map"), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 5. Room 217
    dict(id="c5", music="king", card=dict(type="chapter", n=5, title="Room 217", sub="October 30, 1974"), lines=[
        L("c5-01", "Stephen King was twenty-seven. His first novel, Carrie, had come out that spring, and he and his wife, Tabitha, had moved their family to Boulder.",
          TODO("Boulder")),
        L("c5-02", "Two years earlier, he'd started a novel called Darkshine, about a psychic boy in a psychic amusement park. He had given up on it.", TODO("Darkshine card")),
        L("c5-03", "Then came that night at the Stanley. The empty halls. The music playing to no one. The dream.", TODO("hall"), gap=0.8),
        L("c5-04", "The hotel says the Kings stayed in Room 217.", TODO("217 door")),
        L("c5-05", "In the book, a struggling writer named Jack Torrance takes a job as the winter caretaker of the Overlook, a mountain resort that's snowed in for months. He brings his wife, Wendy, and their son, Danny, who has a gift: the shining.",
          TODO("snowed-in hotel")),
        L("c5-06", "The hotel's ghosts go to work on Jack. And the one room Danny is warned to stay out of is Room 217.", TODO("217"), gap=0.8),
        L("c5-07", "The Shining came out in January 1977. It was King's third novel, and his first hardcover bestseller.", TODO("1977")),
        L("c5-08", "That May, the Stanley Hotel was added to the National Register of Historic Places.", TODO("NRHP"), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 6. The Overlook
    dict(id="c6", music="film", card=dict(type="chapter", n=6, title="The Overlook", sub="1980 – 2015"), lines=[
        L("c6-01", "In 1980, Stanley Kubrick turned the book into a movie, with Jack Nicholson as Jack Torrance.", TODO("1980")),
        L("c6-02", "Kubrick didn't film at the Stanley. The outside of his Overlook is Timberline Lodge, on Mount Hood in Oregon, and the inside was built on sound stages in England.",
          TODO("Timberline Lodge")),
        L("c6-03", "Timberline asked for one change. Its managers were afraid guests would refuse to sleep in the lodge's real Room 217. So in the movie, it's Room 237, a number Timberline doesn't have.",
          TODO("237")),
        L("c6-04", "King never liked Kubrick's version. In 1997, he made his own, a TV miniseries, and this time it was filmed at the Stanley.", TODO("Stanley")),
        L("c6-05", "Hollywood kept coming back. In Dumb and Dumber, the Stanley played a fancy hotel in Aspen.", TODO("Stanley")),
        L("c6-06", "And in 2015, the hotel planted a hedge maze, a nod to Kubrick's film. There's no hedge maze in King's book. He wrote topiary animals instead, the kind that move when you aren't looking.",
          TODO("hedge maze"), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 7. The ghosts
    dict(id="c7", music="ghosts", card=dict(type="chapter", n=7, title="The Ghosts", sub="What guests say"), lines=[
        L("c7-01", "Ever since The Shining, people have come to the Stanley hoping to meet a ghost. Some say they have.", TODO("night")),
        L("c7-02", "In Room 217, guests tell of a presence that tidies up: suitcases unpacked, clothes folded and put away, lights switched off. They say it's the chambermaid from 1911.",
          TODO("room")),
        L("c7-03", "Some say she doesn't approve of unmarried couples sharing a bed.", SAME, gap=0.7),
        L("c7-04", "On the fourth floor, guests report hearing children laughing and running in the halls at night. When they look, no one's there. And there's no known record of a child ever dying there.",
          TODO("4th floor")),
        L("c7-05", "Some say they've seen F.O. Stanley himself, in the billiard room and the bar. And in the music room, people say Flora's piano sometimes plays by itself.",
          TODO("piano")),
        L("c7-06", "Ghost-hunting TV shows have investigated the hotel, and it runs ghost tours of its own.", TODO("tour")),
        L("c7-07", "None of it has ever been proven. And according to the Denver Gazette, an employee caught faking a haunting can be fired.", TODO("card"), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 8. Today
    dict(id="c8", music="today", card=dict(type="chapter", n=8, title="The Stanley Today", sub="2026"), lines=[
        L("c8-01", "Since 1983, the Stanley has stayed open all year. In 2025, it was sold in a four-hundred-million-dollar deal, to a nonprofit created through a Colorado state authority.", TODO("hotel today")),
        L("c8-02", "On the grounds, construction is under way on the Stanley Film Center, with a new theater and a museum of horror films. It's set to open in 2028.",
          TODO("film center"), gap=0.8),
    ]),

    # ------------------------------------------------------------------ epilogue
    dict(id="end", music="end", card=dict(type="chapter", kicker="EPILOGUE", title="The Stanley", sub="Estes Park, Colorado"), tail=1.0, lines=[
        L("e01", "F.O. Stanley came west expecting to die, and lived thirty-seven more years. The hotel he built nearly faded away, until a writer spent one night there, and had a nightmare.",
          TODO("hotel")),
        L("e02", "Is the Stanley haunted? You'll have to decide that for yourself. But few buildings owe as much to a ghost story.", TODO("hotel at dusk"), gap=1.2),
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
