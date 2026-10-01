"""Import only characters from manifest.json that aren't in the project yet, onto the existing shared
skeleton (keeps the already-tuned characters, materials and LODs untouched)."""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "03_import_characters.py")).read().replace("\nmain()\n", "\n")
exec(compile(src, "03_import_characters.py", "exec"))

set_legacy_fbx(True)
skeleton = load(SKELETON)
manifest = read_json(f"{SRC}/manifest.json", {})
sme = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
new = []
for c in manifest.get("characters", []):
    name = c["name"]
    dest = f"{CHAR_DIR}/{name}"
    if eal.does_asset_exist(f"{dest}/{name}"):
        continue
    f = os.path.join(SRC, c.get("file") or f"{name}.fbx")
    if not os.path.exists(f):
        continue
    run_tasks([import_task(f, dest, skel_options(skeleton), name=name)])
    mesh = load(f"{dest}/{name}")
    if mesh:
        sme.regenerate_lod(mesh, 4, False, False)
        new.append(name)
        log("new character", name)
fix_character_materials(CHAR_DIR)
save_dir(CHAR_DIR)
log("new characters", new)
