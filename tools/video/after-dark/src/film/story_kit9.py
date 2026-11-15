"""Props for the Wanatah short (the Wanatah Bank, 1901), added Nov. 15, 2026. They register in story_kit3.PROPS
like every prop, so a storyboard names them in "props": [{"p": "bankblock", ...}].

    bankblock    a two-storey brick bank block of about 1890: corbelled cornice, three arched upper windows, a big
                 front window with a gilt border and no words (name="..." letters it in gilt, only if the real sign's
                 words are known) and a recessed door with a transom.
                 lit=0..1 lights the upper windows; front=True lights the front window; shade=True pulls the blind
                 down inside the front window; door="shut" | "open"; flip=True puts the door on the left
    storefront   a frame store with a false front and an awning, no lettering (storeys=1 | 2, lit=0..1, seed)
    vault        a bank vault door in a heavy frame: square steel door, a combination dial, a spoked handle wheel,
                 two big hinges and a thin painted border. No maker's name. glint=0..1 a moonlit highlight
    tellercage   a teller's counter with a brass grille, an arched window in it and a closed ledger on the counter
    barwindow    a tall window with iron bars; moonlight comes through and lies on the floor (drop= the distance in
                 px from the window's foot down to the floor line, so the pale patch lands on the floor)
    desk         a writing desk with an oil lamp, papers that show only unreadable lines, an inkwell and pen, and a
                 chair pulled up to it
    hitchrail    a hitching rail on two posts at the edge of a board sidewalk

People are small anonymous silhouettes. Nothing shows a body, a real person's likeness or a brand. The 1901 papers
don't describe the Wanatah Bank's building or its sign, so the short draws a generic bank block with no lettering.
"""
import math

import numpy as np

import story_kit3 as K3
import story_kit8 as K8
from story_kit import WARM
from core import smooth_path, paint

prop = K3.prop
BRICK = "#2b1611"
BRICK_D = "#1e0f0b"
STONE = "#4a4038"
IRON = "#120e0c"
GILT = "#cfa54e"
STEEL = "#4b4e50"
STEEL_D = "#2c2e30"
STEEL_L = "#7a7e80"
BRASS = "#8a7038"
WOOD = "#24160e"
WOOD_D = "#170d08"


def _arch_win(c, L, cx, top, bot, w, on, k=0.5, hood=True):
    """A tall window with a round-arched head: top is the arch's crown, bot the sill."""
    r = w / 2
    pts = [(cx - r, bot), (cx - r, top + r)]
    pts += [(cx - r * math.cos(math.pi * t / 12), top + r - r * math.sin(math.pi * t / 12)) for t in range(13)]
    pts += [(cx + r, top + r), (cx + r, bot)]
    c.poly(pts, "#070606")
    if on:
        L.poly(pts, WARM, k)
    c.line([(cx, top + 2), (cx, bot)], "#1a100c", 3)
    c.line([(cx - r, top + r + (bot - top - r) * 0.45), (cx + r, top + r + (bot - top - r) * 0.45)], "#1a100c", 3)
    if hood:
        hp = [(cx - (r + 10) * math.cos(math.pi * t / 12), top + r - (r + 10) * math.sin(math.pi * t / 12)) for t in range(13)]
        c.line(hp, STONE, 7, 0.9)
    c.rect(cx - r - 8, bot, cx + r + 8, bot + 9, STONE, 0.9)


