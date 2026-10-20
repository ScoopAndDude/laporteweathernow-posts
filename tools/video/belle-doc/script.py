#!/usr/bin/env python3
"""The documentary's script: every narration line and the pictures shown with it.

    python3 tools/video/belle-doc/script.py        writes script.json (what doc.py and the voice job read)

Facts come from two research files (Oct. 20, 2026; sources in the YouTube description): the La Porte County
Historical Society, Store norske leksikon, Ted Hartzell's work from Belle's original letters (HistoryNet,
2008), 1908 newspapers (Chronicling America and the state newspaper archives), the AP and the University of
Indianapolis on the 2007-08 exhumation, and others. Disputed points are said as disputed ("by most
accounts", "one doctor... another..."); legends are called legends; the famous "wild rapture" letter and
"Triflers need not apply" are left out because they can't be traced to Belle.
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


def spoken(s):
    """How the narrator should say it: years and decades in words (the captions keep the numerals)."""
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

AD_TEXT = ("Comely widow, who owns large farm in one of the finest districts in La Porte county, Indiana, desires to make the "
           "acquaintance of gentleman equally well provided, with view of joining fortunes. No replies by letter considered "
           "unless sender is willing to follow answer with personal visit.")

# ---------------------------------------------------------------------------------------------- the chapters
def TODO(desc):
    """A stand-in until the right picture is chosen."""
    return QUOTE(desc, "picture to come", size=48)


NOR = dict(map="atlantic")
MIDWEST_PLACES = [
    {"name": "Chicago", "at": [-87.63, 41.88], "show": 0.0},
    {"name": "Michigan City", "at": [-86.89, 41.71], "show": 0.4, "size": 44},
    {"name": "La Porte", "at": [-86.72, 41.61], "show": 0.65},
    {"name": "LAKE MICHIGAN", "at": [-87.25, 42.05], "dot": 0, "font": "fell-sc", "size": 46, "tracking": 4},
    {"name": "INDIANA", "at": [-86.95, 41.3], "dot": 0, "font": "fell-sc", "size": 40, "tracking": 6},
    {"name": "ILLINOIS", "at": [-87.75, 41.3], "dot": 0, "font": "fell-sc", "size": 40, "tracking": 6},
    {"name": "MICHIGAN", "at": [-86.45, 42.1], "dot": 0, "font": "fell-sc", "size": 40, "tracking": 6},
]
SUITOR_PLACES = [
    {"name": "La Porte", "at": [-86.72, 41.61], "show": 0.0},
    {"name": "LAKE MICHIGAN", "at": [-87.2, 43.6], "dot": 0, "font": "fell-sc", "size": 40, "tracking": 4},
]

CHAPTERS = [
    # ------------------------------------------------------------------ cold open
    dict(id="open", music="open", tail=0.2, lines=[
        L("o01", "Before dawn on April twenty-eighth, 1908, a farmhouse burned to the ground just north of La Porte, Indiana.",
          P("belle-farm-13.jpg", z=[1.0, 1.14], f0=[0.5, 0.6], f1=[0.45, 0.66]), lower="La Porte, Indiana | April 28, 1908",
          sfx=[["fire", 0.0]]),
        L("o02", "In the cellar, searchers found the bodies of three children, and a woman. Her head was missing.",
          P("belle-farm-15.jpg", z=[1.05, 1.2], f0=[0.5, 0.42], f1=[0.5, 0.55])),
        L("o03", "Everyone believed the woman was their mother. A widow named Belle Gunness.",
          P("belle-08.jpg", fit="print", z=[1.0, 1.12])),
        L("o04", "Then the digging began.", P("belle-farm-05.jpg", z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.4, 0.62]), gap=0.8,
          sfx=[["thud", 0.9]]),
        L("o05", "Behind the house, in a buried garbage pit, they found a farmer who had come all the way from South Dakota to marry her.",
          P("belle-farm-03.jpg", z=[1.0, 1.15], f0=[0.55, 0.5], f1=[0.6, 0.45])),
        L("o06", "Then they found more.", P("belle-farm-09.jpg", z=[1.05, 1.18]), gap=0.9),
        L("o07", "For years, men had been answering a lonely widow's ads in the newspapers. Many of them were never seen again.",
          dict(type="ad", head="PERSONAL.", text=AD_TEXT, sync=False, z=[1.0, 1.25])),
        L("o08", "This is the story of Belle Gunness, and of the question La Porte has never been able to answer.",
          P("belle-07.jpg", fit="contain", z=[1.0, 1.10]), gap=0.6),
    ]),
    dict(id="title", music="title", tail=0.3, lines=[
        L("t01", None, dict(type="title", title="BELLE GUNNESS", subtitle="The Black Widow of La Porte",
                             kicker="A LA PORTE WEATHER NOW DOCUMENTARY"), hold=7.5),
    ]),

    # ------------------------------------------------------------------ 1. Brynhild
    dict(id="c1", music="norway", card=dict(type="chapter", n=1, title="Brynhild", sub="Selbu, Norway · 1859"), lines=[
        L("c1-01", "She was born Brynhild Paulsdatter Størset, on November eleventh, 1859, in Selbu, a farming district in the hills of central Norway.",
          MAP(**NOR, cam0=[9.0, 61.5, 30], cam1=[11.0, 63.2, 7], title="NORWAY", move_end=0.85,
              places=[{"name": "Selbu", "at": [11.03, 63.22], "show": 0.45}, {"name": "Trondheim", "at": [10.39, 63.43], "show": 0.6, "size": 44, "off": [-210, -40]}])),
        L("c1-02", "She was the youngest of eight children. Her father was a cottar, a tenant who worked another family's land, and a stonecutter.",
          TODO("Selbu / Norwegian farm, 1800s")),
        L("c1-03", "As a teenager she herded cattle and milked cows on the neighbors' farms, and saved for one thing: a ticket to America.",
          TODO("Norwegian farm life / cattle")),
        L("c1-04", "In Selbu, a story is still told about her: that as a young woman she was attacked at a dance, lost the baby she was carrying, and was never the same. There's no record that it happened.",
          QUOTE("A story told in Selbu", None, font="fell-it", size=70), gap=0.6),
        L("c1-05", "In 1881, at twenty-one, she crossed the Atlantic to join her older sister in Chicago.",
          MAP(**NOR, cam0=[-20, 55, 70], cam1=[-38, 50, 95], title="1881", move_end=0.6,
              route=[[11.03, 63.22], [10.39, 63.43], [7.0, 62.6], [4.5, 61.2], [1.5, 57.5], [-0.33, 53.74], [-2.98, 53.41], [-6.0, 52.0],
                     [-25, 50], [-50, 44], [-74.0, 40.7], [-80.0, 41.4], [-87.63, 41.88]],
              route_from=0.08, route_to=0.92,
              places=[{"name": "Selbu", "at": [11.03, 63.22], "show": 0.0}, {"name": "New York", "at": [-74.0, 40.7], "show": 0.7},
                      {"name": "Chicago", "at": [-87.63, 41.88], "show": 0.88},
                      {"name": "ATLANTIC OCEAN", "at": [-38, 47], "dot": 0, "font": "fell-sc", "size": 50, "tracking": 8}])),
        L("c1-06", "In America, Brynhild became Bella. Then Belle.", TODO("Castle Garden / emigrants arriving"), gap=0.7),
    ]),

    # ------------------------------------------------------------------ 2. Chicago
    dict(id="c2", music="chicago", card=dict(type="chapter", n=2, title="Chicago", sub="1881 – 1900"), lines=[
        L("c2-01", "Chicago in the 1880s was one of the fastest-growing cities in the world, and home to more Norwegians than any other city in America.",
          TODO("Chicago street, 1880s-90s")),
        L("c2-02", "Belle worked as a servant. In 1884 she married a fellow Norwegian, Mads Sorenson.",
          TYPED("CHICAGO, 1884", ["Bella Petersen, servant girl,", "marries Mads Ditlev Anton Sorenson,", "a Norwegian from Drammen."])),
        L("c2-03", "They opened a candy store. It caught fire. The insurance paid.", TODO("Chicago storefront, 1890s"), sfx=[["fire", 1.5]]),
        L("c2-04", "Over the years, the candy store and two of their homes burned. Each time, Belle collected.",
          BIG("Three fires", cap="the candy store and two homes, and insurance every time")),
        L("c2-05", "Two children in the Sorensons' care, Caroline and Axel, died as babies. Doctors blamed an inflammation of the bowel, which can also be a sign of poison. Both children were insured.",
          dict(type="names", head="DIED IN INFANCY", names=[["Caroline", "1896"], ["Axel", "1898"]])),
        L("c2-06", "Belle and Mads also raised two girls, Myrtle and Lucy, and a foster daughter, Jennie Olson.",
          P("belle-05.jpg", z=[1.0, 1.12], f0=[0.55, 0.45], f1=[0.62, 0.5]), credit="Photo: Library of Congress, Bain Collection (public domain)"),
        L("c2-07", "On July thirtieth, 1900, Mads came home with a headache. Belle said she gave him a powder for it. Then he died.",
          TODO("Chicago home, 1900")),
        L("c2-08", "It was the one day on which two of his life insurance policies overlapped: the old one ending, and a new, bigger one beginning.",
          BIG("July 30, 1900", cap="the one day two life insurance policies overlapped")),
        L("c2-09", "One doctor suspected poison. Another blamed his heart. There was no autopsy, and no charges.",
          TYPED("MADS SORENSON, 1900", ["One doctor: poison?", "Another: his heart.", "Autopsy: none.", "Charges: none."])),
        L("c2-10", "Belle collected on both policies: by most accounts, eight thousand five hundred dollars.",
          BIG("$8,500", cap="by most accounts")),
        L("c2-11", "She used it to buy a farm, about sixty miles to the east, outside La Porte, Indiana.",
          MAP(map="midwest", cam0=[-87.15, 41.8, 2.3], cam1=[-87.0, 41.72, 1.5], move_end=0.9,
              route=[[-87.63, 41.88], [-87.4, 41.62], [-87.0, 41.6], [-86.72, 41.61]], route_from=0.15, route_to=0.85,
              places=MIDWEST_PLACES), gap=0.7),
    ]),

    # ------------------------------------------------------------------ 3. The farm
    dict(id="c3", music="farm", card=dict(type="chapter", n=3, title="McClung Road", sub="La Porte, Indiana · 1901"), lines=[
        L("c3-01", "In November 1901, Belle moved to La Porte with Jennie, Myrtle and Lucy.",
          P("laporte-08.jpg", fit="contain", z=[1.0, 1.08]), lower="La Porte, Indiana | 1901"),
        L("c3-02", "The farm sat at the north edge of town, on McClung Road: more than forty acres, a big brick house, a barn, and an orchard.",
          P("belle-farm-02.jpg", z=[1.0, 1.12], f0=[0.45, 0.55], f1=[0.55, 0.5])),
        L("c3-03", "La Porte was a busy factory town. Belle kept to herself, and she worked hard.",
          [P("laporte-15.jpg", tone="paper", z=[1.25, 1.6], f0=[0.55, 0.62], f1=[0.5, 0.58], crop=[0.3, 0.3, 1.0, 1.0]), P("laporte-11.jpg", z=[1.0, 1.1])]),
        L("c3-04", "Within months, she married again. On April first, 1902, at the First Baptist Church in La Porte, she wed Peter Gunness, a Norwegian widower who had once boarded with her family in Chicago.",
          TYPED("LA PORTE, APRIL 1, 1902", ["Married: Belle Sorenson", "and Peter Gunness, a widower,", "at the First Baptist Church."])),
        L("c3-05", "Peter brought his two little daughters. Within about a week, the baby died, while she was alone with Belle. No one ever determined why.",
          P("belle-farm-07.jpg", z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.42, 0.55])),
        L("c3-06", "On December sixteenth, 1902, Peter died too.", BIG("December 16, 1902"), gap=0.7),
        L("c3-07", "Belle said a heavy sausage grinder had fallen from a high shelf and struck him on the head.",
          QUOTE("A sausage-grinding machine fell on his head, she wrote.", "Peter's brother Gus, to reporters in 1908")),
        L("c3-08", "The coroner weighed the grinder, and measured how far it could have fallen.",
          TYPED("THE CORONER, DECEMBER 1902", ["Weighed the grinder.", "Measured the fall.", "Called a jury."])),
        L("c3-09", "He was suspicious. But in the end, there were no charges. Belle collected about three thousand dollars in life insurance.",
          BIG("$3,000", cap="life insurance, about")),
        L("c3-10", "Peter's brother came and took his surviving daughter, Swanhild, away with him.",
          P("belle-farm-14.jpg", z=[1.0, 1.1], f0=[0.4, 0.55], f1=[0.5, 0.55])),
        L("c3-11", "In 1903, Belle had a son. She named him Philip.",
          P("belle-02.jpg", fit="print", z=[1.0, 1.1], f0=[0.5, 0.5], f1=[0.55, 0.45]), gap=0.7),
    ]),

    # ------------------------------------------------------------------ 4. The ads
    dict(id="c4", music="ads", card=dict(type="chapter", n=4, title="The Ads", sub="1904 – 1907"), lines=[
        L("c4-01", "Hired men came to work on the farm. Some stayed. Some, people noticed, simply left, sometimes without their things.",
          P("belle-farm-08.jpg", z=[1.0, 1.12], f0=[0.4, 0.5], f1=[0.5, 0.5])),
        L("c4-02", "In 1906, Jennie Olson, the foster daughter Belle had raised since she was a baby, disappeared.",
          TYPED("JENNIE OLSON", ["Foster daughter of Belle Gunness.", "Raised by her since she was a baby.", "Last seen in 1906."])),
        L("c4-03", "Belle said Jennie had gone away to school, in Los Angeles by most accounts. Nobody ever saw her again.",
          P("belle-farm-06.jpg", z=[1.0, 1.12]), gap=0.7),
        L("c4-04", "By then, Belle was writing letters. A lot of them. Her mail carrier said she sent eight to ten a day.",
          TODO("1900s letters / post office")),
        L("c4-05", "She was placing ads in the marriage columns of newspapers, many of them Norwegian-language papers read by farmers all over the Midwest.",
          TODO("1908 newspaper page")),
        L("c4-06", "One of them, as a newspaper reprinted it in 1908, read: " + AD_TEXT,
          dict(type="ad", head="PERSONAL.", text=AD_TEXT, z=[1.05, 1.3]), gap=0.8, sfx=[["page", 0.0]]),
        L("c4-07", "Men answered. Farmers and laborers, most of them Norwegian immigrants like her, many of them with savings.",
          P("belle-11.jpg", z=[1.6, 1.25], f0=[0.55, 0.45], f1=[0.6, 0.5])),
        L("c4-08", "She told them what to do. Sell everything. Bring cash. Sew the money into your clothes. Tell no one.",
          TYPED("WHAT SHE ASKED", ["Sell everything.", "Bring cash.", "Sew the money into your clothes.", "Tell no one."])),
        L("c4-09", "John Moe came from Elbow Lake, Minnesota, with more than a thousand dollars. Within about a week, he was gone.",
          MAP(map="plains", cam0=[-92.0, 44.2, 18], title="THE SUITORS", route=[[-95.98, 45.99], [-91.0, 43.5], [-87.6, 41.9], [-86.72, 41.61]],
              route_from=0.1, route_to=0.85, places=SUITOR_PLACES + [{"name": "Elbow Lake, Minn.", "at": [-95.98, 45.99], "show": 0.02}])),
        L("c4-10", "Henry Gurholdt came from Scandinavia, Wisconsin, with about fifteen hundred. Belle said he'd gone off to Chicago with some horse traders. She kept his trunk, and his fur coat.",
          MAP(map="plains", cam0=[-92.0, 44.2, 18], title="THE SUITORS", route=[[-89.15, 44.46], [-88.4, 43.0], [-87.6, 41.9], [-86.72, 41.61]],
              route_from=0.1, route_to=0.6, places=SUITOR_PLACES + [{"name": "Elbow Lake, Minn.", "at": [-95.98, 45.99], "show": 0.0},
                                                                     {"name": "Scandinavia, Wis.", "at": [-89.15, 44.46], "show": 0.02}])),
        L("c4-11", "Ole Budsberg, a widower from Iola, Wisconsin, was last seen in April 1907 at the La Porte Savings Bank, where he had turned a mortgage on his land into cash.",
          MAP(map="plains", cam0=[-92.0, 44.2, 18], title="THE SUITORS", route=[[-89.13, 44.51], [-88.2, 43.0], [-87.6, 41.9], [-86.72, 41.61]],
              route_from=0.1, route_to=0.6, places=SUITOR_PLACES + [{"name": "Elbow Lake, Minn.", "at": [-95.98, 45.99], "show": 0.0},
                                                                     {"name": "Scandinavia, Wis.", "at": [-89.15, 44.46], "show": 0.0, "off": [18, 14]},
                                                                     {"name": "Iola, Wis.", "at": [-89.13, 44.51], "show": 0.02, "off": [18, -70]}])),
        L("c4-12", "When his sons wrote to ask where he was, Belle answered that he had never arrived.", TODO("letter / envelope 1907"), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 5. Andrew
    dict(id="c5", music="suitors", card=dict(type="chapter", n=5, title="Andrew", sub="1906 – 1908"), lines=[
        L("c5-01", "In 1906, a bachelor farmer from near Aberdeen, South Dakota, answered one of Belle's ads. His name was Andrew Helgelien.",
          MAP(map="plains", cam0=[-93.0, 44.0, 19], title="1906", route=[[-98.49, 45.46], [-95.0, 44.0], [-90.0, 42.5], [-86.72, 41.61]],
              route_from=0.3, route_to=0.95, places=SUITOR_PLACES + [{"name": "Aberdeen, S.D.", "at": [-98.49, 45.46], "show": 0.05}])),
        L("c5-02", "For sixteen months, they wrote to each other.", TODO("letters, 1906-07")),
        L("c5-03", "In one letter, she told him how to carry his money, sewn inside his underwear, and wrote: Do not say one word about it to anyone, not even your nearest relative.",
          dict(type="letter", greeting="My dear friend,", text="Do not say one word about it to anyone, not even your nearest relative.", sign="Bella Gunness", sync=False)),
        L("c5-04", "In another, she wrote: I do not think you will leave me after you have first come here. That I am sure of.",
          dict(type="letter", text="I do not think you will leave me after you have first come here; that I am sure of.", sign="Bella Gunness", sync=False), gap=0.9),
        L("c5-05", "In early January 1908, Andrew came to La Porte. He told his brother he'd be home in a week.",
          P("belle-farm-14.jpg", tone="bw", z=[1.0, 1.1]), lower="La Porte | January 1908"),
        L("c5-06", "He had his savings, nearly three thousand dollars, sent to a bank in La Porte. Belle took the money in cash.",
          BIG("nearly $3,000", cap="Andrew Helgelien's savings")),
        L("c5-07", "The next day, Andrew was gone.", P("belle-farm-06.jpg", tone="bw", z=[1.05, 1.2]), gap=1.0),
        L("c5-08", "Someone else was watching: Belle's hired man, Ray Lamphere. By most accounts he was in love with her, and jealous of Andrew.",
          P("belle-12.jpg", fit="print", z=[1.0, 1.1])),
        L("c5-09", "In February 1908, Belle fired him. Then she went after him: she had him arrested for trespassing, tried to get a peace bond against him, and asked to have him declared insane.",
          P("belle-13.jpg", fit="contain", z=[1.0, 1.08])),
        L("c5-10", "Back in South Dakota, Andrew's brother, Asle, kept writing, asking where Andrew had gone.", TODO("Asle Helgelien / letters")),
        L("c5-11", "Belle wrote back that Andrew had gone away, perhaps to Norway, and suggested Asle sell his brother's stock and come help her look.",
          QUOTE("Sell your brother's stock and come here and we will hunt your brother together.", "Belle Gunness to Asle Helgelien, as printed in 1908")),
        L("c5-12", "She was still writing to other men. On March first, 1908, she told a man in Kansas City that she was a lonely Norwegian woman, and asked whether he could put up a thousand dollars in cash.",
          QUOTE("I am a lonely Norwegian woman.", "Belle Gunness, March 1, 1908, to a man in Kansas City")),
        L("c5-13", "On April twenty-seventh, 1908, Belle went to a La Porte lawyer, Melvin Leliter, and made her will, leaving everything to her children.",
          TYPED("LAST WILL", ["Belle Gunness, April 27, 1908.", "Attorney: Melvin E. Leliter, La Porte.", "Everything to her children."])),
        L("c5-14", "She told him she was afraid Ray Lamphere was going to kill her, and burn down her house.",
          P("belle-08.jpg", fit="contain", z=[1.0, 1.12], f0=[0.5, 0.42])),
        L("c5-15", "That evening, by one account, she bought cakes, a toy train, and two gallons of kerosene.",
          BIG("two gallons of kerosene", cap="April 27, 1908, by one account", size=120), gap=1.2),
    ]),

    # ------------------------------------------------------------------ 6. The fire
    dict(id="c6", music="fire", card=dict(type="chapter", n=6, title="The Fire", sub="April 28, 1908"), lines=[
        L("c6-01", "Around four o'clock the next morning, the new hired man, Joe Maxson, woke to the smell of smoke.",
          TODO("night / smoke"), sfx=[["fire", 2.0]]),
        L("c6-02", "He shouted for Belle and the children. No one answered. He ran for help.", TODO("La Porte fire department / night")),
        L("c6-03", "By the time the fire was out, the big brick house had collapsed into its own cellar.",
          P("belle-farm-13.jpg", z=[1.0, 1.12], f0=[0.5, 0.65], f1=[0.5, 0.6])),
        L("c6-04", "In the ruins, searchers found four bodies: Myrtle, eleven. Lucy, nine. Philip, five. And a woman, without a head.",
          dict(type="names", names=[["Myrtle", "11"], ["Lucy", "9"], ["Philip", "5"], ["and a woman, without a head", ""]], span=0.85), gap=1.0),
        L("c6-05", "That same day, the sheriff went looking for Ray Lamphere. By evening, according to the newspapers, he was under arrest, charged with murdering Belle Gunness and her children.",
          P("belle-12.jpg", fit="contain", z=[1.0, 1.1])),
        L("c6-06", "Lamphere said he had only seen the fire as he passed by on his way to work.", P("belle-13.jpg", fit="print", z=[1.0, 1.08])),
        L("c6-07", "The first newspaper stories called it a tragedy: a widow and her children, burned in their beds.", TODO("1908 headline: FOUR BURNED IN THEIR BEDS")),
        L("c6-08", "That story lasted one week.", P("belle-14.jpg", fit="print", z=[1.0, 1.12]), gap=1.2),
    ]),

    # ------------------------------------------------------------------ 7. The hog lot
    dict(id="c7", music="digging", card=dict(type="chapter", n=7, title="The Hog Lot", sub="May 1908"), lines=[
        L("c7-01", "In early May, a stranger walked into the sheriff's office. It was Asle Helgelien, from South Dakota, with a stack of Belle's letters to his brother.",
          TODO("Asle Helgelien / sheriff")),
        L("c7-02", "He didn't believe Andrew had simply left.", SAME),
        L("c7-03", "Joe Maxson remembered something. In March, Belle had him fill and level a pit of garbage near the hog lot.",
          P("belle-farm-03.jpg", z=[1.0, 1.12], f0=[0.5, 0.55], f1=[0.58, 0.5])),
        L("c7-04", "On May fifth, 1908, they dug there.", BIG("May 5, 1908", file="belle-farm-05.jpg"), sfx=[["thud", 1.2]]),
        L("c7-05", "Wrapped in sacks, they found the remains of Andrew Helgelien.", P("belle-farm-05.jpg", z=[1.05, 1.18], f0=[0.45, 0.6])),
        L("c7-06", "Two feet below him lay Jennie Olson, the foster daughter who had supposedly gone away to school.", TODO("Jennie Olson"), gap=1.0),
        L("c7-07", "They kept digging. By the next night, nine bodies had come out of the yard.", P("belle-farm-09.jpg", z=[1.0, 1.15], f0=[0.5, 0.6], f1=[0.45, 0.5])),
        L("c7-08", "Most had been cut apart. Some were men. Some were children.", P("belle-01.jpg", tone="sepia", z=[1.0, 1.1])),
        L("c7-09", "Searchers recovered the remains of at least a dozen people from the farm. Only a few were ever named: Andrew Helgelien. Jennie Olson. Ole Budsberg. John Moe, and possibly Henry Gurholdt.",
          dict(type="names", head="IDENTIFIED", names=[["Andrew Helgelien", "Mansfield, South Dakota"], ["Jennie Olson", "her foster daughter"],
                                                         ["Ole Budsberg", "Iola, Wisconsin"], ["John Moe", "Elbow Lake, Minnesota"],
                                                         ["Henry Gurholdt (possibly)", "Scandinavia, Wisconsin"]], span=0.8)),
        L("c7-10", "The rest were never named. Seven of them were buried in La Porte's potter's field.", TODO("cemetery, La Porte")),
        L("c7-11", "Estimates of how many people Belle Gunness killed run from fourteen to more than forty.", BIG("14 to 40+", cap="estimates of how many people she killed"), gap=0.9),
        L("c7-12", "And the whole country was watching La Porte.", TODO("1908 headline, May")),
        L("c7-13", "On Sunday, May tenth, thousands of people came out to the farm. The railroads and trolleys alone brought about four thousand more into town.",
          [P("belle-farm-04.jpg", z=[1.0, 1.12]), P("belle-farm-10.jpg", z=[1.0, 1.1])], lower="The Gunness farm | Sunday, May 10, 1908", sfx=[["crowd", 0.0]]),
        L("c7-14", "Peddlers at the gate sold lemonade and lunches, and souvenir pictures. The best seller was a photograph of Belle and her three children.",
          P("belle-09.jpg", fit="print", z=[1.0, 1.12]), gap=0.9),
    ]),

    # ------------------------------------------------------------------ 8. Was it Belle?
    dict(id="c8", music="doubt", card=dict(type="chapter", n=8, title="Was It Belle?", sub="May 1908"), lines=[
        L("c8-01", "But was the woman in the cellar really Belle?", P("belle-07.jpg", fit="contain", z=[1.0, 1.1]), gap=0.7),
        L("c8-02", "Her head was never found.", SAME, gap=0.9),
        L("c8-03", "Neighbors, and at least one local doctor who knew her, said the body was far too small to be hers. Other doctors said the fire could explain it. No reliable measurement survives.",
          TYPED("THE WOMAN IN THE CELLAR", ["Head: never found.", "Too small to be Belle, said neighbors and one doctor.", "The fire shrank it, said others."])),
        L("c8-04", "A Chicago chemist later reported finding poison in the stomachs of the woman and two of the children.",
          TYPED("REPORTED IN 1908", ["Dr. Walter Haines, Rush Medical College:", "arsenic and strychnine."])),
        L("c8-05", "The sheriff and a miner named Louis Schultz washed the ashes through a sluice, like gold.", TODO("sluicing the ashes")),
        L("c8-06", "On May nineteenth, they found two dental plates with false teeth. Belle's dentist said they were hers.", BIG("May 19, 1908", cap="the teeth"), sfx=[["camera", 0.8]]),
        L("c8-07", "The sheriff said it proved, beyond the shadow of a doubt, that Belle had died in the fire. The coroner agreed.",
          QUOTE("beyond the shadow of a doubt", "Sheriff Albert Smutzer, May 1908")),
        L("c8-08", "Not everyone did. The teeth had come through a fire that destroyed a house, and they were in good shape. Many people believed they had been planted.",
          P("belle-08.jpg", fit="print", z=[1.0, 1.1])),
        L("c8-09", "Three days later, a grand jury indicted Ray Lamphere for arson and murder. It also indicted Belle Gunness, for the murder of Andrew Helgelien, though the coroner had just declared her dead.",
          TODO("1908 headline: INDICTED AFTER DEATH"), gap=1.0),
    ]),

    # ------------------------------------------------------------------ 9. The trial
    dict(id="c9", music="trial", card=dict(type="chapter", n=9, title="The Trial", sub="November 1908"), lines=[
        L("c9-01", "Ray Lamphere went on trial in November 1908, at the La Porte County Courthouse.", TODO("La Porte County Courthouse")),
        L("c9-02", "Choosing a jury was hard. Several men were excused because they believed Belle Gunness was still alive.", TODO("courtroom / jurors")),
        L("c9-03", "Lamphere's lawyer, Wirt Worden, argued that she was.", P("belle-13.jpg", fit="contain", z=[1.0, 1.08])),
        L("c9-04", "Witnesses testified that they had seen Belle, alive, that summer.", P("belle-07.jpg", fit="print", z=[1.0, 1.1])),
        L("c9-05", "On Thanksgiving Day, November twenty-sixth, the jury gave its verdict: not guilty of murder. Guilty of arson.",
          BIG("Guilty of arson", cap="November 26, 1908"), sfx=[["gavel", 3.0]]),
        L("c9-06", "He was sentenced to two to twenty-one years in the state prison at Michigan City.", TODO("Indiana State Prison, Michigan City")),
        L("c9-07", "He served about a year. On December thirtieth, 1909, Ray Lamphere died of tuberculosis.", P("belle-12.jpg", fit="print", z=[1.0, 1.1]), gap=0.8),
        L("c9-08", "After his death, newspapers printed what they called his confession. In it, he said he had set the fire, and that the body in the cellar was Belle.",
          TODO("1910 newspaper: confession")),
        L("c9-09", "Other men told other stories. That Lamphere had helped her escape. That the woman in the cellar was a housekeeper lured from Chicago. That Belle had killed forty-two men.",
          TYPED("WHAT OTHERS SAID HE SAID", ["He helped her escape.", "The body was a housekeeper from Chicago.", "She killed 42 men."])),
        L("c9-10", "Those stories came secondhand, after Lamphere was dead, and they contradict each other.", SAME, gap=1.0),
    ]),

    # ------------------------------------------------------------------ 10. Sightings
    dict(id="c10", music="sightings", card=dict(type="chapter", n=10, title="Sightings", sub="1908 – 1931"), lines=[
        L("c10-01", "Within days of the fire, people started seeing Belle Gunness.",
          MAP(map="usa", cam0=[-96, 38.5, 60], title="SIGHTINGS", places=[{"name": "La Porte", "at": [-86.72, 41.61], "show": 0.0}])),
        L("c10-02", "In Syracuse. In Tacoma. For more than twenty years, letters reached La Porte from all over the country.",
          MAP(map="usa", cam0=[-96, 38.5, 60], title="SIGHTINGS", places=[{"name": "La Porte", "at": [-86.72, 41.61], "show": 0.0},
              {"name": "Syracuse", "at": [-76.15, 43.05], "show": 0.05}, {"name": "Tacoma", "at": [-122.44, 47.25], "show": 0.2}])),
        L("c10-03", "In 1931, in Los Angeles, a woman named Esther Carlson was charged with poisoning an eighty-one-year-old man, August Lindstrom, for two thousand dollars.",
          TODO("Los Angeles, 1931")),
        L("c10-04", "She died of tuberculosis before her trial.", SAME),
        L("c10-05", "Two people who had once lived in La Porte looked at her body and said it was Belle. In her trunk were photographs of three children.",
          P("belle-03.jpg", fit="print", z=[1.0, 1.1])),
        L("c10-06", "Esther Carlson had always denied it. Nothing ever proved it.", P("belle-08.jpg", fit="contain", z=[1.0, 1.08]), gap=1.0),
    ]),

    # ------------------------------------------------------------------ 11. The DNA
    dict(id="c11", music="dna", card=dict(type="chapter", n=11, title="The DNA", sub="2007 – 2008"), lines=[
        L("c11-01", "In 2007, a team from the University of Indianapolis set out to answer the question with science.", TODO("University of Indianapolis / lab")),
        L("c11-02", "It was led by Andrea Simmons, a graduate student, a lawyer, and a La Porte native, with forensic anthropologist Stephen Nawrocki.", SAME),
        L("c11-03", "On November fifth, 2007, they opened the grave at Forest Home Cemetery near Chicago, where the headless woman was buried beside Mads Sorenson.",
          TODO("Forest Home Cemetery")),
        L("c11-04", "Inside the casket, with the woman's bones, they found the remains of two children no one had expected.", SAME, gap=0.8),
        L("c11-05", "They hoped to match DNA from the bones with saliva on envelopes Belle had licked a century before.", TODO("envelope / letters")),
        L("c11-06", "But the samples were too old and too degraded. The tests were inconclusive.", BIG("Inconclusive", cap="2008"), gap=1.0),
    ]),

    # ------------------------------------------------------------------ epilogue
    dict(id="end", music="end", card=dict(type="chapter", kicker="EPILOGUE", title="La Porte", sub="Today"), tail=2.5, lines=[
        L("e01", "The house on McClung Road is long gone, and the land is private property.", P("belle-farm-14.jpg", z=[1.0, 1.1])),
        L("e02", "Belle's story is kept at the La Porte County Historical Society Museum, on Indiana Avenue.",
          TYPED("LA PORTE COUNTY HISTORICAL SOCIETY MUSEUM", ["2405 Indiana Ave., La Porte", "Tuesday to Saturday, 10 a.m. to 4:30 p.m.", "Belle Gunness exhibit"])),
        L("e03", "In 2008, a hundred years after the fire, descendants of her victims came to La Porte to put headstones on graves that had been unmarked since 1908.",
          TODO("La Porte cemetery headstones")),
        L("e04", "Andrew Helgelien lies in Patton Cemetery. His stone calls him the last victim.", SAME),
        L("e05", "Most of the others were never named.", dict(type="dark"), gap=1.0),
        L("e06", "Whether Belle Gunness died in that fire, or walked away into the dark and lived out her life under another name, no one has ever proved.",
          P("belle-08.jpg", z=[1.02, 1.25], f0=[0.42, 0.42], f1=[0.42, 0.40])),
        L("e07", "More than a hundred years later, La Porte is still asking.", SAME, gap=1.5),
        L("e08", None, QUOTE("Sources, photo credits and the museum's November 7 program are in the description.", None, size=46), hold=5.0),
    ]),
]


def build():
    script = {"title": "Belle Gunness: The Black Widow of La Porte", "chapters": CHAPTERS}
    json.dump(script, open(os.path.join(HERE, "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    words = sum(len(ln.get("say", "").split()) for ch in CHAPTERS for ln in ch["lines"])
    print(len(CHAPTERS), "chapters,", sum(len(ch["lines"]) for ch in CHAPTERS), "lines,", words, "words")


if __name__ == "__main__":
    build()
