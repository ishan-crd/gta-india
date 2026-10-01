"""Build /Game/Maps/Dharavi - Mumbai's Dharavi, after the reference clip:
  * a busy MAIN ROAD (shops with neon signs, blue tarps, chai tapri, veg carts, autos/scooters) - where the
    monsoon breaks at the end;
  * a concrete GATEWAY into the slum: a grid of narrow gallis lined with one-storey sky-blue / teal
    shanties (laundry lines across, blue drums, bicycles, stray dogs), corrugated-sheet shacks, denser
    3-4 storey tenements (wires, tarps, water tanks) and a wide CHAWL LANE;
  * kids playing gully cricket (a small square and the chawl lane), a pottery / recycling corner.
Reuses the helpers of 05_build_level.py (Scatter, mesh, xf, spawn, trace_z, text_sign, lighting).
Coordinates in cm, ground at Z = 0, X east along the main road, Y north into the slum.
"""
import math
import os
import random
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "05_build_level.py")).read().replace("\nmain()\n", "\n")
exec(compile(_src, "05_build_level.py", "exec"))  # noqa - brings Scatter, mesh, xf, spawn, ... and gi_common

MAP = "/Game/Maps/Dharavi"
DH = f"{ROOT}/Dharavi"
MAT_DIR = f"{ROOT}/Materials"
R = random.Random(20261002)

# ------------------------------------------------------------------------------------------ layout
ROAD_HALF = 700            # main road Y -700..700
SHOP_Y = 1100              # facades of the main-road rows
ROAD_X0, ROAD_X1 = -26000, 26000
SLUM_X0, SLUM_X1 = -14000, 14000
LANES_Y = [(3400, 320), (5800, 320), (8200, 700), (10600, 320), (13000, 320)]   # E-W gallis (centre Y, width)
CROSS_X = [-12000, -9000, -6000, -3000, 0, 3000, 6000, 9000, 12000]               # N-S alleys
CROSS_W = 300
LAUNDRY_Z = 0              # laundry / wire props carry their hook height in the mesh (pivot at the ground)
GATE = unreal.Vector(0, 1500, 0)
SQUARE = (-4600, -1400, 3700, 5300)        # kids' cricket square (x0, x1, y0, y1), kept open
CHAI = unreal.Vector(-3200, 960, 0)
PLAYER_START = unreal.Vector(0, 450, 110)
CRICKET_LANE = (4200, 8200)                # chawl-lane cricket (batsman x, lane y)

SHANTY_1F = [f"Shanty_1F_{i:02d}" for i in range(1, 9)]
SHANTY_2F = [f"Shanty_2F_{i:02d}" for i in range(1, 7)]
TENEMENT = [f"Tenement_3F_{i:02d}" for i in range(1, 7)] + [f"Tenement_4F_{i:02d}" for i in range(1, 5)]
SHACKS = [f"Shack_Corrugated_{i:02d}" for i in range(1, 5)]
TOWN = [f"Bldg_Town_{i:02d}" for i in range(1, 9)]


def in_square(x, y, pad=0):
    return SQUARE[0] - pad < x < SQUARE[1] + pad and SQUARE[2] - pad < y < SQUARE[3] + pad


def near_cross(x0, x1):
    return any(x0 < cx + CROSS_W / 2 + 40 and x1 > cx - CROSS_W / 2 - 40 for cx in CROSS_X)


def zone_names(x, y):
    """Building style by area: blue shanties west (the clip's opening), shacks north-west, tenements
    east / on the chawl lane, mixed in the middle."""
    if abs(y - 8200) < 600 and x > -2000:
        return TENEMENT
    if x < -4000 and y < 9000:
        return SHANTY_1F * 3 + SHANTY_2F
    if x < -4000:
        return SHACKS * 2 + SHANTY_1F + SHANTY_2F
    if x > 5000:
        return TENEMENT * 2 + SHANTY_2F
    return SHANTY_1F + SHANTY_2F * 2 + TENEMENT + SHACKS