@prop
def bankblock(c, L, x, y, s=1.0, name="", lit=0.6, front=False, shade=False, door="shut", flip=False,
              seed=2, ornament=True, **k):
    """A two-storey brick bank block of about 1890 (see the top of this file)."""
    d = -1 if flip else 1
    r = np.random.default_rng(seed)
    x0, x1 = x - 230 * s, x + 230 * s
    top = y - 470 * s
    c.rect(x0, top, x1, y, BRICK)
    for j in range(int(470 * s / (9 * s))):                                       # brick courses
        yy = y - j * 9 * s
        c.line([(x0, yy), (x1, yy)], BRICK_D, 1.0, 0.55)
    for j in range(60):                                                          # a few darker bricks
        bx = x0 + r.uniform(0, 460 * s)
        by = top + r.uniform(10, 460) * s
        c.rect(bx, by, bx + 14 * s, by + 7 * s, "#170a07", 0.5)
    # cornice: corbel table, dentils, a projecting cap and a raised centre parapet
    c.rect(x0 - 6 * s, top - 18 * s, x1 + 6 * s, top, "#1a0d0a")
    for j in range(23):
        dx = x0 + (6 + j * 20) * s
        c.rect(dx, top - 10 * s, dx + 10 * s, top + 4 * s, "#140907")
    c.rect(x0 - 14 * s, top - 34 * s, x1 + 14 * s, top - 18 * s, "#0f0807")
    c.poly([(x - 90 * s, top - 34 * s), (x - 70 * s, top - 74 * s), (x + 70 * s, top - 74 * s), (x + 90 * s, top - 34 * s)],
           BRICK)
    c.rect(x - 80 * s, top - 82 * s, x + 80 * s, top - 72 * s, "#0f0807")
    c.rect(x - 46 * s, top - 64 * s, x + 46 * s, top - 42 * s, "#1a0d0a")       # a blank stone panel
    out = []
    # upper floor: three arched windows
    for j, wx in enumerate((-140, 0, 140)):
        on = r.uniform() < lit
        _arch_win(c, L, x + wx * s, y - 430 * s, y - 286 * s, 66 * s, on)
        if on:
            out.append((x + wx * s, y - 340 * s, (1.0, 0.76, 0.45), 60 * s, True, 0.3))
    # the cast-iron storefront: a beam, pilasters, the front window, the door and a narrow side window
    c.rect(x0, y - 250 * s, x1, y - 232 * s, IRON)
    for px in (-226, -40, 120, 226):
        c.rect(x + d * px * s - 7 * s, y - 232 * s, x + d * px * s + 7 * s, y, IRON)
    wa, wb = sorted((x + d * -212 * s, x + d * -56 * s))
    c.rect(wa, y - 214 * s, wb, y - 44 * s, "#06070a")
    if front:
        L.rect(wa, y - 214 * s, wb, y - 44 * s, WARM, 0.42)
    if shade:
        c.rect(wa + 4 * s, y - 210 * s, wb - 4 * s, y - 92 * s, "#3a3222")
        c.line([(wa + 4 * s, y - 92 * s), (wb - 4 * s, y - 92 * s)], "#1a150c", 4 * s)
        c.circle((wa + wb) / 2, y - 80 * s, 5 * s, "#6a5a3a")
    c.line([((wa + wb) / 2, y - 214 * s), ((wa + wb) / 2, y - 44 * s)], IRON, 4 * s)
    c.rect(wa, y - 44 * s, wb, y - 8 * s, "#0d0b0a")                              # kick plate
    if name:
        words = name.split()
        lines = [" ".join(words[:-1]), words[-1]] if len(words) > 1 else words
        for i, t in enumerate(lines):
            K8._text(c, t, (wa + wb) / 2, y - (178 - i * 40) * s, 30 * s, GILT, "OldStandard-Bold.ttf")
    elif ornament:                                  # a gilt border with no words (what the real sign said is unknown)
        mx = (wa + wb) / 2
        arc = [(mx - 62 * s * math.cos(math.pi * t / 16), y - 150 * s - 26 * s * math.sin(math.pi * t / 16))
               for t in range(17)]
        c.line(arc, GILT, 2.4 * s, 0.85)
        c.line([(p[0], p[1] + 9 * s) for p in arc], GILT, 1.4 * s, 0.6)
        c.line([(mx - 62 * s, y - 150 * s), (mx + 62 * s, y - 150 * s)], GILT, 1.4 * s, 0.6)
        c.circle(mx, y - 186 * s, 4 * s, GILT, 0.85)
    da, db = sorted((x + d * -14 * s, x + d * 92 * s))
    c.rect(da - 6 * s, y - 232 * s, db + 6 * s, y, "#0b0807")                     # the recess
    c.rect(da, y - 226 * s, db, y - 196 * s, "#06070a")                             # transom
    c.line([((da + db) / 2, y - 226 * s), ((da + db) / 2, y - 196 * s)], IRON, 2 * s)
    if door == "open":
        L.rect(da + 8 * s, y - 190 * s, db - 8 * s, y - 6 * s, WARM, 0.6)
        c.rect(da + 8 * s, y - 190 * s, da + 26 * s, y - 6 * s, "#1c120c")
    else:
        c.rect(da + 8 * s, y - 190 * s, db - 8 * s, y - 6 * s, "#1c120c")
        c.rect(da + 18 * s, y - 176 * s, db - 18 * s, y - 104 * s, "#06070a")       # the door's glass
        c.rect(da + 18 * s, y - 88 * s, db - 18 * s, y - 20 * s, "#140c08")
        c.circle(db - 18 * s if d > 0 else da + 18 * s, y - 96 * s, 4 * s, BRASS)
    c.rect(da - 16 * s, y - 6 * s, db + 16 * s, y + 6 * s, STONE, 0.9)              # the step
    sa, sb = sorted((x + d * 136 * s, x + d * 212 * s))
    c.rect(sa, y - 214 * s, sb, y - 60 * s, "#06070a")
    c.rect(sa - 4 * s, y - 60 * s, sb + 4 * s, y - 52 * s, STONE, 0.9)
    return out


