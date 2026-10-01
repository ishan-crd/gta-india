"""Build /Game/Maps/Varanasi: ghats, riverfront, railway + dusty road, town, east bank fort,
lighting/atmosphere and gameplay actors. Deterministic (seeded).

Coordinates in UE cm. See SPEC.md for the layout. Kit pivots / orientation: kit_manifest.json.
"""
import math
import os
import random
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

MAP = "/Game/Maps/Varanasi"
KIT = f"{ROOT}/Kit"
PROPS = f"{ROOT}/Props"
MI = f"{ROOT}/Materials/Instances"

R = random.Random(20261001)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

# ------------------------------------------------------------------------------------------
# Layout constants (cm)
GHAT_X0, GHAT_X1 = -50000, 50000
TOP_Z = 1200                 # top of the ghats / city ground
GHAT_DEPTH = 4000            # ghat steps span Y 0..4000
PROMENADE_Y = 4500           # riverfront facades
RAIL_Y = 10500
ROAD_Y = 12500
TOWN_ROWS = [(14300, 0.0), (19800, 180.0), (21600, 0.0), (27200, 180.0)]  # (facade Y, yaw); yaw 180 faces +Y
EAST_EDGE_Y = -15000
FORT_X0, FORT_X1 = -12000, 12000
NAMED_GHATS = {0: "DASHASHWAMEDH GHAT", -25000: "MANIKARNIKA GHAT", 30000: "ASSI GHAT", -12000: "MAN MANDIR GHAT", 14000: "DARBHANGA GHAT"}
PICKUP = unreal.Vector(-12000, 13650, TOP_Z)
# Cross streets from the road to the ghats: building rows must leave these corridors open.
CROSS_STREETS = (-25000, -12000, 0, 14000, 30000)
CORRIDOR_HALF = 500


def blocks_corridor(x0, x1):
    return any(x0 < cx + CORRIDOR_HALF and x1 > cx - CORRIDOR_HALF for cx in CROSS_STREETS)
PLAYER_START = unreal.Vector(-13600, 13050, TOP_Z + 110)
BIKE_POS = unreal.Vector(-13000, 12750, TOP_Z + 70)

MESHES = {}


def mesh(name):
    if name in MESHES:
        return MESHES[name]
    m = load(f"{KIT}/SM_{name}") or load(f"{PROPS}/{name}/SM_{name}") or load(f"{ROOT}/Detail/SM_{name}")
    if not m:
        warn("missing mesh", name)
    MESHES[name] = m
    return m


def size_of(name):
    m = mesh(name)
    if not m:
        return unreal.Vector(0, 0, 0)
    b = m.get_bounding_box()
    return b.max - b.min


SIGN_SLOT = {}


def sign_mats(name):
    """Material override tuple that puts a random shop sign on the mesh's M_Signboard slot."""
    if name not in SIGN_SLOT:
        idx = -1
        m = mesh(name)
        if m:
            for i, sm in enumerate(m.get_editor_property("static_materials")):
                if str(sm.get_editor_property("material_slot_name")).startswith("M_Signboard"):
                    idx = i
        SIGN_SLOT[name] = idx
    idx = SIGN_SLOT[name]
    if idx < 0:
        return None
    return tuple([""] * idx + ["MI_Sign_%02d" % R.randint(0, 11)])


def xf(x, y, z, yaw=0.0, s=1.0, pitch=0.0, roll=0.0):
    return unreal.Transform(location=unreal.Vector(x, y, z), rotation=unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw),
                            scale=unreal.Vector(s, s, s))


class Scatter:
    """Collects transforms per mesh, then spawns one AGIScatter actor."""

    def __init__(self, label):
        self.label = label
        self.items = {}

    def add(self, name, t, collision=True, cull=0.0, shadow=True, mats=None):
        key = (name, collision, cull, shadow, tuple(mats or ()))
        self.items.setdefault(key, []).append(t)

    def spawn(self):
        actor = eas.spawn_actor_from_class(unreal.GIScatter, unreal.Vector(0, 0, 0))
        actor.set_actor_label(self.label)
        items = []
        for (name, collision, cull, shadow, mats), ts in self.items.items():
            m = mesh(name)
            if not m:
                continue
            it = unreal.GIScatterItem()
            if mats:
                it.set_editor_property("materials", [load(f"{MI}/{x}") if x else None for x in mats])
            it.set_editor_property("mesh", m)
            it.set_editor_property("transforms", ts)
            it.set_editor_property("collision", collision)
            it.set_editor_property("cull_distance", cull)
            it.set_editor_property("cast_shadow", shadow)
            items.append(it)
        actor.set_editor_property("items", items)
        actor.build_instances()
        log("scatter", self.label, sum(len(v) for v in self.items.values()), "instances")
        return actor


