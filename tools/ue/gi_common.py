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
}

SOLID_SLOTS = {
    "M_WindowDark": {"color": (0.012, 0.011, 0.01), "rough": 0.35, "metal": 0.0},
    "M_Saffron": {"color": (0.9, 0.28, 0.02), "rough": 0.6, "metal": 0.0},
    "M_Gold": {"color": (0.95, 0.66, 0.2), "rough": 0.3, "metal": 1.0},
    "M_Whitewash": {"color": (0.78, 0.76, 0.7), "rough": 0.85, "metal": 0.0},
    "M_Signboard": {"color": (0.8, 0.12, 0.08), "rough": 0.6, "metal": 0.0},
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
