"""Illustrated 'comic' rendering style: inked outlines with a slight hand-drawn wobble,
automatic cel shading (shadow and highlight bands cut from the shape itself), hatching
and a paper texture. Any filled shape can be drawn with ink(...)."""
import math

import numpy as np
import skia

from .core import (W, H, clamp, lerp, rgb, mix, shade, paint, lin, rad, poly, spline, taper, hash01, Rng, sprite, SAMPLING)

INK = (0.10, 0.09, 0.12)
LIGHT = (-0.55, -0.83)          # direction light comes FROM (screen space, y down)


def _moved(path, dx, dy):
    p = skia.Path(path)
    p.offset(dx, dy)
    return p


def cel_bands(path, off, light=LIGHT):
    """(shadow, highlight) sub-paths of `path` for a light coming from `light`."""
    lx, ly = light
    sh = skia.Op(path, _moved(path, lx * off, ly * off), skia.PathOp.kDifference_PathOp)
    hi = skia.Op(path, _moved(path, -lx * off * 0.6, -ly * off * 0.6), skia.PathOp.kDifference_PathOp)
    return sh, hi


def wobble(seg=6.0, dev=0.6, seed=1):
    return skia.DiscretePathEffect.Make(seg, dev, seed)


def ink(c, path, fill, lw=3.0, shadow=None, highlight=None, off=None, light=LIGHT, a=1.0, ink_col=INK, wob=True,
        shader=None, hatch=0.0, hatch_ang=0.8, outline=True, shadow_a=1.0, hi_a=0.9):
    """Fill + cel shading + inked outline.

    fill: base colour. shadow/highlight: colours of the cel bands (auto from fill if None).
    off: size of the shading offset (defaults from the shape size)."""
    b = path.getBounds()
    size = max(1.0, min(b.width(), b.height()))
    if off is None:
        off = size * 0.18
    base = rgb(fill)
    if shader is not None:
        c.drawPath(path, paint(shader=shader, a=a))
    else:
        c.drawPath(path, paint(base, a))
    if shadow is not False:
        sc = rgb(shadow) if shadow is not None else shade(mix(base, (0.25, 0.2, 0.45), 0.25), -0.28)
        hc = None if highlight is False else (rgb(highlight) if highlight is not None else shade(base, 0.22))
        sh, hi = cel_bands(path, off, light)
        if sh is not None:
            c.drawPath(sh, paint(sc, a * shadow_a))
            if hatch > 0:
                hatch_lines(c, sh, size * 0.09 + 2, hatch_ang, shade(sc, -0.35), a * hatch, max(0.8, lw * 0.35))
        if hi is not None and hc is not None:
            c.drawPath(hi, paint(hc, a * hi_a))
    if outline and lw > 0:
        p = paint(ink_col, a, stroke=lw)
        if wob:
            p.setPathEffect(wobble(max(3.0, lw * 2.2), lw * 0.18, int(b.left() * 7 + b.top() * 3) & 0xFFFF))
        c.drawPath(path, p)


def stroke(c, pts, lw, col=INK, a=1.0, closed=False, smooth_=True, cap="round"):
    path = spline(pts, closed=closed) if smooth_ and len(pts) > 2 else poly(pts, closed=closed)
    c.drawPath(path, paint(col, a, stroke=lw, cap=cap))


def hatch_lines(c, region, spacing, ang, col, a, lw):
    b = region.getBounds()
    c.save()
    c.clipPath(region, skia.ClipOp.kIntersect, True)
    cx, cy = b.centerX(), b.centerY()
    R = math.hypot(b.width(), b.height()) / 2 + spacing
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    k = -R
    while k <= R:
        x0, y0 = cx + nx * k - dx * R, cy + ny * k - dy * R
        x1, y1 = cx + nx * k + dx * R, cy + ny * k + dy * R
        c.drawLine(x0, y0, x1, y1, paint(col, a, stroke=lw))
        k += spacing
    c.restore()


def union(*paths):
    out = None
    for p in paths:
        if p is None:
            continue
        out = skia.Path(p) if out is None else skia.Op(out, p, skia.PathOp.kUnion_PathOp)
    return out


def limb(a, b, c_, ra, rb, rc):
    """Two-segment limb (e.g. upper arm + forearm) as one closed outline."""
    return union(taper(a, b, ra, rb), taper(b, c_, rb, rc))


def ellipse_path(x, y, rx, ry, rot=0.0):
    p = skia.Path()
    p.addOval(skia.Rect(x - rx, y - ry, x + rx, y + ry))
    if rot:
        m = skia.Matrix()
        m.setRotate(math.degrees(rot), x, y)
        p.transform(m)
    return p


def paper(c, a=0.10):
    """Paper / canvas grain over the whole frame."""
    img = sprite(("paper",), W // 2, H // 2, _paper_fn)
    p = skia.Paint()
    p.setAlphaf(a)
    p.setBlendMode(skia.BlendMode.kMultiply)
    c.save()
    c.scale(2, 2)
    c.drawImage(img, 0, 0, SAMPLING, p)
    c.restore()


def _paper_fn(cv):
    rs = np.random.RandomState(5)
    h, w = H // 2, W // 2
    n = rs.rand(h, w)
    # soft blotches + fibres
    from scipy.ndimage import gaussian_filter
    blot = gaussian_filter(rs.rand(h, w), 18)
    blot = (blot - blot.min()) / (blot.max() - blot.min() + 1e-9)
    fib = gaussian_filter(rs.rand(h, w), (0.6, 3.0))
    fib = (fib - fib.min()) / (fib.max() - fib.min() + 1e-9)
    v = 0.78 + 0.12 * blot + 0.07 * fib + 0.03 * n
    g = (np.clip(v, 0, 1) * 255).astype(np.uint8)
    rgba = np.dstack([g, (g * 0.985).astype(np.uint8), (g * 0.95).astype(np.uint8), np.full_like(g, 255)])
    img = skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.ColorType.kRGBA_8888_ColorType)
    cv.drawImage(img, 0, 0)
