"""Story illustrations for La Porte After Dark (added Nov. 12, 2026, when Scoop asked for pictures that show the
story instead of the same backdrops: "we need to illustrate the stories", "dont keep using the same ones").

Each scene shows what the narrator is describing at that moment. They register themselves in story_kit.KINDS:

    village    a lakeside village at dusk in late summer: a log chapel with a cross, cabins, trees in leaf
    march      people leaving on a dirt track: covered wagons, riders and a line of walkers, all small and far off
               fire=True  a glow and smoke on the horizon behind them   far=True  a long thin line across open prairie
               markers=True  no people: small wooden markers beside the empty track at night
    monument   a statue on a tall granite pedestal in a small park, with a boulder marker by the road
    manor      a 2 1/2-storey maroon-brick English manor with stone trim, gable dormers and tall chimneys
               lit=[0/1...]  windows that glow   dim=True  the lit windows go dark one by one   dawn=True  morning sky
    carworks   a railroad car works: long brick shops, smokestacks and a row of new wooden boxcars in the yard
    hall       inside a Gilded Age house: a wide staircase, a chandelier, a tall window; no one is shown
    cpcourt    a red-brick courthouse with a tall central clock tower and a smaller tower at each end, in the middle
               of a square   car=True  a 1920s touring car at the curb   dawn=True  morning sky
    jpoffice   a small-town office across from the square: a lit window, a hanging sign (sign="..."), a 1920s car

People are small anonymous silhouettes only. Nothing shows a body, a real person's likeness or a brand.
"""
import math

import numpy as np

import art
import story_kit as K
from story_kit import Shot, W, H, WARM, hash2, masonry, put_tex
from core import add_spot, Canvas, poly_path, smooth_path, paint, Fog
from reel_haunts import cv, comp
from reel_frank import flick

DUSK = [(0.0, "#05080f"), (0.3, "#10182a"), (0.5, "#2a2a3c"), (0.6, "#5a3a34"), (0.66, "#8a5234"), (1.0, "#3a2a24")]
BLUE = [(0.0, "#03060c"), (0.35, "#0a1626"), (0.55, "#17304a"), (0.64, "#2c4a62"), (1.0, "#22384a")]
DAWN = [(0.0, "#0c1524"), (0.3, "#22344e"), (0.5, "#5a5a70"), (0.6, "#b07a5c"), (0.66, "#d89a64"), (1.0, "#4a3a30")]
NIGHT = [(0.0, "#020408"), (0.4, "#07101c"), (0.62, "#0f2030"), (1.0, "#14242e")]


def sky(stops, seed, moon=None, stars=260, clouds=0.3):
    return art.sky(W, H, stops=stops, moon=moon, stars=stars, clouds=clouds, seed=seed, cloud_band=(0.0, 0.5),
                   star_max_y=0.45, moon_glow=0.5)


def leafy(c, x, y, h, seed=0, color="#060b09", rim="#1c2a22"):
    """A tree in full leaf: a trunk and a rounded crown built from overlapping blobs."""
    r = np.random.default_rng(seed)
    tw = h * 0.035
    c.poly([(x - tw, y), (x - tw * 0.6, y - h * 0.45), (x + tw * 0.6, y - h * 0.45), (x + tw, y)], color)
    cx, cy, R = x, y - h * 0.68, h * 0.3
    for k in range(16):
        a = r.uniform(0, 2 * math.pi)
        d = r.uniform(0, R * 0.75)
        rr = r.uniform(R * 0.32, R * 0.6)
        bx, by = cx + math.cos(a) * d * 1.15, cy + math.sin(a) * d * 0.9
        c.circle(bx - 3, by - 3, rr, rim, 0.55)
        c.circle(bx, by, rr, color)


def ground(c, y, color="#070908", grass="#040605", seed=0, n=380):
    c.poly([(-20, y), (W + 20, y), (W + 20, H), (-20, H)], color)
    art.grass(c, H - 330, 0, W, grass, n=n, hmin=12, hmax=60, seed=seed)


def wagon(c, x, y, s=1.0, color="#050607", cover="#3a3a36"):
    """A covered wagon from the side, facing right. (x, y) = ground under its middle."""
    c.rect(x - 70 * s, y - 62 * s, x + 70 * s, y - 34 * s, color)
    c.c.drawPath(smooth_path([(x - 72 * s, y - 60 * s), (x - 66 * s, y - 118 * s), (x, y - 132 * s),
                              (x + 66 * s, y - 118 * s), (x + 72 * s, y - 60 * s)], True, k=0.14), paint(cover))
    for hx in (-44, -15, 15, 44):
        c.line([(x + hx * s, y - 62 * s), (x + hx * s, y - 126 * s)], "#2a2a27", 1.6 * s, 0.6)
    for wx, wr in ((-44, 26), (46, 30)):
        c.circle(x + wx * s, y - wr * s, wr * s, color)
        c.circle(x + wx * s, y - wr * s, wr * s * 0.72, "#15181a")
        for k in range(6):
            a = k * math.pi / 3
            c.line([(x + wx * s, y - wr * s), (x + wx * s + math.cos(a) * wr * s, y - wr * s + math.sin(a) * wr * s)],
                   color, 2.2 * s)
    horse(c, x + 150 * s, y, s * 0.95, color)
    c.line([(x + 70 * s, y - 48 * s), (x + 120 * s, y - 62 * s)], color, 2.4 * s)


