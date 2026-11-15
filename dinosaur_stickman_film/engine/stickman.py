"""The stickman: one fixed rig used in every shot.

Proportions never change; only the pose and the world scale `s` do. A pose holds
joint angles (radians). Angles are measured from "straight down", positive towards
the direction the character faces, so the same pose works facing left or right.

Thighs are absolute angles; arms are relative to the torso; knees bend backwards,
elbows forwards. Feet and hands can be solved with two-bone IK.
"""
import math
from dataclasses import dataclass, fields, replace

import skia

from .core import (TAU, clamp, lerp, paint, poly, smooth, noise, glow, rgb, mix, ellipse)

HEAD_R = 9.6
TORSO = 31.0
NECK = 3.4
UARM = 16.5
FARM = 15.8
THIGH = 23.0
SHIN = 22.6
LW = 4.4
LEG = THIGH + SHIN
INK = (0.03, 0.03, 0.035)
INK_FAR = (0.13, 0.13, 0.15)


@dataclass
class Pose:
    x: float = 0.0
    y: float = 0.0
    s: float = 1.0
    f: float = 1.0          # facing +1 right, -1 left
    rot: float = 0.0        # whole-body rotation about the hip (positive pitches forward)
    torso: float = 0.0      # lean forward
    head: float = 0.0       # head tilt forward (relative to torso)
    sh_n: float = 0.15      # near arm shoulder (relative to torso)
    el_n: float = 0.2
    sh_f: float = -0.12
    el_f: float = 0.18
    hp_n: float = 0.04      # near thigh (absolute)
    kn_n: float = 0.05
    hp_f: float = -0.04
    kn_f: float = 0.05
    face: float = 1.0       # eye direction: 1 = facing direction, 0 = camera, -1 = behind
    eye: float = 1.0        # 0 closed .. 1 open
    eye_s: float = 1.0      # eye size (fear > 1)
    look: float = 0.0       # pupil x offset -1..1 (screen-relative to face)
    look_y: float = 0.0     # pupil y offset
    pupil: float = 1.0      # pupil visibility
    breath: float = 0.0     # chest / shoulder rise
    alpha: float = 1.0


NUM_FIELDS = [f.name for f in fields(Pose)]


def P(**kw):
    return Pose(**kw)


def blend(a, b, t):
    """Interpolate every field; facing snaps at the midpoint."""
    t = clamp(t)
    out = {}
    for n in NUM_FIELDS:
        va, vb = getattr(a, n), getattr(b, n)
        out[n] = (va if t < 0.5 else vb) if n == "f" else va + (vb - va) * t
    return Pose(**out)


def _v(th):
    return (math.sin(th), math.cos(th))


def local_joints(p):
    J = {}
    tu = (math.sin(p.torso), -math.cos(p.torso))
    J["hip"] = (0.0, 0.0)
    J["neck"] = (tu[0] * TORSO, tu[1] * TORSO)
    sh_len = TORSO - 2.6 + p.breath * 1.3
    J["sh"] = (tu[0] * sh_len, tu[1] * sh_len)
    ha = p.torso + p.head
    hu = (math.sin(ha), -math.cos(ha))
    J["head"] = (J["neck"][0] + hu[0] * (NECK + HEAD_R), J["neck"][1] + hu[1] * (NECK + HEAD_R))
    J["head_a"] = ha
    for side in ("n", "f"):
        a1 = p.torso + getattr(p, "sh_" + side)
        e = (J["sh"][0] + _v(a1)[0] * UARM, J["sh"][1] + _v(a1)[1] * UARM)
        a2 = a1 + getattr(p, "el_" + side)
        h = (e[0] + _v(a2)[0] * FARM, e[1] + _v(a2)[1] * FARM)
        J["el_" + side], J["hand_" + side] = e, h
        t1 = getattr(p, "hp_" + side)
        k = (_v(t1)[0] * THIGH, _v(t1)[1] * THIGH)
        t2 = t1 - getattr(p, "kn_" + side)
        ft = (k[0] + _v(t2)[0] * SHIN, k[1] + _v(t2)[1] * SHIN)
        J["kn_" + side], J["ft_" + side] = k, ft
    return J


