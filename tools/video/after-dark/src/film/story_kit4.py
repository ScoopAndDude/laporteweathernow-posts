"""More story illustrations for La Porte After Dark (story_kit4.py; added Nov. 12, 2026, for the Portage, Chesterton, Kingston,
Durant, J.D. Marshall and Copshaholm shorts). Same idea as story_kit2.py: each scene shows what the narrator is
describing. They register themselves in story_kit.KINDS:

    skijump    a tall timber-and-steel ski jump on a snowy sand dune above the lake, a small crowd at the foot
               crowd=False  no people (the tower alone)   gone=True  the bare dune with no tower (after it was sold)
    airliner   a 1930s twin-engine airliner, small, crossing a night sky over farm fields (no moon)
               plane=False  the empty sky and fields   lanterns=True  a few lantern lights out in the field
    oldtown    a small railroad-era main street by a river: false-front stores, a church steeple, trees in leaf
               stage="town" (default) | "rising" (water in the street) | "under" (open lake, only moonlight)
               | "drought" (cracked lakebed with stone foundations showing, the lake far off)
    bridge     a steel truss highway bridge over a wide river on a summer evening, the road running onto it
               barricade=True  a wooden barricade across the road with two small guards
               tents=True  a few army tents and small figures beside the road   night=True  a night sky
    steamer    a wooden steam barge of about 1900 on the lake off a line of dunes: one stack aft, a mast forward
               list=degrees  heel the ship over   storm=True  a dark squall sky, no moon
    wreck      under water: a wooden hull lying upside down on a sandy bottom, light slanting down (no one shown)
    propeller  a big four-blade ship's propeller on a stone base beside a beach pavilion, the lake behind
    fieldstone a 2 1/2-storey fieldstone mansion: big red tile gabled roof, a round corner turret with a conical
               roof, an arched wrap-around porch   lit=[0/1...]  windows that glow   dawn=True  morning sky
    plowfield  a walking plow standing in a furrowed field at dawn, a factory with smokestacks far off

People are small anonymous silhouettes only. Nothing shows a body, a real person's likeness or a brand.
"""
import math

import numpy as np

import art
import story_kit as K
from story_kit import Shot, W, H, WARM, hash2
from core import add_spot, Fog, smooth_path, paint
from reel_haunts import cv, comp
from story_kit2 import DUSK, BLUE, DAWN, NIGHT, sky, leafy, ground, walkers

WINTER = [(0.0, "#070b14"), (0.35, "#16223a"), (0.55, "#3a4660"), (0.64, "#6a6c80"), (1.0, "#2c3442")]
STORM = [(0.0, "#020305"), (0.4, "#070b10"), (0.62, "#10181e"), (1.0, "#0c1216")]
SEA = [(0.0, "#0a2a34"), (0.35, "#0a2430"), (0.7, "#061820"), (1.0, "#030c10")]


def water(c, y0, y1, color="#0a1820", glint="#3a5a68", seed=0, n=70):
    """A band of water between y0 and y1 with short ripple lines."""
    c.rect(-20, y0, W + 20, y1, color)
    r = np.random.default_rng(seed)
    for k in range(n):
        y = r.uniform(y0 + 4, y1 - 4)
        x = r.uniform(0, W)
        ln = r.uniform(20, 90) * (0.4 + 0.6 * (y - y0) / max(1, y1 - y0))
        c.line([(x, y), (x + ln, y)], glint, 1.6, r.uniform(0.15, 0.5))


def dune_shape(c, color="#3a3f48", rim="#8a909a", top=620, snow=False):
    """A big dune rising to the right. Returns its crest line as points."""
    pts = [(-20, 1180), (160, 1100), (380, 960), (600, 800), (800, 680), (960, top), (W + 20, top - 20)]
    c.poly(pts + [(W + 20, H), (-20, H)], "#7e8696" if snow else color)
    c.line(pts, "#d0d4dc" if snow else rim, 3, 0.7)
    return pts


# --------------------------------------------------------------------------------------------- Ogden Dunes

