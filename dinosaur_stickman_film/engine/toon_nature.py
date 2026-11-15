"""Illustrated environments: inked clouds, mountains, volcano, trees, tree ferns,
cycads, bushes, ferns, painted grass, flowers, paths and rocks, in vivid colours."""
import math

import skia

from .core import (W, H, TAU, clamp, lerp, rgb, mix, shade, paint, lin, rad, poly, spline, blob, blob_pts, taper, hash01, Rng,
                   noise, sprite, draw_img, tint_cf, ellipse, glow)
from .toon import ink, stroke, union, ellipse_path, INK, hatch_lines
from . import nature as N

SKY = [(0, "#2f86d6"), (0.45, "#6fbdea"), (0.8, "#c6ecf2"), (1, "#fff0c2")]
LEAF = ("#2a7a2e", "#3f9a3a", "#76c64e")         # shadow, base, highlight
BARK = ("#7a4e2e", "#553219", "#9a6a40")
FERN = ("#2f8a34", "#5cb244", "#225f26")
SOFT_INK = (0.20, 0.22, 0.30)


def sky(c, stops=SKY, y0=0, y1=H):
    c.drawRect(skia.Rect(-W, y0 - H, 2 * W, y1 + H), paint(shader=lin((0, y0), (0, y1), stops)))


def cloud_sprite(seed, w=900, h=420, lw=4.0):
    def fn(cv):
        r = Rng(seed)
        path = None
        base = h * 0.78
        for i in range(11):
            u = i / 10
            hump = math.sin(math.pi * u)
            cr = h * (0.13 + 0.22 * hump) * r.u(0.8, 1.15)
            cx = w * (0.1 + 0.8 * u) + r.u(-20, 20)
            cy = base - cr * 0.7 - hump * h * 0.12
            pc = skia.Path()
            pc.addCircle(cx, cy, cr)
            path = pc if path is None else skia.Op(path, pc, skia.PathOp.kUnion_PathOp)
        flat = skia.Path()
        flat.addRRect(skia.RRect.MakeRectXY(skia.Rect(w * 0.08, base - h * 0.16, w * 0.92, base), h * 0.08, h * 0.08))
        path = skia.Op(path, flat, skia.PathOp.kUnion_PathOp)
        ink(cv, path, "#ffffff", lw, shadow="#c9d6f0", highlight=False, off=h * 0.16, ink_col=(0.36, 0.43, 0.62),
            light=(-0.3, -0.95))
    return sprite(("tcloud", seed, w, h), w, h, fn)


def clouds(c, t, specs, a=1.0):
    for x, y, s, sp, seed in specs:
        draw_img(c, cloud_sprite(seed % 5), x + sp * t, y, s, a, ay=0.75)


def mountain_sprite(key, seed, w, h, col, snow=0.25, peaks=None, lw=3.0, ink_col=(0.25, 0.3, 0.5)):
    def fn(cv):
        n = 160
        hh = N.ridge(seed, 257, 0.55)
        xs = [i / (n - 1) for i in range(n)]
        ys = []
        for i, u in enumerate(xs):
            v = hh[int(u * 256)] * 0.35
            if peaks:
                env = max(ph * math.exp(-((u - px) / pw) ** 2) for px, ph, pw in peaks)
                v = v * 0.35 + env * (0.8 + 0.2 * hh[int(u * 256)])
            ys.append(h - (0.12 + 0.86 * min(1, v)) * h)
        pts = [(0, h + 10)] + [(xs[i] * w, ys[i]) for i in range(n)] + [(w, h + 10)]
        path = poly(pts)
        base = rgb(col)
        ink(cv, path, base, lw, shadow=shade(base, -0.18), highlight=shade(base, 0.12), off=h * 0.08, ink_col=ink_col,
            light=(-0.9, -0.4), hatch=0.0)
        if snow > 0:
            cut = h * (0.06 + snow)
            for i in range(n - 1):
                if ys[i] < cut:
                    d = (cut - ys[i]) * 0.6 + 4
                    x0, x1 = xs[i] * w, xs[i + 1] * w + 1
                    q = poly([(x0, ys[i]), (x1, ys[i + 1]), (x1, ys[i + 1] + d * (0.7 + 0.5 * hash01(i, 3))), (x0, ys[i] + d)])
                    cv.drawPath(q, paint("#f6fbff"))
            cv.drawPath(poly(pts[1:-1], closed=False), paint(ink_col, stroke=lw))
        # ridge lines
        r = Rng(seed)
        for i in range(int(w / 70)):
            j = r.i(2, n - 3)
            x = xs[j] * w
            cv.drawPath(spline([(x, ys[j] + 6), (x + r.u(-20, 20), ys[j] + h * 0.15), (x + r.u(-40, 40), ys[j] + h * 0.3)],
                               closed=False), paint(ink_col, 0.35, stroke=lw * 0.5))
    return sprite(("tmtn", key), w, h + 10, fn)


