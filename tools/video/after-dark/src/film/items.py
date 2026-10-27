"""Scene items: things that draw themselves into a Ctx (painting, light layers,
per-frame painters)."""
import math

import cv2
import numpy as np
import skia

from core import (OW, OH, W, H, Canvas, rgb, mix, c4, clamp01, smoothstep, sstep, fbm, noise1d, add_spot, poly_path,
                  smooth_path, paint, lin, rad, ADD, SCREEN, MULT, ERASE, Flame, Embers, Motes, flicker, Noise1,
                  _noise_for, light_map, blur, warp_pts, ease, MOON, AMBER, GHOST, EMBER)
from art import (comp, sky, hills, fog_band, tree, grass, reeds, farmhouse, church, lancet, gravestones, fence,
                 hooded_figure, person, sheet_ghost, bat, crow, pumpkin, carve, turnip, candle, candle_flame, skull,
                 rim_shape, vgrad, ridge)
from scene import flick, ramp, times, const

DARK = "#04080a"
RIM = "#3e5c5a"


# ----------------------------------------------------------------------------- environment

def night(ctx, moon=(1600, 260, 62), seed=0, clouds=0.45, stops=None, warm_horizon=None, stars=420, moon_glow=0.55,
          star_max_y=0.75, cloud_band=(0.0, 0.7)):
    ctx.bg = sky(moon=moon, seed=seed, clouds=clouds, stops=stops, warm_horizon=warm_horizon, stars=stars,
                 moon_glow=moon_glow, star_max_y=star_max_y, cloud_band=cloud_band)


def dusk(ctx, sun=None, seed=0, glow="#ff8a3d", clouds=0.35, dark=0.0):
    """Late-evening sky: deep blue overhead, ember-orange at the horizon. dark 0..1 deepens it."""
    stops = [(0.0, mix("#0d1b2e", "#03070c", dark)), (0.45, mix("#2b3550", "#0b1220", dark)),
             (0.72, mix("#7a4a52", "#2a2230", dark)), (0.86, mix("#d77a45", "#5a3024", dark)),
             (1.0, mix("#f2a65a", "#7a3d22", dark))]
    ctx.bg = sky(moon=None, seed=seed, clouds=clouds, stops=stops, stars=int(120 + 300 * dark), star_max_y=0.45,
                 cloud_color=mix("#3a2f3c", "#141824", dark), cloud_lit=mix("#ff9a5a", "#6a3a2a", dark),
                 cloud_band=(0.1, 0.75))
    if sun:
        sx, sy, sr = sun
        yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
        d = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
        ctx.bg += (np.exp(-d / 420) * 0.55)[..., None] * rgb("#ff9a4a")
        ctx.bg += (np.exp(-d / 90) * 0.6)[..., None] * rgb("#ffd08a")
        disc = smoothstep(sr, sr - 2, d)
        ctx.bg = ctx.bg * (1 - disc[..., None]) + disc[..., None] * rgb("#ffe2a8")


def hill(ctx, base, amp, scale, color, seed, rim=None, rim_w=3.0, rim_a=0.4, haze=None, octaves=5):
    ctx.flush()
    return hills(ctx.bg, base, amp, scale, color, seed, rim=rim, rim_w=rim_w, rim_a=rim_a, fog=haze, octaves=octaves)


def mist(ctx, y, height, color="#7fa39e", a=0.3, seed=0, patchy=0.5):
    ctx.flush()
    fog_band(ctx.bg, y, height, color, a, seed=seed, patchy=patchy)


def ground(ctx, y0, top="#081114", bottom="#020405", feather=60):
    ctx.flush()
    y0 = int(y0)
    g = vgrad(OH - y0, OW, [(0, top), (1, bottom)])
    a = smoothstep(0, feather, np.arange(OH - y0, dtype=np.float32))[:, None, None]
    ctx.bg[y0:] = ctx.bg[y0:] * (1 - a) + g * a


def fog(ctx, front=False, **kw):
    from core import Fog
    f = Fog(**kw)
    if front:
        ctx.front_fog = f
    else:
        ctx.fog = f


# ----------------------------------------------------------------------------- fire

