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


# ------------------------------------------------------------------ litter on land (no bobbing)
LITTER_SLOTS = ["M_LitterPaper", "M_LitterPlastic", "M_LitterRed", "M_LitterBlue", "M_LitterYellow", "M_LitterSilver",
                "M_LitterGreen", "M_LitterLeaf", "M_LitterMarigold", "M_LitterBrown"]


def _merge(bm, sub, mat_index, offset, rot=0.0, tilt=0.0):
    from mathutils import Matrix
    M = Matrix.Translation(offset) @ Matrix.Rotation(rot, 4, "Z") @ Matrix.Rotation(tilt, 4, "X")
    bmesh.ops.transform(sub, matrix=M, verts=sub.verts)
    me = bpy.data.meshes.new("tmp")
    sub.to_mesh(me)
    sub.free()
    n0 = len(bm.faces)
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.material_index = mat_index
    bpy.data.meshes.remove(me)


def _crumple(size, seed, flat=0.25):
    sub = bmesh.new()
    bmesh.ops.create_grid(sub, x_segments=4, y_segments=4, size=size * 0.5)
    off = Vector((seed * 2.3, seed * 0.7, 0))
    for v in sub.verts:
        p = v.co * (4.0 / max(size, 0.01)) + off
        v.co.z += abs(noise.noise(p)) * size * flat + 0.004
        v.co.x += noise.noise(p + Vector((3, 0, 0))) * size * 0.15
        v.co.y += noise.noise(p + Vector((0, 3, 0))) * size * 0.15
    return sub


def _ball(r, seed):
    sub = bmesh.new()
    bmesh.ops.create_icosphere(sub, subdivisions=1, radius=r)
    for v in sub.verts:
        v.co *= 1.0 + 0.35 * noise.noise(v.co * 30 + Vector((seed, 0, 0)))
        v.co.z = v.co.z * 0.75 + r * 0.7
    return sub


def _cup(seed):
    sub = bmesh.new()
    bmesh.ops.create_cone(sub, cap_ends=False, segments=8, radius1=0.028, radius2=0.04, depth=0.09)
    return sub


def _plate(r):
    sub = bmesh.new()
    bmesh.ops.create_circle(sub, cap_ends=True, segments=10, radius=r)
    for v in sub.verts:
        v.co.z = 0.006 + (v.co.length / r) ** 2 * 0.015
    return sub


def _lying_bottle():
    sub = bmesh.new()
    bmesh.ops.create_cone(sub, cap_ends=True, segments=8, radius1=0.035, radius2=0.035, depth=0.22)
    from mathutils import Matrix
    bmesh.ops.rotate(sub, verts=sub.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    for v in sub.verts:
        v.co.z += 0.035
    return sub


def _pick(rng, weights):
    tot = sum(w for _, w in weights)
    r = rng.uniform(0, tot)
    for k, w in weights:
        r -= w
        if r <= 0:
            return k
    return weights[-1][0]


def litter_patch(seed, radius, n, kinds=None):
    """A patch of mixed street litter (paper, chip packets, polythene, cups, bottles, leaf plates, flowers)."""
    rng = __import__("random").Random(seed)
    bm = bmesh.new()
    kinds = kinds or [("wrapper", 5), ("paper", 4), ("poly", 3), ("cup", 2), ("bottle", 1.2), ("plate", 1.5),
                      ("leaf", 2), ("flower", 1.2)]
    for i in range(n):
        a = rng.uniform(0, math.tau)
        rr = radius * math.sqrt(rng.random())
        pos = Vector((math.cos(a) * rr, math.sin(a) * rr, 0.0))
        k = _pick(rng, kinds)
        rot = rng.uniform(0, math.tau)
        if k == "wrapper":
            _merge(bm, _crumple(rng.uniform(0.1, 0.2), seed * 31 + i, 0.4), rng.choice([2, 3, 4, 5, 6]), pos, rot)
        elif k == "paper":
            sub = _ball(rng.uniform(0.03, 0.06), i) if rng.random() < 0.5 else _crumple(rng.uniform(0.15, 0.28), seed + i, 0.15)
            _merge(bm, sub, 0 if rng.random() < 0.7 else 9, pos, rot)
        elif k == "poly":
            _merge(bm, _crumple(rng.uniform(0.25, 0.5), seed * 7 + i, 0.3), rng.choice([1, 1, 2, 3, 6]), pos, rot)
        elif k == "cup":
            _merge(bm, _cup(i), 1 if rng.random() < 0.6 else 9, pos + Vector((0, 0, 0.04)), rot, math.radians(90))
        elif k == "bottle":
            _merge(bm, _lying_bottle(), rng.choice([1, 3, 6]), pos, rot)
        elif k == "plate":
            _merge(bm, _plate(rng.uniform(0.1, 0.15)), 7 if rng.random() < 0.6 else 1, pos, rot)
        elif k == "leaf":
            _merge(bm, _crumple(rng.uniform(0.06, 0.12), i, 0.1), 7 if rng.random() < 0.5 else 9, pos, rot)
        else:
            _merge(bm, _ball(0.03, i), 8, pos, rot)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, LITTER_SLOTS


def garbage_heap(seed, radius, height):
    """Dumped garbage mound: dark compost/dirt dome studded with polythene, packets, plates and bottles."""
    rng = __import__("random").Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=8, radius=radius)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.01], context="VERTS")
    for v in bm.verts:
        n = noise.noise(v.co * 1.7 + Vector((seed, 0, 0)))
        v.co.z = max(0.0, v.co.z) * (height / radius) * (1 + 0.3 * n)
        v.co.x *= 1 + 0.25 * noise.noise(v.co * 0.9 + Vector((0, seed, 0)))
        v.co.y *= 1 + 0.25 * noise.noise(v.co * 0.9 + Vector((seed, seed, 0)))
    for f in bm.faces:
        f.material_index = 10
    for i in range(int(radius * radius * 55)):
        a = rng.uniform(0, math.tau)
        rr = radius * 0.95 * math.sqrt(rng.random())
        z = height * max(0.0, 1 - (rr / radius) ** 2) ** 0.5
        pos = Vector((math.cos(a) * rr, math.sin(a) * rr, z * 0.92))
        tilt = (rr / radius) * 0.9
        k = _pick(rng, [("poly", 5), ("wrapper", 4), ("paper", 2), ("plate", 1.5), ("bottle", 1)])
        if k == "poly":
            _merge(bm, _crumple(rng.uniform(0.3, 0.6), seed * 11 + i, 0.45), rng.choice([1, 1, 2, 3, 6, 9]), pos, a, tilt)
        elif k == "wrapper":
            _merge(bm, _crumple(rng.uniform(0.12, 0.22), i, 0.4), rng.choice([2, 3, 4, 5, 6]), pos, a, tilt)
        elif k == "paper":
            _merge(bm, _ball(rng.uniform(0.04, 0.07), i), 0, pos, a)
        elif k == "plate":
            _merge(bm, _plate(0.13), 7, pos, a, tilt)
        else:
            _merge(bm, _lying_bottle(), rng.choice([1, 3]), pos, a, tilt)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, LITTER_SLOTS + ["M_LitterHeap"]


