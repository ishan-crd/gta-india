"""Mumbai / Dharavi materials:
- MPC_Weather (Wetness, NightGlow) driven at runtime by AGIWeather.
- Wet streets: M_PBR is patched IN PLACE (instances keep their parent): upward-facing surfaces get darker and
  glossy with Wetness, and noise-masked puddles turn into flat mirrors.
- M_Rain: scrolling rain-streak curtain (translucent, unlit) for the camera rain cylinder.
- M_Neon + MI_Neon_01..06: glowing shop signs (brighter at night / in the rain via NightGlow).
Run after make_dharavi_textures.py (system python) has written ~/gta-india/assets/dharavi/*.png.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "01_materials.py")).read().replace("\nmain()\n", "\n")
exec(compile(src, "01_materials.py", "exec"))  # expr / link / new_material / make_instance

TEX_SRC = os.path.expanduser("~/gta-india/assets/dharavi")
DHARAVI_TEX = f"{ROOT}/Dharavi/Textures"
MPC_PATH = f"{MAT_DIR}/MPC_Weather"
atools = unreal.AssetToolsHelpers.get_asset_tools()


def build_mpc():
    mpc = load(MPC_PATH)
    if not mpc:
        mpc = atools.create_asset("MPC_Weather", MAT_DIR, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    params = []
    for name, val in (("Wetness", 0.0), ("NightGlow", 0.25)):
        p = unreal.CollectionScalarParameter()
        p.set_editor_property("parameter_name", name)
        p.set_editor_property("default_value", val)
        params.append(p)
    mpc.set_editor_property("scalar_parameters", params)
    eal.save_loaded_asset(mpc, False)
    return mpc


def coll_param(mat, mpc, name, x, y):
    e = expr(mat, unreal.MaterialExpressionCollectionParameter, x, y)
    e.set_editor_property("collection", mpc)
    e.set_editor_property("parameter_name", name)
    return e


def patch_pbr_wetness(mat, mpc):
    if any(isinstance(e, unreal.MaterialExpressionCollectionParameter) for e in _expressions(mat)):
        log("M_PBR already wet-capable:", mat.get_name())
        return
    bc_node = mel.get_material_property_input_node(mat, unreal.MaterialProperty.MP_BASE_COLOR)
    rough_node = mel.get_material_property_input_node(mat, unreal.MaterialProperty.MP_ROUGHNESS)
    normal_node = mel.get_material_property_input_node(mat, unreal.MaterialProperty.MP_NORMAL)
    if not (bc_node and rough_node and normal_node):
        warn("M_PBR layout unexpected, skipping wetness", mat.get_name())
        return
    x0, y0 = 200, 0
    wet_p = coll_param(mat, mpc, "Wetness", x0, y0 - 300)
    vn = expr(mat, unreal.MaterialExpressionVertexNormalWS, x0, y0 - 200)
    up = expr(mat, unreal.MaterialExpressionComponentMask, x0 + 150, y0 - 200, r=False, g=False, b=True, a=False)
    link(vn, "", up, "")
    up_sat = expr(mat, unreal.MaterialExpressionSaturate, x0 + 300, y0 - 200)
    link(up, "", up_sat, "")
    up_pow = expr(mat, unreal.MaterialExpressionPower, x0 + 420, y0 - 200)
    link(up_sat, "", up_pow, "Base")
    four = expr(mat, unreal.MaterialExpressionConstant, x0 + 300, y0 - 120, r=4.0)
    link(four, "", up_pow, "Exp")
    wet = expr(mat, unreal.MaterialExpressionMultiply, x0 + 560, y0 - 260)
    link(wet_p, "", wet, "A")
    link(up_pow, "", wet, "B")
    # puddle mask from world-space noise
    nz = expr(mat, unreal.MaterialExpressionNoise, x0, y0 + 100)
    for prop, val in (("scale", 0.0028), ("quality", 1), ("levels", 3), ("output_min", 0.0), ("output_max", 1.0)):
        try:
            nz.set_editor_property(prop, val)
        except Exception as e:
            warn("noise prop", prop, e)
    sub = expr(mat, unreal.MaterialExpressionSubtract, x0 + 150, y0 + 100)
    link(nz, "", sub, "A")
    c55 = expr(mat, unreal.MaterialExpressionConstant, x0, y0 + 220, r=0.56)
    link(c55, "", sub, "B")
    mul7 = expr(mat, unreal.MaterialExpressionMultiply, x0 + 300, y0 + 100)
    link(sub, "", mul7, "A")
    c7 = expr(mat, unreal.MaterialExpressionConstant, x0 + 150, y0 + 220, r=7.0)
    link(c7, "", mul7, "B")
    puddle = expr(mat, unreal.MaterialExpressionSaturate, x0 + 450, y0 + 100)
    link(mul7, "", puddle, "")
    pw = expr(mat, unreal.MaterialExpressionMultiply, x0 + 600, y0 + 60)
    link(wet, "", pw, "A")
    link(puddle, "", pw, "B")
    # base colour darkens when wet
    dark = expr(mat, unreal.MaterialExpressionMultiply, x0 + 600, y0 - 450)
    link(bc_node, "", dark, "A")
    c05 = expr(mat, unreal.MaterialExpressionConstant, x0 + 450, y0 - 420, r=0.5)
    link(c05, "", dark, "B")
    bc_l = expr(mat, unreal.MaterialExpressionLinearInterpolate, x0 + 800, y0 - 450)
    link(bc_node, "", bc_l, "A")
    link(dark, "", bc_l, "B")
    link(wet, "", bc_l, "Alpha")
    mel.connect_material_property(bc_l, "", unreal.MaterialProperty.MP_BASE_COLOR)
    # roughness: glossy when wet, mirror in puddles
    c016 = expr(mat, unreal.MaterialExpressionConstant, x0 + 650, y0 + 300, r=0.16)
    r1 = expr(mat, unreal.MaterialExpressionLinearInterpolate, x0 + 800, y0 + 260)
    link(rough_node, "", r1, "A")
    link(c016, "", r1, "B")
    link(wet, "", r1, "Alpha")
    c002 = expr(mat, unreal.MaterialExpressionConstant, x0 + 800, y0 + 380, r=0.02)
    r2 = expr(mat, unreal.MaterialExpressionLinearInterpolate, x0 + 950, y0 + 300)
    link(r1, "", r2, "A")
    link(c002, "", r2, "B")
    link(pw, "", r2, "Alpha")
    mel.connect_material_property(r2, "", unreal.MaterialProperty.MP_ROUGHNESS)
    # puddles are flat
    flat = expr(mat, unreal.MaterialExpressionConstant3Vector, x0 + 650, y0 + 480, constant=unreal.LinearColor(0, 0, 1, 1))
    nl = expr(mat, unreal.MaterialExpressionLinearInterpolate, x0 + 950, y0 + 480)
    link(normal_node, "RGB", nl, "A")
    link(flat, "", nl, "B")
    link(pw, "", nl, "Alpha")
    mel.connect_material_property(nl, "", unreal.MaterialProperty.MP_NORMAL)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat, False)
    log("wetness added to", mat.get_name())


def _expressions(mat):
    try:
        return list(mel.get_material_expressions(mat)) if hasattr(mel, "get_material_expressions") else list(mat.get_editor_property("expressions"))
    except Exception:
        return []


def import_tex(name, srgb=True):
    path = os.path.join(TEX_SRC, name + ".png")
    if not os.path.exists(path):
        warn("missing", path)
        return None
    run_tasks([import_task(path, DHARAVI_TEX)])
    t = load(f"{DHARAVI_TEX}/{name}")
    if t:
        t.set_editor_property("srgb", srgb)
        eal.save_loaded_asset(t, False)
    return t


def build_rain(tex):
    mat = new_material("M_Rain")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    tc = expr(mat, unreal.MaterialExpressionTextureCoordinate, -1200, 0)
    til = expr(mat, unreal.MaterialExpressionScalarParameter, -1200, 150, parameter_name="Tiling", default_value=8.0)
    half = expr(mat, unreal.MaterialExpressionMultiply, -1050, 220)
    link(til, "", half, "A")
    c45 = expr(mat, unreal.MaterialExpressionConstant, -1200, 260, r=0.45)
    link(c45, "", half, "B")
    tv = expr(mat, unreal.MaterialExpressionAppendVector, -900, 150)
    link(til, "", tv, "A")
    link(half, "", tv, "B")
    uv = expr(mat, unreal.MaterialExpressionMultiply, -800, 0)
    link(tc, "", uv, "A")
    link(tv, "", uv, "B")
    pan = expr(mat, unreal.MaterialExpressionPanner, -650, 0, speed_x=0.03, speed_y=-1.7)
    link(uv, "", pan, "Coordinate")
    smp = expr(mat, unreal.MaterialExpressionTextureSample, -450, 0)
    smp.set_editor_property("texture", tex)
    link(pan, "", smp, "UVs")
    amt = expr(mat, unreal.MaterialExpressionScalarParameter, -450, 250, parameter_name="Amount", default_value=1.0)
    op = expr(mat, unreal.MaterialExpressionMultiply, -250, 100)
    link(smp, "R", op, "A")
    link(amt, "", op, "B")
    op2 = expr(mat, unreal.MaterialExpressionMultiply, -100, 150)
    link(op, "", op2, "A")
    c03 = expr(mat, unreal.MaterialExpressionConstant, -250, 250, r=0.32)
    link(c03, "", op2, "B")
    mel.connect_material_property(op2, "", unreal.MaterialProperty.MP_OPACITY)
    col = expr(mat, unreal.MaterialExpressionConstant3Vector, -250, -150, constant=unreal.LinearColor(0.55, 0.6, 0.7, 1))
    em = expr(mat, unreal.MaterialExpressionMultiply, -100, -100)
    link(col, "", em, "A")
    link(op, "", em, "B")
    mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat, False)
    return mat


def build_neon(mpc):
    mat = new_material("M_Neon")
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("used_with_nanite", True)
    t = tex_param(mat, "SignTex", -900, 0, WHITE, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    base = expr(mat, unreal.MaterialExpressionMultiply, -500, -150)
    link(t, "RGB", base, "A")
    c = expr(mat, unreal.MaterialExpressionConstant, -650, -100, r=0.18)
    link(c, "", base, "B")
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    glow = coll_param(mat, mpc, "NightGlow", -900, 250)
    strength = expr(mat, unreal.MaterialExpressionScalarParameter, -900, 350, parameter_name="Strength", default_value=14.0)
    g = expr(mat, unreal.MaterialExpressionMultiply, -650, 300)
    link(glow, "", g, "A")
    link(strength, "", g, "B")
    em = expr(mat, unreal.MaterialExpressionMultiply, -400, 100)
    link(t, "RGB", em, "A")
    link(g, "", em, "B")
    mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    r = expr(mat, unreal.MaterialExpressionConstant, -400, 350, r=0.35)
    mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat, False)
    return mat


def main():
    ensure_dir(DHARAVI_TEX)
    mpc = build_mpc()
    for n in ("M_PBR", "M_PBR_TwoSided"):
        m = load(f"{MAT_DIR}/{n}")
        if m:
            patch_pbr_wetness(m, mpc)
    rain_tex = import_tex("T_RainStreaks", srgb=False)
    if rain_tex:
        build_rain(rain_tex)
    neon = build_neon(mpc)
    for i in range(1, 7):
        t = import_tex(f"T_Neon_{i:02d}")
        if t:
            make_instance(f"MI_Neon_{i:02d}", neon, {"SignTex": t, "Strength": 12.0 + 2.0 * (i % 3)})
    save_dir(ROOT)
    log("dharavi materials done")


main()
