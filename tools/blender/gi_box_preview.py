"""gi_box_preview.py - render SM_DeliveryBox.fbx worn by SK_Player (rest pose) from back-3/4 and front, for review."""
import bpy, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__)); import gi_common as G
CH = os.path.expanduser("~/gta-india/assets/characters")
out = sys.argv[sys.argv.index("--") + 1]
sc = G.reset_scene()
bpy.ops.import_scene.fbx(filepath=CH + "/SK_Player.fbx")
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
sp = arm.data.bones["Spine2"].head_local
bpy.ops.import_scene.fbx(filepath=CH + "/SM_DeliveryBox.fbx")
box = bpy.data.objects["SM_DeliveryBox"]
back_y = max((arm.matrix_world @ v.co).y for o in bpy.data.objects if o.type == 'MESH' and o is not box for v in o.data.vertices if abs(v.co.z - sp.z) < 0.1 and abs(v.co.x) < 0.1)
box.location = Vector((0, back_y + 0.01, sp.z - 0.05))
print("box dims", tuple(round(x, 3) for x in box.dimensions), "at", tuple(box.location))
cd = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.type = 'ORTHO'; cd.ortho_scale = 2.2
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.color_type = 'TEXTURE'; sc.display.shading.light = 'STUDIO'
sc.render.resolution_x = sc.render.resolution_y = 512
for k, dv in enumerate((Vector((0.8, 1, 0.3)), Vector((-0.4, -1, 0.2)), Vector((1, 0, 0.05)))):
    d = dv.normalized(); t = Vector((0, 0.1, 1.0))
    cam.location = t + d * 8; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out}_{k}.png"; bpy.ops.render.render(write_still=True)
cd.ortho_scale = 0.8
d = Vector((0.5, 1, 0.3)).normalized(); t = box.location + Vector((0, 0.21, 0))
cam.location = t + d * 8; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = f"{out}_3.png"; bpy.ops.render.render(write_still=True)