class SkiJump(Shot):
    """A tall ski jump tower on a snowy dune above the lake, around 1930."""
    focus = (620, 760)
    fog_d = 0.06
    fog_color = "#aab4c4"

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = sky(WINTER, 901 + self.seed, stars=30, clouds=0.55)
        c = cv()
        water(c, 1000, 1200, "#141c28", "#5a6a80", 902 + self.seed, 50)                 # the lake, far left
        dune_shape(c, snow=True)
        if not p.get("gone"):
            tx, ty, tb = 900, 250, 640                                                   # tower top, and its foot
            for k in range(7):                                                           # lattice tower legs
                y0 = ty + k * (tb - ty) / 7
                y1 = ty + (k + 1) * (tb - ty) / 7
                w0, w1 = 40 + k * 9, 40 + (k + 1) * 9
                c.line([(tx - w0, y0), (tx - w1, y1)], "#0c0e12", 5)
                c.line([(tx + w0, y0), (tx + w1, y1)], "#0c0e12", 5)
                c.line([(tx - w0, y0), (tx + w1, y1)], "#0c0e12", 2.5)
                c.line([(tx + w0, y0), (tx - w1, y1)], "#0c0e12", 2.5)
                c.line([(tx - w1, y1), (tx + w1, y1)], "#0c0e12", 3)
            c.rect(tx - 50, ty - 26, tx + 50, ty, "#0c0e12")                             # the start platform
            c.line([(tx, ty - 26), (tx, ty - 90)], "#0c0e12", 3)                         # a flag pole
            c.poly([(tx, ty - 90), (tx + 40, ty - 80), (tx, ty - 68)], "#5a1c1c")
            run = [(tx - 40, ty), (700, 430), (520, 640), (400, 800), (330, 880), (290, 900)]   # the inrun and takeoff
            c.c.drawPath(smooth_path(run + [(300, 930), (410, 840), (540, 690), (720, 480), (tx - 30, ty + 40)],
                                     True, k=0.12), paint("#b4bac6"))
            c.line(run, "#0c0e12", 4)
            for k in range(1, 9):                                                        # trestle under the inrun
                a = k / 9.0
                x = tx - 40 + (290 - (tx - 40)) * a
                y = ty + (900 - ty) * a ** 0.8
                base = 1180 - (x + 20) * 0.47 if x < 960 else 640
                c.line([(x, y + 20), (x, max(y + 30, min(base, 1100)))], "#0c0e12", 3)
        if p.get("crowd", True) and not p.get("gone"):
            walkers(c, 40, 520, 1150, 52, 26, seed=903 + self.seed, color="#07080a")
            walkers(c, 80, 620, 1195, 62, 22, seed=904 + self.seed, color="#050608")
        comp(img, c.rgba())
        self.img = img


# --------------------------------------------------------------------------------------------- Chesterton, 1933

class Airliner(Shot):
    """A 1930s twin-engine airliner, small, crossing a dark sky over farm fields."""
    focus = (540, 760)
    fog_d = 0.1

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = sky(NIGHT, 911 + self.seed, stars=420, clouds=0.25)
        c = cv()
        lights = cv()
        c.poly([(-20, 1090), (W + 20, 1070), (W + 20, H), (-20, H)], "#06090a")
        for k in range(9):                                                              # field rows running away
            x = -200 + k * 190
            c.line([(x, H - 500), (540 + (x - 540) * 0.12, 1084)], "#0e1513", 2, 0.8)
        for k in range(5):
            leafy(c, 80 + k * 240 + 40 * hash2(k, 1, self.seed), 1090, 150 + 60 * hash2(k, 2, self.seed),
                  912 + k + self.seed, color="#040807", rim="#0f1a16")
        c.rect(770, 1010, 880, 1082, "#0a0808")                                          # a barn and a silo
        c.poly([(760, 1012), (825, 962), (890, 1012)], "#070606")
        c.rect(892, 980, 922, 1082, "#0b0a0a")
        c.circle(907, 980, 15, "#0b0a0a")
        lights.rect(700, 1050, 712, 1066, WARM, 0.6)                                     # a farmhouse window
        c.rect(680, 1036, 740, 1082, "#080707")
        c.poly([(674, 1038), (710, 1010), (746, 1038)], "#060505")
        self.plane = bool(p.get("plane", True))
        self.lanterns = [(180 + 190 * k + 60 * hash2(k, 5, self.seed), 1150 + 70 * hash2(k, 6, self.seed))
                         for k in range(5)] if p.get("lanterns") else []
        comp(img, c.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]

    def draw_plane(self, out, x, y, s=1.0):
        c = cv()
        col = "#3a424c"
        c.poly([(x - 120 * s, y), (x - 100 * s, y - 12 * s), (x + 70 * s, y - 14 * s), (x + 118 * s, y - 4 * s),
                (x + 124 * s, y + 4 * s), (x + 70 * s, y + 12 * s), (x - 100 * s, y + 8 * s)], col)   # fuselage
        c.poly([(x - 112 * s, y - 6 * s), (x - 138 * s, y - 46 * s), (x - 118 * s, y - 46 * s),
                (x - 88 * s, y - 10 * s)], col)                                          # the fin
        c.poly([(x - 20 * s, y + 4 * s), (x + 30 * s, y + 4 * s), (x + 10 * s, y + 20 * s), (x - 60 * s, y + 22 * s)], col)
        c.ellipse(x + 26 * s, y + 12 * s, 26 * s, 9 * s, "#262c34")                      # the near engine
        for k in range(5):
            c.rect(x - 36 * s + k * 20 * s, y - 8 * s, x - 26 * s + k * 20 * s, y - 2 * s, "#d8c890", 0.85)
        comp(out, c.rgba())

    def animate(self, out, t, u):
        if self.plane:
            k = min(1.0, u / max(2.0, self.dur))
            self.draw_plane(out, 260 + 520 * k, 620 - 60 * k, 1.7)
            add_spot(out, 260 + 520 * k - 204, 620 - 60 * k - 76, 7, (1.0, 0.3, 0.25), 0.9)
        for i, (x, y) in enumerate(self.lanterns):
            sw = 10 * math.sin(t * 0.8 + i)
            add_spot(out, x + sw, y, 46, (1.0, 0.8, 0.5), 0.35)
            add_spot(out, x + sw, y, 7, (1.0, 0.92, 0.75), 1.3)


