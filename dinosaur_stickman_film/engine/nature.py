"""Environment painting: skies, clouds, mountains, volcanoes, trees, ferns, grass,
water, mist and light. Heavy static pieces are rendered once into sprites."""
import math

import numpy as np
import skia

from .core import (W, H, TAU, clamp, lerp, smooth, noise, fbm, hash01, Rng, rgb, mix, shade, ci, c4, paint, lin, rad,
                   poly, spline, blob, blob_pts, taper, ellipse, glow, sprite, draw_img, tint_cf, at, inv)


# ----------------------------------------------------------------- sky & lights
def sky(c, stops, y0=0, y1=H):
    c.drawRect(skia.Rect(-W, y0 - H, W * 2, y1 + H), paint(shader=lin((0, y0), (0, y1), stops)))


def sun(c, x, y, r, color="#fff4d6", a=1.0, halo=6.0):
    glow(c, x, y, r * halo, color, 0.35 * a)
    glow(c, x, y, r * 2.2, color, 0.6 * a)
    c.drawCircle(x, y, r, paint(color, a))


def stars(c, t, seed=1, n=420, y1=H * 0.7, a=1.0):
    r = Rng(seed)
    for i in range(n):
        x, y = r.u(-200, W + 200), r.u(-100, y1)
        s = r.u(0.4, 1.0) ** 3 * 2.2 + 0.4
        tw = 0.65 + 0.35 * math.sin(t * r.u(0.8, 3.0) + r.u(0, 6.28))
        fade = 1 - clamp((y - y1 * 0.6) / (y1 * 0.4))
        c.drawCircle(x, y, s, paint((0.92, 0.94, 1.0), a * tw * fade * r.u(0.4, 1.0)))


def moon(c, x, y, r, a=1.0):
    glow(c, x, y, r * 7, (0.55, 0.65, 0.95), 0.22 * a)
    glow(c, x, y, r * 2.4, (0.85, 0.9, 1.0), 0.35 * a)
    c.drawCircle(x, y, r, paint(shader=rad((x - r * 0.3, y - r * 0.3), r * 1.4, [(0, "#fbfbf4"), (1, "#c9cfdd")]), a=a))
    rr = Rng(5)
    for i in range(7):
        cx, cy = x + rr.u(-0.6, 0.6) * r, y + rr.u(-0.6, 0.6) * r
        if math.hypot(cx - x, cy - y) < r * 0.8:
            c.drawCircle(cx, cy, r * rr.u(0.06, 0.18), paint((0.6, 0.63, 0.72), 0.35 * a))


def cloud_sprite(seed, w=900, h=360, lit="#ffffff", shadow="#9aa6b8", soft=10.0):
    def fn(cv):
        r = Rng(seed)
        puffs = []
        n = 14
        for i in range(n):
            u = i / (n - 1)
            px = w * (0.12 + 0.76 * u) + r.u(-30, 30)
            hump = math.sin(math.pi * u)
            pr = h * (0.16 + 0.22 * hump) * r.u(0.75, 1.15)
            py = h * 0.72 - pr * 0.55 - hump * h * 0.12 + r.u(-10, 10)
            puffs.append((px, py, pr))
        base = skia.Path()
        for px, py, pr in puffs:
            base.addCircle(px, py, pr)
        base.addRect(skia.Rect(w * 0.12, h * 0.6, w * 0.88, h * 0.74))
        cv.drawPath(base, paint(shadow, 1.0, blur=soft))
        cv.save()
        cv.clipPath(base, skia.ClipOp.kIntersect, True)
        for px, py, pr in puffs:
            cv.drawCircle(px - pr * 0.18, py - pr * 0.25, pr * 0.82, paint(lit, 0.9, blur=pr * 0.25))
        cv.restore()
        cv.drawRect(skia.Rect(0, h * 0.70, w, h), paint(shadow, 0.0))
    return sprite(("cloud", seed, w, h, str(lit), str(shadow), soft), w, h, fn)


def clouds(c, t, specs, lit, shadow, a=1.0, cam=None):
    """specs: list of (x, y, scale, speed, seed). Clouds drift with time."""
    for x, y, s, sp, seed in specs:
        img = cloud_sprite(seed % 6, lit=lit, shadow=shadow)
        xx = x + sp * t
        draw_img(c, img, xx, y, s, a, ay=0.7)