def horse(c, x, y, s=1.0, color="#050607", rider=False):
    """A horse from the side, facing right. (x, y) = ground under its middle."""
    c.ellipse(x, y - 70 * s, 46 * s, 22 * s, color)
    c.poly([(x + 30 * s, y - 84 * s), (x + 58 * s, y - 122 * s), (x + 78 * s, y - 112 * s), (x + 50 * s, y - 62 * s)], color)
    c.poly([(x + 54 * s, y - 124 * s), (x + 92 * s, y - 104 * s), (x + 88 * s, y - 92 * s), (x + 62 * s, y - 104 * s)], color)
    for lx, lean in ((-34, -6), (-22, 5), (24, -5), (36, 7)):
        c.line([(x + lx * s, y - 62 * s), (x + (lx + lean) * s, y)], color, 6.5 * s)
    c.line([(x - 44 * s, y - 78 * s), (x - 62 * s, y - 36 * s)], color, 4 * s)
    if rider:
        art.figure(c, x - 2 * s, y - 58 * s, 92 * s, color=color, hat="brim", legs=(14, 14))


def walkers(c, x0, x1, y, h, n, seed=0, color="#050607", dy=0.0):
    """A line of small walking silhouettes between x0 and x1 (adults, a few children), feet at y (+dy per step)."""
    r = np.random.default_rng(seed)
    for k in range(n):
        x = x0 + (x1 - x0) * (k + r.uniform(-0.25, 0.25)) / max(1, n - 1)
        child = r.uniform() < 0.3
        hh = h * (0.62 if child else r.uniform(0.9, 1.05))
        st = r.uniform(3, 9)
        art.figure(c, x, y + dy * k, hh, color=color, child=child, dress=r.uniform() < 0.45, legs=(st, -st),
                   arms=((6, 3), (-6, -3)), lean=0.25)


# --------------------------------------------------------------------------------------------- 1838

class Village(Shot):
    """A lakeside village at dusk in late summer: a log chapel with a cross, cabins and trees in leaf."""
    focus = (560, 1000)
    fog_d = 0.12
    fog_color = "#b09078"

    def __init__(self, p=None):
        super().__init__(p)
        img = sky(DUSK, 801 + self.seed, stars=120, clouds=0.35)
        c = cv()
        art.hills(img, 1010, 26, 520, "#0b1210", 802 + self.seed, rim="#6a4a36", rim_w=3, rim_a=0.4)
        c.rect(-20, 1040, W + 20, 1190, "#2a2c38")                                    # the lake, holding the sky
        for k in range(26):
            yy = 1050 + k * 5.4
            c.line([(40 + hash2(k, 1, self.seed) * 700, yy), (240 + hash2(k, 2, self.seed) * 800, yy)], "#a06a48",
                   1.6, 0.22)
        c.poly([(-20, 1170), (300, 1150), (700, 1168), (W + 20, 1140), (W + 20, H), (-20, H)], "#080a09")
        lights = cv()
        # the log chapel
        x, y = 560, 1180
        c.rect(x - 150, y - 150, x + 150, y, "#0b0908")
        for k in range(8):
            c.line([(x - 150, y - 18 - k * 18), (x + 150, y - 18 - k * 18)], "#2a1c12", 2, 0.8)
        c.poly([(x - 170, y - 146), (x, y - 268), (x + 170, y - 146)], "#080706")
        c.line([(x - 170, y - 146), (x, y - 268), (x + 170, y - 146)], "#6a4a36", 2.5, 0.5)
        c.rect(x - 5, y - 330, x + 5, y - 262, "#070605")
        c.rect(x - 22, y - 312, x + 22, y - 302, "#070605")
        c.rect(x - 26, y - 92, x + 26, y, "#050404")
        for wx in (x - 104, x + 76):
            c.rect(wx, y - 110, wx + 30, y - 56, "#050404")
            lights.rect(wx, y - 110, wx + 30, y - 56, WARM, 0.55)
        # cabins
        for cx_, s, lit in ((170, 0.8, 1), (900, 0.9, 1), (330, 0.55, 0), (790, 0.5, 0)):
            cy = 1182 - (1 - s) * 30
            c.rect(cx_ - 90 * s, cy - 90 * s, cx_ + 90 * s, cy, "#0a0807")
            c.poly([(cx_ - 104 * s, cy - 88 * s), (cx_, cy - 156 * s), (cx_ + 104 * s, cy - 88 * s)], "#070605")
            c.rect(cx_ + 40 * s, cy - 176 * s, cx_ + 62 * s, cy - 120 * s, "#070605")
            if lit:
                c.rect(cx_ - 50 * s, cy - 62 * s, cx_ - 22 * s, cy - 30 * s, "#050404")
                lights.rect(cx_ - 50 * s, cy - 62 * s, cx_ - 22 * s, cy - 30 * s, WARM, 0.5)
        comp(img, c.rgba())
        d = cv()
        leafy(d, 60, 1260, 620, 811 + self.seed)
        leafy(d, 1030, 1270, 700, 812 + self.seed)
        leafy(d, 420, 1190, 300, 813 + self.seed)
        leafy(d, 720, 1186, 260, 814 + self.seed)
        ground(d, 1250, seed=41 + self.seed)
        d.poly([(480, 1250), (640, 1250), (860, H), (260, H)], "#15120f", 0.9)        # the path to the chapel
        comp(img, d.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]


