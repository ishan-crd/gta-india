"""Village / railway-side pieces matching the reference clip: low 1-2 storey village houses, tin-roof
shop sheds, the ghat-top parapet with small domed kiosks, and the suburban EMU coach (off-white body,
purple band, open doors, barred windows) that the crowd rides on.
"""
import math
from kit_core import MB, V, T, lerp
from kit_arch import chhatri, awning_corrugated
import kit_buildings as KB

# ----------------------------------------------------------------------------------------- EMU coach
EMU_L = 21.3          # body length (m)
EMU_W = 3.66          # body width
FLOOR = 1.22          # floor / underside of body
CANT = 3.95           # top of side wall
ROOF = 4.32           # roof crown
DOOR_W = 1.3
DOOR_H = 2.05
DOOR_X = (-7.0, 0.0, 7.0)         # door centres (both sides); GITrain hangs riders here
WIN_SILL = 2.15
WIN_TOP = 3.12
WIN_W = 1.05


def _intervals_minus(a, b, cuts):
    out = [(a, b)]
    for (c0, c1) in cuts:
        nxt = []
        for (u0, u1) in out:
            if c1 <= u0 or c0 >= u1:
                nxt.append((u0, u1))
                continue
            if c0 > u0:
                nxt.append((u0, c0))
            if c1 < u1:
                nxt.append((c1, u1))
        out = nxt
    return [(u0, u1) for (u0, u1) in out if u1 - u0 > 1e-3]


def _emu_side(mb, side, x0, x1):
    """One side wall (side = -1 / +1 in Y): panels around door and window openings, recessed glass-less
    barred windows, purple skirt + waist stripe on grimy off-white, door handrails."""
    y = side * EMU_W / 2
    t = 0.07 * side
    doors = [(dx - DOOR_W / 2, dx + DOOR_W / 2) for dx in DOOR_X]
    # windows: evenly spaced in each panel between doors / ends
    wins = []
    edges = [x0 + 0.9] + [v for d in doors for v in d] + [x1 - 0.9]
    for i in range(0, len(edges), 2):
        a, b = edges[i] + 0.35, edges[i + 1] - 0.35
        n = max(1, int((b - a) / 1.55))
        step = (b - a) / n
        for k in range(n):
            c = a + step * (k + 0.5)
            wins.append((c - WIN_W / 2, c + WIN_W / 2))
    yo, yi = (y, y - t) if side > 0 else (y - t, y)
    yo, yi = min(y, y - t), max(y, y - t)

    def band(z0, z1, mat, cuts):
        for (u0, u1) in _intervals_minus(x0, x1, cuts):
            mb.box(u0, yo, z0, u1, yi, z1, mat)
    # skirt (purple), lower white, waist stripe, window band piers, upper white, cant stripe
    band(FLOOR, FLOOR + 0.42, 'M_TrainPurple', doors)
    band(FLOOR + 0.42, WIN_SILL - 0.12, 'M_TrainWhite', doors)
    band(WIN_SILL - 0.12, WIN_SILL, 'M_TrainPurple', doors)
    band(WIN_SILL, WIN_TOP, 'M_TrainWhite', doors + wins)
    band(WIN_TOP, FLOOR + DOOR_H, 'M_TrainWhite', doors)
    band(FLOOR + DOOR_H, CANT - 0.16, 'M_TrainWhite', [])
    band(CANT - 0.16, CANT, 'M_TrainPurple', [])
    # window recesses: dark interior card, sill, bars
    ins = -side * 0.22
    for (a, b) in wins:
        mb.box(a, y + ins - 0.02 * side, WIN_SILL, b, y + ins, WIN_TOP, 'M_WindowDark')
        mb.box(a, min(y, y + ins), WIN_SILL - 0.02, b, max(y, y + ins), WIN_SILL, 'M_Steel')
        for k in range(7):
            bx = lerp(a + 0.06, b - 0.06, k / 6)
            mb.box(bx - 0.008, y - 0.03 * side - 0.008, WIN_SILL, bx + 0.008, y - 0.03 * side + 0.008, WIN_TOP, 'M_Steel')
        for zz in (WIN_SILL + 0.3, WIN_SILL + 0.62):
            mb.box(a, y - 0.03 * side - 0.008, zz - 0.008, b, y - 0.03 * side + 0.008, zz + 0.008, 'M_Steel')
    # door openings: dark vestibule, floor plate, jambs, two vertical grab poles
    for (a, b) in doors:
        mb.box(a, -side * 0.4, FLOOR, b, -side * 0.38, FLOOR + DOOR_H, 'M_WindowDark')
        mb.box(a, min(y, -side * 0.4), FLOOR - 0.04, b, max(y, -side * 0.4), FLOOR, 'M_Steel')
        for xx in (a, b):
            mb.box(xx - 0.04, min(y, y - t * 3), FLOOR, xx + 0.04, max(y, y - t * 3), FLOOR + DOOR_H, 'M_Steel')
            mb.rod((xx + (0.12 if xx == a else -0.12), y - 0.06 * side, FLOOR + 0.25),
                   (xx + (0.12 if xx == a else -0.12), y - 0.06 * side, FLOOR + DOOR_H - 0.1), 0.018, 'M_Steel', seg=6)
        # footstep below the door
        mb.box(a + 0.1, y, FLOOR - 0.38, b - 0.1, y + 0.22 * side, FLOOR - 0.33, 'M_Steel')


