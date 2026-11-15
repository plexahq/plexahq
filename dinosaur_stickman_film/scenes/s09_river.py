"""Scene 9 - The River Escape. A dive, a desperate swim, the T-Rex wading in, a
crawl onto the far bank and a look back."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_out, ease_in, grade_cf, seg, taper)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import prehistoric as PH

DURATION = 21.5
CUES = {"arrive": 0.0, "skid": 1.0, "look_back": 2.0, "roar_off": 2.2, "jump": 3.3, "splash": 4.0, "surface": 4.7,
        "swim": 5.0, "rex_bank": 7.4, "roar": 7.8, "wade": 10.0, "wade_splash": 10.4, "climb": 13.0, "collapse": 15.0,
        "look": 16.6, "roar2": 16.8, "get_up": 18.5, "run": 19.5}

PAL = PH.P("forest")
REX = D.Theropod(D.REX)
RS = 1.5
GY = 880
WY = 905
BANK_L, BANK_R = 1000, 2620
S = 1.8


def ground_y(x):
    if x <= BANK_L:
        return GY
    if x >= BANK_R:
        return GY
    return WY + 400


def swim_x(t):
    if t < 4.7:
        return 1300
    if t < 10.0:
        return 1300 + 120 * (t - 4.7)
    if t < 12.8:
        return 1300 + 120 * 5.3 + 190 * (t - 10.0)
    return 1300 + 636 + 190 * 2.8


def swim_pose(t, x, speed=1.0):
    ph = (t - 4.7) * (1.1 + 0.6 * speed)
    a = ph * TAU
    p = sm.Pose(x=x, y=WY + 10, s=S, f=1, rot=math.pi / 2 - 0.25, torso=0.0, head=-0.5,
                sh_n=a, el_n=0.3 + 0.3 * math.sin(a), sh_f=a + math.pi, el_f=0.3 + 0.3 * math.sin(a + math.pi),
                hp_n=0.25 * math.sin(a * 2), kn_n=0.2, hp_f=-0.25 * math.sin(a * 2), kn_f=0.2,
                face=1.0 if math.sin(a) > -0.6 else -0.3, eye_s=1.4)
    return p


def stick(t):
    if t < 3.0:
        # decelerate to stop at the edge
        if t < 1.4:
            u = t / 1.4
            x = lerp(250, 975, 1 - (1 - u) ** 2)
            p = sm.gait(x / 40.0 * 0.34, x, GY, S, 1, "sprint")
            if t > 0.9:
                stop = sm.Pose(x=x, y=0, s=S, f=1, torso=-0.35, head=-0.1, sh_n=1.8, el_n=0.5, sh_f=1.4, el_f=0.6,
                               hp_n=0.45, kn_n=0.3, hp_f=-0.2, kn_f=0.4, face=1.0, eye_s=1.6)
                sm.settle(stop, GY)
                p = sm.blend(p, stop, smooth(inv(t, 0.9, 1.3)))
            p.face, p.eye_s = 1.0, 1.6
            return p
        wm = 1 - smooth(inv(t, 1.9, 2.2))
        look = smooth(inv(t, 2.0, 2.3)) * (1 - smooth(inv(t, 2.75, 2.95)))
        p = sm.Pose(x=980, y=0, s=S, f=1, torso=0.15 * wm + 0.05 - 0.1 * look, head=0.1 * wm, face=lerp(1.0, -1.0, look),
                    sh_n=1.8 + 1.2 * math.sin(t * 16) * wm, el_n=0.4, sh_f=1.6 + 1.2 * math.sin(t * 16 + 2) * wm, el_f=0.4,
                    hp_n=0.12, kn_n=0.08, hp_f=-0.1, kn_f=0.06, eye_s=1.6)
        p.look = -look
        sm.settle(p, GY)
        return sm.tremble(p, t, 0.8)
    if t < 4.0:
        if t < 3.3:
            p = sm.Pose(x=980, y=0, s=S, f=1, torso=0.6, head=-0.2, sh_n=-1.0, el_n=0.3, sh_f=-1.1, el_f=0.3,
                        hp_n=0.9, kn_n=1.4, hp_f=0.7, kn_f=1.3, face=1.0, eye_s=1.5)
            return sm.settle(p, GY)
        u = inv(t, 3.3, 4.0)
        x = lerp(980, 1250, u)
        y = lerp(GY - 80, WY + 10, u) - math.sin(math.pi * u) * 160
        return sm.Pose(x=x, y=y, s=S, f=1, rot=lerp(0.3, 2.0, u), torso=0.2, head=-0.3, sh_n=2.9, el_n=0.1, sh_f=2.8, el_f=0.1,
                       hp_n=0.0, kn_n=0.1, hp_f=-0.2, kn_f=0.2, face=1.0, eye_s=1.5)
    if t < 12.8:
        return swim_pose(t, swim_x(t), 1.0 if t > 10 else 0.0)
    if t < 15.0:
        x = BANK_R - 40
        hand = (BANK_R + 30, GY - 2)
        if t < 13.6:
            p = sm.Pose(x=x - 20, y=WY + 25 - 30 * smooth(inv(t, 12.8, 13.6)), s=S, f=1, torso=0.15, head=-0.1, face=1.0, eye_s=1.4,
                        hp_n=0.2, kn_n=0.6, hp_f=-0.1, kn_f=0.5)
            sm.arm_ik(p, "n", hand)
            sm.arm_ik(p, "f", (hand[0] + 20, hand[1]))
            return p
        if t < 14.3:
            u = smooth(inv(t, 13.6, 14.3))
            p = sm.Pose(x=lerp(x - 20, BANK_R + 40, u), y=lerp(WY - 5, GY - 55, u), s=S, f=1, torso=lerp(0.4, 0.9, u), head=-0.3,
                        face=1.0, eye_s=1.3, hp_n=lerp(1.4, 1.2, u), kn_n=lerp(2.2, 2.0, u), hp_f=-0.2, kn_f=0.6)
            sm.arm_ik(p, "n", (BANK_R + 110, GY - 2))
            sm.arm_ik(p, "f", (BANK_R + 130, GY - 2))
            return p
        u = smooth(inv(t, 14.3, 15.0))
        p = sm.stand(x=BANK_R + 60 + 100 * u, y=0, s=S, f=1, torso=0.5, head=0.3, sh_n=0.1, el_n=0.2, sh_f=-0.1, el_f=0.2,
                     face=1.0, eye=0.7)
        sm.settle(p, GY)
        return p
    X = BANK_R + 220
    if t < 18.5:
        fall = smooth(inv(t, 15.0, 15.6))
        lie = sm.Pose(x=X, y=GY - 8, s=S, f=-1, rot=-math.pi / 2, head=-0.1, sh_n=2.6, el_n=0.3, sh_f=2.4, el_f=0.4,
                      hp_n=0.25, kn_n=0.6, hp_f=-0.1, kn_f=0.2, face=0.6, eye=0.4)
        stand = sm.stand(x=X - 40, y=0, s=S, f=1, torso=0.5, head=0.3, face=1.0, eye=0.7)
        sm.settle(stand, GY)
        if t < 15.6:
            return sm.blend(stand, lie, fall)
        b = 0.5 + 0.5 * math.sin(t * TAU * 0.9)
        lie.breath = b * 2
        lie.y -= 3 * b
        look = smooth(inv(t, 16.4, 16.9))
        lie.head = -0.1 - 0.7 * look
        lie.face = lerp(0.6, 1.0, look)
        lie.eye = lerp(0.4, 1.0, look)
        lie.eye_s = 1.0 + 0.4 * look
        lie.look = 0.6 * look
        return lie
    up = smooth(inv(t, 18.5, 19.4))
    if t < 19.5:
        kneel = sm.Pose(x=X + 20, y=0, s=S, f=1, torso=0.6, head=-0.1, sh_n=0.6, el_n=0.6, sh_f=0.3, el_f=0.5,
                        hp_n=1.0, kn_n=1.7, hp_f=0.1, kn_f=1.8, face=1.0, eye_s=1.3)
        sm.settle(kneel, GY, parts=("ft_n", "ft_f", "kn_f"))
        lie = sm.Pose(x=X, y=GY - 8, s=S, f=-1, rot=-math.pi / 2, head=-0.8, sh_n=2.6, el_n=0.3, sh_f=2.4, el_f=0.4,
                      hp_n=0.25, kn_n=0.6, hp_f=-0.1, kn_f=0.2, face=1.0, eye=1.0)
        return sm.blend(lie, kneel, up)
    run = sm.Mover(19.5, 22.0, X + 20, lambda tt: 650 * smooth(inv(tt, 19.5, 19.9)), "sprint", S)
    p = sm.gait(run.phase(t), run.x(t), GY, S, 1, "sprint")
    p.face, p.eye_s = 1.0, 1.5
    return p


def rex(t):
    if t < 6.6:
        return None
    if t < 7.6:
        u = inv(t, 6.6, 7.6)
        x = lerp(-700, 520, 1 - (1 - u) ** 2)
        return dict(x=x, gy=GY, s=RS, f=1, t=t, gait="run", phase=x * 0.4 / (250 * RS), neck_up=0.05, head_pitch=0.2, jaw=0.4)
    P = dict(x=520, gy=GY, s=RS, f=1, t=t, neck_up=0.2, head_pitch=0.2)
    if t < 10.0:
        r = smooth(inv(t, 7.8, 8.1)) * (1 - smooth(inv(t, 9.2, 9.6)))
        P.update(neck_up=0.2 + 0.25 * r, head_pitch=0.2 - 0.25 * r, jaw=0.8 * r, shake=r, pitch=-0.05 * r)
        return P
    # wade in
    wv = 150.0
    tt = min(t, 15.5)
    x = 520 + wv * (tt - 10.0)
    walk = D.REX["walk"]
    P.update(x=x, gait="walk" if t < 15.5 else None, phase=(x - 520) * walk["duty"] / (walk["stride"] * RS), neck_up=0.15, jaw=0.2,
             gy=riverbed(x + 150))
    if t >= 15.5:
        P["stance"] = 0.2
    if t >= 16.6:
        r = smooth(inv(t, 16.8, 17.1)) * (1 - smooth(inv(t, 17.9, 18.3)))
        P.update(neck_up=0.2 + 0.3 * r, head_pitch=0.2 - 0.3 * r, jaw=0.8 * r, shake=r)
    if t >= 18.4:
        back = smooth(inv(t, 18.4, 21.5))
        P["x"] = x - 260 * back
        P["gy"] = riverbed(P["x"] + 150)
        P["gait"] = "walk"
        P["phase"] = -(260 * back) * 0.62 / (150 * RS)
    return P


def environment(c, cam, t):
    PH.sky(c, cam, t, PAL, sun=(1700, 120), cloud_seed=7, cloud_y=160)
    PH.far_mountains(c, cam, t, PAL, y=380, p=0.06, seed=31, h=380, key="s9")
    PH.forest_band(c, cam, PAL, 760, 0.2, seed=32, haze_a=0.45, tall=1.0)
    with cam.view(c, 0.25):
        N.water_band(c, -2000, 4000, 760, 800, t, top="#a9d3dc", bot=PAL["water"][0], flow=10, density=0.4)
    PH.forest_band(c, cam, PAL, 830, 0.4, seed=33, haze_a=0.3, tall=1.0)
    with cam.view(c, 0.55):
        N.water_band(c, -2000, 4000, 820, 900, t, top="#93c7d3", bot=PAL["water"][0], flow=18, density=0.5)
    with cam.view(c, 0.7):
        for i, x in enumerate((-600, -200, 300, 600)):
            N.tree(c, "broad" if i % 2 else "arauc", 60 + i, x, GY + 20, 1000 + 200 * hash01(i, 6), t, wind=0.015,
                   haze=PAL["haze"], haze_a=0.2, sway_extra=0.05 * (1.5 < t < 3.5) * math.sin(t * 12 + i))
        for i, x in enumerate((2900, 3300, 3800, 4200)):
            N.tree(c, "tfern" if i % 2 else "broad", 70 + i, x, GY + 20, 900 + 200 * hash01(i, 7), t, wind=0.015,
                   haze=PAL["haze"], haze_a=0.2)


def riverbed(x):
    return GY + 260 * smooth(inv(x, BANK_L - 150, BANK_L + 700))


def water_back(c, t):
    c.drawRect(skia.Rect(BANK_L + 60, WY, BANK_R - 60, WY + 900), paint(shader=lin((0, WY), (0, WY + 420),
                                                                                 [(0, "#7cc0d2"), (0.5, "#3f8aa2"), (1, "#1b4f63")])))


def water_front(c, t):
    """Translucent water over anything submerged, with a moving surface."""
    pts = []
    x0, x1 = BANK_L + 40, BANK_R - 40
    for i in range(0, 61):
        x = lerp(x0, x1, i / 60)
        y = WY + 4 * math.sin(x * 0.012 + t * 2.2) + 3 * math.sin(x * 0.031 - t * 3.1)
        pts.append((x, y))
    path = poly(pts + [(x1, WY + 900), (x0, WY + 900)])
    c.drawPath(path, paint(shader=lin((0, WY), (0, WY + 260), [(0, "#6fb6c9", 0.62), (0.4, "#3f8aa2", 0.85), (1, "#1b4f63", 0.97)])))
    c.drawPath(poly(pts, closed=False), paint((0.9, 0.97, 1.0), 0.65, stroke=3))
    N.water_band(c, x0, x1, WY + 8, WY + 420, t, top="#5fb0c8", bot="#0f3444", a=1.0, flow=-50,
                 sparkle_a=0.55, density=1.4, fill=False)


def banks(c, t):
    # left bank with a muddy slope into the water
    c.drawPath(poly([(-3000, GY), (BANK_L - 20, GY), (BANK_L + 70, WY + 60), (BANK_L + 70, WY + 900), (-3000, WY + 900)]),
               paint(shader=lin((0, GY), (0, GY + 400), [(0, PAL["ground"][0]), (1, PAL["ground"][1])])))
    c.drawPath(poly([(BANK_R + 20, GY), (6000, GY), (6000, WY + 900), (BANK_R - 70, WY + 900), (BANK_R - 70, WY + 60)]),
               paint(shader=lin((0, GY), (0, GY + 400), [(0, PAL["ground"][0]), (1, PAL["ground"][1])])))
    N.grass(c, -3000, BANK_L - 10, GY + 4, t, seed=91, h=28, density=0.35, col=PAL["grass"][0], col2=PAL["grass"][1])
    N.grass(c, BANK_R + 20, 6000, GY + 4, t, seed=92, h=28, density=0.35, col=PAL["grass"][0], col2=PAL["grass"][1])
    for i, x in enumerate((BANK_L - 40, BANK_R + 40)):
        N.rock(c, x, GY + 24, 120, 50, 80 + i, col=PAL["rock"][0], light=PAL["light"], moss=PAL["forest"][1])
    for i, x in enumerate((-400, 200, 700, BANK_R + 400, BANK_R + 900, BANK_R + 1500)):
        N.fern(c, x, GY + 6, 160, 300 + i, t, wind=0.07, col=PAL["forest"][1], col2=PAL["forest"][2])


def swim_splashes(c, t):
    if 4.7 <= t < 12.8:
        k0 = int((t - 4.7) * 2.6)
        for k in range(max(0, k0 - 4), k0 + 1):
            tk = 4.7 + k / 2.6
            x = swim_x(tk) + 50
            fx.burst(c, t, tk, x, WY - 2, 14, 300 + k, speed=(120, 320), ang=(-2.6, -0.5), grav=1300, life=(0.3, 0.7),
                     size=(2, 4), col=(0.9, 0.97, 1.0), a=0.9)
            fx.ripple(c, t, tk, x, WY + 2, scale=0.8, a=0.5, n=1, dur=1.2, flat=0.1)


def rex_splashes(c, t, P):
    if P is None or t < 10.0:
        return
    walk = D.REX["walk"]
    period = 1.0 / (150.0 * walk["duty"] / (walk["stride"] * RS))
    k0 = int((t - 10.0) / (period / 2))
    for k in range(max(0, k0 - 3), k0 + 1):
        tk = 10.0 + k * period / 2
        if tk > 15.5:
            continue
        x = 520 + 150 * (tk - 10.0) + 200
        if x < BANK_L + 60:
            continue
        fx.splash(c, t, tk, x, WY, scale=0.6, seed=400 + k, big=False)


def render(c, t):
    p = stick(t)
    P = rex(t)
    cam = Cam()
    if t < 3.0:
        cam.x, cam.y, cam.zoom = keys(t, [(0, (560, 650, 1.25)), (1.4, (880, 660, 1.4)), (3.0, (900, 660, 1.45))])
    elif t < 5.0:
        cam.x, cam.y, cam.zoom = 1150, 650, 1.0
    elif t < 10.0:
        cam.x, cam.y, cam.zoom = keys(t, [(5.0, (1450, 620, 0.78)), (10.0, (1550, 620, 0.78))])
    elif t < 11.4:
        cam.x, cam.y, cam.zoom = swim_x(t) + 60, WY - 40, 2.1
    elif t < 12.0:
        cam.x, cam.y, cam.zoom = keys(t, [(11.4, (1500, 640, 0.78)), (12.0, (1560, 640, 0.78))])
    elif t < 15.0:
        cam.x, cam.y, cam.zoom = keys(t, [(12.0, (2520, 760, 1.6)), (15.0, (2640, 740, 1.55))])
    elif t < 18.5:
        cam.x, cam.y, cam.zoom = keys(t, [(15.0, (2050, 640, 0.72)), (18.5, (2100, 650, 0.75))])
    else:
        cam.x, cam.y, cam.zoom = keys(t, [(18.5, (2750, 650, 1.1)), (21.5, (3600, 650, 1.1))], fn=ease_in)
    shake = 0.0
    if 1.0 < t < 1.6:
        shake += 4
    if 7.8 < t < 9.4 or 16.8 < t < 18.0:
        shake += 7
    if P is not None and 6.6 < t < 7.8:
        shake += 6
    cam.shake(t, shake)
    with layer(c, cf=grade_cf(sat=1.0, contrast=1.08, tint=(0.97, 1.0, 1.0))):
        environment(c, cam, t)
        with cam.view(c, 1.0):
            water_back(c, t)
            banks(c, t)
            if P is not None:
                REX.draw(c, P, light=PAL["light"], light_a=0.3, haze=PAL["haze"], haze_a=0.05, shadow=P["x"] < BANK_L - 300)
            sm.draw(c, p, rim=PAL["light"], rim_a=0.3, rim_dir=(-0.6, -0.8), shadow_y=GY + 1 if p.x < BANK_L or p.x > BANK_R else None)
            water_front(c, t)
            if 0.9 < t < 2.0:
                fx.dust(c, t, 1.0, 960, GY, scale=0.8, col=(0.55, 0.48, 0.36), a=0.5, n=6, seed=2, dirx=0.6)
            fx.splash(c, t, 4.0, 1250, WY, scale=1.3, seed=7)
            swim_splashes(c, t)
            rex_splashes(c, t, P)
            if t > 10.0:
                fx.splash(c, t, 13.0, 520 + 150 * 3.0 + 220, WY, scale=1.2, seed=9)
            if 12.8 < t < 14.5:
                fx.burst(c, t, 13.0, BANK_R - 20, WY, 30, 501, speed=(80, 260), ang=(-2.8, -0.3), grav=1200, life=(0.4, 1.0),
                         size=(2, 4), col=(0.9, 0.97, 1.0), spawn=1.2)
            if 14.4 < t < 16:
                fx.burst(c, t, 14.4, p.x, p.y + 20, 24, 502, speed=(20, 80), ang=(1.2, 1.9), grav=600, life=(0.4, 1.0),
                         size=(1.5, 3), col=(0.8, 0.95, 1.0), spawn=1.0, a=0.7)
        pass
