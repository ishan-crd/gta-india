"""Build /Game/Maps/Mumbai - a Dharavi neighbourhood grown out of the Trial lane, after the gtamumbai clip.

  * the TRIAL LANE (vivid blue row houses, laundry overhead, the woman in the sari) is the heart of it and
    opens into the kids' cricket square, exactly as before;
  * around it a grid of narrow GALLIS (3.2 m between the house fronts) of one / two storey shanties, blue
    Trial houses and tin shacks, crossed by N-S alleys, laundry and wires across, drums, bicycles, dogs;
  * a CHAWL STREET (7 m) of 3-4 storey tenements with shops below, a second cricket game and a Ganesh
    pandal under festoon lights;
  * a MARKET STREET (N-S, 6 m) of veg / fruit carts under blue tarps from the main road to the chawl;
  * the MAIN ROAD (14 m) with shop-houses, neon signs, a chai tapri, a zebra crossing and traffic: BEST
    buses, kaali-peeli taxis, autos, scooters - keeping left;
  * the RAILWAY along the north edge: two tracks with Mumbai locals (people hanging out of the doors), shacks
    built right up to the ballast and a small suburban platform;
  * high-rise towers all round on the horizon.
Coordinates in cm, ground at Z = 0; X runs east along the lanes, Y north (rail) / south (main road).
"""
import os
import random
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "05_build_level.py")).read().replace("\nmain()\n", "\n")
exec(compile(_src, "05_build_level.py", "exec"))  # noqa - Scatter, mesh, xf, spawn, build_lighting, text_sign, ...

MAP = "/Game/Maps/Mumbai"
MAT_DIR = f"{ROOT}/Materials"
R = random.Random(20261004)

# ------------------------------------------------------------------------------------------ layout
# Trial lane core (unchanged look): lane along X at Y 0, 4.2 m wall to wall, square to the east
HALF = 210
LANE_X0, LANE_X1 = -1400, 2800
SQ_X0, SQ_X1 = 2800, 4300
SQ_Y0, SQ_Y1 = -800, 1400
PLAYER_START = unreal.Vector(150, -20, 100)

# district extents
W_X0, W_X1 = -15000, 4700           # west block of gallis (ends at the market street's back walls)
E_X0, E_X1 = 7300, 15000            # east block
GALLI_HALF = 160                    # half the clear width between house fronts
GALLIS = [-4400, -2200, 2200, 4400]  # E-W gallis besides the Trial lane (Y = 0)
EAST_GALLIS = GALLIS + [0]           # east of the market the Y 0 line is an ordinary galli
ALLEYS = [-12000, -9000, -6000, -3000, 9800, 12500]   # N-S alleys (3 m)
ALLEY_HALF = 150

CHAWL_S_EDGE, CHAWL_N_EDGE = 6770, 7470          # chawl street fronts (7 m)
CHAWL_Y = (CHAWL_S_EDGE + CHAWL_N_EDGE) / 2
MARKET_W_EDGE, MARKET_E_EDGE = 5700, 6300        # market street fronts (6 m), N-S
MARKET_X = (MARKET_W_EDGE + MARKET_E_EDGE) / 2

ROAD_C = -7840                      # main road centre line
ROAD_HALF = 700
SHOP_N_EDGE = ROAD_C + 1100         # shop fronts on the north side (4 m footpath)
SHOP_S_EDGE = ROAD_C - 1100
ROAD_X0, ROAD_X1 = -30000, 30000

RAIL_S_EDGE = 9300                  # fronts of the shacks facing the tracks (south side)
TRACK_Y = (9600, 10100)
RAIL_N_EDGE = 10400
PLATFORM_X = (-2000, 2000)

GATE_X = -3000                      # concrete gateway from the main road into the alley
CHAI = unreal.Vector(4650, SHOP_N_EDGE - 150, 0)
PANDAL_X = 2100
CHAWL_CRICKET_X = -8000

TRIAL_HOUSES = [f"Trial_House_{i:02d}" for i in range(1, 11)]
SHANTY_1F = [f"Shanty_1F_{i:02d}" for i in range(1, 9)]
SHANTY_2F = [f"Shanty_2F_{i:02d}" for i in range(1, 7)]
TENEMENT = [f"Tenement_3F_{i:02d}" for i in range(1, 7)] + [f"Tenement_4F_{i:02d}" for i in range(1, 5)]
SHACKS = [f"Shack_Corrugated_{i:02d}" for i in range(1, 5)]
TOWN = [f"Bldg_Town_{i:02d}" for i in range(1, 9)]
TOWERS = [f"Tower_Highrise_{i:02d}" for i in range(1, 9)]

# Trial lane core house order (from the Trial map)
HOUSE_W = {f"Trial_House_{i:02d}": w for i, w in enumerate((3.9, 4.3, 3.6, 4.1, 3.8, 4.4, 3.7, 4.0, 4.6, 3.5), 1)}
LEFT_ORDER = ["Trial_House_03", "Trial_House_07", "Trial_House_01", "Trial_House_04", "Trial_House_09", "Trial_House_05",
              "Trial_House_06", "Trial_House_10", "Trial_House_02", "Trial_House_08"]
RIGHT_ORDER = ["Trial_House_05", "Trial_House_10", "Trial_House_02", "Trial_House_08", "Trial_House_04", "Trial_House_07",
               "Trial_House_09", "Trial_House_01", "Trial_House_03", "Trial_House_06"]

BOUNDS = {}


def bounds(n):
    """Local (minx, miny, maxx, maxy) of a mesh, cm."""
    if n not in BOUNDS:
        m = mesh(n)
        if not m:
            BOUNDS[n] = None
        else:
            b = m.get_bounding_box()
            BOUNDS[n] = (b.min.x, b.min.y, b.max.x, b.max.y)
    return BOUNDS[n]


def depth_ok(n, max_depth):
    b = bounds(n)
    return b is not None and (b[3] - b[1]) <= max_depth