def spawn(cls, loc, rot=None, label=None):
    a = eas.spawn_actor_from_class(cls, loc, rot or unreal.Rotator(0, 0, 0))
    if label:
        a.set_actor_label(label)
    return a


def trace_z(x, y, z_from=6000.0, z_to=-2000.0, default=None):
    world = ues.get_editor_world()
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z_from), unreal.Vector(x, y, z_to),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    if hit:
        # HitResult tuple / struct differences across versions
        try:
            return hit.to_tuple()[4].z  # impact_point
        except Exception:
            try:
                return hit.get_editor_property("impact_point").z
            except Exception:
                pass
    return default


def ghat_z(y):
    """Analytic fallback for the step surface height at depth y (0..4000)."""
    return -300.0 + max(0.0, min(1.0, y / GHAT_DEPTH)) * 1500.0


# ------------------------------------------------------------------------------------------
def build_ghats(sc, props, spots, lanes):
    x = GHAT_X0
    i = 0
    while x < GHAT_X1:
        cx = x + 1000
        near_named = any(abs(cx - gx) < 1500 for gx in NAMED_GHATS)
        name = "GhatSteps_Platform_20m" if (near_named or i % 5 == 2) else "GhatSteps_Straight_20m"
        sc.add(name, xf(cx, 0, 0))
        x += 2000
        i += 1
    for ex, yaw in ((GHAT_X0 - 90, 0), (GHAT_X1 + 90, 0)):
        sc.add("GhatSteps_SideWall", xf(ex, 0, 0, yaw))

    # Chhatri umbrellas, temples on the steps, railings, platforms (chowkis).
    for gx in range(GHAT_X0 + 500, GHAT_X1, 700):
        dense = math.exp(-((gx / 9000.0) ** 2)) + 0.35
        if R.random() < 0.55 * dense:
            y = R.uniform(1200, 3600)
            props.append(("Chhatri_Umbrella", gx + R.uniform(-250, 250), y, None, R.uniform(0, 360), R.uniform(0.9, 1.1)))
        if R.random() < 0.25 * dense:
            y = R.uniform(900, 3200)
            props.append(("Chowki_Platform", gx + R.uniform(-250, 250), y, None, R.choice([0, 90, 180]), 1.0))
    for tx in (-33000, -18000, -6000, 8000, 22000, 38000):
        props.append(("Temple_Riverside", tx, 2200, None, 0, 1.0))
    for tx in range(GHAT_X0 + 3000, GHAT_X1, 9000):
        props.append(("Temple_Small", tx + R.uniform(-800, 800), 3700, None, 0, 1.0))
    for fx in range(GHAT_X0 + 1500, GHAT_X1, 2600):
        if R.random() < 0.5:
            props.append(("Flag_Pole_Saffron", fx, R.uniform(2500, 3800), None, 0, 1.0))

    # Crowd: lanes along the steps (more around Dashashwamedh), sitters, bathers, pray-ers.
    for gx in range(GHAT_X0 + 2000, GHAT_X1 - 2000, 6000):
        w = 0.6 + 3.5 * math.exp(-((gx / 9000.0) ** 2))
        for y in (700, 1500, 2400, 3300):
            lanes.append({"start": (gx - 3000, y, ghat_z(y)), "end": (gx + 3000, y, ghat_z(y)), "width": 350, "weight": w})
        lanes.append({"start": (gx - 3000, 4250, TOP_Z), "end": (gx + 3000, 4250, TOP_Z), "width": 300, "weight": w * 1.2})
    for n in range(900):
        gx = R.gauss(0, 12000) if R.random() < 0.6 else R.uniform(GHAT_X0, GHAT_X1)
        gx = max(GHAT_X0 + 300, min(GHAT_X1 - 300, gx))
        pr = math.exp(-((gx / 7000.0) ** 2))
        kind = R.random()
        if kind < 0.4:
            y = R.uniform(800, 3800)
            spots.append({"loc": (gx, y, ghat_z(y)), "yaw": -90 + R.uniform(-40, 40), "mode": R.choice(["Sit", "SitTalk", "SitTalk"]),
                          "priority": pr + R.random() * 0.3})
        elif kind < 0.62:
            y = R.uniform(-1100, -150)
            mode = R.choice(["Tread", "Tread", "Locomotion", "Locomotion", "Wash"])
            z = -150.0 if mode == "Tread" else -108.0
            spots.append({"loc": (gx, y, z), "yaw": -90 + R.uniform(-60, 60), "mode": mode, "priority": pr + 0.2, "fixed": True})
        elif kind < 0.7:
            y = R.uniform(150, 450)                       # washing clothes on the lowest steps
            spots.append({"loc": (gx, y, ghat_z(y)), "yaw": -90 + R.uniform(-20, 20), "mode": "Wash", "priority": pr + 0.1})
        else:
            y = R.uniform(300, 3800)
            spots.append({"loc": (gx, y, ghat_z(y)), "yaw": R.uniform(-180, 180), "mode": R.choice(["Locomotion", "Talk", "Talk"]), "priority": pr})