# ----------------------------------------------------------------- mountains
def ridge(seed, n=257, rough=0.55, amp=1.0):
    r = Rng(seed)
    h = np.zeros(n)
    h[0], h[-1] = r.u(0.2, 0.6), r.u(0.2, 0.6)
    step = n - 1
    scale = amp
    while step > 1:
        half = step // 2
        for i in range(half, n - 1, step):
            h[i] = (h[i - half] + h[i + half]) / 2 + r.n(scale * 0.5)
        scale *= rough
        step = half
    h -= h.min()
    h /= max(h.max(), 1e-6)
    return h


def mountain_sprite(key, seed, w, h, top, base, light, snow=0.0, forest=None, peaks=None, rough=0.55,
                    sun_dir=1.0, haze=None, haze_a=0.0, ridge_min=0.15):
    """A mountain range image: ridge from fractal noise (optionally shaped by peaks=[(x_frac, height_frac, width_frac)])."""
    def fn(cv):
        n = 257
        hh = ridge(seed, n, rough) * 0.35
        xs = np.linspace(0, 1, n)
        if peaks:
            env = np.zeros(n)
            for px, ph, pw in peaks:
                env = np.maximum(env, ph * np.exp(-((xs - px) / pw) ** 2))
            hh = hh * 0.35 + env * (0.75 + 0.25 * ridge(seed + 9, n, 0.6))
        hh = ridge_min + hh * (1 - ridge_min)
        hh = np.clip(hh, 0, 1)
        ys = h - hh * h * 0.98
        pts = [(0, h)] + [(xs[i] * w, ys[i]) for i in range(n)] + [(w, h)]
        path = poly(pts)
        cv.drawPath(path, paint(shader=lin((0, h * 0.0), (0, h), [(0, top), (1, base)])))
        cv.save()
        cv.clipPath(path, skia.ClipOp.kIntersect, True)
        # slope shading: quads that follow the ridge line
        dx = w / (n - 1)
        for i in range(n - 1):
            slope = (ys[i + 1] - ys[i]) / dx * sun_dir
            k = clamp(-slope * 1.6, -1, 1)
            col = light if k > 0 else (0, 0, 0)
            al = abs(k) * (0.38 if k > 0 else 0.25)
            x0, x1 = xs[i] * w, xs[i + 1] * w + 0.8
            ytop = min(ys[i], ys[i + 1])
            q = poly([(x0, ys[i]), (x1, ys[i + 1]), (x1 + (x1 - x0) * 0.0, h), (x0, h)])
            cv.drawPath(q, paint(shader=lin((0, ytop), (0, ytop + h * 0.5), [(0, col, al), (1, col, 0)])))
        # gullies
        r = Rng(seed + 3)
        for i in range(int(w / 9)):
            x = r.u(0, w)
            j = int(x / w * (n - 1))
            y0 = ys[j] + r.u(4, 30)
            ln = r.u(0.08, 0.35) * h
            cv.drawLine(x, y0, x + r.u(-14, 14), y0 + ln, paint((0, 0, 0), r.u(0.04, 0.1), stroke=r.u(1, 3)))
        if snow > 0:
            cut = h * (0.02 + snow)
            for i in range(n - 1):
                if ys[i] < cut or ys[i + 1] < cut:
                    d0 = max(0.0, cut - ys[i]) * 0.8 + 3
                    d1 = max(0.0, cut - ys[i + 1]) * 0.8 + 3
                    x0, x1 = xs[i] * w, xs[i + 1] * w + 0.8
                    q = poly([(x0, ys[i]), (x1, ys[i + 1]), (x1, ys[i + 1] + d1), (x0, ys[i] + d0)])
                    cv.drawPath(q, paint("#eef2f8", 0.85))
        if forest:
            fr = Rng(seed + 11)
            fc, fy = forest
            cnt = int(w / 3.5)
            for i in range(cnt):
                x = fr.u(0, w)
                j = int(x / w * (n - 1))
                ymin = max(ys[j] + 12, h * fy)
                y = fr.u(ymin, h)
                s = fr.u(4, 10) * (0.6 + 0.8 * (y / h))
                col = shade(fc, fr.u(-0.25, 0.1))
                cv.drawPath(poly([(x, y - s * 2.6), (x - s, y), (x + s, y)]), paint(col, 0.9))
        if haze is not None:
            cv.drawRect(skia.Rect(0, 0, w, h), paint(shader=lin((0, 0), (0, h), [(0, haze, haze_a * 0.4), (1, haze, haze_a)])))
        cv.restore()
    return sprite(("mtn", key), w, h, fn)