def to_world(p, pt):
    x, y = pt[0] * p.f, pt[1]
    r = p.rot * p.f
    cr, sr = math.cos(r), math.sin(r)
    return (p.x + (x * cr - y * sr) * p.s, p.y + (x * sr + y * cr) * p.s)


def to_local(p, pt):
    x, y = (pt[0] - p.x) / p.s, (pt[1] - p.y) / p.s
    r = -p.rot * p.f
    cr, sr = math.cos(r), math.sin(r)
    x, y = x * cr - y * sr, x * sr + y * cr
    return (x * p.f, y)


def joints(p):
    J = local_joints(p)
    out = {k: to_world(p, v) for k, v in J.items() if k != "head_a"}
    out["head_a"] = J["head_a"]
    return out


def ik2(d, l1, l2, bend):
    """Two-bone IK in 'angle from down' space. Returns (first-bone angle, bend)."""
    dist = math.hypot(*d)
    dist = clamp(dist, abs(l1 - l2) + 1e-3, (l1 + l2) * 0.9995)
    phi = math.atan2(d[0], d[1])
    a = math.acos(clamp((l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist), -1, 1))
    b = math.acos(clamp((l1 * l1 + l2 * l2 - dist * dist) / (2 * l1 * l2), -1, 1))
    return phi + a * bend, math.pi - b


def leg_ik(p, side, foot_world):
    lx, ly = to_local(p, foot_world)
    th, kn = ik2((lx, ly), THIGH, SHIN, 1)
    setattr(p, "hp_" + side, th)
    setattr(p, "kn_" + side, kn)
    return p


def arm_ik(p, side, hand_world):
    J = local_joints(p)
    lx, ly = to_local(p, hand_world)
    d = (lx - J["sh"][0], ly - J["sh"][1])
    th, el = ik2(d, UARM, FARM, -1)
    setattr(p, "sh_" + side, th - p.torso)
    setattr(p, "el_" + side, el)
    return p


def lowest(p, parts=("ft_n", "ft_f")):
    J = joints(p)
    return max(J[k][1] for k in parts)


def settle(p, gy, parts=("ft_n", "ft_f")):
    """Move the figure vertically so its lowest listed joint rests on gy."""
    J = joints(p)
    if "head" in parts:
        low = max(max(J[k][1] for k in parts if k != "head"), J["head"][1] + HEAD_R * p.s)
    else:
        low = max(J[k][1] for k in parts)
    p.y += gy - low - LW * 0.5 * p.s
    return p


# ----------------------------------------------------------------- drawing
def _limb(c, pts, w, col, a, blur=0.0, dx=0.0, dy=0.0):
    c.drawPath(poly([(x + dx, y + dy) for x, y in pts], closed=False), paint(col, a, stroke=w, blur=blur))


def draw(c, p, rim=None, rim_a=0.55, rim_dir=(-0.7, -0.7), glow_col=None, glow_a=0.0, ink=INK, shadow_y=None,
         shadow_a=0.28, wet=0.0):
    """Draw the stickman. rim = colour of a light catching one edge."""
    J = joints(p)
    s = p.s
    lw = LW * s
    a = p.alpha
    far_arm = [J["sh"], J["el_f"], J["hand_f"]]
    far_leg = [J["hip"], J["kn_f"], J["ft_f"]]
    near_leg = [J["hip"], J["kn_n"], J["ft_n"]]
    near_arm = [J["sh"], J["el_n"], J["hand_n"]]
    torso = [J["hip"], J["neck"]]
    hx, hy = J["head"]
    hr = HEAD_R * s

    if shadow_y is not None:
        cx = (J["ft_n"][0] + J["ft_f"][0]) / 2
        h = max(0.0, shadow_y - max(J["ft_n"][1], J["ft_f"][1]))
        k = clamp(1 - h / (60 * s))
        ellipse(c, cx, shadow_y + 1.5 * s, 17 * s * (0.6 + 0.4 * k), 3.2 * s, paint((0, 0, 0), shadow_a * k * a, blur=2.5 * s))

    if glow_col is not None and glow_a > 0:
        glow(c, hx, (hy + J["hip"][1]) / 2, 70 * s, glow_col, glow_a * a)

    if rim is not None:
        ox, oy = rim_dir[0] * lw * 0.42, rim_dir[1] * lw * 0.42
        rw = lw * 1.75
        for pts in (far_arm, far_leg, torso, near_leg, near_arm):
            _limb(c, pts, rw, rim, rim_a * a, blur=lw * 0.35, dx=ox, dy=oy)
        c.drawCircle(hx + ox, hy + oy, hr + lw * 0.45, paint(rim, rim_a * a, blur=lw * 0.35))

    _limb(c, far_arm, lw, mix(ink, INK_FAR, 1.0) if ink == INK else ink, a)
    _limb(c, far_leg, lw, mix(ink, INK_FAR, 1.0) if ink == INK else ink, a)
    _limb(c, torso, lw * 1.08, ink, a)
    _limb(c, near_leg, lw, ink, a)
    _limb(c, near_arm, lw, ink, a)
    c.drawCircle(hx, hy, hr, paint(ink, a))
    if wet > 0:
        c.drawCircle(hx - hr * 0.35, hy - hr * 0.4, hr * 0.25, paint((1, 1, 1), 0.25 * wet * a, blur=hr * 0.15))
    _eyes(c, p, J, hx, hy, hr)
    return J


