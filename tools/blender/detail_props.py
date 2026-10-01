"""Small detail meshes for the 'lived-in' Varanasi look (matches the reference video):
floating river garbage / offerings and sagging electric wires between poles.

blender -b --python detail_props.py
Outputs FBX (1 m = 100 UE cm, centred pivots) to ~/gta-india/assets/detail/ and a props-style manifest.
"""
import bmesh
import bpy
import json
import math
import os
import random
from mathutils import Vector, noise

OUT = os.path.expanduser("~/gta-india/assets/detail")
R = random.Random(11)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def obj_from_bm(bm, name, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(mat(m))
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def uv_box(o, scale=1.0):
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=scale)
    bpy.ops.object.mode_set(mode="OBJECT")


def export(o, name, info):
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    path = os.path.join(OUT, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Z", axis_up="Y", object_types={"MESH"}, mesh_smooth_type="FACE", bake_anim=False)
    dims = [round(d, 3) for d in o.dimensions]
    info[name] = {"file": path, "bounds_m": dims, "materials": [m.name for m in o.data.materials]}
    print("OK", name, dims)


def crumpled_sheet(size, seed, slot):
    """Floating plastic bag / rag: a noisy, slightly domed sheet."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=10, y_segments=10, size=size * 0.5)
    off = Vector((seed * 3.1, seed * 1.7, 0))
    for v in bm.verts:
        p = v.co * (3.0 / size) + off
        v.co.z += noise.noise(p) * size * 0.18 + max(0.0, 0.5 - v.co.length / size) * size * 0.25
        v.co.x += noise.noise(p + Vector((5, 0, 0))) * size * 0.12
        v.co.y += noise.noise(p + Vector((0, 5, 0))) * size * 0.12
    # ragged edge: drop some boundary verts inward
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, [slot]


def bottle():
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.035, radius2=0.035, depth=0.2)
    neck = bmesh.new()
    bmesh.ops.create_cone(neck, cap_ends=True, segments=8, radius1=0.035, radius2=0.012, depth=0.06)
    me = bpy.data.meshes.new("tmp")
    neck.to_mesh(me)
    neck.free()
    bm.from_mesh(me)
    for v in bm.verts[-len(me.vertices):]:
        v.co.z += 0.13
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "Y"))
    return bm, ["M_PlasticBlue"]


def marigold_cluster(n, spread):
    """Loose marigold flowers / a broken garland floating on the water."""
    bm = bmesh.new()
    for i in range(n):
        a = R.uniform(0, math.tau)
        r = R.uniform(0, spread)
        c = Vector((math.cos(a) * r, math.sin(a) * r, 0.0))
        sub = bmesh.new()
        bmesh.ops.create_icosphere(sub, subdivisions=1, radius=R.uniform(0.022, 0.035))
        for v in sub.verts:
            v.co.z *= 0.6
            v.co += c
        me = bpy.data.meshes.new("f")
        sub.to_mesh(me)
        sub.free()
        bm.from_mesh(me)
    return bm, ["M_Marigold"]


def leaf_bowl():
    """Dona (leaf bowl) with a diya and flowers: the classic Ganga offering."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=0.09)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.0], context="VERTS")
    for v in bm.verts:
        v.co.z *= 0.45
        v.co.z += 0.04
    leaf_faces = list(bm.faces)
    me = bpy.data.meshes.new("fl")
    fl = bmesh.new()
    for i in range(7):
        a = i / 7 * math.tau
        bmesh.ops.create_icosphere(fl, subdivisions=1, radius=0.018)
        for v in fl.verts[-12:]:
            v.co += Vector((math.cos(a) * 0.045, math.sin(a) * 0.045, 0.04))
    fl.to_mesh(me)
    fl.free()
    bm.from_mesh(me)
    for f in bm.faces:
        f.material_index = 0 if f in leaf_faces else 1
    return bm, ["M_Leaf", "M_Marigold"]


def foam_patch(size, seed):
    bm = bmesh.new()
    segs = 18
    verts = []
    for i in range(segs):
        a = i / segs * math.tau
        r = size * (0.5 + 0.25 * noise.noise(Vector((math.cos(a) * 2 + seed, math.sin(a) * 2, 0))))
        verts.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, 0.005)))
    bm.faces.new(verts)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    return bm, ["M_Foam"]


