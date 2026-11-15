"""Scene 8 - Run For Your Life. The chase through the forest."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_out, ease_in, grade_cf, seg, taper)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import prehistoric as PH

DURATION = 23.0
CUES = {"side": 0.0, "front": 5.5, "logs": 9.0, "jump1": 9.9, "jump2": 11.3, "close": 12.5, "glance": 13.4,
        "fallen": 14.5, "slide": 15.6, "crash": 17.0, "snap": 17.6, "wide": 20.0}

PAL = PH.P("chase")
REX = D.Theropod(D.REX)
RS = 1.5
GY = 900
SS = 1.8           # stickman scale
VS = 720.0         # stickman sprint speed (px/s)
RUN = D.REX["run"]


def rex_phase_for(dist):
    return dist * RUN["duty"] / (RUN["stride"] * RS)


def stick_run(x, dist, **kw):
    p = sm.gait(dist * sm.GAITS["sprint"]["duty"] / (sm.GAITS["sprint"]["stride"] * SS), x, GY, SS, 1, "sprint")
    p.face, p.eye_s = 1.0, 1.55
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def rex_run(x, dist, t, **kw):
    P = dict(x=x, gy=GY, s=RS, f=1, t=t, gait="run", phase=rex_phase_for(dist), neck_up=0.05, head_pitch=0.2,
             jaw=0.25 + 0.2 * math.sin(t * 3), tail_lift=0.05)
    P.update(kw)
    return P


def step_shake(t, dist0, vr):
    """Camera shake synced to the T-Rex's footfalls."""
    ph = rex_phase_for(dist0 + vr * t)
    k = (ph * 2) % 1.0
    return 10 * math.exp(-k * 6)


# ----------------------------------------------------------------- A: side tracking with crashing bushes
BUSHES_A = [1400, 2300, 3300, 4200, 5200]


def xr_side(t):
    return 600 + VS * t - 1100 + 120 * smooth(inv(t, 2.0, 5.0))


MOUTH_OFF = REX.mouth_world(dict(x=0, gy=GY, s=RS, f=1, t=0, gait="run", phase=0.0, neck_up=0.05, head_pitch=0.2))[0]


def _hit_time(bx):
    t = 0.0
    while t < 30:
        if xr_side(t) + MOUTH_OFF >= bx - 120:
            return t
        t += 0.01
    return 99.0


HIT_A = [_hit_time(bx) for bx in BUSHES_A]


def shot_side(c, t):
    xs = 600 + VS * t
    xr = xr_side(t)
    cam = Cam(xs - 380, 660, 0.92)
    cam.shake(t, step_shake(t, 0, VS))
    PH.forest_world(c, cam, t, PAL, GY, seed=21, sun=(300, 0), rays=0.1, dark=0.15,
                    shake_trees=lambda x: clamp(1 - abs(x - (xr + 300)) / 500))
    with cam.view(c, 1.0):
        for i, bx in enumerate(BUSHES_A):
            th = HIT_A[i]
            if t < th:
                N.bush(c, bx, GY + 12, 120, 50 + i, pal=PAL["forest"], shake=clamp(1 - abs(xr + 500 - bx) / 400), t=t)
            else:
                fx.leaves(c, t, th, bx, GY - 60, 30, 60 + i, col=PAL["forest"], spread=600, up=500, dur=2.2, size=10, wind=500)
                fx.burst(c, t, th, bx, GY - 40, 16, 70 + i, speed=(300, 800), ang=(-2.6, -0.4), grav=1400, life=(0.6, 1.2),
                         size=(3, 6), col=(0.3, 0.22, 0.14), streak=0.02)
        P = rex_run(xr, xr, t)
        REX.draw(c, P, light=PAL["light"], light_a=0.3, haze=PAL["haze"], haze_a=0.05, dark=0.1)
        p = stick_run(xs, xs)
        p.face = -0.9 if 3.0 < t < 3.5 else 1.0
        sm.draw(c, p, rim=PAL["light"], rim_a=0.3, rim_dir=(-0.6, -0.8), shadow_y=GY + 1)
    PH.forest_foreground(c, cam, t, PAL, GY, seed=22, blur=12, p=1.5, dark=0.55)


