"""
kit_assets.py - asset recipes + registry for the Varanasi kit.
Every recipe returns (MB, hulls) where hulls is a list of convex point lists for UCX collision (may be empty).
"""
import math
import random
from mathutils import Vector, Matrix
from kit_core import MB, V, T, Rz, Rx, S, lerp, regular_poly, TAU
from kit_arch import (facade_wall, fits, jharokha, balcony, chhatri, dome, water_tank, shikhara, kalash, flag,
                      flag_pole, arch_panel, corbels, amalaka, PROF_BAND, PROF_CORNICE, PROF_PLINTH, pyramid_roof,
                      scaled_profile, arch_curve, outline)
import kit_buildings as KB

# permutation: build a prism in (a, b) plane and extrude along X:  (x', y', z') -> (z', x', y')
PERM_X = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def extrude_x(mb, poly_yz, x0, x1, mat, cap_mat=None):
    sub = MB()
    sub.prism(poly_yz, x0, x1, mat, top_mat=cap_mat or mat)
    mb.add(sub, PERM_X)


# ======================================================================= GHAT STEPS
def step_profile(depth, z0, z1, n_land, rise=0.3, tread=0.6, top_len=None):
    """Returns list of treads: (y_front, y_back, z_top, kind) with kind 'step' | 'landing' | 'top'."""
    R = z1 - z0
    n = max(2, round(R / rise))
    rise = R / n
    flights = n_land + 1
    base = n // flights
    extra = n % flights
    ks = [base + (1 if i < extra else 0) for i in range(flights)]
    normal = n - flights
    rem = depth - normal * tread
    if rem < flights * 1.5:
        tread = (depth - flights * 1.8) / normal
        rem = depth - normal * tread
    land = rem / flights
    if top_len is not None:
        land = (rem - top_len) / max(1, n_land)
    out = []
    y = 0.0
    z = z0
    for fi, k in enumerate(ks):
        for s in range(k):
            z += rise
            last = (s == k - 1)
            if last:
                L = land if fi < flights - 1 else (depth - y)
                out.append((y, y + L, z, 'landing' if fi < flights - 1 else 'top'))
                y += L
            else:
                out.append((y, y + tread, z, 'step'))
                y += tread
    return out, rise


def ghat_steps(width=20.0, depth=40.0, z0=-3.0, z1=12.0, n_land=3, seed=1, platform=None, rise=0.3, tread=0.6,
               moor_posts=True):
    rng = random.Random(seed)
    mb = MB()
    hulls = []
    prof, rise = step_profile(depth, z0, z1, n_land, rise, tread)
    hw = width / 2
    # forced cut points for platform
    cuts_forced = []
    if platform:
        cuts_forced = [-platform['w'] / 2, platform['w'] / 2]

    def row_cuts():
        xs = [-hw]
        x = -hw
        while x < hw - 0.01:
            x += rng.uniform(0.9, 1.7)
            if x > hw - 0.5:
                x = hw
            for c in cuts_forced:
                if xs[-1] < c < x:
                    x = c
            xs.append(min(x, hw))
        return xs

    def in_platform(xa, xb, ya, yb):
        if not platform:
            return False
        pw = platform['w'] / 2
        return xa >= -pw - 1e-6 and xb <= pw + 1e-6 and ya >= platform['y0'] - 1e-6 and yb <= platform['y1'] + 1e-6

    for (ya, yb, zt, kind) in prof:
        # split long treads (landings) into slab rows
        if kind == 'step':
            rows = [(ya, yb)]
        else:
            nr = max(1, int((yb - ya) / 1.25))
            rows = [(ya + (yb - ya) * i / nr, ya + (yb - ya) * (i + 1) / nr) for i in range(nr)]
        for ri, (ra, rb) in enumerate(rows):
            xs = row_cuts()
            for i in range(len(xs) - 1):
                xa, xb = xs[i], xs[i + 1]
                if in_platform(xa, xb, ra, rb):
                    continue
                jz = rng.uniform(-0.012, 0.012)
                if rng.random() < 0.03:
                    jz -= 0.05
                top = zt + jz
                if top < 0.25:
                    tm, sm = 'M_SandstoneOld', 'M_SandstoneOld'
                elif kind == 'top':
                    tm, sm = 'M_Pavement', 'M_SandstoneSteps'
                else:
                    tm, sm = 'M_SandstoneSteps', 'M_SandstoneSteps'
                bottom = zt - rise if ri == 0 else zt - 0.25
                mb.chamfer_box(xa + 0.004, ra + 0.004, bottom, xb - 0.004, rb - 0.004, top, sm, ch=0.03, top_mat=tm)
    # underlying mass: sides follow block bottoms
    pts = [(0.0, z0)]
    for (ya, yb, zt, kind) in prof:
        pts.append((ya, zt - rise))
        pts.append((yb, zt - rise))
    pts.append((depth, z0))
    clean = []
    for p in pts:
        if not clean or abs(clean[-1][0] - p[0]) + abs(clean[-1][1] - p[1]) > 1e-6:
            clean.append(p)
    sm = 'M_Sandstone'
    for x, n in ((-hw, (-1, 0, 0)), (hw, (1, 0, 0))):
        mb.face_holes([V(x, y, z) for y, z in clean], [], n, sm)
    mb.face([V(-hw, depth, z0), V(hw, depth, z0), V(hw, depth, prof[-1][2] - rise), V(-hw, depth, prof[-1][2] - rise)], sm, normal=(0, 1, 0))
    mb.face([V(-hw, 0, z0), V(hw, 0, z0), V(hw, depth, z0), V(-hw, depth, z0)], sm, normal=(0, 0, -1))
    # collision: one ramp hull per flight + one box per landing
    fy = 0.0
    fz = z0
    for (ya, yb, zt, kind) in prof:
        if kind in ('landing', 'top'):
            # flight ramp from (fy, fz) to (ya, zt)
            if ya > fy + 0.1:
                hulls.append([(-hw, fy, z0), (hw, fy, z0), (-hw, fy, fz + 0.02), (hw, fy, fz + 0.02),
                              (-hw, ya, zt), (hw, ya, zt), (-hw, ya, z0), (hw, ya, z0)])
            hulls.append([(-hw, ya, z0), (hw, ya, z0), (-hw, yb, z0), (hw, yb, z0),
                          (-hw, ya, zt), (hw, ya, zt), (-hw, yb, zt), (hw, yb, zt)])
            fy, fz = yb, zt
    # platform (chabutra / burj) projecting from the steps
    if platform:
        pw = platform['w'] / 2
        py0, py1 = platform['y0'], platform['y1']
        # top height = step height at the back edge of the platform
        ztp = next(zt for (ya, yb, zt, k) in prof if ya <= py1 <= yb + 1e-6)
        R = pw
        poly = [(-pw, py1), (-pw, py0 + R)]
        for i in range(1, 8):
            a = math.pi + math.pi * i / 8
            poly.append((R * math.cos(a), py0 + R + R * math.sin(a) * 1.0))
        poly += [(pw, py0 + R), (pw, py1)]
        mb.prism(poly, z0, ztp - 0.05, 'M_Sandstone', top_mat='M_Pavement', bottom=False)
        mb.sweep_path(poly + [], [(0, 0), (0.08, 0), (0.08, 0.12), (0, 0.16)], 'M_SandstoneRed', closed=True, z0=ztp - 0.21)
        # parapet around the curved front, open at the back to the steps
        seg = poly[1:-1]
        for a, b in zip(seg[:-1], seg[1:]):
            d = Vector((b[0] - a[0], b[1] - a[1], 0))
            L = d.length
            ang = math.degrees(math.atan2(d.y, d.x))
            sub = MB()
            sub.box(-L / 2 - 0.02, 0.0, 0, L / 2 + 0.02, 0.3, 0.75, 'M_SandstoneRed')
            sub.box(-L / 2 - 0.04, -0.03, 0.75, L / 2 + 0.04, 0.33, 0.83, 'M_Sandstone')
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            mb.add(sub, T(mid[0], mid[1], ztp - 0.05) @ Rz(ang))
        # arched niches in the platform front wall (shrines)
        for i in (3, 5):
            a, b = poly[i], poly[i + 1]
            d = Vector((b[0] - a[0], b[1] - a[1], 0))
            ang = math.degrees(math.atan2(d.y, d.x))
            L = d.length
            sub = MB()
            hgt = ztp - 0.05 - max(z0, 0.3)
            zb = max(z0, 0.3)
            op = dict(kind='cusped', cx=0.0, sill=zb + hgt * 0.35, w=min(0.9, L * 0.6), h=min(1.4, hgt * 0.5), depth=0.4,
                      fw=0.1, frame_mat='M_SandstoneRed', back_mat='M_Saffron')
            if fits(op, -L / 2, L / 2, zb, ztp - 0.05):
                from kit_arch import opening as _op
                _op(sub, op, 'M_Sandstone')
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                mb.add(sub, T(mid[0], mid[1], 0) @ Rz(ang) @ T(0, -0.02, 0))
        hulls.append([(-pw, py0, z0), (pw, py0, z0), (-pw, py1, z0), (pw, py1, z0),
                      (-pw, py0, ztp), (pw, py0, ztp), (-pw, py1, ztp), (pw, py1, ztp)])
    # mooring posts at the first landing edge
    if moor_posts:
        first_land = next(p for p in prof if p[3] == 'landing')
        for x in [(-hw + 1.5) + i * (width - 3) / 3 for i in range(4)]:
            if platform and abs(x) < platform['w'] / 2 + 0.5:
                continue
            mb.boxc(x, first_land[0] + 0.35, first_land[2], 0.3, 0.3, first_land[2] + 0.6, 'M_SandstoneRed')
            mb.add(pyramid_roof(0.3, 0.3, 0.12, 'M_SandstoneRed', overhang=0.02), T(x, first_land[0] + 0.35, first_land[2] + 0.6))
            mb.revolve([(0.05, 0), (0.09, 0.05), (0.05, 0.1)], 10, 'M_MetalRust', center=(x, first_land[0] + 0.19, first_land[2] + 0.35))
    return mb, hulls, prof


