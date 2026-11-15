"""The prehistoric clearing: terrain, grass and fern instancing, giant trees, tree
ferns, rocks, distant mountains and a volcano, physical sky and a warm sun."""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

from lib import mat, from_bm, sphere, capsule, empty, link, hexrgb

PATH_Y = 0.0
CLEAR_R = 13.0


def height(x, y):
    d = math.hypot(x, y)
    hill = noise.noise(Vector((x * 0.02, y * 0.02, 0.3))) * 6 + noise.noise(Vector((x * 0.07, y * 0.07, 1.7))) * 1.2
    edge = min(1.0, max(0.0, (d - 18) / 40))
    bump = noise.noise(Vector((x * 0.3, y * 0.3, 4.2))) * 0.06
    return hill * edge * edge + bump + max(0.0, d - 60) * 0.15


def ground_material():
    m = bpy.data.materials.new("ground")
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ab = nt.nodes.new("ShaderNodeMath")
    ab.operation = "ABSOLUTE"
    nt.links.new(sep.outputs["Y"], ab.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.8
    nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 0.6
    nt.links.new(nz.outputs["Fac"], add.inputs[0])
    nt.links.new(ab.outputs[0], add.inputs[2])
    path = nt.nodes.new("ShaderNodeMapRange")
    path.inputs["From Min"].default_value = 1.0
    path.inputs["From Max"].default_value = 1.6
    path.inputs["To Min"].default_value = 1.0
    path.inputs["To Max"].default_value = 0.0
    nt.links.new(add.outputs[0], path.inputs["Value"])
    grass = nt.nodes.new("ShaderNodeMix")
    grass.data_type = "RGBA"
    grass.inputs["A"].default_value = hexrgb("#3d5a22")
    grass.inputs["B"].default_value = hexrgb("#5f7a2d")
    nz2 = nt.nodes.new("ShaderNodeTexNoise")
    nz2.inputs["Scale"].default_value = 0.15
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    nt.links.new(nz2.outputs["Fac"], grass.inputs["Factor"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = hexrgb("#7a6446")
    nt.links.new(grass.outputs["Result"], mix.inputs["A"])
    nt.links.new(path.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.92
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    vz = nt.nodes.new("ShaderNodeTexNoise")
    vz.inputs["Scale"].default_value = 18
    vz.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], vz.inputs["Vector"])
    nt.links.new(vz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return m


def random_tint_material(name, c1, c2, rough=0.6, translucent=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.inputs["A"].default_value = hexrgb(c1)
    mx.inputs["B"].default_value = hexrgb(c2)
    nt.links.new(oi.outputs["Random"], mx.inputs["Factor"])
    nt.links.new(mx.outputs["Result"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    if translucent:
        p.inputs["Subsurface Weight"].default_value = translucent
        p.inputs["Subsurface Radius"].default_value = (0.3, 0.6, 0.1)
    p.inputs["Sheen Weight"].default_value = 0.3
    return m


def grass_clump(material):
    bm = bmesh.new()
    rnd = random.Random(3)
    for i in range(18):
        a = rnd.uniform(0, 2 * math.pi)
        lean = rnd.uniform(0.15, 0.6)
        h = rnd.uniform(0.18, 0.42)
        w = rnd.uniform(0.012, 0.022)
        base = Vector((math.cos(a) * 0.04, math.sin(a) * 0.04, 0))
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0)) * w
        prev = None
        for k in range(4):
            u = k / 3
            c = base + d * (lean * h * u * u) + Vector((0, 0, h * u))
            ww = 1 - u
            l = bm.verts.new(c - side * ww)
            r = bm.verts.new(c + side * ww)
            if prev:
                bm.faces.new((prev[0], prev[1], r, l))
            prev = (l, r)
    ob = from_bm("grass_clump", bm, material, None, True, 0)
    ob.location = (0, 0, -100)
    return ob


def fern(material, name="fern", fronds=9, length=1.0, seed=1):
    bm = bmesh.new()
    rnd = random.Random(seed)
    for f in range(fronds):
        a = 2 * math.pi * f / fronds + rnd.uniform(-0.2, 0.2)
        rise = rnd.uniform(0.7, 1.1)
        ln = length * rnd.uniform(0.75, 1.1)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0))
        pts = []
        for k in range(10):
            u = k / 9
            pts.append(d * ln * u + Vector((0, 0, ln * (rise * u - 0.95 * u * u))))
        for k in range(1, 9):
            u = k / 9
            c = pts[k]
            ll = ln * 0.22 * math.sin(math.pi * (0.15 + 0.85 * u)) * (1 - 0.5 * u)
            for s in (-1, 1):
                tip = c + side * s * ll + d * ll * 0.35 - Vector((0, 0, ll * 0.25))
                v1 = bm.verts.new(c)
                v2 = bm.verts.new(c + d * ln * 0.07)
                v3 = bm.verts.new(tip)
                bm.faces.new((v1, v2, v3) if s > 0 else (v2, v1, v3))
        for k in range(9):
            a1, b1 = pts[k], pts[k + 1]
            w = 0.012 * length
            v = [bm.verts.new(a1 - side * w), bm.verts.new(a1 + side * w), bm.verts.new(b1 + side * w), bm.verts.new(b1 - side * w)]
            bm.faces.new(v)
    ob = from_bm(name, bm, material, None, True, 0)
    ob.location = (0, 0, -100)
    return ob


def scatter(emitter, inst, count, group, seed, size=1.0, size_rand=0.4, name="ps"):
    """Hair-particle instancing. Blender aligns an instance's local +X with the hair
    direction, so the prototype mesh is rotated to stand along +X first."""
    if not inst.get("x_up"):
        inst.data.transform(Matrix.Rotation(math.pi / 2, 4, "Y"))
        inst["x_up"] = True
    mod = emitter.modifiers.new(name, "PARTICLE_SYSTEM")
    ps = mod.particle_system
    st = ps.settings
    st.type = "HAIR"
    st.use_advanced_hair = True
    st.count = count
    st.hair_length = 1.0
    st.render_type = "OBJECT"
    st.instance_object = inst
    st.particle_size = size
    st.size_random = size_rand
    st.use_rotations = True
    st.rotation_mode = "GLOB_Z"
    st.phase_factor_random = 2.0
    st.use_rotation_instance = True
    st.emit_from = "FACE"
    st.use_emit_random = True
    st.distribution = "RAND"
    ps.seed = seed
    ps.vertex_group_density = group
    emitter.show_instancer_for_render = True


def lathe(radius_fn, h, segs=20, rings=24, seed=0, wobble=0.1):
    """Trunk as a surface of revolution: radius_fn(u) for u in 0..1 (bottom..top)."""
    bm = bmesh.new()
    rows = []
    for i in range(rings + 1):
        u = i / rings
        z = u * h
        row = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            r = radius_fn(u) * (1 + wobble * noise.noise(Vector((math.cos(a) * 1.5, math.sin(a) * 1.5, z * 0.4 + seed))))
            row.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        rows.append(row)
    for i in range(rings):
        for j in range(segs):
            bm.faces.new((rows[i][j], rows[i][(j + 1) % segs], rows[i + 1][(j + 1) % segs], rows[i + 1][j]))
    top = bm.verts.new((0, 0, h))
    for j in range(segs):
        bm.faces.new((rows[-1][j], rows[-1][(j + 1) % segs], top))
    return bm


def tree(trunk_m, leaf_m, x, y, h, r, seed, crown_subdiv=3, crown_sub=1):
    rnd = random.Random(seed)
    z0 = height(x, y) - 0.3
    root = empty("tree", (x, y, z0))
    bm = lathe(lambda u: r * (0.6 + 0.4 * (1 - u)) * (1 + 1.4 * math.exp(-u * h / 0.9)), h + 1.0, seed=seed)
    from_bm("trunk", bm, trunk_m, root, True, 0)
    for k in range(rnd.randint(2, 4)):
        a = rnd.uniform(0, 2 * math.pi)
        z = h * rnd.uniform(0.55, 0.8)
        end = (math.cos(a) * h * 0.22, math.sin(a) * h * 0.22, z + h * 0.12)
        capsule("branch", (0, 0, z), end, r * 0.32, r * 0.15, trunk_m, root, segs=10)
    for k in range(rnd.randint(6, 9)):
        a = rnd.uniform(0, 2 * math.pi)
        dd = rnd.uniform(0, h * 0.3)
        c = (math.cos(a) * dd, math.sin(a) * dd, h * rnd.uniform(0.7, 1.05) + 1)
        rr = h * rnd.uniform(0.18, 0.27)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=crown_subdiv, radius=rr)
        for v in bm.verts:
            n = noise.noise(v.co * (2.5 / rr) + Vector((seed, k, 0)))
            v.co *= 1 + 0.28 * n
            v.co.z *= 0.6
        from_bm("crown", bm, leaf_m, root, True, crown_sub, loc=c)
    return root


def tree_fern(trunk_m, frond_obj, x, y, h, seed):
    rnd = random.Random(seed)
    root = empty("treefern", (x, y, height(x, y) - 0.1))
    capsule("tf_trunk", (0, 0, 0), (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), h), 0.28, 0.2, trunk_m, root, segs=14)
    inst = bpy.data.objects.new("tf_crown", frond_obj.data)
    link(inst, root)
    inst.location = (0, 0, h)
    inst.scale = (3.2, 3.2, 3.0)
    inst.rotation_euler = (0, 0, rnd.uniform(0, 6.28))
    return root


