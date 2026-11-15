"""Core helpers: math, easing, noise, colour, paints, paths, camera, sprite cache.

Every scene draws in a 1920x1080 "world" space through a Camera. Layers can use a
parallax factor p (0 = fixed to the screen, 1 = moves with the world).
"""
import math
import os
from contextlib import contextmanager

import numpy as np
import skia

W, H, FPS = 1920, 1080, 24
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")

TAU = math.pi * 2


# ----------------------------------------------------------------- math / easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def inv(t, a, b):
    """0..1 position of t between a and b (clamped)."""
    if b == a:
        return 1.0 if t >= b else 0.0
    return clamp((t - a) / (b - a))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def smoother(t):
    t = clamp(t)
    return t * t * t * (t * (t * 6 - 15) + 10)


def ease_in(t):
    t = clamp(t)
    return t * t * t


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in2(t):
    t = clamp(t)
    return t * t


def ease_out2(t):
    t = clamp(t)
    return 1 - (1 - t) ** 2


def ease_io(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_back(t, s=1.7):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def seg(t, a, b, fn=smooth):
    return fn(inv(t, a, b))


def bump(t, a, b):
    """0 -> 1 -> 0 hump between a and b."""
    u = inv(t, a, b)
    return math.sin(math.pi * u)


def window(t, a, b, fade_in, fade_out):
    return seg(t, a, a + fade_in) * (1 - seg(t, b - fade_out, b))


def lerp2(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def keys(t, pts, fn=smooth):
    """Piecewise interpolation through [(time, value), ...]; value may be tuple."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1:
            u = fn(inv(t, t0, t1))
            if isinstance(v0, tuple):
                return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return pts[-1][1]


# ----------------------------------------------------------------- noise
_RS = np.random.RandomState(1234)
_PERM = _RS.rand(8192)


def noise(x, seed=0):
    """Smooth 1D value noise in -1..1."""
    x = x + seed * 57.31
    i = math.floor(x)
    f = x - i
    a = _PERM[i & 8191]
    b = _PERM[(i + 1) & 8191]
    u = f * f * (3 - 2 * f)
    return (a + (b - a) * u) * 2 - 1


def fbm(x, seed=0, octaves=3):
    v, amp, fr, tot = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        v += noise(x * fr, seed + o * 13) * amp
        tot += amp
        amp *= 0.5
        fr *= 2.03
    return v / tot


def hash01(*a):
    h = 0
    for v in a:
        h = (h * 1000003 + int(v * 7919 + 17)) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF) / float(0xFFFFFF)


class Rng:
    def __init__(self, seed):
        self.r = np.random.RandomState(int(seed) & 0xFFFFFFFF)

    def u(self, a=0.0, b=1.0):
        return a + (b - a) * self.r.rand()

    def i(self, a, b):
        return int(self.r.randint(a, b))

    def n(self, s=1.0):
        return self.r.randn() * s

    def choice(self, seq):
        return seq[self.r.randint(0, len(seq))]


# ----------------------------------------------------------------- colour
def rgb(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return (int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(c[4:6], 16) / 255.0)
    return tuple(c[:3])


def mix(c1, c2, t):
    a, b = rgb(c1), rgb(c2)
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def mixk(t, pts):
    """Colour keyframes [(t, colour), ...]."""
    if t <= pts[0][0]:
        return rgb(pts[0][1])
    for (t0, c0), (t1, c1) in zip(pts, pts[1:]):
        if t <= t1:
            return mix(c0, c1, smooth(inv(t, t0, t1)))
    return rgb(pts[-1][1])


def shade(c, k):
    """k<0 darken, k>0 lighten."""
    return mix(c, (0, 0, 0), -k) if k < 0 else mix(c, (1, 1, 1), k)


def ci(c, a=1.0):
    """skia int colour."""
    r, g, b = rgb(c)
    return skia.ColorSetARGB(int(clamp(a) * 255), int(clamp(r) * 255), int(clamp(g) * 255), int(clamp(b) * 255))


def c4(c, a=1.0):
    r, g, b = rgb(c)
    return skia.Color4f(r, g, b, clamp(a))


# ----------------------------------------------------------------- paints
BLEND = {
    "add": skia.BlendMode.kPlus,
    "screen": skia.BlendMode.kScreen,
    "multiply": skia.BlendMode.kMultiply,
    "overlay": skia.BlendMode.kOverlay,
    "soft": skia.BlendMode.kSoftLight,
    "atop": skia.BlendMode.kSrcATop,
    "dstout": skia.BlendMode.kDstOut,
}


def paint(color=None, a=1.0, stroke=None, blur=0.0, blend=None, shader=None, cap="round", aa=True):
    p = skia.Paint()
    p.setAntiAlias(aa)
    if shader is not None:
        p.setShader(shader)
        p.setAlphaf(clamp(a))
    elif color is not None:
        p.setColor4f(c4(color, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap == "round":
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
        elif cap == "butt":
            p.setStrokeCap(skia.Paint.kButt_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur and blur > 0.05:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend:
        p.setBlendMode(BLEND[blend])
    return p


def lin(p0, p1, stops):
    """Linear gradient. stops: [(pos, colour, alpha), ...] or [(pos, colour)]."""
    cols = [ci(s[1], s[2] if len(s) > 2 else 1.0) for s in stops]
    pos = [float(s[0]) for s in stops]
    return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], cols, pos)


def rad(center, r, stops):
    cols = [ci(s[1], s[2] if len(s) > 2 else 1.0) for s in stops]
    pos = [float(s[0]) for s in stops]
    return skia.GradientShader.MakeRadial(skia.Point(*center), max(r, 0.01), cols, pos)


def glow(c, x, y, r, color, a=1.0, blend="add", core=0.0):
    """Soft radial light."""
    stops = [(0, color, a), (0.25 + core * 0.5, color, a * 0.45), (1, color, 0)]
    c.drawCircle(x, y, r, paint(shader=rad((x, y), r, stops), blend=blend))


# ----------------------------------------------------------------- paths
def poly(pts, closed=True):
    p = skia.Path()
    if not pts:
        return p
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if closed:
        p.close()
    return p


def spline(pts, closed=True, tension=0.5):
    """Catmull-Rom spline through points as cubic Beziers."""
    path = skia.Path()
    n = len(pts)
    if n < 3:
        return poly(pts, closed)
    k = tension / 3.0 * 2.0
    path.moveTo(*pts[0])
    rng = n if closed else n - 1
    for i in range(rng):
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[0]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else pts[-1]
        c1 = (p1[0] + (p2[0] - p0[0]) * k / 2, p1[1] + (p2[1] - p0[1]) * k / 2)
        c2 = (p2[0] - (p3[0] - p1[0]) * k / 2, p2[1] - (p3[1] - p1[1]) * k / 2)
        path.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if closed:
        path.close()
    return path


def blob_pts(cx, cy, r, seed, n=10, jitter=0.22, sy=1.0, phase=0.0):
    pts = []
    for i in range(n):
        a = TAU * i / n + phase
        rr = r * (1 + jitter * (hash01(seed, i) * 2 - 1))
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * sy))
    return pts


def blob(cx, cy, r, seed, n=10, jitter=0.22, sy=1.0, phase=0.0):
    return spline(blob_pts(cx, cy, r, seed, n, jitter, sy, phase))


def taper(a, b, ra, rb):
    """Tapered capsule path between circles (a, ra) and (b, rb)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy)
    path = skia.Path()
    if d < 1e-6 or d <= abs(ra - rb):
        path.addCircle(a[0], a[1], max(ra, rb))
        return path
    ang = math.atan2(dy, dx)
    off = math.acos(clamp((ra - rb) / d, -1, 1))
    pa1 = (a[0] + ra * math.cos(ang + off), a[1] + ra * math.sin(ang + off))
    pb1 = (b[0] + rb * math.cos(ang + off), b[1] + rb * math.sin(ang + off))
    pb2 = (b[0] + rb * math.cos(ang - off), b[1] + rb * math.sin(ang - off))
    pa2 = (a[0] + ra * math.cos(ang - off), a[1] + ra * math.sin(ang - off))
    path.moveTo(*pa1)
    path.lineTo(*pb1)
    path.arcTo(skia.Rect(b[0] - rb, b[1] - rb, b[0] + rb, b[1] + rb), math.degrees(ang + off), -2 * math.degrees(off), False)
    path.lineTo(*pa2)
    path.arcTo(skia.Rect(a[0] - ra, a[1] - ra, a[0] + ra, a[1] + ra), math.degrees(ang - off), -(360 - 2 * math.degrees(off)), False)
    path.close()
    return path


def rot(p, a, o=(0, 0)):
    s, c = math.sin(a), math.cos(a)
    x, y = p[0] - o[0], p[1] - o[1]
    return (o[0] + x * c - y * s, o[1] + x * s + y * c)


def ellipse(c, x, y, rx, ry, p):
    c.drawOval(skia.Rect(x - rx, y - ry, x + rx, y + ry), p)


# ----------------------------------------------------------------- camera
class Cam:
    """Camera centred on (x, y) in world space. zoom>1 = closer."""

    def __init__(self, x=W / 2, y=H / 2, zoom=1.0, rot=0.0):
        self.x, self.y, self.zoom, self.rot = x, y, zoom, rot
        self.sx = self.sy = self.sr = 0.0

    def shake(self, t, amount, freq=14.0, seed=3):
        self.sx += noise(t * freq, seed) * amount
        self.sy += noise(t * freq, seed + 7) * amount * 0.8
        self.sr += noise(t * freq * 0.7, seed + 19) * amount * 0.0009
        return self

    def matrix(self, p=1.0):
        z = self.zoom ** p if p > 0 else 1.0
        m = skia.Matrix()
        m.preTranslate(W / 2 + self.sx, H / 2 + self.sy)
        m.preRotate(math.degrees(self.rot * p + self.sr))
        m.preScale(z, z)
        m.preTranslate(-(W / 2 + (self.x - W / 2) * p), -(H / 2 + (self.y - H / 2) * p))
        return m

    def to_screen(self, x, y, p=1.0):
        pt = self.matrix(p).mapXY(x, y)
        return (pt.x(), pt.y())

    @contextmanager
    def view(self, c, p=1.0):
        c.save()
        c.concat(self.matrix(p))
        try:
            yield
        finally:
            c.restore()

    def left(self, p=1.0):
        z = self.zoom ** p
        return W / 2 + (self.x - W / 2) * p - W / 2 / z

    def right(self, p=1.0):
        z = self.zoom ** p
        return W / 2 + (self.x - W / 2) * p + W / 2 / z

    def top(self, p=1.0):
        z = self.zoom ** p
        return H / 2 + (self.y - H / 2) * p - H / 2 / z

    def bottom(self, p=1.0):
        z = self.zoom ** p
        return H / 2 + (self.y - H / 2) * p + H / 2 / z


@contextmanager
def layer(c, a=1.0, blur=0.0, blend=None, cf=None):
    """Offscreen layer with opacity, blur (depth of field) or colour filter."""
    p = skia.Paint()
    p.setAlphaf(clamp(a))
    if blur > 0.3:
        p.setImageFilter(skia.ImageFilters.Blur(blur, blur))
    if blend:
        p.setBlendMode(BLEND[blend])
    if cf is not None:
        p.setColorFilter(cf)
    c.saveLayer(None, p)
    try:
        yield
    finally:
        c.restore()


@contextmanager
def at(c, x=0.0, y=0.0, r=0.0, s=1.0, sy=None):
    c.save()
    c.translate(x, y)
    if r:
        c.rotate(math.degrees(r))
    if s != 1.0 or sy is not None:
        c.scale(s, s if sy is None else sy)
    try:
        yield
    finally:
        c.restore()


# ----------------------------------------------------------------- sprite cache
_CACHE = {}
SAMPLING = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)