def asset_ghat_straight():
    mb, hulls, prof = ghat_steps(20.0, 40.0, -3.0, 12.0, 3, seed=11)
    return mb, hulls


def asset_ghat_platform():
    mb, hulls, prof = ghat_steps(20.0, 40.0, -3.0, 12.0, 3, seed=12, platform=dict(w=8.0, y0=6.0, y1=21.0))
    return mb, hulls


def asset_ghat_small():
    mb, hulls, prof = ghat_steps(10.0, 40.0, -3.0, 10.0, 3, seed=13)
    return mb, hulls


def asset_ghat_sidewall(depth=40.0, z0=-3.0, z1=12.0, n_land=3, t=1.2, above=1.0):
    mb = MB()
    prof, rise = step_profile(depth, z0, z1, n_land)
    # raked top line: through the front edge of each landing/top and the start of each flight
    line = [(0.0, z0 + rise + above)]
    for (ya, yb, zt, kind) in prof:
        if kind in ('landing', 'top'):
            line.append((ya, zt + above))
            line.append((yb, zt + above))
    poly = [(0.0, z0)] + line + [(depth, z0)]
    clean = []
    for p in poly:
        if not clean or abs(clean[-1][0] - p[0]) + abs(clean[-1][1] - p[1]) > 1e-6:
            clean.append(p)
    extrude_x(mb, clean, -t / 2, t / 2, 'M_Sandstone')
    # coping along the top line
    for a, b in zip(line[:-1], line[1:]):
        e = 0.12
        mb.hexa([(-t / 2 - e, a[0], a[1]), (t / 2 + e, a[0], a[1]), (t / 2 + e, b[0], b[1]), (-t / 2 - e, b[0], b[1])],
                [(-t / 2 - e, a[0], a[1] + 0.16), (t / 2 + e, a[0], a[1] + 0.16), (t / 2 + e, b[0], b[1] + 0.16), (-t / 2 - e, b[0], b[1] + 0.16)],
                'M_SandstoneRed')
    # string course
    # pier at the water end + at each landing
    piers = [(0.75, line[0][1])] + [(p[0] + 0.0, p[1]) for p in line[1::2]]
    for (y, z) in piers:
        y = max(y, 0.75)
        mb.boxc(0, y, z - 1.2, t + 0.5, 1.5, z + 0.6, 'M_SandstoneRed')
        mb.sweep_path([(-t / 2 - 0.25, y - 0.75), (t / 2 + 0.25, y - 0.75), (t / 2 + 0.25, y + 0.75), (-t / 2 - 0.25, y + 0.75)],
                      [(0, 0), (0.08, 0), (0.08, 0.12), (0, 0.16)], 'M_Sandstone', closed=True, z0=z + 0.6)
        mb.add(pyramid_roof(t + 0.5, 1.5, 0.35, 'M_Sandstone', overhang=0.08), T(0, y, z + 0.76))
    # small shrine niches along the outer face
    for (ya, yb, zt, kind) in prof:
        if kind == 'landing':
            sub = MB()
            from kit_arch import opening as _op
            _op(sub, dict(kind='cusped', cx=0.0, sill=zt + 0.3, w=0.6, h=0.9, depth=0.35, fw=0.08, frame_mat='M_SandstoneRed',
                          back_mat='M_Saffron'), 'M_Sandstone')
            for sgn in (-1, 1):
                mb.add(sub, T(sgn * (t / 2 + 0.001), (ya + yb) / 2 + 1.0, 0) @ Rz(90 * sgn))
    return mb, []


# ======================================================================= TEMPLES
def sanctum(mb, half, z0, h, wall_mat, trim_mat, door=True, door_mat='M_WindowDark', pilasters=True, seed=0):
    """Square garbhagriha walls (half-size), doorway on -Y."""
    for k in range(4):
        sub = MB()
        ops = []
        if k == 0 and door:
            ops.append(dict(kind='cusped', cx=0.0, sill=z0 + 0.22, w=min(1.3, half * 0.9), h=min(h - 0.55, 2.3), depth=0.6, fw=0.14,
                            fd=0.08, frame_mat=trim_mat, back_mat=door_mat))
        elif k != 0 and half > 1.4:
            ops.append(dict(kind='rect', cx=0.0, sill=z0 + h * 0.3, w=0.7, h=min(1.0, h * 0.4), depth=0.3, fw=0.12,
                            frame_mat=trim_mat, back_mat='M_Saffron'))   # deity niches
        ops = KB.keep_fitting(ops, -half, half, z0, z0 + h)
        facade_wall(sub, -half, half, z0, z0 + h, ops, wall_mat)
        if pilasters:
            for sx in (-half + 0.12, half - 0.12):
                sub.box(sx - 0.12, -0.08, z0, sx + 0.12, 0.0, z0 + h, trim_mat, skip=('+y',))
            if half > 1.4:
                sub.box(-0.14 - half * 0.55, -0.12, z0, -half * 0.55 + 0.14, 0.0, z0 + h, trim_mat, skip=('+y',))
                sub.box(half * 0.55 - 0.14, -0.12, z0, half * 0.55 + 0.14, 0.0, z0 + h, trim_mat, skip=('+y',))
        mb.add(sub, Rz(90 * k) @ T(0, -half, 0))
    sq = [(-half, -half), (half, -half), (half, half), (-half, half)]
    mb.sweep_path(sq, PROF_PLINTH, trim_mat, closed=True, z0=z0)
    mb.sweep_path(sq, scaled_profile(PROF_CORNICE, 0.8, 0.7), trim_mat, closed=True, z0=z0 + h)
    mb.boxc(0, 0, z0 + h - 0.05, 2 * half, 2 * half, z0 + h + 0.06, trim_mat)


def stepped_plinth(mb, sx, sy, z0, tiers, mat, top_mat=None, front_steps=True, cy=0.0):
    """Tiered plinth; tiers = [(inset, height), ...] from bottom. Returns top z."""
    z = z0
    for i, (inset, h) in enumerate(tiers):
        mb.box(-sx / 2 + inset, cy - sy / 2 + inset, z, sx / 2 - inset, cy + sy / 2 - inset, z + h, mat,
               mats={'+z': top_mat or mat}, skip=('-z',))
        z += h
    return z