# --------------------------------------------------------------------------------------------- Woodville, Oklahoma

class OldTown(Shot):
    """A small railroad-era town by a river, then the water rising, then the open lake, then the drought."""
    focus = (540, 900)
    fog_d = 0.08
    fog_color = "#a09080"

    def __init__(self, p=None):
        super().__init__(p)
        stage = self.p.get("stage", "town")
        self.stage = stage
        c = cv()
        lights = cv()
        if stage == "under":
            img = sky(BLUE, 921 + self.seed, moon=(760, 420, 54), stars=200, clouds=0.3)
            water(c, 900, H, "#0a1a26", "#4a6a80", 922 + self.seed, 150)
            c.poly([(-20, 900), (300, 880), (700, 892), (W + 20, 878), (W + 20, 904), (-20, 904)], "#050a0c")
            for k in range(14):                                                          # the moon's path
                y = 920 + k * 42
                c.line([(760 - 30 - k * 6, y), (760 + 30 + k * 6, y)], "#9ab4c4", 3, 0.5 - k * 0.025)
        elif stage == "drought":
            img = sky(DAWN, 923 + self.seed, stars=0, clouds=0.25)
            water(c, 930, 990, "#3a4a52", "#c8a880", 924 + self.seed, 30)                # the lake, far off and low
            c.poly([(-20, 985), (W + 20, 975), (W + 20, H), (-20, H)], "#3a3026")
            r = np.random.default_rng(925 + self.seed)
            for k in range(60):                                                          # cracked mud
                x, y = r.uniform(0, W), r.uniform(1010, 1600)
                pts = [(x, y)]
                for j in range(3):
                    x, y = x + r.uniform(-90, 90), y + r.uniform(10, 60)
                    pts.append((x, y))
                c.line(pts, "#1e1811", 2, 0.7)
            for (x0, y0, w_, h_) in ((120, 1080, 300, 90), (560, 1040, 240, 70), (700, 1180, 330, 100), (200, 1230, 260, 80)):
                c.poly([(x0, y0), (x0 + w_, y0 - 12), (x0 + w_ + 40, y0 + h_ - 12), (x0 + 40, y0 + h_)], "#6a6258")
                c.poly([(x0 + 22, y0 + 12), (x0 + w_ - 6, y0 + 2), (x0 + w_ + 22, y0 + h_ - 24), (x0 + 50, y0 + h_ - 12)],
                       "#2e261e")                                                        # stone foundations
            c.line([(880, 990), (880, 930)], "#2a221a", 6)                               # a dead tree stub
            c.line([(880, 950), (910, 925)], "#2a221a", 4)
        else:
            img = sky(DUSK, 926 + self.seed, stars=40, clouds=0.4)
            water(c, 960, 1010, "#2a2c3a", "#b08060", 927 + self.seed, 24)               # the river beyond
            c.poly([(-20, 1000), (W + 20, 1000), (W + 20, H), (-20, H)], "#0b0c0b")
            for k in range(4):
                leafy(c, 60 + k * 330, 1010, 300, 928 + k + self.seed, color="#070c09", rim="#2a3226")
            fronts = [(60, 250, 230), (300, 210, 280), (520, 230, 250), (760, 250, 300)]
            for i, (bx, bw, bh) in enumerate(fronts):                                    # false-front stores
                c.rect(bx, 1180 - bh, bx + bw, 1180, "#2a1a14" if i % 2 else "#33261c")
                c.rect(bx - 6, 1180 - bh - 26, bx + bw + 6, 1180 - bh, "#1a120e")
                c.rect(bx + 20, 1180 - 110, bx + bw - 20, 1180 - 20, "#0c0908")
                c.poly([(bx - 10, 1180 - 130), (bx + bw + 10, 1180 - 130), (bx + bw + 24, 1180 - 110), (bx - 24, 1180 - 110)],
                       "#14100d")                                                        # an awning
                if stage == "town" and hash2(i, 3, self.seed) > 0.3:
                    lights.rect(bx + 30, 1180 - 100, bx + bw - 30, 1180 - 36, WARM, 0.45)
                for j in range(2):
                    wx = bx + 40 + j * (bw - 120)
                    c.rect(wx, 1180 - bh + 40, wx + 40, 1180 - bh + 110, "#0c0908")
            sx = 470                                                                     # the church steeple behind
            c.rect(sx - 26, 760, sx + 26, 960, "#3a3530")
            c.poly([(sx - 32, 762), (sx, 640), (sx + 32, 762)], "#1a1614")
            c.line([(sx, 640), (sx, 606)], "#1a1614", 3)
            c.line([(sx - 12, 620), (sx + 12, 620)], "#1a1614", 3)
            c.poly([(-20, 1180), (W + 20, 1180), (W + 20, H), (-20, H)], "#17130f")       # the dirt street
            if stage == "rising":
                water(c, 1130, H, "#141c26", "#8a7a70", 929 + self.seed, 130)
        comp(img, c.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]


