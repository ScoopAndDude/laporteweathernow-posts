"""Voice-over for the 60-second "Before Pumpkins" short, one sentence at a time so caption timing is exact.

python3 short_vo.py OUTDIR  ->  OUTDIR/vo.wav (24 kHz) and OUTDIR/vo.json
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE, SPEED, LANG, RATE = "af_heart", 0.94, "en-us", 24000
SAY = [(r"\bLa Porte's\b", "Luh-Port's"), (r"\bLa Porte\b", "Luh-Port"), (r"\bSamhain\b", "Sau-in")]

PARAS = [
    "Before pumpkins, Halloween lanterns were carved out of turnips. Twisted faces, ugly on purpose.",
    "Its roots go back to Ireland and Scotland, and a festival called Samhain. On the night of October "
    "thirty-first, people believed the dead walked among the living.",
    "So they set a place at the table for family who had died... and some went out in disguise, so the dead "
    "wouldn't know them.",
    "Then the church made November first All Saints' Day. The night before became All Hallows' Eve. Halloween.",
    "People told fortunes that night. In one Irish game, if your hand found the clay... you'd be dead within "
    "the year.",
    "When Irish families came to America, they found something better to carve. Pumpkins.",
    "And here in La Porte, we have our own Halloween legend. Belle Gunness.",
    "The full story is on our channel. Follow for more of La Porte's dark history... if you dare.",
]
LEAD = 0.45
GAP_S = 0.30      # between sentences
GAP_P = 0.55      # between paragraphs
GAP_DOTS = 0.20   # extra after a sentence that trails off


def spoken(t):
    for pat, rep in SAY:
        t = re.sub(pat, rep, t)
    return t


def sentences(p):
    out = re.findall(r"[^.?!]+(?:\.\.\.[^.?!]+)*[.?!]+", p)
    return [s.strip() for s in out if s.strip()]


def trim(a, thr=0.004, pad=0.03):
    idx = np.nonzero(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a
    i0 = max(0, idx[0] - int(pad * RATE))
    i1 = min(len(a), idx[-1] + int(pad * RATE))
    return a[i0:i1]


def main(out):
    os.makedirs(out, exist_ok=True)
    k = Kokoro(os.path.join(ROOT, "models", "kokoro-v1.0.onnx"), os.path.join(ROOT, "models", "voices-v1.0.bin"))
    pieces = [np.zeros(int(LEAD * RATE), np.float32)]
    t = LEAD
    items = []
    for pi, p in enumerate(PARAS):
        ss = sentences(p)
        for si, s in enumerate(ss):
            a, rate = k.create(spoken(s), voice=VOICE, speed=SPEED, lang=LANG)
            assert rate == RATE
            a = trim(np.asarray(a, np.float32))
            d = len(a) / RATE
            items.append({"para": pi, "sent": si, "text": s, "s": round(t, 3), "e": round(t + d, 3)})
            pieces.append(a)
            t += d
            gap = GAP_S if si < len(ss) - 1 else GAP_P
            if s.endswith("..."):
                gap += GAP_DOTS
            pieces.append(np.zeros(int(gap * RATE), np.float32))
            t += gap
    audio = np.concatenate(pieces)
    sf.write(os.path.join(out, "vo.wav"), audio, RATE)
    json.dump({"rate": RATE, "items": items, "total": round(len(audio) / RATE, 3)},
              open(os.path.join(out, "vo.json"), "w"), indent=1)
    for it in items:
        print("%6.2f-%6.2f  %s" % (it["s"], it["e"], it["text"]))
    print("total %.2f s" % (len(audio) / RATE))


if __name__ == "__main__":
    main(sys.argv[1])
