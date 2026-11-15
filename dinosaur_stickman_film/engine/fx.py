"""Visual effects. Every effect is a pure function of time, so any frame can be
rendered on its own (and in parallel) and still match its neighbours."""
import math

import numpy as np
import skia

from .core import (W, H, TAU, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                   blob, ellipse, glow, sprite, draw_img, inv, ease_out)


# ----------------------------------------------------------------- particles
def burst(c, t, t0, x, y, n, seed, speed=(150, 500), ang=(-math.pi, 0), grav=900.0, life=(0.5, 1.2), size=(2, 6),
          col=(1, 1, 1), a=1.0, drag=0.0, streak=0.0, blur=0.0, spawn=0.0, blend=None, shrink=True, col2=None):
    """Ballistic particles launched at t0 (optionally spread over `spawn` seconds)."""
    for i in range(n):
        h1, h2, h3, h4, h5 = (hash01(i, seed, k) for k in range(5))
        age = t - t0 - h5 * spawn
        lf = lerp(life[0], life[1], h3)
        if age < 0 or age > lf:
            continue
        an = lerp(ang[0], ang[1], h1)
        sp = lerp(speed[0], speed[1], h2)
        vx, vy = math.cos(an) * sp, math.sin(an) * sp
        if drag > 0:
            k = (1 - math.exp(-drag * age)) / drag
        else:
            k = age
        px = x + vx * k
        py = y + vy * k + 0.5 * grav * age * age
        u = age / lf
        sz = lerp(size[0], size[1], h4) * ((1 - u * 0.7) if shrink else 1)
        al = a * (1 - u) ** 1.2
        cc = col if col2 is None else mix(col, col2, u)
        if streak > 0:
            dvx = vx * (math.exp(-drag * age) if drag > 0 else 1)
            dvy = vy * (math.exp(-drag * age) if drag > 0 else 1) + grav * age
            c.drawLine(px, py, px - dvx * streak, py - dvy * streak, paint(cc, al, stroke=sz, blur=blur, blend=blend))
        else:
            c.drawCircle(px, py, sz, paint(cc, al, blur=blur, blend=blend))


def dust(c, t, t0, x, y, scale=1.0, col=(0.6, 0.55, 0.45), a=0.6, n=10, seed=1, spread=1.0, rise=0.4, dur=2.2, dirx=0.0):
    """Soft billowing dust puffs."""
    for i in range(n):
        h1, h2, h3 = hash01(i, seed, 1), hash01(i, seed, 2), hash01(i, seed, 3)
        age = t - t0 - h3 * 0.25
        if age < 0 or age > dur:
            continue
        u = age / dur
        e = ease_out(u)
        ang = math.pi + h1 * math.pi
        dx = math.cos(ang) * 120 * spread * e * scale + dirx * e * 100 * scale
        dy = math.sin(ang) * 30 * e * scale - rise * 80 * e * scale
        r = (14 + 46 * e) * scale * (0.6 + 0.8 * h2)
        c.drawCircle(x + dx, y + dy, r, paint(shade(col, (h2 - 0.5) * 0.2), a * (1 - u) ** 1.5, blur=r * 0.45))


def leaves(c, t, t0, x, y, n, seed, col=("#3c6e2f", "#5a8f3a", "#2c5224"), spread=300, up=250, dur=3.0, size=7, a=1.0,
           wind=0.0):
    """Leaves torn loose: thrown up, then flutter down."""
    for i in range(n):
        h = [hash01(i, seed, k) for k in range(6)]
        age = t - t0 - h[5] * 0.3
        if age < 0 or age > dur:
            continue
        vx = (h[0] - 0.5) * 2 * spread + wind
        vy = -up * (0.5 + h[1])
        k = (1 - math.exp(-2.2 * age)) / 2.2
        px = x + vx * k + math.sin(age * (3 + 3 * h[2]) + i) * 18
        py = y + vy * k + 60 * age * age * (0.6 + h[3])
        an = age * (4 + 6 * h[2]) + i
        sz = size * (0.6 + 0.8 * h[4])
        al = a * (1 - clamp((age - dur * 0.7) / (dur * 0.3)))
        c.save()
        c.translate(px, py)
        c.rotate(math.degrees(an))
        c.scale(1, abs(math.cos(an * 1.3)) * 0.8 + 0.2)
        ellipse(c, 0, 0, sz, sz * 0.45, paint(col[i % len(col)], al))
        c.restore()


