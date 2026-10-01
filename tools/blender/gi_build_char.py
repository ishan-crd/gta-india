"""gi_build_char.py - convert a Sketchfab glTF character into an SK_<Name> on the canonical GI_Human skeleton.

blender -b -t 8 --python gi_build_char.py -- --src ch_man_blue --name SK_Player --height 1.75 --gender male [--template] [--recolor]
Template mode (SK_Player) writes _work/gi_template.json which every other character copies its bone orientations from.
"""
import bpy, sys, os, re, shutil, argparse, json
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import gi_common as G

ap = argparse.ArgumentParser()
ap.add_argument("--src"); ap.add_argument("--name"); ap.add_argument("--height", type=float)
ap.add_argument("--gender", default="male"); ap.add_argument("--template", action="store_true")
ap.add_argument("--recolor", action="store_true"); ap.add_argument("--maxtris", type=int, default=120000)
ap.add_argument("--targettris", type=int, default=100000)
ap.add_argument("--drop-mats", default="", help="comma list: drop source meshes whose materials are all in it (e.g. opaque glasses)")
ap.add_argument("--darken-green", default="", help="comma list of source materials whose base texture has green-dominant pixels (bad hair dye) -> near-black hair")
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])

ROOT = os.path.expanduser("~/gta-india/assets")
OUT = os.path.join(ROOT, "characters")
WORK = os.path.join(OUT, "_work")
os.makedirs(WORK, exist_ok=True)
SHORT = a.name[3:] if a.name.startswith("SK_") else a.name
TEMPLATE = os.path.join(WORK, "gi_template.json")

G.reset_scene()
arm, objs = G.import_gltf(os.path.join(ROOT, "sketchfab", a.src, "scene.gltf"))
for o in objs:
    o.animation_data_clear()
G.clear_pose(arm)
meshes = [o for o in objs if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)]
DROP = set(x for x in a.drop_mats.split(",") if x)
for o in [o for o in meshes if DROP and o.data.materials and all(m and m.name in DROP for m in o.data.materials)]:
    print("dropping mesh", o.name, [m.name for m in o.data.materials])
    meshes.remove(o); bpy.data.objects.remove(o, do_unlink=True)
print("skinned meshes", [m.name for m in meshes])
G.detach(arm)
bm = G.bone_map(arm)
P = G.world_heads(arm, bm)
arm.matrix_world = G.facing_matrix(P) @ arm.matrix_world
bpy.context.view_layer.update()
P = G.world_heads(arm, bm)
H = G.body_height(P)
print("rest height(joints)", H, "toe fwd?", P["LeftToeBase"].y < P["LeftFoot"].y, "left +x?", P["LeftArm"].x > 0)

# ---------------------------------------------------------------- T-pose
ALT = {"Hand": ["HandMiddle1", "HandIndex1", "HandRing1"]}
X = Vector((1, 0, 0)); Z = Vector((0, 0, 1))
OVR = {}
for s, sg in (("Left", 1), ("Right", -1)):
    for b in ("Arm", "ForeArm", "Hand"):
        OVR[s + b] = X * sg
    for b in ("UpLeg", "Leg"):
        OVR[s + b] = -Z
T = None
if not a.template:
    tpl = G.load_json(TEMPLATE)
    T = {c: Vector(d["head"]) for c, d in tpl["bones"].items()}


def children_of(c):
    ch = G.child_for_dir(c)
    s = "Left" if c.startswith("Left") else "Right" if c.startswith("Right") else ""
    base = c[len(s):]
    if base in ALT:
        return [s + x for x in ALT[base]]
    return [ch] if ch else []


for it in range(3):
    for c, _ in G.CANON:
        if c not in bm:
            continue
        P = G.world_heads(arm, bm)
        for ch in children_of(c):
            if ch in P and G.valid_joint(P, ch, H):
                if a.template:
                    d = OVR.get(c)
                else:
                    if ch not in T or c not in T:
                        continue
                    d = (T[ch] - T[c]).normalized()
                    if c in OVR and ch == children_of(c)[0]:
                        d = OVR[c]
                if d is not None:
                    G.align_bone(arm, bm[c], d, P[ch])
                break