def _eyes(c, p, J, hx, hy, hr):
    if p.eye <= 0.02 or p.alpha <= 0.01:
        if p.eye <= 0.02 and p.alpha > 0.01:
            # closed eyes: two short lines
            fa = p.face * p.f
            cx = fa * 0.40 * hr
            sp = hr * 0.62 * (1 - 0.5 * abs(p.face))
            for k, ex in enumerate((cx - sp / 2, cx + sp / 2)):
                ang = J["head_a"] * p.f + p.rot * p.f
                x, y = hx + ex * math.cos(ang), hy + ex * math.sin(ang) + hr * 0.02
                c.drawLine(x - hr * 0.12, y, x + hr * 0.12, y, paint((0.85, 0.87, 0.9), 0.55 * p.alpha, stroke=hr * 0.07))
        return
    fa = clamp(p.face, -1, 1)
    sx = fa * p.f  # screen-space direction of gaze
    cx = sx * 0.42 * hr
    sp = hr * 0.64 * (1 - 0.5 * abs(fa))
    ang = (J["head_a"] + p.rot) * p.f
    ca, sa = math.cos(ang), math.sin(ang)
    for k, ex in enumerate((cx - sp / 2, cx + sp / 2)):
        far = (k == 0 and sx > 0) or (k == 1 and sx < 0)
        sc = (1 - 0.22 * abs(fa)) if far else 1.0
        ey = -hr * 0.08
        x = hx + ex * ca - ey * sa
        y = hy + ex * sa + ey * ca
        rw = hr * 0.17 * sc * p.eye_s
        rh = hr * 0.25 * sc * p.eye_s * clamp(p.eye)
        c.save()
        c.translate(x, y)
        c.rotate(math.degrees(ang))
        ellipse(c, 0, 0, rw, rh, paint((0.97, 0.97, 0.98), p.alpha))
        if p.pupil > 0.01 and p.eye > 0.35:
            px = clamp(p.look * p.f + sx * 0.25, -1, 1) * rw * 0.45
            py = p.look_y * rh * 0.45
            pr = min(rw, rh) * 0.52
            c.drawCircle(px, py, pr, paint(INK, p.alpha * p.pupil))
        c.restore()


# ----------------------------------------------------------------- pose library
def stand(**kw):
    d = dict(sh_n=0.10, el_n=0.12, sh_f=-0.08, el_f=0.10, hp_n=0.05, kn_n=0.04, hp_f=-0.05, kn_f=0.03)
    d.update(kw)
    return Pose(**d)


def breathe(p, t, rate=0.25, amt=1.0):
    b = 0.5 + 0.5 * math.sin(t * TAU * rate)
    q = replace(p)
    q.breath = b * amt
    q.torso += -0.015 * b * amt
    q.sh_n += 0.02 * b * amt
    q.sh_f -= 0.02 * b * amt
    return q


