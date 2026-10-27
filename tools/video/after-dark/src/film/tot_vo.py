"""Voice-over for the trick-or-treat hours reel, one sentence at a time so caption timing is exact.

python3 tot_vo.py OUTDIR  ->  OUTDIR/vo.wav (24 kHz) and OUTDIR/vo.json
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE, SPEED, LANG, RATE = "af_heart", 0.98, "en-us", 24000
# how the voice should say local names (checked against the phonemizer)
SAY = [(r"\bLa Porte\b", "Luh-Port"), (r"\bLaCrosse\b", "Luh-Cross"), (r"\bPottawattamie\b", "Potta-watta-mee"),
       (r"\bWanatah\b", "Wanna-taw"), (r"\bYMCA\b", "Y-M-C-A"), (r"\bPioneerland\b", "Pioneer Land")]
IPA = [("mˌɪkiˈɑːnə", "mˌɪʃiˈænə")]   # Michiana: "mish-ee-AN-uh"

# (paragraph text, pause after it in seconds)
PARAS = [
    ("Trick-or-treat hours for every town in La Porte County. Save this one.", 0.65),
    ("Most towns go out on Saturday, October thirty-first, from five to seven P M.", 0.35),
    ("That's La Porte, Michigan City, Kingsford Heights, Long Beach, Rolling Prairie, Trail Creek, Union Mills, "
     "Wanatah, and Westville.", 0.7),
    ("LaCrosse runs a little later, until seven-thirty.", 0.45),
    ("And Pottawattamie Park goes early: this Sunday, October twenty-fifth, from three to five, in daylight.", 0.5),
    ("Hanna and Michiana Shores haven't announced hours yet.", 0.7),
    ("Can't wait? Trunk-or-treats start Friday, at Franciscan Health in Michigan City.", 0.4),
    ("Saturday, there's Franklin Street, the YMCA, the county museum, and Pioneerland at the fairgrounds.", 0.4),
    ("Sunday, the La Porte police and the Orak Shrine.", 0.7),
    ("Every time and place is at La Porte Weather Now dot com. Happy trick-or-treating!", 0.0),
]
LEAD = 0.35
GAP_S = 0.28


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
    return a[max(0, idx[0] - int(pad * RATE)):min(len(a), idx[-1] + int(pad * RATE))]


def main(out):
    os.makedirs(out, exist_ok=True)
    k = Kokoro(os.path.join(ROOT, "models", "kokoro-v1.0.onnx"), os.path.join(ROOT, "models", "voices-v1.0.bin"))
    pieces = [np.zeros(int(LEAD * RATE), np.float32)]
    t = LEAD
    items = []
    for pi, (p, after) in enumerate(PARAS):
        ss = sentences(p)
        for si, s in enumerate(ss):
            ph = k.tokenizer.phonemize(spoken(s), LANG)
            for a, b in IPA:
                ph = ph.replace(a, b)
            a, rate = k.create(ph, voice=VOICE, speed=SPEED, lang=LANG, is_phonemes=True)
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
    for it in items:
        print("%6.2f-%6.2f  p%d  %s" % (it["s"], it["e"], it["para"], it["text"]))
    print("total %.2f s" % (len(audio) / RATE))


if __name__ == "__main__":
    main(sys.argv[1])