def rock(m, x, y, s, seed):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=s)
    for v in bm.verts:
        n = noise.noise(v.co * (1.6 / s) + Vector((seed, 0, 0)))
        v.co *= 1 + 0.3 * n
        v.co.z *= 0.65
    return from_bm("rock", bm, m, None, True, 1, loc=(x, y, height(x, y) - s * 0.25))


def mountains(m, volc_m):
    for i, (ang, dist, w, hgt, seed) in enumerate(((1.75, 420, 520, 160, 1), (2.3, 380, 420, 120, 2), (1.2, 460, 600, 190, 3),
                                                    (0.6, 400, 500, 140, 4), (2.9, 430, 480, 150, 5), (-0.3, 420, 520, 120, 6))):
        cx, cy = math.cos(ang) * dist, math.sin(ang) * dist
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=60, y_segments=30, size=1.0)
        for v in bm.verts:
            u, vv = v.co.x, v.co.y
            ridge = max(0.0, 1 - abs(vv) * 2.0) * max(0.0, 1 - abs(u) * 1.2)
            n = noise.noise(Vector((u * 4 + seed, vv * 4, seed))) * 0.5 + noise.noise(Vector((u * 12, vv * 12, seed))) * 0.15
            v.co = Vector((u * w, vv * w * 0.6, hgt * (ridge * (0.7 + n)) ** 1.2 - 20))
        ob = from_bm("mountain", bm, m, None, True, 0, loc=(cx, cy, 0))
        ob.rotation_euler = (0, 0, ang + math.pi / 2)
    # volcano
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=260, radius2=24, depth=210)
    for v in bm.verts:
        n = noise.noise(v.co * 0.02 + Vector((9, 9, 9)))
        v.co.x *= 1 + 0.08 * n
        v.co.y *= 1 + 0.08 * n
    from_bm("volcano", bm, volc_m, None, True, 1, loc=(math.cos(1.45) * 560, math.sin(1.45) * 560, 85))