def bonfire(ctx, x, y, size=260, seed=0, embers=60, light_r=900, logs=True, k=1.0, plane=None, intensity=None,
            ground_light=0.55, glow=0.75):
    """Animated bonfire whose base sits at (x, y)."""
    cv = ctx.cv
    if logs:
        r = np.random.default_rng(seed)
        for i in range(7):
            a = r.uniform(-0.9, 0.9)
            L = size * r.uniform(0.6, 0.9)
            x0, y0 = x - math.sin(a) * L * 0.1, y + 6
            cv.line([(x0 - math.cos(a) * L * 0.5, y0 + 10), (x0 + math.cos(a) * L * 0.5, y0 - abs(math.sin(a)) * L * 0.4)],
                    "#120804", size * 0.07)
    fl = Flame(int(size * 1.15), int(size * 1.75), seed=seed, speed=0.9, width=0.55, wobble=0.42)
    fw, fh = fl.w, fl.h
    ints = intensity or (lambda t: 1.0)
    fk = lambda t: ints(t) * flicker(t, seed + 3, 0.18, 1.3) * k
    lc = ctx.light("fire%d" % seed, fk)
    lc.glow(x, y - size * 0.4, light_r, "#ff7a2a", 0.55 * glow)
    lc.glow(x, y - size * 0.3, size * 1.4, "#ffb35a", 0.6 * glow)
    if ground_light:
        lc.ellipse(x, y + size * 0.15, light_r * 0.75, light_r * 0.12, "#ff7a2a", 0.14 * ground_light, blur=40, mode=ADD)
    em = Embers(embers, x - size * 0.3, x + size * 0.3, y - size * 0.5, rise=size * 1.4, spread=size * 0.25,
                seed=seed + 1) if embers else None

    def draw(buf, t):
        kk = ints(t) * k
        if kk <= 0.01:
            return
        f = fl.render(t, intensity=kk * (0.85 + 0.15 * flicker(t, seed + 5, 0.5, 2.0)))
        x0, y0 = int(x - fw / 2), int(y - fh + size * 0.12)
        hh, ww = f.shape[:2]
        X0, Y0 = max(0, x0), max(0, y0)
        X1, Y1 = min(buf.shape[1], x0 + ww), min(buf.shape[0], y0 + hh)
        if X1 > X0 and Y1 > Y0:
            buf[Y0:Y1, X0:X1] += f[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
        if em:
            em.draw(buf, t, k=kk)
    (plane.dyn if plane else ctx.dyn).append(draw)
    return fk


def distant_fires(ctx, pts, seed=0, size=10):
    for i, (x, y) in enumerate(pts):
        fn = flick(seed + i, 0.35, 2.0)
        lc = ctx.light("dfire%d" % i, fn)
        lc.glow(x, y, size * 9, "#ff7a2a", 0.5)
        lc.glow(x, y - size * 0.4, size * 1.6, "#ffd08a", 0.9)


def lit_window_flicker(ctx, name, seed=0, amt=0.08):
    """Make a light layer flicker like a candle-lit room."""
    ctx.light(name, flick(seed, amt, 0.8))


# ----------------------------------------------------------------------------- moving things

def flock(ctx, kind="bat", n=5, box=(400, 150, 1800, 600), seed=0, speed=140, size=(18, 34), direction=1, dur=12):
    """Bats or crows crossing the painting (drawn in painting space)."""
    r = np.random.default_rng(seed)
    birds = []
    for i in range(n):
        birds.append(dict(x=r.uniform(box[0] - 600, box[0] + 200), y=r.uniform(box[1], box[3]),
                          s=r.uniform(*size), ph=r.uniform(0, 6.28), sp=speed * r.uniform(0.7, 1.3),
                          wob=r.uniform(10, 40), fr=r.uniform(5.5, 9) if kind == "bat" else r.uniform(2.2, 3.4),
                          delay=r.uniform(0, dur * 0.6)))

    def draw(buf, t):
        for b in birds:
            tt = t - b["delay"]
            if tt < 0:
                continue
            x = b["x"] + b["sp"] * tt * direction
            y = b["y"] + math.sin(tt * 1.3 + b["ph"]) * b["wob"]
            if not (-80 < x < OW + 80):
                continue
            flap = math.sin(tt * b["fr"] * 2 * math.pi / 2 + b["ph"])
            s = b["s"]
            if kind == "bat":
                silhouette(buf, bat_pts(x, y, s, flap), (0.008, 0.012, 0.016))
            else:
                silhouette(buf, crow_pts(x, y, s, flap, direction), (0.008, 0.01, 0.012))
    ctx.dyn.append(draw)


def bat_pts(x, y, s, flap):
    wy = -flap * 0.55
    pts = [(0, -0.12), (0.08, -0.2), (0.12, -0.05), (0.35, -0.12 + wy * 0.6), (0.62, -0.05 + wy), (1.0, -0.15 + wy * 1.2),
           (0.86, 0.06 + wy * 0.8), (0.72, 0.03 + wy * 0.6), (0.6, 0.12 + wy * 0.5), (0.45, 0.07 + wy * 0.3),
           (0.32, 0.16 + wy * 0.2), (0.12, 0.12), (0.0, 0.2)]
    full = pts + [(-px, py) for px, py in reversed(pts[1:])]
    return np.array([(x + px * s, y + py * s) for px, py in full], np.float32)


def crow_pts(x, y, s, flap, d=1):
    wy = flap * 0.6
    pts = [(-0.55, -0.02), (-0.3, -0.06), (-0.05, -0.08), (0.12, -0.55 * wy - 0.05), (0.32, -0.62 * wy - 0.08),
           (0.2, -0.04), (0.35, -0.03), (0.6, 0.0), (0.38, 0.07), (0.05, 0.09), (-0.35, 0.07)]
    return np.array([(x + px * s * d, y + py * s) for px, py in pts], np.float32)


def silhouette(buf, pts, color, a=1.0):
    x0, y0 = np.floor(pts.min(0)).astype(int) - 2
    x1, y1 = np.ceil(pts.max(0)).astype(int) + 2
    h, w = buf.shape[:2]
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if X1 <= X0 or Y1 <= Y0:
        return
    m = np.zeros((Y1 - Y0, X1 - X0), np.uint8)
    q = ((pts - [X0, Y0]) * 16).astype(np.int32)
    cv2.fillPoly(m, [q], 255, lineType=cv2.LINE_AA, shift=4)
    a_ = (m.astype(np.float32) / 255.0 * a)[..., None]
    buf[Y0:Y1, X0:X1] = buf[Y0:Y1, X0:X1] * (1 - a_) + np.array(color, np.float32) * a_


def wisps(ctx, n=6, box=(300, 600, 1900, 1000), seed=0, color=(0.55, 1.0, 0.75), size=(5, 9), k=1.0, drift=40,
          fade_in=None):
    r = np.random.default_rng(seed)
    ws = [dict(x=r.uniform(box[0], box[2]), y=r.uniform(box[1], box[3]), s=r.uniform(*size), ph=r.uniform(0, 6.28),
               f=r.uniform(0.15, 0.35)) for _ in range(n)]
    nz = Noise1(seed + 4)

    def draw(buf, t):
        kk = k * (fade_in(t) if fade_in else 1.0)
        for i, w_ in enumerate(ws):
            x = w_["x"] + nz(t * w_["f"] + i * 10, 1.0) * drift * 2
            y = w_["y"] + nz(t * w_["f"] + i * 10 + 50, 1.0) * drift
            b = (0.55 + 0.45 * math.sin(t * 1.7 + w_["ph"])) * kk
            add_spot(buf, x, y, w_["s"] * 4, color, 0.12 * b)
            add_spot(buf, x, y, w_["s"], color, 0.9 * b)
            add_spot(buf, x, y, w_["s"] * 0.4, (1, 1, 1), 0.6 * b)
    ctx.dyn.append(draw)


def ghosts(ctx, n=3, box=(500, 760, 1700, 960), seed=0, h=(150, 220), a=0.07, speed=18):
    """Faint pale figures drifting through the fog."""
    r = np.random.default_rng(seed)
    gs = [dict(x=r.uniform(box[0], box[2]), y=r.uniform(box[1], box[3]), h=r.uniform(*h), d=r.choice([-1, 1]),
               ph=r.uniform(0, 6.28)) for _ in range(n)]
    sprites = []
    for g in gs:
        c = Canvas(int(g["h"] * 0.8), int(g["h"] * 1.15))
        hooded_figure(c, c.w / 2, c.h - 4, g["h"], color="#cfe8e2")
        m = blur(c.rgba()[..., 3], 3.0)
        sprites.append(m)

    def draw(buf, t):
        for g, m in zip(gs, sprites):
            x = g["x"] + g["d"] * speed * t
            y = g["y"]
            b = a * (0.6 + 0.4 * math.sin(t * 0.7 + g["ph"]))
            hh, ww = m.shape
            x0, y0 = int(x - ww / 2), int(y - hh)
            X0, Y0 = max(0, x0), max(0, y0)
            X1, Y1 = min(buf.shape[1], x0 + ww), min(buf.shape[0], y0 + hh)
            if X1 > X0 and Y1 > Y0:
                buf[Y0:Y1, X0:X1] += m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None] * b * rgb("#cfe8e2")
    ctx.dyn.append(draw)


