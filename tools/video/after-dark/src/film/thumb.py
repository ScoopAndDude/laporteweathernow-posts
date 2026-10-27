"""YouTube thumbnail for "Before Pumpkins: The Real History of Halloween".

python3 thumb.py OUT.jpg
"""
import sys

import cv2
import numpy as np

from core import OW, OH, W, H, Canvas, Camera, rgb, text_layer, paste, vignette, Embers, GHOST
from interior import Light, light_scene, stone_blocks, wood
from scene import Painted, const


DIM, SKIN = 0.06, 0.50
KEY = 1.0
FONTS = ("fell", "fell")


def scene():
    lx, ly, r = OW * 0.735, OH * 0.47, 330

    def build(ctx):
        alb = stone_blocks(OH, OW, "#5c564e", seed=4, bh=84, bw=(140, 230))
        ledge = int(ly + r * 1.07)
        alb[ledge:] = wood(OH - ledge, OW, "#4a3424", seed=2, along="x") * 0.9
        alb[ledge:ledge + 16] *= 0.3
        light_scene(ctx, alb, [Light("wall", lx, ly + 40, 520, 2300, "#ff9a4a", 1.75, const(1.0))],
                    ambient=("#22323a", 0.05))
        sh = Canvas()
        sh.ellipse(lx, ledge + 8, r * 1.2, r * 0.16, "#000000", 0.8, blur=16)
        ctx.cv = sh
        # the lantern, plus a soft key light from the upper left so the purple top reads as a turnip
        from art import lantern_parts, comp
        from interior import falloff
        ctx.flush()
        base, skin, holes, mask = lantern_parts("turnip", lx, ly, r, face=1, seed=1, w=OW, h=OH, dim=DIM,
                                                skin_k=SKIN)
        ctx.occlude_mask(mask)
        comp(ctx.bg, base)
        albedo = base[..., :3] / DIM
        key = falloff(lx - r * 1.6, ly - r * 1.4, r * 0.8, r * 4.2) * KEY
        halo = Canvas()
        halo.glow(lx, ly + r * 0.2, r * 3.4, "#ff8a2a", 0.24)
        ctx.light_np("lantern", skin + holes + halo.rgb() + albedo * key[..., None] * rgb("#c9b8d8")[None, None, :],
                     const(1.0))

    return Painted(build, dur=1.0, cam=Camera(1.0, 1.0), name="thumb")


def main(out):
    sc = scene()
    frame = sc.render(0.5, 0.5).astype(np.float32)
    # embers drifting up from the lantern
    em = Embers(40, 1250, 1700, 640, rise=210, spread=50, seed=9)
    em.draw(frame, 2.3, k=0.8)
    # darken the left so the title reads
    xx = np.linspace(0, 1, W, dtype=np.float32)
    shade = 0.28 + 0.72 * np.clip((xx - 0.12) / 0.55, 0, 1) ** 1.4
    frame *= shade[None, :, None]
    frame *= vignette(0.6, 2.2)
    cx = 548
    for (txt, size, y), fn in zip((("Before", 205, 352), ("Pumpkins", 236, 594)), FONTS):
        if fn != "black":
            size = int(size * 0.92)
        lay = text_layer(txt, fn, size, "#f6ead0", glow="#ff7a1a", glow_a=0.75, shadow=0.9)
        paste(frame, lay, cx, y)
    sub = text_layer("THE REAL HISTORY OF HALLOWEEN", "sans_b", 40, GHOST, tracking=0.22, shadow=0.8)
    paste(frame, sub, cx, 808)
    frame = np.clip(0.01 + frame * 0.99, 0, 1)
    img = (frame * 255 + 0.5).astype(np.uint8)
    img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_AREA)
    cv2.imwrite(out, cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 93])
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