def ambient_motes(c, t, n=60, seed=1, col=(1, 1, 0.85), a=0.4, area=(0, 0, W, H), size=(1, 3), speed=12, blend="add"):
    x0, y0, x1, y1 = area
    for i in range(n):
        h = [hash01(i, seed, k) for k in range(5)]
        x = x0 + ((h[0] * (x1 - x0) + t * speed * (h[2] - 0.3) + noise(t * 0.2 + i, seed) * 40) % (x1 - x0))
        y = y0 + ((h[1] * (y1 - y0) - t * speed * 0.4 * h[3] + noise(t * 0.25 + i, seed + 3) * 30) % (y1 - y0))
        tw = 0.5 + 0.5 * math.sin(t * (1 + 2 * h[4]) + i)
        r = lerp(size[0], size[1], h[3])
        c.drawCircle(x, y, r, paint(col, a * tw, blur=r * 0.8, blend=blend))


def ash(c, t, n=400, seed=7, a=0.7, col=(0.75, 0.73, 0.7), speed=40, wind=20, area=(-100, -100, W + 100, H + 100), size=(1.5, 4)):
    x0, y0, x1, y1 = area
    for i in range(n):
        h = [hash01(i, seed, k) for k in range(5)]
        depth = 0.4 + h[4] * 0.9
        y = y0 + ((h[1] * (y1 - y0) + t * speed * depth) % (y1 - y0))
        x = x0 + ((h[0] * (x1 - x0) + t * wind * depth + math.sin(t * (0.6 + h[2]) + i) * 25) % (x1 - x0))
        r = lerp(size[0], size[1], h[3]) * depth
        c.drawCircle(x, y, r, paint(shade(col, (h[2] - 0.5) * 0.4), a * (0.4 + 0.6 * h[3]), blur=r * (0.3 if depth < 1 else 0.9)))


def embers(c, t, x0, x1, y, n=60, seed=3, a=0.9, rise=60, area_h=500):
    for i in range(n):
        h = [hash01(i, seed, k) for k in range(5)]
        life = 3 + h[2] * 3
        age = (t + h[3] * life) % life
        x = x0 + h[0] * (x1 - x0) + math.sin(age * 2 + i) * 20
        yy = y - age / life * area_h * (0.4 + h[1])
        fl = 0.5 + 0.5 * math.sin(t * 9 + i * 3)
        r = 1.2 + 2 * h[4]
        al = a * fl * (1 - age / life)
        c.drawCircle(x, yy, r * 2.5, paint((1, 0.45, 0.1), al * 0.4, blur=r * 2, blend="add"))
        c.drawCircle(x, yy, r, paint((1, 0.8, 0.4), al, blend="add"))


def bolt(c, p0, p1, seed, col=(0.7, 0.9, 1), a=1.0, width=2.5, depth=5, rough=0.35, glow_w=10):
    pts = [p0, p1]
    r = Rng(seed)
    for d in range(depth):
        nxt = []
        for a_, b_ in zip(pts, pts[1:]):
            mx, my = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
            dx, dy = b_[0] - a_[0], b_[1] - a_[1]
            l = math.hypot(dx, dy)
            off = r.n(l * rough * 0.5)
            nxt += [a_, (mx - dy / (l or 1) * off, my + dx / (l or 1) * off)]
        nxt.append(pts[-1])
        pts = nxt
    path = poly(pts, closed=False)
    c.drawPath(path, paint(col, a * 0.5, stroke=glow_w, blur=glow_w * 0.8, blend="add"))
    c.drawPath(path, paint((1, 1, 1), a, stroke=width, blend="add"))