def volcano_sprite(key, w, h, top, base, light):
    def fn(cv):
        cx = w / 2
        r = Rng(7)
        pts = [(0, h)]
        for i in range(0, 61):
            u = i / 60
            x = u * w
            d = abs(u - 0.5) * 2
            y = h * (0.1 + 0.9 * (d ** 1.5)) + r.u(-5, 5) * d
            if d < 0.09:
                y = h * 0.1 + (0.09 - d) * h * 0.25
            pts.append((x, y))
        pts.append((w, h))
        path = poly(pts)
        cv.drawPath(path, paint(shader=lin((0, 0), (0, h), [(0, shade(top, -0.15)), (1, base)])))
        cv.save()
        cv.clipPath(path, skia.ClipOp.kIntersect, True)
        # sunlit flank (right) and shadowed flank (left)
        cv.drawPath(poly([(cx, h * 0.08), (w, h * 0.9), (w, h), (cx + 10, h)]), paint(light, 0.22, blur=10))
        cv.drawPath(poly([(cx, h * 0.08), (0, h * 0.9), (0, h), (cx - 10, h)]), paint((0, 0, 0), 0.25, blur=10))
        for i in range(70):
            x = r.u(0.05, 0.95) * w
            k = (x - cx) / (w / 2)
            y0 = h * (0.12 + 0.3 * abs(k))
            cv.drawLine(cx + k * w * 0.05, h * 0.12, x + k * 40, h, paint((0, 0, 0), r.u(0.05, 0.14), stroke=r.u(1.5, 5)))
            if r.u() < 0.4:
                cv.drawLine(cx + k * w * 0.05 + 3, h * 0.12, x + k * 40 + 3, h, paint(light, 0.06, stroke=r.u(1, 3)))
        # faint lava streaks from the crater
        for i in range(3):
            k = r.u(-0.3, 0.3)
            cv.drawPath(spline([(cx + k * 30, h * 0.1), (cx + k * 90, h * 0.25), (cx + k * 160, h * 0.38)], closed=False),
                        paint((1.0, 0.35, 0.1), 0.35, stroke=3, blur=2))
        # haze at the foot
        cv.drawRect(skia.Rect(0, 0, w, h), paint(shader=lin((0, h * 0.5), (0, h), [(0, (1, 1, 1), 0.0), (1, (1, 1, 1), 0.12)])))
        cv.restore()
    return sprite(("volc", key), w, h, fn)


def smoke(c, x, y, t, scale=1.0, col=(0.35, 0.33, 0.33), a=0.6, drift=60.0, n=16, rise=110.0, seed=4, life=8.0):
    for i in range(n):
        age = ((t + i * life / n) % life) / life
        k = hash01(i, seed)
        px = x + (age ** 1.4) * drift * scale + noise(t * 0.3 + i, seed) * 10 * scale
        py = y - age * rise * scale * 2.2
        r = (12 + age * 70 * (0.7 + 0.6 * k)) * scale
        al = a * math.sin(math.pi * min(1, age * 1.2)) * 0.5
        c.drawCircle(px, py, r, paint(mix(col, (0.6, 0.58, 0.56), age * 0.5), al, blur=r * 0.45))


# ----------------------------------------------------------------- trees
def _leaf_pad(cv, x, y, rx, ry, seed, dark, mid, lightc, n=9):
    path = spline(blob_pts(x, y, rx, seed, n, 0.25, ry / rx))
    cv.drawPath(path, paint(dark))
    hp = spline(blob_pts(x - rx * 0.12, y - ry * 0.22, rx * 0.78, seed + 1, n, 0.25, ry / rx * 0.8))
    cv.drawPath(hp, paint(mid))
    tp = spline(blob_pts(x - rx * 0.25, y - ry * 0.42, rx * 0.45, seed + 2, 8, 0.3, ry / rx * 0.7))
    cv.drawPath(tp, paint(lightc, 0.9))