# --------------------------------------------------------------------------------------------- Red River, 1931

class TrussBridge(Shot):
    """A steel truss highway bridge over a wide river on a summer evening, the road running onto it."""
    focus = (560, 900)
    fog_d = 0.06
    fog_color = "#b09078"

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = sky(NIGHT if p.get("night") else DUSK, 931 + self.seed, moon=(180, 360, 40) if p.get("night") else None,
                  stars=300 if p.get("night") else 30, clouds=0.4)
        c = cv()
        art.hills(img, 1010, 16, 700, "#0a0d0b", 932 + self.seed, rim="#6a4a38", rim_w=2, rim_a=0.3)
        water(c, 1010, 1200, "#1c1a22" if not p.get("night") else "#0a1018", "#a07050", 933 + self.seed, 60)
        steel = "#0a0b0d" if not p.get("night") else "#1a2028"
        x0, x1, deck = 180, 1120, 1010                                                   # the bridge, going away right
        spans = 4
        for k in range(spans):
            a0, a1 = x0 + k * (x1 - x0) / spans, x0 + (k + 1) * (x1 - x0) / spans
            sc0, sc1 = 1 - k * 0.2, 1 - (k + 1) * 0.2
            h0, h1 = 190 * sc0, 190 * sc1
            y0, y1 = deck - k * 16, deck - (k + 1) * 16
            mid = (a0 + a1) / 2
            c.line([(a0, y0), (a0 + (mid - a0) * 0.4, y0 - h0), (mid + (a1 - mid) * 0.6, y1 - h1), (a1, y1)], steel, 7 * sc0)
            c.line([(a0, y0), (a1, y1)], steel, 9 * sc0)
            n = 6
            for j in range(1, n):
                xx = a0 + (a1 - a0) * j / n
                yy = y0 + (y1 - y0) * j / n
                top = yy - (h0 + (h1 - h0) * j / n) * (1.0 if 1 < j < n - 1 else 0.82)
                c.line([(xx, yy), (xx, top)], steel, 3 * sc0)
                if j < n - 1:
                    x2 = a0 + (a1 - a0) * (j + 1) / n
                    y2 = y0 + (y1 - y0) * (j + 1) / n
                    c.line([(xx, top), (x2, y2)], steel, 2.2 * sc0)
            c.rect(a1 - 9 * sc1, y1, a1 + 9 * sc1, 1200, "#15161a")                       # a pier
        c.poly([(-20, 1160), (300, 1120), (W + 20, 1180), (W + 20, H), (-20, H)], "#0b0c0a")   # the near bank
        c.poly([(-20, 1500), (-20, 1300), (120, 1090), (200, 1010), (240, 1010), (330, 1120), (520, H)], "#191614")  # road
        for k in range(3):
            leafy(c, 760 + k * 150, 1190, 300 + 40 * k, 934 + k + self.seed, color="#060a08", rim="#2a2a22")
        if p.get("barricade"):
            for (bx, by, s) in ((110, 1230, 1.5), (360, 1224, 1.4)):                      # sawhorse barricade
                c.line([(bx - 70 * s, by - 60 * s), (bx + 70 * s, by - 60 * s)], "#b8a078", 12 * s)
                c.line([(bx - 70 * s, by - 32 * s), (bx + 70 * s, by - 32 * s)], "#b8a078", 10 * s)
                for dx in (-56, 56):
                    c.line([(bx + dx * s - 14 * s, by), (bx + dx * s, by - 72 * s), (bx + dx * s + 14 * s, by)], "#2a2118", 5 * s)
            art.figure(c, 500, 1226, 170, color="#050607", hat="brim", arms=((4, 2), (-4, -2)), legs=(4, -4))
            art.figure(c, 590, 1222, 164, color="#050607", hat="brim", arms=((4, 2), (-4, -2)), legs=(4, -4))
        self.fires = []
        if p.get("tents"):
            for k, (tx, ty, s) in enumerate(((620, 1250, 1.0), (790, 1240, 0.9), (940, 1252, 1.0))):
                c.poly([(tx - 70 * s, ty), (tx, ty - 80 * s), (tx + 70 * s, ty)], "#5a5646")
                c.poly([(tx - 12 * s, ty), (tx, ty - 60 * s), (tx + 12 * s, ty)], "#15140f")
            walkers(c, 560, 1000, 1262, 70, 6, seed=935 + self.seed, color="#050607")
            self.fires = [(720, 1262)]
        comp(img, c.rgba())
        self.img = img

    def animate(self, out, t, u):
        for (x, y) in self.fires:
            f = 0.8 + 0.2 * math.sin(t * 9.0)
            add_spot(out, x, y - 6, 60, (1.0, 0.6, 0.25), 0.4 * f)
            add_spot(out, x, y - 6, 9, (1.0, 0.85, 0.5), 1.4 * f)


