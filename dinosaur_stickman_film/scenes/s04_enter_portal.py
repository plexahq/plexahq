"""Scene 4 - Entering Another Dimension. One last look back, a leap into the portal,
a tumbling ride through a tunnel of light and a white flash."""
import math

import skia

from engine.core import (Cam, W, H, clamp, lerp, smooth, noise, paint, layer, inv, keys, ease_io, ease_out, ease_in, grade_cf,
                         TAU)
from engine import fx, post
from engine import stickman as sm
from scenes import bedroom as B
from scenes import s03_portal_opens as S3

DURATION = 9.5
CUES = {"look_back": 0.2, "crouch": 1.6, "jump": 2.1, "into": 2.6, "tunnel": 3.0, "flash": 7.8, "silence": 8.4}

S = B.SCALE
X0 = S3.SNEAK.x(10.6) + 18 - 46
JUMP_T0, JUMP_T1 = 2.1, 2.75


def stand_pose(t):
    look = smooth(inv(t, 0.15, 0.6)) * (1 - smooth(inv(t, 1.25, 1.55)))
    p = sm.stand(x=X0, y=0, s=S, f=-1, face=lerp(1.0, -1.0, look), head=-0.1 * look, eye_s=1.2,
                 torso=-0.04 * look)
    p.look = -0.8 * look
    sm.settle(p, B.FLOOR)
    return sm.breathe(p, t, 0.3, 0.6)


def crouch_pose(t):
    p = sm.Pose(x=X0, y=0, s=S, f=-1, torso=0.55, head=-0.25, sh_n=-0.9, el_n=0.4, sh_f=-1.0, el_f=0.3,
                hp_n=0.9, kn_n=1.5, hp_f=0.75, kn_f=1.35, face=1.0, eye_s=1.2)
    return sm.settle(p, B.FLOOR)


def jump_pose(t):
    u = inv(t, JUMP_T0, JUMP_T1)
    e = ease_in(u)
    x = lerp(X0, B.PORTAL[0] + 10, e)
    y0 = B.FLOOR - 0.95 * sm.LEG * S
    y = lerp(y0, B.PORTAL[1] + 30, e) - math.sin(math.pi * u) * 120
    p = sm.Pose(x=x, y=y, s=S * lerp(1.0, 0.35, smooth(inv(u, 0.55, 1.0))), f=-1, rot=0.9 * u, torso=0.5,
                head=-0.3, sh_n=2.6, el_n=0.2, sh_f=2.4, el_f=0.25, hp_n=-0.2, kn_n=0.5, hp_f=-0.45, kn_f=0.9,
                face=1.0, eye_s=1.3)
    p.alpha = 1 - smooth(inv(u, 0.8, 1.0))
    return p


TRACK = sm.Track([(0.0, stand_pose), (1.55, stand_pose), (1.9, crouch_pose, ease_out), (2.1, crouch_pose),
                  (2.25, jump_pose, ease_out), (3.0, jump_pose)])


def room(c, t):
    cam = Cam()
    if t < 1.6:
        cam.x, cam.y, cam.zoom = keys(t, [(0, (760, 660, 2.2)), (1.6, (750, 655, 2.3))])
    else:
        u = ease_in(inv(t, 2.3, 3.1))
        base = keys(t, [(1.6, (660, 620, 1.35)), (2.3, (600, 615, 1.45))])
        cam.x = lerp(base[0], B.PORTAL[0], u)
        cam.y = lerp(base[1], B.PORTAL[1], u)
        cam.zoom = base[2] * (1 + u * 4.5)
    cam.shake(t, 5 + 10 * smooth(inv(t, 2.0, 3.0)))
    p = TRACK(t)
    pw = S3.power(20.0) + 0.6 * smooth(inv(t, 2.3, 2.8))
    with cam.view(c):
        B.room_back(c, t + 50, wind=0.35, wind_t0=-100, curtain_pull=0.35, poster_gone=True)
        B.stick_shadow(c, p, 0.9)
        fx.portal(c, B.PORTAL[0], B.PORTAL[1], B.PORTAL_R * 1.05, t + 20, power=pw, open_=1.0)
        B.bed_back(c, t)
        B.nightstand(c, t, papers_gone=4)
        B.bed_front(c, t)
        B.floor(c, t)
        B.lit_overlay(c, t + 20, min(1.4, pw), 1.0)
        path = B.blanket(c, t, sit=1.0, hump=0.4, flutter=0.3, lap_x=1330, cover_x1=1390)
        B.lit_clip(c, path, t + 20, min(1.4, pw), 1.0)
        if 2.7 < t < 3.1:
            fx.glow(c, B.PORTAL[0], B.PORTAL[1], 160, (1, 1, 1), 0.8 * math.sin(math.pi * inv(t, 2.7, 3.1)), blend="add")
        sm.draw(c, p, rim=B.portal_light_col(t), rim_a=0.75, rim_dir=(-0.9, -0.35))
        fx.ambient_motes(c, t, n=70, seed=4, col=B.portal_light_col(t), a=0.55, area=(80, 250, 1300, 880), size=(1.0, 3.2),
                         speed=30)


def tunnel_pose(t):
    u = t - 3.0
    flail = math.sin(u * 7)
    p = sm.Pose(x=W / 2 + noise(u * 0.7, 3) * 60, y=H / 2 + noise(u * 0.6, 8) * 40, s=3.0 + 0.4 * math.sin(u * 1.3), f=1,
                rot=u * 2.6 + 0.6 * math.sin(u * 1.5), torso=0.1, head=0.2 * flail,
                sh_n=2.2 + 0.5 * flail, el_n=0.4, sh_f=-2.0 - 0.5 * flail, el_f=-0.4,
                hp_n=0.6 + 0.3 * flail, kn_n=0.8, hp_f=-0.5 - 0.3 * flail, kn_f=0.6, face=0.0, eye_s=1.5)
    return p


def tunnel_scene(c, t):
    u = t - 3.0
    speed = 0.6 + 0.25 * u
    fx.tunnel(c, u, speed=speed, hue=u * 0.3, twist=u * 0.4)
    p = tunnel_pose(t)
    sm.draw(c, p, rim=(0.6, 0.9, 1.0), rim_a=0.9, rim_dir=(0.0, 0.0), glow_col=(0.6, 0.85, 1.0), glow_a=0.35)


def render(c, t):
    if t < 3.2:
        with layer(c, cf=grade_cf(sat=1.0, contrast=1.06, tint=(0.95, 0.98, 1.06))):
            room(c, t)
    if t >= 2.9:
        with layer(c, a=smooth(inv(t, 2.9, 3.2))):
            tunnel_scene(c, t)
    if t >= 7.6:
        fx.flash(c, smooth(inv(t, 7.6, 8.4)))
