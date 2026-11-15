"""The bedroom set (Act 1), shared by scenes 1-4. World units = pixels at zoom 1."""
import math

import skia

from engine.core import (W, H, TAU, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, ease_in, ease_out, keys, seg)
from engine import nature as N
from engine import fx
from engine import stickman as sm

FLOOR = 880
PORTAL = (430.0, 600.0)
PORTAL_R = 215.0
WINDOW = (1620, 270, 1860, 600)
BED = (1000, 1480)
MATTRESS_Y = 800
SCALE = 2.6          # stickman scale in the bedroom

WALL = "#18213b"
WALL_D = "#0f1528"
FLOOR_C = "#211c2a"
MOON = (0.62, 0.72, 1.0)


def portal_light_col(t):
    k = 0.5 + 0.5 * math.sin(t * 1.7)
    return mix(fx.PORTAL_C1, fx.PORTAL_C2, k * 0.6)


# ----------------------------------------------------------------- flying objects
# (id, kind, start position, release time offset)
FLYERS = [
    ("paper", (1570, 752), 0.0), ("paper", (1585, 750), 0.35), ("paper", (1560, 755), 0.8), ("paper", (1600, 748), 1.3),
    ("book", (1120, 545), 0.6), ("book", (1150, 545), 1.1), ("book", (1305, 545), 1.7),
    ("poster", (830, 425), 1.5),
    ("slipper", (1050, 874), 0.9), ("slipper", (1085, 874), 1.25),
    ("plant", (1335, 540), 2.1),
]


def flyer_pos(i, t, wind_t0):
    """Position, rotation and scale of flying object i at time t (None if not yet released)."""
    kind, (x0, y0), off = FLYERS[i]
    tr = wind_t0 + off
    if t < tr:
        return (x0, y0, 0.0, 1.0, 0.0)
    age = t - tr
    dur = 1.6 + 0.4 * hash01(i, 3)
    u = clamp(age / dur)
    e = ease_in(u)
    px, py = PORTAL
    # curve: lift up first, then swirl into the portal centre
    mx = lerp(x0, px, 0.5) + 80 * (hash01(i, 5) - 0.5)
    my = min(y0, py) - 120 - 100 * hash01(i, 6)
    x = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * mx + e * e * px
    y = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * my + e * e * py
    if kind == "slipper":
        y = lerp(y0, py, e * e)
        x = lerp(x0, px, e)
    swirl = e * e * 120 * math.sin(age * 9 + i)
    x += swirl * 0.3
    y += swirl * 0.2
    rot = age * (3 + 4 * hash01(i, 7)) * (1 if i % 2 else -1)
    sc = 1 - smooth(inv(u, 0.75, 1.0))
    return (x, y, rot, sc, u)


def draw_flyer(c, i, x, y, r, s, power):
    kind = FLYERS[i][0]
    if s <= 0.01:
        return
    with at(c, x, y, r, s):
        if kind == "paper":
            c.drawPath(poly([(-14, -18), (14, -16), (16, 18), (-12, 17)]), paint("#c9cfdf"))
            for k in range(4):
                c.drawLine(-8, -10 + k * 7, 9, -10 + k * 7, paint("#7c849e", stroke=1.2))
        elif kind == "book":
            c.drawRect(skia.Rect(-12, -22, 12, 22), paint(["#7a2e3a", "#2e5a7a", "#6a5a2a"][i % 3]))
            c.drawRect(skia.Rect(-12, -22, -8, 22), paint((0, 0, 0), 0.3))
        elif kind == "poster":
            _poster(c, -70, -95, 140, 190)
        elif kind == "slipper":
            c.drawPath(spline([(-22, 0), (-18, -10), (10, -12), (24, -6), (22, 4), (-20, 4)]), paint("#6a3d5a"))
        elif kind == "plant":
            c.drawPath(poly([(-12, 0), (12, 0), (9, 22), (-9, 22)]), paint("#8a4a32"))
            for k in range(5):
                a = -math.pi / 2 + (k - 2) * 0.4
                c.drawPath(N.taper((0, 0), (math.cos(a) * 28, math.sin(a) * 28), 4, 1.5) if hasattr(N, "taper") else skia.Path(),
                           paint("#3f7a3a"))