def near_alley(a0, a1):
    return any(a0 < ax + ALLEY_HALF + 40 and a1 > ax - ALLEY_HALF - 40 for ax in ALLEYS)


def in_square_zone(x0, x1):
    return x0 < 4700 and x1 > 2800


# ------------------------------------------------------------------------------------------ rows
def run(sc, props, spots, names, axis, edge, side, a0, a1, max_depth=10000.0, skip=None, decor=True, gap=(10, 60), mats_fn=None,
        big_gaps=True):
    """A run of buildings with their fronts on a street edge.
    axis 'x': buildings along X; side +1 = north of the edge facing -Y (yaw 0), -1 = south facing +Y (yaw 180).
    axis 'y': buildings along Y; side -1 = west of the edge facing +X (yaw 90), +1 = east facing -X (yaw -90)."""
    pool = [n for n in names if depth_ok(n, max_depth)]
    if not pool:
        return
    a = a0
    guard = 0
    while a < a1 and guard < 2000:
        guard += 1
        n = R.choice(pool)
        mnx, mny, mxx, mxy = bounds(n)
        w = mxx - mnx
        if a + w > a1 + 50:
            a += 150
            continue
        if skip and skip(a, a + w):
            a += 120
            continue
        front = -mny
        if axis == "x":
            yaw = 0.0 if side > 0 else 180.0
            facade = edge + side * front
            c = a - mnx if side > 0 else a + mxx
            t = xf(c, facade + R.uniform(-8, 8), 0, yaw + R.uniform(-0.8, 0.8))
            mid = (a + a + w) / 2
            door = (mid, edge)
            face_yaw = -90.0 if side > 0 else 90.0
        else:
            yaw = 90.0 if side < 0 else -90.0
            facade = edge + side * front
            c = a - mnx if side < 0 else a + mxx
            t = xf(facade + R.uniform(-8, 8), c, 0, yaw + R.uniform(-0.8, 0.8))
            mid = (a + a + w) / 2
            door = (edge, mid)
            face_yaw = 180.0 if side > 0 else 0.0
        sc.add(n, t, mats=mats_fn(n) if mats_fn else None)
        if decor:
            doorstep(props, spots, axis, door, w, side, face_yaw)
        a += w + (R.uniform(*gap) if (R.random() < 0.85 or not big_gaps) else R.uniform(120, 260))


def doorstep(props, spots, axis, door, w, side, face_yaw):
    """Life at the front: someone on the ota, a drum, a bicycle, an LPG cylinder, a dog."""
    def at(along, out):
        # "out" is measured from the house front into the street
        if axis == "x":
            return door[0] + along, door[1] - side * out
        return door[0] - side * out, door[1] + along
    if R.random() < 0.3:
        x, y = at(R.uniform(-w * 0.3, w * 0.3), 25)
        spots.append({"loc": (x, y, 0), "yaw": face_yaw + R.uniform(-30, 30), "mode": R.choice(["Sit", "SitTalk", "Talk"]), "priority": 0.5})
    if R.random() < 0.4:
        x, y = at(R.uniform(-w * 0.4, w * 0.4), R.uniform(0, 40))
        props.append(("Drum_Blue", x, y, 0, R.uniform(0, 360), 1.0))
    if R.random() < 0.14:
        x, y = at(R.uniform(-w * 0.3, w * 0.3), 10)
        props.append(("BicycleIndian", x, y, 0, (0 if axis == "x" else 90) + R.choice([0, 180]) + R.uniform(-8, 8), 1.0))
    if R.random() < 0.1:
        x, y = at(R.uniform(-w * 0.4, w * 0.4), 5)
        props.append(("LPG_Cylinder", x, y, 0, R.uniform(0, 360), 1.0))
    if R.random() < 0.04:
        x, y = at(R.uniform(-w * 0.4, w * 0.4), 30)
        props.append((R.choice(["DogLying", "DogStanding", "DogStanding2"]), x, y, 0, R.uniform(0, 360), 1.0))


def galli_names(x, y):
    """Blue Trial houses near the core, shacks by the rail and the far west, 2F shanties towards the chawl."""
    if abs(x) < 6000 and abs(y) < 2500:
        return TRIAL_HOUSES * 3 + SHANTY_1F
    if x < -9000:
        return SHACKS * 2 + SHANTY_1F + TRIAL_HOUSES
    if y > 3000:
        return SHANTY_2F * 2 + SHANTY_1F + TRIAL_HOUSES
    return SHANTY_1F * 2 + SHANTY_2F + TRIAL_HOUSES * 2 + SHACKS


# ------------------------------------------------------------------------------------------ builders
def build_ground(sc):
    for gx in range(-32000, 32001, 2000):
        for gy in range(-16000, 16001, 2000):
            if abs(gy - ROAD_C) < 1000:
                mat = "MI_Asphalt"
            elif gy < -5500 or abs(gy - CHAWL_Y) < 1000:
                mat = "MI_Concrete"
            elif gy > 8000:
                mat = "MI_Dirt"
            else:
                mat = R.choice(["MI_Dirt", "MI_Dirt", "MI_Concrete", "MI_GroundLitter"])
            sc.add("Ground_Tile_20m", xf(gx, gy, -2), mats=(mat,))
    for gx in range(-32000, 32001, 2000):
        sc.add("Ground_Tile_20m", xf(gx, CHAWL_Y, 4), mats=("MI_Concrete",))
    # the asphalt row is 20 m wide; footpaths either side in concrete
    for gx in range(-32000, 32001, 2000):
        for gy in (ROAD_C - 1700, ROAD_C + 1700):
            sc.add("Ground_Tile_20m", xf(gx, gy, 3), mats=("MI_Concrete",))