def sky(sc, sun_elev=30.0, sun_rot=118.0, strength=0.3):
    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    sk = nt.nodes.new("ShaderNodeTexSky")
    sk.sky_type = "MULTIPLE_SCATTERING"
    sk.sun_disc = False
    sk.sun_elevation = math.radians(sun_elev)
    sk.sun_rotation = math.radians(sun_rot)
    sk.air_density = 1.0
    sk.aerosol_density = 1.0
    nt.links.new(sk.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    # sun lamp along the same direction
    sd = Vector((math.sin(math.radians(sun_rot)) * math.cos(math.radians(sun_elev)),
                 -math.cos(math.radians(sun_rot)) * math.cos(math.radians(sun_elev)),
                 math.sin(math.radians(sun_elev))))
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy = 5.0
    ld.angle = math.radians(2.0)
    ld.color = (1.0, 0.86, 0.68)
    lo = bpy.data.objects.new("sun", ld)
    link(lo)
    lo.rotation_euler = (-sd).to_track_quat("-Z", "Y").to_euler()
    return sd


def build(sc):
    sd = sky(sc)
    gm = ground_material()
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=220, y_segments=220, size=150)
    for v in bm.verts:
        v.co.z = height(v.co.x, v.co.y)
    ground = from_bm("ground", bm, gm, None, True, 0)
    vg = ground.vertex_groups.new(name="grass")
    vf = ground.vertex_groups.new(name="ferns")
    for v in ground.data.vertices:
        x, y = v.co.x, v.co.y
        d = math.hypot(x, y)
        near = 1 - min(1, max(0, (d - 30) / 15))
        path = min(1, max(0, (abs(y - PATH_Y) - 0.9) / 1.2)) if x < 9 else 1.0
        vg.add([v.index], near * (0.25 + 0.75 * path), "REPLACE")
        ring = min(1, max(0, (d - 5) / 6)) * near
        vf.add([v.index], ring * path, "REPLACE")
    gmat = random_tint_material("grass", "#4d6e25", "#86a03a", rough=0.55)
    fmat = random_tint_material("fernmat", "#2f5a20", "#4f8030", rough=0.5)
    clump = grass_clump(gmat)
    fn = fern(fmat, "fern", 9, 0.9, 1)
    scatter(ground, clump, 55000, "grass", 1, size=1.0, size_rand=0.5, name="grass")
    scatter(ground, fn, 1100, "ferns", 2, size=1.0, size_rand=0.5, name="ferns")
    bark = mat("bark", "#4a3626", rough=0.85, color2="#2e2117", noise_mix=0.7, noise_scale=3, bump=0.6, bump_scale=8)
    leaves = random_tint_material("leaves", "#23461c", "#3e6a24", rough=0.7)
    rnd = random.Random(11)
    # ring of giant trees, with a gap toward the far mountains and two trunks framing the T-Rex's way in
    for i in range(30):
        ang = rnd.uniform(0, 2 * math.pi)
        if 1.2 < ang < 2.1 or 0.0 < ang < 0.75:
            continue
        d = rnd.uniform(15, 34)
        x, y = math.cos(ang) * d, math.sin(ang) * d
        if abs(x + 1.5) < 4.5 and y > 0:
            continue
        tree(bark, leaves, x, y, rnd.uniform(10, 16), rnd.uniform(0.45, 0.8), i)
    tree(bark, leaves, -6.8, 14.5, 15, 0.9, 101)
    tree(bark, leaves, 3.8, 15.5, 14, 0.8, 102)
    tree(bark, leaves, -10.5, 21, 13, 0.7, 103)
    # dense forest belt in the distance (instanced)
    vfo = ground.vertex_groups.new(name="forest")
    for v in ground.data.vertices:
        d = math.hypot(v.co.x, v.co.y)
        ang = math.atan2(v.co.y, v.co.x)
        gap = 0.25 if 1.25 < ang < 2.05 else 1.0
        w = min(1, max(0, (d - 34) / 6)) * (1 - min(1, max(0, (d - 120) / 20))) * gap
        vfo.add([v.index], w, "REPLACE")
    protos = []
    for j in range(3):
        rt = tree(bark, leaves, 0, 0, 12 + 3 * j, 0.6, 500 + j, crown_subdiv=2, crown_sub=0)
        bpy.context.view_layer.update()
        parts = [c for c in rt.children]
        bmj = bmesh.new()
        for c in parts:
            me = c.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
            mtx = c.matrix_local
            tmp = bmesh.new()
            tmp.from_mesh(me)
            for f in tmp.faces:
                f.material_index = 0 if c.name.startswith(("trunk", "branch")) else 1
            bmesh.ops.transform(tmp, matrix=mtx, verts=tmp.verts)
            me2 = bpy.data.meshes.new("tmp")
            tmp.to_mesh(me2)
            bmj.from_mesh(me2)
            tmp.free()
        for c in parts:
            bpy.data.objects.remove(c)
        bpy.data.objects.remove(rt)
        po = from_bm("forest_proto", bmj, [bark, leaves], None, True, 0)
        po.location = (0, 0, -200)
        protos.append(po)
    for j, po in enumerate(protos):
        scatter(ground, po, 170, "forest", 30 + j, size=1.0, size_rand=0.35, name="forest%d" % j)
    frond_big = fern(fmat, "frond_big", 12, 1.0, 7)
    for i, (x, y) in enumerate(((-9, 9), (8, 10), (11, -5), (-12, -4), (-5, 13), (6, 14), (13, 4), (-14, 6), (2, -12), (-7, -11))):
        tree_fern(bark, frond_big, x, y, rnd.uniform(2.5, 4.5), i)
    rm = mat("rockmat", "#76705f", rough=0.85, color2="#4e5a2c", noise_mix=0.5, noise_scale=1.5, bump=0.5, bump_scale=6)
    for i, (x, y, s) in enumerate(((-8, -3, 1.0), (7, 4, 1.4), (-3, 8, 0.8), (10, -7, 1.6), (-11, 2, 1.2), (4, -9, 0.9))):
        rock(rm, x, y, s, i)
    mm = mat("mountain", "#3f5640", rough=0.9, color2="#2c3d2c", noise_mix=0.6, noise_scale=0.01)
    vm = mat("volcano", "#4a4440", rough=0.9)
    mountains(mm, vm)
    return ground, sd
