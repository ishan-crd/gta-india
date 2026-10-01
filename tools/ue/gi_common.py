"""Shared helpers for the GTA India editor-Python build scripts (run inside UnrealEditor-Cmd)."""
import json
import os

import unreal

HOME = os.path.expanduser("~")
ASSETS = f"{HOME}/gta-india/assets"
ROOT = "/Game/GTAIndia"
# Our Blender FBX exports arrive at 1/100 scale in the legacy importer (metres read as cm).
FBX_SCALE = 100.0

at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary

# Kit material slot -> Poly Haven texture set (see SPEC.md)
SLOT_TEXTURES = {
    "M_Sandstone": "large_sandstone_blocks",
    "M_SandstoneRed": "red_sandstone_wall",
    "M_SandstoneSteps": "sandstone_blocks_05",
    "M_SandstoneOld": "old_sandstone_02",
    "M_Pavement": "red_sandstone_pavement",
    "M_PlasterYellow": "yellow_plaster",
    "M_PlasterOchre": "yellow_plaster_02",
    "M_PlasterRed": "red_plaster_weathered",
    "M_PlasterBlue": "blue_plaster_weathered",
    "M_PlasterPeeling": "peeling_painted_wall",
    "M_PlasterMossy": "worn_mossy_plasterwall",
    "M_PlasterDamaged": "damaged_plaster",
    "M_PlasterWhite": "white_plaster_rough_01",
    "M_PlasterPainted": "painted_plaster_wall",
    "M_PlasterWorn": "worn_plaster_wall",
    "M_ClayPlaster": "patterned_clay_plaster",
    "M_BrickPlaster": "red_brick_plaster_patch_02",
    "M_BrickWhite": "whitewashed_brick",
    "M_Mud": "brown_mud",
    "M_MudDry": "brown_mud_dry",
    "M_Dirt": "dirt",
    "M_DryGround": "dry_ground_01",
    "M_Trail": "rocky_trail",
    "M_Riverbed": "mud_cracked_dry_riverbed_002",
    "M_RiverPebbles": "ganges_river_pebbles",
    "M_RoadDamaged": "road_damaged",
    "M_Asphalt": "worn_asphalt",
    "M_CorrugatedRust": "rusty_corrugated_iron",
    "M_Shutter": "rusty_metal_shutter",
    "M_WoodShutter": "wood_shutter",
    "M_WoodPlanks": "weathered_planks",
    "M_RoofTiles": "clay_roof_tiles",
    "M_Cloth": "crepe_satin",
    "M_MetalRust": "rusty_metal_02",
    "M_Concrete": "concrete_floor_worn_001",
    "M_Thatch": "reed_roof_04",
    "M_Ballast": "gravel_floor_02",
    "M_Steel": "rusty_metal",
    "M_TrainWhite": "dirty_concrete",
    "M_TrainPurple": "dirty_concrete",
    "M_TrainRoof": "dirty_concrete",
    "M_GroundLitter": "leaf_scattered_gravel",
    "M_VillageGround": "dry_mud_field_001",
    "M_FlowerDirt": "flower_scattered_dirt",
    "M_MuddyTracks": "muddy_tracks",
    # --- Dharavi kit (kit_dharavi.py)
    "M_PlasterTeal": "painted_concrete",            # green-teal peeling paint
    "M_PlasterTurquoise": "blue_plaster_weathered",  # tinted turquoise (SLOT_TWEAKS)
    "M_PlasterCream": "white_plaster_rough_01",      # tinted cream
    "M_BrickExposed": "rough_plaster_brick",         # exposed brick with plaster remains
    "M_AsbestosRoof": "asbestos_sheet_02",           # grey cement/asbestos corrugated sheets
    "M_CorrugatedGalv": "worn_corrugated_iron",      # worn galvanised sheet
    "M_CorrugatedPainted": "rusty_painted_metal",    # red-oxide painted rusty sheet
    "M_TinGreen": "green_metal_rust",                # painted green tin doors
    "M_TinBlue": "blue_metal_plate",                 # painted blue tin doors / panels
    "M_ConcreteDirty": "dirty_concrete",             # stained concrete (gateway, skirting)
    "M_LaundryRed": "cotton_jersey", "M_LaundryYellow": "cotton_jersey", "M_LaundryPink": "cotton_jersey",
    "M_LaundryGreen": "cotton_jersey", "M_LaundryBlueL": "cotton_jersey", "M_LaundryWhite": "cotton_jersey",
    "M_LaundryPurple": "cotton_jersey", "M_LaundryOrange": "cotton_jersey",
    "M_SackWhite": "cotton_jersey", "M_SackGreen": "cotton_jersey", "M_SackBlue": "cotton_jersey",
    "M_SackBeige": "cotton_jersey",
}

