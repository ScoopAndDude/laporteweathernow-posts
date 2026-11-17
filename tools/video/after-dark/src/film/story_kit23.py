"""Props for the Porter short (the 1921 crossing collision), added Nov. 17, 2026. They register in
story_kit3.PROPS like every prop, so a storyboard names them in "props": [{"p": "semaphore", ...}].

    paxloco     a passenger steam locomotive of about 1920 (a Pacific: a long boiler, three big drivers, a short
                straight stack, an electric headlight on the smokebox) with its tender, side on. x is the front of
                the pilot; flip=True faces it left; beam=0..1 the headlight's beam; smoke=0..1 smoke and steam
                trailing back over the train (0 for none)
    coaches     passenger coaches of about 1920 behind an engine: n cars from x (the front of the first) running
                right (flip=True: left); lit=0..1 lit windows; wood=True a wooden coach's panelled side
    semaphore   a railroad semaphore signal on a mast: arm="stop" (blade level, red light) or "clear" (blade
                angled, green light); flip=True points the blade left; dim=0..1 fades the lamp (a light seen
                through smoke); arms=2 a second blade below the first (Porter's home signal had two)
    intertower  a two-storey frame interlocking tower: a band of lit windows upstairs, an outside stair, no name
                board (the real tower's lettering isn't known); lit=0..1
    crosstrack  a second track crossing the picture at an angle on flat ground: from (x, y) to (x2, y2), drawn as
                two rails on ties, thinner toward the far end (w = the near gauge in px, w2 the far one)
    steamcloud  a soft cloud of smoke and steam drifting across (w, h in px; a=0..1 how thick)

People aren't drawn. Nothing shows the collision itself, a wrecked car or anyone hurt.
The fact-check (Nov. 17, 2026) noted: the Michigan Central came off a long curve with only about 600 feet of
straight track before the crossing (so no straight-to-the-horizon view for it), and the first car behind the New
York Central engine was a wooden horse car (so no coach is drawn behind that engine).
The ICC report describes the Porter plant (a two-storey tower, semaphore home signals, a derail 311 feet from the
crossing, the lines crossing at about 45 degrees) but no source here gives the tower's look, so it is generic.
"""
import math

import story_kit3 as K3
from story_kit import WARM

prop = K3.prop
IRON = "#0c0d0e"


@prop
def paxloco(c, L, x, y, s=1.0, flip=False, beam=0.8, smoke=0.6, **k):
    """A passenger locomotive of about 1920 with its tender (see the top of this file)."""
    d = -1 if flip else 1
    out = []

    def X(v):
        return x - d * v * s

    def R(a, b, top, bot, col, r=0):
        c.rect(min(X(a), X(b)), y - top * s, max(X(a), X(b)), y - bot * s, col, r=r * s)

    def P(pts):
        return [(X(a), y - b * s) for a, b in pts]

    c.poly(P([(0, 8), (40, 8), (40, 60), (22, 60)]), IRON)                         # a short steel pilot
    R(40, 560, 92, 74, IRON)                                                       # the frame
    R(50, 120, 236, 92, IRON, r=8)                                                 # smokebox
    R(100, 430, 228, 100, "#101214", r=50)                                         # the long boiler
    for bx in (180, 260, 340):
        c.line([(X(bx), y - 226 * s), (X(bx), y - 104 * s)], "#26282a", 2 * s)
    R(72, 100, 272, 232, IRON)                                                     # a short straight stack
    R(66, 106, 280, 270, IRON)
    R(200, 240, 258, 222, IRON, r=16)                                              # sand dome
    R(300, 336, 254, 222, IRON, r=16)                                              # steam dome
    R(430, 560, 300, 92, "#0e0f10")                                                # the cab
    c.poly(P([(420, 300), (572, 300), (566, 314), (426, 314)]), IRON)
    wy0, wy1 = y - 282 * s, y - 222 * s
    R(452, 500, 282, 222, "#070505")
    L.rect(min(X(452), X(500)), wy0, max(X(452), X(500)), wy1, "#ff7a30", 0.35)
    out.append((X(476), (wy0 + wy1) / 2, (1.0, 0.5, 0.2), 60 * s, True, 0.3))
    for wx in (210, 300, 390):                                                     # three big drivers
        c.circle(X(wx), y - 46 * s, 46 * s, "#141516")
        c.circle(X(wx), y - 46 * s, 37 * s, "#0a0b0c")
        for t in range(12):
            a = 2 * math.pi * t / 12
            c.line([(X(wx), y - 46 * s), (X(wx) + 37 * s * math.cos(a), y - 46 * s + 37 * s * math.sin(a))],
                   "#1e2022", 2.2 * s)
    c.line([(X(210), y - 46 * s), (X(390), y - 46 * s)], "#2a2c2e", 6 * s)         # side rods
    c.line([(X(110), y - 60 * s), (X(210), y - 46 * s)], "#2a2c2e", 5 * s)         # main rod to the cylinder
    R(86, 150, 84, 40, "#121314", r=6)                                             # cylinder
    for wx in (70, 124):                                                           # leading truck
        c.circle(X(wx), y - 20 * s, 20 * s, "#141516")
    c.circle(X(470), y - 24 * s, 24 * s, "#141516")                                # trailing truck
    R(576, 820, 206, 70, "#0e0f10")                                                # the tender
    c.poly(P([(600, 206), (700, 206), (690, 226), (614, 230)]), "#060606")         # coal
    for wx in (612, 660, 740, 788):
        c.circle(X(wx), y - 22 * s, 22 * s, "#141516")
    hx, hy = X(52), y - 246 * s                                                    # electric headlight
    c.circle(hx, hy, 15 * s, "#151515")
    c.circle(X(46), hy, 11 * s, "#fff2c8", 0.95)
    L.circle(X(46), hy, 20 * s, "#ffe6a8", 0.85)
    out.append((X(46), hy, (1.0, 0.9, 0.68), 100 * s, False, 0.9))
    if beam > 0:
        ex = X(-1000)
        c.poly([(X(40), hy - 12 * s), (ex, hy - 150 * s), (ex, hy + 200 * s), (X(40), hy + 14 * s)],
               "#fff0c8", 0.07 * beam, blur=26 * s)
        L.poly([(X(40), hy - 12 * s), (ex, hy - 120 * s), (ex, hy + 170 * s), (X(40), hy + 12 * s)],
               "#ffe0a0", 0.16 * beam, blur=34 * s)
    if smoke > 0:
        for j in range(8):
            c.ellipse(X(100 + j * 90), y - (320 + j * 22) * s, (44 + j * 20) * s, (24 + j * 9) * s, "#55565a",
                      (0.16 - j * 0.014) * smoke, blur=14 * s)
    return out