@prop
def storefront(c, L, x, y, s=1.0, storeys=1, lit=0.5, seed=0, **k):
    """A frame store with a false front and an awning, no lettering."""
    r = np.random.default_rng(seed)
    hh = (300 if storeys == 1 else 420) * s
    x0, x1 = x - 150 * s, x + 150 * s
    wall = ("#15130f", "#12110e", "#17140f")[seed % 3]
    c.rect(x0, y - hh, x1, y, wall)
    for j in range(int(hh / (12 * s))):
        c.line([(x0, y - j * 12 * s), (x1, y - j * 12 * s)], "#0c0b09", 1.0, 0.7)
    step = (24 + 10 * (seed % 2)) * s                                              # the stepped false front
    c.rect(x0 - 8 * s, y - hh - 14 * s, x1 + 8 * s, y - hh, "#0b0a08")
    c.rect(x - 70 * s, y - hh - step, x + 70 * s, y - hh, wall)
    c.rect(x - 78 * s, y - hh - step - 10 * s, x + 78 * s, y - hh - step, "#0b0a08")
    c.rect(x - 110 * s, y - hh + 26 * s, x + 110 * s, y - hh + 70 * s, "#100e0b")    # a blank sign board
    out = []
    if storeys == 2:
        for wx in (-80, 80):
            on = r.uniform() < lit
            K3._win(c, L, x + (wx - 26) * s, y - 360 * s, x + (wx + 26) * s, y - 250 * s, on)
            if on:
                out.append((x + wx * s, y - 300 * s, (1.0, 0.76, 0.45), 50 * s, True, 0.3))
    c.poly([(x0 - 10 * s, y - 196 * s), (x1 + 10 * s, y - 196 * s), (x1 + 30 * s, y - 160 * s), (x0 - 30 * s, y - 160 * s)],
           "#0a0908")                                                              # the awning
    for px in (-170, 170):
        c.line([(x + px * s, y - 160 * s), (x + px * s, y)], "#0a0908", 5 * s)
    on = r.uniform() < lit
    for wx in ((-130, -40), (40, 130)):
        K3._win(c, L, x + wx[0] * s, y - 150 * s, x + wx[1] * s, y - 40 * s, on, k=0.45)
    c.rect(x - 26 * s, y - 150 * s, x + 26 * s, y, "#0a0807")
    return out


