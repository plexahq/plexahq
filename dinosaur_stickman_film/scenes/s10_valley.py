"""Scene 10 - The Prehistoric Valley. A breath of wonder: waterfall, lake, a herd of
long-necked giants, and one of them leans down to look at the tiny visitor."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_out, ease_in, grade_cf, seg, draw_img, tint_cf)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import prehistoric as PH

DURATION = 20.5
CUES = {"emerge": 0.3, "reveal": 1.5, "amazed": 6.5, "herd": 8.5, "lower": 13.5, "freeze": 14.2, "snort": 15.2,
        "turn_away": 16.0, "walk_on": 17.0}

PAL = PH.P("day")
SAU = D.Sauropod()
GY = 900
S = 1.4

# The big sauropod that leans down. Its pose at full lean decides where the stickman stands.
BIG_X = 1200
BIG_S = 1.55


LOW_CURL = 0.135


def big_pose(t, k=None, curl=None):
    if k is None:
        k = smooth(inv(t, 13.5, 14.8)) * (1 - smooth(inv(t, 16.0, 17.4)))
    return dict(x=BIG_X, gy=GY, s=BIG_S, f=1, t=0.0, moving=False, phase=0.0,
                neck_raise=lerp(0.62, 0.15, k), neck_curl=lerp(-0.06, curl if curl is not None else LOW_CURL, k),
                head_pitch=lerp(0.4, 0.55, k), blink=1.0 if 15.6 < t < 15.75 else 0.0)


def _fit_curl(target_y):
    best, bc = 1e9, 0.1
    for i in range(80):
        cu = -0.02 + i * 0.0025
        y = SAU.head_world(big_pose(0, k=1.0, curl=cu))[1]
        if abs(y - target_y) < best:
            best, bc = abs(y - target_y), cu
    return bc


LOW_CURL = _fit_curl(GY - 150)
HEAD_LOW = SAU.head_world(big_pose(0, k=1.0))
STICK_X = HEAD_LOW[0] + 120


def herd_pose(i, t):
    """Background sauropods grazing / walking slowly."""
    h = [hash01(i, 71, k) for k in range(5)]
    graze = 0.5 + 0.5 * math.sin(t * 0.4 + i * 1.3)
    return dict(neck_raise=lerp(0.65, -0.15, graze * h[0]), neck_curl=lerp(-0.05, 0.08, graze * h[0]), head_pitch=0.5 + 0.4 * graze * h[0])


def valley_backdrop(c, cam, t, near_herd=True):
    PH.sky(c, cam, t, PAL, sun=(1500, 140), sun_r=50, cloud_seed=11, cloud_y=150)
    N.godrays(c, *cam.to_screen(1500, 140, 0.02), t, col=PAL["light"], a=0.13, n=10, spread=1.4, base_ang=2.0, length=2800)
    PH.far_mountains(c, cam, t, PAL, y=300, p=0.06, seed=41, h=460, key="s10",
                     peaks=[(0.12, 0.85, 0.05), (0.3, 0.7, 0.06), (0.5, 1.0, 0.07), (0.68, 0.8, 0.05), (0.85, 0.9, 0.06)])
    PH.mid_mountains(c, cam, t, PAL, y=470, p=0.14, seed=43, h=380, key="s10")
    PH.flock(c, cam, t, p=0.2, n=7, seed=21, area=(-300, 180, 2300, 420), scale=0.8, col=mix("#3b3433", PAL["haze"], 0.35))
    # the great waterfall into the lake
    PH.waterfall_cliff(c, cam, t, PAL, x=650, top=360, bottom=720, width=220, p=0.24, seed=17, cliff_w=1100, haze_a=0.3)
    with cam.view(c, 0.26):
        N.water_band(c, -1500, 3500, 715, 830, t, top="#8fd0e6", bot="#3a8fb0", flow=12, density=1.2)
        N.mist(c, 712, t, col=(1, 1, 1), a=0.4, thick=60, seed=12, speed=8)
    with cam.view(c, 0.35):
        N.ground_fill(c, -2000, 4000, 800, mix(PAL["grass"][1], PAL["haze"], 0.3), mix(PAL["grass"][0], PAL["haze"], 0.15), 600)
    PH.forest_band(c, cam, PAL, 805, 0.35, seed=44, haze_a=0.3, tall=0.8, x0=-2200, w=2600)
    PH.herd(c, cam, t, PAL, 0.4, 850, [1300, 1500, 1680, 1900, 2150], s=0.2, haze_a=0.35, f=-1, speed=5, seed=8)
    PH.herd(c, cam, t, PAL, 0.55, 900, [-200, 150, 2400, 2700], s=0.3, haze_a=0.22, f=1, speed=7, seed=9)


def ground(c, cam, t):
    with cam.view(c, 1.0):
        N.ground_fill(c, cam.left() - 200, cam.right() + 200, GY, PAL["ground"][0], PAL["ground"][1], 1400)
        N.grass(c, cam.left() - 200, cam.right() + 200, GY + 4, t, seed=101, h=30, density=0.4, col=PAL["grass"][0],
                col2=PAL["grass"][1])


# ----------------------------------------------------------------- A: the reveal
def stick_a(t):
    mv = sm.Mover(0.0, 8.5, -150, lambda tt: 160 * (1 - smooth(inv(tt, 4.5, 6.0))), "walk", S)
    if t < 6.2:
        p = sm.gait(mv.phase(t), mv.x(t), GY, S, 1, "walk")
        p.face = 1.0
        p.head = -0.15 * smooth(inv(t, 1.5, 3.0))
        p.eye_s = 1.2
        return p
    p = sm.stand(x=mv.x(t), y=0, s=S, f=1, face=1.0, head=-0.3, eye_s=1.45,
                 sh_n=0.15 + 0.5 * smooth(inv(t, 6.6, 7.4)), el_n=0.3, sh_f=-0.05 + 0.35 * smooth(inv(t, 6.6, 7.4)))
    sm.settle(p, GY)
    return sm.breathe(p, t, 0.3, 1.2)


def shot_reveal(c, t):
    u = ease_io(inv(t, 0.6, 6.4))
    cam = Cam(lerp(150, 780, u), lerp(760, 470, u), math.exp(lerp(math.log(2.6), math.log(0.85), u)))
    valley_backdrop(c, cam, t)
    ground(c, cam, t)
    p = stick_a(t)
    with cam.view(c, 1.0):
        sm.draw(c, p, rim=PAL["light"], rim_a=0.35, rim_dir=(0.8, -0.6), shadow_y=GY + 1)
        for i, x in enumerate((-300, 600, 1500)):
            N.fern(c, x, GY + 6, 150, 120 + i, t, wind=0.08, col=PAL["forest"][1], col2=PAL["forest"][2])
    # foliage parting at the forest edge
    with cam.view(c, 1.25):
        part = smooth(inv(t, 0.0, 1.4))
        with layer(c, blur=6):
            for i in range(4):
                N.fern(c, -260 + i * 120 - part * 320 * (1 if i < 2 else -0.4), GY + 160, 380, 140 + i, t, wind=0.1,
                       col=shade(PAL["forest"][0], -0.3), col2=shade(PAL["forest"][1], -0.3))


# ----------------------------------------------------------------- B: amazement close
def shot_amazed(c, t):
    p = stick_a(t)
    J = sm.joints(p)
    cam = Cam(J["neck"][0] + 30, J["neck"][1] - 10, 3.4)
    with cam.view(c, 0.2):
        with layer(c, blur=10):
            valley_backdrop(c, Cam(900, 520, 1.0), t)
    with cam.view(c, 1.0):
        sm.draw(c, p, rim=PAL["light"], rim_a=0.45, rim_dir=(0.8, -0.6))
    fx.ambient_motes(c, t, n=30, seed=8, col=(1, 1, 0.9), a=0.35, size=(1, 3), speed=10)


# ----------------------------------------------------------------- C/D/E: among the giants
WALK2 = sm.Mover(8.5, 20.5, STICK_X - 700,
                 lambda tt: 120 * (1 - smooth(inv(tt, 12.9, 13.5))) + 110 * smooth(inv(tt, 17.0, 17.6)), "sneak", S)


def stick_c(t):
    x = WALK2.x(t)
    kind = "sneak" if t < 17.0 else "walk"
    p = sm.gait(WALK2.phase(t), x, GY, S, 1, kind)
    p.face, p.eye_s = 1.0, 1.3
    p.head = -0.25 if t < 13.0 else p.head
    if 13.2 <= t < 17.2:
        st = sm.stand(x=x, y=0, s=S, f=1, face=1.0, eye_s=1.5, head=-0.35 + 0.25 * smooth(inv(t, 13.6, 14.6)),
                      torso=-0.08, sh_n=0.2, sh_f=-0.05)
        sm.settle(st, GY)
        st.look = 0.0
        st.look_y = -0.6 * (1 - smooth(inv(t, 14.0, 14.8)))
        frz = smooth(inv(t, 14.0, 14.4)) * (1 - smooth(inv(t, 16.2, 16.8)))
        st = sm.tremble(st, t, 1.2 * frz)
        if t >= 16.4:
            relief = smooth(inv(t, 16.4, 17.0))
            st.breath = 2.0 * (1 - relief)
            st.eye = 1 - 0.6 * relief * (1 - smooth(inv(t, 17.0, 17.2)))
        p = sm.blend(p, st, smooth(inv(t, 13.2, 13.5)) * (1 - smooth(inv(t, 16.9, 17.2))))
    if t >= 17.0:
        p.head = 0.05
        p.eye_s = 1.1
    return p


def herd_layer(c, cam, t, p_layer, items, haze_a, blur=0.0, dark=0.0):
    with cam.view(c, p_layer):
        with layer(c, blur=blur):
            for i, (x, s, f, sp) in enumerate(items):
                gp = herd_pose(i, t)
                P = dict(x=x + sp * t * f, gy=GY + (1 - p_layer) * -40, s=s, f=f, t=t + i, moving=sp > 0,
                         phase=(sp * t) / (110 * s) * 0.25 + hash01(i, 3), **gp)
                SAU.draw(c, P, light=PAL["light"], light_a=0.3, haze=PAL["haze"], haze_a=haze_a, shadow=True)


def shot_herd(c, t):
    p = stick_c(t)
    if t < 13.5:
        cam = Cam(p.x + 180, 560, 0.95)
    elif t < 17.0:
        u = ease_io(inv(t, 13.5, 14.6))
        cam = Cam(lerp(p.x + 180, (HEAD_LOW[0] + p.x) / 2 + 30, u), lerp(560, 760, u), lerp(0.95, 2.0, u))
    else:
        cam = Cam(p.x + 260, 560, 0.95)
    cam.x += 0
    valley_backdrop(c, cam, t)
    herd_layer(c, cam, t, 0.75, [(STICK_X - 1100, 0.9, -1, 14), (STICK_X + 900, 1.0, -1, 12)], 0.2)
    ground(c, cam, t)
    with cam.view(c, 1.0):
        bp = big_pose(t)
        SAU.draw(c, bp, light=PAL["light"], light_a=0.35, haze=PAL["haze"], haze_a=0.04)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.35, rim_dir=(0.8, -0.6), shadow_y=GY + 1)
        if t > 15.0:
            hx, hy = SAU.head_world(bp)
            fx.dust(c, t, 15.2, hx + 40, hy + 10, scale=0.35, col=(0.95, 0.96, 0.95), a=0.35, n=6, seed=6, spread=0.6, rise=0.0,
                    dur=1.3, dirx=1.2)
    if t < 13.5:
        herd_layer(c, cam, t, 1.3, [(STICK_X + 1500, 1.8, -1, 0)], 0.0, blur=9, dark=0.3)


def render(c, t):
    with layer(c, cf=grade_cf(sat=1.1, contrast=1.04, tint=(1.03, 1.0, 0.95))):
        if t < 6.5:
            shot_reveal(c, t)
        elif t < 8.5:
            shot_amazed(c, t)
        else:
            shot_herd(c, t)
