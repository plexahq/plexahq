"""Scene 17 - The Final Image. Silence. Ash falls on an empty, changed world.
Title and closing line."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, grade_cf, text_centered, taper)
from engine import nature as N
from engine import fx, post
from scenes import prehistoric as PH
from scenes import vista as V

DURATION = 20.0
CUES = {"black": 0.0, "ashland": 2.5, "fade_out": 11.0, "title": 12.5, "tagline": 16.7, "end": 20.0}

PAL = PH.P("ash")
GY = 880


def stump(c, x, y, h, seed, lean=0.0, col="#120e0d"):
    """A burnt, broken tree: thin trunk, jagged top, a couple of dead branches."""
    r = Rng(seed)
    w = 6 + h * 0.035
    top = (x + lean * h, y - h)
    pts = [(x - w, y), (top[0] - w * 0.55, top[1] + r.u(0, 10)), (top[0] - w * 0.2, top[1] - r.u(8, 30)),
           (top[0] + w * 0.15, top[1] - r.u(0, 12)), (top[0] + w * 0.5, top[1] - r.u(10, 40)), (top[0] + w * 0.6, top[1] + 6),
           (x + w, y)]
    c.drawPath(poly(pts), paint(col))
    for k in range(r.i(1, 4)):
        u = r.u(0.35, 0.85)
        bx, by = x + lean * h * u, y - h * u
        side = r.choice([-1, 1])
        ln = r.u(0.15, 0.35) * h
        c.drawPath(poly([(bx, by - w * 0.4), (bx + side * ln, by - ln * r.u(0.3, 0.9)), (bx, by + w * 0.4)]), paint(col))
    if r.u() < 0.45:
        ey = y - h * r.u(0.05, 0.4)
        glow(c, x + lean * (y - ey), ey, 10 + w, (1, 0.35, 0.05), 0.45)


def ash_land(c, t):
    u = inv(t, 2.5, 11.0)
    cam = Cam(lerp(820, 1120, ease_io(u)), lerp(560, 540, u), lerp(1.08, 1.0, u))
    with cam.view(c, 0.02):
        N.sky(c, PAL["sky"], -300, 1000)
        glow(c, 1300, 560, 900, (0.9, 0.35, 0.15), 0.3)
        glow(c, 1300, 560, 220, (1.0, 0.55, 0.3), 0.45)
        c.drawCircle(1300, 560, 50, paint((1.0, 0.62, 0.42), 0.55))
    with cam.view(c, 0.06):
        for i in range(6):
            fx.billow(c, -300 + i * 500, 300 + 60 * math.sin(i), 260, 40 + i, (0.18, 0.15, 0.14), 0.7)
    PH.far_mountains(c, cam, t, PAL, y=440, p=0.06, seed=81, h=300, key="ash",
                     peaks=[(0.15, 0.7, 0.06), (0.3, 0.9, 0.05), (0.62, 0.8, 0.07), (0.85, 1.0, 0.06)])
    with cam.view(c, 0.2):
        N.ground_fill(c, -2000, 4000, 700, "#4a3a34", "#221c1a", 900)
        for i in range(26):
            x = -600 + i * 130 + 60 * hash01(i, 3)
            stump(c, x, 705, 40 + 90 * hash01(i, 4), i, lean=(hash01(i, 5) - 0.5) * 0.5, col="#3a2a26")
        N.smoke(c, 300, 690, t, scale=0.8, col=(0.25, 0.23, 0.22), a=0.5, drift=60, rise=100, n=12, seed=2)
        N.smoke(c, 1500, 700, t + 3, scale=1.0, col=(0.25, 0.23, 0.22), a=0.5, drift=60, rise=120, n=12, seed=3)
    with cam.view(c, 0.45):
        N.ground_fill(c, -2000, 4000, 790, "#3a302c", "#161212", 900)
        for i in range(9):
            x = -700 + i * 400 + 150 * hash01(i, 6)
            stump(c, x, 795, 120 + 220 * hash01(i, 7), 100 + i, lean=(hash01(i, 8) - 0.5) * 0.4, col="#1c1514")
        for i in range(4):
            x = -300 + i * 700 + 200 * hash01(i, 9)
            c.drawPath(taper((x, 790), (x + 260, 784 + 10 * hash01(i, 3)), 12, 9), paint("#1c1514"))
        fx.embers(c, t, -600, 2800, 795, n=50, seed=4, a=0.7, area_h=260)
    with cam.view(c, 1.0):
        # the mountain top again: the same flat rock, empty, under ash
        pts = [(-2000, GY), (900, GY + 4), (1250, GY + 30), (1310, GY + 200), (1350, 2400), (-2000, 2400)]
        c.drawPath(poly(pts), paint(shader=lin((0, GY), (0, GY + 400), [(0, "#3a3330"), (1, "#141110")])))
        c.drawPath(poly(pts[:3], closed=False), paint((0.75, 0.72, 0.7), 0.35, stroke=6, blur=3))
        rx = 700
        c.drawPath(spline([(rx - 110, GY + 2), (rx - 100, GY - 46), (rx + 40, GY - 56), (rx + 130, GY - 42), (rx + 140, GY + 2)],
                          tension=0.4), paint(shader=lin((0, GY - 56), (0, GY), [(0, "#4a4440"), (1, "#24201e")])))
        c.drawPath(poly([(rx - 100, GY - 48), (rx + 40, GY - 58), (rx + 130, GY - 44)], closed=False),
                   paint((0.8, 0.78, 0.76), 0.5, stroke=6, blur=2))
        stump(c, 150, GY + 4, 300, 7, lean=-0.15)
        stump(c, -250, GY + 4, 420, 8, lean=0.1)
    fx.ash(c, t, n=420, seed=7, a=0.75, speed=45, wind=18)
    post.fade(c, 1 - smooth(inv(t, 2.5, 4.5)))
    post.fade(c, smooth(inv(t, 10.0, 11.0)))


def titles(c, t):
    c.drawRect(skia.Rect(-10, -10, W + 10, H + 10), paint("#050404"))
    fx.ash(c, t, n=140, seed=9, a=0.25, speed=25, wind=8, size=(1, 2.5))
    a1 = smooth(inv(t, 12.6, 13.9)) * (1 - smooth(inv(t, 15.7, 16.5)))
    if a1 > 0:
        glow(c, W / 2, H / 2 - 10, 700, (0.9, 0.45, 0.2), 0.10 * a1)
        text_centered(c, "THE LAST DAY OF THE DINOSAURS", W / 2, H / 2 + 30, 88, (0.98, 0.9, 0.8), a=a1 * 0.35, track=0.12,
                      blur=10)
        text_centered(c, "THE LAST DAY OF THE DINOSAURS", W / 2, H / 2 + 30, 88, (0.96, 0.92, 0.86), a=a1, track=0.12)
        w = 760 * smooth(inv(t, 13.0, 14.2))
        c.drawLine(W / 2 - w / 2, H / 2 + 80, W / 2 + w / 2, H / 2 + 80, paint((0.9, 0.55, 0.3), 0.6 * a1, stroke=1.5))
    a2 = smooth(inv(t, 16.7, 17.6)) * (1 - smooth(inv(t, 19.0, 19.9)))
    if a2 > 0:
        text_centered(c, "ONE JOURNEY. ONE WORLD. ONE FINAL MOMENT.", W / 2, H / 2 + 16, 40, (0.9, 0.86, 0.8), a=a2, track=0.24,
                      face="cinzel-r")


def render(c, t):
    if t < 2.5:
        c.drawRect(skia.Rect(-10, -10, W + 10, H + 10), paint((0, 0, 0)))
        return
    if t < 11.0:
        with layer(c, cf=grade_cf(sat=0.6, contrast=1.05, tint=(1.03, 0.98, 0.95))):
            ash_land(c, t)
        return
    titles(c, t)