def leaves(ctx, n=30, seed=0, wind=220, color=(0.18, 0.08, 0.03), box=(0, 300, OW, OH)):
    r = np.random.default_rng(seed)
    ls = [dict(x=r.uniform(-400, OW), y=r.uniform(box[1], box[3]), s=r.uniform(6, 13), ph=r.uniform(0, 6.28),
               sp=r.uniform(0.6, 1.4), rot=r.uniform(2, 6)) for _ in range(n)]

    def draw(buf, t):
        for l in ls:
            x = (l["x"] + wind * l["sp"] * t) % (OW + 400) - 200
            y = l["y"] + math.sin(t * 1.4 + l["ph"]) * 40 + t * 25
            y = box[1] + (y - box[1]) % (box[3] - box[1])
            a = t * l["rot"] + l["ph"]
            s = l["s"]
            pts = np.array([(x + math.cos(a) * s, y + math.sin(a) * s * 0.5), (x + math.cos(a + 1.6) * s * 0.4, y + math.sin(a + 1.6) * s * 0.3),
                            (x - math.cos(a) * s, y - math.sin(a) * s * 0.5), (x - math.cos(a + 1.6) * s * 0.4, y - math.sin(a + 1.6) * s * 0.3)], np.float32)
            silhouette(buf, pts, color, 0.9)
    ctx.dyn.append(draw)


def rain(ctx, n=260, seed=0, angle=0.25, speed=1500, color=(0.55, 0.65, 0.7), a=0.18):
    r = np.random.default_rng(seed)
    xs, ys, ls = r.uniform(0, W, n), r.uniform(0, H, n), r.uniform(18, 40, n)

    def draw(frame, t, m):
        y = (ys + speed * t) % (H + 60) - 30
        x = (xs + speed * t * angle) % W
        for i in range(n):
            cv2.line(frame, (int(x[i]), int(y[i])), (int(x[i] - ls[i] * angle), int(y[i] - ls[i])),
                     (color[0] * a, color[1] * a, color[2] * a), 1, cv2.LINE_AA)
    ctx.post.append(draw)


def lightning(ctx, times_=(2.0,), seed=0):
    def fn(t):
        v = 0.0
        for t0 in times_:
            d = t - t0
            if 0 <= d < 0.5:
                v = max(v, math.exp(-d * 9) * (1 if d < 0.06 or 0.12 < d < 0.2 else 0.4))
        return v
    lc = ctx.light("lightning", fn)
    lc.rect(0, 0, OW, OH, "#9fb8c8", 0.55)
    return lc


# ----------------------------------------------------------------------------- landscape props

def stooks(ctx, y, x0, x1, n, seed=0, s=(70, 110), color="#05090b"):
    r = np.random.default_rng(seed)
    for x in np.sort(r.uniform(x0, x1, n)):
        h = r.uniform(*s) * (0.7 + 0.6 * (y - 700) / 600)
        w = h * 0.55
        p = smooth_path([(x - w / 2, y), (x - w * 0.32, y - h * 0.6), (x - w * 0.12, y - h), (x + w * 0.1, y - h * 1.02),
                         (x + w * 0.35, y - h * 0.6), (x + w / 2, y)], True)
        ctx.cv.c.drawPath(p, paint(color))
        ctx.cv.line([(x - w * 0.05, y - h), (x - w * 0.25, y - h * 1.18)], color, 3)
        ctx.cv.line([(x + w * 0.05, y - h), (x + w * 0.22, y - h * 1.16)], color, 3)


