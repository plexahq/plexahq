"""Scene 12 - The Final Escape. A low rock arch the T-Rex cannot pass, a collapsing
ceiling, and a long, exhausted climb to the top of the mountain."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_out, ease_in, grade_cf, seg, taper)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import prehistoric as PH

DURATION = 15.0
CUES = {"enter": 1.4, "ram": 2.4, "snap1": 2.7, "snap2": 3.3, "inside": 3.2, "crack": 5.4, "collapse": 6.0,
        "rumble": 6.2, "climb": 8.8, "rest": 11.0, "top": 13.0}

PAL = PH.P("day")
SUN = PH.P("sunset")
REX = D.Theropod(D.REX)
RS = 1.5
S = 1.5
GY = 900
ARCH0, ARCH1 = 1800, 4500       # the rock tunnel
CEIL = GY - 260                 # tunnel ceiling height


def rock_mass(c, t, crack=0.0):
    """A huge boulder pile with a low tunnel through it."""
    top = [(ARCH0 - 300, GY), (ARCH0 - 220, GY - 520), (ARCH0 + 200, GY - 760), (ARCH0 + 700, GY - 860),
           (ARCH0 + 1500, GY - 980), (ARCH1 - 600, GY - 900), (ARCH1 - 200, GY - 700), (ARCH1 + 200, GY - 420), (ARCH1 + 320, GY)]
    path = spline(top, closed=True, tension=0.4)
    c.drawPath(path, paint(shader=lin((0, GY - 820), (0, GY), [(0, "#9a8b70"), (0.6, "#6e624f"), (1, "#40382d")])))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    r = Rng(9)
    for k in range(60):
        x = r.u(ARCH0 - 300, ARCH1 + 300)
        y = r.u(GY - 820, GY)
        c.drawPath(blob(x, y, r.u(30, 90), r.i(0, 999), 7, 0.25, 0.7), paint(shade("#7a6c56", r.u(-0.2, 0.15)), 0.5))
    c.drawPath(spline([(ARCH0 + 100, GY - 760), (ARCH0 + 700, GY - 830), (ARCH1 - 100, GY - 690)], closed=False),
               paint(PAL["light"], 0.3, stroke=30, blur=20))
    c.restore()
    # tunnel opening (dark interior)
    hole = poly([(ARCH0 - 120, GY), (ARCH0 - 100, CEIL + 30), (ARCH0, CEIL), (ARCH1, CEIL - 10), (ARCH1 + 100, CEIL + 30),
                 (ARCH1 + 120, GY)])
    c.drawPath(hole, paint(shader=lin((ARCH0, 0), (ARCH1, 0), [(0, "#120e0a"), (0.85, "#1c1610"), (1, "#5a4a36")])))
    if crack > 0:
        for k in range(5):
            x0 = lerp(ARCH0 + 200, ARCH0 + 700, k / 4)
            c.drawPath(poly([(x0, CEIL), (x0 + 30, CEIL - 120 * crack), (x0 - 10, CEIL - 240 * crack)], closed=False),
                       paint((0.05, 0.04, 0.03), 0.9, stroke=4))


def stick(t):
    if t < 8.8:
        if t < 3.2:
            mv_x = 900 + 600 * t
            kind = "sprint"
        else:
            mv_x = 900 + 600 * 3.2 + 330 * (t - 3.2)
            kind = "run"
        if t > 6.0:
            mv_x += 60 * smooth(inv(t, 6.2, 6.6))
        gp = sm.GAITS[kind]
        p = sm.gait(mv_x * gp["duty"] / (gp["stride"] * S), mv_x, GY, S, 1, kind)
        p.face, p.eye_s = 1.0, 1.6
        if t > 3.2:
            p.torso += 0.25
            p.y += 8
        if 6.2 < t < 6.8:
            p.torso += 0.3 * math.sin(math.pi * inv(t, 6.2, 6.8))
        return p
    return None


def rex(t):
    stop_x = ARCH0 - 430
    x = min(-700 + 640 * t, stop_x)
    stuck = x >= stop_x
    P = dict(x=x, gy=GY, s=RS, f=1, t=t, gait=None if stuck else "run", phase=x * 0.4 / (250 * RS), neck_up=0.05,
             head_pitch=0.2, jaw=0.4)
    if stuck:
        k = t - (stop_x + 700) / 640
        ram = ease_out(inv(k, 0.0, 0.25))
        P.update(stance=0.25, pitch=0.18 * ram, crouch=40 * ram, neck_up=-0.15 * ram, head_pitch=0.15,
                 x=stop_x + 40 * ram)
        snap = abs(math.sin(k * 5.5)) * (1 - smooth(inv(t, 6.2, 6.6)))
        P["jaw"] = 0.1 + 0.6 * snap
        P["shake"] = 0.5
        if t > 6.2:
            back = smooth(inv(t, 6.2, 7.2))
            P["x"] -= 200 * back
            P["neck_up"] = -0.15 + 0.5 * back
            P["jaw"] = 0.8 * back
    return P


def boulders(c, t, t0):
    """Ceiling collapse: boulders fall and pile up inside the tunnel."""
    if t < t0:
        return
    r = Rng(44)
    for i in range(16):
        x = ARCH0 + 140 + r.u(0, 520)
        d = r.u(0, 0.5)
        age = max(0.0, t - t0 - d)
        rr = r.u(40, 95)
        y_end = GY - rr * 0.8 - (i % 4) * 50
        y = min(CEIL + 40 + 0.5 * 2200 * age * age, y_end)
        c.drawPath(blob(x, y, rr, 900 + i, 8, 0.2, 0.85), paint(shade("#6e624f", r.u(-0.2, 0.1))))
        c.drawPath(blob(x - rr * 0.2, y - rr * 0.25, rr * 0.5, 950 + i, 7, 0.25, 0.8), paint("#9a8b70", 0.5))


def shot_arch(c, t):
    p = stick(t)
    P = rex(t)
    cam = Cam(lerp(1300, ARCH0 + 200, smooth(inv(t, 0.0, 2.6))), 640, 0.85)
    if t > 2.3:
        cam.shake(t, 14 * math.exp(-(t - 2.4) * 2) + 5)
    PH.forest_world(c, cam, t, PAL, GY, seed=61, sun=(1600, 120), rays=0.1, density=0.5, ferns=False)
    with cam.view(c, 1.0):
        REX.draw(c, P, light=PAL["light"], light_a=0.35, haze=PAL["haze"], haze_a=0.04)
        rock_mass(c, t)
        if p is not None and p.x < ARCH0 - 60:
            sm.draw(c, p, rim=PAL["light"], rim_a=0.3, rim_dir=(0.8, -0.6), shadow_y=GY + 1)
        if t > 2.4:
            for k in range(4):
                fx.burst(c, t, 2.45 + k * 0.4, ARCH0 - 60, CEIL + 30, 8, 30 + k, speed=(40, 160), ang=(1.0, 2.2), grav=1500,
                         life=(0.5, 1.0), size=(3, 6), col=(0.5, 0.45, 0.36))
            fx.dust(c, t, 2.45, ARCH0 - 100, CEIL + 60, scale=1.4, col=(0.6, 0.55, 0.45), a=0.45, n=8, seed=9)


def shot_tunnel(c, t):
    """Inside the tunnel: dark rock, light ahead, the snapping head behind."""
    p = stick(t)
    P = rex(t)
    cam = Cam(lerp(ARCH0 + 520, p.x + 160, smooth(inv(t, 3.4, 6.2))), 720, lerp(1.0, 1.35, smooth(inv(t, 3.4, 6.2))))
    crack = smooth(inv(t, 5.3, 6.0))
    cs = 4 + 6 * crack
    if t > 6.0:
        cs += 22 * math.exp(-(t - 6.0) * 1.6)
    cam.shake(t, cs)
    c.drawRect(skia.Rect(-10, -10, W + 10, H + 10), paint("#0d0a07"))
    with cam.view(c, 1.0):
        # tunnel walls lit from the exit
        c.drawRect(skia.Rect(ARCH0 - 1000, CEIL - 800, ARCH1 + 1500, GY + 600), paint("#1a140e"))
        glow(c, ARCH1 + 120, GY - 120, 900, (1.0, 0.85, 0.6), 0.55)
        c.drawRect(skia.Rect(ARCH1 + 60, CEIL, ARCH1 + 1600, GY), paint(shader=lin((ARCH1, 0), (ARCH1 + 400, 0),
                                                                                [(0, (1.0, 0.85, 0.6), 0.0), (1, (1.0, 0.9, 0.7), 0.9)])))
        c.drawRect(skia.Rect(ARCH0 - 1000, GY, ARCH1 + 1500, GY + 600), paint("#2a2117"))
        c.drawRect(skia.Rect(ARCH0 - 1000, CEIL - 800, ARCH1 + 1500, CEIL), paint("#241b13"))
        r = Rng(3)
        for k in range(70):
            x = r.u(ARCH0 - 800, ARCH1 + 200)
            c.drawPath(blob(x, CEIL - r.u(0, 30), r.u(20, 60), k, 7, 0.3, 0.5), paint("#2e241a"))
        # the T-Rex head jammed in the entrance, snapping
        if t < 7.0:
            with layer(c, a=1.0):
                REX.draw(c, P, light=(1, 0.9, 0.7), light_a=0.15, dark=0.55, shadow=False)
        # falling pebbles, then the collapse
        for k in range(10):
            fx.burst(c, t, 3.4 + k * 0.25, ARCH0 + 300 + k * 90, CEIL, 3, 60 + k, speed=(10, 60), ang=(1.4, 1.8), grav=1800,
                     life=(0.4, 0.8), size=(2, 4), col=(0.45, 0.38, 0.3))
        if crack > 0:
            for k in range(5):
                x0 = lerp(ARCH0 + 250, ARCH0 + 700, k / 4)
                c.drawPath(poly([(x0, CEIL), (x0 + 25, CEIL - 60), (x0 - 10, CEIL - 120)], closed=False),
                           paint((0.75, 0.6, 0.4), 0.3 * crack, stroke=3))
        boulders(c, t, 6.0)
        if p is not None:
            sm.draw(c, p, rim=(1.0, 0.85, 0.6), rim_a=0.6, rim_dir=(1, -0.3))
        if t > 6.0:
            fx.dust(c, t, 6.05, ARCH0 + 420, GY - 120, scale=4.0, col=(0.42, 0.36, 0.28), a=0.75, n=16, seed=13, spread=1.6,
                    rise=0.1, dur=3.0, dirx=1.2)
            fx.dust(c, t, 6.3, ARCH0 + 700, GY - 60, scale=3.0, col=(0.5, 0.42, 0.32), a=0.6, n=12, seed=14, spread=1.4,
                    rise=0.05, dur=2.6, dirx=1.6)


# ----------------------------------------------------------------- D/E: the climb in golden light
SLOPE0 = 5000


CLIFF_TOP = 400


def slope_y(x):
    return GY - min(max(0.0, x - SLOPE0), CLIFF_TOP) * 0.55


def climb_pose(t):
    mv = sm.Mover(8.8, 15.0, SLOPE0 + 100,
                  lambda tt: (120 * (1 - smooth(inv(tt, 10.7, 11.0))) + 105 * smooth(inv(tt, 11.8, 12.2))) * (1 - smooth(inv(tt, 13.0, 13.6))),
                  lambda tt: "tired" if tt > 10.0 else "climb", S)
    x = mv.x(t)
    p = sm.gait(mv.phase(t), x, slope_y(x), S, 1, "tired" if t > 10.0 else "climb", ground=slope_y)
    p.face, p.eye = 1.0, 0.8
    if 10.9 < t < 12.0:
        rest = sm.Pose(x=x, y=0, s=S, f=1, torso=1.0, head=0.2, sh_n=0.7, el_n=0.5, sh_f=0.5, el_f=0.6,
                       hp_n=0.5, kn_n=0.6, hp_f=-0.1, kn_f=0.4, face=1.0, eye=0.6)
        sm.settle(rest, slope_y(x) + 6)
        b = 0.5 + 0.5 * math.sin(t * TAU * 1.2)
        rest.breath = 2 * b
        rest.torso += 0.05 * b
        k = smooth(inv(t, 10.9, 11.2)) * (1 - smooth(inv(t, 11.7, 12.0)))
        p = sm.blend(p, rest, k)
    if t > 13.0:
        top = sm.stand(x=x, y=0, s=S, f=1, face=1.0, head=-0.05, eye=1.0, torso=0.15)
        sm.settle(top, slope_y(x))
        top = sm.breathe(top, t, 0.8, 2.0)
        p = sm.blend(p, top, smooth(inv(t, 13.0, 13.6)))
    return p


def shot_climb(c, t):
    p = climb_pose(t)
    pal = SUN
    u = smooth(inv(t, 12.6, 15.0))
    cam = Cam(lerp(p.x + 200, p.x + 300, u), lerp(p.y - 150, p.y - 230, u), lerp(1.3, 1.0, u))
    PH.sky(c, cam, t, pal, sun=(1500, 520), sun_r=60, cloud_seed=19, cloud_y=260)
    PH.far_mountains(c, cam, t, pal, y=520, p=0.06, seed=71, h=380, key="s12")
    N.godrays(c, *cam.to_screen(1500, 520, 0.02), t, col=pal["light"], a=0.16, n=10, spread=2.0, base_ang=3.3, length=2600)
    with cam.view(c, 1.0):
        pts = [(SLOPE0 - 800, GY), (SLOPE0, GY)]
        for k in range(1, 22):
            x = SLOPE0 + k * 80
            pts.append((x, slope_y(x) + (6 * math.sin(k * 1.7) if x < SLOPE0 + CLIFF_TOP else 0)))
        top_x = pts[-1][0]
        pts += [(top_x + 200, pts[-1][1] + 6), (top_x + 260, pts[-1][1] + 60), (top_x + 300, 2600), (SLOPE0 - 800, 2600)]
        c.drawPath(poly(pts), paint(shader=lin((0, slope_y(SLOPE0 + 2000)), (0, GY + 300), [(0, "#a07a5a"), (1, "#4a3628")])))
        c.drawPath(poly(pts[:-3], closed=False), paint((1.0, 0.8, 0.5), 0.6, stroke=8, blur=4))
        for k in range(9):
            x = SLOPE0 + 60 + k * 190
            N.rock(c, x, slope_y(x) + 10, 60 + 40 * hash01(k, 2), 30 + 20 * hash01(k, 3), 300 + k, col="#7a5e48",
                   light=(1.0, 0.8, 0.5), light_a=0.6)
            if k % 3 == 0:
                N.grass(c, x + 40, x + 100, slope_y(x + 70) + 4, t, seed=k, h=22, density=0.5, col="#8a8a3a", col2="#b0a050")
        sm.draw(c, p, rim=(1.0, 0.8, 0.45), rim_a=0.55, rim_dir=(-1, -0.4), shadow_y=slope_y(p.x) + 1)


def render(c, t):
    if t < 3.2:
        with layer(c, cf=grade_cf(sat=1.0, contrast=1.1, tint=(1.04, 1.0, 0.92))):
            shot_arch(c, t)
    elif t < 8.8:
        with layer(c, cf=grade_cf(sat=0.95, contrast=1.15, tint=(1.05, 0.98, 0.9))):
            shot_tunnel(c, t)
    else:
        with layer(c, cf=grade_cf(sat=1.08, contrast=1.05, tint=(1.06, 0.98, 0.9))):
            shot_climb(c, t)