P = G.world_heads(arm, bm)

# ---------------------------------------------------------------- bake meshes in T-pose, world space, join
for o in meshes:
    if o.data.shape_keys:
        o.shape_key_clear()
    if o.data.users > 1:
        o.data = o.data.copy()
    for m in list(o.modifiers):
        if m.type == 'ARMATURE':
            with G.ctx([o], o):
                bpy.ops.object.modifier_apply(modifier=m.name)
    mw = o.matrix_world.copy()
    o.parent = None
    o.data.transform(mw)
    o.matrix_world = Matrix.Identity(4)
    if mw.determinant() < 0:
        o.data.flip_normals()
body = meshes[0]
if len(meshes) > 1:
    with G.ctx(meshes, body):
        bpy.ops.object.join()
body.name = a.name + "_Mesh"
body.data.name = a.name + "_Mesh"

# ---------------------------------------------------------------- vertex groups -> canonical
DEFORM = set(G.CANON_NAMES) - {"root"}
MERGE = {"HeadTop_End": "Head", "LeftToe_End": "LeftToeBase", "RightToe_End": "RightToeBase"}
src2can = {}
for b in arm.data.bones:
    x = b
    while x is not None and G.canon(x.name) not in DEFORM:
        x = x.parent
    t = G.canon(x.name) if x else "Hips"
    src2can[b.name] = MERGE.get(t, t)
me = body.data
idx2can = {vg.index: src2can.get(vg.name) for vg in body.vertex_groups}
unmapped = [vg.name for vg in body.vertex_groups if src2can.get(vg.name) is None]
print("unmapped groups (dropped):", unmapped)
weights = []
for vtx in me.vertices:
    acc = {}
    for g in vtx.groups:
        t = idx2can.get(g.group)
        if t and g.weight > 0:
            acc[t] = acc.get(t, 0.0) + g.weight
    if acc:
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
        s = sum(w for _, w in top)
        acc = {k: w / s for k, w in top}
    weights.append(acc)
body.vertex_groups.clear()
vgs = {c: body.vertex_groups.new(name=c) for c in G.CANON_NAMES if c != "root"}
nz = 0
for i, acc in enumerate(weights):
    if not acc:
        nz += 1
        acc = {"Hips": 1.0}
    for c, w in acc.items():
        vgs[c].add([i], w, 'REPLACE')
print("verts without weights ->Hips:", nz)

# ---------------------------------------------------------------- decimate
tris = sum(len(p.vertices) - 2 for p in me.polygons)
if tris > a.maxtris:
    mod = body.modifiers.new("dec", 'DECIMATE')
    mod.ratio = a.targettris / tris
    mod.use_collapse_triangulate = True
    with G.ctx([body], body):
        bpy.ops.object.modifier_apply(modifier="dec")
    print("decimated", tris, "->", sum(len(p.vertices) - 2 for p in me.polygons))
tris = sum(len(p.vertices) - 2 for p in me.polygons)

# ---------------------------------------------------------------- joints
co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
minz, maxz = co[:, 2].min(), co[:, 2].max()
J = {c: P[c].copy() for c in G.CANON_NAMES if c in P and c not in ("HeadTop_End", "LeftToe_End", "RightToe_End")}
J["HeadTop_End"] = Vector((J["Head"].x, J["Head"].y, maxz))
if a.template:
    rot = {}
else:
    rot = {c: Matrix(d["rot"]) for c, d in tpl["bones"].items()}