def build_boats(props, spots):
    boat_names = ["Boat_Wooden_Varanasi", "Boat_Wooden_Varanasi", "Boat_Wooden_Varanasi", "BoatWooden", "BoatOld"]
    for bx in range(GHAT_X0, GHAT_X1, 900):
        if R.random() < 0.55:
            name = R.choice(boat_names)
            y = R.uniform(-2600, -300)
            yaw = 90 + R.uniform(-25, 25) if y > -1500 else R.uniform(-20, 20)
            props.append((name, bx + R.uniform(-300, 300), y, -35.0, yaw, 1.0))
            if R.random() < 0.35:
                spots.append({"loc": (bx, y, 10.0), "yaw": yaw, "mode": "Sit", "priority": 0.3, "fixed": True})


def build_riverfront(sc, props):
    widths = {}
    for i in range(1, 15):
        n = f"Bldg_Riverfront_{i:02d}"
        widths[n] = size_of(n).x or 1200.0
    palaces = {-18500: "Palace_ChetSingh", 19500: "Palace_Darbhanga", -36000: "Palace_Darbhanga", 24500: "Palace_ChetSingh"}
    x = GHAT_X0 + 200
    while x < GHAT_X1 - 600:
        pal = next((p for px, p in palaces.items() if abs(x - px) < 1200), None)
        if pal and blocks_corridor(x, x + (size_of(pal).x or 3000.0)):
            pal = None
        if pal:
            w = size_of(pal).x or 3000.0
            sc.add(pal, xf(x + w / 2, PROMENADE_Y, TOP_Z))
            x += w + R.uniform(200, 500)
            continue
        n = R.choice(list(widths))
        w = widths[n]
        if blocks_corridor(x, x + w):
            x += 250
            continue
        y = PROMENADE_Y + R.uniform(-150, 350)
        sc.add(n, xf(x + w / 2, y, TOP_Z))
        if R.random() < 0.3:
            props.append(("Water_Tank_Rooftop", x + w / 2 + R.uniform(-300, 300), y + 600, None, 0, 1.0))
        x += w + (R.uniform(350, 700) if R.random() < 0.18 else R.uniform(0, 60))
    # Second row behind (backs to the river row, facing the railway)
    x = GHAT_X0
    while x < GHAT_X1:
        n = f"Bldg_Town_{R.randint(1, 8):02d}"
        w = size_of(n).x or 800.0
        if blocks_corridor(x, x + w):
            x += 250
            continue
        sc.add(n, xf(x + w / 2, 9100, TOP_Z, 180), mats=sign_mats(n))
        x += w + (R.uniform(400, 900) if R.random() < 0.2 else R.uniform(0, 80))


def build_ground(sc):
    # City ground from the promenade to the far town, plus a corridor for the railway.
    for gx in range(-92000, 92001, 2000):
        in_city = GHAT_X0 - 4000 <= gx <= GHAT_X1 + 4000
        for gy in range(5000, 31001, 2000):
            sc.add("Ground_Tile_20m", xf(gx, gy, TOP_Z - 2), cull=0)
        if in_city:
            sc.add("Ground_Tile_20m", xf(gx, 4400, TOP_Z - 2))
    # East bank sand, leaving room for the fort ghat.
    for gx in range(-90000, 90001, 5000):
        for gy in range(-17500, -60001, -5000):
            if FORT_X0 - 2500 < gx < FORT_X1 + 2500 and gy > -21000:
                continue
            z = -60.0 if gy == -17500 else R.uniform(0, 80)
            sc.add("Sandbank_Tile_50m", xf(gx, gy, z, R.choice([0, 90, 180, 270])))
    # Fort plateau behind the east ghat.
    for gx in range(FORT_X0 - 2000, FORT_X1 + 2001, 2000):
        for gy in range(-19600, -40001, -2000):
            sc.add("Ground_Tile_20m", xf(gx, gy, 1000 - 2))