def _poster(c, x, y, w, h):
    c.drawRect(skia.Rect(x, y, x + w, y + h), paint("#3a2f28"))
    c.drawRect(skia.Rect(x + 8, y + 8, x + w - 8, y + h - 8), paint("#c2b79c"))
    # T-Rex skeleton sketch (foreshadowing)
    sk = (0.25, 0.22, 0.2)
    cx, cy = x + w * 0.5, y + h * 0.55
    p = paint(sk, 0.85, stroke=2.2)
    c.drawPath(spline([(cx - 50, cy - 5), (cx - 20, cy - 18), (cx + 10, cy - 20), (cx + 28, cy - 30)], closed=False), p)
    for k in range(7):
        xx = cx - 40 + k * 9
        c.drawLine(xx, cy - 12 - k * 0.8, xx + 2, cy + 2 - k * 0.6, paint(sk, 0.7, stroke=1.4))
    c.drawPath(poly([(cx + 24, cy - 40), (cx + 48, cy - 34), (cx + 44, cy - 24), (cx + 26, cy - 26)]), paint(sk, 0.85, stroke=2.2))
    c.drawLine(cx - 15, cy - 15, cx - 22, cy + 30, p)
    c.drawLine(cx - 22, cy + 30, cx - 12, cy + 50, p)
    c.drawLine(cx - 5, cy - 15, cx + 4, cy + 30, p)
    c.drawLine(cx + 4, cy + 30, cx - 2, cy + 50, p)
    c.drawLine(cx + 10, cy - 18, cx + 18, cy - 4, paint(sk, 0.85, stroke=1.5))


# ----------------------------------------------------------------- the room
def room_back(c, t, glow_a=0.0, power=0.0, wind=0.0, wind_t0=1e9, curtain_pull=0.0, poster_gone=False):
    """Wall, window, moonbeam, shelf, poster. Drawn before the bed and characters."""
    # wall
    c.drawRect(skia.Rect(-600, -400, 2600, FLOOR), paint(shader=lin((0, -100), (0, FLOOR), [(0, WALL_D), (0.6, WALL), (1, shade(WALL, -0.1))])))
    for i in range(-30, 140):
        x = i * 22
        c.drawLine(x, -400, x, FLOOR - 40, paint((0, 0, 0), 0.10 if i % 2 else 0.04, stroke=8))
    c.drawRect(skia.Rect(-600, FLOOR - 42, 2600, FLOOR), paint("#141a2c"))
    c.drawLine(-600, FLOOR - 42, 2600, FLOOR - 42, paint("#2b3656", stroke=3))
    # outlet & switch
    c.drawRect(skia.Rect(930, 690, 956, 726), paint("#2a3350"))
    c.drawRect(skia.Rect(1990, 560, 2016, 600), paint("#2a3350"))
    # window
    _window(c, t, curtain_pull)
    # shelf above bed
    c.drawRect(skia.Rect(1080, 560, 1370, 572), paint("#3b2c26"))
    c.drawPath(poly([(1100, 572), (1112, 572), (1112, 600)]), paint("#2c211c"))
    c.drawPath(poly([(1340, 572), (1352, 572), (1340, 600)]), paint("#2c211c"))
    gone_books = set()
    for i, (kind, pos, off) in enumerate(FLYERS):
        if kind in ("book", "plant") and t >= wind_t0 + off:
            gone_books.add(round(pos[0]))
    bx = 1100
    for k in range(9):
        w = 16 + (k * 7) % 9
        h = 40 + (k * 13) % 18
        if not any(abs(bx + w / 2 - g) < 14 for g in gone_books):
            c.drawRect(skia.Rect(bx, 560 - h, bx + w, 560), paint(["#5e2632", "#24496a", "#5c4c24", "#3b5a3a", "#4a3a5e"][k % 5]))
            c.drawRect(skia.Rect(bx + 3, 560 - h + 6, bx + w - 3, 560 - h + 9), paint((1, 1, 1), 0.15))
        bx += w + 2
    # toy dinosaur on the shelf
    if not any(abs(1335 - g) < 14 for g in gone_books):
        c.drawPath(poly([(1320, 540), (1350, 540), (1346, 558), (1324, 558)]), paint("#8a4a32"))
        for k in range(5):
            a = -math.pi / 2 + (k - 2) * 0.4
            sway = wind * 0.3 * math.sin(t * 20 + k)
            c.drawLine(1335, 540, 1335 + math.cos(a + sway) * 26, 540 + math.sin(a + sway) * 26, paint("#3f7a3a", stroke=4))
    # poster
    if not poster_gone:
        wob = wind * 0.05 * math.sin(t * 25)
        with at(c, 830, 330, wob):
            _poster(c, -70, 0, 140, 190)
    # wall glow (portal about to open)
    if glow_a > 0:
        px, py = PORTAL
        col = portal_light_col(t)
        glow(c, px, py, 380, col, glow_a * 0.55, blend="screen")
        glow(c, px, py, 140, (0.8, 0.95, 1), glow_a * 0.5, blend="add")
        for k in range(6):
            a = t * 0.8 + k * TAU / 6
            rr = 60 + 40 * math.sin(t * 1.3 + k)
            c.drawCircle(px + math.cos(a) * rr, py + math.sin(a) * rr * 0.9, 30, paint(col, glow_a * 0.25, blur=20, blend="add"))
    # moonbeam
    x0, y0, x1, y1 = WINDOW
    dx, dy = -430, 330
    beam = poly([(x0, y0), (x1, y0), (x1 + dx, y1 + dy), (x0 + dx, y1 + dy)])
    c.drawPath(beam, paint(shader=lin((x1, y0), (x0 + dx, y1 + dy), [(0, MOON, 0.16), (1, MOON, 0.02)]), blend="screen", blur=6))


