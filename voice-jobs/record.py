#!/usr/bin/env python3
"""Records voice lines for LPWN social videos in the daily video's voice
(Kokoro-82M, voice af_heart, speed 1.1; La Porte said "luh-PORT"), on GitHub Actions.

For each voice-jobs/<job>/lines.json ([{"id": ..., "text": ...}]) it writes <job>/voice/<id>.wav
(24 kHz mono) and <job>/voice/seconds.json. A job is recorded again only when its lines change.
Started by .github/workflows/social-voice.yml when a lines.json is pushed to this branch.
"""
import glob
import hashlib
import json
import os
import re

import numpy as np
import soundfile as sf
from kokoro import KPipeline

VOICE, SPEED, RATE = "af_heart", 1.1, 24000          # the daily video's voice (scripts/daily_video.py)
PRONOUNCE = {"La Port": "ləpˈɔɹt"}                    # scripts/radio_broadcast.py
SAY_AS = [(r"\blaporteweathernow\.com\b", "La Port Weather Now dot com"),
          (r"\bLa ?Porte\b", "La Port")]


def spoken(text):
    for pat, rep in SAY_AS:
        text = re.sub(pat, rep, text)
    for word, sounds in PRONOUNCE.items():
        text = text.replace(word, f"[{word}](/{sounds}/)")
    return text


pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")


def speak(text):
    chunks = []
    for result in pipe(spoken(text), voice=VOICE, speed=SPEED, split_pattern=r"\n+"):
        audio = result.audio if hasattr(result, "audio") else result[2]
        if audio is not None:
            chunks.append(audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio))
    return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)


for lines_path in sorted(glob.glob("voice-jobs/*/lines.json")):
    job = os.path.dirname(lines_path)
    with open(lines_path, encoding="utf-8") as fh:
        lines = json.load(fh)
    sig = hashlib.sha256(json.dumps([lines, VOICE, SPEED], sort_keys=True).encode()).hexdigest()[:12]
    out = os.path.join(job, "voice")
    os.makedirs(out, exist_ok=True)
    man = os.path.join(out, "seconds.json")
    if os.path.exists(man):
        with open(man, encoding="utf-8") as fh:
            if json.load(fh).get("sig") == sig:
                continue
    secs = {}
    for ln in lines:
        audio = speak(ln["text"]).astype(np.float32)
        sf.write(os.path.join(out, ln["id"] + ".wav"), audio, RATE)
        secs[ln["id"]] = round(len(audio) / RATE, 3)
    with open(man, "w", encoding="utf-8") as fh:
        json.dump({"sig": sig, "voice": f"Kokoro-82M {VOICE}, speed {SPEED}", "seconds": secs}, fh, indent=1)
    print(job, json.dumps(secs))