def araucaria_sprite(seed, h=1000, pal=("#1f3b22", "#2f5a2e", "#5f8f45"), trunk="#4a3a2c"):
    w = int(h * 0.62)

    def fn(cv):
        r = Rng(seed)
        cx = w / 2
        tw = h * 0.018
        lean = r.u(-0.04, 0.04) * h
        cv.drawPath(poly([(cx - tw * 1.6, h), (cx + lean - tw * 0.6, h * 0.12), (cx + lean + tw * 0.6, h * 0.12), (cx + tw * 1.6, h)]),
                    paint(shader=lin((cx - tw, 0), (cx + tw, 0), [(0, shade(trunk, -0.3)), (0.6, trunk), (1, shade(trunk, 0.15))])))
        dark, mid, lt = pal
        tiers = 6
        for i in range(tiers):
            u = i / (tiers - 1)
            y = h * (0.08 + 0.22 * u)
            spread = w * (0.22 + 0.26 * math.sin(math.pi * (0.35 + 0.65 * u)))
            for side in (-1, 1):
                bx = cx + lean * (1 - u) + side * spread
                cv.drawLine(cx + lean * (1 - u), y + 10, bx, y + r.u(-6, 14), paint(shade(trunk, -0.2), 1, stroke=h * 0.006))
                _leaf_pad(cv, bx - side * spread * 0.35, y, spread * 0.62, h * 0.035, r.i(0, 999), dark, mid, lt)
        _leaf_pad(cv, cx + lean, h * 0.06, w * 0.18, h * 0.04, r.i(0, 999), dark, mid, lt)
    return sprite(("arauc", seed, h, pal), w, h, fn)


def frond_path(x, y, ang, length, droop, leaflet, seed, n=14, curl=0.0, both=True, sway=0.0):
    """Fern/palm frond: a curved spine with leaflets on both sides, as one path."""
    path = skia.Path()
    pts = []
    a = ang
    px, py = x, y
    seg = length / n
    for i in range(n + 1):
        pts.append((px, py, a))
        a += droop / n + curl * (i / n) + sway / n
        px += math.cos(a) * seg
        py += math.sin(a) * seg
    spine = [(p[0], p[1]) for p in pts]
    for i in range(1, n):
        x0, y0, aa = pts[i]
        u = i / n
        ll = leaflet * math.sin(math.pi * (0.15 + 0.85 * u)) * (1 - u * 0.6)
        for side in ((-1, 1) if both else (1,)):
            la = aa + side * (1.05 - 0.3 * u) + 0.25
            tip = (x0 + math.cos(la) * ll, y0 + math.sin(la) * ll)
            nxt = pts[i + 1]
            path.addPoly([(x0, y0), tip, ((x0 + nxt[0]) / 2, (y0 + nxt[1]) / 2)], True)
    return path, spine


def treefern_sprite(seed, h=700, pal=("#24461f", "#3f7a33", "#7fb352"), trunk="#3b2e24"):
    w = int(h * 1.1)

    def fn(cv):
        r = Rng(seed)
        cx = w / 2
        top = (cx + r.u(-30, 30), h * 0.3)
        cv.drawPath(spline([(cx - 16, h), (cx - 10, h * 0.7), (top[0] - 8, top[1]), (top[0] + 8, top[1]), (cx + 10, h * 0.7),
                            (cx + 16, h)], closed=True), paint(trunk))
        for i in range(30):
            yy = lerp(h, top[1], i / 30)
            cv.drawLine(cx - 14, yy, cx + 12, yy - 6, paint(shade(trunk, -0.3), 0.6, stroke=2))
        n = 13
        for i in range(n):
            u = i / (n - 1)
            ang = -math.pi / 2 + (u - 0.5) * 3.2 + r.u(-0.1, 0.1)
            ln = h * r.u(0.38, 0.5)
            path, spine = frond_path(top[0], top[1], ang, ln, 1.3 * (1 if math.cos(ang) > 0 else -1) * abs(math.cos(ang)) + 0.3,
                                     ln * 0.13, i)
            col = pal[0] if i % 2 else pal[1]
            cv.drawPath(path, paint(col))
            cv.drawPath(poly(spine, closed=False), paint(shade(col, -0.3), stroke=2.5))
        for i in range(5):
            ang = -math.pi / 2 + r.u(-0.8, 0.8)
            path, spine = frond_path(top[0], top[1], ang, h * 0.3, 0.5 * (1 if math.cos(ang) > 0 else -1), h * 0.035, 50 + i)
            cv.drawPath(path, paint(pal[2]))
    return sprite(("tfern", seed, h, pal), w, h, fn)