def volcano(c, x, y, s, t, smoke_a=0.9):
    w, h = 620 * s, 380 * s
    pts = [(x - w / 2, y), (x - w * 0.09, y - h), (x + w * 0.09, y - h), (x + w / 2, y)]
    body = spline(pts + [(x + w / 2, y + 40), (x - w / 2, y + 40)], closed=True, tension=0.15)
    ink(c, body, "#8a6f86", 3.0 * s, shadow="#6a5268", highlight="#a88ea2", off=60 * s, ink_col=(0.25, 0.22, 0.35),
        light=(-0.9, -0.4))
    c.drawPath(poly([(x - w * 0.09, y - h), (x - w * 0.03, y - h * 0.9), (x + w * 0.04, y - h * 0.93), (x + w * 0.09, y - h)]),
               paint((1, 0.45, 0.15), 0.9))
    for i in range(12):
        age = ((t * 0.12 + i / 12) % 1.0)
        px = x + age * 160 * s + math.sin(age * 4 + i) * 20 * s
        py = y - h - age * 420 * s
        r = (22 + 70 * age) * s
        ink(c, ellipse_path(px, py, r, r * 0.85), mix((0.62, 0.6, 0.66), (0.85, 0.85, 0.9), age), 2.4 * s, shadow=(0.5, 0.48, 0.56),
            highlight=False, off=r * 0.3, ink_col=(0.3, 0.28, 0.36), a=smoke_a * (1 - age) ** 0.6)


def _crown(cv, cx, cy, rr, seed, pal, lw, scallops=True):
    r = Rng(seed)
    path = None
    for k in range(7):
        a = r.u(0, TAU)
        d = r.u(0, rr * 0.55)
        pc = blob(cx + math.cos(a) * d, cy + math.sin(a) * d * 0.6, rr * r.u(0.45, 0.62), r.i(0, 999), 10, 0.18, 0.85)
        path = pc if path is None else skia.Op(path, pc, skia.PathOp.kUnion_PathOp)
    dark, base, light = (rgb(p) for p in pal)
    ink(cv, path, base, lw, shadow=dark, highlight=light, off=rr * 0.22)
    if scallops:
        cv.save()
        cv.clipPath(path, skia.ClipOp.kIntersect, True)
        for k in range(14):
            a = r.u(0, TAU)
            d = r.u(0.1, 0.8) * rr
            px, py = cx + math.cos(a) * d, cy + math.sin(a) * d * 0.6
            cv.drawPath(spline([(px - rr * 0.12, py), (px, py - rr * 0.08), (px + rr * 0.12, py)], closed=False),
                        paint(shade(dark, -0.2), 0.7, stroke=lw * 0.6))
        cv.restore()