# ----------------------------------------------------------------- water fx
def splash(c, t, t0, x, y, scale=1.0, seed=1, a=1.0, col=(0.85, 0.95, 1.0), big=True):
    age = t - t0
    if age < 0 or age > 3.0:
        return
    # rising water column / crown
    if big and age < 1.4:
        u = age / 1.4
        hgt = math.sin(math.pi * min(1, u * 1.3)) * 190 * scale
        wid = (40 + 90 * u) * scale
        for k in range(7):
            ox = (k - 3) / 3 * wid
            hh = hgt * (1 - abs(k - 3) / 4.5) * (0.8 + 0.4 * hash01(k, seed))
            c.drawPath(spline([(x + ox - 14 * scale, y), (x + ox * 1.25, y - hh), (x + ox + 14 * scale, y)], closed=True),
                       paint(col, a * 0.75 * (1 - u), blur=3 * scale))
    burst(c, t, t0, x, y, 70 if big else 25, seed, speed=(200 * scale, 700 * scale), ang=(-math.pi * 0.92, -math.pi * 0.08),
          grav=1500 * scale, life=(0.6, 1.3), size=(2 * scale, 6 * scale), col=col, a=a)
    # foam & ripples
    for k in range(3):
        rr = (age * (260 - k * 60) + 20) * scale
        al = a * (1 - age / 3.0) * 0.6
        ellipse(c, x, y + 4 * scale, rr, rr * 0.12, paint(col, al, stroke=3 * scale))
    if age < 1.6:
        ellipse(c, x, y, (60 + age * 60) * scale, 14 * scale, paint((1, 1, 1), a * 0.7 * (1 - age / 1.6), blur=8 * scale))


def ripple(c, t, t0, x, y, scale=1.0, a=0.6, col=(1, 1, 1), n=3, dur=2.0, flat=0.15):
    for k in range(n):
        age = t - t0 - k * 0.25
        if age < 0 or age > dur:
            continue
        rr = (10 + age * 120) * scale
        ellipse(c, x, y, rr, rr * flat, paint(col, a * (1 - age / dur), stroke=2 * scale))


# ----------------------------------------------------------------- portal & tunnel
PORTAL_C1 = (0.25, 0.85, 1.0)
PORTAL_C2 = (0.62, 0.35, 1.0)
PORTAL_C3 = (1.0, 0.45, 0.9)


def portal(c, x, y, r, t, power=1.0, open_=1.0, seed=1, sy=1.0):
    """Swirling dimensional portal. open_ grows it from a point; power drives glow and sparks."""
    if open_ <= 0.001:
        return
    R = r * open_
    c.save()
    c.translate(x, y)
    c.scale(1, sy)
    glow(c, 0, 0, R * 3.2, PORTAL_C2, 0.35 * power)
    glow(c, 0, 0, R * 1.9, PORTAL_C1, 0.45 * power)
    # inner void
    c.drawCircle(0, 0, R, paint(shader=rad((0, 0), R, [(0, (0.02, 0.0, 0.08)), (0.55, (0.12, 0.04, 0.3)), (0.85, (0.25, 0.2, 0.7)),
                                                       (1, (0.5, 0.8, 1.0))])))
    # spiral arms
    arms = 7
    for k in range(arms):
        pts = []
        base = k * TAU / arms + t * 1.6
        for i in range(30):
            u = i / 29
            rr = R * (0.12 + 0.95 * u)
            an = base + (1 - u) * 3.4 + 0.2 * math.sin(t * 2 + u * 6 + k)
            pts.append((math.cos(an) * rr, math.sin(an) * rr))
        col = PORTAL_C1 if k % 3 == 0 else PORTAL_C2 if k % 3 == 1 else PORTAL_C3
        c.drawPath(spline(pts, closed=False), paint(col, 0.55 * power, stroke=R * 0.06, blur=R * 0.03, blend="add"))
        c.drawPath(spline(pts, closed=False), paint((1, 1, 1), 0.25 * power, stroke=R * 0.012, blend="add"))
    # inward particles
    for i in range(90):
        h = [hash01(i, seed, k) for k in range(4)]
        life = 1.2 + h[2] * 1.5
        age = (t + h[3] * life) % life
        u = age / life
        rr = R * (1.6 - 1.5 * u)
        an = h[0] * TAU + u * 3.0 + t * 0.6
        col = PORTAL_C1 if h[1] < 0.5 else PORTAL_C3
        c.drawCircle(math.cos(an) * rr, math.sin(an) * rr, 1.5 + 2.5 * h[1], paint(col, power * math.sin(math.pi * u), blend="add"))
    # bright distorted rim
    for k in range(3):
        pts = []
        for i in range(48):
            an = i / 48 * TAU
            jit = noise(an * 3 + t * 4 + k * 10, seed + k) * R * 0.05 * (0.5 + power)
            pts.append((math.cos(an) * (R + jit), math.sin(an) * (R + jit)))
        c.drawPath(spline(pts), paint(PORTAL_C1 if k else (0.9, 0.95, 1.0), (0.8 if k == 0 else 0.5) * power,
                                      stroke=R * (0.035 if k == 0 else 0.08), blur=R * (0.01 if k == 0 else 0.05), blend="add"))
    # sparks
    if power > 0.3:
        for i in range(4):
            slot = int(t * 7 + i * 13.7)
            if hash01(slot, seed, i) < 0.55 * power:
                an = hash01(slot, seed, i + 9) * TAU
                l = R * (0.25 + 0.4 * hash01(slot, i, 3))
                p0 = (math.cos(an) * R, math.sin(an) * R)
                p1 = (math.cos(an + 0.3) * (R + l), math.sin(an + 0.3) * (R + l))
                bolt(c, p0, p1, slot * 7 + i, col=PORTAL_C1, a=0.9 * power, width=1.6, glow_w=8)
    c.restore()


