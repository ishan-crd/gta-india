"""Build /Game/Maps/Trial - ONE Dharavi lane, laid out after the reference screenshot:
a ~28 m galli (4.2 m wall to wall) of vivid blue row houses with grey asbestos roofs sloping over it,
otas along the fronts, a curtain doorway and a blue drum on the left, a wooden door, barred window, chappals
and a leaning bicycle on the right, laundry high across the lane, clothes under the eaves; it opens into a
small square where kids play gully cricket, the end house facing down the lane, a brick two-storey behind
the right row and trees over the roofs. The woman in the sari walks towards you on the left.
Camera, player model and pace come from an AGILevelProfile (low, close, centred chase cam).
Player walks +X. Left side of the lane = +Y. Ground at Z = 0.
"""
import math
import os
import random
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "05_build_level.py")).read().replace("\nmain()\n", "\n")
exec(compile(_src, "05_build_level.py", "exec"))  # noqa - Scatter, mesh, xf, spawn, build_lighting, ...

MAP = "/Game/Maps/Trial"
MAT_DIR = f"{ROOT}/Materials"
R = random.Random(20261003)

HALF = 210                 # lane half width at the facades (4.2 m wall to wall)
LANE_X0, LANE_X1 = -1400, 2800
SQ_X0, SQ_X1 = 2800, 4300  # the kids' square
SQ_Y0, SQ_Y1 = -800, 1400
HOUSE_W = {f"Trial_House_{i:02d}": w for i, w in enumerate((3.9, 4.3, 3.6, 4.1, 3.8, 4.4, 3.7, 4.0, 4.6, 3.5), 1)}
LEFT_ORDER = ["Trial_House_03", "Trial_House_07", "Trial_House_01", "Trial_House_04", "Trial_House_09", "Trial_House_05",
              "Trial_House_06", "Trial_House_10", "Trial_House_02", "Trial_House_08"]
RIGHT_ORDER = ["Trial_House_05", "Trial_House_10", "Trial_House_02", "Trial_House_08", "Trial_House_04", "Trial_House_07",
               "Trial_House_09", "Trial_House_01", "Trial_House_03", "Trial_House_06"]
PLAYER_START = unreal.Vector(150, -20, 100)


def row(sc, names, x0, x1, y, yaw):
    """Attached row houses from x0 to x1 along a facade line y; yaw 0 faces -Y, 180 faces +Y."""
    x = x0
    i = 0
    placed = []
    while x < x1:
        n = names[i % len(names)]
        w = HOUSE_W[n] * 100.0
        sc.add(n, xf(x + w / 2, y + R.uniform(-8, 8), 0, yaw + R.uniform(-0.6, 0.6)))
        placed.append((n, x + w / 2))
        x += w + R.uniform(2, 10)
        i += 1
    return placed


def build_ground(sc):
    for gx in range(-4000, 7001, 2000):
        for gy in range(-4000, 5001, 2000):
            sc.add("Ground_Tile_20m", xf(gx, gy, -2), mats=("MI_Dirt",))