def build_trial_core(sc, props):
    """The Trial lane exactly as in the Trial map, plus its square."""
    def row(names, x0, x1, y, yaw):
        x = x0
        i = 0
        while x < x1:
            n = names[i % len(names)]
            w = HOUSE_W[n] * 100.0
            sc.add(n, xf(x + w / 2, y + R.uniform(-8, 8), 0, yaw + R.uniform(-0.6, 0.6)))
            x += w + R.uniform(2, 10)
            i += 1
    row(LEFT_ORDER, LANE_X0, LANE_X1, HALF, 0.0)
    row(RIGHT_ORDER, LANE_X0, LANE_X1, -HALF, 180.0)
    # the lane carries on west with the same blue houses (cut by the N-S alleys)
    for side, yaw, order in ((1, 0.0, LEFT_ORDER), (-1, 180.0, RIGHT_ORDER)):
        x = W_X0
        i = R.randrange(10)
        while x < LANE_X0 - 30:
            n = order[i % len(order)]
            w = HOUSE_W[n] * 100.0
            i += 1
            if near_alley(x, x + w) or x + w > LANE_X0 - 20:
                x += 120
                continue
            sc.add(n, xf(x + w / 2, side * HALF + R.uniform(-8, 8), 0, yaw + R.uniform(-0.6, 0.6)))
            x += w + R.uniform(2, 12)
    # square: rows set back on its north / south edge (opened at the west so the gallis meet it)
    row(LEFT_ORDER[3:] + LEFT_ORDER[:3], SQ_X0 + 200, SQ_X1 + 300, SQ_Y1, 0.0)
    row(RIGHT_ORDER[4:] + RIGHT_ORDER[:4], SQ_X0 + 200, SQ_X1 + 300, SQ_Y0, 180.0)
    sc.add("Trial_House_09", xf(SQ_X1 + 200, 150, 0, -90))
    sc.add("Trial_House_04", xf(SQ_X1 + 200, -310, 0, -90))
    sc.add("Trial_House_06", xf(SQ_X1 + 200, 640, 0, -90))
    # a brick two-storey showing over the right row
    sc.add("Shanty_2F_04", xf(1350, -760, 0, 180))
    for (x, y, s) in ((3300, 2000, 1.3), (1600, 1050, 1.1), (4200, -1600, 1.4), (-300, 1000, 1.0), (600, -1050, 1.2)):
        props.append(("PH_island_tree_02", x, y, 0, R.uniform(0, 360), s))
    for (x, n, yaw) in ((560, "Trial_Laundry_Cross_01", 92), (1850, "Trial_Laundry_Cross_03", 95), (-600, "Trial_Laundry_Cross_02", 90)):
        props.append((n, x, 0, 0, yaw, 1.0))
    props.append(("Trial_Laundry_Cross_03", 3700, 1250, 0, 0, 1.0))
    props.append(("Trial_Laundry_Wall_02", 230, HALF - 6, 0, 0, 1.0))
    props.append(("Trial_Laundry_Wall_01", 980, -HALF + 6, 0, 180, 1.0))
    props.append(("Trial_Laundry_Wall_03", 1700, HALF - 6, 0, 0, 1.0))
    props.append(("Drum_Blue", 760, HALF - 75, 22, 0, 1.0))
    props.append(("BicycleIndian", 1650, -HALF + 70, 0, 4, 1.0))
    props.append(("Trial_Slippers", 1180, -HALF + 55, 22, 30, 1.0))
    props.append(("Trial_Slippers", 300, HALF - 60, 24, -20, 1.0))
    props.append(("LPG_Cylinder", 2350, HALF - 60, 22, 0, 1.0))
    props.append(("Matka_Stack", -700, -HALF + 90, 20, 0, 0.6))
    props.append(("Drum_Blue", 3000, SQ_Y1 - 60, 0, 0, 1.0))
    props.append(("Plastic_Stool", 2100, -HALF + 55, 22, 15, 1.0))
    for i in range(40):
        side = R.choice([-1, 1])
        props.append((R.choice(["PH_grass_medium_01", "PH_grass_bermuda_01", "PH_grass_medium_02"]), R.uniform(-800, 2800),
                      side * R.uniform(120, 150), 0, R.uniform(0, 360), R.uniform(0.4, 0.8)))


def build_gallis(sc, props, spots, lanes):
    depth = 1100 - GALLI_HALF - 40           # what fits back to back between galli centres 2200 apart
    for gy in EAST_GALLIS:
        for (x0, x1) in ((W_X0, W_X1), (E_X0, E_X1)):
            if gy == 0 and x0 == W_X0:
                continue                  # the Trial lane
            def skip(a, b, gy=gy):
                if near_alley(a, b):
                    return True
                # the square's rows back onto the gallis either side of it
                return abs(gy) == 2200 and in_square_zone(a, b)
            # north row (faces -Y) and south row (faces +Y); the inner rows next to the Trial lane only
            # take shallow houses (the Trial rows' backs are 670 cm from its centre)
            for side, md in ((1, depth), (-1, depth)):
                x = x0
                # split long runs into chunks so the style can change along the galli
                while x < x1:
                    xe = min(x1, x + 2500)
                    run(sc, props, spots, galli_names((x + xe) / 2, gy), "x", gy + side * GALLI_HALF, side, x, xe, md, skip)
                    x = xe
            lanes.append({"start": (x0, gy, 0), "end": (x1, gy, 0), "width": GALLI_HALF * 1.2, "weight": 0.5})
            # laundry / wires across, litter, people
            x = x0 + 300
            while x < x1:
                if not near_alley(x - 250, x + 250) and not (abs(gy) == 2200 and in_square_zone(x - 300, x + 300)):
                    r = R.random()
                    if r < 0.4:
                        props.append((R.choice(["Laundry_Line_6m", "Laundry_Line_6m", "Trial_Laundry_Cross_02", "Trial_Laundry_Cross_04"]),
                                      x, gy, 0, 90 + R.uniform(-10, 10), 1.0))
                    elif r < 0.6:
                        props.append(("Wire_Bundle_Alley", x, gy, 0, 90 + R.uniform(-15, 15), 1.0))
                x += R.uniform(450, 1000)
            for i in range(int((x1 - x0) / 700)):
                spots.append({"loc": (R.uniform(x0, x1), gy + R.uniform(-90, 90), 0), "yaw": R.uniform(-180, 180),
                              "mode": R.choice(["Talk", "Locomotion", "Wash", "Sit", "Talk"]), "priority": 0.45})
    # N-S alleys: walk lanes from the main road footpath to the chawl street
    for ax in ALLEYS:
        lanes.append({"start": (ax, SHOP_N_EDGE if ax == GATE_X else GALLIS[0], 0), "end": (ax, CHAWL_S_EDGE, 0),
                      "width": ALLEY_HALF * 1.2, "weight": 0.35})
    # the Trial lane continues west as a walk lane
    lanes.append({"start": (W_X0, 0, 0), "end": (LANE_X0, 0, 0), "width": 220, "weight": 0.4})