# Extra per-slot tweaks: tint (linear RGB), uv scale, roughness scale, two-sided
SLOT_TWEAKS = {
    "M_Cloth": {"tint": (1.0, 0.42, 0.08), "two_sided": True},
    "M_Thatch": {"two_sided": True, "uv": 1.5},
    "M_PlasterYellow": {"tint": (1.05, 0.95, 0.8)},
    "M_PlasterRed": {"tint": (1.0, 0.8, 0.75)},
    "M_Riverbed": {"tint": (0.75, 0.68, 0.6)},
    "M_Steel": {"rough": 0.8},
    "M_TrainWhite": {"tint": (1.12, 1.1, 1.05), "uv": 0.5},
    "M_TrainPurple": {"tint": (0.42, 0.2, 0.75), "uv": 0.5},
    "M_TrainRoof": {"tint": (0.42, 0.41, 0.4), "uv": 0.5, "rough": 0.7},
    "M_GroundLitter": {"tint": (0.95, 0.85, 0.7)},
    # --- Dharavi kit
    "M_PlasterTeal": {"tint": (0.75, 1.05, 1.1)},
    "M_PlasterTurquoise": {"tint": (0.55, 1.2, 1.25)},
    "M_PlasterCream": {"tint": (1.6, 1.5, 1.25)},
    "M_AsbestosRoof": {"tint": (1.05, 1.05, 1.05), "uv": 1.0},
    "M_LaundryRed": {"tint": (0.95, 0.08, 0.06), "two_sided": True},
    "M_LaundryYellow": {"tint": (1.3, 0.95, 0.08), "two_sided": True},
    "M_LaundryPink": {"tint": (1.3, 0.3, 0.6), "two_sided": True},
    "M_LaundryGreen": {"tint": (0.12, 0.65, 0.18), "two_sided": True},
    "M_LaundryBlueL": {"tint": (0.35, 0.65, 1.3), "two_sided": True},
    "M_LaundryWhite": {"tint": (1.3, 1.3, 1.3), "two_sided": True},
    "M_LaundryPurple": {"tint": (0.45, 0.12, 0.8), "two_sided": True},
    "M_LaundryOrange": {"tint": (1.3, 0.45, 0.05), "two_sided": True},
    "M_SackWhite": {"tint": (1.25, 1.25, 1.2), "uv": 3.0},
    "M_SackGreen": {"tint": (0.35, 0.75, 0.4), "uv": 3.0},
    "M_SackBlue": {"tint": (0.3, 0.5, 1.1), "uv": 3.0},
    "M_SackBeige": {"tint": (1.05, 0.9, 0.65), "uv": 3.0},
}

