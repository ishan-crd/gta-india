# render a raw glTF import (rest pose, no anim) front view for debugging: blender -b --python char_rawview.py -- src out.png [bindpose0]
import bpy, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
import gi_common as G
src, out = sys.argv[sys.argv.index("--") + 1:][:2]
guess = len(sys.argv[sys.argv.index("--") + 1:]) < 3
G.reset_scene()
bpy.ops.import_scene.gltf(filepath=os.path.expanduser(f"~/gta-india/assets/sketchfab/{src}/scene.gltf"), guess_original_bind_pose=guess)
for o in bpy.data.objects:
    if o.name.startswith("Icosphere"): bpy.data.objects.remove(o)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
for o in bpy.data.objects: o.animation_data_clear()
G.clear_pose(arm)
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for o in bpy.data.objects:
    if o.type == 'MESH':
        e = o.evaluated_get(dg)
        for vv in e.data.vertices: pts.append(e.matrix_world @ vv.co)
mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
print("mesh bbox", tuple(mn), tuple(mx))
bm = G.bone_map(arm); P = G.world_heads(arm, bm)
for k in ("Hips", "Head", "LeftArm", "LeftHand", "LeftFoot"): print(k, tuple(round(x, 3) for x in P[k]))
sc = bpy.context.scene
cd = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.type = 'ORTHO'; c = (mn + mx) / 2; cd.ortho_scale = max(mx - mn) * 1.2
# look along the axis with smallest extent
ext = mx - mn; ax = min(range(3), key=lambda i: ext[i]); d = Vector((0, 0, 0)); d[ax] = -1
cam.location = c - d * 20; cam.rotation_euler = d.to_track_quat('-Z', 'Z' if ax != 2 else 'Y').to_euler()
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = sc.render.resolution_y = 512
arm.show_in_front = True
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
