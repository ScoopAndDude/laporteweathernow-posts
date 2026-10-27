"""Illustration library: skies, land, trees, buildings, figures and props.

Paintings are OW x OH float32 RGB (numpy). Vector shapes are drawn with Skia on
transparent canvases and composited with comp().
"""
import math

import cv2
import numpy as np
import skia

from core import (OW, OH, Canvas, rgb, mix, c4, clamp01, smoothstep, fbm, noise1d, add_spot, poly_path,
                  smooth_path, paint, lin, rad, ADD, SCREEN, MULT, ERASE, SRCATOP, blur, MOON, AMBER, GHOST)


def comp(buf, layer, a=1.0):
    """layer: premultiplied RGBA same size as buf (RGB)."""
    buf *= (1 - layer[..., 3:4] * a)
    buf += layer[..., :3] * a
    return buf


def add(buf, layer_rgb, k=1.0):
    buf += layer_rgb * k
    return buf


def vgrad(h, w, stops):
    """stops: list of (pos 0..1, color)."""
    ys = np.linspace(0, 1, h, dtype=np.float32)
    out = np.zeros((h, 3), np.float32)
    for c in range(3):
        out[:, c] = np.interp(ys, [s[0] for s in stops], [rgb(s[1])[c] for s in stops])
    return np.repeat(out[:, None, :], w, axis=1)


# ----------------------------------------------------------------------------- sky