def build_chawl(sc, props, spots, lanes):
    def skip_s(a, b):
        return near_alley(a, b) or (a < MARKET_E_EDGE + 100 and b > MARKET_W_EDGE - 100)

    def skip_n(a, b):
        return near_alley(a, b) or (a < PANDAL_X + 380 and b > PANDAL_X - 380)
    run(sc, props, spots, TENEMENT + SHANTY_2F, "x", CHAWL_S_EDGE, -1, -16000, 16000, CHAWL_S_EDGE - 5500, skip_s, gap=(0, 30))
    run(sc, props, spots, TENEMENT + SHANTY_2F, "x", CHAWL_N_EDGE, 1, -16000, 16000, 1240, skip_n, gap=(0, 30))
    lanes.append({"start": (-16000, CHAWL_Y, 0), "end": (16000, CHAWL_Y, 0), "width": 420, "weight": 1.0})
    # laundry high across, wires, neon / signs on a few shops, tarps
    x = -15500
    while x < 15500:
        if not near_alley(x - 300, x + 300) and abs(x - PANDAL_X) > 2500:
            r = R.random()
            if r < 0.3:
                props.append(("Laundry_Line_10m", x, CHAWL_Y, 0, 90 + R.uniform(-8, 8), 1.0))
            elif r < 0.55:
                props.append(("Wire_Bundle_Alley", x, CHAWL_Y, 0, 90 + R.uniform(-15, 15), 1.0))
        if R.random() < 0.3:
            side = R.choice([-1, 1])
            props.append(("Tarp_Canopy_3m", x, (CHAWL_N_EDGE - 150) if side > 0 else (CHAWL_S_EDGE + 150),
                          0, 0 if side > 0 else 180, 1.0))
        x += R.uniform(500, 1100)
    for i in range(140):
        spots.append({"loc": (R.uniform(-15000, 15000), CHAWL_Y + R.uniform(-250, 250), 0), "yaw": R.uniform(-180, 180),
                      "mode": R.choice(["Talk", "Talk", "Locomotion", "Sit", "SitTalk"]), "priority": 0.55})
    # Ganesh pandal under festoon lights
    pz = CHAWL_N_EDGE + 40
    props.append(("Pandal_Ganesh", PANDAL_X, pz, 0, 0, 1.0))
    props.append(("Ganpati", PANDAL_X, pz + 295, 70, 0, 1.0))
    for k, col in enumerate(((255, 60, 200), (60, 255, 120), (255, 200, 60), (90, 140, 255))):
        light = spawn(unreal.PointLight, unreal.Vector(PANDAL_X - 450 + k * 300, CHAWL_Y - 150, 460), label="PandalLight")
        lc = light.get_component_by_class(unreal.PointLightComponent)
        lc.set_editor_property("intensity", 150.0)
        lc.set_editor_property("attenuation_radius", 600.0)
        lc.set_editor_property("light_color", unreal.Color(col[0], col[1], col[2], 255))
        lc.set_editor_property("cast_shadows", False)
    for i in range(26):   # a crowd dancing / praying at the pandal
        spots.append({"loc": (PANDAL_X + R.uniform(-500, 500), CHAWL_Y + R.uniform(-250, 220), 0),
                      "yaw": 90 + R.uniform(-50, 50), "mode": R.choice(["Talk", "Talk", "SitTalk"]), "priority": 1.4})


def build_market(sc, props, spots, lanes):
    def skip(a, b):
        # gallis and the Trial lane open into the market street
        return any(a < gy + GALLI_HALF + 120 and b > gy - GALLI_HALF - 120 for gy in GALLIS) or (a < SQ_Y1 + 600 and b > SQ_Y0 - 600)
    y0, y1 = SHOP_N_EDGE + 1400, CHAWL_S_EDGE - 120
    run(sc, props, spots, SHANTY_2F + SHANTY_1F, "y", MARKET_W_EDGE, -1, y0, y1, MARKET_W_EDGE - W_X1 - 80, skip, decor=False, gap=(0, 30))
    run(sc, props, spots, SHANTY_2F + SHANTY_1F, "y", MARKET_E_EDGE, 1, y0, y1, E_X0 - MARKET_E_EDGE - 80, skip, decor=False, gap=(0, 30))
    lanes.append({"start": (MARKET_X, SHOP_N_EDGE, 0), "end": (MARKET_X, CHAWL_S_EDGE, 0), "width": 220, "weight": 1.6})
    y = y0
    while y < y1:
        for side in (-1, 1):
            if R.random() < 0.8:
                ex = MARKET_W_EDGE + 110 if side < 0 else MARKET_E_EDGE - 110
                if R.random() < 0.5:
                    props.append(("Tarp_Canopy_3m", ex - side * 60, y, 0, 90 if side < 0 else -90, 1.0))
                kind = R.random()
                if kind < 0.45:
                    props.append((R.choice(["Veg_Cart", "VegCartModel"]), ex + side * -10, y, 0, 90 + R.uniform(-8, 8), 1.0))
                elif kind < 0.7:
                    props.append(("StallModel", ex - side * 20, y, 0, 90 if side < 0 else -90, 1.0))
                elif kind < 0.85:
                    props.append(("Snack_Strip", ex - side * 40, y, 0, 90 if side < 0 else -90, 1.0))
                else:
                    props.append((R.choice(["Sack_Pile_01", "Sack_Pile_02", "Sack_Pile_03", "Matka_Stack"]), ex, y, 0, R.uniform(0, 360), 1.0))
                # the vendor
                spots.append({"loc": (ex + side * 80, y + R.uniform(-60, 60), 0), "yaw": 0 if side < 0 else 180,
                              "mode": "Talk", "priority": 1.3})
        y += R.uniform(380, 520)
    for i in range(110):
        spots.append({"loc": (MARKET_X + R.uniform(-150, 150), R.uniform(y0, y1), 0), "yaw": R.uniform(-180, 180),
                      "mode": R.choice(["Talk", "Locomotion", "Talk"]), "priority": 0.9})


