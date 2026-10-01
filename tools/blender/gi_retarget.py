"""gi_retarget.py - retarget a Sketchfab/Mixamo glTF animation onto the GI_Human skeleton of SK_Player and export A_<Clip>.fbx.

blender -b -t 8 --python gi_retarget.py -- --src an_walk --clip A_Walk [--action walk] [--start 0 --end 30]
       [--loop] [--xy inplace|keep|zero] [--z ground|pin|keep|first] [--analyze]
World-space rotation transfer: tgt_world = src_anim_world * inv(src_T_world) * tgt_T_world, where both rigs are first
normalised to the canonical T-pose (facing -Y, left +X, arms along +-X, legs down) using the SK_Player template.
"""
import bpy, sys, os, argparse, math, json
from mathutils import Vector, Matrix, Quaternion
sys.path.insert(0, os.path.dirname(__file__))
import gi_common as G

ap = argparse.ArgumentParser()
ap.add_argument("--src"); ap.add_argument("--clip"); ap.add_argument("--action", default="")
ap.add_argument("--start", type=int, default=None); ap.add_argument("--end", type=int, default=None)
ap.add_argument("--loop", action="store_true"); ap.add_argument("--xy", default="keep"); ap.add_argument("--z", default="ground")
ap.add_argument("--analyze", action="store_true"); ap.add_argument("--note", default="")
ap.add_argument("--noblend", action="store_true"); ap.add_argument("--reorient", action="store_true"); ap.add_argument("--upright", type=float, default=None)
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])

ROOT = os.path.expanduser("~/gta-india/assets")
OUT = os.path.join(ROOT, "characters"); WORK = os.path.join(OUT, "_work")
tpl = G.load_json(os.path.join(WORK, "gi_template.json"))
T = {c: Vector(d["head"]) for c, d in tpl["bones"].items()}

sc = G.reset_scene(30)
arm, objs = G.import_gltf(os.path.join(ROOT, "sketchfab", a.src, "scene.gltf"))
for o in objs:
    if o is not arm and o.animation_data and (o.animation_data.action or len(o.animation_data.nla_tracks)):
        print("WARN other animated object", o.name)
ad = arm.animation_data
acts = [t.strips[0].action for t in ad.nla_tracks if t.strips] + ([ad.action] if ad.action else [])
act = next((x for x in acts if a.action and a.action.lower() in x.name.lower()), None) or ad.action or acts[0]
print("ACTIONS", [x.name for x in acts], "-> using", act.name)
while ad.nla_tracks:
    ad.nla_tracks.remove(ad.nla_tracks[0])
# keep (frame-0) animation of non-canonical ancestors (e.g. _rootJoint carrying a Y-up -> Z-up rotation)
ad.action = act
if hasattr(ad, "action_slot") and act.slots and ad.action_slot is None:
    ad.action_slot = act.slots[0]
sc.frame_set(int(act.frame_range[0]))
keep = {}
b = G.bone_map(arm)["Hips"].parent
while b is not None:
    keep[b.name] = b.matrix_basis.copy(); b = b.parent
print("ancestor bases kept:", {k: [round(x, 3) for x in m.to_quaternion()] for k, m in keep.items()})
ad.action = None
G.clear_pose(arm)
for k, m in keep.items():
    arm.pose.bones[k].matrix_basis = m
bpy.context.view_layer.update()
G.detach(arm)
bm = G.bone_map(arm)
P = G.world_heads(arm, bm)
arm.matrix_world = G.facing_matrix(P) @ arm.matrix_world
bpy.context.view_layer.update()
P = G.world_heads(arm, bm)
H = G.body_height(P)

ALT = {"Hand": ["HandMiddle1", "HandIndex1", "HandRing1"]}


def children_of(c):
    ch = G.child_for_dir(c)
    s = "Left" if c.startswith("Left") else "Right" if c.startswith("Right") else ""
    base = c[len(s):]
    if base in ALT:
        return [s + x for x in ALT[base]]
    return [ch] if ch else []


