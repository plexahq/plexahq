"""Prehistoric landscape kit shared by Acts 2-5: palettes and reusable layers."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, sprite, draw_img, tint_cf, grade_cf, taper)
from engine import nature as N
from engine import fx
from engine import dino as D

PALS = {
    "day": dict(sky=[(0, "#4f97d0"), (0.5, "#9cc9e3"), (0.85, "#e6e7cf"), (1, "#f6e3b4")], sun="#fff6dc", haze=(0.80, 0.87, 0.90),
                cl="#ffffff", cs="#9fb2c8", far=("#7690ad", "#a9bccb"), snow=0.18, mid=("#4f6f66", "#86a394"),
                forest=("#24472c", "#3a6b3a", "#6d9b4f"), grass=("#5e8f3a", "#86b552"), ground=("#4f7a31", "#2c4a1f"),
                light=(1.0, 0.95, 0.8), volc=("#3d3836", "#5b544c"), water=("#7cc4dc", "#2a6f8c"), rock=("#6e6a5e", "#45413a")),
    "forest": dict(sky=[(0, "#7fb2cf"), (1, "#d9e6c9")], sun="#fff3d0", haze=(0.55, 0.68, 0.55), cl="#ffffff", cs="#a9b9b0",
                   far=("#5d7a6a", "#7d9883"), snow=0.0, mid=("#2f4d38", "#45664b"), forest=("#15301c", "#24472a", "#4b7a3a"),
                   grass=("#3e6e2c", "#5f9640"), ground=("#365c25", "#1d3315"), light=(1.0, 0.94, 0.75), volc=("#3c3a36", "#55514a"),
                   water=("#5aa6bd", "#1f5a70"), rock=("#5f5a50", "#3a3630")),
    "chase": dict(sky=[(0, "#5c7f8c"), (1, "#a9b89a")], sun="#ffe9b8", haze=(0.42, 0.52, 0.45), cl="#dfe6df", cs="#7d8c86",
                  far=("#3f5650", "#5b6f66"), snow=0.0, mid=("#22362a", "#334a38"), forest=("#0f2416", "#1b3a22", "#3c6430"),
                  grass=("#2f5a24", "#4d8034"), ground=("#2b4a1d", "#14240e"), light=(1.0, 0.9, 0.7), volc=("#2f2d2a", "#45423c"),
                  water=("#4d97ad", "#163f52"), rock=("#56524a", "#302d28")),
    "sunset": dict(sky=[(0, "#2c3f78"), (0.35, "#8a5a8e"), (0.62, "#f08a5d"), (0.82, "#ffc66e"), (1, "#ffe3a3")], sun="#fff0c0",
                   haze=(1.0, 0.75, 0.55), cl="#ffd2a0", cs="#8c5a78", far=("#8a6a8a", "#d9a08a"), snow=0.15,
                   mid=("#5a4a6a", "#a8786e"), forest=("#2a2a32", "#4a4a3a", "#8a7a4a"), grass=("#7a7a3a", "#b0a050"),
                   ground=("#5a5030", "#2e2818"), light=(1.0, 0.8, 0.5), volc=("#3a2e34", "#6a5050"),
                   water=("#ffc890", "#7a5a7a"), rock=("#7a5e52", "#3e2e2a")),
    "doom": dict(sky=[(0, "#2a0d0a"), (0.4, "#7a1f0e"), (0.7, "#e0521c"), (1, "#ffb055")], sun="#ffd090", haze=(0.85, 0.35, 0.15),
                 cl="#ff9a50", cs="#4a1a14", far=("#5a2a26", "#a04a2a"), snow=0.0, mid=("#3a1c1c", "#6a3020"),
                 forest=("#1a0e0c", "#2e1a12", "#5a3018"), grass=("#4a3a1a", "#6a4a20"), ground=("#3a2414", "#1a0e08"),
                 light=(1.0, 0.55, 0.25), volc=("#2a1814", "#4a2a20"), water=("#ff8a40", "#5a2014"), rock=("#5a3a2a", "#2a1810")),
    "ash": dict(sky=[(0, "#141010"), (0.5, "#3a2a25"), (0.78, "#7a4232"), (1, "#a8644a")], sun="#c8a080", haze=(0.42, 0.38, 0.36), cl="#6a605a",
                cs="#2a2624", far=("#3a3432", "#4e4542"), snow=0.0, mid=("#2a2422", "#3a3230"), forest=("#141212", "#1e1a18", "#2e2826"),
                grass=("#2e2a26", "#3e3830"), ground=("#2a2420", "#121010"), light=(0.9, 0.6, 0.4), volc=("#1e1a18", "#2e2826"),
                water=("#4a4442", "#1e1a1a"), rock=("#3a3430", "#1e1a18")),
}


def P(name):
    return PALS[name]


def sky(c, cam, t, pal, sun=(1500, 160), sun_r=46, clouds=True, cloud_seed=0, cloud_y=200, cloud_a=1.0, sun_a=1.0):
    with cam.view(c, 0.02):
        N.sky(c, pal["sky"], -300, 1000)
        if sun is not None and sun_a > 0:
            N.sun(c, sun[0], sun[1], sun_r, pal["sun"], sun_a)
    if clouds:
        with cam.view(c, 0.06):
            specs = []
            r = Rng(cloud_seed + 3)
            for i in range(7):
                specs.append((r.u(-600, 2600), cloud_y + r.u(-140, 120), r.u(0.6, 1.3), r.u(3, 9), r.i(0, 6)))
            N.clouds(c, t, specs, lit=pal["cl"], shadow=pal["cs"], a=0.92 * cloud_a)


def far_mountains(c, cam, t, pal, y=430, p=0.08, seed=5, h=420, key="", x0=-1200, w=4400, peaks=None):
    img = N.mountain_sprite(("far", key, seed, w, h, str(pal["far"])), seed, w, h, pal["far"][0], pal["far"][1], pal["light"],
                            snow=pal["snow"], rough=0.55, peaks=peaks,
                            haze=pal["haze"], haze_a=0.25)
    with cam.view(c, p):
        c.drawImage(img, x0, y)


def mid_mountains(c, cam, t, pal, y=560, p=0.18, seed=9, h=360, key="", x0=-1400, w=4800, forest=True, peaks=None):
    img = N.mountain_sprite(("mid", key, seed, w, h, str(pal["mid"])), seed, w, h, pal["mid"][0], pal["mid"][1], pal["light"],
                            forest=(pal["forest"][0], 0.3) if forest else None, rough=0.5, peaks=peaks,
                            haze=pal["haze"], haze_a=0.12)
    with cam.view(c, p):
        c.drawImage(img, x0, y)


def volcano(c, cam, t, pal, x=1500, y=600, s=1.0, p=0.1, smoke_a=0.7, glow_a=0.35, key=""):
    img = N.volcano_sprite(("v", key, str(pal["volc"])), 700, 420, pal["volc"][0], pal["volc"][1], pal["light"])
    with cam.view(c, p):
        N.smoke(c, x, y - 400 * s, t, scale=1.6 * s, col=(0.32, 0.3, 0.3), a=smoke_a, drift=140, rise=160, n=22, life=10)
        draw_img(c, img, x, y, s, ay=1.0, cf=tint_cf(pal["haze"], 0.12))
        if glow_a > 0:
            glow(c, x, y - 405 * s, 60 * s, (1, 0.45, 0.15), glow_a)


def forest_band(c, cam, pal, y, p, seed=1, w=5200, h=300, x0=-1600, haze_a=0.35, tall=1.0, dark=0.0):
    col = mix(pal["forest"][0], pal["haze"], haze_a)
    col2 = mix(pal["forest"][2], pal["haze"], haze_a)
    if dark:
        col, col2 = shade(col, -dark), shade(col2, -dark)
    img = N.forest_band_sprite(("fb", seed, str(col), w, h, tall), w, h, col, col2, col, seed=seed, tall=tall)
    with cam.view(c, p):
        c.drawImage(img, x0, y - h * 0.55)


def flock(c, cam, t, p=0.3, n=6, seed=1, area=(-200, 80, 2200, 400), ptero=True, scale=1.0, col="#3b3433", a=1.0, speed=60):
    with cam.view(c, p):
        x0, y0, x1, y1 = area
        for i in range(n):
            h = [hash01(i, seed, k) for k in range(5)]
            x = x0 + ((h[0] * (x1 - x0) + t * speed * (0.6 + 0.6 * h[1])) % (x1 - x0 + 400)) - 200
            y = y0 + h[2] * (y1 - y0) + math.sin(t * 0.5 + i) * 20
            if ptero:
                D.ptero(c, x, y, (0.5 + 0.6 * h[3]) * scale, t * (0.7 + 0.4 * h[4]) + h[1], f=1, col=col, a=a,
                        glide=0.6 if (int(t * 0.5 + i) % 3) else 0.0)
            else:
                D.bird(c, x, y, (0.6 + 0.5 * h[3]) * scale, t * 3 + h[1], col=col, a=a)


def hill(c, pts, pal, t=0.0, grass=True, seed=1, gh=24, density=0.35, depth=900, tone=0.0):
    top = pal["ground"][0] if not tone else shade(pal["ground"][0], tone)
    bot = pal["ground"][1]
    path_pts = pts + [(pts[-1][0], pts[-1][1] + depth), (pts[0][0], pts[0][1] + depth)]
    ys = [q[1] for q in pts]
    c.drawPath(spline(path_pts, tension=0.25), paint(shader=lin((0, min(ys)), (0, max(ys) + 400), [(0, top), (1, bot)])))
    if grass:
        for a, b in zip(pts, pts[1:]):
            n = max(2, int(abs(b[0] - a[0]) / 60))
            for k in range(n):
                u0, u1 = k / n, (k + 1) / n
                xa, xb = lerp(a[0], b[0], u0), lerp(a[0], b[0], u1)
                ya = lerp(a[1], b[1], (u0 + u1) / 2)
                N.grass(c, xa, xb, ya + 4, t, seed=seed + k + int(a[0]), h=gh, density=density, col=pal["grass"][0],
                        col2=pal["grass"][1])


def ground_at(pts, x):
    for a, b in zip(pts, pts[1:]):
        if a[0] <= x <= b[0]:
            return lerp(a[1], b[1], (x - a[0]) / (b[0] - a[0]))
    return pts[0][1] if x < pts[0][0] else pts[-1][1]


def cliff(c, x0, x1, top_y, bot_y, pal, seed=1, light_side=1):
    """A rocky cliff face (x0..x1): columns, strata, moss and hanging vines."""
    key = ("cliff", seed, int(x1 - x0), int(bot_y - top_y), str(pal["rock"]), str(pal["forest"]))
    w, h = int(x1 - x0) + 80, int(bot_y - top_y) + 120

    def fn(cv):
        r = Rng(seed)
        ox, oy = 40, 80
        pts = [(ox, h)]
        n = 14
        for i in range(n + 1):
            u = i / n
            pts.append((ox + u * (w - 80) + r.u(-18, 18), oy + r.u(-30, 30) + (1 - math.sin(math.pi * u)) * 50))
        pts.append((w - 40, h))
        path = poly(pts)
        rock0, rock1 = rgb(pal["rock"][0]), rgb(pal["rock"][1])
        cv.drawPath(path, paint(shader=lin((0, oy), (0, h), [(0, shade(rock0, 0.05)), (0.5, rock0), (1, shade(rock1, -0.2))])))
        cv.save()
        cv.clipPath(path, skia.ClipOp.kIntersect, True)
        x = ox
        while x < w:
            cw = r.u(18, 60)
            k = r.u(-0.18, 0.12)
            cv.drawRect(skia.Rect(x, oy - 40, x + cw, h), paint(shade(rock0, k), 0.55))
            cv.drawLine(x, oy - 40, x + r.u(-6, 6), h, paint((0, 0, 0), 0.35, stroke=r.u(1.5, 4)))
            cv.drawLine(x + 3, oy - 40, x + 3, h, paint(pal["light"], 0.10 if light_side > 0 else 0.03, stroke=2))
            x += cw
        for k in range(9):
            y = oy + (h - oy) * (k + 0.5) / 9 + r.u(-12, 12)
            cv.drawPath(poly([(0, y), (w, y + r.u(-25, 25)), (w, y + 6), (0, y + r.u(3, 8))]), paint((0, 0, 0), 0.08))
            for j in range(int(w / 140)):
                mx = r.u(0, w)
                cv.drawPath(blob(mx, y - 4, r.u(14, 40), r.i(0, 999), 8, 0.35, 0.35), paint(pal["forest"][1], 0.75))
        for j in range(int(w / 26)):
            vx = r.u(ox, w - 40)
            ln = r.u(40, (h - oy) * 0.6)
            sway = r.u(-12, 12)
            cv.drawPath(spline([(vx, oy - 10), (vx + sway, oy + ln * 0.5), (vx + sway * 0.4, oy + ln)], closed=False),
                        paint(shade(pal["forest"][1], r.u(-0.2, 0.15)), 0.9, stroke=r.u(2, 5)))
        cv.drawRect(skia.Rect(0, 0, w, h), paint(shader=lin((0, 0), (w, 0),
                    [(0, (0, 0, 0), 0.25 if light_side > 0 else 0.0), (1, (0, 0, 0), 0.0 if light_side > 0 else 0.25)])))
        cv.restore()
        top = pts[1:-1]
        cv.drawPath(poly(top, closed=False), paint(pal["forest"][0], 1.0, stroke=26))
        for q in top[::1]:
            cv.drawPath(blob(q[0], q[1] - 6, r.u(18, 34), r.i(0, 999), 9, 0.3, 0.6), paint(pal["forest"][1]))
            cv.drawPath(blob(q[0] - 6, q[1] - 14, r.u(10, 20), r.i(0, 999), 8, 0.3, 0.6), paint(pal["forest"][2], 0.9))
    img = sprite(key, w, h, fn)
    c.drawImage(img, x0 - 40, top_y - 80)
    return [(x0, top_y), (x1, top_y)]


def waterfall_cliff(c, cam, t, pal, x, top, bottom, width=140, p=0.35, seed=3, cliff_w=900, haze_a=0.25):
    with cam.view(c, p):
        with layer(c, cf=tint_cf(pal["haze"], haze_a)):
            cliff(c, x - cliff_w / 2, x + cliff_w / 2, top, bottom, pal, seed=seed)
            for k in range(6):
                N.tree(c, "arauc" if k % 2 else "tfern", seed + k, x - cliff_w / 2 + 60 + k * cliff_w / 6.5, top + 10,
                       180 + 60 * hash01(k, seed), t, wind=0.01)
        N.waterfall(c, x, top + 10, bottom, width, t, col=mix((0.9, 0.97, 1.0), pal["haze"], 0.2), deep=pal["water"][0], a=0.95)
        N.mist(c, bottom - 10, t, col=(1, 1, 1), a=0.35, thick=width * 0.6, w0=x - width * 3, w1=x + width * 3, seed=seed, speed=6, n=7)


def river(c, pts, width, t, pal, flow=1.0, a=1.0):
    """Winding river ribbon through pts [(x, y, w_scale)]."""
    top, bot = [], []
    for i, (x, y, ws) in enumerate(pts):
        top.append((x, y - width * ws / 2))
        bot.append((x, y + width * ws / 2))
    path = spline(top + list(reversed(bot)), tension=0.4)
    ys = [q[1] for q in pts]
    c.drawPath(path, paint(shader=lin((0, min(ys) - width), (0, max(ys) + width), [(0, pal["water"][0]), (1, pal["water"][1])]), a=a))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    for i in range(60):
        h = [hash01(i, 21, k) for k in range(4)]
        seg_i = int(h[0] * (len(pts) - 1))
        x0_, y0_, w0 = pts[seg_i]
        x1_, y1_, w1 = pts[seg_i + 1]
        u = (h[1] + t * 0.08 * flow * (0.5 + h[2])) % 1.0
        x = lerp(x0_, x1_, u)
        y = lerp(y0_, y1_, u) + (h[3] - 0.5) * width * lerp(w0, w1, u) * 0.8
        ln = 20 + 40 * h[2] * lerp(w0, w1, u)
        c.drawLine(x, y, x + ln, y + (y1_ - y0_) / max(1, abs(x1_ - x0_)) * ln, paint((1, 1, 1), 0.35 * a * math.sin(math.pi * u),
                                                                                     stroke=1.5 * lerp(w0, w1, u)))
    c.restore()
    c.drawPath(poly(top, closed=False), paint(shade(pal["ground"][1], -0.2), 0.35 * a, stroke=6, blur=4))


def herd(c, cam, t, pal, p, base_y, xs, s=0.18, haze_a=0.5, moving=True, f=1, speed=6.0, seed=1):
    sau = D.Sauropod()
    with cam.view(c, p):
        for i, x in enumerate(xs):
            ph = t * 0.25 + hash01(i, seed) if moving else 0
            xx = x + (t * speed * f if moving else 0)
            sau.draw(c, dict(x=xx, gy=base_y + (hash01(i, seed + 1) - 0.5) * 20, s=s * (0.8 + 0.4 * hash01(i, seed + 2)), f=f,
                             phase=ph, t=t + i, moving=moving, neck_raise=0.5 + 0.4 * hash01(i, seed + 3),
                             neck_curl=-0.05 + 0.1 * hash01(i, seed + 4)), haze=pal["haze"], haze_a=haze_a, shadow=False)


def foreground_ferns(c, t, pal, xs, y, size=260, wind=0.08, blur=0.0, dark=0.25, seed=1, a=1.0):
    with layer(c, blur=blur, a=a):
        for i, x in enumerate(xs):
            N.fern(c, x, y, size * (0.8 + 0.4 * hash01(i, seed)), seed * 10 + i, t, wind=wind,
                   col=shade(pal["forest"][1], -dark), col2=shade(pal["forest"][2], -dark - 0.1))


def sun_rays(c, x, y, t, pal, a=0.12, n=8, base_ang=2.0, spread=1.0, length=2600):
    N.godrays(c, x, y, t, col=pal["light"], a=a, n=n, spread=spread, length=length, base_ang=base_ang)


# ----------------------------------------------------------------- endless forest for tracking shots
def _tiled(c, img, x0, y, cam, p, w):
    left = cam.left(p) - w
    right = cam.right(p) + w
    k0 = math.floor((left - x0) / w)
    k1 = math.ceil((right - x0) / w)
    for k in range(k0, k1 + 1):
        c.drawImage(img, x0 + k * w, y)


def forest_world(c, cam, t, pal, gy, seed=1, sun=(400, 60), rays=0.12, dark=0.0, density=1.0, trunks=True, ferns=True,
                 far=True, haze_far=0.45, ground_tone=0.0, flat=None, shake_trees=None):
    """Dense prehistoric forest seen side-on. Objects are placed by index so the
    world can scroll forever; shake_trees(x) -> 0..1 adds violent swaying."""
    with cam.view(c, 0.02):
        N.sky(c, pal["sky"], -400, 1100)
        if sun:
            N.sun(c, sun[0], sun[1], 40, pal["sun"])
    if far:
        col = mix(pal["forest"][0], pal["haze"], haze_far)
        col2 = mix(pal["forest"][2], pal["haze"], haze_far * 0.9)
        img = N.forest_band_sprite(("fw_far2", seed, str(col)), 3000, 900, col, col2, col, seed=seed, tall=1.0)
        with cam.view(c, 0.15):
            _tiled(c, img, -1000, gy - 900 * 0.55 - 60, cam, 0.15, 3000)
    if rays > 0 and sun:
        sx, sy = cam.to_screen(*sun, 0.02)
        N.godrays(c, sx, sy, t, col=pal["light"], a=rays, n=9, spread=1.0, base_ang=1.15, length=2600)
    # mid trees
    for layer_p, spacing, hz, hmin, hmax, kinds in ((0.35, 260, 0.38, 700, 1000, ("arauc", "broad", "tfern")),
                                                     (0.6, 380, 0.2, 800, 1200, ("broad", "arauc", "tfern"))):
        with cam.view(c, layer_p):
            left, right = cam.left(layer_p) - 600, cam.right(layer_p) + 600
            i0, i1 = int(math.floor(left / spacing)), int(math.ceil(right / spacing))
            for i in range(i0, i1 + 1):
                h1 = hash01(i, seed, layer_p * 10)
                if h1 > 0.8 * density + 0.15:
                    continue
                x = i * spacing + hash01(i, seed, 2) * spacing * 0.6
                kind = kinds[int(hash01(i, seed, 3) * 3) % 3]
                ht = lerp(hmin, hmax, hash01(i, seed, 4))
                ex = shake_trees(x) if shake_trees else 0.0
                N.tree(c, kind, i + int(layer_p * 100), x, gy + (1 - layer_p) * -60, ht, t, wind=0.012 + 0.08 * ex,
                       haze=pal["haze"], haze_a=hz, dark=dark * (1 - layer_p * 0.3), sway_extra=ex * 0.08 * math.sin(t * 9 + i))
            if layer_p == 0.6:
                N.ground_fill(c, left, right, gy - 40, mix(pal["ground"][0], pal["haze"], 0.25), pal["ground"][1], 400)
    # ground
    with cam.view(c, 1.0):
        left, right = cam.left(1.0) - 300, cam.right(1.0) + 300
        g0 = shade(pal["ground"][0], ground_tone) if ground_tone else pal["ground"][0]
        N.ground_fill(c, left, right, gy, g0, pal["ground"][1], 1600)
        N.grass(c, left, right, gy + 4, t, seed=seed + int(left / 400), h=30, density=0.45, col=pal["grass"][0],
                col2=pal["grass"][1], flat=flat)
        if trunks:
            sp = 900
            i0, i1 = int(math.floor(left / sp)), int(math.ceil(right / sp))
            for i in range(i0, i1 + 1):
                if hash01(i, seed, 9) < 0.45:
                    continue
                x = i * sp + hash01(i, seed, 10) * 500
                N.rock(c, x, gy + 6, 90 + 80 * hash01(i, seed, 11), 40 + 40 * hash01(i, seed, 12), i, col=pal["rock"][0],
                       light=pal["light"], moss=pal["forest"][1])
        if ferns:
            sp = 230
            i0, i1 = int(math.floor(left / sp)), int(math.ceil(right / sp))
            for i in range(i0, i1 + 1):
                if hash01(i, seed, 13) < 0.3:
                    continue
                x = i * sp + hash01(i, seed, 14) * 140
                fl = flat(x) if flat else 0.0
                ex = shake_trees(x) if shake_trees else 0.0
                N.fern(c, x, gy + 6, 110 + 90 * hash01(i, seed, 15), i * 7 + seed, t, wind=0.07 + 0.3 * ex,
                       col=pal["forest"][1], col2=pal["forest"][2], flat=fl, shake=ex)


def forest_foreground(c, cam, t, pal, gy, seed=2, blur=8.0, p=1.35, dark=0.45, trunks=False):
    with cam.view(c, p):
        with layer(c, blur=blur):
            left, right = cam.left(p) - 400, cam.right(p) + 400
            sp = 700
            i0, i1 = int(math.floor(left / sp)), int(math.ceil(right / sp))
            for i in range(i0, i1 + 1):
                x = i * sp + hash01(i, seed, 1) * 300
                if hash01(i, seed, 2) < 0.55:
                    N.fern(c, x, gy + 120, 300, i + seed * 5, t, wind=0.06, col=shade(pal["forest"][0], -dark),
                           col2=shade(pal["forest"][1], -dark))
                elif trunks and hash01(i, seed, 3) < 0.5:
                    c.drawRect(skia.Rect(x - 45, -2000, x + 45, gy + 400), paint(shade(pal["forest"][0], -dark - 0.2)))