def build_lane(sc, props):
    # the lane: left row (+Y) facing -Y, right row (-Y) facing +Y
    left = row(sc, LEFT_ORDER, LANE_X0, LANE_X1, HALF, 0.0)
    right = row(sc, RIGHT_ORDER, LANE_X0, LANE_X1, -HALF, 180.0)
    # around the square: left / right blocks set back, the end house facing down the lane (-X)
    row(sc, LEFT_ORDER[3:] + LEFT_ORDER[:3], SQ_X0 - 100, SQ_X1 + 300, SQ_Y1, 0.0)
    row(sc, RIGHT_ORDER[4:] + RIGHT_ORDER[:4], SQ_X0 + 200, SQ_X1 + 300, SQ_Y0, 180.0)
    sc.add("Trial_House_09", xf(SQ_X1 + 200, 150, 0, -90))
    sc.add("Trial_House_04", xf(SQ_X1 + 200, -310, 0, -90))
    sc.add("Trial_House_06", xf(SQ_X1 + 200, 640, 0, -90))
    # behind: a brick two-storey over the right row, taller tenements and trees in the distance
    sc.add("Shanty_2F_04", xf(1350, -760, 0, 180))
    sc.add("Shanty_2F_01", xf(2300, -820, 0, 180))
    sc.add("Tenement_3F_02", xf(SQ_X1 + 1400, 300, 0, -90))
    sc.add("Tenement_3F_05", xf(1800, 1500, 0, 0))
    for (x, y, s) in ((3300, 2300, 1.3), (1600, 1900, 1.1), (5200, -900, 1.4), (4400, 2600, 1.2), (-300, 1900, 1.0), (600, -1700, 1.2)):
        props.append(("PH_island_tree_02", x, y, 0, R.uniform(0, 360), s))
    # laundry high across the lane and the square
    # (the shot has one big line close overhead and one further down the lane)
    for (x, n, yaw) in ((560, "Trial_Laundry_Cross_01", 92), (1850, "Trial_Laundry_Cross_03", 95), (-600, "Trial_Laundry_Cross_02", 90)):
        props.append((n, x, 0, 0, yaw, 1.0))
    props.append(("Trial_Laundry_Cross_03", 3700, 1250, 0, 0, 1.0))      # across the end-house front
    # clothes along the walls (left near, right near) where the eave has none
    props.append(("Trial_Laundry_Wall_02", 230, HALF - 6, 0, 0, 1.0))
    props.append(("Trial_Laundry_Wall_01", 980, -HALF + 6, 0, 180, 1.0))
    props.append(("Trial_Laundry_Wall_03", 1700, HALF - 6, 0, 0, 1.0))
    # street furniture from the shot
    props.append(("Drum_Blue", 760, HALF - 75, 22, 0, 1.0))
    props.append(("BicycleIndian", 1650, -HALF + 70, 0, 4, 1.0))
    props.append(("Trial_Slippers", 1180, -HALF + 55, 22, 30, 1.0))
    props.append(("Trial_Slippers", 300, HALF - 60, 24, -20, 1.0))
    props.append(("LPG_Cylinder", 2350, HALF - 60, 22, 0, 1.0))
    props.append(("Matka_Stack", -700, -HALF + 90, 20, 0, 0.6))
    props.append(("Drum_Blue", 3000, SQ_Y1 - 60, 0, 0, 1.0))
    props.append(("Plastic_Stool", 2100, -HALF + 55, 22, 15, 1.0))
    # weeds at the wall base and a little dust / litter
    for i in range(40):
        side = R.choice([-1, 1])
        props.append((R.choice(["PH_grass_medium_01", "PH_grass_bermuda_01", "PH_grass_medium_02"]), R.uniform(-800, 2800),
                      side * R.uniform(120, 150), 0, R.uniform(0, 360), R.uniform(0.4, 0.8)))
    for i in range(25):
        props.append((R.choice(["Litter_Patch_0", "Litter_Patch_1", "Litter_Patch_2", "Litter_Patch_3"]), R.uniform(-600, 4200),
                      R.uniform(-140, 140) if R.random() < 0.6 else R.uniform(SQ_Y0 + 100, SQ_Y1 - 100), 1, R.uniform(0, 360), R.uniform(0.35, 0.6)))


def build_trial_lighting():
    build_lighting()
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight):
            # morning sun ahead-right of the player: shadows fall back towards the camera on the left
            a.set_actor_rotation(unreal.Rotator(roll=0, pitch=-40, yaw=145), False)
            lc = a.get_component_by_class(unreal.DirectionalLightComponent)
            lc.set_editor_property("intensity", 10.5)
            lc.set_editor_property("temperature", 5700.0)
        elif isinstance(a, unreal.ExponentialHeightFog):
            fc = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
            fc.set_editor_property("fog_density", 0.012)
            fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.55, 0.6, 0.66, 1))
            fc.set_editor_property("start_distance", 2500.0)