# normalise only the limb chains to the T-pose; spine/neck/head/shoulders/feet/fingers keep their own rest so the
# transfer is relative for them (different spine curvature between rigs must not bend the target).
LIMBS = {s + b for s in ("Left", "Right") for b in ("Arm", "ForeArm", "Hand", "UpLeg", "Leg")}
for it in range(3):
    for c, _ in G.CANON:
        if c not in bm or c not in T or c not in LIMBS:
            continue
        P = G.world_heads(arm, bm)
        for ch in children_of(c):
            if ch in P and G.valid_joint(P, ch, H):
                if ch in T:
                    G.align_bone(arm, bm[c], (T[ch] - T[c]).normalized(), P[ch])
                break
mw = arm.matrix_world
present = [c for c in G.CANON_NAMES if c in bm and c != "root"]
Tsrc = {c: (mw @ bm[c].matrix).to_quaternion() for c in present}
P = G.world_heads(arm, bm)
Ts_hips = P["Hips"].copy()
Ts_foot = (P["LeftFoot"].z + P["RightFoot"].z) / 2
G.clear_pose(arm)
for k, m in keep.items():
    arm.pose.bones[k].matrix_basis = m
ad.action = act
if hasattr(ad, "action_slot") and act.slots and ad.action_slot is None:
    ad.action_slot = act.slots[0]
f0, f1 = act.frame_range
f0, f1 = int(math.floor(f0 + 1e-3)), int(math.ceil(f1 - 1e-3))
REO = Matrix.Identity(4)
if a.reorient:   # animation plays in a frame rotated by k*90deg vs the rest pose (Y-up rigs): snap & undo
    sc.frame_set(f0)
    Fa = G.facing_matrix(G.world_heads(arm, bm)).to_3x3()
    Sn = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
    for r in range(3):
        cidx = max(range(3), key=lambda k: abs(Fa[r][k]))
        Sn[r][cidx] = 1 if Fa[r][cidx] > 0 else -1
    REO = Sn.to_4x4()
    print("REORIENT", [list(map(round, r)) for r in Sn])
print("SRC RANGE", f0, f1, "missing canon bones:", [c for c in G.CANON_NAMES if c not in bm and c != "root"])

# ---------------------------------------------------------------- target skeleton (SK_Player)
with bpy.data.libraries.load(os.path.join(WORK, "SK_Player.blend")) as (src, dst):
    dst.objects = ["Armature"]
tgt = dst.objects[0]
sc.collection.objects.link(tgt)
tgt.name = "Armature"
tgt.matrix_world = Matrix.Identity(4)
bones = tgt.data.bones
Rest = {c: bones[c].matrix_local.copy() for c in G.CANON_NAMES}
Tt = {c: Rest[c].to_quaternion() for c in G.CANON_NAMES}
Tt_hips = Rest["Hips"].translation.copy()
Tt_foot = (Rest["LeftFoot"].translation.z + Rest["RightFoot"].translation.z) / 2
ratio = (Tt_hips.z - Tt_foot) / (Ts_hips.z - Ts_foot)
print("hip ratio", ratio)

# fallback sources for missing fingers
FALLBACK = {}
for s in ("Left", "Right"):
    for f in ("Middle", "Ring", "Pinky"):
        for k in (1, 2, 3):
            if f"{s}Hand{f}{k}" not in bm and f"{s}HandIndex{k}" in bm:
                FALLBACK[f"{s}Hand{f}{k}"] = f"{s}HandIndex{k}"

# ---------------------------------------------------------------- sample
frames = list(range(f0, f1 + 1))
basis = {c: [] for c in G.CANON_NAMES}
hips_pos = []
for f in frames:
    sc.frame_set(f)
    mw = arm.matrix_world
    RQ = REO.to_quaternion()
    Rt = {"root": Tt["root"]}
    for c, par in G.CANON:
        if c == "root":
            continue
        srcb = c if c in Tsrc else FALLBACK.get(c)
        if srcb:
            A = RQ @ (mw @ bm[srcb].matrix).to_quaternion()
            delta = A @ Tsrc[srcb].inverted()
            Rt[c] = (delta @ Tt[c]).normalized()
        else:
            Rt[c] = Rt[par] @ Tt[par].inverted() @ Tt[c]
    for c, par in G.CANON:
        if par is None:
            q = Quaternion()
        else:
            rel = Tt[par].inverted() @ Tt[c]
            q = (rel.inverted() @ Rt[par].inverted() @ Rt[c]).normalized()
        basis[c].append(q)
    Ps = REO @ (mw @ bm["Hips"].matrix).translation
    hips_pos.append(Tt_hips + (Ps - Ts_hips) * ratio)