# --------------------------------------------------------------------------------------------- the J.D. Marshall

def steam_barge(c, x, y, s=1.0, ang=0.0):
    """A wooden steam barge of about 1900 seen from the side, bow to the right. (x, y) = waterline midships."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P(px, py):
        return (x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s)
    hull = "#14100e"
    c.poly([P(-300, -40), P(300, -46), P(330, -64), P(290, 0), P(-290, 0), P(-316, -30)], hull)
    c.line([P(-300, -40), P(300, -46)], "#5a4a3a", 3 * s, 0.7)
    c.poly([P(-290, -40), P(-290, -96), P(-150, -96), P(-150, -40)], "#3a3530")          # the cabin, aft
    c.poly([P(-270, -96), P(-270, -130), P(-190, -130), P(-190, -96)], "#2e2a26")        # the pilot house
    for k in range(4):
        a, b = P(-278 + k * 32, -84), P(-262 + k * 32, -60)
        c.poly([a, (b[0], a[1]), b, (a[0], b[1])], "#d0b070", 0.8)
    c.poly([P(-214, -130), P(-218, -236), P(-186, -236), P(-190, -130)], "#0c0a09")      # the stack
    c.line([P(-218, -200), P(-186, -200)], "#6a2a20", 8 * s)
    c.line([P(170, -46), P(170, -300)], "#0c0a09", 5 * s)                                # a mast and boom, forward
    c.line([P(170, -250), P(20, -80)], "#0c0a09", 3 * s)
    for k in range(5):                                                                   # deck gear amidships
        c.line([P(-110 + k * 50, -44), P(-110 + k * 50, -66)], "#0c0a09", 4 * s)
    return P(-202, -240)


class Steamer(Shot):
    """A wooden steam barge on Lake Michigan off a line of dunes."""
    focus = (540, 900)
    fog_d = 0.1

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        storm = bool(p.get("storm"))
        img = sky(STORM if storm else BLUE, 941 + self.seed, moon=None if storm else (840, 380, 46),
                  stars=0 if storm else 220, clouds=0.95 if storm else 0.35)
        c = cv()
        c.poly([(-20, 960), (200, 900), (420, 940), (640, 880), (860, 930), (W + 20, 890), (W + 20, 1000), (-20, 1000)],
               "#1c2026" if not storm else "#0c0f12")                                    # the dunes on shore
        water(c, 990, H, "#0a1620" if not storm else "#070c10", "#4a6a80" if not storm else "#2a3a44",
              942 + self.seed, 170)
        self.ang = math.radians(float(p.get("list", 0)))
        self.top = steam_barge(c, 520, 1140 + (40 if self.ang else 0), 1.15, self.ang)
        water(c, 1150 + (40 if self.ang else 0), 1215 + (40 if self.ang else 0), "#0a1620" if not storm else "#070c10",
              "#4a6a80" if not storm else "#2a3a44", 943 + self.seed, 30)
        comp(img, c.rgba())
        self.img = img
        self.smoke = Fog(seed=944, scale=120, color="#3a3a3c", density=0.5, top=0.3, bottom=0.5, speed=50, w=W, h=H)

    def animate(self, out, t, u):
        self.smoke.apply(out, t)


class Wreck(Shot):
    """Under water: a wooden hull lying upside down on a sandy bottom, light slanting down. No one is shown."""
    focus = (540, 1000)
    fog_d = 0.0

    def __init__(self, p=None):
        super().__init__(p)
        img = sky(SEA, 951 + self.seed, stars=0, clouds=0.0)
        c = cv()
        for k in range(7):                                                               # light rays
            x = 80 + k * 170
            c.poly([(x, 0), (x + 70, 0), (x + 260, 1300), (x + 60, 1300)], "#6ab0b8", 0.05 + 0.02 * (k % 3))
        c.poly([(-20, 1180), (300, 1150), (760, 1170), (W + 20, 1140), (W + 20, H), (-20, H)], "#1c2a26")   # the sand
        r = np.random.default_rng(952 + self.seed)
        for k in range(40):
            x = r.uniform(0, W)
            y = r.uniform(1200, 1700)
            c.line([(x, y), (x + r.uniform(40, 120), y + r.uniform(-4, 4))], "#2c3e38", 2, 0.5)
        hull = "#0c1412"
        c.c.drawPath(smooth_path([(140, 1180), (220, 1010), (480, 950), (800, 965), (960, 1060), (1000, 1180)],
                                 True, k=0.2), paint(hull))                              # the overturned hull
        c.line([(220, 1012), (480, 952), (800, 967), (960, 1062)], "#2a3c38", 6)         # the keel
        for k in range(14):                                                              # planking, some gone
            x = 200 + k * 56
            if k in (5, 6, 10):
                c.poly([(x, 1178), (x + 6, 1010 + abs(k - 7) * 8), (x + 44, 1010 + abs(k - 7) * 8), (x + 50, 1178)], "#050a09")
            c.line([(x, 1178), (x + 6, 1000 + abs(k - 7) * 9)], "#1c2a28", 3, 0.8)
        for k in range(5):                                                               # loose timbers
            x = 80 + k * 210
            c.line([(x, 1230 + 20 * (k % 2)), (x + 120, 1215 + 30 * (k % 3))], "#0c1412", 9)
        comp(img, c.rgba())
        self.img = img
        self.motes = np.random.default_rng(953).uniform(0, 1, (60, 3))

    def animate(self, out, t, u):
        for (a, b, ph) in self.motes:
            x = (a * W + 20 * math.sin(t * 0.3 + ph * 6)) % W
            y = (b * 1300 - t * 12 * (0.5 + ph)) % 1300
            add_spot(out, x, y, 3, (0.6, 0.9, 0.9), 0.35)


class Propeller(Shot):
    """A big four-blade ship's propeller on a stone base beside a beach pavilion, the lake behind."""
    focus = (480, 950)
    fog_d = 0.06
    fog_color = "#b09880"

    def __init__(self, p=None):
        super().__init__(p)
        img = sky(DUSK, 961 + self.seed, stars=30, clouds=0.4)
        c = cv()
        lights = cv()
        water(c, 980, 1080, "#2a2a38", "#b08868", 962 + self.seed, 40)
        c.poly([(-20, 1070), (W + 20, 1060), (W + 20, H), (-20, H)], "#2a261e")           # the beach
        px = 650                                                                         # the pavilion, right
        c.rect(px, 760, W + 20, 1100, "#3a3026")
        c.poly([(px - 30, 762), (px + 60, 690), (W + 20, 690), (W + 20, 762)], "#2a1a14")
        for k in range(4):
            ax = px + 40 + k * 110
            c.c.drawPath(smooth_path([(ax, 1100), (ax, 900), (ax + 40, 860), (ax + 80, 900), (ax + 80, 1100)], True, k=0.2),
                         paint("#0c0a08"))
            lights.rect(ax + 10, 920, ax + 70, 1000, WARM, 0.3)
        x, y, R = 330, 1010, 170                                                         # the propeller
        c.rect(x - 150, y + R + 6, x + 150, y + R + 70, "#6a665e")
        c.rect(x - 150, y + R + 6, x + 150, y + R + 16, "#9a968c")
        for k in range(4):
            a = math.radians(20 + k * 90)
            tip = (x + math.cos(a) * R, y + math.sin(a) * R)
            n = (-math.sin(a), math.cos(a))
            c.c.drawPath(smooth_path([(x, y), (x + math.cos(a) * R * 0.5 + n[0] * 64, y + math.sin(a) * R * 0.5 + n[1] * 64),
                                      tip, (x + math.cos(a) * R * 0.55 - n[0] * 30, y + math.sin(a) * R * 0.55 - n[1] * 30)],
                                     True, k=0.3), paint("#4a3e2c"))
            c.line([(x, y), tip], "#7a6a4a", 3, 0.6)
        c.circle(x, y, 40, "#3a3022")
        c.circle(x, y, 18, "#1a1610")
        comp(img, c.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]