def build_gameplay():
    spawn(unreal.PlayerStart, PLAYER_START, unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0), label="PlayerStart")
    prof = spawn(unreal.GILevelProfile, unreal.Vector(0, 0, 0), label="LevelProfile")
    for name in ("SK_PlayerDhoti",):
        pm = load(f"/Game/Characters/{name}/{name}")
        if pm:
            prof.set_editor_property("player_mesh", pm)
            log("trial player mesh", name)
            break
    prof.set_editor_property("arm_length", 270.0)
    prof.set_editor_property("socket_offset", unreal.Vector(0, 8, 26))
    prof.set_editor_property("field_of_view", 75.0)
    prof.set_editor_property("start_pitch", -5.0)
    prof.set_editor_property("walk_speed", 150.0)
    prof.set_editor_property("hide_bag", True)

    woman = load("/Game/Characters/SK_WomanSaree/SK_WomanSaree")
    if woman:
        w = spawn(unreal.GIScriptedWalker, unreal.Vector(1700, 85, 0), unreal.Rotator(0, 180, 0), label="SareeWoman")
        w.set_editor_property("mesh", woman)
        w.set_editor_property("end_point", unreal.Vector(-500, 95, 0))
        w.set_editor_property("speed", 100.0)
        w.set_editor_property("start_alpha", 0.45)
        w.set_editor_property("pause_at_ends", 5.0)

    kids = [load(f"/Game/Characters/{n}/{n}") for n in ("SK_KidGreen", "SK_KidOrange", "SK_KidTeal", "SK_KidWhite", "SK_KidBare")]
    kids = [k for k in kids if k]
    if not kids:
        kids = [m for m in (load(f"/Game/Characters/{n}/{n}") for n in ("SK_Teen", "SK_BoyKurta")) if m]
    log("trial kids", [k.get_name() for k in kids])
    g = spawn(unreal.GICricketGame, unreal.Vector(3350, -420, 0), unreal.Rotator(0, 90, 0), label="Cricket")
    g.set_editor_property("kid_meshes", kids)
    for prop, n in (("stumps_mesh", "Cricket_Stumps"), ("bat_mesh", "Cricket_Bat"), ("ball_mesh", "Cricket_Ball")):
        m = mesh(n)
        if m:
            g.set_editor_property(prop, m)
    g.set_editor_property("pitch_length", 900.0)
    g.set_editor_property("lane_half_width", 520.0)
    g.set_editor_property("num_fielders", 3)

    mission = spawn(unreal.GIMission, unreal.Vector(0, 0, 0), label="Mission")
    objs = []
    for text, done, kind, loc, radius in (
            ("Gali ke aakhir tak chalo - bachche cricket khel rahe hain.", "Dharavi ki gali!", unreal.GIObjectiveKind.REACH,
             unreal.Vector(2700, 0, 0), 350),
            ("Ball tumhari taraf aaye to wapas phenko (E).", "Bachche khush!", unreal.GIObjectiveKind.RETURN_BALL,
             unreal.Vector(3350, 0, 0), 300)):
        o = unreal.GIObjective()
        o.set_editor_property("text", text)
        o.set_editor_property("done_banner", done)
        o.set_editor_property("kind", kind)
        o.set_editor_property("location", loc)
        o.set_editor_property("radius", float(radius))
        objs.append(o)
    mission.set_editor_property("tour_title", "Trial: [Ek Gali, Dharavi]")
    mission.set_editor_property("objectives", objs)
    mission.set_editor_property("title_cam_start", unreal.Vector(-300, -20, 160))
    mission.set_editor_property("title_cam_end", unreal.Vector(300, -20, 170))
    mission.set_editor_property("title_cam_look_at", unreal.Vector(2500, 0, 150))


def place(sc, props):
    for (name, x, y, z, yaw, s) in props:
        if not mesh(name):
            continue
        cull = 9000.0 if name.startswith(("PH_grass", "Litter_", "Trial_Slippers")) else 0.0
        collision = not name.startswith(("Trial_Laundry", "PH_grass", "Litter_"))
        roll = 7.0 if name == "BicycleIndian" else 0.0   # leaning on the wall
        sc.add(name, xf(x, y, z, yaw, s, roll=roll), collision=collision, cull=cull, shadow=not name.startswith(("Litter_",)))


def main():
    set_legacy_fbx(True)
    if eal.does_asset_exist(MAP):
        les.load_level(MAP)
        for a in eas.get_all_level_actors():
            if isinstance(a, (unreal.WorldSettings, unreal.Brush)):
                continue
            eas.destroy_actor(a)
    else:
        ensure_dir("/Game/Maps")
        les.new_level(MAP)
    ground, houses, props_sc = Scatter("Ground"), Scatter("Houses"), Scatter("Props")
    props = []
    build_ground(ground)
    build_lane(houses, props)
    for sc in (ground, houses):
        sc.spawn()
    build_trial_lighting()
    build_gameplay()
    place(props_sc, props)
    props_sc.spawn()
    les.save_current_level()
    log("level saved", MAP)


main()
