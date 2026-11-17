"""Props for the Munster short (the Brass Tavern and the Kaske House), added Nov. 17, 2026. They register in
story_kit3.PROPS like every prop.

    brasstavern  the Brass Tavern as Wilhelmine Kaske described it in 1934: "a large, two-story, flat-roofed frame
                 building" with "a small, open front porch the width of the house". lit=0..1 lit windows; pole=True
                 a telegraph pole with a wire to the wall. No sign is drawn (its wording isn't known). The
                 National Register form says "low-pitched gable roof"; the flat roof follows her, who lived there.
    charbeams    what a fire left: a low limestone foundation with heavy charred timbers fallen across it, embers
                 glowing (glow=0..1) and thin smoke rising. No one is shown.
    foursquare   the 1910 Kaske House as the National Register describes it: a two-storey American Foursquare frame
                 house with clapboard siding, a clipped-gable (jerkinhead) roof and a front porch. one=[row, col]
                 lights a single window (row 0 = upstairs, col 0..2); lit=0..1 lights windows at random.

The fire's time of day isn't in the sources, so no burning building is drawn: only the smouldering beams she
described ("the beams smouldered for days").
"""
import story_kit3 as K3
from story_kit import WARM

prop = K3.prop


@prop
def brasstavern(c, L, x, y, s=1.0, lit=0.5, pole=False, porch=True, seed=5, **k):
    """A large, two-storey, flat-roofed frame inn of 1845 (see the top of this file)."""
    hw, hh = 300 * s, 330 * s
    out = []
    c.rect(x - hw, y - hh, x + hw, y, "#15110d")
    for j in range(33):                                                            # clapboards
        c.line([(x - hw, y - j * 10 * s), (x + hw, y - j * 10 * s)], "#1d1812", 1.0, 0.7)
    c.rect(x - hw - 14 * s, y - hh - 18 * s, x + hw + 14 * s, y - hh, "#090807")   # the flat roof's cornice
    c.rect(x - hw - 6 * s, y - hh, x + hw + 6 * s, y - hh + 8 * s, "#0d0b09")
    for cx in (-200, 190):                                                         # two brick chimneys
        c.rect(x + cx * s - 16 * s, y - hh - 70 * s, x + cx * s + 16 * s, y - hh - 18 * s, "#1c1310")
    for row, wy in enumerate((290, 150)):                                          # two rows of windows
        for col in range(6):
            if row == 1 and col == 3:
                continue                                                           # the door goes here
            wx = x - hw + (34 + col * 96) * s
            on = K3.hash2(col, row, seed) < lit
            c.rect(wx, y - wy * s, wx + 46 * s, y - (wy - 86) * s, WARM if on else "#070606", 0.85 if on else 1.0)
            if on:
                L.rect(wx, y - wy * s, wx + 46 * s, y - (wy - 86) * s, WARM, 0.45)
                out.append((wx + 23 * s, y - (wy - 43) * s, (1.0, 0.75, 0.45), 70 * s, False, 0.25))
            c.line([(wx + 23 * s, y - wy * s), (wx + 23 * s, y - (wy - 86) * s)], "#15110d", 2 * s)
            c.line([(wx, y - (wy - 43) * s), (wx + 46 * s, y - (wy - 43) * s)], "#15110d", 2 * s)
    dx = x - hw + (34 + 3 * 96) * s                                                # the front door
    c.rect(dx - 4 * s, y - 150 * s, dx + 54 * s, y, "#070606")
    if porch:                                                                      # a small open porch, the width of the house
        c.rect(x - hw - 10 * s, y - 14 * s, x + hw + 10 * s, y, "#0d0b09")
        c.poly([(x - hw - 16 * s, y - 168 * s), (x + hw + 16 * s, y - 168 * s), (x + hw + 26 * s, y - 152 * s),
                (x - hw - 26 * s, y - 152 * s)], "#090807", smooth=False)
        for j in range(7):
            px = x - hw - 4 * s + j * (2 * hw + 8 * s) / 6
            c.rect(px - 5 * s, y - 154 * s, px + 5 * s, y - 14 * s, "#0d0b09")
    if pole:
        px = x + hw + 120 * s
        c.rect(px - 5 * s, y - 430 * s, px + 5 * s, y, "#0b0a09")
        c.rect(px - 40 * s, y - 410 * s, px + 40 * s, y - 402 * s, "#0b0a09")
        c.line([(px - 30 * s, y - 410 * s), (x + hw, y - hh + 40 * s)], "#2a2622", 1.6 * s)
        c.line([(px + 30 * s, y - 410 * s), (px + 400 * s, y - 380 * s)], "#2a2622", 1.6 * s)
    return out