def sprite(key, w, h, fn):
    """Render fn(canvas) into a cached w x h image (with mipmaps)."""
    img = _CACHE.get(key)
    if img is None:
        s = skia.Surface(int(w), int(h))
        cv = s.getCanvas()
        cv.clear(skia.ColorTRANSPARENT)
        fn(cv)
        img = s.makeImageSnapshot().withDefaultMipmaps()
        _CACHE[key] = img
    return img


def cached(key, fn):
    v = _CACHE.get(key)
    if v is None:
        v = fn()
        _CACHE[key] = v
    return v


def draw_img(c, img, x, y, s=1.0, a=1.0, ax=0.5, ay=0.5, r=0.0, blend=None, cf=None, sx=None):
    """Draw image anchored at (ax, ay) fraction, at (x, y), scale s, rotation r."""
    p = skia.Paint()
    p.setAlphaf(clamp(a))
    if blend:
        p.setBlendMode(BLEND[blend])
    if cf is not None:
        p.setColorFilter(cf)
    c.save()
    c.translate(x, y)
    if r:
        c.rotate(math.degrees(r))
    c.scale(s if sx is None else sx, s)
    c.drawImage(img, -img.width() * ax, -img.height() * ay, SAMPLING, p)
    c.restore()


def tint_cf(color, amount):
    """Colour filter that blends towards colour by amount (atmospheric haze)."""
    r, g, b = rgb(color)
    k = 1 - amount
    return skia.ColorFilters.Matrix([
        k, 0, 0, 0, r * amount,
        0, k, 0, 0, g * amount,
        0, 0, k, 0, b * amount,
        0, 0, 0, 1, 0,
    ])