def _window(c, t, pull):
    x0, y0, x1, y1 = WINDOW
    # night outside
    c.drawRect(skia.Rect(x0, y0, x1, y1), paint(shader=lin((0, y0), (0, y1), [(0, "#081028"), (1, "#22355e")])))
    c.save()
    c.clipRect(skia.Rect(x0, y0, x1, y1))
    r = Rng(4)
    for i in range(40):
        c.drawCircle(r.u(x0, x1), r.u(y0, y1 - 100), r.u(0.6, 1.6), paint((1, 1, 1), 0.5 + 0.4 * math.sin(t * r.u(1, 3) + i)))
    N.moon(c, 1790, 340, 30)
    c.drawPath(poly([(x0, y1), (x0, y1 - 60), (1680, y1 - 90), (1730, y1 - 70), (1790, y1 - 110), (1860, y1 - 80), (x1, y1)]),
               paint("#070b18"))
    c.restore()
    fr = paint("#2a2638")
    c.drawRect(skia.Rect(x0 - 14, y0 - 14, x1 + 14, y0), fr)
    c.drawRect(skia.Rect(x0 - 14, y1, x1 + 14, y1 + 18), fr)
    c.drawRect(skia.Rect(x0 - 14, y0, x0, y1), fr)
    c.drawRect(skia.Rect(x1, y0, x1 + 14, y1), fr)
    c.drawRect(skia.Rect((x0 + x1) / 2 - 6, y0, (x0 + x1) / 2 + 6, y1), fr)
    c.drawRect(skia.Rect(x0, (y0 + y1) / 2 - 5, x1, (y0 + y1) / 2 + 5), fr)
    c.drawPath(poly([(x0 + 30, y0 + 10), (x0 + 70, y0 + 10), (x0 + 10, y0 + 120), (x0 + 10, y0 + 60)]), paint((1, 1, 1), 0.06))
    # curtain rod & curtains
    c.drawRect(skia.Rect(x0 - 70, y0 - 50, x1 + 70, y0 - 42), paint("#3c3448"))
    for side, cx in ((-1, x0 - 30), (1, x1 + 30)):
        pts_l, pts_r = [], []
        for k in range(13):
            u = k / 12
            y = y0 - 45 + u * 450
            sway = 6 * math.sin(t * 0.8 + u * 3 + side) * u
            pull_x = -pull * (120 + 80 * u) * u * (1.0 if side < 0 else 1.6) * (1 + 0.2 * math.sin(t * 9 + u * 5))
            w = 40 + 15 * u
            pts_l.append((cx - w + sway + pull_x, y))
            pts_r.append((cx + w + sway + pull_x, y))
        path = spline(pts_l + list(reversed(pts_r)), tension=0.4)
        c.drawPath(path, paint(shader=lin((cx - 50, 0), (cx + 50, 0), [(0, "#2b1f3c"), (0.5, "#43305c"), (1, "#2b1f3c")])))
        for k in range(3):
            c.drawPath(poly([((pts_l[i][0] + pts_r[i][0]) / 2 + (k - 1) * 22, pts_l[i][1]) for i in range(13)], closed=False),
                       paint((0, 0, 0), 0.25, stroke=5, blur=3))


