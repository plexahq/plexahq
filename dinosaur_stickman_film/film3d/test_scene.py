#!/usr/bin/env python3
"""3D test (~12.5 s): an explorer in a prehistoric clearing, the ground shakes,
a T-Rex steps out of the trees and roars, the explorer screams and runs.

  python3 film3d/test_scene.py --start 0 --end 12.5 --scale 1.0 --out film3d/frames
  python3 film3d/test_scene.py --stills 2 5.6 9.2 11.5 --scale 0.5

Rendered with Blender (bpy) Cycles on the CPU. Poses come from the same rigs as
the 2D film (engine/stickman.py, engine/dino.py)."""
import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from lib import reset, add_haze, link, look_at  # noqa: E402
from character import Character, S3, ANKLE_H  # noqa: E402
from trex import TRex3D  # noqa: E402
import world as WD  # noqa: E402
from engine import stickman as sm  # noqa: E402
from engine import dino as D  # noqa: E402
from engine.core import smooth, inv, lerp, noise, keys, ease_io, ease_out, ease_in, clamp  # noqa: E402

FPS = 24
DURATION = 12.5
CUES = {"ooh": 2.4, "thump1": 5.3, "gasp": 5.4, "thump2": 6.1, "turn": 6.4, "rex_step1": 7.45, "rex_step2": 8.1,
        "roar": 8.9, "scream": 10.35, "run": 10.3, "pant": 11.6}

# ----------------------------------------------------------------- the explorer
WALK = sm.Mover(0.0, 4.6, -5.0, lambda t: 1.15 * (1 - smooth(inv(t, 3.4, 4.2))), "walk", S3)
X_STOP = WALK.x(4.6)
RUN = sm.Mover(10.25, 13.0, 0.0, lambda t: 5.2 * smooth(inv(t, 10.25, 10.8)), "sprint", S3)
BACKSTEP = 0.35


def hero(t):
    """-> (pose, origin, yaw, face)"""
    face = dict(eye=1.0)
    blink = any(a < t < a + 0.12 for a in (1.3, 3.6, 4.9, 7.6))
    if t < 4.2:
        p = sm.gait(WALK.phase(t), WALK.x(t), -ANKLE_H, S3, 1, "walk")
        look = math.sin(t * 1.3) * 0.7
        face.update(yaw=look, look=(look * 0.5, 0.25), nod=-0.12, eye=0.0 if blink else 1.0,
                    mouth=0.22 * math.sin(math.pi * inv(t, 2.3, 3.3)), mouth_w=0.6)
        return p, (0, 0), math.pi / 2, face
    yaw = lerp(math.pi / 2, 0.0, smooth(inv(t, 4.2, 4.9)))
    if t < 7.2:
        jolt = math.exp(-max(0.0, t - 5.3) * 6) * (t > 5.3) + 0.7 * math.exp(-max(0.0, t - 6.1) * 6) * (t > 6.1)
        fear = smooth(inv(t, 5.35, 5.6))
        p = sm.stand(x=0, y=0, s=S3, f=1, sh_n=0.1 + 0.35 * fear, el_n=0.15 + 0.9 * fear, sh_f=-0.05 + 0.3 * fear,
                     el_f=0.15 + 0.9 * fear, torso=-0.05 * fear, hp_n=0.05 + 0.1 * jolt, kn_n=0.05 + 0.25 * jolt,
                     hp_f=-0.05 + 0.1 * jolt, kn_f=0.05 + 0.25 * jolt)
        sm.settle(p, -ANKLE_H)
        p = sm.breathe(p, t, 0.3 + 0.5 * fear, 1.0 + fear)
        p = sm.tremble(p, t, 1.4 * fear)
        turn = smooth(inv(t, 6.4, 7.2))
        look0 = 0.35 * math.sin((t - 4.2) * 1.6) * (1 - fear)
        face.update(yaw=lerp(look0, 1.15, turn), twist=0.45 * turn, look=(0.9 * turn, 0.1),
                    eye=0.0 if blink else 1.0, eye_s=1.0 + 0.28 * fear, brow_up=fear, brow_in=0.6 * fear,
                    mouth=0.45 * math.sin(math.pi * inv(t, 5.38, 5.9)) + 0.18 * fear, mouth_w=0.75)
        return p, (X_STOP, 0), yaw, face
    if t < 10.25:
        # facing the T-Rex (+Y): frozen, trembling, then shielding during the roar
        roar = smooth(inv(t, 8.9, 9.2)) * (1 - smooth(inv(t, 10.0, 10.25)))
        back = smooth(inv(t, 8.95, 9.4))
        p = sm.stand(x=0, y=0, s=S3, f=1, torso=-0.15 * roar, head=-0.15 * roar,
                     sh_n=0.4 + 1.6 * roar, el_n=1.0 + 0.6 * roar, sh_f=0.35 + 1.4 * roar, el_f=1.0 + 0.7 * roar,
                     hp_n=0.05 + 0.25 * roar, kn_n=0.05 + 0.2 * roar, hp_f=-0.1 - 0.3 * roar, kn_f=0.05 + 0.1 * roar)
        sm.settle(p, -ANKLE_H)
        p = sm.tremble(p, t, 1.8 + 1.5 * roar)
        face.update(eye_s=1.3, brow_up=1.0, brow_in=0.9, mouth=0.3 + 0.2 * roar, mouth_w=0.7, look=(0, 0.2),
                    eye=0.35 if 9.0 < t < 9.6 else 1.0)
        return p, (X_STOP, -BACKSTEP * back), math.pi, face
    # turn and run toward the camera (-Y)
    p = sm.gait(RUN.phase(t), RUN.x(t), -ANKLE_H, S3, 1, "sprint")
    start = sm.Pose(x=0, y=0, s=S3, f=1, torso=0.5, head=-0.1, sh_n=-1.0, el_n=1.5, sh_f=1.0, el_f=1.5,
                    hp_n=0.6, kn_n=0.9, hp_f=-0.4, kn_f=0.6)
    sm.settle(start, -ANKLE_H)
    if t < 10.55:
        p = sm.blend(start, p, smooth(inv(t, 10.25, 10.55)))
    scream = smooth(inv(t, 10.3, 10.45)) * (1 - smooth(inv(t, 11.4, 11.7)))
    pant = smooth(inv(t, 11.5, 11.8)) * (0.5 + 0.5 * math.sin(t * 22))
    glance = smooth(inv(t, 11.9, 12.05)) * (1 - smooth(inv(t, 12.3, 12.45)))
    face.update(eye_s=1.35, brow_up=1.0, brow_in=1.0, mouth=max(scream * 1.0, 0.35 + 0.25 * pant), mouth_w=0.85,
                yaw=2.2 * glance, look=(-0.8 * glance, 0.1))
    return p, (X_STOP, -BACKSTEP), 0.0, face