def temple(kind, seed):
    rng = random.Random(seed)
    mb = MB()
    if kind == 'small':
        z = stepped_plinth(mb, 3.0, 3.0, 0.0, [(0.0, 0.25), (0.2, 0.25)], 'M_SandstoneRed', 'M_Sandstone')
        half = 1.05
        sanctum(mb, half, z, 2.1, 'M_Whitewash', 'M_Saffron', pilasters=True)
        zt = z + 2.1 + 0.06
        mb.add(shikhara(half * 1.02, 3.3, 'M_Whitewash', top_mat='M_Saffron', band_mat='M_Saffron', seg=48, seed=seed), T(0, 0, zt))
        # front steps
        mb.box(-0.6, -1.8, 0, 0.6, -1.5, 0.25, 'M_SandstoneRed', skip=('-z',))
        # bell
        mb.beam((-0.5, -1.2, z + 2.0), (0.5, -1.2, z + 2.0), 0.04, 0.04, 'M_MetalRust')
        mb.revolve([(0.0, -0.3), (0.12, -0.3), (0.1, -0.15), (0.05, -0.02), (0, 0)], 12, 'M_Gold', center=(0, -1.2, z + 1.98))
        for sx in (-0.5, 0.5):
            mb.box(sx - 0.03, -1.23, z, sx + 0.03, -1.17, z + 2.03, 'M_MetalRust')
        return mb, []
    if kind == 'medium':
        z = stepped_plinth(mb, 8.0, 8.0, 0.0, [(0.0, 0.45), (0.3, 0.4), (0.55, 0.35)], 'M_SandstoneRed', 'M_Pavement')
        # steps at the front
        for i in range(3):
            mb.box(-1.4, -4.0 - 0.35 * (3 - i), 0, 1.4, -4.0, 0.4 * (i + 1), 'M_SandstoneRed', skip=('-z',))
        # garbhagriha at the back
        half = 2.2
        cy = 1.2
        sub = MB()
        sanctum(sub, half, z, 3.6, 'M_SandstoneRed', 'M_Sandstone', door=True)
        zt = z + 3.66
        sub.add(shikhara(half * 1.02, 10.0, 'M_Sandstone', top_mat='M_Sandstone', band_mat='M_SandstoneRed', seg=64, seed=seed), T(0, 0, zt))
        mb.add(sub, T(0, cy, 0))
        # mandapa (pillared porch) in front
        py0, py1 = -3.3, cy - half
        px = 2.0
        pill = [(-px + 0.2, py0 + 0.2), (px - 0.2, py0 + 0.2), (-px + 0.2, (py0 + py1) / 2), (px - 0.2, (py0 + py1) / 2),
                (-0.8, py0 + 0.2), (0.8, py0 + 0.2)]
        ph = 3.1
        for (x, y) in pill:
            mb.boxc(x, y, z, 0.42, 0.42, z + 0.35, 'M_Sandstone')
            mb.revolve([(0.17, z + 0.35), (0.15, z + 1.2), (0.17, z + 1.3), (0.14, z + 1.4), (0.14, z + ph - 0.45),
                        (0.2, z + ph - 0.3), (0.2, z + ph - 0.2)], 8, 'M_Sandstone', lobe=lambda th: 1 + 0.08 * abs(math.cos(4 * th)),
                       center=(x, y, 0))
            mb.boxc(x, y, z + ph - 0.2, 0.46, 0.46, z + ph, 'M_Sandstone')
        # arches on the front between pillars
        xs = [-px + 0.2, -0.8, 0.8, px - 0.2]
        for a, b in zip(xs[:-1], xs[1:]):
            sub = MB()
            arch_panel(sub, a + 0.2, b - 0.2, z + ph - 1.0, z + ph, 0.3, 'M_Sandstone', 'cusped', 16)
            mb.add(sub, T(0, py0 + 0.2, 0))
        mb.box(-px - 0.1, py0 - 0.1, z + ph, px + 0.1, py1 + 0.1, z + ph + 0.3, 'M_SandstoneRed')
        mb.ring_rect(-px - 0.1, py0 - 0.1, px + 0.1, py1 + 0.1, [(0, 0), (0.35, -0.18), (0.35, -0.1), (0.0, 0.1)], 'M_Sandstone', z0=z + ph + 0.2)
        # samvarana (stepped pyramidal) roof over mandapa + small kalash
        mb.add(pyramid_roof(2 * px, py1 - py0, 1.8, 'M_Sandstone', overhang=-0.1, steps=5), T(0, (py0 + py1) / 2, z + ph + 0.3))
        mb.add(kalash(0.9, 'M_Gold'), T(0, (py0 + py1) / 2, z + ph + 0.3 + 1.75))
        # saffron flag pole at corner
        mb.add(flag_pole(5.0, 1.4, 0.9, seed=seed), T(3.6, -3.6, z))
        mb.add(flag_pole(4.0, 1.2, 0.8, seed=seed + 1), T(-3.6, -3.6, z))
        return mb, []
    if kind == 'riverside':
        # tall shikhara on a high plinth whose lower part (z < 0) is meant to be sunk into the ghat steps
        mb.box(-3.0, -3.0, -3.0, 3.0, 3.0, 0.0, 'M_SandstoneOld', skip=('-z',))
        z = stepped_plinth(mb, 5.6, 5.6, 0.0, [(0.0, 0.5), (0.25, 0.5), (0.5, 0.4)], 'M_SandstoneOld', 'M_Sandstone')
        half = 1.9
        sanctum(mb, half, z, 3.2, 'M_Sandstone', 'M_SandstoneRed')
        zt = z + 3.26
        mb.add(shikhara(half * 1.02, 9.0, 'M_Sandstone', top_mat='M_SandstoneOld', band_mat='M_SandstoneRed', seg=64, seed=seed), T(0, 0, zt))
        # small front porch
        for sx in (-1.0, 1.0):
            mb.boxc(sx, -2.4, z, 0.3, 0.3, z + 2.4, 'M_Sandstone')
        mb.box(-1.4, -2.8, z + 2.4, 1.4, -1.9, z + 2.65, 'M_SandstoneRed')
        mb.add(pyramid_roof(2.6, 0.8, 0.6, 'M_Sandstone', overhang=0.1), T(0, -2.35, z + 2.65))
        # steps down the front (onto the ghat)
        for i in range(4):
            mb.box(-1.0, -2.8 - 0.35 * (4 - i), 0.0 - 0.0, 1.0, -2.8, 0.35 * (i + 1), 'M_SandstoneOld', skip=('-z',))
        return mb, []


# ======================================================================= CHHATRIS
def asset_chhatri_umbrella(seed=5):
    rng = random.Random(seed)
    mb = MB()
    R = 1.75
    zr, za = 2.55, 3.15
    seg = 24
    # bamboo pole (slightly leaning not: keep straight for placement)
    mb.cylinder(0, 0, 0, za + 0.12, 0.045, 10, 'M_WoodPlanks')
    for zz in (0.6, 1.3, 2.0):
        mb.cylinder(0, 0, zz, zz + 0.04, 0.052, 10, 'M_WoodPlanks', caps=False)
    # canopy: slightly convex cone, top surface + underside, fringe
    prof_top = []
    n = 7
    for i in range(n + 1):
        t = i / n
        r = R * (1 - t)
        z = zr + (za - zr) * (1 - (1 - t) ** 1.25)
        prof_top.append((r, z))
    # outer (top) surface bottom->top: from rim to apex
    wob = lambda th: 1 + 0.025 * math.sin(th * 7 + seed)
    mb.revolve([(R * 1.0, zr - 0.02)] + prof_top, seg, 'M_Thatch', lobe=wob)
    # underside (inner): from apex down to rim, offset below
    under = [(0.0, za - 0.1)] + [(r * 0.98, z - 0.1) for r, z in reversed(prof_top[:-1])]
    mb.revolve(under, seg, 'M_Thatch', lobe=wob)
    # rim + fringe hanging down (straw skirt)
    mb.revolve([(R * 0.98, zr - 0.12), (R * 1.03, zr - 0.3), (R * 1.04, zr - 0.28), (R * 1.0, zr - 0.02)], seg, 'M_Thatch', lobe=wob)
    mb.revolve([(R * 0.97, zr - 0.02), (R * 1.0, zr - 0.26), (R * 0.99, zr - 0.28), (R * 0.95, zr - 0.12)], seg, 'M_Thatch', lobe=wob)
    # ribs underneath
    for k in range(12):
        a = TAU * k / 12
        mb.rod((0, 0, za - 0.15), (math.cos(a) * R * 0.95, math.sin(a) * R * 0.95, zr - 0.14), 0.018, 'M_WoodPlanks', seg=5)
        if k % 3 == 0:
            mb.rod((0, 0, 1.9), (math.cos(a) * 0.9, math.sin(a) * 0.9, za - 0.45), 0.012, 'M_WoodPlanks', seg=4)
    # top knob
    mb.revolve([(0, za + 0.05), (0.08, za + 0.07), (0.06, za + 0.18), (0, za + 0.22)], 10, 'M_Thatch')
    # stone weight / base
    mb.cylinder(0, 0, 0, 0.18, 0.22, 10, 'M_Concrete')
    return mb, []