# ----------------------------------------------------------------- B: front, low angle
def shot_front(c, t):
    u = t - 5.5
    cam_shake = 0.0
    ph_r = u * 1.6
    k = (ph_r * 2) % 1.0
    cam_shake = 16 * math.exp(-k * 5) * smooth(inv(u, 0.2, 0.6))
    shx, shy = noise(t * 14, 3) * cam_shake, noise(t * 14, 9) * cam_shake
    c.save()
    c.translate(shx, shy)
    # backdrop: dark forest receding behind
    N.sky(c, [(0, "#4a6a70"), (1, "#9aa98a")])
    with layer(c, blur=8):
        PH.forest_world(c, Cam(960 + u * 20, 560, 1.0 + 0.04 * u), t, PAL, 860, seed=23, rays=0.12, dark=0.25, ferns=False,
                        trunks=False)
    N.godrays(c, 960, -100, t, col=PAL["light"], a=0.12, n=7, base_ang=1.57, spread=0.8)
    # ground with a perspective path
    c.drawPath(poly([(0, 860), (W, 860), (W, H), (0, H)]), paint(shader=lin((0, 860), (0, H), [(0, PAL["ground"][0]), (1, PAL["ground"][1])])))
    c.drawPath(poly([(880, 860), (1040, 860), (1500, H), (420, H)]), paint((0.35, 0.3, 0.2), 0.35))
    # side trunks receding (camera tracks backwards)
    for i in range(10):
        h = [hash01(i, 41, k_) for k_ in range(3)]
        z = 0.35 + ((h[0] * 3 + u * 0.9) % 3.0)
        side = -1 if i % 2 else 1
        X = side * (700 + 500 * h[1])
        sx = 960 + X / z
        w = 160 / z
        top = 860 - 2200 / z
        col = mix("#3a2c22", PAL["haze"], clamp((z - 0.5) / 4) * 0.6)
        bl = max(0.0, 10 - z * 6)
        with layer(c, blur=bl):
            c.drawPath(poly([(sx - w * 0.5, 860 + 60 / z), (sx - w * 0.36, top), (sx + w * 0.36, top), (sx + w * 0.5, 860 + 60 / z)]),
                       paint(shader=lin((sx - w / 2, 0), (sx + w / 2, 0), [(0, shade(col, -0.35)), (0.65, col), (1, shade(col, 0.15))])))
            for k_ in range(5):
                bx = sx + (hash01(i, k_, 3) - 0.5) * w * 0.6
                c.drawLine(bx, top, bx + 4 / z, 860, paint((0, 0, 0), 0.25, stroke=max(1, 8 / z)))
    # the T-Rex charging behind
    rs = lerp(0.95, 1.35, smooth(inv(u, 0.0, 3.5)))
    with layer(c, blur=2.5):
        D.rex_front(c, 960 + noise(t * 0.8, 4) * 40, 900, rs, ph_r, jaw=0.55 + 0.25 * math.sin(t * 4), t=t, light=PAL["light"],
                    light_a=0.25, haze=PAL["haze"], haze_a=0.15, dark=0.25)
    for i in range(3):
        fx.dust(c, t, 5.5 + i * 0.8, 960 + (i - 1) * 140, 900, scale=1.4, col=(0.45, 0.42, 0.34), a=0.5, n=8, seed=i + 9)
    # the stickman in front, running at the camera
    sm.draw_front(c, 960 + 30 * math.sin(u * 2.1), 900, 7.0, u * 2.6, look_back=0.0, eye_s=1.55, rim=PAL["light"], rim_a=0.35)
    with layer(c, blur=14):
        N.grass(c, -100, W + 100, H + 30, t, seed=5, h=150, density=0.12, col=shade(PAL["grass"][0], -0.4),
                col2=shade(PAL["grass"][0], -0.3), wind=0.6)
    c.restore()


# ----------------------------------------------------------------- C: jumping over logs
LOGS = [(2000 + VS * (tj - 9.0), tj) for tj in (9.9, 11.3)]   # (world x, time the stickman clears it)
LOG_HIT = [9.0 + (lx - 1360) / VS for lx, tj in LOGS]


