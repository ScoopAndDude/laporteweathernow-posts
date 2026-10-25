import sys, traceback
import numpy as np
from core import W, H, FPS, vignette
from render import active_weights
import shots as S

tl, shots, ovs, total = S.build()
lo = float(sys.argv[1]) if len(sys.argv) > 1 else 0
hi = float(sys.argv[2]) if len(sys.argv) > 2 else total
times = set()
for s in shots:
    if lo <= s.t <= hi:
        for k in range(-14, 15, 2):
            times.add(round(s.t * FPS) + k)
    if lo <= s.end <= hi:
        times.add(int(s.end * FPS) - 1)
built = {}
bad = 0
for f in sorted(times):
    t = f / FPS
    if t < 0 or t >= total:
        continue
    try:
        frame = None
        for i in range(len(shots)):
            wgt, a0, a1 = active_weights(shots, i, t)
            if wgt <= 0:
                continue
            if i not in built:
                s = shots[i]
                built[i] = s.factory(s.end - s.t, s.t)
            u = (t - a0) / max(0.01, a1 - a0)
            img = built[i].render(t - shots[i].t, min(1.0, max(0.0, u)))
            if not np.isfinite(img).all():
                raise ValueError("non-finite pixels in %s" % shots[i].name)
            frame = img if frame is None else frame * (1 - wgt) + img * wgt
        frame = frame * vignette()
        for o in ovs:
            o.draw(frame, t)
    except Exception:
        bad += 1
        print("FAILED at t=%.3f" % t)
        traceback.print_exc()
        if bad > 3:
            break
    for i in list(built):
        if shots[i].end + 1.0 < t:
            built[i].free()
            del built[i]
print("scan done", lo, hi, "failures", bad)