def asset_chowki():
    """Wooden takht/chowki platform used under ghat umbrellas (bonus)."""
    mb = MB()
    L, W, H = 2.0, 1.3, 0.5
    mb.box(-L / 2, -W / 2, H - 0.06, L / 2, W / 2, H, 'M_WoodPlanks')
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box(sx * (L / 2 - 0.05) - 0.05, sy * (W / 2 - 0.05) - 0.05, 0, sx * (L / 2 - 0.05) + 0.05, sy * (W / 2 - 0.05) + 0.05, H - 0.06, 'M_WoodPlanks')
    mb.box(-L / 2 + 0.05, -W / 2 + 0.03, H - 0.16, L / 2 - 0.05, -W / 2 + 0.06, H - 0.06, 'M_WoodPlanks')
    mb.box(-L / 2 + 0.05, W / 2 - 0.06, H - 0.16, L / 2 - 0.05, W / 2 - 0.03, H - 0.06, 'M_WoodPlanks')
    return mb, []


def asset_chhatri_stone():
    mb = MB()
    mb.boxc(0, 0, 0, 4.2, 4.2, 0.45, 'M_SandstoneRed')
    mb.ring_rect(-2.1, -2.1, 2.1, 2.1, [(0, 0.3), (0.06, 0.32), (0.06, 0.45), (0, 0.45)], 'M_Sandstone')
    for i in range(3):
        mb.box(-0.8, -2.1 - 0.3 * (i + 1), 0, 0.8, -2.1, 0.15 * (3 - i), 'M_SandstoneRed', skip=('-z',))
    mb.add(chhatri(size=3.4, n_sides=4, height=2.7, pillar_mat='M_Sandstone', dome_mat='M_Sandstone', plinth_h=0.2, seg=32,
                   dome_style='hemi'), T(0, 0, 0.45))
    return mb, []


# ======================================================================= RAILWAY
RAIL_TOP = 0.9
GAUGE = 1.676


def rail_profile():
    # cross-section of a rail centred at y=0 (in the (y, z) plane), base at z=0, height 0.172
    return [(-0.075, 0.0), (0.075, 0.0), (0.075, 0.012), (0.012, 0.03), (0.009, 0.125), (0.036, 0.135),
            (0.036, 0.172), (-0.036, 0.172), (-0.036, 0.135), (-0.009, 0.125), (-0.012, 0.03), (-0.075, 0.012)]


def track(mb, L=20.0, z_base=0.0, with_ballast=True, sleeper_mat='M_Concrete'):
    hl = L / 2
    zb_top = z_base + 0.55
    if with_ballast:
        # ballast bed trapezoid along X
        extrude_x(mb, [(-2.35, z_base), (2.35, z_base), (1.65, zb_top), (-1.65, zb_top)], -hl, hl, 'M_Ballast')
    rail_h = 0.172
    rz = z_base + RAIL_TOP - rail_h
    sl_top = rz - 0.012
    n = int(L / 0.6)
    for i in range(n):
        x = -hl + (i + 0.5) * L / n
        mb.box(x - 0.13, -1.375, sl_top - 0.21, x + 0.13, 1.375, sl_top, sleeper_mat)
        for sy in (-1, 1):
            yc = sy * (GAUGE / 2 + 0.036)
            mb.box(x - 0.09, yc - 0.1, sl_top, x + 0.09, yc + 0.1, rz, 'M_MetalRust')   # base plates
            mb.box(x - 0.03, yc - 0.1, rz, x + 0.03, yc - 0.075, rz + 0.04, 'M_Steel')  # clips
            mb.box(x - 0.03, yc + 0.075, rz, x + 0.03, yc + 0.1, rz + 0.04, 'M_Steel')
    for sy in (-1, 1):
        yc = sy * (GAUGE / 2 + 0.036)
        extrude_x(mb, [(yc + a, rz + b) for a, b in rail_profile()], -hl, hl, 'M_Steel')


def asset_rail_track():
    mb = MB()
    track(mb, 20.0, 0.0)
    return mb, []


def asset_rail_embankment():
    mb = MB()
    # earth embankment: 12 m base, 6 m top, 3 m high, along X; slight shoulder rounding
    poly = [(-6.0, 0.0), (6.0, 0.0), (5.0, 0.35), (3.3, 2.75), (3.0, 3.0), (-3.0, 3.0), (-3.3, 2.75), (-5.0, 0.35)]
    extrude_x(mb, poly, -10.0, 10.0, 'M_DryGround', cap_mat='M_Dirt')
    # drainage stones / kilometre post
    mb.boxc(8.5, -3.2, 3.0, 0.15, 0.15, 3.9, 'M_Whitewash')
    mb.boxc(8.5, -3.2, 3.9, 0.5, 0.06, 4.3, 'M_Whitewash')
    return mb, []


def asset_rail_bridge():
    """Plate girder span, 20 m along X, deck top = track base at z=0 (girders hang below). Track included."""
    mb = MB()
    hl = 10.0
    for sy in (-1.25, 1.25):
        # I girder: web + flanges
        mb.box(-hl, sy - 0.012, -1.9, hl, sy + 0.012, -0.05, 'M_Steel')
        mb.box(-hl, sy - 0.25, -0.05, hl, sy + 0.25, 0.0, 'M_Steel')
        mb.box(-hl, sy - 0.25, -1.95, hl, sy + 0.25, -1.9, 'M_Steel')
        # stiffeners
        for i in range(17):
            x = -hl + 0.3 + i * (2 * hl - 0.6) / 16
            for s2 in (-1, 1):
                mb.box(x - 0.012, sy + s2 * 0.012, -1.9, x + 0.012, sy + s2 * 0.2, -0.05, 'M_Steel')
    for i in range(9):
        x = -hl + 0.5 + i * (2 * hl - 1.0) / 8
        mb.box(x - 0.1, -1.25, -0.9, x + 0.1, 1.25, -0.05, 'M_Steel')
        mb.beam((x, -1.25, -1.85), (x, 1.25, -0.2), 0.08, 0.02, 'M_Steel')
    # walkway planks + railing on one side
    mb.box(-hl, -2.6, -0.1, hl, -1.5, -0.04, 'M_WoodPlanks')
    for i in range(11):
        x = -hl + i * 2.0
        mb.box(x - 0.03, -2.6, -0.04, x + 0.03, -2.54, 1.0, 'M_Steel')
    mb.box(-hl, -2.6, 0.95, hl, -2.54, 1.0, 'M_Steel')
    track(mb, 20.0, -0.1 - 0.35, with_ballast=False, sleeper_mat='M_WoodPlanks')
    # bearing pedestals at ends
    for x in (-hl + 0.3, hl - 0.3):
        for sy in (-1.25, 1.25):
            mb.boxc(x, sy, -2.25, 0.5, 0.6, -1.95, 'M_Concrete')
    return mb, []


def asset_rail_pier():
    mb = MB()
    mb.boxc(0, 0, -10.0, 2.4, 6.0, -2.25, 'M_Concrete')
    mb.boxc(0, 0, -2.6, 2.8, 6.4, -2.25, 'M_Concrete')
    mb.revolve([(0, -10.0), (1.2, -10.0), (1.2, -2.6), (0, -2.6)], 16, 'M_Concrete', center=(0, 3.0, 0))
    mb.revolve([(0, -10.0), (1.2, -10.0), (1.2, -2.6), (0, -2.6)], 16, 'M_Concrete', center=(0, -3.0, 0))
    mb.transform(T(0, 0, 10.0))
    return mb, []


# ======================================================================= ROADS / GROUND
def periodic_noise(x, y, P, seed, amp):
    r = random.Random(seed)
    s = 0.0
    for k in range(6):
        fx = r.randint(1, 4)
        fy = r.randint(1, 4)
        ph = r.uniform(0, TAU)
        ph2 = r.uniform(0, TAU)
        a = amp / (1 + k * 0.6)
        s += a * math.sin(TAU * fx * x / P + ph) * math.sin(TAU * fy * y / P + ph2)
    return s


def heightfield(mb, x0, x1, y0, y1, nx, ny, hfun, matfun, skirt=0.3):
    grid = [[V(lerp(x0, x1, i / nx), lerp(y0, y1, j / ny), hfun(lerp(x0, x1, i / nx), lerp(y0, y1, j / ny))) for j in range(ny + 1)]
            for i in range(nx + 1)]
    for i in range(nx):
        for j in range(ny):
            q = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
            c = sum(q, Vector()) / 4
            mb.face(q, matfun(c.x, c.y, c.z), normal=(0, 0, 1))
    if skirt:
        zb = min(p.z for col in grid for p in col) - skirt
        edges = [[grid[i][0] for i in range(nx + 1)], [grid[nx][j] for j in range(ny + 1)],
                 [grid[i][ny] for i in range(nx, -1, -1)], [grid[0][j] for j in range(ny, -1, -1)]]
        for e in edges:
            for a, b in zip(e[:-1], e[1:]):
                mid = (a + b) / 2
                mb.face([a, b, V(b.x, b.y, zb), V(a.x, a.y, zb)], matfun(mid.x, mid.y, mid.z),
                        center=V((x0 + x1) / 2, (y0 + y1) / 2, mid.z))
        mb.face([V(x0, y0, zb), V(x1, y0, zb), V(x1, y1, zb), V(x0, y1, zb)], matfun(0, 0, 0), normal=(0, 0, -1))


