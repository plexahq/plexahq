"""The 3D hero: an original cartoon explorer (big head, large expressive eyes, messy
dark hair, red-orange jacket, olive backpack, jeans, boots).

The rig is a chain of empties. Its joint angles come straight from the 2D stickman
poses (engine/stickman.py), so the same gait cycles (with IK feet that never slide)
drive the 3D body. Facing is local -Y; limbs hang along local -Z.
"""
import math

import bmesh
import bpy
from mathutils import Vector

from lib import mat, sphere, capsule, rounded_box, torus, empty, from_bm

THIGH, SHIN = 0.30, 0.295
UARM, FARM = 0.215, 0.206
TORSO = 0.40
HEAD_R = 0.25
ANKLE_H = 0.085
S3 = THIGH / 23.0          # 2D stickman units -> metres


class Character:
    def __init__(self):
        M = {
            "skin": mat("skin", "#f0c39c", rough=0.5, sss=0.25, sss_radius=(1.0, 0.4, 0.25)),
            "cheek": mat("cheek", "#ef9f8c", rough=0.6, sss=0.2),
            "hair": mat("hair", "#5a3622", rough=0.6, sheen=0.5, color2="#3a2216", noise_mix=0.5, noise_scale=40),
            "jacket": mat("jacket", "#c7432b", rough=0.55, sheen=0.3, color2="#a8341f", noise_mix=0.3, noise_scale=12,
                          bump=0.08, bump_scale=60),
            "jacket2": mat("jacket_dark", "#8e2a1b", rough=0.6, sheen=0.3),
            "zip": mat("zip", "#2a2523", rough=0.3, metal=0.6),
            "pants": mat("pants", "#2f4560", rough=0.75, color2="#26384f", noise_mix=0.4, noise_scale=30, bump=0.05,
                         bump_scale=120),
            "boot": mat("boot", "#6b4428", rough=0.6, color2="#553419", noise_mix=0.4, noise_scale=20),
            "sole": mat("sole", "#2a211b", rough=0.8),
            "pack": mat("pack", "#5f6b3a", rough=0.7, color2="#4c5630", noise_mix=0.4, noise_scale=15, bump=0.06,
                        bump_scale=80),
            "strap": mat("strap", "#3c4425", rough=0.7),
            "white": mat("sclera", "#f7f5f0", rough=0.12, coat=0.6),
            "iris": mat("iris", "#5a3a1e", rough=0.2, coat=1.0, color2="#2e1c0d", noise_mix=0.6, noise_scale=80),
            "pupil": mat("pupil", "#060404", rough=0.1, coat=1.0),
            "glint": mat("glint", "#ffffff", emit="#ffffff", emit_strength=3.0),
            "mouth": mat("mouth", "#5a1a1d", rough=0.5),
            "teeth": mat("teeth", "#f4efe6", rough=0.3),
            "tongue": mat("tongue", "#c25a5e", rough=0.4, sss=0.3),
            "brow": mat("brow", "#2c1a10", rough=0.6),
        }
        self.M = M
        R = self.root = empty("hero_root")
        self.hips = empty("hips", (0, 0, 0.6), R)
        sphere("pelvis", 0.16, M["pants"], (0, 0, -0.01), (1.05, 0.8, 0.75), self.hips, subsurf=1)
        # torso
        self.spine = empty("spine", (0, 0, 0.0), self.hips)
        sphere("torso", 0.2, M["jacket"], (0, 0, 0.2), (0.98, 0.72, 1.18), self.spine, subsurf=1)
        torus("hem", 0.168, 0.03, M["jacket2"], (0, 0, 0.03), self.spine, rot=(0, 0, 0))
        capsule("zipper", (0, -0.148, 0.05), (0, -0.142, 0.38), 0.008, 0.008, M["zip"], self.spine)
        for sx in (-1, 1):
            rounded_box("pocket", (0.07, 0.012, 0.06), M["jacket2"], (sx * 0.1, -0.135, 0.11), self.spine, rot=(0.15, 0, 0))
        torus("collar", 0.105, 0.05, M["jacket2"], (0, 0.0, 0.40), self.spine, rot=(0.25, 0, 0))
        # backpack + straps
        rounded_box("pack", (0.3, 0.14, 0.33), M["pack"], (0, 0.19, 0.22), self.spine, bevel=0.35)
        rounded_box("pack_pocket", (0.2, 0.06, 0.14), M["strap"], (0, 0.27, 0.15), self.spine, bevel=0.4)
        for sx in (-1, 1):
            capsule("strap", (sx * 0.1, -0.11, 0.36), (sx * 0.12, -0.13, 0.08), 0.018, 0.018, M["strap"], self.spine)
            capsule("strap_top", (sx * 0.1, -0.11, 0.36), (sx * 0.1, 0.12, 0.37), 0.018, 0.018, M["strap"], self.spine)
        # head
        self.neck = empty("neck", (0, 0, TORSO), self.spine)
        capsule("neckmesh", (0, 0, -0.02), (0, 0, 0.08), 0.06, 0.06, M["skin"], self.neck)
        self.head = empty("head", (0, 0, 0.025), self.neck)
        hc = (0, 0, HEAD_R)
        sphere("skull", HEAD_R, M["skin"], hc, (1.0, 0.95, 1.03), self.head, segs=48, rings=24, subsurf=1)
        for sx in (-1, 1):
            sphere("ear", 0.06, M["skin"], (sx * 0.245, 0.02, HEAD_R - 0.01), (0.45, 0.9, 1.15), self.head)
            sphere("cheek", 0.05, M["cheek"], (sx * 0.135, -0.19, HEAD_R - 0.075), (1.0, 0.5, 0.75), self.head)
        sphere("nose", 0.028, M["skin"], (0, -0.243, HEAD_R - 0.035), (1.0, 0.9, 0.9), self.head)
        self._hair(hc)
        # eyes
        self.eyes, self.lids, self.brows, self.irises = [], [], [], []
        for sx in (-1, 1):
            eg = empty("eye", (sx * 0.093, -0.17, HEAD_R + 0.035), self.head)
            sphere("sclera", 0.07, M["white"], (0, 0, 0), (1.0, 0.85, 1.15), eg, segs=32, rings=16)
            ir = empty("iris_rot", (0, 0, 0), eg)
            sphere("iris", 0.044, M["iris"], (0, -0.048, 0), (1.0, 0.35, 1.0), ir)
            sphere("pupil", 0.025, M["pupil"], (0, -0.062, 0), (1.0, 0.3, 1.0), ir)
            sphere("glint", 0.009, M["glint"], (-0.014, -0.074, 0.017), (1, 0.5, 1), ir)
            lid = empty("lid", (0, 0, 0), eg)
            self._lid(lid, M["skin"])
            self.eyes.append(eg)
            self.irises.append(ir)
            self.lids.append(lid)
            br = empty("brow", (sx * 0.095, -0.215, HEAD_R + 0.112), self.head)
            capsule("browmesh", (-0.045, 0, 0), (0.045, 0, 0), 0.016, 0.012 if sx > 0 else 0.016, M["brow"], br)
            self.brows.append(br)
        # mouth: dark cavity, teeth and tongue; scaled to open
        self.mouth = empty("mouth", (0, -0.205, HEAD_R - 0.1), self.head)
        sphere("cavity", 0.06, M["mouth"], (0, 0, 0), (1.0, 0.45, 0.5), self.mouth)
        sphere("teeth", 0.045, M["teeth"], (0, -0.006, 0.022), (1.0, 0.4, 0.22), self.mouth)
        sphere("tongue", 0.04, M["tongue"], (0, -0.004, -0.02), (1.0, 0.5, 0.3), self.mouth)
        # arms
        self.sh, self.el = {}, {}
        for side, sx in (("n", -1), ("f", 1)):
            s = empty("shoulder_" + side, (sx * 0.185, 0.0, 0.335), self.spine)
            capsule("uarm", (0, 0, 0), (0, 0, -UARM), 0.062, 0.055, M["jacket"], s)
            e = empty("elbow_" + side, (0, 0, -UARM), s)
            capsule("farm", (0, 0, 0), (0, 0, -FARM + 0.02), 0.055, 0.05, M["jacket"], e)
            torus("cuff", 0.048, 0.016, M["jacket2"], (0, 0, -FARM + 0.025), e)
            sphere("hand", 0.052, M["skin"], (0, -0.005, -FARM - 0.03), (0.85, 0.75, 1.1), e)
            sphere("thumb", 0.022, M["skin"], (sx * -0.035, -0.03, -FARM - 0.01), (1, 1, 1.4), e)
            self.sh[side], self.el[side] = s, e
        # legs
        self.th, self.kn, self.an = {}, {}, {}
        for side, sx in (("n", -1), ("f", 1)):
            t = empty("thigh_" + side, (sx * 0.085, 0, 0), self.hips)
            capsule("thighmesh", (0, 0, 0), (0, 0, -THIGH), 0.078, 0.064, M["pants"], t)
            k = empty("knee_" + side, (0, 0, -THIGH), t)
            capsule("shinmesh", (0, 0, 0), (0, 0, -SHIN + 0.04), 0.064, 0.058, M["pants"], k)
            a = empty("ankle_" + side, (0, 0, -SHIN), k)
            rounded_box("boot", (0.115, 0.21, 0.1), M["boot"], (0, -0.045, -0.035), a, bevel=0.45)
            rounded_box("sole", (0.12, 0.22, 0.03), M["sole"], (0, -0.045, -0.083), a, bevel=0.4, subsurf=1)
            torus("boot_top", 0.06, 0.02, M["boot"], (0, 0, 0.01), a)
            self.th[side], self.kn[side], self.an[side] = t, k, a

    def _hair(self, hc):
        M = self.M
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=HEAD_R + 0.018)
        kill = [v for v in bm.verts if v.co.z < -0.6 * v.co.y + 0.02]
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
        from_bm("hair_cap", bm, M["hair"], self.head, True, 1, loc=hc, scale=(1.03, 1.0, 1.05))
        tufts = [((-0.1, -0.19, 0.19), (-0.2, -0.2, 0.15), 0.05), ((0.02, -0.21, 0.2), (0.12, -0.23, 0.17), 0.055),
                 ((0.12, -0.17, 0.2), (0.21, -0.17, 0.14), 0.045), ((0.05, -0.08, 0.26), (-0.03, -0.18, 0.29), 0.055),
                 ((0.0, 0.06, 0.27), (-0.04, 0.0, 0.32), 0.04)]
        for a, b, r in tufts:
            capsule("tuft", (a[0], a[1], a[2] + hc[2]), (b[0], b[1], b[2] + hc[2]), r, 0.018, M["hair"], self.head)

    def _lid(self, parent, m):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.074)
        kill = [v for v in bm.verts if v.co.z < -0.002]
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
        ob = from_bm("lidmesh", bm, m, parent, True, 0, scale=(1.04, 0.9, 1.18))
        return ob

    # ------------------------------------------------------------- posing
    def apply(self, pose, path_origin=(0, 0), yaw=0.0, face=None):
        """pose: 2D stickman Pose (scale S3, ground at -ANKLE_H). yaw: heading (0 = facing -Y)."""
        face = face or {}
        p = pose
        ox, oy = path_origin
        # 2D x runs along the heading; 2D y is down
        fwd = Vector((math.sin(yaw), -math.cos(yaw), 0))
        self.root.location = (ox + fwd.x * p.x, oy + fwd.y * p.x, 0)
        self.root.rotation_euler = (0, 0, yaw)
        self.hips.location = (0, 0, -p.y)
        self.spine.rotation_euler = (p.torso, 0, face.get("twist", 0.0))
        self.neck.rotation_euler = (p.head * 0.5, 0, 0)
        self.head.rotation_euler = (p.head * 0.5 + face.get("nod", 0.0), face.get("roll", 0.0), face.get("yaw", 0.0))
        for side in ("n", "f"):
            self.sh[side].rotation_euler = (-getattr(p, "sh_" + side), 0, 0)
            sx = -1 if side == "n" else 1
            self.sh[side].rotation_euler.y = -sx * face.get("arm_out", 0.08)
            self.el[side].rotation_euler = (-getattr(p, "el_" + side), 0, 0)
            hp, kn = getattr(p, "hp_" + side), getattr(p, "kn_" + side)
            self.th[side].rotation_euler = (-hp, 0, 0)
            self.kn[side].rotation_euler = (kn, 0, 0)
            self.an[side].rotation_euler = (hp - kn, 0, 0)
        # face
        eo = face.get("eye", 1.0)
        es = face.get("eye_s", 1.0)
        look = face.get("look", (0.0, 0.0))
        for i, (eg, ir, lid, br) in enumerate(zip(self.eyes, self.irises, self.lids, self.brows)):
            eg.scale = (es, es, es * (1 + 0.08 * (es - 1)))
            ir.rotation_euler = (-look[1] * 0.45, 0, look[0] * 0.6)
            lid.rotation_euler = (math.radians(lerp(95, -78, eo)), 0, 0)
            sx = -1 if i == 0 else 1
            raise_ = face.get("brow_up", 0.0)
            inner = face.get("brow_in", 0.0)
            br.location.z = HEAD_R + 0.112 + 0.025 * raise_ + 0.01 * (es - 1)
            br.rotation_euler = (0, sx * inner * 0.45, 0)
        mo = face.get("mouth", 0.0)
        mw = face.get("mouth_w", 1.0)
        self.mouth.scale = (mw * (0.8 + 0.25 * mo), 1.0, 0.12 + 1.6 * mo)


def lerp(a, b, t):
    return a + (b - a) * t
