"""Scene 3 - The Portal Opens. The wall erupts into a swirling portal. The stickman
sits up, freezes, approaches, flinches from a spark, fights the wind and decides."""
import math
from dataclasses import replace

import skia

from engine.core import (Cam, W, H, clamp, lerp, smooth, noise, paint, layer, inv, keys, ease_io, ease_out, ease_in,
                         ease_back, grade_cf, spline, TAU, hash01, seg)
from engine import fx, post
from engine import stickman as sm
from scenes import bedroom as B

DURATION = 20.0
CUES = {"burst": 1.0, "sit_up": 2.6, "tilt": 5.2, "out_of_bed": 7.0, "steps": 8.6, "reach": 10.6, "spark": 12.0,
        "wind": 13.6, "slip": 14.6, "breath_in": 17.8, "breath_out": 18.8, "nod": 19.5}

S = B.SCALE
STAND_Y = B.FLOOR
WIND_T0 = 13.7


def open_amount(t):
    return ease_back(inv(t, 1.0, 1.8), 1.4) if t >= 1.0 else 0.0


def power(t):
    if t < 1.0:
        return 0.85 + 0.6 * smooth(inv(t, 0.0, 1.0))
    p = 1.0 + 0.6 * math.exp(-(t - 1.0) * 3)
    p += 0.45 * smooth(inv(t, 13.3, 14.2)) * (1 - 0.3 * smooth(inv(t, 17.0, 19.0)))
    return p


def wind(t):
    return smooth(inv(t, 13.4, 14.2)) * (1 - 0.65 * smooth(inv(t, 17.0, 18.5)))


# ----------------------------------------------------------------- choreography
def lie(t):
    p = sm.Pose(x=1300, y=792, s=S, f=-1, rot=-math.pi / 2, head=-0.05, sh_n=0.05, el_n=0.1, sh_f=0.05, el_f=0.1,
                hp_n=0.0, kn_n=0.02, hp_f=0.03, kn_f=0.05, face=0.0, eye=1.0, eye_s=1.15, look_y=0.9)
    return p


def sit(t, lean=0.05):
    p = sm.Pose(x=1300, y=794, s=S, f=-1, rot=0.0, torso=lean, head=0.0, sh_n=-0.45, el_n=0.35, sh_f=-0.5, el_f=0.3,
                hp_n=math.pi / 2, kn_n=0.0, hp_f=math.pi / 2 - 0.04, kn_f=0.03, face=1.0, eye=1.0, eye_s=1.35)
    return sm.tremble(p, t, 0.6 * smooth(inv(t, 3.2, 3.6)) * (1 - smooth(inv(t, 6.5, 7.0))))


def tilt(t):
    p = sit(t, lean=0.12)
    a = smooth(inv(t, 5.2, 6.4))
    p.head = 0.35 * a
    p.torso += 0.03 * math.sin(t * 2)
    p.eye_s = 1.35 + 0.1 * a
    return p


def edge(t):
    p = sm.Pose(x=1255, y=794, s=S, f=-1, torso=0.2, head=0.05, sh_n=-0.55, el_n=0.4, sh_f=-0.6, el_f=0.35,
                hp_n=math.pi / 2 - 0.15, kn_n=math.pi / 2 - 0.1, hp_f=math.pi / 2 - 0.05, kn_f=math.pi / 2 + 0.05,
                face=1.0, eye_s=1.3)
    return p


def rise(t):
    p = sm.Pose(x=1195, y=0, s=S, f=-1, torso=0.55, head=-0.15, sh_n=0.4, el_n=0.6, sh_f=0.3, el_f=0.5,
                hp_n=0.75, kn_n=1.0, hp_f=0.55, kn_f=0.9, face=1.0, eye_s=1.3)
    return sm.settle(p, STAND_Y)


def stand(x, **kw):
    p = sm.stand(x=x, y=0, s=S, f=-1, face=1.0, eye_s=1.3, **kw)
    return sm.settle(p, STAND_Y)


SNEAK = sm.Mover(8.5, 10.6, 1150, lambda t: -175 * smooth(inv(t, 8.5, 8.9)) * (1 - smooth(inv(t, 10.2, 10.6))), "sneak", S)


def sneak(t):
    p = sm.gait(SNEAK.phase(t), SNEAK.x(t), STAND_Y, S, -1, "sneak")
    p.face, p.eye_s = 1.0, 1.3
    p.sh_n, p.el_n = 0.5 + 0.08 * math.sin(t * 3), 1.1
    p.sh_f, p.el_f = 0.35, 1.2
    return sm.tremble(p, t, 0.4)


X_REACH = None


