"""Render a contact sheet of converted props (FBX) with a 1.8 m human-size reference box."""
import bpy, json, math, os
from mathutils import Vector
OUT = os.path.expanduser("~/gta-india/assets/props")
m = json.load(open(f"{OUT}/props_manifest.json"))
names = [k for k in m if not k.startswith("PH_")]
os.makedirs(f"{OUT}/previews", exist_ok=True)
for name in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=m[name]["file"])
    objs = [o for o in bpy.data.objects if o.type == "MESH"]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -max(1.5, m[name]["bounds_m"][1]), 0.9))
    ref = bpy.context.active_object; ref.scale = (0.4, 0.3, 1.8)
    b = m[name]["bounds_m"]; r = max(b) * 1.3 + 2
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
    cam.location = (r * 0.8, -r * 1.1, r * 0.55); 
    d = Vector((0, 0, b[2] * 0.4)) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); bpy.context.scene.collection.objects.link(sun); sun.rotation_euler = (0.8, 0.2, 0.6)
    sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.color_type = "TEXTURE"
    sc.render.resolution_x = 360; sc.render.resolution_y = 270; sc.render.filepath = f"{OUT}/previews/{name}.png"
    bpy.ops.render.render(write_still=True)
