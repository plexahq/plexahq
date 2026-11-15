"""Scene 1 - A Quiet Night. Exterior of the house under the moon, push in through
the bedroom window, the stickman asleep."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly,
                         spline, blob, ellipse, glow, layer, at, inv, seg, keys, ease_in, ease_io, grade_cf, tint_cf)
from engine import nature as N
from engine import fx, post
from engine import stickman as sm
from scenes import bedroom as B

DURATION = 17.0
CUES = {"fade_in": 0.0, "window_push": 9.0, "inside": 11.0, "shift": 14.6}

BEDROOM_WINDOW = (1262, 452)


def sleeper(t, breath_rate=0.22):
    """Stickman asleep on its back, head on the pillow (right)."""
    b = 0.5 + 0.5 * math.sin(t * TAU * breath_rate)
    shift = smooth(inv(t, 14.6, 15.6)) - smooth(inv(t, 15.6, 16.6)) * 0.4
    p = sm.Pose(x=1300 + 4 * shift, y=792, s=B.SCALE, f=-1, rot=-math.pi / 2, torso=0.0, head=-0.05 - 0.12 * shift,
                sh_n=0.05, el_n=0.1, sh_f=0.05, el_f=0.1,
                hp_n=0.0, kn_n=0.02, hp_f=0.03, kn_f=0.05, face=0.0, eye=0.0, breath=b)
    return p, b


def sleeper_arm(c, p, t, shift=0.0):
    """The near arm resting on top of the blanket (drawn after the blanket)."""
    J = sm.joints(p)
    sh = J["sh"]
    b = p.breath
    el = (sh[0] - 40, B.MATTRESS_Y - 42 - 5 * b - 6 * shift)
    hd = (sh[0] - 92 - 10 * shift, B.MATTRESS_Y - 36 - 6 * b)
    c.drawPath(poly([sh, el, hd], closed=False), paint(sm.INK, stroke=sm.LW * p.s))


def house(c, t):
    wall = "#27314d"
    roof = "#161a28"
    trim = "#6274a3"
    # chimney
    c.drawRect(skia.Rect(1370, 210, 1420, 320), paint("#2a2c3c"))
    N.smoke(c, 1395, 205, t, scale=0.6, col=(0.45, 0.5, 0.62), a=0.25, drift=80, rise=90, n=10)
    # walls
    c.drawRect(skia.Rect(920, 360, 1480, 820), paint(shader=lin((920, 0), (1480, 0), [(0, shade(wall, 0.12)), (1, shade(wall, -0.2))])))
    for k in range(24):
        y = 370 + k * 19
        c.drawLine(920, y, 1480, y, paint((0, 0, 0), 0.18, stroke=2))
    # roof
    c.drawPath(poly([(880, 372), (1200, 170), (1520, 372), (1500, 384), (1200, 196), (900, 384)]), paint("#2a3049"))
    c.drawPath(poly([(892, 370), (1200, 180), (1508, 370), (1200, 196)]), paint(roof))
    c.drawPath(poly([(880, 372), (1200, 170)], closed=False), paint((0.75, 0.82, 1.0), 0.55, stroke=4, blur=2))
    # windows
    for (wx, wy, ww, wh, lit) in ((1060, 452, 110, 130, 0), (BEDROOM_WINDOW[0], BEDROOM_WINDOW[1], 110, 130, 1),
                                   (1060, 650, 110, 120, 0)):
        c.drawRect(skia.Rect(wx - ww / 2 - 8, wy - wh / 2 - 8, wx + ww / 2 + 8, wy + wh / 2 + 8), paint(trim))
        c.drawRect(skia.Rect(wx - ww / 2, wy - wh / 2, wx + ww / 2, wy + wh / 2),
                   paint(shader=lin((0, wy - wh / 2), (0, wy + wh / 2), [(0, "#0b1226"), (1, "#1e2c50")])))
        if lit:
            c.drawRect(skia.Rect(wx - ww / 2, wy - wh / 2, wx + ww / 2, wy + wh / 2), paint((0.35, 0.45, 0.8), 0.12))
            # curtains inside
            c.drawRect(skia.Rect(wx - ww / 2, wy - wh / 2, wx - ww / 2 + 22, wy + wh / 2), paint("#2b1f3c"))
            c.drawRect(skia.Rect(wx + ww / 2 - 22, wy - wh / 2, wx + ww / 2, wy + wh / 2), paint("#2b1f3c"))
        c.drawLine(wx, wy - wh / 2, wx, wy + wh / 2, paint(trim, stroke=6))
        c.drawLine(wx - ww / 2, wy, wx + ww / 2, wy, paint(trim, stroke=6))
        c.drawPath(poly([(wx - ww / 2 + 10, wy - wh / 2), (wx - ww / 2 + 40, wy - wh / 2), (wx - ww / 2, wy - 10)]),
                   paint((1, 1, 1), 0.08))
        c.drawRect(skia.Rect(wx - ww / 2 - 14, wy + wh / 2 + 8, wx + ww / 2 + 14, wy + wh / 2 + 16), paint(trim))
    # door + porch light
    c.drawRect(skia.Rect(1250, 640, 1340, 820), paint("#3a2a2a"))
    c.drawCircle(1325, 735, 4, paint("#c9a45a"))
    c.drawRect(skia.Rect(1236, 626, 1354, 640), paint(trim))
    glow(c, 1380, 660, 140, (1.0, 0.75, 0.4), 0.35)
    c.drawRect(skia.Rect(1374, 648, 1386, 668), paint((1, 0.9, 0.6)))
    # steps
    c.drawRect(skia.Rect(1236, 820, 1354, 836), paint("#3b3f52"))


def exterior(c, t):
    cam = Cam()
    push = keys(t, [(0, (960, 540, 1.0)), (9.0, (1150, 500, 1.32))], fn=ease_io)
    if t > 9.0:
        u = ease_in(inv(t, 9.0, 11.3))
        push = (lerp(1150, BEDROOM_WINDOW[0], u), lerp(500, BEDROOM_WINDOW[1], u), 1.32 * (1 + u * 6.5))
    cam.x, cam.y, cam.zoom = push
    # sky
    with cam.view(c, 0.05):
        N.sky(c, [(0, "#04081a"), (0.55, "#0e1a3c"), (0.85, "#1f3260"), (1, "#2c4272")], -200, 900)
        N.stars(c, t, seed=2, n=380, y1=700)
        N.moon(c, 700, 150, 58)
    with cam.view(c, 0.12):
        N.clouds(c, t, [(-200, 300, 0.9, 9, 1), (330, 120, 0.6, 7, 2), (1500, 260, 1.0, 7, 3), (2100, 160, 0.8, 8, 4)],
                 lit=(0.42, 0.5, 0.75), shadow=(0.10, 0.13, 0.24), a=0.85)
    with cam.view(c, 0.3):
        hills = N.mountain_sprite("night_hills1", 11, 3200, 400, "#16203c", "#0d1428", (0.4, 0.5, 0.8), rough=0.5,
                                  sun_dir=-1)
        c.drawImage(hills, -600, 480)
        c.drawCircle(300, 760, 3, paint((1, 0.8, 0.5), 0.7))
        c.drawCircle(1700, 740, 2.5, paint((1, 0.8, 0.5), 0.6))
    with cam.view(c, 0.55):
        hills2 = N.mountain_sprite("night_hills2", 23, 3400, 300, "#0f1730", "#0a0f20", (0.4, 0.5, 0.8), rough=0.45,
                                   sun_dir=-1)
        c.drawImage(hills2, -700, 640)
        for i in range(10):
            N.tree(c, "arauc" if i % 3 else "broad", i, -500 + i * 330, 860, 260 + 60 * hash01(i, 1), t, wind=0.01,
                   dark=0.75, haze=(0.08, 0.12, 0.24), haze_a=0.3)
    with cam.view(c, 1.0):
        N.ground_fill(c, -800, 2800, 815, "#18223a", "#0a0e1a", 500)
        house(c, t)
        # fence
        for i in range(-12, 36):
            x = i * 60
            if 880 < x < 1520:
                continue
            c.drawRect(skia.Rect(x, 760, x + 14, 840), paint("#2a3049"))
        c.drawRect(skia.Rect(-800, 778, 880, 788), paint("#2a3049"))
        c.drawRect(skia.Rect(1520, 778, 2800, 788), paint("#2a3049"))
        N.tree(c, "broad", 1, 420, 860, 760, t, wind=0.025, dark=0.55, haze=(0.1, 0.14, 0.3), haze_a=0.25)
        N.tree(c, "broad", 2, 1830, 870, 640, t + 3, wind=0.025, dark=0.6, haze=(0.1, 0.14, 0.3), haze_a=0.25, flip=True)
        for i, (bx, by, br) in enumerate(((880, 830, 70), (1540, 832, 80), (760, 840, 60), (1660, 845, 70))):
            N.bush(c, bx, by, br, 40 + i, pal=("#0d1424", "#16213a", "#23345a"))
        N.grass(c, -800, 2800, 900, t, seed=4, h=40, density=0.5, col="#101a2e", col2="#1a2742", wind=0.3)
        fx.ambient_motes(c, t, n=18, seed=9, col=(0.75, 1.0, 0.45), a=0.8, area=(300, 600, 1800, 880), size=(1.5, 3.2), speed=10)
    # moonlight wash
    fx.light_overlay(c, *cam.to_screen(700, 150, 0.05), 1400, (0.4, 0.5, 0.9), 0.18)


def interior(c, t):
    """Inside the bedroom: from the window, the camera drifts across to the sleeper."""
    cam = Cam()
    x, y, z = keys(t, [(10.6, (1700, 470, 1.9)), (13.5, (1420, 640, 1.45)), (17.0, (1330, 690, 1.55))], fn=ease_io)
    cam.x, cam.y, cam.zoom = x, y, z
    p, b = sleeper(t)
    with cam.view(c):
        B.room_back(c, t)
        B.bed_back(c, t)
        B.nightstand(c, t)
        sm.draw(c, p, rim=(0.5, 0.6, 0.95), rim_a=0.35, rim_dir=(0.6, -0.8))
        B.blanket(c, t, breath=b)
        sleeper_arm(c, p, t, smooth(inv(t, 14.6, 15.6)) - 0.4 * smooth(inv(t, 15.6, 16.6)))
        B.bed_front(c, t)
        B.floor(c, t)
        # slippers
        for k, sx in enumerate((1050, 1085)):
            c.drawPath(spline([(sx - 22, 874), (sx - 18, 864), (sx + 10, 862), (sx + 24, 868), (sx + 22, 878), (sx - 20, 878)]),
                       paint("#4a2d44"))
        fx.ambient_motes(c, t, n=25, seed=3, col=(0.7, 0.8, 1.0), a=0.25, area=(1100, 300, 1900, 850), size=(0.8, 1.8), speed=6)


def render(c, t):
    with layer(c, cf=grade_cf(sat=0.9, contrast=1.05, tint=(0.92, 0.98, 1.08))):
        if t < 11.3:
            exterior(c, t)
        if t >= 10.4:
            a = smooth(inv(t, 10.4, 11.3))
            with layer(c, a=a):
                interior(c, t)
    post.fade(c, 1 - smooth(inv(t, 0.0, 2.8)))
