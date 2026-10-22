#!/usr/bin/env python3
"""The History of Halloween documentary's script: every narration line and the pictures shown with it.

    python3 tools/video/halloween-doc/script.py        writes script.json (what doc.py and the voice job read)

Facts come from the research files of Oct. 21, 2026 (sources in the YouTube description): Ronald Hutton's
"The Stations of the Sun" (1996) on Samhain and All Saints; Lisa Morton's "Trick or Treat" (2012); Nicholas Rogers
(2002); the Oxford English Dictionary and Merriam-Webster on the words; Robert Burns's "Halloween" (Kilmarnock, 1786)
with his own footnotes; the Dublin Penny Journal of Jan. 16, 1836; the Kingston (Ont.) Daily News of Nov. 1, 1866;
the Philadelphia Evening Telegraph of Oct. 31, 1866 and Godey's Lady's Book of Oct. 1872; the Sault Daily Star of
Nov. 1, 1917 and later papers on "trick or treat" (Barry Popik's files); Joel Best's Halloween-sadism research
(1958 on); the National Retail Federation's 2026 survey and USDA pumpkin figures; and for Indiana, the Indiana
Historical Bureau's "Devil Cats, Magic Mirrors and Fortune-Telling Cabbage" (2024), the Dictionary of American
Regional English, the Whiting-Robertsdale Historical Society, Jeff Kenney's "Spooky Spectacle" (Towne Post, 2023),
the Culver Citizen (1950, 1956), the Indianapolis Star via the Marion County Historical Society, the La Porte County
Public Library's "100 Years Ago Today," the Hesston Steam Museum, WNDU, and the National Weather Service.

Myths are stamped as myths, and what the records don't show is said plainly. La Porte's own newspapers of those
years are on microfilm, not online, so the film says so and reads the papers of La Porte's neighbors instead.
Pictures: public domain, CC0 or CC BY only, credited in the description; no stock, no AI pictures.
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
    s = re.sub(r"\b(1[5-9])(\d)0s\b", lambda m: two(int(m.group(1))) + (" hundreds" if m.group(2) == "0" else " " + TENS[int(m.group(2))][:-1] + "ies"), s)
    s = re.sub(r"\b(1[5-9]\d\d|20[0-2]\d)\b", lambda m: year_words(int(m.group(1))), s)
    s = s.replace("A.D. ", "").replace("Nov. 1", "November first").replace("Oct. 31", "October thirty-first")
    s = s.replace("$13.5 billion", "thirteen and a half billion dollars").replace("$115", "a hundred and fifteen dollars")
    s = s.replace("$3", "three dollars").replace("$40,000", "forty thousand dollar")
    s = s.replace("1.5 million", "a million and a half").replace("5 to 7", "five to seven")
    s = s.replace("83 degrees", "eighty-three degrees").replace("20 degrees", "twenty degrees").replace("35 degrees", "thirty-five degrees")
    s = s.replace("2.98 inches", "two point nine eight inches").replace("67 miles", "sixty-seven miles").replace("1.6 inches", "one point six inches")
    s = s.replace("1.4 inches", "one point four inches").replace("2.2 inches", "two point two inches")
    s = re.sub(r"\b40s\b", "forties", s).replace("6 to 2", "six to two").replace("10 p.m.", "ten p.m.")
    s = re.sub(r"\bunder 16\b", "under sixteen", s)
    s = s.replace("74 percent", "seventy-four percent").replace("No. 2", "number two").replace("No. 3", "number three")
    return s


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
    text = text.strip().strip("“”\"")           # the shot draws its own quotation marks
    return dict(type="quote", text=text, **({"by": by} if by else {}), **kw)


def TYPED(head, rows, **kw):
    return dict(type="typed", head=head, rows=rows, **kw)


def LETTER(text, by=None, greeting=None, **kw):
    d = dict(type="letter", text=text, sync=False, **kw)
    if by:
        d["by"] = by
    if greeting:
        d["greeting"] = greeting
    return d


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
DARK = {"type": "dark"}

# the three stamps (color, text) used through the film
MYTH = dict(text="MYTH", color="red")
FACT = dict(text="FACT", color="green")
UNKNOWN = dict(text="NO ONE KNOWS", color="amber", size=96)
DISPUTED = dict(text="DISPUTED", color="amber", size=104)


def TODO(desc):
    """A stand-in until the right picture is chosen."""
    return QUOTE(desc, "picture to come", size=48)


# ---------------------------------------------------------------------------------------------- places on the maps
LP = {"name": "La Porte", "at": [-86.7225, 41.6106]}
MC = {"name": "Michigan City", "at": [-86.8950, 41.7075]}
SB = {"name": "South Bend", "at": [-86.2520, 41.6764]}
HAMMOND = {"name": "Hammond", "at": [-87.5000, 41.5834]}
WHITING = {"name": "Whiting", "at": [-87.4945, 41.6798]}
CULVER = {"name": "Culver", "at": [-86.4231, 41.2189]}
INDY = {"name": "Indianapolis", "at": [-86.1581, 39.7684]}
GOSHEN = {"name": "Goshen", "at": [-85.8344, 41.5823]}
LAKE = {"name": "LAKE MICHIGAN", "at": [-87.25, 41.74], "dot": 0, "font": "fell-sc", "size": 46, "tracking": 4}
COUNTY = {"name": "LA PORTE COUNTY", "at": [-86.90, 41.52], "dot": 0, "font": "fell-sc", "size": 40, "tracking": 6}
MICH = {"name": "MICHIGAN", "at": [-86.50, 41.79], "dot": 0, "font": "fell-sc", "size": 38, "tracking": 8}
IND = {"name": "INDIANA", "at": [-86.30, 41.33], "dot": 0, "font": "fell-sc", "size": 38, "tracking": 8}


def place(p, show=0.0, **kw):
    return dict(p, show=show, **kw)


CO = dict(map="county")

# ---------------------------------------------------------------------------------------------- the pictures
# (chosen Oct. 21-22, 2026 from images/manifest*.json and the hauntings film's images)
LP_CARD = "lp-streets-04.jpg"          # "Greetings from LaPorte," 1908 postcard (hauntings film)
INDY1895 = "np-mc-06.jpg"              # Indianapolis Journal, Nov. 1, 1895

CHAPTERS = [
    # ------------------------------------------------------------------ cold open
    dict(id="open", music="open", tail=0.2, lines=[
        L("o01", "Every October, something strange happens on the streets of La Porte, Indiana.",
          P(LP_CARD, tone="sepia", crop=[0.02, 0.03, 0.98, 0.97], z=[1.0, 1.18], f0=[0.5, 0.5], f1=[0.45, 0.42]),
          lower="La Porte | a 1908 postcard", sfx=[["wind", 0.0]]),
        L("o02", "Children dressed as ghosts and witches knock on the doors of strangers and demand candy. And the strangers hand it over.",
          P("x-ford-01.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.15], f0=[0.5, 0.45], f1=[0.55, 0.42]),
          lower="Trick-or-treaters at the White House | 1974", sfx=[["knock", 0.9]]),
        L("o03", "In 1866, a Philadelphia newspaper described the same night a little differently. Among the night's amusements, it said: hanging dead cats to door-bells.",
          NEWS("phila-1866-01.jpg", mode="zoom", hold=0.3, lower="Evening Telegraph, Philadelphia | Oct. 31, 1866"), year="1866", sfx=[["page", 0.0]]),
        L("o04", "The holiday you know is about a hundred years old. The one underneath it is much, much older. And almost everything you've been told about where it came from is wrong.",
          P("burns-02.jpg", tone="sepia", crop=[0.05, 0.05, 0.95, 0.95], z=[1.0, 1.2], f0=[0.5, 0.5], f1=[0.5, 0.42]), year="",
          lower="Halloween in Scotland | an 1896 engraving for Burns's poem", stamp=dict(text="MYTH", color="red", at="wrong", until=2.6)),
        L("o05", "There was no Celtic god of the dead named Samhain. The church did not steal the date. The jack-o'-lantern was a turnip. And trick-or-treat began as a threat.",
          [P("x-coligny-02.jpg", tone="bw", crop=[0.1, 0.1, 0.9, 0.9], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.45]),
           P("allsouls-01.jpg", tone="warm", crop=[0.02, 0.05, 0.98, 0.95], z=[1.0, 1.1], f0=[0.5, 0.45], f1=[0.45, 0.45]),
           P("turnip-05.jpg", tone="night", z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.5, 0.45]),
           P("hw-us-16.jpg", tone="sepia", crop=[0.0, 0.0, 1.0, 1.0], z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.45, 0.4])]),
        L("o06", "We'll also tell you what Halloween looked like right here, in La Porte County, over a hundred and fifty years, through the newspapers of the towns around us, and the weather records of the nights themselves.",
          MAP(**CO, cam0=[-86.70, 41.55, 1.40], cam1=[-86.70, 41.55, 1.22], move_end=0.9,
              places=[LAKE, COUNTY, MICH, IND, place(MC, 0.15), place(LP, 0.3)])),
        L("o07", "This is the real history of Halloween: what's documented, what's legend, and what no one can prove.", DARK, gap=0.8),
    ]),
    dict(id="title", music="title", tail=0.3, lines=[
        L("t01", None, dict(type="title", title="THE REAL HISTORY OF HALLOWEEN", subtitle="Told through a small town's newspapers",
                             kicker="A LA PORTE WEATHER NOW DOCUMENTARY"), hold=7.5),
    ]),

    # ------------------------------------------------------------------ 1. Trick or threat
    dict(id="c1", music="threat", card=dict(type="chapter", n=1, title="Trick or Threat", sub="America · 1866 – 1909"), lines=[
        L("c1-01", "Start with the part nobody puts on a greeting card. In America, Halloween was a night of vandalism long before it was a night of candy.",
          P("pc-witch-07.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.42]),
          lower="A Halloween postcard | about 1910"),
        L("c1-02", "In 1872, Godey's Lady's Book, the best-known women's magazine in the country, complained about gangs of boys who, in its words, batter down panels, dislocate bell-wires, and unhinge gates.",
          QUOTE("“…batter down panels, dislocate bell-wires, unhinge gates…”", "Godey's Lady's Book, October 1872"), year="1872"),
        L("c1-03", "That same fall, a Terre Haute paper reported from the little town of Titusville, Indiana: gates lifted off their hinges, door-bells pulled, and a man who fell over a washtub at his own front door and got a peck of potatoes dumped on his head.",
          TYPED("TERRE HAUTE EVENING GAZETTE · NOV. 7, 1872", ["Gates unhinged.", "“Door-bells were pulled.”", "A washtub at a Main Street door; a peck of potatoes on a man's head.", "A fortune-telling chestnut that burst and hit Mary in the eye."])),
        L("c1-04", "By the 1890s and 1900s, the papers printed the same story every November first. Gates gone. Wagons on roofs. Outhouses tipped. Windows soaped.",
          [NEWS("clip-topeka-1895-1.jpg", mode="hold", lower="Topeka State Journal | Nov. 1, 1895"),
           NEWS("np-pranks-10.jpg", mode="zoom", hold=0.3, lower="Topeka State Journal | Nov. 1, 1905"),
           NEWS("np-pranks-18.jpg", mode="zoom", hold=0.3, lower="Laramie Republican | Nov. 4, 1908")], year="1895", sfx=[["page", 0.0], ["page", 3.5], ["page", 7.0]]),
        L("c1-05", "Some towns called it Cabbage Night, Gate Night, or Mischief Night. In Indianapolis, in 1891, the paper gave the night before Halloween its own name: door-bell night.",
          NEWS("indy-1891-01.jpg", mode="zoom", hold=0.3, lower="Indianapolis Journal | Nov. 2, 1891"), year="1891", sfx=[["page", 0.0]]),
        L("c1-06", "So here is the question this film is really about. How did a night of broken gates become a night when strangers give your children chocolate?",
          P("hw-us-11.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.1], f0=[0.5, 0.5], f1=[0.5, 0.45]), year=""),
        L("c1-07", "To answer that, we have to go back about twelve hundred years, to a monastery in Ireland.", DARK, gap=0.8),
    ]),

    # ------------------------------------------------------------------ 2. Samhain
    dict(id="c2", music="samhain", card=dict(type="chapter", n=2, title="Samhain", sub="What the records actually say · Ireland, the 800s"), lines=[
        L("c2-01", "You have probably heard that Halloween comes from Samhain, an ancient Celtic festival of the dead, when the veil between the worlds grew thin.",
          P("map-ireland-01.jpg", tone="paper", crop=[0.05, 0.05, 0.95, 0.95], z=[1.0, 1.2], f0=[0.5, 0.5], f1=[0.45, 0.4]),
          lower="Ireland | a 19th-century map"),
        L("c2-02", "Here is what the records actually say. The word Samhain, the first of November, appears in Irish writing from about the ninth century on.",
          P("burns-07.jpg", tone="sepia", fit="contain", z=[1.0, 1.06]), year="800s", lower="Stories of Samhain survive in Irish manuscripts copied by monks"),
        L("c2-03", "Those writings were made by Christian monks, copying stories that were already old. In them, Samhain is the start of winter, and the night when kings held their assemblies, and when strange things happen in the tales.",
          TYPED("SAMHAIN IN THE OLD IRISH TALES", ["The first of November: the start of winter.", "Kings hold their assemblies at Tara.", "The hero Fionn fights a fire-breathing enemy.", "A man named Nera walks among the dead."])),
        L("c2-04", "Archaeologists have dug at the Hill of Ward, in County Meath, where a later legend put the great Samhain fire. They found feasting bones in every layer, and heavy burning, going back about three thousand years.",
          P("map-ireland-01.jpg", tone="paper", crop=[0.45, 0.25, 0.95, 0.75], z=[1.0, 1.25], f0=[0.5, 0.5], f1=[0.6, 0.45]), year="",
          lower="County Meath, on a 19th-century map of Ireland"),
        L("c2-05", "Was that Samhain? The lead archaeologist's own words were: tempting, but difficult to conclusively prove.",
          QUOTE("“…tempting, but difficult to conclusively prove.”", "Dr. Stephen Davis, University College Dublin, on the Hill of Ward dig"), stamp=UNKNOWN),
        L("c2-06", "Now the parts that aren't true. Samhain, the Celtic god of the dead.",
          BIG("“A GOD OF THE DEAD”", cap="Samhain, said to be the source of Halloween"), stamp=dict(MYTH, at=2.4)),
        L("c2-07", "No such god appears in any Irish text. He was invented in 1786 by a British army officer named Charles Vallancey, who wrote that the Irish deity Saman was the judge of departed souls. Vallancey, a reviewer said, wrote more nonsense than any man of his time.",
          QUOTE("“…wrote more nonsense than any man of his time.”", "the Quarterly Review, on Charles Vallancey"), year="1786"),
        L("c2-08", "The Celtic New Year. That one comes from two Victorian scholars, John Rhys and James Frazer, around the turn of the last century. The historian Ronald Hutton checked the medieval records. There is no record of such a festival.",
          BIG("“CELTIC NEW YEAR”", cap="a Victorian idea, 1886 – 1901"), year="1890", stamp=dict(DISPUTED, at=3.0)),
        L("c2-09", "Druids and human sacrifice at Samhain. There is no contemporary record of any pagan Samhain rite at all. Not one.",
          BIG("DRUID SACRIFICE", cap="no record of any Samhain rite survives"), year="", stamp=dict(MYTH, at=1.8)),
        L("c2-11", "So: a real festival, at the start of winter, with real fires and real stories. A god, a new year, and a sacrifice that were added much later. That's Samhain.", DARK, gap=0.8),
    ]),

    # ------------------------------------------------------------------ 3. All Hallows
    dict(id="c3", music="hallows", card=dict(type="chapter", n=3, title="All Hallows", sub="Rome, Francia and Ireland · 609 – 1000"), lines=[
        L("c3-01", "The next thing everyone knows: the church moved All Saints' Day to the first of November to stamp out Samhain. Halloween is just All Hallows' Eve, the night before.",
          P("allsouls-01.jpg", tone="warm", crop=[0.02, 0.05, 0.98, 0.95], z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.45, 0.45]),
          lower="All Souls' Day | Ferdinand Georg Waldmüller, 1839"),
        L("c3-02", "The first half is true. Hallow means saint. Hallows' Eve is the evening before All Saints. Shorten it, the Scottish way, and you get Hallowe'en, in print by the 1700s.",
          TYPED("THE WORD", ["All Hallows = All Saints.", "All Hallows' Even = the night before.", "1584, Scotland: “alhallow even.”", "Hallowe'en: in print by the 1700s."]), year="1700"),
        L("c3-03", "The second half is where it gets interesting. Rome's first feast of all the martyrs was in May. In the year 609, Pope Boniface the Fourth dedicated the Pantheon to Mary and the martyrs, on May thirteenth.",
          BIG("MAY 13, 609", cap="Rome's feast of all the martyrs"), year="609"),
        L("c3-04", "The November date shows up in England and Germany first. By about the year 800, Charlemagne's favorite churchman, Alcuin, was keeping All Saints on the first of November. In 835, the emperor Louis the Pious made it official across his empire.",
          TYPED("NOVEMBER 1", ["England, early 700s: kept at the time of Bede.", "About 800: Alcuin, at Charlemagne's court.", "835: the emperor Louis the Pious makes it official."]), year="835"),
        L("c3-05", "Now here's the problem for the stamp-out-Samhain theory. We can check what the Irish church itself did. Its calendars show the Irish keeping All Saints on April twentieth. The November date came out of England and the Frankish empire, and Rome adopted it.",
          BIG("APRIL 20", cap="All Saints' Day in the early Irish church"), year="", stamp=dict(FACT, at="April")),
        L("c3-07", "Was it chosen to compete with a pagan festival? Some historians say yes. Hutton says the evidence points the other way. Nobody can prove it either way.",
          BIG("“THE CHURCH STOLE SAMHAIN”", cap="historians disagree; the Irish evidence says no"), stamp=dict(DISPUTED, at=3.0)),
        L("c3-08", "The second of November, All Souls' Day, for everyone who had died, was added around the year 1000 by an abbot in France. Now the church had two days for the dead, back to back, at the start of winter.",
          P("hw-sc-07.jpg", tone="sepia", crop=[0.05, 0.05, 0.95, 0.95], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.42]), year="1000"),
        L("c3-09", "And that's when the door-knocking starts. In England, from at least 1511, the poor went house to house on All Hallows asking for soul cakes, small spiced cakes, in return for prayers for the family's dead.",
          [P("souling-01.jpg", tone="warm", crop=[0.02, 0.05, 0.98, 0.95], z=[1.0, 1.1], f0=[0.5, 0.5], f1=[0.5, 0.45], lower="The Antrobus Soul Cakers, England | 1970s"),
           P("samhain-04.jpg", tone="warm", z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.5, 0.45], lower="Soul cakes")], year="1511"),
        L("c3-10", "Shakespeare knew it. In the early 1590s, one of his characters is told off for puling, like a beggar at Hallowmas.",
          QUOTE("“…puling like a beggar at Hallowmas.”", "Shakespeare, The Two Gentlemen of Verona, about 1593"), year="1593"),
        L("c3-11", "Souling. Children, at the door, asking for a treat. Four hundred years before anyone said trick or treat.", DARK, year="", gap=0.8),
    ]),

    # ------------------------------------------------------------------ 4. Jack of the lantern
    dict(id="c4", music="jack", card=dict(type="chapter", n=4, title="Jack of the Lantern", sub="Scotland, Ireland and Canada · 1785 – 1867"), lines=[
        L("c4-01", "In 1785, a Scottish farmer named Robert Burns wrote a poem called Halloween. It's our best picture of what the night was like for ordinary people.",
          P("burns-04.jpg", tone="sepia", fit="contain", z=[1.0, 1.08]), year="1785", lower="Robert Burns, “Halloween” (1785; printed 1786) | an 1841 engraving"),
        L("c4-02", "Some merry, friendly, country folks, together did convene, to burn their nits, and pull their stocks, and hold their Halloween.",
          QUOTE("“To burn their nits, an' pou their stocks, / An' haud their Halloween”", "Robert Burns, “Halloween,” 1785 (printed 1786)")),
        L("c4-03", "Burns added footnotes. Young people went out in the dark, hand in hand, eyes shut, and pulled up the first kale stalk they touched. Its shape told them the shape of their future husband or wife.",
          P("burns-05.jpg", tone="sepia", crop=[0.03, 0.03, 0.97, 0.97], z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.42, 0.5])),
        L("c4-04", "They named two nuts for a boy and a girl and set them in the fire, to see if they burned together or jumped apart. A girl took a candle, alone, to a mirror, and ate an apple, to see a face appear behind her.",
          [P("hw-us-09.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.4], lower="A Halloween postcard | about 1910"),
           P("hw-us-29.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.42])]),
        L("c4-05", "Halloween, in 1785, was a night for finding out who you'd marry. In 1833, the painter Daniel Maclise exhibited a party he'd been to the year before at Blarney, in Ireland, with the same games: bobbing for apples, snapping at an apple on a string.",
          P("x-named-06.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.18], f0=[0.5, 0.5], f1=[0.4, 0.5]), year="1833",
          lower="Snap-Apple Night | Daniel Maclise, 1833"),
        L("c4-06", "Now, the lantern. In Ireland, Scotland and the Isle of Man, people hollowed out turnips, carved faces in them, and put a candle inside. This one was carved on the Isle of Man.",
          P("turnip-05.jpg", tone="night", z=[1.0, 1.18], f0=[0.5, 0.5], f1=[0.5, 0.45]), year="", lower="A Hop-tu-Naa turnip lantern, Isle of Man | 2019"),
        L("c4-07", "A print from 1792 shows travelers terrified by one: The Affrightened Travellers, or, the Illuminated Turnip.",
          P("turnip-01.jpg", tone="warm", crop=[0.03, 0.03, 0.97, 0.9], z=[1.0, 1.2], f0=[0.5, 0.5], f1=[0.35, 0.5]), year="1792",
          lower="“Affrightened Travellers; or, the Illuminated Turnip” | Richard Newton, 1792"),
        L("c4-08", "The name jack-o'-lantern is older than the carving. In the 1600s, it meant a will-o'-the-wisp, a ghost light over a bog, and then a night watchman, a man with a lantern.",
          TYPED("JACK-O'-LANTERN", ["1658: a will-o'-the-wisp, a light over the marsh.", "1663: a night watchman, Jack with his lantern.", "1837: a carved lantern."]), year="1658"),
        L("c4-09", "And Stingy Jack, the blacksmith who tricked the Devil and was doomed to wander with a coal in a turnip? Everyone calls it ancient. The earliest printing anyone has found is in a Dublin penny weekly of 1836. And in that version, there's no lantern.",
          BIG("“STINGY JACK”", cap="earliest printing found: Dublin, 1836, with no lantern"), year="1836", stamp=dict(UNKNOWN, at=4.0)),
        L("c4-10", "Then came the famine. Between 1845 and 1855, about 1.5 million Irish people came to America. They brought the games, the fires, the guising, and the lantern. And what they found here was something bigger, and easier to carve.",
          [P("famine-01.jpg", tone="sepia", crop=[0.03, 0.03, 0.97, 0.97], z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.5, 0.45], lower="Emigrants leave Ireland | Henry Doyle, 1868"),
           P("emigrants-01.jpg", tone="sepia", crop=[0.03, 0.03, 0.97, 0.97], z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.45, 0.45], lower="Emigrants at Queenstown | 1874")], year="1845"),
        L("c4-11", "Pumpkins. The earliest dated description anyone has found of candle-lit Halloween pumpkins is from Kingston, Ontario, the day after Halloween, 1866: There was a great sacrifice of pumpkins.",
          QUOTE("“There was a great sacrifice of pumpkins.”", "Daily News, Kingston, Ontario, Nov. 1, 1866"), year="1866"),
        L("c4-12", "The earliest known picture of one was printed in Harper's Weekly the next year. So the pumpkin jack-o'-lantern, the symbol of the whole holiday, is North American, and it's about a hundred and sixty years old.",
          P("pumpkins-01.jpg", tone="warm", crop=[0.02, 0.05, 0.98, 0.95], z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.5, 0.45]), year="1867",
          lower="A pumpkin harvest | an old postcard", stamp=dict(FACT, at="North")),
    ]),

    # ------------------------------------------------------------------ 5. Meanwhile, in La Porte
    dict(id="c5", music="laporte", card=dict(type="chapter", n=5, title="Meanwhile, in La Porte", sub="Northern Indiana · 1868 – 1917"), lines=[
        L("c5-01", "So what was Halloween like here? There's a catch. La Porte's own newspapers from those years aren't online. The Argus and the Herald sit on microfilm at the library on Indiana Avenue.",
          P("lp-streets-21.jpg", fit="contain", tone="sepia-soft", z=[1.0, 1.06]), year="", lower="La Porte | the old Town Hall"),
        L("c5-02", "The library's own hundred-years-ago column, from the Argus of October 1922, has nothing about Halloween at all. The big news on the thirty-first was an Elks' show at the Central theatre.",
          TYPED("LA PORTE ARGUS · OCT. 31, 1922", ["Home talent entertains at an Elks' show.", "The Central theatre is packed.", "Halloween: not mentioned."]), year="1922"),
        L("c5-03", "But the papers of the towns around us are online, and they were reading the same wire stories and chasing the same boys. So here is Halloween in northern Indiana, as the neighbors reported it.",
          MAP(**CO, cam0=[-86.70, 41.55, 1.30], cam1=[-86.75, 41.50, 2.6], move_end=0.9,
              places=[LAKE, COUNTY, MICH, IND, place(LP, 0.0), place(MC, 0.0), place(SB, 0.4), place(HAMMOND, 0.6), place(GOSHEN, 0.8)])),
        L("c5-04", "1868. A Terre Haute paper reported that two Irish girls had left a party on Halloween night to pull cabbages in a neighbor's field, the old game for seeing your future husband. The neighbor shot at them, and killed one, Bridget Murry. He appeared, the paper said, perfectly unconcerned and indifferent.",
          QUOTE("“…appeared perfectly unconcerned and indifferent.”", "Daily Wabash Express, Nov. 3, 1868"), year="1868"),
        L("c5-05", "The old Scottish game had crossed the ocean, and so had the gun.", DARK),
        L("c5-07", "1906. In Whiting, up by the lake, the town put about ten extra policemen on the street for Halloween. It didn't help. Gates were carried off. A window went in at Recht's department store. And the excitement, the paper said, was great when a Recht's employee chased some small children down the street.",
          NEWS("lct-1906-01.jpg", mode="zoom", hold=0.3, lower="Lake County Times, Hammond | Nov. 1, 1906"), year="1906", sfx=[["page", 0.0]]),
        L("c5-08", "That was also the night the thermometer in South Bend fell to 20 degrees, a record low for Halloween that's been tied only once since, in 1925.",
          BIG("20°", cap="South Bend, Halloween 1906: the record low"), sfx=[["wind", 0.2]]),
        L("c5-09", "1909. The quietest Halloween Whiting had ever had, the paper said. Only the door mats and gates vanished, beans and flour hit the windows, and somebody soaped the streetcar rails, so the motorman had to climb down and sand them.",
          NEWS("lct-1909-01.jpg", mode="zoom", hold=0.3, lower="Lake County Times | Nov. 1, 1909"), year="1909", sfx=[["page", 0.0]]),
        L("c5-10", "That winter, sixty miles east of La Porte, the young men of Goshen had gone ghost hunting by moonlight, after the Fort Wayne paper's headline: Hundreds Saw the Goshen Ghost. The ghost led them five blocks and vanished.",
          BIG("“HUNDREDS SAW THE GOSHEN GHOST”", cap="Fort Wayne Journal-Gazette, Feb. 7, 1909")),
        L("c5-10b", "1910. The Lake County Times, in Hammond, the morning after. We'll let you read it.",
          NEWS("clip-lct-1910-2.jpg", mode="hold", lower="Lake County Times, Hammond | Nov. 1, 1910"), year="1910", sfx=[["page", 0.0]]),
        L("c5-10c", "The same night, in Hegewisch, just over the state line, a sixty-year-old porter walked in the dark to an outhouse that wasn't there anymore. Someone had carried it off. He fell into the pit and died. The paper blamed, in its words, Hallowe'en dastards.",
          NEWS("clip-lct-1910-3.jpg", mode="hold", lower="Lake County Times | Nov. 1, 1910"), sfx=[["page", 0.0]]),
        L("c5-11", "1913. On Halloween night, a streetcar strike in Indianapolis turned into a riot. The South Bend paper reported that Halloween observers, hiding their identities under mask and face paint, joined the general disorder. Fifty arrests.",
          NEWS("clip-sbnt-1913a-1.jpg", mode="hold", lower="South Bend News-Times | Nov. 1, 1913"), year="1913", sfx=[["page", 0.0]]),
        L("c5-11b", "In South Bend itself, a seventeen-year-old named George Kline got so annoyed by the boys making noise outside the house where he boarded that he fired a twenty-two rifle at them. One boy was hit in the leg. Not expected to prove serious, the paper said.",
          NEWS("sbnt-1913-02.jpg", mode="zoom", hold=0.3, lower="South Bend News-Times | Nov. 1, 1913"), sfx=[["page", 0.0]]),
        L("c5-12", "And 1917: the coldest Halloween on the South Bend books. The high that day was 35 degrees. Whatever the boys of La Porte did that night, they did it in their coats.",
          BIG("35°", cap="the high in South Bend, Halloween 1917: the coldest on record"), year="1917", sfx=[["wind", 0.3]]),
        L("c5-13", "So far, not one newspaper has used the words trick or treat. Hold that thought.", DARK, year="", gap=0.8),
    ]),

    # ------------------------------------------------------------------ 6. The night that got out of hand
    dict(id="c6", music="trouble", card=dict(type="chapter", n=6, title="The Night That Got Out of Hand", sub="1920 – 1935"), lines=[
        L("c6-01", "By the 1920s, American towns had a problem. Halloween pranks had turned into real damage, and the kids doing it were getting older.",
          P("hw-us-22.jpg", tone="sepia", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.42]), year="1920",
          lower="A Halloween party | Howard Chandler Christy, 1916"),
        L("c6-02", "The answer was to buy them off. In October 1923, the Hammond Elks and the Munster Boy Scouts threw parties. Gary businessmen put up prizes for a costume parade led by a park policeman. And Hammond stores sold Halloween candy, pumpkins, and spooky records.",
          [P("costume-1920-01.jpg", tone="sepia", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.45, 0.45], lower="A Halloween party, Wainwright, Alberta | 1920s"),
           NEWS("sbnt-1923-01.jpg", mode="zoom", box=[0.56, 0.72, 0.90, 1.0], hold=0.3, lower="South Bend News-Times | Nov. 1, 1923")], year="1923", sfx=[["page", 4.0]]),
        L("c6-02b", "That same morning, South Bend's front page put the new idea in a headline: Hallowe'en finds Chicago youth behaving while grown-ups frolic. Sell the youngsters the nice-party idea, it said. The older folks have the wild parties.",
          NEWS("clip-sbnt-1923-2.jpg", mode="hold", lower="South Bend News-Times | Nov. 1, 1923"), sfx=[["page", 0.0]]),
        L("c6-03", "Years later, a mother in East Chicago wrote that she had gone trick-or-treating in costume that same year, 1923. It's a memory, not a clipping, but it's the earliest claim we found in this part of Indiana.",
          P("costume-old-01.jpg", tone="sepia", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.5, 0.4]), lower="Girls in costume | 1918"),
        L("c6-04", "That June, the Indianapolis city council voted on a law to ban masks in public. It was aimed at the Ku Klux Klan, which was then at the height of its power in Indiana. The bill had one exception written into it: Halloween. The council killed it, 6 to 2.",
          TYPED("INDIANAPOLIS CITY COUNCIL · JUNE 18, 1923", ["A ban on masks in public, aimed at the Klan.", "One exception in the bill: Halloween.", "Killed, 6 to 2, before a crowd of nearly a thousand."])),
        L("c6-05", "In 1927, a merchants' association in the Irvington neighborhood of Indianapolis started a Halloween festival. It's still going. It's the oldest in the state we could document.",
          P("x-named-03.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.45]), year="1927",
          lower="A Halloween postcard | 1920s"),
        L("c6-07", "Then came the Depression. By 1933, the damage in some cities was so bad that officials talked about banning Halloween. It's been called Black Halloween ever since.",
          P("costume-1920-02.jpg", tone="sepia", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.45, 0.45], lower="A Halloween party, Wainwright, Alberta | 1920s"), year="1933", sfx=[["page", 0.0]]),
        L("c6-08", "Instead, as the historian Lisa Morton puts it, the towns decided to buy these kids off: parties, parades, carnivals, costume contests.",
          QUOTE("“…buy these kids off.”", "Lisa Morton, Trick or Treat: A History of Halloween")),
        L("c6-09", "It worked, mostly. But it left a question. If you give the kids something, what do they give you back? Somewhere up north, somebody had already worked that out.", DARK, year="", gap=0.8),
    ]),

    # ------------------------------------------------------------------ 7. The invention of trick-or-treat
    dict(id="c7", music="treat", card=dict(type="chapter", n=7, title="The Invention of Trick-or-Treat", sub="Canada and the United States · 1917 – 1952"), lines=[
        L("c7-01", "Most histories say trick or treat was first printed in Blackie, Alberta, in 1927. It wasn't.",
          BIG("BLACKIE, ALBERTA, 1927", cap="“the first trick or treat”"), year="1927", stamp=dict(MYTH, at=3.0)),
        L("c7-02", "The oldest we could find is from the Sault Daily Star of Sault Ste. Marie, Ontario, across the river from Michigan, on the first of November, 1917. Tricks or treats, you could hear the gangs call out.",
          QUOTE("“‘Tricks or treats’ you could hear the gangs call out.”", "The Sault Daily Star, Nov. 1, 1917"), year="1917", stamp=dict(FACT, at="Tricks")),
        L("c7-03", "Listen to that word. Gangs. It wasn't a greeting. It was a deal: give us something, or we'll do something to your house.",
          P("hw-us-12.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.42])),
        L("c7-04", "It crept south. Bay City, Michigan, 1928: the fatal ultimatum, tricks or treats. Portland, Oregon, 1932. Helena, Montana, 1934. And in 1938, the Los Angeles Times called it the Halloween hijacking game.",
          TYPED("“TRICK OR TREAT” HEADS SOUTH", ["1917: Sault Ste. Marie, Ontario.", "1928: Bay City, Michigan — “the fatal ultimatum.”", "1932: Portland. 1934: Helena.", "1938: Los Angeles — “the Halloween hijacking game.”"]), year="1938"),
        L("c7-05", "Then the war got in the way. In May 1942, sugar became the first thing rationed in the United States. For five Halloweens, there wasn't much candy to give.",
          [NEWS("np-sugar-03.jpg", mode="zoom", hold=0.3, lower="Waterbury Democrat | Oct. 8, 1942"),
           NEWS("np-sugar-05.jpg", mode="zoom", hold=0.3, lower="Daily Monitor Leader, Mount Clemens, Mich. | Oct. 10, 1942")], year="1942", sfx=[["page", 0.0], ["page", 4.0]]),
        L("c7-06", "Rationing ended in 1947. By 1948, the words were in the headlines in Washington.",
          NEWS("np-tot-03.jpg", mode="zoom", hold=0.4, lower="Evening Star, Washington | Oct. 27, 1948"), year="1948", sfx=[["page", 0.0]]),
        L("c7-07", "Next door to La Porte County, in Culver, the paper in 1950 reported that houses that gave no treats the year before had had their windows soaped. The town reminded parents that children under 16 were due off the streets by 10, and asked them to help.",
          TYPED("CULVER CITIZEN · OCTOBER 1950", ["Windows soaped where no treats were given.", "A reminder: under-16s off the streets by 10 p.m.", "Parents asked to help."]), year="1950"),
        L("c7-08", "That's the deal, in writing, in Marshall County. Treat, or trick.",
          P("hw-us-32.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.1], f0=[0.5, 0.5], f1=[0.5, 0.45])),
        L("c7-09", "In 1951, Charlie Brown went trick-or-treating in the Peanuts comic strip. In 1952, Donald Duck's nephews did it in a Disney cartoon called Trick or Treat. After that, every kid in America knew the words.",
          NEWS("np-tot-08.jpg", mode="zoom", hold=0.4, lower="Evening Star, Washington | Oct. 30, 1951"), year="1951", sfx=[["page", 0.0]]),
        L("c7-10", "Thirty-five years, from a gang's shout in Ontario to a cartoon duck. That's how long it took to invent trick-or-treat.", DARK, year="", gap=0.8),
    ]),

    # ------------------------------------------------------------------ 8. Porch lights
    dict(id="c8", music="porch", card=dict(type="chapter", n=8, title="Porch Lights", sub="1950 – 1974"), lines=[
        L("c8-01", "Halloween 1950 was the hottest on record in this part of the country. South Bend hit 83 degrees. Chicago, 84. Warm enough to trick-or-treat in shirtsleeves.",
          BIG("83°", cap="South Bend, Halloween 1950: the record high"), year="1950"),
        L("c8-02", "That same night, in Philadelphia, a minister's family named Allison took their children out collecting coins for the United Nations' children's fund instead of candy. They raised three dollars. It became Trick-or-Treat for UNICEF.",
          [NEWS("np-unicef-01.jpg", mode="zoom", hold=0.3, lower="Camas Hot Springs Exchange | Oct. 28, 1954"),
           NEWS("np-tot-09.jpg", mode="zoom", hold=0.3, lower="Evening Star | Nov. 1, 1951")], sfx=[["page", 0.0], ["page", 4.0]]),
        L("c8-04", "The costumes changed too. A Brooklyn company called Ben Cooper had been selling boxed costumes since 1937, with a Disney license. In 1963, it licensed a character almost nobody had heard of yet: Spider-Man.",
          [P("hw-us-19.jpg", tone="bw", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.45], lower="Skeleton costumes on television | 1969"),
           P("hw-us-33.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.5, 0.4], lower="Halloween in Alaska | 1967")], year="1963"),
        L("c8-06", "And in 1974, the First Lady, Betty Ford, handed out treats to UNICEF trick-or-treaters at the White House. The holiday that had been a night of broken gates was now official enough for the White House lawn.",
          P("x-ford-01.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.55, 0.45]), year="1974",
          lower="Betty Ford and trick-or-treaters | the White House, Oct. 31, 1974"),
        L("c8-07", "The same Halloween, in a suburb of Houston, a father handed his eight-year-old son a Pixy Stix.", DARK, year="", gap=0.8),
    ]),

    # ------------------------------------------------------------------ 9. The razor blade that wasn't
    dict(id="c9", music="razor", card=dict(type="chapter", n=9, title="The Razor Blade That Wasn't", sub="1958 – today"), lines=[
        L("c9-01", "If you grew up after 1970, somebody checked your candy. Razor blades in apples. Poison in the chocolate. Strangers out to hurt children.",
          P("x-pixy-01.jpg", tone="night", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.5, 0.45]), year="1970"),
        L("c9-02", "A sociologist named Joel Best has been checking that story since the 1980s. He went through the big national newspapers from 1958 on, the New York Times, the Chicago Tribune, the Los Angeles Times, and followed up the reports with police and hospitals.",
          TYPED("JOEL BEST, UNIVERSITY OF DELAWARE", ["The New York Times, Chicago Tribune and L.A. Times, 1958 on.", "Nearly a hundred reports of tampered candy.", "Followed up with police and hospitals."])),
        L("c9-03", "He found no case, not one, of a child killed or seriously hurt by a stranger's Halloween treat. Most of the reports were pranks or hoaxes. Some were by the children themselves.",
          BIG("0", cap="children killed by a stranger's Halloween candy, 1958 – today"), stamp=dict(MYTH, at="not")),
        L("c9-04", "There were two real deaths, and neither was a stranger. In Detroit in 1970, a five-year-old died of a heroin overdose. Heroin was found on his candy. Investigators traced it to his uncle's stash, and concluded the family had put it on the candy afterward, to cover up.",
          DARK, year="1970"),
        L("c9-05", "And in Pasadena, Texas, on Halloween 1974, eight-year-old Timothy O'Bryan died after eating a Pixy Stix laced with cyanide. His father had insured his children's lives days before.",
          TYPED("PASADENA, TEXAS · OCT. 31, 1974", ["Timothy O'Bryan, 8, dies of cyanide in a Pixy Stix.", "His father had just insured his children's lives.", "He had handed poisoned straws to four other children.", "Ronald Clark O'Bryan was convicted and executed in 1984."]), year="1974"),
        L("c9-06", "Ronald Clark O'Bryan had handed poisoned straws to four other children. None of them ate one. One eleven-year-old couldn't get the staple out. Texas executed him in 1984.",
          SAME, year="1984"),
        L("c9-07", "The one famous Halloween poisoning was a father using the myth as his cover. The myth outlived him. Dear Abby was still warning her readers about poisoned candy in 1983.",
          P("tot-15.jpg", tone="bw", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.45]), year="1983"),
        L("c9-08", "Check your kids' candy if it makes you feel better. But know what the record says. In nearly seventy years, the stranger with the razor blade has never once shown up.", DARK, year="", gap=0.8),
    ]),

    # ------------------------------------------------------------------ 10. Why it survived
    dict(id="c10", music="end", card=dict(type="chapter", n=10, title="Why It Survived", sub="La Porte County · today"), tail=2.5, lines=[
        L("c10-01", "This year, Americans will spend about $13.5 billion on Halloween, $115 a person. 74 percent of us will celebrate. The top children's costume, once again, is Spider-Man.",
          TYPED("HALLOWEEN 2026", ["$13.5 billion spent, up from $13.1 billion last year.", "$115.14 a person.", "74% of Americans celebrating.", "Top kids' costume: Spider-Man."]), year="2026"),
        L("c10-02", "And Indiana is one of the biggest pumpkin states in the country, second or third in most years, behind Illinois. Some of them come off a farm west of La Porte that the Garwood family has worked since 1831.",
          [P("pumpkins-08.jpg", tone="warm", crop=[0.02, 0.05, 0.98, 0.95], z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.5, 0.45]),
           P("hw-us-42.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.45])], year="1831"),
        L("c10-03", "Out at Hesston, the steam museum has run a Ghost Train through the woods on the last weekends of October since at least 2006. In La Porte, the historical society's museum fills its period rooms with costumed guides. And the Washington Park Zoo in Michigan City, which began in 1925 with one pet bear, does Boo at the Zoo.",
          MAP(**CO, cam0=[-86.75, 41.62, 1.25], cam1=[-86.70, 41.62, 1.05], move_end=0.9,
              places=[LAKE, COUNTY, place(LP, 0.1), place(MC, 0.5), place({"name": "Hesston", "at": [-86.6997, 41.7392]}, 0.3)]), year="2006"),
        L("c10-04", "Nearly every town in the county now trick-or-treats in the same window: 5 to 7 in the evening, in daylight. The old free-for-all after dark is gone. The night of the broken gates has become two hours before supper.",
          TYPED("TRICK-OR-TREAT, LA PORTE COUNTY · 2025", ["La Porte, Michigan City, Kingsford Heights,", "Long Beach, Rolling Prairie, Trail Creek,", "Union Mills, Wanatah, Westville:", "5 to 7 p.m., Oct. 31."]), year="2025"),
        L("c10-05", "And this being La Porte Weather Now, the weather. Going by South Bend's records, a typical Halloween here runs in the mid to upper 40s at trick-or-treat time. But not always.",
          P(LP_CARD, tone="warm", crop=[0.02, 0.03, 0.98, 0.97], z=[1.0, 1.1], f0=[0.45, 0.42], f1=[0.5, 0.5]), year=""),
        L("c10-06", "2013: a storm dumped 2.98 inches of rain on La Porte over Halloween night, and gave Fort Wayne its wettest Halloween on record. 2014: a gust of 67 miles an hour off the lake at Michigan City. 2019: 2.2 inches of snow in Valparaiso. 2023: 1.4 inches of snow in South Bend, the second-snowiest ever.",
          TYPED("HALLOWEEN WEATHER, THIS CORNER OF INDIANA", ["1906: 20°, the record low (South Bend).", "1917: a high of 35°, the coldest.", "1950: 83°, the record high.", "1954: 1.6 in. of snow. 2023: 1.4 in.", "2013: 2.98 in. of rain over Halloween night, La Porte.", "2014: a 67 mph gust off Michigan City."]), year="2013"),
        L("c10-07", "So why did it survive? Because it kept changing. A winter fire became a church feast. A church feast became a night for finding out who you'd marry. That became a night for breaking gates, and that became a deal: treat us, and we'll leave your gate alone.",
          [P("burns-02.jpg", tone="sepia", crop=[0.05, 0.05, 0.95, 0.95], z=[1.0, 1.1], f0=[0.5, 0.5], f1=[0.5, 0.45]),
           P("x-named-06.jpg", tone="warm", crop=[0.02, 0.02, 0.98, 0.98], z=[1.0, 1.1], f0=[0.5, 0.5], f1=[0.5, 0.45]),
           P("hw-us-16.jpg", tone="warm", z=[1.0, 1.1], f0=[0.5, 0.45], f1=[0.5, 0.4])], year=""),
        L("c10-08", "And every generation told itself the night was ancient, because that made it feel like it belonged to them. Maybe that's the real tradition. Not the turnip, or the pumpkin, or the candy. The story.", DARK, gap=0.8),
        L("c10-09", "Tell us yours. What did Halloween look like in La Porte when you were a kid? Which street gave out full-size candy bars? Put it in the comments. We read every one, and the best ones go in the next film.",
          QUOTE("What did Halloween look like in La Porte when you were a kid?", "tell us in the comments", size=52), gap=0.8),
        L("c10-10", "If you want the ghost stories, we made a whole film about them: the keeper who still climbs to her lamp, the headless flagman, and the four hundred and ninety-nine unknown people in Pine Lake Cemetery. It's on this channel, with our film on the Belle Gunness farm.",
          TYPED("ALSO ON THIS CHANNEL", ["Haunted: The Ghost Stories of La Porte County", "The Belle Gunness Farm: what the records say"])),
        L("c10-11", "Sources, every photo credit, and the newspaper pages are in the description.",
          QUOTE("Sources, photo credits and the newspaper pages are in the description.", None, size=46), hold=5.0),
    ]),
]


def build():
    script = {"title": "The Real History of Halloween: Told Through a Small Town's Newspapers", "chapters": CHAPTERS}
    json.dump(script, open(os.path.join(HERE, "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    words = sum(len(ln.get("say", "").split()) for ch in CHAPTERS for ln in ch["lines"])
    todo = sum(1 for ch in CHAPTERS for ln in ch["lines"] for v in (ln.get("v") if isinstance(ln.get("v"), list) else [ln.get("v")])
               if isinstance(v, dict) and v.get("by") == "picture to come")
    stamps = sum(1 for ch in CHAPTERS for ln in ch["lines"] if ln.get("stamp"))
    print(len(CHAPTERS), "chapters,", sum(len(ch["lines"]) for ch in CHAPTERS), "lines,", words, "words,", stamps, "stamps,", todo, "pictures to choose")


if __name__ == "__main__":
    build()