def row(sc, props, y_facade, yaw, x0, x1, names_fn, lane_spots, lane_y, spots):
    """A run of buildings along a lane; yaw 0 = facade faces -Y, 180 = faces +Y."""
    x = x0
    while x < x1:
        names = names_fn(x, y_facade)
        n = R.choice(names)
        w = size_of(n).x or 500.0
        if near_cross(x, x + w) or in_square(x + w / 2, y_facade, 300):
            x += 120
            continue
        cx = x + w / 2
        sc.add(n, xf(cx, y_facade + R.uniform(-25, 25), 0, yaw + R.uniform(-1.2, 1.2)))
        side = -1 if yaw == 0 else 1           # towards the lane
        # doorstep life: someone sitting on the ota, a drum, a bicycle, meters on the wall
        fy = y_facade + side * 70
        if R.random() < 0.35:
            spots.append({"loc": (cx + R.uniform(-w * 0.3, w * 0.3), fy, 0), "yaw": (-90 if side < 0 else 90) + R.uniform(-30, 30),
                          "mode": R.choice(["Sit", "SitTalk", "Talk"]), "priority": 0.5})
        if R.random() < 0.45:
            props.append(("Drum_Blue", cx + R.uniform(-w * 0.4, w * 0.4), y_facade + side * R.uniform(45, 90), 0, R.uniform(0, 360), 1.0))
        if R.random() < 0.18:
            props.append(("BicycleIndian", cx + R.uniform(-w * 0.3, w * 0.3), y_facade + side * 55, 0, R.choice([0, 180]) + R.uniform(-8, 8), 1.0))
        if R.random() < 0.2:
            props.append(("ElecMeter", cx + R.uniform(-w * 0.4, w * 0.4), y_facade + side * 6, 160, yaw, 1.0))
        if R.random() < 0.12:
            props.append(("LPG_Cylinder", cx + R.uniform(-w * 0.4, w * 0.4), y_facade + side * 50, 0, R.uniform(0, 360), 1.0))
        x += w + (R.uniform(10, 60) if R.random() < 0.8 else R.uniform(120, 300))


def build_ground(sc):
    for gx in range(-30000, 30001, 2000):
        for gy in (-1000, 1000):
            sc.add("Ground_Tile_20m", xf(gx, gy, -2), mats=("MI_Asphalt",))
        for gy in (-3000, 3000):
            sc.add("Ground_Tile_20m", xf(gx, gy, -2), mats=("MI_Concrete",))
        for gy in range(-7000, -4999, 2000):
            sc.add("Ground_Tile_20m", xf(gx, gy, -2), mats=("MI_Concrete",))
    for gx in range(SLUM_X0 - 4000, SLUM_X1 + 4001, 2000):
        for gy in range(5000, 17001, 2000):
            sc.add("Ground_Tile_20m", xf(gx, gy, -2), mats=(R.choice(["MI_Concrete", "MI_Concrete", "MI_MuddyTracks", "MI_GroundLitter"]),))


