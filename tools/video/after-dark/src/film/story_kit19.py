"""Props for the Bass Lake short (the monster of Cedar Lake, now Bass Lake, Starke County: an 1838 legend in a
Logansport paper and an 1893 newspaper story of a fishing boat smashed by something huge), added Nov. 16, 2026.
They register in story_kit3.PROPS like every prop, so a storyboard names them in "props": [{"p": "rowboat", ...}].

    rowboat      an 1890s wooden rowboat, side on, on the water at y, with n men in hats and a pair of oars.
                 rods = fishing rods out (0-2); handline=True (with rods=0): the first man holds a hand line trailing
                 astern; tow=0..1 bends the first rod toward the bow and runs its line taut into the water ahead, or
                 with rods=0 runs a line made fast at the bow taut ahead (something hooked and pulling the boat);
                 broken=True: the stern smashed open, the boat
                 low and tilted, loose planks around, nobody aboard (sink=True: tilt it stern-down, say -24, and
                 the stern goes under the surface); thrown=True: two men in the air behind the
                 stern, arms out (thrown overboard; no one shown hurt; throw = [(u, height, lean), ...] in boat
                 units, u negative toward the stern); tilt in degrees (+ raises the bow); flip mirrors it (bow left)
    serpenttail  a huge eel-like tail with no fins whipping up out of the water, with spray and foam; flip mirrors
    lakeserpent  a lake monster with humps and a raised neck (the storybook kind; not used: the 1893 story describes
                 a finless body three feet thick, so the Bass Lake short uses eelbody). humps = arches above the
                 water; head=False leaves only the humps; flip mirrors (head left)
    eelbody      the creature as the 1893 story described it, at the surface: a long finless body rolling through the
                 water from its tail end at (x, y) to a huge pointed head darting off (length, thick in px; flip runs
                 it left); pair it with serpenttail for the tail striking a boat
    swirl        rings and foam where something big just went under
    wake         a V of ripples trailing back from a point just under the surface (something swimming away);
                 length in px; flip turns it around (swimming left); head=True shows a dark dome at the point
    cedars       a shoreline of cedars (narrow, ragged cones), n of them across spread px; on water (reflect=True)
                 they get soft reflections
    springcut    a cut-away of a hill with a lake on its top and springs rising through the ground into the lake
                 bed (Bass Lake has no stream flowing in: springs and wells help fill it); height in px;
                 well=True adds a well pipe pouring into the lake
    cottages     a row of small lake cottages along a far shore at y, some windows lit (lit = share), with docks;
                 their lights reflect in the water

Nothing shows a body, an injured person, a real person's likeness, a brand or any lettering.
"""
import math

import numpy as np

import art
import story_kit3 as K3
from story_kit import W, H  # noqa: F401

prop = K3.prop
INK = "#040405"
SERP = "#0a1611"        # greenish-black
SERP_RIM = "#355241"
FOAM = "#d4dee2"


def _rng(seed):
    return np.random.default_rng(seed)


