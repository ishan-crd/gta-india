"""Fix the ARM sampler of the PBR masters: Masks sampler with a linear default texture."""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

ARM_DEFAULT = f"{ROOT}/Textures/large_sandstone_blocks/large_sandstone_blocks_arm"
for name in ("M_PBR", "M_PBR_TwoSided"):
    m = load(f"{ROOT}/Materials/{name}")
    arm = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    arm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    arm.set_editor_property("texture", load(ARM_DEFAULT))
    mel.recompile_material(m)
    st = mel.get_statistics(m)
    log(name, "pixel instructions", st.num_pixel_shader_instructions)
    eal.save_loaded_asset(m, False)
