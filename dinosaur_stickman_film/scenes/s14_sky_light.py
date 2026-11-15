"""Scene 14 - Something In The Sky. A tiny light, then a burning object with a
fiery trail. The peace drains out of the evening."""
import math

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, paint, layer, inv, keys, ease_io, grade_cf, glow, hash01)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from scenes import vista as V

DURATION = 14.0
CUES = {"light": 0.8, "notice": 4.0, "head_up": 4.4, "bright": 6.0, "trail": 7.5, "stand": 10.0, "realize": 12.6}


def doom(t):
    return 0.12 * smooth(inv(t, 6.0, 14.0))


def object_pos(t):
    """The asteroid as seen from the mountain: high in the sky, drifting down-left."""
    u = inv(t, 0.0, 14.0)
    return (lerp(1580, 1300, u), lerp(170, 300, u))


def sky_object(c, cam, t, scale=1.0):
    x, y = object_pos(t)
    sx, sy = cam.to_screen(x, y, 0.02)
    b = smooth(inv(t, 0.8, 4.0)) * 0.5 + 0.5 * smooth(inv(t, 5.5, 10.0))
    tw = 0.8 + 0.2 * math.sin(t * 9)
    r = (2.2 + 6 * smooth(inv(t, 6.0, 13.0))) * scale
    glow(c, sx, sy, r * 14, (1.0, 0.7, 0.4), 0.5 * b * tw)
    if t > 6.5:
        k = smooth(inv(t, 6.5, 12.0))
        fx.asteroid(c, sx, sy, r * 1.2, t, a=k, trail_ang=-0.6, trail_len=6 + 10 * k, heat=0.8 + 0.4 * k, seed=4)
    c.drawCircle(sx, sy, r, paint((1, 0.95, 0.85), b))


def stick(t):
    look = smooth(inv(t, 4.3, 5.0))
    if t < 10.0:
        p = V.sit_pose(head=lerp(0.0, -0.45, look), eye=lerp(0.8, 1.0, look))
        p.eye_s = lerp(1.0, 1.25, look)
        p.look_y = -0.6 * look
        p.breath = 0.6 + 0.4 * math.sin(t * 2)
        return p
    rise = smooth(inv(t, 10.0, 12.2))
    stand = sm.stand(x=V.SIT_ROCK[0] - 60, y=0, s=1.6, f=1, face=1.0, head=-0.45, eye_s=1.4)
    sm.settle(stand, V.EDGE_Y)
    stand.look_y = -0.6
    sit = V.sit_pose(head=-0.45, eye=1.0)
    sit.eye_s, sit.look_y = 1.25, -0.6
    p = sm.blend(sit, stand, rise)
    if t > 12.4:
        k = smooth(inv(t, 12.4, 13.2))
        p.eye_s = 1.4 + 0.3 * k
        p.torso = -0.1 * k
        p.x -= 18 * k
        p = sm.tremble(p, t, 0.8 * k)
    return p


def render(c, t):
    d = doom(t)
    with layer(c, cf=grade_cf(sat=1.06, contrast=1.05, tint=(1.04, 1.0 - 0.1 * d, 0.95 - 0.15 * d))):
        if t < 4.0 or 6.0 <= t < 10.0:
            if t < 4.0:
                cam = Cam(*keys(t, [(0, (960, 560, 1.0)), (4.0, (980, 540, 1.04))]))
            else:
                cam = Cam(*keys(t, [(6.0, (1300, 360, 1.6)), (10.0, (1250, 380, 1.7))], fn=ease_io))
            def extra(c_, cam_):
                sky_object(c_, cam_, t)
            V.back_view(c, t, cam, doom=d, breath=0.6, head_up=smooth(inv(t, 4.2, 5.0)), extra=extra, figure=t < 4.0)
        else:
            if t < 6.0:
                cam = Cam(*keys(t, [(4.0, (1060, 690, 3.0)), (6.0, (1065, 680, 3.1))]))
            else:
                cam = Cam(*keys(t, [(10.0, (1000, 680, 2.0)), (14.0, (975, 650, 2.5))], fn=ease_io))
            V.panorama(c, cam, t, doom=d)
            sky_object(c, cam, t)
            V.cliff_front(c, cam, t, doom=d)
            with cam.view(c, 1.0):
                sm.draw(c, stick(t), rim=(1.0, 0.7, 0.4), rim_a=0.6, rim_dir=(1, -0.3), shadow_y=V.EDGE_Y if t > 11 else None)