def log_shape(c, x, y, ln, r, broken=0.0, t=0.0, t0=0.0, seed=1):
    if broken <= 0:
        c.drawPath(taper((x - ln / 2, y - r), (x + ln / 2, y - r), r, r * 0.9), paint("#4a3626"))
        c.drawPath(taper((x - ln / 2, y - r * 1.3), (x + ln / 2, y - r * 1.3), r * 0.35, r * 0.3), paint("#6a5038", 0.6))
        ellipse(c, x + ln / 2, y - r, r * 0.35, r * 0.9, paint("#8a6a48"))
        return
    for k, side in enumerate((-1, 1)):
        age = t - t0
        px = x + side * ln / 4 + side * 220 * age
        py = y - r - 300 * age + 900 * age * age
        py = min(py, y - r)
        with at(c, px, py, side * age * 4):
            c.drawPath(taper((-ln / 4, 0), (ln / 4, 0), r, r * 0.9), paint("#4a3626"))


def shot_logs(c, t):
    xs = 2000 + VS * (t - 9.0)
    xr = xs - 900
    cam = Cam(xs - 250, 650, 0.9)
    cam.shake(t, step_shake(t, 100, VS))
    PH.forest_world(c, cam, t, PAL, GY, seed=24, sun=(500, 0), rays=0.1, dark=0.15,
                    shake_trees=lambda x: clamp(1 - abs(x - (xr + 300)) / 500))
    p = stick_run(xs, xs)
    for lx, tj in LOGS:
        if abs(t - tj) < 0.32:
            u = (t - tj + 0.32) / 0.64
            p.y -= math.sin(math.pi * u) * 95
            p.hp_n, p.kn_n = 1.3, 2.0
            p.hp_f, p.kn_f = 0.4, 1.6
            p.torso = 0.45
            p.sh_n, p.sh_f = 1.6, -0.6
    with cam.view(c, 1.0):
        P = rex_run(xr, xr, t)
        for i, (lx, tj) in enumerate(LOGS):
            th = LOG_HIT[i]
            if t < th:
                log_shape(c, lx, GY + 6, 360, 34)
            else:
                log_shape(c, lx, GY + 6, 360, 34, broken=1, t=t, t0=th)
                fx.burst(c, t, th, lx, GY - 30, 24, 80 + i, speed=(300, 900), ang=(-2.8, -0.3), grav=1500, life=(0.5, 1.2),
                         size=(3, 7), col=(0.42, 0.3, 0.2), streak=0.02)
                fx.dust(c, t, th, lx, GY, scale=1.5, col=(0.45, 0.4, 0.32), a=0.5, n=10, seed=i + 30)
        REX.draw(c, P, light=PAL["light"], light_a=0.3, haze=PAL["haze"], haze_a=0.05, dark=0.1)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.3, rim_dir=(-0.6, -0.8), shadow_y=GY + 1)
    PH.forest_foreground(c, cam, t, PAL, GY, seed=25, blur=12, p=1.5, dark=0.55)


# ----------------------------------------------------------------- D: close on the runner
def shot_close(c, t):
    xs = 6000 + VS * (t - 12.5)
    p = stick_run(xs, xs)
    glance = smooth(inv(t, 13.3, 13.5)) * (1 - smooth(inv(t, 13.9, 14.1)))
    p.face = lerp(1.0, -1.0, glance)
    p.look = -glance
    p.head = -0.12 - 0.15 * glance
    p.eye_s = 1.6 + 0.2 * glance
    J = sm.joints(p)
    cam = Cam(J["neck"][0] + 20, J["neck"][1] + 10, 3.6)
    cam.shake(t, 8 + step_shake(t, 0, VS))
    with cam.view(c, 0.25):
        with layer(c, blur=14):
            PH.forest_world(c, Cam(xs, 560, 1.0), t, PAL, GY, seed=26, rays=0.15, dark=0.15)
    with cam.view(c, 1.0):
        sm.draw(c, p, rim=PAL["light"], rim_a=0.4, rim_dir=(-0.6, -0.8))
    # streaks of blurred foliage whipping past
    for i in range(6):
        h = [hash01(i, 51, k) for k in range(3)]
        x = W + 400 - ((t * 2600 + h[0] * 3000) % (W + 1200))
        with layer(c, blur=20):
            N.fern(c, x, H + 100 + 80 * h[1], 500, 60 + i, t, col=shade(PAL["forest"][0], -0.5), col2=shade(PAL["forest"][1], -0.5))


