"""Import Poly Haven textures and build the material library (master materials + instances).

UnrealEditor-Cmd GTAIndia.uproject -run=pythonscript -script=01_materials.py
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

MAT_DIR = f"{ROOT}/Materials"
TEX_DIR = f"{ROOT}/Textures"
PH_TEX = f"{ASSETS}/polyhaven/textures"
WATER_NORMAL = "/Water/Textures/Normals/T_Water_TilingNormal_Waves_02"
WHITE = "/Engine/EngineResources/WhiteSquareTexture"
FLAT_NORMAL = "/Engine/EngineMaterials/DefaultNormal"
ARM_DEFAULT = f"{ROOT}/Textures/large_sandstone_blocks/large_sandstone_blocks_arm"


def expr(mat, cls, x, y, **props):
    e = mel.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def link(a, a_out, b, b_in):
    ok = mel.connect_material_expressions(a, a_out, b, b_in)
    if not ok:
        warn("link failed", a.get_name(), a_out, "->", b.get_name(), b_in)
    return ok


def new_material(name, overwrite=True):
    path = f"{MAT_DIR}/{name}"
    if eal.does_asset_exist(path):
        if not overwrite:
            return load(path)
        eal.delete_asset(path)
    return at.create_asset(name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())


def tex_param(mat, name, x, y, default, sampler):
    return expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, x, y,
                parameter_name=name, texture=unreal.load_asset(default), sampler_type=sampler)


def build_pbr(name, two_sided=False):
    mat = new_material(name)
    mat.set_editor_property("two_sided", two_sided)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("used_with_skeletal_mesh", True)

    uv_scale = expr(mat, unreal.MaterialExpressionScalarParameter, -1500, 0, parameter_name="UVScale", default_value=1.0)
    tc = expr(mat, unreal.MaterialExpressionTextureCoordinate, -1500, -150)
    uv = expr(mat, unreal.MaterialExpressionMultiply, -1300, -100)
    link(tc, "", uv, "A")
    link(uv_scale, "", uv, "B")

    base = tex_param(mat, "BaseColor", -1000, -400, WHITE, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    link(uv, "", base, "UVs")
    tint = expr(mat, unreal.MaterialExpressionVectorParameter, -1000, -650, parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
    bc = expr(mat, unreal.MaterialExpressionMultiply, -700, -450)
    link(base, "RGB", bc, "A")
    link(tint, "RGB", bc, "B")

    # Macro variation: sample the same texture at a much larger scale to break up tiling.
    macro_scale = expr(mat, unreal.MaterialExpressionConstant, -1300, 150, r=0.113)
    macro_uv = expr(mat, unreal.MaterialExpressionMultiply, -1150, 150)
    link(uv, "", macro_uv, "A")
    link(macro_scale, "", macro_uv, "B")
    macro = tex_param(mat, "BaseColor", -1000, 150, WHITE, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    link(macro_uv, "", macro, "UVs")
    half = expr(mat, unreal.MaterialExpressionConstant, -800, 350, r=0.5)
    centred = expr(mat, unreal.MaterialExpressionSubtract, -650, 200)
    link(macro, "G", centred, "A")
    link(half, "", centred, "B")
    strength = expr(mat, unreal.MaterialExpressionScalarParameter, -650, 380, parameter_name="MacroVariation", default_value=0.7)
    scaled = expr(mat, unreal.MaterialExpressionMultiply, -500, 250)
    link(centred, "", scaled, "A")
    link(strength, "", scaled, "B")
    one = expr(mat, unreal.MaterialExpressionConstant, -500, 400, r=1.0)
    factor = expr(mat, unreal.MaterialExpressionAdd, -350, 300)
    link(one, "", factor, "A")
    link(scaled, "", factor, "B")
    final_bc = expr(mat, unreal.MaterialExpressionMultiply, -250, -300)
    link(bc, "", final_bc, "A")
    link(factor, "", final_bc, "B")
    mel.connect_material_property(final_bc, "", unreal.MaterialProperty.MP_BASE_COLOR)

    normal = tex_param(mat, "Normal", -1000, 600, FLAT_NORMAL, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    link(uv, "", normal, "UVs")
    mel.connect_material_property(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)

    arm = tex_param(mat, "ARM", -1000, 900, ARM_DEFAULT if eal.does_asset_exist(ARM_DEFAULT) else WHITE, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    link(uv, "", arm, "UVs")
    mel.connect_material_property(arm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    rough_scale = expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1000, parameter_name="RoughnessScale", default_value=1.0)
    rough = expr(mat, unreal.MaterialExpressionMultiply, -500, 950)
    link(arm, "G", rough, "A")
    link(rough_scale, "", rough, "B")
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    metal_scale = expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1150, parameter_name="MetallicScale", default_value=1.0)
    metal = expr(mat, unreal.MaterialExpressionMultiply, -500, 1100)
    link(arm, "B", metal, "A")
    link(metal_scale, "", metal, "B")
    mel.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)

    mel.layout_material_expressions(mat)
    mel.recompile_material(mat)
    return mat


def build_solid():
    mat = new_material("M_Solid")
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("used_with_skeletal_mesh", True)
    color = expr(mat, unreal.MaterialExpressionVectorParameter, -600, 0, parameter_name="Color", default_value=unreal.LinearColor(0.5, 0.5, 0.5, 1))
    mel.connect_material_property(color, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = expr(mat, unreal.MaterialExpressionScalarParameter, -600, 200, parameter_name="Roughness", default_value=0.6)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    metal = expr(mat, unreal.MaterialExpressionScalarParameter, -600, 300, parameter_name="Metallic", default_value=0.0)
    mel.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    emis = expr(mat, unreal.MaterialExpressionVectorParameter, -600, 450, parameter_name="Emissive", default_value=unreal.LinearColor(0, 0, 0, 1))
    mel.connect_material_property(emis, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    return mat


def build_water():
    mat = new_material("M_Water")
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    wp = expr(mat, unreal.MaterialExpressionWorldPosition, -1600, 0)
    xy = expr(mat, unreal.MaterialExpressionComponentMask, -1400, 0, r=True, g=True, b=False, a=False)
    link(wp, "", xy, "")
    normal_tex = unreal.load_asset(WATER_NORMAL) or unreal.load_asset(FLAT_NORMAL)
    layers = []
    for i, (scale, sx, sy) in enumerate(((900.0, 0.015, 0.006), (2600.0, -0.008, 0.011), (340.0, 0.03, -0.02))):
        div = expr(mat, unreal.MaterialExpressionDivide, -1200, i * 250)
        k = expr(mat, unreal.MaterialExpressionConstant, -1350, i * 250 + 120, r=scale)
        link(xy, "", div, "A")
        link(k, "", div, "B")
        pan = expr(mat, unreal.MaterialExpressionPanner, -1000, i * 250, speed_x=sx, speed_y=sy)
        link(div, "", pan, "Coordinate")
        s = expr(mat, unreal.MaterialExpressionTextureSample, -800, i * 250, texture=normal_tex,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        link(pan, "", s, "UVs")
        layers.append(s)
    add1 = expr(mat, unreal.MaterialExpressionAdd, -550, 100)
    link(layers[0], "RGB", add1, "A")
    link(layers[1], "RGB", add1, "B")
    add2 = expr(mat, unreal.MaterialExpressionAdd, -450, 200)
    link(add1, "", add2, "A")
    link(layers[2], "RGB", add2, "B")
    flat = expr(mat, unreal.MaterialExpressionConstant3Vector, -450, 400, constant=unreal.LinearColor(0, 0, 1, 1))
    nstr = expr(mat, unreal.MaterialExpressionScalarParameter, -450, 500, parameter_name="NormalStrength", default_value=0.45)
    lerp = expr(mat, unreal.MaterialExpressionLinearInterpolate, -300, 250)
    link(flat, "", lerp, "A")
    link(add2, "", lerp, "B")
    link(nstr, "", lerp, "Alpha")
    norm = expr(mat, unreal.MaterialExpressionNormalize, -150, 250)
    link(lerp, "", norm, "VectorInput")
    mel.connect_material_property(norm, "", unreal.MaterialProperty.MP_NORMAL)

    color = expr(mat, unreal.MaterialExpressionVectorParameter, -400, -300, parameter_name="WaterColor", default_value=unreal.LinearColor(0.045, 0.06, 0.035, 1))
    mel.connect_material_property(color, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = expr(mat, unreal.MaterialExpressionConstant, -400, -150, r=0.07)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    spec = expr(mat, unreal.MaterialExpressionConstant, -400, -80, r=0.5)
    mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)

    out = expr(mat, unreal.MaterialExpressionSingleLayerWaterMaterialOutput, 0, 500)
    scatter = expr(mat, unreal.MaterialExpressionVectorParameter, -400, 650, parameter_name="Scattering", default_value=unreal.LinearColor(0.05, 0.06, 0.035, 1))
    absorb = expr(mat, unreal.MaterialExpressionVectorParameter, -400, 800, parameter_name="Absorption", default_value=unreal.LinearColor(0.55, 0.42, 0.35, 1))
    phase = expr(mat, unreal.MaterialExpressionConstant, -400, 950, r=0.2)
    for name in ("ScatteringCoefficients", "Scattering Coefficients", "Scattering Coefficients (Albedo)"):
        if mel.connect_material_expressions(scatter, "RGB", out, name):
            break
    for name in ("AbsorptionCoefficients", "Absorption Coefficients"):
        if mel.connect_material_expressions(absorb, "RGB", out, name):
            break
    for name in ("PhaseG", "Phase G"):
        if mel.connect_material_expressions(phase, "", out, name):
            break
    mel.recompile_material(mat)
    return mat


def build_minimap():
    mat = new_material("M_Minimap")
    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    tc = expr(mat, unreal.MaterialExpressionTextureCoordinate, -900, 0)
    tex = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, -200, parameter_name="Map",
               texture=unreal.load_asset(WHITE), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    link(tc, "", tex, "UVs")
    # Warm, slightly contrasty map tint.
    tint = expr(mat, unreal.MaterialExpressionConstant3Vector, -600, -400, constant=unreal.LinearColor(1.15, 1.08, 0.95, 1))
    col = expr(mat, unreal.MaterialExpressionMultiply, -300, -250)
    link(tex, "RGB", col, "A")
    link(tint, "", col, "B")
    # Water renders almost black in a base-colour capture: tint dark pixels river-blue.
    lum = expr(mat, unreal.MaterialExpressionComponentMask, -300, -450, r=False, g=True, b=False, a=False)
    link(tex, "RGB", lum, "")
    thr = expr(mat, unreal.MaterialExpressionConstant, -300, -560, r=0.085)
    shifted = expr(mat, unreal.MaterialExpressionSubtract, -220, -500)
    link(lum, "", shifted, "A")
    link(thr, "", shifted, "B")
    k = expr(mat, unreal.MaterialExpressionConstant, -300, -520, r=30.0)
    lm = expr(mat, unreal.MaterialExpressionMultiply, -150, -480)
    link(shifted, "", lm, "A")
    link(k, "", lm, "B")
    sat_l = expr(mat, unreal.MaterialExpressionSaturate, -50, -480)
    link(lm, "", sat_l, "")
    water = expr(mat, unreal.MaterialExpressionConstant3Vector, -150, -600, constant=unreal.LinearColor(0.12, 0.28, 0.42, 1))
    mix = expr(mat, unreal.MaterialExpressionLinearInterpolate, 50, -300)
    link(water, "", mix, "A")
    link(col, "", mix, "B")
    link(sat_l, "", mix, "Alpha")
    mel.connect_material_property(mix, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    centre = expr(mat, unreal.MaterialExpressionConstant2Vector, -900, 200, r=0.5, g=0.5)
    dist = expr(mat, unreal.MaterialExpressionDistance, -700, 150)
    link(tc, "", dist, "A")
    link(centre, "", dist, "B")
    rad = expr(mat, unreal.MaterialExpressionConstant, -700, 300, r=0.5)
    sub = expr(mat, unreal.MaterialExpressionSubtract, -550, 200)
    link(rad, "", sub, "A")
    link(dist, "", sub, "B")
    sharp = expr(mat, unreal.MaterialExpressionConstant, -550, 350, r=80.0)
    mul = expr(mat, unreal.MaterialExpressionMultiply, -400, 250)
    link(sub, "", mul, "A")
    link(sharp, "", mul, "B")
    sat = expr(mat, unreal.MaterialExpressionSaturate, -250, 250)
    link(mul, "", sat, "")
    # Water captures as near-black: make it transparent so the HUD's river-blue disc shows through.
    opq = expr(mat, unreal.MaterialExpressionMultiply, -100, 300)
    link(sat, "", opq, "A")
    link(sat_l, "", opq, "B")
    mel.connect_material_property(opq, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    return mat


def build_marker():
    mat = new_material("M_Marker")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    color = expr(mat, unreal.MaterialExpressionConstant3Vector, -500, 0, constant=unreal.LinearColor(3.0, 1.9, 0.15, 1))
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    tc = expr(mat, unreal.MaterialExpressionTextureCoordinate, -700, 200)
    v = expr(mat, unreal.MaterialExpressionComponentMask, -550, 200, r=False, g=True, b=False, a=False)
    link(tc, "", v, "")
    op = expr(mat, unreal.MaterialExpressionMultiply, -350, 200)
    k = expr(mat, unreal.MaterialExpressionConstant, -550, 330, r=0.45)
    link(v, "", op, "A")
    link(k, "", op, "B")
    mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    return mat


def import_texture_set(set_name):
    folder = os.path.join(PH_TEX, set_name)
    dest = f"{TEX_DIR}/{set_name}"
    result = {}
    tasks = []
    for kind in ("diff", "nor", "arm"):
        f = os.path.join(folder, f"{set_name}_{kind}.jpg")
        if not os.path.exists(f):
            f = os.path.join(folder, f"{set_name}_{kind}.png")
        if not os.path.exists(f):
            continue
        asset = f"{dest}/{set_name}_{kind}"
        if eal.does_asset_exist(asset):
            result[kind] = load(asset)
            continue
        tasks.append(import_task(f, dest))
    run_tasks(tasks)
    for kind in ("diff", "nor", "arm"):
        asset = f"{dest}/{set_name}_{kind}"
        tex = load(asset)
        if not tex:
            continue
        if kind == "nor":
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property("srgb", False)
            tex.set_editor_property("flip_green_channel", True)  # Poly Haven nor_gl -> DirectX
        elif kind == "arm":
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
            tex.set_editor_property("srgb", False)
        result[kind] = tex
    return result


def make_instance(name, parent, params):
    path = f"{MAT_DIR}/Instances/{name}"
    mi = load(path)
    if not mi:
        mi = at.create_asset(name, f"{MAT_DIR}/Instances", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    for k, v in params.items():
        if isinstance(v, unreal.Texture):
            mel.set_material_instance_texture_parameter_value(mi, k, v)
        elif isinstance(v, tuple):
            mel.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
        else:
            mel.set_material_instance_scalar_parameter_value(mi, k, float(v))
    mel.update_material_instance(mi)
    return mi


def main():
    ensure_dir(MAT_DIR)
    ensure_dir(f"{MAT_DIR}/Instances")
    ensure_dir(TEX_DIR)
    pbr = build_pbr("M_PBR")
    pbr2 = build_pbr("M_PBR_TwoSided", two_sided=True)
    solid = build_solid()
    build_water()
    build_minimap()
    build_marker()

    for slot, set_name in SLOT_TEXTURES.items():
        texs = import_texture_set(set_name)
        if "diff" not in texs:
            warn("missing textures for", slot, set_name)
            continue
        tw = SLOT_TWEAKS.get(slot, {})
        params = {"BaseColor": texs["diff"]}
        if "nor" in texs:
            params["Normal"] = texs["nor"]
        if "arm" in texs:
            params["ARM"] = texs["arm"]
        if "tint" in tw:
            params["Tint"] = tw["tint"]
        if "uv" in tw:
            params["UVScale"] = tw["uv"]
        if "rough" in tw:
            params["RoughnessScale"] = tw["rough"]
        make_instance("MI_" + slot[2:], pbr2 if tw.get("two_sided") else pbr, params)
        log("material", slot)

    for slot, p in SOLID_SLOTS.items():
        make_instance("MI_" + slot[2:], solid, {"Color": p["color"], "Roughness": p["rough"], "Metallic": p["metal"]})

    # Extra tinted cloth variants for awnings / umbrellas / flags.
    cloth = load(f"{TEX_DIR}/crepe_satin/crepe_satin_diff")
    if cloth:
        for nm, col in (("ClothRed", (0.8, 0.06, 0.04)), ("ClothBlue", (0.08, 0.2, 0.7)), ("ClothGreen", (0.1, 0.5, 0.1)),
                        ("ClothYellow", (1.0, 0.75, 0.05)), ("ClothWhite", (0.95, 0.93, 0.9))):
            make_instance("MI_" + nm, pbr2, {"BaseColor": cloth, "Tint": col,
                                              "Normal": load(f"{TEX_DIR}/crepe_satin/crepe_satin_nor") or unreal.load_asset(FLAT_NORMAL),
                                              "ARM": load(f"{TEX_DIR}/crepe_satin/crepe_satin_arm") or unreal.load_asset(WHITE)})

    save_dir(ROOT)
    log("materials done")


main()