def bed_back(c, t):
    """Headboard, footboard back post and mattress (before the sleeper)."""
    # headboard
    c.drawPath(spline([(1478, 880), (1478, 680), (1488, 640), (1512, 636), (1520, 680), (1520, 880)], tension=0.3), paint("#3a2a26"))
    c.drawRect(skia.Rect(1484, 690, 1514, 860), paint("#2c201d"))
    # mattress and sheet
    c.drawRect(skia.Rect(1000, MATTRESS_Y, 1480, 842), paint(shader=lin((0, MATTRESS_Y), (0, 842), [(0, "#7884a8"), (1, "#4c5578")])))
    c.drawRect(skia.Rect(1000, 842, 1480, 862), paint("#3a2a26"))
    for x in (1010, 1462):
        c.drawRect(skia.Rect(x, 862, x + 14, FLOOR), paint("#2c201d"))
    # pillow
    c.drawPath(spline([(1372, 800), (1380, 774), (1420, 768), (1464, 776), (1470, 800)]), paint(shader=lin((0, 768), (0, 800), [(0, "#a3add0"), (1, "#717b9e")])))


def bed_front(c, t):
    # footboard (in front)
    c.drawPath(spline([(985, 880), (985, 750), (992, 728), (1010, 726), (1016, 750), (1016, 880)], tension=0.3), paint("#3f2e29"))


def blanket(c, t, cover_x1=1390, hump=1.0, breath=0.0, flutter=0.0, sit=0.0, lap_x=1270):
    """Blanket over the sleeper. sit moves it down to the lap; cover_x1 = right edge."""
    x0 = 1006
    top = MATTRESS_Y - 36 * hump - 6 * breath
    right = lerp(cover_x1, lap_x + 30, sit)
    pts = [(x0, 842), (x0 - 4, MATTRESS_Y - 4)]
    n = 8
    for k in range(n + 1):
        u = k / n
        x = lerp(x0 + 20, right, u)
        y = top + 10 * math.sin(u * 7 + 1) * (1 - sit * 0.5) - (8 * breath if u > 0.6 else 0)
        y += flutter * 10 * math.sin(t * 14 + u * 9)
        if sit > 0:
            y = lerp(y, MATTRESS_Y - 18 - 10 * math.sin(u * 5), sit)
        pts.append((x, y))
    pts += [(right + 14, MATTRESS_Y + 10), (right + 8, 842)]
    path = spline(pts, tension=0.35)
    c.drawPath(path, paint(shader=lin((0, top), (0, 845), [(0, "#4d62a8"), (1, "#25315e")])))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    for k in range(12):
        x = 1020 + k * 34
        c.drawLine(x, top - 20, x - 10, 860, paint((1, 1, 1), 0.05, stroke=10))
    c.drawPath(poly(pts[2:n + 3], closed=False), paint("#9fb0e8", 0.25, stroke=6, blur=4))
    c.restore()
    # folded hem
    c.drawLine(right - 2, MATTRESS_Y - 6, right + 10, 842, paint("#33437e", stroke=8))
    return path