N = len(frames)
# debug: compare source bone directions with target FK directions at mid frame
_i = 0
sc.frame_set(frames[_i])
_W = None
def _dbg():
    W = fk(_i, hips_pos[_i])
    mw = arm.matrix_world
    for c, ch in (("LeftArm", "LeftForeArm"), ("LeftUpLeg", "LeftLeg"), ("Hips", "Spine"), ("Spine", "Spine1"), ("Spine1", "Spine2"), ("Spine2", "Neck"), ("Neck", "Head"), ("LeftShoulder", "LeftArm")):
        ds = (REO @ (mw @ bm[ch].head) - REO @ (mw @ bm[c].head)).normalized()
        dt = (W[ch].translation - W[c].translation).normalized()
        print("DBG", c, "src", tuple(round(x, 2) for x in ds), "tgt", tuple(round(x, 2) for x in dt), "det", round(mw.determinant(), 5))


def fk(i, hp):
    W = {}
    for c, par in G.CANON:
        if par is None:
            W[c] = Rest[c].copy(); continue
        rel = Rest[par].inverted() @ Rest[c]
        B = basis[c][i].to_matrix().to_4x4()
        if c == "Hips":
            M = hp_matrix = Matrix.Translation(hp) @ (Rest["root"].to_3x3() @ (rel.to_3x3() @ basis[c][i].to_matrix())).to_4x4()
            W[c] = M
        else:
            W[c] = W[par] @ rel @ B
    return W


def contacts(i, hp):
    W = fk(i, hp)
    hs = []
    for s in ("Left", "Right"):
        hs.append(W[s + "Toe_End"].translation.z - Rest[s + "Toe_End"].translation.z)
        hs.append(W[s + "Foot"].translation.z - Rest[s + "Foot"].translation.z)
        hs.append(W[s + "ToeBase"].translation.z - Rest[s + "ToeBase"].translation.z)
    return min(hs), W


MAJOR = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "LeftArm", "LeftForeArm", "RightArm", "RightForeArm",
         "LeftUpLeg", "LeftLeg", "LeftFoot", "RightUpLeg", "RightLeg", "RightFoot"]


def pose_dist(i, j):
    return sum(min(basis[c][i].rotation_difference(basis[c][j]).angle, 2 * math.pi - basis[c][i].rotation_difference(basis[c][j]).angle) for c in MAJOR) / len(MAJOR) * 57.3

