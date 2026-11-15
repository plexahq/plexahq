"""Dinosaur rigs: theropods (T-Rex, small runner), a front-view T-Rex, sauropods,
pterosaurs and birds.

Theropods are built from a spine (tail -> hips -> chest -> neck) with a thickness
profile, giving one smooth organic outline that bends as the animal moves. Legs are
digitigrade with two-bone IK; the head has a hinged jaw. Everything is drawn in a
local frame (facing right, y down, origin on the ground under the hip) and placed with
translate/scale, so facing left is just a mirror.
"""
import math

import skia

from .core import (TAU, clamp, lerp, smooth, noise, paint, lin, rad, poly, spline, taper, rot, mix, shade,
                   rgb, glow, ellipse, hash01, blob)
from .stickman import ik2

# ----------------------------------------------------------------- head shapes
REX_SKULL = [(-4, 10), (-9, -6), (-3, -22), (12, -32), (30, -37), (48, -34), (72, -28), (95, -22), (111, -16),
             (121, -8), (125, 3), (121, 12), (100, 13.5), (76, 14.5), (52, 14.5), (30, 13.5), (12, 12)]
REX_JAW = [(13, 13), (34, 14.5), (56, 15.5), (80, 15.5), (102, 14.5), (117, 13.5), (119, 20), (105, 27), (80, 31),
           (54, 33), (30, 31), (12, 26), (-2, 18), (2, 12)]
REX_UPPER_ROW = [(14, 12.2), (30, 13.5), (52, 14.5), (76, 14.5), (100, 13.5), (119, 12)]
REX_LOWER_ROW = [(14, 13), (34, 14.5), (56, 15.5), (80, 15.5), (102, 14.5), (117, 13.5)]
REX_HINGE = (6, 10)

SMALL_SKULL = [(-3, 6), (-6, -4), (0, -14), (14, -18), (30, -15), (52, -10), (74, -5), (88, -1), (90, 4), (80, 7),
               (55, 8), (30, 8), (10, 7)]
SMALL_JAW = [(10, 7.5), (30, 8.5), (55, 8.5), (80, 7.5), (84, 10), (70, 14), (45, 16), (20, 15), (2, 11), (2, 7)]
SMALL_UPPER_ROW = [(14, 7.4), (30, 8.2), (55, 8.2), (80, 7.2)]
SMALL_LOWER_ROW = [(12, 8), (30, 8.5), (55, 8.5), (80, 7.5)]
SMALL_HINGE = (4, 6)

REX = dict(
    hip_h=200, body=170, arch=16, tail=330, tail_n=12, neck=74, head=122, head_kind="rex",
    thigh=0.43, shin=0.41, meta=0.27, foot_off=14,
    r=[(48, 58), (54, 70), (60, 92), (56, 86), (46, 64), (38, 46), (33, 40), (29, 34)],
    tail_r=(44, 52), arm=30, eye=6.0,
    top="#25241d", main="#545038", belly="#b4a47e", stripe="#1d1c16", claw="#e8dcc0", tooth="#f1e8d0",
    iris="#ffb22e", mouth="#5a1218", tongue="#9b3a3a",
    walk=dict(stride=150, duty=0.62, lift=34, bob=5, pitch=0.03),
    run=dict(stride=250, duty=0.40, lift=60, bob=12, pitch=0.12),
)

SMALL = dict(
    hip_h=34, body=30, arch=3, tail=66, tail_n=10, neck=24, head=17, head_kind="small",
    thigh=0.48, shin=0.52, meta=0.33, foot_off=3,
    r=[(6, 8), (7, 10), (8, 11), (7, 10), (5.5, 7), (3.4, 4.0), (3.0, 3.5), (2.6, 3.0)],
    tail_r=(5.5, 6.5), arm=7, eye=1.7,
    top="#2a4420", main="#5d8a3c", belly="#dcd8a4", stripe="#22381a", claw="#e0d8c0", tooth="#f5f0e0",
    iris="#ff9a2e", mouth="#6a1a20", tongue="#a04848",
    walk=dict(stride=22, duty=0.6, lift=6, bob=1.0, pitch=0.0),
    run=dict(stride=52, duty=0.36, lift=12, bob=2.0, pitch=0.18),
)


def gait_of(spec, kind):
    g = spec[kind] if isinstance(kind, str) else kind
    return dict(stride=g["stride"], duty=g["duty"])


