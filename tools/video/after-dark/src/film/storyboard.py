"""Render one frame from the middle of every shot (with overlays) into contact sheets."""
import multiprocessing as mp
import sys
import traceback

import cv2
import numpy as np

from core import W, H, FPS, vignette, clamp01


def job(idx):
    import shots as S
    tl, shots, ovs, total = S.build()
    s = shots[idx]
    try:
        sc = s.factory(s.end - s.t, s.t)
        tm = s.t + (s.end - s.t) * 0.6
        f = sc.render(tm - s.t, 0.6)
        f = f * vignette()
        for o in ovs:
            o.draw(f, tm)
        f = clamp01(0.012 + f * 0.988)
        sc.free()
        small = (cv2.resize(f, (W // 4, H // 4), interpolation=cv2.INTER_AREA) * 255).astype(np.uint8)
        cv2.putText(small, "%d %s %.1f" % (idx, s.name, s.t), (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 80), 1,
                    cv2.LINE_AA)
        return idx, small, None
    except Exception:
        return idx, None, traceback.format_exc()


if __name__ == "__main__":
    import shots as S
    tl, shots, ovs, total = S.build()
    n = len(shots)
    with mp.get_context("fork").Pool(2) as pool:
        res = pool.map(job, range(n))
    tiles = []
    for idx, img, err in sorted(res, key=lambda r: r[0]):
        if err:
            print("SHOT", idx, shots[idx].name, "FAILED\n", err)
            img = np.zeros((H // 4, W // 4, 3), np.uint8)
            img[:] = (128, 0, 0)
        tiles.append(img)
    cols = 5
    rows = []
    for r in range(0, len(tiles), cols):
        row = tiles[r:r + cols]
        while len(row) < cols:
            row.append(np.zeros_like(tiles[0]))
        rows.append(np.concatenate(row, axis=1))
    per = 6
    for k in range(0, len(rows), per):
        sheet = np.concatenate(rows[k:k + per], axis=0)
        cv2.imwrite(sys.argv[1] + "_%d.jpg" % (k // per), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
    print("ok", n)
