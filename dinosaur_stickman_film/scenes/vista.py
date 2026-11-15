"""The panoramic view from the mountain top (Acts 4-5). `doom` 0..1 turns the
golden evening into the red sky of the impact."""
import math

import skia

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, grade_cf, tint_cf, draw_img)
from engine import nature as N
from engine import fx
from engine import stickman as sm
from engine import dino as D
from scenes import prehistoric as PH

PAL = PH.P("sunset")
DOOM = PH.P("doom")
SUN = (1250, 560)
EDGE_Y = 840          # top of the cliff in the side shots
SIT_ROCK = (1000, EDGE_Y)


def sky_stops(doom):
    a = PAL["sky"]
    b = DOOM["sky"]
    out = []
    for i in range(len(b)):
        pa = a[min(i, len(a) - 1)]
        pb = b[i]
        out.append((pb[0], mix(pa[1], pb[1], doom)))
    return out


def doom_cf(doom):
    if doom <= 0.01:
        return None
    return grade_cf(sat=1.0 + 0.2 * doom, contrast=1.0 + 0.1 * doom, tint=(1.0 + 0.15 * doom, 1 - 0.45 * doom, 1 - 0.6 * doom),
                    bright=-0.12 * doom)


def panorama(c, cam, t, doom=0.0, herd_run=0.0, sun_a=1.0, flock_n=6, light=None):
    """Everything below and beyond the cliff."""
    with cam.view(c, 0.02):
        N.sky(c, sky_stops(doom), -300, 1000)
        if sun_a > 0:
            N.sun(c, SUN[0], SUN[1], 58, mix(PAL["sun"], (1, 0.6, 0.3), doom), sun_a * (1 - 0.5 * doom))
    sx, sy = cam.to_screen(*SUN, 0.02)
    N.godrays(c, sx, sy, t, col=mix(PAL["light"], (1, 0.4, 0.15), doom), a=0.15 * (1 - 0.4 * doom), n=12, spread=3.0,
              base_ang=4.0, length=2600)
    with layer(c, cf=doom_cf(doom)):
        with cam.view(c, 0.05):
            N.clouds(c, t, [(-300, 200, 1.2, 5, 1), (500, 120, 0.9, 4, 2), (1300, 260, 1.3, 6, 3), (2000, 150, 1.0, 5, 4)],
                     lit=PAL["cl"], shadow=PAL["cs"], a=0.9)
        PH.far_mountains(c, cam, t, PAL, y=380, p=0.05, seed=81, h=300, key="vista",
                         peaks=[(0.15, 0.7, 0.06), (0.3, 0.9, 0.05), (0.62, 0.8, 0.07), (0.85, 1.0, 0.06)])
        with cam.view(c, 0.08):
            N.water_band(c, -1500, 3500, 640, 700, t, top="#ffd9a0", bot="#c98a6a", flow=6, sparkle=(1, 0.95, 0.8), sparkle_a=0.7,
                         density=1.5)
        PH.waterfall_cliff(c, cam, t, PAL, x=420, top=560, bottom=650, width=46, p=0.1, seed=91, cliff_w=520, haze_a=0.45)
        PH.mid_mountains(c, cam, t, PAL, y=560, p=0.13, seed=83, h=200, key="vista", forest=True)
        PH.forest_band(c, cam, PAL, 735, 0.2, seed=84, haze_a=0.35, tall=0.6)
        with cam.view(c, 0.25):
            N.ground_fill(c, -2000, 4000, 728, mix(PAL["grass"][0], PAL["haze"], 0.4), mix(PAL["forest"][1], PAL["haze"], 0.2), 900)
            PH.river(c, [(-200, 760, 0.5), (300, 790, 0.7), (800, 770, 0.9), (1200, 820, 1.2), (1500, 900, 1.6), (1900, 1000, 2.2),
                         (2400, 1080, 2.6)], 50, t, dict(PAL, water=("#ffd29a", "#a87a6a")))
        PH.herd(c, cam, t + herd_run * 30, PAL, 0.27, 800, [700, 820, 960, 1080, 1180], s=0.07, haze_a=0.35,
                f=-1, speed=4 + 40 * herd_run, seed=13)
        PH.herd(c, cam, t + herd_run * 30, PAL, 0.32, 860, [1500, 1650, 1800], s=0.09, haze_a=0.3, f=-1,
                speed=4 + 50 * herd_run, seed=14)
        PH.forest_band(c, cam, PAL, 900, 0.38, seed=85, haze_a=0.2, tall=0.8)
        with cam.view(c, 0.38):
            N.mist(c, 870, t, col=(1, 0.85, 0.7), a=0.25, thick=50, seed=5, speed=6)
        PH.flock(c, cam, t, p=0.15, n=flock_n, seed=41, area=(-300, 300, 2300, 520), scale=0.55,
                 col=mix("#3a2a2e", PAL["haze"], 0.3), speed=40 + 120 * herd_run)