@prop
def vault(c, L, x, y, s=1.0, glint=0.5, **k):
    """A bank vault door in a heavy frame (see the top of this file)."""
    c.rect(x - 236 * s, y - 590 * s, x + 236 * s, y, "#2a2926")                    # the frame in the wall
    c.rect(x - 236 * s, y - 590 * s, x + 236 * s, y - 572 * s, "#3a3934")
    c.rect(x - 206 * s, y - 560 * s, x + 206 * s, y - 14 * s, "#0c0c0c")
    c.rect(x - 196 * s, y - 552 * s, x + 196 * s, y - 22 * s, STEEL, r=18 * s)     # the door
    c.rect(x - 170 * s, y - 526 * s, x + 170 * s, y - 48 * s, STEEL_D, r=14 * s)
    c.rect(x - 162 * s, y - 518 * s, x + 162 * s, y - 56 * s, STEEL, r=12 * s)
    c.rect(x - 148 * s, y - 504 * s, x + 148 * s, y - 70 * s, GILT, 0.5, r=10 * s)  # thin painted border
    c.rect(x - 144 * s, y - 500 * s, x + 144 * s, y - 74 * s, STEEL, r=9 * s)
    for hy in (-470, -110):                                                      # hinges
        c.rect(x - 222 * s, y + (hy - 46) * s, x - 192 * s, y + (hy + 46) * s, STEEL_D, r=10 * s)
        c.line([(x - 207 * s, y + (hy - 40) * s), (x - 207 * s, y + (hy + 40) * s)], STEEL_L, 3 * s, 0.6)
    dx, dy = x - 20 * s, y - 330 * s                                             # combination dial
    c.circle(dx, dy, 52 * s, STEEL_D)
    c.circle(dx, dy, 44 * s, "#8a8c88")
    for t in range(40):
        a = 2 * math.pi * t / 40
        r0 = (34 if t % 5 else 30) * s
        c.line([(dx + r0 * math.cos(a), dy + r0 * math.sin(a)), (dx + 42 * s * math.cos(a), dy + 42 * s * math.sin(a))],
               "#2a2a28", 1.6 * s)
    c.circle(dx, dy, 18 * s, "#5a5c5a")
    c.poly([(dx - 6 * s, dy - 62 * s), (dx + 6 * s, dy - 62 * s), (dx, dy - 52 * s)], GILT)
    hx, hy = x + 80 * s, y - 230 * s                                             # the handle wheel
    c.circle(hx, hy, 12 * s, STEEL_L)
    for t in range(5):
        a = 2 * math.pi * t / 5 - math.pi / 2
        ex, ey = hx + 70 * s * math.cos(a), hy + 70 * s * math.sin(a)
        c.line([(hx, hy), (ex, ey)], STEEL_L, 9 * s)
        c.circle(ex, ey, 12 * s, "#9a9c98")
    c.rect(x + 110 * s, y - 420 * s, x + 130 * s, y - 380 * s, STEEL_D)             # bolt-work housing
    if glint > 0:
        c.poly([(x - 120 * s, y - 552 * s), (x - 40 * s, y - 552 * s), (x + 120 * s, y - 22 * s), (x + 40 * s, y - 22 * s)],
               "#c8d4dc", 0.10 * glint)
        L.poly([(x - 120 * s, y - 552 * s), (x - 40 * s, y - 552 * s), (x + 120 * s, y - 22 * s), (x + 40 * s, y - 22 * s)],
               "#6a8aa8", 0.18 * glint)
    c.rect(x - 220 * s, y - 14 * s, x + 220 * s, y, "#1a1a18")                     # the sill
    return []