def build_rail_and_road(sc, props):
    for gx in range(-90000, 90001, 2000):
        sc.add("Rail_Track_20m", xf(gx, RAIL_Y, TOP_Z - 75))
    for gx in range(GHAT_X0 - 4000, GHAT_X1 + 4001, 2000):
        sc.add("Road_Dusty_20m", xf(gx, ROAD_Y, TOP_Z + 2))
    # Cross streets from the road to the promenade through gaps.
    for gx in (-25000, -12000, 0, 14000, 30000):
        for gy in range(6000, 12000, 2000):
            sc.add("Road_Dusty_20m", xf(gx, gy + 1000, TOP_Z + 1, 90))
    for gx in range(GHAT_X0, GHAT_X1, 3500):
        props.append(("Electric_Pole", gx, 13550, TOP_Z, 0, 1.0))
    for n in range(14):
        props.append((R.choice(["AutoRickshaw", "AutoRickshaw2"]), R.uniform(GHAT_X0, GHAT_X1), R.choice([11850, 13200]), TOP_Z + 5,
                      R.choice([0, 180]) + R.uniform(-8, 8), 1.0))
    for n in range(26):
        props.append((R.choice(["Zebu", "Zebu", "Buffalo"]), R.uniform(GHAT_X0, GHAT_X1), R.choice([R.uniform(11800, 13300), R.uniform(4150, 4400)]),
                      None, R.uniform(0, 360), 1.0))


def build_town(sc, props, lanes):
    for row, (fy, yaw) in enumerate(TOWN_ROWS):
        x = GHAT_X0 - 3000
        while x < GHAT_X1 + 3000:
            if abs(x - PICKUP.x) < 700 and row == 0:
                x += 1400  # the dhaba goes here
                continue
            n = f"Bldg_Town_{R.randint(1, 8):02d}"
            w = size_of(n).x or 800.0
            sc.add(n, xf(x + w / 2, fy, TOP_Z, yaw), mats=sign_mats(n))
            gap = R.uniform(500, 900) if R.random() < 0.12 else R.uniform(0, 50)
            x += w + gap
        # Street lane in front of this row
        sy = fy - 700 if yaw == 0 else fy + 700
        for gx in range(GHAT_X0, GHAT_X1, 8000):
            lanes.append({"start": (gx, sy, TOP_Z), "end": (gx + 8000, sy, TOP_Z), "width": 400, "weight": 0.6})
    # Outskirts beyond both ends of the ghats: rows of low town buildings along the railway.
    for side in (-1, 1):
        x = GHAT_X1 + 3000 if side > 0 else GHAT_X0 - 3000
        while abs(x) < 66000:
            n = f"Bldg_Town_{R.randint(1, 8):02d}"
            w = size_of(n).x or 800.0
            sc.add(n, xf(x + side * w / 2, 14300, TOP_Z, 0), mats=sign_mats(n))
            sc.add(n, xf(x + side * w / 2, 8200, TOP_Z, 180), mats=sign_mats(n))
            x += side * (w + R.uniform(0, 400))
    # Streets between rows (paved as road)
    for sy in (20700, 24400):
        for gx in range(GHAT_X0 - 2000, GHAT_X1 + 2001, 2000):
            sc.add("Road_Dusty_20m", xf(gx, sy, TOP_Z + 1))
    # Road-side lanes
    for gx in range(GHAT_X0, GHAT_X1, 8000):
        lanes.append({"start": (gx, 11900, TOP_Z), "end": (gx + 8000, 11900, TOP_Z), "width": 250, "weight": 0.5})
        lanes.append({"start": (gx, 13300, TOP_Z), "end": (gx + 8000, 13300, TOP_Z), "width": 300, "weight": 0.9})
    # Temples and trees in town
    props.append(("HinduTemple", 8000, 17200, TOP_Z, 0, 1.0))
    props.append(("Temple_Medium", -30000, 17000, TOP_Z, 0, 1.0))
    props.append(("TemplesSet", 26000, 17200, TOP_Z, 0, 1.0))
    for n in range(40):
        props.append((R.choice(["PH_island_tree_01", "BananaTree", "BananaTree"]), R.uniform(GHAT_X0, GHAT_X1), R.uniform(16500, 18500), TOP_Z,
                      R.uniform(0, 360), R.uniform(0.8, 1.2)))


