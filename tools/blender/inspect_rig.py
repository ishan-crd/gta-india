# blender -b --python inspect_rig.py -- file.gltf : prints armature bones (first 30), rest pose arm direction, actions
import bpy, sys
path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
for o in bpy.data.objects:
    if o.type == "ARMATURE":
        bones = o.data.bones
        names = [b.name for b in bones]
        print("ARM", o.name, len(names), names[:12])
        for key in ("LeftArm", "LeftUpLeg", "Hips"):
            b = next((b for b in bones if b.name.split(":")[-1].split("_")[0] == key), None)
            if b:
                d = (o.matrix_world.to_3x3() @ (b.tail_local - b.head_local)).normalized()
                print("  ", key, "dir", tuple(round(x, 2) for x in d), "head", tuple(round(x, 2) for x in (o.matrix_world @ b.head_local)))
for a in bpy.data.actions:
    print("ACTION", a.name, tuple(round(x, 1) for x in a.frame_range))