def styro_bits(seed, n, spread):
    """Floating white styrofoam / thermocol plates and chunks (the reference river is full of them)."""
    rng = __import__("random").Random(seed)
    bm = bmesh.new()
    for i in range(n):
        a = rng.uniform(0, math.tau)
        rr = spread * math.sqrt(rng.random())
        sub = bmesh.new()
        if rng.random() < 0.5:
            bmesh.ops.create_cube(sub, size=1.0)
            sx, sy, sz = rng.uniform(0.06, 0.25), rng.uniform(0.05, 0.18), rng.uniform(0.02, 0.05)
            for v in sub.verts:
                v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz + sz * 0.3))
        else:
            sub = _plate(rng.uniform(0.09, 0.14))
        me = bpy.data.meshes.new("s")
        bmesh.ops.rotate(sub, verts=sub.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(rng.uniform(0, 6.3), 3, "Z"))
        bmesh.ops.translate(sub, verts=sub.verts, vec=(math.cos(a) * rr, math.sin(a) * rr, 0))
        sub.to_mesh(me)
        sub.free()
        bm.from_mesh(me)
    return bm, ["M_Foam"]


def floating_trash(seed, n, spread):
    """Mixed floating packets / cups / polythene for the river (bobbing material slots)."""
    rng = __import__("random").Random(seed)
    bm = bmesh.new()
    slots = ["M_Plastic", "M_PlasticBlue", "M_Marigold", "M_Foam", "M_Leaf"]
    for i in range(n):
        a = rng.uniform(0, math.tau)
        rr = spread * math.sqrt(rng.random())
        pos = Vector((math.cos(a) * rr, math.sin(a) * rr, 0.0))
        k = _pick(rng, [("poly", 4), ("wrapper", 3), ("cup", 2), ("plate", 2), ("flower", 2)])
        if k == "poly":
            _merge(bm, _crumple(rng.uniform(0.2, 0.45), seed + i, 0.2), rng.choice([0, 0, 1]), pos, a)
        elif k == "wrapper":
            _merge(bm, _crumple(rng.uniform(0.1, 0.18), i, 0.3), rng.choice([0, 1, 2]), pos, a)
        elif k == "cup":
            _merge(bm, _cup(i), 3, pos + Vector((0, 0, 0.02)), a, math.radians(90))
        elif k == "plate":
            _merge(bm, _plate(rng.uniform(0.1, 0.15)), rng.choice([3, 4]), pos, a)
        else:
            _merge(bm, _ball(0.03, i), 2, pos, a)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, slots


