"""Build /Game/Maps/Varanasi to match the reference clip's geography (cross-section, river -> inland):

  far bank (-Y): dense old-city ghats - steps, riverfront houses, palaces, temples, crowds
  Ganga        : ~150 m of murky water, boats, bathers, buffaloes, garbage everywhere
  near bank    : ghat steps -> sandstone parapet with domed kiosks -> littered strip -> RAILWAY (packed EMU)
                 -> verge -> dusty ROAD -> tin-shed stalls -> low village houses (3 rows) -> fields

Driving along +X the village is on the left and the train + river on the right, like the clip.
Deterministic (seeded). Coordinates in UE cm. Kit pivots / orientation: kit_manifest.json.
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
GHAT_X0, GHAT_X1 = -50000, 50000      # near (village-side) ghats
TOP_Z = 1200                          # top of the ghats / ground level on both banks
GHAT_DEPTH = 4000                     # ghat steps span 40 m from the water
PARAPET_Y = 4150
RAIL_Y = 5900
ROAD_Y = 7400                         # 8 m dirt road: 7000..7800
SHED_Y = 7950                         # tin-shed stalls on the village side of the road
POLE_Y = 8250
VILLAGE_ROWS = [(8700, 0.0), (11400, 0.0), (14100, 0.0)]    # (facade Y, yaw); facades face -Y (road / galis)
GALI_Y = (10700, 13400)               # lanes behind each row
FAR_EDGE_Y = -15000                   # water edge of the far (city) bank
FAR_X0, FAR_X1 = -40000, 40000
FAR_TOP_Y = FAR_EDGE_Y - GHAT_DEPTH   # -19000
FAR_ROW_Y = FAR_TOP_Y - 500           # riverfront facades, facing the river (+Y)
NAMED_GHATS = {0: "DASHASHWAMEDH GHAT", -14000: "MANIKARNIKA GHAT", 16000: "DARBHANGA GHAT", -28000: "SCINDIA GHAT", 30000: "ASSI GHAT"}
PICKUP = unreal.Vector(-12000, 8150, TOP_Z)
PLAYER_START = unreal.Vector(-13600, 7650, TOP_Z + 110)
BIKE_POS = unreal.Vector(-13000, 7300, TOP_Z + 70)
GHAT_ENTRY = unreal.Vector(-2000, 600, 0)        # where the mission points you into the water
DROP = unreal.Vector(0, FAR_TOP_Y - 250, TOP_Z)  # top of the far ghat
# Gaps in the far riverfront row so the drop point and the named ghats stay reachable.
FAR_STREETS = (-28000, -14000, 0, 16000, 30000)
CORRIDOR_HALF = 600


def blocks_corridor(x0, x1):
    return any(x0 < cx + CORRIDOR_HALF and x1 > cx - CORRIDOR_HALF for cx in FAR_STREETS)


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


def ghat_z(d):
    """Analytic fallback for the step surface height at depth d (0..4000 from the water)."""
    return -300.0 + max(0.0, min(1.0, d / GHAT_DEPTH)) * 1500.0


def bank_y(side, d):
    """World Y at depth d from the water on a bank: side +1 = near (village), -1 = far (city)."""
    return d if side > 0 else FAR_EDGE_Y - d


# ------------------------------------------------------------------------------------------
def build_ghat_bank(sc, props, spots, lanes, side, x0, x1, density_c=0.0, density_w=9000.0, temples=True):
    """One bank of ghat steps with umbrellas, chowkis, shrines, flags, and the crowd (sitters, bathers,
    washers, walkers). side +1 = near bank (steps rise to +Y), -1 = far bank (rotated 180)."""
    yaw = 0 if side > 0 else 180
    face = -90 if side > 0 else 90          # facing the river
    edge = 0 if side > 0 else FAR_EDGE_Y
    x = x0
    i = 0
    while x < x1:
        cx = x + 1000
        near_named = any(abs(cx - gx) < 1500 for gx in NAMED_GHATS) if side < 0 else False
        name = "GhatSteps_Platform_20m" if (near_named or i % 5 == 2) else "GhatSteps_Straight_20m"
        sc.add(name, xf(cx, edge, 0, yaw))
        x += 2000
        i += 1
    for ex in (x0 - 90, x1 + 90):
        sc.add("GhatSteps_SideWall", xf(ex, edge, 0, yaw))

    def dens(gx):
        return math.exp(-(((gx - density_c) / density_w) ** 2)) + 0.35

    for gx in range(x0 + 500, x1, 650):
        if R.random() < 0.6 * dens(gx):
            d = R.uniform(1200, 3600)
            props.append(("Chhatri_Umbrella", gx + R.uniform(-250, 250), bank_y(side, d), None, R.uniform(0, 360), R.uniform(0.9, 1.1)))
        if R.random() < 0.25 * dens(gx):
            d = R.uniform(900, 3200)
            props.append(("Chowki_Platform", gx + R.uniform(-250, 250), bank_y(side, d), None, R.choice([0, 90, 180]), 1.0))
    if temples:
        for tx in range(x0 + 4000, x1, 11000):
            props.append(("Temple_Riverside", tx + R.uniform(-1500, 1500), bank_y(side, 2200), None, yaw, 1.0))
        for tx in range(x0 + 2500, x1, 7000):
            props.append(("Temple_Small", tx + R.uniform(-800, 800), bank_y(side, 3700), None, yaw, 1.0))
    for fx in range(x0 + 1500, x1, 2200):
        if R.random() < 0.5:
            props.append(("Flag_Pole_Saffron", fx, bank_y(side, R.uniform(2500, 3800)), None, 0, 1.0))

    for gx in range(x0 + 2000, x1 - 2000, 6000):
        w = 0.6 + 3.5 * math.exp(-(((gx - density_c) / density_w) ** 2))
        for d in (700, 1500, 2400, 3300):
            y = bank_y(side, d)
            lanes.append({"start": (gx - 3000, y, ghat_z(d)), "end": (gx + 3000, y, ghat_z(d)), "width": 350, "weight": w})
    n_people = int((x1 - x0) / 100000.0 * 1000)
    for n in range(n_people):
        gx = R.gauss(density_c, density_w * 1.3) if R.random() < 0.6 else R.uniform(x0, x1)
        gx = max(x0 + 300, min(x1 - 300, gx))
        pr = math.exp(-(((gx - density_c) / 7000.0) ** 2))
        kind = R.random()
        if kind < 0.38:
            d = R.uniform(800, 3800)
            spots.append({"loc": (gx, bank_y(side, d), ghat_z(d)), "yaw": face + R.uniform(-40, 40),
                          "mode": R.choice(["Sit", "SitTalk", "SitTalk"]), "priority": pr + R.random() * 0.3})
        elif kind < 0.62:
            d = -R.uniform(150, 1300)                     # in the water: bathers, waders, washers
            mode = R.choice(["Tread", "Tread", "Locomotion", "Locomotion", "Wash"])
            z = -150.0 if mode == "Tread" else -108.0
            spots.append({"loc": (gx, bank_y(side, d), z), "yaw": face + R.uniform(-60, 60), "mode": mode, "priority": pr + 0.2, "fixed": True})
        elif kind < 0.7:
            d = R.uniform(150, 450)                       # washing clothes on the lowest steps
            spots.append({"loc": (gx, bank_y(side, d), ghat_z(d)), "yaw": face + R.uniform(-20, 20), "mode": "Wash", "priority": pr + 0.1})
        else:
            d = R.uniform(300, 3800)
            spots.append({"loc": (gx, bank_y(side, d), ghat_z(d)), "yaw": R.uniform(-180, 180),
                          "mode": R.choice(["Locomotion", "Talk", "Talk"]), "priority": pr})
    # buffaloes / cows standing in the shallows (the clip has them right next to the bathers)
    for n in range(int((x1 - x0) / 4000)):
        props.append((R.choice(["Buffalo", "Buffalo", "Zebu"]), R.uniform(x0, x1), bank_y(side, -R.uniform(200, 900)), -95.0,
                      R.uniform(0, 360), 1.0))


def build_near_top(sc, props, spots, lanes):
    """Parapet with domed kiosks along the top of the near ghats, and the busy strip up to the railway."""
    for gx in range(GHAT_X0 + 1000, GHAT_X1, 2000):
        sc.add("Ghat_Parapet_20m", xf(gx, PARAPET_Y, TOP_Z))
    for gx in range(GHAT_X0 + 2000, GHAT_X1 - 2000, 6000):
        lanes.append({"start": (gx - 3000, 4700, TOP_Z), "end": (gx + 3000, 4700, TOP_Z), "width": 450, "weight": 1.6})
        lanes.append({"start": (gx - 3000, 5250, TOP_Z), "end": (gx + 3000, 5250, TOP_Z), "width": 250, "weight": 0.6})
    for n in range(500):
        gx = R.gauss(-4000, 14000) if R.random() < 0.7 else R.uniform(GHAT_X0, GHAT_X1)
        gx = max(GHAT_X0 + 300, min(GHAT_X1 - 300, gx))
        y = R.uniform(4450, 5300)
        spots.append({"loc": (gx, y, TOP_Z), "yaw": R.uniform(-180, 180), "mode": R.choice(["Talk", "Talk", "Locomotion", "SitTalk"]),
                      "priority": 0.5 + 0.5 * math.exp(-((gx / 9000.0) ** 2))})
    for n in range(22):
        props.append((R.choice(["Zebu", "Zebu2", "Buffalo"]), R.uniform(GHAT_X0, GHAT_X1), R.uniform(4450, 5250), None, R.uniform(0, 360), 1.0))


def build_far_bank(sc, props, spots, lanes):
    """The dense old city across the river: riverfront houses + palaces facing the water, a second row,
    temples behind, crowds on the promenade."""
    widths = {}
    for i in range(1, 15):
        n = f"Bldg_Riverfront_{i:02d}"
        widths[n] = size_of(n).x or 1200.0
    palaces = {-9000: "Palace_ChetSingh", 9000: "Palace_Darbhanga", -22000: "Palace_Darbhanga", 23500: "Palace_ChetSingh"}
    x = FAR_X0 + 200
    while x < FAR_X1 - 600:
        pal = next((p for px, p in palaces.items() if abs(x - px) < 1200), None)
        if pal and blocks_corridor(x, x + (size_of(pal).x or 3000.0)):
            pal = None
        if pal:
            w = size_of(pal).x or 3000.0
            sc.add(pal, xf(x + w / 2, FAR_ROW_Y, TOP_Z, 180))
            x += w + R.uniform(200, 500)
            continue
        n = R.choice(list(widths))
        w = widths[n]
        if blocks_corridor(x, x + w):
            x += 250
            continue
        y = FAR_ROW_Y - R.uniform(-150, 350)
        sc.add(n, xf(x + w / 2, y, TOP_Z, 180))
        if R.random() < 0.3:
            props.append(("Water_Tank_Rooftop", x + w / 2 + R.uniform(-300, 300), y - 600, None, 0, 1.0))
        x += w + (R.uniform(350, 700) if R.random() < 0.18 else R.uniform(0, 60))
    # second row behind, stepping up the skyline
    x = FAR_X0
    while x < FAR_X1:
        n = f"Bldg_Town_{R.randint(1, 8):02d}"
        w = size_of(n).x or 800.0
        if blocks_corridor(x, x + w):
            x += 250
            continue
        sc.add(n, xf(x + w / 2, FAR_ROW_Y - 3800, TOP_Z, 180), mats=sign_mats(n))
        x += w + (R.uniform(400, 900) if R.random() < 0.2 else R.uniform(0, 80))
    for tx in (-30000, -12000, 6000, 21000):
        props.append((R.choice(["Temple_Medium", "HinduTemple", "TemplesSet"]), tx, FAR_ROW_Y - 2600, TOP_Z, 180, 1.0))
    # promenade crowd on the top of the far ghats
    for gx in range(FAR_X0 + 2000, FAR_X1 - 2000, 6000):
        lanes.append({"start": (gx - 3000, FAR_TOP_Y - 200, TOP_Z), "end": (gx + 3000, FAR_TOP_Y - 200, TOP_Z), "width": 300, "weight": 1.4})
    for n in range(300):
        gx = R.gauss(0, 9000)
        spots.append({"loc": (max(FAR_X0, min(FAR_X1, gx)), FAR_TOP_Y - R.uniform(80, 380), TOP_Z), "yaw": R.uniform(-180, 180),
                      "mode": R.choice(["Talk", "Talk", "Locomotion", "SitTalk"]), "priority": 0.4 + 0.6 * math.exp(-((gx / 6000.0) ** 2))})


def build_ground(sc):
    # Near bank: from the top of the ghats out to the fields.
    for gx in range(-92000, 92001, 2000):
        for gy in range(5000, 33001, 2000):
            sc.add("Ground_Tile_20m", xf(gx, gy, TOP_Z - 2), cull=0)
    # Overlays: littered strip by the river, village ground, fields.
    for gx in range(GHAT_X0, GHAT_X1 + 1, 2000):
        sc.add("Ground_Tile_20m", xf(gx, 5000, TOP_Z - 1), mats=("MI_FlowerDirt",))
    for gx in range(GHAT_X0 - 6000, GHAT_X1 + 6001, 2000):
        for gy in (9000, 11000, 13000, 15000):
            sc.add("Ground_Tile_20m", xf(gx, gy, TOP_Z - 1), mats=("MI_VillageGround",))
    for gx in range(-92000, 92001, 2000):
        for gy in (19000, 21000, 23000, 25000, 27000):
            sc.add("Ground_Tile_20m", xf(gx, gy, TOP_Z - 1), mats=(R.choice(["MI_GrassSparse", "MI_VillageGround", "MI_Grass"]),))
    # Far bank: city ground behind the ghats; sandbanks beyond the ends of the city.
    for gx in range(FAR_X0 - 4000, FAR_X1 + 4001, 2000):
        for gy in range(-20000, -34001, -2000):
            sc.add("Ground_Tile_20m", xf(gx, gy, TOP_Z - 2))
    for gx in range(-90000, 90001, 5000):
        if FAR_X0 - 5000 < gx < FAR_X1 + 5000:
            continue
        for gy in range(-17500, -50001, -5000):
            z = -60.0 if gy == -17500 else R.uniform(0, 80)
            sc.add("Sandbank_Tile_50m", xf(gx, gy, z, R.choice([0, 90, 180, 270])))


def build_rail_and_road(sc, props):
    for gx in range(-90000, 90001, 2000):
        sc.add("Rail_Track_20m", xf(gx, RAIL_Y, TOP_Z - 75))
    for gx in range(GHAT_X0 - 8000, GHAT_X1 + 8001, 2000):
        sc.add("Road_Dusty_20m", xf(gx, ROAD_Y, TOP_Z + 2))
    # village lanes (galis) behind the rows
    for gy in GALI_Y:
        for gx in range(GHAT_X0 - 4000, GHAT_X1 + 4001, 2000):
            sc.add("Road_Dusty_20m", xf(gx, gy, TOP_Z + 1))
    for gx in range(GHAT_X0 - 6000, GHAT_X1 + 6000, 3500):
        props.append(("Electric_Pole", gx, POLE_Y, TOP_Z, 0, 1.0))
    # parked / broken-down autos, carts and bikes along the road shoulders
    for n in range(40):
        props.append((R.choice(["AutoRickshaw", "AutoRickshaw2", "BikePulsar150", "BikePulsar135"]), R.uniform(GHAT_X0, GHAT_X1),
                      R.choice([6900, 7900]) + R.uniform(-60, 60), TOP_Z + 5, R.choice([0, 180]) + R.uniform(-15, 15), 1.0))
    for n in range(40):
        props.append((R.choice(["Zebu", "Zebu", "Zebu2", "Buffalo"]), R.uniform(GHAT_X0, GHAT_X1),
                      R.choice([R.uniform(6300, 6900), R.uniform(7900, 8400), R.uniform(10500, 10900)]), None, R.uniform(0, 360), 1.0))


def build_village(sc, props, lanes, spots):
    """Three rows of low village houses along the road, stalls in front, galis behind, trees and junk."""
    names = [f"Bldg_Village_{i:02d}" for i in range(1, 9)]
    for row, (fy, yaw) in enumerate(VILLAGE_ROWS):
        x = GHAT_X0 - 6000
        while x < GHAT_X1 + 6000:
            if row == 0 and abs(x - PICKUP.x) < 800:
                x += 1600  # the dhaba goes here
                continue
            # mostly village houses, the odd taller town building, empty plots with junk
            r = R.random()
            if r < 0.08:
                gap = R.uniform(600, 1400)
                for k in range(3):
                    props.append((R.choice(["Garbage_Heap_0", "Garbage_Heap_1", "Garbage_Heap_2", "PH_compost_bags", "PH_old_tyre"]),
                                  x + R.uniform(0, gap), fy + R.uniform(100, 600), TOP_Z, R.uniform(0, 360), 1.0))
                x += gap
                continue
            n = R.choice(names) if r < 0.88 else f"Bldg_Town_{R.randint(1, 8):02d}"
            w = size_of(n).x or 700.0
            sc.add(n, xf(x + w / 2, fy + R.uniform(-60, 60), TOP_Z, yaw), mats=sign_mats(n))
            x += w + (R.uniform(200, 700) if R.random() < 0.25 else R.uniform(0, 40))
        # street lane in front of the row
        for gx in range(GHAT_X0, GHAT_X1, 8000):
            lanes.append({"start": (gx, fy - 500, TOP_Z), "end": (gx + 8000, fy - 500, TOP_Z), "width": 350, "weight": 0.9 if row == 0 else 0.5})
    # tin-shed stalls on the village side of the road, with people sitting / chatting under them
    sheds = ["Shed_Tin_01", "Shed_Tin_02", "Shed_Tin_03"]
    for gx in range(GHAT_X0, GHAT_X1, 900):
        if R.random() < 0.42 and abs(gx - PICKUP.x) > 1000:
            x = gx + R.uniform(-200, 200)
            props.append((R.choice(sheds), x, SHED_Y, TOP_Z, 0, 1.0))
            for k in range(R.randint(1, 3)):
                spots.append({"loc": (x + R.uniform(-120, 120), SHED_Y + R.uniform(80, 220), TOP_Z), "yaw": -90 + R.uniform(-50, 50),
                              "mode": R.choice(["Talk", "SitTalk", "Sit"]), "priority": 0.55})
            if R.random() < 0.5:
                props.append(("PH_plastic_monobloc_chair_01", x + R.uniform(-150, 150), SHED_Y - R.uniform(50, 200), TOP_Z, R.uniform(0, 360), 1.0))
    # people along the road shoulders
    for gx in range(GHAT_X0, GHAT_X1, 8000):
        lanes.append({"start": (gx, 6950, TOP_Z), "end": (gx + 8000, 6950, TOP_Z), "width": 200, "weight": 0.6})
        lanes.append({"start": (gx, 7850, TOP_Z), "end": (gx + 8000, 7850, TOP_Z), "width": 250, "weight": 1.0})
    for gy in GALI_Y:
        for gx in range(GHAT_X0, GHAT_X1, 8000):
            lanes.append({"start": (gx, gy, TOP_Z), "end": (gx + 8000, gy, TOP_Z), "width": 300, "weight": 0.45})
    # big shade trees between the stalls / behind the rows, like the clip's left side
    for n in range(110):
        x = R.uniform(GHAT_X0 - 8000, GHAT_X1 + 8000)
        y = R.choice([R.uniform(8150, 8450), R.uniform(10400, 11000), R.uniform(13100, 13700), R.uniform(15500, 19000)])
        props.append((R.choice(["PH_island_tree_02", "PH_island_tree_01", "PH_tree_small_02", "BananaTree", "PH_jacaranda_tree"]),
                      x, y, TOP_Z, R.uniform(0, 360), R.uniform(0.85, 1.25)))
    for n in range(14):
        props.append(("PH_dead_tree_trunk", R.uniform(GHAT_X0, GHAT_X1), R.uniform(15500, 19000), TOP_Z, R.uniform(0, 360), 1.0))
    props.append(("HinduTemple", 8000, 16800, TOP_Z, 0, 1.0))
    props.append(("Temple_Medium", -30000, 16600, TOP_Z, 0, 1.0))
    # village clutter: buckets, crates, cans, cots, bikes leaning on walls
    clutter = ["PH_plastic_crate_01", "PH_plastic_crate_02", "PH_wooden_bucket_01", "PH_metal_jerrycan", "PH_plastic_jerrycan",
               "PH_plastic_container", "PH_cardboard_box_01", "PH_wicker_basket_01", "PH_old_tyre", "PH_cement_bag", "PH_barrel_03",
               "PH_rusted_wheel_rim_01", "PH_ceramic_pot", "PH_small_lpg_tank"]
    for fy, _ in VILLAGE_ROWS:
        for n in range(320):
            props.append((R.choice(clutter), R.uniform(GHAT_X0 - 4000, GHAT_X1 + 4000), fy - R.uniform(60, 420), TOP_Z,
                          R.uniform(0, 360), R.uniform(0.9, 1.1)))


def build_dhaba(props):
    # "Sharma Bhojnalaya": kirana shop + bhelpuri cart + chai stall at the pickup point.
    props.append(("KiranaShop", PICKUP.x, PICKUP.y + 750, TOP_Z, 180, 1.4))
    props.append(("BhelpuriShop", PICKUP.x + 450, PICKUP.y + 150, TOP_Z, 0, 1.0))
    props.append(("ChaiBench", PICKUP.x - 380, PICKUP.y + 180, TOP_Z, 0, 1.0))
    props.append(("TeaBoiler", PICKUP.x - 380, PICKUP.y + 450, TOP_Z + 80, 0, 1.0))
    for i in range(4):
        props.append(("PH_plastic_monobloc_chair_01", PICKUP.x - 700 + i * 90, PICKUP.y + 20, TOP_Z, R.uniform(0, 360), 1.0))


def build_boats(props, spots):
    boat_names = ["Boat_Wooden_Varanasi", "Boat_Wooden_Varanasi", "Boat_Wooden_Varanasi", "BoatWooden", "BoatOld"]
    for bx in range(GHAT_X0, GHAT_X1, 800):
        for side in (1, -1):
            if side < 0 and not (FAR_X0 < bx < FAR_X1):
                continue
            if R.random() < 0.5:
                name = R.choice(boat_names)
                d = -R.uniform(300, 2600)
                y = bank_y(side, d)
                yaw = 90 + R.uniform(-25, 25) if d > -1500 else R.uniform(-20, 20)
                props.append((name, bx + R.uniform(-300, 300), y, -35.0, yaw, 1.0))
                if R.random() < 0.35:
                    spots.append({"loc": (bx, y, 10.0), "yaw": yaw, "mode": "Sit", "priority": 0.3, "fixed": True})
    for n in range(26):   # boats out on the river
        props.append((R.choice(boat_names), R.uniform(-30000, 30000), R.uniform(-12500, -3000), -35.0, R.uniform(0, 360), 1.0))


# weighted: the clip's river is thick with white plastic, thermocol, packets, flowers and leaf bowls
DEBRIS = (["Debris_Marigolds_A"] * 4 + ["Debris_Marigolds_B"] * 2 + ["Debris_LeafBowl"] * 3 + ["Debris_Bottle"] * 2 +
          ["Debris_Bag_0", "Debris_Bag_1", "Debris_Bag_2"] * 3 + ["Debris_Foam_0", "Debris_Foam_1"] * 2 + ["Debris_Rag_0", "Debris_Rag_1"] +
          ["Debris_Styro_0", "Debris_Styro_1"] * 3 + ["Debris_Trash_0", "Debris_Trash_1", "Debris_Trash_2"] * 4)


def build_debris(sc):
    """Floating garbage everywhere: piled along both waterlines, thick in the shallows, drifting across."""
    def drop(x, y):
        name = R.choice(DEBRIS)
        z = 1.0 if "Foam" in name else 2.0
        s = R.uniform(0.45, 0.8) if ("Bag" in name or "Rag" in name) else R.uniform(0.8, 1.3)
        sc.add(name, xf(x, y, z, R.uniform(0, 360), s), collision=False, cull=9000.0, shadow=False)
    for i in range(9000):                          # near waterline
        x = R.gauss(-3000, 15000) if R.random() < 0.7 else R.uniform(GHAT_X0, GHAT_X1)
        if GHAT_X0 < x < GHAT_X1:
            drop(x, -abs(R.gauss(0, 500)) - 40.0)
    for i in range(8000):                          # across the river (denser where you swim)
        x = R.gauss(-1000, 9000) if R.random() < 0.6 else R.uniform(-40000, 40000)
        drop(x, R.uniform(FAR_EDGE_Y + 300, -400))
    for i in range(7000):                          # far waterline
        x = R.gauss(0, 12000) if R.random() < 0.7 else R.uniform(FAR_X0, FAR_X1)
        if FAR_X0 < x < FAR_X1:
            drop(x, FAR_EDGE_Y + abs(R.gauss(0, 500)) + 40.0)


LITTER = ["Litter_Patch_0", "Litter_Patch_1", "Litter_Patch_2", "Litter_Patch_3"]


def build_litter(sc):
    """Garbage on land: along the track, the road shoulders, the ghat-top strip, the village fronts and galis,
    plus dumped heaps by the railway."""
    def patch(x, y, name=None, s=None):
        sc.add(name or R.choice(LITTER), xf(x, y, TOP_Z + 1, R.uniform(0, 360), s or R.uniform(0.8, 1.4)),
               collision=False, cull=7000.0, shadow=False)
    X0, X1 = GHAT_X0 - 6000, GHAT_X1 + 6000
    for i in range(2600):                         # both sides of the ballast
        patch(R.uniform(X0, X1), RAIL_Y + R.choice([-1, 1]) * R.uniform(260, 700))
    for i in range(700):
        sc.add("Litter_Strip", xf(R.uniform(X0, X1), RAIL_Y + R.choice([-1, 1]) * R.uniform(300, 450), TOP_Z + 1, R.choice([0, 180])),
               collision=False, cull=8000.0, shadow=False)
    for i in range(1500):                         # road shoulders (the wheel tracks stay clearer)
        patch(R.uniform(X0, X1), R.choice([R.uniform(6700, 7080), R.uniform(7720, 8200), R.uniform(6700, 7080), R.uniform(7100, 7700)]),
              s=R.uniform(0.6, 1.0))
    for i in range(1100):                         # ghat-top strip (flowers + litter)
        x = R.uniform(GHAT_X0, GHAT_X1)
        patch(x, R.uniform(4300, 5500), R.choice(LITTER + ["Litter_Flowers", "Litter_Flowers"]))
    for fy, _ in VILLAGE_ROWS:                    # in front of the houses
        for i in range(550):
            patch(R.uniform(X0, X1), fy - R.uniform(80, 500))
    for gy in GALI_Y:
        for i in range(700):
            patch(R.uniform(X0, X1), gy + R.uniform(-350, 350))
    for i in range(260):                          # dumped heaps by the track and road
        y = R.choice([RAIL_Y + R.uniform(600, 950), RAIL_Y - R.uniform(450, 700), R.uniform(8200, 8500)])
        sc.add(R.choice(["Garbage_Heap_0", "Garbage_Heap_1", "Garbage_Heap_2"]),
               xf(R.uniform(X0, X1), y, TOP_Z, R.uniform(0, 360), R.uniform(0.8, 1.3)), collision=False, cull=15000.0)
    for i in range(1500):                         # far promenade
        sc.add(R.choice(LITTER + ["Litter_Flowers"]), xf(R.uniform(FAR_X0, FAR_X1), FAR_TOP_Y - R.uniform(50, 450), TOP_Z + 1,
                                                        R.uniform(0, 360), R.uniform(0.8, 1.3)), collision=False, cull=7000.0, shadow=False)


def build_junk_props(props):
    """Bigger junk the litter patches don't cover: bottles, cans, tyres, crates, bags - and a few rats."""
    junk = ["PH_can_rusted", "PH_plastic_bottle_gallon", "PH_bleach_bottle", "PH_compost_bags", "PH_cement_bag", "PH_trashbag",
            "PH_cardboard_box_01", "PH_old_tyre", "PH_plastic_crate_02", "PH_plastic_container", "PH_plastic_jerrycan"]
    for i in range(900):
        y = R.choice([RAIL_Y + R.choice([-1, 1]) * R.uniform(280, 800), R.uniform(6700, 8300), R.uniform(4300, 5500)])
        props.append((R.choice(junk), R.uniform(GHAT_X0, GHAT_X1), y, TOP_Z, R.uniform(0, 360), R.uniform(0.9, 1.1)))
    for i in range(60):
        props.append(("PH_street_rat", R.uniform(GHAT_X0, GHAT_X1), R.choice([RAIL_Y + R.uniform(400, 800), R.uniform(8200, 8500)]),
                      TOP_Z, R.uniform(0, 360), 1.0))