# ----------------------------------------------------------------- the T-Rex
REX_K = 0.015
REX_X = -1.6


def rex(t):
    """-> (P, world loc, yaw)"""
    walk = D.REX["walk"]
    P = dict(x=0, gy=0, s=1, f=1, t=t, neck_up=0.25, head_pitch=0.18, tail_lift=0.1)
    if t < 7.1:
        return P, (REX_X, 60, -60), -math.pi / 2
    if t < 8.5:
        u = inv(t, 7.1, 8.5)
        y = lerp(15.0, 9.5, 1 - (1 - u) ** 1.6)
        dist = (15.0 - y) / REX_K
        P.update(gait="walk", phase=dist * walk["duty"] / walk["stride"] + 0.15, neck_up=0.2, head_pitch=0.15)
        return P, (REX_X, y, WD.height(REX_X, y)), -math.pi / 2
    y = 9.5
    P["stance"] = 0.2
    if t < 10.25:
        up = smooth(inv(t, 8.5, 8.9))
        on = smooth(inv(t, 8.9, 9.25)) * (1 - smooth(inv(t, 9.95, 10.25)))
        P.update(neck_up=0.2 + 0.12 * up - 0.3 * on, head_pitch=0.15 - 0.1 * up + 0.08 * on, pitch=-0.05 * up + 0.08 * on,
                 jaw=0.1 * up + 0.78 * on, shake=1.2 * on, tail_lift=0.1 + 0.12 * on)
        return P, (REX_X, y, WD.height(REX_X, y)), -math.pi / 2
    run = D.REX["run"]
    dt = t - 10.25
    dist_m = 7.5 * max(0.0, dt - 0.3) ** 1.3 + 0.8 * min(dt, 0.3)
    y = 9.5 - dist_m
    P.update(gait="run", phase=(dist_m / REX_K) * run["duty"] / run["stride"], neck_up=0.02, head_pitch=0.22,
             jaw=0.35 + 0.25 * math.sin(t * 7), pitch=0.0)
    x = lerp(REX_X, REX_X - 1.4, smooth(inv(t, 10.25, 11.0)))
    return P, (x, y, WD.height(x, y)), -math.pi / 2


def rex_steps():
    out = [7.45, 8.1]
    walk_end = 8.5
    run = D.REX["run"]
    t = 10.25
    last = 0
    while t < DURATION:
        dt = t - 10.25
        dist_m = 7.5 * max(0.0, dt - 0.3) ** 1.3 + 0.8 * min(dt, 0.3)
        ph = (dist_m / REX_K) * run["duty"] / run["stride"]
        k = int(ph * 2)
        if k > last:
            out.append(t)
            last = k
        t += 1 / 240
    return out