def cycad_sprite(seed, h=380, pal=("#2a4a22", "#4e7d36", "#8ab557"), trunk="#5a4632"):
    w = int(h * 1.3)

    def fn(cv):
        r = Rng(seed)
        cx = w / 2
        tt = h * 0.45
        cv.drawPath(spline([(cx - 40, h), (cx - 34, tt), (cx + 34, tt), (cx + 40, h)]), paint(trunk))
        for i in range(10):
            for j in range(4):
                x = cx - 30 + j * 20 + (i % 2) * 10
                y = h - 12 - i * (h - tt) / 10
                cv.drawPath(poly([(x - 8, y), (x, y - 8), (x + 8, y), (x, y + 8)]), paint(shade(trunk, -0.25), 0.7, stroke=2))
        for i in range(12):
            ang = -math.pi / 2 + (i / 11 - 0.5) * 3.0
            path, spine = frond_path(cx, tt + 6, ang, h * r.u(0.45, 0.6), 0.7 * (1 if math.cos(ang) > 0 else -1), h * 0.09, i)
            cv.drawPath(path, paint(pal[i % 3]))
    return sprite(("cycad", seed, h, pal), w, h, fn)


def broadleaf_sprite(seed, h=1100, pal=("#1c3520", "#2e5a2c", "#5d8f3e"), trunk="#3d3026"):
    w = int(h * 1.0)

    def fn(cv):
        r = Rng(seed)
        cx = w / 2
        # trunk with buttress roots and branches
        tp = [(cx - 110, h), (cx - 50, h * 0.86), (cx - 34, h * 0.45), (cx - 20, h * 0.36), (cx + 20, h * 0.36), (cx + 36, h * 0.5),
              (cx + 55, h * 0.86), (cx + 120, h)]
        cv.drawPath(spline(tp), paint(shader=lin((cx - 60, 0), (cx + 60, 0), [(0, shade(trunk, -0.35)), (0.6, trunk), (1, shade(trunk, 0.2))])))
        for i in range(14):
            x = cx + r.u(-30, 30)
            cv.drawLine(x, h * r.u(0.45, 0.6), x + r.u(-8, 8), h * r.u(0.8, 0.98), paint(shade(trunk, -0.4), 0.5, stroke=r.u(2, 5)))
        for side in (-1, 1):
            cv.drawPath(taper((cx, h * 0.42), (cx + side * w * 0.3, h * 0.24), 22, 8), paint(trunk))
        dark, mid, lt = pal
        pads = []
        for i in range(26):
            a = r.u(math.pi * 1.05, math.pi * 1.95)
            d = r.u(0.1, 1.0) ** 0.6
            pads.append((cx + math.cos(a) * w * 0.42 * d, h * 0.3 + math.sin(a) * h * 0.25 * d, r.u(0.12, 0.2) * w))
        pads.sort(key=lambda p: -p[1])
        for x, y, rr in pads:
            _leaf_pad(cv, x, y, rr, rr * 0.75, r.i(0, 999), dark, mid, lt)
    return sprite(("broad", seed, h, pal), w, h, fn)


def tree(c, kind, seed, x, y, height, t=0.0, wind=0.02, haze=None, haze_a=0.0, dark=0.0, flip=False, a=1.0, sway_extra=0.0):
    """Draw a tree sprite with its base at (x, y)."""
    if kind == "arauc":
        img = araucaria_sprite(seed % 4)
    elif kind == "tfern":
        img = treefern_sprite(seed % 4)
    elif kind == "cycad":
        img = cycad_sprite(seed % 3)
    else:
        img = broadleaf_sprite(seed % 3)
    s = height / img.height()
    sw = wind * (noise(t * 0.45, seed) + 0.4 * noise(t * 1.3, seed + 3)) + sway_extra
    cf = None
    if haze is not None and haze_a > 0:
        cf = tint_cf(haze, haze_a)
    if dark > 0:
        cf = tint_cf((0, 0, 0), dark) if cf is None else skia.ColorFilters.Compose(cf, tint_cf((0, 0, 0), dark))
    draw_img(c, img, x, y, s, a, ax=0.5, ay=1.0, r=sw, cf=cf, sx=-s if flip else None)