class Theropod:
    def __init__(self, spec):
        self.k = spec

    # ------------------------------------------------------------- geometry
    def solve(self, P):
        k = self.k
        t = P.get("t", 0.0)
        g = P.get("gait")
        gp = k[g] if isinstance(g, str) else (g or dict(stride=1, duty=0.6, lift=0, bob=0, pitch=0))
        ph = P.get("phase", 0.0) % 1.0
        moving = g is not None
        run = moving and gp["duty"] < 0.5
        hh = k["hip_h"] - P.get("crouch", 0.0)
        bob = 0.0
        if moving:
            bob = gp["bob"] * (math.cos(ph * TAU * 2) if run else -math.cos(ph * TAU * 2))
        breath = math.sin(t * TAU * P.get("breath_rate", 0.35)) * P.get("breath", 1.0)
        pitch = P.get("pitch", 0.0) + (gp["pitch"] if moving else 0.0) + (0.02 * math.sin(ph * TAU * 2) if moving else 0)
        hip = (0.0, -hh - bob)
        L = k["body"]
        d = (math.cos(pitch), math.sin(pitch))
        up = (math.sin(pitch), -math.cos(pitch))
        arch = k["arch"] * (1 + 0.04 * breath)
        body = []
        for u, a in ((0.0, 0.0), (0.36, 0.85), (0.70, 0.55), (1.0, 0.0)):
            body.append((hip[0] + d[0] * L * u + up[0] * arch * a, hip[1] + d[1] * L * u + up[1] * arch * a))
        # neck
        neck_up = P.get("neck_up", 0.35)
        bend = P.get("neck_bend", -0.12)
        ang = pitch - neck_up
        pts = [body[-1]]
        nseg = 3
        for i in range(nseg):
            ang_i = ang + bend * i + noise(t * 0.7, 31 + i) * 0.02
            q = pts[-1]
            pts.append((q[0] + math.cos(ang_i) * k["neck"] / nseg, q[1] + math.sin(ang_i) * k["neck"] / nseg))
        neck = pts[1:]
        head_ang = ang + bend * (nseg - 1) + P.get("head_pitch", 0.15)
        shake = P.get("shake", 0.0)
        if shake:
            head_ang += noise(t * 18, 5) * 0.08 * shake
        # tail
        tl = []
        q = hip
        n = k["tail_n"]
        seg = k["tail"] / n
        lift = P.get("tail_lift", 0.10)
        sway = P.get("tail_sway", 0.05)
        if moving:
            sway += 0.03
        wave = (ph * TAU * 2) if moving else t * 1.6
        curl = P.get("tail_curl", -0.025)
        for i in range(n):
            a = math.pi + pitch * 0.6 + lift + curl * i + sway * math.sin(wave - i * 0.45) * (i / n) * 2.0
            q = (q[0] + math.cos(a) * seg, q[1] + math.sin(a) * seg)
            tl.append(q)
        spine = list(reversed(tl)) + body + neck
        # radii
        tr = k["tail_r"]
        radii = []
        for i in range(n):
            u = (i + 1) / n  # 0 at tip
            u = 1 - (i) / n
            uu = (n - i) / n
            radii.append((tr[0] * (1 - uu) ** 0.85 + 0.6, tr[1] * (1 - uu) ** 0.85 + 0.6))
        radii = radii[::-1]
        radii = [(tr[0] * ((j + 1) / n) ** 0.9 + 0.5, tr[1] * ((j + 1) / n) ** 0.9 + 0.5) for j in range(n)]
        bk = 1 + 0.035 * breath
        rr = k["r"]
        radii += [(rr[0][0], rr[0][1] * bk), (rr[1][0], rr[1][1] * bk), (rr[2][0], rr[2][1] * bk), (rr[3][0], rr[3][1])]
        radii += [rr[4], rr[5], rr[6], rr[7]][: len(neck)] if len(neck) == 4 else [rr[5], rr[6], rr[7]]
        # legs
        legs = {}
        thigh, shin, meta = hh * k["thigh"], hh * k["shin"], hh * k["meta"]
        thigh = k["hip_h"] * k["thigh"]
        shin = k["hip_h"] * k["shin"]
        meta = k["hip_h"] * k["meta"]
        hj = (hip[0] + 6 * k["hip_h"] / 200, hip[1] + 16 * k["hip_h"] / 200)
        for side, off in (("n", 0.0), ("f", 0.5)):
            over = P.get("foot_" + side)
            if over is not None:
                bx, by, curl_t = over
            elif moving:
                u = (ph + off) % 1.0
                if u < gp["duty"]:
                    kk = u / gp["duty"]
                    rel = gp["stride"] * (0.5 - kk)
                    lft = 0.0
                    curl_t = 0.0
                else:
                    kk = (u - gp["duty"]) / (1 - gp["duty"])
                    rel = gp["stride"] * (-0.5 + smooth(kk))
                    lft = gp["lift"] * math.sin(math.pi * kk)
                    curl_t = math.sin(math.pi * kk)
                bx, by = k["foot_off"] + rel, -lft
            else:
                spread = P.get("stance", 0.18) * k["hip_h"]
                bx, by, curl_t = k["foot_off"] + (spread if side == "n" else -spread * 0.6), 0.0, 0.0
            ma = 0.42 + 0.5 * curl_t
            ank = (bx - math.sin(ma) * meta, by - math.cos(ma) * meta)
            dd = (ank[0] - hj[0], ank[1] - hj[1])
            th, kn = ik2(dd, thigh, shin, 1)
            kp = (hj[0] + math.sin(th) * thigh, hj[1] + math.cos(th) * thigh)
            legs[side] = dict(hip=hj, knee=kp, ank=ank, ball=(bx, by), curl=curl_t)
        # arms
        ch = body[2]
        sh = (ch[0] + 8 * k["hip_h"] / 200, ch[1] + rr[2][1] * 0.45)
        arm_sw = math.sin(t * 2.0) * 0.1 + P.get("arm", 0.0)
        a1 = 1.1 + arm_sw
        el = (sh[0] + math.cos(a1) * k["arm"], sh[1] + math.sin(a1) * k["arm"])
        a2 = a1 - 1.2
        hd = (el[0] + math.cos(a2) * k["arm"] * 0.8, el[1] + math.sin(a2) * k["arm"] * 0.8)
        return dict(spine=spine, radii=radii, legs=legs, head=neck[-1], head_ang=head_ang, arm=(sh, el, hd),
                    jaw=P.get("jaw", 0.0), blink=P.get("blink", 0.0), pupil=P.get("pupil", 1.0), t=t, P=P)

    # ------------------------------------------------------------- helpers for scenes
    def head_world(self, P, geo=None):
        geo = geo or self.solve(P)
        hx, hy = geo["head"]
        a = geo["head_ang"]
        sc = self.k["head"] / 120.0
        # roughly the middle of the skull
        cx = hx + math.cos(a) * 60 * sc
        cy = hy + math.sin(a) * 60 * sc
        return self.to_world(P, (cx, cy))

    def eye_world(self, P, geo=None):
        geo = geo or self.solve(P)
        hx, hy = geo["head"]
        a = geo["head_ang"]
        sc = self.k["head"] / 120.0
        ex, ey = rot((32 * sc, -17 * sc), a)
        return self.to_world(P, (hx + ex, hy + ey))

    def mouth_world(self, P, geo=None):
        geo = geo or self.solve(P)
        hx, hy = geo["head"]
        a = geo["head_ang"]
        sc = self.k["head"] / 120.0
        ex, ey = rot((118 * sc, 16 * sc), a)
        return self.to_world(P, (hx + ex, hy + ey))

    def foot_world(self, P, side, geo=None):
        geo = geo or self.solve(P)
        return self.to_world(P, geo["legs"][side]["ball"])

    def to_world(self, P, pt):
        s, f = P.get("s", 1.0), P.get("f", 1.0)
        return (P["x"] + pt[0] * s * f, P["gy"] + pt[1] * s)

    # ------------------------------------------------------------- drawing
    def draw(self, c, P, light=(1.0, 0.95, 0.8), light_a=0.35, haze=None, haze_a=0.0, geo=None, shadow=True,
             shadow_a=0.3, dark=0.0):
        k = self.k
        geo = geo or self.solve(P)
        s, f = P.get("s", 1.0), P.get("f", 1.0)
        c.save()
        c.translate(P["x"], P["gy"])
        c.scale(s * f, s)
        cols = {n: rgb(k[n]) for n in ("top", "main", "belly", "stripe", "claw", "tooth", "iris", "mouth", "tongue")}
        if dark:
            for n in ("top", "main", "belly", "stripe"):
                cols[n] = shade(cols[n], -dark)
        if haze is not None and haze_a > 0:
            for n in cols:
                cols[n] = mix(cols[n], haze, haze_a)
        if shadow:
            sx = (geo["legs"]["n"]["ball"][0] + geo["legs"]["f"]["ball"][0]) / 2
            ellipse(c, sx - k["hip_h"] * 0.25, 0, k["hip_h"] * 1.6, k["hip_h"] * 0.08,
                    paint((0, 0, 0), shadow_a, blur=k["hip_h"] * 0.05))
        far = shade(cols["main"], -0.35)
        self._leg(c, geo["legs"]["f"], far, shade(cols["claw"], -0.4))
        self._arm(c, geo["arm"], far, shade(cols["claw"], -0.4), 0.9)
        self._body(c, geo, cols, light, light_a)
        self._head(c, geo, cols, light, light_a)
        self._leg(c, geo["legs"]["n"], cols["main"], cols["claw"], near=True, cols=cols, light=light, light_a=light_a)
        self._arm(c, geo["arm"], shade(cols["main"], -0.08), cols["claw"], 1.0)
        c.restore()
        return geo

    def _outline(self, geo):
        sp, rd = geo["spine"], geo["radii"]
        n = len(sp)
        top, bot = [], []
        for i in range(n):
            a = sp[max(0, i - 1)]
            b = sp[min(n - 1, i + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            l = math.hypot(tx, ty) or 1
            nx, ny = ty / l, -tx / l
            top.append((sp[i][0] + nx * rd[i][0], sp[i][1] + ny * rd[i][0]))
            bot.append((sp[i][0] - nx * rd[i][1], sp[i][1] - ny * rd[i][1]))
        tip = sp[0]
        a = sp[1]
        tipx = (tip[0] + (tip[0] - a[0]) * 0.5, tip[1] + (tip[1] - a[1]) * 0.5)
        return [tipx] + top + list(reversed(bot)), top, bot

    def _body(self, c, geo, cols, light, light_a):
        k = self.k
        pts, top, bot = self._outline(geo)
        path = spline(pts, closed=True, tension=0.55)
        ys = [p[1] for p in pts]
        y0, y1 = min(ys), max(ys)
        hh = k["hip_h"]
        sh = lin((0, y0), (0, y1), [(0, cols["top"]), (0.35, cols["main"]), (0.72, mix(cols["main"], cols["belly"], 0.6)),
                                     (1, cols["belly"])])
        c.drawPath(path, paint(shader=sh))
        c.save()
        c.clipPath(path, skia.ClipOp.kIntersect, True)
        # dorsal stripes
        sp, rd = geo["spine"], geo["radii"]
        n = len(sp)
        for i in range(2, n - 2, 1):
            if hash01(i, 3) < 0.25:
                continue
            a, b = sp[i - 1], sp[i + 1]
            tx, ty = b[0] - a[0], b[1] - a[1]
            l = math.hypot(tx, ty) or 1
            nx, ny = ty / l, -tx / l
            r = rd[i][0]
            w = r * 0.22 + 1
            p0 = (sp[i][0] + nx * r * 1.1, sp[i][1] + ny * r * 1.1)
            p1 = (sp[i][0] + nx * r * 0.1 - tx / l * w * 1.5, sp[i][1] + ny * r * 0.1 - ty / l * w * 1.5)
            c.drawPath(taper(p0, p1, w, w * 0.25), paint(cols["stripe"], 0.55))
        # skin spots
        for i in range(1, n - 1):
            for j in range(3):
                h = hash01(i, j, 7)
                if h < 0.4:
                    continue
                r = rd[i][0]
                px = sp[i][0] + (hash01(i, j, 9) - 0.5) * r
                py = sp[i][1] - r * (hash01(i, j, 11) * 0.9 - 0.1)
                ellipse(c, px, py, r * 0.09 + 0.4, r * 0.06 + 0.3, paint(cols["stripe"], 0.25))
        # belly shadow & top light
        c.drawPath(poly([(p[0], p[1] + hh * 0.05) for p in bot], closed=False),
                   paint((0, 0, 0), 0.35, stroke=hh * 0.12, blur=hh * 0.05))
        c.drawPath(poly([(p[0], p[1] + hh * 0.02) for p in top[2:]], closed=False),
                   paint(light, light_a, stroke=hh * 0.04, blur=hh * 0.03))
        c.restore()
        c.drawPath(path, paint(shade(cols["top"], -0.5), 0.5, stroke=max(0.8, hh * 0.006)))

    def _leg(self, c, L, col, claw, near=False, cols=None, light=None, light_a=0.0):
        k = self.k
        hh = k["hip_h"]
        sc = hh / 200.0
        hp, kn, an, ba = L["hip"], L["knee"], L["ank"], L["ball"]
        # thigh muscle
        p = paint(col)
        thigh = taper(hp, kn, 40 * sc, 19 * sc)
        c.drawPath(thigh, p)
        mid = lerp(hp[0], kn[0], 0.42), lerp(hp[1], kn[1], 0.42)
        dx, dy = kn[0] - hp[0], kn[1] - hp[1]
        ang = math.atan2(dy, dx)
        c.save()
        c.translate(*mid)
        c.rotate(math.degrees(ang))
        ellipse(c, 0, -4 * sc, 52 * sc, 34 * sc, p)
        c.restore()
        c.drawPath(taper(kn, an, 19 * sc, 11 * sc), p)
        c.drawPath(taper(an, ba, 11 * sc, 8 * sc), p)
        # toes
        cu = L["curl"]
        for i, (ta, tlen) in enumerate(((0.10, 30), (-0.05, 36), (0.32, 24))):
            a = ta + cu * 0.9
            tip = (ba[0] + math.cos(a) * tlen * sc, ba[1] + math.sin(a) * tlen * sc - (3 * sc if i == 2 else 0))
            c.drawPath(taper(ba, tip, 7 * sc, 3.5 * sc), p)
            ca = a + 0.9
            cl = [tip, (tip[0] + math.cos(a) * 9 * sc, tip[1] + math.sin(a) * 9 * sc + 3 * sc),
                  (tip[0] + math.cos(ca) * 4 * sc, tip[1] + math.sin(ca) * 4 * sc)]
            c.drawPath(poly(cl), paint(claw))
        if near and cols is not None:
            c.save()
            c.clipPath(thigh)
            c.drawPath(poly([hp, kn], closed=False), paint(light, light_a * 0.6, stroke=10 * sc, blur=6 * sc))
            c.restore()
            c.drawPath(thigh, paint(shade(col, -0.5), 0.4, stroke=1.0 * sc))

    def _arm(self, c, arm, col, claw, a):
        k = self.k
        sc = k["hip_h"] / 200.0
        sh, el, hd = arm
        p = paint(col, a)
        c.drawPath(taper(sh, el, 9 * sc, 6 * sc), p)
        c.drawPath(taper(el, hd, 6 * sc, 3.5 * sc), p)
        for d in (0.3, -0.2):
            dx, dy = hd[0] - el[0], hd[1] - el[1]
            ang = math.atan2(dy, dx) + d
            tip = (hd[0] + math.cos(ang) * 8 * sc, hd[1] + math.sin(ang) * 8 * sc)
            c.drawPath(taper(hd, tip, 2.5 * sc, 0.8 * sc), paint(claw, a))

    def _head(self, c, geo, cols, light, light_a):
        k = self.k
        hx, hy = geo["head"]
        sc = k["head"] / 120.0 if k["head_kind"] == "rex" else k["head"] / 90.0
        rex = k["head_kind"] == "rex"
        skull = REX_SKULL if rex else SMALL_SKULL
        jaw = REX_JAW if rex else SMALL_JAW
        urow = REX_UPPER_ROW if rex else SMALL_UPPER_ROW
        lrow = REX_LOWER_ROW if rex else SMALL_LOWER_ROW
        hinge = REX_HINGE if rex else SMALL_HINGE
        ja = geo["jaw"]
        c.save()
        c.translate(hx, hy)
        c.rotate(math.degrees(geo["head_ang"]))
        c.scale(sc, sc)
        jaw_r = [rot(p, ja, hinge) for p in jaw]
        lrow_r = [rot(p, ja, hinge) for p in lrow]
        # mouth interior
        if ja > 0.02:
            inner = urow + list(reversed(lrow_r))
            c.drawPath(spline(inner, closed=True, tension=0.3),
                       paint(shader=lin((0, 0), (0, 40), [(0, shade(cols["mouth"], -0.4)), (1, cols["mouth"])])))
            tg = [rot(p, ja * 0.8, hinge) for p in [(20, 18), (60, 20), (90, 18), (95, 14), (60, 12), (25, 13)]]
            c.drawPath(spline(tg, closed=True), paint(cols["tongue"], 0.95))
        # lower jaw
        jpath = spline(jaw_r, closed=True, tension=0.4)
        c.drawPath(jpath, paint(shader=lin((0, 10), (0, 34), [(0, cols["main"]), (1, cols["belly"])])))
        c.drawPath(jpath, paint(shade(cols["top"], -0.5), 0.5, stroke=1.0))
        if rex:
            self._teeth(c, lrow_r, cols["tooth"], up=True, ja=ja)
        # upper skull
        spath = spline(skull, closed=True, tension=0.45)
        c.drawPath(spath, paint(shader=lin((0, -38), (0, 14), [(0, cols["top"]), (0.6, cols["main"]),
                                                                  (1, mix(cols["main"], cols["belly"], 0.5))])))
        c.save()
        c.clipPath(spath, skia.ClipOp.kIntersect, True)
        if rex:
            for i in range(9):
                x = 20 + i * 11
                c.drawCircle(x, -30 + i * 1.6 + hash01(i, 2) * 3, 2.2 + hash01(i, 3) * 1.5, paint(cols["stripe"], 0.35))
            for i in range(4):
                c.drawPath(poly([(6 + i * 4, -18 + i * 7), (16 + i * 5, -14 + i * 7)], closed=False),
                           paint(cols["stripe"], 0.35, stroke=1.2))
        c.drawPath(poly([(p[0], p[1] + 2) for p in skull[2:11]], closed=False),
                   paint(light, light_a, stroke=4, blur=3))
        c.restore()
        c.drawPath(spath, paint(shade(cols["top"], -0.5), 0.5, stroke=1.0))
        if rex:
            self._teeth(c, urow, cols["tooth"], up=False, ja=ja)
        # nostril
        ellipse(c, 113 if rex else 82, -9 if rex else -3, 4 if rex else 2.5, 2.2 if rex else 1.2, paint((0.05, 0.04, 0.03), 0.8))
        # eye
        ex, ey = (32, -17) if rex else (24, -8)
        er = k["eye"] / sc if rex else k["eye"] / sc
        er = 6.0 if rex else 4.0
        ellipse(c, ex, ey, er * 1.5, er * 1.15, paint((0.06, 0.04, 0.03), 0.9))
        bl = clamp(geo["blink"])
        if bl < 0.95:
            c.save()
            c.clipRect(skia.Rect(ex - er * 2, ey - er + 2 * er * bl, ex + er * 2, ey + er * 2))
            c.drawCircle(ex, ey, er, paint(shader=rad((ex - er * 0.3, ey - er * 0.3), er * 1.3,
                                                      [(0, shade(cols["iris"], 0.3)), (1, shade(cols["iris"], -0.35))])))
            pw = er * (0.22 if rex else 0.35) * geo["pupil"]
            ellipse(c, ex + er * 0.12, ey, pw, er * 0.85, paint((0.02, 0.01, 0.0)))
            c.drawCircle(ex - er * 0.35, ey - er * 0.4, er * 0.22, paint((1, 1, 1), 0.9))
            c.restore()
        # brow
        if rex:
            c.drawPath(spline([(ex - 12, ey - 6), (ex - 2, ey - 11), (ex + 10, ey - 10), (ex + 16, ey - 6)], closed=False),
                       paint(shade(cols["top"], -0.4), 1.0, stroke=4.5))
        else:
            c.drawPath(poly([(ex - 5, ey - 4), (ex + 5, ey - 5)], closed=False), paint(shade(cols["top"], -0.4), 1, stroke=1.6))
        c.restore()

    def _teeth(self, c, row, col, up, ja):
        p = paint(col)
        n = len(row)
        tot = 0
        segs = []
        for a, b in zip(row, row[1:]):
            segs.append((a, b, math.hypot(b[0] - a[0], b[1] - a[1])))
            tot += segs[-1][2]
        count = 13
        for i in range(count):
            d = (i + 0.5) / count * tot
            for a, b, l in segs:
                if d <= l:
                    u = d / l
                    x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
                    break
                d -= l
            size = 7.5 + 3.5 * math.sin(math.pi * (i + 0.5) / count) + hash01(i, 5 if up else 6) * 2
            w = 2.4 + size * 0.15
            if up:
                tip = (x + 1.0, y - size * 0.8)
                ang = -ja
                tip = rot(tip, ang * 0.0, (x, y))
            else:
                tip = (x + 1.5, y + size)
            c.drawPath(poly([(x - w, y), (x + w, y), tip]), p)
            c.drawPath(poly([(x - w * 0.2, y), (x + w, y), tip]), paint((0, 0, 0), 0.15))


# ----------------------------------------------------------------- front-view T-Rex (charging at camera)
def rex_front(c, x, gy, s, phase, jaw=0.6, t=0.0, light="#ffd9a0", light_a=0.4, haze=None, haze_a=0.0, dark=0.0):
    """T-Rex seen head-on, legs stomping alternately. (x, gy) = ground point under the body."""
    k = REX
    cols = {n: rgb(k[n]) for n in ("top", "main", "belly", "stripe", "claw", "tooth", "iris", "mouth", "tongue")}
    if dark:
        for n in ("top", "main", "belly"):
            cols[n] = shade(cols[n], -dark)
    if haze is not None:
        for n in cols:
            cols[n] = mix(cols[n], haze, haze_a)
    ph = phase % 1.0
    bob = 10 * math.cos(ph * TAU * 2)
    sway = 14 * math.sin(ph * TAU)
    c.save()
    c.translate(x, gy)
    c.scale(s, s)
    # legs
    for side in (-1, 1):
        u = (ph + (0 if side < 0 else 0.5)) % 1.0
        lift = max(0.0, math.sin(u * TAU)) * 70
        fx = side * 70 + sway * 0.3
        fy = -lift
        hipx, hipy = side * 62 + sway, -205 + bob
        kx, ky = side * 92 + sway * 0.6, -120 - lift * 0.6 + bob * 0.5
        lp = paint(shade(cols["main"], -0.15))
        c.drawPath(taper((hipx, hipy), (kx, ky), 46, 24), lp)
        c.drawPath(taper((kx, ky), (fx, fy - 30), 24, 15), lp)
        for tx in (-22, 0, 22):
            c.drawPath(taper((fx, fy - 20), (fx + tx, fy + 2), 12, 6), lp)
            c.drawPath(poly([(fx + tx - 5, fy), (fx + tx + 5, fy), (fx + tx * 1.1, fy + 9)]), paint(cols["claw"]))
    # body
    by = -260 + bob
    body = blob(sway, by, 120, 7, n=12, jitter=0.05, sy=1.05)
    c.drawPath(body, paint(shader=rad((sway, by - 40), 170, [(0, cols["belly"]), (0.55, cols["main"]), (1, cols["top"])])))
    c.drawPath(body, paint(light, light_a * 0.6, stroke=10, blur=8))
    # arms
    for side in (-1, 1):
        sx, sy = sway + side * 60, by + 10
        ex, ey = sx + side * 22, sy + 26 + 6 * math.sin(t * 6 + side)
        c.drawPath(taper((sx, sy), (ex, ey), 10, 6), paint(shade(cols["main"], -0.1)))
        c.drawPath(taper((ex, ey), (ex - side * 6, ey + 18), 6, 3), paint(shade(cols["main"], -0.1)))
    # neck + head
    hx, hy = sway * 1.2, by - 150 + bob * 0.4
    c.drawPath(taper((sway, by - 60), (hx, hy + 30), 80, 60), paint(cols["main"]))
    hw = 96
    jo = jaw * 120
    # mouth cavity
    c.drawPath(spline([(hx - hw * 0.8, hy + 10), (hx, hy - 4), (hx + hw * 0.8, hy + 10), (hx + hw * 0.55, hy + 10 + jo),
                       (hx, hy + 20 + jo), (hx - hw * 0.55, hy + 10 + jo)]), paint(shade(cols["mouth"], -0.3)))
    c.drawPath(blob(hx, hy + 18 + jo * 0.7, 40, 3, n=8, jitter=0.1, sy=0.45), paint(cols["tongue"]))
    # lower jaw
    lj = [(hx - hw * 0.85, hy + 6), (hx - hw * 0.62, hy + 14 + jo), (hx, hy + 30 + jo * 1.05), (hx + hw * 0.62, hy + 14 + jo),
          (hx + hw * 0.85, hy + 6), (hx + hw * 0.7, hy + 34 + jo), (hx, hy + 54 + jo), (hx - hw * 0.7, hy + 34 + jo)]
    c.drawPath(spline(lj), paint(shade(cols["main"], -0.05)))
    for i in range(9):
        u = (i + 0.5) / 9
        tx = hx + (u - 0.5) * hw * 1.3
        ty = hy + 12 + jo + 14 * (1 - (2 * u - 1) ** 2) * 1.0
        c.drawPath(poly([(tx - 5, ty + 4), (tx + 5, ty + 4), (tx, ty - 12)]), paint(cols["tooth"]))
    # upper head (wide skull)
    up = [(hx - hw, hy - 30), (hx - hw * 0.7, hy - 66), (hx, hy - 80), (hx + hw * 0.7, hy - 66), (hx + hw, hy - 30),
          (hx + hw * 0.88, hy + 10), (hx, hy + 2), (hx - hw * 0.88, hy + 10)]
    hp = spline(up)
    c.drawPath(hp, paint(shader=lin((0, hy - 80), (0, hy + 10), [(0, cols["top"]), (1, cols["main"])])))
    c.drawPath(hp, paint(light, light_a, stroke=8, blur=6))
    for i in range(10):
        u = (i + 0.5) / 10
        tx = hx + (u - 0.5) * hw * 1.55
        ty = hy + 6 - 6 * (1 - (2 * u - 1) ** 2)
        c.drawPath(poly([(tx - 5.5, ty - 4), (tx + 5.5, ty - 4), (tx, ty + 15)]), paint(cols["tooth"]))
    # snout ridge + nostrils
    c.drawPath(spline([(hx - 26, hy - 70), (hx, hy - 20), (hx + 26, hy - 70)], closed=False), paint(cols["top"], 0.6, stroke=6))
    for side in (-1, 1):
        ellipse(c, hx + side * 18, hy - 18, 7, 4, paint((0.05, 0.03, 0.02), 0.9))
    # eyes (glowing in the dark)
    for side in (-1, 1):
        ex, ey = hx + side * hw * 0.78, hy - 48
        ellipse(c, ex, ey, 11, 8, paint((0.05, 0.03, 0.02)))
        glow(c, ex, ey, 34, cols["iris"], 0.35)
        ellipse(c, ex, ey, 7, 6, paint(cols["iris"]))
        ellipse(c, ex, ey, 1.8, 5.5, paint((0, 0, 0)))
        c.drawPath(poly([(ex - side * 18, ey - 16), (ex + side * 14, ey - 10)], closed=False), paint(cols["top"], 1, stroke=6))
    c.restore()


# ----------------------------------------------------------------- sauropod
SAURO = dict(hip_h=190, body=360, neck=420, neck_n=9, tail=440, tail_n=11, head=44,
             top="#3e4838", main="#6c7556", belly="#c2b98f", stripe="#323b2c")


class Sauropod:
    def __init__(self, spec=SAURO):
        self.k = spec

    def solve(self, P):
        k = self.k
        t = P.get("t", 0.0)
        ph = P.get("phase", 0.0)
        moving = P.get("moving", True)
        hh = k["hip_h"]
        bob = 3 * math.cos(ph * TAU * 2) if moving else 0
        hip = (0.0, -hh - bob)
        sh = (k["body"], -hh * 1.12 - bob * 0.6)
        mid = (k["body"] * 0.5, -hh * 1.28 - bob)
        body = [hip, (k["body"] * 0.25, -hh * 1.22 - bob), mid, (k["body"] * 0.78, -hh * 1.24 - bob), sh]
        # neck: raise and curl
        raise_ = P.get("neck_raise", 0.55)  # radians above horizontal at the base
        curl = P.get("neck_curl", -0.05)    # bend per segment (positive bends down)
        n = k["neck_n"]
        pts = [sh]
        for i in range(n):
            a = -raise_ + curl * i + 0.03 * math.sin(t * 0.8 - i * 0.4)
            q = pts[-1]
            pts.append((q[0] + math.cos(a) * k["neck"] / n, q[1] + math.sin(a) * k["neck"] / n))
        neck = pts[1:]
        head_ang = -raise_ + curl * n + P.get("head_pitch", 0.5)
        tl = []
        q = hip
        tn = k["tail_n"]
        for i in range(tn):
            a = math.pi - 0.25 + i * 0.06 + 0.08 * math.sin(t * 1.1 - i * 0.5) * (i / tn)
            q = (q[0] + math.cos(a) * k["tail"] / tn, q[1] + math.sin(a) * k["tail"] / tn)
            tl.append(q)
        spine = list(reversed(tl)) + body + neck
        radii = [(52 * ((j + 1) / tn) ** 1.1 + 2, 60 * ((j + 1) / tn) ** 1.1 + 2) for j in range(tn)]
        radii += [(70, 96), (86, 120), (92, 128), (86, 122), (66, 92)]
        for i in range(n):
            u = (i + 1) / n
            radii.append((lerp(46, 15, u ** 0.8), lerp(60, 17, u ** 0.8)))
        legs = []
        for name, base, off in (("hf", hip, 0.5), ("ff", sh, 0.75), ("hn", hip, 0.0), ("fn", sh, 0.25)):
            u = (ph + off) % 1.0
            stride = 110
            if moving and u >= 0.75:
                kk = (u - 0.75) / 0.25
                rel = stride * (-0.5 + smooth(kk))
                lft = 26 * math.sin(math.pi * kk)
            elif moving:
                kk = u / 0.75
                rel = stride * (0.5 - kk)
                lft = 0
            else:
                rel, lft = (10 if name[1] == "n" else -14), 0
            top = (base[0] + (8 if name[0] == "h" else -6), base[1] + 30)
            foot = (base[0] + rel + (0 if name[0] == "h" else 10), -lft)
            mid = ((top[0] + foot[0]) / 2 + (8 if name[0] == "f" else -10), (top[1] + foot[1]) / 2)
            legs.append((name, top, mid, foot))
        return dict(spine=spine, radii=radii, legs=legs, head=neck[-1], head_ang=head_ang, t=t, P=P)

    def head_world(self, P, geo=None):
        geo = geo or self.solve(P)
        hx, hy = geo["head"]
        a = geo["head_ang"]
        cx, cy = hx + math.cos(a) * 30, hy + math.sin(a) * 30
        s, f = P.get("s", 1.0), P.get("f", 1.0)
        return (P["x"] + cx * s * f, P["gy"] + cy * s)

    def draw(self, c, P, light=(1, 0.95, 0.8), light_a=0.3, haze=None, haze_a=0.0, shadow=True, silhouette=None):
        k = self.k
        geo = self.solve(P)
        s, f = P.get("s", 1.0), P.get("f", 1.0)
        cols = {n: rgb(k[n]) for n in ("top", "main", "belly", "stripe")}
        if haze is not None and haze_a > 0:
            for n in cols:
                cols[n] = mix(cols[n], haze, haze_a)
        c.save()
        c.translate(P["x"], P["gy"])
        c.scale(s * f, s)
        if shadow:
            ellipse(c, k["body"] * 0.5, 0, k["body"] * 0.95, 14, paint((0, 0, 0), 0.25 * (1 - haze_a), blur=8))
        if silhouette is not None:
            cols = {n: rgb(silhouette) for n in cols}
        far = shade(cols["main"], -0.3) if silhouette is None else cols["main"]
        for name, top, mid, foot in geo["legs"]:
            if name[1] == "f":
                self._leg(c, top, mid, foot, far)
        pts, top_e = self._outline(geo)
        path = spline(pts, closed=True, tension=0.55)
        ys = [p[1] for p in pts]
        if silhouette is None:
            c.drawPath(path, paint(shader=lin((0, min(ys)), (0, max(ys) * 0 + -k["hip_h"] * 0.7),
                                              [(0, cols["top"]), (0.5, cols["main"]), (1, cols["belly"])])))
            c.save()
            c.clipPath(path, skia.ClipOp.kIntersect, True)
            for i in range(0, len(geo["spine"]), 2):
                x, y = geo["spine"][i]
                r = geo["radii"][i][0]
                c.drawCircle(x, y - r * 0.5, r * 0.18, paint(cols["stripe"], 0.25))
            c.drawPath(poly([(p[0], p[1] + 6) for p in top_e], closed=False), paint(light, light_a, stroke=10, blur=8))
            c.restore()
        else:
            c.drawPath(path, paint(cols["main"]))
        for name, top, mid, foot in geo["legs"]:
            if name[1] == "n":
                self._leg(c, top, mid, foot, cols["main"] if silhouette is None else cols["main"])
        # head
        hx, hy = geo["head"]
        c.save()
        c.translate(hx, hy)
        c.rotate(math.degrees(geo["head_ang"]))
        hp = spline([(-6, -10), (14, -16), (34, -12), (48, -4), (50, 6), (30, 12), (6, 12), (-6, 6)])
        c.drawPath(hp, paint(cols["main"] if silhouette is not None else cols["top"]))
        if silhouette is None:
            bl = P.get("blink", 0.0)
            ellipse(c, 16, -5, 4, 3.4 * (1 - bl) + 0.4, paint((0.05, 0.05, 0.04)))
            if bl < 0.5:
                c.drawCircle(15, -6.5, 1.1, paint((1, 1, 1), 0.8))
            ellipse(c, 44, -6, 2.4, 1.5, paint((0.05, 0.05, 0.05), 0.7))
            c.drawPath(poly([(26, 7), (48, 4)], closed=False), paint((0.1, 0.1, 0.1), 0.5, stroke=1.5))
        c.restore()
        c.restore()
        return geo

    def _outline(self, geo):
        sp, rd = geo["spine"], geo["radii"]
        n = len(sp)
        top, bot = [], []
        for i in range(n):
            a = sp[max(0, i - 1)]
            b = sp[min(n - 1, i + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            l = math.hypot(tx, ty) or 1
            nx, ny = ty / l, -tx / l
            top.append((sp[i][0] + nx * rd[i][0], sp[i][1] + ny * rd[i][0]))
            bot.append((sp[i][0] - nx * rd[i][1], sp[i][1] - ny * rd[i][1]))
        return [sp[0]] + top + list(reversed(bot)), top

    def _leg(self, c, top, mid, foot, col):
        p = paint(col)
        c.drawPath(taper(top, mid, 50, 38), p)
        c.drawPath(taper(mid, (foot[0], foot[1] - 18), 38, 33), p)
        ellipse(c, foot[0] + 4, foot[1] - 10, 37, 12, p)


# ----------------------------------------------------------------- pterosaur & birds
def ptero(c, x, y, s, flap, f=1.0, col="#3b3433", crest="#8a3b2b", a=1.0, glide=0.0):
    """flap: phase 0..1. Wings drawn as membranes."""
    c.save()
    c.translate(x, y)
    c.scale(s * f, s)
    w = math.sin(flap * TAU) * (1 - glide)
    p = paint(col, a)
    # far wing
    tipy = -40 * w - 4
    far = [(4, -2), (-12, -24 * w - 6), (-36, tipy * 0.85 - 10), (-6, 6)]
    c.drawPath(spline(far, tension=0.3), paint(shade(rgb(col), -0.2), a))
    # body
    c.drawPath(spline([(-26, 2), (-6, -5), (22, -6), (30, -2), (20, 5), (-6, 6)]), p)
    # head + beak + crest
    c.drawPath(poly([(26, -6), (58, -3), (28, 1)]), p)
    c.drawPath(poly([(24, -6), (12, -16), (28, -8)]), paint(crest, a))
    # near wing
    near = [(6, -1), (-6, 18 * w * 0 - 26 * w - 8), (-44, tipy - 14), (-20, 4), (-2, 6)]
    c.drawPath(spline(near, tension=0.3), p)
    c.restore()


def bird(c, x, y, s, flap, col="#1d1d22", a=1.0):
    w = math.sin(flap * TAU)
    pts = [(-14, -8 * w - 2), (-6, -2 * w), (0, 1), (6, -2 * w), (14, -8 * w - 2)]
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.drawPath(spline(pts, closed=False, tension=0.4), paint(col, a, stroke=2.2))
    c.restore()
