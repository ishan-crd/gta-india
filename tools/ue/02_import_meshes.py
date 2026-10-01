"""Import the Blender kit (buildings, ghats, rail...) and converted props as static meshes.

Kit meshes get Nanite, complex-as-simple collision and materials assigned by slot name.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

KIT_SRC = f"{ASSETS}/kit"
PROP_SRC = f"{ASSETS}/props"
KIT_DIR = f"{ROOT}/Kit"
PROP_DIR = f"{ROOT}/Props"
MI_DIR = f"{ROOT}/Materials/Instances"
# GI_ONLY=name,name,... limits the import to those kit pieces / props (names without the SM_ prefix).
ONLY = {n for n in os.environ.get("GI_ONLY", "").split(",") if n}

# Props that should not use Nanite (translucent parts / small / moving)
NO_NANITE = {"Train_EMU_Car", "Train_EMU_Cab", "AutoRickshaw", "AutoRickshaw2", "BikePulsar150", "BikePulsar135", "TrainCoachLHB", "TrainIndian", "TrainAnim",
             "BoatSF", "BoatOld", "BoatWooden", "Zebu", "Zebu2", "Buffalo"}
# Props that should block the player
PROP_COLLISION = {"CarWagonR", "CarNano", "BusBEST", "TaxiKaaliPeeli2", "HinduTemple", "TemplesSet", "KiranaShop", "BhelpuriShop", "HouseOld", "TemplePillar", "Nandi",
                  "TrainCoachLHB", "TrainIndian", "TrainAnim", "AutoRickshaw", "AutoRickshaw2", "Zebu", "Zebu2", "Buffalo",
                  "BoatSF", "BoatOld", "BoatWooden"}


def fbx_options(import_materials):
    o = unreal.FbxImportUI()
    o.set_editor_property("import_mesh", True)
    o.set_editor_property("import_as_skeletal", False)
    o.set_editor_property("import_animations", False)
    o.set_editor_property("import_materials", import_materials)
    o.set_editor_property("import_textures", import_materials)
    o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    d = o.get_editor_property("static_mesh_import_data")
    d.set_editor_property("combine_meshes", True)
    d.set_editor_property("auto_generate_collision", False)
    d.set_editor_property("generate_lightmap_u_vs", False)
    d.set_editor_property("remove_degenerates", True)
    d.set_editor_property("import_uniform_scale", FBX_SCALE)
    try:
        d.set_editor_property("build_nanite", False)
    except Exception:
        pass
    return o


def set_nanite(mesh, enabled, full_res_fallback=False):
    ns = mesh.get_editor_property("nanite_settings")
    ns.set_editor_property("enabled", enabled)
    if full_res_fallback:
        for prop, val in (("fallback_percent_triangles", 1.0), ("fallback_relative_error", 0.0)):
            try:
                ns.set_editor_property(prop, val)
            except Exception:
                pass
    mesh.set_editor_property("nanite_settings", ns)


def set_complex_collision(mesh):
    bs = mesh.get_editor_property("body_setup")
    if bs:
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)


def assign_slot_materials(mesh):
    mats = mesh.get_editor_property("static_materials")
    for i, sm in enumerate(mats):
        slot = str(sm.get_editor_property("material_slot_name")).split(".")[0]
        mi = load(f"{MI_DIR}/MI_{slot[2:]}") if slot.startswith("M_") else None
        if mi:
            mesh.set_material(i, mi)
        else:
            warn("no material for slot", slot, "on", mesh.get_name())


def import_kit():
    ensure_dir(KIT_DIR)
    files = sorted(f for f in os.listdir(KIT_SRC) if f.lower().endswith(".fbx")) if os.path.isdir(KIT_SRC) else []
    if ONLY:
        files = [f for f in files if f[:-4] in ONLY]
    tasks = [import_task(os.path.join(KIT_SRC, f), KIT_DIR, fbx_options(False), name="SM_" + f[:-4]) for f in files]
    run_tasks(tasks)
    for f in files:
        mesh = load(f"{KIT_DIR}/SM_{f[:-4]}")
        if not mesh:
            warn("kit import failed", f)
            continue
        assign_slot_materials(mesh)
        set_complex_collision(mesh)
        set_nanite(mesh, True, full_res_fallback=True)
        log("kit", f)


def import_props():
    ensure_dir(PROP_DIR)
    manifest = read_json(f"{PROP_SRC}/props_manifest.json", {})
    tasks = []
    names = []
    for name, info in manifest.items():
        if ONLY and name not in ONLY:
            continue
        path = info["file"]
        if not os.path.exists(path):
            continue
        dest = f"{PROP_DIR}/{name}"
        tasks.append(import_task(path, dest, fbx_options(True), name="SM_" + name))
        names.append(name)
    run_tasks(tasks)
    for name in names:
        mesh = load(f"{PROP_DIR}/{name}/SM_{name}")
        if not mesh:
            warn("prop import failed", name)
            continue
        base = name[3:] if name.startswith("PH_") else name
        if name in PROP_COLLISION:
            set_complex_collision(mesh)
        set_nanite(mesh, name not in NO_NANITE and not name.startswith("PH_"))
        log("prop", name)


def main():
    set_legacy_fbx(True)
    import_kit()
    import_props()
    save_dir(ROOT)
    log("meshes done")


main()
