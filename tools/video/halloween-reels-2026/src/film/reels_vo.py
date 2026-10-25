"""Narration for the four Facebook reels (Oct. 22, 2026), one sentence at a time so caption timing is exact.

python3 reels_vo.py [NAME ...]  ->  shorts/r_<name>/vo.wav (24 kHz) and vo.json
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE, SPEED, LANG, RATE = "af_heart", 1.02, "en-us", 24000
SAY = [(r"\bLa Porte\b", "Luh-Port"), (r"\bHelgelien\b", "Hel-guh-leen"), (r"\b1908\b", "nineteen-oh-eight"),
       (r"\b1815\b", "eighteen fifteen"), (r"\b1931\b", "nineteen thirty-one"),
       (r"\bmid-1900s\b", "mid-nineteen-hundreds"), (r"\b5:43\b", "five forty-three"), (r"\b6:10\b", "six ten"),
       (r"\b5 to 7\b", "five to seven"), (r"\b1833\b", "eighteen thirty-three"), (r"\b1972\b", "nineteen seventy-two"),
       (r"\b1841\b", "eighteen forty-one"), (r"\b2008\b", "two thousand eight"), (r"\b5:16\b", "five sixteen"),
       (r"\b5:51\b", "five fifty-one"), (r"\b11:12\b", "eleven twelve"), (r"\b10:49\b", "ten forty-nine"),
       (r"\b4:41\b", "four forty-one"), (r"\b4:17\b", "four seventeen"), (r"\b2 AM\b", "two A M"),
       (r"\bNERDS\b", "Nerds"), (r"M&M's", "M and M's"), (r"CandyStore\.com", "Candy Store dot com")]

# name: [(paragraph, pause after it)]
REELS = {
    "belle3": [
        ("Men answered her newspaper ad. Then one of them disappeared.", 0.5),
        ("Her ad read: comely widow, owns a large farm in La Porte County. Triflers need not apply.", 0.45),
        ("Andrew Helgelien, a South Dakota farmer, wrote back. Her letters told him to bring his money, "
         "and to come prepared to stay forever.", 0.45),
        ("In January 1908, he arrived with nearly three thousand dollars, and was never seen alive again.", 0.55),
        ("Double-tap for Part 4: the clue that didn't fit.", 0.0),
    ],
    "belle4": [
        ("Was the woman in the fire really Belle Gunness? Or just the story the papers told?", 0.5),
        ("A doctor who knew her said the body was shorter, and far lighter. "
         "\"It is not that of Mrs. Gunness.\"", 0.45),
        ("But her dentist said gold dental work from the ashes was hers, and the coroner ruled it was Belle.", 0.5),
        ("Two stories. They can't both be true.", 0.55),
        ("Double-tap for Part 5: the woman arrested in Los Angeles in 1931.", 0.0),
    ],
    "belle5": [
        ("Was Belle Gunness still alive in 1931?", 0.5),
        ("In Los Angeles, a housekeeper named Esther Carlson was charged with poisoning the eighty-one-year-old "
         "man she worked for.", 0.45),
        ("She died of tuberculosis before her trial.", 0.45),
        ("Two people from La Porte viewed her body and swore it was Belle. In her trunk was a photo of three "
         "children, said to be Belle's.", 0.55),
        ("No one ever proved it. Double-tap if you think Belle got away with it.", 0.0),
    ],
    "frank": [
        ("Frankenstein and Dracula trace back to the same rainy summer, and it started with a volcano.", 0.5),
        ("In 1815, Mount Tambora erupted. The next summer turned cold and dark.", 0.45),
        ("Stuck inside on Lake Geneva, Lord Byron, Mary Shelley and John Polidori bet on who could write "
         "the scariest story.", 0.45),
        ("Mary wrote Frankenstein. Polidori wrote The Vampyre, which started the craze that led to Dracula.", 0.55),
        ("Double-tap for La Porte's own Halloween stories. They're just as strange.", 0.0),
    ],
    "wx": [
        ("La Porte's weather was once so strange, scientists studied it.", 0.45),
        ("This week? Mostly dry and near seventy, right up to Halloween.", 0.45),
        ("But for decades in the mid-1900s, La Porte got more rain, thunderstorms and hail than the towns "
         "around it.", 0.45),
        ("One scientist blamed pollution from the steel mills upwind, in Chicago and Gary. "
         "Others still argue about it.", 0.55),
        ("Double-tap for the full weather update, and more La Porte weather history.", 0.0),
    ],
    # Halloween forecast: NWS as of Sun., Oct. 25 (re-record with the newest forecast before it posts)
    "hwfc": [
        ("Will it rain on trick-or-treat? Here's the latest look at Halloween in La Porte.", 0.45),
        ("Saturday looks mild and mostly cloudy, with a high near 71 and only a slight chance of a shower.", 0.45),
        ("Trick-or-treat is 5 to 7. The sun sets at 5:43, and it's dark by about 6:10.", 0.45),
        ("Showers are likely Saturday night, but the best chance looks later, into Sunday.", 0.5),
        ("It can still change, so double-tap for the update.", 0.0),
    ],
    "belle6": [
        ("Almost a hundred years after the fire, scientists dug up the headless woman.", 0.45),
        ("She'd been buried near Chicago in 1908, in the plot of Belle's first husband.", 0.45),
        ("Researchers tried to match her DNA to an envelope Belle had mailed to a suitor.", 0.45),
        ("But the old sample couldn't be properly tested. The answer is still buried.", 0.5),
        ("In 2008, her victims' descendants finally gave their graves headstones. Double-tap to remember them.", 0.0),
    ],
    # trend reels, Oct. 25: tonight's Hunter's Moon, Indiana's favorite candy, the clocks falling back
    "moon": [
        ("Tonight's full moon, the Hunter's Moon, rises over La Porte at 5:16.", 0.45),
        ("Look east-northeast. The sun doesn't set until 5:51, so you'll catch it coming up in daylight.", 0.45),
        ("It's officially full at 11:12 tonight, and the forecast is partly cloudy.", 0.45),
        ("On Halloween, the moon won't rise until 10:49, so bring a flashlight for trick-or-treat.", 0.5),
        ("Double-tap if you're going out to see it.", 0.0),
    ],
    "candy": [
        ("Indiana's favorite Halloween candy this year isn't chocolate.", 0.45),
        ("It's NERDS Gummy Clusters, in CandyStore.com's new state-by-state rankings.", 0.45),
        ("Next door, Illinois picked Sour Patch Kids. Michigan went with Starburst, and Ohio chose Blow Pops.", 0.45),
        ("Across the country, the top five are M&M's, Sour Patch Kids, Skittles, Reese's and NERDS Gummy Clusters.",
         0.5),
        ("Agree? Double-tap, and tell us the best candy to get in La Porte.", 0.0),
    ],
    "dst": [
        ("One week from today, La Porte's sunsets jump an hour earlier.", 0.45),
        ("Daylight saving time ends at 2 AM next Sunday, so set your clocks back an hour Saturday night.", 0.45),
        ("Halloween's sunset is 5:43. The next night, it's 4:41.", 0.45),
        ("And it keeps sliding, to 4:17 by early December.", 0.5),
        ("Love it or hate it? Double-tap if you'll take the extra hour of sleep.", 0.0),
    ],
    # La Porte's own legends (from laporteweathernow.com/hauntings)
    "posey": [
        ("Near Hesston, there's a country cemetery where people say they hear bells.", 0.45),
        ("Posey Chapel Cemetery dates to 1833. Its last chapel was destroyed by arson in 1972.", 0.45),
        ("But legend tells of an older fire, set by a deranged preacher, that killed members of his own "
         "congregation.", 0.5),
        ("Visitors report a woman in white, singing, and lights that bounce between the graves.", 0.5),
        ("Visit in daylight, and double-tap for the next La Porte legend.", 0.0),
    ],
    "patton": [
        ("Some of Belle Gunness's victims are buried right here in La Porte.", 0.45),
        ("Patton Cemetery dates to 1841, and holds some of the oldest graves in the area.", 0.45),
        ("Her teenage foster daughter, Jennie Olson, rests here. So does Andrew Helgelien, the farmer who answered "
         "her ad.", 0.5),
        ("Visitors describe shadows between the stones, voices with no one there, and a heavy sadness near her "
         "victims.", 0.5),
        ("Please visit in daylight, and double-tap for the next La Porte legend.", 0.0),
    ],
    "orr": [
        ("Some people in La Porte call Orr Lake Road Hangman's Road.", 0.45),
        ("The story goes, a couple's car died out here one night. He went for help, and told her to lock the "
         "doors.", 0.45),
        ("All night, she heard a slow scraping across the roof.", 0.55),
        ("At dawn, police told her not to look back. It was his shoes, scraping the roof all night.", 0.55),
        ("There's no record it ever happened. It's an old Indiana legend. Double-tap if you heard it growing up.", 0.0),
    ],
}
LEAD = 0.3
GAP_S = 0.28


def spoken(t):
    for pat, rep in SAY:
        t = re.sub(pat, rep, t)
    return t


def sentences(p):
    p = p.replace("Mrs.", "Mrs\u00a7").replace(".com", "\u00b6com")
    out = re.findall(r"[^.?!]+(?:\.\.\.[^.?!]+)*[.?!]+[\"”]?", p)
    return [s.strip().replace("Mrs\u00a7", "Mrs.").replace("\u00b6com", ".com") for s in out if s.strip()]


def trim(a, thr=0.004, pad=0.03):
    idx = np.nonzero(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a
    return a[max(0, idx[0] - int(pad * RATE)):min(len(a), idx[-1] + int(pad * RATE))]


def main(names):
    k = Kokoro(os.path.join(ROOT, "models", "kokoro-v1.0.onnx"), os.path.join(ROOT, "models", "voices-v1.0.bin"))
    for name in names:
        out = os.path.join(ROOT, "shorts", "r_" + name)
        os.makedirs(out, exist_ok=True)
        pieces = [np.zeros(int(LEAD * RATE), np.float32)]
        t = LEAD
        items = []
        for pi, (p, after) in enumerate(REELS[name]):
            ss = sentences(p)
            for si, s in enumerate(ss):
                a, rate = k.create(spoken(s.replace('"', "")), voice=VOICE, speed=SPEED, lang=LANG)
                a = trim(np.asarray(a, np.float32))
                d = len(a) / RATE
                items.append({"para": pi, "sent": si, "text": s, "s": round(t, 3), "e": round(t + d, 3)})
                pieces.append(a)
                t += d
                gap = GAP_S if si < len(ss) - 1 else after
                pieces.append(np.zeros(int(gap * RATE), np.float32))
                t += gap
        audio = np.concatenate(pieces)
        sf.write(os.path.join(out, "vo.wav"), audio, RATE)
        json.dump({"rate": RATE, "items": items, "total": round(len(audio) / RATE, 3)},
                  open(os.path.join(out, "vo.json"), "w"), indent=1)
        print("== %s: %.2f s" % (name, len(audio) / RATE))
        for it in items:
            print("  %6.2f-%6.2f p%d %s" % (it["s"], it["e"], it["para"], it["text"]))


if __name__ == "__main__":
    main(sys.argv[1:] or list(REELS))
