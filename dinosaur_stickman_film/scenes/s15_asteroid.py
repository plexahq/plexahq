"""Scene 15 - The Asteroid. From space, a burning rock falls toward the young Earth.
Below, the world panics. On the cliff, the stickman steps back."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_in, grade_cf)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import vista as V
from scenes import prehistoric as PH

DURATION = 10.0
CUES = {"space": 0.0, "world": 3.5, "panic": 3.8, "cliff": 7.0, "step_back": 7.5, "face": 8.4}

EARTH = (960, 2650, 2000)


def earth(c, t):
    cx, cy, r = EARTH
    glow(c, cx, cy, r * 1.12, (0.35, 0.6, 1.0), 0.55, blend="screen")
    path = skia.Path()
    path.addCircle(cx, cy, r)
    c.drawPath(path, paint(shader=rad((cx - 300, cy - r * 0.9), r * 1.4, [(0, "#2f6fa8"), (0.6, "#173c66"), (1, "#081a30")])))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    r_ = Rng(12)
    for i in range(14):
        a = -math.pi / 2 + r_.u(-0.55, 0.55)
        d = r_.u(0.82, 1.0) * r
        x, y = cx + math.cos(a) * d + t * 6, cy + math.sin(a) * d
        c.drawPath(blob(x, y, r_.u(80, 260), r_.i(0, 999), 11, 0.35, 0.45), paint(r_.choice(["#5d7a3a", "#7a6a44", "#4a6a34"]), 0.9))
    for i in range(22):
        a = -math.pi / 2 + r_.u(-0.6, 0.6)
        d = r_.u(0.85, 1.0) * r
        x, y = cx + math.cos(a) * d + t * 10, cy + math.sin(a) * d
        c.drawPath(blob(x, y, r_.u(40, 160), r_.i(0, 999), 9, 0.4, 0.25), paint((1, 1, 1), 0.35, blur=12))
    # night side to the right
    c.drawRect(skia.Rect(cx - r, cy - r, cx + r, cy + r), paint(shader=lin((cx - 200, 0), (cx + r * 0.8, 0),
                                                                     [(0, (0, 0, 0), 0.0), (1, (0, 0.01, 0.04), 0.85)])))
    c.restore()
    c.drawCircle(cx, cy, r + 6, paint((0.5, 0.75, 1.0), 0.8, stroke=10, blur=8, blend="add"))


def shot_space(c, t):
    c.drawRect(skia.Rect(-10, -10, W + 10, H + 10), paint("#020208"))
    glow(c, 400, 300, 700, (0.25, 0.1, 0.35), 0.25)
    N.stars(c, t, seed=7, n=700, y1=H, a=1.0)
    z = 1 + 0.06 * t
    with at(c, W / 2, H / 2, 0, z):
        with at(c, -W / 2, -H / 2):
            earth(c, t)
    u = ease_in(inv(t, 0.0, 3.5))
    ax, ay = lerp(1650, 1150, u), lerp(140, 520, u)
    heat = 0.35 + 0.65 * smooth(inv(t, 1.0, 3.3))
    fx.asteroid(c, ax, ay, lerp(70, 110, u), t, a=1.0, trail_ang=-0.7, trail_len=3 + 4 * heat, heat=heat, seed=3)
    fx.ambient_motes(c, t, n=40, seed=31, col=(1, 0.6, 0.3), a=0.6 * heat, area=(ax - 300, ay - 300, ax + 400, ay + 200),
                     size=(1, 3), speed=60)


def shot_world(c, t):
    u = inv(t, 3.5, 7.0)
    cam = Cam(lerp(1000, 1080, u), lerp(520, 560, u), lerp(0.95, 1.05, u))
    cam.shake(t, 3)
    d = 0.55 + 0.3 * u

    def extra(c_, cam_):
        sx, sy = cam_.to_screen(1500 - 120 * u, 120 + 80 * u, 0.02)
        fx.asteroid(c_, sx, sy, 22 + 10 * u, t, trail_ang=-0.6, trail_len=14, heat=1.2, seed=4)
    V.panorama(c, cam, t, doom=d, herd_run=smooth(inv(t, 3.8, 4.6)), flock_n=0)
    extra(c, cam)
    # fleeing flocks
    for i in range(46):
        h = [hash01(i, 91, k) for k in range(5)]
        age = t - 3.6 - h[0] * 0.8
        if age < 0:
            continue
        x = 2100 - (300 + 500 * h[1]) * age - h[2] * 600
        y = 180 + h[3] * 420 - 30 * age + math.sin(age * 3 + i) * 10
        if i % 3 == 0:
            D.ptero(c, x, y, 0.6 + 0.4 * h[4], age * 3 + h[1], f=-1, col="#2a1612")
        else:
            D.bird(c, x, y, 1.0 + h[4], age * 6 + h[2], col="#1e100c")


def stick(t):
    back = smooth(inv(t, 7.5, 8.1))
    p = sm.stand(x=V.SIT_ROCK[0] - 60 - 50 * back, y=0, s=1.6, f=1, face=1.0, head=-0.45 + 0.1 * back, eye_s=1.6 + 0.4 * back,
                 torso=-0.12 * back, sh_n=0.3 + 0.5 * back, el_n=0.6 + 0.6 * back, sh_f=0.2 + 0.4 * back, el_f=0.7)
    if 7.5 < t < 8.1:
        k = math.sin(math.pi * inv(t, 7.5, 8.1))
        p.hp_f, p.kn_f = -0.05 - 0.3 * k, 0.05 + 0.6 * k
    sm.settle(p, V.EDGE_Y)
    p.look_y = -0.6
    return sm.tremble(p, t, 1.0 + 1.0 * smooth(inv(t, 8.4, 9.4)))


def shot_cliff(c, t):
    p = stick(t)
    J = sm.joints(p)
    u = ease_io(inv(t, 7.0, 10.0))
    cam = Cam(lerp(980, J["head"][0] + 10, u), lerp(660, J["head"][1] + 10, u), lerp(1.7, 6.5, u))
    cam.shake(t, 3 + 3 * u)
    d = 0.9
    V.panorama(c, cam, t, doom=d, herd_run=1.0, flock_n=0)
    sx, sy = cam.to_screen(1420, 220, 0.02)
    fx.asteroid(c, sx, sy, 34, t, trail_ang=-0.6, trail_len=14, heat=1.3, seed=4)
    fx.light_overlay(c, sx, sy, 1600, (1.0, 0.45, 0.15), 0.25, blend="screen")
    V.cliff_front(c, cam, t, doom=d)
    with cam.view(c, 1.0):
        sm.draw(c, p, rim=(1.0, 0.45, 0.15), rim_a=0.75, rim_dir=(0.8, -0.6), shadow_y=V.EDGE_Y)


def render(c, t):
    if t < 3.5:
        shot_space(c, t)
    elif t < 7.0:
        with layer(c, cf=grade_cf(sat=1.1, contrast=1.08)):
            shot_world(c, t)
    else:
        with layer(c, cf=grade_cf(sat=1.1, contrast=1.1)):
            shot_cliff(c, t)