# ----------------------------------------------------------------- E: slide under the fallen tree
TREE_X = 9000
SLIDE_T0, SLIDE_T1 = 15.55, 16.35


def stick_e(t):
    x = TREE_X - 900 + VS * (t - 14.5) - 120 * smooth(inv(t, SLIDE_T0, SLIDE_T1))
    if t < SLIDE_T0 - 0.15:
        return stick_run(x, x)
    slide = sm.Pose(x=x, y=0, s=SS, f=1, rot=0.0, torso=-0.95, head=0.4, sh_n=-1.2, el_n=0.4, sh_f=-1.0, el_f=0.5,
                    hp_n=1.45, kn_n=0.15, hp_f=1.1, kn_f=0.9, face=1.0, eye_s=1.6)
    sm.settle(slide, GY, parts=("ft_n", "ft_f", "hip", "hand_n"))
    if t < SLIDE_T0:
        return sm.blend(stick_run(x, x), slide, smooth(inv(t, SLIDE_T0 - 0.15, SLIDE_T0)))
    if t < SLIDE_T1:
        return slide
    return sm.blend(slide, stick_run(x, x), smooth(inv(t, SLIDE_T1, SLIDE_T1 + 0.25)))


CRASH_T = 17.0


def rex_e(t):
    xr = TREE_X - 1850 + 690 * (t - 14.5)
    if t > CRASH_T:
        xr -= 60 * smooth(inv(t, CRASH_T, CRASH_T + 0.3)) - 60 * smooth(inv(t, CRASH_T + 0.3, CRASH_T + 0.9))
    P = rex_run(xr, xr, t)
    if CRASH_T + 0.45 < t < CRASH_T + 0.95:
        k = math.sin(math.pi * inv(t, CRASH_T + 0.45, CRASH_T + 0.95))
        P["neck_up"] = -0.1 * k
        P["jaw"] = 0.25 + 0.7 * (1 - k)
        P["pitch"] = 0.12 * k
    return P


def fallen_tree(c, t):
    """Big trunk resting on a boulder across the path."""
    y = GY - 150
    if t < CRASH_T:
        N.rock(c, TREE_X + 260, GY + 6, 180, 120, 7, col=PAL["rock"][0], light=PAL["light"], moss=PAL["forest"][1])
        c.drawPath(taper((TREE_X - 900, GY - 20), (TREE_X + 520, y - 30), 60, 46), paint(shader=lin((0, y - 80), (0, y + 60),
                   [(0, "#5a4430"), (1, "#2e2218")])))
        for k in range(12):
            u = k / 12
            x0 = lerp(TREE_X - 860, TREE_X + 480, u)
            y0 = lerp(GY - 20, y - 30, u)
            c.drawLine(x0, y0 - 40, x0 + 30, y0 + 30, paint((0, 0, 0), 0.25, stroke=3))
        c.drawPath(blob(TREE_X - 300, GY - 70, 60, 3, 8, 0.4, 0.5), paint(PAL["forest"][1], 0.9))
        return
    N.rock(c, TREE_X + 260, GY + 6, 180, 120, 7, col=PAL["rock"][0], light=PAL["light"], moss=PAL["forest"][1])
    age = t - CRASH_T
    for k, (a, b, sp) in enumerate((((TREE_X - 900, GY - 20), (TREE_X - 120, y + 60), -1), ((TREE_X - 80, y + 40), (TREE_X + 520, y - 30), 1))):
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        dx = sp * (320 * age if k else 120 * age)
        dy = -380 * age + 1100 * age * age if k else 160 * age * age
        dy = min(dy, GY - 40 - cy)
        with at(c, cx + dx, cy + dy, sp * age * (3.0 if k else 0.6)):
            c.drawPath(taper((a[0] - cx, a[1] - cy), (b[0] - cx, b[1] - cy), 58, 46), paint("#4a3626"))
            ellipse(c, (b[0] - cx) if sp < 0 else (a[0] - cx), (b[1] - cy) if sp < 0 else (a[1] - cy), 22, 50, paint("#c8a070"))