def reach(t):
    x0 = SNEAK.x(10.6)
    p = stand(x0, torso=0.12, head=0.1)
    a = smooth(inv(t, 10.6, 11.9))
    back = ease_out(inv(t, 12.0, 12.25))
    hand = (lerp(x0 - 20, x0 - 120, a * (1 - back) + 0 * back), lerp(STAND_Y - 160, STAND_Y - 170, a))
    if back > 0:
        hand = (lerp(x0 - 120, x0 + 15, back), lerp(STAND_Y - 170, STAND_Y - 205, back))
        p.torso = lerp(0.12, -0.25, back)
        p.head = lerp(0.1, -0.2, back)
        p.x += 18 * back
    sm.arm_ik(p, "n", hand)
    p.sh_f, p.el_f = 0.3 + 0.3 * back, 1.2
    p.eye_s = 1.3 + 0.35 * back
    sm.settle(p, STAND_Y)
    return sm.tremble(p, t, 0.5 + 1.2 * back * (1 - smooth(inv(t, 12.4, 13.4))))


def wind_pose(t):
    x0 = SNEAK.x(10.6) + 18
    slip = smooth(inv(t, 14.6, 15.4))
    x = x0 - 46 * slip
    struggle = smooth(inv(t, 13.8, 14.4)) * (1 - smooth(inv(t, 16.4, 17.4)))
    p = sm.Pose(x=x, y=0, s=S, f=-1, torso=-0.38 * struggle, head=-0.2 * struggle, face=1.0, eye_s=1.4)
    # feet braced apart
    p.hp_n, p.kn_n = 0.35 * struggle + 0.05, 0.2 * struggle + 0.05
    p.hp_f, p.kn_f = -0.45 * struggle - 0.05, 0.15 * struggle + 0.05
    # arms: shield face, then windmill during the slip
    wm = smooth(inv(t, 14.6, 14.9)) * (1 - smooth(inv(t, 15.8, 16.3)))
    sw = t * 13
    p.sh_n = lerp(2.3 * struggle, 2.0 + 1.3 * math.sin(sw), wm)
    p.el_n = lerp(1.6 * struggle, 0.3, wm)
    p.sh_f = lerp(1.6 * struggle, 2.0 + 1.3 * math.sin(sw + 2.5), wm)
    p.el_f = lerp(1.8 * struggle, 0.3, wm)
    sm.settle(p, STAND_Y)
    return sm.tremble(p, t, 1.5 * struggle)


def breath_pose(t):
    x0 = SNEAK.x(10.6) + 18 - 46
    inhale = smooth(inv(t, 17.8, 18.8)) * (1 - smooth(inv(t, 18.8, 19.6)))
    nod = math.sin(math.pi * inv(t, 19.5, 19.95)) if 19.5 < t < 19.95 else 0
    p = stand(x0, torso=-0.05 * inhale, head=-0.2 * inhale + 0.3 * nod, sh_n=0.12 + 0.15 * inhale, sh_f=-0.1 - 0.1 * inhale)
    p.breath = inhale * 3
    p.y -= 4 * inhale
    p.eye_s = 1.25
    p.eye = 1 - 0.85 * smooth(inv(t, 18.9, 19.1)) * (1 - smooth(inv(t, 19.3, 19.5)))
    return p


TRACK = sm.Track([
    (0.0, lie), (2.6, lie), (3.1, sit, ease_out), (5.0, sit), (5.2, tilt), (6.8, tilt), (7.0, tilt),
    (7.6, edge), (8.1, rise), (8.5, lambda t: stand(1150)), (8.6, sneak, smooth), (10.55, sneak), (10.75, reach),
    (13.2, reach), (13.8, wind_pose), (17.4, wind_pose), (17.7, breath_pose), (20.0, breath_pose),
])


def stick(t):
    return TRACK(t)


def blanket_state(t):
    """(sit, hump) of the blanket: on the sleeper, on the lap, then pushed back."""
    s = smooth(inv(t, 2.6, 3.1))
    off = smooth(inv(t, 6.9, 7.5))
    return s, 1.0 - 0.6 * off, off


# ----------------------------------------------------------------- shots
SHOTS = [
    (0.0, 2.5, lambda t: keys(t, [(0, (900, 560, 1.0)), (2.5, (880, 560, 1.04))])),
    (2.5, 5.0, lambda t: keys(t, [(2.5, (1250, 700, 1.9)), (5.0, (1265, 700, 1.95))])),
    (5.0, 7.0, lambda t: keys(t, [(5.0, (1250, 690, 3.0)), (7.0, (1245, 688, 3.25))])),
    (7.0, 10.5, lambda t: keys(t, [(7.0, (1040, 620, 1.25)), (10.5, (860, 620, 1.3))], fn=ease_io)),
    (10.5, 13.5, lambda t: keys(t, [(10.5, (700, 640, 1.85)), (13.5, (720, 640, 1.95))])),
    (13.5, 17.5, lambda t: keys(t, [(13.5, (820, 560, 1.0)), (17.5, (780, 570, 1.08))])),
    (17.5, 20.0, lambda t: keys(t, [(17.5, (720, 700, 2.4)), (20.0, (712, 690, 2.6))])),
]


