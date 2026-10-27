"""La Porte After Dark: a vertical short (1080 x 1920, 30 fps, -14 LUFS) made from a storyboard, with no new drawing
code. The scenes are story_kit.py's, the cards story_cards.py's, the voice Kokoro af_heart (like every reel).

    python3 film/reel_story.py STORY.json vo        narration -> shorts/r_<slug>/vo.wav, vo.json (+ how it says names)
    python3 film/reel_story.py STORY.json stills    a contact sheet -> shorts/out/<slug>_preview.jpg (+ each frame)
    python3 film/reel_story.py STORY.json video     the short -> shorts/out/<slug>.mp4, -cover.jpg, .srt
    python3 film/reel_story.py STORY.json remix     redo just the sound on the last render (after a sound-only change)
    python3 film/reel_story.py STORY.json check     loudness, length, narration vs. script, captions, files

The storyboard (see film/stories/*.json for real ones):
{
  "slug": "crown-point-old-jail",                  file names; lowercase letters, numbers, hyphens
  "title": "Crown Point's Old Lake County Jail",   the video's title metadata
  "series": "LA PORTE AFTER DARK",                 small line at the top of the first scene (optional)
  "say": [["\\\\bHesston\\\\b", "Hess-tun"]],         extra pronunciation fixes (regex, spoken form), applied first
  "music": {"seed": 130, "prog": 6},                haunt_music settings (optional)
  "beats": [                                        one beat = one paragraph of narration = one scene
    {"text": "In 1934, ...",                        what the narrator says (sentences end with . ? or !)
     "pause": 0.45,                                 silence after it (default 0.45; the last beat 0)
     "scene": {"kind": "jail", "seed": 1, "move": "in", ...},      story_kit.KINDS and their options
     "label": "CROWN POINT, INDIANA",               small caps line at the top (y 300), from the beat's start
     "label2": {"text": "WHAT VISITORS SAY", "at": "Visitors say"},     replaces label at that phrase
     "title": {"text": "THE OLD LAKE COUNTY JAIL", "at": "Lake County Jail", "style": "bone"|"red", "size": 88},
     "typed": [{"text": "MARCH 3, 1934", "at": "March 3,", "y": 545, "size": 72}],
     "card": {"kind": "year"|"quote"|"headline"|"map"|"photo", "at": "phrase", "until": "phrase", ...},
     "credit": "History: The Old Sheriff's House Foundation",      bottom line; who the facts come from
     "flash": ["phrase"],                           lightning (with thunder) at these words
     "sfx": [{"kind": "clang", "at": "slammed", "gain": 0.6, "offset": 0.0}]
    },
    ...
    {"text": "Comment your town, and it could be next.", "end": true,
     "end_card": {"q": "COMMENT YOUR TOWN", "q2": "IT COULD BE NEXT", "bubble": "Your town, your state",
                  "pill": "The Old Jail Museum: tours on weekends", "scene": {"kind": "jail", "seed": 2}},
     "credit": "All pictures drawn"}
  ]
}
Phrases ("at") are matched word for word (punctuation ignored) in that beat's narration, so copy them from "text".
"""
import json
import math
import os
import re
import sys

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

import reels_common as C
from reels_common import bs, vr, W, H, SR, T, fitT, glow, paste, appear, dim, BONE
from reel_frank import to_pil
from reel_belle import typed, red_title
from reel_haunts import lab, ttl, haunt_music, whispers, steps
import shorts as SH
import story_kit as K
import story_cards as SC
import story_sound as S

ROOT = C.ROOT
RATE = 24000
LEAD = 0.3
GAP_S = 0.28


# --------------------------------------------------------------------------------------------- the storyboard

def load(path):
    st = json.load(open(path, encoding="utf-8"))
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", st.get("slug", "")):
        raise ValueError("slug must be lowercase letters, numbers and hyphens")
    if not st.get("beats"):
        raise ValueError("no beats")
    for i, b in enumerate(st["beats"]):
        if not b.get("text"):
            raise ValueError("beat %d has no text" % i)
        if not b.get("end") and not b.get("scene"):
            raise ValueError("beat %d has no scene" % i)
        if b.get("scene") and b["scene"].get("kind", "card") not in K.KINDS:
            raise ValueError("beat %d: unknown scene kind %r" % (i, b["scene"].get("kind")))
    st["_path"] = os.path.abspath(path)
    return st


def name_of(st):
    return "s_" + st["slug"]