@prop
def coaches(c, L, x, y, s=1.0, n=3, lit=0.6, flip=False, wood=False, seed=3, **k):
    """Passenger coaches of about 1920 (see the top of this file)."""
    d = -1 if flip else 1
    col = "#1d130e" if wood else "#101416"
    for j in range(n):
        a = x + d * j * 446 * s
        b = a + d * 430 * s
        x0, x1 = min(a, b), max(a, b)
        c.rect(x0, y - 176 * s, x1, y - 34 * s, col)
        c.rect(x0 - 4 * s, y - 198 * s, x1 + 4 * s, y - 176 * s, "#090909", r=10 * s)        # roof
        c.rect(x0 + 40 * s, y - 212 * s, x1 - 40 * s, y - 196 * s, "#0b0b0b", r=6 * s)        # clerestory
        if wood:
            for q in range(1, 22):
                px = x0 + q * (x1 - x0) / 22
                c.line([(px, y - 96 * s), (px, y - 36 * s)], "#120b08", 1.2 * s, 0.9)
        c.line([(x0, y - 100 * s), (x1, y - 100 * s)], "#090909", 2 * s)
        for t in range(11):
            wx = x0 + (26 + t * 35.5) * s
            on = K3.hash2(t, j, seed) < lit
            c.rect(wx, y - 156 * s, wx + 24 * s, y - 110 * s, WARM if on else "#070606", 0.85 if on else 1.0)
            if on:
                L.rect(wx, y - 156 * s, wx + 24 * s, y - 110 * s, WARM, 0.45)
        for wx in (44, 84, 346, 386):
            c.circle(x0 + wx * s, y - 18 * s, 19 * s, "#050506")
        c.rect(x0 + 30 * s, y - 36 * s, x0 + 100 * s, y - 28 * s, "#050506")
        c.rect(x1 - 100 * s, y - 36 * s, x1 - 30 * s, y - 28 * s, "#050506")
    return []


@prop
def semaphore(c, L, x, y, s=1.0, arm="stop", flip=False, dim=0.0, arms=1, **k):
    """A lower-quadrant semaphore signal on a mast: arm="stop" (level, red) or "clear" (dropped, green)."""
    d = -1 if flip else 1
    top = y - 420 * s
    c.rect(x - 5 * s, top, x + 5 * s, y, "#0b0b0c")                                # mast
    c.rect(x - 16 * s, y - 12 * s, x + 16 * s, y, "#0b0b0c")
    c.poly([(x - 9 * s, top), (x, top - 26 * s), (x + 9 * s, top)], "#0b0b0c")     # finial
    for j in range(7):                                                             # ladder
        ly = y - (40 + j * 50) * s
        c.line([(x - 5 * s, ly), (x - 22 * s, ly)], "#0b0b0c", 2 * s)
    c.line([(x - 22 * s, y - 20 * s), (x - 22 * s, top + 40 * s)], "#0b0b0c", 2 * s)
    out = []
    for q in range(int(arms)):                                                     # the Porter home signal had two blades
        py = top + (44 + q * 96) * s                                               # the blade's pivot
        ang = 0.0 if arm == "stop" else math.radians(60)
        ln, hw = 150 * s, 15 * s
        ca, sa = math.cos(ang), math.sin(ang)

        def pt(u, v):
            return (x + d * (u * ca - v * sa), py + (u * sa + v * ca))

        red, white = "#a02418", "#d8d2c0"
        c.poly([pt(0, -hw), pt(ln, -hw), pt(ln, hw), pt(0, hw)], red)                  # blade: red with a white band
        c.poly([pt(ln * 0.72, -hw), pt(ln * 0.82, -hw), pt(ln * 0.82, hw), pt(ln * 0.72, hw)], white)
        sx, sy = x - d * 34 * s, py + 4 * s                                            # the lamp, behind the spectacle
        c.rect(min(x, sx) - 2 * s, py - 12 * s, max(x, sx) + 2 * s, py + 14 * s, "#0b0b0c")
        col, rgb = ("#ff4a30", (1.0, 0.25, 0.18)) if arm == "stop" else ("#4aff7a", (0.3, 1.0, 0.5))
        kf = max(0.0, 1.0 - dim)
        c.circle(sx, sy, 12 * s, "#0b0b0c")
        c.circle(sx, sy, 9 * s, col, 0.95 * kf + 0.05)
        L.circle(sx, sy, 14 * s, col, 0.8 * kf)
        if kf > 0.05:
            out.append((sx, sy, rgb, 70 * s, True, 0.6 * kf))
    return out