def cliff_front(c, cam, t, doom=0.0, rock=True):
    """The mountain top in the foreground, falling away to the right."""
    with cam.view(c, 1.0):
        with layer(c, cf=doom_cf(doom)):
            pts = [(-2000, EDGE_Y), (1200, EDGE_Y + 4), (1290, EDGE_Y + 30), (1330, EDGE_Y + 160), (1370, EDGE_Y + 420),
                   (1420, 2400), (-2000, 2400)]
            c.drawPath(poly(pts), paint(shader=lin((0, EDGE_Y), (0, EDGE_Y + 500), [(0, "#8a6a52"), (1, "#3a2a20")])))
            c.drawPath(poly(pts[:4], closed=False), paint((1.0, 0.8, 0.5), 0.55, stroke=7, blur=4))
            r = Rng(5)
            for k in range(30):
                x = r.u(-1500, 1300)
                y = EDGE_Y + r.u(30, 600)
                c.drawLine(x, y, x + r.u(-90, 90), y + r.u(10, 50), paint((0, 0, 0), 0.15, stroke=r.u(2, 6)))
            for k in range(6):
                x = -900 + k * 330
                N.grass(c, x, x + 120, EDGE_Y + 3, t, seed=k + 7, h=22, density=0.5, col="#8a8a3a", col2="#b0a050", wind=0.3)
            if rock:
                c.drawPath(spline([(SIT_ROCK[0] - 110, EDGE_Y + 2), (SIT_ROCK[0] - 100, EDGE_Y - 46), (SIT_ROCK[0] + 40, EDGE_Y - 56),
                                   (SIT_ROCK[0] + 130, EDGE_Y - 42), (SIT_ROCK[0] + 140, EDGE_Y + 2)], tension=0.4),
                           paint(shader=lin((0, EDGE_Y - 56), (0, EDGE_Y), [(0, "#b08a66"), (1, "#5a4232")])))
                c.drawPath(poly([(SIT_ROCK[0] - 100, EDGE_Y - 46), (SIT_ROCK[0] + 40, EDGE_Y - 56), (SIT_ROCK[0] + 130, EDGE_Y - 42)],
                                closed=False), paint((1.0, 0.85, 0.6), 0.6, stroke=5, blur=3))


ROCK_TOP = EDGE_Y - 54


def sit_pose(x=None, breath=0.0, head=0.25, **kw):
    """Sitting on the flat rock, legs over its front edge, facing the view (right)."""
    p = sm.Pose(x=x if x is not None else SIT_ROCK[0] + 20, y=ROCK_TOP - 2, s=1.6, f=1, torso=0.2, head=head, sh_n=0.5, el_n=0.6,
                sh_f=0.35, el_f=0.7, hp_n=1.45, kn_n=1.5, hp_f=1.35, kn_f=1.4, face=1.0, eye=1.0)
    for k, v in kw.items():
        setattr(p, k, v)
    p.breath = breath
    p.torso += 0.05 * breath
    return p


def draw_back_sitting(c, x, y, s, breath=0.0, head_up=0.0, rim=(1.0, 0.75, 0.4), rim_a=0.6, stand=0.0):
    """The stickman seen from behind, sitting (or standing) and facing the view."""
    lw = sm.LW * s
    hip = (x, y - stand * 40 * s)
    neck = (x, hip[1] - (sm.TORSO + breath * 1.2) * s)
    head = (x, neck[1] - (sm.NECK + sm.HEAD_R) * s - head_up * 2 * s)
    sh = (x, neck[1] + 2.5 * s)
    arms = [[(x - 2 * s, sh[1]), (x - 8.5 * s, sh[1] + 15 * s - breath * 1.5 * s), (x - 6 * s, sh[1] + 24 * s - breath * s)],
            [(x + 2 * s, sh[1]), (x + 8.5 * s, sh[1] + 15 * s - breath * 1.5 * s), (x + 6 * s, sh[1] + 24 * s - breath * s)]]
    if stand > 0:
        arms = [[(x - 2 * s, sh[1]), (x - 7 * s, sh[1] + 15 * s), (x - 8 * s, sh[1] + 29 * s)],
                [(x + 2 * s, sh[1]), (x + 7 * s, sh[1] + 15 * s), (x + 8 * s, sh[1] + 29 * s)]]
    legs = []
    if stand > 0:
        legs = [[hip, (x - 6 * s, hip[1] + sm.THIGH * s * stand), (x - 7 * s, hip[1] + sm.LEG * s * stand)],
                [hip, (x + 6 * s, hip[1] + sm.THIGH * s * stand), (x + 7 * s, hip[1] + sm.LEG * s * stand)]]
    strokes = arms + legs + [[hip, neck]]
    for q in strokes:
        c.drawPath(poly(q, closed=False), paint(rim, rim_a, stroke=lw * 1.9, blur=lw * 0.5))
    c.drawCircle(head[0], head[1], sm.HEAD_R * s + lw * 0.45, paint(rim, rim_a, blur=lw * 0.5))
    for q in strokes:
        c.drawPath(poly(q, closed=False), paint(sm.INK, stroke=lw))
    c.drawCircle(head[0], head[1], sm.HEAD_R * s, paint(sm.INK))


def back_view(c, t, cam, doom=0.0, breath=0.0, head_up=0.0, stand=0.0, herd_run=0.0, extra=None, figure=True):
    """From behind the sitting stickman, looking out over the world."""
    panorama(c, cam, t, doom=doom, herd_run=herd_run)
    if extra:
        extra(c, cam)
    if not figure:
        return
    with cam.view(c, 1.0):
        with layer(c, cf=doom_cf(doom)):
            c.drawPath(spline([(400, H + 200), (520, 900), (760, 860), (1160, 870), (1400, 930), (1560, H + 200)], tension=0.4),
                       paint(shader=lin((0, 860), (0, H), [(0, "#6a4c3a"), (1, "#2a1c14")])))
            c.drawPath(poly([(520, 900), (760, 860), (1160, 870), (1400, 930)], closed=False), paint((1.0, 0.8, 0.5), 0.5, stroke=6, blur=4))
        draw_back_sitting(c, 960, 900, 5.0, breath=breath, head_up=head_up, stand=stand,
                          rim=mix((1.0, 0.75, 0.4), (1.0, 0.35, 0.15), doom))
