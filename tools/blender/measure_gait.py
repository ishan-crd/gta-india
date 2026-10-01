"""Measure in-place locomotion clips: ground speed implied by planted feet, cycle length, and the
normalised phase where the left foot plants. blender -b --python measure_gait.py -- A_Walk.fbx ..."""
import bpy, sys, os, json
from mathutils import Vector
files = sys.argv[sys.argv.index("--") + 1:]
res = {}
for f in files:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=f)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    act = arm.animation_data.action
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    fps = bpy.context.scene.render.fps
    lf, rf, hips = arm.pose.bones.get("LeftFoot"), arm.pose.bones.get("RightFoot"), arm.pose.bones.get("Hips")
    samples = []
    for fr in range(f0, f1 + 1):
        bpy.context.scene.frame_set(fr)
        mw = arm.matrix_world
        samples.append(((mw @ lf.head), (mw @ rf.head), (mw @ hips.head)))
    # forward axis = the axis along which feet move the most
    span = [max(s[0][i] for s in samples) - min(s[0][i] for s in samples) for i in range(3)]
    ax = 0 if span[0] > span[1] else 1
    speeds = []
    lowL = min(s[0].z for s in samples)
    lowR = min(s[1].z for s in samples)
    for i in range(1, len(samples)):
        for k, low in ((0, lowL), (1, lowR)):
            if samples[i][k].z < low + 0.03 and samples[i - 1][k].z < low + 0.03:
                speeds.append(abs(samples[i][k][ax] - samples[i - 1][k][ax]) * fps)
    speeds.sort()
    v = speeds[len(speeds) // 2] if speeds else 0.0
    # left plant: first frame where the left foot reaches its low point after being high
    zL = [s[0].z for s in samples]
    plant = min(range(len(zL)), key=lambda i: (zL[i] - lowL) + (0 if i == 0 else max(0, zL[i - 1] - zL[i]) * -1))
    res[os.path.basename(f)] = {"frames": f1 - f0 + 1, "fps": fps, "length_s": (f1 - f0) / fps, "ground_speed_cm_s": round(v * 100, 1),
                                "left_plant_phase": round(plant / max(1, len(zL) - 1), 3), "fwd_axis": "XY"[ax]}
    print("GAIT", json.dumps({os.path.basename(f): res[os.path.basename(f)]}))
