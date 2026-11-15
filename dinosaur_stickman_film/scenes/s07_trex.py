"""Scene 7 - The Tyrannosaurus Rex. Feet crushing ferns, a slow tilt up the body,
the eye, the roar, a terrible silence, the charge."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_out, ease_in, grade_cf, seg)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import prehistoric as PH

DURATION = 19.0
CUES = {"foot1": 0.8, "foot2": 2.15, "tilt": 4.2, "foot3": 3.5, "foot4": 4.85, "foot5": 6.2, "eye": 8.4, "snort": 9.4,
        "roar": 10.9, "silence": 13.6, "lunge": 16.3, "run": 16.6}

PAL = PH.P("forest")
REX = D.Theropod(D.REX)
GY = 900
RS = 1.5                      # T-Rex scale
WALK = D.REX["walk"]
V = 110.0                     # walking speed (world px/s)
CYCLE = WALK["stride"] * RS / WALK["duty"]
CPS = V / CYCLE
X_LAND = 620.0                # where the near foot lands at t=0.8
X0 = X_LAND - (D.REX["foot_off"] + WALK["stride"] / 2) * RS
STOP_T = 7.4


def rex_x(t):
    tt = min(t, STOP_T)
    return X0 + V * (tt - 0.8)


def rex_phase(t):
    return (min(t, STOP_T) - 0.8) * CPS


def foot_down_times():
    out = []
    for k in range(-1, 6):
        out.append(0.8 + k / CPS)
        out.append(0.8 + (k + 0.5) / CPS)
    return sorted(x for x in out if 0 <= x < STOP_T)


STEPS = foot_down_times()
STICK_X = 1990


def rex_pose(t):
    P = dict(x=rex_x(t), gy=GY, s=RS, f=1, t=t, gait="walk" if t < STOP_T else None, phase=rex_phase(t),
             neck_up=0.3, head_pitch=0.2, tail_lift=0.08)
    if t >= STOP_T:
        settle = smooth(inv(t, STOP_T, STOP_T + 0.6))
        P["stance"] = 0.18
        P["neck_up"] = lerp(0.3, 0.18, settle)
        P["head_pitch"] = 0.2 + 0.05 * math.sin(t * 0.8)
        P["blink"] = 1.0 if t < 8.4 else max(0.0, 1 - inv(t, 8.4, 8.75))
        P["pupil"] = lerp(1.5, 0.55, smooth(inv(t, 8.8, 9.6)))
    if t >= 10.4:
        # roar: rear back, then thrust forward with the jaw wide
        r_up = smooth(inv(t, 10.4, 10.9))
        r_on = smooth(inv(t, 10.9, 11.3)) * (1 - smooth(inv(t, 13.0, 13.5)))
        P["neck_up"] = 0.18 + 0.28 * r_up - 0.38 * r_on
        P["head_pitch"] = 0.2 - 0.25 * r_up + 0.12 * r_on
        P["pitch"] = -0.06 * r_up + 0.07 * r_on
        P["jaw"] = 0.12 * r_up + 0.72 * r_on
        P["shake"] = 1.2 * r_on
        P["tail_lift"] = 0.08 + 0.12 * r_on
    if t >= 13.5:
        # lower the head right down to the stickman and stare
        low = smooth(inv(t, 13.5, 15.2))
        P["neck_up"] = lerp(0.18, -0.35, low)
        P["neck_bend"] = -0.12 + 0.1 * low
        P["head_pitch"] = lerp(0.2, 0.32, low)
        P["pitch"] = 0.12 * low
        P["crouch"] = 18 * low
        P["jaw"] = 0.05 * low
        P["shake"] = 0.0
        P["blink"] = 1.0 if 15.0 < t < 15.12 else 0.0
        P["pupil"] = 0.5
    if t >= 16.2:
        lunge = ease_out(inv(t, 16.2, 16.55))
        back = smooth(inv(t, 16.6, 17.2))
        P["pitch"] = 0.12 + 0.12 * lunge - 0.1 * back
        P["x"] = rex_x(t) + 60 * lunge
        P["jaw"] = 0.05 + 0.7 * lunge * (1 - 0.6 * back)
        P["neck_up"] = -0.35 + 0.1 * back
    if t >= 17.0:
        dt = t - 17.0
        run = D.REX["run"]
        P.update(gait="run", phase=dt * 1.6, x=rex_x(t) + 60 + 520 * dt ** 1.25, neck_up=0.0, head_pitch=0.2, jaw=0.4,
                 crouch=0.0, pitch=0.0)
    return P


def stick_pose(t):
    gy = GY
    if t < 16.4:
        fear = smooth(inv(t, 11.0, 11.4))
        blown = smooth(inv(t, 11.0, 11.3)) * (1 - smooth(inv(t, 13.0, 13.6)))
        p = sm.stand(x=STICK_X, y=0, s=1.8, f=-1, face=1.0, eye_s=1.2 + 0.5 * fear, torso=-0.3 * blown,
                     head=-0.2 * blown, sh_n=0.3 + 1.9 * blown, el_n=0.3 + 1.2 * blown, sh_f=0.2 + 1.6 * blown,
                     el_f=0.5 + 1.0 * blown, hp_n=0.25 * blown + 0.05, hp_f=-0.3 * blown - 0.05)
        p.x += 25 * blown
        sm.settle(p, gy)
        frozen = smooth(inv(t, 13.6, 14.0))
        p = sm.tremble(p, t, 0.6 + 1.0 * fear + 1.4 * frozen)
        p.pupil = 1.0
        p.look = 0.6
        return p
    run = sm.Mover(16.4, 19.5, STICK_X + 25, lambda tt: 950 * smooth(inv(tt, 16.55, 16.9)), "sprint", 1.8)
    turn = smooth(inv(t, 16.4, 16.6))
    g = sm.gait(run.phase(t), run.x(t), gy, 1.8, 1, "sprint")
    g.face, g.eye_s = 1.0, 1.6
    start = sm.Pose(x=STICK_X + 25, y=0, s=1.8, f=1, torso=0.5, head=-0.1, sh_n=-1.0, el_n=1.5, sh_f=1.0, el_f=1.5,
                    hp_n=0.6, kn_n=0.9, hp_f=-0.4, kn_f=0.6, face=1.0, eye_s=1.6)
    sm.settle(start, gy)
    if t < 16.6:
        return start
    return sm.blend(start, g, smooth(inv(t, 16.6, 16.85)))


def shake(t):
    s = 0.0
    for tt in STEPS:
        if t >= tt:
            s = max(s, 22 * math.exp(-(t - tt) * 6))
    if 10.9 <= t < 13.4:
        s += 16 * (1 - inv(t, 12.4, 13.4)) * smooth(inv(t, 10.9, 11.1))
    if t >= 16.2:
        s += 10 * math.exp(-(t - 16.2) * 2)
    return s


def flat_for(t):
    """Ferns flattened where a foot is standing."""
    P = rex_pose(t)
    geo = REX.solve(P)
    pts = []
    for side in ("n", "f"):
        fx_, fy_ = REX.foot_world(P, side, geo)
        if fy_ > GY - 30:
            pts.append(fx_)
    return lambda x: max([clamp(1 - abs(x - p) / 120) for p in pts] + [0.0])


def environment(c, cam, t, flat=None, rays=0.14):
    PH.forest_world(c, cam, t, PAL, GY, seed=11, sun=(1400, 80), rays=rays, flat=flat)


def draw_rex(c, t, P, geo=None):
    return REX.draw(c, P, light=PAL["light"], light_a=0.35, haze=PAL["haze"], haze_a=0.05, geo=geo, shadow_a=0.3)


def dusts(c, t):
    for k, tt in enumerate(STEPS):
        if 0 <= t - tt < 2.5:
            P = rex_pose(tt + 0.02)
            side = "n" if abs(((rex_phase(tt) + 1e-3) % 1.0)) < 0.25 else "f"
            fxp = REX.foot_world(P, side)
            fx.dust(c, t, tt, fxp[0], GY, scale=1.6, col=(0.55, 0.5, 0.4), a=0.5, n=9, seed=k, spread=1.3, rise=0.25)
            fx.leaves(c, t, tt, fxp[0], GY - 20, 10, k + 50, spread=260, up=200, dur=2.0, size=7)


# ----------------------------------------------------------------- shots
def shot_feet(c, t):
    cam = Cam(X_LAND + 60, 820, 3.0)
    cam.shake(t, shake(t))
    environment(c, cam, t, flat=flat_for(t), rays=0.1)
    P = rex_pose(t)
    with cam.view(c, 1.0):
        draw_rex(c, t, P)
        dusts(c, t)
        for i, x in enumerate((X_LAND - 300, X_LAND - 120, X_LAND + 90, X_LAND + 280)):
            fl = flat_for(t)(x)
            N.fern(c, x, GY + 6, 170, 200 + i, t, wind=0.06, col=PAL["forest"][1], col2=PAL["forest"][2], flat=fl)
    with cam.view(c, 1.4):
        with layer(c, blur=10):
            N.fern(c, 600, GY + 210, 330, 21, t, wind=0.05, col=shade(PAL["forest"][0], -0.4), col2=shade(PAL["forest"][1], -0.4))
            N.fern(c, 1500, GY + 220, 300, 22, t, wind=0.05, col=shade(PAL["forest"][0], -0.4), col2=shade(PAL["forest"][1], -0.4))


def shot_tilt(c, t):
    u = ease_io(inv(t, 4.2, 8.0))
    P = rex_pose(t)
    hx, hy = REX.head_world(P)
    cam = Cam(lerp(rex_x(t) + 80, hx - 120, u), lerp(820, hy + 80, u), lerp(2.3, 1.15, u))
    cam.shake(t, shake(t) * 0.6)
    environment(c, cam, t, rays=0.18)
    with cam.view(c, 1.0):
        draw_rex(c, t, P)
        dusts(c, t)
    PH.forest_foreground(c, cam, t, PAL, GY, seed=9, blur=12, p=1.5, dark=0.5)


def shot_eye(c, t):
    P = rex_pose(t)
    geo = REX.solve(P)
    ex, ey = REX.eye_world(P, geo)
    cam = Cam(ex + 70, ey + 30, lerp(5.2, 5.6, inv(t, 8.0, 10.4)))
    with cam.view(c, 0.3):
        with layer(c, blur=14):
            environment(c, Cam(ex, ey + 200, 1.0), t, rays=0.2)
    with cam.view(c, 1.0):
        draw_rex(c, t, P, geo)
        if t > 9.3:
            nx, ny = REX.to_world(P, (geo["head"][0] + math.cos(geo["head_ang"]) * 112, geo["head"][1] + math.sin(geo["head_ang"]) * 112 - 8))
            for k in range(2):
                fx.dust(c, t, 9.4 + k * 0.5, nx + 8, ny, scale=0.25, col=(0.92, 0.94, 0.95), a=0.4, n=6, seed=k + 3, spread=0.6,
                        rise=-0.1, dur=1.2, dirx=1.2)


def shot_roar(c, t):
    P = rex_pose(t)
    geo = REX.solve(P)
    cam = Cam(1520, 560, 1.0)
    cam.shake(t, shake(t))
    environment(c, cam, t, rays=0.2)
    with cam.view(c, 1.0):
        draw_rex(c, t, P, geo)
        if t > 10.9:
            mx, my = REX.mouth_world(P, geo)
            fx.burst(c, t, 10.95, mx, my, 50, 9, speed=(500, 1100), ang=(-0.5, 0.35), grav=200, life=(0.5, 1.2), size=(1.5, 3.5),
                     col=(0.92, 0.95, 0.95), a=0.5, spawn=1.8, drag=1.5)
            fx.leaves(c, t, 11.0, mx + 300, my - 100, 26, 12, spread=500, up=80, dur=2.4, size=8, wind=900)
        p = stick_pose(t)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.3, rim_dir=(0.6, -0.8), shadow_y=GY + 1)
    PH.forest_foreground(c, cam, t, PAL, GY, seed=13, blur=10, p=1.4, dark=0.5)


def shot_stare(c, t):
    P = rex_pose(t)
    geo = REX.solve(P)
    p = stick_pose(t)
    ex, ey = REX.eye_world(P, geo)
    u = ease_io(inv(t, 13.5, 16.2))
    cam = Cam(lerp(1330, (ex + p.x) / 2 + 40, u), lerp(700, (ey + p.y) / 2 - 30, u), lerp(1.6, 2.4, u))
    cam.shake(t, shake(t) * 0.5)
    with cam.view(c, 0.4):
        with layer(c, blur=6):
            environment(c, Cam(1300, 600, 1.0), t, rays=0.12)
    with cam.view(c, 1.0):
        draw_rex(c, t, P, geo)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.35, rim_dir=(0.6, -0.8), shadow_y=GY + 1)
        if t > 14.6:
            nx, ny = REX.mouth_world(P, geo)
            fx.dust(c, t, 15.4, nx - 30, ny - 40, scale=0.35, col=(0.9, 0.92, 0.92), a=0.35, n=6, seed=8, spread=0.5,
                    rise=0.0, dur=1.2, dirx=1.5)


def shot_charge(c, t):
    P = rex_pose(t)
    p = stick_pose(t)
    cam = Cam(lerp(1500, p.x - 100, smooth(inv(t, 16.6, 18.4))), 600, 1.25)
    cam.shake(t, shake(t))
    environment(c, cam, t, rays=0.12)
    with cam.view(c, 1.0):
        draw_rex(c, t, P)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.3, rim_dir=(0.6, -0.8), shadow_y=GY + 1)
        fx.leaves(c, t, 17.2, rex_x(t) + 500, GY - 300, 20, 77, spread=500, up=200, dur=2.0, size=8)
    PH.forest_foreground(c, cam, t, PAL, GY, seed=14, blur=10, p=1.4, dark=0.5)


def render(c, t):
    tint = (0.98, 1.0, 0.95) if t < 10.4 else (0.96, 0.98, 0.94)
    with layer(c, cf=grade_cf(sat=0.98, contrast=1.1, tint=tint)):
        if t < 4.2:
            shot_feet(c, t)
        elif t < 8.0:
            shot_tilt(c, t)
        elif t < 10.4:
            shot_eye(c, t)
        elif t < 13.5:
            shot_roar(c, t)
        elif t < 16.2:
            shot_stare(c, t)
        else:
            shot_charge(c, t)
