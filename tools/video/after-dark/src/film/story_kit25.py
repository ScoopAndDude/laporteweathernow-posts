"""Props for the Schererville short (Lake George and the Hart Ditch), added Nov. 17, 2026. They register in
story_kit3.PROPS like every prop.

    ditch      a dug drainage ditch seen from down inside it: raw earth walls rise on both sides and the cut runs
               to a point at (x, y) on the horizon: w = the floor's near width in px, bank = how far the walls
               rise above the horizon at the picture's edges (px), water = the water's colour ("" for a dry cut), spoil=True heaps of dug earth
               along both banks, snow=True frozen ground with snow on the banks, trees=0..1 brush along it
    marsh      a wide shallow lake in a marsh, seen from its edge: open water to the horizon at y with reed beds
               and tussocks in the foreground (draw it on a "water" ground)
    spades     a few spades and a wheelbarrow left standing in the ground (no people)

No one is drawn in the ditch, and the cave-in itself isn't shown.
"""
import story_kit3 as K3

prop = K3.prop
H = 1920


@prop
def ditch(c, L, x, y, s=1.0, w=520, bank=260, water="#22323a", spoil=False, snow=False, trees=0.0, seed=3, **k):
    """A dug ditch seen from down inside it: raw earth walls rising on both sides, the cut running to a vanishing
    point at (x, y) on the horizon (see the top of this file)."""
    W = 1080
    earth = "#2c2118" if not snow else "#342c24"
    dark = "#140e0a" if not snow else "#1c1814"
    hw = w / 2
    bx = k.get("bx", 540)
    if water:                                                                      # the floor of the cut
        c.poly([(x, y), (bx + hw, H + 10), (bx - hw, H + 10)], water, smooth=False)
        c.poly([(x, y), (bx + hw * 0.25, H + 10), (bx - hw * 0.1, H + 10)], "#9aa8ae" if snow else "#5a7480", 0.25,
               smooth=False)
    else:
        c.poly([(x, y), (bx + hw, H + 10), (bx - hw, H + 10)], dark, smooth=False)
    for sgn in (-1, 1):
        ex = -30 if sgn < 0 else W + 30                                            # the picture's edge on this side
        c.poly([(ex, y - bank), (x, y), (bx + sgn * hw, H + 10), (ex, H + 10)], earth, smooth=False)   # the wall
        for q in range(1, 8):                                                      # strata, fanning from the far end
            f = q / 8.0
            c.line([(x, y), (ex, y - bank + (H - y + bank) * f * 0.8)], dark, 2.2, 0.55)
        for q in range(26):                                                        # clods and stones in the wall
            f = 0.15 + 0.85 * K3.hash2(q, seed, 3 + sgn)
            g = K3.hash2(q, seed, 9 + sgn)
            px = x + (ex - x) * f
            top = y - bank * f
            py = top + (H - top) * g * 0.7 * f + 6
            c.ellipse(px, py, 5 + 16 * f, 3 + 8 * f, dark, 0.7)
        cap = "#8c969c" if snow else "#1a1c12"                                     # the ground surface on top
        c.poly([(ex, y - bank - 26), (x, y - 1), (x, y), (ex, y - bank)], cap, smooth=False)
        if spoil:                                                                  # dug earth heaped along the top
            for q in range(5):
                f = 0.25 + q * 0.17
                px = x + (ex - x) * f
                c.ellipse(px, y - bank * f - 10 * f, 90 * f, 46 * f, "#1c150e")
        if trees > 0:
            for q in range(4):
                if K3.hash2(q, seed, 5 + sgn) > trees:
                    continue
                f = 0.2 + q * 0.2
                px = x + (ex - x) * f
                K3.PROPS["tree"](c, L, px, y - bank * f - 6, s=0.3 + 1.3 * f, bare=snow, seed=q + seed)
    return []


@prop
def marsh(c, L, x, y, s=1.0, seed=2, **k):
    """A wide shallow marsh lake: open water to the horizon with reed beds and tussocks in front."""
    import art
    for j in range(5):                                                             # far reed islands on the water
        ix = 120 + K3.hash2(j, seed, 1) * 840
        iy = y + 18 + j * 22
        c.ellipse(ix, iy, 90 + 60 * K3.hash2(j, seed, 2), 5 + j, "#0a100c", 0.9)
    for j, (yy, n, h0, h1) in enumerate(((y + 150, 90, 30, 90), (y + 260, 110, 50, 150), (y + 400, 130, 80, 220))):
        c.ellipse(260 + j * 250, yy + 10, 420, 26 + j * 10, "#070b08", 0.95)        # a mud tussock
        art.reeds(c, yy, -40 + j * 120, 620 + j * 240, "#060a08", n=n, hmin=h0, hmax=h1)
    return []


@prop
def spades(c, L, x, y, s=1.0, n=3, **k):
    """A few spades and a wheelbarrow left standing in the ground (no people)."""
    for j in range(n):
        px = x + (j - n / 2) * 70 * s
        lean = (-10, 6, 14)[j % 3] * s
        c.line([(px, y), (px + lean, y - 150 * s)], "#3a2a1a", 6 * s)
        c.rect(px + lean - 16 * s, y - 158 * s, px + lean + 16 * s, y - 150 * s, "#3a2a1a")
        c.poly([(px - 16 * s, y - 34 * s), (px + 16 * s, y - 34 * s), (px + 12 * s, y + 6 * s), (px - 12 * s, y + 6 * s)],
               "#15171a", smooth=False)
    bx = x + n * 60 * s
    c.poly([(bx, y - 70 * s), (bx + 150 * s, y - 70 * s), (bx + 120 * s, y - 20 * s), (bx + 30 * s, y - 20 * s)], "#1c140e",
           smooth=False)
    c.circle(bx + 30 * s, y - 14 * s, 18 * s, "#0c0c0c")
    c.line([(bx + 120 * s, y - 60 * s), (bx + 230 * s, y - 90 * s)], "#2a1e14", 6 * s)
    return []