class March(Shot):
    """People leaving on foot and by wagon, seen against the evening sky on a low ridge: wagons, riders and a line
    of walkers. fire=True: a glow and smoke on the horizon behind them. far=True: a long thin line, much farther off.
    markers=True: no people; small wooden markers on the empty ridge at night."""
    focus = (560, 1020)
    fog_d = 0.1
    fog_color = "#a08a78"

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        self.fire = bool(p.get("fire"))
        far = bool(p.get("far"))
        markers = bool(p.get("markers"))
        if markers:
            img = sky(NIGHT, 821 + self.seed, moon=(800, 420, 54), stars=420, clouds=0.25)
        else:
            img = sky(DUSK, 821 + self.seed, stars=60, clouds=0.4)
        hz = 1150
        c = cv()
        col = "#050606"
        # the ridge they cross: a long low rise, dark against the sky
        ridge = [(-20, hz + 30), (200, hz + 6), (520, hz - 8), (820, hz + 2), (W + 20, hz - 14), (W + 20, H), (-20, H)]
        c.poly(ridge, col)

        def gy(x):
            pts = ridge[:5]
            for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                if xa <= x <= xb:
                    return ya + (yb - ya) * (x - xa) / (xb - xa)
            return hz
        if markers:
            for mx, s in ((300, 1.0), (430, 0.8), (620, 1.1), (760, 0.7)):
                my = gy(mx) + 4
                c.rect(mx - 4 * s, my - 84 * s, mx + 4 * s, my, col)
                c.rect(mx - 24 * s, my - 64 * s, mx + 24 * s, my - 55 * s, col)
            leafy(c, 960, gy(960) + 20, 520, 836 + self.seed, color=col, rim="#142022")
        elif far:
            for k, x in enumerate(range(60, 1060, 150)):
                if k % 3 == 1:
                    wagon(c, x, gy(x) + 3, 0.42, color=col, cover="#1c1c1a")
                else:
                    walkers(c, x - 50, x + 60, gy(x) + 3, 62, 6, seed=840 + k + self.seed, color=col)
            horse(c, 1010, gy(1010) + 3, 0.42, col, rider=True)
        else:
            horse(c, 120, gy(120) + 4, 0.95, col, rider=True)
            walkers(c, 230, 470, gy(350) + 6, 150, 7, seed=845 + self.seed, color=col)
            wagon(c, 620, gy(620) + 4, 0.95, color=col, cover="#22221f")
            walkers(c, 880, 1040, gy(960) + 6, 150, 5, seed=846 + self.seed, color=col)
        art.grass(c, hz + 40, 0, W, col, n=300, hmin=10, hmax=46, seed=43 + self.seed)
        comp(img, c.rgba())
        self.img = img
        self.hz = hz
        self.smoke = Fog(seed=849, scale=160, color="#3a2a22", density=0.5, top=0.3, bottom=0.62, speed=26, w=W,
                         h=H) if self.fire else None

    def base(self, t, u):
        out = self.img.copy()
        if self.fire:                                   # the village burning, far behind them (drawn behind the ridge)
            fl = flick(t, 7)
            glow = np.zeros_like(out)
            add_spot(glow, 80, self.hz - 10, 170, (1.0, 0.42, 0.12), 0.6 * fl)
            add_spot(glow, 60, self.hz - 2, 46, (1.0, 0.7, 0.3), 0.9 * fl)
            sky_mask = (out.sum(axis=2, keepdims=True) > 0.12).astype(np.float32)
            out += glow * sky_mask
        return out

    def animate(self, out, t, u):
        if self.fire:
            self.smoke.apply(out, t)