def camera(t):
    cam = Cam()
    for a, b, fn in SHOTS:
        if a <= t < b or (b == DURATION and t >= a):
            cam.x, cam.y, cam.zoom = fn(t)
            break
    shake = 0.0
    if t >= 1.0:
        shake += 14 * math.exp(-(t - 1.0) * 2.5)
    shake += 6 * wind(t)
    if 12.0 <= t < 12.5:
        shake += 6 * (1 - inv(t, 12.0, 12.5))
    cam.shake(t, shake)
    return cam


def render(c, t):
    cam = camera(t)
    pw = power(t)
    op = open_amount(t)
    wd = wind(t)
    p = stick(t)
    bsit, bhump, boff = blanket_state(t)
    lit = min(1.4, pw * (0.35 + 0.65 * min(1, op)))
    poster_gone = t >= WIND_T0 + 1.5
    with layer(c, cf=grade_cf(sat=1.0, contrast=1.06, tint=(0.95, 0.98, 1.06))):
        with cam.view(c):
            B.room_back(c, t + 30, glow_a=0.85 if t < 1.0 else 0.0, wind=wd, wind_t0=WIND_T0, curtain_pull=wd,
                        poster_gone=poster_gone)
            B.stick_shadow(c, p, lit * 0.8)
            fx.portal(c, B.PORTAL[0], B.PORTAL[1], B.PORTAL_R * (1 + 0.1 * wd), t, power=pw, open_=op)
            B.bed_back(c, t)
            B.nightstand(c, t, papers_gone=sum(1 for i, f in enumerate(B.FLYERS) if f[0] == "paper" and t >= WIND_T0 + f[2]))
            B.bed_front(c, t)
            B.floor(c, t)
            for i in range(len(B.FLYERS)):
                x, y, r, s, u = B.flyer_pos(i, t, WIND_T0)
                if B.FLYERS[i][0] == "poster" and not poster_gone:
                    continue
                if B.FLYERS[i][0] in ("book", "plant") and t < WIND_T0 + B.FLYERS[i][2]:
                    continue
                if B.FLYERS[i][0] == "paper" and t < WIND_T0 + B.FLYERS[i][2]:
                    continue
                B.draw_flyer(c, i, x, y, r, s, pw)
            B.lit_overlay(c, t, lit, op)
            sm.draw(c, p, rim=B.portal_light_col(t), rim_a=min(0.9, 0.3 + 0.5 * lit), rim_dir=(-0.9, -0.35))
            if t < 7.8:
                path = B.blanket(c, t, sit=bsit, hump=bhump, flutter=0.0, lap_x=1270 + 40 * boff, cover_x1=1390)
                B.lit_clip(c, path, t, lit, op)
            else:
                path = B.blanket(c, t, sit=1.0, hump=0.4, flutter=wd * 0.8, lap_x=1330, cover_x1=1390)
                B.lit_clip(c, path, t, lit, op)
            # spark that bites the reaching hand
            if 11.95 <= t < 12.25:
                J = sm.joints(reach(11.95))
                fx.bolt(c, (B.PORTAL[0] + B.PORTAL_R * 0.95, B.PORTAL[1] - 20), J["hand_n"], int(t * 40), col=fx.PORTAL_C1,
                        a=1.0, width=3, glow_w=14)
            # wind streaks
            if wd > 0.05:
                for i in range(40):
                    k = hash01(i, 5)
                    life = 0.6 + 0.4 * k
                    age = ((t + k * 3) % life) / life
                    y = 300 + hash01(i, 6) * 560
                    x = lerp(1900, B.PORTAL[0] + 120, age)
                    yy = lerp(y, B.PORTAL[1], age ** 2)
                    c.drawLine(x, yy, x + 90 * (1 - age), yy + (y - B.PORTAL[1]) * 0.05, paint((0.7, 0.85, 1), 0.25 * wd * math.sin(math.pi * age), stroke=2))
            fx.ambient_motes(c, t, n=70, seed=4, col=B.portal_light_col(t), a=0.55, area=(80, 250, 1300, 880), size=(1.0, 3.2),
                             speed=14 + 60 * wd)
    if 1.0 <= t < 1.5:
        fx.flash(c, 0.55 * (1 - inv(t, 1.0, 1.5)), col=(0.75, 0.9, 1.0))