def tunnel(c, t, cx=W / 2, cy=H / 2, speed=1.0, hue=0.0, a=1.0, twist=0.0):
    """Flying through a tunnel of light: rings and streaks rushing past."""
    c.drawRect(skia.Rect(-W, -H, 2 * W, 2 * H), paint(shader=rad((cx, cy), W * 0.9, [(0, (0.95, 0.9, 1.0)), (0.06, (0.6, 0.4, 1.0)),
                                                                                     (0.3, (0.12, 0.05, 0.35)), (1, (0.02, 0.0, 0.06))]), a=a))
    palette = [PORTAL_C1, PORTAL_C2, PORTAL_C3, (1.0, 0.8, 0.4)]
    N = 18
    for i in range(N):
        z = ((i - t * speed * 6) % N) / N * 4 + 0.05
        rr = 260 / z
        if rr > W * 1.6:
            continue
        col = palette[(i + int(hue * 4)) % 4]
        al = a * clamp(1.4 - z / 3) * 0.8
        rot = t * 0.8 + i * 0.4 + twist
        c.save()
        c.translate(cx, cy)
        c.rotate(math.degrees(rot))
        pts = []
        for k in range(40):
            an = k / 40 * TAU
            jit = 1 + 0.08 * math.sin(an * 5 + i + t * 3)
            pts.append((math.cos(an) * rr * jit, math.sin(an) * rr * jit * 0.85))
        c.drawPath(spline(pts), paint(col, al, stroke=max(1.5, 14 / z), blur=6 / z + 1, blend="add"))
        c.restore()
    M = 140
    for i in range(M):
        h = [hash01(i, 77, k) for k in range(4)]
        z = ((h[0] * 4 - t * speed * (2.5 + h[1] * 2)) % 4) + 0.05
        an = h[2] * TAU + t * 0.6 + twist
        r1, r2 = 200 / z, 200 / (z + 0.18 + 0.4 * speed)
        col = palette[i % 4]
        al = a * clamp(1.5 - z / 2.5)
        c.drawLine(cx + math.cos(an) * r2, cy + math.sin(an) * r2, cx + math.cos(an) * r1, cy + math.sin(an) * r1,
                   paint(col, al, stroke=1 + 3 / z, blend="add"))
    glow(c, cx, cy, 260, (1, 1, 1), 0.6 * a)


