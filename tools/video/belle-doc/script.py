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
MV = "gunness-45-hi.jpg"          # a 1908 postcard of numbered photos from the case (its legend names each one)
MVC = {
    "smith": [0.249, 0.032, 0.339, 0.258], "schell": [0.343, 0.030, 0.432, 0.262], "smutzer": [0.249, 0.268, 0.336, 0.462],
    "grand_jury": [0.338, 0.272, 0.528, 0.460], "asle": [0.251, 0.470, 0.340, 0.700], "andrew": [0.343, 0.470, 0.434, 0.704],
    "sheriff_coroner": [0.437, 0.468, 0.582, 0.610], "jury": [0.536, 0.178, 0.757, 0.347], "teeth": [0.682, 0.360, 0.788, 0.458],
    "miner": [0.682, 0.470, 0.800, 0.597], "jennie": [0.707, 0.752, 0.798, 0.970], "maxson": [0.802, 0.752, 0.896, 0.970],
    "grave": [0.899, 0.792, 0.981, 0.970], "lamphere_jail": [0.794, 0.032, 0.885, 0.265], "check": [0.255, 0.855, 0.414, 0.970],
    "fire_out": [0.337, 0.708, 0.434, 0.843], "discovery": [0.438, 0.617, 0.523, 0.843], "lamphere": [0.662, 0.032, 0.79, 0.168],
}