def build_main_road(sc, props, spots, lanes):
    # shop rows both sides (taller tenements + town shop-houses), sidewalks, tarps, neon, stalls, lights
    for side, yaw in ((1, 0.0), (-1, 180.0)):
        x = ROAD_X0
        while x < ROAD_X1:
            n = R.choice(TENEMENT + TOWN)
            w = size_of(n).x or 800.0
            if side > 0 and (abs(x + w / 2 - GATE.x) < w / 2 + 380 or abs(x + w / 2 - CHAI.x) < w / 2 + 250):
                x += 200
                continue
            fy = side * SHOP_Y
            sc.add(n, xf(x + w / 2, fy, 0, yaw), mats=sign_mats(n) if n.startswith("Bldg_Town") else None)
            if R.random() < 0.55:   # neon / backlit sign over the shop
                props.append((f"Neon_Sign_{R.randint(1, 6):02d}", x + w / 2 + R.uniform(-w * 0.2, w * 0.2), fy - side * 40,
                              R.uniform(330, 520), yaw, 1.0))
            if R.random() < 0.5:
                props.append((R.choice(["Tarp_Canopy_3m", "Tarp_Canopy_5m"]), x + w / 2, fy - side * 160, 0, yaw, 1.0))
            x += w + R.uniform(0, 60)
        # street lights (switched on by the weather) + poles
        for lx in range(ROAD_X0 + 1000, ROAD_X1, 2600):
            y = side * (ROAD_HALF + 120)
            props.append(("Electric_Pole", lx, y, 0, 0 if side > 0 else 180, 1.0))
            light = spawn(unreal.PointLight, unreal.Vector(lx, y - side * 150, 760), label="StreetLight")
            light.tags = ["StreetLight"]
            lc = light.get_component_by_class(unreal.PointLightComponent)
            lc.set_editor_property("intensity", 0.0)
            lc.set_editor_property("attenuation_radius", 1800.0)
            lc.set_editor_property("light_color", unreal.Color(170, 210, 255, 255))
            lc.set_editor_property("cast_shadows", False)
            lc.set_editor_property("visible", False)
    # sidewalk life: veg carts, stalls, stools, vendors, crowd
    for i in range(70):
        side = R.choice([-1, 1])
        x = R.uniform(ROAD_X0 + 1500, ROAD_X1 - 1500)
        if side > 0 and (abs(x - GATE.x) < 600 or abs(x - CHAI.x) < 600):
            continue
        y = side * R.uniform(760, 900)
        kind = R.random()
        if kind < 0.3:
            props.append((R.choice(["Veg_Cart", "VegCartModel"]), x, y, 0, 90 * side + R.uniform(-15, 15), 1.0))
            spots.append({"loc": (x + 120, y + side * 80, 0), "yaw": -90 * side, "mode": "Talk", "priority": 0.8})
        elif kind < 0.5:
            props.append(("StallModel", x, y + side * 60, 0, 0 if side > 0 else 180, 1.0))
        elif kind < 0.7:
            props.append(("Sack_Pile_0%d" % R.randint(1, 3), x, y + side * 80, 0, R.uniform(0, 360), 1.0))
        else:
            props.append((R.choice(["Plastic_Stool", "Wooden_Bench", "Matka_Stack", "Drum_Blue"]), x, y, 0, R.uniform(0, 360), 1.0))
    for gx in range(ROAD_X0, ROAD_X1, 6000):
        for y, w in ((820, 1.6), (-820, 1.4), (300, 0.25), (-300, 0.2)):
            lanes.append({"start": (gx, y, 0), "end": (gx + 6000, y, 0), "width": 260, "weight": w})
    for i in range(160):
        side = R.choice([-1, 1])
        spots.append({"loc": (R.uniform(ROAD_X0 + 1000, ROAD_X1 - 1000), side * R.uniform(780, 950), 0), "yaw": R.uniform(-180, 180),
                      "mode": R.choice(["Talk", "Talk", "Locomotion", "Sit"]), "priority": 0.6})


