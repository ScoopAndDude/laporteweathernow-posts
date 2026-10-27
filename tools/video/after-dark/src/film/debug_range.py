import sys, traceback
import numpy as np
from core import W, H, FPS, vignette
from render import active_weights
import shots as S

t0, t1 = float(sys.argv[1]), float(sys.argv[2])
step = int(sys.argv[3]) if len(sys.argv) > 3 else 1
tl, shots, ovs, total = S.build()
built = {}
for f in range(int(t0 * FPS), int(t1 * FPS), step):
    t = f / FPS
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
            frame = img if frame is None else frame * (1 - wgt) + img * wgt
        frame = frame * vignette()
        for o in ovs:
            o.draw(frame, t)
    except Exception:
        print("FAILED at t=%.3f frame %d" % (t, f))
        traceback.print_exc()
        sys.exit(1)
print("ok", t0, t1)