class Monument(Shot):
    """A statue on a tall granite pedestal in a small country park, with a boulder marker by the road."""
    focus = (540, 880)
    fog_d = 0.08
    fog_color = "#c0a890"

    def __init__(self, p=None):
        super().__init__(p)
        img = sky(DAWN, 851 + self.seed, stars=0, clouds=0.4)
        art.hills(img, 1180, 20, 600, "#10140f", 852 + self.seed, rim="#8a6a4c", rim_w=3, rim_a=0.4)
        c = cv()
        leafy(c, 150, 1250, 640, 853 + self.seed, color="#0a100c", rim="#2a3a2a")
        leafy(c, 960, 1260, 700, 854 + self.seed, color="#0a100c", rim="#2a3a2a")
        ground(c, 1240, color="#0b0d0a", seed=45 + self.seed)
        x, y = 540, 1250
        for w_, h_, yy in ((250, 46, 0), (200, 40, 46), (150, 300, 86), (176, 30, 386)):      # stepped pedestal
            c.rect(x - w_ / 2, y - yy - h_, x + w_ / 2, y - yy, "#4a4c4e")
            c.line([(x - w_ / 2, y - yy - h_), (x + w_ / 2, y - yy - h_)], "#9a9a94", 2, 0.6)
            c.rect(x, y - yy - h_, x + w_ / 2, y - yy, "#2e3032", 0.6)
        c.rect(x - 52, y - 330, x + 52, y - 200, "#35373a")                                   # the inscription panel
        for k in range(6):
            c.line([(x - 40, y - 314 + k * 18), (x + 40, y - 314 + k * 18)], "#6c6c68", 2, 0.7)
        art.figure(c, x, y - 416, 250, color="#3c3e40", coat=True, arms=((4, 2), (-4, -2)), legs=(2, -2))
        c.poly([(760, 1300), (790, 1236), (850, 1222), (900, 1250), (912, 1300)], "#3a3b3c")  # a boulder marker
        c.rect(800, 1250, 874, 1284, "#6a5a3a")
        comp(img, c.rgba())
        self.img = img


# --------------------------------------------------------------------------------------------- Michigan City

def manor(c, lights, x, y, s=1.0, lit=(), seed=0):
    """A 2 1/2-storey English manor: maroon brick, pale stone trim, steep gables, gable dormers, tall chimneys, a
    stone entrance porch and a terrace wall. (x, y) = bottom centre. Returns the windows [(x0, y0, x1, y1), ...]."""
    w, h = 780 * s, 330 * s
    x0, x1, top = x - w / 2, x + w / 2, y - h
    brick, stone, dark = "#2a1014", "#8a8274", "#0a0607"
    c.poly([(x0 - 16 * s, top), (x0 + 40 * s, top - 150 * s), (x1 - 40 * s, top - 150 * s), (x1 + 16 * s, top)], "#0d0a0b")
    for cx_ in (x0 + 120 * s, x - 40 * s, x1 - 150 * s):                                # chimneys
        c.rect(cx_ - 24 * s, top - 260 * s, cx_ + 24 * s, top - 100 * s, brick)
        c.rect(cx_ - 30 * s, top - 270 * s, cx_ + 30 * s, top - 254 * s, stone)
    c.rect(x0, top, x1, y, brick)
    wins = []
    for gx in (x0 + 150 * s, x1 - 150 * s):                                            # two big front gables
        c.poly([(gx - 130 * s, top + 4), (gx - 130 * s, top - 40 * s), (gx, top - 210 * s), (gx + 130 * s, top - 40 * s),
                (gx + 130 * s, top + 4)], brick)
        c.line([(gx - 132 * s, top - 40 * s), (gx, top - 212 * s), (gx + 132 * s, top - 40 * s)], stone, 5 * s)
        wins.append((gx - 26 * s, top - 120 * s, gx + 26 * s, top - 40 * s))
    for dx in (x - 110 * s, x, x + 110 * s):                                           # gable dormers between them
        c.poly([(dx - 36 * s, top), (dx - 36 * s, top - 60 * s), (dx, top - 104 * s), (dx + 36 * s, top - 60 * s),
                (dx + 36 * s, top)], brick)
        c.line([(dx - 38 * s, top - 60 * s), (dx, top - 106 * s), (dx + 38 * s, top - 60 * s)], stone, 3.5 * s)
        wins.append((dx - 15 * s, top - 62 * s, dx + 15 * s, top - 12 * s))
    for fl in range(2):
        wy = top + 36 * s + fl * 152 * s
        for k in range(8):
            wx = x0 + 44 * s + k * 92 * s
            if fl == 1 and k in (3, 4):
                continue
            wins.append((wx, wy, wx + 46 * s, wy + 104 * s))
    c.rect(x0, top + 150 * s, x1, top + 160 * s, stone, 0.8)                           # stone band courses
    c.rect(x0, top - 2 * s, x1, top + 8 * s, stone, 0.8)
    for (a, b, c_, d_) in wins:
        c.rect(a - 5 * s, b - 5 * s, c_ + 5 * s, d_ + 5 * s, stone, 0.85)
        c.rect(a, b, c_, d_, dark)
        c.line([((a + c_) / 2, b), ((a + c_) / 2, d_)], "#3a342e", 2 * s)
    for k, on in enumerate(lit):
        if on and k < len(wins):
            a, b, c_, d_ = wins[k]
            lights.rect(a, b, c_, d_, WARM, 0.6)
    c.rect(x - 70 * s, y - 150 * s, x + 70 * s, y, stone)                              # the entrance porch
    c.poly([(x - 82 * s, y - 148 * s), (x, y - 200 * s), (x + 82 * s, y - 148 * s)], stone)
    c.c.drawPath(smooth_path([(x - 34 * s, y), (x - 34 * s, y - 80 * s), (x, y - 110 * s), (x + 34 * s, y - 80 * s),
                              (x + 34 * s, y)], True, k=0.14), paint(dark))
    c.rect(x0 - 60 * s, y - 34 * s, x - 90 * s, y, stone, 0.9)                         # the terrace wall
    c.rect(x + 90 * s, y - 34 * s, x1 + 60 * s, y, stone, 0.9)
    return wins, (x0, top, x1, y)


