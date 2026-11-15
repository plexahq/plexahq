"""3D T-Rex. The body is a metaball (ellipsoids along the spine melt into one organic
skin, capsules for the legs), driven every frame by the 2D theropod rig in
engine/dino.py. The skull and jaw are lofted meshes built from the same 2D
profiles, with teeth, eyes and a hinged jaw. Local frame: +X forward, +Z up."""
import math

import bmesh
import bpy
from mathutils import Quaternion, Vector

from lib import empty, from_bm, sphere, capsule, link, hexrgb
from engine import dino as D


def skin_material(name="rex_skin", z0=0.0, z1=4.4, stops=None, stripe=(2.6, 3.6)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = z0
    mr.inputs["From Max"].default_value = z1
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    stops = stops or [(0.0, "#3a3826"), (0.3, "#4c4931"), (0.44, "#ad9b74"), (0.6, "#5a573a"), (1.0, "#22231a")]
    cr.elements[0].position, cr.elements[0].color = stops[0][0], hexrgb(stops[0][1])
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], hexrgb(stops[-1][1])
    for pos, col in stops[1:-1]:
        e = cr.elements.new(pos)
        e.color = hexrgb(col)
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    # dorsal stripes
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 1.6
    wave.inputs["Distortion"].default_value = 6
    wave.inputs["Detail"].default_value = 3
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    st = nt.nodes.new("ShaderNodeMapRange")
    st.inputs["From Min"].default_value = 0.55
    st.inputs["From Max"].default_value = 0.85
    nt.links.new(wave.outputs["Fac"], st.inputs["Value"])
    top = nt.nodes.new("ShaderNodeMapRange")
    top.inputs["From Min"].default_value = stripe[0]
    top.inputs["From Max"].default_value = stripe[1]
    nt.links.new(sep.outputs["Z"], top.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(st.outputs["Result"], mul.inputs[0])
    nt.links.new(top.outputs["Result"], mul.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = hexrgb("#1c1c14")
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    m2.inputs[1].default_value = 0.65
    nt.links.new(mul.outputs[0], m2.inputs[0])
    nt.links.new(m2.outputs[0], mix.inputs["Factor"])
    # mottling
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    mix2.blend_type = "MULTIPLY"
    mix2.inputs["Factor"].default_value = 0.35
    nt.links.new(mix.outputs["Result"], mix2.inputs["A"])
    nt.links.new(nz.outputs["Color"], mix2.inputs["B"])
    nt.links.new(mix2.outputs["Result"], p.inputs["Base Color"])
    # scales: voronoi bump
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 26.0
    vor.feature = "DISTANCE_TO_EDGE"
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.02
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    p.inputs["Roughness"].default_value = 0.62
    p.inputs["Subsurface Weight"].default_value = 0.05
    p.inputs["Sheen Weight"].default_value = 0.2
    return m


def _loft(name, poly, width_fn, sc, material, parent, rings=28, around=18, expo=0.65):
    """Loft a closed side profile (x forward, y down) into a solid with half-width width_fn(x)."""
    xs = [p[0] for p in poly]
    x0, x1 = min(xs) + 0.5, max(xs) - 0.5
    bm = bmesh.new()
    grid = []
    for i in range(rings):
        x = x0 + (x1 - x0) * i / (rings - 1)
        ys = []
        n = len(poly)
        for j in range(n):
            a, b = poly[j], poly[(j + 1) % n]
            if (a[0] - x) * (b[0] - x) <= 0 and a[0] != b[0]:
                u = (x - a[0]) / (b[0] - a[0])
                ys.append(a[1] + (b[1] - a[1]) * u)
        if len(ys) < 2:
            continue
        top, bot = min(ys), max(ys)
        c, hh = (top + bot) / 2, max(0.5, (bot - top) / 2)
        w = width_fn(x)
        row = []
        for k in range(around):
            phi = 2 * math.pi * k / around
            s, co = math.sin(phi), math.cos(phi)
            s = math.copysign(abs(s) ** expo, s)
            co = math.copysign(abs(co) ** expo, co)
            row.append(bm.verts.new((x * sc, w * s * sc, -(c - hh * co) * sc)))
        grid.append(row)
    for i in range(len(grid) - 1):
        for k in range(around):
            bm.faces.new((grid[i][k], grid[i][(k + 1) % around], grid[i + 1][(k + 1) % around], grid[i + 1][k]))
    for row, rev in ((grid[0], True), (grid[-1], False)):
        c = bm.verts.new(sum((v.co for v in row), Vector()) / len(row))
        for k in range(around):
            f = (row[k], row[(k + 1) % around], c)
            bm.faces.new(f[::-1] if rev else f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bm(name, bm, material, parent, True, 2)


class TRex3D:
    def __init__(self, k=0.015):
        self.k = k
        self.rig = D.Theropod(D.REX)
        self.root = empty("rex_root")
        self.skin = skin_material()
        mb = bpy.data.metaballs.new("rex_mb")
        mb.resolution = 0.12
        mb.render_resolution = 0.075
        mb.threshold = 0.6
        self.mb = mb
        self.body = bpy.data.objects.new("rex_body", mb)
        link(self.body, self.root)
        mb.materials.append(self.skin)
        self.elems = None
        self.head_skin = skin_material("rex_head_skin", -0.55, 0.65,
                                       [(0.0, "#a8966f"), (0.4, "#6a6545"), (0.62, "#4a4832"), (1.0, "#24251b")], stripe=(5, 6))
        self._build_head()

    def _build_head(self):
        k = self.k
        sc = D.REX["head"] / 120.0 * k
        self.head = empty("rex_head", (0, 0, 0), self.root)
        teeth = bpy.data.materials.new("rex_teeth")
        teeth.use_nodes = True
        tp = teeth.node_tree.nodes["Principled BSDF"]
        tp.inputs["Base Color"].default_value = hexrgb("#efe4c8")
        tp.inputs["Roughness"].default_value = 0.35
        mouth = bpy.data.materials.new("rex_mouth")
        mouth.use_nodes = True
        mp = mouth.node_tree.nodes["Principled BSDF"]
        mp.inputs["Base Color"].default_value = hexrgb("#5a1418")
        mp.inputs["Roughness"].default_value = 0.35
        mp.inputs["Subsurface Weight"].default_value = 0.3
        eye = bpy.data.materials.new("rex_eye")
        eye.use_nodes = True
        ep = eye.node_tree.nodes["Principled BSDF"]
        ep.inputs["Base Color"].default_value = hexrgb("#e8a325")
        ep.inputs["Roughness"].default_value = 0.08
        ep.inputs["Coat Weight"].default_value = 1.0
        ep.inputs["Emission Color"].default_value = hexrgb("#ff9a20")
        ep.inputs["Emission Strength"].default_value = 0.4
        dark = bpy.data.materials.new("rex_dark")
        dark.use_nodes = True
        dark.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = hexrgb("#080605")
        dark.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.1

        def skull_w(x):
            u = min(1, max(0, (x + 8) / 132))
            return 33 * (1 - u) + 13 * u

        def jaw_w(x):
            u = min(1, max(0, (x + 2) / 120))
            return 29 * (1 - u) + 10 * u

        _loft("rex_skull", D.REX_SKULL, skull_w, sc, self.head_skin, self.head)
        hx, hy = D.REX_HINGE
        self.jaw = empty("rex_jaw", (hx * sc, 0, -hy * sc), self.head)
        jpoly = [(x - hx, y - hy) for x, y in D.REX_JAW]
        _loft("rex_jawmesh", jpoly, lambda x: jaw_w(x + hx), sc, self.head_skin, self.jaw)
        # mouth interior & tongue
        sphere("rex_throat", 1.0, mouth, (55 * sc, 0, -14 * sc), (48 * sc, 22 * sc, 9 * sc), self.head)
        sphere("rex_tongue", 1.0, mouth, ((60 - hx) * sc, 0, -(12 - hy) * sc), (40 * sc, 15 * sc, 5 * sc), self.jaw)
        # teeth
        for row, up, par, off, wfn in ((D.REX_UPPER_ROW, False, self.head, (0, 0), skull_w),
                                       (D.REX_LOWER_ROW, True, self.jaw, (hx, hy), jaw_w)):
            pts = row
            for side in (-1, 1):
                for i in range(12):
                    u = (i + 0.5) / 12
                    seg_f = u * (len(pts) - 1)
                    j = min(int(seg_f), len(pts) - 2)
                    f = seg_f - j
                    x = pts[j][0] + (pts[j + 1][0] - pts[j][0]) * f
                    y = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * f
                    ln = (7 + 4 * math.sin(math.pi * u)) * sc
                    lat = side * (wfn(x) - 3.5) * sc
                    base = Vector(((x - off[0]) * sc, lat, -(y - off[1]) * sc))
                    tip = base + Vector((0.15 * ln, 0, ln if up else -ln))
                    bm = bmesh.new()
                    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=2.4 * sc, radius2=0.2 * sc, depth=ln)
                    ob = from_bm("tooth", bm, teeth, par, True, 0)
                    ob.location = (base + tip) / 2
                    ob.rotation_euler = Vector((0, 0, 1)).rotation_difference((tip - base).normalized()).to_euler()
        # eyes, brow ridges, nostrils
        for side in (-1, 1):
            ex, ey = 32, -17
            lat = side * (skull_w(ex) - 3) * sc
            sphere("rex_eye", 6.2 * sc, eye, (ex * sc, lat, -ey * sc), parent=self.head)
            sphere("rex_pupil", 1.0, dark, (ex * sc, lat + side * 5.6 * sc, -ey * sc), (1.4 * sc, 0.8 * sc, 5.2 * sc), self.head)
            capsule("rex_brow", ((ex - 13) * sc, lat * 0.95, -(ey - 7) * sc), ((ex + 12) * sc, lat * 0.92, -(ey - 9) * sc),
                    4.5 * sc, 3.0 * sc, self.head_skin, self.head)
            sphere("rex_nostril", 2.6 * sc, dark, (113 * sc, side * 9 * sc, 9 * sc), (1.2, 0.6, 0.8), self.head)

    # ------------------------------------------------------------- posing
    def _elements(self, geo):
        """List of (type, centre, quat, radius, size) in metres (rex local)."""
        k = self.k
        out = []
        sp, rd = geo["spine"], geo["radii"]
        n = len(sp)
        for i in range(n - 1):
            for sub in range(3):
                u = sub / 3
                x = sp[i][0] + (sp[i + 1][0] - sp[i][0]) * u
                y = sp[i][1] + (sp[i + 1][1] - sp[i][1]) * u
                rt = rd[i][0] + (rd[i + 1][0] - rd[i][0]) * u
                rb = rd[i][1] + (rd[i + 1][1] - rd[i][1]) * u
                tx, ty = sp[i + 1][0] - sp[i][0], sp[i + 1][1] - sp[i][1]
                ln = math.hypot(tx, ty) or 1
                tx, ty = tx / ln, ty / ln
                nx, ny = ty, -tx
                cx, cy = x + nx * (rt - rb) / 2, y + ny * (rt - rb) / 2
                hh = (rt + rb) / 2
                wf = 0.72 if i < 12 else 0.85
                ang = math.atan2(ty, tx)       # 2D y down: positive = nose down
                q = Quaternion((0, 1, 0), ang)
                out.append(("ELLIPSOID", (cx * k, 0, -cy * k), q, hh * k,
                            (max(ln / 3, hh * 0.6) / hh * 1.25, wf, 1.0)))
        for side, lat in (("n", 1), ("f", -1)):
            L = geo["legs"][side]
            yl = lat * 0.2 * D.REX["hip_h"] * k
            hp, kn, an, ba = L["hip"], L["knee"], L["ank"], L["ball"]
            mid = ((hp[0] * 0.6 + kn[0] * 0.4), (hp[1] * 0.6 + kn[1] * 0.4))
            ang = math.atan2(kn[1] - hp[1], kn[0] - hp[0])
            out.append(("ELLIPSOID", (mid[0] * k, yl, -mid[1] * k), Quaternion((0, 1, 0), ang), 44 * k, (1.55, 0.8, 1.0)))
            for a, b, r in ((hp, kn, 34), (kn, an, 21), (an, ba, 13)):
                ang = math.atan2(b[1] - a[1], b[0] - a[0])
                ln = math.hypot(b[0] - a[0], b[1] - a[1])
                c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                out.append(("CAPSULE", (c[0] * k, yl, -c[1] * k), Quaternion((0, 1, 0), ang), r * k, (ln / 2 * k / (r * k), 1, 1)))
            for t_ang, t_len, dy in ((0.05, 30, 0.0), (-0.05, 34, 9), (0.15, 26, -9)):
                a = t_ang + L["curl"] * 0.9
                c = (ba[0] + math.cos(a) * t_len / 2, ba[1] + math.sin(a) * t_len / 2)
                out.append(("CAPSULE", (c[0] * k, yl + dy * k, -c[1] * k), Quaternion((0, 1, 0), a), 8 * k,
                            (t_len / 2 / 8, 1, 1)))
        sh, el, hd = geo["arm"]
        for lat in (1, -1):
            for a, b, r in ((sh, el, 7), (el, hd, 5)):
                ang = math.atan2(b[1] - a[1], b[0] - a[0])
                ln = math.hypot(b[0] - a[0], b[1] - a[1])
                c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                out.append(("CAPSULE", (c[0] * k, lat * 38 * k, -c[1] * k), Quaternion((0, 1, 0), ang), r * k,
                            (ln / 2 / r, 1, 1)))
        return out

    def apply(self, P, loc, yaw):
        k = self.k
        geo = self.rig.solve(P)
        self.root.location = loc
        self.root.rotation_euler = (0, 0, yaw)
        els = self._elements(geo)
        if self.elems is None:
            self.elems = []
            for typ, c, q, r, s in els:
                e = self.mb.elements.new()
                e.type = typ
                e.stiffness = 2.0
                self.elems.append(e)
        for e, (typ, c, q, r, s) in zip(self.elems, els):
            e.co = c
            e.rotation = q
            e.radius = r * 1.35
            if typ == "ELLIPSOID":
                e.size_x, e.size_y, e.size_z = s
            else:
                e.size_x = s[0] * r
        hx, hy = geo["head"]
        self.head.location = (hx * k, 0, -hy * k)
        self.head.rotation_euler = (0, geo["head_ang"], 0)
        self.jaw.rotation_euler = (0, geo["jaw"], 0)
        return geo