# ----------------------------------------------------------------- fire, smoke, explosion
def fire_ball(c, x, y, r, t, a=1.0, seed=1):
    glow(c, x, y, r * 5, (1.0, 0.45, 0.1), 0.5 * a)
    glow(c, x, y, r * 2.4, (1.0, 0.75, 0.3), 0.7 * a)
    for i in range(10):
        an = i / 10 * TAU + t * 3
        rr = r * (0.8 + 0.3 * noise(t * 6 + i, seed))
        c.drawCircle(x + math.cos(an) * rr * 0.3, y + math.sin(an) * rr * 0.3, rr, paint((1, 0.6, 0.2), 0.35 * a, blur=r * 0.3, blend="add"))
    c.drawCircle(x, y, r * 0.8, paint((1, 0.97, 0.85), a, blur=r * 0.15))


def billow(c, x, y, r, seed, col, a=1.0, lit=None, lit_a=0.0, lit_dir=(0, 1), n=7):
    """A cauliflower cloud lump (smoke/dust), optionally lit from one side."""
    r_ = Rng(seed)
    for i in range(n):
        an = r_.u(0, TAU)
        d = r_.u(0, 0.55)
        px, py = x + math.cos(an) * r * d, y + math.sin(an) * r * d * 0.8
        pr = r * r_.u(0.45, 0.7)
        c.drawCircle(px, py, pr, paint(col, a, blur=pr * 0.25))
        if lit is not None and lit_a > 0:
            c.drawCircle(px + lit_dir[0] * pr * 0.3, py + lit_dir[1] * pr * 0.3, pr * 0.7, paint(lit, a * lit_a, blur=pr * 0.4))


def mushroom(c, x, gy, t, scale=1.0, a=1.0, seed=5):
    """Impact cloud: a rising column with an expanding cap, lit from below by fire.
    t = seconds since impact."""
    if t < 0:
        return
    grow = 1 - math.exp(-t * 0.6)
    top = gy - (120 + 680 * grow) * scale
    capr = (60 + 300 * grow) * scale
    heat = math.exp(-t * 0.45)
    dark = (0.18, 0.12, 0.1)
    hot = (1.0, 0.55, 0.2)
    # column
    for i in range(14):
        u = i / 13
        yy = lerp(gy, top + capr * 0.5, u)
        rr = (40 + 50 * u + 30 * hash01(i, seed)) * scale * (0.6 + 0.6 * grow)
        col = mix(hot, dark, clamp(u * 0.8 + (1 - heat) * 0.7))
        billow(c, x + noise(t * 0.5 + i, seed) * 20 * scale, yy, rr, seed + i, col, a, lit=hot, lit_a=heat * 0.5, lit_dir=(0, 1))
    # cap
    for i in range(22):
        an = math.pi + (i / 21) * math.pi
        rr = capr * (0.7 + 0.3 * hash01(i, seed + 2))
        px = x + math.cos(an) * capr * 1.2
        py = top + math.sin(an) * capr * 0.55 + capr * 0.25
        col = mix((0.55, 0.3, 0.18), dark, clamp(0.5 + (1 - heat) * 0.5 - (i % 3) * 0.1))
        billow(c, px, py, rr * 0.6, seed * 3 + i, col, a, lit=hot, lit_a=heat * 0.4, lit_dir=(0, 1))
    billow(c, x, top, capr * 0.8, seed + 99, mix((0.5, 0.3, 0.2), dark, 1 - heat), a, lit=hot, lit_a=heat * 0.5, n=10)


def shock_ring(c, x, y, r, t, a=1.0, flat=0.18, col=(1, 0.85, 0.6)):
    ellipse(c, x, y, r, r * flat, paint(col, a * 0.8, stroke=max(4, r * 0.03), blur=r * 0.01 + 2, blend="add"))
    ellipse(c, x, y, r * 0.98, r * flat * 0.98, paint((1, 1, 1), a * 0.5, stroke=max(2, r * 0.008), blend="add"))