# missing fingers: template offsets scaled by arm length
for s in ("Left", "Right"):
    for f in G.FINGERS:
        for k in (1, 2, 3):
            c = f"{s}Hand{f}{k}"
            if c not in J:
                if a.template:
                    raise SystemExit("template lacks " + c)
                r = (J[s + "Hand"] - J[s + "Arm"]).length / (T[s + "Hand"] - T[s + "Arm"]).length
                J[c] = J[s + "Hand"] + (T[c] - T[s + "Hand"]) * r
                print("synth", c)


def vg_verts(name, thr=0.5):
    gi = body.vertex_groups[name].index
    out = []
    for vtx in me.vertices:
        for g in vtx.groups:
            if g.group == gi and g.weight > thr:
                out.append(vtx.co.copy()); break
    return out


def dir_of(c):
    if not a.template:
        return rot[c].col[1].copy()
    ch = {"Head": None, "HeadTop_End": None}.get(c, G.child_for_dir(c))
    if c in ("Head", "HeadTop_End"):
        return Vector((0, 0, 1))
    if c.endswith("ToeBase") or c.endswith("Toe_End"):
        s = "Left" if c.startswith("Left") else "Right"
        d = J[s + "ToeBase"] - J[s + "Foot"]; d.z = 0
        return d.normalized()
    if c.endswith("3") and "Hand" in c:
        return (J[c] - J[c[:-1] + "2"]).normalized()
    if c.endswith("Hand"):
        return (J[c + "Middle1"] - J[c]).normalized() if c not in OVR else OVR[c]
    if c == "root":
        return Vector((0, 0, 1))
    return (J[ch] - J[c]).normalized()


for s in ("Left", "Right"):
    d = dir_of(s + "ToeBase")
    vs = vg_verts(s + "ToeBase", 0.3)
    L = max([(p - J[s + "ToeBase"]).dot(d) for p in vs] + [0.03 * H])
    J[s + "Toe_End"] = J[s + "ToeBase"] + d * L

# ---------------------------------------------------------------- normalise scale / position
k = a.height / (maxz - minz)
off = Vector((J["Hips"].x, J["Hips"].y, minz))
me.transform(Matrix.Scale(k, 4) @ Matrix.Translation(-off))
for c in J:
    J[c] = (J[c] - off) * k
J["root"] = Vector((0, 0, 0))
print("height", a.height, "scale", k, "hips z", J["Hips"].z)

if a.template:
    for c in G.CANON_NAMES:
        rot[c] = G.bone_orient(c, dir_of(c))

# ---------------------------------------------------------------- build canonical armature
bpy.data.objects.remove(arm, do_unlink=True)
for o in list(bpy.data.objects):
    if o is not body:
        bpy.data.objects.remove(o, do_unlink=True)
ad = bpy.data.armatures.new("GI_Human")
ao = bpy.data.objects.new("Armature", ad)
bpy.context.scene.collection.objects.link(ao)
bpy.context.view_layer.objects.active = ao
bpy.ops.object.mode_set(mode='EDIT')
for c, par in G.CANON:
    eb = ad.edit_bones.new(c)
    R = rot[c]
    ch = G.child_for_dir(c)
    L = (J[ch] - J[c]).length if ch in J else 0.0
    if L < 0.02:
        L = 0.03 if "Hand" in c and c[-1].isdigit() else 0.08
    if c == "root":
        L = 0.15
    eb.head = J[c]
    eb.tail = J[c] + R.col[1] * L
    eb.align_roll(R.col[2])
    if par:
        eb.parent = ad.edit_bones[par]
    eb.use_connect = False
    eb.use_deform = c != "root"
bpy.ops.object.mode_set(mode='OBJECT')
body.parent = ao
mod = body.modifiers.new("Armature", 'ARMATURE'); mod.object = ao
for p in me.polygons:
    p.use_smooth = True

# check orientations equal template
if not a.template:
    err = max(ao.data.bones[c].matrix_local.to_quaternion().rotation_difference(rot[c].to_quaternion()).angle
              for c in G.CANON_NAMES)
    print("max orientation deviation from template (deg)", err * 57.3)