def umbrella(slot):
    """Open umbrella: handle at the origin (held in the hand), 8-panel canopy ~1 m across above."""
    bm = bmesh.new()
    # shaft + curved handle
    sub = bmesh.new()
    bmesh.ops.create_cone(sub, cap_ends=True, segments=6, radius1=0.009, radius2=0.009, depth=1.0)
    bmesh.ops.translate(sub, verts=sub.verts, vec=(0, 0, 0.5))
    me = bpy.data.meshes.new("u")
    sub.to_mesh(me)
    sub.free()
    bm.from_mesh(me)
    n_shaft = len(bm.faces)
    # canopy: rim at z 0.93, apex 1.13, panels slightly scalloped between ribs
    segs, rings = 8, 4
    apex = bm.verts.new((0, 0, 1.13))
    rim_r, rim_z = 0.52, 0.93
    grid = []
    for k in range(1, rings + 1):
        ring = []
        f = k / rings
        for i in range(segs * 2):
            a = i / (segs * 2) * math.tau
            scallop = 0.0 if i % 2 == 0 else -0.035 * f
            r = rim_r * f
            z = 1.13 - (1.13 - rim_z) * (f ** 1.4) + scallop
            ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        grid.append(ring)
    n = segs * 2
    for i in range(n):
        bm.faces.new((apex, grid[0][i], grid[0][(i + 1) % n]))
    for k in range(rings - 1):
        for i in range(n):
            bm.faces.new((grid[k][i], grid[k + 1][i], grid[k + 1][(i + 1) % n], grid[k][(i + 1) % n]))
    bm.faces.ensure_lookup_table()
    for j, f in enumerate(bm.faces):
        f.material_index = 1 if j < n_shaft else 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, [slot, "M_WindowDark"]


def chai_glass():
    """Cutting-chai glass (6 cm, ribbed, half full of milky tea). Origin = glass centre (held in the hand)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.026, radius2=0.032, depth=0.085)
    for f in bm.faces:
        f.material_index = 0
    tea = bmesh.new()
    bmesh.ops.create_cone(tea, cap_ends=True, segments=10, radius1=0.024, radius2=0.029, depth=0.055)
    bmesh.ops.translate(tea, verts=tea.verts, vec=(0, 0, -0.012))
    me = bpy.data.meshes.new("t")
    tea.to_mesh(me)
    tea.free()
    n0 = len(bm.faces)
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.material_index = 1
    return bm, ["M_ChaiGlass", "M_ChaiTea"]


def kettle():
    """Brass chai kettle held up by the chai-wallah: pot, lid knob, spout, handle. Origin = handle grip."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=0.09)
    for v in bm.verts:
        v.co.z *= 0.85
        v.co += Vector((0.0, 0.0, -0.13))
    sp = bmesh.new()
    bmesh.ops.create_cone(sp, cap_ends=False, segments=6, radius1=0.016, radius2=0.008, depth=0.13)
    from mathutils import Matrix
    bmesh.ops.rotate(sp, verts=sp.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(55), 3, "Y"))
    bmesh.ops.translate(sp, verts=sp.verts, vec=(0.12, 0, -0.1))
    me = bpy.data.meshes.new("s")
    sp.to_mesh(me)
    sp.free()
    bm.from_mesh(me)
    hd = bmesh.new()
    bmesh.ops.create_cone(hd, cap_ends=True, segments=6, radius1=0.008, radius2=0.008, depth=0.14)
    bmesh.ops.rotate(hd, verts=hd.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    bmesh.ops.translate(hd, verts=hd.verts, vec=(-0.02, 0, 0))
    me2 = bpy.data.meshes.new("h")
    hd.to_mesh(me2)
    hd.free()
    bm.from_mesh(me2)
    return bm, ["M_BrassKettle"]


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
    for i in range(4):
        jobs.append((f"Litter_Patch_{i}", lambda i=i: litter_patch(100 + i, R.uniform(0.9, 1.6), R.randint(22, 40))))
    jobs.append(("Litter_Strip", lambda: litter_patch(200, 3.0, 90)))
    jobs.append(("Litter_Flowers", lambda: litter_patch(210, 1.0, 45, [("flower", 6), ("plate", 2), ("leaf", 3), ("poly", 1)])))
    for i in range(3):
        jobs.append((f"Garbage_Heap_{i}", lambda i=i: garbage_heap(300 + i, R.uniform(1.0, 1.8), R.uniform(0.45, 0.8))))
    for i in range(2):
        jobs.append((f"Debris_Styro_{i}", lambda i=i: styro_bits(400 + i, 14, 0.9)))
    for i in range(3):
        jobs.append((f"Debris_Trash_{i}", lambda i=i: floating_trash(500 + i, 26, 1.2)))
    for col in ("Red", "Yellow", "Blue", "Green", "Black", "Pink"):
        jobs.append((f"Umbrella_{col}", lambda col=col: umbrella(f"M_Umbrella{col}")))
    jobs.append(("Prop_ChaiGlass", chai_glass))
    jobs.append(("Prop_Kettle", kettle))
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
