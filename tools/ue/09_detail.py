"""Detail pass assets: floating river debris (bobbing material), electric wires, grass materials and
foliage props. Run after 01-04."""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "01_materials.py")).read().replace("\nmain()\n", "\n")
exec(compile(src, "01_materials.py", "exec"))  # reuse expr / link / new_material / make_instance / import_texture_set

DETAIL_SRC = f"{ASSETS}/detail"
DETAIL_DIR = f"{ROOT}/Detail"
PROP_DIR = f"{ROOT}/Props"
FOLIAGE_HINTS = ("grass", "leaf", "leaves", "fern", "shrub", "plant", "tree", "banana", "foliage", "branch")


def build_floating():
    """Unlit-ish debris on the water: colour param + gentle world-position bob (WPO)."""
    mat = new_material("M_Floating")
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    color = expr(mat, unreal.MaterialExpressionVectorParameter, -700, -200, parameter_name="Color", default_value=unreal.LinearColor(0.8, 0.8, 0.8, 1))
    mel.connect_material_property(color, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = expr(mat, unreal.MaterialExpressionScalarParameter, -700, 0, parameter_name="Roughness", default_value=0.6)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    # bob: z = sin(time*1.6 + (wx+wy)*0.013) * 2.5 cm, plus a slow tilt-free drift on x
    t = expr(mat, unreal.MaterialExpressionTime, -1100, 300)
    k = expr(mat, unreal.MaterialExpressionConstant, -1100, 380, r=1.6)
    tk = expr(mat, unreal.MaterialExpressionMultiply, -950, 320)
    link(t, "", tk, "A")
    link(k, "", tk, "B")
    wp = expr(mat, unreal.MaterialExpressionWorldPosition, -1100, 480)
    xy = expr(mat, unreal.MaterialExpressionComponentMask, -950, 480, r=True, g=True, b=False, a=False)
    link(wp, "", xy, "")
    dot1 = expr(mat, unreal.MaterialExpressionDotProduct, -800, 480)
    one2 = expr(mat, unreal.MaterialExpressionConstant2Vector, -950, 560, r=0.013, g=0.011)
    link(xy, "", dot1, "A")
    link(one2, "", dot1, "B")
    ph = expr(mat, unreal.MaterialExpressionAdd, -650, 400)
    link(tk, "", ph, "A")
    link(dot1, "", ph, "B")
    sn = expr(mat, unreal.MaterialExpressionSine, -500, 400)
    link(ph, "", sn, "")
    amp = expr(mat, unreal.MaterialExpressionConstant, -500, 480, r=2.5)
    z = expr(mat, unreal.MaterialExpressionMultiply, -350, 420)
    link(sn, "", z, "A")
    link(amp, "", z, "B")
    zero = expr(mat, unreal.MaterialExpressionConstant, -350, 520, r=0.0)
    vec = expr(mat, unreal.MaterialExpressionAppendVector, -200, 460)
    zero2 = expr(mat, unreal.MaterialExpressionConstant2Vector, -350, 300, r=0.0, g=0.0)
    link(zero2, "", vec, "A")
    link(z, "", vec, "B")
    mel.connect_material_property(vec, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mel.recompile_material(mat)
    return mat


def import_fbx_static(path, dest, name, import_materials):
    o = unreal.FbxImportUI()
    o.set_editor_property("import_mesh", True)
    o.set_editor_property("import_as_skeletal", False)
    o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    o.set_editor_property("import_materials", import_materials)
    o.set_editor_property("import_textures", import_materials)
    d = o.get_editor_property("static_mesh_import_data")
    d.set_editor_property("combine_meshes", True)
    d.set_editor_property("auto_generate_collision", False)
    d.set_editor_property("import_uniform_scale", FBX_SCALE)
    run_tasks([import_task(path, dest, o, name=name)])
    return load(f"{dest}/{name}")


def make_foliage_masked(folder):
    for p in eal.list_assets(folder, recursive=True, include_folder=False):
        a = load(p.split(".")[0])
        if not isinstance(a, unreal.Material):
            continue
        n = a.get_name().lower()
        if not any(h in n for h in FOLIAGE_HINTS):
            continue
        src_node = mel.get_material_property_input_node(a, unreal.MaterialProperty.MP_BASE_COLOR)
        if src_node and isinstance(src_node, unreal.MaterialExpressionTextureSample):
            a.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
            a.set_editor_property("two_sided", True)
            a.set_editor_property("used_with_instanced_static_meshes", True)
            a.set_editor_property("used_with_nanite", True)
            mel.connect_material_property(src_node, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
            mel.recompile_material(a)
            eal.save_loaded_asset(a, False)
            log("foliage masked", a.get_name())


def main():
    set_legacy_fbx(True)
    ensure_dir(DETAIL_DIR)
    floating = build_floating()
    colors = {"M_Plastic": (0.55, 0.55, 0.5), "M_PlasticBlue": (0.18, 0.3, 0.45), "M_Marigold": (1.0, 0.42, 0.02),
              "M_Leaf": (0.22, 0.28, 0.08), "M_Foam": (0.8, 0.78, 0.7)}
    mis = {}
    for slot, c in colors.items():
        mis[slot] = make_instance("MI_" + slot[2:], floating, {"Color": c, "Roughness": 0.5 if slot != "M_Foam" else 0.9})
    mis["M_Cloth"] = make_instance("MI_DebrisRag", floating, {"Color": (0.35, 0.12, 0.08), "Roughness": 0.8})
    mis["M_WindowDark"] = load(f"{MAT_DIR}/Instances/MI_WindowDark")

    manifest = read_json(f"{DETAIL_SRC}/detail_manifest.json", {})
    for name, info in manifest.items():
        mesh = import_fbx_static(info["file"], DETAIL_DIR, "SM_" + name, False)
        if not mesh:
            warn("detail import failed", name)
            continue
        for i, sm in enumerate(mesh.get_editor_property("static_materials")):
            slot = str(sm.get_editor_property("material_slot_name")).split(".")[0]
            if slot in mis and mis[slot]:
                mesh.set_material(i, mis[slot])
        log("detail", name)

    # Grass ground material
    for set_name, mi_name in (("leafy_grass", "MI_Grass"), ("sparse_grass", "MI_GrassSparse")):
        texs = import_texture_set(set_name)
        if "diff" in texs:
            params = {"BaseColor": texs["diff"], "Normal": texs.get("nor"), "ARM": texs.get("arm"), "Tint": (0.95, 0.9, 0.7)}
            make_instance(mi_name, load(f"{MAT_DIR}/M_PBR"), {k: v for k, v in params.items() if v is not None})

    # Shop signboards (Hindi + English)
    sign_dir = f"{ASSETS}/signs"
    if os.path.isdir(sign_dir):
        files = sorted(f for f in os.listdir(sign_dir) if f.endswith(".png"))
        run_tasks([import_task(os.path.join(sign_dir, f), f"{TEX_DIR}/Signs") for f in files])
        for f in files:
            tex = load(f"{TEX_DIR}/Signs/{f[:-4]}")
            if tex:
                make_instance("MI_" + f[2:-4], load(f"{MAT_DIR}/M_PBR"), {"BaseColor": tex, "RoughnessScale": 0.8, "MacroVariation": 0.0})
                log("sign", f)

    # New Poly Haven foliage props
    props = read_json(f"{ASSETS}/props/props_manifest.json", {})
    for name in ("PH_grass_medium_01", "PH_grass_medium_02", "PH_grass_bermuda_01", "PH_shrub_03", "PH_fern_02"):
        if name in props:
            mesh = import_fbx_static(props[name]["file"], f"{PROP_DIR}/{name}", "SM_" + name, True)
            if mesh:
                ns = mesh.get_editor_property("nanite_settings")
                ns.set_editor_property("enabled", False)
                mesh.set_editor_property("nanite_settings", ns)
                log("foliage prop", name)
    make_foliage_masked(PROP_DIR)
    save_dir(ROOT)
    log("detail done")


main()
