#!/usr/bin/env python3
"""Voice samples for Scoop to pick from (Oct. 21, 2026: "the ai human voice has to flow more humanly").
Records the same three narration lines with several free voices and writes voice-test/<name>.mp3.
Kokoro voices (fast, CPU) and, if it installs, Chatterbox (Resemble AI, MIT), which sounds more human but
is slower to run. Runs in GitHub Actions (halloween-doc-voice-test.yml). Nothing is posted."""
import json
import os
import subprocess
import re

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voice-test")
os.makedirs(OUT, exist_ok=True)
LINES = [
    "Every October, something strange happens on the streets of La Porte, Indiana. Children dressed as ghosts knock on the doors of strangers and demand candy. And the strangers hand it over.",
    "In 1905, a La Porte newspaper complained that boys had carried off gates, overturned outhouses, and hoisted a farmer's wagon onto the roof of a barn. The paper called it, simply, Hallowe'en.",
    "So where did all of this come from? The answer is older than America, older than the church, and stranger than the legend.",
]
TEXT = "\n".join(LINES)


def save(name, audio, rate):
    wav = os.path.join(OUT, name + ".wav")
    sf.write(wav, audio.astype(np.float32), rate)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5", "-b:a", "96k", os.path.join(OUT, name + ".mp3")], check=True)
    os.remove(wav)
    print("made", name)


def kokoro():
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    for voice, speed in [("af_heart", 0.94), ("af_bella", 0.92), ("af_nicole", 0.9), ("am_michael", 0.92), ("am_adam", 0.9), ("bm_george", 0.9), ("am_fenrir", 0.92)]:
        chunks = []
        for r in pipe(TEXT, voice=voice, speed=speed, split_pattern=r"\n+"):
            a = r.audio
            chunks.append(a.detach().cpu().numpy() if hasattr(a, "detach") else np.asarray(a))
            chunks.append(np.zeros(int(0.55 * 24000), np.float32))        # a breath between lines
        save("kokoro-" + voice, np.concatenate(chunks), 24000)


def chatterbox():
    try:
        import torch
        from chatterbox.tts import ChatterboxTTS
    except Exception as e:
        print("chatterbox not available:", e)
        return
    model = ChatterboxTTS.from_pretrained(device="cpu")
    for name, exag, cfg in [("chatterbox-calm", 0.35, 0.4), ("chatterbox-warm", 0.55, 0.5)]:
        chunks = []
        for line in LINES:
            wav = model.generate(line, exaggeration=exag, cfg_weight=cfg)
            chunks.append(wav.squeeze().cpu().numpy())
            chunks.append(np.zeros(int(0.55 * model.sr), np.float32))
        save(name, np.concatenate(chunks), model.sr)


if __name__ == "__main__":
    kokoro()
    chatterbox()
    json.dump({"lines": LINES}, open(os.path.join(OUT, "lines.json"), "w"), indent=1)