def forest_band_sprite(key, w, h, dark, mid, light, seed=1, density=1.0, tall=1.0):
    """A dense wall of distant canopy silhouettes."""
    def fn(cv):
        r = Rng(seed)
        base = poly([(0, h * 0.55), (w, h * 0.55), (w, h), (0, h)])
        cv.drawPath(base, paint(dark))
        n = int(w / 26 * density)
        items = []
        for i in range(n):
            x = r.u(-40, w + 40)
            kind = r.u()
            hh = r.u(0.35, 1.0) * h * 0.58 / 1.5
            items.append((x, kind, hh, r.i(0, 9999)))
        for x, kind, hh, sd in items:
            y = h * 0.62
            if kind < 0.3:  # conifer spire
                cv.drawPath(poly([(x, y - hh * 1.5), (x - hh * 0.2, y), (x + hh * 0.2, y)]), paint(shade(dark, r.u(-0.1, 0.08))))
            elif kind < 0.42:  # tall tree-fern crown
                cv.drawLine(x, y, x + r.u(-6, 6), y - hh * 1.1, paint(dark, stroke=3))
                for k in range(7):
                    a = math.pi + (k / 6) * math.pi
                    cv.drawLine(x, y - hh * 1.1, x + math.cos(a) * hh * 0.4, y - hh * 1.1 + math.sin(a) * hh * 0.2 + hh * 0.18,
                                paint(dark, stroke=4))
            else:
                cv.drawPath(blob(x, y - hh * 0.45, hh * 0.5, sd, 10, 0.22, 0.85), paint(shade(dark, r.u(-0.08, 0.06))))
        # light tops
        r2 = Rng(seed + 5)
        for i in range(int(n * 0.7)):
            x = r2.u(0, w)
            y = h * r2.u(0.45, 0.62)
            cv.drawPath(blob(x, y, r2.u(8, 22) * tall, r2.i(0, 9999), 7, 0.3, 0.6), paint(mid, 0.55))
        cv.drawRect(skia.Rect(0, 0, w, h), paint(shader=lin((0, h * 0.2), (0, h), [(0, light, 0.0), (1, light, 0.0)])))
    return sprite(("fband", key), w, h, fn)


# ----------------------------------------------------------------- ground plants
def fern(c, x, y, size, seed, t=0.0, wind=0.08, col="#2f6a2c", col2=None, n=None, spread=1.0, a=1.0, flat=0.0, shake=0.0):
    """Procedural fern clump with base at (x, y)."""
    r = Rng(seed)
    n = n or r.i(6, 10)
    col2 = col2 or shade(col, 0.25)
    for i in range(n):
        u = (i + 0.5) / n
        ang = -math.pi / 2 + (u - 0.5) * 2.6 * spread + r.u(-0.12, 0.12)
        sw = wind * noise(t * 0.9 + i * 0.37, seed) + shake * noise(t * 22 + i, seed + 5) * 0.3
        ang += sw * 0.6
        ang = lerp(ang, (0 if math.cos(ang) > 0 else math.pi) + 0.05, flat)
        ln = size * r.u(0.7, 1.05)
        side = 1 if math.cos(ang) >= 0 else -1
        path, spine = frond_path(x, y, ang, ln, (1.1 + flat) * side * abs(math.cos(ang)) * 0.9 + 0.25 * side, ln * 0.16, seed * 31 + i,
                                 n=12, sway=sw)
        cc = col if i % 2 else col2
        c.drawPath(path, paint(cc, a))
        c.drawPath(poly(spine, closed=False), paint(shade(cc, -0.3), a, stroke=max(1.0, size * 0.012)))


