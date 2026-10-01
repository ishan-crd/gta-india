"""Rebuild only the minimap material (used after changing its setup)."""
import importlib.util, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("mats", os.path.join(os.path.dirname(os.path.abspath(__file__)), "01_materials.py"))
src = open(spec.origin).read().replace("\nmain()\n", "\n")
exec(compile(src, spec.origin, "exec"))
build_minimap()
save_dir(MAT_DIR)
log("minimap rebuilt")