def dolmen(ctx, x, y, s=1.0, glow_fn=None, color="#060b0d", rim="#4a6a66"):
    cv = ctx.cv
    st = [poly_path([(x - 170 * s, y), (x - 180 * s, y - 230 * s), (x - 140 * s, y - 270 * s), (x - 95 * s, y - 250 * s),
                     (x - 90 * s, y)]),
          poly_path([(x + 90 * s, y), (x + 85 * s, y - 250 * s), (x + 130 * s, y - 280 * s), (x + 175 * s, y - 240 * s),
                     (x + 180 * s, y)]),
          poly_path([(x - 230 * s, y - 250 * s), (x - 120 * s, y - 330 * s), (x + 150 * s, y - 345 * s),
                     (x + 250 * s, y - 300 * s), (x + 220 * s, y - 255 * s), (x + 60 * s, y - 262 * s),
                     (x - 150 * s, y - 238 * s)])]
    lc = ctx.light("portal", glow_fn or const(1.0))
    gp = poly_path([(x - 92 * s, y), (x - 95 * s, y - 248 * s), (x + 86 * s, y - 252 * s), (x + 88 * s, y)])
    lc.c.drawPath(gp, paint(GHOST, 0.55, blur=18 * s))
    lc.glow(x, y - 120 * s, 520 * s, GHOST, 0.45)
    lc.glow(x, y - 100 * s, 180 * s, "#d8ffe9", 0.55)
    for p in st:
        rim_shape(cv, p, color, rim, (4 * s, 4 * s))
        ctx.occlude(p)


def mound(ctx, x, y, w, h, color="#071012", rim="#3a5a52", door_fn=None):
    cv = ctx.cv
    p = smooth_path([(x - w / 2, y), (x - w * 0.3, y - h * 0.8), (x, y - h), (x + w * 0.3, y - h * 0.8), (x + w / 2, y)], True)
    rim_shape(cv, p, color, rim, (4, 4))
    door = poly_path([(x - 40, y), (x - 40, y - 70), (x - 25, y - 95), (x + 25, y - 95), (x + 40, y - 70), (x + 40, y)])
    cv.c.drawPath(door, paint("#020403"))
    lc = ctx.light("mound", door_fn or const(1.0))
    lc.c.drawPath(door, paint(GHOST, 0.5, blur=6))
    lc.glow(x, y - 50, 340, GHOST, 0.3)
    grass(cv, y + 4, x - w / 2, x + w / 2, color, n=300, hmin=8, hmax=26, seed=3)


def road(ctx, vx, vy, bw=1300, color="#0b1416", rut="#060b0d", y_bottom=OH):
    cv = ctx.cv
    p = poly_path([(vx - 8, vy), (vx + 8, vy), (vx + bw / 2, y_bottom), (vx - bw / 2, y_bottom)])
    sh = lin((0, vy), (0, y_bottom), [("#22383a", 1), (color, 1), ("#050a0b", 1)], [0, 0.4, 1])
    cv.c.drawPath(p, paint(None, shader=sh))
    for off in (-0.22, 0.22):
        cv.line([(vx + off * 10, vy + 4), (vx + off * bw * 0.8, y_bottom)], rut, 10, a=0.6)


def roadside_posts(ctx, vx, vy, side=1, n=12, color=DARK, y_bottom=OH, spread=760):
    for i in range(n):
        f = (i + 1) / n
        f = f ** 1.8
        x = vx + side * (14 + spread * f)
        y = vy + (y_bottom - vy) * f
        h = 6 + 230 * f
        w = 2 + 16 * f
        ctx.cv.rect(x - w / 2, y - h, x + w / 2, y, color)


def approaching_light(ctx, vx, vy, t_total=8.0, color="#ffcf8a"):
    nz = Noise1(91)

    def draw(buf, t):
        f = min(1.0, t / t_total) * 0.18 + 0.02
        x = vx + nz(t, 0.4) * 6
        y = vy + 30 + f * 200
        bob = math.sin(t * 5.5) * 1.5
        k = 0.6 + 0.4 * flicker(t, 33, 0.3, 2)
        add_spot(buf, x, y + bob, 18 + f * 30, (1.0, 0.7, 0.35), 0.10 * k)
        add_spot(buf, x, y + bob, 2.5 + f * 6, (1.0, 0.85, 0.6), 0.9 * k)
    ctx.dyn.append(draw)


def cottage(ctx, x, y, s=1.0, lit=1.0, name="cottage", dark=DARK, rim=RIM, door_lit=False, fn=None):
    cv = ctx.cv
    w, h = 340 * s, 150 * s
    body = poly_path([(x, y), (x, y - h), (x + w, y - h), (x + w, y)])
    rim_shape(cv, body, dark, rim, (3 * s, 3 * s))
    thatch = smooth_path([(x - 30 * s, y - h + 10 * s), (x + 20 * s, y - h - 120 * s), (x + w * 0.5, y - h - 150 * s),
                          (x + w - 20 * s, y - h - 120 * s), (x + w + 30 * s, y - h + 10 * s)], True)
    rim_shape(cv, thatch, "#06090a", rim, (3 * s, 3 * s))
    cv.rect(x + w * 0.72, y - h - 160 * s, x + w * 0.8, y - h - 90 * s, dark)
    lc = ctx.light(name, fn or flick(int(x) % 97, 0.1, 0.8))
    for wx in (x + w * 0.15, x + w * 0.62):
        cv.rect(wx, y - h * 0.7, wx + 50 * s, y - h * 0.3, "#3a2410")
        lc.rect(wx, y - h * 0.7, wx + 50 * s, y - h * 0.3, AMBER, 0.9 * lit)
        lc.glow(wx + 25 * s, y - h * 0.5, 160 * s, AMBER, 0.28 * lit)
        lc.rect(wx + 23 * s, y - h * 0.7, wx + 27 * s, y - h * 0.3, "#000000")
    dx = x + w * 0.4
    cv.rect(dx, y - h * 0.62, dx + 55 * s, y, "#120a05")
    if door_lit:
        lc.rect(dx, y - h * 0.62, dx + 55 * s, y, AMBER, 0.75 * lit)
        lc.c.drawPath(poly_path([(dx, y), (dx + 55 * s, y), (dx + 140 * s, y + 90 * s), (dx - 60 * s, y + 90 * s)]),
                      paint(AMBER, 0.18 * lit, blur=10 * s))