def asset_road():
    mb = MB()
    L, Wd = 20.0, 8.0

    def h(x, y):
        a = abs(y) / (Wd / 2)
        crown = 0.08 * (1 - a * a)
        if abs(y) > Wd / 2 - 0.8:
            crown -= 0.06 * (abs(y) - (Wd / 2 - 0.8)) / 0.8
        return crown + periodic_noise(x, y, 20.0, 7, 0.01) * (1 if abs(y) < Wd / 2 - 0.2 else 0)

    def m(x, y, z):
        return 'M_Trail' if abs(y) > Wd / 2 - 1.0 else 'M_Dirt'
    heightfield(mb, -L / 2, L / 2, -Wd / 2, Wd / 2, 40, 16, h, m, skirt=0.3)
    return mb, []


def asset_ground_tile():
    mb = MB()
    heightfield(mb, -10, 10, -10, 10, 20, 20, lambda x, y: periodic_noise(x, y, 20.0, 3, 0.03), lambda x, y, z: 'M_DryGround', skirt=0.2)
    return mb, []


def asset_sandbank():
    mb = MB()

    def h(x, y):
        return periodic_noise(x, y, 50.0, 21, 0.22) + 0.25 * math.sin(TAU * x / 50.0 + 1.0) * math.sin(TAU * y / 50.0) * 0.5

    def m(x, y, z):
        return 'M_RiverPebbles' if periodic_noise(x + 7, y - 3, 50.0, 99, 1.0) > 0.55 else ('M_MudDry' if z > -0.05 else 'M_Riverbed')
    heightfield(mb, -25, 25, -25, 25, 50, 50, h, m, skirt=0.5)
    return mb, []


def asset_gully_stairs():
    """3 m wide stairs, 10 m run, rising 6 m towards +Y (bottom-front centre pivot). Low kerbs + drain channel."""
    mb = MB()
    rng = random.Random(77)
    n = 20
    rise = 6.0 / n
    run = 10.0 / n
    hw = 1.5
    for i in range(n):
        ya = i * run
        zt = (i + 1) * rise
        xs = [-hw, rng.uniform(-0.6, -0.2), rng.uniform(0.3, 0.7), hw]
        for a, b in zip(xs[:-1], xs[1:]):
            mb.chamfer_box(a + 0.004, ya, zt - rise - 0.02, b - 0.004, ya + run, zt + rng.uniform(-0.01, 0.01), 'M_SandstoneSteps',
                           ch=0.025, top_mat='M_SandstoneSteps' if i > 1 else 'M_SandstoneOld')
    # side kerbs (raked) and mass sides
    pts = [(0.0, 0.0)] + [(i * run, i * rise) for i in range(n)] + [(n * run, n * rise - rise)] + [(n * run, 0.0)]
    clean = []
    for (y, z) in [(0.0, -0.02)] + [(i * run, (i + 1) * rise - rise - 0.02) for i in range(n)] + [(n * run, -0.02)]:
        clean.append((y, z))
    for sgn in (-1, 1):
        x = sgn * hw
        mb.face_holes([V(x, y, z) for y, z in [(0.0, -0.3)] + [(i * run, i * rise - 0.02) for i in range(n)] + [(10.0, 6.0 - rise - 0.02), (10.0, -0.3)]],
                      [], (sgn, 0, 0), 'M_SandstoneSteps')
        # raked kerb
        mb.hexa([(x - 0.1, 0.0, 0.25), (x + 0.1, 0.0, 0.25), (x + 0.1, 10.0, 6.25), (x - 0.1, 10.0, 6.25)],
                [(x - 0.1, 0.0, 0.5), (x + 0.1, 0.0, 0.5), (x + 0.1, 10.0, 6.5), (x - 0.1, 10.0, 6.5)], 'M_SandstoneRed')
    return mb, [[(-hw, 0, -0.3), (hw, 0, -0.3), (-hw, 0, rise), (hw, 0, rise), (-hw, 10, 6.0), (hw, 10, 6.0), (-hw, 10, -0.3), (hw, 10, -0.3)]]


# ======================================================================= FORT
def merlons_x(mb, x0, x1, y0, y1, z, mat, w=0.7, gap=0.45, h=1.1, loophole=True):
    n = max(1, int((x1 - x0) / (w + gap)))
    step = (x1 - x0) / n
    for i in range(n):
        cx = x0 + (i + 0.5) * step
        mb.box(cx - w / 2, y0, z, cx + w / 2, y1, z + h * 0.75, mat)
        # rounded kangura top
        sub = MB()
        sub.revolve([(w / 2, 0), (w / 2 * 0.95, h * 0.12), (w / 2 * 0.6, h * 0.22), (0.0, h * 0.28)], 12, mat,
                    sy=(y1 - y0) / w)
        mb.add(sub, T(cx, (y0 + y1) / 2, z + h * 0.75))


def asset_fort_wall():
    mb = MB()
    L, H, Tk = 20.0, 12.0, 4.0
    hl = L / 2
    bat = 0.8
    # battered lower wall: front face slopes from y=-bat at z=0 to y=0 at z=5
    mb.hexa([(-hl, -bat, 0), (hl, -bat, 0), (hl, Tk, 0), (-hl, Tk, 0)], [(-hl, 0, 5.0), (hl, 0, 5.0), (hl, Tk, 5.0), (-hl, Tk, 5.0)],
            'M_SandstoneRed', skip_bottom=True)
    # upper wall with loopholes and jharokhas
    sub = MB()
    ops = []
    for i in range(6):
        cx = -hl + (i + 0.5) * L / 6
        if i in (1, 4):
            continue
        ops.append(dict(kind='rect', cx=cx, sill=7.0, w=0.18, h=0.8, depth=0.6, fw=0.06, frame_mat='M_Sandstone'))
        ops.append(dict(kind='pointed', cx=cx, sill=9.3, w=0.5, h=0.9, depth=0.5, fw=0.08, frame_mat='M_Sandstone'))
    facade_wall(sub, -hl, hl, 5.0, H, ops, 'M_SandstoneRed')
    mb.add(sub)
    mb.box(-hl, 0, 5.0, hl, Tk, H, 'M_SandstoneRed', skip=('-y', '-z'))
    # string courses
    mb.sweep_x(-hl, hl, 0.0, [(0, -0.2), (0.15, -0.2), (0.15, 0.0), (0, 0.1)], 'M_Sandstone', z0=5.0)
    mb.sweep_x(-hl, hl, 0.0, [(0, 0.0), (0.12, 0.0), (0.12, 0.18), (0, 0.18)], 'M_Sandstone', z0=8.4)
    # machicolation corbel band under parapet
    for i in range(40):
        x = -hl + 0.25 + i * (L - 0.5) / 39
        mb.box(x - 0.1, -0.45, H - 0.55, x + 0.1, 0.0, H - 0.05, 'M_Sandstone')
    mb.box(-hl, -0.5, H - 0.05, hl, 0.0, H + 0.1, 'M_Sandstone', skip=('+y',))
    # parapet with merlons (front) and walkway
    mb.box(-hl, -0.5, H + 0.1, hl, 0.1, H + 0.6, 'M_SandstoneRed')
    merlons_x(mb, -hl + 0.1, hl - 0.1, -0.5, 0.1, H + 0.6, 'M_SandstoneRed')
    mb.box(-hl, Tk - 0.5, H, hl, Tk, H + 1.0, 'M_SandstoneRed', skip=('-z',))
    # jharokhas on the wall
    for x in (-hl + 1.5 * L / 6, -hl + 4.5 * L / 6):
        mb.add(jharokha(w=2.2, h=2.2, dp=1.0, n_arches=3, roof='bangla', body_mat='M_Sandstone', trim_mat='M_SandstoneRed',
                        roof_mat='M_Sandstone'), T(x, 0.0, 7.6))
    return mb, []