def catenary_wires(span=35.0, sag=1.1):
    """Four sagging wires between two poles (pivot at the mid-span, at ground level)."""
    bm = bmesh.new()
    points = [(-0.87, 8.85), (-0.32, 8.85), (0.32, 8.85), (0.87, 8.85), (-0.62, 7.9), (0.62, 7.9)]
    segs = 24
    for (y, z) in points:
        ring_prev = None
        for i in range(segs + 1):
            t = i / segs
            x = (t - 0.5) * span
            zz = z - sag * (1 - (2 * t - 1) ** 2) + (0.15 if y < 0 else 0.0) * math.sin(t * math.pi)
            ring = []
            for k in range(4):
                a = k / 4 * math.tau
                ring.append(bm.verts.new((x, y + math.cos(a) * 0.008, zz + math.sin(a) * 0.008)))
            if ring_prev:
                for k in range(4):
                    bm.faces.new((ring_prev[k], ring_prev[(k + 1) % 4], ring[(k + 1) % 4], ring[k]))
            ring_prev = ring
    return bm, ["M_WindowDark"]


def tangled_wires():
    """A messy bundle of service wires hanging from a pole to a building (very Indian street)."""
    bm = bmesh.new()
    segs = 16
    for w in range(9):
        y0 = R.uniform(-0.2, 0.2)
        z0 = R.uniform(6.6, 7.4)
        y1 = R.uniform(4.5, 6.5)
        z1 = R.uniform(4.8, 6.4)
        sag = R.uniform(0.3, 1.0)
        prev = None
        for i in range(segs + 1):
            t = i / segs
            p = Vector((R.uniform(-0.02, 0.02), y0 + (y1 - y0) * t, z0 + (z1 - z0) * t - sag * math.sin(t * math.pi)))
            ring = [bm.verts.new(p + Vector((0, math.cos(k / 3 * math.tau) * 0.006, math.sin(k / 3 * math.tau) * 0.006))) for k in range(3)]
            if prev:
                for k in range(3):
                    bm.faces.new((prev[k], prev[(k + 1) % 3], ring[(k + 1) % 3], ring[k]))
            prev = ring
    return bm, ["M_WindowDark"]


def build():
    info = {}
    jobs = []
    for i in range(3):
        jobs.append((f"Debris_Bag_{i}", lambda i=i: crumpled_sheet(R.uniform(0.35, 0.6), i, "M_Plastic")))
    for i in range(2):
        jobs.append((f"Debris_Rag_{i}", lambda i=i: crumpled_sheet(R.uniform(0.5, 0.8), 10 + i, "M_Cloth")))
    jobs.append(("Debris_Bottle", bottle))
    jobs.append(("Debris_Marigolds_A", lambda: marigold_cluster(14, 0.25)))
    jobs.append(("Debris_Marigolds_B", lambda: marigold_cluster(30, 0.5)))
    jobs.append(("Debris_LeafBowl", leaf_bowl))
    for i in range(2):
        jobs.append((f"Debris_Foam_{i}", lambda i=i: foam_patch(R.uniform(0.6, 1.4), i * 7)))
    jobs.append(("Wires_Span_35m", catenary_wires))
    jobs.append(("Wires_Tangle", tangled_wires))
    for name, fn in jobs:
        reset()
        bm, mats = fn()
        o = obj_from_bm(bm, name, mats)
        uv_box(o, 0.5)
        export(o, name, info)
    json.dump(info, open(os.path.join(OUT, "detail_manifest.json"), "w"), indent=1)


build()