def tree_sprite(kind, seed, h=900):
    w = int(h * (0.8 if kind == "broad" else 0.7))
    lw = h / 180.0

    def fn(cv):
        r = Rng(seed)
        cx = w / 2
        if kind == "broad":
            tw = h * 0.045
            trunk = spline([(cx - tw * 2.2, h - 2), (cx - tw * 1.1, h * 0.8), (cx - tw * 0.8, h * 0.45), (cx - tw * 0.6, h * 0.3),
                            (cx + tw * 0.6, h * 0.3), (cx + tw * 0.9, h * 0.45), (cx + tw * 1.2, h * 0.8), (cx + tw * 2.3, h - 2)],
                           closed=True, tension=0.4)
            ink(cv, trunk, BARK[0], lw, shadow=BARK[1], highlight=BARK[2], off=tw * 0.7, hatch=0.5)
            for k in range(5):
                x = cx + r.u(-0.6, 0.6) * tw
                cv.drawPath(spline([(x, h * r.u(0.5, 0.7)), (x + r.u(-6, 6), h * r.u(0.75, 0.85)), (x + r.u(-6, 6), h * 0.97)],
                                   closed=False), paint(INK, 0.5, stroke=lw * 0.6))
            for side in (-1, 1):
                ink(cv, taper((cx, h * 0.42), (cx + side * w * 0.28, h * 0.27), tw * 0.5, tw * 0.2), BARK[0], lw, shadow=BARK[1],
                    off=tw * 0.3)
            for k in range(5):
                a = math.pi + (k + 0.5) / 5 * math.pi
                _crown(cv, cx + math.cos(a) * w * 0.27, h * 0.27 + math.sin(a) * h * 0.13, w * 0.24, seed * 10 + k, LEAF, lw)
            _crown(cv, cx, h * 0.17, w * 0.27, seed * 10 + 9, LEAF, lw)
        else:  # araucaria-like: tall trunk with tiered pads
            tw = h * 0.025
            trunk = poly([(cx - tw * 1.8, h - 2), (cx - tw * 0.7, h * 0.12), (cx + tw * 0.7, h * 0.12), (cx + tw * 1.8, h - 2)])
            ink(cv, trunk, BARK[0], lw, shadow=BARK[1], highlight=BARK[2], off=tw * 0.6, hatch=0.4)
            for i in range(5):
                u = i / 4
                y = h * (0.1 + 0.24 * u)
                spread = w * (0.2 + 0.24 * math.sin(math.pi * (0.3 + 0.7 * u)))
                for side in (-1, 1):
                    stroke(cv, [(cx, y + 12), (cx + side * spread * 0.8, y + r.u(-4, 10))], lw * 1.4, BARK[1])
                pad = blob(cx, y, spread, seed * 7 + i, 12, 0.12, 0.22)
                ink(cv, pad, LEAF[1], lw, shadow=LEAF[0], highlight=LEAF[2], off=spread * 0.12)
    return sprite(("ttree", kind, seed, h), w, h, fn)


def tree(c, kind, seed, x, y, height, t=0.0, wind=0.015, haze=None, haze_a=0.0, flip=False):
    img = tree_sprite(kind, seed % 4)
    s = height / img.height()
    sw = wind * (noise(t * 0.45, seed) + 0.4 * noise(t * 1.3, seed + 3))
    cf = tint_cf(haze, haze_a) if haze is not None and haze_a > 0 else None
    draw_img(c, img, x, y, s, 1.0, ax=0.5, ay=1.0, r=sw, cf=cf, sx=-s if flip else None)


def tree_fern_sprite(seed, h=520):
    w = int(h * 1.15)
    lw = h / 150.0

    def fn(cv):
        r = Rng(seed)
        cx = w / 2
        top = (cx + r.u(-20, 20), h * 0.34)
        trunk = spline([(cx - 18, h - 2), (cx - 12, h * 0.7), (top[0] - 9, top[1]), (top[0] + 9, top[1]), (cx + 12, h * 0.7),
                        (cx + 18, h - 2)], closed=True)
        ink(cv, trunk, "#6b4a2e", lw, shadow="#4a3020", off=8, hatch=0.6, hatch_ang=-0.6)
        for i in range(13):
            u = i / 12
            ang = -math.pi / 2 + (u - 0.5) * 3.3
            ln = h * r.u(0.4, 0.52)
            droop = 1.3 * (1 if math.cos(ang) > 0 else -1) * abs(math.cos(ang)) + 0.3
            path, spine = N.frond_path(top[0], top[1], ang, ln, droop, ln * 0.14, i, n=14)
            ink(cv, path, FERN[1] if i % 2 else FERN[0], lw * 0.55, shadow=False, wob=False)
            stroke(cv, spine, lw * 0.9, FERN[2])
    return sprite(("ttfern", seed, h), w, h, fn)


