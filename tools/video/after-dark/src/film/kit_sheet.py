"""Contact sheet of story_kit scenes: python3 kit_sheet.py [kind[:json-options] ...] -> shorts/out/kit_sheet.jpg"""
import json
import os
import sys
import time

from PIL import Image

import story_kit as K
from reel_frank import to_pil

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shorts", "out")


def main(args):
    specs = []
    for a in args or list(K.KINDS):
        kind, _, opt = a.partition(":")
        sp = json.loads(opt) if opt else {}
        sp["kind"] = kind
        specs.append(sp)
    tiles = []
    for sp in specs:
        t0 = time.time()
        s = K.make(dict(sp), 6.0)
        t1 = time.time()
        im = to_pil(s.render(2.0, 2.0)).convert("RGB")
        t2 = time.time()
        print("%-12s build %.1fs  frame %.2fs" % (sp["kind"], t1 - t0, t2 - t1), flush=True)
        im.save(os.path.join(OUT, "kit_%s.jpg" % sp["kind"]), quality=88)
        tiles.append(im.resize((360, 640), Image.LANCZOS))
    cols = min(6, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (360 * cols, 640 * rows))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * 360, (i // cols) * 640))
    p = os.path.join(OUT, "kit_sheet.jpg")
    sheet.save(p, quality=85)
    print(p)


if __name__ == "__main__":
    main(sys.argv[1:])