def _bez3(p0, p1, p2, p3, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def _band(c, pts, w0, w1, color, a=1.0, rim=None, rim_a=0.45, rim_w=2.0):
    """A filled band along a centre line, w0 wide at the first point tapering to w1 at the last."""
    left, right = [], []
    n = len(pts)
    for i, (px, py) in enumerate(pts):
        qx, qy = pts[min(n - 1, i + 1)] if i < n - 1 else pts[i]
        ox, oy = pts[max(0, i - 1)]
        tx, ty = qx - ox, qy - oy
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln
        w = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
        left.append((px + nx * w, py + ny * w))
        right.append((px - nx * w, py - ny * w))
    c.poly(left + right[::-1], color, a, smooth=True)
    if rim:
        c.line(left, rim, rim_w, rim_a)
    return left, right


def _ripples(c, x, y, s, n=4, spread=120, a=0.2, seed=1):
    r = _rng(seed)
    for q in range(n):
        c.ellipse(x + r.uniform(-spread, spread) * s, y + r.uniform(-2, 4) * s, r.uniform(20, 44) * s,
                  r.uniform(2.5, 4.5) * s, "#c8d4dc", a * r.uniform(0.6, 1.0), blur=2 * s)


def _spray(c, x, y, s, k=1.0, seed=4, up=220):
    r = _rng(seed)
    for _ in range(int(70 * k)):                                          # droplets
        ang = r.uniform(-2.6, -0.5)
        dist = r.uniform(10, up) * s
        c.circle(x + math.cos(ang) * dist * 1.1, y + math.sin(ang) * dist, r.uniform(1.5, 5.5) * s, FOAM,
                 r.uniform(0.25, 0.8))
    for _ in range(int(12 * k)):                                          # sheets of spray
        dx = r.uniform(-90, 90) * s
        c.poly([(x + dx - 10 * s, y), (x + dx * 1.6 + r.uniform(-20, 20) * s, y - r.uniform(60, up * 0.8) * s),
                (x + dx + 10 * s, y)], FOAM, r.uniform(0.12, 0.3), blur=3 * s)
    c.ellipse(x, y + 2 * s, 130 * s * k, 16 * s, FOAM, 0.45, blur=4 * s)  # foam at the base
    for q in range(3):
        c.ellipse(x, y + 4 * s, (160 + q * 70) * s * k, (14 + q * 5) * s, "#c8d4dc", 0.18 - q * 0.04, blur=2 * s)


# --------------------------------------------------------------------------------------------- the boat

def _seated(c, px, py, s, hat, color, arm_to=None):
    """A man sitting in a boat, seen side on from the waist up; (px, py) = where he meets the gunwale."""
    c.poly([(px - 13 * s, py + 2 * s), (px - 12 * s, py - 30 * s), (px - 6 * s, py - 40 * s), (px + 7 * s, py - 40 * s),
            (px + 13 * s, py - 30 * s), (px + 14 * s, py + 2 * s)], color, smooth=True)          # coat
    c.rect(px - 3.5 * s, py - 46 * s, px + 3.5 * s, py - 38 * s, color)                         # neck
    c.circle(px, py - 53 * s, 9.5 * s, color)                                                   # head
    if hat == "boater":
        c.ellipse(px, py - 61 * s, 15 * s, 3.2 * s, color)
        c.rect(px - 9 * s, py - 70 * s, px + 9 * s, py - 61 * s, color)
    elif hat == "derby":
        c.ellipse(px, py - 61 * s, 13.5 * s, 3.0 * s, color)
        c.ellipse(px, py - 64 * s, 9.5 * s, 8.5 * s, color)
    else:
        c.ellipse(px, py - 60 * s, 11 * s, 6 * s, color)
        c.ellipse(px + 6 * s, py - 58.5 * s, 7 * s, 2 * s, color)
    if arm_to is not None:                                                                      # arms out to a rod
        c.line([(px + 4 * s, py - 33 * s), ((px + arm_to[0]) / 2, (py - 30 * s + arm_to[1]) / 2 - 4 * s), arm_to],
               color, max(1.0, 6 * s))


@prop
def rowboat(c, L, x, y, s=1.0, n=4, rods=1, tow=0.0, broken=False, thrown=False, tilt=0.0, flip=False, seed=2,
            color=INK, throw=((-190, 130, 0.9), (-270, 60, -0.8)), sink=False, handline=False, **k):
    """An 1890s rowboat side on (see the top of this file)."""
    r = _rng(seed)
    d = -1 if flip else 1
    t = math.radians(tilt)

    def P(u, w):                                     # boat coordinates: u along it (+ to the bow), w up
        uu = u * math.cos(t) - w * math.sin(t)
        ww = u * math.sin(t) + w * math.cos(t)
        return (x + d * uu * s, y - ww * s)

    if broken:                                       # the stern smashed open, low in the water
        hull = [P(-70, 30), P(-84, 22), P(-76, 16), P(-92, 10), P(-80, 4), P(-96, -2), P(100, -2), P(128, 10),
                P(140, 40), P(60, 33), P(0, 31)]
        if sink:                                     # going down: whatever is below the waterline is hidden
            hull = [(hx, min(hy, y + 2 * s)) for hx, hy in hull]
            for q in range(3):
                c.ellipse(x - d * 30 * s, y + 3 * s, (150 + q * 50) * s, (6 + q * 3) * s, FOAM, 0.3 - q * 0.08,
                          blur=2 * s)
        c.poly(hull, color)
        c.line([P(-66, 30), P(0, 31), P(60, 33), P(138, 40)], "#7a8692", max(0.8, 2.4 * s), 0.6)   # moonlit gunwale
        c.line([P(-92, 10), P(100, 0)], "#5a6470", max(0.8, 1.6 * s), 0.35)
        for j in range(5):                                             # splintered planks at the break
            u0 = -70 - j * 5
            c.line([P(u0, 28 - j * 6), P(u0 - r.uniform(10, 26), 30 - j * 6 + r.uniform(-6, 6))], color,
                   max(1.0, 3 * s))
        for j in range(7):                                             # loose planks and bits on the water
            px = x - d * r.uniform(150, 330) * s
            py = y + r.uniform(-6, 10) * s
            ln = r.uniform(26, 60) * s
            a = r.uniform(-0.35, 0.35)
            c.line([(px - math.cos(a) * ln / 2, py - math.sin(a) * ln / 2),
                    (px + math.cos(a) * ln / 2, py + math.sin(a) * ln / 2)], "#0b0b0b", max(1.2, 5 * s))
            c.ellipse(px, py + 3 * s, ln * 0.6, 3 * s, "#c8d4dc", 0.15, blur=2 * s)
        c.line([P(10, 33), P(-60, 6), P(-150, -6)], color, max(1.0, 4 * s))   # an oar adrift
        c.ellipse(*P(-150, -6), 16 * s, 4 * s, color)
        _ripples(c, x, y, s, n=7, spread=200, a=0.22, seed=seed)
        return []

    hull = [P(-130, 36), P(-128, 4), P(-110, -2), P(100, -2), P(128, 12), P(142, 46), P(110, 40), P(40, 35),
            P(-40, 34), P(-100, 36)]
    c.poly(hull, color, smooth=False)
    c.line([P(-128, 36), P(-40, 34), P(40, 35), P(110, 40), P(140, 46)], "#2c2a26", max(0.8, 2.0 * s), 0.75)
    c.line([P(-120, 20), P(120, 22)], "#1a1918", max(0.8, 1.4 * s), 0.6)          # a plank seam
    # oars, resting in the oarlocks and dipping into the water
    ox, oy = P(-8, 38)
    c.line([(ox, oy), (ox - d * 30 * s, oy - 10 * s)], color, max(1.0, 4 * s))
    c.line([(ox, oy), (x - d * 120 * s, y + 4 * s)], color, max(1.0, 4 * s))
    c.ellipse(x - d * 128 * s, y + 4 * s, 18 * s, 4 * s, color)
    # the men
    hats = ["boater", "derby", "cap", "boater", "derby"]
    slots = [-95, -42, 18, 72, 112]
    n = max(0, min(int(n), 4 if not thrown else 2))
    rod_hands = []
    for j in range(n):
        u = slots[j] if n > 2 else (slots[1 + j * 2] if n == 2 else slots[2])
        px, py = P(u, 36)
        hand = None
        if j < int(rods):
            hand = (px + d * 26 * s, py - 28 * s)
            rod_hands.append(hand)
        _seated(c, px, py, s, hats[(j + seed) % len(hats)], color, arm_to=hand)
    if handline and n > 0 and not rod_hands:                              # a hand line trailing astern (trolling)
        u0 = slots[0] if n > 2 else (slots[1] if n == 2 else slots[2])
        px, py = P(u0, 36)
        hx, hy = px - d * 14 * s, py - 24 * s
        c.line([(px - d * 2 * s, py - 32 * s), (hx, hy)], color, max(1.0, 6 * s))
        c.line([(hx, hy), (x - d * 330 * s, y + 5 * s)], "#d8dcd8", max(0.6, 1.1 * s), 0.5)
        c.ellipse(x - d * 330 * s, y + 5 * s, 14 * s, 3 * s, "#c8d4dc", 0.25, blur=2 * s)
    if tow > 0 and not rod_hands:                                      # the line made fast at the bow, taut ahead
        bx, by = P(138, 42)
        ex = x + d * (300 + 160 * tow) * s
        c.line([(bx, by), (ex, y + 6 * s)], "#d8dcd8", max(0.8, 1.6 * s), 0.75)
        for q in range(3):
            c.ellipse(ex, y + 6 * s, (14 + q * 16) * s, (3 + q) * s, "#c8d4dc", 0.3 - q * 0.08, blur=2 * s)
    # fishing rods
    for j, (hx, hy) in enumerate(rod_hands):
        if j == 0 and tow > 0:                                         # bent hard toward the bow, line taut
            tipx, tipy = hx + d * (120 - 30 * tow) * s, hy - (60 - 40 * tow) * s
            ctrl = (hx + d * 80 * s, hy - 95 * s)
            pts = []
            for q in range(13):
                tt = q / 12
                pts.append(((1 - tt) ** 2 * hx + 2 * (1 - tt) * tt * ctrl[0] + tt * tt * tipx,
                            (1 - tt) ** 2 * hy + 2 * (1 - tt) * tt * ctrl[1] + tt * tt * tipy))
            c.line(pts, color, max(1.0, 3 * s))
            ex = x + d * (300 + 160 * tow) * s
            c.line([(tipx, tipy), (ex, y + 6 * s)], "#d8dcd8", max(0.8, 1.4 * s), 0.7)
            for q in range(3):                                         # where the line cuts the water
                c.ellipse(ex, y + 6 * s, (14 + q * 16) * s, (3 + q) * s, "#c8d4dc", 0.3 - q * 0.08, blur=2 * s)
        else:
            tipx, tipy = hx + d * 70 * s, hy - 140 * s
            c.line([(hx, hy), (tipx, tipy)], color, max(1.0, 2.6 * s))
            c.line([(tipx, tipy), (tipx + d * 26 * s, y + 4 * s)], "#d8dcd8", max(0.6, 1.0 * s), 0.45)
    if tow > 0:                                                        # pulled through the water: a bow wave
        bx, by = P(140, 0)
        for q in range(5):
            c.line([(bx + d * 6 * s, by + 2 * s), (bx - d * (60 + q * 55) * s, by + (8 + q * 7) * s)], FOAM,
                   max(0.8, 2.2 * s), 0.35 - q * 0.05)
        for q in range(6):
            c.ellipse(x - d * (170 + q * 60) * s, y + 5 * s, (40 + q * 8) * s, 3 * s, "#c8d4dc", 0.2, blur=2 * s)
    if thrown:                                                          # two men in the air behind the stern
        for j, (du, dh, ln) in enumerate(throw):
            fx, fy = x + d * du * s, y - dh * s
            art.figure(c, fx, fy, 110 * s, color=color, hat="brim", lean=ln,
                       arms=((115, 70), (-120, -60)), legs=(30, -22))
    _ripples(c, x, y, s, n=5, spread=150, a=0.22, seed=seed)
    return []


# ------------------------------------------------------------------------------------------ the monster

@prop
def serpenttail(c, L, x, y, s=1.0, flip=False, splash=1.0, color=SERP, **k):
    """A huge finless tail whipping up out of the water (see the top of this file)."""
    d = -1 if flip else 1
    p0, p1, p2, p3 = (0, 0), (40, -320), (-30, -520), (-230, -470)
    pts = [_bez3(p0, p1, p2, p3, q / 30) for q in range(31)]
    pts = [(x + d * px * s, y + py * s) for px, py in pts]
    _band(c, pts, 130 * s, 10 * s, color, rim=SERP_RIM, rim_w=max(1.0, 3 * s))
    if splash:
        _spray(c, x, y, s, k=splash, seed=7)
        _spray(c, x - d * 230 * s, y - 470 * s + 40 * s, s * 0.5, k=0.4, seed=8, up=120)   # water off the tip
    return []


@prop
def lakeserpent(c, L, x, y, s=1.0, humps=3, head=True, flip=False, color=SERP, seed=5, **k):
    """The monster as the 1893 story described it (see the top of this file)."""
    d = -1 if flip else 1
    hs = [(0, 78, 70), (-175, 62, 60), (-330, 46, 48), (-460, 32, 38)][:max(0, int(humps))]
    for u, h, w in hs:                                                  # loops of the body above the water
        cx = x + d * u * s
        arch = [(cx - w * s, y + 4 * s)]
        for q in range(1, 12):
            tt = q / 12
            arch.append((cx + (tt * 2 - 1) * w * s, y - math.sin(tt * math.pi) * h * s))
        arch.append((cx + w * s, y + 4 * s))
        c.poly(arch, color, smooth=True)
        c.line(arch[1:-1], SERP_RIM, max(1.0, 2.4 * s), 0.5)
        for q in range(2):
            c.ellipse(cx, y + 4 * s, (w + 24 + q * 28) * s, (5 + q * 3) * s, "#c8d4dc", 0.25 - q * 0.08, blur=2 * s)
    if hs:                                                              # a wake behind the last loop
        lx = x + d * (hs[-1][0] - hs[-1][2]) * s
        for q in range(4):
            c.line([(lx, y + 3 * s), (lx - d * (90 + q * 70) * s, y + (6 + q * 6) * s)], FOAM, max(0.8, 2 * s),
                   0.3 - q * 0.06)
    if head:                                                            # the neck rising, a huge pointed head
        nb = (x + d * 110 * s, y + 4 * s)
        neck = [_bez3(nb, (nb[0] + d * 20 * s, y - 120 * s), (nb[0] + d * 60 * s, y - 190 * s),
                      (nb[0] + d * 130 * s, y - 205 * s), q / 20) for q in range(21)]
        _band(c, neck, 66 * s, 50 * s, color, rim=SERP_RIM, rim_w=max(1.0, 2.6 * s))
        hx, hy = neck[-1]
        skull = [(hx - d * 34 * s, hy - 40 * s), (hx + d * 30 * s, hy - 52 * s), (hx + d * 92 * s, hy - 34 * s),
                 (hx + d * 170 * s, hy + 4 * s), (hx + d * 96 * s, hy + 26 * s), (hx + d * 30 * s, hy + 36 * s),
                 (hx - d * 32 * s, hy + 30 * s)]
        c.poly(skull, color, smooth=True)
        c.line([(hx + d * 18 * s, hy + 12 * s), (hx + d * 96 * s, hy + 11 * s), (hx + d * 160 * s, hy + 5 * s)],
               SERP_RIM, max(1.0, 2.0 * s), 0.55)                          # the line of the jaw
        c.line(skull[:4], SERP_RIM, max(1.0, 2.4 * s), 0.5)
        for q in range(3):
            c.ellipse(nb[0], y + 5 * s, (60 + q * 30) * s, (5 + q * 3) * s, "#c8d4dc", 0.28 - q * 0.08, blur=2 * s)
        r = _rng(seed)
        for _ in range(16):                                              # water running off the head
            c.circle(hx + d * r.uniform(-20, 160) * s, hy + r.uniform(30, 180) * s, r.uniform(1.2, 3.2) * s, FOAM,
                     r.uniform(0.2, 0.6))
    return []


@prop
def swirl(c, L, x, y, s=1.0, rings=5, seed=6, **k):
    """Rings and foam where something big just went under."""
    r = _rng(seed)
    c.ellipse(x, y + 2 * s, 60 * s, 8 * s, "#020405", 0.55, blur=3 * s)
    for q in range(int(rings)):
        c.ellipse(x, y + 2 * s, (80 + q * 64) * s, (8 + q * 4.5) * s, "#c8d4dc", 0.0, blur=0)
        ring = []
        for j in range(49):
            a = j / 48 * math.tau
            ring.append((x + math.cos(a) * (80 + q * 64) * s, y + 2 * s + math.sin(a) * (8 + q * 4.5) * s))
        c.line(ring, "#c8d4dc", max(0.8, (2.4 - q * 0.3) * s), max(0.05, 0.32 - q * 0.055), blur=1 * s)
    for _ in range(14):
        a = r.uniform(0, math.tau)
        rr = r.uniform(20, 90) * s
        c.ellipse(x + math.cos(a) * rr, y + math.sin(a) * rr * 0.12, r.uniform(4, 10) * s, r.uniform(1.2, 2.5) * s,
                  FOAM, r.uniform(0.15, 0.35), blur=1 * s)
    return []


@prop
def wake(c, L, x, y, s=1.0, length=520, flip=False, head=True, spread=0.32, color=SERP, **k):
    """A V of ripples trailing back from a point just under the surface (see the top of this file)."""
    d = -1 if flip else 1
    if head:
        c.ellipse(x, y - 4 * s, 46 * s, 14 * s, color)
        c.ellipse(x - d * 8 * s, y - 10 * s, 24 * s, 3.5 * s, SERP_RIM, 0.6, blur=1 * s)
        for q in range(3):
            c.ellipse(x + d * 10 * s, y + 2 * s, (52 + q * 22) * s, (5 + q * 2) * s, "#c8d4dc", 0.4 - q * 0.12,
                      blur=1.5 * s)
    steps = 14
    for side in (-1, 1):
        for q in range(1, steps):
            tt = q / steps
            px = x - d * length * tt * s
            py = y + side * length * spread * tt * s * 0.18 + 3 * s
            c.ellipse(px, py, (18 + 34 * tt) * s, (2.4 + 2.4 * tt) * s, "#c8d4dc", max(0.03, 0.42 * (1 - tt)), blur=2 * s)
    for q in range(1, 8):                                                # the trough behind it
        tt = q / 8
        c.ellipse(x - d * length * 0.6 * tt * s, y + 4 * s, (20 + 20 * tt) * s, 2.5 * s, "#020405", 0.25 * (1 - tt),
                  blur=2 * s)
    return []


@prop
def eelbody(c, L, x, y, s=1.0, length=600, thick=54, flip=False, head=True, rise=0.2, seed=7, color=SERP, **k):
    """The 1893 story's creature at the surface: a long finless body (about three feet thick to forty long) rolling
    through the water from its tail end at (x, y) to a huge pointed head at the far end, darting off; flip runs it
    left. Pair it with serpenttail at (x, y) for the tail striking a boat."""
    d = -1 if flip else 1
    n = 48
    pts = []
    for i in range(n + 1):
        tt = i / n
        pts.append((x + d * length * tt * s, y - rise * length * tt * s * 0.25 + math.sin(tt * math.pi * 3) * 5 * s))
    for a0, b0 in ((0.04, 0.27), (0.35, 0.6), (0.68, 0.9)):               # loops of the body above the surface
        sub = pts[int(a0 * n):int(b0 * n) + 1]
        th = thick * s
        top = []
        for j, (px, py) in enumerate(sub):
            tt = j / max(1, len(sub) - 1)
            top.append((px, py - (math.sin(tt * math.pi) * 0.75 + 0.12) * th))
        c.poly([(sub[0][0], sub[0][1] + 3 * s)] + top + [(sub[-1][0], sub[-1][1] + 3 * s)], color, smooth=True)
        c.line(top, SERP_RIM, max(1.0, 2.2 * s), 0.5)
        mx = (sub[0][0] + sub[-1][0]) / 2
        for q in range(2):
            c.ellipse(mx, sub[0][1] + 4 * s, abs(sub[-1][0] - sub[0][0]) * (0.62 + q * 0.2), (4 + q * 3) * s,
                      "#c8d4dc", 0.22 - q * 0.08, blur=2 * s)
    if head:                                                             # a huge pointed head, darting off
        hx, hy = pts[-1]
        skull = [(hx - d * 46 * s, hy + 4 * s), (hx - d * 36 * s, hy - 38 * s), (hx + d * 24 * s, hy - 58 * s),
                 (hx + d * 86 * s, hy - 44 * s), (hx + d * 176 * s, hy - 12 * s), (hx + d * 84 * s, hy + 10 * s),
                 (hx + d * 8 * s, hy + 7 * s)]
        c.poly(skull, color, smooth=True)
        c.line([(hx - d * 26 * s, hy - 6 * s), (hx + d * 84 * s, hy - 3 * s), (hx + d * 166 * s, hy - 11 * s)],
               SERP_RIM, max(1.0, 2.0 * s), 0.55)                          # the line of the jaw
        c.line(skull[1:5], SERP_RIM, max(1.0, 2.2 * s), 0.5)
        for q in range(3):
            c.ellipse(hx + d * 30 * s, hy + 5 * s, (90 + q * 34) * s, (5 + q * 3) * s, "#c8d4dc", 0.3 - q * 0.08,
                      blur=2 * s)
        _spray(c, hx - d * 30 * s, hy + 4 * s, s * 0.45, k=0.45, seed=seed, up=90)
    return []


# ------------------------------------------------------------------------------------------- the shore

def _cedar(c, x, y, h, w, r, color, a=1.0):
    pts = [(x - w * 0.5, y)]
    n = 9
    for q in range(1, n):
        tt = q / n
        pts.append((x - w * 0.5 * (1 - tt) ** 0.9 - r.uniform(0, 0.12) * w, y - h * tt))
    pts.append((x + r.uniform(-0.04, 0.04) * w, y - h - r.uniform(0, 0.06) * h))
    for q in range(n - 1, 0, -1):
        tt = q / n
        pts.append((x + w * 0.5 * (1 - tt) ** 0.9 + r.uniform(0, 0.12) * w, y - h * tt))
    pts.append((x + w * 0.5, y))
    c.poly(pts, color, a, smooth=False)


@prop
def cedars(c, L, x, y, s=1.0, n=8, spread=1000, seed=5, reflect=True, color="#040706", **k):
    """A shoreline of eastern red cedars (see the top of this file)."""
    r = _rng(seed)
    c.rect(x - spread * s * 0.6, y - 14 * s, x + spread * s * 0.6, y + 2 * s, color)        # the low bank
    trees = []
    for j in range(int(n)):
        tx = x - spread * s / 2 + (j + r.uniform(0.1, 0.9)) * spread * s / n
        th = r.uniform(140, 270) * s
        tw = th * r.uniform(0.26, 0.36)
        trees.append((tx, th, tw, int(r.integers(0, 1 << 30))))
    for tx, th, tw, sd in trees:
        _cedar(c, tx, y - 8 * s, th, tw, _rng(sd), color)
    if reflect:
        for tx, th, tw, sd in trees:
            rr = _rng(sd)
            pts = [(tx - tw * 0.5, y + 2 * s), (tx, y + th * 0.55), (tx + tw * 0.5, y + 2 * s)]
            c.poly(pts, color, 0.25, blur=6 * s)
            rr.random()
    return []


@prop
def springcut(c, L, x, y, s=1.0, height=300, seed=9, **k):
    """A cut-away of a low hill with a lake on top, fed by springs from below (see the top of this file)."""
    r = _rng(seed)
    half, top, edge = 520 * s, height * s, min(120.0, height * 0.45) * s
    body = [(x - half, y), (x - half, y - edge), (x - 380 * s, y - edge - 40 * s), (x - 290 * s, y - top + 20 * s),
            (x - 240 * s, y - top), (x + 240 * s, y - top), (x + 290 * s, y - top + 20 * s),
            (x + 380 * s, y - edge - 40 * s), (x + half, y - edge), (x + half, y)]
    c.poly(body, "#1c1610", smooth=True)
    for q in range(5):                                                   # layers of sand and clay
        yy = y - edge + 10 * s + q * 26 * s
        pts = [(x - half + 8 * s, yy)]
        for j in range(1, 20):
            pts.append((x - half + j * half * 2 / 20, yy + math.sin(j * 0.8 + q) * 6 * s))
        c.line(pts, ["#2c2218", "#241c14", "#30261b"][q % 3], max(1.0, 9 * s), 0.55)
    lw, ld = 230 * s, 70 * s                                             # the lake in a shallow bowl on top
    bowl = [(x - lw, y - top)]
    for q in range(1, 16):
        tt = q / 16
        bowl.append((x - lw + tt * 2 * lw, y - top + math.sin(tt * math.pi) * ld))
    bowl.append((x + lw, y - top))
    c.poly(bowl, "#18303f", smooth=True)
    c.line([(x - lw, y - top), (x + lw, y - top)], "#9fb6c4", max(1.0, 3 * s), 0.7)
    for q in range(4):
        c.ellipse(x + r.uniform(-180, 180) * s, y - top + 2 * s, r.uniform(20, 50) * s, 2.5 * s, "#c8d4dc", 0.3,
                  blur=1.5 * s)
    for side in (-1, 1):                                                 # the ground falls away from the lake
        for q in range(3):
            ax = x + side * (300 + q * 70) * s
            c.line([(ax, y - top + (30 + q * 40) * s), (ax + side * 40 * s, y - top + (64 + q * 40) * s)],
                   "#6a5a48", max(1.0, 3 * s), 0.55)
            c.poly([(ax + side * 40 * s, y - top + (64 + q * 40) * s),
                    (ax + side * 28 * s, y - top + (52 + q * 40) * s),
                    (ax + side * 30 * s, y - top + (68 + q * 40) * s)], "#6a5a48", 0.55)
    for j, sx in enumerate((-150, -50, 60, 160)):                        # springs rising through the ground
        pts = []
        base = y - 12 * s
        for q in range(16):
            tt = q / 15
            yy = base - tt * (top - ld * 0.8 - 12 * s + math.sin((sx + 200) / 400 * math.pi) * ld * 0.2)
            pts.append((x + sx * s + math.sin(tt * 7 + j) * 14 * s, yy))
        c.line(pts, "#2f6a86", max(1.0, 7 * s), 0.35, blur=4 * s)
        c.line(pts, "#4f8aa6", max(1.0, 3 * s), 0.7)
        for q in range(6):
            tt = r.uniform(0.1, 1.0)
            px, py = pts[int(tt * 15)]
            c.circle(px + r.uniform(-6, 6) * s, py, r.uniform(2, 4.5) * s, "#9cc8de", 0.55)
        for q in range(5):                                               # bubbles rising in the lake
            c.circle(x + sx * s + r.uniform(-12, 12) * s, y - top + r.uniform(8, ld * 0.8), r.uniform(2, 4) * s,
                     "#b0d4e4", 0.5)
    for tx in (-420, -340, 330, 410, 470):                                # cedars on the shoulders of the hill
        hh = r.uniform(60, 110) * s
        yy = y - edge - (40 if abs(tx) < 400 else 10) * s + 6 * s
        _cedar(c, x + tx * s, yy, hh, hh * 0.3, r, "#050806")
    if k.get("well"):                                                     # a well pipe pouring water into the lake
        px = x + 262 * s
        c.line([(px, y - 14 * s), (px, y - top - 26 * s), (x + lw - 30 * s, y - top - 26 * s)], "#3a3e42",
               max(1.0, 9 * s))
        c.line([(x + lw - 30 * s, y - top - 22 * s), (x + lw - 44 * s, y - top + 2 * s)], "#9cc8de", max(1.0, 5 * s), 0.7)
        for q in range(4):
            c.circle(px + r.uniform(-3, 3) * s, y - (40 + q * 50) * s, 3 * s, "#9cc8de", 0.6)
    c.line(body[1:-1], "#5a4a3a", max(1.0, 2.5 * s), 0.45)
    c.line([(x - half, y - edge), (x - half, y), (x + half, y), (x + half, y - edge)], "#5a4a3a", max(1.0, 2 * s), 0.6)
    return []


@prop
def cottages(c, L, x, y, s=1.0, n=7, spread=1000, lit=0.6, seed=3, docks=True, color="#060708", **k):
    """Small lake cottages along a far shore (see the top of this file)."""
    r = _rng(seed)
    c.rect(x - spread * s * 0.6, y - 10 * s, x + spread * s * 0.6, y + 2 * s, color)
    spots = []
    for j in range(int(n)):
        cx = x - spread * s / 2 + (j + r.uniform(0.15, 0.85)) * spread * s / n
        cw = r.uniform(50, 80) * s
        ch = r.uniform(36, 52) * s
        base = y - 8 * s
        c.rect(cx - cw / 2, base - ch, cx + cw / 2, base, color)
        c.poly([(cx - cw / 2 - 6 * s, base - ch), (cx, base - ch - cw * 0.42), (cx + cw / 2 + 6 * s, base - ch)], color)
        if r.random() < lit:
            wx = cx + r.uniform(-cw * 0.25, cw * 0.25)
            wy = base - ch * 0.55
            c.rect(wx - 6 * s, wy - 6 * s, wx + 6 * s, wy + 6 * s, "#e8b060", 0.95)
            spots.append((wx, wy, (1.0, 0.7, 0.35), 16 * s, False))
            for q in range(4):                                           # the light on the water
                c.rect(wx - 3 * s, y + (6 + q * 12) * s, wx + 3 * s, y + (12 + q * 12) * s, "#e8b060", 0.22 - q * 0.04)
        if docks and r.random() < 0.5:
            c.line([(cx + cw * 0.3, y - 2 * s), (cx + cw * 0.3 + 30 * s, y + 26 * s)], color, max(1.0, 4 * s))
    return spots