def fern(c, x, y, size, seed, t=0.0, wind=0.06, col=None, lw=2.0, flat=0.0, shake=0.0, dark=0.0):
    r = Rng(seed)
    n = r.i(6, 9)
    base = rgb(col or FERN[1])
    if dark:
        base = shade(base, -dark)
    for i in range(n):
        u = (i + 0.5) / n
        ang = -math.pi / 2 + (u - 0.5) * 2.5 + r.u(-0.1, 0.1)
        sw = wind * noise(t * 0.9 + i * 0.37, seed) + shake * noise(t * 22 + i, seed + 5) * 0.3
        ang = lerp(ang + sw * 0.6, (0 if math.cos(ang) > 0 else math.pi) + 0.05, flat)
        ln = size * r.u(0.7, 1.05)
        side = 1 if math.cos(ang) >= 0 else -1
        path, spine = N.frond_path(x, y, ang, ln, (1.1 + flat) * side * abs(math.cos(ang)) * 0.9 + 0.25 * side, ln * 0.17,
                                   seed * 31 + i, n=12, sway=sw)
        col_i = base if i % 2 else shade(base, 0.15)
        ink(c, path, col_i, lw * 0.6, shadow=False, wob=False)
        stroke(c, spine, lw, shade(base, -0.35))


def bush(c, x, y, r_, seed, pal=LEAF, lw=3.0, shake=0.0, t=0.0):
    r = Rng(seed)
    path = None
    for i in range(8):
        a = r.u(math.pi, TAU)
        d = r.u(0, 0.75)
        jx = shake * noise(t * 20 + i, seed) * r_ * 0.06
        pc = blob(x + math.cos(a) * r_ * d + jx, y + math.sin(a) * r_ * d * 0.55 - r_ * 0.15, r_ * r.u(0.38, 0.55), r.i(0, 999), 9,
                  0.2, 0.8)
        path = pc if path is None else skia.Op(path, pc, skia.PathOp.kUnion_PathOp)
    flat = skia.Path()
    flat.addRect(skia.Rect(x - r_ * 0.9, y - r_ * 0.3, x + r_ * 0.9, y + 2))
    path = skia.Op(path, flat, skia.PathOp.kUnion_PathOp)
    ink(c, path, pal[1], lw, shadow=pal[0], highlight=pal[2], off=r_ * 0.25)


def rock(c, x, y, w, h, seed, lw=3.0, col="#9a9488", moss=True):
    pts = blob_pts(x, y - h * 0.45, w * 0.5, seed, 9, 0.18, h / w)
    path = spline(pts, closed=True, tension=0.35)
    flat = skia.Path()
    flat.addRect(skia.Rect(x - w * 0.6, y - 1, x + w * 0.6, y + h))
    path = skia.Op(path, flat, skia.PathOp.kDifference_PathOp)
    ink(c, path, col, lw, shadow=shade(rgb(col), -0.3), highlight=shade(rgb(col), 0.2), off=h * 0.3, hatch=0.5)
    if moss:
        c.save()
        c.clipPath(path, skia.ClipOp.kIntersect, True)
        c.drawPath(blob(x - w * 0.1, y - h * 0.9, w * 0.4, seed + 3, 9, 0.3, 0.35), paint("#6bb04a"))
        c.restore()
        c.drawPath(path, paint(INK, stroke=lw))


