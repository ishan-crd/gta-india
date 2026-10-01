"""Delete generated mesh / character / map assets so they can be re-imported cleanly."""
import unreal
for d in ("/Game/GTAIndia/Kit", "/Game/GTAIndia/Props", "/Game/Characters", "/Game/Maps"):
    if unreal.EditorAssetLibrary.does_directory_exist(d):
        unreal.EditorAssetLibrary.delete_directory(d)
        unreal.log("[GI] deleted " + d)
