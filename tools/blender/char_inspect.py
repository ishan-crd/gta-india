# blender -b --python char_inspect.py -- file.gltf : dump rig/mesh/action info for character pipeline
import bpy, sys, re
from mathutils import Vector
path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
def canon(n):
    n = n.split(":")[-1]
    return re.sub(r"_\d+$", "", n)
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    extra = ""
    if o.type == "MESH":
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        arm = [m.object.name for m in o.modifiers if m.type == "ARMATURE" and m.object]
        extra = f"tris={tris} mats={[m.name if m else None for m in o.data.materials]} vg={len(o.vertex_groups)} arm={arm}"
    print("OBJ", o.type, repr(o.name), "parent", o.parent.name if o.parent else None, "scale", tuple(round(x, 4) for x in o.matrix_world.to_scale()), extra)
for o in bpy.data.objects:
    if o.type != "ARMATURE":
        continue
    bones = o.data.bones
    print("ARM", o.name, len(bones))
    print("  names", [canon(b.name) for b in bones])
    print("  raw", [b.name for b in bones][:8])
    for key in ("Hips", "Head", "HeadTop_End", "LeftArm", "LeftForeArm", "LeftHand", "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase", "LeftToe_End"):
        b = next((b for b in bones if canon(b.name) == key), None)
        if b:
            print("   ", key, tuple(round(x, 3) for x in (o.matrix_world @ b.head_local)))
    if o.animation_data:
        print("  anim action", o.animation_data.action.name if o.animation_data.action else None, "nla", [ (t.name, [s.action.name for s in t.strips]) for t in o.animation_data.nla_tracks])
for a in bpy.data.actions:
    print("ACTION", a.name, tuple(round(x, 1) for x in a.frame_range), "users", a.users)
print("FPS", bpy.context.scene.render.fps)
for img in bpy.data.images:
    print("IMG", img.name, img.size[:], img.filepath)