SOLID_SLOTS = {
    "M_WindowDark": {"color": (0.012, 0.011, 0.01), "rough": 0.35, "metal": 0.0},
    "M_Saffron": {"color": (0.9, 0.28, 0.02), "rough": 0.6, "metal": 0.0},
    "M_Gold": {"color": (0.95, 0.66, 0.2), "rough": 0.3, "metal": 1.0},
    "M_Whitewash": {"color": (0.78, 0.76, 0.7), "rough": 0.85, "metal": 0.0},
    "M_Signboard": {"color": (0.8, 0.12, 0.08), "rough": 0.6, "metal": 0.0},
    # --- Dharavi kit (kit_dharavi.py)
    "M_TarpBlue": {"color": (0.02, 0.12, 0.45), "rough": 0.5, "metal": 0.0},       # blue tarpaulin (geometry is double-sided)
    "M_PlasticBlue": {"color": (0.01, 0.09, 0.4), "rough": 0.4, "metal": 0.0},     # drums, stools, buckets
    "M_PlasticRed": {"color": (0.55, 0.02, 0.02), "rough": 0.4, "metal": 0.0},
    "M_PlasticYellow": {"color": (0.8, 0.5, 0.02), "rough": 0.45, "metal": 0.0},
    "M_Terracotta": {"color": (0.45, 0.15, 0.06), "rough": 0.85, "metal": 0.0},    # matka clay pots
    "M_ClayGreen": {"color": (0.05, 0.2, 0.08), "rough": 0.6, "metal": 0.0},       # painted pot
    "M_TeaSteel": {"color": (0.7, 0.7, 0.72), "rough": 0.3, "metal": 1.0},         # aluminium / steel pots, glasses
    "M_Brass": {"color": (0.8, 0.55, 0.2), "rough": 0.35, "metal": 1.0},
    "M_Glass": {"color": (0.35, 0.4, 0.38), "rough": 0.05, "metal": 0.0},          # jar glass (opaque stand-in)
    "M_LPGRed": {"color": (0.5, 0.02, 0.015), "rough": 0.35, "metal": 0.3},
    "M_Rubber": {"color": (0.02, 0.02, 0.02), "rough": 0.9, "metal": 0.0},         # tyres, cables, grips
    "M_TennisYellow": {"color": (0.75, 0.8, 0.05), "rough": 0.95, "metal": 0.0},
    "M_BatWillow": {"color": (0.62, 0.45, 0.25), "rough": 0.7, "metal": 0.0},
    "M_VegGreen": {"color": (0.06, 0.25, 0.02), "rough": 0.55, "metal": 0.0},
    "M_VegRed": {"color": (0.6, 0.03, 0.02), "rough": 0.35, "metal": 0.0},
    "M_Onion": {"color": (0.4, 0.09, 0.12), "rough": 0.45, "metal": 0.0},
    "M_VegBrown": {"color": (0.32, 0.2, 0.09), "rough": 0.8, "metal": 0.0},
    "M_Poster": {"color": (0.7, 0.6, 0.45), "rough": 0.8, "metal": 0.0},           # 0..1 UV per poster quad (atlas-ready)
    "M_Snack_01": {"color": (0.8, 0.15, 0.02), "rough": 0.3, "metal": 0.2},        # snack sachets
    "M_Snack_02": {"color": (0.85, 0.6, 0.02), "rough": 0.3, "metal": 0.2},
    "M_Snack_03": {"color": (0.04, 0.15, 0.7), "rough": 0.3, "metal": 0.2},
    "M_Snack_04": {"color": (0.08, 0.45, 0.08), "rough": 0.3, "metal": 0.2},
    "M_SnackFoil": {"color": (0.75, 0.75, 0.78), "rough": 0.25, "metal": 0.9},
    # light-box sign faces (0..1 UV over each face) - meant to become emissive (see "emissive" hint)
    "M_Neon_01": {"color": (1.0, 0.05, 0.4), "rough": 0.4, "metal": 0.0, "emissive": (8.0, 0.4, 3.0)},
    "M_Neon_02": {"color": (0.05, 0.8, 1.0), "rough": 0.4, "metal": 0.0, "emissive": (0.4, 6.0, 8.0)},
    "M_Neon_03": {"color": (1.0, 0.05, 0.02), "rough": 0.4, "metal": 0.0, "emissive": (8.0, 0.4, 0.2)},
    "M_Neon_04": {"color": (0.1, 1.0, 0.2), "rough": 0.4, "metal": 0.0, "emissive": (0.8, 8.0, 1.5)},
    "M_Neon_05": {"color": (1.0, 0.7, 0.05), "rough": 0.4, "metal": 0.0, "emissive": (8.0, 5.0, 0.4)},
    "M_Neon_06": {"color": (1.0, 1.0, 1.0), "rough": 0.4, "metal": 0.0, "emissive": (6.0, 6.0, 6.5)},
}


def log(*args):
    unreal.log("[GI] " + " ".join(str(a) for a in args))


def warn(*args):
    unreal.log_warning("[GI] " + " ".join(str(a) for a in args))


def ensure_dir(path):
    if not eal.does_directory_exist(path):
        eal.make_directory(path)


def set_legacy_fbx(enabled=True):
    """Use the classic FBX importer (FbxImportUI options) instead of Interchange for .fbx."""
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX " + ("False" if enabled else "True"))


def import_task(filename, dest, options=None, name=None, replace=True):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", filename)
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", replace)
    t.set_editor_property("save", False)
    if name:
        t.set_editor_property("destination_name", name)
    if options is not None:
        t.set_editor_property("options", options)
    return t


def run_tasks(tasks):
    if not tasks:
        return []
    at.import_asset_tasks(tasks)
    out = []
    for t in tasks:
        out.extend(t.get_editor_property("imported_object_paths") or [])
    return out


def load(path):
    return unreal.load_asset(path) if eal.does_asset_exist(path) else None


def save_dir(path):
    eal.save_directory(path, only_if_is_dirty=True, recursive=True)


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def asset_path(obj):
    return obj.get_path_name().split(".")[0]