def build_dhaba(props):
    # "Sharma Bhojnalaya": kirana shop + bhelpuri cart + chai stall at the pickup point.
    props.append(("KiranaShop", PICKUP.x, PICKUP.y + 450, TOP_Z, 180, 1.4))
    props.append(("BhelpuriShop", PICKUP.x + 450, PICKUP.y + 50, TOP_Z, 0, 1.0))
    props.append(("ChaiBench", PICKUP.x - 380, PICKUP.y + 80, TOP_Z, 0, 1.0))
    props.append(("TeaBoiler", PICKUP.x - 380, PICKUP.y + 350, TOP_Z + 80, 0, 1.0))
    for i in range(4):
        props.append(("PH_plastic_monobloc_chair_01", PICKUP.x - 700 + i * 90, PICKUP.y - 80, TOP_Z, R.uniform(0, 360), 1.0))


def build_east_bank(sc, props, spots, lanes):
    x = FORT_X0
    while x < FORT_X1:
        sc.add("GhatStepsSmall_10m", xf(x + 500, EAST_EDGE_Y, 0, 180))
        x += 1000
    sc.add("GhatSteps_SideWall", xf(FORT_X0 - 90, EAST_EDGE_Y, 0, 180))
    sc.add("GhatSteps_SideWall", xf(FORT_X1 + 90, EAST_EDGE_Y, 0, 180))
    wall_y = EAST_EDGE_Y - 4300
    for wx in range(FORT_X0 + 1000, FORT_X1 - 999, 2000):
        if abs(wx) < 1500:
            continue
        sc.add("Fort_Wall_20m", xf(wx, wall_y, 1000, 180))
    sc.add("Fort_Gate", xf(0, wall_y, 1000, 180))
    for tx in (FORT_X0 + 200, FORT_X1 - 200, -2600, 2600):
        sc.add("Fort_Tower", xf(tx, wall_y - 400, 1000, 180))
    for i in range(6):
        props.append(("Chhatri_Umbrella", R.uniform(FORT_X0 + 500, FORT_X1 - 500), R.uniform(-16200, -18200), None, R.uniform(0, 360), 1.0))
    lanes.append({"start": (FORT_X0, -18900, 1000), "end": (FORT_X1, -18900, 1000), "width": 300, "weight": 1.2})
    lanes.append({"start": (-30000, -20000, 60), "end": (30000, -20000, 60), "width": 800, "weight": 0.6})
    for n in range(40):
        y = R.uniform(-16000, -18800)
        gx = R.uniform(FORT_X0 + 300, FORT_X1 - 300)
        spots.append({"loc": (gx, y, 0), "yaw": 90 + R.uniform(-40, 40), "mode": R.choice(["Sit", "SitTalk", "Talk"]), "priority": 0.6})
    for n in range(12):
        props.append((R.choice(["Zebu", "Buffalo"]), R.uniform(-40000, 40000), R.uniform(-17000, -30000), None, R.uniform(0, 360), 1.0))
    for n in range(18):
        props.append(("BoatOld", R.uniform(-40000, 40000), R.uniform(-15800, -16800), -20.0, R.uniform(0, 360), 1.0))


# weighted: mostly flowers / leaf bowls / small plastic, few rags (the reference is offerings + plastic)
DEBRIS = (["Debris_Marigolds_A"] * 5 + ["Debris_Marigolds_B"] * 3 + ["Debris_LeafBowl"] * 4 + ["Debris_Bottle"] * 3 +
          ["Debris_Bag_0", "Debris_Bag_1", "Debris_Bag_2"] * 2 + ["Debris_Foam_0", "Debris_Foam_1"] * 2 + ["Debris_Rag_0"])


def build_debris(sc):
    """Floating garbage and offerings piled at the ghats' waterline (as in the reference), thinning out
    across the river."""
    def drop(x, y):
        name = R.choice(DEBRIS)
        z = 1.0 if "Foam" in name else 2.0
        s = R.uniform(0.45, 0.8) if ("Bag" in name or "Rag" in name) else R.uniform(0.8, 1.4)
        sc.add(name, xf(x, y, z, R.uniform(0, 360), s), collision=False, cull=9000.0, shadow=False)
    for i in range(5200):
        x = R.gauss(0, 14000) if R.random() < 0.7 else R.uniform(GHAT_X0, GHAT_X1)
        if not (GHAT_X0 < x < GHAT_X1):
            continue
        y = -abs(R.gauss(0, 380)) - 40.0          # hugging the bottom steps
        drop(x, y)
    for i in range(1800):                          # drifting mid-river
        drop(R.uniform(-30000, 30000), R.uniform(-14000, -500))
    for i in range(1200):                          # piled at the far (east) ghat too
        drop(R.uniform(FORT_X0, FORT_X1), EAST_EDGE_Y + abs(R.gauss(0, 350)) + 40.0)


