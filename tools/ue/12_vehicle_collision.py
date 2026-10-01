"""Vehicles get simple box collision (no walking into coach interiors, solid autos)."""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

sml = unreal.EditorStaticMeshLibrary
for name in ("TrainIndian", "TrainCoachLHB", "TrainAnim", "AutoRickshaw", "AutoRickshaw2", "BikePulsar150", "BikePulsar135"):
    m = load(f"{ROOT}/Props/{name}/SM_{name}")
    if not m:
        continue
    sml.remove_collisions(m)
    sml.add_simple_collisions(m, unreal.ScriptingCollisionShapeType.BOX)
    bs = m.get_editor_property("body_setup")
    bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
    eal.save_loaded_asset(m, False)
    log("box collision", name, sml.get_simple_collision_count(m))