@prop
def tellercage(c, L, x, y, s=1.0, **k):
    """A teller's counter with a brass grille, an arched window and a closed ledger."""
    c.rect(x - 280 * s, y - 210 * s, x + 280 * s, y, WOOD)
    c.rect(x - 292 * s, y - 226 * s, x + 292 * s, y - 206 * s, "#3a2416")
    for px in range(-240, 260, 120):
        c.rect(x + (px - 44) * s, y - 180 * s, x + (px + 44) * s, y - 40 * s, WOOD_D)
    gy0, gy1 = y - 226 * s, y - 470 * s
    c.rect(x - 280 * s, gy1 - 16 * s, x + 280 * s, gy1, "#3a2416")                # the grille's header
    wx0, wx1 = x - 60 * s, x + 60 * s
    for j in range(int(560 / 18) + 1):
        bx = x - 280 * s + j * 18 * s
        if wx0 < bx < wx1:
            continue
        c.line([(bx, gy0), (bx, gy1)], BRASS, 3 * s, 0.9)
    c.line([(x - 280 * s, gy0 - 120 * s), (x + 280 * s, gy0 - 120 * s)], BRASS, 3 * s, 0.7)
    arch = [(wx0, gy0)] + [(x - 60 * s * math.cos(math.pi * t / 12), gy0 - 150 * s - 60 * s * math.sin(math.pi * t / 12))
                           for t in range(13)] + [(wx1, gy0)]
    c.line(arch, BRASS, 5 * s)
    c.rect(wx0 - 10 * s, gy0 - 8 * s, wx1 + 10 * s, gy0 + 4 * s, "#4a3020")       # the window's ledge
    lx, ly = x - 190 * s, y - 226 * s                                             # a closed ledger
    c.rect(lx - 54 * s, ly - 26 * s, lx + 54 * s, ly, "#3a1a12")
    c.rect(lx - 50 * s, ly - 22 * s, lx + 50 * s, ly - 6 * s, "#b8ac90", 0.8)
    c.rect(lx - 54 * s, ly - 30 * s, lx + 54 * s, ly - 24 * s, "#4a2216")
    return []


@prop
def barwindow(c, L, x, y, s=1.0, drop=180, moon=False, **k):
    """A tall window with iron bars and the moonlight it lets onto the floor."""
    w, h = 90 * s, 380 * s
    c.rect(x - w - 10 * s, y - h - 10 * s, x + w + 10 * s, y + 10 * s, "#2a1c14")
    c.rect(x - w, y - h, x + w, y, "#0e1824")
    L.rect(x - w, y - h, x + w, y, "#6a8aa8", 0.28)
    if moon:
        c.circle(x + 30 * s, y - h + 90 * s, 26 * s, "#d8dccc", 0.8)
        L.circle(x + 30 * s, y - h + 90 * s, 26 * s, "#a8b8c8", 0.4)
    c.line([(x - w, y - h * 0.5), (x + w, y - h * 0.5)], "#2a1c14", 6 * s)
    c.line([(x, y - h), (x, y)], "#2a1c14", 6 * s)
    for j in range(7):
        bx = x - w + (j + 0.5) * (2 * w / 7)
        c.line([(bx, y - h), (bx, y)], IRON, 7 * s)
    fy = y + drop
    patch = [(x - w, fy + 10 * s), (x + w, fy + 10 * s), (x + w - 120 * s, fy + 200 * s), (x - w - 160 * s, fy + 200 * s)]
    c.poly(patch, "#8aa0b4", 0.05, blur=10)
    L.poly(patch, "#6a8aa8", 0.10, blur=14)
    for j in range(7):
        bx = x - w + (j + 0.5) * (2 * w / 7)
        c.line([(bx, fy + 10 * s), (bx - 140 * s, fy + 200 * s)], "#000000", 6 * s, 0.18, blur=3)
    return []