def build_main_road(sc, props, spots, lanes):
    def skip_n(a, b):
        return (a < MARKET_E_EDGE + 150 and b > MARKET_W_EDGE - 150) or (a < GATE_X + 420 and b > GATE_X - 420) or \
            (a < CHAI.x + 300 and b > CHAI.x - 300)
    town_or_tenement = TENEMENT + TOWN
    mats = lambda n: sign_mats(n) if n.startswith("Bldg_Town") else None
    run(sc, props, spots, town_or_tenement, "x", SHOP_N_EDGE, 1, ROAD_X0, ROAD_X1, -5500 - SHOP_N_EDGE, skip_n, decor=False,
        gap=(0, 30), mats_fn=mats, big_gaps=False)
    run(sc, props, spots, town_or_tenement, "x", SHOP_S_EDGE, -1, ROAD_X0, ROAD_X1, 1400, None, decor=False, gap=(0, 30), mats_fn=mats,
        big_gaps=False)
    # neon signs / tarps along the shop fronts
    x = ROAD_X0
    while x < ROAD_X1:
        for side in (1, -1):
            edge = SHOP_N_EDGE if side > 0 else SHOP_S_EDGE
            if side > 0 and skip_n(x - 100, x + 100):
                continue
            if R.random() < 0.45:
                props.append((f"Neon_Sign_{R.randint(1, 6):02d}", x, edge - side * 30, R.uniform(330, 500), 0 if side > 0 else 180, 1.0))
            if R.random() < 0.4:
                props.append((R.choice(["Tarp_Canopy_3m", "Tarp_Canopy_5m"]), x, edge - side * 170, 0, 0 if side > 0 else 180, 1.0))
        x += R.uniform(700, 1300)
    # street lights (switched on by the weather) and poles
    for side in (1, -1):
        for lx in range(ROAD_X0 + 1000, ROAD_X1, 2600):
            y = ROAD_C + side * (ROAD_HALF + 120)
            props.append(("Electric_Pole", lx, y, 0, 0 if side > 0 else 180, 1.0))
            light = spawn(unreal.PointLight, unreal.Vector(lx, y - side * 150, 760), label="StreetLight")
            light.tags = ["StreetLight"]
            lc = light.get_component_by_class(unreal.PointLightComponent)
            lc.set_editor_property("intensity", 0.0)
            lc.set_editor_property("attenuation_radius", 1800.0)
            lc.set_editor_property("light_color", unreal.Color(170, 210, 255, 255))
            lc.set_editor_property("cast_shadows", False)
            lc.set_editor_property("visible", False)
    # footpath life
    for i in range(80):
        side = R.choice([-1, 1])
        x = R.uniform(-20000, 20000)
        if side > 0 and skip_n(x - 200, x + 200):
            continue
        y = ROAD_C + side * R.uniform(780, 920)
        k = R.random()
        if k < 0.3:
            props.append((R.choice(["Veg_Cart", "VegCartModel"]), x, y, 0, 90 * side + R.uniform(-15, 15), 1.0))
            spots.append({"loc": (x + 120, y + side * 80, 0), "yaw": -90 * side, "mode": "Talk", "priority": 0.8})
        elif k < 0.5:
            props.append(("StallModel", x, y + side * 60, 0, 0 if side > 0 else 180, 1.0))
        else:
            props.append((R.choice(["Plastic_Stool", "Wooden_Bench", "Matka_Stack", "Drum_Blue", "Sack_Pile_01"]), x, y, 0, R.uniform(0, 360), 1.0))
    for gx in range(-24000, 24000, 6000):
        for y, w in ((ROAD_C + 880, 0.7), (ROAD_C - 880, 0.6)):
            lanes.append({"start": (gx, y, 0), "end": (gx + 6000, y, 0), "width": 240, "weight": w})
    for i in range(60):
        side = R.choice([-1, 1])
        spots.append({"loc": (R.uniform(-12000, 12000), ROAD_C + side * R.uniform(780, 960), 0), "yaw": R.uniform(-180, 180),
                      "mode": R.choice(["Talk", "Talk", "Locomotion", "Sit"]), "priority": 0.6})
    # zebra crossing at the market, gateway into the alley
    props.append(("Road_Zebra_14m", MARKET_X, ROAD_C, 1, 0, 1.0))
    props.append(("Road_Zebra_14m", GATE_X, ROAD_C, 1, 0, 1.0))
    props.append(("Gateway_Concrete", GATE_X, SHOP_N_EDGE + 60, 0, 0, 1.0))
    text_sign("DHARAVI", unreal.Vector(GATE_X, SHOP_N_EDGE, 380), -90, 60, (1.0, 0.95, 0.85))


