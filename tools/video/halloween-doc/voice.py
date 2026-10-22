#!/usr/bin/env python3
"""Records the documentary's narration (lines.json, made from script.json by `doc.py lines`) into voice/<id>.flac
and voice/voice.json (each line's length and word timings, which the captions, stamps and page spotlights use).
Runs in GitHub Actions (.github/workflows/halloween-doc-voice.yml), in parts, where the models download.
Lines that haven't changed since the last run are kept as they are, so a fix re-records only what changed.

Two voices:
  chatterbox (default; Scoop, Oct. 21, 2026: "the ai human voice has to flow more humanly"): Resemble AI's
    Chatterbox, MIT-licensed, run on the CPU. It gives no word timings, so each line is listened back to with
    faster-whisper, the heard words are matched to the script, and a line that doesn't come back as written is
    recorded again with another seed (Chatterbox sometimes skips or repeats a phrase).
  kokoro: Kokoro-82M af_heart, the shorts' voice, with its own word timings.
Pick with VOICE_ENGINE=chatterbox|kokoro. VOICE_PART=i/n records every n-th line (for the matrix job).

A line can have "tts": the words as they should be spoken (years spelled out), while "say" is how they read in
the captions. Names the voices wouldn't know are respelled (RESPELL, for Chatterbox) or given in IPA (PRONOUNCE,
for Kokoro)."""
import difflib
import json
import os
import re
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.environ.get("VOICE_ENGINE", "chatterbox")
KOKORO_VOICE, KOKORO_SPEED = "af_heart", 0.94
# Chatterbox: exaggeration 0.35 / cfg 0.4 is the "chatterbox-calm" sample Scoop heard
EXAG, CFG = float(os.environ.get("VOICE_EXAG", "0.35")), float(os.environ.get("VOICE_CFG", "0.4"))
PAUSE = 0.28                                  # seconds between sentences of one line

# how Chatterbox should say names it wouldn't know (plain respellings; the captions keep the real spelling)
RESPELL = {
    "La Porte": "La Port", "LaPorte": "La Port", "Samhain": "Sah-win", "Hallowmas": "Hallow-mass",
    "Vallancey": "Val-an-see", "Maclise": "Mac-leese", "Alcuin": "Al-kwin", "Godey's": "Go-dee's", "Rhys": "Reese",
    "Terre Haute": "Terra Hote", "Sault Ste. Marie": "Soo Saint Marie", "Sault Daily Star": "Soo Daily Star",
    "Boniface": "Bonniface", "Meath": "Meeth", "Anoka": "Uh-no-ka", "Wabash": "Waw-bash", "Pixy Stix": "Pixie Sticks",
    "O'Bryan": "O'Brian", "Frazer": "Frazier", "Hutton": "Hutt-on", "Potawatomi": "Pot-a-wah-to-mee", "Hesston": "Hess-ton",
    "Blarney": "Blar-nee", "Culver": "Cull-ver", "Munster": "Mun-ster", "Kingsbury": "Kings-berry", "Valparaiso": "Val-pa-ray-zo",
    "Irvington": "Irving-ton", "Hoosier": "Hoo-zher", "Whiting": "Why-ting", "Recht's": "Rex", "puling": "pewling",
    "Ichabod": "Ick-a-bod", "Burns's": "Burns'",
}
# the same for Kokoro (IPA, in the style Kokoro's misaki uses)
PRONOUNCE = {
    "La Porte": "ləpˈɔɹt", "LaPorte": "ləpˈɔɹt", "Laporte": "ləpˈɔɹt", "Potawatomi": "pˌɑtəwˈɑtəmi", "Hoosier": "hˈuʒəɹ",
    "Kingsford": "kˈɪŋzfəɹd", "Samhain": "sˈɑwɪn", "Hallowmas": "hˈælOmæs", "Vallancey": "vˈælənsi", "Maclise": "məklˈis",
    "Alcuin": "ˈælkwɪn", "Godey's": "ɡˈOdiz", "Rhys": "ɹˈis", "Meath": "mˈiθ", "Anoka": "ənˈOkə", "Wabash": "wˈɔbæʃ",
    "Boniface": "bˈɑnɪfəs", "Hutton": "hˈʌtən", "Frazer": "fɹˈAzəɹ", "puling": "pjˈulɪŋ", "Recht's": "ɹˈɛkts",
}


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def sentences(text):
    """Chatterbox is happiest with one sentence at a time (it drifts on long passages)."""
    parts = re.split(r"(?<=[.!?…])\s+(?=[A-Z“\"'(\d])", text.strip())
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if out and len(out[-1]) < 40:                 # a very short sentence rides with the one before it
            out[-1] += " " + p
        else:
            out.append(p)
    return out


