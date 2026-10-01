"""Give every solid prop collision (the dhaba chairs, crates, carts... were walk-through).
Foliage and floating debris stay non-colliding."""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

SKIP = ("grass", "fern", "shrub", "tree", "banana", "debris", "wires", "plant", "flower")
n = 0
for p in eal.list_assets(f"{ROOT}/Props", recursive=True, include_folder=False):
    m = load(p.split(".")[0])
    if not isinstance(m, unreal.StaticMesh) or any(k in m.get_name().lower() for k in SKIP):
        continue
    bs = m.get_editor_property("body_setup")
    if not bs:
        continue
    if bs.get_editor_property("collision_trace_flag") != unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
        geom = bs.get_editor_property("agg_geom")
        if len(geom.get_editor_property("convex_elems")) + len(geom.get_editor_property("box_elems")) == 0:
            bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            eal.save_loaded_asset(m, False)
            n += 1
log("collision enabled on", n, "props")