def build_wires(sc):
    """Sagging electric wires between the roadside poles, plus tangles running to the shops."""
    for gx in range(GHAT_X0, GHAT_X1 - 3500, 3500):
        sc.add("Wires_Span_35m", xf(gx + 1750, 13550, TOP_Z), collision=False, cull=12000.0)
        if R.random() < 0.6:
            sc.add("Wires_Tangle", xf(gx, 13550, TOP_Z), collision=False, cull=8000.0)


def build_grass(sc):
    """Grass field beside the railway (the reference shows green grass along the track) + clumps."""
    for gx in range(GHAT_X0 - 20000, GHAT_X1 + 20001, 2000):
        for gy in (9700, 11300):
            sc.add("Ground_Tile_20m", xf(gx, gy, TOP_Z + 1), mats=("MI_Grass",))
    for i in range(9000):
        x = R.uniform(GHAT_X0 - 20000, GHAT_X1 + 20000)
        y = R.choice([R.uniform(8900, 10150), R.uniform(10850, 12000)])
        name = R.choice(["PH_grass_medium_01", "PH_grass_medium_02", "PH_grass_bermuda_01", "PH_grass_medium_02", "PH_fern_02"])
        sc.add(name, xf(x, y, TOP_Z + 1, R.uniform(0, 360), R.uniform(0.8, 1.5)), collision=False, cull=7000.0, shadow=False)
    for i in range(70):
        x = R.uniform(GHAT_X0 - 15000, GHAT_X1 + 15000)
        y = R.choice([R.uniform(9000, 9900), R.uniform(11200, 11900), R.uniform(16500, 18500)])
        sc.add(R.choice(["PH_island_tree_01", "PH_island_tree_01", "BananaTree", "PH_shrub_02"]), xf(x, y, TOP_Z, R.uniform(0, 360), R.uniform(0.9, 1.6)),
               collision=False, cull=25000.0)


def build_dust(lanes_unused=None):
    """Warm dust haze over the road (local fog volumes)."""
    try:
        for gx in range(GHAT_X0, GHAT_X1, 12000):
            a = spawn(unreal.LocalFogVolume, unreal.Vector(gx, ROAD_Y, TOP_Z + 150), label="RoadDust")
            a.set_actor_scale3d(unreal.Vector(70, 12, 3))
            c = a.get_component_by_class(unreal.LocalFogVolumeComponent)
            for prop, val in (("radial_fog_extinction", 0.25), ("height_fog_extinction", 0.3), ("height_fog_falloff", 1200.0),
                              ("fog_albedo", unreal.LinearColor(0.85, 0.7, 0.5, 1))):
                try:
                    c.set_editor_property(prop, val)
                except Exception as e:
                    warn("fog prop", prop, e)
    except Exception as e:
        warn("local fog volumes unavailable", e)


def place_props(sc, props):
    for (name, x, y, z, yaw, s) in props:
        if z is None:
            z = trace_z(x, y)
            if z is None:
                z = ghat_z(y) if 0 <= y <= GHAT_DEPTH else TOP_Z
        cull = 0.0
        if name.startswith("PH_") or name in ("Chowki_Platform", "TeaBoiler", "ChaiBench"):
            cull = 15000.0
        collision = name not in ("Flag_Pole_Saffron",)
        sc.add(name, xf(x, y, z, yaw, s), collision=collision, cull=cull)


def text_sign(text, loc, yaw, size=120.0, color=(1.0, 0.85, 0.3)):
    a = spawn(unreal.TextRenderActor, loc, unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw), label="Sign_" + text[:20])
    c = a.get_editor_property("text_render")
    c.set_editor_property("text", text)
    c.set_editor_property("world_size", size)
    c.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
    c.set_editor_property("text_render_color", unreal.Color(int(color[2] * 255), int(color[1] * 255), int(color[0] * 255), 255))
    return a