def meadow(c, x0, x1, y, depth, t, seed=1, cols=("#58a83a", "#79c446", "#3e8a2c"), density=1.0, flowers=True, lw=2.0):
    """Painted grass field: base gradient + brush strokes + flowers, from y down to y+depth."""
    c.drawRect(skia.Rect(x0, y, x1, y + depth), paint(shader=lin((0, y), (0, y + depth), [(0, cols[1]), (1, cols[0])])))
    r = Rng(seed)
    n = int((x1 - x0) * depth / 900 * density)
    p1, p2, p3 = skia.Path(), skia.Path(), skia.Path()
    for i in range(n):
        u = r.u() ** 0.8
        yy = y + u * depth
        xx = r.u(x0, x1)
        hgt = (6 + 20 * u) * r.u(0.6, 1.3)
        lean = (r.u(-0.4, 0.4) + 0.25 * noise(t * 0.8 + xx * 0.003, seed))
        tip = (xx + math.sin(lean) * hgt, yy - math.cos(lean) * hgt)
        w = 1.2 + 2.5 * u
        pp = (p1, p2, p3)[i % 3]
        pp.moveTo(xx - w, yy)
        pp.quadTo(xx + (tip[0] - xx) * 0.5 - w * 0.3, yy - hgt * 0.5, tip[0], tip[1])
        pp.quadTo(xx + (tip[0] - xx) * 0.5 + w * 0.3, yy - hgt * 0.5, xx + w, yy)
        pp.close()
    c.drawPath(p1, paint(cols[2], 0.85))
    c.drawPath(p2, paint(shade(rgb(cols[1]), 0.15), 0.9))
    c.drawPath(p3, paint(cols[0], 0.9))
    if flowers:
        for i in range(int((x1 - x0) * depth / 9000 * density)):
            u = r.u() ** 0.7
            yy = y + u * depth
            xx = r.u(x0, x1)
            fr = 2 + 5 * u
            col = r.choice(["#fff4a8", "#ffffff", "#ff9ec4", "#ffd34e", "#c8a6ff"])
            for k in range(5):
                a = k / 5 * TAU
                c.drawCircle(xx + math.cos(a) * fr, yy + math.sin(a) * fr * 0.7, fr * 0.7, paint(col))
            c.drawCircle(xx, yy, fr * 0.55, paint("#f5a623"))


def grass_tufts(c, x0, x1, y, t, seed=3, h=60, col="#3e8a2c", lw=2.2, spacing=70, shake=None):
    r = Rng(seed)
    x = x0
    while x < x1:
        hh = h * r.u(0.6, 1.2)
        path = skia.Path()
        for k in range(7):
            a = -math.pi / 2 + (k - 3) * 0.22 + 0.15 * noise(t * 0.8 + x * 0.01 + k, seed) + (shake(x) if shake else 0)
            ln = hh * r.u(0.6, 1.0)
            tip = (x + math.cos(a) * ln, y + math.sin(a) * ln)
            path.moveTo(x - 4, y + 2)
            path.quadTo(x + math.cos(a) * ln * 0.5 - 2, y + math.sin(a) * ln * 0.5, tip[0], tip[1])
            path.quadTo(x + math.cos(a) * ln * 0.5 + 2, y + math.sin(a) * ln * 0.5, x + 4, y + 2)
            path.close()
        ink(c, path, col, lw, shadow=False, wob=False)
        x += spacing * r.u(0.6, 1.4)


def dirt_path(c, pts_top, pts_bot, lw=3.0, col="#d9a964", seed=2):
    path = spline(pts_top + list(reversed(pts_bot)), closed=True, tension=0.4)
    ink(c, path, col, lw, shadow="#b98642", highlight="#ecc684", off=10, light=(-0.2, -1.0))
    r = Rng(seed)
    b = path.getBounds()
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    for i in range(int(b.width() / 25)):
        x = r.u(b.left(), b.right())
        y = r.u(b.top(), b.bottom())
        rr = r.u(2, 6)
        ink(c, ellipse_path(x, y, rr * 1.4, rr), "#a98f78", 1.2, shadow=False, wob=False)
    c.restore()
