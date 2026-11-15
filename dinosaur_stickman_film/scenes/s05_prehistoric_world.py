"""Scene 5 - The Prehistoric World. A fall from the sky, a soft crash into grass,
then the camera pulls back to reveal an ancient, enormous, living world."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_out, ease_in, grade_cf, tint_cf, seg)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from engine import dino as D
from scenes import prehistoric as PH

DURATION = 22.0
XFADE = 0.0
CUES = {"white": 0.0, "fall": 0.4, "land": 3.0, "get_up": 4.0, "look": 6.0, "reveal": 7.2, "wide2": 13.5, "plant": 18.0,
        "touch": 19.6, "grass": 20.8}

PAL = PH.P("day")


# ----------------------------------------------------------------- shot A: falling
def shot_fall(c, t):
    u = inv(t, 0.0, 3.0)
    N.sky(c, [(0, "#3f8fd0"), (0.6, "#8cc4e6"), (1, "#d8ecf0")])
    N.sun(c, 1500, 160, 40, PAL["sun"])
    # clouds rising past the camera
    for i in range(9):
        h = [hash01(i, 17, k) for k in range(4)]
        y = 1400 - ((t * (500 + 400 * h[0]) + h[1] * 1600) % 2200)
        img = N.cloud_sprite(i % 6, lit="#ffffff", shadow="#a8b8cc")
        from engine.core import draw_img
        draw_img(c, img, h[2] * W, y, 1.0 + 1.6 * h[3], 0.85, ay=0.7)
    for i in range(30):
        h = [hash01(i, 19, k) for k in range(3)]
        y = H + 100 - ((t * 1400 * (0.6 + h[0]) + h[1] * 1300) % 1500)
        c.drawLine(h[2] * W, y, h[2] * W, y + 90, paint((1, 1, 1), 0.35, stroke=2))
    # canopy rushes up at the end
    if t > 2.2:
        k = ease_in(inv(t, 2.2, 3.0))
        y = lerp(H + 300, -200, k)
        for i in range(8):
            N.tree(c, "arauc", i, 120 + i * 240, y + 900 + 80 * hash01(i, 2), 1100, t, wind=0.02)
    p = sm.Pose(x=W / 2 + noise(t * 0.8, 3) * 80, y=H * 0.45 + 40 * math.sin(t * 1.3), s=3.2, f=1, rot=t * 2.4, torso=0.2,
                head=0.3 * math.sin(t * 6), sh_n=2.4 + 0.6 * math.sin(t * 9), el_n=0.5, sh_f=-2.2 + 0.6 * math.sin(t * 8),
                el_f=-0.3, hp_n=0.5 + 0.4 * math.sin(t * 7), kn_n=0.9, hp_f=-0.4 + 0.4 * math.sin(t * 7 + 2), kn_f=0.7,
                face=0.2, eye_s=1.5)
    sm.draw(c, p, rim=(1, 1, 1), rim_a=0.4, rim_dir=(0.6, -0.8))
    post.fade(c, 1 - smooth(inv(t, 0.0, 0.8)), col=(1, 1, 1))


# ----------------------------------------------------------------- shot B: crash and get up
GROUND_B = 880


def lie_down(t):
    p = sm.Pose(x=900, y=GROUND_B - 6, s=3.0, f=1, rot=math.pi / 2 - 0.05, head=0.2, sh_n=-0.2, el_n=0.2, sh_f=0.6, el_f=0.4,
                hp_n=0.15, kn_n=0.4, hp_f=-0.1, kn_f=0.2, face=0.6, eye=0.0)
    return p


def push_up(t):
    p = sm.Pose(x=905, y=0, s=3.0, f=1, rot=0.0, torso=1.15, head=-0.3, sh_n=1.4, el_n=0.15, sh_f=1.2, el_f=0.1,
                hp_n=0.1, kn_n=1.9, hp_f=0.0, kn_f=1.8, face=0.7, eye=0.5, eye_s=0.9)
    return sm.settle(p, GROUND_B, parts=("ft_n", "ft_f", "kn_n", "hand_n"))


def kneel(t):
    p = sm.Pose(x=910, y=0, s=3.0, f=1, torso=0.25, head=-0.1, sh_n=0.5, el_n=0.6, sh_f=0.2, el_f=0.4,
                hp_n=0.9, kn_n=1.6, hp_f=-0.05, kn_f=1.75, face=0.6, eye=0.8)
    return sm.settle(p, GROUND_B, parts=("ft_n", "ft_f", "kn_f"))


def stand_wobble(t):
    w = math.sin(t * 5) * (1 - smooth(inv(t, 5.4, 6.4)))
    p = sm.stand(x=915, y=0, s=3.0, f=1, torso=0.08 * w, head=0.15 * w, sh_n=0.35 + 0.3 * w, sh_f=-0.3 + 0.3 * w,
                 face=0.8, eye_s=1.05)
    p.x += 8 * w
    sm.settle(p, GROUND_B)
    return p


def look_around(t):
    p = stand_wobble(t)
    k = t - 6.0
    p.face = keys(t, [(6.0, 0.8), (6.5, -1.0), (7.0, -1.0), (7.2, 0.2)])
    p.head = -0.15 + 0.08 * math.sin(k * 2)
    p.eye_s = 1.25
    p.look = 0.4
    return sm.breathe(p, t, 0.3, 1.0)


TRACK_B = sm.Track([(3.0, lie_down), (4.0, lie_down), (4.8, push_up), (5.2, kneel), (5.7, stand_wobble), (6.0, look_around),
                    (7.2, look_around)])


def shot_ground(c, t):
    cam = Cam(960, 560, 1.0)
    cam.shake(t, 18 * math.exp(-max(0, t - 3.0) * 4) if t >= 3.0 else 0)
    cam.x = 960 + 30 * smooth(inv(t, 3.0, 7.2))
    with cam.view(c, 0.02):
        N.sky(c, PAL["sky"], -200, 900)
        N.sun(c, 420, 140, 50, PAL["sun"])
    with cam.view(c, 0.2):
        with layer(c, blur=6):
            PH.forest_band(c, cam, PAL, 640, 0.2, seed=3, haze_a=0.45, tall=1.3) if False else None
            img = N.forest_band_sprite(("fbB", 3), 3600, 420, mix(PAL["forest"][0], PAL["haze"], 0.45),
                                       mix(PAL["forest"][2], PAL["haze"], 0.4), mix(PAL["forest"][0], PAL["haze"], 0.45), seed=3, tall=1.4)
            c.drawImage(img, -800, 420)
    with cam.view(c, 0.45):
        with layer(c, blur=4):
            for i in range(6):
                N.tree(c, "broad" if i % 2 else "arauc", i + 3, -300 + i * 520, 900, 900 + 300 * hash01(i, 4), t, wind=0.01,
                       haze=PAL["haze"], haze_a=0.35)
    N.godrays(c, 420, 140, t, col=PAL["light"], a=0.14, n=8, spread=0.9, base_ang=1.0, length=2400)
    with cam.view(c, 1.0):
        PH.hill(c, [(-400, GROUND_B), (2400, GROUND_B)], PAL, t, grass=False)
        flat = lambda x: clamp(1 - abs(x - 900) / 260) * (1 - smooth(inv(t, 3.0, 6.0))) * (1.0 if t >= 3.0 else 0)
        N.grass(c, -300, 2300, GROUND_B + 4, t, seed=8, h=60, density=0.6, col=PAL["grass"][0], col2=PAL["grass"][1], flat=flat)
        for i, x in enumerate((300, 520, 1400, 1650)):
            N.fern(c, x, GROUND_B + 6, 200, 70 + i, t, wind=0.07, col=PAL["forest"][1], col2=PAL["forest"][2])
        p = TRACK_B(t)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.35, rim_dir=(-0.7, -0.7), shadow_y=GROUND_B + 2)
        if t >= 3.0:
            fx.dust(c, t, 3.0, 900, GROUND_B - 10, scale=1.6, col=(0.75, 0.72, 0.6), a=0.5, n=12, seed=4, spread=1.4)
            fx.leaves(c, t, 3.0, 900, GROUND_B - 30, 26, 7, spread=420, up=420, dur=3.5, size=8)
        N.grass(c, -300, 2300, GROUND_B + 30, t + 4, seed=9, h=40, density=0.4, col=shade(PAL["grass"][0], -0.1),
                col2=PAL["grass"][0])
    with layer(c, blur=10):
        N.grass(c, -100, 2100, H + 20, t, seed=11, h=180, density=0.08, col=shade(PAL["grass"][0], -0.35),
                col2=shade(PAL["grass"][0], -0.25))


# ----------------------------------------------------------------- shot C: the reveal
KNOLL = [(-900, 830), (-200, 815), (400, 828), (800, 836), (1080, 852), (1200, 930), (1260, 1300)]


def reveal_pose(t):
    x = 700
    gy = PH.ground_at(KNOLL, x)
    p = sm.stand(x=x, y=0, s=1.3, f=1, face=keys(t, [(7.2, 1.0), (9.0, 1.0), (9.8, 0.0), (10.6, 1.0)]),
                 head=keys(t, [(7.2, -0.1), (8.5, -0.3), (11.0, -0.35), (13.0, -0.2)]), eye_s=1.3)
    awe = smooth(inv(t, 10.6, 11.8))
    p.sh_n, p.el_n = 0.1 + 0.6 * awe, 0.2 + 0.3 * awe
    p.sh_f, p.el_f = -0.1 + 0.45 * awe, 0.3
    sm.settle(p, gy)
    return sm.breathe(p, t, 0.3, 1.0)


def world_layers(c, cam, t, pal, wide=True):
    PH.sky(c, cam, t, pal, sun=(1380, 170), sun_r=44, cloud_seed=2, cloud_y=170)
    N.godrays(c, *cam.to_screen(1380, 170, 0.02), t, col=pal["light"], a=0.1, n=9, spread=1.2, base_ang=2.1, length=2600)
    PH.far_mountains(c, cam, t, pal, y=330, p=0.08, seed=5, h=440, key="s5",
                     peaks=[(0.2, 0.9, 0.06), (0.32, 0.7, 0.05), (0.55, 0.95, 0.07), (0.78, 0.8, 0.06)])
    PH.volcano(c, cam, t, pal, x=1520, y=740, s=0.95, p=0.1, key="s5")
    PH.mid_mountains(c, cam, t, pal, y=520, p=0.18, seed=9, h=320, key="s5")
    PH.flock(c, cam, t, p=0.22, n=5, seed=3, area=(-300, 260, 2300, 420), scale=0.7, col=mix("#3b3433", pal["haze"], 0.4))
    PH.waterfall_cliff(c, cam, t, pal, x=430, top=470, bottom=760, width=120, p=0.3, seed=3, cliff_w=760)
    with cam.view(c, 0.32):
        N.mist(c, 720, t, col=(1, 1, 1), a=0.3, thick=60, seed=4)
    with cam.view(c, 0.4):
        N.ground_fill(c, -1500, 3500, 780, mix(pal["forest"][1], pal["haze"], 0.35), mix(pal["forest"][0], pal["haze"], 0.2), 900)
    PH.forest_band(c, cam, pal, 790, 0.38, seed=6, haze_a=0.3, tall=0.9)
    with cam.view(c, 0.42):
        PH.river(c, [(430, 770, 0.6), (700, 812, 0.8), (1000, 800, 1.0), (1350, 840, 1.2), (1700, 830, 1.3), (2300, 880, 1.6)],
                 70, t, pal)
    PH.herd(c, cam, t, pal, 0.45, 880, [1450, 1620, 1760], s=0.15, haze_a=0.45, f=-1, speed=4)
    PH.forest_band(c, cam, pal, 920, 0.55, seed=7, haze_a=0.18, tall=1.0)
    with cam.view(c, 0.55):
        N.mist(c, 900, t, col=(1, 1, 1), a=0.25, thick=50, seed=7, speed=10)


def shot_reveal(c, t):
    cam = Cam()
    u = ease_io(inv(t, 7.2, 13.3))
    cam.x = lerp(712, 960, u)
    cam.y = lerp(760, 480, u)
    cam.zoom = math.exp(lerp(math.log(3.4), math.log(0.8), u))
    world_layers(c, cam, t, PAL)
    with cam.view(c, 1.0):
        PH.hill(c, KNOLL, PAL, t, seed=21, gh=22, density=0.5)
        for i, x in enumerate((-500, -260, 260, 980)):
            N.fern(c, x, PH.ground_at(KNOLL, x) + 6, 120, 90 + i, t, wind=0.08, col=PAL["forest"][1], col2=PAL["forest"][2])
        N.rock(c, 1020, 852, 120, 60, 3, col=PAL["rock"][0], light="#e8dcc0")
        p = reveal_pose(t)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.4, rim_dir=(0.8, -0.6), shadow_y=PH.ground_at(KNOLL, 700) + 1)
    with cam.view(c, 1.15):
        N.tree(c, "broad", 1, -180, 1050, 1500, t, wind=0.015)
        N.tree(c, "tfern", 2, 2150, 1100, 900, t, wind=0.02, flip=True)
    PH.flock(c, cam, t, p=0.7, n=7, seed=8, area=(-200, 120, 2200, 360), ptero=False, scale=1.2, col="#2a2a30", speed=110)


# ----------------------------------------------------------------- shot D: second wide shot
def shot_wide2(c, t):
    cam = Cam()
    u = inv(t, 13.5, 18.0)
    cam.x, cam.y, cam.zoom = lerp(820, 1240, ease_io(u)), 520, 1.0
    PH.sky(c, cam, t, PAL, sun=(1500, 200), cloud_seed=5, cloud_y=150)
    PH.far_mountains(c, cam, t, PAL, y=360, p=0.06, seed=12, h=380, key="s5b",
                     peaks=[(0.15, 0.7, 0.05), (0.4, 0.95, 0.08), (0.7, 0.75, 0.05), (0.9, 0.9, 0.05)])
    PH.volcano(c, cam, t, PAL, x=300, y=720, s=0.8, p=0.08, key="s5b")
    PH.waterfall_cliff(c, cam, t, PAL, x=820, top=360, bottom=760, width=170, p=0.45, seed=8, cliff_w=900, haze_a=0.15)
    with cam.view(c, 0.5):
        N.ground_fill(c, 1270, 3600, 700, mix(PAL["grass"][0], PAL["haze"], 0.35), mix(PAL["forest"][1], PAL["haze"], 0.3), 300)
    PH.forest_band(c, cam, PAL, 700, 0.5, seed=12, haze_a=0.35, tall=0.7, x0=1250, w=3000)
    PH.herd(c, cam, t, PAL, 0.5, 745, [1500, 1700, 1880, 2050, 2250], s=0.2, haze_a=0.35, f=1, speed=6, seed=4)
    with cam.view(c, 0.6):
        N.water_band(c, -800, 3000, 760, 1100, t, top=PAL["water"][0], bot=PAL["water"][1], flow=30)
        N.mist(c, 770, t, col=(1, 1, 1), a=0.35, thick=70, seed=2, speed=12)
    PH.flock(c, cam, t, p=0.4, n=6, seed=11, area=(-200, 120, 2600, 380), scale=1.1)
    with cam.view(c, 1.0):
        PH.hill(c, [(-600, 960), (300, 940), (900, 990), (1500, 1000), (2600, 960)], PAL, t, seed=31, gh=34)
        for i, x in enumerate((-200, 150, 1700, 2050)):
            N.tree(c, "cycad", i, x, 990, 380, t, wind=0.03)
        for i, x in enumerate((60, 500, 1350, 1900)):
            N.fern(c, x, 1000, 180, 40 + i, t, wind=0.1, col=PAL["forest"][1], col2=PAL["forest"][2])


# ----------------------------------------------------------------- shot E: the strange plant
PLANT_X, GROUND_E = 1080, 900


def crouch_e(t):
    p = sm.Pose(x=880, y=0, s=2.6, f=1, torso=0.5, head=0.15, sh_n=0.3, el_n=0.5, sh_f=0.1, el_f=0.6,
                hp_n=1.3, kn_n=2.3, hp_f=1.0, kn_f=2.2, face=1.0, eye_s=1.15)
    sm.settle(p, GROUND_E)
    reach = smooth(inv(t, 18.8, 19.6)) * (1 - 0.5 * ease_out(inv(t, 19.75, 20.0)))
    J = sm.joints(p)
    tgt = (lerp(J["sh"][0] + 20, PLANT_X - 22, reach), lerp(J["sh"][1] + 60, GROUND_E - 150, reach))
    if t > 20.8:
        g = (t - 20.8)
        tgt = (lerp(J["sh"][0] + 40, 960 + 40 * math.sin(g * 3), smooth(inv(t, 20.8, 21.2))), GROUND_E - 40)
    sm.arm_ik(p, "n", tgt)
    p.head = 0.15 + 0.25 * smooth(inv(t, 20.2, 20.6)) * (1 - smooth(inv(t, 21.2, 21.6)))
    p.eye_s = 1.15 + 0.35 * smooth(inv(t, 19.7, 19.9)) * (1 - smooth(inv(t, 20.3, 20.8)))
    return p


def strange_plant(c, t):
    touched = smooth(inv(t, 19.6, 20.0))
    recover = smooth(inv(t, 20.6, 22.0))
    fold = touched * (1 - 0.8 * recover)
    x, y = PLANT_X, GROUND_E
    for i in range(5):
        a0 = -math.pi / 2 + (i - 2) * 0.32
        ln = 150 + 40 * hash01(i, 3)
        pts = []
        ang = a0
        px, py = x + (i - 2) * 6, y
        for k in range(14):
            pts.append((px, py))
            ang += (0.06 + 0.25 * (k / 13) ** 2 * (1 + fold * 1.5)) * (1 if i >= 2 else -1) * (0.6 + 0.4 * k / 13)
            px += math.cos(ang) * ln / 13
            py += math.sin(ang) * ln / 13
            if py > y:
                py = y
        c.drawPath(spline(pts, closed=False), paint("#2f5a2a", stroke=6))
        tip = pts[-1]
        pulse = 0.5 + 0.5 * math.sin(t * 3 + i) + 1.5 * bump_t(t, 19.6, 20.6)
        glow(c, tip[0], tip[1], 34, (1.0, 0.55, 0.85), 0.35 * pulse)
        c.drawCircle(tip[0], tip[1], 9 - 3 * fold, paint(mix((0.95, 0.4, 0.75), (1, 0.85, 0.5), 0.3 * pulse)))
        for k in range(3, 13, 2):
            q = pts[k]
            for s_ in (-1, 1):
                la = math.atan2(pts[k + 1][1] - q[1], pts[k + 1][0] - q[0]) + s_ * (1.2 - 1.0 * fold)
                ll = 26 * (1 - k / 16)
                c.drawPath(N.frond_path(q[0], q[1], la, ll, 0.3 * s_, 5, k, n=4)[0], paint("#4c8a3a"))


def bump_t(t, a, b):
    return math.sin(math.pi * inv(t, a, b)) if a < t < b else 0.0


def shot_plant(c, t):
    cam = Cam(970, 760, 2.0)
    cam.x += 15 * smooth(inv(t, 18.0, 22.0))
    with cam.view(c, 0.05):
        N.sky(c, PAL["sky"], -200, 900)
    with cam.view(c, 0.3):
        with layer(c, blur=9):
            img = N.forest_band_sprite(("fbE", 4), 3600, 420, mix(PAL["forest"][0], PAL["haze"], 0.35),
                                       mix(PAL["forest"][2], PAL["haze"], 0.3), mix(PAL["forest"][0], PAL["haze"], 0.35), seed=4, tall=1.6)
            c.drawImage(img, -600, 440)
    N.godrays(c, 300, 0, t, col=PAL["light"], a=0.12, n=6, spread=0.6, base_ang=1.1, length=2000)
    with cam.view(c, 1.0):
        PH.hill(c, [(-200, GROUND_E), (2200, GROUND_E)], PAL, t, grass=False)
        N.grass(c, 400, 1600, GROUND_E + 4, t, seed=12, h=40, density=0.7, col=PAL["grass"][0], col2=PAL["grass"][1],
                flat=lambda x: clamp(1 - abs(x - (960 + 40 * math.sin((t - 20.8) * 3))) / 60) * 0.6 if t > 20.9 else 0)
        N.fern(c, 640, GROUND_E + 4, 180, 5, t, wind=0.08, col=PAL["forest"][1], col2=PAL["forest"][2])
        strange_plant(c, t)
        p = crouch_e(t)
        sm.draw(c, p, rim=PAL["light"], rim_a=0.4, rim_dir=(-0.7, -0.7), shadow_y=GROUND_E + 2)
        fx.ambient_motes(c, t, n=24, seed=5, col=(1, 0.8, 0.95), a=0.6, area=(950, 650, 1250, 900), size=(1, 2.5), speed=8)
    with layer(c, blur=12):
        N.fern(c, 1700, H + 60, 420, 9, t, wind=0.08, col=shade(PAL["forest"][1], -0.4), col2=shade(PAL["forest"][2], -0.4))


def render(c, t):
    with layer(c, cf=grade_cf(sat=1.08, contrast=1.04, tint=(1.02, 1.0, 0.96))):
        if t < 3.0:
            shot_fall(c, t)
        elif t < 7.2:
            shot_ground(c, t)
        elif t < 13.5:
            shot_reveal(c, t)
        elif t < 18.0:
            shot_wide2(c, t)
        else:
            shot_plant(c, t)