def build_lighting():
    sun = spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 20000), unreal.Rotator(roll=0, pitch=-13, yaw=100), label="Sun")
    lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    lc.set_editor_property("intensity", 9.0)
    lc.set_editor_property("use_temperature", True)
    lc.set_editor_property("temperature", 4600.0)
    lc.set_editor_property("atmosphere_sun_light", True)
    lc.set_editor_property("cast_shadows", True)
    lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    for prop, val in (("enable_light_shaft_bloom", True), ("bloom_scale", 0.05), ("bloom_threshold", 0.6),
                      ("bloom_tint", unreal.Color(255, 205, 150, 255))):
        try:
            lc.set_editor_property(prop, val)
        except Exception as e:
            warn("sun prop", prop, e)
    try:
        lc.set_editor_property("light_source_angle", 1.2)
        lc.set_editor_property("cast_cloud_shadows", True)
    except Exception:
        pass

    spawn(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), label="SkyAtmosphere")
    sky = spawn(unreal.SkyLight, unreal.Vector(0, 0, 3000), label="SkyLight")
    sl = sky.get_component_by_class(unreal.SkyLightComponent)
    sl.set_editor_property("real_time_capture", True)
    sl.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sl.set_editor_property("intensity", 1.1)

    fog = spawn(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0), label="HeightFog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", 0.035)
    fc.set_editor_property("fog_height_falloff", 0.12)
    fc.set_editor_property("enable_volumetric_fog", True)
    fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.55, 0.42, 0.28, 1))
    fc.set_editor_property("directional_inscattering_luminance", unreal.LinearColor(1.0, 0.62, 0.3, 1))
    fc.set_editor_property("start_distance", 1500.0)
    try:
        fc.set_editor_property("volumetric_fog_scattering_distribution", 0.6)
        fc.set_editor_property("volumetric_fog_albedo", unreal.Color(235, 205, 170, 255))
        fc.set_editor_property("volumetric_fog_extinction_scale", 1.5)
    except Exception:
        pass

    try:
        spawn(unreal.VolumetricCloud, unreal.Vector(0, 0, 0), label="Clouds")
    except Exception:
        pass

    ppv = spawn(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), label="PostProcess")
    ppv.set_editor_property("unbound", True)
    s = ppv.get_editor_property("settings")
    def pp(name, value):
        try:
            s.set_editor_property("override_" + name, True)
            s.set_editor_property(name, value)
        except Exception as e:
            warn("pp", name, e)
    pp("auto_exposure_bias", 0.3)
    pp("bloom_intensity", 0.9)
    pp("white_temp", 5900.0)
    pp("color_saturation", unreal.Vector4(1.12, 1.08, 1.0, 1.0))
    pp("color_contrast", unreal.Vector4(1.06, 1.06, 1.06, 1.0))
    pp("color_gain_highlights", unreal.Vector4(1.06, 1.0, 0.9, 1.0))
    pp("color_gamma_shadows", unreal.Vector4(1.0, 0.98, 1.02, 1.0))
    pp("vignette_intensity", 0.35)
    pp("scene_fringe_intensity", 0.25)
    pp("local_exposure_highlight_contrast_scale", 0.8)
    pp("lumen_scene_lighting_quality", 1.0)
    pp("lumen_final_gather_quality", 1.0)
    ppv.set_editor_property("settings", s)