def gate(ctx, x, y, s=1.0, light=True):
    cv = ctx.cv
    for px in (x - 210 * s, x + 150 * s):
        p = poly_path([(px, y), (px, y - 380 * s), (px + 60 * s, y - 380 * s), (px + 60 * s, y)])
        rim_shape(cv, p, DARK, RIM, (3 * s, 3 * s))
        cv.rect(px - 8 * s, y - 400 * s, px + 68 * s, y - 380 * s, DARK)
    if light:
        lc = ctx.light("beyond", flick(5, 0.05, 0.3))
        lc.glow(x, y - 200 * s, 600 * s, "#f6e7c0", 0.55)
        lc.glow(x, y - 200 * s, 200 * s, "#fffaf0", 0.65)
    bars = skia.Path()
    for i in range(13):
        bx = x - 150 * s + i * 23 * s
        top = y - 330 * s - 30 * s * math.sin(math.pi * i / 12)
        cv.line([(bx, y), (bx, top)], "#020304", 6 * s)
        cv.poly([(bx - 7 * s, top), (bx, top - 22 * s), (bx + 7 * s, top)], "#020304")
        if light:
            pp = poly_path([(bx - 3 * s, y), (bx - 3 * s, top - 22 * s), (bx + 3 * s, top - 22 * s), (bx + 3 * s, y)])
            ctx.occlude(pp)
    for yy in (y - 60 * s, y - 250 * s):
        cv.line([(x - 152 * s, yy), (x + 150 * s, yy)], "#020304", 8 * s)
        if light:
            ctx.occlude(poly_path([(x - 152 * s, yy - 4 * s), (x + 150 * s, yy - 4 * s), (x + 150 * s, yy + 4 * s), (x - 152 * s, yy + 4 * s)]))


def signpost(ctx, x, y, s=1.0):
    cv = ctx.cv
    cv.rect(x - 7 * s, y - 330 * s, x + 7 * s, y, DARK)
    cv.poly([(x, y - 300 * s), (x + 170 * s, y - 310 * s), (x + 195 * s, y - 290 * s), (x + 170 * s, y - 270 * s),
             (x, y - 262 * s)], DARK)
    cv.poly([(x, y - 240 * s), (x - 150 * s, y - 228 * s), (x - 175 * s, y - 208 * s), (x - 150 * s, y - 188 * s),
             (x, y - 200 * s)], DARK)


def red_eyes(ctx, x, y, s=1.0, fn=None):
    lc = ctx.light("eyes", fn or const(1.0))
    for dx in (-16 * s, 16 * s):
        lc.ellipse(x + dx, y, 7 * s, 4 * s, "#ff2a12", 1.0)
        lc.glow(x + dx, y, 40 * s, "#ff2a12", 0.5)


def pumpkin_field(ctx, y0, n=40, seed=0, moonlit=True):
    r = np.random.default_rng(seed)
    cv = ctx.cv
    items = []
    for i in range(n):
        f = r.uniform(0, 1) ** 0.8
        y = y0 + f * (OH - y0 + 150)
        x = r.uniform(-50, OW + 50)
        rr = 18 + 120 * f ** 1.6
        items.append((y, x, rr))
    for y, x, rr in sorted(items):
        cv.line([(x - rr * 2, y + rr * 0.6), (x + rr * 2.4, y + rr * 0.4)], "#0b1408", max(2, rr * 0.06), a=0.9)
        pumpkin(cv, x, y, rr, seed=int(x), base=mix("#c45a16", "#2a1a10", 0.55 if moonlit else 0),
                dark=mix("#6a2a08", "#120804", 0.6), stem="#18200e")


def jack(ctx, x, y, r, seed=0, kind=0, fn=None, name=None, lit=1.0, glow_r=3.0, plane=None, body=None):
    """A carved, lit jack-o'-lantern."""
    cv = plane.cv if plane else ctx.cv
    nm = name or "jack%d" % seed
    lc = ctx.light(nm, fn or flick(seed, 0.12, 1.2))
    pumpkin(cv, x, y, r, seed=seed, base=body or "#c8601c")
    ry = r * 0.78
    carve(cv, lc, x, y, r, ry, kind=kind, lit=lit)
    lc.glow(x, y + ry * 0.9, r * glow_r, "#ff7a1a", 0.22 * lit)
    return lc


def turnip_lantern(ctx, x, y, r, seed=0, kind=1, fn=None, name=None, lit=1.0, plane=None):
    cv = plane.cv if plane else ctx.cv
    nm = name or "turnip%d" % seed
    lc = ctx.light(nm, fn or flick(seed, 0.16, 1.4))
    turnip(cv, x, y, r, seed=seed)
    carve(cv, lc, x, y + r * 0.05, r * 0.85, r * 0.8, kind=kind, lit=lit, glow="#ffcf6a", inner="#ff9a2a")
    lc.glow(x, y, r * 3.2, "#ff8a2a", 0.2 * lit)
    return lc


def stone_wall(ctx, y_top, y_bottom, x0=0, x1=OW, seed=0, color="#0b1214", rim="#2c4442"):
    r = np.random.default_rng(seed)
    cv = ctx.cv
    rows = int((y_bottom - y_top) / 46) + 1
    for i in range(rows):
        yy = y_top + i * 46
        x = x0 - r.uniform(0, 60)
        while x < x1:
            w = r.uniform(70, 140)
            p = smooth_path([(x + 4, yy + 4), (x + w * 0.5, yy + r.uniform(0, 5)), (x + w - 4, yy + 4),
                             (x + w - 2, yy + 40), (x + w * 0.5, yy + 44), (x + 3, yy + 42)], True)
            col = mix(color, "#000000", r.uniform(0, 0.5))
            rim_shape(cv, p, col, rim, (2, 2), rim_a=0.5)
            x += w + 3


# ----------------------------------------------------------------------------- towns

