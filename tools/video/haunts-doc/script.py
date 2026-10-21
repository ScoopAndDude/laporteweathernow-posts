#!/usr/bin/env python3
"""The hauntings documentary's script: every narration line and the pictures shown with it.

    python3 tools/video/haunts-doc/script.py        writes script.json (what doc.py and the voice job read)

Facts come from the research file of Oct. 20, 2026 (sources in the YouTube description): the National Park
Service and Hoosier State Chronicles on Harriet Colfax, the Michigan City Historical Society and the lighthouse's
National Register nomination, the Indiana Historical Bureau's podcasts (the 1905 headless flagman, Cathcart's
spirit circles), the 1859 Spiritualist Register, Emma Hardinge's 1870 history, the Barker Mansion's markers,
the DePauw/United Methodist archives (Posey Chapel), Find a Grave and the county cemetery association, the
Indiana DNR, WKVI and the Towne Post (Kingsbury), the La Porte County Historical Society and the NWS (the
Aug. 11, 2026 derecho), and the 2011 Herald-Dispatch "most haunted" list.

Legends are told as legends ("the story goes", "people say"), and what the records don't show is said plainly
("we found no record"). Left out because no source could be found, or to protect real families: Gravity Hill,
Orr Lake Road, Saugany Lake, Soldiers Memorial Park, Devil's Bridge, Range Road, the I Street clinic, Dog Face
Bridge and the zoo chimp. The Colfax-Hartwell relationship is described only in the Park Service's words.
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


def TODO(desc):
    """A stand-in until the right picture is chosen."""
    return QUOTE(desc, "picture to come", size=48)


# ---------------------------------------------------------------------------------------------- places on the maps
LP = {"name": "La Porte", "at": [-86.7225, 41.6106]}
MC = {"name": "Michigan City", "at": [-86.8950, 41.7075]}
POSEY = {"name": "Posey Chapel", "at": [-86.6273, 41.7531]}
ROLLING = {"name": "Rolling Prairie", "at": [-86.6161, 41.6742]}
KINGSBURY = {"name": "Kingsbury", "at": [-86.6978, 41.5281]}
KFH = {"name": "Kingsford Heights", "at": [-86.6917, 41.4806]}
LAKE = {"name": "LAKE MICHIGAN", "at": [-87.25, 41.74], "dot": 0, "font": "fell-sc", "size": 46, "tracking": 4}
COUNTY = {"name": "LA PORTE COUNTY", "at": [-86.90, 41.52], "dot": 0, "font": "fell-sc", "size": 40, "tracking": 6}
MICH = {"name": "MICHIGAN", "at": [-86.50, 41.79], "dot": 0, "font": "fell-sc", "size": 38, "tracking": 8}
IND = {"name": "INDIANA", "at": [-86.30, 41.33], "dot": 0, "font": "fell-sc", "size": 38, "tracking": 8}


def place(p, show=0.0, **kw):
    return dict(p, show=show, **kw)


CO = dict(map="county")

# pictures chosen Oct. 20-21, 2026 from images/manifest*.json (and the Belle film's images)
H08 = "hardinge-08.jpg"           # Hardinge 1870, printed page 337: Cathcart's own account and his P.S.
H08_BOX = [0.03, 0.19, 0.88, 0.355]
PACK = "packard1876-05.jpg"       # Packard 1876, printed page 134: how Posey Chapel began
PACK_BOX = [0.12, 0.315, 0.97, 0.675]

CHAPTERS = [
    # ------------------------------------------------------------------ cold open
    dict(id="open", music="open", tail=0.2, lines=[
        L("o01", "On the shore of Lake Michigan, for forty-three years, a woman climbed to the same lamp every night and lit it. Some people say she still does.",
          P("lh-cards-03.jpg", tone="night", crop=[0.04, 0.08, 0.96, 0.95], z=[1.0, 1.2], f0=[0.5, 0.45], f1=[0.36, 0.42]),
          lower="Michigan City | the harbor lights, on a 1933 postcard", sfx=[["waves", 0.0]]),
        L("o02", "Inland, a former congressman sat in the dark and listened to a drum that, he said, no one was playing.",
          P("seance-23.jpg", tone="night", crop=[0.05, 0.05, 0.95, 0.85], z=[1.05, 1.2], f0=[0.5, 0.5], f1=[0.45, 0.42]),
          lower="A seance in New York | 1909", sfx=[["drum", 3.2]]),
        L("o03", "In a La Porte cemetery, a single marker stands for four hundred and ninety-nine unknown persons.",
          P("lp-pine-01.jpg", crop=[0.16, 0.47, 0.96, 0.92], z=[1.0, 1.18], f0=[0.5, 0.5], f1=[0.45, 0.55]),
          lower="Pine Lake Cemetery, La Porte | from the 1874 county atlas"),
        L("o04", "Out in the farm country, the story goes, a chapel burned more than a hundred and fifty years ago, and was never at peace again.",
          DARK, sfx=[["fire", 0.3]]),
        L("o05", "And in the summer of 1905, a newspaper told of a man with no head, standing by the railroad tracks after dark, flagging down a train.",
          P("rail-tank-07.jpg", tone="night", crop=[0.0, 0.18, 1.0, 0.88], z=[1.0, 1.15], f0=[0.75, 0.5], f1=[0.62, 0.5]), sfx=[["train", 2.5]]),
        L("o06", "These are the ghost stories of La Porte County, Indiana.",
          MAP(**CO, cam0=[-86.70, 41.55, 1.40], cam1=[-86.70, 41.55, 1.22], move_end=0.9,
              places=[LAKE, COUNTY, MICH, IND, place(MC, 0.15), place(LP, 0.3)])),
        L("o07", "And this is the history behind them: what's real, what's legend, and what no one can prove.", DARK, gap=0.8),
    ]),
    dict(id="title", music="title", tail=0.3, lines=[
        L("t01", None, dict(type="title", title="HAUNTED", subtitle="The ghost stories of La Porte County",
                             kicker="A LA PORTE WEATHER NOW DOCUMENTARY"), hold=7.5),
    ]),

    # ------------------------------------------------------------------ 1. The door
    dict(id="c1", music="door", card=dict(type="chapter", n=1, title="The Door", sub="La Porte County · 1832"), lines=[
        L("c1-01", "La Porte is French for “the door.” The name is said to come from a natural opening in the forest, a doorway onto the prairie.",
          P("lp-streets-17.jpg", fit="contain", tone="sepia-soft", z=[1.0, 1.06]), lower="La Porte | French for “the door”"),
        L("c1-02", "For generations before any settlers came, this was Potawatomi land.",
          MAP(**CO, cam0=[-86.75, 41.55, 1.40], cam1=[-86.75, 41.52, 1.30], move_end=0.9, title="POTAWATOMI LAND", places=[LAKE])),
        L("c1-03", "Under treaties signed in 1826 and 1832, the Potawatomi ceded their land here to the United States. In 1838, the government forced hundreds of Potawatomi people to leave Indiana for Kansas. The march is remembered as the Trail of Death. Potawatomi people still live in the region today.",
          TYPED("POTAWATOMI LAND", ["1826 and 1832: treaties with the United States.", "1838: hundreds forced from Indiana to Kansas,", "on the march remembered as the Trail of Death.", "Potawatomi people still live in the region."]), gap=0.8),
        L("c1-04", "La Porte County was created in 1832.",
          [P("lp-court-08.jpg", fit="print", z=[1.0, 1.08], lower="La Porte County's second courthouse | about 1848"),
           P("lp-lakes-16.jpg", tone="paper", crop=[0.0, 0.03, 0.55, 0.97], z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.55, 0.5], lower="La Porte | from an 1888 town booklet")]),
        L("c1-05", "On the lake, at the mouth of Trail Creek, Isaac Elston founded Michigan City on land he bought in 1830. On July Fourth, 1836, the first commercial ship, the Sea Serpent, sailed into the creek.",
          [P("mc-harbor-04.jpg", tone="paper", crop=[0.05, 0.12, 0.95, 0.95], z=[1.0, 1.25], f0=[0.5, 0.5], f1=[0.5, 0.72], lower="The harbor at Michigan City | an 1840 survey"),
           P("laporte-old-07.jpg", z=[1.0, 1.12], f0=[0.45, 0.5], f1=[0.55, 0.5], lower="Trail Creek, Michigan City | 1911")]),
        L("c1-06", "The railroads came in 1852, and the factories after them.",
          [P("rail-tank-07.jpg", tone="sepia", crop=[0.0, 0.18, 1.0, 0.88], z=[1.0, 1.1], f0=[0.4, 0.5], f1=[0.6, 0.5]),
           P("laporte-old-02.jpg", z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.42, 0.5], lower="A La Porte factory | 1911")]),
        L("c1-07", "In 1860, the state began building a prison at Michigan City. In 1933, ten inmates broke out of it with pistols smuggled in by John Dillinger.",
          [P("named-03.jpg", fit="print", z=[1.0, 1.08], lower="Indiana State Prison | 1871"),
           P("prison-33.jpg", tone="warm", crop=[0.02, 0.03, 0.98, 0.78], z=[1.0, 1.1], f0=[0.4, 0.5], f1=[0.55, 0.5], lower="Indiana State Prison | about 1908")]),
        L("c1-08", "For all its history, we couldn't find a ghost story about the prison that anyone could trace to a source.", SAME),
        L("c1-09", "Even the land has changed. A sand dune about two hundred feet tall, the Hoosier Slide, once towered over the harbor. By 1920, it had been dug away, much of it to make glass.",
          [P("named-02.jpg", tone="warm", crop=[0.02, 0.06, 0.98, 0.97], z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.5, 0.4], lower="The Hoosier Slide | 1907"),
           P("laporte-old-12.jpg", tone="warm", z=[1.0, 1.12], f0=[0.6, 0.5], f1=[0.45, 0.45], lower="The harbor and the Hoosier Slide | 1909")]),
        L("c1-10", "A place where so much has come and gone leaves stories behind. Some are history. Some are legend. Many are a little of both.",
          P("lp-streets-21.jpg", fit="contain", tone="sepia-soft", z=[1.0, 1.08])),
        L("c1-11", "In this film, we'll tell you which is which, as best the records allow.", SAME, gap=0.8),
    ]),

    # ------------------------------------------------------------------ 2. The keeper
    dict(id="c2", music="keeper", card=dict(type="chapter", n=2, title="The Keeper", sub="Michigan City · 1861 – 1904"), lines=[
        L("c2-01", "In 1853, a young music teacher named Harriet Colfax moved from Ogdensburg, New York, to Michigan City, with her brother.",
          P("map-laporte-13.jpg", tone="paper", crop=[0.1, 0.05, 0.9, 0.55], z=[1.0, 1.15], f0=[0.5, 0.35], f1=[0.42, 0.45]),
          lower="Michigan City | an 1884 insurance map"),
        L("c2-02", "He ran a newspaper, and she helped him set the type. In 1856, he died of tuberculosis. He was twenty-six.",
          TYPED("HARRIET COLFAX", ["From Ogdensburg, New York.", "Michigan City, 1853: a music teacher,", "setting type at her brother's newspaper."])),
        L("c2-03", "In 1861, Harriet was appointed keeper of the Michigan City lighthouse.",
          P("lh-old-01.jpg", tone="sepia-soft", crop=[0.0, 0.0, 0.66, 1.0], z=[1.0, 1.1], f0=[0.45, 0.45], f1=[0.5, 0.35]),
          lower="The Michigan City lighthouse | built 1858 (photo, 2007)"),
        L("c2-04", "Newspapers long said she owed the job to her cousin, Schuyler Colfax, a congressman from South Bend who later became vice president. She told a reporter she'd been appointed by Mr. Lincoln, soon after his inauguration.",
          [P("colfax-s-11.jpg", fit="print", tone="bw", z=[1.0, 1.08], lower="Schuyler Colfax | photographed by Mathew Brady"),
           QUOTE("appointed by Mr. Lincoln soon after his inauguration", "Harriet Colfax, in an 1881 interview")]),
        L("c2-05", "The lighthouse was new, built in 1858 of stone and brick, with the light in a cupola on the roof.",
          P("lh-old-01.jpg", tone="sepia-soft", crop=[0.0, 0.0, 0.66, 1.0], z=[1.15, 1.45], f0=[0.55, 0.3], f1=[0.58, 0.16])),
        L("c2-06", "Every evening, she lit the lamps. At first they burned lard oil. It had to be heated first, and on cold nights it could harden again before she got it to the light.",
          P("fresnel-07.jpg", tone="warm", z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.5, 0.42])),
        L("c2-07", "In 1871, a second light was built out on the pier, at the end of a long, raised wooden walkway. A few years later, it was moved to the west pier, across Trail Creek. To reach it, she rowed across the creek in a small boat.",
          P("lh-cards-01.jpg", crop=[0.0, 0.0, 1.0, 0.82], z=[1.0, 1.25], f0=[0.6, 0.45], f1=[0.28, 0.42]), lower="The pier and its raised walkway | 1911"),
        L("c2-08", "In storms, the walk was dangerous. In 1872, she wrote, the waves dashed over the top of the beacon.",
          P("mc-lake-08.jpg", crop=[0.0, 0.0, 1.0, 0.68], z=[1.0, 1.15], f0=[0.4, 0.5], f1=[0.55, 0.45]), lower="A rough day on Lake Michigan, Michigan City | 1910",
          sfx=[["waves", 0.0]]),
        L("c2-09", "Her log for May twenty-eighth, 1873: A terrible hurricane tonight at about the time of lighting up. Narrowly escaped being swept into the lake.",
          LETTER("A terrible hurricane to-night at about the time of lighting up. Narrowly escaped being swept into the lake.", by="Harriet Colfax's log, May 28, 1873", greeting="May 28, 1873.")),
        L("c2-10", "In 1886, a storm knocked the pier beacon into the lake. And an 1890 newspaper story told how, one night, she found the beacon's lock tampered with, and broke a pane of glass to get the lamp lit.",
          [P("mc-pier-02.jpg", z=[1.0, 1.12], f0=[0.45, 0.4], f1=[0.5, 0.5], lower="The pier walk in winter | 1916"),
           TYPED("STORMS AND DANGERS", ["1872, her log: waves over the beacon.", "1873, her log: nearly swept into the lake.", "1886: a storm takes the beacon.", "1890, a newspaper: a tampered lock."])]),
        L("c2-11", "She kept the light for forty-three years. People called her Old Faithful.", BIG("43 years", cap="keeper of the Michigan City light, 1861 – 1904")),
        L("c2-12", "She didn't keep it alone. Ann Hartwell, a teacher she had known in Ogdensburg, followed her to Michigan City and lived with her at the lighthouse. The National Park Service calls Ann her lifelong companion.",
          P("lh-old-01.jpg", tone="sepia-soft", crop=[0.0, 0.0, 0.66, 1.0], z=[1.1, 1.2], f0=[0.4, 0.62], f1=[0.5, 0.6])),
        L("c2-13", "Ann taught in the public schools for about twenty-five years, then opened a book exchange that became the area's first lending library.",
          TYPED("ANN HARTWELL", ["A teacher in Michigan City's public schools", "for about twenty-five years.", "Then: the area's first lending library."])),
        L("c2-14", "In October 1904, at about eighty years old, Harriet Colfax retired.",
          P("lh-cards-02.jpg", crop=[0.25, 0.0, 1.0, 0.85], z=[1.0, 1.12], f0=[0.4, 0.4], f1=[0.42, 0.3]), lower="Michigan City's pier light | 1910"),
        L("c2-15", "As she got ready to leave, a Chicago newspaper quoted her: I could not bear to see anyone else light my lamp.",
          QUOTE("I could not bear to see anyone else light my lamp.", "Harriet Colfax, quoted in the Chicago Daily Tribune, Oct. 2, 1904"), gap=0.9),
        L("c2-16", "Six days after she retired, the light in the old lighthouse was put out for good. The lantern came off the roof, and a new light took its place at the end of the pier.",
          [P("lhx-cat-05.jpg", fit="print", crop=[0.30, 0.28, 0.73, 0.70], z=[1.0, 1.1], lower="Michigan City Light Station | a Lighthouse Service photo, 1917"),
           P("lhx-search-07.jpg", tone="bw", z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.5, 0.35], lower="The pierhead light | U.S. Coast Guard photo")]),
        L("c2-17", "Harriet and Ann moved into a new home. In January, Ann died. That April, Harriet died too.",
          TYPED("1905", ["January: Ann Hartwell dies.", "April: Harriet Colfax dies.", "Both are buried at Greenwood Cemetery."]), gap=0.8),
        L("c2-18", "They're buried in Greenwood Cemetery, in Michigan City.", SAME),
        L("c2-19", "The old lighthouse has been a museum since 1973, run by the Michigan City Historical Society.",
          P("lh-old-01.jpg", tone="warm", z=[1.0, 1.08], f0=[0.5, 0.5], f1=[0.55, 0.45]), lower="Old Lighthouse Museum | Michigan City (photo, 2007)"),
        L("c2-20", "And it's said to have a ghost. In 2026, a boating magazine wrote that the lighthouse is said to be haunted by its keeper, still on duty. Even the magazine admitted no one knows for sure.",
          QUOTE("said to still remain on duty", "Lakeland Boating, July 2026")),
        L("c2-21", "We couldn't find anyone who says they've seen her. Only the story that she's still on duty. Which would suit a woman who said she couldn't bear to see anyone else light her lamp.",
          P("lhx-search-04.jpg", tone="night", z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.55, 0.42]), gap=1.2),
    ]),

    # ------------------------------------------------------------------ 3. Mourning
    dict(id="c3", music="parlor", card=dict(type="chapter", n=3, title="Mourning", sub="The Barker Mansion · 1886 – 1910"), lines=[
        L("c3-01", "In downtown Michigan City stands the Barker Mansion.",
          P("barker-cat-01.jpg", tone="sepia-soft", z=[1.0, 1.1], f0=[0.5, 0.45], f1=[0.45, 0.4]), lower="Barker Mansion | 631 Washington St., Michigan City"),
        L("c3-02", "John H. Barker ran the Haskell and Barker Car Company, which built thousands of railroad freight cars a year. In 1905, he turned his family's home into a mansion of thirty-eight rooms.",
          P("mc-carworks-01.jpg", tone="bw", crop=[0.04, 0.05, 0.96, 0.95], z=[1.0, 1.1]), lower="A freight car built by Haskell & Barker | about 1918"),
        L("c3-03", "The family knew grief. In 1886, Barker built a hall at Trinity Episcopal Church in memory of three children, all of whom had died as babies.",
          TYPED("BARKER HALL, 1886", ["Trinity Episcopal Church, Michigan City.", "In memory of three children,", "all of whom died as babies."])),
        L("c3-04", "Both of Catherine Barker's parents died in 1910. When her father died that December, newspapers across the country reported that his entire fortune, thirty million dollars, went to her. She was fourteen.",
          [NEWS("np-barker-02-col.jpg", mode="hold", box=[0.300, 0.022, 0.700, 0.440], lower="The Durham Recorder | Dec. 8, 1910", w=1.15),
           NEWS("np-barker-04-head.jpg", mode="clip", z=[1.0, 1.08], rot=1.0, lower="The Spokane Press | Dec. 12, 1910")], sfx=[["page", 0.0]]),
        L("c3-05", "Victorians lived close to death, and they had rules for it. Clocks were stopped at the hour of a death. Mirrors were covered. Families wore black, sometimes for years, and had photographs taken of the dead.",
          TYPED("VICTORIAN MOURNING", ["Stop the clocks.", "Cover the mirrors.", "Wear black.", "Photograph the dead."])),
        L("c3-06", "The mansion's October candlelight tours are about those Victorian superstitions. But the museum is clear about what they are not.",
          P("barker-cat-01.jpg", tone="night", z=[1.1, 1.25], f0=[0.45, 0.45], f1=[0.5, 0.4])),
        L("c3-07", "This is not a haunted house, paranormal investigation, or ghost tour.",
          QUOTE("This is not a haunted house, paranormal investigation, or ghost tour.", "Barker Mansion, on its 2026 candlelight tour"), gap=0.6),
        L("c3-08", "Fifty years earlier, though, some people in La Porte believed they could do more than mourn the dead. They believed they could talk with them.",
          DARK, gap=1.0),
    ]),

    # ------------------------------------------------------------------ 4. The spirit rooms
    dict(id="c4", music="spirits", card=dict(type="chapter", n=4, title="The Spirit Rooms", sub="La Porte · the 1850s"), lines=[
        L("c4-01", "In the spring of 1848, two young sisters in Hydesville, New York, said they could talk with a spirit through rapping sounds. Within a few years, Spiritualism had spread across the country.",
          P("fox-sisters-05.jpg", fit="print", tone="bw", z=[1.0, 1.1]), lower="The Fox sisters | 1852"),
        L("c4-02", "Believers sat in circles in darkened rooms, hands on a table, and waited for the dead to answer.",
          P("table-turning-02.jpg", tone="paper", crop=[0.06, 0.03, 0.94, 0.97], z=[1.0, 1.12]), lower="Table-turning, as a French cartoonist saw it | 1853"),
        L("c4-03", "By the mid-1850s, according to the Indiana Historical Bureau, Spiritualism was fairly widespread in Indiana.",
          P("spirit-photo-08.jpg", fit="print", tone="sepia", z=[1.0, 1.1]), lower="A “spirit photograph” | about 1920"),
        L("c4-04", "Charles W. Cathcart was one of La Porte County's leading men. Born on the island of Madeira in 1809, he went to sea as a boy, settled near La Porte in 1831, and served in the Indiana Senate, in Congress, and, briefly, in the United States Senate.",
          TYPED("CHARLES W. CATHCART", ["Born on Madeira, 1809. At sea as a boy.", "Settles near La Porte, 1831.", "Indiana Senate, 1837 – 1840.", "U.S. House, 1845 – 1849.", "U.S. Senate, 1852 – 1853."])),
        L("c4-05", "He was a skeptic. When a family named Poston began holding spirit circles nearby, on a farm along the stage road between La Porte and Westville, he went to expose them.",
          P("seance-15.jpg", tone="night", crop=[0.05, 0.05, 0.95, 0.85], z=[1.0, 1.12]), lower="A seance in New York | 1909"),
        L("c4-06", "He built a gadget of his own: a paper tube of phosphorus, sulfur and acid that, turned upside down, would light up a dark room in a flash. He called it his lightning bug.",
          NEWS("hardinge-07.jpg", mode="zoom", box=[0.12, 0.43, 0.94, 0.62], hold=0.3, spot=[0.13, 0.480, 0.93, 0.590], spot_at=0.35),
          lower="Emma Hardinge, Modern American Spiritualism | 1870"),
        L("c4-07", "The lights went out, and the music began. A spirit the circle called Old King took up a bass drum, fastened to a frame above the table.",
          DARK, sfx=[["drum", 2.2], ["drum", 3.0], ["drum", 3.8]], gap=0.6),
        L("c4-08", "Cathcart slipped his lightning bug onto the middle of the table.",
          P("table-turning-27.jpg", tone="bw", crop=[0.05, 0.05, 0.95, 0.85], z=[1.0, 1.06], flash=2.4), sfx=[["flash", 2.4]], gap=1.4),
        L("c4-09", "In the Spiritual Telegraph, a Spiritualist newspaper in New York, he described what everyone saw: the stick beating the drum, as if handled from above, with no mortal nearer than about eight feet of it.",
          NEWS(H08, mode="zoom", box=H08_BOX, hold=0.3, spot=[0.03, 0.294, 0.87, 0.324], spot_at=0.45),
          lower="Cathcart's account, reprinted in Modern American Spiritualism | 1870"),
        L("c4-10", "What a picture for an artist, he wrote. Then, he said, the stick rose, drew a slow curve in the air, and dropped gently onto the shoulder of the Postons' daughter, the circle's medium.",
          [NEWS(H08, mode="hold", box=H08_BOX, spot=[0.03, 0.256, 0.87, 0.284], spot_at=0.05),
           NEWS(H08, mode="hold", box=H08_BOX, spot=[0.03, 0.325, 0.87, 0.350], spot_at=0.05)], gap=0.6),
        L("c4-11", "The skeptic was won over. Soon his own family was holding circles at home, with music, moving furniture and voices. His youngest child, he wrote, could see the spirits.",
          P("seance-14.jpg", tone="night", crop=[0.05, 0.05, 0.95, 0.85], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.42, 0.4]), lower="A seance in New York | 1909",
          sfx=[["triangle", 2.5]]),
        L("c4-11b", "He even made a joke of it. With many I have lost my standing as a philosopher, he wrote, but with all, I have won the reputation of a first-rate lamplighter.",
          NEWS(H08, mode="zoom", box=[0.03, 0.83, 0.88, 0.915], hold=0.3, spot=[0.03, 0.852, 0.87, 0.880], spot_at=0.4)),
        L("c4-12", "By 1858, a national directory of Spiritualists listed his circle under Indiana: Cathcart's Spirit Room, Laporte.",
          NEWS("register1859-01.jpg", mode="zoom", box=[0.08, 0.28, 0.86, 0.44], hold=0.3, spot=[0.37, 0.373, 0.80, 0.390], spot_at=0.5),
          lower="The Spiritualist Register | 1858"),
        L("c4-13", "And in 1870, in her history of American Spiritualism, the medium Emma Hardinge gave it a chapter of its own: Cathcart's Spirit Room.",
          [P("hardinge-c-07.jpg", fit="print", tone="bw", crop=[0.0, 0.0, 1.0, 1.0], z=[1.0, 1.08], lower="Emma Hardinge | in an 1884 book"),
           NEWS("hardinge-04.jpg", mode="zoom", box=[0.06, 0.385, 0.86, 0.48], hold=0.3, spot=[0.25, 0.452, 0.67, 0.470], spot_at=0.45,
                lower="Modern American Spiritualism, chapter 32 | 1870")]),
        L("c4-14", "We couldn't find where the spirit rooms stood. Charles Cathcart died in 1888, on his farm near La Porte. He's buried at Pine Lake Cemetery.",
          P("lp-lakes-16.jpg", tone="paper", crop=[0.0, 0.03, 0.55, 0.97], z=[1.05, 1.25], f0=[0.5, 0.5], f1=[0.35, 0.25]), lower="La Porte | an 1888 map", gap=1.0),
    ]),

    # ------------------------------------------------------------------ 5. Unknown persons
    dict(id="c5", music="graves", card=dict(type="chapter", n=5, title="Unknown Persons", sub="Pine Lake and Patton Cemeteries"), lines=[
        L("c5-01", "Pine Lake Cemetery, in La Porte, was established in 1856. Its first burial was two years later.",
          P("lp-pine-01.jpg", tone="sepia", crop=[0.06, 0.05, 0.96, 0.95], z=[1.0, 1.1], f0=[0.5, 0.5], f1=[0.5, 0.6]),
          lower="Pine Lake Cemetery | from the 1874 county atlas"),
        L("c5-02", "Graves from the town's old city cemetery were moved here.",
          P("lp-pine-01.jpg", tone="sepia", crop=[0.16, 0.47, 0.96, 0.92], z=[1.1, 1.3], f0=[0.5, 0.5], f1=[0.62, 0.55])),
        L("c5-03", "Not all of them had names. A marker there stands for four hundred and ninety-nine unknown persons, moved from an older burial ground.",
          BIG("499", cap="unknown persons")),
        L("c5-04", "Accounts disagree about when it happened. One says 1871. The marker itself says 1893.", TYPED("THE REBURIALS", ["One account: 1871.", "The marker: 1893."])),
        L("c5-05", "All that digging left a story behind. When one old coffin was opened, the story goes, the woman inside was found upside down and twisted, as if she had been buried alive.",
          DARK, gap=0.8),
        L("c5-06", "We found no record of it. Stories like it are told about old cemeteries all over the world.", SAME),
        L("c5-07", "Visitors tell of something else: shadows, like mist, above the stones.",
          P("lp-pine-01.jpg", tone="night", crop=[0.16, 0.47, 0.96, 0.92], z=[1.2, 1.35], f0=[0.45, 0.6], f1=[0.5, 0.52])),
        L("c5-08", "Elsewhere in La Porte is Patton Cemetery, begun, by one account, in 1841.",
          P("map-laporte-07.jpg", tone="paper", crop=[0.05, 0.05, 0.95, 0.6], z=[1.0, 1.12]), lower="La Porte | an 1886 insurance map"),
        L("c5-09", "Andrew Helgelien, a victim of Belle Gunness, is buried there. His stone calls him the last victim. His story is in our last documentary.",
          P("gunness-45-hi.jpg", crop=[0.899, 0.792, 0.981, 0.970], fit="print", tone="sepia", z=[1.0, 1.12], rot=0.0),
          lower="Andrew Helgelien's grave | on a 1908 postcard"),
        L("c5-10", "A neighbor once told of hearing voices in the cemetery at night, and looking out to find no one there.", DARK),
        L("c5-11", "This year, the trouble at Patton has been the weather. The derecho of August eleventh, 2026, brought gusts near sixty miles an hour to La Porte. Afterward, the historical society said the cemetery was unsafe for the public to enter, and canceled its October tour.",
          TYPED("PATTON CEMETERY, 2026", ["Aug. 11: a derecho, gusts near 60 mph in La Porte.", "After: unsafe for the public to enter.", "October's history tour: canceled."]), gap=1.0),
    ]),

    # ------------------------------------------------------------------ 6. The chapel
    dict(id="c6", music="chapel", card=dict(type="chapter", n=6, title="The Chapel", sub="Posey Chapel · Galena Township"), lines=[
        L("c6-01", "In the farm country northeast of La Porte, in Galena Township, there's a small cemetery called Posey Chapel.",
          MAP(**CO, cam0=[-86.70, 41.66, 0.55], cam1=[-86.64, 41.72, 0.32], move_end=0.85,
              places=[LAKE, place(LP, 0.0), place(MC, 0.0), place(ROLLING, 0.2), place(POSEY, 0.5, size=44)])),
        L("c6-02", "In 2011, when a local newspaper counted down the county's ten most haunted places, Posey Chapel was number one.", BIG("No. 1", cap="La Porte County's most haunted, by one 2011 count")),
        L("c6-03", "The legend, as it's told online: the church burned more than a hundred and fifty years ago, and its preacher took his own life near the gate.",
          DARK),
        L("c6-04", "Since then, people say, there have been lights in the trees, red eyes, a woman in white, and on some nights, the sound of a woman singing.",
          TYPED("WHAT PEOPLE SAY", ["Lights in the trees.", "Red eyes.", "A woman in white.", "A woman singing."])),
        L("c6-05", "Here's what the records say.", DARK, gap=0.5),
        L("c6-06", "A Methodist congregation was founded here in 1833, a year after the county itself.",
          P("lpcounty-x-10.jpg", tone="sepia", crop=[0.08, 0.10, 0.94, 0.52], z=[1.0, 1.12]), lower="A La Porte County farm | from the 1874 county atlas"),
        L("c6-07", "The county's first history, written in 1876, tells how its chapel began. A Methodist minister named Posey, sent to Galena Township, talked his congregation into building one.",
          NEWS(PACK, mode="zoom", box=PACK_BOX, hold=0.3, spot=[0.13, 0.415, 0.97, 0.500], spot_at=0.45),
          lower="Jasper Packard, History of La Porte County | 1876"),
        L("c6-07b", "Neighbors came from eight or ten miles away and worked for a week. The log chapel stood on an acre of land given by Whitman Goit, and it was named Posey Chapel, for the preacher who founded it.",
          NEWS(PACK, mode="hold", box=PACK_BOX, spot=[0.13, 0.540, 0.97, 0.625], spot_at=0.05)),
        L("c6-08", "By 1876, the log chapel had been torn down and replaced with a frame church. One modern writer says a fire came first, in 1855. If so, there really was a fire more than a hundred and fifty years ago.",
          [NEWS(PACK, mode="hold", box=PACK_BOX, spot=[0.13, 0.627, 0.97, 0.668], spot_at=0.05),
           TYPED("POSEY CHAPEL", ["1833: a Methodist congregation.", "About 1841: a log chapel, built in a week.", "By 1876: a frame church in its place.", "One modern account: a fire in 1855."])]),
        L("c6-09", "And there was another. In 1972, the church burned again, and this time it wasn't rebuilt. That writer says the fire was set on purpose.",
          BIG("1972", cap="the church burns again; it is not rebuilt")),
        L("c6-10", "Today, a pavilion stands where the chapel stood, among hundreds of graves.",
          MAP(**CO, cam0=[-86.64, 41.72, 0.32], cam1=[-86.632, 41.745, 0.18], move_end=0.9, places=[place(POSEY, 0.0, size=44)])),
        L("c6-11", "As for the preacher, there really was one, and the chapel carries his name. But we found no record that any preacher there took his own life, and no record of anyone dying in either fire.", SAME),
        L("c6-12", "It's still an active cemetery, where families bury their own. If you go, go by day, and leave it as you found it.", SAME, gap=1.0),
    ]),

    # ------------------------------------------------------------------ 7. The flagman
    dict(id="c7", music="rails", card=dict(type="chapter", n=7, title="The Flagman", sub="Flaherty's Siding · 1905"), lines=[
        L("c7-01", "On July thirty-first, 1905, the Muncie Evening Press ran a story about a ghost near La Porte, under the headline Headless Ghost Grows Uneasy.",
          TYPED("MUNCIE EVENING PRESS, JULY 31, 1905", ["HEADLESS GHOST", "GROWS UNEASY"]), sfx=[["page", 0.0]]),
        L("c7-01b", "Within two weeks, versions of the story were running in newspapers as far away as Connecticut, Virginia and Kansas.",
          NEWS("np-ghost-04-head.jpg", mode="clip", z=[1.0, 1.08], rot=-1.0), lower="Barbour County Index, Medicine Lodge, Kansas | Aug. 16, 1905", sfx=[["page", 0.0]]),
        L("c7-02", "It told of a place called Flaherty's Siding, where, after dark, a figure had been seen on the railroad platform.",
          P("rail-tank-02.jpg", tone="night", crop=[0.04, 0.0, 0.98, 0.35], z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.42, 0.5])),
        L("c7-03", "It had no head. It carried a dinner pail, and it swung its arms as if it were flagging an approaching train.",
          NEWS("np-ghost-04-drawing.jpg", mode="clip", z=[1.0, 1.12], rot=0.8), lower="“The Headless Apparition” | a newspaper drawing, 1905"),
        L("c7-04", "Then it would vanish, often with a shriek.", DARK, gap=0.6),
        L("c7-05", "Headless, the paper said, and acting for all the world like an animate thing.",
          NEWS("np-ghost-04-a.jpg", mode="hold", box=[0.1674, 0.7953, 0.8372, 0.9314], spot=[0.1674, 0.8081, 0.8372, 0.8337])),
        L("c7-06", "People believed it was Columbus Cole, a well-known local man who had been run over by an engine, close to the spot where the water tank stood. The accident, the paper said, had taken his head.",
          NEWS("np-ghost-03-col.jpg", mode="hold", box=[0.2105, 0.1661, 0.8789, 0.2446], spot=[0.2105, 0.1750, 0.8789, 0.2386]),
          lower="New Haven Morning Journal and Courier | Aug. 14, 1905, from the Indianapolis Sentinel"),
        L("c7-06b", "But in another version, printed in Kansas and Virginia, Cole had died in a boiler explosion that blew off the top of his head. Even in 1905, the story wouldn't hold still.",
          NEWS("np-ghost-04-b.jpg", mode="hold", box=[0.1674, 0.6593, 0.8372, 0.7582], spot=[0.1674, 0.6769, 0.8372, 0.7411]), lower="Barbour County Index | Aug. 16, 1905"),
        L("c7-07", "Some young men from town decided it was a hoax, and went out to prove it.",
          P("rail-tank-10.jpg", tone="night", crop=[0.0, 0.1, 1.0, 0.9], z=[1.0, 1.15], f0=[0.6, 0.5], f1=[0.45, 0.5])),
        L("c7-08", "The first night, they saw nothing.", DARK, gap=0.6),
        L("c7-09", "On the second night, one of them called for quiet. There, near the old water tank, stood the headless figure. They watched it for five minutes or more.",
          [NEWS("np-ghost-03-col.jpg", mode="hold", box=[0.2105, 0.6107, 0.8789, 0.6839], spot=[0.2105, 0.6214, 0.8789, 0.6762]),
           NEWS("np-ghost-03-col.jpg", mode="hold", box=[0.2105, 0.7232, 0.8789, 0.8036], spot=[0.2105, 0.7604, 0.8789, 0.7982])], sfx=[["wind", 0.0]]),
        L("c7-10", "Then they ran to the spot. It was gone.", DARK, gap=0.7),
        L("c7-11", "By one account, they recognized the dinner pail: the one Cole always carried to and from work. We were no longer skeptics, the paper quoted them, but believers.",
          [NEWS("np-ghost-03-col.jpg", mode="hold", box=[0.2105, 0.7232, 0.8789, 0.8036], spot=[0.2105, 0.7330, 0.8789, 0.7589]),
           NEWS("np-ghost-03-col.jpg", mode="hold", box=[0.2105, 0.8589, 0.8789, 0.9107], spot=[0.2105, 0.8727, 0.8789, 0.8996])]),
        L("c7-12", "We tried to find Columbus Cole. The Indianapolis version put the water tank on the Lake Erie railway. But we couldn't find a record of Cole's death, or even where Flaherty's Siding was. If you know, tell us in the comments.",
          TYPED("STILL UNKNOWN", ["When and how Columbus Cole died.", "Where Flaherty's Siding was,", "on the Lake Erie line near La Porte."])),
        L("c7-13", "And if you go looking, stay off the tracks. Trains still run through La Porte County, and they don't stop for ghosts.",
          P("mc-lake-02.jpg", tone="warm", z=[1.0, 1.12], f0=[0.5, 0.5], f1=[0.5, 0.45]), lower="South Shore Line, Michigan City | 1968", sfx=[["train", 0.5]], gap=0.8),
    ]),

    # ------------------------------------------------------------------ 8. Victory City
    dict(id="c8", music="war", card=dict(type="chapter", n=8, title="Victory City", sub="Kingsbury · 1940 – 1960"), lines=[
        L("c8-01", "In the fall of 1940, before the United States entered the Second World War, the government picked farmland south of La Porte for an ammunition plant.",
          [MAP(**CO, cam0=[-86.72, 41.56, 0.75], cam1=[-86.71, 41.53, 0.50], move_end=0.85,
               places=[place(LP, 0.0), place(KINGSBURY, 0.3), place(KFH, 0.55)], w=1.2),
           P("kingsbury-01.jpg", tone="bw", crop=[0.04, 0.02, 0.96, 0.40], z=[1.0, 1.12], lower="“The defense program comes to the cornfield” | a federal booklet, about 1941")]),
        L("c8-02", "It took in more than thirteen thousand acres. About two hundred and fifty families had to leave their homes and farms.",
          [BIG("13,454 acres", cap="about 250 families moved out", size=130),
           P("kingsbury-02.jpg", tone="bw", crop=[0.04, 0.02, 0.96, 0.40], z=[1.0, 1.12], lower="Rail spur and storage yard, Kingsbury | about 1941")]),
        L("c8-03", "The Kingsbury Ordnance Plant loaded shells and assembled fuses, up to a hundred and eighty thousand fuses a day.",
          P("kingsbury-02.jpg", fit="print", tone="bw", crop=[0.046, 0.530, 0.541, 0.903], z=[1.0, 1.08]),
          lower="A storehouse for finished ammunition, going up | Kingsbury, about 1941"),
        L("c8-04", "In May 1942, it employed twenty thousand, seven hundred and eighty-five people. Nearly half of them were women.",
          BIG("20,785", cap="workers, May 1942; nearly half of them women")),
        L("c8-05", "To house them, builders started nearly three thousand homes in a new town, laid out in a circle like a wagon wheel. At first, it was called Victory City. Today it's Kingsford Heights.",
          P("kingsbury2-01.jpg", tone="paper", crop=[0.30, 0.06, 0.62, 0.32], z=[1.0, 1.15], f0=[0.5, 0.5], f1=[0.45, 0.45]),
          lower="Kingsford Heights | U.S. Geological Survey map, 1958"),
        L("c8-06", "The work was dangerous. An explosive called tetryl turned some workers' skin orange.", SAME),
        L("c8-07", "In that 2011 list of the county's most haunted places, the plant was number ten. The writer said she'd been told that explosions had killed workers there during the war.",
          BIG("No. 10", cap="the 2011 list")),
        L("c8-08", "We found no record of deadly explosions there. One writer who researched the plant says there were never any major accidents.", SAME),
        L("c8-09", "The plant closed after the war, reopened for the Korean War, and closed for good around 1960.",
          TYPED("KINGSBURY ORDNANCE PLANT", ["1940: site chosen.", "1942: 20,785 workers.", "1945: closed.", "1951: reopened for Korea.", "About 1960: closed for good."])),
        L("c8-10", "In 1965, much of the land went to the state. Today it's the Kingsbury Fish and Wildlife Area, where people hunt, fish and hike.",
          P("kingsbury-04.jpg", tone="warm", z=[1.0, 1.15], f0=[0.5, 0.55], f1=[0.5, 0.65]), lower="The old plant land, from the air | 2025"),
        L("c8-11", "Other parts of the old plant are private industrial land, and off-limits. If you go, stay on public land, and wear orange in hunting season.", SAME),
        L("c8-12", "Sometimes a place feels haunted simply because so much happened there, and so few people remember.", SAME, gap=1.2),
    ]),

    # ------------------------------------------------------------------ epilogue
    dict(id="end", music="end", card=dict(type="chapter", kicker="EPILOGUE", title="The Light on the Pier", sub="Today"), tail=2.5, lines=[
        L("e01", "Most of these stories can't be proved. And the records don't back up some of them at all.",
          P("mc-lake-10.jpg", tone="warm", crop=[0.03, 0.06, 0.97, 0.92], z=[1.0, 1.12], f0=[0.5, 0.45], f1=[0.5, 0.4])),
        L("e02", "But the people in them were real. A keeper who climbed to her lamp for forty-three years. A congressman who sat in the dark and listened. Four hundred and ninety-nine people no one could name. A congregation that lost its church. A man the paper called Columbus Cole. And twenty thousand workers who went to war without going overseas.",
          dict(type="names", head="THE PEOPLE IN THE STORIES", names=[["Harriet Colfax", "keeper, 1861 – 1904"], ["Charles W. Cathcart", "of the Spirit Room"],
                                                                     ["499 unknown persons", "Pine Lake Cemetery"], ["The Posey Chapel congregation", "1833 – 1972"],
                                                                     ["Columbus Cole", "Flaherty's Siding"], ["20,785 workers", "Kingsbury, 1942"]], span=0.9)),
        L("e03", "Maybe that's what a ghost story is: a way of remembering.", DARK, gap=1.0),
        L("e04", "The Old Lighthouse Museum is open Wednesday through Sunday afternoons until the end of October.",
          TYPED("OLD LIGHTHOUSE MUSEUM", ["100 Heisman Harbor Rd., Michigan City", "Wed.-Sun., 1-4 p.m. Central, through Oct. 31", "Adults $10"])),
        L("e05", "The cemeteries are active, and they belong to the families. Go by day, be respectful, and stay off private land.",
          TYPED("IF YOU GO", ["Cemeteries: by day, and with respect.", "Patton Cemetery: check before you go.", "Railroad tracks and private land: stay off."])),
        L("e06", "The lamp Harriet Colfax tended went dark in 1904. But out at the end of the pier in Michigan City, a light still shines every night.",
          P("loc-lh-01.jpg", tone="warm", crop=[0.0, 0.0, 1.0, 0.85], z=[1.0, 1.15], f0=[0.5, 0.45], f1=[0.42, 0.45]), lower="Michigan City's pier light | photo by Carol M. Highsmith"),
        L("e07", "Some people like to think she's still keeping watch.", SAME, gap=1.5),
        L("e08", None, QUOTE("Sources, photo credits and visiting details are in the description.", None, size=46), hold=5.0),
    ]),
]


def build():
    script = {"title": "Haunted: The Ghost Stories of La Porte County", "chapters": CHAPTERS}
    json.dump(script, open(os.path.join(HERE, "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    words = sum(len(ln.get("say", "").split()) for ch in CHAPTERS for ln in ch["lines"])
    todo = sum(1 for ch in CHAPTERS for ln in ch["lines"] for v in (ln.get("v") if isinstance(ln.get("v"), list) else [ln.get("v")])
               if isinstance(v, dict) and v.get("by") == "picture to come")
    print(len(CHAPTERS), "chapters,", sum(len(ch["lines"]) for ch in CHAPTERS), "lines,", words, "words,", todo, "pictures to choose")


if __name__ == "__main__":
    build()
