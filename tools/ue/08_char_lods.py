"""Generate automatic LODs for character meshes (big win for the crowd)."""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

sme = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
for p in eal.list_assets("/Game/Characters", recursive=True, include_folder=False):
    a = load(p.split(".")[0])
    if not isinstance(a, unreal.SkeletalMesh):
        continue
    ok = sme.regenerate_lod(a, 4, False, False)
    try:
        n = sme.get_lod_count(a)
    except Exception:
        n = "?"
    log("lods", a.get_name(), ok, n)
    eal.save_loaded_asset(a, False)
log("DONE")