def respell(text):
    for word, said in sorted(RESPELL.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(r"(?<!\w)" + re.escape(word) + r"(?!\w)", said, text)
    return text


# ----------------------------------------------------------------------------------------------- the two voices
class Kokoro:
    rate = 24000

    def __init__(self):
        from kokoro import KPipeline
        self.pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")

    def record(self, spoken, seed=0):
        text = spoken
        for word, sounds in sorted(PRONOUNCE.items(), key=lambda kv: -len(kv[0])):
            text = re.sub(r"(?<![\w\[])" + re.escape(word) + r"(?![\w\]])", f"[{word}](/{sounds}/)", text)
        chunks, words, at = [], [], 0.0
        for result in self.pipe(text, voice=KOKORO_VOICE, speed=KOKORO_SPEED, split_pattern=r"\n+"):
            audio = result.audio if hasattr(result, "audio") else result[2]
            if audio is None:
                continue
            a = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            for tok in (getattr(result, "tokens", None) or []):
                st, en = getattr(tok, "start_ts", None), getattr(tok, "end_ts", None)
                if (tok.text or "").strip() and st is not None and en is not None:
                    words.append([tok.text, round(at + float(st), 3), round(at + float(en), 3)])
            chunks.append(a)
            at += len(a) / self.rate
        return np.concatenate(chunks).astype(np.float32), words


class Chatterbox:
    def __init__(self):
        import torch
        from chatterbox.tts import ChatterboxTTS
        self.torch = torch
        self.model = ChatterboxTTS.from_pretrained(device="cpu")
        self.rate = self.model.sr
        from faster_whisper import WhisperModel
        self.ears = WhisperModel("small.en", device="cpu", compute_type="int8")

    def say(self, text, seed):
        self.torch.manual_seed(seed)
        wav = self.model.generate(text, exaggeration=EXAG, cfg_weight=CFG)
        a = wav.squeeze().cpu().numpy().astype(np.float32)
        # trim silence at both ends (keep 60 ms)
        loud = np.where(np.abs(a) > 0.01)[0]
        if len(loud):
            a = a[max(0, loud[0] - int(0.06 * self.rate)):min(len(a), loud[-1] + int(0.06 * self.rate))]
        return a

    def listen(self, audio):
        """What whisper hears, with word times."""
        tmp = os.path.join(HERE, "voice", "_listen.wav")
        sf.write(tmp, audio, self.rate)
        segs, _ = self.ears.transcribe(tmp, word_timestamps=True, language="en", beam_size=3, condition_on_previous_text=False)
        heard = []
        for s in segs:
            for w in (s.words or []):
                heard.append([w.word.strip(), float(w.start), float(w.end)])
        return heard

    def record(self, spoken, seed=0):
        """Records sentence by sentence; each sentence is checked against what whisper hears and retried with a
        new seed if it came back wrong. Returns the audio and the script's words with times."""
        chunks, words, at = [], [], 0.0
        for si, sent in enumerate(sentences(spoken)):
            script_words = [w for w in sent.split() if norm(w)]
            best = None
            for attempt in range(4):
                a = self.say(respell(sent), seed + 7919 * si + 104729 * attempt)
                heard = self.listen(a)
                score, timed = align(script_words, heard, len(a) / self.rate)
                if best is None or score > best[0]:
                    best = (score, a, timed)
                if score >= 0.86:
                    break
                print(f"   retry {attempt + 1} (match {score:.2f}): {sent[:60]}", flush=True)
            score, a, timed = best
            chunks.append(a)
            words += [[w, round(at + s, 3), round(at + e, 3)] for w, s, e in timed]
            at += len(a) / self.rate
            chunks.append(np.zeros(int(PAUSE * self.rate), np.float32))
            at += PAUSE
        audio = np.concatenate(chunks[:-1]) if chunks else np.zeros(1, np.float32)
        return audio, words


def align(script_words, heard, total):
    """Matches the script's words to the heard words; unmatched script words get times between their neighbors.
    Returns (share of script words heard, [[word, start, end], ...])."""
    a = [norm(w) for w in script_words]
    b = [norm(w) for w, _, _ in heard]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    times = [None] * len(a)
    matched = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = (heard[j1 + k][1], heard[j1 + k][2])
                matched += 1
        elif tag == "replace" and (i2 - i1) == (j2 - j1):     # same count, different spelling: respellings, numbers
            for k in range(i2 - i1):
                times[i1 + k] = (heard[j1 + k][1], heard[j1 + k][2])
                matched += 0.7
    # fill the gaps evenly between known neighbors
    known = [i for i, t in enumerate(times) if t]
    if not known:
        step = total / max(1, len(a))
        times = [(i * step, (i + 1) * step) for i in range(len(a))]
    else:
        for i in range(len(a)):
            if times[i]:
                continue
            prev = max([k for k in known if k < i], default=None)
            nxt = min([k for k in known if k > i], default=None)
            t0 = times[prev][1] if prev is not None else 0.0
            t1 = times[nxt][0] if nxt is not None else total
            lo = prev + 1 if prev is not None else 0
            hi = nxt if nxt is not None else len(a)
            n = hi - lo
            step = (t1 - t0) / max(1, n)
            times[i] = (t0 + (i - lo) * step, t0 + (i - lo + 1) * step)
    return (matched / max(1, len(a))), [[w, s, e] for w, (s, e) in zip(script_words, times)]


# ----------------------------------------------------------------------------------------------- main
def main():
    lines = json.load(open(os.path.join(HERE, "lines.json"), encoding="utf-8"))["lines"]
    out = os.path.join(HERE, "voice")
    os.makedirs(out, exist_ok=True)
    vj = os.path.join(out, "voice.json")
    old = {}
    if os.path.exists(vj):
        old = {x["id"]: x for x in json.load(open(vj, encoding="utf-8"))["lines"]}
    part = os.environ.get("VOICE_PART", "0/1")
    pi, pn = (int(x) for x in part.split("/"))
    mine = [ln for i, ln in enumerate(lines) if i % pn == pi]
    name = f"Chatterbox (exaggeration {EXAG}, cfg {CFG})" if ENGINE == "chatterbox" else f"Kokoro-82M {KOKORO_VOICE}, speed {KOKORO_SPEED}"
    voice = None
    record, made = [], 0
    for ln in mine:
        spoken = ln.get("tts") or ln["say"]
        key = name + " | " + spoken + " | " + "; ".join(f"{w}={p}" for w, p in sorted((RESPELL if ENGINE == "chatterbox" else PRONOUNCE).items()) if w in spoken)
        path = os.path.join(out, ln["id"] + ".flac")
        prev = old.get(ln["id"])
        if prev and prev.get("key") == key and os.path.exists(path):
            prev["say"] = ln["say"]
            record.append(prev)
            continue
        if voice is None:
            voice = Chatterbox() if ENGINE == "chatterbox" else Kokoro()
        audio, words = voice.record(spoken, seed=sum(map(ord, ln["id"])))
        sf.write(path, audio, voice.rate, format="FLAC")
        record.append({"id": ln["id"], "say": ln["say"], "text": spoken, "key": key, "seconds": round(len(audio) / voice.rate, 3), "words": words})
        made += 1
        print(ln["id"], record[-1]["seconds"], "s", flush=True)
    rate = voice.rate if voice else (old and next(iter(old.values())).get("rate")) or 24000
    partfile = os.path.join(out, f"part-{pi}.json")
    with open(partfile, "w", encoding="utf-8") as fh:
        json.dump({"voice": name, "rate": rate, "lines": record}, fh, ensure_ascii=False, indent=1)
    print(f"part {part}: {made} lines recorded, {len(record)} in all, {sum(r['seconds'] for r in record) / 60:.1f} minutes")


def merge():
    """Joins the parts into voice.json in script order and drops recordings of lines that no longer exist."""
    lines = json.load(open(os.path.join(HERE, "lines.json"), encoding="utf-8"))["lines"]
    out = os.path.join(HERE, "voice")
    recs, name, rate = {}, None, 24000
    for f in sorted(os.listdir(out)):
        if f.startswith("part-") and f.endswith(".json"):
            d = json.load(open(os.path.join(out, f), encoding="utf-8"))
            name, rate = d["voice"], d["rate"]
            for r in d["lines"]:
                r["rate"] = rate
                recs[r["id"]] = r
            os.remove(os.path.join(out, f))
    record = [recs[ln["id"]] for ln in lines if ln["id"] in recs]
    keep = {r["id"] for r in record}
    for f in os.listdir(out):
        if f.endswith(".flac") and f[:-5] not in keep or f.startswith("_"):
            os.remove(os.path.join(out, f))
    json.dump({"voice": name, "rate": rate, "lines": record}, open(os.path.join(out, "voice.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    missing = [ln["id"] for ln in lines if ln["id"] not in recs]
    print(f"{len(record)} lines, {sum(r['seconds'] for r in record) / 60:.1f} minutes; missing: {missing or 'none'}")


if __name__ == "__main__":
    merge() if (sys.argv[1:] and sys.argv[1] == "merge") else main()
