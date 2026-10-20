#!/usr/bin/env python3
"""Records the documentary's narration (lines.json, made from script.json by `doc.py lines`) with the same
voice as the shorts (Kokoro-82M, af_heart) into voice/<id>.flac and voice/voice.json (each line's length,
word timings and the sounds the voice used, to check names and numbers). Runs in GitHub Actions
(.github/workflows/belle-doc-voice.yml), where the model downloads. Lines that haven't changed since the
last run are kept as they are, so a fix re-records only what changed.

A line can have "tts": the words as they should be spoken (years and numbers spelled out), while "say" is
how they read in the captions."""
import json
import os
import re

import numpy as np
import soundfile as sf
from kokoro import KPipeline

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE, SPEED, RATE = "af_heart", 0.94, 24000
# names the voice wouldn't know how to say (IPA, in the style Kokoro's misaki uses)
PRONOUNCE = {
    "La Porte": "ləpˈɔɹt", "LaPorte": "ləpˈɔɹt", "Gunness": "ɡˈʌnəs", "Gunnesses": "ɡˈʌnəsᵻz",
    "Brynhild": "bɹˈɪnhɪld", "Størset": "stˈɜɹsɛt", "Storset": "stˈɜɹsɛt", "Paulsdatter": "pˈWlzdɑtəɹ",
    "Selbu": "sˈɛlbu", "Trondheim": "tɹˈɑnhIm", "Sorenson": "sˈɔɹənsən", "Helgelien": "hˈɛlɡəlin",
    "Lamphere": "lˈæmfɪɹ", "Budsberg": "bˈʌdzbɜɹɡ", "Asle": "ˈɑslə", "Ole": "ˈOli", "Skandinaven": "skˌændɪnˈɑvən",
    "Smutzer": "smˈʌtsəɹ", "Leliter": "lˈɛlɪtəɹ", "Mads": "mˈæds", "Jennie": "ʤˈɛni", "Myrtle": "mˈɜɹtᵊl",
    "Gurholdt": "ɡˈʊɹhOlt", "Lindbloom": "lˈɪndblum", "Maxson": "mˈæksən", "Iola": "Iˈolə",
    "Nawrocki": "nəɹˈɑki", "Swanhild": "swˈɑnhɪld", "McClung": "məklˈʌŋ", "Sorensons": "sˈɔɹənsənz", "Moe": "mˈO",
}


def main():
    lines = json.load(open(os.path.join(HERE, "lines.json"), encoding="utf-8"))["lines"]
    out = os.path.join(HERE, "voice")
    os.makedirs(out, exist_ok=True)
    vj = os.path.join(out, "voice.json")
    old = {}
    if os.path.exists(vj):
        old = {x["id"]: x for x in json.load(open(vj, encoding="utf-8"))["lines"]}
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    record, made = [], 0
    for ln in lines:
        spoken = ln.get("tts") or ln["say"]
        # a line is recorded again when its words change, or when the way one of its names is said changes
        key = spoken + " | " + "; ".join(f"{w}={p}" for w, p in sorted(PRONOUNCE.items()) if w in spoken)
        path = os.path.join(out, ln["id"] + ".flac")
        prev = old.get(ln["id"])
        if prev and prev.get("key", prev.get("text")) == key and os.path.exists(path):
            prev["say"] = ln["say"]
            record.append(prev)
            continue
        text = spoken
        for word, sounds in sorted(PRONOUNCE.items(), key=lambda kv: -len(kv[0])):
            text = re.sub(r"(?<![\w\[])" + re.escape(word) + r"(?![\w\]])", f"[{word}](/{sounds}/)", text)
        chunks, words, phon, at = [], [], [], 0.0
        for result in pipe(text, voice=VOICE, speed=SPEED, split_pattern=r"\n+"):
            audio = result.audio if hasattr(result, "audio") else result[2]
            if audio is None:
                continue
            a = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            for tok in (getattr(result, "tokens", None) or []):
                st, en = getattr(tok, "start_ts", None), getattr(tok, "end_ts", None)
                if (tok.text or "").strip():
                    phon.append(f"{tok.text}={getattr(tok, 'phonemes', '')}")
                    if st is not None and en is not None:
                        words.append([tok.text, round(at + float(st), 3), round(at + float(en), 3)])
            chunks.append(a)
            at += len(a) / RATE
        audio = np.concatenate(chunks).astype(np.float32)
        sf.write(path, audio, RATE, format="FLAC")
        record.append({"id": ln["id"], "say": ln["say"], "text": spoken, "key": key, "seconds": round(len(audio) / RATE, 3), "words": words,
                       "phonemes": " ".join(phon)})
        made += 1
        print(ln["id"], record[-1]["seconds"], "s")
    keep = {r["id"] for r in record}
    for f in os.listdir(out):
        if f.endswith(".flac") and f[:-5] not in keep:
            os.remove(os.path.join(out, f))
    with open(vj, "w", encoding="utf-8") as fh:
        json.dump({"voice": f"Kokoro-82M {VOICE}, speed {SPEED}", "rate": RATE, "lines": record}, fh, ensure_ascii=False, indent=1)
    total = sum(r["seconds"] for r in record)
    print(f"{made} lines recorded, {len(record)} in all, {total / 60:.1f} minutes")


if __name__ == "__main__":
    main()
