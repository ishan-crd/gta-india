# blender -b --python inspect_gltf.py -- file.gltf
import bpy, sys
path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
for o in bpy.data.objects:
    if o.type == "ARMATURE":
        bones = [b.name for b in o.data.bones]
        print("ARMATURE", o.name, len(bones), bones[:70])
    elif o.type == "MESH":
        print("MESH", o.name, len(o.data.polygons), "dims", tuple(round(d, 2) for d in o.dimensions), "mats", [m.name for m in o.data.materials if m])
for a in bpy.data.actions:
    print("ACTION", a.name, a.frame_range[:])