def grass(c, x0, x1, y, t, seed=1, h=26, density=0.35, col="#4c7f35", col2="#6fa047", wind=0.25, a=1.0, flat=None):
    """Grass blades along y. flat(x) -> 0..1 flattening (shockwave, footsteps)."""
    r = Rng(seed)
    n = int((x1 - x0) * density)
    p1, p2 = skia.Path(), skia.Path()
    for i in range(n):
        x = x0 + r.u(0, 1) * (x1 - x0)
        hh = h * r.u(0.5, 1.2)
        lean = r.u(-0.25, 0.25) + wind * (noise(t * 0.8 + x * 0.004, seed) + 0.5)
        if flat is not None:
            lean += flat(x) * 1.3
        w = r.u(1.2, 2.4)
        tip = (x + math.sin(lean) * hh, y - math.cos(lean) * hh)
        mid = (x + math.sin(lean * 0.5) * hh * 0.5, y - math.cos(lean * 0.5) * hh * 0.5)
        pa = p1 if i % 3 else p2
        pa.moveTo(x - w, y + 2)
        pa.quadTo(mid[0] - w * 0.5, mid[1], tip[0], tip[1])
        pa.quadTo(mid[0] + w * 0.5, mid[1], x + w, y + 2)
        pa.close()
    c.drawPath(p1, paint(col, a))
    c.drawPath(p2, paint(col2, a))


def bush(c, x, y, r_, seed, pal=("#1f3f1e", "#2f5d2a", "#4f8a3a"), shake=0.0, t=0.0, a=1.0):
    r = Rng(seed)
    pads = []
    for i in range(9):
        ang = r.u(math.pi, TAU)
        d = r.u(0.0, 0.8)
        pads.append((x + math.cos(ang) * r_ * d, y + math.sin(ang) * r_ * d * 0.6 - r_ * 0.15, r_ * r.u(0.35, 0.55)))
    pads.sort(key=lambda p: -p[1])
    for i, (px, py, pr) in enumerate(pads):
        jx = shake * noise(t * 20 + i, seed) * r_ * 0.08
        jy = shake * noise(t * 23 + i, seed + 1) * r_ * 0.05
        _pad_c(c, px + jx, py + jy, pr, pr * 0.75, seed * 13 + i, pal, a)


def _pad_c(c, x, y, rx, ry, seed, pal, a=1.0):
    dark, mid, lt = pal
    c.drawPath(spline(blob_pts(x, y, rx, seed, 9, 0.25, ry / rx)), paint(dark, a))
    c.drawPath(spline(blob_pts(x - rx * 0.12, y - ry * 0.2, rx * 0.75, seed + 1, 9, 0.25, ry / rx * 0.8)), paint(mid, a))
    c.drawPath(spline(blob_pts(x - rx * 0.25, y - ry * 0.4, rx * 0.4, seed + 2, 8, 0.3, ry / rx * 0.7)), paint(lt, 0.85 * a))


def rock(c, x, y, w, h, seed, col="#6b665e", light="#c9c1ad", a=1.0, light_a=0.5, moss=None):
    """Faceted boulder with base centre at (x, y)."""
    r = Rng(seed)
    n = 9
    pts = []
    for i in range(n):
        ang = math.pi + math.pi * i / (n - 1)
        rr = r.u(0.8, 1.1)
        pts.append((x + math.cos(ang) * w * 0.5 * rr, y + math.sin(ang) * h * rr))
    pts += [(x + w * 0.52, y + 2), (x - w * 0.52, y + 2)]
    path = poly(pts)
    c.drawPath(path, paint(shader=lin((x, y - h), (x, y), [(0, shade(col, 0.1)), (1, shade(col, -0.35))]), a=a))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    c.drawPath(poly([(x - w * 0.6, y - h * 1.2), (x + w * 0.1, y - h * 1.2), (x - w * 0.05, y - h * 0.3), (x - w * 0.6, y)]),
               paint(light, light_a * a, blur=3))
    if moss:
        c.drawPath(poly([(x - w * 0.6, y - h * 1.1), (x + w * 0.6, y - h * 1.1), (x + w * 0.5, y - h * 0.75), (x - w * 0.5, y - h * 0.8)]),
                   paint(moss, 0.55 * a, blur=4))
    c.restore()