# ---------------------------------------------------------------- materials / textures
TEXDIR = os.path.join(OUT, "textures", SHORT)
if os.path.isdir(TEXDIR):
    shutil.rmtree(TEXDIR)
os.makedirs(TEXDIR)
texinfo = {}


def upstream_image(sock, depth=0):
    if not sock.is_linked or depth > 6:
        return None
    n = sock.links[0].from_node
    if n.type == 'TEX_IMAGE':
        return n
    for i in n.inputs:
        r = upstream_image(i, depth + 1)
        if r:
            return r
    return None


def darken_green(img, dst):
    """green-dominant pixels -> dark brown-black hair keeping the strand shading."""
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(-1, 4)
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    mask = np.clip((g - np.maximum(r, b)) / 0.04, 0, 1)
    lum = (0.3 * r + 0.59 * g + 0.11 * b)
    lum = lum / max(float(lum[mask > 0.5].max()) if (mask > 0.5).any() else 1.0, 1e-3)
    hair = np.stack([0.035 + 0.06 * lum, 0.028 + 0.045 * lum, 0.024 + 0.035 * lum], 1)
    px[:, :3] = px[:, :3] * (1 - mask[:, None]) + hair * mask[:, None]
    out = bpy.data.images.new(os.path.basename(dst), w, h, alpha=True)
    out.pixels.foreach_set(px.ravel())
    out.filepath_raw = dst; out.file_format = 'PNG'; out.save()
    print("darken_green", os.path.basename(dst), "frac", float((mask > 0.5).mean()))
    return out


def recolor_yellow(img, dst):
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(-1, 4)
    rgb = px[:, :3]
    mx = rgb.max(1); mn = rgb.min(1); dlt = mx - mn + 1e-8
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    hue = np.where(mx == r, ((g - b) / dlt) % 6, np.where(mx == g, (b - r) / dlt + 2, (r - g) / dlt + 4)) * 60.0
    sat = np.where(mx > 0, dlt / (mx + 1e-8), 0)
    dh = np.abs(((hue - 222.0) + 180) % 360 - 180)
    mask = np.clip((55.0 - dh) / 20.0, 0, 1) * np.clip((sat - 0.12) / 0.12, 0, 1)
    # yellow: hue 48, keep shading from value (blue has low luminance -> lift it)
    val = np.clip(mx, 0, 1)
    V = np.clip(0.30 + 0.80 * val ** 0.8, 0, 0.97)
    S = np.clip(0.88 + 0.12 * sat, 0, 1)
    hh = 48.0 / 60.0
    c = V * S; x = c * (1 - abs(hh % 2 - 1)); m = V - c
    yr, yg, yb = c + m, x + m, m  # hue in [0,1) sector: (C, X, 0)
    new = np.stack([yr, yg, yb], 1)
    px[:, :3] = rgb * (1 - mask[:, None]) + new * mask[:, None]
    out = bpy.data.images.new(os.path.basename(dst), w, h, alpha=True)
    out.pixels.foreach_set(px.ravel())
    out.filepath_raw = dst; out.file_format = 'PNG'; out.save()
    print("recolored pixels frac", float((mask > 0.5).mean()))
    return out