def MVP(key, **kw):
    """One photo from the multiview postcard, as a print on the desk."""
    d = dict(fit="print", tone="sepia", z=[1.0, 1.08], rot=0.0)
    d.update(kw)
    return P(MV, crop=MVC[key], **d)


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
        L("o03", "At first, everyone believed the woman was their mother. A widow named Belle Gunness.",
          P("belle-08.jpg", fit="print", z=[1.0, 1.12])),
        L("o04", "Then the digging began.", P("belle-farm-05.jpg", z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.4, 0.62]), gap=0.8,
          sfx=[["thud", 0.9]]),
        L("o05", "Behind the house, in a buried garbage pit, they found a farmer who had come all the way from South Dakota to marry her.",
          P("belle-farm-03.jpg", z=[1.0, 1.15], f0=[0.55, 0.5], f1=[0.6, 0.45])),
        L("o06", "Then they found more.", P("belle-farm-09.jpg", z=[1.05, 1.18]), gap=0.9),
        L("o07", "For years, men had been answering a lonely widow's ads in the newspapers. Many of them were never seen again.",
          dict(type="ad", head="PERSONAL.", text=AD_TEXT, sync=False, z=[1.0, 1.25]), lower="As printed in the Omaha Daily Bee | May 8, 1908"),
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
          MAP(**NOR, cam0=[9.0, 61.0, 34], cam1=[10.6, 63.0, 15], title="NORWAY", move_end=0.85,
              places=[{"name": "Selbu", "at": [11.03, 63.22], "show": 0.45}, {"name": "Trondheim", "at": [10.39, 63.43], "show": 0.6, "size": 44, "off": [-210, -40]}])),
        L("c1-02", "She was the youngest of eight children. Her father was a cottar, a tenant who worked another family's land, and a stonecutter.",
          P("selbu-04.jpg", tone="bw", crop=[0.0, 0.10, 1.0, 0.86], z=[1.0, 1.12], f0=[0.55, 0.55], f1=[0.5, 0.5]), lower="Selbu, Norway"),
        L("c1-03", "As a teenager she herded cattle and milked cows on the neighbors' farms, and saved for one thing: a ticket to America.",
          P("selbu-01-hi.jpg", tone="bw", crop=[0.02, 0.36, 0.475, 0.80], z=[1.0, 1.1], f0=[0.4, 0.5], f1=[0.55, 0.5])),
        L("c1-04", "In Selbu, a story has been told about her: that as a young woman she was attacked at a dance, lost the baby she was carrying, and was never the same. There's no record that it happened.",
          QUOTE("A story told in Selbu", None, font="fell-it", size=70), gap=0.6),
        L("c1-05", "In 1881, at twenty-one, she crossed the Atlantic to join her older sister in Chicago.",
          [MAP(**NOR, cam0=[-20, 55, 70], cam1=[-38, 50, 95], title="1881", move_end=0.6,
              route=[[11.03, 63.22], [10.39, 63.43], [7.0, 62.6], [4.5, 61.2], [1.5, 57.5], [-0.33, 53.74], [-2.98, 53.41], [-6.0, 52.0],
                     [-25, 50], [-50, 44], [-74.0, 40.7], [-80.0, 41.4], [-87.63, 41.88]],
              route_from=0.08, route_to=0.92,
              places=[{"name": "Selbu", "at": [11.03, 63.22], "show": 0.0}, {"name": "New York", "at": [-74.0, 40.7], "show": 0.7},
                      {"name": "Chicago", "at": [-87.63, 41.88], "show": 0.88},
                      {"name": "ATLANTIC OCEAN", "at": [-38, 47], "dot": 0, "font": "fell-sc", "size": 50, "tracking": 8}], w=2.4),
           P("gunness-44.jpg", fit="print", tone="bw", z=[1.0, 1.08], lower="Her sister, Nellie Larson | Chicago, about 1908")], gap=1.1),
        L("c1-06", "In America, Brynhild became Bella, or Belle.",
          P("castle-garden2-01.jpg", tone="bw", crop=[0.0, 0.0, 1.0, 0.93], z=[1.0, 1.14], f0=[0.5, 0.45], f1=[0.62, 0.6]),
          lower="Castle Garden, New York | where immigrants landed", gap=0.7),
    ]),

    # ------------------------------------------------------------------ 2. Chicago
    dict(id="c2", music="chicago", card=dict(type="chapter", n=2, title="Chicago", sub="1881 – 1900"), lines=[
        L("c2-01", "Chicago in the 1880s was one of the fastest-growing cities in the world, and home to more Norwegians than any other city in America.",
          [P("chicago-1880s-01.jpg", tone="bw", crop=[0.0, 0.0, 1.0, 0.94], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.42, 0.55]),
           P("chicago-1880s-28.jpg", tone="bw", crop=[0.0, 0.0, 1.0, 0.93], z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.5, 0.55]),
           P("chicago-1890s-27.jpg", fit="print", tone="bw", z=[1.0, 1.08])], lower="Chicago | 1880s and 1890s"),
        L("c2-02", "Belle worked as a servant. In 1884 she married a fellow Norwegian, Mads Sorenson.",
          TYPED("CHICAGO, 1884", ["Bella Petersen, servant girl,", "marries Mads Ditlev Anton Sorenson,", "a Norwegian from Drammen."])),
        L("c2-03", "They opened a candy store. It caught fire. The insurance paid.",
          NEWS("news-39-a.jpg", mode="zoom", box=[0.385, 0.146, 0.668, 0.178], hold=0.3, spot=[0.388, 0.1505, 0.666, 0.1755], spot_at=0.45),
          lower="A 1908 timeline of the case | Turner County Herald (Hurley, S.D.), May 14, 1908", sfx=[["fire", 1.5]]),
        L("c2-04", "Over the years, the candy store and two of their homes burned. Each time, Belle collected.",
          NEWS("news-39-a.jpg", mode="hold", box=[0.385, 0.166, 0.668, 0.198], spot=[0.388, 0.1505, 0.666, 0.1925], spot_at=0.0)),
        L("c2-05", "Two children in the Sorensons' care, Caroline and Axel, died as babies. Doctors blamed an inflammation of the bowel, which can also be a sign of poison. Both children were insured.",
          dict(type="names", head="DIED IN INFANCY", names=[["Caroline", "1896"], ["Axel", "1898"]])),
        L("c2-06", "They were also raising two little girls, Myrtle and Lucy, and an older foster daughter, Jennie Olson.",
          P("belle-05.jpg", z=[1.0, 1.12], f0=[0.55, 0.45], f1=[0.62, 0.5]), credit="Photo: Library of Congress, Bain Collection (public domain)"),
        L("c2-07", "On July thirtieth, 1900, Mads came home with a headache. Belle said she gave him a powder for it. Then he died.",
          P("chicago-1880s-19.jpg", fit="print", tone="bw", z=[1.0, 1.1])),
        L("c2-08", "It was the one day on which two of his life insurance policies overlapped: the old one ending, and a new, bigger one beginning.",
          BIG("July 30, 1900", cap="the one day two life insurance policies overlapped")),
        L("c2-09", "One doctor suspected poison. Another blamed his heart. There was no autopsy, and no charges.",
          TYPED("MADS SORENSON, 1900", ["One doctor: poison?", "Another: his heart.", "Autopsy: none.", "Charges: none."])),
        L("c2-10", "Belle collected on both policies: by most accounts, eight thousand five hundred dollars.",
          BIG("$8,500", cap="by most accounts")),
        L("c2-11", "She used it to buy a farm about fifty miles east of Chicago, outside La Porte, Indiana.",
          MAP(map="midwest", cam0=[-87.15, 41.8, 2.3], cam1=[-87.0, 41.72, 1.5], move_end=0.9,
              route=[[-87.63, 41.88], [-87.4, 41.62], [-87.0, 41.6], [-86.72, 41.61]], route_from=0.15, route_to=0.85,
              places=MIDWEST_PLACES), gap=0.7),
    ]),

    # ------------------------------------------------------------------ 3. The farm
    dict(id="c3", music="farm", card=dict(type="chapter", n=3, title="McClung Road", sub="La Porte, Indiana · 1901"), lines=[
        L("c3-01", "In November 1901, Belle moved to La Porte with Jennie, Myrtle and Lucy.",
          P("laporte-08.jpg", fit="contain", z=[1.0, 1.08]), lower="La Porte, Indiana"),
        L("c3-02", "The farm sat at the north edge of town, on McClung Road: more than forty acres, a big brick house, a barn, and an orchard.",
          [P("belle-farm-02.jpg", z=[1.0, 1.12], f0=[0.45, 0.55], f1=[0.55, 0.5], w=1.5), P("belle-farm-06.jpg", fit="print", z=[1.0, 1.08])]),
        L("c3-03", "La Porte was a busy factory town. Out on her farm, Belle worked hard.",
          [P("laporte-cat-01.jpg", tone="paper", crop=[0.08, 0.02, 0.97, 0.66], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.55, 0.45]),
           P("laporte-11.jpg", z=[1.0, 1.1])]),
        L("c3-04", "Within months, she married again. On April first, 1902, at the First Baptist Church in La Porte, she wed Peter Gunness, a Norwegian widower who had once boarded with her family in Chicago.",
          TYPED("LA PORTE, APRIL 1, 1902", ["Married: Belle Sorenson", "and Peter Gunness, a widower,", "at the First Baptist Church."])),
        L("c3-05", "Peter brought his two little daughters. Within about a week, the baby died in Belle's care, while Peter was out of the house. The death was put down to fluid in the lungs.",
          P("belle-farm-07.jpg", z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.42, 0.55])),
        L("c3-06", "On December sixteenth, 1902, Peter died too.", BIG("December 16, 1902", file="gunness-30.jpg", tone="bw"), gap=0.7),
        L("c3-07", "Belle said a heavy sausage grinder had fallen from a high shelf and struck him on the head.",
          QUOTE("A sausage-grinding machine fell on his head, she wrote.", "Peter's brother Gus, to reporters in 1908")),
        L("c3-08", "The coroner was suspicious. He weighed the grinder, measured how far it could have fallen, and decided the blow could have killed him.",
          TYPED("THE CORONER, DECEMBER 1902", ["Weighed the grinder.", "Measured the fall.", "Called a jury.", "Verdict: Belle cleared."])),
        L("c3-09", "An inquest cleared Belle, and she collected about three thousand dollars in life insurance.",
          BIG("$3,000", cap="life insurance, about")),
        L("c3-10", "Peter's brother came and took his surviving daughter, Swanhild, away with him.",
          P("gunness-51.jpg", z=[1.0, 1.12], f0=[0.5, 0.6], f1=[0.5, 0.45])),
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
          MVP("jennie", z=[1.0, 1.1]), gap=0.7),
        L("c4-04", "By then, Belle was writing letters. A lot of them. Her mail carrier said she sent eight to ten a day.",
          BIG("8 to 10 letters a day", cap="by her mail carrier's count", size=130)),
        L("c4-05", "She was placing ads in the marriage columns of newspapers, many of them Norwegian-language papers read by farmers all over the Midwest.",
          [NEWS("bee-0508.jpg", mode="zoom", box=[0.042, 0.094, 0.178, 0.128], hold=0.3),
           NEWS("bee-0508.jpg", mode="hold", box=[0.040, 0.245, 0.180, 0.305], spot=[0.044, 0.2485, 0.178, 0.3015], spot_at=0.1)],
          lower="The Omaha Daily Bee | May 8, 1908"),
        L("c4-06", "One ad, printed in 1908 as hers, read: " + AD_TEXT,
          dict(type="ad", head="PERSONAL.", text=AD_TEXT, z=[1.05, 1.3]), gap=0.8, sfx=[["page", 0.0]],
          lower="As printed in the Omaha Daily Bee | May 8, 1908"),
        L("c4-07", "Men answered. Farmers and laborers, most of them Norwegian immigrants like her, many of them with savings.",
          MAP(map="plains", cam0=[-92.0, 44.2, 18], title="THE SUITORS",
              places=SUITOR_PLACES + [{"name": "Elbow Lake, Minn.", "at": [-95.98, 45.99], "show": 0.25},
                                      {"name": "Scandinavia, Wis.", "at": [-89.15, 44.46], "show": 0.42, "off": [18, 14]},
                                      {"name": "Iola, Wis.", "at": [-89.13, 44.51], "show": 0.55, "off": [18, -70]},
                                      {"name": "Aberdeen, S.D.", "at": [-98.49, 45.46], "show": 0.68}])),
        L("c4-08", "She told them what to do. Sell everything. Bring cash. Sew the money into your clothes. Tell no one.",
          TYPED("WHAT SHE ASKED", ["Sell everything.", "Bring cash.", "Sew the money into your clothes.", "Tell no one."])),
        L("c4-09", "John Moe came from Elbow Lake, Minnesota, reportedly with more than a thousand dollars. He was never seen alive again.",
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
        L("c4-12", "When his sons wrote to ask where he was, Belle answered that he had never arrived.",
          TYPED("OLE BUDSBERG", ["Last seen: La Porte Savings Bank, April 1907.", "His sons wrote to Belle.", "Her answer: he never arrived."]), gap=0.8),
    ]),

    # ------------------------------------------------------------------ 5. Andrew
    dict(id="c5", music="suitors", card=dict(type="chapter", n=5, title="Andrew", sub="1906 – 1908"), lines=[
        L("c5-01", "In 1906, a bachelor farmer from near Aberdeen, South Dakota, answered one of Belle's ads. His name was Andrew Helgelien.",
          [MAP(map="plains", cam0=[-93.0, 44.0, 19], title="1906", route=[[-98.49, 45.46], [-95.0, 44.0], [-90.0, 42.5], [-86.72, 41.61]],
              route_from=0.3, route_to=0.95, places=SUITOR_PLACES + [{"name": "Aberdeen, S.D.", "at": [-98.49, 45.46], "show": 0.05}], w=2.0),
           MVP("andrew", lower="Andrew Helgelien | of Mansfield, South Dakota")]),
        L("c5-02", "For sixteen months, they wrote to each other.", NEWS("news-23-a.jpg", mode="clip", box=[0.0, 0.02, 0.5, 0.40], size=[0.8, 0.84], z=[1.0, 1.1]), lower="The Washington Herald | May 10, 1908"),
        L("c5-03", "In one letter, she told him how to carry his money, sewn inside his underwear, and wrote: Do not say one word about it to anyone, not even your nearest relative.",
          dict(type="letter", greeting="My dear friend, \u2026", text="Do not say one word about it to anyone, not even your nearest relative.", sync=False,
               by="Belle Gunness to Andrew Helgelien, Nov. 22, 1906 (translated from Norwegian)")),
        L("c5-04", "In another, she wrote: I do not think you will leave me after you have first come here. That I am sure of.",
          dict(type="letter", text="I do not think you will leave me after you have first come here; that I am sure of.", sync=False,
               by="Belle Gunness to Andrew Helgelien, undated letter (translated from Norwegian)"), gap=0.9),
        L("c5-05", "In early January 1908, Andrew came to La Porte. He told his brother he'd be home in a week.",
          P("belle-farm-14.jpg", tone="bw", z=[1.0, 1.1]), lower="La Porte | January 1908"),
        L("c5-06", "He had his savings, nearly three thousand dollars, sent to a bank in La Porte. Belle took the money in cash.",
          [BIG("nearly $3,000", cap="Andrew Helgelien's savings"),
           MVP("check", box=[0.82, 0.62], z=[1.0, 1.1], lower="Andrew Helgelien's check | First National Bank, La Porte, January 1908")]),
        L("c5-07", "The next day, Andrew was gone.", P("gunness-67.jpg", tone="bw", crop=[0.03, 0.04, 0.97, 0.95], z=[1.05, 1.2]), gap=1.0),
        L("c5-08", "Someone else was watching: Belle's hired man, Ray Lamphere. By most accounts he was in love with her, and jealous of Andrew.",
          MVP("lamphere", box=[0.8, 0.7], lower="Ray Lamphere | on a 1908 postcard")),
        L("c5-09", "In February 1908, Belle fired him. Then she went after him: she had him arrested for trespassing, tried to get a peace bond against him, and asked to have him declared insane.",
          TYPED("BELLE AND RAY LAMPHERE, 1908", ["February: she fired him.", "Then: arrested for trespassing,", "a peace bond sought against him,", "a request to declare him insane."])),
        L("c5-10", "Back in South Dakota, Andrew's brother, Asle, kept writing, asking where Andrew had gone.",
          MVP("asle"), lower="Asle Helgelien | Andrew's brother"),
        L("c5-11", "Belle wrote back that Andrew had gone away, perhaps to Norway, and suggested Asle sell his brother's stock and come help her look.",
          QUOTE("Sell your brother's stock and come here and we will hunt your brother together.", "The gist of Belle's letters to Asle, as the Omaha Daily Bee summed it up, May 8, 1908")),
        L("c5-12", "She was still writing to other men. On March first, 1908, she told a man in Kansas City that she was a lonely Norwegian woman, and asked whether he could put up a thousand dollars in cash.",
          dict(type="letter", text="I am a lonely Norwegian woman.", sync=False,
               by="Belle Gunness to Christian Hansen, March 1, 1908, as printed in the Morning Oregonian")),
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
          MVP("maxson", tone="bw"), lower="Joe Maxson | the hired man", sfx=[["fire", 2.0]]),
        L("c6-02", "He shouted for Belle and the children. No one answered. He ran for help.",
          P("gunness-66.jpg", tone="night", crop=[0.03, 0.05, 0.97, 0.80], z=[1.0, 1.16], f0=[0.5, 0.55], f1=[0.5, 0.45])),
        L("c6-03", "By the time the fire was out, the big brick house had collapsed into its own cellar.",
          [MVP("fire_out", z=[1.0, 1.1]), P("belle-farm-13.jpg", z=[1.0, 1.12], f0=[0.5, 0.65], f1=[0.5, 0.6])]),
        L("c6-04", "In the ruins, searchers found four bodies: Myrtle, eleven. Lucy, nine. Philip, five. And a woman, without a head.",
          dict(type="names", head="FOUND IN THE CELLAR", names=[["Myrtle", "11"], ["Lucy", "9"], ["Philip", "5"], ["a woman, head missing", ""]], span=0.85), gap=1.0),
        L("c6-05", "That same day, the sheriff went looking for Ray Lamphere. By evening, according to the newspapers, he was under arrest, charged with murdering Belle Gunness and her children.",
          P("belle-13.jpg", fit="contain", z=[1.0, 1.1]), lower="Ray Lamphere | 1908"),
        L("c6-06", "Lamphere said he had only seen the fire as he passed by on his way to work.", SAME),
        L("c6-07", "The first newspaper stories called it a tragedy: a widow and her children, burned in their beds.",
          NEWS("bee-0429.jpg", mode="zoom", box=[0.695, 0.715, 0.832, 0.812], hold=0.3, spot=[0.697, 0.7185, 0.830, 0.7475], spot_at=0.55),
          lower="The Omaha Daily Bee | April 29, 1908"),
        L("c6-08", "That story lasted one week.", SAME, gap=1.2),
    ]),

    # ------------------------------------------------------------------ 7. The hog lot
    dict(id="c7", music="digging", card=dict(type="chapter", n=7, title="The Hog Lot", sub="May 1908"), lines=[
        L("c7-01", "In early May, a stranger walked into the sheriff's office. It was Asle Helgelien, from South Dakota, with a stack of Belle's letters to his brother.",
          [MVP("smutzer", tone="bw", lower="Sheriff Albert Smutzer"), MVP("asle", tone="bw", w=1.4)]),
        L("c7-02", "He didn't believe Andrew had simply left.", SAME),
        L("c7-03", "Joe Maxson remembered something. In March, Belle had him fill and level a pit of garbage near the hog lot.",
          [P("belle-farm-03.jpg", z=[1.0, 1.12], f0=[0.5, 0.55], f1=[0.58, 0.5]), P("gunness-36.jpg", fit="print", z=[1.0, 1.08])]),
        L("c7-04", "On May fifth, 1908, they dug there.", BIG("May 5, 1908", file="belle-farm-05.jpg"), sfx=[["thud", 1.2]]),
        L("c7-05", "Wrapped in sacks, they found the remains of Andrew Helgelien.", MVP("discovery", z=[1.0, 1.1])),
        L("c7-06", "Nearby, two feet beneath him by one newspaper's account, lay Jennie Olson, the foster daughter who had supposedly gone away to school.", MVP("jennie", tone="bw", z=[1.04, 1.14]), gap=1.0),
        L("c7-07", "They kept digging. By the next night, nine bodies had come out of the yard.", P("belle-farm-09.jpg", z=[1.0, 1.15], f0=[0.5, 0.6], f1=[0.45, 0.5])),
        L("c7-08", "Most had been cut apart. Most were men. At least two were teenagers, Jennie among them.",
          P("gunness-41.jpg", fit="print", z=[1.0, 1.1])),
        L("c7-09", "Searchers recovered the remains of at least a dozen people from the farm. Only a few were ever named: Andrew Helgelien. Jennie Olson. Ole Budsberg. John Moe, and possibly Henry Gurholdt.",
          dict(type="names", head="IDENTIFIED", names=[["Andrew Helgelien", "Mansfield, South Dakota"], ["Jennie Olson", "her foster daughter"],
                                                         ["Ole Budsberg", "Iola, Wisconsin"], ["John Moe", "Elbow Lake, Minnesota"],
                                                         ["Henry Gurholdt (possibly)", "Scandinavia, Wisconsin"]], span=0.8)),
        L("c7-10", "The rest were never named. Seven of them were buried in La Porte's potter's field. And the farm was never thoroughly searched.", P("gunness-43.jpg", z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.45, 0.55])),
        L("c7-11", "Most researchers say she killed at least fourteen people. Some believe it was twenty-five or more. The number you'll often hear, more than forty, comes from legend.",
          TYPED("HOW MANY?", ["At least 14: most researchers.", "25 or more: some researchers.", "More than 40: legend."]), gap=0.9),
        L("c7-12", "And the whole country was watching La Porte.",
          dict(type="pile", items=[{"file": "news-04-a.jpg"}, {"file": "news-05-a.jpg"}, {"file": "news-02-a.jpg", "width": 0.27},
                                   {"file": "news-01-a.jpg", "width": 0.30}, {"file": "news-35-a.jpg", "width": 0.27}, {"file": "news-37-a.jpg", "width": 0.25},
                                   {"file": "news-06-a.jpg", "width": 0.33}], span=0.85), gap=0.8),
        L("c7-13", "On Sunday, May tenth, thousands of people came out to the farm. The railroads and trolleys alone brought about four thousand more into town.",
          [P("gunness-21.jpg", tone="warm", crop=[0.03, 0.04, 0.97, 0.94], z=[1.0, 1.1]), P("belle-farm-04.jpg", z=[1.0, 1.12]), NEWS("news-16-a.jpg", mode="clip")],
          lower="The Gunness farm | May 1908", sfx=[["crowd", 0.0]]),
        L("c7-14", "Peddlers at the gate sold lemonade and lunches, and souvenir pictures. The best seller was a photograph of Belle and her three children.",
          P("gunness-71.jpg", fit="print", z=[1.0, 1.12], f0=[0.5, 0.45]), gap=0.9),
    ]),

    # ------------------------------------------------------------------ 8. Was it Belle?
    dict(id="c8", music="doubt", card=dict(type="chapter", n=8, title="Was It Belle?", sub="May 1908"), lines=[
        L("c8-01", "But was the woman in the cellar really Belle?", P("belle-07.jpg", fit="contain", z=[1.0, 1.1]), gap=0.7),
        L("c8-02", "Her head was never found.", SAME, gap=0.9),
        L("c8-03", "Neighbors, and at least one local doctor who knew her, said the body was far too small to be hers. Other doctors said the fire could explain it.",
          P("belle-farm-15.jpg", z=[1.15, 1.3], f0=[0.5, 0.75], f1=[0.5, 0.7])),
        L("c8-03b", "In 1908, the coroner guessed its height at five foot three. Belle was about five foot eight. A century later, scientists' first estimate from the skeleton was five foot six to five foot nine. Without the head, none of it proved anything.",
          TYPED("THE WOMAN IN THE CELLAR", ["1908, the coroner's guess: about 5 ft. 3 in.", "Belle Gunness: about 5 ft. 8 in.", "2007, from the bones: 5'6\" to 5'9\"."])),
        L("c8-04", "A Chicago chemist later reported finding poison in the stomachs of the woman and two of the children.",
          TYPED("REPORTED IN 1908", ["Dr. Walter Haines, Rush Medical College:", "arsenic and strychnine."])),
        L("c8-05", "The sheriff and a miner named Louis Schultz washed the ashes through a sluice, like gold.",
          [P("gunness-64.jpg", fit="print", z=[1.0, 1.08]), MVP("miner", z=[1.0, 1.1])]),
        L("c8-06", "On May nineteenth, they found two dental plates with false teeth. Belle's dentist said they were hers.",
          MVP("teeth", box=[0.8, 0.62], z=[1.0, 1.12]), lower="May 19, 1908 | the teeth, on a 1908 postcard", sfx=[["camera", 0.8]]),
        L("c8-07", "The sheriff said it proved, beyond the shadow of a doubt, that Belle had died in the fire. The coroner agreed.",
          QUOTE("beyond the shadow of a doubt", "Sheriff Albert Smutzer, May 1908")),
        L("c8-08", "Not everyone did. The teeth had come through a fire that destroyed a house, and they were in good shape. Many people believed they had been planted.",
          P("belle-08.jpg", fit="print", z=[1.0, 1.1])),
        L("c8-09", "Three days later, a grand jury indicted Ray Lamphere for arson and murder. It also indicted Belle Gunness, for the murder of Andrew Helgelien, though the coroner had just declared her dead.",
          [MVP("grand_jury", box=[0.84, 0.70], z=[1.0, 1.1], lower="The grand jury | 1908"), NEWS("news-58-b.jpg", mode="clip", size=[0.7, 0.8], lower="The Washington Herald | May 23, 1908")], gap=1.0),
    ]),

    # ------------------------------------------------------------------ 9. The trial
    dict(id="c9", music="trial", card=dict(type="chapter", n=9, title="The Trial", sub="November 1908"), lines=[
        L("c9-01", "Ray Lamphere went on trial in November 1908, at the La Porte County Courthouse.",
          NEWS("paper-nov-04-a.jpg", mode="clip", size=[0.88, 0.80], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.42, 0.45]), lower="The Spokane Press | Nov. 9, 1908"),
        L("c9-02", "As the jury was chosen, six men were excused because they believed Belle Gunness was still alive.",
          MVP("jury", box=[0.84, 0.72], z=[1.0, 1.12]), lower="The jury that tried Ray Lamphere | November 1908"),
        L("c9-03", "Lamphere's lawyer, Wirt Worden, argued that she was.",
          NEWS("paper-nov-05-a.jpg", mode="clip", size=[0.62, 0.82], z=[1.0, 1.1]), lower="The Washington Times | Nov. 10, 1908"),
        L("c9-03b", "Prosecutors had a watch Lamphere was carrying when he was arrested. John Moe's half-brother said it was Moe's. Lamphere said Belle had given it to him.",
          TYPED("THE WATCH", ["Found on Ray Lamphere.", "John Moe's, said Moe's half-brother.", "A gift from Belle, said Lamphere."])),
        L("c9-04", "Defense witnesses said they had seen Belle, alive, that summer.", P("belle-07.jpg", fit="print", z=[1.0, 1.1])),
        L("c9-05", "On Thanksgiving Day, November twenty-sixth, the jury gave its verdict: not guilty of murder. Guilty of arson.",
          BIG("Guilty of arson", cap="November 26, 1908"), sfx=[["gavel", 3.0]]),
        L("c9-05b", "The poison found in the bodies may have helped him. His lawyer argued that it showed Lamphere had nothing to do with their deaths.", SAME),
        L("c9-06", "He was sentenced to two to twenty-one years in the state prison at Michigan City.", P("prison-33.jpg", tone="warm", crop=[0.02, 0.03, 0.98, 0.78], z=[1.0, 1.1], f0=[0.4, 0.5], f1=[0.55, 0.5]), lower="Indiana State Prison | Michigan City, about 1908"),
        L("c9-07", "He served about a year. On December thirtieth, 1909, Ray Lamphere died of tuberculosis.", MVP("lamphere_jail", tone="bw"), gap=0.8),
        L("c9-08", "After his death, newspapers printed what they called his confession. In it, he said he had chloroformed Belle and the children while he and a woman robbed the house, and that the body in the cellar was Belle.",
          [dict(type="pile", items=[{"file": "paper-1910-03-a.jpg", "width": 0.26}, {"file": "paper-1910-02-a.jpg", "width": 0.30},
                                    {"file": "paper-1910-07-a.jpg", "width": 0.24}], span=0.8, credit="Newspapers, January 1910 \u00b7 Library of Congress", w=1.0),
           NEWS("paper-1910-04-a.jpg", mode="clip", size=[0.55, 0.86], z=[1.0, 1.14], f0=[0.5, 0.35], f1=[0.5, 0.62], w=1.4,
                lower="Evening Times-Republican (Marshalltown, Iowa) | Jan. 13, 1910")]),
        L("c9-08b", "The minister he had confided in said he had never repeated a word of what Lamphere told him.",
          MVP("schell"), lower="The Rev. Edwin A. Schell"),
        L("c9-09", "Other men told other stories. That Lamphere had helped her escape. That the woman in the cellar was a housekeeper lured from Chicago. That Belle had killed forty-two men.",
          TYPED("WHAT OTHERS SAID HE SAID", ["He helped her escape.", "The body was a housekeeper from Chicago.", "She killed 42 men."])),
        L("c9-10", "All of these stories, the printed confession included, came secondhand, after Lamphere was dead, and they contradict each other.", SAME, gap=1.0),
    ]),

    # ------------------------------------------------------------------ 10. Sightings
    dict(id="c10", music="sightings", card=dict(type="chapter", n=10, title="Sightings", sub="1908 – 1931"), lines=[
        L("c10-01", "Within days of the bodies being found, people started seeing Belle Gunness.",
          MAP(map="usa", cam0=[-97, 41.0, 62], title="SIGHTINGS", places=[{"name": "La Porte", "at": [-86.72, 41.61], "show": 0.0}])),
        L("c10-02", "In Syracuse. In Tacoma. For more than twenty years, letters reached La Porte from all over the country.",
          MAP(map="usa", cam0=[-97, 41.0, 62], title="SIGHTINGS", places=[{"name": "La Porte", "at": [-86.72, 41.61], "show": 0.0},
              {"name": "Syracuse", "at": [-76.15, 43.05], "show": 0.05}, {"name": "Tacoma", "at": [-122.44, 47.25], "show": 0.2}])),
        L("c10-03", "In 1931, in Los Angeles, a woman named Esther Carlson was charged with poisoning an eighty-one-year-old man, August Lindstrom, for two thousand dollars.",
          MAP(map="usa", cam0=[-97, 41.0, 62], cam1=[-112, 36.5, 30], title="1931", move_end=0.5,
              places=[{"name": "La Porte", "at": [-86.72, 41.61], "show": 0.0}, {"name": "Syracuse", "at": [-76.15, 43.05], "show": 0.0},
                      {"name": "Tacoma", "at": [-122.44, 47.25], "show": 0.0}, {"name": "Los Angeles", "at": [-118.24, 34.05], "show": 0.3}])),
        L("c10-04", "She died of tuberculosis before her trial.", SAME),
        L("c10-05", "Two people who had once lived in La Porte looked at her body and said it was Belle. In her trunk were photographs of three children.",
          P("belle-03.jpg", fit="print", z=[1.0, 1.1])),
        L("c10-06", "Esther Carlson had always denied it. She said she had been working in Hartford, Connecticut, the whole time. Her remains have never been tested.",
          P("belle-08.jpg", fit="contain", z=[1.0, 1.08]), gap=1.0),
    ]),

    # ------------------------------------------------------------------ 11. The DNA
    dict(id="c11", music="dna", card=dict(type="chapter", n=11, title="The DNA", sub="2007 – 2008"), lines=[
        L("c11-01", "In 2007, a team from the University of Indianapolis set out to answer the question with science.",
          P("uindy-02.jpg", tone="sepia-soft", z=[1.0, 1.1], f0=[0.5, 0.45], f1=[0.5, 0.5]), lower="University of Indianapolis | today"),
        L("c11-02", "It was led by Andrea Simmons, a graduate student, a lawyer, and a La Porte native, with forensic anthropologist Stephen Nawrocki.",
          TYPED("THE TEAM, 2007", ["Andrea Simmons: graduate student,", "lawyer, La Porte native.", "Stephen Nawrocki:", "forensic anthropologist."])),
        L("c11-03", "On November fifth, 2007, they opened the grave at Forest Home Cemetery near Chicago, where the headless woman was buried beside Mads Sorenson.",
          P("forest-home-11.jpg", tone="sepia-soft", crop=[0.0, 0.0, 1.0, 0.56], z=[1.0, 1.1], f0=[0.5, 0.6], f1=[0.42, 0.55]), lower="Forest Home Cemetery | Forest Park, Illinois, today"),
        L("c11-04", "Inside the casket, with the woman's bones, they found the remains of two children no one had expected.",
          TYPED("THE GRAVE, 2007 AND 2008", ["Inside: the woman's bones,", "and two children no one expected.", "In one child's grave: adult bones."]), gap=0.8),
        L("c11-04b", "The next spring, when they opened the children's graves, they found adult bones in one of them.", SAME, gap=0.8),
        L("c11-05", "They hoped to match DNA from the bones with saliva on envelopes Belle may have sealed a century before.",
          TYPED("THE TEST", ["DNA from the bones,", "against saliva on the envelopes and stamps", "of letters Belle mailed to a suitor."])),
        L("c11-06", "But the samples were too old and too degraded. The tests were inconclusive.", BIG("Inconclusive", cap="2008"), gap=1.0),
    ]),

    # ------------------------------------------------------------------ epilogue
    dict(id="end", music="end", card=dict(type="chapter", kicker="EPILOGUE", title="La Porte", sub="Today"), tail=2.5, lines=[
        L("e01", "The house on McClung Road is long gone.", P("gunness-56.jpg", tone="warm", crop=[0.03, 0.12, 0.97, 0.92], z=[1.0, 1.1], f0=[0.5, 0.5], f1=[0.46, 0.55])),
        L("e02", "Belle's story is kept at the La Porte County Historical Society Museum, on Indiana Avenue.",
          TYPED("LA PORTE COUNTY HISTORICAL SOCIETY MUSEUM", ["2405 Indiana Ave., Suite 1, La Porte", "Tue.-Sat., 10 a.m.-4:30 p.m. Central", "Belle Gunness exhibit"])),
        L("e03", "In 2008, a hundred years after the fire, descendants of her victims came to La Porte to put headstones on graves that had been unmarked since 1908.",
          BIG("April 26, 2008", cap="headstones for graves unmarked since 1908")),
        L("e04", "Andrew Helgelien lies in Patton Cemetery. His stone calls him the last victim.",
          MVP("grave", z=[1.0, 1.12]), lower="Andrew Helgelien's grave | on a 1908 postcard"),
        L("e05", "Most of the others were never named.", dict(type="dark"), gap=1.0),
        L("e06", "Whether Belle Gunness died in that fire, or walked away into the dark and lived out her life under another name, no one has ever proved.",
          P("belle-08.jpg", z=[1.02, 1.22], f0=[0.42, 0.42], f1=[0.42, 0.40])),
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
