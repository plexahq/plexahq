"""Blender helpers: scene reset, materials, primitive meshes, empties and an
atmospheric haze that is added to every material (cheap aerial perspective)."""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector, Quaternion


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    addon_utils.enable("cycles", default_set=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    return sc


# ----------------------------------------------------------------- materials
def hexrgb(h, a=1.0):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    # sRGB -> linear
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (c[0], c[1], c[2], a)


def mat(name, color, rough=0.5, sss=0.0, sss_radius=(0.8, 0.3, 0.2), metal=0.0, sheen=0.0, coat=0.0, spec=0.5,
        emit=None, emit_strength=1.0, color2=None, noise_scale=6.0, noise_mix=0.0, bump=0.0, bump_scale=30.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    col = hexrgb(color) if isinstance(color, str) else color
    p.inputs["Base Color"].default_value = col
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Specular IOR Level"].default_value = spec
    if sss:
        p.subsurface_method = "BURLEY"
        p.inputs["Subsurface Weight"].default_value = sss
        p.inputs["Subsurface Radius"].default_value = sss_radius
        p.inputs["Subsurface Scale"].default_value = 0.05
    if sheen:
        p.inputs["Sheen Weight"].default_value = sheen
    if coat:
        p.inputs["Coat Weight"].default_value = coat
    if emit is not None:
        p.inputs["Emission Color"].default_value = hexrgb(emit) if isinstance(emit, str) else emit
        p.inputs["Emission Strength"].default_value = emit_strength
    if color2 is not None and noise_mix > 0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = noise_scale
        nz.inputs["Detail"].default_value = 6
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.inputs["A"].default_value = col
        mx.inputs["B"].default_value = hexrgb(color2) if isinstance(color2, str) else color2
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value = 0.35
        ramp.inputs["From Max"].default_value = 0.65
        nt.links.new(nz.outputs["Fac"], ramp.inputs["Value"])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = noise_mix
        nt.links.new(ramp.outputs["Result"], mul.inputs[0])
        nt.links.new(mul.outputs[0], mx.inputs["Factor"])
        nt.links.new(mx.outputs["Result"], p.inputs["Base Color"])
    if bump > 0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = bump_scale
        nz.inputs["Detail"].default_value = 8
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        nt.links.new(nz.outputs["Fac"], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    return m


def emission_mat(name, color, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = hexrgb(color) if isinstance(color, str) else color
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


def add_haze(color=(0.75, 0.68, 0.55), dist=140.0, max_fac=0.92, skip=()):
    """Blend every material toward a haze colour with camera distance."""
    for m in bpy.data.materials:
        if m.name in skip or not m.use_nodes:
            continue
        nt = m.node_tree
        out = nt.nodes.get("Material Output")
        if out is None or not out.inputs["Surface"].is_linked:
            continue
        src = out.inputs["Surface"].links[0].from_socket
        cam = nt.nodes.new("ShaderNodeCameraData")
        div = nt.nodes.new("ShaderNodeMath")
        div.operation = "DIVIDE"
        div.inputs[1].default_value = -dist
        nt.links.new(cam.outputs["View Distance"], div.inputs[0])
        ex = nt.nodes.new("ShaderNodeMath")
        ex.operation = "EXPONENT"
        nt.links.new(div.outputs[0], ex.inputs[0])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "MULTIPLY_ADD"
        inv.inputs[1].default_value = -max_fac
        inv.inputs[2].default_value = max_fac
        nt.links.new(ex.outputs[0], inv.inputs[0])
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*color, 1)
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(inv.outputs[0], mix.inputs["Fac"])
        nt.links.new(src, mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])


# ----------------------------------------------------------------- objects
def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = Matrix.Identity(4)
    return obj


def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.05
    link(e, parent)
    e.location = loc
    e.rotation_euler = rot
    return e


def from_bm(name, bm, material=None, parent=None, smooth=True, subsurf=0, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    link(ob, parent)
    ob.location, ob.rotation_euler, ob.scale = loc, rot, scale
    if material is not None:
        if isinstance(material, (list, tuple)):
            for m in material:
                me.materials.append(m)
        else:
            me.materials.append(material)
    if subsurf:
        mod = ob.modifiers.new("sub", "SUBSURF")
        mod.levels = min(1, subsurf)
        mod.render_levels = subsurf
    return ob


def sphere(name, r, material, loc=(0, 0, 0), scale=(1, 1, 1), parent=None, rot=(0, 0, 0), segs=32, rings=16, subsurf=0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    return from_bm(name, bm, material, parent, True, subsurf, loc, rot, scale)


def _orient(a, b):
    d = Vector(b) - Vector(a)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized()) if d.length > 1e-9 else Quaternion()
    return d.length, q


def capsule(name, a, b, ra, rb, material, parent=None, segs=24):
    """Tapered capsule from point a to b (in parent space)."""
    ln, q = _orient(a, b)
    bm = bmesh.new()
    m = Matrix.Translation(Vector(a)) @ q.to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=segs, radius1=ra, radius2=rb, depth=ln,
                          matrix=m @ Matrix.Translation((0, 0, ln / 2)))
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=ra, matrix=Matrix.Translation(Vector(a)))
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=rb, matrix=Matrix.Translation(Vector(b)))
    return from_bm(name, bm, material, parent, True, 0)


def rounded_box(name, size, material, loc=(0, 0, 0), parent=None, rot=(0, 0, 0), bevel=0.3, subsurf=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    ob = from_bm(name, bm, material, parent, True, 0, loc, rot)
    bv = ob.modifiers.new("bev", "BEVEL")
    bv.width = min(size) * bevel
    bv.segments = 3
    if subsurf:
        s = ob.modifiers.new("sub", "SUBSURF")
        s.levels = 1
        s.render_levels = subsurf
    return ob


def torus(name, major, minor, material, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    bm = bmesh.new()
    seg, ring = 40, 16
    verts = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        row = []
        for j in range(ring):
            b = 2 * math.pi * j / ring
            r = major + minor * math.cos(b)
            row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), minor * math.sin(b))))
        verts.append(row)
    for i in range(seg):
        for j in range(ring):
            bm.faces.new((verts[i][j], verts[(i + 1) % seg][j], verts[(i + 1) % seg][(j + 1) % ring], verts[i][(j + 1) % ring]))
    return from_bm(name, bm, material, parent, True, 0, loc, rot)


def look_at(obj, target, roll=0.0):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if roll:
        obj.rotation_euler.rotate_axis("Z", roll)