def _emu_roof(mb, x0, x1):
    prof = [(-EMU_W / 2, CANT), (-1.55, CANT + 0.17), (-1.0, ROOF - 0.05), (0.0, ROOF), (1.0, ROOF - 0.05), (1.55, CANT + 0.17),
            (EMU_W / 2, CANT)]
    for i in range(len(prof) - 1):
        (y0, z0), (y1, z1) = prof[i], prof[i + 1]
        mb.face([V(x0, y0, z0), V(x0, y1, z1), V(x1, y1, z1), V(x1, y0, z0)], 'M_TrainRoof', center=V((x0 + x1) / 2, 0, 0))
    # roof ventilators + rain gutters
    x = x0 + 1.6
    while x < x1 - 1.4:
        mb.cylinder(x, 0.0, ROOF - 0.04, ROOF + 0.16, 0.28, 10, 'M_Steel')
        mb.cylinder(x, 0.0, ROOF + 0.16, ROOF + 0.2, 0.34, 10, 'M_TrainRoof')
        x += 2.4
    for s in (-1, 1):
        mb.box(x0, s * EMU_W / 2 - 0.05, CANT - 0.02, x1, s * EMU_W / 2 + 0.05, CANT + 0.05, 'M_Steel')


def _emu_under(mb, x0, x1):
    # underframe + equipment boxes + bogies
    mb.box(x0 + 0.3, -1.3, FLOOR - 0.32, x1 - 0.3, 1.3, FLOOR, 'M_Steel')
    for (a, b) in ((-4.8, -1.6), (1.2, 3.8)):
        mb.box(a, -1.1, FLOOR - 0.85, b, 1.1, FLOOR - 0.32, 'M_MetalRust')
    for bx in (x0 + 3.2, x1 - 3.2):
        mb.box(bx - 1.6, -1.25, 0.55, bx + 1.6, 1.25, 0.95, 'M_Steel')
        for ax in (bx - 1.25, bx + 1.25):
            for s in (-1, 1):
                mb.rod((ax, s * 0.76, 0.46), (ax, s * 0.9, 0.46), 0.46, 'M_Steel', seg=14)
            mb.rod((ax, -0.76, 0.46), (ax, 0.76, 0.46), 0.08, 'M_Steel', seg=6)
        for s in (-1, 1):   # springs
            mb.cylinder(bx, s * 1.05, 0.95, FLOOR - 0.32, 0.14, 8, 'M_MetalRust')