class Manor(Shot):
    """The Barker Mansion's shape: a 2 1/2-storey maroon-brick English manor with stone trim, gables and dormers."""
    focus = (540, 980)
    fog_d = 0.1
    fog_color = "#7a8a9a"

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        dawn = bool(p.get("dawn"))
        img = sky(DAWN if dawn else BLUE, 861 + self.seed, moon=None if dawn else (860, 330, 44),
                  stars=0 if dawn else 320, clouds=0.35)
        art.hills(img, 1190, 14, 700, "#0a0e12", 862 + self.seed, rim="#3a4a5a", rim_w=3, rim_a=0.3)
        c = cv()
        lights = cv()
        s = float(p.get("scale", 1.0))
        lit = p.get("lit", [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0])
        self.wins, box = manor(c, lights, 540, 1240, s, lit=() if p.get("dim") else lit, seed=self.seed)
        comp(img, c.rgba())
        x0, top, x1, y = [int(v) for v in box]
        tex = masonry(y - top, x1 - x0, bw=40, bh=14, seed=863 + self.seed, color=(0.2, 0.07, 0.08),
                      mortar=(0.08, 0.05, 0.05), var=0.3)
        # brick texture only where the wall shows (not over the windows or the porch)
        m = np.full((y - top, x1 - x0), 0.35, np.float32)
        for (a, b, c_, d_) in self.wins:
            m[max(0, int(b - top) - 6):max(0, int(d_ - top) + 6), max(0, int(a - x0) - 6):int(c_ - x0) + 6] = 0
        m[int(y - top - 205 * s):, int(540 - x0 - 84 * s):int(540 - x0 + 84 * s)] = 0
        put_tex(img, tex, m, x0, top)
        d = cv()
        leafy(d, 40, 1300, 760, 864 + self.seed, color="#05080a", rim="#16222a")
        leafy(d, 1060, 1310, 700, 865 + self.seed, color="#05080a", rim="#16222a")
        d.poly([(-20, 1240), (W + 20, 1240), (W + 20, H), (-20, H)], "#07090b")
        d.poly([(470, 1240), (610, 1240), (800, H), (280, H)], "#16181a", 0.9)
        for fx in range(0, W + 40, 44):                                                # an iron fence along the walk
            d.rect(fx, 1330, fx + 4, 1420, "#020304")
        d.rect(-20, 1350, 430, 1356, "#020304")
        d.rect(650, 1350, W + 20, 1356, "#020304")
        art.grass(d, H - 320, 0, W, "#030405", n=300, hmin=10, hmax=40, seed=47 + self.seed)
        comp(img, d.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]
        self.dim = bool(p.get("dim"))
        self.lit = [k for k, on in enumerate(lit) if on and k < len(self.wins)]

    def animate(self, out, t, u):
        if self.dim:                                    # the lit windows go dark one by one
            n = len(self.lit)
            for i, k in enumerate(self.lit):
                off = self.dur * (0.2 + 0.7 * (i + 1) / n)
                a = max(0.0, min(1.0, (off - u) / 0.5))
                if a > 0:
                    x0, y0, x1, y1 = [int(v) for v in self.wins[k]]
                    out[y0:y1, x0:x1] += np.array([1.0, 0.7, 0.36], np.float32) * 0.55 * a * flick(t, k)


