"""Scene framework: a painting with flickering light layers, per-frame painters,
parallax planes and fog, filmed by a moving camera."""
import math

import cv2
import numpy as np

from core import (W, H, OW, OH, Canvas, Camera, warp, warp_pts, Fog, clamp01, sstep, ease, flicker, rgb, blur)
from art import comp


class Scene:
    dur = 6.0

    def __init__(self):
        self._built = False

    def ensure(self):
        if not self._built:
            self.build()
            self._built = True

    def build(self):
        pass

    def render(self, t, u):
        raise NotImplementedError

    def free(self):
        self._built = False


class Black(Scene):
    def __init__(self, color=(0, 0, 0)):
        super().__init__()
        self.color = np.array(color, np.float32)

    def render(self, t, u):
        f = np.empty((H, W, 3), np.float32)
        f[:] = self.color
        return f


def cropped(arr, thresh=1.0 / 1024):
    """Return (sub-array, (y0, y1, x0, x1)) holding the non-zero part of an RGB array."""
    nz = arr.max(axis=2) > thresh
    if not nz.any():
        return arr[:1, :1].copy(), (0, 1, 0, 1)
    rows = np.nonzero(nz.any(axis=1))[0]
    cols = np.nonzero(nz.any(axis=0))[0]
    y0, y1, x0, x1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    return np.ascontiguousarray(arr[y0:y1, x0:x1]), (y0, y1, x0, x1)


class Plane:
    def add_glow(self, rgb_arr, fn):
        """Additive light carried on this plane (moves with it); fn(t) scales it."""
        sub, (y0, y1, x0, x1) = cropped(rgb_arr)

        def f(src, t):
            k = fn(t)
            if k > 0.001:
                region = src[y0:y1, x0:x1, :3]
                region += sub * k
        self.dyn.append(f)

    def __init__(self, depth=1.0, w=OW, h=OH):
        self.cv = Canvas(w, h)
        self.depth = depth
        self.dyn = []           # fn(rgba_buf, t)
        self.offset = None      # fn(t) -> (dx, dy) in painting pixels
        self.rgba = None

    def finish(self):
        self.rgba = self.cv.rgba()
        self.cv = None


class Ctx:
    """Collects everything a painted scene needs while it is being built."""

    def __init__(self, bg=None, w=OW, h=OH):
        self.w, self.h = w, h
        self.bg = bg if bg is not None else np.zeros((h, w, 3), np.float32)
        self.cv = Canvas(w, h)
        self.lights = {}          # name -> [Canvas, fn, numpy]
        self.dyn = []             # fn(buf, t)  (painting space, before the camera)
        self.post = []            # fn(frame, t, m)  (frame space, after the camera)
        self.planes = []
        self.fog = None
        self.fog_density = None
        self.front_fog = None
        self.dirty = False

    # vector drawing goes to self.cv; call flush() before more numpy painting
    def flush(self):
        layer = self.cv.rgba()
        if layer[..., 3].max() > 0:
            comp(self.bg, layer)
        self.cv = Canvas(self.w, self.h)

    def light(self, name, fn=None):
        if name not in self.lights:
            self.lights[name] = [Canvas(self.w, self.h), fn or (lambda t: 1.0), None]
        elif fn is not None:
            self.lights[name][1] = fn
        return self.lights[name][0]

    def light_np(self, name, arr, fn=None):
        """Add a numpy light layer (RGB, additive)."""
        if name in self.lights and self.lights[name][2] is not None:
            self.lights[name][2] += arr
        else:
            self.light(name, fn)
            self.lights[name][2] = arr.astype(np.float32)
        if fn is not None:
            self.lights[name][1] = fn

    def occlude(self, path):
        """Erase a foreground shape from every light layer drawn so far."""
        import skia
        from core import paint, ERASE
        for cv, fn, arr in self.lights.values():
            cv.c.drawPath(path, paint("#000000", 1.0, mode=ERASE))

    def occlude_mask(self, mask):
        """Remove light (drawn so far) wherever a foreground object covers it. mask: HxW alpha."""
        import skia
        from core import np_to_skimage
        m4 = np.zeros(mask.shape + (4,), np.float32)
        m4[..., 3] = mask
        img = np_to_skimage(m4)
        for name, entry in self.lights.items():
            cv, fn, arr = entry
            if arr is not None:
                arr *= (1 - mask[..., None])
            p = skia.Paint()
            p.setBlendMode(skia.BlendMode.kDstOut)
            cv.c.drawImage(img, 0, 0, skia.SamplingOptions(), p)

    def lantern(self, kind, x, y, r, face=1, seed=0, fn=None, name=None, dim=0.06, skin_k=0.75, halo=0.22):
        """Place a carved, lit lantern (turnip, mangel or pumpkin) into the painting."""
        from art import lantern_parts, comp
        from core import Canvas
        self.flush()
        base, skin, holes, mask = lantern_parts(kind, x, y, r, face=face, seed=seed, w=self.w, h=self.h, dim=dim,
                                                skin_k=skin_k)
        self.occlude_mask(mask)
        comp(self.bg, base)
        nm = name or "lantern%d_%d" % (int(x), int(y))
        from scene import flick as _fl
        f = fn or _fl(seed + 17, 0.15, 1.3)
        halo_cv = Canvas(self.w, self.h)
        halo_cv.glow(x, y + r * 0.2, r * 3.4, "#ff8a2a", halo)
        self.light_np(nm, skin + holes + halo_cv.rgb(), f)
        return f

    def plane(self, depth=1.0):
        p = Plane(depth, self.w, self.h)
        self.planes.append(p)
        return p