# --------------------------------------------------------------------------------------------- narration

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
       "seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def two(n):
    if n < 20:
        return ONES[n]
    return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")


def num_words(s):
    """How the narrator reads a number: years like 1934 as 'nineteen thirty-four', others plainly."""
    m = re.fullmatch(r"(\d{1,4})(s)?", s)
    if m:
        n = int(m.group(1))
        if 1100 <= n <= 1999 or 2010 <= n <= 2099:
            hi, lo = divmod(n, 100)
            w = two(hi) + " " + ("hundred" if lo == 0 else ("oh-" + ONES[lo] if lo < 10 else two(lo)))
        elif 2000 <= n <= 2009:
            w = "two thousand" + (" " + ONES[n - 2000] if n > 2000 else "")
        elif n < 100:
            w = two(n)
        elif n < 1000:
            w = ONES[n // 100] + " hundred" + (" " + two(n % 100) if n % 100 else "")
        else:
            w = two(n // 1000) + " thousand" + (" " + num_words(str(n % 1000)) if n % 1000 else "")
        if m.group(2):
            if w.endswith("y"):
                return w[:-1] + "ies"
            return w + "s"
        return w
    m = re.fullmatch(r"(\d+)\.(\d+)", s)
    if m:
        return num_words(m.group(1)) + " point " + " ".join(ONES[int(c)] for c in m.group(2))
    return s


# How the voice gets local names right (checked with kokoro_onnx's phonemizer, Oct. 26, 2026). Add to these, and to a
# story's own "say", whenever the "pronunciation" listing from the vo step shows a name coming out wrong.
LOCAL_SAY = [(r"\bDillinger\b", "Dillinjer"), (r"\bGipp\b", "Ghip"), (r"\bValparaiso\b", "Valparayzo")]
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
ORD = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh", 8: "eighth",
       9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth", 15: "fifteenth",
       16: "sixteenth", 17: "seventeenth", 18: "eighteenth", 19: "nineteenth", 20: "twentieth", 30: "thirtieth"}


def ordinal(n):
    if n in ORD:
        return ORD[n]
    return TENS[n // 10] + "-" + ORD[n % 10]


def say_dates(text):
    """'March 3' -> 'March third'; '1934' -> 'nineteen thirty-four'; '1930s' -> 'nineteen-thirties'
    (left alone, the voice reads 1934 as 'nineteen hundred thirty-four')."""
    text = re.sub(r"\b(%s) (\d{1,2})\b(?!,? ?\d{3})" % MONTHS, lambda m: m.group(1) + " " + ordinal(int(m.group(2))), text)
    text = re.sub(r"\b(%s) (\d{1,2}), (\d{4})\b" % MONTHS,
                  lambda m: m.group(1) + " " + ordinal(int(m.group(2))) + ", " + m.group(3), text)
    return re.sub(r"(?<![\d.,$])\b(1[1-9]\d\d|20\d\d)(s?)\b(?![.,]\d)", lambda m: num_words(m.group(1) + m.group(2)), text)


def say_rules(st):
    import reels_vo as V
    rules = [(re.compile(p), r) for p, r in st.get("say", [])]
    rules += [(re.compile(p), r) for p, r in LOCAL_SAY]
    rules.append((None, say_dates))
    rules += [(re.compile(p), r) for p, r in V.SAY if not re.search(r"\\b(1[1-9]|20)\d\d", p)]
    return rules


def spoken(text, rules):
    for pat, rep in rules:
        text = rep(text) if pat is None else pat.sub(rep, text)
    return text


def weights(st):
    """Caption timing weights for words that take longer to say than their letters suggest (numbers, respellings)."""
    rules = say_rules(st)
    out = {}
    for b in st["beats"]:
        for w in b["text"].split():
            core = re.sub(r"[^\w'-]", "", w)
            if not core:
                continue
            sp = spoken(core, rules)
            sp = " ".join(num_words(x) if re.search(r"\d", x) else x for x in re.split(r"\s+", sp))
            if sp != core or re.search(r"\d", core):
                out[core] = round(sum(SH.syllables(p) for p in re.split(r"[\s-]+", sp) if p) + 0.35, 2)
    return out


def sentences(p):
    import reels_vo as V
    return V.sentences(p)


def narrate(st):
    from kokoro_onnx import Kokoro
    import reels_vo as V
    rules = say_rules(st)
    voice = st.get("voice", {}).get("name", "af_heart")
    speed = float(st.get("voice", {}).get("speed", 1.02))
    k = Kokoro(os.path.join(ROOT, "models", "kokoro-v1.0.onnx"), os.path.join(ROOT, "models", "voices-v1.0.bin"))
    out = os.path.join(ROOT, "shorts", "r_" + name_of(st))
    os.makedirs(out, exist_ok=True)
    pieces = [np.zeros(int(LEAD * RATE), np.float32)]
    t = LEAD
    items = []
    beats = st["beats"]
    for pi, b in enumerate(beats):
        ss = sentences(b["text"])
        if " ".join(ss) != " ".join(b["text"].split()):
            raise ValueError("beat %d: couldn't split into sentences cleanly: %r" % (pi, ss))
        after = float(b.get("pause", 0.0 if pi == len(beats) - 1 else 0.45))
        for si, s in enumerate(ss):
            a, rate = k.create(spoken(s.replace('"', "").replace("“", "").replace("”", ""), rules),
                               voice=voice, speed=speed, lang="en-us")
            a = V.trim(np.asarray(a, np.float32))
            d = len(a) / RATE
            items.append({"para": pi, "sent": si, "text": s, "s": round(t, 3), "e": round(t + d, 3)})
            pieces.append(a)
            t += d
            gap = GAP_S if si < len(ss) - 1 else after
            pieces.append(np.zeros(int(gap * RATE), np.float32))
            t += gap
    audio = np.concatenate(pieces)
    sf.write(os.path.join(out, "vo.wav"), audio, RATE)
    json.dump({"rate": RATE, "items": items, "total": round(len(audio) / RATE, 3), "weights": weights(st)},
              open(os.path.join(out, "vo.json"), "w"), indent=1)
    print("== %s: %.2f s" % (st["slug"], len(audio) / RATE))
    for it in items:
        print("  %6.2f-%6.2f p%d %s" % (it["s"], it["e"], it["para"], it["text"]))
    # how the voice will say the names and numbers (check these against how locals say them)
    try:
        from kokoro_onnx.tokenizer import Tokenizer
        tok = Tokenizer()
        words = sorted(set(w for b in beats for w in re.findall(r"[A-Z][\w'-]+|\d[\d,.]*s?", b["text"])))
        print("pronunciation (check names):")
        for w in words:
            print("  %-18s -> %-24s /%s/" % (w, spoken(w, rules), tok.phonemize(spoken(w, rules), "en-us")))
    except Exception as e:                                           # the phoneme listing is a help, not a must
        print("(no phoneme listing: %s)" % e)


# --------------------------------------------------------------------------------------------- the film

def end_bubble(text):
    f = C.font("semi", 44)
    w = int(f.getlength(text)) + 90
    img = Image.new("RGBA", (w + 40, 130), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 10, 20 + w, 100), radius=26, fill=(242, 240, 234, 240))
    d.polygon([(60, 98), (92, 98), (56, 124)], fill=(242, 240, 234, 240))
    d.text((52, 30), text, font=f, fill=(70, 70, 76, 255))
    return img, 52 + f.getlength(text) + 6


class Timeline:
    def __init__(self, R, st):
        self.R, self.st = R, st
        n = len(st["beats"])
        self.starts = [R.para(i)[0] for i in range(n)]
        self.ends = [R.para(i)[1] for i in range(n)]

    def at(self, i, phrase, end=False):
        """Time of a phrase inside beat i (its first word; end=True: its last word's end)."""
        after = self.starts[i] - 0.01
        try:
            return self.R.end(phrase, after) if end else self.R.at(phrase, after)
        except (KeyError, IndexError):
            raise KeyError("beat %d: phrase %r not found in: %s" % (i, phrase, self.st["beats"][i]["text"]))


def build(st, R):
    beats = st["beats"]
    n = len(beats)
    TL = Timeline(R, st)
    cuts = [0.0] + [(TL.ends[i] + TL.starts[i + 1]) / 2 for i in range(n - 1)] + [R.dur + 1.0]
    for i, b in enumerate(beats):
        if b.get("end") and i > 0:
            cuts[i] = TL.starts[i] - 0.15
    scenes, events, flashes = [], [], []
    rng_seed = sum(ord(c) for c in st["slug"])

    for i, b in enumerate(beats):
        t0, t1 = cuts[i], cuts[i + 1]
        dur = max(1.0, t1 - t0)
        if b.get("end"):
            scenes.append(end_scene(st, b, i, t0, t1, TL, events))
            continue
        spec = dict(b["scene"])
        kind = spec.get("kind", "card")
        lab1 = b.get("label") or (st.get("series") if i == 0 else None)
        lab2 = b.get("label2")
        title = b.get("title")
        if isinstance(title, str):
            title = {"text": title}
        tys = b.get("typed", [])
        card = b.get("card")
        credit = b.get("credit", "")
        t_title = TL.at(i, title["at"]) - 0.1 if title and title.get("at") else t0 + 0.25
        t_lab2 = TL.at(i, lab2["at"]) - 0.1 if lab2 else None
        t_ty = [TL.at(i, ty["at"]) - 0.1 if ty.get("at") else t0 + 0.3 for ty in tys]
        tc = (None, None)
        if card:
            tc = (TL.at(i, card["at"]) - 0.15 if card.get("at") else t0 + 0.2,
                  TL.at(i, card["until"]) - 0.1 if card.get("until") else None)
        for ph in b.get("flash", []):
            ft = TL.at(i, ph)
            flashes.append((ft + 0.1, 0.25))
            events.append((S.accent("thunder", i), ft + 0.1, 0.55, "bed"))
        for sx in b.get("sfx", []):
            at = TL.at(i, sx["at"]) if sx.get("at") else t0
            snd = S.accent(sx["kind"], i) if sx["kind"] not in ("type", "hit", "pop", "whoosh") else sx["kind"]
            if snd is not None:
                events.append((snd, at + float(sx.get("offset", 0.0)), float(sx.get("gain", 0.5)),
                               "bed" if sx["kind"] in ("thunder", "drip", "heartbeat", "music_box") else "hits"))
        # the scene's own sounds: a bed under it, and one accent early on
        bed_kind, acc = K.AMBIENCE.get(kind, (None, None))
        if spec.get("rain"):
            bed_kind = "rain"
        bd = S.bed(bed_kind, dur + 0.8, seed=i) if bed_kind else None
        if bd is not None:
            events.append((bd, max(0.0, t0 - 0.2), 0.42, "bed"))
        ac = S.accent(acc, i) if acc else None
        if ac is not None and dur > 2.5:
            events.append((ac, t0 + min(1.2, dur * 0.3), 0.3, "bed" if acc in ("drip", "bell") else "hits"))
        if i > 0:
            events.append(("whoosh", t0, 0.5))
        if title:
            events.append(("hit" if title.get("style") == "red" else "pop", t_title, 0.6))
        for tt_ in t_ty:
            events.append(("type", tt_, 0.8))
        if card:
            events.append(("whoosh" if card["kind"] in ("map", "photo") else "pop", tc[0], 0.45))

        series = st.get("series") if i == 0 and b.get("label") else None

        def prep(ctx, spec=spec, dur=dur, lab1=lab1, lab2=lab2, title=title, series=series):
            ctx["s"] = K.make(dict(spec), dur)
            ctx["series"] = lab(series.upper(), 26, (200, 214, 206)) if series else None
            ctx["l"] = lab(lab1.upper()) if lab1 else None
            ctx["l2"] = lab(lab2["text"].upper(), 34, (200, 214, 206)) if lab2 else None
            if title and title.get("style") != "red":
                ctx["n"] = ttl(title["text"], int(title.get("size", 88)))
            ctx["card"] = {}

        def draw(f, u, t, ctx, t0=t0, t1=t1, title=title, t_title=t_title, t_lab2=t_lab2, tys=tys, t_ty=t_ty,
                 card=card, tc=tc, credit=credit):
            f.alpha_composite(to_pil(ctx["s"].render(t, u)))
            bs.shade(f)
            ly = 300
            if ctx["series"] is not None:
                paste(f, ctx["series"], W / 2, 292, appear(t, t0 + 0.05, 0.3))
                ly = 338
            if ctx["l"] is not None:
                a = appear(t, t0 + 0.05, 0.3)
                if ctx["l2"] is not None:
                    a *= 1 - appear(t, t_lab2 - 0.3, 0.3)
                paste(f, ctx["l"], W / 2, ly, a)
            if ctx["l2"] is not None:
                paste(f, ctx["l2"], W / 2, 300, appear(t, t_lab2, 0.3))
            if title:
                if title.get("style") == "red":
                    if t >= t_title - 0.2:
                        red_title(f, title["text"].upper(), int(title.get("size", 100)), t, t_title)
                else:
                    a = appear(t, t_title, 0.3)
                    paste(f, ctx["n"], W / 2, int(title.get("y", 430)) + 12 * (1 - a), a)
            for ty, tt_ in zip(tys, t_ty):
                typed(f, ty["text"], t, tt_, int(ty.get("y", 545)), size=int(ty.get("size", 72)),
                      rate=float(ty.get("rate", 0.045)))
            if card:
                SC.draw(f, card, t, tc[0], tc[1], ctx["card"])
            bs.credit_line(f, credit)

        sc = C.Scene(t0, t1, draw, prep, flicker=0.4 if kind in ("room", "cellar", "cell") else None)
        scenes.append(sc)

    look = st.get("look", {})
    atm = bs.Atmos(tint=tuple(look.get("tint", (196, 204, 206))), fog=0.08, vignette=0.58, grain=12, seed=17)
    film = C.Film(R, scenes, flashes=flashes, flicker=float(look.get("flicker", 0.2)), atmos=atm)
    mus = st.get("music", {})
    music = haunt_music(R, seed=int(mus.get("seed", 100 + rng_seed % 50)), prog=int(mus.get("prog", 6)))
    return film, events, music


def end_scene(st, b, i, t0, t1, TL, events):
    ec = b.get("end_card", {})
    spec = dict(ec.get("scene") or {"kind": "card"})
    credit = b.get("credit", "All pictures drawn")

    def prep(ctx):
        ctx["s"] = K.make(dict(spec), max(1.0, t1 - t0))
        ctx["q"] = glow(fitT(ec.get("q", "COMMENT YOUR TOWN"), "bask", 104, BONE, max_w=C.CW, min_size=60), (0, 0, 0),
                        radius=24, strength=0.95)
        ctx["q2"] = glow(fitT(ec.get("q2", "IT COULD BE NEXT"), "bask", 120, (250, 70, 56), max_w=C.CW, min_size=60),
                         (150, 0, 0), radius=34, strength=0.7)
        ctx["b"], ctx["cur"] = end_bubble(ec.get("bubble", "Your town, your state"))
        ctx["pill"] = vr.pill(ec["pill"], "xbold", 38, (10, 20, 18), (170, 255, 214, 255), padx=26,
                              pady=14) if ec.get("pill") else None

    def draw(f, u, t, ctx):
        f.alpha_composite(to_pil(ctx["s"].render(t, u + 6.0)))
        bs.shade(f)
        dim(f, 0.4 * appear(u, 0.0, 0.3))
        paste(f, ctx["q"], W / 2, 430, appear(u, 0.0, 0.25))
        paste(f, ctx["q2"], W / 2, 560, appear(u, 0.15, 0.25))
        bb = ctx["b"]
        a = appear(u, 0.4, 0.3)
        paste(f, bb, W / 2, 740 + 10 * (1 - a), a)
        if a > 0.9 and int(u * 2.2) % 2 == 0:
            x0 = W / 2 - bb.width / 2 + ctx["cur"]
            ImageDraw.Draw(f).rectangle((x0, 740 - 30, x0 + 4, 740 + 16), fill=(70, 70, 76, 255))
        if ctx["pill"] is not None:
            paste(f, ctx["pill"], W / 2, 900, appear(u, 0.6, 0.3))
        bs.credit_line(f, credit)

    events += [("whoosh", t0, 0.5), ("pop", t0 + 0.4, 0.6), ("pop", t0 + 0.75, 0.5)]
    return C.Scene(t0, t1, draw, prep, flicker=0.0)


# --------------------------------------------------------------------------------------------- outputs

def reel(st):
    vo = json.load(open(os.path.join(ROOT, "shorts", "r_" + name_of(st), "vo.json")))
    C.WEIGHT.update(vo.get("weights", {}))
    return C.Reel(name_of(st), tail=float(st.get("tail", 1.4)))


def srt(R, path):
    def ts(x):
        ms = int(round(x * 1000))
        return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)
    groups, cur = [], []
    for wd in R.words:                                     # caption lines up to ~42 characters, broken at sentences
        cand = " ".join(w[0] for w in cur + [wd])
        if cur and (len(cand) > 42 or cur[-1][0][-1:] in ".?!"):
            groups.append(cur)
            cur = []
        cur.append(wd)
    if cur:
        groups.append(cur)
    with open(path, "w", encoding="utf-8") as f:
        for k, g in enumerate(groups):
            a = g[0][1]
            b_ = g[-1][2] + 0.05
            if k + 1 < len(groups):
                b_ = min(b_, groups[k + 1][0][1] - 0.01)
            f.write("%d\n%s --> %s\n%s\n\n" % (k + 1, ts(a), ts(b_), " ".join(w[0] for w in g)))


