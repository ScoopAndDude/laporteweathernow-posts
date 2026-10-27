"""Render a few frames of scenes into a contact sheet for checking.

python3 preview.py OUT.jpg "lib1.road_scene(8)" "lib1.graveyard(8)" ... [--t 0.2,0.6] [--full]
"""
import importlib
import sys
import time

import cv2
import numpy as np

from core import W, H, vignette, clamp01, Grain


def finish(frame):
    out = frame * vignette()
    out = 0.010 + out * 0.99
    return clamp01(out)


def main():
    args = sys.argv[1:]
    out = args.pop(0)
    ts = [0.15, 0.85]
    full = False
    if "--t" in args:
        i = args.index("--t")
        ts = [float(x) for x in args[i + 1].split(",")]
        del args[i:i + 2]
    if "--full" in args:
        full = True
        args.remove("--full")
    rows = []
    for expr in args:
        ns = {}
        for mod in ("lib1", "lib2", "lib3", "lib4", "lib5", "cards"):
            try:
                ns[mod] = importlib.import_module(mod)
            except ModuleNotFoundError:
                pass
        t0 = time.time()
        sc = eval(expr, ns)
        sc.ensure()
        tb = time.time() - t0
        frames = []
        tr = []
        for u in ts:
            t1 = time.time()
            f = sc.render(u * sc.dur, u)
            tr.append(time.time() - t1)
            frames.append(finish(f))
        print(f"{expr:40s} build {tb:5.2f}s  frame {np.mean(tr) * 1000:6.1f} ms", flush=True)
        if full:
            for k, f in enumerate(frames):
                cv2.imwrite(out.replace(".jpg", f"_{len(rows)}_{k}.jpg"),
                            cv2.cvtColor((f * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
        small = [cv2.resize(f, (W // 3, H // 3), interpolation=cv2.INTER_AREA) for f in frames]
        rows.append(np.concatenate(small, axis=1))
        sc.free()
    sheet = np.concatenate(rows, axis=0)
    cv2.imwrite(out, cv2.cvtColor((sheet * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])


if __name__ == "__main__":
    main()
