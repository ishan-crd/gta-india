"""gi_contact.py - verification renders: re-import exported SK_*.fbx and A_*.fbx, apply each anim to each character.

blender -b --python gi_contact.py -- --chars SK_Player,SK_ManRed --anims rest,A_Walk,A_Run --out DIR [--frac 0.5] [--view front|side|34]
Writes DIR/<char>__<anim>.png (512px). Compose with gi_sheet.py.
"""
import bpy, sys, os, argparse, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
import gi_common as G

ap = argparse.ArgumentParser()
ap.add_argument("--chars"); ap.add_argument("--anims", default="rest"); ap.add_argument("--out")
ap.add_argument("--frac", type=float, default=0.5); ap.add_argument("--view", default="34")
ap.add_argument("--size", type=int, default=512); ap.add_argument("--fracs", default="")
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
CH = os.path.expanduser("~/gta-india/assets/characters")
os.makedirs(a.out, exist_ok=True)

G.reset_scene(30)
sc = bpy.context.scene


def imp(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, use_anim=True, automatic_bone_orientation=False, ignore_leaf_bones=False)
    return [o for o in bpy.data.objects if o not in before]


chars = {}
for c in a.chars.split(","):
    objs = imp(os.path.join(CH, c + ".fbx"))
    arm = next(o for o in objs if o.type == 'ARMATURE')
    # Blender's FBX importer connects single-child bones (root->Hips), which would ignore Hips translation keys.
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for eb in arm.data.edit_bones:
        eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    chars[c] = objs
    print("CHAR", c, "arm scale", tuple(round(x, 3) for x in arm.matrix_world.to_scale()),
          "dims", [tuple(round(x, 3) for x in o.dimensions) for o in objs if o.type == 'MESH'])
acts = {}
for an in a.anims.split(","):
    if an == "rest":
        continue
    before = set(bpy.data.actions)
    objs = imp(os.path.join(CH, an + ".fbx"))
    new = [x for x in bpy.data.actions if x not in before]
    acts[an] = new[0]
    print("ANIM", an, new[0].name, tuple(new[0].frame_range))
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)

# ground + light + camera
bpy.ops.mesh.primitive_plane_add(size=6)
ground = bpy.context.active_object
gm = bpy.data.materials.new("ground"); gm.diffuse_color = (0.35, 0.35, 0.35, 1); ground.data.materials.append(gm)
cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam)
sc.camera = cam
cam_d.type = 'ORTHO'; cam_d.ortho_scale = 2.4
tgt = Vector((0, 0, 0.9))
dirs = {"front": Vector((0, -1, 0.12)), "side": Vector((1, 0, 0.12)), "34": Vector((0.7, -1, 0.3)), "back": Vector((0, 1, 0.12)),
        "top": Vector((0.3, -0.4, 1))}
d = dirs[a.view].normalized()
cam.location = tgt + d * 8
cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_shadows = True; sh.show_cavity = False
sc.render.resolution_x = sc.render.resolution_y = a.size
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.15, 0.17, 0.2)
sh.background_type = 'WORLD'

for c, objs in chars.items():
    for o in bpy.data.objects:
        if o.type in ('MESH', 'ARMATURE') and o is not ground:
            o.hide_render = o not in objs
    arm = next(o for o in objs if o.type == 'ARMATURE')
    for an in a.anims.split(","):
        if an == "rest":
            if arm.animation_data:
                arm.animation_data.action = None
            G.clear_pose(arm)
            sc.frame_set(0)
            fr = 0
        else:
            act = acts[an]
            arm.animation_data_create()
            arm.animation_data.action = act
            if hasattr(arm.animation_data, "action_slot") and act.slots:
                arm.animation_data.action_slot = act.slots[0]
            f0, f1 = act.frame_range
            fr = int(round(f0 + (f1 - f0) * a.frac))
            sc.frame_set(fr)
            for k, fx in enumerate([float(x) for x in a.fracs.split(",") if x]):
                sc.frame_set(int(round(f0 + (f1 - f0) * fx)))
                sc.render.filepath = os.path.join(a.out, f"{c}__{an}@{k}.png")
                bpy.ops.render.render(write_still=True)
            sc.frame_set(fr)
        # ground check: lowest vertex
        mesh = next(o for o in objs if o.type == 'MESH')
        dg = bpy.context.evaluated_depsgraph_get()
        ev = mesh.evaluated_get(dg)
        mw = ev.matrix_world
        import numpy as np
        co = np.empty(len(ev.data.vertices) * 3); ev.data.vertices.foreach_get('co', co)
        zs = (co.reshape(-1, 3) @ np.array(mw.to_3x3()).T)[:, 2] + mw.translation.z
        print("POSE", c, an, "frame", fr, "minz %.3f maxz %.3f" % (min(zs), max(zs)))
        sc.render.filepath = os.path.join(a.out, f"{c}__{an}.png")
        bpy.ops.render.render(write_still=True)
print("done")