def build_wires(sc):
    """Sagging electric wires between the roadside poles, plus tangles running to the houses."""
    for gx in range(GHAT_X0 - 6000, GHAT_X1 + 6000 - 3500, 3500):
        sc.add("Wires_Span_35m", xf(gx + 1750, POLE_Y, TOP_Z), collision=False, cull=12000.0)
        if R.random() < 0.7:
            sc.add("Wires_Tangle", xf(gx, POLE_Y, TOP_Z), collision=False, cull=8000.0)


def build_grass(sc):
    """Green verge along the railway and road (the clip shows grass by the track) + clumps, fields."""
    for gx in range(GHAT_X0 - 40000, GHAT_X1 + 40001, 2000):
        for gy in (RAIL_Y + 900,):
            sc.add("Ground_Tile_20m", xf(gx, gy, TOP_Z), mats=("MI_Grass",))
    for i in range(9000):
        x = R.uniform(GHAT_X0 - 30000, GHAT_X1 + 30000)
        y = R.choice([R.uniform(RAIL_Y + 300, 6950), R.uniform(5300, RAIL_Y - 300), R.uniform(16000, 26000)])
        name = R.choice(["PH_grass_medium_01", "PH_grass_medium_02", "PH_grass_bermuda_01", "PH_grass_medium_02", "PH_fern_02"])
        sc.add(name, xf(x, y, TOP_Z + 1, R.uniform(0, 360), R.uniform(0.8, 1.5)), collision=False, cull=7000.0, shadow=False)
    for i in range(160):
        x = R.uniform(-90000, 90000)
        y = R.uniform(17000, 30000) if (GHAT_X0 - 6000 < x < GHAT_X1 + 6000) else R.uniform(8000, 30000)
        sc.add(R.choice(["PH_island_tree_01", "PH_island_tree_02", "PH_tree_small_02", "BananaTree", "PH_shrub_02"]),
               xf(x, y, TOP_Z, R.uniform(0, 360), R.uniform(0.9, 1.6)), collision=False, cull=30000.0)