# --------------------------------------------------------------------------------------------- Copshaholm

class Fieldstone(Shot):
    """A 2 1/2-storey fieldstone mansion with a big red tile roof, a round corner turret and an arched porch."""
    focus = (540, 900)
    fog_d = 0.08

    def __init__(self, p=None):
        super().__init__(p)
        p = self.p
        img = sky(DAWN if p.get("dawn") else BLUE, 971 + self.seed, moon=None if p.get("dawn") else (190, 330, 42),
                  stars=0 if p.get("dawn") else 220, clouds=0.35)
        c = cv()
        lights = cv()
        leafy(c, 60, 1250, 620, 972 + self.seed, color="#070b09", rim="#22302a")
        leafy(c, 1040, 1250, 560, 973 + self.seed, color="#070b09", rim="#22302a")
        ground(c, 1240, color="#090b09", seed=61 + self.seed)
        x0, x1, base, eave = 190, 860, 1240, 880
        stone, tile, dark, trim = "#4a4640", "#5a221a", "#0a0807", "#8a8478"
        c.poly([(x0 - 20, eave), (x0 + 110, eave - 230), (x1 - 110, eave - 230), (x1 + 20, eave)], tile)   # main roof
        for cx_ in (x0 + 150, x1 - 190):                                                 # chimneys
            c.rect(cx_ - 22, eave - 330, cx_ + 22, eave - 180, stone)
            c.rect(cx_ - 28, eave - 340, cx_ + 28, eave - 326, trim)
        c.rect(x0, eave, x1, base, stone)
        r = np.random.default_rng(974)
        for k in range(520):                                                             # fieldstones: grey and red
            sx, sy = r.uniform(x0 + 6, x1 - 6), r.uniform(eave + 6, base - 6)
            c.ellipse(sx, sy, r.uniform(8, 17), r.uniform(6, 12), "#6a5a52" if r.uniform() < 0.3 else "#5c5a56",
                      r.uniform(0.35, 0.8))
        gx = x0 + 190                                                                    # the big front gable
        c.poly([(gx - 150, eave + 4), (gx - 150, eave - 30), (gx, eave - 250), (gx + 150, eave - 30), (gx + 150, eave + 4)],
               stone)
        c.line([(gx - 152, eave - 30), (gx, eave - 252), (gx + 152, eave - 30)], tile, 10)
        wins = [(gx - 34, eave - 150, gx + 34, eave - 60)]
        for dx in (x0 + 430, x0 + 540):                                                  # roof dormers
            c.poly([(dx - 34, eave - 60), (dx - 34, eave - 120), (dx, eave - 160), (dx + 34, eave - 120), (dx + 34, eave - 60)],
                   stone)
            c.line([(dx - 36, eave - 120), (dx, eave - 162), (dx + 36, eave - 120)], tile, 6)
            wins.append((dx - 16, eave - 116, dx + 16, eave - 66))
        for k in range(6):
            wx = x0 + 40 + k * 104
            wins.append((wx, eave + 40, wx + 50, eave + 150))
        tx, tr = x1 - 10, 78                                                             # the round corner turret
        c.rect(tx - tr, eave - 90, tx + tr, base, stone)
        for k in range(110):
            sx, sy = r.uniform(tx - tr + 6, tx + tr - 6), r.uniform(eave - 84, base - 6)
            c.ellipse(sx, sy, r.uniform(8, 15), r.uniform(6, 11), "#6a5a52" if r.uniform() < 0.3 else "#5c5a56", 0.6)
        c.rect(tx + 10, eave - 90, tx + tr, base, "#000000", 0.3)                         # the turret's shaded side
        c.poly([(tx - tr - 12, eave - 88), (tx, eave - 300), (tx + tr + 12, eave - 88)], tile)
        c.line([(tx, eave - 300), (tx, eave - 336)], dark, 3)
        for wy in (eave - 50, eave + 70, eave + 200):
            wins.append((tx - 22, wy, tx + 22, wy + 84))
        for k in range(5):                                                               # the arched porch
            ax = x0 - 30 + k * 132
            c.rect(ax - 12, base - 150, ax + 12, base, trim)
            if k < 4:
                c.c.drawPath(smooth_path([(ax + 12, base - 150), (ax + 66, base - 196), (ax + 120, base - 150),
                                          (ax + 120, base - 136), (ax + 66, base - 178), (ax + 12, base - 136)], True, k=0.2),
                             paint(trim))
        c.poly([(x0 - 50, base - 196), (x0 - 30, base - 236), (x0 + 520, base - 236), (x0 + 540, base - 196)], tile)
        for (a, b, c_, d_) in wins:
            c.rect(a - 5, b - 5, c_ + 5, d_ + 5, trim, 0.9)
            c.rect(a, b, c_, d_, dark)
            c.line([((a + c_) / 2, b), ((a + c_) / 2, d_)], "#3a342e", 2)
        for k, on in enumerate(p.get("lit", (1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1))):
            if on and k < len(wins):
                a, b, c_, d_ = wins[k]
                lights.rect(a, b, c_, d_, WARM, 0.6)
        comp(img, c.rgba())
        self.img = img
        self.lights = lights.rgba()[..., :3]


