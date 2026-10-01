"""gi_common.py - shared helpers for the GI_Human character / animation pipeline (Blender 5.x).

Canonical skeleton "GI_Human" (Mixamo names, no prefix).  Convention in Blender:
  T-pose, character faces -Y, left side is +X, up +Z, feet on Z=0, `root` bone at origin.
"""
import bpy, re, json, os, math
from mathutils import Vector, Matrix, Quaternion

FINGERS = ["Thumb", "Index", "Middle", "Ring", "Pinky"]


def _canon_bones():
    b = [("root", None), ("Hips", "root"), ("Spine", "Hips"), ("Spine1", "Spine"), ("Spine2", "Spine1"),
         ("Neck", "Spine2"), ("Head", "Neck"), ("HeadTop_End", "Head")]
    for s in ("Left", "Right"):
        b += [(s + "Shoulder", "Spine2"), (s + "Arm", s + "Shoulder"), (s + "ForeArm", s + "Arm"), (s + "Hand", s + "ForeArm")]
        for f in FINGERS:
            b += [(f"{s}Hand{f}1", s + "Hand"), (f"{s}Hand{f}2", f"{s}Hand{f}1"), (f"{s}Hand{f}3", f"{s}Hand{f}2")]
    for s in ("Left", "Right"):
        b += [(s + "UpLeg", "Hips"), (s + "Leg", s + "UpLeg"), (s + "Foot", s + "Leg"), (s + "ToeBase", s + "Foot"),
              (s + "Toe_End", s + "ToeBase")]
    return b


CANON = _canon_bones()                      # ordered parent-first
CANON_NAMES = [n for n, _ in CANON]
PARENT = dict(CANON)


def child_for_dir(n):
    """canonical (or source-only) joint whose head the bone should point at."""
    s = "Left" if n.startswith("Left") else "Right" if n.startswith("Right") else ""
    m = {"Hips": "Spine", "Spine": "Spine1", "Spine1": "Spine2", "Spine2": "Neck", "Neck": "Head", "Head": "HeadTop_End"}
    if n in m:
        return m[n]
    base = n[len(s):]
    m2 = {"Shoulder": "Arm", "Arm": "ForeArm", "ForeArm": "Hand", "Hand": "HandMiddle1", "UpLeg": "Leg", "Leg": "Foot",
          "Foot": "ToeBase", "ToeBase": "Toe_End"}
    if base in m2:
        return s + m2[base]
    mt = re.match(r"Hand(\w+?)(\d)$", base)
    if mt:
        return f"{s}Hand{mt.group(1)}{int(mt.group(2)) + 1}"   # finger 3 -> finger 4 (source only)
    return None


def z_ref(n):
    """world-space reference for each bone's local Z axis (roll rule, T-pose, facing -Y)."""
    if "Thumb" in n or n.endswith("Foot") or n.endswith("ToeBase") or n.endswith("Toe_End"):
        return Vector((0, 0, 1))
    return Vector((0, -1, 0))


def canon(name):
    n = name.split(":")[-1]
    return re.sub(r"(_\d+)+$", "", n)   # also RPM re-exports: Hips_66_12


def reset_scene(fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = fps
    sc.render.fps_base = 1.0
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    return sc


def import_gltf(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in list(new):
        if o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o, do_unlink=True)
    new = [o for o in bpy.data.objects if o not in before]
    arms = [o for o in new if o.type == 'ARMATURE']
    arm = max(arms, key=lambda a: len(a.data.bones))
    return arm, new


def bone_map(arm):
    """canonical name -> pose bone (first match)."""
    d = {}
    for pb in arm.pose.bones:
        c = canon(pb.name)
        if c not in d:
            d[c] = pb
    return d


def detach(obj):
    mw = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = mw


def world_heads(arm, bm):
    mw = arm.matrix_world
    return {c: mw @ pb.head for c, pb in bm.items()}


def valid_joint(P, c, H):
    """end joints from Sketchfab glTFs are often garbage (origin / under feet)."""
    if c not in P:
        return False
    par = {"HeadTop_End": "Head", "LeftToe_End": "LeftToeBase", "RightToe_End": "RightToeBase"}.get(c)
    if par is None:
        mt = re.match(r"(Left|Right)Hand(\w+?)4$", c)
        if mt:
            par = f"{mt.group(1)}Hand{mt.group(2)}3"
    if par is None or par not in P:
        return True
    d = (P[c] - P[par]).length
    return 0.005 * H < d < 0.25 * H


def facing_matrix(P):
    """rotation mapping the rig's rest frame to canonical (left=+X, up=+Z, face -Y)."""
    up = (P.get("Neck", P.get("Head")) - P["Hips"]).normalized()
    lr = (P["LeftUpLeg"] - P["RightUpLeg"])
    if "LeftArm" in P and "RightArm" in P:
        lr = lr.normalized() + (P["LeftArm"] - P["RightArm"]).normalized()
    X = (lr - up * lr.dot(up)).normalized()
    Z = up
    Y = Z.cross(X).normalized()
    B = Matrix((X, Y, Z)).transposed()   # columns = rig axes in world
    return B.transposed().to_4x4()       # inverse rotation


def body_height(P):
    feet = [P[k].z for k in ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase") if k in P]
    return P["Head"].z - min(feet)


def rot_about(head, q):
    return Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head)


def align_bone(arm, pb, target_dir, child_head):
    mw = arm.matrix_world
    head = mw @ pb.head
    cur = child_head - head
    if cur.length < 1e-9:
        return
    q = cur.normalized().rotation_difference(target_dir.normalized())
    W = mw @ pb.matrix
    pb.matrix = mw.inverted() @ (rot_about(head, q) @ W)
    bpy.context.view_layer.update()


def tpose_align(arm, bm, dirs, skip=()):
    """rotate source bones (pose mode) so each canonical bone points along dirs[c] (world)."""
    H = None
    for it in range(2):
        for c, _ in CANON:
            if c in skip or c not in bm or c not in dirs:
                continue
            ch = child_for_dir(c)
            P = world_heads(arm, bm)
            if H is None:
                H = body_height(P)
            if ch is None or ch not in P or not valid_joint(P, ch, H):
                continue
            align_bone(arm, bm[c], dirs[c], P[ch])


def clear_pose(arm):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def bone_orient(c, d):
    """3x3 world orientation: Y=d, Z=z_ref orthogonalised."""
    y = d.normalized()
    z = z_ref(c)
    z = (z - y * z.dot(y))
    if z.length < 1e-4:
        z = Vector((0, 0, 1)) - y * y.z
    z.normalize()
    x = y.cross(z).normalized()
    return Matrix((x, y, z)).transposed()


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def v(t):
    return Vector(t)


def ctx(objs, active):
    return bpy.context.temp_override(selected_objects=objs, selected_editable_objects=objs, active_object=active, object=active)
