"""Illustrated (inked, cel-shaded) dinosaurs built on the rigs in engine/dino.py."""
import math

import skia

from .core import (TAU, clamp, lerp, rgb, mix, shade, paint, lin, rad, poly, spline, taper, rot, hash01, glow)
from . import dino as D
from .toon import ink, stroke, union, limb, ellipse_path, INK, cel_bands

REX_COL = dict(body="#5c8a34", body_sh="#3c6324", body_hi="#86b44a", belly="#efd994", belly_sh="#cdb06a", stripe="#2f5020",
               leg_far="#46702a", claw="#f3ead2", tooth="#fffaf0", eye="#ffd02a", mouth="#7a1622", gum="#b13a46",
               tongue="#d9576a")


def theropod(c, rig, P, cols=REX_COL, lw=None, dark=0.0):
    """Side view. Returns the solved geometry."""
    k = rig.k
    geo = rig.solve(P)
    s, f = P.get("s", 1.0), P.get("f", 1.0)
    hh = k["hip_h"]
    lw = lw or max(2.0, 4.2 * s * hh / 200)
    lwl = lw / s     # line width in local units
    C = {n: (shade(rgb(v), -dark) if dark else rgb(v)) for n, v in cols.items()}
    c.save()
    c.translate(P["x"], P["gy"])
    c.scale(s * f, s)
    # ground shadow
    sx = (geo["legs"]["n"]["ball"][0] + geo["legs"]["f"]["ball"][0]) / 2
    c.drawOval(skia.Rect(sx - hh * 1.5, -hh * 0.06, sx + hh * 1.3, hh * 0.06), paint((0.08, 0.1, 0.04), 0.35, blur=hh * 0.04))
    _leg(c, geo["legs"]["f"], C["leg_far"], C["body_sh"], C["claw"], lwl, hh)
    _arm(c, geo["arm"], C["leg_far"], C["claw"], lwl, hh)
    # body
    pts, top, bot = rig._outline(geo)
    body = spline(pts, closed=True, tension=0.55)
    ys = [q[1] for q in pts]
    y0, y1 = min(ys), max(ys)
    shader = lin((0, y0), (0, y1), [(0, C["body"]), (0.5, C["body"]), (0.72, C["belly"]), (1, C["belly"])])
    ink(c, body, C["body"], lwl * 1.15, shadow=C["body_sh"], highlight=C["body_hi"], off=hh * 0.12, shader=shader, hatch=0.25)
    c.save()
    c.clipPath(body, skia.ClipOp.kIntersect, True)
    sp, rd = geo["spine"], geo["radii"]
    n = len(sp)
    for i in range(2, n - 2):
        if hash01(i, 3) < 0.3:
            continue
        a_, b_ = sp[i - 1], sp[i + 1]
        tx, ty = b_[0] - a_[0], b_[1] - a_[1]
        l = math.hypot(tx, ty) or 1
        nx, ny = ty / l, -tx / l
        r = rd[i][0]
        w = r * 0.2 + 1
        p0 = (sp[i][0] + nx * r * 1.1, sp[i][1] + ny * r * 1.1)
        p1 = (sp[i][0] + nx * r * 0.15 - tx / l * w, sp[i][1] + ny * r * 0.15 - ty / l * w)
        tp = taper(p0, p1, w, w * 0.2)
        c.drawPath(tp, paint(C["stripe"], 0.85))
    for i in range(1, n - 1, 2):
        r = rd[i][0]
        for j in range(2):
            if hash01(i, j, 5) < 0.5:
                continue
            px = sp[i][0] + (hash01(i, j, 6) - 0.5) * r
            py = sp[i][1] - r * hash01(i, j, 7) * 0.6
            c.drawCircle(px, py, r * 0.07 + 0.6, paint(C["stripe"], 0.5))
    # belly scute lines
    for q in bot[n // 3: n - 4: 2]:
        c.drawLine(q[0], q[1] - hh * 0.07, q[0] + hh * 0.02, q[1] - hh * 0.01, paint(C["belly_sh"], 0.9, stroke=lwl * 0.6))
    c.restore()
    ink(c, body, C["body"], lwl * 1.15, shadow=False, shader=None, a=0.0)
    c.drawPath(body, paint(INK, stroke=lwl * 1.15))
    _head(c, geo, C, lwl, rig)
    _leg(c, geo["legs"]["n"], C["body"], C["body_sh"], C["claw"], lwl, hh, hi=C["body_hi"])
    _arm(c, geo["arm"], C["body"], C["claw"], lwl, hh)
    c.restore()
    return geo


def _leg(c, L, col, sh, claw, lwl, hh, hi=None):
    sc = hh / 200.0
    hp, kn, an, ba = L["hip"], L["knee"], L["ank"], L["ball"]
    mid = (lerp(hp[0], kn[0], 0.42), lerp(hp[1], kn[1], 0.42))
    ang = math.atan2(kn[1] - hp[1], kn[0] - hp[0])
    thigh = ellipse_path(mid[0], mid[1] - 4 * sc, 54 * sc, 36 * sc, ang)
    legp = union(thigh, limb(hp, kn, an, 34 * sc, 19 * sc, 11 * sc), taper(an, ba, 11 * sc, 8 * sc))
    toes = []
    cu = L["curl"]
    for i, (ta, tl) in enumerate(((0.10, 30), (-0.05, 36), (0.32, 24))):
        a = ta + cu * 0.9
        tip = (ba[0] + math.cos(a) * tl * sc, ba[1] + math.sin(a) * tl * sc - (3 * sc if i == 2 else 0))
        toes.append((tip, a))
        legp = union(legp, taper(ba, tip, 7.5 * sc, 4 * sc))
    ink(c, legp, col, lwl, shadow=sh, highlight=hi if hi is not None else False, off=12 * sc)
    for tip, a in toes:
        cl = [tip, (tip[0] + math.cos(a) * 11 * sc, tip[1] + math.sin(a) * 11 * sc + 3 * sc),
              (tip[0] + math.cos(a + 1.1) * 5 * sc, tip[1] + math.sin(a + 1.1) * 5 * sc)]
        ink(c, poly(cl), claw, lwl * 0.6, shadow=False)


def _arm(c, arm, col, claw, lwl, hh):
    sc = hh / 200.0
    sh, el, hd = arm
    ink(c, limb(sh, el, hd, 9 * sc, 6 * sc, 4 * sc), col, lwl * 0.8, shadow=False)
    for d in (0.35, -0.25):
        ang = math.atan2(hd[1] - el[1], hd[0] - el[0]) + d
        tip = (hd[0] + math.cos(ang) * 9 * sc, hd[1] + math.sin(ang) * 9 * sc)
        ink(c, taper(hd, tip, 2.6 * sc, 0.9 * sc), claw, lwl * 0.4, shadow=False)


def _head(c, geo, C, lwl, rig):
    k = rig.k
    hx, hy = geo["head"]
    sc = k["head"] / 120.0
    ja = geo["jaw"]
    c.save()
    c.translate(hx, hy)
    c.rotate(math.degrees(geo["head_ang"]))
    c.scale(sc, sc)
    lw = lwl / sc * 1.05
    hinge = D.REX_HINGE
    jaw_r = [rot(p, ja, hinge) for p in D.REX_JAW]
    lrow = [rot(p, ja, hinge) for p in D.REX_LOWER_ROW]
    if ja > 0.02:
        inner = D.REX_UPPER_ROW + list(reversed(lrow))
        ip = spline(inner, closed=True, tension=0.3)
        c.drawPath(ip, paint(C["mouth"]))
        tg = [rot(p, ja * 0.85, hinge) for p in [(18, 18), (60, 21), (92, 18), (96, 14), (60, 12), (22, 13)]]
        ink(c, spline(tg, closed=True), C["tongue"], lw * 0.6, shadow=False)
    jp = spline(jaw_r, closed=True, tension=0.4)
    ink(c, jp, C["belly"], lw, shadow=C["belly_sh"], highlight=False, off=8)
    _teeth(c, lrow, C["tooth"], True, lw)
    sp = spline(D.REX_SKULL, closed=True, tension=0.45)
    ink(c, sp, C["body"], lw, shadow=C["body_sh"], highlight=C["body_hi"], off=12,
        shader=lin((0, -38), (0, 14), [(0, C["body"]), (0.7, C["body"]), (1, mix(C["body"], C["belly"], 0.5))]))
    c.save()
    c.clipPath(sp, skia.ClipOp.kIntersect, True)
    for i in range(7):
        c.drawCircle(24 + i * 13, -30 + i * 1.5, 2.6, paint(C["stripe"], 0.6))
    c.restore()
    _teeth(c, D.REX_UPPER_ROW, C["tooth"], False, lw)
    c.drawPath(ellipse_path(113, -9, 4.5, 2.4, -0.2), paint(INK))
    # eye: big, yellow, angry
    ex, ey = 32, -16
    ink(c, ellipse_path(ex, ey, 9.5, 7.2), C["eye"], lw * 0.8, shadow=shade(C["eye"], -0.25), highlight=False, off=3)
    c.drawPath(ellipse_path(ex + 1.5, ey, 1.8, 6.0), paint(INK))
    c.drawCircle(ex - 3, ey - 3, 1.8, paint((1, 1, 1)))
    stroke(c, [(ex - 15, ey - 9), (ex - 2, ey - 15), (ex + 12, ey - 11)], lw * 1.8)
    for i in range(3):
        stroke(c, [(ex - 18 + i * 4, ey + 6 + i * 3), (ex - 10 + i * 4, ey + 9 + i * 3)], lw * 0.5)
    c.restore()


def _teeth(c, row, col, up, lw):
    segs, tot = [], 0.0
    for a, b in zip(row, row[1:]):
        l = math.hypot(b[0] - a[0], b[1] - a[1])
        segs.append((a, b, l))
        tot += l
    count = 12
    for i in range(count):
        d = (i + 0.5) / count * tot
        for a, b, l in segs:
            if d <= l:
                u = d / l
                x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
                break
            d -= l
        size = 8 + 4 * math.sin(math.pi * (i + 0.5) / count)
        w = 2.8 + size * 0.14
        tip = (x + 1.0, y - size * 0.85) if up else (x + 1.5, y + size)
        ink(c, poly([(x - w, y), (x + w, y), tip]), col, lw * 0.35, shadow=False, wob=False)


def rex_front(c, x, gy, s, phase, jaw=0.6, t=0.0, cols=REX_COL, lw=None, roar=0.0):
    """T-Rex head-on (charging / roaring at the camera). (x, gy) = ground under the body."""
    C = {n: rgb(v) for n, v in cols.items()}
    lw = (lw or max(2.5, 5.0 * s)) / s
    ph = phase % 1.0
    bob = 10 * math.cos(ph * TAU * 2)
    sway = 14 * math.sin(ph * TAU)
    c.save()
    c.translate(x, gy)
    c.scale(s, s)
    c.drawOval(skia.Rect(-170, -14, 170, 14), paint((0.08, 0.1, 0.04), 0.35, blur=8))
    for side in (-1, 1):
        u = (ph + (0 if side < 0 else 0.5)) % 1.0
        lift = max(0.0, math.sin(u * TAU)) * 60
        fx, fy = side * 74 + sway * 0.3, -lift
        hipx, hipy = side * 64 + sway, -215 + bob
        kx, ky = side * 98 + sway * 0.6, -128 - lift * 0.6 + bob * 0.5
        lp = union(ellipse_path(hipx + side * 6, hipy + 30, 52, 70, side * 0.2), limb((hipx, hipy), (kx, ky), (fx, fy - 30), 44, 24, 15))
        for tx in (-24, 0, 24):
            lp = union(lp, taper((fx, fy - 22), (fx + tx, fy + 2), 12, 6))
        ink(c, lp, C["body"] if side > 0 else C["leg_far"], lw, shadow=C["body_sh"], highlight=False, off=14)
        for tx in (-24, 0, 24):
            ink(c, poly([(fx + tx - 6, fy), (fx + tx + 6, fy), (fx + tx * 1.1, fy + 11)]), C["claw"], lw * 0.5, shadow=False)
    by = -270 + bob
    body = ellipse_path(sway, by, 128, 132)
    ink(c, body, C["body"], lw, shadow=C["body_sh"], highlight=C["body_hi"], off=34,
        shader=rad((sway, by + 30), 150, [(0, C["belly"]), (0.55, C["belly"]), (0.62, C["body"]), (1, C["body"])]))
    for i in range(6):
        yy = by + 10 + i * 17
        c.drawLine(sway - 42 + abs(i - 2.5) * 6, yy, sway + 42 - abs(i - 2.5) * 6, yy, paint(C["belly_sh"], stroke=lw * 0.6))
    for side in (-1, 1):
        sx_, sy_ = sway + side * 64, by + 4
        ex_, ey_ = sx_ + side * 24, sy_ + 28 + 6 * math.sin(t * 6 + side)
        ink(c, limb((sx_, sy_), (ex_, ey_), (ex_ - side * 6, ey_ + 20), 11, 7, 4), C["body"], lw * 0.8, shadow=False)
    hx, hy = sway * 1.2, by - 152 + bob * 0.4 - 20 * roar
    ink(c, taper((sway, by - 60), (hx, hy + 30), 84, 62), C["body"], lw, shadow=C["body_sh"], highlight=False, off=20)
    hw = 100
    jo = jaw * 125
    cav = spline([(hx - hw * 0.8, hy + 10), (hx, hy - 4), (hx + hw * 0.8, hy + 10), (hx + hw * 0.55, hy + 10 + jo),
                  (hx, hy + 22 + jo), (hx - hw * 0.55, hy + 10 + jo)])
    c.drawPath(cav, paint(shade(C["mouth"], -0.15)))
    c.drawPath(ellipse_path(hx, hy + 30 + jo * 0.55, hw * 0.36, 16 + jo * 0.16), paint(shade(C["mouth"], -0.4)))
    ink(c, ellipse_path(hx, hy + 20 + jo * 0.72, 44, 9 + jo * 0.1), C["tongue"], lw * 0.6, shadow=False)
    lj = [(hx - hw * 0.86, hy + 6), (hx - hw * 0.62, hy + 14 + jo), (hx, hy + 30 + jo * 1.05), (hx + hw * 0.62, hy + 14 + jo),
          (hx + hw * 0.86, hy + 6), (hx + hw * 0.72, hy + 36 + jo), (hx, hy + 58 + jo), (hx - hw * 0.72, hy + 36 + jo)]
    ink(c, spline(lj), C["belly"], lw, shadow=C["belly_sh"], highlight=False, off=10)
    for i in range(9):
        u = (i + 0.5) / 9
        tx = hx + (u - 0.5) * hw * 1.3
        ty = hy + 13 + jo + 14 * (1 - (2 * u - 1) ** 2)
        ink(c, poly([(tx - 6, ty + 4), (tx + 6, ty + 4), (tx, ty - 14)]), C["tooth"], lw * 0.4, shadow=False, wob=False)
    up = [(hx - hw, hy - 30), (hx - hw * 0.72, hy - 70), (hx, hy - 84), (hx + hw * 0.72, hy - 70), (hx + hw, hy - 30),
          (hx + hw * 0.9, hy + 10), (hx, hy + 2), (hx - hw * 0.9, hy + 10)]
    sk = spline(up)
    ink(c, sk, C["body"], lw, shadow=C["body_sh"], highlight=C["body_hi"], off=16)
    for i in range(10):
        u = (i + 0.5) / 10
        tx = hx + (u - 0.5) * hw * 1.58
        ty = hy + 6 - 6 * (1 - (2 * u - 1) ** 2)
        ink(c, poly([(tx - 6.5, ty - 4), (tx + 6.5, ty - 4), (tx, ty + 18)]), C["tooth"], lw * 0.4, shadow=False, wob=False)
    stroke(c, [(hx - 26, hy - 74), (hx, hy - 24), (hx + 26, hy - 74)], lw * 0.8, C["body_sh"])
    stroke(c, [(hx - 40, hy - 60), (hx - 10, hy - 30)], lw * 0.7, C["stripe"])
    stroke(c, [(hx + 40, hy - 60), (hx + 10, hy - 30)], lw * 0.7, C["stripe"])
    for side in (-1, 1):
        c.drawPath(ellipse_path(hx + side * 17, hy - 18, 8, 4.5, side * 0.3), paint(INK))
        ex, ey = hx + side * hw * 0.72, hy - 46
        glow(c, ex, ey, 34, (1.0, 0.45, 0.1), 0.3)
        ink(c, ellipse_path(ex, ey, 10, 6.5, -side * 0.25), C["eye"], lw * 0.8, shadow=(0.95, 0.45, 0.1), highlight=False, off=3)
        c.drawPath(ellipse_path(ex, ey, 1.8, 6), paint(INK))
        c.drawCircle(ex - side * 3, ey - 2, 1.6, paint((1, 1, 1)))
        ridge = poly([(ex - side * 26, ey - 16), (ex + side * 18, ey - 6), (ex + side * 14, ey - 18), (ex - side * 20, ey - 26)])
        ink(c, ridge, C["body_sh"], lw * 0.9, shadow=False)
    c.restore()