class PlowField(Shot):
    """A walking plow standing in a furrowed field at dawn, a factory with smokestacks far off."""
    focus = (480, 1000)
    fog_d = 0.1
    fog_color = "#c0a088"

    def __init__(self, p=None):
        super().__init__(p)
        img = sky(DAWN, 981 + self.seed, stars=0, clouds=0.35)
        c = cv()
        for k in range(6):                                                               # the plow works, far off
            bx = 520 + k * 96
            c.rect(bx, 930, bx + 96, 1000, "#15100e")
            c.poly([(bx, 930), (bx + 66, 900), (bx + 96, 930)], "#0c0908")
        self.stacks = [(600, 760), (820, 800), (1000, 780)]
        for sx, sy in self.stacks:
            c.poly([(sx - 14, 930), (sx - 9, sy), (sx + 9, sy), (sx + 14, 930)], "#0d0908")
        c.poly([(-20, 1000), (W + 20, 1000), (W + 20, H), (-20, H)], "#1a130d")
        for k in range(14):                                                              # furrows running away
            x = -500 + k * 150
            c.line([(x, H - 400), (540 + (x - 540) * 0.1, 1002)], "#0c0806", 5, 0.8)
        x, y, col = 430, 1230, "#07080a"                                                 # the plow
        c.line([(x - 150, y - 190), (x - 40, y - 60), (x + 150, y - 70)], col, 10)        # handle and beam
        c.line([(x - 190, y - 170), (x - 70, y - 50)], col, 9)
        c.line([(x - 150, y - 190), (x - 190, y - 170)], col, 7)
        c.c.drawPath(smooth_path([(x - 60, y - 56), (x + 40, y - 70), (x + 96, y), (x - 20, y - 6)], True, k=0.25),
                     paint("#9aa0a8"))                                                   # the chilled moldboard
        c.poly([(x + 40, y - 70), (x + 120, y + 4), (x + 60, y)], "#c0c6cc")              # the share
        c.line([(x + 150, y - 70), (x + 176, y - 20)], col, 7)                            # the clevis and wheel
        c.circle(x + 176, y - 6, 22, col)
        c.circle(x + 176, y - 6, 12, "#1a130d")
        comp(img, c.rgba())
        self.img = img
        self.smoke = Fog(seed=983, scale=140, color="#5a4a40", density=0.4, top=0.3, bottom=0.5, speed=30, w=W, h=H)

    def animate(self, out, t, u):
        self.smoke.apply(out, t)


K.KINDS.update({"skijump": SkiJump, "airliner": Airliner, "oldtown": OldTown, "bridge": TrussBridge, "steamer": Steamer,
                "wreck": Wreck, "propeller": Propeller, "fieldstone": Fieldstone, "plowfield": PlowField})
K.AMBIENCE.update({"skijump": ("waves", "wind"), "airliner": ("wind", None), "oldtown": ("wind", "bell"),
                   "bridge": ("wind", None), "steamer": ("waves", "foghorn"), "wreck": ("room", None),
                   "propeller": ("waves", None), "fieldstone": ("wind", "creak"), "plowfield": ("wind", None)})
