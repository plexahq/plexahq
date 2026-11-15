"""Scene 16 - Impact. Atmospheric entry, a blinding flash, the fireball and shockwave,
the wall of dust that swallows the mountain and then the world."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_in, ease_out, grade_cf)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import vista as V

DURATION = 11.0
CUES = {"entry": 0.0, "impact": 1.6, "fireball": 2.4, "shockwave": 2.8, "wave_hits": 6.0, "engulf": 7.9, "world": 8.6,
        "silence": 11.0}
T_IMPACT = 1.6
IMPACT = (1220, 690)       # in the p=0.1 layer of the vista


def shot_entry(c, t):
    cam = Cam(900, 600, 1.0)
    cam.shake(t, 4 + 10 * smooth(inv(t, 0.8, 1.6)))
    V.panorama(c, cam, t, doom=1.0, herd_run=1.0, flock_n=0)
    u = ease_in(inv(t, 0.0, T_IMPACT))
    tx, ty = cam.to_screen(*IMPACT, 0.1)
    ax, ay = lerp(2200, tx, u), lerp(-260, ty, u)
    fx.light_overlay(c, ax, ay, 2000, (1.0, 0.55, 0.2), 0.35 + 0.3 * u, blend="screen")
    fx.asteroid(c, ax, ay, 46 + 30 * u, t, trail_ang=math.atan2(-260 - ty, 2200 - tx), trail_len=18, heat=1.5, seed=5)
    V.cliff_front(c, cam, t, doom=1.0)
    with cam.view(c, 1.0):
        p = sm.stand(x=V.SIT_ROCK[0] - 110, y=0, s=1.6, f=1, face=1.0, head=-0.2, eye_s=1.9, torso=-0.12, sh_n=0.8, el_n=1.2,
                     sh_f=0.6, el_f=1.0)
        sm.settle(p, V.EDGE_Y)
        sm.draw(c, sm.tremble(p, t, 2.0), rim=(1.0, 0.55, 0.2), rim_a=0.8, rim_dir=(0.8, -0.6), shadow_y=V.EDGE_Y)


def explosion(c, cam, t, k_scale=1.0):
    """Fireball, shock ring and mushroom cloud at the impact point (p=0.1 layer)."""
    age = t - T_IMPACT
    with cam.view(c, 0.1):
        x, y = IMPACT
        ring = 60 + 2400 * (1 - math.exp(-age * 0.55))
        # scorched land behind the ring
        ellipse(c, x, y + 10, ring * 0.95, ring * 0.12, paint((0.12, 0.05, 0.03), 0.55, blur=30))
        fx.shock_ring(c, x, y + 10, ring, age, a=clamp(1.2 - age * 0.15), flat=0.12)
        fx.mushroom(c, x, y, age, scale=0.55 * k_scale, a=1.0, seed=7)
        dome = 120 + 260 * (1 - math.exp(-age * 1.2))
        heat = math.exp(-age * 0.35)
        c.save()
        c.clipRect(skia.Rect(x - 4000, y - 4000, x + 4000, y + 12))
        glow(c, x, y, dome * 3.0, (1.0, 0.5, 0.15), 0.8 * heat)
        c.drawCircle(x, y, dome, paint(shader=rad((x, y - dome * 0.3), dome, [(0, (1, 0.98, 0.85)), (0.5, (1, 0.7, 0.25)),
                                                                                (1, (0.9, 0.25, 0.05))]), a=0.95 * heat + 0.05))
        c.restore()
        fx.burst(c, t, T_IMPACT + 0.3, x, y - 40, 70, 17, speed=(400, 1500), ang=(-math.pi + 0.25, -0.25), grav=500,
                 life=(2.0, 4.0), size=(2, 5), col=(1, 0.75, 0.3), col2=(0.4, 0.15, 0.05), streak=0.03, drag=0.2)


def shot_blast(c, t):
    cam = Cam(*keys(t, [(2.4, (1150, 560, 1.15)), (6.0, (1100, 520, 0.95))], fn=ease_out))
    cam.shake(t, 10 + 8 * math.exp(-(t - 2.4)))
    V.panorama(c, cam, t, doom=1.0, herd_run=1.0, flock_n=0)
    explosion(c, cam, t)
    with cam.view(c, 0.35):
        # a row of trees that bend as the shockwave passes
        age = t - T_IMPACT
        front = 1220 - (60 + 2400 * (1 - math.exp(-age * 0.55))) * 0.5
        for i in range(16):
            x = -400 + i * 170
            passed = clamp((1250 - x) / 700 - (1 - min(1, age / 4.5)) * 2.0)
            bend = -0.9 * smooth(passed) + 0.05 * math.sin(t * 20 + i) * smooth(passed)
            N.tree(c, "arauc" if i % 2 else "broad", 200 + i, x, 905, 260 + 60 * hash01(i, 2), t, wind=0.02,
                   haze=(0.5, 0.2, 0.1), haze_a=0.2, dark=0.85, sway_extra=bend)
    fx.flash(c, 1 - smooth(inv(t, 2.4, 3.3)))


def shot_wave(c, t):
    """On the mountain: the dust wall arrives."""
    u = inv(t, 6.0, 8.6)
    cam = Cam(V.SIT_ROCK[0] - 40, 690, 2.0)
    cam.shake(t, 12 + 30 * smooth(inv(t, 6.8, 7.8)))
    front = lerp(2600, 400, ease_in(u))
    wind = smooth(inv(front, 2200, 1100))
    V.panorama(c, cam, t, doom=1.0, herd_run=1.0, flock_n=0)
    with cam.view(c, 0.1):
        fx.mushroom(c, IMPACT[0], IMPACT[1], t - T_IMPACT, scale=0.55, a=1.0, seed=7)
    V.cliff_front(c, cam, t, doom=1.0)
    with cam.view(c, 1.0):
        # the stickman bracing into the blast, then knocked off its feet
        brace = smooth(inv(t, 6.2, 6.9))
        knocked = smooth(inv(t, 7.55, 8.0))
        p = sm.Pose(x=V.SIT_ROCK[0] - 120 - 140 * knocked, y=0, s=1.6, f=1, torso=0.35 * brace - 0.9 * knocked,
                    head=-0.3 * brace, face=1.0, eye_s=1.9, eye=1 - 0.5 * brace,
                    sh_n=2.2 * brace + 1.0 * knocked, el_n=1.6 * brace, sh_f=1.9 * brace + 1.5 * knocked, el_f=1.7 * brace,
                    hp_n=0.4 * brace, kn_n=0.5 * brace, hp_f=-0.5 * brace, kn_f=0.2 * brace, rot=-0.6 * knocked)
        sm.settle(p, V.EDGE_Y)
        p.y -= 60 * knocked
        p.x += 8 * noise(t * 30, 2) * brace
        fx.burst(c, t, 6.3, V.SIT_ROCK[0] + 400, V.EDGE_Y - 80, 80, 23, speed=(500, 1100), ang=(math.pi - 0.3, math.pi + 0.15),
                 grav=200, life=(0.8, 1.6), size=(1.5, 4), col=(0.4, 0.3, 0.25), streak=0.03, spawn=2.0)
        fx.leaves(c, t, 6.4, V.SIT_ROCK[0] + 500, V.EDGE_Y - 200, 30, 24, col=("#3a2a1a", "#5a3a1a", "#2a1a10"), spread=300,
                  up=100, dur=2.0, size=8, wind=-1400)
        sm.draw(c, p, rim=(1.0, 0.5, 0.2), rim_a=0.8, rim_dir=(0.9, -0.4))
        fx.dust_wall(c, front, V.EDGE_Y + 60, 1600, t, direction=-1, col=(0.32, 0.2, 0.15), lit=(1.0, 0.45, 0.15), a=1.0)
    fx.light_overlay(c, W, H / 2, 2000, (1.0, 0.4, 0.1), 0.25 * wind, blend="screen")


def shot_world(c, t):
    """Ultra wide: the dust swallows everything."""
    u = inv(t, 8.6, 11.0)
    cam = Cam(1100, 520, lerp(0.75, 0.68, u))
    cam.shake(t, 8)
    V.panorama(c, cam, t, doom=1.0, herd_run=1.0, flock_n=0)
    with cam.view(c, 0.1):
        x, y = IMPACT
        age = t - T_IMPACT
        fx.mushroom(c, x, y, age, scale=0.55, a=1.0, seed=7)
        R = lerp(900, 3400, ease_in(u))
        r_ = Rng(77)
        for i in range(60):
            a = math.pi + r_.u(0, math.pi)
            d = r_.u(0.8, 1.0) * R
            px, py = x + math.cos(a) * d * 1.3, y + 40 + math.sin(a) * d * 0.45
            rr = r_.u(140, 320) * (0.6 + 0.6 * u)
            fx.billow(c, px, py, rr, 600 + i, (0.24, 0.15, 0.11), 1.0, lit=(1.0, 0.45, 0.15), lit_a=0.3, lit_dir=(0, 1))
        c.drawPath(spline([(x - R * 1.3, y + 60), (x - R * 1.2, y - R * 0.35), (x, y - R * 0.48), (x + R * 1.2, y - R * 0.35),
                           (x + R * 1.3, y + 60), (x + R * 1.3, y + 2000), (x - R * 1.3, y + 2000)]), paint((0.22, 0.13, 0.1), 1.0))
    fx.light_overlay(c, W / 2, H * 0.7, 1800, (1.0, 0.35, 0.1), 0.2, blend="screen")
    post.fade(c, smooth(inv(t, 10.4, 11.0)) * 0.85)


def render(c, t):
    with layer(c, cf=grade_cf(sat=1.12, contrast=1.1)):
        if t < T_IMPACT:
            shot_entry(c, t)
        elif t < 2.4:
            c.drawRect(skia.Rect(-10, -10, W + 10, H + 10), paint((1, 1, 1)))
            k = inv(t, T_IMPACT, 2.4)
            glow(c, W * 0.62, H * 0.62, 600 + 1600 * k, (1, 0.9, 0.7), 0.6)
        elif t < 6.0:
            shot_blast(c, t)
        elif t < 8.6:
            shot_wave(c, t)
        else:
            shot_world(c, t)
    if T_IMPACT <= t < T_IMPACT + 0.12:
        fx.flash(c, 1.0)
