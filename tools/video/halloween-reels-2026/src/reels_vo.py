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
       (r"\bmid-1900s\b", "mid-nineteen-hundreds")]

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
}
LEAD = 0.3
GAP_S = 0.28


def spoken(t):
    for pat, rep in SAY:
        t = re.sub(pat, rep, t)
    return t


def sentences(p):
    p = p.replace("Mrs.", "Mrs\u00a7")
    out = re.findall(r"[^.?!]+(?:\.\.\.[^.?!]+)*[.?!]+[\"”]?", p)
    return [s.strip().replace("Mrs\u00a7", "Mrs.") for s in out if s.strip()]


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