class CarWorks(Shot):
    """A railroad car works around 1900: long brick shops, smokestacks and a row of new wooden boxcars."""
    focus = (540, 1080)
    fog_d = 0.18
    fog_color = "#8a8078"

    def __init__(self, p=None):
        super().__init__(p)
        img = sky(DUSK, 871 + self.seed, stars=40, clouds=0.5)
        c = cv()
        lights = cv()
        c.poly([(-20, 1000), (W + 20, 1000), (W + 20, H), (-20, H)], "#0c0d0d")
        for k in range(5):                                                             # sawtooth-roofed shops
            bx = -40 + k * 240
            c.rect(bx, 800, bx + 240, 1000, "#1a0f0c")
            c.poly([(bx, 800), (bx + 170, 720), (bx + 240, 800)], "#0c0908")
            for j in range(4):
                wx = bx + 24 + j * 54
                c.rect(wx, 850, wx + 30, 950, "#080606")
                if hash2(k, j, self.seed) > 0.35:
                    lights.rect(wx, 850, wx + 30, 950, WARM, 0.5)
        self.stacks = [(210, 470), (700, 530), (940, 590)]
        for sx, sy in self.stacks:
            c.poly([(sx - 26, 800), (sx - 16, sy), (sx + 16, sy), (sx + 26, 800)], "#0d0908")
            c.rect(sx - 20, sy, sx + 20, sy + 12, "#1c1412")
        for row, (ry, s) in enumerate(((1120, 0.62), (1270, 0.9))):                    # boxcars on two yard tracks
            c.rect(-20, ry, W + 20, ry + 8 * s, "#34383a")
            for k in range(-1, 5):
                bx = k * 330 * s + (60 if row else -40)
                c.rect(bx, ry - 170 * s, bx + 300 * s, ry - 30 * s, "#3a1c14")
                c.rect(bx - 6 * s, ry - 182 * s, bx + 306 * s, ry - 168 * s, "#0c0908")
                for j in range(1, 12):
                    c.line([(bx + j * 25 * s, ry - 168 * s), (bx + j * 25 * s, ry - 32 * s)], "#0c0706", 1.5 * s, 0.7)
                c.rect(bx + 110 * s, ry - 160 * s, bx + 190 * s, ry - 36 * s, "#4a2418")
                for wx in (40, 86, 214, 260):
                    c.circle(bx + wx * s, ry - 14 * s, 20 * s, "#050506")
        art.grass(c, H - 260, 0, W, "#040504", n=260, hmin=10, hmax=36, seed=49 + self.seed)
        comp(img, c.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]
        self.smoke = Fog(seed=873, scale=140, color="#4a4038", density=0.6, top=0.14, bottom=0.4, speed=40, w=W, h=H)

    def animate(self, out, t, u):
        self.smoke.apply(out, t)


class Hall(Shot):
    """Inside a Gilded Age house at night: a wide staircase, a chandelier, a tall window. No one is shown."""
    focus = (540, 980)
    fog_d = 0.0

    def __init__(self, p=None):
        super().__init__(p)
        img = np.zeros((H, W, 3), np.float32)
        img[:] = np.array([0.035, 0.022, 0.018], np.float32)
        c = cv()
        lights = cv()
        c.rect(0, 0, W, 1250, "#120b09")                                               # panelled wall
        for k in range(7):
            px = 30 + k * 150
            c.rect(px, 760, px + 120, 1210, "#1a100c")
            c.rect(px + 10, 770, px + 110, 1200, "#140c09")
        c.rect(0, 730, W, 746, "#2a1a12")
        c.rect(430, 300, 650, 720, "#0a1420")                                          # the tall landing window
        c.rect(424, 294, 656, 302, "#3a281c")
        for k in (1, 2):
            c.line([(430 + k * 73, 300), (430 + k * 73, 720)], "#3a281c", 5)
        for k in (1, 2, 3):
            c.line([(430, 300 + k * 105), (650, 300 + k * 105)], "#3a281c", 5)
        lights.rect(430, 300, 650, 720, "#6a8aa8", 0.25)
        for k in range(12):                                                            # the staircase, rising away
            u = k / 11.0
            y = 1500 - 520 * u
            hw = 420 - 190 * u
            c.rect(540 - hw, y - 44, 540 + hw, y, "#2a1810" if k % 2 else "#24140e")
            c.rect(540 - hw * 0.45, y - 44, 540 + hw * 0.45, y, "#4a1418", 0.9)        # the runner
            for sgn in (-1, 1):
                c.rect(540 + sgn * hw - 5, y - 150, 540 + sgn * hw + 5, y - 40, "#1a0f0a")
        for sgn in (-1, 1):
            c.line([(540 + sgn * 420, 1350), (540 + sgn * 230, 830)], "#3a2418", 12)
            c.rect(540 + sgn * 420 - 22, 1290, 540 + sgn * 420 + 22, 1560, "#24160e")
            c.circle(540 + sgn * 420, 1276, 26, "#3a2418")
        c.poly([(0, 1500), (W, 1500), (W, H), (0, H)], "#0e0806")
        c.line([(540, 0), (540, 150)], "#1c140c", 4)                                   # the chandelier
        self.bulbs = []
        for k in range(7):
            a = math.pi * (0.1 + 0.8 * k / 6.0)
            bx, by = 540 + math.cos(a) * 150, 170 + math.sin(a) * 60
            c.line([(540, 150), (bx, by)], "#5a4420", 4)
            self.bulbs.append((bx, by + 8))
        comp(img, c.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]

    def animate(self, out, t, u):
        fl = flick(t, 5)
        add_spot(out, 540, 230, 420, (1.0, 0.72, 0.4), 0.22 * fl)
        for bx, by in self.bulbs:
            add_spot(out, bx, by, 9, (1.0, 0.9, 0.7), 1.2 * fl)


# --------------------------------------------------------------------------------------------- Crown Point

