"""gi_manifest.py - collect _work/*.json into characters/manifest.json (python3)."""
import json, os, glob
OUT = os.path.expanduser("~/gta-india/assets/characters")
W = os.path.join(OUT, "_work")
order = ["SK_Player", "SK_ManBlue", "SK_ManRed", "SK_SareeWoman", "SK_ManKurta", "SK_ManKurta2", "SK_WomanSaree", "SK_Teen", "SK_OfficeWoman",
         # crowd batch 2 (ordinary Indian street people)
         "SK_ManPolo", "SK_ManStriped", "SK_ManShirt", "SK_OldManKurta", "SK_BoyKurta",
         "SK_WomanPinkSaree", "SK_WomanMarathi", "SK_WomanSareeYellow", "SK_KidGreen", "SK_KidOrange", "SK_KidTeal", "SK_KidWhite", "SK_KidBare", "SK_PlayerDhoti"]
AGE = {"SK_KidGreen": "child", "SK_KidOrange": "child", "SK_KidTeal": "child", "SK_KidWhite": "child", "SK_KidBare": "child",
       "SK_Teen": "teen", "SK_OldManKurta": "old", "SK_BoyKurta": "child", "SK_WomanSareeYellow": "middle_aged", "SK_ManPolo": "middle_aged"}
anims = ["A_Idle", "A_Walk", "A_Run", "A_Jump", "A_Fall", "A_Land", "A_Swim", "A_Tread", "A_SitIdle", "A_SitTalk", "A_PickUp", "A_Death"]
chars = []
for n in order:
    d = json.load(open(os.path.join(W, n + ".json")))
    chars.append({"name": n, "file": d["file"], "height_m": d["height_m"], "gender": d["gender"], "tris": d["tris"],
                  "source": d["source"], "textures_dir": f"textures/{n[3:]}", "texture_copies_for_fbx": n + ".fbm/",
                  "age": AGE.get(n, "adult"),
                  "textures": {m: {"base": t["base"], "normal": t["normal"], "roughness": t["roughness"]} for m, t in d["textures"].items()}})
an = []
for n in anims:
    d = json.load(open(os.path.join(W, n + ".json")))
    an.append({"name": n, "file": d["file"], "frames": d["frames"], "fps": 30, "length_s": d["length_s"], "loop": d["loop"],
               "in_place": d["in_place"], "source": d["source"], "source_action": d["source_action"],
               "source_frames_30fps": d["source_range"], "hips_z": d["hips_z_mode"], "note": d["note"]})
box = json.load(open(os.path.join(W, "SM_DeliveryBox.json")))
m = {
    "skeleton": {"name": "GI_Human", "reference_mesh": "SK_Player.fbx", "bone_count": 66,
                 "hierarchy": "root > Hips > Spine > Spine1 > Spine2 > Neck > Head > HeadTop_End; Spine2 > {Left,Right}Shoulder > Arm > ForeArm > Hand > Hand{Thumb,Index,Middle,Ring,Pinky}{1,2,3}; Hips > {Left,Right}UpLeg > Leg > Foot > ToeBase > Toe_End",
                 "rest_pose": "T-pose, arms along +-X, legs straight down, feet on Z=0, root at origin between the feet",
                 "bone_axes": "Blender: bone Y -> child joint; roll so local Z = world -Y (forward) except thumbs/feet/toes where local Z = world +Z. All characters copy the SK_Player bone orientations exactly (max deviation 0 deg).",
                 "armature_object_name": "Armature"},
    "facing": {"blender": "-Y (character's left = +X, up = +Z)", "unreal_expected": "+Y (UE mannequin convention) -> rotate mesh component yaw -90 to face +X"},
    "units": "metres in Blender; FBX written in centimetres (1 m = 100 UE units)",
    "export_settings": {"exporter": "Blender 5.2 FBX (io_scene_fbx)", "apply_unit_scale": True, "apply_scale_options": "FBX_SCALE_UNITS",
                        "global_scale": 1.0, "axis_forward": "-Z", "axis_up": "Y", "bake_space_transform": False,
                        "primary_bone_axis": "Y", "secondary_bone_axis": "X", "add_leaf_bones": False, "armature_nodetype": "NULL",
                        "use_armature_deform_only": False,
                        "meshes": {"object_types": ["ARMATURE", "MESH"], "bake_anim": False, "mesh_smooth_type": "FACE",
                                   "path_mode": "COPY", "embed_textures": False},
                        "anims": {"object_types": ["ARMATURE"], "bake_anim": True, "bake_anim_use_all_actions": False,
                                  "bake_anim_use_nla_strips": False, "bake_anim_force_startend_keying": True, "bake_anim_step": 1.0,
                                  "bake_anim_simplify_factor": 0.0, "fps": 30}},
    "characters": chars,
    "dropped_characters": {"SK_ManDhoti": "source glTF is broken: the mesh is mostly an unbound dhoti cloth sheet and body parts sit away from the skeleton even in the raw import (no clean T-pose possible)",
                           "SK_ManSitting": "odd 25-bone non-Mixamo rig bound in a sitting pose - not trivial",
                           "SK_OldVillager (ch_villager)": "cartoon proportions (huge head, stylised) - not realistic next to the rest of the crowd",
                           "SK_ManFormal (ch_man_formal_rpm)": "same ReadyPlayerMe base mesh/outfit as SK_ManShirt - duplicate",
                           "SK_ManGreenShirt (ch_man_opurbo)": "built fine but generic long-sleeve western look; kept the set at 8",
                           "SK_WomanModern (ch_woman_modern)": "built fine but sunglasses + jeans party outfit; poor fit for a Varanasi ghat crowd",
                           "ch_man_kalakar / ch_old_uncle / ch_girl_kurta / ch_man_pinkkurta": "Rigify / MB-Lab / Character Creator rigs (no Mixamo bone names) - not retargeted"},
    "anims": an,
    "props": [{"name": "SM_DeliveryBox", "file": box["file"], "tris": box["tris"], "size_m": {"width_x": 0.44, "depth_y": 0.42, "height_z": 0.44, "with_straps_y": box["dims_m"][1]},
               "material": "M_DeliveryBox", "texture": box["texture"],
               "pivot": "centre of the face that touches the rider's back (box -Y face); box extends toward +Y in Blender (behind a -Y-facing character) = -Y in UE (behind a +Y-facing character). Straps on that face; 'GANGA EXPRESS' on the outward +Y face (Blender)."}],
    "credits": "~/gta-india/assets/sketchfab/CREDITS.txt",
}
json.dump(m, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
print("manifest ok", len(chars), len(an))