def asset_fort_tower():
    mb = MB()
    R0, R1, H = 5.2, 4.6, 14.0
    seg = 48
    # battered drum
    mb.revolve([(0, 0), (R0, 0), (R1, 6.0), (R1, H - 0.6), (0, H - 0.6)], seg, 'M_SandstoneRed')
    mb.revolve([(R1, 6.0), (R1 + 0.15, 6.0), (R1 + 0.15, 6.25), (R1, 6.3)], seg, 'M_Sandstone')
    # corbel ring + parapet ring
    for k in range(36):
        a = TAU * k / 36
        sub = MB()
        sub.box(-0.1, -0.5, -0.5, 0.1, 0.0, 0.0, 'M_Sandstone')
        mb.add(sub, T(math.cos(a) * R1, math.sin(a) * R1, H - 0.6) @ Rz(math.degrees(a) + 90))
    mb.revolve([(R1, H - 0.6), (R1 + 0.5, H - 0.6), (R1 + 0.5, H + 0.4), (R1 - 0.4, H + 0.4), (R1 - 0.4, H - 0.6)], seg, 'M_SandstoneRed')
    for k in range(18):
        a = TAU * (k + 0.5) / 18
        sub = MB()
        sub.boxc(0, 0, 0, 0.9, 0.7, 0.8, 'M_SandstoneRed')
        sub.revolve([(0.45, 0.8), (0.4, 0.95), (0.25, 1.05), (0, 1.1)], 10, 'M_SandstoneRed', sy=0.7 / 0.9)
        mb.add(sub, T(math.cos(a) * (R1 + 0.05), math.sin(a) * (R1 + 0.05), H + 0.4) @ Rz(math.degrees(a) + 90))
    # loopholes (dark slits) around
    for k in range(10):
        a = TAU * k / 10 + 0.3
        for z in (8.0, 11.0):
            sub = MB()
            sub.box(-0.1, -0.05, z, 0.1, 0.02, z + 0.8, 'M_WindowDark')
            mb.add(sub, T(math.cos(a) * (R1 + 0.02), math.sin(a) * (R1 + 0.02), 0) @ Rz(math.degrees(a) + 90))
    # top chhatri (octagonal)
    mb.add(chhatri(size=4.2, n_sides=8, height=3.0, pillar_mat='M_Sandstone', dome_mat='M_Sandstone', plinth_h=0.3, seg=32,
                   dome_style='onion'), T(0, 0, H - 0.6))
    return mb, []


def asset_fort_gate():
    mb = MB()
    W, H, D = 14.0, 16.0, 8.0
    hw = W / 2
    aw, ah = 4.6, 7.8
    # front and back facades with the passage arch (through-hole) + jharokha
    for side, M in (('front', T(0, 0, 0)), ('back', T(0, D, 0) @ Rz(180))):
        sub = MB()
        ops = [dict(kind='pointed', cx=0.0, sill=0.32, w=aw, h=ah, depth=D if side == 'front' else 0.0, fw=0.25, fd=0.15,
                    frame_mat='M_Sandstone', back_mat=None, reveal=(side == 'front'), reveal_mat='M_SandstoneRed', seg=20)]
        if side == 'front':
            for cx in (-4.6, 4.6):
                ops.append(dict(kind='cusped', cx=cx, sill=4.0, w=1.0, h=1.8, depth=0.4, fw=0.12, frame_mat='M_Sandstone'))
                ops.append(dict(kind='pointed', cx=cx, sill=8.2, w=0.9, h=1.6, depth=0.4, fw=0.1, frame_mat='M_Sandstone'))
        facade_wall(sub, -hw, hw, 0.0, H, ops, 'M_SandstoneRed')
        mb.add(sub, M)
    # side walls, roof
    mb.box(-hw, 0, 0, hw, D, H, 'M_SandstoneRed', skip=('-y', '+y', '-z'))
    # passage floor
    mb.box(-aw / 2, -0.5, 0.0, aw / 2, D + 0.5, 0.3, 'M_Pavement', skip=('-z',))
    # open door leaves inside the passage
    for sgn in (-1, 1):
        sub = MB()
        sub.box(0, 0, 0.3, 0.12, 2.3, 0.3 + ah - 1.8, 'M_WoodPlanks')
        for zz in (1.0, 2.5, 4.0):
            sub.box(-0.03, 0.05, zz, 0.0, 2.25, zz + 0.1, 'M_Steel')   # iron straps
        mb.add(sub, T(sgn * (aw / 2 - 0.15) - (0.12 if sgn > 0 else 0), 0.8, 0))
    # iron spikes on the door face (sparse)
    # flanking semi-octagonal towers
    for sgn in (-1, 1):
        KB.oct_tower(mb, sgn * (hw + 0.8), 1.2, 2.6, 0.0, 5, 'M_SandstoneRed', 'M_Sandstone', random.Random(5 + sgn),
                     top_chhatri=True, chh_mat='M_Sandstone', fh=3.4, faces=(0, 1, 7, 2 if sgn > 0 else 6))
    # string course + jharokha above the arch
    mb.sweep_x(-hw, hw, 0.0, [(0, -0.2), (0.15, -0.2), (0.15, 0.0), (0, 0.1)], 'M_Sandstone', z0=10.6)
    mb.add(jharokha(w=3.2, h=2.4, dp=1.1, n_arches=3, roof='bangla', body_mat='M_Sandstone', trim_mat='M_SandstoneRed',
                    roof_mat='M_Sandstone'), T(0, 0, 11.6))
    # parapet & merlons
    mb.box(-hw, -0.4, H, hw, D, H + 0.5, 'M_SandstoneRed')
    merlons_x(mb, -hw + 0.1, hw - 0.1, -0.4, 0.2, H + 0.5, 'M_SandstoneRed')
    # small chhatris at top
    for cx in (-3.2, 3.2):
        mb.add(chhatri(size=2.2, height=2.0, pillar_mat='M_Sandstone', dome_mat='M_Sandstone', seg=20), T(cx, D / 2, H + 0.5))
    # ganesh niche / saffron above the arch keystone
    mb.boxc(0, -0.2, 0.3 + ah + 0.6, 0.6, 0.2, 0.3 + ah + 1.3, 'M_Saffron')
    return mb, [[(-hw - 3, 0, 0), (-aw / 2, 0, 0), (-hw - 3, D, 0), (-aw / 2, D, 0), (-hw - 3, 0, H), (-aw / 2, 0, H), (-hw - 3, D, H), (-aw / 2, D, H)],
                [(aw / 2, 0, 0), (hw + 3, 0, 0), (aw / 2, D, 0), (hw + 3, D, 0), (aw / 2, 0, H), (hw + 3, 0, H), (aw / 2, D, H), (hw + 3, D, H)],
                [(-aw / 2, 0, 0.3 + ah), (aw / 2, 0, 0.3 + ah), (-aw / 2, D, 0.3 + ah), (aw / 2, D, 0.3 + ah), (-aw / 2, 0, H), (aw / 2, 0, H), (-aw / 2, D, H), (aw / 2, D, H)],
                [(-aw / 2, 0, 0.0), (aw / 2, 0, 0.0), (-aw / 2, D, 0.0), (aw / 2, D, 0.0), (-aw / 2, 0, 0.3), (aw / 2, 0, 0.3), (-aw / 2, D, 0.3), (aw / 2, D, 0.3)]]