def tremble(p, t, amt=1.0):
    q = replace(p)
    q.torso += noise(t * 31, 3) * 0.02 * amt
    q.head += noise(t * 37, 5) * 0.05 * amt
    q.sh_n += noise(t * 29, 7) * 0.06 * amt
    q.sh_f += noise(t * 33, 11) * 0.06 * amt
    q.el_n += noise(t * 41, 13) * 0.06 * amt
    q.x += noise(t * 27, 17) * 0.5 * amt * p.s
    return q


GAITS = {
    "walk":   dict(stride=30, duty=0.60, lift=6.5, bob=1.3, lean=0.05, arm=0.42, elb=0.32, elb_amp=0.10, crouch=1.2, head=0.02),
    "sneak":  dict(stride=17, duty=0.72, lift=6.0, bob=0.6, lean=0.20, arm=0.18, elb=1.00, elb_amp=0.05, crouch=5.5, head=-0.05),
    "run":    dict(stride=66, duty=0.36, lift=19, bob=4.0, lean=0.30, arm=0.95, elb=1.65, elb_amp=0.20, crouch=3.0, head=-0.12),
    "sprint": dict(stride=76, duty=0.34, lift=22, bob=4.5, lean=0.40, arm=1.10, elb=1.75, elb_amp=0.25, crouch=3.5, head=-0.18),
    "tired":  dict(stride=20, duty=0.66, lift=4.0, bob=2.2, lean=0.42, arm=0.12, elb=0.20, elb_amp=0.04, crouch=4.5, head=0.30),
    "climb":  dict(stride=22, duty=0.62, lift=9.0, bob=1.8, lean=0.48, arm=0.45, elb=0.9, elb_amp=0.3, crouch=6.0, head=-0.05),
}


def gait_params(kind):
    if isinstance(kind, dict):
        return kind
    return GAITS[kind]


def mix_gait(a, b, t):
    A, B = gait_params(a), gait_params(b)
    return {k: lerp(A[k], B[k], t) for k in A}


def gait(phase, x, gy, s=1.0, f=1.0, kind="walk", ground=None, **over):
    """Locomotion pose. phase = cycles travelled (see Mover). gy = ground y at x.
    ground(x) -> y lets feet follow slopes."""
    g = dict(gait_params(kind))
    g.update(over)
    ph = phase % 1.0
    run = g["duty"] < 0.5
    if run:
        bob = -g["bob"] * math.cos(ph * TAU * 2)          # high in flight
    else:
        bob = g["bob"] * math.cos(ph * TAU * 2)           # high at mid-stance
    hip_h = (LEG * 0.97 - g["crouch"] + bob) * s
    p = Pose(x=x, y=gy - hip_h, s=s, f=f, torso=g["lean"] + 0.03 * math.sin(ph * TAU * 2), head=g["head"])
    for side, off in (("n", 0.0), ("f", 0.5)):
        u = (ph + off) % 1.0
        if u < g["duty"]:
            k = u / g["duty"]
            rel = g["stride"] * (0.5 - k)
            lift = 0.0
        else:
            k = (u - g["duty"]) / (1 - g["duty"])
            e = smooth(k)
            rel = g["stride"] * (-0.5 + e)
            lift = g["lift"] * math.sin(math.pi * k) * (1.0 if run else 1.0)
        fx = x + rel * s * f
        fy = (ground(fx) if ground else gy) - lift * s - LW * 0.5 * s
        leg_ik(p, side, (fx, fy))
    sw = math.cos(ph * TAU)
    p.sh_n = -g["arm"] * sw - (0.1 if run else 0.0)
    p.sh_f = g["arm"] * sw - (0.1 if run else 0.0)
    p.el_n = g["elb"] + g["elb_amp"] * max(0, sw)
    p.el_f = g["elb"] + g["elb_amp"] * max(0, -sw)
    return p


