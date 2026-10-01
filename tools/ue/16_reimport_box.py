"""Re-import the delivery backpack (SM_DeliveryBox) after regenerating it with tools/blender/gi_box*.py.
Deletes the old mesh/material/texture first so the new texture is picked up."""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

SRC = f"{ASSETS}/characters"
DEST = "/Game/Characters/DeliveryBox"
set_legacy_fbx(True)
for p in eal.list_assets(DEST, recursive=False, include_folder=False):
    eal.delete_asset(p.split(".")[0])
    log("deleted", p)
o = unreal.FbxImportUI()
o.set_editor_property("import_mesh", True)
o.set_editor_property("import_as_skeletal", False)
o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
o.set_editor_property("import_materials", True)
o.set_editor_property("import_textures", True)
o.get_editor_property("static_mesh_import_data").set_editor_property("combine_meshes", True)
o.get_editor_property("static_mesh_import_data").set_editor_property("import_uniform_scale", FBX_SCALE)
run_tasks([import_task(f"{SRC}/SM_DeliveryBox.fbx", DEST, o, name="SM_DeliveryBox")])
mesh = load(f"{DEST}/SM_DeliveryBox")
log("box reimported", mesh)
save_dir(DEST)
