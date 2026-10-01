"""gi_box.py - SM_DeliveryBox.fbx: 44 (W, X) x 42 (D, Y) x 44 (H, Z) cm insulated delivery backpack box.
Pivot = centre of the face that touches the rider's back (the box's -Y face); box extends toward +Y.
In Blender the character faces -Y, so his back faces +Y: place the pivot on the upper back with NO rotation and the box
sits behind him. Straps are on the -Y face; a webbing carry handle arches over the top. Red Zomato-style
padded bag (texture from gi_box_texture.py): wordmark on the outward +Y face and both sides.
blender -b --python gi_box.py  (expects characters/T_DeliveryBox_BaseColor.png from gi_box_texture.py)
"""
import bpy, bmesh, os, sys, shutil
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
import gi_common as G

OUT = os.path.expanduser("~/gta-india/assets/characters")
TEX = os.path.join(OUT, "T_DeliveryBox_BaseColor.png")
W, D, H = 0.44, 0.42, 0.44
G.reset_scene()
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co = Vector((v.co.x * W, v.co.y * D + D / 2, v.co.z * H))
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.04, segments=4, affect='EDGES', profile=0.55)   # padded, soft edges
box_faces = list(bm.faces)
# straps: two slightly arched bands on the -Y face
strap_faces = []
for sx in (-0.11, 0.11):
    ret = bmesh.ops.create_cube(bm, size=1.0)
    vs = ret["verts"]
    for v in vs:
        v.co = Vector((sx + v.co.x * 0.05, -0.012 + v.co.y * 0.016, v.co.z * (H - 0.04)))
    fs = list({f for v in vs for f in v.link_faces})
    bmesh.ops.subdivide_edges(bm, edges=[e for e in {e for f in fs for e in f.edges} if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.1],
                              cuts=6, use_grid_fill=True)
    vs = [v for v in bm.verts if abs(v.co.x - sx) <= 0.026 and v.co.y < 0.0]
    for v in vs:
        t = v.co.z / ((H - 0.04) / 2)
        v.co.y -= 0.035 * (1 - t * t)          # arch away from the box (toward the back)
    strap_faces += list({f for v in vs for f in v.link_faces})
# carry handle: a flat webbing loop arching over the top, running front-to-back (along Y)
import math
seg = 12
for k in range(seg):
    a0, a1 = math.pi * k / seg, math.pi * (k + 1) / seg
    ret = bmesh.ops.create_cube(bm, size=1.0)
    vs = ret["verts"]
    for v in vs:
        a = a0 if v.co.y < 0 else a1
        r = 0.09 + (0.008 if v.co.z > 0 else -0.008)
        v.co = Vector((v.co.x * 0.04, D / 2 - math.cos(a) * 0.11, H / 2 + math.sin(a) * r + 0.004))
    strap_faces += list({f for v in vs for f in v.link_faces})
strap_set = set(strap_faces)
uv = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    n = f.normal
    for l in f.loops:
        p = l.vert.co
        zz = (p.z + H / 2) / H
        if f in strap_set:
            u, vv = 0.5 + 0.5 * ((p.x + 0.2) / 0.4 % 1.0), 0.5 * zz
        elif n.y > 0.5:                      # outward face
            u, vv = 0.5 * ((W / 2 - p.x) / W), 0.5 + 0.5 * zz
        elif abs(n.x) > abs(n.z) and abs(n.x) >= abs(n.y):   # sides
            u, vv = 0.5 + 0.5 * (p.y / D if n.x > 0 else 1 - p.y / D), 0.5 + 0.5 * zz
        else:                                # top/bottom/back
            u, vv = 0.5 * ((p.x + W / 2) / W), 0.5 * ((p.y / D) if abs(n.z) > 0.5 else zz)
        l[uv].uv = (min(max(u, 0.001), 0.999), min(max(vv, 0.001), 0.999))
me = bpy.data.meshes.new("SM_DeliveryBox")
bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = False
ob = bpy.data.objects.new("SM_DeliveryBox", me)
bpy.context.scene.collection.objects.link(ob)
mat = bpy.data.materials.new("M_DeliveryBox")
mat.use_nodes = True
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
img = bpy.data.images.load(TEX)
tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img
nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.75
me.materials.append(mat)
# auto smooth-ish: mark sharp by angle so the bevels shade nicely
with G.ctx([ob], ob):
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=0.6)
    except Exception as e:
        print("smooth by angle failed", e)
tris = sum(len(p.vertices) - 2 for p in me.polygons)
dims = tuple(round(x, 3) for x in ob.dimensions)
print("BOX tris", tris, "dims", dims)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "_work", "SM_DeliveryBox.blend"))
for o in bpy.data.objects:
    o.select_set(o is ob)
fbm = os.path.join(OUT, "SM_DeliveryBox.fbm")
if os.path.isdir(fbm):
    shutil.rmtree(fbm)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "SM_DeliveryBox.fbx"), use_selection=True, object_types={'MESH'},
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y',
                         mesh_smooth_type='FACE', path_mode='COPY', embed_textures=False)
G.save_json(os.path.join(OUT, "_work", "SM_DeliveryBox.json"), {"name": "SM_DeliveryBox", "file": "SM_DeliveryBox.fbx",
            "tris": tris, "dims_m": dims, "texture": "T_DeliveryBox_BaseColor.png", "material": "M_DeliveryBox"})
