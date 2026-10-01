"""Convert downloaded glTF props into clean FBX static meshes for UE.

blender -b -t 8 --python convert_props.py -- <name> [<name> ...]   (no names = all)

Each prop: import glTF, drop junk / skinning / animation, apply transforms, join into one mesh,
orient the longest horizontal axis along +X (optional per prop), scale to a real-world size,
put the pivot at the bottom centre, export FBX (1 m = 100 UE cm) with textures copied.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Matrix, Vector

HOME = os.path.expanduser("~")
SRC = f"{HOME}/gta-india/assets"
OUT = f"{HOME}/gta-india/assets/props"

# name: (source gltf relative to assets, size_m, size_axis, align_long_axis_to_x, extra_yaw_deg)
PROPS = {
    "AutoRickshaw": ("sketchfab/autorickshaw/scene.gltf", 2.65, "long", True, 0),
    "AutoRickshaw2": ("sketchfab/autorickshaw2/scene.gltf", 2.65, "long", True, 0),
    "TrainCoachLHB": ("sketchfab/train_lhb/scene.gltf", 23.5, "long", True, 0),
    "TrainIndian": ("sketchfab/train_indian/scene.gltf", 21.3, "long", True, 0),
    "TrainAnim": ("sketchfab/train_anim/scene.gltf", 21.3, "long", True, 0),
    "TemplesSet": ("sketchfab/temples/scene.gltf", 14.0, "height", False, 0),
    "HinduTemple": ("sketchfab/hindu_temple/scene.gltf", 16.0, "height", False, 0),
    "KiranaShop": ("sketchfab/kirana_shop/scene.gltf", 3.4, "height", False, 0),
    "BhelpuriShop": ("sketchfab/bhelpuri_shop/scene.gltf", 2.4, "height", False, 0),
    "BoatSF": ("sketchfab/boat/scene.gltf", 6.5, "long", True, 0),
    "BoatOld": ("sketchfab/boat_old/scene.gltf", 5.5, "long", True, 0),
    "BoatWooden": ("sketchfab/boat_wooden/scene.gltf", 5.0, "long", True, 0),
    "Nandi": ("sketchfab/nandi/scene.gltf", 1.3, "height", False, 0),
    "HouseOld": ("sketchfab/house_old/scene.gltf", 7.5, "height", False, 0),
    "BananaTree": ("sketchfab/banana_tree/scene.gltf", 4.5, "height", False, 0),
    "TeaBoiler": ("sketchfab/tea_boiler/scene.gltf", 0.55, "height", False, 0),
    "ChaiBench": ("sketchfab/chai_bench/scene.gltf", 1.8, "long", True, 0),
    "TemplePillar": ("sketchfab/temple_pillar/scene.gltf", 3.2, "height", False, 0),
    "BikePulsar150": ("sketchfab/bike_pulsar150/scene.gltf", 2.03, "long", True, 0),
    "BikePulsar135": ("sketchfab/bike_pulsar135/scene.gltf", 2.0, "long", True, 0),
    "Zebu": ("sketchfab/zebu/scene.gltf", 2.1, "long", True, 0),
    "Zebu2": ("sketchfab/zebu2/scene.gltf", 2.1, "long", True, 0),
    "Buffalo": ("sketchfab/buffalo/scene.gltf", 2.5, "long", True, 0),
    "CarWagonR": ("sketchfab/car_wagonr/scene.gltf", 3.6, "long", True, 0),
    "CarNano": ("sketchfab/car_nano/scene.gltf", 3.1, "long", True, 0),
}

# Poly Haven models are already real-world scale (metres) and Z-up after glTF import.
PH = f"{SRC}/polyhaven/models"


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def bake_world(meshes):
    """Unparent meshes keeping their world transform BEFORE deleting parents, then apply transforms."""
    bpy.context.view_layer.update()
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in list(bpy.data.objects):
        if o not in meshes:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()


def world_bounds(objs):
    bpy.context.view_layer.update()
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def convert(name, src, size_m, axis, align, yaw, out_dir):
    reset()
    bpy.ops.import_scene.gltf(filepath=src)
    # Keep only meshes; strip armatures (we export static meshes) while keeping the posed shape.
    for o in list(bpy.data.objects):
        if o.type == "MESH":
            for m in list(o.modifiers):
                if m.type == "ARMATURE":
                    bpy.context.view_layer.objects.active = o
                    try:
                        bpy.ops.object.modifier_apply(modifier=m.name)
                    except Exception:
                        o.modifiers.remove(m)
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name.lower() != "icosphere" and len(o.data.polygons) > 0]
    if not meshes:
        print("NO MESHES", name)
        return None
    bake_world(meshes)
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    obj.rotation_mode = "XYZ"

    lo, hi = world_bounds([obj])
    size = hi - lo
    if align and size.y > size.x:
        obj.rotation_euler = (0, 0, math.radians(90))
        bpy.ops.object.transform_apply(rotation=True)
    if yaw:
        obj.rotation_euler = (0, 0, math.radians(yaw))
        bpy.ops.object.transform_apply(rotation=True)
    lo, hi = world_bounds([obj])
    size = hi - lo
    ref = max(size.x, size.y) if axis == "long" else size.z
    s = size_m / max(ref, 1e-6)
    obj.scale = (s, s, s)
    bpy.ops.object.transform_apply(scale=True)
    lo, hi = world_bounds([obj])
    centre = (lo + hi) * 0.5
    obj.location = (-centre.x, -centre.y, -lo.z)
    bpy.ops.object.transform_apply(location=True)
    lo, hi = world_bounds([obj])

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.fbx")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z", axis_up="Y", object_types={"MESH"}, mesh_smooth_type="FACE",
        path_mode="COPY", embed_textures=False, bake_anim=False, use_mesh_modifiers=True)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    info = {"name": name, "file": path, "bounds_m": [round(v, 3) for v in (hi - lo)], "tris": tris,
            "materials": [m.name for m in obj.data.materials if m]}
    print("OK", json.dumps(info))
    return info


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    manifest_path = os.path.join(OUT, "props_manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    jobs = []
    for name, (rel, size, axis, align, yaw) in PROPS.items():
        jobs.append((name, f"{SRC}/{rel}", size, axis, align, yaw, OUT))
    # Poly Haven models: keep native scale -> size_m=None means no rescale.
    for d in sorted(os.listdir(PH)):
        gl = os.path.join(PH, d, f"{d}.gltf")
        if os.path.exists(gl):
            jobs.append((f"PH_{d}", gl, None, None, False, 0, os.path.join(OUT, "polyhaven")))
    for job in jobs:
        name = job[0]
        if args and name not in args:
            continue
        try:
            if job[2] is None:
                info = convert_native(*job[:2], job[6])
            else:
                info = convert(*job)
            if info:
                manifest[name] = info
        except Exception as e:  # keep going
            print("FAIL", name, e)
    json.dump(manifest, open(manifest_path, "w"), indent=1)


def convert_native(name, src, out_dir):
    reset()
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in list(bpy.data.objects):
        if o not in meshes:
            bpy.data.objects.remove(o, do_unlink=True)
    bake_world(meshes)
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.rotation_mode = "XYZ"
    lo, hi = world_bounds([obj])
    centre = (lo + hi) * 0.5
    obj.location = (-centre.x, -centre.y, -lo.z)
    bpy.ops.object.transform_apply(location=True)
    lo, hi = world_bounds([obj])
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z", axis_up="Y", object_types={"MESH"}, mesh_smooth_type="FACE",
        path_mode="COPY", embed_textures=False, bake_anim=False)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    info = {"name": name, "file": path, "bounds_m": [round(v, 3) for v in (hi - lo)], "tris": tris,
            "materials": [m.name for m in obj.data.materials if m]}
    print("OK", json.dumps(info))
    return info


main()