@prop
def desk(c, L, x, y, s=1.0, lamp=True, **k):
    """A writing desk with an oil lamp, unreadable papers, an inkwell and pen, and a chair."""
    c.rect(x - 250 * s, y - 196 * s, x + 250 * s, y - 176 * s, "#3a2416")           # the top
    c.rect(x - 250 * s, y - 176 * s, x - 90 * s, y, WOOD)                          # pedestal with drawers
    for j in range(3):
        c.rect(x - 238 * s, y - (166 - j * 56) * s, x - 102 * s, y - (120 - j * 56) * s, WOOD_D)
        c.circle(x - 170 * s, y - (143 - j * 56) * s, 4 * s, BRASS)
    c.rect(x + 214 * s, y - 176 * s, x + 238 * s, y, WOOD)
    c.rect(x - 90 * s, y - 176 * s, x + 214 * s, y - 150 * s, WOOD_D)               # the apron
    for j, (px, rot) in enumerate(((-40, -0.05), (10, 0.04), (60, -0.02))):         # papers, unreadable lines
        pw, ph = 74 * s, 16 * s
        cx, cy = x + px * s, y - 198 * s - j * 2 * s
        pts = [(-pw, -ph), (pw, -ph), (pw, ph), (-pw, ph)]
        ca, sa = math.cos(rot), math.sin(rot)
        c.poly([(cx + a * ca - b * sa, cy + a * sa + b * ca) for a, b in pts], "#cfc6ae", 0.92)
        for t in range(3):
            yy = -8 + t * 7
            c.line([(cx + (-60 * s) * ca - yy * s * sa, cy + (-60 * s) * sa + yy * s * ca),
                    (cx + (50 * s) * ca - yy * s * sa, cy + (50 * s) * sa + yy * s * ca)], "#6a6250", 1.4 * s, 0.6)
    c.rect(x + 120 * s, y - 222 * s, x + 146 * s, y - 196 * s, "#0c0c10")            # inkwell
    c.line([(x + 132 * s, y - 222 * s), (x + 110 * s, y - 270 * s)], "#d8d0b8", 3 * s)  # pen
    out = []
    if lamp:
        lx = x - 170 * s
        c.ellipse(lx, y - 200 * s, 40 * s, 10 * s, BRASS)
        c.poly([(lx - 30 * s, y - 202 * s), (lx + 30 * s, y - 202 * s), (lx + 22 * s, y - 250 * s), (lx - 22 * s, y - 250 * s)],
               "#6a5428")
        c.rect(lx - 8 * s, y - 262 * s, lx + 8 * s, y - 250 * s, BRASS)
        c.c.drawPath(smooth_path([(lx - 12 * s, y - 262 * s), (lx - 20 * s, y - 300 * s), (lx - 12 * s, y - 340 * s),
                                  (lx + 12 * s, y - 340 * s), (lx + 20 * s, y - 300 * s), (lx + 12 * s, y - 262 * s)], True),
                     paint("#e8dcc0", 0.35))
        c.ellipse(lx, y - 296 * s, 6 * s, 14 * s, "#ffd890", 0.9)
        out.append((lx, y - 300 * s, (1.0, 0.72, 0.38), 260 * s, True, 0.75))
    ch = x + 120 * s                                                              # the chair, pulled up
    c.rect(ch - 60 * s, y - 120 * s, ch + 60 * s, y - 100 * s, "#120a06")
    c.rect(ch - 56 * s, y - 100 * s, ch - 46 * s, y + 30 * s, "#120a06")
    c.rect(ch + 46 * s, y - 100 * s, ch + 56 * s, y + 30 * s, "#120a06")
    c.rect(ch + 40 * s, y - 330 * s, ch + 58 * s, y - 104 * s, "#120a06")
    c.rect(ch - 58 * s, y - 330 * s, ch - 40 * s, y - 104 * s, "#120a06")
    c.rect(ch - 58 * s, y - 330 * s, ch + 58 * s, y - 300 * s, "#120a06")
    c.rect(ch - 58 * s, y - 250 * s, ch + 58 * s, y - 236 * s, "#120a06")
    return out


@prop
def hitchrail(c, L, x, y, s=1.0, w=240, **k):
    """A hitching rail on two posts at the edge of a board sidewalk."""
    c.rect(x - (w + 40) * s, y - 8 * s, x + (w + 40) * s, y + 6 * s, "#1a1612")
    for j in range(int((w + 40) * 2 / 26)):
        bx = x - (w + 40) * s + j * 26 * s
        c.line([(bx, y - 8 * s), (bx, y + 6 * s)], "#0c0a08", 1.2, 0.8)
    for px in (-w, w):
        c.rect(x + px * s - 6 * s, y - 96 * s, x + px * s + 6 * s, y - 8 * s, "#0c0a08")
    c.rect(x - w * s - 10 * s, y - 100 * s, x + w * s + 10 * s, y - 90 * s, "#0c0a08")
    return []
