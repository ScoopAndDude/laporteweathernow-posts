"""Render clean source footage for the shorts: no lower thirds, no callouts, no vignette.

python3 render_clips.py SPEC.json OUTDIR [NAME ...]

SPEC is a list of clips: {"name": "b", "segs": [[t0, t1, mode], ...]}
mode "film" renders the cut as in the documentary (crossfades and all);
mode "<shot name>" renders only that shot, even outside its own time on screen.
Each clip becomes OUTDIR/<name>.mp4 plus OUTDIR/<name>.json listing the source time of every frame.
"""
import json
import os
import subprocess
import sys
import time

import numpy as np

from core import W, H, FPS
from render import active_weights


def main():
    spec_path, outdir = sys.argv[1], sys.argv[2]
    only = set(sys.argv[3:])
    spec = json.load(open(spec_path))
    import shots as S
    tl, shots, ovs, total = S.build()
    index = {s.name: i for i, s in enumerate(shots)}
    rng = np.random.default_rng(5)
    dither = ((rng.random((H, W, 1), dtype=np.float32) - 0.5) * (1.6 / 255)).astype(np.float32)
    built = {}

    def scene(i):
        if i not in built:
            s = shots[i]
            built[i] = s.factory(s.end - s.t, s.t)
        return built[i]

    def window(i):
        s = shots[i]
        fn = shots[i + 1].fade if i + 1 < len(shots) else 0.0
        return s.t - s.fade / 2, s.end + fn / 2

    os.makedirs(outdir, exist_ok=True)
    for clip in spec:
        if only and clip["name"] not in only:
            continue
        out = os.path.join(outdir, clip["name"] + ".mp4")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
               "-pix_fmt", "yuv420p", "-g", "24", out]
        enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        times = []
        modes = []
        t_start = time.time()
        for t0, t1, mode in clip["segs"]:
            f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS))
            for f in range(f0, f1):
                t = f / FPS
                if mode == "film":
                    frame = None
                    for i in range(len(shots)):
                        wgt, a0, a1 = active_weights(shots, i, t)
                        if wgt <= 0:
                            continue
                        u = (t - a0) / max(0.01, a1 - a0)
                        img = scene(i).render(t - shots[i].t, min(1.0, max(0.0, u)))
                        frame = img if frame is None else frame * (1 - wgt) + img * wgt
                    if frame is None:
                        frame = np.zeros((H, W, 3), np.float32)
                else:
                    i = index[mode]
                    a0, a1 = window(i)
                    u = (t - a0) / max(0.01, a1 - a0)
                    frame = scene(i).render(t - shots[i].t, min(1.0, max(0.0, u))).copy()
                frame = 0.012 + frame * 0.988
                frame += dither
                np.clip(frame, 0, 1, out=frame)
                enc.stdin.write((frame * 255 + 0.5).astype(np.uint8).tobytes())
                times.append(round(t, 4))
                modes.append(mode)
                # free scenes whose time on screen is over
                if mode == "film":
                    for i in list(built):
                        if t > window(i)[1] + 0.1:
                            built[i].free()
                            del built[i]
            # a solo shot is done once its segment is
            if mode != "film":
                for i in list(built):
                    built[i].free()
                    del built[i]
        enc.stdin.close()
        enc.wait()
        json.dump({"fps": FPS, "times": times, "modes": modes}, open(os.path.join(outdir, clip["name"] + ".json"), "w"))
        print("%s: %d frames in %.1f min" % (clip["name"], len(times), (time.time() - t_start) / 60), flush=True)
        for i in list(built):
            built[i].free()
            del built[i]


if __name__ == "__main__":
    main()