class Painted(Scene):
    """A scene made by a builder function fn(ctx) -> None."""

    def __init__(self, fn, dur=6.0, cam=None, fog=None, front_fog=None, name="", grade=None):
        super().__init__()
        self.fn = fn
        self.dur = dur
        self.cam = cam or Camera(1.0, 1.06)
        self.fog_spec = fog
        self.front_fog_spec = front_fog
        self.name = name
        self.grade = grade

    def build(self):
        ctx = Ctx()
        self.fn(ctx)
        ctx.flush()
        self.bg = ctx.bg
        self.lights = []
        for name, (cv, fn, arr) in ctx.lights.items():
            layer = cv.rgba()[..., :3]
            if arr is not None:
                layer = layer + arr
            # keep only the part of the layer that actually holds light
            nz = layer.max(axis=2) > (1.0 / 1024)
            if not nz.any():
                continue
            rows = np.nonzero(nz.any(axis=1))[0]
            cols = np.nonzero(nz.any(axis=0))[0]
            y0, y1, x0, x1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
            self.lights.append((np.ascontiguousarray(layer[y0:y1, x0:x1], np.float32), fn, (y0, y1, x0, x1)))
        self.dyn = ctx.dyn
        self.post = ctx.post
        for p in ctx.planes:
            p.finish()
        self.planes = ctx.planes
        self.fog = Fog(**self.fog_spec) if self.fog_spec else ctx.fog
        self.front_fog = Fog(**self.front_fog_spec) if self.front_fog_spec else ctx.front_fog
        self.work = np.empty_like(self.bg) if (self.lights or self.dyn) else None

    def free(self):
        for k in ("bg", "lights", "planes", "work", "fog", "front_fog"):
            if hasattr(self, k):
                delattr(self, k)
        self._built = False

    def render(self, t, u):
        self.ensure()
        if self.work is not None:
            buf = self.work
            np.copyto(buf, self.bg)
            for layer, fn, (y0, y1, x0, x1) in self.lights:
                k = fn(t)
                if k > 0.001:
                    region = buf[y0:y1, x0:x1]
                    cv2.scaleAdd(layer, float(k), region, dst=region)
            for f in self.dyn:
                f(buf, t)
        else:
            buf = self.bg
        m = self.cam.matrix(u, t)
        out = warp(buf, m)
        if self.fog is not None:
            self.fog.apply(out, t)
        for p in self.planes:
            src = p.rgba
            if p.dyn:
                src = src.copy()
                for f in p.dyn:
                    f(src, t)
            mp = self.cam.matrix(u, t, depth=p.depth)
            if p.offset is not None:
                dx, dy = p.offset(t)
                mp = mp.copy()
                mp[0, 2] -= dx
                mp[1, 2] -= dy
            w4 = cv2.warpAffine(src, mp, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            out *= (1 - w4[..., 3:4])
            out += w4[..., :3]
        if self.front_fog is not None:
            self.front_fog.apply(out, t)
        for f in self.post:
            f(out, t, m)
        if self.grade is not None:
            self.grade(out, t)
        return out


class Blend(Scene):
    """Cross-dissolve between two scenes inside one shot (double exposure)."""

    def __init__(self, a, b, t0, t1, dur):
        super().__init__()
        self.a, self.b, self.t0, self.t1 = a, b, t0, t1
        self.dur = dur

    def render(self, t, u):
        k = sstep(self.t0, self.t1, t)
        if k <= 0:
            return self.a.render(t, u)
        if k >= 1:
            return self.b.render(t, u)
        fa = self.a.render(t, u)
        fb = self.b.render(t, u)
        return fa * (1 - k) + fb * k

    def free(self):
        self.a.free()
        self.b.free()


class Seq(Scene):
    """Several scenes cross-dissolving inside one shot: parts = [(scene, t_start)]."""

    def __init__(self, parts, dur, fade=0.7):
        super().__init__()
        self.parts = parts
        self.dur = dur
        self.fade = fade

    def render(self, t, u):
        idx = 0
        for i, (sc, ts) in enumerate(self.parts):
            if t >= ts:
                idx = i
        sc, ts = self.parts[idx]
        te = self.parts[idx + 1][1] if idx + 1 < len(self.parts) else self.dur
        lu = (t - ts) / max(0.1, te - ts)
        f = sc.render(t - ts, min(1, max(0, lu)))
        if idx > 0 and t - ts < self.fade:
            k = sstep(0, self.fade, t - ts)
            ps, pts_ = self.parts[idx - 1]
            pu = (t - pts_) / max(0.1, ts - pts_)
            g = ps.render(t - pts_, min(1, pu))
            f = g * (1 - k) + f * k
        return f

    def free(self):
        for sc, _ in self.parts:
            sc.free()


# ----------------------------------------------------------------------------- time helpers

def ramp(t0, t1, a=0.0, b=1.0):
    return lambda t: a + (b - a) * sstep(t0, t1, t)


def times(*fns):
    def f(t):
        v = 1.0
        for g in fns:
            v *= g(t) if callable(g) else g
        return v
    return f


def flick(seed=0, amt=0.15, speed=1.0, base=1.0):
    return lambda t: base * flicker(t, seed, amt, speed)


def const(k):
    return lambda t: k