def touring_car(c, x, y, s=1.0, color="#07090b", rim="#5a6a70"):
    """A 1920s touring car from the side, facing left. (x, y) = ground under its middle. Returns the lamp position."""
    c.rect(x - 150 * s, y - 92 * s, x + 130 * s, y - 40 * s, color)                    # body
    c.rect(x - 230 * s, y - 84 * s, x - 150 * s, y - 40 * s, color)                    # hood
    c.rect(x - 244 * s, y - 92 * s, x - 228 * s, y - 36 * s, "#1a2226")                # radiator
    c.poly([(x - 70 * s, y - 92 * s), (x - 60 * s, y - 170 * s), (x + 120 * s, y - 170 * s), (x + 134 * s, y - 92 * s)],
           color)                                                                      # the folding top
    c.rect(x - 52 * s, y - 158 * s, x + 20 * s, y - 100 * s, "#16222a")
    c.rect(x + 30 * s, y - 158 * s, x + 108 * s, y - 100 * s, "#16222a")
    c.line([(x - 236 * s, y - 84 * s), (x + 130 * s, y - 92 * s)], rim, 2 * s, 0.6)
    c.poly([(x - 262 * s, y - 34 * s), (x - 150 * s, y - 52 * s), (x - 120 * s, y - 34 * s)], color)   # fenders
    c.poly([(x + 60 * s, y - 34 * s), (x + 150 * s, y - 56 * s), (x + 176 * s, y - 34 * s)], color)
    c.rect(x - 120 * s, y - 38 * s, x + 60 * s, y - 30 * s, color)                     # running board
    for wx in (-190, 112):
        c.circle(x + wx * s, y - 36 * s, 38 * s, "#030405")
        c.circle(x + wx * s, y - 36 * s, 26 * s, "#1a2024")
        c.circle(x + wx * s, y - 36 * s, 8 * s, "#3a444a")
    c.circle(x - 250 * s, y - 70 * s, 11 * s, "#2a2a22")
    return (x - 258 * s, y - 70 * s)


class CrownPointCourthouse(Shot):
    """A red-brick courthouse in the middle of a square: a tall central clock tower and a smaller tower at each end."""
    focus = (540, 880)
    fog_d = 0.08
    fog_color = "#8a9aa8"

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        dawn = bool(p.get("dawn"))
        img = sky(DAWN if dawn else BLUE, 881 + self.seed, moon=None if dawn else (170, 300, 40),
                  stars=0 if dawn else 300, clouds=0.3)
        c = cv()
        lights = cv()
        brick, stone, roof = "#3a1612", "#8a8070", "#10100f"
        x0, x1, base, top = 150, 930, 1250, 930
        c.rect(x0, top, x1, base, brick)
        c.poly([(x0 - 14, top), (x0 + 30, top - 70), (x1 - 30, top - 70), (x1 + 14, top)], roof)
        for tx, tw, th in ((x0 + 60, 120, 250), (x1 - 60, 120, 250)):                  # the end towers
            c.rect(tx - tw / 2, top - th + 120, tx + tw / 2, base, brick)
            c.poly([(tx - tw / 2 - 10, top - th + 124), (tx, top - th - 60), (tx + tw / 2 + 10, top - th + 124)], roof)
            c.rect(tx - 16, top - th + 160, tx + 16, top - th + 230, "#0a0808")
        c.rect(470, 560, 610, base, brick)                                             # the central clock tower
        c.rect(456, 548, 624, 566, stone)
        c.rect(476, 430, 604, 552, brick)
        c.poly([(462, 436), (540, 250), (618, 436)], roof)
        c.rect(536, 200, 544, 256, roof)
        lights.circle(540, 492, 44, "#ffe9b8", 0.75)
        c.circle(540, 492, 47, stone)
        c.circle(540, 492, 42, "#e8dcb8")
        c.line([(540, 492), (540, 462)], "#141210", 4)
        c.line([(540, 492), (562, 500)], "#141210", 4)
        c.rect(x0, top + 150, x1, top + 160, stone, 0.8)
        for fl in range(2):
            wy = top + 36 + fl * 160
            for k in range(11):
                wx = x0 + 34 + k * 66
                if 440 < wx + 20 < 640 and fl == 1:
                    continue
                c.rect(wx, wy, wx + 36, wy + 100, "#0a0808")
                c.c.drawPath(smooth_path([(wx - 3, wy + 6), (wx + 18, wy - 18), (wx + 39, wy + 6)], False),
                             paint(stone, stroke=5))
                if hash2(wx, wy, self.seed) > (0.75 if dawn else 0.45):
                    lights.rect(wx, wy, wx + 36, wy + 100, WARM, 0.6)
        c.c.drawPath(smooth_path([(506, base), (506, base - 110), (540, base - 150), (574, base - 110), (574, base)],
                                 True, k=0.14), paint("#0a0808"))
        comp(img, c.rgba())
        tex = masonry(base - top, x1 - x0, bw=38, bh=13, seed=883 + self.seed, color=(0.26, 0.09, 0.07),
                      mortar=(0.1, 0.06, 0.05), var=0.3)
        put_tex(img, tex, np.full((base - top, x1 - x0), 0.22, np.float32), x0, top)
        d = cv()
        for k in range(8):
            d.rect(430 + k * 14, 1250 + k * 9, 650 - k * 14 + 28 * k, 1259 + k * 9, "#4a463e")
        d.poly([(-20, 1320), (W + 20, 1320), (W + 20, H), (-20, H)], "#0a0c0e")
        d.poly([(-20, 1330), (W + 20, 1330), (W + 20, 1480), (-20, 1480)], "#1c2024")  # the street round the square
        leafy(d, 60, 1330, 520, 884 + self.seed, color="#05080a", rim="#16222a")
        leafy(d, 1030, 1330, 560, 885 + self.seed, color="#05080a", rim="#16222a")
        self.lamps = [(310, 1150), (770, 1150)]
        for lx, ly in self.lamps:
            d.rect(lx - 5, ly, lx + 5, 1330, "#030405")
            d.circle(lx, ly - 12, 16, "#2a2a22")
        self.head = touring_car(d, 700, 1420, 0.8, color="#020304") if p.get("car") else None
        comp(img, d.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]
        self.dawn = dawn

    def animate(self, out, t, u):
        if not self.dawn:
            for lx, ly in self.lamps:
                add_spot(out, lx, ly - 12, 90, (1.0, 0.8, 0.5), 0.3)
                add_spot(out, lx, ly - 12, 10, (1.0, 0.92, 0.75), 1.3)
        if self.head:
            add_spot(out, self.head[0], self.head[1], 70, (1.0, 0.9, 0.6), 0.5)
            add_spot(out, self.head[0], self.head[1], 9, (1.0, 0.95, 0.8), 1.5)