def _emu_end(mb, x, sign, cab):
    """End wall at x (sign = +1 front / -1 rear). Cab ends get a purple nose, windscreens, lights."""
    hw = EMU_W / 2
    if not cab:
        mb.box(x - 0.06 * sign, -hw, FLOOR, x, hw, CANT, 'M_TrainWhite')
        # gangway bellows + end door
        mb.box(x, -0.55, FLOOR + 0.05, x + 0.32 * sign, 0.55, FLOOR + 2.15, 'M_WindowDark')
        mb.box(x - 0.02 * sign, -hw, FLOOR, x + 0.05 * sign, hw, FLOOR + 0.42, 'M_TrainPurple')
        # buffers / coupler
        for s in (-1, 1):
            mb.rod((x, s * 0.95, FLOOR - 0.15), (x + 0.4 * sign, s * 0.95, FLOOR - 0.15), 0.17, 'M_Steel', seg=10)
        mb.box(x, -0.18, FLOOR - 0.45, x + 0.45 * sign, 0.18, FLOOR - 0.15, 'M_Steel')
        return
    nose = 0.65 * sign
    # nose: lower block, slanted windscreen band, roof cap
    mb.hexa([V(x, -hw, FLOOR), V(x, hw, FLOOR), V(x + nose, hw - 0.15, FLOOR), V(x + nose, -hw + 0.15, FLOOR)],
            [V(x, -hw, 2.2), V(x, hw, 2.2), V(x + nose, hw - 0.15, 2.2), V(x + nose, -hw + 0.15, 2.2)], 'M_TrainPurple')
    mb.hexa([V(x, -hw, 2.2), V(x, hw, 2.2), V(x + nose, hw - 0.15, 2.2), V(x + nose, -hw + 0.15, 2.2)],
            [V(x, -hw, CANT), V(x, hw, CANT), V(x + 0.25 * sign, hw - 0.1, CANT), V(x + 0.25 * sign, -hw + 0.1, CANT)], 'M_WindowDark')
    # window pillars + destination board
    for yy in (-hw + 0.12, -0.06, hw - 0.18):
        mb.box(x + 0.25 * sign, yy, 2.2, x + 0.62 * sign, yy + 0.07, CANT - 0.25, 'M_TrainPurple')
    mb.box(x + 0.22 * sign, -1.1, CANT - 0.3, x + 0.3 * sign, 1.1, CANT, 'M_TrainPurple')
    # headlights + marker lamps + horn
    mb.cylinder(x + nose + 0.02 * sign, 0.0, CANT + 0.05, CANT + 0.3, 0.16, 10, 'M_Whitewash')
    for s in (-1, 1):
        mb.box(x + nose, s * 1.15 - 0.12, FLOOR + 0.62, x + nose + 0.04 * sign, s * 1.15 + 0.12, FLOOR + 0.8, 'M_Whitewash')
        mb.box(x + nose, s * 0.8 - 0.07, FLOOR + 0.62, x + nose + 0.04 * sign, s * 0.8 + 0.07, FLOOR + 0.76, 'M_Saffron')
    mb.box(x + nose, -0.25, FLOOR - 0.45, x + nose + 0.35 * sign, 0.25, FLOOR - 0.1, 'M_Steel')     # coupler
    mb.box(x, -hw + 0.1, FLOOR - 0.6, x + nose, hw - 0.1, FLOOR - 0.3, 'M_Steel')                 # cowcatcher


def asset_emu_car(cab=False):
    """EMU coach along X, wheel bottom (rail top) at z=0, centred; cab version has the driving nose at +X
    and a pantograph."""
    mb = MB()
    x0, x1 = -EMU_L / 2, EMU_L / 2
    mb.box(x0, -EMU_W / 2 + 0.07, FLOOR, x1, EMU_W / 2 - 0.07, FLOOR + 0.05, 'M_Steel')   # floor
    for s in (-1, 1):
        _emu_side(mb, s, x0, x1)
    _emu_roof(mb, x0, x1)
    _emu_under(mb, x0, x1)
    _emu_end(mb, x1, 1, cab)
    _emu_end(mb, x0, -1, False)
    if cab:
        px = x1 - 5.0
        for s in (-1, 1):
            mb.box(px - 1.0, s * 0.6 - 0.05, ROOF, px + 1.0, s * 0.6 + 0.05, ROOF + 0.25, 'M_Steel')
        mb.rod((px - 0.8, 0, ROOF + 0.25), (px, 0, ROOF + 1.2), 0.03, 'M_Steel')
        mb.rod((px, 0, ROOF + 1.2), (px + 0.8, 0, ROOF + 1.7), 0.03, 'M_Steel')
        mb.box(px + 0.5, -0.9, ROOF + 1.68, px + 1.1, 0.9, ROOF + 1.75, 'M_Steel')
    return mb, []