# ======================================================================= BOAT
def asset_boat(seed=8):
    """Classic Varanasi wooden rowing boat (~7.2 m), long axis along X, keel bottom at z=0, centred."""
    mb = MB()
    L = 7.2
    ns = 24
    nsec = 9
    thick = 0.05

    def station(t):
        # t in [-1, 1] along the length
        a = abs(t)
        half_w = 0.95 * (1 - a ** 2.4) + 0.04
        depth = 0.62 + 0.25 * a ** 3        # sheer rises at the ends
        bottom = 0.0 + 0.18 * a ** 2.2       # rocker
        return half_w, depth, bottom

    def section(t, inset=0.0):
        hw, dpt, bot = station(t)
        pts = []
        for k in range(nsec + 1):
            s = -1 + 2 * k / nsec      # -1 (left gunwale) .. 1 (right gunwale)
            ang = s * math.pi / 2
            y = (hw - inset) * math.sin(ang) * (1.0 if abs(s) > 0.2 else 1.0)
            # flat-ish bottom, flared sides
            z = bot + (dpt - bot) * (1 - math.cos(ang) ** 0.6) + inset * 0.8 * math.cos(ang)
            pts.append(V(t * L / 2, y, z))
        return pts
    outer = [section(-1 + 2 * i / ns) for i in range(ns + 1)]
    inner = [section(-1 + 2 * i / ns, thick) for i in range(ns + 1)]
    # paint: top band saffron, second band blue, rest wood
    for i in range(ns):
        for k in range(nsec):
            q = [outer[i][k], outer[i + 1][k], outer[i + 1][k + 1], outer[i][k + 1]]
            zmid = sum(p.z for p in q) / 4
            hw, dpt, bot = station(-1 + 2 * (i + 0.5) / ns)
            rel = (zmid - bot) / (dpt - bot)
            m = 'M_Saffron' if (k in (0, nsec - 1)) else ('M_PlasterBlue' if k in (1, nsec - 2) and rel > 0.55 else 'M_WoodPlanks')
            c = V((q[0].x + q[1].x) / 2, 0, dpt * 0.8)
            mb.face(q, m, center=c)
            qi = [inner[i][k], inner[i + 1][k], inner[i + 1][k + 1], inner[i][k + 1]]
            mb.face(qi, 'M_WoodPlanks', normal=(c - sum(qi, Vector()) / 4))
    # gunwale tops
    for i in range(ns):
        for k in (0, nsec):
            q = [outer[i][k], outer[i + 1][k], inner[i + 1][k], inner[i][k]]
            mb.face(q, 'M_Saffron', normal=(0, 0, 1))
    # end caps (stem / stern) - close with posts
    for i, sgn in ((0, -1), (ns, 1)):
        ring = outer[i] + list(reversed(inner[i]))
        mb.face_holes(ring, [], (sgn, 0, 0), 'M_WoodPlanks')
        hw, dpt, bot = station(sgn * 1.0)
        mb.box(sgn * L / 2 - 0.08, -0.06, bot, sgn * L / 2 + 0.08, 0.06, dpt + 0.22, 'M_WoodPlanks')
    # thwarts (benches) + raised decks at the ends
    for t in (-0.55, -0.2, 0.15, 0.5):
        hw, dpt, bot = station(t)
        x = t * L / 2
        mb.box(x - 0.14, -hw + 0.08, dpt - 0.2, x + 0.14, hw - 0.08, dpt - 0.15, 'M_WoodPlanks')
    for sgn in (-1, 1):
        t0, t1 = 0.72, 0.92
        hw, dpt, bot = station(t0)
        mb.box(min(sgn * t0 * L / 2, sgn * t1 * L / 2), -hw * 0.9, dpt - 0.12, max(sgn * t0 * L / 2, sgn * t1 * L / 2), hw * 0.9, dpt - 0.07, 'M_WoodPlanks')
    # floor boards
    mb.box(-L * 0.35, -0.45, 0.1, L * 0.35, 0.45, 0.13, 'M_WoodPlanks')
    # oars resting across
    for sgn in (-1, 1):
        mb.beam((-0.3, sgn * 1.05, 0.72), (1.9, sgn * 0.6, 0.74), 0.05, 0.05, 'M_WoodPlanks')
        mb.box(1.9 - 0.02, sgn * 0.6 - 0.09, 0.66, 2.45, sgn * 0.6 + 0.09, 0.69, 'M_WoodPlanks')
        mb.box(0.0 - 0.03, sgn * 0.97 - 0.03, 0.62, 0.03, sgn * 0.97 + 0.03, 0.82, 'M_WoodPlanks')   # tholes
    return mb, []


# ======================================================================= MISC
def asset_electric_pole():
    mb = MB()
    H = 9.0
    # tapered concrete pole (H-section approximated with a tapered box) + crossbar + insulators + transformer box
    mb.hexa([(-0.14, -0.1, 0), (0.14, -0.1, 0), (0.14, 0.1, 0), (-0.14, 0.1, 0)],
            [(-0.07, -0.07, H), (0.07, -0.07, H), (0.07, 0.07, H), (-0.07, 0.07, H)], 'M_Concrete')
    for zc, L in ((H - 0.35, 1.9), (H - 1.3, 1.4)):
        mb.box(-0.05, -L / 2, zc - 0.05, 0.05, L / 2, zc + 0.05, 'M_Steel')
        mb.beam((0, -0.1, zc - 0.6), (0, -L * 0.35, zc - 0.05), 0.03, 0.03, 'M_Steel')
        mb.beam((0, 0.1, zc - 0.6), (0, L * 0.35, zc - 0.05), 0.03, 0.03, 'M_Steel')
        for y in (-L / 2 + 0.08, -L / 6, L / 6, L / 2 - 0.08):
            mb.revolve([(0.0, 0.05), (0.04, 0.05), (0.05, 0.1), (0.035, 0.12), (0.05, 0.16), (0.03, 0.2), (0.0, 0.2)], 8, 'M_Whitewash',
                       center=(0, y, zc))
    # street light arm
    mb.beam((0, -0.08, 6.5), (0, -1.3, 6.9), 0.04, 0.04, 'M_Steel')
    mb.box(-0.1, -1.5, 6.78, 0.1, -1.15, 6.9, 'M_Steel')
    # junction/meter box and tangled service wire stubs
    mb.box(-0.2, -0.3, 2.3, 0.2, -0.1, 2.9, 'M_MetalRust')
    mb.box(-0.02, -0.14, 2.9, 0.02, -0.1, 7.5, 'M_WindowDark')
    return mb, []


def asset_wall_boundary():
    mb = MB()
    L, H = 10.0, 2.0
    mb.box(-L / 2, -0.12, 0, L / 2, 0.12, H, 'M_BrickPlaster')
    mb.box(-L / 2 - 0.02, -0.16, H, L / 2 + 0.02, 0.16, H + 0.08, 'M_Concrete')
    mb.box(-L / 2, -0.16, 0, L / 2, 0.16, 0.25, 'M_Concrete')
    for x in (-L / 2 + 0.2, 0.0, L / 2 - 0.2):
        mb.boxc(x, 0, 0, 0.4, 0.4, H + 0.3, 'M_PlasterWhite')
        mb.boxc(x, 0, H + 0.3, 0.48, 0.48, H + 0.38, 'M_Concrete')
    # glass shards / iron spikes on top
    for i in range(40):
        x = -L / 2 + 0.25 + i * (L - 0.5) / 39
        mb.box(x - 0.01, -0.01, H + 0.08, x + 0.01, 0.01, H + 0.22, 'M_MetalRust')
    return mb, []


def asset_steps_railing():
    mb = MB()
    L = 5.0
    for i in range(6):
        x = -L / 2 + i * L / 5
        mb.cylinder(x, 0, 0, 1.0, 0.025, 8, 'M_Steel')
        mb.boxc(x, 0, 0, 0.14, 0.14, 0.02, 'M_Steel')
    mb.rod((-L / 2, 0, 1.0), (L / 2, 0, 1.0), 0.03, 'M_Steel', seg=8)
    mb.rod((-L / 2, 0, 0.5), (L / 2, 0, 0.5), 0.018, 'M_Steel', seg=6)
    return mb, []


def asset_flag_pole():
    mb = MB()
    mb.add(flag_pole(7.0, 1.8, 1.1, seed=3, r=0.045))
    mb.cylinder(0, 0, 0, 0.35, 0.22, 10, 'M_Concrete')
    return mb, []


def asset_water_tank():
    mb = MB()
    mb.add(water_tank('plastic', r=0.6, h=1.25, stand=1.0))
    return mb, []


def asset_temple(kind, seed):
    return temple(kind, seed)