def town_row(ctx, y, x0, x1, seed=0, hmin=180, hmax=420, lit_p=0.4, color="#05090b", rim="#2e4847", style="old",
             name="town", steeple=None, window=AMBER):
    r = np.random.default_rng(seed)
    cv = ctx.cv
    lc = ctx.light(name, flick(seed, 0.04, 0.3))
    x = x0
    while x < x1:
        w = r.uniform(160, 320)
        h = r.uniform(hmin, hmax)
        roof = r.choice(["gable", "flat", "gable", "false"])
        if roof == "gable":
            p = poly_path([(x, y), (x, y - h), (x + w / 2, y - h - w * 0.35), (x + w, y - h), (x + w, y)])
        elif roof == "false":
            p = poly_path([(x, y), (x, y - h - 30), (x + w * 0.2, y - h - 30), (x + w * 0.25, y - h - 50), (x + w * 0.75, y - h - 50),
                           (x + w * 0.8, y - h - 30), (x + w, y - h - 30), (x + w, y)])
        else:
            p = poly_path([(x, y), (x, y - h), (x + w, y - h), (x + w, y)])
        rim_shape(cv, p, color, rim, (3, 3), rim_a=0.5)
        rows = max(1, int(h / 110))
        cols = max(1, int(w / 80))
        for ri in range(rows):
            for ci in range(cols):
                wx = x + (ci + 0.5) * w / cols - 16
                wy = y - h + 40 + ri * 105
                if wy > y - 70:
                    continue
                if r.random() < lit_p:
                    cv.rect(wx, wy, wx + 32, wy + 52, "#2a1a0a")
                    lc.rect(wx, wy, wx + 32, wy + 52, window, r.uniform(0.5, 0.95))
                    lc.glow(wx + 16, wy + 26, 90, window, 0.18)
                else:
                    cv.rect(wx, wy, wx + 32, wy + 52, "#0c1416")
        x += w + r.uniform(0, 20)
    if steeple:
        sx, sh = steeple
        p = poly_path([(sx - 45, y), (sx - 45, y - sh * 0.6), (sx, y - sh), (sx + 45, y - sh * 0.6), (sx + 45, y)])
        rim_shape(cv, p, color, rim, (3, 3))


def gas_lamp(ctx, x, y, s=1.0, name=None, color="#ffcf7a", k=1.0, fn=None, pool=True):
    cv = ctx.cv
    cv.rect(x - 6 * s, y - 300 * s, x + 6 * s, y, "#030506")
    cv.poly([(x - 26 * s, y - 300 * s), (x + 26 * s, y - 300 * s), (x + 18 * s, y - 360 * s), (x - 18 * s, y - 360 * s)],
            "#0a0f10")
    cv.poly([(x - 32 * s, y - 360 * s), (x + 32 * s, y - 360 * s), (x, y - 385 * s)], "#030506")
    lc = ctx.light(name or "lamp%d" % int(x), fn or flick(int(x), 0.06, 1.5))
    lc.rect(x - 16 * s, y - 356 * s, x + 16 * s, y - 304 * s, color, 0.9 * k)
    lc.glow(x, y - 330 * s, 420 * s, color, 0.35 * k)
    lc.glow(x, y - 330 * s, 120 * s, "#fff2d0", 0.5 * k)
    if pool:
        lc.ellipse(x, y + 10 * s, 260 * s, 50 * s, color, 0.12 * k, blur=20 * s, mode=ADD)


def street_lamp_modern(ctx, x, y, s=1.0, k=1.0, name=None, color="#ffd9a0"):
    cv = ctx.cv
    cv.rect(x - 5 * s, y - 420 * s, x + 5 * s, y, "#030506")
    cv.line([(x, y - 420 * s), (x + 80 * s, y - 440 * s)], "#030506", 8 * s)
    cv.rect(x + 60 * s, y - 448 * s, x + 120 * s, y - 432 * s, "#030506", r=4)
    lc = ctx.light(name or "slamp%d" % int(x), const(k))
    lc.rect(x + 64 * s, y - 434 * s, x + 116 * s, y - 428 * s, color, 1.0)
    lc.c.drawPath(poly_path([(x + 64 * s, y - 432 * s), (x + 116 * s, y - 432 * s), (x + 300 * s, y), (x - 120 * s, y)]),
                  paint(color, 0.10, blur=30 * s))
    lc.glow(x + 90 * s, y - 430 * s, 140 * s, color, 0.45)
    lc.ellipse(x + 90 * s, y + 6 * s, 260 * s, 46 * s, color, 0.16, blur=18 * s, mode=ADD)


def courthouse(ctx, x, y, s=1.0, clock_fn=None):
    """Romanesque courthouse with a tall clock tower; (x, y) = bottom-left."""
    cv = ctx.cv
    body = poly_path([(x, y), (x, y - 260 * s), (x + 140 * s, y - 300 * s), (x + 520 * s, y - 300 * s),
                      (x + 660 * s, y - 260 * s), (x + 660 * s, y)])
    rim_shape(cv, body, DARK, RIM, (3 * s, 3 * s))
    tx = x + 270 * s
    tower = poly_path([(tx, y - 280 * s), (tx, y - 640 * s), (tx + 15 * s, y - 660 * s), (tx + 105 * s, y - 660 * s),
                       (tx + 120 * s, y - 640 * s), (tx + 120 * s, y - 280 * s)])
    rim_shape(cv, tower, DARK, RIM, (3 * s, 3 * s))
    roof = poly_path([(tx - 6 * s, y - 660 * s), (tx + 60 * s, y - 800 * s), (tx + 126 * s, y - 660 * s)])
    rim_shape(cv, roof, DARK, RIM, (3 * s, 3 * s))
    for cx_ in (tx - 10 * s, tx + 130 * s):
        cv.poly([(cx_ - 14 * s, y - 640 * s), (cx_, y - 700 * s), (cx_ + 14 * s, y - 640 * s)], DARK)
    lc = ctx.light("clock", clock_fn or const(1.0))
    cx_, cy_ = tx + 60 * s, y - 590 * s
    cv.circle(cx_, cy_, 38 * s, "#2a2414")
    lc.circle(cx_, cy_, 36 * s, "#f6e3b0", 0.85)
    lc.glow(cx_, cy_, 140 * s, "#f6e3b0", 0.3)
    # hands at about 5:44
    for ang, L in ((math.radians(-90 + 5.73 * 30), 20 * s), (math.radians(-90 + 44 * 6), 30 * s)):
        lc.line([(cx_, cy_), (cx_ + math.cos(ang) * L, cy_ + math.sin(ang) * L)], "#000000", 3 * s)
        ctx.occlude(poly_path([(cx_ - 1, cy_ - 1), (cx_ + math.cos(ang) * L, cy_ + math.sin(ang) * L), (cx_ + 1, cy_ + 1)]))
    for i in range(5):
        wx = x + 40 * s + i * 120 * s
        if abs(wx - tx - 40 * s) < 100 * s:
            continue
        cv.rect(wx, y - 220 * s, wx + 46 * s, y - 120 * s, "#0d1517", r=20 * s)