def grade_cf(sat=1.0, contrast=1.0, bright=0.0, tint=(1, 1, 1), lift=(0, 0, 0)):
    """Saturation, contrast, brightness, per-channel gain and lift."""
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    s = sat
    m = [
        lr * (1 - s) + s, lg * (1 - s), lb * (1 - s),
        lr * (1 - s), lg * (1 - s) + s, lb * (1 - s),
        lr * (1 - s), lg * (1 - s), lb * (1 - s) + s,
    ]
    out = []
    off = 0.5 * (1 - contrast) + bright
    for row in range(3):
        g = tint[row] * contrast
        out += [m[row * 3] * g, m[row * 3 + 1] * g, m[row * 3 + 2] * g, 0, off + lift[row]]
    out += [0, 0, 0, 1, 0]
    return skia.ColorFilters.Matrix(out)


# ----------------------------------------------------------------- text
_TF = {}


def typeface(name):
    tf = _TF.get(name)
    if tf is None:
        paths = {
            "cinzel": os.path.join(FONTS, "Cinzel-600.ttf"),
            "cinzel-r": os.path.join(FONTS, "Cinzel-400.ttf"),
            "inter-light": "/usr/share/fonts/opentype/inter/InterDisplay-Light.otf",
            "inter": "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf",
        }
        tf = skia.Typeface.MakeFromFile(paths[name])
        _TF[name] = tf
    return tf


def text_centered(c, s, x, y, size, color, a=1.0, face="cinzel", track=0.0, blur=0.0, blend=None):
    font = skia.Font(typeface(face), size)
    font.setEdging(skia.Font.Edging.kAntiAlias)
    widths = [font.measureText(ch) for ch in s]
    total = sum(widths) + track * size * (len(s) - 1)
    xx = x - total / 2
    p = paint(color, a, blur=blur, blend=blend)
    for ch, w in zip(s, widths):
        c.drawString(ch, xx, y, font, p)
        xx += w + track * size
    return total
