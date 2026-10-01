"""Import characters onto one shared skeleton, then the animation clips, then the delivery box."""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

SRC = f"{ASSETS}/characters"
CHAR_DIR = "/Game/Characters"
ANIM_DIR = "/Game/Characters/Anims"
SKELETON = f"{CHAR_DIR}/SK_Player/SK_Player_Skeleton"


def skel_options(skeleton):
    o = unreal.FbxImportUI()
    o.set_editor_property("import_mesh", True)
    o.set_editor_property("import_as_skeletal", True)
    o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    o.set_editor_property("import_materials", True)
    o.set_editor_property("import_textures", True)
    o.set_editor_property("import_animations", False)
    o.set_editor_property("create_physics_asset", False)
    if skeleton:
        o.set_editor_property("skeleton", skeleton)
    d = o.get_editor_property("skeletal_mesh_import_data")
    d.set_editor_property("import_morph_targets", False)
    d.set_editor_property("import_uniform_scale", FBX_SCALE)
    try:
        d.set_editor_property("use_t0_as_ref_pose", False)
    except Exception:
        pass
    return o


def anim_options(skeleton):
    o = unreal.FbxImportUI()
    o.set_editor_property("import_mesh", False)
    o.set_editor_property("import_as_skeletal", True)
    o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    o.set_editor_property("import_animations", True)
    o.set_editor_property("import_materials", False)
    o.set_editor_property("import_textures", False)
    o.set_editor_property("skeleton", skeleton)
    a = o.get_editor_property("anim_sequence_import_data")
    a.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    a.set_editor_property("remove_redundant_keys", False)
    a.set_editor_property("import_uniform_scale", FBX_SCALE)
    try:
        a.set_editor_property("import_bone_tracks", True)
    except Exception:
        pass
    return o


ALPHA_HINTS = ("hair", "lash", "brow", "eyelash", "haircut", "beard")


def fix_character_materials(folder):
    """Hair / lashes use alpha: make those materials masked with base-colour alpha as the mask."""
    for p in eal.list_assets(folder, recursive=True, include_folder=False):
        a = load(p.split(".")[0])
        if not isinstance(a, unreal.Material):
            continue
        name = a.get_name().lower()
        a.set_editor_property("used_with_skeletal_mesh", True)
        if any(h in name for h in ALPHA_HINTS):
            src = mel.get_material_property_input_node(a, unreal.MaterialProperty.MP_BASE_COLOR)
            if src and isinstance(src, unreal.MaterialExpressionTextureSample):
                a.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
                a.set_editor_property("two_sided", True)
                mel.connect_material_property(src, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
                log("masked material", a.get_name())
        mel.recompile_material(a)


def main():
    set_legacy_fbx(True)
    manifest = read_json(f"{SRC}/manifest.json", {})
    chars = manifest.get("characters", [])
    anims = manifest.get("anims", [])
    if not chars:
        warn("no characters manifest")
        return
    # Player first: it defines the skeleton.
    chars.sort(key=lambda c: 0 if c["name"] == "SK_Player" else 1)
    skeleton = None
    for c in chars:
        name = c["name"]
        f = os.path.join(SRC, c.get("file") or f"{name}.fbx")
        if not os.path.exists(f):
            warn("missing", f)
            continue
        dest = f"{CHAR_DIR}/{name}"
        run_tasks([import_task(f, dest, skel_options(skeleton), name=name)])
        mesh = load(f"{dest}/{name}")
        if not mesh:
            warn("character import failed", name)
            continue
        if skeleton is None:
            skeleton = mesh.get_editor_property("skeleton")
        log("character", name, "skeleton", skeleton.get_name() if skeleton else None)

    if not skeleton:
        return
    ok = unreal.GIEditorLib.setup_shared_skeleton(skeleton, "root", "Hips")
    log("shared skeleton setup", ok)

    ensure_dir(ANIM_DIR)
    for a in anims:
        name = a["name"]
        f = os.path.join(SRC, a.get("file") or f"{name}.fbx")
        if not os.path.exists(f):
            continue
        run_tasks([import_task(f, ANIM_DIR, anim_options(skeleton), name=name)])
        seq = load(f"{ANIM_DIR}/{name}")
        if seq:
            try:
                seq.set_editor_property("enable_root_motion", False)
            except Exception:
                pass
            log("anim", name, seq.get_editor_property("sequence_length") if hasattr(seq, "get_editor_property") else "")
        else:
            # The FBX importer may append the take name; find any sequence starting with the name.
            found = [p for p in eal.list_assets(ANIM_DIR, recursive=False) if os.path.basename(p).split(".")[0].startswith(name)]
            warn("anim not at expected path", name, found)

    box = f"{SRC}/SM_DeliveryBox.fbx"
    if os.path.exists(box):
        o = unreal.FbxImportUI()
        o.set_editor_property("import_mesh", True)
        o.set_editor_property("import_as_skeletal", False)
        o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        o.set_editor_property("import_materials", True)
        o.set_editor_property("import_textures", True)
        o.get_editor_property("static_mesh_import_data").set_editor_property("combine_meshes", True)
        o.get_editor_property("static_mesh_import_data").set_editor_property("import_uniform_scale", FBX_SCALE)
        run_tasks([import_task(box, f"{CHAR_DIR}/DeliveryBox", o, name="SM_DeliveryBox")])

    fix_character_materials(CHAR_DIR)
    save_dir(CHAR_DIR)
    log("characters done")


main()
