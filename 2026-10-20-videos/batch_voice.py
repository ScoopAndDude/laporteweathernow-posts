#!/usr/bin/env python3
"""The Oct. 19 batch again, with the voiceover (recorded on GitHub in the daily video's voice:
Kokoro-82M af_heart, speed 1.1). Each scene lasts at least as long as its line plus a breath,
the same timing rule as the daily video (scripts/daily_video.py: LEAD 0.10 s, TAIL 0.30 s).

  python3 batch_voice.py VOICE_DIR [name ...]     (VOICE_DIR has <video>-<scene>.wav and seconds.json)
Writes out-voice/<file>.mp4 (and the cover JPG).
"""
import copy
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

import batch_oct19 as B
import render_reels as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUTV = os.path.join(HERE, "out-voice")
LEAD, TAIL, TAIL_LAST, RATE = 0.10, 0.30, 0.70, 24000
KEY = {"lpwn-reel-1": "1", "lpwn-reel-2": "2", "lpwn-reel-3": "3", "lpwn-reel-4": "4",
       "lpwn-reel-6": "6", "lpwn-reel-7": "7", "lpwn-reel-8": "8", "lpwn-reel-9": "9"}


def voiced(reel, vdir):
    key = KEY[reel["file"][:11]]
    reel = copy.deepcopy(reel)
    clips = []
    for i, b in enumerate(reel["beats"]):
        a, r = sf.read(os.path.join(vdir, f"{key}-{i + 1}.wav"), dtype="float32")
        if a.ndim > 1:
            a = a.mean(axis=1)
        assert r == RATE, (r, RATE)
        loud = np.flatnonzero(np.abs(a) > 0.01)          # trim the recording's own silence (keep 60 ms)
        if loud.size:
            pad = int(0.06 * RATE)
            a = a[max(0, loud[0] - pad):min(len(a), loud[-1] + pad)]
        lead = 0.04 if i == 0 else LEAD
        tail = TAIL_LAST if i == len(reel["beats"]) - 1 else TAIL
        b["dur"] = round(max(b["dur"], lead + len(a) / RATE + tail), 2)
        clips.append((lead, a))
    total = sum(b["dur"] for b in reel["beats"])
    track = np.zeros(int((total + 0.5) * RATE), dtype=np.float32)
    t = 0.0
    for b, (lead, a) in zip(reel["beats"], clips):
        i = int((t + lead) * RATE)
        track[i:i + len(a)] += a[:max(0, len(track) - i)]
        t += b["dur"]
    return reel, track, total


def main(vdir, want):
    os.makedirs(OUTV, exist_ok=True)
    R.OUT = os.path.join(HERE, "out-silent-timed")
    for reel in B.ALL:
        if want and not any(w in reel["file"] for w in want):
            continue
        reel, track, total = voiced(reel, vdir)
        R.render_reel(reel)                       # the picture, timed to the voice
        wav = os.path.join(R.OUT, reel["file"] + "-voice.wav")
        sf.write(wav, track, RATE)
        silent = os.path.join(R.OUT, reel["file"] + ".mp4")
        out = os.path.join(OUTV, reel["file"] + ".mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-ar", "48000", "-ac", "2",
                        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
        os.replace(os.path.join(R.OUT, reel["file"] + ".jpg"), os.path.join(OUTV, reel["file"] + ".jpg"))
        print(f"  with voice: {out}  {total:.1f} s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