_dbg()
# ---------------------------------------------------------------- analyze
if a.analyze:
    print("ANALYZE", a.src, act.name, "N", N)
    for i in range(0, N, max(1, N // 60)):
        h, W = contacts(i, hips_pos[i])
        up = (W["Head"].translation - W["Hips"].translation).normalized()
        pitch = math.degrees(math.acos(max(-1, min(1, up.z))))
        print("F %4d hips (%.2f %.2f %.2f) h %.3f pitch %.0f d0 %.1f" % (frames[i], *hips_pos[i], h, pitch, pose_dist(0, i)))
    # loop candidates: for each start in first quarter, best end with dist small
    best = []
    for s in range(0, max(1, N // 3), 2):
        for e in range(s + 12, N):
            best.append((pose_dist(s, e) + 0.5 * pose_dist(min(s + 1, N - 1), min(e + 1, N - 1)), s, e))
    best.sort()
    print("LOOP best (dist,s,e):", [(round(d, 1), frames[s], frames[e]) for d, s, e in best[:12]])
    longest = sorted([x for x in best if x[0] < 4.0], key=lambda x: -(x[2] - x[1]))[:6]
    print("LOOP longest<4deg:", [(round(d, 1), frames[s], frames[e]) for d, s, e in longest])
    raise SystemExit(0)

# ---------------------------------------------------------------- trim
s_i = frames.index(a.start) if a.start is not None else 0
e_i = frames.index(a.end) if a.end is not None else N - 1
idx = list(range(s_i, e_i + 1))
basis = {c: [basis[c][i] for i in idx] for c in basis}
hips_pos = [hips_pos[i].copy() for i in idx]
N = len(idx)

# optional: counter-rotate the whole body about X so the torso lean (hips->neck, YZ plane) becomes --upright degrees
if a.upright is not None:
    tgt_d = Vector((0, -math.sin(math.radians(a.upright)), math.cos(math.radians(a.upright))))
    for i in range(N):
        W = fk(i, hips_pos[i])
        d = W["Neck"].translation - W["Hips"].translation
        d = Vector((0, d.y, d.z)).normalized()
        Q = d.rotation_difference(tgt_d)
        Rh = Tt["Hips"] @ basis["Hips"][i]
        basis["Hips"][i] = (Tt["Hips"].inverted() @ Q @ Rh).normalized()

# hips horizontal
if a.xy == "inplace":
    p0, p1 = hips_pos[0].copy(), hips_pos[-1].copy()
    for i in range(N):
        t = i / (N - 1)
        d = p0.lerp(p1, t)
        hips_pos[i].x += Tt_hips.x - d.x
        hips_pos[i].y += Tt_hips.y - d.y
    # remove residual mean offset
    mx = sum(p.x for p in hips_pos) / N - Tt_hips.x; my = sum(p.y for p in hips_pos) / N - Tt_hips.y
    for p in hips_pos:
        p.x -= mx; p.y -= my
elif a.xy == "zero":
    dx, dy = hips_pos[0].x - Tt_hips.x, hips_pos[0].y - Tt_hips.y
    for p in hips_pos:
        p.x -= dx; p.y -= dy

# loop closure: distribute rotation / hips residual so last frame == first
if a.loop and not a.noblend:
    for c in G.CANON_NAMES:
        seq = basis[c]
        for i in range(1, N):
            if seq[i].dot(seq[i - 1]) < 0:
                seq[i].negate()
        r = seq[0] @ seq[-1].inverted()
        for i in range(N):
            t = i / (N - 1)
            seq[i] = (Quaternion().slerp(r, t) @ seq[i]).normalized()
    dz = hips_pos[0] - hips_pos[-1]
    for i in range(N):
        hips_pos[i] += dz * (i / (N - 1))

# vertical / ground
hs = [contacts(i, hips_pos[i])[0] for i in range(N)]
if a.z == "ground":
    off = -min(hs)
    for p in hips_pos:
        p.z += off
elif a.z == "first":
    off = -hs[0]
    for p in hips_pos:
        p.z += off
elif a.z == "pin":
    for i, p in enumerate(hips_pos):
        p.z -= hs[i]
elif a.z == "pinall":   # lowest body part touches the ground every frame (falls / deaths)
    RAD = {"Hips": 0.11, "Spine": 0.11, "Spine1": 0.11, "Spine2": 0.11, "Neck": 0.08, "Head": 0.10, "HeadTop_End": 0.03,
           "LeftHand": 0.04, "RightHand": 0.04, "LeftForeArm": 0.05, "RightForeArm": 0.05, "LeftArm": 0.06, "RightArm": 0.06,
           "LeftLeg": 0.07, "RightLeg": 0.07, "LeftUpLeg": 0.09, "RightUpLeg": 0.09}
    for i, p in enumerate(hips_pos):
        h, W = contacts(i, p)
        hb = min(W[c].translation.z - r for c, r in RAD.items())
        p.z -= min(h, hb)
elif a.z == "center":   # water: keep bob, centre hips at rest height
    m = sum(p.z for p in hips_pos) / N
    for p in hips_pos:
        p.z += Tt_hips.z - m
hs2 = [contacts(i, hips_pos[i])[0] for i in range(N)]
print("contact h after: min %.3f max %.3f" % (min(hs2), max(hs2)))
for i in range(0, N, 3):
    W = fk(i, hips_pos[i])
    print("ZF", i, "hips z %.3f lfoot z %.3f rtoe %.3f" % (hips_pos[i].z, W["LeftFoot"].translation.z, W["RightToe_End"].translation.z))
W = fk(N // 2, hips_pos[N // 2])
up = (W["Head"].translation - W["Hips"].translation).normalized()
pitch_mid = math.degrees(math.acos(max(-1, min(1, up.z))))
travel = (hips_pos[-1] - hips_pos[0])
print("mid pitch %.0f deg, hips travel xy %.3f, loop end dist %.2f deg" % (pitch_mid, travel.xy.length, pose_dist(0, N - 1)))

# ---------------------------------------------------------------- write action
for c in G.CANON_NAMES:
    seq = basis[c]
    for i in range(1, N):
        if seq[i].dot(seq[i - 1]) < 0:
            seq[i].negate()
actn = bpy.data.actions.new(a.clip)
slot = actn.slots.new('OBJECT', "Armature")
layer = actn.layers.new("Layer")
strip = layer.strips.new(type='KEYFRAME')
cb = strip.channelbag(slot, ensure=True)


def put(path, idx_, vals, group):
    fc = cb.fcurves.new(path, index=idx_)
    grp = cb.groups.get(group) if hasattr(cb, "groups") else None
    fc.keyframe_points.add(len(vals) + 1)
    co = []
    for i, val in enumerate(vals):
        co += [float(i), float(val)]
    # rest key after the exported range: the FBX exporter writes bone Lcl (= import rest) from the current frame,
    # so we park the scene on this rest frame when exporting.
    restv = 1.0 if (path.endswith("rotation_quaternion") and idx_ == 0) else 0.0
    co += [float(len(vals) + 5), restv]
    fc.keyframe_points.foreach_set("co", co)
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
    fc.update()


for c in G.CANON_NAMES:
    pb = tgt.pose.bones[c]
    pb.rotation_mode = 'QUATERNION'
    for k in range(4):
        put(f'pose.bones["{c}"].rotation_quaternion', k, [q[k] for q in basis[c]], c)
    if c == "Hips":
        rel = Rest["root"].inverted() @ Rest["Hips"]
        locs = []
        for i in range(N):
            # pose matrix of hips = root_rest @ rel @ basis  ->  basis translation
            want = hips_pos[i]
            Bt = (Rest["Hips"].inverted() @ Matrix.Translation(want)).translation  # rotation-independent part
            # full: basis = Rest_h^-1 @ [want, R] ; translation of basis = Rest_h3^-1 @ (want - rest_head)
            Bt = Rest["Hips"].to_3x3().inverted() @ (want - Rest["Hips"].translation)
            locs.append(Bt)
        for k in range(3):
            put(f'pose.bones["{c}"].location', k, [l[k] for l in locs], c)
    else:
        for k in range(3):
            put(f'pose.bones["{c}"].location', k, [0.0] * N, c)
tgt.animation_data_create()
tgt.animation_data.action = actn
tgt.animation_data.action_slot = slot
sc.frame_start, sc.frame_end = 0, N - 1

# verify: evaluated Blender pose vs our FK at mid frame
sc.frame_set(N // 2)
Wb = tgt.pose.bones["LeftHand"].head
Wf = fk(N // 2, hips_pos[N // 2])["LeftHand"].translation
print("FK check LeftHand blender", tuple(round(x, 3) for x in Wb), "fk", tuple(round(x, 3) for x in Wf))

# remove source
for o in list(bpy.data.objects):
    if o is not tgt:
        bpy.data.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()
for o in bpy.data.objects:
    o.select_set(o is tgt)
bpy.context.view_layer.objects.active = tgt
fbx = os.path.join(OUT, a.clip + ".fbx")
sc.frame_set(N + 5)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'ARMATURE'},
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', global_scale=1.0,
                         axis_forward='-Z', axis_up='Y', bake_space_transform=False,
                         add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                         use_armature_deform_only=False, armature_nodetype='NULL',
                         bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                         bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
                         path_mode='AUTO', embed_textures=False)
G.save_json(os.path.join(WORK, a.clip + ".json"), {
    "name": a.clip, "file": a.clip + ".fbx", "frames": N, "fps": 30, "length_s": round((N - 1) / 30, 3),
    "loop": a.loop, "in_place": a.xy == "inplace", "source": a.src, "source_action": act.name,
    "source_range": [frames[s_i], frames[e_i]], "hips_z_mode": a.z, "mid_pitch_deg": round(pitch_mid),
    "hips_travel_xy_m": round(travel.xy.length, 3), "note": a.note})
print("EXPORTED", fbx, "frames", N)