class JPOffice(Shot):
    """A small-town office across from the square at night: a lit window, a painted sign over it (sign="...") and a
    1920s touring car at the curb. No one is shown."""
    focus = (500, 960)
    fog_d = 0.08
    fog_color = "#8a9aa8"

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = sky(BLUE, 891 + self.seed, moon=(900, 300, 36), stars=300, clouds=0.3)
        c = cv()
        lights = cv()
        base = 1190
        for bx, bw, bt, col in ((-40, 300, 640, "#1c1210"), (260, 520, 560, "#2a1614"), (780, 340, 680, "#1a1412")):
            c.rect(bx, bt, bx + bw, base, col)
            c.rect(bx - 6, bt - 22, bx + bw + 6, bt, "#0e0b0a")
            for k in range(int(bw // 120)):
                wx = bx + 44 + k * 120
                c.rect(wx, bt + 60, wx + 52, bt + 170, "#090808")
                if hash2(bx, k, self.seed) > 0.6:
                    lights.rect(wx, bt + 60, wx + 52, bt + 170, WARM, 0.4)
        c.rect(300, 920, 560, base - 30, "#0a0808")                                    # the office window
        lights.rect(300, 920, 560, base - 30, WARM, 0.75)
        c.line([(430, 920), (430, base - 30)], "#2a1c14", 6)
        c.rect(610, 930, 720, base, "#120c0a")                                         # the door
        lights.rect(628, 950, 702, 1060, WARM, 0.5)
        c.rect(-20, base, W + 20, base + 26, "#3a3a38")                                # the sidewalk
        c.poly([(-20, base + 26), (W + 20, base + 26), (W + 20, H), (-20, H)], "#101214")
        self.lamp = (880, 900)
        c.rect(874, 900, 886, base + 6, "#030405")
        c.circle(880, 886, 18, "#2a2a22")
        self.head = touring_car(c, 560, 1300, 0.85, color="#020304")
        comp(img, c.rgba())
        from PIL import Image, ImageDraw
        txt = str(p.get("sign", "JUSTICE OF THE PEACE"))
        im = Image.new("RGBA", (480, 78), (226, 214, 186, 255))
        dr = ImageDraw.Draw(im)
        dr.rectangle((4, 4, 475, 73), outline=(40, 30, 22, 255), width=3)
        f = K.C.font("oldst_b", 36)
        while f.getlength(txt) > 440:
            f = K.C.font("oldst_b", int(f.size) - 2)
        dr.text(((480 - f.getlength(txt)) / 2, (78 - f.size * 1.18) / 2), txt, font=f, fill=(30, 22, 16, 255))
        from reel_haunts import layer_from_pil
        comp(img, layer_from_pil(im, 280, 810), 0.8)
        self.img = img
        self.lights = lights.rgba()[..., :3]

    def animate(self, out, t, u):
        add_spot(out, self.lamp[0], self.lamp[1] - 14, 110, (1.0, 0.8, 0.5), 0.35)
        add_spot(out, self.lamp[0], self.lamp[1] - 14, 10, (1.0, 0.92, 0.75), 1.3)
        add_spot(out, self.head[0], self.head[1], 70, (1.0, 0.9, 0.6), 0.5)
        add_spot(out, self.head[0], self.head[1], 9, (1.0, 0.95, 0.8), 1.5)


K.KINDS.update({"village": Village, "march": March, "monument": Monument, "manor": Manor, "carworks": CarWorks,
                "hall": Hall, "cpcourt": CrownPointCourthouse, "jpoffice": JPOffice})
K.AMBIENCE.update({"village": ("wind", "bell"), "march": ("wind", None), "monument": ("wind", None),
                   "manor": ("wind", "creak"), "carworks": ("rumble", "whistle"), "hall": ("room", "creak"),
                   "cpcourt": ("wind", "bell"), "jpoffice": ("wind", None)})