# ----------------------------------------------------------------- cameras
def camera(t, ch_loc):
    """-> (location, target, lens, focus_distance, fstop, shake)"""
    if t < 4.2:
        u = ease_io(inv(t, 0.0, 4.2))
        loc = Vector((lerp(1.2, 2.6, u), -6.6, 1.0))
        tgt = Vector((lerp(-3.6, -0.6, u), 1.5, 1.6))
        return loc, tgt, 30, (Vector(ch_loc) - loc).length, 5.6, 0.0
    if t < 7.2:
        loc = Vector((X_STOP + 0.22, -2.35 + 0.15 * inv(t, 4.2, 7.2), 1.40))
        tgt = Vector((X_STOP - 0.03, 0, 1.31))
        sh = 0.0
        for a, k in ((5.3, 1.0), (6.1, 0.8)):
            if t >= a:
                sh += k * math.exp(-(t - a) * 5)
        return loc, tgt, 50, (tgt - loc).length + 0.05, 2.4, sh
    if t < 10.25:
        u = ease_io(inv(t, 7.2, 10.25))
        loc = Vector((X_STOP - 1.35, -2.7 - 0.4 * u, 1.0))
        tgt = Vector((REX_X + 0.3, 9.0, lerp(3.1, 3.5, u)))
        sh = 0.0
        for a in (7.45, 8.1):
            if t >= a:
                sh += 0.5 * math.exp(-(t - a) * 6)
        if 8.95 < t < 10.1:
            sh += 0.9 * smooth(inv(t, 8.95, 9.1))
        return loc, tgt, 28, 11.5, 5.6, sh
    cx, cy = ch_loc[0], ch_loc[1]
    loc = Vector((cx + 0.7, cy - 4.0, 0.55))
    tgt = Vector((cx - 0.2, cy + 4.0, 2.0))
    sh = 0.35
    for a in rex_steps():
        if t >= a and a > 10.2:
            sh += 0.35 * math.exp(-(t - a) * 7)
    return loc, tgt, 26, 4.05, 2.8, sh


# ----------------------------------------------------------------- build & render
def build(scale=1.0, samples=10):
    sc = reset()
    WD.build(sc)
    ch = Character()
    rx = TRex3D(REX_K)
    add_haze(color=(0.68, 0.76, 0.88), dist=340.0, max_fac=0.78, skip=("glint",))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    link(cam)
    cam.data.sensor_width = 36
    cam.data.dof.use_dof = True
    sc.camera = cam
    r = sc.render
    r.resolution_x, r.resolution_y = int(1920 * scale), int(1080 * scale)
    r.resolution_percentage = 100
    r.use_persistent_data = True
    r.image_settings.file_format = "PNG"
    cy = sc.cycles
    cy.samples = samples
    cy.adaptive_threshold = 0.04
    cy.use_denoising = True
    cy.max_bounces = 3
    cy.diffuse_bounces = 1
    cy.glossy_bounces = 1
    cy.transmission_bounces = 1
    cy.volume_bounces = 0
    cy.use_fast_gi = True
    cy.fast_gi_method = "REPLACE"
    sc.world.light_settings.distance = 6.0
    r.use_simplify = True
    r.simplify_subdivision_render = 1
    cy.transparent_max_bounces = 4
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except TypeError:
            pass
    return sc, ch, rx, cam


def apply(t, ch, rx, cam):
    p, origin, yaw, face = hero(t)
    ch.apply(p, origin, yaw, face)
    ch_loc = ch.root.location.copy()
    P, loc, ryaw = rex(t)
    rx.apply(P, loc, ryaw)
    cl, ct, lens, fd, fs, sh = camera(t, ch_loc)
    cam.location = cl
    look_at(cam, ct)
    if sh:
        cam.rotation_euler.x += noise(t * 13, 3) * 0.012 * sh
        cam.rotation_euler.z += noise(t * 13, 9) * 0.012 * sh
        cam.location.z += noise(t * 15, 5) * 0.03 * sh
    cam.data.lens = lens
    cam.data.dof.focus_distance = fd
    cam.data.dof.aperture_fstop = fs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=DURATION)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--samples", type=int, default=10)
    ap.add_argument("--out", default=os.path.join(HERE, "frames"))
    ap.add_argument("--stills", type=float, nargs="*")
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--threads", type=int, default=0)
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    sc, ch, rx, cam = build(a.scale, a.samples)
    os.makedirs(a.out, exist_ok=True)
    if a.threads:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = a.threads
    frames = [int(round(t * FPS)) for t in a.stills] if a.stills else \
        list(range(int(a.start * FPS) + a.offset, int(round(a.end * FPS)), a.every))
    frames = [f for f in frames if not os.path.exists(os.path.join(a.out, f"f_{f:05d}.png"))]
    t0 = time.time()
    for i, f in enumerate(frames):
        t = f / FPS
        apply(t, ch, rx, cam)
        sc.frame_set(f)
        sc.render.filepath = os.path.join(a.out, f"f_{f:05d}.png")
        ft = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"frame {f} t={t:.2f} {time.time() - ft:.1f}s  [{i + 1}/{len(frames)}] elapsed {(time.time() - t0) / 60:.1f} min",
              flush=True)


if __name__ == "__main__":
    main()
