"""Set usage flags on every material so nothing falls back to the default material in cooked /
-game runs (Nanite, instanced static meshes, skeletal meshes)."""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

FLAGS = ("used_with_nanite", "used_with_instanced_static_meshes", "used_with_skeletal_mesh", "used_with_static_lighting")


def main():
    n = 0
    for folder in ("/Game/GTAIndia", "/Game/Characters"):
        for p in eal.list_assets(folder, recursive=True, include_folder=False):
            a = load(p.split(".")[0])
            if not isinstance(a, unreal.Material):
                continue
            if a.get_editor_property("material_domain") != unreal.MaterialDomain.MD_SURFACE:
                continue
            changed = False
            for f in FLAGS:
                if f == "used_with_nanite" and a.get_editor_property("shading_model") == unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER:
                    continue
                try:
                    if not a.get_editor_property(f):
                        a.set_editor_property(f, True)
                        changed = True
                except Exception:
                    pass
            if changed:
                mel.recompile_material(a)
                eal.save_loaded_asset(a, False)
                n += 1
    log("usage flags set on", n, "materials")


main()
