"""Clothing variety + underwater murk.
- Outfit materials of the Avaturn-style characters get OutfitTint / OutfitTintStrength parameters
  (colourise the clothes; the crowd picks random Indian clothing colours at runtime).
- The single-material saree woman gets hue-shifted saree textures (saffron, red, green, blue, magenta).
- M_Murk: translucent sphere material for the underwater view.
Writes ~/gta-india/assets/characters/variety.json for 06_write_config.py.
"""
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "01_materials.py")).read().replace("\nmain()\n", "\n")
exec(compile(src, "01_materials.py", "exec"))

CHAR_DIR = "/Game/Characters"
OUT_JSON = f"{ASSETS}/characters/variety.json"
VARIANT_HUES = {"Saffron": 24, "Red": 0, "Green": 125, "Blue": 220, "Magenta": 315}


def build_murk():
    mat = new_material("M_Murk")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    col = expr(mat, unreal.MaterialExpressionConstant3Vector, -400, 0, constant=unreal.LinearColor(0.16, 0.13, 0.05, 1))
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = expr(mat, unreal.MaterialExpressionConstant, -400, 200, r=0.93)
    mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)


def make_outfit_tintable(m):
    """BaseColor = lerp(tex, desaturate(tex) * OutfitTint * 1.7, OutfitTintStrength)."""
    if "OutfitTint" in [str(x) for x in mel.get_vector_parameter_names(m)]:
        return True
    src_node = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
    if not src_node:
        return False
    out_name = "RGB" if isinstance(src_node, unreal.MaterialExpressionTextureSample) else ""
    des = expr(m, unreal.MaterialExpressionDesaturation, -500, -300)
    link(src_node, out_name, des, "")
    tint = expr(m, unreal.MaterialExpressionVectorParameter, -500, -450, parameter_name="OutfitTint", default_value=unreal.LinearColor(1, 1, 1, 1))
    mul = expr(m, unreal.MaterialExpressionMultiply, -350, -350)
    link(des, "", mul, "A")
    link(tint, "RGB", mul, "B")
    boost = expr(m, unreal.MaterialExpressionConstant, -350, -450, r=1.7)
    mul2 = expr(m, unreal.MaterialExpressionMultiply, -220, -350)
    link(mul, "", mul2, "A")
    link(boost, "", mul2, "B")
    strength = expr(m, unreal.MaterialExpressionScalarParameter, -350, -200, parameter_name="OutfitTintStrength", default_value=0.0)
    lerp = expr(m, unreal.MaterialExpressionLinearInterpolate, -100, -300)
    link(src_node, out_name, lerp, "A")
    link(mul2, "", lerp, "B")
    link(strength, "", lerp, "Alpha")
    mel.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.recompile_material(m)
    eal.save_loaded_asset(m, False)
    return True


def hue_variants(src_png, out_dir, base):
    """Run the recolour in the system python (editor python has no numpy/Pillow)."""
    import subprocess
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    r = subprocess.run(["/usr/bin/python3", os.path.join(HERE, "hue_variants.py"), src_png, out_dir, base],
                       capture_output=True, text=True, env=env)
    log("hue variants", r.stdout.strip().splitlines()[-1:] if r.stdout else r.stderr[-300:])
    return {n: os.path.join(out_dir, f"{base}_{n}.png") for n in VARIANT_HUES if os.path.exists(os.path.join(out_dir, f"{base}_{n}.png"))}


def main():
    build_murk()
    variety = {}
    for p in eal.list_assets(CHAR_DIR, recursive=True, include_folder=False):
        mesh = load(p.split(".")[0])
        if not isinstance(mesh, unreal.SkeletalMesh) or mesh.get_name() == "SK_Player":
            continue
        entry = {"tint_slots": [], "variants": []}
        mats = mesh.get_editor_property("materials")
        for sm in mats:
            slot = str(sm.get_editor_property("material_slot_name"))
            mi = sm.get_editor_property("material_interface")
            if mi and "outfit" in mi.get_name().lower() and "shoes" not in mi.get_name().lower() and isinstance(mi, unreal.Material):
                if make_outfit_tintable(mi):
                    entry["tint_slots"].append(slot)
        if mesh.get_name() == "SK_SareeWoman" and len(mats) == 1:
            m = mats[0].get_editor_property("material_interface")
            node = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
            tex = node.get_editor_property("texture") if isinstance(node, unreal.MaterialExpressionTextureSample) else None
            src_file = tex.get_editor_property("asset_import_data").get_first_filename() if tex else ""
            if src_file and os.path.exists(src_file):
                out_dir = f"{ASSETS}/characters/variants"
                os.makedirs(out_dir, exist_ok=True)
                try:
                    files = hue_variants(src_file, out_dir, "T_SareeWoman")
                except Exception as e:
                    warn("hue variants failed in editor python", e)
                    files = {}
                folder = f"{CHAR_DIR}/SK_SareeWoman/Variants"
                for name, f in files.items():
                    run_tasks([import_task(f, folder)])
                    vt = load(f"{folder}/{os.path.basename(f)[:-4]}")
                    dup_path = f"{folder}/M_SareeWoman_{name}"
                    if not eal.does_asset_exist(dup_path):
                        eal.duplicate_asset(m.get_path_name().split(".")[0], dup_path)
                    dm = load(dup_path)
                    dn = mel.get_material_property_input_node(dm, unreal.MaterialProperty.MP_BASE_COLOR)
                    if vt and isinstance(dn, unreal.MaterialExpressionTextureSample):
                        dn.set_editor_property("texture", vt)
                        mel.recompile_material(dm)
                        eal.save_loaded_asset(dm, False)
                        entry["variants"].append(dup_path)
        variety[mesh.get_name()] = entry
        log("variety", mesh.get_name(), entry)
    json.dump(variety, open(OUT_JSON, "w"), indent=1)
    save_dir(CHAR_DIR)
    save_dir(f"{ROOT}/Materials")
    log("variety done")


main()
