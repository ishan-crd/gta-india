"""Re-import SK_Player (after rebuilding it in Blender from a new source) onto the existing shared
skeleton, keeping every other character, animation and the skeleton asset untouched."""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "03_import_characters.py")).read().replace("\nmain()\n", "\n")
exec(compile(src, "03_import_characters.py", "exec"))

set_legacy_fbx(True)
skeleton = load(SKELETON)
f = os.path.join(SRC, "SK_Player.fbx")
dest = f"{CHAR_DIR}/SK_Player"
if skeleton and os.path.exists(f):
    # A re-import onto the old asset keeps its old material slots (new slots come in empty), so drop the
    # old mesh + its materials/textures first; the shared skeleton asset stays.
    for p in eal.list_assets(dest, recursive=False, include_folder=False):
        base = p.split(".")[0]
        if not base.endswith("SK_Player_Skeleton"):
            eal.delete_asset(base)
            log("deleted", base)
    run_tasks([import_task(f, dest, skel_options(skeleton), name="SK_Player")])
    mesh = load(f"{dest}/SK_Player")
    log("player reimported", mesh.get_name() if mesh else None, "skeleton", skeleton.get_name())
    for sm in mesh.get_editor_property("materials"):
        log("slot", sm.get_editor_property("material_slot_name"), sm.get_editor_property("material_interface"))
    fix_character_materials(dest)
    save_dir(dest)
else:
    warn("player reimport skipped: skeleton", skeleton, "fbx exists", os.path.exists(f))