# ----------------------------------------------------------------------------------- village houses
def VILLAGE_VARIANTS():
    V_ = []
    V_.append(('Bldg_Village_01', 3101, 5.0, 7.0, 1, dict(mat='M_PlasterBlue', trim='M_PlasterWhite', shops=1, balc_floors=[],
               chhajja_floors=[], shop_kinds=['open'], awning=['corr'], roof_opts=dict(tanks=1, rebar=True, clothesline=True))))
    V_.append(('Bldg_Village_02', 3202, 6.5, 8.0, 2, dict(mat='M_PlasterPainted', trim='M_PlasterWhite', shops=2, balc_floors=[1],
               shop_kinds=['shutter_half', 'open'], awning=['corr', 'corr'], floor_mats={1: 'M_BrickPlaster'},
               roof_opts=dict(tanks=1, rebar=True))))
    V_.append(('Bldg_Village_03', 3303, 4.5, 6.5, 1, dict(mat='M_BrickPlaster', trim='M_PlasterWorn', shops=1, balc_floors=[],
               chhajja_floors=[], shop_kinds=['wood'], awning=['cloth'], parapet=None, roof_opts=dict(tanks=0, rebar=True))))
    V_.append(('Bldg_Village_04', 3404, 7.0, 8.5, 2, dict(mat='M_PlasterYellow', trim='M_PlasterWhite', shops=2, balc_floors=[1],
               balc_style='iron', shop_kinds=['shutter', 'open'], awning=['corr', 'cloth'], floor_mats={0: 'M_PlasterDamaged'},
               roof_opts=dict(tanks=2, clothesline=True))))
    V_.append(('Bldg_Village_05', 3505, 5.5, 7.5, 1, dict(mat='M_PlasterMossy', trim='M_PlasterBlue', shops=1, balc_floors=[],
               chhajja_floors=[], shop_kinds=['open'], awning=['corr'], roof_opts=dict(tanks=1, rebar=True, clothesline=True))))
    V_.append(('Bldg_Village_06', 3606, 6.0, 8.0, 2, dict(mat='M_BrickWhite', trim='M_PlasterRed', shops=1, balc_floors=[],
               chhajja_floors=[1], shop_kinds=['shutter_half'], awning=['corr'], extra_floor=dict(front=2.5, mat='M_BrickPlaster'))))
    V_.append(('Bldg_Village_07', 3707, 4.0, 6.0, 1, dict(mat='M_ClayPlaster', trim='M_PlasterWhite', shops=1, balc_floors=[],
               chhajja_floors=[], shop_kinds=['open'], awning=['cloth'], parapet=None, roof_opts=dict(tanks=0, clothesline=True))))
    V_.append(('Bldg_Village_08', 3808, 8.0, 8.0, 2, dict(mat='M_PlasterPeeling', trim='M_PlasterWhite', shops=3, balc_floors=[1],
               shop_kinds=['open', 'shutter_half', 'open'], awning=['corr', 'corr', 'cloth'], roof_opts=dict(tanks=2, rebar=True))))
    return V_


def asset_tin_shed(seed=1, w=3.2, d=2.6):
    """Roadside shop / tea stall lean-to: 4 bamboo + steel poles, rusty corrugated roof, a plank counter.
    Origin = front-centre at ground; opens towards -Y."""
    import random
    rng = random.Random(seed)
    mb = MB()
    hf, hb = 2.45 + rng.uniform(-0.1, 0.1), 2.85
    for (px, py, h) in ((-w / 2, -0.1, hf), (w / 2, -0.1, hf), (-w / 2, d, hb), (w / 2, d, hb)):
        mb.cylinder(px, py, 0, h, 0.045, 6, 'M_WoodPlanks' if rng.random() < 0.6 else 'M_MetalRust')
    awning_corrugated(mb, -w / 2 - 0.25, w / 2 + 0.25, hb + 0.04, dp=d + 0.55, drop=hb - hf + 0.05, y0=d + 0.15)
    # counter + crates + back cloth
    mb.box(-w / 2 + 0.15, 0.1, 0, w / 2 - 0.15, 0.7, 0.85, 'M_WoodPlanks')
    mb.box(-w / 2 + 0.1, 0.05, 0.85, w / 2 - 0.1, 0.75, 0.9, 'M_WoodPlanks')
    for i in range(rng.randint(2, 4)):
        cx = rng.uniform(-w / 2 + 0.4, w / 2 - 0.4)
        mb.boxc(cx, d - 0.4, 0, 0.5, 0.4, rng.uniform(0.3, 0.9), 'M_WoodPlanks')
    mb.box(-w / 2, d - 0.02, 0.0, w / 2, d + 0.02, hb - 0.2, 'M_Cloth' if rng.random() < 0.5 else 'M_CorrugatedRust')
    return mb, []