class Mover:
    """Integrates a speed curve so walk cycles never slide.

    speed(t) in world units/second, kind(t) -> gait name or dict, s = scale.
    Samples at 240 Hz from t0..t1 and gives position and gait phase at any t."""

    def __init__(self, t0, t1, x0, speed, kind="walk", s=1.0, rate=240):
        import numpy as np
        self.t0, self.rate = t0, rate
        n = int((t1 - t0) * rate) + 2
        self.xs = np.zeros(n)
        self.ph = np.zeros(n)
        x, ph = x0, 0.0
        dt = 1.0 / rate
        for i in range(n):
            t = t0 + i * dt
            self.xs[i], self.ph[i] = x, ph
            v = speed(t)
            g = gait_params(kind(t) if callable(kind) else kind)
            x += v * dt
            ph += abs(v) * dt * g["duty"] / (g["stride"] * s)
        self.kind = kind

    def _i(self, t):
        f = (t - self.t0) * self.rate
        i = int(clamp(math.floor(f), 0, len(self.xs) - 2))
        return i, clamp(f - i, 0, 1)

    def x(self, t):
        i, u = self._i(t)
        return self.xs[i] + (self.xs[i + 1] - self.xs[i]) * u

    def phase(self, t):
        i, u = self._i(t)
        return self.ph[i] + (self.ph[i + 1] - self.ph[i]) * u


class Track:
    """Pose keyframes: [(time, pose_or_fn, ease)]. fn(t) -> Pose for live poses."""

    def __init__(self, keys):
        self.keys = keys

    def __call__(self, t):
        ks = self.keys

        def ev(k, tt):
            v = k[1]
            return v(tt) if callable(v) else v
        if t <= ks[0][0]:
            return ev(ks[0], t)
        for a, b in zip(ks, ks[1:]):
            if t <= b[0]:
                fn = b[2] if len(b) > 2 else smooth
                u = fn(clamp((t - a[0]) / max(1e-6, b[0] - a[0])))
                return blend(ev(a, t), ev(b, t), u)
        return ev(ks[-1], t)


def draw_front(c, x, y, s, phase, look_back=0.0, eye_s=1.4, rim=None, rim_a=0.5, ink=INK, arms_up=0.0):
    """Stickman running straight at the camera. (x, y) = hip. phase = gait cycles."""
    ph = phase * TAU
    lw = LW * s
    bob = abs(math.sin(ph)) * 4 * s
    hip = (x, y - bob)
    neck = (x + math.sin(ph) * 2 * s, hip[1] - TORSO * s)
    head = (neck[0], neck[1] - (NECK + HEAD_R) * s)
    sh = (neck[0], neck[1] + 2.6 * s)
    pts = []
    for side in (-1, 1):
        u = math.sin(ph + (0 if side < 0 else math.pi))
        lift = max(0.0, u)
        kx = x + side * 6 * s
        knee = (kx, hip[1] + THIGH * s * (1 - 0.65 * lift))
        foot = (kx + side * 2 * s, knee[1] + SHIN * s * (1 - 0.15 * lift) - 6 * s * lift)
        pts.append([(x + side * 4 * s, hip[1]), knee, foot])
        a = math.sin(ph + (math.pi if side < 0 else 0))
        el = (sh[0] + side * 12 * s, sh[1] + 12 * s - 6 * s * a)
        hd = (el[0] - side * 4 * s, el[1] - 10 * s * (0.6 + 0.6 * a) - arms_up * 20 * s)
        pts.append([(sh[0] + side * 3 * s, sh[1]), el, hd])
    allp = pts + [[hip, neck]]
    if rim is not None:
        for q in allp:
            c.drawPath(poly(q, closed=False), paint(rim, rim_a, stroke=lw * 1.8, blur=lw * 0.4))
        c.drawCircle(head[0], head[1], HEAD_R * s + lw * 0.4, paint(rim, rim_a, blur=lw * 0.4))
    for q in allp:
        c.drawPath(poly(q, closed=False), paint(ink, stroke=lw))
    c.drawCircle(head[0], head[1], HEAD_R * s, paint(ink))
    hr = HEAD_R * s
    for side in (-1, 1):
        ex = head[0] + side * hr * 0.32 - look_back * hr * 0.3
        ey = head[1] - hr * 0.08
        ellipse(c, ex, ey, hr * 0.17 * eye_s, hr * 0.25 * eye_s, paint((0.97, 0.97, 0.98)))
        c.drawCircle(ex + look_back * hr * 0.05, ey, hr * 0.09 * eye_s, paint(INK))
    return head
