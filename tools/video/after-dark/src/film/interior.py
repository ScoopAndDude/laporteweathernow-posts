"""Candle-lit interiors: paint an albedo picture, then light it with warm sources
(each source is its own flickering light layer) over a dim blue ambient."""
import math

import cv2
import numpy as np
import skia

from core import (OW, OH, Canvas, rgb, mix, clamp01, smoothstep, fbm, add_spot, poly_path, smooth_path, paint, lin,
                  rad, ADD, blur, flicker, Noise1, _noise_for, AMBER)
from art import comp, vgrad, candle, candle_flame, turnip, carve, pumpkin, skull
from scene import flick, const


def falloff(x, y, r0, rmax, w=OW, h=OH, sy=1.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - x) ** 2 + ((yy - y) * sy) ** 2)
    return (1.0 / (1.0 + (d / r0) ** 2)) * clamp01(1 - d / rmax) ** 2


class Light:
    def __init__(self, name, x, y, r0=180, rmax=1600, color="#ffb066", k=1.6, fn=None, sy=1.0):
        self.name, self.x, self.y, self.r0, self.rmax = name, x, y, r0, rmax
        self.color, self.k, self.fn, self.sy = color, k, fn, sy


def light_scene(ctx, albedo, lights, ambient=("#1d2c33", 0.20), amb_map=None):
    """albedo: RGB numpy painting. Sets ctx.bg and the light layers."""
    amb = rgb(ambient[0]) * ambient[1]
    if amb_map is not None:
        ctx.bg = albedo * amb[None, None, :] * amb_map[..., None]
    else:
        ctx.bg = albedo * amb[None, None, :]
    for L in lights:
        lm = falloff(L.x, L.y, L.r0, L.rmax, sy=L.sy)
        ctx.light_np(L.name, albedo * (lm * L.k)[..., None] * rgb(L.color)[None, None, :], L.fn)


# ----------------------------------------------------------------------------- textures

