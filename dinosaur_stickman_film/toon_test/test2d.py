#!/usr/bin/env python3
"""Illustrated-style test (12.5 s): same beats and timing as the 3D test, so the same
soundtrack (with the character's reactions) lines up.

  python3 toon_test/test2d.py stills 2 5.6 9.3 11.5
  python3 toon_test/test2d.py video        # -> final/test_2d.mp4
"""
import math
import os
import subprocess
import sys
from multiprocessing import get_context

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "film3d"))

import skia  # noqa: E402

from engine.core import (W, H, TAU, Cam, clamp, lerp, smooth, noise, hash01, Rng, rgb, mix, shade, paint, lin, rad, poly, spline,
                         blob, ellipse, glow, layer, at, inv, keys, ease_io, ease_out, ease_in, grade_cf)  # noqa: E402
from engine import stickman as sm, hero2d as hero, toon, toon_dino as TD, toon_nature as TN, fx, post  # noqa: E402
from engine import dino as D  # noqa: E402
import test_scene as T3  # noqa: E402  (timeline shared with the 3D test)

FPS = 24
DUR = T3.DURATION
GY = 880
S_A = 2.5
REX = D.Theropod(D.REX)


# ----------------------------------------------------------------- shared backdrop
def backdrop(c, cam, t, haze=0.0, birds_t0=None):
    with cam.view(c, 0.02):
        TN.sky(c)
        glow(c, 1500, 160, 520, (1.0, 0.92, 0.6), 0.55, blend="screen")
        c.drawCircle(1500, 160, 52, paint((1.0, 0.97, 0.82)))
    with cam.view(c, 0.05):
        TN.clouds(c, t, [(-200, 210, 0.75, 6, 0), (520, 120, 0.6, 4, 1), (1250, 250, 0.85, 5, 2), (2000, 150, 0.7, 6, 3)])
    with cam.view(c, 0.08):
        img = TN.mountain_sprite("m1", 7, 3600, 420, "#8aa3d8", snow=0.22,
                                 peaks=[(0.15, 0.8, 0.05), (0.33, 1.0, 0.06), (0.6, 0.85, 0.05), (0.82, 0.95, 0.06)])
        c.drawImage(img, -900, 360)
        TN.volcano(c, 1560, 760, 0.85, t)
    with cam.view(c, 0.14):
        img = TN.mountain_sprite("m2", 11, 4200, 300, "#5fa48a", snow=0.0, peaks=[(0.3, 0.7, 0.12), (0.7, 0.8, 0.1)], lw=2.6,
                                 ink_col=(0.18, 0.3, 0.3))
        c.drawImage(img, -1200, 560)
    # distant forest band
    with cam.view(c, 0.25):
        for i in range(-14, 34):
            x = i * 120 + hash01(i, 2) * 80
            TN.tree(c, "broad" if hash01(i, 3) > 0.35 else "arauc", i, x, 820, 260 + 90 * hash01(i, 4), t, haze=(0.62, 0.8, 0.85),
                    haze_a=0.42)
    if birds_t0 is not None and t > birds_t0:
        for i in range(16):
            h_ = [hash01(i, 41, k) for k in range(4)]
            age = t - birds_t0 - h_[0] * 0.4
            if age > 0:
                bx, by = cam.to_screen(600 + h_[1] * 900 + (h_[2] - 0.5) * 500 * age, 520 - 300 * age, 0.25)
                D.bird(c, bx, by, 1.8 + h_[3], age * 6 + h_[1], col=(0.12, 0.12, 0.16))
    with cam.view(c, 0.5):
        TN.meadow(c, cam.left(0.5) - 200, cam.right(0.5) + 200, 840, 120, t, seed=5, density=0.6, flowers=False)
        for i in range(-6, 16):
            x = i * 330 + hash01(i, 6) * 140
            TN.tree(c, "broad" if i % 3 else "arauc", i + 20, x, 860, 520 + 160 * hash01(i, 7), t, haze=(0.7, 0.86, 0.9), haze_a=0.2)
        for i in range(-4, 12):
            x = i * 470 + 200
            c.save()
            c.translate(x, 862)
            c.scale(0.6, 0.6)
            img = TN.tree_fern_sprite(i % 3)
            c.drawImage(img, -img.width() / 2, -img.height(), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
            c.restore()


def sunrays(c, t, a=0.16):
    from engine import nature as N
    N.godrays(c, 1500, 120, t, col=(1.0, 0.92, 0.65), a=a, n=9, spread=1.3, base_ang=2.0, length=2600)


def ground(c, cam, t, shake_x=None):
    with cam.view(c, 1.0):
        l, r = cam.left() - 300, cam.right() + 300
        TN.meadow(c, l, r, GY - 40, 900, t, seed=8, density=1.2)
        for i in range(int(l // 700) - 1, int(r // 700) + 2):
            x = i * 700 + hash01(i, 21) * 300
            ellipse(c, x, GY - 30, 260, 26, paint((0.12, 0.35, 0.12), 0.35, blur=10))
        TN.dirt_path(c, [(l, GY - 6), (r, GY - 10)], [(l, GY + 46), (r, GY + 40)], lw=3.0)
        for i in range(int(l // 600) - 1, int(r // 600) + 2):
            x = i * 600 + hash01(i, 9) * 300
            if hash01(i, 10) < 0.5:
                TN.rock(c, x, GY - 12, 120, 70, i, lw=3.2)
            else:
                TN.bush(c, x, GY - 20, 90, i + 50, lw=3.2, shake=shake_x(x) if shake_x else 0, t=t)
            TN.fern(c, x + 260, GY - 18, 120, i + 70, t, lw=2.6)


# ----------------------------------------------------------------- shot A: walking into the clearing
def hero_a(t):
    dx = (T3.WALK.x(t) - T3.WALK.x(0.0)) / T3.S3 * S_A
    x = 420 + dx
    p = sm.gait(T3.WALK.phase(t), x, GY + 14, S_A, 1, "walk")
    ooh = math.sin(math.pi * inv(t, 2.3, 3.3)) if 2.3 < t < 3.3 else 0.0
    p.face = 1.0
    p.head = -0.08 - 0.2 * ooh + 0.05 * math.sin(t * 1.3)
    p.look = 0.3 * math.sin(t * 1.3)
    p.look_y = -0.4 * ooh
    blink = any(a < t < a + 0.12 for a in (1.3, 3.6))
    expr = dict(eye=0.0 if blink else 1.0, smile=0.5 * (1 - ooh), mouth=0.28 * ooh, eye_s=1.0 + 0.12 * ooh, brow_up=0.6 * ooh)
    return p, expr


def shot_a(c, t):
    p, expr = hero_a(t)
    cam = Cam(p.x + 260, 560, 1.0)
    backdrop(c, cam, t)
    ground(c, cam, t)
    with cam.view(c, 1.0):
        hero.side(c, p, expr, shadow_y=GY + 14)
    with cam.view(c, 1.35):
        l = cam.left(1.35)
        for i in range(int(l // 520) - 1, int(cam.right(1.35) // 520) + 2):
            x = i * 520 + hash01(i, 12) * 200
            TN.fern(c, x, H + 140, 260, i + 90, t, lw=4.0, dark=0.25)
        TN.grass_tufts(c, l - 200, cam.right(1.35) + 200, H + 60, t, seed=4, h=120, col="#3f9a32", lw=1.6, spacing=130)


# ----------------------------------------------------------------- shot B: close-up, the ground shakes
def thump(t):
    a = 0.0
    for tt, k in ((T3.CUES["thump1"], 1.0), (T3.CUES["thump2"], 0.85)):
        if t >= tt:
            a = max(a, k * math.exp(-(t - tt) * 5))
    return a


def shot_b(c, t):
    sh = thump(t)
    cam = Cam(1400, 520, 1.0)
    cam.shake(t, 22 * sh)
    with layer(c, blur=9):
        backdrop(c, cam, t, birds_t0=T3.CUES["thump1"] + 0.1)
        ground(c, cam, t)
    fear = smooth(inv(t, 5.35, 5.6))
    turn = smooth(inv(t, 6.4, 7.2))
    face0 = lerp(0.8, 0.0, smooth(inv(t, 4.2, 4.7))) + 0.3 * math.sin((t - 4.2) * 1.8) * (1 - fear) * smooth(inv(t, 4.6, 4.9))
    face = lerp(face0, -0.95, turn)
    gasp = math.sin(math.pi * inv(t, 5.38, 5.9)) if 5.38 < t < 5.9 else 0.0
    blink = 4.9 < t < 5.02
    expr = dict(face=face, eye=0.0 if blink else 1.0, eye_s=1.0 + 0.32 * fear, brow_up=fear, brow_in=0.7 * fear,
                mouth=0.5 * gasp + 0.15 * fear, smile=0.5 * (1 - fear), look=0.5 * math.sin((t - 4.2) * 1.8) * (1 - fear),
                look_y=0.0)
    bob = 6 * sh
    hero.front(c, 960 + noise(t * 30, 2) * 3 * fear + cam.sx, 975 + cam.sy, 11.0, t, expr,
               arms=dict(l=(0.15 + 0.5 * fear, 0.3 + 1.9 * fear), r=(0.15 + 0.5 * fear, 0.3 + 1.9 * fear)), bob=bob,
               lean=0.03 * math.sin(t * 2) * (1 - fear))
    # leaves shaken loose from above
    for k, tt in enumerate((T3.CUES["thump1"], T3.CUES["thump2"])):
        fx.leaves(c, t, tt, 960, -40, 14, 30 + k, col=TN.LEAF, spread=700, up=-80, dur=2.5, size=16)


# ----------------------------------------------------------------- shot C: the T-Rex steps out and roars
def rex_c_phase(t):
    steps = [7.45 - 0.65, 7.45, 8.1]
    if t < steps[0]:
        return 0.0
    if t < 8.5:
        return 0.5 + (t - 7.45) / 1.3
    return 0.5 + (8.5 - 7.45) / 1.3


def shot_c(c, t):
    u = smooth(inv(t, 7.1, 8.5))
    roar = smooth(inv(t, 8.9, 9.25)) * (1 - smooth(inv(t, 9.95, 10.25)))
    cam = Cam(960, 540, lerp(1.0, 1.06, inv(t, 7.2, 10.25)))
    shk = 0.0
    for a in (7.45, 8.1):
        if t >= a:
            shk += 10 * math.exp(-(t - a) * 6)
    cam.shake(t, shk + 16 * roar)
    backdrop(c, cam, t)
    with cam.view(c, 1.0):
        TN.meadow(c, -400, 2400, 790, 600, t, seed=13, density=1.0)
        TN.dirt_path(c, [(700, 790), (1220, 790)], [(250, 1100), (1700, 1100)], lw=3.0)
        TN.tree(c, "broad", 3, 380, 830, 900, t)
        TN.tree(c, "broad", 1, 1560, 840, 860, t, flip=True)
        rs = lerp(0.55, 1.22, u)
        TD.rex_front(c, 940, lerp(800, 900, u), rs, rex_c_phase(t), jaw=0.15 + 0.7 * roar, t=t, roar=roar)
        if roar > 0:
            fx.burst(c, t, 8.95, 940, 520, 60, 7, speed=(600, 1300), ang=(0.3, 2.8), grav=300, life=(0.6, 1.4), size=(2, 4.5),
                     col=(0.95, 0.97, 1.0), a=0.6, spawn=1.0, drag=1.2)
            fx.leaves(c, t, 8.95, 940, 600, 30, 11, col=TN.LEAF, spread=900, up=200, dur=2.0, size=14)
        for k, a in enumerate((7.45, 8.1)):
            fx.dust(c, t, a, 940 + (k * 2 - 1) * 60 * rs, lerp(800, 900, u), scale=1.2 * rs, col=(0.75, 0.62, 0.4), a=0.5, n=8,
                    seed=k)
    tremble = 1.0 + 1.5 * roar
    hero.front(c, 1450 + noise(t * 28, 3) * 4 * tremble, 1090, 5.6, t, dict(), back=True,
               arms=dict(l=(0.3 + 1.0 * roar, 1.2 + 1.4 * roar), r=(0.3 + 1.0 * roar, 1.2 + 1.4 * roar)))
    with cam.view(c, 1.3):
        TN.grass_tufts(c, -300, 2300, H + 80, t, seed=7, h=130, col="#3f9a32", lw=1.6, spacing=150)


# ----------------------------------------------------------------- shot D: run!
def rex_d_phase(t):
    steps = [s for s in T3.rex_steps() if s > 10.2]
    if not steps or t < steps[0]:
        return 0.5 * (t - 10.25) / max(0.1, (steps[0] - 10.25) if steps else 1)
    k = sum(1 for s in steps if s <= t) - 1
    k = max(0, min(k, len(steps) - 2))
    a, b = steps[k], steps[k + 1]
    return 0.5 + 0.5 * k + 0.5 * clamp((t - a) / (b - a), 0, 1.5)


def shot_d(c, t):
    u = inv(t, 10.25, 12.5)
    cam = Cam(960, 540, 1.0)
    steps = [s for s in T3.rex_steps() if s > 10.2]
    shk = 6.0
    for a in steps:
        if t >= a:
            shk += 14 * math.exp(-(t - a) * 7)
    cam.shake(t, shk)
    backdrop(c, Cam(960 + 30 * u, 560, 1.0 + 0.05 * u), t)
    with cam.view(c, 1.0):
        TN.meadow(c, -400, 2400, 800, 600, t, seed=17, density=1.0)
        TN.dirt_path(c, [(820, 800), (1100, 800)], [(200, 1150), (1720, 1150)], lw=3.0)
        # trees rushing past on both sides (camera backs away as the hero runs at it)
        for i in range(8):
            h_ = [hash01(i, 51, k) for k in range(3)]
            z = 0.45 + ((h_[0] * 2.4 + u * 1.6) % 2.4)
            side = -1 if i % 2 else 1
            X = side * (620 + 380 * h_[1])
            sx = 960 + X / z
            ht = 1100 / z
            TN.tree(c, "broad" if i % 3 else "arauc", i + 7, sx, 800 + 120 / z, ht, t, haze=(0.7, 0.86, 0.9), haze_a=clamp((z - 0.6) * 0.18))
        rs = lerp(0.85, 1.75, u ** 1.3)
        TD.rex_front(c, 900 + 40 * math.sin(t * 2), lerp(830, 1000, u ** 1.3), rs, rex_d_phase(t), jaw=0.45 + 0.35 * math.sin(t * 8),
                     t=t, roar=0.3)
        for k, a in enumerate(steps):
            if 0 <= t - a < 1.5:
                fx.dust(c, t, a, 900 + (k % 2 * 2 - 1) * 70 * rs, lerp(830, 1000, u ** 1.3), scale=1.3 * rs, col=(0.75, 0.62, 0.4),
                        a=0.5, n=7, seed=k + 9)
    scream = smooth(inv(t, 10.3, 10.45)) * (1 - smooth(inv(t, 11.4, 11.7)))
    pant = smooth(inv(t, 11.5, 11.8)) * (0.5 + 0.5 * math.sin(t * 22))
    glance = smooth(inv(t, 11.9, 12.05)) * (1 - smooth(inv(t, 12.3, 12.45)))
    expr = dict(face=-0.75 * glance, eye_s=1.4, brow_up=1.0, brow_in=1.0, mouth=max(scream, 0.35 + 0.25 * pant), mouth_w=0.9,
                look=-0.6 * glance)
    hs = lerp(4.2, 4.9, u)
    ph = T3.RUN.phase(t) if t > 10.3 else 0.0
    hero.front(c, 960 + 30 * math.sin(t * 3.1) + cam.sx, 760 + hs * 2 + cam.sy, hs, t, expr, run=ph,
               bob=abs(math.sin(ph * TAU)) * 4, shadow_y=760 + 47 * hs)
    with cam.view(c, 1.3):
        TN.grass_tufts(c, -300, 2300, H + 90, t * 3, seed=19, h=140, col="#3f9a32", lw=1.6, spacing=160)


def render(c, t):
    with layer(c, cf=grade_cf(sat=1.12, contrast=1.06, tint=(1.03, 1.0, 0.96))):
        if t < 4.2:
            shot_a(c, t)
            sunrays(c, t)
        elif t < 7.2:
            shot_b(c, t)
        elif t < 10.25:
            shot_c(c, t)
            sunrays(c, t, 0.12)
        else:
            shot_d(c, t)
            sunrays(c, t, 0.1)
    toon.paper(c, 0.10)
    post.vignette(c, 0.32)
    post.fade(c, 1 - smooth(inv(t, 0.0, 0.6)))


# ----------------------------------------------------------------- render
def frame(f, scale=1.0):
    surf = skia.Surface(int(W * scale), int(H * scale))
    c = surf.getCanvas()
    c.clear(skia.ColorBLACK)
    c.save()
    c.scale(scale, scale)
    render(c, f / FPS)
    c.restore()
    return surf


def _chunk(args):
    f0, f1, path = args
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-pix_fmt", "yuv420p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(frame(f).toarray().tobytes())
    p.stdin.close()
    p.wait()
    return f0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "video"
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    if mode == "stills":
        for tt in map(float, sys.argv[2:]):
            frame(int(round(tt * FPS)), 0.5).makeImageSnapshot().save(os.path.join(out_dir, f"still_{tt:05.2f}.png"))
        return
    n = int(round(DUR * FPS))
    jobs = [(f0, min(n, f0 + 30), os.path.join(out_dir, f"seg_{f0:04d}.mp4")) for f0 in range(0, n, 30)]
    with get_context("fork").Pool(4) as pool:
        for _ in pool.imap_unordered(_chunk, jobs):
            pass
    lst = os.path.join(out_dir, "list.txt")
    with open(lst, "w") as fh:
        for j in jobs:
            fh.write(f"file '{j[2]}'\n")
    final = os.path.join(ROOT, "final", "test_2d.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                           "-i", os.path.join(ROOT, "film3d", "test_audio.wav"), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final])
    print("wrote", final, f"{os.path.getsize(final) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