def finish(R, video_path, mix, out_path_, title, target=-14.0, limit=0.68):
    """Like reels_common.finish, but limited harder so the true peak stays under -1 dBTP after AAC encoding."""
    import subprocess
    wav = out_path_.replace(".mp4", ".wav")
    tmp = wav + ".raw.wav"
    sf.write(tmp, np.stack([mix, mix], 1), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    gain = target - I + 0.25
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    "volume=%.2fdB,alimiter=limit=%.3f:attack=3:release=80:level=false:latency=true" % (gain, limit),
                    "-c:a", "pcm_f32le", wav], check=True)
    os.remove(tmp)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video_path, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", "%.3f" % (R.n / C.FPS),
                    "-movflags", "+faststart", "-metadata", "title=%s" % title,
                    "-metadata", "artist=La Porte Weather Now", out_path_], check=True)
    os.remove(wav)
    return I, gain


def out_path(st):
    return os.path.join(C.OUT, st["slug"] + ".mp4")


def check(st):
    """Everything a reviewer looks at before it posts. Returns a list of problems (empty = good)."""
    probs = []
    vo = json.load(open(os.path.join(ROOT, "shorts", "r_" + name_of(st), "vo.json")))
    said = " ".join(it["text"] for it in vo["items"])
    script = " ".join(" ".join(b["text"].split()) for b in st["beats"])
    if said != script:
        probs.append("narration doesn't match the storyboard text (re-run vo)")
    p = out_path(st)
    if not os.path.exists(p):
        return probs + ["no video yet: " + p]
    I, tp, d = C.measure(p)
    if abs(I + 14) > 1.0:
        probs.append("loudness %.1f LUFS (want -14 +/- 1)" % I)
    if tp is not None and tp > -1.0:
        probs.append("true peak %.1f dBFS (want -1.0 or lower)" % tp)
    if not 15 <= d <= 75:
        probs.append("length %.1f s (want 15-75 s for Shorts, Reels and TikTok)" % d)
    for ext in ("-cover.jpg", ".srt"):
        if not os.path.exists(p.replace(".mp4", ext)):
            probs.append("missing " + p.replace(".mp4", ext))
    # every beat has a source credit (the last one can just say the pictures are drawn)
    for i, b in enumerate(st["beats"][:-1]):
        if not b.get("credit"):
            probs.append("beat %d has no credit line (say where the facts come from)" % i)
    words = len(script.split())
    print("length %.1f s, %d words, %.1f LUFS, peak %s dBFS" % (d, words, I, tp))
    return probs