for slot in body.material_slots:
    mat = slot.material
    if mat is None:
        continue
    orig = mat.name
    # ReadyPlayerMe: Wolf3D_Outfit_Top.001 -> outfit_top (UE tints slots named *outfit*, never *shoes*)
    orig = re.sub(r"\.\d{3}$", "", orig)
    orig = {"Wolf3D_Outfit_Top": "outfit_top", "Wolf3D_Outfit_Bottom": "outfit_bottom",
            "Wolf3D_Outfit_Footwear": "outfit_shoes"}.get(orig, orig)
    mat.name = f"M_{SHORT}_{orig}".replace(".", "_")
    info = {}
    if mat.use_nodes:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        roles = {}
        if bsdf:
            for role, sock in (("base", "Base Color"), ("normal", "Normal"), ("roughness", "Roughness"),
                               ("metallic", "Metallic"), ("emissive", "Emission Color"), ("alpha", "Alpha")):
                if sock in bsdf.inputs:
                    n = upstream_image(bsdf.inputs[sock])
                    if n and n.image:
                        roles[role] = n
        done = {}
        for role, n in roles.items():
            img = n.image
            if img.name in done:
                info[role] = done[img.name]; continue
            src = bpy.path.abspath(img.filepath)
            ext = os.path.splitext(src)[1].lower() or ".png"
            if ext == ".jpeg":
                ext = ".jpg"
            rname = {"base": "BaseColor", "normal": "Normal", "roughness": "MetalRough", "metallic": "MetalRough",
                     "emissive": "Emissive", "alpha": "BaseColor"}[role]
            dst = os.path.join(TEXDIR, f"T_{SHORT}_{orig}_{rname}{ext}".replace(" ", "_"))
            if role == "base" and orig in a.darken_green.split(","):
                dst = os.path.join(TEXDIR, f"T_{SHORT}_{orig}_BaseColor.png".replace(" ", "_"))
                newimg = darken_green(img, dst)
                newimg.colorspace_settings.name = 'sRGB'
                n.image = newimg
                img = newimg
            elif role == "base" and a.recolor:
                dst = os.path.join(TEXDIR, f"T_{SHORT}_{orig}_BaseColor_Yellow.png")
                newimg = recolor_yellow(img, dst)
                newimg.colorspace_settings.name = 'sRGB'
                n.image = newimg
                img = newimg
            else:
                if os.path.exists(src):
                    shutil.copy(src, dst)
                elif img.packed_file:
                    img.filepath_raw = dst; img.save()
                img.filepath = dst
            img.name = os.path.basename(dst)
            done[img.name] = os.path.relpath(dst, OUT)
            info[role] = os.path.relpath(dst, OUT)
    texinfo[mat.name] = {"base": info.get("base"), "normal": info.get("normal"),
                         "roughness": info.get("roughness"),
                         "roughness_channel": "G (glTF metallicRoughness: G=roughness, B=metallic)" if info.get("roughness") else None}
    if "alpha" in info:
        texinfo[mat.name]["alpha_from_base"] = True
    texinfo[mat.name]["blend"] = mat.blend_method if hasattr(mat, "blend_method") else None
G.save_json(os.path.join(TEXDIR, "textures.json"), texinfo)

# ---------------------------------------------------------------- template / info / save / export
if a.template:
    G.save_json(TEMPLATE, {"source": a.src, "bones": {c: {"head": list(J[c]), "rot": [list(r) for r in rot[c]],
                                                          "parent": G.PARENT[c]} for c in G.CANON_NAMES}})
info = {"name": a.name, "file": a.name + ".fbx", "height_m": a.height, "gender": a.gender, "tris": tris,
        "source": a.src, "hips_z": J["Hips"].z, "textures": texinfo}
G.save_json(os.path.join(WORK, a.name + ".json"), info)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, a.name + ".blend"))

for o in bpy.context.view_layer.objects:
    o.select_set(o in (ao, body))
bpy.context.view_layer.objects.active = ao
fbx = os.path.join(OUT, a.name + ".fbx")
fbm = os.path.join(OUT, a.name + ".fbm")
if os.path.isdir(fbm):
    shutil.rmtree(fbm)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'ARMATURE', 'MESH'},
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', global_scale=1.0,
                         axis_forward='-Z', axis_up='Y', bake_space_transform=False,
                         add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                         use_armature_deform_only=False, armature_nodetype='NULL',
                         bake_anim=False, mesh_smooth_type='FACE', use_mesh_modifiers=False, use_tspace=False,
                         path_mode='COPY', embed_textures=False)
print("EXPORTED", fbx, "tris", tris)