# ======================================================================= REGISTRY
def registry():
    R = []

    def add(name, cat, fn, pivot, notes='', preview_dir=(-0.55, -1.0, 0.5), ground=True):
        R.append(dict(name=name, category=cat, fn=fn, pivot=pivot, notes=notes, preview_dir=preview_dir, ground=ground))
    add('GhatSteps_Straight_20m', 'ghat', asset_ghat_straight,
        'origin = middle of the front (water) edge at water level Z=0; steps rise towards +Y; mass bottom at Z=-3',
        '20 m wide (X), 40 m deep (Y 0..40), Z -3..+12, ~0.3 rise / 0.6 tread, 3 landings + top platform. '
        'Individual chamfered stone slabs with jitter. UCX ramp hull per flight + box per landing.', preview_dir=(-0.8, -1.0, 0.6))
    add('GhatSteps_Platform_20m', 'ghat', asset_ghat_platform,
        'origin = middle of the front (water) edge at water level Z=0; steps rise towards +Y',
        'Same as straight flight with a central 8 m wide raised chabutra/burj platform (Y 6..21) with curved front, parapet and shrine niches; '
        'platform top is flush with the steps at its back edge.', preview_dir=(-0.8, -1.0, 0.6))
    add('GhatSteps_SideWall', 'ghat', lambda: asset_ghat_sidewall(),
        'origin = wall centreline at the water edge (Y=0), Z=0 water level; wall runs Y 0..40 along +Y, 1.2 m thick centred on X=0',
        'Raked end wall / side cap for the 20 m ghat flights (+1 m above the step line), piers with pyramid caps at landings, '
        'shrine niches. Place at X = +/-(10 + 0.6) m next to a 20 m flight.', preview_dir=(-1.0, -0.5, 0.45))
    add('GhatStepsSmall_10m', 'ghat', asset_ghat_small,
        'origin = middle of the front (water) edge at water level Z=0; steps rise towards +Y',
        '10 m wide, 40 m deep, Z -3..+10 (east bank / Ramnagar). Rotate 180 deg yaw to face the river from the east bank.', preview_dir=(-0.9, -1.0, 0.6))
    for (name, seed, W, D, fl, p) in KB.RIVERFRONT_VARIANTS():
        add(name, 'building_riverfront', (lambda seed=seed, W=W, D=D, fl=fl, p=p: (KB.riverfront_house(seed, W, D, fl, p), [])),
            'origin = bottom-centre of the FRONT facade wall (Z=0 = underside of sandstone plinth); facade faces -Y (river)',
            '%.1f m wide x %.1f m deep, %d storeys (3.2 m) on a %.1f m sandstone plinth; plinth/balconies/jharokhas project into -Y. '
            'Sit on top of ghats at Z=+12 m.' % (W, D, fl, p.get('plinth_h', 1.6)))
    for v, nm, note in ((1, 'Palace_Darbhanga', 'Darbhanga-ghat style sandstone palace, 32 m wide, 7 storeys on a 4 m battered plinth, octagonal corner towers with chhatris, projecting frontispiece.'),
                        (2, 'Palace_ChetSingh', 'Chet Singh fort-palace style, 28 m wide, 6 storeys on a 5 m plinth, ochre plaster + red sandstone, tall octagonal corner towers.')):
        add(nm, 'building_palace', (lambda v=v: (KB.palace(900 + v, v), [])),
            'origin = bottom-centre of the FRONT facade wall (Z=0 = underside of plinth); facade faces -Y (river)', note)
    for (name, seed, W, D, fl, p) in KB.TOWN_VARIANTS():
        add(name, 'building_town', (lambda seed=seed, W=W, D=D, fl=fl, p=p: (KB.town_house(seed, W, D, fl, p), [])),
            'origin = bottom-centre of the FRONT (street) facade, Z=0 = street level; facade faces -Y',
            '%.1f m wide x %.1f m deep, %d storeys, ground-floor shops with rolling shutters / wood shutters, awnings, '
            'M_Signboard quads (0..1 UVs, not world-scale), wire hooks. Side walls blank (party walls).' % (W, D, fl))
    add('Temple_Small', 'temple', lambda: asset_temple('small', 31), 'origin = bottom-centre of the plinth footprint (3x3 m), door faces -Y',
        '3x3 m whitewashed shrine with saffron-banded shikhara, gold kalash, saffron flag, bell.')
    add('Temple_Medium', 'temple', lambda: asset_temple('medium', 32), 'origin = centre of the 8x8 m plinth at ground level; entrance faces -Y',
        '8x8 m sandstone temple, shikhara ~10 m above the sanctum walls (~16 m total), urushringas, mandapa porch, gold kalash, saffron flags.')
    add('Temple_Riverside', 'temple', lambda: asset_temple('riverside', 33),
        'origin = centre of footprint at the step surface; foundation block extends to Z=-3 so it can be sunk into ghat steps; faces -Y',
        '5.6 m footprint riverside shrine (Ratneshwar style) with water-stained lower courses.')
    add('Chhatri_Umbrella', 'props', asset_chhatri_umbrella, 'origin = foot of the bamboo pole at ground level',
        '3.5 m diameter straw umbrella (M_Thatch) on a bamboo pole (M_WoodPlanks), canopy rim 2.55 m, apex 3.15 m.')
    add('Chhatri_Stone', 'props', asset_chhatri_stone, 'origin = centre of platform base at ground level; front steps face -Y',
        '4.2 m sandstone platform with a 4-pillar cusped-arch chhatri pavilion and dome.')
    add('Chowki_Platform', 'props', asset_chowki, 'origin = centre bottom', 'Wooden takht for priests under umbrellas (bonus).')
    add('Rail_Track_20m', 'rail', asset_rail_track, 'origin = bottom-centre of the ballast bed; track runs along X; rail top at Z=0.9',
        'Broad gauge 1.676 m, concrete sleepers every ~0.6 m, rail profile swept, ballast trapezoid 4.7 m base.')
    add('Rail_Embankment_20m', 'rail', asset_rail_embankment, 'origin = bottom-centre; runs along X; flat top (6 m) at Z=3',
        '12 m base, 6 m top, 3 m high earth embankment. Place Rail_Track_20m on top at Z=+3.')
    add('Rail_Bridge_Span_20m', 'rail', asset_rail_bridge, 'origin = centre of span at deck level; track runs along X, rail top at Z=+0.45',
        'Plate-girder span with integrated track (wooden sleepers) and walkway; girders hang 2 m below; bearings at Z=-2.25.')
    add('Rail_Bridge_Pier', 'rail', asset_rail_pier, 'origin = pier base centre; top (bearing seat) at Z=+7.75 (put span origin 10 m above base)',
        'Concrete pier with rounded cutwaters, 10 m tall total.')
    add('Road_Dusty_20m', 'ground', asset_road, 'origin = centre of the road at edge level Z=0; runs along X; crown +0.08 m',
        '8 m wide dirt road with rocky-trail shoulders (M_Trail), 0.3 m skirt below.', preview_dir=(-0.6, -1.0, 0.9))
    add('Gully_Stairs_10m', 'ground', asset_gully_stairs, 'origin = bottom-front centre (lowest step edge) at Z=0; rises 6 m towards +Y over 10 m',
        '3 m wide gully stairs (20 x 0.3 m risers, 0.5 m treads) with raked sandstone kerbs. UCX ramp.', preview_dir=(-0.9, -1.0, 0.6))
    add('Ground_Tile_20m', 'ground', asset_ground_tile, 'origin = tile centre, Z=0 average surface', 'Tileable (periodic noise, edges match).', preview_dir=(-0.6, -1.0, 0.9))
    add('Sandbank_Tile_50m', 'ground', asset_sandbank, 'origin = tile centre, Z=0 average surface',
        'Gently undulating (+/-0.4 m) tileable sandbank, M_MudDry with M_RiverPebbles / M_Riverbed patches.', preview_dir=(-0.6, -1.0, 0.9))
    add('Fort_Wall_20m', 'fort', asset_fort_wall, 'origin = bottom-centre of the front face (vertical part at Y=0; battered base projects to Y=-0.8); faces -Y',
        '20 m long, 4 m thick, ~13 m high sandstone curtain wall with battered base, kangura merlons, machicolation corbels, loopholes, 2 jharokhas.')
    add('Fort_Tower', 'fort', asset_fort_tower, 'origin = centre of the round bastion base', 'Round battered bastion R 5.2->4.6 m, 14 m + octagonal chhatri on top.')
    add('Fort_Gate', 'fort', asset_fort_gate, 'origin = bottom-centre of the front face; walk-through passage along +Y; faces -Y',
        '14 m wide 16 m high gatehouse with a 4.6 x 7.8 m pointed-arch passage (open), flanking octagonal towers, jharokha, chhatris. UCX boxes keep the passage open.')
    add('Boat_Wooden_Varanasi', 'props', asset_boat, 'origin = keel bottom centre; long axis along X; waterline approx Z=+0.3',
        '7.2 m double-ended wooden rowing boat with saffron gunwale and blue band, thwarts, oars.', preview_dir=(-0.8, -1.0, 0.7))
    add('Electric_Pole', 'props', asset_electric_pole, 'origin = pole base centre; crossbars along Y', '9 m concrete pole with 2 crossbars, insulators, street light, meter box.')
    add('Wall_Boundary_10m', 'props', asset_wall_boundary, 'origin = bottom-centre; runs along X', '2 m brick-plaster boundary wall with piers and spikes.')
    add('Steps_Railing_5m', 'props', asset_steps_railing, 'origin = bottom-centre; runs along X', 'Steel pipe railing, 1 m high, 6 posts.')
    add('Flag_Pole_Saffron', 'props', asset_flag_pole, 'origin = pole base', '7 m bamboo pole with saffron pennant.')
    add('Water_Tank_Rooftop', 'props', asset_water_tank, 'origin = stand base centre', 'Black plastic (M_WindowDark) ribbed tank on a rusty stand.')
    return R