def main(path, mode, times=None):
    st = load(path)
    if mode == "vo":
        narrate(st)
        return
    R = reel(st)
    film, ev, music = build(st, R)
    if mode == "stills":
        ts = times or [round(R.dur * k / 12, 2) for k in range(12)]
        print(film.stills([t for t in ts if t < R.dur], st["slug"]))
        return
    if mode == "video":
        os.makedirs(C.OUT, exist_ok=True)
        vid = os.path.join(C.OUT, "_%s_video.mp4" % st["slug"])
        film.video(vid, cover_t=float(st.get("cover_t", 0.8)))
        mix = C.soundtrack(R, music, ev, music_gain=0.5)
        out = out_path(st)
        finish(R, vid, mix, out, st.get("title", st["slug"]))
        if not st.get("keep_raw"):
            pass
        os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
        os.replace(vid, os.path.join(C.OUT, "_%s_silent.mp4" % st["slug"]))      # kept for a quick re-mix
        srt(R, out.replace(".mp4", ".srt"))
        print("made", out, C.measure(out))
        return
    if mode == "remix":
        vid = os.path.join(C.OUT, "_%s_silent.mp4" % st["slug"])
        mix = C.soundtrack(R, music, ev, music_gain=0.5)
        out = out_path(st)
        finish(R, vid, mix, out, st.get("title", st["slug"]))
        srt(R, out.replace(".mp4", ".srt"))
        print("re-mixed", out, C.measure(out))
        return
    if mode == "check":
        probs = check(st)
        print("\n".join("PROBLEM: " + p for p in probs) if probs else "check: all good")
        sys.exit(1 if probs else 0)
    raise SystemExit("mode: vo | stills | video | remix | check")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None)
