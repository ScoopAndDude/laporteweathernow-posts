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

CHAPTERS = [
    # ------------------------------------------------------------------ cold open
    dict(id="open", music="open", tail=0.2, lines=[
        L("o01", "On the shore of Lake Michigan, for forty-three years, a woman climbed to the same lamp every night and lit it. Some people say she still does.",
          TODO("the old Michigan City lighthouse, at dusk"), sfx=[["waves", 0.0]]),
        L("o02", "Inland, a former congressman sat in the dark and listened to a drum that, he said, no one was playing.",
          TODO("a 19th-century séance engraving"), sfx=[["drum", 3.2]]),
        L("o03", "In a La Porte cemetery, a single marker stands for four hundred and ninety-nine unknown persons.",
          TODO("old cemetery, fog")),
        L("o04", "Out in the farm country, the story goes, a chapel burned more than a hundred and fifty years ago, and was never at peace again.",
          TODO("a country chapel at night")),
        L("o05", "And in the summer of 1905, a newspaper told of a man with no head, standing by the railroad tracks after dark, flagging down a train.",
          TODO("1905 newspaper: headless ghost"), sfx=[["train", 2.5]]),
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
          TODO("an 1860s map of La Porte County"), lower="La Porte | French for “the door”"),
        L("c1-02", "For generations before any settlers came, this was Potawatomi land.",
          TODO("Potawatomi people in Indiana, George Winter, 1837")),
        L("c1-03", "Under treaties signed in 1826 and 1832, the Potawatomi ceded their land here to the United States. In 1838, the government forced hundreds of Potawatomi people to leave Indiana for Kansas. The march is remembered as the Trail of Death. Potawatomi people still live in the region today.",
          TYPED("POTAWATOMI LAND", ["1826 and 1832: treaties with the United States.", "1838: hundreds forced from Indiana to Kansas,", "on the march remembered as the Trail of Death."]), gap=0.8),
        L("c1-04", "La Porte County was created in 1832.", P("lp-court-08.jpg", fit="print", z=[1.0, 1.08]), lower="La Porte County's second courthouse | about 1848"),
        L("c1-05", "On the lake, at the mouth of Trail Creek, Isaac Elston founded Michigan City on land he bought in 1830. On July Fourth, 1836, the first commercial ship, the Sea Serpent, sailed into the creek.",
          TODO("Michigan City harbor, old postcard"), lower="Michigan City, Indiana"),
        L("c1-06", "The railroads came in 1852, and the factories after them.", TODO("railroad / car works, old photo")),
        L("c1-07", "In 1860, the state began building a prison at Michigan City. In 1933, ten inmates broke out of it with pistols smuggled in by John Dillinger.",
          P("prison-33.jpg", tone="warm", crop=[0.02, 0.03, 0.98, 0.78], z=[1.0, 1.1], f0=[0.4, 0.5], f1=[0.55, 0.5]), lower="Indiana State Prison | Michigan City, about 1908"),
        L("c1-08", "For all its history, we couldn't find a ghost story about the prison that anyone could trace to a source.", SAME),
        L("c1-09", "Even the land has changed. A sand dune about two hundred feet tall, the Hoosier Slide, once towered over the harbor. By 1920, it had been dug away, much of it to make glass.",
          P("laporte-old-12.jpg", tone="warm", z=[1.0, 1.12], f0=[0.6, 0.5], f1=[0.45, 0.45]), lower="The harbor and the Hoosier Slide | 1909"),
        L("c1-10", "A place where so much has come and gone leaves stories behind. Some are history. Some are legend. Many are a little of both.", TODO("La Porte old street, dusk")),
        L("c1-11", "In this film, we'll tell you which is which, as best the records allow.", SAME, gap=0.8),
    ]),

    # ------------------------------------------------------------------ 2. The keeper
    dict(id="c2", music="keeper", card=dict(type="chapter", n=2, title="The Keeper", sub="Michigan City · 1861 – 1904"), lines=[
        L("c2-01", "In 1853, a young music teacher named Harriet Colfax moved from Ogdensburg, New York, to Michigan City, with her brother.",
          TODO("Harriet Colfax portrait, or Michigan City 1850s")),
        L("c2-02", "He ran a newspaper, and she helped him set the type. In 1856, he died of tuberculosis. He was twenty-six.",
          TYPED("HARRIET COLFAX", ["From Ogdensburg, New York.", "Michigan City, 1853: a music teacher,", "setting type at her brother's newspaper."])),
        L("c2-03", "In 1861, Harriet was appointed keeper of the Michigan City lighthouse.",
          TODO("the 1858 lighthouse, old photo"), lower="The Michigan City lighthouse | built 1858"),
        L("c2-04", "Newspapers long said she owed the job to her cousin, Schuyler Colfax, a congressman from South Bend who later became vice president. She told a reporter she'd been appointed by Mr. Lincoln, soon after his inauguration.",
          [TODO("Schuyler Colfax portrait"), QUOTE("appointed by Mr. Lincoln soon after his inauguration", "Harriet Colfax, in an 1881 interview")]),
        L("c2-05", "The lighthouse was new, built in 1858 of stone and brick, with the light in a cupola on the roof.", TODO("HABS drawing or photo of the lighthouse")),
        L("c2-06", "Every evening, she lit the lamps. At first they burned lard oil. It had to be heated first, and on cold nights it could harden again before she got it to the light.",
          TODO("lighthouse lamp / Fresnel lens")),
        L("c2-07", "In 1871, a second light was built out on the pier, at the end of a long, raised wooden walkway. A few years later, it was moved to the west pier, across Trail Creek. To reach it, she rowed across the creek in a small boat.",
          TODO("the pier light and the elevated walk, old postcard")),
        L("c2-08", "In storms, the walk was dangerous. In 1872, she wrote, the waves dashed over the top of the beacon.",
          TODO("storm waves at the Michigan City pier"), sfx=[["waves", 0.0]]),
        L("c2-09", "Her log for May twenty-eighth, 1873: A terrible hurricane tonight at about the time of lighting up. Narrowly escaped being swept into the lake.",
          LETTER("A terrible hurricane to-night at about the time of lighting up. Narrowly escaped being swept into the lake.", by="Harriet Colfax's log, May 28, 1873", greeting="May 28, 1873.")),
        L("c2-10", "In 1886, a storm knocked the pier beacon into the lake. And an 1890 newspaper story told how, one night, she found the beacon's lock tampered with, and broke a pane of glass to get the lamp lit.",
          TYPED("STORMS AND DANGERS", ["1872, her log: waves over the beacon.", "1873, her log: nearly swept into the lake.", "1886: a storm takes the beacon.", "1890, a newspaper: a tampered lock."])),
        L("c2-11", "She kept the light for forty-three years. People called her Old Faithful.", BIG("43 years", cap="keeper of the Michigan City light, 1861 – 1904")),
        L("c2-12", "She didn't keep it alone. Ann Hartwell, a teacher she had known in Ogdensburg, followed her to Michigan City and lived with her at the lighthouse. The National Park Service calls Ann her lifelong companion.",
          TODO("the lighthouse keeper's house")),
        L("c2-13", "Ann taught in the public schools for about twenty-five years, then opened a book exchange that became the area's first lending library.",
          TYPED("ANN HARTWELL", ["A teacher in Michigan City's public schools", "for about twenty-five years.", "Then: the area's first lending library."])),
        L("c2-14", "In October 1904, at about eighty years old, Harriet Colfax retired.", TODO("1904 newspaper: Miss Colfax retires")),
        L("c2-15", "As she got ready to leave, a Chicago newspaper quoted her: I could not bear to see anyone else light my lamp.",
          QUOTE("I could not bear to see anyone else light my lamp.", "Harriet Colfax, quoted in the Chicago Daily Tribune, Oct. 2, 1904"), gap=0.9),
        L("c2-16", "Six days after she retired, the light in the old lighthouse was put out for good. The lantern came off the roof, and a new light took its place at the end of the pier.",
          TODO("the pierhead light, about 1910")),
        L("c2-17", "Harriet and Ann moved into a new home. In January, Ann died. That April, Harriet died too.",
          TYPED("1905", ["January: Ann Hartwell dies.", "April: Harriet Colfax dies.", "Both are buried at Greenwood Cemetery."]), gap=0.8),
        L("c2-18", "They're buried in Greenwood Cemetery, in Michigan City.", SAME),
        L("c2-19", "The old lighthouse has been a museum since 1973, run by the Michigan City Historical Society.",
          TODO("the Old Lighthouse Museum today"), lower="Old Lighthouse Museum | Michigan City"),
        L("c2-20", "And it's said to have a ghost. In 2026, a boating magazine wrote that the lighthouse is said to be haunted by its keeper, still on duty. Even the magazine admitted no one knows for sure.",
          QUOTE("said to still remain on duty", "Lakeland Boating, July 2026")),
        L("c2-21", "We couldn't find anyone who says they've seen her. Only the story that she's still on duty. Which would suit a woman who said she couldn't bear to see anyone else light her lamp.",
          TODO("the lighthouse lantern at night"), gap=1.2),
    ]),

    # ------------------------------------------------------------------ 3. Mourning
    dict(id="c3", music="parlor", card=dict(type="chapter", n=3, title="Mourning", sub="The Barker Mansion · 1886 – 1910"), lines=[
        L("c3-01", "In downtown Michigan City stands the Barker Mansion.", TODO("the Barker Mansion"), lower="Barker Mansion | 631 Washington St., Michigan City"),
        L("c3-02", "John H. Barker ran the Haskell and Barker Car Company, which built thousands of railroad freight cars a year. In 1905, he turned his family's home into a mansion of thirty-eight rooms.",
          TODO("Haskell & Barker car works, old postcard")),
        L("c3-03", "The family knew grief. In 1886, Barker built a hall at Trinity Episcopal Church in memory of three children, all of whom had died as babies.",
          TODO("Trinity Episcopal Church, Michigan City")),
        L("c3-04", "A marker at the mansion says both of Catherine Barker's parents died in 1910. She was fourteen, and, the marker says, the world's richest heiress.",
          TODO("1910 newspaper: Catherine Barker, heiress")),
        L("c3-05", "Victorians lived close to death, and they had rules for it. Clocks were stopped at the hour of a death. Mirrors were covered. Families wore black, sometimes for years, and had photographs taken of the dead.",
          TYPED("VICTORIAN MOURNING", ["Stop the clocks.", "Cover the mirrors.", "Wear black.", "Photograph the dead."])),
        L("c3-06", "The mansion's October candlelight tours are about those Victorian superstitions. But the museum is clear about what they are not.",
          SAME),
        L("c3-07", "This is not a haunted house, paranormal investigation, or ghost tour.",
          QUOTE("This is not a haunted house, paranormal investigation, or ghost tour.", "Barker Mansion, on its 2026 candlelight tour"), gap=0.6),
        L("c3-08", "Fifty years earlier, though, some people in La Porte believed they could do more than mourn the dead. They believed they could talk with them.",
          DARK, gap=1.0),
    ]),

    # ------------------------------------------------------------------ 4. The spirit rooms
    dict(id="c4", music="spirits", card=dict(type="chapter", n=4, title="The Spirit Rooms", sub="La Porte · the 1850s"), lines=[
        L("c4-01", "In the spring of 1848, two young sisters in Hydesville, New York, said they could talk with a spirit through rapping sounds. Within a few years, Spiritualism had spread across the country.",
          TODO("the Fox sisters, engraving")),
        L("c4-02", "Believers sat in circles in darkened rooms, hands on a table, and waited for the dead to answer.", TODO("table-turning séance engraving")),
        L("c4-03", "By the mid-1850s, according to the Indiana Historical Bureau, Spiritualism was fairly widespread in Indiana.", SAME),
        L("c4-04", "Charles W. Cathcart was one of La Porte County's leading men. Born on the island of Madeira in 1809, he served in the Indiana Senate, in Congress, and, briefly, in the United States Senate.",
          TYPED("CHARLES W. CATHCART", ["Born on Madeira, 1809.", "Indiana Senate, 1837 – 1840.", "U.S. House, 1845 – 1849.", "U.S. Senate, 1852 – 1853."])),
        L("c4-05", "He was a skeptic. When he heard about a spirit circle at the home of a Mr. Poston, in La Porte County, he went to expose it.",
          TODO("a parlor séance, 1850s engraving")),
        L("c4-06", "He brought along a homemade device that could light up the dark room in a flash.", SAME, sfx=[["flash", 2.0]]),
        L("c4-07", "The lights went out. A spirit the circle called Old King took up a bass drum.", DARK, sfx=[["drum", 1.8], ["drum", 3.0]], gap=0.6),
        L("c4-08", "Cathcart set off his flash.", DARK, sfx=[["flash", 0.6]], gap=0.8),
        L("c4-09", "He described what he saw in the Spiritual Telegraph, a Spiritualist newspaper in New York: the stick beating the drum, as if handled from above, with no mortal nearer than about eight feet of it.",
          QUOTE("no mortal nearer than about eight feet of it", "Charles W. Cathcart, in the Spiritual Telegraph")),
        L("c4-10", "What a picture for an artist, he wrote.", QUOTE("What a picture for an artist!", "Charles W. Cathcart, in the Spiritual Telegraph"), gap=0.6),
        L("c4-11", "The skeptic started holding circles of his own, and they were even livelier: flying furniture, voices with no bodies, and spirits playing music in the dark.",
          TODO("spirit musicians / instruments engraving"), sfx=[["triangle", 2.5]]),
        L("c4-12", "In 1859, a national directory of Spiritualists listed them by name: Cathcart's Spirit Rooms, Laporte.",
          TYPED("THE SPIRITUALIST REGISTER, 1859", ["Trance mediums:", "…", "Cathcart's Spirit Rooms, Laporte."])),
        L("c4-13", "And in 1870, in her history of American Spiritualism, the medium Emma Hardinge gave them a chapter of their own: Cathcart's Spirit Room.",
          TODO("Hardinge 1870, the Cathcart chapter page")),
        L("c4-14", "We couldn't find where the spirit rooms stood. Charles Cathcart died in 1888, on his farm near La Porte. He's buried at Pine Lake Cemetery.",
          TODO("La Porte, 1850s-1880s view"), gap=1.0),
    ]),

    # ------------------------------------------------------------------ 5. Unknown persons
    dict(id="c5", music="graves", card=dict(type="chapter", n=5, title="Unknown Persons", sub="Pine Lake and Patton Cemeteries"), lines=[
        L("c5-01", "Pine Lake Cemetery, in La Porte, was established in 1856. Its first burial was two years later.", TODO("Pine Lake, La Porte, old postcard"), lower="Pine Lake | La Porte"),
        L("c5-02", "Graves from the town's old city cemetery were moved here.", TODO("old cemetery")),
        L("c5-03", "Not all of them had names. A marker there stands for four hundred and ninety-nine unknown persons, moved from an older burial ground.",
          BIG("499", cap="unknown persons")),
        L("c5-04", "Accounts disagree about when it happened. One says 1871. The marker itself says 1893.", TYPED("THE REBURIALS", ["One account: 1871.", "The marker: 1893."])),
        L("c5-05", "All that digging left a story behind. When one old coffin was opened, the story goes, the woman inside was found upside down and twisted, as if she had been buried alive.",
          DARK, gap=0.8),
        L("c5-06", "We found no record of it. Stories like it are told about old cemeteries all over the world.", SAME),
        L("c5-07", "Visitors tell of something else: shadows, like mist, above the stones.", TODO("cemetery stones in fog")),
        L("c5-08", "Elsewhere in La Porte is Patton Cemetery, begun, by one account, in 1841.", TODO("La Porte, old view (Patton)")),
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
        L("c6-06", "A Methodist congregation was founded here in 1833, a year after the county itself.", TODO("1830s Methodist / country church engraving")),
        L("c6-07", "The cemetery began as a family plot. It takes its name from Ida Posey, who, by one account, helped build a chapel here in 1841.",
          TYPED("POSEY CHAPEL", ["1833: a Methodist congregation.", "By one account:", "1841, a chapel, with Ida Posey's help;", "1855, rebuilt after a fire."])),
        L("c6-08", "By the same account, the chapel burned and was rebuilt in 1855. So, by that account, there really was a fire more than a hundred and fifty years ago.", SAME),
        L("c6-09", "And there was another. In 1972, the church burned again, and this time it wasn't rebuilt. One writer says the fire was set on purpose.",
          BIG("1972", cap="the church burns again; it is not rebuilt")),
        L("c6-10", "Today, a pavilion stands where the chapel stood, among hundreds of graves.", TODO("country cemetery, quiet")),
        L("c6-11", "As for the preacher, we found no record that any preacher there took his own life, and no record of anyone dying in either fire.", SAME),
        L("c6-12", "It's still an active cemetery, where families bury their own. If you go, go by day, and leave it as you found it.", SAME, gap=1.0),
    ]),

    # ------------------------------------------------------------------ 7. The flagman
    dict(id="c7", music="rails", card=dict(type="chapter", n=7, title="The Flagman", sub="Flaherty's Siding · 1905"), lines=[
        L("c7-01", "On July thirty-first, 1905, the Muncie Evening Press ran a story about a ghost near La Porte, under the headline Headless Ghost Grows Uneasy.",
          TYPED("MUNCIE EVENING PRESS, JULY 31, 1905", ["HEADLESS GHOST", "GROWS UNEASY"]), sfx=[["page", 0.0]]),
        L("c7-02", "It told of a place called Flaherty's Siding, where, after dark, a figure had been seen on the railroad platform.",
          TODO("a small railroad station / platform, about 1905")),
        L("c7-03", "It had no head. It carried a dinner pail, and it swung its arms as if it were flagging an approaching train.",
          TODO("railroad water tank, about 1905")),
        L("c7-04", "Then it would vanish, often with a shriek.", DARK, gap=0.6),
        L("c7-05", "Headless, the paper said, and acting for all the world like an animate thing.",
          QUOTE("Headless, and acting for all the world like an animate thing", "Muncie Evening Press, July 31, 1905")),
        L("c7-06", "People believed it was Columbus Cole, a well-known local man who had been run over by an engine, close to the spot where the water tank stood. The accident, the paper said, had taken his head.",
          TODO("steam locomotive at night")),
        L("c7-07", "Some young men from town decided it was a hoax, and went out to prove it.", SAME),
        L("c7-08", "The first night, they saw nothing.", DARK, gap=0.6),
        L("c7-09", "On the second night, one of them called for quiet. There, near the old water tank, stood the headless figure. They watched it for five minutes or more.",
          TODO("water tank by the tracks, night"), sfx=[["wind", 0.0]]),
        L("c7-10", "Then they ran to the spot. It was gone.", DARK, gap=0.7),
        L("c7-11", "By one account, they recognized the dinner pail: the one Cole always carried to and from work. We were no longer skeptics, the paper quoted them, but believers.",
          QUOTE("We were no longer skeptics, but believers.", "Muncie Evening Press, July 31, 1905")),
        L("c7-12", "We tried to find Columbus Cole. We couldn't find a record of his death, which railroad it was, or even where Flaherty's Siding was. If you know, tell us in the comments.",
          TYPED("STILL UNKNOWN", ["When Columbus Cole died.", "Which railroad it was.", "Where Flaherty's Siding was."])),
        L("c7-13", "And if you go looking, stay off the tracks. Trains still run through La Porte County, and they don't stop for ghosts.",
          TODO("La Porte railroad depot, old postcard"), sfx=[["train", 0.5]], gap=0.8),
    ]),

    # ------------------------------------------------------------------ 8. Victory City
    dict(id="c8", music="war", card=dict(type="chapter", n=8, title="Victory City", sub="Kingsbury · 1940 – 1960"), lines=[
        L("c8-01", "In the fall of 1940, before the United States entered the Second World War, the government picked farmland south of La Porte for an ammunition plant.",
          MAP(**CO, cam0=[-86.72, 41.56, 0.75], cam1=[-86.71, 41.53, 0.50], move_end=0.85,
              places=[place(LP, 0.0), place(KINGSBURY, 0.3), place(KFH, 0.55)])),
        L("c8-02", "It took in more than thirteen thousand acres. About two hundred and fifty families had to leave their homes and farms.",
          BIG("13,454 acres", cap="about 250 families moved out", size=130)),
        L("c8-03", "The Kingsbury Ordnance Plant loaded shells and assembled fuses, up to a hundred and eighty thousand fuses a day.", TODO("ordnance plant / fuses, 1940s")),
        L("c8-04", "In May 1942, it employed twenty thousand, seven hundred and eighty-five people. Nearly half of them were women.",
          BIG("20,785", cap="workers, May 1942; nearly half of them women")),
        L("c8-05", "To house them, builders started nearly three thousand homes in a new town, laid out in a circle like a wagon wheel. At first, it was called Victory City. Today it's Kingsford Heights.",
          TODO("Kingsford Heights / wagon wheel plan")),
        L("c8-06", "The work was dangerous. An explosive called tetryl turned some workers' skin orange.", SAME),
        L("c8-07", "In that 2011 list of the county's most haunted places, the plant was number ten. The writer said she'd been told that explosions had killed workers there during the war.",
          BIG("No. 10", cap="the 2011 list")),
        L("c8-08", "We found no record of deadly explosions there. One writer who researched the plant says there were never any major accidents.", SAME),
        L("c8-09", "The plant closed after the war, reopened for the Korean War, and closed for good around 1960.",
          TYPED("KINGSBURY ORDNANCE PLANT", ["1940: site chosen.", "1942: 20,785 workers.", "1945: closed.", "1951: reopened for Korea.", "About 1960: closed for good."])),
        L("c8-10", "In 1965, much of the land went to the state. Today it's the Kingsbury Fish and Wildlife Area, where people hunt, fish and hike.",
          TODO("Kingsbury Fish & Wildlife Area today")),
        L("c8-11", "Other parts of the old plant are private industrial land, and off-limits. If you go, stay on public land, and wear orange in hunting season.", SAME),
        L("c8-12", "Sometimes a place feels haunted simply because so much happened there, and so few people remember.", SAME, gap=1.2),
    ]),

    # ------------------------------------------------------------------ epilogue
    dict(id="end", music="end", card=dict(type="chapter", kicker="EPILOGUE", title="The Light on the Pier", sub="Today"), tail=2.5, lines=[
        L("e01", "Most of these stories can't be proved. And the records don't back up some of them at all.", TODO("lake at dusk")),
        L("e02", "But the people in them were real. A keeper who climbed to her lamp for forty-three years. A congressman who sat in the dark and listened. Four hundred and ninety-nine people no one could name. A congregation that lost its church. A man the paper called Columbus Cole. And twenty thousand workers who went to war without going overseas.",
          dict(type="names", head="THE PEOPLE IN THE STORIES", names=[["Harriet Colfax", "keeper, 1861 – 1904"], ["Charles W. Cathcart", "of the Spirit Rooms"],
                                                                     ["499 unknown persons", "Pine Lake Cemetery"], ["The Posey Chapel congregation", "1833 – 1972"],
                                                                     ["Columbus Cole", "Flaherty's Siding"], ["20,785 workers", "Kingsbury, 1942"]], span=0.9)),
        L("e03", "Maybe that's what a ghost story is: a way of remembering.", DARK, gap=1.0),
        L("e04", "The Old Lighthouse Museum is open Wednesday through Sunday afternoons until the end of October.",
          TYPED("OLD LIGHTHOUSE MUSEUM", ["100 Heisman Harbor Rd., Michigan City", "Wed.-Sun., 1-4 p.m. Central, through Oct. 31", "Adults $10"])),
        L("e05", "The cemeteries are active, and they belong to the families. Go by day, be respectful, and stay off private land.",
          TYPED("IF YOU GO", ["Cemeteries: by day, and with respect.", "Patton Cemetery: check before you go.", "Railroad tracks and private land: stay off."])),
        L("e06", "The lamp Harriet Colfax tended went dark in 1904. But out at the end of the pier in Michigan City, a light still shines every night.",
          TODO("the pierhead light at night")),
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