def sky(w=OW, h=OH, stops=None, moon=None, stars=420, clouds=0.45, seed=0, moon_glow=0.55, cloud_color="#0d1a20",
        cloud_lit="#6f8c8c", star_max_y=0.75, cloud_band=(0.0, 0.7), warm_horizon=None):
    """moon = (x, y, r) in pixels or None. Returns RGB painting."""
    stops = stops or [(0.0, "#020507"), (0.45, "#07131a"), (0.78, "#12262c"), (1.0, "#1c3337")]
    img = vgrad(h, w, stops)
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    mglow = np.zeros((h, w), np.float32)
    if moon:
        mx, my, mr = moon
        d = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2) / mr
        mglow = np.exp(-np.maximum(d - 1, 0) * 0.55) * 0.5 + np.exp(-np.maximum(d - 1, 0) * 3.0) * 0.5
        img += (mglow * moon_glow * 0.55)[..., None] * rgb("#5f8580")[None, None, :]
    if warm_horizon:
        col, strength, height = warm_horizon
        band = smoothstep(1 - height, 1.0, yy / h)
        img += (band * strength)[..., None] * rgb(col)[None, None, :]
    # stars
    star = np.zeros((h, w, 3), np.float32)
    for _ in range(stars):
        x, y = r.uniform(0, w), r.uniform(0, h * star_max_y) ** 1.0
        y = r.uniform(0, 1) ** 1.6 * h * star_max_y
        b = r.uniform(0.15, 0.9) ** 2.2
        s = r.uniform(0.5, 1.1) if b < 0.5 else r.uniform(0.9, 1.6)
        add_spot(star, x, y, s, (0.85, 0.92, 1.0), b * 1.6)
    fade = smoothstep(star_max_y * h, star_max_y * h * 0.55, yy)[..., None]
    star *= fade
    # clouds
    if clouds > 0:
        n = fbm(h // 2, w // 2, scale=260, octaves=6, seed=seed + 9)
        n2 = fbm(h // 2, w // 2, scale=60, octaves=4, seed=seed + 19)
        n = cv2.resize(n * 0.8 + n2 * 0.2, (w, h), interpolation=cv2.INTER_CUBIC)
        band = smoothstep(cloud_band[0] * h - 120, cloud_band[0] * h + 80, yy) * smoothstep(cloud_band[1] * h + 60, cloud_band[1] * h - 160, yy)
        dens = smoothstep(1 - clouds * 0.75, 1.02 - clouds * 0.3, n) * band
        star *= (1 - dens[..., None] * 0.95)
        lit = clamp01(mglow * 1.3) * dens
        cc = rgb(cloud_color)[None, None, :]
        img = img * (1 - dens[..., None] * 0.85) + cc * dens[..., None] * 0.85
        img += (lit * 0.45)[..., None] * rgb(cloud_lit)[None, None, :]
    img += star
    if moon:
        mx, my, mr = moon
        d = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2) / mr
        disc = smoothstep(1.0, 0.975, d)
        maria = fbm(h // 4, w // 4, scale=18, octaves=4, seed=seed + 31)
        maria = cv2.resize(maria, (w, h), interpolation=cv2.INTER_CUBIC)
        shade = (1 - 0.22 * d ** 2) * (0.82 + 0.18 * smoothstep(0.35, 0.75, maria))
        mcol = rgb(MOON)[None, None, :] * shade[..., None]
        img = img * (1 - disc[..., None]) + mcol * disc[..., None]
        # thin halo just outside the limb
        halo = np.exp(-np.maximum(d - 1, 0) * 9.0) * (d > 0.99)
        img += (halo * 0.35)[..., None] * rgb("#cfe8e2")[None, None, :]
    return img.astype(np.float32)


def stars_only(buf, n, seed, y_max, k=1.0):
    r = np.random.default_rng(seed)
    for _ in range(n):
        x = r.uniform(0, buf.shape[1])
        y = r.uniform(0, 1) ** 1.5 * y_max
        b = r.uniform(0.15, 0.9) ** 2.2
        add_spot(buf, x, y, r.uniform(0.5, 1.3), (0.85, 0.92, 1.0), b * 1.5 * k)


# ----------------------------------------------------------------------------- land

def ridge(w, base, amp, scale, seed, octaves=5, x_shift=0):
    n = noise1d(w + abs(x_shift) + 4, scale, octaves=octaves, seed=seed)
    n = n[abs(x_shift): abs(x_shift) + w] if x_shift >= 0 else n[:w]
    return base - amp * n


def hills(buf, base, amp, scale, color, seed, rim=None, rim_w=4.0, rim_a=0.5, octaves=5, profile=None, fog=None):
    """Fill everything below a noise ridge line. Returns the profile (y per x)."""
    h, w = buf.shape[:2]
    prof = ridge(w, base, amp, scale, seed, octaves) if profile is None else profile
    yy = np.arange(h, dtype=np.float32)[:, None]
    cov = clamp01(yy - prof[None, :] + 0.5)
    col = rgb(color)[None, None, :]
    if fog is not None:
        # atmospheric haze fading into the ground
        fc, fa, fh = fog
        haze = smoothstep(fh, 0, yy - prof[None, :]) * fa
        layer = col * (1 - haze[..., None]) + rgb(fc)[None, None, :] * haze[..., None]
    else:
        layer = col
    buf[:] = buf * (1 - cov[..., None]) + layer * cov[..., None]
    if rim:
        d = yy - prof[None, :]
        rimm = np.exp(-np.maximum(d, 0) / rim_w) * cov
        buf += (rimm * rim_a)[..., None] * rgb(rim)[None, None, :]
    return prof


def fog_band(buf, y, height, color, a, seed=0, patchy=0.5):
    h, w = buf.shape[:2]
    yy = np.arange(h, dtype=np.float32)[:, None]
    band = np.exp(-((yy - y) / height) ** 2)
    if patchy:
        n = fbm(h // 4, w // 4, scale=90, octaves=4, seed=seed)
        n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
        band = band * (1 - patchy + patchy * n)
    f = (band * a)[..., None]
    buf[:] = 1 - (1 - buf) * (1 - f * rgb(color)[None, None, :])
    return buf


def ground_gradient(buf, y0, top, bottom):
    h, w = buf.shape[:2]
    g = vgrad(h - int(y0), w, [(0, top), (1, bottom)])
    buf[int(y0):] = g
    return buf


# ----------------------------------------------------------------------------- trees and plants

def tree(cv, x, y, h, seed=0, color="#020406", depth=7, spread=0.5, lean=0.0, gnarl=0.32, width=None,
         droop=0.15, a=1.0, twig=True, start_branch=0.38):
    """A bare, crooked tree. (x, y) is the base of the trunk."""
    r = np.random.default_rng(seed)
    tw = width or h * 0.05
    p = paint(color, a, stroke=1, cap=skia.Paint.kRound_Cap)

    def seg(x0, y0, ang, length, w0, w1, d):
        n = 4
        px, py = x0, y0
        a_ = ang
        for i in range(n):
            a_ += r.normal(0, gnarl * 0.35)
            a_ += droop * 0.06 * math.cos(a_) * (depth - d)  # heavier limbs sag
            l = length / n
            nx, ny = px + math.cos(a_) * l, py + math.sin(a_) * l
            ww = w0 + (w1 - w0) * (i + 1) / n
            p.setStrokeWidth(max(0.7, ww))
            cv.c.drawLine(px, py, nx, ny, p)
            px, py = nx, ny
        return px, py, a_

    def grow(x0, y0, ang, length, w, d):
        ex, ey, ea = seg(x0, y0, ang, length, w, w * 0.7, d)
        if d <= 0:
            if twig:
                for _ in range(r.integers(1, 3)):
                    ta = ea + r.normal(0, 0.6)
                    tl = length * r.uniform(0.3, 0.6)
                    p.setStrokeWidth(0.8)
                    cv.c.drawLine(ex, ey, ex + math.cos(ta) * tl, ey + math.sin(ta) * tl, p)
            return
        kids = 2 if r.random() < 0.78 else 3
        for k in range(kids):
            off = (k - (kids - 1) / 2) * spread * r.uniform(0.7, 1.35) + r.normal(0, 0.12)
            grow(ex, ey, ea + off, length * r.uniform(0.66, 0.82), w * r.uniform(0.58, 0.72), d - 1)

    # trunk
    trunk_len = h * start_branch
    ang = -math.pi / 2 + lean
    # root flare
    flare = poly_path([(x - tw * 1.6, y + 2), (x - tw * 0.55, y - tw * 1.2), (x + tw * 0.55, y - tw * 1.2),
                       (x + tw * 1.7, y + 2)])
    cv.c.drawPath(flare, paint(color, a))
    ex, ey, ea = seg(x, y, ang, trunk_len, tw, tw * 0.78, depth)
    n_main = 2 if r.random() < 0.6 else 3
    for k in range(n_main):
        off = (k - (n_main - 1) / 2) * spread * 1.1 + r.normal(0, 0.1)
        grow(ex, ey, ea + off, h * 0.3 * r.uniform(0.85, 1.1), tw * 0.62, depth - 1)


def grass(cv, y, x0, x1, color, n=500, hmin=10, hmax=46, seed=0, a=1.0, lean=0.25, width=(1.2, 3.0)):
    r = np.random.default_rng(seed)
    for _ in range(n):
        x = r.uniform(x0, x1)
        hh = r.uniform(hmin, hmax)
        bend = r.normal(lean, 0.35) * hh
        w = r.uniform(*width)
        pth = skia.Path()
        pth.moveTo(x - w, y + 3)
        pth.quadTo(x + bend * 0.3, y - hh * 0.55, x + bend, y - hh)
        pth.quadTo(x + bend * 0.3 + w * 0.5, y - hh * 0.5, x + w, y + 3)
        pth.close()
        cv.c.drawPath(pth, paint(color, a))


def reeds(cv, y, x0, x1, color, n=160, hmin=60, hmax=180, seed=0, a=1.0):
    r = np.random.default_rng(seed)
    p = paint(color, a, stroke=2.2)
    for _ in range(n):
        x = r.uniform(x0, x1)
        hh = r.uniform(hmin, hmax)
        bend = r.normal(0.15, 0.25) * hh * 0.3
        pth = skia.Path()
        pth.moveTo(x, y + 4)
        pth.quadTo(x + bend * 0.2, y - hh * 0.6, x + bend, y - hh)
        p.setStrokeWidth(r.uniform(1.4, 3.0))
        cv.c.drawPath(pth, p)
        if r.random() < 0.3:   # cattail head
            cv.ellipse(x + bend, y - hh + 10, 4, 13, color, a)


# ----------------------------------------------------------------------------- buildings

def rim_shape(cv, path, dark, rim, offset=(3, 3), rim_a=0.7, blur_r=0):
    """Draw a silhouette with a thin moonlit rim on the upper-left edge."""
    cv.c.drawPath(path, paint(rim, rim_a, blur=blur_r))
    p2 = skia.Path(path)
    p2.offset(*offset)
    cv.c.save()
    cv.c.clipPath(path, doAntiAlias=True)
    cv.c.drawPath(p2, paint(dark, 1.0))
    cv.c.restore()


def farmhouse(cv, lights, x, y, s=1.0, dark="#05090b", rim="#3b5654", window="#ffb45c", lit=(1, 1, 1, 0, 1),
              chimney_smoke=False, porch=True):
    """Two-storey gable farmhouse; (x, y) = bottom-left. lights: Canvas for the window glow layer."""
    W_, H_ = 420 * s, 300 * s
    roof_h = 150 * s
    body = poly_path([(x, y), (x, y - H_), (x + W_ * 0.5, y - H_ - roof_h), (x + W_, y - H_), (x + W_, y)])
    rim_shape(cv, body, dark, rim, (4 * s, 4 * s))
    # chimney
    ch = poly_path([(x + W_ * 0.68, y - H_ - roof_h * 0.45), (x + W_ * 0.68, y - H_ - roof_h * 0.95),
                    (x + W_ * 0.76, y - H_ - roof_h * 0.95), (x + W_ * 0.76, y - H_ - roof_h * 0.29)])
    cv.c.drawPath(ch, paint(dark))
    # wing
    wing = poly_path([(x + W_, y), (x + W_, y - H_ * 0.55), (x + W_ + 200 * s, y - H_ * 0.55 - 70 * s),
                      (x + W_ + 200 * s, y)])
    cv.c.drawPath(wing, paint(dark))
    if porch:
        pr = poly_path([(x - 30 * s, y - H_ * 0.40), (x + W_ + 10 * s, y - H_ * 0.40), (x + W_ - 10 * s, y - H_ * 0.47),
                        (x - 10 * s, y - H_ * 0.47)])
        cv.c.drawPath(pr, paint(dark))
        for px in np.linspace(x - 20 * s, x + W_ - 5 * s, 6):
            cv.rect(px, y - H_ * 0.42, px + 7 * s, y, dark)
    wins = [(x + W_ * 0.18, y - H_ * 0.83), (x + W_ * 0.62, y - H_ * 0.83), (x + W_ * 0.18, y - H_ * 0.32),
            (x + W_ * 0.62, y - H_ * 0.32), (x + W_ * 0.42, y - H_ - roof_h * 0.35)]
    ww, wh = 58 * s, 88 * s
    for i, (wx, wy) in enumerate(wins):
        on = lit[i] if i < len(lit) else 0
        sz = (ww * 0.7, wh * 0.6) if i == 4 else (ww, wh)
        if on:
            cv.rect(wx, wy, wx + sz[0], wy + sz[1], "#4a2a10")
            lights.rect(wx, wy, wx + sz[0], wy + sz[1], window, 0.95 * on)
            lights.glow(wx + sz[0] / 2, wy + sz[1] / 2, 140 * s, window, 0.35 * on)
            # mullions over the glow
            lights.rect(wx + sz[0] / 2 - 2 * s, wy, wx + sz[0] / 2 + 2 * s, wy + sz[1], "#000000", 1.0, mode=None)
            lights.rect(wx, wy + sz[1] * 0.48, wx + sz[0], wy + sz[1] * 0.48 + 4 * s, "#000000", 1.0)
        else:
            cv.rect(wx, wy, wx + sz[0], wy + sz[1], "#0d1619")
    return W_, H_


def church(cv, lights, x, y, s=1.0, dark="#05090b", rim="#3b5654", window="#ffb45c", lit=0.9):
    """Small stone church with a spire; (x, y) = bottom-left of nave."""
    nave_w, nave_h, roof = 520 * s, 230 * s, 150 * s
    nave = poly_path([(x, y), (x, y - nave_h), (x + nave_w * 0.5, y - nave_h - roof), (x + nave_w, y - nave_h),
                      (x + nave_w, y)])
    rim_shape(cv, nave, dark, rim, (4 * s, 4 * s))
    tx = x - 120 * s
    tw = 150 * s
    tower = poly_path([(tx, y), (tx, y - 420 * s), (tx + tw * 0.5, y - 720 * s), (tx + tw, y - 420 * s), (tx + tw, y)])
    rim_shape(cv, tower, dark, rim, (4 * s, 4 * s))
    cross_x, cross_y = tx + tw * 0.5, y - 720 * s
    cv.rect(cross_x - 3 * s, cross_y - 60 * s, cross_x + 3 * s, cross_y, dark)
    cv.rect(cross_x - 18 * s, cross_y - 45 * s, cross_x + 18 * s, cross_y - 39 * s, dark)
    # lancet windows
    for i in range(4):
        wx = x + 70 * s + i * 110 * s
        lancet(cv, lights, wx, y - 70 * s, 40 * s, 120 * s, window, lit)
    lancet(cv, lights, tx + tw * 0.5 - 22 * s, y - 300 * s, 44 * s, 110 * s, window, lit * 0.7)
    # door
    lancet(cv, lights, tx + tw * 0.5 - 30 * s, y, 60 * s, 110 * s, "#2b170a", 0.0)


def lancet(cv, lights, x, y_bottom, w, h, color, lit):
    p = skia.Path()
    p.moveTo(x, y_bottom)
    p.lineTo(x, y_bottom - h * 0.62)
    p.quadTo(x, y_bottom - h * 0.92, x + w / 2, y_bottom - h)
    p.quadTo(x + w, y_bottom - h * 0.92, x + w, y_bottom - h * 0.62)
    p.lineTo(x + w, y_bottom)
    p.close()
    if lit > 0:
        cv.c.drawPath(p, paint("#3a210c"))
        lights.c.drawPath(p, paint(color, lit))
        lights.glow(x + w / 2, y_bottom - h * 0.5, h * 1.3, color, 0.30 * lit)
        lights.rect(x + w / 2 - 1.5, y_bottom - h, x + w / 2 + 1.5, y_bottom, "#000000")
    else:
        cv.c.drawPath(p, paint(color))
    return p


def gravestones(cv, y, x0, x1, n, seed=0, dark="#05090b", rim="#41605e", hmin=60, hmax=150, tilt=0.15,
                kinds=("round", "cross", "slab", "round", "obelisk")):
    r = np.random.default_rng(seed)
    xs = np.sort(r.uniform(x0, x1, n))
    for x in xs:
        hh = r.uniform(hmin, hmax)
        ww = hh * r.uniform(0.45, 0.7)
        kind = kinds[r.integers(0, len(kinds))]
        ang = r.normal(0, tilt)
        cv.c.save()
        cv.c.translate(x, y + r.uniform(-6, 10))
        cv.c.rotate(math.degrees(ang))
        if kind == "round":
            p = skia.Path()
            p.moveTo(-ww / 2, 0)
            p.lineTo(-ww / 2, -hh + ww / 2)
            p.arcTo(skia.Rect(-ww / 2, -hh, ww / 2, -hh + ww), 180, 180, False)
            p.lineTo(ww / 2, 0)
            p.close()
        elif kind == "cross":
            t = ww * 0.28
            p = poly_path([(-t / 2, 0), (-t / 2, -hh * 0.62), (-ww / 2, -hh * 0.62), (-ww / 2, -hh * 0.62 - t),
                           (-t / 2, -hh * 0.62 - t), (-t / 2, -hh), (t / 2, -hh), (t / 2, -hh * 0.62 - t),
                           (ww / 2, -hh * 0.62 - t), (ww / 2, -hh * 0.62), (t / 2, -hh * 0.62), (t / 2, 0)])
        elif kind == "obelisk":
            p = poly_path([(-ww * 0.35, 0), (-ww * 0.22, -hh * 1.1), (0, -hh * 1.25), (ww * 0.22, -hh * 1.1),
                           (ww * 0.35, 0)])
        else:
            p = poly_path([(-ww / 2, 0), (-ww / 2, -hh * 0.8), (-ww * 0.35, -hh), (ww * 0.35, -hh), (ww / 2, -hh * 0.8),
                           (ww / 2, 0)])
        rim_shape(cv, p, dark, rim, (3, 3))
        cv.c.restore()


def fence(cv, y, x0, x1, dark="#04080a", spacing=46, h=90, seed=0, broken=0.15):
    r = np.random.default_rng(seed)
    x = x0
    prev = None
    while x < x1:
        hh = h * r.uniform(0.8, 1.1)
        lean = r.normal(0, 0.06)
        if r.random() > broken:
            pth = poly_path([(x - 5, y), (x - 5 + lean * hh, y - hh), (x + 6 + lean * hh, y - hh - 8),
                             (x + 6, y)])
            cv.c.drawPath(pth, paint(dark))
            if prev is not None:
                for k, fy in enumerate((0.3, 0.7)):
                    cv.line([(prev[0], prev[1] - prev[2] * fy), (x, y - hh * fy)], dark, 5)
            prev = (x, y, hh)
        else:
            prev = None
        x += spacing * r.uniform(0.85, 1.15)


# ----------------------------------------------------------------------------- figures

def hooded_figure(cv, x, y, h, color="#030506", a=1.0, mask=None, lean=0.0, lantern_hand=None, rim=None):
    """Cloaked, hooded figure standing at (x, y) feet, height h. mask: colour of a pale mask face."""
    s = h
    pts = [(0, -1.0), (0.09, -0.985), (0.135, -0.93), (0.15, -0.86), (0.17, -0.80), (0.24, -0.75), (0.255, -0.6),
           (0.25, -0.42), (0.27, -0.2), (0.30, -0.03), (0.22, 0.0), (0.12, -0.02), (0.02, 0.0), (-0.1, -0.02),
           (-0.2, 0.0), (-0.3, -0.03), (-0.27, -0.2), (-0.25, -0.42), (-0.255, -0.6), (-0.24, -0.75), (-0.17, -0.80),
           (-0.15, -0.86), (-0.135, -0.93), (-0.09, -0.985)]
    P = [(x + (px + lean * (1 + py)) * s, y + py * s) for px, py in pts]
    path = smooth_path(P, True)
    if rim:
        rim_shape(cv, path, color, rim, (2.5, 2.5))
    else:
        cv.c.drawPath(path, paint(color, a))
    fx, fy = x + lean * 0.12 * s, y - 0.865 * s
    if mask:
        cv.ellipse(fx, fy, 0.075 * s, 0.095 * s, mask, a)
        cv.ellipse(fx - 0.028 * s, fy - 0.015 * s, 0.017 * s, 0.012 * s, "#000000", a)
        cv.ellipse(fx + 0.028 * s, fy - 0.015 * s, 0.017 * s, 0.012 * s, "#000000", a)
        mp = poly_path([(fx - 0.03 * s, fy + 0.045 * s), (fx, fy + 0.035 * s), (fx + 0.03 * s, fy + 0.045 * s),
                        (fx, fy + 0.06 * s)])
        cv.c.drawPath(mp, paint("#000000", a))
    else:
        cv.ellipse(fx, fy, 0.07 * s, 0.09 * s, "#000000", a)
    return path


def person(cv, x, y, h, color="#030506", a=1.0, hat=None, dress=False, child=False, lean=0.0, arm_out=0.0,
           bonnet=False, cape=False):
    """Simple standing silhouette. hat: None|'witch'|'brim'|'cap'."""
    s = h
    head_r = 0.075 * s if not child else 0.1 * s
    hx, hy = x + lean * s * 0.1, y - s + head_r
    cv.circle(hx, hy, head_r, color, a)
    neck = hy + head_r * 0.9
    sh = 0.17 * s if not child else 0.15 * s
    if dress:
        body = [(hx - sh * 0.75, neck + 0.03 * s), (hx + sh * 0.75, neck + 0.03 * s), (x + 0.27 * s, y),
                (x - 0.27 * s, y)]
        cv.poly(body, color, a, smooth=False)
    else:
        torso = [(hx - sh, neck + 0.05 * s), (hx + sh, neck + 0.05 * s), (x + 0.12 * s, y - 0.45 * s),
                 (x - 0.12 * s, y - 0.45 * s)]
        cv.poly(torso, color, a)
        cv.line([(x - 0.06 * s, y - 0.47 * s), (x - 0.08 * s, y)], color, 0.09 * s, a)
        cv.line([(x + 0.06 * s, y - 0.47 * s), (x + 0.09 * s, y)], color, 0.09 * s, a)
    # arms
    cv.line([(hx - sh * 0.9, neck + 0.08 * s), (hx - sh * 1.1 - arm_out * s * 0.2, neck + 0.35 * s)], color, 0.07 * s, a)
    cv.line([(hx + sh * 0.9, neck + 0.08 * s), (hx + sh * 1.1 + arm_out * s * 0.25, neck + 0.33 * s - arm_out * 0.1 * s)],
            color, 0.07 * s, a)
    if hat == "witch":
        cv.poly([(hx - head_r * 2.3, hy - head_r * 0.5), (hx + head_r * 2.3, hy - head_r * 0.5),
                 (hx + head_r * 0.9, hy - head_r * 0.9), (hx + head_r * 1.6, hy - head_r * 4.2),
                 (hx - head_r * 0.9, hy - head_r * 0.9)], color, a, smooth=False)
    elif hat == "brim":
        cv.rect(hx - head_r * 1.9, hy - head_r * 0.75, hx + head_r * 1.9, hy - head_r * 0.45, color, a)
        cv.rect(hx - head_r * 1.0, hy - head_r * 1.9, hx + head_r * 1.0, hy - head_r * 0.6, color, a, r=4)
    elif hat == "cap":
        cv.ellipse(hx, hy - head_r * 0.6, head_r * 1.1, head_r * 0.6, color, a)
    if bonnet:
        cv.ellipse(hx, hy - head_r * 0.2, head_r * 1.45, head_r * 1.35, color, a)
    if cape:
        cv.poly([(hx - sh * 0.9, neck), (hx + sh * 0.9, neck), (x + 0.33 * s, y - 0.05 * s), (x - 0.33 * s, y - 0.05 * s)],
                color, a)
    return (hx, hy, head_r)


def sheet_ghost(cv, x, y, h, color="#e9ecea", a=1.0, eyes="#000000"):
    s = h
    pts = [(-0.02, -1.0), (0.14, -0.96), (0.2, -0.8), (0.22, -0.5), (0.27, -0.15), (0.33, 0.0), (0.2, -0.04),
           (0.1, 0.01), (0.0, -0.04), (-0.1, 0.01), (-0.2, -0.04), (-0.33, 0.0), (-0.27, -0.15), (-0.22, -0.5),
           (-0.2, -0.8), (-0.15, -0.96)]
    P = [(x + px * s, y + py * s) for px, py in pts]
    cv.c.drawPath(smooth_path(P, True), paint(color, a))
    cv.ellipse(x - 0.06 * s, y - 0.76 * s, 0.028 * s, 0.045 * s, eyes, a)
    cv.ellipse(x + 0.06 * s, y - 0.76 * s, 0.028 * s, 0.045 * s, eyes, a)


def bat(cv, x, y, s, flap, color="#020304", a=1.0):
    """flap in [-1, 1]."""
    wy = -flap * 0.55
    pts = [(0, -0.12), (0.08, -0.2), (0.12, -0.05), (0.35, -0.12 + wy * 0.6), (0.62, -0.05 + wy), (1.0, -0.15 + wy * 1.2),
           (0.86, 0.06 + wy * 0.8), (0.72, 0.03 + wy * 0.6), (0.6, 0.12 + wy * 0.5), (0.45, 0.07 + wy * 0.3),
           (0.32, 0.16 + wy * 0.2), (0.12, 0.12), (0.0, 0.2)]
    full = pts + [(-px, py) for px, py in reversed(pts[1:])]
    P = [(x + px * s, y + py * s) for px, py in full]
    cv.c.drawPath(poly_path(P), paint(color, a))


def crow(cv, x, y, s, flap, color="#020304", a=1.0):
    wy = flap * 0.5
    pts = [(-0.55, -0.02), (-0.3, -0.06), (-0.12, -0.1 - wy * 0.2), (0.15, -0.6 - wy), (0.3, -0.62 - wy * 1.1),
           (0.12, -0.06), (0.35, -0.04), (0.55, 0.02), (0.38, 0.08), (0.05, 0.1), (-0.35, 0.08)]
    P = [(x + px * s, y + py * s) for px, py in pts]
    cv.c.drawPath(smooth_path(P, True), paint(color, a))


# ----------------------------------------------------------------------------- props

def pumpkin(cv, x, y, r, seed=0, base="#d9661c", dark="#7a2e08", stem="#3d4a1c", squash=0.78, lobes=7, a=1.0,
            lit_from=(-0.4, -0.5), shade=0.65):
    """Shaded pumpkin centred at (x, y), radius r (horizontal)."""
    rr = np.random.default_rng(seed)
    ry = r * squash
    cv.c.save()
    for i in range(lobes):
        f = (i + 0.5) / lobes * 2 - 1
        lx = x + f * r * 0.62
        lw = r * (0.46 - 0.12 * abs(f))
        lh = ry * (1.0 - 0.1 * abs(f))
        col = mix(base, dark, 0.15 + 0.5 * abs(f))
        sh = rad((lx - lw * 0.3, y - lh * 0.35), lw * 1.6,
                 [(mix(col, "#ffb36b", 0.35), 1), (col, 1), (mix(col, "#2a0c02", 0.6), 1)], [0, 0.55, 1])
        cv.ellipse(lx, y, lw, lh, None, a, shader=sh)
    cv.c.restore()
    # stem
    stem_p = poly_path([(x - r * 0.07, y - ry * 0.86), (x - r * 0.05, y - ry * 1.18), (x + r * 0.08, y - ry * 1.28),
                        (x + r * 0.1, y - ry * 1.18), (x + r * 0.06, y - ry * 0.86)])
    cv.c.drawPath(stem_p, paint(stem, a))
    return ry


def jack_face(kind=0):
    """Carved face shapes as polygons in unit coords (x right, y down), centred at 0,0, radius ~1."""
    if kind == 0:
        eyeL = [(-0.55, -0.12), (-0.3, -0.48), (-0.12, -0.1)]
        eyeR = [(0.12, -0.1), (0.3, -0.48), (0.55, -0.12)]
        nose = [(-0.09, 0.08), (0.0, -0.06), (0.09, 0.08)]
        mouth = [(-0.66, 0.18), (-0.45, 0.26), (-0.36, 0.18), (-0.25, 0.32), (-0.12, 0.24), (0.0, 0.36), (0.12, 0.24),
                 (0.25, 0.32), (0.36, 0.18), (0.45, 0.26), (0.66, 0.18), (0.5, 0.52), (0.25, 0.44), (0.12, 0.56),
                 (0.0, 0.46), (-0.12, 0.56), (-0.25, 0.44), (-0.5, 0.52)]
    elif kind == 1:   # crooked turnip face
        eyeL = [(-0.5, -0.05), (-0.42, -0.42), (-0.15, -0.18)]
        eyeR = [(0.18, -0.2), (0.38, -0.36), (0.48, -0.02), (0.3, 0.02)]
        nose = [(-0.06, 0.12), (0.02, -0.02), (0.08, 0.14)]
        mouth = [(-0.55, 0.25), (-0.3, 0.32), (-0.2, 0.22), (-0.05, 0.36), (0.1, 0.24), (0.25, 0.36), (0.5, 0.22),
                 (0.38, 0.55), (0.15, 0.46), (-0.05, 0.6), (-0.25, 0.46), (-0.42, 0.56)]
    else:             # wide-eyed scream
        eyeL = [(-0.48, -0.15), (-0.35, -0.42), (-0.15, -0.38), (-0.12, -0.1), (-0.3, 0.0)]
        eyeR = [(0.12, -0.1), (0.15, -0.38), (0.35, -0.42), (0.48, -0.15), (0.3, 0.0)]
        nose = [(-0.05, 0.12), (0.0, 0.02), (0.05, 0.12)]
        mouth = [(-0.3, 0.3), (-0.15, 0.22), (0.0, 0.25), (0.15, 0.22), (0.3, 0.3), (0.22, 0.6), (0.0, 0.7),
                 (-0.22, 0.6)]
    return [eyeL, eyeR, nose, mouth]


def carve(cv, lights, x, y, rx, ry, kind=0, glow="#ffb347", inner="#ff8a1c", lit=1.0, scale=1.0, face_y=0.0):
    """Cut a glowing face into whatever was drawn at (x, y)."""
    shapes = jack_face(kind)
    for poly in shapes:
        P = [(x + px * rx * 0.8 * scale, y + (py + face_y) * ry * 0.85 * scale) for px, py in poly]
        p = poly_path(P)
        cv.c.drawPath(p, paint("#1a0800"))
        if lit > 0:
            lights.c.drawPath(p, paint(inner, lit))
            # brighter core of each hole
            q = skia.Path(p)
            cx = sum(px for px, _ in P) / len(P)
            cy = sum(py for _, py in P) / len(P)
            lights.c.save()
            lights.c.clipPath(p, doAntiAlias=True)
            lights.glow(cx, cy, max(rx, ry) * 0.5, glow, 1.0 * lit, mode=None, falloff=(1.0, 0.8, 0.3, 0.0))
            lights.c.restore()
    if lit > 0:
        lights.glow(x, y, max(rx, ry) * 2.6, "#ff8f2e", 0.30 * lit)


def turnip(cv, x, y, r, seed=0, top="#7b3f78", body="#efe2c8", a=1.0, cut_top=True):
    """Turnip: round, slightly flattened bulb with purple shoulders and a thin taproot. (x, y) = bulb centre."""
    ry = r * 0.9
    sh = rad((x - r * 0.35, y - ry * 0.35), r * 1.5, [("#fffaf0", 1), (body, 1), ("#8f7f6a", 1)], [0, 0.5, 1])
    pth = smooth_path([(x, y - ry), (x + r * 0.72, y - ry * 0.8), (x + r * 1.0, y - ry * 0.05), (x + r * 0.78, y + ry * 0.62),
                       (x + r * 0.28, y + ry * 0.95), (x + r * 0.06, y + ry * 1.08), (x - r * 0.06, y + ry * 1.08),
                       (x - r * 0.28, y + ry * 0.95), (x - r * 0.78, y + ry * 0.62), (x - r * 1.0, y - ry * 0.05),
                       (x - r * 0.72, y - ry * 0.8)])
    cv.c.drawPath(pth, paint(None, a, shader=sh))
    root = poly_path([(x - r * 0.05, y + ry * 1.02), (x + r * 0.05, y + ry * 1.02), (x + r * 0.01, y + ry * 1.38),
                      (x - r * 0.01, y + ry * 1.38)])
    cv.c.drawPath(root, paint("#a89a80", a))
    cv.c.save()
    cv.c.clipPath(pth, doAntiAlias=True)
    crown = rad((x - r * 0.2, y - ry * 1.25), r * 1.4, [(top, 0.95), (top, 0.8), (top, 0.0)], [0, 0.55, 1])
    cv.rect(x - r * 1.2, y - ry * 1.2, x + r * 1.2, y + ry * 0.25, None, a, shader=crown)
    cv.c.restore()
    if cut_top:
        cv.ellipse(x, y - ry * 0.84, r * 0.5, r * 0.13, "#3b2a1a", a)
        cv.ellipse(x, y - ry * 0.85, r * 0.45, r * 0.1, "#140a04", a)
    return pth


def lantern_parts(kind, x, y, r, face=1, seed=0, w=OW, h=OH, dim=0.16, skin_k=0.75, warm="#ffa860"):
    """A carved lantern split into: dark base (RGBA), glowing skin (RGB), glowing holes (RGB), mask."""
    body = Canvas(w, h)
    holes = Canvas(w, h)
    if kind == "turnip":
        turnip(body, x, y, r, seed=seed)
        carve(body, holes, x, y + r * 0.05, r * 0.85, r * 0.8, kind=face, glow="#ffd27a", inner="#ff9a2a")
        cy = y + r * 0.2
    elif kind == "mangel":
        mangel(body, x, y, r, seed=seed)
        carve(body, holes, x, y - r * 0.05, r * 0.75, r * 0.85, kind=face, glow="#ffd27a", inner="#ff9a2a")
        cy = y + r * 0.2
    else:
        pumpkin(body, x, y, r, seed=seed)
        carve(body, holes, x, y, r, r * 0.78, kind=face)
        cy = y + r * 0.25
    alb = body.rgba()
    mask = alb[..., 3].copy()
    base = alb.copy()
    base[..., :3] *= dim
    x0, x1 = int(max(0, x - r * 2)), int(min(w, x + r * 2))
    y0, y1 = int(max(0, y - r * 2)), int(min(h, y + r * 2))
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    g = np.exp(-(((xx - x) / (r * 0.9)) ** 2 + ((yy - cy) / (r * 0.8)) ** 2))
    skin = np.zeros((h, w, 3), np.float32)
    skin[y0:y1, x0:x1] = alb[y0:y1, x0:x1, :3] * rgb(warm)[None, None, :] * (0.25 + 0.75 * g)[..., None] * skin_k
    return base, skin, holes.rgb(), mask


def mangel(cv, x, y, r, seed=0):
    sh = rad((x - r * 0.3, y - r * 0.4), r * 1.8, [("#ffe0a0", 1), ("#d89a50", 1), ("#6a3a1a", 1)], [0, 0.5, 1])
    p = smooth_path([(x, y - r * 1.25), (x + r * 0.7, y - r * 0.95), (x + r * 0.85, y - r * 0.1), (x + r * 0.55, y + r * 0.8),
                     (x + r * 0.1, y + r * 1.5), (x - r * 0.05, y + r * 1.5), (x - r * 0.55, y + r * 0.8), (x - r * 0.85, y - r * 0.1),
                     (x - r * 0.7, y - r * 0.95)], True)
    cv.c.drawPath(p, paint(None, shader=sh))
    cv.c.save()
    cv.c.clipPath(p, doAntiAlias=True)
    cv.rect(x - r, y - r * 1.4, x + r, y - r * 0.6, "#8a3a2a", 0.6, blur=r * 0.25)
    cv.c.restore()
    cv.ellipse(x, y - r * 1.12, r * 0.42, r * 0.11, "#1a0c04")


def candle(cv, x, y, h, w, color="#e8dcc0", a=1.0):
    """Candle body; (x, y) = bottom-centre. Returns the wick tip position."""
    sh = lin((x - w / 2, 0), (x + w / 2, 0), [("#8d806a", 1), (color, 1), ("#fff6e4", 1), (color, 1), ("#6d6150", 1)],
             [0, 0.3, 0.45, 0.7, 1])
    cv.rect(x - w / 2, y - h, x + w / 2, y, None, a, shader=sh)
    cv.ellipse(x, y - h, w / 2, w * 0.16, "#f4ead6", a)
    # drips
    r = np.random.default_rng(int(x * 7 + y))
    for _ in range(3):
        dx = r.uniform(-w * 0.45, w * 0.45)
        dl = r.uniform(h * 0.08, h * 0.3)
        cv.rect(x + dx - w * 0.06, y - h, x + dx + w * 0.06, y - h + dl, "#f7eedd", a, r=w * 0.06)
    cv.line([(x, y - h), (x + 1, y - h - w * 0.28)], "#1b1208", max(1.5, w * 0.06), a)
    return (x + 1, y - h - w * 0.28)


def candle_flame(frame, x, y, size, t, seed=0, k=1.0, glow=True):
    """Animated candle flame drawn additively onto a float RGB frame. (x, y) = wick tip."""
    from core import Noise1, _noise_for
    n = _noise_for(seed + 77)
    sway = n(t, 1.3) * 0.18 + n(t + 9, 4.0) * 0.06
    stretch = 1.0 + n(t + 3, 2.2) * 0.12
    hh = size * 2.6 * stretch
    ww = size * 0.62
    x0, x1 = int(x - size * 2), int(x + size * 2) + 1
    y0, y1 = int(y - hh * 1.25), int(y + size * 0.5) + 1
    fh, fw = frame.shape[:2]
    if x1 <= 0 or y1 <= 0 or x0 >= fw or y0 >= fh:
        return
    X0, Y0 = max(0, x0), max(0, y0)
    X1, Y1 = min(fw, x1), min(fh, y1)
    yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
    v = clamp01((y - yy) / hh + 0.12)                    # 0 at base .. 1 at tip
    off = sway * size * 2.2 * v ** 1.6
    half = ww * np.sin(np.pi * np.clip(v, 0, 1) ** 0.7) * (1 - v) ** 0.35 + 0.6
    d = np.abs(xx - x - off) / half
    body = clamp01(1 - d) ** 0.8 * smoothstep(1.0, 0.85, v)
    core = clamp01(1 - d * 1.5) ** 1.2 * smoothstep(0.65, 0.25, v) * smoothstep(0.0, 0.12, v)
    blue = clamp01(1 - d) * smoothstep(0.16, 0.0, v)
    col = (body[..., None] * np.array([1.0, 0.55, 0.16], np.float32) * 0.9 +
           core[..., None] * np.array([1.0, 0.95, 0.8], np.float32) * 0.9 +
           blue[..., None] * np.array([0.15, 0.25, 0.6], np.float32) * 0.6) * k
    frame[Y0:Y1, X0:X1] += col
    if glow:
        add_spot(frame, x + sway * size, y - hh * 0.45, size * 1.2, (1.0, 0.7, 0.35), 0.35 * k)


def skull(cv, lights, x, y, s, bone="#d9cfb6", lit=1.0, glow="#ffb347"):
    cr = rad((x - s * 0.25, y - s * 0.35), s * 1.3, [("#fff8e8", 1), (bone, 1), ("#5d5446", 1)], [0, 0.5, 1])
    cv.ellipse(x, y - s * 0.15, s * 0.62, s * 0.58, None, shader=cr)
    jaw = smooth_path([(x - s * 0.42, y + s * 0.15), (x + s * 0.42, y + s * 0.15), (x + s * 0.32, y + s * 0.52),
                       (x, y + s * 0.62), (x - s * 0.32, y + s * 0.52)])
    cv.c.drawPath(jaw, paint(None, shader=cr))
    sockets = [(x - s * 0.24, y - s * 0.02), (x + s * 0.24, y - s * 0.02)]
    for sx, sy in sockets:
        cv.ellipse(sx, sy, s * 0.15, s * 0.16, "#120804")
        if lit:
            lights.ellipse(sx, sy, s * 0.13, s * 0.14, "#ff9a3a", lit * 0.9)
            lights.glow(sx, sy, s * 0.35, glow, lit * 0.8, mode=None)
    nose = poly_path([(x - s * 0.07, y + s * 0.25), (x, y + s * 0.1), (x + s * 0.07, y + s * 0.25)])
    cv.c.drawPath(nose, paint("#120804"))
    if lit:
        lights.c.drawPath(nose, paint("#ff8a2a", lit * 0.6))
    for i in range(6):
        tx = x - s * 0.25 + i * s * 0.1
        cv.rect(tx, y + s * 0.36, tx + s * 0.07, y + s * 0.47, "#efe6d2", r=2)
    if lit:
        lights.glow(x, y, s * 2.2, "#ff9233", lit * 0.25)


# ----------------------------------------------------------------------------- better figures

def _limb(cv, pts, w0, w1, color, a=1.0):
    """Tapered limb through 2-3 points."""
    n = len(pts)
    segs = []
    for i in range(n - 1):
        segs.append((pts[i], pts[i + 1], w0 + (w1 - w0) * i / (n - 1), w0 + (w1 - w0) * (i + 1) / (n - 1)))
    for (p0, p1, wa, wb) in segs:
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy) + 1e-6
        nx, ny = -dy / L, dx / L
        poly = [(p0[0] + nx * wa / 2, p0[1] + ny * wa / 2), (p1[0] + nx * wb / 2, p1[1] + ny * wb / 2),
                (p1[0] - nx * wb / 2, p1[1] - ny * wb / 2), (p0[0] - nx * wa / 2, p0[1] - ny * wa / 2)]
        cv.c.drawPath(poly_path(poly), paint(color, a))
        cv.circle(p1[0], p1[1], wb / 2, color, a)
    cv.circle(pts[0][0], pts[0][1], w0 / 2, color, a)


def figure(cv, x, y, h, color="#030405", a=1.0, child=False, dress=False, coat=False, hat=None, bonnet=False,
           arms=((8, 4), (-8, -4)), legs=(4, -4), lean=0.0, cape=False, bucket=None, hold=None):
    """A natural-looking standing silhouette. (x, y) = feet, h = height.
    arms: ((upper, lower) angle in degrees from straight down, for left and right; positive = outward)."""
    hr = h * (0.085 if child else 0.066)
    hx = x + lean * h * 0.08
    hy = y - h + hr * 1.05
    sh_y = hy + hr * 1.6
    sw = h * (0.11 if child else 0.125)          # half shoulder width
    hip_y = y - h * (0.42 if child else 0.47)
    ww = h * (0.08 if child else 0.085)
    # torso
    torso = smooth_path([(hx - sw * 0.35, hy + hr * 0.8), (hx + sw * 0.35, hy + hr * 0.8), (hx + sw, sh_y),
                         (x + ww * 1.1, hip_y - h * 0.06), (x + ww * 1.15, hip_y + h * 0.02), (x - ww * 1.15, hip_y + h * 0.02),
                         (x - ww * 1.1, hip_y - h * 0.06), (hx - sw, sh_y)], True)
    cv.c.drawPath(torso, paint(color, a))
    cv.ellipse(hx, hy, hr * 0.92, hr, color, a)
    cv.rect(hx - hr * 0.35, hy + hr * 0.6, hx + hr * 0.35, sh_y, color, a)
    # legs
    for side, ang in ((-1, legs[0]), (1, legs[1])):
        hip = (x + side * ww * 0.55, hip_y)
        r = math.radians(ang) * side
        knee = (hip[0] + math.sin(r) * h * 0.24, hip[1] + math.cos(r) * h * 0.24)
        foot = (knee[0] + math.sin(r * 0.5) * h * 0.24, y - h * 0.015)
        _limb(cv, [hip, knee, foot], h * 0.085, h * 0.042, color, a)
        cv.ellipse(foot[0] + side * h * 0.02, y - h * 0.012, h * 0.045, h * 0.018, color, a)
    if dress or coat:
        hem = h * (0.25 if dress else 0.17)
        hem_y = y - (h * 0.04 if dress else h * 0.22)
        skirt = smooth_path([(x - ww * 1.1, hip_y - h * 0.08), (x + ww * 1.1, hip_y - h * 0.08), (x + hem, hem_y),
                             (x + hem * 0.5, hem_y + h * 0.01), (x - hem * 0.5, hem_y + h * 0.01), (x - hem, hem_y)], True)
        cv.c.drawPath(skirt, paint(color, a))
    if cape:
        cp = smooth_path([(hx - sw * 0.6, sh_y - hr * 0.2), (hx + sw * 0.6, sh_y - hr * 0.2), (x + h * 0.2, y - h * 0.12),
                          (x, y - h * 0.08), (x - h * 0.2, y - h * 0.12)], True)
        cv.c.drawPath(cp, paint(color, a))
    # arms
    hands = []
    for side, (ua, la) in ((-1, arms[0]), (1, arms[1])):
        sh = (hx + side * sw * 0.92, sh_y + hr * 0.15)
        r1 = math.radians(ua) * side
        r2 = math.radians(ua + la) * side
        el = (sh[0] + math.sin(r1) * h * 0.17, sh[1] + math.cos(r1) * h * 0.17)
        hd = (el[0] + math.sin(r2) * h * 0.16, el[1] + math.cos(r2) * h * 0.16)
        _limb(cv, [sh, el, hd], h * 0.055, h * 0.035, color, a)
        cv.circle(hd[0], hd[1], h * 0.024, color, a)
        hands.append(hd)
    if hat == "witch":
        cv.ellipse(hx, hy - hr * 0.55, hr * 2.2, hr * 0.32, color, a)
        cv.poly([(hx - hr * 0.95, hy - hr * 0.6), (hx + hr * 0.95, hy - hr * 0.6), (hx + hr * 0.5, hy - hr * 2.6),
                 (hx + hr * 1.5, hy - hr * 3.6), (hx - hr * 0.2, hy - hr * 2.5)], color, a, smooth=False)
    elif hat == "top":
        cv.rect(hx - hr * 1.6, hy - hr * 0.75, hx + hr * 1.6, hy - hr * 0.5, color, a)
        cv.rect(hx - hr * 0.9, hy - hr * 2.4, hx + hr * 0.9, hy - hr * 0.6, color, a, r=3)
    elif hat == "brim":
        cv.ellipse(hx, hy - hr * 0.55, hr * 1.9, hr * 0.3, color, a)
        cv.ellipse(hx, hy - hr * 0.95, hr * 1.0, hr * 0.7, color, a)
    elif hat == "cap":
        cv.ellipse(hx, hy - hr * 0.5, hr * 1.05, hr * 0.65, color, a)
        cv.ellipse(hx + hr * 0.7, hy - hr * 0.35, hr * 0.7, hr * 0.2, color, a)
    elif hat == "hood":
        cv.c.drawPath(smooth_path([(hx - hr * 1.3, hy + hr * 1.2), (hx - hr * 1.2, hy - hr * 0.6), (hx + hr * 0.3, hy - hr * 2.0),
                                   (hx + hr * 1.2, hy - hr * 0.6), (hx + hr * 1.3, hy + hr * 1.2)], True), paint(color, a))
    if bonnet:
        cv.c.drawPath(smooth_path([(hx - hr * 1.35, hy + hr * 0.9), (hx - hr * 1.45, hy - hr * 0.4), (hx, hy - hr * 1.45),
                                   (hx + hr * 1.45, hy - hr * 0.4), (hx + hr * 1.35, hy + hr * 0.9), (hx, hy + hr * 0.2)], True),
                      paint(color, a))
    return dict(head=(hx, hy, hr), hands=hands)


def hooded(cv, x, y, h, color="#030405", a=1.0, mask=None, lean=0.0, ragged=0.5, seed=0, rim=None, eyes="#000000"):
    """Tall cloaked figure with a pointed hood and a ragged hem; optional pale mask."""
    r = np.random.default_rng(seed)
    s = h
    pts = [(0.0, -1.0), (0.07, -0.96), (0.115, -0.90), (0.13, -0.83), (0.16, -0.79), (0.21, -0.74), (0.22, -0.55),
           (0.22, -0.30), (0.25, -0.08)]
    hem = []
    n = 9
    for i in range(n + 1):
        f = i / n
        hx = 0.25 - 0.5 * f
        hy = -0.02 + (r.uniform(-0.05, 0.03) * ragged if 0 < i < n else 0)
        hem.append((hx, hy))
    back = [(-0.25, -0.08), (-0.22, -0.30), (-0.22, -0.55), (-0.21, -0.74), (-0.16, -0.79), (-0.13, -0.83),
            (-0.115, -0.90), (-0.07, -0.96)]
    P = [(x + (px + lean * (1 + py) * 0.5) * s, y + py * s) for px, py in pts + hem[1:-1] + back]
    path = smooth_path(P, True)
    if rim:
        rim_shape(cv, path, color, rim, (-3, 2), rim_a=0.8)
    else:
        cv.c.drawPath(path, paint(color, a))
    fx, fy = x + lean * 0.06 * s, y - 0.865 * s
    if mask:
        mp = smooth_path([(fx - 0.055 * s, fy - 0.06 * s), (fx + 0.055 * s, fy - 0.06 * s), (fx + 0.06 * s, fy + 0.02 * s),
                          (fx + 0.03 * s, fy + 0.075 * s), (fx - 0.03 * s, fy + 0.075 * s), (fx - 0.06 * s, fy + 0.02 * s)], True)
        cv.c.drawPath(mp, paint(mask, a))
        for sx in (-1, 1):
            ep = poly_path([(fx + sx * 0.012 * s, fy - 0.022 * s), (fx + sx * 0.048 * s, fy - 0.03 * s),
                            (fx + sx * 0.042 * s, fy - 0.004 * s), (fx + sx * 0.015 * s, fy - 0.0 * s)])
            cv.c.drawPath(ep, paint(eyes, a))
        cv.c.drawPath(poly_path([(fx - 0.004 * s, fy + 0.02 * s), (fx + 0.004 * s, fy + 0.02 * s), (fx, fy + 0.035 * s)]),
                      paint(eyes, a * 0.8))
    else:
        cv.ellipse(fx, fy, 0.06 * s, 0.08 * s, "#000000", a)
    return path