# ----------------------------------------------------------------------------- sea and ships

def sea(ctx, horizon, color="#0a171b", lit="#4d6f70", seed=0, moon_x=None):
    ctx.flush()
    h = OH - horizon
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    base = vgrad(h, OW, [(0, "#1c3034"), (0.2, color), (1, "#020607")])
    r = np.random.default_rng(seed)
    # long horizontal swells, finer toward the horizon
    acc = np.zeros((h, OW), np.float32)
    for k, (sx, sy, a) in enumerate(((900, 40, 0.5), (420, 18, 0.3), (160, 7, 0.2))):
        n = fbm(max(8, h // sy * 4), max(8, OW // sx * 8), scale=4, octaves=3, seed=seed + k)
        acc += cv2.resize(n, (OW, h), interpolation=cv2.INTER_CUBIC) * a
    # perspective: compress the pattern toward the horizon
    rows = (np.linspace(0, 1, h) ** 1.8 * (h - 1)).astype(int)
    acc = acc[rows]
    crest = smoothstep(0.55, 0.85, acc)
    trough = smoothstep(0.45, 0.2, acc)
    base = base * (1 - 0.35 * trough[..., None]) + crest[..., None] * rgb(lit) * (0.10 + 0.25 * (1 - yy))[..., None]
    if moon_x is not None:
        xx = np.arange(OW, dtype=np.float32)[None, :]
        path = np.exp(-((xx - moon_x) / (40 + 420 * yy)) ** 2)
        glit = smoothstep(0.6, 0.9, acc) * path
        base += (glit * 0.9 + path * 0.06)[..., None] * rgb("#cfe8e2")
    ctx.bg[horizon:] = base


def tall_ship(cv, x, y, s=1.0, color="#020405", sail="#0c1414", edge="#3a504e"):
    """Three-masted ship in silhouette with billowing sails; (x, y) = waterline centre. Returns a lantern position."""
    hull = smooth_path([(x - 360 * s, y - 80 * s), (x - 120 * s, y - 60 * s), (x + 200 * s, y - 64 * s), (x + 390 * s, y - 95 * s),
                        (x + 330 * s, y + 10 * s), (x - 260 * s, y + 18 * s)], True)
    cv.c.drawPath(hull, paint(color))
    cv.line([(x + 380 * s, y - 92 * s), (x + 560 * s, y - 170 * s)], color, 8 * s)
    masts = ((x - 190 * s, 470 * s), (x + 20 * s, 560 * s), (x + 230 * s, 440 * s))
    for mx, mh in masts:
        cv.rect(mx - 6 * s, y - 70 * s - mh, mx + 6 * s, y - 60 * s, color)
        for k, (yy, w) in enumerate(((0.10, 70), (0.36, 105), (0.64, 128))):
            top = y - 70 * s - mh * (1 - yy)
            bot = top + mh * 0.24
            ww = w * s
            cv.line([(mx - ww * 1.05, top), (mx + ww * 1.05, top)], color, 5 * s)
            sp = smooth_path([(mx - ww, top), (mx + ww, top), (mx + ww * 1.12, top + (bot - top) * 0.55), (mx + ww * 0.92, bot),
                              (mx, bot + 10 * s), (mx - ww * 0.92, bot), (mx - ww * 1.12, top + (bot - top) * 0.55)], True)
            cv.c.drawPath(sp, paint(sail))
            cv.c.drawPath(sp, paint(edge, 0.35, stroke=2 * s))
    for k in range(5):
        cv.line([(x + 20 * s, y - 630 * s), (x - 360 * s + k * 170 * s, y - 80 * s)], color, 1.6 * s, a=0.8)
    cv.line([(x + 20 * s, y - 630 * s), (x + 560 * s, y - 170 * s)], color, 1.6 * s, a=0.8)
    cv.line([(x - 190 * s, y - 540 * s), (x - 360 * s, y - 80 * s)], color, 1.6 * s, a=0.8)
    return x - 300 * s, y - 100 * s


# ----------------------------------------------------------------------------- modern

def string_lights(ctx, pts, n=24, colors=("#ff8a2a", "#ffcf6a", "#a64dff", "#ff8a2a"), name="string", sag=40, fn=None):
    cv = ctx.cv
    lc = ctx.light(name, fn or flick(7, 0.05, 0.6))
    (x0, y0), (x1, y1) = pts
    pp = []
    for i in range(n + 1):
        f = i / n
        x = x0 + (x1 - x0) * f
        y = y0 + (y1 - y0) * f + sag * math.sin(math.pi * f)
        pp.append((x, y))
    cv.line(pp, "#050505", 2)
    for i, (x, y) in enumerate(pp[1:-1]):
        c = colors[i % len(colors)]
        cv.circle(x, y + 7, 5, "#2a1a10")
        lc.circle(x, y + 7, 5, c, 1.0)
        lc.glow(x, y + 7, 46, c, 0.35)


def porch(ctx, x, y, s=1.0, light_k=1.0, name="porch", fn=None, door_color="#2a1b10"):
    """Front porch: door, porch light, steps. (x, y) = centre of the door bottom."""
    cv = ctx.cv
    wall = poly_path([(x - 900 * s, y), (x - 900 * s, y - 640 * s), (x + 900 * s, y - 640 * s), (x + 900 * s, y)])
    cv.c.drawPath(wall, paint(None, shader=lin((0, y - 640 * s), (0, y), [("#141c1f", 1), ("#0d1416", 1)])))
    for k in range(18):
        yy = y - 640 * s + k * 36 * s
        cv.line([(x - 900 * s, yy), (x + 900 * s, yy)], "#0a0f11", 2 * s)
    cv.rect(x - 95 * s, y - 330 * s, x + 95 * s, y, door_color)
    cv.rect(x - 110 * s, y - 345 * s, x + 110 * s, y - 330 * s, "#1d2629")
    cv.rect(x - 110 * s, y - 345 * s, x - 95 * s, y, "#1d2629")
    cv.rect(x + 95 * s, y - 345 * s, x + 110 * s, y, "#1d2629")
    for i in range(3):
        cv.rect(x - 70 * s, y - 300 * s + i * 95 * s, x + 70 * s, y - 220 * s + i * 95 * s, mix(door_color, "#000", 0.3), r=4)
    cv.circle(x + 70 * s, y - 160 * s, 7 * s, "#8a7a50")
    lc = ctx.light(name, fn or const(light_k))
    lx, ly = x + 190 * s, y - 300 * s
    cv.rect(lx - 18 * s, ly - 40 * s, lx + 18 * s, ly + 20 * s, "#1a1a14", r=5)
    lc.rect(lx - 13 * s, ly - 34 * s, lx + 13 * s, ly + 14 * s, "#ffe2a8", 1.0)
    lc.glow(lx, ly, 520 * s, "#ffd28a", 0.35)
    lc.glow(lx, ly, 120 * s, "#fff2d8", 0.55)
    for i in range(3):
        cv.rect(x - 300 * s - i * 40 * s, y + i * 40 * s, x + 300 * s + i * 40 * s, y + (i + 1) * 40 * s,
                mix("#151b1d", "#07090a", i / 3))
    return lx, ly


def kids_walking(ctx, specs, depth=1.0, speed=60.0, plane=None):
    """specs: list of dict(x, y, h, kind, bucket) - silhouettes on a plane that drifts sideways."""
    from art import figure
    pl = plane or ctx.plane(depth)
    for sp in specs:
        k = sp.get("kind", "witch")
        x, y, h = sp["x"], sp["y"], sp["h"]
        col = sp.get("color", "#030405")
        hand = None
        if k == "ghost":
            sheet_ghost(pl.cv, x, y, h, color=sp.get("sheet", "#d8dcda"))
            hand = (x + h * 0.22, y - h * 0.42)
        elif k == "witch":
            info = figure(pl.cv, x, y, h, col, child=True, hat="witch", dress=True, cape=True, arms=((10, 5), (25, 35)))
            hand = info["hands"][1]
        elif k == "belle":
            info = figure(pl.cv, x, y, h, col, child=True, bonnet=True, dress=True, arms=((10, 5), (25, 35)))
            hand = info["hands"][1]
        elif k == "cape":
            info = figure(pl.cv, x, y, h, col, child=True, cape=True, arms=((10, 5), (25, 35)))
            hand = info["hands"][1]
        elif k == "adult":
            info = figure(pl.cv, x, y, h, col, coat=True, hat=sp.get("hat"), arms=((8, 4), (15, 10)))
        else:
            info = figure(pl.cv, x, y, h, col, child=True, hat=sp.get("hat"), arms=((10, 5), (25, 35)))
            hand = info["hands"][1]
        if sp.get("bucket") and hand is not None:
            bx, by = hand[0] + h * 0.02, hand[1] + h * 0.07
            pl.cv.line([(bx - h * 0.055, by - h * 0.06), (hand[0], hand[1]), (bx + h * 0.055, by - h * 0.06)], "#111111", 2)
            pumpkin(pl.cv, bx, by, h * 0.075, seed=int(x), base="#e0701e")
    if speed:
        pl.offset = lambda t, s=speed: (s * t, math.sin(t * 7) * 2.0)
    return pl


class EmberBed:
    """Glowing coals: shifting noise mapped through the fire palette."""

    def __init__(self, x, y, w, h, seed=0):
        from core import fire_lut
        self.lut = fire_lut()
        self.x0, self.y0 = int(x - w / 2), int(y - h / 2)
        self.w, self.h = int(w), int(h)
        self.n = [fbm(self.h, self.w, scale=max(4.0, w / 30), octaves=4, seed=seed + k) for k in range(3)]
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        self.mask = clamp01(1 - (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)) ** 0.6

    def draw(self, buf, t, k=1.0):
        a = 0.5 + 0.5 * math.sin(t * 0.9)
        b = 0.5 + 0.5 * math.sin(t * 1.7 + 2)
        n = self.n[0] * (0.45 + 0.3 * a) + self.n[1] * (0.35 + 0.2 * b) + self.n[2] * 0.2
        heat = smoothstep(0.40, 0.80, n) * self.mask * k
        col = self.lut[(clamp01(heat) * 255).astype(np.uint8)]
        y0, x0 = self.y0, self.x0
        buf[y0:y0 + self.h, x0:x0 + self.w] += col


def embers_glow(ctx, x, y, w, seed=0, fn=None, k=1.0, name="coals"):
    bed = EmberBed(x, y, w, w * 0.22, seed=seed)
    f = fn or flick(seed + 40, 0.2, 0.7)
    ctx.dyn.append(lambda buf, t: bed.draw(buf, t, k * f(t)))
    return f
