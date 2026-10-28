import os, shutil, sys
os.symlink = lambda s, d, *a, **k: shutil.copy(s, d)
sys.path.insert(0, '.')
import reels_common as C
FD = os.path.join(C.ROOT, "doc", "fonts")
C.bs.BASK = os.path.join(FD, "GFSBaskerville.otf")      # the Linux paths hard-coded in shorts.py, repointed here
C.bs.MONO = os.path.join(FD, "DejaVuSansMono-Bold.ttf")
import reel_afterdark_us as M
name, mode = sys.argv[1], sys.argv[2]
times = [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None
M.main(name, mode, times)