def build_rail(sc, props, spots, lanes):
    for gx in range(-32000, 32001, 2000):
        for ty in TRACK_Y:
            sc.add("Rail_Track_20m", xf(gx, ty, -75))
    # shacks built right up to the ballast on both sides, a station platform on the north side
    def skip_n(a, b):
        return a < PLATFORM_X[1] + 600 and b > PLATFORM_X[0] - 600
    run(sc, props, spots, SHACKS * 3 + SHANTY_1F, "x", RAIL_S_EDGE, -1, -16000, 16000, 580, None, gap=(0, 40))
    run(sc, props, spots, SHACKS * 3 + SHANTY_1F, "x", RAIL_N_EDGE, 1, -30000, 30000, 900, skip_n, gap=(0, 40))
    run(sc, props, spots, SHACKS, "x", RAIL_S_EDGE, -1, -30000, -16200, 700, None, decor=False)
    run(sc, props, spots, SHACKS, "x", RAIL_S_EDGE, -1, 16200, 30000, 700, None, decor=False)
    props.append(("Rail_Platform_40m", (PLATFORM_X[0] + PLATFORM_X[1]) / 2, TRACK_Y[1] + 265, 0, 0, 1.0))
    # people walking along / across the tracks, on the platform
    lanes.append({"start": (-16000, RAIL_S_EDGE + 140, 0), "end": (16000, RAIL_S_EDGE + 140, 0), "width": 120, "weight": 0.35})
    for i in range(30):
        spots.append({"loc": (R.uniform(PLATFORM_X[0] + 200, PLATFORM_X[1] - 200), TRACK_Y[1] + 265 + R.uniform(80, 380), 90),
                      "yaw": -90 + R.uniform(-40, 40), "mode": R.choice(["Talk", "Talk", "Locomotion"]), "priority": 1.0})
    for i in range(40):
        side = R.choice([-1, 1])
        props.append((R.choice(["Litter_Patch_0", "Litter_Patch_1", "Garbage_Heap_0", "Garbage_Heap_1"]), R.uniform(-16000, 16000),
                      (RAIL_S_EDGE + R.uniform(30, 120)) if side < 0 else (RAIL_N_EDGE - R.uniform(30, 120)), 1, R.uniform(0, 360), R.uniform(0.5, 0.9)))


def build_boundary(sc, props):
    """Walls round the district (the towers sit behind them), across the main road ends and the track ends."""
    for x in range(-30500, 31000, 1000):
        sc.add("Wall_Boundary_10m", xf(x, RAIL_N_EDGE + 1000, 0))
        sc.add("Wall_Boundary_10m", xf(x, SHOP_S_EDGE - 1550, 0, 180))
    for y in range(int(SHOP_N_EDGE + 1300), int(RAIL_N_EDGE + 1000), 1000):
        if RAIL_S_EDGE - 400 < y < RAIL_N_EDGE + 400:
            continue                      # the trains run through
        sc.add("Wall_Boundary_10m", xf(-16300, y, 0, 90))
        sc.add("Wall_Boundary_10m", xf(16300, y, 0, -90))
    for x in (-28500, 28500):
        for y in range(int(SHOP_S_EDGE - 1500), int(SHOP_N_EDGE + 1600), 1000):
            sc.add("Wall_Boundary_10m", xf(x, y, 0, 90))
    for x in (-31000, 31000):
        for y in range(int(RAIL_S_EDGE - 1500), int(RAIL_N_EDGE + 1100), 1000):
            sc.add("Wall_Boundary_10m", xf(x, y, 0, 90))


def build_skyline(sc):
    """High-rises on the horizon in every direction (the clip's rooftop shots)."""
    def tower(x, y, yaw):
        sc.add(R.choice(TOWERS), xf(x, y, 0, yaw + R.uniform(-6, 6), R.uniform(0.9, 1.25)), collision=False)
    for i in range(70):
        tower(R.uniform(-45000, 45000), R.uniform(22000, 42000), 180)        # north, over the rail
    for i in range(55):
        tower(R.uniform(-45000, 45000), R.uniform(-42000, -18000), 0)        # south, over the main road
    for i in range(25):
        tower(R.uniform(-48000, -33000), R.uniform(-12000, 14000), 90)       # west, past the road / track ends
        tower(R.uniform(33000, 48000), R.uniform(-12000, 14000), -90)         # east


def build_lighting_mumbai():
    build_lighting()
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight):
            a.set_actor_rotation(unreal.Rotator(roll=0, pitch=-40, yaw=145), False)
            lc = a.get_component_by_class(unreal.DirectionalLightComponent)
            lc.set_editor_property("intensity", 10.5)
            lc.set_editor_property("temperature", 5700.0)
        elif isinstance(a, unreal.ExponentialHeightFog):
            fc = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
            fc.set_editor_property("fog_density", 0.014)
            fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.55, 0.6, 0.66, 1))
            fc.set_editor_property("start_distance", 2500.0)


def kids():
    ks = [load(f"/Game/Characters/{n}/{n}") for n in ("SK_KidGreen", "SK_KidOrange", "SK_KidTeal", "SK_KidWhite", "SK_KidBare")]
    ks = [k for k in ks if k]
    return ks or [m for m in (load(f"/Game/Characters/{n}/{n}") for n in ("SK_Teen", "SK_BoyKurta")) if m]


def cricket(label, loc, yaw, pitch_len, half_w, fielders):
    g = spawn(unreal.GICricketGame, loc, unreal.Rotator(roll=0, pitch=0, yaw=yaw), label=label)
    g.set_editor_property("kid_meshes", kids())
    for prop, n in (("stumps_mesh", "Cricket_Stumps"), ("bat_mesh", "Cricket_Bat"), ("ball_mesh", "Cricket_Ball")):
        m = mesh(n)
        if m:
            g.set_editor_property(prop, m)
    g.set_editor_property("pitch_length", pitch_len)
    g.set_editor_property("lane_half_width", half_w)
    g.set_editor_property("num_fielders", fielders)


