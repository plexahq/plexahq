"""Scene 6 - The First Dinosaurs. A walk through the forest, a rustling bush, a
small curious dinosaur, then the ground starts to shake."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_out, ease_in, grade_cf, seg)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import prehistoric as PH

DURATION = 16.0
CUES = {"walk": 0.0, "rustle": 4.0, "pop": 6.0, "jump_back": 6.15, "chirp": 8.6, "run_off": 10.0, "relax": 10.8,
        "thump1": 11.7, "thump2": 12.8, "birds": 13.0, "thump3": 13.9, "turn": 14.4, "thump4": 15.0}
THUMPS = [11.7, 12.8, 13.9, 15.0]

PAL = PH.P("forest")
GY = 900
S = 1.8
BUSH_X = 2150
SMALL = D.Theropod(D.SMALL)

WALK = sm.Mover(0.0, 16.0, 900, lambda t: 150 * (1 - smooth(inv(t, 4.2, 5.2))) - 120 * (6.15 <= t < 6.55), "walk", S)


def stick(t):
    x = WALK.x(t)
    if t < 5.2:
        p = sm.gait(WALK.phase(t), x, GY, S, 1, "walk")
        p.face = 1.0
        p.head = 0.02 + 0.1 * smooth(inv(t, 4.0, 4.6))
        return p
    stop = sm.stand(x=x, y=0, s=S, f=1, torso=-0.08, face=1.0, eye_s=1.2)
    sm.settle(stop, GY)
    if t < 6.15:
        return sm.blend(sm.gait(WALK.phase(t), x, GY, S, 1, "walk"), stop, smooth(inv(t, 5.0, 5.4)))
    if t < 7.0:
        # startled hop backwards
        u = inv(t, 6.15, 6.75)
        p = sm.Pose(x=x, y=0, s=S, f=1, torso=-0.35, head=-0.3, sh_n=1.9, el_n=0.9, sh_f=1.6, el_f=1.1,
                    hp_n=0.4, kn_n=0.9, hp_f=-0.1, kn_f=0.5, face=1.0, eye_s=1.6)
        sm.settle(p, GY)
        p.y -= math.sin(math.pi * u) * 40
        return sm.blend(p, stop, smooth(inv(t, 6.75, 7.0)))
    if t < 10.4:
        p = sm.stand(x=x, y=0, s=S, f=1, torso=-0.06, face=1.0, eye_s=1.3,
                     head=0.35 * smooth(inv(t, 7.6, 8.1)) * (1 - smooth(inv(t, 9.0, 9.5))), sh_n=0.4, el_n=0.9, sh_f=0.3, el_f=1.0)
        sm.settle(p, GY)
        p.look = 0.4
        return sm.breathe(p, t, 0.5, 1.0)
    if t < 11.6:
        r = smooth(inv(t, 10.6, 11.2))
        p = sm.stand(x=x, y=0, s=S, f=1, torso=0.05 * r, head=0.15 * r, face=1.0, eye_s=1.0, eye=1 - 0.7 * r)
        sm.settle(p, GY)
        p.breath = 1.0 - r
        return p
    # ground shakes: tense, then the slow head turn back
    turn = smooth(inv(t, 14.4, 15.6))
    p = sm.stand(x=x, y=0, s=S, f=1, torso=-0.04, face=lerp(1.0, -0.9, turn), head=-0.12 * turn, eye_s=1.0 + 0.5 * turn,
                 sh_n=0.25, sh_f=-0.05)
    p.look = -0.6 * turn
    sm.settle(p, GY)
    return sm.tremble(p, t, 0.6 * smooth(inv(t, 11.8, 12.4)))


def small_dino(t):
    """Small curious theropod: emerges from the bush, studies the stickman, darts off."""
    if t < 6.0:
        return None
    emerge = ease_out(inv(t, 6.0, 6.35))
    x = lerp(BUSH_X + 60, BUSH_X - 230, emerge)
    P = dict(x=x, gy=GY, s=2.1, f=-1, t=t, neck_up=0.55, head_pitch=0.1)
    if t < 10.0:
        tilt = math.sin(t * 2.2) * 0.25 * smooth(inv(t, 6.8, 7.3))
        P["head_pitch"] = 0.1 + tilt + 0.15 * noise(t * 6, 2)
        P["neck_up"] = 0.55 + 0.1 * math.sin(t * 1.7)
        P["blink"] = 1.0 if (7.9 < t < 8.05 or 9.3 < t < 9.42) else 0.0
        if 8.55 < t < 8.85:
            P["jaw"] = 0.35 * math.sin(math.pi * inv(t, 8.55, 8.85))
        return P
    run = D.gait_of(D.SMALL, "run")
    dt = t - 10.0
    v = 900 * smooth(inv(t, 10.0, 10.25))
    P.update(f=1, gait="run", x=lerp(BUSH_X - 230, BUSH_X - 230 + 1300, min(1, dt / 1.4) ** 1.2),
             phase=dt * 3.4, neck_up=0.2, head_pitch=0.25)
    return P


def bush_shake(t):
    return smooth(inv(t, 4.0, 4.3)) * (1 - smooth(inv(t, 6.2, 6.6))) + 0.6 * (10.0 < t < 10.4)


def thump_amount(t):
    a = 0.0
    for k, tt in enumerate(THUMPS):
        if t >= tt:
            a = max(a, (0.5 + 0.12 * k) * math.exp(-(t - tt) * 5))
    return a


def shot_track(c, t):
    cam = Cam()
    cam.x = WALK.x(t) + 280
    cam.y = 700
    cam.zoom = 1.5
    PH.forest_world(c, cam, t, PAL, GY, seed=6, sun=(350, 40))
    with cam.view(c, 1.0):
        P = small_dino(t)
        if P is not None and P["x"] > BUSH_X - 300 - 2000:
            SMALL.draw(c, P, light=PAL["light"], light_a=0.3, shadow_a=0.25)
        N.bush(c, BUSH_X, GY + 10, 150, 31, pal=PAL["forest"], shake=bush_shake(t), t=t)
        N.bush(c, BUSH_X + 160, GY + 14, 110, 32, pal=PAL["forest"], shake=bush_shake(t) * 0.6, t=t)
        if 4.0 < t < 6.6:
            fx.leaves(c, t, 4.1, BUSH_X, GY - 120, 6, 3, spread=120, up=60, dur=2.5, size=6)
        p = stick(t)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.3, rim_dir=(-0.6, -0.8), shadow_y=GY + 1)
    PH.forest_foreground(c, cam, t, PAL, GY, seed=4)


def shot_ground(c, t):
    """Close on the forest floor: pebbles hop, a puddle ripples with every thump."""
    cam = Cam(960, 700, 2.4)
    cam.shake(t, 12 * thump_amount(t))
    with cam.view(c, 0.3):
        with layer(c, blur=10):
            PH.forest_world(c, Cam(960, 600, 1.0), t, PAL, 900, seed=7, rays=0.0, ferns=False, trunks=False)
    with cam.view(c, 1.0):
        N.ground_fill(c, -400, 2400, 760, PAL["ground"][0], PAL["ground"][1], 600)
        # puddle
        ellipse(c, 1080, 790, 210, 26, paint(shader=lin((0, 764), (0, 816), [(0, "#9cc4cf"), (1, "#3d6f7c")])))
        for tt in THUMPS:
            fx.ripple(c, t, tt, 1080, 790, scale=1.2, a=0.7, n=3, dur=1.6, flat=0.12)
        N.grass(c, 500, 1500, 764, t, seed=3, h=30, density=0.5, col=PAL["grass"][0], col2=PAL["grass"][1])
        r = Rng(5)
        for i in range(9):
            x = 640 + i * 70 + r.u(-20, 20)
            hop = 0.0
            for tt in THUMPS:
                if t >= tt:
                    age = t - tt - 0.03 * i
                    if 0 < age < 0.35:
                        hop = max(hop, math.sin(math.pi * age / 0.35) * (14 + 10 * hash01(i, 2)))
            N.rock(c, x, 768 - hop, 22 + 18 * hash01(i, 3), 12 + 10 * hash01(i, 4), i + 40, col=PAL["rock"][0], light=PAL["light"])
        N.fern(c, 1450, 770, 200, 12, t, wind=0.06, col=PAL["forest"][1], col2=PAL["forest"][2], shake=3 * thump_amount(t))


def shot_canopy(c, t):
    cam = Cam(960, 560, 0.85)
    cam.shake(t, 8 * thump_amount(t))
    with cam.view(c, 0.02):
        N.sky(c, PAL["sky"], -200, 1000)
    N.godrays(c, 300, -60, t, col=PAL["light"], a=0.14, n=8, base_ang=1.2)
    with cam.view(c, 1.0):
        for i, (x, h) in enumerate(((150, 1500), (620, 1700), (1100, 1450), (1600, 1650), (1950, 1500))):
            N.tree(c, "broad", i + 11, x, 1700, h, t, wind=0.02 + 0.06 * thump_amount(t),
                   haze=PAL["haze"], haze_a=0.08 + 0.08 * (i % 2))
        # birds burst from the crowns
        for i in range(34):
            h = [hash01(i, 33, k) for k in range(5)]
            t0 = 13.0 + h[0] * 0.5
            age = t - t0
            if age < 0:
                continue
            sx, sy = 200 + h[1] * 1600, 420 + h[2] * 300
            vx, vy = -250 + 500 * h[3], -380 - 200 * h[4]
            x = sx + vx * age
            y = sy + vy * age + 30 * math.sin(age * 4 + i)
            D.bird(c, x, y, 2.4 + 1.2 * h[4], age * (5 + 2 * h[3]), col="#1d2220")
        fx.leaves(c, t, 13.0, 960, 500, 30, 9, spread=600, up=100, dur=3.0, size=9)


def shot_turn(c, t):
    p = stick(t)
    cam = Cam(p.x + 30, p.y - 70, 3.2)
    cam.shake(t, 6 * thump_amount(t))
    with cam.view(c, 0.25):
        with layer(c, blur=10):
            PH.forest_world(c, Cam(p.x - 300, 560, 1.0), t, PAL, GY, seed=6, sun=(350, 40), rays=0.15)
    with cam.view(c, 1.0):
        sm.draw(c, p, rim=PAL["light"], rim_a=0.35, rim_dir=(-0.6, -0.8))


def render(c, t):
    with layer(c, cf=grade_cf(sat=1.05, contrast=1.06, tint=(1.0, 1.02, 0.96))):
        if t < 11.6:
            shot_track(c, t)
        elif t < 12.9:
            shot_ground(c, t)
        elif t < 14.3:
            shot_canopy(c, t)
        else:
            shot_turn(c, t)