def shot_tree(c, t):
    p = stick_e(t)
    P = rex_e(t)
    cam = Cam(lerp(TREE_X - 300, p.x - 300, smooth(inv(t, 16.2, 18.5))), 620, 0.95)
    cs = step_shake(t, 0, 690) * 0.6
    if t >= CRASH_T:
        cs += 30 * math.exp(-(t - CRASH_T) * 3)
    cam.shake(t, cs)
    PH.forest_world(c, cam, t, PAL, GY, seed=27, sun=(700, 0), rays=0.12, dark=0.15,
                    shake_trees=lambda x: clamp(1 - abs(x - (P["x"] + 300)) / 500) + (0.8 if abs(x - TREE_X) < 500 and t > CRASH_T else 0))
    with cam.view(c, 1.0):
        REX.draw(c, P, light=PAL["light"], light_a=0.3, haze=PAL["haze"], haze_a=0.05, dark=0.1)
        fallen_tree(c, t)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.3, rim_dir=(-0.6, -0.8), shadow_y=GY + 1)
        if SLIDE_T0 <= t < SLIDE_T1 + 0.6:
            fx.dust(c, t, SLIDE_T0, p.x - 30, GY, scale=0.8, col=(0.5, 0.45, 0.35), a=0.4, n=6, seed=3, dirx=-0.5)
        if t >= CRASH_T:
            fx.burst(c, t, CRASH_T, TREE_X - 100, GY - 160, 60, 91, speed=(400, 1300), ang=(-2.9, -0.2), grav=1500, life=(0.6, 1.6),
                     size=(3, 9), col=(0.5, 0.36, 0.22), streak=0.02)
            fx.leaves(c, t, CRASH_T, TREE_X - 100, GY - 200, 50, 92, col=PAL["forest"], spread=900, up=600, dur=3.0, size=10)
            fx.dust(c, t, CRASH_T, TREE_X - 100, GY - 40, scale=2.6, col=(0.45, 0.4, 0.32), a=0.55, n=14, seed=93, spread=1.5)
    PH.forest_foreground(c, cam, t, PAL, GY, seed=28, blur=12, p=1.5, dark=0.55)


# ----------------------------------------------------------------- F: wide shot
def shot_wide(c, t):
    u = t - 20.0
    xs = 14000 + VS * u
    xr = xs - 1000
    cam = Cam(xs - 500, 520, 0.55)
    cam.shake(t, step_shake(t, 0, VS) * 0.4)
    PH.forest_world(c, cam, t, PAL, GY, seed=29, sun=(900, -200), rays=0.14, dark=0.1, density=0.7,
                    shake_trees=lambda x: clamp(1 - abs(x - (xr + 300)) / 700))
    with cam.view(c, 1.0):
        REX.draw(c, rex_run(xr, xr, t), light=PAL["light"], light_a=0.3, haze=PAL["haze"], haze_a=0.08)
        sm.draw(c, stick_run(xs, xs), shadow_y=GY + 1)
        for i in range(22):
            h = [hash01(i, 61, k) for k in range(4)]
            age = u - h[0] * 0.8
            if age < 0:
                continue
            bx = xr + 200 + h[1] * 1200 + (-300 + 600 * h[2]) * age
            by = 200 + h[3] * 300 - 400 * age
            D.bird(c, bx, by, 3.0, age * 6 + h[1], col="#1d2220")
    PH.flock(c, cam, t, p=0.6, n=4, seed=17, area=(xs - 2000, -400, xs + 1500, -100), scale=1.6, speed=200)


def render(c, t):
    with layer(c, cf=grade_cf(sat=0.92, contrast=1.12, tint=(0.97, 1.0, 0.95), bright=-0.03)):
        if t < 5.5:
            shot_side(c, t)
        elif t < 9.0:
            shot_front(c, t)
        elif t < 12.5:
            shot_logs(c, t)
        elif t < 14.5:
            shot_close(c, t)
        elif t < 20.0:
            shot_tree(c, t)
        else:
            shot_wide(c, t)