# ----------------------------------------------------------------- water
def waterfall(c, x, y0, y1, w, t, col="#d8eef5", deep="#5aa7c4", a=1.0, seed=3):
    c.drawRect(skia.Rect(x - w / 2, y0, x + w / 2, y1), paint(shader=lin((x - w / 2, 0), (x + w / 2, 0),
                                                                        [(0, deep, 0.85 * a), (0.5, col, 0.95 * a), (1, deep, 0.85 * a)])))
    r = Rng(seed)
    L = y1 - y0
    for i in range(int(w / 3)):
        xx = x - w / 2 + r.u(0, w)
        sp = r.u(0.6, 1.0)
        ln = r.u(0.1, 0.3) * L
        off = (t * L * 0.9 * sp + r.u(0, L)) % (L + ln) - ln
        ya, yb = y0 + max(0, off), y0 + min(L, off + ln)
        if yb > ya:
            c.drawLine(xx, ya, xx, yb, paint((1, 1, 1), r.u(0.25, 0.6) * a, stroke=r.u(1, 2.5) * w / 60))
    # foam
    for i in range(14):
        k = hash01(i, seed)
        fx = x + (k - 0.5) * w * 1.5
        fr = w * (0.25 + 0.3 * hash01(i, seed + 1)) * (1 + 0.15 * math.sin(t * 3 + i))
        c.drawCircle(fx, y1 - fr * 0.2, fr, paint((1, 1, 1), 0.35 * a, blur=fr * 0.4))


def water_band(c, x0, x1, y0, y1, t, top="#5fb3cf", bot="#1d5c78", a=1.0, flow=40.0, seed=2, sparkle=(1, 1, 0.9),
               sparkle_a=0.5, density=1.0, fill=True):
    """Horizontal body of water seen at a low angle, with drifting highlights."""
    if fill:
        c.drawRect(skia.Rect(x0, y0, x1, y1), paint(shader=lin((0, y0), (0, y1), [(0, top), (1, bot)]), a=a))
    r = Rng(seed)
    n = int((x1 - x0) * (y1 - y0) / 2400 * density)
    for i in range(n):
        u = r.u()
        yy = y0 + (u ** 1.6) * (y1 - y0)
        depth = (yy - y0) / max(1, (y1 - y0))
        ln = r.u(10, 60) * (0.4 + depth)
        xx = x0 + ((r.u(0, 1) * (x1 - x0) + t * flow * (0.5 + depth)) % (x1 - x0))
        al = (0.5 + 0.5 * math.sin(t * r.u(1, 3) + i)) * sparkle_a * a * (0.4 + 0.6 * (1 - depth))
        c.drawLine(xx, yy, xx + ln, yy, paint(sparkle, al, stroke=1 + depth * 2))


def mist(c, y, t, col=(1, 1, 1), a=0.3, thick=80, w0=-400, w1=W + 400, seed=1, speed=8.0, n=9):
    for i in range(n):
        k = hash01(i, seed)
        x = w0 + ((k * (w1 - w0) + t * speed * (0.6 + k)) % (w1 - w0))
        rx = thick * (3 + 3 * hash01(i, seed + 1))
        ellipse(c, x, y + (hash01(i, seed + 2) - 0.5) * thick, rx, thick * (0.6 + 0.6 * k), paint(col, a * (0.5 + 0.5 * k), blur=thick * 0.6))


def godrays(c, x, y, t, col=(1, 0.95, 0.8), a=0.12, n=7, spread=0.9, length=2200, base_ang=1.9, seed=2, width=0.05):
    for i in range(n):
        k = hash01(i, seed)
        ang = base_ang + (k - 0.5) * spread
        wdt = width * (0.5 + k)
        al = a * (0.5 + 0.5 * math.sin(t * 0.4 + i * 1.7))
        p0 = (x + math.cos(ang - wdt) * length, y + math.sin(ang - wdt) * length)
        p1 = (x + math.cos(ang + wdt) * length, y + math.sin(ang + wdt) * length)
        c.drawPath(poly([(x, y), p0, p1]), paint(shader=rad((x, y), length, [(0, col, al), (1, col, 0)]), blend="screen",
                                                  blur=12))


def ground_fill(c, x0, x1, pts_or_y, col_top, col_bot, depth=600):
    if isinstance(pts_or_y, (int, float)):
        y = pts_or_y
        c.drawRect(skia.Rect(x0, y, x1, y + depth), paint(shader=lin((0, y), (0, y + depth), [(0, col_top), (1, col_bot)])))
        return
    pts = list(pts_or_y) + [(x1, pts_or_y[-1][1] + depth), (x0, pts_or_y[0][1] + depth)]
    ys = [p[1] for p in pts_or_y]
    c.drawPath(spline(pts, tension=0.3) if False else poly(pts),
               paint(shader=lin((0, min(ys)), (0, max(ys) + depth * 0.6), [(0, col_top), (1, col_bot)])))
