#!/usr/bin/env python3
"""Records lines.json with the weather radio's voice (Kokoro-82M, af_heart) into voice/NN.wav (24 kHz) and
voice/voice.json. Runs in GitHub Actions (.github/workflows/belle-voice.yml), where the model downloads."""
import json
import os

import numpy as np
import soundfile as sf
from kokoro import KPipeline

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE, SPEED, RATE = "af_heart", 0.94, 24000
PRONOUNCE = {"La Porte": "ləpˈɔɹt", "Gunness": "ɡˈʌnəs"}   # "luh-PORT", "GUN-ess"


def main():
    lines = json.load(open(os.path.join(HERE, "lines.json"), encoding="utf-8"))["lines"]
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    out = os.path.join(HERE, "voice")
    os.makedirs(out, exist_ok=True)
    record = []
    for ln in lines:
        text = ln["say"]
        for word, sounds in PRONOUNCE.items():
            text = text.replace(word, f"[{word}](/{sounds}/)")
        chunks = []
        for result in pipe(text, voice=VOICE, speed=SPEED, split_pattern=r"\n+"):
            audio = result.audio if hasattr(result, "audio") else result[2]
            if audio is None:
                continue
            chunks.append(audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio))
        audio = np.concatenate(chunks).astype(np.float32)
        sf.write(os.path.join(out, ln["id"] + ".wav"), audio, RATE)
        record.append({"id": ln["id"], "say": ln["say"], "seconds": round(len(audio) / RATE, 2)})
        print(ln["id"], record[-1]["seconds"], "s")
    with open(os.path.join(out, "voice.json"), "w", encoding="utf-8") as fh:
        json.dump({"voice": f"Kokoro-82M {VOICE}, speed {SPEED}", "rate": RATE, "lines": record}, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
