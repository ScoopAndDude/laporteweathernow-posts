"""Redo a finished reel's sound with a lower limiter ceiling (keeps the video stream as is).

python3 remix_audio.py belle6
"""
import os
import re
import subprocess
import sys

import numpy as np
import soundfile as sf

import reels_common as C


def main(name, ceiling=0.66):
    if name == "belle6":
        import reel_belle6 as M
        R = C.Reel("belle6")
        film, ev, music, title = M.build(R)
        mix = C.soundtrack(R, music, ev)
        out = os.path.join(C.OUT, M.OUTFILE)
    else:
        raise SystemExit("unknown reel")
    tmpv = out.replace(".mp4", "_v.mp4")
    os.replace(out, tmpv)
    wav = out.replace(".mp4", ".wav")
    raw = wav + ".raw.wav"
    sf.write(raw, np.stack([mix, mix], 1), C.SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", raw, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    gain = -14.0 - I + 0.35
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                    "volume=%.2fdB,alimiter=limit=%.2f:attack=2:release=60:level=false:latency=true" % (gain, ceiling),
                    "-c:a", "pcm_f32le", wav], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmpv, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", "%.3f" % (R.n / C.FPS), "-movflags",
                    "+faststart", "-metadata", "title=%s" % title, "-metadata", "artist=La Porte Weather Now", out],
                   check=True)
    for p in (raw, wav, tmpv):
        os.remove(p)
    print("remixed", out, C.measure(out))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.66)
