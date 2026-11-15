"""Scene 13 - The Beautiful View. The chase is over. The stickman sits on the edge
of the world, breathes, and finally feels safe."""
import math

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, paint, layer, inv, keys, ease_io, grade_cf)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from scenes import vista as V

DURATION = 20.0
XFADE = 0.8
CUES = {"walk": 0.0, "sit": 3.0, "breath": 4.5, "behind": 9.0, "relax": 16.0, "exhale": 16.6, "look_up": 18.6}


def stick(t):
    if t < 3.0:
        mv = sm.Mover(0.0, 3.2, 300, lambda tt: 260 * (1 - smooth(inv(tt, 2.2, 2.9))), "tired", 1.6)
        p = sm.gait(mv.phase(t), mv.x(t), V.EDGE_Y, 1.6, 1, "tired")
        p.face, p.eye = 1.0, 0.7
        return p
    sit = V.sit_pose(breath=0.0, head=0.4, eye=0.7)
    if t < 3.8:
        start = sm.Pose(x=sit.x - 40, y=0, s=1.6, f=1, torso=0.5, head=0.3, hp_n=0.4, kn_n=0.6, hp_f=-0.1, kn_f=0.3, face=1.0,
                        eye=0.7)
        sm.settle(start, V.EDGE_Y)
        return sm.blend(start, sit, smooth(inv(t, 3.0, 3.8)))
    # heavy breathing that slowly calms down
    rate = lerp(1.25, 0.32, smooth(inv(t, 4.5, 17.0)))
    amp = lerp(2.6, 1.0, smooth(inv(t, 4.5, 15.0)))
    ph = 0.0
    # integrate phase so the rhythm stays continuous while it slows
    n = 40
    for i in range(n):
        tt = 3.8 + (t - 3.8) * (i + 0.5) / n
        ph += lerp(1.25, 0.32, smooth(inv(tt, 4.5, 17.0))) * (t - 3.8) / n
    b = 0.5 + 0.5 * math.sin(ph * TAU)
    exhale = smooth(inv(t, 16.6, 18.2))
    head = 0.4 + 0.25 * smooth(inv(t, 16.0, 16.8)) - 0.85 * smooth(inv(t, 18.6, 19.8))
    p = V.sit_pose(breath=amp * b * (1 - 0.6 * exhale) + 1.5 * smooth(inv(t, 16.0, 16.6)) * (1 - exhale), head=head)
    p.torso += 0.1 * (1 - smooth(inv(t, 4.5, 14.0))) - 0.08 * smooth(inv(t, 18.6, 19.8))
    p.eye = lerp(0.6, 0.35, exhale) if t < 18.6 else lerp(0.35, 0.8, smooth(inv(t, 18.6, 19.5)))
    p.sh_n += 0.06 * b * amp
    p.sh_f += 0.06 * b * amp
    return p


def side_shot(c, t, cam):
    V.panorama(c, cam, t)
    V.cliff_front(c, cam, t)
    with cam.view(c, 1.0):
        p = stick(t)
        sm.draw(c, p, rim=(1.0, 0.75, 0.4), rim_a=0.6, rim_dir=(1, -0.3), shadow_y=V.EDGE_Y if t < 3.5 else None)
    fx.ambient_motes(c, t, n=40, seed=12, col=(1, 0.85, 0.6), a=0.35, size=(1, 2.5), speed=8)


def render(c, t):
    with layer(c, cf=grade_cf(sat=1.08, contrast=1.04, tint=(1.04, 1.0, 0.95))):
        if t < 4.5:
            cam = Cam(*keys(t, [(0, (760, 620, 1.05)), (4.5, (880, 640, 1.15))], fn=ease_io))
            side_shot(c, t, cam)
        elif t < 9.0:
            cam = Cam(*keys(t, [(4.5, (1040, 700, 2.6)), (9.0, (1050, 705, 2.8))]))
            side_shot(c, t, cam)
        elif t < 16.0:
            u = ease_io(inv(t, 9.0, 16.0))
            cam = Cam(lerp(1000, 960, u), lerp(700, 560, u), lerp(1.25, 1.0, u))
            p = stick(t)
            V.back_view(c, t, cam, breath=p.breath, head_up=0.0)
        else:
            cam = Cam(*keys(t, [(16.0, (1060, 690, 3.0)), (20.0, (1075, 685, 3.3))]))
            side_shot(c, t, cam)
