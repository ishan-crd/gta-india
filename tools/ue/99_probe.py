import unreal
m = unreal.load_asset("/Game/GTAIndia/Materials/M_PBR")
mel = unreal.MaterialEditingLibrary
unreal.log("[GI] num expr %d" % mel.get_num_material_expressions(m))
for prop in ("MP_BASE_COLOR", "MP_NORMAL", "MP_ROUGHNESS", "MP_METALLIC", "MP_AMBIENT_OCCLUSION"):
    n = mel.get_material_property_input_node(m, getattr(unreal.MaterialProperty, prop))
    unreal.log("[GI] %s <- %s" % (prop, n.get_name() if n else None))
mel.recompile_material(m)
try:
    unreal.log("[GI] stats %s" % mel.get_statistics(m))
except Exception as e:
    unreal.log("[GI] stats err %s" % e)