@prop
def charbeams(c, L, x, y, s=1.0, glow=0.7, seed=2, **k):
    """A limestone foundation with heavy charred timbers fallen across it, embers and thin smoke."""
    out = []
    w = 360 * s
    for j in range(12):                                                            # the foundation's stones
        bx = x - w + j * (2 * w / 12)
        c.rect(bx + 2 * s, y - 46 * s, bx + 2 * w / 12 - 2 * s, y, "#3a3830" if j % 2 else "#33312a")
    c.rect(x - w, y - 50 * s, x + w, y - 44 * s, "#2a2822")
    beams = [(-300, -50, 120, -210, 22), (-120, -48, 260, -150, 20), (-240, -120, 60, -60, 18),
             (40, -52, 330, -250, 22), (-40, -48, -10, -300, 20), (180, -50, 210, -230, 18)]
    for i, (ax, ay, bx, by, th) in enumerate(beams):
        c.line([(x + ax * s, y + ay * s), (x + bx * s, y + by * s)], "#070606", th * s)
        if glow > 0:
            for q in range(5):                                                     # embers along each timber
                f = (K3.hash2(i, q, seed) * 0.8 + 0.1)
                ex, ey = x + (ax + (bx - ax) * f) * s, y + (ay + (by - ay) * f) * s
                c.circle(ex, ey, 3.2 * s, "#ff7a30", 0.8 * glow)
                L.circle(ex, ey, 9 * s, "#ff6a20", 0.6 * glow)
    if glow > 0:
        L.ellipse(x, y - 110 * s, 300 * s, 150 * s, "#ff5a18", 0.22 * glow, blur=60 * s)
    for j in range(9):                                                             # thin smoke
        c.ellipse(x + (-140 + j * 34) * s, y - (260 + j * 62) * s, (50 + j * 16) * s, (34 + j * 10) * s, "#6a6a6e",
                  0.11 - j * 0.009, blur=22 * s)
    return out


@prop
def foursquare(c, L, x, y, s=1.0, lit=0.0, one=None, seed=3, **k):
    """A two-storey American Foursquare frame house with a clipped-gable roof and a front porch."""
    hw, hh = 190 * s, 330 * s
    out = []
    wall = "#17130f"
    c.rect(x - hw, y - hh, x + hw, y, wall)
    for j in range(33):
        c.line([(x - hw, y - j * 10 * s), (x + hw, y - j * 10 * s)], "#201a14", 1.0, 0.7)
    top = y - hh - 150 * s                                                         # the jerkinhead (clipped gable)
    c.poly([(x - hw - 22 * s, y - hh), (x - 70 * s, top + 40 * s), (x, top), (x + 70 * s, top + 40 * s),
            (x + hw + 22 * s, y - hh)], "#080707", smooth=False)
    c.poly([(x - hw + 26 * s, y - hh), (x - 62 * s, top + 62 * s), (x + 62 * s, top + 62 * s),
            (x + hw - 26 * s, y - hh)], wall, smooth=False)
    c.poly([(x - 78 * s, top + 44 * s), (x, top + 4 * s), (x + 78 * s, top + 44 * s), (x + 62 * s, top + 64 * s),
            (x - 62 * s, top + 64 * s)], "#080707", smooth=False)                  # the clipped peak
    c.rect(x - 26 * s, y - hh - 64 * s, x + 26 * s, y - hh - 14 * s, "#070606")    # attic window
    c.rect(x + 96 * s, top + 10 * s, x + 124 * s, y - hh - 40 * s, "#1c1310")      # chimney

    def win(wx, wy, ww, wh, on):
        c.rect(wx, wy, wx + ww, wy + wh, WARM if on else "#070606", 0.88 if on else 1.0)
        if on:
            L.rect(wx, wy, wx + ww, wy + wh, WARM, 0.5)
            out.append((wx + ww / 2, wy + wh / 2, (1.0, 0.75, 0.45), 110 * s, False, 0.4))
        c.line([(wx + ww / 2, wy), (wx + ww / 2, wy + wh)], wall, 2 * s)
        c.line([(wx, wy + wh / 2), (wx + ww, wy + wh / 2)], wall, 2 * s)

    for col in range(3):                                                           # upstairs
        on = (one is not None and list(one) == [0, col]) or (one is None and K3.hash2(col, 0, seed) < lit)
        win(x - hw + (36 + col * 124) * s, y - 296 * s, 60 * s, 96 * s, on)
    for col in (0, 2):                                                             # downstairs, beside the door
        on = (one is not None and list(one) == [1, col]) or (one is None and K3.hash2(col, 1, seed) < lit)
        win(x - hw + (36 + col * 124) * s, y - 150 * s, 60 * s, 96 * s, on)
    c.rect(x - 28 * s, y - 150 * s, x + 28 * s, y - 22 * s, "#070606")             # front door
    c.poly([(x - hw - 18 * s, y - 176 * s), (x + hw + 18 * s, y - 176 * s), (x + hw + 2 * s, y - 204 * s),
            (x - hw - 2 * s, y - 204 * s)], "#090807", smooth=False)               # porch roof
    for px in (-hw - 6 * s, -64 * s, 64 * s, hw + 6 * s):                          # porch posts
        c.rect(x + px - 6 * s, y - 176 * s, x + px + 6 * s, y - 22 * s, "#0b0a09")
    c.rect(x - hw - 16 * s, y - 24 * s, x + hw + 16 * s, y, "#0b0a09")             # porch floor and steps
    c.rect(x - 50 * s, y - 12 * s, x + 50 * s, y + 6 * s, "#0d0c0a")
    return out
