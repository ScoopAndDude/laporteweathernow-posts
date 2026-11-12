"""Painted scenes: a finished picture (for example one made in Canva) used as the whole scene, with the usual
slow camera move and the usual extras (snow, fog, rain) on top.

    {"kind": "paint", "src": "paint/xmas/p1_schooner.jpg", "move": "in", "amount": 0.1, "focus": [540, 900],
     "snow": true, "dim": 0.9, "amb": "waves"}

The picture is fitted to cover 1080x1920. If it was made by an AI tool the short must say so: put
"AI-generated pictures" in the credit line and mark the post as AI-generated where the platform asks.
"""
import os

import cv2
import numpy as np

import story_kit as K

W, H = K.W, K.H
HERE = os.path.dirname(os.path.abspath(__file__))


class Painting(K.Shot):
    focus = (540, 900)
    fog_d = 0.0

    def __init__(self, p=None):
        super().__init__(p)
        path = self.p["src"]
        if not os.path.isabs(path):
            path = os.path.join(HERE, path)
        im = cv2.imread(path, cv2.IMREAD_COLOR)
        if im is None:
            raise FileNotFoundError(path)
        h, w = im.shape[:2]
        s = max(W / w, H / h)
        im = cv2.resize(im, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_LANCZOS4)
        h, w = im.shape[:2]
        x0, y0 = (w - W) // 2, (h - H) // 2
        im = im[y0:y0 + H, x0:x0 + W, ::-1].astype(np.float32) / 255.0
        im *= float(self.p.get("dim", 0.92))
        # a soft dark edge so captions and labels read on any picture
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        im *= 1.0 - 0.38 * np.clip((yy - 0.62) / 0.38, 0, 1) ** 1.5
        im *= 1.0 - 0.30 * np.clip((0.14 - yy) / 0.14, 0, 1) ** 1.5
        self.img = np.ascontiguousarray(im)


K.KINDS["paint"] = Painting
K.AMBIENCE["paint"] = ("waves", None)
