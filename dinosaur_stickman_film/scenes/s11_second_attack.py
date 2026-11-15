"""Scene 11 - The Second Attack. A roar across the valley, the T-Rex bursts from the
trees, a race up a rocky path, a leap over a gap and a one-handed grip."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_out, ease_in, grade_cf, seg, taper)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import prehistoric as PH
from scenes import s10_valley as V

DURATION = 15.0
CUES = {"roar": 0.3, "turn": 0.8, "burst": 2.3, "chase": 4.2, "leap": 7.6, "grab": 8.1, "pebbles": 8.2, "reach": 9.9,
        "pull": 10.5, "over": 11.6, "rex_edge": 12.4, "roar2": 13.0, "step": 14.2}

PAL = PH.P("day")
REX = D.Theropod(D.REX)
RS = 1.5
S = 1.5
GY = 900
GAP0, GAP1 = 4200, 4390


def ground(x):
    if x < 2000:
        return GY
    if x < GAP0:
        return GY - (x - 2000) * 0.18
    if x < GAP1:
        return 2400
    return GY - (GAP0 - 2000) * 0.18 - (x - GAP1) * 0.12


LEDGE_Y = GY - (GAP0 - 2000) * 0.18


def rocky_world(c, cam, t, shake_x=None):
    PH.sky(c, cam, t, PAL, sun=(1500, 220), cloud_seed=13, cloud_y=170)
    PH.far_mountains(c, cam, t, PAL, y=250, p=0.06, seed=51, h=520, key="s11",
                     peaks=[(0.3, 0.9, 0.07), (0.55, 1.0, 0.09), (0.8, 0.85, 0.06)])
    PH.mid_mountains(c, cam, t, PAL, y=380, p=0.16, seed=53, h=520, key="s11",
                     peaks=[(0.45, 0.9, 0.12), (0.7, 1.0, 0.1)])
    PH.flock(c, cam, t, p=0.25, n=6, seed=31, area=(-300, 150, 2600, 400), scale=0.8, col=mix("#3b3433", PAL["haze"], 0.35))
    with cam.view(c, 1.0):
        left, right = cam.left() - 300, cam.right() + 300
        pts = []
        x = left
        while x <= right:
            if GAP0 - 1 < x < GAP1 + 1:
                x = GAP1 + 1 if x < GAP1 else x
            pts.append((x, ground(x)))
            x += 40
        # rock mass: left of gap and right of gap
        for a, b in ((left, GAP0), (GAP1, right)):
            if b <= a:
                continue
            seg_pts = [(x_, ground(x_)) for x_ in range(int(a), int(b) + 1, 40)] + [(b, ground(b - 1 if b == GAP0 else b))]
            poly_pts = seg_pts + [(b, 2400), (a, 2400)]
            c.drawPath(poly(poly_pts), paint(shader=lin((0, LEDGE_Y - 300), (0, GY + 400), [(0, "#8a7f6c"), (1, "#4a4236")])))
            c.save()
            c.clipPath(poly(poly_pts), skia.ClipOp.kIntersect, True)
            r = Rng(int(a) + 5)
            for k in range(int((b - a) / 30)):
                xx = r.u(a, b)
                yy = ground(min(max(xx, a), b - 1)) + r.u(10, 500)
                c.drawLine(xx, yy, xx + r.u(-60, 60), yy + r.u(20, 120), paint((0, 0, 0), 0.12, stroke=r.u(2, 6)))
            c.restore()
            c.drawPath(poly(seg_pts, closed=False), paint("#b5a888", 0.6, stroke=6))
        # the chasm walls
        c.drawRect(skia.Rect(GAP0, LEDGE_Y, GAP1, 2400), paint(shader=lin((0, LEDGE_Y), (0, LEDGE_Y + 600), [(0, "#2a241e"), (1, "#050403")])))
        # grass tufts and rocks along the path
        sp = 260
        for i in range(int(left // sp), int(right // sp) + 1):
            xx = i * sp + hash01(i, 3) * 120
            if GAP0 - 60 < xx < GAP1 + 60:
                continue
            if hash01(i, 4) < 0.5:
                N.rock(c, xx, ground(xx) + 8, 60 + 60 * hash01(i, 5), 30 + 30 * hash01(i, 6), i, col="#7a705e", light=PAL["light"])
            else:
                N.grass(c, xx - 40, xx + 40, ground(xx) + 4, t, seed=i, h=20, density=0.5, col=PAL["grass"][0], col2=PAL["grass"][1])


# ----------------------------------------------------------------- A: the roar echoes
def stick_a(t):
    turn = smooth(inv(t, 0.8, 1.3))
    p = sm.stand(x=V.STICK_X + 330, y=0, s=S, f=1, face=lerp(1.0, -1.0, turn), eye_s=1.0 + 0.6 * smooth(inv(t, 0.4, 0.7)),
                 torso=-0.05 * turn, head=-0.1 * turn)
    p.look = -turn
    sm.settle(p, GY)
    return sm.tremble(p, t, 0.5 * turn)


def shot_echo(c, t):
    p = stick_a(t)
    cam = Cam(p.x - 120, 700, 1.7)
    cam.shake(t, 6 * smooth(inv(t, 0.3, 0.6)) * (1 - smooth(inv(t, 1.6, 2.2))))
    V.valley_backdrop(c, cam, t + 20)
    V.ground(c, cam, t)
    with cam.view(c, 1.0):
        sm.draw(c, p, rim=PAL["light"], rim_a=0.35, rim_dir=(0.8, -0.6), shadow_y=GY + 1)
    for i in range(18):
        h = [hash01(i, 81, k) for k in range(4)]
        age = t - 0.4 - h[0] * 0.5
        if age > 0:
            D.ptero(c, 200 + h[1] * 1500 + (h[2] - 0.5) * 600 * age, 300 + h[3] * 200 - 260 * age, 0.9, age * 2.5 + h[1],
                    f=1 if h[2] > 0.5 else -1, col="#3b3433")


# ----------------------------------------------------------------- B: bursting out of the trees
def rex_b(t):
    u = inv(t, 2.2, 4.2)
    x = lerp(-900, 900, u)
    P = dict(x=x, gy=GY, s=RS, f=1, t=t, gait="run", phase=x * 0.4 / (250 * RS), neck_up=0.2, head_pitch=0.0,
             jaw=0.75 * smooth(inv(t, 2.4, 2.6)) * (1 - smooth(inv(t, 3.6, 4.0))), shake=0.6)
    return P


def shot_burst(c, t):
    cam = Cam(500, 560, 0.8)
    cam.shake(t, 10 * smooth(inv(t, 2.3, 2.5)))
    V.valley_backdrop(c, cam, t + 20)
    V.ground(c, cam, t)
    with cam.view(c, 1.0):
        for i, x in enumerate((-900, -650, -380)):
            N.tree(c, "broad" if i % 2 else "arauc", 90 + i, x, GY + 10, 1100, t, wind=0.02,
                   sway_extra=0.12 * smooth(inv(t, 2.2, 2.6)) * math.sin(t * 14 + i) * (1 - smooth(inv(t, 3.2, 4.0))))
        REX.draw(c, rex_b(t), light=PAL["light"], light_a=0.35, haze=PAL["haze"], haze_a=0.05)
        fx.leaves(c, t, 2.3, -350, GY - 300, 40, 33, spread=700, up=400, dur=2.0, size=10)
        fx.dust(c, t, 2.4, -200, GY, scale=2.0, col=(0.6, 0.55, 0.45), a=0.45, n=10, seed=5)
        sp = dict(x=1700, gy=GY, s=1.2, f=-1, t=t, moving=False, neck_raise=0.6 + 0.4 * smooth(inv(t, 2.5, 3.2)),
                  neck_curl=-0.08, head_pitch=0.3)
        V.SAU.draw(c, sp, light=PAL["light"], light_a=0.3, haze=PAL["haze"], haze_a=0.1)


# ----------------------------------------------------------------- C-F: the rocky path and the gap
VS = 640.0


def stick_x_c(t):
    return 2400 + VS * (t - 4.2)


T_LEAP = 7.6
X_LEAP = stick_x_c(T_LEAP)
GRAB = (GAP1 + 4, LEDGE_Y - (0) - 2)


def stick_path(t):
    if t < T_LEAP:
        x = min(stick_x_c(t), GAP0 - 20)
        return _run(x, t)
    if t < 8.1:
        u = inv(t, T_LEAP, 8.1)
        x = lerp(X_LEAP, GRAB[0] - 30, u)
        y = lerp(ground(X_LEAP) - 80, GRAB[1] + 70, u) - math.sin(math.pi * u) * 110
        return sm.Pose(x=x, y=y, s=S, f=1, torso=0.3, head=-0.3, sh_n=2.7, el_n=0.2, sh_f=2.2, el_f=0.4,
                       hp_n=0.8 - u, kn_n=1.0, hp_f=-0.5, kn_f=0.6, face=1.0, eye_s=1.6)
    if t < 12.2:
        pull = smooth(inv(t, 10.5, 11.6))
        over = smooth(inv(t, 11.6, 12.2))
        sw = math.sin((t - 8.1) * 4) * math.exp(-(t - 8.1) * 1.5)
        hang_y = GRAB[1] + (sm.UARM + sm.FARM + sm.TORSO - 2) * S * 0.98
        p = sm.Pose(x=GRAB[0] - 18 + sw * 10 + 20 * pull, y=lerp(hang_y, GRAB[1] + 12, pull), s=S, f=1, torso=lerp(0.05, 0.8, pull),
                    head=-0.5, face=1.0, eye_s=1.7,
                    hp_n=0.4 + 0.5 * math.sin(t * 9) * (1 - pull) + 1.0 * pull, kn_n=0.6 + 0.4 * math.sin(t * 9 + 1) + pull,
                    hp_f=-0.2 + 0.5 * math.sin(t * 9 + 2) * (1 - pull), kn_f=0.5 + 0.3 * math.sin(t * 9 + 3))
        sm.arm_ik(p, "n", GRAB)
        reach = smooth(inv(t, 9.6, 9.95))
        if t > 9.95:
            sm.arm_ik(p, "f", (GRAB[0] + 34, GRAB[1]))
        else:
            p.sh_f, p.el_f = lerp(0.3, 2.6, reach) + 0.4 * math.sin(t * 7), 0.3
        if over > 0:
            st = sm.Pose(x=GRAB[0] + 70, y=0, s=S, f=1, torso=0.9, head=-0.2, sh_n=0.9, el_n=0.6, sh_f=0.7, el_f=0.6,
                         hp_n=1.2, kn_n=2.0, hp_f=0.2, kn_f=1.6, face=1.0, eye_s=1.4)
            sm.settle(st, LEDGE_Y, parts=("ft_n", "ft_f", "kn_f"))
            p = sm.blend(p, st, over)
        return sm.tremble(p, t, 0.6)
    x0 = GRAB[0] + 70
    mv = sm.Mover(12.2, 15.5, x0, lambda tt: 560 * smooth(inv(tt, 12.3, 12.8)), "sprint", S)
    p = sm.gait(mv.phase(t), mv.x(t), ground(mv.x(t)), S, 1, "sprint", ground=ground)
    st = sm.Pose(x=x0, y=0, s=S, f=1, torso=0.9, head=-0.2, sh_n=0.9, el_n=0.6, sh_f=0.7, el_f=0.6,
                 hp_n=1.2, kn_n=2.0, hp_f=0.2, kn_f=1.6, face=1.0, eye_s=1.4)
    sm.settle(st, LEDGE_Y, parts=("ft_n", "ft_f", "kn_f"))
    p.face, p.eye_s = 1.0, 1.5
    return sm.blend(st, p, smooth(inv(t, 12.2, 12.6)))


def _run(x, t):
    gp = sm.GAITS["sprint"]
    p = sm.gait(x * gp["duty"] / (gp["stride"] * S), x, ground(x), S, 1, "sprint", ground=ground)
    p.face, p.eye_s = 1.0, 1.6
    return p


def rex_path(t):
    if t < 12.4:
        x = stick_x_c(t) - 1250
    else:
        x = stick_x_c(12.4) - 1250
    x = min(x, GAP0 - 520)
    stopped = t >= 12.4 or stick_x_c(t) - 1250 >= GAP0 - 520
    gy = ground(x + 200)
    P = dict(x=x, gy=gy, s=RS, f=1, t=t, gait=None if stopped else "run", phase=x * 0.4 / (250 * RS), neck_up=0.1,
             head_pitch=0.15, jaw=0.35, pitch=-0.12)
    if stopped:
        P["stance"] = 0.2
        r = smooth(inv(t, 13.0, 13.3)) * (1 - smooth(inv(t, 13.8, 14.1)))
        P.update(neck_up=0.1 + 0.3 * r, head_pitch=0.15 - 0.3 * r, jaw=0.3 + 0.5 * r, shake=r)
        if t > 14.1:
            u = smooth(inv(t, 14.1, 15.0))
            P["x"] = x + 330 * u
            P["gait"] = "walk"
            P["phase"] = 0.6 * u
            P["gy"] = lerp(gy, ground(GAP1 + 100), u)
    return P


def shot_path(c, t):
    p = stick_path(t)
    P = rex_path(t)
    if t < 7.2:
        cam = Cam(p.x - 300, p.y - 120, 0.95)
    elif t < 9.2:
        cam = Cam(GAP0 + 40, LEDGE_Y + 40, 1.6)
    elif t < 12.2:
        cam = Cam(GRAB[0] - 10, GRAB[1] + 60, 3.2)
    else:
        cam = Cam(lerp(GAP0 - 100, p.x - 200, smooth(inv(t, 12.2, 15.0))), LEDGE_Y - 80, 0.85)
    sh = 0.0
    if t < 7.2:
        sh = 7
    if 13.0 < t < 14.1:
        sh += 8
    cam.shake(t, sh)
    rocky_world(c, cam, t)
    with cam.view(c, 1.0):
        if t < 7.2 or t > 12.2:
            REX.draw(c, P, light=PAL["light"], light_a=0.35, haze=PAL["haze"], haze_a=0.05)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.35, rim_dir=(0.8, -0.6), shadow_y=ground(p.x) + 1 if not (T_LEAP < t < 12.2) else None)
        if 8.1 <= t < 12.0:
            for k in range(6):
                fx.burst(c, t, 8.15 + k * 0.6, GRAB[0] + 10, GRAB[1] + 4, 5, 700 + k, speed=(30, 120), ang=(0.8, 2.3),
                         grav=1600, life=(0.8, 1.4), size=(2, 4), col=(0.55, 0.5, 0.42))
        if t < 7.2:
            fx.dust(c, t, 5.0, P["x"] + 200, ground(P["x"] + 200), scale=1.6, col=(0.65, 0.6, 0.5), a=0.4, n=8, seed=3)


def render(c, t):
    with layer(c, cf=grade_cf(sat=1.05, contrast=1.08, tint=(1.04, 1.0, 0.94))):
        if t < 2.2:
            shot_echo(c, t)
        elif t < 4.2:
            shot_burst(c, t)
        else:
            shot_path(c, t)