def nightstand(c, t, papers_gone=0):
    c.drawRect(skia.Rect(1525, 760, 1640, 880), paint(shader=lin((1525, 0), (1640, 0), [(0, "#33261f"), (1, "#4a382c")])))
    c.drawRect(skia.Rect(1520, 752, 1645, 764), paint("#55402f"))
    c.drawRect(skia.Rect(1535, 790, 1630, 830), paint((0, 0, 0), 0.25))
    c.drawCircle(1583, 810, 4, paint("#a89060"))
    # lamp
    c.drawRect(skia.Rect(1540, 744, 1566, 752), paint("#2e2a36"))
    c.drawLine(1553, 744, 1553, 700, paint("#2e2a36", stroke=4))
    c.drawPath(poly([(1530, 700), (1576, 700), (1566, 668), (1540, 668)]), paint("#5a4e6e"))
    # clock with glowing digits
    c.drawRect(skia.Rect(1590, 728, 1636, 752), paint("#141420"))
    font = skia.Font(skia.Typeface("DejaVu Sans Mono"), 15)
    c.drawString("3:07", 1595, 746, font, paint((0.3, 1.0, 0.6), 0.9))
    glow(c, 1613, 740, 30, (0.3, 1.0, 0.6), 0.12)
    # paper stack
    for k in range(4 - papers_gone):
        c.drawRect(skia.Rect(1560 + k, 748 - k * 2, 1606 + k, 752 - k * 2), paint("#b8bed0"))


def floor(c, t, slippers=True):
    c.drawRect(skia.Rect(-600, FLOOR, 2600, FLOOR + 400), paint(shader=lin((0, FLOOR), (0, FLOOR + 240), [(0, "#2c2534"), (1, "#120f18")])))
    for i in range(-10, 60):
        x = i * 70
        c.drawLine(x, FLOOR, x - 40 - (x - 960) * 0.4, FLOOR + 400, paint((0, 0, 0), 0.25, stroke=2))
    # rug
    c.drawPath(poly([(560, FLOOR + 14), (1180, FLOOR + 14), (1250, FLOOR + 70), (500, FLOOR + 70)]), paint("#3b2440"))
    c.drawPath(poly([(580, FLOOR + 20), (1170, FLOOR + 20), (1230, FLOOR + 64), (520, FLOOR + 64)]), paint("#59345a", stroke=3))


def portal_shadow_wall(c, power, objects):
    """Long soft shadows on the wall, thrown away from the portal (to the right)."""
    if power <= 0.01:
        return
    with layer(c, a=0.5 * min(1, power), blur=10):
        for poly_pts in objects:
            c.drawPath(poly(poly_pts), paint((0, 0, 0), 1.0))


def lit_overlay(c, t, power, open_=1.0):
    """The portal's coloured light washing the room."""
    if power <= 0.01:
        return
    px, py = PORTAL
    col = portal_light_col(t)
    fl = 1 + 0.08 * math.sin(t * 13) + 0.05 * math.sin(t * 29)
    fx.light_overlay(c, px, py, 1250 * open_ + 200, col, 0.30 * power * fl, blend="screen")
    fx.light_overlay(c, px, py, 600 * open_ + 100, (0.85, 0.75, 1.0), 0.16 * power * fl, blend="screen")


def stick_shadow(c, pose, power):
    """The stickman's shadow on the wall, stretched away from the portal."""
    if power <= 0.02:
        return
    from dataclasses import replace
    q = replace(pose)
    dx = (q.x - PORTAL[0])
    q.x = q.x + dx * 0.35 + 30
    q.y = q.y - 40
    q.s = q.s * 1.25
    q.eye = 1.0
    with layer(c, a=0.45 * min(1.0, power), blur=8):
        sm.draw(c, q, ink=(0, 0, 0))


def lit_clip(c, path, t, power, open_=1.0):
    if path is None or power <= 0.01:
        return
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    lit_overlay(c, t, power, open_)
    c.restore()