def build_slum(sc, props, spots, lanes):
    for (ly, lw) in LANES_Y:
        # north side of the lane (facing -Y) and south side (facing +Y)
        row(sc, props, ly + lw / 2, 0.0, SLUM_X0, SLUM_X1, zone_names, None, ly, spots)
        row(sc, props, ly - lw / 2, 180.0, SLUM_X0, SLUM_X1, zone_names, None, ly, spots)
        lanes.append({"start": (SLUM_X0, ly, 0), "end": (SLUM_X1, ly, 0), "width": lw * 0.6, "weight": 0.8 if lw > 400 else 0.5})
        # laundry and wires across the galli, litter, dogs
        x = SLUM_X0 + 300
        while x < SLUM_X1:
            if not near_cross(x - 200, x + 200) and not in_square(x, ly, 200):
                r = R.random()
                # keep the cricket lane clear of low laundry (the kids need the space, you need the view)
                if r < 0.45 and lw < 400:
                    props.append((R.choice(["Laundry_Line_6m", "Laundry_Line_6m", "Laundry_Line_10m"]), x, ly, LAUNDRY_Z, 90 + R.uniform(-12, 12), 1.0))
                elif r < 0.65:
                    props.append(("Wire_Bundle_Alley", x, ly, 0, 90 + R.uniform(-15, 15), 1.0))
            x += R.uniform(380, 900)
    for cx in CROSS_X:
        lanes.append({"start": (cx, 1300 if cx == 0 else 2800, 0), "end": (cx, 13500, 0), "width": CROSS_W * 0.6, "weight": 0.35})
    # gateway into the slum, straight off the main road
    props.append(("Gateway_Concrete", GATE.x, GATE.y, 0, 0, 1.0))
    # the kids' square: open ground with a dog, bicycles, drums
    props.append(("DogLying", SQUARE[0] + 300, SQUARE[2] + 260, 0, 30, 1.0))
    props.append(("BicycleIndian", SQUARE[1] - 200, SQUARE[3] - 150, 0, 15, 1.0))
    props.append(("Drum_Blue", SQUARE[0] + 120, SQUARE[3] - 120, 0, 0, 1.0))
    # pottery (Kumbharwada) + recycling corner, north-east
    for i in range(70):
        x, y = R.uniform(6200, 11800), R.uniform(2400, 5300)
        if near_cross(x - 60, x + 60) or any(abs(y - ly) < lw / 2 + 60 for ly, lw in LANES_Y):
            continue
        props.append((R.choice(["Matka_Stack", "MatkaModel", "Matka_Stack", "Sack_Pile_01", "Sack_Pile_02", "Sack_Pile_03"]), x, y, 0, R.uniform(0, 360), 1.0))
    # dogs about
    for i in range(18):
        ly, lw = R.choice(LANES_Y)
        props.append((R.choice(["DogLying", "DogLying", "DogStanding", "DogStanding2"]), R.uniform(SLUM_X0, SLUM_X1),
                      ly + R.choice([-1, 1]) * (lw / 2 - 50), 0, R.uniform(0, 360), 1.0))
    # people in the gallis
    for i in range(420):
        ly, lw = R.choice(LANES_Y)
        x = R.uniform(SLUM_X0, SLUM_X1)
        spots.append({"loc": (x, ly + R.uniform(-lw / 3, lw / 3), 0), "yaw": R.uniform(-180, 180),
                      "mode": R.choice(["Talk", "Talk", "Locomotion", "Wash", "Sit"]), "priority": 0.45})


def build_litter(sc):
    def patch(x, y, s=None):
        sc.add(R.choice(LITTER), xf(x, y, 1, R.uniform(0, 360), s or R.uniform(0.7, 1.2)), collision=False, cull=6000.0, shadow=False)
    for i in range(1600):
        ly, lw = R.choice(LANES_Y)
        patch(R.uniform(SLUM_X0, SLUM_X1), ly + R.uniform(-lw / 2, lw / 2) * 0.9)
    for i in range(1400):
        patch(R.uniform(ROAD_X0, ROAD_X1), R.choice([-1, 1]) * R.uniform(560, 900))
    for i in range(70):
        ly, lw = R.choice(LANES_Y)
        sc.add(R.choice(["Garbage_Heap_0", "Garbage_Heap_1", "Garbage_Heap_2"]), xf(R.uniform(SLUM_X0, SLUM_X1), ly + R.choice([-1, 1]) * lw * 0.35, 0,
               R.uniform(0, 360), R.uniform(0.5, 0.9)), collision=False, cull=12000.0)


def build_dharavi_lighting():
    build_lighting()
    # a sunny Mumbai morning: higher, whiter sun than the Varanasi golden hour, light haze
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight):
            a.set_actor_rotation(unreal.Rotator(roll=0, pitch=-38, yaw=125), False)
            lc = a.get_component_by_class(unreal.DirectionalLightComponent)
            lc.set_editor_property("intensity", 10.0)
            lc.set_editor_property("temperature", 5600.0)
        elif isinstance(a, unreal.ExponentialHeightFog):
            fc = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
            fc.set_editor_property("fog_density", 0.02)
            fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.5, 0.52, 0.55, 1))


