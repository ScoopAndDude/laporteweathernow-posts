"""Render the film's picture: python3 render.py OUTDIR [--from S --to S] [--workers N] [--crf 20] [--preset medium]"""
import argparse
import math
import multiprocessing as mp
import os
import subprocess
import sys
import time

import numpy as np

from core import W, H, FPS, vignette, Grain, clamp01, sstep


def active_weights(shots, i, t):
    """Visibility of shot i at time t (crossfades centred on each cut)."""
    s = shots[i]
    fi = s.fade
    fn = shots[i + 1].fade if i + 1 < len(shots) else 0.0
    a0 = s.t - fi / 2
    a1 = s.end + fn / 2
    if t < a0 or t >= a1:
        return 0.0, a0, a1
    win = 1.0 if fi <= 0.001 else sstep(s.t - fi / 2, s.t + fi / 2, t)
    if i == 0 and t < s.t + 0.001:
        win = 1.0
    return win, a0, a1


def render_range(args):
    k, f0, f1, out, crf, preset = args[:6]
    import shots as S
    tl, shots, ovs, total = S.build()
    vig = vignette()
    # a fixed, invisible dither pattern stops dark gradients from banding without costing bitrate
    rng = np.random.default_rng(5)
    dither = ((rng.random((H, W, 1), dtype=np.float32) - 0.5) * (1.6 / 255)).astype(np.float32)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-tune", "film",
           "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", "48", "-bf", "3", out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    built = {}
    t_start = time.time()
    log = open(out + ".log", "w")
    for f in range(f0, f1):
        t = f / FPS
        frame = None
        for i in range(len(shots)):
            wgt, a0, a1 = active_weights(shots, i, t)
            if wgt <= 0:
                continue
            if i not in built:
                s = shots[i]
                built[i] = s.factory(s.end - s.t, s.t)
            sc = built[i]
            u = (t - a0) / max(0.01, a1 - a0)
            img = sc.render(t - shots[i].t, min(1.0, max(0.0, u)))
            if frame is None:
                frame = img
            else:
                frame = frame * (1 - wgt) + img * wgt
        if frame is None:
            frame = np.zeros((H, W, 3), np.float32)
        frame *= vig
        for o in ovs:
            o.draw(frame, t)
        frame = 0.012 + frame * 0.988
        frame += dither
        np.clip(frame, 0, 1, out=frame)
        enc.stdin.write((frame * 255 + 0.5).astype(np.uint8).tobytes())
        # free scenes that are finished
        for i in list(built):
            s = shots[i]
            fn = shots[i + 1].fade if i + 1 < len(shots) else 0.0
            if t > s.end + fn / 2 + 0.1:
                built[i].free()
                del built[i]
        if (f - f0) % 240 == 0:
            el = time.time() - t_start
            done = f - f0 + 1
            print("[w%d] frame %d/%d  t=%.1fs  %.0f ms/frame  eta %.1f min" % (
                k, done, f1 - f0, t, el / done * 1000, el / done * (f1 - f) / 60), file=log, flush=True)
    enc.stdin.close()
    enc.wait()
    print("[w%d] done %.1f min" % (k, (time.time() - t_start) / 60), file=log, flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--frames", nargs=2, type=int, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.frames:
        os.makedirs(a.outdir, exist_ok=True)
        render_range((9, a.frames[0], a.frames[1], a.out, a.crf, a.preset))
        return
    import shots as S
    tl, shots, ovs, total = S.build()
    t1 = a.t1 if a.t1 is not None else total
    f0, f1 = int(round(a.t0 * FPS)), int(math.ceil(t1 * FPS))
    os.makedirs(a.outdir, exist_ok=True)
    # split at shot starts close to equal frame counts
    cuts = [f0]
    for k in range(1, a.workers):
        target = f0 + (f1 - f0) * k / a.workers
        best = min((int(round(s.t * FPS)) for s in shots if f0 < s.t * FPS < f1), key=lambda x: abs(x - target),
                   default=int(target))
        cuts.append(best)
    cuts.append(f1)
    jobs = [(k, cuts[k], cuts[k + 1], os.path.join(a.outdir, "part%d.mp4" % k), a.crf, a.preset)
            for k in range(a.workers)]
    print("frames", f0, f1, "cuts", cuts, flush=True)
    with mp.get_context("fork").Pool(a.workers) as pool:
        outs = pool.map(render_range, jobs)
    lst = os.path.join(a.outdir, "parts.txt")
    with open(lst, "w") as fh:
        for o in outs:
            fh.write("file '%s'\n" % os.path.abspath(o))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(a.outdir, "video.mp4")], check=True)
    print("wrote", os.path.join(a.outdir, "video.mp4"))


if __name__ == "__main__":
    main()