def place_props(sc, props):
    for (name, x, y, z, yaw, s) in props:
        if z is None:
            z = trace_z(x, y)
            if z is None:
                d = y if y >= 0 else FAR_EDGE_Y - y
                z = ghat_z(d) if 0 <= d <= GHAT_DEPTH else TOP_Z
        cull = 0.0
        if name.startswith("PH_") or name.startswith("Garbage_") or name in ("Chowki_Platform", "TeaBoiler", "ChaiBench"):
            cull = 15000.0
        if name in ("PH_street_rat", "PH_can_rusted", "PH_bleach_bottle", "PH_plastic_bottle_gallon"):
            cull = 4000.0
        big_tree = name in ("PH_island_tree_01", "PH_island_tree_02", "PH_jacaranda_tree", "BananaTree", "PH_tree_small_02")
        if big_tree:
            cull = 30000.0
        collision = name not in ("Flag_Pole_Saffron", "PH_street_rat") and not name.startswith("Garbage_")
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
    river = spawn(unreal.GIRiver, unreal.Vector(0, -7500, 0), label="Ganga")
    river.set_editor_property("half_extent", unreal.Vector2D(95000, 11000))
    bed = spawn(unreal.StaticMeshActor, unreal.Vector(0, -7500, -600), label="RiverBed")
    smc = bed.get_editor_property("static_mesh_component")
    smc.set_editor_property("static_mesh", unreal.load_asset("/Engine/BasicShapes/Plane"))
    bed.set_actor_scale3d(unreal.Vector(1900, 230, 1))
    mi = load(f"{MI}/MI_Riverbed")
    if mi:
        smc.set_material(0, mi)

    spawn(unreal.PlayerStart, PLAYER_START, unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0), label="PlayerStart")
    spawn(unreal.GIBike, BIKE_POS, unreal.Rotator(0, 0, 0), label="Bike_Pulsar")
    spawn(unreal.GIBike, unreal.Vector(-11500, 7600, TOP_Z + 70), unreal.Rotator(roll=0.0, pitch=0.0, yaw=180.0), label="Bike_Pulsar2")

    train = spawn(unreal.GITrain, unreal.Vector(-30000, RAIL_Y, TOP_Z + 15), label="Train")
    train.set_editor_property("speed", 850.0)
    train.set_editor_property("track_start_x", -62000.0)
    train.set_editor_property("track_end_x", 62000.0)

    traffic = spawn(unreal.GITraffic, unreal.Vector(0, 0, 0), label="Traffic")
    lanes_t = []
    for y, d, n in ((ROAD_Y - 230, 1.0, 10), (ROAD_Y + 230, -1.0, 10)):
        tl = unreal.GITrafficLane()
        tl.set_editor_property("y", float(y))
        tl.set_editor_property("z", float(TOP_Z + 4))
        tl.set_editor_property("direction", d)
        tl.set_editor_property("count", n)
        lanes_t.append(tl)
    traffic.set_editor_property("lanes", lanes_t)
    traffic.set_editor_property("min_x", float(GHAT_X0 - 8000))
    traffic.set_editor_property("max_x", float(GHAT_X1 + 8000))
    traffic.set_editor_property("vehicle_meshes", [m for m in (mesh("AutoRickshaw"), mesh("AutoRickshaw2"), mesh("BikePulsar135"),
                                                               mesh("BikePulsar150")) if m])

    mission = spawn(unreal.GIMission, unreal.Vector(0, 0, 0), label="Mission")
    ghat_z_at = trace_z(GHAT_ENTRY.x, GHAT_ENTRY.y) or ghat_z(GHAT_ENTRY.y)
    drop_z = trace_z(DROP.x, DROP.y) or TOP_Z
    mission.set_editor_property("pickup_location", unreal.Vector(PICKUP.x, PICKUP.y, TOP_Z + 50))
    mission.set_editor_property("ghat_location", unreal.Vector(GHAT_ENTRY.x, GHAT_ENTRY.y, ghat_z_at + 50))
    mission.set_editor_property("drop_location", unreal.Vector(DROP.x, DROP.y, drop_z + 50))
    mission.set_editor_property("far_bank_y", FAR_EDGE_Y - 300)
    # Title: drift along the river past the near ghats with the train and the village behind.
    mission.set_editor_property("title_cam_start", unreal.Vector(-11000, -5200, 700))
    mission.set_editor_property("title_cam_end", unreal.Vector(4000, -4300, 1500))
    mission.set_editor_property("title_cam_look_at", unreal.Vector(-2000, 5200, 1500))

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

    # Signs: ghat names on the far riverfront (facing the river), the dhaba, the station halt board.
    for gx, name in NAMED_GHATS.items():
        text_sign(name, unreal.Vector(gx, FAR_ROW_Y + 160, TOP_Z + 650), 90, 110)
    text_sign("SHARMA BHOJNALAYA", unreal.Vector(PICKUP.x, PICKUP.y + 500, TOP_Z + 380), -90, 70, (1.0, 0.95, 0.9))


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
    propsc = Scatter("Props")
    props, spots, lanes = [], [], []

    build_ground(ground)
    build_ghat_bank(ghats, props, spots, lanes, 1, GHAT_X0, GHAT_X1, density_c=-3000.0, temples=False)
    build_ghat_bank(ghats, props, spots, lanes, -1, FAR_X0, FAR_X1, density_c=0.0)
    build_near_top(ghats, props, spots, lanes)
    build_far_bank(city, props, spots, lanes)
    build_rail_and_road(infra, props)
    build_village(city, props, lanes, spots)
    build_dhaba(props)
    build_boats(props, spots)
    build_junk_props(props)

    detail = Scatter("RiverDetail")
    litter = Scatter("Litter")
    nature = Scatter("Nature")
    build_debris(detail)
    build_litter(litter)
    build_wires(infra)
    build_grass(nature)

    for sc in (ground, ghats, city, infra, detail, litter, nature):
        sc.spawn()
    # Props need the ground/steps collision in place for traces.
    place_props(propsc, props)
    propsc.spawn()

    build_lighting()
    build_gameplay(lanes, spots)

    les.save_current_level()
    log("level saved", MAP)


main()