def plaster(h=OH, w=OW, color="#6b5d4b", seed=0, var=0.25):
    n = fbm(h // 2, w // 2, scale=180, octaves=6, seed=seed)
    n = cv2.resize(n, (w, h))
    base = rgb(color)[None, None, :] * (1 - var / 2 + var * n[..., None])
    stain = smoothstep(0.62, 0.9, fbm(h // 4, w // 4, scale=60, octaves=4, seed=seed + 3))
    stain = cv2.resize(stain, (w, h))
    return base * (1 - 0.35 * stain[..., None])


def wood(h, w, color="#5a3a22", seed=0, along="x", grain=0.35, boards=0):
    r = np.random.default_rng(seed)
    if along == "x":
        n = fbm(max(8, h // 10), w // 2, scale=40, octaves=4, seed=seed)
        n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
        fine = cv2.resize(fbm(max(8, h // 2), w // 8, scale=6, octaves=2, seed=seed + 1), (w, h))
    else:
        n = fbm(h // 2, max(8, w // 10), scale=40, octaves=4, seed=seed)
        n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
        fine = cv2.resize(fbm(h // 8, max(8, w // 2), scale=6, octaves=2, seed=seed + 1), (w, h))
    g = 0.5 + 0.5 * np.sin((n * 18 + fine * 3.0) * math.pi)
    img = rgb(color)[None, None, :] * (1 - grain + grain * (0.6 * g + 0.4 * n))[..., None]
    if boards:
        if along == "x":
            for k in range(1, boards):
                y = int(h * k / boards)
                img[max(0, y - 2):y + 2] *= 0.35
        else:
            for k in range(1, boards):
                x = int(w * k / boards)
                img[:, max(0, x - 2):x + 2] *= 0.35
    return img.astype(np.float32)


def stone_blocks(h, w, color="#5a5650", seed=0, bh=70, bw=(110, 190), mortar="#2a2724"):
    r = np.random.default_rng(seed)
    cv = Canvas(w, h, bg=mortar)
    y = 0
    row = 0
    while y < h:
        x = -r.uniform(0, 100)
        while x < w:
            ww = r.uniform(*bw)
            col = mix(color, "#000000", r.uniform(0, 0.35))
            col = mix(col, "#7a6a50", r.uniform(0, 0.2))
            cv.rect(x + 3, y + 3, x + ww - 3, y + bh - 3, col, r=8)
            x += ww
        y += bh
        row += 1
    img = cv.rgb()
    n = fbm(h // 2, w // 2, scale=30, octaves=4, seed=seed + 2)
    img *= (0.75 + 0.5 * cv2.resize(n, (w, h)))[..., None]
    return img


# ----------------------------------------------------------------------------- furniture and props (albedo canvases)

def table_top(alb, y_back, y_front=OH, color="#4a2e1a", seed=0, x0=0, x1=OW, edge="#1a0e06"):
    """Paint a wooden table top (numpy albedo) from y_back to y_front; front edge band at the bottom."""
    y_back, y_front, x0, x1 = int(y_back), int(y_front), int(x0), int(x1)
    h = y_front - y_back
    t = wood(h, x1 - x0, color, seed=seed, along="x", boards=4)
    shade = np.linspace(0.75, 1.1, h, dtype=np.float32)[:, None, None]
    alb[int(y_back):int(y_front), int(x0):int(x1)] = t * shade
    alb[int(y_back):int(y_back) + 3, int(x0):int(x1)] *= 0.4


def fireplace(cv, x, y, w=760, h=620, stone="#6e6458", seed=0):
    """Stone fireplace; (x, y) = bottom-centre. Returns the firebox rect."""
    r = np.random.default_rng(seed)
    outer = (x - w / 2, y - h, x + w / 2, y)
    # stones around the opening
    cv.rect(*outer, "#2a2622")
    by = y - h
    while by < y:
        bx = outer[0] - r.uniform(0, 40)
        while bx < outer[2]:
            bw = r.uniform(70, 130)
            col = mix(stone, "#000000", r.uniform(0, 0.4))
            cv.rect(max(outer[0], bx + 3), by + 3, min(outer[2], bx + bw - 3), by + 52, col, r=7)
            bx += bw
        by += 55
    # mantel
    cv.rect(x - w / 2 - 60, y - h - 40, x + w / 2 + 60, y - h + 10, "#3a2414")
    cv.rect(x - w / 2 - 60, y - h + 10, x + w / 2 + 60, y - h + 22, "#1c1009")
    # opening (arched)
    ow, oh = w * 0.62, h * 0.62
    p = skia.Path()
    p.moveTo(x - ow / 2, y)
    p.lineTo(x - ow / 2, y - oh * 0.75)
    p.quadTo(x, y - oh * 1.12, x + ow / 2, y - oh * 0.75)
    p.lineTo(x + ow / 2, y)
    p.close()
    cv.c.drawPath(p, paint(None, shader=lin((0, y - oh), (0, y), [("#0b0807", 1), ("#1c140f", 1)])))
    # hearth floor
    cv.rect(x - w / 2 - 40, y, x + w / 2 + 40, y + 30, "#4a443d")
    return (x - ow / 2, y - oh, x + ow / 2, y)


def embers_bed(cv_light, x, y, w, seed=0, k=1.0):
    r = np.random.default_rng(seed)
    for i in range(60):
        ex = x + r.normal(0, w * 0.22)
        ey = y - abs(r.normal(0, 12))
        rr = r.uniform(5, 16)
        c = mix("#ff3a0a", "#ffb04a", r.uniform(0, 1))
        cv_light.ellipse(ex, ey, rr, rr * 0.55, c, r.uniform(0.3, 0.9) * k)
    cv_light.glow(x, y - 10, w * 0.8, "#ff5a1a", 0.5 * k)


def logs(cv, x, y, w, color="#1d120a"):
    cv.c.save()
    cv.line([(x - w * 0.42, y - 10), (x + w * 0.38, y - 26)], color, 34)
    cv.line([(x - w * 0.35, y - 34), (x + w * 0.42, y - 12)], mix(color, "#000", 0.3), 30)
    cv.c.restore()


def chair(cv, x, y, s=1.0, color="#2b1a0e", back=True):
    """Ladder-back chair seen from the front; (x, y) = floor at the front legs."""
    w = 170 * s
    seat_y = y - 230 * s
    cv.rect(x - w / 2, seat_y - 14 * s, x + w / 2, seat_y + 14 * s, color, r=4 * s)
    for lx in (x - w / 2 + 8 * s, x + w / 2 - 22 * s):
        cv.rect(lx, seat_y, lx + 14 * s, y, color)
    if back:
        for lx in (x - w / 2 + 4 * s, x + w / 2 - 18 * s):
            cv.rect(lx, seat_y - 360 * s, lx + 14 * s, seat_y, color, r=6 * s)
        for k in range(4):
            yy = seat_y - 330 * s + k * 75 * s
            cv.rect(x - w / 2 + 10 * s, yy, x + w / 2 - 10 * s, yy + 22 * s, color, r=8 * s)


def plate(cv, x, y, r, color="#d9d2c0", sy=0.35):
    cv.ellipse(x, y + r * sy * 0.15, r * 1.02, r * sy * 1.02, "#000000", 0.35, blur=6)
    cv.ellipse(x, y, r, r * sy, color)
    cv.ellipse(x, y, r * 0.72, r * sy * 0.7, mix(color, "#8a826f", 0.35))
    cv.ellipse(x, y - r * sy * 0.05, r * 0.66, r * sy * 0.62, mix(color, "#fffaf0", 0.2))


def cup(cv, x, y, s=1.0, color="#cfc6b0"):
    sh = lin((x - 34 * s, 0), (x + 34 * s, 0), [("#6e6658", 1), (color, 1), ("#fffaf0", 1), (color, 1), ("#4e4638", 1)],
             [0, 0.35, 0.5, 0.7, 1])
    cv.c.drawPath(poly_path([(x - 34 * s, y - 80 * s), (x + 34 * s, y - 80 * s), (x + 27 * s, y), (x - 27 * s, y)]),
                  paint(None, shader=sh))
    cv.ellipse(x, y - 80 * s, 34 * s, 9 * s, "#3a2a1a")
    cv.c.drawPath(smooth_path([(x + 32 * s, y - 62 * s), (x + 58 * s, y - 55 * s), (x + 56 * s, y - 25 * s), (x + 28 * s, y - 22 * s)], False),
                  paint(color, stroke=7 * s))


def jug(cv, x, y, s=1.0, color="#8a6a4a"):
    sh = lin((x - 70 * s, 0), (x + 70 * s, 0), [("#2a1d10", 1), (color, 1), ("#d8b890", 1), (color, 1), ("#1d140a", 1)],
             [0, 0.3, 0.45, 0.7, 1])
    p = smooth_path([(x - 30 * s, y - 220 * s), (x + 30 * s, y - 220 * s), (x + 40 * s, y - 180 * s), (x + 75 * s, y - 100 * s),
                     (x + 60 * s, y - 10 * s), (x, y), (x - 60 * s, y - 10 * s), (x - 75 * s, y - 100 * s), (x - 40 * s, y - 180 * s)], True)
    cv.c.drawPath(p, paint(None, shader=sh))
    cv.ellipse(x, y - 220 * s, 30 * s, 8 * s, "#140c06")


def bowl(cv, x, y, s=1.0, color="#7a5a3a", fill="#c9a36a"):
    sh = lin((x - 110 * s, 0), (x + 110 * s, 0), [("#2a1a0d", 1), (color, 1), ("#c9a070", 1), (color, 1), ("#1a1008", 1)],
             [0, 0.3, 0.45, 0.7, 1])
    p = smooth_path([(x - 110 * s, y - 60 * s), (x + 110 * s, y - 60 * s), (x + 80 * s, y - 10 * s), (x, y), (x - 80 * s, y - 10 * s)], True)
    cv.c.drawPath(p, paint(None, shader=sh))
    cv.ellipse(x, y - 60 * s, 110 * s, 26 * s, mix(color, "#000", 0.4))
    cv.ellipse(x, y - 62 * s, 96 * s, 20 * s, fill)


def soul_cake(cv, x, y, r, seed=0):
    rr = np.random.default_rng(seed)
    cv.ellipse(x, y + r * 0.12, r, r * 0.42, "#5a3414")
    sh = rad((x - r * 0.3, y - r * 0.15), r * 1.3, [("#f0c27a", 1), ("#d79a52", 1), ("#9a5e26", 1)], [0, 0.6, 1])
    cv.ellipse(x, y, r, r * 0.38, None, shader=sh)
    cv.line([(x - r * 0.7, y), (x + r * 0.7, y)], "#8a4e1c", r * 0.08)
    cv.line([(x, y - r * 0.27), (x, y + r * 0.27)], "#8a4e1c", r * 0.08)
    for _ in range(9):
        a = rr.uniform(0, 6.28)
        d = rr.uniform(0.2, 0.8)
        cv.circle(x + math.cos(a) * r * d, y + math.sin(a) * r * d * 0.38, r * 0.045, "#2a1206")


def hazelnut(cv, x, y, r, rot=0.0):
    cv.c.save()
    cv.c.translate(x, y)
    cv.c.rotate(rot)
    cv.ellipse(0, r * 0.15, r * 1.05, r * 0.5, "#000000", 0.4, blur=5)
    sh = rad((-r * 0.35, -r * 0.4), r * 1.6, [("#c98a52", 1), ("#8a5426", 1), ("#3a1e0a", 1)], [0, 0.55, 1])
    p = smooth_path([(0, -r * 1.05), (r * 0.8, -r * 0.4), (r * 0.85, r * 0.3), (0, r * 0.62), (-r * 0.85, r * 0.3), (-r * 0.8, -r * 0.4)], True)
    cv.c.drawPath(p, paint(None, shader=sh))
    cv.ellipse(0, r * 0.38, r * 0.7, r * 0.26, "#d8c09a")
    cv.c.restore()


def saucer(cv, x, y, r, content=None):
    cv.ellipse(x, y + r * 0.1, r * 1.05, r * 0.36, "#000000", 0.45, blur=8)
    sh = rad((x - r * 0.3, y - r * 0.1), r * 1.4, [("#fbf6ec", 1), ("#d8d0bf", 1), ("#8f8676", 1)], [0, 0.6, 1])
    cv.ellipse(x, y, r, r * 0.34, None, shader=sh)
    cv.ellipse(x, y, r * 0.66, r * 0.22, "#b8b0a0")
    cv.ellipse(x, y - 2, r * 0.6, r * 0.19, "#e9e3d6")
    if content == "ring":
        p = paint("#d4a237", stroke=r * 0.06)
        cv.c.drawOval(skia.Rect(x - r * 0.22, y - r * 0.13, x + r * 0.22, y + r * 0.03), p)
        cv.c.drawOval(skia.Rect(x - r * 0.21, y - r * 0.12, x + r * 0.21, y + r * 0.02), paint("#fff2b8", 0.6, stroke=r * 0.015))
    elif content == "coin":
        cv.ellipse(x, y - r * 0.04, r * 0.24, r * 0.09, "#6a5a3a")
        cv.ellipse(x, y - r * 0.06, r * 0.24, r * 0.09, None,
                   shader=rad((x - r * 0.08, y - r * 0.1), r * 0.3, [("#fff2c0", 1), ("#c9a046", 1), ("#7a5e1e", 1)], [0, 0.5, 1]))
    elif content == "clay":
        p = smooth_path([(x - r * 0.3, y), (x - r * 0.22, y - r * 0.14), (x - r * 0.05, y - r * 0.2), (x + r * 0.18, y - r * 0.16),
                         (x + r * 0.3, y - r * 0.02), (x + r * 0.1, y + r * 0.06), (x - r * 0.15, y + r * 0.05)], True)
        cv.c.drawPath(p, paint(None, shader=rad((x - r * 0.1, y - r * 0.12), r * 0.4, [("#8a6a4a", 1), ("#4a3322", 1), ("#20140a", 1)], [0, 0.5, 1])))


def mirror(cv, x, y, rx, ry, frame="#8a6a2a"):
    sh = rad((x - rx * 0.3, y - ry * 0.3), max(rx, ry) * 1.4, [("#f2d98a", 1), (frame, 1), ("#3a2a0a", 1)], [0, 0.5, 1])
    cv.ellipse(x, y, rx + 34, ry + 34, None, shader=sh)
    cv.ellipse(x, y, rx + 12, ry + 12, "#2a1e08")
    glass = rad((x - rx * 0.3, y - ry * 0.4), max(rx, ry) * 1.3, [("#3a4448", 1), ("#151b1e", 1), ("#07090a", 1)], [0, 0.5, 1])
    cv.ellipse(x, y, rx, ry, None, shader=glass)


def clock(cv, x, y, s=1.0):
    p = smooth_path([(x - 90 * s, y), (x - 90 * s, y - 150 * s), (x - 60 * s, y - 220 * s), (x, y - 240 * s), (x + 60 * s, y - 220 * s),
                     (x + 90 * s, y - 150 * s), (x + 90 * s, y)], True)
    cv.c.drawPath(p, paint(None, shader=lin((x - 90 * s, 0), (x + 90 * s, 0), [("#2a170a", 1), ("#6a4022", 1), ("#2a170a", 1)])))
    cv.circle(x, y - 140 * s, 58 * s, "#e9dcc0")
    for i in range(12):
        a = i / 12 * 2 * math.pi
        cv.line([(x + math.sin(a) * 48 * s, y - 140 * s - math.cos(a) * 48 * s), (x + math.sin(a) * 54 * s, y - 140 * s - math.cos(a) * 54 * s)],
                "#2a2017", 3 * s)
    return (x, y - 140 * s)


def book(cv, x, y, w, h, color="#4a1c14", title=None):
    cv.rect(x, y - h * 0.12, x + w, y, "#e8dcc0")
    for k in range(6):
        cv.line([(x + 4, y - h * 0.12 + k * h * 0.02), (x + w - 4, y - h * 0.12 + k * h * 0.02)], "#b8a98a", 1)
    cv.rect(x - 6, y - h * 0.16, x + w + 6, y - h * 0.11, color, r=4)
    cv.rect(x - 6, y - 4, x + w + 6, y + 6, color, r=4)
    cv.rect(x - 10, y - h * 0.16, x + 12, y + 6, mix(color, "#000", 0.3), r=6)


def candy_pile(cv, x0, y0, x1, y1, n=70, seed=0):
    r = np.random.default_rng(seed)
    cols = ["#d8432a", "#e8b030", "#3a7ad8", "#6ac85a", "#e86aa8", "#f2f2f2", "#8a4ad8", "#ff8a2a"]
    items = sorted([(r.uniform(y0, y1), r.uniform(x0, x1)) for _ in range(n)])
    for y, x in items:
        kind = r.integers(0, 4)
        c = cols[r.integers(0, len(cols))]
        s = r.uniform(0.8, 1.3) * (0.7 + 0.6 * (y - y0) / max(1, y1 - y0))
        rot = r.uniform(-40, 40)
        cv.c.save()
        cv.c.translate(x, y)
        cv.c.rotate(rot)
        if kind == 0:     # twist-wrapped sweet
            cv.ellipse(0, 0, 22 * s, 13 * s, c)
            cv.poly([(-20 * s, 0), (-38 * s, -11 * s), (-38 * s, 11 * s)], c)
            cv.poly([(20 * s, 0), (38 * s, -11 * s), (38 * s, 11 * s)], c)
            cv.ellipse(-5 * s, -4 * s, 10 * s, 4 * s, "#ffffff", 0.45)
        elif kind == 1:   # bar
            cv.rect(-40 * s, -13 * s, 40 * s, 13 * s, c, r=3 * s)
            cv.rect(-40 * s, -4 * s, 40 * s, 4 * s, mix(c, "#fff", 0.4))
        elif kind == 2:   # paper straw (striped tube)
            cv.rect(-55 * s, -6 * s, 55 * s, 6 * s, "#f6f0e6", r=3 * s)
            for k in range(6):
                cv.rect(-50 * s + k * 18 * s, -6 * s, -42 * s + k * 18 * s, 6 * s, c)
        else:             # round candy
            cv.circle(0, 0, 15 * s, c)
            cv.circle(-4 * s, -5 * s, 5 * s, "#ffffff", 0.5)
        cv.c.restore()


def apple_on_stick(cv, x, y, r):
    cv.rect(x - 5, y - r * 2.4, x + 5, y - r * 0.6, "#c8a878")
    sh = rad((x - r * 0.35, y - r * 0.4), r * 1.5, [("#ff8a7a", 1), ("#c41a12", 1), ("#3a0402", 1)], [0, 0.45, 1])
    p = smooth_path([(x, y - r * 0.85), (x + r * 0.7, y - r * 0.95), (x + r, y - r * 0.2), (x + r * 0.7, y + r * 0.8),
                     (x, y + r * 0.95), (x - r * 0.7, y + r * 0.8), (x - r, y - r * 0.2), (x - r * 0.7, y - r * 0.95)], True)
    cv.c.drawPath(p, paint(None, shader=sh))
    cv.ellipse(x - r * 0.38, y - r * 0.45, r * 0.18, r * 0.3, "#ffffff", 0.55, blur=4)
    cv.ellipse(x, y + r * 0.95, r * 0.9, r * 0.22, "#8a1008", 0.8)


def radio_cathedral(cv, x, y, s=1.0):
    """1930s cathedral radio; (x, y) = bottom-centre. Returns dial centre."""
    w, h = 300 * s, 420 * s
    p = skia.Path()
    p.moveTo(x - w / 2, y)
    p.lineTo(x - w / 2, y - h * 0.62)
    p.cubicTo(x - w / 2, y - h * 1.02, x + w / 2, y - h * 1.02, x + w / 2, y - h * 0.62)
    p.lineTo(x + w / 2, y)
    p.close()
    cv.c.drawPath(p, paint(None, shader=lin((x - w / 2, 0), (x + w / 2, 0),
                                             [("#2a1408", 1), ("#7a4622", 1), ("#b07040", 1), ("#6a3a1a", 1), ("#20100a", 1)],
                                             [0, 0.25, 0.45, 0.75, 1])))
    # grille arch
    gw, gh = w * 0.62, h * 0.55
    g = skia.Path()
    g.moveTo(x - gw / 2, y - h * 0.38)
    g.lineTo(x - gw / 2, y - h * 0.62)
    g.cubicTo(x - gw / 2, y - h * 0.93, x + gw / 2, y - h * 0.93, x + gw / 2, y - h * 0.62)
    g.lineTo(x + gw / 2, y - h * 0.38)
    g.close()
    cv.c.drawPath(g, paint("#2e2418"))
    cv.c.save()
    cv.c.clipPath(g, doAntiAlias=True)
    for k in range(7):
        gx = x - gw / 2 + (k + 0.5) * gw / 7
        cv.rect(gx - 7 * s, y - h, gx + 7 * s, y, "#5a3418")
    cv.c.restore()
    dial = (x, y - h * 0.26)
    cv.circle(dial[0], dial[1], 34 * s, "#1a120a")
    for kx in (x - 90 * s, x + 90 * s):
        cv.circle(kx, y - h * 0.12, 18 * s, "#1a0e06")
        cv.circle(kx - 4 * s, y - h * 0.12 - 4 * s, 7 * s, "#5a3a1a")
    return dial


def ration_book(cv, x, y, s=1.0, rot=-6):
    from core import font  # noqa
    cv.c.save()
    cv.c.translate(x, y)
    cv.c.rotate(rot)
    w, h = 520 * s, 700 * s
    cv.rect(-w / 2 + 12, -h / 2 + 14, w / 2 + 12, h / 2 + 14, "#000000", 0.45, blur=14)
    cv.rect(-w / 2, -h / 2, w / 2, h / 2, "#efe6cf")
    cv.rect(-w / 2 + 18 * s, -h / 2 + 18 * s, w / 2 - 18 * s, h / 2 - 18 * s, "#2a3a5a", 1.0)
    cv.rect(-w / 2 + 22 * s, -h / 2 + 22 * s, w / 2 - 22 * s, h / 2 - 22 * s, "#efe6cf")
    # stamp grid at the bottom
    for i in range(4):
        for j in range(3):
            sx = -w / 2 + 50 * s + i * 108 * s
            sy = h / 2 - 260 * s + j * 72 * s
            cv.rect(sx, sy, sx + 96 * s, sy + 62 * s, "#e2d6b8")
            cv.c.drawRect(skia.Rect(sx, sy, sx + 96 * s, sy + 62 * s), paint("#8a7a5a", stroke=1.5))
    cv.c.restore()


def lightbox(cv, x, y, w, h):
    cv.rect(x - 14, y - 14, x + w + 14, y + h + 14, "#20262a", r=8)
    cv.rect(x, y, x + w, y + h, "#9fc4d8")