def build_gameplay(lanes, spots, props):
    spawn(unreal.PlayerStart, PLAYER_START, unreal.Rotator(roll=0.0, pitch=0.0, yaw=90.0), label="PlayerStart")
    sc_mesh = mesh("ScooterActiva")
    if sc_mesh:
        v = spawn(unreal.GIBike, unreal.Vector(600, 520, 90), unreal.Rotator(0, 0, 0), label="Drivable_Scooter")
        v.set_editor_property("mesh_override", sc_mesh)
        v.set_editor_property("mesh_yaw_override", 0.0)
    am = mesh("AutoMumbai")
    if am:
        v = spawn(unreal.GIBike, unreal.Vector(-1200, -520, 95), unreal.Rotator(0, 180, 0), label="Drivable_Auto")
        v.set_editor_property("mesh_override", am)
        v.set_editor_property("mesh_yaw_override", 0.0)
        v.set_editor_property("four_wheeler", True)

    # traffic on the main road (Mumbai keeps left: heading +X the left side is +Y)
    traffic = spawn(unreal.GITraffic, unreal.Vector(0, 0, 0), label="Traffic")
    lanes_t = []
    for y, d, n in ((330, 1.0, 12), (-330, -1.0, 12)):
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
    fleet = [("AutoMumbai", 0.0), ("AutoMumbai", 0.0), ("AutoMumbai", 0.0), ("ScooterActiva", 0.0), ("ScooterActiva", 0.0),
             ("BikePulsar135", 180.0), ("CarWagonR", 180.0), ("CarNano", 180.0)]
    fleet = [(mesh(n), y) for n, y in fleet if mesh(n)]
    traffic.set_editor_property("vehicle_meshes", [m for m, _ in fleet])
    traffic.set_editor_property("vehicle_mesh_yaws", [float(y) for _, y in fleet])

    # chai tapri on the main road
    chai = spawn(unreal.GIChaiStall, CHAI, unreal.Rotator(0, 0, 0), label="ChaiStall")
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

    # kids' cricket: the square and the chawl lane
    kid_meshes = [load(f"/Game/Characters/{n}/{n}") for n in ("SK_Teen", "SK_BoyKurta", "SK_Teen", "SK_BoyKurta", "SK_ManPolo", "SK_ManShirt")]
    kid_meshes = [m for m in kid_meshes if m]
    for label, loc, yaw, pitch_len, half_w, fielders in (
            ("Cricket_Square", unreal.Vector(SQUARE[0] + 350, (SQUARE[2] + SQUARE[3]) / 2, 0), 0.0, 1400.0, 600.0, 5),
            ("Cricket_ChawlLane", unreal.Vector(CRICKET_LANE[0], CRICKET_LANE[1], 0), 0.0, 1600.0, 330.0, 6)):
        g = spawn(unreal.GICricketGame, loc, unreal.Rotator(0, yaw, 0), label=label)
        g.set_editor_property("kid_meshes", kid_meshes)
        for prop, n in (("stumps_mesh", "Cricket_Stumps"), ("bat_mesh", "Cricket_Bat"), ("ball_mesh", "Cricket_Ball")):
            m = mesh(n)
            if m:
                g.set_editor_property(prop, m)
        g.set_editor_property("pitch_length", pitch_len)
        g.set_editor_property("lane_half_width", half_w)
        g.set_editor_property("num_fielders", fielders)

    # weather
    w = spawn(unreal.GIWeather, unreal.Vector(0, 0, 0), label="Weather")
    w.set_editor_property("rain_material", load(f"{MAT_DIR}/M_Rain"))
    w.set_editor_property("weather_collection", load(f"{MAT_DIR}/MPC_Weather"))
    w.set_editor_property("rain_loop", load(f"{ROOT}/Audio/A_Rain"))
    w.set_editor_property("thunder_sound", load(f"{ROOT}/Audio/S_Thunder"))
    w.set_editor_property("umbrella_meshes", [m for m in (mesh(f"Umbrella_{c}") for c in ("Red", "Yellow", "Blue", "Green", "Black", "Pink")) if m])

    # walk-around mission
    mission = spawn(unreal.GIMission, unreal.Vector(0, 0, 0), label="Mission")
    objs = []
    for text, done, kind, loc, radius, reward in (
            ("Darwaze se Dharavi ki galiyon mein ghuso.", "Dharavi! Yahan sab chalta hai.", unreal.GIObjectiveKind.REACH,
             unreal.Vector(-2900, 3400, 0), 500, 0),
            ("Main road pe chai ki tapri dhoondo - ek cutting chai lo (E).", "Garam chai! +10 HP", unreal.GIObjectiveKind.CHAI,
             unreal.Vector(CHAI.x, CHAI.y - 250, 0), 300, 0),
            ("Chawl wali gali mein bachche cricket khel rahe hain. Unki ball wapas karo (E).", "Bachche khush! +₹50", unreal.GIObjectiveKind.RETURN_BALL,
             unreal.Vector(CRICKET_LANE[0] + 800, CRICKET_LANE[1], 0), 300, 50),
            ("Wapas main road pe jao. Baadal ghir aaye hain...", "Mumbai ki baarish! Rain or shine, grind chalta rahega.", unreal.GIObjectiveKind.MONSOON,
             unreal.Vector(7000, 0, 0), 900, 100)):
        o = unreal.GIObjective()
        o.set_editor_property("text", text)
        o.set_editor_property("done_banner", done)
        o.set_editor_property("kind", kind)
        o.set_editor_property("location", loc)
        o.set_editor_property("radius", float(radius))
        o.set_editor_property("reward", reward)
        objs.append(o)
    mission.set_editor_property("tour_title", "Mission: [Dharavi ki Galiyan]")
    mission.set_editor_property("objectives", objs)
    mission.set_editor_property("title_cam_start", unreal.Vector(-6000, -500, 900))
    mission.set_editor_property("title_cam_end", unreal.Vector(4000, -300, 1300))
    mission.set_editor_property("title_cam_look_at", unreal.Vector(0, 3500, 300))

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
             "SitTalk": unreal.GIPoseMode.SIT_TALK, "Wash": unreal.GIPoseMode.WASH}
    spot_structs = []
    for s in spots:
        p = unreal.GIStaticSpot()
        p.set_editor_property("location", unreal.Vector(*s["loc"]))
        p.set_editor_property("yaw", float(s["yaw"]))
        p.set_editor_property("mode", modes[s["mode"]])
        p.set_editor_property("priority", float(s["priority"]))
        spot_structs.append(p)
    crowd.set_editor_property("spots", spot_structs)
    log("dharavi crowd lanes", len(lane_structs), "spots", len(spot_structs))
    text_sign("DHARAVI", unreal.Vector(GATE.x, GATE.y - 60, 380), -90, 60, (1.0, 0.95, 0.85))


def place(sc, props):
    for (name, x, y, z, yaw, s) in props:
        m = mesh(name)
        if not m:
            continue
        if z is None:
            z = trace_z(x, y) or 0.0
        cull = 0.0
        if name.startswith(("PH_", "Garbage_", "Dog", "Drum_", "LPG_", "Plastic_", "ElecMeter", "Matka", "Bicycle")):
            cull = 9000.0
        collision = not name.startswith(("Laundry_", "Wire_", "Neon_", "Tarp_", "Dog", "ElecMeter"))
        sc.add(name, xf(x, y, z, yaw, s), collision=collision, cull=cull)


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
    ground, city, props_sc, litter = Scatter("Ground"), Scatter("Buildings"), Scatter("Props"), Scatter("Litter")
    props, spots, lanes = [], [], []
    build_ground(ground)
    build_main_road(city, props, spots, lanes)
    build_slum(city, props, spots, lanes)
    build_litter(litter)
    for sc in (ground, city, litter):
        sc.spawn()
    build_dharavi_lighting()
    build_gameplay(lanes, spots, props)
    place(props_sc, props)
    props_sc.spawn()
    les.save_current_level()
    log("level saved", MAP)


main()
