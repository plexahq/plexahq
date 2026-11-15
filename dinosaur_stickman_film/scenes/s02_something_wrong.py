"""Scene 2 - Something Is Wrong. A faint blue light appears on the wall and grows;
particles drift; the sleeper stirs and opens its eyes."""
import math

from engine.core import (Cam, clamp, lerp, smooth, noise, paint, layer, inv, keys, ease_io, grade_cf, TAU)
from engine import fx, post
from engine import stickman as sm
from scenes import bedroom as B
from scenes.s01_quiet_night import sleeper, sleeper_arm

DURATION = 11.0
XFADE = 0.0
CUES = {"glow": 0.6, "hum": 1.5, "stir": 6.4, "eyes_open": 8.4, "eyes_full": 9.3}


def glow_level(t):
    return 0.08 + 0.75 * smooth(inv(t, 0.6, 10.5)) ** 1.4 + 0.06 * math.sin(t * 5.3) * smooth(inv(t, 2, 6))


def waking(t):
    p, b = sleeper(t + 17.0)
    stir = smooth(inv(t, 6.4, 7.2)) - 0.6 * smooth(inv(t, 7.2, 7.9))
    p.head = -0.05 - 0.25 * stir + 0.2 * smooth(inv(t, 9.8, 10.6))
    p.x += 6 * stir
    # eyes: closed, flutter, open, blink, open wide
    e = 0.0
    if t > 8.4:
        e = smooth(inv(t, 8.4, 8.6)) * 0.55
    if t > 8.75:
        e = 0.55 * (1 - smooth(inv(t, 8.75, 8.85)))
    if t > 9.25:
        e = smooth(inv(t, 9.25, 9.55))
    p.eye = e
    p.eye_s = 1.0 + 0.15 * smooth(inv(t, 10.0, 10.6))
    p.face = 0.0
    p.look_y = 0.9 * smooth(inv(t, 9.8, 10.3))
    return p, b, stir


def render(c, t):
    g = glow_level(t)
    power = g * 0.55
    p, b, stir = waking(t)
    cam = Cam()
    if t < 6.0:
        cam.x, cam.y, cam.zoom = keys(t, [(0, (1000, 560, 1.0)), (6.0, (860, 560, 1.1))], fn=ease_io)
    else:
        cam.x, cam.y, cam.zoom = keys(t, [(6.0, (1395, 772, 2.7)), (11.0, (1405, 770, 3.0))], fn=ease_io)
    with layer(c, cf=grade_cf(sat=0.9, contrast=1.05, tint=(0.92, 0.98, 1.08))):
        with cam.view(c):
            B.room_back(c, t + 17, glow_a=g)
            B.bed_back(c, t)
            B.nightstand(c, t)
            B.bed_front(c, t)
            B.floor(c, t)
            for k, sx in enumerate((1050, 1085)):
                from engine.core import spline
                c.drawPath(spline([(sx - 22, 874), (sx - 18, 864), (sx + 10, 862), (sx + 24, 868), (sx + 22, 878), (sx - 20, 878)]),
                           paint("#4a2d44"))
            B.lit_overlay(c, t, power, open_=0.6)
            sm.draw(c, p, rim=B.portal_light_col(t), rim_a=0.25 + 0.5 * g, rim_dir=(-0.9, -0.4))
            path = B.blanket(c, t, breath=b, flutter=0.0)
            B.lit_clip(c, path, t, power, 0.6)
            sleeper_arm(c, p, t, stir)
            fx.ambient_motes(c, t, n=int(20 + 60 * g), seed=4, col=B.portal_light_col(t), a=0.6 * g,
                             area=(100, 250, 1100, 880), size=(1.0, 3.0), speed=14)
    post.fade(c, 1 - smooth(inv(t, 0.0, 0.25)) if False else 0.0)