def build_gameplay(lanes, spots):
    river = spawn(unreal.GIRiver, unreal.Vector(0, -9000, 0), label="Ganga")
    river.set_editor_property("half_extent", unreal.Vector2D(95000, 11400))
    bed = spawn(unreal.StaticMeshActor, unreal.Vector(0, -8000, -600), label="RiverBed")
    smc = bed.get_editor_property("static_mesh_component")
    smc.set_editor_property("static_mesh", unreal.load_asset("/Engine/BasicShapes/Plane"))
    bed.set_actor_scale3d(unreal.Vector(1900, 260, 1))
    mi = load(f"{MI}/MI_Riverbed")
    if mi:
        smc.set_material(0, mi)

    start = spawn(unreal.PlayerStart, PLAYER_START, unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0), label="PlayerStart")
    spawn(unreal.GIBike, BIKE_POS, unreal.Rotator(0, 0, 0), label="Bike_Pulsar")
    spawn(unreal.GIBike, unreal.Vector(-11500, 12200, TOP_Z + 70), unreal.Rotator(roll=0.0, pitch=0.0, yaw=180.0), label="Bike_Pulsar2")

    train = spawn(unreal.GITrain, unreal.Vector(-30000, RAIL_Y, TOP_Z + 15), label="Train")
    train.set_editor_property("speed", 1100.0)
    train.set_editor_property("track_start_x", -62000.0)
    train.set_editor_property("track_end_x", 62000.0)

    traffic = spawn(unreal.GITraffic, unreal.Vector(0, 0, 0), label="Traffic")
    lanes_t = []
    for y, d, n in ((ROAD_Y - 230, 1.0, 9), (ROAD_Y + 230, -1.0, 9)):
        tl = unreal.GITrafficLane()
        tl.set_editor_property("y", float(y))
        tl.set_editor_property("z", float(TOP_Z + 4))
        tl.set_editor_property("direction", d)
        tl.set_editor_property("count", n)
        lanes_t.append(tl)
    traffic.set_editor_property("lanes", lanes_t)
    traffic.set_editor_property("vehicle_meshes", [m for m in (mesh("AutoRickshaw"), mesh("AutoRickshaw2"), mesh("BikePulsar135")) if m])

    mission = spawn(unreal.GIMission, unreal.Vector(0, 0, 0), label="Mission")
    ghat_z_at = trace_z(0, 700) or ghat_z(700)
    drop_z = trace_z(0, EAST_EDGE_Y - 3700) or 1000
    mission.set_editor_property("pickup_location", unreal.Vector(PICKUP.x, PICKUP.y, TOP_Z + 50))
    mission.set_editor_property("ghat_location", unreal.Vector(0, 700, ghat_z_at + 50))
    mission.set_editor_property("drop_location", unreal.Vector(0, EAST_EDGE_Y - 3700, drop_z + 50))
    mission.set_editor_property("far_bank_y", EAST_EDGE_Y - 300)
    mission.set_editor_property("title_cam_start", unreal.Vector(-9000, -6500, 900))
    mission.set_editor_property("title_cam_end", unreal.Vector(7000, -5200, 1600))
    mission.set_editor_property("title_cam_look_at", unreal.Vector(0, 3500, 1700))

    crowd = spawn(unreal.GICrowdManager, unreal.Vector(0, 0, 0), label="Crowd")
    lane_structs = []
    for l in lanes:
        w = unreal.GIWalkLane()
        w.set_editor_property("start", unreal.Vector(*l["start"]))
        w.set_editor_property("end", unreal.Vector(*l["end"]))
        w.set_editor_property("width", float(l["width"]))
        w.set_editor_property("weight", float(l["weight"]))
        lane_structs.append(w)
    crowd.set_editor_property("lanes", lane_structs)
    modes = {"Sit": unreal.GIPoseMode.SIT, "Locomotion": unreal.GIPoseMode.LOCOMOTION, "StandArmsOut": unreal.GIPoseMode.STAND_ARMS_OUT,
             "Wade": unreal.GIPoseMode.WADE, "Tread": unreal.GIPoseMode.TREAD, "SitTalk": unreal.GIPoseMode.SIT_TALK,
             "Wash": unreal.GIPoseMode.WASH, "Talk": unreal.GIPoseMode.TALK}
    spot_structs = []
    for s in spots:
        p = unreal.GIStaticSpot()
        p.set_editor_property("location", unreal.Vector(*s["loc"]))
        p.set_editor_property("yaw", float(s["yaw"]))
        p.set_editor_property("mode", modes[s["mode"]])
        p.set_editor_property("priority", float(s["priority"]))
        p.set_editor_property("fixed_z", bool(s.get("fixed", False)))
        spot_structs.append(p)
    crowd.set_editor_property("spots", spot_structs)
    log("crowd lanes", len(lane_structs), "spots", len(spot_structs))

    # Signs
    for gx, name in NAMED_GHATS.items():
        text_sign(name, unreal.Vector(gx, PROMENADE_Y - 160, TOP_Z + 650), -90, 110)
    text_sign("SHARMA BHOJNALAYA", unreal.Vector(PICKUP.x, PICKUP.y + 200, TOP_Z + 380), -90, 70, (1.0, 0.95, 0.9))
    text_sign("RAMNAGAR GHAT", unreal.Vector(0, EAST_EDGE_Y - 3900, 2400), 90, 140)


def main():
    set_legacy_fbx(True)
    if eal.does_asset_exist(MAP):
        # Rebuild in place: open the map and clear every actor we placed last time.
        les.load_level(MAP)
        for a in eas.get_all_level_actors():
            if isinstance(a, (unreal.WorldSettings, unreal.Brush)):
                continue
            eas.destroy_actor(a)
    else:
        ensure_dir("/Game/Maps")
        les.new_level(MAP)

    ground = Scatter("Ground")
    ghats = Scatter("Ghats")
    city = Scatter("Buildings")
    infra = Scatter("RailRoad")
    east = Scatter("EastBank")
    propsc = Scatter("Props")
    props, spots, lanes = [], [], []

    build_ground(ground)
    build_ghats(ghats, props, spots, lanes)
    build_riverfront(city, props)
    build_rail_and_road(infra, props)
    build_town(city, props, lanes)
    build_dhaba(props)
    build_east_bank(east, props, spots, lanes)
    build_boats(props, spots)

    detail = Scatter("RiverDetail")
    nature = Scatter("Nature")
    build_debris(detail)
    build_wires(infra)
    build_grass(nature)

    for sc in (ground, ghats, city, infra, east, detail, nature):
        sc.spawn()
    # Props need the ground/steps collision in place for traces.
    place_props(propsc, props)
    propsc.spawn()

    build_lighting()
    build_gameplay(lanes, spots)

    les.save_current_level()
    log("level saved", MAP)


main()