# ------------------------------------------------------------------------------- ghat-top parapet
def asset_ghat_parapet():
    """20 m low sandstone parapet along X at the top of the ghats (origin bottom-centre, river side -Y),
    with two small domed kiosks sitting on it like the reference (and a gap in the middle to walk through)."""
    mb = MB()
    hl = 10.0
    for (a, b) in ((-hl, -1.0), (1.0, hl)):
        mb.box(a, -0.35, 0, b, 0.35, 0.45, 'M_SandstoneRed')                 # plinth
        mb.box(a, -0.25, 0.45, b, 0.25, 1.05, 'M_Sandstone')                 # wall
        mb.box(a - 0.02, -0.32, 1.05, b + 0.02, 0.32, 1.15, 'M_SandstoneRed')  # coping
        x = a + 1.0
        while x < b - 0.5:                                                     # little pilasters
            mb.box(x - 0.15, -0.3, 0.45, x + 0.15, 0.3, 1.1, 'M_SandstoneRed')
            x += 2.0
    for kx in (-6.0, 6.0):
        mb.boxc(kx, 0, 0, 2.3, 2.3, 1.15, 'M_SandstoneRed')
        mb.add(chhatri(size=1.9, n_sides=4, height=1.9, pillar_mat='M_Sandstone', dome_mat='M_Sandstone', plinth_h=0.15,
                       seg=20, dome_style='hemi'), T(kx, 0, 1.15))
    # gate piers either side of the opening
    for s in (-1, 1):
        mb.boxc(s * 1.2, 0, 0, 0.5, 0.7, 1.8, 'M_SandstoneRed')
        mb.cylinder(s * 1.2, 0, 1.8, 2.05, 0.22, 10, 'M_Sandstone')
    return mb, []


def register(add):
    add('Train_EMU_Car', 'rail', lambda: asset_emu_car(False),
        'origin = centre of the car at rail top (z=0 = wheel bottom); long axis X; doors at x = -7, 0, +7 m on both sides',
        '21.3 m suburban EMU coach: grimy off-white with purple band, 3 open doors per side with grab poles, barred windows, '
        'curved roof with ventilators, underframe and bogies.', preview_dir=(-0.7, -1.0, 0.45))
    add('Train_EMU_Cab', 'rail', lambda: asset_emu_car(True),
        'as Train_EMU_Car; driving nose + pantograph at +X', 'Leading EMU motor coach.', preview_dir=(0.8, -1.0, 0.45))
    for (name, seed, W, D, fl, p) in VILLAGE_VARIANTS():
        add(name, 'building_village', (lambda seed=seed, W=W, D=D, fl=fl, p=p: (KB.town_house(seed, W, D, fl, p), [])),
            'origin = bottom-centre of the FRONT (street) facade, Z=0 = street level; facade faces -Y',
            '%.1f m wide x %.1f m deep, %d storey village house / shop (railway-side village).' % (W, D, fl))
    for i in range(3):
        add('Shed_Tin_%02d' % (i + 1), 'props', (lambda i=i: asset_tin_shed(40 + i, 2.8 + i * 0.6, 2.4 + 0.2 * i)),
            'origin = front-centre at ground; opens towards -Y', 'Roadside tin-roof stall.')
    add('Ghat_Parapet_20m', 'ghat', asset_ghat_parapet,
        'origin = bottom-centre; wall runs along X; river side is -Y', '20 m sandstone parapet with two domed kiosks and a central gap.')