@prop
def intertower(c, L, x, y, s=1.0, lit=1.0, **k):
    """A two-storey frame interlocking tower with a band of lit windows upstairs and an outside stair."""
    hw = 105 * s
    c.rect(x - hw, y - 300 * s, x + hw, y, "#12100d")
    for j in range(30):                                                            # clapboards
        c.line([(x - hw, y - j * 10 * s), (x + hw, y - j * 10 * s)], "#1a1612", 1.0, 0.7)
    c.poly([(x - hw - 26 * s, y - 300 * s), (x + hw + 26 * s, y - 300 * s), (x + 40 * s, y - 366 * s),
            (x - 40 * s, y - 366 * s)], "#070707")                                 # hipped roof, deep eaves
    c.rect(x + 46 * s, y - 392 * s, x + 66 * s, y - 340 * s, "#14100e")            # stove chimney
    w0, w1 = y - 270 * s, y - 196 * s                                              # the operating floor's windows
    for j in range(5):
        wx = x - hw + (10 + j * 39) * s
        c.rect(wx, w0, wx + 32 * s, w1, WARM if lit > 0 else "#070606", 0.9 if lit > 0 else 1.0)
        if lit > 0:
            L.rect(wx, w0, wx + 32 * s, w1, WARM, 0.5 * lit)
        c.line([(wx + 16 * s, w0), (wx + 16 * s, w1)], "#12100d", 2 * s)
    c.rect(x - 30 * s, y - 84 * s, x + 20 * s, y, "#070606")                       # ground-floor door
    c.rect(x + 46 * s, y - 120 * s, x + 80 * s, y - 70 * s, "#070606")             # a dark lower window
    c.line([(x + hw, y - 186 * s), (x + hw + 150 * s, y)], "#0a0908", 7 * s)       # outside stair
    c.line([(x + hw, y - 226 * s), (x + hw + 150 * s, y - 40 * s)], "#0a0908", 3 * s)
    for j in range(6):
        px = x + hw + j * 30 * s
        py = y - 186 * s + j * 37.2 * s
        c.line([(px, py), (px, py - 40 * s)], "#0a0908", 2 * s)
    return [(x, (w0 + w1) / 2, (1.0, 0.75, 0.45), 150 * s, False, 0.5 * lit)] if lit > 0 else []


@prop
def crosstrack(c, L, x, y, s=1.0, x2=900, y2=1100, w=150, w2=20, **k):
    """A second track crossing the picture at an angle: two rails on ties from (x, y) near to (x2, y2) far."""
    n = 46
    dx, dy = x2 - x, y2 - y
    ln = math.hypot(dx, dy) or 1.0
    for j in range(n):                                                             # ties, closer with distance
        f = (j / n) ** 1.7
        cx, cy = x + dx * f, y + dy * f
        hw = (w + (w2 - w) * f) * 0.78
        th = max(1.5, 16 * (1 - f) + 1.5)
        c.line([(cx - hw, cy), (cx + hw, cy)], "#15171a", th)
    for sgn in (-1, 1):
        c.poly([(x + sgn * w / 2 - 4, y), (x + sgn * w / 2 + 4, y), (x2 + sgn * w2 / 2 + 1, y2),
                (x2 + sgn * w2 / 2 - 1, y2)], "#3a3f42")
    return []


@prop
def steamcloud(c, L, x, y, s=1.0, w=520, h=260, a=0.5, seed=1, **k):
    """A soft cloud of smoke and steam drifting across the picture."""
    for j in range(14):
        fx = K3.hash2(j, seed, 1) - 0.5
        fy = K3.hash2(j, seed, 2) - 0.5
        r = (0.28 + 0.3 * K3.hash2(j, seed, 3))
        c.ellipse(x + fx * w * s, y + fy * h * s, r * w * 0.6 * s, r * h * 0.7 * s, "#7a7c82",
                  0.16 * a, blur=30 * s)
    return []