def dust_wall(c, x_front, gy, height, t, direction=1, col=(0.35, 0.25, 0.2), lit=(1, 0.5, 0.2), a=1.0, seed=8, depth=1600):
    """A wall of dust advancing along the ground; everything behind x_front is engulfed."""
    if direction > 0:
        c.drawRect(skia.Rect(x_front - depth - 3000, gy - height, x_front - 40, gy + 400), paint(col, a))
    else:
        c.drawRect(skia.Rect(x_front + 40, gy - height, x_front + depth + 3000, gy + 400), paint(col, a))
    for i in range(30):
        u = i / 29
        yy = gy - u * height
        bulge = (60 + 140 * hash01(i, seed)) * (1 + 0.2 * math.sin(t * 2 + i))
        px = x_front - direction * (bulge * 0.4 + 40) + noise(t + i * 0.3, seed) * 30
        billow(c, px, yy, 90 + 80 * hash01(i, seed + 1), seed + i, shade(col, 0.05 * (hash01(i, 4) - 0.5)), a, lit=lit, lit_a=0.35,
               lit_dir=(direction * 0.4, 0.6))


# ----------------------------------------------------------------- asteroid
def asteroid(c, x, y, r, t, a=1.0, trail_ang=-2.5, trail_len=6.0, heat=1.0, seed=3):
    """Burning asteroid with plasma trail pointing at trail_ang."""
    tx, ty = math.cos(trail_ang), math.sin(trail_ang)
    # trail
    for i in range(36):
        u = i / 35
        d = u * r * trail_len
        rr = r * (1.1 + u * 1.6)
        jx = noise(t * 3 + i * 0.7, seed) * r * 0.25 * u
        col = mix((1, 0.9, 0.6), (1, 0.35, 0.05), u)
        c.drawCircle(x + tx * d - ty * jx, y + ty * d + tx * jx, rr, paint(col, a * heat * 0.22 * (1 - u), blur=rr * 0.6, blend="add"))
    for i in range(30):
        u = i / 29
        d = u * r * trail_len * 1.2
        rr = r * (0.9 + u * 2.4)
        c.drawCircle(x + tx * d, y + ty * d, rr, paint((0.25, 0.18, 0.16), a * 0.18 * (1 - u) * heat, blur=rr * 0.5))
    glow(c, x, y, r * 4, (1, 0.5, 0.15), 0.6 * a * heat)
    # rock body
    pts = blob_pts_rot(x, y, r, seed)
    path = spline(pts)
    c.drawPath(path, paint(shader=rad((x - tx * r * 0.5, y - ty * r * 0.5), r * 1.6, [(0, (0.45, 0.38, 0.33)), (1, (0.1, 0.08, 0.08))]), a=a))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    r_ = Rng(seed)
    for i in range(9):
        cx, cy = x + r_.u(-0.7, 0.7) * r, y + r_.u(-0.7, 0.7) * r
        c.drawCircle(cx, cy, r * r_.u(0.08, 0.22), paint((0.05, 0.04, 0.04), 0.4 * a))
    # glowing leading edge
    c.drawCircle(x - tx * r * 0.9, y - ty * r * 0.9, r * 1.1, paint((1, 0.65, 0.25), a * 0.75 * heat, blur=r * 0.4, blend="add"))
    c.restore()


def blob_pts_rot(x, y, r, seed):
    from .core import blob_pts
    return blob_pts(x, y, r, seed, 11, 0.18)


# ----------------------------------------------------------------- lightning flash / overlays
def flash(c, a, col=(1, 1, 1)):
    if a > 0.002:
        c.drawRect(skia.Rect(-10, -10, W + 10, H + 10), paint(col, clamp(a)))


def light_overlay(c, x, y, r, col, a, blend="screen"):
    if a > 0.002:
        c.drawRect(skia.Rect(-10, -10, W + 10, H + 10), paint(shader=rad((x, y), r, [(0, col, a), (1, col, 0)]), blend=blend))


def heat_haze_rays(c, x, y, t, col, a, n=14, length=3000, seed=4):
    for i in range(n):
        an = hash01(i, seed) * TAU + t * 0.05
        w = 0.02 + 0.04 * hash01(i, seed + 1)
        p0 = (x + math.cos(an - w) * length, y + math.sin(an - w) * length)
        p1 = (x + math.cos(an + w) * length, y + math.sin(an + w) * length)
        c.drawPath(poly([(x, y), p0, p1]), paint(shader=rad((x, y), length, [(0, col, a), (1, col, 0)]), blend="add"))