def build_gameplay(lanes, spots, props):
    spawn(unreal.PlayerStart, PLAYER_START, unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0), label="PlayerStart")
    prof = spawn(unreal.GILevelProfile, unreal.Vector(0, 0, 0), label="LevelProfile")
    pm = load("/Game/Characters/SK_PlayerDhoti/SK_PlayerDhoti")
    if pm:
        prof.set_editor_property("player_mesh", pm)
    prof.set_editor_property("arm_length", 270.0)
    prof.set_editor_property("socket_offset", unreal.Vector(0, 8, 26))
    prof.set_editor_property("field_of_view", 75.0)
    prof.set_editor_property("start_pitch", -5.0)
    prof.set_editor_property("walk_speed", 150.0)
    prof.set_editor_property("hide_bag", True)

    woman = load("/Game/Characters/SK_WomanSaree/SK_WomanSaree")
    if woman:
        w = spawn(unreal.GIScriptedWalker, unreal.Vector(1700, 85, 0), unreal.Rotator(roll=0, pitch=0, yaw=180), label="SareeWoman")
        w.set_editor_property("mesh", woman)
        w.set_editor_property("end_point", unreal.Vector(-500, 95, 0))
        w.set_editor_property("speed", 100.0)
        w.set_editor_property("start_alpha", 0.45)
        w.set_editor_property("pause_at_ends", 5.0)

    cricket("Cricket", unreal.Vector(3350, -420, 0), 90, 900.0, 520.0, 3)
    cricket("Cricket_Chawl", unreal.Vector(CHAWL_CRICKET_X, CHAWL_Y, 0), 0, 1500.0, 330.0, 5)

    # rideable: a scooter in the square, an auto and a taxi at the main road kerbs
    for n, loc, yaw, myaw, four in (("ScooterActiva", unreal.Vector(4000, 1050, 90), 200.0, 0.0, False),
                                    ("AutoMumbai", unreal.Vector(GATE_X + 900, ROAD_C - ROAD_HALF + 110, 95), 0.0, 0.0, True),
                                    ("TaxiKaaliPeeli2", unreal.Vector(MARKET_X - 1400, ROAD_C + ROAD_HALF - 120, 95), 180.0, 0.0, True)):
        m = mesh(n)
        if m:
            v = spawn(unreal.GIBike, loc, unreal.Rotator(roll=0, pitch=0, yaw=yaw), label="Drivable_" + n)
            v.set_editor_property("mesh_override", m)
            v.set_editor_property("mesh_yaw_override", myaw)
            v.set_editor_property("four_wheeler", four)

    # main-road traffic keeping left (UE is left-handed: heading +X the left side is -Y)
    traffic = spawn(unreal.GITraffic, unreal.Vector(0, 0, 0), label="Traffic")
    lanes_t = []
    for y, d, n in ((ROAD_C - 350, 1.0, 14), (ROAD_C + 350, -1.0, 14)):
        tl = unreal.GITrafficLane()
        tl.set_editor_property("y", float(y))
        tl.set_editor_property("z", 4.0)
        tl.set_editor_property("direction", d)
        tl.set_editor_property("count", n)
        lanes_t.append(tl)
    traffic.set_editor_property("lanes", lanes_t)
    traffic.set_editor_property("min_x", float(ROAD_X0))
    traffic.set_editor_property("max_x", float(ROAD_X1))
    traffic.set_editor_property("speed", 650.0)
    fleet = [("AutoMumbai", 0.0), ("AutoMumbai", 0.0), ("AutoMumbai", 0.0), ("TaxiKaaliPeeli2", 0.0), ("TaxiKaaliPeeli2", 0.0),
             ("TaxiKaaliPeeli2", 0.0), ("BusBEST", 180.0), ("ScooterActiva", 0.0), ("ScooterActiva", 0.0), ("BikePulsar135", 180.0),
             ("CarWagonR", 180.0)]
    fleet = [(mesh(n), y) for n, y in fleet if mesh(n)]
    traffic.set_editor_property("vehicle_meshes", [m for m, _ in fleet])
    traffic.set_editor_property("vehicle_mesh_yaws", [float(y) for _, y in fleet])

    # Mumbai locals on both tracks: crowds hanging out of the doors, nobody on the roof
    for ty, speed, x0 in ((TRACK_Y[0], 900.0, -20000.0), (TRACK_Y[1], -850.0, 15000.0)):
        tr = spawn(unreal.GITrain, unreal.Vector(x0, ty, 15), label="LocalTrain")
        tr.set_editor_property("speed", speed)
        tr.set_editor_property("track_start_x", -34000.0)
        tr.set_editor_property("track_end_x", 34000.0)
        tr.set_editor_property("crowd_share", 0.18)
        tr.set_editor_property("door_riders_only", True)

    # chai tapri on the main road by the market
    chai = spawn(unreal.GIChaiStall, CHAI, unreal.Rotator(roll=0, pitch=0, yaw=0), label="ChaiStall")
    vendor = load("/Game/Characters/SK_ManStriped/SK_ManStriped")
    if vendor:
        chai.set_editor_property("vendor_mesh", vendor)
    for prop, n in (("kettle_mesh", "Prop_Kettle"), ("glass_mesh", "Prop_ChaiGlass")):
        m = mesh(n)
        if m:
            chai.set_editor_property(prop, m)
    props.append(("Chai_Stall", CHAI.x, CHAI.y, 0, 0, 1.0))
    for i in range(3):
        props.append(("Plastic_Stool", CHAI.x - 220 + i * 150, CHAI.y - 260, 0, R.uniform(0, 360), 1.0))
        spots.append({"loc": (CHAI.x - 260 + i * 170, CHAI.y - 300, 0), "yaw": 90 + R.uniform(-30, 30), "mode": "Talk", "priority": 1.5})

    # monsoon
    w = spawn(unreal.GIWeather, unreal.Vector(0, 0, 0), label="Weather")
    w.set_editor_property("rain_material", load(f"{MAT_DIR}/M_Rain"))
    w.set_editor_property("weather_collection", load(f"{MAT_DIR}/MPC_Weather"))
    w.set_editor_property("rain_loop", load(f"{ROOT}/Audio/A_Rain"))
    w.set_editor_property("thunder_sound", load(f"{ROOT}/Audio/S_Thunder"))
    w.set_editor_property("umbrella_meshes", [m for m in (mesh(f"Umbrella_{c}") for c in ("Red", "Yellow", "Blue", "Green", "Black", "Pink")) if m])

    # walk-around: the lane and the kids, the market, chai on the main road, the monsoon
    mission = spawn(unreal.GIMission, unreal.Vector(0, 0, 0), label="Mission")
    objs = []
    for text, done, kind, loc, radius, reward in (
            ("Gali ke aakhir tak chalo - bachche cricket khel rahe hain.", "Dharavi ki gali!", unreal.GIObjectiveKind.REACH,
             unreal.Vector(2700, 0, 0), 350, 0),
            ("Ball tumhari taraf aaye to wapas phenko (E).", "Bachche khush! +₹50", unreal.GIObjectiveKind.RETURN_BALL,
             unreal.Vector(3350, 0, 0), 300, 50),
            ("Sabzi mandi se hote hue main road pe chai ki tapri dhoondo - ek cutting chai lo (E).", "Garam chai! +10 HP",
             unreal.GIObjectiveKind.CHAI, unreal.Vector(CHAI.x, CHAI.y - 250, 0), 300, 0),
            ("Main road pe chalo. Baadal ghir aaye hain...", "Mumbai ki baarish! Rain or shine, grind chalta rahega.",
             unreal.GIObjectiveKind.MONSOON, unreal.Vector(CHAI.x + 2500, ROAD_C + 900, 0), 900, 100)):
        o = unreal.GIObjective()
        o.set_editor_property("text", text)
        o.set_editor_property("done_banner", done)
        o.set_editor_property("kind", kind)
        o.set_editor_property("location", loc)
        o.set_editor_property("radius", float(radius))
        o.set_editor_property("reward", reward)
        objs.append(o)
    mission.set_editor_property("tour_title", "Mumbai: [Dharavi ki Galiyan]")
    mission.set_editor_property("objectives", objs)
    mission.set_editor_property("title_cam_start", unreal.Vector(-300, -20, 160))
    mission.set_editor_property("title_cam_end", unreal.Vector(300, -20, 170))
    mission.set_editor_property("title_cam_look_at", unreal.Vector(2500, 0, 150))

    crowd = spawn(unreal.GICrowdManager, unreal.Vector(0, 0, 0), label="Crowd")
    crowd.set_editor_property("ambient_category", "mumbai")
    lane_structs = []
    for l in lanes:
        wl = unreal.GIWalkLane()
        wl.set_editor_property("start", unreal.Vector(*l["start"]))
        wl.set_editor_property("end", unreal.Vector(*l["end"]))
        wl.set_editor_property("width", float(l["width"]))
        wl.set_editor_property("weight", float(l["weight"]))
        lane_structs.append(wl)
    crowd.set_editor_property("lanes", lane_structs)
    modes = {"Sit": unreal.GIPoseMode.SIT, "Locomotion": unreal.GIPoseMode.LOCOMOTION, "Talk": unreal.GIPoseMode.TALK,
             "SitTalk": unreal.GIPoseMode.SIT_TALK, "Wash": unreal.GIPoseMode.WASH, "StandArmsOut": unreal.GIPoseMode.STAND_ARMS_OUT}
    cell = {}
    for (name, x, y, z, yaw, sc_) in props:
        if name.startswith(("Drum_", "LPG_", "Bicycle", "Sack_", "Matka", "Veg_Cart", "VegCartModel", "StallModel", "Snack_",
                            "Plastic_", "Wooden_", "Electric_", "Chai_", "Dog", "Garbage_", "PH_island", "Pandal_", "Ganpati")):
            cell.setdefault((int(x // 200), int(y // 200)), []).append((x, y, 150.0 if name.startswith(("Veg", "Stall", "Snack", "Pandal", "Chai")) else 90.0))

    def blocked(x, y):
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for (px, py, r) in cell.get((int(x // 200) + i, int(y // 200) + j), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < r * r:
                        return True
        return False
    kept = [s for s in spots if s["priority"] >= 1.5 or not blocked(s["loc"][0], s["loc"][1])]
    log("spots kept", len(kept), "of", len(spots))
    spot_structs = []
    for s in kept:
        p = unreal.GIStaticSpot()
        p.set_editor_property("location", unreal.Vector(*s["loc"]))
        p.set_editor_property("yaw", float(s["yaw"]))
        p.set_editor_property("mode", modes[s["mode"]])
        p.set_editor_property("priority", float(s["priority"]))
        spot_structs.append(p)
    crowd.set_editor_property("spots", spot_structs)
    log("mumbai crowd lanes", len(lane_structs), "spots", len(spot_structs))


def place(sc, props):
    for (name, x, y, z, yaw, s) in props:
        if not mesh(name):
            continue
        cull = 9000.0 if name.startswith(("PH_grass", "Litter_", "Trial_Slippers", "Drum_", "LPG_", "Plastic_", "Dog", "Bicycle",
                                          "Matka", "Sack_", "Garbage_")) else 0.0
        collision = not name.startswith(("Trial_Laundry", "Laundry_", "Wire_", "Neon_", "Tarp_", "PH_grass", "Litter_", "Dog",
                                         "Festoon_", "Road_Zebra", "Garbage_"))
        roll = 7.0 if name == "BicycleIndian" else 0.0
        sc.add(name, xf(x, y, z, yaw, s, roll=roll), collision=collision, cull=cull, shadow=not name.startswith(("Litter_", "Road_Zebra")))


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
    ground, houses, city, props_sc, sky = Scatter("Ground"), Scatter("Houses"), Scatter("City"), Scatter("Props"), Scatter("Skyline")
    props, spots, lanes = [], [], []
    build_ground(ground)
    build_trial_core(houses, props)
    build_gallis(houses, props, spots, lanes)
    build_chawl(city, props, spots, lanes)
    build_market(city, props, spots, lanes)
    build_main_road(city, props, spots, lanes)
    build_rail(city, props, spots, lanes)
    build_boundary(city, props)
    build_skyline(sky)
    for sc in (ground, houses, city, sky):
        sc.spawn()
    build_lighting_mumbai()
    build_gameplay(lanes, spots, props)
    place(props_sc, props)
    props_sc.spawn()
    les.save_current_level()
    log("level saved", MAP)


main()
