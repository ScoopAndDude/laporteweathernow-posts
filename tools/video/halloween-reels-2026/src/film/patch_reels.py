"""Re-render the opening seconds of finished reels (the first frame is what people see before it plays) and
remix their sound, keeping the rest of each earlier render.

    python3 patch_reels.py belle3 belle4 wx
"""
import os
import sys

import reels_common as C
import reel_belle
import reel_wx


def run(name):
    if name in ("belle3", "belle4"):
        R = C.Reel(name)
        film, ev, music, title = reel_belle.BUILD[name](R)
        out = os.path.join(C.OUT, reel_belle.FILES[name])
        gain = 0.55
        cover_t = 0.6
    else:
        R = C.Reel("wx")
        film, ev, music, title = reel_wx.build(R)
        out = os.path.join(C.OUT, reel_wx.OUTFILE)
        gain = 0.35
        cover_t = 0.8
    tmp = os.path.join(C.OUT, "_%s_patched.mp4" % name)
    n = C.patch_start(film, out, tmp, 60, cover_t=cover_t)
    print(name, "frames", n, "of", R.n, flush=True)
    mix = C.soundtrack(R, music, ev, music_gain=gain)
    C.finish(R, tmp, mix, out, title)
    os.replace(tmp.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(tmp)
    print("patched", out, C.measure(out), flush=True)


if __name__ == "__main__":
    for nm in sys.argv[1:]:
        run(nm)
